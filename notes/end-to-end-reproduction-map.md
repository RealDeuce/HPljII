# End-To-End ROM Reproduction Map

Goal: reproduce LaserJet II output pixels from the same host byte stream by
using ROM-derived parser behavior, state fields, page-record formats, and
render routines. The primary explanatory spine is
[firmware-dataflow-model.md](firmware-dataflow-model.md). This note is the
current coverage/evidence map for that pipeline; detailed ledgers remain in
`notes/reverse-engineering-ledger.md` and `notes/semantic-state-model.md`.

## Pipeline Contract

```text
host bytes
  -> 0xa904 normalized byte fetch
  -> 0xda9a / 0xdaf0 / 0xdb74 parser and six-byte command records
  -> command handlers and delayed payload handlers
  -> page-root/display-list objects
  -> 0xff1e publication
  -> 0x1ed84 / 0x1edc6 render-record bridge
  -> 0x1ef6a band render dispatch
  -> compact text, segment-list, rule, fixed-width, and raster renderers
```

Page assembly is display-list based. Command handlers build one current page
root at `0x78297a`; compact/raster bucket objects live under root `+0x1c`,
rules under `+0x24`, fixed-list objects under `+0x28`, and context slots under
`+0x2c..+0x68`. Publication `0xff1e` snapshots that root into a page/control
pool record and clears `0x78297a`. Render entry then copies those roots through
`0x1ed84` / `0x1edc6` and renders scheduler-selected band words through
`0x1eba4` / `0x1ef6a`; the ROM-local model does not require or imply a
parser-time full-page bitmap.

Every reproduction claim below requires a checked-in note that names the ROM
address boundary and cites focused disassembly, ROM bytes/tables, static
cross-reference analysis, or generated table extracts used as supporting
material. Fixture scripts may be cited as model-consistency checks, but they
are not primary evidence. The checked-in note is the deliverable; ignored
generated reports are supporting material, not the only documentation.

Evidence in these notes is disassembly-centered. Primary evidence is ROM bytes,
decoded tables, instruction listings, static cross-references, and RAM fields
read or written by those instructions. Semantic names and output effects are
interpretations derived from that static evidence. Fixture scripts and generated
checks are model-consistency aids: they exercise the documented interpretation
against selected byte streams, but they are not evidence from a running printer
or an executing ROM. "Confidence" therefore means how directly the disassembly
supports a claim, with fixtures cited only as reproducible checks of the
interpretation.

Coverage means a checked-in note names the ROM address range, field
writers, field readers/consumers, visible or state output, fixtures, and
disassembly evidence for that edge. For example, host byte-source coverage
means `0xa904..0xabf0` and the cited disassembly/model checks define which
firmware byte source feeds parser `0xda9a` / `0xdaf0` / `0xdb74`; it does not
mean every physical bus signal has been named. Render coverage means
`0x1ed84` / `0x1edc6` / `0x1ef6a` plus the compact, segment-list, rule,
fixed-list, and raster helpers explain how ROM state is converted into bitmap
bytes. Those bitmap bytes are the ROM-derived result being documented; there is
no later external rendered-row image to compare against.

The physical timing boundary is separate from ROM-local reproduction
coverage. Timing-sensitive surfaces are host fetch/polling
(`0xa904..0xab8a`), scan/status interrupt and wait-object dispatch
(`0x0f84..0x1282`), and active render scheduling
(`0x1eb2a..0x1ed84`). The disassembly-backed model records the state effects
after those events are observed: pending bytes `0x78399e/0x78399f`, shadow byte
`0x7828f9`, wait-object state, active source `0x780eae`, active work pointer
`0x783a18`, and band words. Board evidence is only needed when a claim depends
on mapping physical formatter/DC connector signals or MMIO bits that the ROM
treats as external events. The named physical formatter/DC edge is
connector `J205`: `BD`, `VDO`, `VSREQ`, `VSYNC`, `PRNT`, command/status
strobes, and ready signals. Current ROM evidence does not yet map those
signals to exact MMIO bits; the board-facing boundary is tracked in
[dc-controller-engine.md](dc-controller-engine.md).

## Stream Trace Procedure

Use this procedure when starting from a concrete supported host byte stream.
It keeps the controlling artifact byte/dataflow oriented while preserving the
command-family and page-image structure:

1. Normalize the byte source:
   start at [host-byte-fetch.md](host-byte-fetch.md) and classify which
   `0xa904` source produces each parser byte: live/ring/direct host input,
   pushback stack, data-chain replay, or macro replay. If the stream includes
   delayed payload bytes, keep the payload reader's direct `0xa904` calls
   separate from parser-wrapper bytes.
2. Classify each admitted byte:
   use [pcl-command-map.md](pcl-command-map.md#inbound-byte-outcome-classes)
   to decide whether the byte is printable, alternate/data append, explicit
   no-output parser behavior, syntax/prefix state, a state-only terminal, a
   delayed-payload arming byte, a page-object producer, a publication/render
   boundary, or a host/status side channel.
3. Follow parser records and dispatch:
   for command bytes, use [pcl-parser-core.md](pcl-parser-core.md) to track
   parser mode `0x782999`, parser record cursor `0x78299e`, the six-byte
   record fields, delayed-payload scratch `0x782a1a/0x782a1c/0x782a20..`,
   normal table `0x112a4`, and alternate/data table `0x116f6`. Then jump to
   the owner note named by
   [pcl-command-map.md](pcl-command-map.md#supported-stream-dispatch-matrix).
4. Record command state effects:
   in the owner note, capture the canonical fields written by the handler,
   parser scratch consumed, derived/cache fields, firmware bookkeeping,
   readers/consumers, and no-output side effects. State-only commands remain
   in this step until a later byte consumes their changed fields.
5. Map page/image objects:
   when a command creates page content, use
   [page-record-storage.md](page-record-storage.md) and its renderer-facing
   object class map to identify the page-root field written by the producer:
   compact/segment/raster buckets under root `+0x1c`, rule list under root
   `+0x24`, fixed list under root `+0x28`, and context slots under root
   `+0x2c..+0x68`.
6. Cross the publication and scheduler boundary:
   use [publication-commands.md](publication-commands.md),
   [page-record-storage.md](page-record-storage.md), and
   [active-render-scheduler.md](active-render-scheduler.md) to follow
   `0xff1e`, pool cursors `0x780ea6/0x780eaa/0x780eae`, render-work pointer
   `0x783a18`, active copy `0x1ed84`, and bridge `0x1edc6`. If the stream is
   not published yet, the visible output remains pending page-record state.
7. Derive pixels from ROM render helpers:
   use [page-raster-imaging.md](page-raster-imaging.md) and the Bitmap Render
   Dispatch Contract in [semantic-state-model.md](semantic-state-model.md) to
   follow `0x1ef6a` into compact text/downloaded glyph helpers, segment-list
   helper `0x1f812`, rule helpers `0x1f4e0` / `0x1f596`, fixed-list helper
   `0x1f756`, or encoded raster helper `0x1f88e`. Row vectors are derived
   from those ROM helpers, object fields, and ROM/resource bitmap bytes, not
   from an external print comparison.
8. State any unresolved boundary exactly:
   if the trace stops, classify the stop as ROM-local unknown,
   hardware/MMIO boundary, missing external resource data, or optional
   physical correlation. Name the exact address range and the state or byte
   whose value is not proven.

## State Classification Guide

Use these categories consistently when documenting a command family or
end-to-end stream:

- Canonical state:
  persistent firmware state that later handlers or renderers consume as the
  source of truth. Examples include parser mode `0x782999`, selected text
  slot `0x782f06`, current page root `0x78297a`, page-root bucket/rule/fixed
  roots `+0x1c/+0x24/+0x28`, downloaded glyph records installed by
  `0x16498`, VFC table `0x782dde..0x782edd`, published pool head
  `0x780ea6`, active source `0x780eae`, and render roots copied by
  `0x1edc6`.
- Derived/cache state:
  values recomputed from canonical inputs or object fields and safe to derive
  when replaying the ROM model. Examples include bucket/key caches
  `0x782a7c..0x782a7e`, raster split capacity `0x782a80`, render-band caches
  `0x783a20`, `0x783a22`, `0x783a28`, stride `0x783a1c`, compact glyph cache
  `0x783a2c`, and destination phase/cache fields used by `0x1f3d4` /
  `0x1f626`.
- Parser scratch:
  transient tokenizer, command-record, and delayed-payload storage whose
  contents matter only until dispatch restores or consumes them. Examples
  include six-byte records at `0x78299e..`, digit scratch
  `0x782a42..`, matched-byte scratch `0x783196..0x783199`, delayed flag and
  saved record `0x782a1a/0x782a1c/0x782a20..0x782a25`, and payload-reader
  local stack words.
- Firmware bookkeeping:
  allocator, scheduler, retry, append, and frame state that controls firmware
  progress but is not itself a page/image semantic value. Examples include
  stream allocator fields `0x782a70/0x782a72/0x782a76`, publication flag
  `0x782996`, data-chain frame pointer `0x782d76`, append sink `0xe002`,
  render work selectors `0x7820bc/0x7820c0`, active render pointer
  `0x783a18`, wait-object records, and status/service counters.
- Hardware/external state:
  ROM-visible MMIO registers, physical bus signals, optional resource windows,
  retained storage, and formatter/DC timing inputs. Examples include direct
  host/device registers around `0x8e01`, `$8000.w`, `$a200`, `$a400`,
  `$fffee00b..$fffee013`, optional resource windows
  `0x200000..0x5ffffe`, and formatter/DC connector signals documented in
  [dc-controller-engine.md](dc-controller-engine.md).
- Unknown or unresolved state:
  use only when a concrete address range or field has observed reads/writes
  but its source, consumer, physical identity, or legal values are not proven.
  The boundary entry must say whether it is ROM-local unknown,
  hardware/MMIO, missing external resource data, or optional physical
  correlation. Current examples are the physical decode for
  `0x0c0000..0x0c0321`, exact MMIO-to-formatter signal mapping, and bounded
  downloaded-glyph helper table/source-read edges.

Do not use fixtures as a separate state class. A fixture can exercise a
documented interpretation, but the documented field must still be classified
as one of the categories above.

## Minimal Host Input Walkthrough

This is the smallest top-level host-byte spine. It documents the firmware
boundary before parser state exists: routine `0xa904` chooses one normalized
byte source, returns an unsigned byte in `D7`, or returns `D7 = -1` for the
documented no-byte gate. Parser, payload, macro, raster, and downloaded-font
readers all build on this byte contract.

Representative sources:

```text
ring bytes: 21 21
data-chain replay bytes: 21 0d
direct mode byte: 1a
```

Source priority at `0xa904`:

- Service byte `0x7821cd` wins first. `0xa904` calls
  `0x10cc(0x780202)` through the service retry path and then retries the
  byte-source decision.
- Buffered-source byte `0x780e66` plus gate byte `0x780e3b` returns
  `D7 = -1` before any stack, data-chain, ring, or direct hardware source is
  consumed.
- First pushback stack count `0x783e8c` and pointer `0x783e8e` win next.
  The pointer is one past the next byte; the routine predecrements it before
  reading.
- Active data-chain frame pointer `0x782d76` wins after the first stack.
  Frame longword `+4` is the remaining count or `-1` end marker. Nonzero
  counts call `0x9f6a`; end markers clear the field, call `0xe22c`, and retry.
- Second pushback stack count `0x783e76` and pointer `0x783e78` win after the
  data-chain source.
- Ring input is used when selector `0x780e40 == 0` and ring count
  `0x783e54` is nonzero. It reads from pointer `0x783e56`, wraps after
  `0x783e53` to `0x783a4c`, decrements the count, and returns the byte.
- Direct mode 1 uses status/data/acknowledge registers `0x8e01`, `0x8801`,
  and `0x8c01`, then control writes through `0xa601` and `0xaa01`.
- Other nonzero direct modes use status/data/control registers
  `0xfffee005`, `0xfffee001`, and `0xfffee009`.

Consumer boundaries:

- Parser wrapper `0xda9a` calls `0xa904` and only adds ESC-aware lookahead.
  Non-`ESC` bytes enter parser loop `0x11774` unchanged.
- Payload/control reader `0xdace` also calls `0xa904`, but its local
  `0x1a 0x58` probe belongs to that reader family, not to the byte source.
- Display-functions, transparent text, raster payload, VFC payload, and
  downloaded-font readers either call `0xa904` directly or through their
  family reader; each owns its own `D7 = -1` and `0x1a` behavior.
- Macro execute/call replay has no separate direct call site. Replay frames
  created by `0xe418` become active data-chain frames under `0x782d76`, so
  replayed bytes re-enter through the same `0xa904` source priority.

Output effect:

- `0xa904` does not parse PCL and does not create page objects or pixels.
- Its visible reproduction effect is source equivalence. The same byte stream
  can come from ring input, pushback, data-chain replay, or direct hardware
  and then follow the same parser and page-object path.
- The byte source must not globally normalize `0x1a 0x58`. Direct modes report
  `0x1a` through `0x9ec0` and preserve `D7 = 0x1a`; payload readers such as
  `0xdace`, transparent text, raster, and downloaded-font readers apply their
  own local pair handling after the byte is fetched.

State classification:

- Canonical:
  first stack `0x783e8c` / `0x783e8e`, data-chain frame pointer `0x782d76`,
  second stack `0x783e76` / `0x783e78`, ring count/read/write state
  `0x783e54` / `0x783e56` / `0x783e5a`, ring bounds
  `0x783a4c..0x783e53`, and direct selector `0x780e40`.
- Derived/cache:
  ring occupancy and free-capacity values, low-water threshold `0x783e5e`,
  status-escape sequence cursor `0x783e62`, and control-shadow bytes
  `0x7828fa` / `0x7828fb`.
- Parser scratch:
  none. Parser scratch begins only after a returned byte reaches `0xda9a`,
  `0x11774`, `0x12218`, or a payload reader.
- Firmware bookkeeping:
  service-needed byte `0x7821cd`, service-active byte `0x7821cc`,
  buffered-source bits `0x780e66`, no-byte gate `0x780e3b`,
  direct-mode completion byte `0x7828ec`, host status accumulator
  `0x780e2e`, and data-chain frame-end unwinding through `0xe22c`.
- Hardware/external:
  direct-mode register banks `0x8e01` / `0x8801` / `0x8c01` /
  `0xa601` / `0xaa01` and `0xfffee005` / `0xfffee001` /
  `0xfffee009`. Their ROM-visible ready/data/control roles are documented;
  physical connector signal names remain board-level boundaries.
- Unknown:
  board-level names and timing for the direct MMIO banks, data-chain frame
  byte `+0x09` values outside observed execute `2`, call `3`, and non-replay
  page-finalization `4`, and user-facing names for host-input quiesce/reset
  branches `0x4218..0x44d2` and `0x61e4..0x6362`.

Evidence:

- Checked-in explanations:
  [host-byte-fetch.md](host-byte-fetch.md),
  [macro-data-chain.md](macro-data-chain.md),
  `Worked Path: Host Byte Source Priority` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md), and
  `Host Byte Fetch And Data-Chain Input` in
  [semantic-state-model.md](semantic-state-model.md).
- Focused listings and extracts:
  `generated/disasm/ic30_ic13_host_byte_fetch_00a904.lst`,
  `generated/disasm/ic30_ic13_host_input_quiesce_004200.lst`,
  `generated/disasm/ic30_ic13_host_input_quiesce_0061e4.lst`,
  `generated/analysis/ic30_ic13_host_byte_fetch_flow.md`, and
  `generated/analysis/ic30_ic13_renderer_fixture_harness.md`.

## Minimal Stream Walkthrough: `!!`

This is the smallest checked-in byte-to-pixel spine for ordinary printable
text. It composes the detailed `Worked Path: Printable Glyph` and `Worked Path:
Text Source Objects And Compact Buckets` sections in
[firmware-dataflow-model.md](firmware-dataflow-model.md) into one top-level
trace.

Input bytes:

```text
21 21
```

Parser and dispatch:

- Each `0x21` byte is normalized by byte-source entry `0xa904` and delivered
  to parser wrapper `0xda9a`.
- Parser loop `0x11774` is in mode zero with parser state byte `0x782999 = 0`.
  Alternate/data mode `0x782c18` is clear.
- No normal-table command row claims `0x21`. The printable fallback dispatches
  each byte to `0xd04a`; no six-byte command record or delayed-payload record
  is created for these two bytes.

Printable source and page-object construction:

- `0xd04a` calls `0x1393a(host_byte, 0x782d7e)`. The source object at
  `0x782d7e` receives the selected font/context pointer, glyph/source pointer,
  mapped compact glyph byte, source flag, and context slot.
- In the documented built-in `LINE_PRINTER` path, `0x1393a` maps host byte
  `0x21` to compact glyph byte `0x20`, glyph-entry pointer `0x015330`,
  source flag `1`, and context slot `0`.
- Source flag `1` routes through the flagged built-in path
  `0xd550 -> 0xd824`. `0xd824` writes positioned source fields
  `+0x12/+0x14/+0x16`, marks page-root live-font flag `0x78297f + slot`,
  and calls `0x12f2e`.
- `0x12f2e` consumes the source glyph byte, source pointer, source flag,
  positioned coordinates, and context slot. It derives compact bucket/key
  fields at `0x782a7c..0x782a7e`, then calls `0x1387c`.
- `0x1387c` stores or reuses a compact bucket object under current page-root
  field `+0x1c`. For the two `!` bytes, the second byte reuses the compatible
  short compact object while capacity remains and appends another
  glyph/coordinate entry.

Publication, bridge, and render:

- Before publication, visible output is pending page-record state rooted at
  current page root `0x78297a`.
- Publication `0xff1e` snapshots the current root into a page/control pool
  record, preserves compact bucket roots, and clears `0x78297a`.
- Render entry `0x1ed84` selects the active source record through
  `0x780eae`. Bridge `0x1edc6` copies source root `+0x1c` to render-record
  `+0x18` and copies page-root context slots `+0x2c..+0x68` to render-record
  context slots `+0x24..+0x60`.
- Scheduler entry `0x1eba4` calls `0x1ef6a` for the active band. `0x1ef6a`
  calls `0x1ef86` for band setup and `0x1efc2` for bucket-chain dispatch.
- `0x1efc2` sees compact object class byte `+0x04 & 0xc0 == 0` and dispatches
  through `0x1effe`. For the built-in short compact object, `0x1effe` selects
  `0x1f034`; `0x1f354` resolves glyph `0x20` through the copied context slot;
  row-copy helpers selected from the table at `0x1fa5c` write the ROM-derived
  bitmap rows into the active band buffer.

State classification:

- Canonical:
  input byte values, parser mode `0x782999`, selected font context and map,
  source object `0x782d7e`, current page root `0x78297a`, page-root compact
  bucket root `+0x1c`, compact bucket object payload entries, page-root
  context slot, published source record, active source `0x780eae`, and
  render-record bucket/context roots.
- Derived/cache:
  compact bucket/key fields `0x782a7c..0x782a7e`, glyph offsets from the
  selected font record, compact coordinate words, render-band fields
  `0x783a20`, `0x783a22`, `0x783a28`, stride `0x783a1c`, and compact glyph
  cache `0x783a2c`.
- Parser scratch:
  the unmatched printable byte in the parser loop and normal-table lookup
  state. No parser command record, digit scratch, or delayed-payload scratch
  survives this printable fallback route.
- Firmware bookkeeping:
  live-font flags at `0x78297f + slot`, stream allocator cursors
  `0x782a70/0x782a72/0x782a76`, publication flag `0x782996`, pool cursors
  `0x780ea6/0x780eaa/0x780eae`, render-work pointer `0x783a18`, and
  scheduler progress fields.
- Hardware/external:
  the physical source that supplied the same normalized `0x21 0x21` bytes to
  `0xa904`, plus any formatter/DC timing events that cause later publication
  and active-band rendering. These do not change the ROM-local byte-to-bitmap
  construction once the same normalized bytes and publication boundary exist.
- Unknown:
  no ROM-local parser-to-compact-render middle edge is unresolved for this
  built-in printable path. Remaining work starts only from streams or state
  that change the selected context/map, source flag, compact selector class,
  bridge roots, scheduler band fields, or row-construction helper.

Evidence:

- Checked-in explanations:
  `Worked Path: Printable Glyph` and `Worked Path: Text Source Objects And
  Compact Buckets` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md),
  [pcl-parser-core.md](pcl-parser-core.md),
  [font-context-metrics.md](font-context-metrics.md),
  [page-record-storage.md](page-record-storage.md),
  [active-render-scheduler.md](active-render-scheduler.md), and
  [page-raster-imaging.md](page-raster-imaging.md).
- Focused listings:
  `generated/disasm/ic30_ic13_main_parser_loop_011774.lst`,
  `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`,
  `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`,
  `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`,
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`,
  `generated/disasm/ic30_ic13_active_render_scheduler_01eb2a.lst`,
  `generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`,
  `generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst`,
  and `generated/disasm/ic30_ic13_bitmap_row_copy_tables_01fa5c.lst`.

## Minimal Text Placement Walkthrough

This extends the printable path to stateful placement commands. The placement
commands do not draw by themselves in the covered streams. They write cursor,
margin, HMI/VMI, or dot-position state; the following printable byte consumes
that state and queues a compact text object at the derived coordinate.

Representative streams:

```text
ESC &k6H !!
ESC &a6l9M !
ESC &a2c+1R !
ESC *p30x30Y !
ESC &f0S ESC &a2C ESC &f1S !
```

Parser and command dispatch:

- Host bytes enter through `0xa904`, parser wrapper `0xda9a`, and parser loop
  `0x11774`.
- `ESC &k#H` reaches HMI handler `0xca8c`.
- `ESC &a#L` reaches left-margin handler `0xeb58`; lowercase `l` keeps
  parser mode `12` active so the following `#M` reaches right-margin handler
  `0xec0c`.
- `ESC &a#C` and `ESC &a#H` reach horizontal cursor handlers `0xf39e` and
  `0xf416`; `ESC &a#R` and `ESC &a#V` reach vertical cursor handlers
  `0xf560` and `0xf60a`.
- Lowercase `c` in `ESC &a2c+1R` keeps parser mode `12` active so the
  relative row command reaches `0xf560` before the printable byte.
- `ESC *p#X` and `ESC *p#Y` reach dot-position handlers `0xf48c` and
  `0xf692`; lowercase `x` keeps parser mode `18` active for the chained
  vertical dot-position final.
- `ESC &f#S` reaches cursor-stack handler `0xf75e`.
- The following printable byte falls through the ordinary printable route
  `0xd04a -> 0xd824 -> 0x12f2e -> 0x1387c`.

Placement behavior:

- `0xca8c` writes accepted HMI values to `0x78315c`. In the documented
  `ESC &k6H!!` stream it stores packed advance `15`, so the second printable
  byte queues at compact coordinate `0x0501` instead of the default
  `0x0201`.
- `0xeb58` converts the left-margin column through HMI `0x78315c`, writes
  accepted values to `0x782dd6`, and may move horizontal cursor `0x782c8a`.
- `0xec0c` converts `abs(parameter) + 1` columns through HMI, writes right
  margin `0x782dda`, sets right-limit latch `0x782a57`, and may clamp current
  horizontal cursor left.
- `0xf39e` converts column units through HMI; `0xf416` converts horizontal
  decipoints through five packed subunits per decipoint. Both commit through
  `0xf4ca`, which applies the relative flag, clamps against page width
  `0x782db8`, updates right-limit state, and writes horizontal cursor
  `0x782c8a`.
- `0xf560` converts row units through VMI `0x783160`; `0xf60a` converts
  vertical decipoints through five packed subunits per decipoint. Both commit
  through `0xf6e2`, which applies relative or top-offset base, clamps vertical
  bounds, and writes vertical cursor `0x782c8e`.
- `0xf48c` and `0xf692` shift whole-dot parameters into the packed coordinate
  domain, then share the same `0xf4ca` / `0xf6e2` commit helpers.
- `0xf75e` pushes or pops cursor-stack entries in `0x782c96..0x782d36`. The
  documented push/move/pop stream restores the original cursor before the
  following printable queues at compact coordinate `0x0001`.

Page-object and render effect:

- The placement commands themselves queue no compact glyph object in the
  covered streams.
- The following printable byte consumes cursor `0x782c8a/0x782c8e`, HMI
  `0x78315c`, selected font context, and pending-width state in `0xd04a`.
- `0xd824 -> 0x12f2e` turns the positioned source into compact object entries;
  `0x1387c` stores or appends those entries under current page-root bucket
  `+0x1c`.
- Documented streams route `ESC &a6l9M!` to compact coordinate `0x0207`,
  `ESC &a2c+1R!` to `0x1a02`, and `ESC *p30x30Y!` to `0x9402`.
- Publication, bridge, scheduler, and render are the same as the printable
  path: `0xff1e -> 0x1ed84 -> 0x1edc6 -> 0x1eba4 -> 0x1ef6a -> 0x1efc2`.

Span-flush sibling:

- Cursor-changing handlers can force pending span publication before they
  overwrite cursor/span state.
- `ESC &a6L!` reaches `0xeb58`, moves horizontal cursor from packed `10` to
  packed `108`, and materializes selector-`0x4000` segment-list object
  `00 00 00 00 40 00 00 01 32 00 03 00 00 10` through
  `0xf34a -> 0x12714 -> 0x126e2` before the following printable queues.
- `ESC &a1R!` reaches `0xf560`, flushes the same pending span state, moves
  vertical cursor to packed `95.1`, and queues the following printable at
  compact coordinate `0xa001`.

State classification:

- Canonical:
  horizontal cursor `0x782c8a`, vertical cursor `0x782c8e`, HMI
  `0x78315c`, VMI `0x783160`, left margin `0x782dd6`, right margin
  `0x782dda`, page width `0x782db8`, vertical bounds
  `0x782dc6/0x782dca`, top offset `0x782dce`, cursor stack
  `0x782c96..0x782d36`, current page root `0x78297a`, compact text objects,
  and selector-`0x4000` span objects.
- Derived/cache:
  packed unit conversions, compact coordinate words, bucket/key fields, right
  limit comparisons, pending span bounds `0x783186/0x783188`, and render-band
  fields after publication.
- Parser scratch:
  parser modes `12` and `18` for lowercase-final chaining, six-byte command
  records rooted at `0x78299e`, parsed relative-flag bit, numeric parameters,
  and the resumed parser state for the following printable byte.
- Firmware bookkeeping:
  right-limit latch `0x782a57`, pending-width latch `0x782a58`,
  pending-text/cursor latch `0x782a6d`, span-flush enable `0x783184`,
  allocation cursors, publication flag `0x782996`, scheduler cursors, and
  render-work progress.
- Hardware/external:
  none for the ROM-local placement contract.
- Unknown:
  no unresolved ROM-local middle edge remains for the documented HMI,
  margin-to-printable, cursor-to-printable, dot-position-to-printable,
  cursor-stack, or span-flush streams. Remaining placement work starts from
  streams that change selected font context, pending-width behavior, span
  object shape, compact object bytes, bucket selection, bridge roots, or
  ROM-derived row construction.

Evidence:

- Checked-in explanations:
  `Worked Path: Cursor And Margin Placement` and `Worked Path: Text Span
  Flush And Underline Objects` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md),
  [direct-control-codes.md](direct-control-codes.md),
  [pcl-command-map.md](pcl-command-map.md),
  [page-record-storage.md](page-record-storage.md),
  [page-raster-imaging.md](page-raster-imaging.md), and
  [semantic-state-model.md](semantic-state-model.md).
- Focused listings and extracts:
  `generated/disasm/ic30_ic13_hmi_vmi_handlers_00ca8c.lst`,
  `generated/disasm/ic30_ic13_dot_position_handlers_00f48c.lst`,
  `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`,
  `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`,
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`,
  `generated/analysis/ic30_ic13_text_cursor_span_flow.md`, and
  `generated/analysis/ic30_ic13_direct_control_code_flow.md`.

## Minimal Text Span/Underline Walkthrough

This is the smallest top-level path for pending text-span output. It covers
underline/text-attribute state, the printable metric consumers that update
pending span bounds, and the flush points that turn those bounds into
page-record objects. The printable glyph still uses the compact text path; the
span is a separate page object rendered by the segment-list or fixed-list
renderer.

Representative stream:

```text
ESC &d3D ! ESC &d@
```

Parser and span-state dispatch:

- Host bytes enter through `0xa904`, parser wrapper `0xda9a`, and parser loop
  `0x11774`.
- `ESC &d3D` dispatches to underline/text-attribute tokenizer `0x12622`.
- For the documented selector, `0x12622` writes underline/text-attribute
  selector byte `0x783185 = 1`.
- Printable byte `0x21` then reaches `0xd04a` and follows the ordinary
  source-object and compact queue path.
- Final `ESC &d@` dispatches to `0x12622` again and takes the terminal flush
  path through `0x12714`, followed by `0x126e2` span re-arm work.

Pending span update:

- `0xd04a` calls `0x1393a` to build source object `0x782d7e` from the
  selected font context.
- In the covered flagged built-in path, `0xd550 -> 0xd824` queues the compact
  glyph through `0x12f2e` and marks page-root live-font state.
- After the compact glyph queues, `0xd824` calls span consumer `0xd8fc` when
  span updates are enabled.
- `0xd8fc` reads selected context fields `+0x16`, `+0x18`, and `+0x1a`.
  Because `0x783185` is set, it uses alternate offset word `+0x1a` to update
  the high-y span bound.
- The pending span lives in `0x783184`, `0x783186`, `0x783188`, and
  `0x78318a` until a flush point runs. It is not a page object before
  `0x12714`.

Page-object creation:

- `0x12714` clears pending flag `0x783184`, packages an 8-byte local source
  from the pending bounds, ensures current root `0x78297a` through `0x10084`,
  gates the source against page extent `0x782db6`, and calls `0x13520`.
- `0x13520` derives selector/key state through `0x137a2` and branches on
  orientation byte `0x782da3`.
- In portrait, `0x13520 -> 0x1354a -> 0x135f0` inserts class-`0x40`
  segment-list objects under page-root bucket array `+0x1c`.
- The documented underline stream flushes this portrait object:

```text
00 00 00 00 40 00 00 01 3a 00 03 00 00 12
```

- Its class byte `+0x04 = 0x40` selects segment-list rendering, count word
  `+0x06 = 1` says one six-byte entry follows, entry key is `0x3a00`, y is
  `3`, and extent is `18`.
- In landscape, the same pending-span source routes to fixed-list insertion
  `0x136d2` under page-root `+0x28`; bridge and rendering then consume it as
  a fixed-list object rather than a bucket-chain segment-list object.

Flush producers:

- CR handler `0xf02c` can flush pending span through
  `0xf34a -> 0x12714 -> 0x126e2` before cursor reset and line advance.
- Left-margin handler `0xeb58` can flush the same pending span before moving
  horizontal cursor `0x782c8a`.
- Vertical cursor handler `0xf560` can flush the span before moving vertical
  cursor `0x782c8e`.
- The documented CR/margin/cursor sibling object is:

```text
00 00 00 00 40 00 00 01 32 00 03 00 00 10
```

- That is a bucket-chain segment-list object with selector word `0x4000`,
  one entry, packed key `0x3200`, y `3`, and extent `16`.

Bridge and render effect:

- Publication `0xff1e` preserves both the compact glyph object and any flushed
  span object under the current page root.
- Bridge `0x1edc6` copies source bucket root `+0x1c` to render-record
  `+0x18` for portrait segment-list spans and copies fixed-list root `+0x28`
  to render-record `+0x20` for landscape fixed-list spans.
- `0x1ef6a -> 0x1efc2` dispatches class-`0x40` segment-list objects to
  `0x1f812`. `0x1f812` consumes the six-byte entries and calls `0x1f862`,
  which writes counted mask spans using full words plus a trailing mask from
  table `0x308f2`.
- Fixed-list span objects render through `0x1f756` / `0x1f7b0` / `0x1f626`.
  The fixed-list bridge initializes continuation bytes so later bands can
  resume remaining rows.

State classification:

- Canonical:
  underline/text-attribute selector `0x783185`, pending span enable
  `0x783184`, span bounds `0x783186`, `0x783188`, and `0x78318a`, selected
  font context, source object `0x782d7e`, orientation byte `0x782da3`,
  current page root `0x78297a`, compact glyph object, segment-list span
  objects under root `+0x1c`, and fixed-list span objects under root `+0x28`.
- Derived/cache:
  packed span keys such as `0x3a00` and `0x3200`, producer bucket/key fields
  `0x782a7c..0x782a7e`, selected font metric offsets, segment-list masks from
  `0x308f2`, fixed-list pattern words from `0x308de`, and render-band fields.
- Parser scratch:
  six-byte `ESC &d3D` and `ESC &d@` records rooted at `0x78299e`, parser mode
  state, and the printable byte between the two commands.
- Firmware bookkeeping:
  page-root live-font flags, span re-arm work in `0x126e2`, allocation
  cursors for `0x13520` / `0x135f0` / `0x136d2`, retry/finalization bits,
  publication flag `0x782996`, scheduler cursors, and render-work progress.
- Hardware/external:
  none for the ROM-local span/underline contract.
- Unknown:
  no unresolved ROM-local middle edge remains for the documented underline
  stream, CR/margin/vertical-cursor span flushes, portrait segment-list
  insertion, landscape fixed-list insertion, or allocation-failure retry.
  Remaining span work starts from selected-font or byte-stream variants that
  change concrete metric fields, pending span bounds, orientation branch,
  fixed/segment object fields, bridge roots, or ROM-derived row construction.

Evidence:

- Checked-in explanations:
  `Worked Path: Text Span Flush And Fixed-Width Spans` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md),
  [direct-control-codes.md](direct-control-codes.md),
  [font-context-metrics.md](font-context-metrics.md),
  [page-record-storage.md](page-record-storage.md),
  [page-raster-imaging.md](page-raster-imaging.md), and
  [semantic-state-model.md](semantic-state-model.md).
- Focused listings and extracts:
  `generated/disasm/ic30_ic13_text_span_flush_012714.lst`,
  `generated/disasm/ic30_ic13_text_span_state_0126e2.lst`,
  `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`,
  `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`,
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`,
  `generated/analysis/ic30_ic13_text_cursor_span_flow.md`,
  `generated/analysis/ic30_ic13_printable_text_path.md`, and
  `generated/analysis/ic30_ic13_render_dispatch_tables.md`.

## Minimal Parser Dispatch Walkthrough

This is the smallest top-level parser spine. It explains how normalized bytes
become printable fallback calls, six-byte command records, table handlers,
delayed payload calls, stored alternate/data bytes, or explicit no-output
parser decisions before command-family notes take over.

Representative byte classes:

```text
21
00 07 0b
ESC &l66P
ESC *b2W c3 3c
```

Parser entry and record format:

- Parser loop `0x11774` starts from bytes returned by wrapper `0xda9a`.
- `0xda9a` calls normalized byte source `0xa904`. Non-`ESC` bytes return
  unchanged. `ESC` causes one extra wrapper fetch so `ESC ?` forms can be
  swallowed or reported before the main loop sees the next parser byte.
- Parser mode byte `0x782999` selects the current table range. Normal mode
  uses table roots `0x112a4` / `0x112a8`; alternate/data mode selected by
  `0x782c18` uses table roots `0x116f6` / `0x116fa`.
- Each parser-table row is six bytes: matched byte, next mode, and handler
  longword.
- Parameterized ESC commands are tokenized by `0xdaf0` and `0xdb74` into
  six-byte records rooted at cursor `0x78299e`:

```text
+0  flags
+1  final byte
+2  signed integer parameter
+4  signed fractional parameter
```

Normal printable and direct table dispatch:

- In mode zero with alternate/data clear, bytes whose low seven bits are
  `>= 0x20` normally take the fast printable path to `0xd04a`.
- Nonprintable bytes and nonzero parser modes scan the current table. A
  matching row with a handler longword calls that handler.
- A matching row with no handler writes the row's next mode and may take the
  terminal reset path. It is still a real parser decision, not an unknown
  command.
- Prefix handlers such as `0x11eb6`, `0x11ec8`, `0x11eda`, and `0x11eec`
  update parser mode and callback helper state. Terminal handlers such as
  `0xf9e8`, `0xedb0`, `0x10898`, or `0x11f82` are the handoff from syntax to
  semantic command-family documentation.

Command-record and delayed-payload behavior:

- `0xdb74` fills one six-byte record, including optional sign, capped integer
  digits, up to four fractional digits, and final byte `+1`.
- `0xdaf0` combines lowercase-final command-family records with later
  uppercase finals in the same ESC family. Lowercase finals can leave a record
  pending instead of immediately running a terminal command.
- Delayed payload setup `0x121cc` rewinds record cursor `0x78299e`, writes
  pending byte `0x782a1a`, stores handler pointer `0x782a1c`, and saves the
  six-byte record at `0x782a20..0x782a25`.
- Terminal restore `0x12218` later copies the saved record back to the active
  cursor and calls the saved handler. This is why a stream such as
  `ESC *b2W c3 3c` is two-stage: parser syntax records byte count `2`, then
  raster handler `0x105d0` consumes payload bytes after restore.
- Other delayed consumers use the same restore boundary: transparent data
  `0x12452`, VFC table load `0x12cfe`, downloaded descriptor path `0x15d0a`,
  downloaded payload path `0x16c14`, and generic counted wrapper `0x1228a`.

No-output and alternate/data cases:

- Normal mode-zero C0 bytes `0x00`, `0x07`, and `0x0b` are explicit blank
  rows in the normal table. They write mode `0`, call `0x12218`, reset parser
  scratch, and do not call printable or control handlers.
- Alternate/data mode handles blank C0 rows differently. Mode-zero
  alternate/data rows for `0x00` and `0x07..0x0f` append the matched byte
  through `0xe002` before the same terminal reset path, preserving input for
  macro/data-chain replay while suppressing normal BS/HT/LF/FF/CR/SO/SI
  effects.
- `ESC ?` is handled by wrapper `0xda9a`, not by a page-output handler.
- `ESC Z` is local terminator input for display-functions readers
  `0x12536` and `0x12120`, not a standalone drawing command.
- `ESC &lT/t` has no standalone page-output effect in the documented parser
  table; lowercase `t` only participates in command-family chaining through
  rewind helper `0x11f4c`.

State classification:

- Canonical:
  parser mode `0x782999`, command-record cursor `0x78299e`, normal versus
  alternate/data selector `0x782c18`, active command records, and terminal
  handler ownership chosen from the parser tables.
- Derived/cache:
  table scan bounds, callback helper pointer `0x78299a`, and local lookahead
  decisions from `0xdaf0` / `0xda9a`.
- Parser scratch:
  digit and nonnumeric scratch cursors `0x782a3e` and `0x782a26`, scratch
  buffers `0x782a42..` and `0x782a2a..`, matched-byte buffer
  `0x783196..0x783199`, and temporary tokenizer accumulators.
- Firmware bookkeeping:
  delayed-payload pending byte `0x782a1a`, delayed handler pointer
  `0x782a1c`, saved record `0x782a20..0x782a25`, alternate echo latch
  `0x782a56`, and append sink `0xe002`.
- Hardware/external:
  none beyond the byte source that supplied `0xa904`; physical bus timing does
  not change parser classification after the same byte has been admitted.
- Unknown:
  no unresolved ROM-local middle edge remains for parser-table dispatch,
  command-record construction, delayed-payload snapshot/restore, or the cited
  no-output rows. Remaining parser work starts only from byte streams that
  expose a different terminal handler, delayed consumer, append path, or
  command-family state transition.

Evidence:

- Checked-in explanations:
  [pcl-parser-core.md](pcl-parser-core.md),
  [pcl-command-map.md](pcl-command-map.md),
  `Worked Path: Command Record And Payload Dispatch` and
  `Worked Path: Explicit No-Output Parser Rows` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md), and
  `Parser Record And Delayed Payload State` in
  [semantic-state-model.md](semantic-state-model.md).
- Focused listings and extracts:
  `generated/disasm/ic30_ic13_pcl_escape_parser_00da9a.lst`,
  `generated/disasm/ic30_ic13_main_parser_loop_011774.lst`,
  `generated/disasm/ic30_ic13_tokenizer_stateful_helpers_011ba6.lst`,
  `generated/disasm/ic30_ic13_payload_dispatch_011f82.lst`,
  `generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst`,
  `generated/disasm/ic30_ic13_parser_setup_handlers_011ea4.lst`,
  `generated/analysis/ic30_ic13_parser_dispatch_tables.md`,
  `generated/analysis/ic30_ic13_pcl_command_map.md`, and
  `generated/analysis/ic30_ic13_parser_xrefs.md`.

## Minimal Ignored/No-Output Parser Walkthrough

This is the smallest top-level ignored/no-output parser spine. It separates
explicit parser decisions from unknown commands: some bytes are consumed by
the ROM and deliberately produce no page object, while alternate/data mode can
store the same byte instead of running its normal immediate effect.

Representative streams:

```text
NUL BEL VT
ESC ? 11
ESC Y ! ESC Z
ESC &lT
```

Parser classification:

- Normal-mode C0 bytes `0x00`, `0x07`, and `0x0b` enter through
  `0xa904 -> 0xda9a -> 0x11774`.
- In the normal mode-zero table, these three bytes have explicit rows with
  next mode `0` and no handler longword. They are matched table rows, not
  unmatched printable fallback.
- Adjacent normal C0 rows dispatch to handlers such as BS `0xf2a8`, HT
  `0xf1cc`, LF `0xf08c`, FF `0xf0f0`, CR `0xf02c`, SO `0xc6b8`, and SI
  `0xc68a`; the no-output rows deliberately have no handler.
- A zero-handler row writes parser mode `0`, enters terminal path
  `0x11912..0x119bc`, calls delayed restore boundary `0x12218`, and then
  resets parser scratch.
- Because `0x12218` can restore and dispatch a pending delayed payload before
  scratch reset, these rows are not a simple byte skip when
  `0x782a1a/0x782a1c/0x782a20..0x782a25` are active.

Parser artifacts and unimplemented rows:

- `ESC ?` is consumed in byte wrapper `0xda9a`, not by a page-output handler.
  After `0xda9a` sees `ESC`, wrapper fetch `0xdaa6` checks the next byte; when
  it is `?`, wrapper fetch `0xdab2` consumes a third byte. Third byte `0x11`
  is swallowed and the wrapper restarts; other third bytes follow the wrapper
  reporting path described in [pcl-parser-core.md](pcl-parser-core.md).
- `ESC Z` is local terminator input for `ESC Y ... ESC Z` display-functions
  readers. Normal reader `0x12536` and alternate/data reader `0x12120`
  consume the terminator inside direct `0xa904` loops. It is not a standalone
  imaging command in the main parser table.
- `ESC &lT/t` is an unimplemented parser-table slot. Uppercase `T` has no
  terminal handler. Lowercase `t` reaches generic rewind helper `0x11f4c` for
  lowercase command-family chaining and does not write page environment,
  page-object, publication, or render state by itself.

Alternate/data counterpart:

- Alternate/data mode uses table roots `0x116f6` / `0x116fa` instead of the
  normal table roots `0x112a4` / `0x112a8`.
- In alternate/data mode, mode-zero blank C0 rows `0x00` and `0x07..0x0f`
  are append-preserving terminal rows.
- Path `0x11930..0x11ab8` stores the matched byte in parser scratch, flushes
  command and numeric scratch through `0x123ae` and `0x123de`, appends the
  byte through macro/data sink `0xe002`, then rejoins the terminal reset path.
- Therefore alternate/data BS, HT, LF, FF, CR, SO, and SI bytes are preserved
  as stored input instead of running normal-mode cursor/control handlers.
  They can become visible only if macro/data-chain replay later feeds those
  stored bytes back through `0xa904`.

Output effect:

- Normal `0x00`, `0x07`, and `0x0b` do not call printable handler `0xd04a`,
  direct-control handlers, page-root allocation, publication, scheduler, or
  render entry.
- `ESC ?`, display-reader `ESC Z`, and `ESC &lT/t` are parser artifacts or
  unimplemented rows, not hidden drawing commands.
- The reproduction model must still preserve parser mode, delayed-payload
  restore, command scratch reset, and alternate/data append behavior, because
  those effects can determine how later bytes are parsed or replayed.

State classification:

- Canonical:
  parser mode `0x782999`, normal versus alternate/data selector `0x782c18`,
  command-record cursor `0x78299e`, delayed pending byte `0x782a1a`,
  delayed handler pointer `0x782a1c`, and saved delayed record
  `0x782a20..0x782a25`.
- Derived/cache:
  none for immediate page imaging. Alternate/data appended bytes are stored
  input for later macro/data-chain replay, not rendered state.
- Parser scratch:
  matched-byte buffer `0x783196..0x783199`, nonnumeric scratch cursor
  `0x782a26`, numeric scratch cursor `0x782a3e`, scratch buffers
  `0x782a2a..` and `0x782a42..`, and alternate echo latch `0x782a56`.
- Firmware bookkeeping:
  parser table pointers, active callback helper pointer `0x78299a`,
  terminal delayed-restore boundary `0x12218`, append sink `0xe002`, and
  scratch flush helpers `0x123ae` / `0x123de`.
- Hardware/external:
  none for the ROM-local no-output parser contract after bytes have entered
  through `0xa904`.
- Unknown:
  no unresolved ROM-local middle edge remains for normal no-output C0 rows,
  alternate/data append-preserving C0 rows, `ESC ?`, display-reader `ESC Z`,
  or `ESC &lT/t`. Remaining ignored/error work starts only from byte streams
  that exercise a different rejecting predicate, delayed consumer, append
  path, or status/error-reporting side channel.

Evidence:

- Checked-in explanations:
  `Worked Path: Explicit No-Output Parser Rows` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md),
  [pcl-parser-core.md](pcl-parser-core.md),
  [pcl-command-map.md](pcl-command-map.md),
  [display-functions.md](display-functions.md), and
  [macro-data-chain.md](macro-data-chain.md).
- Focused listings and extracts:
  `generated/disasm/ic30_ic13_main_parser_loop_011774.lst`,
  `generated/disasm/ic30_ic13_pcl_escape_parser_00da9a.lst`,
  `generated/analysis/ic30_ic13_parser_dispatch_tables.md`,
  `generated/analysis/ic30_ic13_pcl_command_map.md`, and
  `generated/analysis/ic30_ic13_parser_xrefs.md`.

## Minimal Host/Status Side-Channel Walkthrough

This is the smallest top-level side-channel spine. It covers parser-visible
commands and status workers that write host/interface output bytes rather than
page objects. They matter to exact byte-stream reproduction because a
bidirectional host can react to these bytes, and a full output FIFO can stall a
parser-side producer.

Representative response stream:

```text
ESC *r1K 11
```

Parser and response dispatch:

- Host bytes enter through `0xa904`, parser wrapper `0xda9a`, and parser loop
  `0x11774`.
- The parser-table command path reaches wrapper `0x12034` for `ESC *r#K`.
  The same wrapper is reached by the `ESC *s#^` sibling.
- `0x12034` calls setup helper `0x11efe`, appending a synthetic six-byte
  record with record word `+2 = 1`.
- Producer `0x122be..0x12326` rewinds parser record cursor `0x78299e` to that
  synthetic record, fetches the following query byte through `0xda9a`, and
  tests the active record word.
- If the fetched byte is `0x11` and record word `+2` is `1` or `-1`, the
  producer walks ROM literal `33440A\r\n` at `0x12280` and enqueues each byte
  through blocking FIFO helper `0xb090`.
- Other fetched bytes are reported through `0x9ec0` instead of entering the
  host-output FIFO.

Output FIFO and status worker:

- Startup helper `0x31d6` initializes FIFO storage `0x783e92..0x783ed1`,
  count `0x783ed2`, read pointer `0x783ed4`, and write pointer `0x783ed8`.
- `0xb0c0` enqueues one byte when count `0x783ed2 < 0x40`, wraps write
  pointer `0x783ed8`, increments the count, and returns success.
- `0xb090` retries `0xb0c0` and waits through `0x10c8(0x7801e2)` while the
  FIFO is full.
- Output worker `0xae2c` sleeps only when FIFO count `0x783ed2`, pending
  status count `0x780e22`, and bridge-service byte `0x783e61` are all zero.
- In output mode `0`, worker `0xae2c` drains FIFO bytes through `0xb022` and
  writes them through retry helper `0xaf7c` to `0xfffe0003`.
- In output mode `1`, it dequeues and discards FIFO bytes.
- In other nonzero modes, it sends queued FIFO bytes through
  `0xafcc -> 0xa1d6` to `0xfffee003`.
- Status builder `0xaece` can also emit service byte `0x13` from
  `0x783e61`, or build normal status bytes from base `0x30` using
  `0x780e12`, `0x780e90`, `0x780e2a`, `0x780e0a`, and reason byte
  `0x783e60`.

Output effect:

- This path creates no page root, page object, published record, render work
  record, or pixels.
- It does not feed `0x1ed84`, `0x1edc6`, `0x1ef6a`, or bitmap render helpers.
- It can still affect a full reproduction session if the modeled host consumes
  `33440A\r\n` or status bytes and sends different later input, or if full
  FIFO state stalls `0xb090`.
- A closed byte-stream-to-page renderer that ignores backchannel bytes can
  treat this path as no page-output while preserving parser/FIFO state.

State classification:

- Canonical:
  output FIFO count `0x783ed2`, read pointer `0x783ed4`, write pointer
  `0x783ed8`, storage `0x783e92..0x783ed1`, backend selector `0x780e40`,
  response literal `0x12280..0x12288`, active record word `+2`, and fetched
  query byte.
- Derived/cache:
  pending status count `0x780e22`, bridge-service byte `0x783e61`,
  reason byte `0x783e60`, accepted-byte cache `0x780e62`, aggregate words
  `0x780e12` and `0x780e0a`, warning/status accumulator `0x780e2a`,
  page-environment status flag `0x780e90`, and media/status cache
  `0x780e98`.
- Parser scratch:
  synthetic record from `0x11efe`, parser record cursor `0x78299e`, and the
  `0x122be` query fetch state.
- Firmware bookkeeping:
  wait object `0x7801e2`, output-worker sleep state, critical sections around
  FIFO mutation, and service/message helpers under `0x7612`, `0x8656`, and
  `0x8a48`.
- Hardware/external:
  output registers `0xfffe0001`, `0xfffe0003`, `0xfffee005`, and
  `0xfffee003`, plus the external protocol meaning of query byte `0x11`.
- Unknown:
  no ROM-local page/render edge remains. Remaining boundaries are the physical
  output-register mapping, the external protocol name for the `0x11` query,
  and host behavior if it consumes backchannel bytes.

Evidence:

- Checked-in explanations:
  [errors-and-status.md](errors-and-status.md),
  [io-interfaces.md](io-interfaces.md),
  [host-byte-fetch.md](host-byte-fetch.md),
  `Worked Path: Host Interface Output FIFO And Model-ID Backchannel` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md), and
  `Host Interface Output FIFO` in
  [semantic-state-model.md](semantic-state-model.md).
- Focused listings and extracts:
  `generated/disasm/ic30_ic13_payload_dispatch_011f82.lst`,
  `generated/disasm/ic30_ic13_host_output_fifo_00b022.lst`,
  `generated/disasm/ic30_ic13_host_output_worker_00ae2c.lst`,
  `generated/disasm/ic30_ic13_host_output_retry_00af7c.lst`,
  `generated/disasm/ic30_ic13_interface_output_mmio_00a1b0.lst`,
  `generated/analysis/ic30_ic13_parser_dispatch_tables.md`,
  `generated/analysis/ic30_ic13_pcl_command_map.md`, and
  `generated/analysis/ic30_ic13_strings.txt`.

## Minimal External Service/Error Walkthrough

This is the smallest top-level service/error preemption spine. It is not
entered by a PCL command table row. It documents the ROM-visible
`0x2e38 -> 0xba48` external-ready/service loop that can stop or defer parser
work, publish status bits, display service messages, and then return through
the scheduler/status aggregate.

Entry and loop state:

- `0xba48` is entered from the external-ready/service caller cluster. On
  entry it writes `0x7822da`, clears `0x780e09`, displays ROM string
  `0xb63b` (`01 EXT READY`) through wrapper `0x8c7a`, writes
  `$a200 = 0xff00`, and stores the final `0x36e4` aggregate result into
  `0x780e08`.
- `0xbb36` sets handshake latch `0x782302 = 1` only when the ROM enters the
  external-ready loop.
- `0xbb84` consumes `$fffee00b.7` as the live-loop condition.
- While the loop is live, helpers `0xbbb2`, `0xbc56`, `0xbc88`, `0xbcfe`,
  `0xbd84`, `0xbdae`, `0xc092`, and `0xc0ae` maintain register shadows,
  text/message buffering, deferred action, handshaking, and status-bit
  publication.
- Teardown runs through `0xc06e -> 0xc108 -> 0x19dd2 -> 0x36e4`. The
  scheduler return from `0x19dd2` is ignored at this caller; the final status
  byte written to `0x780e08` comes from the following `0x36e4` aggregate.

Service and error behavior:

- `0xc340` seeds message buffer `0x782312` from `01 EXT READY`.
- `0xbcfe` appends masked printable bytes from `$fffee011` into
  `0x782312`; carriage return terminates the buffer and displays it through
  `0x8c7a`.
- `0xc0ae` publishes `$fffee005.7` and `$fffee005.6` as status bits
  `0x780e2e.7` and `0x780e2e.6` through `0x9bee`.
- `0xc1c6` dispatches service/error conditions from status fields including
  `0x780e36 & 0x18`, `0x780e2e & 0xc0`, `0x780e39.3`, `0x780e39.4`,
  `0x780e31.7`, `0x780e31.6`, and pending-message flag `0x782301`.
- Retained-record commit/readback failure writes `0x780e39.3` through
  `0x571e -> 0x9bee(0x780e36, 0x00000008)`. When `0xc1c6` later consumes that
  bit, it reaches non-returning display helper `0x85c0`, which displays
  `68 SERVICE` from string `0xb45c` through wrapper `0x8c90`.
- Startup retained-record load has a separate service path:
  `0x5a16 -> 0x97e4 -> 0x56c2 -> 0x1284` reports `67 SERVICE` when no active
  retained-record marker is found.

Output effect:

- This loop does not allocate page roots, queue page objects, publish
  page/control records, or call render entry `0x1ef6a`.
- It can affect exact reproduction by preempting parser work, changing
  status/service latches, changing operator-panel messages, driving external
  registers, or entering non-returning service display.
- A byte-stream renderer that starts from canonical ready state and ignores
  board service loops can treat this as outside the page-image path. A
  board-level or protocol-faithful emulator must preserve the loop because it
  changes when later host bytes are admitted and what status/service state is
  visible.

State classification:

- Canonical status/output:
  final aggregate byte `0x780e08`, status longword `0x780e36..0x780e39`,
  `$a200`, `$fffee00d`, `$a801`, retained-record active marker state, and
  dirty flags `0x780eba..0x780ed8`.
- Derived/cache:
  shadow byte `0x7822eb`, last sampled `$fffee00b` byte `0x7822ec`,
  low-three-bit mirror `0x7828f9`, timestamp snapshots
  `0x78230a/0x78230e`, and retained commit/readback buffers.
- Parser/status scratch:
  message count `0x782300`, pending-message flag `0x782301`, message buffer
  `0x782312..0x782322`, last debounced `$8000.w` byte `0x7821aa`, and timer
  baseline `0x7821ac`.
- Firmware bookkeeping:
  handshake latch `0x782302`, service-poll latch `0x7822fd`,
  deferred-action latch `0x7822fe`, edge latch `0x7822ff`, sampled byte
  `0x7822fa`, scratch bytes `0x7821e7..0x7821ef`, and scheduler/status
  teardown state.
- Hardware/external:
  board-level identity of `$fffee00b`, `$fffee00d`, `$fffee00f`,
  `$fffee011`, `$fffee013`, `$fffee005`, `$fffee003`, `$fffee001`, `$a200`,
  `$a801`, and the physical retained-storage device.
- Unknown:
  no unresolved ROM-local page-object or render edge remains. Remaining
  boundaries are the physical identity/timing of the external register family,
  physical retained-storage failure conditions, and user-facing names for
  sibling service bits not yet tied to strings.

Evidence:

- Checked-in explanations:
  [external-ready-service.md](external-ready-service.md),
  [errors-and-status.md](errors-and-status.md),
  [io-interfaces.md](io-interfaces.md),
  `Worked Path: External Ready Service Preemption` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md), and
  `External Ready And Service Status Loop` in
  [semantic-state-model.md](semantic-state-model.md).
- Focused listings and extracts:
  `generated/disasm/ic30_ic13_external_ready_service_loop_00ba48.lst`,
  `generated/disasm/ic30_ic13_external_service_io_00bcd8.lst`,
  `generated/disasm/ic30_ic13_external_service_reset_00c06e.lst`,
  `generated/disasm/ic30_ic13_status_bit_helpers_009ba2.lst`,
  `generated/disasm/ic30_ic13_interface_status_aggregate_0036e4.lst`,
  `generated/disasm/ic30_ic13_default_env_record_maintenance_0056c2.lst`,
  `generated/analysis/ic30_ic13_strings.txt`, and
  `generated/analysis/ic30_ic13_long_reference_scan.md`.

## Minimal Direct-Control Walkthrough

This is the smallest top-level control/cursor spine. The control bytes and
cursor commands do not draw by themselves. They mutate line-termination,
cursor, margin, HMI/VMI, or pending-span state; later printable bytes consume
that state and create the page objects that render pixels.

Line-termination stream:

```text
ESC &k1G ! CR !
```

Cursor-placement stream:

```text
ESC &a2c+1R !
```

Parser and direct-control dispatch:

- All bytes enter through host source `0xa904`, parser wrapper `0xda9a`, and
  parser loop `0x11774`.
- `ESC &k1G` dispatches to handler `0xedf8`.
- `0xedf8` rewinds command-record cursor `0x78299e`, normalizes selector `1`,
  and writes line-termination byte `0x78318f = 0x80`.
- The first printable `!` reaches normal printable handler `0xd04a` and
  queues a compact text object through `0xd824 -> 0x12f2e -> 0x1387c`.
- CR byte `0x0d` is a normal mode-zero table entry and reaches handler
  `0xf02c`.
- `0xf02c` calls CR helper `0xf06e`, which copies left/default margin
  `0x782dd6` into horizontal cursor `0x782c8a`.
- `0xf02c` then calls span flush helper `0xf34a`.
- Because `0x78318f.7` is set, `0xf02c` also calls LF helper `0xf0b2`, which
  advances vertical cursor `0x782c8e` by VMI `0x783160`.
- The second printable `!` returns to `0xd04a` and consumes the post-CR/LF
  cursor position.

Cursor command dispatch:

- `ESC &a#C` dispatches to horizontal column handler `0xf39e`.
- Lowercase final `c` keeps parser mode `12` active, so chained relative row
  command `+1R` reaches vertical row handler `0xf560`.
- `0xf39e` converts column units through current HMI `0x78315c`, then commits
  through `0xf4ca`, which applies the relative flag, clamps against page
  width `0x782db8`, updates right-limit state, clears pending text, and
  refreshes active span state.
- `0xf560` converts row units through current VMI `0x783160`. Absolute row
  moves add top offset `0x782dce` plus the ROM fractional row bias; relative
  row moves add to the current vertical cursor.
- `0xf560` commits through `0xf6e2`, which ensures a page root, clears or
  flushes pending text state, clamps vertical bounds, and writes
  `0x782c8e`.
- The following printable `!` reaches `0xd04a` after those writes.

Page-object effects:

- `ESC &k#G`, CR, LF, HT, BS, and `ESC &a` cursor commands do not queue
  compact glyph objects directly.
- Their visible effect is the cursor and pending-span state consumed by later
  printable bytes or by FF publication.
- In `ESC &k1G!\r!`, handler sequence
  `0xedf8 -> 0xd04a -> 0xf02c -> 0xd04a` allocates one page root, reuses
  compact bucket `0`, and queues the second glyph at compact coordinate
  `0x3b00`.
- The LF sibling `ESC &k2G!\n!` writes mode byte `0x60`; LF handler `0xf08c`
  applies CR+LF before the second glyph and queues the same compact coordinate
  `0x3b00`.
- The HT/BS sibling `ESC &k0G HT BS !` routes through `0xedf8`, `0xf1cc`,
  `0xf2a8`, and `0xd04a`; HT advances x to `21`, BS backs up to `20`, and
  the glyph queues at compact coordinate `0x0a01`.
- `ESC &a2C!`, `ESC &a1R!`, and `ESC &a2c+1R!` route cursor handlers into
  following printable output at compact coordinates `0x0a02`, `0x1001`, and
  `0x1a02`.
- Cursor stack stream `ESC &f0S ESC &a2C ESC &f1S!` routes through
  `0xf75e`, `0xf39e`, and `0xf75e`; the pop restores the original cursor
  before the printable queues at compact coordinate `0x0001`.

Span-flush siblings:

- Cursor-changing handlers that call `0xf34a` can materialize pending span
  state before moving the cursor.
- `ESC &a6L!` moves `0x782c8a` from packed `10` to packed `108`; the flush
  path writes selector-`0x4000` segment-list object
  `00 00 00 00 40 00 00 01 32 00 03 00 00 10`.
- `0x126e2` re-arms span bounds to x `108`, and the following printable
  queues compact coordinate `0x0207`.
- `ESC &a1R!` proves the vertical-cursor sibling: handler `0xf560` flushes
  pending state, moves y to packed `95.1`, and the following printable queues
  compact coordinate `0xa001` in bucket `4`.
- Segment-list span objects render through `0x1f812`; landscape fixed-width
  siblings use render root `+0x20` and `0x1f756`.

Render path:

- Publication uses the ordinary current-root boundary through `0xff1e`.
- `0x1ed84` and `0x1edc6` bridge compact bucket, span, and context roots into
  render-record roots.
- The shifted compact glyphs render through `0x1ef6a -> 0x1efc2 -> 0x1effe`
  and the compact row-copy helpers.
- Span-flush objects bridge as selector-`0x4000` segment-list bucket objects
  and render through `0x1efc2 -> 0x1f812`.

State classification:

- Canonical:
  line-termination mode `0x78318f`, horizontal cursor `0x782c8a`, vertical
  cursor `0x782c8e`, left margin `0x782dd6`, right margin `0x782dda`, page
  width `0x782db8`, HMI `0x78315c`, VMI `0x783160`, current page root
  `0x78297a`, compact bucket objects, and selector-`0x4000` span objects.
- Derived/cache:
  compact coordinates such as `0x3b00`, `0x0a02`, `0x1a02`, `0xa001`, and
  `0x0001`, packed unit conversions, right-limit comparisons, span source
  bounds, bucket keys, and render-band fields.
- Parser scratch:
  parser mode `12` for lowercase-final chaining, command-record cursor
  `0x78299e`, six-byte command records, parsed relative-flag bit `0`, numeric
  parameter buffers, direct control byte `0x0d`, and resumed parser state for
  following printable bytes.
- Firmware bookkeeping:
  right-limit latch `0x782a57`, pending-width latch `0x782a58`, pending-text
  latch `0x782a6d`, span-flush enable `0x783184`, span re-arm fields
  `0x783186` / `0x783188`, allocation cursors, publication flag `0x782996`,
  scheduler cursors, and render-work progress words.
- Hardware/external:
  none for the ROM-local cursor-to-page-object contract beyond the physical
  source that supplied normalized bytes to `0xa904` and later engine timing.
- Unknown:
  no unresolved ROM-local middle edge remains for the documented
  `ESC &k1G!\r!`, `ESC &a2C!`, `ESC &a1R!`, `ESC &a2c+1R!`, HT/BS, or
  cursor-stack streams. Remaining work starts from variants that change
  compact object bytes, span object shape, bucket selection, bridge state, or
  ROM-derived rows.

Evidence:

- Checked-in explanations:
  `Worked Path: Mixed Direct Controls`, `Worked Path: Cursor And Margin
  Placement`, and `Worked Path: Text Span Flush And Fixed-Width Spans` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md),
  [direct-control-codes.md](direct-control-codes.md),
  [pcl-command-map.md](pcl-command-map.md),
  [page-record-storage.md](page-record-storage.md),
  [page-raster-imaging.md](page-raster-imaging.md),
  [font-context-metrics.md](font-context-metrics.md), and
  [semantic-state-model.md](semantic-state-model.md).
- Focused listings and extracts:
  `generated/disasm/ic30_ic13_control_code_handlers_00f02c.lst`,
  `generated/disasm/ic30_ic13_hmi_vmi_handlers_00ca8c.lst`,
  `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`,
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`,
  `generated/analysis/ic30_ic13_direct_control_code_flow.md`,
  `generated/analysis/ic30_ic13_printable_text_path.md`, and
  `generated/analysis/ic30_ic13_text_cursor_span_flow.md`.

## Minimal Page Layout Walkthrough

This is the smallest top-level layout-control spine. These command bytes
normally do not queue pixels immediately. They rewrite page, vertical-layout,
wrap, or perforation state; later printable/control bytes consume that state
to choose coordinates, suppress or recover a glyph, or publish a page.

Representative streams:

```text
ESC &l66P !
ESC &l3E !
ESC &l60F !
ESC &l1L !
ESC &s0C
ESC &s1C
```

Parser and command dispatch:

- Host bytes enter through `0xa904`, parser wrapper `0xda9a`, and parser loop
  `0x11774`.
- `ESC &l#P` dispatches to page-length handler `0xf9e8`.
- `ESC &l#C` and `ESC &l#D` dispatch to VMI/LPI handlers `0xcb00` and
  `0xc992`.
- `ESC &l#E` and `ESC &l#F` dispatch to top-margin/text-length handlers
  `0xece2` and `0xea9e`.
- `ESC &l#L` dispatches to perforation-skip handler `0xee64`.
- `ESC &s#C` dispatches to wrap-mode handler `0xedb0`.
- A following printable byte returns to `0xd04a`, queues compact text through
  `0xd824 -> 0x12f2e -> 0x1387c`, and later renders only after the ordinary
  `0xff1e -> 0x1ed84 -> 0x1edc6 -> 0x1ef6a` publication path.

Layout command behavior:

- `ESC &l66P` converts the parsed line count through current VMI `0x783160`,
  writes page extent `0x782dba`, selects the internal page code, recomputes
  page/text-bottom geometry, and refreshes the following printable cursor.
- `ESC &l0P` takes the default-page branch in the same handler. It can flush
  pending text, publish an existing root through `0xff1e`, mirror paper-source
  state to `0x780e8f`, signal `0x780e26`, and restore the default page code.
- `ESC &l#C` converts VMI in 1/48-inch units, writes accepted nonzero values
  to `0x783160`, and refreshes pending vertical cursor `0x782c8e`.
- `ESC &l#D` accepts the ROM LPI set, maps it to packed line advance
  `0x783160`, marks modified-layout byte `0x782ee1`, and refreshes pending
  vertical cursor `0x782c8e`.
- `ESC &l#E` scales top-margin lines through VMI, rejects zero-VMI and
  beyond-page positions, writes top offset `0x782dce`, restores default text
  length, and refreshes pending vertical cursor.
- `ESC &l#F` scales text length through VMI, rejects lengths beyond the page
  below the current top margin, writes text-bottom state `0x782dd2`, and uses
  selector `0` to restore the default text length.
- `ESC &l#L` writes perforation-skip byte `0x783191` only for selectors `0`
  and `1`.
- `ESC &s#C` writes wrap byte `0x783190` only for selectors `0` and `1`.
  Selector `0` enables wrap and selector `1` clears it.

Consumers and output effect:

- These layout handlers do not create glyph pixels directly in the cited
  streams.
- Printable prechecks `0xd28a` and `0xd6bc` consume wrap byte `0x783190`.
  With wrap disabled, horizontal overflow returns the reject value and the
  glyph is not queued. With wrap enabled, the precheck calls recovery helper
  `0xf054`, retries from recovered x `0`, and queues only if the retry fits.
- Vertical overflow helper `0xf36c` consumes vertical cursor `0x782c8e`,
  derived limit `0x782dc2`, and perforation byte `0x783191`. Enabled
  overflow with nonzero limit calls page-eject helper `0xf124`; below-limit,
  zero-limit, and disabled-skip cases stay on the no-eject path.
- Cursor movement, LF/FF, VFC, and absolute row handlers consume VMI
  `0x783160`, top offset `0x782dce`, text-bottom state `0x782dd2`, and
  derived limit `0x782dc2`.
- The `ESC &l66P !` path proves the page-length state is consumed by the
  following printable byte: `0xf9e8 -> 0xd04a` refreshes placement and queues
  the `!` compact object at coordinate `0x9001`.
- The `ESC &l1L !` path proves perforation state and the following printable
  share the same parser-to-page-record pipeline: `0xee64` writes `0x783191`,
  then `0xd04a` queues the compact object.

State classification:

- Canonical:
  page extent `0x782dba`, VMI `0x783160`, top offset `0x782dce`,
  text-bottom state `0x782dd2`, cursor x/y `0x782c8a` / `0x782c8e`,
  wrap byte `0x783190`, perforation byte `0x783191`, page code/default state,
  paper-source byte `0x782da6`, and output/control bytes `0x780e8f` /
  `0x780e26`.
- Derived/cache:
  limit `0x782dc2`, compact coordinates such as `0x9001`, geometry caches,
  VFC line caches, bucket keys, and render-band fields after publication.
- Parser scratch:
  parser mode and six-byte command records rooted at `0x78299e`, parsed
  numeric parameters, delayed command-family state for lowercase finals, and
  normalized host bytes from `0xa904`.
- Firmware bookkeeping:
  modified-layout byte `0x782ee1`, pending text latch, current-root
  publication/clear state, page-finalization counters, allocator cursors, and
  scheduler progress after later publication.
- Hardware/external:
  `0x780e8f` and `0x780e26` are ROM-visible output/control bytes in the
  `ESC &l0P` branch. Physical formatter/DC timing remains outside this
  ROM-local layout contract.
- Unknown:
  no unresolved ROM-local parser-to-handler or handler-to-following-printable
  edge remains for the cited streams. Remaining work starts from command
  variants that change geometry caches, overflow branches, page-object bytes,
  bridge state, or ROM-derived row construction.

Evidence:

- Checked-in explanations:
  `Worked Path: Page Length, Wrap, And Perforation Controls` and
  `Worked Path: Cursor And Margin Placement` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md),
  [direct-control-codes.md](direct-control-codes.md),
  [pcl-command-map.md](pcl-command-map.md),
  [page-raster-imaging.md](page-raster-imaging.md), and
  [semantic-state-model.md](semantic-state-model.md).
- Focused listings and extracts:
  `generated/disasm/ic30_ic13_page_length_handler_00f9e8.lst`,
  `generated/disasm/ic30_ic13_hmi_vmi_handlers_00ca8c.lst`,
  `generated/disasm/ic30_ic13_perforation_skip_handler_00ee64.lst`,
  `generated/disasm/ic30_ic13_wrap_mode_handler_00edb0.lst`,
  `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`,
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`,
  `generated/analysis/ic30_ic13_direct_control_code_flow.md`, and
  `generated/analysis/ic30_ic13_page_geometry_tables.md`.

## Minimal Page Geometry Walkthrough

This is the smallest top-level page-size and orientation spine. It covers the
geometry commands that rewrite page dimensions and placement state, and shows
how those fields are consumed later by printable placement, raster bounds,
rectangle clipping, publication, and rendering. These commands do not draw
pixels directly.

Representative streams:

```text
ESC &l1A
ESC &l1O
ESC &l1a1O
! ESC &l1A
! ESC &l1O
```

Parser and command dispatch:

- Host bytes enter through `0xa904`, parser wrapper `0xda9a`, and parser loop
  `0x11774`.
- `ESC &l#A` reaches page-size handler `0xfc74`.
- `ESC &l#O` reaches orientation handler `0x10220`.
- Chained `ESC &l1a1O` stays in the same `&l` parser family: lowercase
  page-size final `a` keeps the family active, then uppercase `O` terminates
  the chain through the orientation handler.
- If printable content already exists, the printable byte first reaches
  `0xd04a` and queues a compact object under current page root `0x78297a`
  before the geometry handler runs.

Page-size behavior:

- `0xfc74` maps PCL page-size parameters to internal page codes and writes
  code byte `0x782da2`. The documented mappings are
  `1 -> 6`, `2 -> 2`, `3 -> 5`, `26 -> 1`, `80 -> 0x88`, `81 -> 0x87`,
  `90 -> 0x89`, and `91 -> 0x8a`.
- The ROM table helpers `0x9d16`, `0x9d4e`, `0x9d86`, and `0x9dbe` mask the
  internal code with `0x7f` and index eleven word entries. The generated
  table report identifies the corresponding portrait/landscape logical
  widths and lengths.
- For letter `ESC &l1A`, the documented state after rebuild is internal code
  `6`, active size `3030 x 2025`, portrait margin/extent input `3150`, top
  offset `90`, printable extent `3090`, and half-page remainder `0x782dc0 =
  11`.
- PCL size `80` maps to internal code `0x88`, which masks to geometry-table
  index `8`.

Orientation behavior:

- `0x10220` accepts orientation values below `2`. If the requested value
  differs from orientation byte `0x782da3`, it publishes any queued current
  page, writes the new orientation, rebuilds page geometry, updates VMI/HMI
  related state, and reloads current font/metric state.
- Shared geometry helpers choose active extents from the table outputs:
  `0xf9ac` chooses portrait or landscape page length, `0xf87e` swaps
  `0x782db2` / `0x782db4` into active extents `0x782db6` / `0x782db8`, and
  `0x103ea` reloads orientation threshold values into
  `0x782daa..0x782db0`.
- For letter landscape `ESC &l1O`, the documented state is orientation `1`,
  active extents `2025 x 3030`, landscape margin `2175`, printable extent
  `2125`, top offset `100`, and threshold sequence
  `2175, 2550, 2480, 2550`.

Publication and later consumers:

- `! ESC &l1A` and `! ESC &l1O` publish the already queued compact text object
  before the new geometry takes effect. Page size uses the `0xfc74` /
  `0xf34a` / `0xff1e` edge; orientation uses the `0x10220` /
  `0xf34a` / `0xff1e` edge.
- The published pre-command root flows through the ordinary render path:
  `0xff1e -> 0x1ed84 -> 0x1edc6 -> 0x1eba4 -> 0x1ef6a`.
- Following printable placement consumes geometry fields through the text path
  `0xd04a -> 0xd824 -> 0x12f2e -> 0x1387c`.
- Raster-start and transfer paths consume active extents and orientation:
  `0x1075a` chooses raster origin from `0x782c8a` in portrait or
  `0x782c8e` in landscape, while transfer gates compare against active bounds
  derived from geometry fields.
- Rectangle source producer `0x10b80` consumes cursor, orientation
  `0x782da3`, and page extents `0x782db8/0x782db6` to clip or reject rules
  before it writes source record `0x782a88`.

Output effect:

- Isolated page-size or orientation commands update later placement state and
  do not queue page objects.
- When content is pending, page-size and orientation commands are page
  boundaries: the pending page is published under the old geometry, then the
  handler installs new geometry for following objects.
- Pixel provenance remains the ordinary page-object path. Geometry affects
  coordinates, clipping, bounds, and page-boundary ordering; it is not a
  renderer and does not supply row data by itself.

State classification:

- Canonical:
  page code `0x782da2`, orientation byte `0x782da3`, table outputs
  `0x782db2` / `0x782db4`, active extents `0x782db6` / `0x782db8`, page
  length/extent `0x782dba`, top offset `0x782dce`, text bottom
  `0x782dd2`, cursor `0x782c8a/0x782c8e`, and current page root
  `0x78297a`.
- Derived/cache:
  orientation-specific threshold sequence `0x782daa..0x782db0`, half-page
  remainder `0x782dc0`, printable extent, refreshed pending cursor state,
  compact bucket/key fields, raster byte limits, rectangle clipped source
  fields, and render-band caches after publication.
- Parser scratch:
  `&l` parser mode, six-byte command records rooted at `0x78299e`, parsed
  page-size/orientation parameters, and lowercase-chain state for
  `ESC &l1a1O`.
- Firmware bookkeeping:
  publication flag `0x782996`, page-change/status flags, pending text flush
  state, stream allocator cursors, and scheduler progress after publication.
- Hardware/external:
  none for the ROM-local geometry transformation. Physical engine timing after
  publication remains outside this page-geometry contract.
- Unknown:
  no unresolved ROM-local parser-to-geometry or geometry-to-consumer middle
  edge remains for the documented page-size, orientation, chained
  page-size/orientation, and pending-publication streams. Remaining geometry
  work starts from command combinations that expose different table indexes,
  page-length thresholds, downstream placement, raster bounds, rectangle
  clipping, bridge roots, or ROM-derived row construction.

Evidence:

- Checked-in explanations:
  [page-raster-imaging.md](page-raster-imaging.md),
  [publication-commands.md](publication-commands.md),
  [pcl-command-map.md](pcl-command-map.md),
  `Worked Path: Publication Commands To Rendered Page Records` and
  `Worked Path: Page Length, Wrap, And Perforation Controls` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md),
  and `Page Geometry And Direct Layout State` in
  [semantic-state-model.md](semantic-state-model.md).
- Focused listings and extracts:
  `generated/disasm/ic30_ic13_page_size_handler_00fc74.lst`,
  `generated/disasm/ic30_ic13_orientation_handler_010220.lst`,
  `generated/disasm/ic30_ic13_page_geometry_tables_009d16.lst`,
  `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`,
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`,
  `generated/analysis/ic30_ic13_page_geometry_tables.md`, and
  `generated/analysis/ic30_ic13_page_record_bridge.md`.

## Minimal Page Assembly Walkthrough

This is the smallest top-level page-object spine. It starts after parser
handlers have accepted commands and before publication. At this layer the ROM
does not maintain a full-page bitmap. It builds a current page/control root
with typed display-list objects, then later publishes and renders that root.

Representative mixed stream:

```text
! ESC *c12a5b0P ESC *t300R ESC *r0A ESC *b2W c3 3c
```

Current-root setup:

- Page-object producers call ensure-root helper `0x10084`.
- If current root pointer `0x78297a` is nonzero, `0x10084` reuses the root.
- On first allocation, `0x10084` creates a page/control root, marks root byte
  `+4 = 1`, seeds stream-link pointer `0x782a72 = root + 0x20`, calls
  initializer `0x10110`, clears transient byte `0x782990`, and zeroes the
  256 compact/raster bucket heads under root `+0x1c`.
- `0x10110` installs page geometry fields, status/header fields, list heads,
  and the selected current-font context slot at root `+0x2c`.

Shared stream allocation:

- Variable-size page objects are allocated by `0x1381c`.
- `0x1381c` owns stream bookkeeping `0x782a70`, `0x782a72`, and `0x782a76`.
  It reuses remaining bytes in the current stream chunk when possible, or
  links a fresh 0x100-byte chunk through the prior `0x782a72` target.
- The same stream allocator backs compact text, raster bucket objects,
  rectangle/rule nodes, and fixed-list nodes. Producer identity comes from the
  root field and object class, not from a separate heap.

Producer-to-root map:

- Printable text reaches `0xd04a -> 0x12f2e -> 0x1387c`.
  `0x1387c` writes compact bucket objects under root `+0x1c`, reusing a
  matching selector object while count `+6` is below capacity.
- Encoded raster rows reach delayed handler `0x105d0`, then
  `0x13070 -> 0x13250`. They write class-`0x80` bucket objects under root
  `+0x1c`; dense rows can split before the bucket chain is rendered.
- Rectangle/rule commands reach `0x10898 -> 0x13386 -> 0x133aa`. They write
  ordered rule-list nodes under root `+0x24`.
- Pending text spans reach `0x12714`. Portrait spans use
  `0x13520` / `0x1354a` / `0x135f0` to write class-`0x40` segment-list
  objects under root `+0x1c`; landscape spans use `0x136d2` to write
  fixed-list objects under root `+0x28`.

Bridge-facing object classes:

- Root `+0x1c` holds compact text, downloaded-glyph, segment-list, and
  encoded-raster bucket objects. Bridge `0x1edc6` later copies this root to
  render-record field `+0x18`.
- Root `+0x24` holds rectangle/rule list nodes. Bridge `0x1edc6` later copies
  and normalizes this list into render-record field `+0x1c`.
- Root `+0x28` holds fixed-list nodes. Bridge `0x1edc6` later copies and
  normalizes this list into render-record field `+0x20`.
- Root `+0x2c..+0x68` holds 16 font/resource context slots. Bridge `0x1edc6`
  later copies them to render-record `+0x24..+0x60` for compact-glyph and
  downloaded-glyph render helpers.

Output effect:

- Page assembly has no pixels by itself. It determines which objects exist,
  their bucket/list order, and which render roots will receive them.
- The mixed text/rule/raster stream composes one current page root containing
  a compact text object, a selector-7 rule object, and a mode-0 raster object.
  Publication and render later consume those root fields through the ordinary
  `0xff1e -> 0x1ed84 -> 0x1edc6 -> 0x1ef6a` path.
- Allocation failure is visible as preserved prior page state. If `0x1381c`
  fails inside `0x133aa`, root `+0x24` is not modified. If it fails inside
  `0x136d2`, root `+0x28` and existing fixed nodes are preserved.

State classification:

- Canonical:
  current root pointer `0x78297a`, root state byte `+4`, root bucket/list
  fields `+0x1c`, `+0x24`, `+0x28`, context slots `+0x2c..+0x68`, and typed
  object fields such as next pointer `+0`, selector/class `+4`, count/key
  `+6`, and payload bytes.
- Derived/cache:
  producer keys `0x782a7c..0x782a7e`, compact coordinates, bucket indexes,
  object capacity decisions, bridge destination offsets, and render-band
  fields derived later by `0x1ef86`.
- Parser scratch:
  none newly owned by page assembly. Parser records and delayed-payload
  cursors are owned by their command-family handlers before the producer calls
  into `0x10084`, `0x1387c`, `0x133aa`, `0x136d2`, or `0x13070`.
- Firmware bookkeeping:
  stream allocator fields `0x782a70`, `0x782a72`, `0x782a76`, first-root wait
  latches `0x782c72` / `0x782c73`, transient byte `0x782990`, allocator
  failure returns, and later publication flag `0x782996`.
- Hardware/external:
  none for the ROM-local page-assembly contract. Hardware timing starts after
  publication when scheduler/device wait paths decide when render work runs.
- Unknown:
  no unknown page-root field is assigned in the documented allocator cluster.
  Remaining work starts from byte streams that change root topology, allocator
  failure timing, object layout, bridge fields, scheduler-selected roots, or
  ROM-derived row construction.

Evidence:

- Checked-in explanations:
  [page-record-storage.md](page-record-storage.md),
  [page-raster-imaging.md](page-raster-imaging.md),
  [publication-commands.md](publication-commands.md),
  [active-render-scheduler.md](active-render-scheduler.md), and
  `Shared Page-Record Storage And Allocator` in
  [semantic-state-model.md](semantic-state-model.md).
- Focused listings and extracts:
  `generated/disasm/ic30_ic13_page_root_allocate_010084.lst`,
  `generated/disasm/ic30_ic13_display_list_helpers_013386.lst`,
  `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`,
  `generated/disasm/ic30_ic13_raster_object_queue_013070.lst`,
  `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`,
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`,
  `generated/analysis/ic30_ic13_page_root_allocation.md`,
  `generated/analysis/ic30_ic13_compact_bucket_allocator.md`, and
  `generated/analysis/ic30_ic13_page_record_bridge.md`.

## Minimal Publication Walkthrough

This is the smallest top-level page-boundary spine. Publication commands do
not create pixels from their own command bytes. They preserve already queued
page objects, copy them into a published page/control record through
`0xff1e`, clear or mutate current-page state, and let the scheduler/render
bridge consume the published record later.

FF stream:

```text
ESC &k2G ! FF
```

Reset stream:

```text
! ESC E
```

Parser and command dispatch:

- Host bytes enter through `0xa904`, parser wrapper `0xda9a`, and parser loop
  `0x11774`.
- `ESC &k2G` reaches line-termination handler `0xedf8`, which writes
  line-termination mode `0x78318f`.
- Printable `!` reaches `0xd04a`, ensures current page root `0x78297a`
  through `0x10084`, and queues a compact text object through
  `0x12f2e -> 0x1387c`.
- FF byte `0x0c` is a normal-table direct control and reaches handler
  `0xf0f0`.
- `ESC E` reaches software-reset handler `0xcc52`.

Current page before publication:

- The queued compact object is under current page-root bucket array `+0x1c`.
- The context slot at page-root `+0x2c` is preserved as `0x440946b4` in the
  documented FF/reset streams.
- The compact bucket object published by the FF and reset streams is:

```text
00 00 00 00 00 00 00 01 20 00 01
```

Publication behavior:

- FF handler `0xf0f0` applies line-termination side effects, flushes pending
  text, finalizes the valid current root through `0xff1e`, marks page eject
  with pending text byte `0xff`, and clears the current root.
- Reset handler `0xcc52` calls `0xcc70`, which flushes pending text, calls
  `0xff1e` when a current page root exists, waits through `0x9ac2`, clears
  orientation byte `0x782da3`, rebuilds the default environment through
  `0xcda2`, refreshes HMI through `0xcbd4`, and clears parser/data-chain
  state through `0xe146`.
- Missing-root `ESC E` is a no-publication boundary: it clears reset state
  without inventing a page object or published record.
- `0xff1e` writes page/control pool state byte `+4 = 2`, preserves the bucket
  root and context slots, writes published pool pointer `0x780ea6`, sets
  publication flag `0x782996`, and clears current root pointer `0x78297a`.

Publication-command matrix:

- `ESC E` publishes a valid current root before environment/parser rebuild;
  no current root means no publication.
- `FF` publishes the current root after line-termination side effects. Its
  visible pixels are the objects queued before FF.
- `ESC &l#A` page-size handler `0xfc74` publishes queued objects before
  writing the new page code and geometry.
- `ESC &l#O` orientation handler `0x10220` publishes queued objects before
  changing orientation byte `0x782da3` and active extents.
- `ESC &l#H` paper-source handler `0xef62` flushes and publishes queued text
  before writing paper-source/output state.
- `ESC &l#X` copies handler `0xeef0` stores copy count `0x782da4`; the later
  FF publication copies that value into published pool-header word `+0x0c`.

Bridge, scheduling, and pixels:

- After `0xff1e`, parser work is finished for the page. The published record
  becomes scheduler input.
- Scheduler selection promotes a page/control pool record into active source
  pointer `0x780eae`.
- `0x1ed84` copies active published-record header fields into a render work
  record and calls `0x1edc6`.
- `0x1edc6` copies source bucket root `+0x1c` to render `+0x18`, rule-list
  root `+0x24` to render `+0x1c`, fixed-list root `+0x28` to render `+0x20`,
  and context slots `+0x2c..+0x68` to render `+0x24..+0x60`.
- Active scheduler loop `0x1eba4..0x1ecd2` calls `0x1ef6a` when a band has
  enough capacity to render.
- `0x1ef6a` dispatches this stream's compact object through
  `0x1ef86 -> 0x1efc2 -> 0x1effe`, using the context copied by `0x1edc6`.

State classification:

- Canonical:
  current page root `0x78297a`, compact bucket object, page-root context slot,
  published page/control record, published pool pointer `0x780ea6`, active
  source pointer `0x780eae`, and render-record bucket/context roots.
- Derived/cache:
  compact bucket/key fields, stream allocator fields `0x782a70`,
  `0x782a72`, and `0x782a76`, copied pool-header values, render-band caches
  `0x783a20`, `0x783a22`, and `0x783a28`, and same-geometry scheduler fields.
- Parser scratch:
  parser modes and six-byte command records for `ESC &k2G`, `ESC E`,
  publication commands, unmatched printable byte `0x21`, and direct control
  byte `0x0c`.
- Firmware bookkeeping:
  line-termination mode `0x78318f`, publication flag `0x782996`, page-root
  clear state, pending text byte `0xff`, reset rebuild state from `0xcc70` /
  `0xcda2` / `0xe146`, copy count `0x782da4`, paper-source state
  `0x782da6`, and scheduler progress words.
- Hardware/external:
  paper-source output/control bytes `0x780e8f` and `0x780e26`, plus physical
  formatter/DC timing after the ROM-local published-record handoff.
- Unknown:
  no unresolved ROM-local parser-to-publication, publication-to-bridge, or
  bridge-to-render middle edge remains for the documented FF/reset/page-control
  streams. Remaining uncertainty is limited to variants that change pool-header
  fields, source-record selection, bridge values, or ROM-derived rows.

Evidence:

- Checked-in explanations:
  `Worked Path: Reset And Default Environment`, `Worked Path: FF
  Publication`, `Worked Path: Publication Commands To Rendered Page Records`,
  and `Worked Path: Published Record To Active Bands` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md),
  [publication-commands.md](publication-commands.md),
  [reset-default-environment.md](reset-default-environment.md),
  [page-record-storage.md](page-record-storage.md),
  [active-render-scheduler.md](active-render-scheduler.md), and
  [semantic-state-model.md](semantic-state-model.md).
- Focused listings and extracts:
  `generated/disasm/ic30_ic13_esc_e_reset_00cc52.lst`,
  `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`,
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`,
  `generated/disasm/ic30_ic13_active_render_scheduler_01eb2a.lst`,
  `generated/disasm/ic30_ic13_page_size_handler_00fc74.lst`,
  `generated/disasm/ic30_ic13_orientation_handler_010220.lst`,
  `generated/disasm/ic30_ic13_paper_source_handler_00ef62.lst`,
  `generated/disasm/ic30_ic13_copies_handler_00eef0.lst`,
  `generated/analysis/ic30_ic13_page_root_finalization.md`, and
  `generated/analysis/ic30_ic13_esc_e_reset_flow.md`.

## Minimal Paper Source And Copies Walkthrough

This is the smallest top-level path for the two `ESC &l` page-environment
commands whose visible effect is mediated by publication rather than direct
pixel drawing. `ESC &l#H` publishes already queued content before changing paper
source/output state. `ESC &l#X` stores a copy count and relies on a later
publication command, normally FF, to place that count in the published
page/control header.

Representative streams:

```text
! ESC &l2H
! ESC &l2X FF
```

Parser and dispatch:

- Host bytes enter through `0xa904`, parser wrapper `0xda9a`, and parser loop
  `0x11774`.
- Printable `!` reaches `0xd04a`, ensures current root `0x78297a` through
  `0x10084`, and queues a compact text object through `0x12f2e -> 0x1387c`.
- `ESC &l2H` reaches paper-source handler `0xef62`.
- `ESC &l2X` reaches copies handler `0xeef0`; the following FF byte `0x0c`
  reaches handler `0xf0f0`.

Paper-source command path:

- Handler `0xef62` reads current paper-source byte `0x782da6`, rewinds the
  parser record by subtracting six from `0x78299e`, reads parsed word `+2`, and
  normalizes it to an absolute selector.
- Before changing paper-source state, it flushes pending text through `0xf34a`,
  publishes the current page root through `0xff1e`, and refreshes cursor state
  through `0xf8fc`.
- The selector table at `0xef3a` maps selector `0` to `0xefae`, selector `1` to
  `0xefb6`, selector `2` to `0xefe8`, selector `3` to `0xeff0`, and other
  selectors to `0xeff8`.
- Selector `2` writes selected value `0x80` through `0xefe8`, reaches the common
  output path at `0xefc0`, and then writes paper-source byte
  `0x782da6 = 0x80` at `0xf010`.
- When the output path accepts the selection, `0xefce` mirrors the selected byte
  to `0x780e8f` and `0xefd4..0xefe4` signals bit `0` through control word
  `0x780e26`. The handler also sets pending refresh byte `0x782998 = 1` at
  `0xf01c`.

Copies command path:

- Handler `0xeef0` rewinds the parser record by subtracting six from
  `0x78299e`, reads parsed word `+2`, and normalizes it to an absolute count.
- `0xef16..0xef26` clamps values above `99` by writing `0x782da4 = 99`.
- `0xef28..0xef2c` ignores zero and otherwise stores the normalized count in
  `0x782da4`.
- `0xeef0` does not publish a page by itself. In the representative stream,
  following FF handler `0xf0f0` publishes the queued page through `0xff1e`,
  which copies copy count `0x782da4 = 2` into published pool-header word
  `+0x0c`.

Output and page-image effect:

- `ESC &l2H` does not create a paper-source pixel object. Its pixel output comes
  from the compact text object queued before the command, then published by the
  command's `0xf34a -> 0xff1e` path.
- `ESC &l2X` does not create a pixel object or publish immediately. Its
  ROM-visible page effect is the stored copy count consumed by later
  publication.
- The rendered pixels for both representative streams use the ordinary
  publication and render path:
  `0xff1e -> 0x1ed84 -> 0x1edc6 -> 0x1eba4 -> 0x1ef6a`. The command-specific
  effects are page/control header fields and paper-source output state, not a
  separate renderer.

State classification:

- Canonical:
  current page root `0x78297a`, compact text object, published page/control
  record, copy count `0x782da4`, paper-source byte `0x782da6`, published
  pool-header word `+0x0c`, paper-source output byte `0x780e8f`, and output
  control word `0x780e26`.
- Derived/cache:
  normalized selector/count values, selected paper-source byte `0x80`, copied
  pool-header fields, and render-record roots after `0x1ed84` / `0x1edc6`.
- Parser scratch:
  six-byte `ESC &l2H` and `ESC &l2X` command records, parser record pointer
  `0x78299e`, and direct FF control byte.
- Firmware bookkeeping:
  pending text flush state, publication flag `0x782996`, pending refresh byte
  `0x782998`, stream allocator cursors, cursor refresh state from `0xf8fc`, and
  scheduler progress words.
- Hardware/external:
  the physical paper-source/output mechanism behind software-visible bytes
  `0x780e8f` and `0x780e26`, and any physical copy-count actuation after the
  published page/control record leaves the ROM-local model.
- Unknown:
  no unresolved ROM-local parser, field-write, publication, or render middle
  edge remains for the documented selector-`2` and copy-count-`2` streams.
  Remaining variants start only from other paper-source selectors, zero/negative
  or high copy values, other published header fields, or physical mechanism
  behavior beyond the ROM-visible output/control bytes.

Evidence:

- Checked-in explanations:
  [publication-commands.md](publication-commands.md),
  `ESC &l#H` and `ESC &l#X` in
  [pcl-command-map.md](pcl-command-map.md),
  `Worked Path: Publication Commands To Rendered Page Records` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md), and
  `Publication Commands To Rendered Page Records` in
  [semantic-state-model.md](semantic-state-model.md).
- Focused listings:
  `generated/disasm/ic30_ic13_paper_source_handler_00ef62.lst`,
  `generated/disasm/ic30_ic13_copies_handler_00eef0.lst`,
  `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`, and
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`.
- Supporting fixtures:
  `mixed printable/paper-source page-record stream publishes queued text`,
  `mixed printable/copies/FF stream publishes copy count`,
  `addressed paper-source and copies publications render page records`,
  `host-fetched FF geometry and paper-source publications preserve 0xff1e pool
  header`, `host-fetched copies publication preserves 0xeef0 pool header word`,
  and `0xeef0 ESC &l#X stores absolute clamped copy count`.

## Minimal Render Scheduler Walkthrough

This is the smallest top-level spine from a published page/control record to
active band rendering. It starts after `0xff1e` publication and before object
render dispatch. Parser records, command parameters, and delayed payload
cursors are no longer direct inputs here; the scheduler consumes published
page/control records and render work records.

Representative input:

```text
any stream that reaches `0xff1e`, such as `! FF` or the mixed text/rule/raster
stream in the render-dispatch walkthrough below
```

Source record selection:

- `0xff1e` writes the source root longword to protected published pool-head
  pointer `0x780ea6`, sets publication flag `0x782996`, and clears current
  root pointer `0x78297a`.
- Pool initialization `0x3144..0x3162` seeds `0x780ea6`, scheduler cursor
  `0x780eaa`, active source `0x780eae`, and release cursor `0x780eb2` to the
  pool base.
- Candidate selection `0x7ec6..0x7f90` promotes a selectable candidate from
  `0x780e6e[]` into `0x780eaa` and `0x780eb2`.
- Cursor path `0x7722..0x779a` advances or releases scheduler cursors while
  protecting `0x780ea6`.
- Active scheduler entry `0x1eb32..0x1eb50` copies selected cursor
  `0x780eaa` into active source pointer `0x780eae`.

Render work selection and bridge:

- Startup `0x2feb6` initializes two-work-record selector bytes `0x7820bc`
  and `0x7820c0`, then clears paired work-record header words.
- `0x1ecd6..0x1ed76` alternates render work records `0x7820c4` and
  `0x782128`, writes active render pointer `0x783a18`, initializes geometry
  through `0x1ee9e` when required, or reuses same-geometry fields through
  helper `0x33238`.
- `0x1ed84` copies active source header fields from `0x780eae` into the
  selected render work record and calls `0x1edc6`.
- `0x1edc6` copies source bucket root `+0x1c` to render root `+0x18`, source
  rule-list root `+0x24` to render root `+0x1c`, source fixed-list root
  `+0x28` to render root `+0x20`, and context slots `+0x2c..+0x68` to render
  slots `+0x24..+0x60`.

Active band loop:

- Active loop `0x1eba4..0x1ecd2` reads active render pointer `0x783a18`,
  selector bytes `0x7820bc` / `0x7820c0`, and work-record fields `+0x06`,
  `+0x0c`, `+0x0e`, `+0x10`, and `+0x16`.
- Cleanup branches call `0x1ef38`, clear active-render flag `0x780ea4`, and
  signal wait object `0x780182` when `0x780ea5 == 1` or active work
  `+0x0c < +0x10`.
- The throttle branch clears `+0x0e`, signals `0x780182`, and yields through
  `0x10d8(2)` when `+0x0e > 0x28`.
- The capacity branch computes available capacity from active and paired
  remaining rows. If capacity is less than `9`, it clears `+0x0e`, signals
  `0x780182`, and waits through `0x10d0(2)`.
- The render branch calls `0x1ef6a`, then increments active band word
  `+0x10` and throttle word `+0x0e`.
- `0x1ef86` derives per-band caches `0x783a20`, `0x783a22`, `0x783a28`, and
  stride `0x783a1c` before object dispatch starts.

Output effect:

- The scheduler does not create page objects or pixels from host bytes. It
  chooses the active source record, chooses the render work record, copies
  roots into that record, and decides which band words reach `0x1ef6a`.
- ROM-local pixel provenance begins when `0x1ef6a` dispatches render roots in
  fixed order. The scheduler evidence establishes the address and field path
  that gets published objects to those dispatch calls; it does not depend on
  comparing rendered rows against an external image.
- Physical formatter/DC timing can wake, stall, or pace the scheduler through
  wait-object and MMIO-facing state, but that timing does not add another
  parser-to-page-object or page-object-to-render-root transformation in this
  ROM-local model.

State classification:

- Canonical:
  protected published pool head `0x780ea6`, scheduler cursor `0x780eaa`,
  active source pointer `0x780eae`, release cursor `0x780eb2`, active render
  pointer `0x783a18`, render work records `0x7820c4` / `0x782128`, render
  roots `+0x18`, `+0x1c`, `+0x20`, context slots `+0x24..+0x60`, and active
  band word `+0x10`.
- Derived/cache:
  render-band rows `0x783a20`, remainder `0x783a22`, destination base
  `0x783a28`, stride `0x783a1c`, same-geometry destination word `+8`, and
  candidate-slot ordering in `0x780e6e[]`.
- Parser scratch:
  none. Parser and command-family state has already been consumed by
  page-record producers before `0xff1e`.
- Firmware bookkeeping:
  selector bytes `0x7820bc` / `0x7820c0`, active flags `0x780ea4` /
  `0x780ea5`, throttle word `+0x0e`, wait object `0x780182`, timer/status
  latches, scheduler trap state, and pool-record state byte `+4`.
- Hardware/external:
  MMIO-facing fields and strobes around `$8000`, `$8a01`, `$a200`, `$a400`,
  `$a801`, and `0xffff2000`; exact board-signal names and physical event
  timing are outside the ROM-local documentation boundary.
- Unknown:
  no unresolved ROM-local scheduler middle edge remains for the documented
  source-selection, work-record alternation, bridge, and active-band branches.
  Remaining uncertainty is hardware/MMIO timing and byte streams that create
  different source records or object continuation fields.

Evidence:

- Checked-in explanations:
  [active-render-scheduler.md](active-render-scheduler.md),
  `Worked Path: Published Record To Active Bands` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md),
  `Published Record To Active Render Scheduler` in
  [semantic-state-model.md](semantic-state-model.md),
  [page-record-storage.md](page-record-storage.md), and
  [page-raster-imaging.md](page-raster-imaging.md).
- Focused listings and extracts:
  `generated/disasm/ic30_ic13_active_render_scheduler_01eb2a.lst`,
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`,
  `generated/disasm/ic30_ic13_bitmap_state_setup_01ee9e.lst`,
  `generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`,
  `generated/disasm/ic30_ic13_page_pool_init_003100.lst`,
  `generated/disasm/ic30_ic13_page_pool_candidate_select_007ec6.lst`,
  `generated/disasm/ic30_ic13_page_pool_cursor_007612.lst`,
  `generated/disasm/ic30_ic13_startup_render_work_init_02feb6.lst`,
  `generated/disasm/ic30_ic13_active_pool_engine_gate_002038.lst`,
  `generated/disasm/ic30_ic13_engine_copy_pass_0022f4.lst`,
  `generated/analysis/ic30_ic13_page_record_bridge.md`, and
  `generated/analysis/ic30_ic13_render_path_references.md`.

## Minimal Render Dispatch Walkthrough

This is the smallest top-level renderer spine after publication. It starts
after parser commands and page-object producers have already materialized
objects, `0xff1e` has published a page/control record, and `0x1ed84` /
`0x1edc6` have copied page roots into a render work record. At this layer,
parser records and payload cursors are no longer inputs; render roots and
object bytes are.

Representative mixed stream:

```text
! ESC *c12a5b0P ESC *t300R ESC *r0A ESC *b2W c3 3c FF
```

The stream queues compact text, a selector-7 rectangle rule, and a mode-0
encoded raster object under one page root. FF publishes that root, then the
render path composes the bucket and rule roots in fixed ROM order.

Render-record inputs:

- `0xff1e` has already copied the current page root into a published
  page/control record and cleared `0x78297a`.
- Scheduler selection promotes a page/control pool record into active source
  pointer `0x780eae`.
- `0x1ed84` copies active source header fields into the selected render work
  record and calls `0x1edc6`.
- `0x1edc6` copies source bucket root `+0x1c` to render root `+0x18`,
  source rule-list root `+0x24` to render root `+0x1c`, source fixed-list
  root `+0x28` to render root `+0x20`, and context slots `+0x2c..+0x68` to
  render slots `+0x24..+0x60`.
- Active render pointer `0x783a18` selects the render work record consumed by
  `0x1ef6a`.

Scheduler and render entry:

- Active loop `0x1eba4..0x1ecd2` reads active and paired work-record fields
  `+0x06`, `+0x0c`, `+0x0e`, `+0x10`, and `+0x16`.
- If capacity is sufficient, it calls `0x1ef6a`, then increments active band
  word `+0x10` and throttle word `+0x0e`.
- If cleanup, throttle, or capacity-wait predicates fire, the loop updates
  wait-object and scheduler state without calling `0x1ef6a`.
- `0x1ef6a` uses fixed call order:

```text
0x1ef86 -> 0x1efc2 -> 0x1f446 -> 0x1f756
```

- `0x1ef86` computes current-band caches.
- `0x1efc2` walks bucket-chain objects from render root `+0x18`.
- `0x1f446` walks rule-list objects from render root `+0x1c`.
- `0x1f756` walks fixed-list objects from render root `+0x20`.

Bucket, rule, and fixed dispatch:

- Bucket object byte `+0x04` in range `0x00..0x3f` enters compact dispatch
  `0x1effe`. Bits `0x10` and `0x20` select short compact `0x1f034`, wide
  compact `0x1f0d2`, segmented compact `0x1f1f0`, or segmented-wide compact
  `0x1f264` through table `0x1f024`.
- Bucket object byte `+0x04` in range `0x40..0x7f` enters segment-list
  renderer `0x1f812 -> 0x1f862`.
- Bucket object byte `+0x04` in range `0x80..0xff` enters encoded-raster
  renderer `0x1f88e`. Object byte `+0x05 & 3` selects literal mode `0`,
  byte-expansion mode `1`, byte-pair expansion mode `2`, or cascaded
  expansion mode `3`.
- Rule-list dispatcher `0x1f446` sends selector `object[5] & 0x0f == 7` to
  solid writer `0x1f596`; selectors `0..6` and `8..13` reach patterned writer
  `0x1f4e0` through table `0x1f4a0`.
- Fixed-list dispatcher `0x1f756` runs on five-band boundaries, consumes
  render root `+0x20`, selects pattern longwords from table `0x308de`, and
  writes rows through `0x1f7b0` / `0x1f626`.

Destination and pixel writes:

- Destination helper `0x1f626` computes destination pointer `A1` from packed
  object coordinates, band state `0x783a20`, destination base `0x783a28`,
  offset table `0x7839f8..`, stride `0x783a1c`, and fallback base
  `0x7810b4`.
- Compact glyph helpers resolve the render context copied at
  `+0x24..+0x60`; object byte `+0x05` low nibble selects the slot, and
  `0x1f008` writes active context cache `0x783a2c` before `0x1f354` resolves
  glyph bitmap pointers, span width, and row count.
- Compact row-copy tables `0x1f08e` and `0x1f1ac` select unrolled writers for
  byte widths `1..16`; wide compact modes use `0x2f27c` for full 16-byte
  chunks and the remainder table for trailing bytes.
- Segment-list renderer `0x1f812 -> 0x1f862` consumes six-byte entries and
  writes full-mask words plus a trailing mask from table `0x308f2`.
- Encoded raster renderer `0x1f88e` expands object payload bytes `+0x0a..`
  according to the selected mode table.
- The shared pixel operation is direct destination storage in ROM call order.
  The documented helpers do not apply an implicit OR/XOR/AND blend against
  existing destination words. Later stores can overwrite earlier stores.

Mixed-page composition:

- In the representative mixed stream, the published bucket root contains the
  compact text object and the mode-0 raster object. The published rule root
  contains the selector-7 rectangle object.
- `0x1efc2` dispatches the mode-0 raster object to `0x1f88e` and the compact
  text object to `0x1effe`.
- `0x1f446` then renders the selector-7 rule through solid helper `0x1f596`.
- The visible result is order-dependent composition of queued objects, not
  immediate drawing by `ESC *c`, `ESC *b`, or FF command bytes.
- Rule and fixed-list helpers mutate continuation fields such as rule `+0x0c`
  and fixed-list `+0x0a`, so later render bands resume the same object rather
  than reparsing the host stream.

State classification:

- Canonical:
  render roots `+0x18`, `+0x1c`, and `+0x20`, render context slots
  `+0x24..+0x60`, bucket object fields `+0x04`, `+0x05`, `+0x06`, `+0x08`,
  payload `+0x0a..`, rule-list fields `+0x05`, `+0x06`, `+0x08`, `+0x0a`,
  `+0x0c`, and fixed-list fields `+0x04..+0x0d`.
- Derived/cache:
  active render pointer `0x783a18`, band split count `0x783a20`, band
  remainder `0x783a22`, destination base `0x783a28`, stride `0x783a1c`,
  offset table `0x7839f8..`, compact context cache `0x783a2c`, wide-mode
  caches `0x783a40..0x783a48`, and fallback base `0x7810b4 + D2`.
- Parser scratch:
  none at this layer. Parser records, delayed payload state, and payload
  source positions have already become page-record objects.
- Firmware bookkeeping:
  render continuation fields, object-chain next pointers, compact row-copy
  phase `0x783a46`, active-band progress words, active flags
  `0x780ea4/0x780ea5`, and wait-object state.
- Hardware/external:
  physical consumption of rendered band buffers by the formatter/DC engine is
  outside this ROM-local pixel-composition contract.
- Unknown:
  no unresolved shared render-dispatch edge remains for the documented compact,
  segment-list, encoded-raster, rule-list, or fixed-list object classes.
  Remaining work starts from byte streams that create different object fields,
  selected contexts, helper targets, continuation state, fallback splits, or
  ROM-derived rows.

Evidence:

- Checked-in explanations:
  `Worked Path: Published Record To Active Bands`, `Worked Path: Render
  Dispatch And Pixel Composition`, and `Worked Path: Mixed Text/Rule/Raster
  Page Record` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md),
  [page-raster-imaging.md](page-raster-imaging.md),
  [active-render-scheduler.md](active-render-scheduler.md),
  [page-record-storage.md](page-record-storage.md),
  [raster-graphics.md](raster-graphics.md),
  [rectangle-graphics.md](rectangle-graphics.md), and
  [semantic-state-model.md](semantic-state-model.md).
- Focused listings and extracts:
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`,
  `generated/disasm/ic30_ic13_bitmap_state_setup_01ee9e.lst`,
  `generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`,
  `generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst`,
  `generated/disasm/ic30_ic13_bitmap_row_copy_tables_01fa5c.lst`,
  `generated/analysis/ic30_ic13_page_record_bridge.md`,
  `generated/analysis/ic30_ic13_render_path_references.md`, and
  `generated/analysis/ic30_ic13_render_dispatch_tables.md`.

## Minimal Font Selection Walkthrough

This is the smallest top-level font-selection spine that changes later text
pixels. The font-selection bytes do not draw. They write primary or secondary
font request state, select a concrete ROM resource, rebuild the selected
host-byte-to-glyph map, and install that context so later printable bytes can
create different compact text objects.

Primary input stream:

```text
ESC (s0p10h12v0s0b3T ! !
```

Secondary input stream:

```text
ESC )s0p16h8v0s0b0T SO ! !
```

Parser and request-field dispatch:

- Both streams enter through `0xa904`, parser wrapper `0xda9a`, and parser
  loop `0x11774`.
- `ESC (` creates the primary setup record through `0x1201e`; `ESC )`
  creates the secondary setup record through `0x12008`.
- Parser modes advance `0 -> 1 -> 4 -> 13` while the `s...T` attribute
  sequence accumulates. Lowercase finals stay in mode `13`; uppercase final
  `T` returns to parser mode `0`.
- Lowercase finals dispatch to spacing `p` handler `0xc930`, pitch `h`
  handler `0xc89c`, point-size `v` handler `0xc6ec`, style `s` handler
  `0xc780`, and stroke `b` handler `0xc840`.
- Uppercase final `T` reaches wrapper `0x1205a`, which calls typeface writer
  `0xc7e0` and common refresh entry `0xc580`.

Font selection and map rebuild:

- The primary stream decodes to spacing `0`, pitch `0x03e8`, height
  `0x04b0`, style `0`, stroke `0`, and typeface `3`.
- Those request fields are stored in the primary request block around
  `0x782eec..0x782ef2`; dirty flags `0x782f2c` / `0x782f2d` mark refresh
  work before `0xc580`.
- `0xc580` calls `0x13eb8(0)` for primary slot `0`. The documented primary
  path runs
  `0x148f8 -> 0x1569c -> 0x156de -> 0x153c6 -> 0x1519a -> 0x147b2 ->
  0x14758 -> 0x14398 -> 0x144d2 -> 0x14c64`.
- Symbol, pitch, height, and stroke filtering select slot `0x782354`, record
  `0x00004c`, and context longword `0xc008004c`.
- `0x144d2` writes primary current-font context record `0x782ee6`.
- `0x14c64` rebuilds primary map `0x782f32`.
- The secondary stream follows the same selection family for slot `1`;
  nearest-pitch selection chooses slot `0x782350`, record `0x02e122`, and
  context longword `0xc00ae122`.
- `0x144d2` writes secondary current-font context record `0x782ef6`, and
  `0x14c64` rebuilds secondary map `0x783032`.
- SO byte `0x0e` later reaches handler `0xc6b8`, selecting secondary text
  slot `1`; SI byte `0x0f` reaches sibling `0xc68a`, selecting primary slot
  `0`.

Printable consumption and page objects:

- The primary stream's two printable `!` bytes route through handler
  `0xd04a` after selection.
- Source helper `0x1393a` reads selected slot `0`, context `0xc008004c`, and
  map `0x782f32`; host byte `0x21` maps to glyph `0x00`.
- The selected built-in record supplies HMI from byte `+0x21 = 0` and
  longword `+0x24 = 0x00780000`, producing packed advance `30`.
- `0xd04a -> 0xd824 -> 0x12f2e -> 0x1387c` queues this compact object:

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

Publication, bridge, and pixels:

- Publication uses the ordinary page-root path through `0xff1e`.
- `0x1ed84` selects the published page/control record into a render work
  record.
- `0x1edc6` copies page-root context slots into render-record context slots.
  The primary stream carries render-record context slot `0` as `0xc008004c`;
  the secondary stream carries context slots `(0xc008004c, 0xc00ae122)`.
- Compact render dispatch `0x1ef6a -> 0x1efc2 -> 0x1effe` resolves glyphs
  through `0x1f354` using the copied context slots. The selected font is
  therefore the context longword plus mapped glyph byte, not the raw PCL
  request or original host byte alone.
- The primary stream's first nonblank row is:

```text
.............###...........................###...
```

- The secondary stream's first visible row is:

```text
.........################..################...###
```

State classification:

- Canonical:
  selected text slot `0x782f06`, primary context `0x782ee6`, secondary
  context `0x782ef6`, primary map `0x782f32`, secondary map `0x783032`,
  active symbol words `0x783144/0x783146`, remembered symbol words
  `0x782f08/0x782f0a`, selected page-root slot `0x78297e`, page-root context
  slots, compact text objects, and render-record context slots.
- Derived/cache:
  candidate survivor lists, selected candidate slot `0x7828a8`, selected
  target `0x7828de`, snapshot records `0x783148/0x783152`, HMI `0x78315c`,
  transient selected context `0x782992`, current font id `0x782f2e`, compact
  coordinates, glyph-entry pointers, and render-band fields.
- Parser scratch:
  setup records from `0x1201e` / `0x12008`, mode-13 font-selection command
  records, dirty flags `0x782f2c/0x782f2d` while refresh is pending, and the
  following printable bytes.
- Firmware bookkeeping:
  page-root live-font flags, `0xc4fc` slot-scan state, symbol-map snapshot
  provenance byte `+0x09`, selected-font flags `0x783132/0x783133`,
  publication flag `0x782996`, scheduler cursors, and render-work progress
  words.
- Hardware/external:
  the physical host path that supplied the same normalized bytes to `0xa904`,
  plus later formatter/DC timing outside the ROM-local page-record/render
  chain.
- Unknown:
  no unresolved ROM-local middle edge remains for the primary and secondary
  built-in selection streams documented here. Remaining font work starts only
  from variants that change candidate windows `0x7827a0..0x7827b8`, selected
  slot `0x7828a8`, active symbol words, selected context/map bytes, compact
  object shape, bridge state, or ROM-derived rows.

Evidence:

- Checked-in explanations:
  `Worked Path: Font Selection To Visible Glyphs` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md),
  [font-context-metrics.md](font-context-metrics.md),
  [built-in-resource-scan.md](built-in-resource-scan.md),
  [resource-rom.md](resource-rom.md),
  [page-record-storage.md](page-record-storage.md),
  [page-raster-imaging.md](page-raster-imaging.md), and
  [semantic-state-model.md](semantic-state-model.md).
- Focused listings and extracts:
  `generated/disasm/ic30_ic13_font_context_install_00c428.lst`,
  `generated/disasm/ic30_ic13_font_update_common_00c580.lst`,
  `generated/disasm/ic30_ic13_font_candidate_activate_01569c.lst`,
  `generated/disasm/ic30_ic13_font_id_select_017708.lst`,
  `generated/disasm/ic30_ic13_symbol_set_handler_01be22.lst`,
  `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`,
  `generated/analysis/ic30_ic13_active_symbol_set_flow.md`,
  `generated/analysis/ic30_ic13_font_context_bridge.md`, and
  `generated/analysis/ic30_ic13_text_glyph_index_flow.md`.

## Minimal Raster Payload Walkthrough

This is the smallest top-level raster byte-to-pixel spine for an accepted
mode-0 row. It composes `Worked Path: Raster Row` and `Worked Path: Raster
Transfer Gates And Modes` in
[firmware-dataflow-model.md](firmware-dataflow-model.md) with the object and
renderer detail in [raster-graphics.md](raster-graphics.md).

Input stream:

```text
ESC *t300R ESC *r1A ESC *b4W f0 0f aa 55
```

Input bytes:

```text
1b 2a 74 33 30 30 52 1b 2a 72 31 41
1b 2a 62 34 57 f0 0f aa 55
```

Parser and command dispatch:

- Host bytes are normalized by `0xa904` and delivered to parser loop
  `0x11774`.
- `ESC *t300R` produces command record `80 52 01 2c 00 00` and calls handler
  `0x10808`.
- `ESC *r1A` produces command record `80 41 00 01 00 00` and calls handler
  `0x1075a`.
- `ESC *b4W` produces command record `80 57 00 04 00 00` and calls handler
  `0x11f82`; the four payload bytes are not consumed by the parser command
  matcher.

Raster state and delayed payload:

- `0x10808` consumes the requested resolution while raster active byte
  `0x783182` is clear. For `300`, it writes scale `1` and encoded mode `0`
  into raster state block `0x783170`.
- `0x1075a` starts raster graphics. Parameter `1` seeds the origin from the
  active cursor axis, writes the raster baseline/origin fields, computes byte
  limit `+0x10`, and leaves active byte `+0x12` set.
- `0x11f82` schedules delayed handler `0x105d0` through `0x121cc`, storing
  pending flag `0x782a1a = 1`, handler longword `0x782a1c = 0x105d0`, and the
  saved six-byte command record in `0x782a20..0x782a25`.
- When parser mode returns to zero, `0x12218` restores record
  `80 57 00 04 00 00` and calls `0x105d0` through the saved handler pointer.
  `0x105d0` reads byte count `4`, writes row/count state in `0x783170`, and
  gates the payload against page extent and byte limit.

Page-object construction:

- For this accepted nonnegative row, `0x105d0` ensures a current page root
  through `0x10084`, stores accepted count `+0x04 = 4`, stores overflow
  `+0x06 = 0`, and calls `0x13070` with state pointer `A4 = 0x783170`.
- `0x13070` computes bucket index `0x782a7c` from raster row `+0x02`, packed
  key `0x782a7e` from row/x state, and requested object size from accepted
  count `+0x04`.
- `0x13250` allocates and links an encoded-span bucket object under current
  page-root field `+0x1c`. `0x138de` copies the accepted payload bytes from
  `0xa904` into object payload `+0x0a`.
- The mode-0 object for this stream is:

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

Publication, bridge, and render:

- The raster object remains pending page content under current page root
  `0x78297a` until a publication path runs.
- `0xff1e` publishes the current root, sets publication flag `0x782996`, and
  clears `0x78297a`.
- `0x1ed84` seeds the active render record from active source `0x780eae`.
  `0x1edc6` copies source root `+0x1c` to render-record `+0x18`.
- `0x1eba4` calls `0x1ef6a` for an active band. `0x1ef6a` calls `0x1ef86` for
  band setup and `0x1efc2` for bucket-chain dispatch.
- `0x1efc2` sees object byte `+0x04 & 0xc0 == 0x80` and dispatches to encoded
  raster writer `0x1f88e`.
- `0x1f88e` selects helper `0x1f8da` from table `0x1f8ca` because
  `object[5] & 0x03 == 0`. Mode `0` copies literal payload words into the
  destination row; the row contents come from the object payload bytes and the
  ROM writer path, not from an external row comparison.

State classification:

- Canonical:
  input bytes, parser command records, raster state block `0x783170`, current
  page root `0x78297a`, encoded-span object bytes under root `+0x1c`,
  published source record, active source `0x780eae`, and render-record bucket
  roots.
- Derived/cache:
  bucket index `0x782a7c`, packed key `0x782a7e`, per-object capacity
  `0x782a80`, render-band fields `0x783a20`, `0x783a22`, `0x783a28`, stride
  `0x783a1c`, and mode-derived expansion helper selection.
- Parser scratch:
  pending flag `0x782a1a`, handler pointer `0x782a1c`, saved command record
  `0x782a20..0x782a25`, restored `80 57 00 04 00 00` record, payload cursor,
  and any bytes drained or copied by the delayed payload reader.
- Firmware bookkeeping:
  stream allocator cursors `0x782a70/0x782a72/0x782a76`, publication flag
  `0x782996`, pool cursors `0x780ea6/0x780eaa/0x780eae`, render-work pointer
  `0x783a18`, and scheduler progress fields.
- Hardware/external:
  the physical source that supplied the same normalized bytes to `0xa904`,
  plus the later formatter/DC timing events that allow active-band rendering.
  These do not alter the ROM-local encoded-span object or `0x1f88e` pixel
  construction once the same normalized bytes and publication boundary exist.
- Unknown:
  no ROM-local parser, delayed-payload, object-layout, bridge, or mode-0
  render-dispatch edge is unresolved for this accepted raster path. Remaining
  raster work starts only when a stream changes gate outcomes, accepted count
  or drain behavior, allocator split state, encoded mode, bridge roots,
  packed-key advance, or `0x1f88e` row-construction helper.

Evidence:

- Checked-in explanations:
  `Worked Path: Raster Row` and `Worked Path: Raster Transfer Gates And Modes`
  in [firmware-dataflow-model.md](firmware-dataflow-model.md),
  [raster-graphics.md](raster-graphics.md),
  [pcl-parser-core.md](pcl-parser-core.md),
  [page-record-storage.md](page-record-storage.md),
  [active-render-scheduler.md](active-render-scheduler.md), and
  [page-raster-imaging.md](page-raster-imaging.md).
- Focused listings:
  `generated/disasm/ic30_ic13_main_parser_loop_011774.lst`,
  `generated/disasm/ic30_ic13_raster_handlers_0105d0.lst`,
  `generated/disasm/ic30_ic13_raster_object_queue_013070.lst`,
  `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`,
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`,
  `generated/disasm/ic30_ic13_active_render_scheduler_01eb2a.lst`,
  `generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`, and
  `generated/disasm/ic30_ic13_bitmap_encoded_span_modes_01f88e.lst`.

## Minimal Dense Raster Split Walkthrough

This extends the accepted `ESC *b#W` raster path above to a row whose accepted
payload is too large for one encoded-span object. The split is a
page-object-construction behavior, not a renderer behavior: `0x13070` and
`0x13250` create one or more class-`0x80` bucket objects before publication,
and `0x1f88e` later consumes whatever object chain the producer built.

Representative condition:

```text
ESC *t300R ESC *r1A ESC *b300W <300 payload bytes>
```

Parser and transfer gate:

- Parser dispatch is unchanged from the simple raster payload path:
  `ESC *b#W` reaches `0x11f82`, which schedules delayed handler `0x105d0`
  through `0x121cc`; `0x12218` restores the six-byte command record and calls
  `0x105d0`.
- `0x105d0` owns transfer acceptance. It writes raster row word `+0x02`,
  accepted byte count `+0x04`, overflow count `+0x06`, and active byte
  `+0x12` in raster state block `0x783170`.
- Only accepted nonnegative rows call `0x13070`. Beyond-extent rows drain
  bytes through `0xdace`; negative rows ensure a page root and drain without
  queueing an encoded object.

Split allocation:

- `0x13070..0x13136` derives bucket index `0x782a7c`, packed key
  `0x782a7e`, requested object size `accepted + 0x0a`, and the render mode
  byte copied later into object `+0x05`.
- `0x13250..0x132ae` links each returned object at the head of the selected
  current-page bucket chain under root `+0x1c`, writes class byte
  `+0x04 = 0x80`, and copies the raster mode byte into `+0x05`.
- `0x132be..0x13320` is the same-chunk branch. When the requested size fits
  remaining stream bytes `0x782a70`, it writes capacity
  `0x782a80 = size - 0x0a`, advances free cursor `0x782a76`, subtracts from
  `0x782a70`, and returns the old free pointer.
- `0x132ce..0x132fc` is the current-tail branch. When the request does not
  fit but at least `12` bytes remain, it writes
  `0x782a80 = 0x782a70 - 0x0a`, clears `0x782a70`, and returns the current
  free pointer.
- `0x13328..0x13382` is the new-chunk branch. It allocates a `0x100`-byte
  stream chunk through `0x1710`, links it through `0x782a72`, seeds
  `0x782a76 = chunk + 4`, and either reuses the same-chunk path or caps an
  oversized request at capacity `0x00f2`.

Object-chain effect:

- `0x13146..0x13220` writes object capacity word `+0x06` from `0x782a80`,
  writes packed key `+0x08` from `0x782a7e`, and copies up to that many
  payload bytes through `0x138de`.
- If accepted bytes remain, `0x1319e..0x131d0` subtracts the copied capacity
  from raster state `+0x04`, advances the packed key through
  `0x332ee(0x782a80, mode + 1)`, and loops back to allocate the next object.
- For the documented static `0x012c` accepted-count case with an empty fresh
  chunk, the first object is capped at capacity `0x00f2`, the second object
  carries the remaining `0x003a` bytes, and the later `0x003a` object becomes
  the bucket head because `0x13250` inserts each object at the head.
- For the documented current-tail case with `0x782a70 = 0x0014`, a request
  larger than the tail writes `0x782a80 = 0x000a`, emits one ten-byte object
  from the tail, clears `0x782a70`, advances the packed key, and loops for the
  remaining accepted bytes.

Render consequence:

- Publication and bridge preserve the encoded object chain through
  `0xff1e -> 0x1ed84 -> 0x1edc6`.
- Scheduler and render dispatch are unchanged:
  `0x1eba4 -> 0x1ef6a -> 0x1efc2 -> 0x1f88e`.
- Pixel provenance for a dense row is therefore the ordered bucket-chain walk
  over the split class-`0x80` objects plus the selected `0x1f88e` mode helper.
  The row bytes are derived from object payload, packed keys, mode helper, and
  destination fields; no external rendered-row image is part of the evidence.

State classification:

- Canonical:
  raster state block `0x783170`, encoded-span object fields `+0x04`,
  `+0x05`, `+0x06`, `+0x08`, payload `+0x0a..`, current page-root bucket
  heads, published bucket roots, and render-record bucket root `+0x18`.
- Derived/cache:
  bucket index `0x782a7c`, packed key `0x782a7e`, per-object capacity
  `0x782a80`, packed-key advance through `0x332ee`, render-band caches
  `0x783a20`, `0x783a22`, `0x783a28`, and stride `0x783a1c`.
- Parser scratch:
  restored delayed `80 57 ...` command record, delayed handler state
  `0x782a1a/0x782a1c/0x782a20..0x782a25`, payload cursor, and drained bytes.
- Firmware bookkeeping:
  stream allocator cursors `0x782a70`, `0x782a72`, `0x782a76`,
  publication/copy-stop byte `0x782996`, allocator failure returns, scheduler
  cursors, and render-work progress.
- Hardware/external:
  none for this ROM-local split contract.
- Unknown:
  no unresolved branch target remains inside `0x13070..0x13382` for the
  documented same-chunk, current-tail, new-chunk, and capped-new-chunk paths.
  Remaining dense-raster work starts only from byte streams that change
  transfer acceptance, drain behavior, allocator pre-state, copy-stop state,
  bridge bucket roots, or mode-specific row construction in `0x1f88e`.

Evidence:

- Checked-in explanations:
  `Dense-Row Split Composition Checkpoint` in
  [raster-graphics.md](raster-graphics.md#dense-row-split-composition-checkpoint),
  `Worked Path: Raster Transfer Gates And Modes` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md),
  and `Raster Transfer Gate And Encoded Rows` in
  [semantic-state-model.md](semantic-state-model.md).
- Focused listings:
  `generated/disasm/ic30_ic13_raster_handlers_0105d0.lst`,
  `generated/disasm/ic30_ic13_raster_object_queue_013070.lst`,
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`,
  `generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`, and
  `generated/disasm/ic30_ic13_bitmap_encoded_span_modes_01f88e.lst`.

## Minimal Macro Replay Walkthrough

This is the smallest top-level stored-byte replay spine. It shows how bytes
that were first received as host input can be stored in a macro record, replay
through `0xa904` as parser input, and then use the same page-object and render
pipeline as live host bytes.

Input stream:

```text
ESC &f123Y ESC &f0X ! CR ESC &f1X ESC &f2X
```

Input bytes:

```text
1b 26 66 31 32 33 59 1b 26 66 30 58 21 0d
1b 26 66 31 58 1b 26 66 32 58
```

Parser and macro command dispatch:

- Live bytes enter through `0xa904`, parser wrapper `0xda9a`, and parser loop
  `0x11774`.
- Normal parser mode `17` routes `ESC &f#Y` to `0xe112` and `ESC &f#X` to
  `0xdd08`.
- `0xe112` rewinds the six-byte command record and writes absolute parsed id
  `123` to current macro id field `0x783164`.
- `0xdd08` rewinds command-record cursor `0x78299e`, calls `0xe0a4`, and
  dispatches selector `0`, `1`, or `2` from the parsed `ESC &f#X` parameter.
- `0xe0a4` selects or allocates a 12-byte record in macro pool `0x782a98`,
  writes current record pointer `0x782d7a`, and treats a record as selectable
  only when record head pointer `+0x00` is nonzero and id word `+0x08`
  matches the requested id.

Definition storage:

- Selector `0` reaches `0xdd86` and starts definition mode. Following payload
  bytes append to the selected macro record through `0xe002` instead of
  dispatching as normal text/control bytes.
- Alternate/data parser table `0x116f6` still routes `x/X` to `0xdd08`, so
  the later `ESC &f1X` can stop the definition while ordinary payload bytes
  are stored.
- `0xe002` appends stored bytes into linked `0x100`-byte chunks rooted by
  macro record `+0x00`; each chunk has a four-byte next pointer followed by
  252 payload bytes.
- For this stream, stored payload bytes are `21 0d`. During definition, the
  printable handler `0xd04a` and CR handler `0xf02c` do not run for those
  bytes.
- Selector `1` reaches `0xddfc`, normalizes record `+0x04` from raw chunk
  count to payload count, clears empty or auto-prefix-only records, and leaves
  the nonempty `21 0d` record selectable.

Execute frame and replay:

- Selector `2` reaches `0xde7c -> 0xe418`. `0xe418` advances data-chain frame
  pointer `0x782d76` by `0x0e` and writes an execute replay frame.
- Frame `+0x00/+0x04` copy the macro payload-chain head and raw byte count,
  frame `+0x08 = 4`, frame `+0x09 = 2`, and frame `+0x0a` points at the
  execute environment snapshot chain.
- On the next parser byte request, `0xa904` gives the active data-chain frame
  priority over outer live input. Replayed bytes `21 0d` return to
  `0x11774` as ordinary parser bytes.
- Replayed byte `0x21` falls through the normal printable fallback to
  `0xd04a`. Replayed byte `0x0d` reaches CR handler `0xf02c`.
- At the frame-end marker, `0xa904` calls `0xe22c`. For execute frame kind
  `2`, `0xe22c` restores the environment snapshot, frees the snapshot chain
  through `0x18b4`, rewinds `0x782d76`, and resumes the outer byte source.

Page-object and render effect:

- Replayed `0xd04a` uses the same printable source path as live byte `0x21`.
  In the documented `LINE_PRINTER` case it maps to compact glyph byte `0x20`,
  source flag `1`, and source object `0x782d7e`.
- The flagged built-in path `0xd550 -> 0xd824 -> 0x12f2e -> 0x1387c` queues a
  compact text object under current page-root bucket `+0x1c`.
- The covered replayed glyph object prefix is the same as the direct
  printable path:

```text
00 00 00 00 00 00 00 01 20 00 01
```

- Replayed CR updates cursor/control state through `0xf02c`; in this `!\r`
  path it does not create a separate page object.
- Publication `0xff1e` later snapshots the current page root, clears
  `0x78297a`, and exposes the compact object to render entry.
- `0x1ed84` seeds the active render record, `0x1edc6` copies bucket/context
  roots, and `0x1ef6a -> 0x1efc2 -> 0x1effe` dispatches the replay-produced
  compact object to the same compact text renderer used by live host bytes.
  Macro execute replay has no macro-specific renderer.

State classification:

- Canonical:
  current macro id `0x783164`, macro record pool `0x782a98`, selected record
  pointer `0x782d7a`, macro payload chunks, active data-chain frame pointer
  `0x782d76`, execute frame fields `+0x00/+0x04/+0x08/+0x09/+0x0a`, replayed
  byte values, current page root `0x78297a`, compact text object, published
  source record, and render-record bucket/context roots.
- Derived/cache:
  normalized payload count from selector `1`, execute snapshot chain,
  compact bucket/key fields `0x782a7c..0x782a7e`, glyph offsets from the
  selected font record, and render-band fields `0x783a20`, `0x783a22`, and
  `0x783a28`.
- Parser scratch:
  mode-17 macro command tokenizer state, alternate/data parser table
  selection at `0x116f6`, definition-mode byte `0x782c18`, append-error byte
  `0x782c19`, command-record cursor `0x78299e`, and replayed bytes `21 0d`.
- Firmware bookkeeping:
  macro chunk allocator state rooted at `0x783988`, record raw count `+0x04`,
  host gate bit 1 in `0x780e66`, frame-end cleanup through `0xe22c`, stream
  allocator fields `0x782a70/0x782a72/0x782a76`, publication flag
  `0x782996`, and scheduler/render progress words.
- Hardware/external:
  the original physical source that supplied the macro-definition and execute
  command bytes to `0xa904`, plus later formatter/DC timing events that cause
  publication and active-band rendering. Replayed payload bytes themselves are
  ROM-local data-chain bytes once the macro record exists.
- Unknown:
  no ROM-local middle edge is unresolved for this stored `!\r` execute path
  to compact text rendering. Remaining macro work must change replay-frame
  fields, skip-gate state, parser/delayed-payload dispatch, page-object
  fields, bridge roots, continuation fields, or ROM-derived row construction.

Evidence:

- Checked-in explanations:
  `Worked Path: Macro Execute Replay` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md),
  [macro-data-chain.md](macro-data-chain.md),
  [host-byte-fetch.md](host-byte-fetch.md),
  [pcl-parser-core.md](pcl-parser-core.md),
  [page-record-storage.md](page-record-storage.md), and
  [page-raster-imaging.md](page-raster-imaging.md).
- Focused listings and extracts:
  `generated/disasm/ic30_ic13_pcl_escape_parser_00da9a.lst`,
  `generated/disasm/ic30_ic13_macro_record_chain_helpers_00dfba.lst`,
  `generated/disasm/ic30_ic13_macro_environment_snapshot_helpers_00e65c.lst`,
  `generated/disasm/ic30_ic13_main_parser_loop_011774.lst`,
  `generated/disasm/ic30_ic13_host_byte_fetch_00a904.lst`,
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`, and
  `generated/analysis/ic30_ic13_tokenizer_macro_callers.md`.

## Minimal Overlay Publication Walkthrough

This is the smallest top-level overlay replay spine. It differs from macro
execute replay because the stored bytes are consumed by page finalization
before publication, not by a live `ESC &f2X` parser command.

Setup stream:

```text
ESC &f123Y ESC &f0X ! CR ESC &f1X ESC &f4X
```

Publication-time effect:

```text
current page content -> 0xff1e overlay detour -> replay ! CR
-> page-root publication -> normal render dispatch
```

Macro record and overlay state:

- `ESC &f123Y` reaches `0xe112` and writes current macro id `0x783164`.
- `ESC &f0X` reaches `0xdd08`, selects record id `123` through `0xe0a4`,
  and starts definition mode through selector `0`.
- Payload bytes `21 0d` append through `0xe002` into the selected macro
  record. They do not run `0xd04a` or `0xf02c` during definition.
- `ESC &f1X` stops the definition through selector `1`, normalizes the stored
  payload count, and leaves the nonempty record selectable.
- `ESC &f4X` reaches selector `4`, resolves the current record, writes
  overlay state byte `0x782a92`, and copies the selected macro id to
  `0x782a94`.

Publication detour:

- Page finalization reaches `0xff1e`. When overlay state is enabled, the
  selected overlay record exists, and current page-root retry bit `+0x14.0`
  is clear, `0xff1e` / `0xff8e` reselects id `0x782a94` through `0xe0a4`.
- `0xe4f4` builds a non-replay frame at `0x782d4c`, snapshots the active
  page/parser environment, saves cursor longword `0x782c92`, and refreshes
  layout through `0xe5e2`.
- The frame copies macro record `+0x00/+0x04` to frame `+0x00/+0x04`, writes
  byte `+0x08 = 4`, writes frame kind `+0x09 = 4`, and writes snapshot pointer
  `+0x0a = 0`.
- If the frame has payload bytes, `0xe4f4` sets host gate bit 1 in
  `0x780e66`. `0xa904` then gives this frame priority over live host input.
- Stored overlay bytes `21 0d` re-enter parser loop `0x11774` as ordinary
  bytes. `0x21` routes to `0xd04a`; `0x0d` routes to `0xf02c`.
- At the frame-end marker, `0xa904` calls `0xe22c`. For frame kind `4`,
  `0xe22c` restores page/parser state, sets overlay/page-parser state
  `0x782a92 = 0x63`, and resumes the publication path.

Page-object and render effect:

- Replayed `0xd04a` uses the same text source and compact object path as live
  byte `0x21`: `0xd550 -> 0xd824 -> 0x12f2e -> 0x1387c`.
- The replayed compact object is added to the current page root before the
  root is published. Overlay replay therefore composes with any existing base
  page objects, such as selector-7 rule objects, rather than rendering into a
  separate bitmap.
- After replay cleanup, `0xff1e` publishes the page root. `0x1ed84` and
  `0x1edc6` copy bucket, rule, fixed-list, and context roots into the active
  render record.
- `0x1ef6a` renders the composed record through the same compact, rule,
  fixed-list, segment-list, and raster helpers used by live host bytes. Overlay
  replay has no overlay-specific pixel writer.

State classification:

- Canonical:
  macro record pool `0x782a98`, selected record pointer `0x782d7a`, overlay
  state `0x782a92`, saved overlay id `0x782a94`, current page root
  `0x78297a`, page-root retry flag `+0x14.0`, non-replay frame fields at
  `0x782d4c`, replayed payload bytes, page-root object roots, published
  source record, and render-record roots.
- Derived/cache:
  normalized macro payload count, replay-derived compact coordinates, rule
  decoder mutations when a base rule is present, render-band fields
  `0x783a20`, `0x783a22`, and `0x783a28`, and any cursor/layout values
  recomputed by `0xe5e2`.
- Parser scratch:
  mode-17 macro command records, alternate/data definition state, stored
  overlay payload bytes while the non-replay frame is active, replayed parser
  bytes `21 0d`, and delayed-payload records for overlay variants that replay
  transparent or raster commands.
- Firmware bookkeeping:
  macro chunk allocation, frame kind `+0x09 = 4`, frame stride byte
  `+0x08 = 4`, host gate bit 1 in `0x780e66`, saved cursor longword
  `0x782c92`, environment snapshots, `0xe22c` cleanup, publication flag
  `0x782996`, and scheduler/render progress fields.
- Hardware/external:
  the physical source that supplied the setup stream and the formatter/DC
  timing events that later cause publication and active-band rendering. Once
  the macro record and overlay state exist, the overlay replay bytes are
  ROM-local data-chain bytes.
- Unknown:
  no ROM-local middle edge is unresolved for the documented overlay `!\r`
  publication path. Overlay variants matter only when they change replay-frame
  fields, skip-gate state, parser/delayed-payload dispatch, page-object
  fields, bridge roots, continuation fields, or ROM-derived row construction.

Skip-gate boundaries:

- Disabled overlay mode, missing selected record from `0xe0a4(0x782a94)`, and
  current page-root retry bit `+0x14.0` all skip `0xe4f4` and publish the base
  page without overlay replay.
- These are output-affecting parser/page boundaries, not hardware boundaries:
  they decide whether replayed bytes mutate the current page root before
  publication.

Evidence:

- Checked-in explanations:
  `Worked Path: Macro Overlay Replay Publication` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md),
  [macro-data-chain.md](macro-data-chain.md),
  [publication-commands.md](publication-commands.md),
  [host-byte-fetch.md](host-byte-fetch.md),
  [page-record-storage.md](page-record-storage.md), and
  [page-raster-imaging.md](page-raster-imaging.md).
- Focused listings and extracts:
  `generated/disasm/ic30_ic13_macro_record_chain_helpers_00dfba.lst`,
  `generated/disasm/ic30_ic13_macro_environment_snapshot_helpers_00e65c.lst`,
  `generated/disasm/ic30_ic13_host_byte_fetch_00a904.lst`,
  `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`,
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`,
  `generated/disasm/ic30_ic13_main_parser_loop_011774.lst`, and
  `generated/analysis/ic30_ic13_tokenizer_macro_callers.md`.

## Minimal Rectangle Rule Walkthrough

This is the smallest top-level rectangle/rule spine. It covers a page object
that is not stored in the compact/raster bucket array: the producer writes a
rule-list object under page-root `+0x24`, the bridge copies it to render
`+0x1c`, and the renderer dispatches it through `0x1f446`.

Input stream:

```text
ESC *c12a5b0P
```

Input bytes:

```text
1b 2a 63 31 32 61 35 62 30 50
```

Parser and command dispatch:

- Host bytes are normalized by `0xa904`, pass through parser wrapper
  `0xda9a`, and enter parser loop `0x11774`.
- The parser walks modes `0 -> 1 -> 3 -> 16 -> 16 -> 16 -> 0`. Prefix setup
  handlers `0x11eb6`, `0x11ec8`, and `0x11eda` keep the `ESC *c` family
  active while chained parameters are parsed.
- `ESC *c12a` produces a six-byte command record consumed by handler
  `0x10e68`.
- `5b` stays in the same `*c` family and calls handler `0x10e22`.
- `0P` terminates the family and calls fill handler `0x10898`.

Rectangle state and rule source:

- `0x10e68` rewinds command-record cursor `0x78299e` and writes dot width
  `12` to rectangle width field `0x78316a`.
- `0x10e22` rewinds the next command record and writes dot height `5` to
  rectangle height field `0x783166`.
- `0x10898` rewinds the final command record and maps fill parameter `0` to
  selector `7`, the solid black rule selector.
- `0x10898` calls `0x10b80` when width and height are nonzero. `0x10b80`
  consumes current cursor fields `0x782c8a/0x782c8e`, orientation byte
  `0x782da3`, page extents `0x782db8/0x782db6`, and pending
  width/height/fill state.
- `0x10b80` clips or rejects the rectangle, ensures a current page root
  through `0x10084`, and writes source record `0x782a88`. For this primary
  stream the source record represents x `10`, y `20`, width `12`, height `5`,
  and selector `7`.

Rule-list object construction:

- `0x13386` consumes source record `0x782a88` and derives rule bucket/key
  fields through `0x134d6`.
- `0x133aa` allocates a 14-byte rule object through `0x1381c` and inserts it
  in ascending object byte `+0x04` order under current page-root list `+0x24`.
- The primary object before bridge is:

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

Publication, bridge, and render:

- The rule object remains pending under current page-root list `+0x24` until
  publication.
- `0xff1e` publishes the page root. `0x1ed84` seeds the active render record
  from selected source `0x780eae`.
- `0x1edc6` copies source root `+0x24` to render-record `+0x1c`. During that
  copy it ORs object byte `+0x05` with `0x10` and copies height `+0x0a` to
  continuation word `+0x0c`.
- The bridged object is:

```text
00 00 00 00 01 17 4a 00 00 0c 00 05 00 05
```

- `0x1eba4` calls `0x1ef6a` for an active band. `0x1ef6a` calls `0x1ef86`,
  then bucket-chain dispatcher `0x1efc2`, then rule-list dispatcher
  `0x1f446`, then fixed-list dispatcher `0x1f756`.
- `0x1f446` walks render-record rule list `+0x1c`. The bridged selector byte
  `0x17` has low nibble `7`, so `0x1f446` dispatches to solid helper
  `0x1f596`.
- `0x1f596` decodes key `0x4a00` as x `10`, y `20`, width `12`, rows `5`,
  and partial mask `0xfff0`. It writes the generated solid rule rows into the
  active band buffer.

State classification:

- Canonical:
  rectangle width `0x78316a`, rectangle height `0x783166`, area-fill id
  `0x78316e`, cursor/page geometry fields consumed by `0x10b80`, source
  record `0x782a88`, current page root `0x78297a`, rule-list root `+0x24`,
  rule object bytes, published source record, and render-record rule list
  `+0x1c`.
- Derived/cache:
  rule bucket/key fields `0x782a7c`, `0x782a7d`, and `0x782a7e`, horizontal
  phase `0x782dc0`, bridged selector bit `0x10`, continuation word `+0x0c`,
  render-band fields `0x783a20`, `0x783a22`, and `0x783a28`, and destination
  phase/cache fields used by `0x1f596`.
- Parser scratch:
  parser mode byte, command-record cursor `0x78299e`, and the six-byte
  command records consumed by `0x10e68`, `0x10e22`, and `0x10898`.
- Firmware bookkeeping:
  stream allocator fields `0x782a70/0x782a72/0x782a76`, page-root retry bit
  `+0x15.0` for no-room retry, publication flag `0x782996`, pool cursors,
  render-work pointer `0x783a18`, and scheduler progress fields.
- Hardware/external:
  the physical source that supplied the normalized `ESC *c12a5b0P` bytes to
  `0xa904`, plus later formatter/DC timing events that allow publication and
  active-band rendering. These do not change the ROM-local rule object or
  `0x1f596` pixel construction.
- Unknown:
  no ROM-local selector-7 rule object, bridge, or solid-render dispatch edge
  is unresolved for this path. Remaining rectangle work starts only when a
  stream changes clipping output, allocation rollover, retry publication
  fields, rule object bytes, bridge state, render dispatch, or row
  construction.

Evidence:

- Checked-in explanations:
  `Worked Path: Rectangle Rule` and `Worked Path: Rectangle Rule Selectors
  And Clipping` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md),
  [rectangle-graphics.md](rectangle-graphics.md),
  [pcl-parser-core.md](pcl-parser-core.md),
  [page-record-storage.md](page-record-storage.md), and
  [page-raster-imaging.md](page-raster-imaging.md).
- Focused listings and extracts:
  `generated/disasm/ic30_ic13_main_parser_loop_011774.lst`,
  `generated/disasm/ic30_ic13_rectangle_graphics_010898.lst`,
  `generated/disasm/ic30_ic13_display_list_helpers_013386.lst`,
  `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`,
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`,
  and `generated/analysis/ic30_ic13_rectangle_graphics_flow.md`.

## Minimal Transparent Payload Walkthrough

This is the smallest top-level transparent-print-data spine. It covers a
counted payload that is not a binary skip: `ESC &p#X` arms a delayed reader,
and the payload bytes are then routed into the normal text/page-object path.

Input stream:

```text
ESC &p2X!!
```

Input bytes:

```text
1b 26 70 32 58 21 21
```

Parser and delayed-payload setup:

- Host bytes are normalized by `0xa904`, pass through parser wrapper
  `0xda9a`, and enter parser loop `0x11774`.
- `ESC &p2X` enters the transparent-print-data command family and calls
  handler `0x11f5a`.
- `0x11f5a` is an arming stub. It pushes delayed handler pointer `0x12452`
  and calls shared delayed-payload scheduler `0x121cc`.
- `0x121cc` rewinds command-record cursor `0x78299e` by six, writes pending
  flag `0x782a1a = 1`, writes handler pointer `0x782a1c = 0x12452`, and
  saves command record `80 58 00 02 00 00` at `0x782a20..0x782a25`.
- When parser mode returns to zero, `0x12218` restores that saved command
  record and calls `0x12452`.

Payload reader and routing:

- `0x12452` rewinds `0x78299e` by six and reads command-record word `+2`.
  The absolute value of that word is the transparent payload count.
- It reads selected text/context slot `0x782f06`, derives a selected-slot
  context byte through `0x332ee` and `0x782eea + 0x10 * slot`, and chooses a
  local filtering word from either that context byte or fallback byte
  `0x782efa` depending on high-character flags `0x783132/0x783133`.
- The payload loop fetches raw payload bytes directly through `0xa904`.
  A payload byte `0x1a` probes one more byte: `1a 58` becomes routed value
  `0x7f`, while `1a xx` with `xx != 58` routes `xx` and consumes the probe.
- In this primary stream, both payload bytes are `0x21`. They route through
  `0xd04a` as ordinary printable bytes.

Page-object and render effect:

- Each routed `0x21` takes the normal printable path through
  `0xd04a -> 0x1393a`.
- In the documented `LINE_PRINTER` path, each byte maps to compact glyph byte
  `0x20`, source flag `1`, and the flagged built-in queue path
  `0xd550 -> 0xd824 -> 0x12f2e -> 0x1387c`.
- The two routed payload bytes reuse one compatible short compact object under
  current page-root bucket array `+0x1c`, just like direct host stream `!!`.
- Publication `0xff1e` snapshots the current root, `0x1ed84` seeds the active
  render record, and `0x1edc6` copies bucket/context roots.
- `0x1ef6a -> 0x1efc2 -> 0x1effe` dispatches the compact object to the same
  compact text renderer used by direct printable bytes. Transparent print data
  has no separate renderer.

State classification:

- Canonical:
  restored transparent command record `80 58 00 02 00 00`, record word `+2`
  payload count, selected text/context slot `0x782f06`, routed payload bytes
  `21 21`, current page root `0x78297a`, compact text object, published
  source record, and render-record bucket/context roots.
- Derived/cache:
  selected-slot context byte `0x782eea + 0x10 * 0x782f06`, fallback filtering
  byte `0x782efa`, high-character flags `0x783132/0x783133`, compact
  coordinates for the two payload glyphs, compact bucket/key fields
  `0x782a7c..0x782a7e`, glyph offsets from the selected font record, and
  render-band fields `0x783a20`, `0x783a22`, and `0x783a28`.
- Parser scratch:
  delayed-payload pending flag `0x782a1a`, delayed handler pointer
  `0x782a1c`, saved record bytes `0x782a20..0x782a25`, command-record cursor
  `0x78299e`, and current payload count inside `0x12452`.
- Firmware bookkeeping:
  local filtering word at `A6-2`, source-object scratch `0x782d7e`, stream
  allocator fields `0x782a70/0x782a72/0x782a76`, publication flag
  `0x782996`, pool cursors, render-work pointer `0x783a18`, and scheduler
  progress fields.
- Hardware/external:
  the physical source that supplied the command and payload bytes to `0xa904`,
  plus later formatter/DC timing events that allow publication and active-band
  rendering. These do not change the ROM-local delayed-reader route or compact
  text pixel construction.
- Unknown:
  no ROM-local parser, delayed-payload, primary routing, page-object, bridge,
  or compact-render edge is unresolved for `ESC &p2X!!`. The remaining
  transparent boundary is the secondary segmented high-control fallback-row
  physical resource-window source at firmware range `0x0c0000..0x0c0321`,
  reached by `SO ESC &p3X ! 80 !` after the primary parser/payload route has
  already succeeded.

Evidence:

- Checked-in explanations:
  `Worked Path: Transparent Print Data` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md),
  [transparent-print-data.md](transparent-print-data.md),
  [pcl-parser-core.md](pcl-parser-core.md),
  [direct-control-codes.md](direct-control-codes.md),
  [font-context-metrics.md](font-context-metrics.md),
  [page-record-storage.md](page-record-storage.md), and
  [page-raster-imaging.md](page-raster-imaging.md).
- Focused listings and extracts:
  `generated/disasm/ic30_ic13_transparent_data_handler_011f5a.lst`,
  `generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst`,
  `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`,
  `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`,
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`, and
  `generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst`.

## Minimal Display Functions Walkthrough

This is the smallest top-level `ESC Y ... ESC Z` direct-reader spine. Unlike
ordinary parser commands, the bytes after `ESC Y` are read directly through
`0xa904` until a local normalized `ESC Z` terminator is seen.

Input stream:

```text
ESC Y ! 05 ! ESC Z
```

Parser and direct-reader dispatch:

- The initial command bytes enter through `0xa904`, parser wrapper `0xda9a`,
  and parser loop `0x11774`.
- Normal parser mode `1` routes byte `Y` to handler `0x12536`.
- After dispatch, `0x12536` fetches loop bytes directly through `0xa904`.
  These loop bytes do not pass through `0xda9a` or the normal parser table.
- The loop keeps local flag `D4`: zero until a routed value is `ESC`
  (`0x1b`), one after `ESC`, and tested when the current value is `Z`
  (`0x5a`). `Z` terminates only when `D4 == 1`.
- Pair `1a 58` is locally normalized to routed value `0x7f` after helper
  `0xd99a`.

Loop routing and page-object effect:

- `0x12536` derives the same filter state used by transparent print data:
  selected slot `0x782f06`, selected context byte
  `0x782eea + 0x10 * slot`, fallback high-control byte `0x782efa`, and local
  high-control filter word at `A6-2`.
- Values `0x00..0x1f` route through fixed-space handler `0xd0f0` only when
  the selected context byte is zero.
- Values `0x80..0x9f` route through `0xd0f0` only when the local filter word
  is zero.
- All other values route through printable handler `0xd04a`. If the routed
  value is CR `0x0d`, `0x12536` calls post-handler `0xf054` after the route.
- For this stream, `0x12536` consumes loop values `21 05 21 1b 5a` and routes
  them:

```text
d04a d0f0 d04a d0f0 d04a
```

- The terminating `ESC Z` pair participates as routed values before the loop
  exits. In the documented built-in path, visible compact entries are `!`,
  `!`, and `Z`; fixed-space routes advance cursor state without compact glyph
  entries.
- Routed printable values use the same `0xd04a -> 0xd824 -> 0x12f2e ->
  0x1387c` compact text path as ordinary printable bytes.
- Publication and render are shared: `0xff1e` publishes the page root,
  `0x1ed84` / `0x1edc6` copy bucket/context roots, and
  `0x1ef6a -> 0x1efc2 -> 0x1effe` renders the compact object.

Alternate/data and status siblings:

- Alternate/data parser mode `1` routes `ESC Y` to handler `0x12120`.
  `0x12120` appends literal prefix `ESC Y` and each normalized loop value
  through macro/data append sink `0xe002` until the same local `ESC Z`
  termination or no-byte return.
- The alternate/data reader has no immediate page-root, page-object,
  publication, or pixel effect. Its output is stored input for later macro or
  data-chain replay.
- Local Control-Z handlers are table-local consumers for `0x1a`, not one
  global parser rule. The documented siblings route literal/synthetic values
  through `0xd04a`, append through `0xe002`, or normalize `1a 58` through
  `0xd99a` depending on parser mode and filter state.
- `ESC z` reaches status/display-off handler `0xcd86`. It tests active
  data-chain frame byte `+9` at `0x782d76 + 9` and calls status helper
  `0x9c2c` only when that byte is zero. This path writes status-side state but
  queues no page objects and renders no pixels.

State classification:

- Canonical:
  direct-reader termination flag `D4`, normalized loop value `D5`, selected
  text/context slot `0x782f06`, routed values, current page root `0x78297a`,
  compact text objects, alternate append stream for `0x12120`, active
  data-chain frame pointer `0x782d76`, published source record, and
  render-record bucket/context roots.
- Derived/cache:
  selected context byte `0x782eea + 0x10 * slot`, fallback filter byte
  `0x782efa`, high-character flags `0x783132/0x783133`, local filter word,
  compact coordinates and glyph mappings, status marker `0x7822db`,
  warning/status bit `0x780e2a.3`, and render-band fields `0x783a20`,
  `0x783a22`, and `0x783a28`.
- Parser scratch:
  the initial `ESC Y` parser mode/table dispatch state and the parser state
  resumed after the direct reader returns. The loop bytes themselves are
  direct-reader values, not normal parser command records.
- Firmware bookkeeping:
  `0xd99a` local control-report side effect, `0xf054` CR post-handler, append
  sink `0xe002`, service-in-progress marker `0x7821cc`, `0x9c2c` wait
  behavior on `0x780e2d.3`, stream allocator fields, publication flag
  `0x782996`, pool cursors, and scheduler/render progress fields.
- Hardware/external:
  the physical source that supplied `ESC Y` and loop bytes to `0xa904`, plus
  later formatter/DC timing events for publication and active-band rendering.
  External consumers of `0x7821cc`, `0x7822db`, and `0x780e2a.3` remain
  outside this ROM-local display-functions path.
- Unknown:
  no ROM-local middle edge remains for the normal `0x12536` reader loop,
  default-filter and filter-on route predicates, alternate/data `0x12120`
  append loop, local Control-Z siblings, or `0xcd86 -> 0x9c2c` status
  boundary.

Evidence:

- Checked-in explanations:
  `Worked Path: Display Functions Direct Reader` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md),
  [display-functions.md](display-functions.md),
  [pcl-parser-core.md](pcl-parser-core.md),
  [transparent-print-data.md](transparent-print-data.md),
  [page-record-storage.md](page-record-storage.md), and
  [page-raster-imaging.md](page-raster-imaging.md).
- Focused listings and extracts:
  `generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst`,
  `generated/disasm/ic30_ic13_control_z_handlers_0120d2.lst`,
  `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`,
  `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`,
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`, and
  `generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst`.

## Minimal VFC Walkthrough

This is the smallest top-level vertical-forms-control spine. VFC table
definition consumes a binary payload and writes layout state; it does not draw.
VFC channel jumps later consume that table to move the cursor or publish the
current page before the next printable byte queues visible text.

Table-load stream:

```text
ESC &l4W 00 00 00 02 !
```

Channel-jump stream:

```text
ESC &l2V !
```

Page-eject sibling:

```text
! ESC &l0V !
```

Parser and delayed table payload:

- All stream bytes enter through `0xa904`, parser wrapper `0xda9a`, and
  parser loop `0x11774`.
- `ESC &l#W` routes through the `ESC &l` family to handler `0x11f6e`.
- `0x11f6e` schedules delayed handler `0x12cfe` through shared delayed
  payload path `0x121cc`.
- `0x121cc` stores the six-byte command record and delayed-handler pointer in
  parser scratch. The lowercase preservation sibling `ESC &l4w4W` records
  lowercase snapshot `80 77 00 04 00 00` and keeps it until uppercase `W`
  terminates the family.
- `0x12218` restores the saved record after parser mode returns to zero and
  calls `0x12cfe`.
- `0x12cfe` rewinds command-record cursor `0x78299e`, reads the absolute
  payload byte count, consumes payload through data reader `0xdace`, writes
  VFC table words rooted at `0x782dde`, clears unused table bytes, derives VFC
  bottom `0x782dc2`, copies text-bottom cache `0x782dd2`, and clears modified
  layout flag `0x782ee1`.
- In `ESC &l4W 00 00 00 02 !`, bytes `00 00 00 02` become the table prefix
  and are consumed before the following printable `!`.
- The following `!` then returns to ordinary printable handler `0xd04a` and
  queues at compact coordinate `0x9001`.

Default table and channel-jump consumers:

- Default-table builder `0x12b96` rebuilds the 128-word VFC table from cached
  line bounds. Shared layout refresh `0xe5e2` calls the same builder after it
  refreshes top offset, margins, text bottom, pending cursor, and font-context
  state.
- For the documented Letter/6 LPI default table, channel selectors are
  one-based: selector `2` searches for bit `0x0002`, and the default table
  marks lines `61` and `62` for channel `2`.
- `ESC &l#V` routes to handler `0x1280a`.
- `0x1280a` reads selector, current VMI `0x783160`, vertical cursor
  `0x782c8e`, horizontal cursor `0x782c8a`, top offset `0x782dce`, line
  caches `0x782ede` and `0x782ee0`, and VFC table words
  `0x782dde..0x782edd`.
- Selector `n` becomes mask `1 << (n - 1)`. Selector `2` therefore searches
  table bit `0x0002`.

Cursor-only output path:

- In the forward in-text `ESC &l2V !` fixture, `0x1280a` finds channel `2` at
  line `1`.
- It ensures a current page root through `0x10084`, resets horizontal cursor
  through `0xf06e`, flushes pending text through `0xf34a`, writes vertical
  cursor y `176`, and lets the following printable `!` queue at compact
  coordinate `0xb001`.
- The before-top sibling starts at y `89`, below top offset `90`; branch
  `0x128ae..0x128f4` normalizes the search start line to `0` before the same
  line-1 hit and the same following printable coordinate `0xb001`.
- These cursor-only paths do not publish the current page. The visible effect
  is the following printable object's coordinate on the current root.

Page-boundary output path:

- Selector-zero top-of-form stream `ESC &l0V!` computes target y `126`, leaves
  an already matching cursor unchanged, ensures a page root, and queues `!` at
  compact coordinate `0x9e02`.
- Selector-zero page-eject stream `! ESC &l0V !` first queues a printable on
  the old page. Branch `0x1299c..0x129c4` then runs
  `0xf06e -> 0xf34a -> 0xf34a -> 0xf124`, publishes the old page through
  `0xff1e`, resets x/y to `10`/`126`, and queues the next `!` on a fresh page
  at compact coordinate `0x9001`.
- Wrap-hit stream `! ESC &l2V !` starts at y `226`, publishes the old page,
  wraps to line `1`, writes y `176`, and queues the next `!` at coordinate
  `0xb001`.
- Wrap-no-hit and target-after-text paths publish the old page and recover to
  top-of-form or near-top y before the following printable queues.
- Non-publishing recovery siblings write the same recovered cursor state
  without calling `0xf124`; the following printable remains on the current
  page.

Publication, bridge, and pixels:

- VFC never writes pixels directly. Pixel output comes from already queued
  page objects or from the printable byte that follows a VFC cursor move.
- Publishing VFC branches use the same `0xf124 -> 0xff1e` boundary as FF and
  reset.
- `0xff1e` preserves the old page root's compact bucket objects in the
  published page/control record, sets publication flag `0x782996`, and clears
  current root pointer `0x78297a`.
- The next printable byte allocates or reuses a fresh current page root through
  the normal `0xd04a -> 0xd824 -> 0x12f2e -> 0x1387c` path.
- Published pre-VFC rows render through `0x1ed84`, `0x1edc6`, and `0x1ef6a`.
  Post-VFC rows render from the fresh page root when that later page is
  published.

State classification:

- Canonical:
  VFC table `0x782dde..0x782edd`, current VMI `0x783160`, top offset
  `0x782dce`, vertical cursor `0x782c8e`, horizontal cursor `0x782c8a`,
  margins `0x782dd6` and `0x782dda`, current page root `0x78297a`,
  published source record, and render-record bucket/context roots.
- Derived/cache:
  VFC bottom `0x782dc2`, text-bottom cache `0x782dd2`, line-count caches
  `0x782ede`, `0x782edf`, and `0x782ee0`, selector mask
  `1 << (selector - 1)`, recovered y values, compact coordinates such as
  `0xb001` and `0x9001`, and render-band fields.
- Parser scratch:
  command-record cursor `0x78299e`, delayed-payload flag `0x782a1a`,
  delayed handler pointer `0x782a1c`, saved command record bytes, direct
  `ESC &l#W` payload bytes, and the current `ESC &l#V` selector.
- Firmware bookkeeping:
  modified-layout flag `0x782ee1`, pending text/cursor latches
  `0x782a58` and `0x782a6d`, pending span-flush flag `0x783184`, publication
  flag `0x782996`, scheduler cursors, and render-work progress words.
- Hardware/external:
  the physical source that supplied the same normalized bytes to `0xa904`,
  plus later formatter/DC timing outside the ROM-local page-record/render
  chain.
- Unknown:
  no unresolved ROM-local middle edge remains for the documented table-load,
  default-table, forward jump, selector-zero, wrap-hit, wrap-no-hit,
  target-after-text, start-after-text, or alternate high-start VFC paths.
  Manual-facing names for line-count fields `0x782ede`, `0x782edf`, and
  `0x782ee0` remain inferred.

Evidence:

- Checked-in explanations:
  `Worked Path: Vertical Forms Control` and `Worked Path: VFC Table And
  Channel Branch Matrix` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md),
  [vertical-forms-control.md](vertical-forms-control.md),
  [direct-control-codes.md](direct-control-codes.md),
  [publication-commands.md](publication-commands.md),
  [page-record-storage.md](page-record-storage.md),
  [active-render-scheduler.md](active-render-scheduler.md), and
  [semantic-state-model.md](semantic-state-model.md).
- Focused listings and extracts:
  `generated/disasm/ic30_ic13_vertical_forms_control_01280a.lst`,
  `generated/disasm/ic30_ic13_control_code_handlers_00f02c.lst`,
  `generated/disasm/ic30_ic13_hmi_vmi_handlers_00ca8c.lst`,
  `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`,
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`, and
  `generated/analysis/ic30_ic13_renderer_fixture_harness.md`.

## Minimal Downloaded Glyph Walkthrough

This is the smallest top-level resource-installation spine that later changes
pixel output. The font commands do not draw during payload installation; they
mutate downloaded-font state. The visible output starts only when a later
printable byte resolves through the installed downloaded glyph.

Input stream:

```text
ESC *c4660d37e5F
ESC )s2193W <0x0891 payload bytes>
% FF
```

Font-control dispatch:

- All stream bytes enter through host byte source `0xa904` and parser loop
  `0x11774`.
- `ESC *c4660d` routes through `0x11eb6`, `0x11ec8`, `0x11eda`, and
  `0x15a56`. Handler `0x15a56` writes current downloaded-font id
  `0x782f2e = 0x1234`.
- `37e` remains in the same `*c` command family and reaches `0x15a18`.
  Handler `0x15a18` writes current character word `0x782f30 = 0x25`.
- `5F` reaches font-control handler `0x16df6`, then `0x16e86 -> 0x17108`.
  The current downloaded-font record has flag bit `6` set, while counters
  `0x782782/0x782786` move from `7/2` to `6/3`.

Downloaded-character payload installation:

- `ESC )s2193W` routes through `0x11eb6`, `0x12008`, `0x11ff6`, and
  `0x11f96`.
- Because the parsed `W` count is nonzero, `0x11f96` schedules delayed
  handler `0x16c14` through shared delayed-payload path `0x121cc` /
  `0x12218`.
- `0x121cc` stores restored record `80 57 08 91 00 00`, pending flag
  `0x782a1a`, and delayed-handler pointer `0x782a1c`.
- `0x12218` restores the command record after parser mode returns to zero
  and calls `0x16c14`.
- `0x16c14` rewinds command-record cursor `0x78299e`, writes payload budget
  `0x783140 = 0x0891`, resolves the current downloaded-font record by
  `0x782f2e`, and enters the downloaded-character install path.
- The installed character uses current character `0x25`, glyph-table entry
  `0x00de`, character record delta `0x0500`, and bitmap offset `0x050c`.
- The installed glyph record bytes are:

```text
00 00 00 00 0c 02 00 81 00 88 00 00
```

- The record describes mode byte `2`, rows `0x81`, width `0x88`, span
  `0x11`, bitmap size `0x0891`, and split-plane payload layout.
- Reader `0x16942` consumes payload bytes through `0xa904`, writes row-prefix
  bytes through `A4`, writes trailing-plane bytes through `A3`, normalizes
  `1a 58` through `0xd99a`, and records continuation state only if the byte
  budget ends before the bitmap copy completes.
- The success path returns through `0x15dc6 -> 0x16498 -> 0x15dcc ->
  0x12328` with `0x783140 = 0`, so no payload bytes are drained before the
  next parser handler.

Printable use and page-object creation:

- The following printable byte `%` reaches handler `0xd04a`.
- `0xd04a` resolves host byte `0x25` through the installed downloaded
  context. The documented source has glyph entry `0x0500`, rows `0x81`,
  width byte `0x11`, x `22`, y `22`, and context slot `3`.
- `0xd824 -> 0x12f2e -> 0x1387c` converts that positioned source into
  segmented-wide compact page objects.
- Selector `0x3003` splits the glyph into two segment objects:

```text
bucket 9: 00 00 00 00 30 03 00 01 25 01 66 01
bucket 1: 00 00 00 00 30 03 00 01 25 00 66 01
```

Object fields:

- `+0x04`: compact selector byte `0x30`, selecting segmented-wide rendering.
- `+0x05`: downloaded context slot `3`.
- `+0x06`: entry count `1`.
- payload byte `0x25`: installed glyph id.
- following byte `0x01` or `0x00`: segment number.
- coordinate `0x6601`: positioned destination for the segment.

Publication, scheduling, and pixels:

- FF reaches handler `0xf0f0`, which finalizes the page through `0xff1e`.
- `0xff1e` publishes the current page root, preserving bucket array entries
  `9` and `1`, empty rule/fixed lists, and context slots `(0, 0, 0, 0)`.
  It clears current page-root pointer `0x78297a` and sets publication flag
  `0x782996`.
- `0x1ed84` copies the published record into an active render work record.
- `0x1edc6` preserves the bucket root and context slots for compact-renderer
  dispatch.
- Scheduler entry `0x1eba4` can produce band words `0..9` for the published
  downloaded-glyph record and call `0x1ef6a` for each active band.
- `0x1ef6a` runs `0x1ef86 -> 0x1efc2 -> 0x1f446 -> 0x1f756`. This stream has
  no rule or fixed-list objects, so visible output comes from bucket dispatch
  `0x1efc2`.
- `0x1efc2` sends compact selector `0x30` to `0x1effe`; the segmented-wide
  row path reaches `0x1f1f0` / `0x1f264` and wide row-copy helpers.
- The documented publication path renders bucket `9`, segment `1`, at page
  row `86`; bucket `1`, segment `0`, is blank for that active band.

State classification:

- Canonical:
  current downloaded-font id `0x782f2e`, current character `0x782f30`,
  current downloaded-font records `0x782640..0x782776`, current-record flag
  bit `6`, installed glyph-table entry `0x00de`, glyph record bytes, current
  page root `0x78297a`, compact bucket objects, published source record, and
  render-record bucket/context roots.
- Derived/cache:
  payload byte budget `0x783140`, parsed span `0x7827c2`, parsed row count
  `0x7827c4`, bitmap byte count `0x7827be`, compact selector `0x3003`,
  segment numbers, bucket indices, and render-band fields.
- Parser scratch:
  command-record cursor `0x78299e`, delayed-payload fields `0x782a1a`,
  `0x782a1c`, `0x782a20..0x782a25`, staged descriptor scratch
  `0x7827de..0x7827e9`, and continuation fields `0x7827c6..0x7827da`.
- Firmware bookkeeping:
  downloaded-record counters `0x782782` and `0x782786`, candidate counters and
  cursors updated by `0x16c14`, heap allocation/release helpers, stream
  allocator fields, publication flag `0x782996`, scheduler cursors, and
  render-work progress words.
- Hardware/external:
  the physical host path that supplied bytes to `0xa904` and later formatter
  timing outside the ROM-local page-record/render chain.
- Unknown:
  no unresolved ROM-local middle edge remains for this segmented-wide
  install-to-print-to-publication path. Remaining downloaded-glyph boundaries
  are broader row/span cross-products, short compact helper indices above
  table entry `128` in `0x1fe76`, wrapped width low bytes selecting invalid
  compact mode-0 helper targets through `0x1f034` / `0x1f08e`,
  segmented-wide span-31 fallback source offset `+0xb50`, and the oversized
  segmented-wide payload-count cap `0x7fff` before `0x16498`.

Evidence:

- Checked-in explanations:
  `Worked Path: Downloaded Glyph` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md),
  `End-To-End Downloaded Glyph Path` in
  [downloaded-fonts.md](downloaded-fonts.md),
  [font-context-metrics.md](font-context-metrics.md),
  [page-record-storage.md](page-record-storage.md),
  [active-render-scheduler.md](active-render-scheduler.md),
  [page-raster-imaging.md](page-raster-imaging.md), and
  [semantic-state-model.md](semantic-state-model.md).
- Focused listings and extracts:
  `generated/disasm/ic30_ic13_assign_font_id_015a56.lst`,
  `generated/disasm/ic30_ic13_font_control_dispatch_016df6.lst`,
  `generated/disasm/ic30_ic13_font_payload_setup_015b80.lst`,
  `generated/disasm/ic30_ic13_font_payload_readers_016874.lst`,
  `generated/disasm/ic30_ic13_font_payload_readers_016880.lst`,
  `generated/disasm/ic30_ic13_font_payload_descriptor_helpers_016a10.lst`,
  `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`,
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`,
  `generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst`,
  and `generated/analysis/ic30_ic13_font_control_flow.md`.

## Current Residual Edge Index

Use this index before opening a new trace window. The supported stream
families below already have checked-in parser, state, page-object, bridge, and
render documentation; new work should start from one of these exact residual
edges or from a byte stream that changes a named field in the family sections.

- Pixel-affecting resource data:
  `Boundary: Secondary Segment-57 Source` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md) is the only current
  documented byte-to-bitmap edge whose rows depend on unknown external
  firmware-address data. The ROM path is traced through transparent payload
  reader `0x12452`, printable/source object production, compact segmented
  objects, bridge `0x1ed84` / `0x1edc6`, and compact renderer
  `0x1f354 -> 0x1f1f0`. The remaining input is resource-window data for
  firmware range `0x0c0000..0x0c0321` after verified bytes
  `0x0bfe22..0x0bffff`.
- ROM-local downloaded-glyph helper boundaries:
  `Boundary: Short Compact Downloaded-Glyph High Rows` documents the unchecked
  `0x1fe76` fallback row-copy table read for short compact rows
  `0x0101..0x0103`; valid entries end at index `128`, while fallback counts
  `199..201` read code bytes as target pointers, with row `0x0102` reaching
  `0x329ad3c0`. `Boundary: Downloaded-Glyph Wrapped Width Low Bytes`
  documents the low-byte width truncation that can send preserved installed
  spans through compact mode-0 invalid targets such as `0x0102 -> 0x0066cc`.
  `Boundary: Segmented-Wide Downloaded-Glyph Fallback Source` documents the
  span-31 fallback A2 source-read boundary at offset `+0xb50` after
  `0x1f264` selected-segment dispatch. These are ROM-local byte-to-renderer
  boundaries, not parser, publication, or bridge gaps.
- Host physical interface:
  `0xa904..0xab8a` is documented as the normalized byte-source contract for
  parser reproduction. Remaining work is physical bus/MMIO naming for host
  modes, not a parser or command-dispatch gap, unless a new trace changes the
  normalized `D7` byte sequence delivered to `0xda9a`.
- Formatter/DC physical timing:
  `0x0f84..0x1282`, `0x1cf8..0x1ea8`, and `0x1eb2a..0x1ed84` are documented
  as ROM-visible wait-object, copy-window, active-source, and band-scheduler
  state machines. Remaining work is mapping external events and connector
  signals to those observed state changes, not deriving pixels from page
  objects.
- ROM-local command variants:
  new parser work should begin only when a byte stream changes a documented
  field or branch boundary: selected font/context fields, transparent/display
  filtering, downloaded-glyph install state, macro replay frame state, raster
  gate/object fields, rectangle clipping/allocation, publication roots,
  bridge roots, render dispatch, or helper row construction.
- Checked-in documentation requirement:
  generated reports and fixtures can support the items above, but completion
  for any new edge means updating the relevant checked-in note with writers,
  readers/consumers, field classification, output effect, evidence, and exact
  unresolved boundary.

## Supported Stream Entry Points

Use this index when starting from a concrete byte stream. Each entry points to
the checked-in note that carries the parser route, state fields, page/render
objects, fixtures, evidence, and unresolved boundaries for that stream family:

- Printable text, direct controls, and cursor placement:
  `!!`, `ESC &k1G!\r!`, `ESC &a2C!`, `ESC &a72V!`,
  `ESC &a2c+1R!`, `ESC &a6l9M!`, `ESC &d3D! ESC &d@`;
  start with `Worked Path: Printable Glyph`,
  `Worked Path: Mixed Direct Controls`, `Worked Path: Cursor And Margin
  Placement`, and `Worked Path: Text Span Flush And Fixed-Width Spans` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md).
- Parser artifacts and no-output cases:
  normal `0x00` / `0x07` / `0x0b`, alternate/data blank C0 rows, `ESC ?`,
  `ESC Z`, and `ESC &lT/t`; start with
  `Worked Path: Explicit No-Output Parser Rows` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md) and
  [pcl-parser-core.md](pcl-parser-core.md).
- Transparent/display payload readers:
  `ESC &p#X...`, `ESC Y ... ESC Z`, and local Control-Z forms; start with
  [transparent-print-data.md](transparent-print-data.md),
  [display-functions.md](display-functions.md), and their worked paths in
  [firmware-dataflow-model.md](firmware-dataflow-model.md).
- Font selection and visible glyph output:
  `ESC (s0p10h12v0s0b3T!!`,
  `ESC )s0p16h8v0s0b0T SO !!`, final-`X` / final-`@` streams, and
  pitch-mode `ESC &k#S`; start with
  [font-context-metrics.md](font-context-metrics.md),
  [resource-rom.md](resource-rom.md), and `Worked Path: Font Selection To
  Visible Glyphs`. The font commands update candidate/context/map state
  through `0xc580`, `0x13eb8`, `0x144d2`, and `0x14c64`; visible output is
  produced only when later printable bytes consume those contexts through
  `0xd04a -> 0x1393a -> 0x12f2e` and publication copies both compact buckets
  and context slots through `0xff1e` / `0x1edc6`.
- Downloaded-font payloads and downloaded-glyph rendering:
  `ESC )s#W` descriptor/character streams followed by printable output or
  rule/raster composition. Start with
  [downloaded-fonts.md](downloaded-fonts.md), then follow the downloaded-glyph
  worked paths and boundaries in
  [firmware-dataflow-model.md](firmware-dataflow-model.md). The key parser
  branch is `0x11f96`: zero-count streams enter `0x15d0a`, nonzero payloads
  enter `0x16c14`, successful downloaded-character installs reach `0x16498`,
  and later printable bytes queue objects through `0x12f2e`. For row-count
  streams, low-byte rows `0x0001..0x00ff` render through the documented
  compact helpers; high-row short compact cases such as installed rows
  `0x0101..0x0103` stop at the exact `0x1fe76` fallback table boundary rather
  than claiming pixels beyond the ROM jump-table overflow. For a heterogeneous
  downloaded-glyph page image, start with `Worked Path: Downloaded Glyph
  Rule/Raster Composition`, which follows `ESC )s18W` through the byte-24
  handoff into rectangle, printable, raster, publication, bridge, and render
  dispatch.
- Raster, rectangle/rule, and mixed page-image streams:
  `ESC *t300R ESC *r0A ESC *b2W...`,
  `ESC *c12a5b0P`, and
  `! ESC *c12a5b0P ESC *t300R ESC *r0A ESC *b2W c3 3c FF`;
  start with [raster-graphics.md](raster-graphics.md),
  [rectangle-graphics.md](rectangle-graphics.md), and `Worked Path: Mixed
  Text/Rule/Raster Page Record`.
- Publication, VFC, macro replay, and status side channels:
  `! ESC E`, `ESC &k2G! FF`, `! ESC &l2X FF`, `ESC &l#W` / `ESC &l#V`,
  macro `ESC &f#X` streams, and `ESC *r1K 11`; start with
  [publication-commands.md](publication-commands.md),
  [vertical-forms-control.md](vertical-forms-control.md),
  [macro-data-chain.md](macro-data-chain.md), and
  [errors-and-status.md](errors-and-status.md).

## Current End-To-End Coverage

- Host byte source priority and callers:
  ROM evidence is `0xa904..0xabf0` in
  `generated/disasm/ic30_ic13_host_byte_fetch_00a904.lst`; the checked-in
  semantic checkpoint is [host-byte-fetch.md](host-byte-fetch.md), with
  primary entry point `Worked Path: Host Byte Source Priority` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md).
  Reproduction evidence includes fixtures for no-byte, service retry, LIFO,
  data-chain, ring, and direct modes, plus the all-caller classification
  promoted from `generated/analysis/ic30_ic13_host_byte_fetch_flow.md`.
  All `19` direct `JSR 0xa904` sites are grouped there by parser wrapper,
  `0x1a 0x58` probe, display/text readers, raster payload, downloaded-font
  payload, and macro replay data-chain behavior. The observed data-chain frame
  layout is composed with the byte-source checkpoint: `0x782d76` points at
  frame `+0x00` payload/chunk pointer, `+0x04` byte count or `-1` end marker,
  byte `+0x08 = 4`, byte `+0x09` as execute `2`, call `3`, or non-replay
  page-finalization `4`, and longword `+0x0a` as snapshot pointer or zero.
  Remaining host-input risk is physical MMIO naming/timing and any producer
  for other frame `+0x09` values, not byte-source priority, direct caller
  classification, or observed macro/data-chain replay.
- External service/status preemption:
  ROM evidence is `0xba48..0xc36e` in
  `generated/disasm/ic30_ic13_external_ready_service_loop_00ba48.lst` and
  `generated/disasm/ic30_ic13_external_service_reset_00c06e.lst`.
  Reproduction evidence is
  [external-ready-service.md](external-ready-service.md),
  `External Ready And Service Status Loop` in `notes/semantic-state-model.md`,
  and `Worked Path: External Ready Service Preemption` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md), plus fixtures for
  `0xc0ae` publishing
  `$fffee005.7/.6` through `0x9bee(0x780e2e, 0x80/0x40)`, `0xc1c6`
  entering non-returning `68 SERVICE` at `0x85c0` from
  `0x780e36 & 0x00000008`, and `0xc1c6` replaying pending buffer
  `0x782312` through `0x8c7a` when no status bits are active. This cluster
  is not a page-imaging producer, but it can stop or defer normal parsing
  before page objects are generated. The retained-storage service edge is
  software-composed in [external-ready-service.md](external-ready-service.md):
  commit/readback failure sets `0x780e39.3` through
  `0x571e -> 0x9bee(0x780e36, 0x00000008)`, and `0xc1c6` consumes the same bit
  as non-returning `68 SERVICE` through `0x85c0`. Startup retained-record load
  is the separate `0x5a16 -> 0x97e4 -> 0x56c2 -> 0x1284` path that reports
  `67 SERVICE` when no active marker is found. The teardown handoff through
  `0xc108 -> 0x19dd2 -> 0x36e4` is now bounded in
  [page-font-scheduler.md](page-font-scheduler.md) and
  `Page/Font Scheduler Handoff`: `0x19dd2` publishes scratch pointer
  `0x782894`, `0x19eb6` scans optional windows `0x200000..0x3ffffe` and
  `0x400000..0x5ffffe` when `$8000.14/15` permit it, `0x1a042` and
  `0x19f08` compare those scratch slots against canonical slots at
  `0x7828b6`, and the status branch can raise
  `0x9bee(0x780e2e, 0x00000200)` with byte `0x780e8d`. Remaining risk is the
  board-level external-register identity, the physical retained-storage
  conditions that make `0x96c4` fail through all retries or leave no startup
  active marker, and physical optional-resource contents for the changed
  optional-window scheduler sequence now modeled by
  fixture
  `0x19dd2 optional-window change composes refresh helpers`. That fixture drives
  `0x19dd2 -> 0x1ba92/0x178fa/0x19d9c/0x1a4fa/0x1a900` and checks candidate-list,
  current-record, canonical-window, and active-context effects for synthetic
  inputs; fixture `0x19dd2 modeled unchanged and status branch exits` pins the
  both-zero and `0x72a2 == 0` status-return contracts for modeled predicates.
  Physical optional-window contents remain open. Candidate-slot
  deletion/compaction through `0x1bd2e`, scanner behavior through `0x1a616`,
  teardown through `0x1887a`, active-context lookup through `0x1b4c0`, and
  font/default refresh through `0x1b04c` / `0x179aa` are documented in sibling
  semantic checkpoints. Fixture `0x447a/0x4760 consume scheduler return
  differently` now pins the host-quiesce caller contract: `0x447a` ignores
  `D7`, while `0x4760` returns immediately for `D7 = 0` and enters menu/default
  state setup for `D7 != 0`. Fixture `0xbb0a external-ready teardown ignores
  scheduler return` pins the external-ready caller contract:
  `0xc108 -> 0x19dd2 -> 0x36e4` ignores scheduler `D7` and writes `0x780e08`
  from the following status aggregate. Fixture
  `0x1a2e4 font scan ignores scheduler return` pins the font-resource-scan
  caller contract: `0x1a3b8` snapshots `0x78278e` into `0x782780`,
  `0x1a3c2` ignores scheduler `D7`, `0x1a3c8..0x1a3e0` passes
  `0x78219b/0x78219c` plus local `A6-0x02` to `0x1b50e`, and only resolver
  `D7 == 0` reaches `0x6364`.
- Host/status side channels:
  ROM evidence is `0x12034`, `0x122be..0x12326`,
  `0xb022..0xb0c0`, `0xae2c..0xaece`, and `0x2888..0x2c3a`.
  Checked-in documentation is [errors-and-status.md](errors-and-status.md),
  [io-interfaces.md](io-interfaces.md), [host-byte-fetch.md](host-byte-fetch.md),
  and the semantic checkpoints `Host Interface Output FIFO` and
  `Page Environment Status And Pool Cursor Gate` in
  [semantic-state-model.md](semantic-state-model.md), surfaced first as
  `Worked Path: Host Interface Output FIFO And Model-ID Backchannel` and
  `Worked Path: Page Environment Status Bridge` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md). This cluster has
  no direct page-object or pixel effect: `ESC *r1K 11` and the `ESC *s#^`
  sibling enqueue literal `33440A\r\n` through host-output FIFO helpers, and
  status producers such as `0x2888` feed outbound status bytes through
  `0xaece`. Fixture
  `0x12034/0x122be model-ID response emits FIFO literal` now pins both command
  entries, the `0x11efe` synthetic record, accepted query byte `0x11`,
  reject paths, and FIFO literal bytes. It still belongs in byte-stream
  reproduction because a full FIFO can stall producer `0xb090`, and a
  bidirectional host can react to the backchannel bytes by sending different
  future input.
- Parser byte and command records:
  ROM evidence is `0xda9a`, `0xdaf0`, `0xdb74`, and `0x11774`.
  The checked-in contracts are [pcl-parser-core.md](pcl-parser-core.md) and
  `Parser Record And Delayed Payload State` in
  [semantic-state-model.md](semantic-state-model.md), surfaced first as
  `Worked Path: Command Record And Payload Dispatch` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md). Supporting evidence
  is `generated/analysis/ic30_ic13_parser_xrefs.md` plus tokenizer and
  delayed-payload fixtures. The delayed-payload family matrix in that worked
  path maps command forms to arming stubs, restored handlers, state writes,
  and downstream owners. Command finals and payload bytes are separate events:
  six-byte records are saved through `0x121cc`, restored through `0x12218`,
  and then consumed by raster, transparent text, downloaded-font, generic
  payload, macro, and alternate/data handlers.
- Ignored and no-output parser rows:
  ROM evidence is parser loop `0x11774`, terminal reset path
  `0x11912..0x119bc`, delayed restore helper `0x12218`, normal parser table
  `0x112a4`, and alternate/data parser table `0x116f6`. Checked-in
  documentation is [pcl-parser-core.md](pcl-parser-core.md),
  [pcl-command-map.md](pcl-command-map.md), and `Parser Record And Delayed
  Payload State` in [semantic-state-model.md](semantic-state-model.md),
  surfaced first as `Worked Path: Explicit No-Output Parser Rows` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md). Normal mode-zero
  bytes `0x00`, `0x07`, and `0x0b` are explicit zero-handler rows: they write
  next mode `0`, run pending delayed restore through `0x12218`, reset
  `0x78299e`, `0x782a26`, `0x782a3e`, `0x782a56`, and matched-byte scratch,
  and do not allocate a page root, queue a page object, publish a record, or
  schedule render work. Alternate/data blank C0 rows `0x00` and `0x07..0x0f`
  append through `0xe002` before the same terminal reset path instead of
  running normal BS/HT/LF/FF/CR/SO/SI handlers. The alternate/data table is
  not a blanket ignore: most immediate page-state commands have blank
  handlers or lowercase `0x11f4c` rewind entries, while payload/storage
  families such as transparent data, VFC table payloads, raster rows,
  downloaded-font payloads, and macro control still execute so macro/data
  bytes remain reproducible. `ESC E` still reaches reset handler `0xcc52`.
  Related parser artifacts are bounded separately: `ESC ?` is consumed in
  wrapper `0xda9a`, `ESC Z` terminates the direct display-functions reader,
  and `ESC &lT/t` has no standalone page-output effect.
  Reproduction rule: do not treat all skipped bytes alike. Explicit normal
  zero-handler rows still preserve the `0x12218` delayed-restore boundary;
  alternate/data zero-handler rows preserve bytes through `0xe002`; unmatched
  normal bytes only become printable when the `0x782f06` / `0x782eeb`
  predicate allows the `0xd04a` fallback.
- Transparent print data:
  ROM evidence is `0x11f5a`, `0x12452`, `0xd04a`, `0xd0f0`, and `0xd550`,
  plus disassembly
  `generated/disasm/ic30_ic13_transparent_data_handler_011f5a.lst`.
  Reproduction evidence is [transparent-print-data.md](transparent-print-data.md).
  The tracked semantic contract is that `ESC &p#X` is a counted delayed
  byte-stream splice, not an opaque skip. Handler `0x11f5a` schedules
  `0x12452` through `0x121cc`; `0x12218` restores command record
  `80 58 ...`; `0x12452` consumes the absolute record word `+2` count from
  `0xa904`, preserves local `1a 58 -> 7f` and `1a xx -> xx` behavior, and
  routes normalized payload bytes through `0xd04a` or `0xd0f0` according to
  context filtering. Canonical fields are the command-record count, selected
  context slot `0x782f06`, and text cursor `0x782c8a`; parser scratch is
  `0x782a1a`, `0x782a1c`, and `0x782a20..0x782a25`; derived/filtering state
  is `0x782eea + 0x10 * 0x782f06`, `0x782efa`, and high-byte flags
  `0x783132`/`0x783133`. Remaining risk is the secondary segment-57
  resource-window continuation, tracked by
  `Boundary: Secondary Segment-57 Source` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md): fixture
  `transparent secondary segment-57 continuation policies diverge after
  verified bytes` pins glyph `0x5f`, segment `0x39`, firmware source
  `0x0bfe22`, required range `0x0bfe22..0x0c0321`, and the first `478`
  bytes inside the verified `IC32,IC15` resource-pair image. Scanner fixtures
  `0x41a HEAD scanner would duplicate records under simple resource mirror`
  and `0x41a HEAD scanner rejects non-HEAD 0x40000 continuations` constrain
  the physical continuation hypotheses. Startup checksum evidence narrows but
  does not close the edge: [firmware-startup.md](firmware-startup.md) records
  the resource-pair byte-sum range as `0x080000..0x0bffff`, so it covers the
  verified suffix but not the `0x0c0000` continuation bytes.
- Display functions:
  ROM evidence is normal handler `0x12536..0x1261e`, alternate/data handler
  `0x12120..0x1219c`, and parser-table entries in normal table `0x112a4`
  and alternate table `0x116f6`. Reproduction evidence is
  [display-functions.md](display-functions.md),
  `Display Functions ESC Y Reader` in `notes/semantic-state-model.md`,
  `ESC Y Display Functions Readers` in `notes/pcl-parser-core.md`, surfaced
  first as `Worked Path: Display Functions Direct Reader` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md), and disassembly
  `generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst`.
  The covered command-family contract is `ESC Y ... ESC Z` as a direct
  `0xa904` reader loop with local `1a 58 -> 7f` normalization, loop-local
  `ESC`-seen scratch in `D4`, normalized payload byte in `D7`, and termination
  when routed/appended `ESC Z` is seen or fetch returns `-1`. Normal handler
  `0x12536` routes normalized bytes through `0xd04a` or `0xd0f0` according to
  selected-context filtering state: canonical `0x782c18`, `0x782f06`, and
  parser dispatch state; derived/filtering state
  `0x782eea + 0x10 * 0x782f06`, `0x782efa`, `0x783132`, and `0x783133`; and
  parser scratch stack word `A6-2`. Alternate/data handler `0x12120` appends
  literal `ESC Y` plus normalized loop bytes through firmware bookkeeping sink
  `0xe002` into macro/data-chain chunk `0x783988`; normal CR output also uses
  bookkeeping helper `0xf054`. Fixtures
  `ESC Y display-functions stream reaches page-record output`,
  `ESC Y display-functions filter-on routes controls as printable`, and
  `0x12120 ESC Y alternate append stores normalized display bytes` cover the
  default-filter page-output path, nonzero context/filter page-output path,
  and alternate/data append-only path. No unresolved middle edge remains for
  this command-family loop.
- Parser dispatch tables:
  ROM evidence is normal table `0x112a4` and alternate table `0x116f6`.
  Checked-in documentation is [pcl-command-map.md](pcl-command-map.md),
  [pcl-parser-core.md](pcl-parser-core.md), and the command-family checkpoints
  in [semantic-state-model.md](semantic-state-model.md), surfaced first as
  `Worked Path: Command Record And Payload Dispatch` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md). Supporting evidence
  is `generated/analysis/ic30_ic13_pcl_command_map.md` and ROM dispatch trace
  fixtures. The `Semantic Owners` section in
  [pcl-command-map.md](pcl-command-map.md) is the current command-family index:
  it maps parser rows to checked-in notes that carry field groups, writers,
  readers/consumers, output effects, fixtures, and disassembly evidence.
- Direct controls and cursor state:
  ROM evidence includes `0xf02c`, `0xf06e`, `0xf34a`, cursor handlers
  `0xf39e` / `0xf416` / `0xf48c` / `0xf560` / `0xf60a` / `0xf692`, page
  length handler `0xf9e8`, VMI/LPI handlers `0xcb00` / `0xc992`,
  top-margin/text-length handlers `0xece2` / `0xea9e`, wrap handler
  `0xedb0`, and perforation-skip handler `0xee64`.
  Reproduction evidence is `Text Cursor And Direct Controls` in
  `notes/semantic-state-model.md`, surfaced first as
  `Worked Path: Mixed Direct Controls` and
  `Worked Path: Cursor And Margin Placement` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md), plus host-fetched
  direct-control fixtures. Layout-control evidence is surfaced first as
  `Worked Path: Page Length, Wrap, And Perforation Controls`: `ESC &l#P`
  writes page extent `0x782dba`, `ESC &l#C/#D` writes line advance
  `0x783160`, `ESC &l#E` writes top offset `0x782dce`, `ESC &l#F` writes
  bottom/text-length state, `ESC &s#C` writes end-of-line wrap flag
  `0x783190`, and `ESC &l#L` writes perforation-skip byte `0x783191`.
  Those commands normally do not draw immediately; their visible effect is
  through later LF/FF and cursor helpers, printable prechecks `0xd28a` /
  `0xd6bc`, VFC, vertical overflow helper `0xf36c`, or the following
  printable path `0xd04a -> 0x12f2e`.
- Text source object creation:
  ROM evidence is `0xd3b2`, `0xd824`, `0x12f2e`, and `0x1387c`.
  Reproduction evidence is `Text Source Objects And Compact Buckets` in
  `notes/semantic-state-model.md`, surfaced first as
  `Worked Path: Text Source Objects And Compact Buckets` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md), plus compact text
  bucket render fixtures.
- Pending text span flushing:
  Pending text span state is the canonical RAM block
  `0x783184..0x78318a`: enable byte `0x783184`, low-x watermark
  `0x783186`, high-x watermark `0x783188`, and high-y watermark
  `0x78318a`.
  Helper `0x126e2` opens or re-arms that block from current x `0x782c8a`.
  Printable consumers `0xd4ac` and `0xd8fc` extend it from selected font
  context metrics, and shared flush helper `0xf34a` plus low-water branches in
  those consumers materialize it through `0x12714`.
  `0xd4ac` reads unflagged context bytes `+0x2b`, `+0x2c`, and `+0x2d`;
  `0xd8fc` reads flagged context words `+0x16`, `+0x18`, and `+0x1a`.
  The parser-facing writers that show the same pending block can become
  visible output are CR `0xf02c`, left-margin command handler `0xeb58`, and
  vertical-cursor command handler `0xf560`.
  Flush output is orientation-dependent: portrait `0x12714` calls
  `0x13520` / `0x1354a` / `0x135f0` to write selector-`0x4000`
  segment-list objects under page-root `+0x1c`, consumed by renderer
  `0x1f812`; landscape reaches `0x136d2` to write fixed-width objects under
  page-root `+0x28`, bridged by `0x1edc6` to render root `+0x20` and consumed
  by `0x1f756` / `0x1f7b0`.
  Derived/cache fields are the local 8-byte `0x12714` source and producer key
  fields `0x782a7c..0x782a7e`; parser scratch is limited to the command
  records that cause `0xf34a` or `0x12622` to flush; firmware bookkeeping is
  the root ensure path `0x10084`, allocation cursors, and the
  allocation-failure publish/retry bit in page-root `+0x14`.
  Concrete output evidence includes the fixtures `0x12714 portrait text span
  flush queues segment-list span`, `0x12714 landscape text span flush queues
  fixed-width span`, `live CR span flush materializes 0x12714 page object`,
  `left-margin parser span flush materializes 0x12714 page object`,
  `vertical-cursor parser span flush materializes 0x12714 page object`,
  `flagged printable d8fc low-watermark flush renders span`, `unflagged
  printable d4ac low-watermark flush renders span`,
  `0x1354a portrait text span split queues adjacent buckets`,
  `0x12714 landscape span inserts into nonempty fixed list`, and
  `0x12714 allocation failure publishes page and retries span`.
  Checked-in evidence is `Text Span Flush And Fixed-Width Spans` in
  [semantic-state-model.md](semantic-state-model.md), `Worked Path: Text Span
  Flush And Fixed-Width Spans` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md),
  [font-context-metrics.md](font-context-metrics.md), and
  [page-record-storage.md](page-record-storage.md).
  Confidence is high for the pending state writers, metric gates, object byte
  shapes, orientation split, bridge shape, and rendered rows because each has
  disassembly support plus fixture checks.
  No unresolved ROM-local middle edge remains for this pending-span-to-page
  object handoff; remaining work is selected-font or byte-stream variants that
  change source-object fields, unflagged/flagged metric fields, pending span
  bounds, `0x12714` page-extent acceptance, orientation branch, page-object
  fields, bridge roots, or rendered rows.
- Page-root storage:
  The shared page-object state starts at current root pointer `0x78297a`.
  Canonical root fields are bucket heads `+0x1c` for compact text,
  segment-list spans, and encoded raster; stream chunk head `+0x20`;
  rule-list head `+0x24`; fixed-list head `+0x28`; current font/context slots
  `+0x2c..+0x68`; and root state byte `+4`, initialized as current state `1`
  and published as state `2`.
  `0x10084` ensures or allocates the root, seeds stream pointer
  `0x782a72 = root + 0x20`, calls initializer `0x10110`, clears transient
  byte `0x782990`, and zeroes the 256 bucket heads.
  `0x1381c` is the shared variable-size object allocator: it writes allocator
  cursors `0x782a70`, `0x782a72`, and `0x782a76`, and links fresh 0x100-byte
  chunks when the current chunk cannot satisfy a producer.
  Producer families share that storage: `0x12f2e` / `0x1387c` write compact
  text and glyph entries under root `+0x1c`; `0x12714` / `0x13520` /
  `0x135f0` write portrait segment-list spans under `+0x1c`; `0x13070` /
  `0x13250` write encoded-raster objects under `+0x1c`; `0x13386` /
  `0x133aa` write ordered rule nodes under `+0x24`; and `0x136d2` writes
  fixed-list or landscape span nodes under `+0x28`.
  Derived/cache state is producer key state `0x782a7a..0x782a7e`, allocator
  cursors, and bridge/render caches such as `0x783a20`, `0x783a22`, and
  `0x783a28`.
  Parser scratch ends at the producer boundary: six-byte command records,
  delayed raster payload snapshots, and printable bytes are no longer
  consulted after the page objects are queued.
  Firmware bookkeeping is publication flag `0x782996`, root state byte `+4`,
  no-room/retry bits such as root flag word `+0x14`, allocator failure
  returns, and render-work progress fields.
  Publication `0xff1e` consumes the current root, copies its roots and header
  fields into the page/control pool, writes pool head `0x780ea6`, sets
  `0x782996`, and clears `0x78297a`.
  Render bridge `0x1ed84` selects the page/control source; `0x1edc6` copies
  source `+0x1c` to render `+0x18`, `+0x24` to render `+0x1c`, `+0x28` to
  render `+0x20`, and context slots `+0x2c..+0x68` to render
  `+0x24..+0x60`.
  The storage layer has no pixels by itself, but it determines which objects
  exist, their list order, and which render dispatcher later consumes them:
  compact and raster bucket dispatch through `0x1efc2`, segment-list spans
  through `0x1f812`, rules through `0x1f446`, and fixed-list rows through
  `0x1f756`.
  Concrete output evidence includes fixtures `0x10084-modeled page-root
  allocation side effects`, `0x10110 page-root initializer installs selected
  context slot`, `0x1381c stream allocator chunks display-list storage`,
  `0x1387c address-aware bucket allocation uses 0x1381c storage`,
  `addressed page-record writers share 0x1381c across chunk rollover`,
  `addressed text/rule/raster field groups reach publication and render
  entry`, `addressed stream page record materializes through 0xff1e and
  0x1ed84`, `0x1edc6 page-record bridge copies compact bucket and context
  slots`, and `0x1edc6 page-record bridge normalizes rule and fixed lists`.
  Checked-in evidence is [page-record-storage.md](page-record-storage.md),
  `Shared Page-Record Storage And Allocator` in
  [semantic-state-model.md](semantic-state-model.md), and `Worked Path: Shared
  Page-Record Storage And Allocator` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md).
  Confidence is high for first-root setup, shared stream allocation, producer
  roots, chunk rollover, no-room preservation, publication, bridge copies, and
  render-dispatch ownership because the cited fixtures cover multiple writer
  families and the shared consumers.
  No unresolved ROM-local producer-to-root-to-render mapping remains for the
  listed object classes; remaining work starts from byte streams that create a
  new object shape, root field, bridge value, continuation state, or rendered
  row.
- Rule/rectangle producers:
  Rectangle commands enter from `ESC *c` parser records and converge at
  `0x10898` for `ESC *c#P`.
  Canonical command fields are rectangle width `0x78316a`, rectangle height
  `0x783166`, and area-fill id `0x78316e`; writers are dot-size handlers
  `0x10e68` / `0x10e22`, decipoint handlers `0x10a40` / `0x10ae0`, and
  area-fill handler `0x10dce`.
  `0x10898` maps fill parameters to selector `7` for solid black,
  gray-percent selectors `0..7`, and pattern selectors `8..13`, with
  landscape pattern remaps `1 -> 9`, `2 -> 8`, `3 -> 11`, and `4 -> 10`.
  `0x10b80` consumes cursor `0x782c8a` / `0x782c8e`, orientation
  `0x782da3`, extents `0x782db8` / `0x782db6`, and the stored dimensions to
  reject off-page rectangles, clip negative or overrun edges, and write source
  record `0x782a88`: x, y, width, height, and fill selector.
  `0x13386` derives rule keys through `0x134d6`; `0x133aa` allocates a
  14-byte object through `0x1381c` and inserts it under page-root `+0x24` in
  ordered bucket/key position.
  Canonical rule object fields are next pointer `+0`, bucket byte `+4`,
  selector byte `+5`, packed key `+6`, width `+8`, height `+0x0a`, and
  continuation height `+0x0c`.
  Derived/cache state is producer key state `0x782a7c`, `0x782a7d`, and
  `0x782a7e`; parser scratch is only the six-byte command record cursor
  `0x78299e` that the handlers rewind before reading the parsed record.
  Firmware bookkeeping is shared stream allocator state
  `0x782a70/0x782a72/0x782a76` and retry flag bit page-root `+0x15.0`: if
  `0x13386` returns zero, `0x10d22..0x10d3e` marks the root, publishes through
  `0xff1e`, ensures a fresh root through `0x10084`, and retries the same
  source record.
  Bridge `0x1edc6` copies page-root `+0x24` to render-record `+0x1c`, ORs
  object byte `+5` with `0x10`, and copies height `+0x0a` into continuation
  field `+0x0c`.
  Renderer `0x1ef6a` calls rule-list dispatcher `0x1f446` after bucket
  dispatch `0x1efc2`; selector `7` reaches solid helper `0x1f596`, while
  selectors `0..6` and `8..13` reach pattern helper `0x1f4e0`.
  Those helpers consume packed key, width, and continuation height and mutate
  continuation state across render bands.
  Concrete output evidence includes fixtures `rectangle command stream queues
  chained ESC *c rule object`, `0x11774 ROM dispatch table routes chained
  ESC *c rule stream`, `0x10898 ESC *c#P maps fill selectors and queues rule
  object`, `0x10b80 rectangle fill clips negative left edge before queueing`,
  `0x10b80 rectangle fill clips right/top/bottom edges and ignores off-page
  fills`, `0x13386/0x133aa-modeled rectangle/rule list object and bridge
  normalization`, `0x133aa address-aware rule-list insertion uses 0x1381c
  storage`, `0x133aa no-room return preserves rule-list head`, `0x1f446/0x1f596
  renders solid black rectangle rule pixels`, `0x1f596 carries solid rule
  remainder across render bands`, `0x1f4e0 renders gray and HP pattern
  selector matrix`, `0x1f4e0 carries patterned rule remainder across render
  bands`, `0x1f4e0 renders sub-byte shifted HP pattern rule pixels`,
  `host-fetched alternate rectangle selectors feed full page records`, and
  `host-fetched rectangle selector matrix feeds full page records`.
  Checked-in evidence is [rectangle-graphics.md](rectangle-graphics.md),
  `Rectangle Rule Producer And Renderer` in
  [semantic-state-model.md](semantic-state-model.md), and `Worked Path:
  Rectangle Rule` plus `Worked Path: Rectangle Rule Selectors And Clipping` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md).
  Confidence is high for parser handler order, selector mapping, clipping and
  reject gates, source-record bytes, rule object bytes, ordered insertion,
  bridge normalization, solid/pattern dispatch, band continuation, and no-room
  retry output.
  No unresolved software-visible middle edge remains for the covered
  selector-7, gray, pattern, landscape-remap, clipping, no-room, addressed
  storage, publication, and mixed text/rule/raster streams.
  Remaining work is limited to byte streams that change clipping output,
  `0x1381c` rollover/allocation state, retry publication fields, rule object
  bytes, bridge state, render dispatch, or rendered rows.
- Raster producers:
  ROM evidence is `0x10808`, `0x1075a`, `0x105d0`, `0x13070`, and
  `0x13250`.
  The checked-in command-family checkpoint is
  [raster-graphics.md](raster-graphics.md), with semantic checkpoint
  `Raster Transfer Gate And Encoded Rows` in
  [semantic-state-model.md](semantic-state-model.md), surfaced first as
  `Worked Path: Raster Row` and
  `Worked Path: Raster Transfer Gates And Modes` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md). Supporting evidence
  is `generated/analysis/ic30_ic13_raster_graphics_flow.md` and host-fetched
  raster stream fixtures. The checkpoint covers lower-resolution modes `1..3`,
  consecutive uppercase `ESC *b#W` transfers, lowercase `ESC *b#w` same-family
  chaining, `ESC *rB` active-byte clear, active-resolution ignore, `0x105d0`
  cap/drain gates, page-record object bytes, bridge dispatch, and rendered rows.

  The mixed page-image cluster is now composed in `Mixed Text/Rule/Raster Page
  Record`: fixture
  `host-fetched text rectangle raster FF publishes rendered page record`
  drives `! ESC *c12a5b0P ESC *t300R ESC *r0A ESC *b2W c3 3c FF` from the
  modeled `0xa904` host source through parser handlers, delayed `0x105d0`,
  `0xff1e`, `0x1ed84`/`0x1edc6`, and ROM-derived row construction. Fixture
  `addressed text/rule/raster field groups reach publication and render entry`
  names the same materialized objects: text object `0x00d0c004`, rule object
  `0x00d0c02a`, raster object `0x00d0c038`, restored raster record
  `80 57 00 02 00 00`, payload `c3 3c` at offset `28`, stream allocator
  bookkeeping `0x782a70 = 0x00bc`, `0x782a72 = 0x00d0c000`,
  `0x782a76 = 0x00d0c044`, and render caches `0x783a20 = 0x0050`,
  `0x783a22 = 0`, `0x783a28 = 0x00100000`. Fixture
  `addressed text/rule/multi-row raster publication preserves bucket chain`
  covers the sibling with two delayed raster transfers, raster objects
  `0x00d0d038` and `0x00d0d044`, bucket chain
  `0x00d0d044 -> 0x00d0d038 -> 0x00d0d004`, allocator bookkeeping
  `0x782a70 = 0x00b0`, `0x782a72 = 0x00d0d000`,
  `0x782a76 = 0x00d0d050`, and final raster row counter `2`.

  The current handoff ledger pins field ownership across `0x105d0`,
  `0x10084`, `0x13070`, `0x13250`, and `0x132b6`: `A4 = 0x783170`,
  restored record `A5 = 0x78299e - 6`, accepted/overflow words
  `+0x04/+0x06`, row word `+0x02`, current root `0x78297a`, bucket/key caches
  `0x782a7c/0x782a7e`, stream chunk state `0x782a70/0x782a76/0x782a80`, and
  copy-stop flag `0x782996`. No remaining ROM semantic boundary is assigned to
  that handoff. Further ROM work should target streams that change the
  `0x105d0 -> 0x10084 -> 0x13070 -> 0x13250 -> 0x132b6` gate outcome,
  raster-object fields, bridge state, render dispatch, or reproduction
  contract.
- Page publication:
  Publication is the page-object-to-page/control-record boundary at
  `0xff1e..0x10080`.
  The canonical input is current page root `0x78297a`, including compact bucket
  root `+0x1c`, rule-list root `+0x24`, fixed-list root `+0x28`, context slots
  `+0x2c..+0x68`, state byte `+4`, copy-count/environment header fields, and
  retry/finalization flags.
  `0xff1e` writes page/control pool state byte `+4 = 2`, copies the current
  root into the published pool, writes pool-head pointer `0x780ea6`, sets
  publication flag `0x782996`, and clears current-root pointer `0x78297a`.
  The checked command-family streams are `! ESC E`, `ESC &k2G! FF`,
  `! ESC &l1A`, `! ESC &l1O`, `! ESC &l2H`, and `! ESC &l2X FF`.
  Their writers are reset handler `0xcc52` / `0xcc70`, FF handler `0xf0f0`,
  page-size handler `0xfc74`, orientation handler `0x10220`, paper-source
  handler `0xef62`, and copies handler `0xeef0`.
  The semantic ordering is byte-stream visible: reset, page-size,
  orientation, and paper-source publish already queued page objects before
  they mutate the default environment, geometry, orientation, or paper-source
  state; FF publishes after the `ESC &k2G` line-termination mode applies its
  CR-style x reset; copies stores `0x782da4` before the following FF
  publication copies it into pool-header word `+0x0c`.
  Parser scratch is temporary command records and the modeled `0xa904` host
  ring bytes; after the handlers queue page objects, publication consumes
  page-root fields rather than parser records.
  Derived/cache state includes render-band caches `0x783a20`, `0x783a22`, and
  `0x783a28`, which appear only after `0x1ed84` / `0x1edc6` bridge the
  published record.
  Firmware bookkeeping includes stream allocator state
  `0x782a70/0x782a72/0x782a76`, publication flag `0x782996`, transient byte
  `0x782990`, pool header defaults, and command-specific header copies such
  as copy count `+0x0c`.
  Downstream consumers are active-record bridge `0x1ed84`, page-record bridge
  `0x1edc6`, and render entry `0x1ef6a`; the covered streams dispatch the
  preserved compact Line Printer `!` object through compact renderer
  `0x1effe`.
  Concrete output evidence includes fixtures `publication streams tie parser
  handlers to page-record publication boundary`, `host-fetched publication
  streams reach parser and published rows`, `host-fetched publication streams
  preserve 0x1edc6 bridge contract`, `published page records feed 0x1ed84 and
  0x1ef6a render entry`, `mixed printable/reset stream keeps pre-reset text
  rows renderable`, `mixed printable/FF page-record stream publishes queued
  text`, `addressed printable reset publishes rendered page record`,
  `addressed printable FF publishes rendered page record`, `addressed page
  geometry publications render page records`, `addressed paper-source and
  copies publications render page records`, `host-fetched ESC E clears
  missing page root without publication`, and `host-fetched copies publication
  preserves 0xeef0 pool header word`.
  Checked-in evidence is [publication-commands.md](publication-commands.md),
  `Publication Commands To Rendered Page Records` in
  [semantic-state-model.md](semantic-state-model.md), and `Worked Path: Reset
  And Default Environment`, `Worked Path: FF Publication`, and `Worked Path:
  Publication Commands To Rendered Page Records` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md).
  Confidence is high for parser handler order, pre-command object preservation,
  reset/FF/geometry/paper-source/copies side-effect ordering, pool-header
  defaults and copy-count field, current-root clearing, bridge preservation,
  and rendered rows.
  The unresolved boundary is not ROM-local publication state: final rows are
  documented through `0xff1e -> 0x1ed84 -> 0x1edc6 -> 0x1ef6a`, with
  fixtures serving as model-consistency checks for those interpreted rows.
  Remaining work is byte streams that expose a new pool-header field,
  source-record choice, bridge value, or rendered row.
- Macro/data-chain replay:
  ROM evidence is `0xe112`, `0xdd08`, `0xe0a4`, `0xe002`, `0xe418`,
  `0xe4f4`, `0xe22c`, `0xe65c`, byte-source multiplexer `0xa904`, parser loop
  `0x11774`, and publication branch `0xff1e..0xff8e`. Checked-in
  documentation is [macro-data-chain.md](macro-data-chain.md) and
  `Macro Definition And Data-Chain Replay` in
  [semantic-state-model.md](semantic-state-model.md), surfaced first as
  `Worked Path: Macro Execute Replay` and
  `Worked Path: Macro Overlay Replay Publication` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md). The covered
  execute/call path defines macro id `123`, stores payload `21 0d`, builds a
  data-chain frame with `+8 = 4` and frame kind `+9 = 2` or `3`, lets
  `0xa904` replay the stored bytes ahead of live input, and routes them back
  through normal parser handlers `0xd04a` and `0xf02c` to the same compact text
  page object and render path as live host bytes. The overlay path stores
  selector state `0x782a92/0x782a94`; `0xff1e` resolves the saved record,
  builds a non-replay frame through `0xe4f4`, re-enters parser loop `0x11774`,
  and queues replayed text, controls, transparent payloads, spans, or raster
  objects before the page is published.
- Render bridge:
  The render bridge is the copied-record boundary from active source
  `0x780eae` into the render work record selected at `0x783a18`.
  Entry `0x1ed84` consumes source header words and source roots from
  `0x780eae`, seeds render header words from source `+0x18/+0x1a`, and then
  delegates queue/list/context copying to `0x1edc6`.
  `0x1edc6` copies source bucket root `+0x1c` to render `+0x18`, source
  rule-list root `+0x24` to render `+0x1c`, source fixed-list root `+0x28` to
  render `+0x20`, and context slots `+0x2c..+0x68` to render
  `+0x24..+0x60`.
  Rule and fixed-list objects are normalized during this bridge: rule selector
  byte `+5` is ORed with `0x10`, rule height `+0x0a` is copied into
  continuation `+0x0c`, and fixed-list continuation/count fields are prepared
  for `0x1f756`.
  Canonical render roots after the bridge are render `+0x18` for compact,
  segment-list, and encoded-raster bucket objects; render `+0x1c` for
  rule-list objects; render `+0x20` for fixed-list objects; and render
  `+0x24..+0x60` for font/resource contexts.
  Derived/cache state includes render-band fields later written by `0x1ef86`
  (`0x783a20`, `0x783a22`, `0x783a28`), render stride `0x783a1c`, and
  bridge-normalized continuation fields; parser scratch is none because parser
  records have already become page objects before publication.
  Downstream consumer `0x1ef6a` reads `0x783a18`, calls `0x1ef86`, dispatches
  render `+0x18` through `0x1efc2`, render `+0x1c` through `0x1f446`, and
  render `+0x20` through `0x1f756`.
  Concrete output evidence includes fixtures `0x1ed84 active page-record copy
  seeds render-record header words`, `0x1edc6 page-record bridge copies
  compact bucket and context slots`, `0x1edc6 page-record bridge normalizes
  rule and fixed lists`, `0x1edc6 bridge records render-record destination
  offsets`, `published page records feed 0x1ed84 and 0x1ef6a render entry`,
  and mixed text/rule/raster bridge fixtures.
  Checked-in evidence is [page-record-storage.md](page-record-storage.md),
  [page-raster-imaging.md](page-raster-imaging.md),
  `Shared Page-Record Storage And Allocator`,
  `Published Record To Active Render Scheduler`, and
  `Bitmap Render Dispatch Contract` in
  [semantic-state-model.md](semantic-state-model.md), surfaced first as
  `Worked Path: Published Record To Active Bands` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md).
  Confidence is high for source-root copying, context-slot copying,
  rule/fixed normalization, render-root ownership, and ROM-derived row-write
  paths after the bridge.
  No unresolved ROM-local bridge edge remains for the documented compact,
  segment-list, encoded-raster, rule, and fixed-list objects; remaining work
  starts from byte streams that change source record fields, bridge-normalized
  values, or row-write paths.
- Active render scheduler:
  The active render scheduler is the software-visible path from a published
  page/control record to render-band calls.
  Canonical pool state is protected published head `0x780ea6`, scheduler
  cursor `0x780eaa`, active source `0x780eae`, release cursor `0x780eb2`, and
  engine/status counter `0x780e04`.
  Pool initialization `0x3144..0x3162` seeds those cursors; candidate staging
  and release paths `0x1c04..0x2016` populate `0x780e6e[]`; candidate
  selection `0x7ec6..0x7f90` promotes a selectable record into
  `0x780eaa/0x780eb2`; cursor path `0x7722..0x779a` advances or releases
  cursors while protecting `0x780ea6`.
  Active scheduler entry `0x1eb32..0x1eb50` copies `0x780eaa` into
  `0x780eae`.
  Canonical render-work state is two-work-record selector bytes `0x7820bc`
  and `0x7820c0`, paired records `0x7820c4` and `0x782128`, and active render
  pointer `0x783a18`; startup `0x2feb6` initializes selector state, and
  `0x1ecd6..0x1ed76` alternates the destination record, writes `0x783a18`,
  initializes geometry through `0x1ee9e` when needed, or reuses
  same-geometry fields through helper `0x33238` before calling `0x1ed84`.
  Derived/cache state is band rows `0x783a20`, remainder `0x783a22`,
  destination base `0x783a28`, stride `0x783a1c`, same-geometry destination
  word `+8`, row-copy pointers/scalars such as `0x783992`,
  `0x7839a0`, `0x7839a4`, `0x7839a8`, `0x7839ac`, and status latches
  `0x78399e/0x78399f/0x78398c`.
  Firmware bookkeeping includes active flags `0x780ea4/0x780ea5`, candidate
  slots `0x780e6e[]`, record state byte `+4`, wait-object records rooted at
  `0x780182`, scheduler pending bits `0x78017e`, timer/status dividers
  `0x78017f..0x780181`, and copied RAM trap/vector stubs
  `0x780000..0x780173`.
  The active band loop `0x1eba4..0x1ecd2` consumes active and paired
  work-record fields `+0x06`, `+0x0c`, `+0x0e`, `+0x10`, and `+0x16`.
  It cleans up when `0x780ea5` is set or `+0x0c < +0x10`, throttles when
  `+0x0e > 0x28`, waits when computed capacity is below `9`, and otherwise
  calls `0x1ef6a` before incrementing render band word `+0x10` and throttle
  word `+0x0e`.
  Hardware/external state is the MMIO-facing timing surface around `$8000`,
  `$8a01`, `$a200`, `$a400`, `$a801`, and `0xffff2000`: the firmware-visible
  latches and wait-object effects are documented, but exact board-signal names
  remain outside this ROM-local scheduler checkpoint.
  Concrete output evidence includes fixtures `0x1eb2a/0x1ecd6 selects
  published record for render entry`, `0x1ecd6 same-geometry render work reuse
  reaches render entry`, `0x3144/0x7ec6/0x7712 page pool aliases feed
  scheduler cursor`, `0x1958/0x1c04/0x1eea staged candidate reaches render
  scheduler`, `0x2126/0x1a4c/0x2038 active pool copy window feeds engine
  rows`, `0x0fa2/0x1db0/0x1e44 status feedback drives copy and done flag`,
  `0x1036/0x108e/0x123a wait-object scheduler handoff`,
  `0x1144..0x11f8 scheduler trap handlers update wait objects`,
  `0x1cf8/0x1e80/0x1ea8 wrapper dispatch selects engine variants`,
  `0x1eba4/0x1ef6a active render loop advances or yields bands`, and
  `0x1eba4 scheduler band words render published downloaded glyph`.
  Checked-in evidence is
  [active-render-scheduler.md](active-render-scheduler.md),
  `Published Record To Active Render Scheduler` in
  [semantic-state-model.md](semantic-state-model.md), and `Worked Path:
  Published Record To Active Bands` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md).
  Confidence is high for pool-head versus cursor roles, candidate selection,
  `0x780eaa -> 0x780eae`, work-record alternation, `0x783a18`,
  same-geometry reuse, active-loop branches, wait-object transitions, and
  the ROM-local path from scheduler-produced band words to render-entry
  calls.
  Remaining edges are bounded hardware/MMIO timing and naming edges:
  `0x0d52..0x0f7a`, `0x0f84..0x102e`, `0x10bc..0x1282`, and
  `0x1cf8..0x1ea8` are modeled as firmware-visible scheduler and wait-object
  state, but not yet mapped one-to-one to formatter/DC connector signals.
- Render dispatch:
  Render dispatch starts after the scheduler has selected active render record
  pointer `0x783a18` and the bridge has copied page roots into render roots.
  The fixed call order is `0x1ef6a -> 0x1ef86 -> 0x1efc2 -> 0x1f446 ->
  0x1f756`: band-cache setup, bucket-chain dispatch, rule-list dispatch, and
  fixed-list dispatch.
  Canonical render roots are render `+0x18` for compact, segment-list, and
  encoded-raster bucket chains; render `+0x1c` for rule-list objects; render
  `+0x20` for fixed-list objects; and render `+0x24..+0x60` for context or
  resource slots.
  Canonical bucket object fields are next pointer `+0`, class byte `+0x04`,
  context/mode byte `+0x05`, count/capacity word `+0x06`, packed coordinate
  word `+0x08`, and payload `+0x0a..`.
  Class byte `+0x04` selects compact glyph/text objects `0x00..0x3f` through
  `0x1effe`, segment-list objects `0x40..0x7f` through `0x1f812`, and encoded
  raster objects `0x80..0xff` through `0x1f88e`.
  Compact subdispatch uses `+0x04` bits `0x10` and `0x20` to select
  `0x1f034`, `0x1f0d2`, `0x1f1f0`, or `0x1f264`; compact payload entries
  start with a glyph/resource byte consumed by `0x1f354`.
  Encoded raster mode byte `+0x05 & 3` selects literal mode `0`, byte-to-word
  expansion mode `1`, byte-to-long expansion mode `2`, or cascaded expansion
  mode `3`.
  Canonical rule/fixed fields are bridged rule selector `+0x05`, packed key
  `+0x06`, width `+0x08`, original height `+0x0a`, continuation height
  `+0x0c`, and fixed-list fields `+0x04..+0x0d`; `0x1f446` sends selector
  `7` to solid helper `0x1f596` and selectors `0..6` / `8..13` to pattern
  helper `0x1f4e0`, while `0x1f756` consumes fixed-list rows through
  `0x1f7b0`.
  Derived/cache render state is band split count `0x783a20`, band remainder
  `0x783a22`, destination base `0x783a28`, stride `0x783a1c`, offset table
  `0x7839f8..`, phase byte `$a001`, compact context cache `0x783a2c`,
  compact row-copy phase `0x783a46`, and fallback buffer base `0x7810b4 + D2`.
  Destination helpers `0x1f3d4`, `0x1f414`, and `0x1f626` decode packed
  coordinates into row index, subbyte phase, byte-pair offset, current-band
  rows, and fallback rows.
  Parser scratch is none at this layer; upstream producers have already
  reduced parser records and payload bytes to page-record objects.
  Firmware bookkeeping is continuation/count mutation in rule `+0x0c`,
  fixed-list `+0x0a`, bucket object counters, object next pointers, and
  scheduler-maintained active-band progress.
  Pixel composition at this layer is order-dependent direct destination
  writing: compact, raster, segment-list, rule, and fixed-list helpers store
  generated source words into the active band or fallback buffer; the
  documented helpers do not OR/XOR/AND new pixels with prior destination
  contents.
  Reproduction rule: execute the band in ROM call order, use `0x783a28` plus
  offset table `0x7839f8..` for current-band destinations, use
  `0x7810b4 + D2` only for documented fallback rows, and treat later direct
  stores as overwrites rather than logical blends.
  Writers are page producers `0x12f2e` / `0x1387c`, `0x12714` /
  `0x13520` / `0x135f0`, `0x13070` / `0x13250`, `0x13386` / `0x133aa`, and
  `0x136d2`; bridge writer `0x1edc6`; band-cache writer `0x1ef86`; and row
  writers `0x1f034`, `0x1f0d2`, `0x1f1f0`, `0x1f264`, `0x1f4e0`,
  `0x1f596`, `0x1f756`, `0x1f812`, and `0x1f88e`.
  Concrete output evidence includes fixtures `0x1ef86 render band setup
  computes remainder and destination base`, `0x1efc2 bucket-chain dispatcher
  selects bucket and object classes`, `0x1ef6a render entry composes bucket,
  rule, and fixed-width lists in call order`, `0x1ef6a page-band walk merges
  text raster and crossing rule`, `bridged text, rule, and raster layers
  compose into one page band`, `parser-driven downloaded glyph rule raster
  stream composes through 0x1ef6a`, `0x1f812 segment-list object renders
  counted mask spans`, `0x1f756 fixed-width list renders bridged +0x20
  object`, `0x1f446/0x1f596 renders solid black rectangle rule pixels`,
  `0x1f4e0 renders gray and HP pattern selector matrix`, encoded raster
  fixtures `0x1f88e mode-0` through `mode-3`, and compact fixtures for
  `0x1f034`, `0x1f0d2`, `0x1f1f0`, and `0x1f264`.
  Checked-in evidence is the `Bitmap Object Dispatch Semantic Checkpoint` and
  `Compact Glyph Row-Copy Semantic Checkpoint` in
  [page-raster-imaging.md](page-raster-imaging.md),
  `Bitmap Render Dispatch Contract` in
  [semantic-state-model.md](semantic-state-model.md), and `Worked Path: Render
  Dispatch And Pixel Composition` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md).
  Confidence is high for render-root ownership, call order, bucket class split,
  compact subdispatch, segment-list layout, encoded raster modes, rule/fixed
  selectors, destination arithmetic, row-copy table targets, and row-level
  output for the cited fixtures.
  No unresolved shared render-dispatch edge remains for the documented object
  classes. Remaining ROM-local work starts from byte streams that create
  different object fields, selected-font contexts, helper targets,
  continuation state, fallback split, or rendered rows.
- Mixed page-image stream:
  The primary heterogeneous page-image stream is
  `! ESC *c12a5b0P ESC *t300R ESC *r0A ESC *b2W c3 3c FF`.
  It documents that no single command draws the final image: parser handlers
  first queue compact text, rectangle/rule, and encoded-raster objects under
  one page root; `0xff1e` publishes the root; `0x1ed84` / `0x1edc6` bridge it
  into a render record; and `0x1ef6a` composes the visible rows.
  Host bytes enter through `0xa904` and parser loop `0x11774`.
  Printable `!` reaches `0xd04a`, source helper `0x1393a`, positioning
  `0xd824`, root ensure `0x10084`, and compact queue
  `0x12f2e -> 0x1387c`.
  `ESC *c12a5b0P` reaches `0x10e68`, `0x10e22`, and final fill handler
  `0x10898`, which queues selector-7 rule data through `0x10b80`,
  `0x13386`, and `0x133aa`.
  `ESC *t300R` reaches `0x10808`, `ESC *r0A` reaches `0x1075a`, and
  `ESC *b2W` reaches `0x11f82`, which schedules delayed transfer handler
  `0x105d0` through `0x121cc`; terminal restore `0x12218` reinstalls record
  `80 57 00 02 00 00`, then `0x105d0` consumes payload `c3 3c` and queues a
  mode-0 encoded raster object through `0x13070` / `0x13250`.
  Canonical page-record state in the addressed fixture is text object
  `0x00d0c004`, rule object `0x00d0c02a`, raster object `0x00d0c038`,
  bucket root `+0x1c`, rule-list root `+0x24`, and context slot `+0x2c =
  0x440946b4`.
  Published bucket bytes include encoded object
  `00 d0 c0 04 80 00 00 02 00 00 c3 3c`; published rule bytes are
  `00 00 00 00 01 07 5c 01 00 0c 00 05 00 00`.
  Parser scratch is the delayed raster snapshot
  `01 00 01 05 d0 80 57 00 02 00 00`, restored transfer record
  `80 57 00 02 00 00`, payload offset `28`, and payload bytes `c3 3c`.
  Firmware bookkeeping is stream allocator state
  `0x782a70 = 0x00bc`, `0x782a72 = 0x00d0c000`,
  `0x782a76 = 0x00d0c044`, one stream allocation, one page-root allocation,
  one publication, one current-root clear, and publication flag `0x782996`.
  Derived/cache render state includes `0x783a20 = 0x0050`,
  `0x783a22 = 0`, and `0x783a28 = 0x00100000`.
  Downstream consumers are `0xff1e`, bridge `0x1ed84` / `0x1edc6`, bucket
  dispatch `0x1efc2`, raster renderer `0x1f88e`, compact renderer
  `0x1effe`, rule dispatcher `0x1f446`, and solid rule helper `0x1f596`.
  The consecutive-raster sibling
  `! ESC *c12a5b0P ESC *t300R ESC *r0A ESC *b2W f0 0f ESC *b2W 0f f0 FF`
  documents bucket-chain ordering for repeated delayed raster transfers:
  addressed raster objects at `0x00d0d038` and `0x00d0d044` publish as chain
  `0x00d0d044 -> 0x00d0d038 -> 0x00d0d004`, allocator state ends at
  `0x782a70 = 0x00b0`, `0x782a72 = 0x00d0d000`,
  `0x782a76 = 0x00d0d050`, and final raster `row_y = 2`.
  The page-band walker fixture extends the same render-entry contract across
  bands `0` and `5`: compact text and mode-0 raster dispatch from render
  bucket root `+0x18`, a patterned rule mutates and carries via rule root
  `+0x1c`, and the second band renders the remaining rule rows with no
  leftover rule or fixed-list state.
  Concrete output evidence includes fixtures `host-fetched text rectangle
  raster FF publishes rendered page record`, `addressed text rectangle raster
  FF publishes rendered page record`, `addressed text/rule/raster field groups
  reach publication and render entry`, `host-fetched text rectangle multi-row
  raster FF publishes rendered page record`, `addressed text/rule/multi-row
  raster publication preserves bucket chain`, and `0x1ef6a page-band walk
  merges text raster and crossing rule`.
  Checked-in evidence is `Mixed Text/Rule/Raster Page Record` in
  [semantic-state-model.md](semantic-state-model.md), `Worked Path: Mixed
  Text/Rule/Raster Page Record` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md),
  [page-raster-imaging.md](page-raster-imaging.md),
  [raster-graphics.md](raster-graphics.md), and
  [rectangle-graphics.md](rectangle-graphics.md).
  Confidence is high for parser handler order, delayed raster scratch,
  addressed object addresses, published page-record fields, bridge state,
  render call order, bucket-chain order, rule carry, and visible rows.
  No unresolved middle edge remains for this exact stream's text source, rule
  selector, delayed raster restore, page-root storage, publication, bridge, or
  per-band bitmap merge.
  Remaining ROM-local work starts from byte streams that change text source
  fields, rectangle clipping or selectors, raster gate outcomes,
  `0x1381c` allocation/rollover state, bridge roots, continuation state, or
  rendered rows.
- Built-in glyph data:
  ROM evidence is the IC32/IC15 resource ROM tables and bitmap records.
  Checked-in documentation is [resource-rom.md](resource-rom.md),
  [built-in-resource-scan.md](built-in-resource-scan.md),
  [font-context-metrics.md](font-context-metrics.md), and
  [font-sample-page.md](font-sample-page.md), surfaced first as
  `Worked Path: Built-In Resource Scan And Candidate Windows`,
  `Worked Path: Font Selection To Visible Glyphs`,
  `Worked Path: Firmware Font Sample Page`, and
  `Worked Path: Compact Glyph Row-Copy Helpers` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md). Supporting evidence
  includes `generated/analysis/ic32_ic15_builtin_glyph_payloads.md` and compact
  glyph fixtures.
  IC32/IC15 file offset `N` maps to firmware resource address `0x80000 + N`.
  Header-like font records such as first `COURIER` record `0x080418`
  / context `0x44080418` and first `LINE_PRINTER` record `0x0946b4`
  / context `0x440946b4` carry bit-30 offset-table form. Font selection and
  sample-page paths install those contexts into current-font state
  `0x782ee6` / `0x782ef6`, rebuild maps `0x782f32` / `0x783032`, and refresh
  page-root slots through `0xc428` / `0xc4fc`.
  Printable bytes then flow through `0xd04a -> 0x1393a -> 0x12f2e` into
  compact page objects. Publication/rendering copies page-root context slots
  through `0x1ed84` / `0x1edc6`; compact dispatch
  `0x1ef6a -> 0x1efc2 -> 0x1effe -> 0x1f354` resolves the selected resource
  offset table. `0x1f354` consumes glyph-entry byte `+4` as bitmap delta,
  byte `+5` as small mode/plane, word `+6` as row count, and word `+8` as
  pixel width before the row-copy helpers emit pixels.
  Firmware-generated sample pages enter the same path after `0x1e0b2`,
  `0x1c204`, resolver `0x1b50e`, installer `0x1c5e8`, row formatter
  `0x1cabe`, and sample-run helper `0x1cf34`. Fixture
  `font sample full printout segments render through 0x1ed84 and 0x1ef6a`
  pins eight class/source segments, render-bucket counts
  `[1, 6, 6, 65, 1, 5, 5, 50]`, and aggregate rendered-surface digest
  `5e5e735b4fb2a2a4dff4794099a02eaf23fa2dd3e469df8d053db88a321ea6f2`.
- Font selection to visible glyphs:
  Font selection is a parser-state-to-rendered-glyph path, not an immediate
  drawing command. Parser terminal handler `0x120be` and helper `0x1be22`
  write requested symbol/default/font-ID state, common refresh `0xc580`
  decides which primary or secondary slot needs work, candidate path
  `0x13eb8 -> 0x156de -> 0x153c6 -> 0x1519a -> 0x14398` selects a font
  candidate, `0x144d2` writes the selected context, and `0x14c64` rebuilds
  the host-character-to-glyph map.
  Canonical state is selected text slot `0x782f06`, primary context record
  `0x782ee6`, secondary context record `0x782ef6`, primary glyph map
  `0x782f32`, secondary glyph map `0x783032`, active symbol words
  `0x783144/0x783146`, remembered symbol words `0x782f08/0x782f0a`,
  selected page-root font slot `0x78297e`, page-root context slots
  `+0x2c..`, and later compact text objects.
  `0xc428(slot)` reads the selected longword from `0x782ee6` or `0x782ef6`;
  `0xc4fc` finds or installs that longword in one of 16 page-root font slots,
  and later `0x1edc6` copies those slots into render-record contexts.
  Printable source helper `0x1393a` consumes the selected context and
  `0x782f32` or `0x783032` to map the original host byte to a glyph byte
  before `0xd04a -> 0x12f2e -> 0x1387c` queues compact objects.
  Compact render dispatch `0x1ef6a -> 0x1efc2 -> 0x1effe -> 0x1f354` then
  resolves glyph bitmaps from the copied render-record context slot, so the
  renderer identity is selected context longword plus mapped glyph byte, not
  the raw PCL request plus original host byte.
  Derived/cache state includes candidate survivor lists, selected candidate
  `0x7828a8`, target `0x7828de`, snapshots `0x783148/0x783152`, HMI
  `0x78315c`, transient context `0x782992`, current font id `0x782f2e`,
  selected-font flags `0x783132/0x783133`, compact coordinates, glyph-entry
  pointers, and render-band fields.
  Parser scratch includes setup records from `0x1201e` / `0x12008`, mode-13
  font-selection command records, dirty flags `0x782f2c/0x782f2d` while
  refresh is pending, final-`X` parameter records consumed by `0x17708`, and
  the following printable bytes.
  Firmware bookkeeping includes page-root live-font flags, `0xc4fc` slot-scan
  state, symbol-map snapshot provenance byte `+0x09`, publication flag
  `0x782996`, scheduler cursors, and render-work progress words.
  Covered visible streams select primary context `0xc008004c` and secondary
  context `0xc00ae122`, rebuild maps `0x782f32` / `0x783032`, install
  page-root context slots through `0xc428` / `0xc4fc`, and render later
  printable bytes from those contexts. SO and SI controls use the same bridge:
  `0xc6b8` installs/selects secondary slot `1`, while `0xc68a`
  installs/selects primary slot `0`.
  Covered variants include primary and secondary inline selection, symbol-miss
  fallback through `0x156de`, remembered-symbol recovery, non-Roman symbols,
  final-`@` defaults, final-`X` font-ID success through `0x17708`, direct
  font-ID non-selected exits that preserve prior output, and bit-30-clear
  inline/downloaded context selection.
  Concrete output evidence includes fixtures `inline primary font selection
  stream renders visible rows`, `inline secondary font selection stream renders
  SO visible rows`, `primary symbol miss falls back before visible page-record
  rows`, `secondary symbol miss falls back before visible SO page-record rows`,
  `live primary current-font RAM install feeds SI page-record rows`,
  `live secondary current-font RAM install feeds SO page-record rows`,
  `font-ID built-in selection feeds visible page-record rows`,
  `font-ID secondary built-in selection feeds visible SO page-record rows`,
  `font-ID primary inline/downloaded selection feeds visible page-record
  rows`, `font-ID inline/downloaded selection feeds visible page-record rows`,
  `font-ID non-selected exits keep prior visible rows`,
  `font-ID secondary non-selected exits keep prior SO visible rows`, and
  `0x13eb8 no-dispatch exits keep prior visible rows`.
  Checked-in evidence is [font-context-metrics.md](font-context-metrics.md),
  [built-in-resource-scan.md](built-in-resource-scan.md),
  `Built-In Font Selection To Visible Text` in
  [semantic-state-model.md](semantic-state-model.md), and `Worked Path: Font
  Selection To Visible Glyphs` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md).
  Confidence is high for primary/secondary selection, symbol fallback,
  final-`X` success and non-selected exits, page-root slot install/reuse,
  glyph-map consumption, bridge preservation, and rendered rows.
  No unresolved ROM-local middle edge remains for the documented primary and
  secondary built-in selection streams. Remaining work must change a concrete
  selected-font boundary: candidate windows `0x7827a0..0x7827b8`, selected
  slot `0x7828a8`, active symbol words `0x783144/0x783146`, selected context
  records `0x782ee6/0x782ef6`, primary/secondary maps `0x782f32/0x783032`,
  snapshot keys `0x783148/0x783152`, page-root font slot/context fields,
  source-object fields `0x782d7e+0x00/+0x04/+0x0b/+0x10/+0x16`, HMI/cursor
  advance, span metrics, compact object shape, bridge context slots, or
  ROM-derived rows.
- Downloaded font payloads:
  Downloaded fonts are a parser-payload-to-selected-resource path. Font-control
  writers `0x15a56`, `0x15a18`, and `0x16df6` set the current id/character
  context; descriptor/payload parser routes `0x15d0a` and `0x16c14` install
  payload records; font refresh `0x13eb8 -> 0x14c64` selects those records;
  printable bytes then use the installed resource through
  `0xd04a -> 0x1393a -> 0xd824/0xd3b2 -> 0x12f2e`.
  The command does not draw by itself. Pixels appear only after the selected
  downloaded resource has been converted into compact page objects and rendered
  through `0x1ed84 -> 0x1edc6 -> 0x1ef6a`.
  Canonical parser/resource state is current font id `0x782f2e`, current
  character `0x782f30`, parser cursor `0x78299e`, device mode byte
  `0x782a92`, current-record pool `0x782640..0x782776`, record id `+0x00`,
  flag byte/word `+0x02`, payload pointer `+0x06`, current-font counters
  `0x782782/0x782786`, candidate counters/windows
  `0x78278e/0x782790/0x782796/0x782798/0x78279e` and
  `0x7827a0/0x7827ac/0x7827b0/0x7827b4`, selected candidate flags bit `30`
  and bit `26`, and allocated downloaded payloads such as the `0x1719c`
  header.
  Canonical page/image state is the downloaded glyph table entry, record delta,
  bitmap offset and copied bitmap bytes, compact text object, bucket root, page
  context slots, and published page record. For the segmented-wide stream,
  `0x16498` installs glyph `%` with record bytes
  `00 00 00 00 0c 02 00 81 00 88 00 00`, the page queue uses selector
  `0x3003` in buckets `9` and `1`, `0xff1e` publishes the record,
  `0x1ed84`/`0x1edc6` bridge it, and
  `0x1ef6a -> 0x1efc2 -> 0x1effe -> 0x1f264` renders the pixels.
  Parser scratch is payload budget `0x783140`, delayed `W` command records
  such as `80 57 00 12 00 00`, descriptor scratch `0x7827de..0x7827e9`,
  parsed bitmap count `0x7827be`, span `0x7827c2`, row count `0x7827c4`,
  saved continuation block `0x7827c6..0x7827d8`, and the stream split between
  font bytes and following page bytes. Linear bitmap payload copies use
  `0x168dc`; split-plane copies use `0x16942`.
  Derived/cache state is the selected font map rebuilt by
  `0x14c64`/`0x14e24`, source objects emitted by `0x1393a`, compact objects
  emitted by `0x12f2e`, bridged render-record context emitted by `0x1edc6`,
  and per-band dispatch fields derived by `0x1ef86`.
  Firmware bookkeeping is replacement/release ordering, candidate insertion
  through `0x1bc38`, count/window shifts, copy status, stream position, return
  drain through `0x12328`, stale-continuation cleanup, publication flag
  `0x782996`, and current-page-root clearing after `0xff1e`.
  Nonzero `ESC )s#W` resource headers validate through `0x16fae`, allocate
  through `0x17026`, initialize `0x1719c` payload headers, and install bit-30
  candidate longwords through `0x16c14` / `0x1bc38`. The integrated
  downloaded-pointer path maps printable `!` through context `0x40000000`,
  queues compact and span objects, and renders offset-table downloaded glyph
  rows. Type-1 and type-2 headers are covered with candidate prefixes
  `0x40000000` and `0x44000000`.
  The bit-30-clear fixed-record route is a separate zero-count `0x15d0a`
  path: `0x15e42 -> 0x16606 -> 0x15dcc -> 0x12328` for current-record
  installs, and `0x15e64 -> 0x15c4c -> 0x15dcc -> 0x12328` for continuation
  records. Its visible output is still later printable text, with
  `0x14e24`, `0x1393a`, `0x12f2e`, `0x1edc6`, and `0x1ef6a` consuming the
  fixed-record table and bitmap bytes.
  Covered visible variants include short selector `0x0003` through `0x1fe76`,
  wide selector `0x1003` through `0x1f0d2`, segmented selector `0x2000` /
  `0x2003` through `0x1f1f0`, segmented-wide selector `0x3003` through
  `0x1f264`, type-0/type-1/type-2 resource-header publications, metric
  consumers `0xd4ac` and `0xd8fc`, FF publication through `0xff1e`, and mixed
  downloaded-glyph/rule/raster composition before `0x1ef6a`.
  Downloaded glyph row/span publication is a separate renderer-helper
  checkpoint, not generic variant breadth. `0x16498` writes canonical glyph
  records and bitmap bytes; `0x12f2e` consumes the current printable source
  record and derives selector bits, bucket index, and compact object bytes;
  `0xff1e` publishes the bucket array; `0x1ed84` / `0x1ef6a` dispatch the
  published object to `0x1effe`; and `0x1effe` reaches short helper
  `0x1fe76`, wide helper `0x1f0d2`, segmented helper `0x1f1f0`, or
  segmented-wide helper `0x1f264`.
  Canonical state for this subpath is the installed glyph table entry,
  record byte `+5`, record row word `+6`, width word `+8`, bitmap bytes at
  `+0x0c`, the compact object in page-root bucket `+0x1c`, and the published
  bucket root. Derived/cache state is the selector word, low row/width bytes
  consumed by `0x12f2e`, `0x1f414` current/fallback split counts, row-copy
  table index, wide-mode caches `0x783a40..0x783a48`, and fallback buffer base
  `0x7810b4 + D2`. Parser scratch is the restored `ESC )s#W` command record,
  payload budget `0x783140`, and post-install drain through `0x12328`.
  Firmware bookkeeping is copy status, continuation state, allocation/release
  state, and page publication state.
  The row-count matrix closes parser-produced rows `0x0001..0x00ff` for the
  documented short/segmented family. Fixtures
  `downloaded glyph row-count matrix publishes and renders additional
  short/segmented counts`, `host-fetched rows-0x20 short downloaded glyph FF
  publication renders page record`, `host-fetched rows-0x40 short downloaded
  glyph FF publication renders page record`, `host-fetched row-0x80 downloaded
  character remains short compact`, `host-fetched segmented downloaded
  character renders through 0x1f1f0`, and
  `host-fetched rows-0x82 segmented downloaded glyph FF publication renders
  page record` carry those rows through install, printable source capture,
  publication, bridge, and render rows. The high-row truncation fixtures
  preserve installed row words `0x0101..0x0103`, but show that `0x12f2e`
  sees only low row bytes `0x01..0x03`, queues selector `0x0003`, and reaches
  the exact short-helper boundary where `0x1f414` fallback counts `199..201`
  index beyond the `0x1fe76` valid maximum `128`. That boundary is the
  unchecked `0x1fe8a + 4 * D3` row-count table read in `0x1fe76`: entry `128`
  at `0x2008a` is the last valid pointer, and entries above it read row-copy
  code bytes beginning at `0x2008e` as pointer data.
  The width side has the same source-byte classification. Fixture
  `downloaded glyph width-byte boundary truncates page-record span` preserves
  installed spans through `0x020d`; low source width bytes `0x00..0x10`
  select compact mode-0 helper entries outside decoded row-copy helper heads,
  while high source width bytes `0x11..0xff` select compact-wide `0x1f0d2`
  and render documented rows for the sampled high-byte cases. Segmented-wide
  high-row fixtures cover selected segment rendering through `0x1f264` for
  sampled rows through `0x0787`, with span-31 siblings through `0x03ff`
  bounded at fallback A2 source offset `+0xb50` and larger row/span products
  bounded by the `0x7fff` parser payload-count cap before renderer entry.
  Concrete output evidence includes fixtures `host-fetched printable byte uses
  installed downloaded glyph page object`, `combined host-fetched font download
  stream prints installed glyph`, `combined font download FF publishes
  installed glyph page record`, `host-fetched resource header plus glyph
  payload renders offset-table downloaded glyph`, `type-1 and type-2 resource
  glyph FF publications render page records`, `host-fetched 0x15d0a
  current-record resource object feeds fixed-record render`, `host-fetched
  0x15d0a continuation resource object resumes fixed-record render`,
  `host-fetched 0x15d0a split-plane continuation resource object resumes
  fixed-record render`, `downloaded glyph byte-24 state handoff feeds following
  page handler`, `parser-driven downloaded glyph rule raster stream composes
  through 0x1ef6a`, and `segmented downloaded glyph raster FF publications
  render page records`.
  Checked-in evidence is [downloaded-fonts.md](downloaded-fonts.md), the
  downloaded-font checkpoints in
  [semantic-state-model.md](semantic-state-model.md), `Downloaded Font Support`
  in [font-context-metrics.md](font-context-metrics.md), and worked paths
  `Downloaded Glyph`, `Downloaded Glyph Rule/Raster Composition`,
  `Nonzero Resource Payload`, and `Fixed-Record Resource Object` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md).
  Confidence is high for descriptor dispatch, current-record state,
  zero-drain success boundaries, resource allocation, candidate insertion,
  selected map consumption, short/wide/segmented downloaded glyph rendering,
  FF publication, and mixed rule/raster/downloaded-glyph composition in the
  cited ROM paths. The fixtures named above drive those parser branches and
  check internal helper transcriptions; the semantic claims come from the
  checked-in handler, field, page-object, bridge, and render-helper notes.
  Resolved middle boundaries include `0x15dc6 -> 0x16498 -> 0x15dcc ->
  0x12328`, `0x16c14..0x16c68 -> 0x12328`, fixed-record current and
  continuation routes through `0x16606` and `0x15c4c`, resource-header
  allocation through `0x17026/0x1719c`, candidate insertion through `0x1bc38`,
  the byte-24 install-to-page handoff, parser-produced row counts
  `0x0001..0x00ff`, wide span publication through sampled high spans, and
  segmented-wide selected-segment rendering for below-cap high-row products.
  Remaining exact boundaries are variant breadth, not the covered paths. The
  fixed-record current and continuation ranges are now decomposed in
  [downloaded-fonts.md](downloaded-fonts.md): remaining work there is
  branch-combination coverage that changes table base, active-context refresh,
  release-helper effect, copy status, or later page-record selector inside
  `0x16612..0x16870` and `0x15c4c..0x15d08`. Other remaining exact boundaries
  are selected-font combinations that change a concrete context/map boundary
  before visible output: selected context longword, selected target
  `0x7828de`, selected slot pointer `0x7828a8`, primary/secondary maps,
  page-root context slots, source-object fields, HMI/cursor advance, compact
  selector class, span metric fields, page-object fields, bridge roots, or
  ROM-derived row construction. The remaining exact ROM-local helper failures
  are already named as bounded edges: short compact
  fallback indices above `0x1fe76` valid index `128` where the unchecked table
  read enters code bytes at `0x2008e`, low wrapped width bytes that target
  non-row-copy helpers, segmented-wide span-31 fallback source offset
  `+0xb50`, and downloaded-glyph payloads that exceed the `0x7fff` parser
  count cap before renderer entry. The cap boundary is arithmetic, not an
  open renderer edge: segmented-wide spans start at `17`, so
  `floor(0x7fff / 17) = 0x0787`; `0x0788*17` stops before `0x16498` can
  install a glyph or any page object can reach `0x1f264`.

## Reproducible Byte-Stream Families

- Plain printable text and text with direct controls are covered from host
  bytes through parser, compact bucket objects, bridge, and rendered rows.
  Evidence: fixtures `plain printable parser trace feeds page-record queue`,
  `host-fetched mixed control stream reaches parser and page-record render`,
  `host-fetched direct text/control streams feed 0x1ed84 and 0x1ef6a`,
  `ESC 9 clear margins feeds CR and page-record output`,
  `ESC = half-line feed reaches shifted page-record output`, and
  `ESC &d underline selector materializes span output`.
  The representative control path is `ESC &k1G ! CR !`: host bytes enter
  `0xa904 -> 0xda9a -> 0x11774`, command handler `0xedf8` writes
  line-termination byte `0x78318f = 0x80`, the first `!` reaches `0xd04a`,
  CR handler `0xf02c` resets horizontal cursor `0x782c8a` from left margin
  `0x782dd6`, flushes pending span state through `0xf34a`, and calls LF helper
  `0xf0b2` because bit 7 is set. The second `!` then queues at compact coord
  `0x3b00` through `0xd04a -> 0xd824 -> 0x12f2e -> 0x1387c`, publishes through
  `0xff1e`, crosses `0x1ed84` / `0x1edc6`, and renders through `0x1ef6a`.
  Direct-control variants share the same canonical placement fields:
  horizontal cursor `0x782c8a`, vertical cursor `0x782c8e`, margins
  `0x782dd6` / `0x782dda`, HMI `0x78315c`, VMI `0x783160`, top offset
  `0x782dce`, bottom/text-length state `0x782dd2`,
  wrap byte `0x783190`, and perforation-skip byte `0x783191`. `ESC 9`
  handler `0xe9ba` clears margins before later CR/text consumes them;
  `ESC =` handler `0xf176` advances by half VMI before later text;
  `ESC &d` handler `0x12622` writes underline selector `0x783185` and can
  flush selector-`0x4000` span objects through `0x12714`, which later render
  through segment-list path `0x1f812`.
- Layout-control streams are covered where command bytes alter later visible
  output without drawing immediately. Evidence:
  `Worked Path: Page Length, Wrap, And Perforation Controls` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md),
  [direct-control-codes.md](direct-control-codes.md), fixtures
  `0xf9e8 ESC &l#P stream reaches page-length handler`,
  `0xc992 ESC &l#D accepts ROM LPI set and refreshes pending vertical
  cursor`, `0xcb00 ESC &l#C converts 1/48-inch VMI and keeps zero unmodified`,
  `0xea9e ESC &l#F sets text length bottom or restores default`,
  `0xece2 ESC &l#E sets top margin, default text length, and pending cursor`,
  `0xcb00/0xc992/0xece2/0xea9e chained ESC &l stream selects vertical layout
  handlers`, `vertical layout parser trace feeds page-record queue`,
  `mixed page-length stream refreshes cursor before printable page-record
  queue`, `0xedb0 ESC &s#C toggles end-of-line wrap for selectors 0 and 1
  only`, `0xd28a and 0xd6bc prechecks share continue reject and wrap
  decisions`, `0xee64 ESC &l#L toggles perforation skip for selectors 0 and 1
  only`, `0xf36c perforation skip gates vertical overflow page eject`, and
  `perforation skip parser trace feeds page-record queue`. The reproduction
  effect is later placement, queue suppression/recovery, or page-eject
  behavior through the same page-record and render pipeline as ordinary text.
  The concrete layout-control path starts at `0xa904 -> 0xda9a -> 0x11774`.
  `ESC &l66P` and `ESC &l0P` dispatch to `0xf9e8`; `ESC &l1L` dispatches to
  `0xee64`; and `ESC &s0C` / `ESC &s1C` dispatch to `0xedb0`. Nonzero page
  length uses VMI `0x783160`, writes page extent `0x782dba`, selects internal
  page code `0x782da2`, recomputes geometry/text-bottom state, and the covered
  `ESC &l66P !` stream queues the following printable at compact coord
  `0x9001`. The zero-length branch flushes pending text, can publish through
  `0xff1e`, mirrors `0x782da6` to `0x780e8f`, signals `0x780e26`, and selects
  default page code `0x780e97` or fallback `2`. Wrap handler `0xedb0` writes
  `0x783190`: selector `0` enables and selector `1` clears. Printable
  prechecks `0xd28a` and `0xd6bc` consume that byte: disabled wrap rejects
  horizontal overflow, enabled wrap recovers through `0xf054` and retries from
  the recovered cursor when the retried placement fits. Perforation handler
  `0xee64` writes `0x783191`: selector `1` enables and selector `0` clears.
  Overflow helper `0xf36c` consumes `0x782c8e`, `0x782dc2`, and `0x783191`;
  only enabled overflow with nonzero limit calls `0xf124`, publishes/ejects,
  recomputes y from top offset and VMI, and returns `D7 = 0`. Other cases
  return `D7 = 1` without page eject.
- Built-in font-selection streams are covered for primary and secondary
  visible output, symbol fallback, remembered-symbol recovery, non-Roman
  symbol sets, real final-`@` default-symbol table streams, final-`X` font-ID
  success, final-`X` preserved-output exits, bit-30-clear inline/downloaded
  context selection, and selected current-font RAM handoff through SI/SO.
  Evidence: [font-context-metrics.md](font-context-metrics.md),
  `Worked Path: Font Selection To Visible Glyphs` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md), and fixtures
  `inline primary font selection stream renders visible rows`,
  `inline secondary font selection stream renders SO visible rows`,
  `primary symbol miss falls back before visible page-record rows`,
  `remembered secondary symbol feeds visible SO page-record rows`,
  `non-Roman symbol streams select visible built-ins`,
  `real final-@ default-table streams select visible built-ins`,
  `font-ID built-in selection feeds visible page-record rows`,
  `font-ID secondary built-in selection feeds visible SO page-record rows`,
  `font-ID primary inline/downloaded selection feeds visible page-record rows`,
  and `font-ID non-selected exits keep prior visible rows`. The reproduction
  effect is context/map selection before ordinary printable bytes queue compact
  objects; font-selection commands have no separate renderer.
  The concrete request path starts at `0xa904 -> 0xda9a -> 0x11774`. Primary
  `ESC (` setup uses `0x1201e`; secondary `ESC )` setup uses `0x12008`.
  Attribute finals in parser mode `13` write request fields through handlers
  such as spacing `0xc930`, pitch `0xc89c`, point size `0xc6ec`, style
  `0xc780`, stroke `0xc840`, and uppercase typeface wrapper
  `0x1205a -> 0xc7e0 -> 0xc580`. Primary requests write
  `0x782eec..0x782ef2`; secondary requests write the sibling request block.
  Refresh `0xc580` calls `0x13eb8(slot)`, which filters candidates through
  `0x148f8`, `0x1569c`, `0x156de`, `0x153c6`, `0x1519a`, `0x147b2`,
  `0x14758`, `0x14398`, `0x144d2`, and `0x14c64`. The selected primary
  stream writes current context `0x782ee6 = 0xc008004c` and map `0x782f32`;
  the selected secondary stream writes current context `0x782ef6 =
  0xc00ae122` and map `0x783032`.
  Symbol-set finals route through `0x120be -> 0x1be22`, write requested
  symbol words at `0x782ef4 + 0x10 * slot`, dirty refresh flags
  `0x782f2c` / `0x782f2d`, and use `0x156de` to consume requested,
  remembered, and fallback words before the same candidate/map path. Final
  `@` subdispatches through `0x1bed4`, `0x1bf0a`, `0x1bf36`, or `0x1bf74`
  to copy default-symbol table words `0x782f1c`, `0x782f20`, `0x782f24`,
  and `0x782f28`. Final `X` keeps the prior requested symbol word and calls
  `0x17708(slot, parameter)`, selecting built-in contexts such as
  `0xc0089fb0` / `0xc00ae122` or bit-30-clear inline/downloaded context
  `0x00000100`; its scan-miss, candidate-slot-miss, class-mismatch, and
  context-full exits preserve the prior visible context.
  `0xc428(slot)` installs the selected context into the active page root:
  slot `0` reads `0x782ee6`, slot `1` reads `0x782ef6`, `0xc4fc` finds a
  matching or free page-root context slot, and `0xc428` writes selected
  page-root slot `0x78297e`. SI `0xc68a` installs/selects primary slot `0`;
  SO `0xc6b8` installs/selects secondary slot `1` and updates selected text
  slot `0x782f06`. Later printable bytes consume that state through
  `0xd04a -> 0x1393a`: primary text reads context `0xc008004c` and map
  `0x782f32`, secondary text reads context `0xc00ae122` and map `0x783032`,
  and `0x12f2e` queues compact objects under the ordinary page-root bucket
  path. Publication and rendering are unchanged:
  `0xff1e -> 0x1ed84 -> 0x1edc6 -> 0x1ef6a -> 0x1effe -> 0x1f354`, with
  `0x1edc6` copying page-root context slots into render-record context slots.
  Common refresh `0xc580` is the branch gate between parsed request state and
  page-root context state. Its checked-in fixture cluster covers dirty-1
  primary and secondary installs, full live-slot reuse of a matching context,
  full live-slot no-match skip when `0xc4fc` returns `0x11`,
  selector-mismatch refresh without context install, dirty-2 selector-match
  install through `0xc428`, and dirty-2 selector-mismatch remembered-word-only
  behavior. Those cases classify the state roles: canonical current contexts
  `0x782ee6` / `0x782ef6`, active symbol words `0x783144` / `0x783146`,
  remembered words `0x782f08` / `0x782f0a`, page-root context slots, and
  selected slot `0x78297e`; derived/cache selected candidate and map state
  from `0x13eb8` / `0x14c64`; parser scratch dirty flags
  `0x782f2c` / `0x782f2d`; and firmware bookkeeping in the `0xc4fc` slot scan
  and live-font flags. Evidence fixtures are `0xc580 dirty primary branch
  installs page-root font context`, `0xc580 dirty secondary branch installs
  page-root font context`, `0xc580 full live-slot branch reuses matching
  page-root font context`, `0xc580 full live-slot branch skips install when
  c4fc reports full`, `0xc580 selector-mismatch branch refreshes candidate
  without context install`, `0xc580 dirty-2 selector-match branch installs
  current context only`, `0xc580 dirty-2 secondary selector-match branch
  installs current context only`, and `0xc580 dirty-2 selector-mismatch branch
  only copies remembered word`.
  Pitch-mode `ESC &k#S/s` is a compatibility producer into that same refresh
  pipeline, not an independent text renderer. Handler `0xc390` accepts
  selectors `0`, `2`, and `4`; selector `0` synthesizes pitch `10.0000`,
  runs `0xc89c -> 0xc580`, then synthesizes a second record and runs the
  same pair again; selector `2` synthesizes pitch `16.6600`; selector `4`
  synthesizes pitch `12.0000`. Other selectors exit without calling the
  pitch writer or common refresh. The output handoff is therefore:
  `0xc390 -> 0xc89c -> 0xc580 -> 0xc428/0x14c64` when state changes, then
  later printable bytes consume the selected context through
  `0xd04a -> 0x1393a -> 0x12f2e` and render through the ordinary
  page-root/context bridge. Evidence is
  [font-context-metrics.md](font-context-metrics.md),
  `Worked Path: Pitch Mode To Font Refresh` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md), and
  `generated/disasm/ic30_ic13_pitch_mode_handler_00c390.lst`.
  Canonical state is selected slot `0x782f06`, primary/secondary contexts
  `0x782ee6` / `0x782ef6`, maps `0x782f32` / `0x783032`, active and remembered
  symbol words `0x783144` / `0x783146` and `0x782f08` / `0x782f0a`,
  page-root context slots, selected page-root slot `0x78297e`, compact text
  objects, and render-record context slots. Derived/cache state includes
  candidate survivor lists, selected candidate slot `0x7828a8`, selected
  target `0x7828de`, snapshot records `0x783148` / `0x783152`, HMI
  `0x78315c`, transient selected context `0x782992`, current font ID
  `0x782f2e`, default-symbol tables, compact coordinates, and glyph-entry
  pointers. Parser scratch is the setup records from `0x1201e` / `0x12008`,
  mode-13 command records, dirty flags while refresh is pending, and following
  printable bytes. No ROM-local middle edge remains for the listed primary,
  secondary, symbol fallback, remembered-symbol, non-Roman, default-symbol,
  font-ID success/non-selected, common-refresh, and SI/SO handoff streams.
  Remaining font-selection work starts only from command combinations that
  change selected contexts, map bytes, page-root slot behavior, compact object
  shape, bridge state, or rendered rows.
- Explicit no-output parser rows are covered for normal `NUL BEL VT` and for
  alternate/data blank C0 append-preserving rows. Evidence:
  `Worked Path: Explicit No-Output Parser Rows` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md),
  [pcl-parser-core.md](pcl-parser-core.md),
  [pcl-command-map.md](pcl-command-map.md), and generated parser table extract
  `generated/analysis/ic30_ic13_parser_dispatch_tables.md`. The reproduction
  effect is absence of page objects in normal mode while preserving pending
  delayed restore at `0x12218`; in alternate/data mode the bytes are stored
  through `0xe002` before parser reset.
  Normal mode-zero rows `0x00`, `0x07`, and `0x0b` enter through
  `0xa904 -> 0xda9a -> 0x11774`, match explicit parser-table entries with
  next mode `0` and no handler longword, and therefore bypass the unmatched
  mode-zero fallback at `0x118d6..0x11900` that can route other bytes through
  selected-context printable handler `0xd04a`. The zero-handler path writes
  parser mode `0`, calls the terminal restore/reset boundary `0x12218`, and
  resets command-record cursor `0x78299e`, nonnumeric scratch cursor
  `0x782a26`, numeric scratch cursor `0x782a3e`, alternate echo latch
  `0x782a56`, and matched-byte scratch `0x783196..0x783199`. It does not run
  adjacent normal C0 handlers such as BS `0xf2a8`, HT `0xf1cc`, LF `0xf08c`,
  FF `0xf0f0`, CR `0xf02c`, SO `0xc6b8`, or SI `0xc68a`.
  Alternate/data mode uses parser table `0x116f6`: blank C0 rows `0x00` and
  `0x07..0x0f` first store the byte in parser scratch, flush command and
  numeric scratch through `0x123ae` and `0x123de`, append the matched byte
  through macro/data sink `0xe002`, and then rejoin the same terminal reset
  boundary. Canonical state for this checkpoint is parser mode `0x782999`,
  alternate/data selector `0x782c18`, delayed-payload fields
  `0x782a1a`/`0x782a1c`/`0x782a20..0x782a25`, and the command/scratch cursors;
  derived output exists only as stored macro/data input in alternate/data
  mode. No ROM-local page-object, publication, or render edge remains for
  these rows.
- Transparent print data streams are covered for printable bytes,
  default-filtered C0/high-control bytes, nonzero-filtered C0/high-control
  bytes, `1a 58` and non-`0x58` probe handling, primary high-control samples
  `0x81`, `0x88`, `0x90`, `0x97`, `0x98`, and `0x9f`, and the secondary
  segmented page-record boundary. Evidence: fixtures
  `transparent data parser trace feeds page-record queue`,
  `transparent non-0x58 probe byte reaches page-record output`,
  `transparent data control payloads advance through fixed-space path`,
  `transparent default-filtered control enters unflagged fixed-record path`,
  `transparent nonzero filters route controls through printable path`,
  `transparent nonzero high-control byte queues tall glyph bucket`,
  `transparent nonzero high-control interior samples remain printable`,
  `transparent nonzero high-control upper bound remains printable`, and
  `transparent secondary high-control byte enters segmented page-record path`.
  The renderer-visible secondary prefix is covered through bucket `448`;
  bucket `456` is bounded as the physical resource-window continuation issue
  above.
  The command path starts at `0xa904 -> 0xda9a -> 0x11774`. `ESC &p#X`
  dispatches to arming stub `0x11f5a`, which pushes delayed handler `0x12452`
  and calls `0x121cc`. `0x121cc` rewinds command-record cursor `0x78299e` by
  six, stores pending flag `0x782a1a = 1`, stores handler pointer
  `0x782a1c = 0x12452`, and saves the six-byte command record at
  `0x782a20..0x782a25`. When parser mode returns to zero, `0x12218` restores
  that record and calls `0x12452`; for `ESC &p4X`, the restored record is
  `80 58 00 04 00 00`.
  `0x12452` is a counted direct reader, not an opaque binary skip. It rewinds
  `0x78299e`, reads signed record word `+2`, uses its absolute value as the
  payload count, reads selected text/context slot `0x782f06`, scales it
  through `0x332ee`, and reads context byte `0x782eea + 0x10 * slot`. If
  high-character flags `0x783132` and `0x783133` are clear, local high-control
  filter word `A6-2` comes from fallback byte `0x782efa`; otherwise it comes
  from the selected context byte. The loop fetches raw payload bytes through
  `0xa904`. Byte `0x1a` probes one more byte: `1a 58` calls `0xd99a` and
  routes normalized value `0x7f`, while `1a xx` with `xx != 0x58` consumes
  the probe prefix and routes `xx`.
  After normalization, C0 values `0x00..0x1f` route through `0xd0f0` only
  when selected context byte `D3` is zero; high controls `0x80..0x9f` route
  through `0xd0f0` only when local filter word `A6-2` is zero; all other
  values route through `0xd04a`. The default `ESC &p4X!\x05\x85!` stream
  therefore routes `21 05 85 21` as `d04a d0f0 d0f0 d04a`: the printable
  bytes queue compact entries, while the default-filtered C0 and high-control
  bytes advance fixed spacing in the flagged built-in path without allocating
  compact text objects. Nonzero filters send those same ranges through
  `0xd04a`; an unflagged fixed-record context can let the `0xd0f0`
  substituted space queue a compact object instead of cursor-only spacing.
  Printable transparent values re-enter the ordinary text/page path:
  `0xd04a -> 0x1393a -> 0xd824/0xd3b2 -> 0x12f2e -> 0x1387c -> 0xff1e ->
  0x1ed84 -> 0x1edc6 -> 0x1ef6a`. Canonical state is the restored count word
  `+2`, selected slot `0x782f06`, cursor `0x782c8a`, current page root
  `0x78297a`, compact text object, published record, and render-record
  bucket/context roots. Derived/cache state is selected context byte
  `0x782eea + 0x10 * slot`, fallback filter `0x782efa`, high-character flags,
  compact coordinates, and render-band fields. Parser scratch is the delayed
  payload state `0x782a1a` / `0x782a1c` / `0x782a20..0x782a25`, command-record
  cursor `0x78299e`, and local payload count. No ROM-local middle edge remains
  for `ESC &p#X` parser dispatch, payload counting, probe normalization,
  route predicates, compact object production, bridge, or render dispatch; the
  remaining transparent edge is only the external resource-window source for
  the secondary segmented fallback rows at `0x0c0000..0x0c0321`.
- Display-functions streams are covered for normal page output and
  alternate/data append. Normal fixture `ESC Y display-functions stream
  reaches page-record output` drives `ESC Y!\x05! ESC Z` through handler
  `0x12536`, queues visible text including the terminating `Z`, and renders
  the resulting page records. Fixture `ESC Y display-functions filter-on routes
  controls as printable` sets nonzero context/high-control filters, normalizes
  `1a 58` to `7f`, routes `05 80 7f 21 1b 5a` through `0xd04a`, queues six
  compact entries, and renders digest
  `1cdd8203b43944801ec8d1d01c6ab4fa3808fc1f81a7ebfa4d04452369193b63`.
  Alternate/data fixture `0x12120 ESC Y alternate append stores normalized
  display bytes` checks append-only output `1b 59 21 7f 1b 5a` through
  `0xe002` without text imaging.
  The command-family contract is [display-functions.md](display-functions.md).
  Initial bytes enter through `0xa904 -> 0xda9a -> 0x11774`, but after the
  mode-1 dispatch the reader loops fetch later bytes directly through
  `0xa904`. Normal mode dispatches `ESC Y` to `0x12536`; alternate/data mode
  dispatches it to `0x12120`. Both loops keep local termination flag `D4`,
  route or append normalized loop value `D5`, normalize local pair
  `0x1a 0x58` to `0x7f` through `0xd99a`, and stop only after a normalized
  `ESC Z` pair or no-byte return. Normal `0x12536` consumes selected slot
  `0x782f06`, selected context byte `0x782eea + 0x10 * slot`, fallback filter
  `0x782efa`, high-character flags `0x783132` / `0x783133`, and stack filter
  word `A6-2`. C0 values `0x00..0x1f` route to `0xd0f0` only when the
  selected context byte is zero; high controls `0x80..0x9f` route to `0xd0f0`
  only when the local high-control filter is zero; all other values route to
  `0xd04a`. Printable routes then use the ordinary text path
  `0xd04a -> 0xd824 -> 0x12f2e -> 0x1387c -> 0xff1e -> 0x1ed84/0x1edc6 ->
  0x1ef6a`. Alternate/data `0x12120` writes literal `ESC Y` and each
  normalized value through append sink `0xe002` into macro/data-chain storage,
  so it has no immediate page objects. Neighboring `ESC z` at `0xcd86` is a
  status edge, not the `ESC Y` reader: it reads active data-chain frame
  pointer `0x782d76`, tests frame byte `+9`, and calls `0x9c2c` only when that
  byte is zero; `0x9c2c` sets `0x7821cc` / `0x7822db`, signals bit `0x8` in
  `0x780e2a` through `0x9b5e`, and clears `0x7821cc`. No ROM-local middle edge
  remains for `0x12536..0x1261e`, `0x12120..0x1219c`, the local Control-Z
  siblings, or the `0xcd86 -> 0x9c2c` status boundary; unresolved names are
  external status-consumer labels.
- Page-geometry streams are covered for page size, orientation, nonzero
  page length, and the `ESC &l0P` zero-length default-page branch. Evidence:
  [page-raster-imaging.md](page-raster-imaging.md),
  [publication-commands.md](publication-commands.md),
  [pcl-command-map.md](pcl-command-map.md), `Page Geometry And Direct Layout
  State` and `Publication Commands To Rendered Page Records` in
  [semantic-state-model.md](semantic-state-model.md), fixtures
  `0x9d16/0x9d4e/0x9d86/0x9dbe page geometry lookups mask page code`,
  `ROM page geometry tables match manual logical dimensions`,
  `ROM page geometry tables recover manual printable-area margins`,
  `0xfc74 ESC &l#A maps page size and recomputes portrait geometry`,
  `0x10220 ESC &l#O swaps active extents and selects orientation margins`,
  `0xfc74/0x10220 chained ESC &l stream selects page size then orientation`,
  `0xf9e8 ESC &l#P converts VMI lines to page length and selects internal
  page code`, `0xf9e8 ESC &l#P stream reaches page-length handler`,
  `mixed printable/page-size page-record stream publishes queued text`,
  `mixed printable/page-size page-record finalization publishes bridged
  record`, `mixed printable/orientation page-record stream publishes queued
  text before landscape change`, `mixed printable/orientation page-record
  finalization publishes bridged record`, and `addressed page geometry
  publications render page records`.
  Geometry commands are parser-state-to-later-placement commands, not pixel
  renderers. Page-size handler `0xfc74` publishes any queued page before
  storing internal page code `0x782da2` and reloading table-backed geometry.
  Orientation handler `0x10220` publishes any queued page before writing
  orientation byte `0x782da3`, swapping active extents, and selecting
  orientation-specific margins. Page-length handler `0xf9e8` writes page
  length/vertical extent `0x782dba`; nonzero lengths recompute geometry and
  refresh the next printable cursor, while `ESC &l0P` takes the default-page
  branch through `0xfa62..0xfaa6` and `0xfb4a..0xfc52`.
  Canonical geometry state is internal page code `0x782da2`, orientation
  `0x782da3`, table outputs `0x782db2` and `0x782db4`, active extents
  `0x782db6` and `0x782db8`, vertical extent `0x782dba`, top offset
  `0x782dce`, text bottom `0x782dd2`, and page-environment bytes
  `0x782da6`, `0x780e8e`, `0x780e8f`, `0x780e26`, and `0x780e97`.
  The ROM lookup helpers `0x9d16`, `0x9d4e`, `0x9d86`, and `0x9dbe` read
  tables `0x00a112`, `0x00a128`, `0x00a13e`, and `0x00a154`; they mask page
  code with `0x7f`, accept indexes `0..10`, and recover manual logical
  dimensions and printable-area margins for supported page sizes
  `1`, `2`, `3`, `26`, `80`, `81`, `90`, and `91`.
  Derived/cache state includes orientation-specific margin sequence
  `0x782daa..0x782db0`, half-page remainder `0x782dc0`, default text-length
  caches, HMI/VMI-derived printable cursor refresh, render-band geometry, and
  page-change/status flags. Parser scratch is the six-byte command record at
  `0x78299e`, the parsed parameter word, and pending text/span state flushed
  before geometry mutation.
  Firmware bookkeeping is the publication-before-mutation ordering through
  `0xf34a` / `0xff1e`, wait/status edge `0x9ac2`, default-page fallback code
  selection, optional page-environment mirroring, and current-page-root
  clearing after publication.
  Writers are `0xfc74` for page size, `0x10220` for orientation, `0xf9e8`
  for page length/default-page refresh, `0x9d16` / `0x9d4e` / `0x9d86` /
  `0x9dbe` for table lookup outputs, and `0xff1e` for published records when
  queued content must be finalized first.
  Readers/consumers are later printable placement through
  `0xd04a -> 0xd824 -> 0x12f2e`, VFC and perforation-skip helpers,
  raster-origin handlers `0x1075a` / `0x10606..0x10632`, rectangle clipper
  `0x10b80`, span flusher `0x12714`, publication `0xff1e`, bridge
  `0x1ed84` / `0x1edc6`, and render dispatch `0x1ef6a`.
  Output effect is either no immediate page object, for isolated geometry
  changes, or publication of already queued content before the new geometry
  takes effect. The covered `! ESC &l1A` stream publishes the compact text
  bucket before page code `6` and portrait geometry are installed; the covered
  `! ESC &l1O` stream publishes the compact text bucket before orientation
  `1` and landscape geometry are installed. The covered `ESC &l66P !` stream
  writes extent `3300` and makes the following printable queue at compact
  coordinate `0x9001`; the covered `ESC &l0P` stream selects fallback page code
  `2`, mirrors `0x780e8f = 0x80`, signals `0x780e26 = 1`, writes text bottom
  `3240`, and reloads extent `3300`.
  Confidence is high for table lookups, page-size/orientation state writes,
  publication-before-mutation ordering, nonzero and zero page-length branches,
  and following printable placement because the cited fixtures cover both
  handler-level state and ROM-derived row construction.
  No unresolved ROM-local middle edge remains for the documented
  `ESC &l#A`, `ESC &l#O`, `ESC &l66P`, `ESC &l0P`, `ESC &l#C/#D`,
  `ESC &l#E`, or `ESC &l#F` paths. Remaining work is broader geometry
  cross-products that expose new consumer behavior; physical output, if
  captured, would be optional correlation outside the ROM render buffer.
- Raster graphics streams are covered for `ESC *t#R`, `ESC *r#A`, delayed
  `ESC *b#W`, lowercase transfer chaining, active-raster resolution behavior,
  row caps, beyond-extent drains, and modes 0/1/2/3. Evidence:
  [raster-graphics.md](raster-graphics.md),
  `Raster Transfer Gate And Encoded Rows` in
  [semantic-state-model.md](semantic-state-model.md), `Worked Path: Raster
  Transfer Gates And Modes` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md), host-fetched
  raster fixtures, and supporting report
  `generated/analysis/ic30_ic13_raster_graphics_flow.md`.
  The primary stream
  `ESC *t300R ESC *r1A ESC *b4W f0 0f aa 55` reaches parser handlers
  `0x10808`, `0x1075a`, and `0x11f82`. `0x11f82` schedules delayed transfer
  handler `0x105d0` through `0x121cc`; `0x12218` restores record
  `80 57 00 04 00 00` and calls `0x105d0` when payload bytes are available.
  The delayed record is not passed by volatile registers only: `0x12218`
  writes it back to the parser-record buffer, and `0x105d0` reopens
  `0x78299e - 6` at `0x105e4..0x105f2` before reading count word `+2`.
  Canonical raster state is rooted at `0x783170`: row coordinate `+0x02`,
  accepted count `+0x04`, overflow count `+0x06`, mode `+0x08`, origin
  `+0x0a`, scale `+0x0e`, maximum row byte count `+0x10`, and active flag
  `+0x12`. Canonical page state is the page-root bucket chain under `+0x1c`
  and encoded raster objects with class byte `0x80`, mode byte `+0x05`,
  capacity `+0x06`, packed key `+0x08`, and payload bytes at `+0x0a`.
  Accepted rows pass through `0x10084`, `0x13070`, `0x13250`, and `0x138de` to
  queue encoded raster objects such as
  `00 00 00 00 80 00 00 04 00 01 f0 0f aa 55`: class byte `0x80`, mode byte
  `0`, capacity `4`, packed key `0x0001`, and payload bytes at `+0x0a`.
  Parser scratch is delayed state `0x782a1a`, saved handler `0x782a1c`,
  snapshot bytes `0x782a20..0x782a25`, the restored `80 57 ...` record,
  payload offset and bytes, and skipped payload drained through `0xdace` or
  `0x12328`. The payload copier `0x138de` fetches through `0xa904` and locally
  normalizes `1a 58` to copied byte `00`.
  Derived/cache state is row bucket `0x782a7c`, packed key `0x782a7e`,
  per-object payload capacity `0x782a80`, orientation-derived row longword
  `D4`, render-record bucket roots copied by `0x1edc6`, and render-band
  destination fields.
  Firmware bookkeeping is current page root `0x78297a`, pending service bytes
  `0x782c72/0x782c73`, root active/retry bytes, stream allocator state
  `0x782a70/0x782a72/0x782a76`, allocation/copy stop flag `0x782996`, and
  post-transfer cursor advancement. `0x107fa` clears only active flag `+0x12`;
  while `+0x12` is set, `0x10808` resolution changes are ignored.
  Writers are `0x10808` for resolution-derived mode/scale, `0x1075a` for
  origin and active state, `0x107fa` for active clear, `0x11f82`/`0x121cc` for
  delayed transfer state, `0x105d0` for gate counts and row state, `0x10084`
  for root availability, `0x13070`/`0x13250` for row objects, and `0x138de`
  for payload bytes.
  Readers/consumers are `0x105d0` for the restored command record,
  `0x13070` for raster state, publication `0xff1e`, bridge `0x1ed84` /
  `0x1edc6`, bucket dispatch `0x1efc2`, and encoded raster renderer
  `0x1f88e`.
  Publication and rendering copy the bucket chain through `0xff1e`,
  `0x1ed84`, and `0x1edc6`; `0x1ef6a -> 0x1efc2 -> 0x1f88e` renders the object.
  Mode `0` copies literal words, while modes `1`, `2`, and `3` expand payload
  bytes into two, three, or four output rows through ROM expansion tables.
  The gate fixtures classify capped transfers, beyond-extent drains, negative
  rows, consecutive transfers, and active-resolution ignore as object or
  no-object outcomes before this same render path. Beyond-extent rows drain
  without ensuring a root; negative rows ensure a root, drain without queueing
  an object, and advance from row `-1` to `0`.
  Concrete output evidence includes fixtures `host-fetched raster stream
  reaches parser and queued pixels`, `host-fetched raster stream preserves
  0x1edc6 bridge contract`, `0x105d0-modeled raster transfer skip and cap
  gate`, `modeled raster command stream applies 0x105d0 byte-count cap`,
  `modeled raster command stream drains beyond-extent transfer without
  queueing`, `modeled raster command stream drains negative-row transfer and
  advances`, `0x13070/0x13250 raster row queues encoded-span object`,
  `0x1f88e mode-0 raster object renders queued literal row`, `0x1f88e
  mode-1 raster object expands queued bytes into two rows`, `0x1f88e mode-2
  raster object expands queued byte pair into three rows`, `0x1f88e mode-3
  raster object expands queued bytes into four rows`, and `host-fetched raster
  mode streams feed 0x1ed84 and 0x1ef6a`.
  Mixed composition evidence `host-fetched text rectangle and raster page
  record feeds 0x1ed84 and 0x1ef6a` and `addressed text/rule/raster field
  groups reach publication and render entry` checks that encoded raster objects
  share the same page-root, publication, bridge, and band-render path as
  compact text and rule objects.
  Confidence is high for delayed-record restore, `0x105d0` gate outcomes,
  root boundary, encoded object layout, bridge preservation, mode helpers,
  active-resolution behavior, lowercase `*b` chaining, dense
  capped-new-chunk/current-tail allocation through `0x132b6..0x13382`, and
  ROM-derived row construction for the cited streams. No unresolved ROM-local
  raster object, bridge, or render edge remains for the documented paths.
  Remaining work is new byte streams that expose different `0x105d8..0x10752`,
  `0x10084..0x10218`, `0x13070..0x13250`, or `0x132b6..0x13382` gate outcomes,
  accepted counts or drains, allocator state `0x782a70/0x782a72/0x782a76`,
  split capacity `0x782a80`, encoded object bytes
  `+0x04/+0x05/+0x06/+0x08/+0x0a..`, bridge bucket roots, copy-stop byte
  `0x782996`, packed-key advance through `0x332ee`, or mode-specific
  `0x1f88e` row-construction paths.
- Rectangle/rule streams are covered for size commands, fill selectors,
  clipping, no-room retry, bridge normalization, solid/pattern rendering,
  selector-7 text/rule page records, all non-solid selector IDs in text/rule
  page records, and the landscape pattern remaps. Evidence:
  [rectangle-graphics.md](rectangle-graphics.md), `Rectangle Rule Producer And
  Renderer` in [semantic-state-model.md](semantic-state-model.md),
  `Worked Path: Rectangle Rule` and `Worked Path: Rectangle Rule Selectors And
  Clipping` in [firmware-dataflow-model.md](firmware-dataflow-model.md),
  parser trace fixtures for `ESC *c` rule streams, and supporting reports
  `generated/analysis/ic30_ic13_rectangle_graphics_flow.md`,
  `generated/disasm/ic30_ic13_rectangle_graphics_010898.lst`, and
  `generated/disasm/ic30_ic13_display_list_helpers_013386.lst`.
  The primary chained stream `ESC *c12a5b0P` reaches handlers `0x10e68`,
  `0x10e22`, and `0x10898`: width field `0x78316a`, height field
  `0x783166`, and fill selector `7` for solid black. `0x10898` then calls
  clip/queue helper `0x10b80`, which consumes cursor `0x782c8a` /
  `0x782c8e`, extents `0x782db8` / `0x782db6`, orientation `0x782da3`, and
  current page root `0x78297a` to populate source record `0x782a88`.
  `0x13386` / `0x133aa` derive bucket/key fields `0x782a7c..0x782a7e`, allocate
  a 14-byte rule object through `0x1381c`, and insert it under page-root
  `+0x24`. The selector-7 object for the primary stream is
  `00 00 00 00 01 07 4a 00 00 0c 00 05 00 00`: bucket byte `+4`, fill
  selector `+5`, packed key `+6`, width `+8`, height `+0a`, and continuation
  `+0c`.
  Bridge `0x1edc6` copies page-root `+0x24` to render-record `+0x1c`, ORs
  selector byte `+5` with `0x10`, and copies height `+0x0a` into continuation
  `+0x0c`. `0x1ef6a` renders rule lists after bucket objects: `0x1f446`
  dispatches selector `7` to solid helper `0x1f596`, while gray selectors
  `0..6` and HP pattern selectors `8..13` dispatch to `0x1f4e0`.
  Canonical command state is rectangle width `0x78316a`, rectangle height
  `0x783166`, area-fill id `0x78316e`, cursor origin `0x782c8a` /
  `0x782c8e`, orientation `0x782da3`, page extents `0x782db8` /
  `0x782db6`, source record `0x782a88`, current page root `0x78297a`,
  page-root rule list `+0x24`, published rule list, and render-record rule
  list `+0x1c`.
  Derived/cache state is rule bucket/key state `0x782a7c`, `0x782a7d`, and
  `0x782a7e`, horizontal phase `0x782dc0`, bridged selector bit `0x10`,
  render continuation word `+0x0c`, pattern table selection, and render-band
  fields. Parser scratch is the mode state, command-record cursor `0x78299e`,
  and the six-byte records consumed by `0x10e68`, `0x10e22`, `0x10a40`,
  `0x10ae0`, `0x10dce`, and `0x10898`. Firmware bookkeeping is stream
  allocator state `0x782a70/0x782a72/0x782a76`, page-root retry bit
  `+0x15.0`, publication flag `0x782996`, scheduler cursors, and render-work
  progress.
  Writers are `0x10e68`/`0x10e22` for dot dimensions,
  `0x10a40`/`0x10ae0` for decipoint dimensions, `0x10dce` for area-fill id,
  `0x10898` for fill-selector mapping, `0x10b80` for clipped source record,
  `0x13386`/`0x133aa` for rule-list object insertion, `0x10d22..0x10d3e`
  for no-room retry publication, and `0x1edc6` for bridge normalization.
  Readers/consumers are `0x10b80` for cursor/extents/orientation clipping,
  `0x133aa` for page-root allocator and sorted rule-list insertion,
  publication `0xff1e`, bridge `0x1ed84` / `0x1edc6`, rule dispatcher
  `0x1f446`, solid helper `0x1f596`, and pattern helper `0x1f4e0`.
  Fill selector mapping is part of the byte-stream contract: missing or `0P`
  maps to selector `7`; `2P` maps area-fill percentages in `0x78316e` to gray
  selectors `0..7`; `3P` maps portrait pattern ids `1..6` to selectors
  `8..13`; landscape pattern ids `1..4` remap to `1 -> 9`, `2 -> 8`,
  `3 -> 11`, and `4 -> 10`.
  Concrete output evidence includes fixtures `rectangle command stream queues
  chained ESC *c rule object`, `0x11774 ROM dispatch table routes chained
  ESC *c rule stream`, `host-fetched rectangle rule stream preserves 0x1edc6
  bridge contract`, `host-fetched rectangle rule feeds 0x1ed84 and 0x1ef6a`,
  `0x10898 ESC *c#P maps fill selectors and queues rule object`,
  `0x10b80 rectangle fill clips negative left edge before queueing`,
  `0x10b80 rectangle fill clips right/top/bottom edges and ignores off-page
  fills`, `0x13386/0x133aa-modeled rectangle/rule list object and bridge
  normalization`, `0x133aa address-aware rule-list insertion uses 0x1381c
  storage`, `0x133aa no-room return preserves rule-list head`,
  `0x1f446/0x1f596 renders solid black rectangle rule pixels`, `0x1f596
  carries solid rule remainder across render bands`, `0x1f4e0 renders gray and
  HP pattern selector matrix`, `0x1f4e0 carries patterned rule remainder
  across render bands`, `0x1f4e0 renders sub-byte shifted HP pattern rule
  pixels`, `host-fetched alternate rectangle selectors feed full page records`,
  `host-fetched rectangle selector matrix feeds full page records`,
  `host-fetched text plus rectangle page record feeds 0x1ed84 and 0x1ef6a`,
  `addressed text plus rectangle stream matches page-record output`, and
  `rectangle parser trace feeds no-room retry path`.
  Output effect is deferred page-image state, not an immediate draw.
  Selector `7` renders through `0x1f596`; the solid crossing fixture starts at
  y `78`, draws two rows in the first band, carries three rows in `+0x0c`,
  and draws the remainder at y `0` in the next band. Non-solid selectors
  render through `0x1f4e0`; the selector matrix covers gray percent mapping,
  portrait pattern ids, landscape remaps, sub-byte masks, and continuation
  across render bands. Mixed fixture checks exercise the interpretation that
  the same rule list composes with compact text and encoded raster objects
  through the shared
  `0x1ed84 -> 0x1edc6 -> 0x1ef6a` render path.
  Confidence is high for parser handler order, dimension and fill-selector
  mapping, clipping/reject gates, rule object bytes, ordered insertion, bridge
  normalization, solid/pattern dispatch, continuation mutation across bands,
  no-room retry output, and mixed text/rule/raster composition.
  No unresolved software-visible middle edge remains for the covered
  selector-7, gray-selector, pattern-selector, landscape-remap, clipping,
  no-room retry, addressed-storage, publication, and mixed text/rule/raster
  streams. Remaining work is limited to byte streams that change clipping
  output, `0x1381c` rollover/allocation state, retry publication fields, rule
  object bytes, bridge state, render dispatch, or rendered rows.
- Reset, FF, page-size, orientation, paper-source, copies, and VFC publication
  paths are covered through `0xff1e` for current modeled page records. VFC
  coverage includes `ESC &l#W` delayed table payloads, lowercase
  same-family delayed-record preservation, channel-2 forward and before-top
  jumps, selector-zero top-of-form, selector-zero page eject, wrap hit,
  wrap no-hit, target-after-text publication, and non-publishing recovery
  paths. Evidence is tracked in `notes/vertical-forms-control.md` with
  branch boundaries `0x128ae..0x128f4`, `0x12966..0x129c4`,
  `0x129c6..0x12af8`, `0x12a22..0x12a78`, and `0x129ee..0x12b5a`.
  Related publication evidence is checked in under
  [publication-commands.md](publication-commands.md) and
  `Publication Commands To Rendered Page Records` in
  [semantic-state-model.md](semantic-state-model.md), with supporting reports
  `generated/analysis/ic30_ic13_esc_e_reset_flow.md` and
  `generated/analysis/ic30_ic13_page_root_finalization.md`.
  The shared publication path consumes current page root `0x78297a` through
  `0xff1e`, writes published pool pointer `0x780ea6`, sets publication flag
  `0x782996`, copies compact bucket root `+0x1c` and context slot `+0x2c`, and
  clears the current root before `0x1ed84` / `0x1edc6` bridge the published
  record into `0x1ef6a`.
  Canonical publication state is current page root `0x78297a`, published pool
  pointer `0x780ea6`, publication flag `0x782996`, compact/raster bucket root
  `+0x1c`, rule list `+0x24`, fixed list `+0x28`, context slots `+0x2c..`,
  pool-header state byte `+4`, copy-count word `+0x0c`, and command-side
  fields such as line-termination mode `0x78318f`, copy count `0x782da4`,
  paper-source byte `0x782da6`, pending refresh byte `0x782998`, and
  output/control bytes `0x780e8f` / `0x780e26`.
  Canonical VFC state is table `0x782dde..0x782edd`, VMI `0x783160`, top
  offset `0x782dce`, current y/x `0x782c8e` / `0x782c8a`, text margins
  `0x782dd6` / `0x782dda`, text-bottom cache `0x782dd2`, VFC limit
  `0x782dc2`, line caches `0x782ede` / `0x782edf` / `0x782ee0`, and modified
  layout flag `0x782ee1`.
  Derived/cache state includes render-band words `0x783a20`, `0x783a22`, and
  `0x783a28`, page-size/orientation active extents, VFC line-start and target
  calculations, default VFC table bytes from `0x12b96`, and row digests used
  only as fixture-check outputs. Parser scratch is the six-byte command record at
  `0x78299e`, delayed payload state from `0x121cc` / `0x12218`, and the
  `ESC &l#W` payload bytes consumed through `0xdace`.
  Firmware bookkeeping is page-record stream allocator state
  `0x782a70/0x782a72/0x782a76`, current-root clearing, pending text/span
  latches `0x782a58`, `0x782a6d`, and `0x783184`, `0x9ac2` wait/status
  servicing, `0xf124` page-eject state, and synthetic/nondefault `0xff1e`
  pool-header copies.
  Covered parser-to-publication streams are `! ESC E` through reset handler
  `0xcc52`, `ESC &k2G ! FF` through `0xedf8` and `0xf0f0`, `! ESC &l1A`
  through page-size handler `0xfc74`, `! ESC &l1O` through orientation handler
  `0x10220`, `! ESC &l2H` through paper-source handler `0xef62`, and
  `! ESC &l2X FF` through copy-count handler `0xeef0` before FF publication.
  The command-side fields are copy count `0x782da4`, paper-source byte
  `0x782da6`, pending paper-source refresh `0x782998`, output bytes
  `0x780e8f` / `0x780e26`, orientation `0x782da3`, and geometry fields updated
  after page-size/orientation publication.
  VFC table load `ESC &l#W` uses `0x11f6e -> 0x121cc -> 0x12218 -> 0x12cfe`
  to consume delayed payload bytes into table `0x782dde..0x782edd`, derive
  VFC limit `0x782dc2`, copy text-bottom cache `0x782dd2`, and clear modified
  layout flag `0x782ee1`. VFC channel jumps through `0x1280a` consume that
  table, VMI `0x783160`, top offset `0x782dce`, current y `0x782c8e`, and
  line caches `0x782ede` / `0x782edf` / `0x782ee0`.
  Writers are `0xcc52`, `0xf0f0`, `0xfc74`, `0x10220`, `0xef62`, and
  `0xeef0` for publication-triggering command state; `0xff1e` for published
  pool records; `0x11f6e` / `0x121cc` for delayed VFC payload scheduling;
  `0x12cfe` for explicit VFC table load; `0x12b96` and `0xe5e2` for default
  VFC/layout refresh; `0xfe54` for line-count caches; and `0x1280a`,
  `0xf06e`, `0xf34a`, and `0xf124` for cursor reset, pending-text flush, and
  page-boundary effects.
  Readers/consumers are parser loop `0x11774`, publication `0xff1e`, bridge
  `0x1ed84` / `0x1edc6`, render entry `0x1ef6a`, VFC consumer `0x1280a`,
  perforation overflow helper `0xf36c`, and later printable text through
  `0xd04a -> 0x12f2e`.
  Non-publishing VFC paths only reset x/y before the next `0xd04a` printable;
  publishing VFC paths call `0xf124 -> 0xff1e` so the pre-VFC printable renders
  from the old page and the following printable queues on a fresh page.
  Concrete publication evidence includes fixtures `publication streams tie
  parser handlers to page-record publication boundary`, `host-fetched
  publication streams reach parser and published rows`, `addressed printable
  reset publishes rendered page record`, `addressed printable FF publishes
  rendered page record`, `addressed page geometry publications render page
  records`, `addressed paper-source and copies publications render page
  records`, `host-fetched FF geometry and paper-source publications preserve
  0xff1e pool header defaults`, `host-fetched copies publication preserves
  0xeef0 pool header word`, and `host-fetched ESC E clears missing page root
  without publication`.
  Concrete VFC evidence includes fixtures `0x12cfe ESC &l#W loads vertical
  forms control state`, `mixed VFC definition stream consumes payload before
  printable page-record queue`, `mixed VFC lowercase delayed record survives
  until uppercase W`, `mixed VFC channel jump stream moves cursor before
  printable page-record queue`, `mixed VFC before-top channel jump normalizes
  start line before printable`, `mixed VFC selector-zero top-of-form no-op
  reaches printable page-record queue`, `mixed VFC selector-zero page-eject
  publishes old page before fresh printable`, `mixed VFC wrap-hit publishes old
  page before fresh printable`, `mixed VFC wrap-no-hit publishes old page and
  returns to top`, `mixed VFC target-after-text recovers near top before fresh
  printable`, `0x1280a VFC alternate high-start recovery entries`, and
  `0x12b96 default VFC table channel convention`.
  Output effect is page-boundary and cursor state, not direct drawing.
  Publication commands render already queued objects before side effects such
  as reset, page-size/orientation change, or paper-source output mutate the
  environment. VFC table definition changes later cursor/page behavior, and
  VFC channel jumps either move the following printable coordinate on the same
  page or publish the old page before the following printable queues on a fresh
  page.
  Confidence is high for parser handler order, host-byte draining, `0xff1e`
  pool headers, command side effects, VFC table bytes, delayed payload
  restoration, lowercase delayed-record preservation, cursor-only VFC paths,
  page-publishing VFC paths, render bridge fields, and final rows for the
  cited streams. Medium only for manual-facing names of derived line-count
  fields `0x782ede`, `0x782edf`, and `0x782ee0`.
  No ROM-local parser-to-publication, publication-to-render, VFC table-load,
  or VFC channel-jump middle edge remains for the documented streams.
  Remaining work is new byte streams that change page-record bucket shape,
  pool-header fields, bridge state, VFC line/cache state, or rendered rows.
- Macro replay streams are covered for definition, execute/call replay,
  mixed-control replay, overlay publication, repeated overlay publication,
  overlay skip gates, and overlay payloads that cross cursor, margin,
  transparent-data, raster, multi-row raster, and span-flush command families.
  Evidence: [macro-data-chain.md](macro-data-chain.md),
  `Worked Path: Macro Execute Replay` and
  `Worked Path: Macro Overlay Replay Publication` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md), and fixtures
  `macro execute data-chain replay feeds page-record stream`,
  `host-fetched macro replay payloads feed 0x1ed84 and 0x1ef6a`,
  `macro execute page-record layer composes with rule and raster band`,
  `macro overlay finalization replays before page publication`,
  `macro overlay replays across repeated page publications`,
  `macro overlay skip gates preserve base page publication`, and the overlay
  mixed-control, cursor-position, chained-margin, transparent, raster,
  multi-row raster, and span-flush publication fixtures. The reproduction
  effect is that replayed macro bytes become normal parser input through
  `0xa904`/`0x11774`; macro replay has no separate renderer.
  Macro command state starts with current macro id `0x783164` from handler
  `0xe112` and a 32-entry macro record pool at `0x782a98`. Each record stores
  payload-chain head `+0x00`, raw byte count `+0x04`, id word `+0x08`, and
  temporary/permanent byte `+0x0a`; selected record pointer `0x782d7a` is
  written by lookup helper `0xe0a4`.
  `ESC &f#X` handler `0xdd08` dispatches selectors `0..10`: definition start
  and stop, execute, call, overlay enable/disable, delete, and permanence
  controls. Definition appends payload through `0xe002` into linked `0x100`
  byte chunks. Execute/call selectors build data-chain frames through `0xe418`
  at active pointer `0x782d76`, with frame `+0x00/+0x04` copied from the macro
  record, byte `+0x08 = 4`, frame kind `+0x09 = 2` for execute or `3` for call,
  and snapshot pointer `+0x0a`.
  Canonical macro state is current macro id `0x783164`, 32 macro records at
  `0x782a98`, selected record pointer `0x782d7a`, record payload head
  `+0x00`, raw byte count `+0x04`, id word `+0x08`, permanence byte
  `+0x0a`, active data-chain frame pointer `0x782d76`, frame payload head
  `+0x00`, frame count `+0x04`, frame source byte `+0x08`, frame kind
  `+0x09`, snapshot pointer `+0x0a`, overlay state `0x782a92`, saved overlay
  id `0x782a94`, and call-context stack `0x782c1e..0x782c6d` with stack
  pointer `0x782c6e`.
  Canonical stored payload state is linked `0x100`-byte chunks written by
  `0xe002`: a longword next pointer followed by 252 payload bytes, with raw
  counts including four header bytes per allocated chunk. Canonical heap state
  is allocator free count `0x780e86`, bitmap pointer `0x783972`, payload base
  `0x783988`, bitmap limits/cursors `0x783976`, `0x78397a`, `0x78397e`,
  `0x783982`, and tracked byte count `0x783986`.
  Derived/cache state includes normalized macro payload count at selector `1`
  stop, environment snapshot chains from `0xe8f0`, flat non-replay snapshots
  under `0x7834c2`, overlay fixture coordinates and row digests, replayed
  page-record objects, and font-context refresh results from `0xe65c`.
  Parser scratch is normal mode-17 `ESC &f` command records, alternate/data
  `x/X` dispatch, definition-mode bytes `0x782c18` and `0x782c19`, the
  rewound command-record cursor `0x78299e`, and delayed payload records
  replayed from stored macro bytes.
  Firmware bookkeeping is host gate bit 1, frame-end cleanup through `0xe22c`,
  heap allocation/free chains through `0x170c` / `0x1710` / `0x18b4`,
  allocation-failure status through `0x9b5e(0x780e2e, 4)`, non-replay overlay
  layout refresh through `0xe5e2`, page-root retry flag `+0x14.0`, and parser
  reset/frame cleanup through `0x1240a`.
  Writers are `0xe112` for current id, `0xe0a4` for selected record,
  `0xdd08` and selector handlers `0xdd86..0xdf36` for macro control state,
  `0xe002` for payload chunks, `0xe418` for execute/call frames, `0xe4f4` for
  overlay non-replay frames, `0xe22c` for frame unwind, `0xe65c` for macro
  context/font refresh, and allocator helpers for heap-backed payload and
  snapshot chains.
  Readers/consumers are `0xdd08` for selector dispatch and guard checks,
  `0xe0a4` for record lookup, `0xe002` for definition append, `0xa904` for
  data-chain replay bytes, parser loop `0x11774` for replay dispatch,
  publication `0xff1e` for overlay detour, and the ordinary page/render
  consumers `0x1387c` / `0x1381c`, `0xff1e`, `0x1ed84` / `0x1edc6`, and
  `0x1ef6a`.
  `0xa904` gives those frame bytes priority over live host bytes, so replayed
  payloads re-enter parser loop `0x11774` and route through the ordinary
  handlers such as `0xd04a`, `0xf02c`, `0xedf8`, cursor/margin handlers,
  transparent handler `0x12452`, raster transfer `0x105d0`, and span flush
  `0x12714`. Page objects, publication, bridge, and render dispatch are then
  the normal `0x1387c` / `0x1381c`, `0xff1e`, `0x1ed84` / `0x1edc6`, and
  `0x1ef6a` path.
  Overlay state uses `0x782a92` and saved overlay id `0x782a94`. During
  publication, `0xff1e` consumes that state and page-root retry bit `+0x14.0`;
  when the enabled overlay record exists, `0xe4f4` builds a non-replay frame
  with kind `+0x09 = 4`, replays the stored payload before the same publication
  boundary, and `0xe22c` restores parser/page state afterward. Disabled,
  missing-record, or retry-flag skip gates preserve the base page publication.
  Concrete output evidence includes fixtures `0xe112 stores absolute parsed
  macro id`, `0xe0a4 macro record lookup uses head presence and first free
  slot`, `0xe002 appends macro definition bytes into 0x100 chunks`,
  `0xdd08 execute and call push macro data-chain frames`, `0xe418 frame
  metadata distinguishes execute and call context`, `macro execute frame
  payload feeds 0xa904 data-chain bytes`, `macro execute data-chain parser
  trace feeds page-record stream`, `macro call data-chain parser trace feeds
  page-record stream`, `host-fetched macro replay payloads preserve 0x1edc6
  bridge contract`, `host-fetched macro replay payloads feed 0x1ed84 and
  0x1ef6a`, `macro execute data-chain replay feeds page-record stream`,
  `macro mixed-control data-chain parser trace feeds page-record stream`,
  `0xe4f4/0xe22c produce and end data-chain frames`, and `macro snapshot
  helpers copy linked and flat environment ranges`.
  Overlay evidence includes fixtures `macro overlay finalization replays before
  page publication`, `macro overlay replays across repeated page publications`,
  `macro overlay skip gates preserve base page publication`, `macro overlay
  mixed-control payload publishes with page rule`, `macro overlay
  cursor-position payload publishes with page rule`, `macro overlay
  vertical-decipoint payload publishes with page rule`, `macro overlay chained
  cursor-position payload publishes with page rule`, `macro overlay chained
  margin payload publishes with page rule`, `macro overlay transparent payload
  publishes with page rule`, `macro overlay raster payload publishes with page
  rule`, `macro overlay multi-row raster payload publishes with page rule`, and
  `macro overlay span-flush payload publishes with page rule`.
  Output effect is stored-byte replay, not a macro-specific renderer.
  Execute/call replay of stored `!\r` queues the same compact text objects and
  rendered rows as live host bytes. Mixed-control replay of
  `ESC &k1G!\r!` writes line-termination state through `0xedf8` before
  ordinary text/CR handling. Overlay replay runs during `0xff1e` publication,
  adds replayed page objects to the page being finalized, and then publishes
  the combined base page plus overlay text/raster/span objects through the same
  bridge and render entry.
  Confidence is high for selector dispatch, record lookup, payload chunk
  format, execute/call frame metadata, data-chain byte-source priority,
  replayed parser dispatch, bridge/render equivalence, overlay replay before
  publication, repeated overlay publication, and overlay skip gates.
  Medium for manual-facing names of macro context-stack bytes and overlay
  state `0x782a92`; the ROM effects are documented even where names are
  inferred.
  No remaining macro execute/call replay, font-context refresh, overlay
  publication, repeated enabled-overlay publication, mixed-control overlay,
  cursor-position overlay, chained-margin overlay, raster overlay, multi-row
  raster overlay, span-flush overlay, transparent-data overlay, or overlay
  skip-gate middle edge remains for the documented streams. Remaining work
  must change replay-frame fields, skip-gate state, parser/delayed-payload
  dispatch, page-object fields, bridge roots, continuation fields, or
  ROM-derived row construction; over-deep context-stack failure behavior
  remains a separate external/manual boundary.
- The initial mixed page-image suite is covered for one complete
  host-fetched byte stream:
  `! ESC *c12a5b0P ESC *t300R ESC *r0A ESC *b2W c3 3c FF`.
  It drains through the modeled `0xa904` ring source, routes through the
  parser handlers above, queues compact text, a selector-7 rectangle
  rule, and a mode-0 raster object into addressed page-record storage,
  publishes through `0xff1e`, crosses the `0x1ed84` / `0x1edc6`
  render bridge, and derives the final composed rows from the documented
  render routines. Evidence:
  `Mixed Text/Rule/Raster Page Record` in `notes/semantic-state-model.md`.
  The representative page root has compact/raster bucket array `+0x1c`, rule
  list `+0x24`, and context slots `+0x2c`. Addressed fixtures place the text
  object at `0x00d0c004`, rule object at `0x00d0c02a`, raster object at
  `0x00d0c038`, and context slot 0 as `0x440946b4`. Publication preserves the
  bucket root as `00 d0 c0 04 80 00 00 02 00 00 c3 3c` and the selector-7
  rule list as `00 00 00 00 01 07 5c 01 00 0c 00 05 00 00`. Parser scratch
  for the delayed raster transfer is restored record `80 57 00 02 00 00`,
  delayed snapshot `01 00 01 05 d0 80 57 00 02 00 00`, payload offset `28`,
  and payload `c3 3c`. Firmware allocator bookkeeping ends at
  `0x782a70 = 0x00bc`, `0x782a72 = 0x00d0c000`, and
  `0x782a76 = 0x00d0c044`.
  The multi-row sibling documents bucket ordering for consecutive raster objects:
  bucket `+0x1c` chains `0x00d0d044 -> 0x00d0d038 -> 0x00d0d004`, so render
  dispatch sees the second raster row, first raster row, then compact text,
  with raster `row_y = 2`. Writers are the parser handlers
  `0xd04a`, `0x10e68`, `0x10e22`, `0x10898`, `0x10808`, `0x1075a`,
  delayed `0x105d0`, and FF handler `0xf0f0`; consumers are allocator
  `0x1381c` / `0x1387c`, publication `0xff1e`, bridge `0x1ed84` /
  `0x1edc6`, and renderer `0x1ef6a`. Render call order is
  `0x1ef86`, `0x1efc2`, `0x1f446`, `0x1f756`, with raster chain items going
  to `0x1f88e` and compact text going to `0x1effe`.
- The modeled per-band renderer now covers a crossing patterned rule
  together with compact text and a mode-0 raster row. Fixture
  `0x1ef6a page-band walk merges text raster and crossing rule`
  dispatches bucket-array compact/raster objects, carries the mutated
  rule node from band `0`, renders the remaining rule rows in band `5`,
  and leaves no rule/fixed-list residue. This closes the modeled
  per-band merge for that heterogeneous case.
  Derived render fields for the fixture include band/cursor state
  `0x783a20 = 0x0050`, `0x783a22 = 0`, and `0x783a28 = 0x00100000`.
  When `0x1f446` / `0x1f4e0` cannot finish the patterned rule in the current
  band, the mutated rule node remains on the render record with its row count
  reduced; the second-band entry consumes that carried node and finishes the
  rule while preserving the already-rendered text/raster rows. No unresolved
  software-visible middle edge remains for the documented text/rule/raster
  page-record fields, publication, bridge, bucket order, or per-band merge;
  future work belongs to byte streams that change object bytes, allocator
  state, bridge roots, render dispatch, or rendered rows.
- A downloaded-glyph page-image stream is covered for
  `ESC *c4660d37e5F`, `ESC )s2193W <0x0891 payload bytes>`, printable
  `%`, and FF publication. The fixture drains the same modeled `0xa904`
  source, preserves the control/payload/printable/publication byte
  boundaries, installs glyph `0x25`, publishes segmented buckets `1` and
  `9` through `0xff1e`, walks those published bucket words through
  `0x1ed84`/`0x1ef6a` band rendering, checks `0x1eba4` scheduler progression
  through band words `0..9`, and derives the published rows with bucket `9`
  producing the visible downloaded row. Evidence: fixtures
  `combined font download FF publishes installed glyph page record`,
  `published downloaded glyph segmented buckets render across bands`, and
  `0x1eba4 scheduler band words render published downloaded glyph`, plus
  `Downloaded Font Descriptor And Payload Chain` in
  `notes/semantic-state-model.md`.
  The FF publication stream is `2216` host bytes: font-control bytes
  `0..14`, downloaded-character payload bytes `14..2214`, printable `%` at
  `2214..2215`, and FF at `2215..2216`. Font control writes current font id
  `0x782f2e = 0x1234`, current character `0x782f30 = 0x25`, and marks the
  current downloaded-font record through `0x16df6`. The `ESC )s2193W` payload
  installs a split-plane downloaded glyph at record delta `0x0500`; after copy,
  return edge `0x15dc6 -> 0x16498 -> 0x15dcc -> 0x12328` leaves remaining
  count `0x783140 = 0`, drains zero bytes, and resumes at handler `0xd04a`
  for printable `%`.
  Printable `%` consumes the installed object through the ordinary
  `0xd04a -> 0x1393a -> 0x12f2e` path and queues segmented-wide selector
  `0x3003` for glyph `0x25`. Publication keeps bucket root
  `00 00 00 00 30 03 00 01 25 01 66 01...`, publishes bucket array entries
  `9` and `1`, leaves rule/fixed lists empty, copies context slots
  `0,0,0,0`, clears current root `0x78297a`, and sets publication flag `1`.
  `0x1ed84` seeds render work from that published record; `0x1ef6a` walks
  modeled band words `1` and `9`, dispatches both compact objects through
  `0x1effe`, leaves the bucket-1 segment-0 band blank for this payload, and
  renders the visible downloaded segment-1 row from bucket `9` at page row
  `86`. Scheduler fixture `0x1eba4 scheduler band words render published
  downloaded glyph` starts from the `0xff1e`/`0x1ed84` seed with source
  `+0x18` cleared and render work `+0x10/+0x16` zero, then produces
  `0x1ef6a` calls for band words `0..9`; only published buckets `1` and `9`
  dispatch compact objects.
- Downloaded-glyph/rule/raster render composition is covered for the
  host-fetched `ESC )s18W` even-span wide glyph install and a parser-driven
  page stream `ESC *c12a3b0P ) ESC *t300R ESC *r0A ESC *b2W c3 3c`. Evidence:
  fixture `parser-driven downloaded glyph rule raster stream composes through
  0x1ef6a`, which asserts the font/page fetch boundaries, page handlers
  `0x10e68`, `0x10e22`, `0x10898`, `0xd04a`, `0x10808`, `0x1075a`, and
  `0x11f82`, the `0x12f2e` glyph object, bridged selector-7 rule object,
  `0x13070` raster object, `0x1ed84`/`0x1ef6a` call order, dispatch targets
  `0x1f88e` and `0x1effe`, rule helper `0x1f596`, and final composed rows.
  Fixture `segmented downloaded glyph composes with raster through 0x1ef6a`
  extends the composition evidence to the `ESC )s258W` selector-`0x2003`
  segmented glyph family: bucket `9` contains the segment-1 object plus a
  mode-0 raster object, dispatches through `0x1f88e` and `0x1f1f0`, and
  renders digest
  `0b5440d6733ab9a072e0c14d1a470e6bc944dc98ddbf789152cf65c945dd0f01`.
  Fixture `split-plane segmented downloaded glyph composes with raster through
  0x1ef6a` covers the split-plane `ESC )s387W` sibling with glyph `0x28`,
  buckets `9` and `1`, the same bucket-9 raster object, dispatch targets
  `0x1f88e` and `0x1f1f0`, and digest
  `a380045041433910619b809637eda41e81842a3516acb83b488d07f1d3c68872`.
  Fixture `segmented downloaded glyph raster FF publications render page
  records` then publishes both segmented+raster records through `0xff1e`,
  preserves bucket `9` raster plus segment-1 objects and bucket `1`
  segment-0 objects, and renders the published records with the same two
  digests.
  The parser-driven even-span stream is one 54-byte `0xa904` ring fetch:
  font bytes `0..24` install the glyph, and page bytes `24..54` draw the
  rule/raster/text composition with no remaining ring bytes. The font phase
  reaches delayed handler `0x16c14` through `0x11eb6`, `0x12008`,
  `0x11ff6`, and `0x11f96`; `0x16498` installs glyph `0x29` by writing table
  entry `0x00ee`, record delta `0x0780`, record bytes
  `00 00 00 00 0c 01 00 01 00 90 00 00`, bitmap offset `0x078c`, bitmap
  size `18`, and the 18 linear bitmap bytes
  `f0 0f aa 55 3c c3 81 7e ff 00 18 e7 24 db 42 bd 66 99`. The page phase
  consumes the font-command helper's final header as the page memory image,
  then routes through page handlers `0x10e68`, `0x10e22`, `0x10898`,
  `0xd04a`, `0x10808`, `0x1075a`, and delayed `0x105d0`.
  The resulting page objects are bucket-5 downloaded glyph object
  `00 00 00 00 10 03 00 01 29 06 01...`, bridged selector-7 rule
  `00 00 00 00 05 17 08 01 00 0c 00 03 00 03`, and mode-0 raster object
  `00 00 00 00 80 00 00 02 00 00 c3 3c`. Render entry uses call order
  `0x1ef86`, `0x1efc2`, `0x1f446`, `0x1f756`: `0x1ef6a` dispatches the
  raster object to `0x1f88e`, the glyph object to `0x1effe` / `0x1f0d2`, and
  the rule to solid helper `0x1f596`. The derived rows are row `0` with
  raster payload `c3 3c`, downloaded glyph at x `22`, and rule from x `24`
  through x `35`, followed by rows `1` and `2` containing the rule only.
  Remaining variant work starts only when a byte stream changes the final
  header, installed record, post-install drain, following parser handler,
  page-object bytes, bucket assignment, dispatch target, or rows.
- Built-in and downloaded compact text rendering is composed from printable
  byte dispatch through visible rows for both selected source families:
  flagged built-in offset-table glyphs and unflagged inline/downloaded fixed
  records. Evidence:
  [font-context-metrics.md](font-context-metrics.md),
  [resource-rom.md](resource-rom.md),
  [downloaded-fonts.md](downloaded-fonts.md),
  `Text Source Objects And Compact Buckets` in
  [semantic-state-model.md](semantic-state-model.md),
  `Worked Path: Compact Text Source Classes And Selector Modes` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md), and supporting
  reports `generated/analysis/ic30_ic13_printable_text_path.md`,
  `generated/analysis/ic30_ic13_text_cursor_span_flow.md`,
  `generated/analysis/ic30_ic13_text_glyph_index_flow.md`,
  `generated/analysis/ic30_ic13_font_control_flow.md`, and
  `generated/analysis/ic32_ic15_builtin_glyph_payloads.md`.
  Parser loop `0x11774` leaves an unmatched printable host byte in `D5`;
  `0xd04a` normalizes over-`0xff` and high-bit cases, then calls
  `0x1393a(host_byte, 0x782d7e)`. `0x1393a` writes canonical source object
  `0x782d7e`: selected context pointer `+0x00`, glyph-entry or fixed-record
  pointer `+0x04`, mapped glyph word/byte `+0x0a/+0x0b`, and source-class
  flag `+0x10`. Source flag zero selects unflagged path
  `0xd140 -> 0xd3b2`; nonzero selects flagged built-in path
  `0xd550 -> 0xd824`.
  The paired positioning writers are now one semantic producer rather than two
  isolated handlers. `0xd140` and `0xd550` run prechecks `0xd28a` and
  `0xd6bc`, write gate result `0x782a6e`, compute advance, and commit cursor
  word `0x782c8a` only after queue/clamp handling. `0xd3b2` and `0xd824`
  write positioned source fields `+0x12`, `+0x14`, and `+0x16`, set live font
  flag `0x78297f + 0x78297e`, call `0x12f2e`, and share the same no-room
  retry through page-root flag `+0x14.0`, `0xff1e`, and `0x10084`.
  Concrete source examples are checked by fixtures:
  `0xd824-modeled positioned text source fields` maps built-in
  `LINE_PRINTER` host byte `0x21` to glyph `0x20`, glyph entry `0x015330`,
  flag `1`, source x `16`, y `0`, slot `0`;
  `0xd3b2-modeled unflagged source fields` maps host `0x21` to glyph `0x01`,
  fixed record `02 03 04 00 00 00 00 80`, source x `22`, y `22`, slot `3`.
  `0xd04a printable entry normalizes over-0xff and high-bit values` and
  `0xd04a high-character flags and selected slot choose mask behavior` bound
  the parser-side normalization before this source object is built.
  `0x12f2e` consumes source pointer `+0x04`, mapped glyph `+0x0b`, source flag
  `+0x10`, positioned fields, and context slot `+0x16`. It derives bucket
  index `0x782a7c`, compact coordinate/key fields, and selector bits, then
  calls `0x1387c` to reuse or allocate a compact object under page-root bucket
  array `+0x1c`. Short objects use size `0x26`, capacity `0x0a`, and
  `glyph, coord` entries. Segmented objects use size `0x28`, capacity `0x08`,
  and `glyph, segment, coord` entries. Width above the compact threshold sets
  selector bit `0x1000`; tall rows set bit `0x2000`; width plus tall rows set
  selector `0x3000`. Fixture
  `addressed 0x12f2e selector-mode matrix allocates and renders all compact
  modes` runs selectors `0x0003`, `0x1003`, `0x2003`, and `0x3003` through
  addressed page storage and render dispatch in one state block.
  Publication and rendering preserve the same object identity. `0xff1e`
  publishes the page-root bucket heads; bridge `0x1ed84` / `0x1edc6` copies
  bucket roots and context slots into the active render record; render entry
  `0x1ef6a -> 0x1efc2` sends compact-class bucket objects to `0x1effe`.
  `0x1effe` selects short renderer `0x1f034`, compact-wide renderer
  `0x1f0d2`, segmented renderer `0x1f1f0`, or segmented-wide renderer
  `0x1f264` from object byte bits `0x10` and `0x20`. Fixtures
  `compact text bucket object fixture rendered rows`,
  `constructed inline/downloaded wide glyph maps through 0x1f0d2`,
  `constructed inline/downloaded segmented glyph maps through 0x1f1f0`, and
  `constructed inline/downloaded segmented-wide glyph maps through 0x1f264`
  pin row output for the short, wide, segmented, and segmented-wide compact
  renderers. Byte-stream fixtures `single printable byte stream renders
  expected rows`, `two printable byte stream renders advanced glyph rows`, and
  `two printable byte stream with line-printer HMI renders subbyte rows`
  close the direct printable-byte to row-pixel path for ordinary built-in
  compact text.
  State classification for this cluster is explicit. Canonical state is source
  object `0x782d7e`, selected font context, current cursor words `0x782c8a`
  and `0x782c8e`, current page root `0x78297a`, selected context slot
  `0x78297e`, live-font flags, compact bucket objects, published bucket roots,
  and render-record bucket/context roots. Derived/cache state is precheck
  result `0x782a6e`, bucket index `0x782a7c`, compact coordinate/selector
  bits, glyph offsets, span watermarks `0x783186..0x78318a`, render-band
  fields `0x783a20`, `0x783a22`, `0x783a28`, and compact render cache
  `0x783a2c`. Parser scratch is `D5`, parser state `0x782999`,
  alternate/data mode `0x782c18`, high-character flags `0x783132` and
  `0x783133`, and the temporary normalization result from `0xd99a`. Firmware
  bookkeeping is stream allocator cursors `0x782a70`, `0x782a72`,
  `0x782a76`, page-root retry flag `+0x14.0`, publication flag `0x782996`,
  and render-progress fields after publication. The remaining unknown state is
  bounded to byte streams that change source-object fields, selected-map
  results, HMI/cursor advance, compact selector class, bridge context slots,
  helper dispatch, fallback splitting, or rendered rows.
  Confidence is high for source field meanings, paired writer behavior,
  `0x12f2e` short/segmented object shapes, selector bits, queue no-room retry,
  compact subdispatch, and row output for the cited fixtures. It remains
  medium for broader source-class cross-products. The exact unresolved ROM
  boundary is not between parser and compact renderer for the documented
  cases; it starts at new byte-stream
  variants through `0xd04a..0x12f2e` or compact helper variants through
  `0x1f034..0x1f264` that alter the object bytes or rendered rows.

## Canonical State Groups

- Host/input canonical state: `0x780e40`, `0x780e66`, `0x780e3b`,
  `0x783e54`, `0x783e56`, `0x783e76`, `0x783e78`, `0x783e8c`,
  `0x783e8e`, and `0x782d76` frame fields `+0x00`, `+0x04`, `+0x08`,
  `+0x09`, and `+0x0a`. Evidence:
  [host-byte-fetch.md](host-byte-fetch.md),
  `Host Byte Fetch And Data-Chain Input` in
  [semantic-state-model.md](semantic-state-model.md), and supporting report
  `generated/analysis/ic30_ic13_host_byte_fetch_flow.md`.
- Parser scratch: six-byte command records at `0x78299e..0x7829a7`,
  delayed handler snapshots, payload counters, and alternate/data mode state.
  Evidence: `Parser Record And Delayed Payload State` in
  [semantic-state-model.md](semantic-state-model.md), tokenizer fixtures, and
  `generated/analysis/ic30_ic13_parser_xrefs.md`. The parser-record checkpoint
  classifies canonical state (`0x782999`, `0x78299e`, `0x782c18`), tokenizer
  scratch (`0x782a26`, `0x782a2a..`, `0x782a3e`, `0x782a42..`,
  `0x783196..0x783199`), firmware bookkeeping (`0x78299a`, `0x782a1a`,
  `0x782a1c`, `0x782a20..0x782a25`, `0x782a56`), and derived font-designation
  records from `0x11efe` / `0x11f26`.
- Canonical print environment: cursor words `0x782c8a` and `0x782c8e`,
  HMI/VMI words, margins, page geometry fields under `0x782da2..0x782dc0`,
  line-termination mode, cursor stack, and font slot state. Evidence:
  [direct-control-codes.md](direct-control-codes.md),
  `Text Cursor And Direct Controls`, and page-geometry fixtures, including
  the `ESC *p#X/#Y` dot-position path through handlers `0xf48c` and
  `0xf692`. Those handlers convert parsed integer dot units to packed
  whole-dot cursor coordinates with `parameter << 16`, then share the
  `0xf4ca` / `0xf6e2` commit helpers before printable output is queued.
- Canonical page model: current page root `0x78297a`, page-root class byte
  `+4`, bucket array `+0x1c`, rule list `+0x24`, fixed-width list `+0x28`,
  context slots `+0x2c`, and stream allocator fields `0x782a70`,
  `0x782a72`, `0x782a76`. Evidence:
  [page-record-storage.md](page-record-storage.md) and
  `Shared Page-Record Storage And Allocator`.
- Derived/cache state: bucket/key bytes `0x782a7a..0x782a7e`, render-band
  fields `0x783a20`, `0x783a22`, `0x783a28`, pending span watermarks
  `0x783184..0x78318a`, raster mode/scale caches, delayed raster row
  coordinates, and mode-selected encoded raster object bytes. Evidence:
  `Text Span Flush And Fixed-Width Spans`,
  [page-raster-imaging.md](page-raster-imaging.md),
  `Bitmap Render Dispatch Contract` in
  [semantic-state-model.md](semantic-state-model.md), raster fixtures, and
  supporting report `generated/analysis/ic30_ic13_page_record_bridge.md`.
- Firmware bookkeeping: publication flag `0x782996`, page/root transient
  bytes `0x78297e`, `0x782c72`, `0x782c73`, retry flag bit in page-root
  `+0x14`, macro/data-chain frames, and heap/resource allocation metadata.
  Evidence: page-finalization, macro, allocator, and font-resource notes.
- Hardware/external state: physical host/interface and engine timing surfaces
  that the ROM observes but does not define as byte-stream semantics. The
  covered host-byte model starts after external events have produced
  ROM-visible bytes or status bits; remaining physical-interface work is
  mapping MMIO banks and serial/parallel/RS-422/optional-I/O signals rather
  than parser behavior. Evidence: [io-interfaces.md](io-interfaces.md) and
  [host-byte-fetch.md](host-byte-fetch.md). Formatter/DC timing is similarly
  external after the ROM-visible scheduler state: notes
  [page-raster-imaging.md](page-raster-imaging.md) and
  [dc-controller-engine.md](dc-controller-engine.md) track unresolved mapping
  from `$a200`, `$a400`, `0xffff2000`, `$a601`, `$a801`, `$aa01`,
  `0xfffe0001`, and `0xfffe0003` to connector signals such as `BD`, `VDO`,
  `VSREQ`, `VSYNC`, `PRNT`, `CMND`, `CCLK`, `CBSY`, `STATS`, `PCLK`,
  `SBSY`, `RDY`, `PPRDY`, and `CPRDY`. Timing-sensitive ROM ranges
  `0x0f84..0x1282`, `0x1cf8..0x1ea8`, and active-render handoff
  `0x1eb2a..0x1ed84` are modeled as ROM-visible state machines; the residual
  boundary is when physical events make status bits, wait objects, and engine
  readiness change.
- Unknown or unresolved state: explicit bounded edges rather than generic
  gaps. The remaining pixel-affecting resource-window edge is the secondary
  transparent-data segmented source read at firmware range
  `0x0c0000..0x0c0321`. The software path to that read is documented through
  `0x12452`, page-record storage, bridge, and compact renderer `0x1f1f0`; the
  unresolved part is physical ROM decode after verified resource-pair suffix
  `0x0bfe22..0x0bffff`. Evidence:
  [transparent-print-data.md](transparent-print-data.md),
  [resource-rom.md](resource-rom.md), and
  [built-in-resource-scan.md](built-in-resource-scan.md).

## Pixel-Perfect Coverage And Residual Risks

These are the highest-value coverage areas and residual risks because each can
change rendered pixels, byte-stream compatibility, or final confidence. Most
entries below are composed ROM contracts with bounded remaining variants rather
than open middle edges.

1. Font/context span metrics are composed from downloaded descriptor bytes to
   visible span output. The producer side is documented in
   [downloaded-fonts.md](downloaded-fonts.md); the selected-context and
   consumer side is documented in
   [font-context-metrics.md](font-context-metrics.md) and
   `Text Span Flush And Fixed-Width Spans` in
   [semantic-state-model.md](semantic-state-model.md).
   `0x1719c` copies accepted type-0, type-1, and type-2 descriptor fields into
   the allocated font payload. The metric producers are now concrete formulas:
   `0x17430` derives flagged height/count field `+0x18 = +0x14 - +0x16 - 1`,
   `0x1757a` writes rounded/clamped unflagged field
   `+0x2c = min((value + 2) >> 2, word(+0x14)) << 2`, and `0x1762a` writes the
   signed flagged offset word `+0x1a`.
   The consumers are paired with the text source class. Unflagged span helper
   `0xd4ac` reads context bytes `+0x2b`, `+0x2c`, and `+0x2d`; flagged helper
   `0xd8fc` reads words `+0x16`, `+0x18`, and `+0x1a`. Both consume current y
   `0x782c8e`, page extent `0x782db6`, pending-span flag `0x783184`,
   alternate-y flag `0x783185`, and x/y watermarks `0x783186..0x78318a`.
   Their output is either no span update, a threshold/high-water update, or a
   flush through `0x12714` / `0x126e2` into page-record span objects, followed
   by the ordinary page publication, bridge, and render path.
   State classification for this cluster is explicit. Canonical state is the
   selected font context, copied descriptor payload fields, source object
   `0x782d7e +0x00` context pointer, current cursor, page extent, and pending
   span state `0x783184..0x78318a`. Derived/cache state is the formula output
   fields `+0x18`, `+0x1a`, and `+0x2c`, rounded/clamped metric values, and
   the page-record span object written after a low-x flush. Parser scratch is
   the `ESC )s#W` payload counter and validation scratch consumed before
   `0x1719c`. Firmware bookkeeping is allocation/install state and candidate
   refresh state around the downloaded font resource. Unknown/manual state is
   limited to HP-facing names for validation entries that the ROM consumes but
   does not copy into the staged metric fields.
   Fixtures cover the branch family and parser-produced value classes rather
   than single isolated constants. `d4ac and d8fc span consumer branch family
   controls flush output` covers disabled, lower-bound, page-extent, and high-x
   consumer outcomes for both source forms. `host-fetched metric variant
   changes d4ac gate and d8fc rows`, `host-fetched clamped metric variant
   changes d4ac gate and d8fc rows`, `host-fetched lower-bound metric variant
   suppresses d4ac and d8fc spans`, and `host-fetched upper-bound metric
   variant keeps d4ac span but suppresses d8fc` check that fetched descriptors can
   flip each consumer gate while compact glyph objects still queue and render.
   The legal value matrices then classify the remaining formula space:
   `legal descriptor metric value matrix drives d4ac and d8fc consumers`,
   `legal descriptor metric boundary values drive d4ac and d8fc consumers`,
   `legal descriptor metric low-nibble rounding drives d4ac and d8fc
   consumers`, `legal descriptor metric byte-boundary rounding drives d4ac and
   d8fc consumers`, `legal descriptor metric mixed values drive d4ac and d8fc
   consumers`, and `legal descriptor metric tight range values drive d4ac and
   d8fc consumers`.
   Concrete checked examples include the zero-offset legal case copying
   `+0x14/+0x18/+0x1a/+0x2c = 0x0018/0x0013/0x0000/0x0000`, preserving the
   standard `d4ac` span digest and making `d8fc` publish high-y `21`; the
   midpoint case copying `0x0018/0x0013/0x0007/0x0018` and moving `d8fc`
   high-y to `14`; the negative-offset case copying
   `0x0018/0x0013/0xfffe/0x0008` and making `d8fc` compute high-y `-65513`;
   the byte-boundary rounded cases `0x00fd`, `0x00fe`, `0x0101`, and `0x0102`;
   and the mixed case `0x0008/0x0030/0x002a/0x02`, which suppresses `d4ac` as
   beyond page extent while rendering `d8fc`.
   Seven validation no-install forms plus the short-budget `ESC )s8W` entry-5
   failure document parser-to-validation rejection, allocation skip, no candidate
   install, resumed default-font printable output, and derived rows. Therefore
   the remaining metric work is not an unresolved ROM-local producer-to-consumer
   edge. It is regression expansion or selected-font cross-products only when a
   new byte stream changes copied fields, consumer branch, page-record span
   object, or rendered rows; HP/manual field naming remains external.
2. VFC table definition and channel jumps now have a tracked command-family
   contract in `notes/vertical-forms-control.md`. That contract groups
   canonical VFC state `0x782dde..0x782edd`, canonical layout inputs
   `0x783160`, `0x782dce`, `0x782c8e`, `0x782c8a`, and margins
   `0x782dd6`/`0x782dda`; derived line caches `0x782dd2`, `0x782dc2`,
   `0x782ede`, `0x782edf`, and `0x782ee0`; parser scratch `0x78299e`;
   and firmware bookkeeping `0x782ee1`, `0x782a58`, `0x782a6d`,
   `0x783184`, and `0x78297a`. The documented output effects cover delayed
   payload consumption before printable text, cursor-only channel jumps,
   top-of-form no-op, selector-zero publication, wrap-hit publication,
   wrap-no-hit publication, target-after-text publication, and
   non-publishing recovery. The remaining VFC risk is HP/manual names for the
   derived line-count fields, not an unresolved middle edge in the documented
   `ESC &l#W` / `ESC &l#V` path.
   The adjacent perforation-skip command is also no longer only a parser-state
   toggle: `ESC &l#L` writes `0x783191` through handler `0xee64`, and fixture
   `0xf36c perforation skip gates vertical overflow page eject` checks the
   visible consumer at `0xf36c`. Page ejection through `0xf124` occurs only
   when `0x782c8e > 0x782dc2`, `0x782dc2` is nonzero, and `0x783191` is
   nonzero; below-limit, zero-limit, and disabled-skip cases return `D7 = 1`
   without publication.
3. Macro replay and overlay publication are composed as stored-byte input
   sources, not as a separate renderer. Checked-in documentation is
   [macro-data-chain.md](macro-data-chain.md),
   `Macro Definition And Data-Chain Replay` in
   [semantic-state-model.md](semantic-state-model.md), and the macro worked
   paths in [firmware-dataflow-model.md](firmware-dataflow-model.md).
   Canonical macro state is current id `0x783164`, macro record pool
   `0x782a98`, selected record pointer `0x782d7a`, record fields `+0x00`,
   `+0x04`, `+0x08`, and `+0x0a`, active data-chain frame pointer
   `0x782d76`, frame fields `+0x00`, `+0x04`, `+0x08`, `+0x09`, and
   `+0x0a`, overlay state `0x782a92`, saved overlay id `0x782a94`, and
   call-context stack `0x782c1e..0x782c6d`. Parser scratch is mode-17
   `ESC &f` command records, alternate/data definition-mode state, replayed
   payload bytes, delayed transparent/raster records, and the parser-mode
   state active inside a non-replay frame. Firmware bookkeeping is chunk
   allocation, environment snapshots, host gate bit 1, frame cleanup through
   `0xe22c`, page-root retry flag `+0x14.0`, and page publication state.
   Execute/call selectors build replay frames through `0xe418`: frame byte
   `+0x09` is `2` for execute and `3` for call. `0xa904` gives those frames
   priority over live host bytes, so stored payloads re-enter parser loop
   `0x11774` and reach ordinary handlers such as `0xd04a`, `0xf02c`, and
   `0xedf8`. Overlay selector `4` is consumed during publication:
   `0xff1e` checks `0x782a92`, saved id `0x782a94`, and root retry flag
   `+0x14.0`; if replay is enabled, `0xe0a4` reselects the macro and
   `0xe4f4` builds a non-replay frame with `+0x08 = 4` and `+0x09 = 4`
   before publication proceeds. Disabled overlay mode, missing selected
   record, and retry-flag cases skip replay and publish the base page.
   The documented overlay matrix covers one end-to-end path for each covered
   command family: mixed controls `ESC &k1G!\r!`, cursor `ESC &a2C!`,
   vertical decipoints `ESC &a72V!`, chained cursor `ESC &a2c+1R!`, chained
   margins `ESC &a6l9M!`, transparent data `ESC &p2X!!`, one-row raster
   `! ESC *t300R ESC *r0A ESC *b2W c3 3c`, multi-row raster
   `! ESC *t300R ESC *r0A ESC *b2W f0 0f ESC *b2W 0f f0`, and span flush
   `ESC &a6L!`. These payloads replay through the normal parser and queue
   compact text, span, rule, or raster page objects before the same
   `0xff1e -> 0x1ed84 -> 0x1edc6 -> 0x1ef6a` render path. Evidence fixtures
   include `macro overlay finalization replays before page publication`,
   `macro overlay replays across repeated page publications`, `macro overlay
   skip gates preserve base page publication`, `macro overlay mixed-control
   payload publishes with page rule`, `macro overlay cursor-position payload
   publishes with page rule`, `macro overlay vertical-decipoint payload
   publishes with page rule`, `macro overlay chained cursor-position payload
   publishes with page rule`, `macro overlay chained margin payload publishes
   with page rule`, `macro overlay transparent payload publishes with page
   rule`, `macro overlay raster payload publishes with page rule`, `macro
   overlay multi-row raster payload publishes with page rule`, and
   `macro overlay span-flush payload publishes with page rule`.
   No remaining ROM-local middle edge remains for macro execute/call replay,
   overlay re-entry at `0xff1e`, repeated enabled-overlay publication, the
   documented overlay payload families, or overlay skip gates. Remaining macro
   work starts only from broader payload variants that change parser dispatch,
   page-object fields, delayed payload state, replay frame state, or rendered
   rows.
4. Active-record selection and render-band scheduling are documented as a
   ROM-internal reproduction boundary, rather than a page-object gap. Fixture
   `0x1eb2a/0x1ecd6 selects published record for render entry` checks
   `0x780eaa -> 0x780eae`, work-record alternation through `0x7820bc`, active render
   pointer `0x783a18`, and `0x1ed84`/`0x1ef6a` output for a published page/control
   record. Fixture `0x1958/0x1c04/0x1eea staged candidate reaches render scheduler`
   checks candidate staging, `0x1fd4` slot insertion, state-4 release, and
   candidate promotion through `0x7ec6..0x7f90`. Fixture
   `0x1eba4/0x1ef6a active render loop advances or yields bands` covers
   cleanup, throttle, capacity-wait, and render-call branches, while fixture
   `0x1eba4 scheduler band words render published downloaded glyph` checks
   the ROM-local interpretation of scheduler-produced band words `0..9`
   against a published downloaded-glyph record.
   The remaining scheduler risk is not a ROM object/rendering middle edge: it is
   board-level timing for `$8000.4`
   selection at `0x0f84..0x0fa0` and `0x1020..0x102e`, MMIO effects around `$a601 =
   0xfd`, `$a801`, `$aa01`, `0xfffe0001`, and `0xfffe0003`, and the physical event
   timing that drives modeled wait-object/trap states through `0x10bc..0x11f8` and
   `0x123a..0x1282`. Evidence: `Published Record To Active Render Scheduler` in
   `notes/semantic-state-model.md` and `Active Render Scheduler` in
   `notes/page-raster-imaging.md`.
5. Downloaded font support now has tracked documentation for descriptor,
   resource-payload, current-record, bit-30-clear resource-object, bit-30-clear
   resource-object no-install exits, even-span and split-plane continuation resume,
   status-0 fixed-record release, bit-30 offset-table release delegate, release reject
   no-rewrite exits, split-plane character-object, linear character-object, and
   downloaded-glyph render paths in `notes/downloaded-fonts.md`. The `0x16c14`
   existing-record allocation-failure teardown through `0x1887a` is documented for the
   bit-30-clear extended fixed-record case with fixture checks, and the direct `0x1887a`
   release variant matrix now covers bit-30-set class-one, bit-30-set class-zero, and
   bit-30-clear class-zero cleanup branches. The `0x16fae` validation table now has
   ROM-effect names for all 32 entries plus concrete success and failure fixtures, and
   host-fetched invalid-resource-type, first-code overflow, zero line/count, high
   line/count, reversed-range, high range/count, and invalid-class paths document
   parser-to-validation no-install boundaries plus following-printable default output.
   The nonzero `ESC )s#W` resource-payload path is composed in
   `notes/semantic-state-model.md` under `Nonzero Resource Payload Checkpoint`: the
   documented state now spans ROM parser restore, `0x16fae` validation,
   `0x17026`/`0x1719c` allocation, `0x16c14`/`0x1bc38` candidate insertion, `0x14c64`
   consumption, integrated `ESC )s3W` downloaded-pointer glyph install, and page-visible
   `d4ac`/`d8fc` metric consumers. Fixture `host-fetched resource header plus glyph
   payload renders offset-table downloaded glyph` closes the basic type-0 `ESC )s80W`
   plus linear three-row glyph boundary without fixture-side mutation. Fixture `type-1
   and type-2 resource headers accept downloaded glyph payload stream` closes the same
   fetched-glyph boundary for legal type-1 and type-2 headers. Fixture `type-1 and
   type-2 resource glyph FF publications render page records` now adds the legal
   type-1/type-2 publication sibling: `ESC )s3W` plus printable `!` and FF publishes
   bucket `1`, preserves candidate contexts `0x40000000` and `0x44000000`, dispatches
   the span through `0x1f812` and the glyph through `0x1effe`, and renders the same
   rows. Fixture `type-1 and type-2 resource wide glyph FF publications render page
   records` adds the legal wide sibling: `ESC )s18W` plus printable `!` and FF publishes
   bucket `1`, preserves the same candidate contexts, dispatches the span through
   `0x1f812`, dispatches compact-wide object byte `0x10` through `0x1effe` to `0x1f0d2`,
   and renders digest
   `3985c4c7f33d361e0673e7361ce58aa1b9ba12bd003a2b9166eaddb93888e11e`. Fixture `type-1
   and type-2 resource segmented glyph FF publications render page records` adds the
   legal segmented sibling: `ESC )s258W` plus printable `!` and FF publishes bucket `9`,
   preserves bucket `1` as span plus segment `0`, dispatches compact object byte `0x20`
   through `0x1effe` to `0x1f1f0`, and renders digest
   `f449349d69d7acaff44a3f753253e4ef626057d41a5c8f6d827ce871bfc089b4`. Remaining work
   for this cluster is now broader glyph row/span/continuation shapes beyond the covered
   short, wide, and segmented glyphs and publication variants outside those legal
   type-1/type-2 span+glyph page-record shapes. Downloaded-character coverage now
   includes parser-produced normal, wide/control, even-span wide, segmented, split-plane
   segmented, and segmented-wide compact render shapes, and the combined
   downloaded-glyph stream now reaches FF publication with both segmented buckets
   preserved and scheduler-produced band words `0..9` rendered. The combined
   segmented-wide publication fixture now also pins the full-success return boundary:
   `combined font download FF publishes installed glyph page record` leaves `0x783140 =
   0`, drains zero bytes through `0x12328`, and resumes at handler `0xd04a` for
   printable `%` before FF publication. The payload-control wide sibling now has its
   nonzero return drain pinned: fixture `host-fetched payload-control downloaded glyph
   FF publishes page record` carries normalized `1a 58`, selector `0x1003`, bucket `1`,
   `0xff1e`, `0x1ed84`, and `0x1ef6a` to the same `0x1f0d2` modeled row, while the
   same-stream return leaves `0x783140 = 1`, drains the following `&` through `0x12328`,
   and leaves FF for handler `0xf0f0`. The rows-`0x82` segmented sibling now publishes
   through FF as well: fixture `host-fetched rows-0x82 segmented downloaded glyph FF
   publication renders page record` carries `ESC )s260W`, selector `0x2003`, buckets `1`
   and `9`, `0xff1e`, `0x1ed84`, and `0x1ef6a` to two `0x1f1f0` segment-1 rows. The
   rows-`0x20` short sibling now publishes through FF too: fixture `host-fetched
   rows-0x20 short downloaded glyph FF publication renders page record` carries `ESC
   )s64W`, selector `0x0003`, bucket `1`, `0xff1e`, `0x1ed84`, and `0x1ef6a` to `38`
   visible `0x1fe76` rows. The rows-`0x40` short sibling now publishes through FF as
   well: fixture `host-fetched rows-0x40 short downloaded glyph FF publication renders
   page record` carries `ESC )s128W`, selector `0x0003`, bucket `1`, `0xff1e`,
   `0x1ed84`, and `0x1ef6a` to `64` blank current-band `0x1fe76` rows. The accepted
   descriptor-record mode-byte boundary for this helper table is now documented by
   fixture `0x16b1a descriptor width helper emits only mode 1/2`: `0x16b36..0x16b6a`
   writes only mode `1`/`2` from span parity, and `0x16b26..0x16b34` rejects invalid
   widths without scratch writes. Fixture `0x15d0a descriptor grammar exits and handler
   matrix` covers the zero-count descriptor route's early drains and all four
   current-record/continuation by bit-30 handler polarities. The bit-30-clear
   fixed-record current-record and linear/split-plane continuation full-success
   boundaries now pin `0x15e42 -> 0x16606 -> 0x15dcc -> 0x12328` and `0x15e64 -> 0x15c4c
   -> 0x15dcc -> 0x12328` with zero drains before handler `0xd04a`. The field grouping,
   writers, consumers, output effect, and exact unresolved variant boundaries for those
   resource-object fixtures are composed in `notes/semantic-state-model.md` under
   `Fixed-Record Resource Object Checkpoint`. Other release variants and full-success
   return-boundary siblings are now classified as regression cross-products unless they
   expose a different `0x783140` remainder, `0x12328` drain status, next handler, or
   page-record selector from the even-span rule/raster path, row-count matrix,
   wide-remainder matrix, segmented-wide matrix, high-row segmented-wide matrix,
   segmented, split-plane segmented, segmented-wide publication, payload-control
   publication, and bit-30-clear fixed-record fixtures. The wrapped source-width-byte
   branch is now fully classified for `0x00..0x10` and `0x11..0xff`; remaining work
   there is the ROM-local invalid compact-mode-0 helper target behavior, not
   parser-state discovery. Fixture `0x15c4c partial resource resumes update
   continuation state` covers the fixed-record continuation route's status-`2` resave
   behavior for linear and split-plane bit-30-clear resource objects. ROM-internal
   descriptor-validation error visibility is documented at the rejecting predicate
   boundary instead: fixture `ESC )s#W validation failures preserve following printable
   output` carries the seven `ESC )s80W` predicate failures plus the short-budget `ESC
   )s8W` entry-`5` failure through the following default-font page path. The remaining
   descriptor-validation gap is external HP/manual naming for consumed-but-not-staged
   fields. The mode-byte-`0` no-install boundary is documented separately: fixture
   `0x16498 replacement allocation failure partial and rejected downloaded character
   exits preserve state` checks the unchanged table/header interpretation at object
   boundary `0x16498`, and fixture `0x16498 no-install exits preserve following
   printable output` checks that the following printable and FF publication stay on the
   unchanged default-font page path. The even-span downloaded-glyph plus rule/raster
   composition now has an exact modeled install-to-page handoff: host-fetched `ESC
   )s18W` produces the resource image consumed by the parser-driven page stream,
   including glyph `0x29`, table entry `0x00ee`, record delta `0x0780`, bitmap offset
   `0x078c`, and the 18 copied bitmap bytes. The same fixture checks the byte-source
   interpretation as one 54-byte `0xa904` ring fetch: font bytes `0..24`, page bytes
   `24..54`, and no remaining ring bytes. ROM control flow now narrows the post-install
   return boundary: disassembly
   `generated/disasm/ic30_ic13_font_payload_setup_015b80.lst` shows `0x15dc6 -> 0x16498
   -> 0x15dcc -> 0x12328`, where `0x15dcc` passes the remaining `0x783140` count to
   `0x12328`; the fixture pins this instance with copy status `1`, copy stream position
   `18`, remaining `0x783140 = 0`, zero-byte drain, and next parser handler `0x10e68`.
   The no-install visible-output fixture pins the same return edges with `0x783140 = 6`,
   six drained rejected-payload bytes, and next handler `0xd04a`; the status-`2`
   partial-install fixture pins the linear/split returns with `0x783140 = 0`, zero
   drain, and next handler `0xd04a`. The downloaded-glyph publication fixtures now also
   pin normal, row-`0x80`, linear-segmented, and split-plane segmented full-success
   publication returns with `0x783140 = 0`, zero drain, and next handler `0xd04a`. The
   combined segmented-wide publication fixture pins the same zero-drain return for
   selector `0x3003`: `0x783140 = 0`, zero drain, and next handler `0xd04a`. The
   payload-control wide publication fixture pins the nonzero return sibling: `0x783140 =
   1`, drained byte `0x26`, and post-return handler `0xf0f0`.
6. Hardware-facing host modes are behaviorally modeled above `0xa904`, but
   MMIO identity and electrical timing for Centronics/serial/RS-422 are not
   board-confirmed. This does not block the documented byte-stream renderer;
   it only blocks hardware-level emulation claims. Evidence:
   [host-byte-fetch.md](host-byte-fetch.md) and supporting report
   `generated/analysis/ic30_ic13_host_byte_fetch_flow.md`.
7. Final device-output correlation is outside the ROM evidence model and is
   not a completion condition. The checked-in model derives rows from
   disassembly and ROM data. The initial
   mixed page-image stream above is a ROM-derived internal reproduction
   contract, not a physical-device validation artifact. The font-sample
   printout now has its own
   internal rendered-surface checkpoint: fixture `font sample full printout
   segments render through 0x1ed84 and 0x1ef6a` renders all eight source/class
   page-record segments with aggregate digest
   `5e5e735b4fb2a2a4dff4794099a02eaf23fa2dd3e469df8d053db88a321ea6f2`.
   Fixtures `font sample heading continuation emits fresh source heading page
   record` and
   `font sample cartridge heading continuations emit source-specific page
   records` now cover internal and cartridge heading-preflight
   page-record objects. Fixture `font sample row continuation emits fresh
   source heading page record` covers the row-overrun `I01` forced
   page-record object; fixture
   `font sample class-one row continuation emits fresh source heading page
   record` covers the class-one `I16` sibling from `0x40099d18` to
   `0x4409a0e4` with bucket digest
   `842dd781a1093819f918e128999786f94f16cc3562ca25c3a82503ced74f3f3c`.
   Fixture
   `font sample alternate-row continuation emits preadvanced row page record`
   now covers the alternate-row caller edge after `0x1d868` returns D7 `1`:
   `0x1c4a4 -> 0x1d868 -> 0x1c4b6 -> 0x1c9f6 -> 0x1c4ca -> 0x1ca2c ->
   0x1c4d4 -> 0xf06e -> 0x1c4e8 -> 0x1d050 -> 0x1c4f2 -> 0x1cabe`.
   It emits `I01COURIER101210U` after pre-row y advance
   `0x00520000 -> 0x00900000` and pins bucket digest
   `c6f0cbe07a7681d3ecfd3447b8296e97cbf8042d6d962d825f6018d980d5396b`.
   Broader row-overrun cross-products remain static-model expansion work.
   Physical baseline/cell placement names, if needed, are external correlation
   rather than ROM execution evidence.

## Next Disassembly Targets

The next work should follow dataflow, not isolated handlers. Start from these
boundaries only when new evidence changes the documented state or pixel output.

1. Transparent secondary segment-57 resource decode remains the highest
   pixel-affecting external-data boundary. The parser, filtering, page-record,
   bridge, and renderer path is documented in
   [transparent-print-data.md](transparent-print-data.md) and the Transparent
   Print Data section above. The unresolved input is physical/resource-window
   data for firmware range `0x0c0000..0x0c0321`, after verified resource-pair
   suffix `0x0bfe22..0x0bffff`. Useful next evidence is board/emulator decode
   for that range, startup candidate counters after `0x1a2e4`, direct bus reads
   around `0x0c0000`, or a board-level memory-map explanation for which
   continuation policy the ROM address bus actually sees. Do not re-trace `0x12452`,
   transparent filtering, secondary buckets through `448`, or compact renderer
   arithmetic unless new decode evidence contradicts the current boundary.
2. Reset/default provenance is no longer a ROM-local parser/page/render gap.
   [reset-default-environment.md](reset-default-environment.md) and
   `Default Environment Record Producers` cover the reset consumer, default
   backing-record producers, retained-record helpers, page-root publication,
   HMI/VMI conversion, and addressed compact-bucket publication. Remaining work
   is external: the device or panel protocol behind `$8000.w`,
   retained-storage identity and board-level serial pins behind `$a400` /
   `$8c01`, physical retained-storage failure/content conditions behind
   `67 SERVICE` and `68 SERVICE`, manual wording for retained-record failures,
   and physical self-test placement.
3. Font metrics, font selection, downloaded-glyph row/span publication, and
   macro overlay replay are composed checkpoints. Treat additional cases as
   regression expansion unless a byte stream changes a named state boundary:
   copied metric fields, consumer branch, selected context or map, page-root
   slot behavior, downloaded-glyph selector/helper dispatch, `0x783140`
   remainder, `0x12328` drain status, replay frame state, delayed payload
   state, page-object bytes, bridge roots, or rendered rows. The controlling
   sections above cite the exact fixtures and notes for those contracts.
4. Page-image expansion should target new pixel-affecting ROM state only. Add
   cases when they expose a new publication selector, allocator/rollover branch,
   raster gate outcome, rectangle selector or clipping behavior, render helper
   target, fallback split, continuation mutation, active scheduler state, or
   row output. Do not re-run already-composed text/rule/raster, downloaded-font,
   font-selection, VFC, macro, or publication streams only to produce another
   digest.
5. Final physical correlation remains separate from ROM-local documentation.
   The current model derives rows from ROM disassembly, resource bytes,
   page-record fields, and render helpers. A representative physical print, if
   one is ever used, can only correlate that model with a device; it is not an
   oracle for the documentation and is not a substitute for static ROM evidence.
   Fixture output is likewise only a ROM-local branch or transcription check;
   the deliverable is the documented path that constructs rows.
