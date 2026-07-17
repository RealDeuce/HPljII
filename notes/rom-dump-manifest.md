# ROM Dump Manifest

Sources: local TC531000P, TC531001CP/TC531001CP-F076, and VT231025 reads;
`TC531000AP.PDF`; `data/rom_manifest.json`.

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
- The two anonymous `C2053A #C06` packages interleave as package B on the
  even lane and package A on the odd lane. This produces a separate optional
  cartridge resource image; it is not part of the built-in resource window.
- The four numbered `92286PC` packages form two fixed-`FONT` banks. Package
  `1818-4521` is the even lane with `1818-4519` odd in bank 0; package
  `1818-4522` is even with `1818-4520` odd in bank 1. The banks contain 39 and
  26 real font records, respectively.
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

## C2053A C06 Cartridge Resource Interleave

- ROM path:
  anonymous package B on the even byte lane and package A on the odd byte
  lane, producing
  `generated/roms/cartridges/c2053a-c06/c2053a-c06-even-b-odd-a.bin`.
- Device and read method:
  both packages are `TC531001CP-F076` 128K x 8 mask ROMs, read twice with a
  T48 and `minipro -y -p M27C1001@DIP32`; each package's two reads matched.
- Raw SHA-256:
  package A is
  `791b5c1920dbf93977f59bb1caf4ad4d4f019ff7c3d87b947712b99e279eff67`;
  package B is
  `a26ee6be2a85f83d23146b0bb6c4623be0815624117dfb05545392aec2b63aea`.
- Logical-image SHA-256:
  `b5d002e54b3e572458770c7507958f48ce35a17e3f54f05b29042079314681c9`.
- Structural evidence:
  the image starts with `HEAD`, walks 16 consecutive type-`0x14` records,
  and reaches a zero terminator at `0x03f91c`. The reverse order begins
  `EHDA` and fails the firmware's `HEAD` scanner.
- Output effect:
  this supplies immutable optional font and symbol resources. The extracted
  records are six `LtrGothic`, one `OCR A`, one `OCR B`, two `Line Draw`, two
  `Code 3of9`, one `UPC 13mil`, one `UPC 10mil`, and two `USPS ZIP` records.
- Emulator asset:
  `tools/extract_resource_fonts.py` writes the slot-independent
  `hp-laserjet-resource-fonts-v1` JSON asset at
  `generated/roms/cartridges/c2053a-c06/fonts.json`. It preserves all 2,242
  table slots, 1,729 mode-1 glyph payloads, 513 absent slots, selection
  fields, complete glyph-entry prefixes, signed placement, dimensions, row
  padding, and 235,965 bitmap bytes.
- Evidence:
  `data/rom_manifest.json`, `tools/extract_resource_fonts.py`, and the
  local-only package, logical image, and generated font asset named above.

## 92286PC ProCollection Cartridge

The local cartridge contains four 128K x 8 mask ROMs. Packages `1818-4519`,
`1818-4521`, and `1818-4522` are marked `VT231025`; package `1818-4520` is
marked `TC531001CP`. All were read with a T48 using
`minipro -y -p M27C1001@DIP32`. The reader reports ID `0x0000` rather than
the EPROM profile's `0x2005`, as expected for these mask ROMs.

Verified package reads:

| Package | Verified reads | SHA-256 | Tail marker |
| --- | --- | --- | --- |
| `1818-4519` | read 1 = read 2 | `797f4e61ad0b33de8facae120f3b56108901733b42fdd8e086989a6ac62eb416` | `1818-4519-2830` |
| `1818-4520` | read 1 = read 2 | `c03d74d9fba838cd567209e4327eb9d31903ff082bbb1af9bb2bc56f279fa604` | `1818-4520-2830` |
| `1818-4521` | read 1 = read 2 | `a930b544bbb0197dac586f96af91e99cfcd6567bcd895f5b0412091ffb77ae53` | `1818-4521-2830` |
| `1818-4522` | read 6 = read 7 | `cf12b7dd987bebaace2d176ab1fb612d994329f073dca15f42efe2e5d2962106` | `1818-4522-2830` |

The first five `1818-4522` reads varied while the package had poor contact.
They were deleted after cleaning, reseating, and obtaining matching reads 6
and 7. They are not evidence and no known-bad canonical dump remains.

The valid lane and bank composition is:

| Bank | Even lane | Odd lane | Logical SHA-256 | Structural result |
| ---: | --- | --- | --- | --- |
| 0 | `1818-4521` | `1818-4519` | `a0421299a399edd2c20c87d0c01eea0765f9cce6c581639f014f358c71687c82` | starts `FONTTmsRmn`; 39 real records |
| 1 | `1818-4522` | `1818-4520` | `2a5f478a080d3e76186be2fc87fbdc388164a8478b5e1a1e9f2be8cd195a5783` | starts `FONTLtrGothic`; 26 real records |

Both 256 KiB banks are complete fixed-record chains. A record starts with
`FONT`, carries its ten-byte padded name at `+0x04`, and reaches the next
record by adding longword `+0x2e`. Bank 0 reaches `FONTDUMMY` at `0x03c1ee`
and a zero terminator at `0x03c22e`; bank 1 reaches `FONTDUMMY` at combined
image offset `0x07bc4c` and a zero terminator at `0x07bc8c`. The package
number sequence groups `4519/4521` as bank 0 and `4520/4522` as bank 1.

Concatenating the banks in that order produces the canonical local image
`generated/roms/cartridges/92286pc/92286pc.bin`, 524,288 bytes with SHA-256
`8cdddc5f62b92a734dcabcdc0350d5814c2c0e669d4dc200ead92875133003b7`.
The 39 plus 26 real records exactly match the manual's 65-font inventory.
Their names are 16 `Courier`, 14 `TmsRmn`, 12 `LtrGothic`, 12 `Pres Elite`,
9 `Helv`, and 2 `Line Print` records.

`tools/extract_resource_fonts.py` recognizes this fixed-`FONT` form separately
from the C06 `HEAD`/type-`0x14` form. For each font it preserves the raw
64-byte header and all 96 eight-byte glyph-table entries. The firmware-backed
entry interpretation is:

- `0x14e24..0x14eb6` probes entry `record + 0x40 + 8 * glyph`; bytes `+0/+1`
  and the low 24 bits of longword `+4` decide whether the slot is usable;
- `0x1f3a0..0x1f3d2` reads byte `+0` as stored row span, byte `+1` as row
  count, and adds the longword's low 24 bits to the record base for bitmap
  data; and
- an odd span greater than one is stored as row-prefix bytes followed by one
  trailing-byte plane, matching `A3 = A2 + (span - 1) * rows` at
  `0x1f3c6..0x1f3d0`.

The generated slot-independent asset is
`generated/roms/cartridges/92286pc/fonts.json`, schema
`hp-laserjet-resource-fonts-v1`, resource format `fixed-FONT-chain`. It is
5,076,821 bytes with SHA-256
`3cb93d9b474f2fc96d307521248c119603dddd5220f34c4ea57f7546079861f6`.
It preserves 6,240 slots: 6,175 exact bitmap payloads, 65 absent slots, and
576,866 payload bytes. The supporting disassembly is
`generated/disasm/ic30_ic13_active_object_dispatch_014ba4.lst` and
`generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst`.

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
