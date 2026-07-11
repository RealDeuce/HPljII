# IC30/IC13 Host Byte Fetch Flow

Generated from routine `0x0000a904`, its local branches through `0x0000abf0`,
and absolute-call/state-reference scans of the verified firmware image. This
report tracks the normalized byte source that feeds the PCL parser and
raster/download payload readers. Names remain provisional where MMIO register
roles are not board-confirmed.

## Source Priority

| Order | Entry/condition | Firmware behavior | Reproduction meaning |
| ---: | --- | --- | --- |
| 1 | `0x7821cd != 0` at `0xa904` | branches to `0xaa88`, sets `0x7821cc`, calls `0x10cc(0x780202)`, clears `0x7821cc`, then retries `0xa904` | service/error work can run before any byte source is consumed |
| 2 | `0x780e66 != 0` and `0x780e3b != 0` | returns `D7 = -1` immediately | callers must treat negative `D7` as no-byte/end/error, as several payload readers already do |
| 3 | `0x783e8c != 0` | reads byte from `--0x783e8e`, decrements `0x783e8c`, returns | first stacked pushback/source buffer has priority over live hardware input |
| 4 | `(*0x782d76)+4 != 0` | if field is not `-1`, calls `0x9f6a` and returns; if field is `-1`, clears it, calls `0xe22c`, and retries | current data-chain source can supply bytes or signal a chain transition before other buffers |
| 5 | `0x783e76 != 0` | reads byte from `--0x783e78`, decrements `0x783e76`, returns | second stacked byte source is consumed after the data-chain source |
| 6 | `0x780e40 == 0` and `0x783e54 != 0` | reads byte from ring pointer `0x783e56`, wraps after `0x783e53` back to `0x783a4c`, decrements `0x783e54`, returns | buffered ring input is used before direct hardware fallback when direct mode is not selected |
| 7 | `0x780e40 == 1` | enters direct path `0xa9f0` using short MMIO registers `0x8e01`, `0x8801`, `0x8c01`, plus `0xa601`/`0xaa01` handshakes | one hardware input backend polls status bit 4, reads one byte, waits for acknowledge bit 0 to clear, then toggles control lines |
| 8 | `0x780e40 != 0 && != 1` | enters direct path `0xaaa6` using long MMIO registers `0xfffee005`, `0xfffee001`, `0xfffee009` | alternate hardware input backend polls ready/error bits, reads one byte, and updates a separate control shadow |

## Direct Hardware Input Modes

| Selector | Status/data/control evidence | Success path | Timeout/error path |
| --- | --- | --- | --- |
| `0x780e40 == 1` | `0xa9f4` reads `0x8e01` bit `0x10`; `0xaa06` reads data byte from `0x8801`; `0xaa26` waits for `0x8c01` bit 0 to clear; `0xaa3a..0xaa64` writes `0xa601` and `0xaa01` from shadow `0x7828fa` | byte is masked to 8 bits in `D7`; `0x1a` is reported through `0x9ec0` and preserved as `0x1a`; handshake clears `0x7828ec` and `0x7821c4` | if `0x8e01.4` is not seen before `D0=0x2710` expires, branches through service helper at `0xaa88` and retries |
| `0x780e40 != 0 && != 1` | `0xaae4` reads `0xfffee005`; bit 0 means data ready; bits 7/6 are error/status cases; `0xab08` reads data byte from `0xfffee001`; `0xab2e..0xab44` writes shadow `0x7828fb` to `0xfffee009` | byte is masked to 8 bits in `D7`; `0x1a` is reported through `0x9ec0` and preserved as `0x1a`; success sets `0x7828ec=1`, sets control-shadow bit 6, and clears `0x7821c4` | bit 7 ORs `0x80` into `0x780e2e`; bit 6 ORs `0x40` into `0x780e2e`; timeout or status/error branches through service helper at `0xab70` and retries |
| cleanup helper `0xab8e` | called from `0x35de` after helper `0xa39a` returns zero; mode 1 toggles `0xaa01`/`0xa601` from `0x7828fa`, mode 2 applies `bclr #0x40,D0` to `0x7828fb` before writing `0xfffee009` | normalizes handshake state after external service code | not a byte source by itself |

## Callers and Payload Consumers

Direct absolute `JSR 0xa904` callers: `0x00da9a`, `0x00daa6`, `0x00dab2`,
`0x00dace`, `0x00dada`, `0x012142`, `0x012152`, `0x0124bc`, `0x0124cc`,
`0x012582`, `0x012592`, `0x0138fa`, `0x013904`, `0x0168dc`, `0x0168fe`,
`0x016960`, `0x01697a`, `0x0169ca`, `0x0169e0`.

The table below classifies every direct caller found in the verified firmware
image.

| Caller | Role | Byte handling | End/control handling |
| ---: | --- | --- | --- |
| `0x00da9a` | ESC-aware parser byte wrapper | First fetch for normal parser input; returns non-ESC bytes directly. | No explicit `D7=-1` test here; caller loop decides parser end/state. |
| `0x00daa6` | ESC wrapper display-functions probe | Second fetch after ESC; checks for `?` display-function prefix. | No explicit `D7=-1` test. |
| `0x00dab2` | ESC wrapper display-functions probe | Third fetch after `ESC ?`; loops on `0x11`, otherwise reports the byte through `0x9ec0` and returns ESC. | No explicit `D7=-1` test. |
| `0x00dace` | `0x1a 0x58` control probe | Fetches a byte and, if it is `0x1a`, fetches a second byte looking for `0x58`. | On `0x1a 0x58`, calls `0xd99a` and returns `D7=0`; otherwise leaves the fetched byte path unchanged. |
| `0x00dada` | `0x1a 0x58` control probe | Second byte of the `0xdace` probe. | Only the exact `0x58` second byte triggers `0xd99a` and normalized zero. |
| `0x012142` | alternate/data text append reader | After seeding `ESC Y`, fetches bytes, appends through `0xe002`, and treats `ESC ... Z` as an end marker. | Stops on `D7=-1`; `0x1a 0x58` calls `0xd99a` and appends `0x7f`. |
| `0x012152` | alternate/data text append reader | Second byte of the local `0x1a 0x58` probe in the `ESC Y` append reader. | Only exact `0x58` normalizes the pair to appended `0x7f`. |
| `0x0124bc` | bounded text repeat reader | Reads up to counter `D4`, routes printable bytes through `0xd04a`, and filters control ranges through `0xd0f0` depending on active symbol state. | Stops on `D7=-1`; `0x1a 0x58` calls `0xd99a` and substitutes `0x7f` before text handling. |
| `0x0124cc` | bounded text repeat reader | Second byte of the bounded reader's `0x1a 0x58` probe. | Only exact `0x58` normalizes to `0x7f`. |
| `0x012582` | ESC-terminated text repeat reader | Reads text until `D7=-1` or an `ESC ... Z` terminator, routes printable bytes through `0xd04a`, and calls `0xf054` after CR. | Stops on `D7=-1`; `0x1a 0x58` calls `0xd99a` and substitutes `0x7f`. |
| `0x012592` | ESC-terminated text repeat reader | Second byte of the ESC-terminated reader's `0x1a 0x58` probe. | Only exact `0x58` normalizes to `0x7f`. |
| `0x0138fa` | raster payload copy reader | Copies normalized host bytes into raster object storage for delayed transfer handler `0x105d0`. | Uses the same local `0x1a 0x58` probe shape; negative `D7` ends/drains through the raster reader status path. |
| `0x013904` | raster payload copy reader | Second byte of the raster copy `0x1a 0x58` probe. | Exact `0x58` calls `0xd99a` and stores normalized zero. |
| `0x0168dc` | linear downloaded-font payload reader | Copies host bytes to `A4`, decrements payload budget `0x783140`, and saves continuation state when the current copy window expires. | `0x1a 0x58` calls `0xd99a` and stores zero; negative `D7` returns failure status. |
| `0x0168fe` | linear downloaded-font payload reader | Second byte of the linear reader's `0x1a 0x58` probe. | Only exact `0x58` normalizes to stored zero. |
| `0x016960` | split-plane downloaded-font prefix reader | Copies prefix-span bytes to `A4` for odd-width split-plane glyph rows. | `0x1a 0x58` calls `0xd99a` and stores zero; negative `D7` returns failure status. |
| `0x01697a` | split-plane downloaded-font tail reader | Copies one trailing byte per row to `A3` after the prefix plane. | `0x1a 0x58` calls `0xd99a` and stores zero; negative `D7` returns failure status. |
| `0x0169ca` | split-plane downloaded-font prefix reader | Second byte of the prefix-plane `0x1a 0x58` probe. | Only exact `0x58` normalizes to stored zero. |
| `0x0169e0` | split-plane downloaded-font tail reader | Second byte of the tail-plane `0x1a 0x58` probe. | Only exact `0x58` normalizes to stored zero. |

## State Reference Scan

| Address | Current role | Longword literal references |
| ---: | --- | --- |
| `0x007821cd` | fetch blocked / service-needed flag tested before all sources | `0x002f5a`, `0x004246`, `0x0044a2`, `0x006216`, `0x006332`, `0x006566`, `0x006738`, `0x007136`, `0x007222`, `0x00a906` |
| `0x00780e66` | buffer-source bitfield; bits are cleared as stacked sources drain | `0x00432e`, `0x006238`, `0x009f1e`, `0x009f5a`, `0x00a910`, `0x00a928`, `0x00a950`, `0x00a9a4`, `0x00e28e`, `0x00e37e`, `0x00e3dc`, `0x00e458`, `0x00e4ac`, `0x00e5d6` |
| `0x00780e3b` | forces immediate `D7=-1` return when `0x780e66` is set | `0x004326`, `0x004334`, `0x006230`, `0x00623e`, `0x009eca`, `0x00a91a`, `0x0117de`, `0x0117ea` |
| `0x00783e8c` | first LIFO byte count | `0x00318a`, `0x007326`, `0x009f2a`, `0x009f3a`, `0x009f42`, `0x00a92e`, `0x00a946` |
| `0x00783e8e` | first LIFO byte pointer; bytes are read with predecrement | `0x0031ce`, `0x009f48`, `0x009f4e`, `0x00a938`, `0x00a940` |
| `0x00782d76` | current data-chain/control pointer; field `+4` selects helper `0x9f6a` or end marker | `0x00732e`, `0x009ee2`, `0x009f74`, `0x00a956`, `0x00cd90`, `0x00dd48`, `0x00e010`, `0x00e154`, `0x00e1ee`, `0x00e236`, `0x00e27e`, `0x00e3ce`, `0x00e426`, `0x00e4e8`, `0x00e5aa` |
| `0x00783e76` | second LIFO byte count | `0x003184`, `0x00731e`, `0x009eee`, `0x009efe`, `0x009f06`, `0x00a982`, `0x00a99a` |
| `0x00783e78` | second LIFO byte pointer; bytes are read with predecrement | `0x0031c4`, `0x009f0c`, `0x009f12`, `0x00a98c`, `0x00a994` |
| `0x00783e54` | ring-buffer byte count | `0x00317e`, `0x007316`, `0x00784c`, `0x00a6fc`, `0x00a772`, `0x00a864`, `0x00a9b4`, `0x00a9dc` |
| `0x00783e56` | ring-buffer read pointer | `0x003194`, `0x00a9c0`, `0x00a9d6` |
| `0x00780e40` | direct hardware input mode selector | `0x00302a`, `0x003086`, `0x00349c`, `0x00350c`, `0x0035a8`, `0x0035f6`, `0x00362c`, `0x003696`, `0x0042d4`, `0x005434`, `0x006086`, `0x00609c`, `0x0060a4`, `0x0072dc`, `0x0072fa`, `0x00a034`, ... (32 total) |
| `0x00780e2e` | alternate direct-input status/error accumulator | `0x001e6a`, `0x001f7e`, `0x003458`, `0x0036f4`, `0x003ce4`, `0x004366`, `0x00626e`, `0x00789c`, `0x0078ce`, `0x007922`, `0x007948`, `0x007970`, `0x007998`, `0x0079c2`, `0x007ab8`, `0x007b26`, ... (48 total) |
| `0x007828ec` | direct-input handshake state byte | `0x00a348`, `0x00aa52`, `0x00aad8`, `0x00ab48`, `0x00abac`, `0x00abd6` |
| `0x007821c4` | direct-input timeout/service state cleared after successful handshakes | `0x0031ba`, `0x003a08`, `0x003a14`, `0x00aa6c`, `0x00aa7e`, `0x00ab4e` |
| `0x007821cc` | set while service helper `0x10cc(0x780202)` runs before retrying fetch | `0x00648e`, `0x00650a`, `0x009c44`, `0x009c62`, `0x00aa8c`, `0x00aa9e`, `0x00ab74`, `0x00ab86` |
| `0x007828fa` | `0x8e01/0x8801/0x8c01` mode control shadow written to `0xaa01` | `0x00026a`, `0x002d7c`, `0x002d8e`, `0x00a24a`, `0x00a260`, `0x00a27c`, `0x00a292`, `0x00a2d6`, `0x00a2e8`, `0x00a35e`, `0x00a364`, `0x00a7bc`, `0x00a7d0`, `0x00aa42`, `0x00ab9c` |
| `0x007828fb` | `0xfffee005/0xfffee001` mode control shadow written to `0xfffee009` | `0x00a302`, `0x00a30a`, `0x00a31a`, `0x00a32a`, `0x00a330`, `0x00a384`, `0x00a38a`, `0x00aac2`, `0x00aad2`, `0x00ab30`, `0x00ab40`, `0x00abdc`, `0x00abec`, `0x00acbc`, `0x00acc4`, `0x00accc`, ... (18 total) |

## Current Reproduction Contract

- A byte-stream emulator can feed parser/imaging work above `0xa904` by
  returning normalized `D7` bytes in the same order as the priority table,
  while preserving `D7=-1` as a no-byte/end/error return for callers that test
  it. `tools/render_fixture_harness.py` now has executable `0xa904`
  source-priority fixtures covering the no-byte return, service retry, first
  LIFO, data-chain end retry, second LIFO, ring-buffer mode, and both direct
  hardware modes including direct-mode `0x1a` reporting and mode-2
  control-shadow bit 6; it also feeds ring-buffer bytes for `ESC &k1G!\r!`
  through the ROM parser trace, page-record queue, `0x1edc6` bridge, and final
  rendered rows, and feeds the primary `ESC *t300R` / `ESC *r1A` / `ESC *b4W`
  raster stream through the same `0xa904` ring source before the
  parser/delayed-transfer/page-record/bridge/render boundary.
- Exact host-interface emulation still needs board/manual correlation for
  `0x8e01/0x8801/0x8c01`, `0xa601/0xaa01`, and
  `0xfffee005/0xfffee001/0xfffee009`; current ROM evidence only proves the
  polling, data, handshake, and status-bit behavior.
- Both direct modes special-case input byte `0x1a` through `0x9ec0`, and
  higher-level payload readers also interpret `0x1a 0x58` by calling `0xd99a`;
  byte-stream reproduction must preserve that control path rather than
  treating all payload bytes as opaque.
- All 19 direct `0xa904` call sites are now classified. Parser wrapper callers
  can pass `D7=-1` upward without a local stop test, text repeat readers stop
  on it, raster and font payload readers treat it as an end/error status, and
  `0x1a 0x58` is normalized differently by consumer family: `0xdace` returns
  zero, text repeat readers substitute `0x7f`, and raster/font payload readers
  store zero.
- Font payload reader `0x168dc` copies linear downloaded-font bytes to `A4`,
  decrements byte budget `0x783140` only for stored payload bytes, and saves
  continuation state in `0x7827c6/0x7827ca/0x7827d2` when the budget expires.
  Reader `0x16942` handles split odd-width glyph planes: `A4` receives `rows *
  prefix_span` bytes, `A3 = A4 + rows * prefix_span` receives one trailing
  byte per row, and continuation state also records `0x7827ce`, `0x7827d6`,
  and `0x7827d8`. `0x172c0` scans 10-byte current downloaded-font records
  under `0x782640..0x782776`, returning existing/free/full statuses; `0x16c14`
  uses that result to replace an existing payload through `0x1887a`, clear
  matching continuation state, or install a new payload and update candidate
  counters/cursors. `0x170be` maps a low-24-bit payload pointer back to a
  current-record slot and id; `0x17108` sets record flag bit 6 and transfers a
  count from `0x782782` to `0x782786` for an unmarked current payload record;
  `0x17150` clears that bit and transfers the count back. `0x15a56` normalizes
  the current font id from `ESC *c#D`, and `0x16df6` dispatches `ESC *c#F`
  values while suppressing values `0`, `1`, `2`, `3`, and `6` when `0x782a92
  == 2`. `0x16fae` walks the validation table at `0x16eae`, then copies up to
  16 optional symbol bytes through `0x1599c` into `0x782842` and stores the
  count at `0x782856`; `0x17362` sets staged type byte `+0x0c` and `0x7827ba`,
  `0x17026` stages record type `0x15` and allocation size `((0x7827ba << 2) +
  0x9b) >> 6`, and `0x1719c` copies the sparse staged header plus optional
  symbol bytes into the allocated record. `tools/render_fixture_harness.py`
  now has executable fixtures for both readers, record
  bookkeeping/lookup/marking/unmarking, font-id/control dispatch, `ESC )s80W`
  resource-payload command restoration, validation/symbol-byte staging,
  table-driven staged-header predicate side effects, payload-backed inline
  map/render, type-2 payload-backed wide/segmented fixed-record rendering, and
  allocation/header initialization, including `0x1a 0x58` handling,
  continuation checkpoints, replacement/free-slot updates, no-slot budget
  skip, count transfer, validation failure, zero-budget validation,
  table-driven predicate clamps, payload-backed inline map/render, and
  optional symbol-byte append offsets.
