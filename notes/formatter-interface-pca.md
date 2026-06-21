# Formatter / Interface PCA

Sources: `hplaserjetclassicsiiiii.pdf` ch. 1, ch. 5 sections 5-5 and 5-6, ch. 7 table
7-53; `33440-90905...pdf` ch. 13.

## Naming

The service manual uses:

- HP 33440: `Interface PCA`.
- HP 33449: `Formatter PCA`.
- Combined term: `Interface/Formatter PCA`.

For LaserJet II ROM work, prefer `Interface PCA`.

## Responsibilities

The Interface PCA is responsible for:

- Host communication over standard serial, standard parallel, or optional I/O.
- Control panel scanning and LCD/status display generation.
- Communication with the DC Controller PCA.
- PCL command parsing and print environment management.
- ASCII, font, raster, and graphics processing.
- Page composition into dot/image data for the engine.
- Font storage and font cartridge access.
- Configuration storage and page count storage in NVRAM.
- Self-test logic for program ROM, font ROM, RAM, DRAM controller, interface logic, and
  LEDs.

## HP 33440 Architecture

Service manual figure 5-17 describes the HP 33440 Interface PCA as these blocks:

- 16-bit CPU executing ROM programs.
- ROM storing control programs and internal character dot patterns.
- NVRAM, 32 bytes.
- SRAM, 4 KB scratch area in the CPU address space.
- Address controller gate array (`GA1`).
- DRAM, 512 KB maximum onboard.
- Optional expansion DRAM, 1 MB, 2 MB, or 4 MB.
- Bit shifter.
- Timing controller.
- I/O controller.
- Video interface with two 4 KB scan buffer memories.
- Font cartridge interface for the two cartridge slots.

## CPU

The service manual does not identify the HP 33440 CPU by part family. The prose only
says the CPU block contains a 16-bit microprocessor, and figure 5-17 labels the block
simply as `CPU`.

Do not assume it is the same as the HP 33449 without board inspection. The HP 33449
formatter is explicitly Motorola 68000-based, but that statement appears in the HP 33449
formatter section, not the HP 33440 Interface PCA section.

When the formatter board arrives, record the CPU package marking, clock source, ROM
package markings, and any gate-array markings before dumping ROMs. Those will be needed
to choose the disassembler CPU target and build the address map.

## ROM

- Maximum HP 33440 ROM capacity: 1 MB.
- ROM stores both firmware and internal character-set dot patterns.
- The address controller can change the ROM address region via jumpers attached to the
  gate array.
- The ROM is used in four separate sections.

Disassembly implication: expect vectors, code, font data, command tables, and possibly
multiple ROM regions selected or banked by the address controller.

## RAM

- Onboard DRAM: 512 KB max.
- Optional expansion DRAM: +1 MB, +2 MB, or +4 MB.
- Standard available user memory from Technical Reference: 395 KB.
- DRAM stores host input, printing/font information, page-formatting data, and formatter
  parameters.
- The CPU subdivides DRAM dynamically.
- Technical Reference memory estimates:
  - Each rule, underline, or pattern: 15 bytes.
  - Each printed character: 4.25 bytes.
  - Each raster line: raster byte count plus 10 bytes.
  - Optional memory is available as user memory.

## NVRAM

- HP 33440 Interface PCA NVRAM capacity: 32 bytes.
- Stores control-panel configuration and page count.
- Page count is current while powered. On power-off, it is rounded down to the nearest
  10-page increment and saved.
- `68 SERVICE` indicates NVRAM failure; the printer can continue with factory defaults
  until repair, but settings are lost.

See [control-panel-nvram-selftest.md](control-panel-nvram-selftest.md) for reset
behavior.

## SRAM

- 4 KB SRAM used as a scratch area in the CPU address space.
- This is likely important very early in ROM startup, before DRAM test/configuration
  finishes.

## Address Controller

- Implemented as gate array `GA1`.
- Provides ROM-region address control and DRAM addressing.
- Enables access to onboard and expansion DRAM.

ROM-tracing implication: accesses to memory control registers or gate-array mapped space
may affect ROM region selection or DRAM timing/addressing.

## Bit Shifter

The service manual says the bit shifter is used to:

- Offset printed characters.
- Overlay printed characters.
- Shift data by 1 to 15 bits.

This suggests hardware assist for horizontal positioning, raster alignment, and possibly
font compositing.

## Timing Controller

Generates:

- Timing signals for DRAM reads/writes.
- DRAM refresh signals.

## I/O Controller

Controls:

- Timing of data input from an optional I/O PCA to the CPU via the parallel interface
  connector.
- Timing of communication with the DC Controller.

## Video Interface

- Contains two 4 KB scan buffers.
- Outputs continuously converted dot data to the DC Controller.
- Formatter/DC video-related signals on connector `J205` include:
  - `VDO`: video data from Interface PCA.
  - `VSREQ`: vertical sync request.
  - `VSYNC`: vertical sync pulse.
  - `BD`: beam detect / horizontal sync pulse from engine side.
  - `PRNT`: initiates printing operation.

Emulator implication: a first formatter emulator may not need full scan-buffer fidelity,
but ROM that tests `54 SERVICE` scan-buffer behavior may touch this hardware directly.

## Font Cartridge Interface

- Two cartridge slots, left and right.
- Font cartridges are ROM cartridges containing font dot patterns.
- Optional cartridges can also overlay/replace portions of machine ROM for
  emulation/personality behavior.
- Removing/replacing cartridges while online or while data is buffered causes
  user-visible cartridge messages and can require power cycling.

Font source priority from LaserJet III user manual is soft font, left cartridge, right
cartridge, internal; confirm this against LaserJet II behavior while tracing.

## HP 33449 Contrast

LaserJet III is useful as a later comparison point but should not be copied into HP
33440 assumptions:

- CPU: Motorola 68000, 9.83 MHz.
- ROM: 2 MB; early units use six 1-Mbit EPROMs and three 4-Mbit ROMs; most use four
  4-Mbit ROMs.
- NVRAM: 1024 bits.
- DRAM: 1024 KB onboard.
- ASIC handles DRAM control, hardware assist, and video DMA.
- Adds PCL5, HP-GL/2, scalable typefaces, Resolution Enhancement, page protection,
  localized messages.

## Startup and Self-Test Areas

`05 SELF TEST` validates:

- Program ROM.
- Internal font ROM.
- Interface/Formatter PCA RAM.
- Optional RAM PCAs.
- DRAM controller.
- Interface/Formatter logic.
- LEDs.

Self-test printout reports:

- Page count.
- Program ROM date code.
- Internal font ROM date code.
- Auto Continue state.
- Installed memory.
- Symbol set.
- Printing Menu settings.
- Configuration Menu settings.

## Formatter-Related Service Errors

- `31 SERVICE`: program ROM checksum error.
- `32 SERVICE`: internal font ROM checksum error.
- `33 SERVICE`: dynamic RAM or optional memory error.
- `54 SERVICE`: laser scan buffer error.
- `55 SERVICE`: dynamic RAM controller error.
- `57 SERVICE`: miscellaneous hardware or address error on Interface/Formatter PCA.
- `68 SERVICE`: NVRAM failure.
- `55 ERROR`: undefined or unanswered status exchange between Interface/Formatter and DC
  Controller.

See [errors-and-status.md](errors-and-status.md) for a fuller table.

## Open Questions for ROM Work

- Exact HP 33440 CPU type and clock.
- Exact ROM package count and interleave/order for the incoming ROM set.
- Address map: ROM regions, NVRAM, SRAM, DRAM, gate array registers, I/O controller,
  video buffers, cartridge slots, control panel, and DC Controller port.
- Whether scan buffers are memory-mapped, port-mapped, DMA-fed, or gate-array mediated.
- How optional I/O and cartridge ROM overlay are decoded.
