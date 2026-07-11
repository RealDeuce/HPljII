# Errors and Status Messages

Sources: `hplaserjetclassicsiiiii.pdf` ch. 7 table 7-2; `33440-90905...pdf` ch.
13.

## Owner Summary

This note owns ROM status, attendance, host-output FIFO, and parser-visible
backchannel behavior. These paths matter to byte-stream reproduction because
they can return bytes to a bidirectional host, stall a parser-side producer,
or change service/status control flow. They do not create page roots, page
objects, publication records, render work, or bitmap rows.

Primary routes:

- Host-output FIFO:
  `0xb0c0` appends one byte, `0xb022` removes one byte, and blocking wrapper
  `0xb090` retries on a full FIFO using wait object `0x7801e2`.
- Output worker:
  `0xae2c` drains service byte `0x13`, pending status bytes, or FIFO bytes
  according to backend selector `0x780e40`; helper `0xaece` builds outbound
  status bytes.
- Parser-visible model-ID response:
  `ESC *r#K` and `ESC *s#^` reach wrapper `0x12034`; producer
  `0x122be..0x12326` consumes the next query byte through `0xda9a` and emits
  literal `33440A\r\n` from `0x12280..0x12288` only for query byte `0x11`
  with active record word `1` or `-1`.
- Page-environment status:
  `0x2888` compares selected page/control record fields with active
  environment state, writes `0x780e90` and `0x780e98`, and feeds host status
  and panel/service selection.
- Panel/service status:
  `0x36e4`, `0x7612`, `0x7c96..0x7e20`, `0x8656`, `0x8a48`, and display
  helpers under `0x8c7a..0x9406` fold status longwords, sensor/status bytes,
  and page-environment state into host-visible or panel-visible messages.
- Terminal error/status reports:
  stack-entry `0x1284` and register-entry `0x128c` consume a two-byte report
  code, select a status string through helper `0x158c`, display it through
  wrapper `0x8c7a`, cache the first two message bytes in
  `0x783ef0..0x783ef1`, and then enter the hardware-facing report loop. This
  is a panel/MMIO status sink, not a page-image producer.

Field groups:

- Canonical host-output state:
  FIFO storage `0x783e92..0x783ed1`, count `0x783ed2`, read pointer
  `0x783ed4`, write pointer `0x783ed8`, backend selector `0x780e40`, and
  wait object `0x7801e2`.
- Canonical parser/backchannel state:
  synthetic setup record from `0x12034 -> 0x11efe`, active parser cursor
  `0x78299e`, query byte from `0xda9a`, and literal `0x12280..0x12288`.
- Canonical status state:
  page-environment bytes `0x780e8e` / `0x780e8f`, selected page/control bytes
  `+6/+7/+8`, status root fields `0x780e12`, `0x780e0a`, `0x780e2a`,
  `0x780e32`, `0x780e2e`, and `0x780e36`.
- Canonical report state:
  two-byte report inputs at `0x1284` stack offsets `+7` / `+0x0b` or
  `0x128c` registers `D0` / `D1`, selected string pointer from `0x158c`, and
  cached message bytes `0x783ef0..0x783ef1`.
- Derived/cache state:
  pending status count `0x780e22`, service byte latch `0x783e61`, reason byte
  `0x783e60`, accepted status byte `0x780e62`, page-environment flag
  `0x780e90`, media-feed cache `0x780e98`, and display shadow buffers.
- Parser scratch:
  transient query/fetch state while `0x122be..0x12326` reads through
  `0xda9a` before either accepting query byte `0x11` or reporting another byte
  through `0x9ec0`. These bytes do not enter page/image state.
- Firmware bookkeeping:
  service latch fields, aggregate-status helper state, panel desired/shadow
  buffers, display wrapper flag `0x78296c`, attendance byte `0x7821f9`, and
  self-test/font-print selectors. Error-report bookkeeping includes saved
  stack pointer `0x783eea`, gate byte `0x7821a5`, loop counter `D4`, and
  sentinel byte `D6`.
- Hardware/external state:
  physical output backend registers, panel side effects, and DC-controller or
  sensor sources that produce attendance bits. The error-report loop reaches
  `$8000.w`, `$ffff3800`, and helper `0x1492`.
- Unknown:
  physical names/timing for output MMIO banks, panel flag-`1` effects, exact
  external protocol name for query byte `0x11`, and sensor producers for
  `0x7821f9`. Error-report physical protocol details after `0x1492` are
  also external. No ROM-local page-object or render edge is unknown here.

Output effect:

- Host backchannel bytes are protocol output, not page pixels.
- Pixel reproduction changes only indirectly if a bidirectional host reacts to
  status/model-ID bytes by sending a different future stream, or if FIFO
  fullness blocks a parser-side producer.
- A closed byte-stream renderer can treat these paths as no-page-output
  protocol state while still preserving FIFO order, blocking semantics, and
  status byte formulas when host backchannel behavior is modeled.

## Host/Status Side-Channel Decision Checkpoint

This checkpoint composes the ROM-visible host/status side channel from parser
command dispatch or status producers to host-visible bytes, panel/status
state, terminal report state, or an explicit no-page-output outcome. It starts
at parser wrapper `0x12034`, FIFO/status worker `0xae2c`,
page-environment status helper `0x2888`, aggregate status helper `0x36e4`, or
error-report helper `0x1284` / `0x128c`, and ends before any page-root or
render-record path because this family does not create pixels directly.

Decision route:

- Model-ID commands: parser forms `ESC *r#K` and `ESC *s#^` both dispatch
  wrapper `0x12034`. The wrapper calls `0x11efe`, appends a synthetic six-byte
  setup record with word `+2 = 1`, then enters `0x122be..0x12326`.
- Query gate: `0x122be..0x12326` rewinds parser cursor `0x78299e`, fetches
  the following byte through `0xda9a`, and emits literal `33440A\r\n` from
  `0x12280..0x12288` only when query byte `0x11` meets active record word
  `1` or `-1`; other query bytes go to `0x9ec0`.
- FIFO enqueue: accepted response bytes enter the 64-byte output FIFO through
  blocking helper `0xb090`, which retries `0xb0c0` and waits on object
  `0x7801e2` when FIFO count `0x783ed2` is full.
- Output worker: `0xae2c` drains service byte `0x13`, pending status bytes, or
  queued FIFO bytes according to backend selector `0x780e40`. Helper `0xaece`
  builds outbound status bytes from base `0x30`.
- Page-environment status: `0x2888` compares selected page/control bytes with
  active environment state, writes `0x780e90` / `0x780e98`, and sets
  `0x780e2a.4`; these fields feed `0xaece` and the `0x7612` status-helper
  choice.
- Aggregate status: `0x36e4` folds status longwords into `0x780e12`,
  `0x780e0e`, `0x780e0a`, and `0x780e1a`; the same fields affect `0xaece`
  status-byte bits and service-control returns.
- Error/status report: callers such as retained-record load, resource scan,
  font selection, host-output retry, or bitmap error exits call `0x1284` or
  `0x128c` with two report bytes. `0x1284` first copies stack arguments into
  registers; `0x128c` masks both report bytes, selects the message through
  `0x158c`, displays it through `0x8c7a`, caches the first two message bytes,
  and then enters the hardware-facing loop under `0x12d4..0x13b0`.

State classification:

- Canonical parser/backchannel state: synthetic setup record from
  `0x12034 -> 0x11efe`, active parser cursor `0x78299e`, accepted query byte,
  active record word `+2`, and literal `0x12280..0x12288`.
- Canonical host-output state: FIFO storage `0x783e92..0x783ed1`, count
  `0x783ed2`, read pointer `0x783ed4`, write pointer `0x783ed8`, wait object
  `0x7801e2`, and backend selector `0x780e40`.
- Canonical status state: selected page/control bytes `+6/+7/+8`, active
  environment bytes `0x780e8e` / `0x780e8f`, status longwords `0x780e12`,
  `0x780e0a`, `0x780e2a`, `0x780e32`, `0x780e2e`, and `0x780e36`.
- Canonical report state: two-byte error/status report inputs, selected
  message pointer, and cached visible bytes `0x783ef0..0x783ef1`.
- Derived/cache state: pending status count `0x780e22`, service byte latch
  `0x783e61`, reason byte `0x783e60`, accepted status byte `0x780e62`,
  page-environment flag `0x780e90`, media-feed cache `0x780e98`, and folded
  status fields `0x780e0e` / `0x780e1a`.
- Parser scratch: transient query/fetch state consumed by
  `0x122be..0x12326` before the byte is accepted or reported.
- Firmware bookkeeping: FIFO critical sections, wait-object scheduling,
  display/message shadow state, service latch fields, panel wrapper flag
  `0x78296c`, saved error-report stack pointer `0x783eea`, and gate byte
  `0x7821a5`.
- Hardware/external state: physical output backend registers selected by
  `0x780e40`, panel side effects, DC-controller or sensor inputs that produce
  attendance bits, and the error-report loop through `$8000.w`, `$ffff3800`,
  and helper `0x1492`.
- Unknown: external protocol name for accepted query byte `0x11`, physical
  names/timing for output MMIO banks, physical sensor producers for
  `0x7821f9`, and panel flag-`1` effects after `0x9406`.

Writers, readers, and output effect:

- Writers are `0x12034` / `0x11efe` / `0x122be` for response command state,
  `0xb0c0` / `0xb090` for FIFO append state, `0xb022` for FIFO removal,
  `0xaece` for outbound status bytes, `0x2888` for page-environment status,
  `0x36e4` for aggregate status fields, and `0x1284` / `0x128c` for
  terminal error/status report state.
- Readers and consumers are `0xda9a` for the model-ID query byte,
  `0xae2c` for FIFO/status worker priority, backend writers selected by
  `0x780e40`, `0x7612` / `0x8656` / `0x8a48` for service or panel messages,
  and any bidirectional host that consumes FIFO/status bytes.
- The direct output is host-visible protocol bytes or panel/service state, not
  page/image state. These paths do not call `0x10084`, `0xff1e`, `0x1ed84`,
  `0x1edc6`, or `0x1ef6a`.
- Pixel output can change only indirectly if FIFO fullness stalls a
  parser-side producer before later bytes are admitted, or if a bidirectional
  host reacts to model-ID or status bytes by sending a different future input
  stream.

Evidence and unresolved boundary:

- Parser/model-ID evidence is
  `generated/disasm/ic30_ic13_payload_dispatch_011f82.lst` and fixture
  `0x12034/0x122be model-ID response emits FIFO literal`.
- FIFO and worker evidence is
  `generated/disasm/ic30_ic13_host_output_fifo_00b022.lst`,
  `generated/disasm/ic30_ic13_host_output_worker_00ae2c.lst`,
  `generated/disasm/ic30_ic13_host_output_retry_00af7c.lst`, and fixtures
  `0xb0c0/0xb022 output FIFO wraps and preserves order`,
  `0xb090 waits on full FIFO then enqueues after drain`, and
  `0xae2c drains FIFO by configured output mode`.
- Status evidence is
  `generated/disasm/ic30_ic13_interface_status_aggregate_0036e4.lst`,
  `generated/disasm/ic30_ic13_page_environment_status_002888.lst`,
  `generated/disasm/ic30_ic13_page_pool_cursor_007612.lst`, and fixtures
  `0xaece emits service byte and combined status byte` and
  `0x2888 sets page-environment status consumed by 0xaece`.
- Error-report evidence is
  `generated/disasm/ic30_ic13_error_report_entry_001284.lst` and
  `generated/disasm/ic30_ic13_error_report_00128c.lst`, with upstream report
  callers visible in reset/default, resource-scan, font-selection,
  host-output, and bitmap listings.
- No ROM-local page-object, publication, render-scheduler, or pixel-generation
  edge remains in this side-channel checkpoint. Remaining boundaries are
  hardware/MMIO identity, external protocol naming, panel behavior, and
  physical sensor producers.

## Host/Status Outcome Matrix

This matrix is the command-family contract for side-channel paths that a
byte-stream renderer must preserve when bidirectional host behavior is in
scope. The outcomes terminate in host-visible bytes, status/panel state, a
producer wait, or an explicit no-page-output boundary; none of them creates
page roots, page objects, published records, render work, or bitmap rows.

- Model-ID accepted query:
  parser commands `ESC *r#K` and `ESC *s#^` reach wrapper `0x12034`, setup
  helper `0x11efe`, and producer `0x122be..0x12326`. Active record word
  `+2 = 1` or `-1` plus following query byte `0x11` makes the producer walk
  literal `0x12280..0x12288` (`33440A\r\n`) and enqueue each byte through
  blocking helper `0xb090`. Canonical parser/backchannel state is the
  synthetic setup record, parser cursor `0x78299e`, query byte, active record
  word, ROM literal, and FIFO state `0x783ed2` / `0x783ed4` / `0x783ed8` /
  `0x783e92..0x783ed1`. Output effect is host-visible response bytes only.
  Evidence: `generated/disasm/ic30_ic13_payload_dispatch_011f82.lst` and
  fixture `0x12034/0x122be model-ID response emits FIFO literal`.
- Model-ID rejected query:
  the same `0x12034 -> 0x11efe -> 0x122be..0x12326` route consumes a
  following byte through `0xda9a`, but bytes other than `0x11`, or active
  record words other than `1` / `-1`, branch to report/pushback helper
  `0x9ec0` instead of walking the literal. The synthetic record and query
  byte are parser scratch consumed by this producer. Output effect is no FIFO
  response and no page object. Evidence:
  `generated/disasm/ic30_ic13_payload_dispatch_011f82.lst`.
- FIFO enqueue accepted:
  helper `0xb0c0` writes one byte when count `0x783ed2 < 0x40`, stores at
  write pointer `0x783ed8`, wraps after `0x783ed1` to `0x783e92`, increments
  count, and returns success. This is canonical host-output state, not page
  state. Evidence: `generated/disasm/ic30_ic13_host_output_fifo_00b022.lst`
  and fixture `0xb0c0/0xb022 output FIFO wraps and preserves order`.
- FIFO enqueue full:
  helper `0xb0c0` returns failure with count, read pointer, write pointer, and
  FIFO storage unchanged when `0x783ed2 >= 0x40`. Blocking wrapper `0xb090`
  waits through `0x10c8(0x7801e2)` and retries the same byte, so a full FIFO
  can stall a parser-side response producer before later input bytes are
  admitted. Output effect is producer wait, not page output. Evidence:
  fixture `0xb090 waits on full FIFO then enqueues after drain`.
- FIFO dequeue accepted:
  helper `0xb022` copies the byte at read pointer `0x783ed4`, wraps after
  `0x783ed1` to `0x783e92`, decrements count `0x783ed2`, and returns success.
  Consumers are output worker `0xae2c` and backend-specific send helpers.
  Evidence: `generated/disasm/ic30_ic13_host_output_fifo_00b022.lst`.
- FIFO dequeue empty:
  helper `0xb022` clears the caller destination byte, returns failure, and
  leaves count and pointers unchanged. Worker `0xae2c` can then sleep only
  when FIFO count `0x783ed2`, pending status count `0x780e22`, and service
  byte `0x783e61` are all zero. Output effect is no host byte and no page
  output. Evidence: `generated/disasm/ic30_ic13_host_output_worker_00ae2c.lst`.
- Output worker mode `0`:
  worker `0xae2c` first calls status/service helper `0xaece`, then drains FIFO
  bytes through `0xb022` and retry helper `0xaf7c`. `0xaece` emits service
  byte `0x13` when `0x783e61` is set, otherwise builds a status byte from base
  `0x30` using `0x780e12`, `0x780e90`, `0x780e2a`, `0x780e0a`, and reason
  byte `0x783e60` while pending status count `0x780e22` is nonzero. Output
  effect is backend-visible status or FIFO bytes. Evidence:
  `generated/disasm/ic30_ic13_host_output_worker_00ae2c.lst`,
  `generated/disasm/ic30_ic13_host_output_retry_00af7c.lst`, and fixture
  `0xaece emits service byte and combined status byte`.
- Output worker mode `1`:
  worker `0xae2c` dequeues FIFO bytes through `0xb022` and loops without
  calling `0xaece`; the ROM-visible path discards those bytes. Output effect
  is FIFO drain with no status-byte emission and no page output. Evidence:
  fixture `0xae2c drains FIFO by configured output mode`.
- Output worker other nonzero modes:
  worker `0xae2c` drains FIFO bytes through `0xb022` and sends accepted bytes
  through retry helper `0xafcc`, which calls backend writer `0xa1d6` and can
  wait through `0x10d0(0x0b)`. Output effect is backend-visible FIFO bytes,
  bounded by hardware/MMIO backend identity. Evidence:
  `generated/disasm/ic30_ic13_host_output_worker_00ae2c.lst`.
- Page-environment status update:
  helper `0x2888` compares selected page/control bytes `+6/+7/+8` with
  active environment bytes `0x780e8e` / `0x780e8f`, then writes
  `0x780e90`, `0x780e98`, and bit `0x10` in `0x780e2a` for eligible media or
  environment status. Readers are `0xaece` for host status bit `0` and
  `0x7612..0x7834`, which select `0x8a48` instead of `0x8656` when
  `0x780e90` is set. Output effect is host/status or panel-message state, not
  a page object. Evidence:
  `generated/disasm/ic30_ic13_page_environment_status_002888.lst` and fixture
  `0x2888 sets page-environment status consumed by 0xaece`.
- Aggregate status update:
  helper `0x36e4` folds status longwords into `0x780e12`, `0x780e0e`,
  `0x780e0a`, and `0x780e1a`, mirrors active status into byte `0x780e68`,
  and feeds `0xaece` status-byte formulas plus service-control consumers.
  Output effect is derived status state only. Evidence:
  `generated/disasm/ic30_ic13_interface_status_aggregate_0036e4.lst`.
- Terminal error/status report:
  stack-entry `0x1284` or register-entry `0x128c` consumes a two-byte report
  code. The body masks the bytes into words, selects a status string through
  `0x158c`, displays it through wrapper `0x8c7a`, copies the first two
  selected message bytes into `0x783ef0..0x783ef1`, and then enters the
  hardware-facing loop at `0x12d4..0x13b0`. Upstream callers include
  retained-record load, resource checksum, font-selection, host-output retry,
  and bitmap error exits. Output effect is panel/MMIO report state, not page
  output. Evidence:
  `generated/disasm/ic30_ic13_error_report_entry_001284.lst`,
  `generated/disasm/ic30_ic13_error_report_00128c.lst`, and the
  [Error Report Helper](#error-report-helper) section below.

State grouping for all outcomes:

- Canonical:
  parser/model response state, FIFO storage/count/pointers, backend selector
  `0x780e40`, selected page/control bytes, active environment bytes, status
  longwords, and two-byte report inputs plus cached report bytes
  `0x783ef0..0x783ef1`.
- Derived/cache:
  pending status count `0x780e22`, service byte latch `0x783e61`, reason byte
  `0x783e60`, accepted status byte `0x780e62`, page-environment flag
  `0x780e90`, media-feed cache `0x780e98`, and folded status fields.
- Parser scratch:
  the query byte and synthetic setup record while `0x122be..0x12326` decides
  whether to emit or reject the model-ID response.
- Firmware bookkeeping:
  FIFO critical sections, wait object `0x7801e2`, worker sleeps/wakes, service
  latch cleanup, panel/display shadow state, saved report stack pointer
  `0x783eea`, and report gate byte `0x7821a5`.
- Hardware/external:
  selected output backend registers, physical panel behavior, DC-controller or
  sensor sources, and the terminal report loop through `$8000.w`,
  `$ffff3800`, and `0x1492`.
- Unknown:
  physical protocol name for query byte `0x11`, output-backend electrical
  identities, physical sensor producers, and panel flag-`1` side effects.

Unresolved boundaries:

- No ROM-local host-byte-to-page-object or page-object-to-pixel edge remains
  in this family. The exact remaining boundaries are hardware/MMIO identity
  for output backends, external protocol naming for the accepted query byte,
  physical sensor producers, report-loop electrical behavior after `0x1492`,
  and panel behavior after display helpers.

## Normal Status

| Message | Meaning |
| --- | --- |
| `00 READY` | Printer ready. |
| `02 WARMING UP` | Fuser/engine warmup. |
| `04 SELF TEST` | Continuous self-test printing. |
| `05 SELF TEST` | Self test in progress. |
| `06 PRINTING TEST` | Self-test page printing. |
| `06 FONT PRINTOUT` | Font sample pages printing. |
| `07 RESET` | Panel reset in progress. |
| `08 COLD RESET` | Cold reset in progress. |
| `09 MENU RESET` | Printing Menu reset in progress. |
| `10 RESET TO SAVE` | Reset needed to apply selected Printing Menu changes. |
| `15 ENGINE TEST` | Engine test pattern printing from physical test button. |

## ROM Status Composition

The ROM has four documented status/backchannel paths that matter to
byte-stream reproduction even though they do not draw pixels themselves:

- host/interface backchannel status through `0xae2c` / `0xaece`;
- host/interface model-ID response bytes through `0x12034` /
  `0x122be..0x12326`;
- page-environment service status through `0x2888`, `0x7612`, `0x8a48`, and
  `0x8656`.
- terminal error/status reports through `0x1284` / `0x128c`, display wrapper
  `0x8c7a`, and the report loop under `0x12d4..0x13b0`.

The low-level ledger remains in `notes/semantic-state-model.md` under
`Interface Output FIFO And Status Bytes` and
`Page Environment Status And Pool Cursor Gate`.
The external-ready/service loop and retained-storage `68 SERVICE` path are
documented in [external-ready-service.md](external-ready-service.md#owner-summary).

### Error Report Helper

Helper `0x1284` is the stack-argument entry and `0x128c` is the register-entry
body for two-byte error/status reports. This is the sink reached by startup,
resource, font, and service paths when they report a terminal code such as
`67 SERVICE`, a resource checksum error, or a font-selection error. It is a
panel/MMIO status path, not a page-object or renderer path.

Route and behavior:

- `0x1284` copies byte arguments from stack offsets `+7` and `+0x0b` into
  `D0` and `D1`, then falls into `0x128c`.
- `0x128c..0x1298` masks both bytes into words `D2` and `D3` and starts from
  string-table base `0xb44b`.
- `0x12a2..0x12b0` snapshots the current stack pointer in `0x783eea`, clears
  byte `0x7821a5`, and calls selector helper `0x158c`.
- `0x12b4..0x12c2` displays the selected message through wrapper `0x8c7a`.
- `0x12c6..0x12ce` copies the first two selected message bytes into
  `0x783ef0..0x783ef1`; the later loop reuses that two-byte buffer as the
  visible status source.
- `0x12d4..0x1354` loops on `$8000.w & 0x44`, output helper `0x1492`, and
  delay helper `0x14c6`. After more than four idle samples it calls
  `0x1356`.
- `0x1356..0x13b0` writes `0xffff` to `$ffff3800`, splits the two report bytes
  into nibbles, and indexes hex string `0x163a` to emit the code digits.

Field grouping:

- Canonical report inputs:
  byte pair `(D0,D1)` at entry `0x128c`, or the stack bytes consumed by
  `0x1284`.
- Derived/cache state:
  masked words `D2/D3`, selected message pointer `A1`, two-byte message copy
  `0x783ef0..0x783ef1`, and hex nibbles derived at `0x135e..0x136a`.
- Firmware bookkeeping:
  saved stack pointer `0x783eea`, gate byte `0x7821a5`, loop counter `D4`, and
  sentinel byte `D6`.
- Hardware/external:
  `$8000.w`, `$ffff3800`, and the physical destination driven by helper
  `0x1492`.
- Unknown:
  exact physical protocol for the repeated `0x1492` writes and the manual name
  for `0x7821a5`. The ROM-local input bytes, display wrapper, cached message
  bytes, and no-page-output boundary are documented.

Output effect:

- The helper does not allocate page roots, page records, render work, or row
  buffers.
- The helper can change visible panel/service state and can enter a repeated
  hardware-output loop. A closed byte-stream renderer should record the
  reported byte pair and selected string boundary, then stop at the hardware
  output loop unless the surrounding model explicitly includes panel/MMIO
  behavior.
- Known upstream examples include startup retained-record failure
  `0x56c2 -> 0x1284(0xe2, 0x21)` selecting string `0xb44b`
  (`67 SERVICE`), resource checksum failure `0x128c(0xe0, 0x10)`, and
  font-selection reports such as `0x1284(0xe3, 0x34)` and
  `0x128c(0xe7, 0x91)`.

### Field Groups

Canonical host-output state:

- `0x783ed2`: host-output FIFO count.
- `0x783ed4`: FIFO read pointer.
- `0x783ed8`: FIFO write pointer.
- `0x783e92..0x783ed1`: 64-byte FIFO storage.
- `0x780e40`: output backend selector. Mode `0` uses `0xfffe0001` /
  `0xfffe0003`; mode `1` dequeues and discards; other nonzero modes use
  `0xfffee005` / `0xfffee003`.

Canonical page-environment status:

- `0x780e8e`: active page-environment byte compared against selected
  page/control record byte `+7`.
- `0x780e8f`: output page-environment byte written by `0x2a14`.
- selected page/control record bytes `+6`, `+7`, and `+8`: status candidate,
  environment candidate, and service-needed byte consumed by `0x2888`.

Derived/cache status:

- `0x780e22`: pending status count consumed by `0xaece`.
- `0x783e61`: bridge-service pending byte; emits literal `0x13`.
- `0x783e60`: service-reason byte ORed into the outbound status byte.
- `0x780e62`: last accepted service/status byte from `0xaece`.
- `0x780e12`: aggregate status longword from `0x36e4`.
- `0x780e0a`: active status longword from `0x36e4`.
- `0x780e2a`: warning/status accumulator. `0x2888` sets bit `4` when it
  raises page-environment status.
- `0x780e90`: page-environment status flag. It feeds host status bit `0` in
  `0xaece` and selects `0x8a48` instead of `0x8656` in the page-pool cursor
  service path.
- `0x780e98`: cached status code used by `0x8a48` media-feed formatting.

Canonical backchannel response:

- `0x12280..0x12288`: zero-terminated literal `33440A\r\n`.
- `0x12034`: command-table wrapper reached from `ESC *r#K` and `ESC *s#^`. It
  calls setup helper `0x11efe`, which appends a synthetic secondary/setup
  six-byte record with word `+2 = 1`, then enters `0x122be`.
- `0x122be..0x12326`: producer that rewinds `0x78299e` to the synthetic record,
  fetches the following byte through `0xda9a`, and either enqueues the literal
  through `0xb090` or reports the byte through `0x9ec0`.

Firmware bookkeeping:

- `0x7801e2`: wait object used when the output worker or FIFO producer must
  yield.
- `0x7839d2`: ready/cleanup trigger tested by `0x2c08`. When set, cleanup
  clears it and runs the `0x2c44` subpath before clearing service-pending
  state.
- `0x7839d3`: service-pending byte set by `0x2a38` and cleared by copied-stub
  status handling and cleanup.
- `0x780e3e` and `0x7822e6`: normal service-message latch and next poll
  deadline maintained by `0x8656`.
- `0x780e8a`: normal service-message selector for the `0x8656` table.
- `0x7821f9`: engine/attendance status byte consumed by `0x7cf8` for
  `11 PAPER OUT`, `12 PRINTER OPEN`, `13 PAPER JAM`, `14 NO EP CART`, and
  `15 ENGINE TEST` selection.
- `0x7821b8` / `0x7821b9`: self-test/font-print selectors consumed by
  `0x8656`.
- `0x78292c..0x78293c`: desired 16-character operator-panel message buffer
  maintained by `0x9182`, `0x955a`, and `0x95ae`.
- `0x78293d..0x78294d`: displayed/shadow message buffer cleared by
  `0x9584`, populated by `0x92f8`, and compared against the desired buffer
  by `0x95fa`.
- `0x78296c`: current display/message mode flag. Wrapper `0x8c7a` supplies
  flag `0`; wrapper `0x8c90` supplies flag `1`.
- `0x78296d` / `0x78296e`: display character counter and pending wrapper flag.

Parser scratch:

- Model-ID response parsing uses parser scratch. Wrapper `0x12034` appends a
  synthetic six-byte setup record through `0x11efe`, producer
  `0x122be..0x12326` rewinds active record cursor `0x78299e`, and the
  following query byte is fetched through parser byte wrapper `0xda9a`.
  The handler emits literal `33440A\r\n` only when the active record word `+2`
  is `1` or `-1` and the fetched query byte is `0x11`.
- The synthetic record and query byte are consumed immediately by
  `0x122be..0x12326`; they do not become page/image state.
- The other status and page-environment paths here do not consume PCL parser
  records directly; their state is host-interface, pool, panel, and service
  bookkeeping.

Unknown:

- physical signal names for `0xfffe0001` / `0xfffe0003`, `0xfffee005` /
  `0xfffee003`, `$8a01`, and `$a801`;
- the physical DC-controller sensor bits that write `0x7821f9`;
- user-facing names for selected record byte `+6`, `0x780e98`, and the folded
  aggregate status categories beyond the strings already listed below;
- the physical panel effect of the flag-`1` display table built by `0x9406`.

### Writers

- `0xb0c0` enqueues one FIFO byte, wraps `0x783ed8`, and increments
  `0x783ed2`.
- `0xb022` dequeues one FIFO byte, wraps `0x783ed4`, and decrements
  `0x783ed2`.
- `0xb090` retries `0xb0c0` and waits through `0x10c8(0x7801e2)` when the
  FIFO is full.
- `0xaece` clears `0x783e61` after service byte `0x13`, decrements
  `0x780e22` after a status byte is accepted, and records accepted byte
  `0x780e62`.
- `0x122be..0x12326` writes response bytes by walking the literal at
  `0x12280` and calling `0xb090` for each byte when the parser/query gate
  passes.
- `0x36e4` derives aggregate fields `0x780e12`, `0x780e0e`, `0x780e0a`,
  and `0x780e68`.
- `0x2888` clears or sets `0x780e90`, writes `0x780e98`, and ORs
  `0x10` into `0x780e2a` for an eligible page-environment status.
- `0x2a14` publishes selected record byte `+7` to `0x780e8f`.
- `0x2c08..0x2c3a` clears service flags including `0x7839d3` and
  `0x780e90`.
- `0x2c44..0x2c7e` runs only from cleanup when `0x7839d2` was set. It toggles
  `$a801` shadow helpers `0xa668`, `0xa620`, and `0xa638`, waits through
  `0x2332`, then calls candidate-slot insertion helper `0x1fd4` with a null
  longword argument.
- `0x8656` updates `0x780e3e` / `0x7822e6` and emits normal service strings.
- `0x8a48` emits media-feed strings from `0x780e8e`, `0x780e98`, and table
  `0xb490`.
- `0x9112` formats two-part display messages in `0x78292c`: it clears the
  desired buffer, copies a base string at a one-based caller offset, copies a
  suffix string at a second one-based caller offset, then calls
  `0x9182(0x78292c, flag)`.
- `0x9182` installs operator-panel messages. It copies source text to
  `0x78292c`, compares text plus wrapper flag against `0x78293d` /
  `0x78296c`, returns unchanged messages without hardware writes, and on
  change refreshes the shadow buffer and stores the new flag in `0x78296c`.
- `0x9406` is the flag-`1` path selected by `0x8c90`: it derives output masks
  from the first two shadow-message bytes, initializes words
  `0x78291c..0x78292a`, and points `0x782904` / `0x78290c` at those words.

### Operator-Panel Message Formatter

This checkpoint owns the ROM-local message-formatting edge between status
selection and the physical panel-output boundary. It does not assign physical
display wiring after `0x9406`; it documents the software state that decides
which text and wrapper flag are presented to that boundary.

Instruction route:

- `0x9112..0x9130` clears the desired message buffer through `0x955a`. If the
  caller's first one-based offset argument is zero, it substitutes current
  display counter byte `0x78296d`.
- `0x9132..0x9144` applies the same zero-substitution rule to the second
  one-based offset argument.
- `0x9144..0x9166` copies the first string into destination `A6+0x0c` and the
  second string into destination `A6+0x14` by calling `0x95ae(offset - 1,
  destination)`. Callers use this to assemble two-part strings such as
  paper-feed messages from fixed ROM strings and variable suffix positions.
- `0x9168..0x9178` calls `0x9182(0x78292c, flag)` with the caller's wrapper
  flag from `A6+0x18`. The formatted buffer is therefore fed into the same
  installer as direct display-message wrappers `0x8c7a` and `0x8c90`.
- `0x9182..0x91a4` first checks whether the source pointer is already
  `0x78292c`. External source strings are copied into the desired buffer by
  clearing through `0x955a` and copying through `0x95ae(0, source)`.
- `0x91a6..0x91b2` compares the requested wrapper flag and desired text against
  the displayed shadow through `0x95fa`. If there is no change, `0x9182`
  returns without rewriting the panel shadow or calling the physical-output
  helper.
- `0x91b4..0x91e8` is the changed-message path. It resets output state through
  `0x952a`, writes mask `0xfffffeef` through `0x949c`, delays through
  `0x8bea(5)`, clears the displayed shadow through `0x9584`, sets
  `0x78296d = 1`, copies desired text to the shadow through `0x92f8`, and
  stores requested flag byte in pending flag `0x78296e`.
- `0x91f0..0x9206` calls physical-output helper `0x9406` only when the
  requested flag is nonzero, then commits current flag byte `0x78296c`.

State classification:

- Canonical display state:
  desired message buffer `0x78292c..0x78293c`, displayed shadow buffer
  `0x78293d..0x78294d`, current wrapper flag `0x78296c`, display counter
  `0x78296d`, and pending wrapper flag `0x78296e`.
- Derived/cache state:
  one-based string offsets supplied to `0x9112`, zero-offset substitution from
  `0x78296d`, and comparison result from `0x95fa`.
- Firmware bookkeeping:
  clear/copy helpers `0x955a`, `0x95ae`, `0x9584`, `0x92f8`, output reset
  `0x952a`, mask writer `0x949c`, and delay helper `0x8bea`.
- Hardware/external state:
  physical panel signaling after `0x9406`. The ROM-visible precondition for
  that handoff is fully named here: changed text plus nonzero wrapper flag.
- Parser scratch:
  none. These routines are status/display side effects, not command-token
  parser state.
- Output effect:
  no page object or pixels. A changed software message updates the displayed
  shadow and, for wrapper flag `1`, enters `0x9406`; an unchanged message is a
  no-output status/display event.
- Evidence:
  `generated/disasm/ic30_ic13_formatted_message_helper_009112.lst`,
  `generated/disasm/ic30_ic13_display_message_core_009182.lst`, string
  evidence in `generated/analysis/ic30_ic13_strings.txt`, and caller routing
  in `generated/disasm/ic30_ic13_page_environment_message_008a48.lst` and
  `generated/disasm/ic30_ic13_message_dispatch_wrappers_008c7a.lst`.

### Readers And Consumers

- `0xae2c` is the output worker. It sleeps only when FIFO count
  `0x783ed2`, pending status count `0x780e22`, and bridge-service byte
  `0x783e61` are all zero.
- `0x12034` is the observed parser-table entry that reaches the model-ID
  response producer from `ESC *r#K` and `ESC *s#^`.
- `0x122be..0x12326` consumes a parser byte through `0xda9a` and the active
  record word `+2`. The accepted `0x11` query with word `1` or `-1` emits
  `33440A\r\n`; other bytes are pushed back/reported through `0x9ec0`.
- `0xaece` builds outbound status bytes from base `0x30`: `0x780e12` or
  `0x780e90` sets bit `0`, `0x780e2a` sets bit `1`, `0x780e0a` sets bit
  `2`, and `0x783e60` is ORed into the byte.
- `0x7612..0x7834` consumes `0x780e90` to choose page-environment message
  helper `0x8a48` when set or normal service helper `0x8656` when clear.
- `0x2c08` consumes `0x7839d2` as a cleanup trigger. If the byte is clear, the
  path skips `0x2c44` and still clears `0x7839d3`, calls `0xa5da`, clears
  `0x780e90`, and exits through `0x15ac`.
- `0x2c44` consumes the active-pool candidate insertion contract indirectly:
  it calls `0x1fd4` with a zero longword argument, so any downstream effect is
  limited to the scheduler candidate-slot bookkeeping documented in
  [active-render-scheduler.md](active-render-scheduler.md#scheduler-outcome-matrix),
  not page-object creation.
- `0x8a48` maps `0x780e8e = 0x80` to `PF FEED` / `PE FEED` forms and
  `0x780e8e = 0x90` to envelope/manual-feed forms.
- `0x8a48` indexes suffix table `0xb490` with `0x780e98` or
  `0x780e98 & 0x7f`; the observed suffix strings are `LETTER`, `A4`,
  `B5`, `MINI`, `LEGAL`, `EXEC`, `COM-10`, `MONARCH`, `DL`, and `C5`.
- `0x7c96..0x7cc8` dispatches aggregate status byte `0x780e35`: bit `1`
  calls attendance selector `0x7cf8`, bit `2` calls paper-list helper
  `0x7ea0`, and bit `3` calls the adjacent status helper at `0x7f98`.
- `0x7ccc..0x7cf6` is a direct printer-open/status clear helper: it displays
  string `0xb1d6` (`12 PRINTER OPEN`) through wrapper `0x8c90`, calls
  `0x6798`, then clears bit `3` of aggregate status longword `0x780e32`
  through `0x9c0c(0x780e32, 8)`.
- `0x7cf8..0x7e20` maps attendance byte `0x7821f9` to operator-panel strings.
  Bit `2` selects `0xb1d6` (`12 PRINTER OPEN`), bit `3` selects `0xb1e7`
  (`13 PAPER JAM`), bit `6` selects `0xb1f8` (`14 NO EP CART`), bit `4`
  selects `0xb1c5` (`11 PAPER OUT`), and bit `1` selects `0xb209`
  (`15 ENGINE TEST`). If none of those bits is set, the routine keeps default
  string `0xb3c3` (`55 ERROR`).
- The `11 PAPER OUT` branch at `0x7d9a..0x7dca` also clears `0x780e96`,
  copies it to `0x780e97`, and, when `0x780e6a` is set, clears active-status
  byte `0x780e68` inside the `0x15a6` / `0x15ac` critical section.
- Display wrapper choice inside `0x7cf8` depends on the selected string.
  `15 ENGINE TEST` uses wrapper `0x8c7a`; other selected attendance strings
  normally use `0x8c90`, with `UC` (`0xb23c`) or `LC` (`0xb24d`) substituting
  for paper-out when `0x780e02` is set, selected string is `11 PAPER OUT`,
  and `0x6f32(0x2a)` returns bit `5` or bit `6` clear.
- `0x8656` selects normal status strings such as `16 TONER LOW`,
  `SERVICE MODE`, `04 SELF TEST`, `05 SELF TEST`, `06 PRINTING TEST`, and
  `06 FONT PRINTOUT`.
- `0x8c7a` and `0x8c90` select the `0x9182` wrapper flag. Flag `0` is the
  normal install path; flag `1` also arms the `0x9406` display-output table
  after the text has changed.

### Host Output FIFO Contract

The host-output FIFO is the ROM-visible boundary for parser commands that
return bytes to the host instead of producing page objects. It is separate
from the input byte source at `0xa904` and from the page/image path rooted at
`0x78297a`.

FIFO storage and pointers are canonical host-output state:

- `0x783e92..0x783ed1`: 64-byte circular storage.
- `0x783ed2`: count word.
- `0x783ed4`: read pointer.
- `0x783ed8`: write pointer.
- `0x7801e2`: wait object signaled when producers or the worker change FIFO
  availability.

Producer helper `0xb0c0` appends one byte:

- `0xb0c4..0xb0d8` enters the critical section and rejects the append when
  count `0x783ed2 >= 0x40`, returning `D7 = 0` with no pointer or count
  change.
- `0xb0da..0xb102` stores the byte argument at write pointer `0x783ed8`,
  increments the pointer, and wraps it to `0x783e92` after `0x783ed1`.
- `0xb110..0xb126` increments count `0x783ed2`, leaves the critical section,
  and returns `D7 = 1`.

Retry wrapper `0xb090` is the blocking enqueue used by the model-ID response
producer. It calls `0xb0c0`; on a full FIFO it signals or waits on
`0x7801e2` through `0x10c8(0x7801e2)` and retries the same byte. After a
successful append it also signals `0x7801e2` before returning. The byte stream
therefore preserves order: no later response byte is enqueued until the
current byte has entered the FIFO.

Consumer helper `0xb022` removes one byte:

- `0xb028..0xb034` enters the critical section and tests count
  `0x783ed2`.
- Empty FIFO path `0xb062..0xb070` clears the caller's destination byte,
  returns `D7 = 0`, and leaves count/pointers unchanged.
- Nonempty path `0xb036..0xb060` copies byte `[0x783ed4]` to the caller
  destination, increments the read pointer, and wraps it to `0x783e92` after
  `0x783ed1`.
- `0xb072..0xb088` decrements count `0x783ed2`, leaves the critical section,
  and returns `D7 = 1`.

Output effect: parser-visible response commands such as
`0x12034 -> 0x122be` enqueue the literal `33440A\r\n` through `0xb090`.
The output worker `0xae2c` / `0xaece` later consumes either FIFO bytes,
status bytes, or bridge-service byte `0x13` according to its own priority.
None of these FIFO operations create page roots, queue page objects, publish
records, or invoke `0x1ed84` / `0x1ef6a`.

Evidence:
`generated/disasm/ic30_ic13_host_output_fifo_00b022.lst`;
`generated/disasm/ic30_ic13_host_output_worker_00ae2c.lst`;
`generated/disasm/ic30_ic13_payload_dispatch_011f82.lst` for
`0x12034..0x12326`; and
`generated/analysis/ic30_ic13_pcl_command_map.md` for the parser-table route
into `0x12034`.

### Host Output Worker Contract

Worker `0xae2c` is the wait-object consumer that drains host-visible output
state. It consumes the FIFO above, the pending status count, and the
bridge-service byte. It does not consume page roots or render records.

Worker sleep/wake gate:

- `0xae30..0xae5c` enters a critical section, ORs FIFO count `0x783ed2`,
  pending status count `0x780e22`, and bridge-service byte `0x783e61`, and
  waits through `0x10d0(0x15)` only when all three are zero.
- Any nonzero source leaves the critical section and selects an output backend
  from `0x780e40`.

Backend selector behavior:

- `0x780e40 == 0`: `0xae6a..0xae8e` first calls status/service helper
  `0xaece`, then dequeues FIFO bytes through `0xb022`. Each dequeued byte is
  sent through retry helper `0xaf7c`, which repeatedly calls backend writer
  `0xa1b0` until accepted or until retry count `0x4e20` triggers error report
  `0x1284(0xe2, 4)`.
- `0x780e40 == 1`: `0xae9e..0xaeaa` only dequeues FIFO bytes through
  `0xb022` and loops back to the worker gate. The bytes are discarded by the
  ROM-visible worker path; status helper `0xaece` is not called in this mode.
- Other nonzero `0x780e40` values: `0xaeac..0xaecc` dequeues FIFO bytes
  through `0xb022` and sends accepted bytes through retry helper `0xafcc`.
  `0xafcc` calls backend writer `0xa1d6`, waits through `0x10d0(0x0b)` when
  engine/status counter `0x780e04` advances too far, and retries until the
  backend accepts the byte.

Status/service helper `0xaece` owns the mode-0 status priority before FIFO
bytes:

- `0xaedc..0xaf02`: if `0x783e61` is nonzero, try to send literal service byte
  `0x13` through `0xa1b0`. On success, write `0x780e62 = 0x13` and clear
  `0x783e61`.
- `0xaf08..0xaf26`: if pending status count `0x780e22` is zero, return with
  no status byte.
- `0xaf16..0xaf62`: build status byte from base `0x30`. Set bit `0` when
  `0x780e12` or `0x780e90` is nonzero, bit `1` when `0x780e2a` is nonzero,
  bit `2` when `0x780e0a` is nonzero, then OR reason byte `0x783e60`.
- `0xaf62..0xaf7a`: only after `0xa1b0` accepts that byte does the helper
  clear `0x783e60` and decrement `0x780e22`.

Output effect: model-ID response bytes, status bytes, and bridge-service byte
`0x13` are host-visible protocol output. They do not call `0x10084`,
`0xff1e`, `0x1ed84`, or `0x1ef6a`. They affect pixel reproduction only
indirectly, when a bidirectional host reacts to the output or when a blocking
FIFO/status backend stalls the parser-side producer.

Evidence:
`generated/disasm/ic30_ic13_host_output_worker_00ae2c.lst`;
`generated/disasm/ic30_ic13_host_output_retry_00af7c.lst`;
`generated/disasm/ic30_ic13_interface_output_mmio_00a1b0.lst`;
fixtures `0xaece emits service byte and combined status byte` and
`0xae2c drains FIFO by configured output mode`.

### Model-ID Command Stream

The concrete parser-visible response stream is:

```text
ESC *r1K 0x11
```

The `ESC *s#^` command-table sibling reaches the same wrapper and response
producer.

Byte-stream route:

- Host bytes enter through `0xa904`, parser wrapper `0xda9a`, and parser loop
  `0x11774`.
- `ESC *r#K` reaches mode `7`; `ESC *s#^` reaches mode `6`.
- Both command forms dispatch wrapper `0x12034`.
- `0x12034` calls `0x11efe`, which appends a synthetic six-byte setup record
  with word `+2 = 1`, then enters producer `0x122be`.
- `0x122be..0x12326` rewinds parser record cursor `0x78299e`, fetches the
  following query byte through `0xda9a`, and tests the active record word
  `+2`.
- Query byte `0x11` with active word `1` or `-1` emits the literal at
  `0x12280..0x12288` (`33440A\r\n`) through FIFO helper `0xb090`.
- Other query bytes are reported through `0x9ec0` and do not enter the
  host-output FIFO.

State and output effect:

- Canonical parser/response state is the synthetic record, the active record
  word `+2`, the query byte, and ROM literal `0x12280..0x12288`.
- Canonical host-output state is FIFO count/pointers/storage
  `0x783ed2`, `0x783ed4`, `0x783ed8`, and `0x783e92..0x783ed1`.
- Firmware bookkeeping is the blocking enqueue wait on `0x7801e2` when
  `0xb090` sees a full FIFO.
- This command creates no page root, no page object, no publication record,
  and no render work. It can affect later pixels only if a bidirectional host
  consumes the response bytes and sends different future input, or if FIFO
  fullness stalls the parser-side producer.
- The ROM-local parser-to-FIFO edge is resolved for this path. Remaining
  uncertainty is the hardware/MMIO identity of the selected output backend
  registers named by `0x780e40`.

### Output Effect

These paths do not create page-record objects and do not feed `0x1ed84` or
`0x1ef6a`. They can still affect exact reproduction in two indirect ways:

- a full host-output FIFO can stall a parser-side response producer through
  `0xb090`;
- a bidirectional host may react to service/status bytes, changing the future
  byte stream that reaches `0xa904`.
- a bidirectional host may also react to the literal `33440A\r\n` model-ID
  response; a closed byte-stream renderer can ignore that response unless its
  host script depends on backchannel bytes.

For a closed byte-stream renderer that ignores backchannel responses, these
status/backchannel paths are protocol and service-scheduling state, not
bitmap-composition state.

### Reproduction Contract

A byte-stream renderer or protocol emulator must preserve these status-side
contracts when host backchannel behavior is modeled:

- `ESC *r#K` and `ESC *s#^` both dispatch wrapper `0x12034`; `0x12034` calls
  `0x11efe`, appends the synthetic six-byte record with word `+2 = 1`, and
  then enters `0x122be..0x12326`.
- `0x122be..0x12326` consumes the next parser byte through `0xda9a`. Only
  query byte `0x11` with active record word `1` or `-1` enqueues the ROM
  literal `33440A\r\n` from `0x12280..0x12288`; other query bytes are reported
  through `0x9ec0`.
- Response bytes enter the 64-byte host-output FIFO through blocking helper
  `0xb090`, so a full FIFO can stall the parser-side producer before later
  host bytes are admitted.
- Output worker `0xae2c` drains FIFO bytes or status/service bytes according
  to backend selector `0x780e40`; this is host-visible protocol output, not a
  page-root or render-record producer.
- Status worker `0xaece` builds outbound status bytes from base `0x30` using
  `0x780e12`, `0x780e90`, `0x780e2a`, `0x780e0a`, and reason byte
  `0x783e60`.
- Page-environment status helper `0x2888` writes `0x780e90`, `0x780e98`, and
  `0x780e2a.4`; those fields can affect `0xaece` status bytes and
  `0x7612..0x7834` panel/service selection, but they do not create page
  objects.
- None of these paths call `0x10084`, `0xff1e`, `0x1ed84`, `0x1edc6`, or
  `0x1ef6a`. Pixel output changes only if a bidirectional host reacts to the
  response/status bytes by sending a different later byte stream, or if status
  service prevents later bytes from reaching `0xa904`.

### Aggregate Status Helper `0x36e4`

The aggregate helper is the ROM-local join point for service/status longwords
before host-output status bytes or external-ready teardown consumers see them.
It is not a parser handler and it does not create page records, but its return
value and side effects feed the host/status side channel documented above.

Writers and formulas:

- `0x36ec..0x36fe` writes aggregate error/service longword
  `0x780e12 = 0x780e32 | 0x780e2e | 0x780e36`.
- `0x3704..0x3710` writes aggregate warning/service longword
  `0x780e0e = 0x780e12 | 0x780e2a`.
- `0x3716` calls helper `0x15a6` before active-status folding.
- `0x371c..0x372a` writes active-status longword
  `0x780e0a = byte(0x780e68) | 0x780e12`.
- `0x3730..0x3742` mirrors active status back into byte `0x780e68`: nonzero
  `0x780e0a` writes `0xff`, and zero `0x780e0a` writes `0`.
- `0x3748` calls helper `0x15ac`, then `0x374e..0x3752` copies
  `0x780e0a` into `0x780e1a`.

Forced-status branch:

- `0x3758..0x37a8` takes the special branch only when all predicates pass:
  `0x7821a8 != 0`, `0xbb84()` returns nonzero, `0x72d4()` returns nonzero,
  `0x72a2()` returns nonzero, `0x780e36 == 0`, `(0x780e32 & 0x0f) == 0`,
  `(0x780e2a & 0x09) == 0`, `0x782272 == 0`, and `0x7822dc == 0`.
- When those predicates pass, `0x37aa..0x37ca` forces
  `0x780e0a = 1`, `0x780e0e = 1`, clears `0x780e12`, writes
  `0x780e1a = 1`, and returns `D7 = 0x10`.
- This branch is status-side behavior. It does not imply a page-object or
  render effect. It can only affect byte-stream reproduction indirectly through
  host/status protocol or service scheduling.

Normal return encoding:

- If the forced branch is not taken, `0x37cc..0x37f2` builds the return value
  in `D7` from three aggregate fields:
  bit `7` is set when `0x780e0a == 0`, bit `0` is set when `0x780e0e != 0`,
  and bit `1` is set when `0x780e12 != 0`.
- The same fields feed outbound status byte construction in `0xaece`:
  `0x780e12` or `0x780e90` sets host-status bit `0`, `0x780e2a` sets bit `1`,
  `0x780e0a` sets bit `2`, and `0x783e60` is ORed into the base `0x30` byte.

Field classes:

- Canonical status inputs:
  `0x780e32`, `0x780e2e`, `0x780e36`, `0x780e2a`, `0x780e68`,
  `0x7821a8`, panel/menu progress `0x782272`, and menu latch `0x7822dc`.
- Derived/cache status:
  `0x780e12`, `0x780e0e`, `0x780e0a`, and `0x780e1a`.
- Firmware bookkeeping:
  helper predicates `0xbb84`, `0x72d4`, and `0x72a2`, plus helper calls
  `0x15a6` and `0x15ac`.
- Hardware/external:
  the physical sources behind helper predicates are not named by this listing.
  `0xbb84` is documented in
  [external-ready-service.md](external-ready-service.md#owner-summary) as consuming
  `$fffee00b.7`.
- Unknown:
  user-facing names for the folded status categories remain unresolved; the
  arithmetic, return-bit encoding, and no-page-output boundary are ROM-local.

### Confidence And Evidence

Confidence is high for FIFO capacity/order, output mode selection, outbound
status-byte composition, `0x780e90` production, media-feed message selection,
and normal service-message routing because these are direct disassembly reads
and executable fixtures. Confidence is high for model-ID literal emission from
the disassembly path `0x12034 -> 0x122be..0x12326`, string-table hit at
`0x12280`, and fixture
`0x12034/0x122be model-ID response emits FIFO literal`.

Fixture evidence:

- `0xb0c0/0xb022 output FIFO wraps and preserves order`
- `0xb090 waits on full FIFO then enqueues after drain`
- `0xaece emits service byte and combined status byte`
- `0xae2c drains FIFO by configured output mode`
- `0x12034/0x122be model-ID response emits FIFO literal`
- `0x2888 sets page-environment status consumed by 0xaece`
- `0x2888 publishes environment mismatch or status-cache changes`
- `0x7612 selects page-environment or normal service helper`
- `0x8a48 maps page environment bytes to media-feed messages`

Disassembly evidence:

- `generated/disasm/ic30_ic13_error_report_entry_001284.lst`
- `generated/disasm/ic30_ic13_error_report_00128c.lst`
- `generated/disasm/ic30_ic13_host_output_worker_00ae2c.lst`
- `generated/disasm/ic30_ic13_interface_output_mmio_00a1b0.lst`
- `generated/disasm/ic30_ic13_interface_status_aggregate_0036e4.lst`
- `generated/disasm/ic30_ic13_host_output_fifo_00b022.lst`
- `generated/disasm/ic30_ic13_payload_dispatch_011f82.lst`
- `generated/analysis/ic30_ic13_strings.txt`
- `generated/disasm/ic30_ic13_page_environment_status_002888.lst`
- `generated/disasm/ic30_ic13_page_status_cleanup_002c00.lst`
- `generated/disasm/ic30_ic13_page_pool_candidate_insert_001c04.lst`
- `generated/disasm/ic30_ic13_page_pool_cursor_007612.lst`
- `generated/disasm/ic30_ic13_page_service_messages_008656.lst`
- local `unidasm` window `0x7c96..0x7e20` over
  `generated/roms/ic30_ic13.bin` for attendance-message selection.
- `generated/disasm/ic30_ic13_page_environment_message_008a48.lst`
- `generated/disasm/ic30_ic13_message_dispatch_wrappers_008c7a.lst`
- `generated/disasm/ic30_ic13_formatted_message_helper_009112.lst`
- `generated/disasm/ic30_ic13_display_message_core_009182.lst`

Unresolved middle edges:

- No unresolved ROM object/rendering edge remains in these status paths.
- `0x12034 -> 0x122be..0x12326`: producer entry, parser/query gate, literal
  bytes, and output FIFO writes are pinned. The remaining work is only the
  external protocol name for the `0x11` query that emits `33440A\r\n` from
  `0x12280`.
- Other remaining work is user-facing names for folded status categories and
  selected record bytes, physical panel behavior after `0x9406`, physical
  naming/timing for the output MMIO banks, and the DC-controller/engine
  producer that converts actual paper, cover, cartridge, and engine-test
  signals into `0x7821f9` bits.

## Attendance / User Action

| Message | Meaning / action |
| --- | --- |
| `11 PAPER OUT` | Add paper; HP 33440 service-table wording. |
| `12 PRINTER OPEN` | Close top cover. |
| `13 PAPER JAM` | Clear paper, then continue/reset to reprint as appropriate. |
| `14 NO EP CRT` | Install EP-S cartridge. |
| `16 TONER LOW` | Replace or redistribute EP-S cartridge. |
| `PC LOAD [paper]` | Requested paper size not installed or tray is empty. |
| `PE FEED [envelope]` | Manual envelope feed requested. |
| `PF FEED [paper]` | Manual paper feed requested. |
| `ENVELOPE=[size]` | HP 33440 envelope tray; select COM10, MONARC, C5, or DL. |
| `FC LEFT/RIGHT/BOTH` | Font cartridge changed offline with buffered data. |
| `FE CARTRIDGE` | Cartridge removed online; power off, reinsert, power on. |

For `PC LOAD [paper]`, `[paper]` can be A4, EXEC, LETTER, or LEGAL.

## Data / Page Errors

- `20 ERROR`: Memory overflow: too much font, macro, raster, or
  page-composition data. Continue prints what was received. Simplify job
  or add memory.
- `21 ERROR`: Page too complex for formatter/engine timing. Reduce
  complexity. HP 33449 can also use page protection with extra memory.
- `22 ERROR`: Host/printer communication protocol problem. Check baud,
  handshake, and I/O settings. XON/XOFF and DTR are supported; ENQ/ACK
  is not.
- `40 ERROR`: Data transfer error. Common causes include powering host
  down while printer online or mismatched baud rates.
- `41 ERROR`: Temporary page error. Often beam detect related; printer
  attempts recovery and page repeat. If beam detect cannot recover for
  about two seconds, expect `51 ERROR`.

## Optional I/O and Cartridge Errors

| Message | Meaning |
| --- | --- |
| `42 ERROR` | Optional I/O problem; press continue, reseat optional I/O PCA. |
| `43 ERROR` | Optional interface communication problem. |
| `69 SERVICE` | Timeout between Interface/Formatter PCA and optional I/O PCA. |
| `70 ERROR` | HP 33449 firmware cartridge not designed for printer. |
| `71 ERROR` | HP 33449 firmware cartridge not designed for printer. |
| `72 SERVICE` | HP 33449 font cartridge removed too quickly after insertion. |
| `79 SERVICE` | HP 33449 formatter error; isolate memory, cartridges, I/O. |

`72 SERVICE` can also indicate a bad font-cartridge connector.

## Engine Service Errors

| Message | Meaning |
| --- | --- |
| `50 SERVICE` | Fuser fault. Power off 10+ minutes, then troubleshoot fuser. |
| `51 ERROR` | Laser lost for about two seconds / beam detect malfunction. |
| `52 ERROR` | Scanner motor unable to maintain speed. |

## Memory / Formatter Service Errors

- `53 ERROR`: HP 33440 optional memory incompatible with Interface PCA;
  use HP memory.
- `31 SERVICE`: Program ROM checksum error on Interface/Formatter PCA.
- `32 SERVICE`: Internal font ROM checksum error on Interface/Formatter
  PCA.
- `33 SERVICE`: Dynamic RAM or optional memory PCA error. Remove
  optional memory and retest.
- `54 SERVICE`: Laser scan buffer error.
- `55 SERVICE`: Dynamic RAM controller error.
- `57 SERVICE`: Miscellaneous Interface/Formatter PCA hardware or
  address error. Check cables, font cartridges, accessories; then
  replace PCA if persistent.
- `68 ERROR`: HP 33449 recoverable NVRAM error; settings may reset.
- `68 SERVICE`: NVRAM failure. On HP 33440/33449, operation may continue
  with factory defaults until Interface/Formatter PCA replacement.

ROM retained-storage distinction:

- `67 SERVICE` is the startup active-record failure path. Bulk loader
  `0x5a16` marks all retained-record flags dirty, calls read helper `0x97e4`,
  and clears the flags; later active-bank selector `0x56c2` calls
  `0x1284(0xe2, 0x21)` if no scanned record word has bit `15` set. String
  `0xb44b` is `67 SERVICE`.
- `68 SERVICE` is the retained commit/readback failure status path.
  Maintenance helper `0x571e` calls `0x9bee(0x780e36, 0x00000008)` after
  exhausted `0x96c4` commit retries, setting `0x780e39.3`. External-service
  dispatcher `0xc1c6` consumes that bit and calls non-returning display helper
  `0x85c0`, which displays string `0xb45c` (`68 SERVICE`) through `0x8c90`.
- Neither path allocates page objects or reaches render entry `0x1ef6a`; they
  can only affect pixel reproduction by stopping/deferring parsing or changing
  host/service status behavior before later input is admitted.

## Formatter/DC Controller Communication

- `55 ERROR`: Communication problem between DC Controller PCA and
  Interface/Formatter PCA. Undefined status exchanged or status request
  unanswered. Service procedure says run Engine Test to verify DC
  Controller path, check J209 jumper and voltages, then replace
  Interface/Formatter PCA or DC Controller PCA.

Note: There is both `55 ERROR` and `55 SERVICE`; keep them distinct.
`55 ERROR` is formatter/DC communication. `55 SERVICE` is dynamic RAM
controller.

## Self-Test Failure Mapping

Self-test covers:

- Program ROM -> `31 SERVICE`.
- Internal font ROM -> `32 SERVICE`.
- DRAM/optional memory -> `33 SERVICE`.
- Scan buffers -> `54 SERVICE`.
- DRAM controller -> `55 SERVICE`.
- NVRAM -> `68 SERVICE` or model-specific `68 ERROR`.

## Sensor-Related Message Sources

- Paper out / load: ROM branch `0x7cf8` tests `0x7821f9.4` and selects
  string `0xb1c5` (`11 PAPER OUT`). Service hardware names this source as
  cassette sensor `PS301` plus tray-size switches `SW201`-`SW203`.
- Manual feed: page-environment helper `0x8a48` formats `PF FEED`,
  `PE FEED`, or `PE FEED ENVELOPE` from `0x780e8e` / `0x780e98`; service
  hardware names the physical sensor as `PS302`.
- Paper jam: ROM branch `0x7cf8` tests `0x7821f9.3` and selects string
  `0xb1e7` (`13 PAPER JAM`). Service hardware names this as delivery sensor
  `PS331`.
- Printer open: ROM branch `0x7cf8` tests `0x7821f9.2` and selects string
  `0xb1d6` (`12 PRINTER OPEN`). Helper `0x7ccc` also displays the same string
  and clears `0x780e32.3`; the physical source remains the cover / +24B
  interlock path.
- No EP cartridge: ROM branch `0x7cf8` tests `0x7821f9.6` and selects string
  `0xb1f8` (`14 NO EP CART`). Service hardware names this as cartridge
  sensitivity switches `CSENS1`/`CSENS2` both high.
- Toner low: toner sensor `TSENS`.
- Beam/scanner errors: `BD`, scanner tach `FG+`/`FG-`, scanner speed
  control `SCNCONT`, laser feedback `PD`.

## Emulator Takeaways

- Implement error codes as named engine/formatter states, not only
  display strings.
- `Auto Continue` affects whether recoverable errors wait indefinitely
  or display for about 10 seconds then resume.
- Many service codes map directly to hardware blocks; use them as
  milestones when reverse-engineering startup self-test branches.
- Keep HP 33449-only messages available as compatibility references but
  avoid exposing them in HP 33440 mode unless ROM behavior proves
  otherwise.
