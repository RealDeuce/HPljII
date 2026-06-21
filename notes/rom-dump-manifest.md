# ROM Dump Manifest

Sources: local TC531000P reads; `TC531000AP.PDF`; `data/rom_manifest.json`.

The verified ROM images are local-only artifacts and are intentionally ignored
by Git. Track filenames, hashes, package locations, read method, and analysis
notes here; keep raw bytes in the working directory.

## Read Setup

- Device family: Toshiba `TC531000P`, 128K x 8 mask ROM, DIP28.
- Reader profile: `LQ500_4C_A16_PIN22@DIP28`.
- Control polarity: active-low `/CE` is correct for these parts.
- Active-high CE probe returned erased-looking data and was rejected.
- Address pin note: TC531000 pin 22 is A16; pin 20 is the CE or `/CE` mask
  option.

## Verified Raw ROMs

- IC13
  - Chip marking: SH7-9236-01
  - Local filename: `ic13_sh7-9236-01_tc531000p.bin`
  - SHA-256: `0e6fa34f0d25763ac1b687f1a24d07190ddc04057690b3e3846c114284db42d5`
  - Evidence: read1/read2 matched; tail marker `SH7-9236-01000`
- IC15
  - Chip marking: SH7-9234-01
  - Local filename: `ic15_sh7-9234-01_tc531000p.bin`
  - SHA-256: `623396d62a450794e4e0c6356009921ca7fb04a7cb7d2e15a35554630c697396`
  - Evidence: two reads matched; tail marker `SH7-9234-01`
- IC30
  - Chip marking: SH7-9235-01
  - Local filename: `ic30_sh7-9235-01_tc531000p.bin`
  - SHA-256: `63959a0ad8a4185f6a127afa23dfc89b1f0d7dd04a2a84da853abb30ffd1aeb6`
  - Evidence: three reads matched; ROM tail marker `SH7-9235-01000`
- IC32
  - Chip marking: SH7-9233-01
  - Local filename: `ic32_sh7-9233-01_tc531000p.bin`
  - SHA-256: `7f9abfe55629770b0f4bcd0e3bc671143d4cca6ec666edfac34d9e0587ae6452`
  - Evidence: read4/read5 matched; earlier reads retained as unverified local
    files

All four verified raw images are 131072 bytes.

## Interleaves

Generate local interleaves and probes with:

```sh
tools/generate_rom_artifacts.py
tools/analyze_roms.py
```

Generated files are written under `generated/`, which is also ignored by Git.

- firmware
  - Byte order: IC30, IC13
  - Local output: `generated/roms/ic30_ic13.bin`
  - SHA-256: `feeaf8d651b593af72b65d76fe6b85ee7d191278570438caeac49e0b74dbd079`
  - Interpretation: 68000 executable ROM pair
- resources
  - Byte order: IC32, IC15
  - Local output: `generated/roms/ic32_ic15.bin`
  - SHA-256: `dd4ca68e1790dc81dfdb4c364a0bc5e449f4c53e1bfc39a1536c26369eab935c`
  - Interpretation: resource/font/data ROM pair

Rejected order probes:

- IC13, IC30: reset vector/order does not produce sane 68000 startup.
- IC15, IC32: resource header strings are garbled.

## Pairing Evidence

`IC30,IC13` begins with a plausible 68000 vector table:

- Initial supervisor stack pointer: `0x00800000`.
- Reset PC: `0x00000110`.
- Exception vectors point into a regular RAM trampoline range beginning at
  `0x00780000`.

Disassembling at `0x00000110` as `m68000` produces coherent startup code:
interrupt mask setup, `RESET`, hardware register writes, RAM tests, trampoline
initialization, and jumps into later initialization routines.

`IC32,IC15` reconstructs a readable resource header:

```text
HEAD ... Copyright (C) Hewlett-Packard Company, 1986
```

MAME disassembly of the same pair does not look like executable reset/startup
code, so treat it as data until proven otherwise.
