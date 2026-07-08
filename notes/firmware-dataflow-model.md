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

Rows named in this documentation are ROM-derived rows: bytes produced by
following ROM disassembly, decoded resource data, page-record fields, and
render helpers. Future device output is not part of the evidence standard, and
there is no independent rendered-row oracle. Fixtures can check that a
documented byte stream reaches the documented ROM state and that helper
transcriptions are internally consistent; they cannot substitute for ROM
tracing or compare pixels against a separate truth image. When an unresolved
item asks for a fixture, the fixture is only a branch/path driver; the semantic
documentation still has to trace the ROM handlers, field writes, page objects,
and render helpers that generate the rows. No future fixture or physical
capture is required to upgrade a ROM-local claim; the upgrade comes from
documenting the missing disassembly edge.

## Reader Path Index

Use these worked paths as entry points for the byte-stream-to-pixel model:

- Startup and initial firmware state:
  `Worked Path: Startup Initial State`.
- Host byte source and replay priority:
  `Worked Path: Host Byte Source Priority`.
- Parser records, dispatch tables, delayed payloads, ignored rows, and
  parser artifacts:
  `Worked Path: Command Record And Payload Dispatch`,
  `Worked Path: Explicit No-Output Parser Rows`.
- Host/status side channels with no direct page-object effect:
  `Worked Path: Host Interface Output FIFO And Model-ID Backchannel`,
  `Worked Path: Page Environment Status Bridge`,
  `Worked Path: External Ready Service Preemption`.
- Text, controls, cursor placement, and transparent/display byte readers:
  `Worked Path: Printable Glyph`,
  `Worked Path: Text Source Objects And Compact Buckets`,
  `Worked Path: Mixed Direct Controls`,
  `Worked Path: Cursor And Margin Placement`,
  `Worked Path: Text Span Flush And Fixed-Width Spans`,
  `Worked Path: Transparent Print Data`,
  `Worked Path: Display Functions Direct Reader`.
- Font selection, downloaded glyphs, macro replay, and resource boundaries:
  `Worked Path: Page Font Scheduler Resource Handoff`,
  `Worked Path: Built-In Resource Scan And Candidate Windows`,
  `Worked Path: Font Selection To Visible Glyphs`,
  `Worked Path: Pitch Mode To Font Refresh`,
  `Worked Path: Firmware Font Sample Page`,
  `Worked Path: Selected Font Metrics To Span Output`,
  `Worked Path: Downloaded Glyph`,
  `Worked Path: Downloaded Glyph Rule/Raster Composition`,
  `Worked Path: Nonzero Resource Payload`,
  `Worked Path: Fixed-Record Resource Object`,
  `Boundary: Short Compact Downloaded-Glyph High Rows`,
  `Boundary: Downloaded-Glyph Wrapped Width Low Bytes`,
  `Boundary: Segmented-Wide Downloaded-Glyph Fallback Source`,
  `Boundary: Downloaded-Glyph Payload Count Cap`,
  `Worked Path: Macro Execute Replay`,
  `Worked Path: Macro Overlay Replay Publication`,
  `Boundary: Secondary Segment-57 Source`.
- Page publication, page environment changes, and active render scheduling:
  `Worked Path: Reset And Default Environment`,
  `Worked Path: FF Publication`,
  `Worked Path: Publication Commands To ROM-Derived Page Rows`,
  `Worked Path: Page Length, Wrap, And Perforation Controls`,
  `Worked Path: Shared Page-Record Storage And Allocator`,
  `Worked Path: Published Record To Active Bands`,
  `Worked Path: Mixed Text/Rule/Raster Page Record`,
  `Worked Path: Compact Glyph Row-Copy Helpers`,
  `Worked Path: Render Dispatch And Pixel Composition`.
- Non-text page objects and render dispatch:
  `Worked Path: Vertical Forms Control`,
  `Worked Path: VFC Table And Channel Branch Matrix`,
  `Worked Path: Rectangle Rule`,
  `Worked Path: Rectangle Rule Selectors And Clipping`,
  `Worked Path: Raster Row`,
  `Worked Path: Raster Transfer Gates And Modes`.

Each worked path names the handlers, ROM fields, output effect, field
classification, evidence files, and unresolved boundary for that slice.

## Worked Path: Startup Initial State

This path covers the ROM-defined initial state that exists before the first
host byte reaches `0xa904`. It is not a PCL command path and does not draw
pixels. It matters because byte-stream reproduction depends on the empty
host-input buffers, output FIFO, heap allocator, render work records, wait
objects, and resource-window bounds that later parser and imaging paths
consume.

Reset and early setup:

- Reset vector PC is `0x00000110` and initial SSP is `0x00800000`.
- Reset entry `0x0110` masks interrupts, issues 68000 `RESET`, delays, and
  writes early MMIO defaults including `$a200 = 0`, `$fffe0001 = 3`,
  `$aa01 = 0xf1`, `$a601 = 0`, and `$a801 = 0x7e`.
- Startup helper `0x0298` copies 62 six-byte `JMP absolute long` stubs from
  ROM table `0x04c0` into RAM trampoline range `0x780000..0x780173`.
- The startup then runs RAM/config/resource tests and setup helpers before the
  scheduler ring starts at `0x0c24`.

Renderer-relevant initialized state:

- `0x2c84` enters the default-environment producer cluster, bulk-reads retained
  default records through `0x5a16` / `0x97e4`, loads the active default record
  through `0x5f96`, and seeds environment bytes `0x780e44..0x780e58`.
- `0x0b18` computes heap and resource-window bounds. With the observed reset
  defaults it writes heap start `0x780efa = 0x783f4a`, heap byte count
  `0x780efe = 0x000640b6`, resource/window base `0x7810b4 = 0x007e8000`,
  and resource/window size-minus-two `0x7810b8 = 0x00017ffe`.
- `0x164a` initializes the heap allocator: free-unit count `0x780e86`,
  bitmap-base pointer `0x783972 = 0x784906`, payload-base pointer
  `0x783988 = 0x784c40`, and low/high scan fields consumed by allocation
  helpers `0x170c`, `0x1710`, and `0x18b4`.
- `0x2feb6` initializes render work selector state by writing
  `0x7820bc = 1` and `0x7820c0 = 1`, then clearing work header words
  `0x7820c8` and `0x78212c`.
- `0x3178` initializes host byte-source buffers: ring count `0x783e54`,
  second LIFO count `0x783e76`, and first LIFO count `0x783e8c` are cleared;
  ring pointers `0x783e56` / `0x783e5a` are set to `0x783a4c`; ring
  low-water threshold `0x783e5e = 0x40`; sequence cursor
  `0x783e62 = 0xa8a4`; write-pointer mirror `0x7821c4 = 0x783a4c`; LIFO
  pointers `0x783e78 = 0x783e66` and `0x783e8e = 0x783e7c`.
- `0x31d6` initializes the 64-byte host-output FIFO by clearing count
  `0x783ed2` and setting read/write pointers `0x783ed4` and `0x783ed8` to
  `0x783e92`.
- Scheduler bootstrap `0x0c24` builds eight wait-object records
  `0x780182..0x780262` from table `0x15d0`, installs priorities, private
  stacks, restart PCs, and closes the scheduler ring before entering priority
  switch `0x1266`.

State classification:

- Canonical startup state:
  default-environment bytes `0x780e44..0x780e58`, heap fields `0x780efa`,
  `0x780efe`, `0x780e86`, `0x783972`, and `0x783988`, host input fields
  `0x783e54..0x783e8e` plus `0x7821c4`, output FIFO fields
  `0x783ed2`, `0x783ed4`, and `0x783ed8`, and wait-object ring records
  `0x780182..0x780262`.
- Derived/cache state:
  MMIO shadows `0x7828fa`, `0x7828f9`, and `0x7828f6`; timer divider seeds
  `0x78017f`, `0x780180`, and `0x780181`; startup resource bounds
  `0x7810b4` / `0x7810b8`; render work selector/header fields
  `0x7820bc`, `0x7820c0`, `0x7820c8`, and `0x78212c`.
- Parser scratch:
  none in this startup block. Parser records and payload scratch are reset
  later by parser/reset paths such as `0xe146`, `0x11774`, and `0x12218`.
- Firmware bookkeeping:
  RAM trampoline stubs `0x780000..0x780173`, startup-test gate `0x783eee`,
  scheduler private-stack frames, wait-object priorities, and retained-record
  dirty/readback buffers.
- Hardware/external state:
  early MMIO and strap inputs behind `$8000`, `$8c01`, `$ff8000`, `$a200`,
  `$a400`, `$a601`, `$a801`, `$aa01`, `$fffe0001`, `$fffe0003`,
  `$ffff1020`, `$ffff2000`, and `$ffff3800`.
- Unknown:
  physical names and electrical timing for those MMIO devices remain
  board-level work. The software ownership of the initialized parser,
  allocator, byte-source, FIFO, scheduler, and render-work state is not open
  in this checkpoint.

Output effect:

- Startup does not allocate page roots, queue page objects, publish pages, or
  render rows.
- Its reproduction effect is initial state. `Worked Path: Host Byte Source
  Priority` depends on `0x3178`, `Worked Path: Model-ID And Status
  Backchannel` depends on `0x31d6`, `Worked Path: Shared Page-Record Storage
  And Allocator` depends on `0x164a`, and `Worked Path: Published Record To
  Active Bands` depends on `0x2feb6` and the `0x0c24` wait-object ring.

Evidence:

- Detail note: [firmware-startup.md](firmware-startup.md).
- Disassembly evidence:
  `generated/disasm/ic30_ic13_startup_memory_probe_00073a.lst`,
  `generated/disasm/ic30_ic13_startup_memory_tests_0008a2.lst`,
  `generated/disasm/ic30_ic13_heap_allocator_init_00164a.lst`,
  `generated/disasm/ic30_ic13_startup_render_work_init_02feb6.lst`,
  `generated/disasm/ic30_ic13_startup_byte_source_init_003178.lst`,
  `generated/disasm/ic30_ic13_startup_status_ring_init_0031d6.lst`,
  `generated/disasm/ic30_ic13_trampoline_handlers_000c7e.lst`, and
  `generated/disasm/ic30_ic13_scheduler_trap_handlers_00110c.lst`.
- Generated table evidence:
  `generated/analysis/ic30_ic13_vectors.txt` and
  `generated/analysis/ic30_ic13_startup_tables.txt`.

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
- frame `+0x08`: stride/offset byte, observed as `4` for covered frames.
- frame `+0x09`: covered frame kind: execute `2` from `0xe418`, call `3`
  from `0xe418`, or non-replay page-finalization/overlay frame `4` from
  `0xe4f4`.
- frame `+0x0a`: execute/call environment snapshot pointer, or zero for the
  non-replay frame.

The data-chain byte-source handoff is therefore a parser input mechanism, not
a separate command interpreter. Execute and call frames replay stored bytes
through the same parser and page-object paths as live host bytes; the
non-replay frame is consumed by the page-finalization/overlay machinery
documented in [macro-data-chain.md](macro-data-chain.md). The only open frame
layout edge at this layer is whether any ROM producer writes a frame kind
outside observed `+0x09` values `2`, `3`, and `4`.

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

## Worked Path: Shared Page-Record Storage And Allocator

This path is the common page-object storage boundary beneath text, raster,
rectangle/rule, span flush, publication, and render bridge paths. It documents
one state block with multiple writers and consumers before any object renderer
writes pixels. The detailed storage contract and fixture ledger are in
[page-record-storage.md](page-record-storage.md); the unified semantic ledger is
`Shared Page-Record Storage And Allocator` in
[semantic-state-model.md](semantic-state-model.md).

Producer entry points:

- `0xd04a` resolves printable text and queues compact entries through
  `0x12f2e` / `0x1387c`.
- `0x12714` flushes pending spans. Portrait spans queue segment-list bucket
  objects under root `+0x1c`; landscape spans queue fixed-list objects through
  `0x136d2` under root `+0x28`.
- `0x105d0` consumes delayed `ESC *b#W` raster payload bytes and queues
  encoded-span bucket objects through `0x13070` / `0x13250`.
- `0x10898` completes rectangle/rule commands and inserts ordered rule nodes
  through `0x10b80`, `0x13386`, and `0x133aa`.

All four families converge on the current page root:

- `0x10084` ensures root pointer `0x78297a`. When a root is missing it
  allocates one, marks byte `+4 = 1`, seeds `0x782a72 = root + 0x20`, calls
  initializer `0x10110`, clears `0x782990`, and zeroes the bucket-head array
  at root `+0x1c`.
- `0x10110` initializes page code, status/flag fields, dimension and band
  fields, list heads, and selected current-font context slot `+0x2c`.
- `0x1381c` owns variable-size stream allocation. It updates stream
  bookkeeping `0x782a70`, `0x782a72`, and `0x782a76`; when it needs a new
  0x100-byte chunk, it links that chunk through the prior `0x782a72` target.
- `0x1387c` links or reuses compact/raster bucket objects under root `+0x1c`.
- `0x13386` derives rule key state through `0x134d6`, then `0x133aa`
  links rule objects under root `+0x24`. For nonempty lists, helper
  `0x13472` compares existing object byte `+4` with key `0x782a7c` and
  returns one of three link cases: insert after predecessor, append after
  tail, or insert at head. The new object stores byte `+4` from `0x782a7d`,
  ORs selector bits into byte `+5`, stores key word `+6` from `0x782a7e`,
  and copies width/height from source words `+4/+6`.
- `0x1366c` derives fixed-list state through `0x137a2`, then `0x136d2`
  links fixed-list objects under root `+0x28`. For nonempty lists, helper
  `0x13690` searches before allocation, returning the predecessor before
  the first object whose byte `+4` exceeds key `0x782a7c`, or the tail when
  the tail byte is less than or equal to the key. `0x136d2` then allocates
  the 14-byte object and links at head, after predecessor, or after tail.
  The new object stores byte `+4` from `0x782a7d`, byte `+5` from normalized
  source byte `+1`, key word `+6` from `0x782a7e`, and extent word `+8`
  from source word `+6`.

Page-object class handoff matrix:

- Compact text and downloaded-glyph objects:
  producers `0xd04a -> 0x12f2e -> 0x1387c`; current-root field `+0x1c`;
  render-root field `+0x18`; bucket class byte `+0x04` in `0x00..0x3f`.
  Render dispatch is `0x1efc2 -> 0x1effe`, then compact helper
  `0x1f034`, `0x1f0d2`, `0x1f1f0`, or `0x1f264` depending on selector bits.
  Output rows come from source glyph/resource bytes resolved through
  `0x1f354` and row-copy helpers.
- Portrait text-span segment-list objects:
  producers `0x12714 -> 0x13520/0x135f0`; current-root field `+0x1c`;
  render-root field `+0x18`; bucket class byte `+0x04` in `0x40..0x7f`.
  Render dispatch is `0x1efc2 -> 0x1f812 -> 0x1f862`. Output rows are span
  masks and full words derived from the queued segment entries, not from
  parser scratch.
- Encoded raster span objects:
  producers `0x105d0 -> 0x13070 -> 0x13250`; current-root field `+0x1c`;
  render-root field `+0x18`; bucket class byte `+0x04` in `0x80..0xff`.
  Render dispatch is `0x1efc2 -> 0x1f88e`. Object byte `+0x05 & 3` selects
  literal or expansion mode helpers, and the queued payload bytes produce the
  rendered raster rows.
- Rectangle/rule objects:
  producers `0x10898 -> 0x10b80 -> 0x13386 -> 0x133aa`; current-root field
  `+0x24`; render-root field `+0x1c`; list order is the `0x13472` search
  result described above; object byte/key fields are `+0x04/+0x06`.
  Render dispatch is `0x1f446`, which sends bridged selector `7` to solid
  helper `0x1f596` and other documented selectors to patterned helper
  `0x1f4e0`.
- Fixed-list and landscape span objects:
  producers `0x12714 -> 0x136d2` or fixed-list command paths; current-root
  field `+0x28`; render-root field `+0x20`; list order is the `0x13690`
  predecessor/tail search result described above; fixed-list fields are
  `+0x04..+0x0d`. Render dispatch is `0x1f756`, gated on five-band
  boundaries, then row writing through `0x1f7b0` / `0x1f626`.

The chunk-rollover fixture proves these producers are one shared allocator,
not separate command-local stores. In
`addressed page-record writers share 0x1381c across chunk rollover`,
`0x10084` seeds `0x782a72 = root + 0x20`; seven compact writers through
`0x12f2e` / `0x1387c` allocate objects at `0x00d05004`,
`0x00d0502a`, `0x00d05050`, `0x00d05076`, `0x00d0509c`,
`0x00d050c2`, and `0x00d05104`; then `0x133aa` and `0x136d2`
allocate rule/fixed objects at `0x00d0512a` and `0x00d05138`. The stream
links are `root + 0x20 -> 0x00d05000 -> 0x00d05100`, and final stream
bookkeeping is `0x782a70 = 0x00ba`, `0x782a72 = 0x00d05100`, and
`0x782a76 = 0x00d05146`.

Field classification:

- Canonical page state:
  current root `0x78297a`; root `+0x1c` bucket heads; root `+0x20` stream
  chunk chain; root `+0x24` rule list; root `+0x28` fixed list; root
  `+0x2c..+0x68` context slots; compact/raster, segment-list, rule, and
  fixed-list object headers and payload bytes allocated through `0x1381c`.
- Derived/cache state:
  producer keys `0x782a7a..0x782a7e`; render-band outputs `0x783a20`,
  `0x783a22`, and `0x783a28`; destination/cache fields written by the
  bridge and later consumed by render dispatch.
- Parser scratch:
  six-byte command records, delayed-payload snapshots, and direct-reader
  byte counts before the producer call. Once `0x12f2e`, `0x13070`,
  `0x133aa`, or `0x136d2` has queued an object, the queued page object no
  longer depends on the parser scratch that led to it.
- Firmware bookkeeping:
  stream cursors `0x782a70`, `0x782a72`, and `0x782a76`; pending first-root
  latches `0x782c72` / `0x782c73`; transient byte `0x782990`; publication
  flag `0x782996`; root state byte `+4`.
- Hardware/external state:
  none for the ROM-local allocator and bridge contract.
- Unknown:
  no unresolved ROM-local middle edge remains for the listed root fields,
  stream accounting, local no-room returns, publication fields, or
  render-bridge root copies. Remaining work starts from new byte streams that
  expose a different object shape, continuation state, or rendered row.

Publication and render handoff:

- `0xff1e` consumes the current root, publishes it into the page/control pool,
  sets `0x782996`, writes published root state, and clears `0x78297a`.
- `0x1ed84` selects the active source record from scheduler state and seeds
  render-record header words.
- `0x1edc6` copies root `+0x1c` to render `+0x18`, root `+0x24` to render
  `+0x1c`, root `+0x28` to render `+0x20`, and context slots
  `+0x2c..+0x68` to render `+0x24..+0x60`.
- `0x1edc6` then converts copied rule and fixed-list nodes into render-time
  continuation state. The rule loop at `0x1edf4..0x1ee0e` walks render
  `+0x1c`, marks each rule byte `+0x05 |= 0x10`, and copies height word
  `+0x0a` into remaining-row word `+0x0c`. The fixed-list loop at
  `0x1ee10..0x1ee5e` walks render `+0x20`, marks each fixed byte
  `+0x05 |= 0x10`, copies extent word `+0x08` into remaining-row word
  `+0x0a`, and initializes bytes `+0x0c = 1` and `+0x0d = 8`.

Output effect:

- The allocator itself draws no pixels. It determines the object collections,
  object ordering, and page/context roots later consumed by the render
  dispatcher.
- Fixture `addressed text/rule/raster field groups reach publication and
  render entry` proves compact text, a selector-7 rule, and a mode-0 raster
  row share one addressed page record, publish through `0xff1e`, bridge
  through `0x1ed84` / `0x1edc6`, and enter render dispatch through
  `0x1ef6a`.
- Fixtures `0x133aa no-room return preserves rule-list head` and
  `0x136d2 no-room return preserves fixed-list head after search` prove
  failed allocation leaves the prior visible rule/fixed lists intact for
  later publication.

Evidence:

- Detail note: [page-record-storage.md](page-record-storage.md).
- Semantic ledger: `Shared Page-Record Storage And Allocator` in
  [semantic-state-model.md](semantic-state-model.md).
- Generated analysis:
  `generated/analysis/ic30_ic13_page_root_allocation.md`,
  `generated/analysis/ic30_ic13_page_root_references.md`,
  `generated/analysis/ic30_ic13_compact_bucket_allocator.md`, and
  `generated/analysis/ic30_ic13_page_record_bridge.md`.
- Disassembly:
  `generated/disasm/ic30_ic13_page_root_allocate_010084.lst`,
  `generated/disasm/ic30_ic13_display_list_helpers_013386.lst`,
  `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`,
  `generated/disasm/ic30_ic13_raster_object_queue_013070.lst`,
  `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`, and
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`.

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

Rule and fixed-width lists are not simple pass-through roots. Bridge helper
`0x1edc6` mutates the copied render nodes before renderer dispatch:

- rule nodes under render `+0x1c`: `0x1edf4..0x1ee0e` marks byte
  `+0x05 |= 0x10` and copies height word `+0x0a` to continuation word
  `+0x0c`;
- fixed-list nodes under render `+0x20`: `0x1ee10..0x1ee5e` marks byte
  `+0x05 |= 0x10`, copies extent word `+0x08` to continuation word `+0x0a`,
  and sets bytes `+0x0c = 1` and `+0x0d = 8`.

Compact bucket roots and context slots are mostly pass-through. The bridge
contract is documented in
[page-record-storage.md](page-record-storage.md) and
`generated/analysis/ic30_ic13_page_record_bridge.md`.

Reproduction rule:

- Treat the current page root as a per-page display list, not a bitmap. Host
  bytes and command handlers append or mutate page objects under root
  `+0x1c`, `+0x24`, and `+0x28`; they do not allocate a full-page raster
  surface while parsing.
- Treat `0xff1e` as the page snapshot boundary. After publication the
  authoritative page image is the page/control pool record selected through
  `0x780ea6` / `0x780eaa`, not the cleared current-root pointer
  `0x78297a`.
- Treat `0x1ed84` / `0x1edc6` as the render-record bridge. A renderer must
  copy bucket roots, rule/fixed roots, and context slots before deriving
  pixels; compact glyph bytes alone are not enough because `0x1effe` resolves
  resources through the copied context slots.
- Treat `0x1eba4` and `0x1ef6a` as band selection and band rendering. The ROM
  renders selected band words from the published display list into the current
  band/fallback buffers using `0x783a20`, `0x783a22`, and `0x783a28`; vertical
  coordinates choose buckets, segments, and fallback splits rather than causing
  a parser-time full-page bitmap allocation.

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

Render-band setup is explicit arithmetic, not an opaque scheduler state.
At `0x1ef86..0x1efc0`, helper `0x1ef86` loads render work word `+0x10`,
adds word `+0x08`, subtracts word `+0x0a`, and divides the result by word
`+0x06` with unsigned word division. It stores the division remainder in
`0x783a22`, stores `(word +0x06 - remainder) << 4` in `0x783a20`, and stores
`long +0x00 + ((remainder << 6) * word +0x04)` in both `0x783a28` and render
work long `+0x12`. The following bucket dispatcher `0x1efc2` indexes render
root `+0x18` by active band word `+0x10`, so these derived fields control
where the selected bucket/list objects write pixels in the current band.

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

Host-source to parser-result matrix:

- Service retry and no-byte gate:
  `0xa904` first runs `0x10cc(0x780202)` and retries if service byte
  `0x7821cd` is set. If buffered-source byte `0x780e66` and gate byte
  `0x780e3b` are both set, it returns `D7 = -1` before consuming queued
  bytes. Parser wrappers and payload readers see this as no byte; no parser
  record or page object is produced by this branch.
- First pushback stack:
  count `0x783e8c` and pointer `0x783e8e` win over data-chain, second
  pushback, ring, and direct hardware sources. The returned byte is
  parser-visible exactly as if it came from the host stream; consumers such as
  `0xda9a`, direct readers, or payload handlers own any later normalization.
- Active data-chain frame:
  pointer `0x782d76` wins after the first pushback stack. Frame `+0x00`
  supplies payload bytes, frame `+0x04` supplies count or `-1` end marker,
  byte `+0x08` is the observed stride/offset value, byte `+0x09` classifies
  execute, call, or overlay/non-replay frames, and longword `+0x0a` holds the
  execute/call snapshot pointer. End markers call `0xe22c` and retry; normal
  bytes re-enter the same parser paths as live host bytes.
- Second pushback stack:
  count `0x783e76` and pointer `0x783e78` win after data-chain frames. This
  path has the same parser-visible effect as the first pushback stack but a
  lower source priority.
- Ring-buffer input:
  when selector byte `0x780e40` is zero, ring occupancy `0x783e54`, read
  pointer `0x783e56`, write pointer `0x783e5a`, and buffer
  `0x783a4c..0x783e53` supply live queued host bytes. The parser sees the
  returned byte in `D7`; the ring path is sufficient for deterministic
  byte-stream rendering from a fixed input.
- Direct hardware input:
  direct selector `0x780e40 == 1` polls `0x8e01` and reads `0x8801`; other
  nonzero selector values poll `0xfffee005` and read `0xfffee001`. The
  returned value is still just the next byte to parser callers. Register
  names, connector mapping, and timing are hardware/MMIO boundaries unless a
  live board interface is being modeled.

The source matrix has no page-output effect by itself. Its output is either a
parser-visible byte in `D7` or `D7 = -1`. Pixel-producing behavior begins only
after callers such as `0xda9a`, `0x11774`, direct-reader loops, delayed
payload handlers, or macro replay consumers interpret the byte.

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
  `0xfffee001`, `0xfffee005`, and `0xfffee009`. The only ROM-local
  data-chain layout uncertainty in this byte-source checkpoint is an
  unlocated producer for a frame kind outside observed `+0x09` values `2`,
  `3`, and `4`; the covered execute, call, and non-replay frame producers
  and consumers are owned by [macro-data-chain.md](macro-data-chain.md).

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

Delayed-payload family matrix:

- `ESC *b#W` / `w` raster row:
  arming path `0x11f82 -> 0x121cc`, restored handler `0x105d0`.
  The handler reads absolute count from record `+2`, consumes payload bytes
  through the payload reader, updates raster block `0x783170`, and queues
  encoded-span objects through `0x10084 -> 0x13070 -> 0x13250`. Render
  ownership is `Worked Path: Raster Row` and `Worked Path: Raster Transfer
  Gates And Modes`.
- `ESC &p#X` / `x` transparent print data:
  arming path `0x11f5a -> 0x121cc`, restored handler `0x12452`.
  The handler reads absolute count from record `+2`, routes payload bytes
  through transparent filtering, and either feeds fixed-space/control handling
  or ordinary printable text object production. Owner is
  `Worked Path: Transparent Print Data`.
- `ESC &l#W` / `w` VFC table load:
  arming path `0x11f6e -> 0x121cc`, restored handler `0x12cfe`.
  The handler reads table byte count from record `+2`, copies channel rows
  into `0x782dde..0x782edd`, derives channel presence/cache fields, and is
  later consumed by `ESC &l#V`. Owners are `Worked Path: Vertical Forms
  Control` and `Worked Path: VFC Table And Channel Branch Matrix`.
- `ESC (s#W` / `ESC )s#W`, count `0`:
  arming path `0x11f96 -> 0x121cc`, restored handler `0x15d0a`.
  The handler interprets the following descriptor/current-record grammar,
  writes descriptor budget `0x783140`, fixed-record/current resource state,
  and later source records consumed by printable glyph output. Owner is
  `Worked Path: Fixed-Record Resource Object`.
- `ESC (s#W` / `ESC )s#W`, nonzero count:
  arming path `0x11f96 -> 0x121cc`, restored handler `0x16c14`.
  The handler stores payload budget in `0x783140`, validates/downloads
  descriptor or glyph bytes, installs resource candidates or
  downloaded-character records, and leaves printable bytes to create page
  objects through `0xd04a -> 0x12f2e`. Owners are
  `Worked Path: Downloaded Glyph` and `Worked Path: Nonzero Resource Payload`.
- Generic stateful-helper `W/w` payload:
  arming path helper-specific `0x121cc(0x1228a)`, restored handler
  `0x1228a`. The handler rewinds to the restored record, drains the absolute
  byte count through `0x12328` / `0xdace`, and does not echo bytes as printable
  input. In alternate/data mode `0x12358` either delegates here or appends
  payload bytes to the data chain.

Alternate/data-mode contrast:

- Alternate/data mode is selected by byte `0x782c18`.
- The alternate pointer table at `0x116f6` keeps enough syntax to collect
  command records and stop macro definitions, but many normal side effects
  are suppressed.
- Immediate page-state commands mostly have blank alternate/data handlers:
  cursor/layout controls, selected-font update terminals, rectangle setters,
  raster-control setters, and dot-position commands parse without mutating
  their normal canonical fields. Lowercase chaining finals mostly reach
  `0x11f4c`, which rewinds `0x78299e` so command-family syntax can continue.
- Payload/storage commands remain active where stored input needs exact bytes:
  `ESC &p#X` / `x`, `ESC &l#W` / `w`, `ESC *b#W` / `w`,
  `ESC (s#W` / `w`, `ESC )s#W` / `w`, and macro control
  `ESC &f#X` / `x`.
- `ESC E` still reaches reset handler `0xcc52`; alternate/data mode does not
  shield parser or page state from an explicit reset command.
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

## Worked Path: Host Interface Output FIFO And Model-ID Backchannel

This path covers the host-interface output FIFO, its status-byte worker, and a
parser-visible command that produces host/interface output instead of page
objects. It belongs in the dataflow model because a bidirectional host can
react to these bytes and change the later stream that reaches `0xa904`, even
though the ROM does not draw pixels for the response.

The primary response stream is:

```text
ESC *r1K 0x11
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

Host/status side-channel matrix:

- Model-ID/backchannel command:
  parser wrapper `0x12034 -> 0x122be..0x12326` consumes command state and
  query byte `0x11`; accepted queries enqueue literal `33440A\r\n` through
  `0xb090`. Output is host-visible FIFO data only. It creates no page root,
  page object, publication record, or render work record.
- FIFO enqueue and drain:
  producers `0xb0c0` / `0xb090` write FIFO count/pointers
  `0x783ed2/0x783ed4/0x783ed8` and storage `0x783e92..0x783ed1`; worker
  `0xae2c` drains through `0xb022` and output helpers `0xaf7c` or
  `0xafcc` depending on backend selector `0x780e40`. Output is physical host
  interface data, with `0xb090` able to stall while the FIFO is full.
- Status-byte worker:
  `0xaece` consumes pending status count `0x780e22`, bridge-service byte
  `0x783e61`, reason byte `0x783e60`, aggregate words `0x780e12`,
  `0x780e0a`, warning/status accumulator `0x780e2a`, and page-environment
  flag `0x780e90`. Output is a host-visible status/service byte, not page
  imaging.
- Page-environment status bridge:
  helper `0x2888` consumes selected page/control-pool record bytes from
  `0x780eaa`, writes `0x780e8f`, `0x780e90`, `0x780e98`, and
  `0x780e2a.4`, and feeds both `0xaece` status bytes and panel/service paths
  under `0x7612..0x7834`. Output is host status or panel/service state.
- External-ready/service preemption:
  loop `0xba48..0xc36e` consumes external MMIO state, can display
  `01 EXT READY` or service messages, can publish status bits, and can block
  or defer normal parser progress. It does not allocate page roots or enter
  bitmap render dispatch.

For fixed host-byte pixel reproduction, these side channels are no-page-output
unless a modeled bidirectional host reacts by sending different later bytes or
the service loop prevents bytes from reaching `0xa904`. For a board-level
emulator, their FIFO timing, status bytes, panel messages, and MMIO identities
are observable firmware behavior.

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
  by configured output mode`,
  `0x12034/0x122be model-ID response emits FIFO literal`, and
  `0x2888 sets page-environment status consumed by 0xaece`.
- The unresolved edge is external naming and timing: the protocol name for
  query byte `0x11`, physical output-register mapping, and whether a
  particular host script consumes these backchannel bytes.

## Worked Path: Page Environment Status Bridge

This path covers the bridge from a selected page/control-pool record into
host-visible status and panel/service messages. It does not create page
objects or pixels, but it matters to byte-stream reproduction because the same
state is visible through output worker `0xae2c` / `0xaece` and through the
page-pool cursor service path at `0x7612..0x7834`.

Producer and cleanup behavior:

- Helper `0x2888` is the primary producer. It compares the selected scheduler
  record at `0x780eaa` against active page-environment byte `0x780e8e`.
- `0x2888` only evaluates selected records whose state byte `+4` is `2` or
  `3`, and it exits early when active-pool attention/status flag `0x780e6d`
  is set.
- The selected record bytes observed here are `+6` as status candidate, `+7`
  as page-environment candidate, and `+8` as service-needed byte.
- On the mismatch/publication path, `0x2a14` copies selected byte `+7` to
  `0x780e8f` and sets `0x780e29.0`.
- On the active high-bit path, `0x2888` sets page-environment status flag
  `0x780e90`, copies selected byte `+6` to cache byte `0x780e98`, and sets
  warning/status accumulator bit `0x780e2a.4` through `0x9bee`.
- Helper `0x29b2` is the status-cache fallback writer. It writes `0x780e98`
  from its argument byte and then sets either `0x780e29.3` when `0x780e02`
  and `0x780e91` allow that path, or `0x780e30.0` otherwise.
- Helper `0x2a38` sets service-pending byte `0x7839d3`, calls `0xa5c2`, and
  clears `0x780e90` when its predicates allow service.
- Cleanup `0x2c08..0x2c3a` clears `0x7839d2`, may call `0x2c44`, clears
  `0x7839d3`, calls `0xa5da`, and clears `0x780e90`.

Host/status consumers:

- Status-byte builder `0xaece` consumes `0x780e90` as bit `0` of the
  outbound base `0x30` status byte. The same byte also includes bit `1` from
  `0x780e2a`, bit `2` from `0x780e0a`, and ORed reason byte `0x783e60`.
- Page-pool cursor service `0x7612..0x7834` consumes `0x780e90` as the
  selector between media-feed formatter `0x8a48` and normal service-message
  selector `0x8656`; its `0x77b0` path can also clear `0x780e90`.
- Copied-stub handler `0x0d12..0x0d24` consumes and clears service-pending
  byte `0x7839d3`.

Panel/message consumers:

- Media-feed formatter `0x8a48` consumes `0x780e8e` and `0x780e98`.
  When `0x780e8e == 0x80`, high bit set in `0x780e98` selects `PE FEED`
  (`0xb291`) through `0x9112`; clear selects `PF FEED` (`0xb280`) through
  `0x9112`.
- When `0x780e8e == 0x90`, high bit set in `0x780e98` again selects
  `PE FEED`; clear selects `PE FEED ENVELOPE` (`0xb2a2`) through `0x8c90`.
- Normal service-message selector `0x8656` maintains toner/service latch
  `0x780e3e`, writes next poll deadline `0x7822e6 = 0x780e04 + 0x65`, and
  dispatches service/self-test strings through selector byte `0x780e8a` and
  related flags.
- Display/message wrappers `0x8c7a` and `0x8c90` call `0x9182` with mode
  arguments `0` and `1`. Formatted message helper `0x9112` feeds the same
  display-message core.

State classification:

- Canonical page-environment state: active page-environment byte `0x780e8e`,
  output page-environment byte `0x780e8f`, and selected record bytes `+6`,
  `+7`, and `+8` from the record selected by `0x780eaa`.
- Derived/cache status: page-environment status flag `0x780e90`, status-code
  cache `0x780e98`, warning/status bit `0x780e2a.4`, service-pending byte
  `0x7839d3`, toner/service latch `0x780e3e`, service selector `0x780e8a`,
  and next service poll deadline `0x7822e6`.
- Parser scratch: none. This path is not entered from the PCL parser tables.
- Firmware bookkeeping: gates `0x780e6d`, `0x780e02`, and `0x780e91`; latch
  bits `0x780e29.0`, `0x780e29.3`, and `0x780e30.0`; message buffers
  `0x78292c..0x78293c` and `0x78293d..0x78294d`; message state bytes
  `0x78296c`, `0x78296d`, `0x78296e`, `0x782970`, and `0x782971`; and the
  display helpers `0x8c7a`, `0x8c90`, `0x9112`, and `0x9182`.
- Hardware/external state: service-strobe shadow bit `0x7828f9.2`, hardware
  byte `$a801`, and hardware/status byte `$8a01`.
- Unknown: user-facing names for selected record bytes `+6`, `+7`, and `+8`
  beyond the page-environment interpretation; physical signal names for
  `$8a01.5`, `$8a01.3`, and `$a801.2`; exact physical panel output after
  `0x9182..0x9406`; and the sensor names behind `0x6e32(0x1f)` and
  `0x6f32(0x2a)`.

Output effect:

- This path does not allocate page roots, page records, render work records,
  or bitmap rows.
- It affects host-visible output through `0xaece` status bit `0`, so a
  bidirectional host may react with different later bytes.
- It affects panel/service output through `0x8a48`, `0x8656`, `0x8c7a`,
  `0x8c90`, `0x9112`, and `0x9182`.
- For pixel reproduction from a fixed host byte stream, the path is a
  no-page-output side channel. For reproduction of a live bidirectional host
  session, the status byte and panel/service state are part of the observable
  firmware behavior.

Evidence and unresolved boundary:

- Semantic source: [semantic-state-model.md](semantic-state-model.md),
  section `Page Environment Status Bridge`.
- Disassembly evidence:
  `generated/disasm/ic30_ic13_page_environment_status_002888.lst`,
  `generated/disasm/ic30_ic13_page_status_cleanup_002c00.lst`,
  `generated/disasm/ic30_ic13_page_pool_cursor_007612.lst`,
  `generated/disasm/ic30_ic13_page_service_messages_008656.lst`,
  `generated/disasm/ic30_ic13_page_environment_message_008a48.lst`,
  `generated/disasm/ic30_ic13_message_dispatch_wrappers_008c7a.lst`,
  `generated/disasm/ic30_ic13_formatted_message_helper_009112.lst`,
  `generated/disasm/ic30_ic13_display_message_core_009182.lst`,
  `generated/disasm/ic30_ic13_8a01_a801_status_bits_00a42c.lst`,
  `generated/disasm/ic30_ic13_host_output_worker_00ae2c.lst`, and
  `generated/disasm/ic30_ic13_trampoline_handlers_000c7e.lst`.
- String evidence:
  `generated/analysis/ic30_ic13_strings.txt`, including `PF FEED`,
  `PE FEED`, `PE FEED ENVELOPE`, `16 TONER LOW`, `SERVICE MODE`, `UC`,
  `LC`, and self-test/font-print strings.
- Fixture evidence includes
  `0x2888 sets page-environment status consumed by 0xaece`,
  `0x2888 publishes environment mismatch or status-cache changes`,
  `0x7612 selects page-environment or normal service helper`, and
  `0x8a48 maps page environment bytes to media-feed messages`.
- Exact unresolved middle edges are `0x9112..0x9182` for full message
  formatter lifting, `0x9182..0x9406` for physical panel output, and
  `0x6e32(0x1f)` / `0x6f32(0x2a)` for physical sensor naming.

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
- The retained-storage status edges are now software-composed in
  [external-ready-service.md](external-ready-service.md): commit/readback
  failure writes `0x780e39.3` through `0x571e -> 0x9bee`, and `0xc1c6`
  consumes that bit as non-returning `68 SERVICE` through `0x85c0`; startup
  retained-record load reaches separate active-bank validation
  `0x5a16 -> 0x97e4 -> 0x56c2 -> 0x1284` and reports `67 SERVICE` when no
  active marker is found.
- The remaining exact boundaries are external: physical identity of the
  `$fffee00*`, `$a200`, and `$a801` register family; the physical
  retained-storage condition that makes commit/readback fail through all
  retries; the physical retained-storage contents that leave no active marker
  after startup readback; and a full board-level `0xba48` loop scenario that
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

Scheduler branch-to-consumer matrix:

- Both predicates zero:
  `0x19dd2` calls `0x19fb8(0)`, runs shared font/default refresh
  `0x1b04c`, and returns `D7 = 1`. It does not prune candidates, release
  downloaded-font payloads, rescan optional ranges, or replace canonical
  resource-window table `0x7828b6`.
- Status-return branch:
  when the first predicate is nonzero and `0x72a2` returns zero,
  `0x19e32..0x19e46` writes `0x780e8d`, raises status mask `0x00000200` at
  status root `0x780e2e` through `0x9bee`, calls `0x19fb8(predicate)`, and
  returns `D7 = 0`. This is a firmware/status side effect, not page output.
- Long-refresh branch:
  nonzero predicates outside the status-return branch call
  `0x1ba92(predicate)`, `0x178fa(predicate)`, `0x19d9c()`,
  `0x1a4fa(fresh_side_predicate)`, and `0x1a900()`, then return
  `D7 = 1`. This can remove candidate entries, release current downloaded
  payloads, mark remaining candidates dirty, rescan optional windows through
  `0x1a616`, validate active contexts, and commit scratch state to
  `0x7828b6`.
- Host-quiesce caller `0x447a`:
  ignores scheduler `D7`; only the side effects above can affect later
  parsing or font state.
- Host/menu caller `0x4760`:
  consumes scheduler `D7`; `D7 = 0` returns immediately, while `D7 != 0`
  enters menu/default setup and polling state.
- External-ready teardown caller `0xbb16`:
  records scheduler side effects but ignores `D7` before status aggregation
  through `0x36e4`.
- Font-resource scan caller `0x1a3c2`:
  ignores scheduler `D7`, then passes `0x78219b`, `0x78219c`, and local
  `A6-0x02` to resolver `0x1b50e`. Only resolver `D7 == 0` selects the
  following `0x6364` default refresh call.

The matrix output is refreshed resource/font state or status/caller control,
not pixels. Later visible output can change only when subsequent font
selection, downloaded-font resolution, resource lookup, or caller continuation
consumes the modified candidate, context, or status state.

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

## Worked Path: Built-In Resource Scan And Candidate Windows

This path covers how the verified `IC32,IC15` resource ROM becomes the
candidate windows that later font-selection commands consume. It does not draw
pixels by itself; its pixel effect is choosing which built-in context longword,
glyph map, metrics, and bitmap payloads printable text will use.

Resource scan and candidate producer:

- `0x1a2e4` clears candidate counters, seeds cursor windows at `0x782324`,
  sets built-in scan bounds `0x080000..0x0ffffe`, and calls `0x1a616`.
- `0x1a616` scans resource records and recognizes or skips signatures such as
  `HEAD`, `FONT`, `TABL`, `tabl`, and `DUMY`.
- Accepted font records are handed to `0x1a9be`, which writes candidate
  longwords, increments total count `0x78278e`, partitions records by class
  and address range, and advances cursor windows `0x7827a0..0x7827b4`.
- Fixture `0x41a HEAD scanner walks verified IC32/IC15 resource chain` pins
  the startup-visible typed-record chain that bounds this built-in window:
  24 typed records from firmware address `0x08004c` through `0x0ae122`,
  terminating at `0x0b2f80`.
- Fixture `actual IC32/IC15 built-in records feed 0x1a9be partitions` pins
  the decoded built-in scan result for candidate partitioning.

Candidate-window state:

- Canonical state includes candidate pointer-list base `0x782324`, total
  candidate count `0x78278e`, class/range counts `0x782790..0x78279e`,
  cursor windows `0x7827a0..0x7827b4`, active candidate window
  `0x78287c` / `0x7827b8`, selected candidate slot `0x7828a8`, and selected
  context records `0x782ee6` / `0x782ef6`.
- For the verified built-ins, class-one low/range counters are
  `0x782792 = 12` and `0x782794 = 0`; class-zero low/range counters are
  `0x78279a = 12` and `0x78279c = 0`.
- Final cursor windows are `0x7827a0 = 0x782324`,
  `0x7827a4 = 0x782354`, `0x7827a8 = 0x782354`,
  `0x7827ac = 0x782354`, `0x7827b0 = 0x782384`, and
  `0x7827b4 = 0x782384`.
- Fixture `0x1a616 candidate scan continuation policy changes built-in counts`
  constrains segment-57 continuation behavior: an `IC32,IC15` mirror at
  offset `0x40000` would double total count to `48`, while code-pair and
  zero-fill continuations preserve the verified `24` total.

Activation, filtering, and selection consumers:

- `0x1569c` activates the selected class window, writes `0x78287c` /
  `0x7827b8`, and sets candidate active bit `0x80000000`.
- `0x156de` filters active candidates by requested or fallback symbol words
  from parser-produced state. It reads resource symbol words through
  `0x15890` / `0x158be`.
- `0x1519a` filters requested height through decoded built-in heights from
  `0x13bca`; `0x153c6` filters spacing and pitch through resource byte
  `+0x21` and decoded pitch from `0x13b76`.
- `0x14398` and comparator `0x13c06` choose selected slot `0x7828a8` using
  resource window, decoded height, byte `+0x2f`, signed byte `+0x30`, and
  byte `+0x31`.
- `0x13eb8`, `0x144d2`, and `0x14c64` consume the selected candidate to write
  current context records and rebuild active glyph maps for printable text.
  Remaining font-selection work must change a concrete boundary in that chain:
  candidate windows `0x7827a0..0x7827b8`, selected slot `0x7828a8`, active
  symbol words `0x783144/0x783146`, selected context records
  `0x782ee6/0x782ef6`, active maps `0x782f32/0x783032`, snapshot keys
  `0x783148/0x783152`, page-root font slot/context fields, source-object
  fields, HMI/cursor advance, bridge context slots, or rendered rows.

Output effect:

- The scan changes pixels only through later font selection. For
  `ESC (s0p10h12v0s0b3T!!`, the verified candidate windows select primary
  slot `0x782354` and context `0xc008004c`.
- For `ESC )s0p16h8v0s0b0T SO !!`, the same candidate state selects
  secondary slot `0x782350` and context `0xc00ae122`.
- `0x1393a`, `0xd824`, `0x12f2e`, `0x1ed84`, and `0x1ef6a` then consume
  those selected contexts indirectly when printable bytes become compact
  objects and rendered rows.
- Resource glyph fixtures connect the canonical bitmap payloads to compact
  row-copy output for contexts `0x4008004c`, `0x44080418`, and `0x440946b4`.
  Fixture `line-printer built-in base map host 0x21 to glyph 32` pins the
  default Line Printer map used by the ordinary printable fixtures.

State classification for this path:

- Canonical state:
  built-in resource records, glyph-table entries, bitmap payloads, candidate
  pointer list `0x782324`, candidate counts/windows, active candidate window,
  selected slot `0x7828a8`, selected contexts, and active glyph maps.
- Derived/cache state:
  scan cursor `0x782884`, scan bounds `0x78288c` / `0x782890`, active symbol
  words `0x783144` / `0x783146`, fallback tables `0x782f0c..0x782f18`,
  default-symbol tables `0x782f1c..0x782f28`, HMI/cache values, and decoded
  height/pitch values.
- Parser scratch:
  requested symbol words `0x782ef4` / `0x782f04`, parsed font-selection
  request fields `0x782eec..0x782f06`, final-`X` transient font ID state, and
  final-`@` command records.
- Firmware bookkeeping:
  candidate active bit `0x80000000`, bit-30 built-in context flag, bit-26
  record-byte mirror, dirty refresh bytes `0x782f2c` / `0x782f2d`, and
  page-root context install state written after selection.
- Unknown:
  cartridge/external windows outside `0x080000..0x0ffffe` remain
  unverified, and manual-facing names for record metadata `+0x28..+0x31`
  remain inferred from decoded-height and chooser behavior.

Evidence for this path is in
[built-in-resource-scan.md](built-in-resource-scan.md),
[resource-rom.md](resource-rom.md),
[font-context-metrics.md](font-context-metrics.md), and
[semantic-state-model.md](semantic-state-model.md), section
`Built-In Resource Scan And Candidate Windows`. Key supporting reports and
listings are `generated/analysis/ic32_ic15_font_records.md`,
`generated/analysis/ic32_ic15_resource_glyph_probe.md`,
`generated/disasm/ic30_ic13_font_resource_scan_01a2e4.lst`,
`generated/disasm/ic30_ic13_font_candidate_classify_01a9be.lst`,
`generated/disasm/ic30_ic13_font_candidate_activate_01569c.lst`,
`generated/disasm/ic30_ic13_font_candidate_filters_01519a.lst`,
`generated/disasm/ic30_ic13_active_object_scan_014398.lst`, and
`generated/disasm/ic30_ic13_font_update_common_00c580.lst`.

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

## Worked Path: Text Source Objects And Compact Buckets

This path generalizes the single printable-glyph path above into the shared
source-object and compact-bucket producer used by flagged built-in text,
unflagged inline/downloaded text, transparent/display bytes that route as
printable characters, and downloaded glyph consumers.

Parser entry and shared source object:

- `0xd04a` receives the printable host byte in `D5` after parser loop
  `0x11774` finds no command-dispatch row for it.
- `0xd04a` normalizes over-`0xff` and high-bit byte cases, then calls
  `0x1393a(host_byte, 0x782d7e)`.
- Source object `0x782d7e` is canonical for this cluster. `0x1393a` writes
  the selected context pointer at `+0x00`, glyph or fixed-record pointer at
  `+0x04`, mapped compact glyph byte at `+0x0b`, and source-class flag at
  `+0x10`.
- Source flag `+0x10 = 0` selects the unflagged inline/downloaded route
  `0xd140 -> 0xd3b2`. Nonzero selects the flagged built-in route
  `0xd550 -> 0xd824`.
- Fixtures `0xd04a printable entry normalizes over-0xff and high-bit values`
  and `0xd04a high-character flags and selected slot choose mask behavior`
  pin the byte-normalization exits before the shared source object is built.

Positioning, precheck, and queue handoff:

- `0xd140` and `0xd550` run paired prechecks `0xd28a` and `0xd6bc`, write
  gate result `0x782a6e`, compute cursor advance, and commit current x
  `0x782c8a` only after queue and clamp handling.
- `0xd3b2` and `0xd824` both write positioned source fields `+0x12`,
  `+0x14`, and `+0x16`, set page-root live-font flag
  `0x78297f + 0x78297e`, and call `0x12f2e`.
- Fixture `0xd28a and 0xd6bc prechecks share continue reject and wrap decisions`
  proves the shared continue, reject, wrap-recovery, and vertical-extent
  outcomes before either writer queues an object.
- Fixture `0xd824-modeled positioned text source fields` pins the flagged
  built-in `LINE_PRINTER` case: host `0x21` maps to glyph `0x20`, glyph
  pointer `0x015330`, flag `1`, source x `16`, source y `0`, and slot `0`.
- Fixture `0xd3b2-modeled unflagged source fields` pins the unflagged case:
  host `0x21` maps to glyph `0x01`, record
  `02 03 04 00 00 00 00 80`, source x `22`, source y `22`, and slot `3`.

Compact object producer:

- `0x12f2e` consumes source pointer `+0x04`, mapped glyph `+0x0b`,
  source flag `+0x10`, positioned fields `+0x12/+0x14`, and context slot
  `+0x16`.
- It derives bucket index `0x782a7c`, compact coordinate/key fields,
  selector bits, and then calls `0x1387c` to allocate or reuse a compact
  bucket object under page-root `+0x1c`.
- Short objects use object size `0x26`, capacity `0x0a`, and entries
  `glyph, coord`. Segmented objects use object size `0x28`, capacity
  `0x08`, and entries `glyph, segment, coord`.
- Width above the compact threshold sets selector bit `0x1000`; tall rows set
  selector bit `0x2000`; width plus tall rows set selector `0x3000`.
- Fixture `addressed 0x12f2e selector-mode matrix allocates and renders all compact
  modes` pins the addressed storage and render dispatch for selector classes `0x0003`,
  `0x1003`, `0x2003`, and `0x3003`.

Page and render consumers:

- `0x1387c` stores compact objects in the current page-root bucket array
  `+0x1c`. Publication through `0xff1e` preserves those bucket heads in the
  published record.
- `0x1ed84` / `0x1edc6` copy the bucket roots and context slots into the
  active render record.
- `0x1ef6a` dispatches bucket chains through `0x1efc2`, and compact class
  bytes enter `0x1effe`.
- `0x1effe` selects short renderer `0x1f034`, compact-wide renderer
  `0x1f0d2`, segmented renderer `0x1f1f0`, or segmented-wide renderer
  `0x1f264`.
- Fixtures `compact text bucket object fixture rendered rows`,
  `constructed inline/downloaded wide glyph maps through 0x1f0d2`,
  `constructed inline/downloaded segmented glyph maps through 0x1f1f0`, and
  `constructed inline/downloaded segmented-wide glyph maps through 0x1f264`
  pin the renderer-facing rows for the selector classes.

No-room and retry behavior:

- `0xd3b2` and `0xd824` share the same queue no-room recovery shape. A failed
  `0x12f2e` allocation sets page-root retry flag `+0x14.0`, publishes the
  old root through `0xff1e`, ensures a fresh root through `0x10084`, and
  retries with the original source fields intact.
- Fixture `0xd3b2 and 0xd824 text queue no-room retry preserves source and rows`
  proves this for short flagged and unflagged sources.
- Fixture
  `0xd3b2 and 0xd824 segmented text queue no-room retry preserves source and rows`
  proves the same recovery for segmented/tall sources, including unflagged
  buckets `9/1` and flagged built-in buckets `64..0`.

State classification for this path:

- Canonical state:
  source object `0x782d7e`, selected font context, current cursor words
  `0x782c8a` / `0x782c8e`, page root `0x78297a`, context slot `0x78297e`,
  live-font flags `0x78297f + slot`, compact bucket objects, published bucket
  roots, and render-record bucket/context roots.
- Derived/cache state:
  precheck result `0x782a6e`, bucket index `0x782a7c`, compact coordinate and
  selector bits, glyph offsets, span watermarks `0x783186..0x78318a`, and
  render-band fields `0x783a20`, `0x783a22`, and `0x783a28`.
- Parser scratch:
  unmatched printable byte in `D5`, parser state byte `0x782999`,
  alternate/data mode `0x782c18`, high-character flags `0x783132` and
  `0x783133`, and temporary normalization result from `0xd99a`.
- Firmware bookkeeping:
  stream allocator cursors `0x782a70`, `0x782a72`, and `0x782a76`,
  page-root retry flag `+0x14.0`, publication flag `0x782996`, and
  scheduler/render progress fields after publication.
- Unknown:
  no unresolved middle edge remains for the documented source classes,
  selector modes, precheck outcomes, high-byte normalization cases, no-room
  retries, or compact renderer dispatch. Remaining work starts from byte
  streams that change source-object fields, selected-map results, HMI/cursor
  advance, compact selector class, bridge context slots, or rendered rows.

Evidence for this path is in
[semantic-state-model.md](semantic-state-model.md), section
`Text Source Objects And Compact Buckets`,
[font-context-metrics.md](font-context-metrics.md),
[page-record-storage.md](page-record-storage.md), and
[page-raster-imaging.md](page-raster-imaging.md). Key supporting reports and
listings are `generated/analysis/ic30_ic13_printable_text_path.md`,
`generated/analysis/ic30_ic13_text_cursor_span_flow.md`,
`generated/analysis/ic30_ic13_text_glyph_index_flow.md`,
`generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`, and
`generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`.

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
- The candidate windows consumed here come from the built-in resource scan
  `0x1a2e4 -> 0x1a616 -> 0x1a9be`. For the verified IC32/IC15 image, that
  scan contributes 24 `HEAD`-path font records, split into 12 class-zero and
  12 class-one low-window candidates.
- Primary refresh copies class-zero window `0x7827ac` / `0x782798` to active
  pointer/count `0x78287c` / `0x7827b8`, giving `0x782354` / `12`.
  Secondary refresh copies class-one window `0x7827a0` / `0x782790`, giving
  `0x782324` / `12`.
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
- For the verified built-ins, that active list is the concrete class-zero or
  class-one window above; [symbol-set-selection.md](symbol-set-selection.md)
  records the resulting non-Roman survivors and selected resource records.
- `0x14c64` rebuilds the selected map from either the bit-30 resource path
  `0x14d9c` or the bit-30-clear inline/downloaded path `0x14e24` /
  `0x14eb6`, then applies symbol patcher `0x14f16` and snapshot helper
  `0x1440c`.
- [symbol-map-patching.md](symbol-map-patching.md) documents the
  `0x14f16` map mutation: the selected font must normalize to Roman-8
  `0x0115`, after which active symbol words `0x783144` / `0x783146` select
  hard-coded `0E` / `0U` behavior or a `0x14fce` patch table.
- Primary fixture `ESC (1234U ESC (s0p10h12v0s0b3T!!` proves a requested
  symbol miss falls back to word `0x0115` before selecting the same primary
  context and rendering the same compact rows.
- Secondary fixture `ESC )1234U ESC )s0p16h8v0s0b0T SO !!` proves a class-one
  miss can recover through remembered word `0x000e` or fallback word
  `0x000e` before selecting the same secondary context.
- Non-Roman symbol-set streams `ESC (0N`, `ESC (10U`, and `ESC (11U` route
  through `0x120be` to symbol helper target `0x1c0a4`, then refresh through
  the same `0x13eb8` / `0x14c64` path. The primary visible fixture pairs
  those commands with `ESC (s0p10h12v0s0b3T!!`; the secondary fixture pairs
  `ESC )0N`, `ESC )10U`, and `ESC )11U` with
  `ESC )s0p16h8v0s0b0T SO !!`.
- For those non-Roman primary streams, selected contexts are `0xc0080cb8`,
  `0xc4080418`, and `0xc4080868`. The secondary streams select
  `0xc00ae122`, `0xc40ad87a`, and `0xc40adcce`. The rendered rows remain in
  the same primary and secondary digest families as the ordinary visible
  streams, while the selected contexts and map patch path differ.
- Final `@` forms are parser-visible default-symbol commands, not parser
  artifacts. `ESC (0@`, `ESC )0@`, `ESC )1@`, `ESC )2@`, and `ESC (3@` all
  route through terminal handler `0x120be` and then subdispatch to `0x1bed4`,
  `0x1bed4`, `0x1bf0a`, `0x1bf36`, and `0x1bf74`.
- The real-backed final-`@` stream reads default-symbol table words
  `0x0005`, `0x000e`, `0x0155`, and `0x000e`, leaves final active words
  `[0x000e, 0x0005]`, and then selects visible built-ins when followed by the
  normal primary or secondary font-selection tails.
- Final `X` font-ID forms also route through `0x120be`, but call helper
  `0x17708` instead of replacing the previous requested symbol word. Primary
  built-in `ESC (7X!!` selects context `0xc0089fb0`; secondary built-in
  `ESC )8X SO !!` selects context `0xc00ae122`.
- Bit-30-clear final-`X` streams select inline/downloaded context
  `0x00000100`: primary `ESC (4660X!` queues compact prefix
  `00 00 00 00 00 00 00 01 01 66 01 00 00 00`, and secondary
  `ESC )4660X SO !` queues prefix
  `00 00 00 00 00 01 00 01 01 66 01 00 00 00`.
- `0x17708` has four documented non-selected exits: record scan miss,
  candidate-slot miss, class mismatch, and page-root context-full. In those
  cases no `0x14c64` map dispatch occurs, and later printable bytes render
  from the prior primary or secondary context rather than from the requested
  font ID.
- `0x13eb8` also has preserved-output exits. The transient path stages
  selected context `0xc008004c` in `0x782992` but does not write the normal
  current-font context or rebuild the map; the cache-hit path returns after
  `0x148f8`. Fixtures carry both exits through later printable/SO tails and
  prove that the prior context remains the visible source.
- Common refresh gate `0xc580` is the branch point that determines whether
  parsed font state reaches a page-root slot. The documented branch cluster
  covers dirty-1 primary/secondary installs, matching-context reuse,
  full-table no-match skip, selector-mismatch refresh-only, dirty-2
  selector-match installs, and dirty-2 selector-mismatch remembered-word-only
  behavior.

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

Font-selection command-to-output matrix:

- Attribute selection `ESC (s...T` / `ESC )s...T`:
  lowercase finals write request fields; uppercase final `T` calls
  `0xc7e0 -> 0xc580`. The visible effect is delayed until `0xc580` /
  `0x13eb8` / `0x144d2` / `0x14c64` select a context and rebuild the map
  consumed by later printable bytes.
- Symbol-set finals through `0x120be` / `0x1be22`:
  normal finals write requested symbol word `0x782ef4 + 0x10 * slot` and
  refresh through `0xc580`. They change the map selection and glyph patching
  used by later `0x1393a`, not any already queued compact objects.
- Final `@` default-symbol forms:
  `0x120be` subdispatches to the ROM default-symbol table helpers. The
  resulting active/remembered symbol words feed the same `0xc580` and map
  rebuild path before later printable bytes become page objects.
- Final `X` font-ID forms:
  `0x120be` calls `0x17708`. Successful paths write active symbol/context
  selection state and dispatch `0x14c64`; documented non-selected exits stop
  before map rebuild, so following printable bytes continue from the prior
  context.
- SI/SO controls:
  `0xc68a` selects primary slot `0`, and `0xc6b8` selects secondary slot `1`.
  They affect the next printable byte's map/context choice through
  `0x782f06`; they do not alter compact objects already queued on the page.

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

Reproduction rule:

- Treat font-selection commands as canonical text-state writers, not page
  object writers. The parsed `ESC (s...T` / `ESC )s...T` streams update
  request fields and dirty flags, then `0xc580`, `0x13eb8`, `0x144d2`, and
  `0x14c64` select a context record and rebuild the primary or secondary map.
- Preserve the selected context until a printable byte consumes it. The
  visible handoff is the later printable path:
  `0xd04a -> 0x1393a -> 0xd3b2/0xd824 -> 0x12f2e`, which writes compact
  page objects and marks the page-root context slot live.
- Publication must copy both sides of that state: `0xff1e` publishes the
  compact bucket root, while `0x1edc6` copies page-root context slots
  `+0x2c..+0x68` to render-record slots `+0x24..+0x60`. A reproducer that
  copies glyph bytes without these context slots cannot reproduce selected
  font rows.
- SI/SO are render-affecting because they choose which installed slot the
  following printable byte uses; they do not change already queued compact
  object bytes. The selected slot is represented by `0x782f06` and
  page-root slot byte `0x78297e`, then consumed as compact object context slot
  `+0x05` and render context cache `0x783a2c`.

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
  `0x78315c`, transient selected context `0x782992`, current font ID
  `0x782f2e`, default-symbol tables `0x782f1c`, `0x782f20`,
  `0x782f24`, and `0x782f28`, compact coordinates, glyph-entry pointers, and
  render-band fields.
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
  flags, compact object shapes, bridge state, or ROM-derived rows.

Evidence for this path is in
[font-context-metrics.md](font-context-metrics.md),
[symbol-set-selection.md](symbol-set-selection.md),
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
`generated/disasm/ic30_ic13_font_id_select_017708.lst`,
`generated/disasm/ic30_ic13_symbol_set_handler_01be22.lst`, and
`generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`.

## Worked Path: Pitch Mode To Font Refresh

This path covers `ESC &k#S/s`, a compatibility pitch-mode command. It is a
host-byte command family, but it does not allocate page objects or draw by
itself. Its only page-visible effect is that it rewrites the active font pitch
request and rejoins the ordinary `0xc89c` / `0xc580` font-refresh path before
later printable bytes select glyphs, HMI, compact coordinates, and rendered
rows.

Parser and command behavior:

- `ESC &k#S` and lowercase chaining form `ESC &k#s` enter through byte fetch
  `0xa904`, parser wrapper `0xda9a`, and parser loop `0x11774`.
- The terminal handler is `0xc390`. It reads the absolute selector from the
  parsed command record behind command cursor `0x78299e`.
- Jump table `0xc370` accepts selectors `0`, `2`, and `4`; other selector
  values return through default exit `0xc420` without calling `0xc89c` or
  `0xc580`.
- Selector `0` rewrites the active record as synthetic pitch `10.0000`, calls
  `0xc89c` and `0xc580`, then writes word `1` into the next synthetic record,
  advances `0x78299e` by `0x0c`, and calls `0xc89c` / `0xc580` again.
- Selector `2` rewrites the active record as synthetic pitch `16.6600`
  (`integer 16`, fraction word `0x19c8`) and calls `0xc89c` / `0xc580` once.
- Selector `4` rewrites the active record as synthetic pitch `12.0000` and
  calls `0xc89c` / `0xc580` once.

Downstream font-refresh effect:

- Pitch writer `0xc89c` consumes the synthetic record through cursor
  `0x78299e`, folds signed values positive, clamps integer values at
  `0x028f`, computes `(integer * 10000 + fraction) / 100`, and writes the
  pitch word at `0x782ef0 + 0x10 * slot`.
- `0xc89c` marks dirty flags `0x782f2c` and `0x782f2d`.
- Common refresh `0xc580` is the same gate used by ordinary font-selection
  commands. It can call `0x13eb8`, install or reuse a page-root font context
  through `0xc428` / `0xc4fc`, rebuild maps through `0x14c64`, or exit without
  a new context depending on dirty state, slot availability, and selector
  match.
- Later printable bytes consume the refreshed selected context through
  `0xd04a`, `0x1393a`, `0x12f2e`, page-root context slots, `0xff1e`,
  `0x1ed84`, `0x1edc6`, and `0x1ef6a`.

State classification:

- Canonical font-request state:
  pitch word `0x782ef0 + 0x10 * slot`, current font contexts `0x782ee6` and
  `0x782ef6`, maps `0x782f32` and `0x783032`, selected text slot
  `0x782f06`, page-root context slots, and rendered compact text objects
  produced by later printable bytes.
- Derived/cache state:
  selected candidate pointer `0x7828a8`, selected target `0x7828de`,
  transient context record `0x782992`, selected-font flags `0x783132` /
  `0x783133`, HMI `0x78315c`, compact coordinates, glyph-entry pointers, and
  render-band fields.
- Parser scratch:
  the six-byte `ESC &k#S/s` record, synthetic pitch records written by
  `0xc390`, command cursor `0x78299e`, and the advanced second synthetic
  record used only by selector `0`.
- Firmware bookkeeping:
  dirty flags `0x782f2c` and `0x782f2d`, `0xc580` branch state, page-root
  live-font flags, `0xc4fc` slot-scan state, publication flag `0x782996`, and
  render scheduler progress.
- Hardware/external state: none for this ROM-local command bridge.
- Unknown:
  no separate pitch-mode renderer exists. Remaining work is a host-byte stream
  that pairs `ESC &k#S/s` with surrounding font-selection state and proves a
  different selected context, HMI, compact object, bridge state, or rendered
  rows. The producer boundary itself is not an unresolved renderer edge.

Evidence:

- Detail note: [font-context-metrics.md](font-context-metrics.md), section
  `Pitch Mode Command`.
- Semantic checkpoint: `Built-In Font Selection To Visible Text` in
  [semantic-state-model.md](semantic-state-model.md).
- Disassembly evidence:
  `generated/disasm/ic30_ic13_pitch_mode_handler_00c390.lst`,
  `generated/disasm/ic30_ic13_font_update_common_00c580.lst`,
  `generated/disasm/ic30_ic13_font_context_install_00c428.lst`,
  `generated/disasm/ic30_ic13_font_candidate_activate_01569c.lst`, and
  `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`.
- Downstream visible-output fixtures are the selected-font fixtures named in
  `Worked Path: Font Selection To Visible Glyphs`, because `ESC &k#S/s`
  rejoins the same `0xc89c` / `0xc580` refresh contract before printable
  bytes create page objects.

## Worked Path: Firmware Font Sample Page

This path covers the built-in font-sample printout generator. It is not a
host-byte stream: firmware selects resource records, formats row text, and
calls the ordinary printable path directly. It belongs in the reproduction
model because it exercises the same current-font context install, compact text
objects, page-record bridge, and render dispatch used by host-driven text.

Entry and setup:

- Setup entry `0x1e0b2` checks that at least one font record is available,
  clears copy/wrap/perforation state, rebuilds orientation and page-root state,
  writes forced sample-page VMI/HMI defaults, chooses the starting vertical
  cursor, and passes a derived remaining-row count to `0x1ea4e`.
- Printout entry `0x1c204` starts the source/class passes. If no font records
  exist, it reports status `0xe3/0x51` instead of emitting page text.
- The class loop `0x1c28e..0x1c344` runs class-zero and class-one passes,
  skipping empty classes and ejecting between passes through `0xf0f0`.
- The source loop `0x1c2fe..0x1c332` iterates source groups `0..3`, and
  `0x1c354..0x1c5e4` walks one source group.

Candidate and row selection:

- Resolver `0x1b50e` consumes source mode and row ordinal. It first tries fast
  probe `0x1b8ea`, then scans mode-specific first and second candidate
  windows.
- Candidate classifiers `0x1b750` and `0x1b7b2` feed the resolver;
  `0x1c746`, `0x1c766`, `0x1c7a8`, and `0x1c710` normalize records and test
  class/orientation before visible row emission.
- Selected resource install `0x1c5e8` writes current-font/page-root state,
  rebuilds maps through `0x14c64`, and refreshes the page-root font slot
  through `0xc428`.
- Source/category heading helper `0x1ca2c` selects labels from table
  `0x1c170`, emits source headings, and writes row-height state.
- Row formatter `0x1cabe` emits row prefix, font name/style, pitch/height,
  symbol-set text, and sample columns through `0xd04a`, `0xd0f0`, and
  horizontal advance helper `0x1d152`.
- Sample-run helper `0x1cf34` emits ROM run table `0x1c1cf`, optionally
  advances to an alternate sample row, emits run table `0x1c1e9`, and writes
  the caller page-break flag.

Page and render path:

- Printable row bytes enter the ordinary text producer through `0xd04a`,
  `0x1393a`, `0xd824` / `0xd3b2`, and `0x12f2e`.
- Compact text objects are queued under the current page root; later
  publication and rendering use the normal `0xff1e`, `0x1ed84`, `0x1edc6`,
  and `0x1ef6a` path.
- The full printout is modeled as eight class/source page-record segments,
  from class `0` source `0` through class `1` source `3`, with row counts
  `[0, 1, 1, 14, 0, 1, 1, 14]`.
- Fixture `font sample full printout segments render through 0x1ed84 and
  0x1ef6a` pins render-bucket counts `[1, 6, 6, 65, 1, 5, 5, 50]`,
  rendered bucket-row totals `[33, 210, 210, 2012, 33, 146, 146, 1257]`,
  and aggregate rendered-surface digest
  `5e5e735b4fb2a2a4dff4794099a02eaf23fa2dd3e469df8d053db88a321ea6f2`.

Continuation and page-limit forms:

- `0x1ca2c`, `0x1d050`, `0x1d868`, and `0x1dcf2` compare cursor and
  page-limit state before emitting headings, current rows, alternate rows, or
  continuation pages.
- Fixture `font sample page-limit branches trigger continuation calls` pins
  the shared page-limit predicates.
- The covered forced-continuation object forms are heading preflight, cartridge
  heading, internal class-zero row-overrun `I01`, internal class-one
  row-overrun `I16`, and alternate-row `I01` after the
  `0x1c4a4 -> 0x1d868 -> 0x1c4b6 -> 0x1c9f6 -> 0x1c4ca -> 0x1ca2c ->
  0x1c4d4 -> 0xf06e -> 0x1c4e8 -> 0x1d050 -> 0x1c4f2 -> 0x1cabe` caller
  sequence.

State classification:

- Canonical sample state:
  accepted resource count `0x78278e`, class counts `0x782798` / `0x782790`,
  candidate pointer/count windows, current and alternate selected contexts,
  source labels at `0x1c170`, sample run tables `0x1c1cf` and `0x1c1e9`,
  current page root, page-root context slots, vertical cursor `0x782c8e`, and
  page-limit word `0x782db6`.
- Derived/cache state:
  row-height cache `0x783f06`, recent-context count/list
  `0x783f08` / `0x783f0a`, row-to-row y advance from `0x1d050`, alternate-row
  fit result from `0x1d868`, multi-probe fit state from `0x1dcf2`, compact
  bucket sets, and render-surface hashes.
- Parser scratch:
  synthesized orientation command record at `0x78299e` written by `0x1d76c`,
  fast-probe scratch `0x7828a0`, caller-visible candidate word `0x7828a4`,
  selector scratch `0x78289f`, and Roman-8 substitution scratch
  `0x7828ac` / `0x7821a0`.
- Firmware bookkeeping:
  per-source status bytes `0x783f02..0x783f05`, local page-break word
  `-6(A6)`, page-root publication state, and render scheduler progress.
- Hardware/external state:
  none for the ROM-local generated-page contract.
- Unknown:
  record fields `+0x28/+0x2a` are consumed as decoded-height inputs by
  `0x1519a`; fields `+0x2f..+0x31` are consumed as same-class chooser
  tie-breakers by `0x1428c`. Manual-facing baseline/cell names remain open;
  physical output is optional correlation, not a ROM-local evidence source.

Evidence:

- Detail note: [font-sample-page.md](font-sample-page.md).
- Resource note: [resource-rom.md](resource-rom.md).
- Semantic checkpoint: `Built-In Font Sample Printout Loop` in
  [semantic-state-model.md](semantic-state-model.md).
- Disassembly evidence:
  `generated/disasm/ic30_ic13_font_sample_page_01c170.lst`,
  `generated/disasm/ic30_ic13_font_sample_row_helpers_01d198.lst`,
  `generated/disasm/ic30_ic13_font_page_setup_01e0b2.lst`,
  `generated/disasm/ic30_ic13_font_resource_object_lookup_01b4c0.lst`,
  `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`,
  `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`, and
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`.

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
  render handoff. Remaining work is selected-font cross-products only when a
  new stream changes copied metric fields, selected context form, pending span
  fields, span object bytes, or rendered rows; manual-facing names for
  consumed validation fields remain external.

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

Reproduction rule:

- Treat explicit zero-handler rows as table decisions, not missing
  disassembly. Normal mode-zero `0x00`, `0x07`, and `0x0b` run the terminal
  parser cleanup path and do not fall through to printable text or direct
  control handling.
- Preserve the delayed-payload boundary even for no-output rows. A terminal
  zero-handler row can call `0x12218` before scratch reset, so a renderer must
  not collapse it to a simple byte skip when a delayed handler is pending.
- In alternate/data mode, zero-handler C0 rows are stored input, not ignored
  output: `0x11930..0x11ab8` appends them through `0xe002` before the
  terminal reset path. They can later become visible only if macro/data-chain
  replay feeds those stored bytes back through `0xa904`.
- Only unmatched normal mode-zero bytes reach the printable fallback, and only
  when the active font-context predicate at `0x782f06` / `0x782eeb` allows
  `0xd04a`. If the predicate rejects, the byte is ignored without page-object
  production.
- Treat `ESC ?`, display-reader `ESC Z`, and `ESC &lT/t` as parser artifacts
  or unimplemented rows unless a later byte stream reaches a documented
  command-family handler. They are not hidden drawing commands.

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

Neighboring command-family status paths:

- Control-Z handlers are local mode-specific consumers, not one global
  parser rule. Handler `0x120d2` conditionally routes literal `0x1a` through
  `0xd04a` when the selected context byte equals `1`; handler `0x1210c`
  appends literal `0x1a` through `0xe002`; handler `0x1219e` routes synthetic
  value `0x100` through `0xd04a`; and handler `0x121b2` calls `0xd99a` before
  appending normalized value `0x7f` through `0xe002`.
- `ESC z` is the display-functions-off/status terminal at `0xcd86`, not a
  text-rendering command. It consumes active data-chain frame pointer
  `0x782d76`, tests frame byte `+9`, and calls `0x9c2c` only when that byte
  is zero.
- Helper `0x9c2c` waits while service/status busy bit `0x780e2d.3` is set,
  sets service-in-progress marker `0x7821cc`, sets status marker `0x7822db`,
  ORs `0x08` into warning/status accumulator `0x780e2a` through
  `0x9b5e(0x780e2a, 0x8)`, and clears `0x7821cc` before return.
- These status paths do not allocate page roots, queue page objects, publish
  pages, or render pixels. They matter to reproduction only as parser-visible
  command behavior and as status-side state that can affect a bidirectional
  host or service loop.

Direct-reader command-to-output matrix:

- `ESC &p#X` transparent print data:
  parser edge `0x11774 -> 0x11f5a -> 0x121cc -> 0x12218 -> 0x12452`.
  The command record word `+2` becomes the absolute payload count, and
  `0x12452` fetches that many routed values directly through `0xa904`.
  Values route to printable handler `0xd04a` or fixed-space handler
  `0xd0f0` based on selected context/filter state. Printable routes queue
  ordinary compact or segmented text objects; default-filtered fixed-space
  routes may only advance cursor state in the pinned built-in source path.
- `ESC Y ... ESC Z` normal display-functions reader:
  parser edge `0x11774 -> 0x12536`, then direct loop fetches through
  `0xa904` until local normalized `ESC Z` termination or no-byte return.
  Loop values use the same context/filter route predicates as transparent
  data. Values sent to `0xd04a` queue text objects; values sent to `0xd0f0`
  perform fixed-space behavior. The terminating `ESC Z` pair participates in
  the route stream before the loop exits.
- `ESC Y ... ESC Z` alternate/data reader:
  parser edge `0x11774 -> 0x12120`; the handler appends literal `ESC Y` and
  each normalized loop value through macro/data sink `0xe002`. It creates no
  immediate page root, page object, publication, or rendered output. Its
  output is stored input for later data-chain or macro replay.
- Local Control-Z handlers:
  handlers `0x120d2`, `0x1210c`, `0x1219e`, and `0x121b2` are table-local
  consumers for `0x1a`, not a global parser rule. Depending on parser mode and
  filter state they route a literal/synthetic value to `0xd04a`, append it
  through `0xe002`, or normalize `1a 58` through `0xd99a`.
- `ESC z` display-functions-off/status:
  handler `0xcd86` tests active data-chain frame kind at `0x782d76 + 9` and
  calls status helper `0x9c2c` only for kind `0`. It writes status-side state
  `0x7821cc`, `0x7822db`, and `0x780e2a.3`, but it does not queue page
  objects or render pixels.

State roles for the direct-reader matrix are shared with transparent print:
canonical text/page state is selected slot `0x782f06`, cursor `0x782c8a`,
current page root `0x78297a`, queued page objects, and later published/render
records; derived/filter state is selected context byte
`0x782eea + 0x10 * slot`, fallback filter `0x782efa`, and high-character
flags `0x783132` / `0x783133`; parser scratch is the delayed transparent
record, display-functions loop flag/value registers, and resumed parser mode;
firmware bookkeeping is `0xd99a`, `0xf054`, append sink `0xe002`, status
helper `0x9c2c`, stream allocators, and publication/scheduler progress.

Open boundary:

- The ROM-local direct-reader routes above are closed for the documented
  primary, filtered, and alternate/data streams. The only remaining
  pixel-affecting edge in this cluster is the external secondary
  segment-57 resource continuation at `0x0c0000..0x0c0321`, documented in
  `Boundary: Secondary Segment-57 Source`. That is a missing resource-window
  decode boundary, not an `ESC &p#X` or `ESC Y` parser/route gap.

State classification for this path:

- Canonical state:
  direct-reader termination flag `D4`, normalized loop value `D5`, selected
  text/context slot `0x782f06`, current page root `0x78297a`, compact text
  objects, macro/data append stream for alternate mode, active data-chain frame
  pointer `0x782d76`, published source record, and render-record
  bucket/context roots.
- Derived/cache state:
  selected context byte `0x782eea + 0x10 * slot`, fallback filter byte
  `0x782efa`, local high-control filter word, compact coordinates, glyph
  mapping results, status marker `0x7822db`, warning/status bit `0x780e2a.3`,
  and render-band fields.
- Parser scratch:
  initial `ESC Y` parser mode and table dispatch state, plus any parser state
  resumed after the direct reader returns.
- Firmware bookkeeping:
  `0xd99a` local control-report side effect, `0xf054` CR post-handler,
  append sink `0xe002`, stream allocator fields, publication flag
  `0x782996`, service-in-progress marker `0x7821cc`, `0x9c2c` wait behavior
  on `0x780e2d.3`, scheduler cursors, and render-work progress words.
- Unknown:
  no unresolved ROM-local middle edge remains for the normal `0x12536` direct
  reader loop, its default-filter and filter-on route predicates, or the
  alternate/data `0x12120` append loop, local Control-Z handlers, or the
  `0xcd86 -> 0x9c2c` display-functions-off status edge. External
  status-consumer naming for `0x7821cc`, `0x7822db`, and `0x780e2a.3`
  remains outside this ROM-local path.

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

Direct-control command-to-output matrix:

- `ESC &k#G` line termination:
  handler `0xedf8` writes mode byte `0x78318f`. It creates no page object by
  itself. Later CR/LF/FF direct-control handlers consume its bits and move the
  cursor or publish the current root.
- CR byte `0x0d`:
  handler `0xf02c` calls `0xf06e` to copy left margin `0x782dd6` into
  horizontal cursor `0x782c8a`, flushes pending span state through `0xf34a`,
  and optionally calls LF helper `0xf0b2` when `0x78318f.7` is set. Its
  output effect is the following printable object's x/y coordinate.
- LF byte `0x0a`:
  handler `0xf08c` calls `0xf0b2` to add VMI `0x783160` to vertical cursor
  `0x782c8e`, with optional CR-style horizontal reset when `0x78318f.6` is
  set. The moved cursor is consumed by later printable bytes.
- FF byte `0x0c`:
  handler `0xf0f0` applies the line-termination mode, then publishes the
  current page root through `0xff1e` when one exists. Its visible output is
  the pre-FF queued page objects.
- HT and BS bytes `0x09` / `0x08`:
  handlers `0xf1cc` and `0xf2a8` mutate horizontal cursor `0x782c8a` using
  HMI `0x78315c`, tab-stop arithmetic, left-margin clamp, and previous-width
  state. They do not queue page objects directly.
- `ESC &k#H` HMI:
  handler `0xca8c` writes packed HMI `0x78315c`; later printable, margin,
  cursor, HT, and BS paths consume it for coordinate conversion and advance.
- `ESC &s#C` wrap:
  handler `0xedb0` writes wrap byte `0x783190`; printable prechecks
  `0xd28a` and `0xd6bc` consume it before object queueing.
- `ESC &f#S` cursor stack:
  handler `0xf75e` pushes or pops cursor fields, including vertical offset
  `0x782dbe`; a pop changes the following printable object's coordinate.

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

Cursor/margin command-to-output matrix:

- `ESC &a#L` left margin:
  handler `0xeb58` converts columns through HMI `0x78315c`, writes accepted
  values to `0x782dd6`, and may move horizontal cursor `0x782c8a`. The next
  printable byte consumes that cursor and queues the visible compact object.
- `ESC &a#M` right margin:
  handler `0xec0c` writes right margin `0x782dda`, sets latch `0x782a57`,
  and may clamp current horizontal cursor left. Its output effect is through
  following printable placement and later wrap/reject decisions.
- `ESC &a#C` and `ESC &a#H` horizontal cursor:
  handlers `0xf39e` and `0xf416` convert column or decipoint units, then
  commit through `0xf4ca` to `0x782c8a`. The following printable byte is the
  visible consumer.
- `ESC &a#R` and `ESC &a#V` vertical cursor:
  handlers `0xf560` and `0xf60a` convert row or decipoint units, then commit
  through `0xf6e2` to `0x782c8e`. If pending span state exists, the command
  can materialize a span object before moving y.
- `ESC *p#X` and `ESC *p#Y` dot cursor:
  handlers `0xf48c` and `0xf692` shift whole-dot parameters into packed
  coordinates and share the same `0xf4ca` / `0xf6e2` commit helpers.
- Span-flush siblings:
  cursor-changing handlers that call `0xf34a` can create selector-`0x4000`
  segment-list objects through `0x12714` before the cursor write. Those span
  objects and the following printable object are separate page-record effects.

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

## Worked Path: Text Span Flush And Fixed-Width Spans

This path covers pending text-span output driven by underline/text-attribute
state, printable metric consumers, and direct-control flush points. The
printable glyph still queues through the compact text path, but span consumers
maintain pending bounds that can later flush into selector-`0x4000`
segment-list objects, landscape fixed-width objects, or a publication retry
path.

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
- Portrait `0x12714` fixtures prove the local source can queue a single
  segment-list object or split a three-row span across adjacent bucket
  objects when the span crosses a 16-row bucket boundary.
- Landscape `0x12714` fixtures prove the same pending fields are transformed
  into fixed-list objects under page-root `+0x28`, bridged to render
  `+0x20`, and consumed by `0x1f756` / `0x1f7b0`.
- Allocation-failure fixture
  `0x12714 allocation failure publishes page and retries span` proves that
  a failed first `0x136d2` allocation marks page-root `+0x14`, publishes the
  existing page through `0xff1e`, creates a fresh root through `0x10084`,
  rebuilds the same local span source, and retries the fixed-list insertion.

Orientation and retry behavior:

- `0x12714` clears pending flag `0x783184`, packages an 8-byte local source,
  ensures current root `0x78297a` through `0x10084`, gates the source against
  page extent `0x782db6`, and then calls `0x13520`.
- `0x13520` uses orientation byte `0x782da3` after `0x137a2` derives
  selector/key state. Portrait orientation routes to `0x1354a` /
  `0x135f0`; landscape routes to `0x136d2`.
- Portrait producer `0x135f0` appends six-byte entries to a segment-list
  object with class byte `0x40`. Renderer `0x1f812` consumes those entries
  from render root `+0x18` and writes counted mask rows.
- Portrait splitter `0x1354a` emits the first entry before a 16-row bucket
  boundary, increments bucket index `0x782a7c`, clears row bits in key
  `0x782a7e`, and emits the remaining rows in the next bucket.
- Landscape producer `0x136d2` inserts a fixed-width object ordered by bucket
  byte under root `+0x28`. Bridge `0x1edc6` copies it to render `+0x20`,
  copies source word `+8` to render word `+0x0a`, and sets continuation
  bytes `+0x0c = 1` and `+0x0d = 8`.
- Fixed-list renderer `0x1f756` runs on five-band boundaries, filters object
  byte `+4` against the current band, uses `object[5] & 0x0f` to select a
  pattern longword from ROM table `0x308de`, clears bridge flag bit `0x10`,
  decrements remaining rows at object `+0x0a`, and writes the low pattern
  word through `0x1f7b0` / `0x1f626`.

State classification for this path:

- Canonical state:
  underline/text-attribute selector `0x783185`, pending span enable
  `0x783184`, span bounds `0x783186` / `0x783188` / `0x78318a`, selected
  font context, orientation byte `0x782da3`, geometry inputs `0x782db2` and
  `0x782db6`, current page root `0x78297a`, compact glyph object,
  selector-`0x4000` segment-list span object, and landscape fixed-list object.
- Derived/cache state:
  packed segment-list keys such as `0x3a00`, landscape key `0x3300`,
  producer bucket/key fields `0x782a7c..0x782a7e`, compact text coordinate,
  selected context metric fields, render-band fields, segment-list trailing
  masks from `0x308f2`, and fixed-list pattern words from `0x308de`.
- Parser scratch:
  six-byte `ESC &d3D` and `ESC &d@` records at `0x78299e`, parser mode state,
  and the printable byte between the two commands.
- Firmware bookkeeping:
  page-root live-font flags, span re-arm work in `0x126e2`, allocation cursors
  for `0x13520` / `0x135f0` / `0x136d2`, retry/finalization bit in page-root
  flag word `+0x14`, publication flag `0x782996`, scheduler cursors, and
  render-work progress words.
- Unknown:
  no unresolved ROM-local middle edge remains for the documented underline
  stream, CR/margin/vertical-cursor span flushes, portrait split, landscape
  fixed-list insertion, or allocation-failure retry. Remaining span work is
  selected-font or byte-stream variants that change concrete consumed fields:
  source object `+0x00/+0x04/+0x0b/+0x10/+0x16`, unflagged metric bytes
  `+0x2b/+0x2c/+0x2d`, flagged metric words `+0x16/+0x18/+0x1a`, pending span
  state `0x783184..0x78318a`, `0x12714` page-extent acceptance, orientation
  branch, fixed-list/segment-list object fields, bridge roots, or rendered
  rows. It is not the pending-span-to-page-object handoff.

Evidence for this path is in
[direct-control-codes.md](direct-control-codes.md),
[font-context-metrics.md](font-context-metrics.md),
[page-record-storage.md](page-record-storage.md),
[page-raster-imaging.md](page-raster-imaging.md), and
[semantic-state-model.md](semantic-state-model.md). Key supporting reports are
`generated/analysis/ic30_ic13_text_cursor_span_flow.md`,
`generated/analysis/ic30_ic13_text_glyph_index_flow.md`, and
`generated/disasm/ic30_ic13_text_span_flush_012714.lst`,
`generated/disasm/ic30_ic13_display_list_helpers_013386.lst`, and
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
- The same scanner split is visible in the candidate-count fields: a visible
  mirror doubles total `0x78278e` to `48` and low class counters `0x782792` /
  `0x78279a` to `24` each; code-pair and zero-fill keep the verified
  `24` / `12` / `12` state.
- Tool `tools/probe_resource_window.py --quiet` is the checked-in repro entry
  for this boundary. It reports the verified resource-pair hashes, the
  `478`-byte suffix digest, the `802`-byte continuation candidate hashes, the
  current-band digest, and the scanner/candidate-count split above without
  dumping row-level logs on success.

The exact unresolved boundary is therefore firmware range
`0x0c0000..0x0c0321`. Closing it requires static board, emulator, or gate-array
memory-map evidence; ROM/disassembly evidence can document the candidate
continuations and their consequences, but cannot select the physical byte
source at `0x0c0000`.

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

Downloaded-font command-to-output matrix:

- `ESC *c#D`:
  parser edge `0x11774 -> 0x11eb6 -> 0x11ec8 -> 0x11eda ->
  0x15a56`; writer `0x15a56` rewinds parser-record cursor `0x78299e`
  and writes current downloaded-font id `0x782f2e`. Consumers
  `0x15d0a` and `0x16c14` resolve the current record by this id. There is
  no page object by itself; it selects which downloaded-font record later
  payload commands mutate.
- `ESC *c#E`:
  the same `*c` parser chain reaches `0x15a18`; writer `0x15a18` writes
  current character/code word `0x782f30`. Consumer `0x16498` uses it for the
  glyph-table entry when a character payload installs. There is no page
  object by itself; it names the glyph that later printable bytes can resolve.
- `ESC *c#F`:
  the same `*c` parser chain reaches `0x16df6`. Value `5F` reaches
  `0x16e86 -> 0x17108`, sets current-record flag bit `6`, and moves counts
  `0x782782/0x782786`; value `4F` uses unmark sibling `0x17150`.
  Marked/unmarked record counts constrain later current-record allocation,
  release, and selection. There is no page object by itself; it changes
  bookkeeping before descriptor or payload commands.
- `ESC )s0W` / `ESC (s0W`:
  parser edge `0x11f96 -> 0x121cc -> 0x12218 -> 0x15d0a`; writer
  `0x15d0a` writes payload budget `0x783140`, consumes descriptor bytes
  through `0x1599c`, and routes bit-30-clear fixed-record objects or
  continuation paths. Fixed-record resource object paths feed printable-byte
  selection and compact text production through `0xd04a`, `0xd824`, and
  `0x12f2e`. Output is visible only after a following printable byte consumes
  the selected resource; rejected descriptors drain and leave following
  default printable output unchanged.
- Nonzero `ESC )s#W` / `ESC (s#W` resource header:
  parser edge `0x11f96 -> 0x121cc -> 0x12218 -> 0x16c14`; writer
  `0x16c14` writes `0x783140`, current-record ids/payload pointers,
  candidate flags, counters, and installed payload state after validation
  through `0x16fae` and allocation through `0x17026` / `0x1719c`. Consumers
  include selection and metric paths `0x14c64`, `d4ac`, and `d8fc`; later
  downloaded-character payloads may reuse the installed resource form. There
  are no pixels at install time; later printable bytes can queue compact,
  wide, or segmented downloaded-glyph page objects.
- Nonzero `ESC )s#W` / `ESC (s#W` downloaded-character payload:
  parser edge `0x11f96 -> 0x121cc -> 0x12218 -> 0x16c14 -> 0x15dc6 ->
  0x16498 -> 0x15dcc -> 0x12328`; writer `0x16498` writes glyph-table
  entries, glyph record bytes, bitmap bytes, continuation state on partial
  copies, and release/no-install cleanup through `0x17a24` / `0x1887a` when
  needed. Printable handler `0xd04a` resolves host bytes through the
  installed context; `0xd824 -> 0x12f2e -> 0x1387c` queues compact page
  objects. Accepted payloads become visible only when a following printable
  byte queues objects; `0xff1e -> 0x1ed84 -> 0x1edc6 -> 0x1ef6a` publishes
  and renders them through compact targets `0x1fe76`, `0x1f0d2`, `0x1f1f0`,
  or `0x1f264`. No-install exits drain payload bytes and leave the next
  printable byte on the prior/default font path.

Matrix evidence is the detailed ledger below, `Downloaded Glyph`,
`Nonzero Resource Payload`, and `Fixed-Record Resource Object` checkpoints in
[semantic-state-model.md](semantic-state-model.md), and listings
`generated/disasm/ic30_ic13_assign_font_id_015a56.lst`,
`generated/disasm/ic30_ic13_font_control_dispatch_016df6.lst`,
`generated/disasm/ic30_ic13_font_payload_setup_015b80.lst`,
`generated/disasm/ic30_ic13_font_resource_object_add_016c14.lst`,
`generated/disasm/ic30_ic13_font_payload_object_path_016040.lst`,
`generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`, and
`generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`.

Open ROM-local boundaries for this command family are the documented
downloaded-glyph helper edges, not missing external output comparisons:
unchecked short compact helper indices above table entry `128` in `0x1fe76`,
wrapped width low bytes selecting invalid compact mode-0 helper targets through
`0x1f034` / `0x1f08e`, segmented-wide span-31 fallback source offset `+0xb50`,
and the oversized segmented-wide payload-count cap `0x7fff` before `0x16498`
can publish a glyph.

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

Validation, no-install, and partial-install exits:

- Descriptor validation for downloaded-resource headers is table-driven at
  `0x16fae` from table `0x16eae`. When a rejecting predicate fails,
  `0x17026` returns allocation status `0`, and `0x16c14` leaves current
  downloaded-font records, candidate cursors, and selected installed
  candidate state unchanged.
- Fixture `ESC )s#W validation failures preserve following printable output`
  proves seven host-fetched `ESC )s80W` validation no-install streams plus
  the short-budget `ESC )s8W` entry-5 failure. Invalid resource type, first
  code overflow, zero line/count, high line/count, reversed range/count, high
  range/count, invalid class, and short descriptor budget all resume the
  parser at the following printable `!`, queue the default-font compact
  object, and render the same rows as baseline `!`.
- Character-object writer `0x16498` has its own no-install exits. Fixture
  `0x16498 replacement allocation failure partial and rejected downloaded
  character exits preserve state` covers old-pointer replacement release
  through `0x17a24`, allocation failure through `0x170c` / `0x9b5e` /
  `0x1887a`, descriptor mode-byte `0` rejection, and high-character/header
  type rejection.
- Fixture `0x16498 no-install exits preserve following printable output`
  carries those character-object no-install exits through the next printable
  byte and FF. The rejected payload bytes drain through
  `0x15dc6 -> 0x16498 -> 0x15dcc -> 0x12328`; the following `!` routes to
  `0xd04a`, queues the unchanged default-font compact object, publishes
  through `0xff1e`, and renders through `0x1ed84` / `0x1ef6a`.
- Copy status `2` is the opposite visible contract. Fixture
  `0x16498 status-2 partial installs remain printable` proves linear and
  split-plane partial objects write table entries, object records, partial
  bitmap bytes, and continuation fields, then the following printable resolves
  the partial glyph and renders rows from copied bytes plus zero-filled
  missing bytes. The same fixture carries both partial objects through FF
  publication and published-record rendering.
- Continuation helper `0x15b9a` resumes downloaded-character continuation
  fields. On status `1`, it completes the bitmap copy and clears
  continuation state. On status `2`, it resaves advanced destinations and
  counters. On status `0`, it calls `0x17a24` to release the offset-table
  entry, clears continuation fields, and leaves the partially rewritten object
  unreachable from the glyph table.

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
  `0x7827de..0x7827e9`, validation payload budget `0x783140`, restored
  rejected records such as `80 57 00 50 00 00` and `80 57 00 08 00 00`, and
  continuation fields `0x7827c6..0x7827da`.
- Firmware bookkeeping:
  downloaded-record counters `0x782782` and `0x782786`, candidate counters and
  cursors updated by `0x16c14`, heap allocation and release helpers, stream
  allocator fields, validation status/allocation status, no-install cleanup
  through `0x1887a` / `0x17a24`, publication flag `0x782996`, scheduler
  cursors, and render-work progress words.
- Unknown:
  no unresolved ROM-local middle edge remains for the covered segmented-wide
  install-to-print-to-publication path, the listed normal/wide selector
  siblings, descriptor validation no-install exits, character-object
  no-install exits, or status-`2` partial-install visible-output exits.
  Remaining downloaded-glyph work is broader row/span cross-products, exact
  HP manual labels for some descriptor fields, and ROM-local behavior after
  documented wrapped source-byte invalid-helper boundaries.

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
`generated/disasm/ic30_ic13_font_resource_validate_016fae.lst`,
`generated/disasm/ic30_ic13_font_resource_validate_predicates_017358.lst`,
`generated/disasm/ic30_ic13_font_resource_find_017026.lst`,
`generated/disasm/ic30_ic13_font_payload_object_path_016040.lst`,
`generated/disasm/ic30_ic13_font_fixed_record_release_017a24.lst`,
`generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`, and
`generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`.

## Worked Path: Nonzero Resource Payload

This path covers the nonzero `ESC )s#W` resource-header route where delayed
handler `0x16c14` installs a `0x1719c` payload as a selected downloaded-font
resource. It is distinct from the direct downloaded-character payload above:
the first `W` stream builds resource/candidate state, and later glyph payloads
or metric consumers make that resource visible.

Parser dispatch and resource install:

- Host bytes enter through `0xa904` and parser loop `0x11774`.
- `ESC )s80W` reaches `0x11f96` through handlers `0x11eb6`, `0x12008`,
  and `0x11ff6`.
- Because the parsed count is nonzero, `0x11f96` schedules delayed handler
  `0x16c14`; `0x121cc` snapshots record `80 57 00 50 00 00`, and
  `0x12218` restores it before calling the handler.
- `0x16c14` rewinds command-record cursor `0x78299e`, writes remaining byte
  budget `0x783140`, validates the resource header through `0x16fae`, and
  allocates or replaces the current-record payload through the `0x17026` /
  `0x1719c` resource path.
- Fixture `resource payload stream ties ROM parser dispatch to 0x16c14 install`
  pins parser modes `1 -> 4 -> 13 -> 0`, delayed handler `0x16c14`, payload
  offset `6`, and payload prefix
  `00 01 02 00 ff ff 00 04 00 06 00 09 01 05 12 34`.

Canonical installed-resource state:

- Current downloaded-font records `0x782640..0x782776`, selected current id
  `0x782f2e`, record payload pointer `+6`, and candidate-list root
  `0x7827a0` are canonical state for this path.
- Candidate counters and cursors `0x78278e`, `0x782790`, `0x782796`,
  `0x782798`, and `0x78279e` are canonical because later selection scans
  consume them.
- Fixture `ESC )s80W resource stream installs 0x1719c payload through 0x16c14`
  proves payload length `80`, validation status `1`, allocation size `10`,
  current id `0x1234`, replacement release of old payload `0x456789`, and
  installed candidate longword `0x40000000`.
- Fixture `0x16c14 routes installed font resource through 0x1bc38 slot`
  pins the successful class-one insertion sibling with candidate longword
  `0x44220000`, shifted candidate list, and updated counters/cursors.
- Fixture `0x172c0-modeled font resource record scan statuses` pins the
  current-record scan statuses that feed the install path: existing id
  status `0`, missing id with a free record status `1`, and missing id with
  no free record status `2`.

Downloaded-pointer glyph consumer:

- After the resource header is installed, a later `ESC )s3W f0 f0 f0` glyph
  payload uses the same nonzero delayed-handler mechanism, then the
  downloaded-character branch returns through
  `0x15dc6 -> 0x16498 -> 0x15dcc -> 0x12328`.
- Fixture `host-fetched resource header plus glyph payload renders offset-table
  downloaded glyph` writes table entry `0x00ce`, record delta `0x0180`, bitmap offset
  `0x018c`, bitmap bytes `f0 f0 f0`, span `1`, width `4`, and row count `3`.
- The installed record is
  `00 00 00 00 0c 01 00 03 00 04 00 00`; printable `!` maps through context
  `0x40000000`, queues compact object
  `00 00 00 00 00 00 00 01 21 5a 00`, and renders the installed bitmap rows
  beside the `d8fc` span object.
- Fixture `type-1 and type-2 resource headers accept downloaded glyph payload stream`
  proves legal setup types `1` and `2` for the same downloaded-pointer form.
  Both allocate payload units `0x100`, write table entry `0x00ce`, record
  delta `0x0300`, bitmap offset `0x030c`, span `1`, width `4`, and row count
  `3`; type `1` installs candidate `0x40000000`, and type `2` installs
  candidate `0x44000000`.

Selection, publication, and visible output:

- `0x14c64` consumes the bit-30 offset-table resource form, writes selected
  symbol `0x1234`, range `0x0000..0x007f`, map address `0x782f32`, and the
  `0x15890` snapshot from payload word `+0x22`.
- Metric consumers use the same installed resource. The `d4ac` fixture reads
  payload bytes `+0x2b = 0`, `+0x2c = 0`, and `+0x2d = 0x20`; the `d8fc`
  fixture reads payload words `+0x16 = 4`, `+0x18 = 4`, and `+0x1a = 5`.
- Fixture `type-1 and type-2 resource glyph FF publications render page records`
  carries legal setup types `1` and `2` through printable `!` and FF. Bucket
  `1` preserves the segment-list span object followed by the compact glyph
  object, and `0x1ed84` / `0x1ef6a` render the published rows through
  segment-list target `0x1f812` and compact target `0x1effe`.
- The wide sibling installs record
  `00 00 00 00 0c 01 00 01 00 90 00 00`, publishes compact-wide object byte
  `0x10`, and reaches renderer `0x1f0d2`.
- The segmented sibling installs record
  `00 00 00 00 0c 01 00 81 00 10 00 00`, publishes selector `0x2000`
  segment objects in buckets `1` and `9`, and reaches segmented renderer
  `0x1f1f0`.

State classification for this path:

- Canonical state:
  current-record pool `0x782640..0x782776`, selected current id `0x782f2e`,
  payload pointer `+6`, `0x1719c` payload header, candidate-list root
  `0x7827a0`, candidate counters/cursors, downloaded-pointer table entries,
  glyph records, bitmap bytes, page objects, and published page records.
- Derived/cache state:
  selected resource map from `0x14c64`, selected symbol/range fields,
  `0x15890` snapshot, printable source object, compact selector class,
  segment-list span objects, render-record bucket roots, and band-local render
  fields.
- Parser scratch:
  delayed record snapshots such as `80 57 00 50 00 00` and
  `80 57 00 03 00 00`, payload budget `0x783140`, staged descriptor state
  from `0x16fae`, and zero-drain or residual-drain state passed to `0x12328`.
- Firmware bookkeeping:
  validation status, allocation status, old-payload release, candidate
  insertion through `0x1bc38`, candidate flag normalization, installed-count
  updates, class-one counter shifts, and final selection refresh through
  `0x1b04c`.
- Unknown:
  no unresolved middle edge remains for parser restore, allocation, candidate
  insertion, selected-map dispatch, legal type-0/type-1/type-2 short glyphs,
  legal type-1/type-2 FF publication, or the cited metric consumers.
  Remaining boundaries are variant breadth: downloaded-pointer row, span, and
  continuation shapes beyond the covered short, wide, and segmented glyphs,
  plus publication variants outside the documented legal type-1/type-2
  span+glyph records.

Evidence for this path is in
[downloaded-fonts.md](downloaded-fonts.md) and
[semantic-state-model.md](semantic-state-model.md), especially
`Nonzero Resource Payload Checkpoint`. Key supporting listings are
`generated/disasm/ic30_ic13_font_payload_setup_015b80.lst`,
`generated/disasm/ic30_ic13_font_resource_object_add_016c14.lst`,
`generated/disasm/ic30_ic13_font_resource_validate_016fae.lst`,
`generated/disasm/ic30_ic13_font_resource_find_017026.lst`,
`generated/disasm/ic30_ic13_font_payload_object_path_016040.lst`,
`generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`, and
`generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`.

## Worked Path: Fixed-Record Resource Object

This path covers the zero-count downloaded-font descriptor route where
`ESC )s0W` does not skip an empty payload. It restores a descriptor packet,
selects a bit-30-clear resource object, writes or resumes a fixed-record
bitmap object, and then lets the following printable byte produce visible
compact text rows.

Parser dispatch and resource-object selection:

- Host bytes enter through `0xa904` and the parser loop at `0x11774`.
- `ESC )s0W` reaches `0x11f96` through the same `)s#W` command family as
  downloaded glyphs, but the zero parsed count schedules delayed handler
  `0x15d0a` instead of the nonzero payload handler `0x16c14`.
- `0x121cc` stores restored record `80 57 00 00 00 00`; `0x12218` later
  restores that record and calls `0x15d0a`.
- `0x15d0a` writes descriptor budget `0x783140`, consumes descriptor bytes
  through `0x1599c`, and routes bit-30-clear current records with status `1`
  through `0x15e42 -> 0x16606`.
- The continuation route uses status `2` and
  `0x15e64 -> 0x15c4c`. Both routes rejoin the parser through
  `0x15dcc -> 0x12328`, so the next visible command is the following
  printable handler `0xd04a`.

Current-record install:

- `0x16606` clears stale continuation fields before validating the fixed
  resource descriptor.
- In fixture
  `host-fetched 0x15d0a current-record resource object feeds fixed-record render`,
  the selected object installs glyph `0x21` into the fixed-record table entry
  at payload `+0x48`.
- The canonical fixed-record bytes are
  `02 03 04 00 00 00 02 00`; the bitmap bytes copied to payload `+0x0200`
  are `aa 55 f0 0f c3 3c`.
- The copy succeeds with status `1`, stream position `6`,
  `0x783140 = 0`, zero drained bytes, and parser return to `0xd04a`.

Continuation install:

- A partial `0x16606` copy saves continuation block fields `0x7827c6`,
  `0x7827da`, `0x7827c8`, `0x7827ca`, `0x7827ce`, `0x7827d2`,
  `0x7827d6`, and `0x7827d8`.
- `0x15c4c` consumes that block on the later status-`2` descriptor route. A
  status-`1` resume clears the block, while a status-`2` resume advances and
  resaves it.
- Fixture `host-fetched 0x15d0a continuation resource object resumes fixed-record
  render` splits bitmap copy across two packets: first `aa 55`, then `f0 0f c3 3c`.
- Fixture `host-fetched 0x15d0a split-plane continuation resource object resumes
  fixed-record render` proves the odd-width split-plane form with record `03 02 04 00 00
  00 02 00` and completed bitmap layout `a0 a1 c0 c1 b0 d0`.
- Fixture `0x15c4c failed resource resume releases fixed-record object`
  covers status `0`: `0x15c4c` takes `0x15cb8..0x15ccc`, calls `0x17d7c`,
  rewrites payload `+0x48`, refreshes active-primary marker
  `0x7828de = 0`, and clears the continuation fields at `0x15cd6..0x15d08`.

Page-object and visible output effect:

- The font command itself does not draw. It updates fixed-record font data
  that later consumers read after the parser returns.
- `0x14c64` / `0x14e24` refresh the active fixed-record map, `0x1393a`
  builds the printable source, and `0x12f2e` queues the compact page object.
- The current-record fixture resolves printable `!` through the installed
  fixed record, emits object prefix
  `00 00 00 00 00 03 00 01 01 66 01`, and renders three mode-0 rows
  beginning at x `22`, y `6`.
- The split-plane continuation fixture emits object prefix
  `00 00 00 00 00 03 00 01 01 76 01` and renders two rows beginning at
  x `22`, y `7`.
- FF publication and active rendering follow the shared page pipeline:
  `0xff1e` publishes the page root, `0x1ed84` bridges it into the active
  render record, and `0x1ef6a` dispatches compact rendering from the queued
  object.

State classification for this path:

- Canonical state:
  current character `0x782f30`, selected bit-30-clear payload pointer
  `0x78285e`, fixed-record table entries at payload `+0x48`, bitmap bytes at
  payload `+0x0200`, active fixed-record font payload, queued compact page
  objects, and published page record.
- Derived/cache state:
  active fixed-record map from `0x14c64` / `0x14e24`, printable source object
  from `0x1393a`, compact selector `0x0003`, page bucket placement, active
  render record, and band-local compact renderer state.
- Parser scratch:
  restored delayed record `80 57 00 00 00 00`, descriptor byte budget
  `0x783140`, and continuation block `0x7827c6..0x7827da`.
- Firmware bookkeeping:
  route edge, copy status, stream position, reject reason, stale-continuation
  clear, active-context refresh marker `0x7828de`, and release rewrite state
  owned by `0x17d7c`.
- Unknown:
  broader fixed-record object-shape variants remain outside the covered
  fixtures. Exact unresolved boundaries are current-record variants between
  `0x16606..0x16770` and continuation variants between `0x15c4c..0x15d08`
  that are not the documented one-piece, linear-continuation,
  split-plane-continuation, partial-resave, or failed-release cases.

Evidence for this path is in
[downloaded-fonts.md](downloaded-fonts.md) and
[semantic-state-model.md](semantic-state-model.md), especially
`Fixed-Record Resource Object Checkpoint`. Key supporting listings are
`generated/disasm/ic30_ic13_font_payload_setup_015b80.lst`,
`generated/disasm/ic30_ic13_font_payload_object_path_016040.lst`,
`generated/disasm/ic30_ic13_font_payload_readers_016874.lst`,
`generated/disasm/ic30_ic13_font_fixed_record_release_017a24.lst`,
`generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`, and
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
- This is direct ROM table layout, not a parser uncertainty:
  `0x1fe76..0x1fe88` loads row-count table base `0x1fe8a`, shifts `D3` left
  by two, reads an unchecked longword pointer, and jumps to it. Entries
  `0..128` are valid; entry `128` at `0x2008a` points to `0x2008e`. Address
  `0x2008e` is executable row-copy code beginning with bytes `32 9a d3 c0`,
  so entries above `128`, including fallback counts `199..201`, interpret code
  bytes as pointers and yield `0x329ad3c0`.

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
  high-row matrix. The exact boundary is the unchecked `0x1fe8a + 4 * D3`
  table read entering row-copy code bytes at `0x2008e`. The parser, installed
  glyph state, low-byte selector truncation, publication bucket, render bucket,
  and row-split counts are documented.

Output effect:

- Rows `0x0001..0x00ff` have page-visible publication and renderer evidence in
  the downloaded-glyph row-count matrix.
- Rows `0x0101..0x0103` preserve installed row words and publish the low-byte
  short compact object, but no pixel-output claim is made after the invalid
  `0x1fe76` fallback index.
- Segmented-wide high-row paths are a separate solved branch for the sampled
  span/row combinations: they reach `0x1f264` or parser payload-count caps,
  not this short compact helper boundary.

Reproduction rule:

- A byte-stream reproducer must keep the installed glyph row word and the
  printable page-source low row byte as separate state. The installed object is
  canonical downloaded-glyph state written by `0x16498`; the low row byte is
  parser/page scratch consumed by `0x12f2e` when it chooses selector
  `0x0003`, `0x2003`, or `0x3003`.
- The supported short compact path is the continuous low-byte row family
  `0x0001..0x00ff`: it can be reproduced through publication bucket selection,
  `0x1ed84` / `0x1ef6a`, compact target `0x1effe`, and row-copy helper
  `0x1fe76`.
- A nonzero high byte does not by itself make the short compact path
  reproducible. If the low byte still selects selector `0x0003`, `0x1f414`
  can feed a fallback row count above `128` to `0x1fe76`; that crosses the
  unchecked jump-table boundary and has no documented pixel contract.
- High-row reproduction remains defined only when the byte stream selects a
  documented segmented-wide path, where `0x12f2e` queues selector `0x3003`
  and render dispatch reaches `0x1f264`, or when the parser payload-count cap
  stops the stream before renderer entry.

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

### Boundary: Downloaded-Glyph Wrapped Width Low Bytes

This is the exact ROM-local visible-output boundary for downloaded glyph
widths whose installed 16-bit span is preserved but whose printable page
source exposes only the low width byte to the compact page-object producer.
It is not a parser, install, publication, or bridge gap.

Boundary stream family:

- Fixture `downloaded glyph width-byte boundary truncates page-record span`
  installs spans `0x00ff`, every span `0x0100..0x0111`, `0x017f`,
  `0x0180`, `0x01fe`, and descriptor-rounded span `0x020d`.
- `0x16498` preserves the canonical installed width words at glyph record
  `+8`.
- The unflagged printable source presented to `0x12f2e` exposes only byte
  `+0`, so source width bytes `0x00..0x10` queue selector `0x0003`, while
  source width bytes `0x11..0xff` queue selector `0x1003`.

Producer and consumer behavior:

- The valid high-source-byte side publishes bucket `0`, bridges normally
  through `0x1ed84` / `0x1ef6a`, dispatches compact target `0x1effe`, enters
  wide compact helper `0x1f0d2`, and derives rows from the installed bitmap
  for sampled spans `0x00ff`, `0x0111`, `0x017f`, `0x0180`, and
  `0x01fe`.
- The wrapped low-source-byte side also publishes bucket `0` and bridges
  normally, but selector `0x0003` enters compact mode-0. Its full-span helper
  table entries are outside the decoded row-copy helper heads.
- The exact invalid target classes are fixture-pinned:
  `0x0100 -> 0x20700000`, `0x0101 -> 0x4e90202c`,
  `0x0102 -> 0x0066cc` at opcode `0x4a39`, `0x0103 -> 0x4cdf1030`,
  `0x0104 -> 0x4e750001`, `0x0105..0x010b -> 0xf4e00001`,
  `0x010c -> 0xf5960001`, `0x010d..0x0110 -> 0xf4e00001`, and
  `0x020d -> 0x4e904cdf`.
- The `0x0102` case is now pinned to the source table bytes, not just the
  target. Compact mode-0 helper `0x1f034` indexes longword table `0x1f08e`
  with the full span word in `D5`. Span `0x0102` shifts to offset `0x0408`,
  so the lookup reads entry address `0x1f08e + 0x0408 = 0x1f496`, whose bytes
  are `00 00 66 cc`. The target `0x0066cc` is the middle of an unrelated
  firmware routine: `generated/disasm/ic30_ic13_invalid_compact_mode0_target_0066c0.lst`
  shows it begins at `tst.b $7821b9.l`, can call scheduler/wait helpers
  `0x10c8`, `0x15a6`, `0x15ac`, and `0x9ac2`, and later unwinds with
  `movem.l (A7)+, D0/D5/A4-A5` / `unlk A6`. That is not a decoded row-copy
  helper prologue, so no pixel-output contract is claimed beyond selecting
  this invalid target.

State classification:

- Canonical state:
  downloaded glyph table entries, installed glyph width words, bitmap payload
  bytes, current page root, bucket `0` publication, and render-record bucket
  root.
- Derived/cache state:
  printable source low width byte, selector `0x0003` or `0x1003`, compact
  object byte, render bucket word `0`, wide compact full-chunk/remainder
  metadata, and invalid mode-0 helper target longwords.
- Parser scratch:
  restored `ESC )s#W` command records, payload byte budget `0x783140`, copy
  status `1`, zero-byte drain through `0x12328`, and next handler `0xd04a`.
- Firmware bookkeeping:
  downloaded-record allocation/release state around `0x16c14` / `0x16498`,
  stream allocator state, publication flag `0x782996`, and render-work
  progress.
- Hardware/external state:
  none for this boundary.
- Unknown:
  ROM-local execution after the documented invalid compact mode-0 helper
  targets. The parser, installed glyph state, low-byte width source, selector
  choice, publication bucket, render bridge, and valid compact-wide pixel side
  are documented. The in-firmware invalid sibling `0x0102 -> 0x0066cc` is
  bounded as an accidental computed jump into non-render control code under the
  compact renderer's register and stack context, not as an unknown page-record
  or render-dispatch edge.

Output effect:

- Source width bytes `0x11..0xff` are pixel-defined for the sampled wrapped
  spans: they render through `0x1f0d2` using the installed bitmap rows.
- Source width bytes `0x00..0x10` are not pixel-modeled after the invalid
  helper target is selected. They remain a precise invalid-helper boundary,
  not an unknown page-record or parser state.

Evidence:

- Detail note: [downloaded-fonts.md](downloaded-fonts.md), section
  `Downloaded Glyph Row-Count Publication Checkpoint`.
- Semantic checkpoint: `Downloaded Glyph Row-Count Publication Checkpoint` in
  [semantic-state-model.md](semantic-state-model.md).
- Fixture evidence:
  `downloaded glyph width-byte boundary truncates page-record span`,
  `downloaded glyph wide-remainder matrix publishes and renders compact
  chunks`, and `0x16b1a descriptor width helper emits only mode 1/2`.
- Disassembly evidence:
  `generated/disasm/ic30_ic13_invalid_compact_mode0_target_0066c0.lst`,
  `generated/disasm/ic30_ic13_font_payload_setup_015b80.lst`,
  `generated/disasm/ic30_ic13_font_payload_object_path_016040.lst`,
  `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`,
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`,
  `generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst`,
  and `generated/disasm/ic30_ic13_bitmap_row_copy_tables_01fa5c.lst`.

### Boundary: Segmented-Wide Downloaded-Glyph Fallback Source

This is the exact ROM-local visible-output boundary for sampled
segmented-wide high-row downloaded glyphs whose selected segment reaches
renderer `0x1f264`, but whose span-31 fallback row-copy would read past the
modeled A2 bitmap source. The same parser, install, publication, bridge, and
renderer path is pixel-defined for neighboring spans.

Boundary stream family:

- The primary fixture is `downloaded segmented-wide high-row span-31 fallback
  hits source boundary`.
- Sibling fixtures repeat the same split for row words `0x0182`, `0x01ff`,
  `0x0281`, `0x0282`, `0x02ff`, `0x0381`, `0x0382`, and `0x03ff`.
- The successful neighboring spans are documented for the same row family:
  spans `17`, `18`, and `32` render selected segment `1` through `0x1f264`
  with `32` current rows and `96` fallback rows derived from installed bitmap
  bytes.

Producer and consumer behavior:

- `0x16498` preserves the canonical installed row word and span in the
  downloaded glyph record. For row words above `0x00ff`, the printable source
  still exposes only the low row byte to `0x12f2e`.
- `0x12f2e` therefore publishes selector `0x3003` segments `1` and `0`
  under buckets `8` and `0` for low row bytes above `0x80`.
- `0xff1e`, `0x1ed84`, and `0x1ef6a` preserve the selected bucket path.
  Bucket `8` dispatches segment `1` through compact target `0x1effe` to
  segmented-wide renderer `0x1f264`.
- `0x1f414` splits the selected segment into `32` current rows and `96`
  fallback rows for the sampled high-row cases.
- Span `31` reaches the same selected-segment path but stops when
  `validate_wide_compact_row_copy` detects fallback A2 source read past the
  modeled bitmap at offset `+0xb50`.
- Higher row/span siblings diverge at a separate parser-count boundary:
  `0x04xx` span-31/span-32, `0x05xx` span-24-or-above, and tested higher
  oversized cases stop inside the `ESC )s#W` payload before renderer entry.

State classification:

- Canonical state:
  downloaded glyph table entries, installed row and width words, bitmap
  payload bytes, selector-`0x3003` bucket objects, bucket `8` selected segment
  `1`, bucket `0` segment `0`, and render-record bucket roots.
- Derived/cache state:
  printable source low row byte, segment row skip `0x80`, A2/A3 source
  offsets, full-chunk helper `0x2f27c`, `0x1f1ac` remainder choice,
  `0x1f414` current/fallback split, and fallback A2 source offset `+0xb50`.
- Parser scratch:
  restored `ESC )s#W` records, payload byte budget `0x783140`, copy status
  `1`, zero-byte drain through `0x12328`, and next handler `0xd04a` for the
  successful below-cap cases.
- Firmware bookkeeping:
  downloaded-record allocation/release state around `0x16c14` / `0x16498`,
  stream allocator state, publication flag `0x782996`, and render-work
  progress.
- Hardware/external state:
  none for the ROM-local renderer source-boundary classification.
- Unknown:
  byte-stream variants that change the explicit span-31 source-boundary cases.
  The parser/install/publication/bridge path, selected segment, renderer
  target, row split, and exact source offset are documented.

Output effect:

- The successful siblings are pixel-defined: the sampled rows render selected
  segment `1` through `0x1f264` with current and fallback rows derived from
  the installed bitmap.
- The span-31 siblings through row `0x03ff` are not pixel-modeled past A2
  offset `+0xb50`. That is a bounded source-read edge, not an unknown selector
  or render-dispatch edge.
- Oversized higher siblings are parser-count boundaries before renderer entry,
  not `0x1f264` source-boundary cases.

Evidence:

- Detail note: [downloaded-fonts.md](downloaded-fonts.md), section
  `Downloaded Glyph Row-Count Publication Checkpoint`.
- Renderer detail: [page-raster-imaging.md](page-raster-imaging.md),
  compact glyph row-copy sections around `0x1f264`.
- Fixture evidence:
  `downloaded segmented-wide high-row span-31 fallback hits source boundary`,
  `downloaded segmented-wide row-0x0182 span-31 fallback hits source
  boundary`,
  `downloaded segmented-wide row-0x01ff span-31 fallback hits source
  boundary`,
  `downloaded segmented-wide row-0x0281 span-31 fallback hits source
  boundary`,
  `downloaded segmented-wide high-row 0x02xx span-31 matrix hits source
  boundary`, and
  `downloaded segmented-wide high-row 0x03xx span-31 matrix hits source
  boundary`.
- Disassembly evidence:
  `generated/disasm/ic30_ic13_font_payload_setup_015b80.lst`,
  `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`,
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`,
  `generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst`,
  `generated/disasm/ic30_ic13_glyph_row_copy_helper_02f27c.lst`, and
  `generated/disasm/ic30_ic13_bitmap_row_copy_tables_01fa5c.lst`.

### Boundary: Downloaded-Glyph Payload Count Cap

This is the exact parser/payload boundary for segmented-wide high-row
downloaded glyphs whose required `ESC )s#W` bitmap byte count exceeds the
parser's restored count cap. These cases do not reach the installed-glyph
writer or renderer in this host-fetched stream shape.

Boundary stream family:

- Fixtures `downloaded segmented-wide high-row 0x04xx oversized payload counts
  stop before renderer`,
  `downloaded segmented-wide high-row 0x05xx oversized payload counts stop
  before renderer`, and
  `downloaded segmented-wide high-row parser-limit oversized counts stop
  before renderer` record the stopped cases.
- Successful neighboring cases are documented for the same family:
  rows `0x0481`, `0x0482`, and `0x04ff` render spans `17`, `18`, and `24`;
  rows `0x0581` and `0x0582` render spans `17`, `18`, and `23`;
  row `0x05ff` renders spans `17`, `18`, and `21`;
  rows `0x0681` and `0x0682` render spans `17`, `18`, and `19`;
  row `0x06ff` renders spans `17` and `18`; rows `0x0781`, `0x0782`, and
  `0x0787` render span `17`.

Producer and consumer behavior:

- The parser-delayed payload path restores an `ESC )s#W` byte count clamped to
  `0x7fff`.
- The byte count consumed by the downloaded-character bitmap path is
  `row_word * span` for this segmented-wide family. Since segmented-wide
  rendering requires span `>= 17`, the largest row word that can still fit the
  restored count cap at the minimum span is
  `floor(0x7fff / 17) = 0x0787`. The adjacent row `0x0788` at span `17`
  requires `0x7ff8` payload bytes and therefore cannot reach `0x16498` or
  `0x1f264` through this host-fetched command shape.
- Oversized products such as `0x0481*31`, `0x0481*32`, `0x0482*31`,
  `0x0482*32`, `0x04ff*31`, `0x04ff*32`, `0x0581*24`, `0x0581*32`,
  `0x0582*24`, `0x0582*32`, `0x05ff*22`, `0x05ff*32`, `0x0681*20`,
  `0x0682*20`, `0x06ff*19`, `0x0781*18`, `0x0782*18`, `0x0787*18`, and
  `0x0788*17` exceed that cap.
- For those streams, the restored payload count stops inside the bitmap data
  before the next command byte is reached. The fixtures record
  `command_prefix_length`, `parser_stop_offset`, and `full_payload_end_offset`.
- Because the stream stops before `0x16498` completes an installed glyph
  object, no selector `0x3003` page object is produced and no `0x1f264`
  renderer/source boundary is reached.

State classification:

- Canonical state:
  none newly installed for the stopped oversized payload. Successful
  neighboring below-cap cases install canonical downloaded glyph row/width
  words, bitmap bytes, and selector-`0x3003` bucket objects.
- Derived/cache state:
  computed row/span product, minimum segmented-wide span `17`, cap-derived
  maximum row `0x0787`, clamped restored payload count `0x7fff`, parser stop
  offset, and full payload end offset.
- Parser scratch:
  delayed `ESC )s#W` records, pending payload handler state, payload byte
  budget `0x783140`, and the host byte-source position where the stream stops
  before renderer entry.
- Firmware bookkeeping:
  partial parser/delayed-payload state used to drain or resume command input;
  no completed downloaded-record allocation or page publication for the
  stopped cases.
- Hardware/external state:
  none for this ROM-local parser cap.
- Unknown:
  no ROM-local renderer edge is open for these oversized streams because they
  do not reach the renderer. Remaining uncertainty is only what a broader
  host/application stream does after the parser stop point.

Output effect:

- Below-cap neighbors produce installed glyphs, publish selector `0x3003`
  buckets, and render selected segment `1` through `0x1f264`.
- Oversized cases produce no page pixels in this path. They stop at the
  parser payload-count boundary before installed glyph publication and before
  render dispatch.
- Row `0x0787` at span `17` is the last sampled segmented-wide high-row case
  that reaches the renderer through this host-fetched `ESC )s#W` shape; the
  adjacent `0x0788*17` stream stops at the count cap before any installed
  glyph record or page object exists.

Evidence:

- Detail note: [downloaded-fonts.md](downloaded-fonts.md), section
  `Downloaded Glyph Row-Count Publication Checkpoint`.
- Renderer summary: [page-raster-imaging.md](page-raster-imaging.md),
  compact glyph row-copy checkpoint.
- Semantic checkpoint: `Downloaded Glyph Row-Count Publication Checkpoint` in
  [semantic-state-model.md](semantic-state-model.md).
- Fixture evidence:
  `downloaded segmented-wide high-row 0x04xx oversized payload counts stop
  before renderer`,
  `downloaded segmented-wide high-row 0x05xx oversized payload counts stop
  before renderer`, and
  `downloaded segmented-wide high-row parser-limit oversized counts stop
  before renderer`.
- Disassembly evidence:
  `generated/disasm/ic30_ic13_font_payload_setup_015b80.lst`,
  `generated/disasm/ic30_ic13_font_payload_readers_016874.lst`,
  `generated/disasm/ic30_ic13_font_payload_object_path_016040.lst`, and
  `generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst`.

## Worked Path: Compact Glyph Row-Copy Helpers

This path covers the shared renderer helper family that turns compact text and
downloaded-glyph page objects into destination bitmap rows. It is downstream
of parser dispatch, page-object allocation, publication, and render-record
copying: by the time this path starts, `0x1ef6a` has selected a compact bucket
object and `0x1effe` is dispatching its selector byte.

Entry and dispatch:

- `0x1efc2` walks compact bucket objects from the active render record and
  calls `0x1effe` for each object whose band word is active.
- `0x1effe` dispatches selector forms to the compact glyph renderers:
  normal compact `0x1f034`, wide compact `0x1f0d2`, segmented compact
  `0x1f1f0`, and segmented-wide compact `0x1f264`.
- `0x1f354` resolves the page-record context slot and glyph id. Bit-30-set
  contexts use the resource offset-table form; bit-30-clear contexts use
  fixed eight-byte inline/downloaded glyph entries.
- `0x1f414` splits returned row count `D3` into current-band rows and
  fallback rows before the selected row-copy helper runs.

Helper-family contract:

- `0x1f034` and `0x1f1f0` use main width table `0x1f08e`. Width indexes
  `1..16` select row-copy helpers `0x1fa5c`, `0x1fe76`, `0x20290`,
  `0x207ac`, `0x20cc8`, `0x212e4`, `0x21900`, `0x2201c`, `0x22738`,
  `0x22f54`, `0x23770`, `0x24090`, `0x249b0`, `0x253d0`, `0x25df0`, and
  `0x26910`.
- `0x1f0d2` and `0x1f264` render full 16-byte chunks through helper
  `0x2f27c`, then use wide-remainder table `0x1f1ac` for remainder widths
  `1..15`. Remainder `0` means another full chunk, not a remainder helper.
- Every helper uses a row-count jump table. The table indexes `D3`, jumps into
  an unrolled copy tail, and copies one destination row per table step.
- Even byte widths copy words only from `A2`. Odd byte widths copy word
  pairs from `A2` plus one trailing byte per row from `A3`.
- Destination row advance comes from stride `0x783a1c`. Wide and
  segmented-wide helpers also use caches `0x783a40`, `0x783a42`,
  `0x783a44`, `0x783a46`, and `0x783a48` written by `0x1f0d2` and
  `0x1f264`.

State classification:

- Canonical state:
  render-record compact bucket roots, page-root context slots copied by
  `0x1edc6`, selected font/downloaded glyph context records, glyph table
  entries, installed glyph row/width/mode words, and bitmap payload bytes.
- Derived/cache state:
  active context longword `0x783a2c`, destination stride `0x783a1c`,
  current-band fields `0x783a20`, `0x783a22`, and `0x783a28`, glyph source
  registers `A2` and `A3`, span `D1`, row count `D3`, row-split outputs from
  `0x1f414`, and wide-mode caches `0x783a40..0x783a48`.
- Parser scratch:
  none consumed by these helpers. Parser records and delayed downloaded-glyph
  payload records are upstream evidence for installed glyph data, not state
  read by row-copy helpers.
- Firmware bookkeeping:
  render-work progress fields, continuation fields for partial downloaded
  payload copies, and invalid row-copy table targets used only as failure
  boundaries.
- Hardware/external state:
  none for the software row-copy contract.
- Unknown:
  remaining legal command cross-products are only useful when they expose a
  new ROM-derived row-copy object form, helper target, or continuation field.
  ROM-local invalid-index edges remain exact boundaries rather than modeled
  pixels: short compact `0x1fe76` fallback row indexes above `128`, and
  wrapped low-byte width cases that select non-helper mode-0 table targets.

Output effect:

- Built-in-font fixtures prove host-fetched primary/secondary selection and
  symbol-set variants install page-root context slots, queue compact objects,
  pass through `0x1ed84` / `0x1ef6a`, and render visible rows through this
  helper family.
- Downloaded-glyph fixtures prove parser-produced `ESC )s#W` payloads install
  normal, wide, segmented, and segmented-wide glyph payloads, publish compact
  objects, and derive rows from installed bitmap bytes through all main helpers
  and the wide chunk/remainder path.
- Row-count and width-boundary fixtures classify the failures separately:
  installed canonical row/width words may survive, while the current printable
  source record exposes only low row/width bytes to `0x12f2e`; those wrapped
  page-object bytes can choose invalid helper-table entries.
  The grouped renderer-side contract is
  `Invalid Compact Helper Boundary Composition` in
  [page-raster-imaging.md](page-raster-imaging.md): the short high-row
  `0x1fe76 -> 0x1fe8a` fallback-index boundary and the wrapped low-width
  `0x1f034 -> 0x1f08e` mode-0 boundary are exact computed-jump boundaries,
  not parser, publication, bridge, or physical-output gaps.

Evidence:

- Detail note:
  [page-raster-imaging.md](page-raster-imaging.md), section
  `Subrenderer Payloads`.
- Downloaded-glyph producer note:
  [downloaded-fonts.md](downloaded-fonts.md), section
  `Downloaded Glyph Row-Count Publication Checkpoint`.
- Disassembly evidence:
  `generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst`,
  `generated/disasm/ic30_ic13_bitmap_row_copy_tables_01fa5c.lst`,
  `generated/disasm/ic30_ic13_glyph_row_copy_helper_02f27c.lst`, and
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`.
- Generated table evidence:
  `generated/analysis/ic30_ic13_render_subrenderers.md` and
  `generated/analysis/ic30_ic13_render_row_copy_fixtures.md`.
- Fixture families:
  `downloaded glyph width-span matrix publishes and renders all main
  helpers`,
  `downloaded glyph wide-remainder matrix publishes and renders compact
  chunks`,
  `downloaded glyph segmented-wide matrix publishes and renders compact
  chunks`,
  `downloaded segmented-wide row-span cross-products render selected segment`,
  `downloaded glyph width-byte boundary truncates page-record span`,
  `downloaded glyph row-count matrix publishes and renders additional
  short/segmented counts`, and
  `host-fetched rows-0x102 downloaded glyph FF publication truncates
  page-record rows`.

## Worked Path: Reset And Default Environment

This path covers `ESC E` software reset. It is both a page-boundary command
and an environment rebuild: if a current page root is valid, reset publishes it
before resetting parser, page, font, raster, and default-environment state.

Primary streams:

```text
! ESC E
ESC E
```

Parser dispatch:

- Host bytes enter through `0xa904` and parser loop `0x11774`.
- Printable `!` reaches `0xd04a`, ensures a current page root through
  `0x10084`, and queues a compact text object through `0x12f2e` /
  `0x1387c`.
- `ESC E` reaches reset handler `0xcc52`.

Reset command behavior:

- `0xcc52` calls `0xcc70`, `0xcbd4`, and `0xe146`, then clears reset status
  byte `0x782a93`.
- `0xcc70` flushes pending text through `0xf34a`, calls `0xff1e` to publish or
  clear the current root, waits through `0x9ac2`, clears orientation byte
  `0x782da3`, calls environment rebuild helper `0xcda2`, and resets
  raster/page-derived state.
- `0xcda2` rebuilds the four page/control pool records at `0x780f02`, copies
  canonical defaults, recomputes VMI/HMI, resets parser scratch pointers, and
  writes reset bookkeeping fields.
- `0xcbd4` refreshes HMI and active-symbol snapshots from current-font context
  `0x782ee6`.
- `0xe146` resets parser/data-chain records and text accumulation state,
  freeing any 0x100-byte data-chain allocations through `0x18b4`.

Default inputs consumed by reset:

- `0x78219d`: default byte copied to reset environment word `0x782da4` by
  `0xcda2`.
- `0x78219e`: default line-spacing word converted into reset VMI `0x783160`.
- `0x7821a2`: default environment/paper byte copied to `0x782da6` when reset
  gate `0x7810b2` permits it; `0xcc70` also copies it to `0x780e8f` when
  `0x780e3c == 1`.
- `0x5e80`, menu/update handlers `0x5060`, `0x50be`, and `0x52ba`, retained
  record helpers `0x96c4` / `0x97e4`, and maintenance helpers `0x56c2` /
  `0x571e` / `0x5a62` produce or maintain those canonical defaults. Their
  detailed producer contract lives in
  [reset-default-environment.md](reset-default-environment.md).

Default record producer chain:

- `0x7822d5` selects the compact default-record bank. The ROM scales it
  through helper `0x332ee(..., 3)` and uses
  `0x780eda + 2 * scaled_index` as the active backing record base.
- Loader `0x5e80` copies backing record byte `+0` to canonical default
  `0x78219d`, copies record word `+2` to canonical line-spacing word
  `0x78219e`, and derives canonical byte `0x7821a2` from record byte `+5`
  bit 2 as `0x80` or `0`.
- Menu/update handlers mirror field writes into both the backing record and
  the canonical reset defaults: `0x5060` updates record byte `+0` and
  `0x78219d`; `0x50be` updates record byte `+5` bit 2 and `0x7821a2`;
  `0x52ba` updates record word `+2` and `0x78219e`.
- Record maintenance helper `0x56c2` selects the active bank by scanning
  word-2 entries for bit 15. Helper `0x571e` rotates/copies three-word
  record groups, updates maintenance counter `0x780ef0`, and clears auxiliary
  flags at `0x780eb8`. Helper `0x5a62` either clears all 16 backing records
  for input byte `0xde` or rebuilds records from ROM fallback tables
  `0xba3e` and `0xba44`.
- Startup helper `0x5a16` forces dirty flags `0x780eba..0x780ed8` to all
  ones, calls retained-record read helper `0x97e4`, then clears the flags.
  The observed startup caller `0x2c84` does not branch on a readback success
  value from `0x5a16`; active-record validation failure later reports
  `67 SERVICE` through `0x56c2 -> 0x1284`.
- Commit helper `0x96c4` serializes dirty records through command class
  `0x83`, calls `0x97e4` for readback through command class `0x86`, restores
  the pre-read RAM image, and compares dirty readback words. Exhausted commit
  retries set status bit `0x780e39.3` through
  `0x9bee(0x780e36, 0x00000008)`, which the service loop consumes as
  `68 SERVICE`.
- Serial helper `0x9a4a` writes low-three-bit phase pairs to `$a400` through
  shadow `0x7828f6`. The retained-record callers use `1 -> 3` for zero bits,
  `5 -> 7` for one bits, and `1 -> 0` for deassert. Read helper `0x994e`
  samples `$8c01.1` into retained-record readback words.
- Panel/service byte sampler `0xa3ca` returns a debounced byte from
  `$8000.w & 0xff`; dispatcher `0x3dae` maps stable service bytes through the
  table at `0x3d66`, including default-store paths `0xef -> 0x3ef8`,
  `0xfd -> 0x3f6a`, and `0xbf -> 0x4922`.

Publication and output effect:

- With a valid current page root, `0xcc70 -> 0xff1e` publishes queued page
  objects before the environment rebuild. The reset page then follows the
  normal render path through `0x1ed84`, `0x1edc6`, and `0x1ef6a`.
- With no current page root, `ESC E` clears missing-root state without
  inventing a page object or publication.
- Fixtures `mixed printable/reset page-record stream queues through 0x1387c
  before reset`, `mixed printable/reset page-record finalization publishes
  bridged record`, and `addressed printable reset publishes rendered page
  record` prove the valid-root `! ESC E` path through compact bucket storage,
  `0xff1e` publication, bridge, and ROM-derived row construction.
- Fixtures `ESC E stream clears missing page root without publication` and
  `host-fetched ESC E clears missing page root without publication` prove the
  missing-root path from parser dispatch to reset with no page output.

State classification:

- Canonical state:
  reset defaults `0x78219d`, `0x78219e`, `0x7821a2`, reset gate `0x7810b2`,
  page/control pool records at `0x780f02`, current root `0x78297a`, published
  pointer `0x780ea6`, current-font context `0x782ee6`, and parser/data-chain
  base records.
- Derived/cache state:
  reset HMI `0x78315c`, VMI `0x783160`, top offset `0x782dce`, raster block
  `0x783170`, active-symbol snapshots, and page-control bucket-array pointers
  rebuilt as `0x7810bc + 0x400*n`.
- Parser scratch:
  parser/control records `0x782c1e..0x782c6d`, parser cursor `0x782c6e`,
  scratch pointer `0x782a26`, cursor-stack pointer `0x782d36`, data-chain
  pointer `0x782d76`, and text accumulation bytes `0x783196..0x783199`.
- Firmware bookkeeping:
  publication flag `0x782996`, reset latch bytes `0x782997` / `0x782998`,
  cleared flags `0x782990`, `0x78297e`, `0x783184`, `0x783185`,
  `0x782f2c`, `0x78318f`, `0x783190`, status byte `0x782a93`,
  default-record dirty flags `0x780eba..0x780ed8`, retained-readback buffers
  `0x782252..0x782270`, pre-read snapshot `0x782232..0x782250`, and
  maintenance words `0x780ede` / `0x780ef0`.
- Hardware/external state:
  physical retained-storage device behind `$a400` / `$8c01`, external
  `$8000.w` panel/service producer, and board-level pin names remain external.
- Unknown:
  no ROM-local middle edge remains for the software-visible `ESC E` valid-root
  publication path, missing-root no-publication path, selected-record load into
  canonical defaults, canonical default consumption, VMI/HMI rebuild,
  parser/data-chain clearing, or compact-text rendered reset page. Remaining
  reset/default uncertainty is external physical/device identity and
  manual-facing names for some latches.

Evidence:

- Detail note: [reset-default-environment.md](reset-default-environment.md).
- Publication note: [publication-commands.md](publication-commands.md).
- Semantic checkpoint: `Reset And Default Environment` and
  `Publication Commands To ROM-Derived Page Rows` in
  [semantic-state-model.md](semantic-state-model.md).
- Fixture evidence:
  - `ESC E stream publishes valid page root and resets environment/parser state`
  - `ESC E stream clears missing page root without publication`
  - `host-fetched ESC E clears missing page root without publication`
  - `addressed printable reset publishes rendered page record`
  - `0x5e80 -> 0xcda2 reset consumes default record outputs`
  - `0xcfea/0xcf52/0x104d8 convert default line spacing to reset VMI`
  - `0x5e80 loads selected default record into canonical defaults`
  - `0x5060/0x50be/0x52ba update default record and dirty flags`
  - `0x5a16 forces retained-record read mask then clears it`
  - `0x56c2 selects active retained record or reports 67 SERVICE`
- Disassembly evidence:
  `generated/disasm/ic30_ic13_esc_e_reset_00cc52.lst`,
  `generated/disasm/ic30_ic13_esc_e_environment_reset_00cda2.lst`,
  `generated/disasm/ic30_ic13_esc_e_metric_refresh_00cbd4.lst`,
  `generated/disasm/ic30_ic13_esc_e_parser_state_reset_00e146.lst`,
  `generated/disasm/ic30_ic13_default_env_load_005e80.lst`,
  `generated/disasm/ic30_ic13_default_env_menu_update_004fb0.lst`,
  `generated/disasm/ic30_ic13_default_env_record_maintenance_0056c2.lst`,
  `generated/disasm/ic30_ic13_retained_record_bulk_load_005a16.lst`,
  `generated/disasm/ic30_ic13_nvram_default_record_commit_0096c4.lst`,
  `generated/disasm/ic30_ic13_nvram_serial_bit_helpers_009860.lst`,
  `generated/disasm/ic30_ic13_panel_service_dispatch_003dae.lst`,
  `generated/disasm/ic30_ic13_panel_service_byte_source_00a39a.lst`,
  and `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`.

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
- The published FF page-record rows use the pre-eject compact text row path.

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

## Worked Path: Publication Commands To ROM-Derived Page Rows

This path covers page-environment publication commands whose visible pixels
come from already queued page objects, while the command itself changes page
or environment state around the publication boundary. It extends the FF-only
publication path to reset, page size, orientation, paper source, and
copy-count streams.

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

Publication command-to-output matrix:

- `ESC E` reset:
  handler `0xcc52` reaches `0xcc70`, which flushes pending text, publishes a
  valid current root through `0xff1e`, and only then rebuilds parser,
  page-environment, raster, and default state. If no current root exists, reset
  clears missing-root state without synthesizing a publication.
- `FF` / form feed:
  handler `0xf0f0` publishes the current root through `0xff1e` after
  line-termination side effects such as CR-style x reset. Its visible pixels
  are the objects queued before FF.
- `ESC &l#A` page size:
  handler `0xfc74` publishes queued objects before writing the new page code
  and recomputing page geometry. The rendered page uses the old root; the new
  geometry affects following objects.
- `ESC &l#O` orientation:
  handler `0x10220` publishes queued objects before changing orientation byte
  `0x782da3` and active extents. The published pixels are therefore still from
  the pre-orientation page root.
- `ESC &l#H` paper source:
  handler `0xef62` flushes/publishes queued text, refreshes cursor state, and
  then writes paper-source/output state such as `0x782da6`, `0x782998`,
  `0x780e8f`, and `0x780e26`.
- `ESC &l#X` copies:
  handler `0xeef0` stores copy count `0x782da4` but does not publish. The
  later FF publication copies that count into pool-header word `+0x0c`.

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
  middle edge remains for these streams. Remaining uncertainty is limited to
  page-environment variants that produce different pool-header fields,
  geometry, bucket roots, bridge state, or row-construction inputs.

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

## Worked Path: Page Length, Wrap, And Perforation Controls

This path covers layout controls whose command bytes normally do not emit
pixels immediately, but whose state changes alter the next printable object or
the next vertical overflow decision. It links the page-length, VMI/LPI,
top-margin, text-length, perforation-skip, and wrap handlers to shared
printable/vertical consumers and the following-printable page-record output
path.

Representative streams:

```text
ESC &l66P !
ESC &l0P
ESC &l6D !
ESC &l3E !
ESC &l60F !
ESC &l1L !
ESC &s0C
ESC &s1C
```

Parser dispatch:

- All host-fetched streams enter through byte fetch `0xa904`, parser wrapper
  `0xda9a`, and parser loop `0x11774`.
- `ESC &l66P` and `ESC &l0P` dispatch to page-length handler `0xf9e8`.
- `ESC &l#C` dispatches to VMI handler `0xcb00`.
- `ESC &l#D` dispatches to LPI handler `0xc992`.
- `ESC &l#E` dispatches to top-margin handler `0xece2`.
- `ESC &l#F` dispatches to text-length handler `0xea9e`.
- `ESC &l1L` dispatches to perforation-skip handler `0xee64`.
- `ESC &s0C` and `ESC &s1C` dispatch to wrap-mode handler `0xedb0`.
- The following printable byte `0x21` reaches `0xd04a`, then page-record
  queueing through `0x12f2e` / `0x1387c`, and later render dispatch through
  `0x1ed84` / `0x1ef6a`.

Command behavior:

- `ESC &l66P` converts the parsed line count through current VMI
  `0x783160`, writes page extent `0x782dba = 3300`, selects internal page
  code `2`, recomputes geometry/text-bottom state, and refreshes the
  following printable cursor to compact coordinate `0x9001`.
- `ESC &l0P` takes the default-page branch. It publishes pending state if a
  current root exists, optionally mirrors paper-source byte `0x782da6` to
  software-visible output byte `0x780e8f`, signals control word `0x780e26`,
  and selects the default page code from `0x780e97` or fallback code `2`.
- `ESC &l#C` converts an absolute 1/48-inch VMI value using 75 packed
  subunits per unit. Values whose converted VMI is zero leave the prior value
  unchanged; accepted values write `0x783160` and refresh vertical cursor
  `0x782c8e`.
- `ESC &l#D` accepts the ROM's LPI set, maps it to packed VMI `0x783160`,
  marks modified-layout byte `0x782ee1`, and refreshes vertical cursor
  `0x782c8e`.
- `ESC &l#E` scales top-margin lines through current VMI `0x783160`, rejects
  zero VMI and positions at or beyond page extent `0x782dba`, writes top
  offset `0x782dce`, restores default text length, and refreshes vertical
  cursor.
- `ESC &l#F` scales text-length lines through VMI, rejects lengths beyond the
  remaining page below current top margin, writes bottom/text-length limit,
  and restores the default bottom when selector `0` is used.
- `ESC &l1L` sets perforation-skip byte `0x783191 = 1`. Selector `0` clears
  it; selectors outside `0..1` leave the prior byte unchanged.
- `ESC &s0C` sets end-of-line wrap flag `0x783190 = 1`. `ESC &s1C` clears
  it; selectors outside `0..1` preserve the previous flag.

Downstream consumers:

- Printable prechecks `0xd28a` and `0xd6bc` consume `0x783190`. With wrap
  clear, horizontal overflow returns precheck result `1` and suppresses the
  glyph queue. With wrap set, the precheck calls recovery helper `0xf054`,
  retries from recovered x `0`, and returns `0` when the retried glyph fits.
  Vertical extent failure still returns reject result `1`.
- Vertical overflow helper `0xf36c` consumes cursor y `0x782c8e`,
  text-bottom/perforation limit `0x782dc2`, and perforation-skip byte
  `0x783191`. Below-limit cursor, zero `0x782dc2`, and disabled
  perforation skip all return `D7 = 1` without page eject. Enabled overflow
  with `cursor_y > 0x782dc2` calls modeled page-eject helper `0xf124`,
  increments page finalization, clears pending text, recomputes y from top
  offset and VMI, and returns `D7 = 0`.
- Cursor and vertical movement handlers consume `0x783160`, `0x782dce`,
  `0x782dd2`, and the derived text-bottom/perforation limit when computing
  printable y coordinates and page-boundary decisions.
- The `ESC &l1L !` and `ESC &l66P !` streams prove that these delayed layout
  controls reach visible page-record output when followed by printable data.
  The perforation-skip stream pins the `0xee64` writer plus the following
  compact object and ROM-derived row construction. The page-length stream
  pins the `0xf9e8 -> 0xd04a` path, including refreshed cursor y and the
  compact text object.

Layout command-to-output matrix:

- `ESC &l#P` page length:
  handler `0xf9e8` converts line count through VMI `0x783160`, writes page
  extent `0x782dba`, selects or restores the page code, and recomputes
  text-bottom/geometry state. It creates no glyph object directly; the next
  printable byte consumes the refreshed cursor and geometry through `0xd04a`.
- `ESC &l0P` default page length:
  the same handler takes the default-page branch, can publish an existing
  current root, can mirror paper-source state to `0x780e8f` / `0x780e26`,
  and then restores the default page code. Its immediate visible output, when
  a root exists, is the pre-command page publication.
- `ESC &l#C` VMI and `ESC &l#D` LPI:
  handlers `0xcb00` and `0xc992` write line advance `0x783160`, then refresh
  pending vertical cursor state. Later LF/FF, `ESC &a#R`, `ESC =`, VFC, page
  length, and printable placement consume the new line advance.
- `ESC &l#E` top margin:
  handler `0xece2` writes top offset `0x782dce`, restores default text
  length, and refreshes cursor y. Following printable bytes consume the new
  y origin; VFC and overflow helpers consume it for page-boundary math.
- `ESC &l#F` text length:
  handler `0xea9e` writes the bottom/text-length limit used to derive
  `0x782dc2`. It changes later vertical overflow and perforation decisions
  rather than queueing a page object immediately.
- `ESC &l#L` perforation skip:
  handler `0xee64` writes byte `0x783191` for selectors `0` and `1`. It is
  consumed by vertical overflow helper `0xf36c`, which either leaves the
  caller on the no-eject path or calls page-eject helper `0xf124`.
- `ESC &s#C` wrap:
  handler `0xedb0` writes byte `0x783190` for selectors `0` and `1`.
  Printable prechecks `0xd28a` and `0xd6bc` consume it before queueing; wrap
  disabled rejects horizontal overflow, while wrap enabled routes through
  recovery helper `0xf054` and then retries placement.
- Following printable consumer:
  after any of these layout commands, printable handler `0xd04a` is the first
  page-object producer in the documented streams. It queues compact text
  through `0x12f2e` / `0x1387c`, and later publication/rendering uses the
  normal `0xff1e -> 0x1ed84 -> 0x1edc6 -> 0x1ef6a` path.

Output effect:

- Page-length, VMI/LPI, top-margin, text-length, wrap-mode, and
  perforation-skip commands do not create glyph pixels by themselves in the
  covered streams.
- Page length changes later printable placement and page geometry. The
  nonzero fixture proves the `ESC &l66P !` stream queues the following
  printable at compact coordinate `0x9001` after the handler recomputes
  vertical extent and cursor-derived state.
- VMI/LPI, top-margin, and text-length commands change later vertical cursor,
  page-boundary, and following-printable placement decisions.
- Wrap mode changes whether later horizontal overflow is rejected or recovered
  into a new-line retry before queueing.
- Perforation skip changes whether later vertical overflow performs a page
  eject through `0xf124` or leaves the caller on the reject/no-eject path.

State classification for this path:

- Canonical state:
  page length/vertical extent `0x782dba`, VMI `0x783160`,
  top offset `0x782dce`, bottom/text-length state `0x782dd2`,
  end-of-line wrap flag `0x783190`, perforation-skip byte `0x783191`,
  current cursor x/y `0x782c8a` / `0x782c8e`, page code/default selection
  bytes, paper-source byte `0x782da6`, and software-visible output/control
  bytes `0x780e8f` / `0x780e26`.
- Derived/cache state:
  text-bottom/perforation limit `0x782dc2`, compact text coordinates,
  recomputed page geometry, bucket selection, and render-band caches created
  after `0x1ed84`.
- Parser scratch:
  six-byte command records for `ESC &l#P`, `ESC &l#C`, `ESC &l#D`,
  `ESC &l#E`, `ESC &l#F`, `ESC &l#L`, and `ESC &s#C`, parser cursor
  `0x78299e`, and host-ring drain state from `0xa904`.
- Firmware bookkeeping:
  pending publication latches, current-root clear state, pending text latch,
  page-finalization counters, and scheduler progress words after a later
  publication.
- Hardware/external state:
  `0x780e8f` and `0x780e26` are ROM-visible output/control bytes in the
  `ESC &l0P` branch. Their physical formatter-to-engine timing is outside
  the ROM-local proof.
- Unknown:
  no unresolved ROM-local parser-to-handler or handler-to-following-printable
  middle edge remains for these covered streams. Remaining uncertainty is the
  manual-facing naming of some latches and physical device behavior past
  `0x780e8f` / `0x780e26`.

Evidence for this path is in
[direct-control-codes.md](direct-control-codes.md),
[publication-commands.md](publication-commands.md),
[semantic-state-model.md](semantic-state-model.md), and
[end-to-end-reproduction-map.md](end-to-end-reproduction-map.md). Key
supporting listings are
`generated/disasm/ic30_ic13_page_length_handler_00f9e8.lst`,
`generated/disasm/ic30_ic13_hmi_vmi_handlers_00ca8c.lst`,
`generated/disasm/ic30_ic13_perforation_skip_handler_00ee64.lst`,
`generated/disasm/ic30_ic13_wrap_mode_handler_00edb0.lst`, and
`generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`.
The top-margin and text-length handler evidence is carried by
`generated/analysis/ic30_ic13_direct_control_code_flow.md` and
[direct-control-codes.md](direct-control-codes.md). The fixtures cited by
those notes are:

- "0xf9e8 ESC &l#P converts VMI lines to page length and selects internal
  page code"
- "0xf9e8 ESC &l#P stream reaches page-length handler"
- "0xc992 ESC &l#D accepts ROM LPI set and refreshes pending vertical cursor"
- "0xcb00 ESC &l#C converts 1/48-inch VMI and keeps zero unmodified"
- "0xea9e ESC &l#F sets text length bottom or restores default"
- "0xece2 ESC &l#E sets top margin, default text length, and pending cursor"
- "0xcb00/0xc992/0xece2/0xea9e chained ESC &l stream selects vertical layout
  handlers"
- "vertical layout parser trace feeds page-record queue"
- "mixed page-length stream refreshes cursor before printable page-record
  queue"
- "0xee64 ESC &l#L toggles perforation skip for selectors 0 and 1 only"
- "perforation skip parser trace feeds page-record queue"
- "0xf36c perforation skip gates vertical overflow page eject"
- "0xedb0 ESC &s#C toggles end-of-line wrap for selectors 0 and 1 only"
- "0xd28a and 0xd6bc prechecks share continue reject and wrap decisions"

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
  `0x782128`, active render pointer `0x783a18`, and the same ROM-local
  render-entry path as a direct `0x1ed84` / `0x1ef6a` setup.
- Fixture `0x1ecd6 same-geometry render work reuse reaches render entry`
  proves the same-geometry branch computes destination word `+8`, derives
  `0x783a20 = 0x0020`, `0x783a22 = 3`, and
  `0x783a28 = 0x00103800`, and still reaches the documented render-entry
  path.
- Fixture `0x1eba4/0x1ef6a active render loop advances or yields bands` pins
  the render, capacity-wait, cleanup, and throttle outcomes from active and
  paired work-record fields.
- Fixture `0x1eba4 scheduler band words render published downloaded glyph`
  proves ten scheduler-produced band words `0..9` feed a published
  downloaded-glyph page record into `0x1ef6a`; only buckets `1` and `9`
  dispatch compact objects, and bucket `9` reaches the ROM-derived row-write
  path for page row `86`.

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

Render-root to pixel-writer matrix:

- Render root `+0x18`, compact bucket objects:
  `0x1efc2` selects the active bucket from render work word `+0x10` and
  dispatches class byte `+0x04 & 0xc0 == 0` to `0x1effe`. Subdispatch bits
  `0x10` and `0x20` select short compact `0x1f034`, wide compact `0x1f0d2`,
  segmented compact `0x1f1f0`, or segmented-wide compact `0x1f264`. These
  writers resolve glyph/resource bitmap state through `0x1f354` and store
  generated row bytes or words into the active band or fallback buffer.
- Render root `+0x18`, segment-list bucket objects:
  `0x1efc2` dispatches class byte `+0x04 & 0xc0 == 0x40` to
  `0x1f812 -> 0x1f862`. The renderer consumes six-byte span entries and
  writes full-mask words plus trailing masks for pending text spans.
- Render root `+0x18`, encoded-raster bucket objects:
  `0x1efc2` dispatches class byte `+0x04 & 0x80 != 0` to `0x1f88e`.
  Object byte `+0x05 & 3` selects literal mode `0`, byte-expansion mode `1`,
  byte-pair expansion mode `2`, or cascaded expansion mode `3`; each mode
  expands payload bytes `+0x0a..` into generated destination words.
- Render root `+0x1c`, rule-list objects:
  `0x1f446` consumes bridged rule nodes. Selector `object[5] & 0x0f == 7`
  reaches solid writer `0x1f596`; selectors `0..6` and `8..13` reach
  patterned writer `0x1f4e0` through table `0x1f4a0`. Rule continuation
  field `+0x0c` is firmware state consumed across later bands.
- Render root `+0x20`, fixed-list objects:
  `0x1f756` runs on five-band boundaries, consumes fixed-list fields
  `+0x04..+0x0d`, selects pattern longwords from table `0x308de`, and writes
  through `0x1f7b0` / `0x1f626`.

This matrix is the final ROM-local pixel-production boundary. The inputs are
render-record roots and object fields already copied by `0x1edc6`; parser
records, command handlers, and payload cursors are no longer consulted here.
The outputs are direct stores to the active band or fallback buffer in ROM
call order. Physical transfer of those buffer bytes to the engine remains a
formatter/DC timing boundary, not a parser or renderer-dispatch gap.

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
- The shared pixel operation is a direct destination store in render order,
  not an implicit logical blend against existing destination contents. Compact
  row-copy helpers, encoded-raster modes, segment-list spans, solid rules, and
  fixed-list helpers write generated words, bytes, or longwords to the active
  band or fallback buffer. Patterned-rule helper `0x1f4e0` masks the generated
  pattern word before storing it; the documented helpers do not read the
  destination word and OR/XOR/AND it with earlier pixels.

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
  continuation rows through the fallback buffer rooted at `0x7810b4` plus
  the horizontal byte-pair offset decoded from the packed coordinate. In the
  compact path `0x1f3d4` leaves that offset in `D2`; in the `0x1f626` path
  the helper leaves it in `A2`. The scheduler then calls `0x1ef6a` again
  with later band words.

Reproduction rule:

- Start each render pass from the active render work record at `0x783a18`.
  The parser and page-object producers are no longer consulted at this layer.
- Run the fixed dispatch order for a band: `0x1ef86` derives destination
  state, `0x1efc2` renders bucket-chain objects, `0x1f446` renders rule-list
  objects, and `0x1f756` renders fixed-list objects. Later classes can
  overwrite earlier destination words because the helpers store generated
  words directly.
- Use `0x783a28` and offset table `0x7839f8..` for active-band destinations,
  with stride `0x783a1c`. Use fallback base
  `0x7810b4 + byte_pair_offset` only when destination helpers such as
  `0x1f414` report rows beyond the current band.
- Do not implement an implicit compositing mode. The documented helper set
  writes bytes, words, or longwords in ROM call order. Pattern helpers mask
  their generated pattern before storing it, but they do not read the
  destination word and blend against already-rendered pixels.

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
  caches `0x783a40..0x783a48`, and fallback base
  `0x7810b4 + byte_pair_offset`.
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
  or rendered rows.

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

## Worked Path: Downloaded Glyph Rule/Raster Composition

This path composes a downloaded glyph install with following page-imaging
commands in one host byte stream. It documents the state handoff at byte `24`
between the `ESC )s18W` font payload and the following page stream:

```text
ESC )s18W <18 bitmap bytes>
ESC *c12a3b0P ) ESC *t300R ESC *r0A ESC *b2W c3 3c
```

The full stream is a single `0xa904` ring-source stream, not two independent
host sources. The font phase is bytes `0..24`; the page phase is bytes
`24..54`.

Parser and command flow:

- `ESC )s18W` reaches `0x11f96` through parser-family handlers `0x11eb6`,
  `0x12008`, and `0x11ff6`.
- `0x11f96` schedules delayed handler `0x16c14` through `0x121cc`; restore
  path `0x12218` reinstalls record `80 57 00 12 00 00`.
- `0x16c14 -> 0x16498` installs downloaded glyph `0x29` at table entry
  `0x00ee`, record delta `0x0780`, record bytes
  `00 00 00 00 0c 01 00 01 00 90 00 00`, bitmap offset `0x078c`, bitmap size
  `18`, and bitmap bytes
  `f0 0f aa 55 3c c3 81 7e ff 00 18 e7 24 db 42 bd 66 99`.
- The install helper drains to byte `24` with no pending handler. Fixture
  `downloaded glyph byte-24 state handoff feeds following page handler`
  records that the final font-command header is the page memory image consumed
  by the following handler.
- Page bytes `24..54` route through rectangle handlers `0x10e68`,
  `0x10e22`, and `0x10898`; printable handler `0xd04a`; raster setup
  handlers `0x10808` and `0x1075a`; delayed raster wrapper `0x11f82`; and
  raster payload consumer `0x105d0`.

Canonical page state:

- The downloaded glyph object is queued through `0xd04a -> 0x1393a ->
  0x12f2e` as bucket-5 object
  `00 00 00 00 10 03 00 01 29 06 01...`.
- The selector-7 rectangle is queued through `0x10898 -> 0x10b80 ->
  0x13386 -> 0x133aa`; after bridge normalization it is
  `00 00 00 00 05 17 08 01 00 0c 00 03 00 03`.
- The mode-0 raster object is queued through `0x105d0 -> 0x13070 ->
  0x13250` as
  `00 00 00 00 80 00 00 02 00 00 c3 3c`.
- Publication sibling fixture `parser-driven downloaded glyph rule raster FF
  publishes page record` appends FF, publishes bucket `5`, preserves the raw
  selector-7 rule list, clears current root `0x78297a`, and sets publication
  flag `0x782996`.

State classification:

- Canonical state: downloaded glyph table entry `0x00ee`, installed record
  delta `0x0780`, bitmap offset `0x078c`, bitmap bytes, current page root,
  bucket-5 glyph/raster chain, selector-7 rule object, and published page
  record.
- Derived/cache state: final font-command header used as the page memory
  image, bridge-normalized rule selector bit `0x10`, render bucket word `5`,
  and render-band setup from `0x1ef86`.
- Parser scratch: font bytes `0..24`, page bytes `24..54`, restored
  downloaded-font record `80 57 00 12 00 00`, raster record
  `80 57 00 02 00 00`, raster snapshot
  `01 00 01 05 d0 80 57 00 02 00 00`, and raster payload `c3 3c`.
- Firmware bookkeeping: downloaded-record allocation state around
  `0x16c14` / `0x16498`, stream allocator state, publication flag
  `0x782996`, root clear count, and render-work progress.
- Hardware/external state: none for this ROM-local byte-to-bitmap path.

Output effect:

- Render entry `0x1ed84` copies the active or published page record into a
  render work record; `0x1edc6` copies bucket roots, rule roots, and context
  slots.
- `0x1ef6a` calls `0x1ef86`, bucket dispatch `0x1efc2`, rule dispatch
  `0x1f446`, and fixed-list dispatch `0x1f756`.
- The raster object dispatches to `0x1f88e`, the downloaded glyph dispatches
  through `0x1effe -> 0x1f0d2`, and the rule dispatches through `0x1f596`.
- The derived rows are row `0` with raster payload `c3 3c`, downloaded glyph
  at x `22`, and rule from x `24` through x `35`, followed by rows `1` and
  `2` containing the rule only.

Evidence and unresolved boundary:

- Detail checkpoint: `Downloaded Glyph Rule/Raster Composition` in
  [semantic-state-model.md](semantic-state-model.md).
- Detail note: [downloaded-fonts.md](downloaded-fonts.md).
- Fixture evidence:
  `parser-driven downloaded glyph rule raster stream composes through
  0x1ef6a`, `downloaded glyph byte-24 state handoff feeds following page
  handler`, `even-span downloaded glyph rule raster FF publication renders
  page record`, and
  `parser-driven downloaded glyph rule raster FF publishes page record`.
- Disassembly evidence:
  `generated/disasm/ic30_ic13_font_payload_object_path_016040.lst`,
  `generated/disasm/ic30_ic13_font_payload_readers_016874.lst`,
  `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`,
  `generated/disasm/ic30_ic13_rectangle_graphics_010898.lst`,
  `generated/disasm/ic30_ic13_raster_handlers_0105d0.lst`,
  `generated/disasm/ic30_ic13_raster_object_queue_013070.lst`,
  `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`, and
  `generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`.
- No unresolved middle edge remains for the documented byte-24 handoff,
  glyph/rule/raster page-object fields, publication, bridge roots, or render
  dispatch. Further work must change the final header, installed record,
  post-install drain, following parser handler, page-object bytes, bucket
  assignment, dispatch target, or derived rows.

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

VFC command-to-output matrix:

- `ESC &l#W` table definition:
  delayed path `0x11f6e -> 0x121cc -> 0x12218 -> 0x12cfe`. It writes VFC
  table `0x782dde..0x782edd`, derived bottom `0x782dc2`, text-bottom cache
  `0x782dd2`, and modified-layout flag `0x782ee1`. It consumes payload bytes
  but queues no page object; visible output changes only when later cursor,
  wrap, printable, or page-boundary paths consume the new table/cache state.
- Default table/layout refresh:
  `0xe5e2 -> 0x12b96` rebuilds top offset, margins, text-bottom cache,
  line-count caches, and default VFC channel bits. It is shared layout state,
  not a direct page-object producer, and later `0x1280a`, printable placement,
  and overflow logic consume it.
- `ESC &l#V` cursor-only jump:
  `0x1280a` finds a target that does not require page publication, resets x
  through `0xf06e`, flushes pending text through `0xf34a`, writes cursor y,
  and leaves the following printable on the current root `0x78297a`.
- `ESC &l#V` page-boundary jump:
  `0x1280a` takes a selector-zero, wrap, or recovery path that calls
  `0xf124 -> 0xff1e`. The old page root is published before the following
  printable byte allocates or reuses a fresh current root.
- `ESC &l#V` recovery without publication:
  `0x1280a` writes the same recovered cursor state as a publishing sibling
  but skips `0xf124`. The following printable stays on the current page, so
  reproduction must not synthesize a page break merely because recovery logic
  ran.

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

## Worked Path: VFC Table And Channel Branch Matrix

This path composes the VFC state block and `0x1280a` branch matrix beyond the
basic table-load and forward jump examples. It documents the variants that
change cursor placement, page publication, and the page object consumed by the
next printable byte. The detail contract is in
[vertical-forms-control.md](vertical-forms-control.md); the semantic checkpoint
is `Vertical Forms Control` in
[semantic-state-model.md](semantic-state-model.md).

Canonical table and layout writers:

- `0x12cfe` is the delayed `ESC &l#W` payload handler. It reads the restored
  byte count, consumes payload through `0xdace`, writes channel words
  `0x782dde..0x782edd`, derives VFC bottom `0x782dc2`, copies text-bottom
  cache `0x782dd2`, and clears modified-layout flag `0x782ee1`.
  The handler only installs even byte counts that fit the current VFC table
  window; odd counts or counts beyond `2 * (0x782ede + 1)` are drained without
  table writes. Accepted payloads write at most `0x100` bytes, with any excess
  drained through `0xdace`.
- `0x12b96` builds the default 128-word VFC table from cached line bounds.
  The default-table fixture pins the one-based channel convention: selector
  `n` maps to bit `1 << (n - 1)`.
- Shared layout refresh `0xe5e2` recomputes top offset `0x782dce`, left/right
  margins `0x782dd6` / `0x782dda`, vertical cursor `0x782c8e`, text-bottom
  cache `0x782dd2`, line caches `0x782ede..0x782ee0`, and then calls
  `0x12b96`.
- `0xfe54` writes the line-count caches `0x782edf`, `0x782ee0`, and
  `0x782ede`.

Consumer fields at `0x1280a`:

- Canonical VFC table:
  `0x782dde..0x782edd`.
- Canonical cursor/layout inputs:
  VMI `0x783160`, top offset `0x782dce`, vertical cursor `0x782c8e`,
  horizontal cursor `0x782c8a`, and left margin `0x782dd6`.
- Derived/cache line bounds:
  text-bottom cache `0x782dd2`, VFC limit `0x782dc2`, last-text/index fields
  `0x782ede`, `0x782edf`, and `0x782ee0`.
- Firmware bookkeeping:
  pending cursor/text latches `0x782a58` and `0x782a6d`, pending span flag
  `0x783184`, modified-layout flag `0x782ee1`, current root `0x78297a`, and
  publication flag `0x782996`.

Branch matrix:

- `0x128ae..0x128f4`: before-top normalization. It rewrites the computed start
  line before the ordinary forward scan and does not publish by itself.
- `0x1292a..0x1295c -> 0x12aa6..0x12af8`: forward in-text hit. It resets x
  through `0xf06e`, flushes pending text through `0xf34a`, writes target y,
  and keeps the next printable on the current page.
- `0x12966..0x1299a`: selector-zero target-equal exit. It computes
  top-of-form and leaves x/y unchanged when the cursor is already there.
- `0x1299c..0x129c4`: selector-zero page eject. It runs
  `0xf06e -> 0xf34a -> 0xf34a -> 0xf124`, publishes the old page, and leaves
  the next printable on a fresh page.
- `0x129c6..0x12af8`: wrap hit. It wraps to line `0`, finds a hit before the
  original start line, publishes through `0xf124`, and then commits target y.
- `0x129ee..0x12b5a`: publishing target-after-text recovery. It finds a
  channel after `0x782ee0`, publishes the old page, then recovers y through
  `0x12afc..0x12b5a`.
- `0x129fc..0x12afc`: non-publishing target-after-text recovery. It is the
  before-top sibling where start line `0` skips the `0xf124` edge and only
  recovers x/y.
- `0x12a02..0x12afc`: start-after-text no-wrap recovery. With no matching
  channel bit, it skips publication and writes the recovered y.
- `0x12a22..0x12a78`: wrap-no-hit page eject. With no matching bit through
  the forward and wrapped scans, it publishes the old page and returns to
  top-of-form y.
- `0x12a7a..0x12af8`: start-after-text wrapped in-text hit. It wraps from a
  start line past text bottom to an in-text channel and commits without
  publication.
- `0x12a7a..0x12afc`: start-after-text wrapped bottom recovery. It wraps to a
  line after `0x782ee0`, skips publication, and writes recovered y.
- `0x1299c..0x12b92`: selector-zero start-after-text recovery. It skips the
  page-eject edge when the computed start line is already past text bottom and
  writes top-of-form y.

Output effects:

- `ESC &l4W 00 00 00 02 !` proves table payload bytes are consumed before the
  following printable byte, leaving the `!` queued at compact coordinate
  `0x9001`.
- Lowercase `ESC &l4w4W` proves the earlier lowercase delayed record
  `80 77 00 04 00 00` survives until uppercase `W` terminates the family.
- Forward and before-top selector-2 jumps queue the following printable at
  compact coordinate `0xb001` after y is written to `176`.
- Selector-zero target-equal `ESC &l0V!` leaves a matching top-of-form cursor
  unchanged and queues `!` at compact coordinate `0x9e02`.
- Selector-zero page eject `! ESC &l0V !`, wrap-hit `! ESC &l2V !`,
  wrap-no-hit, and publishing target-after-text paths publish the old page
  through `0xf124 -> 0xff1e` before the following printable byte is queued on
  a fresh page.
- Non-publishing recovery siblings write the same cursor state without calling
  `0xf124`, so the following printable remains on the current page.

State classification:

- Canonical state:
  VFC table `0x782dde..0x782edd`, VMI `0x783160`, top offset `0x782dce`,
  cursor fields `0x782c8a` / `0x782c8e`, margins, current page root, published
  source record, and render-record bucket/context roots.
- Derived/cache state:
  line-count caches `0x782ede`, `0x782edf`, `0x782ee0`, VFC limit
  `0x782dc2`, text-bottom cache `0x782dd2`, selector masks, recovered y
  values, and compact coordinates.
- Parser scratch:
  delayed record state `0x782a1a`, `0x782a1c`, `0x782a20..0x782a25`, command
  cursor `0x78299e`, `ESC &l#V` selector, and direct payload bytes.
- Firmware bookkeeping:
  modified-layout flag `0x782ee1`, pending latches `0x782a58` and
  `0x782a6d`, pending span flag `0x783184`, publication flag `0x782996`,
  scheduler cursors, and render-work progress.
- Hardware/external state:
  none for the ROM-local VFC table and channel-jump contract.
- Unknown:
  no unresolved ROM-local middle edge remains for the documented table-load,
  default-table, forward jump, selector-zero, wrap-hit, wrap-no-hit,
  target-after-text, start-after-text, and alternate high-start paths.
  Manual-facing names for `0x782ede`, `0x782edf`, and `0x782ee0` remain
  inferred.

Evidence:

- Detail note: [vertical-forms-control.md](vertical-forms-control.md).
- Semantic checkpoint: `Vertical Forms Control` in
  [semantic-state-model.md](semantic-state-model.md).
- Fixtures:
  `0x12cfe ESC &l#W loads vertical forms control state`,
  `mixed VFC definition stream consumes payload before printable page-record
  queue`,
  `mixed VFC lowercase delayed record survives until uppercase W`,
  `mixed VFC channel jump stream moves cursor before printable page-record
  queue`,
  `mixed VFC before-top channel jump normalizes start line before printable`,
  `mixed VFC selector-zero page-eject publishes old page before fresh
  printable`,
  `mixed VFC wrap-hit publishes old page before fresh printable`,
  `mixed VFC wrap-no-hit publishes old page and returns to top`,
  `mixed VFC target-after-text recovers near top before fresh printable`,
  `0x1280a VFC alternate high-start recovery entries`, and
  `0x12b96 default VFC table channel convention`.
- Disassembly:
  `generated/disasm/ic30_ic13_vertical_forms_control_01280a.lst`,
  `generated/disasm/ic30_ic13_control_code_handlers_00f02c.lst`,
  `generated/disasm/ic30_ic13_hmi_vmi_handlers_00ca8c.lst`,
  `generated/disasm/ic30_ic13_macro_record_chain_helpers_00dfba.lst`,
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

Macro selector dataflow matrix:

- Selector `0` starts definition mode through `0xdd86`. Later payload bytes
  are stored by `0xe002` into macro-record chunks instead of running normal
  text, control, or page-object handlers.
- Selector `1` stops definition through `0xddfc`. It normalizes the raw
  chunk count in record `+0x04`, clears empty or auto-prefix-only records,
  and leaves nonempty records selectable for replay.
- Selector `2` executes the selected record through `0xde7c -> 0xe418`.
  The replay frame has kind byte `+9 = 2`; `0xa904` later feeds the stored
  payload bytes back to `0x11774` as parser input.
- Selector `3` calls the selected record through `0xdea2 -> 0xe418`.
  The replay frame has kind byte `+9 = 3` and pushes a macro context entry
  before the same `0xa904` data-chain byte-source replay.
- Selector `4` enables overlay through `0xdec8`: it stores overlay state
  `0x782a92`, copies the selected id into `0x782a94`, and leaves actual
  replay to the later `0xff1e -> 0xe4f4` publication path.
- Selector `5` disables overlay through `0xdef4`; selectors `6`, `7`, and
  `8` delete all, temporary, or selected records; selectors `9` and `10`
  mark the selected record temporary or permanent. These record-management
  selectors affect future replay eligibility but do not directly create page
  objects or pixels.

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
  byte streams that change replay-frame fields, skip-gate state,
  parser/delayed-payload dispatch, page-object fields, bridge roots,
  continuation fields, or ROM-derived row construction. External/manual names
  for macro context bytes remain separate.

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

## Worked Path: Macro Overlay Replay Publication

This path covers macro selector `4` overlay state as a page-publication input.
Unlike normal execute/call replay, overlay replay is not triggered by a live
`ESC &f2X` or `ESC &f3X` byte. It is consumed by page finalization before the
base page is published, and its stored bytes re-enter the normal parser so they
can add text, controls, spans, rules, or raster objects to the page root.

Overlay setup and publication entry:

- `ESC &f#Y` selects macro id `0x783164` through handler `0xe112`.
- `ESC &f4X` reaches macro control handler `0xdd08`, resolves the current
  record through `0xe0a4`, and enables overlay/page-parser state byte
  `0x782a92`. It copies the selected macro id into `0x782a94`.
- `ESC &f5X` disables the same overlay state through `0xdef4`.
- Page finalization reaches the overlay branch at `0xff1e` / `0xff8e`.
  When overlay state is enabled and page-root flag bit `+0x14.0` is clear,
  `0xe0a4(0x782a94)` reselects the saved macro record and `0xe4f4` builds a
  non-replay data-chain frame.
- If overlay is disabled, the selected record is missing, or the page-root
  retry flag is set, fixture `macro overlay skip gates preserve base page
  publication` proves the base page still publishes without replaying overlay
  bytes.

Non-replay frame and byte-source handoff:

- `0xe4f4` snapshots the active page/parser environment, pushes selected
  context fields, refreshes layout through `0xe5e2`, and writes a frame at
  `0x782d4c`.
- The frame copies macro record `+0x00/+0x04` to frame `+0x00/+0x04`, writes
  byte `+8 = 4`, writes frame kind `+9 = 4`, and writes snapshot pointer
  `+0x0a = 0`.
- If the frame byte count is positive, `0xe4f4` sets host gate bit 1 in
  `0x780e66`.
- `0xa904` then treats this frame as the highest-priority data-chain source,
  ahead of live host input. The stored overlay bytes are parsed by the same
  `0xda9a`, `0xdaf0`, `0xdb74`, and `0x11774` paths as ordinary host bytes.
- Frame cleanup through `0xe22c` restores the saved page/parser state after
  overlay replay completes.

Covered payload families:

- Mixed controls:
  stored `ESC &k1G!\r!` replays wrap-mode handler `0xedf8`, printable
  `0xd04a`, CR `0xf02c`, and another printable `0xd04a`, then publishes two
  compact text entries with the base selector-7 rule.
- Cursor positioning:
  stored `ESC &a2C!` replays `0xf39e` then `0xd04a`, queues compact text at
  coord `0x0a02`, and preserves the base rule object.
- Vertical decipoints:
  stored `ESC &a72V!` replays `0xf60a` then `0xd04a`, moves packed vertical
  cursor `20 -> 30`, queues compact text at coord `0x9001`, and preserves the
  base rule object.
- Chained cursor and margin commands:
  stored `ESC &a2c+1R!` replays `0xf39e`, `0xf560`, and `0xd04a`;
  stored `ESC &a6l9M!` replays `0xeb58`, `0xec0c`, and `0xd04a`.
  The margin replay writes packed left/right margins `108` and `180` before
  following text is queued.
- Transparent data:
  stored `ESC &p2X!!` replays handler `0x11f5a`, delayed restore `0x12218`,
  and payload handler `0x12452`; payload bytes `21 21` route through
  `0xd04a` and become compact text.
- Raster data:
  stored `! ESC *t300R ESC *r0A ESC *b2W c3 3c` queues compact text plus one
  mode-0 encoded raster object. The multi-row sibling stores two delayed
  raster transfers, queues two raster objects, and advances raster `row_y`
  to `2`.
- Span flush:
  stored `ESC &a6L!` replays `0xeb58` and `0xd04a`, then materializes a
  selector-`0x4000` segment-list span object through `0xf34a` / `0x12714`.

State classification:

- Canonical macro state:
  macro record pool `0x782a98`, current record pointer `0x782d7a`, saved
  overlay macro id `0x782a94`, overlay state byte `0x782a92`, macro record
  payload chunks, and non-replay frame fields at `0x782d4c`.
- Canonical page state:
  current page root `0x78297a`, compact/raster bucket roots, rule list,
  fixed/span list, publication record, and render-record roots copied through
  `0x1ed84` / `0x1edc6`.
- Derived/cache state:
  replay-derived text coordinates such as `0x0a02`, `0x9001`, `0x3a02`,
  and `0x0207`; rule decoder suffixes; render-band fields; raster `row_y`
  after replayed transfers.
- Parser scratch:
  stored overlay payload bytes, replayed command records, delayed transparent
  record `80 58 00 02 00 00`, delayed raster transfer records, and local
  parser-mode state while the non-replay frame is active.
- Firmware bookkeeping:
  frame kind `+9 = 4`, frame stride byte `+8 = 4`, host gate bit 1 in
  `0x780e66`, page-root retry flag `+0x14.0`, environment snapshots, and
  frame cleanup through `0xe22c`.
- Hardware/external state:
  none for the ROM-local overlay replay and publication behavior.
- Unknown:
  no unresolved ROM-local middle edge remains for the documented overlay
  payload families. Remaining macro work must change replay-frame fields,
  skip-gate state, parser/delayed-payload dispatch, page-object fields, bridge
  roots, continuation fields, or ROM-derived row construction.

Output effect:

- Overlay replay is a parser/page-object producer, not a renderer. The pixels
  come from the same downstream compact text, span, rule, and raster renderers
  used by live host bytes.
- Fixtures `macro overlay finalization replays before page publication` and
  `macro overlay replays across repeated page publications` prove the replay
  happens before the current page is published and can recur on later page
  publications.
- The mixed-control, cursor, margin, transparent, raster, multi-row raster,
  and span-flush overlay fixtures prove stored overlay bytes can mutate
  parser/environment state, queue page objects, preserve base page rule
  objects, publish through `0xff1e`, bridge through `0x1ed84` / `0x1edc6`,
  and render through `0x1ef6a`.

Evidence:

- Detail note: [macro-data-chain.md](macro-data-chain.md).
- Semantic checkpoint: `Macro Definition And Data-Chain Replay` in
  [semantic-state-model.md](semantic-state-model.md).
- Fixtures:
  `macro overlay finalization replays before page publication`,
  `macro overlay replays across repeated page publications`,
  `macro overlay skip gates preserve base page publication`,
  `macro overlay mixed-control payload publishes with page rule`,
  `macro overlay cursor-position payload publishes with page rule`,
  `macro overlay vertical-decipoint payload publishes with page rule`,
  `macro overlay chained cursor-position payload publishes with page rule`,
  `macro overlay chained margin payload publishes with page rule`,
  `macro overlay transparent payload publishes with page rule`,
  `macro overlay raster payload publishes with page rule`,
  `macro overlay multi-row raster payload publishes with page rule`, and
  `macro overlay span-flush payload publishes with page rule`.
- Disassembly:
  `generated/disasm/ic30_ic13_macro_record_chain_helpers_00dfba.lst`,
  `generated/disasm/ic30_ic13_macro_environment_snapshot_helpers_00e65c.lst`,
  `generated/disasm/ic30_ic13_pcl_escape_parser_00da9a.lst`,
  `generated/disasm/ic30_ic13_main_parser_loop_011774.lst`,
  `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`, and
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

## Worked Path: Rectangle Rule Selectors And Clipping

This path composes the rectangle/rule command-family variants beyond the
primary selector-7 black rule. It covers size writers, fill-selector mapping,
clipping and reject gates, ordered rule-list storage, no-room retry,
bridge-normalized rule objects, and solid/pattern renderers. The detailed
contract is in [rectangle-graphics.md](rectangle-graphics.md); the semantic
checkpoint is `Rectangle Rule Producer And Renderer` in
[semantic-state-model.md](semantic-state-model.md).

Command-family writers:

- `0x10e68` handles `ESC *c#A` and writes dot width `0x78316a`.
- `0x10e22` handles `ESC *c#B` and writes dot height `0x783166`.
- `0x10a40` handles `ESC *c#H`; `0x10ae0` handles `ESC *c#V`.
  These decipoint handlers multiply by five 300-dpi subunits, round
  fractional subunits up, add the firmware `+11` subunit bias, and write the
  same width/height fields.
- `0x10dce` handles `ESC *c#G` and writes area-fill id `0x78316e`.
- `0x10898` handles `ESC *c#P`, maps the active fill selector, validates the
  stored width/height, and calls the rectangle source producer when a queued
  rule should be created.

Rectangle command-to-output matrix:

- `ESC *c#A` and `ESC *c#B` dot dimensions:
  handlers `0x10e68` and `0x10e22` write pending width `0x78316a` and height
  `0x783166`. They queue no object by themselves; `ESC *c#P` later consumes
  those fields.
- `ESC *c#H` and `ESC *c#V` decipoint dimensions:
  handlers `0x10a40` and `0x10ae0` convert decipoints through five 300-dpi
  subunits plus the firmware rounding/bias rule, then write the same
  width/height fields consumed by `0x10898`.
- `ESC *c#G` area-fill id:
  handler `0x10dce` writes `0x78316e`. It affects output only when a later
  `2P` or `3P` fill command maps that id to a gray or pattern selector.
- `ESC *c#P` fill rectangle:
  handler `0x10898` maps the stored fill state to a selector, rejects zero
  width/height or invalid selector combinations, and calls `0x10b80` for
  accepted rectangles. `0x10b80` clips against cursor, page extent, and
  orientation state, then writes source record `0x782a88`.
- Rule object production:
  `0x13386 -> 0x133aa` consumes source record `0x782a88`, derives
  bucket/key fields, allocates a 14-byte rule object, and inserts it under
  current page-root list `+0x24`.
- Publication and render:
  `0xff1e -> 0x1ed84 -> 0x1edc6` copies the rule list to render-record
  `+0x1c`; `0x1edc6` ORs selector byte `+5` with `0x10` and initializes
  continuation word `+0x0c`. `0x1ef6a -> 0x1f446` dispatches selector `7`
  to `0x1f596` and non-solid selectors to `0x1f4e0`.
- No-room retry:
  if `0x13386` returns zero, `0x10d22..0x10d3e` marks page-root retry bit
  `+0x15.0`, publishes the current root, ensures a fresh root, and retries
  the same source record. The command output is therefore split across the
  old published page and the retried fresh page root.

Fill selector mapping:

- Missing or `0P` maps to selector `7` for solid black.
- `2P` maps area-fill percentages in `0x78316e` to gray selectors `0..7`.
  Fixture streams cover fill ids `2`, `10`, `20`, `35`, `50`, `80`, and
  `99`.
- `3P` maps pattern ids `1..6` to selectors `8..13` in portrait.
- In landscape, pattern ids `1..4` remap to `1 -> 9`, `2 -> 8`,
  `3 -> 11`, and `4 -> 10`.
- Invalid mode/id combinations return without queueing. Zero width or height
  records the selector but does not create a rule object.

Clipping and rule-source production:

- `0x10b80` consumes cursor fields `0x782c8a` and `0x782c8e`, orientation
  `0x782da3`, page extents `0x782db8` and `0x782db6`, stored width/height,
  and the mapped selector.
- It writes source record `0x782a88`: x `+0`, y `+2`, width `+4`, height
  `+6`, and selector `+8`.
- Portrait clipping rejects rectangles wholly outside the page, clips negative
  left/top edges to zero, and clips right/bottom edges to the page extent.
- Landscape uses the same reject/clip gates, then swaps axes so portrait
  height becomes rule width and portrait width becomes rule height.
- The negative-left fixture starts at x `-3`, width `10`, and queues x `0`,
  width `7`. The clipping matrix also covers right-edge, top-edge,
  bottom-edge, landscape-right-edge, horizontal-outside, vertical-outside, and
  empty-after-clip outcomes.

Rule-list storage and no-room retry:

- `0x13386` calls `0x134d6`, which derives bucket index `0x782a7c` and packed
  key `0x782a7e` from source x/y plus horizontal phase `0x782dc0`.
- `0x133aa` allocates a 14-byte rule object through `0x1381c` and inserts it
  under page-root list `+0x24` in ascending object byte `+4` order. Equal
  bucket bytes insert after the existing equal node.
- Rule object fields are next pointer `+0`, bucket byte `+4`, fill selector
  `+5`, packed key `+6`, width `+8`, height `+0a`, and continuation height
  `+0c`.
- If `0x13386` returns zero, retry path `0x10d22..0x10d3e` sets page-root
  retry flag `+0x15.0`, publishes the current root through `0xff1e`, ensures a
  fresh root through `0x10084`, and retries the same source record through
  `0x13386`.

Bridge and render consumers:

- `0x1edc6` copies source root `+0x24` to render-record `+0x1c`, ORs object
  byte `+5` with `0x10`, and copies height `+0x0a` into continuation word
  `+0x0c`.
- `0x1ef6a` calls `0x1f446` after bucket-chain dispatch `0x1efc2` and before
  fixed-list dispatch `0x1f756`.
- `0x1f446` walks bridged rule-list nodes for each band. Selector `7`
  dispatches to solid helper `0x1f596`; selectors `0..6` and `8..13`
  dispatch to pattern helper `0x1f4e0`.
- `0x1f596` and `0x1f4e0` consume packed key, width, selector, and
  continuation height. Crossing rules mutate continuation word `+0x0c` and
  resume on the next band.

State classification:

- Canonical state:
  rectangle width `0x78316a`, rectangle height `0x783166`, area-fill id
  `0x78316e`, source record `0x782a88`, rule objects under page-root `+0x24`,
  published rule list, and bridged render-record rule list `+0x1c`.
- Derived/cache state:
  bucket/key fields `0x782a7c`, `0x782a7d`, and `0x782a7e`; horizontal phase
  `0x782dc0`; bridged selector bit `0x10`; continuation word `+0x0c`; row
  digests and render-band fields.
- Parser scratch:
  six-byte command records consumed by `0x10e68`, `0x10e22`, `0x10a40`,
  `0x10ae0`, `0x10dce`, and `0x10898`; parser mode and command cursor
  `0x78299e`.
- Firmware bookkeeping:
  stream allocator cursors `0x782a70`, `0x782a72`, and `0x782a76`; retry flag
  `+0x15.0`; publication flag `0x782996`; scheduler cursors and render-work
  progress words.
- Hardware/external state:
  none for the ROM-local rectangle/rule command-family contract.
- Unknown:
  no unresolved software-visible middle edge remains for the covered
  selector-7, gray-selector, pattern-selector, landscape-remap, clipping,
  no-room retry, addressed-storage, publication, and mixed text/rule/raster
  streams. Remaining rectangle work is limited to byte streams that change
  clipping output, allocation rollover, retry publication fields, rule object
  bytes, bridge state, render dispatch, or rendered rows.

Output effect:

- Selector `7` renders through `0x1f596`; the solid crossing fixture starts at
  y `78`, draws two rows in the first band, carries three rows in `+0x0c`,
  and draws the remainder at y `0` in the next band.
- Non-solid selectors render through `0x1f4e0`. The selector matrix pins gray
  selectors `0..6`, pattern selectors `8..13`, sub-byte shifted HP pattern
  rows, and patterned continuation across bands.
- `host-fetched alternate rectangle selectors feed full page records` proves
  gray selector `4` and portrait pattern selector `9` with compact text,
  bridge normalization, `0x1f446` dispatch, and composed page-row digests.
- `host-fetched rectangle selector matrix feeds full page records` extends
  that page-visible path to every non-solid selector id and the landscape
  pattern remaps.
- The no-room retry fixture proves allocation failure publishes the existing
  compact text bucket, creates a fresh root, retries the preserved selector-7
  source record, bridges it, and renders the retried rule.

Evidence:

- Detail note: [rectangle-graphics.md](rectangle-graphics.md).
- Semantic checkpoint: `Rectangle Rule Producer And Renderer` in
  [semantic-state-model.md](semantic-state-model.md).
- Fixtures:
  `0x10e68/0x10e22/0x10a40/0x10ae0 rectangle size commands update packed
  dimensions`,
  `0x10898 ESC *c#P maps fill selectors and queues rule object`,
  `0x10b80 rectangle fill clips negative left edge before queueing`,
  `0x10b80 rectangle fill clips right/top/bottom edges and ignores off-page
  fills`,
  `0x13386/0x133aa-modeled rectangle/rule list object and bridge
  normalization`,
  `0x1f446/0x1f596 renders solid black rectangle rule pixels`,
  `0x1f4e0 renders gray and HP pattern selector matrix`,
  `0x1f4e0 carries patterned rule remainder across render bands`,
  `0x1f446 page-band walk assembles patterned rule rows`,
  `host-fetched alternate rectangle selectors feed full page records`,
  `host-fetched rectangle selector matrix feeds full page records`, and
  `rectangle parser trace feeds no-room retry path`.
- Disassembly:
  `generated/disasm/ic30_ic13_rectangle_graphics_010898.lst`,
  `generated/disasm/ic30_ic13_display_list_helpers_013386.lst`,
  `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`,
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`,
  `generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`, and
  `generated/analysis/ic30_ic13_rectangle_graphics_flow.md`.

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
  outcomes, dense-row splitting, bridge fields, or ROM-derived row
  construction.

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

## Worked Path: Raster Transfer Gates And Modes

This path composes the raster command-family variants that change parser
handoff, transfer acceptance, object bytes, or ROM-derived row construction. It
builds on the primary `Raster Row` stream above and promotes the broader
fixture-backed contract from [raster-graphics.md](raster-graphics.md) and
`Raster Transfer Gate And Encoded Rows` in
[semantic-state-model.md](semantic-state-model.md).

Parser and delayed-transfer contract:

- `ESC *t#R` reaches `0x10808`, which writes raster scale `+0x0e` and encoded
  mode `+0x08` only when active byte `+0x12` is clear.
- `ESC *r#A` reaches `0x1075a`, which writes origin/baseline, active byte,
  and byte limit. Parameter `1` seeds the origin from the active cursor axis;
  other parameters seed from the left edge.
- `ESC *r#B` reaches `0x107fa` and clears only active byte `+0x12`.
- `ESC *b#W` reaches `0x11f82`, which schedules delayed handler `0x105d0`
  through `0x121cc`; `0x12218` restores the saved six-byte record and calls
  `0x105d0` through `jsr (A2)`.
- Lowercase same-family `ESC *b#w` records stay pending inside the `*b`
  parser family. The fixture-backed stream `ESC *b2w2W` preserves delayed
  record `80 77 00 02 00 00` until the uppercase terminator consumes payload
  at offset `19`.

Canonical raster fields:

- Raster state block `0x783170`:
  `+0x00` baseline copy, `+0x02` row coordinate, `+0x04` accepted byte count,
  `+0x06` overflow count, `+0x08` encoded mode, `+0x0a` origin/baseline,
  `+0x0e` scale, `+0x10` maximum accepted row byte count, and `+0x12` active
  byte.
- Encoded page object:
  `+0x00` next pointer, `+0x04 = 0x80` class byte, `+0x05` mode byte,
  `+0x06` even-rounded capacity, `+0x08` packed coordinate/key, and payload
  bytes beginning at `+0x0a`.
- Current page root:
  `0x78297a` and root `+0x1c` bucket heads, shared with compact text and
  other bucket-chain producers.

Transfer gate behavior at `0x105d0`:

- Beyond-extent rows drain the parsed byte count through `0xdace` at
  `0x1065c..0x10698`, return before `0x10084`, queue no object, and do not
  advance the row.
- In-range rows whose byte count exceeds limit `+0x10` store accepted count
  in `+0x04`, store overflow in `+0x06`, queue only the accepted bytes, and
  drain the remainder later.
- Negative rows store the same accepted/overflow state, call `0x10084`, drain
  the transfer through `0xdace`, skip `0x13070`, and advance from row `-1` to
  row `0`.
- Rows that pass the gate call `0x13070` with the raster state pointer
  `A4 = 0x783170`; `0x13070` computes bucket/key fields and `0x13250`
  allocates encoded-span objects under root `+0x1c`.

Mode and row-object variants:

- `ESC *t150R` selects scale `2`, encoded mode `1`, and later renders through
  `0x1f88e -> 0x1f8e6`, expanding each payload byte through word table
  `0x30914` into two current/fallback row writes.
- `ESC *t100R` selects scale `3`, encoded mode `2`, and later renders through
  `0x1f88e -> 0x1f920`, running even-indexed and odd-indexed payload-byte
  passes through longword table `0x30b14` into three current/fallback row
  writes.
- `ESC *t75R` selects scale `4`, encoded mode `3`, and later renders through
  `0x1f88e -> 0x1f9c6`, expanding each byte through two levels of table
  `0x30914` into four current/fallback row writes.
- While active byte `+0x12` is set, a later `ESC *t75R` is ignored; after
  `ESC *rB`, a later `ESC *t150R` updates mode and scale again.
- Consecutive uppercase `ESC *b2W` transfers restore independent records,
  consume payloads at offsets `17` and `24`, queue objects at packed coords
  `0x0000` and `0x1000`, and advance modeled `row_y` to `2`.
- `0x138de` copies payload through `0xa904` and locally maps control pair
  `1a 58` to copied byte `00`.

Raster command-to-output matrix:

- `ESC *t#R` resolution:
  handler `0x10808` writes scale `+0x0e` and encoded mode `+0x08` in
  raster state block `0x783170` only while active byte `+0x12` is clear.
  Its output effect is deferred: the next accepted `ESC *b#W` transfer
  writes object mode byte `+0x05`, which selects an `0x1f88e` expansion
  helper during rendering.
- `ESC *r#A` start raster:
  handler `0x1075a` writes origin/baseline, active state, and byte limit
  `+0x10`. It queues no page object by itself; `0x105d0` consumes these
  fields when the next delayed row transfer arrives.
- `ESC *r#B` end raster:
  handler `0x107fa` clears only active byte `+0x12`. That permits later
  resolution commands to update mode/scale again, but does not itself delete
  queued raster objects or publish a page.
- `ESC *b#W` raster row transfer:
  handler `0x11f82` schedules delayed handler `0x105d0`; `0x105d0` consumes
  the restored byte count, drains skipped bytes, writes row/count state, and
  calls `0x13070` only for accepted rows. Accepted rows become encoded-span
  bucket objects under page-root `+0x1c`.
- Lowercase `ESC *b#w`:
  the parser keeps the same `*b` command family pending until an uppercase
  terminal arrives. The uppercase terminal supplies the restored handler and
  payload boundary that finally reaches `0x105d0`.
- Render effect:
  publication and bridge copy accepted raster objects through
  `0xff1e -> 0x1ed84 -> 0x1edc6`; `0x1ef6a -> 0x1efc2 -> 0x1f88e` consumes
  object mode `+0x05` and payload bytes. Gate failures that only drain bytes
  have no page-object or render effect.

Dense-row allocation and splitting:

- `0x132b6` can satisfy a request from remaining stream bytes
  `0x782a70`, use a current chunk tail when at least `12` bytes remain, or
  allocate a new `0x100`-byte chunk through `0x1710`.
- It records per-object payload capacity in `0x782a80`; `0x13070` writes that
  value to object `+0x06`, copies up to that many bytes through `0x138de`, and
  loops for remaining accepted bytes.
- Zero-length, no-room, and copy-stop exits drain the remaining accepted plus
  overflow count through `0x12328`.
- The instruction-level split rule is documented as
  `Dense-Row Split Composition Checkpoint` in
  [raster-graphics.md](raster-graphics.md#dense-row-split-composition-checkpoint):
  `0x132be..0x13320` is same-chunk allocation,
  `0x132ce..0x132fc` is current-tail allocation, and
  `0x13328..0x13382` is new-chunk or capped-new-chunk allocation. The static
  dense-row walkthrough there derives a fresh-chunk `0x012c` accepted transfer
  into `0x00f2` and `0x003a` encoded objects, with the later object inserted at
  the bucket head, and separately derives the current-tail branch when prior
  page objects leave at least `12` but not enough remaining chunk bytes.

State classification:

- Canonical state:
  raster block `0x783170`, encoded-span object bytes under page-root `+0x1c`,
  published bucket roots, render-record bucket roots, and rendered row data.
- Derived/cache state:
  bucket index `0x782a7c`, packed key `0x782a7e`, per-object capacity
  `0x782a80`, render-band fields `0x783a20`, `0x783a22`, and `0x783a28`,
  and mode-derived expansion helper choice.
- Parser scratch:
  delayed record snapshot `0x782a20..0x782a25`, pending flag `0x782a1a`,
  handler pointer `0x782a1c`, restored `80 57 ...` records, payload offsets,
  and drained payload bytes.
- Firmware bookkeeping:
  stream allocator cursors `0x782a70`, `0x782a72`, and `0x782a76`,
  copy-stop/publication flag `0x782996`, page-root retry bit `+0x15.0`,
  scheduler cursors, and render-work progress words.
- Hardware/external state:
  none for the ROM-local raster command-family contract.
- Unknown:
  no unresolved ROM-local parser, gate, object layout, bridge, mode dispatch,
  or dense-row branch target remains for the covered raster streams. Remaining
  raster work is byte-stream variants that expose different gate outcomes,
  accepted counts or drains, allocator state `0x782a70/0x782a72/0x782a76`,
  split capacity `0x782a80`, encoded object bytes
  `+0x04/+0x05/+0x06/+0x08/+0x0a..`, bridge bucket roots, copy-stop byte
  `0x782996`, packed-key advance through `0x332ee`, or mode-specific
  `0x1f88e` rows.

Output effect:

- Accepted raster transfers do not draw immediately. They queue encoded-span
  objects under page-root `+0x1c`; publication and render dispatch later copy
  those objects through `0x1ed84` / `0x1edc6` and render them through
  `0x1ef6a -> 0x1efc2 -> 0x1f88e`.
- The capped transfer fixture checks count `4` with limit `2` queues payload
  `f0 0f`, stores overflow `2`, and renders `####........####`.
- Beyond-extent and negative-row fixtures check that discarded payloads are still
  consumed, with the negative-row branch ensuring a root before draining.
- Mode fixtures check visible rows for modes `0..3`, including shifted mode-0
  and mode-2 rows and a mode-2 band-clipped current/fallback split.

Evidence:

- Detail note: [raster-graphics.md](raster-graphics.md).
- Semantic checkpoint: `Raster Transfer Gate And Encoded Rows` in
  [semantic-state-model.md](semantic-state-model.md).
- Fixtures:
  `0x10808 ESC *t#R selects raster mode and scale thresholds`,
  `0x1075a ESC *r#A seeds raster baseline from cursor or left edge`,
  `0x1075a raster origin source follows orientation`,
  `0x107fa ESC *r#B clears raster active flag only`,
  `0x105d0-modeled raster transfer skip and cap gate`,
  `raster mode streams tie ROM parser dispatch to modeled queued objects`,
  `host-fetched raster mode streams feed 0x1ed84 and 0x1ef6a`,
  `modeled raster command stream queues consecutive ESC *b#W rows`,
  `modeled raster command stream defers lowercase ESC *b w payload until
  uppercase terminator`,
  `raster payload reader normalizes 0xdace controls before queueing pixels`,
  and the `0x1f88e mode-0` through `mode-3` render fixtures listed in
  [raster-graphics.md](raster-graphics.md).
- Disassembly:
  `generated/disasm/ic30_ic13_raster_handlers_0105d0.lst`,
  `generated/disasm/ic30_ic13_raster_object_queue_013070.lst`,
  `generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst`,
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`, and
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
resource data, or optional physical correlation outside the ROM-derived model.

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
- Optional physical correlation: full internal-font sample and
  self-test/page-placement comparison against a real LaserJet II output would
  only correlate the ROM-derived model with a device. The ROM-local path is
  documented through sample traversal
  `0x1c334..0x1c5e4`, page-object production `0x1c5e8..0x1ed84`, bridge
  `0x1ed84` / `0x1edc6`, and render entry `0x1ef6a`; no external rendered-row
  oracle is required for parser, resource, page-record, or bitmap-renderer
  documentation.
- ROM-local visible-output helper boundary:
  `Boundary: Short Compact Downloaded-Glyph High Rows` documents the exact
  short compact downloaded-glyph fallback edge in helper `0x1fe76`. Rows
  `0x0101..0x0103` preserve installed row state and document low-byte selector
  truncation through `0x12f2e`, bucket `1` publication, render bucket word
  `1`, and `0x1f414` fallback counts `199..201`. The unresolved
  renderer-helper edge is the unchecked `0x1fe8a + 4 * D3` row-copy table
  read in `0x1fe76`; entry `128` is the last valid pointer and entries above
  it read executable code bytes beginning at `0x2008e` as pointer data.
- ROM-local visible-output helper boundary:
  `Boundary: Downloaded-Glyph Wrapped Width Low Bytes` documents the exact
  width-byte sibling. Installed width words for spans `0x0100..0x0111`,
  `0x017f`, `0x0180`, `0x01fe`, and `0x020d` are preserved, but the printable
  source exposes only the low width byte to `0x12f2e`. Low source bytes
  `0x00..0x10` choose compact mode-0 helper targets outside decoded row-copy
  helper heads, including in-firmware target `0x0066cc` at opcode `0x4a39`
  for span `0x0102`; high source bytes `0x11..0xff` render through
  compact-wide helper `0x1f0d2`.
  These two helper-boundary siblings are grouped in
  `Invalid Compact Helper Boundary Composition` in
  [page-raster-imaging.md](page-raster-imaging.md), with field classes,
  writers, readers, exact target addresses, and output contract.
- ROM-local visible-output source boundary:
  `Boundary: Segmented-Wide Downloaded-Glyph Fallback Source` documents the
  exact span-31 selected-segment source edge. Sampled high-row segmented-wide
  glyphs preserve installed rows, publish selector `0x3003`, dispatch bucket
  `8` segment `1` through `0x1f264`, and split into `32` current rows plus
  `96` fallback rows; the adjacent span-31 siblings through row `0x03ff` stop
  at fallback A2 source offset `+0xb50`.
- ROM-local parser/payload boundary:
  `Boundary: Downloaded-Glyph Payload Count Cap` documents oversized
  segmented-wide high-row streams that exceed the restored `ESC )s#W` count
  cap `0x7fff`. Adjacent below-cap row/span products reach `0x16498`,
  selector `0x3003`, and renderer `0x1f264`. Because segmented-wide spans
  start at `17`, `floor(0x7fff / 17) = 0x0787`; oversized products such as
  `0x0788*17` require `0x7ff8` bytes and stop at the recorded parser payload
  offset before installed glyph publication or render dispatch.
- ROM-local variant boundaries rather than generic gaps:
  raster byte streams that change the documented `0x132b6..0x13382`
  current-tail or capped-new-chunk object-chain derivation; dense page/object
  streams that change `0x1381c` rollover, `0x133aa` / `0x136d2` list ordering,
  or bridge fields; macro overlay payloads that change replay-frame fields,
  skip-gate state, parser/delayed-payload dispatch, page-object fields, bridge
  roots, continuation fields, or ROM-derived row construction; and selected
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
