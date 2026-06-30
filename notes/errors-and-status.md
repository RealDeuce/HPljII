# Errors and Status Messages

Sources: `hplaserjetclassicsiiiii.pdf` ch. 7 table 7-2; `33440-90905...pdf` ch.
13.

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

The ROM has two fixture-backed status paths that matter to byte-stream
reproduction even though they do not draw pixels themselves:

- host/interface backchannel status through `0xae2c` / `0xaece`;
- page-environment service status through `0x2888`, `0x7612`, `0x8a48`, and
  `0x8656`.

The low-level ledger remains in `notes/semantic-state-model.md` under
`Interface Output FIFO And Status Bytes` and
`Page Environment Status And Pool Cursor Gate`.
The external-ready/service loop and retained-storage `68 SERVICE` path are
documented in [external-ready-service.md](external-ready-service.md).

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

Firmware bookkeeping:

- `0x7801e2`: wait object used when the output worker or FIFO producer must
  yield.
- `0x7839d3`: service-pending byte set by `0x2a38` and cleared by copied-stub
  status handling and cleanup.
- `0x780e3e` and `0x7822e6`: normal service-message latch and next poll
  deadline maintained by `0x8656`.
- `0x780e8a`: normal service-message selector for the `0x8656` table.
- `0x7821b8` / `0x7821b9`: self-test/font-print selectors consumed by
  `0x8656`.

Parser scratch:

- none for these status paths. Parser-side producers can enqueue response
  bytes through `0xb090`, but the status fields above are host-interface,
  pool, and service bookkeeping rather than PCL parser state.

Unknown:

- physical signal names for `0xfffe0001` / `0xfffe0003`, `0xfffee005` /
  `0xfffee003`, `$8a01`, and `$a801`;
- user-facing names for selected record byte `+6`, `0x780e98`, and the folded
  aggregate status categories beyond the strings already listed below;
- the display-engine distinction between wrapper `0x8c7a` flag `0` and
  wrapper `0x8c90` flag `1`.

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
- `0x36e4` derives aggregate fields `0x780e12`, `0x780e0e`, `0x780e0a`,
  and `0x780e68`.
- `0x2888` clears or sets `0x780e90`, writes `0x780e98`, and ORs
  `0x10` into `0x780e2a` for an eligible page-environment status.
- `0x2a14` publishes selected record byte `+7` to `0x780e8f`.
- `0x2c08..0x2c3a` clears service flags including `0x7839d3` and
  `0x780e90`.
- `0x8656` updates `0x780e3e` / `0x7822e6` and emits normal service strings.
- `0x8a48` emits media-feed strings from `0x780e8e`, `0x780e98`, and table
  `0xb490`.

### Readers And Consumers

- `0xae2c` is the output worker. It sleeps only when FIFO count
  `0x783ed2`, pending status count `0x780e22`, and bridge-service byte
  `0x783e61` are all zero.
- `0xaece` builds outbound status bytes from base `0x30`: `0x780e12` or
  `0x780e90` sets bit `0`, `0x780e2a` sets bit `1`, `0x780e0a` sets bit
  `2`, and `0x783e60` is ORed into the byte.
- `0x7612..0x7834` consumes `0x780e90` to choose page-environment message
  helper `0x8a48` when set or normal service helper `0x8656` when clear.
- `0x8a48` maps `0x780e8e = 0x80` to `PF FEED` / `PE FEED` forms and
  `0x780e8e = 0x90` to envelope/manual-feed forms.
- `0x8656` selects normal status strings such as `16 TONER LOW`,
  `SERVICE MODE`, `04 SELF TEST`, `05 SELF TEST`, `06 PRINTING TEST`, and
  `06 FONT PRINTOUT`.

### Output Effect

These paths do not create page-record objects and do not feed `0x1ed84` or
`0x1ef6a`. They can still affect exact reproduction in two indirect ways:

- a full host-output FIFO can stall a parser-side response producer through
  `0xb090`;
- a bidirectional host may react to service/status bytes, changing the future
  byte stream that reaches `0xa904`.

For a closed byte-stream renderer that ignores backchannel responses, the
fixture-backed status paths are protocol and service-scheduling state, not
bitmap-composition state.

### Confidence And Evidence

Confidence is high for FIFO capacity/order, output mode selection, outbound
status-byte composition, `0x780e90` production, media-feed message selection,
and normal service-message routing because these are direct disassembly reads
and executable fixtures.

Fixture evidence:

- `0xb0c0/0xb022 output FIFO wraps and preserves order`
- `0xb090 waits on full FIFO then enqueues after drain`
- `0xaece emits service byte and combined status byte`
- `0xae2c drains FIFO by configured output mode`
- `0x2888 sets page-environment status consumed by 0xaece`
- `0x2888 publishes environment mismatch or status-cache changes`
- `0x7612 selects page-environment or normal service helper`
- `0x8a48 maps page environment bytes to media-feed messages`

Disassembly evidence:

- `generated/disasm/ic30_ic13_host_output_worker_00ae2c.lst`
- `generated/disasm/ic30_ic13_interface_output_mmio_00a1b0.lst`
- `generated/disasm/ic30_ic13_interface_status_aggregate_0036e4.lst`
- `generated/disasm/ic30_ic13_host_output_fifo_00b022.lst`
- `generated/disasm/ic30_ic13_page_environment_status_002888.lst`
- `generated/disasm/ic30_ic13_page_pool_cursor_007612.lst`
- `generated/disasm/ic30_ic13_page_service_messages_008656.lst`
- `generated/disasm/ic30_ic13_page_environment_message_008a48.lst`

Unresolved middle edges:

- No unresolved ROM object/rendering edge remains in these status paths.
- Remaining work is the external protocol name for the `0x11` query that
  emits `33440A\r\n` from `0x12280`, user-facing names for folded status
  categories and selected record bytes, `0x9182` / `0x9112` display-engine
  internals, and physical naming/timing for the output MMIO banks.

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

- Paper out / load: cassette sensor `PS301`, tray-size switches
  `SW201`-`SW203`.
- Manual feed: manual feed sensor `PS302`.
- Paper jam: delivery sensor `PS331`.
- Printer open: cover / +24B interlock path.
- No EP cartridge: cartridge sensitivity switches `CSENS1`/`CSENS2` both
  high.
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
