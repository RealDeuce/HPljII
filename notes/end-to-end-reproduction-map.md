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
  -> 0x11774 dispatch classes over tables 0x112a4 / 0x116f6
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

## Reader Entry Points

Use these entry points according to the artifact in hand:

- For a manual PCL command name or syntax row, start with the ROM Semantic Index in
  [pcl4-language.md](pcl4-language.md#owner-summary). That index maps PCL Level IV
  command families to first parser handlers, concrete stream examples, page-object
  bytes, render routes, and owner notes. It is a routing map, not the full proof.
- For a concrete byte stream, use `Stream Trace Procedure` below, then the
  `Supported Stream Entry Points` cluster map. Those sections keep the trace
  byte-oriented: source bytes, parser records, command handler, state fields,
  page objects, publication, bridge, and render helper.
- For the common page/image and pixel-output hop after a command-family note
  has created page content, use `Shared Page-Object Contract` and
  `Command-Family To Render Route Table`, then `Render Helper Boundary Index`
  in this file. Those sections collect the handler-to-object route,
  page-root fields, publication and bridge fields, render-record roots,
  helper dispatch order, buffer destinations, and exact ROM-local render
  boundaries that are shared by printable text, spans, raster, rules, and
  downloaded glyphs.
- For a known supported family, use `Reproducible Byte-Stream Families`. That
  section records the current end-to-end contracts for printable/direct
  controls, layout, font selection, no-output rows, host/status side channels,
  transparent/display readers, raster/rectangle imaging, VFC, macro replay,
  publication, downloaded fonts, and mixed page-image composition.
- For completion/risk work, use `Current Residual Edge Index`,
  `Pixel-Perfect Coverage And Residual Risks`, and
  `Next Documentation Targets`.
  New ROM tracing should begin only when a stream changes a named parser
  field, command state field, page-object byte, publication/bridge field,
  render helper input, or exact unresolved boundary named there.
  [unresolved-boundaries.md](unresolved-boundaries.md) is the compact index of
  those exact remaining stop points, grouped by boundary classification; its
  [Renderer Stop Contract](unresolved-boundaries.md#renderer-stop-contract)
  gives the reproducer rule for downloaded-glyph invalid helper/source cases
  after the upstream parser, page-object, publication, and render-helper entry
  state is already modeled.

The same semantic claim should appear at the highest useful level only once:
the language map names the route, this file composes the route into the
host-byte-to-pixel model, and the owner note carries the low-level ledger with
handler addresses, fields, consumers, evidence, and unresolved boundaries.

## Objective Coverage Index

This index maps the active documentation objective to the checked-in owner
sections that currently carry the proof. It is a navigation contract, not a
completion claim: if a stream changes a field, object byte, render input, or
boundary outside these owners, the relevant owner note must be extended.

- Host input handling and parser state transitions:
  [host-byte-fetch.md](host-byte-fetch.md#owner-summary) owns `0xa904..0xab8a`, source
  priority, data-chain replay, direct hardware fetches, and the `D7` caller contract.
  [pcl-parser-core.md](pcl-parser-core.md#owner-summary) owns `0xda9a`, `0xdaf0`,
  `0xdb74`, parser mode `0x782999`, command-record cursor `0x78299e`, and parser loop
  `0x11774`.
- Normal bytes, C0 controls, ESC entry, parameterized commands, binary
  payloads, macro/replay input, and ignored/error cases:
  [direct-control-codes.md](direct-control-codes.md#owner-summary) owns
  printable `0xd04a`, C0 controls, cursor movement, spans, and line
  termination; [pcl-parser-core.md](pcl-parser-core.md#parser-core-outcome-matrix)
  owns ESC parsing, no-output rows, and parser artifacts;
  [pcl-parser-firmware.md](pcl-parser-firmware.md#parser-firmware-outcome-matrix)
  owns delayed restore `0x121cc -> 0x12218` and generic counted drains;
  [macro-data-chain.md](macro-data-chain.md#owner-summary) owns
  `0xe418`, `0xe4f4`, and `0xe22c` replay frames.
- Command dispatch tables and mapping from parsed forms to handlers:
  [pcl-command-map.md](pcl-command-map.md#dispatch-class-checkpoint) owns
  dispatch classes, table rows, terminal handlers, explicit zero rows,
  delayed-payload setup, alternate/data append, and callback/no-match exits
  from parser table roots `0x112a4` and `0x116f6`.
- Detailed command-family behavior:
  [pcl4-language.md](pcl4-language.md#level-iv-command-family-outcome-matrix)
  is the manual-family route map. Owner notes carry the low-level fields and
  effects: publication/page control, direct controls, display/transparent
  readers, font and symbol selection, raster graphics, rectangle/rules,
  downloaded fonts, macros, VFC, host/status side channels, and resource ROM
  paths.
- Page/image assembly model:
  [page-record-storage.md](page-record-storage.md#owner-summary) owns current page root
  `0x78297a`, compact/raster bucket root `+0x1c`, rule-list root `+0x24`, fixed-list
  root `+0x28`, context slots `+0x2c..+0x68`, stream allocation through `0x1381c` /
  `0x1387c`, and publication `0xff1e`. Shared object shape and render bridge context are
  summarized in `Shared Page-Object Contract` below, with the
  producer/root/object/bridge route grouped by class in `Page Object Shape Route Index`
  in
  [firmware-dataflow-model.md](firmware-dataflow-model.md#page-object-shape-route-index).
- Output/render engine:
  [active-render-scheduler.md](active-render-scheduler.md#owner-summary) owns active
  render scheduling and wait-object handoff.
  [page-raster-imaging.md](page-raster-imaging.md#pixel-generation-owner-summary) owns
  bridge `0x1ed84 -> 0x1edc6`, render dispatch `0x1ef6a`, compact text/downloaded-glyph
  helpers, segment-list and fixed-list helpers, rule/rectangle helpers, encoded raster
  helper `0x1f88e`, destination buffers, and ROM-defined pixel composition.
- Field and state classification:
  [semantic-state-model.md](semantic-state-model.md#owner-summary) is the
  canonical field-classification ledger. Owner notes repeat local groups as
  canonical state, derived/cache state, parser scratch, firmware bookkeeping,
  hardware/external state, and unknown state only where those fields affect a
  specific route.
- Evidence and unresolved boundaries: [source-index.md](source-index.md#owner-summary)
  owns manual/PDF evidence boundaries. Checked-in owner notes cite focused listings
  under `generated/disasm/`, table extracts under `generated/analysis/`, ROM fields,
  static cross-references, and named fixtures as supporting evidence.
  [unresolved-boundaries.md](unresolved-boundaries.md#unresolved-boundary-outcome-matrix)
  is the compact index of exact stop points by reason: ROM-local invalid target/source,
  missing resource data, hardware/MMIO boundary, optional external data, or
  manual/physical correlation.

## Shared Page-Object Contract

The current checked-in model treats page content as queued ROM objects, not as a
parser-time bitmap. This section is the common object contract used by the
command-family notes; detailed ledgers remain in [Page Object Storage Outcome
Matrix](page-record-storage.md#page-object-storage-outcome-matrix),
[page-raster-imaging.md](page-raster-imaging.md), and
[semantic-state-model.md](semantic-state-model.md).

- Canonical page root:
  current root `0x78297a`, stream allocator fields
  `0x782a70/0x782a72/0x782a76`, bucket array root `+0x1c`, rule-list root
  `+0x24`, fixed-list root `+0x28`, and selected context/resource longword
  slots `+0x2c..+0x68`. Writers are `0x10084`, `0x10110`, `0xc428`,
  `0xc4fc`, `0x1381c`, `0x1387c`, `0x133aa`, and `0x136d2`; publication and
  render consumers are `0xff1e`, `0x1ed84`, `0x1edc6`, and `0x1ef6a`.
- Compact text and downloaded glyph objects: printable bytes route through `0xd04a ->
  0x1393a -> 0x12f2e -> 0x1387c` and queue bucket objects under root `+0x1c`. Examples
  now documented in [pcl-command-map.md](pcl-command-map.md) include primary final-`X`
  `ESC (7X!!` object prefix `00 00 00 00 00 00 00 02 00 89 00 00 87 02`, secondary `ESC
  )8X SO !!` prefix `00 00 00 00 00 01 00 02 00 c9 00 00 cb 01`, and downloaded
  printable `!` object `00 00 00 00 00 00 00 01 21 5a 00`. The source-object boundary is
  [Printable Source Capture
  Checkpoint](font-context-metrics.md#printable-source-capture-checkpoint): it owns how
  `0x1393a` maps the original host byte through the active map, writes source fields
  `+0x00/+0x04/+0x0a/+0x0b/+0x10/+0x12/+0x14/+0x16`, and hands the source to `0xd3b2` /
  `0xd824` and `0x12f2e`.
- Segment/span objects:
  pending text decoration or span state flushes through `0x12714` into a
  class-`0x40` object. The documented `ESC &d3D ! ESC &d@` path queues span
  object `00 00 00 00 40 00 00 01 3a 00 03 00 00 12`, then renders through
  `0x1efc2 -> 0x1f812 -> 0x1f862`; see
  [pcl-command-map.md](pcl-command-map.md) and
  [page-raster-imaging.md](page-raster-imaging.md).
- Raster and rectangle/rule objects:
  raster rows route through `0x105d0 -> 0x138de -> 0x13070` / `0x13250` into
  bucket objects under root `+0x1c`; rectangles route through
  `0x10898 -> 0x10b80 -> 0x13386` / `0x133aa` into the rule list at `+0x24`.
  Documented examples include primary mode-0 raster object
  `00 00 00 00 80 00 00 04 00 01 f0 0f aa 55` and selector-7 rule objects
  `00 00 00 00 01 07 4a 00 00 0c 00 05 00 00` /
  `00 00 00 00 01 17 4a 00 00 0c 00 05 00 05`.
- Publication and render consumers:
  `0xff1e` snapshots page-root buckets, lists, context slots, and header
  fields into a page/control pool record. `0x1ed84` selects an active source
  record, `0x1edc6` copies source `+0x1c/+0x24/+0x28/+0x2c..+0x68` into render
  record `+0x18/+0x1c/+0x20/+0x24..+0x60`, and `0x1ef6a` dispatches the active
  band through bucket, rule, fixed-list, compact, segment-list, and raster
  helpers. The checked-in outcome contract for that join is
  [Render Entry Outcome Matrix](page-raster-imaging.md#render-entry-outcome-matrix).

Context-slot handoff: `0x10110` and `0xc428 -> 0xc4fc` copy selected context/resource
longwords from current-font RAM records into page-root slots `+0x2c..+0x68`. Printable
queue paths `0xd3b2` and `0xd824` store the selected slot number in the compact
object/source state, while `0x1edc6` copies the slot longwords into render slots
`+0x24..+0x60`. Compact dispatch then loads one copied slot into `0x783a2c` before
resolver `0x1f354` locates glyph bitmap bytes. This is why a byte-stream trace must
preserve both compact object payload bytes and the copied context-slot values. The owner
checkpoint is [Context Slot Preservation
Checkpoint](page-record-storage.md#context-slot-preservation-checkpoint).

Compact-render handoff: after bridge, `0x1efc2 -> 0x1effe` reads compact object selector
and context-slot bytes from render root `+0x18`, loads `0x783a2c`, and dispatches
through table `0x1f024` to short, wide, segmented, or segmented-wide helpers. The
checked-in owner checkpoint is [Compact Render Dispatch Outcome
Matrix](page-raster-imaging.md#compact-render-dispatch-outcome-matrix); it ties selector
bits `0x00/0x10/0x20/0x30` to helpers `0x1f034`, `0x1f0d2`, `0x1f1f0`, and `0x1f264`,
and bounds the invalid computed-jump cases.

The compact producer-to-render summary for all page-object classes is
`Page Object Shape Route Index` in
[firmware-dataflow-model.md](firmware-dataflow-model.md#page-object-shape-route-index).
It groups compact text/downloaded glyphs, portrait segment-list spans,
encoded raster objects, rectangle rule-list objects, and landscape fixed-list
spans by producer address, root field, canonical object bytes, bridge field,
first render consumer, field classification, and exact residual boundary.

State classification for this shared layer is: canonical state is the current
page root, queued object records, context slots, and published page/control
records; derived/cache state is bucket index `0x782a7c`, compact coordinate
keys, selected-font maps, render stride `0x783a1c`, band fields
`0x783a20/0x783a22/0x783a28`, and copied render roots; parser scratch is the
six-byte command records and delayed payload state consumed before object
creation; firmware bookkeeping is allocator accounting, publication flag
`0x782996`, scheduler cursors, and render-work alternator state; hardware or
external state begins where the ROM waits on formatter/DC events instead of
writing one of these fields.

The remaining unresolved page/render edges must change a named object field,
root/list field, publication field, bridge field, scheduler-produced band word,
or ROM row-helper input. The current explicit residuals are exact physical
formatter/DC timing and ROM-local downloaded-glyph helper variants such as the
high-row `0x1fe76` fallback and the wrapped source-byte helper targets through
`0x1f034` / `0x1f08e`. The heap/free-list contract is not an open page/render
edge: `0x1381c` owns page-root stream-link side effects, while the shared
allocator bitmap/free behavior for `0x170c`, `0x1710`, and `0x18b4` is composed
in `Macro Definition And Data-Chain Replay` in
[semantic-state-model.md](semantic-state-model.md).

### Command-Family To Render Route Table

Use this table after `pcl-command-map.md` has identified the terminal handler
or delayed payload owner. It is the checked-in semantic join from parsed
command families to page/image objects and then to the render helper that can
write pixels.

- Printable text:
  normal unmatched printable bytes, transparent/display routed bytes, and
  replayed printable bytes reach `0xd04a`. Source setup uses `0x1393a`,
  `0xd140` / `0xd550`, and `0xd3b2` / `0xd824`. The canonical page object is
  a compact bucket under root `+0x1c` from `0x12f2e -> 0x1387c`; context
  slots under root `+0x2c..+0x68` select built-in or downloaded resources.
  Bridge `0x1edc6` copies root `+0x1c` to render `+0x18`, and
  `0x1efc2 -> 0x1effe` selects `0x1f034`, `0x1f0d2`, `0x1f1f0`, or
  `0x1f264`. Pixels come from compact object entries and copied context
  slots.
- Direct cursor/layout controls:
  handlers such as `0xf02c`, `0xf08c`, `0xf0f0`, `0xedf8`, `0xca8c`,
  `0xeb58`, `0xec0c`, `0xf39e`, `0xf560`, `0xf48c`, and `0xf692` write
  canonical placement and layout fields: `0x782c8a`, `0x782c8e`, margins,
  HMI/VMI, span watermarks, wrap/perforation state, and possible publication
  through `0xf124 -> 0xff1e`. These handlers have no direct pixel helper;
  later text, span, raster, rectangle, or publication consumers read the
  mutated fields. Span flush `0x12714` can create class-`0x40` segment-list
  objects rendered by `0x1f812`.
- Transparent print data:
  `ESC &p#X` arms `0x11f5a -> 0x121cc`; restore `0x12218` calls payload
  reader `0x12452`. Counted payload bytes route to `0xd04a` or fixed-space
  `0xd0f0`; any compact objects are ordinary text objects under root `+0x1c`.
  The render route is the same compact route as printable text. The remaining
  pixel-affecting boundary is the secondary segment-57 resource read at
  `0x0c0000..0x0c0321`, documented in `transparent-print-data.md`.
- Raster graphics:
  `ESC *t#R` uses `0x10808`; `ESC *r#A/#B` use `0x1075a` / `0x107fa`;
  delayed `ESC *b#W` restores to `0x105d0`. The canonical raster block is
  `0x783170`. Accepted transfers queue encoded-raster bucket objects through
  `0x13070 -> 0x13250 -> 0x138de` under root `+0x1c`, with class byte
  `+4 = 0x80` and payload at `+0x0a`. Bridge `0x1edc6` copies root `+0x1c`
  to render `+0x18`; `0x1efc2 -> 0x1f88e` selects `0x1f8da`, `0x1f8e6`,
  `0x1f920`, or `0x1f9c6` from object byte `+5 & 3`. Pixels come from queued
  payload bytes and expansion tables `0x30914` / `0x30b14`.
- Rectangle/rule graphics:
  `ESC *c` size/fill handlers write `0x78316a`, `0x783166`, and `0x78316e`;
  fill `#P` runs `0x10898 -> 0x10b80 -> 0x13386 -> 0x133aa`. Clipped source
  `0x782a88` becomes a 14-byte rule object under page-root `+0x24`; bridge
  `0x1edc6` sets selector bit `+5.4` and continuation word `+0x0c`. It then
  copies root `+0x24` to render `+0x1c`. `0x1f446` dispatches solid selector
  `7` to `0x1f596` and other selectors through pattern helper `0x1f4e0`.
  Pixels come from width, height, selector, and pattern tables.
- Text spans and underline:
  direct-control span state is kept in `0x783184..0x78318a`; flush enters
  `0x12714`. Portrait spans queue class-`0x40` segment-list objects under
  root `+0x1c` through `0x13520` / `0x135f0`; landscape spans queue fixed-list
  objects under root `+0x28` through `0x136d2`. The portrait route renders
  through `0x1efc2 -> 0x1f812 -> 0x1f862`; the landscape route renders through
  `0x1f756 -> 0x1f7b0`. Pixels come from queued span widths, coordinates, and
  continuation fields.
- Downloaded fonts and glyphs:
  font-control and payload commands route through `0x15a56`, `0x16df6`,
  delayed selector `0x11f96`, descriptor `0x15d0a`, resource install
  `0x16c14`, and character install `0x16498`. Canonical state is current
  downloaded-font id and character `0x782f2e/0x782f30`, records
  `0x782640..0x782776`, installed glyph tables, bitmap payload bytes, and
  later compact objects queued by printable `0xd04a -> 0x12f2e`. Selected
  glyph output uses the compact text route; documented valid helpers are
  `0x1f034`, `0x1f0d2`, `0x1f1f0`, and `0x1f264`. Invalid or high-row helper
  boundaries stop at exact targets such as `0x1fe76..0x1fe88` or wrapped
  `0x1f034 -> 0x1f08e`.
- Publication and copies:
  FF/reset/layout publication routes enter `0xf124` / `0xff1e`; copies use
  `0xeef0` before later publication. Current root `0x78297a` is copied into
  page/control pool record `0x780ea6`; copy count and header fields are
  preserved; current root is cleared. The active scheduler selects source
  `0x780eae`; `0x1ed84 -> 0x1edc6` bridges roots into render
  `+0x18/+0x1c/+0x20` and context slots before `0x1eba4 -> 0x1ef6a` renders
  band words.

Evidence: the handler-to-owner mapping is in
[pcl-command-map.md](pcl-command-map.md#semantic-owners). Detailed state,
writer, reader, and unresolved-boundary ledgers are in
[direct-control-codes.md](direct-control-codes.md#owner-summary),
[transparent-print-data.md](transparent-print-data.md#owner-summary),
[raster-graphics.md](raster-graphics.md#owner-summary),
[rectangle-graphics.md](rectangle-graphics.md#owner-summary),
[downloaded-fonts.md](downloaded-fonts.md#owner-summary),
[page-record-storage.md](page-record-storage.md#page-assembly-decision-checkpoint),
and [page-raster-imaging.md](page-raster-imaging.md#pixel-generation-owner-summary).

## Render Helper Boundary Index

The render helper layer is documented as ROM dataflow from bridged page objects
to bitmap writes. Its common entry is
`0x1ef6a -> 0x1ef86 -> 0x1efc2 -> 0x1f446 -> 0x1f756`, with detailed evidence
in [Render Entry Owner Summary](page-raster-imaging.md#render-entry-owner-summary),
[Pixel Composition Checkpoint](page-raster-imaging.md#pixel-composition-checkpoint),
[page-raster-imaging.md](page-raster-imaging.md#renderbanding-bridge),
`Bitmap Render Dispatch Contract` in
[semantic-state-model.md](semantic-state-model.md), and listings
`generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`,
`generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`, and
`generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst`.

Field grouping for this render layer is explicit. Canonical inputs are the
render-record roots copied by `0x1edc6`: bucket root `+0x18`, rule root
`+0x1c`, fixed root `+0x20`, context slots `+0x24..+0x60`, and the object
fields under those roots. Derived/cache state is render stride `0x783a1c`,
band caches `0x783a20/0x783a22/0x783a28`, compact context cache `0x783a2c`,
destination phase `$a001`, fallback base `0x7810b4 + byte_pair_offset`, row
tables `0x1f08e` / `0x1f1ac`, chunk helper table `0x2f2ac`, and raster
expansion tables `0x30914` / `0x30b14`. Parser scratch is absent at this
layer because `0x12f2e`, `0x13070`, `0x133aa`, `0x136d2`, or `0x12714` have
already converted command records and payload bytes into page objects.
Firmware bookkeeping is continuation mutation in rule/fixed/span objects and
wide-copy phase `0x783a46`. Hardware/external state begins after the ROM has
written the band buffer; physical engine consumption is not a ROM-local row
helper input.

Writers are the page-object producers and bridge: `0x12f2e` / `0x1387c` for
compact text and downloaded glyph objects, `0x13070` / `0x13250` for raster
objects, `0x13386` / `0x133aa` for rule objects, `0x136d2` for fixed-list
objects, `0x12714` / `0x13520` / `0x135f0` for span objects, and `0x1edc6` for
render-record roots. Readers are `0x1efc2` for bucket classes, `0x1effe` for
compact subdispatch, `0x1f034` / `0x1f0d2` / `0x1f1f0` / `0x1f264` for compact
text and downloaded glyphs, `0x1f812` for segment spans, `0x1f446` with
`0x1f4e0` / `0x1f596` for rules, `0x1f756` for fixed-list spans, and
`0x1f88e` with `0x1f8da` / `0x1f8e6` / `0x1f920` / `0x1f9c6` for encoded
raster modes.

The output effect is direct current-band or fallback-buffer writes derived
from object fields and ROM tables. Compact helpers resolve glyphs through
`0x1f354`, split current/fallback rows through `0x1f414`, then copy rows
through `0x1f08e` main-width helpers, `0x1f1ac` remainder helpers, or
`0x2f27c` full 16-byte chunks. Raster helper `0x1f88e` writes literal or
expanded payload rows according to mode bits and tables `0x30914` / `0x30b14`.
Rule and span helpers mutate remaining-row fields when a band split leaves
continuation work. Concrete checked-in examples include the final-`X` compact
object prefixes, downloaded printable `!` object, `ESC &d3D ! ESC &d@` span
object, mode-0 raster object, selector-7 rule objects, and mixed text/rule/
raster page streams documented in [pcl-command-map.md](pcl-command-map.md)
and [page-raster-imaging.md](page-raster-imaging.md).

The unresolved render-helper boundaries are exact:

- `0x1fe76..0x1fe88` short compact span-2 row helper loads table base
  `0x1fe8a`, shifts `D3` by two, reads a longword target, and jumps. Valid
  entries end at row index `128`; higher fallback counts read executable code
  bytes beginning at `0x2008e` as pointer data. The documented row-`0x0102`
  downloaded-glyph fallback count `200` reads target `0x329ad3c0`.
- `0x1f034 -> 0x1f08e` wrapped-width mode-0 cases use the full span word as a
  table index instead of a legal byte width. For span `0x0102`, entry address
  `0x1f08e + 0x0408 = 0x1f496` contains bytes `00 00 66 cc`, producing jump
  target `0x0066cc`; listing
  `generated/disasm/ic30_ic13_invalid_compact_mode0_target_0066c0.lst` shows
  that target is not a row-copy helper.
- `0x1f264` segmented-wide high-row span-31 siblings are bounded at fallback
  source offset `+0xb50` for the documented row products. Adjacent below-cap
  siblings continue as selected-segment render cases, while oversized
  row/span products stop earlier at the `0x16c14` / restored `ESC )s#W`
  payload-count cap `0x7fff` and never create a page object.

Those boundaries are ROM-local invalid-target or source-read boundaries, not
unknown parser dispatch, page-object publication, render scheduling, or
physical output comparison gaps. Reproduction handling is indexed in
[unresolved-boundaries.md](unresolved-boundaries.md#pixel-affecting-boundaries):
preserve the ROM-derived upstream state, then stop at the exact invalid helper
target or source-read boundary instead of inventing rows beyond it.

## Objective Coverage Matrix

Use this section to map the current checked-in documentation back to the
ROM-disassembly objective. A requirement is only counted here when the linked
checked-in notes describe behavior, state fields, evidence, and any remaining
boundary; generated reports and fixture names are supporting evidence, not the
controlling artifact.

- Host input handling and parser state transitions:
  covered by [host-byte-fetch.md](host-byte-fetch.md),
  [pcl-parser-core.md](pcl-parser-core.md), `Admitted Byte Outcome Bridge`,
  the `Minimal Host Input Walkthrough`, and `Worked Path: Host Byte Source
  Priority` / `Worked Path: Command Record And Payload Dispatch` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md). The ROM-local
  contract is `0xa904` normalized byte output into `0xda9a` / `0xdaf0` /
  `0xdb74`, parser loop `0x11774`, parser mode `0x782999`, six-byte records at
  `0x78299e..`, and the branch outcomes that either reach a family owner,
  append through `0xe002`, return through service/no-byte state, or stop as an
  explicit no-output parser row. Residuals are physical bus/MMIO naming unless
  a new source changes the normalized byte sequence.
- Normal bytes, control codes, ESC entry, parameterized commands, binary payloads,
  macro/replay, and ignored/error cases: the branch-level parser outcomes are documented
  in [pcl-parser-core.md](pcl-parser-core.md#parser-core-outcome-matrix), summarized in
  `Admitted Byte Outcome Bridge`, and indexed by
  [pcl-command-map.md](pcl-command-map.md#inbound-byte-outcome-classes). These outcomes
  include printable dispatch `0xd04a`, direct C0 handlers, explicit zero-handler rows,
  parser-external service/return `0x117d2..0x11818`, no-match fallback/append/callback
  paths `0x118b2..0x11900` / `0x11b32..0x11b8a`, delayed binary payload restore, and
  macro/data replay through `0xa904`. The ROM Semantic Index in
  [pcl4-language.md](pcl4-language.md#owner-summary) adds the command-language entry
  point: for each major PCL Level IV family it names first parser handlers,
  representative byte streams, page-object bytes or state fields, render routes, and
  owner notes. Checked-in owners are [direct-control-codes.md](direct-control-codes.md),
  [transparent-print-data.md](transparent-print-data.md#transparent-payload-decision-checkpoint),
  [display-functions.md](display-functions.md),
  [macro-data-chain.md](macro-data-chain.md), [raster-graphics.md](raster-graphics.md),
  [downloaded-fonts.md](downloaded-fonts.md), and
  [vertical-forms-control.md](vertical-forms-control.md). The minimal walkthroughs for
  parser dispatch, ignored/no-output rows, transparent data, display functions,
  symbol-set/map updates, macro replay, overlay replay, VFC, raster, and downloaded
  glyphs give byte-stream examples. The `Supported Stream Entry Points` address-level
  cluster map is the current checked-in route index for starting from a concrete byte
  stream: it names the parser route and the first command-family/page/render owners for
  printable text, direct controls, parser artifacts, transparent/display readers, font
  selection, scheduler handoff, downloaded fonts, raster/rectangle graphics,
  publication/render, macro replay, and VFC.
- Command dispatch tables and parsed forms to handlers:
  covered by [pcl-command-map.md](pcl-command-map.md), generated table extracts
  cited there, the ROM Semantic Index in
  [pcl4-language.md](pcl4-language.md), and `Worked Path: Command Record And
  Payload Dispatch`.
  Normal table `0x112a4`, alternate/data table `0x116f6`, parser loop
  `0x11774`, matched-handler range `0x11912..0x119a4`, zero-handler range
  `0x119a6..0x119f4`, alternate append range `0x11930..0x11ab8`, delayed
  arming helpers `0x11f5a` / `0x11f6e` / `0x11f82` / `0x11f96`, restore path
  `0x121cc -> 0x12218`, no-match callback pointer `0x78299a`, and owner notes
  form the current dispatch contract.
- Detailed command-family behavior:
  documented by the owner notes listed in the `Supported Stream Entry Points`
  section below. Each owner records parsed inputs, RAM writers, consumers,
  side effects, output/page effects, field classification, confidence, and
  exact residual boundaries. High-volume families include font selection in
  the [Symbol/Font Designation Outcome
  Matrix](symbol-set-selection.md#symbolfont-designation-outcome-matrix) and
  the [Font Request Outcome
  Matrix](font-context-metrics.md#font-request-outcome-matrix), downloaded
  fonts in [downloaded-fonts.md](downloaded-fonts.md), rectangles in
  [rectangle-graphics.md](rectangle-graphics.md), raster in
  [raster-graphics.md](raster-graphics.md), publication in
  [publication-commands.md](publication-commands.md), and reset provenance in
  [reset-default-environment.md](reset-default-environment.md). The address
  cluster map does not replace those ledgers; it is the top-level dispatch
  bridge from parsed command forms into those command-family ledgers and from
  page producers into publication and renderer owners.
- Page/image assembly model: covered by [Page Assembly Decision
  Checkpoint](page-record-storage.md#page-assembly-decision-checkpoint), [Context Slot
  Preservation Checkpoint](page-record-storage.md#context-slot-preservation-checkpoint),
  [page-raster-imaging.md](page-raster-imaging.md), `Worked Path: Shared Page-Record
  Storage And Allocator`, `Page Object Shape Route Index`, `Page Image Assembly`, and
  `Page Versus Band Model` in [firmware-dataflow-model.md](firmware-dataflow-model.md),
  and the `Minimal Page Assembly Walkthrough`. The canonical model is current root
  `0x78297a`, stream
  allocator state `0x782a70/0x782a72/0x782a76`, compact and raster buckets under root
  `+0x1c`, rules under `+0x24`, fixed objects under `+0x28`, selected context/resource
  longword slots `+0x2c..+0x68`, publication `0xff1e`, bridge `0x1ed84` / `0x1edc6`, and
  scheduler-selected band rendering rather than a parser-time full-page bitmap.
  `Page Object Shape Route Index` is the compact proof map for producer, root field,
  object bytes, bridge field, first renderer, field classification, and residual
  boundary by object class.
- Output/render engine:
  covered by [active-render-scheduler.md](active-render-scheduler.md),
  [page-raster-imaging.md](page-raster-imaging.md), `Published Record To Active
  Render Scheduler` and `Bitmap Render Dispatch Contract` in
  [semantic-state-model.md](semantic-state-model.md), `Band Scheduling Route Index`, and
  `Worked Path: Render Dispatch And Pixel Composition` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md). The current ROM-local render
  path is
  published pool state `0x780ea6/0x780eaa/0x780eae`, active render pointer
  `0x783a18`, bridge roots `+0x18/+0x1c/+0x20`, render entry `0x1ef6a`, bucket
  dispatch `0x1efc2`, compact helpers `0x1f034..0x1f264`, segment-list helper
  `0x1f812`, rule helpers `0x1f4e0` / `0x1f596`, fixed-list helper `0x1f756`,
  and raster helper `0x1f88e`. `Band Scheduling Route Index` is the compact proof map
  for `0xff1e` publication, source selection `0x780eaa -> 0x780eae`, work-record
  alternation, active pointer `0x783a18`, band-loop no-pixel exits, and the
  capacity-approved handoff into `0x1ef6a`.
- Field/state classification:
  owned by [semantic-state-model.md](semantic-state-model.md#owner-summary),
  defined by the `State Classification Guide`, summarized in `Canonical State
  Groups`, and repeated in the minimal walkthroughs and owner notes. The
  categories are canonical state, derived/cache state, parser scratch,
  firmware bookkeeping, hardware/external state, and unknown or unresolved
  state. A field classification is counted only when a checked-in note names
  the writer, reader/consumer, output effect, and boundary that make the field
  matter to parser, page-object, publication, scheduler, render, status, or
  no-output behavior.
- Concrete evidence for semantic claims:
  required by the `Pipeline Contract`, attached to each minimal walkthrough in
  `Checked-in explanations` and `Focused listings` subsections, and indexed by
  the owner notes. [source-index.md](source-index.md#owner-summary) owns the
  manual/PDF evidence boundary: manuals can name syntax, units, hardware
  labels, or user-facing behavior, but ROM behavior still requires dumped ROM
  bytes, handler addresses, ROM fields, disassembly files under
  `generated/disasm/`, generated table extracts, resource bytes, static
  cross-references, or named model-consistency fixtures cited from a checked-in
  owner note. Fixture output is never the primary semantic claim.
- Explicit unresolved boundaries:
  maintained first in the `Unresolved Boundary Outcome Matrix` in
  [unresolved-boundaries.md](unresolved-boundaries.md), with route-specific
  context in `Current Residual Edge Index`,
  `Pixel-Perfect Coverage And Residual Risks`, `Next Documentation Targets`, and
  `Unresolved Boundaries` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md). Current bounded
  residual classes are secondary segment-57 resource decode
  `0x0c0000..0x0c0321` with suffix and continuation evidence in
  [Secondary Segment-57 Resource
  Source](unresolved-boundaries.md#secondary-segment-57-resource-source),
  ROM-local downloaded-glyph helper invalid target/source boundaries, host
  physical interface naming/timing, optional resource-window contents,
  retained-storage/service persistence, formatter/DC physical timing, and new
  ROM-local command variants only when they change
  named state or row-construction inputs.

## Stream Trace Procedure

Use this procedure when starting from a concrete supported host byte stream.
It keeps the controlling artifact byte/dataflow oriented while preserving the
command-family and page-image structure:

1. Normalize the byte source:
   start at [Host Byte Source Outcome
   Matrix](host-byte-fetch.md#host-byte-source-outcome-matrix) and classify
   which `0xa904` source produces each parser byte: live/ring/direct host
   input, pushback stack, data-chain replay, or macro replay. If the stream
   includes delayed payload bytes, keep the payload reader's direct `0xa904`
   calls separate from parser-wrapper bytes. Then use the caller-return
   contract in [host-byte-fetch.md](host-byte-fetch.md#d7-caller-return-contract)
   to identify the consumer class for the returned byte before applying
   parser, payload, display, raster, downloaded-font, or replay semantics.
2. Classify each admitted byte:
   first use `Admitted Byte Outcome Bridge` in this file, then
   [Parser Core Outcome
   Matrix](pcl-parser-core.md#parser-core-outcome-matrix) and
   [Inbound Byte Outcome
   Classes](pcl-command-map.md#inbound-byte-outcome-classes)
   to place the byte on a concrete `0x11774` branch: printable handler,
   alternate/data append, matched command handler, zero-handler reset,
   no-match fallback, callback continuation, delayed-payload restore, or
   parser-external return. The dispatch class determines whether the next
   semantic owner is a prefix/setup row, terminal handler, delayed-payload
   owner, explicit no-output row, alternate/data append path, or service
   outcome.
3. Follow parser records and dispatch:
   for matched command bytes, continue in
   [pcl-parser-core.md](pcl-parser-core.md#parser-core-outcome-matrix) to
   track parser mode `0x782999`, parser record cursor `0x78299e`, the six-byte
   record fields,
   delayed-payload state `0x782a1a/0x782a1c/0x782a20..`, normal table
   `0x112a4`, and alternate/data table `0x116f6`. Then jump from the class
   checkpoint through
   [Parser-To-Owner Outcome Handoff](pcl-command-map.md#parser-to-owner-outcome-handoff)
   to the owner note named by
   [pcl-command-map.md](pcl-command-map.md#supported-stream-dispatch-matrix).
   The handoff section classifies the shared parser fields and names the
   checked-in outcome checkpoint that owns command effects, page objects, or
   explicit no-output/status behavior.
4. Record command state effects:
   in the owner note, capture the canonical fields written by the handler,
   parser scratch consumed, derived/cache fields, firmware bookkeeping,
   readers/consumers, and no-output side effects. State-only commands remain
   in this step until a later byte consumes their changed fields.
5. Map page/image objects: when a command creates page content, use `Command-Family To
   Render Route Table` in this file plus [Page Assembly Decision
   Checkpoint](page-record-storage.md#page-assembly-decision-checkpoint) and its
   renderer-facing object class map. Identify the page-root field written by the
   producer: compact/segment/raster buckets under root `+0x1c`, rule list under root
   `+0x24`, fixed list under root `+0x28`, and selected context/resource longword
   slots under root `+0x2c..+0x68`. For compact text and downloaded glyphs, also record
   the compact object slot selector and the selected page-root slot `0x78297e`, because
   those fields determine which copied render context `0x1f354` consumes.
6. Cross the publication and scheduler boundary:
   use [publication-commands.md](publication-commands.md),
   [page-record-storage.md](page-record-storage.md), and
   the [Scheduler Outcome
   Matrix](active-render-scheduler.md#scheduler-outcome-matrix) to follow
   `0xff1e`, pool cursors `0x780ea6/0x780eaa/0x780eae`, render-work pointer
   `0x783a18`, active copy `0x1ed84`, and bridge `0x1edc6`. If the stream is
   not published yet, the visible output remains pending page-record state.
7. Derive pixels from ROM render helpers: use [Pixel Composition
   Checkpoint](page-raster-imaging.md#pixel-composition-checkpoint),
   [page-raster-imaging.md](page-raster-imaging.md), and the Bitmap Render Dispatch
   Contract in [semantic-state-model.md](semantic-state-model.md) to follow `0x1ef6a`
   into compact text/downloaded glyph helpers, segment-list helper `0x1f812`, rule
   helpers `0x1f4e0` / `0x1f596`, fixed-list helper `0x1f756`, or encoded raster helper
   `0x1f88e`. Row vectors are derived from those ROM helpers, object fields, and
   ROM/resource bitmap bytes, not from an external print comparison.
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

## Admitted Byte Outcome Bridge

This bridge is the required handoff between raw host bytes and command-family
owners. It exists so a byte-stream trace does not jump straight from parsed
syntax to page output without naming the parser outcome that made the later
state legal.

The admitted byte source is `0xa904`. Parser syntax bytes then pass through
wrapper `0xda9a`, tokenizer helpers `0xdaf0` / `0xdb74`, and parser loop
`0x11774`. Counted payload readers use their family-specific direct fetch path
after delayed-payload restore, so their raw data bytes should not be folded
back into parser syntax unless the owner note names that route.

Outcome classes:

- Printable byte:
  normal mode dispatch reaches `0xd04a`, then text source and compact-object
  producers `0x1393a` / `0x12f2e`. Canonical state moves from parser byte to
  selected-font context and page-root bucket objects under root `+0x1c`.
  Owners: [direct-control-codes.md](direct-control-codes.md),
  [font-context-metrics.md](font-context-metrics.md),
  [page-record-storage.md](page-record-storage.md), and
  [page-raster-imaging.md](page-raster-imaging.md).
- Direct C0 control:
  CR, LF, FF, HT, and BS route through `0xf02c`, `0xf08c`, `0xf0f0`,
  `0xf1cc`, and `0xf2a8`. These mutate cursor/page state, publish a page
  for FF, or create no page object depending on the control. Owners:
  [direct-control-codes.md](direct-control-codes.md) and
  [publication-commands.md](publication-commands.md).
- Explicit no-output parser row:
  normal-table zero handlers such as `NUL`, `BEL`, and `VT` reset parser mode
  and produce no page object or state mutation beyond parser bookkeeping.
  Alternate/data blank C0 rows append through `0xe002` instead. Owners:
  [pcl-parser-core.md](pcl-parser-core.md#parser-core-outcome-matrix) and
  [pcl-command-map.md](pcl-command-map.md#inbound-byte-outcome-classes).
- Parser-external service or return:
  `0x117d2..0x11818` clears no-byte latch `0x780e3b`, services wait object
  `0x780202` through `0x10c8`, and returns from the parser loop when
  macro/page state byte `0x782a92 == 0x63`. This consumes a parser-loop turn
  without routing the current normalized byte to a command-family handler.
  Owner: [pcl-parser-core.md](pcl-parser-core.md#parser-core-outcome-matrix).
- Mode-zero no-match fallback:
  `0x118b2..0x11900` handles bytes that did not match a normal-table row while
  parser mode is zero. Context byte `0x782ee6 + 16 * 0x782f06 + 5 == 1`
  routes the byte to printable handler `0xd04a`; other values ignore the byte
  and fetch again. Owner:
  [pcl-parser-core.md](pcl-parser-core.md#parser-core-outcome-matrix).
- Nonzero-mode callback no-match:
  `0x11b32..0x11b7e` passes the byte to active callback pointer `0x78299a`
  when a nonzero parser mode has no matching table row. A callback return to
  mode zero clears parser cursors and pending delayed-payload byte
  `0x782a1a`; otherwise the parser remains in the command-family mode and
  fetches again. Owner:
  [pcl-parser-core.md](pcl-parser-core.md#parser-core-outcome-matrix).
- Parameterized command terminal:
  `0xdaf0` / `0xdb74` materialize one or more six-byte records at
  `0x78299e..`; `0x11774` dispatches the terminal handler from normal table
  `0x112a4` or alternate/data table `0x116f6`. The command-family owner,
  not the parser note, owns the handler's RAM writes, downstream consumers,
  and output effect. The route index is
  [pcl-command-map.md](pcl-command-map.md#supported-stream-dispatch-matrix);
  the language-facing entry point is
  [pcl4-language.md](pcl4-language.md#rom-semantic-index-for-quick-reference).
- Delayed binary payload:
  setup helpers such as `0x11f5a`, `0x11f6e`, `0x11f82`, and `0x11f96` call
  `0x121cc` to save a six-byte record in `0x782a20..0x782a25`, arm handler
  pointer `0x782a1c`, and store the payload budget. Restore `0x12218` copies
  the saved record back before the family reader consumes raw bytes. Owners:
  [transparent-print-data.md](transparent-print-data.md),
  [raster-graphics.md](raster-graphics.md),
  [downloaded-fonts.md](downloaded-fonts.md), and
  [vertical-forms-control.md](vertical-forms-control.md).
- Alternate/data or macro replay byte:
  alternate/data mode uses flag `0x782c18`, table `0x116f6`, append helper
  `0xe002`, and delayed alternate restore `0x12358`. Macro and overlay replay
  feed `0xa904` through active data-chain frame `0x782d76`, frame fields
  `+0x00/+0x04/+0x08/+0x09`, and frame builders `0xe418` / `0xe4f4`.
  Owner: [macro-data-chain.md](macro-data-chain.md).
- Host/status side channel:
  commands such as `ESC *r#K` and `ESC *s#^` parse like normal command
  terminals but write response bytes through model/status output paths instead
  of page objects. Owners:
  [Host/Status Outcome Matrix](errors-and-status.md#hoststatus-outcome-matrix) and
  [io-interfaces.md](io-interfaces.md).

State classification for this bridge:

- Canonical parser state:
  normalized byte `D7`, mode byte `0x782999`, alternate/data flag
  `0x782c18`, record cursor `0x78299e`, and delayed-payload fields
  `0x782a1a/0x782a1c/0x782a20..0x782a25`.
- Parser scratch:
  tokenizer byte/numeric scratch `0x782a26/0x782a2a..` and
  `0x782a3e/0x782a42..`, plus matched-byte scratch `0x783196..0x783199`.
- Canonical downstream state:
  only begins after the outcome class reaches a family owner: cursor/layout
  fields, selected-font contexts, page roots, downloaded glyph records,
  macro/data-chain frames, VFC table words, raster/rectangle state, status
  output state, or published page/control records.
- Derived/cache state:
  command-combining records, object bucket keys, renderer cache words, and row
  helper products are derived only after the terminal handler or page-object
  producer has written the canonical fields named by its owner note.
- Firmware bookkeeping:
  callback pointer `0x78299a`, pushback/log helper `0x9ec0`, append sink
  `0xe002`, drain helper `0x12328`, payload-control helper `0xd99a`, and
  retry/publication flags.
- Unknown:
  no ROM-local parser outcome class is currently unknown for the supported
  streams indexed in this note. Any remaining stop must be carried forward to
  the exact downstream owner boundary, for example a resource source range,
  invalid render-helper target, optional external data window, or hardware/MMIO
  register identity.

Writers are `0xa904`, `0xda9a`, `0xdaf0`, `0xdb74`, `0x11774`, delayed setup
`0x121cc`, restore `0x12218`, alternate/data append `0xe002`, and data-chain
frame builders `0xe418` / `0xe4f4`. Readers and consumers are the terminal
handler selected by the parser tables, the family payload reader after restore,
or the page/status/macro owner named above. The output effect at this bridge is
therefore one of: a page-object-producing handler, a state-only command whose
later consumers are named by its owner, a counted payload reader, a replay
source feeding `0xa904`, a host/status response, an explicit no-output parser
row, a no-match fallback/ignore, a callback continuation, or a parser-external
service/return.

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
  board-level names and timing for the direct MMIO banks, plus user-facing
  names for host-input quiesce/reset branches `0x4218..0x44d2` and
  `0x61e4..0x6362`. Data-chain frame kind byte `+0x09` is no longer an
  unresolved ROM-local producer edge for the verified image: execute `2` and
  call `3` come from `0xe418` callers `0xde96` and `0xdebc`, non-replay
  page-finalization `4` comes from `0xe4f4` caller `0xff8e`, and stale frame
  kind bytes are cleared to zero by `0xe1e4`.

Evidence:

- Checked-in explanations:
  [host-byte-fetch.md](host-byte-fetch.md),
  [macro-data-chain.md](macro-data-chain.md),
  `Worked Path: Host Byte Source Priority` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md), and
  `Host Byte Fetch And Data-Chain Input` in
  [semantic-state-model.md](semantic-state-model.md), especially its
  [D7 Caller Return Checkpoint](semantic-state-model.md#d7-caller-return-checkpoint).
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
- With initialized `LINE_PRINTER` HMI, the concrete compact object stored for
  `!!` is:

```text
00 00 00 00 00 00 00 02 20 00 01 20 02 02
```

  Object byte `+0x06 = 2` is the short-entry count. The two entries are glyph
  `0x20` at compact coordinates `0x0001` and `0x0202`; `0x1f3d4` decodes the
  second coordinate as byte base `+0x04` plus subpixel term `0x12`, placing the
  second glyph at pixel x `34` in the documented render fixture. This ties the
  top-level `!!` stream to the same object/row contract as the
  `Text Source Objects And Compact Buckets` owner note without treating the
  fixture rows as an external oracle.

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
  state. No parser command record, digit scratch, or delayed-payload state
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
  `generated/disasm/ic30_ic13_bitmap_row_copy_tables_01fa5c.lst`, and
  `generated/analysis/ic30_ic13_renderer_fixture_harness.md`.

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

This is the smallest top-level parser spine. It explains how normalized bytes become
printable fallback calls, six-byte command records, table handlers, delayed payload
calls, stored alternate/data bytes, or explicit no-output parser decisions before
command-family notes take over. The detailed dispatch-class owner handoff is
[pcl-command-map.md#dispatch-class-checkpoint](pcl-command-map.md#dispatch-class-checkpoint);
this walkthrough keeps only the byte-flow spine.

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
  cursor. In normal mode it calls the saved handler; in alternate/data mode it
  routes through `0x12358`, which calls saved wrapper `0x1228a` only when that
  exact wrapper was armed and otherwise echoes positive payload counts through
  `0xe002`. This is why a normal stream such as `ESC *b2W c3 3c` is
  two-stage: parser syntax records byte count `2`, then raster handler
  `0x105d0` consumes payload bytes after restore.
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

## Minimal Generic Counted Payload Drain Walkthrough

This is the top-level path for counted `W/w` payloads that use the generic
drain wrapper rather than a command-family payload owner such as raster,
transparent text, VFC, or downloaded fonts. It documents binary payload bytes
that are consumed for parser compatibility but do not directly produce page
objects.

Representative parser edge:

```text
stateful command family sees parsed count # and final W/w
payload bytes follow immediately in the host stream
```

Parser and delayed-payload scheduling:

- Stateful helpers `0x11ba6`, `0x11c6c`, `0x11d0c`, and `0x11dd2` recognize
  `W/w` as a counted-payload boundary and schedule wrapper `0x1228a` through
  `0x121cc`. The local `ESC &d` tokenizer at `0x12622..0x12654` uses the same
  wrapper for `W/w`.
- `0x121cc` rewinds the active command-record cursor by six bytes, then writes
  delayed-payload pending flag `0x782a1a = 1`, saved handler
  `0x782a1c = 0x1228a`, and saved six-byte command record
  `0x782a20..0x782a25` only when no delayed payload is already pending.
- When the parser returns to mode zero, terminal reset path `0x12218` restores
  the saved record to `0x78299e`, clears pending flag `0x782a1a`, dispatches
  saved handler `0x1228a` in normal mode, and then clears saved handler
  longword `0x782a1c`.

Generic drain behavior:

- `0x1228a` rewinds the restored record, reads signed word `+2`, takes the
  absolute value as the byte count, and calls `0x12328`.
- `0x12328` consumes that many payload bytes through `0xdace`. The payload
  reader calls `0xa904`, treats fetch `D7 = -1` as an early negative return,
  and applies its local `0x1a 0x58` rule before the byte is counted as
  consumed.
- Normal generic drains do not echo bytes through `0xe002`, do not call
  printable handler `0xd04a`, and do not call a command-family payload handler.

Alternate/data mode:

- If `0x12218` dispatches while alternate/data mode `0x782c18` is nonzero, it
  calls `0x12358` with wrapper argument `0x1228a`.
- When saved handler `0x782a1c` is already `0x1228a`, `0x12358` calls the same
  generic drain wrapper. This preserves generic counted-drain behavior for
  stateful `W/w` payloads even in alternate/data mode.
- When saved handler differs from `0x1228a`, `0x12358` does not call that
  saved command-family handler. It rewinds the restored record, returns
  immediately for nonpositive counts, and for positive counts drains bytes
  through `0xdace` while echoing each normalized byte through append helper
  `0xe002`.
- That alternate/data branch is why raster, transparent-text, and font payload
  handlers do not run from alternate/data mode unless the parser returns to
  normal mode before delayed restore.

Output effect:

- The generic `0x1228a -> 0x12328` path has no page-root, page-object,
  publication, bridge, render, or pixel output. Its effect is byte-stream
  synchronization: payload bytes are removed from the host stream so the next
  parser byte starts after the counted payload.
- The alternate/data non-wrapper branch has no immediate page output either,
  but it preserves payload bytes in the active macro/data append stream through
  `0xe002`, so those bytes can become future replay input if that stored data
  is later executed.

State classification:

- Canonical parser state:
  parser mode `0x782999`, alternate/data mode `0x782c18`, active six-byte
  command record at `0x78299e`, and the restored count word at record `+2`.
- Parser scratch:
  tokenizer byte/numeric scratch used before `0x121cc`, plus the payload bytes
  while they are being drained through `0xdace`.
- Firmware bookkeeping:
  delayed-payload pending flag `0x782a1a`, saved handler `0x782a1c`, saved
  command record `0x782a20..0x782a25`, generic drain wrapper `0x1228a`, drain
  helper `0x12328`, alternate/data dispatcher `0x12358`, and append helper
  `0xe002`.
- Canonical page/render state:
  none. Any later page output must come from parser bytes after the drain or
  from separately replayed bytes appended through `0xe002`.
- Hardware/external:
  the original physical source of the payload bytes before `0xa904`.
- Unknown:
  no ROM-local parser middle edge remains for generic counted drains. Remaining
  work is command-family specific only when a saved handler is not the generic
  wrapper or when appended alternate/data bytes are later replayed.

Evidence:

- Checked-in explanations:
  [pcl-parser-core.md](pcl-parser-core.md), especially `Delayed Payload
  Scheduler` and `Parser Record Semantic Checkpoint`, and
  [direct-control-codes.md](direct-control-codes.md) for the local `ESC &d`
  `W/w` tokenizer boundary.
- Focused listings and extracts:
  `generated/disasm/ic30_ic13_payload_dispatch_011f82.lst`,
  `generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst`,
  `generated/disasm/ic30_ic13_main_parser_loop_011774.lst`, and
  `generated/analysis/ic30_ic13_tokenizer_macro_callers.md`.
- Fixture checks:
  `0x121cc snapshots delayed payload handler and parsed record`,
  `0x12218 restores delayed parsed record and dispatches saved handler`,
  `0x1228a consumes absolute delayed payload count without echo`, and
  `0x12358 direct alternate path echoes positive payload bytes only`.

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
  `0x119a6..0x119f4`, calls delayed restore boundary `0x12218`, and then
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
ESC *r1K 0x11
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

## Minimal Page/Font Scheduler Handoff Walkthrough

This is the smallest top-level handoff that reconciles optional font/resource
state before parsing or rendering resumes. It is not reached by a PCL command
table row, and it does not queue page objects or emit pixels directly. It
matters for exact byte-stream reproduction because later font selection,
downloaded-font lookup, and glyph rendering consume the candidate/context
state that this handoff can prune, refresh, or commit.

Entry and caller contracts:

- Host quiesce caller `0x447a` calls `0x19dd2` and ignores scheduler `D7`;
  only scheduler side effects can change later parsing or font state.
- Host/menu caller `0x4760` calls `0x19dd2` and consumes scheduler `D7`:
  `D7 = 0` returns immediately, while `D7 != 0` enters menu/default setup.
- External-ready teardown runs `0xba48 -> 0xc06e -> 0xc108 -> 0x19dd2 ->
  0x36e4`. Caller `0xbb16` ignores scheduler `D7`; final byte `0x780e08`
  comes from the following `0x36e4` status aggregate.
- Font-resource scan caller `0x1a2e4 -> 0x1a3c2` snapshots candidate count
  `0x78278e` to `0x782780`, calls `0x19dd2`, ignores scheduler `D7`, then
  passes `0x78219b`, `0x78219c`, and local `A6-0x02` to resolver `0x1b50e`.

Scheduler scan and predicate flow:

- `0x19dd6..0x19dda` publishes local scratch block `A6-0x28` through global
  pointer `0x782894`.
- `0x19eb6..0x19f00` clears two 20-byte scratch slots, checks optional-window
  gate bits `$8000.14` and `$8000.15`, and calls `0x1a0f2(1)` or
  `0x1a0f2(2)` when the matching gate permits a scan.
- `0x1a0f2..0x1a21e` scans optional window `0x200000..0x3ffffe` into scratch
  slot `0`, or optional window `0x400000..0x5ffffe` into scratch slot `1`.
  It publishes active scan fields `0x78288c`, `0x782884`, `0x782890`, and
  terminal byte `0x782898`.
- `0x1b9c0` classifies each resource cursor: `HEAD` returns `1`; `FONT`,
  `font`, `DUMY`, `TABL`, or `tabl` at the cursor or cursor `+8` return `0`;
  neither match returns `-1`.
- `0x1a220..0x1a252` handles classifier return `1` by advancing through the
  record length and returning record word `+0x0e`; `0x1a254..0x1a2e2` handles
  classifier return `0` by skipping known signatures and returning the first
  non-signature record word `+0x06`. Return `-1` appends a zero word and
  advances to the next optional-resource grid point.
- `0x1a042..0x1a0f0` compares canonical table slots
  `0x7828b6 + slot * 0x14` against the fresh scratch slots. `0x19f08..0x19fb6`
  performs the mirror comparison from fresh scratch to canonical table.
  `0x19de6..0x19df6` stores the two predicate bytes in `A6-0x29` and
  `A6-0x2a`.

Branch behavior:

- Both predicate bytes zero:
  `0x19dd2` calls `0x19fb8(0)`, runs shared font/default refresh `0x1b04c`,
  and returns `D7 = 1`.
- Status-return branch:
  when the first predicate is nonzero and `0x72a2` returns zero,
  `0x19e32..0x19e46` writes `0x780e8d`, raises status mask `0x00000200`
  through `0x9bee(0x780e2e, 0x00000200)`, calls `0x19fb8(predicate)`, and
  returns `D7 = 0`.
- Long-refresh branch:
  nonzero predicates outside the status-return branch call
  `0x1ba92(predicate)`, `0x178fa(predicate)`, `0x19d9c()`,
  `0x1a4fa(fresh_side_predicate)`, and `0x1a900()`, then return `D7 = 1`.
  This branch can prune candidate entries, release current downloaded-font
  payloads, mark candidates dirty, rescan optional ranges, validate active
  contexts, and copy the fresh scratch table into canonical `0x7828b6`.

Output effect:

- No direct page root, page object, render record, band work item, row-copy
  helper, or bitmap buffer is produced by `0x19dd2..0x1a2e2`.
- Pixel output can change only indirectly, when later font designation,
  downloaded-font resolution, resource lookup, printable text, publication, or
  rendering consumes the changed candidate/context/resource state.
- A byte-stream renderer with no optional cartridges can treat the optional
  windows as absent, while preserving the canonical table and caller-return
  behavior. A renderer that supports optional resources must preserve this
  handoff before later glyph selection or downloaded-font lookup.

State classification:

- Canonical:
  resource-window table `0x7828b6..0x7828dd`, status root `0x780e2e`, and
  status predicate byte `0x780e8d`.
- Derived/cache:
  scratch pointer `0x782894`, scan pointer `0x782884`, active optional-window
  base `0x78288c`, active optional-window limit `0x782890`, terminal byte
  `0x782898`, and candidate-list pointers/counts `0x7827a8`, `0x7827ac`,
  `0x7827b0`, `0x7827b4`, `0x782790`, `0x782794`, `0x782798`,
  `0x78279c`, predicate bytes `A6-0x29` and `A6-0x2a`, scratch slot
  `A6-0x28..A6-0x15` for window `0x200000..0x3ffffe`, scratch slot
  `A6-0x14..A6-0x01` for window `0x400000..0x5ffffe`, and caller local
  `A6-0x02` consumed after `0x1a3c2`.
- Parser scratch:
  none. This scheduler-local state is not a PCL command record or tokenizer
  buffer.
- Firmware bookkeeping:
  candidate-count snapshot `0x782780`, current downloaded-font records
  `0x782640..0x782776`, candidate pointer-list entries rooted at `0x782324`,
  active-font dirty bytes `0x782f2c` and `0x782f2d`, caller bookkeeping behind
  `0x447a` and `0x4760`, and return register `D7`.
- Hardware/external:
  optional-window gate bits `$8000.14` and `$8000.15`, and physical optional
  resource contents at `0x200000..0x3ffffe` and `0x400000..0x5ffffe`.
- Unknown:
  board-level names for `$8000.14/.15`, the user-visible name for status mask
  `0x00000200`, and physical optional-resource records that drive classifier
  return `-1`.

Evidence:

- Checked-in explanations:
  [page-font-scheduler.md](page-font-scheduler.md#page-font-scheduler-outcome-matrix),
  `Worked Path: Page Font Scheduler Resource Handoff` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md), and
  `Page/Font Scheduler Handoff` in
  [semantic-state-model.md](semantic-state-model.md).
- Focused listings:
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

Unresolved boundary:

- The ROM-local scheduler chain is bounded for the unchanged, status-return,
  and modeled changed-window exits. Remaining work starts at external optional
  resource data or board memory-map evidence for windows `0x200000..0x3ffffe`
  and `0x400000..0x5ffffe`; that evidence would name physical records and
  determine which candidate pruning, current-record release, canonical-table
  commit, or later page/font state changes are possible.

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
  boundaries are indexed as explicit external/manual-correlation entries:
  physical identity/timing for the external register family under
  [Active Render Device Handoff](unresolved-boundaries.md#active-render-device-handoff),
  retained-storage identity/failure conditions under
  [Retained Defaults And Service
  Persistence](unresolved-boundaries.md#retained-defaults-and-service-persistence),
  and HP/manual-facing names for folded status categories under
  [Folded Status Category
  Names](unresolved-boundaries.md#folded-status-category-names).

Evidence:

- Checked-in explanations:
  [external-ready-service.md](external-ready-service.md#external-ready-outcome-matrix),
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
  cursor-stack streams. Remaining direct-control work starts from variants
  that change a named consumer boundary: line-termination byte `0x78318f`
  before `0xf02c` / `0xf08c` / `0xf0f0`, cursor words
  `0x782c8a` / `0x782c8e` before `0xd04a`, margin/HMI/VMI fields
  `0x782dd6` / `0x782dda` / `0x78315c` / `0x783160`, span source fields
  `0x783184..0x78318a` before `0xf34a` / `0x12714`, page-root publication
  state before `0xff1e`, compact object bytes before `0x1ed84` / `0x1ef6a`,
  or row-construction inputs below `0x1effe`.

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

- `ESC &l66P` converts the parsed line count through current VMI `0x783160`, writes page
  extent `0x782dba`, selects the internal page code, recomputes page/text-bottom
  geometry, and refreshes the following printable cursor. The field-level route is
  documented in [Page-Length Nonzero Placement
  Checkpoint](publication-commands.md#page-length-nonzero-placement-checkpoint).
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
- That following printable uses the same single-entry short compact object
  shape as the ordinary printable path. The layout command has already
  refreshed placement; `ESC &l66P` itself writes page-layout state, and
  `0xd04a -> 0x12f2e -> 0x1387c` queues the printable entry. For the documented
  line-printer fixture, the queued object prefix is:

```text
00 00 00 00 00 00 00 01 20 90 01
```

  The first four bytes are the null next-object link, the next four bytes hold
  selector/context/count for a one-entry compact text object, and the payload
  entry is glyph `0x20` at compact coordinate `0x9001`.
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
  `generated/analysis/ic30_ic13_page_geometry_tables.md`, plus
  `generated/analysis/ic30_ic13_renderer_fixture_harness.md`.

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
- In both documented streams, the pre-command printable is the ordinary
  one-entry compact text object. The fixture report records the published
  object window as:

```text
00 00 00 00 00 00 00 01 20 00 01 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
```

  Its live compact prefix is the null next link, one-entry selector/count
  fields, and payload entry glyph `0x20` at compact coordinate `0x0001`.
  The geometry command publishes that object before writing the new page code
  or orientation, so the rendered rows are the pre-geometry rows while later
  objects consume the newly installed geometry fields.
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
  `Worked Path: Publication Commands To ROM-Derived Page Rows` and
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
  `generated/analysis/ic30_ic13_page_record_bridge.md`, plus
  `generated/analysis/ic30_ic13_renderer_fixture_harness.md`.

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
  ordered rule-list nodes under root `+0x24`. `0x13472` defines that order by
  comparing existing object byte `+4` with key `0x782a7c`, then `0x133aa`
  links the new 14-byte object at head, after the returned predecessor, or
  after the returned tail.
- Pending text spans reach `0x12714`. Portrait spans use
  `0x13520` / `0x1354a` / `0x135f0` to write class-`0x40` segment-list
  objects under root `+0x1c`; landscape spans use `0x136d2` to write
  fixed-list objects under root `+0x28`. `0x13690` searches fixed-list byte
  `+4` values before `0x136d2` allocates, so allocation failure after the
  search still leaves root `+0x28` and existing nodes unchanged.

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
- The addressed fixture for that stream pins the root contents before
  rendering: compact text object `0x00d0c004`, selector-7 rule object
  `0x00d0c02a`, mode-0 raster object `0x00d0c038`, bucket root `+0x1c`,
  rule-list root `+0x24`, and context slot `+0x2c = 0x440946b4`.
  The published raster bucket object is:

```text
00 d0 c0 04 80 00 00 02 00 00 c3 3c
```

  That object links back to the compact text object, carries class `0x80`,
  count `2`, and payload bytes `c3 3c`. The rule-list object is:

```text
00 00 00 00 01 07 5c 01 00 0c 00 05 00 00
```

  That rule has no next node, bucket/key byte `0x01`, selector `7`, packed key
  `0x5c01`, width `0x000c`, height `0x0005`, and continuation height `0`.
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
  `generated/analysis/ic30_ic13_page_record_bridge.md`, plus
  `generated/analysis/ic30_ic13_renderer_fixture_harness.md`.

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
  streams. New ROM-local publication/render work must start from a stream that
  changes one of the named handoff fields: publication header bytes/words
  `+0x04`, `+0x07`, `+0x08`, `+0x0a`, `+0x0c`, `+0x18`, or `+0x1a` written
  by `0xffb0..0x10080`; pool/source selectors `0x780ea6`, `0x780eaa`, or
  `0x780eae`; bridge roots `+0x1c`, `+0x24`, `+0x28`, or context slots
  `+0x2c..+0x68` before `0x1edc6`; render roots `+0x18`, `+0x1c`, `+0x20`,
  or `+0x24..+0x60` after `0x1edc6`; render work `+0x10`; object bytes
  consumed by `0x1ef6a`; or row-construction inputs below the selected
  renderer.

Evidence:

- Checked-in explanations: `Worked Path: Reset And Default Environment`, `Worked Path:
  FF Publication`, `Worked Path: Publication Commands To ROM-Derived Page Rows`, and
  `Worked Path: Published Record To Active Bands` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md), [Representative
  Parsed-Stream Outcomes](publication-commands.md#representative-parsed-stream-outcomes)
  and `Publication Header Copy Checkpoint` in
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

## Minimal Reset Default Environment Walkthrough

This is the top-level path from reset/default records into later byte-stream
rendering. `ESC E` is both a publication boundary and an environment rebuild:
it can publish already queued pixels, then reset the parser, page environment,
font motion metrics, raster state, and default-derived fields that subsequent
host bytes consume.

Representative stream:

```text
! ESC E !
```

Reset dispatch and ordering:

- Host bytes enter through `0xa904`, parser wrapper `0xda9a`, and parser loop
  `0x11774`.
- The first `!` reaches `0xd04a`, ensuring current page root `0x78297a` and
  queuing a compact text object.
- `ESC E` reaches handler `0xcc52`.
- `0xcc52` calls reset helper `0xcc70`, metric refresh `0xcbd4`, and
  parser/data-chain reset `0xe146`, then clears reset status byte `0x782a93`.
- `0xcc70` flushes pending text through `0xf34a`, publishes a valid current
  root through `0xff1e` or clears missing-root state, waits through `0x9ac2`,
  clears orientation byte `0x782da3`, calls environment rebuild helper
  `0xcda2`, and rebuilds raster/page-derived state.

Default producer and consumer path:

- Selected default backing records are loaded through `0x5e80`, using selector
  `0x7822d5` to choose a record under `0x780eda`.
- Backing record byte `+0` becomes canonical default byte `0x78219d`; backing
  record word `+2` becomes default line-spacing word `0x78219e`; backing record
  byte `+5` bit 2 derives default environment/paper byte `0x7821a2` as `0x80`
  or `0`.
- Menu/update handlers `0x5060`, `0x50be`, and `0x52ba` can update the backing
  records and the canonical defaults before a later reset consumes them.
- `0xcda2` consumes `0x78219d`, `0x78219e`, `0x7821a2`, reset gate
  `0x7810b2`, and current-font context `0x782ee6`.
- `0xcda2` copies `0x78219d` into reset environment word `0x782da4`, copies
  `0x7821a2` into paper/environment byte `0x782da6` when the gate permits, and
  derives reset VMI `0x783160` from `0x78219e` through `0xcfea`, `0xcf52`, and
  `0x104d8`.
- `0xcbd4` refreshes HMI `0x78315c` and active-symbol snapshots from current
  font context `0x782ee6`.
- `0xe146` clears parser/data-chain records, text accumulation bytes, and macro
  context-stack records before subsequent host bytes are parsed.

Output and page-image effect:

- The pre-reset `!` is published before reset rebuilds the environment; it
  renders through the ordinary path `0xff1e -> 0x1ed84 -> 0x1edc6 -> 0x1ef6a`.
- For the checked `! ESC E` publication half, the pre-reset compact object is:

```text
00 00 00 00 00 00 00 01 20 00 01
```

  The live entry is glyph `0x20` at compact coordinate `0x0001`. The published
  page-record window keeps that prefix followed by zero padding in the bucket
  object area, and the fixture records final reset-side state as current page
  root `0`, one publication, one root clear, one span flush, HMI
  `0x00120000`, data-chain pointer `0x782d3e`, and reset status `0`.
- If no current page root exists, `ESC E` clears/rebuilds state without
  synthesizing a page object or pixels.
- The post-reset `!` is parsed after `0xcda2`, `0xcbd4`, and `0xe146` have
  rebuilt HMI/VMI, current text slot, parser state, and raster state. Its
  position and later page-object fields therefore depend on the reset-derived
  defaults above.

State classification:

- Canonical:
  selected default records under `0x780eda`, defaults `0x78219d`, `0x78219e`,
  `0x7821a2`, reset environment word `0x782da4`, paper/environment byte
  `0x782da6`, current page root `0x78297a`, published page/control record, and
  parser/data-chain base records.
- Derived/cache:
  reset HMI `0x78315c`, reset VMI `0x783160`, top offset `0x782dce`, raster
  state block `0x783170`, selected backing-record index from `0x7822d5`,
  line-count conversion results, and render-band caches after publication.
- Parser scratch:
  `ESC E` command record, parser/data-chain records cleared by `0xe146`,
  post-reset parser mode, and any following printable bytes.
- Firmware bookkeeping:
  retained/default dirty flags `0x780eba..0x780ed8`, readback buffer
  `0x782252..0x782270`, publication flag `0x782996`, reset completion byte
  `0x782a93`, reset pending bytes `0x782997/0x782998`, and retained-record
  maintenance counters.
- Hardware/external:
  physical retained-storage device behind `$a400` / `$8c01`, the external
  producer of `$8000.w` panel/service bytes, and physical conditions behind
  retained-record failures.
- Unknown:
  no ROM-local middle edge remains for `ESC E` publication, missing-root reset,
  default-record consumption by `0xcda2`, HMI/VMI refresh, or parser/data-chain
  clearing. Remaining reset/default uncertainty is external retained-storage and
  panel/service input provenance, plus manual-facing names for several latches.

Evidence:

- Checked-in explanations:
  [reset-default-environment.md](reset-default-environment.md#reset-default-outcome-matrix),
  `Control Panel Default Outcome Matrix` in
  [control-panel-nvram-selftest.md](control-panel-nvram-selftest.md), `Worked Path:
  Reset And Default Environment` and `Default Environment Record Producers` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md), and `ESC E Reset And Default
  Environment` in [semantic-state-model.md](semantic-state-model.md).
- Focused listings:
  `generated/disasm/ic30_ic13_esc_e_reset_00cc52.lst`,
  `generated/disasm/ic30_ic13_esc_e_environment_reset_00cda2.lst`,
  `generated/disasm/ic30_ic13_esc_e_metric_refresh_00cbd4.lst`,
  `generated/disasm/ic30_ic13_esc_e_parser_state_reset_00e146.lst`,
  `generated/disasm/ic30_ic13_default_env_load_005e80.lst`,
  `generated/disasm/ic30_ic13_default_env_menu_update_004fb0.lst`,
  `generated/disasm/ic30_ic13_default_env_record_maintenance_0056c2.lst`,
  `generated/disasm/ic30_ic13_retained_record_bulk_load_005a16.lst`, and
  `generated/disasm/ic30_ic13_nvram_default_record_commit_0096c4.lst`, plus
  `generated/analysis/ic30_ic13_renderer_fixture_harness.md`.

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
- The addressed paper-source stream uses one stream chunk at `0x00d0c000` and
  publishes the same one-entry compact bucket prefix as the other
  publication-boundary streams:

```text
00 00 00 00 00 00 00 01 20 00 01
```

  The printable payload is glyph `0x20` at compact coordinate `0x0001`.
  After the publication boundary, `0xef62` leaves selected value `0x80`,
  paper-source byte `0x782da6 = 0x80`, pending refresh byte
  `0x782998 = 1`, cursor x/y at packed `5` / `92.1`, and ROM-visible
  output/control bytes `0x780e8f = 0x80` and `0x780e26 = 1`.
- `ESC &l2X` does not create a pixel object or publish immediately. Its
  ROM-visible page effect is the stored copy count consumed by later
  publication.
- The addressed copies stream uses one stream chunk at `0x00d0d000`. Handler
  `0xeef0` stores `0x782da4 = 2`; the trailing FF publishes the existing
  compact bucket, clears current root `0x78297a`, and copies the count into
  published pool-header word `+0x0c = 2`.
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
  `Worked Path: Publication Commands To ROM-Derived Page Rows` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md), and
  `Publication Commands To ROM-Derived Page Rows` in
  [semantic-state-model.md](semantic-state-model.md).
- Focused listings:
  `generated/disasm/ic30_ic13_paper_source_handler_00ef62.lst`,
  `generated/disasm/ic30_ic13_copies_handler_00eef0.lst`,
  `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`, and
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`, plus
  `generated/analysis/ic30_ic13_renderer_fixture_harness.md`.
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
- In the documented scheduler-selection fixture, published source record
  `0x00d0eaa0` is copied into active source `0x780eae`; selector byte
  `0x7820bc` switches from `0` to `1`; render work record `0x782128` is
  selected; and `0x783a18 = 0x782128` becomes the active render pointer
  consumed by `0x1ef6a`.
- `0x1ed84` copies active source header fields from `0x780eae` into the
  selected render work record and calls `0x1edc6`.
- `0x1edc6` copies source bucket root `+0x1c` to render root `+0x18`, source
  rule-list root `+0x24` to render root `+0x1c`, source fixed-list root
  `+0x28` to render root `+0x20`, and context slots `+0x2c..+0x68` to render
  slots `+0x24..+0x60`.
- The bridge also initializes render-time continuation fields. At
  `0x1edf4..0x1ee0e`, each rule-list node has selector byte `+0x05` ORed
  with `0x10` and height word `+0x0a` copied to remaining rows `+0x0c`. At
  `0x1ee10..0x1ee5e`, each fixed-list node has byte `+0x05` ORed with
  `0x10`, word `+0x08` copied to remaining rows `+0x0a`, byte `+0x0c` set to
  `1`, and byte `+0x0d` set to `8`. Later band renders consume these mutated
  render-record fields.

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
- The active-loop render fixture starts with active selector `0x7820bc = 1`,
  paired selector `0x7820c0 = 0`, active record `0x782128`, and paired record
  `0x7820c4`. With active `+6 = 20`, active remaining rows
  `+0x10 - +0x16 = 3`, and paired remaining rows `3`, computed capacity is
  `14`, so `0x1ec8e..0x1ecac` calls `0x1ef6a`, increments active band word
  `+0x10` from `3` to `4`, and increments throttle word `+0x0e` from `7` to
  `8`.
- The capacity-wait sibling uses active `+6 = 10`, active remaining `4`, and
  paired remaining `1`, producing capacity `5`; `0x1ecb0..0x1ecd2` clears
  `+0x0e`, signals wait object `0x780182`, and waits through `0x10d0(2)`
  without calling `0x1ef6a`.
- The downloaded-glyph scheduler fixture checks the loop-produced band words:
  after `0xff1e` / `0x1ed84` seed render words `+0x10/+0x16` from zeroed
  source `+0x18`, `0x1eba4` produces render calls for band words `0..9` and
  leaves work word `+0x10 = 10`. Only copied buckets `1` and `9` dispatch
  compact objects in that stream, with bucket `9` producing page row `86`.

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
  band word `+0x10`. Rule-list remaining rows `+0x0c` and fixed-list
  remaining rows `+0x0a` become canonical render-record fields after bridge
  helper `0x1edc6` initializes them.
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
  `generated/analysis/ic30_ic13_render_path_references.md`, plus
  `generated/analysis/ic30_ic13_renderer_fixture_harness.md`.

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
- The same bridge initializes rule-list and fixed-list continuation fields:
  rule selector byte `+0x05` is marked with `0x10`, rule height `+0x0a`
  becomes remaining rows `+0x0c`, fixed byte `+0x05` is marked with `0x10`,
  fixed height `+0x08` becomes remaining rows `+0x0a`, and fixed bytes
  `+0x0c/+0x0d` become `1/8`.
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
- In the band-setup fixture, `0x1ef86` divides
  `(work +0x10 + work +0x08 - work +0x0a) = 0x0014` by work word
  `+0x06 = 6`, stores remainder `2` in `0x783a22`, stores scaled current-band
  rows `64` in `0x783a20`, and stores destination base `0x00101000` in both
  `0x783a28` and render-record long `+0x12`.
- `0x1efc2` walks bucket-chain objects from render root `+0x18`.
- In the bucket-dispatch fixture, `0x1efc2` indexes render bucket word `2` at
  slot offset `8`, then routes object class bytes through the same compact,
  segment-list, and encoded-raster branches documented below.
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
  caches `0x783a40..0x783a48`, and fallback base
  `0x7810b4 + byte_pair_offset`.
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
  `generated/analysis/ic30_ic13_render_dispatch_tables.md`, plus
  `generated/analysis/ic30_ic13_renderer_fixture_harness.md`.

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
- The built-in candidate window consumed by that path is created earlier by
  `0x1a2e4 -> 0x1a616 -> 0x1a9be`. For the verified IC32/IC15 resources,
  that scan accepts 24 `HEAD`-path font records, with 12 class-zero and
  12 class-one candidates in the low built-in resource window.
- Primary selection copies class-zero window `0x7827ac` / `0x782798` into
  active pointer/count `0x78287c` / `0x7827b8`, giving `0x782354` / `12`.
  Secondary selection copies class-one window `0x7827a0` / `0x782790`,
  giving `0x782324` / `12`.
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
  candidate counts/cursors `0x78278e`, `0x782790..0x78279e`, and
  `0x7827a0..0x7827b4`, active candidate pointer/count
  `0x78287c` / `0x7827b8`, candidate survivor lists, selected candidate slot
  `0x7828a8`, selected target `0x7828de`, snapshot records
  `0x783148/0x783152`, HMI `0x78315c`, transient selected context
  `0x782992`, current font id `0x782f2e`, compact coordinates,
  glyph-entry pointers, and render-band fields.
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
- Checked-in command-family detail:
  [symbol-set-selection.md](symbol-set-selection.md).
- Focused listings and extracts:
  `generated/disasm/ic30_ic13_font_context_install_00c428.lst`,
  `generated/disasm/ic30_ic13_font_update_common_00c580.lst`,
  `generated/disasm/ic30_ic13_font_candidate_activate_01569c.lst`,
  `generated/disasm/ic30_ic13_font_id_select_017708.lst`,
  `generated/disasm/ic30_ic13_symbol_set_handler_01be22.lst`,
  `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`,
  `generated/analysis/ic30_ic13_active_symbol_set_flow.md`,
  `generated/analysis/ic30_ic13_font_context_bridge.md`, and
  `generated/analysis/ic30_ic13_text_glyph_index_flow.md`, plus
  `generated/analysis/ic30_ic13_renderer_fixture_harness.md`.

## Minimal Symbol-Set Map Walkthrough

This walkthrough isolates the symbol-set and map-patching subpath inside font
selection. Symbol commands do not draw immediately. They change requested
symbol words, refresh the selected font context, rebuild or patch the active
character-to-glyph map, and thereby change how later printable bytes become
compact glyph payloads.

Representative streams:

```text
ESC (0N ESC (s0p10h12v0s0b3T ! !
ESC (10U ESC (s0p10h12v0s0b3T ! !
ESC (11U ESC (s0p10h12v0s0b3T ! !
ESC (0@ ESC (s0p10h12v0s0b3T ! !
ESC (7X ! !
```

Parser and requested-symbol route:

- Primary `ESC (` reaches setup wrapper `0x1201e`, which writes synthetic
  setup slot word `0`; secondary `ESC )` reaches `0x12008`, which writes slot
  word `1`.
- Symbol/designation terminal wrapper `0x120be` calls handler `0x1be22`, then
  calls common refresh `0xc580`.
- `0x1be22` rewinds command-record cursor `0x78299e`, reads final byte `+1`,
  integer parameter `+2`, and the synthetic slot word. Ordinary finals compute
  requested word `(abs(parameter) << 5) + final - 0x40`.
- Primary ordinary finals write `0x782ef4`; secondary ordinary finals write
  `0x782f04`. Successful ordinary finals set dirty flags
  `0x782f2c = 1` and `0x782f2d = 1`.
- Final `@` dispatches through ROM table `0x1bde2`. The documented `@0..@3`
  cases copy default-symbol words or run default-font helper paths before the
  same refresh gate.
- Final `X` is font-id selection, not an ordinary symbol word. It restores the
  prior requested symbol word, sets marker `0x78287b`, calls
  `0x17708(slot, font_id)`, and enters refresh with dirty flag
  `0x782f2c = 2`.

Candidate refresh and map rebuild:

- `0xc580` consumes dirty flags, selected text slot `0x782f06`, and
  page-root live flags `0x78297f..0x78298e`. Dirty `1` can call candidate
  refresh `0x13eb8`; dirty `2` skips candidate refresh and can install only
  the current context for the selected slot.
- Candidate refresh reaches `0x1569c` and `0x156de`. `0x1569c` selects the
  active candidate window, and `0x156de` filters by requested words
  `0x782ef4` / `0x782f04`, remembered words `0x782f08` / `0x782f0a`, and
  fallback table `0x782f0c..0x782f18`.
- For the verified built-in class-zero window, `ESC (0N`, `ESC (10U`, and
  `ESC (11U` write requested words `0x000e`, `0x0155`, and `0x0175`, then
  select built-in record starts `0x000cb8`, `0x000418`, and `0x000868`.
- `0x144d2` writes current-font context record `0x782ee6` or `0x782ef6`.
  `0x14c64` rebuilds the active map `0x782f32` or `0x783032`.
- `0x14f16` runs after `0x14c64` has built a base map. It reads selected
  candidate `0x7828a8`, checks the selected font's normalized symbol, and only
  applies its hard-coded or table-patch paths when that selected font
  normalizes to Roman-8 word `0x0115`.
- Non-Roman streams such as `ESC (0N`, `ESC (10U`, and `ESC (11U` therefore
  select distinct built-in records. They are not modeled as Roman-8 record
  `0x00004c` plus a `0x14f16` patch.

Printable consumption and output effect:

- The later `ESC (s0p10h12v0s0b3T` attribute stream uses the same selected
  symbol state while choosing the visible font context.
- Later printable `!` bytes reach `0xd04a -> 0x1393a`. Source helper
  `0x1393a` reads selected slot `0x782f06`, current context
  `0x782ee6` / `0x782ef6`, and active map `0x782f32` / `0x783032`.
- Primary `ESC (0N`, `ESC (10U`, and `ESC (11U` followed by the Courier
  attribute stream select contexts `0xc0080cb8`, `0xc4080418`, and
  `0xc4080868`, then queue compact text from those contexts.
- Secondary `ESC )0N`, `ESC )10U`, and `ESC )11U` select class-one contexts
  `0xc00ae122`, `0xc40ad87a`, and `0xc40adcce`; SO handler `0xc6b8` selects
  slot `1` before later printable bytes consume secondary map `0x783032`.
- Page-object production, publication, bridge, and render dispatch are the
  ordinary compact-text route:
  `0xd04a -> 0xd824 -> 0x12f2e -> 0x1387c -> 0xff1e -> 0x1ed84 ->
  0x1edc6 -> 0x1ef6a -> 0x1effe`.
- The pixel effect is future glyph selection. Already queued compact payloads
  keep the glyph byte captured when their printable byte originally ran.

State classification:

- Canonical:
  requested symbol words `0x782ef4` / `0x782f04`, active symbol words
  `0x783144` / `0x783146`, current contexts `0x782ee6` / `0x782ef6`, selected
  text slot `0x782f06`, active maps `0x782f32` / `0x783032`, page-root context
  slots, compact text payload glyph bytes, and render-record context slots.
- Derived/cache:
  remembered words `0x782f08` / `0x782f0a`, fallback words
  `0x782f0c..0x782f18`, default-symbol table `0x782f1c..0x782f28`, selected
  candidate pointer `0x7828a8`, active candidate pointer/count
  `0x78287c` / `0x7827b8`, selected map slot `0x7828de`, and map flags
  `0x783132` / `0x783133`.
- Parser scratch:
  synthetic setup records from `0x1201e` / `0x12008`, terminal command
  records at `0x78299e`, final byte, integer parameter, dirty flags while
  refresh is pending, and final-`@` subdispatch index.
- Firmware bookkeeping:
  `0x78287b`, page-root context-slot scan state in `0xc4fc`, transient
  full-root flag `0x78298f`, candidate active bits, and local patch-table
  cursors inside `0x14f16`.
- Hardware/external:
  none for the verified built-in symbol streams. Cartridge or other optional
  resource records remain external data inputs to the same candidate-filtering
  addresses.
- Unknown:
  no unresolved ROM-local middle edge remains for ordinary symbol finals,
  final `@`, final `X`, selected-context map rebuild, or `0x14f16..0x14fcc`
  patcher control flow in the documented paths. Remaining work must change
  candidate records, selected map bytes, final context install, compact object
  shape, bridge state, or ROM-derived rows.

Evidence:

- Checked-in explanations:
  [Symbol/Font Designation Outcome
  Matrix](symbol-set-selection.md#symbolfont-designation-outcome-matrix),
  [symbol-map-patching.md](symbol-map-patching.md),
  [font-context-metrics.md](font-context-metrics.md),
  [built-in-resource-scan.md](built-in-resource-scan.md), and
  `Symbol Set And Map Patch Boundary` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md).
- Focused listings and extracts:
  `generated/disasm/ic30_ic13_symbol_set_handler_01be22.lst`,
  `generated/disasm/ic30_ic13_font_update_common_00c580.lst`,
  `generated/disasm/ic30_ic13_font_candidate_activate_01569c.lst`,
  `generated/disasm/ic30_ic13_font_id_select_017708.lst`,
  `generated/disasm/ic30_ic13_active_object_dispatch_014ba4.lst`, and
  `generated/analysis/ic30_ic13_symbol_set_patch_tables.md`.
- Fixture names cited by the owner notes:
  `0x120be/0x1be22 symbol-set stream updates active words and 0x14f16 glyph
  maps`, `symbol-set parser trace feeds active map patches`, `live parser
  symbol-set streams select non-Roman built-ins`,
  `real final-@ default-table streams select visible built-ins`, and
  `font-ID built-in selection feeds visible page-record rows`.

## Minimal Built-In Glyph Resource Walkthrough

This section documents where built-in text pixels come from after font
selection has chosen a context and `0x1393a` has mapped a host byte to a glyph
byte. Font-selection state answers which context and map are active; this
resource path answers which IC32/IC15 bytes become row-copy input.

Representative upstream streams:

```text
ESC (s0p10h12v0s0b3T ! !
ESC )s0p16h8v0s0b0T SO ! !
```

Resource address and context form:

- The IC32/IC15 resource image maps file offset `N` to firmware resource
  address `0x80000 + N`.
- Built-in context longwords carry flag bits plus that firmware address. The
  primary selected context `0xc008004c` points at built-in record offset
  `0x00004c` after flag masking; generated resource extraction lists the same
  record as context `0x4008004c`. The secondary selected context
  `0xc00ae122` points at record offset `0x02e122`.
- Bit 30 selects the offset-table form in renderer helper `0x1f354`. In that
  form, `0x1f354` masks the context base to the resource address, reads the
  selected record's offset table, adds the long relative table entry to the
  record base, and interprets the resulting glyph-entry header.

Host byte to glyph entry:

- `0x14c64` rebuilds primary map `0x782f32` or secondary map `0x783032` before
  text is queued. For bit-30 offset-table resources, `0x14d9c` builds a base
  map from selected record words `+0x0e` and `+0x10`: bytes before the first
  code are zero, bytes from first through last become sequential glyph indexes
  starting at zero, and bytes after the last code are zero. Inverted ranges
  report `(0xe7, 0x91)` through `0x128c`. `0x14f16` applies symbol-set patches
  when the selected symbol path requires them.
- `0x1393a` selects primary map/context when `0x782f06 == 0`, or secondary
  map/context when `0x782f06 != 0`.
- `0x1393a` stores the mapped byte as the low byte at text object `+0x0b` and
  copies the selected context longword into text object `+0`.
- `0x12f2e` copies text object byte `+0x0b` as the first byte of each compact
  payload entry. That payload byte, not necessarily the original host byte, is
  the glyph index later consumed by `0x1f354`.

Renderer-side glyph fields:

- Publication and bridge preserve the page-root context slots:
  `0xff1e -> 0x1ed84 -> 0x1edc6`.
- Compact dispatch reaches
  `0x1ef6a -> 0x1efc2 -> 0x1effe -> 0x1f354`.
- `0x1f008` loads the selected render-record context slot into active context
  cache `0x783a2c` before `0x1f354` resolves the glyph.
- For built-in offset-table entries, `0x1f354` consumes glyph-entry byte `+4`
  as bitmap delta, byte `+5` as mode/plane value, word `+6` as row count, and
  word `+8` as pixel width.
- The generated built-in payload extract confirms this formula across `24`
  scanned records, `5730` table slots, and `5310` extracted payloads. Records
  include `(unnamed)` record `0x00004c`, first `COURIER` record `0x000418`,
  first `LINE_PRINTER` record `0x0146b4`, and secondary selected
  `LINE_PRINTER` record `0x02e122`.
- The row-copy matrix ties those resource bytes to ROM helper targets. Context
  `0x4008004c`, glyph `0`, entry `0x001088`, width `9`, rows `32`, and span
  `2` dispatch through helper `0x01fe76`; context `0x44080418`, glyph `0`,
  entry `0x007baa`, width `28`, rows `29`, and span `4` dispatch through
  helper `0x0207ac`; context `0x440946b4`, glyph `32`, entry `0x015330`,
  width `4`, rows `22`, and span `1` dispatch through helper `0x01fa5c`.
- The ROM-scanned matrix covers spans `1`, `2`, `4`, `6`, and `8`. It records
  `5730` glyph records across `24` resource records, mode counts
  `[(0, 420), (1, 5310)]`, no render spans wider than `16` bytes, and no
  non-mode-1 entries with nonzero bitmap deltas in the verified built-in ROMs.

Output and page-image effect:

- Primary selection stream `ESC (s0p10h12v0s0b3T ! !` queues compact object
  `00 00 00 00 00 00 00 02 00 6a 00 00 68 02`, bridges context
  `0xc008004c`, and renders Courier rows through compact helper `0x1fe76`.
- Secondary selection stream `ESC )s0p16h8v0s0b0T SO ! !` queues compact object
  prefix `00 00 00 00 00 01 00 02 00 c9 00 00 cb 01`, bridges context
  `0xc00ae122`, and renders secondary Line Printer rows through helper
  `0x207ac`.
- The pixel provenance for those rows is:
  host byte -> active map byte -> compact payload glyph byte -> render-record
  context slot -> IC32/IC15 glyph-entry fields -> row-copy helper bytes.

State classification:

- Canonical:
  IC32/IC15 resource bytes, built-in font records, offset tables, glyph-entry
  fields, primary/secondary current-font contexts `0x782ee6` / `0x782ef6`,
  active character maps `0x782f32` / `0x783032`, page-root context slots, compact
  payload glyph bytes, and render-record context slots.
- Derived/cache:
  selected candidate slot `0x7828a8`, selected context longword, active context
  cache `0x783a2c`, masked resource base, relative glyph offset, `A2` bitmap
  pointer, optional `A3` trailing-plane pointer, span `D1`, rows `D3`, and
  row-copy table target.
- Parser scratch:
  font-selection command records, active symbol-set request words, dirty flags
  `0x782f2c/0x782f2d`, and original host bytes before `0x1393a` maps them.
- Firmware bookkeeping:
  candidate-window scans, map snapshot state `0x783148/0x783152`, page-root
  font-slot scan state in `0xc4fc`, publication flag `0x782996`, and render-work
  progress.
- Hardware/external:
  none for the verified IC32/IC15 built-in record bytes used by the cited
  primary and secondary streams.
- Unknown:
  the built-in glyph field layout and selected-resource-to-renderer path are not
  unresolved for the cited streams. The separate resource-data boundary remains
  secondary segment-57 continuation after verified firmware address
  `0x0bffff`, where the ROM path is known but the physical/resource-window
  decode after `0x0c0000` is not verified.

Evidence:

- Checked-in explanations:
  [resource-rom.md](resource-rom.md#resource-rom-outcome-matrix),
  [built-in-resource-scan.md](built-in-resource-scan.md),
  [font-context-metrics.md](font-context-metrics.md),
  `Built-In Font Selection To Visible Text` in
  [semantic-state-model.md](semantic-state-model.md), and `Worked Path: Font
  Selection To Visible Glyphs` / `Worked Path: Compact Glyph Row-Copy Helpers`
  in [firmware-dataflow-model.md](firmware-dataflow-model.md).
- Generated extracts:
  `generated/analysis/ic32_ic15_builtin_glyph_payloads.md`,
  `generated/analysis/ic32_ic15_font_records.md`,
  `generated/analysis/ic30_ic13_text_glyph_index_flow.md`, and
  `generated/analysis/ic30_ic13_render_row_copy_fixtures.md`, plus
  `generated/analysis/ic30_ic13_renderer_fixture_harness.md`.
- Focused listings:
  `generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst`,
  `generated/disasm/ic30_ic13_bitmap_row_copy_tables_01fa5c.lst`,
  `generated/disasm/ic30_ic13_glyph_row_copy_helper_02f27c.lst`,
  `generated/disasm/ic30_ic13_font_context_install_00c428.lst`, and
  `generated/disasm/ic30_ic13_default_font_tables_01ab84.lst`.

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
- For the object above, the ROM-derived literal row is:

```text
................####........#####.#.#.#..#.#.#.#
```

  This row is the direct consequence of payload bytes `f0 0f aa 55`, packed
  coordinate/key `0x0001`, mode helper `0x1f8da`, and the bridged render root
  consumed by `0x1efc2 -> 0x1f88e`.

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
  `generated/disasm/ic30_ic13_bitmap_encoded_span_modes_01f88e.lst`, plus
  `generated/analysis/ic30_ic13_renderer_fixture_harness.md`.

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
- The resulting two-object chain has these renderer-facing object fields from
  `+0x04` onward:

```text
80 00 00 f2 <initial packed key> <payload bytes 0x0000..0x00f1>
80 00 00 3a <advanced packed key> <payload bytes 0x00f2..0x012b>
```

  Both objects are class `0x80`, mode `0`. The first loop copies `0x00f2`
  payload bytes, subtracts that capacity from raster state `+0x04`, and
  advances the packed key through `0x332ee(0x00f2, 1)`. The second loop copies
  the remaining `0x003a` bytes, leaves the new chunk with `0x782a70 = 0x00b8`,
  and becomes the page-root bucket head pointing back to the earlier object.
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
  `generated/disasm/ic30_ic13_bitmap_encoded_span_modes_01f88e.lst`, plus
  `generated/analysis/ic30_ic13_renderer_fixture_harness.md`.

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

- The replay fixture records the same payload as glyph list `[32]` and
  coordinate list `[1]`. Its page-record bridge object is the compact prefix
  above followed by padding:

```text
00 00 00 00 00 00 00 01 20 00 01 00 00 00
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
  `generated/analysis/ic30_ic13_tokenizer_macro_callers.md`, plus
  `generated/analysis/ic30_ic13_renderer_fixture_harness.md`.

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
  selected overlay record exists, and current page-root flags word `+0x14`
  bit 0 is clear, `0xff1e` / `0xff8e` reselects id `0x782a94` through
  `0xe0a4`.
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
- For the minimal `!\r` overlay payload, the replayed printable queues the
  same one-glyph compact object bytes as the direct and macro-execute text
  paths:

```text
00 00 00 00 00 00 00 01 20 00 01
```

  The leading longword is the bucket-chain next pointer, the count byte is
  `1`, and the payload begins with glyph byte `0x20` plus the compact
  coordinate bytes. The following replayed carriage return routes through
  `0xf02c`; it advances parser/page cursor state for subsequent bytes but
  does not allocate a second visible object for this minimal payload.
- Repeated overlay publication keeps the macro record canonical and replays
  it on each page boundary. The same stored `!\r` payload composes with the
  first page's selector-7 rule object:

```text
00 00 00 00 01 07 88 01 00 0c 00 03 00 00
```

  and then with the second page's selector-7 rule object:

```text
00 00 00 00 01 07 e4 00 00 08 00 04 00 00
```

  This makes overlay state `0x782a92` / `0x782a94` canonical page-finalization
  state, while page-root objects remain page-local canonical data under
  `0x78297a`.
- The skip-gate branch is also page-object visible. A base page with printable
  `?` and selector-7 rule object:

```text
00 00 00 00 01 07 a2 00 00 06 00 02 00 00
```

  publishes unchanged when overlay mode is disabled, when `0xe0a4(0x782a94)`
  finds no nonempty selected record, or when page-root flags word `+0x14` bit
  0 blocks overlay re-entry. Those gates therefore affect whether replay
  mutates the page root, not how the renderer later interprets the base
  objects.
- After replay cleanup, `0xff1e` publishes the page root. `0x1ed84` and
  `0x1edc6` copy bucket, rule, fixed-list, and context roots into the active
  render record.
- `0x1ef6a` renders the composed record through the same compact, rule,
  fixed-list, segment-list, and raster helpers used by live host bytes. Overlay
  replay has no overlay-specific pixel writer.

Overlay payload variants:

- Stored cursor payload `ESC &a2C!` remains in the same non-replay frame kind
  but routes the replayed cursor command through `0xf39e` before printable
  `0xd04a`. It moves packed horizontal cursor `10 -> 36`, then queues compact
  text payload:

```text
00 01 20 0a 02
```

  The page still composes with selector-7 rule object:

```text
00 00 00 00 01 07 82 02 00 07 00 02 00 00
```

  which the rule renderer `0x1f596` mutates to:

```text
00 00 00 00 01 07 82 02 00 07 00 02 ff ca
```

- Stored vertical-decipoint payload `ESC &a72V!` routes through `0xf60a`,
  moves packed vertical cursor `20 -> 30`, leaves x at packed `10`, and queues
  compact text payload:

```text
00 01 20 90 01
```

  Here the canonical overlay fields are still `0x782a92` / `0x782a94`; the
  derived/cache fields are the compact coordinate `0x9001`, rule key
  `0x8801`, and renderer continuation/mutation fields written by the bridge
  and `0x1f596`.
- Stored transparent-data payload `ESC &p2X!!` proves that overlay replay can
  enter delayed binary payload mode. Parser handler `0x11f5a` saves delayed
  record:

```text
80 58 00 02 00 00
```

  then delayed handler `0x12452` restores it and feeds raw bytes `21 21`
  through `0xd04a`. The queued compact object begins:

```text
00 00 00 00 00 00 00 02 20 00 01 20 02 02
```

  while the page's selector-7 rule:

```text
00 00 00 00 01 07 e0 02 00 09 00 02 00 00
```

  remains a normal rule-list object consumed by the publication bridge and
  rule renderer.
- Stored raster payload `! ESC *t300R ESC *r0A ESC *b2W c3 3c` proves that
  overlay replay can cross from printable text into raster command state and
  back into normal page buckets. It queues the compact text object for `!`
  plus a mode-0 raster object:

```text
00 00 00 00 80 00 00 02 00 00 c3 3c
```

  The raster object is then copied by `0x1ed84` / `0x1edc6` into the active
  render record and consumed by `0x1ef6a` through the same raster helper path
  as a live `ESC *b#W` payload.

State classification:

- Canonical:
  macro record pool `0x782a98`, selected record pointer `0x782d7a`, overlay
  state `0x782a92`, saved overlay id `0x782a94`, current page root
  `0x78297a`, page-root flags word `+0x14` bit 0, non-replay frame fields
  at `0x782d4c`, replayed payload bytes, page-root object roots, published
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
  current page-root flags word `+0x14` bit 0 all skip `0xe4f4` and publish
  the base page without overlay replay.
- These are output-affecting parser/page boundaries, not hardware boundaries:
  they decide whether replayed bytes mutate the current page root before
  publication.

Unresolved middle edges:

- No ROM-local middle edge is currently unresolved for the documented minimal
  `!\r` overlay publication path from selector `4` through `0xff1e`, `0xe4f4`,
  `0xa904`, `0x11774`, `0xd04a`, `0xf02c`, `0xe22c`, `0x1ed84`, `0x1edc6`,
  and `0x1ef6a`.
- For overlay variants, the remaining unresolved edges are the same bounded
  command-family edges documented in their primary command sections. The
  overlay-specific boundary is only the replay frame:
  `0xe4f4 -> 0xa904 -> 0x11774 -> 0xe22c`.

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
  `generated/analysis/ic30_ic13_tokenizer_macro_callers.md`, plus
  `generated/analysis/ic30_ic13_renderer_fixture_harness.md`.

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
- With initialized `LINE_PRINTER` HMI, the object is the same two-entry short
  compact object documented by the direct printable walkthrough:

```text
00 00 00 00 00 00 00 02 20 00 01 20 02 02
```

  The transparent reader owns only the delayed count, payload fetch, and route
  decisions. Once both bytes have routed to `0xd04a`, object fields
  `+0x04 = 0`, `+0x05 = 0`, `+0x06 = 2`, glyph bytes `0x20/0x20`, and
  compact coordinates `0x0001/0x0202` are produced by the normal text source
  and compact-bucket path.
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
  `generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst`,
  plus `generated/analysis/ic30_ic13_renderer_fixture_harness.md`.

## Minimal Secondary Segment-57 Boundary Walkthrough

This is the top-level path for the remaining pixel-affecting external resource
boundary. It is not a transparent-parser, page-record, bridge, or compact-render
dispatch gap. The ROM-local path reaches a concrete segmented glyph source
range, and the unresolved input is the physical resource-window decode after the
verified IC32/IC15 resource pair ends.

Boundary stream:

```text
SO ESC &p3X ! 80 !
```

Parser, selection, and page-object path:

- SO byte `0x0e` reaches handler `0xc6b8`, selects secondary text slot `1`, and
  installs secondary context `0xc00ae122` in the page root through
  `0xc428(1)` / `0xc4fc`.
- `ESC &p3X` reaches arming handler `0x11f5a`, which schedules transparent
  payload reader `0x12452` through delayed path `0x121cc` / `0x12218`.
- Restored transparent record `80 58 00 03 00 00` gives payload bytes
  `21 80 21`. With secondary filtering active, all three route to `0xd04a`.
- The two `!` bytes read secondary context `0xc00ae122`, map to glyph `0`, and
  queue short selector-1 entries. Payload byte `0x80` maps to glyph `0x5f`.
- The high-control byte queues segmented compact objects with selector
  `0x2001`; the bridged render context slots are `(0x440946b4, 0xc00ae122)`.

Resolved renderer source:

- `0x1f354` uses the bit-30 offset-table form for secondary context
  `0xc00ae122`.
- For secondary `LINE_PRINTER`, table index `0x5f` has relative offset `0`, so
  the glyph entry resolves to record header file offset `0x02e122`.
- The interpreted glyph entry has bitmap delta `0`, mode `0`, rows `20062`,
  width `74`, and render span `10`.
- Segmented renderer `0x1f1f0` applies segment `0x39` as row skip `7296`,
  clamps the selected segment to `0x80` rows, and advances source A2 to file
  offset `0x03fe22`.
- File offset `0x03fe22` maps to firmware source address `0x0bfe22`. The row
  source needs bytes through firmware address `0x0c0321`.

Exact boundary:

- Required source range:
  `0x0bfe22..0x0c0321`.
- Verified IC32/IC15 suffix:
  `0x0bfe22..0x0bffff`, `478` bytes, digest
  `e0a0fd34ce7a39f79ecd27c0ee288631554a0ff78359b72e27ea6087651bcf1f`.
- Unverified continuation:
  `0x0c0000..0x0c0321`, `802` bytes. This range is beyond the verified
  `0x40000`-byte resource-pair image.
- Mirror, code-pair continuation, and zero-fill policies all produce the same
  current-band digest
  `f0c1127f9e6b203f9829ab43f159b89c3f7dda687a47d4c09971077eac55c96e`, but
  diverge in fallback rows after the verified suffix.

State classification:

- Canonical:
  secondary selected context `0xc00ae122`, secondary map `0x783032`, routed
  transparent payload bytes, selector-`0x2001` compact segment objects, glyph
  `0x5f`, segment `0x39`, render-record context slots, and verified resource
  suffix bytes `0x0bfe22..0x0bffff`.
- Derived/cache:
  local transparent filtering word, row skip `7296`, selected bucket sequence,
  glyph-entry interpretation, source file offset `0x03fe22`, firmware source
  address `0x0bfe22`, suffix digest, continuation candidate hashes, and
  current/fallback row digests.
- Parser scratch:
  restored transparent command record `80 58 00 03 00 00`, delayed handler
  fields `0x782a1a/0x782a1c/0x782a20..0x782a25`, payload count, and transparent
  reader cursor.
- Firmware bookkeeping:
  page-root font-slot install state, stream allocator state, publication flag
  `0x782996`, render-work progress, startup scanner counts used to constrain
  continuation hypotheses, and probe-script hash bookkeeping.
- Hardware/external:
  physical ROM/resource decode for firmware address `0x0c0000..0x0c0321`.
- Unknown:
  the exact byte source for `0x0c0000..0x0c0321`. Closing this boundary requires
  static board, emulator, or gate-array memory-map evidence. ROM/disassembly
  evidence can document the candidate continuation policies, but cannot select
  the physical byte source.

Evidence:

- Checked-in explanations:
  `Boundary: Secondary Segment-57 Source` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md),
  [transparent-print-data.md](transparent-print-data.md),
  [resource-rom.md](resource-rom.md#resource-rom-outcome-matrix),
  [built-in-resource-scan.md](built-in-resource-scan.md),
  [formatter-interface-pca.md](formatter-interface-pca.md), and
  [rom-dump-manifest.md](rom-dump-manifest.md).
- Reproduction probe:
  `tools/probe_resource_window.py --quiet`.
- Focused listings and extracts:
  `generated/disasm/ic30_ic13_transparent_data_handler_011f5a.lst`,
  `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`,
  `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`,
  `generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst`,
  `generated/disasm/ic30_ic13_font_resource_scan_01a2e4.lst`, and
  `generated/disasm/ic30_ic13_cart_resource_scan_0003e8.lst`.

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
- For the documented default-filter stream, the entry-producing loop values
  are `0x21`, `0x21`, and terminating `0x5a`. They queue glyph bytes `0x20`,
  `0x20`, and `0x59` at compact coordinates `0x0001`, `0x0403`, and
  `0x0405`. The intervening `0x05` and terminating `ESC` bytes route through
  `0xd0f0`: they advance cursor state but do not append compact glyph entries
  in the pinned built-in source path. The checked-in owner note records the
  same route as `d04a d0f0 d04a d0f0 d04a`.
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
  `generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst`,
  plus `generated/analysis/ic30_ic13_renderer_fixture_harness.md`.

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
- The payload bytes are installed as table data only for accepted even counts
  within the current VFC table window. Odd counts and counts beyond
  `2 * (0x782ede + 1)` are drained through `0xdace` without table writes;
  accepted counts write at most `0x100` bytes and drain any excess.
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
- The following printable uses the ordinary single-entry short compact object
  shape. For the line-1 channel jump, the payload entry is glyph `0x20` at
  coordinate `0xb001`, so the queued object prefix is:

```text
00 00 00 00 00 00 00 01 20 b0 01
```

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
- The pre-VFC and post-VFC printables are separate page-root objects on the
  publishing paths. The pre-VFC compact object is preserved in the old
  published root, while the post-VFC fresh-root object uses the same short
  shape with payload entry glyph `0x20` at compact coordinate `0x9001`.
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
  parser record cursor `0x78299e`, delayed-payload fields `0x782a1a` /
  `0x782a1c` / `0x782a20..0x782a25`, current downloaded-font id
  `0x782f2e`, current character `0x782f30`, current downloaded-font records
  `0x782640..0x782776`, current-record flag bit `6`, installed
  glyph-table entry `0x00de`, glyph record bytes, current page root
  `0x78297a`, compact bucket objects, published source record, and
  render-record bucket/context roots.
- Derived/cache:
  payload byte budget `0x783140`, parsed span `0x7827c2`, parsed row count
  `0x7827c4`, bitmap byte count `0x7827be`, compact selector `0x3003`,
  segment numbers, bucket indices, and render-band fields.
- Parser scratch:
  staged descriptor scratch `0x7827de..0x7827e9` and continuation fields
  `0x7827c6..0x7827da`.
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

## Minimal Downloaded Glyph Boundary Walkthrough

This section separates the solved downloaded-glyph path above from the remaining
ROM-local helper boundaries. All four boundaries start from the same broad
install-to-print pipeline:

```text
ESC )s#W <downloaded-glyph payload> printable FF
```

Shared path before divergence:

- Host bytes enter through `0xa904`, parser loop `0x11774`, delayed-payload
  setup `0x121cc`, and delayed restore `0x12218`.
- Downloaded-character handler `0x16c14` consumes the restored `ESC )s#W`
  record, drives payload readers such as `0x16942`, and installs completed
  glyph records through `0x16498` when the payload reaches a legal complete
  object.
- A later printable byte reaches `0xd04a`; source production through
  `0xd824 -> 0x12f2e` exposes low row or width bytes to compact page-object
  selection.
- Publication and render use the normal page path:
  `0xff1e -> 0x1ed84 -> 0x1edc6 -> 0x1ef6a -> 0x1effe`.

Boundary classes:

- Short compact high rows:
  installed row words `0x0101..0x0103` are preserved by `0x16498`, but the
  printable source exposes low row bytes `0x01..0x03` to `0x12f2e`. The producer
  therefore queues selector `0x0003` under bucket `1`. `0x1f414` can split row
  `0x0102` into `58` current-band rows and fallback count `200`; helper
  `0x1fe76` only has valid row-count entries through index `128`. The exact
  boundary is unchecked table read `0x1fe8a + 4 * D3`, where index `200` reads
  row-copy code bytes `32 9a d3 c0` as target `0x329ad3c0`.
- Wrapped width low bytes:
  `0x16498` preserves installed width words, but unflagged printable sources
  expose only width byte `+0` to `0x12f2e`. Source width bytes `0x11..0xff`
  select wide compact helper `0x1f0d2`; wrapped bytes `0x00..0x10` select
  compact mode-0 helper `0x1f034` with full-span table indexes. Span `0x0102`
  indexes `0x1f08e + 0x0408 = 0x1f496`, reads bytes `00 00 66 cc`, and jumps to
  unrelated firmware at `0x0066cc` rather than a decoded row-copy helper.
- Segmented-wide fallback source:
  row words above `0x00ff` can still produce selector `0x3003` when the low row
  byte selects segmented-wide output. Buckets `8` and `0` preserve segments
  `1` and `0`; bucket `8` dispatches through `0x1f264`. Successful neighboring
  spans `17`, `18`, and `32` render selected segment `1` with a `32/96`
  current/fallback split. Span `31` follows the same parser, install,
  publication, bridge, and renderer path, but the fallback row-copy source read
  reaches modeled A2 offset `+0xb50`; that is the exact source-boundary stop.
- Payload count cap:
  segmented-wide high-row streams whose required bitmap bytes exceed the
  restored `ESC )s#W` count cap stop before installation. The parser count cap
  is `0x7fff`; with minimum segmented-wide span `17`, the last possible row word
  is `floor(0x7fff / 17) = 0x0787`. The adjacent `0x0788 * 17` case requires
  `0x7ff8` bytes, so it stops inside the delayed payload before `0x16498`,
  before any selector-`0x3003` page object, and before renderer `0x1f264`.

State classification:

- Canonical:
  installed downloaded glyph records and bitmap payload bytes for below-cap
  completed installs; current page root `0x78297a`; selector `0x0003`,
  `0x1003`, or `0x3003` compact bucket objects; published page/control record;
  render-record bucket roots.
- Derived/cache:
  source low row byte, source low width byte, row/span product, bucket number,
  segment number, `0x1f414` current/fallback split, row-copy table target,
  invalid compact-mode target, A2/A3 source offsets, and parser-cap maximum row
  `0x0787`.
- Parser scratch:
  delayed `ESC )s#W` command records, payload budget `0x783140`, delayed handler
  fields `0x782a1a/0x782a1c/0x782a20..0x782a25`, parser stop offset, and next
  printable handler state when the stream completes.
- Firmware bookkeeping:
  downloaded-record allocation/release around `0x16c14` / `0x16498`,
  continuation fields for partial payload copies, stream allocator state,
  publication flag `0x782996`, and render-work progress.
- Hardware/external:
  none for these four ROM-local helper boundaries.
- Unknown:
  no unresolved parser, install, publication, bridge, or renderer-dispatch edge
  remains for the named boundary streams. The remaining unknowns are the exact
  execution contract after computed jumps into non-row-copy code or source reads
  beyond the modeled installed bitmap, and broader byte streams that avoid the
  documented stops by changing row count, width, span, or payload length.

Evidence:

- Checked-in explanations: `Boundary: Short Compact Downloaded-Glyph High Rows`,
  `Boundary: Downloaded-Glyph Wrapped Width Low Bytes`, `Boundary: Segmented-Wide
  Downloaded-Glyph Fallback Source`, and `Boundary: Downloaded-Glyph Payload Count Cap`
  in [firmware-dataflow-model.md](firmware-dataflow-model.md), `Downloaded-Glyph Render
  Decision Checkpoint` in
  [downloaded-fonts.md](downloaded-fonts.md#downloaded-glyph-render-decision-checkpoint),
  `Downloaded Glyph Renderer Boundary State` in
  [semantic-state-model.md](semantic-state-model.md), and compact row-copy sections in
  [page-raster-imaging.md](page-raster-imaging.md).
- Focused listings:
  `generated/disasm/ic30_ic13_font_resource_object_add_016c14.lst`,
  `generated/disasm/ic30_ic13_font_payload_readers_016880.lst`,
  `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`,
  `generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst`,
  `generated/disasm/ic30_ic13_bitmap_row_copy_tables_01fa5c.lst`,
  `generated/disasm/ic30_ic13_glyph_row_copy_helper_02f27c.lst`, and
  `generated/disasm/ic30_ic13_invalid_compact_mode0_target_0066c0.lst`.

## Current Residual Edge Index

Use this index before opening a new trace window. The supported stream
families below already have checked-in parser, state, page-object, bridge, and
render documentation, and the address-level cluster map in
`Supported Stream Entry Points` names the owner route for each current
supported family. New work should start from one of these exact residual edges
or from a byte stream that changes a named field in the family sections.

- Pixel-affecting resource data:
  `Boundary: Secondary Segment-57 Source` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md) is the only current
  documented byte-to-bitmap edge whose rows depend on unknown external
  firmware-address data. The ROM path is traced through transparent payload
  reader `0x12452`, printable/source object production, compact segmented
  objects, bridge `0x1ed84` / `0x1edc6`, and compact renderer
  `0x1f354 -> 0x1f1f0`. The remaining input is resource-window data for
  firmware range `0x0c0000..0x0c0321` after verified bytes
  `0x0bfe22..0x0bffff`. The exact checked-in stop is
  [Secondary Segment-57 Resource
  Source](unresolved-boundaries.md#secondary-segment-57-resource-source):
  `tools/probe_resource_window.py --quiet` verifies the `478`-byte suffix,
  `802`-byte continuation requirement, and mirror/code-pair/zero-fill
  candidate-scan consequences, so the remaining evidence needed is the
  physical decode source for that continuation range.
- ROM-local downloaded-glyph renderer/payload boundaries:
  `Boundary: Short Compact Downloaded-Glyph High Rows` documents the unchecked
  `0x1fe76` fallback row-copy table read for short compact rows
  `0x0101..0x0103`; valid entries end at index `128`, while fallback counts
  `199..201` read code bytes as target pointers, with row `0x0102` reaching
  `0x329ad3c0`. `Boundary: Downloaded-Glyph Wrapped Width Low Bytes`
  documents the low-byte width truncation that can send preserved installed
  spans through compact mode-0 invalid targets such as `0x0102 -> 0x0066cc`.
  `Boundary: Segmented-Wide Downloaded-Glyph Fallback Source` documents the
  span-31 fallback A2 source-read boundary at offset `+0xb50` after
  `0x1f264` selected-segment dispatch. `Boundary: Downloaded-Glyph Payload
  Count Cap` documents the parser/payload sibling: oversized segmented-wide
  high-row streams exceed the restored `ESC )s#W` count cap `0x7fff`, so they
  stop before installed-glyph publication or render dispatch. These are
  ROM-local byte-to-output boundaries, not page-object publication or bridge
  gaps.
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
  bridge roots, render dispatch, or helper row construction. For page-object
  variants, compare the stream against `Page Object Shape Route Index` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md#page-object-shape-route-index)
  and name the changed producer, root field, canonical object bytes, bridge
  field, first render consumer, or exact residual boundary. For scheduler-only
  variants, compare the stream against `Band Scheduling Route Index` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md#band-scheduling-route-index)
  and name the changed publication field, source selector, work record, band
  word, no-pixel exit, or capacity-approved `0x1ef6a` call.
- Checked-in documentation requirement:
  generated reports and fixtures can support the items above, but completion
  for any new edge means updating the relevant checked-in note with writers,
  readers/consumers, field classification, output effect, evidence, and exact
  unresolved boundary.

## Supported Stream Entry Points

Use this index when starting from a concrete byte stream. Each entry points to
the checked-in note that carries the parser route, state fields, page/render
objects, fixtures, evidence, and unresolved boundaries for that stream family:

Address-level cluster map:

- Printable text cluster:
  `0xa904 -> 0xda9a -> 0x11774 -> 0xd04a -> 0x1393a ->
  0x12f2e -> 0x1387c -> 0xff1e -> 0x1ed84 -> 0x1edc6 ->
  0x1ef6a -> 0x1effe`. Owner notes are
  [font-context-metrics.md](font-context-metrics.md),
  [page-record-storage.md](page-record-storage.md), and
  [page-raster-imaging.md](page-raster-imaging.md). Normal unmatched
  mode-zero printable bytes reach `0xd04a` only when alternate/data mode
  `0x782c18` is clear. `0xd04a` builds source object `0x782d7e` through
  `0x1393a`, using selected slot `0x782f06`, current context
  `0x782ee6` / `0x782ef6`, and active map `0x782f32` / `0x783032`.
  `0xd824` positions the source from cursor/page geometry, marks the
  page-root font slot live at `0x78297f + slot`, and `0x12f2e -> 0x1387c`
  queues compact bucket objects under root `+0x1c`. Publication and pixels
  require `0xff1e`, bridge `0x1ed84 -> 0x1edc6`, band dispatch `0x1ef6a`,
  compact dispatcher `0x1efc2 -> 0x1effe`, glyph resolver `0x1f354`, and the
  selected row-copy helper. The supported stream residual is any later byte
  stream that changes selected context/map, source class, compact selector
  shape, bridge context roots, or compact row-copy helper input.
  Concrete printable streams are now part of the route index. For `!`, byte
  `0x21` is fetched through `0xa904`, reaches `0xd04a` as an unmatched
  mode-zero byte, maps through `0x1393a` under built-in `LINE_PRINTER` to
  glyph `0x20`, glyph entry `0x015330`, source flag `1`, positioned source
  x `16`, y `0`, and context slot `0`. `0x12f2e -> 0x1387c` queues short
  compact object `00 00 00 00 00 00 00 01 20 00 01` under page-root `+0x1c`.
  Publication copies it through `0xff1e -> 0x1ed84 -> 0x1edc6`; render
  dispatch `0x1ef6a -> 0x1efc2 -> 0x1effe` selects `0x1f034`, resolver
  `0x1f354`, and row-copy helper `0x01fa5c`. For `!!`, the same
  `LINE_PRINTER` HMI and cursor advance place the second glyph at compact
  coordinate `0x0202` in the same compact object family. The unflagged
  sibling in `Built-in and downloaded compact text rendering` maps host
  `0x21` to glyph `0x01`, fixed record `02 03 04 00 00 00 00 80`,
  source x `22`, y `22`, slot `3`, and the same
  `0x12f2e -> 0x1387c -> 0x1effe` pipeline. Evidence is
  `Worked Path: Printable Glyph` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md), the concrete
  two-printable-byte route in [pcl-command-map.md](pcl-command-map.md), and
  the text renderer section of [page-raster-imaging.md](page-raster-imaging.md).
  Printable text state classification: canonical parser/text state is the
  mode-zero printable byte in `D5`, selected slot `0x782f06`, current-font
  records `0x782ee6` / `0x782ef6`, active maps `0x782f32` / `0x783032`, and
  source object `0x782d7e` fields `+0x00`, `+0x04`, `+0x08`, `+0x0a`,
  `+0x10`, `+0x12`, `+0x14`, and `+0x16` written by `0x1393a`, `0xd3b2`,
  and `0xd824`. Canonical page/image state is current root `0x78297a`,
  page-root slot `0x78297e`, live-font byte `0x78297f + slot`, compact bucket
  root `+0x1c`, bucket object links, selector/class byte `+0x04`, entry count
  `+0x06`, and compact payload entries written by `0x12f2e -> 0x1387c`.
  Derived/cache state is HMI and previous-width placement state `0x78315c` /
  `0x782a58..0x782a5c`, bucket index `0x782a7c`, compact coordinate words,
  selector bits for context, width, and tall rows, plus render roots and band
  fields after `0x1edc6`. Parser scratch is the transient printable byte,
  high-bit normalization and `0xd99a` reporting, plus high-character flags
  `0x783132/0x783133` while `0xd04a` decides whether to mask before
  `0x1393a`. Firmware bookkeeping is text queue precheck result `0x782a6e`,
  pending span state `0x783184..0x78318a`, page-root retry bit `+0x14.0`,
  stream allocator fields `0x782a70/0x782a72/0x782a76`, publication flag
  `0x782996`, and the compact render phase/cache fields used by `0x1effe` /
  `0x1f354`. Hardware state is not a printable-cluster input after `0xa904`
  has supplied the byte; later physical output timing starts only after the
  ROM-derived render rows have been written.
- Direct control and placement cluster:
  parser rows dispatch CR/LF/FF/HT/BS/SO/SI to `0xf02c`, `0xf08c`,
  `0xf0f0`, `0xf1cc`, `0xf2a8`, `0xc6b8`, and `0xc68a`; cursor and margin
  commands dispatch to `0xeb58`, `0xec0c`, `0xf39e`, `0xf416`, `0xf48c`,
  `0xf560`, `0xf60a`, and `0xf692`. Owner note is
  [direct-control-codes.md](direct-control-codes.md); selected slot handoff
  is composed in
  [Selected Context Switch
  Checkpoint](direct-control-codes.md#selected-context-switch-checkpoint).
  The output edge is usually delayed until later printable text, span flush
  `0xf34a -> 0x12714`, or publication `0xff1e` consumes the changed
  cursor/layout state.
  `ESC &k#G` writes line-termination byte `0x78318f` through `0xedf8`; CR,
  LF, and FF consume its bits through `0xf02c`, `0xf08c`, and `0xf0f0`.
  CR `0xf02c` runs `0xf06e` to copy left margin `0x782dd6` into cursor x
  `0x782c8a`, flushes pending span state through `0xf34a`, and optionally
  calls LF helper `0xf0b2` when `0x78318f.7` is set. LF `0xf08c` optionally
  performs the same CR-style x reset when `0x78318f.6` is set, always flushes
  through `0xf34a`, and advances cursor y `0x782c8e` by VMI `0x783160`
  through `0xf0b2`, including vertical overflow/perforation check `0xf36c`.
  FF `0xf0f0` optionally resets x when `0x78318f.5` is set, flushes spans,
  ensures a page root, and calls page-eject helper `0xf124 -> 0xff1e`, then
  marks pending page-eject byte `0x782a6d = 0xff`. HT `0xf1cc` converts HMI
  `0x78315c` through `0x104fe`, advances to the next eight-column stop from
  left margin `0x782dd6`, clamps against right margin `0x782dda` or page
  width `0x782db8`, and writes cursor x `0x782c8a`. BS `0xf2a8` ensures a
  page root, subtracts HMI or previous-width state, clamps at the left margin,
  writes cursor x, and sets previous-width latch `0x782a58`. HMI
  `ESC &k#H` writes `0x78315c`; wrap `ESC &s#C` writes `0x783190`; cursor
  stack `ESC &f#S` saves/restores cursor fields. Cursor/margin commands write
  canonical placement fields `0x782c8a`, `0x782c8e`, `0x782dd6`, and
  `0x782dda` through `0xf4ca` / `0xf6e2`. Cursor-changing commands can flush
  pending span state through `0xf34a -> 0x12714` before writing the new cursor;
  the following printable byte then consumes the changed state through the
  printable cluster. `ESC 9` reaches `0xe9ba`, clears left margin
  `0x782dd6`, copies page width `0x782db8` to right margin `0x782dda`, and
  affects output only when later CR/HT/text/graphics consume those limits.
  `ESC =` reaches `0xf176`, ensures a page root, flushes pending span state,
  advances cursor y `0x782c8e` by half of VMI `0x783160`, and reuses the
  LF/perforation overflow path. `ESC &a#L/#M` route to `0xeb58` / `0xec0c`:
  left margin converts columns through HMI `0x78315c`, writes `0x782dd6`, and
  may move cursor x; right margin converts `abs(parameter) + 1`, writes
  `0x782dda`, sets latch `0x782a57`, and may clamp cursor x left. `ESC
  &a#C/#H` route to `0xf39e` / `0xf416` and commit x through `0xf4ca`;
  `ESC &a#R/#V` route to `0xf560` / `0xf60a` and commit y through `0xf6e2`.
  Dot-position `ESC *p#X/#Y` route to `0xf48c` / `0xf692`, shift parsed
  whole-dot values into packed coordinates, and share the same commit helpers.
  These placement commands draw only through following printable, raster-start,
  rectangle/rule, VFC, or publication consumers of the committed cursor fields.
  Underline/text-attribute command `ESC &d...` reaches tokenizer/handler
  `0x12622`: selector stream `ESC &d3D` writes underline/span selector
  `0x783185 = 1` and re-arms pending span state through `0x126e2`, while
  following printable text updates pending span fields `0x783184`,
  `0x783186`, `0x783188`, and `0x78318a` through metric consumers
  `0xd4ac` / `0xd8fc`. A later `ESC &d@`, CR, left-margin change, or vertical
  cursor change can flush that pending block through `0xf34a -> 0x12714 ->
  0x126e2`, materializing selector-`0x4000` segment-list objects under
  page-root `+0x1c`; publication then bridges them through `0x1edc6` and
  segment-list renderer `0x1f812`.
  Concrete direct-control and layout streams are now part of the route index.
  `ESC &k1G!\r!` reaches `0xedf8`, `0xd04a`, `0xf02c`, and `0xd04a`;
  mode byte `0x80` makes CR apply CR+LF, and the second glyph queues in
  compact bucket `0` at coordinate `0x3b00`. Siblings `ESC &k2G!\n!` and
  `ESC &k0G HT BS !` route through `0xf08c` and `0xf1cc` / `0xf2a8`,
  queueing post-control compact coordinates `0x3b00` and `0x0a01`.
  Placement streams `ESC &a2C!`, `ESC &a1R!`, `ESC &a2c+1R!`, and
  `ESC *p30x30Y!` commit cursor state through `0xf4ca` / `0xf6e2` before
  the following printable queues compact coordinates `0x0a02`, `0x1001`,
  `0x1a02`, and `0x9402`. Layout streams share the same delayed-output
  rule: `ESC &l66P !` writes page-length state through `0xf9e8` and the
  following printable queues glyph `0x20` at `0x9001`; `ESC &l3E !` updates
  top-margin state through `0xece2` before the following printable also
  queues at `0x9001`; and `ESC &l1L !` writes perforation byte `0x783191`
  through `0xee64` before the ordinary printable path queues the visible
  object. Wrap streams `ESC &s0C ...` and `ESC &s1C ...` write or clear wrap
  byte `0x783190` through `0xedb0`; the visible effect is deferred until
  printable prechecks `0xd28a` / `0xd6bc` see horizontal overflow. With wrap
  clear, the precheck returns rejection before `0x12f2e`; with wrap set, it
  calls recovery helper `0xf054` and can continue into ordinary compact-object
  queueing when the recovered placement fits. Span-flush stream `ESC &a6L!`
  materializes selector-`0x4000` segment-list object
  `00 00 00 00 40 00 00 01 32 00 03 00 00 10` through
  `0xf34a -> 0x12714`, then re-arms span state for the following printable at
  compact coordinate `0x0207`. Evidence is
  [direct-control-codes.md](direct-control-codes.md) and
  [pcl-command-map.md](pcl-command-map.md#supported-stream-dispatch-matrix).
  Direct-control state classification: canonical placement state is cursor
  `0x782c8a/0x782c8e`, margins `0x782dd6/0x782dda`, HMI/VMI
  `0x78315c/0x783160`, page width/bounds state consumed by cursor clamps, and
  current page root `0x78297a`. Canonical control/layout modes are
  line-termination byte `0x78318f`, wrap byte `0x783190`, perforation-skip
  byte `0x783191`, page-eject pending byte `0x782a6d`, and page-length or
  top/text-bottom fields consumed by `0xf36c`, VFC, printable placement, and
  publication. Canonical stack/span state is cursor stack
  `0x782c96..0x782d36`, stack pointer `0x782d36`, pending span fields
  `0x783184..0x78318a`, and selector-`0x4000` span objects produced by
  `0xf34a -> 0x12714`. Derived/cache state is source scratch `0x782d7e`,
  compact coordinates created by the following printable path, tab-stop and
  decipoint conversions through `0x104fe` / `0x10518`, and queue/render keys
  for span objects after `0x12714`. Parser scratch is the admitted direct
  control byte or six-byte parsed command record at `0x78299e`; direct
  controls themselves do not become page objects unless a span flush or page
  publication path consumes their state. Firmware bookkeeping is right-limit
  latch `0x782a57`, previous-width latch and words `0x782a58..0x782a5c`,
  text queue precheck/wrap result `0x782a6e`, retry/finalization bit
  `+0x14.0`, and publication flag `0x782996`. Hardware state is outside this
  cluster after parser dispatch; physical timing starts only after later
  publication/render code consumes the page objects created from the mutated
  cursor, span, or layout state.
- Page geometry cluster:
  page-size and orientation commands dispatch through
  `0x11774 -> 0xfc74` and `0x11774 -> 0x10220`; page-length/default-page
  commands dispatch through `0x11774 -> 0xf9e8`. Owner notes are
  [page-raster-imaging.md](page-raster-imaging.md),
  [publication-commands.md](publication-commands.md), and
  [pcl-command-map.md](pcl-command-map.md). These commands normally do not
  queue pixels directly. They write canonical geometry state consumed by later
  printable placement, VFC/perforation movement, raster bounds, rectangle
  clipping, page publication, and render scheduling. `ESC &l1A` reaches
  `0xfc74`, maps PCL page size `1` to internal code `6`, writes page code
  `0x782da2`, rebuilds active size `3030 x 2025`, top offset `90`, printable
  extent `3090`, and half-page remainder `0x782dc0 = 11`. `ESC &l1O`
  reaches `0x10220`, writes orientation byte `0x782da3 = 1`, swaps active
  extents to `2025 x 3030`, selects landscape margin `2175`, printable
  extent `2125`, top offset `100`, and threshold sequence
  `2175, 2550, 2480, 2550`. Chained `ESC &l1a1O` stays in the `&l` parser
  family, runs `0xfc74` for lowercase final `a`, then runs `0x10220` for
  uppercase final `O` with the same final landscape state. When content is
  already queued, `! ESC &l1A` and `! ESC &l1O` publish the pre-geometry
  compact object `00 00 00 00 00 00 00 01 20 00 01` through
  `0xf34a -> 0xff1e` before page code or orientation is changed, so those
  rows render under the old geometry. Nonzero `ESC &l66P !` uses VMI
  `0x783160` in `0xf9e8`, writes page extent `0x782dba = 3300`, selects
  internal code `2`, refreshes top offset `90`, and the following printable
  queues compact coordinate `0x9001`. Zero `ESC &l0P` takes the default-page
  branch, can publish pending text, selects fallback page code `2`, writes
  text bottom `3240`, mirrors `0x780e8f = 0x80`, and signals
  `0x780e26 = 1`. Evidence is `Minimal Page Geometry Walkthrough` above,
  [page-raster-imaging.md](page-raster-imaging.md), and
  [publication-commands.md](publication-commands.md).
  Page-geometry state classification: canonical geometry state is page code
  `0x782da2`, orientation byte `0x782da3`, page extent `0x782dba`, active
  extents `0x782db6/0x782db8`, margins `0x782dd6/0x782dda`, top offset
  `0x782dce`, VMI/HMI `0x783160/0x78315c`, cursor `0x782c8a/0x782c8e`, and
  text/perforation limits `0x782dd2/0x782dc2`. Canonical page/publication
  state is current root `0x78297a`, pending geometry header flag `0x782997`,
  publication flag `0x782996`, paper-source output bytes `0x780e8f` /
  `0x780e26` on the `ESC &l0P` default branch, and any pre-geometry page
  object published through `0xff1e`. Derived/cache state is table geometry
  words `0x782db2/0x782db4`, phase word `0x782dc0`, line caches
  `0x782ede..0x782ee0`, default VFC table state, compact coordinates created
  by later printable bytes, raster row limits, rectangle clipping extents, and
  render-band fields after publication. Parser scratch is the six-byte
  command record rewound and consumed by `0xfc74`, `0xf9e8`, or `0x10220`;
  same-family chaining such as `ESC &l1a1O` only preserves parser context until
  the next final consumes it. Firmware bookkeeping is modified-layout byte
  `0x782ee1`, pending cursor/text latch `0x782a6d`, overlay/parser mode byte
  `0x782a92` cleared by page-length refresh unless it is selector `2`, and
  allocator/scheduler progress after a publication. Hardware/external state is
  limited to the paper-source output/control mirror in the default-page branch
  and later formatter timing; page-size, orientation, and nonzero page-length
  fields are ROM-local inputs to later page-object construction.
- Parser artifact and no-output cluster:
  explicit zero-handler rows, unmatched command forms, alternate/data appends,
  no-byte service returns, callback continuations, and delayed restore paths
  stay in `0x11774`, `0x117d2..0x11818`, `0x118b2..0x11900`,
  `0x11930..0x11ab8`, `0x119a6..0x119f4`, `0x11b32..0x11b8a`, `0x12218`,
  `0x1228a`, `0x12328`, `0x12358`, normal table `0x112a4`, and alternate
  table `0x116f6`. Owners are
  [pcl-parser-core.md](pcl-parser-core.md) and
  [pcl-command-map.md](pcl-command-map.md), with
  `Minimal Generic Counted Payload Drain Walkthrough` covering the no-output
  `W/w` wrapper path. The residual is a new table row or delayed-restore
  branch that changes saved parser record state or reaches a page-object
  owner. Normal zero-handler rows `0x00`, `0x07`, and `0x0b` match explicit
  table entries, run terminal cleanup through `0x119a6..0x119f4`, call
  delayed restore `0x12218`, reset parser scratch, and do not fall through to
  printable or direct-control handlers. Alternate/data blank C0 rows
  `0x00` and `0x07..0x0f` append through `0xe002` before cleanup, so they can
  become visible only if later macro/data-chain replay feeds them back through
  `0xa904`. `ESC ?` is consumed by the `0xda9a` ESC-aware wrapper, `ESC Z` is
  local to display-functions readers, and `ESC &lT/t` has no page-output
  handler. No-byte service path `0x117d2..0x11818` clears `0x780e3b`, services
  wait object `0x780202`, and can return from the parser loop when
  `0x782a92 == 0x63`. Normal mode-zero no-match path `0x118b2..0x11900`
  either sends the byte to printable `0xd04a` when selected context byte
  `0x782ee6 + 16 * 0x782f06 + 5` is `1`, or ignores the byte and fetches
  again. Alternate/data mode-zero no-match path `0x11b82..0x11b8a` appends
  the byte through `0xe002`. Nonzero-mode no-match path `0x11b32..0x11b7e`
  calls active callback pointer `0x78299a`; a mode-zero callback return clears
  parser cursors and delayed byte `0x782a1a`, while a nonzero return keeps the
  command-family mode active.
  Concrete parser-artifact streams are now part of the route index.
  Normal-mode `NUL BEL VT` enters through `0xa904 -> 0xda9a -> 0x11774`,
  matches explicit zero-handler rows for `0x00`, `0x07`, and `0x0b`, runs
  `0x119a6..0x119f4 -> 0x12218`, resets command/numeric scratch, and creates
  no page root, page object, publication, render record, or host-output FIFO
  byte. `ESC ? 11` is swallowed in wrapper `0xda9a`: after `ESC`, fetch
  `0xdaa6` sees `?`, fetch `0xdab2` consumes third byte `0x11`, and the
  wrapper resumes byte fetch without entering a command-family handler.
  `ESC Y ! ESC Z` is display-reader input, not a global `ESC Z` command:
  normal reader `0x12536` consumes the terminating pair inside its direct
  `0xa904` loop, while alternate/data reader `0x12120` appends literal
  `ESC Y` and loop bytes through `0xe002` until the same local terminator.
  In alternate/data mode, blank C0 rows `0x00` and `0x07..0x0f` take
  `0x11930..0x11ab8`, flush scratch through `0x123ae` / `0x123de`, append
  the matched byte through `0xe002`, and then rejoin the terminal reset path;
  therefore alternate/data BS/HT/LF/FF/CR/SO/SI bytes are stored input, not
  immediate cursor-control effects. `ESC &lT` is an unimplemented
  parser-table terminal with no handler; lowercase final `t` in the same
  `&l` family reaches rewind helper `0x11f4c` for chaining only. Evidence is
  [pcl-parser-core.md](pcl-parser-core.md),
  [pcl-command-map.md](pcl-command-map.md), and `Worked Path: Explicit
  No-Output Parser Rows` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md).
  Service/no-match outcomes share the same no-page-output contract unless they
  explicitly reroute to `0xd04a` or a callback owner: `0x117d2..0x11818`
  consumes the `0x780e3b` no-byte latch and wait-object service boundary,
  `0x118b2..0x11900` uses the selected-font context byte to decide
  printable-versus-ignore for unmatched normal mode-zero bytes,
  `0x11b82..0x11b8a` appends unmatched alternate/data mode-zero bytes, and
  `0x11b32..0x11b7e` delegates unmatched nonzero-mode bytes to callback
  `0x78299a`. These are parser control-flow outcomes, not hidden imaging
  commands; page/render state begins only if the branch reaches `0xd04a` or a
  downstream command-family owner.
  Parser-artifact state classification: canonical parser state is mode byte
  `0x782999`, normal versus alternate/data selector `0x782c18`, command-record
  cursor `0x78299e`, active six-byte records, delayed pending byte
  `0x782a1a`, delayed handler pointer `0x782a1c`, saved record
  `0x782a20..0x782a25`, and the selected table roots `0x112a4` or `0x116f6`.
  Canonical page/render state is intentionally absent for the documented
  normal `0x00` / `0x07` / `0x0b`, `ESC ?`, display-reader `ESC Z`, and
  `ESC &lT/t` cases: no current page root, page object, publication record,
  render record, or pixel row is created by these parser decisions. Derived
  state is limited to later replay potential for alternate/data bytes appended
  through `0xe002`; those bytes are stored input, not immediate image state.
  Parser scratch is matched-byte buffer `0x783196..0x783199`, nonnumeric
  cursor/buffer `0x782a26` / `0x782a2a..`, numeric cursor/buffer
  `0x782a3e` / `0x782a42..`, tokenizer lookahead, and alternate echo latch
  `0x782a56`. Firmware bookkeeping is callback pointer `0x78299a`, service
  path `0x117d2..0x11818`, terminal reset path `0x119a6..0x119f4`,
  no-match paths `0x118b2..0x11900` and `0x11b32..0x11b8a`, delayed restore
  boundary `0x12218`, generic drain helpers `0x1228a` / `0x12328`,
  alternate dispatcher `0x12358`, scratch flush helpers `0x123ae` /
  `0x123de`, append sink `0xe002`, pushback/log helper `0x9ec0`, and
  payload-control helper `0xd99a`. Hardware/external state is outside this
  cluster after `0xa904` admits the bytes. Unknown state remains only for
  future streams that reach a different rejecting predicate, callback owner,
  delayed consumer, append path, or status/error side channel.
- Transparent/display-reader cluster: transparent data uses `0x11f5a -> 0x121cc ->
  0x12218 -> 0x12452`; display functions use normal reader `0x12536` or alternate/data
  reader `0x12120`; Control-Z siblings use `0x120d2`, `0x1219e`, `0x1210c`, and
  `0x121b2`. Owners are [Transparent Payload Decision
  Checkpoint](transparent-print-data.md#transparent-payload-decision-checkpoint) and
  [display-functions.md](display-functions.md). The remaining pixel-affecting residual
  is not parser routing; it is the secondary segment-57 resource continuation read at
  firmware range `0x0c0000..0x0c0321`. Transparent `ESC &p#X` saves a delayed record
  through `0x121cc`; `0x12452` reopens the restored count, fetches payload bytes
  directly through `0xa904`, locally normalizes `1a 58` through `0xd99a`, and routes
  each value to printable `0xd04a` or fixed-space `0xd0f0` using
  selected-context/high-control filters. Normal `ESC Y ... ESC Z` enters `0x12536`, then
  reads directly through `0xa904` until local `ESC Z` termination; the terminating pair
  is routed before exit. Alternate/data `0x12120` appends literal `ESC Y` and normalized
  loop values through `0xe002`, creating stored input rather than immediate page
  objects. Control-Z handlers are local table consumers, not a global parser rule.
  Concrete direct-reader streams are now part of the route index. `ESC &p2X!!` restores
  record `80 58 00 02 00 00`, routes payload bytes `21 21` through `0xd04a`, queues
  compact coordinates `0x0001` and `0x0202`, and later renders through the ordinary
  compact-text path. `ESC &p4X!\x05\x85!` under default zero filters restores `80 58 00
  04 00 00`, routes `d04a d0f0 d0f0 d04a`, and queues object prefix `00 00 00 00 00 00
  00 02 20 00 01 20 06 04`; the two fixed-space routes advance cursor state without
  compact entries in the flagged built-in path. With nonzero filters, `ESC
  &p4X!\x05\x80!` routes all four payload values through `0xd04a` and queues prefix `00
  00 00 00 00 00 00 04 20 00 01 04 0d 01 7f 00 03 20 06 04`. Secondary stream `SO ESC
  &p3X!\x80!` selects slot `1`, routes all values through `0xd04a`, and the high-control
  byte creates selector-`0x2001` segmented buckets; selected bucket `0` begins `00 00 00
  00 20 01 00 01 5f 00 1c 01 00 00 00 00` before the documented source-read boundary at
  segment 57. Display stream `ESC Y!\x05! ESC Z` reaches `0x12536`, consumes values `21
  05 21 1b 5a`, routes `d04a d0f0 d04a d0f0 d04a`, and queues visible `!`, `!`, and `Z`
  at compact coordinates `0x0001`, `0x0403`, and `0x0405`. Filter-on display stream `ESC
  Y\x05\x80\x1aX! ESC Z` normalizes `1a 58` to `0x7f`, routes all six values through
  `0xd04a`, and queues object prefix `00 00 00 00 00 00 00 06 04 0b 00 7f 0e 01 7e 1f 02
  20 06 04 1a 53 05 59 06 06`. Alternate/data reader `0x12120` appends payload `21 1a 58
  1b 5a` as stored stream `1b 59 21 7f 1b 5a` through `0xe002`. Evidence is [Transparent
  Payload Decision
  Checkpoint](transparent-print-data.md#transparent-payload-decision-checkpoint),
  [display-functions.md](display-functions.md), and
  [pcl-command-map.md](pcl-command-map.md#supported-stream-dispatch-matrix).
  Transparent/display state classification: canonical transparent parser state
  is command-record count `+2`, cursor `0x78299e`, delayed pending flag
  `0x782a1a`, delayed handler pointer `0x782a1c`, and saved record
  `0x782a20..0x782a25`. Canonical text/filter state is selected slot
  `0x782f06`, C0 filter byte `0x782eea + 0x10 * slot`, fallback
  high-control filter byte `0x782efa`, high-character flags
  `0x783132/0x783133`, cursor `0x782c8a`, active context/map state, and
  page-record roots produced by `0xd04a` / `0x12f2e` / `0x1387c`.
  Canonical display-reader state is the local ESC-before-Z flag and current
  normalized loop value in `0x12536`, or append sink `0xe002` plus stored
  macro/data chunks in `0x12120`. Derived/cache state is local filter word
  `A6-2`, normalized payload value, selected-slot scale from `0x332ee`,
  source scratch `0x782d7e`, compact coordinates, and segmented bucket/render
  caches. Parser scratch is the fetched payload stream from `0xa904`, local
  transparent count, local `0x1a` probe byte, and mode-1/mode-2 dispatch rows.
  Firmware bookkeeping is `0xd99a` reporting/normalization, alternate/data
  restore redirect `0x1226e..0x1227e -> 0x12358(0x1228a)`, `0xf054` after a
  routed CR, and append-only storage through `0xe002`. Hardware/external state
  is limited to the secondary segment-57 fallback rows, where compact rendering
  needs resource bytes at `0x0c0000..0x0c0321` after the verified
  `0x0bfe22..0x0bffff` suffix.
- Host/status side-channel cluster: `ESC *r#K` and `ESC *s#^` dispatch through wrapper
  `0x12034` to `0x122be..0x12326`; host-output FIFO and status workers use `0xb0c0`,
  `0xb090`, `0xb022`, `0xae2c`, and `0xaece`. Owners are [Host/Status Side-Channel
  Decision
  Checkpoint](errors-and-status.md#hoststatus-side-channel-decision-checkpoint),
  [io-interfaces.md](io-interfaces.md), and [host-byte-fetch.md](host-byte-fetch.md).
  This cluster produces host-visible bytes, not page-image objects. `0x12034` calls
  setup helper `0x11efe` to append a synthetic six-byte record with word `+2 = 1`;
  `0x122be` rewinds parser record cursor `0x78299e`, fetches the following query byte
  through `0xda9a`, and emits literal `33440A\r\n` from `0x12280..0x12288` through
  blocking enqueue `0xb090` only for accepted query byte `0x11`. FIFO state is canonical
  host-output state at count `0x783ed2`, pointers `0x783ed4` / `0x783ed8`, and storage
  `0x783e92..0x783ed1`; worker `0xae2c` drains queued bytes according to backend
  selector `0x780e40`. Sibling status producer `0xaece` consumes pending-status fields
  `0x780e22`, `0x783e61`, `0x783e60`, `0x780e12`, `0x780e0a`, `0x780e2a`, and `0x780e90`
  to emit service/status bytes. The neighboring `ESC z` route is owned by
  [display-functions.md](display-functions.md) and
  [pcl-command-map.md](pcl-command-map.md): handler `0xcd86` tests active data-chain
  frame byte `0x782d76 + 9`, calls status helper `0x9c2c` only when that byte is zero,
  and otherwise returns without a signal. Helper `0x9c2c -> 0x9b5e` waits on
  service/status busy bit `0x780e2d.3`, sets markers `0x7821cc` and `0x7822db`, ORs bit
  `0x08` into accumulator `0x780e2a`, then clears `0x7821cc`. No FIFO/status consumer
  feeds `0xd04a`, `0xff1e`, `0x1ed84`, `0x1edc6`, or `0x1ef6a`; the pixel-reproduction
  residual is only FIFO-induced parser stall, `ESC z` service scheduling, or a modeled
  bidirectional host reacting with different later bytes, plus external
  protocol/register naming. Concrete side-channel streams are now part of the route
  index. `ESC *r1K 0x11` reaches wrapper `0x12034`, setup helper `0x11efe`, and producer
  `0x122be..0x12326`; the active record word `+2 = 1` and query byte `0x11` make the
  producer walk literal `33440A\r\n` at `0x12280..0x12288` and enqueue each byte through
  blocking FIFO helper `0xb090`. The sibling `ESC *s#^ 0x11` reaches the same wrapper
  from parser mode `6`; both commands reject other query bytes through `0x9ec0` instead
  of FIFO output. FIFO helper `0xb0c0` appends while count `0x783ed2 < 0x40`, wraps
  write pointer `0x783ed8` across storage `0x783e92..0x783ed1`, and `0xb090` waits on
  `0x7801e2` when full. Worker `0xae2c` drains the FIFO through backend selector
  `0x780e40`: mode `0` writes through `0xaf7c` and can first emit `0xaece`
  service/status bytes, mode `1` discards queued FIFO bytes, and other nonzero modes
  send them through `0xafcc -> 0xa1d6`. Status example `0xaece` emits service byte
  `0x13` when `0x783e61` is set, and otherwise builds base-`0x30` status bytes from
  `0x780e12`, `0x780e90`, `0x780e2a`, `0x780e0a`, and reason byte `0x783e60`. Evidence
  is [Host/Status Side-Channel Decision
  Checkpoint](errors-and-status.md#hoststatus-side-channel-decision-checkpoint),
  [host-byte-fetch.md](host-byte-fetch.md), and
  [pcl-command-map.md](pcl-command-map.md#supported-stream-dispatch-matrix).
  Host/status state classification: canonical parser/backchannel state is the
  synthetic setup record from `0x12034 -> 0x11efe`, active parser cursor
  `0x78299e`, accepted query byte `0x11`, and response literal
  `33440A\r\n`. Canonical host-output state is FIFO storage
  `0x783e92..0x783ed1`, count `0x783ed2`, read pointer `0x783ed4`, write
  pointer `0x783ed8`, wait object `0x7801e2`, backend selector `0x780e40`,
  and backend-ready state consumed by `0xa1b0` / `0xa1d6`. Canonical status
  state is selected page/control bytes `+6/+7/+8`, folded status fields
  `0x780e12`, `0x780e0e`, `0x780e0a`, `0x780e1a`, accumulator `0x780e2a`,
  active service byte `0x783e61`, reason byte `0x783e60`, and bridge/status
  byte `0x780e90`. Derived/cache state is pending status count `0x780e22`,
  last accepted service/status byte `0x780e62`, host-status composition bits,
  and reason-byte folding in `0xaece`. Parser scratch is transient query/fetch
  state in `0x122be..0x12326` before the byte is accepted as `0x11` or
  reported through `0x9ec0`; these bytes do not become page/image state.
  Firmware bookkeeping is FIFO critical sections,
  blocking enqueue through `0xb090`, worker drain selection in `0xae2c`,
  `ESC z` service markers `0x7821cc` / `0x7822db`, and external protocol or
  register naming behind `0x780e40`. Hardware/external state is limited to
  physical output backend readiness and host reaction to emitted bytes; no
  status/FIFO path creates page roots, page objects, render records, or pixels
  directly.
- Font-selection cluster:
  designation streams run `0x1201e` / `0x12008 -> 0x120be -> 0x1be22 ->
  0xc580 -> 0x13eb8 -> 0x144d2 -> 0x14c64`, with final-`X` success and
  preserve-output exits through `0x17708`. Owners are
  [Symbol/Font Designation Outcome
  Matrix](symbol-set-selection.md#symbolfont-designation-outcome-matrix),
  [Font Request Outcome
  Matrix](font-context-metrics.md#font-request-outcome-matrix), and
  [built-in-resource-scan.md](built-in-resource-scan.md). Pixels appear only
  after later printable bytes consume `0x782ee6` / `0x782ef6` and
  `0x782f32` / `0x783032` through `0xd04a`. Attribute streams
  `ESC (s...T` / `ESC )s...T` write request fields through lowercase writers
  `0xc930`, `0xc89c`, `0xc6ec`, `0xc780`, `0xc840`, and final `T` writer
  `0xc7e0`; common refresh `0xc580` calls `0x13eb8`, candidate filtering,
  `0x144d2` current-context install, and `0x14c64` map rebuild. Pitch-mode
  stream `ESC &k#S/s` reaches handler `0xc390`, accepts selectors `0`, `2`,
  and `4`, rewrites synthetic pitch records for `10.0000`, `16.6600`, or
  `12.0000`, and rejoins `0xc89c -> 0xc580`; other selectors exit through
  `0xc420` without a font refresh. It draws only when later printable bytes
  consume the selected context/map through the same `0xd04a -> 0x1393a ->
  0x12f2e` path. Symbol-set
  finals through `0x120be -> 0x1be22` rewind parser record `0x78299e` and,
  for ordinary final bytes, compute requested symbol word
  `(abs(parameter) << 5) + final - 0x40`, writing slot `0` at `0x782ef4` or
  slot `1` at `0x782f04` before setting dirty flags `0x782f2c = 1` and
  `0x782f2d = 1`. Final `X` restores the previous requested word instead of
  accepting that ordinary-final computed word, sets marker `0x78287b`, calls
  font-id selector `0x17708(slot, parameter)`, and enters `0xc580` with dirty
  flag `2`; successful paths select built-in or inline/downloaded contexts,
  while non-selected exits stop before `0x14c64` and preserve prior printable
  output. Final `@` dispatches through table `0x1bde2`: `@0`, `@1`, and `@2`
  copy ROM/default or previous requested words, `@3` runs the default-font
  path, and other parameters restore the old requested word. Common refresh
  `0xc580` is the gate from request state to printable state: dirty `1` can
  call candidate refresh `0x13eb8`, dirty `2` skips that candidate refresh,
  `0x144d2` writes current contexts `0x782ee6` / `0x782ef6`, and `0x14c64`
  rebuilds maps `0x782f32` / `0x783032`. SO/SI controls `0xc6b8` / `0xc68a`
  select slot `1` or `0`, and `0xc428` installs the selected context into
  page-root slot state before later printable bytes queue context-indexed
  compact objects; the direct-control side of that handoff is the
  [Selected Context Switch
  Checkpoint](direct-control-codes.md#selected-context-switch-checkpoint).
  Concrete final-`X` stream examples are now part of the route index.
  `ESC (7X!!` reaches setup `0x1201e`, terminal `0x120be`, font-id selector
  `0x17708`, selected context `0xc0089fb0`, and compact object prefix
  `00 00 00 00 00 00 00 02 00 89 00 00 87 02`. The secondary sibling
  `ESC )8X SO !!` reaches setup `0x12008`, SO handler `0xc6b8`, selected
  context `0xc00ae122`, page-root slot `1`, and prefix
  `00 00 00 00 00 01 00 02 00 c9 00 00 cb 01`. Bit-30-clear
  inline/downloaded final-`X` streams select context `0x00000100`: primary
  `ESC (4660X!` rebuilds map `0x782f32` and queues
  `00 00 00 00 00 00 00 01 01 66 01 00 00 00`, while secondary
  `ESC )4660X SO !` rebuilds `0x783032` and queues
  `00 00 00 00 00 01 00 01 01 66 01 00 00 00`. The documented non-selected
  exits keep prior context instead of drawing from the requested font id:
  primary `ESC (7X!!` can render from prior context `0xc008004c` with prefix
  `00 00 00 00 00 00 00 02 00 6a 00 00 68 02`, and secondary
  `ESC )8X SO !!` can render from prior context `0xc40ad87a` with prefix
  `00 00 00 00 00 01 00 02 20 c9 00 20 cb 01`. Pitch-mode evidence is
  [Pitch Mode Command](font-context-metrics.md#pitch-mode-command), the
  [Font Request Outcome Matrix](font-context-metrics.md#font-request-outcome-matrix),
  and `Worked Path: Pitch Mode To Font Refresh` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md). Evidence is
  [pcl-command-map.md](pcl-command-map.md#supported-stream-dispatch-matrix)
  and the font-selection owner notes cited above.
  Font-selection state classification: canonical request/selection state is
  requested symbol words `0x782ef4/0x782f04`, selected text slot
  `0x782f06`, current-font contexts `0x782ee6/0x782ef6`, active symbol
  words `0x783144/0x783146`, active maps `0x782f32/0x783032`, page-root
  context slots under root `+0x2c..+0x68`, selected page-root slot
  `0x78297e`, compact text glyph bytes captured by later printable records,
  and render-record context slots copied by `0x1edc6`. Canonical resource
  inputs for verified built-ins are the IC32/IC15 `HEAD` records, font record
  fields consumed by `0x156de`, `0x1519a`, `0x153c6`, and `0x14398`, glyph
  table entries, and bitmap payload rows. Derived/cache state is remembered
  and fallback symbol words `0x782f08..0x782f28`, candidate pointer/count
  windows `0x782324`, `0x78278e..0x7827b8`, selected candidate slot
  `0x7828a8`, selected target `0x7828de`, selected-font snapshots
  `0x783148/0x783152`, map flags `0x783132/0x783133`, transient probe
  context `0x782992`, HMI `0x78315c`, and compact coordinates produced after
  printable consumption. Parser scratch is the synthetic slot setup record
  written by `0x1201e` or `0x12008`, mode-13 attribute records consumed by
  `0xc930`, `0xc89c`, `0xc6ec`, `0xc780`, `0xc840`, and `0xc7e0`, final byte
  and parameter words consumed by `0x1be22`, and the `0xc390` pitch-mode
  synthetic record before it rejoins `0xc89c -> 0xc580`. Firmware
  bookkeeping is dirty flags `0x782f2c/0x782f2d`, final-`X` marker
  `0x78287b`, page-root live-font flags `0x78297f..0x78298e`, transient
  full-root flag `0x78298f`, `0xc4fc` slot-scan return state, candidate
  high-bit marks, and local `0x14f16` patch cursors. Hardware/external state
  is absent for the verified built-in streams; optional cartridge or
  post-`0x0bffff` resource-window contents are external data inputs to the
  same selection/render path, not parser-dispatch gaps.
- Page/font scheduler handoff cluster:
  quiesce and resource callers reach `0x19dd2` from `0x447a`, `0x4760`,
  `0xbb16`, and `0x1a3c2`; teardown and scan paths include
  `0xc108 -> 0x19dd2 -> 0x36e4` and
  `0x1a2e4 -> 0x1a3c2 -> 0x19dd2 -> 0x1b50e`. Owner note is
  [page-font-scheduler.md](page-font-scheduler.md#page-font-scheduler-outcome-matrix),
  with the minimal path in `Minimal Page/Font Scheduler Handoff Walkthrough`.
  This cluster produces no direct pixels; residuals are physical
  optional-window contents
  `0x200000..0x3ffffe` / `0x400000..0x5ffffe` and board-level names for
  `$8000.14/.15`. Concrete scheduler exits are now part of the route index.
  Unchanged optional-window predicates run `0x19fb8(0)`, refresh through
  `0x1b04c`, and return `D7 = 1`. The status-return branch writes
  `0x780e8d`, raises mask `0x00000200` through
  `0x9bee(0x780e2e, 0x00000200)`, calls `0x19fb8(predicate)`, and returns
  `D7 = 0`. Changed-window exits call `0x1ba92`, `0x178fa`, `0x19d9c`,
  `0x1a4fa`, and `0x1a900` before returning `D7 = 1`; later pixels can
  change only when font designation, downloaded-font lookup, printable text,
  publication, or rendering consumes the changed candidate/context state.
  Page/font scheduler state classification: canonical state is the two-slot
  optional resource-window table `0x7828b6..0x7828dd`, status root
  `0x780e2e`, status predicate byte `0x780e8d`, candidate count
  `0x78278e`, and candidate-list count/window fields pruned or committed by
  `0x1ba92` and `0x1a900`. Derived/cache state is scratch pointer
  `0x782894`, optional-window scan cursor/base/limit
  `0x782884/0x78288c/0x782890`, terminal byte `0x782898`, active
  candidate-window pointers/counts `0x7827a8..0x7827b4` /
  `0x782790..0x78279c`, and caller local result word `A6-0x02` for the
  `0x1a2e4 -> 0x1b50e` font-scan path, predicate bytes
  `A6-0x29` / `A6-0x2a`, and fresh scan slots `A6-0x28..A6-0x15` and
  `A6-0x14..A6-0x01` filled by `0x1a0f2`. Parser scratch is none for this
  scheduler-local route.
  Firmware bookkeeping is current downloaded-font records
  `0x782640..0x782776`, candidate pointer-list entries `0x782324..`, dirty
  bytes `0x782f2c/0x782f2d`, return value `D7`, caller-specific quiesce/menu
  fields, and stack argument reuse for `0x19fb8`, `0x1ba92`, `0x178fa`, and
  `0x1a4fa`. Hardware/external state is the optional resource-window contents
  at `0x200000..0x3ffffe` and `0x400000..0x5ffffe`, plus the board-level
  meaning of `$8000.14` and `$8000.15`; the scheduler itself does not queue
  page objects, publish page records, call render entry, or write bitmap rows.
  Evidence is
  [page-font-scheduler.md](page-font-scheduler.md#page-font-scheduler-outcome-matrix)
  and fixtures
  `0x19dd2 optional-window change composes refresh helpers`,
  `0x19dd2 modeled unchanged and status branch exits`,
  `0x447a/0x4760 consume scheduler return differently`,
  `0xbb0a external-ready teardown ignores scheduler return`, and
  `0x1a2e4 font scan ignores scheduler return`.
- Downloaded-font cluster:
  font control uses `0x15a56`, `0x15a18`, and `0x16df6`; delayed `W`
  payloads use `0x11f96 -> 0x15d0a` for count zero and
  `0x11f96 -> 0x16c14` for nonzero counts. Installed glyphs become page
  objects only after `0x16498` and later printable dispatch through
  `0xd04a -> 0x12f2e`. Owner note is
  [downloaded-fonts.md](downloaded-fonts.md). The byte-to-pixel route is:
  `ESC *c#D/#E/#F` updates current id/character/record bookkeeping through
  `0x15a56`, `0x15a18`, and `0x16df6`; zero-count `ESC (s0W` /
  `ESC )s0W` restores through `0x121cc -> 0x12218 -> 0x15d0a` and installs or
  rejects descriptor/fixed-record state; nonzero `ESC (s#W` / `ESC )s#W`
  restores through `0x121cc -> 0x12218 -> 0x16c14`; completed character
  payloads install glyph records through `0x16498`; the following printable
  byte resolves that state through `0xd04a -> 0xd824 -> 0x12f2e -> 0x1387c`;
  publication and pixels then cross `0xff1e -> 0x1ed84 -> 0x1edc6 ->
  0x1ef6a -> 0x1effe`. Supported visible branches include short compact
  `0x1fe76`, wide compact `0x1f0d2`, segmented `0x1f1f0`, segmented-wide
  `0x1f264`, and mixed rule/raster composition with `0x1f446` / `0x1f88e`.
  The normal offset-table downloaded-glyph stream is concrete:
  host-fetched `ESC )s80W` restores record `80 57 00 50 00 00`, enters
  `0x16c14`, validates the 64-byte descriptor through `0x16fae`, allocates
  through `0x17026` / `0x1719c`, and installs class-one candidate longword
  `0x40000000`. Companion `ESC )s3W f0 f0 f0` restores record
  `80 57 00 03 00 00`, writes table entry `0x00ce`, installs glyph record
  `00 00 00 00 0c 01 00 03 00 04 00 00`, copies bitmap bytes at delta
  `0x018c`, and leaves glyph `0x21` available. The following printable `!`
  queues compact object `00 00 00 00 00 00 00 01 21 5a 00`, publishes span
  object `00 00 00 00 40 00 00 01 04 06 03 00 00 14`, and renders through the
  same `0x1ed84 -> 0x1edc6 -> 0x1ef6a` path. Evidence is
  [pcl-command-map.md](pcl-command-map.md#supported-stream-dispatch-matrix)
  and [downloaded-fonts.md](downloaded-fonts.md).
  Downloaded-font state classification: canonical command state is current
  downloaded-font id `0x782f2e`, current character word `0x782f30`,
  parser/device mode byte `0x782a92`, the current-record pool
  `0x782640..0x782776`, current-record counts `0x782782/0x782786`, record id
  `+0x00`, flags `+0x02`, and payload pointer `+0x06`. Canonical
  resource/glyph state is candidate count `0x78278e`, candidate windows
  `0x782790..0x7827b4`, installed payload headers, glyph pointer tables,
  downloaded character records, bitmap payload bytes, active glyph maps,
  continuation words `0x7827c6..0x7827da`, compact bucket objects from
  `0x12f2e`, page-root bucket chains, published bucket arrays from `0xff1e`,
  and compact selector families `0x0003`, `0x1003`, `0x2003`, and `0x3003`.
  Derived/cache state is selected-map bytes built by `0x14e24`, source
  objects from `0x1393a`, compact coordinates and segment bytes from
  `0x12f2e`, active render work words from `0x1ed84`, row chunks selected by
  compact helpers, and row/span products that feed the documented helper
  boundaries. Canonical parser state includes delayed-payload state
  `0x782a1a`, saved handler `0x782a1c`, and saved records
  `0x782a20..0x782a25`. Parser scratch is staged descriptor/header storage
  `0x7827de..0x7827e9`, staging pointer `0x782862`, optional symbol bytes
  `0x782842..0x782856`, and bitmap parse fields
  `0x7827be/0x7827c2/0x7827c4`. Firmware bookkeeping
  is candidate insertion `0x1bc38`, release helpers `0x1887a`, `0x18b92`,
  `0x18bf2`, `0x17a24`, and `0x17d7c`, dirty context refresh, default
  refresh `0x1b04c`, allocator state, and continuation cleanup on no-install
  or failed-resume exits. Hardware/external state is limited to the host byte
  source and later formatter timing; the named residual downloaded-glyph
  boundaries below are ROM-local helper, source-read, or payload-count stops,
  not missing parser or publication routes.
  Exact residuals are the named compact-helper table/source/count boundaries
  in `Minimal Downloaded Glyph Boundary Walkthrough`: unchecked short-compact
  `0x1fe76` table reads above valid index `128`, wrapped width low bytes
  selecting invalid `0x1f034` targets, span-31 fallback source offset
  `+0xb50`, and oversized segmented-wide products stopped by the `0x7fff`
  payload-count cap before `0x16498`.
- Raster and rectangle cluster:
  rectangle state and rule production run through `0x10898 -> 0x10b80 ->
  0x13386 -> 0x133aa -> 0x1f446`; raster state and encoded rows run through
  `0x10808`, `0x1075a`, `0x11f82 -> 0x121cc -> 0x12218 -> 0x105d0 ->
  0x13070 -> 0x13250 -> 0x1f88e`. Owners are
  [rectangle-graphics.md](rectangle-graphics.md) and
  [raster-graphics.md](raster-graphics.md). Rectangle bytes follow
  `ESC *c#A/#B/#H/#V/#G/#P`: dimension writers `0x10e68`, `0x10e22`,
  `0x10a40`, and `0x10ae0` populate `0x78316a` / `0x783166`; `0x10dce`
  writes area-fill id `0x78316e`; `0x10898` maps fill selector; `0x10b80`
  clips against cursor/orientation/extents; `0x13386 -> 0x133aa` queues the
  rule object under page-root `+0x24`; `0x1edc6` bridges it to render-record
  `+0x1c`; and `0x1f446` dispatches solid selector `7` to `0x1f596` or
  gray/pattern selectors to `0x1f4e0`. Raster bytes follow `ESC *t#R`,
  `ESC *r#A/#B`, and delayed `ESC *b#W`: `0x10808` writes resolution-derived
  mode/scale while inactive; `0x1075a` seeds origin, limit, and active state;
  `0x107fa` clears only the active byte; `0x11f82 -> 0x121cc -> 0x12218`
  restores the transfer record; `0x105d0` gates/caps/drains payload bytes;
  `0x13070 -> 0x13250` queues encoded objects under page-root `+0x1c`; and
  `0x1ef6a -> 0x1efc2 -> 0x1f88e` renders modes `0..3`. Raster state is the
  block rooted at `0x783170`: row `+0x02`, accepted byte count `+0x04`,
  overflow/drain count `+0x06`, encoded mode `+0x08`, baseline/origin
  `+0x0a`, scale `+0x0e`, row byte limit `+0x10`, and active flag `+0x12`.
  `0x10808` writes scale/mode only when active flag `+0x12` is clear;
  `0x1075a` sets the active flag and seeds origin from cursor x `0x782c8a` or
  cursor y `0x782c8e` according to orientation `0x782da3`; `0x107fa` clears
  only `+0x12`, allowing later resolution changes to take effect. Transfer
  handler `0x105d0` rereads restored record word `+2` as the payload count,
  drains negative or beyond-extent rows without `0x13070`, and calls
  `0x13070` only for accepted rows. `0x13070` derives bucket `0x782a7c` and
  packed key `0x782a7e`; `0x13250` links an encoded-span object with class
  byte `+0x04 = 0x80`, mode byte `+0x05`, rounded payload capacity `+0x06`,
  key `+0x08`, and payload bytes at `+0x0a`. Renderer `0x1f88e` masks
  object byte `+0x05 & 3`: mode `0` renders literal rows, modes `1`, `2`,
  and `3` expand payload bytes into `2`, `3`, or `4` output rows through ROM
  helper tables. Residual work must change clipping, transfer acceptance/drain
  outcome, allocator state, object bytes, bridge roots, or renderer helper
  inputs.

  Concrete stream examples are now part of the route index. Chained
  `ESC *c12a5b0P` reaches handlers `0x10e68`, `0x10e22`, and `0x10898`, then
  queues selector-7 rule object
  `00 00 00 00 01 07 4a 00 00 0c 00 05 00 00` under page-root `+0x24`.
  Retried no-room publication can requeue the same selector path after
  `0x10d22 -> 0xff1e -> 0x10084`; render bridge `0x1edc6` copies the rule
  list to render-record `+0x1c`, and `0x1f446` dispatches solid selector `7`
  to `0x1f596`. Primary raster stream
  `ESC *t300R ESC *r1A ESC *b4W f0 0f aa 55` queues mode-0 raster object
  `00 00 00 00 80 00 00 04 00 01 f0 0f aa 55` under page-root `+0x1c`; its
  class byte `0x80` selects encoded raster dispatch, mode byte `0` selects
  helper `0x1f8da`, word `+0x06 = 4` is copied payload capacity, and key
  `+0x08 = 0x0001` is the packed coordinate. Dense accepted mode-0 rows can
  split before publication into `0x00f2` then `0x003a` objects; `0x13250`
  inserts the later object at the bucket head, so the published chain is
  newest-first when `0x1ed84` / `0x1ef6a` consume it. Evidence is
  [pcl-command-map.md](pcl-command-map.md#supported-stream-dispatch-matrix),
  [rectangle-graphics.md](rectangle-graphics.md), and
  [raster-graphics.md](raster-graphics.md).
  Raster/rectangle state classification: canonical rectangle state is width
  `0x78316a`, height `0x783166`, area-fill id `0x78316e`, page/cursor inputs
  `0x782c8a/0x782c8e`, orientation `0x782da3`, extents
  `0x782db8/0x782db6`, source record `0x782a88`, page-root rule-list head
  `root+0x24`, 14-byte rule objects from `0x133aa`, selector byte `+0x05`,
  packed key `+0x06`, width `+0x08`, height `+0x0a`, and continuation word
  `+0x0c`. Canonical raster state is block `0x783170`, including baseline
  `+0x00`, row `+0x02`, accepted count `+0x04`, overflow/drain count
  `+0x06`, encoded mode `+0x08`, origin `+0x0a`, scale `+0x0e`, row byte
  limit `+0x10`, and active byte `+0x12`. Canonical page/image state is
  current root `0x78297a`, bucket root `+0x1c`, encoded object class `+0x04`,
  raster mode byte `+0x05`, count `+0x06`, key `+0x08`, copied payload bytes
  `+0x0a..`, bridge-normalized rule list `+0x1c`, and render bucket root
  `+0x18`. Derived/cache state is rule/raster bucket index `0x782a7c`, low
  bucket byte `0x782a7d`, packed key `0x782a7e`, allocation capacity
  `0x782a80`, horizontal phase `0x782dc0`, band caches
  `0x783a20/0x783a22/0x783a28`, destination stride `0x783a1c`, fallback
  storage rooted at `0x7810b4`, and dense-row split objects inserted by
  `0x13250`. Parser scratch is the six-byte `ESC *c` command record consumed
  by rectangle handlers, delayed-payload byte `0x782a1a`, saved handler
  `0x782a1c`, saved record `0x782a20..0x782a25`, restored cursor
  `0x78299e`, and the live `ESC *b#W` record until `0x105d0` reads it.
  Firmware bookkeeping is stream allocator state `0x782a70`, `0x782a72`, and
  `0x782a76`, copy-stop/publication flag `0x782996`, root retry flag
  `+0x15.0`, no-room retry path `0x10d22 -> 0xff1e -> 0x10084`, and chunk
  allocator behavior in `0x132b6..0x13382`. Hardware/external state is absent
  after payload bytes are admitted by `0xa904` / `0xdace`; later physical
  engine consumption starts after the shared render buffers are written.
- Publication and render-scheduler cluster:
  reset, FF, page-size, page-length zero/default, orientation, paper-source,
  copies, VFC publication, and no-room retries converge on `0xff1e`.
  Published records then run
  `0x1ed84 -> 0x1edc6 -> 0x1eba4 -> 0x1ef6a`. Owners are
  [publication-commands.md](publication-commands.md),
  [page-record-storage.md](page-record-storage.md), and
  [active-render-scheduler.md](active-render-scheduler.md). The byte-stream
  route is that command handlers such as reset `0xcc52`, FF `0xf0f0`,
  page-size `0xfc74`, page-length zero/default `0xf9e8`, orientation
  `0x10220`, paper source `0xef62`, copy count `0xeef0`, VFC page-boundary
  helper `0xf124`, or allocator retry paths call `0xff1e` after any required
  pending text/span flush. `0xff1e` consumes current page root `0x78297a`,
  copies compact/raster bucket root `+0x1c`,
  rule list `+0x24`, fixed list `+0x28`, context slots `+0x2c..`, pool-header
  state, and copy-count/source fields into the page/control pool, sets
  publication flag `0x782996`, and clears the current root. `0x1ed84` selects
  the published source, `0x1edc6` bridges roots into render-record
  `+0x18/+0x1c/+0x20` and context slots, `0x1eba4` schedules band words, and
  `0x1ef6a` dispatches compact/raster buckets, rules, and fixed lists.
  Page-size `ESC &l#A` publishes queued objects before `0xfc74` writes page
  code `0x782da2`, sets pending flag `0x782997`, and rebuilds geometry such
  as active extents and top offset. Page-length nonzero `ESC &l#P` refreshes
  page extent `0x782dba`, page code `0x782da2`, and later printable placement;
  page-length zero/default `ESC &l0P` can flush through `0xf34a`, publish
  through `0xff1e`, and then restore default page state plus optional
  paper-source output/control state. Orientation `ESC &l#O` publishes before
  `0x10220` writes orientation byte `0x782da3` and installs
  orientation-specific extents, so rendered pixels belong to the
  pre-orientation page root. Paper-source `ESC &l#H` flushes and publishes
  through `0xef62`, then writes environment byte `0x782da6`, pending byte
  `0x782998`, and software-visible output/control bytes `0x780e8f` /
  `0x780e26` for changed source state. Copies `ESC &l#X` is the delayed
  publication variant: `0xeef0` stores nonzero absolute copy count
  `0x782da4`, clamps values above `99`, and does not publish until later
  `FF` / reset / page-boundary publication copies it into pool-header word
  `+0x0c`.
  Concrete publication streams are now part of the route index. For
  `! ESC E`, `! ESC &l1A`, `! ESC &l1O`, `! ESC &l2H`, and `! ESC &l2X FF`,
  the pre-command printable queues compact object
  `00 00 00 00 00 00 00 01 20 00 01` before the publication command mutates
  page or environment state. `0xff1e` preserves page-root context slot
  `+0x2c = 0x440946b4`, writes pool state byte `+4 = 2`, stores the
  published pointer in `0x780ea6`, sets flag `0x782996`, and clears
  `0x78297a`. For reset, FF, page-size, orientation, and paper-source, the
  published header preserves default environment/status fields. For
  `! ESC &l2X FF`, `0xeef0` first writes `0x782da4 = 2`; the following FF
  publication copies it into pool-header word `+0x0c`. The scheduler then
  promotes the record through `0x780eae`; `0x1ed84` / `0x1edc6` copy header
  words, bucket root `+0x1c`, and context slots before
  `0x1ef6a -> 0x1effe` renders the compact object. Evidence is
  [publication-commands.md](publication-commands.md) and
  [pcl-command-map.md](pcl-command-map.md#supported-stream-dispatch-matrix).
  Publication-cluster state classification: canonical state is the current
  page root `0x78297a`, page-root bucket/list pointers `+0x1c/+0x24/+0x28`,
  context slots `+0x2c..`, published source pointer `0x780ea6`, active source
  pointer `0x780eae`, copy count `0x782da4`, paper source byte `0x782da6`,
  page code `0x782da2`, and orientation byte `0x782da3`. Derived/cache state
  is the geometry rebuilt by `0xfc74` / `0x10220` / `0xf9e8`, bucket keys and
  compact coordinates already written by producers, render-record roots
  `+0x18/+0x1c/+0x20`, and render-band fields computed after `0x1ed84`.
  Parser scratch is the six-byte command record that brought the stream to
  `0xf0f0`, `0xfc74`, `0x10220`, `0xef62`, `0xeef0`, or `0xcc52`, plus any
  pending span state flushed through `0xf34a` before publication. Firmware
  bookkeeping is publication flag `0x782996`, pending geometry/source flags
  `0x782997` / `0x782998`, pool state byte `+4`, pool-header copy word
  `+0x0c`, and scheduler progress words. Hardware/external state is limited
  to formatter/DC timing after the selected published record is available; it
  does not change the ROM-derived bucket/list/context roots copied by
  `0x1edc6`.
  Hardware timing can change when active-band work is scheduled, but
  not the documented page-object-to-row construction for an already selected
  published record.
- Macro, data-chain, and overlay cluster:
  macro commands run `0xe112` / `0xdd08`; record selection and storage use
  `0xe0a4` and `0xe002`; execute/call frames use `0xe418` and `0xe22c`;
  overlay publication uses `0xff1e -> 0xe0a4 -> 0xe4f4 -> 0x11774`.
  Owner note is [macro-data-chain.md](macro-data-chain.md). The supported
  output rule is that replayed bytes become ordinary parser input and use the
  same page-object and render owners as live host bytes. `ESC &f#Y` writes
  current macro id `0x783164` through `0xe112`; `ESC &f#X` reaches `0xdd08`
  selectors for definition, execute, call, overlay, delete, and permanence.
  Definition stores payload bytes through alternate/data append sink `0xe002`
  into linked 0x100-byte chunks recorded in the 32-entry macro pool at
  `0x782a98`. Execute and call selectors look up records through `0xe0a4` and
  build data-chain frames at `0x782d76` through `0xe418`, with frame
  `+0x09 = 2` for execute or `3` for call. Host fetch `0xa904` prioritizes
  those frame bytes, so replay enters parser loop `0x11774` and reaches the
  ordinary command owners for printable text, controls, transparent data,
  raster, rectangle, span flush, publication, and rendering. Overlay state
  `0x782a92` / `0x782a94` is consumed during `0xff1e`; `0xe4f4` builds a
  non-replay frame with kind `+0x09 = 4` before publication when the enabled
  record exists, while disabled, missing-record, or retry-flag gates publish
  the base page unchanged.

  Concrete replay effects are now part of the route index. Minimal overlay
  stream `ESC &f123Y ESC &f0X ! CR ESC &f1X ESC &f4X` stores payload
  `21 0d`; publication replays it before root copy, queues compact one-glyph
  object prefix `00 00 00 00 00 00 00 01 20 00 01`, and then CR advances
  cursor/page state without adding a second visible object. Repeated enabled
  overlay publication keeps the macro record canonical and composes that same
  replayed text with page-specific selector-7 rule objects such as
  `00 00 00 00 01 07 88 01 00 0c 00 03 00 00` and
  `00 00 00 00 01 07 e4 00 00 08 00 04 00 00`. Skip gates are concrete:
  disabled overlay mode, missing record from `0xe0a4(0x782a94)`, or page-root
  flags word `+0x14` bit 0 skip `0xe4f4`, so a base printable/rule page such
  as rule object `00 00 00 00 01 07 a2 00 00 06 00 02 00 00` publishes
  unchanged. Stored payload variants prove overlay replay uses ordinary owners:
  `ESC &p2X!!` routes through transparent restore `0x12452` and queues compact
  text prefix `00 00 00 00 00 00 00 02 20 00 01 20 02 02`; stored
  `! ESC *t300R ESC *r0A ESC *b2W c3 3c` reaches delayed raster handler
  `0x105d0` and queues mode-0 raster object
  `00 00 00 00 80 00 00 02 00 00 c3 3c`; stored `ESC &a6L!` flushes
  selector-`0x4000` segment-list object
  `00 00 00 00 40 00 00 01 32 00 03 00 00 10`. Evidence is
  [macro-data-chain.md](macro-data-chain.md) and
  [pcl-command-map.md](pcl-command-map.md#supported-stream-dispatch-matrix).
  Macro/data-chain state classification: canonical state is current macro id
  `0x783164`, macro record pool `0x782a98`, selected record pointer
  `0x782d7a`, active data-chain frame pointer `0x782d76`, frame fields
  `+0x00/+0x04/+0x08/+0x09/+0x0a`, overlay state byte `0x782a92`, saved
  overlay id `0x782a94`, and page-root retry gate in flags word `+0x14` bit
  zero. Derived/cache state is normalized stored payload length, replay
  compact coordinates, replay-produced page objects, and the font/context
  refreshes restored from frame snapshots. Parser scratch is definition-mode
  byte `0x782c18`, append error byte `0x782c19`, parser records consumed by
  `0xdd08`, and alternate parser bytes that append through `0xe002` instead
  of executing immediately. Firmware bookkeeping is heap chunk allocation/free
  state, eight macro context-stack records, host gate bit 1, frame-end
  unwinding through `0xe22c`, and overlay detour state while `0xff1e`
  temporarily re-enters `0x11774`. The output effect is not a macro-specific
  renderer: replayed bytes re-enter the ordinary command owners, and overlay
  replay changes pixels only through the page objects those ordinary handlers
  create before `0xff1e` copies the root.
- VFC cluster:
  `ESC &l#W` uses delayed route
  `0x11f6e -> 0x121cc -> 0x12218 -> 0x12cfe`; `ESC &l#V` consumes the table
  through `0x1280a`. Owner note is
  [vertical-forms-control.md](vertical-forms-control.md). Output is cursor
  movement or page publication before later printable bytes queue page objects.
  `0x12cfe` rewinds the restored command record, consumes table payload bytes
  through `0xdace`, writes accepted even-count bytes into table
  `0x782dde..0x782edd`, derives limit/cache fields `0x782dc2` and `0x782dd2`,
  and clears modified-layout flag `0x782ee1`; zero-count/default handling
  rebuilds the table through `0x12b96`, while odd or over-window counts drain
  without installing table bytes. `0x1280a` maps selector `n` to mask
  `1 << (n - 1)`, scans the table with VMI `0x783160`, top offset
  `0x782dce`, current y `0x782c8e`, and line caches
  `0x782ede/0x782edf/0x782ee0`, then either resets cursor x/y for the next
  printable byte or calls `0xf124 -> 0xff1e` so the old page is published
  before following printable output queues on a fresh page. The adjacent
  page-layout route `ESC &l#L` is owned by
  [direct-control-codes.md](direct-control-codes.md) and
  [pcl-command-map.md](pcl-command-map.md): handler `0xee64` rewinds the
  parser record, clears perforation-skip byte `0x783191` for selector `0`,
  sets it for selector `1`, and leaves other selectors without a state write.
  Shared overflow helper `0xf36c` is the visible consumer; it reads cursor y
  `0x782c8e`, text-bottom/perforation limit `0x782dc2`, and byte `0x783191`,
  then calls `0xf124 -> 0xff1e` only when the nonzero limit is exceeded and
  perforation skip is enabled. Otherwise it returns without publishing the
  current page, so later printable/raster objects stay on the same page root.

  Concrete VFC streams are now part of the route index. Table load
  `ESC &l4W 00 00 00 02 !` stores prefix `00 00 00 02` at
  `0x782dde`, derives VFC/text-bottom cache state, consumes the four payload
  bytes before printable parsing resumes, and leaves the following `!` queued
  at compact coord `0x9001`. Forward channel jump `ESC &l2V!` finds channel
  `2` at line `1`, writes y `176`, resets x to left margin `10`, and queues
  the following `!` at compact coord `0xb001`; before-top y `89` normalizes
  through `0x128ae..0x128f4` and reaches the same coord. Selector-zero
  target-equal `ESC &l0V!` leaves an already matching top-of-form cursor in
  place and queues `!` at compact coord `0x9e02`. Publishing splits are
  concrete too: `! ESC &l0V !` publishes the pre-VFC `!` at compact coord
  `0xbe02`, resets x/y to `10` / `126`, and queues the post-VFC `!` on a
  fresh page at `0x9001`; wrap-hit `! ESC &l2V !` publishes the old printable
  at `0xde02`, wraps to line `1`, writes y `176`, and queues the fresh-page
  printable at `0xb001`; target-after-text recovery publishes the old page at
  absolute coord `0x4e02` and queues the fresh printable at `0x3001`.
  Evidence is [vertical-forms-control.md](vertical-forms-control.md) and
  [pcl-command-map.md](pcl-command-map.md#supported-stream-dispatch-matrix).
  VFC state classification: canonical state is the 128-word VFC table
  `0x782dde..0x782edd`, VMI `0x783160`, top offset `0x782dce`, cursor
  `0x782c8a/0x782c8e`, margins `0x782dd6/0x782dda`, VFC/text-bottom caches
  `0x782dc2/0x782dd2`, line-bound caches
  `0x782ede/0x782edf/0x782ee0`, current page root `0x78297a`, and
  publication helpers `0xf124` / `0xff1e`. Derived/cache state is the
  computed start line, target line, selector mask `1 << (n - 1)`,
  default-table channel pattern from `0x12b96`, and following printable
  coordinates produced after `0x1280a` commits cursor state. Parser scratch
  is the delayed `ESC &l#W` record saved by `0x121cc`, restored by
  `0x12218`, cursor `0x78299e`, and payload bytes consumed by `0xdace`.
  Firmware bookkeeping is modified-layout flag `0x782ee1`, pending-width
  latch `0x782a58`, pending cursor/text latch `0x782a6d`, span-enable byte
  `0x783184`, and perforation-skip byte `0x783191` for the adjacent
  `ESC &l#L` overflow consumer. The output effect is cursor-only unless
  `0x1280a` or shared overflow helper `0xf36c` calls `0xf124 -> 0xff1e`; in
  those cases the old page root is published before later bytes create fresh
  page objects.
  Residuals are only variants that change VFC table bytes, channel target
  choice, publication split, perforation limit/cursor/skip state, or following
  object coordinates.

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
- Transparent/display payload readers: `ESC &p#X...`, `ESC Y ... ESC Z`, and local
  Control-Z forms; start with [Transparent Payload Outcome
  Matrix](transparent-print-data.md#transparent-payload-outcome-matrix),
  [Display Functions Decision
  Checkpoint](display-functions.md#display-functions-decision-checkpoint), and their
  worked paths in [firmware-dataflow-model.md](firmware-dataflow-model.md).
- Font selection and visible glyph output:
  `ESC (s0p10h12v0s0b3T!!`,
  `ESC )s0p16h8v0s0b0T SO !!`, final-`X` / final-`@` streams, and
  pitch-mode `ESC &k#S`; for symbol-set streams also include `ESC (0N`,
  `ESC (10U`, `ESC (11U`, and the secondary `ESC )...` forms before the
  printable tail. Start with
  [symbol-set-selection.md](symbol-set-selection.md),
  [font-context-metrics.md](font-context-metrics.md),
  [built-in-resource-scan.md](built-in-resource-scan.md),
  [resource-rom.md](resource-rom.md#resource-rom-outcome-matrix), and
  `Worked Path: Font Selection To Visible Glyphs`. The font commands update
  candidate/context/map state
  through resource-scan windows, `0xc580`, `0x13eb8`, `0x144d2`, and
  `0x14c64`; visible output is produced only when later printable bytes
  consume those contexts through `0xd04a -> 0x1393a -> 0x12f2e` and
  publication copies both compact buckets and context slots through `0xff1e`
  / `0x1edc6`.
- Downloaded-font payloads and downloaded-glyph rendering:
  `ESC )s#W` descriptor/character streams followed by printable output or
  rule/raster composition. Start with
  the downloaded-font rows in [pcl-command-map.md](pcl-command-map.md),
  then [downloaded-fonts.md](downloaded-fonts.md), followed by the
  downloaded-glyph worked paths and boundaries in
  [firmware-dataflow-model.md](firmware-dataflow-model.md). The key parser
  branch is `0x11f96`: zero-count streams enter `0x15d0a`, nonzero payloads
  enter `0x16c14`, successful downloaded-character installs reach `0x16498`,
  and later printable bytes queue objects through `0x12f2e`. The command-map
  row classifies current-font state, current-record/candidate state, delayed
  payload scratch, descriptor/resource scratch, continuation fields, and
  install/release bookkeeping before the owner note expands the low-level
  ledger. For row-count streams, low-byte rows `0x0001..0x00ff` render through
  the documented compact helpers; high-row short compact cases such as
  installed rows `0x0101..0x0103` stop at the exact `0x1fe76` fallback table
  boundary rather than claiming pixels beyond the ROM jump-table overflow. For
  a heterogeneous downloaded-glyph page image, start with `Worked Path:
  Downloaded Glyph Rule/Raster Composition`, which follows `ESC )s18W` through
  the byte-24 handoff into rectangle, printable, raster, publication, bridge,
  and render dispatch.
- Raster, rectangle/rule, and mixed page-image streams:
  `ESC *t300R ESC *r0A ESC *b2W...`,
  `ESC *c12a5b0P`, and
  `! ESC *c12a5b0P ESC *t300R ESC *r0A ESC *b2W c3 3c FF`;
  start with [raster-graphics.md](raster-graphics.md),
  [rectangle-graphics.md](rectangle-graphics.md), and `Worked Path: Mixed
  Text/Rule/Raster Page Record`.
- Publication, VFC, macro replay, and status side channels:
  `! ESC E`, `ESC &k2G! FF`, `! ESC &l2X FF`, `ESC &l#W` / `ESC &l#V`,
  macro `ESC &f#X` streams, and `ESC *r1K 0x11`; start with
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
  Static xrefs close the ROM-local frame-kind producer set:
  `0xe418` is called only from `0xde96` / `0xdebc`, passing `2` / `3`;
  `0xe4f4` is called from `0xff8e` and writes `4`; `0xe1e4` clears stale
  frame kind bytes to zero. Remaining host-input risk is physical MMIO
  naming/timing, not byte-source priority, direct caller classification,
  frame-kind production, or observed macro/data-chain replay.
- External service/status preemption:
  ROM evidence is `0xba48..0xc36e` in
  `generated/disasm/ic30_ic13_external_ready_service_loop_00ba48.lst` and
  `generated/disasm/ic30_ic13_external_service_reset_00c06e.lst`.
  Reproduction evidence is
  [external-ready-service.md](external-ready-service.md#external-ready-outcome-matrix),
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
  software-composed in
  [external-ready-service.md](external-ready-service.md#external-ready-outcome-matrix):
  commit/readback failure sets `0x780e39.3` through
  `0x571e -> 0x9bee(0x780e36, 0x00000008)`, and `0xc1c6` consumes the same bit
  as non-returning `68 SERVICE` through `0x85c0`. Startup retained-record load
  is the separate `0x5a16 -> 0x97e4 -> 0x56c2 -> 0x1284` path that reports
  `67 SERVICE` when no active marker is found. The teardown handoff through
  `0xc108 -> 0x19dd2 -> 0x36e4` is now bounded in
  [page-font-scheduler.md](page-font-scheduler.md#page-font-scheduler-outcome-matrix)
  and
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
- Host/status side channels: ROM evidence is `0x12034`, `0x122be..0x12326`,
  `0xb022..0xb0c0`, `0xae2c..0xaece`, and `0x2888..0x2c3a`. Checked-in documentation is
  [Host/Status Side-Channel Decision
  Checkpoint](errors-and-status.md#hoststatus-side-channel-decision-checkpoint),
  [io-interfaces.md](io-interfaces.md), [host-byte-fetch.md](host-byte-fetch.md), and
  the semantic checkpoints `Host Interface Output FIFO` and `Page Environment Status And
  Pool Cursor Gate` in [semantic-state-model.md](semantic-state-model.md), surfaced
  first as `Worked Path: Host Interface Output FIFO And Model-ID Backchannel` and
  `Worked Path: Page Environment Status Bridge` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md). This cluster has no direct
  page-object or pixel effect: `ESC *r1K 0x11` and the `ESC *s#^` sibling enqueue
  literal `33440A\r\n` through host-output FIFO helpers, and status producers such as
  `0x2888` feed outbound status bytes through `0xaece`. Fixture `0x12034/0x122be
  model-ID response emits FIFO literal` now pins both command entries, the `0x11efe`
  synthetic record, accepted query byte `0x11`, reject paths, and FIFO literal bytes. It
  still belongs in byte-stream reproduction because a full FIFO can stall producer
  `0xb090`, and a bidirectional host can react to the backchannel bytes by sending
  different future input.
- Parser byte and command records:
  ROM evidence is `0xda9a`, `0xdaf0`, `0xdb74`, and `0x11774`.
  The checked-in contracts are
  [pcl-parser-core.md](pcl-parser-core.md#parser-core-outcome-matrix) and
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
  ROM evidence is parser loop `0x11774`, service path `0x117d2..0x11818`,
  no-match paths `0x118b2..0x11900` and `0x11b32..0x11b8a`, terminal reset
  path `0x119a6..0x119f4`, delayed restore helper `0x12218`, normal parser
  table `0x112a4`, and alternate/data parser table `0x116f6`. Checked-in
  documentation is
  [pcl-parser-core.md](pcl-parser-core.md#parser-core-outcome-matrix),
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
  handlers or lowercase `0x11f4c` rewind entries, while macro/data storage
  bytes remain reproducible through append paths. Delayed payload restore in
  alternate/data mode follows `0x12358`: generic wrapper `0x1228a` drains as
  a wrapper, while non-wrapper raster, transparent-text, VFC, and font saved
  handlers are not called from that branch. `ESC E` still reaches reset
  handler `0xcc52`.
  Imaging command families now have explicit no-output/storage consequences
  from this branch: alternate/data `ESC *c` rows leave rectangle fields
  `0x78316a`, `0x783166`, `0x78316e`, source record `0x782a88`, and rule-list
  root `+0x24` unchanged; alternate/data `ESC *t` / `ESC *r` rows leave raster
  block `0x783170` unchanged; and alternate/data `ESC *b#W/w` restores through
  `0x12358` without calling `0x105d0`, `0x13070`, `0x13250`, or `0x138de`.
  These bytes can affect imaging only after stored input replays through the
  normal parser route.
  Direct-control and publication-adjacent families have the same explicit
  no-output boundary in alternate/data mode. BS, HT, LF, FF, CR, SO, and SI
  append through `0xe002` instead of calling their normal handlers, so cursor,
  stack, span, line-termination, and selected-context fields stay unchanged.
  `ESC &l A/C/D/E/F/H/L/O/P/T/V/X` rows in table `0x116f6` are blank or
  `0x11f4c` outcomes, so page-size, page-length, orientation, paper-source,
  copies, VMI/HMI, and VFC-target fields are not written and no page
  publication runs from those rows. The active exceptions remain `ESC E`
  reset and `ESC &l#W/w` VFC payload storage. Evidence is
  [direct-control-codes.md](direct-control-codes.md#owner-summary) and
  [publication-commands.md](publication-commands.md#owner-summary).
  Related parser artifacts are bounded separately: `ESC ?` is consumed in
  wrapper `0xda9a`, `ESC Z` terminates the direct display-functions reader,
  and `ESC &lT/t` has no standalone page-output effect.
  Reproduction rule: do not treat all skipped bytes alike. Explicit normal
  zero-handler rows still preserve the `0x12218` delayed-restore boundary;
  alternate/data zero-handler rows preserve bytes through `0xe002`; unmatched
  normal bytes only become printable when the `0x782f06` / `0x782eeb`
  predicate allows the `0xd04a` fallback.
- Transparent print data: ROM evidence is `0x11f5a`, `0x12452`, `0xd04a`, `0xd0f0`, and
  `0xd550`, plus disassembly
  `generated/disasm/ic30_ic13_transparent_data_handler_011f5a.lst`. Reproduction
  evidence is [Transparent Payload Decision
  Checkpoint](transparent-print-data.md#transparent-payload-decision-checkpoint). The
  tracked semantic contract is that `ESC &p#X` is a counted delayed byte-stream splice,
  not an opaque skip. Handler `0x11f5a` schedules `0x12452` through `0x121cc`; `0x12218`
  restores command record `80 58 ...`; `0x12452` consumes the absolute record word `+2`
  count from `0xa904`, preserves local `1a 58 -> 7f` and `1a xx -> xx` behavior, and
  routes normalized payload bytes through `0xd04a` or `0xd0f0` according to context
  filtering. Canonical fields are the command-record count, selected context slot
  `0x782f06`, and text cursor `0x782c8a`; parser scratch is `0x782a1a`, `0x782a1c`, and
  `0x782a20..0x782a25`; derived/filtering state is `0x782eea + 0x10 * 0x782f06`,
  `0x782efa`, and high-byte flags `0x783132`/`0x783133`. Remaining risk is the secondary
  segment-57 resource-window continuation, tracked by `Boundary: Secondary Segment-57
  Source` in [firmware-dataflow-model.md](firmware-dataflow-model.md): fixture
  `transparent secondary segment-57 continuation policies diverge after verified bytes`
  pins glyph `0x5f`, segment `0x39`, firmware source `0x0bfe22`, required range
  `0x0bfe22..0x0c0321`, and the first `478` bytes inside the verified `IC32,IC15`
  resource-pair image. Scanner fixtures `0x41a HEAD scanner would duplicate records
  under simple resource mirror` and `0x41a HEAD scanner rejects non-HEAD 0x40000
  continuations` constrain the physical continuation hypotheses. Startup checksum
  evidence narrows but does not close the edge:
  [firmware-startup.md](firmware-startup.md) records the resource-pair byte-sum range as
  `0x080000..0x0bffff`, so it covers the verified suffix but not the `0x0c0000`
  continuation bytes.
- Display functions: ROM evidence is normal handler `0x12536..0x1261e`, alternate/data
  handler `0x12120..0x1219c`, and parser-table entries in normal table `0x112a4` and
  alternate table `0x116f6`. Reproduction evidence is [Display Functions Decision
  Checkpoint](display-functions.md#display-functions-decision-checkpoint), `Display
  Functions ESC Y Reader` in `notes/semantic-state-model.md`, `ESC Y Display Functions
  Readers` in `notes/pcl-parser-core.md`, surfaced first as `Worked Path: Display
  Functions Direct Reader` in [firmware-dataflow-model.md](firmware-dataflow-model.md),
  and disassembly `generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst`.
  The covered command-family contract is `ESC Y ... ESC Z` as a direct `0xa904` reader
  loop with local `1a 58 -> 7f` normalization, loop-local `ESC`-seen scratch in `D4`,
  normalized payload byte in `D7`, and termination when routed/appended `ESC Z` is seen
  or fetch returns `-1`. Normal handler `0x12536` routes normalized bytes through
  `0xd04a` or `0xd0f0` according to selected-context filtering state: canonical
  `0x782c18`, `0x782f06`, and parser dispatch state; derived/filtering state `0x782eea +
  0x10 * 0x782f06`, `0x782efa`, `0x783132`, and `0x783133`; and parser scratch stack
  word `A6-2`. Alternate/data handler `0x12120` appends literal `ESC Y` plus normalized
  loop bytes through firmware bookkeeping sink `0xe002` into macro/data-chain chunk
  `0x783988`; normal CR output also uses bookkeeping helper `0xf054`. Fixtures `ESC Y
  display-functions stream reaches page-record output`, `ESC Y display-functions
  filter-on routes controls as printable`, and `0x12120 ESC Y alternate append stores
  normalized display bytes` cover the default-filter page-output path, nonzero
  context/filter page-output path, and alternate/data append-only path. No unresolved
  middle edge remains for this command-family loop.
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
  [Segment-List Outcome
  Matrix](page-record-storage.md#segment-list-outcome-matrix) plus
  [Fixed-List Outcome
  Matrix](page-record-storage.md#fixed-list-outcome-matrix) in
  [page-record-storage.md](page-record-storage.md).
  Confidence is high for the pending state writers, metric gates, object byte
  shapes, orientation split, bridge shape, and ROM-derived row construction
  because each cited edge has handler, field, or render-helper evidence; fixtures
  only exercise the documented path and state shape.
  No unresolved ROM-local middle edge remains for this pending-span-to-page
  object handoff; remaining work is selected-font or byte-stream variants that
  change source-object fields, unflagged/flagged metric fields, pending span
  bounds, `0x12714` page-extent acceptance, orientation branch, page-object
  fields, bridge roots, or ROM row-construction inputs.
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
  The exact queue boundaries are composed in
  [Rectangle Outcome Matrix](rectangle-graphics.md#rectangle-outcome-matrix):
  `0x10ba0..0x10bcc` rejects or compensates x, `0x10bd4..0x10c0e` rejects or
  compensates y, `0x10c42..0x10d0a` writes the portrait source record, and
  `0x10c74..0x10dcc` writes the landscape-swapped source record.
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
  bytes, bridge state, render dispatch, or ROM-derived row construction.
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
  cap/drain gates, page-record object bytes, bridge dispatch, and ROM-derived row
  construction.

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
  Alternate/data raster syntax is an explicit no-object branch:
  `ESC *t#R`, `ESC *r#A`, and `ESC *r#B` are blank or `0x11f4c` outcomes in
  table `0x116f6`, so `0x10808`, `0x1075a`, and `0x107fa` do not write raster
  block `0x783170`. `ESC *b#W/w` still arms `0x11f82 -> 0x121cc`, but
  alternate/data restore reaches `0x12358` instead of saved handler
  `0x105d0`; no accepted counts, raster objects, page-root bucket entries,
  bridge roots, or `0x1f88e` inputs are produced until replay returns the
  stored bytes to normal mode.
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
  It also composes pending header flags before marking the root ready:
  page-size/page-length flag `0x782997` sets root byte `+0x0a.0` and clears
  `0x780e99`; remaining status/header byte `0x780e99` sets root byte
  `+0x08`; paper-source/layout flag `0x782998` sets root byte `+0x0a.1`.
  Every non-early publication copies paper-source/environment byte `0x782da6`
  to root byte `+0x07` and copy count `0x782da4` to root word `+0x0c`.
  Evidence is in [publication-commands.md](publication-commands.md), section
  `Published Header Flags`, from `0xffd2..0x1005a`.
  The checked command-family streams are `! ESC E`, `ESC &k2G! FF`,
  `! ESC &l1A`, `! ESC &l0P`, `! ESC &l1O`, `! ESC &l2H`, and
  `! ESC &l2X FF`.
  Their writers are reset handler `0xcc52` / `0xcc70`, FF handler `0xf0f0`,
  page-size handler `0xfc74`, page-length handler `0xf9e8`, orientation
  handler `0x10220`, paper-source handler `0xef62`, and copies handler
  `0xeef0`.
  The semantic ordering is byte-stream visible: reset, page-size,
  page-length zero/default, orientation, and paper-source publish already
  queued page objects before or while they mutate default-page, geometry,
  orientation, or paper-source state; FF publishes after the `ESC &k2G`
  line-termination mode applies its CR-style x reset; copies stores
  `0x782da4` before the following FF publication copies it into pool-header
  word `+0x0c`.
  Page-size `0xfc74`, page-length `0xf9e8`, reset-default helper `0xcda2`,
  and paper-source handler `0xef62` are the ROM-local writers for the pending
  header bytes consumed by `0xff1e`.
  Parser scratch is temporary command records and the modeled `0xa904` host
  ring bytes; after the handlers queue page objects, publication consumes
  page-root fields rather than parser records.
  Derived/cache state includes render-band caches `0x783a20`, `0x783a22`, and
  `0x783a28`, which appear only after `0x1ed84` / `0x1edc6` bridge the
  published record.
  Firmware bookkeeping includes stream allocator state
  `0x782a70/0x782a72/0x782a76`, publication flag `0x782996`, transient byte
  `0x782990`, pool header defaults, pending header flags `0x782997` /
  `0x782998`, status/header byte `0x780e99`, and command-specific header
  copies such as copy count `+0x0c`.
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
  preserves 0xeef0 pool header word`, plus page-length fixtures
  `0xf9e8 ESC &l#P converts VMI lines to page length and selects internal
  page code` and `0xf9e8 ESC &l#P stream reaches page-length handler`.
  Checked-in evidence is [publication-commands.md](publication-commands.md),
  `Publication Commands To ROM-Derived Page Rows` in
  [semantic-state-model.md](semantic-state-model.md), and `Worked Path: Reset
  And Default Environment`, `Worked Path: FF Publication`, and `Worked Path:
  Publication Commands To ROM-Derived Page Rows` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md).
  Confidence is high for parser handler order, pre-command object preservation,
  reset/FF/geometry/page-length-zero/paper-source/copies side-effect ordering,
  pool-header defaults and copy-count field, current-root clearing, bridge
  preservation, and ROM-derived row construction for the direct publication
  streams.
  The unresolved boundary is not ROM-local publication state: final rows are
  documented through `0xff1e -> 0x1ed84 -> 0x1edc6 -> 0x1ef6a`, with
  fixtures serving as model-consistency checks for those interpreted rows.
  Remaining work is byte streams that expose a new pool-header field,
  source-record choice, bridge value, or row-construction input.
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
  [active-render-scheduler.md](active-render-scheduler.md),
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
  Published Record To Active Bands` plus `Band Scheduling Route Index` in
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
  compact row-copy phase `0x783a46`, and fallback buffer base
  `0x7810b4 + byte_pair_offset`.
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
  `0x7810b4 + byte_pair_offset` only for documented fallback rows, and treat
  later direct stores as overwrites rather than logical blends.
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
  output derived from the cited object and render-helper paths.
  No unresolved shared render-dispatch edge remains for the documented object
  classes. Remaining ROM-local work starts from byte streams that create
  different object fields, selected-font contexts, helper targets,
  continuation state, fallback split, or ROM-derived row construction.
- Mixed page-image stream:
  The primary heterogeneous page-image stream is
  `! ESC *c12a5b0P ESC *t300R ESC *r0A ESC *b2W c3 3c FF`.
  It documents that no single command draws the final image: parser handlers
  first queue compact text, rectangle/rule, and encoded-raster objects under
  one page root; `0xff1e` publishes the root; `0x1ed84` / `0x1edc6` bridge it
  into a render record; and `0x1ef6a` runs the ROM helpers that write the
  resulting row bytes.
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
  render call order, bucket-chain order, rule carry, and ROM-derived row
  construction.
  No unresolved middle edge remains for this exact stream's text source, rule
  selector, delayed raster restore, page-root storage, publication, bridge, or
  per-band bitmap merge.
  Remaining ROM-local work starts from byte streams that change text source
  fields, rectangle clipping or selectors, raster gate outcomes,
  `0x1381c` allocation/rollover state, bridge roots, continuation state, or
  row-construction inputs.
- Built-in glyph data:
  ROM evidence is the IC32/IC15 resource ROM tables and bitmap records.
  Checked-in documentation is
  [resource-rom.md](resource-rom.md#resource-rom-outcome-matrix),
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
  The sibling scan `0x196c4..0x19730` walks the same page-root context slots
  by masked low-24-bit resource/context value and live flags `0x78297f+n`.
  A live match calls `0x1ba6c`, which flushes pending text, publishes the
  current root through `0xff1e`, refreshes page/font defaults through
  `0xf8fc`, flushes again, and waits through `0x9ac2`; no root or no match
  waits through `0x9ac2` without publication.
  The selected-font cache path is part of the byte-stream contract:
  `0x13a48` compares the selected snapshot, while `0x14ba4..0x14c5c` can
  accept an active-object signature match by record bytes, bounded size/range
  checks, `0x158be` symbol word, Roman-8 `0x0115` compatibility, or the
  four-pair table at `0x15840`. A cache-preserving return keeps the existing
  map/context state for later printable bytes; it does not queue page objects.
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
  glyph-map consumption, bridge preservation, and ROM-derived row construction.
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
  `0x14e24..0x14f12` builds the active map from the fixed-record table:
  accepted `0x14eb6` entries copy their candidate index into `0x782f32` or
  `0x783032`, rejected entries become zero, and selected byte `+0x0e`
  decides whether upper-half map entries can be produced.
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
  `0x7810b4 + byte_pair_offset`. Parser scratch is the restored
  `ESC )s#W` command record, payload budget `0x783140`, and post-install
  drain through `0x12328`.
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
  bytes through parser, compact bucket objects, bridge, and ROM-derived row
  construction.
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
  [symbol-set-selection.md](symbol-set-selection.md),
  [built-in-resource-scan.md](built-in-resource-scan.md),
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
  The candidate records filtered by that path come from the startup/resource
  scan `0x1a2e4 -> 0x1a616 -> 0x1a9be`. In the verified built-in image,
  `0x1a9be` accepts 24 `HEAD`-path records and partitions them into 12
  class-zero and 12 class-one low-window candidates. Primary refresh activates
  class-zero pointer/count `0x782354` / `12`; secondary refresh activates
  class-one pointer/count `0x782324` / `12`. Later symbol, pitch, height,
  stroke, and chooser filters operate on those concrete windows, leaving
  selected slot `0x7828a8` and context/map state for `0x144d2` / `0x14c64`.
  Symbol-set finals route through `0x120be -> 0x1be22`, write requested
  symbol words at `0x782ef4 + 0x10 * slot`, dirty refresh flags
  `0x782f2c` / `0x782f2d`, and use `0x156de` to consume requested,
  remembered, and fallback words before the same candidate/map path. Final
  `@` subdispatches through `0x1bed4`, `0x1bf0a`, `0x1bf36`, or `0x1bf74`
  to copy default-symbol table words `0x782f1c`, `0x782f20`, `0x782f24`,
  and `0x782f28`. Final `X` keeps the prior requested symbol word and calls
  `0x17708(slot, parameter)`, selecting built-in contexts such as
  `0xc0089fb0` / `0xc00ae122` or bit-30-clear inline/downloaded context
  `0x00000100`. The exact selector branch is documented in
  [symbol-set-selection.md](symbol-set-selection.md#final-byte-special-cases):
  `0x17708` temporarily writes the parameter to current font-id field
  `0x782f2e`, restores the old value at `0x1778c`, and changes visible output
  only when success tails `0x177cc` or `0x17802` write `0x7828de`,
  `0x7828a8`, active symbol word `0x783144 + 2*slot`, and rebuilt map state.
  Scan-miss, candidate-slot-miss, class-mismatch, and context-full exits
  preserve the prior visible context.
  `0xc428(slot)` installs the selected context into the active page root:
  slot `0` reads `0x782ee6`, slot `1` reads `0x782ef6`, `0xc4fc` finds a
  matching or free page-root context slot, and `0xc428` writes selected
  page-root slot `0x78297e`. SI `0xc68a` installs/selects primary slot `0`;
  SO `0xc6b8` installs/selects secondary slot `1` and updates selected text
  slot `0x782f06`. This state-only control path is owned by
  [Selected Context Switch
  Checkpoint](direct-control-codes.md#selected-context-switch-checkpoint).
  Later printable bytes consume that state through
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
  shape, bridge state, or ROM-derived row construction.
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
- Host/status side-channel streams are covered for the ROM-local model-ID
  response and outbound status FIFO. Evidence:
  [errors-and-status.md](errors-and-status.md),
  [host-byte-fetch.md](host-byte-fetch.md),
  [pcl-command-map.md](pcl-command-map.md), and fixture
  `0x12034/0x122be model-ID response emits FIFO literal`.
  The concrete model-response stream is `ESC *r1K 0x11`; the `ESC *s#^`
  sibling reaches the same wrapper. Parser bytes enter through
  `0xa904 -> 0xda9a -> 0x11774`, then `ESC *r#K` reaches mode `7` and
  `ESC *s#^` reaches mode `6`. Both dispatch wrapper `0x12034`, which calls
  `0x11efe` to append a synthetic setup record with word `+2 = 1`, then enters
  `0x122be`.
  Producer `0x122be..0x12326` rewinds parser record cursor `0x78299e`, fetches
  the following query byte through `0xda9a`, and emits literal `33440A\r\n`
  from ROM string `0x12280..0x12288` only when the query byte is `0x11` and
  the active record word is `1` or `-1`. Each literal byte is enqueued through
  `0xb090`, which retries FIFO writer `0xb0c0` and waits on wait object
  `0x7801e2` if FIFO count `0x783ed2` is full. FIFO consumers
  `0xae2c` / `0xaece` later drain bytes using read/write pointers
  `0x783ed4` / `0x783ed8` and storage `0x783e92..0x783ed1`.
  This family has no page-object or pixel effect: it does not create a current
  page root, does not call `0xff1e`, and does not feed `0x1ed84` /
  `0x1ef6a`. Its reproduction effect is protocol-visible bytes and possible
  parser stalling when the host-output FIFO is full. A closed byte-stream
  renderer can ignore the response only when the host script does not consume
  backchannel bytes to choose later input.
  Canonical state is FIFO count/pointers/storage `0x783ed2`, `0x783ed4`,
  `0x783ed8`, `0x783e92..0x783ed1`, output backend selector `0x780e40`, and
  literal bytes `0x12280..0x12288`. Parser scratch is the synthetic six-byte
  setup record and the fetched query byte. Firmware bookkeeping is wait object
  `0x7801e2`, pending status count `0x780e22`, bridge-service byte
  `0x783e61`, and status-byte fields consumed by `0xaece`. Hardware/external
  state is the physical output backend behind `0xfffe0001` / `0xfffe0003` or
  `0xfffee005` / `0xfffee003`; physical protocol naming for the `0x11` query
  remains external, not a ROM-local parser/page/render gap.
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
  State` and `Publication Commands To ROM-Derived Page Rows` in
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
  `ESC &l#E`, or `ESC &l#F` paths. Remaining geometry work starts only when a
  byte stream changes table-derived page code or orientation fields, extent or
  text-bottom words consumed by printable placement and overflow checks,
  publication-before-mutation state at `0xff1e`, VFC/perforation-skip
  consumers, raster-origin or rectangle-clipping inputs, or render rows derived
  after those changed fields. Physical output, if captured, would be optional
  correlation outside the ROM render buffer.
- Raster graphics streams are covered for `ESC *t#R`, `ESC *r#A`, delayed `ESC *b#W`,
  lowercase transfer chaining, active-raster resolution behavior, row caps,
  beyond-extent drains, and modes 0/1/2/3. Evidence: [Raster Command-To-Pixel Owner
  Summary](raster-graphics.md#owner-summary),
  [raster-graphics.md](raster-graphics.md), `Raster Transfer Gate And Encoded Rows` in
  [semantic-state-model.md](semantic-state-model.md), `Worked Path: Raster Transfer
  Gates And Modes` in [firmware-dataflow-model.md](firmware-dataflow-model.md),
  host-fetched raster fixtures, and supporting report
  `generated/analysis/ic30_ic13_raster_graphics_flow.md`. The primary stream `ESC *t300R
  ESC *r1A ESC *b4W f0 0f aa 55` reaches parser handlers `0x10808`, `0x1075a`, and
  `0x11f82`. `0x11f82` schedules delayed transfer handler `0x105d0` through `0x121cc`;
  `0x12218` restores record `80 57 00 04 00 00` and calls `0x105d0` when payload bytes
  are available. The delayed record is not passed by volatile registers only: `0x12218`
  writes it back to the parser-record buffer, and `0x105d0` reopens `0x78299e - 6` at
  `0x105e4..0x105f2` before reading count word `+2`. Canonical raster state is rooted at
  `0x783170`: row coordinate `+0x02`, accepted count `+0x04`, overflow count `+0x06`,
  mode `+0x08`, origin `+0x0a`, scale `+0x0e`, maximum row byte count `+0x10`, and
  active flag `+0x12`. Canonical page state is the page-root bucket chain under `+0x1c`
  and encoded raster objects with class byte `0x80`, mode byte `+0x05`, capacity
  `+0x06`, packed key `+0x08`, and payload bytes at `+0x0a`. Accepted rows pass through
  `0x10084`, `0x13070`, `0x13250`, and `0x138de` to queue encoded raster objects such as
  `00 00 00 00 80 00 00 04 00 01 f0 0f aa 55`: class byte `0x80`, mode byte `0`,
  capacity `4`, packed key `0x0001`, and payload bytes at `+0x0a`. Parser scratch is
  delayed state `0x782a1a`, saved handler `0x782a1c`, snapshot bytes
  `0x782a20..0x782a25`, the restored `80 57 ...` record, payload offset and bytes, and
  skipped payload drained through `0xdace` or `0x12328`. The payload copier `0x138de`
  fetches through `0xa904` and locally normalizes `1a 58` to copied byte `00`.
  Derived/cache state is row bucket `0x782a7c`, packed key `0x782a7e`, per-object
  payload capacity `0x782a80`, orientation-derived row longword `D4`, render-record
  bucket roots copied by `0x1edc6`, and render-band destination fields. Firmware
  bookkeeping is current page root `0x78297a`, pending service bytes
  `0x782c72/0x782c73`, root active/retry bytes, stream allocator state
  `0x782a70/0x782a72/0x782a76`, allocation/copy stop flag `0x782996`, and post-transfer
  cursor advancement. `0x107fa` clears only active flag `+0x12`; while `+0x12` is set,
  `0x10808` resolution changes are ignored. Writers are `0x10808` for resolution-derived
  mode/scale, `0x1075a` for origin and active state, `0x107fa` for active clear,
  `0x11f82`/`0x121cc` for delayed transfer state, `0x105d0` for gate counts and row
  state, `0x10084` for root availability, `0x13070`/`0x13250` for row objects, and
  `0x138de` for payload bytes. Readers/consumers are `0x105d0` for the restored command
  record, `0x13070` for raster state, publication `0xff1e`, bridge `0x1ed84` /
  `0x1edc6`, bucket dispatch `0x1efc2`, and encoded raster renderer `0x1f88e`.
  Publication and rendering copy the bucket chain through `0xff1e`, `0x1ed84`, and
  `0x1edc6`; `0x1ef6a -> 0x1efc2 -> 0x1f88e` renders the object. Mode `0` copies literal
  words, while modes `1`, `2`, and `3` expand payload bytes into two, three, or four
  output rows through ROM expansion tables. The gate fixtures classify capped transfers,
  beyond-extent drains, negative rows, consecutive transfers, and active-resolution
  ignore as object or no-object outcomes before this same render path. Beyond-extent
  rows drain without ensuring a root; negative rows ensure a root, drain without
  queueing an object, and advance from row `-1` to `0`. Concrete output evidence
  includes fixtures `host-fetched raster stream reaches parser and queued pixels`,
  `host-fetched raster stream preserves 0x1edc6 bridge contract`, `0x105d0-modeled
  raster transfer skip and cap gate`, `modeled raster command stream applies 0x105d0
  byte-count cap`, `modeled raster command stream drains beyond-extent transfer without
  queueing`, `modeled raster command stream drains negative-row transfer and advances`,
  `0x13070/0x13250 raster row queues encoded-span object`, `0x1f88e mode-0 raster object
  renders queued literal row`, `0x1f88e mode-1 raster object expands queued bytes into
  two rows`, `0x1f88e mode-2 raster object expands queued byte pair into three rows`,
  `0x1f88e mode-3 raster object expands queued bytes into four rows`, and `host-fetched
  raster mode streams feed 0x1ed84 and 0x1ef6a`. Mixed composition evidence
  `host-fetched text rectangle and raster page record feeds 0x1ed84 and 0x1ef6a` and
  `addressed text/rule/raster field groups reach publication and render entry` exercises
  the documented page-root, publication, bridge, and band-render path shared by encoded
  raster objects, compact text, and rule objects. Confidence is high for delayed-record
  restore, `0x105d0` gate outcomes, root boundary, encoded object layout, bridge
  preservation, mode helpers, active-resolution behavior, lowercase `*b` chaining, dense
  capped-new-chunk/current-tail allocation through `0x132b6..0x13382`, and ROM-derived
  row construction for the cited streams. No unresolved ROM-local raster object, bridge,
  or render edge remains for the documented paths. Remaining work is new byte streams
  that expose different `0x105d8..0x10752`, `0x10084..0x10218`, `0x13070..0x13250`, or
  `0x132b6..0x13382` gate outcomes, accepted counts or drains, allocator state
  `0x782a70/0x782a72/0x782a76`, split capacity `0x782a80`, encoded object bytes
  `+0x04/+0x05/+0x06/+0x08/+0x0a..`, bridge bucket roots, copy-stop byte `0x782996`,
  packed-key advance through `0x332ee`, or mode-specific `0x1f88e` row-construction
  paths.
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
  Alternate/data `ESC *c` command records are parser scratch only: uppercase
  `A/B/G/H/P/V` rows in table `0x116f6` are blank, lowercase
  `a/b/g/h/p/v` rows call only rewind helper `0x11f4c`, and none of
  `0x10e68`, `0x10e22`, `0x10a40`, `0x10ae0`, `0x10dce`, or `0x10898` runs.
  Rectangle dimensions, fill state, source record, rule-list object, bridge
  state, and render inputs therefore do not change in alternate/data mode.
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
  object bytes, bridge state, render dispatch, or ROM-derived row construction.
- Reset, FF, page-size, page-length zero/default, orientation, paper-source,
  copies, and VFC publication paths are covered through `0xff1e` for current
  modeled page records. Page length is the publication-adjacent sibling:
  nonzero `ESC &l#P` refreshes
  geometry and later placement, while zero/default `ESC &l0P` can publish
  pending text before restoring default page state. VFC coverage includes
  `ESC &l#W` delayed table payloads, lowercase
  same-family delayed-record preservation, channel-2 forward and before-top
  jumps, selector-zero top-of-form, selector-zero page eject, wrap hit,
  wrap no-hit, target-after-text publication, and non-publishing recovery
  paths. Evidence is tracked in `notes/vertical-forms-control.md` with
  branch boundaries `0x128ae..0x128f4`, `0x12966..0x129c4`,
  `0x129c6..0x12af8`, `0x12a22..0x12a78`, and `0x129ee..0x12b5a`.
  Related publication evidence is checked in under
  [Publication Owner Summary](publication-commands.md#owner-summary),
  [publication-commands.md](publication-commands.md), and
  `Publication Commands To ROM-Derived Page Rows` in
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
  fields such as line-termination mode `0x78318f`, page length/extent
  `0x782dba`, page code `0x782da2`, pending page-size/page-length byte
  `0x782997`, copy count `0x782da4`, paper-source byte `0x782da6`, pending
  refresh byte `0x782998`, and output/control bytes `0x780e8f` /
  `0x780e26`.
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
  Covered parser-to-publication and publication-adjacent streams are `! ESC E`
  through reset handler `0xcc52`, `ESC &k2G ! FF` through `0xedf8` and
  `0xf0f0`, `! ESC &l1A` through page-size handler `0xfc74`,
  `ESC &l66P !` and `! ESC &l0P` through page-length handler `0xf9e8`,
  `! ESC &l1O` through orientation handler `0x10220`, `! ESC &l2H` through
  paper-source handler `0xef62`, and `! ESC &l2X FF` through copy-count
  handler `0xeef0` before FF publication. The command-side fields are page
  length/extent `0x782dba`, page code `0x782da2`, pending layout byte
  `0x782997`, copy count `0x782da4`, paper-source byte `0x782da6`, pending
  paper-source refresh `0x782998`, output bytes `0x780e8f` / `0x780e26`,
  orientation `0x782da3`, and geometry fields updated after
  page-size/page-length/orientation publication or placement refresh.
  VFC table load `ESC &l#W` uses `0x11f6e -> 0x121cc -> 0x12218 -> 0x12cfe`
  to consume delayed payload bytes into table `0x782dde..0x782edd`, derive
  VFC limit `0x782dc2`, copy text-bottom cache `0x782dd2`, and clear modified
  layout flag `0x782ee1`. VFC channel jumps through `0x1280a` consume that
  table, VMI `0x783160`, top offset `0x782dce`, current y `0x782c8e`, and
  line caches `0x782ede` / `0x782edf` / `0x782ee0`.
  Writers are `0xcc52`, `0xf0f0`, `0xfc74`, `0xf9e8`, `0x10220`, `0xef62`,
  and `0xeef0` for publication-triggering or publication-adjacent command
  state; `0xff1e` for published pool records; `0x11f6e` / `0x121cc` for
  delayed VFC payload scheduling; `0x12cfe` for explicit VFC table load;
  `0x12b96` and `0xe5e2` for default VFC/layout refresh; `0xfe54` for
  line-count caches; and `0x1280a`, `0xf06e`, `0xf34a`, and `0xf124` for
  cursor reset, pending-text flush, and page-boundary effects.
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
  0xeef0 pool header word`, `0xf9e8 ESC &l#P converts VMI lines to page length
  and selects internal page code`, `0xf9e8 ESC &l#P stream reaches page-length
  handler`, `mixed page-length stream refreshes cursor before printable
  page-record queue`, and `host-fetched ESC E clears missing page root without
  publication`.
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
  pool-header fields, bridge state, VFC line/cache state, or row-construction
  inputs.
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
  layout refresh through `0xe5e2`, page-root flags word `+0x14` bit 0, and
  parser reset/frame cleanup through `0x1240a`.
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
  publication, `0xff1e` consumes that state and page-root flags word `+0x14`
  bit 0; when the enabled overlay record exists, `0xe4f4` builds a
  non-replay frame with kind `+0x09 = 4`, replays the stored payload before
  the same publication boundary, and `0xe22c` restores parser/page state
  afterward. Disabled, missing-record, or retry-flag skip gates preserve the
  base page publication.
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
  ROM-derived row construction. Over-deep context nesting is already bounded
  as an unchecked ROM pointer path: eighth push ends at `0x782c6e`, ninth
  push starts at `0x782c6e`, and empty pop reads `0x782c14`; only the
  physical/user-visible symptom after adjacent RAM corruption remains
  external.
- The initial mixed page-image suite is covered for one complete host-fetched byte
  stream: `! ESC *c12a5b0P ESC *t300R ESC *r0A ESC *b2W c3 3c FF`. It drains through the
  modeled `0xa904` ring source, routes through the parser handlers above, queues compact
  text, a selector-7 rectangle rule, and a mode-0 raster object into addressed
  page-record storage, publishes through `0xff1e`, crosses the `0x1ed84` / `0x1edc6`
  render bridge, and derives the final composed rows from the documented render
  routines. Evidence: `Mixed Text/Rule/Raster Page Record` in
  `notes/semantic-state-model.md` and [Mixed Page Composition
  Checkpoint](page-record-storage.md#mixed-page-composition-checkpoint). The
  representative page root has compact/raster bucket array `+0x1c`, rule list `+0x24`,
  and context slots `+0x2c`. Addressed fixtures place the text object at `0x00d0c004`,
  rule object at `0x00d0c02a`, raster object at `0x00d0c038`, and context slot 0 as
  `0x440946b4`. Publication preserves the bucket root as `00 d0 c0 04 80 00 00 02 00 00
  c3 3c` and the selector-7 rule list as `00 00 00 00 01 07 5c 01 00 0c 00 05 00 00`.
  Parser scratch for the delayed raster transfer is restored record `80 57 00 02 00 00`,
  delayed snapshot `01 00 01 05 d0 80 57 00 02 00 00`, payload offset `28`, and payload
  `c3 3c`. Firmware allocator bookkeeping ends at `0x782a70 = 0x00bc`, `0x782a72 =
  0x00d0c000`, and `0x782a76 = 0x00d0c044`. The multi-row sibling documents bucket
  ordering for consecutive raster objects: bucket `+0x1c` chains `0x00d0d044 ->
  0x00d0d038 -> 0x00d0d004`, so render dispatch sees the second raster row, first raster
  row, then compact text, with raster `row_y = 2`. Writers are the parser handlers
  `0xd04a`, `0x10e68`, `0x10e22`, `0x10898`, `0x10808`, `0x1075a`, delayed `0x105d0`,
  and FF handler `0xf0f0`; consumers are allocator `0x1381c` / `0x1387c`, publication
  `0xff1e`, bridge `0x1ed84` / `0x1edc6`, and renderer `0x1ef6a`. Render call order is
  `0x1ef86`, `0x1efc2`, `0x1f446`, `0x1f756`, with raster chain items going to `0x1f88e`
  and compact text going to `0x1effe`.
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
  state, bridge roots, render dispatch, or ROM-derived row construction.
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
  helper dispatch, fallback splitting, or row-construction inputs.
  Confidence is high for source field meanings, paired writer behavior,
  `0x12f2e` short/segmented object shapes, selector bits, queue no-room retry,
  compact subdispatch, and row output for the cited fixtures. It remains
  medium for broader source-class cross-products. The exact unresolved ROM
  boundary is not between parser and compact renderer for the documented
  cases; it starts at new byte-stream
  variants through `0xd04a..0x12f2e` or compact helper variants through
  `0x1f034..0x1f264` that alter the object bytes or ROM-derived row
  construction.

## Canonical State Groups

- Host/input canonical state: `0x780e40`, `0x780e66`, `0x780e3b`,
  `0x783e54`, `0x783e56`, `0x783e76`, `0x783e78`, `0x783e8c`,
  `0x783e8e`, and `0x782d76` frame fields `+0x00`, `+0x04`, `+0x08`,
  `+0x09`, and `+0x0a`. Evidence:
  [host-byte-fetch.md](host-byte-fetch.md),
  `Host Byte Fetch And Data-Chain Input` in
  [semantic-state-model.md](semantic-state-model.md), and supporting report
  `generated/analysis/ic30_ic13_host_byte_fetch_flow.md`.
- Host-output/status canonical state: parser-visible model-ID response state from
  `0x12034 -> 0x122be`, literal response bytes at `0x12280..0x12288`, FIFO storage
  `0x783e92..0x783ed1`, count `0x783ed2`, read/write pointers `0x783ed4/0x783ed8`, wait
  object `0x7801e2`, backend selector `0x780e40`, page-environment status bytes
  `0x780e8e/0x780e8f`, selected page/control bytes `+6/+7/+8`, and status roots
  `0x780e12`, `0x780e0a`, `0x780e2a`, `0x780e32`, `0x780e2e`, and `0x780e36`. Evidence:
  [errors-and-status.md](errors-and-status.md), [io-interfaces.md](io-interfaces.md),
  and `Host/Status Side-Channel Decision Checkpoint` in
  [errors-and-status.md](errors-and-status.md#hoststatus-side-channel-decision-checkpoint).
- Parser state and scratch:
  canonical parser state is mode `0x782999`, command-record cursor and
  records at `0x78299e..0x7829a7`, alternate/data mode `0x782c18`, delayed
  pending flag `0x782a1a`, delayed handler pointer `0x782a1c`, and saved
  delayed record `0x782a20..0x782a25`. Parser scratch is tokenizer and
  matched-byte state while a command family is still being combined.
  Evidence: `Parser Record And Delayed Payload State` in
  [semantic-state-model.md](semantic-state-model.md), tokenizer fixtures, and
  `generated/analysis/ic30_ic13_parser_xrefs.md`. Tokenizer scratch is
  `0x782a26`, `0x782a2a..`, `0x782a3e`, `0x782a42..`, and
  `0x783196..0x783199`; firmware bookkeeping is callback pointer `0x78299a`,
  helper latch `0x782a56`, and derived font-designation records from
  `0x11efe` / `0x11f26`.
- Canonical macro/replay state: current macro id `0x783164`, macro record
  pool `0x782a98`, selected record pointer `0x782d7a`, record head/count/id
  and permanence fields, active data-chain frame pointer `0x782d76`, frame
  fields `+0x00/+0x04/+0x08/+0x09/+0x0a`, overlay mode byte `0x782a92`,
  saved overlay id `0x782a94`, and page-root retry gate in flags word
  `+0x14` bit 0. Evidence: [macro-data-chain.md](macro-data-chain.md),
  [host-byte-fetch.md](host-byte-fetch.md), and `Macro, Data-Chain, And
  Overlay` in [semantic-state-model.md](semantic-state-model.md).
- Canonical print environment: cursor words `0x782c8a` and `0x782c8e`,
  HMI/VMI words, margins, page geometry fields under `0x782da2..0x782dc0`,
  line-termination mode, cursor stack, and font slot state. Evidence:
  [direct-control-codes.md](direct-control-codes.md),
  `Text Cursor And Direct Controls`, and page-geometry fixtures, including
  the `ESC *p#X/#Y` dot-position path through handlers `0xf48c` and
  `0xf692`. Those handlers convert parsed integer dot units to packed
  whole-dot cursor coordinates with `parameter << 16`, then share the
  `0xf4ca` / `0xf6e2` commit helpers before printable output is queued.
- Canonical font/resource state: selected text slot `0x782f06`,
  current-font contexts `0x782ee6` / `0x782ef6`, active maps `0x782f32` /
  `0x783032`, requested and active symbol words, built-in or optional
  candidate windows under `0x782324` and `0x78278e..0x7827b8`, optional
  resource-window slots `0x7828b6..0x7828dd`, current downloaded-font id and
  character `0x782f2e/0x782f30`, current downloaded-font records
  `0x782640..0x782776`, installed glyph records, and bitmap payload bytes.
  Evidence: [symbol-set-selection.md](symbol-set-selection.md),
  [font-context-metrics.md](font-context-metrics.md),
  [built-in-resource-scan.md](built-in-resource-scan.md),
  [downloaded-fonts.md](downloaded-fonts.md), and
  [page-font-scheduler.md](page-font-scheduler.md#page-font-scheduler-outcome-matrix).
- Canonical page model: current page root `0x78297a`, page-root class byte
  `+4`, bucket array `+0x1c`, rule list `+0x24`, fixed-width list `+0x28`,
  context slots `+0x2c`, and stream allocator fields `0x782a70`,
  `0x782a72`, `0x782a76`. Evidence:
  [page-record-storage.md](page-record-storage.md) and
  `Shared Page-Record Storage And Allocator`.
- Canonical graphics producer state: rectangle width/height/fill
  `0x78316a`, `0x783166`, and `0x78316e`; rectangle source record
  `0x782a88`; raster block `0x783170` with baseline, row, accepted/drain
  counts, mode, origin, scale, byte limit, and active byte; encoded raster
  object fields `+0x04/+0x05/+0x06/+0x08/+0x0a..`; and rule-list object
  fields selector/key/width/height/continuation. Evidence:
  [rectangle-graphics.md](rectangle-graphics.md),
  [raster-graphics.md](raster-graphics.md), and
  [page-raster-imaging.md](page-raster-imaging.md).
- Canonical publication/render state: publication flag `0x782996`,
  published source pointer `0x780ea6`, active source pointer `0x780eae`,
  render-record roots `+0x18/+0x1c/+0x20`, render context slots, active
  render pointer `0x783a18`, compact/raster/rule/fixed dispatch roots, and
  render entry `0x1ef6a`. Evidence:
  [publication-commands.md](publication-commands.md),
  [active-render-scheduler.md](active-render-scheduler.md), and
  [page-raster-imaging.md](page-raster-imaging.md).
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
  [resource-rom.md](resource-rom.md#resource-rom-outcome-matrix), and
  [built-in-resource-scan.md](built-in-resource-scan.md).

## Pixel-Perfect Coverage And Residual Risks

These are the highest-value coverage areas and residual risks because each can
change rendered pixels, byte-stream compatibility, or final confidence. Most
entries below are composed ROM contracts with bounded remaining variants rather
than open middle edges.

The baseline printable-byte contract is the `!!` stream in
`Minimal Stream Walkthrough: !!` plus the printable-text entry in
`Supported Stream Entry Points`: normalized bytes `21 21` reach
`0xa904 -> 0xda9a -> 0x11774 -> 0xd04a`, build flagged `LINE_PRINTER`
sources through `0x1393a` / `0xd824`, queue compact object
`00 00 00 00 00 00 00 02 20 00 01 20 02 02` through
`0x12f2e -> 0x1387c`, publish via `0xff1e`, bridge via
`0x1ed84 -> 0x1edc6`, and render through
`0x1ef6a -> 0x1efc2 -> 0x1effe -> 0x1f034 -> 0x1f354` with row-copy helper
table `0x1fa5c`. This is the reference byte-to-pixel spine for later command
families that only change parser state, selected context/map, page-object
shape, publication boundary, or render helper inputs.

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
   object, or row-construction input; HP/manual field naming remains external.
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
   [Macro Replay Outcome Matrix](macro-data-chain.md#macro-replay-outcome-matrix),
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
   `0xe22c`, page-root flags word `+0x14` bit 0, and page publication state.
   Execute/call selectors build replay frames through `0xe418`: frame byte
   `+0x09` is `2` for execute and `3` for call. `0xa904` gives those frames
   priority over live host bytes, so stored payloads re-enter parser loop
   `0x11774` and reach ordinary handlers such as `0xd04a`, `0xf02c`, and
   `0xedf8`. Overlay selector `4` is consumed during publication:
   `0xff1e` checks `0x782a92`, saved id `0x782a94`, and root flags word
   `+0x14` bit 0; if replay is enabled, `0xe0a4` reselects the macro and
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
   page-object fields, delayed payload state, replay frame state, or
   row-construction inputs.
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
   against a published downloaded-glyph record. The [Scheduler Outcome
   Matrix](active-render-scheduler.md#scheduler-outcome-matrix) makes that
   band contract explicit: only the capacity-approved branch
   `0x1ec8e..0x1ecac` calls `0x1ef6a`; cleanup, stale-work,
   throttle-yield, and capacity-wait branches are no-pixel scheduler outcomes
   for that iteration. `Band Scheduling Route Index` in
   [firmware-dataflow-model.md](firmware-dataflow-model.md#band-scheduling-route-index)
   groups the same publication, source-selection, work-record, band-loop, and
   renderer-handoff fields as a checked-in reader path.
   The remaining scheduler risk is not a ROM object/rendering middle edge: it is
   board-level timing for `$8000.4`
   selection at `0x0f84..0x0fa0` and `0x1020..0x102e`, MMIO effects around `$a601 =
   0xfd`, `$a801`, `$aa01`, `0xfffe0001`, and `0xfffe0003`, and the physical event
   timing that drives modeled wait-object/trap states through `0x10bc..0x11f8` and
   `0x123a..0x1282`. Evidence: `Published Record To Active Render Scheduler` in
   `notes/semantic-state-model.md` and `Active Render Scheduler` in
   `notes/page-raster-imaging.md`.
5. Downloaded font support is now documented as one command-to-output cluster instead of
   isolated handler notes. The low-level ledger remains in
   [downloaded-fonts.md](downloaded-fonts.md), with composed checkpoints in
   [semantic-state-model.md](semantic-state-model.md) under `Downloaded Font Descriptor
   And Payload Chain`, `Downloaded Character Route Checkpoint`, `Nonzero Resource
   Payload Checkpoint`, and `Fixed-Record Resource Object Checkpoint`, plus
   [Fixed-Record Render Decision
   Checkpoint](downloaded-fonts.md#fixed-record-render-decision-checkpoint) and
   [Inline/Downloaded Compact Render
   Path](downloaded-fonts.md#inline-downloaded-compact-render-path) in
   [downloaded-fonts.md](downloaded-fonts.md).

   Command and resource route:

   - Parser dispatch reaches `0x11f96` for restored `ESC )s#W` records.
     Count `0` schedules descriptor handler `0x15d0a`; nonzero counts schedule
     delayed payload handler `0x16c14`.
   - The nonzero resource path validates descriptor bytes at `0x16fae`, builds
     resource payloads through `0x17026` / `0x1719c`, inserts candidates through
     `0x16c14` / `0x1bc38`, selects maps through `0x14c64`, and installs
     downloaded characters through `0x16498`.
   - The zero-count bit-30-clear fixed-record path is separate: current-record
     success follows `0x15e42 -> 0x16606 -> 0x15dcc -> 0x12328`, while
     continuation success follows `0x15e64 -> 0x15c4c -> 0x15dcc -> 0x12328`.
   - Release and replacement cleanup are documented at `0x1887a` for the
     bit-30-clear extended fixed-record case plus the direct bit-30-set
     class-one, bit-30-set class-zero, and bit-30-clear class-zero release
     branches.

   Visible/page-output route:

   - Installed payloads feed the normal printable path: `0xd04a` /
     `0x1393a` build source objects from the selected font map, `0xd4ac` and
     `0xd8fc` consume descriptor metrics, `0x12f2e` queues compact page
     objects, `0xff1e` publishes the page record, and `0x1ed84` /
     `0x1edc6` / `0x1ef6a` dispatch rendering.
   - The inline/downloaded fixed-record route is not a separate renderer:
     `0x14c64` / `0x14e24` rebuild selected maps, `0x1393a` captures the
     current-font context longword from `0x782ee6` / `0x782ef6`,
     `0x12f2e` chooses compact, compact-wide, segmented, or segmented-wide
     object shapes from source dimensions, and `0x1f354` resolves the fixed
     record through the render-record context slot copied by `0x1edc6`.
   - Covered ROM-derived object shapes include type-0, type-1, and type-2
     resource headers; normal, wide/control, even-span wide, short row-count,
     segmented row-count, split-plane segmented, segmented-wide, and
     segmented-wide high-row downloaded glyphs; and rule/raster composition
     after a downloaded glyph has been installed.
   - Selector words `0x0003`, `0x1003`, `0x2003`, and `0x3003` are tied to
     compact short, compact-wide, segmented, and segmented-wide downloaded
     glyph output. The relevant render helpers are `0x1effe`, `0x1f0d2`,
     `0x1f1f0`, `0x1f264`, and current-band/fallback writer `0x1fe76`.
   - The byte-24 install-to-page handoff is a single `0xa904` ring stream split
     into font bytes `0..24` and page bytes `24..54`. The installed glyph is
     `0x29`, table entry `0x00ee`, record delta `0x0780`, bitmap offset
     `0x078c`, and `18` copied bitmap bytes before the following page commands
     consume the same byte source.

   State classification:

   - Canonical state: current font id `0x782f2e`, current character
     `0x782f30`, current-record pool `0x782640..0x782776`, candidate windows
     and counts, installed glyph table entries, glyph record bytes, bitmap
     payload bytes, selected resource/context longwords, page roots, page
     objects, and bucket lists.
   - Derived/cache state: maps selected by `0x14c64` / `0x14e24`, selector
     words `0x0003` / `0x1003` / `0x2003` / `0x3003`, row/span products,
     bucket words, render helper targets, and scheduler-produced band words
     `0..9` for published downloaded-glyph records.
   - Parser scratch: restored six-byte `ESC )s#W` records, payload budget
     `0x783140`, descriptor scratch `0x7827de..0x7827e9`, optional symbol
     staging `0x782842..0x782851`, count/span/row scratch, and the split
     between font payload bytes and following page bytes.
   - Firmware bookkeeping: allocation/release status, replacement teardown,
     continuation save/resume state, copy status, `0x12328` drain state,
     publication status, and current-root clearing.
   - Hardware/external state: none for the documented ROM-local downloaded-font
     command and render paths. Optional cartridge/external resource-window
     contents remain separate from these local payload installs.
   - Unknown: HP/manual names for consumed-but-not-staged validation fields;
     execution after documented invalid compact-helper jumps, such as wrapped
     source-width span `0x0102` selecting `0x0066cc` through `0x1f034` /
     `0x1f08e`, where the target is control/status code rather than a
     row-copy helper; and any future glyph row/span or continuation variant
     only if it changes a documented field, object, bridge state, or
     row-construction helper.

   Return and drain boundaries:

   - Full-success downloaded-character installs take
     `0x15dc6 -> 0x16498 -> 0x15dcc -> 0x12328`. The byte-24 handoff instance
     has copy status `1`, copy stream position `18`, remaining
     `0x783140 = 0`, zero drain, and next parser handler `0x10e68`.
   - Normal, row-`0x80`, linear-segmented, split-plane segmented, and
     segmented-wide publication siblings also leave `0x783140 = 0`, drain zero
     bytes through `0x12328`, and resume at handler `0xd04a`.
   - The payload-control wide sibling leaves `0x783140 = 1`, drains byte
     `0x26`, and leaves the following FF for handler `0xf0f0`.
   - No-install and rejection paths preserve the following printable/default
     page path. The visible no-install boundary leaves `0x783140 = 6`, drains
     six rejected bytes, and resumes at handler `0xd04a`; the status-`2`
     partial-install boundary leaves `0x783140 = 0`, drains zero bytes, and
     resumes at handler `0xd04a`.

   Evidence:

   - Disassembly:
     `generated/disasm/ic30_ic13_font_payload_setup_015b80.lst`,
     `generated/disasm/ic30_ic13_font_resource_validate_016fae.lst`,
     `generated/disasm/ic30_ic13_font_payload_descriptor_helpers_016a10.lst`,
     `generated/disasm/ic30_ic13_font_resource_find_017026.lst`,
     `generated/disasm/ic30_ic13_font_resource_payload_initializer_01719c.lst`,
     `generated/disasm/ic30_ic13_font_resource_object_add_016c14.lst`,
     `generated/disasm/ic30_ic13_font_candidate_object_alloc_01bc38.lst`,
     `generated/disasm/ic30_ic13_font_payload_object_path_016040.lst`,
     `generated/disasm/ic30_ic13_font_payload_readers_0168dc.lst`,
     `generated/disasm/ic30_ic13_font_payload_readers_016874.lst`,
     `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`, and
     `generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst`.
   - Checked-in notes:
     [Downloaded-Font Outcome
     Matrix](downloaded-fonts.md#downloaded-font-outcome-matrix),
     [semantic-state-model.md](semantic-state-model.md),
     `Downloaded-Glyph Render Decision Checkpoint` in
     [downloaded-fonts.md](downloaded-fonts.md#downloaded-glyph-render-decision-checkpoint),
     `Fixed-Record Render Decision Checkpoint` in
     [downloaded-fonts.md](downloaded-fonts.md#fixed-record-render-decision-checkpoint),
     `Descriptor Metric Semantic Checkpoint` in
     [font-context-metrics.md](font-context-metrics.md), and worked paths
     `Downloaded Glyph`, `Downloaded Glyph Rule/Raster Composition`,
     `Nonzero Resource Payload`, and `Fixed-Record Resource Object` in
     [firmware-dataflow-model.md](firmware-dataflow-model.md).
   - Fixture evidence is cited only as reproducible ROM-path support. The
     named families cover validation/no-install exits, type-1/type-2 resource
     publication, row-count and wide/segmented/segmented-wide glyph forms,
     fixed-record current/continuation routes, release routes, byte-24 handoff,
     rule/raster composition, and active scheduler band words. They are not an
     external rendered-row oracle.
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

## Next Documentation Targets

The next work should add checked-in explanation for byte-stream dataflow, not
standalone fixture output and not isolated handler traces. A new trace is worth
opening only when it changes a named parser field, command-family state field,
page/image object byte, publication or bridge field, render-helper input, or an
exact unresolved boundary. The low-level ledger can grow underneath that work,
but the checkpoint is complete only when the owner note and this map let a
reader follow what the ROM does.

Priority ROM-local documentation targets:

1. Command-family variants that change page-object shape or render input. Useful
   remaining examples should start from `Command-Family To Page-Object Crosswalk` in
   [firmware-dataflow-model.md](firmware-dataflow-model.md#command-family-to-page-object-crosswalk)
   and then change one of the concrete render-helper fields named in [Render Helper
   Boundary Index](page-raster-imaging.md#render-helper-boundary-index) and the
   producer/root/object/bridge fields summarized by `Page Object Shape Route Index` in
   [firmware-dataflow-model.md](firmware-dataflow-model.md#page-object-shape-route-index):
   scheduler-only variants should use `Band Scheduling Route Index` in
   [firmware-dataflow-model.md](firmware-dataflow-model.md#band-scheduling-route-index)
   as the already-covered publication-to-renderer handoff boundary. Remaining variants
   should change compact selector class, segment/fixed-list object bytes, raster encoded
   object fields, rule/fixed roots, continuation mutation, fallback split, or row-copy
   helper inputs. Compact-selector streams should start only when they change source
   bytes consumed by `0x12f2e`, selector bits, segment payload entries, helper target,
   fallback split, row-copy index, or an exact boundary beyond the [compact selector
   outcome matrix](downloaded-fonts.md#compact-selector-outcome-matrix). Segment-list
   portrait-span streams should start only when they change key derivation, split
   buckets, entry bytes, bucket bridge state, a new allocation-failure publication/retry
   outcome, or row construction beyond the [segment-list outcome
   matrix](page-record-storage.md#segment-list-outcome-matrix). Fixed-list
   landscape-span streams should start only when they change key derivation, insertion
   order, object bytes, bridge continuation fields, five-band gating, or row
   construction beyond the [fixed-list outcome
   matrix](page-record-storage.md#fixed-list-outcome-matrix). Raster streams should
   start only when they change accepted-byte counts, row advancement, object bytes, or
   render inputs beyond the [raster transfer gate outcome
   matrix](raster-graphics.md#transfer-gate-outcome-matrix) or [encoded raster object
   outcome matrix](raster-graphics.md#encoded-raster-object-outcome-matrix). Rule-list
   streams should start only when they change clipped source fields, ordered insertion,
   object bytes, bridge continuation fields, selector dispatch, or row construction
   beyond the [rule-list outcome
   matrix](page-record-storage.md#rule-list-outcome-matrix). Rectangle streams should
   start only when they change the boundaries named in [Remaining
   Edges](rectangle-graphics.md#remaining-edges): clipping output, `0x1381c`
   rollover/allocation state, retry publication fields, rule object bytes, bridge state,
   render dispatch, continuation mutation, or row construction. Publication examples for
   reset, FF, page-size, orientation, paper-source, and copies are now owned by [Page
   Environment Outcome Matrix](publication-commands.md#page-environment-outcome-matrix);
   new publication work should start only from streams that change pool-header fields,
   source-record selection, bridge values, or a render helper input. The allocator
   rollover path across `0x10084`, `0x1381c`, `0x1387c`, `0x133aa`, and `0x136d2` is now
   owned by [page-record-storage.md](page-record-storage.md#output-effect), including
   concrete stream chunks, object addresses, final cursors, and downstream render
   consumers. New allocator work should start only from byte streams that change the
   root topology, object shape, no-room/retry state, or bridge fields. The owner update
   must name the handler, fields written, later consumers, page-object bytes or
   no-output outcome, and the first render boundary reached.
2. Parser-to-family route work should start only from an exact missing row/stream, not
   from the parser tables in the abstract. The current checked-in parser audit assigns
   the supported rows in [Supported Stream Dispatch
   Matrix](pcl-command-map.md#supported-stream-dispatch-matrix) and the `ROM Semantic
   Index For Quick Reference` in
   [pcl4-language.md](pcl4-language.md#rom-semantic-index-for-quick-reference) to owner
   notes; no known supported command family is intentionally left at table ownership
   only. New parser work is useful when a specific byte stream changes a parser outcome
   class, delayed-payload restore, alternate/data append, owner handler, RAM field
   write, downstream reader, page-object field, or state-only consumer that is not
   already named by those indexes. Generated dispatch rows remain supporting evidence;
   the deliverable is still the checked-in owner route from admitted bytes to state,
   page output, or an explicit no-output/status outcome.
3. Page-image composition cases that add a new object class interaction.
   Extend the mixed text/rule/raster and downloaded-glyph composition paths
   only when the stream changes root ordering, bucket/list selection, bridge
   roots, scheduler band words, row-helper dispatch, or direct-store
   composition. Do not repeat already-composed text/rule/raster,
   downloaded-font, font-selection, VFC, macro, or publication streams only to
   produce another digest.
4. State-only commands whose pixel effect is delayed. The documentation should
   connect the command's canonical field write to the later consumer that makes
   it visible: for example layout fields consumed by printable placement,
   raster origin/bounds, rectangle clipping, publication, or page overflow. If
   no later consumer is known, record that exact field and consumer boundary
   instead of treating the command as visually complete. SO/SI selected-context
   switching, printable source capture, cursor-stack push/pop, and the documented
   layout writers are now
   owned by [Direct-Control Outcome
   Matrix](direct-control-codes.md#direct-control-outcome-matrix); new state-only
   work should start only when a stream changes a canonical field, downstream
   consumer, page-object field, compact source/object field beyond the
   [printable source outcome
   matrix](direct-control-codes.md#printable-source-outcome-matrix), or exact
   boundary not named by those checkpoints.

Edges that should not drive more ROM tracing unless new evidence changes a
named upstream field:

1. Transparent secondary segment-57 resource decode is the current
   pixel-affecting missing-data boundary, but the ROM path is already traced.
   The parser, filtering, page-record, bridge, and renderer route is
   documented in [Transparent Payload Decision
   Checkpoint](transparent-print-data.md#transparent-payload-decision-checkpoint)
   and [Secondary Segment-57 Resource
   Source](unresolved-boundaries.md#secondary-segment-57-resource-source).
   The unresolved input is physical/resource-window data for firmware range
   `0x0c0000..0x0c0321`, after verified resource-pair suffix
   `0x0bfe22..0x0bffff`. Do not re-trace `0x12452`, transparent filtering,
   secondary buckets through `448`, or compact renderer arithmetic unless new
   decode evidence contradicts that boundary.
2. Reset/default provenance is no longer a ROM-local parser/page/render gap.
   [reset-default-environment.md](reset-default-environment.md#reset-default-outcome-matrix)
   and `Default Environment Record Producers` cover the reset consumer, default
   backing-record producers, retained-record helpers, page-root publication, HMI/VMI
   conversion, and addressed compact-bucket publication. Remaining work is external
   naming or physical correlation for retained storage, service conditions, folded
   status categories, and self-test placement.
3. Font metrics, font selection, downloaded-glyph row/span publication, and
   macro overlay replay are composed checkpoints. Additional cases are useful
   only when they change copied metric fields, a consumer branch, selected
   context or map, page-root slot behavior, downloaded-glyph selector/helper
   dispatch, `0x783140` remainder, `0x12328` drain status, replay frame state,
   delayed payload state, page-object bytes, bridge roots, or row-construction
   inputs.
4. Final physical correlation remains separate from ROM-local documentation.
   The current model derives rows from ROM disassembly, resource bytes,
   page-record fields, and render helpers. A representative physical print, if
   one is ever used, can only correlate that model with a device; it is not an
   oracle for the documentation and is not a substitute for static ROM
   evidence. Fixture output is likewise only a ROM-local branch or
   transcription check; the deliverable is the documented path that constructs
   rows.
