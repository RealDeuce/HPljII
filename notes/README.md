# HP LaserJet II ROM Disassembly Notes

These notes summarize the local PDF set into emulator-oriented
references. They focus on the HP 33440 / LaserJet Series II unless a
LaserJet III detail is explicitly called out as shared hardware or a
compatibility boundary.

Evidence policy: firmware claims in this directory are grounded first in ROM
bytes, disassembly, decoded tables, static cross-references, and RAM fields
read or written by those instructions. Fixture scripts and generated reports
are supporting checks for the documented interpretation; they do not represent
runtime observation of a real printer or an executing ROM. When older notes
describe evidence strength, read that as a statement about the cited static
disassembly, field writes, and decoded data, not as hardware-emulation
validation.

Fixture row vectors are ROM-derived artifacts: they should be cited as
documented consequences of decoded object fields, bitmap bytes, and render
helpers. They are not comparisons against real printer output, an executed ROM,
or any other external pixel reference. A fixture may prove that a byte stream
reaches a documented branch or helper transcription, but it does not strengthen
pixel claims by comparison. Pixel claims must cite the ROM fields, handlers,
and render helpers that produce those rows.

## Controlling Documentation Spine

For a concrete host byte stream, the checked-in owner notes are the controlling
artifact. Generated listings and fixture logs support those notes; they are not
standalone deliverables.

The generated text evidence cited by these notes is also checked in when it is
small and reviewable: focused disassembly listings under `generated/disasm/*.lst`
and generated analysis reports under `generated/analysis/*.md`. Bulk generated
outputs, raw ROM-derived payload dumps, and ROM images remain local-only.

- Host bytes enter through [host-byte-fetch.md](host-byte-fetch.md#owner-summary),
  which documents `0xa904` source priority, data-chain replay, direct host
  paths, and the normalized byte returned in `D7`. Its
  [D7 Caller Return Contract](host-byte-fetch.md#d7-caller-return-contract)
  is the handoff from byte admission to parser wrappers, direct payload
  readers, display/transparent readers, raster data, downloaded-font payloads,
  and macro/data-chain replay; the central state checkpoint is
  [D7 Caller Return Checkpoint](semantic-state-model.md#d7-caller-return-checkpoint).
- Parser state is owned by
  [pcl-parser-core.md](pcl-parser-core.md#owner-summary): parser mode
  `0x782999`, command-record cursor `0x78299e`, six-byte parsed records,
  normal/alternate tables, and delayed payload restore
  `0x121cc -> 0x12218`. Its `Inbound Byte Outcome Contract` is the branch-level
  owner for deciding whether a normalized byte becomes printable output,
  alternate/data append, a matched command handler, a zero-handler reset, a
  no-match fallback, callback continuation, or parser-external return.
- Command dispatch is indexed by
  [pcl-command-map.md](pcl-command-map.md#reproduction-contract):
  parser rows are classified as prefix/setup state, terminal handler
  handoff, delayed-payload setup/restore, explicit no-output row,
  alternate/data append, or service/no-match/callback outcome before a
  command-family owner is selected. Individual command families then move to
  owner notes such as
  [direct-control-codes.md](direct-control-codes.md#owner-summary),
  [publication-commands.md](publication-commands.md#owner-summary),
  [display-functions.md](display-functions.md#owner-summary),
  [transparent-print-data.md](transparent-print-data.md#owner-summary),
  [font-context-metrics.md](font-context-metrics.md#owner-summary),
  [symbol-set-selection.md](symbol-set-selection.md#owner-summary),
  [errors-and-status.md](errors-and-status.md#owner-summary),
  [raster-graphics.md](raster-graphics.md#owner-summary),
  [rectangle-graphics.md](rectangle-graphics.md#owner-summary),
  [downloaded-fonts.md](downloaded-fonts.md#owner-summary),
  [macro-data-chain.md](macro-data-chain.md#owner-summary), and
  [vertical-forms-control.md](vertical-forms-control.md#owner-summary).
  Those notes, not generated tables, own parsed inputs, RAM fields,
  downstream consumers, page/output effects, cited evidence, and exact
  residual boundaries for the selected terminal handler.
- Manual PCL command names and syntax rows are indexed by
  [pcl4-language.md](pcl4-language.md#owner-summary). Its ROM Semantic Index maps PCL
  Level IV families to first parser handlers, representative byte streams, page-object
  bytes or state fields, render routes, and owner notes.
- Page/image assembly is owned by
  [page-record-storage.md](page-record-storage.md#owner-summary): current root
  `0x78297a`, compact/raster buckets at root `+0x1c`, rules at `+0x24`, fixed-list
  objects at `+0x28`, context slots at `+0x2c..+0x68`, and publication through `0xff1e`.
  The page-shape contract is [Page Image Shape And Band
  Contract](page-record-storage.md#page-image-shape-and-band-contract): parsing builds a
  typed page-root object graph, publication/bridge create render roots, and scheduler
  band calls derive the row buffers. The renderer-facing lifetime summary is [Page Image
  Assembly Checkpoint](page-raster-imaging.md#page-image-assembly-checkpoint):
  parser-time page objects are canonical state, while `0x1ef86` band caches are derived
  render state. For the shortest object-class route from producer to first renderer, use
  `Page Object Shape Route Index` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md#page-object-shape-route-index).
- Rendering is owned by
  [active-render-scheduler.md](active-render-scheduler.md#owner-summary) and
  [page-raster-imaging.md](page-raster-imaging.md#pixel-generation-owner-summary):
  published-record scheduling, active render pointer `0x783a18`, bridge
  `0x1ed84` / `0x1edc6`, render entry `0x1ef6a`, compact
  text/downloaded-glyph helpers, rule/fixed-list helpers, and encoded raster
  helper `0x1f88e`. The shortest publication-to-renderer handoff is
  `Band Scheduling Route Index` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md#band-scheduling-route-index).
  The shared row-store order, current-band/fallback destination model, and
  overwrite composition rule are in
  [Pixel Composition Checkpoint](page-raster-imaging.md#pixel-composition-checkpoint).
- The broad host-byte-to-pixel walkthrough and residual-boundary index is
  [end-to-end-reproduction-map.md](end-to-end-reproduction-map.md). Its
  [Objective Coverage Matrix](end-to-end-reproduction-map.md#objective-coverage-matrix)
  maps the active documentation requirements to the checked-in owner notes and
  concrete ROM address boundaries. The unified semantic field index is
  [semantic-state-model.md](semantic-state-model.md), and the detailed dataflow spine is
  [firmware-dataflow-model.md](firmware-dataflow-model.md). Its
  `Inbound Byte Route Matrix`, `Minimal End-To-End Example`, parser
  command-dispatch anchors, `Binary Payload Lifecycle`, `State-Only Command
  Dependency Map`, `Parser Artifact And No-Output Boundary`,
  `Transparent And Display Reader Boundary`,
  `Page Geometry And Layout State Boundary`,
  `Host/Status Side-Channel Boundary`,
  `Publication And Page-Control Boundary`,
  `Font Context And Glyph Source Boundary`,
  `Symbol Set And Map Patch Boundary`, `Page Versus Band Model`,
  `Render Scheduling`, `Pixel composition contract`, and
  `Boundary: Secondary Segment-57 Source` are the shortest checked-in path
  from an admitted byte stream to page objects, rendered pixels, and exact
  pixel-affecting stop points.
- Resource bytes are owned by [resource-rom.md](resource-rom.md#owner-summary) and
  [built-in-resource-scan.md](built-in-resource-scan.md#owner-summary). The verified
  `IC32,IC15` pair supplies built-in resource bytes through firmware address
  `0x0bffff`; the transparent secondary segment-57 continuation rule in
  [resource-rom.md](resource-rom.md#owner-summary) is the owner for the remaining
  pixel-affecting resource boundary at `0x0c0000..0x0c0321`.
- Exact remaining stop points are indexed in
  [unresolved-boundaries.md](unresolved-boundaries.md), grouped as ROM-local
  invalid-target/source, ROM-local unresolved caller, missing external
  resource data, hardware/MMIO, optional external data, or manual/physical
  correlation.

## Stream Trace Workflow

Use this short route when reading a supported PCL byte stream through the
checked-in ROM model:

0. Establish the ROM-visible baseline. For power-on/default-state streams, start from
   [firmware-startup.md](firmware-startup.md#owner-summary): host byte-source buffers
   `0x783e54..0x783e8e`, output FIFO `0x783ed2` / `0x783ed4` / `0x783ed8`, heap fields
   `0x780e86` and `0x783972..0x783988`, render-work selector seeds `0x7820bc` /
   `0x7820c0`, and wait-object records `0x780182..0x780262`. For streams that include
   `ESC E`, use
   [reset-default-environment.md](reset-default-environment.md#owner-summary): reset
   publishes or clears the current root before rebuilding environment fields,
   parser/data-chain state, VMI/HMI, raster state `0x783170`, and page/control pool
   records. Physical MMIO names, retained-storage identity, and optional extension
   contents are boundaries unless they change one of those ROM-visible fields.
1. If starting from a manual command name, use the ROM Semantic Index in
   [pcl4-language.md](pcl4-language.md#owner-summary) to find the command-family route
   and concrete stream anchor. If starting from raw bytes, use
   [Reader Entry Points](end-to-end-reproduction-map.md#reader-entry-points) and
   [Stream Trace Procedure](end-to-end-reproduction-map.md#stream-trace-procedure). For
   the compact route through the current spine, start with
   [Inbound Byte Route Matrix](firmware-dataflow-model.md#inbound-byte-route-matrix) and
   [Minimal End-To-End Example](firmware-dataflow-model.md#minimal-end-to-end-example).
2. Start with byte admission in [host-byte-fetch.md](host-byte-fetch.md#owner-summary):
   classify each byte source at `0xa904` as live/ring input, pushback,
   macro/data-chain replay, or a payload reader's direct fetch. Then use its
   [D7 Caller Return Contract](host-byte-fetch.md#d7-caller-return-contract)
   to decide whether the returned byte is parser syntax, counted payload data,
   a direct display/transparent byte, raster data, downloaded-glyph bitmap
   data, or replayed input. The state-model counterpart is
   [D7 Caller Return Checkpoint](semantic-state-model.md#d7-caller-return-checkpoint).
3. Classify the parser outcome in [Admitted Byte Outcome
   Bridge](end-to-end-reproduction-map.md#admitted-byte-outcome-bridge), then
   [pcl-parser-core.md](pcl-parser-core.md#owner-summary): follow `0xda9a` / `0xdaf0` /
   `0xdb74` into parser loop `0x11774`, preserving parser mode `0x782999`, six-byte
   records at `0x78299e..`, alternate/data flag `0x782c18`, and delayed restore `0x121cc
   -> 0x12218`. For counted binary payload commands, use [Binary Payload
   Lifecycle](firmware-dataflow-model.md#binary-payload-lifecycle) and [Stream Trace
   Procedure](end-to-end-reproduction-map.md#stream-trace-procedure) to split normal
   restore from alternate/data restore: normal restore calls saved handlers such as
   `0x12452`, `0x12cfe`, `0x105d0`, `0x15d0a`, or `0x16c14`, while alternate/data
   restore routes positive payload bytes through `0x12358 -> 0xdace -> 0xe002` as stored
   macro/data-chain input with no immediate page-object or render effect. For
   definition-mode or replayed bytes, use [Alternate/Data And Macro Replay
   Boundary](firmware-dataflow-model.md#alternatedata-and-macro-replay-boundary) before
   jumping to the family owner. For explicit ignored rows, wrapper artifacts, or generic
   counted drains, use [Parser Artifact And No-Output
   Boundary](firmware-dataflow-model.md#parser-artifact-and-no-output-boundary).
4. Use [pcl-command-map.md](pcl-command-map.md#owner-summary) only as the dispatch
   index. After a terminal handler is named, continue in the family owner note for
   parsed inputs, RAM writers, readers/consumers, output effect, and residual boundary.
   If the owner classifies the route as host/status, explicit no-output,
   generic drain, append-only storage, or status-only behavior, preserve the
   named FIFO/status/report/parser/append state and stop page-image traversal
   until a later admitted byte reaches a page-producing owner. Terminal
   report routes stop at `0x1284` / `0x128c -> 0x158c -> 0x8c7a` and cached
   report bytes `0x783ef0..0x783ef1`, as owned by
   [errors-and-status.md](errors-and-status.md#hoststatus-outcome-matrix).
   The parser command-dispatch anchors in
   [firmware-dataflow-model.md](firmware-dataflow-model.md) summarize the common
   terminal-handler handoffs before the full flattened table. The `Command Family Owner
   Matrix` in the same file gives the compact handler-to-owner handoff and output class
   for each command family. For text/font routes, use `Font Context And Glyph Source
   Boundary` to connect selected contexts and maps to printable source objects, and use
   `Symbol Set And Map Patch Boundary` when `ESC (` / `ESC )`, final `X`, or final `@`
   changes requested symbols, maps, or `0x14f16` patching. Then use `Downloaded Glyph
   Boundary Decision Rules` for downloaded-glyph helper and payload stop points. For
   transparent/display readers, use `Transparent And Display Reader Boundary` before
   crossing into text output, alternate/data append, or status behavior. For layout
   routes, use `Page Geometry And Layout State Boundary` to connect page-length, VMI,
   LPI, top-margin, text-length, wrap, and perforation commands to later placement,
   overflow, publication, and render effects. For raster and rectangle routes, use
   `Raster And Rectangle Graphics Object Boundary` to connect graphics setup and payload
   commands to page objects and render helpers. Dispatch handoff should be concrete:
   [publication-commands.md](publication-commands.md#owner-summary) owns reset, FF,
   page-size, page-length zero/default, orientation, paper-source, copies, and the
   `0xff1e` publication boundary;
   [display-functions.md](display-functions.md#owner-summary) owns `ESC Y`, local
   Control-Z variants, alternate/data append, and `ESC z` status behavior;
   [errors-and-status.md](errors-and-status.md#owner-summary) owns `ESC *r#K`,
   `ESC *s#^`, host-output FIFO/status bytes, and terminal report sinks
   `0x1284` / `0x128c`;
   [font-context-metrics.md](font-context-metrics.md#owner-summary) owns font request
   refresh, page-root context slots, glyph maps, printable source fields, and span
   metrics; and [symbol-set-selection.md](symbol-set-selection.md#owner-summary) plus
   [symbol-map-patching.md](symbol-map-patching.md#owner-summary) own `ESC (` / `ESC )`,
   final `X`, final `@`, requested symbol words, and map patching before later printable
   bytes reach `0xd04a`. The checked-in dispatch tables to use at this boundary are
   [Dispatch Class Checkpoint](pcl-command-map.md#dispatch-class-checkpoint), [Parser
   Handler Owner Matrix](pcl-command-map.md#parser-handler-owner-matrix), and [Supported
   Stream Dispatch Matrix](pcl-command-map.md#supported-stream-dispatch-matrix).
5. When a command creates visible page content, cross into
   [page-record-storage.md](page-record-storage.md#owner-summary): compact/raster
   buckets live under root `+0x1c`, rules under `+0x24`, fixed-list objects under
   `+0x28`, and context slots under `+0x2c..+0x68`. The shared `Shared Page-Object
   Contract` in [end-to-end-reproduction-map.md](end-to-end-reproduction-map.md) is the
   route index for these common object fields. [Page Image Shape And Band
   Contract](page-record-storage.md#page-image-shape-and-band-contract) is the storage
   owner answer for what the "page image" is: current root, bucket/rule/fixed/context
   roots, publication, bridge roots, band caches, fallback buffer, and renderer order.
   `Page Versus Band Model` in [firmware-dataflow-model.md](firmware-dataflow-model.md)
   is the concise explanation of why parsing builds a page-object graph rather than a
   full-page bitmap.
6. For publication and scheduling, follow `Publication And Page-Control Boundary` and
   `Render Scheduling` in [firmware-dataflow-model.md](firmware-dataflow-model.md), then
   follow `0xff1e` into the page/control pool and
   [active-render-scheduler.md](active-render-scheduler.md#owner-summary): scheduler
   source `0x780eae`, active render pointer `0x783a18`, and bridge `0x1ed84 -> 0x1edc6`.
   `Band Scheduling Route Index` in
   [firmware-dataflow-model.md](firmware-dataflow-model.md#band-scheduling-route-index)
   is the handoff map from page roots to render roots, band word, and first renderer
   consumers.
7. For pixels, finish in
   [page-raster-imaging.md](page-raster-imaging.md#pixel-generation-owner-summary):
   render entry `0x1ef6a`,
   bucket dispatch `0x1efc2`, rule dispatch `0x1f446`, fixed-list dispatch
   `0x1f756`, and helper-specific row construction. The shared
   `Render Helper Boundary Index` in
   [end-to-end-reproduction-map.md](end-to-end-reproduction-map.md) names the
   common helper order, buffer destinations, and exact ROM-local render
   boundaries. The `Pixel composition contract` in
   [firmware-dataflow-model.md](firmware-dataflow-model.md) summarizes render
   call order, active-band and fallback buffers, object-class handoff, and
   direct-store composition.
   Formatter/DC timing after ROM render work is a boundary, not a hidden pixel
   source; use [dc-controller-engine.md](dc-controller-engine.md#reproduction-contract)
   only to preserve ROM-visible wait, scheduler, and render fields that change
   selected records, band words, or `0x1ef6a` call order.
8. If the route stops, record the exact boundary in the
   `Unresolved Boundary Outcome Matrix` in
   [unresolved-boundaries.md](unresolved-boundaries.md). Classify it as
   ROM-local invalid target/source, ROM-local unresolved caller,
   hardware/MMIO, missing external resource data, optional external data, or
   manual/physical correlation. Do not replace a missing ROM edge with fixture
   output or a hardware assumption. For the transparent
   secondary segment-57 path, use
   `Boundary: Secondary Segment-57 Source` in
   [firmware-dataflow-model.md](firmware-dataflow-model.md) and the
   continuation rule in [resource-rom.md](resource-rom.md#owner-summary).

## Evidence Contract

Checked-in explanatory notes are the controlling artifact. Disassembly
addresses, ROM bytes/tables, and RAM field writer/reader chains are the
primary evidence for semantic claims. Generated reports, harness fixtures, and
row digests are supporting checks: they can show that a documented branch,
state shape, or transcription is exercised, but they are not an external pixel
oracle and should not be used to invent behavior past a missing ROM edge.

When adding a new command-family or dataflow edge, cite the concrete handler,
field, object byte, render helper, or unresolved boundary in the checked-in
note that owns it. If fixture output is cited, state what it checks, such as a
parser route, field value, object layout, bridge copy, or helper input.

## Files

- [source-index.md](source-index.md) - what each PDF contains and how to
  use it.
- [hardware-overview.md](hardware-overview.md) - model identity, specs,
  major assemblies, paper path, print process. Start with
  `Hardware Context Outcome Matrix` for product facts that affect ROM-visible
  dataflow.
- [formatter-interface-pca.md](formatter-interface-pca.md) - HP 33440
  formatter architecture, memory, NVRAM, video path. Start with
  `Formatter Boundary Outcome Matrix` for ROM/image provenance and
  board-facing boundaries.
- [dc-controller-engine.md](dc-controller-engine.md) - engine responsibilities,
  sensors, motors, laser, high voltage, formatter/DC signals. Start with
  `DC Boundary Outcome Matrix` for ROM-visible engine-boundary effects.
- [control-panel-nvram-selftest.md](control-panel-nvram-selftest.md) -
  keys, menu state, resets, service mode, self tests. Start with
  `Control Panel Default Outcome Matrix` for ROM-visible default outcomes.
- [io-interfaces.md](io-interfaces.md#owner-summary) - Centronics, RS-232C, RS-422,
  flow control, buffers.
- [pcl4-language.md](pcl4-language.md#owner-summary) - PCL Level IV semantics,
  environment, command syntax, command quick reference.
- [pcl-to-pdf-rom-goals.md](pcl-to-pdf-rom-goals.md) - revised goal:
  stream-to-PDF renderer, and what ROMs are expected to contribute.
- [end-to-end-reproduction-map.md](end-to-end-reproduction-map.md) -
  primary host-byte-to-rendered-pixel route/evidence map for supported
  streams, state groups, objective requirements, and open reproduction
  boundaries.
  Start here when following a concrete byte stream or checking what part of the
  ROM-disassembly objective is covered by checked-in documentation.
- [firmware-dataflow-model.md](firmware-dataflow-model.md) - detailed
  checked-in dataflow spine from host bytes through parser, commands,
  page/image objects, render scheduling, pixel generation, and exact
  unresolved-boundary index.
- [semantic-state-model.md](semantic-state-model.md#owner-summary) - cross-family
  state classification and producer/consumer composition for parser, page-object,
  publication, scheduler, render, status, and boundary fields.
- [errors-and-status.md](errors-and-status.md#owner-summary) - status, attendance,
  error, service codes, host-output FIFO/status bytes, and terminal report
  sinks `0x1284` / `0x128c` with cached report bytes
  `0x783ef0..0x783ef1`.
- [external-ready-service.md](external-ready-service.md#owner-summary) - documented
  external-ready/service loop status bits, messages, register shadows, and
  scheduler/status teardown.
- [page-font-scheduler.md](page-font-scheduler.md#owner-summary) - documented
  optional-resource page/font scheduler handoff, refresh helpers, return paths,
  and caller contracts.
- [rom-dump-manifest.md](rom-dump-manifest.md) - verified ROM dump
  hashes, package markings, interleave order, and rejected order probes. Start
  with `ROM Dump Outcome Matrix` for provenance boundaries.
- [firmware-startup.md](firmware-startup.md#owner-summary) - first annotated 68000
  reset/startup findings from the executable ROM pair.
- [host-byte-fetch.md](host-byte-fetch.md#owner-summary) - documented
  `0xa904` host byte-source multiplexer, direct I/O handshakes, caller
  semantics, and semantic checkpoint.
- [pcl-parser-core.md](pcl-parser-core.md#owner-summary) - documented parser byte
  wrapper, tokenizer, dispatch loop, delayed-payload handoff, and semantic
  checkpoint.
- [display-functions.md](display-functions.md#owner-summary) - documented
  `ESC Y ... ESC Z` display-functions loop, alternate append path, Control-Z
  siblings, and `ESC z` status edge.
- [direct-control-codes.md](direct-control-codes.md#owner-summary) - documented
  CR/LF/FF/HT/BS, line-termination mode, cursor stack, and cursor/margin
  control paths to page-record output.
- [macro-data-chain.md](macro-data-chain.md#owner-summary) - documented macro
  definition, execute/call replay, overlay publication, and data-chain byte
  replay to page-record output.
- [reset-default-environment.md](reset-default-environment.md#owner-summary) -
  documented `ESC E` reset, default-record producers, retained-record paths,
  and reset publication behavior.
- [publication-commands.md](publication-commands.md#owner-summary) -
  documented publication owner boundary, reset, FF, page-size, page-length
  zero/default, orientation, paper-source, and copies routes to rendered page records or
  publication-adjacent state.
- [transparent-print-data.md](transparent-print-data.md#owner-summary) -
  documented `ESC &p#X` delayed payload handling, text/fixed-space routing,
  page-record re-entry, and the secondary segmented resource boundary.
- [raster-graphics.md](raster-graphics.md#owner-summary) - documented `ESC *t`,
  `ESC *r`, and delayed `ESC *b#W` raster path to encoded-span output.
- [rectangle-graphics.md](rectangle-graphics.md#owner-summary) - documented
  `ESC *c` rectangle/rule path to solid and patterned rule rendering.
- [vertical-forms-control.md](vertical-forms-control.md#owner-summary) -
  documented `ESC &l#W` VFC table definition and `ESC &l#V` channel-jump
  output effects.
- [font-context-metrics.md](font-context-metrics.md#owner-summary) - documented font
  context selection, page-root slot install, glyph maps, and descriptor/span
  metric checkpoints.
- [symbol-set-selection.md](symbol-set-selection.md#owner-summary) - documented
  `ESC (` / `ESC )` symbol-set, final-`@`, and final-`X` paths into
  font-context refresh and glyph-map selection.
- [symbol-map-patching.md](symbol-map-patching.md#owner-summary) - documented
  `0x14f16` Roman-8 map patching, hard-coded `0E` / `0U` cases, and the
  `0x14fce` patch table consumed before printable glyph mapping.
- [built-in-resource-scan.md](built-in-resource-scan.md#owner-summary) - documented
  IC32/IC15 resource scan, candidate windows, built-in record filters, and
  glyph-row evidence.
- [downloaded-fonts.md](downloaded-fonts.md#owner-summary) - documented soft-font
  descriptor, payload, validation/no-install, current-record, and
  downloaded-glyph render paths.
- [font-sample-page.md](font-sample-page.md#owner-summary) - documented
  firmware-generated font sample printout from resource candidates through page-record
  segments, multi-probe continuation preflight, and rendered surfaces.
- [pcl-parser-firmware.md](pcl-parser-firmware.md#parser-firmware-outcome-matrix) -
  current host-byte fetch and PCL escape tokenizer/dispatch anchors.
- [pcl-command-map.md](pcl-command-map.md#dispatch-class-checkpoint) -
  firmware parser-table dispatch classes, handler-owner matrix, supported
  stream dispatch matrix, and flattened command-to-handler map.
- [page-raster-imaging.md](page-raster-imaging.md#owner-summary) -
  page geometry lookup tables, orientation state, page-record storage,
  active-render, bitmap object-dispatch, compact row-copy checkpoints, and
  raster graphics imaging path.
- [page-record-storage.md](page-record-storage.md#owner-summary) - documented
  page-root, stream allocator, object-list, publication, and render-record
  bridge contracts. Start with `Page Image Shape And Band Contract` when answering
  whether a stream produces page roots, bucket/list objects, bands, fallback rows, or a
  parser-time bitmap.
- [active-render-scheduler.md](active-render-scheduler.md#owner-summary) -
  documented published-record selection, render-work alternation, wait-object
  state, and band-render scheduler contracts.
- [semantic-state-model.md](semantic-state-model.md) - composed
  renderer-facing state blocks with field groups, evidence, and
  unresolved middle edges.
- [resource-rom.md](resource-rom.md#owner-summary) - current findings for the
  IC32/IC15 resource/font ROM pair.
- [unresolved-boundaries.md](unresolved-boundaries.md) - exact remaining
  ROM-local invalid-target/source, ROM-local unresolved-caller, resource-data,
  hardware/MMIO, optional-data, and physical/manual correlation boundaries.
- [reverse-engineering-ledger.md](reverse-engineering-ledger.md) -
  supporting low-level tracking ledger. Use it as evidence breadcrumbs; the
  current reader-facing route and remaining exact boundaries are the checked-in
  owner notes, [firmware-dataflow-model.md](firmware-dataflow-model.md), and
  [unresolved-boundaries.md](unresolved-boundaries.md).

## Emulator-Relevant Boundaries

- The current deliverable is checked-in ROM dataflow documentation for
  reproducing page output from supported host byte streams. A
  LaserJet II-compatible input-stream renderer can use that model, but
  generated fixtures, scripts, and future renderer code are supporting
  artifacts rather than the controlling documentation.
- The ROMs on the Interface PCA are expected to be most useful for mode
  interactions, default tables, parser behavior, and built-in font
  raster/metric extraction.
- The DC Controller is a separate engine controller. It handles paper
  motion, laser/scanner control, fuser temperature, high voltage, erase
  lamps, motors, sensors, and engine diagnostics. It should not be
  needed for a PDF-output renderer except as background for
  understanding the formatter's final video/page path.

## Source Notation

Each file lists source breadcrumbs using local PDF filenames plus manual
section/table numbers when available. OCR is imperfect, so prefer the
original PDF for any electrical measurement, pin orientation, or diagram
ambiguity.
