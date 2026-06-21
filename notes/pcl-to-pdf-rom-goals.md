# PCL-to-PDF Renderer and ROM Goals

Sources: project discussion;
`33440-90905_HP_LaserJet_series_II_Technical_Reference_Manual_Aug1989.pdf`;
`hplaserjetclassicsiiiii.pdf`.

## Current Goal

Build a LaserJet II-compatible converter:

```text
PCL/input byte stream -> rendered pages -> PDF
```

This is not a full hardware emulator. The formatter board and ROMs are
references and data sources, not necessarily execution targets.

## What We Should Not Need

For PDF output, we should not need accurate modeling of:

- DC Controller CPU or firmware, if any.
- Main motor, scanner motor, fuser, high voltage, fans, solenoids, or sensors.
- Paper timing, beam timing, jams, fuser warmup, or mechanical engine delays.
- Real Centronics/serial electrical timing beyond accepting byte streams.

The service manual hardware notes remain useful for understanding architecture
and diagnostics, but they should not drive the renderer design.

## What the ROMs Are Expected to Provide

The formatter ROMs are valuable for facts the manuals do not fully specify:

- Built-in bitmap font rasters.
- Built-in font metrics, cell sizes, baselines, offsets, pitches, and style
  metadata.
- Symbol-set mapping tables and internal character conversions.
- PCL parser dispatch tables.
- Exact handling of combined escape sequences and malformed commands.
- Exact mode interactions:
  - `ESC E` reset versus panel reset.
  - display-functions mode.
  - transparent print data.
  - raster graphics mode.
  - macro definition/execution/overlay state.
  - font selection and fallback priority.
  - cursor push/pop and reset interactions.
  - page-size, orientation, margins, HMI, VMI, and text-length interactions.
- Default environment tables.
- Paper/page geometry constants.
- Memory accounting and error thresholds, if reproducing `20 ERROR` / `21 ERROR`
  matters.

## Implementation Shape

Suggested renderer components:

- Byte stream reader.
- PCL parser:
  - control codes.
  - two-character escape sequences.
  - parameterized escape sequences.
  - command combining.
  - binary payload commands.
- Print environment model:
  - factory defaults.
  - user defaults.
  - modified print environment.
  - cursor and cursor stack.
  - primary/secondary font state.
  - macro state.
- Page model:
  - physical page size.
  - logical page.
  - printable area.
  - clipping rules.
  - 300 dpi bitmap target initially.
- Renderers:
  - text from built-in and downloaded fonts.
  - raster graphics.
  - rectangular rules/fills/patterns.
  - macros/overlays.
- PDF backend:
  - simplest path: one compressed image per rendered page.
  - later path: emit text/vector primitives where compatible.

## ROM Analysis Milestones

1. Photograph/record formatter board markings.
2. Identify CPU, clock, ROM packages, RAM, NVRAM, gate arrays, and
   cartridge/interface connectors.
3. Dump ROMs and preserve raw byte order.
4. Determine ROM interleave/banking and CPU endian/order.
5. Locate reset/vector/startup code.
6. Locate ASCII strings and display-message tables.
7. Locate PCL command dispatch tables.
8. Locate factory default tables.
9. Locate page geometry tables and compare with Technical Reference figures 2-2
   and 2-3.
10. Locate built-in font tables:
    - descriptors.
    - metrics.
    - symbol sets.
    - glyph bitmaps.
11. Write extraction scripts for built-in fonts and tables.
12. Build behavioral tests from ROM-derived edge cases.

## Documentation Status

The current notes should be enough to avoid routine PDF lookup for:

- PCL syntax and major command behavior.
- default environments and reset behavior.
- logical page and printable-area geometry.
- control-panel/NVRAM/self-test behavior.
- host I/O protocol facts.
- formatter versus DC-controller responsibility split.
- major status/error codes.

Expected remaining PDF lookups:

- Verifying OCR-sensitive tables before implementing exact soft-font descriptor
  parsing.
- Checking diagrams if board connector orientation or signal direction matters.
- Looking up rarely used PCL commands not copied into the quick reference.

Expected ROM-only unknowns:

- HP 33440 CPU identity and exact address map.
- ROM package order/interleave.
- Built-in font raster data and exact metrics.
- Firmware edge cases and mode interactions not specified by manuals.
