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

## Owner Summary

This note owns the ROM-visible external-ready and service loop entered through
`0x2e38 -> 0xba48`. The loop can preempt normal host parsing, update service
register shadows, display external-ready or service messages, publish status
bits, and return through the page/font scheduler and aggregate-status helper.
It is not an imaging producer.

Primary routes:

- Entry and display:
  `0xba48` enters the external-ready path, displays `01 EXT READY` through
  `0x8c7a`, writes `$a200 = 0xff00`, and later stores the aggregate `0x36e4`
  result into `0x780e08`.
- Live-loop and shadows:
  `0xbb84` reads `$fffee00b.7`; `0xbbb2`, `0xbc56`, and `0xbc88` maintain
  shadows `0x7822eb`, `0x7822ec`, `0x7828f9`, timestamps, and ready/service
  latches.
- Text/message intake:
  `0xc340` seeds `0x782312` with `01 EXT READY`; `0xbcfe` appends bytes from
  `$fffee011` until carriage return, then displays the buffered text.
- Service/status publication:
  `0xc0ae` publishes `$fffee005.7` and `$fffee005.6` into `0x780e2e` through
  `0x9bee`; retained-storage writer `0x571e` can raise `0x780e39.3`, and
  `0xc1c6` consumes that bit as the non-returning `68 SERVICE` path.
- Teardown:
  `0xbb0a` / `0xc06e` clears service shadows, calls `0xc108`, runs the
  page/font scheduler `0x19dd2`, ignores scheduler `D7`, and stores the
  final aggregate status byte from `0x36e4`.

Field groups:

- Canonical status/output state:
  final status byte `0x780e08`, status longword `0x780e36..0x780e39`,
  external status/control register shadows at `$a200`, `$fffee00d`, and
  `$a801`, and retained-storage failure bit `0x780e39.3`.
- Derived/cache state:
  sampled register shadows `0x7822eb`, `0x7822ec`, `0x7828f9`, timing
  snapshots `0x78230a` / `0x78230e`, and text buffer state
  `0x782300..0x782322`.
- Parser scratch:
  none from PCL parser records. The text buffer is service-interface scratch,
  not host PCL parser state.
- Firmware bookkeeping:
  ready/service latches `0x782302`, `0x7822fd`, `0x7822fe`, `0x7822ff`,
  copied byte `0x7822fa`, stable service byte `0x7821aa`, timer baseline
  `0x7821ac`, and scratch bytes `0x7821e7..0x7821ef`.
- Hardware/external state:
  physical identity and timing of `$fffee00b`, `$fffee00d`, `$fffee00f`,
  `$fffee011`, `$fffee013`, `$fffee005`, `$fffee003`, `$fffee001`, `$a200`,
  `$a801`, and the retained-storage device.
- Unknown:
  board-level meaning of the external register family and some sibling service
  bits. No ROM-local page-object or render edge is unknown in this loop.

Output effect:

- The loop does not call `0x10084`, queue page objects, publish page records,
  call render entry, or write bitmap rows.
- It can affect reproduction by preempting normal parsing, changing
  service/status latches, displaying operator messages, or changing whether
  later host bytes are admitted.
- A byte-stream renderer that starts from admitted canonical state can treat
  this as no-pixel service state; a board/protocol emulator must preserve the
  register shadows, status bits, message buffer, `68 SERVICE` path, and
  teardown handoff.

## External Ready Outcome Matrix

This matrix composes `0xba48..0xc36e` into ROM-visible service/status
outcomes. The loop is outside PCL page imaging: it can preempt host parsing and
change status or service state, but it does not create page objects or bitmap
rows.

Entry and external-ready display:

- ROM path:
  `0x2e38 -> 0xba48 -> 0xbb36`.
- State category:
  canonical status/output state, derived/cache state, and firmware
  bookkeeping.
- Writers:
  displays string `0xb63b` (`01 EXT READY`) through `0x8c7a`, writes
  `$a200 = 0xff00`, clears `0x780e09`, sets entry latch `0x782302` when
  entering the loop, and eventually writes aggregate status byte `0x780e08`.
- Readers / consumers:
  external-ready loop state, status aggregation `0x36e4`, and operator/status
  display paths consume these fields.
- Output effect:
  no page pixels; the visible effect is service/display state outside the page
  renderer.
- Evidence:
  `generated/disasm/ic30_ic13_external_ready_service_loop_00ba48.lst` and
  `generated/analysis/ic30_ic13_strings.txt`.

Register shadow and message intake:

- ROM path:
  `0xbb84`, `0xbbb2`, `0xbc56`, `0xbc88`, `0xbcfe`, and `0xc340`.
- State category:
  derived/cache state, parser/status scratch, firmware bookkeeping, and
  hardware/external state.
- Writers:
  samples `$fffee00b`, writes shadows `0x7822eb`, `0x7822ec`, and
  `0x7828f9`, updates timing snapshots `0x78230a/0x78230e`, seeds
  `0x782312` with `01 EXT READY`, and appends external text bytes from
  `$fffee011` until carriage return.
- Readers / consumers:
  display helper `0x8c7a`, service dispatcher `0xc1c6`, final reset helper
  `0xc108`, and status aggregation paths consume these shadows and buffers.
- Output effect:
  no page object. The message buffer can drive operator display text and can
  preempt or delay normal parser progress.
- Evidence:
  `generated/disasm/ic30_ic13_external_service_io_00bcd8.lst` and fixture
  `0xc1c6 displays pending external-ready message`.

External status-bit publication:

- ROM path:
  `0xc0ae -> 0x9bee`.
- State category:
  canonical status/output state and hardware/external state.
- Writers:
  publishes `$fffee005.7` and `$fffee005.6` as masks `0x80` and `0x40` into
  status longword root `0x780e2e`.
- Readers / consumers:
  host/status owner paths and service dispatch consume the published status
  bits.
- Output effect:
  host/status side effect only; no page-root or render entry is involved.
- Evidence:
  `generated/disasm/ic30_ic13_status_bit_helpers_009ba2.lst` and fixture
  `0xc0ae publishes external status bits through 0x9bee`.

Retained-storage service status:

- ROM path:
  writer `0x571e -> 0x9bee`; consumer `0xc1c6 -> 0x85c0`.
- State category:
  canonical status state, canonical retained-record state, firmware
  bookkeeping, and hardware/external state.
- Writers:
  exhausted retained-record commit/readback retries set `0x780e39.3` through
  mask `0x00000008`.
- Readers / consumers:
  `0xc1c6` tests `0x780e39.3`, clears service latch `0x7822fd`, samples the
  service byte through `0xc2b8`, then calls non-returning service display
  `0x85c0`.
- Output effect:
  displays `68 SERVICE` and stops in service display; no page/image path is
  entered.
- Evidence:
  `generated/disasm/ic30_ic13_default_env_record_maintenance_0056c2.lst` and
  fixture `0xc1c6 dispatches 68 SERVICE from retained-status bit`.

Pending external-ready message:

- ROM path:
  `0xc1c6`.
- State category:
  parser/status scratch and firmware bookkeeping.
- Writers:
  consumes pending-message flag `0x782301`, displays buffer `0x782312`
  through `0x8c7a`, clears `0x782301`, and returns `D7 = 0`.
- Readers / consumers:
  caller/status loop observes the return value and cleared pending-message
  state.
- Output effect:
  operator/status display only; no page object or bitmap row.
- Evidence:
  fixture `0xc1c6 displays pending external-ready message`.

Teardown and scheduler handoff:

- ROM path:
  `0xbb0a -> 0xc06e -> 0xc108 -> 0x19dd2 -> 0x36e4`.
- State category:
  firmware bookkeeping, derived/cache state, and scheduler state.
- Writers:
  clears service shadows, writes the cleared value to `$fffee00d`, clears
  service-poll latch `0x7822fd`, calls page/font scheduler `0x19dd2`, ignores
  scheduler `D7`, and writes final aggregate status byte `0x780e08` from
  `0x36e4`.
- Readers / consumers:
  later host/status flow consumes the final aggregate byte; scheduler side
  effects are owned by the page/font scheduler matrix.
- Output effect:
  no direct pixels. Normal parser/render work can resume after service teardown
  according to the caller state.
- Evidence:
  `generated/disasm/ic30_ic13_external_service_reset_00c06e.lst`,
  [page-font-scheduler.md](page-font-scheduler.md#page-font-scheduler-outcome-matrix),
  and fixture `0xbb0a external-ready teardown ignores scheduler return`.

State grouping for this matrix:

- Canonical state:
  status byte `0x780e08`, status longwords `0x780e2e` and
  `0x780e36..0x780e39`, external control writes `$a200` / `$fffee00d` /
  `$a801`, retained-storage failure bit `0x780e39.3`, and display/message
  strings.
- Derived/cache state:
  register shadows `0x7822eb`, `0x7822ec`, `0x7828f9`, timestamp snapshots
  `0x78230a/0x78230e`, and text-buffer state `0x782300..0x782322`.
- Parser scratch:
  none from PCL parser records; the message buffer is service-interface
  scratch.
- Firmware bookkeeping:
  ready/service latches `0x782302`, `0x7822fd`, `0x7822fe`, `0x7822ff`,
  stable service byte `0x7821aa`, timer baseline `0x7821ac`, copied byte
  `0x7822fa`, and scratch bytes `0x7821e7..0x7821ef`.
- Hardware/external state:
  physical identity and timing of the `$fffee00*`, `$a200`, `$a801`,
  retained-storage, and service/panel interfaces.
- Unknown:
  board-level device identity and some sibling service-bit names. No ROM-local
  page-object, publication, render, or bitmap-write edge is unknown in this
  service loop.

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

## Retained-Storage Service Status Paths

The ROM has two separate retained-storage failure surfaces. They share the
default-record state block but do not have the same software edge.

Commit/readback failure is a deferred service-status bit:

- Producer: default-record maintenance helper `0x571e` retries commit helper
  `0x96c4`. In the direct commit branch, exhausted attempts through
  `0x57ea..0x5808` reach `0x59f4..0x5a04`; in the normal maintenance branch,
  exhausted outer retries through `0x593c..0x59ce` reach
  `0x59b0..0x59ba`.
- State write: both exits call `0x9bee(0x780e36, 0x00000008)`. Since
  `0x780e36..0x780e39` is a big-endian status longword, this sets bit `3` of
  byte `0x780e39`.
- Consumer: external-service dispatcher `0xc1c6` tests aggregate bits
  `0x780e36 & 0x18`, clears `0x7822fd`, samples the service byte through
  `0xc2b8`, then tests `0x780e39.3` at `0xc1f4..0xc1fc`.
- Output effect: when the bit is set, `0xc1c6` calls `0x85c0`; `0x85c0`
  displays string `0xb45c` (`68 SERVICE`) through wrapper `0x8c90` and then
  loops forever at `0x85d0`. No page root, page object, publication, or render
  entry is involved.

Startup retained-record load is a separate active-record validation path:

- Producer/read path: `0x5a16` temporarily writes all
  `0x780eba..0x780ed8` dirty flags to `1`, calls retained read helper
  `0x97e4`, then clears the same flags. The helper does not return a success
  value that its startup caller branches on.
- Consumer/error path: active-bank selector `0x56c2` scans record word-2
  entries at `0x780eda + 2*D5` for bit `15`. If the scan passes the modeled
  retained-record groups without finding an active marker, `0x56f0..0x56fe`
  calls `0x1284(0xe2, 0x21)`.
- Output effect: `0x1284` uses string base `0xb44b`, which is `67 SERVICE` in
  `generated/analysis/ic30_ic13_strings.txt`. This path is not the same as
  the `0x571e -> 0x9bee -> 0xc1c6 -> 0x85c0` `68 SERVICE` path, and no ROM
  edge has been found that treats failed startup readback as an implicit
  `0xba3e` / `0xba44` factory-default fallback.

State classification for this service block:

- Canonical status: status longword `0x780e36..0x780e39`; bit
  `0x780e39.3` is the retained commit/readback failure consumed as
  `68 SERVICE`.
- Canonical retained records: backing words under `0x780eda`, active-bank
  selector `0x7822d5`, active marker bit `15` in the scanned word-2 entries,
  and dirty/read-mask flags `0x780eba..0x780ed8`.
- Derived/cache: commit/readback buffers `0x782252..0x782270` and
  `0x782232..0x782250`, maintenance counter `0x780ef0`, active/status word
  `0x780ede`, and service-loop shadows `0x7822eb`, `0x7822ec`, and
  `0x7828f9`.
- Firmware bookkeeping: retry counters and loop locals inside
  `0x571e`, service-poll latch `0x7822fd`, service byte cache `0x7821aa`, and
  message/display fields touched by `0x1284`, `0x85c0`, and `0x8c90`.
- Hardware/external: the physical retained-storage device behind `$a400` /
  `$8c01`, the external conditions that make `0x96c4` fail repeatedly, and
  the board-level source of the startup retained data read by `0x97e4`.

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

## Evidence Status

Direct ROM evidence covers the loop structure, `01 EXT READY` string identity, `68
SERVICE` display boundary, retained-storage commit-failure writer, status-shadow fields,
register writes, and fixture-backed `0xc0ae` / `0xc1c6` behavior.

The remaining boundary is the physical identity of the external register family. The
strings and loop behavior establish a service/external-interface role, but board-level
device mapping is still unresolved.

## Remaining Edges

- `0x571e -> 0x9bee -> 0xc1c6 -> 0x85c0`: no ROM-local software edge remains
  between the retained commit/readback failure writer and `68 SERVICE`
  display consumer. The unresolved boundary is the physical retained-storage
  condition that makes `0x96c4` fail through all retry attempts.
- `0x5a16 -> 0x97e4 -> 0x56c2 -> 0x1284`: startup retained-record load and
  active-record validation are bounded as a separate `67 SERVICE` path. No
  ROM edge from failed power-on readback into the `0xba3e` / `0xba44`
  factory-default fallback has been found; the remaining boundary is the
  physical retained-storage content/device behavior that leads to missing
  active markers.
- `$fffee00*`, `$a200`, and `$a801`: ROM-visible traffic is bounded; physical
  device and pin-level meanings remain board-level work.
- `0xba48` full loop: no fixture currently drives `$fffee00b` through the
  outer live-condition transition in one full modeled session. The teardown
  caller contract after `0xc108` is fixture-backed.
