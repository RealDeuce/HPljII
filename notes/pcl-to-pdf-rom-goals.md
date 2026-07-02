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
- Main motor, scanner motor, fuser, high voltage, fans, solenoids, or
  sensors.
- Paper timing, beam timing, jams, fuser warmup, or mechanical engine
  delays.
- Real Centronics/serial electrical timing beyond accepting byte
  streams.

The service manual hardware notes remain useful for understanding
architecture and diagnostics, but they should not drive the renderer
design.

## What the ROMs Are Expected to Provide

The formatter ROMs are valuable for facts the manuals do not fully
specify:

- Built-in bitmap font rasters.
- Built-in font metrics, cell sizes, baselines, offsets, pitches, and
  style metadata.
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
  - page-size, orientation, margins, HMI, VMI, and text-length
    interactions.
- Default environment tables.
- Paper/page geometry constants.
- Memory accounting and error thresholds, if reproducing `20 ERROR` /
  `21 ERROR` matters.

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

## Current ROM-Derived Renderer Contract

The implementation-facing pipeline is now documented in
[end-to-end-reproduction-map.md](end-to-end-reproduction-map.md):

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

Concrete software contracts already exist for these renderer components:

- Byte stream reader:
  `0xa904` byte-source priority, data-chain frame layout, pushback stacks,
  ring buffer, direct hardware modes, and host/status output FIFO are
  composed in [host-byte-fetch.md](host-byte-fetch.md),
  [io-interfaces.md](io-interfaces.md), and
  [semantic-state-model.md](semantic-state-model.md).
- Parser:
  six-byte parser records, dispatch tables, alternate/data mode, and
  delayed-payload restore through `0x121cc` / `0x12218` are composed in
  [pcl-parser-core.md](pcl-parser-core.md) and
  [pcl-command-map.md](pcl-command-map.md).
- Print environment:
  cursor/HMI/VMI/margins, direct controls, line termination, cursor stack,
  transparent data, display-functions mode, VFC, reset/default records, and
  macro data-chain replay are composed in
  [semantic-state-model.md](semantic-state-model.md),
  [transparent-print-data.md](transparent-print-data.md), and
  [vertical-forms-control.md](vertical-forms-control.md).
- Font state:
  built-in resource scans, candidate windows, primary/secondary selected
  contexts, symbol fallbacks, final-`@`, final-`X`, page-root context-slot
  installs, downloaded descriptors, downloaded glyph payloads, and span
  metrics are composed in [resource-rom.md](resource-rom.md),
  [font-context-metrics.md](font-context-metrics.md), and
  [downloaded-fonts.md](downloaded-fonts.md).
- Page model:
  page-root allocation `0x10084`, stream allocator `0x1381c`, compact text
  buckets `0x1387c`, rule/fixed lists `0x133aa` / `0x136d2`, publication
  `0xff1e`, and render bridge `0x1ed84` / `0x1edc6` are composed in
  [page-raster-imaging.md](page-raster-imaging.md) and
  [semantic-state-model.md](semantic-state-model.md).
- Renderers:
  compact text, built-in and downloaded glyphs, raster modes `0..3`,
  rectangle/rule fills, band walking, and mixed text/rule/raster page
  streams are documented in [page-raster-imaging.md](page-raster-imaging.md),
  [raster-graphics.md](raster-graphics.md), and
  [rectangle-graphics.md](rectangle-graphics.md).

The strongest current byte-stream fixtures include:

- plain and direct-control text from `0xa904` through `0x1ed84` /
  `0x1ef6a`: `plain printable parser trace feeds page-record queue`,
  `host-fetched mixed control stream reaches parser and page-record render`,
  and `host-fetched direct text/control streams feed 0x1ed84 and 0x1ef6a`;
- reset, FF, page-size, orientation, paper-source, copies, and VFC
  publication through `0xff1e`: `host-fetched publication streams reach parser
  and published rows`, `published page records feed 0x1ed84 and 0x1ef6a render
  entry`, and the VFC fixtures named in
  [vertical-forms-control.md](vertical-forms-control.md);
- mixed text/selector-7 rule/raster/FF publication through page-record
  storage and final rows: `host-fetched text rectangle raster FF publishes
  rendered page record` and
  `host-fetched text rectangle multi-row raster FF publishes rendered page
  record`;
- primary and secondary built-in font-selection visible-output streams,
  including symbol fallback, final-`@`, final-`X` built-in, final-`X`
  inline/downloaded, and final-`X` preserved-output variants:
  `inline primary font selection stream renders visible rows`,
  `inline secondary font selection stream renders SO visible rows`,
  `real final-@ default-table streams select visible built-ins`, and
  `font-ID built-in selection feeds visible page-record rows`,
  `font-ID secondary built-in selection feeds visible SO page-record rows`,
  `font-ID primary inline/downloaded selection feeds visible page-record rows`,
  `font-ID inline/downloaded selection feeds visible page-record rows`,
  `font-ID non-selected exits keep prior visible rows`, and
  `font-ID secondary non-selected exits keep prior SO visible rows`;
- downloaded-glyph FF publication, downloaded-glyph/rule/raster composition,
  type-1/type-2 resource publication, and segmented downloaded-glyph band
  rendering:
  `combined font download FF publishes installed glyph page record`,
  `parser-driven downloaded glyph rule raster stream composes through
  0x1ef6a`,
  `type-1 and type-2 resource glyph FF publications render page records`,
  `type-1 and type-2 resource wide glyph FF publications render page records`,
  `type-1 and type-2 resource segmented glyph FF publications render page
  records`, and
  `0x1eba4 scheduler band words render published downloaded glyph`.

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
9. Locate page geometry tables and compare with Technical Reference
   figures 2-2 and 2-3.
10. Locate built-in font tables:
    - descriptors.
    - metrics.
    - symbol sets.
    - glyph bitmaps.
11. Write extraction scripts for built-in fonts and tables.
12. Build behavioral tests from ROM-derived edge cases.

Current milestone status:

- ROM dumping and interleave are settled in
  [rom-dump-manifest.md](rom-dump-manifest.md) and
  `data/rom_manifest.json`: `IC30,IC13` is the executable 68000 firmware
  pair, and `IC32,IC15` is the resource/font pair. Raw images remain
  local-only.
- Reset/startup, scheduler bootstrap, host byte fetch, parser dispatch,
  page geometry, font/resource records, downloaded fonts, page records,
  publication, render bridge, and render dispatch all have tracked notes.
- Behavioral fixtures now cover the major parser-to-render command families
  named above. Remaining fixture work should target new byte-stream variants
  that expose different ROM state or broader cross-product validation, not
  first discovery of the main byte-to-pixel path.

## Documentation Status

The current notes should be enough to avoid routine PDF lookup for:

- PCL syntax and major command behavior.
- default environments and reset behavior.
- logical page and printable-area geometry.
- control-panel/NVRAM/self-test behavior.
- host I/O protocol facts.
- formatter versus DC-controller responsibility split.
- major status/error codes.
- ROM-backed byte-source/parser/page-record/render state needed for the
  covered byte-stream families.
- Built-in and downloaded-font candidate/context/glyph payload semantics for
  the documented visible-output fixtures.

Expected remaining PDF lookups:

- Verifying OCR-sensitive tables before implementing exact soft-font
  descriptor parsing.
- Checking diagrams if board connector orientation or signal direction
  matters.
- Looking up rarely used PCL commands not copied into the quick
  reference.

Expected remaining boundaries:

- External resource-window evidence: exact board address decode after the
  verified resource pair at
  firmware `0x0c0000..0x0c0321`, which affects the secondary transparent
  segment-57 fallback rows documented in
  [transparent-print-data.md](transparent-print-data.md) and
  [resource-rom.md](resource-rom.md). The startup resource-pair byte-sum covers
  `0x080000..0x0bffff`, so checksum success does not resolve those continuation
  bytes.
- Physical/manual correlation: manual-facing baseline/cell terminology and
  physical paper comparison for the full internal-font printout, after the
  ROM-side sample page and rendered-surface digest already documented in
  [resource-rom.md](resource-rom.md).
- Physical interface correlation: identity and pin mapping for
  retained-storage, panel/service, optional-resource, and formatter/DC MMIO
  registers. Host-interface
  software roles are documented in [host-byte-fetch.md](host-byte-fetch.md)
  and [io-interfaces.md](io-interfaces.md): the two direct-input banks now
  have ROM-visible ready, data, acknowledge/status, and control-shadow roles.
  Their remaining unknown is physical connector/interface mapping and timing.
- Optional provenance for already-modeled handoffs, such as dense raster
  producer state `0x105d0 -> 0x10084 -> 0x13070` and the downloaded-font
  install-to-page boundary after `ESC )s18W`. These are not current
  ROM-semantic blockers when the checked-in notes already document field
  ownership, consumers, fixtures, and output rows.
- ROM-local work: broader command cross-products only where they expose a new
  state boundary; already-covered command families should be treated as
  regression expansion.
