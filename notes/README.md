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
  streams, state groups, and open reproduction boundaries. Start here when
  following a concrete byte stream.
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
  page-size, orientation, paper-source, and copies publication streams to
  rendered page records.
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
