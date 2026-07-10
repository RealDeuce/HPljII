# I/O Interfaces

Sources:
`33440-90905_HP_LaserJet_series_II_Technical_Reference_Manual_Aug1989.pdf`
appendix B; `hplaserjetclassicsiiiii.pdf` ch. 3 and appendix D.

## Interface Selection

The LaserJet II supports:

- Centronics-compatible parallel.
- RS-232C serial.
- RS-422 differential serial.
- Optional I/O slot for other interfaces.

Configuration is stored in NVRAM. HP 33440 factory default I/O is
serial. HP 33449 factory default is parallel.

## Owner Summary

The ROM-facing host interface boundary is split into normalized input
(`0xa904`) and host/status output (`0xae2c` plus FIFO helpers). For
byte-stream reproduction, `0xa904` is the first semantic boundary: parser and
payload readers receive a byte or `D7 = -1` from this routine regardless of
whether the original source was a ring buffer, macro/data-chain replay,
pushback stack, or direct hardware backend.

The detailed low-level ledger is in [host-byte-fetch.md](host-byte-fetch.md).
Status/backchannel fields are also composed in
[errors-and-status.md](errors-and-status.md).
External-ready/service register traffic is documented in
[external-ready-service.md](external-ready-service.md).

### Field Groups

Canonical input state:

- First pushback stack: count `0x783e8c`, pointer `0x783e8e`.
- Active data-chain frame: pointer `0x782d76`; frame `+0x00` is the
  payload/chunk pointer, `+0x04` is the byte count or `-1` end marker, byte
  `+0x08 = 4`, byte `+0x09` is the producer class, and longword `+0x0a` is an
  environment-snapshot pointer or zero.
- Second pushback stack: count `0x783e76`, pointer `0x783e78`.
- Ring input source: count `0x783e54`, read pointer `0x783e56`, write pointer
  `0x783e5a`, and bounds `0x783a4c..0x783e53`.
- Direct-input selector `0x780e40`: zero selects ring mode, `1` selects the
  short MMIO backend, and other nonzero values select the long MMIO backend.

Canonical direct input backends:

- `0x780e40 == 1`: status-ready bit `0x8e01.4`, data register
  `0x8801`, acknowledge-wait bit `0x8c01.0`, and control writes
  through `0xa601` / `0xaa01`. Handler `0xa904` writes `$a601` phase
  values `0xdf` and `0xfb`, writes two `$aa01` variants derived from
  `0x7828fa`, clears `0x7828ec`, and clears `0x7821c4` after a byte is
  accepted.
- `0x780e40 != 0 && != 1`: status `0xfffee005`, data `0xfffee001`, and
  control write `0xfffee009`. Handler `0xa904` treats
  `0xfffee005.0` as data-ready, ORs `0xfffee005.6/.7` into
  `0x780e2e` as `0x40`/`0x80`, reads accepted data from `0xfffee001`,
  then sets control-shadow bit `0xfffee009.6` and mirrors it in
  `0x7828fb`.

Canonical host/status output:

- `0x783ed2`: output FIFO byte count.
- `0x783ed4`: output FIFO read pointer.
- `0x783ed8`: output FIFO write pointer.
- `0x783e92..0x783ed1`: 64-byte output FIFO storage.
- `0x780e40`: output backend selector. Mode `0` writes through
  `0xfffe0003`; mode `1` dequeues and discards; other nonzero modes write
  through `0xfffee003`.

Derived/cache and firmware bookkeeping:

- `0x780e66`: buffered-source gate bits. Observed bits are bit `3` for the
  no-byte gate, bit `2` for the first pushback stack, bit `1` for data-chain
  frames, and bit `0` for the second pushback stack.
- `0x780e3b`: immediate no-byte gate; when paired with nonzero `0x780e66`,
  `0xa904` returns `D7 = -1` before checking buffered sources.
- `0x7821cd` / `0x7821cc`: service-needed gate and in-service marker around
  `0x10cc(0x780202)`.
- `0x7828fa` / `0x7828fb`: direct-mode control shadows written to `0xaa01` or
  `0xfffee009`.
- `0x7828ec`, `0x7821c4`, and `0x780e2e`: direct-mode active-byte,
  timeout/control, and status/error bookkeeping.
- `0x780e22`, `0x783e61`, `0x783e60`, and `0x780e62`: pending output status,
  bridge-service byte, reason byte, and last accepted status byte for
  `0xaece`.

Unknown:

- exact physical names, connector mapping, and timing for the two
  direct-input banks and the output registers: `0x8e01`, `0x8801`,
  `0x8c01`, `0xa601`, `0xaa01`, `0xfffee005`, `0xfffee001`,
  `0xfffee009`, `0xfffe0001`, and `0xfffe0003`;
- whether the observed short and long MMIO backends correspond one-to-one with
  Centronics, serial, RS-422, or optional I/O without additional glue logic;
- any data-chain frame byte `+0x09` values beyond the observed execute `2`,
  call `3`, and non-replay page-finalization `4` producers.

### Writers

- `0xa904` consumes one input source according to priority and updates source
  counts, pointers, direct-mode shadows, and status bits.
- `0x9ec0` writes pushback bytes to either `0x783e8c` / `0x783e8e` or
  `0x783e76` / `0x783e78`.
- `0xe418` writes execute/call data-chain frames; `0xe4f4` writes the
  non-replay page-finalization frame; `0xe22c` handles frame end.
- `0xa6cc` / `0xa846` feed the ring source and update bridge/status state.
- `0xb0c0`, `0xb022`, and `0xb090` enqueue, dequeue, and blocking-wait on the
  host-output FIFO.
- `0xaece` emits service/status bytes and updates `0x783e61`, `0x783e60`,
  `0x780e22`, and `0x780e62`.
- `0xae2c` drains FIFO bytes through the backend selected by `0x780e40`.

### Readers And Consumers

- Parser wrapper `0xda9a`, display-function probes, text repeat readers,
  raster payload readers, and downloaded-font payload readers call `0xa904`.
- The main parser loop and command handlers consume the returned bytes through
  `0xda9a`, `0x11774`, delayed-payload restore, or family-specific payload
  readers.
- `0xae2c` consumes the output FIFO and pending status fields. In mode `0`,
  `0xaece` builds outbound status bytes from base `0x30`; in other modes the
  worker drains or uses the alternate output backend.

### Output Effect

The input path affects pixels by deciding which byte reaches the parser next.
The same byte sequence can come from live ring input, macro/data-chain replay,
pushback stacks, or direct MMIO and still feed the same command handlers,
page-record producers, and renderers.

The output path does not draw pixels. It can affect exact reproduction only
indirectly: a full output FIFO can stall a parser-side response producer, and a
bidirectional host may react to service/status bytes, changing the later host
byte stream.

### Reproduction Contract

A byte-stream renderer or emulator must preserve these ROM-visible interface
effects before parser, command, or page-image code consumes them:

- Treat `0xa904` as the canonical inbound byte boundary. Parser wrappers,
  transparent/display readers, raster payload readers, downloaded-font payload
  readers, and macro/data-chain replay all consume the returned `D7` byte or
  `D7 = -1`.
- Preserve source priority in `0xa904`: service retry/no-byte gate, first
  pushback stack, active data-chain frame, second pushback stack, ring input,
  and then the selected direct-MMIO backend.
- Preserve the no-byte return when `0x780e66` and `0x780e3b` gate buffered
  sources. A no-byte result is not a parser byte and cannot create page
  objects.
- Preserve data-chain replay as ordinary parser input. Execute/call frames
  from `0xe418` and non-replay publication frames from `0xe4f4` feed bytes
  through the same `0xa904` return channel as host input.
- Preserve direct-input side effects only as ROM-visible state: mode `1`
  ready/data/acknowledge roles for `0x8e01`, `0x8801`, and `0x8c01`; mode
  `2` ready/data/status/control roles for `0xfffee005`, `0xfffee001`, and
  `0xfffee009`; and the shadow/status writes to `0x7828fa`, `0x7828fb`,
  `0x7828ec`, `0x7821c4`, and `0x780e2e`.
- Preserve host-output FIFO order, wrap, full-FIFO wait, and output-worker
  drain through `0xb0c0`, `0xb022`, `0xb090`, `0xaece`, and `0xae2c`.
  Output bytes do not render pixels, but FIFO backpressure can stall a
  parser-side response producer before later input is accepted.
- Treat physical connector names and MMIO timing as hardware boundaries unless
  they change one of the ROM-visible fields above.

### Interface Outcome Matrix

This matrix is the ROM-facing contract for host input and host/status output.
It separates byte-stream reproduction state from physical interface naming:
the ROM-local question is which byte or status effect reaches firmware state,
not which external connector caused it.

- Buffered source no-byte gate:
  `0xa904` first checks immediate no-byte gate `0x780e3b` with buffered-source
  gate bits `0x780e66`. When this gate is active, it returns `D7 = -1`
  before first pushback, data-chain replay, second pushback, ring input, or
  direct hardware sources. The output effect is no admitted parser byte and no
  page state change.
- First pushback stack:
  when `0x783e8c` is nonzero, `0xa904` consumes the first pushback source at
  `0x783e8e`, updates its count/pointer state, and returns the byte to parser
  wrapper `0xda9a` or a family payload reader. The downstream pixel effect is
  whatever that returned byte does through parser dispatch.
- Active data-chain frame:
  when `0x782d76` names an active frame, `0xa904` reads frame payload pointer
  `+0x00`, count `+0x04`, offset byte `+0x08`, and frame kind `+0x09`.
  Execute/call frames from `0xe418` use kinds `2` and `3`; overlay
  publication frames from `0xe4f4` use kind `4`. End markers call `0xe22c`
  and restart source selection. Replayed bytes are canonical parser input, so
  macro output has no separate renderer.
- Second pushback stack:
  after data-chain replay and before ring/direct input, `0xa904` consumes the
  second pushback source at `0x783e78` when count `0x783e76` is nonzero. Its
  output effect is the same as first pushback: one parser-visible byte and
  updated source bookkeeping.
- Ring input source:
  in normal buffered mode, `0xa904` consumes the ring source rooted at
  `0x783a4c..0x783e53`, using count `0x783e54`, read pointer `0x783e56`, and
  write pointer `0x783e5a`. Once returned, the byte is indistinguishable from
  other admitted sources to `0x11774` and command-family handlers.
- Direct input mode 1:
  with `0x780e40 == 1`, `0xa904` polls status-ready bit `0x8e01.4`, reads
  data from `0x8801`, performs handshake/control writes through `0xa601` and
  `0xaa01`, clears `0x7828ec` and `0x7821c4`, and preserves local `0x1a`
  reporting behavior. The unknown part is the physical name of this MMIO bank,
  not the parser-visible byte returned to firmware.
- Direct input mode 2:
  with `0x780e40 != 0 && != 1`, `0xa904` polls `0xfffee005.0`, reads data
  from `0xfffee001`, ORs status bits `0xfffee005.6/.7` into `0x780e2e`, and
  sets control-shadow bit `0xfffee009.6` mirrored in `0x7828fb`. This path can
  change status state as well as admit a byte.
- Host-output FIFO enqueue:
  producers such as the model-ID response call `0xb090`, which retries
  `0xb0c0` until the 64-byte FIFO at `0x783e92..0x783ed1` accepts the byte.
  When count `0x783ed2` is full, `0xb090` waits on object `0x7801e2`; this can
  stall the producer, but it creates no page object.
- Host-output worker:
  `0xae2c` consumes pending service/status fields and FIFO state. In output
  mode `0`, it can call status helper `0xaece`, dequeue FIFO bytes through
  `0xb022`, and write through the mode-0 backend. In mode `1`, it dequeues and
  discards FIFO bytes. In other nonzero modes, it writes through the alternate
  backend rooted at `0xfffee003`.
- Status-byte construction:
  `0xaece` emits service byte `0x13` from latch `0x783e61`, consumes pending
  status count `0x780e22`, reason byte `0x783e60`, and status fields such as
  `0x780e90` / `0x780e2a`, then writes host-visible status bytes. It affects
  pixels only if a bidirectional host changes later input in response.

State grouping for this matrix:

- Canonical input state:
  pushback stacks `0x783e8c/0x783e8e` and `0x783e76/0x783e78`, data-chain
  frame pointer `0x782d76`, ring count/pointers
  `0x783e54/0x783e56/0x783e5a`, direct-input selector `0x780e40`, and the
  returned byte in `D7`.
- Canonical output state:
  FIFO count/read/write/storage `0x783ed2`, `0x783ed4`, `0x783ed8`, and
  `0x783e92..0x783ed1`; backend selector `0x780e40`; service/status latches
  `0x783e61`, `0x783e60`, `0x780e22`, and `0x780e62`.
- Derived/cache state:
  source gate bits `0x780e66`, direct-mode shadows `0x7828fa` / `0x7828fb`,
  direct active-byte/status fields `0x7828ec`, `0x7821c4`, and `0x780e2e`,
  and page/status fields consumed by `0xaece`.
- Parser scratch:
  none owned by the interface layer after `D7` is returned. Parser records,
  delayed-payload snapshots, and command-family scratch begin in
  `0xda9a` / `0x11774` or the family payload reader that consumes the byte.
- Firmware bookkeeping:
  service-needed marker `0x7821cd`, in-service marker `0x7821cc`, wait object
  `0x7801e2`, data-chain frame cleanup `0xe22c`, and output-worker sleep or
  wake state.
- Hardware/external state:
  the physical identities, connector mapping, and timing for the short and
  long MMIO banks and output registers.
- Unknown:
  no ROM-local byte-source priority, FIFO ordering, or status-byte producer
  edge is unknown for the documented paths. Remaining unknowns are physical
  interface names and connector timing. Data-chain frame-kind production is
  closed for the verified ROM image: `0xe418` is called only from `0xde96` and
  `0xdebc` with kinds `2` and `3`, `0xe4f4` is called from `0xff8e` and writes
  kind `4`, and `0xe1e4` clears stale frame kind bytes to `0`.

### Confidence And Evidence

Confidence is high for source priority, service retry, no-byte return,
pushback/ring pointer movement, direct-mode `0x1a` reporting, mode-2 status
accumulation, FIFO order/wrap, and outbound status-byte construction. These
are direct ROM listings and executable fixtures.

Fixture evidence:

- `0xa904 no-byte branch returns -1 before buffered sources`
- `0xa904 services pending work then prefers first LIFO source`
- `0xa904 data-chain end marker retries before second LIFO source`
- `0xa904 buffered ring source wins before direct hardware in mode 0`
- `0xa904 direct mode 1 preserves 0x1a and clears handshake state`
- `0xa904 direct mode 2 reads ready byte and sets control-shadow bit 6`
- `0xa620/0xa668/0xa6cc engine shadow and byte bridge`
- `macro execute frame payload feeds 0xa904 data-chain bytes`
- `host-fetched mixed control stream reaches parser and page-record render`
- `combined host-fetched font download stream prints installed glyph`
- `parser-driven downloaded glyph rule raster stream composes through
  0x1ef6a`
- `0xb0c0/0xb022 output FIFO wraps and preserves order`
- `0xb090 waits on full FIFO then enqueues after drain`
- `0x2888 publishes environment mismatch or status-cache changes`
- `0x2888 sets page-environment status consumed by 0xaece`
- `0xaece emits service byte and combined status byte`
- `0xae2c drains FIFO by configured output mode`

Disassembly evidence:

- `generated/disasm/ic30_ic13_host_byte_fetch_00a904.lst`
- `generated/disasm/ic30_ic13_a801_a601_io_00a4e8.lst`
- `generated/disasm/ic30_ic13_host_output_worker_00ae2c.lst`
- `generated/disasm/ic30_ic13_host_output_fifo_00b022.lst`
- `generated/disasm/ic30_ic13_interface_output_mmio_00a1b0.lst`
- `generated/disasm/ic30_ic13_startup_byte_source_init_003178.lst`
- `generated/disasm/ic30_ic13_startup_status_ring_init_0031d6.lst`

Unresolved middle edges:

- no unresolved ROM parser/object/rendering edge remains in the normalized
  input priority or output FIFO/status paths;
- remaining interface work is physical naming/timing of the MMIO banks,
  serial/parallel/RS-422/optional-I/O mapping, and board-level timing for the
  documented status/control bits.

## Parallel Connector

36-pin Centronics-style connector. Technical Reference says printer
receptacle is Amphenol `850-57FE-403600-20` or equivalent. Cable plug
must be compatible with Amphenol `57-30360`. Recommended cable length:
under 10 feet.

| Pin | Signal | Meaning |
| --- | --- | --- |
| 1 | `-Strobe` input | Host data strobe, active low |
| 2-9 | `Data 1`..`Data 8` input | Data 1 is LSB, Data 8 is MSB |
| 10 | `-Acknlg` output | Acknowledge pulse |
| 11 | `Busy` output | High means not ready for data |
| 12 | `Paper Error` output | High for paper/operator attention conditions |
| 13 | `Select` output | High when online and no errors |
| 14, 15 | NC | No connection |
| 16 | `0 VDC` | Logic ground |
| 17 | Chassis ground | Frame ground |
| 18 | `+5 VDC` output | +5 through 220 ohm resistor, compatibility only |
| 19-27 | data/strobe returns | Grounds |
| 28 | Ack return | Ground |
| 29 | Busy return | Ground |
| 30 | Signal ground | Ground |
| 31 | `-Input Prime` input | Ignored by printer |
| 32 | `-Nfault` output | Low when offline or error/fault |
| 33 | `Auxout1` output | Always high when powered |
| 34 | NC | No connection |
| 35 | `Auxout2` output | Always high when powered |
| 36 | NC | No connection |

Signals with leading `-` are active low.

## Parallel Handshake Behavior

- Host presents data on pins 2-9.
- Host drives `-Strobe` low when data is valid.
- `Busy` goes high at the falling edge of `-Strobe`.
- During normal transfer, the printer produces `-Ack` before `Busy`
  returns low.
- `Busy` remains high when `-Fault` is low or the I/O buffer is full.
- On offline-to-online, `Select` goes high, the printer sends an `-Ack`,
  and `Busy` goes low.
- On online-to-offline, `Select` goes low; the printer can still accept
  a late character without data loss.

Timing from Technical Reference figure B-1:

| Parameter | Minimum | Typical | Maximum |
| --- | ---: | ---: | ---: |
| Data setup before `-Strobe` on | 0.5 us | | |
| Data hold after `-Strobe` off | 0.5 us | | |
| `-Strobe` pulse width | 1.0 us | | 500 us |
| `-Strobe` on to `Busy` on | 0.0 us | | 1.0 us |
| `Busy` duration online | 10.0 us | 143 us image/font, 2.0 ms text | 10 s |
| `-Ack` off to `Busy` off | 0.0 us | 2.5 us | |
| `-Ack` pulse width | 2.5 us | | 10 us |
| `Busy` off to next cycle | 0.0 us | | |

## Parallel Electrical Notes

- Outputs `-Ack`, `Busy`, `Paper Error`, `Select`, `Auxout1`, `Auxout2`,
  and `-Fault` use SN7407 or equivalent open-collector buffers with
  pullups between 1K and 3.3K to +5 V.
- Data inputs use SN74LS241 or equivalent hysteresis buffers with 1K
  pullup to +5 V.
- Strobe input uses SN74LS14 hysteresis buffer, 680 ohm pullup to +5 V,
  and 33 pF to ground.

## Serial Connector

Serial uses a 25-pin D-sub female connector. User cable plug is male
25-pin D-sub.

RS-232C cable length: under 15 m / 50 ft. RS-422 cable length: up to
1200 m / 4000 ft.

| Pin | Description | RS-232C | RS-422 | Direction |
| --- | --- | --- | --- | --- |
| 1 | Protective ground | yes | yes | - |
| 2 | Transmitted data from printer | yes | | output |
| 3 | Received data to printer | yes | | input |
| 3 | Received data inverted `RDA` | | yes | input |
| 4 | Request to send | yes | | output, high when powered |
| 5 | Clear to send | yes | | input, not required for flow-control transmit |
| 6 | Data set ready | yes | | input, not required to receive data |
| 7 | Signal ground | yes | yes | - |
| 8 | NC | | | |
| 9 | Send data inverted `SDA` | | yes | output |
| 10 | Send data non-inverted `SDB` | | yes | output |
| 11 | NC | | | |
| 18 | Receive data non-inverted `RDB` | | yes | input |
| 19 | NC/unused in table | | | |
| 20 | Data terminal ready | yes | | output |
| 25 | NC | | | |

The HP 33440 selects RS-232C or RS-422 with a physical switch inside the
back cover:

- Down: RS-232C.
- Up: RS-422.
- Factory shipped as RS-232C.

The HP 33449 selects RS-232C/RS-422 from the control panel; do not
assume this for HP 33440.

## Serial Data Format

- Asynchronous.
- 1 start bit.
- 8 data bits.
- 1 stop bit.
- No parity.

Supported baud rates:

- 300
- 600
- 1200
- 2400
- 4800
- 9600
- 19200

## Serial Flow Control

Two flow-control mechanisms are always available:

- XON/XOFF in-band protocol.
- DTR hardware protocol on pin 20.

The I/O buffer for serial flow-control decisions is 1 KB.

### XON/XOFF

- XON is DC1, hex `11`.
- XOFF is DC3, hex `13`.

Printer sends XON when all are true:

- I/O buffer has less than 128 bytes of data, meaning at least 896 bytes
  empty.
- Printer is online.
- Printer is not busy.

`ROBUST XON=ON` makes the printer repeat XON once per second until data
arrives. Factory setting is on.

Printer sends XOFF when any is true:

- I/O buffer has 64 or fewer bytes empty.
- Printer is offline.
- Printer is busy.

If host keeps sending after XOFF, the printer sends more XOFFs as
remaining empty space reaches 32, 16, 8, 4, 2, 1, and 0 bytes. It also
sends XOFF when power-on state changes from `05 SELF TEST` to
`02 WARMING UP`.

### DTR

DTR indicates ready/not-ready for data and is always operating.

Default polarity:

- `DTR POLARITY=HI`: asserted/high means ready.
- `DTR POLARITY=LO`: inverted behavior.

DTR ready conditions match XON conditions:

- Less than 128 bytes in the 1 KB buffer.
- Online.
- Not busy.

DTR not-ready conditions match XOFF conditions:

- 64 or fewer bytes empty.
- Offline.
- Busy.

## I/O Errors

- `22 ERROR`: protocol mismatch or host/printer communication problem,
  often handshake or baud/config mismatch.
- `40 ERROR`: data transfer error, including host powered off while
  printer is online or mismatched baud rate.

The printer does not support Enquire/Acknowledge (`ENQ/ACK`) protocol.

## Emulator Takeaways

- Serial emulation needs both in-band XON/XOFF and DTR state even if the
  host only uses one.
- The 1 KB I/O buffer and thresholds are concrete and should be modeled
  for compatibility tests.
- Parallel emulation should support accepting a late character during
  online-to-offline transition.
- `-Input Prime` should be ignored.
- `+5 V` on Centronics pin 18 is compatibility sense only, not external
  power.
