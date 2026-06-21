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

Configuration is stored in NVRAM. HP 33440 factory default I/O is serial. HP
33449 factory default is parallel.

## Parallel Connector

36-pin Centronics-style connector. Technical Reference says printer receptacle
is Amphenol `850-57FE-403600-20` or equivalent. Cable plug must be compatible
with Amphenol `57-30360`. Recommended cable length: under 10 feet.

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
- During normal transfer, the printer produces `-Ack` before `Busy` returns low.
- `Busy` remains high when `-Fault` is low or the I/O buffer is full.
- On offline-to-online, `Select` goes high, the printer sends an `-Ack`, and
  `Busy` goes low.
- On online-to-offline, `Select` goes low; the printer can still accept a late
  character without data loss.

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

- Outputs `-Ack`, `Busy`, `Paper Error`, `Select`, `Auxout1`, `Auxout2`, and
  `-Fault` use SN7407 or equivalent open-collector buffers with pullups between
  1K and 3.3K to +5 V.
- Data inputs use SN74LS241 or equivalent hysteresis buffers with 1K pullup to
  +5 V.
- Strobe input uses SN74LS14 hysteresis buffer, 680 ohm pullup to +5 V, and 33
  pF to ground.

## Serial Connector

Serial uses a 25-pin D-sub female connector. User cable plug is male 25-pin
D-sub.

RS-232C cable length: under 15 m / 50 ft. RS-422 cable length: up to 1200 m /
4000 ft.

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

The HP 33440 selects RS-232C or RS-422 with a physical switch inside the back
cover:

- Down: RS-232C.
- Up: RS-422.
- Factory shipped as RS-232C.

The HP 33449 selects RS-232C/RS-422 from the control panel; do not assume this
for HP 33440.

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

- I/O buffer has less than 128 bytes of data, meaning at least 896 bytes empty.
- Printer is online.
- Printer is not busy.

`ROBUST XON=ON` makes the printer repeat XON once per second until data arrives.
Factory setting is on.

Printer sends XOFF when any is true:

- I/O buffer has 64 or fewer bytes empty.
- Printer is offline.
- Printer is busy.

If host keeps sending after XOFF, the printer sends more XOFFs as remaining
empty space reaches 32, 16, 8, 4, 2, 1, and 0 bytes. It also sends XOFF when
power-on state changes from `05 SELF TEST` to `02 WARMING UP`.

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

- `22 ERROR`: protocol mismatch or host/printer communication problem, often
  handshake or baud/config mismatch.
- `40 ERROR`: data transfer error, including host powered off while printer is
  online or mismatched baud rate.

The printer does not support Enquire/Acknowledge (`ENQ/ACK`) protocol.

## Emulator Takeaways

- Serial emulation needs both in-band XON/XOFF and DTR state even if the host
  only uses one.
- The 1 KB I/O buffer and thresholds are concrete and should be modeled for
  compatibility tests.
- Parallel emulation should support accepting a late character during
  online-to-offline transition.
- `-Input Prime` should be ignored.
- `+5 V` on Centronics pin 18 is compatibility sense only, not external power.
