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

## Reader Path Index

Use these worked paths as entry points for the byte-stream-to-pixel model:

- Host byte source and replay priority:
  `Worked Path: Host Byte Source Priority`.
- Parser records, dispatch tables, delayed payloads, ignored rows, and
  parser artifacts:
  `Worked Path: Command Record And Payload Dispatch`,
  `Worked Path: Explicit No-Output Parser Rows`.
- Host/status side channels with no direct page-object effect:
  `Worked Path: Model-ID And Status Backchannel`,
  `Worked Path: External Ready Service Preemption`.
- Text, controls, cursor placement, and transparent/display byte readers:
  `Worked Path: Printable Glyph`,
  `Worked Path: Mixed Direct Controls`,
  `Worked Path: Cursor And Margin Placement`,
  `Worked Path: Underline Text Span`,
  `Worked Path: Transparent Print Data`,
  `Worked Path: Display Functions Direct Reader`.
- Font selection, downloaded glyphs, macro replay, and resource boundaries:
  `Worked Path: Page Font Scheduler Resource Handoff`,
  `Worked Path: Font Selection To Visible Glyphs`,
  `Worked Path: Selected Font Metrics To Span Output`,
  `Worked Path: Downloaded Glyph`,
  `Boundary: Short Compact Downloaded-Glyph High Rows`,
  `Worked Path: Macro Execute Replay`,
  `Boundary: Secondary Segment-57 Source`.
- Page publication, page environment changes, and active render scheduling:
  `Worked Path: FF Publication`,
  `Worked Path: Page Environment Publication`,
  `Worked Path: Published Record To Active Bands`,
  `Worked Path: Mixed Text/Rule/Raster Page Record`,
  `Worked Path: Render Dispatch And Pixel Composition`.
- Non-text page objects and render dispatch:
  `Worked Path: Vertical Forms Control`,
  `Worked Path: Rectangle Rule`,
  `Worked Path: Raster Row`.

Each worked path names the handlers, ROM fields, output effect, field
classification, evidence files, and unresolved boundary for that slice.

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

Payload and direct-reader modes:

- Delayed payload snapshot:
  `0x121cc` rewinds command-record cursor `0x78299e`, writes pending byte
  `0x782a1a`, stores handler pointer `0x782a1c`, and saves the active
  six-byte record at `0x782a20..0x782a25`. Terminal mode-zero reset later
  calls `0x12218`, which restores that record and calls the saved handler.
- Raster payload:
  `ESC *b#W` arms `0x105d0` through `0x11f82 -> 0x121cc`. After
  `0x12218`, `0x105d0` rereads restored record `+2` as byte count, drains or
  caps bytes through `0xdace` / `0xa904`, and queues accepted encoded-span
  objects through `0x13070` / `0x13250`.
- Transparent text payload:
  `ESC &p#X` arms `0x12452` through `0x11f5a -> 0x121cc`. After restore,
  `0x12452` reads the absolute count, fetches payload bytes directly through
  `0xa904`, applies its local `1a 58 -> 7f` rule, and routes bytes to
  printable/control text handlers.
- Vertical forms payload:
  `ESC &l#W` arms `0x12cfe` through `0x11f6e -> 0x121cc`. After restore,
  `0x12cfe` reads the count, consumes bytes through `0xdace`, writes VFC
  table `0x782dde..0x782edd`, and updates cursor-limit state consumed by
  `ESC &l#V`.
- Downloaded font and glyph payloads:
  `ESC (s#W` / `ESC )s#W` use handler `0x11f96`. Count zero schedules
  descriptor path `0x15d0a`; nonzero counts schedule resource/character
  payload path `0x16c14`. Both consume the restored record and payload budget
  `0x783140` before updating downloaded-resource records that later printable
  glyphs consume.
- Generic counted payload wrapper:
  stateful tokenizer helpers can schedule `0x1228a`; after restore it drains
  the absolute count through `0x12328` without echoing bytes. In
  alternate/data mode, `0x12358` either delegates to `0x1228a` or appends
  positive-count payload bytes through the alternate append path.
- Direct reader loops:
  display-functions handlers `0x12536` and `0x12120` do not use the delayed
  snapshot. They read bytes directly through `0xa904` until local `ESC Z`
  termination, routing normal-mode bytes to text output or alternate/data
  bytes to append storage.

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

Command output-effect classes:

- Immediate compact text output:
  unmatched printable bytes and byte readers such as transparent data
  `0x11f5a -> 0x12452` and display functions `0x12536` eventually re-enter
  printable/text queue paths `0xd04a`, `0xd0f0`, `0xd824`, and `0x12f2e`.
- Cursor and layout state for later output:
  CR/LF/HT/BS handlers `0xf02c`, `0xf08c`, `0xf1cc`, and `0xf2a8`,
  cursor/margin handlers `0xeb58`, `0xec0c`, `0xf39e`, `0xf416`, `0xf560`,
  `0xf60a`, `0xf48c`, and `0xf692`, HMI/VMI handlers `0xca8c`, `0xcb00`,
  and `0xc992`, and wrap/perforation handlers `0xedb0` and `0xee64` mutate
  state consumed by later printable text, span flushing, VFC, or raster
  placement.
- Publication/page-boundary commands:
  FF `0xf0f0`, reset `0xcc52`, page-size `0xfc74`, orientation `0x10220`,
  paper-source `0xef62`, and copy-count storage `0xeef0` converge on
  publication through `0xff1e` before render bridge `0x1ed84` / `0x1edc6`.
- Binary payload producers:
  raster transfer `0x11f82 -> 0x105d0`, VFC table load
  `0x11f6e -> 0x12cfe`, transparent data `0x11f5a -> 0x12452`, and
  downloaded-font/glyph payloads `0x11f96 -> 0x15d0a/0x16c14` use delayed
  parser restore `0x121cc -> 0x12218`, then either queue page objects or
  update state consumed by later commands.
- Font/resource state for later output:
  symbol/font-designation wrapper `0x120be`, attribute wrappers
  `0x12082`, `0x12096`, `0x12046`, `0x1206e`, `0x120aa`, and `0x1205a`,
  common refresh `0xc580`, candidate selection `0x13eb8`, symbol fallback
  `0x156de`, font-ID selection `0x17708`, and page-root context install
  `0xc428` / `0xc4fc` affect later `0xd04a` glyph resolution rather than
  drawing pixels immediately.
- Non-text page-object producers:
  rectangle/rule commands `0x10e68`, `0x10e22`, `0x10dce`, `0x10a40`,
  `0x10ae0`, and final fill `0x10898` write rule state and queue objects
  through `0x10b80`, `0x13386`, and `0x133aa`; raster commands `0x10808`,
  `0x1075a`, `0x107fa`, and delayed `0x105d0` queue encoded-span objects
  through `0x13070` / `0x13250`.
- Macro/data-chain replay:
  macro ID `0xe112`, macro control `0xdd08`, lookup `0xe0a4`, append
  `0xe002`, execute/call frame builder `0xe418`, overlay frame builder
  `0xe4f4`, and cleanup `0xe22c` create or consume stored byte streams that
  return to byte fetch `0xa904`.
- Host/status output without page objects:
  model-ID wrapper `0x12034 -> 0x122be` and host-output FIFO helpers
  `0xb0c0`, `0xb090`, and `0xae2c` write backchannel bytes rather than page
  records.
- Explicit no-page-output parser rows:
  normal mode-zero rows for `0x00`, `0x07`, and `0x0b`, alternate/data C0
  append rows, `ESC ?`, `ESC Z`, and unimplemented `ESC &lT/t` parser rows
  are documented as parser artifacts or direct-reader terminators, not missing
  imaging commands.

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

Producer-to-renderer map:

- `0x12f2e -> 0x1387c`: printable text, transparent/display bytes, and
  downloaded glyphs. These write bucket-array objects under root `+0x1c`,
  bridge to render `+0x18`, and render through compact dispatch
  `0x1efc2 -> 0x1effe`.
- `0x12714 -> 0x13520/0x135f0`: portrait flushed text spans. These write
  segment-list bucket objects under root `+0x1c`, bridge to render `+0x18`,
  and render through `0x1f812`.
- `0x12714 -> 0x136d2`: landscape flushed text spans. These write fixed-list
  objects under root `+0x28`, bridge to render `+0x20`, and render through
  `0x1f756`.
- `0x13070 -> 0x13250`: raster payload rows from `ESC *b#W`. These write
  encoded-span bucket objects under root `+0x1c`, bridge to render `+0x18`,
  and render through `0x1f88e`.
- `0x13386 -> 0x133aa`: rectangle/rule commands from `ESC *c#P`. These write
  rule-list objects under root `+0x24`, bridge to render `+0x1c`, and render
  through `0x1f446`.

The shared stream allocator means these objects can be interleaved in the same
page root. Fixture `addressed page-record writers share 0x1381c across chunk
rollover` proves compact, rule, and fixed-list writers share the same root
stream. Fixture `addressed text/rule/raster field groups reach publication and
render entry` proves compact text, selector-7 rule, and mode-0 raster objects
publish from one page record and render through the bridge. The dense raster
split path `0x132b6` may create multiple encoded-span bucket objects from one
accepted transfer, but those objects still use the same `+0x1c -> +0x18 ->
0x1f88e` consumer path.

State role split:

- Canonical page-object state:
  root fields `+0x1c`, `+0x24`, `+0x28`, context slots `+0x2c..+0x68`, and
  object headers/payloads allocated through `0x1381c`.
- Derived/cache state:
  producer keys `0x782a7a..0x782a7e`, stream allocator cursors
  `0x782a70`, `0x782a72`, and `0x782a76`, and bridge/render caches such as
  `0x783a20`, `0x783a22`, `0x783a28`, and `0x783a2c`.
- Parser scratch:
  the six-byte records and delayed-payload snapshots that led to these
  producers; they are no longer consulted after objects are queued.
- Firmware bookkeeping:
  publication flag `0x782996`, page-root state byte `+4`, no-room/retry flags,
  and scheduler progress fields.
- Unknown:
  no unresolved ROM-local producer-to-root-to-render mapping remains for the
  listed object classes. New work should start from byte streams that create a
  different object shape, root field, bridge value, continuation state, or
  rendered row.

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

## Worked Path: Host Byte Source Priority

This is the byte-source boundary before any PCL command semantics. The primary
direct stream is the mixed printable/control stream:

```text
ESC &k1G ! CR !
```

In bytes:

```text
1b 26 6b 31 47 21 0d 21
```

Source priority:

- `0xa904` first runs pending service helper `0x10cc(0x780202)` and retries
  from the top when service byte `0x7821cd` is set.
- If buffered-source byte `0x780e66` is set and gate byte `0x780e3b` is also
  set, `0xa904` returns `D7 = -1` before consuming any byte source.
- The first pushback stack then wins over all later sources. Its canonical
  fields are count word `0x783e8c` and one-past-next pointer `0x783e8e`.
- The active data-chain frame at `0x782d76` wins next. Frame `+0x00/+0x04`
  hold the payload pointer and remaining byte count, or `+0x04 = -1` for an
  end marker that makes `0xa904` call `0xe22c` and retry.
- The second pushback stack follows, using count word `0x783e76` and
  one-past-next pointer `0x783e78`.
- When selector byte `0x780e40` is zero, the ring source follows. It reads
  from pointer `0x783e56`, decrements occupancy word `0x783e54`, wraps after
  `0x783e53` back to `0x783a4c`, and returns the byte in `D7`.
- Direct hardware modes run only after the buffered sources and ring source
  have not supplied a byte. Selector `0x780e40 == 1` polls `0x8e01` and reads
  `0x8801`; other nonzero selector values poll `0xfffee005` and read
  `0xfffee001`.

Startup/reset helper `0x3178` is the empty-state producer for this path. It
clears the ring and pushback counts, initializes ring read/write pointers
`0x783e56` and `0x783e5a` to `0x783a4c`, sets LIFO pointers `0x783e78` and
`0x783e8e`, and sets low-water threshold `0x783e5e = 0x40`.

Parser handoff:

- Normal parser bytes go through `0xda9a`. It calls `0xa904`, returns
  non-ESC bytes unchanged, and only performs ESC lookahead/logging when the
  first returned byte is `0x1b`.
- `0xdaf0` and `0xdb74` build six-byte command records from bytes supplied
  by `0xda9a`; they do not choose host sources themselves.
- Payload/control reader `0xdace` is separate. It calls `0xa904`, and only
  its local `0x1a 0x58` probe maps to a normalized control result. This is
  not a global byte-source normalization.
- Display-functions, transparent-text, raster, VFC, and downloaded-font
  payload readers either call `0xa904` directly or call a payload reader that
  does. Each reader owns its own negative-return and `0x1a` pair behavior.

Direct-output stream effect:

- With the primary ring stream above, `0xa904` supplies bytes to `0xda9a`.
- Parser loop `0x11774` dispatches `ESC &k1G` to wrap-mode handler `0xedf8`.
- The following `!` reaches printable handler `0xd04a` and queues a compact
  glyph through `0x12f2e` / `0x1387c`.
- `CR` reaches control-code handler `0xf02c`, mutates text cursor state, and
  leaves no direct pixels by itself.
- The final `!` again reaches `0xd04a`, queues another compact glyph, and the
  later bridge/render path `0x1ed84` / `0x1edc6` / `0x1ef6a` renders the same
  page objects documented in the mixed-control path below.

Macro replay effect:

- Macro execute/call handlers build data-chain frames through `0xe418`.
  Overlay/page-finalization replay builds a non-replay frame through
  `0xe4f4`.
- Those frames become the active `0x782d76` source. The replay bytes do not
  enter a special parser; `0xa904` returns them before ring or direct
  hardware input, so the same `0xda9a`, `0x11774`, command handlers, page
  object producers, and renderers consume them.
- Fixture `macro execute frame payload feeds 0xa904 data-chain bytes` proves
  the source handoff. Fixtures `macro execute data-chain parser trace feeds
  page-record stream` and `macro mixed-control data-chain parser trace feeds
  page-record stream` prove the replayed bytes reach the same parser and page
  record consumers as live ring bytes.

State classification:

- Canonical input state: first pushback stack `0x783e8c` / `0x783e8e`,
  active data-chain pointer `0x782d76` and frame `+0x00`, `+0x04`, `+0x08`,
  `+0x09`, `+0x0a`, second pushback stack `0x783e76` / `0x783e78`, ring
  occupancy/read/write fields `0x783e54`, `0x783e56`, `0x783e5a`, and direct
  selector byte `0x780e40`.
- Derived/cache state: ring free capacity derived by `0xa6f4` from
  `0x783e54`, low-water threshold `0x783e5e`, and status-sequence cursor
  `0x783e62`.
- Parser scratch: none is owned by `0xa904`. Scratch starts once a byte
  reaches `0xda9a`, parser loop `0x11774`, delayed payload restore `0x12218`,
  or a direct payload reader.
- Firmware bookkeeping: service bytes `0x7821cd` and `0x7821cc`, buffered
  source/gate bytes `0x780e66` and `0x780e3b`, direct-mode handshake shadows
  `0x7821c4`, `0x7828ec`, `0x7828fa`, `0x7828fb`, and status accumulator
  `0x780e2e`.
- Unknown or external state: the board-level names for direct hardware
  registers `0x8e01`, `0x8801`, `0x8c01`, `0xa601`, `0xaa01`,
  `0xfffee001`, `0xfffee005`, and `0xfffee009`, and any data-chain frame
  class outside observed `+0x09` values `2`, `3`, and `4`.

Writers, readers, and evidence:

- `0xa904` consumes all byte sources and updates source counts, pointers,
  pending bits, retry state, and data-chain end state.
- `0x9ec0` writes the two pushback stacks consumed by `0xa904`.
- `0xa6cc` and `0xa846` write the ring source consumed by `0xa904`.
- `0xe418`, `0xe4f4`, `0x9f6a`, and `0xe22c` own data-chain frame
  production, byte consumption, and frame-end cleanup.
- `0xda9a`, `0xdaf0`, `0xdb74`, `0xdace`, `0x11774`, payload readers, and
  macro replay are the observed byte-source consumers.
- The low-level contract is documented in
  [host-byte-fetch.md](host-byte-fetch.md), [pcl-parser-core.md](pcl-parser-core.md),
  and [macro-data-chain.md](macro-data-chain.md). Disassembly evidence is
  `generated/disasm/ic30_ic13_host_byte_fetch_00a904.lst`,
  `generated/disasm/ic30_ic13_startup_byte_source_init_003178.lst`,
  `generated/disasm/ic30_ic13_pcl_escape_parser_00da9a.lst`,
  `generated/disasm/ic30_ic13_main_parser_loop_011774.lst`,
  `generated/disasm/ic30_ic13_macro_record_chain_helpers_00dfba.lst`,
  and
  `generated/disasm/ic30_ic13_macro_environment_snapshot_helpers_00e65c.lst`.

Reproduction contract:

- Preserve the `0xa904` source priority exactly: no-byte gate, first pushback,
  active data-chain frame, second pushback, ring, then direct hardware.
- Preserve service retry as invisible to parser callers except for the
  immediate `D7 = -1` gate branch.
- Preserve data-chain replay as a byte-source override before live input.
- Preserve local payload-reader normalization. Do not rewrite `0x1a 0x58`
  globally before dispatch.
- Treat direct hardware register naming as external unless emulating the live
  board interface. For byte-stream rendering, the ring and data-chain sources
  are sufficient software-visible producers.

## Worked Path: Command Record And Payload Dispatch

This path covers the shared parser handoff from source bytes to six-byte
command records and delayed binary payload consumption. The primary stream is
the raster transfer prefix:

```text
ESC *b4W 00 ff 00 ff
```

In bytes:

```text
1b 2a 62 34 57 00 ff 00 ff
```

Parser source and command records:

- `0xda9a` supplies ESC-aware parser bytes from `0xa904`.
- Parser loop `0x11774` scans six-byte dispatch-table rows from the normal
  pointer table at `0x112a4` while parser mode byte `0x782999` is zero.
- `ESC` selects setup handler `0x11eb6`, which writes callback pointer
  `0x11ba6` to `0x78299a` and advances parser mode for the following bytes.
- The `*b` family reaches the stateful helper path that tokenizes through
  `0xdaf0` and `0xdb74`.
- `0xdb74` fills one six-byte command record at cursor `0x78299e`:

```text
+0 flags
+1 final byte
+2 signed integer parameter
+4 signed fractional parameter
```

- For `ESC *b4W`, the restored transfer record is
  `80 57 00 04 00 00`: numeric-present flag `0x80`, final byte `W`,
  integer count `4`, and fractional value `0`.

Delayed payload scheduling:

- The `W` final dispatches to handler `0x11f82`, which schedules raster
  transfer handler `0x105d0` through shared scheduler `0x121cc`.
- `0x121cc` rewinds command-record cursor `0x78299e` by six, sets pending
  flag `0x782a1a = 1`, stores handler pointer `0x105d0` at `0x782a1c`, and
  snapshots the six-byte record at `0x782a20..0x782a25`.
- Payload bytes are not consumed by the table row that sees `W`. The parser
  must return to a terminal mode-zero boundary.
- `0x12218` is called by the terminal parser reset path. It clears pending
  flag `0x782a1a`, copies saved bytes `0x782a20..0x782a25` back to the active
  `0x78299e` cursor, advances the cursor by six, calls saved handler
  `0x105d0`, and clears handler pointer `0x782a1c`.
- Handler `0x105d0` then consumes the following four bytes as payload. The
  same scheduler fields are used by transparent text, vertical forms control,
  downloaded-font payloads, and generic counted payload wrapper `0x1228a`.

Alternate/data-mode contrast:

- Alternate/data mode is selected by byte `0x782c18`.
- The alternate pointer table at `0x116f6` keeps enough syntax to collect
  command records and stop macro definitions, but many normal side effects
  are suppressed.
- `0x12218` still restores delayed state in alternate/data mode. When the
  saved handler reaches alternate payload wrapper `0x12358`, positive counts
  are consumed through `0xdace` and appended through `0xe002` instead of
  producing immediate page objects.
- The direct counted wrapper `0x1228a` drains absolute byte counts through
  `0x12328` / `0xdace` without echoing bytes through alternate append.

State classification:

- Canonical parser state: parser mode byte `0x782999`, command-record cursor
  `0x78299e`, six-byte command records, and alternate/data flag `0x782c18`.
- Parser scratch: command-byte cursor `0x782a26`, command scratch bytes
  `0x782a2a..`, numeric cursor `0x782a3e`, numeric scratch bytes
  `0x782a42..`, and local matched-byte buffer `0x783196..0x783199`.
- Firmware bookkeeping: active helper pointer `0x78299a`, delayed pending
  flag `0x782a1a`, delayed handler pointer `0x782a1c`, saved command record
  `0x782a20..0x782a25`, and alternate echo latch `0x782a56`.
- Derived/cache records: synthetic font-designation records written by
  `0x11efe` and `0x11f26`, and cursor rewind decisions made by `0xdaf0`,
  `0x11f4c`, and delayed scheduler `0x121cc`.
- Unknown: none for record layout, delayed snapshot, or restore dispatch.
  Remaining unknowns after this edge belong to command-family handlers or
  payload-specific object formats.

Writers and readers:

- `0xdb74` writes record flags, final byte, signed integer word, signed
  fractional word, and tokenizer scratch.
- `0xdaf0` combines records within one ESC command family and rewinds
  `0x78299e` when lookahead still belongs to the family.
- `0x11774` writes parser mode transitions and calls `0x12218` at terminal
  mode-zero reset boundaries.
- `0x11ba6`, `0x11c6c`, `0x11d0c`, and `0x11dd2` are the stateful helpers
  that tokenize multi-record command families and arm delayed payload calls.
- `0x121cc` writes delayed-payload bookkeeping; `0x12218` restores it and
  dispatches the saved handler.
- Raster transfer `0x105d0`, transparent text `0x12452`, VFC table loader
  `0x12cfe`, font descriptor/download handlers `0x15d0a` and `0x16c14`, and
  generic wrapper `0x1228a` consume this restored-record contract.

Output effect:

- The parser-record boundary does not draw pixels. Its output effect is that
  later command-family handlers receive the same active six-byte record the
  ROM parsed before any payload bytes were read.
- In the raster example, restored record `80 57 00 04 00 00` tells
  `0x105d0` to consume four payload bytes and queue raster row objects through
  the raster path documented below.
- In transparent text, the same delayed mechanism restores the byte count
  before `0x12452` routes payload bytes into text and fixed-space output.
- In downloaded fonts, the restored record selects descriptor or character
  payload handling before later printable bytes can resolve to downloaded
  glyph objects.

Evidence and reproduction contract:

- Detail note: [pcl-parser-core.md](pcl-parser-core.md), especially
  `Parser Record Semantic Checkpoint`.
- Command index: [pcl-command-map.md](pcl-command-map.md), including
  `ESC *b#W`, `ESC &p#X`, `ESC &l#W`, and `ESC (s#W` / `ESC )s#W`.
- Disassembly evidence:
  `generated/disasm/ic30_ic13_pcl_escape_parser_00da9a.lst`,
  `generated/disasm/ic30_ic13_main_parser_loop_011774.lst`,
  `generated/disasm/ic30_ic13_tokenizer_stateful_helpers_011ba6.lst`,
  `generated/disasm/ic30_ic13_payload_dispatch_011f82.lst`,
  and `generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst`.
- Fixture evidence includes
  `0xdaf0 tokenizes lowercase-final numeric chain into two six-byte records`,
  `0xdb74 parses sign, capped fraction digits, and final byte`,
  `0x121cc snapshots delayed payload handler and parsed record`,
  `0x12218 restores delayed parsed record and dispatches saved handler`,
  `0x1228a consumes absolute delayed payload count without echo`, and
  `modeled raster command stream parses ESC *t300R / ESC *r1A / ESC *b4W
  payload boundary`.
- Preserve the cursor rewind and delayed snapshot. Do not collapse command
  final bytes and following payload bytes into one parser event.

## Worked Path: Model-ID And Status Backchannel

This path covers a parser-visible command that produces host/interface output
instead of page objects. It belongs in the dataflow model because a
bidirectional host can react to these bytes and change the later stream that
reaches `0xa904`, even though the ROM does not draw pixels for the response.

The primary response stream is:

```text
ESC *r1K 11
```

The same producer is also reached from `ESC *s#^` through parser-table handler
`0x12034`.

Parser and command behavior:

- The command bytes enter through byte fetch `0xa904`, parser wrapper
  `0xda9a`, and parser loop `0x11774`.
- The command-table row reaches wrapper `0x12034`.
- `0x12034` calls setup helper `0x11efe`, appending a synthetic six-byte
  record with byte `0x80` and word `+2 = 1`.
- The wrapper then enters `0x122be..0x12326`.
- `0x122be..0x12326` rewinds command-record cursor `0x78299e` to the
  synthetic record, fetches the following query byte through `0xda9a`, and
  tests the active record word `+2`.
- If the fetched byte is `0x11` and the active word is `1` or `-1`, the
  producer walks ROM literal `33440A\r\n` at `0x12280` and enqueues each byte
  through blocking FIFO helper `0xb090`.
- Other fetched bytes are reported through `0x9ec0` instead of entering the
  host-output FIFO.

Host-output FIFO and worker:

- Startup helper `0x31d6` initializes FIFO storage `0x783e92..0x783ed1`,
  count `0x783ed2`, read pointer `0x783ed4`, and write pointer `0x783ed8`.
- `0xb0c0` is the nonblocking enqueue primitive. It accepts one byte while
  count `0x783ed2 < 0x40`, writes through `0x783ed8`, wraps at
  `0x783ed1`, increments the count, and returns success.
- `0xb090` retries `0xb0c0` and waits through `0x10c8(0x7801e2)` while the
  FIFO is full.
- Output worker `0xae2c` sleeps only when FIFO count `0x783ed2`, pending
  status count `0x780e22`, and bridge-service byte `0x783e61` are all zero.
- In output mode `0`, worker `0xae2c` drains FIFO bytes through `0xb022` and
  writes them through retry helper `0xaf7c` to `0xfffe0003`.
- In output mode `1`, it dequeues and discards FIFO bytes.
- In other nonzero modes, it sends queued FIFO bytes through helper
  `0xafcc` / `0xa1d6` to `0xfffee003`.

Status-byte sibling:

- The same worker also emits service/status bytes through `0xaece` when
  pending status count `0x780e22` or bridge-service byte `0x783e61` is set.
- `0xaece` can emit literal service byte `0x13` when `0x783e61` is set.
- For normal status bytes, `0xaece` builds from base `0x30`: `0x780e12` or
  `0x780e90` sets bit `0`, `0x780e2a` sets bit `1`, `0x780e0a` sets bit `2`,
  and reason byte `0x783e60` is ORed into the output.
- Page-environment helper `0x2888` is an observed producer for
  `0x780e90`, cache byte `0x780e98`, and warning/status accumulator bit
  `0x780e2a.4`.

State classification:

- Canonical host-output state: FIFO count `0x783ed2`, read pointer
  `0x783ed4`, write pointer `0x783ed8`, storage `0x783e92..0x783ed1`, and
  backend selector `0x780e40`.
- Canonical response state: literal `33440A\r\n` at `0x12280..0x12288`,
  active six-byte record word `+2`, parser record cursor `0x78299e`, and
  query byte fetched through `0xda9a`.
- Derived/cache status: pending status count `0x780e22`, bridge-service byte
  `0x783e61`, service-reason byte `0x783e60`, accepted byte cache
  `0x780e62`, aggregate words `0x780e12` and `0x780e0a`, warning/status
  accumulator `0x780e2a`, page-environment status flag `0x780e90`, and cached
  media/status code `0x780e98`.
- Parser scratch: the synthetic setup record appended by `0x11efe` and the
  normal command-record cursor state used by `0x122be`.
- Firmware bookkeeping: wait object `0x7801e2`, output worker sleep state,
  and service-message fields consumed by `0x7612`, `0x8656`, and `0x8a48`.
- Hardware/external state: physical names and timing for `0xfffe0001`,
  `0xfffe0003`, `0xfffee005`, `0xfffee003`, and the host protocol name for
  query byte `0x11`.

Output effect:

- This path does not allocate page roots, page objects, published records, or
  render work records.
- It does not feed `0x1ed84`, `0x1edc6`, `0x1ef6a`, or any bitmap renderer.
- It can affect exact byte-stream reproduction only indirectly: a full FIFO
  can stall the parser-side producer in `0xb090`, and a bidirectional host can
  react to `33440A\r\n` or status bytes by sending different future input.
- A closed byte-stream renderer that ignores backchannel bytes can treat this
  path as no page-output effect while still preserving the parser/FIFO state if
  it models host protocol timing.

Evidence and unresolved boundary:

- Detail notes: [errors-and-status.md](errors-and-status.md),
  [io-interfaces.md](io-interfaces.md), and
  [host-byte-fetch.md](host-byte-fetch.md).
- Command index: [pcl-command-map.md](pcl-command-map.md) rows for
  `ESC *r#K`, `ESC *s#^`, and handler `0x12034`.
- Disassembly evidence:
  `generated/disasm/ic30_ic13_payload_dispatch_011f82.lst`,
  `generated/disasm/ic30_ic13_host_output_fifo_00b022.lst`,
  `generated/disasm/ic30_ic13_host_output_worker_00ae2c.lst`,
  `generated/disasm/ic30_ic13_interface_output_mmio_00a1b0.lst`,
  `generated/disasm/ic30_ic13_interface_status_aggregate_0036e4.lst`,
  `generated/disasm/ic30_ic13_startup_status_ring_init_0031d6.lst`, and
  `generated/analysis/ic30_ic13_strings.txt`.
- Fixture evidence includes `0xb0c0/0xb022 output FIFO wraps and preserves
  order`, `0xb090 waits on full FIFO then enqueues after drain`,
  `0xaece emits service byte and combined status byte`, `0xae2c drains FIFO
  by configured output mode`, and
  `0x2888 sets page-environment status consumed by 0xaece`.
- The unresolved edge is external naming and timing: the protocol name for
  query byte `0x11`, physical output-register mapping, and whether a
  particular host script consumes these backchannel bytes.

## Worked Path: External Ready Service Preemption

This path covers a board/service loop that can preempt normal parser work but
does not create page objects or pixels. It is the top-level placement for the
`0x2e38 -> 0xba48` external-ready/service cluster.

Entry and loop role:

- `0xba48` is entered from the external-ready/service caller cluster, not from
  a PCL command table row.
- On the entry path, `0xba48` writes `0x7822da`, clears `0x780e09`, displays
  ROM string `0xb63b` (`01 EXT READY`) through message wrapper `0x8c7a`, and
  writes `$a200 = 0xff00`.
- Helper `0xbb36` sets handshake latch `0x782302 = 1` only when the ROM enters
  the external-ready loop.
- `0xbb84` consumes `$fffee00b.7` as the loop live condition.
- While live, the loop runs the helper family `0xbbb2`, `0xbc56`, `0xbc88`,
  `0xbcfe`, `0xbd84`, `0xbdae`, `0xc092`, and `0xc0ae` for register shadows,
  text input, outbound writes, handshaking, deferred action, and status-bit
  publication.
- When the loop leaves, teardown runs through `0xc06e -> 0xc108 -> 0x19dd2 ->
  0x36e4`. The scheduler return value from `0x19dd2` is ignored; the final
  aggregate status byte is written to `0x780e08`.

Message and service behavior:

- `0xc340` seeds buffer `0x782312` from `01 EXT READY`.
- `0xbcfe` appends masked printable bytes from `$fffee011` into
  `0x782312`; carriage return terminates the buffer and displays it through
  `0x8c7a`.
- `0xc1a6` clears message/service scratch fields `0x782300`, `0x782301`,
  `0x7821aa`, and `0x7821ac`.
- `0xc1c6` dispatches service/error conditions from status fields including
  `0x780e36 & 0x18`, `0x780e2e & 0xc0`, `0x780e39.3`, `0x780e39.4`,
  `0x780e31.7`, and `0x780e31.6`.
- When retained-storage failure bit `0x780e39.3` is set, `0xc1c6` reaches
  non-returning service display `0x85c0`, which displays ROM string
  `0xb45c` (`68 SERVICE`) through wrapper `0x8c90`.
- `0x571e` is a documented upstream writer for `0x780e39.3` through
  `0x9bee(0x780e36, 0x00000008)` on retained-record commit failure paths.

State classification:

- Canonical status/output state: final aggregate byte `0x780e08`, status
  longword `0x780e36..0x780e39`, `$a200`, `$fffee00d`, and `$a801`.
- Derived/cache state: shadow byte `0x7822eb`, last sampled `$fffee00b` byte
  `0x7822ec`, low-three-bit mirror `0x7828f9`, and timestamp snapshots
  `0x78230a` / `0x78230e`.
- Parser/status scratch: message count `0x782300`, pending-message flag
  `0x782301`, message buffer `0x782312..0x782322`, last debounced `$8000.w`
  byte `0x7821aa`, and timer baseline `0x7821ac`.
- Firmware bookkeeping: handshake latch `0x782302`, service-poll latch
  `0x7822fd`, deferred-action latch `0x7822fe`, edge latch `0x7822ff`,
  sampled byte `0x7822fa`, and scratch bytes `0x7821e7..0x7821ef`.
- Hardware/external state: `$fffee00b`, `$fffee00d`, `$fffee00f`,
  `$fffee011`, `$fffee013`, `$fffee005`, `$fffee003`, `$fffee001`, `$a200`,
  and `$a801` are ROM-visible but board-level in physical identity.

Output effect:

- This cluster can stop or defer normal parsing before page objects are
  generated.
- It can alter service/status latches and operator-panel messages, and it can
  drive hardware registers.
- It does not allocate a page root, queue page objects, publish a page/control
  record, or call render entry `0x1ef6a`.
- A byte-stream renderer that starts from canonical ready state and ignores
  board service loops can skip this path. A board-level emulator must model it
  because it can block parsing, change status bytes, or enter non-returning
  service display.

Evidence and unresolved boundaries:

- Detail notes: [external-ready-service.md](external-ready-service.md),
  [errors-and-status.md](errors-and-status.md),
  [io-interfaces.md](io-interfaces.md), and
  [page-font-scheduler.md](page-font-scheduler.md).
- Disassembly evidence:
  `generated/disasm/ic30_ic13_external_ready_service_loop_00ba48.lst`,
  `generated/disasm/ic30_ic13_external_service_io_00bcd8.lst`,
  `generated/disasm/ic30_ic13_external_service_reset_00c06e.lst`,
  `generated/disasm/ic30_ic13_status_bit_helpers_009ba2.lst`, and
  `generated/analysis/ic30_ic13_strings.txt`.
- Fixture evidence includes `0xc0ae publishes external status bits through
  0x9bee`, `0xc1c6 dispatches 68 SERVICE from retained-status bit`,
  `0xc1c6 displays pending external-ready message`, and
  `0xbb0a external-ready teardown ignores scheduler return`.
- The remaining exact boundaries are external: physical identity of the
  `$fffee00*`, `$a200`, and `$a801` register family; one continuous live
  fixture for `0x571e -> 0x9bee -> 0xc1c6 -> 0x85c0`; startup
  retained-load failure to `67 SERVICE`; and a full `0xba48` loop fixture that
  drives `$fffee00b.7` through the live-condition transition.

## Worked Path: Page Font Scheduler Resource Handoff

This path covers the ROM-visible scheduler handoff at `0x19dd2..0x1a2e2`.
It is not entered by a PCL command row. It can run after host/external quiesce,
including the external-ready teardown path `0xc06e -> 0xc108 -> 0x19dd2`, and
before normal parsing or rendering resumes.

The role of the path is to reconcile optional resource-window state with the
canonical font/resource tables that later font selection and glyph rendering
consume:

```text
caller quiesce point
  -> scratch scan of optional windows
  -> canonical/scratch comparison predicates
  -> unchanged, status-return, or long-refresh branch
  -> candidate pruning, payload release, dirty marking, and canonical commit
  -> caller-specific continuation through D7
```

Entry and scan behavior:

- `0x19dd6..0x19dda` publishes the local scratch block pointer `A6-0x28` to
  `0x782894`.
- `0x19eb6..0x19f00` clears two 20-byte scratch slots, checks board-visible
  gates `$8000.14` and `$8000.15`, and calls `0x1a0f2(1)` or `0x1a0f2(2)` for
  enabled optional resource windows.
- `0x1a0f2..0x1a21e` selects the active optional window, writes scan fields
  `0x78288c`, `0x782884`, and `0x782890`, appends resource words into the
  selected scratch slot, and copies a terminal byte to `0x782898`.
- `0x1b9c0` classifies the current resource cursor. `HEAD` returns `1`;
  `FONT`, `font`, `DUMY`, `TABL`, or `tabl` at the cursor or at cursor `+8`
  return `0`; and neither match returns `-1`.
- `0x1a220..0x1a252` handles classifier return `1` by copying record byte
  `+0x0c`, advancing by record longword `+0x04`, and returning record word
  `+0x0e`.
- `0x1a254..0x1a2e2` handles classifier return `0` by skipping known
  signatures and then copying the first non-signature record byte `+0x05`,
  advancing eight bytes, and returning word `+0x06`. Classifier return `-1`
  appends a zero word and advances to the next optional-resource grid point.

Comparison and branch behavior:

- `0x1a042..0x1a0f0` compares canonical slots at `0x7828b6 + slot * 0x14`
  against the matching scratch slots.
- `0x19f08..0x19fb6` compares fresh scratch slots back against the matching
  canonical slots.
- `0x19de6..0x19df6` stores the two predicate bytes in `A6-0x29` and
  `A6-0x2a`.
- `0x19dfa..0x19e04` consumes both predicate bytes to choose unchanged versus
  changed paths.
- If `0x72a2 == 0` and the first predicate is nonzero,
  `0x19e32..0x19e46` writes `0x780e8d`, raises status mask `0x00000200`
  through `0x9bee(0x780e2e, 0x00000200)`, and returns `D7 = 0`.
- The unchanged and long-refresh paths return `D7 = 1`.

Refresh side effects:

- `0x1ba92..0x1bb9c` prunes candidate-list entries inside the affected
  optional-resource range and adjusts candidate-list counts and pointer
  windows.
- `0x178fa..0x179a8` walks the 32 current downloaded-font records at
  `0x782640..0x782776` and releases matching nonzero payload pointers through
  `0x1887a`.
- `0x19d9c..0x19dca` marks candidate entries dirty.
- `0x1a4fa..0x1a612` selects the fresh-side optional-resource scan range,
  writes `0x78288c`, `0x782890`, and `0x782888 = 0x40000`, then calls
  `0x1a616`.
- `0x1a900..0x1a9b6` calls `0x1b04c`, validates active contexts `0x782ee6`
  and `0x782ef6` through `0x1b4c0`, calls `0x179aa(0/1)` when a context is
  missing or not bit-27 marked, and copies ten longwords from scratch
  `0x782894` into canonical table `0x7828b6`.

Caller contracts:

- Known callers are `0x00447a`, `0x004760`, `0x007164`, `0x00bb16`, and
  `0x01a3c2`.
- Host-input quiesce caller `0x447a` ignores scheduler `D7` and continues
  through the quiesce tail.
- Host/menu caller `0x4760` consumes scheduler `D7`: `D7 = 0` returns
  immediately, while `D7 != 0` enters menu/default setup and polling.
- External-ready teardown `0xba48 -> 0xbb16` records scheduler side effects
  but ignores scheduler `D7` before status aggregation through `0x36e4`.
- Font-resource scan caller `0x1a2e4 -> 0x1a3c2` ignores scheduler `D7`, then
  passes `0x78219b`, `0x78219c`, and stack local `A6-0x02` to `0x1b50e`.

State classification:

- Canonical state: resource-window table `0x7828b6..0x7828dd`, status root
  `0x780e2e`, and status predicate byte `0x780e8d`.
- Derived/cache state: scratch pointer `0x782894`, scan pointer `0x782884`,
  active optional-window base `0x78288c`, active optional-window limit
  `0x782890`, terminal byte `0x782898`, and candidate-list pointers/counts
  `0x7827a8`, `0x7827ac`, `0x7827b0`, `0x7827b4`, `0x782790`,
  `0x782794`, `0x782798`, and `0x78279c`.
- Parser scratch: stack predicate bytes `A6-0x29` and `A6-0x2a`, scratch slot
  `A6-0x28..A6-0x15` for window `0x200000..0x3ffffe`, scratch slot
  `A6-0x14..A6-0x01` for window `0x400000..0x5ffffe`, and caller local
  `A6-0x02` used after `0x1a3c2`.
- Firmware bookkeeping: candidate-count snapshot `0x782780`, current
  downloaded-font records `0x782640..0x782776`, candidate pointer-list
  entries at `0x782324..`, active-font dirty bytes `0x782f2c` and
  `0x782f2d`, caller bookkeeping behind `0x447a` and `0x4760`, and return
  register `D7`.
- Hardware/external state: gate bits `$8000.14` and `$8000.15`, and the
  physical contents of optional windows `0x200000..0x3ffffe` and
  `0x400000..0x5ffffe`.
- Unknown: the board-level names for `$8000.14/.15`, the manual-facing name
  for status mask `0x00000200`, and physical optional-resource records that
  drive the classifier's non-signature `-1` boundary.

Output effect:

- This path has no direct page-record, render-record, or bitmap output.
- Its pixel risk is indirect. Optional-window changes can remove font/resource
  candidates, release downloaded-font payloads, mark candidate entries dirty,
  refresh active font slots, commit a new canonical resource-window table, or
  change a caller's continuation through `D7`.
- A byte-stream renderer with no optional cartridges can start from the
  verified built-in resource state and treat the optional windows as absent. A
  renderer that supports cartridge or external resources must preserve this
  handoff because later font selection and glyph resolution consume the
  refreshed candidate and context state.

Evidence and unresolved boundary:

- Detail note: [page-font-scheduler.md](page-font-scheduler.md).
- Related resource and font notes:
  [resource-rom.md](resource-rom.md),
  [downloaded-fonts.md](downloaded-fonts.md),
  [font-context-metrics.md](font-context-metrics.md), and
  [external-ready-service.md](external-ready-service.md).
- Disassembly evidence:
  `generated/disasm/ic30_ic13_page_scheduler_019dd2.lst`,
  `generated/disasm/ic30_ic13_font_resource_refresh_helpers_0178fa.lst`,
  `generated/disasm/ic30_ic13_font_scheduler_commit_01a4fa.lst`,
  `generated/disasm/ic30_ic13_font_candidate_window_prune_01ba92.lst`,
  `generated/disasm/ic30_ic13_font_default_update_01ba40.lst`,
  `generated/disasm/ic30_ic13_host_input_quiesce_004200.lst`,
  `generated/disasm/ic30_ic13_host_scheduler_caller_004700.lst`,
  `generated/disasm/ic30_ic13_external_ready_service_loop_00ba48.lst`,
  `generated/disasm/ic30_ic13_font_resource_scan_01a2e4.lst`, and
  `generated/disasm/ic30_ic13_status_bit_helpers_009ba2.lst`.
- Fixture evidence includes
  `0x19dd2 optional-window change composes refresh helpers`,
  `0x19dd2 modeled unchanged and status branch exits`,
  `0x447a/0x4760 consume scheduler return differently`,
  `0xbb0a external-ready teardown ignores scheduler return`, and
  `0x1a2e4 font scan ignores scheduler return`.
- The unresolved middle edge is external resource data, not the ROM-local
  scheduler chain: windows `0x200000..0x3ffffe` and `0x400000..0x5ffffe`
  need cartridge or board memory-map evidence to name physical contents and to
  exercise every classifier boundary beyond the modeled changed, unchanged,
  and status-return exits.

## Worked Path: Printable Glyph

This is the normal-byte counterpart to the raster example below. The primary
stream is one printable byte:

```text
!
```

In bytes:

```text
21
```

Parser dispatch:

- The host byte is fetched through `0xa904` and returned through the normal
  parser wrapper `0xda9a`.
- Parser loop `0x11774` is in mode zero, parser state byte `0x782999` is
  zero, and alternate/data mode `0x782c18` is clear.
- No command-dispatch table row claims byte `0x21`, so the normal printable
  fallback calls `0xd04a`.

Printable source construction:

- `0xd04a` uses scratch source object `0x782d7e` and calls
  `0x1393a(host_byte, 0x782d7e)`.
- `0x1393a` consumes the selected current-font context and character map. In
  the documented built-in `LINE_PRINTER` case, host byte `0x21` maps to glyph
  byte `0x20`, glyph-entry pointer `0x015330`, and source flag `1`.
- `0xd04a` tests source byte `+0x10`. The flagged built-in source takes the
  `0xd550` path.

Cursor and queue handoff:

- `0xd550` calls `0xd6bc` for cursor and metric arithmetic.
- The positioned queue handoff `0xd824` writes source coordinates from current
  cursor/page geometry into source words `+0x12` and `+0x14`.
- For the pinned `LINE_PRINTER` source with cursor x `10`, cursor y `21`, and
  glyph offsets x `6`, y `21`, `0xd824` writes positioned source x `16`,
  y `0`, and context slot `0`.
- `0xd824` marks the current page-root font slot live at
  `0x78297f + slot`, then calls `0x12f2e`.

Page-object creation:

- `0x12f2e` copies source byte `+0x0b` as the compact glyph byte and consumes
  positioned source fields `+0x12`, `+0x14`, and `+0x16`.
- `0x12f2e` computes the compact bucket/key fields and calls `0x1387c`.
- `0x1387c` uses page-root `+0x1c` as the compact bucket array. It reuses a
  matching object while capacity remains, or allocates a new stream object
  through the shared allocator.

The pinned positioned compact object is:

```text
00 00 00 00 00 00 00 01 20 00 01
```

Object fields:

- `+0x00`: next pointer `0`.
- `+0x04`: class/selector byte `0`, selecting short compact rendering.
- `+0x05`: context slot `0`.
- `+0x06`: entry count `1`.
- `+0x08`: first compact payload byte, glyph `0x20`.
- payload coordinate: `0x0001`, decoded by the compact renderer as the
  positioned destination for this glyph.

Publication and bridge:

- The compact object remains under the current page root until a publication
  path finalizes the root.
- `0xff1e` publishes the root when a page boundary or publication command
  requires it, and clears current root pointer `0x78297a`.
- `0x1ed84` seeds the active render record from selected source
  `0x780eae`.
- `0x1edc6` copies source root `+0x1c` to render-record `+0x18` and copies
  page-root context slots `+0x2c..+0x68` to render-record slots
  `+0x24..+0x60`.

Render scheduling and pixels:

- `0x1eba4` calls `0x1ef6a` for an active band when scheduler capacity allows
  rendering.
- `0x1ef6a` calls `0x1ef86` for band setup, then `0x1efc2` for bucket-chain
  dispatch.
- `0x1efc2` sees compact class byte `+0x04 & 0xc0 == 0` and dispatches to
  `0x1effe`.
- `0x1effe` selects short compact renderer `0x1f034`; the glyph resolver
  `0x1f354` resolves glyph `0x20` through the copied context slot.
- The row-copy helper table selects helper `0x01fa5c` for this one-byte-span
  glyph. The positioned fixture renders the first rows as:

```text
................####
....................
................####
```

State classification for this path:

- Canonical state:
  selected font context, active character map, source object `0x782d7e`,
  current page root `0x78297a`, compact bucket object, page-root context slot,
  published source record, and render-record bucket/context roots.
- Derived/cache state:
  compact bucket/key fields `0x782a7a..0x782a7e`, glyph offsets from the
  selected font record, render-band fields `0x783a20`, `0x783a22`, and
  `0x783a28`, and compact context cache `0x783a2c`.
- Parser scratch:
  parser state byte `0x782999`, alternate/data mode `0x782c18`, and the
  current unmatched byte `0x21`.
- Firmware bookkeeping:
  page-root live-font flags at `0x78297f + slot`, stream allocator fields
  `0x782a70`, `0x782a72`, and `0x782a76`, publication flag `0x782996`,
  scheduler cursors, and render-work progress words.
- Unknown:
  no unresolved ROM-local parser-to-compact-object edge remains for this
  pinned printable path. Remaining text work is byte streams that change the
  selected context, character map, source flag, compact selector class,
  bridge state, or rendered rows.

Evidence for this path is in
[font-context-metrics.md](font-context-metrics.md),
[page-record-storage.md](page-record-storage.md),
[page-raster-imaging.md](page-raster-imaging.md), and
[semantic-state-model.md](semantic-state-model.md). The key supporting reports
are `generated/analysis/ic30_ic13_printable_text_path.md`,
`generated/analysis/ic30_ic13_text_glyph_index_flow.md`,
`generated/analysis/ic30_ic13_text_cursor_span_flow.md`, and focused listing
`generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`.

## Worked Path: Font Selection To Visible Glyphs

This path covers the font-selection state that the printable path consumes.
Font commands do not draw immediately. They update primary or secondary font
request fields, select a concrete resource candidate, rebuild a host-byte to
glyph map, install the selected context into the page root, and only then let
later printable bytes create visible compact text objects.

Primary stream:

```text
ESC (s0p10h12v0s0b3T ! !
```

Secondary stream:

```text
ESC )s0p16h8v0s0b0T SO ! !
```

Parser dispatch:

- Both streams enter through host fetch `0xa904`, parser wrapper `0xda9a`,
  and parser loop `0x11774`.
- `ESC (` creates the primary setup record through `0x1201e`; `ESC )` creates
  the secondary setup record through `0x12008`.
- Parser modes advance `0 -> 1 -> 4 -> 13` for the `s...T` attribute
  sequence. Lowercase finals stay in mode `13`; uppercase final `T` returns
  to mode `0`.
- Lowercase finals dispatch to spacing `p` handler `0xc930`, pitch `h`
  handler `0xc89c`, point-size `v` handler `0xc6ec`, style `s` handler
  `0xc780`, and stroke `b` handler `0xc840`.
- Uppercase final `T` reaches wrapper `0x1205a`, which calls typeface writer
  `0xc7e0` and common refresh `0xc580`.
- In the secondary stream, SO byte `0x0e` later reaches handler `0xc6b8`,
  which selects secondary text slot `1`. SI byte `0x0f` reaches sibling
  handler `0xc68a`, which selects primary slot `0`.

Font request and candidate selection:

- The primary request decodes to spacing `0`, pitch `0x03e8`, height
  `0x04b0`, style `0`, stroke `0`, and typeface `3`.
- The writer fields are stored in the primary request block around
  `0x782eec..0x782ef2`, and refresh flags `0x782f2c` / `0x782f2d` are marked
  dirty before `0xc580`.
- `0xc580` calls refresh path `0x13eb8(0)` for the primary slot.
- The primary fixture follows
  `0x148f8 -> 0x1569c -> 0x156de -> 0x153c6 -> 0x1519a -> 0x147b2 ->
  0x14758 -> 0x14398 -> 0x144d2 -> 0x14c64`.
- Symbol filtering keeps primary slots `0x782354`, `0x782364`, and
  `0x782374`; later pitch, height, and stroke filters select slot
  `0x782354`, record `0x00004c`, and context longword `0xc008004c`.
- `0x144d2` writes primary current-font context record `0x782ee6`.
- `0x14c64` rebuilds primary map `0x782f32`.
- The secondary stream follows the same family with class selector `1`;
  symbol filtering keeps slots `0x782330`, `0x782340`, and `0x782350`, and
  nearest-pitch selection chooses slot `0x782350`, record `0x02e122`, and
  context longword `0xc00ae122`.
- `0x144d2` writes secondary current-font context record `0x782ef6`.
- `0x14c64` rebuilds secondary map `0x783032`.

Symbol and map behavior:

- Symbol-set commands share terminal handler `0x120be` and symbol-word helper
  `0x1be22`.
- Ordinary symbol-set finals store the requested word at
  `0x782ef4 + 0x10 * slot` and call `0xc580`.
- `0x156de` consumes requested, remembered, and fallback symbol words while
  filtering the active candidate list.
- `0x14c64` rebuilds the selected map from either the bit-30 resource path
  `0x14d9c` or the bit-30-clear inline/downloaded path `0x14e24` /
  `0x14eb6`, then applies symbol patcher `0x14f16` and snapshot helper
  `0x1440c`.
- Primary fixture `ESC (1234U ESC (s0p10h12v0s0b3T!!` proves a requested
  symbol miss falls back to word `0x0115` before selecting the same primary
  context and rendering the same compact rows.
- Secondary fixture `ESC )1234U ESC )s0p16h8v0s0b0T SO !!` proves a class-one
  miss can recover through remembered word `0x000e` or fallback word
  `0x000e` before selecting the same secondary context.

Page-root context install:

- `0xc428(slot)` selects `0x782ee6` for primary slot `0` and `0x782ef6` for
  secondary slot `1`.
- With an existing current page root, `0xc428` calls `0xc4fc` to find a
  matching page-root context slot by low 24 bits or the first inactive slot.
- The selected page-root slot is written to `0x78297e`.
- Printable queueing later marks the live flag `0x78297f + slot`.
- Live primary fixture `SI !!` proves seeded current-font RAM
  `0x782ee6 = 0xc008004c` installs page-root context slot `0` without first
  allocating a page root.
- Live secondary fixture `SO !!` proves seeded current-font RAM
  `0x782ef6 = 0xc00ae122` installs page-root context slot `1`.

Printable and page-object effect:

- In the primary stream, the two printable `!` bytes route through `0xd04a`
  after selection.
- `0x1393a` reads selected slot `0`, context `0xc008004c`, and map
  `0x782f32`; host byte `0x21` maps to glyph `0x00`.
- The selected built-in record supplies HMI from byte `+0x21 = 0` and
  longword `+0x24 = 0x00780000`, which converts to packed advance `30`.
- `0x12f2e` queues this compact object:

```text
00 00 00 00 00 00 00 02 00 6a 00 00 68 02
```

- The primary entries use compact coordinates `0x6a00` and `0x6802`.
- In the secondary stream, SO selects slot `1`; `0x1393a` reads context
  `0xc00ae122` and map `0x783032`, maps host byte `0x21` to glyph `0x00`,
  and uses HMI advance `18`.
- The secondary compact object prefix is:

```text
00 00 00 00 00 01 00 02 00 c9 00 00 cb 01
```

Render path:

- Publication uses the ordinary page-root path through `0xff1e`.
- `0x1ed84` selects the published page/control record into a render work
  record.
- `0x1edc6` copies page-root context slots into render-record context slots.
- The primary stream carries render-record context slot `0` as `0xc008004c`.
- The secondary stream carries render-record context slots
  `(0xc008004c, 0xc00ae122)`.
- Compact render dispatch `0x1ef6a -> 0x1efc2 -> 0x1effe` resolves glyphs
  through `0x1f354` using those copied context slots, so the selected font
  determines the actual bitmap rows.
- The primary fixture's first nonblank row is:

```text
.............###...........................###...
```

- The secondary fixture's first visible row is:

```text
.........################..################...###
```

State classification for this path:

- Canonical state:
  selected text slot `0x782f06`, primary context `0x782ee6`, secondary context
  `0x782ef6`, primary map `0x782f32`, secondary map `0x783032`, active symbol
  words `0x783144` / `0x783146`, remembered symbol words `0x782f08` /
  `0x782f0a`, page-root context slots, selected page-root slot `0x78297e`,
  compact text objects, and render-record context slots.
- Derived/cache state:
  candidate survivor lists, selected candidate slot `0x7828a8`, selected
  target `0x7828de`, snapshot records `0x783148` / `0x783152`, HMI
  `0x78315c`, compact coordinates, glyph-entry pointers, and render-band
  fields.
- Parser scratch:
  setup records from `0x1201e` / `0x12008`, mode-13 font-selection command
  records, dirty flags `0x782f2c` / `0x782f2d` while refresh is pending, and
  the following printable bytes.
- Firmware bookkeeping:
  page-root live-font flags, `0xc4fc` slot scan state, symbol-map snapshot
  provenance byte `+0x09`, selected-font flags `0x783132` / `0x783133`,
  publication flag `0x782996`, scheduler cursors, and render-work progress
  words.
- Unknown:
  no unresolved ROM-local middle edge remains for the primary and secondary
  built-in selection streams documented here. Remaining font work is limited
  to variants that choose different candidate records, map bytes, context
  flags, compact object shapes, bridge state, or physical-device output.

Evidence for this path is in
[font-context-metrics.md](font-context-metrics.md),
[built-in-resource-scan.md](built-in-resource-scan.md),
[pcl-command-map.md](pcl-command-map.md),
[page-record-storage.md](page-record-storage.md),
[page-raster-imaging.md](page-raster-imaging.md), and
[semantic-state-model.md](semantic-state-model.md). Key supporting reports are
`generated/analysis/ic30_ic13_active_symbol_set_flow.md`,
`generated/analysis/ic30_ic13_font_context_bridge.md`,
`generated/analysis/ic30_ic13_text_glyph_index_flow.md`, and focused listings
`generated/disasm/ic30_ic13_font_context_install_00c428.lst`,
`generated/disasm/ic30_ic13_font_update_common_00c580.lst`,
`generated/disasm/ic30_ic13_font_candidate_activate_01569c.lst`,
`generated/disasm/ic30_ic13_font_id_select_017708.lst`, and
`generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`.

## Worked Path: Selected Font Metrics To Span Output

This path covers the metric side of selected-font state. It starts with a
selected context or downloaded descriptor payload and ends with a visible
segment-list span. It is separate from compact glyph bitmap lookup: the same
printable byte can queue a compact glyph object through `0x12f2e` and update
span watermarks through `0xd4ac` or `0xd8fc`.

Producer and selection flow:

- Built-in, inline, and downloaded selection all converge on a current-font
  context written by `0x144d2`, map rebuild `0x14c64`, page-root slot install
  `0xc428` / `0xc4fc`, and printable source capture `0x1393a`.
- Source byte `+0x10` selects the metric consumer family. Zero enters the
  unflagged printable path `0xd140 -> 0xd3b2 -> 0xd4ac`; nonzero enters the
  flagged path `0xd550 -> 0xd824 -> 0xd8fc`.
- Downloaded descriptor validation `0x16fae..0x17016` reads the 32-entry
  descriptor table at `0x16eae`. It stages fields under `0x782862`;
  `0x1719c..0x1725c` copies the accepted fields into the allocated payload
  consumed later by printable source capture.

Metric fields:

- Unflagged consumer `0xd4ac` reads context bytes `+0x2b`, `+0x2c`, and
  `+0x2d`. They act as alternate y offset, lower y bound, and height or page
  extent contribution for pending text spans.
- Flagged consumer `0xd8fc` reads context words `+0x16`, `+0x18`, and
  `+0x1a`. They act as lower y bound, height or page extent contribution, and
  alternate y offset for offset-table/resource-style contexts.
- Parser-produced downloaded metrics use canonical descriptor fields
  `+0x16` first code or lower bound, `+0x14` range/count, and `+0x1a` signed
  flagged offset. Helper `0x17430..0x1749c` derives
  `+0x18 = +0x14 - +0x16 - 1`; helper `0x1762a..0x1763c` writes signed
  offset word `+0x1a`.
- Derived unflagged field `+0x2c` is written by `0x1757a..0x175b8` as
  `min((value + 2) >> 2, word(+0x14)) << 2`.

Span state and consumers:

- Pending span state lives in derived/cache fields `0x783184..0x78318a`.
  `0x783184` enables the span update, `0x783185` selects alternate-y
  behavior, `0x783186` / `0x783188` carry low/high x, and `0x78318a`
  carries high y.
- `0xd4ac` and `0xd8fc` both reject disabled state, before-lower y, and
  beyond-page-extent y. On accepted input, they update high-y and high-x from
  the selected metric fields and current cursor.
- When current x is below low-water `0x783186`, both consumers flush through
  `0x12714` / `0x126e2`. The flush produces segment-list bucket objects under
  page-root `+0x1c`.
- Those segment-list objects bridge through `0x1edc6` to render record
  `+0x18` and render through `0x1ef6a -> 0x1efc2 -> 0x1f812`.

State classification:

- Canonical state:
  selected context records `0x782ee6` / `0x782ef6`, page-root context slots,
  source flag byte `+0x10`, unflagged fields `+0x2b..+0x2d`, flagged fields
  `+0x16`, `+0x18`, `+0x1a`, and segment-list page objects emitted by
  `0x12714`.
- Derived/cache state:
  descriptor-derived words `+0x18` and `+0x2c`, pending span watermarks
  `0x783184..0x78318a`, selected candidate pointers `0x7828a8` /
  `0x7828de`, and render-band fields used by `0x1f812`.
- Parser scratch:
  descriptor staging base `0x782862`, validation cursor, payload budget
  `0x783140`, optional symbol staging `0x782842..0x782856`, and active
  command records while downloaded descriptors are parsed.
- Firmware bookkeeping:
  descriptor type byte `+0x0c`, allocation units `0x7827ba`, downloaded
  record/candidate management around `0x16c14`, page-root live flags, and
  publication/scheduler progress.
- Hardware/external state:
  none for this ROM-local span contract.
- Unknown:
  no unresolved middle edge remains for the documented producer formulas,
  legal selected forms, `0xd4ac` / `0xd8fc` consumer gates, or segment-list
  render handoff. Remaining work is broader selected-font cross-products or
  manual-facing names for consumed validation fields, unless a new stream
  changes copied metric fields, selected context form, span object bytes, or
  rendered rows.

Output effects:

- Fixture `unflagged printable d4ac low-watermark flush renders span` proves
  cursor y `21`, fields `+0x2b/+0x2c/+0x2d = 7/0/10`, and alternate-y state
  produce high-y `28`, flush through `0x12714`, and render segment-list rows
  `12..14`.
- Fixture `flagged printable d8fc low-watermark flush renders span` proves
  cursor y `21`, fields `+0x16/+0x18/+0x1a = 0/10/18`, and alternate-y state
  produce high-y `3`, flush through `0x12714`, and render segment-list rows
  `3..5`.
- Host-fetched `ESC )s80W` descriptor fixtures prove `0x16fae` /
  `0x1719c` can feed both legal forms: inline/unflagged contexts reach
  `0xd4ac` and resource/flagged contexts reach `0xd8fc`; swapped forms fail
  at concrete map/render boundaries rather than forming additional legal
  metric paths.
- Legal descriptor-matrix fixtures prove the ROM formulas above across lower
  bounds, page extent equality, signed-offset extremes, range endpoints,
  low-nibble rounding, byte-boundary rounding, mixed values, and tight ranges.

Evidence:

- Detail note: [font-context-metrics.md](font-context-metrics.md), especially
  `Canonical span-metric consumers`,
  `Parser-produced downloaded-font metric fields`, and the fixture-pinned
  metric effects.
- Semantic checkpoint:
  `Text Span Flush And Fixed-Width Spans` and
  `Selected-Font Metric Producer/Consumer Contract` in
  [semantic-state-model.md](semantic-state-model.md).
- Disassembly evidence:
  `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`,
  `generated/disasm/ic30_ic13_font_payload_setup_015b80.lst`,
  `generated/disasm/ic30_ic13_font_payload_readers_016874.lst`,
  `generated/disasm/ic30_ic13_font_context_install_00c428.lst`, and
  `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`.
- Fixture evidence includes
  `flagged printable d8fc low-watermark flush renders span`,
  `unflagged printable d4ac low-watermark flush renders span`,
  `d4ac and d8fc span consumer branch family controls flush output`,
  `host-fetched 0x1719c payload metrics feed d4ac span rows`,
  `host-fetched 0x1719c payload metrics feed d8fc span rows`,
  `descriptor metric fields match across inline and resource contexts`,
  `legal descriptor metric value matrix drives d4ac and d8fc consumers`,
  `legal descriptor metric boundary values drive d4ac and d8fc consumers`,
  `legal descriptor metric range endpoints drive d4ac and d8fc consumers`,
  `legal descriptor metric low-nibble rounding drives d4ac and d8fc
  consumers`, and
  `legal descriptor metric byte-boundary rounding drives d4ac and d8fc
  consumers`.

## Worked Path: Explicit No-Output Parser Rows

This path covers ignored/no-output parser behavior. The primary normal-mode
stream is three C0 bytes:

```text
NUL BEL VT
```

In bytes:

```text
00 07 0b
```

Parser dispatch:

- The bytes enter through `0xa904`, parser wrapper `0xda9a`, and parser loop
  `0x11774`.
- Normal mode-zero parser table entries for `0x00`, `0x07`, and `0x0b` have
  next mode `0` and no handler longword.
- Because these bytes match explicit table rows, they do not reach the
  unmatched mode-zero fallback at `0x118d6..0x11900`.
- They also do not reach normal control handlers. In the same table,
  adjacent C0 rows have handlers such as BS `0xf2a8`, HT `0xf1cc`, LF
  `0xf08c`, FF `0xf0f0`, CR `0xf02c`, SO `0xc6b8`, and SI `0xc68a`; the
  three covered rows deliberately have no handler.

State effect:

- The zero-handler row writes parser mode `0`.
- Because the new mode is zero, the loop enters the terminal reset/finalize
  path at `0x11912..0x119bc`.
- That path calls `0x12218`, so any pending delayed payload is restored and
  dispatched before parser scratch is reset.
- It then resets command-record cursor `0x78299e`, nonnumeric scratch cursor
  `0x782a26`, numeric scratch cursor `0x782a3e`, alternate echo latch
  `0x782a56`, and the local matched-byte buffer.

Output effect:

- No printable text handler runs.
- No direct control handler runs.
- No page root is allocated, no page object is queued, no page is published,
  and no render work is scheduled by these bytes.
- The reproduction contract is still observable: a pending delayed payload
  must be allowed to run at the terminal `0x12218` boundary before the parser
  scratch reset.

Alternate/data-mode counterpart:

- Alternate/data parser mode uses pointer table `0x116f6` instead of the
  normal table `0x112a4`.
- In alternate/data mode, mode-zero blank C0 rows `0x00` and `0x07..0x0f`
  are append-preserving terminal rows.
- Path `0x11930..0x11ab8` stores the matched byte in parser scratch, flushes
  command and numeric scratch through `0x123ae` and `0x123de`, appends the
  matched byte through macro/data sink `0xe002`, then rejoins the same
  terminal reset path.
- Therefore alternate/data `0x08`, `0x09`, `0x0a`, `0x0c`, `0x0d`,
  `0x0e`, and `0x0f` are preserved as stored bytes instead of running the
  normal-mode BS, HT, LF, FF, CR, SO, or SI handlers.

Other parser artifacts and unimplemented rows:

- `ESC ?` is handled inside parser byte wrapper `0xda9a`, not as a terminal
  imaging command. After `0xda9a` sees `ESC`, wrapper fetch `0xdaa6` checks
  the next byte. If it is `?`, wrapper fetch `0xdab2` consumes a third byte.
  Third byte `0x11` is swallowed and the wrapper restarts; any other third
  byte is reported through `0x9ec0` and the wrapper returns `ESC` to the main
  parser.
- `ESC Z` is the local terminator for `ESC Y ... ESC Z` display-functions
  readers. Normal handler `0x12536` and alternate/data handler `0x12120`
  consume the terminating bytes inside their direct `0xa904` loops. The main
  parser table row is therefore not a standalone page-output command.
- `ESC &lT/t` is intentionally unimplemented in the parser table. Uppercase
  `T` has no terminal handler longword. Lowercase `t` only reaches generic
  helper `0x11f4c`, which rewinds `0x78299e` for lowercase command-family
  chaining; it does not write page environment, page objects, or render state
  by itself.

State classification for this path:

- Canonical state:
  parser mode byte `0x782999`, command-record cursor `0x78299e`, normal versus
  alternate/data selector `0x782c18`, delayed-payload pending fields
  `0x782a1a`, `0x782a1c`, and saved record bytes `0x782a20..0x782a25`.
- Derived/cache state:
  none for page imaging. In alternate/data mode, the appended bytes become
  derived stored input for a later macro/data-chain replay path.
- Parser scratch:
  matched-byte buffer `0x783196..0x783199`, nonnumeric scratch cursor
  `0x782a26`, numeric scratch cursor `0x782a3e`, scratch buffers
  `0x782a2a..` and `0x782a42..`, and alternate echo latch `0x782a56`.
- Firmware bookkeeping:
  parser table pointers, active callback helper pointer `0x78299a`, and the
  terminal `0x12218` delayed-restore/reset boundary.
- Unknown:
  no unresolved ROM-local middle edge remains for the normal-mode
  `0x00`/`0x07`/`0x0b` no-output rows or alternate/data append-preserving C0
  rows. The `ESC ?`, `ESC Z`, and `ESC &lT/t` rows above are parser
  artifacts or unimplemented rows, not unknown page-output commands. Output
  uncertainty is not physical; the documented effect is absence of page-object
  production in normal mode.

Evidence for this path is in [pcl-parser-core.md](pcl-parser-core.md),
[pcl-command-map.md](pcl-command-map.md), and
[semantic-state-model.md](semantic-state-model.md). The generated parser table
extract `generated/analysis/ic30_ic13_parser_dispatch_tables.md` shows the
normal-mode blank rows at mode-0 table `0x010eae..0x010ef6` and the
alternate/data blank rows at mode-0 table `0x0112f4..0x01133c`. Key supporting
listings are `generated/disasm/ic30_ic13_main_parser_loop_011774.lst` and
`generated/disasm/ic30_ic13_pcl_escape_parser_00da9a.lst`. The command-map
classification for `ESC ?`, `ESC Z`, and `ESC &lT/t` is in
[pcl-command-map.md](pcl-command-map.md) and generated table extract
`generated/analysis/ic30_ic13_pcl_command_map.md`.

## Worked Path: Display Functions Direct Reader

This path covers `ESC Y ... ESC Z`, which is not parsed as ordinary bytes after
the `Y` command. The handler enters a direct reader loop over later host bytes
and stops only after a normalized `ESC Z` pair or no-byte return.

The primary stream is:

```text
ESC Y ! 05 ! ESC Z
```

Parser dispatch:

- The initial command bytes enter through `0xa904`, parser wrapper `0xda9a`,
  and parser loop `0x11774`.
- Normal parser mode 1 routes byte `Y` to handler `0x12536`.
- Alternate/data parser mode 1 routes byte `Y` to handler `0x12120`.
- After that dispatch, both handlers fetch loop bytes directly through
  `0xa904`, not through `0xda9a` and not through the normal parser table.
- The local loop tracks whether the previous routed/appended value was
  `ESC` in flag `D4`. A value `Z` terminates only when `D4 == 1`.
- Pair `1a 58` is normalized inside the reader to value `0x7f` after
  side-effect helper `0xd99a`.

Normal output behavior:

- Handler `0x12536` derives the same filter state used by transparent print
  data: selected slot `0x782f06`, selected context byte
  `0x782eea + 0x10 * slot`, fallback high-control byte `0x782efa`, and local
  high-control filter word at `A6-2`.
- Values `0x00..0x1f` route through fixed-space handler `0xd0f0` only when
  the selected context byte is zero.
- Values `0x80..0x9f` route through `0xd0f0` only when the local filter word
  is zero.
- All other values route through printable handler `0xd04a`.
- If the routed value is CR `0x0d`, `0x12536` calls post-handler `0xf054`
  after the text/control route.

For the primary stream, `0x12536` consumes values `21 05 21 1b 5a` and routes
them as:

```text
d04a d0f0 d04a d0f0 d04a
```

The terminating `ESC Z` bytes participate as routed values before the loop
exits. The visible entries are `!`, `!`, and `Z`, queued at compact
coordinates `0x0001`, `0x0403`, and `0x0405`. The fixed-space routes advance
cursor state without producing compact glyph entries in the pinned built-in
source path.

Page-object and render path:

- Routed printable values use the same `0xd04a -> 0xd824 -> 0x12f2e`
  compact text path as ordinary printable bytes.
- `0x12f2e` queues compact text entries under current page-root bucket array
  `+0x1c` through shared bucket producer `0x1387c`.
- A later publication path calls `0xff1e`, then `0x1ed84` and `0x1edc6` copy
  the bucket and context roots into an active render work record.
- `0x1ef6a` dispatches the compact object through `0x1efc2`, `0x1effe`,
  glyph resolver `0x1f354`, and the compact row-copy helpers.

Alternate/data behavior:

- Handler `0x12120` writes literal prefix `ESC Y` through macro/data append
  sink `0xe002`.
- It then appends each normalized loop value through `0xe002` until the same
  `ESC Z` termination or no-byte return.
- The fixture-backed append stream `21 1a 58 1b 5a` is stored as:

```text
1b 59 21 7f 1b 5a
```

- This alternate/data path has no immediate pixels. Its output is stored input
  for later macro/data-chain replay.

Filter-on variant:

- With selected-context byte `1` and high-control filter `1`, stream
  `ESC Y 05 80 1a 58 ! ESC Z` normalizes `1a 58` to `0x7f`.
- Values `05 80 7f 21 1b 5a` all route through `0xd04a` and queue six compact
  entries, proving that display-functions bytes in control-looking ranges can
  become visible glyphs when the filters are nonzero.

State classification for this path:

- Canonical state:
  direct-reader termination flag `D4`, normalized loop value `D5`, selected
  text/context slot `0x782f06`, current page root `0x78297a`, compact text
  objects, macro/data append stream for alternate mode, published source
  record, and render-record bucket/context roots.
- Derived/cache state:
  selected context byte `0x782eea + 0x10 * slot`, fallback filter byte
  `0x782efa`, local high-control filter word, compact coordinates, glyph
  mapping results, and render-band fields.
- Parser scratch:
  initial `ESC Y` parser mode and table dispatch state, plus any parser state
  resumed after the direct reader returns.
- Firmware bookkeeping:
  `0xd99a` local control-report side effect, `0xf054` CR post-handler,
  append sink `0xe002`, stream allocator fields, publication flag
  `0x782996`, scheduler cursors, and render-work progress words.
- Unknown:
  no unresolved ROM-local middle edge remains for the normal `0x12536` direct
  reader loop, its default-filter and filter-on route predicates, or the
  alternate/data `0x12120` append loop. External status-consumer naming for
  neighboring `ESC z` remains outside this visible-output path.

Evidence for this path is in
[display-functions.md](display-functions.md),
[pcl-parser-core.md](pcl-parser-core.md),
[transparent-print-data.md](transparent-print-data.md),
[page-record-storage.md](page-record-storage.md),
[page-raster-imaging.md](page-raster-imaging.md), and
[semantic-state-model.md](semantic-state-model.md). Key supporting listings
are `generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst`,
`generated/disasm/ic30_ic13_control_z_handlers_0120d2.lst`, and
`generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`.

## Worked Path: Mixed Direct Controls

This path covers a mixed text/control stream where an `ESC &k#G`
line-termination command changes how a later direct CR byte mutates cursor
state before the next printable glyph. It connects normal parser dispatch,
direct-control state, compact page records, and rendered glyph rows.

The primary stream is:

```text
ESC &k1G ! CR !
```

In bytes:

```text
1b 26 6b 31 47 21 0d 21
```

Parser dispatch:

- The command bytes enter through host fetch `0xa904`, parser wrapper
  `0xda9a`, and parser loop `0x11774`.
- `ESC &k1G` dispatches to handler `0xedf8`.
- `0xedf8` rewinds the six-byte command record at `0x78299e`, normalizes
  selector `1`, and writes line-termination byte `0x80` to `0x78318f`.
- The first printable byte `0x21` falls through the normal printable route
  at `0xd04a`.
- Direct CR byte `0x0d` is a normal mode-zero table entry whose handler is
  `0xf02c`.
- `0xf02c` calls CR helper `0xf06e`, which copies left/default margin
  `0x782dd6` into horizontal cursor `0x782c8a`.
- `0xf02c` then calls span flush helper `0xf34a`; that preserves any
  pending text span before the cursor state changes.
- Because `0x78318f` bit 7 is set, `0xf02c` calls LF helper `0xf0b2`.
  That advances vertical cursor `0x782c8e` by VMI `0x783160`.
- The second printable byte `0x21` again reaches `0xd04a`, now using the
  post-CR and post-LF cursor position.

Command behavior and page objects:

- Both printable bytes use the compact text path documented in
  `Worked Path: Printable Glyph`: `0xd04a -> 0xd824 -> 0x12f2e`, with
  shared compact bucket storage through `0x1387c`.
- The first glyph proves that ordinary printable routing remains active
  after the `ESC &k1G` command.
- The direct CR byte itself produces no compact glyph object. Its page-visible
  effect is the cursor mutation consumed by the later printable byte.
- Fixture `mixed printable/control parser trace feeds page-record queue`
  pins the handler sequence `0xedf8`, `0xd04a`, `0xf02c`, `0xd04a`.
- Fixture `mixed printable/control page-record stream queues through
  0x1387c` pins a single page-record root and compact bucket reuse.
- The second glyph queues at compact coord `0x3b00`, proving that the
  `0xf02c` CR handler applied the stored CR+LF mode before the later
  `0xd04a` placement.

Render path:

- Publication uses the same page-root publication path described in
  `Worked Path: FF Publication`: `0xff1e` selects the queued page objects
  for rendering.
- Render setup `0x1ed84` and bridge `0x1edc6` copy the compact bucket and
  context roots into the active render work record.
- Render dispatch `0x1ef6a` reaches compact text renderer `0x1efc2` and
  the glyph-row copy helpers through the normal compact text branch.
- Fixture `mixed printable/control page-record bridge renders post-CR glyph
  rows` pins the bridged rows for the second glyph, so the documented state
  mutation is visible as shifted output rows rather than only as RAM state.

Related direct-control variants:

- `ESC &k2G!\n!` writes mode byte `0x60`; LF handler `0xf08c` tests bit 6
  and applies CR+LF before the second glyph, also queueing it at compact
  coord `0x3b00`.
- `ESC &k2G!\f` routes FF through `0xf0f0`; mode `0x60` makes FF perform
  a CR-style horizontal reset and page-eject work.
- `ESC &k0G HT BS !` routes `0xedf8`, `0xf1cc`, `0xf2a8`, and `0xd04a`.
  HT advances horizontal cursor to `21`, BS backs it to `20`, and the glyph
  queues at compact coord `0x0a01` / pixel x `26`.
- `ESC &k6H!!` routes HMI handler `0xca8c`; packed HMI value `15` moves the
  second glyph to compact coord `0x0501` without changing downstream compact
  text storage or render dispatch.

State classification for this path:

- Canonical state:
  line-termination mode `0x78318f`, horizontal cursor `0x782c8a`, vertical
  cursor `0x782c8e`, left/default margin `0x782dd6`, VMI `0x783160`, current
  page root `0x78297a`, compact bucket object, published source record, and
  render-record bucket/context roots.
- Derived/cache state:
  compact text coordinates, including pinned second-glyph coord `0x3b00`,
  glyph metrics used by `0xd04a`, and render-band fields produced after
  bridge setup.
- Parser scratch:
  parser mode byte `0x782999`, command-record cursor `0x78299e`, six-byte
  `ESC &k1G` record contents, normal direct-control byte `0x0d`, and the
  parser state resumed for the second printable byte.
- Firmware bookkeeping:
  page-root allocation state, compact bucket allocation cursors, span-flush
  bookkeeping in `0xf34a`, publication flag `0x782996`, scheduler cursors,
  and render-work progress words.
- Unknown:
  no unresolved ROM-local middle edge remains for the documented
  `ESC &k1G!\r!` parser-to-render path. Remaining uncertainty is outside this
  stream: broader direct-control variants, hardware output timing, and
  physical print-engine effects.

Evidence for this path is in
[direct-control-codes.md](direct-control-codes.md),
[pcl-command-map.md](pcl-command-map.md),
[font-context-metrics.md](font-context-metrics.md),
[page-record-storage.md](page-record-storage.md),
[page-raster-imaging.md](page-raster-imaging.md), and
[semantic-state-model.md](semantic-state-model.md). Key supporting listings
are `generated/disasm/ic30_ic13_control_code_handlers_00f02c.lst`,
`generated/disasm/ic30_ic13_hmi_vmi_handlers_00ca8c.lst`, and
`generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`.

## Worked Path: Cursor And Margin Placement

This path covers `ESC &a` margin and cursor-position commands. These commands
do not draw by themselves in the covered streams. They write canonical
placement state, and the next printable byte consumes that state to produce a
compact text object and visible glyph rows.

Representative streams:

```text
ESC &a6l9M !
ESC &a2c+1R !
ESC *p30x30Y !
```

Parser dispatch:

- All streams enter through host fetch `0xa904`, parser wrapper `0xda9a`,
  and parser loop `0x11774`.
- `ESC &a#L` dispatches to left-margin handler `0xeb58`.
- Lowercase final `l` keeps parser mode `12` active, so the chained
  parameter and final `M` dispatch to right-margin handler `0xec0c`.
- `ESC &a#C` dispatches to horizontal column handler `0xf39e`.
- Lowercase final `c` keeps parser mode `12` active, so relative row command
  `+1R` dispatches to vertical row handler `0xf560`.
- `ESC &a#H` dispatches to horizontal decipoint handler `0xf416`.
- `ESC &a#V` dispatches to vertical decipoint handler `0xf60a`.
- `ESC *p#X` and `ESC *p#Y` dispatch to dot-position handlers `0xf48c` and
  `0xf692`.
- The following printable byte `0x21` reaches `0xd04a` after those state
  writes and becomes the visible consumer.

Margin command behavior:

- `0xeb58` converts the absolute column count through current HMI
  `0x78315c`, rejects values beyond `0x782dda - HMI`, and writes accepted
  values to left margin `0x782dd6`.
- If the accepted left margin is right of current horizontal cursor
  `0x782c8a`, or pending text is marked, `0xeb58` also moves `0x782c8a` and
  can flush pending spans through `0xf34a`, `0x12714`, and `0x126e2`.
- `0xec0c` converts `abs(parameter) + 1` columns through HMI, rejects values
  before `0x782dd6 + HMI`, clamps beyond page width `0x782db8`, writes right
  margin `0x782dda`, and can move `0x782c8a` left.
- `0xec0c` also sets right-limit latch `0x782a57`.

Cursor command behavior:

- `0xf39e` converts column units through HMI `0x78315c`.
- `0xf416` converts horizontal decipoints using five packed subunits per
  decipoint.
- Both horizontal handlers commit through helper `0xf4ca`, which applies the
  parsed relative flag, clamps between zero and page width `0x782db8`, updates
  right-limit state against `0x782dda`, clears pending text, and refreshes
  active span state.
- `0xf560` converts row units through VMI `0x783160`. Absolute row moves add
  top offset `0x782dce` and the ROM's fractional row bias before conversion.
- `0xf60a` converts vertical decipoints using five packed subunits per
  decipoint.
- Both vertical handlers commit through helper `0xf6e2`, which ensures a page
  root, clears or flushes pending text state, applies the parsed relative flag
  or top-offset base, clamps against vertical bounds, and writes vertical
  cursor `0x782c8e`.
- Dot-position handlers `0xf48c` and `0xf692` shift the parsed whole-dot
  value into the packed coordinate domain, then commit through `0xf4ca` or
  `0xf6e2`.

Command behavior to page objects:

- The placement commands themselves create no compact glyph object in the
  covered streams.
- The following printable byte consumes `0x782c8a`, `0x782c8e`, HMI
  `0x78315c`, and font context in `0xd04a`.
- `0xd04a -> 0xd824 -> 0x12f2e` creates the compact text source object.
- `0x1387c` stores that compact object in the bucket chosen from the current
  cursor-derived coordinate.
- `ESC &a1L!`, `ESC &a1M!`, and `ESC &a6l9M!` route margin handlers
  `0xeb58` / `0xec0c` into following `0xd04a` output at compact coords
  `0x0801`, `0x0a02`, and `0x0207`.
- `ESC &a2C!`, `ESC &a72H!`, `ESC &a1R!`, `ESC &a72V!`, and
  `ESC &a2c+1R!` route cursor handlers to compact coords `0x0a02`,
  `0x0402`, `0x1001`, `0x9001`, and `0x1a02`.
- `ESC *p30x30Y!` routes dot-position handlers `0xf48c` and `0xf692` to
  following printable output at compact coord `0x9402`.

Span-flush sibling behavior:

- `ESC &a6L!` proves a margin command can also publish pending span state
  before moving the cursor. `0xeb58` moves `0x782c8a` from packed `10` to
  packed `108`, and its `0xf34a` path materializes selector-`0x4000`
  segment-list object
  `00 00 00 00 40 00 00 01 32 00 03 00 00 10`.
- `0x126e2` re-arms span bounds to x `108`, and the following printable
  queues compact coord `0x0207`. Rendering produces span rows `3..5` beside
  the compact glyph at x `114`.
- `ESC &a1R!` proves a vertical cursor command can publish the same pending
  span object before moving y. `0xf560` flushes pending state, moves y to
  packed `95.1`, and the following printable queues compact coord `0xa001`
  in bucket `4`.

Render path:

- Publication and render scheduling are unchanged from the printable path:
  page publication reaches `0xff1e`, render setup reaches `0x1ed84`, and the
  page-record bridge reaches `0x1edc6`.
- The compact text objects created after placement commands dispatch through
  `0x1ef6a`, compact renderer `0x1efc2`, glyph resolver `0x1f354`, and the
  compact row-copy helpers.
- The span-flush siblings also bridge selector-`0x4000` segment-list objects
  from compact bucket storage and render them through the span renderer.

State classification for this path:

- Canonical state:
  horizontal cursor `0x782c8a`, vertical cursor `0x782c8e`, left margin
  `0x782dd6`, right margin `0x782dda`, page width `0x782db8`, vertical bounds
  `0x782dc6` / `0x782dca`, top offset `0x782dce`, HMI `0x78315c`, VMI
  `0x783160`, current page root `0x78297a`, compact bucket objects, and
  selector-`0x4000` span objects.
- Derived/cache state:
  compact coordinates such as `0x0207`, `0x1a02`, `0x9402`, and `0xa001`,
  packed unit conversions, right-limit comparisons, bucket keys, and
  render-band fields.
- Parser scratch:
  parser mode `12` for lowercase-final command chaining, six-byte command
  records at `0x78299e`, parsed relative-flag bit 0, numeric parameter
  buffers, and the resumed parser state for the following printable byte.
- Firmware bookkeeping:
  right-limit latch `0x782a57`, pending-width latch `0x782a58`, pending-text
  latch `0x782a6d`, span-flush enable `0x783184`, span re-arm fields
  `0x783186` / `0x783188`, allocation cursors, publication flag `0x782996`,
  and render-work progress words.
- Unknown:
  no unresolved ROM-local middle edge remains for the listed
  margin/cursor-to-printable streams. Broader variants remain open only where
  they would produce different compact object bytes, bucket selection, span
  object shape, or final physical device behavior.

Evidence for this path is in
[direct-control-codes.md](direct-control-codes.md),
[pcl-command-map.md](pcl-command-map.md),
[page-record-storage.md](page-record-storage.md),
[page-raster-imaging.md](page-raster-imaging.md),
[font-context-metrics.md](font-context-metrics.md), and
[semantic-state-model.md](semantic-state-model.md). Key supporting listings
are `generated/disasm/ic30_ic13_control_code_handlers_00f02c.lst`,
`generated/disasm/ic30_ic13_dot_position_handlers_00f48c.lst`,
`generated/disasm/ic30_ic13_hmi_vmi_handlers_00ca8c.lst`, and
`generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`.

## Worked Path: Underline Text Span

This path covers text-span output driven by underline/text-attribute state.
The printable glyph still queues through the compact text path, but the
attribute also makes the font metric consumer maintain pending span bounds.
The later underline terminal command flushes those bounds into a
selector-`0x4000` segment-list object that renders separate mask rows.

Primary stream:

```text
ESC &d3D ! ESC &d@
```

Parser dispatch:

- The command bytes enter through host fetch `0xa904`, parser wrapper
  `0xda9a`, and parser loop `0x11774`.
- `ESC &d3D` dispatches to underline/text-attribute tokenizer `0x12622`.
- `0x12622` writes selector byte `0x783185 = 1` for the covered `3D`
  selector path.
- Printable byte `0x21` then routes through `0xd04a`.
- Final `ESC &d@` dispatches to `0x12622` again, takes the terminal flush
  path, and calls `0x12714` before `0x126e2` re-arms span state.

Printable span update:

- `0xd04a` calls `0x1393a` to build source object `0x782d7e` from the
  selected font context.
- In the covered flagged built-in path, the printable byte takes
  `0xd550 -> 0xd824`.
- `0xd824` queues the compact glyph through `0x12f2e` and marks the selected
  page-root font slot live at `0x78297f + slot`.
- After queueing, `0xd824` calls span consumer `0xd8fc` when span updates are
  enabled.
- `0xd8fc` reads selected context fields `+0x16`, `+0x18`, and `+0x1a`.
  Because `0x783185` is set, it uses alternate offset word `+0x1a` to update
  the high-y span bound.
- The span state now lives in pending fields `0x783184`, `0x783186`,
  `0x783188`, and `0x78318a`; it is not yet a page object.

Page-object creation:

- Final `ESC &d@` reaches `0x12622` and flushes the pending span.
- `0x12714` builds a local span source from pending span bounds and calls the
  shared display-list producer path `0x13520`.
- Portrait span insertion reaches `0x135f0`, which stores a segment-list
  object under the page-root compact bucket array.
- The object flushed by the covered underline stream is:

```text
00 00 00 00 40 00 00 01 3a 00 03 00 00 12
```

Object fields:

- `+0x04`: class byte `0x40`, selecting segment-list rendering.
- `+0x06`: one segment-list entry.
- Entry key `0x3a00`: packed bucket/key for the span.
- Entry y `3`.
- Entry width/extent `18`.

Render path:

- The compact glyph and segment-list span remain under the current page root
  until publication.
- `0xff1e` publishes the root and `0x1ed84` selects the published
  page/control record into a render work record.
- `0x1edc6` copies the compact bucket array to render-record `+0x18` and
  context slots to render-record `+0x24..+0x60`.
- `0x1ef6a` calls `0x1ef86`, bucket dispatcher `0x1efc2`, rule/list renderer
  `0x1f446`, and fixed-list renderer `0x1f756`.
- `0x1efc2` dispatches the segment-list object by `+0x04 & 0xc0 == 0x40` to
  `0x1f812`.
- `0x1f812` consumes the six-byte entry and calls `0x1f862`, which writes
  counted mask spans using full words plus a trailing mask from table
  `0x308f2`.

Related producer variants:

- `ESC &k1G!\r` proves CR handler `0xf02c` can materialize pending span state
  through `0xf34a -> 0x12714 -> 0x126e2` before cursor reset/line advance.
- `ESC &a6L!` proves left-margin handler `0xeb58` can flush the same portrait
  segment-list object before moving horizontal cursor to packed `108`.
- `ESC &a1R!` proves vertical cursor handler `0xf560` can flush the span
  before moving y to packed `95.1`, leaving the span in bucket `0` and the
  following compact glyph in bucket `4`.
- Synthetic and parser-produced metric fixtures in
  [font-context-metrics.md](font-context-metrics.md) prove both `0xd4ac`
  unflagged and `0xd8fc` flagged span consumers can emit or suppress span
  objects according to selected font metric fields.

State classification for this path:

- Canonical state:
  underline/text-attribute selector `0x783185`, pending span enable
  `0x783184`, span bounds `0x783186` / `0x783188` / `0x78318a`, selected
  font context, current page root `0x78297a`, compact glyph object, and
  selector-`0x4000` segment-list span object.
- Derived/cache state:
  packed segment-list key `0x3a00`, compact text coordinate, selected context
  metric fields, render-band fields, and the renderer trailing-mask lookup.
- Parser scratch:
  six-byte `ESC &d3D` and `ESC &d@` records at `0x78299e`, parser mode state,
  and the printable byte between the two commands.
- Firmware bookkeeping:
  page-root live-font flags, span re-arm work in `0x126e2`, allocation cursors
  for `0x13520` / `0x135f0`, publication flag `0x782996`, scheduler cursors,
  and render-work progress words.
- Unknown:
  no unresolved ROM-local middle edge remains for the documented underline
  span stream. Remaining span work is broader metric, orientation, and
  allocation variants that change object bytes, list selection, bridge state,
  or physical-device output.

Evidence for this path is in
[direct-control-codes.md](direct-control-codes.md),
[font-context-metrics.md](font-context-metrics.md),
[page-record-storage.md](page-record-storage.md),
[page-raster-imaging.md](page-raster-imaging.md), and
[semantic-state-model.md](semantic-state-model.md). Key supporting reports are
`generated/analysis/ic30_ic13_text_cursor_span_flow.md`,
`generated/analysis/ic30_ic13_text_glyph_index_flow.md`, and
`generated/analysis/ic30_ic13_render_dispatch_tables.md`. Key listings are
`generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst`,
`generated/disasm/ic30_ic13_text_span_flush_012714.lst`,
`generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`,
`generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`, and
`generated/disasm/ic30_ic13_bitmap_draw_core_01f3d4.lst`.

## Worked Path: Transparent Print Data

This path covers a counted payload mode. Transparent print data is not an
opaque binary skip: the payload reader consumes raw bytes and routes each
normalized value back into text or fixed-space behavior.

The primary stream is:

```text
ESC &p4X ! 05 85 !
```

In bytes:

```text
1b 26 70 34 58 21 05 85 21
```

Parser dispatch and delayed payload setup:

- The command bytes enter through `0xa904`, parser wrapper `0xda9a`, and
  parser loop `0x11774`.
- `ESC &p4X` routes through the command table to handler `0x11f5a`.
- `0x11f5a` is an arming stub. It pushes delayed handler `0x12452` and calls
  shared scheduler `0x121cc`.
- `0x121cc` rewinds command-record cursor `0x78299e` by six, stores pending
  flag `0x782a1a = 1`, stores handler longword `0x782a1c = 0x12452`, and
  saves command record `80 58 00 04 00 00` at `0x782a20..0x782a25`.
- When parser mode returns to zero, `0x12218` restores the saved record and
  calls `0x12452`.

Payload reader behavior:

- `0x12452` rewinds `0x78299e` by six and reads command-record word `+2`.
  The absolute value of that word is the transparent payload count.
- It reads selected text/context slot `0x782f06`, scales the slot through
  helper `0x332ee`, and reads context byte `0x782eea + 0x10 * slot`.
- If high-character flags `0x783132` and `0x783133` are clear, the local
  high-control filtering word comes from fallback byte `0x782efa`; otherwise
  it comes from the selected context byte.
- The payload loop fetches raw bytes through `0xa904`. A `-1` byte returns
  early. A byte `0x1a` probes one more byte: `1a 58` becomes transparent
  value `0x7f` after `0xd99a`, while `1a xx` with `xx != 58` routes `xx` and
  consumes the probe prefix.
- For the primary stream with default zero filtering, payload values
  `21 05 85 21` route as `d04a d0f0 d0f0 d04a`.

Command behavior and page objects:

- Payload byte `0x21` takes the normal printable path through `0xd04a`.
  In the pinned `LINE_PRINTER` case, it maps to glyph byte `0x20` and queues a
  compact text entry through `0xd824 -> 0x12f2e -> 0x1387c`.
- C0 payload byte `0x05` routes through fixed-space handler `0xd0f0` because
  the selected context byte is zero.
- High-control payload byte `0x85` also routes through `0xd0f0` because the
  local filtering word is zero.
- In the flagged built-in source path, `0xd0f0` substitutes host space
  `0x20`, clears source longword `+4`, enters `0xd550`, and advances cursor
  spacing without allocating a compact text object.
- The final `0x21` routes through `0xd04a` and queues the second visible
  compact text entry after the two spacing advances.

The compact object prefix for the primary stream is:

```text
00 00 00 00 00 00 00 02 20 00 01 20 06 04
```

Object fields:

- `+0x00`: next pointer `0`.
- `+0x04`: compact class byte `0`.
- `+0x05`: context slot `0`.
- `+0x06`: entry count `2`.
- payload entry 0: glyph `0x20`, compact coordinate `0x0001`.
- payload entry 1: glyph `0x20`, compact coordinate `0x0604`.

Publication, bridge, and pixels:

- The queued compact object remains under current page-root bucket array
  `+0x1c` until page publication.
- `0xff1e` publishes the page root and clears current root pointer
  `0x78297a`.
- `0x1ed84` seeds the active render record from selected source
  `0x780eae`.
- `0x1edc6` copies the bucket root to render-record `+0x18` and copies the
  selected context slot into render-record context slots.
- `0x1ef6a` calls `0x1efc2`; the compact object dispatches through
  `0x1effe`, glyph resolver `0x1f354`, and the same row-copy helpers used by
  direct printable text.
- The visible rows contain two `!` glyphs separated by spacing from the two
  default-filtered payload bytes.

Covered routing variants:

- `ESC &p2X!!` routes both payload bytes through `0xd04a` and renders the same
  rows as plain `!!`.
- `ESC &p2X 1a 41 !` uses restored count `2` but consumes three host bytes;
  the routed values are `41 21`, so the probe prefix is not visible.
- With nonzero selected-context and filtering bytes, `ESC &p4X ! 05 80 !`
  routes all four payload values through `0xd04a` and queues visible compact
  entries for both control-range bytes.
- In an unflagged fixed-record context, default-filtered C0 payload byte
  `0x05` still enters `0xd0f0`, but the substituted space can queue a compact
  glyph object instead of becoming cursor-only spacing.
- After SO selects secondary context slot `1`, `SO ESC &p3X ! 80 !` follows
  the same delayed reader and route decision but can produce segmented
  page-record objects instead of short compact objects.

State classification for this path:

- Canonical state:
  restored command record word `+2`, selected text/context slot `0x782f06`,
  text cursor `0x782c8a`, current page root `0x78297a`, compact text object,
  published source record, and render-record bucket/context roots.
- Derived/cache state:
  selected-slot context byte `0x782eea + 0x10 * 0x782f06`, fallback filtering
  byte `0x782efa`, high-character flags `0x783132` and `0x783133`, compact
  coordinates `0x0001` and `0x0604`, and render-band fields.
- Parser scratch:
  delayed-payload pending flag `0x782a1a`, delayed handler pointer
  `0x782a1c`, saved record bytes `0x782a20..0x782a25`, command-record cursor
  `0x78299e`, and the current payload count in `0x12452`.
- Firmware bookkeeping:
  local filtering word at `A6-2`, source-object scratch `0x782d7e`, stream
  allocator fields, publication flag `0x782996`, scheduler cursors, and
  render-work progress words.
- Unknown:
  no unresolved ROM-local middle edge remains for the primary mixed
  transparent-data path or the listed route-polarity variants. The remaining
  transparent edge is the secondary segmented high-control fallback-row
  physical resource-window source at firmware range `0x0c0000..0x0c0321`,
  not the `ESC &p#X` parser route, payload counter, or compact-renderer
  dispatch.

Evidence for this path is in
[transparent-print-data.md](transparent-print-data.md),
[pcl-parser-core.md](pcl-parser-core.md),
[direct-control-codes.md](direct-control-codes.md),
[font-context-metrics.md](font-context-metrics.md),
[page-record-storage.md](page-record-storage.md),
[page-raster-imaging.md](page-raster-imaging.md), and
[semantic-state-model.md](semantic-state-model.md). Key supporting listings
are `generated/disasm/ic30_ic13_transparent_data_handler_011f5a.lst`,
`generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst`,
`generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`, and
`generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`.

### Boundary: Secondary Segment-57 Source

The remaining transparent-data boundary is precise and external. It is not an
unresolved parser, transparent payload, page-record, or row-skip edge.

The stream `SO ESC &p3X ! 80 !` proves a secondary high-control byte can enter
the segmented page-record path. The renderable prefix reaches bucket `448`.
The first unresolved bucket is `456`:

- selector `0x2001`;
- glyph `0x5f`;
- segment `0x39`;
- row skip `7296`;
- resolved glyph entry file offset `0x02e122`;
- bitmap source file offset `0x03fe22`;
- firmware source address `0x0bfe22`;
- required read range `0x0bfe22..0x0c0321`.

Only bytes `0x0bfe22..0x0bffff` are inside the verified `IC32,IC15`
resource-pair image. The remaining `802` bytes begin at firmware address
`0x0c0000`, outside the verified resource pair.

Disassembly evidence makes the software side exact:

- `0x1f354` takes the bit-30 offset-table form, adds the selected table entry,
  and reads row count, width, mode, and bitmap delta from the resulting glyph
  record.
- For secondary `LINE_PRINTER`, table index `0x5f` has relative offset `0`,
  so the glyph entry resolves to the record header at file offset `0x02e122`.
- `0x1f1f0` computes `segment << 7`, subtracts that row skip from the row
  count, clamps remaining rows to `0x80`, multiplies by even byte span `10`,
  and advances the bitmap pointer to file offset `0x03fe22`.

The continuation policy is physical/resource-window state:

- Mirror, code-pair continuation, and zero-fill policies all produce the same
  current-band digest
  `f0c1127f9e6b203f9829ab43f159b89c3f7dda687a47d4c09971077eac55c96e`.
- They diverge only for fallback rows after the verified suffix.
- The verified suffix `0x0bfe22..0x0bffff` has digest
  `e0a0fd34ce7a39f79ecd27c0ee288631554a0ff78359b72e27ea6087651bcf1f`.
- Startup scanner evidence constrains but does not choose the continuation:
  a full mirror at `0x0c0000` would expose a second `HEAD` chain and `48`
  typed records, while code-pair and zero-fill continuations expose non-HEAD
  markers and keep the same `24` typed records as the verified image.

The exact unresolved boundary is therefore firmware range
`0x0c0000..0x0c0321`. Closing it requires board or emulator memory-map
evidence, a direct bus read around `0x0c0000`, live startup candidate counters,
or an observed page result that matches one of the fallback-row policies.

## Worked Path: Downloaded Glyph

This path covers a host-fetched downloaded-character stream whose installed
glyph later becomes visible text and then published page output. The primary
stream is the segmented-wide fixture:

```text
ESC *c4660d37e5F ESC )s2193W <0x0891 payload bytes> % FF
```

The control bytes select font id `0x1234`, character code `0x25`, mark the
current downloaded-font record, install a glyph payload, print `%`, and eject
the page.

Parser dispatch and font-control state:

- All bytes enter through `0xa904` and parser loop `0x11774`.
- `ESC *c4660d` walks the font-control command chain through handlers
  `0x11eb6`, `0x11ec8`, `0x11eda`, and `0x15a56`; `0x15a56` writes current
  downloaded font id `0x782f2e = 0x1234`.
- `37e` stays in the same command family and reaches `0x15a18`, which writes
  current character word `0x782f30 = 0x25`.
- `5F` dispatches through `0x16df6` to mark the current downloaded-font
  record. The covered fixture reaches `0x16e86` and `0x17108`, setting record
  flag bit `6` and moving counts `0x782782/0x782786` from `7/2` to `6/3`.

Downloaded-character payload installation:

- `ESC )s2193W` reaches `0x11f96` after the parser-family handlers
  `0x11eb6`, `0x12008`, and `0x11ff6`.
- Because the parsed `W` count is nonzero, `0x11f96` schedules delayed handler
  `0x16c14` through the shared delayed-payload mechanism.
- `0x121cc` stores the restored record `80 57 08 91 00 00`, pending flag
  `0x782a1a`, and delayed handler pointer `0x782a1c`.
- `0x12218` restores that record after parser mode returns to zero and calls
  `0x16c14`.
- `0x16c14` rewinds command-record cursor `0x78299e`, writes payload byte
  budget `0x783140 = 0x0891`, resolves the current downloaded-font record,
  and installs the payload under the current record.
- The installed character uses current character `0x25`, table entry
  `0x00de`, character record delta `0x0500`, and bitmap offset `0x050c`.
- The installed glyph record bytes are:

```text
00 00 00 00 0c 02 00 81 00 88 00 00
```

- The record means mode byte `2`, rows `0x81`, width `0x88`, span `0x11`,
  bitmap size `0x0891`, and split-plane payload layout.
- `0x16942` is the split-plane reader for this payload. It consumes bytes
  through `0xa904`, writes row-prefix bytes through `A4`, writes trailing-plane
  bytes through `A3`, normalizes `1a 58` through `0xd99a`, and records
  continuation state only if the byte budget ends before the copy completes.

Printable use and page-object creation:

- After the payload is installed and remaining budget is drained, the following
  printable byte `%` returns to parser handler `0xd04a`.
- `0xd04a` resolves host byte `0x25` through the installed downloaded context.
  The covered source has glyph entry `0x0500`, rows `0x81`, width byte
  `0x11`, x `22`, y `22`, and context slot `3`.
- `0xd824 -> 0x12f2e` converts the positioned source into segmented-wide
  compact page objects through shared bucket producer `0x1387c`.
- The source becomes selector `0x3003` and is split into two segment objects:

```text
bucket 9: 00 00 00 00 30 03 00 01 25 01 66 01
bucket 1: 00 00 00 00 30 03 00 01 25 00 66 01
```

Object fields:

- `+0x04`: compact selector byte `0x30`, selecting segmented-wide rendering.
- `+0x05`: context slot `3`.
- `+0x06`: entry count `1`.
- payload byte `0x25`: downloaded glyph id.
- following byte `0x01` or `0x00`: segment number.
- coordinate `0x6601`: positioned destination for the segment.

Publication, bridge, scheduler, and pixels:

- FF reaches `0xf0f0`, which finalizes the page through `0xff1e`.
- `0xff1e` publishes the current page root, preserving bucket array entries
  `9` and `1`, empty rule/fixed lists, and context slots `(0, 0, 0, 0)`.
  It clears current root pointer `0x78297a` and sets publication flag
  `0x782996`.
- `0x1ed84` copies the published record into an active render work record.
- `0x1edc6` preserves the bucket root and context slots for compact-renderer
  dispatch.
- The scheduler entry `0x1eba4` can produce band words `0..9` for the
  published downloaded-glyph record and call `0x1ef6a` for each active band.
- `0x1ef6a` runs `0x1ef86 -> 0x1efc2 -> 0x1f446 -> 0x1f756`. This path has no
  rule or fixed-list objects, so visible output is from bucket dispatch
  `0x1efc2`.
- `0x1efc2` sends compact selector `0x30` to `0x1effe`; the segmented-wide
  row path reaches `0x1f1f0` / `0x1f264` and the wide row-copy helpers.
- The covered publication fixture renders bucket `9` segment `1` at page row
  `86`; bucket `1` segment `0` is blank for the active band in that fixture.

Composed variants:

- `ESC )s18W ... ) FF` installs an even-span wide glyph and publishes selector
  `0x1003` bucket `1`, rendered through `0x1effe -> 0x1f0d2`.
- `ESC )s6W ... & FF` installs a normal compact glyph and publishes selector
  `0x0003` bucket `1`, rendered through `0x1effe -> 0x1fe76`.
- Row-threshold streams around rows `0x80..0x82` prove the selector boundary:
  rows `0x80` remain short compact, while rows `0x81` and `0x82` enter
  segmented rendering.
- Parser-driven rule/raster composition after an `ESC )s18W` install proves
  the installed downloaded glyph can share one page record with selector-7
  rules and mode-0 raster objects before `0x1ef6a` renders all three object
  families.

State classification for this path:

- Canonical state:
  current downloaded font id `0x782f2e`, current character `0x782f30`,
  current downloaded-font records `0x782640..0x782776`, current-record flag
  bit `6`, installed payload pointer, glyph table entry `0x00de`, glyph
  record bytes, current page root `0x78297a`, bucket objects, published source
  record, and render-record bucket/context roots.
- Derived/cache state:
  payload byte budget `0x783140`, parsed span `0x7827c2`, parsed row count
  `0x7827c4`, bitmap byte count `0x7827be`, compact selector `0x3003`,
  segment numbers, bucket indices, and render-band fields.
- Parser scratch:
  command-record cursor `0x78299e`, delayed-payload fields `0x782a1a`,
  `0x782a1c`, `0x782a20..0x782a25`, staged descriptor scratch
  `0x7827de..0x7827e9`, and continuation fields `0x7827c6..0x7827da`.
- Firmware bookkeeping:
  downloaded-record counters `0x782782` and `0x782786`, candidate counters and
  cursors updated by `0x16c14`, heap allocation and release helpers, stream
  allocator fields, publication flag `0x782996`, scheduler cursors, and
  render-work progress words.
- Unknown:
  no unresolved ROM-local middle edge remains for the covered segmented-wide
  install-to-print-to-publication path or the listed normal/wide selector
  siblings. Remaining downloaded-glyph work is broader row/span
  cross-products, exact HP manual labels for some descriptor fields, and
  physical/pixel behavior after documented wrapped source-byte invalid-helper
  boundaries.

Evidence for this path is in
[downloaded-fonts.md](downloaded-fonts.md),
[font-context-metrics.md](font-context-metrics.md),
[page-record-storage.md](page-record-storage.md),
[active-render-scheduler.md](active-render-scheduler.md),
[page-raster-imaging.md](page-raster-imaging.md), and
[semantic-state-model.md](semantic-state-model.md). Key supporting listings
are `generated/disasm/ic30_ic13_assign_font_id_015a56.lst`,
`generated/disasm/ic30_ic13_font_control_dispatch_016df6.lst`,
`generated/disasm/ic30_ic13_font_payload_setup_015b80.lst`,
`generated/disasm/ic30_ic13_font_payload_readers_016874.lst`,
`generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`, and
`generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`.

### Boundary: Short Compact Downloaded-Glyph High Rows

This is the exact ROM-local visible-output boundary for downloaded glyph row
counts whose high byte is nonzero but whose printable page source still
selects the short compact renderer. It is not a parser, install, publication,
or bridge gap: those earlier edges are fixture-backed.

Boundary stream family:

- `ESC )s516W <payload> 3 FF` installs glyph `0x33` with row count `0x0102`.
- Adjacent matrix fixtures cover rows `0x0101`, `0x0102`, and `0x0103`.
- The parser-restored records carry byte budgets `0x0202`, `0x0204`, and
  `0x0206`; the installed downloaded-character records preserve the matching
  16-bit row words.

Producer and consumer behavior:

- `0x16498` installs the canonical downloaded glyph record and bitmap. For
  row `0x0102`, the record bytes are
  `00 00 00 00 0c 01 01 02 00 10 00 00`, and glyph table entry `0x0116`
  points at the installed object.
- The printable source record does not carry the full 16-bit row count to the
  page-object producer. It exposes only the low row byte to `0x12f2e`.
- For rows `0x0101..0x0103`, `0x12f2e` therefore sees low bytes
  `0x01..0x03`, derives selector `0x0003`, and publishes only bucket `1`
  through `0xff1e`.
- The page/render bridge is normal: `0x1ed84` / `0x1ef6a` select render
  bucket word `1`, `0x1ef86` derives current-band state, and compact dispatch
  reaches the short row-copy helper path.
- `0x1f414` splits the full installed row words at coordinate `0x6601`. For
  row `0x0102`, the split is `58` current-band rows plus `200` fallback rows.
  The adjacent rows split to fallback counts `199` and `201`.
- Short compact helper `0x1fe76` has valid row-count table entries only
  through index `128`. Row `0x0102` would read fallback index `200`, whose
  table target is `0x329ad3c0`.

State classification:

- Canonical state:
  downloaded glyph table entries, installed record row words `0x0101`,
  `0x0102`, and `0x0103`, bitmap payload bytes, current page root, bucket `1`
  publication, and render-record bucket root.
- Derived/cache state:
  printable source low row byte, selector `0x0003`, render bucket word `1`,
  `0x783a20 = 0x0040`, `0x783a28 = 0x00100800`, and `0x1f414`
  current/fallback row split.
- Parser scratch:
  restored `ESC )s#W` records such as `80 57 02 04 00 00`, payload byte
  budget `0x783140`, copy status `1`, zero-byte drain through `0x12328`, and
  next handler `0xd04a`.
- Firmware bookkeeping:
  downloaded-record allocation/release state around `0x16c14` / `0x16498`,
  stream allocator state, publication flag `0x782996`, and render-work
  progress.
- Hardware/external state:
  none for this boundary.
- Unknown:
  the unresolved item is only the short compact fallback helper target for
  table indices above `128`, specifically indices `199..201` for the covered
  high-row matrix. The parser, installed glyph state, low-byte selector
  truncation, publication bucket, render bucket, and row-split counts are
  documented.

Output effect:

- Rows `0x0001..0x00ff` have page-visible publication and renderer evidence in
  the downloaded-glyph row-count matrix.
- Rows `0x0101..0x0103` preserve installed row words and publish the low-byte
  short compact object, but no pixel-output claim is made after the invalid
  `0x1fe76` fallback index.
- Segmented-wide high-row paths are a separate solved branch for the sampled
  span/row combinations: they reach `0x1f264` or parser payload-count caps,
  not this short compact helper boundary.

Evidence:

- Detail note: [downloaded-fonts.md](downloaded-fonts.md), especially
  `Downloaded Glyph Row-Count Publication Checkpoint`.
- Renderer detail: [page-raster-imaging.md](page-raster-imaging.md),
  compact glyph row-copy sections around `0x1f414` and `0x1fe76`.
- Semantic checkpoint: `Downloaded Glyph Row-Count Publication Checkpoint` in
  [semantic-state-model.md](semantic-state-model.md).
- Fixture evidence:
  `host-fetched rows-0x102 downloaded glyph FF publication truncates
  page-record rows`,
  `downloaded glyph high-row truncation matrix preserves installed rows`,
  `downloaded glyph row-count matrix publishes and renders additional
  short/segmented counts`, and
  `downloaded segmented-wide row-byte boundary truncates page-record
  segments`.
- Disassembly evidence:
  `generated/disasm/ic30_ic13_font_payload_setup_015b80.lst`,
  `generated/disasm/ic30_ic13_font_payload_readers_016874.lst`,
  `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`,
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`,
  `generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst`,
  and `generated/disasm/ic30_ic13_bitmap_row_copy_tables_01fa5c.lst`.

## Worked Path: FF Publication

This path shows how an already queued page object becomes a published page
record. The primary stream is:

```text
ESC &k2G ! FF
```

In bytes:

```text
1b 26 6b 32 47 21 0c
```

Parser dispatch and command behavior:

- `ESC &k2G` routes through parser loop `0x11774` to handler `0xedf8`, which
  writes line-termination mode `0x78318f`.
- Printable byte `0x21` is then routed through `0xd04a` and queues the compact
  `LINE_PRINTER` glyph object described in `Worked Path: Printable Glyph`.
- FF byte `0x0c` is an explicit normal-table control row and calls handler
  `0xf0f0`.
- Because `ESC &k2G` set the line-termination mode, the FF path applies
  CR-style horizontal reset behavior before page eject.

Current page before publication:

- The printable byte has allocated one current page root at `0x78297a`.
- The compact text object is under page-root bucket array `+0x1c`.
- The addressed FF fixture uses stream chunk `0x00d09000` and ends with
  `0x782a70 = 0x00d6`, `0x782a72 = 0x00d09000`, and
  `0x782a76 = 0x00d0902a`.
- Page-root context slot `+0x2c` is preserved as `0x440946b4`.

The compact bucket object published by this stream is:

```text
00 00 00 00 00 00 00 01 20 00 01
```

Publication:

- `0xf0f0` flushes pending text, finalizes the valid current root through
  `0xff1e`, marks page eject with pending text byte `0xff`, and clears the
  current root.
- `0xff1e` writes page/control pool state byte `+4 = 2`, preserves the bucket
  root and context slot fields, writes published pool pointer `0x780ea6`, sets
  publication flag `0x782996`, and clears current root pointer `0x78297a`.
- The addressed fixture records one page root, one publication, one root
  clear, one finalization, one pending-text marker, and one span flush.

Bridge and render:

- The scheduler later selects the published record into active source
  `0x780eae`.
- `0x1ed84` copies active published-record header fields into the selected
  render work record.
- `0x1edc6` copies the published bucket root to render-record `+0x18` and the
  context slot to render-record `+0x24`.
- `0x1ef6a` renders in call order
  `0x1ef86 -> 0x1efc2 -> 0x1f446 -> 0x1f756`; this stream dispatches one
  compact bucket object through `0x1efc2 -> 0x1effe`.
- The published FF page-record rows match the pre-eject compact text rows.

State classification for this path:

- Canonical state:
  line-termination mode `0x78318f`, current page root `0x78297a`, compact
  bucket object, page-root context slot, published page/control record,
  published pool pointer `0x780ea6`, and render-record bucket/context roots.
- Derived/cache state:
  compact bucket/key fields from the printable path and render-band fields
  `0x783a20`, `0x783a22`, and `0x783a28`.
- Parser scratch:
  parser modes and temporary six-byte records for `ESC &k2G`, unmatched
  printable byte `0x21`, and direct control byte `0x0c`.
- Firmware bookkeeping:
  stream allocator fields `0x782a70`, `0x782a72`, `0x782a76`, publication flag
  `0x782996`, page-root clear count, pending text byte `0xff`, scheduler
  cursors, and render-work progress words.
- Unknown:
  no unresolved ROM-local FF publication-to-render edge remains for this
  stream. Physical printer output timing remains outside the ROM-local
  contract.

Evidence for this path is in
[publication-commands.md](publication-commands.md),
[direct-control-codes.md](direct-control-codes.md),
[page-record-storage.md](page-record-storage.md),
[active-render-scheduler.md](active-render-scheduler.md), and
[semantic-state-model.md](semantic-state-model.md). The key listings are
`generated/disasm/ic30_ic13_control_code_handlers_00f02c.lst`,
`generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`, and
`generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`.

## Worked Path: Page Environment Publication

This path covers publication commands whose visible pixels come from already
queued page objects, while the command itself changes page or environment
state around the publication boundary. It extends the FF-only publication path
to reset, page size, orientation, paper source, and copy-count streams.

Representative streams:

```text
! ESC E
! ESC &l1A
! ESC &l1O
! ESC &l2H
! ESC &l2X FF
```

Parser dispatch:

- All streams enter through host fetch `0xa904`, parser wrapper `0xda9a`,
  and parser loop `0x11774`.
- The initial printable byte `0x21` reaches `0xd04a` and queues a compact
  `LINE_PRINTER` glyph object before the publication command.
- `ESC E` dispatches to software-reset handler `0xcc52`.
- `ESC &l1A` dispatches to page-size handler `0xfc74`.
- `ESC &l1O` dispatches to orientation handler `0x10220`.
- `ESC &l2H` dispatches to paper-source handler `0xef62`.
- `ESC &l2X` dispatches to copies handler `0xeef0`; the following FF byte
  dispatches to `0xf0f0`, which performs the publication using the stored copy
  count.

Command behavior before publication:

- The printable byte allocates or reuses the current page root at `0x78297a`
  and stores the compact text object under page-root bucket array `+0x1c`.
- Reset `0xcc52` publishes through reset helper `0xcc70` before rebuilding the
  environment and parser/data-chain state.
- Page-size handler `0xfc74` publishes queued text before storing the new
  page code and recomputing page geometry.
- Orientation handler `0x10220` publishes queued text before changing
  orientation byte `0x782da3` and installing orientation-specific extents.
- Paper-source handler `0xef62` flushes pending text, publishes the queued
  page, refreshes cursor state, and then writes paper-source/output state.
- Copies handler `0xeef0` does not publish immediately. It stores copy count
  `0x782da4`, and the later FF handler `0xf0f0` publishes that count into the
  pool header.

Published page-record shape:

- All covered streams publish the pre-command compact `!` object:

```text
00 00 00 00 00 00 00 01 20 00 01
```

- Page-root context slot `+0x2c` is preserved as `0x440946b4` in the covered
  host-fetched and addressed publication streams.
- `0xff1e` writes published pool state byte `+4 = 2`, copies the current root
  longword to `0x780ea6`, sets publication flag `0x782996`, and clears
  current root pointer `0x78297a`.
- For reset, FF, page-size, orientation, and paper-source streams, the
  published pool header keeps default environment/status fields.
- For `! ESC &l2X FF`, `0xeef0` stores `0x782da4 = 2`; the following
  `0xff1e` publication copies that value into published pool-header word
  `+0x0c`.

Command-specific state effects:

- `! ESC E` publishes the page if a current root exists, then resets page and
  parser state. The missing-root fixture proves `ESC E` can also clear reset
  state without creating a published record.
- `! ESC &l1A` publishes first, then leaves page code `6`, portrait
  orientation, active size `3030 x 2025`, top offset `90`, and page-change
  flag `1`.
- `! ESC &l1O` publishes first, then writes orientation `1`, active size
  `2025 x 3030`, vertical offset source `50`, top offset `100`, and the
  landscape geometry threshold sequence.
- `! ESC &l2H` publishes first, then selector `2` leaves selected value
  `0x80`, writes `0x782da6 = 0x80`, sets `0x782998 = 1`, mirrors
  `0x780e8f = 0x80`, and ORs bit 0 into `0x780e26` when the output path is
  available.
- `! ESC &l2X FF` stores copy count `2` at `0x782da4`; direct fixture
  `0xeef0 ESC &l#X stores absolute clamped copy count` also pins selector
  rules where `0` leaves the old count unchanged, `-3` stores `3`, and `150`
  clamps to `99`.

Render path:

- The scheduler later selects the published record into active source
  `0x780eae`.
- `0x1ed84` copies the active published-record header into a render work
  record.
- `0x1edc6` copies bucket root `+0x1c`, rule/fixed-list roots, and context
  slots into the render record.
- `0x1ef6a` consumes the render record in call order
  `0x1ef86 -> 0x1efc2 -> 0x1f446 -> 0x1f756`.
- The covered streams dispatch the compact text object to `0x1effe` with
  context slot `0` and render the same rows as the pre-command printable
  glyph.

State classification for this path:

- Canonical state:
  current page root `0x78297a`, compact bucket object, page-root context slot,
  published pool record, published pool pointer `0x780ea6`, copy count
  `0x782da4`, paper-source byte `0x782da6`, pending paper-source/status byte
  `0x782998`, paper-source output/control bytes `0x780e8f` and `0x780e26`,
  page-size code `0x782da2`, orientation byte `0x782da3`, and active
  page-geometry fields.
- Derived/cache state:
  page extents, top offsets, orientation threshold values, compact bucket/key
  fields, and render-band fields created after `0x1ed84`.
- Parser scratch:
  parser modes and six-byte command records for `ESC E`, `ESC &l1A`,
  `ESC &l1O`, `ESC &l2H`, and `ESC &l2X`, plus host-ring drain state from
  `0xa904`.
- Firmware bookkeeping:
  stream allocator fields such as `0x782a70`, `0x782a72`, and `0x782a76`,
  publication flag `0x782996`, page-root clear state, reset/data-chain
  rebuild state from `0xcc70` / `0xcda2` / `0xe146`, and scheduler progress
  words.
- Hardware/external state:
  `0x780e8f` and `0x780e26` are software-visible paper-source output/control
  bytes. The exact formatter-to-engine physical timing remains outside the
  ROM-local proof.
- Unknown:
  no unresolved ROM-local parser-to-publication or publication-to-render
  middle edge remains for these streams. Remaining uncertainty is physical
  device comparison and page-environment variants that produce different pool
  header fields, geometry, bucket roots, bridge state, or rendered rows.

Evidence for this path is in
[publication-commands.md](publication-commands.md),
[reset-default-environment.md](reset-default-environment.md),
[page-record-storage.md](page-record-storage.md),
[page-raster-imaging.md](page-raster-imaging.md),
[active-render-scheduler.md](active-render-scheduler.md), and
[semantic-state-model.md](semantic-state-model.md). Key supporting listings
are `generated/disasm/ic30_ic13_esc_e_reset_00cc52.lst`,
`generated/disasm/ic30_ic13_page_size_handler_00fc74.lst`,
`generated/disasm/ic30_ic13_orientation_handler_010220.lst`,
`generated/disasm/ic30_ic13_paper_source_handler_00ef62.lst`,
`generated/disasm/ic30_ic13_copies_handler_00eef0.lst`,
`generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`, and
`generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`.

## Worked Path: Published Record To Active Bands

This path covers the scheduler handoff after a page/control record has already
been published by `0xff1e`. The scheduler does not create page objects. It
selects a published source record, chooses an active render work record,
copies bucket/list/context roots through `0x1ed84` / `0x1edc6`, and decides
which band words reach `0x1ef6a`.

Starting condition:

- A previous command path has created a current page root and `0xff1e` has
  published it.
- `0xff1e` wrote the source root longword to protected pool-head pointer
  `0x780ea6`, set publication flag `0x782996`, and cleared current root
  `0x78297a`.
- Parser work is complete. This scheduler path starts from page/control pool
  records, not host bytes.

Source selection:

- Pool initialization `0x3144..0x3162` seeds `0x780ea6`, `0x780eaa`,
  `0x780eae`, `0x780eb2`, and `0x780eb6` to pool base `0x780f02`.
- Candidate selection `0x7ec6..0x7f90` promotes a selectable candidate from
  `0x780e6e[]` into scheduler cursor `0x780eaa` and release cursor
  `0x780eb2`.
- Cursor path `0x7722..0x779a` advances or releases scheduler cursors while
  respecting protected pool head `0x780ea6`.
- Active scheduler entry `0x1eb32..0x1eb50` copies selected cursor
  `0x780eaa` into active source record pointer `0x780eae`.

Render work selection and bridge:

- Startup `0x2feb6` initializes two-work-record selector state
  `0x7820bc = 1` and `0x7820c0 = 1`, then clears paired render-work header
  words.
- `0x1ecd6..0x1ed76` toggles selector `0x7820bc`, chooses destination render
  work record `0x7820c4` or `0x782128`, and writes active render pointer
  `0x783a18`.
- If geometry changed, `0x1ed6c..0x1ed76` calls setup helper `0x1ee9e` before
  active-record copy.
- If geometry matches the previous work record, `0x1ed36..0x1ed6a` computes a
  same-geometry remainder through helper `0x33238`, copies previous geometry
  fields, and then reaches the same `0x1ed84` copy path.
- `0x1ed84` consumes active source `0x780eae`, copies source header words into
  the selected render work record, and calls `0x1edc6`.
- `0x1edc6` copies source bucket root `+0x1c` to render `+0x18`, source
  rule-list root `+0x24` to render `+0x1c`, source fixed-list root `+0x28` to
  render `+0x20`, and context slots `+0x2c..+0x68` to render
  `+0x24..+0x60`.

Active band loop:

- Active loop `0x1eba4..0x1ecd2` reads active render pointer `0x783a18`,
  active selector `0x7820bc`, paired selector `0x7820c0`, and active work
  words `+0x06`, `+0x0c`, `+0x0e`, `+0x10`, and `+0x16`.
- Cleanup branch: if `0x780ea5 == 1` or active work `+0x0c < +0x10`, the loop
  calls `0x1ef38`, clears active-render flag `0x780ea4`, and signals wait
  object `0x780182` through trap veneers.
- Throttle branch: if active work `+0x0e > 0x28`, the loop clears `+0x0e`,
  signals `0x780182`, and yields through `0x10d8(2)`.
- Capacity branch: the loop computes available capacity from active and paired
  remaining rows. If capacity is less than `9`, it clears `+0x0e`, signals
  `0x780182`, and waits through `0x10d0(2)`.
- Render branch: if capacity is at least `9`, the loop calls `0x1ef6a`, then
  increments active band word `+0x10` and throttle word `+0x0e`.

Output effect:

- Fixture `0x1eb2a/0x1ecd6 selects published record for render entry` proves
  published source `0x00d0eaa0` reaches active source `0x780eae`, render work
  `0x782128`, active render pointer `0x783a18`, and the same rows as direct
  `0x1ed84` / `0x1ef6a` rendering.
- Fixture `0x1ecd6 same-geometry render work reuse reaches render entry`
  proves the same-geometry branch computes destination word `+8`, derives
  `0x783a20 = 0x0020`, `0x783a22 = 3`, and
  `0x783a28 = 0x00103800`, and still reaches the same composed rows.
- Fixture `0x1eba4/0x1ef6a active render loop advances or yields bands` pins
  the render, capacity-wait, cleanup, and throttle outcomes from active and
  paired work-record fields.
- Fixture `0x1eba4 scheduler band words render published downloaded glyph`
  proves ten scheduler-produced band words `0..9` feed a published
  downloaded-glyph page record into `0x1ef6a`; only buckets `1` and `9`
  dispatch compact objects, and bucket `9` produces visible page row `86`.

State classification for this path:

- Canonical state:
  published pool-head pointer `0x780ea6`, scheduler cursor `0x780eaa`, active
  source pointer `0x780eae`, release cursor `0x780eb2`, active render pointer
  `0x783a18`, paired render work records `0x7820c4` / `0x782128`, and copied
  render roots `+0x18`, `+0x1c`, `+0x20`, and `+0x24..+0x60`.
- Derived/cache state:
  render-band rows `0x783a20`, remainder `0x783a22`, destination base
  `0x783a28`, render stride `0x783a1c`, same-geometry destination word `+8`,
  row-copy source pointer `0x783992`, and active-pool row-copy scalars.
- Parser scratch:
  none. Host parsing and page-object production have ended before this
  scheduler path begins.
- Firmware bookkeeping:
  candidate slots `0x780e6e[]`, record state byte `+4`, selector bytes
  `0x7820bc` / `0x7820c0`, active flags `0x780ea4` / `0x780ea5`, wait-object
  records rooted at `0x780182`, timer/status latches, and scheduler trap
  state.
- Hardware/external state:
  MMIO-facing fields and strobes around `$8000`, `$8a01`, `$a200`, `$a400`,
  `$a801`, and `0xffff2000` are software-visible, but their exact
  formatter/DC connector timing is outside this ROM-local proof.
- Unknown:
  no unresolved software-visible middle edge remains for published-record
  selection, render-work alternation, active bridge fields, or scheduler band
  words in the covered fixtures. Remaining uncertainty is physical engine
  pacing and bit-to-signal naming for formatter/DC hardware.

Evidence for this path is in
[active-render-scheduler.md](active-render-scheduler.md),
[page-record-storage.md](page-record-storage.md),
[page-raster-imaging.md](page-raster-imaging.md),
[dc-controller-engine.md](dc-controller-engine.md), and
[semantic-state-model.md](semantic-state-model.md). Key supporting reports are
`generated/analysis/ic30_ic13_page_record_bridge.md` and
`generated/analysis/ic30_ic13_render_path_references.md`. Key listings are
`generated/disasm/ic30_ic13_active_render_scheduler_01eb2a.lst`,
`generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`,
`generated/disasm/ic30_ic13_bitmap_state_setup_01ee9e.lst`,
`generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`,
`generated/disasm/ic30_ic13_page_pool_candidate_select_007ec6.lst`,
`generated/disasm/ic30_ic13_page_pool_cursor_007612.lst`,
`generated/disasm/ic30_ic13_active_pool_engine_gate_002038.lst`, and
`generated/disasm/ic30_ic13_engine_copy_pass_0022f4.lst`.

## Worked Path: Render Dispatch And Pixel Composition

This path covers the shared bitmap dispatch after the active-band scheduler
has called `0x1ef6a`. It starts with an active render record already selected
in `0x783a18`; parser commands and page-object producers have already
materialized page-root objects and `0x1edc6` has copied their roots into the
render record.

Dispatch order:

- `0x1ef6a` consumes active render pointer `0x783a18`.
- `0x1ef86` computes current-band caches before any object class renders.
- `0x1efc2` walks bucket-chain objects from render-record `+0x18`.
- `0x1f446` walks rule-list objects from render-record `+0x1c`.
- `0x1f756` walks fixed-list objects from render-record `+0x20`.

Bucket object classes:

- Object byte `+0x04` in range `0x00..0x3f` enters compact dispatch
  `0x1effe`. Byte bits `0x10` and `0x20` select compact helpers
  `0x1f034`, `0x1f0d2`, `0x1f1f0`, or `0x1f264` through table `0x1f024`.
  These objects are produced by printable text, downloaded glyphs, and compact
  glyph queue path `0x12f2e -> 0x1387c`.
- Object byte `+0x04` in range `0x40..0x7f` enters segment-list renderer
  `0x1f812`. These objects are produced by pending text-span flush paths
  `0x12714 -> 0x13520/0x135f0`.
- Object byte `+0x04` in range `0x80..0xff` enters encoded raster renderer
  `0x1f88e`. These objects are produced by raster row queue path
  `0x13070 -> 0x13250`.

Pixel-writing behavior:

- `0x1f626` computes destination pointer `A1` from packed object
  coordinates, band state `0x783a20`, destination base `0x783a28`, offset
  table `0x7839f8..`, stride `0x783a1c`, and fallback base `0x7810b4`.
- Compact glyph helpers resolve a context slot copied at render
  `+0x24..+0x60`; object byte `+0x05` low nibble selects the slot, and
  `0x1f008` writes active context cache `0x783a2c` before `0x1f354` resolves
  glyph bitmap pointers, span width, and row count.
- Compact row-copy helper tables `0x1f08e` and `0x1f1ac` select unrolled
  writers for byte widths `1..16`; wide compact modes use `0x2f27c` for full
  16-byte chunks and the remainder table for trailing bytes.
- Segment-list renderer `0x1f812 -> 0x1f862` consumes six-byte entries whose
  coordinate, row-count nibble, skipped byte, and width/mask word produce full
  `0xffff` words plus a trailing mask from table `0x308f2`.
- Encoded raster renderer `0x1f88e` selects mode helpers from table
  `0x1f8ca` using object byte `+0x05 & 0x03`: mode `0` copies literal words,
  mode `1` expands each byte into two rows through table `0x30914`, mode `2`
  expands through table `0x30b14` into up to three rows, and mode `3` expands
  through `0x30914` into four row destinations.
- Rule-list renderer `0x1f446` dispatches bridged fill selector
  `object[5] & 0x0f`. Selector `7` reaches solid helper `0x1f596`;
  selectors `0..6` and `8..13` reach patterned helper `0x1f4e0` through table
  `0x1f4a0`.
- Fixed-list renderer `0x1f756` runs only on five-band boundaries, consumes
  render-record `+0x20`, selects a pattern longword from table `0x308de`, and
  writes rows through `0x1f7b0` / `0x1f626`.

Composition effect:

- The ROM composes object classes in `0x1ef6a` call order: bucket-chain
  objects first, rule-list objects second, and fixed-list objects last.
- Bucket-chain order is the linked order under the active bucket selected from
  render word `+0x10`; producer paths such as `0x1387c` and `0x13250` insert
  objects into those chains before publication.
- Rule and fixed-list helpers mutate continuation fields, such as rule
  `+0x0c` and fixed-list `+0x0a`, so later render bands resume the same
  object rather than reparsing the page stream.
- Current-band overflow for compact glyphs and encoded raster rows writes
  continuation rows through the fallback buffer rooted at `0x7810b4 + D2`;
  the scheduler then calls `0x1ef6a` again with later band words.

State classification:

- Canonical state:
  render roots `+0x18`, `+0x1c`, `+0x20`, context slots `+0x24..+0x60`,
  bucket object fields `+0x04`, `+0x05`, `+0x06`, `+0x08`, and payload
  `+0x0a..`, rule-list fields `+0x05`, `+0x06`, `+0x08`, `+0x0a`, and
  `+0x0c`, and fixed-list fields `+0x04..+0x0d`.
- Derived/cache state:
  active render pointer `0x783a18`, band split count `0x783a20`, band
  remainder `0x783a22`, destination base `0x783a28`, stride `0x783a1c`,
  offset table `0x7839f8..`, compact context cache `0x783a2c`, wide-mode
  caches `0x783a40..0x783a48`, and fallback base `0x7810b4 + D2`.
- Parser scratch:
  none. Parser records, delayed payload state, and payload source positions
  have already been reduced to page-record objects by earlier producers.
- Firmware bookkeeping:
  render continuation fields, object-chain next pointers, compact row-copy
  phase `0x783a46`, and active-band progress words maintained by the
  scheduler.
- Hardware/external state:
  physical consumption of the already-rendered band buffer by the formatter/DC
  engine remains outside this ROM-local pixel composition contract.
- Unknown:
  no unresolved shared render-dispatch edge remains for the documented object
  classes. Remaining work is new byte-stream variants that create different
  object fields, selected-font contexts, helper targets, continuation state,
  or rendered rows, plus physical full-page comparison.

Evidence:

- Detail note: [page-raster-imaging.md](page-raster-imaging.md), especially
  `Bitmap Object Dispatch Semantic Checkpoint` and
  `Compact Glyph Row-Copy Semantic Checkpoint`.
- Producer notes:
  [direct-control-codes.md](direct-control-codes.md),
  [font-context-metrics.md](font-context-metrics.md),
  [downloaded-fonts.md](downloaded-fonts.md),
  [raster-graphics.md](raster-graphics.md), and
  [rectangle-graphics.md](rectangle-graphics.md).
- Disassembly evidence:
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`,
  `generated/disasm/ic30_ic13_bitmap_state_setup_01ee9e.lst`,
  `generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`,
  `generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst`,
  `generated/disasm/ic30_ic13_bitmap_draw_core_01f3d4.lst`,
  `generated/disasm/ic30_ic13_bitmap_encoded_span_modes_01f88e.lst`, and
  `generated/disasm/ic30_ic13_bitmap_row_copy_tables_01fa5c.lst`.
- Fixture evidence includes
  `0x1ef6a render entry composes bucket, rule, and fixed-width lists in call
  order`,
  `0x1ef6a page-band walk merges text raster and crossing rule`,
  `bridged text, rule, and raster layers compose into one page band`,
  `parser-driven downloaded glyph rule raster stream composes through
  0x1ef6a`,
  `0x1f812 segment-list object renders counted mask spans`,
  `0x1f756 fixed-width list renders bridged +0x20 object`,
  `0x1f446/0x1f596 renders solid black rectangle rule pixels`,
  `0x1f4e0 renders gray and HP pattern selector matrix`,
  `0x1f88e mode-0 raster object renders queued literal row`,
  `0x1f88e mode-1 raster object expands queued bytes into two rows`,
  `0x1f88e mode-2 raster object expands queued byte pair into three rows`,
  `0x1f88e mode-3 raster object expands queued bytes into four rows`,
  `0x1f034 compact text splits current band and fallback rows`,
  `0x1f0d2 renders wide inline compact payload row`,
  `0x1f1f0 renders segmented inline compact payload row`, and
  `0x1f264 renders segmented wide inline compact payload row`.

## Worked Path: Mixed Text/Rule/Raster Page Record

This path is the current heterogeneous page-image contract. It follows one
host byte stream through parser dispatch, page-record storage, publication,
render-record bridging, and pixel composition:

```text
! ESC *c12a5b0P ESC *t300R ESC *r0A ESC *b2W c3 3c FF
```

The stream is important because no single command draws the final image. The
parser queues three typed objects under one current page root, `0xff1e`
publishes that root, `0x1ed84` / `0x1edc6` bridge it into a render record,
and `0x1ef6a` renders the bucket and rule lists.

Parser and command flow:

- Host bytes are fetched by `0xa904` and dispatched by parser loop
  `0x11774`.
- Printable `!` reaches `0xd04a`, builds a source through `0x1393a`,
  positions it through `0xd824`, ensures a root through `0x10084`, and queues
  compact text through `0x12f2e` / `0x1387c`.
- `ESC *c12a5b0P` reaches `0x10e68`, `0x10e22`, and final fill handler
  `0x10898`, which queues a selector-7 rectangle rule through `0x10b80`,
  `0x13386`, and `0x133aa`.
- `ESC *t300R` reaches `0x10808`, and `ESC *r0A` reaches `0x1075a`, preparing
  raster state block `0x783170`.
- `ESC *b2W` reaches `0x11f82`, which schedules delayed handler `0x105d0`
  through `0x121cc`. Terminal restore `0x12218` reinstalls command record
  `80 57 00 02 00 00`; `0x105d0` consumes payload `c3 3c` and queues a
  mode-0 encoded raster object through `0x13070` / `0x13250`.
- FF reaches `0xf0f0` and publishes the current page through `0xff1e`.

Canonical objects and fields:

- Page-root bucket array `+0x1c` holds the compact text object at
  `0x00d0c004` and the raster object at `0x00d0c038`; the published bucket
  root is the encoded object bytes
  `00 d0 c0 04 80 00 00 02 00 00 c3 3c`.
- Page-root rule list `+0x24` holds the rectangle object at `0x00d0c02a`;
  the published rule bytes are
  `00 00 00 00 01 07 5c 01 00 0c 00 05 00 00`.
- Context slots starting at root `+0x2c` are copied with the page; slot 0 is
  `0x440946b4` in the addressed fixture for this stream.
- `0x1edc6` copies root `+0x1c` to render `+0x18`, root `+0x24` to render
  `+0x1c`, and context slots to render `+0x24..+0x60`.

State classification:

- Canonical state:
  current page root `0x78297a`, bucket/rule/context root fields, compact text
  object bytes, selector-7 rule object bytes, encoded raster object bytes,
  published source record, and render-record roots.
- Derived/cache state:
  stream allocator cursors `0x782a70 = 0x00bc`,
  `0x782a72 = 0x00d0c000`, `0x782a76 = 0x00d0c044`, plus render-band caches
  `0x783a20 = 0x0050`, `0x783a22 = 0`, and
  `0x783a28 = 0x00100000`.
- Parser scratch:
  delayed snapshot `01 00 01 05 d0 80 57 00 02 00 00`, restored transfer
  record `80 57 00 02 00 00`, payload offset `28`, and payload bytes
  `c3 3c`.
- Firmware bookkeeping:
  one stream allocation, one page-root allocation, one publication, one root
  clear, publication flag `0x782996`, and active render scheduler progress.
- Hardware/external state:
  none required for the ROM-local byte-to-bitmap contract. Physical engine
  pacing is a separate output boundary after the rendered band buffer exists.
- Unknown:
  no unresolved middle edge remains for the object fields or render bridge in
  this exact stream. Remaining ROM-local work is byte streams that change text
  source fields, rectangle clipping or selector state, raster gate outcomes,
  `0x1381c` allocation/rollover fields, bridge roots, continuation state, or
  rendered rows.

Output and composition effect:

- `0xff1e` publishes the same compact text, selector-7 rule, and mode-0 raster
  objects that were assembled under the current page root.
- `0x1ef6a` calls `0x1ef86`, then renders bucket objects through `0x1efc2`.
  The raster object dispatches to `0x1f88e`, and the compact text object
  dispatches to `0x1effe`.
- `0x1ef6a` then renders the rule list through `0x1f446`; selector `7`
  reaches solid helper `0x1f596`.
- The documented row output contains the compact `!`, the mode-0 raster row
  from payload `c3 3c`, and the rectangle rule after the same publication and
  render-entry boundaries.

The consecutive-raster sibling extends this path with two delayed transfers:

```text
! ESC *c12a5b0P ESC *t300R ESC *r0A
ESC *b2W f0 0f ESC *b2W 0f f0 FF
```

It stores raster objects at `0x00d0d038` and `0x00d0d044`, publishes bucket
chain `0x00d0d044 -> 0x00d0d038 -> 0x00d0d004`, leaves allocator state
`0x782a70 = 0x00b0`, `0x782a72 = 0x00d0d000`,
`0x782a76 = 0x00d0d050`, and renders encoded row `0f f0`, encoded row
`f0 0f`, then compact text. Raster `row_y` advances to `2`.

Evidence:

- Detail checkpoint: `Mixed Text/Rule/Raster Page Record` in
  [semantic-state-model.md](semantic-state-model.md).
- Reproduction map:
  [end-to-end-reproduction-map.md](end-to-end-reproduction-map.md).
- Fixture evidence:
  `host-fetched text rectangle raster FF publishes rendered page record`,
  `addressed text rectangle raster FF publishes rendered page record`,
  `addressed text/rule/raster field groups reach publication and render
  entry`,
  `host-fetched text rectangle multi-row raster FF publishes rendered page
  record`,
  `addressed text/rule/multi-row raster publication preserves bucket chain`,
  and `0x1ef6a page-band walk merges text raster and crossing rule`.
- Disassembly evidence:
  `generated/disasm/ic30_ic13_main_parser_loop_011774.lst`,
  `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`,
  `generated/disasm/ic30_ic13_rectangle_graphics_010898.lst`,
  `generated/disasm/ic30_ic13_raster_handlers_0105d0.lst`,
  `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`,
  `generated/disasm/ic30_ic13_raster_object_queue_013070.lst`,
  `generated/disasm/ic30_ic13_display_list_helpers_013386.lst`,
  `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`,
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`, and
  `generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`.

## Worked Path: Vertical Forms Control

This path covers the VFC command family: `ESC &l#W` loads a channel table, and
`ESC &l#V` consumes that table to move the text cursor or publish the current
page before the next printable byte.

The table-load stream is:

```text
ESC &l4W 00 00 00 02 !
```

The channel-jump stream is:

```text
ESC &l2V !
```

Parser dispatch and table definition:

- The bytes enter through `0xa904`, parser wrapper `0xda9a`, and parser loop
  `0x11774`.
- `ESC &l#W` routes through the `ESC &l` family to handler `0x11f6e`.
- `0x11f6e` schedules delayed handler `0x12cfe` through shared scheduler
  `0x121cc`.
- `0x121cc` stores the six-byte command record and delayed handler pointer in
  parser scratch. The lowercase-preservation fixture shows that
  `ESC &l4w4W` keeps the earlier lowercase `w` record
  `80 77 00 04 00 00` while uppercase `W` leaves the pending delayed record
  intact.
- `0x12218` restores the saved record after parser mode returns to zero and
  calls `0x12cfe`.
- `0x12cfe` rewinds command-record cursor `0x78299e`, reads the absolute byte
  count, consumes payload through data reader `0xdace`, writes the VFC table
  rooted at `0x782dde`, clears unused table bytes, derives VFC bottom
  `0x782dc2`, copies text-bottom cache `0x782dd2`, and clears modified-layout
  flag `0x782ee1`.
- For `ESC &l4W 00 00 00 02 !`, bytes `00 00 00 02` become the table prefix
  and are consumed before the following printable byte. The following `!`
  queues at compact coordinate `0x9001`.

Default table and layout refresh:

- `0x12b96` rebuilds the default 128-word VFC table from cached line bounds.
- Shared page-layout refresh helper `0xe5e2` calls the same default-table
  builder after it refreshes top offset, text bottom, margins, pending cursor,
  and static font-context state.
- For the documented Letter/6 LPI default, channel selectors are one-based:
  selector `2` searches for bit `0x0002`, and the default table marks lines
  `61` and `62` for channel 2.

Channel jump behavior:

- `ESC &l#V` routes to handler `0x1280a`.
- `0x1280a` reads selector, current VMI `0x783160`, vertical cursor
  `0x782c8e`, top offset `0x782dce`, line caches `0x782ede` and
  `0x782ee0`, and VFC table words `0x782dde..0x782edd`.
- Selector `n` becomes mask `1 << (n - 1)`. Selector `2` therefore searches
  for table bit `0x0002`.
- In the forward in-text fixture, `0x1280a` finds channel 2 at line `1`,
  ensures a current page root through `0x10084`, resets horizontal cursor
  through `0xf06e`, flushes pending text through `0xf34a`, writes y `176`,
  and lets the following printable `!` queue at compact coordinate `0xb001`.
- In the before-top sibling, y `89` is below top offset `90`; branch
  `0x128ae..0x128f4` normalizes the start line to `0` before the same line-1
  search and printable coordinate `0xb001`.

Page-boundary behavior:

- VFC does not render pixels directly. Its visible effect is the cursor and
  page-root state consumed by later printable bytes, or an explicit
  publication before those bytes.
- Selector-zero target-equal path `ESC &l0V!` computes top-of-form y `126`,
  leaves an already matching cursor unchanged, ensures a page root, and queues
  `!` at compact coordinate `0x9e02`.
- Selector-zero page-eject stream `! ESC &l0V !` first queues a printable on
  the old page, then branch `0x1299c..0x129c4` runs
  `0xf06e -> 0xf34a -> 0xf34a -> 0xf124`, publishes the old page through
  `0xff1e`, resets x/y to `10`/`126`, and queues the next `!` on a fresh page
  at compact coordinate `0x9001`.
- Wrap-hit stream `! ESC &l2V !` starts at y `226`, publishes the old page,
  wraps to line `1`, writes y `176`, and queues the next `!` at coordinate
  `0xb001`.
- Wrap-no-hit and target-after-text siblings publish the old page and recover
  to top-of-form or near-top y before queuing the next printable. The
  non-publishing recovery siblings write the same cursor state without calling
  `0xf124`.

Publication, bridge, and pixels:

- Page-eject VFC branches publish through the same `0xf124 -> 0xff1e`
  boundary used by FF and reset.
- `0xff1e` preserves the old page root's compact bucket objects in the
  published page/control record, sets publication flag `0x782996`, and clears
  current root pointer `0x78297a`.
- The next printable byte allocates or reuses a fresh current page root through
  the normal printable path.
- Published pre-VFC rows render through `0x1ed84`, `0x1edc6`, and
  `0x1ef6a`; post-VFC rows render from the fresh page root when that page is
  later published.

State classification for this path:

- Canonical state:
  VFC table `0x782dde..0x782edd`, current VMI `0x783160`, top offset
  `0x782dce`, vertical cursor `0x782c8e`, horizontal cursor `0x782c8a`, text
  margins `0x782dd6` and `0x782dda`, current page root `0x78297a`, published
  source record, and render-record bucket/context roots.
- Derived/cache state:
  VFC bottom `0x782dc2`, text-bottom cache `0x782dd2`, line-count caches
  `0x782ede`, `0x782edf`, and `0x782ee0`, selector mask
  `1 << (selector - 1)`, compact coordinates such as `0xb001` and `0x9001`,
  and render-band fields.
- Parser scratch:
  command-record cursor `0x78299e`, delayed-payload flag `0x782a1a`,
  delayed handler pointer `0x782a1c`, saved command record bytes, and the
  current `ESC &l#V` selector.
- Firmware bookkeeping:
  modified-layout flag `0x782ee1`, pending text/cursor latches
  `0x782a58` and `0x782a6d`, pending span-flush flag `0x783184`, publication
  flag `0x782996`, scheduler cursors, and render-work progress words.
- Unknown:
  no unresolved ROM-local middle edge remains for the documented VFC
  table-definition, default-table, forward channel jump, selector-zero,
  wrap-hit, wrap-no-hit, or target-after-text page-boundary paths. The manual
  names for line-count fields `0x782ede`, `0x782edf`, and `0x782ee0` remain
  inferred.

Evidence for this path is in
[vertical-forms-control.md](vertical-forms-control.md),
[direct-control-codes.md](direct-control-codes.md),
[publication-commands.md](publication-commands.md),
[page-record-storage.md](page-record-storage.md),
[active-render-scheduler.md](active-render-scheduler.md), and
[semantic-state-model.md](semantic-state-model.md). Key supporting listings
are `generated/disasm/ic30_ic13_vertical_forms_control_01280a.lst`,
`generated/disasm/ic30_ic13_control_code_handlers_00f02c.lst`,
`generated/disasm/ic30_ic13_hmi_vmi_handlers_00ca8c.lst`,
`generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`, and
`generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`.

## Worked Path: Macro Execute Replay

This path shows a stored byte stream returning to the normal parser and page
model. The primary stream defines macro id `123`, stores `! CR`, stops the
definition, then executes the stored payload:

```text
ESC &f123Y ESC &f0X ! CR ESC &f1X ESC &f2X
```

In bytes:

```text
1b 26 66 31 32 33 59 1b 26 66 30 58 21 0d
1b 26 66 31 58 1b 26 66 32 58
```

Parser dispatch and macro selection:

- The live host bytes enter through `0xa904`, parser wrapper `0xda9a`, and
  parser loop `0x11774`.
- Normal parser mode `17` routes `ESC &f#Y` to `0xe112` and `ESC &f#X`
  to `0xdd08`.
- `0xe112` rewinds the six-byte command record and stores the absolute
  parsed id word `123` in current macro id field `0x783164`.
- `0xdd08` rewinds command-record cursor `0x78299e`, calls `0xe0a4`, and
  selects or allocates the matching 12-byte macro record under pool
  `0x782a98`.
- `0xe0a4` writes current macro record pointer `0x782d7a`. It treats a
  record as selectable only when record head pointer `+0x00` is nonzero, and
  it compares the requested id against record word `+0x08`.

Definition storage:

- Selector `0` reaches `0xdd86`, starts definition mode, and makes ordinary
  following bytes append to the selected macro record instead of dispatching
  as page output.
- Alternate/data parser table `0x116f6` still routes `x/X` to `0xdd08`, so
  the later `ESC &f1X` can stop the definition while ordinary payload
  controls are appended.
- `0xe002` appends bytes into linked 0x100-byte chunks rooted by macro record
  `+0x00`. Each chunk has a four-byte next pointer followed by 252 payload
  bytes.
- For this stream, payload bytes `21 0d` are stored. The direct printable
  handler `0xd04a` and CR handler `0xf02c` do not run during definition.
- Record `+0x04` is the raw count including four header bytes per allocated
  chunk. Selector `1` stop derives the payload count as
  `raw_count - (((raw_count + 0xff) >> 8) * 4)` and keeps the nonempty
  record selectable.

Execute frame and replay:

- Selector `2` reaches `0xde7c`, which executes the selected record through
  `0xe418`.
- `0xe418` advances active data-chain frame pointer `0x782d76` by `0x0e`
  and writes a replay frame:
  frame `+0x00/+0x04` copy the macro payload-chain head and raw byte count,
  frame `+0x08 = 4`, frame `+0x09 = 2`, and frame `+0x0a` is an environment
  snapshot chain pointer.
- When the parser next asks for bytes, `0xa904` gives the active data-chain
  frame priority over outer live input.
- The replayed bytes `21 0d` return to parser loop `0x11774` as ordinary
  input bytes. `0x21` falls through to printable handler `0xd04a`; `0x0d`
  reaches CR handler `0xf02c`.
- At the frame end marker, `0xa904` calls `0xe22c`. For execute frame
  kind `2`, `0xe22c` restores the environment snapshot, frees the snapshot
  chain through `0x18b4`, rewinds `0x782d76`, and resumes the outer byte
  source.

Page-object effect:

- Replayed `0xd04a` uses the same printable source path as live byte `0x21`.
  In the pinned `LINE_PRINTER` case it maps host byte `0x21` to glyph
  byte `0x20`, source flag `1`, and source object `0x782d7e`.
- The positioned queue path `0xd824 -> 0x12f2e` writes a compact text object
  under current page-root bucket array `+0x1c` through shared producer
  `0x1387c`.
- The object prefix for the covered replayed glyph is the same compact object
  as the direct printable path:

```text
00 00 00 00 00 00 00 01 20 00 01
```

- Replayed CR updates cursor/control state through `0xf02c`; it does not
  create a separate page object in this pinned `!\r` replay path.

Publication, bridge, and pixels:

- The replay-built compact object remains in the current page root until a
  page publication path such as FF calls `0xff1e`.
- `0xff1e` publishes the current root into the page/control pool and clears
  current root pointer `0x78297a`.
- `0x1ed84` seeds the active render work record from selected published
  source `0x780eae`.
- `0x1edc6` copies page-root bucket array `+0x1c` to render-record `+0x18`
  and copies context slots `+0x2c..+0x68` to render-record
  `+0x24..+0x60`.
- `0x1ef6a` dispatches render-record bucket objects through `0x1efc2`.
  The replayed compact text object reaches `0x1effe`, glyph resolver
  `0x1f354`, and the same row-copy helpers as direct printable text.
- Macro execute replay therefore has no macro-specific renderer. Its visible
  pixels come from the same compact text renderer used by live host byte
  `0x21`.

State classification for this path:

- Canonical state:
  current macro id `0x783164`, macro record pool `0x782a98`, current record
  pointer `0x782d7a`, active data-chain frame pointer `0x782d76`, frame
  fields `+0x00/+0x04/+0x08/+0x09/+0x0a`, current page root `0x78297a`,
  compact text object, published source record, and render-record
  bucket/context roots.
- Derived/cache state:
  normalized payload count from selector `1`, execute environment snapshot
  chain, compact bucket/key fields `0x782a7a..0x782a7e`, glyph offsets from
  the selected font record, and render-band fields `0x783a20`, `0x783a22`,
  and `0x783a28`.
- Parser scratch:
  parser mode `17`, alternate/data table selection at `0x116f6`,
  definition-mode byte `0x782c18`, append-error byte `0x782c19`,
  command-record cursor `0x78299e`, and replayed bytes `21 0d`.
- Firmware bookkeeping:
  chunk allocator state around `0x783988`, record raw count `+0x04`,
  host gate bit 1 in `0x780e66`, frame-end cleanup through `0xe22c`,
  stream allocator fields, publication flag `0x782996`, scheduler cursors,
  and render-work progress words.
- Unknown:
  no unresolved ROM-local middle edge remains for this covered execute replay
  path from stored `!\r` to compact text rendering. Remaining macro work is
  broader payload variants, overlay variants outside the documented matrix,
  external/manual names for macro context bytes, and final physical output
  comparison.

Evidence for this path is in
[macro-data-chain.md](macro-data-chain.md),
[host-byte-fetch.md](host-byte-fetch.md),
[pcl-parser-core.md](pcl-parser-core.md),
[page-record-storage.md](page-record-storage.md),
[page-raster-imaging.md](page-raster-imaging.md), and
[semantic-state-model.md](semantic-state-model.md). Key supporting listings
are `generated/disasm/ic30_ic13_pcl_escape_parser_00da9a.lst`,
`generated/disasm/ic30_ic13_macro_record_chain_helpers_00dfba.lst`,
`generated/disasm/ic30_ic13_macro_environment_snapshot_helpers_00e65c.lst`,
`generated/disasm/ic30_ic13_main_parser_loop_011774.lst`, and
`generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`.

## Worked Path: Rectangle Rule

This path covers a parameterized command family that does not use bucket-chain
text/raster objects. The primary stream is:

```text
ESC *c12a5b0P
```

In bytes:

```text
1b 2a 63 31 32 61 35 62 30 50
```

Parser dispatch:

- The bytes enter through `0xa904`, `0xda9a`, and parser loop `0x11774`.
- The parser walks modes `0 -> 1 -> 3 -> 16 -> 16 -> 16 -> 0`.
- Prefix setup handlers `0x11eb6`, `0x11ec8`, and `0x11eda` keep the
  `ESC *c` family active while parameters and lowercase finals accumulate.
- `ESC *c12a` calls handler `0x10e68`.
- `5b` stays in the same family and calls handler `0x10e22`.
- `0P` terminates the family and calls handler `0x10898`.

Command behavior:

- `0x10e68` rewinds the six-byte command record and stores dot width `12` in
  rectangle width field `0x78316a`.
- `0x10e22` rewinds the next command record and stores dot height `5` in
  rectangle height field `0x783166`.
- `0x10898` rewinds the final record and maps fill parameter `0` to selector
  `7`, meaning solid black.
- `0x10898` then calls the rectangle clip/queue path when width and height are
  nonzero.

Rule source and page-object creation:

- `0x10b80` reads current cursor fields `0x782c8a` and `0x782c8e`, page
  extents `0x782db8` and `0x782db6`, orientation byte `0x782da3`, and the
  pending width/height/fill fields.
- It clips or rejects the rectangle against page extents, ensures a current
  page root through `0x10084`, and writes source record `0x782a88`.
- For the primary fixture, source record fields produce x `10`, y `20`,
  width `12`, height `5`, and selector `7`.
- `0x13386` computes derived rule bucket/key fields through `0x134d6`.
- `0x133aa` allocates a 14-byte rule object through `0x1381c` and inserts it
  into the page-root rule list at root `+0x24`.

The primary rule object before bridge is:

```text
00 00 00 00 01 07 4a 00 00 0c 00 05 00 00
```

Object fields:

- `+0x00`: next pointer `0`.
- `+0x04`: bucket byte `1`.
- `+0x05`: fill selector `7`.
- `+0x06`: packed key `0x4a00`.
- `+0x08`: width `12`.
- `+0x0a`: height `5`.
- `+0x0c`: render continuation height, still `0` before bridge.

Publication and bridge:

- The rule object remains under current page-root list `+0x24` until a
  publication path finalizes the root.
- `0xff1e` publishes the current root when the page is finalized.
- `0x1ed84` seeds the active render record from selected source
  `0x780eae`.
- `0x1edc6` copies source root `+0x24` to render-record `+0x1c`.
- During that copy, `0x1edc6` ORs object byte `+0x05` with `0x10` and copies
  height `+0x0a` to continuation word `+0x0c`.

The bridged rule object is:

```text
00 00 00 00 01 17 4a 00 00 0c 00 05 00 05
```

Render scheduling and pixels:

- `0x1eba4` calls `0x1ef6a` for an active band when capacity allows rendering.
- `0x1ef6a` calls `0x1ef86`, then bucket dispatch `0x1efc2`, then rule-list
  dispatch `0x1f446`, then fixed-list dispatch `0x1f756`.
- `0x1f446` walks render-record rule list `+0x1c`.
- The bridged selector byte `0x17` has low nibble `7`, so `0x1f446`
  dispatches to solid helper `0x1f596`.
- `0x1f596` decodes key `0x4a00` as x `10`, y `20`, width `12`, rows `5`,
  and partial mask `0xfff0`.

The documented visible rows for the black rule are:

```text
......................
..........############
..........############
..........############
..........############
..........############
```

Continuation behavior:

- If a solid rule crosses a render band, `0x1f596` subtracts the rows drawn in
  the current band from continuation word `+0x0c`.
- The pinned crossing fixture starts at y `78` with height `5`, draws two rows
  in the first band, carries `3` rows in `+0x0c`, and draws the remaining rows
  at y `0` in the next band.

State classification for this path:

- Canonical state:
  rectangle width `0x78316a`, rectangle height `0x783166`, area-fill field
  `0x78316e`, source record `0x782a88`, current page root `0x78297a`, rule
  list root `+0x24`, published source record, and render-record rule list
  `+0x1c`.
- Derived/cache state:
  rule bucket/key fields `0x782a7c`, `0x782a7d`, `0x782a7e`, horizontal phase
  `0x782dc0`, and render-band fields `0x783a20`, `0x783a22`, `0x783a28`.
- Parser scratch:
  parser mode byte, command-record cursor `0x78299e`, and the six-byte records
  consumed by `0x10e68`, `0x10e22`, and `0x10898`.
- Firmware bookkeeping:
  stream allocator fields `0x782a70`, `0x782a72`, and `0x782a76`,
  page-root retry bit `+0x15.0`, publication flag `0x782996`, scheduler
  cursors, and render-work progress words.
- Unknown:
  no unresolved ROM-local selector-7 rule object or solid dispatch edge
  remains for this path. Remaining rectangle work is byte streams that change
  clipping, allocation rollover, retry publication, selector mapping, bridge
  fields, or rendered rows.

Evidence for this path is in
[rectangle-graphics.md](rectangle-graphics.md),
[page-record-storage.md](page-record-storage.md),
[page-raster-imaging.md](page-raster-imaging.md), and
[semantic-state-model.md](semantic-state-model.md). The key supporting report
is `generated/analysis/ic30_ic13_rectangle_graphics_flow.md`; the focused
listings are `generated/disasm/ic30_ic13_rectangle_graphics_010898.lst`,
`generated/disasm/ic30_ic13_display_list_helpers_013386.lst`, and
`generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`.

## Worked Path: Raster Row

This is the current concrete example of the full dataflow. The primary byte
stream is:

```text
ESC *t300R ESC *r1A ESC *b4W f0 0f aa 55
```

In bytes:

```text
1b 2a 74 33 30 30 52 1b 2a 72 31 41
1b 2a 62 34 57 f0 0f aa 55
```

Parser dispatch:

- The host bytes are fetched through `0xa904` and delivered to parser loop
  `0x11774`.
- `ESC *t300R` produces command record `80 52 01 2c 00 00` and calls
  handler `0x10808`.
- `ESC *r1A` produces command record `80 41 00 01 00 00` and calls handler
  `0x1075a`.
- `ESC *b4W` produces command record `80 57 00 04 00 00` and calls handler
  `0x11f82`.

Command behavior:

- `0x10808` handles raster resolution. Because raster active byte
  `0x783182` is clear, requested `300` selects scale `1` and encoded mode
  `0` in raster state block `0x783170`.
- `0x1075a` starts raster graphics. Parameter `1` seeds the origin from the
  active cursor axis, copies that origin to raster state `+0x00`, computes
  byte limit `+0x10`, and leaves the raster state ready for row transfers.
- `0x11f82` does not consume the four payload bytes. It schedules delayed
  handler `0x105d0` through `0x121cc`, saving the handler longword and the
  six-byte command record in parser scratch.

Delayed payload handoff:

- `0x121cc` stores pending byte `0x782a1a = 1`, handler longword
  `0x782a1c = 0x105d0`, and snapshot
  `01 00 01 05 d0 80 57 00 04 00 00`.
- When parser mode returns to zero, `0x12218` restores record
  `80 57 00 04 00 00` into the command-record buffer and calls `0x105d0`
  through the saved handler pointer.
- `0x105d0` rewinds `0x78299e` by six, reads record word `+2` as byte count
  `4`, sets active byte `+0x12`, computes the transfer row, and gates the
  payload against page extent and byte limit.

Page-object creation:

- Accepted rows pass the beyond-extent test, so `0x105d0` ensures a current
  page root through `0x10084`.
- `0x105d0` stores the raster row word in state `+0x02`, accepted byte count
  in state `+0x04`, and overflow count in state `+0x06`.
- Nonnegative accepted rows call `0x13070` with raster state block
  `0x783170`.
- `0x13070` computes bucket index `0x782a7c` from row `+0x02`, packed key
  `0x782a7e` from row/x state, and requested object size from accepted count
  `+0x04`.
- `0x13250` allocates and links an encoded raster bucket object under
  page-root `+0x1c`.
- `0x138de` copies the accepted payload bytes from `0xa904` into object
  payload `+0x0a`. Its local control-pair rule maps queued `1a 58` to byte
  `00`; the primary stream has no such pair.

The primary encoded object is:

```text
00 00 00 00 80 00 00 04 00 01 f0 0f aa 55
```

Object fields:

- `+0x00`: next pointer `0`.
- `+0x04`: class byte `0x80`, selecting encoded raster rendering.
- `+0x05`: encoded mode `0`.
- `+0x06`: payload capacity `4`.
- `+0x08`: packed coordinate/key `0x0001`.
- `+0x0a`: payload bytes `f0 0f aa 55`.

Publication and bridge:

- The row object remains page content under the current page root until a
  publication path such as FF or `0xff1e` finalizes the root.
- `0xff1e` publishes the current root, sets publication flag `0x782996`, and
  clears current root pointer `0x78297a`.
- The scheduler selects a published source into `0x780eae`.
- `0x1ed84` seeds the active render record.
- `0x1edc6` copies source root `+0x1c` to render-record `+0x18`, preserving
  the encoded raster bucket chain for render dispatch.

Render scheduling and pixels:

- `0x1eba4` advances active render work and calls `0x1ef6a` when the current
  band has capacity.
- `0x1ef6a` calls `0x1ef86` to compute band destination fields, then calls
  `0x1efc2` for bucket-chain objects.
- `0x1efc2` sees object byte `+4 & 0xc0 == 0x80` and dispatches to encoded
  raster writer `0x1f88e`.
- `0x1f88e` selects helper `0x1f8da` from table `0x1f8ca` because
  `object[5] & 0x03 == 0`.
- Mode `0` copies literal payload words into the destination row. For the
  primary object above, the documented rendered row is:

```text
................####........#####.#.#.#..#.#.#.#
```

State classification for this path:

- Canonical state:
  raster block `0x783170`, current page root `0x78297a`, encoded bucket object
  fields, published source record, and render-record bucket root.
- Derived/cache state:
  `0x782a7c`, `0x782a7e`, `0x782a80`, `0x783a20`, `0x783a22`, and
  `0x783a28`.
- Parser scratch:
  delayed snapshot fields `0x782a1a`, `0x782a1c`, `0x782a20..0x782a25`,
  restored record `80 57 00 04 00 00`, and payload source position.
- Firmware bookkeeping:
  stream allocator fields `0x782a70`, `0x782a72`, `0x782a76`, publication
  flag `0x782996`, scheduler cursors, and render-work progress words.
- Unknown:
  no unresolved ROM-local object layout or dispatch edge remains for this
  primary path. Remaining raster work is byte-stream variants that change gate
  outcomes, dense-row splitting, bridge fields, or rendered rows.

Evidence for the path is in [raster-graphics.md](raster-graphics.md),
[page-record-storage.md](page-record-storage.md),
[active-render-scheduler.md](active-render-scheduler.md), and
[page-raster-imaging.md](page-raster-imaging.md). The key focused listings are
`generated/disasm/ic30_ic13_raster_handlers_0105d0.lst`,
`generated/disasm/ic30_ic13_raster_object_queue_013070.lst`,
`generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`,
`generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`,
`generated/disasm/ic30_ic13_active_render_scheduler_01eb2a.lst`, and
`generated/disasm/ic30_ic13_bitmap_encoded_span_modes_01f88e.lst`.

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

- Hardware/MMIO: direct host-input and host-output register names behind
  `0x8e01`, `0x8801`, `0x8c01`, `0xa601`, `0xaa01`,
  `0xfffee001`, `0xfffee003`, `0xfffee005`, `0xfffee009`,
  `0xfffe0001`, and `0xfffe0003`. The ROM-visible ready/data/status and
  control-shadow roles are documented; physical serial/parallel/optional-I/O
  mapping still needs board correlation.
- Hardware/MMIO: service, panel, and retained-storage sources behind
  `$8000.w`, `$a200`, `$a400`, `$a801`, `$8a01`, and the `$fffee00b`,
  `$fffee00d`, `$fffee00f`, `$fffee011`, `$fffee013` register family. ROM
  consumers and status effects are documented in the reset/default,
  host-byte-fetch, and external-ready notes; the external device/protocol
  identity remains board-level.
- Hardware/MMIO to physical engine: scheduler and status helper ranges
  `0x0d52..0x0f7a`, `0x0f84..0x0fa0`, `0x1020..0x102e`,
  `0x10bc..0x11f8`, `0x123a..0x1282`, and `0x1cf8..0x1ea8`.
  Software-visible wait objects, latches, and render scheduling are modeled;
  mapping to formatter/DC signals such as `BD`, `VDO`, `VSREQ`, `VSYNC`,
  `PRNT`, `CMND`, `CCLK`, `CBSY`, `STATS`, `PCLK`, `SBSY`, `RDY`, `PPRDY`,
  and `CPRDY` remains physical timing work.
- Missing external resource data: optional resource windows
  `0x200000..0x3ffffe` and `0x400000..0x5ffffe`. The ROM scan and scheduler
  state are documented; cartridge/external resource contents are not present in
  the verified local ROM set.
- Missing physical memory-map data: built-in resource continuation
  `0x0c0000..0x0c0321`. Transparent secondary segment-57 rendering reaches
  source range `0x0bfe22..0x0c0321`; only `0x0bfe22..0x0bffff` is inside the
  verified IC32/IC15 resource-pair image. Mirror, code-pair, and zero-fill
  policies are fixture-bounded, but the physical decode after `0x0c0000`
  remains unproven.
- ROM-local visible-output helper boundary:
  `Boundary: Short Compact Downloaded-Glyph High Rows` documents the exact
  short compact downloaded-glyph fallback edge in helper `0x1fe76`. Rows
  `0x0101..0x0103` preserve installed row state and prove low-byte selector
  truncation through `0x12f2e`, bucket `1` publication, render bucket word
  `1`, and `0x1f414` fallback counts `199..201`; helper table indices above
  the documented valid maximum `128` remain the unresolved renderer-helper
  edge.
- ROM-local variant boundaries rather than generic gaps:
  dense page/object streams that change `0x1381c` rollover, `0x13250` encoded
  raster gate outcomes, `0x133aa` / `0x136d2` list ordering, or bridge fields;
  macro overlay payload variants beyond the documented matrix; and selected
  font combinations that change context/map/selector state before visible
  output.

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
