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

## ROM Interface Boundary

The ROM-facing host interface boundary is split into normalized input
(`0xa904`) and host/status output (`0xae2c` plus FIFO helpers). For
byte-stream reproduction, `0xa904` is the first semantic boundary: parser and
payload readers receive a byte or `D7 = -1` from this routine regardless of
whether the original source was a ring buffer, macro/data-chain replay,
pushback stack, or direct hardware backend.

The detailed low-level ledger is in [host-byte-fetch.md](host-byte-fetch.md).
Status/backchannel fields are also composed in
[errors-and-status.md](errors-and-status.md).

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

- `0x780e40 == 1`: status `0x8e01`, data `0x8801`, acknowledge wait
  `0x8c01`, and control writes through `0xa601` / `0xaa01`.
- `0x780e40 != 0 && != 1`: status `0xfffee005`, data `0xfffee001`, and
  control write `0xfffee009`.

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

- exact physical names for `0x8e01`, `0x8801`, `0x8c01`,
  `0xa601`, `0xaa01`, `0xfffee005`, `0xfffee001`, `0xfffee009`,
  `0xfffe0001`, and `0xfffe0003`;
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
- `host-fetched mixed control stream reaches parser and page-record render`
- `combined host-fetched font download stream prints installed glyph`
- `parser-driven downloaded glyph rule raster stream composes through
  0x1ef6a`
- `0xb0c0/0xb022 output FIFO wraps and preserves order`
- `0xb090 waits on full FIFO then enqueues after drain`
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
  serial/parallel/RS-422/optional-I/O mapping, and any unobserved data-chain
  frame producer values.

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
