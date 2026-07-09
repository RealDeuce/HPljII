# HP LaserJet II ROM Disassembly Notes

These notes summarize the local PDF set into emulator-oriented
references. They focus on the HP 33440 / LaserJet Series II unless a
LaserJet III detail is explicitly called out as shared hardware or a
compatibility boundary.

Evidence policy: firmware claims in this directory are grounded first in ROM
bytes, disassembly, decoded tables, static cross-references, and RAM fields
read or written by those instructions. Fixture scripts and generated reports
are supporting checks for the documented interpretation; they do not represent
runtime observation of a real printer or an executing ROM. When a note states
confidence, read it as confidence in the static disassembly interpretation, not
as hardware-emulation validation.

Fixture row vectors are ROM-derived artifacts: they should be cited as
documented consequences of decoded object fields, bitmap bytes, and render
helpers. They are not comparisons against real printer output, an executed ROM,
or any other external pixel reference. A fixture may prove that a byte stream
reaches a documented branch or helper transcription, but it does not raise
pixel confidence by comparison. Pixel claims must cite the ROM fields,
handlers, and render helpers that produce those rows.

## Controlling Documentation Spine

For a concrete host byte stream, the checked-in owner notes are the controlling
artifact. Generated listings and fixture logs support those notes; they are not
standalone deliverables.

- Host bytes enter through [host-byte-fetch.md](host-byte-fetch.md), which
  documents `0xa904` source priority, data-chain replay, direct host paths, and
  the normalized byte passed to parser wrapper `0xda9a`.
- Parser state is owned by [pcl-parser-core.md](pcl-parser-core.md): parser
  mode `0x782999`, command-record cursor `0x78299e`, six-byte parsed records,
  normal/alternate tables, and delayed payload restore
  `0x121cc -> 0x12218`. Its `Inbound Byte Outcome Contract` is the
  branch-level owner for deciding whether a normalized byte becomes printable
  output, alternate/data append, a matched command handler, a zero-handler
  reset, a no-match fallback, callback continuation, or parser-external return.
- Command dispatch is indexed by [pcl-command-map.md](pcl-command-map.md).
  Individual command families then move to owner notes such as
  [direct-control-codes.md](direct-control-codes.md),
  [transparent-print-data.md](transparent-print-data.md),
  [raster-graphics.md](raster-graphics.md),
  [rectangle-graphics.md](rectangle-graphics.md),
  [downloaded-fonts.md](downloaded-fonts.md),
  [macro-data-chain.md](macro-data-chain.md), and
  [vertical-forms-control.md](vertical-forms-control.md).
- Manual PCL command names and syntax rows are indexed by
  [pcl4-language.md](pcl4-language.md). Its ROM Semantic Index maps PCL Level
  IV families to first parser handlers, representative byte streams,
  page-object bytes or state fields, render routes, and owner notes.
- Page/image assembly is owned by
  [page-record-storage.md](page-record-storage.md): current root
  `0x78297a`, compact/raster buckets at root `+0x1c`, rules at `+0x24`,
  fixed-list objects at `+0x28`, context slots at `+0x2c..+0x68`, and
  publication through `0xff1e`.
- Rendering is owned by [active-render-scheduler.md](active-render-scheduler.md)
  and [page-raster-imaging.md](page-raster-imaging.md): published-record
  scheduling, active render pointer `0x783a18`, bridge
  `0x1ed84` / `0x1edc6`, render entry `0x1ef6a`, compact text/downloaded-glyph
  helpers, rule/fixed-list helpers, and encoded raster helper `0x1f88e`.
- The broad host-byte-to-pixel walkthrough and residual-boundary index is
  [end-to-end-reproduction-map.md](end-to-end-reproduction-map.md). The unified
  semantic field index is [semantic-state-model.md](semantic-state-model.md),
  and the detailed dataflow spine is
  [firmware-dataflow-model.md](firmware-dataflow-model.md). Its
  `Inbound Byte Route Matrix`, `Minimal End-To-End Example`, parser
  command-dispatch anchors, `Binary Payload Lifecycle`, `State-Only Command
  Dependency Map`, `Host/Status Side-Channel Boundary`,
  `Page Versus Band Model`, and `Pixel composition contract` are the shortest
  checked-in path from an admitted byte stream to page objects and rendered
  pixels.
- Resource bytes are owned by [resource-rom.md](resource-rom.md) and
  [built-in-resource-scan.md](built-in-resource-scan.md). The verified
  `IC32,IC15` pair supplies built-in resource bytes through firmware address
  `0x0bffff`; the transparent secondary segment-57 continuation rule in
  [resource-rom.md](resource-rom.md) is the owner for the remaining
  pixel-affecting resource boundary at `0x0c0000..0x0c0321`.

## Stream Trace Workflow

Use this short route when reading a supported PCL byte stream through the
checked-in ROM model:

1. If starting from a manual command name, use the ROM Semantic Index in
   [pcl4-language.md](pcl4-language.md) to find the command-family route and
   concrete stream anchor. If starting from raw bytes, use `Reader Entry
   Points` and `Stream Trace Procedure` in
   [end-to-end-reproduction-map.md](end-to-end-reproduction-map.md).
   For the compact route through the current spine, start with
   `Inbound Byte Route Matrix` and `Minimal End-To-End Example` in
   [firmware-dataflow-model.md](firmware-dataflow-model.md).
2. Start with byte admission in [host-byte-fetch.md](host-byte-fetch.md):
   classify each byte source at `0xa904` as live/ring input, pushback,
   macro/data-chain replay, or a payload reader's direct fetch.
3. Classify the parser outcome in
   [pcl-parser-core.md](pcl-parser-core.md): follow `0xda9a` / `0xdaf0` /
   `0xdb74` into parser loop `0x11774`, preserving parser mode `0x782999`,
   six-byte records at `0x78299e..`, alternate/data flag `0x782c18`, and
   delayed restore `0x121cc -> 0x12218`. For counted binary payload commands,
   use `Binary Payload Lifecycle` in
   [firmware-dataflow-model.md](firmware-dataflow-model.md). For
   definition-mode or replayed bytes, use `Alternate/Data And Macro Replay
   Boundary` in the same file before jumping to the family owner.
4. Use [pcl-command-map.md](pcl-command-map.md) only as the dispatch index.
   After a terminal handler is named, continue in the family owner note for
   parsed inputs, RAM writers, readers/consumers, output effect, and residual
   boundary. The parser command-dispatch anchors in
   [firmware-dataflow-model.md](firmware-dataflow-model.md) summarize the
   common terminal-handler handoffs before the full flattened table. The
   `Command Family Owner Matrix` in the same file gives the compact
   handler-to-owner handoff and output class for each command family. For
   text/font routes, use `Font Context And Glyph Source Boundary` to connect
   selected contexts and maps to printable source objects.
5. When a command creates visible page content, cross into
   [page-record-storage.md](page-record-storage.md): compact/raster buckets
   live under root `+0x1c`, rules under `+0x24`, fixed-list objects under
   `+0x28`, and context slots under `+0x2c..+0x68`. The shared
   `Shared Page-Object Contract` in
   [end-to-end-reproduction-map.md](end-to-end-reproduction-map.md) is the
   route index for these common object fields. `Page Versus Band Model` in
   [firmware-dataflow-model.md](firmware-dataflow-model.md) is the concise
   explanation of why parsing builds a page-object graph rather than a
   full-page bitmap.
6. For publication, follow `Publication And Page-Control Boundary` in
   [firmware-dataflow-model.md](firmware-dataflow-model.md), then follow
   `0xff1e` into the page/control pool and
   [active-render-scheduler.md](active-render-scheduler.md): scheduler source
   `0x780eae`, active render pointer `0x783a18`, and bridge
   `0x1ed84 -> 0x1edc6`.
7. For pixels, finish in
   [page-raster-imaging.md](page-raster-imaging.md): render entry `0x1ef6a`,
   bucket dispatch `0x1efc2`, rule dispatch `0x1f446`, fixed-list dispatch
   `0x1f756`, and helper-specific row construction. The shared
   `Render Helper Boundary Index` in
   [end-to-end-reproduction-map.md](end-to-end-reproduction-map.md) names the
   common helper order, buffer destinations, and exact ROM-local render
   boundaries. The `Pixel composition contract` in
   [firmware-dataflow-model.md](firmware-dataflow-model.md) summarizes render
   call order, active-band and fallback buffers, object-class handoff, and
   direct-store composition.
8. If the route stops, record the exact boundary as ROM-local unknown,
   hardware/MMIO, missing external resource data, or optional physical
   correlation. Do not replace a missing ROM edge with fixture output or a
   hardware assumption.

## Files

- [source-index.md](source-index.md) - what each PDF contains and how to
  use it.
- [hardware-overview.md](hardware-overview.md) - model identity, specs,
  major assemblies, paper path, print process.
- [formatter-interface-pca.md](formatter-interface-pca.md) - HP 33440
  formatter architecture, memory, NVRAM, video path.
- [dc-controller-engine.md](dc-controller-engine.md) - engine
  responsibilities, sensors, motors, laser, high voltage, formatter/DC
  signals.
- [control-panel-nvram-selftest.md](control-panel-nvram-selftest.md) -
  keys, menu state, resets, service mode, self tests.
- [io-interfaces.md](io-interfaces.md) - Centronics, RS-232C, RS-422,
  flow control, buffers.
- [pcl4-language.md](pcl4-language.md) - PCL Level IV semantics,
  environment, command syntax, command quick reference.
- [pcl-to-pdf-rom-goals.md](pcl-to-pdf-rom-goals.md) - revised goal:
  stream-to-PDF renderer, and what ROMs are expected to contribute.
- [end-to-end-reproduction-map.md](end-to-end-reproduction-map.md) -
  primary host-byte-to-rendered-pixel coverage/evidence map for supported
  streams, state groups, objective coverage, and open reproduction boundaries.
  Start here when following a concrete byte stream or checking what part of the
  ROM-disassembly objective is covered by checked-in documentation.
- [firmware-dataflow-model.md](firmware-dataflow-model.md) - detailed
  checked-in dataflow spine from host bytes through parser, commands,
  page/image objects, render scheduling, pixel generation, and exact
  unresolved-boundary index.
- [errors-and-status.md](errors-and-status.md) - status, attendance,
  error, and service codes useful during ROM tracing.
- [external-ready-service.md](external-ready-service.md) - documented
  external-ready/service loop status bits, messages, register shadows, and
  scheduler/status teardown.
- [page-font-scheduler.md](page-font-scheduler.md) - documented
  optional-resource page/font scheduler handoff, refresh helpers, return paths,
  and caller contracts.
- [rom-dump-manifest.md](rom-dump-manifest.md) - verified ROM dump
  hashes, package markings, interleave order, and rejected order probes.
- [firmware-startup.md](firmware-startup.md) - first annotated 68000
  reset/startup findings from the executable ROM pair.
- [host-byte-fetch.md](host-byte-fetch.md) - documented `0xa904` host
  byte-source multiplexer, direct I/O handshakes, caller semantics, and
  semantic checkpoint.
- [pcl-parser-core.md](pcl-parser-core.md) - documented parser byte
  wrapper, tokenizer, dispatch loop, delayed-payload handoff, and semantic
  checkpoint.
- [display-functions.md](display-functions.md) - documented `ESC Y ... ESC Z`
  display-functions loop, alternate append path, Control-Z siblings, and
  `ESC z` status edge.
- [direct-control-codes.md](direct-control-codes.md) - documented
  CR/LF/FF/HT/BS, line-termination mode, cursor stack, and cursor/margin
  control paths to page-record output.
- [macro-data-chain.md](macro-data-chain.md) - documented macro definition,
  execute/call replay, overlay publication, and data-chain byte replay to
  page-record output.
- [reset-default-environment.md](reset-default-environment.md) - documented
  `ESC E` reset, default-record producers, retained-record paths, and reset
  publication behavior.
- [publication-commands.md](publication-commands.md) - documented reset, FF,
  page-size, page-length zero/default, orientation, paper-source, and copies
  publication routes to rendered page records or publication-adjacent state.
- [transparent-print-data.md](transparent-print-data.md) - documented
  `ESC &p#X` delayed payload handling and printable text re-entry.
- [raster-graphics.md](raster-graphics.md) - documented `ESC *t`,
  `ESC *r`, and delayed `ESC *b#W` raster path to encoded-span output.
- [rectangle-graphics.md](rectangle-graphics.md) - documented `ESC *c`
  rectangle/rule path to solid and patterned rule rendering.
- [vertical-forms-control.md](vertical-forms-control.md) - documented
  `ESC &l#W` VFC table definition and `ESC &l#V` channel-jump output effects.
- [font-context-metrics.md](font-context-metrics.md) - documented font
  context selection, page-root slot install, glyph maps, and descriptor/span
  metric checkpoints.
- [symbol-set-selection.md](symbol-set-selection.md) - documented
  `ESC (` / `ESC )` symbol-set, final-`@`, and final-`X` paths into
  font-context refresh and glyph-map selection.
- [symbol-map-patching.md](symbol-map-patching.md) - documented
  `0x14f16` Roman-8 map patching, hard-coded `0E` / `0U` cases, and the
  `0x14fce` patch table consumed before printable glyph mapping.
- [built-in-resource-scan.md](built-in-resource-scan.md) - documented
  IC32/IC15 resource scan, candidate windows, built-in record filters, and
  glyph-row evidence.
- [downloaded-fonts.md](downloaded-fonts.md) - documented soft-font
  descriptor, payload, validation/no-install, current-record, and
  downloaded-glyph render paths.
- [font-sample-page.md](font-sample-page.md) - documented firmware-generated
  font sample printout from resource candidates through page-record segments
  and rendered surfaces.
- [pcl-parser-firmware.md](pcl-parser-firmware.md) - current host-byte
  fetch and PCL escape tokenizer/dispatch anchors.
- [pcl-command-map.md](pcl-command-map.md) - flattened PCL
  command-to-handler map summary from the firmware parser tables.
- [page-raster-imaging.md](page-raster-imaging.md) - page geometry
  lookup tables, orientation state, page-record storage, active-render,
  bitmap object-dispatch, compact row-copy checkpoints, and raster graphics
  imaging path.
- [page-record-storage.md](page-record-storage.md) - documented page-root,
  stream allocator, object-list, publication, and render-record bridge
  contracts.
- [active-render-scheduler.md](active-render-scheduler.md) - documented
  published-record selection, render-work alternation, wait-object state, and
  band-render scheduler contracts.
- [semantic-state-model.md](semantic-state-model.md) - composed
  renderer-facing state blocks with field groups, evidence, and
  unresolved middle edges.
- [resource-rom.md](resource-rom.md) - current findings for the
  IC32/IC15 resource/font ROM pair.
- [reverse-engineering-ledger.md](reverse-engineering-ledger.md) -
  current host-interface-to-imaging tracking map and next ROM targets.

## Emulator-Relevant Boundaries

- The project goal is a LaserJet II-compatible input-stream to PDF
  converter, not full hardware emulation.
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
