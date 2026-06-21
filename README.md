# HP LaserJet II ROM analysis

This repository contains working reverse-engineering notes, tools, ROM-dump manifests, and local
generated artifacts for the HP LaserJet Series II formatter firmware.

It exists to support LaserJet II-compatible printer output in Dreamulator:

https://github.com/RealDeuce/Dreamulator/

The goal is not to create a generic LaserJet document archive or a full printer hardware emulator.
The goal is to keep the evidence needed to implement a ROM-derived PCL Level IV input-stream
renderer: parser behavior, reset and print environment state, page geometry, raster graphics, macro
handling, built-in font selection, symbol-set mapping, glyph metrics, and final 300 dpi page pixels.

## Why this exists

Dreamulator already has printer output paths for other printers where rendering behavior is derived
from the original device rather than from a generic substitute font. The LaserJet II should follow
the same model, with a renderer whose behavior comes from the HP formatter ROMs and manuals.

The LaserJet II formatter ROMs and reference manuals contain enough behavior to identify:

- the PCL byte-stream parser, tokenizer, command dispatch tables, and payload handling paths;
- host-byte source priority, pushback/data-chain behavior, and interface handshake candidates;
- control-code behavior for CR, LF, FF, HT, BS, line-termination modes, and cursor-stack operations;
- page-size, orientation, margin, VMI/HMI, cursor-position, and reset interactions;
- raster-graphics setup, row transfer, clipping, page-object queueing, and encoded span rendering;
- rectangle/rule graphics, fill selectors, gray/pattern rendering, and band crossing behavior;
- macro definition, execution/call frame setup, overlay state, and macro record pool behavior;
- built-in font/resource scanning, font candidate selection, symbol-set patching, glyph-index
  mapping, and resource ROM glyph entries;
- the bridge from parser-produced page objects into render records and bitmap subrenderers.

Keeping verified dump hashes, notes, scripts, disassembly windows, and fixture outputs together
makes the Dreamulator implementation reproducible. When the renderer needs a behavioral detail, this
repository should show whether that detail is already known, where it came from, and which ROM
offsets or manual sections are useful for confirming it.

## Repository contents

- `notes/README.md`: Index for the emulator-oriented note set. Start here for the local
  documentation map.
- `notes/source-index.md`: What each local PDF contains and which sections are useful for
  LaserJet II work.
- `notes/pcl-to-pdf-rom-goals.md`: Project boundary: PCL/input byte stream to rendered
  pages/PDF, not full DC-controller or engine emulation.
- `notes/rom-dump-manifest.md`: Human-readable ROM dump manifest, read setup, verified hashes,
  interleave order, and rejected order probes.
- `data/rom_manifest.json`: Machine-readable raw ROM and interleave manifest consumed by the
  tooling.
- `notes/firmware-startup.md`: 68000 reset vectors, startup sequence, RAM trampoline setup,
  extension/resource probing, and early MMIO candidates.
- `notes/pcl-parser-firmware.md`: Host byte fetch, ESC tokenizer, parser tables, direct
  controls, reset, macros, record pools, and parser-side findings.
- `notes/pcl-command-map.md`: Firmware-derived high-value PCL command-to-handler map.
- `notes/page-raster-imaging.md`: Page geometry, raster state, page-object queues, render-record
  bridge, bitmap dispatch, text/raster/rule rendering paths.
- `notes/resource-rom.md`: `IC32,IC15` resource ROM role: `HEAD` records, built-in font markers,
  glyph-entry probes, symbol-set mapping, and font candidate lists.
- `notes/reverse-engineering-ledger.md`: Current anchored facts, open work, and working rules
  for continuing ROM analysis.
- `notes/hardware-overview.md`: Product identity, major assemblies, and hardware summary from
  manuals.
- `notes/formatter-interface-pca.md`: Formatter/interface PCA architecture, memory, video path,
  and host interfaces.
- `notes/dc-controller-engine.md`: Engine-controller responsibilities and the boundary between
  hardware behavior and renderer needs.
- `notes/control-panel-nvram-selftest.md`: Control panel, menu/NVRAM behavior, reset modes,
  service mode, and self tests.
- `notes/io-interfaces.md`: Centronics, RS-232C, RS-422, buffers, and flow-control facts.
- `notes/pcl4-language.md`: PCL Level IV command syntax, semantics, defaults, and quick
  reference extracted from the manuals.
- `notes/errors-and-status.md`: Status, attendance, error, and service codes relevant during
  tracing.
- `generated/analysis/`: Local generated analysis reports derived from ROM bytes. Ignored by
  git.
- `generated/disasm/`: Local focused 68000 disassembly windows. Ignored by git.
- `generated/roms/`: Local interleaved ROM images. Ignored by git.
- `tools/generate_rom_artifacts.py`: Verifies raw ROM hashes, regenerates interleaves,
  vector/header notes, and focused disassembly windows.
- `tools/analyze_roms.py`: Generates ROM analysis indexes, parser/resource reports, command
  maps, and cross-reference summaries.
- `tools/render_fixture_harness.py`: Executable fixture harness for parser, resource,
  page-object, and bitmap-renderer behavior.
- `33440-90905_HP_LaserJet_series_II_Technical_Reference_Manual_Aug1989.pdf`: HP LaserJet Series
  II Technical Reference Manual; primary PCL4 source.
- `hplaserjetclassicsiiiii.pdf`: LaserJet II/III combined service manual; hardware, formatter,
  DC controller, control panel, diagnostics, and errors.
- `5843739.pdf`: LaserJet Series II data sheet.
- `manualsplus_06859.pdf`: LaserJet III user manual archive, used only for compatibility
  boundaries and overlapping behavior.
- `TC531000AP.PDF`: Toshiba TC531000P mask ROM datasheet used for dump setup.

## ROM summary

Four 128 KiB Toshiba `TC531000P` mask ROMs from the formatter were read locally. The verified raw
ROM files are ignored by git and should remain local working inputs:

- IC13, marking `SH7-9236-01`: `ic13_sh7-9236-01_tc531000p.bin`.
  Odd/even partner for the executable firmware pair.
- IC30, marking `SH7-9235-01`: `ic30_sh7-9235-01_tc531000p.bin`.
  Odd/even partner for the executable firmware pair.
- IC15, marking `SH7-9234-01`: `ic15_sh7-9234-01_tc531000p.bin`.
  Odd/even partner for the resource/font pair.
- IC32, marking `SH7-9233-01`: `ic32_sh7-9233-01_tc531000p.bin`.
  Odd/even partner for the resource/font pair.

The current verified interleaves are:

- Firmware: IC30, IC13 byte order; local output `generated/roms/ic30_ic13.bin`.
  Interpretation: 262144-byte 68000 executable ROM pair.
- Resources: IC32, IC15 byte order; local output `generated/roms/ic32_ic15.bin`.
  Interpretation: 262144-byte resource/font/data ROM pair.

The `IC30,IC13` pair begins with a plausible 68000 vector table:

- initial supervisor stack pointer: `0x00800000`;
- reset PC: `0x00000110`;
- exception vectors point into RAM trampoline stubs beginning around `0x00780000`.

Disassembling the reset PC as `m68000` produces coherent startup code: interrupt masking, `RESET`,
early hardware writes, RAM tests, RAM trampoline generation, and extension/resource probing.

The `IC32,IC15` pair begins with a readable `HEAD` resource header and HP copyright text. It
contains repeated `COURIER` and `LINE_PRINTER` font records, dense offset tables, and glyph data
consumed by the firmware renderer path.

Generate or refresh the local interleaves and focused disassembly with:

```sh
tools/generate_rom_artifacts.py
```

Then regenerate the analysis indexes with:

```sh
tools/analyze_roms.py
```

The tools expect MAME `unidasm` at `../mame/unidasm` when disassembly output is needed.

## Key firmware structures

Current high-value executable firmware anchors in the `IC30,IC13` interleave:

| Address | Current role |
| --- | --- |
| `0x00000110` | 68000 reset entry |
| `0x000003e8` | optional `PROG` extension probing |
| `0x0000041a` | `HEAD` resource-record scanner |
| `0x0000a904` | normalized host-byte fetch source |
| `0x0000da9a` | ESC-aware byte fetch wrapper |
| `0x0000daf0` / `0x0000db74` | PCL escape tokenizer and six-byte command record builder |
| `0x00011774` | main parser loop |
| `0x000112a4` | normal parser pointer table |
| `0x000116f6` | alternate/data parser pointer table |
| `0x0000cc52` | `ESC E` software reset path |
| `0x0000fc74` | `ESC &l#A` page-size handler |
| `0x00010220` | `ESC &l#O` orientation handler |
| `0x000105d0` | delayed raster-row transfer handler for `ESC *b#W` |
| `0x00013070` | raster row page-object queueing |
| `0x00012f2e` / `0x0001387c` | compact text/glyph page-object queueing |
| `0x00013386` / `0x00013520` | rectangle/rule-like page-object queueing |
| `0x0001edc6` | page/control record to render-record bridge |
| `0x0001ef6a` | bitmap bucket walk/render entry |
| `0x0001effe` | compact text/glyph object dispatch |
| `0x0001f88e` | encoded raster span dispatch |
| `0x0001a2e4` | built-in resource/font candidate scan setup |
| `0x0001be22` | symbol-set/font-designation handler |
| `0x00017708` | font ID selection |

The parser table entries are six-byte records:

```text
byte_to_match, next_mode, handler_long
```

`notes/pcl-command-map.md` is the best entry point for command handlers that matter to rendering:
reset, direct controls, page geometry, cursor movement, raster graphics, rectangle/rule graphics,
macros, font selection, symbol sets, and downloaded-font control.

## Resource ROM and glyph path

The `IC32,IC15` resource pair maps into the firmware resource window beginning at `0x00080000`.
Current resource findings include:

- a `HEAD` header scanned by firmware routine `0x0000041a`;
- header-like built-in font records for `COURIER` and `LINE_PRINTER`;
- bit-30 built-in font context longwords consumed by renderer helper `0x0001f354`;
- glyph-entry headers with bitmap delta, mode/plane byte, row count, and pixel width fields;
- symbol-set map initialization through `0x14d9c`, symbol-set patching through `0x14f16`, and active
  symbol words at `0x783144` / `0x783146`;
- host `ESC (` / `ESC )` command flow through `0x120be` and `0x1be22`.

The compact text renderer does not use the host byte directly as a glyph index. Printable bytes flow
through active character maps at `0x782f32` or `0x783032`; the mapped byte is queued in compact text
objects and later consumed by the bitmap renderer.

## Renderer boundary

The intended renderer boundary is:

```text
PCL/input byte stream -> rendered 300 dpi pages -> PDF
```

For this project, the DC Controller and print engine are background context, not execution targets.
The PDF renderer should not need accurate fuser, scanner, motor, high-voltage, paper-jam, sensor, or
beam-timing emulation. The formatter ROMs are most useful for PCL edge cases, environment defaults,
font resources, page-object construction, and pixel placement.

## Fixture harness

`tools/render_fixture_harness.py` is the executable regression harness for ROM-derived behavior. It
currently models and verifies narrow but concrete pieces of:

- host byte source priority and direct hardware input paths;
- PCL numeric token records and delayed payload dispatch;
- control-code side effects and `ESC E` reset publication behavior;
- page geometry, orientation, margins, cursor positioning, and line-termination interactions;
- raster command/data streams, row-object queueing, bridge behavior, and encoded span rendering;
- rectangle/rule command streams and gray/pattern fill rendering;
- built-in glyph resource resolution and compact glyph row-copy behavior;
- symbol-set selection and map patching;
- macro command records, data-chain frame setup, and page-object composition fixtures.

Run it after the generated ROM artifacts exist:

```sh
tools/render_fixture_harness.py
```

It emits or refreshes local reports under `generated/analysis/`.

## How this should be used by Dreamulator work

Use this repository as the evidence pack for the LaserJet II renderer:

1. Keep verified local raw ROM dumps at the filenames listed in `data/rom_manifest.json`; they are
   ignored by git.
2. Regenerate interleaves and disassembly with `tools/generate_rom_artifacts.py`.
3. Regenerate analysis reports with `tools/analyze_roms.py`.
4. Use `notes/pcl-parser-firmware.md` and `notes/pcl-command-map.md` for parser and command
   behavior.
5. Use `notes/page-raster-imaging.md` for page geometry, object queues, rendering bridge, and bitmap
   dispatch.
6. Use `notes/resource-rom.md` for built-in font/resource and glyph-index behavior.
7. Use `tools/render_fixture_harness.py` as the regression point for any behavior ported into
   Dreamulator.
8. When a new emulator behavior is unclear, add the trace, generated report, or fixture here first,
   then port the behavior into Dreamulator.

The desired end state is a LaserJet II-compatible output path whose PCL parser, page geometry,
built-in font raster data, symbol-set behavior, graphics modes, and final pixel placement come from
this ROM analysis rather than from host fonts or approximations.
