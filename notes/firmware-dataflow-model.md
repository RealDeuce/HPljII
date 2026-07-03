# Firmware Dataflow Model

Goal: explain how the LaserJet II formatter ROM turns host bytes into page
objects and then rendered output. This is the reader-facing spine for the
reverse-engineering notes. Generated analysis files, fixture names, and focused
disassemblies are evidence for claims in this file and in the linked detail
notes; they are not the primary model.

The current documented path is:

```text
host bytes
  -> normalized byte fetch
  -> parser state and six-byte command records
  -> command handlers and delayed payload handlers
  -> current page root and page objects
  -> publication into the page/control pool
  -> active render work record
  -> band render dispatch
  -> object renderers and pixel writes
```

This file is intentionally top-down. It names the state handoffs a renderer or
emulator must preserve, then points to the detail notes that own each command
family or object producer.

## Host Bytes

All normal parser input is funneled through the byte-source multiplexer at
`0xa904..0xabf0`. The documented sources are direct host input, pending/LIFO
bytes, macro/data-chain replay, ring-buffer input, service retry paths, and
no-byte returns.

The byte fetcher does not decide PCL semantics. Its job is to return the next
normalized byte, or a no-byte/error result, to callers such as the parser
wrappers at `0xda9a`, `0xdaf0`, and `0xdb74`. The checked-in contract is
[host-byte-fetch.md](host-byte-fetch.md). That note owns the caller
classification and the macro/data-chain frame layout:

- `0x782d76`: active data-chain frame pointer.
- frame `+0x00`: payload or chunk pointer.
- frame `+0x04`: remaining byte count, or `-1` end marker.
- frame `+0x09`: observed replay/finalization class.
- frame `+0x0a`: snapshot pointer or zero.

Host-interface timing and physical MMIO naming are outside this ROM-local byte
contract. They matter only when a claim depends on the physical producer of a
status or input bit rather than the byte value already returned to firmware.

## Parser State

The parser builds six-byte command records and uses ROM dispatch tables to
route completed commands. The main parser loop and wrappers are documented in
[pcl-parser-core.md](pcl-parser-core.md) and summarized in
[pcl-command-map.md](pcl-command-map.md).

Important ROM boundaries:

- `0x11774`: main parser loop and dispatch entry.
- `0xda9a`, `0xdaf0`, `0xdb74`: byte wrappers and parser entry points.
- `0x112a4`: normal parser pointer table.
- `0x116f6`: alternate/data parser pointer table.
- `0x121cc`: saves a delayed payload handler and the current six-byte record.
- `0x12218`: restores the saved record and calls the delayed handler.

Each parser table entry is six bytes:

```text
byte_to_match, next_mode, handler_long
```

Mode-zero control rows are explicit parser rows. For example, normal rows for
`0x00`, `0x07`, and `0x0b` reset/finalize parser state without printable
fallback or page output. Alternate/data rows for `0x00` and `0x07..0x0f`
append the byte through `0xe002` before the same terminal reset path.

The parser-level distinction that matters for reproduction is whether a byte:

- becomes printable text;
- becomes a direct control command;
- extends an ESC command record;
- completes a command and calls a handler;
- schedules a delayed payload handler;
- is consumed by a direct reader loop such as display functions;
- is appended to macro/data-chain storage; or
- is ignored/reset as an explicit table row.

## Command Dispatch

[pcl-command-map.md](pcl-command-map.md) is the command-family index. It maps
parsed command forms to handler addresses and points to the detail note that
owns the semantic behavior.

The parser table does not itself define output pixels. It routes to handlers
that mutate environment state, enqueue page objects, publish pages, or schedule
payload readers. The command-family notes own those effects:

- Printable text and direct controls:
  [direct-control-codes.md](direct-control-codes.md) documents cursor
  movement, text span flushing, and compact text objects.
- `ESC E`, FF, page setup, and publication commands:
  [publication-commands.md](publication-commands.md) documents environment
  reset, page finalization, and published records.
- `ESC &p#X` transparent data:
  [transparent-print-data.md](transparent-print-data.md) documents counted
  byte splicing back into text output.
- `ESC Y ... ESC Z` display functions:
  [display-functions.md](display-functions.md) documents the direct reader
  loop to text output or append storage.
- Macro definition, execute, call, and overlay:
  [macro-data-chain.md](macro-data-chain.md) documents stored byte streams
  replayed through `0xa904`.
- Raster graphics `ESC *t`, `ESC *r`, and `ESC *b`:
  [raster-graphics.md](raster-graphics.md) documents encoded raster row
  objects.
- Rectangles and rules `ESC *c`:
  [rectangle-graphics.md](rectangle-graphics.md) documents rule/fill objects.
- Font selection and metrics:
  [font-context-metrics.md](font-context-metrics.md) documents current font
  context and glyph metrics.
- Downloaded fonts and glyphs:
  [downloaded-fonts.md](downloaded-fonts.md) documents downloaded records and
  compact/segmented glyph objects.
- Built-in resources:
  [resource-rom.md](resource-rom.md) documents built-in font/glyph data
  consumed by text renderers.
- Vertical forms control:
  [vertical-forms-control.md](vertical-forms-control.md) documents VFC table
  definition and channel jumps.

For each command family, the detail note should identify the parsed command
record, handler address, state fields read and written, downstream consumers,
visible output effect, and unresolved boundaries.

## Command Behavior To Page Objects

Command handlers feed a small set of page-object producers. That is the first
major convergence point after parser dispatch.

Current page root and stream storage are documented in
[page-record-storage.md](page-record-storage.md). Canonical fields include:

- `0x78297a`: current page/control root pointer.
- root `+0x1c`: bucket-head array for compact text, segmented glyph/text, and
  encoded raster objects.
- root `+0x20`: linked stream chunks used by object storage.
- root `+0x24`: rule/list chain.
- root `+0x28`: fixed-width or second-mode list chain.
- root `+0x2c..+0x68`: 16 current font/context slots.
- root byte `+4`: root state, initialized as current state `1` and published
  as state `2`.

The shared producers are:

- `0x10084`: ensure or allocate the current page root.
- `0x1381c`: allocate variable-size stream storage under root `+0x20`.
- `0x1387c`: allocate or reuse compact/raster bucket objects under root
  `+0x1c`.
- `0x12f2e`: queue compact text and glyph payload entries.
- `0x12714`: flush pending text spans into segment-list or fixed-width
  objects.
- `0x13070` / `0x13250`: queue encoded raster row objects.
- `0x133aa`: insert ordered rectangle/rule objects under root `+0x24`.
- `0x136d2`: insert fixed-width or landscape span objects under root `+0x28`.

This means command behavior should usually be documented as:

```text
parsed command -> command state writes -> one of the shared page producers
```

For example, `ESC *b#W` is not a pixel writer. The parser schedules delayed
handler `0x105d0`, `0x105d0` reads payload bytes through the byte fetcher and
updates raster state, then `0x13070` / `0x13250` queues encoded-span page
objects. Pixels appear later when the render dispatcher consumes those
objects.

## Page Image Assembly

The ROM builds a page/control record as linked object structures, not as a
single full-page bitmap during parsing. The current page root owns separate
object collections:

- bucket array `+0x1c` for compact text/glyph objects, segmented glyph/text
  objects, and encoded raster objects;
- rule/list chain `+0x24` for rectangle and fill objects;
- fixed-width chain `+0x28` for selected landscape/span-like output;
- font/context slots `+0x2c..+0x68` copied with the page so compact renderers
  can resolve glyph resources later.

`0xff1e` publishes a valid current root into the page/control pool, writes the
published state, sets `0x782996`, and clears `0x78297a`. Publication separates
parser-time object assembly from render-time consumption.

The render bridge then copies a published source into an active render work
record:

- `0x1ed84`: active page-record copy entry; seeds render header words from the
  active source record selected by the scheduler.
- `0x1edc6`: copies root `+0x1c` to render record `+0x18`, root `+0x24` to
  render `+0x1c`, root `+0x28` to render `+0x20`, and context slots
  `+0x2c..+0x68` to render `+0x24..+0x60`.

Rule and fixed-width lists are normalized by `0x1edc6` before renderer
dispatch. Compact bucket roots and context slots are mostly pass-through.
The bridge contract is documented in
[page-record-storage.md](page-record-storage.md) and
`generated/analysis/ic30_ic13_page_record_bridge.md`.

## Render Scheduling

The active render scheduler is documented in
[active-render-scheduler.md](active-render-scheduler.md). It selects published
records, alternates render work records, derives the current band destination,
and calls the render dispatcher when enough capacity is available.

Key scheduler state:

- `0x780ea6`: published pool-head pointer.
- `0x780eaa`: scheduler cursor for the selected page/control record.
- `0x780eae`: active source record consumed by `0x1ed84`.
- `0x7820bc` / `0x7820c0`: two-work-record selector state.
- `0x7820c4` / `0x782128`: paired render work records.
- `0x783a18`: active render work-record pointer consumed by `0x1ef6a`.
- render work `+0x10`: active band word.
- `0x783a20`, `0x783a22`, `0x783a28`: derived band rows, remainder, and
  destination base computed by `0x1ef86`.

The scheduler does not define object semantics. Its output is the selected
render work record and band state passed to `0x1ef6a`. Physical engine timing
and formatter/DC signal names remain separate board-facing boundaries.

## Pixel And Object Rendering

The render entry `0x1ef6a` consumes the active render record in this order:

1. `0x1ef86`: derive current band/destination fields.
2. `0x1efc2`: dispatch bucket-chain objects from render `+0x18`.
3. `0x1f446`: render rule/list objects from render `+0x1c`.
4. `0x1f756`: render fixed-width objects from render `+0x20`.

Bucket objects are classed by object byte `+4`:

- `0x00..0x3f`: compact text/glyph rendering.
- `0x40..0x7f`: segmented list rendering.
- `0x80..0xff`: encoded raster rendering.

The detailed render contracts live in [page-raster-imaging.md](page-raster-imaging.md)
and the renderer sections of [semantic-state-model.md](semantic-state-model.md).
Command-family notes point back here when they reach their page-object
producer and forward to the renderer note that consumes the object.

Renderer-facing examples:

- Printable text and downloaded glyphs converge through `0x12f2e` bucket
  objects, context slot copies, and compact renderers under `0x1efc2`.
- Raster rows converge through `0x13070` / `0x13250` encoded-span objects and
  the `0x1f88e` renderer family.
- Rectangles/rules converge through `0x133aa`, bridge list `+0x1c`, and
  renderer `0x1f446`.
- Landscape/fixed-width span output converges through `0x136d2`, bridge list
  `+0x20`, and renderer `0x1f756`.

## State Classification

Detail notes should classify fields by role so the reproduction model does not
confuse canonical state with scratch or cached render values.

- Canonical state: page roots, command environment fields, current font
  contexts, raster state, macro/data-chain records, and published records that
  later code consumes as authoritative.
- Derived/cache state: bucket indices, render destination bases, band-derived
  words, normalized bridge fields, and temporary metrics computed from
  canonical state.
- Parser scratch: six-byte command record cursors, delayed-payload snapshots,
  loop-local ESC flags, and temporary parser append pointers.
- Firmware bookkeeping: allocation cursors, flags, wait objects, status
  latches, and scheduler progress counters that control firmware execution but
  are not PCL state by themselves.
- Hardware/external state: MMIO bits, formatter/DC signals, physical optional
  resource windows, retained-storage device behavior, and timing sources.
- Unknown: fields with observed reads/writes but no stable semantic role yet.

## Unresolved Boundaries

Unresolved items should be written as exact boundaries, not broad caveats.
Each one should state whether it is ROM-local, hardware/MMIO, missing external
resource data, or unverified physical output behavior.

Current top-level boundaries include:

- host/interface physical signal naming behind some `$8000`, `$a200`, `$a400`,
  and `$fffee00x` accesses;
- formatter/DC signal mapping for the final board-facing video/page path;
- optional cartridge/resource window contents where the ROM scans outside the
  verified IC32/IC15 resource-pair bytes;
- transparent secondary segment-57 continuation data at
  `0x0c0000..0x0c0321`;
- renderer edge cases that have exact helper boundaries in the detail notes,
  such as short compact downloaded-glyph fallback indices beyond the documented
  `0x1fe76` table range.

These are not blockers for documenting ROM-local parser, command, page-object,
or render behavior that is already visible in the disassembly.

## Documentation Rule

When adding new reverse-engineering work, update the first applicable layer in
this dataflow:

```text
input -> parser -> command -> page object -> publication -> scheduler -> pixels
```

A useful checkpoint explains what changed in that path, names the exact ROM
addresses and state fields, and links the detailed note where the evidence
lives. Fixture output or generated analysis should be cited as supporting
evidence, but the explanatory behavior belongs in checked-in notes.
