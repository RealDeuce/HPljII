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
  rows. Output uncertainty is not physical; the documented effect is absence
  of page-object production in normal mode.

Evidence for this path is in [pcl-parser-core.md](pcl-parser-core.md),
[pcl-command-map.md](pcl-command-map.md), and
[semantic-state-model.md](semantic-state-model.md). The generated parser table
extract `generated/analysis/ic30_ic13_parser_dispatch_tables.md` shows the
normal-mode blank rows at mode-0 table `0x010eae..0x010ef6` and the
alternate/data blank rows at mode-0 table `0x0112f4..0x01133c`. Key supporting
listings are `generated/disasm/ic30_ic13_main_parser_loop_011774.lst` and
`generated/disasm/ic30_ic13_pcl_escape_parser_00da9a.lst`.

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
