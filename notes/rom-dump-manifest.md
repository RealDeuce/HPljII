# ROM Dump Manifest

Sources: local TC531000P reads; `TC531000AP.PDF`; `data/rom_manifest.json`.

The verified ROM images are local-only artifacts and are intentionally
ignored by Git. Track filenames, hashes, package locations, read method,
and analysis notes here; keep raw bytes in the working directory.

## Owner Summary

This note owns ROM provenance for the disassembly. It identifies which
local-only mask-ROM reads are verified, which board locations form the
executable 68000 pair and resource/font pair, and which generated interleaves
are valid evidence for checked-in disassembly and resource notes.

Primary route:

- Raw TC531000P reads are verified by repeated matching dumps and by package
  tail markers printed inside each image.
- `IC30,IC13` interleaves into the executable firmware image. It owns the ROM
  bytes used by 68000 disassembly, parser tables, command handlers, page
  assembly, render scheduling, and bitmap/render helpers.
- `IC32,IC15` interleaves into the built-in resource/font image. It owns the
  verified resource bytes consumed by font and glyph lookup until the
  documented resource-window boundary at firmware address `0x0c0000`.
- Rejected reverse orders are negative evidence only. They are not valid
  firmware or resource sources for semantic claims.

State classification:

- Canonical ROM provenance: board locations `IC13`, `IC15`, `IC30`, `IC32`,
  chip markings, verified raw SHA-256 hashes, read method, and repeated-read
  evidence.
- Canonical firmware/resource evidence: generated interleave hashes
  `ic30_ic13.bin` and `ic32_ic15.bin`, firmware reset vector
  `SP=0x00800000` / `PC=0x00000110`, and the readable resource `HEAD`
  header/copyright string.
- Derived/cache evidence: files under `generated/`, disassembly listings, and
  analysis reports produced from these interleaves. They are reproducible
  artifacts, not separate ROM sources.
- Firmware bookkeeping: `data/rom_manifest.json`, which mirrors this
  checked-in manifest in machine-readable form for local tools.
- Hardware/external state: board decode after the verified resource pair,
  including the secondary segment-57 continuation at
  `0x0c0000..0x0c0321`.
- Unknown: physical gate-array decode and any external resource bytes outside
  the verified local images.

Output effect:

- This manifest does not describe parser behavior or draw pixels directly.
  Its output effect is evidentiary: it defines the byte images from which
  handler addresses, ROM fields, command tables, resource bytes, and
  unresolved resource boundaries are derived.
- A byte-stream reproduction claim should cite disassembly or owner notes built
  from `IC30,IC13` for executable behavior, and resource notes built from
  `IC32,IC15` for built-in glyph/resource bytes. Claims past `0x0bffff` must
  stop at the documented external-resource boundary unless new board or
  resource evidence supplies those bytes.

## ROM Dump Outcome Matrix

This matrix records which local-only dump artifacts are allowed to support
checked-in semantic claims. The raw ROM bytes stay out of Git; the checked-in
contract is the provenance, hashes, valid interleaves, negative probes, and
exact unresolved byte ranges.

Verified raw mask-ROM reads:

- ROM path:
  `IC13`, `IC15`, `IC30`, and `IC32` as individual `TC531000P` 128K x 8
  devices read with the `LQ500_4C_A16_PIN22@DIP28` profile.
- State class:
  canonical ROM provenance.
- Writers:
  none in firmware. The reader procedure produced local-only dump files; this
  checked-in note and `data/rom_manifest.json` record the hashes and chip
  markings.
- Readers / consumers:
  interleave generation, firmware/resource analysis, and any future raw-byte
  verification scripts.
- Output effect:
  evidentiary only. Individual byte-wide dumps do not describe parser
  behavior until paired into a valid firmware or resource image.
- Evidence:
  verified SHA-256 hashes and tail markers in this note and
  `data/rom_manifest.json`.

Executable firmware interleave:

- ROM path:
  `IC30,IC13 -> generated/roms/ic30_ic13.bin -> SP 0x00800000 ->
  PC 0x00000110`.
- State class:
  canonical firmware/resource evidence and derived/cache evidence.
- Writers:
  no runtime writer. The interleave defines immutable executable firmware
  bytes for the disassembler and checked-in notes.
- Readers / consumers:
  focused disassembly listings, parser/core documentation, command-family
  owners, page-object owners, render scheduler, and pixel-generation notes.
- Output effect:
  defines the executable address space for all handler addresses, ROM fields,
  command tables, and render helpers cited in the documentation.
- Evidence:
  `data/rom_manifest.json`, `generated/analysis/ic30_ic13_vectors.txt`, and
  coherent 68000 startup disassembly at reset PC `0x00000110`.

Built-in resource interleave:

- ROM path:
  `IC32,IC15 -> generated/roms/ic32_ic15.bin -> firmware resource
  0x080000..0x0bffff`.
- State class:
  canonical firmware/resource evidence and canonical resource data.
- Writers:
  no runtime writer. The interleave defines immutable verified built-in
  resource bytes.
- Readers / consumers:
  startup `HEAD` scanner, font/resource scan, built-in candidate windows,
  font selection, glyph resolver, and compact text renderers.
- Output effect:
  supplies built-in font records, glyph tables, and bitmap payloads that later
  become pixels after parser-selected font context and page objects reach the
  render path.
- Evidence:
  `data/rom_manifest.json`,
  [resource-rom.md](resource-rom.md#resource-rom-outcome-matrix),
  [built-in-resource-scan.md](built-in-resource-scan.md#resource-scan-outcome-matrix),
  `generated/analysis/ic32_ic15_header.txt`, and
  `generated/analysis/ic32_ic15_resource_markers.txt`.

Rejected interleave orders:

- ROM path:
  `IC13,IC30` and `IC15,IC32`.
- State class:
  derived/cache evidence and firmware bookkeeping.
- Writers:
  local analysis tools produced rejected-order probes.
- Readers / consumers:
  this manifest, formatter boundary documentation, and future provenance
  audits.
- Output effect:
  negative evidence only. These byte orders must not be cited for semantic
  firmware, parser, resource, or pixel claims.
- Evidence:
  `IC13,IC30` lacks sane 68000 startup vectors; `IC15,IC32` garbles the
  resource header strings. Hashes and rejection reasons are recorded in
  `data/rom_manifest.json`.

Generated analysis artifacts:

- ROM path:
  `tools/generate_rom_artifacts.py`, `tools/analyze_roms.py`, and focused
  disassembly/report generation from the valid interleaves.
- State class:
  derived/cache evidence.
- Writers:
  local tools create ignored `generated/` outputs from the verified local ROM
  inputs.
- Readers / consumers:
  checked-in owner notes cite generated listings, table extracts, fixture
  reports, and resource analyses as supporting evidence.
- Output effect:
  supports documentation claims, but does not create a new ROM source. If a
  generated report disagrees with this manifest, the raw verified hashes and
  interleave contract are authoritative.
- Evidence:
  generated file references throughout the owner notes and the regeneration
  commands in this manifest.

Resource continuation boundary:

- ROM path:
  verified suffix `0x0bfe22..0x0bffff`, then unresolved firmware range
  `0x0c0000..0x0c0321`.
- State class:
  hardware/external state and unknown resource data.
- Writers:
  no checked-in writer. A future board, emulator, gate-array, or external
  resource source must supply these bytes before claims can continue past the
  verified suffix.
- Readers / consumers:
  transparent segment-57 paths and any resource-render path that reads beyond
  the verified `IC32,IC15` suffix.
- Output effect:
  exact unresolved pixel boundary. Rows requiring bytes in
  `0x0c0000..0x0c0321` must remain unresolved unless new evidence supplies the
  physical byte source.
- Evidence: [resource-rom.md](resource-rom.md#resource-rom-outcome-matrix),
  [unresolved-boundaries.md](unresolved-boundaries.md#secondary-segment-57-resource-source),
  and `tools/probe_resource_window.py`.

State grouping for this matrix:

- Canonical:
  board locations, package markings, raw SHA-256 hashes, verified interleave
  hashes, reset vector fields, and verified resource header identity.
- Derived/cache:
  generated interleaves, focused disassembly, string/resource reports, probe
  hashes, and rejected-order probes.
- Parser scratch:
  none. Parser state is downstream of the executable firmware image.
- Firmware bookkeeping:
  `data/rom_manifest.json`, regeneration commands, read-method notes, and
  rejected-order records.
- Hardware/external:
  local-only raw ROM files, board address decode after the verified resource
  pair, optional cartridge/resource windows, and gate-array mapping.
- Unknown:
  physical decode and byte source for `0x0c0000..0x0c0321`, plus any resource
  bytes outside the verified local images.

Evidence and unresolved boundaries:

- Evidence for the valid firmware pair is the vector table and MAME 68000
  startup disassembly at reset PC `0x00000110`.
- Evidence for the valid resource pair is the readable `HEAD` header and
  copyright string, plus the resource scan and transparent segment-57 notes
  that consume the image through `0x0bffff`.
- The exact remaining provenance boundary is the built-in resource decode after the
  verified `IC32,IC15` suffix, especially `0x0c0000..0x0c0321`. It is tracked in
  [unresolved-boundaries.md](unresolved-boundaries.md#secondary-segment-57-resource-source).

## Read Setup

- Device family: Toshiba `TC531000P`, 128K x 8 mask ROM, DIP28.
- Reader profile: `LQ500_4C_A16_PIN22@DIP28`.
- Control polarity: active-low `/CE` is correct for these parts.
- Active-high CE probe returned erased-looking data and was rejected.
- Address pin note: TC531000 pin 22 is A16; pin 20 is the CE or `/CE`
  mask option.

## Verified Raw ROMs

- IC13
  - Chip marking: SH7-9236-01
  - Local filename: `ic13_sh7-9236-01_tc531000p.bin`
  - SHA-256:
    `0e6fa34f0d25763ac1b687f1a24d07190ddc04057690b3e3846c114284db42d5`
  - Evidence: read1/read2 matched; tail marker `SH7-9236-01000`
- IC15
  - Chip marking: SH7-9234-01
  - Local filename: `ic15_sh7-9234-01_tc531000p.bin`
  - SHA-256:
    `623396d62a450794e4e0c6356009921ca7fb04a7cb7d2e15a35554630c697396`
  - Evidence: two reads matched; tail marker `SH7-9234-01`
- IC30
  - Chip marking: SH7-9235-01
  - Local filename: `ic30_sh7-9235-01_tc531000p.bin`
  - SHA-256:
    `63959a0ad8a4185f6a127afa23dfc89b1f0d7dd04a2a84da853abb30ffd1aeb6`
  - Evidence: three reads matched; ROM tail marker `SH7-9235-01000`
- IC32
  - Chip marking: SH7-9233-01
  - Local filename: `ic32_sh7-9233-01_tc531000p.bin`
  - SHA-256:
    `7f9abfe55629770b0f4bcd0e3bc671143d4cca6ec666edfac34d9e0587ae6452`
  - Evidence: read4/read5 matched; earlier reads retained as unverified
    local
    files

All four verified raw images are 131072 bytes.

## Interleaves

Generate local interleaves and probes with:

```sh
tools/generate_rom_artifacts.py
tools/analyze_roms.py
```

Generated files are written under `generated/`, which is also ignored by
Git.

Recheck the transparent segment-57 resource-window boundary directly from
the ignored local ROM inputs with:

```sh
tools/probe_resource_window.py
```

That probe verifies the raw hashes, reconstructs the firmware/resource
interleaves, hashes the verified `0x0bfe22..0x0bffff` suffix, hashes the
mirror/code-pair/zero-fill `0x0c0000..0x0c0321` continuation candidates,
and checks the `0x41a` / `0x1a616` scanner consequences.

- firmware
  - Byte order: IC30, IC13
  - Local output: `generated/roms/ic30_ic13.bin`
  - SHA-256:
    `feeaf8d651b593af72b65d76fe6b85ee7d191278570438caeac49e0b74dbd079`
  - Interpretation: 68000 executable ROM pair
- resources
  - Byte order: IC32, IC15
  - Local output: `generated/roms/ic32_ic15.bin`
  - SHA-256:
    `dd4ca68e1790dc81dfdb4c364a0bc5e449f4c53e1bfc39a1536c26369eab935c`
  - Interpretation: resource/font/data ROM pair

Rejected order probes:

- IC13, IC30: reset vector/order does not produce sane 68000 startup.
- IC15, IC32: resource header strings are garbled.

## Pairing Evidence

`IC30,IC13` begins with a plausible 68000 vector table:

- Initial supervisor stack pointer: `0x00800000`.
- Reset PC: `0x00000110`.
- Exception vectors point into a regular RAM trampoline range beginning
  at `0x00780000`.

Disassembling at `0x00000110` as `m68000` produces coherent startup
code: interrupt mask setup, `RESET`, hardware register writes, RAM
tests, trampoline initialization, and jumps into later initialization
routines.

`IC32,IC15` reconstructs a readable resource header:

```text
HEAD ... Copyright (C) Hewlett-Packard Company, 1986
```

MAME disassembly of the same pair does not look like executable
reset/startup code, so treat it as data until proven otherwise.
