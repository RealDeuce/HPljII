# HP LaserJet II ROM Disassembly Notes

These notes summarize the local PDF set into emulator-oriented references. They focus on the HP 33440 / LaserJet Series II unless a LaserJet III detail is explicitly called out as shared hardware or a compatibility boundary.

## Files

- [source-index.md](source-index.md) - what each PDF contains and how to use it.
- [hardware-overview.md](hardware-overview.md) - model identity, specs, major assemblies, paper path, print process.
- [formatter-interface-pca.md](formatter-interface-pca.md) - HP 33440 formatter architecture, memory, NVRAM, video path.
- [dc-controller-engine.md](dc-controller-engine.md) - engine responsibilities, sensors, motors, laser, high voltage, formatter/DC signals.
- [control-panel-nvram-selftest.md](control-panel-nvram-selftest.md) - keys, menu state, resets, service mode, self tests.
- [io-interfaces.md](io-interfaces.md) - Centronics, RS-232C, RS-422, flow control, buffers.
- [pcl4-language.md](pcl4-language.md) - PCL Level IV semantics, environment, command syntax, command quick reference.
- [pcl-to-pdf-rom-goals.md](pcl-to-pdf-rom-goals.md) - revised goal: stream-to-PDF renderer, and what ROMs are expected to contribute.
- [errors-and-status.md](errors-and-status.md) - status, attendance, error, and service codes useful during ROM tracing.
- [rom-dump-manifest.md](rom-dump-manifest.md) - verified ROM dump hashes, package markings, interleave order, and rejected order probes.
- [firmware-startup.md](firmware-startup.md) - first annotated 68000 reset/startup findings from the executable ROM pair.
- [pcl-parser-firmware.md](pcl-parser-firmware.md) - current host-byte fetch and PCL escape tokenizer/dispatch anchors.
- [pcl-command-map.md](pcl-command-map.md) - flattened PCL command-to-handler map summary from the firmware parser tables.
- [page-raster-imaging.md](page-raster-imaging.md) - page geometry lookup tables, orientation state, and first raster graphics imaging path.
- [resource-rom.md](resource-rom.md) - current findings for the IC32/IC15 resource/font ROM pair.
- [reverse-engineering-ledger.md](reverse-engineering-ledger.md) - current host-interface-to-imaging tracking map and next ROM targets.

## Emulator-Relevant Boundaries

- The project goal is a LaserJet II-compatible input-stream to PDF converter, not full hardware emulation.
- The ROMs on the Interface PCA are expected to be most useful for mode interactions, default tables, parser behavior, and built-in font raster/metric extraction.
- The DC Controller is a separate engine controller. It handles paper motion, laser/scanner control, fuser temperature, high voltage, erase lamps, motors, sensors, and engine diagnostics. It should not be needed for a PDF-output renderer except as background for understanding the formatter's final video/page path.

## Source Notation

Each file lists source breadcrumbs using local PDF filenames plus manual section/table numbers when available. OCR is imperfect, so prefer the original PDF for any electrical measurement, pin orientation, or diagram ambiguity.
