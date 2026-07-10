# DC Controller and Engine Interface

Sources: `hplaserjetclassicsiiiii.pdf` ch. 5 sections 5-2 through 5-6, ch. 7
table 7-53 and timing chart.

## Owner Summary

This note owns the physical formatter/DC engine boundary after the ROM has
selected published page/control records and rendered band buffers. It ties the
service-manual connector signals to the ROM-visible scheduler, wait-object,
and MMIO timing edges without treating physical engine behavior as a hidden
parser or bitmap-renderer step.

Primary boundary:

- ROM-local page rendering is documented up to published-record selection,
  render-work setup, active band dispatch, and row-buffer writes in
  [active-render-scheduler.md](active-render-scheduler.md#owner-summary) and
  [page-raster-imaging.md](page-raster-imaging.md#pixel-generation-owner-summary).
- The formatter/DC edge begins when ROM paths wait on or update timing/status
  fields around `0x0d52..0x0f7a`, `0x0f84..0x10f2`, `0x10bc..0x1282`,
  `0x1cf8..0x1ea8`, `0xa680`, and `0x1eba4..0x1ecd2`.
- Service-manual connector `J205` names likely physical signals:
  `BD`, `VDO`, `VSREQ`, `VSYNC`, `PRNT`, `CMND`, `CCLK`, `CBSY`, `STATS`,
  `PCLK`, `SBSY`, `RDY`, `PPRDY`, and `CPRDY`.
- Current ROM evidence has not mapped those signal names one-to-one to MMIO
  bits such as `$8000`, `$8a01`, `$a200`, `$a400`, `$a601`, `$a801`,
  `$aa01`, `0xfffe0001`, or `0xfffe0003`.

Field groups:

- Canonical ROM-visible scheduler state:
  published pool head `0x780ea6`, scheduler cursor `0x780eaa`, active source
  `0x780eae`, render work selector `0x7820bc`, active render pointer
  `0x783a18`, render work band word `+0x10`, and wait-object records.
- Derived/cache state:
  scan/status latches `0x78398c`, `0x78399e`, `0x78399f`, shadow byte
  `0x7828f9`, output tables `0x782900` / `0x782914`, and render-band caches
  `0x783a20`, `0x783a22`, `0x783a28`, and `0x783a1c`.
- Firmware bookkeeping:
  timer/status divider bytes, wait-object queue state, active-pool wrapper
  flags, timeout/attention flags, and MMIO output shadows.
- Hardware/external state:
  physical DC Controller timing, beam-detect/video synchronization,
  ready/busy handshakes, motor/laser/paper/fuser hardware, and connector
  signal identities.
- Unknown:
  exact register-to-pin mapping and physical timing conditions. These are
  hardware/MMIO boundaries, not unknown parser dispatch, page-object storage,
  render-helper selection, or pixel composition behavior.

Output effect:

- Hardware timing can wake, stall, pace, or abort scheduler work when it
  changes ROM-visible fields such as wait-object state, ready/busy predicates,
  selected source record, render band word, or render-entry call count.
- Once the same normalized bytes, page records, scheduler state, and band
  calls reach the ROM render helpers, pixel rows are defined by the ROM-local
  page/render documentation rather than by service-manual signal names.

## Role

The DC Controller PCA is the machine control system. It coordinates:

- Paper motion.
- Laser drive.
- Scanner motor and main motor drive.
- Erase lamps.
- High-voltage system.
- Fuser temperature.
- Paper size and paper availability.
- +24 V power operation.
- Machine status reported to the Interface PCA.

The Interface PCA formats pages and sends commands/video; the DC
Controller turns those into engine actions and status.

## Functional Blocks Around the DC Controller

- Interface PCA: host I/O, PCL, page composition, video data, user
  interface.
- DC Controller PCA: engine timing/control.
- Laser/scanning assembly: laser diode, polygon/scanner motor, beam
  detect path.
- DC power supply/main motor driver.
- High-voltage power supply.
- Paper control PCA and solenoids.
- Fuser and delivery sensor.
- EP-S cartridge and cartridge sensitivity switches.

## Formatter/DC Connector Signals (`J205`)

The service manual signal table gives the Interface/Formatter to DC
Controller connector as:

| Pin | Signal | Direction / meaning |
| --- | --- | --- |
| J205-A1 | `SG` | Signal ground |
| J205-A2 | `PPRDY` | Printer power ready |
| J205-A3 | `VSREQ` | Vertical sync request |
| J205-A4 | `STATS` | DC Controller status |
| J205-A5 | `CBSY` | Interface PCA sending command to DC Controller |
| J205-A6 | `VSYNC` | Vertical sync pulse |
| J205-A7 | `VDO` | Video data from Interface PCA |
| J205-A8 | `CCLK` | Command strobe from Interface PCA |
| J205-A9 | `-5V` | -5 Vdc |
| J205-A10 | unused | Not used |
| J205-B1 | `BD` | Beam detect / horizontal sync pulse |
| J205-B2 | `RDY` | Printer ready |
| J205-B3 | `SBSY` | DC Controller sending status to Interface PCA |
| J205-B4 | `PCLK` | Status strobe from DC Controller |
| J205-B5 | `PRNT` | Initiates printing operation |
| J205-B6 | `CPRDY` | Interface PCA power ready |
| J205-B7 | `CMND` | Interface PCA command |
| J205-B8 | unused | Not used |
| J205-B9 | `+24VA` | +24 Vdc |
| J205-B10 | `FG` | Frame ground |

Emulator implication: the formatter ROM likely treats the engine as a
command/status peripheral with busy/strobe handshakes plus video and
sync lines.

## Laser and Scanner Signals

Laser PCA connector `J202`:

| Pin | Signal | Meaning |
| --- | --- | --- |
| J202-01 | `DSADJ` | Photodiode sensitivity adjustment bias |
| J202-02 | `PD` | Photodiode feedback for laser power |
| J202-03 | `LDRV` | Laser diode current source, modulated by formatter video |
| J202-04 | `+5 Vdc` | +5 Vdc |
| J202-05 | `FG` | Frame ground |

Scanner motor connector `J203`:

| Pin | Signal | Meaning |
| --- | --- | --- |
| J203-01 | `FG-` | Scanner motor tach feedback |
| J203-02 | `GND(FG)` | Ground |
| J203-03 | `FG+` | Scanner motor tach feedback |
| J203-04 | `GND(FG)` | Ground |
| J203-05 | `SCNCONT` | Scanner motor speed control voltage |
| J203-06 | `GND` | Ground |
| J203-07 | `+24VA` | +24A Vdc |

`LED201` on the DC Controller indicates scanner motor at correct speed.

## Beam Detect

- The laser beam sweeps across a six-faced rotating polygon mirror.
- Before each sweep reaches the drum, it reflects into a fiber optic
  cable.
- The DC Controller converts this light pulse into `BD`, the beam detect
  / horizontal sync pulse.
- `BD` synchronizes one scan line of video data.
- Once beam-detect synchronization is established, video data from the
  Interface PCA can be transferred to modulate the laser diode. The
  service manual describes the print period as beginning when the DC
  Controller receives `VDO` from the Interface/Formatter PCA and ending
  when the last line of print data is transmitted.
- Loss of beam detect is associated with `41 ERROR` first; if it cannot
  recover after about two seconds, `51 ERROR` occurs.

The beam-detect timing window is owned by the DC Controller. For ROM
pixel reproduction, this means `BD` is a physical pacing/sync input to
the formatter-side video path rather than a PCL or page-object semantic
field. A hardware emulator needs to provide plausible `BD` and
ready/status timing; a byte-stream renderer only needs the resulting
formatter-visible state when that timing changes which page record or
band is rendered.

## ROM Timing Boundary

Current ROM work has named the software-visible side of the formatter/DC
timing boundary, but not the register-to-pin decode:

- `0x0d52..0x0f7a`: periodic timer/status trampoline. It acknowledges a
  tick through `0xffff2000`, debounces low-MMIO inputs, rotates `$a200`
  / `$a400` output tables, and updates wait-object countdowns.
- `0x0f84..0x10f2`: scan/status interrupt path. It updates
  `0x78398c`, `0x78399e`, `0x78399f`, and `$a801` shadow byte
  `0x7828f9`, then signals wait object `0x780182`.
- `0x10bc..0x1282`: trap veneers and wait-object scheduler used by
  those events.
- `0x1cf8..0x1ea8`: active-pool wrapper that consumes pending
  `0x78399e` / `0x78399f`, `$a801.6` readiness via `0xa680`, and
  timeout/attention flags.
- `0x1eba4..0x1ecd2`: active render loop that renders, throttles,
  yields, or cleans up bands before `0x1ef6a`.

Manual-correlated physical signals still requiring board/register
correlation are `BD`, `VDO`, `VSREQ`, `VSYNC`, `PRNT`, `CMND`, `CCLK`,
`CBSY`, `STATS`, `PCLK`, `SBSY`, `RDY`, `PPRDY`, and `CPRDY`. These are
the likely physical meanings behind some combination of `$8000`,
`$8a01`, `$a200`, `$a400`, `$a601`, `$a801`, `$aa01`, `0xfffe0001`, and
`0xfffe0003`, but no exact one-to-one mapping is checked in yet.

## Clock Source And Pixel-Reproduction Boundary

The exact CPU oscillator is still a board-level fact, not a ROM-semantic
field. Current disassembly and fixture evidence localizes where that fact
can affect pixels:

- Host input timing can matter before bytes enter the normalized source
  priority at `0xa904..0xab8a`. Once the same host bytes are admitted in
  the same order, parser records and page objects are deterministic ROM
  state.
- The scan/status interrupt at `0x0f84..0x10f2` is timing-sensitive. It
  tests `$8000.4`, writes `$a601 = 0xfd` on the active branch, advances
  counter `0x78398c`, compares thresholds `0x78398e` and `0x783998`,
  sets pending bytes `0x78399e` / `0x78399f`, toggles shadow byte
  `0x7828f9`, writes `$a801`, and signals wait object `0x780182`
  through `0x1036`.
- The wait-object and trap layer at `0x10bc..0x1282` converts those
  timing events into scheduler-visible state: pending bit `0x78017e.1`,
  pending object pointer `0x78017a`, active object `0x780176`, active
  priority `0x780174`, object state word `+0x0a`, wait argument `+0x0c`,
  and saved stack `+0x1a`.
- The active render path at `0x1eb2a..0x1ed84` then selects source record
  `0x780eae`, toggles render work records through `0x7820bc`, writes
  active work pointer `0x783a18`, and reaches the render entry
  `0x1ef6a`.

For byte-stream-to-pixel reproduction, the contract is therefore the
sequence of firmware-visible fields above, not the absolute oscillator
frequency. The clock becomes pixel-relevant only if it changes host byte
admission, ready/busy result, timeout branch, wait-object wake order, or
which published page/control record reaches `0x1ed84` / `0x1ef6a`.

For cycle-accurate hardware emulation, the clock source remains required
because it sets the wall-clock relation between CPU polling, `$8000` /
`$8a01` inputs, `$a200` / `$a400` / `$a601` / `$a801` / `$aa01` outputs,
and the manual-correlated `J205` signals.

## Main Motor and +24 V Control

Power connector `J212` includes:

| Pin | Signal | Meaning |
| --- | --- | --- |
| J212-01/02 | `GND` | Ground |
| J212-03/04 | `+5V` | +5 Vdc |
| J212-05 | `-5V` | -5 Vdc |
| J212-06 | `RESET` | Initializes DC Controller microprocessors |
| J212-07 | `REMOTE` | Enables +24 Vdc supplies |
| J212-08 | `1A` | Main motor drive |
| J212-09 | `A` | Main motor drive |
| J212-10 | `1B` | Main motor drive |
| J212-11 | `B` | Main motor drive |
| J212-12 | `GND` | Ground |
| J212-13 | `+24VB` | +24B Vdc |
| J212-14 | `+24VA` | +24A Vdc |

The main motor drives the pickup roller, registration assembly, drum,
feed rollers, fuser, and delivery rollers through gear trains.

## Paper Control (`J213`)

| Pin | Signal | Meaning |
| --- | --- | --- |
| J213-01 | `CSENS1` | EP-S cartridge sensitivity/presence |
| J213-02 | `CSENS2` | EP-S cartridge sensitivity/presence |
| J213-03 | `REGD` | Registration solenoid `SL302` drive |
| J213-04 | `CPUD` | Paper pickup solenoid `SL301` drive |
| J213-05 | `+24V` | +24 Vdc |
| J213-06 | `GND` | Ground |
| J213-07 | `+5V` | +5 Vdc |
| J213-08 | `PEMP` | Paper-out signal, low when paper not detected by `PS301` |
| J213-09 | `MPFS` | Manual feed sensor, paper present at `PS302` |

The OCR truncates the final row label in places; `MPFS` is the manual
paper feed sensor signal by description.

## Fuser / Erase / Fan (`J206`-`J208`)

| Connector | Signal | Meaning |
| --- | --- | --- |
| J206-01 | `+24V` | +24A Vdc |
| J206-02 | `GND 24V` | Return for +24A Vdc |
| J206-03 | `PEL` | Preconditioning erase lamps enable |
| J206-04 | `FSRTH` | Fuser thermistor temperature signal |
| J206-05 | `GND` | Ground |
| J206-06 | `PDP` | Paper delivery / exit sensor `PS331` |
| J206-07 | `+5V` | +5 Vdc |
| J207-01 | `+24VA` | Lower cooling fan drive voltage |
| J207-02 | `GND` | Ground |
| J208-01 | `FAN` | Enables upper cooling fan during printing |
| J208-02 | `FSRD` | Fuser heater drive pulse |
| J208-03 | `GND` | Ground |

`FSRD` may only be observable on a scope, according to the service
table.

## High Voltage (`J210`, `J211`)

DC Controller high-voltage control connector `J210`:

| Signal | Meaning |
| --- | --- |
| `TMODE0`, `TMODE1` | Test mode control lines |
| `DBDC` | Adds DC voltage to developing bias when low |
| `DBAC` | Adds AC voltage to developing bias when low |
| `HV1ON` | Primary corona DC high voltage when low |
| `HVTON` | Transfer corona DC high voltage when low |
| `TPA`, `TPB`, `TSTPTE` | Select engine test patterns |
| `TSTPT` | Low when test print switch is pressed |
| `RDYNH` | Printer forced ready when low |
| `LPCK` | Forces laser to selected cartridge-sensitivity power level when low |
| `CSNT1`, `CSNT2` | Laser power select |
| `SCNON` | Scanner motor starts when low |

High-voltage power supply connector `J211`:

| Signal | Meaning |
| --- | --- |
| `THV` | Enables transfer corona circuitry; +18 V disabled, 0 V enabled |
| `HVST` | High-voltage reset |
| `HVT1` | Enables primary corona circuitry; +18 V disabled, 0 V enabled |
| `DBAC` | Enables developer AC bias; +18 V disabled, 0 V enabled |
| `TSENS` | Toner sensor voltage level |
| `DBDC` | Enables developer DC bias; +18 V disabled, 0 V enabled |
| `GND` | Ground |
| `+24 Vdc` | +24 Vdc |

Some signal names on J211 are partially corrupted in OCR; descriptions
are from the service table.

## Tray and Cover Indicators

- `SW201`: right tray-size switch.
- `SW202`: middle tray-size switch.
- `SW203`: left tray-size switch.
- `SW205`: bottom cover installed / thermistor bypass switch.

## Engine Test

`15 ENGINE TEST` is activated by the physical test print button. It
prints vertical lines and bypasses the Interface PCA. It verifies the DC
Controller and print engine components independent of formatter page
generation.

In an emulator, this can become a DC Controller self-contained print
pattern state that does not require PCL or page memory.

## Minimal Engine Stub Behavior

A practical first emulator engine stub should provide:

- Power-on sequence: reset, warmup, ready.
- `RDY`, `PPRDY`, `CPRDY` behavior.
- Command/status handshakes over `CMND`/`CCLK`/`CBSY` and
  `STATS`/`PCLK`/`SBSY`.
- `BD` pulses during active print/video.
- `VSYNC` / `VSREQ` response sufficient for formatter ROM progress.
- Paper-present, tray-size, cartridge-present, fuser-ready, and no-jam
  defaults.
- Error injection for paper out, cover open, no cartridge, paper jam,
  scanner failure, fuser failure, and formatter/DC communication
  timeout.

## Open Questions for Tracing

- Exact command byte/protocol encoding on `CMND` and `STATS`.
- Whether `VSREQ` is Interface-to-engine or engine-to-Interface in
  actual hardware timing; table names alone are not enough.
- Scan line timing expected by the formatter ROM.
- Which status bits generate each control-panel message.
- How the DC Controller reports fuser warmup versus ready.
