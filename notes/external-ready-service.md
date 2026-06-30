# External Ready And Service Loop

This note documents the ROM-visible external-ready/service loop entered through
`0x2e38 -> 0xba48`. It is a host/service-interface checkpoint that can preempt
normal parsing, display external-ready/service messages, publish status bits,
and then hand control back through the page/font scheduler and status
aggregator.

Status: composed for the multi-handler cluster `0xba48..0xc36e`, including
external-ready display, register shadowing, text/message buffering,
service-bit dispatch, retained-storage failure status, and loop teardown. It
does not create page-record objects or pixels directly.

## Evidence

- `generated/disasm/ic30_ic13_external_ready_service_loop_00ba48.lst`
- `generated/disasm/ic30_ic13_external_service_io_00bcd8.lst`
- `generated/disasm/ic30_ic13_external_service_reset_00c06e.lst`
- `generated/disasm/ic30_ic13_status_message_selection_008430.lst`
- `generated/disasm/ic30_ic13_default_env_record_maintenance_0056c2.lst`
- `generated/disasm/ic30_ic13_status_bit_helpers_009ba2.lst`
- `generated/analysis/ic30_ic13_strings.txt`
- `generated/analysis/ic30_ic13_long_reference_scan.md`
- `notes/semantic-state-model.md` section
  `External Ready And Service Status Loop`
- `notes/errors-and-status.md`
- `notes/io-interfaces.md`

Primary fixtures:

- `0xc0ae publishes external status bits through 0x9bee`
- `0xc1c6 dispatches 68 SERVICE from retained-status bit`
- `0xc1c6 displays pending external-ready message`
- `0xbb0a external-ready teardown ignores scheduler return`

## Field Groups

Canonical status/output state:

- `0x780e08`: final status byte written from the `0x36e4` aggregate result on
  bypass and teardown exits.
- `0x780e36..0x780e39`: status longword. `0x9bee` ORs masks into this
  longword; `0x780e39.3` is the retained-storage failure bit consumed as
  `68 SERVICE`.
- `$a200`: written as `0xff00` by `0xba48` on loop entry and later by
  `0xbd84` as `0xa300 | (byte_from_$fffee013 << 8)`.
- `$fffee00d`: receives status/control shadow `0x7822eb`.
- `$a801`: receives low-three-bit input/status shadow `0x7828f9`.

Derived/cache state:

- `0x7822eb`: `$8a01 & 0x34` with bit 7 forced by `0xbc56`; later rewritten
  to `$fffee00d`.
- `0x7822ec`: last sampled `$fffee00b`; bit 7 is the outer live condition in
  `0xbb84`.
- `0x7828f9`: low three bits mirror `$fffee00b & 7`; bit 0 updates timing
  snapshots and selects the `0xc108` final-mark path.
- `0x78230a` / `0x78230e`: `0x780e04` timestamp snapshots used by `0xbdae`.

Parser/status scratch:

- `0x782300`: byte count for text accumulated in `0x782312`.
- `0x782301`: pending-message flag consumed by the non-error branch in
  `0xc1c6`.
- `0x782312..0x782322`: 16-byte text buffer. `0xc340` seeds it from string
  `0xb63b` (`01 EXT READY`), and `0xbcfe` appends bytes from `$fffee011`.
- `0x7821aa`: last debounced `$8000.w` byte sampled by `0xc2b8`.
- `0x7821ac`: timer baseline used by `0xc2f8`.

Firmware bookkeeping:

- `0x782302`: handshake/ready latch written by `0xbb36`, `0xbbb2`, and
  `0xbdae`.
- `0x7822fd`: service-poll enabled latch set by `0xbb66`, cleared by
  `0xc06e`, and cleared by `0xc1c6` before service/error dispatch.
- `0x7822fe`: deferred-action latch set by `0xbbb2` and consumed by `0xc092`.
- `0x7822ff`: edge-tracking latch maintained by `0xbbb2`.
- `0x7822fa`: byte copied from `$fffee001` by `0xbdae`.
- `0x7821b0`: set by `0xc2b8` on debounced service byte `0xfd` and by
  `0xc2f8` after timer delta `0xc9`.
- `0x7821e7` and `0x7821e8..0x7821ef`: scratch bytes managed by
  `0xbf4a` / `0xbfe2`.

Unknown:

- Board-level identity of `$fffee00b`, `$fffee00d`, `$fffee00f`,
  `$fffee011`, `$fffee013`, `$fffee005`, `$fffee003`, `$fffee001`, `$a200`,
  and `$a801`.
- Exact user-visible names for sibling service bits `0x780e39.4` and
  `0x780e31.6/7`.
- Whether the external register family maps to optional I/O, formatter
  service hardware, or another board-level interface without additional glue.

## Writers

- `0xba48` writes `0x7822da`, clears `0x780e09`, displays `0xb63b`
  (`01 EXT READY`) through `0x8c7a`, writes `$a200 = 0xff00`, and stores the
  final `0x36e4` result into `0x780e08`.
- `0xbb36` clears `0x782302`, calls `0x6f32(0x4c)`, and sets
  `0x782302 = 1` only when entering the external-ready loop.
- `0xbb66` sets `0x7822eb.7`, refreshes `$fffee00d` through `0xbc56`, and
  sets `0x7822fd`.
- `0xbbb2`, `0xbc56`, and `0xbc88` maintain `0x7822eb`, `0x7822ec`,
  `0x7828f9`, `0x7822fe`, `0x7822ff`, `0x78230a`, `0x78230e`, and
  `0x782302`.
- `0xbcfe` appends masked printable bytes from `$fffee011` into
  `0x782312`; carriage return terminates and displays the buffer through
  `0x8c7a`.
- `0xbd84` writes `$a200` from `$fffee013`.
- `0xbdae` sets `0x782302`, can clear bit 0 in `0x780e32` through `0x9c0c`,
  copies `$fffee001` into `0x7822fa`, and writes `$fffee003` after the
  `$fffee005.1` branch accepts a byte.
- `0xc06e` clears `0x7822eb`, writes the cleared value to `$fffee00d`, and
  clears `0x7822fd`.
- `0xc092` consumes `0x7822fe` by calling `0x197ac` and clearing the latch.
- `0xc0ae` publishes `$fffee005.7` and `$fffee005.6` as `0x780e2e` bits
  through `0x9bee`.
- `0xc1a6` clears message/service scratch `0x782300`, `0x782301`,
  `0x7821aa`, and `0x7821ac`.
- `0xc1c6` dispatches service/error conditions. When `0x780e39.3` is set, it
  calls `0x85c0`, which displays `68 SERVICE` from string `0xb45c` through
  `0x8c90` and loops forever.
- `0x571e` is the retained-storage commit-failure writer for `0x780e39.3`.
  Its exhausted retry paths at `0x59b0..0x59ba` and `0x59f4..0x5a04` raise
  mask `0x00000008` at `0x780e36`.
- `0x9bee` is the generic set helper; with address `0x780e36` and mask
  `0x00000008`, it sets `0x780e39.3`.
- `0xc2b8` samples stable `$8000.w` bytes through `0xa3ca`, stores changed
  bytes into `0x7821aa`, and sets `0x7821b0` for byte `0xfd`.
- `0xc2f8` records a timer baseline in `0x7821ac` and sets `0x7821b0` after
  elapsed delta `0xc9`.
- `0xc340` copies 17 bytes from `01 EXT READY` string `0xb63b` into
  `0x782312`, including the terminator.

## Readers And Consumers

- `0xba48` consumes `0xbb36` and `0xbb84` return values to choose bypass,
  loop, or teardown.
- `0xbb84` consumes `$fffee00b.7` as the outer loop live condition.
- `0xbbb2` consumes `0x7822fd`, `0x7822ff`, `0x7822eb.2`, `0x7822ec.1`,
  `0x7828f9.0`, `0x780e04`, and helper `0xa45c` state.
- `0xbdae` consumes `0x782302`, timestamp deltas, `$fffee005.0/1`,
  `0xa5b0`, `0xa45c`, and parity predicate `0xbf04`.
- `0xbf04` consumes one byte and returns true only when the low eight bits
  have odd parity and bit 7 is clear.
- `0xbf4a` consumes helper `0xa45c`, mask argument bits, `0x7821e7`, and
  scratch bytes `0x7821e8..0x7821ef`; timeout/error exits return `0xc1`.
- `0xc108` consumes `0x7828f9.0` and `0x780e35.0` for final interface reset
  and status paths through `0xa42c`, `0x6798`, or `0x680c`.
- `0xc1c6` consumes `0x780e36 & 0x18`, `0x780e2e & 0xc0`,
  `0x780e39.3`, `0x780e39.4`, `0x780e31.7`, `0x780e31.6`, `0x782301`, and
  buffer `0x782312`.

## Output Effect

This cluster is not an imaging producer. It can affect exact byte-stream
reproduction by preempting normal operation, changing service/status latches,
driving hardware registers, displaying external-ready or service text, and
returning through `0xc108 -> 0x19dd2 -> 0x36e4` before normal work resumes.

Fixture `0xc0ae publishes external status bits through 0x9bee` proves
`$fffee005.7 -> 0x9bee(0x780e2e, 0x80)`, `$fffee005.6 ->
0x9bee(0x780e2e, 0x40)`, and the no-bit return path.

Fixture `0xc1c6 dispatches 68 SERVICE from retained-status bit` proves the
consumer boundary for `0x780e36 & 0x00000008`: `0xc284`, clearing
`0x7822fd`, stable service-byte sampling through `0xc2b8`, and non-returning
call `0x85c0` using string `0xb45c`.

Fixture `0xc1c6 displays pending external-ready message` proves the
no-status branch where `0x782301 == 1` displays buffer `0x782312` through
`0x8c7a`, clears `0x782301`, and returns `D7 = 0`.

Fixture `0xbb0a external-ready teardown ignores scheduler return` proves the
teardown handoff `0xc06e -> 0xc108 -> 0x19dd2 -> 0x36e4`: scheduler returns
`D7 = 0` and `D7 = 1` are recorded but ignored, and final byte `0x780e08`
comes from the following `0x36e4` aggregate result.

## Reproduction Contract

A byte-stream renderer can ignore this loop only if it starts from canonical
printer state and treats the host stream as already admitted. A board-level or
protocol-faithful emulator must preserve:

- `01 EXT READY` entry display through `0xba48` and `0xc340`;
- `$fffee00b.7` as the ROM-visible live-loop condition;
- register shadows `0x7822eb`, `0x7822ec`, and `0x7828f9`;
- service/status publication through `0xc0ae` and `0x9bee`;
- retained-storage failure bit `0x780e39.3` and the non-returning
  `0xc1c6 -> 0x85c0` `68 SERVICE` path;
- pending message buffer `0x782312` and flag `0x782301`;
- teardown through `0xc06e -> 0xc108 -> 0x19dd2 -> 0x36e4`;
- final status byte write to `0x780e08`.

## Confidence

High for the loop structure, `01 EXT READY` string identity, `68 SERVICE`
display boundary, retained-storage commit-failure writer, status-shadow
fields, register writes, and fixture-backed `0xc0ae` / `0xc1c6` behavior.

Medium for the physical identity of the external register family. The strings
and loop behavior establish a service/external-interface role, but board-level
device mapping is still unresolved.

## Remaining Edges

- `0x571e -> 0x9bee -> 0xc1c6 -> 0x85c0`: writer and consumer boundaries are
  documented and fixture-backed separately. A single live execution fixture
  covering the whole retained-storage failure path is still absent.
- `0x5a16 -> 0x97e4 -> 0x56c2 -> 0x1284`: startup retained-load failure is
  bounded separately as `67 SERVICE`; no ROM edge from failed power-on load
  into the `0xba3e` / `0xba44` factory-default fallback has been found.
- `$fffee00*`, `$a200`, and `$a801`: ROM-visible traffic is bounded; physical
  device and pin-level meanings remain board-level work.
- `0xba48` full loop: no fixture currently drives `$fffee00b` through the
  outer live-condition transition in one full modeled session. The teardown
  caller contract after `0xc108` is fixture-backed.
