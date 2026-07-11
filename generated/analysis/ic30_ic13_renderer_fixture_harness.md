# IC30/IC13 Executable Renderer Fixture Harness

This report is emitted by `tools/render_fixture_harness.py` after executing
ROM-derived fixture models.

## Host Byte Fetch Fixtures

These fixtures model the normalized byte-source priority of routine `0xa904`
before the main parser or payload readers see `D7`. They are not electrical
interface emulation, but they pin the order and state side effects needed by a
byte-stream reproduction harness.

- `0x780e66 != 0` plus `0x780e3b != 0` returns `D7 = -1` before buffered or
  direct sources are consumed.
- A pending `0x7821cd` service flag runs helper `0x10cc(0x780202)` and retries
  before the first LIFO source is consumed.
- A current data-chain end marker runs helper `0xe22c` and retries, then the
  second LIFO source can provide the byte.
- In buffered mode `0x780e40 == 0`, the ring source wins before direct
  hardware fallback.
- Direct mode `1` returns the `0x8801` byte after `0x8e01.4` is ready,
  preserves `0x1a` while reporting it through `0x9ec0`, and clears the
  handshake/timeout state.
- Direct mode `2` returns the `0xfffee001` byte when `0xfffee005.0` is ready,
  sets `0x7828ec`, clears the timeout state, and sets bit 6 in the `0x7828fb`
  control shadow.
- A ring-fed `ESC &k1G!\r!` stream now carries the exact fetched bytes through
  the ROM parser trace, page-record root allocation, compact bucket queue,
  `0x1edc6` bridge, and final rendered rows.

| Fixture | Source | D7 | Events |
| --- | --- | ---: | --- |
| no-byte branch | `no-byte` | `-1` | `[]` |
| service + first LIFO | `first-lifo` | `66` | `[{'kind': 'service-retry', 'helper': 4300, 'argument': 7864834}, {'kind': 'first-lifo', 'remaining': 1}]` |
| data-chain transition + second LIFO | `second-lifo` | `85` | `[{'kind': 'data-chain-transition', 'helper': 57900}, {'kind': 'second-lifo', 'remaining': 0}]` |
| ring source | `ring` | `102` | `[{'kind': 'ring-byte', 'remaining': 1}]` |
| direct mode 1 | `direct-mode-1` | `26` | `[{'kind': 'control-1a-report', 'helper': 40640}, {'kind': 'mode1-handshake', 'status': 16, 'ack': 0, 'control_shadow': 52}]` |
| direct mode 2 | `direct-mode-2` | `126` | `[{'kind': 'mode2-handshake', 'status': 1, 'control_shadow': 96}]` |
- host-fetched mixed stream bytes: `1b 26 6b 31 47 21 0d 21`; queued object
  prefix `00 00 00 00 00 00 00 02 20 00 01 20 3b 00`

## PCL Tokenizer and Delayed Payload Fixtures

These fixtures model the six-byte parsed command records built by `0xdaf0` /
`0xdb74` and the delayed payload snapshot used by `0x121cc` before handlers
such as raster transfer `0x105d0` consume following data bytes.

- `300r150R` produces two records because the first numeric record has flag
  bit 7 set and the next byte is still in the parameter/intermediate range;
  the lowercase final stays in the same parser family until the uppercase
  final.
- Signed numeric parsing sets flag byte `0x81`, caps fractional storage to
  four digits, skips excess fractional digits, and stores signed word fields.
- A semicolon final is stored in the record but returns `D7 = 0`, matching the
  command-combining continuation path.
- `0x121cc` snapshots pending flag `1`, the saved handler longword, and the
  current six-byte parsed command record; `0x12218` restores that record at
  `0x78299e` and dispatches the saved handler when alternate/data mode is
  clear.
- In alternate/data mode, `0x12358` either calls wrapper `0x1228a`, which
  consumes the absolute parsed byte count through `0x12328` without echo, or
  consumes only positive counts itself while echoing each normalized byte
  through `0xe002`; both paths use `0xdace`, where payload control `1a 58`
  calls `0xd99a` and contributes byte `00`.
- `ESC &p#X` arms delayed handler `0x12452`; the transparent text fixture
  restores the saved parsed record, consumes the absolute byte count through
  `0xa904`, normalizes `1a 58` to `0x7f`, and routes printable bytes to
  `0xd04a` while filtered controls route to `0xd0f0`.

- chained resolution record bytes: `80 72 01 2c 00 00 80 52 00 96 00 00`
- signed/fraction record bytes: `81 57 ff f4 f2 80`, scratch `b'-12.3456'`
- semicolon continuation record bytes: `80 3b 00 01 00 00 80 58 00 02 00 00`,
  returned D7 `[0, 88]`
- delayed raster transfer snapshot: `01 00 01 05 d0 80 57 00 04 00 00`
- delayed transparent text snapshot: `01 00 01 24 52 80 58 00 05 00 00`,
  values `[65, 127, 5, 133, 66]`, routes `['0xd04a', '0xd04a', '0xd0f0',
  '0xd0f0', '0xd04a']`
- alternate wrapper consume values: `[170, 0, 187]`, echoed `[]`, control hits
  `1`
- alternate direct consume values: `[170, 0, 187]`, echoed `[170, 0, 187]`,
  negative-count values `[]`

## Page Geometry Command Fixtures

These fixtures model the ROM table lookups at
`0x9d16`/`0x9d4e`/`0x9d86`/`0x9dbe`, the `ESC &l#A` page-size handler at
`0xfc74`, the `ESC &l#P` page-length handler at `0xf9e8`, the `ESC &l#W`
vertical-forms-control payload handler at `0x12cfe`, the `ESC &l#V` VFC
channel-jump handler at `0x1280a`, and the `ESC &l#O` orientation handler at
`0x10220`.

- Page-code lookup masks the internal code with `0x7f`; PCL `80` stores
  internal code `0x88`, which reads table index `8`.
- `ESC &l#A` maps PCL values `1`, `2`, `3`, `26`, `80`, `81`, `90`, and `91`
  to internal page codes, finalizes pending page state, updates width/height
  words, then recomputes portrait or landscape extents.
- `ESC &l#P` converts current VMI times absolute line count into page extent
  `0x782dba`, selects an internal page code from orientation thresholds,
  recomputes default text bounds, and refreshes the following text cursor. Its
  zero-parameter branch publishes pending page state, reloads default page
  geometry through `0xf9ac`, and can emit the paper-source output/control
  bytes.
- `ESC &l#W` reaches delayed handler `0x12cfe`, consumes its payload through
  the `0xdace` data reader, loads the vertical-forms-control table at
  `0x782dde`, and recomputes text-bottom cache `0x782dd2` from channel-bit
  words.
- `ESC &l#V` reaches handler `0x1280a`, searches channel bits in the table at
  `0x782dde`, ensures a page root through `0x10084`, resets horizontal cursor
  through `0xf06e`, flushes pending text through `0xf34a`, and moves the
  vertical cursor before the next printable byte is queued.
- `ESC &l#O` accepts only values `0` and `1`; changing orientation finalizes
  pending page state, swaps active width/height in landscape, changes the
  vertical offset source from `60` to `50`, and reloads the orientation margin
  thresholds through `0x103ea`. A byte-stream fixture now drives chained `ESC
  &l1a1O` through handlers `0xfc74` and `0x10220`.

- Letter portrait from `ESC &l1A`: code `6`, width `3030`, height `2025`,
  margin `3150`, top offset `90`
- PCL 80 envelope lookup: code `0x88`, width `2130`, height `1012`, margin
  `2250`
- Letter landscape from `ESC &l1O`: active `2025x3030`, margin `2175`,
  printable extent `2125`, top offset `100`
- page-geometry stream events: `[{'sequence': b'\x1b&l1a', 'record':
  b'\x80a\x00\x01\x00\x00', 'parameter': 1, 'handler': 64628, 'before':
  {'page_code': 2, 'orientation': 0, 'width': 0, 'height': 0, 'active_width':
  0, 'active_height': 0, 'margin_reference': 0, 'vertical_offset_source': 0,
  'top_offset': 0, 'pending_text_flushes': 0, 'page_finalizations': 0},
  'after': {'page_code': 6, 'orientation': 0, 'width': 3030, 'height': 2025,
  'active_width': 3030, 'active_height': 2025, 'margin_reference': 3150,
  'vertical_offset_source': 60, 'top_offset': 90, 'pending_text_flushes': 1,
  'page_finalizations': 1}, 'chained': True}, {'sequence': b'1O', 'record':
  b'\x80O\x00\x01\x00\x00', 'parameter': 1, 'handler': 66080, 'before':
  {'page_code': 6, 'orientation': 0, 'width': 3030, 'height': 2025,
  'active_width': 3030, 'active_height': 2025, 'margin_reference': 3150,
  'vertical_offset_source': 60, 'top_offset': 90, 'pending_text_flushes': 1,
  'page_finalizations': 1}, 'after': {'page_code': 6, 'orientation': 1,
  'width': 3030, 'height': 2025, 'active_width': 2025, 'active_height': 3030,
  'margin_reference': 2175, 'vertical_offset_source': 50, 'top_offset': 100,
  'pending_text_flushes': 2, 'page_finalizations': 2}, 'chained': False}]`
- Landscape thresholds loaded by `0x103ea`: `[2175, 2550, 2480, 2550]`
- `ESC &l66P` at 6 LPI: code `2`, extent `3300`, top offset `90`, text bottom
  `3240`
- `ESC &l0P` zero-parameter branch: code `2`, extent `3300`, paper-source
  output `0x80`, control word `1`
- `ESC &l4W` payload `00 00 00 02`: text-bottom cache `0x00be0000`, VFC table
  prefix `00 00 00 02`
- Default `0x12b96` VFC table channels are now pinned by selector bit: channel
  1 is line 0, channel 2 marks the last two text lines, channel 3 spans all
  active text lines plus page last, and channels 4..16 follow the ROM
  divisor/boundary masks.
- A mixed printable/page-size page-record stream starts without a current page
  root, drives `!` then `ESC &l1A`, allocates the page-record root on the
  printable queue step, and publishes the queued compact text bucket through
  the page-size handler's `0xf34a`/`0xff1e` boundary before storing the new
  page code and recomputing geometry.
- page-size publication object bytes: `00 00 00 00 00 00 00 01 20 00 01 00 00
  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00`
- page-size published page-record bridge rows match the pre-geometry compact
  text rows.
- A mixed page-length stream `ESC &l66P!` routes through ROM parser handlers
  `0xf9e8` and `0xd04a`, refreshes the text cursor to y `126`, and queues the
  following printable at compact coord `0x9001`.
- A mixed VFC stream `ESC &l4W 00 00 00 02 !` routes through `0x11f6e`,
  restores delayed handler `0x12cfe`, consumes the four payload bytes before
  parsing `!`, and leaves the printable queued at compact coord `0x9001`.
- A mixed VFC lowercase stream `ESC &l4w4W 00 00 00 02 !` records lowercase
  snapshot `80 77 00 04 00 00`, ignores the uppercase reschedule while
  pending, restores the lowercase record, consumes payload after uppercase
  `W`, and queues `!` at compact coord `0x9001`.
- A mixed VFC channel stream `ESC &l2V!` routes through `0x1280a`, finds
  channel 2 at line 1, moves y from `126` to `176`, resets x from `40` to the
  left margin `10`, and queues `!` at compact coord `0xb001`.
- A mixed VFC before-top stream `ESC &l2V!` starts at y `89`, normalizes the
  channel search start line through `0x128ae..0x128f4`, finds channel 2 at
  line 1, and queues `!` at compact coord `0xb001`.
- A mixed VFC before-top target-after-text stream `ESC &l2V!` starts at y
  `89`, finds channel 2 at line 63, skips `0xf124` through `0x129fc..0x12afc`,
  recovers y to `104`, and queues `!` at compact coord `0x3001`.
- A mixed VFC start-after-text stream `ESC &l2V!` with an empty table starts
  at y `3290`, keeps start line 64 as the recovery target through
  `0x12a02..0x12afc`, skips wrap/publication, recovers y to `54`, and queues
  `!` at compact coord `0x1001`.
- A mixed VFC start-after-text stream `ESC &l2V!` with the default line-1
  channel bit starts at y `3290`, wraps through `0x12a7a..0x12af8`, skips
  publication, lands at y `176`, and queues `!` at compact coord `0xb001`.
- A mixed VFC start-after-text stream `ESC &l2V!` with only a line-63 channel
  bit starts at y `3290`, wraps through `0x12a7a..0x12afc`, skips publication,
  recovers y to `104`, and queues `!` at compact coord `0x3001`.
- A mixed VFC selector-zero stream `ESC &l0V!` routes through the `0x1280a`
  top-of-form target compare. When the computed target already equals y `126`,
  it keeps x/y unchanged, ensures the page root through `0x10084`, and queues
  `!` at compact coord `0x9e02`.
- A mixed VFC selector-zero start-after-text stream `ESC &l0V!` starts at y
  `3290`, routes through `0x1299c..0x12b92`, skips publication, returns to
  top-of-form y `126`, and queues `!` at compact coord `0x9001`.
- A mixed VFC selector-zero page-eject stream `!\x1b&l0V!` routes through
  `0x1299c..0x129c4`, publishes the old page at compact coord `0xbe02` through
  `0xf124`, resets x/y to `10`/`126`, and queues the next `!` on a fresh page
  at compact coord `0x9001`.
- A mixed VFC wrap-hit stream `!\x1b&l2V!` starts at y `226`, wraps the
  channel search through `0x129c6..0x12af8`, publishes the old page at compact
  coord `0xde02`, and queues the next `!` on a fresh page at compact coord
  `0xb001`.
- A mixed VFC wrap-no-hit stream `!\x1b&l2V!` with no channel 2 stops at
  `0x12a22..0x12a78`, publishes the old page at compact coord `0xde02`,
  returns to top-of-form y `126`, and queues the next `!` at compact coord
  `0x9001`.
- A mixed VFC target-after-text stream `!\x1b&l2V!` with channel 2 at line 63
  routes through `0x129ee..0x12b5a`, publishes the old page at compact coord
  `0x4e02`, recovers y to `104`, and queues the next `!` at compact coord
  `0x3001`.
- Direct high-start VFC branch fixtures start at line 80 and pin
  `0x12a02..0x12afc` no-hit recovery, `0x12a7a..0x12afc` wrapped line-70
  recovery, and selector-zero `0x12b5e..0x12b92` recovery.
- A mixed printable/orientation page-record stream starts from letter portrait
  with no current page root, drives `!` then `ESC &l1O`, allocates the
  page-record root on the printable queue step, and publishes the queued
  compact text bucket through the orientation handler's `0xf34a`/`0xff1e`
  boundary before switching to landscape geometry.
- orientation publication object bytes: `00 00 00 00 00 00 00 01 20 00 01 00
  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  00`
- orientation published page-record bridge rows match the pre-landscape
  compact text rows.

## Macro Command and Data-Chain Fixtures

These fixtures model the `ESC &f#Y` macro-id handler at `0xe112`, the `ESC
&f#X` macro-control dispatch at `0xdd08`, and the macro replay data-chain
frame built by `0xe418` for execute/call.

- `0xe112` stores the absolute parsed macro id word in `0x783164`.
- Selector `0` starts macro definition, clears/reuses the selected 12-byte
  record, sets alternate/data mode, and for lowercase `x` seeds the stored
  byte stream with `ESC &f`; selector `1` stops definition and clears
  empty/auto-prefix-only records.
- Selectors `2` and `3` replay an existing macro by pushing a data-chain frame
  whose byte `+8` is `4` and byte `+9` is the execute/call selector.
- `0xe418` writes frame `+0x00/+0x04` from macro record `+0x00/+0x04`, stores
  an environment snapshot pointer at frame `+0x0a`, and only call mode pushes
  a 10-byte context-stack entry from `0x782ee6` / `0x782ef6`.
- `0xe8f0` stores environment ranges as 0x100-byte linked chunks with a next
  pointer plus 63 longwords; `0xe8a2` restores those chunks and expects the
  chain to be exhausted, while `0xe972` and `0xe996` copy flat inclusive
  longword ranges in opposite directions.
- `0x170c` and `0x1710` allocate 64-byte heap units from opposite scan
  directions; `0x100` requests consume four units, optional zero-fill clears
  the allocated run, and `0x18b4` frees either a contiguous run or a linked
  chain when count is zero.
- `0xe65c` consumes either the call context-stack entry or static record
  `0x782c64`; entry bytes `+8/+9` refresh primary/secondary font slots through
  `0x13eb8`, then the selected slot passes through `0xc428`, optional
  empty-install rebuild, `0x1b04c`, and dirty-flag clear.
- Selectors `4`/`5` enable/disable overlay state, `6`/`7`/`8` delete
  all/temporary/current macros, and `9`/`10` toggle the temporary/permanent
  byte at record `+0x0a`.

- assigned macro id: `123`
- chained macro stream `1b 26 66 2d 31 32 33 79 30 78 31 58` assigns id `123`,
  starts lowercase definition mode through `0xdd08`, then stops and clears the
  auto-prefix-only record.
- ROM dispatch trace for the same stream walks modes `0 -> 1 -> 5 -> 17 -> 17
  -> 17 -> 0` through handlers `0xe112, 0xdd08, 0xdd08`, producing parsed
  records `81 79 ff 85 00 00, 80 78 00 00 00 00, 80 58 00 01 00 00` before the
  modeled macro side effects.
- macro definition dispatch trace proves `ESC &f1X` exits through alternate
  table `0x116f6` handler `0xdd08`, while payload bytes `21 0d` are stored and
  not claimed by alternate table handlers; normal CR would have selected
  `0xf02c` outside alternate mode.
- host-fetched macro definition stream drains `19` bytes from the modeled
  `0xa904` ring source before the same alternate parser trace stores payload
  `21 0d` and exits definition mode.
- macro definition stream `1b 26 66 31 32 33 59 1b 26 66 30 58 21 0d 1b 26 66
  31 58 1b 26 66 32 58` stores payload `21 0d`, stops with the record kept,
  then `ESC &f2X` pushes execute frame `{'payload': b'!\r', 'byte_count': 2,
  'byte_8': 4, 'byte_9': 2, 'environment': 'execute'}`.
- host-fetched macro execute stream drains `24` command bytes through the
  ROM/alternate parser trace, builds frame `{'payload': b'!\r', 'byte_count':
  2, 'byte_8': 4, 'byte_9': 2, 'environment': 'execute'}`, then replays
  payload `21 0d` through `0xa904` into handlers `0xd04a, 0xf02c`.
- macro call stream `1b 26 66 31 32 33 59 1b 26 66 30 58 21 0d 1b 26 66 31 58
  1b 26 66 33 58` pushes call frame `{'payload': b'!\r', 'byte_count': 2,
  'byte_8': 4, 'byte_9': 3, 'environment': 'call'}`.
- host-fetched macro call stream drains `24` command bytes through the
  ROM/alternate parser trace, builds frame `{'payload': b'!\r', 'byte_count':
  2, 'byte_8': 4, 'byte_9': 3, 'environment': 'call'}`, then replays payload
  `21 0d` through `0xa904` into handlers `0xd04a, 0xf02c`.
- macro overlay stream `1b 26 66 31 32 33 59 1b 26 66 30 58 21 0d 1b 26 66 31
  58 1b 26 66 34 58 1b 26 66 35 58` enables overlay id `123`, then disables
  parser overlay mode.
- macro overlay vertical-decipoint payload `1b 26 61 37 32 56 21` replays
  through `0xf60a` / `0xd04a`, queues compact text object `00 00 00 00 00 00
  00 01 20 90 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  00 00 00 00 00 00 00`, keeps rule object `00 00 00 00 01 07 88 01 00 07 00
  02 00 00`, and renders digest
  `7ef1cc5d5557fa5a30c57e8ad6918b09747c210daed2639e9d75ccfed727e964`.
- macro overlay raster payload `21 1b 2a 74 33 30 30 52 1b 2a 72 30 41 1b 2a
  62 32 57 c3 3c` replays through `0xe4f4` / `0x11774`, queues compact text
  plus mode-0 raster object `00 00 00 00 80 00 00 02 00 00 c3 3c`, keeps rule
  object `00 00 00 00 01 07 44 01 00 0a 00 02 00 00`, and renders digest
  `bc21050018fd3e992709c704fff732499aa9d06565de31d7ae0340869971c5b3`.
- macro overlay multi-row raster payload `21 1b 2a 74 33 30 30 52 1b 2a 72 30
  41 1b 2a 62 32 57 f0 0f 1b 2a 62 32 57 0f f0` replays through `0xe4f4` /
  `0x11774`, queues compact text plus mode-0 raster objects `00 00 00 00 80 00
  00 02 00 00 f0 0f` / `00 00 00 00 80 00 00 02 10 00 0f f0`, advances raster
  `row_y` to `2`, keeps rule object `00 00 00 00 01 07 44 01 00 0a 00 02 00
  00`, and renders digest
  `58c2293bbc6b187db0e964571e5812ab2192d32d8e648a38d61e407a58538638`.
- macro overlay span-flush payload `1b 26 61 36 4c 21` replays through
  `0xe4f4` / `0x11774`, routes `0xeb58` before printable `0xd04a`,
  materializes segment-list span object `00 00 00 00 40 00 00 01 32 00 03 00
  00 10 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  00`, keeps rule object `00 00 00 00 01 07 a4 02 00 07 00 02 00 00`, and
  renders digest
  `6775414374ba3c31f7846a180d93cc9b68e230ea6981ae722b32eb39081f9bca`.
- `0xe0a4` lookup statuses are existing/free/full = `1/0/2`; it skips a
  matching id with zero head, reuses stale-id free slot index `1`, and writes
  `0x782d7a = 0x00782aa4` for that allocation.
- macro permanence/delete streams prove selector `10` survives
  delete-temporary and selector `9` makes the same record removable: `{'id':
  123, 'payload': b'!\r', 'permanent': True}` / `{'id': 0, 'payload': b'',
  'permanent': False}`.
- macro delete-current/all streams prove selector `8` clears only the selected
  id while selector `6` clears the pool head records: `[{'id': 0, 'payload':
  b'', 'permanent': False}, {'id': 124, 'payload': b'?\r', 'permanent':
  False}]` / `[{'id': 0, 'payload': b'', 'permanent': False}, {'id': 0,
  'payload': b'', 'permanent': False}]`.
- macro guard streams prove definition mode ignores non-stop control and
  active data-chain mode ignores non-replay control while still allowing
  execute: `{'kind': 'macro-control-ignored', 'selector': 4, 'reason':
  'alternate-mode', 'sequence': b'\x1b&f4X', 'parameter': 4, 'handler': 56584,
  'chained': False}` / `[{'kind': 'macro-control-ignored', 'selector': 4,
  'reason': 'active-data-chain', 'sequence': b'\x1b&f4X', 'parameter': 4,
  'handler': 56584, 'chained': False}, {'kind': 'macro-data-chain', 'mode': 2,
  'payload': b'!\r', 'sequence': b'\x1b&f2X', 'parameter': 2, 'handler':
  56584, 'chained': False}]`.
- macro command streams now drain `279` bytes from the modeled `0xa904` ring
  source across id/start/stop, execute/call, overlay, permanence/delete,
  delete-current/all, and guard cases before landing on the same records and
  data-chain frames.
- macro execute frame payload fetches through `0xa904` as data-chain bytes
  `0x21 0x0d`, then end-marker helper `0xe22c` resumes outer byte `0x5a`.
- `0xe4f4` builds non-replay frame byte `+9 = 4` at `0x00782d4c` from the
  current macro record after snapshotting `281` flat longwords; `0xe22c` then
  copies `281` of them back from `0x7834c2` into `0x782d3a..0x78319a`, keeps
  the frame current, clears host gate bit 1 for a zero count, restores cursor
  long `0x11223344`, and sets `0x782a92 = 0x63`.
- macro context stack reset clears eight 10-byte records
  `0x00782c1e..0x00782c6d`; the eighth push ends at pointer `0x00782c6e`, the
  ninth unguarded push starts at pointer storage `0x00782c6e`, and an empty
  `0xe65c(0)` pop reads `0x00782c14`.
- `0x164a` default heap init takes `0x00783f4a`/`0x640b6`, reserves `2492`
  prefix bytes, seeds `6351` free 64-byte units, and stores payload base
  `0x00784c40`.
- heap allocator fixture: `0x170c(1,1,0x100)` returns `0x00783988`,
  `0x1710(2,0,0x40)` returns `0x00784108`, linked free releases
  `['0x00783988', '0x00783a88']`, and contiguous free releases
  `['0x00783c88']`.
- `0xe002` first append allocates chunk `0x00783988`, writes byte `0x1b` at
  payload offset `0`, and leaves raw record count `5`.
- `0xe002` boundary append links second chunk `0x00783a88` after `0x00783988`,
  writes byte `0x42`, and leaves raw count `0x105` for 253 payload bytes.
- macro stop normalization maps raw counts `7 -> 3` and `6 -> 2`; auto-prefix
  payload clears through `0xdfba`, while payload `b'!\r'` is kept.
- `0xe65c(0)` stack-pop fixture refreshes slots `[0, 1]`, copies remembered
  words `(8738, 13107)`, and leaves dirty flag `0` after final `0x1b04c`.
- `0xe65c` empty-install fixture records selected context `0x12345678`, active
  primary word `0x4567`, candidate `0x80345678`, and event path
  `['context-pop', 'context-entry-cleared', 'call-c428',
  'context-install-empty', 'call-1b4c0', 'call-144d2', 'call-14c64',
  'dirty-set', 'call-c428', 'call-1b04c', 'dirty-cleared']`.
- `0xe65c(1)` static-record fixture uses direct `+8` plus `0xe860` secondary
  class mismatch, refreshes slots `[0, 1]`, and clears `0x782c64` to
  `{'long_0': 0, 'long_4': 0, 'byte_8': 0, 'byte_9': 0}`.
- `0xe860` field probe reads class byte `0` from inline/downloaded record
  `+0x16` and class byte `1` from bit-30 offset-table record `+0x20`,
  refreshing slots `[0]` against selector `0x782da3 = 1`.
- `0xe65c` bridge fixture drives refresh slots `[0, 1]` through `0x13eb8` maps
  `0x00782f32`/`0x00783032`, then installs context record `0xc00ae122` into
  page-root font slot `0` through `0xc428`.
- macro execute payload stream `21 0d` queues glyphs `[32]`, coords `[1]`,
  then CR leaves cursor `0x00050000,0x00150000`.
- macro execute replay stream `21 0d` feeds the page-record fixture; object
  `00 00 00 00 00 00 00 01 20 00 01 00 00 00` bridges through `0x1edc6` and
  renders the same rows.
- macro execute parser-to-page-record boundary: replayed stream `21 0d` routes
  through handlers `0xd04a` and `0xf02c`, then feeds the same bridged
  page-record object and rows.
- macro call parser-to-page-record boundary: call frame stream `21 0d` routes
  through handlers `0xd04a` and `0xf02c`, then feeds the same bridged
  page-record object and rows as execute.
- macro mixed-control payload `1b 26 6b 31 47 21 0d 21` replays from the
  data-chain frame into the same page-record stream as host bytes; object `00
  00 00 00 00 00 00 02 20 00 01 20 3b 00` renders rows matching the direct
  mixed-stream model.
- host-fetched mixed-control macro stream drains `30` command bytes through
  the ROM/alternate parser trace, stores payload `1b 26 6b 31 47 21 0d 21`,
  builds frame `{'payload': b'\x1b&k1G!\r!', 'byte_count': 8, 'byte_8': 4,
  'byte_9': 2, 'environment': 'execute'}`, and replays into handlers `0xedf8,
  0xd04a, 0xf02c, 0xd04a` before producing the same ROM-derived rows.
- macro mixed-control parser-to-page-record boundary: replayed stream `1b 26
  6b 31 47 21 0d 21` routes through handlers `0xedf8`, `0xd04a`, `0xf02c`, and
  `0xd04a`, then feeds the same bridged page-record object and rows.
- macro replay render-entry boundary: execute/call payload rows and
  mixed-control payload rows now cross `0x1ed84` active-record copy and
  `0x1ef6a`; dispatch counts `1` / `1`.
- macro execute payload page-record layer composes with a selector-7 rule and
  mode-0 raster row; composed row 12:
  `##....##..####..####....................`
- lowercase start payload: `b'\x1b&f'`, stop event `{'kind':
  'macro-stop-cleared-empty', 'index': 0}`
- execute frame: `{'payload': b'!\r', 'byte_count': 2, 'byte_8': 4, 'byte_9':
  2, 'environment': 'execute'}`
- execute frame metadata: `{'frame_addr': 7875916, 'frame_size': 14,
  'payload_ptr_source': 'record+0x00', 'byte_count_source': 'record+0x04',
  'env_snapshot_source': 7877010, 'env_snapshot_target': 7877018,
  'env_snapshot_ptr': 13697024, 'context_stack_entry': None}`
- call frame: `{'payload': b'!\r', 'byte_count': 2, 'byte_8': 4, 'byte_9': 3,
  'environment': 'call'}`
- call frame metadata: `{'frame_addr': 7875916, 'frame_size': 14,
  'payload_ptr_source': 'record+0x00', 'byte_count_source': 'record+0x04',
  'env_snapshot_source': 7875998, 'env_snapshot_target': 7877018,
  'env_snapshot_ptr': 13697024, 'context_stack_entry': {'addr': 7875614,
  'long_0_source': 7876326, 'long_4_source': 7876342, 'byte_8': 0, 'byte_9':
  0}}`
- execute frame-end event: `{'kind': 'macro-frame-end', 'mode': 2,
  'frame_addr': 7875916, 'restore': {'dest_start': 7877010, 'dest_end':
  7877018, 'restored': [7877010, 7877014, 7877018], 'leftover': [],
  'exhausted': True, 'error': None}, 'freed_snapshot_ptr': 13697024,
  'context_entry': None, 'post_helper': 74762, 'log_helper': 40640}`
- call frame-end event: `{'kind': 'macro-frame-end', 'mode': 3, 'frame_addr':
  7875916, 'restore': {'dest_start': 7875998, 'dest_end': 7877018, 'restored':
  [7875998, 7876002, 7876006, 7876010, 7876014, 7876018, 7876022, 7876026,
  7876030, 7876034, 7876038, 7876042, 7876046, 7876050, 7876054, 7876058,
  7876062, 7876066, 7876070, 7876074, 7876078, 7876082, 7876086, 7876090,
  7876094, 7876098, 7876102, 7876106, 7876110, 7876114, 7876118, 7876122,
  7876126, 7876130, 7876134, 7876138, 7876142, 7876146, 7876150, 7876154,
  7876158, 7876162, 7876166, 7876170, 7876174, 7876178, 7876182, 7876186,
  7876190, 7876194, 7876198, 7876202, 7876206, 7876210, 7876214, 7876218,
  7876222, 7876226, 7876230, 7876234, 7876238, 7876242, 7876246, 7876250,
  7876254, 7876258, 7876262, 7876266, 7876270, 7876274, 7876278, 7876282,
  7876286, 7876290, 7876294, 7876298, 7876302, 7876306, 7876310, 7876314,
  7876318, 7876322, 7876326, 7876330, 7876334, 7876338, 7876342, 7876346,
  7876350, 7876354, 7876358, 7876362, 7876366, 7876370, 7876374, 7876378,
  7876382, 7876386, 7876390, 7876394, 7876398, 7876402, 7876406, 7876410,
  7876414, 7876418, 7876422, 7876426, 7876430, 7876434, 7876438, 7876442,
  7876446, 7876450, 7876454, 7876458, 7876462, 7876466, 7876470, 7876474,
  7876478, 7876482, 7876486, 7876490, 7876494, 7876498, 7876502, 7876506,
  7876510, 7876514, 7876518, 7876522, 7876526, 7876530, 7876534, 7876538,
  7876542, 7876546, 7876550, 7876554, 7876558, 7876562, 7876566, 7876570,
  7876574, 7876578, 7876582, 7876586, 7876590, 7876594, 7876598, 7876602,
  7876606, 7876610, 7876614, 7876618, 7876622, 7876626, 7876630, 7876634,
  7876638, 7876642, 7876646, 7876650, 7876654, 7876658, 7876662, 7876666,
  7876670, 7876674, 7876678, 7876682, 7876686, 7876690, 7876694, 7876698,
  7876702, 7876706, 7876710, 7876714, 7876718, 7876722, 7876726, 7876730,
  7876734, 7876738, 7876742, 7876746, 7876750, 7876754, 7876758, 7876762,
  7876766, 7876770, 7876774, 7876778, 7876782, 7876786, 7876790, 7876794,
  7876798, 7876802, 7876806, 7876810, 7876814, 7876818, 7876822, 7876826,
  7876830, 7876834, 7876838, 7876842, 7876846, 7876850, 7876854, 7876858,
  7876862, 7876866, 7876870, 7876874, 7876878, 7876882, 7876886, 7876890,
  7876894, 7876898, 7876902, 7876906, 7876910, 7876914, 7876918, 7876922,
  7876926, 7876930, 7876934, 7876938, 7876942, 7876946, 7876950, 7876954,
  7876958, 7876962, 7876966, 7876970, 7876974, 7876978, 7876982, 7876986,
  7876990, 7876994, 7876998, 7877002, 7877006, 7877010, 7877014, 7877018],
  'leftover': [], 'exhausted': True, 'error': None}, 'freed_snapshot_ptr':
  13697024, 'context_entry': {'addr': 7875614, 'long_0_source': 7876326,
  'long_4_source': 7876342, 'byte_8': 0, 'byte_9': 0}, 'post_helper': 74762,
  'log_helper': 40640}`
- permanent survives delete-temporary: `{'id': 123, 'payload': b'!\r',
  'permanent': True}`

## Resource HEAD Scanner Fixtures

These fixtures model startup/resource routine `0x41a`, which searches optional
resource windows for `HEAD`, walks length-delimited records, and treats record
type `0x000000be` as an executable extension handoff.

- verified `IC32,IC15` scan: one `HEAD` at `0x00000`, `24` walked typed
  records from `0x0004c` through `0x2e122`, terminator `0x00000000` at
  `0x32f80`, next probe step `0x40000`, and final probe `0x40000`.
- simple resource-pair mirror consequence: scanning `IC32,IC15 + IC32,IC15`
  would see `HEAD` offsets 0x00000, 0x40000, walk 48 typed records, and
  terminate at probes `0x32f80 -> 0x80000`; therefore a full mirror at
  `0x0c0000` is not a local row-source detail, it would also duplicate
  candidate-scan input unless hardware/gating hides it from the scanner.
- non-HEAD continuation scan consequence: appending the code pair or zero-fill
  after `IC32,IC15` keeps the `0x41a` scan to one `HEAD` chain and 24 typed
  records; the second probe at `0x40000` sees markers `0x00800000` and
  `0x00000000`, so both variants skip to final probe `0x80000` instead of
  duplicating records.
- boundary fixture: crossing the cumulative `0x40000` threshold at `0x40000`
  raises the next probe units to `2`, so a null terminator steps by `0x80000`
  instead of the default `0x40000`.
- executable fixture: type `0xbe` with length `8` jumps to `0x200010`; length
  `7` reports error bytes `D0=0xe0`, `D1=0x10` through handler `0x0128c`.

## Built-In Glyph Bitmap Fixtures

These rows are decoded from the resource-ROM bytes returned by the same
built-in offset-table path that renderer helper `0x1f354` uses. `#` is a set
pixel and `.` is a clear pixel; rows are clipped to the glyph width field.

### context `0x4008004c`, glyph `0`

entry `0x001088`, bitmap `0x001092`, width `9`, rows `32`, span `2`

`...###...`
`..#####..`
`..#####..`
`..#####..`
`..#####..`
`..#####..`
`..#####..`
`..#####..`
`..#####..`
`...###...`
`..#####..`
`..#####..`
`...###...`
`..#####..`
`...###...`
`..#####..`
`...###...`
`...###...`
`...###...`
`...###...`
`...###...`
`.........`
`.........`
`.........`
`.........`
`..#####..`
`.#######.`
`#########`
`#########`
`#########`
`.#######.`
`..#####..`

### context `0x44080418`, glyph `0`

entry `0x007baa`, bitmap `0x007bb4`, width `28`, rows `29`, span `4`

`...........######...........`
`........############........`
`.......####......####.......`
`.....###............###.....`
`....##................##....`
`...##..................##...`
`..##....................##..`
`..##....................##..`
`.##......................##.`
`.##......................##.`
`.##......#........#......##.`
`##......###......###......##`
`##.......#........#.......##`
`##........................##`
`##........................##`
`##........................##`
`##........................##`
`##........................##`
`.##......................##.`
`.##.....##........##.....##.`
`.##......##......##......##.`
`..##......########......##..`
`..##.......######.......##..`
`...##..................##...`
`....##................##....`
`.....###............###.....`
`.......###........###.......`
`........############........`
`...........######...........`

### context `0x440946b4`, glyph `0`

entry `0x018730`, bitmap `0x01873a`, width `16`, rows `16`, span `2`

`......####......`
`....########....`
`..###......###..`
`..##........##..`
`.##..........##.`
`.##..........##.`
`##.####..####.##`
`##..##....##..##`
`##............##`
`##............##`
`.##..#....#..##.`
`.##..######..##.`
`..##..####..##..`
`..###......###..`
`....########....`
`......####......`

### context `0x440946b4`, glyph `32`

entry `0x015330`, bitmap `0x01533a`, width `4`, rows `22`, span `1`

`####`
`....`
`####`
`....`
`####`
`....`
`####`
`....`
`####`
`....`
`####`
`....`
`####`
`....`
`####`
`....`
`####`
`....`
`####`
`....`
`####`
`....`

## Main Row-Copy Integration Fixtures

These fixtures feed the same resource glyph bytes through the main
compact-glyph row-copy table at `0x1f08e`. The destination buffer uses a
synthetic `0x20` byte row stride, matching the existing row-copy fixtures, and
the reconstructed destination rows must match the direct resource decode
above.

| Context | Glyph | Span | Helper | Result |
| ---: | ---: | ---: | ---: | --- |
| `0x4008004c` | `0` | `2` | `0x01fe76` | decoded destination rows match resource rows |
| `0x44080418` | `0` | `4` | `0x0207ac` | decoded destination rows match resource rows |
| `0x440946b4` | `0` | `2` | `0x01fe76` | decoded destination rows match resource rows |
| `0x440946b4` | `32` | `1` | `0x01fa5c` | decoded destination rows match resource rows |

A ROM-scanned row-copy matrix now selects the first mode-1 built-in glyph
found for each available render span `1`, `2`, `4`, `6`, and `8`, then
compares direct bitmap decode against the `0x1f08e` destination-copy path.

| Span | Context | Glyph | Entry | Width | Rows | Helper | First row | Result |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `1` | `0x4008004c` | `91` | `0x003916` | `3` | `50` | `0x01fa5c` | `###` | `row-copy rows match direct decode` |
| `2` | `0x4008004c` | `0` | `0x001088` | `9` | `32` | `0x01fe76` | `...###...` | `row-copy rows match direct decode` |
| `4` | `0x4008004c` | `1` | `0x0010d2` | `18` | `17` | `0x0207ac` | `.#####......#####.` | `row-copy rows match direct decode` |
| `6` | `0x40099d18` | `2` | `0x01add4` | `38` | `19` | `0x0212e4` | `............###.......###.............` | `row-copy rows match direct decode` |
| `8` | `0x40099d18` | `91` | `0x01d25c` | `50` | `3` | `0x02201c` | `##################################################` | `row-copy rows match direct decode` |

- Full built-in glyph scan: `5730` glyph records across `24` resource records;
  mode counts `[(0, 420), (1, 5310)]`, mode-1 render spans `[(1, 244), (2,
  1080), (4, 3348), (6, 552), (8, 86)]`, max mode-1 width `50`, and max mode-1
  rows `50`.
- The same scan finds `0` render spans wider than 16 bytes and `0` non-mode-1
  entries with nonzero bitmap deltas; the `420` mode-0 entries are zero-delta
  aliases at one entry per resource record, so the verified built-in ROMs do
  not provide a normal bitmap-entry fixture for `0x1f0d2`, `0x1f1f0`, or
  `0x1f264`.

## Direct Control-Code Cursor Fixtures

These fixtures model the packed 12-subunit cursor/page state touched by
`0xf02c..0xf55e`. They are synthetic state fixtures, not a full parser
byte-stream run yet, but they pin the ROM-derived side effects that text
streams need before page-object rendering.

- `ESC &k#G` line-termination bits: `0 -> 0x00`, `1 -> 0x80`, `2 -> 0x60`, `3
  -> 0xe0`.
- `ESC &k#H` stores HMI as 30 packed subunits per 1/120-inch unit; `ESC &k6H`
  stores packed advance `15` in `0x78315c` and moves following printable
  spacing to compact coords `0x0600` and `0x0501`.
- CR resets x to the left margin and flushes a pending text span; in mode 1 it
  also advances y from `20+11/12` by `2/12` to `21+1/12`.
- LF in mode 2 performs the CR-style x reset before advancing y by VMI.
- FF in mode 2 performs the CR-style x reset, flushes pending text,
  ensures/finalizes a page root marker, and leaves pending text/page-eject
  state as `0xff`.
- HT from x `17`, left margin `5`, and HMI `1` advances to the next
  eight-column stop at x `21`; a second fixture clamps HT to page width `90`
  when the cursor is already beyond the right limit.
- BS subtracts HMI, clamps at the left margin when it would cross it, and in
  alternate metrics mode subtracts the previous-width word instead.
- Byte-stream fixtures now drive the same model from actual PCL/control bytes:
  `ESC &k1G` followed by CR applies CR+LF, `ESC &k2G` followed by LF applies
  CR+LF, `ESC &k2G` followed by FF performs the CR-style reset plus page-eject
  finalization, `ESC &k3G` followed by CR/LF/FF applies all three combined
  line-termination bits in sequence, and `ESC &k0G` followed by HT/BS advances
  to x `21` then backs up to x `20`.
- `ESC &f0S` pushes the horizontal cursor and the vertical cursor plus
  `0x782dbe` onto the cursor stack; `ESC &f1S` pops, restores horizontal
  position clamped to active extent minus `1/12`, restores vertical position
  after subtracting `0x782dbe` and clamps to printable extent minus `1/12`,
  then clears pending/right-limit flags. A byte-stream fixture now drives `ESC
  &f0S` / `ESC &f1S` through the same `0xf75e` selector path.
- `ESC &a#C` converts columns through current HMI, `ESC &a#H` converts
  decipoints as five packed subunits per decipoint, and both commit through
  horizontal helper `0xf4ca` with absolute/relative handling and page-width
  clamps.
- `ESC &a#R` converts rows through current VMI; absolute rows add the
  firmware's `0.7200` row bias before using the top offset, while relative
  rows add to the current vertical cursor. `ESC &a#V` uses the same
  five-subunit decipoint conversion. Both commit through vertical helper
  `0xf6e2` and clamp to vertical bounds where the handler does so. A
  byte-stream fixture now drives chained `ESC &a3.5c+1R` through handlers
  `0xf39e` and `0xf560`.
- `ESC &s#C` toggles the end-of-line wrap flag: selector `0` stores enabled,
  selector `1` clears it, and other selectors leave the current flag
  unchanged.
- `ESC *p#X/#Y` shifts the parsed integer left 16 bits to form whole-dot
  packed cursor coordinates, then commits through the same `0xf4ca` and
  `0xf6e2` helpers as the `ESC &a` cursor-position commands.
- `ESC &l#D` accepts only the ROM LPI set `1,2,3,4,6,8,12,16,24,48`, treats
  zero as 12 LPI, and writes line advance `0x783160`; `ESC &l#C` converts VMI
  in 1/48-inch units using 75 packed subunits per unit and allows zero without
  setting the modified-layout flag.
- `ESC &l#P` uses current VMI to convert line count into page extent, chooses
  a page code from orientation thresholds, and refreshes the following
  printable cursor; `ESC &l66P!` queues `!` at compact coord `0x9001`.
- `ESC &l#E` sets top offset `0x782dce` from VMI lines minus vertical offset
  source `0x782dbe`, then recomputes default text-length bottom `0x782dd2`;
  `ESC &l#F` stores explicit text-length bottom as top offset plus VMI-scaled
  lines, or restores the default when the parameter is zero. A byte-stream
  fixture now drives chained `ESC &l8c6d3e2F` through handlers `0xcb00`,
  `0xc992`, `0xece2`, and `0xea9e`; `ESC &l#L` reaches `0xee64` and toggles
  perforation-skip byte `0x783191` for selectors `0` and `1`.
- `ESC &a#L` stores an absolute left margin in HMI columns when it does not
  pass `right_margin - HMI`; it moves the cursor and flushes pending spans
  only when the new margin is right of the current cursor or pending text is
  marked.
- `ESC &a#M` stores `abs(parameter) + 1` HMI columns as the right margin,
  rejects values before `left_margin + HMI`, clamps beyond page width, and
  moves the cursor/right-limit latch when the new right margin is left of the
  current cursor. A byte-stream fixture now drives chained `ESC &a6l9M`
  through handlers `0xeb58` and `0xec0c`.
- The direct-control fixture parser intentionally recognizes only `ESC &k#G`,
  `ESC E`, and direct control bytes; mixed printable/control/reset coverage is
  added separately for narrow normal-mode streams, while combined escape
  sequences and real page-object allocation still need fuller parser-driven
  fixtures.

- cursor stack push entry: `{'x': 786436, 'stored_y': 6160389}`
- cursor stack pop cursor: x `0x000c0004`, y `0x00220005`
- cursor stack stream events: `[{'sequence': b'\x1b&f0S', 'parameter': 0,
  'handler': 63326, 'event': {'kind': 'cursor-push', 'depth': 1, 'entry':
  {'x': 786436, 'stored_y': 6160389}}}, {'sequence': b'\x1b&f1S', 'parameter':
  1, 'handler': 63326, 'event': {'kind': 'cursor-pop', 'depth': 0, 'entry':
  {'x': 786436, 'stored_y': 6160389}, 'max_x': 132644875, 'max_y':
  202440715}}]`
- cursor stack clamped pop: x `0x0063000b`, y `0x004f000b`
- `ESC &a3.5C`: absolute x `0x00070000`, relative x `0x00110000`
- `ESC &a72H`: x `0x001e0000`, clamped `ESC &a500H` x `0x00640000`
- `ESC &a2R`: y `0x007a0007`, relative `ESC &a+1R` y `0x00200000`
- cursor-position stream events: `[{'sequence': b'\x1b&a3.5c', 'record':
  b'\x80c\x00\x03\x13\x88', 'parameter': 3, 'fraction': 5000, 'relative':
  False, 'handler': 62366, 'cursor_before': {'x': 655360, 'y': 1310720},
  'event': {'kind': 'horizontal-position', 'relative': False, 'amount':
  458752, 'cursor_x': 458752}, 'chained': True}, {'sequence': b'+1R',
  'record': b'\x81R\x00\x01\x00\x00', 'parameter': 1, 'fraction': 0,
  'relative': True, 'handler': 62816, 'cursor_before': {'x': 458752, 'y':
  1310720}, 'event': {'kind': 'vertical-position', 'relative': True, 'amount':
  786432, 'cursor_y': 2097152, 'clamp_max': False}, 'chained': False}]`
- `ESC &a72V`: clamped y `0x006e0000`
- `ESC &s#C`: selector 0 flag `1`, selector 1 flag `0`, selector 2 flag `1`
- `ESC *p25X`: x `0x00190000`, relative `ESC *p+5X` x `0x000f0000`, clamped
  `ESC *p500X` x `0x00640000`
- `ESC *p12Y`: y `0x00660000`, relative `ESC *p+5Y` y `0x00190000`, clamped
  `ESC *p500Y` y `0x00780000`
- `ESC &l6D`: VMI `0x00320000`, pending cursor y `0x007e0000`
- `ESC &l8C`: VMI `0x00320000`, `ESC &l1.5C` VMI `0x00090004`
- `ESC &l66P`: extent `3300`, refreshed cursor y `0x007e0000`
- `ESC &l3E`: top offset `0x005a0000`, text bottom `0x00f00000`
- `ESC &l2F`: text bottom `0x00be0000`, `ESC &l0F` default bottom `0x00f00000`
- `ESC &l1L`: perforation skip `1`
- vertical-layout stream events: `[{'sequence': b'\x1b&l8c', 'record':
  b'\x80c\x00\x08\x00\x00', 'parameter': 8, 'fraction': 0, 'relative': False,
  'handler': 51968, 'cursor_before': 1310720, 'events': [{'kind':
  'vertical-cursor-refresh', 'cursor_y': 2359296}, {'kind': 'vmi', 'vmi':
  3276800}], 'chained': True}, {'sequence': b'6d', 'record':
  b'\x80d\x00\x06\x00\x00', 'parameter': 6, 'fraction': 0, 'relative': False,
  'handler': 51602, 'cursor_before': 2359296, 'events': [{'kind':
  'vertical-cursor-refresh', 'cursor_y': 2359296}, {'kind': 'lines-per-inch',
  'vmi': 3276800}], 'chained': True}, {'sequence': b'3e', 'record':
  b'\x80e\x00\x03\x00\x00', 'parameter': 3, 'fraction': 0, 'relative': False,
  'handler': 60642, 'cursor_before': 2359296, 'events': [{'kind':
  'vertical-cursor-refresh', 'cursor_y': 8257536}, {'kind': 'top-margin',
  'top_offset': 5898240, 'text_length_bottom': 15728640}], 'chained': True},
  {'sequence': b'2F', 'record': b'\x80F\x00\x02\x00\x00', 'parameter': 2,
  'fraction': 0, 'relative': False, 'handler': 60062, 'cursor_before':
  8257536, 'events': [{'kind': 'text-length', 'bottom': 12451840}], 'chained':
  False}]`
- `ESC &a6L`: left margin `0x000c0000`, cursor `0x000c0000`
- `ESC &a9M`: right margin `0x00140000`, cursor `0x00140000`
- margin stream events: `[{'sequence': b'\x1b&a6l', 'record':
  b'\x80l\x00\x06\x00\x00', 'parameter': 6, 'handler': 60248, 'cursor_before':
  3276800, 'events': [{'kind': 'left-margin', 'margin': 786432}], 'chained':
  True}, {'sequence': b'9M', 'record': b'\x80M\x00\t\x00\x00', 'parameter': 9,
  'handler': 60428, 'cursor_before': 3276800, 'events': [{'kind':
  'right-margin-cursor-move', 'cursor_x': 1310720}, {'kind': 'right-margin',
  'margin': 1310720}], 'chained': False}]`

## `ESC E` Reset Fixtures

The initial reset fixtures model the sequence documented in
`generated/analysis/ic30_ic13_esc_e_reset_flow.md`. They are synthetic state
fixtures driven by the actual byte stream `ESC E`; the publication-stream
fixtures below now supplement them with parser-produced compact page objects
from `! ESC E`.

- Valid page-root case: flushes pending text span, runs the active-record wait
  hook, publishes the current page/control record, sets the publication flag,
  clears transient page bytes, then clears the current page root.
- Missing/invalid page-root case: clears the current page root without
  publication.
- The missing-root case now also starts `ESC E` from the modeled `0xa904` ring
  source, reaches ROM parser handler `0xcc52`, and lands on the same
  no-publication reset state.
- Both cases reset orientation to portrait, recompute the vertical offset from
  `0x96 - source`, clear the related vertical offset word, reinitialize raster
  state to scale minus one `3` / scale `4`, refresh HMI and symbol snapshots
  from the current-font context, reset the parser/data-chain pointer to
  `0x782d3e`, clear parser/text accumulation state, prune command/data
  records, and clear reset status `0x782a93`.
- Remaining reset work is physical/default-environment correlation and byte
  streams that expose new reset publication fields, not the software-visible
  reset-to-render contract for a compact text pending page.

## Compact Text Bucket Fixture

This fixture starts with the base built-in character map that `0x14d9c`
creates for `LINE_PRINTER`: host byte `0x21` maps to glyph byte `0x20`. The
`0x1393a` source-object model records context `0x440946b4`, glyph entry
`0x015330`, flag `1`, `x=0`, `y=0`, and context slot `0`; the `0x12f2e`
producer model then emits the short compact text bucket consumed by renderer
`0x1effe` / `0x1f034`. The compact object bytes now come from the modeled
source fields rather than a hand-written glyph/coordinate pair, and a mode-0
split fixture drives `0x1f414`-style current-band rows plus continuation rows
through the `0x7810b4 + D2` fallback buffer.

- base map: host `0x21` -> glyph `0x20`
- symbol-set stream events: `[{'sequence': b'\x1b(2U', 'record':
  b'\x80U\x00\x02\x00\x00', 'slot': 0, 'setup_handler': 73758,
  'terminal_handler': 73918, 'dispatch_target': 114852, 'parameter': 2,
  'final': 85, 'kind': 'symbol-set', 'dirty_before_refresh': 1,
  'dirty_maps_before_refresh': 1, 'font_id_call': None, 'previous_word': 277,
  'provisional_word': 85, 'requested_word': 85, 'active_word': 85,
  'refreshes': 1}, {'sequence': b'\x1b)0E', 'record':
  b'\x80E\x00\x00\x00\x01', 'slot': 1, 'setup_handler': 73736,
  'terminal_handler': 73918, 'dispatch_target': 114852, 'parameter': 0,
  'final': 69, 'kind': 'symbol-set', 'dirty_before_refresh': 1,
  'dirty_maps_before_refresh': 1, 'font_id_call': None, 'previous_word': 277,
  'provisional_word': 5, 'requested_word': 5, 'active_word': 5, 'refreshes':
  2}]`
- symbol-set parser-to-map boundary: stream `1b 28 32 55 1b 29 30 45` routes
  primary setup `0x1201e`, secondary setup `0x12008`, and terminal handler
  `0x120be`, then the modeled active words `0x0055` and `0x0005` feed the
  patch-table and Roman Extension map updates below.
- `0xc580` dirty primary refresh fixture:
dirty `0x782f2c = 1`, selector slot `0`, no live page-root slots, and a
present page root find slot `0` clear, run `0xc4fc`, call `0x13eb8`, then call
`0xc428`; page-root context slot `0` receives selected longword `0xc008004c`,
`0x78297e` selects slot `0`, and live flags stay clear until printable source
queuing marks `0x78297f+n`. The secondary mirror uses selector slot `1` and
installs selected longword `0xc00ae122` through the same path.
- `0xc580` all-live matching-context fixture:
all 16 live flags set briefly toggles `0x78298f`, calls `0x13eb8`, reuses
existing page-root context slot `3` through `0xc4fc`, calls `0x13eb8` again,
and leaves `0xc428` selecting slot `3` for subsequent text queuing.
- `0xc580` shortcut fixtures:
all-live/no-match returns `0x11` from `0xc4fc` and skips the second `0x13eb8`
plus `0xc428`; selector mismatch calls only `0x13eb8(D5)` before the final
active-to-remembered word copy.
- `0xc580` dirty-2 fixtures:
selector match calls only `0xc428(D5)` before the final copy, with primary
`0x782ee6` and secondary `0x782ef6` both pinned; selector mismatch skips both
`0x13eb8` and `0xc428`.
- scanned candidate-list partitioning: `0x1a9be` leaves total `5`, class-one
  low/range counts `1`/`1`, class-zero low/range counts `1`/`1`, and cursor
  windows `0x7827a0=0x782324 / 0x7827a4=0x782328 / 0x7827a8=0x78232c /
  0x7827ac=0x78232c / 0x7827b0=0x782330 / 0x7827b4=0x782334`; this pins the
  list starts used later by current/default font searches.
- actual `IC32,IC15` built-in candidate scan: `24` accepted `HEAD`-path
  records, class-one low/range counts `12`/`0`, class-zero low/range counts
  `12`/`0`, first context `0x4008004c`, last context `0x400ae122`.
- page/font scheduler optional-window fixture: `0x19dd2` predicates `(1, 1)`
  run long refresh helpers `['0x1ba92', '0x178fa', '0x19d9c', '0x1a4fa',
  '0x1a900', '0x19fb8']`, prune `1` candidate through `0x1ba92`/`0x1bd2e`,
  release `1` current record through `0x178fa`/`0x1887a`, mark dirty indexes
  `[0]`, rescan range `(2097152, 4194302)` through `0x1a4fa`/`0x1a616`, and
  commit canonical slot zero to `[8738, 0, 0, 0, 0, 0, 0, 0, 0, 85]` through
  `0x1a900`.
- page/font scheduler branch-exit fixture: unchanged predicates return `D7=1`
  after `['0x19fb8', '0x1b04c']`, while the modeled `0x72a2 == 0` status
  branch writes `0x780e8d = 1`, raises mask `0x00000200`, returns `D7=0`, and
  calls `['0x72a2', '0x9bee', '0x19fb8']`.
- host quiesce scheduler callers: `0x447a` ignores scheduler `D7` and always
  writes tail bytes `{'0x780e3a': 1, '0x7821cd_bit0': 1, '0x7821b0': 1,
  '0x780e68': 0}`, while `0x4760` returns immediately for `D7=0` and, for
  `D7!=0`, writes `{'0x782272': 3, '0x782278': 0, '0x782288': 7, '0x78228c':
  100, '0x782290': 284280, '0x7822de': 4660}`, optionally reports `(226, 32)`,
  and loops through the menu/default byte path unless a new input byte clears
  `0x782272`.
- font-resource scan scheduler caller: `0x1a2e4` snapshots candidate count `3`
  into `0x782780`, ignores scheduler `D7=0/1`, then calls `0x1b50e` with
  `0x78219b/0x78219c`; only the `0x1b50e` return drives the following `0x6364`
  default refresh. The zero-candidate case reports `(231, 57)` before still
  reaching the scheduler call.
- font sample row fields: `0x1cabe` over first `COURIER` record `0x000418`
  emits printable bytes `49 30 31 43 4f 55 52 49 45 52 31 30 31 32 31 30 55`,
  with prefix `I01`, name `COURIER`, pitch `10`, height `12`, symbol `10U`,
  `2` fixed-space calls through `0xd0f0`, and `12` explicit horizontal units
  through `0x1d152` before the sample bytes.
- font sample row-field page-record placement: that first `COURIER` row-field
  stream now queues `17` printable glyph entries into compact bucket `[0]`
  with object counts `[7, 10]`, leaves the two `0xd0f0` symbol-column fixed
  spaces as cursor-only events, ends at cursor x `0x05be0000`, and renders
  bucket rows with hash
  `4756fe985af471915c3de75c4637c09e51c28a80af75989a1125f6d9cbf2347c`.
- font sample carried first row: adding sample run 1 after those row fields in
  the same page-record state queues `25` more bytes, extends the page record
  to buckets `[-1, 0]`, leaves final cursor x `0x08ac0000`, and renders bucket
  hashes `{-1:
  '78d11b068621d9a47fcce073c9b5d1a591bdfc9368bf5d32f6e81186911d4428', 0:
  '975779b94eb6e9eefaaa0134e7ef5915d5471e16b6568315f612def3cb440949'}`.
- font sample run-2 transition: after run 1, `0xf06e` resets cursor x from
  `0x08ac0000` to line anchor `0x00000000`; `0x1d050` uses first `COURIER`
  record `+0x16 = 40`, prior `0x783f06 = 13`, and `0x1cfe4` advance `744`
  subunits to move y from `0x00200000` to `0x005e0000`; `0x1d152(0x31)` then
  starts sample run 2 at x `0x05be0000`. The carried page record queues run 2
  into buckets `[-1, 0, 3, 4]`, final cursor `0x08ac0000,0x005e0000`, with
  compact object hashes `{-1:
  ['9917ff7d8cf390817753aa4bd4e199622d7d91ec593529ff1a5a638d06c9cbe1'], 0:
  ['c7ee0c27ccc1fef0666e2eaca8330a3c2e2e84faff310d7c9f82e42a9898b388',
  '7e99a72f06b2b32c21bf0da80de005928b58ae8602c0bb5bcb4ad999430ca6bd',
  '8dc2c1c43fd8e67d554ee018595ad3715d1f7731f79cd42f3037e6d026733d32',
  '99a818922a85049e8edfabbc8d8ebe5317b1f676ab74cbee1717d64717b3219e'], 3:
  ['38ecdd4f968463692b9181e9f39b2b8f66850555ca6dfa1b2d8fd3043d80df87',
  'd5ebcb8ec98bac63f306729ef80239ccbfdd7d7e2e837bcc6ffa035fe314fdfd'], 4:
  ['2e7a32816cfa8ffd670eb71e6d0443e26537f7d5e4d9f7e0d02dd111bbec8fca']}`.
- font sample page-limit continuation branches: `0x1ca2c` compares cursor y
  `32` plus row height `13` against page limit `45`, so equality takes
  `0x1c9f6`, while page limit `95` fits. `0x1d050` advances first `COURIER` y
  from `0x00520000` to `0x00900000`; with page limit `100` it calls `0x1c9f6`,
  reprints heading via
  `0x1ca2c(source=3,row=1,current=0x4008004c,selected=0x44080418)`, then
  schedules a second `0x1cfe4` advance of `744` subunits, while page limit
  `1010` takes the no-continuation path.
- font sample heading-continuation page record: fixture `font sample heading
  continuation emits fresh source heading page record` ties the `0x1ca2c ->
  0x1c9f6` pre-heading overrun to a fresh `INTERNAL FONTS` heading-only
  segment with context `0x4008004c`, buckets `[0]`, final cursor
  `0x00000000,0x00520000`, and bucket digest
  `e43b602451f3f31ea84e49c7be1d12b34ae3d1b7369b5dd7096aa7e96db1268c`.
- font sample cartridge heading continuations: fixture `font sample cartridge
  heading continuations emit source-specific page records` reuses the same
  `0x1ca2c -> 0x1c9f6` pre-heading overrun for source 1 class-zero context
  `0x4008004c` and source 2 class-one context `0x40099d18`; it emits `b'LEFT
  FONT CARTRIDGE'` and `b'RIGHT FONT CARTRIDGE'` heading-only page records
  with bucket digests
  `a4c3a808dd2430bc463e091a57e0462bdff94e50a5e8a5b21f615764e9f6a63d` and
  `03025c4239ec3d130bff4f4e05362b1c9730b9848e7e99a2934c4868b600badb`.
- font sample row-continuation page record: fixture `font sample row
  continuation emits fresh source heading page record` ties that `0x1d050 ->
  0x1c9f6 -> 0x1ca2c` branch to a fresh `INTERNAL FONTS` source-heading
  segment for row `I01COURIER101210U`, context `0x44080418`, buckets `[0, 2,
  3, 6, 7, 8, 16, 24, 32, 40, 48, 56, 64]`, final cursor
  `0x08ac0000,0x00900000`, and bucket digest
  `2dc6c3326aad3118d2b96c44cf0ab727ee2926069c5035722cceef470db8b7ef`.
- font sample class-one row-continuation page record: fixture `font sample
  class-one row continuation emits fresh source heading page record` ties the
  class-one `0x1d050 -> 0x1c9f6 -> 0x1ca2c` branch from current context
  `0x40099d18` to selected context `0x4409a0e4`, emits row
  `I16COURIER101210U`, queues buckets `[0, 3, 4, 7, 8, 16, 24, 32, 40, 48, 56,
  64]`, final cursor `0x08ac0000,0x00900000`, and bucket digest
  `842dd781a1093819f918e128999786f94f16cc3562ca25c3a82503ced74f3f3c`.
- font sample alternate-row continuation page record: fixture `font sample
  alternate-row continuation emits preadvanced row page record` ties `0x1d868`
  D7=1 through caller sequence `0x1c4a4 -> 0x1d868 -> 0x1c4b6 -> 0x1c9f6 ->
  0x1c4ca -> 0x1ca2c -> 0x1c4d4 -> 0xf06e -> 0x1c4e8 -> 0x1d050 -> 0x1c4f2 ->
  0x1cabe`, emits row `I01COURIER101210U` after pre-row y advance `0x00520000
  -> 0x00900000`, queues buckets `[0, 7, 8, 16, 24, 32, 40, 48, 56, 64]`, and
  pins bucket digest
  `c6f0cbe07a7681d3ecfd3447b8296e97cbf8042d6d962d825f6018d980d5396b`.
- font sample alternate-row fit gate: `0x1d868` calls
  `0x1cece(selected=0x44080418,row=1)`, snapshots `0x783132`, installs current
  context `0x4008004c` through `0x1c5e8`, and skips `0x1d8ba` when the flag is
  zero. With `0x783132 = 1`, `0x1d8ba` projects y from `0x00900000` to
  `0x00ce0000` using `744` subunits, takes row height `13`, and compares
  projected bottom `219` against `0x782db6`; limit `300` fits and equality at
  limit `219` returns D7=1 for continuation.
- font sample multi-probe preflight: `0x1dcf2` uses shared calculator
  `0x1dc38` to write a row-height word and project each candidate y. With
  `0x783132 = 0`, first `COURIER` y `0x00900000 -> 0x00ce0000` fits under
  limit `300` and returns D7=0 at `0x1de1a`; with `0x783132 = 1`, y
  `0x00900000 -> 0x00ce0000 -> 0x010c0000` fits under the same limit and
  returns D7=0 at `0x1dd8e`. Tightening the limit to `250` makes the second
  probe overrun, converts raw `0x1218` to reset y `0x01820000`, and the mode-1
  reset probe bottom `511` returns D7=1 at `0x1de24`; starting at y
  `0x01f40000` with limit `600` proves the reset mode-1 and mode-0 probes can
  both fit and return D7=0 at `0x1de16`.
- font sample carried run-2 render: buckets `3` and `4` now cross `0x1ed84` /
  `0x1ef6a` with wide destination stride `0x0180`; bucket 3 setup
  `{'dividend': 3, 'divisor_word_06': 5, 'remainder_783a22': 3,
  'band_rows_scaled_783a20': 32, 'destination_base_783a28': 1122304}`
  dispatches `2` compact objects with current row hash
  `823d26ff1ebdb3068224faa8dfc0679eef91cd959f1dd370d13f018eb21ce6a4` and
  fallback hashes
  `['973d6e26612036125768dcc697900e150e57899007ff846da320c457913e6d51',
  'd989877c1640e33f8036c4882d504a01a8f884945759d4b886d7ce132c23356b']`, while
  bucket 4 setup `{'dividend': 4, 'divisor_word_06': 5, 'remainder_783a22': 4,
  'band_rows_scaled_783a20': 16, 'destination_base_783a28': 1146880}`
  dispatches `1` compact object with current row hash
  `5e71581663bd2a7c363a866b8bea232fb69f0524e2046da47fd54375cb800796` and
  fallback hashes
  `['06dc84fbb9421397716b0bfccb9b807942ba9a29671436503c91813626d87d5f']`.
- font sample source heading composition: `0x1ca2c` source index `3` selects
  table pointer `0x01c180` / `b'INTERNAL FONTS'`, queues `14` heading bytes
  through current context `0x44080418`, advances y through `0x1cfb4` from
  `0x00200000` to `0x00520000`, then carries first `COURIER` row fields,
  sample run 1, and the `0x1d050` run-2 transition in one page-record state.
  The heading space byte takes the segmented page-record path into buckets
  `[64, 56, 48, 40, 32, 24, 16, 8, 0]`; the final carried state ends at cursor
  `0x08ac0000,0x00900000`, buckets `[0, 2, 3, 6, 7, 8, 16, 24, 32, 40, 48, 56,
  64]`, and object hashes `{0:
  ['000562ec9d99dd04162a1d392f4545ae0793543ceb4836894d3f9981127920f5',
  '834fc629b6ef04ae1fbfd2a8b3cc1bed7582f4092ed594dcbcfc6ad96eee2b6a',
  '9b4cb23e8e85c3375345d77427c756a886b335c19ae227a788e5f1bc55d68761'], 2:
  ['7da542b07d8a6ebcb7e3217e4f34c8501bee977e1a6e2dc57202140343f4acaa'], 3:
  ['dcffcb008bafa53a5b83d25b2145e9f5cd2260c3b261a22359e21bd6c2bd107a',
  '4f85ad44e7383d83c0928d5554787e723e3df01fef72a6c4e08dbb3fef3b3be5',
  'da206f0c59b13e293761e620449e67120b9f5f2406b26df92d2075224c9999a3',
  'd209c309618cd06853ecfa925c6b03666c32933077bab15ba6b731d42f926596',
  '4b57aacdd3e2b5448723b44dc0cbe21e5b2f4b37b65c49c647fe62f7cee2fc56'], 6:
  ['7993ed274ad3d0053a65ca7fa88df05cbacbbfd0446429a3d842fbc132ea42bf',
  'd7a682289aed990d6cd620d686d61567e683833a3074ee87db646f6b48c4dba2'], 7:
  ['36c988c7920bb1883215cec52f642e77b99d36df8c75504366375d4f7430ff91'], 8:
  ['16c1ca6c649bfc4fd834aa82a140cc4ac23b60ec5eccfc47c5bc32385c272ab9'], 16:
  ['c213c34ab7788be9b3ca370608a95adaf5371ec4ed4a9d9b03fb9896226c2f94'], 24:
  ['99d60f551df96fb2d09f5d51d044a686c712e2e799d4b8ac5fa0c5dbd8a56327'], 32:
  ['bcca01b3ba59d1dc291853ba175d7c69002bc84a0b58b6c2e9e6fc9b6c525f9d'], 40:
  ['bc48316110ac9ec9a80d457ea228da0a68b9ffbd3288cd2f9737c4206dc2a639'], 48:
  ['f46ab49d0956f87cfa38e065687296293337a1c0abdb629b515892a6195327ce'], 56:
  ['aceb54267b8db5717a1e01f26aa410114468c3ba27b32cc277303602132dfece'], 64:
  ['24119daa7a11d6f74569cef76eabd26b87f133cc1f53cfa5712937e09f637a42']}`.
- font sample first two resolved rows: mode-3 `0x1b50e` request indexes 1 and
  2 suppress current Roman-8 slot `0x782354` / record `0x00004c`, then select
  `0x782358` / record `0x000418` / word `0x0155` and `0x78235c` / record
  `0x000868` / word `0x0175`. The row-to-row `0x1d050` path resets x to line
  anchor, advances y from `0x00900000` to `0x00ce0000`, formats second row
  bytes `49 30 32 43 4f 55 52 49 45 52 31 30 31 32 31 31 55`, assigns
  page-record context slots `0x44080418, 0x44080868`, reaches buckets `[0, 2,
  3, 6, 7, 8, 10, 11, 14, 15, 16, 24, 32, 40, 48, 56, 64]`, and ends at cursor
  `0x08ac0000,0x010c0000`.
- font sample actual first internal rows: fast-probe request index 0 selects
  slot `0x782354` / record `0x00004c` / word `0x0115`; `0x1d198` falls through
  table `0x1c11a` and prints row bytes `49 30 30 4c 49 4e 45 20 50 52 49 4e 54
  45 52 31 30 31 32 38 55`. The actual source-heading composition uses context
  slots `0x4008004c, 0x44080418, 0x44080868`, then row-to-row `0x1d050`
  transitions reach y `0x00c90003` and `0x01450003`, buckets `[0, 2, 3, 4, 6,
  7, 10, 11, 13, 14, 15, 18, 21, 22, 23]`, and final cursor
  `0x08ac0000,0x01830003` after rows 0, 1, and 2.
- font sample first internal source group: `0x1c398..0x1c5d6` resolves request
  indexes `0..14`, emits `14` class-zero rows, rejects class-one request
  indexes `14`, writes source status byte `0x783f05 = 14`, and terminates on
  `class-mismatch-status-write` at request `14`. Duplicate Roman-8
  substitution requests `5,10` remain visible with words `0x0005,0x0005` but
  are not re-appended by `0x1c540..0x1c5c6`; final recent contexts are
  `0x4008004c,0x44080418,0x44080868,0x40080cb8,0x40089fb0,0x4408a37c,0x4408a7cc,0x4008ac1c,0x400942e4,0x440946b4,0x44094b08,0x40094f5c`,
  page context slots are
  `0x4008004c,0x44080418,0x44080868,0x40080cb8,0x40089fb0,0x4408a37c,0x4408a7cc,0x4008ac1c,0x400942e4,0x440946b4,0x44094b08,0x40094f5c`,
  and selected page buckets hash to `{26:
  ['ff3e5268a418ebbefac479fa3a8b0e67888a0eb2616a714cba28f1b17bcc8e22',
  '927de1122a9d5c999d3dfa20fbc50dc5f9b3dc1673f9ccac2a6cd5a62af5512d',
  'fb007a871c7a51f230ca582c7efccffa9d436722ad23780bab03321e51965edc'], 66:
  ['d7f57b392dbd795d5c30d6a9569840da70b98cf52b404202d3053716e44b9494',
  '075e6b1cccf3cf4c39b84d4011569edaa0e03eef7d5dfc87390f5cfe25160144',
  'bf1393aac19712dd35515243392e58ba8f7a999bede610a5a3403c88227c6a58'], 82:
  ['b83056921c998367d52967753da1255113861698e63d3b472f86031b473adfa0',
  '4890ee64cd679c3f7ebfb84d5c12f7c1c77e4bad23f58a60a086c3742171006e',
  '8ac0bb82defac1f8c63742cd0581f82c5c49a4680becd1b207cbf4ee6c331e62',
  '9ac3886848a4a56e72149b344a7dcb393014ea3a30ea6582f744af258974f822',
  '2f366dec728502f86198ad959382ad25a15048c38887d7f450153935d48d2a12'], 90:
  ['d3bdc2b00eec88c65cb0f84abcb92cf96710cf8fddc269e48b3833e67c22069f']}`.
- font sample internal class-one source group: `0x1e9a0` seeds current context
  `0x40099d18`; after request 0, `0x1c41a..0x1c428` reads prior source status
  `14` and resumes at request `14`; `0x1c398..0x1c5d6` emits `14` class-one
  rows from request indexes `0,16,17,18,19,20,21,22,23,24,25,26,27,28`,
  rejects class-zero request indexes `14,15`, writes source status byte
  `0x783f05 = 29`, and terminates on `resolver-miss` at request `29`.
  Duplicate Roman-8 substitution requests `20,25` remain visible with words
  `0x0005,0x0005`; final recent contexts are
  `0x40099d18,0x4409a0e4,0x4409a534,0x4009a984,0x400a3484,0x440a3850,0x440a3ca0,0x400a40f0,0x400ad4aa,0x440ad87a,0x440adcce,0x400ae122`,
  page context slots are
  `0x40099d18,0x4409a0e4,0x4409a534,0x4009a984,0x400a3484,0x440a3850,0x440a3ca0,0x400a40f0,0x400ad4aa,0x440ad87a,0x440adcce,0x400ae122`,
  and selected page buckets hash to `{26:
  ['84e5696094804a0fd2e163372062e0963856ea643dc906cfd090518d7abd9103',
  '8c29d34b2d90c8c0b17e4c743f55161b77dce636decc6d3a2068ff79152eaafd',
  'c93d0e8f38e269980cff1de455c2c35b6ab68a908f04160dbdf0713520cc7c20',
  '7fb9f404daea411957ef1af65d8c58454bd1dbdeb46539ec9444256730931682'], 66:
  ['601e7edcf3fe4dd9645c61037036489fba02f998c8f6c809dbfac3d127e8b44e',
  'eae524e7eec9f3562fdf034e1aa9abbb2e41da2b7159aa602f74261e7a506fd9'], 82:
  ['070dfaa7cb0a5629e676fc9c697e85348db84198189d32e055ebc3690bb6de3d'], 98:
  ['fbb3279e7a9945b2d86bcf6339e6de62d6d827a23db6e353fb9778a5b3080d97',
  'a3885003758f78b4310fcc487730156a8b29297f17098cc736757ff4c741ba66',
  '8b3a885ca0059f87fcb22f5cfd2f7f60f7dc5e34076364c997f181a3b270f5c1']}`.
- font sample non-internal source groups: source 0 uses mode 0 and emits no
  rows in either pass, writing `0x783f02 = 1`; sources 1 and 2 use modes 1 and
  2, each emit only the request-0 fast-probe row in each class pass
  (`L00`/`R00`) and write `0x783f03 = 1` / `0x783f04 = 1`. The class-one pass
  for each source reads the prior status byte through `0x1c41a..0x1c428`
  before terminating at request 1.
- font sample source-heading page records for sources 0..2: source 0 queues
  `b'"PERMANENT" SOFT FONTS'` as a heading-only page-record state with buckets
  `[0]`, counts `{0: 3}`, digest
  `89fb4143a293f80bb8c07bab86d5c94940ba73039f2bd9ba1e3de0c2c6c4fb4c`, and
  final cursor `0x00000000,0x00520000`; source 1 class-zero/class-one queue
  `b'L00LINE PRINTER10128U'` and `b'L00LINE PRINTER10128U'` with bucket
  digests `cc583ac71b083d3cf241a1a72ff6345e22d585a9eef1a0ba850427b6d43e2aba` /
  `51dade4f3a0af13cb533c9f62c5ea955a63f02046622e39a00b4ac8b072f63d6`; source 2
  class-zero/class-one queue `b'R00LINE PRINTER10128U'` and `b'R00LINE
  PRINTER10128U'` with bucket digests
  `eaf10ca6b5b5716170b313ce542df82a6974c1ac22ee0e87308dead7be22c6a1` /
  `3d23d5c6c5320d406d1db34523d3ad01c819d4e938e3dee4fa0a5d20747ed152`.
- font sample full-printout placement skeleton: `0x1c204` clears source status
  bytes, then `0x1c28e` runs class passes `[0, 1]`; each pass calls `0x1d76c`,
  `0x10084`, `0x1e9a0`, `0x1c9b8`, `0x1c916`, and `0x1cfb4` before sources
  `0..3`. The composed source/class segments emit row counts `[0, 1, 1, 14, 0,
  1, 1, 14]`, status writes `[(0, 0, 7880450, 1), (1, 0, 7880451, 1), (2, 0,
  7880452, 1), (3, 0, 7880453, 14), (0, 1, 7880450, 1), (1, 1, 7880451, 1),
  (2, 1, 7880452, 1), (3, 1, 7880453, 29)]`, bucket counts `[3, 13, 13, 142,
  3, 12, 12, 122]`, context-slot counts `[1, 1, 1, 12, 1, 1, 1, 12]`, and
  aggregate segment digest
  `f4105538bd1506731f04810ed2f50cce23815751c4f979ed6f60efab4cde08c7` for `32`
  total rows.
- font sample full-printout sample-run correlation: every emitted row in the
  eight source/class segments queues run-1 table `0x1c1cf` and run-2 table
  `0x1c1e9`; non-empty segment row counts are `[(1, 0, 1), (2, 0, 1), (3, 0,
  14), (1, 1, 1), (2, 1, 1), (3, 1, 14)]`, first/last printed rows are `[(1,
  0, b'L00LINE PRINTER10128U', b'L00LINE PRINTER10128U'), (2, 0, b'R00LINE
  PRINTER10128U', b'R00LINE PRINTER10128U'), (3, 0, b'I00LINE PRINTER10128U',
  b'I13LINE_PRINTER16.68.50N'), (1, 1, b'L00LINE PRINTER10128U', b'L00LINE
  PRINTER10128U'), (2, 1, b'R00LINE PRINTER10128U', b'R00LINE PRINTER10128U'),
  (3, 1, b'I00LINE PRINTER10128U', b'I28LINE_PRINTER16.68.50N')]`, all run
  event counts are `[25]` / `[25]`, direct isolated render hashes remain
  `{'run1_bucket_-1':
  'b6a0061f7de34c0fa1a0586263f3f167c84d95219e05437e74a286356409af37',
  'run1_bucket_0':
  'd7dfb89c8cff5e309b95aac43cd64e0f74f17db1dd9118253544343f17b4c1ce',
  'run2_bucket_-1':
  'c77bca7364adbda480c5a31fa4be469175c031bd5f14fc4a54a2e6fb09174be5',
  'run2_bucket_0':
  'b10556bfb02fbb6a2ffec2a82add396619bae3ace0ebab657113f4d3648c41b5'}`, and
  the aggregate correlation digest is
  `4f664dc44f9ad98cbe25d4bdead651a2902bec1f90367c650bb2d1352d6f3e8a`.
- font sample full-printout rendered surfaces: fixture `font sample full
  printout segments render through 0x1ed84 and 0x1ef6a` renders all eight
  source/class page-record segments through the bridge and band renderer.
  Segment
  `(source,class,row_count,render_buckets,rendered_rows,max_width,digest)`
  values are `[(0, 0, 0, 1, 33, 656,
  '105c04604475622eb5b4511ca69b95634bd2d9c5ddefcb0cb07e12ef45b234d1'), (1, 0,
  1, 6, 210, 2219,
  '1e99e81ad52be89b8551089ff87d6852ec69bb3f5d61fa0fbb1d01b94f88541f'), (2, 0,
  1, 6, 210, 2219,
  '940ec458086cb0917da3c2de65b52d2bfec0e57f1d334e8f5ba83946c9739419'), (3, 0,
  14, 65, 2012, 2219,
  'dd7e19b1aa077ccb794e73051e68c54e11e335ffcd110e92dc01b39132c638af'), (0, 1,
  0, 1, 33, 4083,
  '9a71cdb0b6f8b1365d439119b2b8e1d3d4b3b6a720f729ac94065edef5ba4d2f'), (1, 1,
  1, 5, 146, 4097,
  '018cdd48ede556dc439d5c5434f775aa7a10dd38321b4645e697542a9c7b825e'), (2, 1,
  1, 5, 146, 4097,
  '76b22e4a81d534146a094b0f432909cbb5623d333d29cd373a63e7adb600f786'), (3, 1,
  14, 50, 1257, 4097,
  '3bffa7214d9a478ec5fb5fd47ccb3458e9079daea12d77443437dd9ff11b4224')]`; total
  rendered bucket rows `4047`, aggregate surface digest
  `5e5e735b4fb2a2a4dff4794099a02eaf23fa2dd3e469df8d053db88a321ea6f2`.
- font sample row fields: first `LINE_PRINTER` record `0x0146b4` emits
  printable bytes `49 30 37 4c 49 4e 45 5f 50 52 49 4e 54 45 52 31 36 2e 36 38
  2e 35 31 30 55`, with prefix `I07`, name `LINE_PRINTER`, pitch `16.6`,
  height `8.5`, symbol `10U`, `3` fixed-space calls through `0xd0f0`, and `8`
  explicit horizontal units through `0x1d152`; the height value is rounded by
  the mode-1 `0x1cc6e` add-five path.
- active candidate windows: `0x1569c` selects class-zero pointer
  `0x782354`/count `12` when `0x782da3 == 0`, or class-one pointer
  `0x782324`/count `12` otherwise; selected entries receive active bit
  `0x80000000` before later filtering.
- active symbol filter: `0x156de` keeps only matching active entries, clears
  rejected active bits, moves `0x78287c` to the first survivor, and shrinks
  `0x7827b8`; class-zero primary `0x0115` keeps slots `0x782354, 0x782364,
  0x782374`/records `0x00004c, 0x009fb0, 0x0142e4`, while parser-derived `ESC
  )1234U` word `0x9a55` misses every class-one candidate and falls through to
  fallback-table word `0x000e`, keeping slots `0x782330, 0x782340, 0x782350`.
- remembered secondary visible output: fixture `remembered secondary symbol
  feeds visible SO page-record rows` starts from parser-derived `ESC )1234U`
  word `0x9a55`, rejects requested candidates through `0x156de`, then uses
  remembered secondary word `0x000e`; the first remembered probe is slot
  `0x782324` / record `0x019d18`, the first remembered match is slot
  `0x782330` / record `0x01a984`, `0x144d2` selects context `0xc00ae122`, SO
  handler `0x0c6b8` selects slot 1, object prefix `00 00 00 00 00 01 00 02 00
  c9 00 00 cb 01`, and row digest
  `b8ee0f8dd3e6ed70afa219bc00605d75249ae047a67fb67189693057d7936e6c`.
- live non-Roman symbol-set selection: fixture `live parser symbol-set streams
  select non-Roman built-ins` drives primary streams through parser handlers
  `0x11eb6`, `0x1201e`, and `0x120be`, then through `0x13eb8`/`0x14c64`.
  `(label, stream, requested word, survivor records, chosen record, dispatch)`
  values are `[('0N', '1b 28 30 4e', 14, [3256, 44060, 85852], 3256,
  'selected-symbol-not-roman8:0021-00ff@0x782f32'), ('10U', '1b 28 31 30 55',
  341, [1048, 41852, 83636], 1048,
  'selected-symbol-not-roman8:0001-00ff@0x782f32'), ('11U', '1b 28 31 31 55',
  373, [2152, 42956, 84744], 2152,
  'selected-symbol-not-roman8:0001-00ff@0x782f32')]`, proving `0N`, `10U`, and
  `11U` select distinct built-in records and use the
  `selected-symbol-not-roman8` map path rather than `0x14f16` Roman-8
  patching.
- active candidate chooser: `0x14398` seeds the first active slot and calls
  `0x13c06` for each later active slot; resource class is compared first, then
  same-class built-ins use `0x1428c` to compare decoded height, byte `+0x2f`,
  signed byte `+0x30`, and byte `+0x31`. For class-zero Roman-8 survivors,
  this selects slot `0x782364` / record `0x009fb0` because tuple `[1200, 0, 3,
  3]` beats the first survivor and the later 16.66-pitch survivor.
- full `0x13eb8` refresh: parsed primary `0p10h12v0s0b3T` follows calls
  `0x148f8, 0x1569c, 0x156de, 0x153c6, 0x1519a, 0x147b2, 0x14758, 0x14398,
  0x144d2, 0x14c64`; symbol, spacing/pitch, and height filters leave slots
  `0x782354, 0x782364`, `0x14758` stroke filtering keeps slot `0x782354` /
  record `0x00004c`, `0x144d2` writes current-font context `0x782ee6`, and
  `0x14c64` rebuilds map `0x782f32` with patch `unchanged`.
- secondary `0x13eb8` refresh: parsed `0p16h8v0s0b0T` follows calls `0x148f8,
  0x1569c, 0x156de, 0x153c6, 0x14398, 0x144d2, 0x14c64`; symbol filter keeps
  slots `0x782330, 0x782340, 0x782350`, nearest-pitch `0x153c6` keeps slot
  `0x782350` / record `0x02e122`, `0x144d2` writes context `0x782ef6`, and
  `0x14c64` rebuilds secondary map `0x783032` with patch
  `selected-symbol-not-roman8`.
- inline font-selection streams: primary bytes `1b 28 73 30 70 31 30 68 31 32
  76 30 73 30 62 33 54 21 21` write context `0xc008004c`, derive HMI `30`,
  queue object `00 00 00 00 00 00 00 02 00 6a 00 00 68 02`, and match pinned
  Courier rows; secondary bytes `1b 29 73 30 70 31 36 68 38 76 30 73 30 62 30
  54 0e 21 21` write context `0xc00ae122`, SO selects slot `1`, derives HMI
  `18`, queues object `00 00 00 00 00 01 00 02 00 c9 00 00 cb 01`, and match
  pinned secondary rows.
- non-Roman visible symbol streams: fixture `non-Roman symbol streams select
  visible built-ins` composes `ESC (0N`/`10U`/`11U` and `ESC )0N`/`10U`/`11U`
  with their matching font-selection command and printable `!!` tail. `(case,
  selected context, mapped byte, glyph entry, object prefix, rendered-row
  sha256)` values are `[('primary-0N', '0xc0080cb8', '0x00', '0x001088', '00
  00 00 00 00 00 00 02 00 6a 00 00 68 02',
  '8b36cfd64d818c0982b172982156f8be9687388c9679cd83538c9d1098d9bb2c'),
  ('secondary-0N', '0xc00ae122', '0x00', '0x02e4f6', '00 00 00 00 00 01 00 02
  00 c9 00 00 cb 01',
  'b8ee0f8dd3e6ed70afa219bc00605d75249ae047a67fb67189693057d7936e6c'),
  ('primary-10U', '0xc4080418', '0x20', '0x001088', '00 00 00 00 00 00 00 02
  20 6a 00 20 68 02',
  '8b36cfd64d818c0982b172982156f8be9687388c9679cd83538c9d1098d9bb2c'),
  ('secondary-10U', '0xc40ad87a', '0x20', '0x02e4f6', '00 00 00 00 00 01 00 02
  20 c9 00 20 cb 01',
  'b8ee0f8dd3e6ed70afa219bc00605d75249ae047a67fb67189693057d7936e6c'),
  ('primary-11U', '0xc4080868', '0x20', '0x001088', '00 00 00 00 00 00 00 02
  20 6a 00 20 68 02',
  '8b36cfd64d818c0982b172982156f8be9687388c9679cd83538c9d1098d9bb2c'),
  ('secondary-11U', '0xc40adcce', '0x20', '0x02e4f6', '00 00 00 00 00 01 00 02
  20 c9 00 20 cb 01',
  'b8ee0f8dd3e6ed70afa219bc00605d75249ae047a67fb67189693057d7936e6c')]`; the
  secondary cases also cross SO handler `0xc6b8` before rendering from context
  slot 1.
- `0x13eb8` exits: the transient `0x78298f` path stores selected longword
  `0xc008004c`, restores saved active word `0x9999`, and skips
  `0x144d2`/`0x14c64`; the `0x148f8` cache-hit path returns after calls
  `0x148f8` with active symbols `[4369, 8738]`.
- `0x13eb8` preserved visible output: fixture `0x13eb8 no-dispatch exits keep
  prior visible rows` appends printable tails to both no-dispatch exits. The
  transient path selects `0xc008004c` into `0x782992` but following `!!`
  renders prior context `0xc0089fb0`, object `00 00 00 00 00 00 00 02 00 89 00
  00 87 02`, digest
  `73cbb28bfab786807b9a3186eb3946efae550cde2e5448f0549f88ebf8c8a631`; the
  cache-hit secondary path returns after `0x148f8`, crosses SO, and renders
  prior context `0xc40ad87a`, object `00 00 00 00 00 01 00 02 20 c9 00 20 cb
  01`, digest
  `b8ee0f8dd3e6ed70afa219bc00605d75249ae047a67fb67189693057d7936e6c`.
- selected font dispatch: `0x14c64` cache-miss handling for that selected
  built-in record updates primary range table `0x783134` to `0x0021..0x007e`,
  selected flag `0x783132 = 1`, rebuilds map `0x782f32` through `0x14d9c`,
  applies active symbol `0x0005` through `roman-extension` handling, and
  snapshots state at `0x783148` through `0x1440c`.
- selected inline/downloaded dispatch: `0x14c64` bit-30-clear cache-miss
  handling writes selected record byte `+0x0e` to flag register `0x783132 =
  1`, rebuilds map `0x782f32` through `0x14e24`/`0x14eb6` with extended-half
  probing `True`, applies active symbol `0x0115` through `unchanged` handling,
  and snapshots inline state byte `+8 = 1` at `0x783148` through `0x1440c`.
- font-ID selection: `0x17708` now has executable success paths for bit-30
  built-in and bit-30-clear inline/downloaded candidates. The built-in path
  scans current id `0x0007`, resolves candidate slot `0x782364`, accepts
  record byte `+0x20 = 0xff`, reuses page-root slot `2` through `0xc4fc`,
  writes active word `0x0115` through `0x15890`, and then enters `0x14c64`;
  the inline path scans id `0x1234`, resolves slot `0x782900`, accepts byte
  `+0x16 = 0x00`, writes active word `0x0115` through `0x158be`, and
  dispatches the secondary map at `0x783032`.
- font-ID non-selected exits: fixture `0x17708 font-ID non-selected exits
  preserve prior selection` pins four terminal helper statuses before map
  dispatch: scan miss status `scan-miss` after `0x172c0` status `1`,
  candidate-slot miss for payload `0x089fb0` with selected pointer `0`, class
  mismatch at pointer `0x782364` with record class `0xff` versus wanted
  `0x00`, and page-root context-full status `context-full` after `0xc4fc`
  returns `0x11`; all four restore `0x782f2e = 0x2222` and do not call
  `0x14c64`.
- font-ID preserved visible output: fixture `font-ID non-selected exits keep
  prior visible rows` carries host-fetched stream `ESC (7X!!` through the same
  parser record, applies those four non-selected `0x17708` terminal states,
  then renders the printable `!!` tail from prior context `0xc008004c` with
  object prefix `00 00 00 00 00 00 00 02 00 6a 00 00 68 02` and rendered-row
  digest `8b36cfd64d818c0982b172982156f8be9687388c9679cd83538c9d1098d9bb2c`;
  fixture `font-ID secondary non-selected exits keep prior SO visible rows`
  carries `ESC )8X SO !!` through the slot-1 non-selected states, then renders
  from prior secondary context `0xc40ad87a` with object prefix `00 00 00 00 00
  01 00 02 20 c9 00 20 cb 01` and digest
  `b8ee0f8dd3e6ed70afa219bc00605d75249ae047a67fb67189693057d7936e6c`.
- font-ID visible selection: fixture `font-ID built-in selection feeds visible
  page-record rows` carries host-fetched stream `ESC (7X!!` through `0xa904`,
  parser handlers `0x11eb6` / `0x1201e` / `0x120be`, `0x17708` selected
  context `0xc0089fb0`, printable `0xd04a` rows, object prefix `00 00 00 00 00
  00 00 02 00 89 00 00 87 02`, and rendered-row digest
  `73cbb28bfab786807b9a3186eb3946efae550cde2e5448f0549f88ebf8c8a631`.
- font-ID secondary built-in visible selection: fixture `font-ID secondary
  built-in selection feeds visible SO page-record rows` carries host-fetched
  stream `ESC )8X SO !!` through `0xa904`, parser handlers `0x11eb6` /
  `0x12008` / `0x120be`, `0x17708` selected context `0xc00ae122`, existing
  page-root slot `1`, SO handler `0xc6b8`, object prefix `00 00 00 00 00 01 00
  02 00 c9 00 00 cb 01`, and rendered-row digest
  `b8ee0f8dd3e6ed70afa219bc00605d75249ae047a67fb67189693057d7936e6c`.
- font-ID primary inline/downloaded visible selection: fixture `font-ID
  primary inline/downloaded selection feeds visible page-record rows` carries
  host-fetched stream `ESC (4660X!` through `0xa904`, parser handlers
  `0x11eb6` / `0x1201e` / `0x120be`, `0x17708` selected context `0x00000100`,
  page-root context slot `0`, printable `0xd04a`, object prefix `00 00 00 00
  00 00 00 01 01 66 01 00 00 00`, and rendered-row digest
  `e0c6cbbf133aaaf522868ef7f28856f06b0d54b4dd9368a090fe7c85e7b1d563`.
- font-ID secondary inline/downloaded visible selection: fixture `font-ID
  inline/downloaded selection feeds visible page-record rows` carries
  host-fetched stream `ESC )4660X SO !` through `0xa904`, parser handlers
  `0x11eb6` / `0x12008` / `0x120be`, `0x17708` selected context `0x00000100`,
  page-root context slot `1`, SO handler `0xc6b8`, printable `0xd04a`, object
  prefix `00 00 00 00 00 01 00 01 01 66 01 00 00 00`, and rendered-row digest
  `e0c6cbbf133aaaf522868ef7f28856f06b0d54b4dd9368a090fe7c85e7b1d563`.
- height filter: `0x1519a` reads primary/secondary requested height from
  `0x782ef2`/`0x782f02`, keeps active candidates in requested +/- `0x19` when
  possible, otherwise uses `0x1533e` to select nearest lower/upper heights;
  class-zero requested `0x04b0` keeps `8` slots `0x782354, 0x782358, 0x78235c,
  0x782360, 0x782364, 0x782368, 0x78236c, 0x782370`, while requested `0x0384`
  falls back to nearest height `0x0352` and keeps `4` slots `0x782374,
  0x782378, 0x78237c, 0x782380`.
- spacing/pitch filter: `0x153c6` first probes/prunes spacing from
  primary/secondary `0x782eef`/`0x782eff` against built-in `+0x21`, then
  filters pitch from `0x782ef0`/`0x782f00` through `0x13b76`; class-zero
  spacing `0` and pitch `0x03e8` keeps `8` slots `0x782354, 0x782358,
  0x78235c, 0x782360, 0x782364, 0x782368, 0x78236c, 0x782370`, while pitch
  `0x04b0` falls forward through `0x1562c` to `0x0682` and keeps `4` slots
  `0x782374, 0x782378, 0x78237c, 0x782380`.
- default-font table builders: `0x1ac0a` current-candidate mode copies word
  `0x02c1` into all four `@0`/`@1` table slots, while synthesized mode writes
  `0x0115 / 0x0015 / 0x0055 / 0x0005`; `0x1af36` builds fallback slots `0x0115
  / 0x0015 / 0x0085 / 0x00a5` for the corresponding `0x156de`
  candidate-selection fallback.
- current-default lookup: `0x1b250` treats `0x78219c == 0xff` as disabled,
  otherwise asks `0x1b50e` for a resource address and symbol word, maps that
  low-24 address back into the canonical candidate slot list with `0x1b4c0`,
  stores the resolved slot in `0x7828a0`, copies the returned word to
  `0x7828a4`, and sets `0x78289f` to `1` only when the selected slot precedes
  boundary pointer `0x7827ac`.
- real built-in current-default lookup: real `0x1b50e` results feed `0x1b250`
  and map record `0x08004c` to slot `0x782354` with selector `0x78289f = 0`,
  while record `0x09a984` maps to slot `0x782330` before boundary `0x7827ac`
  with selector `0x78289f = 1`.
- current-default resolver: `0x1b50e` first accepts the `0x1b8ea` fast probe
  only for requested index `0`; otherwise it scans two list windows selected
  by mode `0`, `1`, `2`, or `3`. `0x1b750` classifies each candidate through
  `0x1b7b2` range/special/downloaded admissibility and `0x1b8b6` current
  Roman-8 duplicate suppression; non-special requests can count a Roman-8
  candidate twice, with the duplicate ordinal writing the requested word
  instead of `0x0115`.
- real built-in default resolver: mode-3 `0x1b50e` over scanned candidates
  selects slot `0x782354` / record `0x08004c` for ordinal 1, counts the same
  Roman-8 record twice when requested symbol is non-Roman-8 (`0x0005` on
  ordinal 2), and suppresses the current Roman-8 slot before selecting
  `0x782358`.
- synthesized default search: `0x1ab84` clears the selected candidate pointer,
  tries `0x1adaa(1)` and `0x1adaa(2)` under the current `0x78289f`, flips
  `0x78289f` only after both miss, repeats both range searches, and finally
  falls through to `0x1ae7e`; a flipped-orientation hit or miss leaves the
  flipped selector in place for the caller.
- real built-in synthesized default search: `0x1ab84` over scanned candidates
  flips orientation before fallback, then selects slot `0x782354` / record
  `0x08004c` by Roman-8 fallback for requested `0x0005` and slot `0x782330` /
  record `0x09a984` by exact `0x000e`.
- default-font candidate search: `0x1ad66` first tries `0x1adaa(1)` and then
  `0x1adaa(2)` before `0x1ae7e`; `0x1bbfe` now derives range-hit words through
  the bit-30-selected symbol readers, and `0x1b060` validates default
  candidates by orientation, pitch `0x03e8`, height `0x04b0`, style bytes,
  spacing byte `3`, and requested-symbol fallback rules. The fixture pins
  primary-slot range-1 word `0x0115`, secondary-slot range-2 word `0x0055`,
  fallback `0x1b060` requested word `0x0005`, and base-candidate reader
  sources `0x15890` / `0x158be`.
- real built-in default fallback: scanned class-zero candidates feed `0x1b060`
  and choose slot `0x782354` / record `0x08004c` by Roman-8 fallback for
  requested `0x0005`; scanned class-one candidates choose slot `0x782330` /
  record `0x09a984` by exact symbol `0x000e`.
- symbol-set special-case parser boundary: stream `1b 28 37 58 1b 29 30 40 1b
  28 31 40 1b 29 32 40 1b 28 33 40 1b 29 33 40` routes final `X` and `@`
  through terminal handler `0x120be`; the model keeps the previous requested
  word while calling font-id helper `0x17708` for `X`, sets `0x78287b`, enters
  `0xc580` with dirty flag `2`, reads the `0x1ac0a` default-symbol table for
  `@0`/`@1`, copies primary to secondary for `@2`, and uses the
  current-candidate default-font word for `@3`, ending with active words
  `0x02c1` / `0x02c1`.
- real default-table caller boundary: stream `1b 28 30 40 1b 29 30 40 1b 29 31
  40 1b 29 32 40 1b 28 33 40` routes through the same ROM `0x120be` terminal
  handler; real-backed table words `0x0005 / 0x000e / 0x0155 / 0x000e` drive
  `@0`, `@1`, `@2`, and `@3` requested words `0x0005 / 0x000e / 0x0005 /
  0x0005 / 0x000e`, ending active words `0x000e` / `0x0005`.
- real final-`@` visible streams: fixture `real final-@ default-table streams
  select visible built-ins` appends primary `ESC (s0p10h12v0s0b3T!!` and
  secondary `ESC )s0p16h8v0s0b0T SO !!` tails after the real-backed
  `@0`/`@1`/`@2`/`@3` caller stream. The final active words `0x000e` /
  `0x0005` select primary context `0xc0080cb8` and secondary context
  `0xc00ad4aa`, object prefixes `00 00 00 00 00 00 00 02 00 6a 00 00 68 02` /
  `00 00 00 00 00 01 00 02 00 c9 00 00 cb 01`, and row digests
  `8b36cfd64d818c0982b172982156f8be9687388c9679cd83538c9d1098d9bb2c` /
  `b8ee0f8dd3e6ed70afa219bc00605d75249ae047a67fb67189693057d7936e6c`.
- `ESC (2U` selects primary word `0x0055` and patches `LINE_PRINTER` map byte
  `0x24 -> 0xb9`; `ESC )0E` selects secondary word `0x0005` and copies
  upper-half map byte `0xa1 -> 0xa0` before clearing the upper half.
- source fields: context `0x440946b4`, glyph entry `0x015330`, width `4`, rows
  `22`, flag `1`, x `0`, y `0`, context slot `0`
- producer path: `short`, bucket index `0`, object size `0x26`, capacity `10`,
  entry size `3`
- object bytes: `00 00 00 00 00 00 00 01 20 00 00`
- payload bytes: `00 01 20 00 00`
- selector: `0x0000`, context slot `0`
- rendered entry: glyph `32`, coord `0x0000`, dest base `+0x00`, span `1`,
  helper `0x01fa5c`
- rendered rows:
`####`
`....`
`####`
`....`
`####`
`....`
`####`
`....`
`####`
`....`
`####`
`....`
`####`
`....`
`####`
`....`
`####`
`....`
`####`
`....`
`####`
`....`

## `0x1387c` Page-Record Compact Bucket Allocator Fixture

This fixture moves the short text bucket one step closer to the real page-root
shape. It models `0x10084` first-page-root allocation before the `0x1387c`
bucket path, as documented in
`generated/analysis/ic30_ic13_page_root_allocation.md`: a missing current root
can run the active-record wait hook, clears pending bytes
`0x782c73`/`0x782c72`, marks root byte `+4 = 1`, clears `0x782a70`, stores
`0x782a72 = root+0x20`, clears byte `0x782990`, initializes root fields
through `0x10110`, installs the selected current-font context into root slot
0, and zeros 256 bucket-head longwords through root `+0x1c`. The fixture also
pins that `0x782a76` is not seeded by `0x10084`; it remains unchanged until
the shared stream allocator creates/uses a chunk.
- `0x10110` geometry fields: root byte `+0x06` copies page code `0x06`, byte
  `+0x09` derives to `0x12`, and word `+0x16` derives to `0x0030` for the
  explicit geometry fixture.

- `0x10084` first allocation: created `True`, active-record wait `True`,
  stream remaining `0`, link pointer `0x000021`, next-free pointer unchanged
  `0x00cafe00`, bucket clear longwords `256`.
- existing-root `0x10084` call: created `False`, allocations `1`, current root
  `1 -> 1`.
- `0x1381c` stream allocator: first object size `0x26` returns `0x00d00004`,
  leaves `0x00d6` bytes, next size `0x28` reuses the chunk at `0x00d0002a`,
  and crossing size `0xf0` links chunk `0x00d00100` after `0x00d00000` with
  `0x000c` bytes left.
- selected context slot bootstrap: selector `1` copies source `0x782ef6` into
  root slot 0 as `0x440946b4` after clearing `16` context slots.

The `0x1387c` model indexes the page-root `+0x1c` bucket array by `0x782a7c`,
walks the bucket chain looking for the same selector word at object `+4`,
reuses that object when count `+6` is below the caller-supplied capacity, or
allocates and links a new object at the bucket head when the matching object
is full or missing.

- address-aware `0x1387c`: first allocation returns object `0x00d01004`, reuse
  returns the same object while count `0 < capacity`, and a full object forces
  new head `0x00d0102a` whose next pointer is the prior head `0x00d01004`.
- first allocation: allocated `True`, bucket `0`, selector `0x0000`, count `0
  -> 1`, coord `0x0000`
- second same-selector insertion: allocated `False`, chain index `0`, count `1
  -> 2`, coord `0x0001`
- reused object bytes: `00 00 00 00 00 00 00 02 20 00 00 20 00 01 00 00 00 00
  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00`
- full-object case: a prefilled count-10 object causes `0x1387c` to allocate a
  new head object while leaving the old object second in the chain.
- page-record queued rows:
`####............####`
`....................`
`####............####`
`....................`
`####............####`
`....................`
`####............####`
`....................`
`####............####`
`....................`
`####............####`
`....................`
`####............####`
`....................`
`####............####`
`....................`
`####............####`
`....................`
`####............####`
`....................`
`####............####`
`....................`

## `0x1edc6` Page-Record Bridge Fixture

This fixture models the render-record bridge at `0x1edc6` after a compact text
bucket has been queued under a page/control record through the `0x1387c` model
above. The firmware copies page-root `+0x1c` to render-record `+0x18`,
page-root `+0x24` to render-record `+0x1c`, page-root `+0x28` to render-record
`+0x20`, and the 16 font/context slots from page-root `+0x2c..+0x68` to
render-record `+0x24..+0x60`. It then normalizes the two rule/list chains
in-place before band rendering.

- bridged compact bucket root: `00 00 00 00 00 00 00 02 20 00 00 20 00 01 00
  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00`
- bridged context slots `[0..1]`: `0x440946b4`, `0x00000000`
- normalized `+0x24`/render `+0x1c` rule-list node: `00 00 00 00 00 13 00 00
  00 00 12 34 12 34`
- normalized `+0x28`/render `+0x20` fixed-list node: `00 00 00 00 00 14 00 00
  ab cd ab cd 01 08`
- render-record destination snapshot: source bucket `+0x1c` is visible at
  render `+0x18`, normalized rule list at render `+0x1c`, normalized fixed
  list at render `+0x20`, and context slot 0 at render `+0x24 = 0x440946b4`.
- active-record copy snapshot: source words `+0x18 = 0x1234` and `+0x1a =
  0x5678` become render words `+0x0a = 0x1234`, `+0x0c = 0x5678`, `+0x10 =
  0x1234`, `+0x16 = 0x1234`, with render `+0x0e` cleared before the queue/list
  bridge.
- `0x1ef86` render-band setup fixture divides `(word +0x10 + word +0x08 - word
  +0x0a) = 0x0014` by word `+0x06 = 6`, leaving remainder `2` in `0x783a22`,
  scaled rows `64` in `0x783a20`, and destination base `0x00101000` in
  `0x783a28` and render-record `+0x12`.
- `0x1efc2` bucket-chain dispatcher fixture indexes render bucket word `2` at
  slot offset `8` and dispatches object byte `+4` classes through ``compact ->
  0x01effe`, `segment-list -> 0x01f812`, `encoded-span -> 0x01f88e``.
- `0x1f812` segment-list fixture reads count `1` at object `+0x06`; entry 0
  decodes coord `0x1001`, row count `2`, width word `0x0025`, full words `2`,
  and trailing mask `0xf800` before filling rows through `0x1f862`.
- producer-shaped rectangle/rule fixtures: `0x13386`/`0x133aa` stores bucket
  byte `0x04`, key `0x5303`, width `0x0012`, and height `0x0034` before bridge
  byte `+5` becomes `0x17`; `0x137a2`/`0x136d2` stores key `0x1002` and extent
  `0x0044` before bridge byte `+5` becomes `0x16`.
- `0x1f756` fixed-width list fixture reads render-record `+0x20`, selector `6`
  -> pattern long `0xc000e000` from table `0x0308f6`, draws `3` rows through
  `0x1f7b0`, and leaves object bytes `00 00 00 00 00 06 10 02 00 03 ff b4 01
  08`.
- `ESC *c#A/#B` store positive dot dimensions directly; `ESC *c#H/#V` convert
  decipoints through five subunits per decipoint and round up before storing.
  The fixture pins `ESC *c72H` as `0x001e000b` and `ESC *c1.5V` as
  `0x00010007`.
- `ESC *c#G/#P` selector fixtures pin black fill selector `7`, gray-fill id
  `50` selector `4`, and landscape pattern id `2` selector `8`; the queued
  black rule object is `00 00 00 00 01 07 4a 00 00 0c 00 05 00 00` before
  bridge normalization.
- chained rectangle stream `1b 2a 63 31 32 61 35 62 30 50` queues the same
  selector-7 rule object through handlers `0x010e68, 0x010e22, 0x010898` and
  renders the same solid pixels after bridge normalization.
- ROM dispatch trace for the same stream walks parser modes `0 -> 1 -> 3 -> 16
  -> 16 -> 16 -> 0` through handlers `0x11eb6`, `0x11ec8`, `0x11eda`,
  `0x10e68`, `0x10e22`, and `0x10898`, then queues the bridged rule `00 00 00
  00 01 17 4a 00 00 0c 00 05 00 05`.
- `0x1f446` dispatches that bridged black rule to solid helper `0x01f596`; key
  `0x4a00` decodes to x `10`, y `20`, width `12`, rows `5`, and partial mask
  `0xfff0`.
- rendered black-rule visible rows:
`......................`
`..........############`
`..........############`
`..........############`
`..........############`
`..........############`
- band-crossing solid rule starts at y `78` with height `5`: first band draws
  `2` rows, leaves `3` rows in object `+0x0c`, and next band draws `3` rows
  from y `0`.
- band-crossing pattern rule uses selector `13`: first band starts at pattern
  row `14` with words `0xe007, 0xc003`, leaves `3` rows, and the next band
  resumes at pattern row `0` with words `0xc003, 0xe007, 0x700e`.
- page-band walk over bands `0,5` assembles page rows 76..83:
`................`
`................`
`###..........###`
`##............##`
`##............##`
`###..........###`
`.###........###.`
`................`
- gray selector `0` dispatches through pattern helper `0x01f4e0`; pattern base
  `0x02ff3e`, start `0x02ff3e`, first words `0x8080, 0x0000, 0x0000, 0x0000`,
  left mask `0xff00`, right mask `0x0000`.
- rendered gray-rule rows:
`#.......`
`........`
`........`
`........`
- full 16x16 non-solid selector matrix covers: selector 0 -> 0x02ff3e,
  selector 1 -> 0x02ffde, selector 2 -> 0x03007e, selector 3 -> 0x03011e,
  selector 4 -> 0x0301be, selector 5 -> 0x03025e, selector 6 -> 0x0302fe,
  selector 8 -> 0x03039e, selector 9 -> 0x03043e, selector 10 -> 0x0304de,
  selector 11 -> 0x03057e, selector 12 -> 0x03061e, selector 13 -> 0x0306be.
- sub-byte HP pattern fixture uses selector `13`, key `0x3500`, decoded x `5`,
  y `3`, width `19`, row-low `3`, pattern start `0x0306c4`, left mask
  `0x07ff`, right mask `0xff00`.
- rendered shifted HP-pattern rows:
`........................`
`........................`
`........................`
`.......###......###....#`
`........###....###......`
`.........###..###.......`
`..........######........`
`...........####.........`
`...........####.........`
- `0x10b80` clipping fixture starts at x `-3` with width `10`, queues x `0`
  width `7`, and emits object `00 00 00 00 00 07 40 00 00 07 00 05 00 00`.
- extended `0x10b80` clipping now also pins right-edge, top-edge, bottom-edge,
  and landscape right-edge queue coordinates plus horizontal-outside,
  vertical-outside, and empty-after-clip ignore reasons.
- `0x10d22` no-room retry fixture starts with an existing compact text bucket,
  marks retry flag `0x0001`, publishes that bucket through `0xff1e`, allocates
  a fresh root through `0x10084`, and retries the selector-7 rule object `00
  00 00 00 01 07 4a 00 00 0c 00 05 00 00`.
- rectangle parser-to-retry boundary: the same `ESC *c12a5b0P` parser trace
  reaches handlers `0x10e68`, `0x10e22`, and `0x10898`, then the no-room path
  publishes the existing compact text bucket before retrying and rendering
  that selector-7 rule object from a fresh root.
- bridged compact rows match the page-record queued rows above.
- a non-overlapping text+rule composition fixture renders compact text at x
  `16`, y `0` and a selector-7 solid rule at x `24`, y `24` from the same
  bridged render record, then composes them into one fixed 40-pixel band.
- text+rule composed sample rows:
`................####....................`
`........................................`
`................####....................`
`........................................`
`........................############....`
`........................############....`
`........................############....`
- a raster layer fixture renders a mode-0 row at x `0`, y `12` through its own
  `0x1edc6` raster bridge, then composes it with the text+rule band.
- text+rule+raster composed row 12: `##....##..####..####....................`
- a synthetic `0x1ef6a` render-entry fixture now executes call order `0x01ef86
  -> 0x01efc2 -> 0x01f446 -> 0x01f756`, selecting compact text and encoded
  raster bucket objects through `0x1efc2`, then composing the `0x1f446` rule
  list and `0x1f756` fixed-width list; composed row 1:
  `................................###.............`.
- a `0x1ef6a` page-band walk now merges compact text, a mode-0 raster row, and
  a crossing patterned rule across bands `0` and `5`, carrying the mutated
  rule node into the second band.
- a published text+rule+raster fixture now snapshots the full bucket array,
  rule list, and context slots through modeled `0xff1e`, then renders that
  published record through `0x1ed84` and `0x1ef6a` with the same rows.
- remaining gap: the parser-produced heterogeneous page-object path is covered
  by the later addressed text/rule/raster fixtures; what remains here is byte
  streams that expose new page-object shapes and final device-output
  validation.

## Parser-Derived Raster State Fixture

This fixture models the raster state fields written by `ESC *t#R` handler
`0x10808` and `ESC *r#A` handler `0x1075a` before the existing `0x13070`
row-object queue path. It is still a state model rather than a full parser run
through `0x121cc` / `0x105d0`, but the encoded raster mode comes from the
resolution command threshold instead of being hand-picked.

| Parameter | Encoded mode | Scale word | Limit for extent 255 |
| ---: | ---: | ---: | ---: |
| `300` | `0` | `1` | `32` |
| `150` | `1` | `2` | `16` |
| `100` | `2` | `3` | `11` |
| `75` | `3` | `4` | `8` |

- `ESC *r1A` with orientation `0` seeds raster origin from `0x782c8a`, while
  orientation `1` seeds from `0x782c8e`.
The executable axis fixture pins portrait origin word `17`, landscape origin
word `43`, and left-edge parameter `0` origin word `0`.
- `ESC *r0A` starts at the left edge, giving origin `0`, baseline word `0`,
mode `0`, scale `1`, and limit `32` for extent `255`.
- `ESC *rB` handler `0x107fa` clears only the raster active byte, leaving
origin/baseline/mode/scale/limit/row counters untouched in this state fixture.
- parser-derived transfer object bytes: `00 00 00 00 80 00 00 04 00 01 f0 0f
  aa 55`
- `0x105d0` transfer gate fixture: row beyond extent drains `4` bytes before
  `0x10084`, negative row drains `4` bytes after root ensure and count stores,
  and byte count `4` with limit `2` queues only `2` bytes as object `00 00 00
  00 80 00 00 02 00 01 f0 0f`, recording overflow `2`.
- parser-derived rendered row:
`................####........#####.#.#.#..#.#.#.#`
- remaining gap: the later host-fetched raster fixtures cover parser dispatch,
  delayed-record restore, queued objects, and render rows; remaining raster
  work should expose new `0x121cc` / `0x105d0` gate outcomes, object fields,
  or rendered rows.

## ROM Parser Dispatch Trace Fixture

This fixture walks the primary raster stream through the ROM dispatch table
used by main parser loop `0x11774`. It proves the byte sequence reaches prefix
handlers `0x11eb6` / `0x11ec8` / `0x11eda`, final handlers `0x10808`,
`0x1075a`, and `0x11f82`, then returns to mode 0 where `0x12218` restores the
delayed `ESC *b4W` record and dispatches handler `0x105d0` before payload
bytes are consumed. A paired cross-boundary check now ties that parser trace
to the modeled command/data stream: the restored record, payload offset,
page-root allocation, queued raster object, `0x1edc6` bridge, rendered row,
and final row counter all match for the same byte stream. The same primary
stream is also fetched byte-for-byte through the modeled `0xa904` ring source
before reaching the parser/object/render boundary. A second parser-to-gate
edge check uses the `ESC *t300R` / `ESC *r0A` / `ESC *b4W` stream to prove the
same ROM parser handlers and `0x105d0` restore feed capped queueing,
page-extent queueing, beyond-extent drain/no-row-advance, and negative-row
drain/advance outcomes; that edge stream is now also fetched through the
modeled `0xa904` ring source.

- dispatch stream bytes: `1b 2a 74 33 30 30 52 1b 2a 72 31 41 1b 2a 62 34 57
  f0 0f aa 55`
- dispatch path:
- offset `0`, table `0x010eae`, byte `0x1b`, mode `0 -> 1`, handler `0x011eb6`
- offset `1`, table `0x010f20`, byte `0x2a`, mode `1 -> 3`, handler `0x011ec8`
- offset `2`, table `0x010f44`, byte `0x74`, mode `3 -> 15`, handler
  `0x011eda`
- offset `6`, table `0x0111f0`, byte `0x52`, mode `15 -> 0`, handler
  `0x010808`
- offset `7`, table `0x010eae`, byte `0x1b`, mode `0 -> 1`, handler `0x011eb6`
- offset `8`, table `0x010f20`, byte `0x2a`, mode `1 -> 3`, handler `0x011ec8`
- offset `9`, table `0x010f50`, byte `0x72`, mode `3 -> 7`, handler `0x011eda`
- offset `11`, table `0x011070`, byte `0x41`, mode `7 -> 0`, handler
  `0x01075a`
- offset `12`, table `0x010eae`, byte `0x1b`, mode `0 -> 1`, handler
  `0x011eb6`
- offset `13`, table `0x010f20`, byte `0x2a`, mode `1 -> 3`, handler
  `0x011ec8`
- offset `14`, table `0x010f62`, byte `0x62`, mode `3 -> 14`, handler
  `0x011eda`
- offset `16`, table `0x0111e4`, byte `0x57`, mode `14 -> 0`, handler
  `0x011f82`
- command records:
- `1b 2a 74 33 30 30 52`: record `80 52 01 2c 00 00`, final handler
  `0x010808`, restore `None`, payload offset `None`, payload ``
- `1b 2a 72 31 41`: record `80 41 00 01 00 00`, final handler `0x01075a`,
  restore `None`, payload offset `None`, payload ``
- `1b 2a 62 34 57`: record `80 57 00 04 00 00`, final handler `0x011f82`,
  restore `{'kind': 'direct-handler', 'handler': 67024}`, payload offset `17`,
  payload `f0 0f aa 55`

## Modeled Raster Command/Data Stream Fixture

This fixture starts from actual PCL command bytes, then models the delayed
payload boundary that `0x121cc` records for handler `0x105d0`. It is still not
a full parser-produced page-object run, but the primary stream is now paired
with the ROM dispatch trace above, and each transfer event carries the
six-byte parsed record, the exact `0x121cc` snapshot bytes, and the `0x12218`
restore/dispatch result before routing the restored payload through the
modeled `0x105d0` gate. Queued transfers now carry the modeled `0x10084`
page-root allocation record before `0x13070`/`0x13250` link the raster object.
The 300/150/100/75-dpi streams pin byte-stream-selected modes 0..3, and the
150/100/75-dpi streams now start from the modeled `0xa904` ring source before
reaching the same parser/restore/render boundary. The capped stream proves the
parser/data fixture consumes the full restored byte count while queueing only
the gate-accepted byte count. The page-extent boundary stream still queues at
`row_y == page_extent` and advances to the next row. The beyond-extent stream
drains payload bytes without queueing or advancing the modeled row state,
while the negative-row stream stores the capped count/overflow pair, ensures a
root, drains without queueing, and advances the modeled row state to zero.
Same-group lowercase-final sequences now stay in the firmware parser mode
until the final uppercase command byte.

- stream bytes: `1b 2a 74 33 30 30 52 1b 2a 72 31 41 1b 2a 62 34 57 f0 0f aa
  55`
- parsed events:
- `ESC *t300R`: mode `0`, scale `1`, limit `32`
- `ESC *r1A`: origin `0x00100000`, baseline word `16`, limit `30`
- `ESC *b4W`: parsed record `80 57 00 04 00 00`, delayed snapshot `01 00 01 05
  d0 80 57 00 04 00 00`.
Restore dispatch `{'kind': 'direct-handler', 'handler': 67024}`, payload
offset `17`, payload `f0 0f aa 55`. Gate `queued` stores `4`/overflows `0`,
row advance `True`, transfer state `{'x': 16, 'y': 0, 'byte_count': 4, 'mode':
0}`.
- queued object bytes: `00 00 00 00 80 00 00 04 00 01 f0 0f aa 55`
- rendered stream row:
`................####........#####.#.#.#..#.#.#.#`
- bridged command-stream page object survives `0x1edc6` and renders the same
  row.
- primary raster transfer page-root allocation: created `True`, current root
  after `1`.
Allocation count `1`, bucket clear longwords `256`.
- host-fetched raster stream bytes: `1b 2a 74 33 30 30 52 1b 2a 72 31 41 1b 2a
  62 34 57 f0 0f aa 55`.
Fetched through `0xa904` ring source before queueing object `00 00 00 00 80 00
00 04 00 01 f0 0f aa 55` and rendering
`['................####........#####.#.#.#..#.#.#.#']`.
- host-fetched raster payload control normalization: raw payload `f0 1a 58 aa
  55` becomes queued payload `f0 00 aa 55`.
Ring bytes `22`, control hits `1`, queued object `00 00 00 00 80 00 00 04 00
00 f0 00 aa 55`, rendered `['####............#.#.#.#..#.#.#.#']`.
- capped stream through `0x105d0`: byte count `4`, limit `2`, stored `2`.
Overflow `2`, object `00 00 00 00 80 00 00 02 00 00 f0 0f`.
- page-extent boundary stream through `0x105d0`: y `15`, queued `True`, row
  after `16`.
Object `00 00 00 00 80 00 00 02 f0 00 f0 0f`, final rendered row
`####........####`.
- beyond-extent stream through `0x105d0`: drained `4`, queued `False`.
Row advance `False`, row after `20`, object length `0`.
- negative-row stream through `0x105d0`: drained `4`, queued `False`.
Stored `2`, overflow `2`, limit `2`. Row advance `True`, row after `0`, object
length `0`.
- raster parser-to-gate edge boundary: the same `ESC *t300R` / `ESC *r0A` /
`ESC *b4W` parser trace reaches handlers `0x10808`, `0x1075a`, and `0x11f82`,
restores handler `0x105d0`, then the capped fixture stores only the first two
payload bytes, the page-extent fixture queues y `15` then advances to `16`,
the beyond-extent fixture drains all four bytes without advancing `row_y`, and
the negative-row fixture stores the capped count/overflow pair, drains all
four bytes, and advances `row_y` from `-1` to `0`.
- host-fetched raster gate edge: the same edge stream drains `21` bytes from
  `0xa904` before matching the capped object `00 00 00 00 80 00 00 02 00 00 f0
  0f`, extent-boundary object `00 00 00 00 80 00 00 02 f0 00 f0 0f`,
  beyond-extent drain `4`, and negative-row drain `4`.
- lower-resolution parser boundary: `ESC *t150R`, `ESC *t100R`, and `ESC
  *t75R` streams now drain from the modeled `0xa904` ring source, pass through
  the ROM `0x11774` parser table to handlers `0x10808`, `0x1075a`, and
  `0x11f82`, match the modeled payload offset and queued mode object, then
  cross `0x1ed84`/`0x1ef6a` with encoded modes 1, 2, and 3.
- `mode-1` parser records `80 52 00 96 00 00; 80 41 00 00 00 00; 80 57 00 02
  00 00`, payload offset `17`, queued object `00 00 00 00 80 01 00 02 00 00 f0
  0f`
- `mode-2` parser records `80 52 00 64 00 00; 80 41 00 00 00 00; 80 57 00 02
  00 00`, payload offset `17`, queued object `00 00 00 00 80 02 00 02 00 00 f0
  0f`
- `mode-3` parser records `80 52 00 4b 00 00; 80 41 00 00 00 00; 80 57 00 02
  00 00`, payload offset `16`, queued object `00 00 00 00 80 03 00 02 00 00 f0
  0f`
- multi-row parser boundary: the host-fetched stream with two consecutive
  uppercase `ESC *b2W` commands restores independent `80 57 00 02 00 00`
  records, consumes payloads at offsets `17` and `24`, advances modeled
  `row_y` to `2`, and queues page-record objects at coords `0x0000` and
  `0x1000`.
- host-fetched chained transfer boundary: `ESC *b2w2W` keeps parser mode in
  the `*b` family after lowercase `w`, preserves delayed record `80 77 00 02
  00 00`, restores that same record at uppercase `W`, and consumes payload
  bytes only after offset `19`.
- raster render-entry boundary: the host-fetched multi-row and
  chained-transfer bucket arrays now cross `0x1ed84` active-record copy and
  `0x1ef6a`; multi-row dispatch entries `2`, chained-transfer dispatch entries
  `1`, rows `['####........####', '....########....']` /
  `['####........####']`.

- mode-1 stream bytes: `1b 2a 74 31 35 30 52 1b 2a 72 30 41 1b 2a 62 32 57 f0
  0f`
- mode-1 parsed events:
- `ESC *t150R`: mode `1`, scale `2`, limit `16`
- `ESC *r0A`: origin `0x00000000`, baseline word `0`, limit `16`
- `ESC *b2W`: delayed handler `0x0105d0`, payload offset `17`, payload `f0
  0f`, transfer state `{'x': 0, 'y': 0, 'byte_count': 2, 'mode': 1}`
- mode-1 queued object bytes: `00 00 00 00 80 01 00 02 00 00 f0 0f`
- mode-1 rendered stream rows:
`########................########`
`########................########`

- mode-2 stream bytes: `1b 2a 74 31 30 30 52 1b 2a 72 30 41 1b 2a 62 32 57 f0
  0f`
- mode-2 parsed events:
- `ESC *t100R`: mode `2`, scale `3`, limit `11`
- `ESC *r0A`: origin `0x00000000`, baseline word `0`, limit `11`
- `ESC *b2W`: delayed handler `0x0105d0`, payload offset `17`, payload `f0
  0f`, transfer state `{'x': 0, 'y': 0, 'byte_count': 2, 'mode': 2}`
- mode-2 queued object bytes: `00 00 00 00 80 02 00 02 00 00 f0 0f`
- mode-2 rendered stream rows:
`############................############........`
`############................############........`
`############................############........`

- mode-3 stream bytes: `1b 2a 74 37 35 52 1b 2a 72 30 41 1b 2a 62 32 57 f0 0f`
- mode-3 parsed events:
- `ESC *t75R`: mode `3`, scale `4`, limit `8`
- `ESC *r0A`: origin `0x00000000`, baseline word `0`, limit `8`
- `ESC *b2W`: delayed handler `0x0105d0`, payload offset `16`, payload `f0
  0f`, transfer state `{'x': 0, 'y': 0, 'byte_count': 2, 'mode': 3}`
- mode-3 queued object bytes: `00 00 00 00 80 03 00 02 00 00 f0 0f`
- mode-3 rendered stream rows:
`################................................################`
`################................................################`
`################................................################`
`################................................################`

- multi-row stream bytes: `1b 2a 74 33 30 30 52 1b 2a 72 30 41 1b 2a 62 32 57
  f0 0f 1b 2a 62 32 57 0f f0`
- multi-row transfer events:
- payload offset `17`, payload `f0 0f`, transfer state `{'x': 0, 'y': 0,
  'byte_count': 2, 'mode': 0}`, row_y after `1`
- payload offset `24`, payload `0f f0`, transfer state `{'x': 0, 'y': 1,
  'byte_count': 2, 'mode': 0}`, row_y after `2`
- multi-row queued chain, newest first:
`00 00 00 00 80 00 00 02 10 00 0f f0` `00 00 00 00 80 00 00 02 00 00 f0 0f`
- multi-row rendered rows, source order:
- coord `0x0000`, y `0`, payload `f0 0f`
`####........####`
- coord `0x1000`, y `1`, payload `0f f0`
`................`
`....########....`

- raster-end stream bytes: `1b 2a 74 33 30 30 52 1b 2a 72 30 41 1b 2a 62 32 57
  f0 0f 1b 2a 72 42 1b 2a 74 31 35 30 52`
- raster-end parsed events:
- `ESC *t300R`: mode `3 -> 0`, scale `1`, limit `32`
- `ESC *r0A`: active `0 -> 1`, origin `0x00000000`, baseline word `0`, limit
  `32`
- `ESC *b2W`: payload offset `17`, payload `f0 0f`, transfer state `{'x': 0,
  'y': 0, 'byte_count': 2, 'mode': 0}`, row_y after `1`
- `ESC *rB`: active `1 -> 0`, mode `0`, scale `1`, limit `32`, row_y `1`
- `ESC *t150R`: mode `0 -> 1`, scale `2`, limit `16`
- host-fetched raster-end parser handlers: `0x10808, 0x1075a, 0x11f82,
  0x107fa, 0x10808`.
The `ESC *b2W` record restores `0x105d0`, then `ESC *rB` clears active state
before `ESC *t150R` updates mode/scale again.
- raster-end final state: active `0`, mode `1`, scale `2`, limit `16`, row_y
  `1`
- active-resolution stream bytes: `1b 2a 74 33 30 30 52 1b 2a 72 30 41 1b 2a
  74 37 35 52 1b 2a 62 32 57 f0 0f`
- host-fetched active-resolution parser handlers: `0x10808, 0x1075a, 0x10808,
  0x11f82`.
Active `ESC *t75R` leaves mode `0 -> 0`, scale `1`, and limit `32`. The
following `ESC *b2W` queues mode `0` object `00 00 00 00 80 00 00 02 00 00 f0
0f` and renders `['####........####']`.
- chained resolution stream bytes: `1b 2a 74 33 30 30 72 31 35 30 52`
- host-fetched chained resolution events: `b'\x1b*t300r'` then `b'150R'`,
  leaving mode `1` / scale `2`.
- chained `ESC *b` stream bytes: `1b 2a 74 33 30 30 52 1b 2a 72 30 41 1b 2a 62
  32 77 32 57 f0 0f`
- chained `ESC *b` transfer events:
- sequence `b'\x1b*b2w'` records delayed snapshot `01 00 01 05 d0 80 77 00 02
  00 00` and remains in parser mode for the uppercase terminator.
- sequence `b'2W'`, payload offset `19`, payload `f0 0f`, row_y after `1`,
  chained `False`
- chained `ESC *b` queued chain, newest first:
`00 00 00 00 80 00 00 02 00 00 f0 0f`
- remaining gap: the same command family now has host-fetched
  parser/data-chain fixtures for lower-resolution modes, consecutive
  transfers, active-resolution ignore, and lowercase `*b` chaining; remaining
  recognizer work is new command-family byte streams that change parser state
  or raster output.

## Raster Row Page-Record Fixture

This fixture models one byte-aligned raster row through the page-object path
used by `0x105d0`: `0x13070` computes the bucket/key fields from the raster
state, `0x13250` allocates and links an encoded-span object under page-root
`+0x1c`, `0x138de` copies host payload bytes into object `+0x0a`, and
`0x1f88e` mode 0 renders the literal row after the `0x1edc6` bridge copies the
bucket root into render-record `+0x18`.

- raster state: x `16`, y `0`, byte count `4`, mode `0`, payload `f0 0f aa 55`
- queued raster object bytes: `00 00 00 00 80 00 00 04 00 01 f0 0f aa 55`
- object fields: class `0x80`, mode byte `0x00`, byte count `4`, coord
  `0x0001`, bucket `0`, key `0x0001`
- rendered mode-0 literal row:
`................####........#####.#.#.#..#.#.#.#`
- bridged raster rows match the queued raster object render.
- non-byte-aligned mode-0 queued raster object bytes: `00 00 00 00 80 00 00 02
  04 01 c3 3c`
- rendered sub-byte shifted mode-0 row:
`....................##....##..####..`
- mode-1 queued raster object bytes: `00 00 00 00 80 01 00 02 00 01 f0 0f`
- rendered mode-1 expanded rows:
`................########................########`
`................########................########`
- mode-2 queued raster object bytes: `00 00 00 00 80 02 00 02 00 01 f0 0f`
- rendered mode-2 expanded rows:
`................############................############........`
`................############................############........`
`................############................############........`
- non-byte-aligned mode-2 queued raster object bytes: `00 00 00 00 80 02 00 02
  04 01 f0 0f`
- rendered sub-byte shifted mode-2 rows:
`....................############................############........`
`....................############................############........`
`....................############................############........`
- band-clipped mode-2 queued raster object bytes: `00 00 00 00 80 02 00 02 f0
  01 f0 0f`
- band-clipped mode-2 current-band rows: `1`, remaining after band: `2`
- band-clipped mode-2 visible row:
`................############................############........`
- band-clipped mode-2 fallback rows:
`................############................############........`
`................############................############........`
- mode-3 queued raster object bytes: `00 00 00 00 80 03 00 02 00 01 f0 0f`
- rendered mode-3 expanded rows:
- row 0:
  `................################................................`
  `################`
- row 1:
  `................################................................`
  `################`
- row 2:
  `................################................................`
  `################`
- row 3:
  `................################................................`
  `################`
- remaining gap: parser/data-chain handoff is fixture-backed through restored
  records, queued objects, and render rows; remaining work is new `0x121cc` /
  `0x105d0` gate outcomes, encoded object fields, or rendered rows.

## `0xd824` Positioned Text Bucket Fixture

This fixture models the flagged/built-in positioning handoff at `0xd824`
before running the same `0x12f2e` producer model. With `LINE_PRINTER` host
byte `0x21`, source x-offset `0`, cursor x `10`, cursor y `21`, orientation
`0`, and printable offset `0`, the real glyph-entry words at `0x015330` add x
offset `6` and subtract y offset `21`; `0xd824` therefore writes source
coordinates `x=16`, `y=0`, context slot `0`, then `0x12f2e` emits compact
coord `0x0001`.

- positioned source: x `16`, y `0`, context slot `0`, overflow correction `0`
- glyph offsets: x `6`, y `21`
- object bytes: `00 00 00 00 00 00 00 01 20 00 01`
- payload bytes: `00 01 20 00 01`
- rendered entry: glyph `32`, coord `0x0001`, dest base `+0x02`, span `1`,
  helper `0x01fa5c`
- rendered rows:
`................####`
`....................`
`................####`
`....................`
`................####`
`....................`
`................####`
`....................`
`................####`
`....................`
`................####`
`....................`
`................####`
`....................`
`................####`
`....................`
`................####`
`....................`
`................####`
`....................`
`................####`
`....................`

The same model also exercises the negative-left overflow branch. With cursor x
`10` and source x-offset `-26`, `0xd824` sees `cursor_x + source_x_offset =
-16`, returns overflow correction `0x00100000`, rewrites the working cursor to
`26`, then adds the glyph x offset `6` to queue source x `32`. That produces
compact coord `0x0002`, still byte-aligned for the current renderer fixture.

- overflow positioned source: x `32`, y `0`, context slot `0`, overflow
  correction `0x00100000`
- overflow object bytes: `00 00 00 00 00 00 00 01 20 00 02`
- overflow payload bytes: `00 01 20 00 02`
- overflow rendered entry: glyph `32`, coord `0x0002`, dest base `+0x04`, span
  `1`, helper `0x01fa5c`
- overflow rendered rows:
`................................####`
`....................................`
`................................####`
`....................................`
`................................####`
`....................................`
`................................####`
`....................................`
`................................####`
`....................................`
`................................####`
`....................................`
`................................####`
`....................................`
`................................####`
`....................................`
`................................####`
`....................................`
`................................####`
`....................................`
`................................####`
`....................................`

## Single Printable Byte Stream Fixture

This fixture starts one step earlier than the producer-modeled text bucket:
the host byte stream is `21` (`!`). Under the documented normal parser
conditions, that byte reaches `0xd04a`, enters `0x1393a`, maps through the
active `LINE_PRINTER` character map to glyph byte `0x20`, takes the
flagged/built-in `0xd824` path with cursor `(10,21)`, emits the same short
`0x12f2e` compact object as the positioned fixture, and renders through
`0x1effe` / `0x1f034`. The adjacent printable-entry normalization fixtures now
pin the `0xd04a` over-`0xff` and high-bit branches: a nonzero `0xd99a` result
exits before source build, a zero result substitutes host `0x7f` and builds
glyph `0x7e`, primary high byte `0xa1` masks to host `0x21` while wrapping the
source build with `0xc6b8`/`0xc68a`, either high-character flag preserves
`0xa1` as glyph `0xa0`, and selected secondary slot masks without the primary
wrapper. The paired precheck fixture now pins `0xd28a` and `0xd6bc` result
semantics before the queue handoff: ordinary success returns `0`, horizontal
overflow with wrap disabled returns `1` and suppresses queueing, the same
overflow with `0x783190` set calls `0xf054` and retries from recovered x `0`,
and vertical-extent failure returns `1` on both source classes. The paired
text queue retry fixture now pins the short-object no-room path for both
`0xd3b2` and `0xd824`: a failed addressed `0x12f2e` allocation sets page-root
retry flag `+0x14.0`, publishes the old compact bucket through `0xff1e`,
ensures a fresh root through `0x10084`, retries the preserved source at
`0x00d06004`, and renders rows matching the published bucket through
`0x1effe`. The paired segmented retry fixture extends that no-room contract to
tall objects: unflagged rows `0x81` retry bucket words `9` and `1`, while the
flagged tall built-in space glyph retries all nine bucket indexes `0..64`;
selected published and retried buckets render matching rows through `0x1effe`.

- stream bytes: `21`
- source object from `0x1393a`: context `0x440946b4`, host `0x21`, mapped
  glyph `0x20`, glyph entry `0x015330`, flag `1`
- compact object bytes: `00 00 00 00 00 00 00 01 20 00 01`
- rendered rows match the `0xd824` positioned text fixture above.
- remaining gap: parser-produced page objects are covered by the adjacent
  printable/control stream fixtures; remaining source/bucket work is new
  source fields, bucket shapes, retry behavior, or visible row output.

## Two Printable Byte Stream Fixture

This fixture keeps the same normal printable path but repeats it for stream
bytes `21 21` (`!!`). Between bytes it models the simple `0xd550`
default-advance branch: alternate metrics and previous-width centering are
disabled, the drawable source is present, precheck succeeds, and the packed
cursor is advanced by `0x00100000` so both compact coordinates stay
byte-aligned for the current renderer fixture.

- stream bytes: `21 21`
- cursor advances: `0x000a0000` -> `0x001a0000` -> `0x002a0000`
- combined compact object bytes: `00 00 00 00 00 00 00 02 20 00 01 20 00 02`
- compact entries: glyph `0x20` at coords `0x0001` and `0x0002`
- rendered rows:
`................####............####`
`....................................`
`................####............####`
`....................................`
`................####............####`
`....................................`
`................####............####`
`....................................`
`................####............####`
`....................................`
`................####............####`
`....................................`
`................####............####`
`....................................`
`................####............####`
`....................................`
`................####............####`
`....................................`
`................####............####`
`....................................`
`................####............####`
`....................................`
- this byte-aligned advance is a renderer control fixture; it is not the
  initialized `LINE_PRINTER` HMI.

The initialized `LINE_PRINTER` built-in metric path follows the `0x10550`
conversion branch used by current-font refresh code: resource longword
`0x00480000` at context offset `+0x24` becomes HMI/default advance
`0x00120000`. Reusing the same `!!` stream with that advance queues the second
glyph at compact coord `0x0202`; renderer helper `0x1f3d4` decodes that as
byte base `+0x04` plus `$a001 = 0x12`, so the fixture draws the second glyph
at pixel x `34`.

- metric source: context `0x440946b4`, resource base `0x0146b4`, byte `+0x21 =
  0x00`, long `+0x24 = 0x00480000`
- `0x10550` result: `0x00120000`
- real-HMI compact object bytes: `00 00 00 00 00 00 00 02 20 00 01 20 02 02`
- real-HMI compact entries: glyph `0x20` at coords `0x0001` and `0x0202`
- real-HMI rendered rows:
`................####..............####`
`......................................`
`................####..............####`
`......................................`
`................####..............####`
`......................................`
`................####..............####`
`......................................`
`................####..............####`
`......................................`
`................####..............####`
`......................................`
`................####..............####`
`......................................`
`................####..............####`
`......................................`
`................####..............####`
`......................................`
`................####..............####`
`......................................`
`................####..............####`
`......................................`
- plain parser-to-page-record boundary: stream `21 21` routes both printable
  bytes through `0xd04a`, allocates one page-record root, reuses bucket `0`,
  and renders the same real-HMI rows after the `0x1edc6` bridge.
- HMI parser-to-page-record boundary: stream `1b 26 6b 36 48 21 21` routes
  `ESC &k6H` through handler `0xca8c`, stores packed HMI `15`, then queues two
  printable `!` bytes through `0xd04a` at compact coords `0x0600` and `0x0501`
  before rendering the bridged rows with 15-pixel spacing.
- SI/SO parser-to-page-record boundary: stream `21 0e 21 0f 21` routes `SO`
  through `0xc6b8` and `SI` through `0xc68a`; SO switches `0x782f06` to
  secondary context slot `1`, SI switches it back to primary slot `0`, and the
  page-record chain renders selector-1 and selector-0 compact objects from
  context slots `0x44094b08` and `0x440946b4`.
- transparent parser-to-page-record boundary: stream `1b 26 70 32 58 21 21`
  routes `ESC &p2X` through handler `0x11f5a`, restores delayed handler
  `0x12452`, consumes the following two payload bytes through `0xa904`, queues
  both bytes through `0xd04a` into the same compact coords `0x0001` and
  `0x0202`, and renders the same real-HMI rows after the `0x1edc6` bridge.
- display-functions parser-to-page-record boundary: stream `1b 59 21 05 21 1b
  5a` routes normal-table `ESC Y` through handler `0x12536`, consumes values
  `21 05 21 1b 5a` through the `0xa904` loop before terminating, sends `0x05`
  and terminating `ESC` through `0xd0f0`, queues visible `!`, `!`, and `Z`
  entries at compact coords `0x0001`, `0x0403`, and `0x0405`, and renders row
  digest `c7d0fb0a66181acd591244aab0a7f450f895b3b89ea98d189a00a25c3de04d85`.
- display-functions filter-on boundary: stream `1b 59 05 80 1a 58 21 1b 5a`
  sets selected-context byte `1` and high-control filter `1`, normalizes `1a
  58` to `7f`, routes values `05 80 7f 21 1b 5a` through `0xd04a`, queues six
  compact entries with prefix `00 00 00 00 00 00 00 06 04 0b 00 7f 0e 01 7e 1f
  02 20 06 04 1a 53 05 59 06 06`, and renders row digest
  `1cdd8203b43944801ec8d1d01c6ab4fa3808fc1f81a7ebfa4d04452369193b63`.
- display-functions alternate append boundary: stream payload `21 1a 58 1b 5a`
  through `0x12120` appends literal `ESC Y` plus normalized values `21 7f 1b
  5a` through `0xe002`, terminates after appended `ESC Z`, and stores payload
  `1b 59 21 7f 1b 5a` in macro chunk `0x783988`.
- transparent control-payload boundary: stream `1b 26 70 34 58 21 05 85 21`
  routes `0x21` bytes through `0xd04a` and default-filtered payload bytes
  `0x05` and `0x85` through `0xd0f0`; the fixed-space route maps host byte
  `0x20` to glyph `0x1f`, clears the glyph pointer before `0xd550`, advances
  cursor spacing without queuing text objects, and leaves the two visible
  entries at compact coords `0x0001` and `0x0604`.
- transparent unflagged fixed-record boundary: stream `1b 26 70 33 58 21 05
  21` routes C0 payload `0x05` through `0xd0f0`, substitutes host byte `0x20`,
  enters `0xd140`/`0xd3b2`, queues unflagged glyph `0` at compact coord
  `0x4802` between surrounding unflagged `!` coords `0x7601` and `0x7a03`,
  bridges context slot `0x00000100`, and renders bucket digest
  `89629435e063529ce7150d603ed9be37a74658317db3e97a4ae01b1c8d64f9d9`.
- transparent nonzero-filter boundary: stream `1b 26 70 34 58 21 05 80 21`
  sets selected context byte `1` and local filtering word `1`, so C0 payload
  `0x05` and high-control payload `0x80` both route through `0xd04a`, map to
  glyphs `0x04` and `0x7f`, and queue visible compact coords `0x0d01` and
  `0x0003`.
- transparent high-control interior samples: payload bytes `0x81`, `0x88`,
  `0x90`, and `0x97` all route as `d04a d04a d04a`, map to glyphs `0x80`,
  `0x87`, `0x8f`, and `0x96`, queue the high-control glyph in bucket `-1`, and
  leave the surrounding `!` bytes in bucket `0`.
- transparent high-control upper-bound boundary: stream `1b 26 70 33 58 21 9f
  21` keeps selected context byte `1` and local filtering word `1`, so payload
  byte `0x9f` routes through `0xd04a`, maps to glyph `0x9e`, uses glyph entry
  `0x016d1e`, queues compact coord `0xee01` in bucket `-1`, and renders
  selected bucket digest
  `ec0f944207561c1b9c9139749c3e37d122aebf53e2a50849dd8703416545c719`.
- transparent secondary segmented render prefix: `SO ESC &p3X!\x80!` builds
  157 nonempty buckets and the current model renders buckets `0..448` (57
  buckets) with aggregate digest
  `292eafb8b558bd36ca0caa5caa2771976c0e611456ac0b610ec8916b9d1f03f9`; bucket
  `456` then fails at glyph `0x5f` segment `0x39`, row skip `7296`, source
  `0x03fe22`, needing `1280` bytes with `478` available.
- transparent secondary segment-57 continuation hypotheses: the verified
  resource bytes determine the current-band digest
  `f0c1127f9e6b203f9829ab43f159b89c3f7dda687a47d4c09971077eac55c96e`; source
  window `0x0bfe22..0x0c0321` has 478 verified suffix bytes (sha256
  `e0a0fd34ce7a39f79ecd27c0ee288631554a0ff78359b72e27ea6087651bcf1f`) and
  needs 802 bytes after firmware address `0x0c0000`, where
  mirror/code-pair/zero-fill continuation sources hash to
  `e435e3b9d033e491b57282a88b0f321aa5fecae8128fa060844cc01379349563`,
  `90934acf59d9e8519c9149dc5df228f8fec2bff8451427be265489be967cdd16`, and
  `359f38eef400e2fa3924a3258652e74ee19cd46cb92e47bce91f1194fce25e9e` and make
  fallback digests diverge as
  `75cc8b60cd33f5c659ad702530ebacdc7685f2b75d63e18b9ce055383153f142`,
  `dc58960aff83e718df147897de51944939626c4e8422a53da5443bca48a53df5`, and
  `6373cecdf5f20d78b01abe5aa65c051d82ddef345b7cf7fe1504f93c9cb2c425`.
- transparent `1a` probe boundary: stream `1b 26 70 32 58 1a 41 21` keeps byte
  count `2` but consumes raw payload `1a 41 21`; because the probe byte is not
  `0x58`, routed values are `0x41` and `0x21`, which render visible `A!`.

A first mixed printable/control stream fixture now drives `ESC &k1G`,
printable `!`, CR, then printable `!` through one pass. The `ESC &k1G` byte
stream stores line-termination mode `0x80`; CR therefore resets x to the left
margin and also applies LF/VMI before the second printable byte is positioned.
With left margin `5`, VMI `3`, and initialized `LINE_PRINTER` HMI
`0x00120000`, the second glyph queues at source `(11,3)` / compact coord
`0x3b00`, decoded by `0x1f3d4` as `$a001 = 0x1b`.

- mixed stream bytes: `1b 26 6b 31 47 21 0d 21`
- mixed compact object bytes: `00 00 00 00 00 00 00 02 20 00 01 20 3b 00`
- mixed compact entries: glyph `0x20` at coords `0x0001` and `0x3b00`
- mixed final cursor: x `0x00170000`, y `0x00180000`, page roots `1`, span
  flushes `1`
- mixed rendered rows:
`................####`
`....................`
`................####`
`...........####.....`
`...................#`
`...........####.....`
`...................#`
`...........####.....`
`...................#`
`...........####.....`
`...................#`
`...........####.....`
`...................#`
`...........####.....`
`...................#`
`...........####.....`
`...................#`
`...........####.....`
`...................#`
`...........####.....`
`...................#`
`...........####.....`
`....................`
`...........####.....`
`....................`
- note: the shifted second glyph writes a full one-byte span, so its blank
  rows clear pixels `x=11..18` and can erase part of an earlier glyph in the
  same bucket.

The same mixed stream is now also queued through the page-record allocator
shape as the stream is processed, rather than being combined after the fact.
The first printable byte allocates bucket `0` through `0x1387c`; after CR+LF,
the second printable byte reuses that object and increments the count to `2`.
Bridging the resulting full `0x26` object through `0x1edc6` renders the same
post-CR rows.

- page-record stream object bytes: `00 00 00 00 00 00 00 02 20 00 01 20 3b 00
  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00`
- page-record bridged context slots `[0..1]`: `0x440946b4`, `0x00000000`
- mixed parser-to-page-record boundary: the same stream routes through
  handlers `0xedf8`, `0xd04a`, `0xf02c`, and `0xd04a`, allocates one
  page-record root, reuses bucket `0`, and renders the same bridged rows.
- LF parser-to-page-record boundary: stream `1b 26 6b 32 47 21 0a 21` routes
  `ESC &k2G` through handler `0xedf8`, the first printable `!` through
  `0xd04a`, LF through `0xf08c`, and the second printable `!` through
  `0xd04a`; LF applies CR+LF before the second glyph, queueing compact coord
  `0x3b00` and rendering the same post-CR rows.
- HT/BS parser-to-page-record boundary: stream `1b 26 6b 30 47 09 08 21`
  routes `ESC &k0G` through handler `0xedf8`, HT through `0xf1cc`, BS through
  `0xf2a8`, and printable `!` through `0xd04a`; HT advances the cursor to x
  `21`, BS backs it up to x `20`, then the bridged glyph queues at compact
  coord `0x0a01` and renders at pixel x `26`.
- margin parser-to-page-record boundary: stream `1b 26 61 31 4c 21` routes
  `ESC &a1L` through handler `0xeb58`, moves the cursor/left margin to one
  initialized `LINE_PRINTER` HMI column, then queues printable `!` through
  `0xd04a` at compact coord `0x0801` and renders the bridged glyph at pixel x
  `24`.
- right-margin parser-to-page-record boundary: stream `1b 26 61 31 4d 21`
  routes `ESC &a1M` through handler `0xec0c`, moves the cursor/right margin
  left to two initialized `LINE_PRINTER` HMI columns, then queues printable
  `!` through `0xd04a` at compact coord `0x0a02` and renders the bridged glyph
  at pixel x `42`.
- chained-margin parser-to-page-record boundary: stream `1b 26 61 36 6c 39 4d
  21` routes lowercase-final `ESC &a6l` through handler `0xeb58`, keeps parser
  mode `12` for `9M` through handler `0xec0c`, then queues printable `!`
  through `0xd04a` at compact coord `0x0207` and renders the bridged glyph at
  pixel x `114`.
- cursor-position parser-to-page-record boundary: stream `1b 26 61 32 43 21`
  routes `ESC &a2C` through handler `0xf39e`, moves the cursor to two
  initialized `LINE_PRINTER` HMI columns, then queues printable `!` through
  `0xd04a` at compact coord `0x0a02` and renders the bridged glyph at pixel x
  `42`.
- horizontal-decipoint parser-to-page-record boundary: stream `1b 26 61 37 32
  48 21` routes `ESC &a72H` through handler `0xf416`, converts 72 decipoints
  into 30 packed cursor units, then queues printable `!` through `0xd04a` at
  compact coord `0x0402` and renders the bridged glyph at pixel x `36`.
- vertical cursor-position parser-to-page-record boundary: stream `1b 26 61 31
  52 21` routes `ESC &a1R` through handler `0xf560`, moves the vertical cursor
  to one initialized VMI row plus firmware absolute-row bias, then queues
  printable `!` through `0xd04a` at compact coord `0x1001` in bucket `4` and
  renders the bridged glyph with one blank row before the glyph body.
- vertical-decipoint parser-to-page-record boundary: stream `1b 26 61 37 32 56
  21` routes `ESC &a72V` through handler `0xf60a`, converts 72 decipoints into
  packed vertical cursor y `30`, then queues printable `!` through `0xd04a` at
  compact coord `0x9001` in bucket `0` and renders the bridged glyph after
  nine blank rows.
- dot-position parser-to-page-record boundary: stream `1b 2a 70 33 30 78 33 30
  59 21` routes lowercase-final `ESC *p30x` through handler `0xf48c`, keeps
  parser mode `18` for `30Y` through handler `0xf692`, then queues printable
  `!` through `0xd04a` at compact coord `0x9402` and renders the bridged glyph
  after nine blank rows.
- chained cursor-position parser-to-page-record boundary: stream `1b 26 61 32
  63 2b 31 52 21` routes lowercase-final `ESC &a2c` through handler `0xf39e`,
  keeps parser mode `12` for relative `+1R` through handler `0xf560`, then
  queues printable `!` through `0xd04a` at compact coord `0x1a02` in bucket
  `3` and renders the bridged glyph after one blank row.
- vertical-layout parser-to-page-record boundary: stream `1b 26 6c 33 45 21`
  routes `ESC &l3E` through handler `0xece2`, refreshes the pending vertical
  cursor from top margin row 3, then queues printable `!` through `0xd04a` at
  compact coord `0x9001` in bucket `6` and renders the bridged glyph with nine
  blank rows before the glyph body.
- perforation-skip parser-to-page-record boundary: stream `1b 26 6c 31 4c 21`
  routes `ESC &l1L` through handler `0xee64`, sets byte `0x783191`, then
  queues printable `!` through `0xd04a` at compact coord `0x0001` and renders
  the bridged glyph at the original origin.
- cursor-stack parser-to-page-record boundary: stream `1b 26 66 30 53 1b 26 61
  32 43 1b 26 66 31 53 21` routes `ESC &f0S`, `ESC &a2C`, and `ESC &f1S`
  through handlers `0xf75e`, `0xf39e`, and `0xf75e`; the pop restores the
  original cursor before printable `!` queues through `0xd04a` at compact
  coord `0x0001` and renders the bridged glyph at the original origin.

A ROM parser trace now anchors the publication streams before the modeled
page-record layer: `21 1b 45` routes printable `!` through the mode-0 `0xd04a`
branch and `ESC E` through handler `0xcc52`; `1b 26 6b 32 47 21 0c` routes
`ESC &k2G` through handler `0xedf8`, printable `!` through `0xd04a`, and FF
through handler `0xf0f0`; `21 1b 26 6c 31 41`, `21 1b 26 6c 31 4f`, `21 1b 26
6c 32 48`, and `21 1b 26 6c 32 58 0c` route printable `!` through `0xd04a`
before page-size `ESC &l1A` reaches `0xfc74`, orientation `ESC &l1O` reaches
`0x10220`, paper-source `ESC &l2H` reaches `0xef62`, and copies `ESC &l2X`
reaches `0xeef0` before FF reaches `0xf0f0`. The publication-boundary fixture
ties those parser handler sequences to the modeled page-record side for the
same six byte streams: each allocates one root on printable `!`, publishes one
compact bucket through `0xff1e`, clears the current root, and renders the
published rows after the `0x1edc6` bridge. A host-fetch publication fixture
now starts those same reset, FF, page-size, orientation, paper-source, and
copies streams from the modeled `0xa904` ring source, drains all input bytes
from the ring, replays the same parser handlers, and lands on the same
published compact rows. The copies stream also proves `0xeef0` stores the
absolute clamped copy count in `0x782da4`, which `0xff1e` copies to published
header word `+0x0c`. The reset, FF, page-size, orientation, paper-source, and
copies publication streams now also have addressed allocation variants: `! ESC
E`, `ESC &k2G! FF`, `! ESC &l1A`, `! ESC &l1O`, `! ESC &l2H`, and `! ESC &l2X
FF` queue printable `!` through addressed `0x1387c`/`0x1381c`, materialize the
compact bucket record, publish through their `0xff1e` boundaries, and render
through `0x1ed84`/`0x1ef6a` with the same rows. The addressed paper-source
fixture also pins `0xef62` side effects after publication: selected value
`0x80`, `0x782da6 = 0x80`, `0x782998 = 1`, cursor x/y packed `5`/`92.1`, and
paper-source output/control bytes `0x780e8f = 0x80` and `0x780e26 = 1`. The
addressed copies fixture pins `0xeef0` storing copy count `2` in `0x782da4`,
then the trailing FF publishes a pool record with header word `+0x0c = 2`. The
published-record render-entry fixture then carries each of those six `0xff1e`
records through `0x1ed84` active-record copy and the `0x1ef6a` call order,
selecting the compact bucket through `0x1efc2` and rendering the same rows. A
host-fetched direct text/control fixture now starts the plain,
transparent-data, CR/LF, HT/BS, margin, cursor-position, dot-position,
vertical-layout, and cursor-stack page-record streams from the modeled
`0xa904` ring source, drains every byte, replays the same parser handlers or
delayed payload handler, and lands on the same `0x1387c` page-record objects.
The cursor-row case now also carries the nonzero bucket word through
`0x1ef86`, clips compact text to `0x783a20 = 16` current-band rows, and
records the continuation rows in the fallback buffer.
- validation-failure visible output: eight `ESC )s#W` no-install streams fail
  entries `[2, 4, 5, 5, 6, 6, 7, 5]`; the short-budget `ESC )s8W` case
  restores record `80 57 00 08 00 00` and fails entry `5` after `8` bytes,
  then the following printable `!` routes to handler `0x0d04a`, queues the
  default-font object `00 00 00 00 00 00 00 01 20 00 01 00 00 00 00 00 00 00
  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00`, and produces
  the baseline ROM-derived rows/object in every case.
- downloaded-character no-install visible recovery/publication: cases
  `['allocation_failure', 'mode_reject', 'range_reject']` return reasons
  `{'allocation_failure': 'allocation-failed', 'mode_reject':
  'unsupported-record-shape', 'range_reject': 'char-outside-header-type'}`,
  drain rejected payload bytes `{'allocation_failure': [222, 173, 190, 239,
  202, 254], 'mode_reject': [240, 15, 170, 85, 60, 195], 'range_reject': [240,
  15, 170, 85, 60, 195]}` through `0x12328`, leave following printable `!` on
  handler `0x0d04a`, queue the same default-font object `00 00 00 00 00 00 00
  01 20 00 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  00 00 00 00 00 00`, then trailing FF reaches handler `0x0f0f0`, publishes
  bucket `0` through `0xff1e`, and matches baseline rows/object `True`.
The same direct page-record group now crosses `0x1ed84` active-record copy and
the `0x1ef6a` render-entry call order, including nonzero bucket selection for
the vertical cursor/layout cases. A host-fetched text-plus-rectangle fixture
now drains `! ESC *c12a5b0P`, queues the compact text bucket and selector-7
rule in the same page record, and carries that combined bucket/rule record
through `0x1ed84` and `0x1ef6a`. A host-fetched
text-plus-rectangle-plus-raster fixture now drains `! ESC *c12a5b0P ESC *t300R
ESC *r0A ESC *b2W` through the same mixed page-record stream runner. That
runner queues compact text, the selector-7 rule, and the delayed `0x105d0`
mode-0 raster transfer in one page record before rendering the combined
bucket/rule/raster record through `0x1ed84` and `0x1ef6a`. Adding FF to that
same stream now publishes the heterogeneous text/rule/raster page record
through the modeled `0xff1e` boundary, clears the current root, and renders
the published record through `0x1ed84` and `0x1ef6a` with the same rows. The
addressed variant now proves the same trailing-FF publication after text,
rule, and raster objects materialize through addressed storage. The addressed
text/rule/raster composition checkpoint classifies the stream objects for that
same byte stream: canonical page-record fields include text object
`0x00d0c004`, rule object `0x00d0c02a`, raster object `0x00d0c038`, bucket
head `+0x1c = 0x00d0c038`, rule head `+0x24 = 0x00d0c02a`, and context slot 0
`0x440946b4`; parser scratch includes restored raster record `80 57 00 02 00
00`, delayed snapshot `01 00 01 05 d0 80 57 00 02 00 00`, payload offset `28`,
and payload `c3 3c`; firmware bookkeeping includes `0x782a70 = 0x00bc`,
`0x782a72 = 0x00d0c000`, `0x782a76 = 0x00d0c044`, one stream allocation, one
page-root allocation, one publication, one root clear, and publication flag
`1`; derived render caches include `0x783a20 = 0x0050`, `0x783a22 = 0`, and
`0x783a28 = 0x00100000` before dispatch targets `0x1f88e` and `0x1effe`
compose the visible rows. The multi-row text/rule/raster sibling drives `! ESC
*c12a5b0P ESC *t300R ESC *r0A ESC *b2W f0 0f ESC *b2W 0f f0 FF` through the
same mixed page-record runner. The modeled publication preserves bucket `0` as
second raster row, first raster row, then compact text; the addressed variant
stores raster objects at `0x00d0d038` and `0x00d0d044`, links `0x00d0d044 ->
0x00d0d038 -> 0x00d0d004`, advances `row_y` to `2`, and renders dispatch
targets `0x1f88e`, `0x1f88e`, and `0x1effe` with the bridged rule list.

A mixed printable/reset stream fixture drives printable `!` followed by `ESC
E`. It keeps the pre-reset compact text object renderable, then applies the
reset publication path from the same byte stream: pending text is flushed, the
valid current page root is published and cleared, the environment is rebuilt,
and HMI is refreshed from the selected current-font metric. The page-record
variant now starts without a current page root, marks the first printable as
the page-record root allocation point, models the `0xff1e` publication record
for that queued compact bucket before reset clears the current root, then
bridges and renders the published record through `0x1edc6`. The addressed
reset variant queues the same printable byte through addressed
`0x1387c`/`0x1381c`, materializes the page record, publishes it through
`0xff1e`, and renders the published record through `0x1ed84`/`0x1ef6a` with
the same rows.

- mixed reset stream bytes: `21 1b 45`
- mixed reset compact object bytes: `00 00 00 00 00 00 00 01 20 00 01`
- mixed reset compact entry: glyph `0x20` at coord `0x0001`
- mixed reset final state: current page root `0`, publications `1`, root
  clears `1`, span flushes `1`, HMI `0x00120000`, data-chain pointer
  `0x782d3e`, reset status `0`
- page-record reset object bytes: `00 00 00 00 00 00 00 01 20 00 01 00 00 00
  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00`
- page-record reset bridged rows match the pre-reset compact text rows.
- published page-record bucket bytes: `00 00 00 00 00 00 00 01 20 00 01 00 00
  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00`
- published page-record `0xff1e` header fields: state byte `+4 = 2`,
  environment byte `+7 = 0x00`, status byte `+8 = 0`, status byte `+0x0a =
  0x00`, environment word `+0x0c = 0x0000`, word `+0x18 = 0x0000`, word `+0x1a
  = 0x0000`, and published pointer `0x780ea6 = 1`.
- synthetic nonzero `0xff1e` header fixture copies pending status bits to
  `+8/+0x0a`, environment state to `+7/+0x0c`, and root word `+0x16` to
  `+0x1a` while preserving the bucket root at `+0x1c`.
- published page-record bridge rows match the pre-reset compact text rows.

A mixed printable/FF page-record stream drives `ESC &k2G`, printable `!`, then
FF from no current page root. The printable queue step allocates the
page-record root; the FF handler applies the mode-2 CR-style horizontal reset,
flushes pending text, finalizes the valid root through modeled `0xff1e`, marks
page eject with pending text `0xff`, and publishes the queued compact text
bucket before clearing the current root. Bridging the published record through
`0x1edc6` renders the same rows as the pre-eject compact text object.

- mixed FF stream bytes: `1b 26 6b 32 47 21 0c`
- page-record FF object bytes: `00 00 00 00 00 00 00 01 20 00 01 00 00 00 00
  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00`
- page-record FF final state: current page root `0`, publications `1`, root
  clears `1`, page roots `1`, finalizes `1`, pending text `0xff`, span flushes
  `1`
- published FF page-record bucket bytes: `00 00 00 00 00 00 00 01 20 00 01 00
  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  00`
- published FF page-record bridge rows match the pre-eject compact text rows.
- remaining gap: reset, FF, page-size, orientation, paper-source, and copies
  records now run from parser trace through publication, `0x1ed84`, and
  `0x1ef6a`; residual work is broader full-page merge/device comparison and
  additional source/bucket variants that change page-record fields or rows.

## `0xd3b2` Unflagged Positioning Fixture

This fixture pins the unflagged/inline positioning arithmetic at `0xd3b2`,
then continues through the unflagged branch of `0x12f2e`. The first inline
case now starts from a selected inline/downloaded context model: `0x14e24`
calls `0x14eb6`-equivalent fixed-record probes, maps host byte `0x21` to glyph
`1`, and `0x1393a` builds the source object with record pointer `context_base
+ 0x40 + 8*glyph`. The selected-map memory also constructs wide, segmented,
and segmented-wide fixed records for host bytes `0x23`, `0x24`, and `0x25`,
then drives them through `0x1393a`, `0xd3b2`, `0x12f2e`, and renderers
`0x1f0d2`, `0x1f1f0`, and `0x1f264`; the later synthetic records remain as
renderer-isolation controls. For unflagged sources, record byte `+0` is the
width threshold byte, byte `+1` is the row count used for short/segmented
selection, and byte `+2` feeds the signed positioning arithmetic.

- selected inline map: context `0x00000100`, host `0x21 -> glyph 1`, invalid
  sentinel host `0x22 -> glyph 0`, glyph-1 record `02 03 04 00 00 00 00 80`,
  bitmap `0x000180`.
- selected inline source object from `0x1393a`: glyph entry `0x000148`, flag
  `0`, x `0`, y `0`, context slot `3`, valid `True`.
- selected inline positioned object bytes through `0xd3b2`/`0x12f2e`: `00 00
  00 00 00 03 00 01 01 66 01`; page-record prefix `00 00 00 00 00 03 00 01 01
  66 01`.
- selected inline mode-0 rendered rows from fixed-record bitmap bytes:
`......................................`
`......................................`
`......................................`
`......................................`
`......................................`
`......................................`
`......................#.#.#.#..#.#.#.#`
`......................####........####`
`......................##....##..####..`
- constructed wide inline map: host `0x23 -> glyph 3`, record `11 03 04 00 00
  00 01 20`, object `00 00 00 00 10 03 00 01 03 66 01`, renderer `0x1f0d2`,
  span `0x11`, rows `3`, source layout `inline-trailing-plane`.
- constructed segmented inline map: host `0x24 -> glyph 4`, record `02 81 04
  00 00 00 03 00`, first segment object `00 00 00 00 20 03 00 01 04 01 66 01`,
  renderer `0x1f1f0`, row skip `0x80`, rows `1`.
- constructed segmented-wide inline map: host `0x25 -> glyph 5`, record `11 81
  04 00 00 00 05 00`, first segment object `00 00 00 00 30 03 00 01 05 01 66
  01`, renderer `0x1f264`, row skip `0x80`, span `0x11`, source layout
  `inline-trailing-plane`.

- downloaded-character descriptor width helper `0x16b1a`: sampled widths `[1,
8, 9, 16, 17, 24, 25, 4200]` produce accepted mode set `[1, 2]` from span
parity, while invalid widths `[0, 4201]` return status `0` and leave scratch
unchanged.
- downloaded-glyph width-span matrix: host-fetched `ESC )s#W` descriptors with
spans `1..16` install widths `8..128`, publish through printable+FF, and
render bucket `0` through `0x1ed84` / `0x1ef6a`; odd spans greater than one
use split-plane copies at `0x16498`, all cases return through `0x15dc6 ->
0x16498 -> 0x15dcc -> 0x12328` with `0x783140 = 0`, and each published row set
matches the installed bitmap. Case summaries `(span, mode, split, helper, row
sha256)` are `[(1, 2, False, '0x1fa5c',
'9441f5719a0626c2d44e1a6b89d6098ef20ab27c6aa59b1a2d650a62a1cea0ca'), (2, 1,
False, '0x1fe76',
'4ed16c14bd0bacc95657f0393c50847ed42a3f91a6dcc36eef9cecaf05714c08'), (3, 2,
True, '0x20290',
'bed7dd9852f5f6bc3753c2b9e010b716e79289bd89fe6e550f58308f3d8824b3'), (4, 1,
False, '0x207ac',
'1bd52a31a0ab5f22b6ffd9416c293197b84d5094cbd8fdbc178407e2c9331caf'), (5, 2,
True, '0x20cc8',
'a0aacff818f66207ac93bce1a17929b2982b0a6e849e642ccc3bb38c4c9112e3'), (6, 1,
False, '0x212e4',
'f76233969ee10e3fc32396db99b598fea636052d81e562499dcd9f6b8806e0e0'), (7, 2,
True, '0x21900',
'5447be80f6c8d88dde2271c301b8c39cd5cf0b0c4df92072997ce873ffee9608'), (8, 1,
False, '0x2201c',
'54b9fa02b1b5f9814ac35dda4224844b16b0098def10e35e3a2f539f1abd5ff6'), (9, 2,
True, '0x22738',
'0d398f0e45eebcc4515c0e6792987c4754239926fcde498ffeafddbf8cc41444'), (10, 1,
False, '0x22f54',
'dd5e6945d064add69c0e58b799eeae9b32e92cbf53a11303f60cbd7a5d49d3bb'), (11, 2,
True, '0x23770',
'72c4ca88b03a6d6347c402471f2b6605d79f6f4456262a013de2356877929f80'), (12, 1,
False, '0x24090',
'f75a27fa2f88c3fa56e7c590828ca012b12fadcd4823c9893cfeec8a413f8828'), (13, 2,
True, '0x249b0',
'ff7ed881242bbcaf9dadc9a63c9fe493bdba665363b2df8a81823960ceabfdc3'), (14, 1,
False, '0x253d0',
'8561e405a8c1ba7195177524e2263363b0d647dbc17b4e9027660e0ee9f7f75b'), (15, 2,
True, '0x25df0',
'a079be2b7048bb3189c1d042fb3d7c2ea79adda163dade7da8227128c2b6bd2c'), (16, 1,
False, '0x26910',
'e8c0cc73909e278576859022c9aa89df9d9f37b1da4466cb875098bbfdd2ff8b')]`.
- downloaded-glyph width-byte boundary: fixture `downloaded glyph width-byte
boundary truncates page-record span` installs descriptor spans `0x00ff`, every
span `0x0100..0x0111`, `0x017f`, `0x0180`, `0x01fe`, and `0x020d` with
canonical width words through `0x16498`, then feeds the current unflagged
printable source record into `0x12f2e`. The source record exposes only byte
`+0`: source width bytes `0x11..0xff` queue selector `0x1003`, while source
width bytes `0x00..0x10` queue selector `0x0003`. All cases publish bucket `0`
through `0xff1e`, clear the current root, and preserve the queued object as
published bucket root. The visible render edge is now split by source byte:
spans `0x00ff`, `0x0111`, `0x017f`, `0x0180`, and `0x01fe` stay compact-wide
through `0x1f0d2` and match installed bitmap rows, while the complete low-byte
range `0x00..0x10` enters compact mode-0 at `0x1effe` and reads `0x1f08e +
span * 4` entries outside the decoded row-copy helper heads, including
non-helper longwords `0x20700000`, `0x4e90202c`, and `0x4e904cdf`. Case
summaries `(span, width byte, selector, visible status, model rows equal
installed-bitmap decode, render edge, record)` are `[(259, 3, '0x0003',
'invalid-helper-boundary', None, {'renderer': 126974, 'mode': 'compact-mode0',
'render_span': 259, 'source_width_byte': 3, 'helper_entry': 128154,
'helper_target': 1289687088, 'helper_target_in_rom': False, 'helper_opcode':
0, 'helper_target_class': 'outside-firmware-address-space', 'pixel_claim':
'none: helper table entry is outside decoded row-copy helper heads'}, '00 00
00 00 0c 02 00 03 08 18 00 00'), (260, 4, '0x0003', 'invalid-helper-boundary',
None, {'renderer': 126974, 'mode': 'compact-mode0', 'render_span': 260,
'source_width_byte': 4, 'helper_entry': 128158, 'helper_target': 1316290561,
'helper_target_in_rom': False, 'helper_opcode': 0, 'helper_target_class':
'outside-firmware-address-space', 'pixel_claim': 'none: helper table entry is
outside decoded row-copy helper heads'}, '00 00 00 00 0c 01 00 03 08 20 00
00'), (261, 5, '0x0003', 'invalid-helper-boundary', None, {'renderer': 126974,
'mode': 'compact-mode0', 'render_span': 261, 'source_width_byte': 5,
'helper_entry': 128162, 'helper_target': 4108320769, 'helper_target_in_rom':
False, 'helper_opcode': 0, 'helper_target_class':
'outside-firmware-address-space', 'pixel_claim': 'none: helper table entry is
outside decoded row-copy helper heads'}, '00 00 00 00 0c 02 00 03 08 28 00
00'), (262, 6, '0x0003', 'invalid-helper-boundary', None, {'renderer': 126974,
'mode': 'compact-mode0', 'render_span': 262, 'source_width_byte': 6,
'helper_entry': 128166, 'helper_target': 4108320769, 'helper_target_in_rom':
False, 'helper_opcode': 0, 'helper_target_class':
'outside-firmware-address-space', 'pixel_claim': 'none: helper table entry is
outside decoded row-copy helper heads'}, '00 00 00 00 0c 01 00 03 08 30 00
00'), (263, 7, '0x0003', 'invalid-helper-boundary', None, {'renderer': 126974,
'mode': 'compact-mode0', 'render_span': 263, 'source_width_byte': 7,
'helper_entry': 128170, 'helper_target': 4108320769, 'helper_target_in_rom':
False, 'helper_opcode': 0, 'helper_target_class':
'outside-firmware-address-space', 'pixel_claim': 'none: helper table entry is
outside decoded row-copy helper heads'}, '00 00 00 00 0c 02 00 03 08 38 00
00'), (264, 8, '0x0003', 'invalid-helper-boundary', None, {'renderer': 126974,
'mode': 'compact-mode0', 'render_span': 264, 'source_width_byte': 8,
'helper_entry': 128174, 'helper_target': 4108320769, 'helper_target_in_rom':
False, 'helper_opcode': 0, 'helper_target_class':
'outside-firmware-address-space', 'pixel_claim': 'none: helper table entry is
outside decoded row-copy helper heads'}, '00 00 00 00 0c 01 00 03 08 40 00
00'), (265, 9, '0x0003', 'invalid-helper-boundary', None, {'renderer': 126974,
'mode': 'compact-mode0', 'render_span': 265, 'source_width_byte': 9,
'helper_entry': 128178, 'helper_target': 4108320769, 'helper_target_in_rom':
False, 'helper_opcode': 0, 'helper_target_class':
'outside-firmware-address-space', 'pixel_claim': 'none: helper table entry is
outside decoded row-copy helper heads'}, '00 00 00 00 0c 02 00 03 08 48 00
00'), (266, 10, '0x0003', 'invalid-helper-boundary', None, {'renderer':
126974, 'mode': 'compact-mode0', 'render_span': 266, 'source_width_byte': 10,
'helper_entry': 128182, 'helper_target': 4108320769, 'helper_target_in_rom':
False, 'helper_opcode': 0, 'helper_target_class':
'outside-firmware-address-space', 'pixel_claim': 'none: helper table entry is
outside decoded row-copy helper heads'}, '00 00 00 00 0c 01 00 03 08 50 00
00'), (267, 11, '0x0003', 'invalid-helper-boundary', None, {'renderer':
126974, 'mode': 'compact-mode0', 'render_span': 267, 'source_width_byte': 11,
'helper_entry': 128186, 'helper_target': 4108320769, 'helper_target_in_rom':
False, 'helper_opcode': 0, 'helper_target_class':
'outside-firmware-address-space', 'pixel_claim': 'none: helper table entry is
outside decoded row-copy helper heads'}, '00 00 00 00 0c 02 00 03 08 58 00
00'), (268, 12, '0x0003', 'invalid-helper-boundary', None, {'renderer':
126974, 'mode': 'compact-mode0', 'render_span': 268, 'source_width_byte': 12,
'helper_entry': 128190, 'helper_target': 4120248321, 'helper_target_in_rom':
False, 'helper_opcode': 0, 'helper_target_class':
'outside-firmware-address-space', 'pixel_claim': 'none: helper table entry is
outside decoded row-copy helper heads'}, '00 00 00 00 0c 01 00 03 08 60 00
00'), (269, 13, '0x0003', 'invalid-helper-boundary', None, {'renderer':
126974, 'mode': 'compact-mode0', 'render_span': 269, 'source_width_byte': 13,
'helper_entry': 128194, 'helper_target': 4108320769, 'helper_target_in_rom':
False, 'helper_opcode': 0, 'helper_target_class':
'outside-firmware-address-space', 'pixel_claim': 'none: helper table entry is
outside decoded row-copy helper heads'}, '00 00 00 00 0c 02 00 03 08 68 00
00'), (270, 14, '0x0003', 'invalid-helper-boundary', None, {'renderer':
126974, 'mode': 'compact-mode0', 'render_span': 270, 'source_width_byte': 14,
'helper_entry': 128198, 'helper_target': 4108320769, 'helper_target_in_rom':
False, 'helper_opcode': 0, 'helper_target_class':
'outside-firmware-address-space', 'pixel_claim': 'none: helper table entry is
outside decoded row-copy helper heads'}, '00 00 00 00 0c 01 00 03 08 70 00
00'), (258, 2, '0x0003', 'invalid-helper-boundary', None, {'renderer': 126974,
'mode': 'compact-mode0', 'render_span': 258, 'source_width_byte': 2,
'helper_entry': 128150, 'helper_target': 26316, 'helper_target_in_rom': True,
'helper_opcode': 19001, 'helper_target_class':
'in-firmware-non-row-copy-helper-opcode', 'pixel_claim': 'none: helper table
entry is outside decoded row-copy helper heads'}, '00 00 00 00 0c 01 00 03 08
10 00 00'), (271, 15, '0x0003', 'invalid-helper-boundary', None, {'renderer':
126974, 'mode': 'compact-mode0', 'render_span': 271, 'source_width_byte': 15,
'helper_entry': 128202, 'helper_target': 4108320769, 'helper_target_in_rom':
False, 'helper_opcode': 0, 'helper_target_class':
'outside-firmware-address-space', 'pixel_claim': 'none: helper table entry is
outside decoded row-copy helper heads'}, '00 00 00 00 0c 02 00 03 08 78 00
00'), (272, 16, '0x0003', 'invalid-helper-boundary', None, {'renderer':
126974, 'mode': 'compact-mode0', 'render_span': 272, 'source_width_byte': 16,
'helper_entry': 128206, 'helper_target': 4108320769, 'helper_target_in_rom':
False, 'helper_opcode': 0, 'helper_target_class':
'outside-firmware-address-space', 'pixel_claim': 'none: helper table entry is
outside decoded row-copy helper heads'}, '00 00 00 00 0c 01 00 03 08 80 00
00'), (273, 17, '0x1003', 'rendered', True, {'renderer': 127186, 'mode':
'compact-wide', 'selector': 4099, 'bucket_index': 0, 'render_span': 273,
'rows_word': 3, 'setup': {'input_word_10': 0, 'divisor_word_06': 5,
'remainder_783a22': 0, 'band_rows_scaled_783a20': 80}, 'split': {'coord': 0,
'row_index': 0, 'input_rows': 3, 'band_rows_scaled_783a20': 80,
'rows_available': 80, 'rows_in_band': 3, 'remaining_after_band': 0,
'returned_d3': 3}, 'full_chunks': 17, 'remainder': 1, 'full_chunk_helper':
193148, 'remainder_helper': 160816}, '00 00 00 00 0c 02 00 03 08 88 00 00'),
(383, 127, '0x1003', 'rendered', True, {'renderer': 127186, 'mode':
'compact-wide', 'selector': 4099, 'bucket_index': 0, 'render_span': 383,
'rows_word': 3, 'setup': {'input_word_10': 0, 'divisor_word_06': 5,
'remainder_783a22': 0, 'band_rows_scaled_783a20': 80}, 'split': {'coord': 0,
'row_index': 0, 'input_rows': 3, 'band_rows_scaled_783a20': 80,
'rows_available': 80, 'rows_in_band': 3, 'remaining_after_band': 0,
'returned_d3': 3}, 'full_chunks': 23, 'remainder': 15, 'full_chunk_helper':
193148, 'remainder_helper': 189998}, '00 00 00 00 0c 02 00 03 0b f8 00 00'),
(384, 128, '0x1003', 'rendered', True, {'renderer': 127186, 'mode':
'compact-wide', 'selector': 4099, 'bucket_index': 0, 'render_span': 384,
'rows_word': 3, 'setup': {'input_word_10': 0, 'divisor_word_06': 5,
'remainder_783a22': 0, 'band_rows_scaled_783a20': 80}, 'split': {'coord': 0,
'row_index': 0, 'input_rows': 3, 'band_rows_scaled_783a20': 80,
'rows_available': 80, 'rows_in_band': 3, 'remaining_after_band': 0,
'returned_d3': 3}, 'full_chunks': 24, 'remainder': 0, 'full_chunk_helper':
193148, 'remainder_helper': 0}, '00 00 00 00 0c 01 00 03 0c 00 00 00'), (510,
254, '0x1003', 'rendered', True, {'renderer': 127186, 'mode': 'compact-wide',
'selector': 4099, 'bucket_index': 0, 'render_span': 510, 'rows_word': 3,
'setup': {'input_word_10': 0, 'divisor_word_06': 5, 'remainder_783a22': 0,
'band_rows_scaled_783a20': 80}, 'split': {'coord': 0, 'row_index': 0,
'input_rows': 3, 'band_rows_scaled_783a20': 80, 'rows_available': 80,
'rows_in_band': 3, 'remaining_after_band': 0, 'returned_d3': 3},
'full_chunks': 31, 'remainder': 14, 'full_chunk_helper': 193148,
'remainder_helper': 187106}, '00 00 00 00 0c 01 00 03 0f f0 00 00'), (255,
255, '0x1003', 'rendered', True, {'renderer': 127186, 'mode': 'compact-wide',
'selector': 4099, 'bucket_index': 0, 'render_span': 255, 'rows_word': 3,
'setup': {'input_word_10': 0, 'divisor_word_06': 5, 'remainder_783a22': 0,
'band_rows_scaled_783a20': 80}, 'split': {'coord': 0, 'row_index': 0,
'input_rows': 3, 'band_rows_scaled_783a20': 80, 'rows_available': 80,
'rows_in_band': 3, 'remaining_after_band': 0, 'returned_d3': 3},
'full_chunks': 15, 'remainder': 15, 'full_chunk_helper': 193148,
'remainder_helper': 189998}, '00 00 00 00 0c 02 00 03 07 f8 00 00'), (256, 0,
'0x0003', 'invalid-helper-boundary', None, {'renderer': 126974, 'mode':
'compact-mode0', 'render_span': 256, 'source_width_byte': 0, 'helper_entry':
128142, 'helper_target': 544210944, 'helper_target_in_rom': False,
'helper_opcode': 0, 'helper_target_class': 'outside-firmware-address-space',
'pixel_claim': 'none: helper table entry is outside decoded row-copy helper
heads'}, '00 00 00 00 0c 01 00 03 08 00 00 00'), (257, 1, '0x0003',
'invalid-helper-boundary', None, {'renderer': 126974, 'mode': 'compact-mode0',
'render_span': 257, 'source_width_byte': 1, 'helper_entry': 128146,
'helper_target': 1318068268, 'helper_target_in_rom': False, 'helper_opcode':
0, 'helper_target_class': 'outside-firmware-address-space', 'pixel_claim':
'none: helper table entry is outside decoded row-copy helper heads'}, '00 00
00 00 0c 02 00 03 08 08 00 00'), (525, 13, '0x0003',
'invalid-helper-boundary', None, {'renderer': 126974, 'mode': 'compact-mode0',
'render_span': 525, 'source_width_byte': 13, 'helper_entry': 129218,
'helper_target': 1318079711, 'helper_target_in_rom': False, 'helper_opcode':
0, 'helper_target_class': 'outside-firmware-address-space', 'pixel_claim':
'none: helper table entry is outside decoded row-copy helper heads'}, '00 00
00 00 0c 02 00 03 10 68 00 00')]`.
- downloaded-glyph wide-remainder matrix: host-fetched `ESC )s#W` descriptors
with matched spans `17..32` and high-span probes `33`, `48`, `49`, `64`, and
`255` publish bucket `0` as selector `0x1003`, dispatch object byte `0x10`
through `0x1ed84` / `0x1ef6a` to `0x1f0d2`, render full chunks through
`0x2f27c`, render remainders `1..15` through `0x1f1ac[remainder]`, render span
`32` as the no-remainder two-full-chunk sibling, and derive rows from
installed bitmap bytes above span `32`. Case summaries `(span, mode, split,
remainder, remainder helper, model rows equal installed-bitmap decode, row
sha256)` are `[(17, 2, True, 1, '0x27430', True,
'd4db5037506d9198b5cdefc72b346251ddd0fd975af478609a70942a4303def4'), (18, 1,
False, 2, '0x27850', True,
'5f8627ae44aea2688bed194c83a0c17430b66ce8a6011acbfbce8fa3537b59dc'), (19, 2,
True, 3, '0x27d84', True,
'e5e73b08ef0846cde340c74fc8816e6233e3cce83400efb52b2e4d6147a80a53'), (20, 1,
False, 4, '0x283ba', True,
'be50e640fe18c62a94f0d2022821790d09e17ee64c05d673776f7099511af2fe'), (21, 2,
True, 5, '0x289f0', True,
'd23793f239ba26446f6f6bf127d26ed52ec50e90327c6b44f279885e5f2a1b14'), (22, 1,
False, 6, '0x29126', True,
'c15e0525915419726f045e0cde5ffeafdbb2b4b760c30948f591e67c05d0eb98'), (23, 2,
True, 7, '0x2985c', True,
'3205b90d6b77bbca18c56c853c33300e8d86527921ff720f5f87bc0d9799b7d0'), (24, 1,
False, 8, '0x2a092', True,
'b49cd0ff1875624f6458e843fecde62a83a3bb849560782fa277ca9cf5440dbd'), (25, 2,
True, 9, '0x2a8c8', True,
'134862834d8734dedf76c0cc715fabf57e60a495de4463bd3abdd888a022767b'), (26, 1,
False, 10, '0x2b1fe', True,
'60be1c8712390434d3d88c41f72b6e5c269f971e2a2764fc116bbc37f4d89298'), (27, 2,
True, 11, '0x2bb34', True,
'ce53c60c4adcccfebb6f23e6a8d336268f1b40c6015271e5b8072fb52ea31ab1'), (28, 1,
False, 12, '0x2c56e', True,
'd98be3105ce906dcd5e30086fa7077c725a9ab22f340fc03ca9b3e75f4036d81'), (29, 2,
True, 13, '0x2cfa8', True,
'8b1040a45d72ca0520886ae7cfb594d044379f9f423844e659b0a911c44565f1'), (30, 1,
False, 14, '0x2dae2', True,
'6da7901279b32bcc222228ce972df3f7dd77948bdae95c4cbf2fe8b92b69277b'), (31, 2,
True, 15, '0x2e62e', True,
'89bd80887655f5a355890b6cd4f7ee0294362f2fff23376c3609825ce7237d49'), (32, 1,
False, 0, '0x00000', True,
'74313da49c64099c8c1e7f57e5f60a6af74e817e1a7ad016a9a6eb3df3dae039'), (33, 2,
True, 1, '0x27430', True,
'26bb53c2931cf88b3dc92b68d2ae32fa72d6a28b9b4ef433f597a6474d929eb2'), (48, 1,
False, 0, '0x00000', True,
'3ba725eb9484f9cd5dbe3245cad0611d4a6119ab4f43773c20e54b281d7a9d60'), (49, 2,
True, 1, '0x27430', True,
'dab6d0217409dfd4d67d1066a5049990cf650fe2f2b1cb8ee1eeaf0ccf336efd'), (64, 1,
False, 0, '0x00000', True,
'f1d647abf77a65108d731772f65a131b2fee3bfa867a49f78a203cfdc3e7bc51'), (255, 2,
True, 15, '0x2e62e', True,
'255ad78f495735678c3337f1ad2e7c35b50c3c2d3a388fc043e0eb6f1fa19092')]`.
- downloaded-glyph segmented-wide matrix: host-fetched `ESC )s#W` descriptors
with matched spans `17..32` plus high-span probes `33`, `48`, `49`, and `64`
at rows `0x81` publish buckets `0` and `8` as selector `0x3003`, dispatch
segment `1` object byte `0x30` through `0x1ed84` / `0x1ef6a` to `0x1f264`,
render full chunks through `0x2f27c`, render remainders `1..15` through
`0x1f1ac[remainder]`, and render span `32` as the no-remainder two-full-chunk
sibling; row derivations above span `32` consume installed bitmap bytes. Case
summaries `(span, mode, split, remainder, A2 offset, A3 offset, model rows
equal installed-bitmap decode, row sha256)` are `[(17, 2, True, 1, 2048, 128,
True, 'c1caa96be75723428224026f32ce885d10a7d21c62d729d71ccf066c18d42bc9'),
(18, 1, False, 2, 2304, 0, True,
'aca3147ec5e28c98458662ac7e77d0404d3ddb49f7e776d3119040eca9480dd2'), (19, 2,
True, 3, 2304, 128, True,
'ab86efa1b42be1de8f7d2ecdc3a279e16bea2c01f74d7f7ce92be011741469a3'), (20, 1,
False, 4, 2560, 0, True,
'bf0edf7169e293f51d99b39038f1afa9890719af337f73babd6bb90a366da4c5'), (21, 2,
True, 5, 2560, 128, True,
'9d9865d2a7517854361c54f2740ccffef1e1756bccfb6d1313dcf1a65a9b2f8d'), (22, 1,
False, 6, 2816, 0, True,
'1dc7163c378e7291cba0de50f5984e1a629b98e03abe85ed7666929d4e55a80c'), (23, 2,
True, 7, 2816, 128, True,
'6c4ae8b7b4aa7c50b40fc4cf3fb495e0a299d12d75501ff840b73a115f6fd736'), (24, 1,
False, 8, 3072, 0, True,
'529821c36835817c34880d906cde954c03b3e56ac26cc6efd47fc05052ae0be1'), (25, 2,
True, 9, 3072, 128, True,
'4fe9ffa891075f87bed422f06c6fadd05915a314fbdeefc624ff8dcf62bcb07c'), (26, 1,
False, 10, 3328, 0, True,
'9fd21c698288d44e4291e16700f6416d524520394e7a63c43c30221aba58881e'), (27, 2,
True, 11, 3328, 128, True,
'4cf5b7d6576e27edb16d9dfe1db67d669dff72ddf904ac95da424182115756d3'), (28, 1,
False, 12, 3584, 0, True,
'b1f09819f6805aff62027f8c30a188aa63263060f7c175391eaf755407e7af4a'), (29, 2,
True, 13, 3584, 128, True,
'627c202a6b934537101f10f61bd2e810e722bf44cbee1ab4abe39fb9024858af'), (30, 1,
False, 14, 3840, 0, True,
'184728cf2eed666094181cb36632e15703bdf5827e987a4923dbc93f61ae5f4d'), (31, 2,
True, 15, 3840, 128, True,
'34726d3441206dfc13bbdbb5ed32d49956565bd6b0542711f1075ee9a8ec61dd'), (32, 1,
False, 0, 4096, 0, True,
'6aa6403b131bb35cdd7828a390b9cb9933d33427755e4a7fe8e3d744712f13f4'), (33, 2,
True, 1, 4096, 128, True,
'f19d6249455463cf24f559a8554ff4af42dd51e24b15d68c5ef331322b2ed03a'), (48, 1,
False, 0, 6144, 0, True,
'ad2b23b26e06945200962ecad5e55e3afa040f2f905a9e4a58fe7c7aa82b747e'), (49, 2,
True, 1, 6144, 128, True,
'd7a7f3655ab2c9b2e4f0de9bc0af87d8fe874f8d7c9db042760453e88502a8c4'), (64, 1,
False, 0, 8192, 0, True,
'3f50798cb224750d8018d054c4c923a500f0a788c71383c526f2ec85e4f095aa')]`.
- downloaded-glyph segmented-wide row/span cross-products: fixture `downloaded
segmented-wide row-span cross-products render selected segment` extends the
rows-`0x81` segmented-wide matrix to row words `0x0082` and `0x0083` crossed
with spans `17`, `18`, `31`, and `32`. All cases publish buckets `0` and `8`
as selector `0x3003`, dispatch segment `1` through `0x1ed84` / `0x1ef6a` to
`0x1f264`, preserve the full-success return boundary, and match installed
bitmap rows. Case summaries `(rows, span, mode, remainder, current rows,
fallback rows, row sha256)` are `[(130, 17, 2, 1, 2, 0,
'6601e8fee61ed1f585b01d252b2f99817a77d695d1bc53aec362c13a4e5e0664'), (130, 18,
1, 2, 2, 0,
'32fa9da71f2e3b1c48f2a7c495fc3b204b7f655c02347cb5a0fad2094c78d0ec'), (130, 31,
2, 15, 2, 0,
'f50a1cab82417414b5013bcdbbf20cb8f779ea0ba3a0cc7fd4f796dc1e2050a5'), (130, 32,
1, 0, 2, 0,
'bf0c5f640b1676a82a9c9b69bbe6afa921359b2d4af8965730d37bdf99c3034c'), (131, 17,
2, 1, 3, 0,
'e2705fe40f7882eea6f7496a9597865f8caad9afda088327be6b4f4f1e73300a'), (131, 18,
1, 2, 3, 0,
'ffdf9355fb3ee1c86083ff2c3e3e685a356a30e6ba8aca9f3d3dc8e39ef7c91f'), (131, 31,
2, 15, 3, 0,
'91dab987ca9df99aee17e8fa8912ca5e6b92a9a01ac69a275975e81bf25f8e4b'), (131, 32,
1, 0, 3, 0,
'0fa2c5d8bfc046bea13d3677d29a2f02e1a101b4be5471b470e7bd2ae4b84835')]`.
- downloaded-glyph segmented-wide high-row fallback fixtures cover installed
row words `0x0181`, `0x0182`, `0x01ff`, `0x0281`, `0x0282`, `0x02ff`,
`0x0381`, `0x0382`, `0x03ff`, `0x0481`, `0x0482`, `0x04ff`, `0x0581`,
`0x0582`, `0x05ff`, `0x0681`, `0x0682`, `0x06ff`, `0x0781`, `0x0782`, and
`0x0787`: `0x16498` preserves each canonical row word, the current unflagged
printable source record exposes only the low row byte to `0x12f2e`, and rows
with low byte above `0x80` queue selector `0x3003` segments `1` and `0`.
Selected segment `1` publishes bucket `8`, dispatches through `0x1ed84` /
`0x1ef6a` to `0x1f264`, and matches installed bitmap rows for spans `17`,
`18`, and `32` through `0x03ff`, spans `17`, `18`, and `24` for `0x04xx`,
spans `17`, `18`, and `23` for `0x0581`/`0x0582`, spans `17`, `18`, and `21`
for `0x05ff`, spans `17`, `18`, and `19` for `0x0681`/`0x0682`, spans `17` and
`18` for `0x06ff`, and span `17` for `0x0781`, `0x0782`, and `0x0787`.
Adjacent span-31 fixtures through `0x03ff` stop at fallback A2 source-read
boundary `+0xb50`; `0x04xx`, `0x05xx`, `0x06xx`, and `0x07xx` oversized
siblings stop at the parser payload-count cap before renderer entry. Case
summaries `(rows, span, selector, segment, current rows, fallback rows, row
sha256)` are `[(385, 17, '0x3003', 1, 32, 96,
'8f26d271a92e93718acdfd0d11f6592f48e5516e616ded07f3d9cb5d88ea7af1'), (385, 18,
'0x3003', 1, 32, 96,
'0268044865744635e4a1182e80ea07a28b2ab617e42bfbb3e15a84dffc419559'), (385, 32,
'0x3003', 1, 32, 96,
'060dfc5c8b416f17500c062c0f1cd57406fc3fd8326e12ea7c1cd97293eee4c6'), (386, 17,
'0x3003', 1, 32, 96,
'8f26d271a92e93718acdfd0d11f6592f48e5516e616ded07f3d9cb5d88ea7af1'), (386, 18,
'0x3003', 1, 32, 96,
'0268044865744635e4a1182e80ea07a28b2ab617e42bfbb3e15a84dffc419559'), (386, 32,
'0x3003', 1, 32, 96,
'060dfc5c8b416f17500c062c0f1cd57406fc3fd8326e12ea7c1cd97293eee4c6'), (511, 17,
'0x3003', 1, 32, 96,
'8f26d271a92e93718acdfd0d11f6592f48e5516e616ded07f3d9cb5d88ea7af1'), (511, 18,
'0x3003', 1, 32, 96,
'0268044865744635e4a1182e80ea07a28b2ab617e42bfbb3e15a84dffc419559'), (511, 32,
'0x3003', 1, 32, 96,
'060dfc5c8b416f17500c062c0f1cd57406fc3fd8326e12ea7c1cd97293eee4c6'), (641, 17,
'0x3003', 1, 32, 96,
'8f26d271a92e93718acdfd0d11f6592f48e5516e616ded07f3d9cb5d88ea7af1'), (641, 18,
'0x3003', 1, 32, 96,
'0268044865744635e4a1182e80ea07a28b2ab617e42bfbb3e15a84dffc419559'), (641, 32,
'0x3003', 1, 32, 96,
'060dfc5c8b416f17500c062c0f1cd57406fc3fd8326e12ea7c1cd97293eee4c6'), (642, 17,
'0x3003', 1, 32, 96,
'8f26d271a92e93718acdfd0d11f6592f48e5516e616ded07f3d9cb5d88ea7af1'), (642, 18,
'0x3003', 1, 32, 96,
'0268044865744635e4a1182e80ea07a28b2ab617e42bfbb3e15a84dffc419559'), (642, 32,
'0x3003', 1, 32, 96,
'060dfc5c8b416f17500c062c0f1cd57406fc3fd8326e12ea7c1cd97293eee4c6'), (767, 17,
'0x3003', 1, 32, 96,
'8f26d271a92e93718acdfd0d11f6592f48e5516e616ded07f3d9cb5d88ea7af1'), (767, 18,
'0x3003', 1, 32, 96,
'0268044865744635e4a1182e80ea07a28b2ab617e42bfbb3e15a84dffc419559'), (767, 32,
'0x3003', 1, 32, 96,
'060dfc5c8b416f17500c062c0f1cd57406fc3fd8326e12ea7c1cd97293eee4c6'), (897, 17,
'0x3003', 1, 32, 96,
'8f26d271a92e93718acdfd0d11f6592f48e5516e616ded07f3d9cb5d88ea7af1'), (897, 18,
'0x3003', 1, 32, 96,
'0268044865744635e4a1182e80ea07a28b2ab617e42bfbb3e15a84dffc419559'), (897, 32,
'0x3003', 1, 32, 96,
'060dfc5c8b416f17500c062c0f1cd57406fc3fd8326e12ea7c1cd97293eee4c6'), (898, 17,
'0x3003', 1, 32, 96,
'8f26d271a92e93718acdfd0d11f6592f48e5516e616ded07f3d9cb5d88ea7af1'), (898, 18,
'0x3003', 1, 32, 96,
'0268044865744635e4a1182e80ea07a28b2ab617e42bfbb3e15a84dffc419559'), (898, 32,
'0x3003', 1, 32, 96,
'060dfc5c8b416f17500c062c0f1cd57406fc3fd8326e12ea7c1cd97293eee4c6'), (1023,
17, '0x3003', 1, 32, 96,
'8f26d271a92e93718acdfd0d11f6592f48e5516e616ded07f3d9cb5d88ea7af1'), (1023,
18, '0x3003', 1, 32, 96,
'0268044865744635e4a1182e80ea07a28b2ab617e42bfbb3e15a84dffc419559'), (1023,
32, '0x3003', 1, 32, 96,
'060dfc5c8b416f17500c062c0f1cd57406fc3fd8326e12ea7c1cd97293eee4c6'), (1153,
17, '0x3003', 1, 32, 96,
'8f26d271a92e93718acdfd0d11f6592f48e5516e616ded07f3d9cb5d88ea7af1'), (1153,
18, '0x3003', 1, 32, 96,
'0268044865744635e4a1182e80ea07a28b2ab617e42bfbb3e15a84dffc419559'), (1153,
24, '0x3003', 1, 32, 96,
'b348b16b9ca11ff34b1a8631ecaafbdf698d253f812c5447bdd2f38b9cdfcd0d'), (1154,
17, '0x3003', 1, 32, 96,
'8f26d271a92e93718acdfd0d11f6592f48e5516e616ded07f3d9cb5d88ea7af1'), (1154,
18, '0x3003', 1, 32, 96,
'0268044865744635e4a1182e80ea07a28b2ab617e42bfbb3e15a84dffc419559'), (1154,
24, '0x3003', 1, 32, 96,
'b348b16b9ca11ff34b1a8631ecaafbdf698d253f812c5447bdd2f38b9cdfcd0d'), (1279,
17, '0x3003', 1, 32, 96,
'8f26d271a92e93718acdfd0d11f6592f48e5516e616ded07f3d9cb5d88ea7af1'), (1279,
18, '0x3003', 1, 32, 96,
'0268044865744635e4a1182e80ea07a28b2ab617e42bfbb3e15a84dffc419559'), (1279,
24, '0x3003', 1, 32, 96,
'b348b16b9ca11ff34b1a8631ecaafbdf698d253f812c5447bdd2f38b9cdfcd0d'), (1409,
17, '0x3003', 1, 32, 96,
'8f26d271a92e93718acdfd0d11f6592f48e5516e616ded07f3d9cb5d88ea7af1'), (1409,
18, '0x3003', 1, 32, 96,
'0268044865744635e4a1182e80ea07a28b2ab617e42bfbb3e15a84dffc419559'), (1409,
23, '0x3003', 1, 32, 96,
'60bee95c742793a9f8aaf2958e1241ba3ce483bca6ee6a2e86b0a201bd0c45ca'), (1410,
17, '0x3003', 1, 32, 96,
'8f26d271a92e93718acdfd0d11f6592f48e5516e616ded07f3d9cb5d88ea7af1'), (1410,
18, '0x3003', 1, 32, 96,
'0268044865744635e4a1182e80ea07a28b2ab617e42bfbb3e15a84dffc419559'), (1410,
23, '0x3003', 1, 32, 96,
'60bee95c742793a9f8aaf2958e1241ba3ce483bca6ee6a2e86b0a201bd0c45ca'), (1535,
17, '0x3003', 1, 32, 96,
'8f26d271a92e93718acdfd0d11f6592f48e5516e616ded07f3d9cb5d88ea7af1'), (1535,
18, '0x3003', 1, 32, 96,
'0268044865744635e4a1182e80ea07a28b2ab617e42bfbb3e15a84dffc419559'), (1535,
21, '0x3003', 1, 32, 96,
'20a135c74614938ab2b2b1be7f5e6e9403a0aa9c988678d51b389e5858c8e5a8'), (1665,
17, '0x3003', 1, 32, 96,
'8f26d271a92e93718acdfd0d11f6592f48e5516e616ded07f3d9cb5d88ea7af1'), (1665,
18, '0x3003', 1, 32, 96,
'0268044865744635e4a1182e80ea07a28b2ab617e42bfbb3e15a84dffc419559'), (1665,
19, '0x3003', 1, 32, 96,
'bf45243656caf88e8e2f54a4ac0e6f78535ab40b0764c4c37a695c893354d6d3'), (1666,
17, '0x3003', 1, 32, 96,
'8f26d271a92e93718acdfd0d11f6592f48e5516e616ded07f3d9cb5d88ea7af1'), (1666,
18, '0x3003', 1, 32, 96,
'0268044865744635e4a1182e80ea07a28b2ab617e42bfbb3e15a84dffc419559'), (1666,
19, '0x3003', 1, 32, 96,
'bf45243656caf88e8e2f54a4ac0e6f78535ab40b0764c4c37a695c893354d6d3'), (1791,
17, '0x3003', 1, 32, 96,
'8f26d271a92e93718acdfd0d11f6592f48e5516e616ded07f3d9cb5d88ea7af1'), (1791,
18, '0x3003', 1, 32, 96,
'0268044865744635e4a1182e80ea07a28b2ab617e42bfbb3e15a84dffc419559'), (1921,
17, '0x3003', 1, 32, 96,
'8f26d271a92e93718acdfd0d11f6592f48e5516e616ded07f3d9cb5d88ea7af1'), (1922,
17, '0x3003', 1, 32, 96,
'8f26d271a92e93718acdfd0d11f6592f48e5516e616ded07f3d9cb5d88ea7af1'), (1927,
17, '0x3003', 1, 32, 96,
'8f26d271a92e93718acdfd0d11f6592f48e5516e616ded07f3d9cb5d88ea7af1')]`.
- downloaded-glyph segmented-wide row-byte boundary: fixture `downloaded
segmented-wide row-byte boundary truncates page-record segments` installs span
`0x11` with canonical row words `0x0002`, `0x007f`, `0x0080`, `0x0081`,
`0x0083`, `0x00fe`, `0x00ff`, `0x0100`, `0x0101`, `0x0181`, `0x0182`,
`0x01ff`, `0x0200`, and `0x0201`; the current unflagged printable source
record exposes only row byte `+1` to `0x12f2e`. Rows whose low byte is above
`0x80` queue selector `0x3003` for segments `1` and `0`; rows whose low byte
is `0x00..0x80` queue selector `0x1003`. That means rows `0x0181`, `0x0182`,
and `0x01ff` queue only produced segments `1` and `0`, not higher canonical
segments, while rows `0x0100`, `0x0101`, `0x0200`, and `0x0201` wrap to
compact-wide selector `0x1003`. Segmented outcomes publish buckets `0` and `8`
through `0xff1e`, while wrapped compact-wide outcomes publish bucket `0`. The
render edge is pinned as `0x1f0d2` for row words `0x0100` and `0x0101`, using
the canonical row words from the installed glyph and splitting them as
`80/176` and `80/177` current/fallback rows; row word `0x0181` reaches
`0x1f264` only for segment `1` (`32/96`) and segment `0` (`80/48`). Case
summaries `(rows, row byte, selector, path, render edge)` are `[(2, 2,
'0x1003', 'short-page-record', {'renderer': 127186, 'mode': 'compact-wide',
'selector': 4099, 'bucket_index': 0, 'render_span': 17, 'rows_word': 2,
'setup': {'input_word_10': 0, 'divisor_word_06': 5, 'remainder_783a22': 0,
'band_rows_scaled_783a20': 80}, 'split': {'coord': 0, 'row_index': 0,
'input_rows': 2, 'band_rows_scaled_783a20': 80, 'rows_available': 80,
'rows_in_band': 2, 'remaining_after_band': 0, 'returned_d3': 2},
'full_chunks': 1, 'remainder': 1, 'full_chunk_helper': 193148,
'remainder_helper': 160816}), (127, 127, '0x1003', 'short-page-record',
{'renderer': 127186, 'mode': 'compact-wide', 'selector': 4099, 'bucket_index':
0, 'render_span': 17, 'rows_word': 127, 'setup': {'input_word_10': 0,
'divisor_word_06': 5, 'remainder_783a22': 0, 'band_rows_scaled_783a20': 80},
'split': {'coord': 0, 'row_index': 0, 'input_rows': 127,
'band_rows_scaled_783a20': 80, 'rows_available': 80, 'rows_in_band': 80,
'remaining_after_band': 47, 'returned_d3': 3080272}, 'full_chunks': 1,
'remainder': 1, 'full_chunk_helper': 193148, 'remainder_helper': 160816}),
(128, 128, '0x1003', 'short-page-record', {'renderer': 127186, 'mode':
'compact-wide', 'selector': 4099, 'bucket_index': 0, 'render_span': 17,
'rows_word': 128, 'setup': {'input_word_10': 0, 'divisor_word_06': 5,
'remainder_783a22': 0, 'band_rows_scaled_783a20': 80}, 'split': {'coord': 0,
'row_index': 0, 'input_rows': 128, 'band_rows_scaled_783a20': 80,
'rows_available': 80, 'rows_in_band': 80, 'remaining_after_band': 48,
'returned_d3': 3145808}, 'full_chunks': 1, 'remainder': 1,
'full_chunk_helper': 193148, 'remainder_helper': 160816}), (129, 129,
'0x3003', 'segmented-page-record', [{'renderer': 127588, 'mode':
'compact-segmented-wide', 'bucket_index': 8, 'segment': 1, 'row_skip': 128,
'rows_here': 1, 'render_span': 17, 'rows_word': 129, 'setup':
{'input_word_10': 8, 'divisor_word_06': 5, 'remainder_783a22': 3,
'band_rows_scaled_783a20': 32}, 'split': {'coord': 0, 'row_index': 0,
'input_rows': 1, 'band_rows_scaled_783a20': 32, 'rows_available': 32,
'rows_in_band': 1, 'remaining_after_band': 0, 'returned_d3': 1},
'full_chunks': 1, 'remainder': 1, 'full_chunk_helper': 193148,
'remainder_helper': 160816}, {'renderer': 127588, 'mode':
'compact-segmented-wide', 'bucket_index': 0, 'segment': 0, 'row_skip': 0,
'rows_here': 128, 'render_span': 17, 'rows_word': 129, 'setup':
{'input_word_10': 0, 'divisor_word_06': 5, 'remainder_783a22': 0,
'band_rows_scaled_783a20': 80}, 'split': {'coord': 0, 'row_index': 0,
'input_rows': 128, 'band_rows_scaled_783a20': 80, 'rows_available': 80,
'rows_in_band': 80, 'remaining_after_band': 48, 'returned_d3': 3145808},
'full_chunks': 1, 'remainder': 1, 'full_chunk_helper': 193148,
'remainder_helper': 160816}]), (131, 131, '0x3003', 'segmented-page-record',
[{'renderer': 127588, 'mode': 'compact-segmented-wide', 'bucket_index': 8,
'segment': 1, 'row_skip': 128, 'rows_here': 3, 'render_span': 17, 'rows_word':
131, 'setup': {'input_word_10': 8, 'divisor_word_06': 5, 'remainder_783a22':
3, 'band_rows_scaled_783a20': 32}, 'split': {'coord': 0, 'row_index': 0,
'input_rows': 3, 'band_rows_scaled_783a20': 32, 'rows_available': 32,
'rows_in_band': 3, 'remaining_after_band': 0, 'returned_d3': 3},
'full_chunks': 1, 'remainder': 1, 'full_chunk_helper': 193148,
'remainder_helper': 160816}, {'renderer': 127588, 'mode':
'compact-segmented-wide', 'bucket_index': 0, 'segment': 0, 'row_skip': 0,
'rows_here': 128, 'render_span': 17, 'rows_word': 131, 'setup':
{'input_word_10': 0, 'divisor_word_06': 5, 'remainder_783a22': 0,
'band_rows_scaled_783a20': 80}, 'split': {'coord': 0, 'row_index': 0,
'input_rows': 128, 'band_rows_scaled_783a20': 80, 'rows_available': 80,
'rows_in_band': 80, 'remaining_after_band': 48, 'returned_d3': 3145808},
'full_chunks': 1, 'remainder': 1, 'full_chunk_helper': 193148,
'remainder_helper': 160816}]), (254, 254, '0x3003', 'segmented-page-record',
[{'renderer': 127588, 'mode': 'compact-segmented-wide', 'bucket_index': 8,
'segment': 1, 'row_skip': 128, 'rows_here': 126, 'render_span': 17,
'rows_word': 254, 'setup': {'input_word_10': 8, 'divisor_word_06': 5,
'remainder_783a22': 3, 'band_rows_scaled_783a20': 32}, 'split': {'coord': 0,
'row_index': 0, 'input_rows': 126, 'band_rows_scaled_783a20': 32,
'rows_available': 32, 'rows_in_band': 32, 'remaining_after_band': 94,
'returned_d3': 6160416}, 'full_chunks': 1, 'remainder': 1,
'full_chunk_helper': 193148, 'remainder_helper': 160816}, {'renderer': 127588,
'mode': 'compact-segmented-wide', 'bucket_index': 0, 'segment': 0, 'row_skip':
0, 'rows_here': 128, 'render_span': 17, 'rows_word': 254, 'setup':
{'input_word_10': 0, 'divisor_word_06': 5, 'remainder_783a22': 0,
'band_rows_scaled_783a20': 80}, 'split': {'coord': 0, 'row_index': 0,
'input_rows': 128, 'band_rows_scaled_783a20': 80, 'rows_available': 80,
'rows_in_band': 80, 'remaining_after_band': 48, 'returned_d3': 3145808},
'full_chunks': 1, 'remainder': 1, 'full_chunk_helper': 193148,
'remainder_helper': 160816}]), (255, 255, '0x3003', 'segmented-page-record',
[{'renderer': 127588, 'mode': 'compact-segmented-wide', 'bucket_index': 8,
'segment': 1, 'row_skip': 128, 'rows_here': 127, 'render_span': 17,
'rows_word': 255, 'setup': {'input_word_10': 8, 'divisor_word_06': 5,
'remainder_783a22': 3, 'band_rows_scaled_783a20': 32}, 'split': {'coord': 0,
'row_index': 0, 'input_rows': 127, 'band_rows_scaled_783a20': 32,
'rows_available': 32, 'rows_in_band': 32, 'remaining_after_band': 95,
'returned_d3': 6225952}, 'full_chunks': 1, 'remainder': 1,
'full_chunk_helper': 193148, 'remainder_helper': 160816}, {'renderer': 127588,
'mode': 'compact-segmented-wide', 'bucket_index': 0, 'segment': 0, 'row_skip':
0, 'rows_here': 128, 'render_span': 17, 'rows_word': 255, 'setup':
{'input_word_10': 0, 'divisor_word_06': 5, 'remainder_783a22': 0,
'band_rows_scaled_783a20': 80}, 'split': {'coord': 0, 'row_index': 0,
'input_rows': 128, 'band_rows_scaled_783a20': 80, 'rows_available': 80,
'rows_in_band': 80, 'remaining_after_band': 48, 'returned_d3': 3145808},
'full_chunks': 1, 'remainder': 1, 'full_chunk_helper': 193148,
'remainder_helper': 160816}]), (256, 0, '0x1003', 'short-page-record',
{'renderer': 127186, 'mode': 'compact-wide', 'selector': 4099, 'bucket_index':
0, 'render_span': 17, 'rows_word': 256, 'setup': {'input_word_10': 0,
'divisor_word_06': 5, 'remainder_783a22': 0, 'band_rows_scaled_783a20': 80},
'split': {'coord': 0, 'row_index': 0, 'input_rows': 256,
'band_rows_scaled_783a20': 80, 'rows_available': 80, 'rows_in_band': 80,
'remaining_after_band': 176, 'returned_d3': 11534416}, 'full_chunks': 1,
'remainder': 1, 'full_chunk_helper': 193148, 'remainder_helper': 160816}),
(257, 1, '0x1003', 'short-page-record', {'renderer': 127186, 'mode':
'compact-wide', 'selector': 4099, 'bucket_index': 0, 'render_span': 17,
'rows_word': 257, 'setup': {'input_word_10': 0, 'divisor_word_06': 5,
'remainder_783a22': 0, 'band_rows_scaled_783a20': 80}, 'split': {'coord': 0,
'row_index': 0, 'input_rows': 257, 'band_rows_scaled_783a20': 80,
'rows_available': 80, 'rows_in_band': 80, 'remaining_after_band': 177,
'returned_d3': 11599952}, 'full_chunks': 1, 'remainder': 1,
'full_chunk_helper': 193148, 'remainder_helper': 160816}), (385, 129,
'0x3003', 'segmented-page-record', [{'renderer': 127588, 'mode':
'compact-segmented-wide', 'bucket_index': 8, 'segment': 1, 'row_skip': 128,
'rows_here': 128, 'render_span': 17, 'rows_word': 385, 'setup':
{'input_word_10': 8, 'divisor_word_06': 5, 'remainder_783a22': 3,
'band_rows_scaled_783a20': 32}, 'split': {'coord': 0, 'row_index': 0,
'input_rows': 128, 'band_rows_scaled_783a20': 32, 'rows_available': 32,
'rows_in_band': 32, 'remaining_after_band': 96, 'returned_d3': 6291488},
'full_chunks': 1, 'remainder': 1, 'full_chunk_helper': 193148,
'remainder_helper': 160816}, {'renderer': 127588, 'mode':
'compact-segmented-wide', 'bucket_index': 0, 'segment': 0, 'row_skip': 0,
'rows_here': 128, 'render_span': 17, 'rows_word': 385, 'setup':
{'input_word_10': 0, 'divisor_word_06': 5, 'remainder_783a22': 0,
'band_rows_scaled_783a20': 80}, 'split': {'coord': 0, 'row_index': 0,
'input_rows': 128, 'band_rows_scaled_783a20': 80, 'rows_available': 80,
'rows_in_band': 80, 'remaining_after_band': 48, 'returned_d3': 3145808},
'full_chunks': 1, 'remainder': 1, 'full_chunk_helper': 193148,
'remainder_helper': 160816}]), (386, 130, '0x3003', 'segmented-page-record',
[{'renderer': 127588, 'mode': 'compact-segmented-wide', 'bucket_index': 8,
'segment': 1, 'row_skip': 128, 'rows_here': 128, 'render_span': 17,
'rows_word': 386, 'setup': {'input_word_10': 8, 'divisor_word_06': 5,
'remainder_783a22': 3, 'band_rows_scaled_783a20': 32}, 'split': {'coord': 0,
'row_index': 0, 'input_rows': 128, 'band_rows_scaled_783a20': 32,
'rows_available': 32, 'rows_in_band': 32, 'remaining_after_band': 96,
'returned_d3': 6291488}, 'full_chunks': 1, 'remainder': 1,
'full_chunk_helper': 193148, 'remainder_helper': 160816}, {'renderer': 127588,
'mode': 'compact-segmented-wide', 'bucket_index': 0, 'segment': 0, 'row_skip':
0, 'rows_here': 128, 'render_span': 17, 'rows_word': 386, 'setup':
{'input_word_10': 0, 'divisor_word_06': 5, 'remainder_783a22': 0,
'band_rows_scaled_783a20': 80}, 'split': {'coord': 0, 'row_index': 0,
'input_rows': 128, 'band_rows_scaled_783a20': 80, 'rows_available': 80,
'rows_in_band': 80, 'remaining_after_band': 48, 'returned_d3': 3145808},
'full_chunks': 1, 'remainder': 1, 'full_chunk_helper': 193148,
'remainder_helper': 160816}]), (511, 255, '0x3003', 'segmented-page-record',
[{'renderer': 127588, 'mode': 'compact-segmented-wide', 'bucket_index': 8,
'segment': 1, 'row_skip': 128, 'rows_here': 128, 'render_span': 17,
'rows_word': 511, 'setup': {'input_word_10': 8, 'divisor_word_06': 5,
'remainder_783a22': 3, 'band_rows_scaled_783a20': 32}, 'split': {'coord': 0,
'row_index': 0, 'input_rows': 128, 'band_rows_scaled_783a20': 32,
'rows_available': 32, 'rows_in_band': 32, 'remaining_after_band': 96,
'returned_d3': 6291488}, 'full_chunks': 1, 'remainder': 1,
'full_chunk_helper': 193148, 'remainder_helper': 160816}, {'renderer': 127588,
'mode': 'compact-segmented-wide', 'bucket_index': 0, 'segment': 0, 'row_skip':
0, 'rows_here': 128, 'render_span': 17, 'rows_word': 511, 'setup':
{'input_word_10': 0, 'divisor_word_06': 5, 'remainder_783a22': 0,
'band_rows_scaled_783a20': 80}, 'split': {'coord': 0, 'row_index': 0,
'input_rows': 128, 'band_rows_scaled_783a20': 80, 'rows_available': 80,
'rows_in_band': 80, 'remaining_after_band': 48, 'returned_d3': 3145808},
'full_chunks': 1, 'remainder': 1, 'full_chunk_helper': 193148,
'remainder_helper': 160816}]), (512, 0, '0x1003', 'short-page-record',
{'renderer': 127186, 'mode': 'compact-wide', 'selector': 4099, 'bucket_index':
0, 'render_span': 17, 'rows_word': 512, 'setup': {'input_word_10': 0,
'divisor_word_06': 5, 'remainder_783a22': 0, 'band_rows_scaled_783a20': 80},
'split': {'coord': 0, 'row_index': 0, 'input_rows': 512,
'band_rows_scaled_783a20': 80, 'rows_available': 80, 'rows_in_band': 80,
'remaining_after_band': 432, 'returned_d3': 28311632}, 'full_chunks': 1,
'remainder': 1, 'full_chunk_helper': 193148, 'remainder_helper': 160816}),
(513, 1, '0x1003', 'short-page-record', {'renderer': 127186, 'mode':
'compact-wide', 'selector': 4099, 'bucket_index': 0, 'render_span': 17,
'rows_word': 513, 'setup': {'input_word_10': 0, 'divisor_word_06': 5,
'remainder_783a22': 0, 'band_rows_scaled_783a20': 80}, 'split': {'coord': 0,
'row_index': 0, 'input_rows': 513, 'band_rows_scaled_783a20': 80,
'rows_available': 80, 'rows_in_band': 80, 'remaining_after_band': 433,
'returned_d3': 28377168}, 'full_chunks': 1, 'remainder': 1,
'full_chunk_helper': 193148, 'remainder_helper': 160816})]`. The font payload
reader fixtures model the byte-copy loops immediately before these fixed
records are usable. Linear reader `0x168dc` copies host bytes into one
destination, treats `0x1a 0x58` as a control escape by calling `0xd99a` and
storing a zero payload byte, and records continuation state when byte budget
`0x783140` expires. Split-plane reader `0x16942` writes `rows * prefix_span`
bytes at `A4`, then one trailing byte per row at `A3 = A4 + rows *
prefix_span`; this is the same A2/A3 layout used by odd-width inline render
fixtures.

- linear copy with `1a 58`: `aa 00 bb cc`, status `1`, budget `0`, control
  hits `1`
- linear continuation after two payload bytes: status `2`, remaining `2`,
  state `{'flag': 1, 'remaining': 2, 'dest_offset': 2}`
- split-plane copy: prefix `a0 a1 c0 c1`, trailing `b0 d0`
- split-plane continuation before trailing byte: status `2`, state `{'flag':
  1, 'prefix_remaining': -1, 'row_remaining': 0, 'prefix_offset': 4,
  'trailing_offset': 1}`
- split-plane copy with `1a 58`: prefix `a0 00`, trailing `b0`, control hits
  `1`
- host-fetched downloaded-character control payload: `ESC )s18W` drains `24`
ring bytes, normalizes prefix `00 aa aa aa aa aa aa aa aa aa aa aa aa aa aa
aa`, and trailing `55`. rendered rows:
- row 0:
  `........#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.`
  `#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.`
  `.#.#.#.#`
- payload-control downloaded-glyph FF publication: host-fetched `ESC )s18W`
  plus printable `&` and FF stores table entry `0x00e2`, normalizes one
  payload control escape, leaves `0x783140 = 1`, drains `[38]` through
  `0x12328`, leaves post-return handlers `['0x0f0f0']`, and the modeled
  page-record publication publishes bucket entries `[1]`, renders bucket word
  `1`, and preserves the wide row through `0xff1e` / `0x1ed84` / `0x1ef6a`.
- host-fetched even-span wide downloaded character: `ESC )s18W` installs glyph
`0x29` at table entry `0x00ee`, copies `18` linear bytes through `0x168dc`
with no control escapes, queues selector `0x1003`, and renders through
`0x1f0d2` row
`......................####........#####.#.#.#..#.#.#.#..####..##....###......#.######.########...........##...###..###..#..#..##.##.##.#....#.#.####.#.##..##.#..##..#`.
- host-fetched row-0x80 downloaded character: `ESC )s256W` installs glyph
`0x2a` at table entry `0x00f2`, copies `256` linear bytes through `0x168dc`,
keeps `rows = 0x80` on short selector `0x0003` rather than segmented selector
`0x2003`, dispatches compact target `0x1effe`, and renders row digest
`918ec4cca20024057ec1b82577b2ab5c039c6fc9a3f756be9bbb62a088bab7ac`.
- `0x16498` replacement/allocation-failure/partial/rejected
downloaded-character exits: linear status-2 copy stores table `0x00f6 ->
0x0840`, copies `4/6` bitmap bytes, and saves continuation `{'flag': 1,
'payload': 0, 'word_0x7827c8': 43, 'dest': 2128, 'trailing_dest': 0,
'remaining': 2, 'd4_counter': 0, 'd3_counter': 0}`; split-plane status-2 copy
stores table `0x00fa -> 0x0880`, copies prefix `a0 a1` and trailing `b0`, and
saves continuation `{'flag': 1, 'payload': 0, 'word_0x7827c8': 44, 'dest':
2190, 'trailing_dest': 2193, 'remaining': 0, 'd4_counter': 1, 'd3_counter':
0}`; replacement glyph `0x2e` releases old record `00 00 02 00` through
`0x17a24`, clears continuation `True`, then stores new table pointer `0x0900`;
allocation failure requests `1` unit from `0x170c`, reports `0x9b5e(0x780e2e,
4)`, releases current payload `0x123456` through `0x1887a`, copies `no` bitmap
bytes, and leaves table `0x0106 -> 0x0000`; mode-0 and header-type range
rejects return `unsupported-record-shape`/`char-outside-header-type` without
changing their headers.
- `0x16498` status-2 partial visible output: linear `ESC )s4W` stores table
`0x00f6 -> 0x0840`, leaves bitmap `f0 0f aa 55 00 00`, saves continuation
`{'flag': 1, 'payload': 0, 'word_0x7827c8': 43, 'dest': 2128, 'trailing_dest':
0, 'remaining': 2, 'd4_counter': 0, 'd3_counter': 0}`, returns with `0x783140
= 0` and drain `{'status': 1, 'values': [], 'pos': 0, 'remaining': 0,
'control_hits': 0}`, then printable `0x2b` reaches handler `0x0d04a`, queues
selector `0x0003` and renders final rows
`['......................####........####',
'......................#.#.#.#..#.#.#.#',
'......................................']`; trailing FF publishes bucket `1`
through `0xff1e` and renders the published rows with digest
`3902a16b4ce383abf9c6bcc90057dfe5ed8fcab9b95b521bbd00a369f71d9596`.
Split-plane `ESC )s3W` stores table `0x00fa -> 0x0880`, leaves bitmap `a0 a1
00 00 b0 00`, saves continuation `{'flag': 1, 'payload': 0, 'word_0x7827c8':
44, 'dest': 2190, 'trailing_dest': 2193, 'remaining': 0, 'd4_counter': 1,
'd3_counter': 0}`, returns with `0x783140 = 0` and drain `{'status': 1,
'values': [], 'pos': 0, 'remaining': 0, 'control_hits': 0}`, then printable
`0x2c` reaches handler `0x0d04a`, queues selector `0x0003` and renders final
rows `['......................#.#.....#.#....#........',
'......................#.##....................']`; trailing FF publishes
bucket `1` through `0xff1e` and renders the published rows with digest
`0edf437de5d7b0ba19545dba9d81bb0ef0586d286d4146f71df3ab20846c78fc`.
- host-fetched segmented downloaded character: `ESC )s258W` installs glyph
`0x27` at table entry `0x00e6`, copies `258` linear bytes through `0x168dc`,
queues selector `0x2003`, and renders segment `1` through `0x1f1f0` row
`......................####........####`.
- segmented downloaded glyph plus raster composition: the same `ESC )s258W`
install queues selector `0x2003` segment objects in buckets `[9, 1]`, adds
mode-0 raster object `00 00 00 00 80 00 00 02 00 00 c3 3c` to bucket `9`, and
renders digest
`0b5440d6733ab9a072e0c14d1a470e6bc944dc98ddbf789152cf65c945dd0f01` through
`0x1ed84`/`0x1ef6a`.
- host-fetched split-plane segmented downloaded character: `ESC )s387W`
installs glyph `0x28` at table entry `0x00ea`, copies prefix `f0 0f` and
trailing `aa` through `0x16942`, queues selector `0x2003`, and renders segment
`1` through `0x1f1f0` row `......................####........#####.#.#.#.`.
- split-plane segmented downloaded glyph plus raster composition: the same
`ESC )s387W` install queues selector `0x2003` segment objects in buckets `[9,
1]`, adds mode-0 raster object `00 00 00 00 80 00 00 02 00 00 c3 3c` to bucket
`9`, and renders digest
`a380045041433910619b809637eda41e81842a3516acb83b488d07f1d3c68872` through
`0x1ed84`/`0x1ef6a`.
- segmented downloaded glyph raster FF publications: linear and split-plane
segmented+raster records publish through `0xff1e` with selected bucket `9`,
preserve bucket-array entries `1, 9` and `1, 9`, and render published rows
with digests
`0b5440d6733ab9a072e0c14d1a470e6bc944dc98ddbf789152cf65c945dd0f01` and
`a380045041433910619b809637eda41e81842a3516acb83b488d07f1d3c68872`.
- split-plane segmented downloaded glyph publication: appending printable
`0x28` and FF after `ESC )s387W` routes tail handlers `0xd04a` and `0xf0f0`
after a zero-byte return drain to handler `0x0d04a`, publishes bucket `9`
through `0xff1e`, preserves bucket-array entries `1, 9`, and renders through
`0x1ed84` / `0x1ef6a` row `......................####........#####.#.#.#.`.
- command edge fixtures: `ESC *c#E` handler `0x15a18` stores absolute
  character/code word `0x7fff` in `0x782f30`; `ESC )s0W` reaches `0x11f96` and
  schedules delayed handler `0x15d0a`, while nonzero `ESC )s#W` schedules
  delayed handler `0x16c14` with absolute byte budget `0x0891`.
- `ESC *c17d25e5F` ROM dispatch trace: parser modes `0 -> 1 -> 3 -> 16 -> 16
  -> 16 -> 0` select handlers `0x11eb6`, `0x11ec8`, `0x11eda`, `0x15a56`,
  `0x15a18`, and `0x16df6`; the chained records set current font id `17`,
  current character `25`, then mark the matching current record with counters
  `{'0x782782': 6, '0x782786': 3}`.
- ROM dispatch trace: `ESC )s0W` and `ESC )s4W` walk parser modes `0 -> 1 -> 4
  -> 13 -> 0` through handlers `0x11eb6`, `0x12008`, `0x11ff6`, and `0x11f96`;
  `0x11f96` then snapshots delayed handlers `0x15d0a` and `0x16c14`, with
  descriptor offset `5` and payload offset `5`.
- descriptor route fixture: `0x15d0a` accepts descriptor kind byte `4`, maps
  selector `0` to current-record status `1` and bit-30 handler `0x16498`, maps
  selector `1` to continuation status `2` and handler `0x15c4c`, and rejects
  kind byte `3` by draining `3` remaining bytes.
- descriptor command streams: `1b 29 73 30 57` restores record `80 57 00 00 00
  00` through delayed handler `0x15d0a`; descriptor `04 00 aa bb` with modeled
  budget `4` routes to current-record handler `0x16498`, while descriptor `04
  01 cc` with budget `3` routes continuation handler `0x15c4c`.
- descriptor parser/route boundary: `ESC )s0W` now ties ROM parser modes `1 ->
  4 -> 13 -> 0`, restored delayed handler `0x15d0a`, descriptor offsets `5/5`,
  and descriptor bytes `04 00 aa bb` / `04 01 cc` to `0x15d0a` current-record
  handler `0x16498` and continuation handler `0x15c4c`.
- host-fetched descriptor boundary: current-record and continuation `ESC )s0W`
  streams drain from the modeled `0xa904` ring source, restore record `80 57
  00 00 00 00`, and route through handlers `0x16498` / `0x15c4c`.

The next modeled step is the current downloaded-font record bookkeeping at
`0x172c0` and `0x16c14`. The record scan treats each `0x782640..0x782776` slot
as a 10-byte entry: word `+0` is the current font/resource id, byte/word area
`+2` carries flags that `0x16c14` clears at bits 5..7, and long `+6` points at
the allocated payload. Status `0` means an existing id with nonzero payload
was found, status `1` means a free zero-id/zero-payload slot was found, and
status `2` makes `0x16c14` consume/skip the byte budget instead of installing
a payload.

- `0x172c0` scan fixtures: existing id `0x1234` -> status `0` at slot `0`;
  missing id with free slot -> status `1` at slot `1`; missing id with no free
  slot -> status `2`.
- replacement path: existing slot `0` releases payload `0x123456`, clears
  matching continuation state `True`, installs payload `0x456789`, clears
  record flag bits 5..7 to `0x00`, and writes candidate flags `0x44000088`
  with high-byte bit 6 set and byte `+0x0c == 2` high-byte bit 2 set.
- byte `+0x20 == 1` counter branch after replacement: counters `{'0x78278e':
  5, '0x782790': 2, '0x782796': 2, '0x782798': 0, '0x78279e': 0, '0x78278a':
  11, '0x782782': 8, '0x782786': 3}`, cursors `{'0x7827ac': 32, '0x7827b0':
  48, '0x7827b4': 64}`.
- integrated install path: `0x16c14` calls `0x1bc38` before its flag edits;
  payload `0x220000` is inserted at returned slot `0x782328`, then the slot
  longword becomes `0x44220000` and the shifted candidate list is
  `['0x00210000', '0x44220000', '0x00230000', '0x00410000']`.
- allocation-failure replacement path: `0x16c14` releases existing payload
  `0x123456` through `0x1887a` before returning budget action
  `skip-allocation-failed`; helper `0x18bf2` clears `191` fixed-record
  characters through `0x18090`, deletes candidate slot `0x782328`, clears
  continuation state `True`, marks context bytes `[{'entry': 0, 'slot':
  'primary', 'byte': 8}, {'entry': 1, 'slot': 'secondary', 'byte': 9}]`, and
  leaves no new candidate installed.
- free-slot path: slot `1` receives id `0x7777` and payload `0x111111`; byte
  `+0x20 != 1` increments counters `{'0x78278e': 1, '0x782790': 0, '0x782796':
  0, '0x782798': 1, '0x78279e': 1, '0x78278a': 1, '0x782782': 1}` with
  candidate flags `0x4000008c`.
- no-slot path: status `2` leaves records unchanged and reports budget action
  `skip-no-record-slot`.
- candidate insertion helper `0x1bc38`: class-zero payload `0x00400000`
  inserts at slot `0x782328` between `0x00300000` and `0x00500000`; class-one
  payload `0x00220000` first accounts for `1` class-zero tail entry, then
  inserts at slot `0x782328`; invalid class byte returns error `(231, 49)`.

The adjacent current-record helpers and the host command edge are now modeled
as well. `0x170be` masks the candidate payload pointer to 24 bits, scans the
same 10-byte current-record table by payload long `+6`, returns the matching
signed id word, and stores the record pointer for callers. `0x17108` reuses
`0x172c0`; when the current id already has a payload and flag bit 6 at record
byte `+2` is clear, it sets that bit, decrements `0x782782`, and increments
`0x782786`. `0x17150` is the inverse count-transfer helper. `0x15a56`
normalizes the parsed `ESC *c#D` font id, and the `0x16df6` dispatch table
routes `ESC *c#F` values to the mark/unmark helpers while suppressing values
`0`, `1`, `2`, `3`, and `6` when mode byte `0x782a92 == 2`.

- payload lookup: payload `0x99123456` masks to `0x123456`, finds slot `0`,
  and returns id `0x1234`; missing payload returns `-1`.
- current-record mark: id `0x1234` changes flag byte from `0x00` to `0x40`,
  with counters `{'0x782782': 6, '0x782786': 3}`; already-marked and
  missing/free-slot cases leave counters unchanged.
- current-record unmark: id `0x1234` changes flag byte from `0x40` to `0x00`,
  with counters `{'0x782782': 7, '0x782786': 2}`; already-unmarked cases leave
  counters unchanged.
- command-edge fixtures: `0x15a56` maps parsed ids `[0, 17, -17, -32768,
  0x8001]` to `[0, 17, 17, 32767, 32767]`; `0x16df6` value `5` targets
  `0x016e86` and marks, value `4` targets `0x016e7e` and unmarks, value `2`
  targets `0x016e4c` but is suppressed in parser mode `2`, and unknown value
  `99` targets no-op `0x016eaa`.

The allocation/header side of that path is now pinned through `0x16fae`,
`0x17362`, `0x17026`, and `0x1719c`. Validator `0x16fae` walks the 32-entry
validation table at `0x16eae` in 8-byte steps, fails immediately if a
predicate returns anything other than `1`, and on success copies up to 16
symbol bytes from `0x1599c` into `0x782842` while byte budget `0x783140`
remains positive, storing the count in `0x782856`. Setup helper `0x17362`
writes staged byte `+0x0c` from the requested type and sets `0x7827ba` to
`0x80` for type `0` or `0x100` for types `1`/`2`. `0x17026` then computes the
allocation size as `((0x7827ba << 2) + 0x9b) >> 6`, writes staged long `+0 =
0x15` and long `+4 = size`, calls the allocator with class `1` and alignment
`0x40`, and initializes the allocated record through `0x1719c`.

- validation semantic map: `32` entries at `0x16eae`, `15`
  consumed-but-not-staged entries, type entry `{'index': 2, 'd5': 3,
  'table_address': 93886, 'reader': 88476, 'predicate': 95074, 'field': 'font
  resource type', 'reader_kind': 'byte', 'effect': 'writes payload byte +0x0c
  and payload units 0x80/0x100'}`, range/count entry `{'index': 6, 'd5': 7,
  'table_address': 93918, 'reader': 88532, 'predicate': 95280, 'field':
  'bounded metric word +0x14 and derived count', 'reader_kind': 'word',
  'effect': 'writes +0x14 and +0x18 = value - word(+0x16) - 1'}`, rounded
  metric entry `{'index': 12, 'd5': 13, 'table_address': 93966, 'reader':
  88532, 'predicate': 95610, 'field': 'rounded metric word +0x2c',
  'reader_kind': 'word', 'effect': 'writes min((value + 2) >> 2, word(+0x14))
  << 2 to +0x2c'}`, flagged metric entry `{'index': 21, 'd5': 22,
  'table_address': 94038, 'reader': 88502, 'predicate': 95786, 'field':
  'flagged metric word +0x1a', 'reader_kind': 'signed-byte', 'effect': 'writes
  sign-extended value to payload word +0x1a'}`, range initializer `{'index':
  25, 'd5': 26, 'table_address': 94070, 'reader': 88532, 'predicate': 95810,
  'field': 'character range initializer', 'reader_kind': 'word', 'effect':
  'clears payload word +0x0e and writes +0x10 = 0x7f or 0xff'}`, dependent
  height entry `{'index': 28, 'd5': 29, 'table_address': 94094, 'reader':
  88476, 'predicate': 95938, 'field': 'dependent byte +0x2a', 'reader_kind':
  'byte', 'effect': 'writes payload byte +0x2a; clamps to 0x80 when
  word(+0x28) is capped'}`.
- validation fixtures: all 32 table entries passing copy `16` symbol bytes `30
  31 32 33 34 35 36 37 38 39 3a 3b 3c 3d 3e 3f` and leave budget `4`; a failed
  entry at index `7` returns status `0` after `8` visits; zero budget still
  validates but copies `0` bytes.
- table-driven validation stream: `32` decoded table entries consume `48`
  bytes before the symbol tail, leave budget `16`, set type byte `+0x0c = 0`,
  range words `+0x12/+0x14/+0x16/+0x18 = 0x0006/0x0009/0x0004/0x0004`, clamp
  spacing words `+0x24/+0x28 = 0x41a0/0x2aaa`, clamp bytes `+0x26/+0x2a/+0x30
  = 00/80/f9`, and copy symbols `41 42 43 44 45 46 47 48 49 4a 4b 4c 4d 4e 4f
  50`.
- validation failure fixtures: invalid resource type fails at entry `2` after
  `4` consumed bytes with byte `+0x0c = 0`; reversed range fails at entry `6`
  after first code `10` and range/count word `5`, leaving derived count word
  `+0x18 = 0` and copying no symbols.
- host-fetched invalid resource payload: `1b 29 73 38 30 57 00 01 02 03`
  reaches restored record `80 57 00 50 00 00`, fails validation entry `2`
  after `4` bytes, skips allocation with status `0`, leaves install `None`,
  and drains entirely from `['ring']` source.
- host-fetched reversed-range resource payload: `1b 29 73 38 30 57 00 01 00 00
  00 00 00 0a 00 06 00 05` reaches restored record `80 57 00 50 00 00`, fails
  validation entry `6` after `12` bytes with words `+0x16/+0x14 = 10/5`, skips
  allocation with status `0`, leaves install `None`, and drains entirely from
  `['ring']` source.
- host-fetched validation-failure family: first-code overflow fails entry `4`
  after `8` bytes, zero and high line/count words fail entry `5` after `10`
  bytes, high and reversed range/count words fail entry `6` after `12` bytes,
  and invalid class byte fails entry `7` after `13` bytes; each restores
  record `80 57 00 50 00 00`, skips allocation, leaves install `None`, and
  drains from `['ring']` source.
- setup type fixtures: type `0` -> byte `+0x0c = 0`, units `0x080`; type `2`
  -> byte `+0x0c = 2`, units `0x100`; unsupported type returns status `0`
  without changing byte `+0x0c`.
- allocation fixture: units `0x080` produce allocation size `10`, staged long
  `+0 = 0x00000015`, staged long `+4 = 10`; invalid validation returns status
  `0` and no payload.
- `0x1719c` sparse header copy fixture: payload long `+0 = 0x00000015`, long
  `+4 = 10`, word `+8 = 0x004a`, byte `+0x0c = 0`, word `+0x0e = 0x1111`, byte
  `+0x20 = 0xc0`, byte `+0x21 = 0xc1`, word `+0x22 = 0x8888`, bytes
  `+0x2f..+0x31 = cf d0 d1`.
- optional symbol bytes: `0x1719c` writes long `+0x38 = 0x024a`, then count
  `3` and bytes `41 42 43` at `payload + 0x024a`.
- payload-backed inline fixture: the table-driven `0x16fae` staging allocates
  a `0x1719c` payload with header word `+8 = 0x004a`, type byte `+0x0c = 0`,
  extra symbol count `16`, then a fixed record placed at the `0x14eb6` scanned
  offset `+0x40 + 8*1 = 0x0048` maps host `0x21` to glyph `1`, queues object
  `00 00 00 00 00 03 00 01 01 66 01`, and renders the same mode-0 rows from
  bitmap `0x00a0`.
- resource payload command stream: `1b 29 73 38 30 57` walks ROM parser modes
  `1 -> 4 -> 13 -> 0`, restores delayed handler `0x16c14`, starts payload at
  offset `6` / length `80`, validates `64` bytes through `0x16fae`, allocates
  size `10` through `0x17026`/`0x1719c`, and installs candidate longword
  `0x40000000` through `0x16c14`/`0x1bc38`.
- host-fetched resource payload boundary: the complete `86`-byte `ESC )s80W`
  command/payload stream drains from the modeled `0xa904` ring source,
  restores record `80 57 00 50 00 00`, validates through `0x16fae`, and
  installs selected longword `0x40000000`.
- host-fetched resource chain: the fetched font-control record for current id
  `0x1234` now feeds the fetched `ESC )s80W` resource stream, releases prior
  payload `0x456789`, installs candidate longword `0x40000000`, and dispatches
  the same selected symbol `0x1234` through the bit-30 resource form.
- installed payload-backed resource dispatch: the same `0x1719c` payload goes
  through integrated `0x16c14`/`0x1bc38`, setting candidate longword
  `0x40000000`; `0x14c64` then takes the bit-30 offset-table branch, writes
  range `0x0000..0x007f`, rebuilds map `0x782f32` through `0x14d9c`, maps host
  `0x21` to glyph `33`, and snapshots `0x15890` symbol `0x1234` from
  `+0x22-word`.
- payload-backed fixed-record isolation dispatch: forcing that same `0x1719c`
  payload through bit-30-clear slot `0x782324` selects the `0x14e24`/`0x14eb6`
  fixed-record form, writes flag `0x783132 = 0`, rebuilds map `0x782f32`, maps
  host `0x21` to glyph `1`, and snapshots `0x158be` symbol `0x0000` from
  `+0x17-encoded`; this remains a fixed-record control case rather than the
  `0x16c14` installed resource form.
- type-2 payload-backed inline fixture: `0x17362` setup type `2` allocates
  payload units `0x100` / allocation size `18`, then fixed records for host
  `0x23` and `0x24` render through `0x1f0d2` and `0x1f1f0`; that header
  allocation is not large enough for the `0x1f264` segmented-wide bitmap
  payload.
- type-1 payload-backed span-metric fixture: host-fetched `ESC )s80W` writes
  payload byte `+0x0c = 1`, payload units `0x100`, allocation size `18`,
  candidate longword `0x40000000`, then feeds copied metric fields to `0xd4ac`
  high-y `26` and `0xd8fc` high-y `16` with visible span rows.
- type-1/type-2 wide resource publication: fixture `type-1 and type-2 resource
wide glyph FF publications render page records` replays `1b 29 73 31 38 57 f0
0f aa 55 3c c3 81 7e ff 00 18 e7 24 db 42 bd 66 99`, installs record `00 00 00
00 0c 01 00 01 00 90 00 00` at delta `0x0340`, publishes compact-wide object
`00 00 00 00 10 00 00 01 21 5a 00` after the span object, dispatches through
`0x1effe` to `0x1f0d2`, and renders digest
`3985c4c7f33d361e0673e7361ce58aa1b9ba12bd003a2b9166eaddb93888e11e`.
- type-1/type-2 segmented resource publication: fixture `type-1 and type-2
resource segmented glyph FF publications render page records` replays `1b 29
73 32 35 38 57 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 f0 0f`, installs record `00 00 00 00 0c 01 00 81 00 10 00 00` at delta
`0x0360`, publishes segment buckets `[1, 9]`, dispatches bucket `9` through
`0x1effe` to `0x1f1f0`, and renders digest
`f449349d69d7acaff44a3f753253e4ef626057d41a5c8f6d827ce871bfc089b4`.
- metric-variant span fixture: host-fetched `ESC )s80W` changes copied word
  `+0x2c` to `0x0010` and word `+0x1a` to `0x0002`; default `+0x2d = 0x20`
  fails the tight `0xd4ac` page-extent gate, variant `+0x2d = 0x10` queues
  span object `00 00 00 00 40 00 00 01 a4 06 03 00 00 14 00 00 00 00 00 00 00
  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00`, and `0xd8fc` moves
  high-y to `19` / object `00 00 00 00 40 00 00 01 34 06 03 00 00 14 00 00 00
  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00`.
- descriptor metric producer-form cross-product: fixture `descriptor metric
  fields match across inline and resource contexts` proves inline/unflagged
  `d4ac` renders row digest
  `67554ea70d7cfd9b11c0777e3cf65d51600a44301a4f93bd4d9b0c0fbc23c00e`,
  resource/flagged `d8fc` renders row digest
  `00c97b69bc50326e442dd060c88b710b8f00217d40809bed276d8ba48581fdc7`,
  resource/unflagged fails as `offset-table glyph 1 is missing for context
  0x40000000`, and inline/flagged fails as `context 0x00000000 does not select
  the offset-table form`.
- legal descriptor metric value matrix: fixture `legal descriptor metric value
  matrix drives d4ac and d8fc consumers` covers small-rounded,
  clamped-rounded, midpoint-rounded, zero-rounded-offset, negative-offset,
  lower-bound, and upper-bound parser-produced descriptors. The zero case
  copies `+0x14/+0x18/+0x1a/+0x2c = 0x0018/0x0013/0x0000/0x0000`, keeps `d4ac`
  row digest
  `67554ea70d7cfd9b11c0777e3cf65d51600a44301a4f93bd4d9b0c0fbc23c00e`, and
  makes `d8fc` publish high-y `21` / row digest
  `47361fc76bd6284f9d764c0377a3fda64edd3944b5cb2dff72acfd2224bc25e8`.
- negative-offset metric matrix case: input offset byte `0xfe` is copied as
  word `+0x1a = 0xfffe`; `d4ac` keeps row digest
  `67554ea70d7cfd9b11c0777e3cf65d51600a44301a4f93bd4d9b0c0fbc23c00e`, while
  `d8fc` consumes that word as `65534`, computes high-y `-65513`, queues
  object `00 00 00 00 40 00 00 01 04 06 03 00 00 14 00 00 00 00 00 00 00 00 00
  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00`, and renders row digest
  `72bfa14c2a84532e2bdf6fb8fddf26ed6904c49dcf4fdcb322592471b5d5b281`.
- midpoint metric matrix case: copied words `+0x14/+0x18/+0x1a/+0x2c =
  0x0018/0x0013/0x0007/0x0018`, `d4ac` row digest
  `67554ea70d7cfd9b11c0777e3cf65d51600a44301a4f93bd4d9b0c0fbc23c00e`, and
  `d8fc` high-y `14` with compact-only row digest
  `1a73b5e7454202d800c69f626bcf34e7d0d583b459e04c0bd4250010bf3ba28a`.
- metric boundary fixture: fixture `legal descriptor metric boundary values
  drive d4ac and d8fc consumers` proves `d8fc` accepts lower equality `+0x16 =
  21`, accepts exact page extent with `+0x18 = 43`, copies max positive offset
  byte `0x7f` as word `+0x1a = 0x007f` and max negative offset byte `0xff` as
  word `+0x1a = 0xffff`, with high-y values `-106`/`-65514`; it rounds input
  `0x0013` up to copied `+0x2c = 0x0014`, and maps rounded inputs `0x1500`,
  `0x1508`, and `0x15ff` to copied `+0x2c = 0x0060`/`0x0060`/`0x0060`, so
  `d4ac` exits `beyond-page-extent` in all high-byte cases.
- metric extent-fence fixture: fixture `legal descriptor metric extent
  fenceposts drive d4ac and d8fc consumers` varies range words `0x002f`,
  `0x0031`, and `0x0032` with offset bytes `0`, `1`, and `2`. It proves
  `0x17430` derived heights `42`, `44`, and `45`, keeps `d4ac` on digest
  `67554ea70d7cfd9b11c0777e3cf65d51600a44301a4f93bd4d9b0c0fbc23c00e`, accepts
  the height-42 zero-offset `d8fc` case with high-y `21`, and rejects the
  height-44/45 cases as `beyond-page-extent` even when `+0x1a` is `1` or `2`.
- metric range-endpoint fixture: fixture `legal descriptor metric range
  endpoints drive d4ac and d8fc consumers` proves first-code zero copies
  `+0x14/+0x16/+0x18 = 0x0018/0x0000/0x0017`, and first-code `range - 1`
  copies `0x0015/0x0014/0x0000`; both keep `d4ac` row digest
  `67554ea70d7cfd9b11c0777e3cf65d51600a44301a4f93bd4d9b0c0fbc23c00e` and
  `d8fc` high-y `20` / row digest
  `f830d30ea60a61f0b74a489c4b7df1bb25dc464b6765d170c19e7278a0267eab`.
- metric mixed-value fixture: fixture `legal descriptor metric mixed values
  drive d4ac and d8fc consumers` proves mid-range `first/range/rounded/offset
  = 0x0008/0x0030/0x002a/0x02` copies `+0x18/+0x1a/+0x2c =
  0x0027/0x0002/0x002c`, suppresses `d4ac` as `beyond-page-extent`, and
  renders `d8fc` digest
  `00c97b69bc50326e442dd060c88b710b8f00217d40809bed276d8ba48581fdc7`; rounded
  input `0x00ff` caps to copied `+0x2c = 0x00c0`, offset byte `0x80`
  sign-extends to `+0x1a = 0xff80` with high-y `-65387`, and late first-code
  `0x002f` derives `+0x18 = 0`, letting `d4ac` render while `d8fc` exits
  `before-context-lower`.
- metric tight-range fixture: fixture `legal descriptor metric tight range
  values drive d4ac and d8fc consumers` proves range-one zero/clamped rounded
  copies `+0x14/+0x16/+0x18 = 0x0001/0x0000/0x0000` and `+0x2c =
  0x0000/0x0004`, while range-two max-offset cases copy `+0x14/+0x16/+0x18 =
  0x0002/0x0001/0x0000` and `+0x1a = 0x007f/0xffff`; `d4ac` keeps row digest
  `67554ea70d7cfd9b11c0777e3cf65d51600a44301a4f93bd4d9b0c0fbc23c00e`,
  zero-offset `d8fc` keeps row digest
  `47361fc76bd6284f9d764c0377a3fda64edd3944b5cb2dff72acfd2224bc25e8`, and
  max-offset `d8fc` renders high-y `-106`/`-65514` with row digest
  `72bfa14c2a84532e2bdf6fb8fddf26ed6904c49dcf4fdcb322592471b5d5b281`.
- metric low-nibble rounding fixture: fixture `legal descriptor metric
  low-nibble rounding drives d4ac and d8fc consumers` proves rounded inputs
  `0x0001`, `0x0003`, `0x0004`, `0x0005`, and `0x000f` copy to `+0x2c` words
  `0x0000, 0x0004, 0x0004, 0x0004, 0x0010`; `d4ac` keeps row digest
  `67554ea70d7cfd9b11c0777e3cf65d51600a44301a4f93bd4d9b0c0fbc23c00e`, and
  `d8fc` keeps high-y `20` / row digest
  `f830d30ea60a61f0b74a489c4b7df1bb25dc464b6765d170c19e7278a0267eab` for each
  case.
- metric byte-boundary rounding fixture: fixture `legal descriptor metric
  byte-boundary rounding drives d4ac and d8fc consumers` proves rounded inputs
  `0x00fd`, `0x00fe`, `0x0101`, and `0x0102` copy to `+0x2c` words `0x00fc,
  0x0100, 0x0100, 0x0104`; range cap `0x0040` forces input `0x0102` back to
  `0x0100`. The `0x00fd` copy suppresses `d4ac` with digest
  `86e3bb70d51c66ac608345dc3bff6476447ebc500d7c271808a53d6638d59ad6`, while
  the `0x00fe` byte-boundary copy emits the normal `d4ac` span digest
  `67554ea70d7cfd9b11c0777e3cf65d51600a44301a4f93bd4d9b0c0fbc23c00e`; `d8fc`
  exits `beyond-page-extent` for the large derived-height cases.
- clamped metric fixture: host-fetched `ESC )s80W` lowers range/count word
  `+0x14` to `0x0005`, clamps oversized rounded metric input into copied word
  `+0x2c = 0x0014`, keeps byte `+0x2b = 0`, flips the tight `0xd4ac` extent
  gate with `+0x2d = 0x14`, and moves `0xd8fc` high-y to `18` / object `00 00
  00 00 40 00 00 01 24 06 03 00 00 14 00 00 00 00 00 00 00 00 00 00 00 00 00
  00 00 00 00 00 00 00 00 00 00 00`.
- lower-bound metric fixture: host-fetched `ESC )s80W` writes first code
  `+0x16 = 0x0018`, range/count `+0x14 = 0x0600`, derived count `+0x18 =
  0x05e7`, and rounded word `+0x2c = 0x1800`; `d4ac` reads byte `+0x2c =
  0x18`, `d8fc` reads word `+0x16 = 0x0018`, and both exit before lower bound
  at cursor y `21` while the compact glyph objects `00 00 00 00 00 00 00 01 01
  7a 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  00 00 00 00` / `00 00 00 00 00 00 00 01 21 5a 00 00 00 00 00 00 00 00 00 00
  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00` remain queued.
- upper-bound metric fixture: host-fetched `ESC )s80W` expands range/count
  `+0x14` to `0x0040`, derives flagged height `+0x18 = 0x003b`, keeps
  unflagged word `+0x2c = 0x0020`, queues `d4ac` span object `00 00 00 00 40
  00 00 01 a4 06 03 00 00 14 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  00 00 00 00 00 00 00 00`, but makes `d8fc` exit `beyond-page-extent` at
  cursor y `21` while compact object `00 00 00 00 00 00 00 01 21 5a 00 00 00
  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00`
  remains renderable.
- downloaded character command stream: `1b 29 73 32 31 39 33 57` reaches
  delayed handler `0x16c14` through `0x121cc`, restores record `80 57 08 91 00
  00`, and starts payload at offset `8` with byte budget `0x0891`.
- downloaded character parser/object boundary: the same `ESC )s2193W` stream
  walks `0x11774` modes `1 -> 4 -> 13 -> 0`, selects final handler `0x11f96`,
  restores delayed handler `0x16c14`, proves payload offset `8` / length
  `0x0891`, and carries the split-plane tail `aa aa aa aa aa aa aa aa aa aa aa
  aa aa aa aa aa 55` into the `0x16498` object rendered below.
- host-fetched downloaded character boundary: the complete `2201`-byte `ESC
  )s2193W` command/payload stream drains from the modeled `0xa904` ring
  source, replays the same parser handlers, restores record `80 57 08 91 00
  00`, and renders the same compact object rows.
- downloaded character-object fixture: that command stream feeds `0x16498`,
  which allocates a separate class-1 object for glyph `0x25`, computes
  allocation size `35` / object size `0x08c0`, stores pointer-table entry
  `0x00de` at header `+0x4a + 4*0x25`, writes record `00 00 00 00 0c 02 00 81
  00 88 00 00`, and copies `0x0891` split-plane payload bytes through
  `0x16874`/`0x16942`; the compact object `00 00 00 00 30 03 00 01 25 01 66
  01` resolves as `downloaded-pointer` and renders the `0x1f264`
  segmented-wide row.
- host-fetched font-control boundary: the complete `ESC *c4660d37e5F` stream
  drains from the modeled `0xa904` ring source, sets current id `0x1234`,
  current character `0x25`, and mark counters `{'0x782782': 6, '0x782786':
  3}`; those parser-derived values drive the `ESC )s0W` current-record
  descriptor route to `0x16498` and the `ESC )s2193W` character payload table
  entry `0x00de`.
- host-fetched font-control chain: the fetched `ESC *c4660d37e5F` state now
  feeds fetched `ESC )s0W` and `ESC )s2193W` streams, preserving current id
  `0x1234`, current character `0x25`, descriptor handler `0x16498`, table
  entry `0x00de`, bitmap size `0x0891`, and the rendered segmented-wide rows.
- installed downloaded printable boundary: fetched byte `0x25` dispatches
  through `0xd04a`, maps to installed glyph `0x25`, queues segment buckets
  `9/1` through `0x12f2e`/`0x1387c`, and renders segment `1` through
  `0x1ed84`/`0x1ef6a`.
- combined font-download printable stream: one modeled `0xa904` ring fetch now
  drains `ESC *c4660d37e5F`, `ESC )s2193W` payload, and printable `%`,
  restores payload record `80 57 08 91 00 00`, carries current character
  `0x25` into the installed glyph, queues segment buckets `9/1`, preserves the
  bucket root through `0x1edc6`, and renders segment `1` through
  `0x1ed84`/`0x1ef6a`.
- combined stream parser boundaries: total `2215` bytes, control `0..13`,
  payload `13..2214`, printable `2214..2215`; control handlers `0x11eb6,
  0x11ec8, 0x11eda, 0x15a56, 0x15a18, 0x16df6`, payload handlers `0x11eb6,
  0x12008, 0x11ff6, 0x11f96`, printable handlers `0x0d04a`.
- combined stream page object: selector `0x3003`, coord `0x6601`, glyph
  `0x25`, rows `0x0081`, width `0x11`; segment objects `9:00 00 00 00 30 03 00
  01 25 01 66 01` and `1:00 00 00 00 30 03 00 01 25 00 66 01`; bridge bucket
  and render-record bucket both match the segment-1 object.
- combined stream render entry: `0x1ed84` active-copy fields stay zero for
  this minimal page record; `0x1ef6a` setup uses dividend `9`, divisor `5`,
  remainder `4`, band rows `0x0010`, destination `0x00102000`, then dispatches
  byte `+4 = 0x30` to compact target `0x1effe` with context slot `3`.
- combined stream FF publication: appending FF drains `2216` bytes total,
  leaves payload return `0x783140 = 0`, drains `0` bytes through `0x12328`,
  resumes at handler `0x0d04a`, routes tail handlers `0x0d04a, 0x0f0f0`,
  publishes bucket entries `[1, 9]` through `0xff1e`, clears current root to
  `0`, and keeps the single-bucket render check pinned at bucket `9`.
- combined stream published band walk: modeled band words `[1, 9]` render
  segments `[0, 1]`; bucket `1` is blank for this payload while bucket `9`
  produces page row `86`.
- combined stream scheduler band walk: `0x1eba4` produces render-call band
  words `(0, 1, 2, 3, 4, 5, 6, 7, 8, 9)` after `0xff1e`/`0x1ed84` seed work
  word `+0x10` from cleared source `+0x18`; only published buckets `[1, 9]`
  dispatch compact objects, and bucket `9` still produces page row `86`.
- even-span downloaded-glyph FF publication: host-fetched `ESC )s18W` plus
  printable `)` and FF restores record `80 57 00 12 00 00`, routes tail
  handlers `0x0d04a, 0x0f0f0` after a zero-byte return drain, publishes bucket
  entries `[1]`, renders bucket word `1` through `0x1ed84`/`0x1ef6a`, and
  dispatches object byte `0x10` to `0x1effe` / `0x1f0d2`.
- even-span downloaded-glyph return boundary: `0x15dc6 -> 0x16498 -> 0x15dcc
  -> 0x12328` ends font bytes at `24`, leaves remaining `0x783140 = 0`, drains
  `0` bytes through `0x12328`, and resumes the following page stream at
  handler `0x10e68`.
- even-span downloaded-glyph byte-24 handoff: page parsing consumes
  `font_command_final_header` at stream position `24`, matches the install
  event header `True`, resumes at handler `0x10e68`, sees table pointer `00 00
  07 80`, record `00 00 00 00 0c 01 00 01 00 90 00 00`, bitmap `f0 0f aa 55 3c
  c3 81 7e ff 00 18 e7 24 db 42 bd 66 99`, and renders digest
  `84762454e8bba9ce22aa5922b598fc5aed7c3ef9dfe9e55223a178c567f612d3`.
- nonboundary short downloaded-glyph FF publication: host-fetched `ESC )s32W`
  plus printable `+` and FF restores record `80 57 00 20 00 00`, installs rows
  `16` / selector `0x0003`, routes tail handlers `0x0d04a, 0x0f0f0`, publishes
  bucket entries `[1]`, renders bucket word `1`, and preserves row digest
  `28220dd2ecafaf07afc095fa0cc3cb6ed070984b3e3da6762b49ebda582d492b` through
  the published record.
- rows-0x20 short downloaded-glyph FF publication: host-fetched `ESC )s64W`
  plus printable `1` and FF restores record `80 57 00 40 00 00`, installs
  table entry `0x010e`, keeps selector `0x0003`, publishes bucket entries
  `[1]`, renders bucket word `1`, and produces `38` visible rows through
  `0x1fe76`.
- rows-0x40 short downloaded-glyph FF publication: host-fetched `ESC )s128W`
  plus printable `2` and FF restores record `80 57 00 80 00 00`, installs
  table entry `0x0112`, keeps selector `0x0003`, publishes bucket entries
  `[1]`, renders bucket word `1`, and produces `64` current-band rows through
  `0x1fe76`.
- normal/row-0x80/segmented downloaded-glyph FF publications: host-fetched
  `ESC )s6W` plus printable `&` and FF restores record `80 57 00 06 00 00`;
  `ESC )s256W` plus printable `*` and FF restores record `80 57 01 00 00 00`;
  `ESC )s258W` plus printable `'` and FF restores record `80 57 01 02 00 00`.
  Zero-byte return drains resume at handlers `0x0d04a`/`0x0d04a`/`0x0d04a`;
  tail handlers `0x0d04a, 0x0f0f0`/`0x0d04a, 0x0f0f0`/`0x0d04a, 0x0f0f0`
  publish bucket entries `[1]`/`[1]`/`[1, 9]`, render bucket words
  `1`/`1`/`9`, and dispatch object bytes `0x00`/`0x00`/`0x20` to `0x1effe` for
  `0x1fe76`/`0x1fe76`/`0x1f1f0`.
- rows-0x82 segmented downloaded-glyph FF publication: host-fetched `ESC
  )s260W` plus printable `0` and FF restores record `80 57 01 04 00 00`,
  installs table entry `0x010a`, publishes bucket entries `[1, 9]`, renders
  bucket word `9`, and produces `2` segment-1 visible rows through `0x1f1f0`.
- rows-0x102 downloaded-glyph FF publication: host-fetched `ESC )s516W` plus
  printable `3` and FF restores record `80 57 02 04 00 00`, installs table
  entry `0x0116` with record `00 00 00 00 0c 01 01 02 00 10 00 00`, but the
  printable page source exposes row byte `0x02`; `0x12f2e` queues selector
  `0x0003`, publishes bucket entries `[1]`, and `0x1f414` splits glyph rows
  `0x0102` into current/fallback counts `58`/`200`; the `0x1fe76` row-copy
  table is valid through `128`, so fallback table entry `0x329ad3c0` remains
  the unresolved visible-output boundary.
- downloaded-glyph high-row truncation matrix: rows `0x0101, 0x0102, 0x0103`
  install canonical 16-bit row words, but the printable page source exposes
  low-byte rows `0x01, 0x02, 0x03`; all publish bucket `1`, split through
  `0x1f414` into `(current, fallback)` counts `[(58, 199), (58, 200), (58,
  201)]`, and exceed the `0x1fe76` row-copy table limit `128` on fallback.
- downloaded-glyph row-count matrix: additional rows `0x0001, 0x0002, 0x0003,
  0x0004, 0x0005, 0x0006, 0x0007, 0x0008, 0x0009, 0x000a, 0x000b, 0x000c,
  0x000d, 0x000e, 0x000f, 0x0010, 0x0011, 0x0012, 0x0013, 0x0014, 0x0015,
  0x0016, 0x0017, 0x0018, 0x0019, 0x001a, 0x001b, 0x001c, 0x001d, 0x001e,
  0x001f, 0x0021, 0x0022, 0x0023, 0x0024, 0x0025, 0x0026, 0x0027, 0x0028,
  0x0029, 0x002a, 0x002b, 0x002c, 0x002d, 0x002e, 0x002f, 0x0030, 0x0031,
  0x0032, 0x0033, 0x0034, 0x0035, 0x0036, 0x0037, 0x0038, 0x0039, 0x003a,
  0x003b, 0x003c, 0x003d, 0x003e, 0x003f, 0x0041, 0x0042, 0x0043, 0x0044,
  0x0045, 0x0046, 0x0047, 0x0048, 0x0049, 0x004a, 0x004b, 0x004c, 0x004d,
  0x004e, 0x004f, 0x0050, 0x0051, 0x0052, 0x0053, 0x0054, 0x0055, 0x0056,
  0x0057, 0x0058, 0x0059, 0x005a, 0x005b, 0x005c, 0x005d, 0x005e, 0x005f,
  0x0060, 0x0061, 0x0062, 0x0063, 0x0064, 0x0065, 0x0066, 0x0067, 0x0068,
  0x0069, 0x006a, 0x006b, 0x006c, 0x006d, 0x006e, 0x006f, 0x0070, 0x0071,
  0x0072, 0x0073, 0x0074, 0x0075, 0x0076, 0x0077, 0x0078, 0x0079, 0x007a,
  0x007b, 0x007c, 0x007d, 0x007e, 0x007f, 0x0083, 0x0084, 0x0085, 0x0086,
  0x0087, 0x0088, 0x0089, 0x008a, 0x008b, 0x008c, 0x008d, 0x008e, 0x008f,
  0x0090, 0x0091, 0x0092, 0x0093, 0x0094, 0x0095, 0x0096, 0x0097, 0x0098,
  0x0099, 0x009a, 0x009b, 0x009c, 0x009d, 0x009e, 0x009f, 0x00a0, 0x00a1,
  0x00a2, 0x00a3, 0x00a4, 0x00a5, 0x00a6, 0x00a7, 0x00a8, 0x00a9, 0x00aa,
  0x00ab, 0x00ac, 0x00ad, 0x00ae, 0x00af, 0x00b0, 0x00b1, 0x00b2, 0x00b3,
  0x00b4, 0x00b5, 0x00b6, 0x00b7, 0x00b8, 0x00b9, 0x00ba, 0x00bb, 0x00bc,
  0x00bd, 0x00be, 0x00bf, 0x00c0, 0x00c1, 0x00c2, 0x00c3, 0x00c4, 0x00c5,
  0x00c6, 0x00c7, 0x00c8, 0x00c9, 0x00ca, 0x00cb, 0x00cc, 0x00cd, 0x00ce,
  0x00cf, 0x00d0, 0x00d1, 0x00d2, 0x00d3, 0x00d4, 0x00d5, 0x00d6, 0x00d7,
  0x00d8, 0x00d9, 0x00da, 0x00db, 0x00dc, 0x00dd, 0x00de, 0x00df, 0x00e0,
  0x00e1, 0x00e2, 0x00e3, 0x00e4, 0x00e5, 0x00e6, 0x00e7, 0x00e8, 0x00e9,
  0x00ea, 0x00eb, 0x00ec, 0x00ed, 0x00ee, 0x00ef, 0x00f0, 0x00f1, 0x00f2,
  0x00f3, 0x00f4, 0x00f5, 0x00f6, 0x00f7, 0x00f8, 0x00f9, 0x00fa, 0x00fb,
  0x00fc, 0x00fd, 0x00fe, 0x00ff` all fetch through `ESC )s#W`, publish
  through printable+FF, and render through `0x1ed84`/`0x1ef6a`; all `250`
  cases return through `0x15dc6 -> 0x16498 -> 0x15dcc -> 0x12328` with
  `0x783140 = 0`, zero drained bytes, and next handler `0xd04a`. Case
  summaries `(name, selector, buckets, render bucket, row count, row sha256)`
  are `[('short rows-0x01', '0x0003', [1], 1, 7,
  '414d7ded5b3171c17c1cb04a8752c58da1e3ae0c206685539d4f92047537a74c'), ('short
  rows-0x02', '0x0003', [1], 1, 8,
  '6c5d89cbf41892d5b0e611bb05e7163893f6e4c5e3208a911c86549c4fa25565'), ('short
  rows-0x03', '0x0003', [1], 1, 9,
  '1d737da9bde647abe8c186eba9dfa0253652aa4d929d7fd30055529083b40af4'), ('short
  rows-0x04', '0x0003', [1], 1, 10,
  '0c25b1b238e8805219f48c7b2cc034253fb84a7f3f0423fe68af1a2bba2b0498'), ('short
  rows-0x05', '0x0003', [1], 1, 11,
  '8796e68d518b5af77869326a405316dd780bbb23f3a176982eb1d54f3e3cffdd'), ('short
  rows-0x06', '0x0003', [1], 1, 12,
  'b791b24072d4758b9a4e40ae7600cd7e0b2bbbe3757dd001f8819dc6d94a5b7a'), ('short
  rows-0x07', '0x0003', [1], 1, 13,
  'd2beea9dbf9a604abeb5fe8cc87636002405da8f46d6cbbf585af7e7481cd088'), ('short
  rows-0x08', '0x0003', [1], 1, 14,
  '83190a9480d7d5ea3d755c4f1239bf58b4417e68d1e059610cf647cdd1bb7d62'), ('short
  rows-0x09', '0x0003', [1], 1, 15,
  'ff048f2bbf144f5d2b55da9b1bca2cdf4c3f72b92d5272b7f2b8fb6ce11228f7'), ('short
  rows-0x0a', '0x0003', [1], 1, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'), ('short
  rows-0x0b', '0x0003', [1], 1, 17,
  '3830ca130052dd9f7ce79cf1c1e427cd3b5f992534e55ae45baebed3c84f9465'), ('short
  rows-0x0c', '0x0003', [1], 1, 18,
  '12afecf01d69fbaf6a6b6798528fd1fd5855067537b9122b4643eb9736325e5d'), ('short
  rows-0x0d', '0x0003', [1], 1, 19,
  'd85196db9e646951a3df3ae39725bda5d759fc37a54885e6ea7b87c697c52198'), ('short
  rows-0x0e', '0x0003', [1], 1, 20,
  'bc0243b6594c80656ae2a00f04d072afaba854c4b892a73893a4df144b55f40c'), ('short
  rows-0x0f', '0x0003', [1], 1, 21,
  '4fb2a253d67451397844fa77e3f41949a6ef5d7542d64609710f0dfdd371fd0e'), ('short
  rows-0x10', '0x0003', [1], 1, 22,
  'f7c5a4f154a9515a9787f30676de81c1b248f2aacc0b7c2df0f66042689e7900'), ('short
  rows-0x11', '0x0003', [1], 1, 23,
  'f0bcf79ee5c12cfb0b1e02660e080073f58b6a24aca83943fb81ba01330358ce'), ('short
  rows-0x12', '0x0003', [1], 1, 24,
  '75ad70f7657d7d88bfad58baa76c0dd1597e4807a5e5c7f469e2060153133e4d'), ('short
  rows-0x13', '0x0003', [1], 1, 25,
  '87d3ee023ae18013588aa0fce57a9fc87cc3371e24aa97e72abb29339dd3deb1'), ('short
  rows-0x14', '0x0003', [1], 1, 26,
  'ec555b603447b8cd160cad7fd11441bc102f2b7ec2dc411d4b0681c53de68115'), ('short
  rows-0x15', '0x0003', [1], 1, 27,
  'ae1590bd859a8a26f066f72cb2813185cc07539d0d0f9a83ef07c02209ed9b46'), ('short
  rows-0x16', '0x0003', [1], 1, 28,
  '578b85379140fee69877d7cf26219aa9adf3435f4cd8a1a02c888025ca635bb5'), ('short
  rows-0x17', '0x0003', [1], 1, 29,
  '7bc251b074515f3ba67f8023b9b229db47e3b5e345f3eeedb00177d7c300696d'), ('short
  rows-0x18', '0x0003', [1], 1, 30,
  '124edc88ff7756abf3c5a7a141b8efcab5b974eb3938cc67f74d336c27a0fbe1'), ('short
  rows-0x19', '0x0003', [1], 1, 31,
  '915780de2b3b4aa763ddf64cf93e5fd701c2174f3c748b822445c8ac92594988'), ('short
  rows-0x1a', '0x0003', [1], 1, 32,
  '1dc650da3d15d919c8b0c1b35de9347c5543c728ec06c55177258f2180ad5cca'), ('short
  rows-0x1b', '0x0003', [1], 1, 33,
  '6961ed6d2c76089849c830e2461cf07ccd67d72090b1ef72040a9357a83e7096'), ('short
  rows-0x1c', '0x0003', [1], 1, 34,
  'ee5e29521c7ce7aed815bb985c73e28ac1bce501cf996d50ec0f5215a1d206c2'), ('short
  rows-0x1d', '0x0003', [1], 1, 35,
  '862c30777fd3a9ff4311ee3b0d0ce10720cd7d55adc14774b0d9f4307ebc7f92'), ('short
  rows-0x1e', '0x0003', [1], 1, 36,
  '51fd53d04461a766dc36438634c2d908bc6d5681d9419fab6d2dcc0e9b37e0ed'), ('short
  rows-0x1f', '0x0003', [1], 1, 37,
  '1b5d7f126bba9cf60712a0d75804b68cea26419e49c5240fe3592546902ce283'), ('short
  rows-0x21', '0x0003', [1], 1, 39,
  'd4a58394fd46386cf7d05284db1039efdcd0c11c8b08f1f8428163cd996a4fbf'), ('short
  rows-0x22', '0x0003', [1], 1, 40,
  '7c2391a0360da7cd06e378ff7fd86127f3eb1f2cbb6b174917ab058f65c2a6f1'), ('short
  rows-0x23', '0x0003', [1], 1, 41,
  'fbce21833f1fc008a4478f627fcbce94eb805ae540d444f53d9d94f1e4e19931'), ('short
  rows-0x24', '0x0003', [1], 1, 42,
  'd0817e4c4463d95ec216b9ca2d4d967a49dce6c4215476399d517efa2f3f76ab'), ('short
  rows-0x25', '0x0003', [1], 1, 43,
  '1067adb846cd1adf3c9bcaa404bdab6b4f015dc40e441c13c908b3214daee27f'), ('short
  rows-0x26', '0x0003', [1], 1, 44,
  '2a19112e51876d8c7b7b775f3ea276605264f080f498a6136aa9137db851254e'), ('short
  rows-0x27', '0x0003', [1], 1, 45,
  '353b1cd91e67c6c9e82964cc8bcf148dca88e690a20a2b5b3818033055a0467f'), ('short
  rows-0x28', '0x0003', [1], 1, 46,
  'cd419bb6eccfe3bb8c19f318a7be9de001daaf53713d9860e5cec466d0abdda7'), ('short
  rows-0x29', '0x0003', [1], 1, 47,
  '45047bd3f47fbb5669013f28ec439da9574395f7afb73663d4d436903b1827e2'), ('short
  rows-0x2a', '0x0003', [1], 1, 48,
  'c805a8fb8e549aa490cdd19f0c23e4999a2cf7f8994706d37eaddd3ede7cbc60'), ('short
  rows-0x2b', '0x0003', [1], 1, 49,
  '8497824fe787b7d7ce2dbf2c375bd9a01661ce340acd4355703555cb947d2c76'), ('short
  rows-0x2c', '0x0003', [1], 1, 50,
  '32c5c0d47231c735710524666973e59ffdff336b342aee0034def51c65d9e05c'), ('short
  rows-0x2d', '0x0003', [1], 1, 51,
  '6d5a95c565a19106c90785aedb5093dea0ced098ebe7297cf9e8c0b06e95fc3c'), ('short
  rows-0x2e', '0x0003', [1], 1, 52,
  'e9a5360ee4b011e93d97aa553be19f75c23f73190d6aa1afd01faf4b109f36d8'), ('short
  rows-0x2f', '0x0003', [1], 1, 53,
  '7be9cbfe3af001696a760bf934d98475129b4342cfab532072a58d53ce2a63cd'), ('short
  rows-0x30', '0x0003', [1], 1, 54,
  'a87abebc40d641d54a232b30dae061fb8a5327cbfa689ae38af7315af87dba84'), ('short
  rows-0x31', '0x0003', [1], 1, 55,
  '4474c3ad4a1d1fde20d5acf4b6aff3e2e7b8e7888068a96931980e77926ac861'), ('short
  rows-0x32', '0x0003', [1], 1, 56,
  '48643a06316f359327fdac88ddeee1873f5e78bd67b18550ad9f441d545ac26e'), ('short
  rows-0x33', '0x0003', [1], 1, 57,
  '91f5a4b7db04663648d0f5e7a04f1664524011520df5d98857a963057e5d6ed0'), ('short
  rows-0x34', '0x0003', [1], 1, 58,
  '53dc039917ceea083d3834f6e7bae8128cfe405b7cb4c198115d48255a83d586'), ('short
  rows-0x35', '0x0003', [1], 1, 59,
  '9696cf1e2d7118ed8d33eaa3c1ccaf805705509b136f8c24316593faa935d221'), ('short
  rows-0x36', '0x0003', [1], 1, 60,
  '0da10bd9c3174db6aee83ced58e66c19612c45e53a90cc040461be0958fb5a4b'), ('short
  rows-0x37', '0x0003', [1], 1, 61,
  '629094a741ff851453cad75824ed2a4195138c567f934ed6cada3d27cccf1a64'), ('short
  rows-0x38', '0x0003', [1], 1, 62,
  '802690ab4e5365347c34bbae7f112d5e031708dabe45523d30f031d90ae8aeb7'), ('short
  rows-0x39', '0x0003', [1], 1, 63,
  '87d9a7f38355eba8b8069c4d06077c3d594010402aa7fb2c9e409bacb3837041'), ('short
  rows-0x3a', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x3b', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x3c', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x3d', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x3e', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x3f', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x41', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x42', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x43', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x44', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x45', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x46', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x47', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x48', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x49', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x4a', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x4b', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x4c', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x4d', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x4e', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x4f', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x50', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x51', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x52', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x53', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x54', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x55', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x56', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x57', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x58', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x59', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x5a', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x5b', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x5c', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x5d', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x5e', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x5f', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x60', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x61', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x62', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x63', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x64', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x65', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x66', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x67', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x68', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x69', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x6a', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x6b', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x6c', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x6d', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x6e', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x6f', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x70', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x71', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x72', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x73', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x74', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x75', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x76', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x77', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x78', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x79', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x7a', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x7b', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x7c', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x7d', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x7e', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'), ('short
  rows-0x7f', '0x0003', [1], 1, 64,
  '5000f7a7c66dd0c0e520daafd9a3b2de08aa6b67196dc4623e3ee0ed673fa47c'),
  ('segmented rows-0x83', '0x2003', [1, 9], 9, 9,
  '1d737da9bde647abe8c186eba9dfa0253652aa4d929d7fd30055529083b40af4'),
  ('segmented rows-0x84', '0x2003', [1, 9], 9, 10,
  '0c25b1b238e8805219f48c7b2cc034253fb84a7f3f0423fe68af1a2bba2b0498'),
  ('segmented rows-0x85', '0x2003', [1, 9], 9, 11,
  '8796e68d518b5af77869326a405316dd780bbb23f3a176982eb1d54f3e3cffdd'),
  ('segmented rows-0x86', '0x2003', [1, 9], 9, 12,
  'b791b24072d4758b9a4e40ae7600cd7e0b2bbbe3757dd001f8819dc6d94a5b7a'),
  ('segmented rows-0x87', '0x2003', [1, 9], 9, 13,
  'd2beea9dbf9a604abeb5fe8cc87636002405da8f46d6cbbf585af7e7481cd088'),
  ('segmented rows-0x88', '0x2003', [1, 9], 9, 14,
  '83190a9480d7d5ea3d755c4f1239bf58b4417e68d1e059610cf647cdd1bb7d62'),
  ('segmented rows-0x89', '0x2003', [1, 9], 9, 15,
  'ff048f2bbf144f5d2b55da9b1bca2cdf4c3f72b92d5272b7f2b8fb6ce11228f7'),
  ('segmented rows-0x8a', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0x8b', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0x8c', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0x8d', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0x8e', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0x8f', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0x90', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0x91', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0x92', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0x93', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0x94', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0x95', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0x96', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0x97', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0x98', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0x99', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0x9a', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0x9b', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0x9c', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0x9d', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0x9e', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0x9f', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xa0', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xa1', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xa2', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xa3', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xa4', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xa5', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xa6', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xa7', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xa8', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xa9', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xaa', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xab', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xac', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xad', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xae', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xaf', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xb0', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xb1', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xb2', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xb3', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xb4', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xb5', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xb6', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xb7', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xb8', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xb9', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xba', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xbb', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xbc', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xbd', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xbe', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xbf', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xc0', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xc1', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xc2', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xc3', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xc4', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xc5', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xc6', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xc7', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xc8', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xc9', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xca', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xcb', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xcc', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xcd', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xce', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xcf', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xd0', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xd1', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xd2', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xd3', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xd4', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xd5', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xd6', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xd7', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xd8', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xd9', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xda', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xdb', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xdc', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xdd', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xde', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xdf', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xe0', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xe1', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xe2', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xe3', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xe4', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xe5', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xe6', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xe7', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xe8', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xe9', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xea', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xeb', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xec', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xed', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xee', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xef', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xf0', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xf1', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xf2', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xf3', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xf4', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xf5', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xf6', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xf7', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xf8', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xf9', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xfa', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xfb', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xfc', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xfd', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xfe', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932'),
  ('segmented rows-0xff', '0x2003', [1, 9], 9, 16,
  'a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932')]`.

- context metric flag clear: cursor `(10,20)`, printable offset `7`, source
  x-offset `5` -> x `22`, y `22`, context slot `3`, overflow correction `0`
- unflagged short object bytes from record `02 03 04`: `00 00 00 00 00 03 00
  01 01 66 01`
- unflagged page-record short object prefix: `00 00 00 00 00 03 00 01 01 66
  01`
- record byte `+0 = 0x11` sets selector bit `0x1000`, producing object bytes:
  `00 00 00 00 10 03 00 01 01 66 01`
- addressed selector-mode matrix: selectors `0x0003`, `0x1003`, `0x2003`, and
  `0x3003` allocate through `0x1381c`, leave bucket heads `1 -> 0x00d090c8`
  and `9 -> 0x00d090a0`, and render bucket words `1` and `9` through compact
  target `0x1effe`.
- synthetic wide inline render record at context `0x00000100` maps glyph `1`
  to span `0x11`, rows `3`, and split A2/A3 bitmap planes; the
  selector-`0x1000` object renders through `0x1f0d2` as `1` full 16-byte chunk
  plus `1` trailing byte using helpers `0x02f27c` and `0x027430`.
- the same `0x1f0d2` synthetic wide record now crosses a 16-row band at row
  `14`, leaving `2` current-band rows and `1` fallback rows.
- record byte `+1 = 0x81` selects segmented entries with selector `0x2003`:
- bucket `9`, segment `1`: `00 00 00 00 20 03 00 01 01 01 66 01`
- bucket `1`, segment `0`: `00 00 00 00 20 03 00 01 01 00 66 01`
- synthetic inline render record at context `0x00000100` maps glyph `1` to
  span `2`, rows `0x81`, bitmap delta `0x80`; the segment-1 object renders row
  `128` from bytes `aa 55` through `0x1f1f0`:
`......................................`
`......................................`
`......................................`
`......................................`
`......................................`
`......................................`
`......................#.#.#.#..#.#.#.#`
- record bytes `+0 = 0x11`, `+1 = 0x81` select combined selector `0x3003`; the
  segment-1 object renders row `128` through `0x1f264` with split A2/A3
  planes, helpers `0x02f27c` and `0x027430`, and object bytes `00 00 00 00 30
  03 00 01 01 01 66 01`.
- synthetic segment-1 split fixtures now cross row `14` for `0x1f1f0` and
  `0x1f264`, proving the current-band/fallback reruns for both segmented
  compact paths.
- context metric flag set plus left overflow: cursor `(10,20)`, printable
  offset `20`, source x-offset `-15` -> x `9`, y `18`, context slot `3`,
  overflow correction `0x00050000`
- remaining gap: parser-produced font command/data streams now populate
  current records, source/page objects, and visible render rows for the
  covered variants; remaining work is font-command/data streams that change
  current records, source/page objects, bridge state, or rendered rows.

## Segmented Text Bucket Producer Fixture

The same producer model also covers the `0x12f2e` segmented path where the
glyph height word exceeds `0x80`. For `LINE_PRINTER`, host byte `0x20` maps to
glyph byte `0x1f`; the resolved table target is the record base `0x0146b4`,
whose height word is `0x0454` and width word is `0x004a`. `0x12f2e` therefore
sets selector bit `0x2000`, computes segment index `(rows - 1) >> 7 = 8`, and
emits one four-byte entry per segment while stepping the bucket index down by
eight.

- source fields: context `0x440946b4`, host `0x20`, glyph `0x1f`, glyph entry
  `0x0146b4`, width `74`, rows `1108`
- producer path: `segmented`, selector `0x2000`, object size `0x28`, capacity
  `8`, entry size `4`
- page-record allocator first pass: `9` segment objects allocated through
  `0x1387c`; first bucket `64`/segment `8` count `0 -> 1`
- page-record allocator second pass: same selector `0x2000` reuses all segment
  buckets; first bucket count `1 -> 2` and prefix `00 00 00 00 20 00 00 02 1f
  08 00 00 1f 08 00 00`
- firmware-scanned tall target summary: `420` targets across `24` records;
  every target has delta `0`, mode `0`, and width `74`, so the verified
  built-in resources do not provide normal bitmap-entry fixtures for
  `0x1f0d2`, `0x1f1f0`, or `0x1f264`.
| Bucket | Segment byte | Object bytes |
| ---: | ---: | --- |
| `64` | `8` | `00 00 00 00 20 00 00 01 1f 08 00 00` |
| `56` | `7` | `00 00 00 00 20 00 00 01 1f 07 00 00` |
| `48` | `6` | `00 00 00 00 20 00 00 01 1f 06 00 00` |
| `40` | `5` | `00 00 00 00 20 00 00 01 1f 05 00 00` |
| `32` | `4` | `00 00 00 00 20 00 00 01 1f 04 00 00` |
| `24` | `3` | `00 00 00 00 20 00 00 01 1f 03 00 00` |
| `16` | `2` | `00 00 00 00 20 00 00 01 1f 02 00 00` |
| `8` | `1` | `00 00 00 00 20 00 00 01 1f 01 00 00` |
| `0` | `0` | `00 00 00 00 20 00 00 01 1f 00 00 00` |

checks: 695

- 0xa904 no-byte branch returns -1 before buffered sources: ok
- 0xa904 services pending work then prefers first LIFO source: ok
- 0xa904 data-chain end marker retries before second LIFO source: ok
- 0xa904 buffered ring source wins before direct hardware in mode 0: ok
- 0xa904 direct mode 1 preserves 0x1a and clears handshake state: ok
- 0xa904 direct mode 2 reads ready byte and sets control-shadow bit 6: ok
- 0xc0ae publishes external status bits through 0x9bee: ok
- 0xc1c6 dispatches 68 SERVICE from retained-status bit: ok
- 0xc1c6 displays pending external-ready message: ok
- 0xbb0a external-ready teardown ignores scheduler return: ok
- 0xb0c0/0xb022 output FIFO wraps and preserves order: ok
- 0xb090 waits on full FIFO then enqueues after drain: ok
- 0x12034/0x122be model-ID response emits FIFO literal: ok
- 0xaece emits service byte and combined status byte: ok
- 0xae2c drains FIFO by configured output mode: ok
- 0x2888 sets page-environment status consumed by 0xaece: ok
- 0x2888 publishes environment mismatch or status-cache changes: ok
- 0x7612 selects page-environment or normal service helper: ok
- 0x8a48 maps page environment bytes to media-feed messages: ok
- 0x5e80 loads selected default record into canonical defaults: ok
- 0x5060/0x50be/0x52ba update default record and dirty flags: ok
- 0x5a16 forces retained-record read mask then clears it: ok
- 0x56c2 selects active retained record or reports 67 SERVICE: ok
- 0x5e80 -> 0xcda2 reset consumes default record outputs: ok
- 0xcfea/0xcf52/0x104d8 convert default line spacing to reset VMI: ok
- 0xdaf0 tokenizes lowercase-final numeric chain into two six-byte records: ok
- 0xdb74 parses sign, capped fraction digits, and final byte: ok
- 0xdb74 returns D7 zero for semicolon continuation final: ok
- 0x121cc snapshots delayed payload handler and parsed record: ok
- 0x12218 restores delayed parsed record and dispatches saved handler: ok
- 0x11f5a/0x12452 transparent text restores and consumes counted bytes: ok
- 0x12452 transparent text probe keeps non-0x58 byte: ok
- 0x12120 ESC Y alternate append stores normalized display bytes: ok
- 0x1228a consumes absolute delayed payload count without echo: ok
- 0x12358 direct alternate path echoes positive payload bytes only: ok
- 0x9d16/0x9d4e/0x9d86/0x9dbe page geometry lookups mask page code: ok
- ROM page geometry tables match manual logical dimensions: ok
- ROM page geometry tables recover manual printable-area margins: ok
- 0xfc74 ESC &l#A maps page size and recomputes portrait geometry: ok
- 0x10220 ESC &l#O swaps active extents and selects orientation margins: ok
- 0xfc74/0x10220 chained ESC &l stream selects page size then orientation
  handlers: ok
- 0xf9e8 ESC &l#P converts VMI lines to page length and selects internal page
  code: ok
- 0xf9e8 ESC &l#P stream reaches page-length handler: ok
- 0xe112 stores absolute parsed macro id: ok
- 0xdd08 starts and stops empty macro definitions: ok
- 0x11774 ROM dispatch table routes chained ESC &f macro stream: ok
- macro command stream assigns id and starts/stops empty definition: ok
- 0x116f6 alternate parser routes macro stop but suppresses payload controls:
  ok
- host-fetched macro definition stream routes alternate parser table: ok
- macro command stream defines payload and executes data-chain frame: ok
- host-fetched macro execute stream builds replay frame: ok
- macro command stream defines payload and calls data-chain frame: ok
- host-fetched macro call stream builds replay frame: ok
- macro command stream enables and disables overlay state: ok
- 0xe0a4 macro record lookup uses head presence and first free slot: ok
- macro command stream toggles permanence before delete-temporary: ok
- macro command stream deletes current record or all records: ok
- macro command stream respects definition and active-chain guards: ok
- host-fetched macro command streams update records and frames: ok
- macro execute frame payload feeds 0xa904 data-chain bytes: ok
- macro execute payload queues printable glyph then applies CR: ok
- macro execute payload page-record bridge renders queued glyph: ok
- macro execute data-chain replay feeds page-record stream: ok
- macro execute data-chain parser trace feeds page-record stream: ok
- macro call data-chain parser trace feeds page-record stream: ok
- macro execute mixed control payload replays through page-record stream: ok
- host-fetched mixed-control macro execute stream builds replay frame: ok
- macro mixed-control data-chain parser trace feeds page-record stream: ok
- host-fetched macro replay payloads preserve 0x1edc6 bridge contract: ok
- host-fetched macro replay payloads feed 0x1ed84 and 0x1ef6a: ok
- macro execute page-record layer composes with rule and raster band: ok
- macro overlay finalization replays before page publication: ok
- macro overlay replays across repeated page publications: ok
- macro overlay skip gates preserve base page publication: ok
- macro overlay mixed-control payload publishes with page rule: ok
- macro overlay cursor-position payload publishes with page rule: ok
- macro overlay vertical-decipoint payload publishes with page rule: ok
- macro overlay chained cursor-position payload publishes with page rule: ok
- macro overlay chained margin payload publishes with page rule: ok
- macro overlay transparent payload publishes with page rule: ok
- macro overlay raster payload publishes with page rule: ok
- macro overlay multi-row raster payload publishes with page rule: ok
- macro overlay span-flush payload publishes with page rule: ok
- 0xdd08 execute and call push macro data-chain frames: ok
- 0xe418 frame metadata distinguishes execute and call context: ok
- 0xe146/e418/e4f4/e65c macro context stack has eight records and no guard: ok
- macro snapshot helpers copy linked and flat environment ranges: ok
- 0x164a initializes heap allocator bitmap and payload base: ok
- 0x170c/0x1710 allocate and 0x18b4 frees heap units: ok
- 0xe002 appends macro definition bytes into 0x100 chunks: ok
- 0xe4f4/0xe22c produce and end data-chain frames: ok
- 0xe65c refreshes macro font context entries: ok
- 0xe5e2 refreshes page layout, default VFC table, and static font context: ok
- 0x12b96 default VFC table channel convention: ok
- 0xdd08 overlay and temporary/permanent macro controls: ok
- mode 0 literal words: ok
- mode 1 byte expansion: ok
- mode 2 byte expansion: ok
- mode 3 cascaded expansion: ok
- coordinate decode 0x1234: ok
- band clip 0x7000 count 5: ok
- destination shifted current band: ok
- destination fallback buffer: ok
- ESC &k#G line termination mode bits: ok
- CR resets horizontal cursor and flushes pending text span: ok
- CR line-termination mode 1 also advances vertical cursor: ok
- LF line-termination mode 2 resets horizontal cursor: ok
- FF line-termination mode 2 resets horizontal cursor and marks page eject: ok
- HT advances to next eight-column stop: ok
- HT clamps to page width when already beyond right limit: ok
- BS subtracts HMI and sets pending previous-width latch: ok
- BS clamps at left margin when crossing it: ok
- BS alternate metrics subtracts previous width word: ok
- control stream ESC &k1G then CR applies CR+LF: ok
- control stream ESC &k2G then LF applies CR+LF: ok
- control stream ESC &k2G then FF applies CR+page-eject: ok
- control stream ESC &k3G applies CR/LF/FF combined line termination: ok
- control stream HT then BS updates tab and previous-width state: ok
- 0xf75e ESC &f0S pushes cursor with vertical offset: ok
- 0xf75e ESC &f1S pops cursor and clears pending flags: ok
- cursor stack stream ESC &f0S / ESC &f1S selects 0xf75e push/pop: ok
- 0xf75e cursor stack bounds and pop clamps to current extents: ok
- 0xf39e ESC &a#C converts columns through HMI and relative flag: ok
- 0xf416 ESC &a#H converts decipoints and clamps horizontal cursor: ok
- 0xf560 ESC &a#R uses VMI with absolute top offset and relative cursor base:
  ok
- cursor position stream ESC &a3.5c+1R selects 0xf39e then 0xf560: ok
- 0xf60a ESC &a#V converts decipoints and clamps vertical cursor: ok
- 0xedb0 ESC &s#C toggles end-of-line wrap for selectors 0 and 1 only: ok
- 0xf48c/0xf692 ESC *p#X/#Y use whole-dot packed cursor commits: ok
- 0xc992 ESC &l#D accepts ROM LPI set and refreshes pending vertical cursor:
  ok
- 0xcb00 ESC &l#C converts 1/48-inch VMI and keeps zero unmodified: ok
- 0xea9e ESC &l#F sets text length bottom or restores default: ok
- 0xece2 ESC &l#E sets top margin, default text length, and pending cursor: ok
- 0xee64 ESC &l#L toggles perforation skip for selectors 0 and 1 only: ok
- 0xf36c perforation skip gates vertical overflow page eject: ok
- 0xcb00/0xc992/0xece2/0xea9e chained ESC &l stream selects vertical layout
  handlers: ok
- 0xeb58 ESC &a#L sets left margin and moves cursor only when needed: ok
- 0xec0c ESC &a#M applies plus-one column, clamps, and moves cursor at right
  edge: ok
- margin stream ESC &a6l9M selects 0xeb58 then 0xec0c: ok
- ESC E stream publishes valid page root and resets environment/parser state:
  ok
- ESC E stream clears missing page root without publication: ok
- host-fetched ESC E clears missing page root without publication: ok
- 0x41a HEAD scanner walks verified IC32/IC15 resource chain: ok
- 0x41a HEAD scanner would duplicate records under simple resource mirror: ok
- 0x41a HEAD scanner rejects non-HEAD 0x40000 continuations: ok
- 0x1a616 candidate scan continuation policy changes built-in counts: ok
- 0x41a HEAD scanner advances next probe after 0x40000 boundary: ok
- 0x41a HEAD scanner handles 0xbe executable records: ok
- main row-copy width 3 rows 3 writes: ok
- main row-copy width 3 final registers: ok
- main row-copy width 16 rows 3 write count: ok
- main row-copy width 16 first/last writes: ok
- main row-copy width 16 final registers: ok
- remainder row-copy width 1 rows 3 writes: ok
- remainder row-copy width 1 final registers: ok
- chunk row-copy width 16 rows 3 write count: ok
- chunk row-copy width 16 first/last writes: ok
- chunk row-copy width 16 final registers: ok
- resource context 0x4008004c glyph 0 fields: ok
- resource context 0x4008004c glyph 0 bitmap sample: ok
- resource context 0x4008004c glyph 0 full bitmap rows: ok
- resource context 0x4008004c glyph 0 main row-copy rendered rows: ok
- resource context 0x44080418 glyph 0 fields: ok
- resource context 0x44080418 glyph 0 full bitmap rows: ok
- resource context 0x44080418 glyph 0 main row-copy rendered rows: ok
- resource context 0x440946b4 glyph 0 fields: ok
- resource context 0x440946b4 glyph 0 full bitmap rows: ok
- resource context 0x440946b4 glyph 0 main row-copy rendered rows: ok
- resource context 0x440946b4 glyph 32 fields: ok
- resource context 0x440946b4 glyph 32 full bitmap rows: ok
- resource context 0x440946b4 glyph 32 main row-copy rendered rows: ok
- resource glyph row-copy span matrix matches direct decode: ok
- firmware-scanned built-in glyph coverage summary: ok
- line-printer built-in base map host 0x21 to glyph 32: ok
- 0x120be/0x1be22 symbol-set stream updates active words and 0x14f16 glyph
  maps: ok
- 0xc580 dirty primary branch installs page-root font context: ok
- 0xc580 dirty secondary branch installs page-root font context: ok
- 0xc580 full live-slot branch reuses matching page-root font context: ok
- 0xc580 full live-slot branch skips install when c4fc reports full: ok
- 0xc580 selector-mismatch branch refreshes candidate without context install:
  ok
- 0xc580 dirty-2 selector-match branch installs current context only: ok
- 0xc580 dirty-2 secondary selector-match branch installs current context
  only: ok
- 0xc580 dirty-2 selector-mismatch branch only copies remembered word: ok
- symbol-set parser trace feeds active map patches: ok
- 0x1a9be scanned font candidate list partitioning: ok
- actual IC32/IC15 built-in records feed 0x1a9be partitions: ok
- named COURIER and LINE_PRINTER records expose deterministic metadata: ok
- named built-in records expose firmware selection fields: ok
- font sample built-in row fields format through 0x1cabe: ok
- font sample Courier row fields cross page-record placement: ok
- font sample Courier row fields and run 1 share page-record state: ok
- font sample Courier row fields carry run 1 through 0x1d050 to run 2: ok
- font sample page-limit branches trigger continuation calls: ok
- font sample heading continuation emits fresh source heading page record: ok
- font sample cartridge heading continuations emit source-specific page
  records: ok
- font sample alternate row fit gate follows 0x1d868: ok
- font sample alternate-row continuation emits preadvanced row page record: ok
- font sample multi-probe preflight follows 0x1dcf2: ok
- font sample carried run 2 buckets render through 0x1ed84 and 0x1ef6a: ok
- font sample source heading carries into first Courier row: ok
- font sample row continuation emits fresh source heading page record: ok
- font sample class-one row continuation emits fresh source heading page
  record: ok
- font sample first internal source group follows 0x1c334 row loop: ok
- font sample internal class-one source group follows 0x1c334 row loop: ok
- font sample non-internal source groups follow modes 0..2: ok
- font sample source headings 0..2 compose page records: ok
- font sample full printout source placement follows firmware order: ok
- font sample full printout rows reuse ROM sample byte runs: ok
- font sample full printout segments render through 0x1ed84 and 0x1ef6a: ok
- font sample resolver carries first two Courier rows: ok
- font sample source heading carries default plus first two Courier rows: ok
- named built-in first glyphs expose positioning offsets: ok
- 0x1569c activates concrete built-in candidate windows: ok
- 0x156de filters concrete active candidate windows: ok
- 0x14398 chooses concrete active built-in candidate: ok
- 0x14c64 dispatches concrete selected built-in font: ok
- 0x17708 font-ID selects concrete built-in candidate: ok
- 0x17708 font-ID non-selected exits preserve prior selection: ok
- font-ID non-selected exits keep prior visible rows: ok
- font-ID built-in selection feeds visible page-record rows: ok
- font-ID secondary built-in selection feeds visible SO page-record rows: ok
- font-ID secondary non-selected exits keep prior SO visible rows: ok
- 0x1519a filters concrete active candidates by height: ok
- 0x153c6 filters concrete active candidates by spacing and pitch: ok
- live parser symbol-set streams select non-Roman built-ins: ok
- parsed font-selection metrics feed concrete candidate filters: ok
- 0x13eb8 refresh carries parsed primary font selection to dispatch: ok
- 0x13eb8 refresh carries parsed secondary font selection to dispatch: ok
- 0xe65c refresh composes with font context bridge: ok
- 0x13eb8 transient and cache-hit exits avoid dispatch: ok
- 0x13eb8 no-dispatch exits keep prior visible rows: ok
- parsed font-selection stream writes primary font-state fields: ok
- parsed primary built-in font selection feeds visible page-record rows: ok
- inline primary font selection stream renders visible rows: ok
- primary symbol miss falls back before visible page-record rows: ok
- remembered primary symbol feeds visible page-record rows: ok
- remembered secondary symbol feeds visible SO page-record rows: ok
- live primary current-font RAM install feeds SI page-record rows: ok
- parsed primary selection current-font RAM feeds SI visible rows: ok
- parsed secondary built-in font selection feeds visible SO page-record rows:
  ok
- inline secondary font selection stream renders SO visible rows: ok
- non-Roman symbol streams select visible built-ins: ok
- live secondary current-font RAM install feeds SO page-record rows: ok
- parsed secondary selection current-font RAM feeds SO visible rows: ok
- secondary symbol miss falls back before visible SO page-record rows: ok
- 0x1ac0a/0x1af36 default-font table builders: ok
- 0x1b250 current-default candidate lookup: ok
- 0x1b50e current-default resolver scan and predicates: ok
- 0x1b250 real current-default candidate lookup: ok
- 0x1ab84 synthesized default-font search: ok
- 0x1ad66/0x1adaa/0x1ae7e default-font candidate search: ok
- symbol-set parser trace covers X and @ special cases: ok
- real default-table caller stream uses ROM-backed words: ok
- real final-@ default-table streams select visible built-ins: ok
- 0x1393a-modeled text source object fields: ok
- 0x12f2e-modeled short bucket object fields: ok
- 0x10084-modeled page-root allocation side effects: ok
- 0x10110 page-root initializer installs selected context slot: ok
- 0x10110 page-root initializer copies geometry fields: ok
- 0x1381c stream allocator chunks display-list storage: ok
- 0x1387c address-aware bucket allocation uses 0x1381c storage: ok
- 0x133aa address-aware rule-list insertion uses 0x1381c storage: ok
- 0x133aa no-room return preserves rule-list head: ok
- 0x136d2 address-aware fixed-list insertion uses 0x1381c storage: ok
- 0x136d2 no-room return preserves fixed-list head after search: ok
- addressed stream page record materializes through 0xff1e and 0x1ed84: ok
- 0x1eb2a/0x1ecd6 selects published record for render entry: ok
- 0x1ecd6 same-geometry render work reuse reaches render entry: ok
- 0x3144/0x7ec6/0x7712 page pool aliases feed scheduler cursor: ok
- 0x1958/0x1c04/0x1eea staged candidate reaches render scheduler: ok
- 0x2126/0x1a4c/0x2038 active pool copy window feeds engine rows: ok
- 0x0fa2/0x1db0/0x1e44 status feedback drives copy and done flag: ok
- 0xa620/0xa668/0xa6cc engine shadow and byte bridge: ok
- 0x1036/0x108e/0x123a wait-object scheduler handoff: ok
- 0x1144..0x11f8 scheduler trap handlers update wait objects: ok
- 0x1cf8/0x1e80/0x1ea8 wrapper dispatch selects engine variants: ok
- 0x1eba4/0x1ef6a active render loop advances or yields bands: ok
- addressed page-record writers share 0x1381c across chunk rollover: ok
- 0xd04a printable entry normalizes over-0xff and high-bit values: ok
- 0xd04a high-character flags and selected slot choose mask behavior: ok
- 0xd28a and 0xd6bc prechecks share continue reject and wrap decisions: ok
- 0xd824-modeled positioned text source fields: ok
- 0x1387c page-record bucket allocator reuses matching short object: ok
- 0x1387c page-record bucket allocator links new head when full: ok
- 0xd824-positioned short bucket object fields: ok
- 0xd824-modeled negative-overflow positioned source fields: ok
- 0xd824-negative-overflow short bucket object fields: ok
- 0xd3b2 and 0xd824 text queue no-room retry preserves source and rows: ok
- 0xd3b2 and 0xd824 segmented text queue no-room retry preserves source and
  rows: ok
- 0x14c64 dispatches selected inline/downloaded font: ok
- 0x17708 font-ID selects inline/downloaded candidate: ok
- font-ID inline/downloaded selection feeds visible page-record rows: ok
- font-ID primary inline/downloaded selection feeds visible page-record rows:
  ok
- 0x14e24-modeled inline/downloaded map entries: ok
- constructed inline/downloaded wide glyph maps through 0x1f0d2: ok
- 0xe860 reads inline +0x16 and offset-table +0x20 class bytes: ok
- constructed inline/downloaded segmented glyph maps through 0x1f1f0: ok
- constructed inline/downloaded segmented-wide glyph maps through 0x1f264: ok
- 0x1393a-modeled selected inline source object fields: ok
- selected inline source queues and renders through unflagged path: ok
- selected inline page-record object preserves context through 0x1edc6 bridge:
  ok
- 0x168dc-modeled font payload linear copy handles 0x1a58: ok
- 0x168dc-modeled font payload linear copy continuation state: ok
- 0x16942-modeled font payload split-plane copy layout: ok
- 0x16942-modeled font payload split-plane continuation state: ok
- 0x16942-modeled font payload split-plane copy handles 0x1a58: ok
- host-fetched downloaded character payload control reaches wide render: ok
- host-fetched downloaded payload-control object feeds 0x1ed84 and 0x1ef6a: ok
- host-fetched downloaded payload-control object preserves 0x1edc6 bridge
  contract: ok
- host-fetched payload-control downloaded glyph FF publishes page record: ok
- host-fetched even-span wide downloaded character renders through 0x1f0d2: ok
- host-fetched even-span downloaded glyph FF publishes rendered page record:
  ok
- host-fetched downloaded glyph composes with rule and raster through 0x1ef6a:
  ok
- even-span downloaded glyph rule raster FF publication renders page record:
  ok
- downloaded glyph byte-24 state handoff feeds following page handler: ok
- parser-driven downloaded glyph rule raster stream composes through 0x1ef6a:
  ok
- parser-driven downloaded glyph rule raster FF publishes page record: ok
- 0x15a18/0x11f96-modeled font payload command edge: ok
- 0x11774 ROM dispatch table routes font W streams to delayed handlers: ok
- 0x11774 ROM dispatch table routes chained font selection streams: ok
- 0x11774 ROM dispatch table routes ESC *c font-control chain: ok
- 0x15d0a-modeled font descriptor route: ok
- 0x15d0a descriptor grammar exits and handler matrix: ok
- 0x121cc/0x15d0a-modeled font descriptor command stream: ok
- font descriptor stream ties ROM parser dispatch to 0x15d0a routes: ok
- host-fetched font descriptor streams route through 0x15d0a: ok
- 0x16606 no-install exits clear stale continuation without payload writes: ok
- host-fetched 0x15d0a current-record resource object feeds fixed-record
  render: ok
- host-fetched 0x15d0a continuation resource object resumes fixed-record
  render: ok
- 0x15c4c failed resource resume releases fixed-record object: ok
- 0x17d7c releases extended fixed-record table with secondary refresh: ok
- 0x17d7c delegates bit-30 release to offset-table helper: ok
- 0x17d7c release reject exits preserve table and continuation state: ok
- 0x15c4c partial resource resumes update continuation state: ok
- host-fetched 0x15d0a split-plane continuation resource object resumes
  fixed-record render: ok
- 0x172c0-modeled font resource record scan statuses: ok
- 0x16c14-modeled downloaded font replacement bookkeeping: ok
- 0x16c14 routes installed font resource through 0x1bc38 slot: ok
- 0x16c14 allocation failure releases existing payload through 0x1887a: ok
- 0x1887a release variant matrix covers cleanup branches: ok
- 0x16c14-modeled downloaded font free-slot bookkeeping: ok
- 0x16c14-modeled downloaded font no-slot budget skip: ok
- 0x1bc38-modeled candidate insertion branches: ok
- 0x19dd2 optional-window change composes refresh helpers: ok
- 0x19dd2 modeled unchanged and status branch exits: ok
- 0x447a/0x4760 consume scheduler return differently: ok
- 0x1a2e4 font scan ignores scheduler return: ok
- 0x170be-modeled font payload record lookup: ok
- 0x17108-modeled current font record mark/count transfer: ok
- 0x17150-modeled current font record unmark/count transfer: ok
- 0x15a56-modeled assign font ID normalization: ok
- 0x16df6-modeled font-control dispatch mark/unmark and suppression: ok
- 0x16fae validation table semantic map covers staged and pass-through
  entries: ok
- 0x16fae-modeled font resource validation and symbol-byte staging: ok
- 0x16fae table-driven validation predicates populate staged header fields: ok
- 0x17362-modeled font resource setup type: ok
- 0x17026/0x1719c-modeled font resource allocation and header initialization:
  ok
- ESC )s80W resource stream installs 0x1719c payload through 0x16c14: ok
- ESC )s80W invalid resource type fails validation before allocation: ok
- ESC )s80W reversed resource range fails validation before allocation: ok
- ESC )s80W additional validation predicate failures skip allocation: ok
- resource payload stream ties ROM parser dispatch to 0x16c14 install: ok
- host-fetched resource payload stream installs selected 0x1719c font: ok
- host-fetched font control state drives resource payload stream: ok
- 0x16c14-installed 0x1719c payload dispatches as bit-30 resource form: ok
- 0x1719c-backed inline payload dispatches through 0x14c64: ok
- 0x16fae/0x1719c-backed inline payload maps, queues, and renders one fixed
  record: ok
- host-fetched 0x1719c payload metrics feed d4ac span rows: ok
- host-fetched 0x1719c payload metrics feed d8fc span rows: ok
- host-fetched resource header plus glyph payload renders offset-table
  downloaded glyph: ok
- 0x16fae/0x1719c-backed type-2 inline payload maps constructed compact
  renderer records: ok
- host-fetched type-2 0x1719c payload metrics feed d4ac and d8fc span rows: ok
- host-fetched type-1 0x1719c payload metrics feed d4ac and d8fc span rows: ok
- type-1 and type-2 resource headers accept downloaded glyph payload stream:
  ok
- type-1 and type-2 resource glyph FF publications render page records: ok
- type-1 and type-2 resource wide glyph FF publications render page records:
  ok
- type-1 and type-2 resource segmented glyph FF publications render page
  records: ok
- host-fetched metric variant changes d4ac gate and d8fc rows: ok
- host-fetched clamped metric variant changes d4ac gate and d8fc rows: ok
- host-fetched lower-bound metric variant suppresses d4ac and d8fc spans: ok
- host-fetched upper-bound metric variant keeps d4ac span but suppresses d8fc:
  ok
- legal descriptor metric value matrix drives d4ac and d8fc consumers: ok
- legal descriptor metric boundary values drive d4ac and d8fc consumers: ok
- legal descriptor metric extent fenceposts drive d4ac and d8fc consumers: ok
- legal descriptor metric range endpoints drive d4ac and d8fc consumers: ok
- legal descriptor metric mixed values drive d4ac and d8fc consumers: ok
- legal descriptor metric tight range values drive d4ac and d8fc consumers: ok
- legal descriptor metric low-nibble rounding drives d4ac and d8fc consumers:
  ok
- legal descriptor metric byte-boundary rounding drives d4ac and d8fc
  consumers: ok
- descriptor metric fields match across inline and resource contexts: ok
- 0x16498-backed downloaded character object renders segmented-wide compact
  row: ok
- downloaded character stream ties ROM parser dispatch to rendered object: ok
- host-fetched downloaded character stream reaches rendered object: ok
- host-fetched downloaded character object feeds 0x1ed84 and 0x1ef6a: ok
- host-fetched downloaded character object preserves 0x1edc6 bridge contract:
  ok
- host-fetched linear downloaded character stream renders through 0x168dc: ok
- host-fetched row-0x80 downloaded character remains short compact: ok
- 0x16b1a descriptor width helper emits only mode 1/2: ok
- downloaded glyph width-span matrix publishes and renders all main helpers:
  ok
- downloaded glyph width-byte boundary truncates page-record span: ok
- downloaded glyph wide-remainder matrix publishes and renders compact chunks:
  ok
- downloaded glyph segmented-wide matrix publishes and renders compact chunks:
  ok
- downloaded segmented-wide row-span cross-products render selected segment:
  ok
- downloaded segmented-wide high-row fallback renders selected segment: ok
- downloaded segmented-wide high-row even-span fallback renders selected
  segment: ok
- downloaded segmented-wide high-row span-31 fallback hits source boundary: ok
- downloaded segmented-wide high-row span-32 fallback renders selected
  segment: ok
- downloaded segmented-wide row-0x0182 span-31 fallback hits source boundary:
  ok
- downloaded segmented-wide row-0x0182 fallbacks render selected segment: ok
- downloaded segmented-wide row-0x01ff span-31 fallback hits source boundary:
  ok
- downloaded segmented-wide row-0x01ff fallbacks render selected segment: ok
- downloaded segmented-wide row-0x0281 span-31 fallback hits source boundary:
  ok
- downloaded segmented-wide row-0x0281 fallbacks render selected segment: ok
- downloaded segmented-wide high-row 0x02xx matrix renders selected segment:
  ok
- downloaded segmented-wide high-row 0x02xx span-31 matrix hits source
  boundary: ok
- downloaded segmented-wide high-row 0x03xx matrix renders selected segment:
  ok
- downloaded segmented-wide high-row 0x03xx span-31 matrix hits source
  boundary: ok
- downloaded segmented-wide high-row 0x04xx matrix renders selected segment:
  ok
- downloaded segmented-wide high-row 0x04xx oversized payload counts stop
  before renderer: ok
- downloaded segmented-wide high-row 0x05xx matrix renders selected segment:
  ok
- downloaded segmented-wide high-row 0x05xx oversized payload counts stop
  before renderer: ok
- downloaded segmented-wide high-row parser-limit matrix renders selected
  segment: ok
- downloaded segmented-wide high-row parser-limit oversized counts stop before
  renderer: ok
- downloaded segmented-wide row-byte boundary truncates page-record segments:
  ok
- 0x15b9a resumes downloaded-character continuation objects: ok
- 0x15b9a partial and failed resumes update continuation or release object: ok
- 0x16498 status-2 partial installs remain printable: ok
- 0x16498 replacement allocation failure partial and rejected downloaded
  character exits preserve state: ok
- host-fetched nonboundary short downloaded glyph FF publication renders page
  record: ok
- host-fetched rows-0x20 short downloaded glyph FF publication renders page
  record: ok
- host-fetched rows-0x40 short downloaded glyph FF publication renders page
  record: ok
- host-fetched segmented downloaded character renders through 0x1f1f0: ok
- segmented downloaded glyph composes with raster through 0x1ef6a: ok
- host-fetched rows-0x82 segmented downloaded glyph FF publication renders
  page record: ok
- host-fetched rows-0x102 downloaded glyph FF publication truncates
  page-record rows: ok
- downloaded glyph high-row truncation matrix preserves installed rows: ok
- downloaded glyph row-count matrix publishes and renders additional
  short/segmented counts: ok
- downloaded normal row-0x80 and segmented glyph FF publications render page
  records: ok
- host-fetched split-plane segmented downloaded character renders through
  0x1f1f0: ok
- split-plane segmented downloaded glyph composes with raster through 0x1ef6a:
  ok
- segmented downloaded glyph raster FF publications render page records: ok
- split-plane segmented downloaded glyph FF publication renders page record:
  ok
- host-fetched printable byte uses installed downloaded glyph page object: ok
- combined host-fetched font download stream prints installed glyph: ok
- combined font download FF publishes installed glyph page record: ok
- published downloaded glyph segmented buckets render across bands: ok
- 0x1eba4 scheduler band words render published downloaded glyph: ok
- host-fetched font control state drives descriptor and character streams: ok
- host-fetched font control stream feeds descriptor and character payload
  state: ok
- font control stream state feeds descriptor route and character payload: ok
- 0xd3b2-modeled unflagged source fields: ok
- 0x12f2e-modeled unflagged short bucket object fields: ok
- 0x1387c page-record unflagged short bucket object: ok
- addressed 0x12f2e selector-mode matrix allocates and renders all compact
  modes: ok
- 0x12f2e-modeled unflagged width byte selects compact mode bit: ok
- 0x1f0d2 renders wide inline compact payload row: ok
- 0x1f0d2 wide compact text splits current band and fallback rows: ok
- 0x12f2e-modeled unflagged tall inline bucket objects: ok
- 0x12f2e-modeled unflagged wide tall inline bucket objects: ok
- 0x1f264 renders segmented wide inline compact payload row: ok
- 0x1f264 segmented-wide compact text splits current band and fallback rows:
  ok
- 0x1f1f0 renders segmented inline compact payload row: ok
- 0x1f1f0 segmented compact text splits current band and fallback rows: ok
- 0xd3b2-modeled unflagged overflow source fields: ok
- 0x1393a-modeled tall text source object fields: ok
- 0x12f2e-modeled segmented bucket metadata: ok
- 0x12f2e-modeled segmented bucket objects: ok
- 0x1387c page-record segmented allocator places tall glyph buckets: ok
- 0x1387c page-record segmented allocator reuses tall glyph buckets: ok
- firmware-scanned tall built-in glyph target summary: ok
- compact text bucket object fixture metadata: ok
- compact text bucket object fixture rendered rows: ok
- 0x1f034 compact text splits current band and fallback rows: ok
- 0x1387c page-record queued short object renders reused entries: ok
- 0x1edc6 page-record bridge copies compact bucket and context slots: ok
- 0x1edc6 page-record bridge normalizes rule and fixed lists: ok
- 0x1edc6 bridge records render-record destination offsets: ok
- 0x1ed84 active page-record copy seeds render-record header words: ok
- 0x1ef86 render band setup computes remainder and destination base: ok
- 0x1efc2 bucket-chain dispatcher selects bucket and object classes: ok
- 0x1f812 segment-list object renders counted mask spans: ok
- 0x13386/0x133aa-modeled rectangle/rule list object and bridge normalization:
  ok
- 0x137a2/0x136d2-modeled fixed-rule list object and bridge normalization: ok
- 0x1f756 fixed-width list renders bridged +0x20 object: ok
- 0x12714 portrait text span flush queues segment-list span: ok
- 0x1354a portrait text span split queues adjacent buckets: ok
- 0x12714 landscape text span flush queues fixed-width span: ok
- 0x12714 landscape span inserts into nonempty fixed list: ok
- 0x12714 allocation failure publishes page and retries span: ok
- 0x10e68/0x10e22/0x10a40/0x10ae0 rectangle size commands update packed
  dimensions: ok
- 0x10898 ESC *c#P maps fill selectors and queues rule object: ok
- rectangle command stream queues chained ESC *c rule object: ok
- 0x11774 ROM dispatch table routes chained ESC *c rule stream: ok
- host-fetched rectangle rule stream preserves 0x1edc6 bridge contract: ok
- host-fetched rectangle rule feeds 0x1ed84 and 0x1ef6a: ok
- 0x1f446/0x1f596 renders solid black rectangle rule pixels: ok
- 0x1f596 carries solid rule remainder across render bands: ok
- 0x1f4e0 carries patterned rule remainder across render bands: ok
- 0x1f446 page-band walk assembles patterned rule rows: ok
- 0x1f446/0x1f4e0 renders gray selector pattern pixels: ok
- 0x1f4e0 renders gray and HP pattern selector matrix: ok
- 0x1f4e0 renders sub-byte shifted HP pattern rule pixels: ok
- 0x10b80 rectangle fill clips negative left edge before queueing: ok
- 0x10b80 rectangle fill clips right/top/bottom edges and ignores off-page
  fills: ok
- 0x10d22 rectangle/rule no-room retry finalizes root then retries: ok
- rectangle parser trace feeds no-room retry path: ok
- 0x10808 ESC *t#R selects raster mode and scale thresholds: ok
- 0x1075a ESC *r#A seeds raster baseline from cursor or left edge: ok
- 0x1075a raster origin source follows orientation: ok
- 0x107fa ESC *r#B clears raster active flag only: ok
- parser-derived ESC *t300R / ESC *r1A state queues mode-0 raster row: ok
- 0x105d0-modeled raster transfer skip and cap gate: ok
- 0x11774 ROM dispatch table routes raster stream to delayed transfer: ok
- modeled raster command stream parses ESC *t300R / ESC *r1A / ESC *b4W
  payload boundary: ok
- modeled raster command stream queues and renders ESC *b4W payload: ok
- modeled raster command stream bridges queued ESC *b4W page object: ok
- raster transfer ensures page root before queueing row object: ok
- raster stream ties parser dispatch to queued page object: ok
- host-fetched raster stream reaches parser and queued pixels: ok
- host-fetched raster stream preserves 0x1edc6 bridge contract: ok
- raster payload reader normalizes 0xdace controls before queueing pixels: ok
- host-fetched raster control payload normalizes before queueing pixels: ok
- modeled raster command stream applies 0x105d0 byte-count cap: ok
- modeled raster command stream queues inclusive page-extent row: ok
- modeled raster command stream drains beyond-extent transfer without
  queueing: ok
- modeled raster command stream drains negative-row transfer and advances: ok
- raster parser trace feeds capped and drained transfer gates: ok
- host-fetched raster gate stream reaches capped and drained paths: ok
- modeled raster command stream selects 150-dpi mode-1 state: ok
- modeled raster command stream queues and renders 150-dpi mode-1 payload: ok
- modeled raster command stream selects 100-dpi mode-2 state: ok
- modeled raster command stream queues and renders 100-dpi mode-2 payload: ok
- modeled raster command stream selects 75-dpi mode-3 state: ok
- modeled raster command stream queues and renders 75-dpi mode-3 payload: ok
- raster mode streams tie ROM parser dispatch to modeled queued objects: ok
- host-fetched raster mode streams reach parser and rendered rows: ok
- host-fetched raster mode streams feed 0x1ed84 and 0x1ef6a: ok
- modeled raster command stream queues consecutive ESC *b#W rows: ok
- modeled raster command stream renders consecutive queued rows: ok
- raster multi-row parser trace feeds consecutive queued objects: ok
- host-fetched raster multi-row stream reaches consecutive queued rows: ok
- modeled raster command stream parses ESC *rB and re-enables resolution
  changes: ok
- raster end parser trace feeds active-clear and resolution re-enable: ok
- host-fetched raster end stream clears active state and re-enables
  resolution: ok
- raster active resolution parser trace preserves current mode: ok
- host-fetched active raster resolution stream preserves current mode: ok
- modeled raster command stream accepts lowercase same-group resolution
  chaining: ok
- host-fetched raster chained resolution stays in same parser family: ok
- modeled raster command stream defers lowercase ESC *b w payload until
  uppercase terminator: ok
- raster chained transfer parser trace preserves lowercase delayed record: ok
- host-fetched raster chained transfer preserves lowercase delayed record: ok
- host-fetched raster multi-row and chained streams preserve 0x1edc6 bridge
  contract: ok
- host-fetched raster streams feed 0x1ed84 and 0x1ef6a: ok
- 0x13070/0x13250 raster row queues encoded-span object: ok
- 0x1f88e mode-0 raster object renders queued literal row: ok
- 0x1edc6 page-record bridge preserves queued raster object: ok
- 0x13070/0x13250 raster row queues non-byte-aligned encoded-span object: ok
- 0x1f88e mode-0 raster object renders sub-byte shifted literal row: ok
- 0x13070/0x13250 raster mode-1 row queues encoded-span object: ok
- 0x1f88e mode-1 raster object expands queued bytes into two rows: ok
- 0x13070/0x13250 raster mode-2 row queues encoded-span object: ok
- 0x1f88e mode-2 raster object expands queued byte pair into three rows: ok
- 0x13070/0x13250 raster mode-2 row queues non-byte-aligned encoded-span
  object: ok
- 0x1f88e mode-2 raster object renders sub-byte shifted expanded rows: ok
- 0x13070/0x13250 raster mode-2 row queues band-clipped encoded-span object:
  ok
- 0x1f88e mode-2 raster object clips current-band rows and continues in
  fallback buffer: ok
- 0x13070/0x13250 raster mode-3 row queues encoded-span object: ok
- 0x1f88e mode-3 raster object expands queued bytes into four rows: ok
- 0xd824-positioned compact text rendered rows: ok
- bridged compact text and rule objects compose into one page band: ok
- bridged text, rule, and raster layers compose into one page band: ok
- 0x1ef6a render entry composes bucket, rule, and fixed-width lists in call
  order: ok
- 0x1ef6a page-band walk merges text raster and crossing rule: ok
- 0xd824-negative-overflow compact text rendered rows: ok
- single printable byte stream builds positioned compact text object: ok
- single printable byte stream renders expected rows: ok
- two printable byte stream combines compact text entries: ok
- two printable byte stream renders advanced glyph rows: ok
- line-printer flagged HMI metric via 0x10550: ok
- 0xca8c ESC &k#H stores packed HMI for in-range absolute values only: ok
- two printable byte stream with line-printer HMI renders subbyte entry: ok
- two printable byte stream with line-printer HMI renders subbyte rows: ok
- plain printable parser trace feeds page-record queue: ok
- font sample run 1 prefix crosses page-record render entry: ok
- font sample run 1 full row spans compact buckets: ok
- font sample run 2 full row spans compact buckets: ok
- ESC )s#W validation failures preserve following printable output: ok
- 0x16498 no-install exits preserve following printable output: ok
- HMI parser trace feeds page-record queue: ok
- SI/SO parser trace selects page-record text contexts: ok
- transparent data parser trace feeds page-record queue: ok
- ESC Y display-functions stream reaches page-record output: ok
- ESC Y display-functions filter-on routes controls as printable: ok
- transparent non-0x58 probe byte reaches page-record output: ok
- transparent data control payloads advance through fixed-space path: ok
- transparent default-filtered control enters unflagged fixed-record path: ok
- transparent nonzero filters route controls through printable path: ok
- transparent nonzero high-control byte queues tall glyph bucket: ok
- transparent nonzero high-control interior samples remain printable: ok
- transparent nonzero high-control upper bound remains printable: ok
- transparent secondary high-control byte enters segmented page-record path:
  ok
- transparent secondary segmented render prefix exposes source boundary: ok
- transparent secondary segment-57 continuation policies diverge after
  verified bytes: ok
- mixed printable/control stream applies CR+LF before second glyph: ok
- mixed printable/control stream renders post-CR glyph rows: ok
- mixed printable/control page-record stream queues through 0x1387c: ok
- mixed printable/control page-record bridge renders post-CR glyph rows: ok
- live CR span flush materializes 0x12714 page object: ok
- left-margin parser span flush materializes 0x12714 page object: ok
- vertical-cursor parser span flush materializes 0x12714 page object: ok
- ESC 9 clear margins feeds CR and page-record output: ok
- ESC = half-line feed reaches shifted page-record output: ok
- ESC &d underline selector materializes span output: ok
- flagged printable d8fc low-watermark flush renders span: ok
- unflagged printable d4ac low-watermark flush renders span: ok
- d4ac and d8fc span consumer branch family controls flush output: ok
- mixed printable/control parser trace feeds page-record queue: ok
- host-fetched mixed control stream reaches parser and page-record render: ok
- LF parser trace feeds page-record queue: ok
- HT/BS parser trace feeds page-record queue: ok
- margin command parser trace feeds page-record queue: ok
- right margin command parser trace feeds page-record queue: ok
- chained margin command parser trace feeds page-record queue: ok
- cursor position parser trace feeds page-record queue: ok
- horizontal decipoint parser trace feeds page-record queue: ok
- vertical cursor position parser trace feeds page-record queue: ok
- vertical decipoint parser trace feeds page-record queue: ok
- dot position parser trace feeds page-record queue: ok
- chained cursor position parser trace feeds page-record queue: ok
- vertical layout parser trace feeds page-record queue: ok
- perforation skip parser trace feeds page-record queue: ok
- cursor stack parser trace feeds page-record queue: ok
- host-fetched direct text/control streams reach page-record render: ok
- host-fetched direct text/control streams preserve 0x1edc6 bridge contract:
  ok
- host-fetched direct text/control streams feed 0x1ed84 and 0x1ef6a: ok
- host-fetched cursor-row compact text splits at 0x783a20 boundary: ok
- host-fetched text plus rectangle page record feeds 0x1ed84 and 0x1ef6a: ok
- host-fetched alternate rectangle selectors feed full page records: ok
- host-fetched rectangle selector matrix feeds full page records: ok
- addressed text plus rectangle stream matches page-record output: ok
- host-fetched text rectangle and raster page record feeds 0x1ed84 and
  0x1ef6a: ok
- addressed text rectangle raster stream matches page-record output: ok
- addressed text rectangle raster publication renders rows: ok
- published text rectangle and raster page record feeds 0x1ed84 and 0x1ef6a:
  ok
- host-fetched text rectangle raster FF publishes rendered page record: ok
- addressed text rectangle raster FF publishes rendered page record: ok
- addressed text/rule/raster field groups reach publication and render entry:
  ok
- host-fetched text rectangle multi-row raster FF publishes rendered page
  record: ok
- addressed text/rule/multi-row raster publication preserves bucket chain: ok
- 0x11774 parser path routes mixed publication streams: ok
- 0x11774 parser path routes geometry publication streams: ok
- 0xeef0 ESC &l#X stores absolute clamped copy count: ok
- mixed printable/reset stream publishes page root after text: ok
- mixed printable/reset stream keeps pre-reset text rows renderable: ok
- mixed printable/reset page-record stream queues through 0x1387c before
  reset: ok
- mixed printable/reset page-record bridge keeps pre-reset rows renderable: ok
- mixed printable/reset page-record finalization publishes bridged record: ok
- addressed printable reset publishes rendered page record: ok
- addressed printable FF publishes rendered page record: ok
- mixed printable/reset publication records 0xff1e pool header defaults: ok
- 0xff1e-modeled publication copies status and environment header fields: ok
- mixed printable/FF page-record stream publishes queued text: ok
- mixed printable/FF page-record finalization publishes bridged record: ok
- mixed printable/paper-source page-record stream publishes queued text: ok
- mixed printable/copies/FF stream publishes copy count: ok
- mixed printable/page-size page-record stream publishes queued text before
  geometry change: ok
- mixed printable/page-size page-record finalization publishes bridged record:
  ok
- mixed page-length stream refreshes cursor before printable page-record
  queue: ok
- 0x12cfe ESC &l#W loads vertical forms control state: ok
- mixed VFC definition stream consumes payload before printable page-record
  queue: ok
- mixed VFC lowercase delayed record survives until uppercase W: ok
- mixed VFC channel jump stream moves cursor before printable page-record
  queue: ok
- mixed VFC before-top channel jump normalizes start line before printable: ok
- mixed VFC before-top target-after-text skips publication: ok
- mixed VFC start-after-text skips wrap and publication: ok
- mixed VFC start-after-text wraps to table hit before printable: ok
- mixed VFC start-after-text wraps to bottom recovery before printable: ok
- mixed VFC selector-zero top-of-form no-op reaches printable page-record
  queue: ok
- mixed VFC selector-zero start-after-text returns to top: ok
- mixed VFC selector-zero page-eject publishes old page before fresh
  printable: ok
- mixed VFC wrap-hit publishes old page before fresh printable: ok
- mixed VFC wrap-no-hit publishes old page and returns to top: ok
- mixed VFC target-after-text recovers near top before fresh printable: ok
- 0x1280a VFC alternate high-start recovery entries: ok
- mixed printable/orientation page-record stream publishes queued text before
  landscape change: ok
- mixed printable/orientation page-record finalization publishes bridged
  record: ok
- addressed page geometry publications render page records: ok
- addressed paper-source and copies publications render page records: ok
- publication streams tie parser handlers to page-record publication boundary:
  ok
- host-fetched publication streams reach parser and published rows: ok
- host-fetched reset publication preserves 0xff1e pool header defaults: ok
- host-fetched FF geometry and paper-source publications preserve 0xff1e pool
  header defaults: ok
- host-fetched copies publication preserves 0xeef0 pool header word: ok
- host-fetched publication streams preserve 0x1edc6 bridge contract: ok
- published page records feed 0x1ed84 and 0x1ef6a render entry: ok
