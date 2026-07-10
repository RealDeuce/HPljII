# Hardware Overview

Sources: `hplaserjetclassicsiiiii.pdf` ch. 1, ch. 5, ch. 6; `5843739.pdf`.

## Owner Summary

This note owns product and engine context for the ROM documentation. It
separates manual hardware facts that bound the LaserJet II target from
ROM-visible state that can change byte admission, page-object construction,
render scheduling, or final row buffers. It is not the owner for parser
handlers, page records, resource bytes, or formatter/DC register decoding.

Primary route into the ROM model:

- Product identity and PCL level identify the target as HP 33440A /
  LaserJet Series II, a 300 dpi PCL Level IV printer.
- Formatter/interface details that affect the disassembly are owned by
  [formatter-interface-pca.md](formatter-interface-pca.md): 68000-family CPU
  evidence, ROM package pairing, DRAM/NVRAM context, built-in resource decode,
  and board-level provenance boundaries. Start with its
  `Formatter Boundary Outcome Matrix` for ROM-visible dataflow effects.
- Host interface facts that affect byte streams are owned by
  [io-interfaces.md](io-interfaces.md#owner-summary) and
  [host-byte-fetch.md](host-byte-fetch.md#owner-summary). Those notes reduce
  serial, parallel, optional I/O, pushback, ring, and macro/data-chain replay
  sources to the normalized `0xa904` byte-source contract.
- Engine facts that affect rendered output timing are owned by
  [dc-controller-engine.md](dc-controller-engine.md#owner-summary),
  [active-render-scheduler.md](active-render-scheduler.md#owner-summary), and
  [page-raster-imaging.md](page-raster-imaging.md#pixel-generation-owner-summary).
  Those notes stop at ROM-visible scheduler fields, wait objects, render work
  records, band words, and row buffers.

State classification:

- Canonical product context: model `33440A`, PCL Level IV language, 300 x 300
  dpi resolution, Canon SX-family engine, 512 KB internal RAM, supported memory
  expansion, built-in fixed-pitch fonts, and standard paper/media limits.
- Canonical ROM-visible hardware state: only the fields documented in the
  owner notes above, such as normalized input bytes from `0xa904`, host-output
  FIFO fields, page/control records, wait-object state, active render pointer
  `0x783a18`, and scheduler band fields.
- Derived/cache state: manual timing, paper-path, engine, and sensor facts
  after they have been reduced to ROM-visible status bits, wait-object events,
  page-control state, or scheduler decisions by traced firmware.
- Firmware bookkeeping: none owned here. Formatter bookkeeping fields are
  classified by the parser, page, scheduler, resource, status, and reset
  owner notes.
- Hardware/external state: motors, laser/scanner assembly, beam detect,
  paper sensors, fuser, cartridge sensitivity switches, DC Controller timing,
  connector signals, and electrical host-interface details before the ROM
  observes them through registers or admitted bytes.
- Unknown: physical register-to-connector mapping, exact MMIO-to-signal
  decode, optional board/resource contents, and service-manual names for some
  ROM status categories. These are tracked as exact boundaries in
  [unresolved-boundaries.md](unresolved-boundaries.md).

Output effect:

- Hardware context does not draw pixels by itself. Pixel-producing behavior in
  the checked-in model comes from parser-selected command handlers, page-root
  objects, publication, render scheduling, and bitmap helpers.
- Hardware facts become pixel-relevant only when they change ROM-visible
  state: admitted byte order, status/ready branch, wait-object wake order,
  selected page/control record, render band word, resource byte source, or
  render input buffer.
- Physical paper timing, toner transfer, fuser behavior, and service-message
  wording are correlation targets for hardware emulation or manual mapping,
  not substitutes for ROM disassembly evidence.

Evidence and boundaries:

- Manual evidence is the service manual and product data sheet cited above.
- ROM evidence is the owner-note chain linked in this summary, especially
  `0xa904` byte admission, `0xff1e` publication, `0x1ed84` / `0x1edc6`
  render bridge, active scheduler ranges `0x1eb2a..0x1ed84`, and render entry
  `0x1ef6a`.
- The relevant unresolved hardware boundaries are direct host MMIO banks,
  ring/status bridge registers, optional resource windows, retained storage,
  folded status category names, and active render device handoff in
  [unresolved-boundaries.md](unresolved-boundaries.md#host-and-hardware-boundaries).

## Identity

- Product: HP LaserJet Series II, HP model 33440A.
- Printer language: PCL4 / PCL Level IV.
- Print engine: Canon SX-family dry electrophotographic laser engine.
- Rated resolution: 300 x 300 dpi.
- Rated speed: up to 8 pages/minute after first page.
- First page: less than 16 seconds after data receipt, application
  dependent.
- Warmup from cold power-on: less than 30 seconds.
- Typical monthly usage from data sheet: up to 5000 pages/month.

## Memory and Expansion

- Installed RAM: 512 KB total internal read/write memory.
- Standard user memory: about 395 KB.
- Expansion: one memory slot; accepts 1 MB, 2 MB, or 4 MB boards.
- Maximum total memory: 4.5 MB.
- Accessory boards listed in the data sheet:
  - `33443A` - 1 MB memory board.
  - `33444A` - 2 MB memory board.
  - `33445A` - 4 MB memory board.

## Paper Handling

- Input tray capacity: 200 sheets.
- Top output tray capacity: 100 sheets, face-down, correct order.
- Rear face-up output: about 20 sheets, reverse order.
- Standard tray sizes: letter, legal, A4, executive. The data sheet also
  mentions B5-sized input tray support.
- Envelope support: manual feed or envelope tray accessory.
- Paper weight: 60 to 135 g/m2, equivalent to 16 to 35 lb.
- Manual feed is expected for envelopes, heavier paper, odd sizes,
  labels, and transparencies.

## Built-In Fonts

The data sheet lists internal fixed-pitch fonts in portrait and
landscape:

- Courier medium, 10 cpi, 12 point.
- Courier bold, 10 cpi, 12 point.
- Compressed Line Printer, 16.66 cpi, 8.5 point.

Factory default font: Courier portrait medium, Roman-8, fixed, 10 cpi,
12 point, upright, medium stroke.

## Major External Parts

- Front: control panel, two font cartridge slots, paper tray slot,
  manual feed guides, face-down output tray, top cover release.
- Rear: serial and parallel ports, optional I/O slot, power connector,
  power switch, face-up output tray and latch, test print button.
- Expansion memory slot is under a cover; one slot on HP 33440.

## Major Internal Parts

The service manual says the HP 33440 and HP 33449 internal print-engine
parts are essentially identical. Major internal assemblies:

- Delivery assembly.
- Face-down tray and face-up output path.
- Erase lamp assembly.
- Primary corona in the EP-S cartridge.
- Beam-to-drum mirror.
- Laser/scanning assembly.
- Paper tray, separation pad, feed roller assembly.
- Registration rollers.
- Transfer corona roller and transfer corona assembly.
- Photosensitive EP drum inside EP-S cartridge.
- Feed guide assembly.
- Fusing assembly: upper fusing roller and lower pressure roller.
- Interface PCA, DC Controller PCA, DC power supply, high-voltage power
  supply, paper control PCA, fans.

## Image Formation

Image formation centers on the EP-S cartridge and proceeds through:

- Cleaning: mechanical toner removal by cleaning blade plus electrical
  cleanup by erase lamps.
- Conditioning: primary corona applies a uniform negative charge to the
  drum. The service manual describes the drum surface target as
  approximately -600 V.
- Writing: the laser/scanner discharges selected drum areas to roughly
  -100 V, creating the latent image.
- Developing: toner is applied to the discharged image.
- Transferring: transfer corona moves toner from drum to paper.
- Fusing: heat and pressure fix toner to the page.

The EP-S cartridge contains the photosensitive drum, primary corona,
developing station, toner cavity, and cleaning station. Cartridge life
is described as about 4000 pages of normal text at roughly 5 percent
coverage.

## Drum Sensitivity

The EP-S cartridge uses tabs to indicate drum sensitivity and cartridge
presence to microswitches. Service manual table 5-1 gives:

| Drum state | CSENS1 | CSENS2 |
| --- | --- | --- |
| High sensitivity | L | L |
| Medium sensitivity | L | H |
| Low sensitivity | H | L |
| Cartridge not installed | H | H |

`L` means switch activated in the manual table. The DC Controller uses
this to select laser power.

## Paper Path Timing

- Cassette feed begins after the DC Controller receives a print command
  and starts the main motor.
- About two seconds later, the paper pickup solenoid is enabled.
- The pickup roller makes one rotation and feeds paper to the
  registration rollers.
- Registration rollers are initially stopped so the paper edge bows
  against them.
- When image and paper leading edges align, the registration clutch
  solenoid starts the registration rollers.
- After transfer, paper is carried through the fuser and delivery
  rollers.
- Manual feed timing is the same except for the input sensor and a
  longer warmup allowance for heavy media. The fuser target cited for
  this path is 180 C / 355 F.

## Sensors and Switches

- `PS301`: cassette paper sensor / paper-out sensor.
- `PS302`: manual paper feed sensor.
- `PS331`: paper delivery / exit sensor at the fusing assembly.
- `SW201`, `SW202`, `SW203`: tray-size switches.
- `SW205`: bottom cover / thermistor bypass switch.
- Cartridge sensitivity/presence switches map to `CSENS1` and `CSENS2`.

## Paper Jam Conditions

The service manual describes paper delivery sensor `PS331` as detecting
jams when:

- Paper fails to reach the delivery sensor in time.
- Paper fails to clear the delivery sensor in time.
- Paper is present at the delivery sensor on power-up. If the fuser is
  still hot, the printer may eject it.

## Power

Service manual electrical specs:

- 100/115 V or 220/240 V families, 50/60 Hz depending on model.
- Printing maximum: about 870 W at 115 V, 850 W at 220 V.
- Standby: about 170 W.
- DC power supply outputs include `+5 Vdc`, `-5 Vdc`, `+24A Vdc`, and
  `+24B Vdc`.
- `+5 Vdc` comes up first and is enough to wake the DC Controller
  microprocessor.
- DC Controller asserts `REMOTE` to enable the +24 V supplies after
  initialization.

## Emulator Takeaways

- The formatter ROM should see a printer with a separately controlled
  print engine, not direct motor/sensor hardware.
- For early emulation, model the engine as a state machine with ready,
  warmup, print-in-progress, beam-detect, paper-present, paper-exit,
  fuser-ready, and fault states.
- The service manual's engine test bypasses the Interface PCA; that is a
  strong diagnostic boundary: if `15 ENGINE TEST` works, DC Controller
  and print engine are mostly functional independent of formatter ROM.
