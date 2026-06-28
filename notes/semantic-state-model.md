# Semantic State Model

This file composes broad-enough ROM clusters into renderer-facing state
concepts. It complements the low-level ledger in
`notes/reverse-engineering-ledger.md`; it does not replace address-level
notes, disassembly windows, or executable fixtures.

## Host Byte Fetch And Data-Chain Input

Status: anchored as the normalized byte-source boundary feeding the main
parser and payload readers. Physical interface names for the two direct
hardware register banks still need board/manual correlation, but the
firmware priority order and state side effects are executable fixtures.

Concept: `0xa904` is the byte-source multiplexer. It returns the next
normalized byte in `D7`, or `-1` when a no-byte gate wins. It is used by
the main parser, delayed payload handlers, transparent text, macro
replay, raster payload readers, and font download streams. Higher-level
byte-stream reproduction should model all input as one of these sources
before parser dispatch.

### Field Groups

- Canonical byte sources:
  - first pushback stack: `0x783e8c` count and `0x783e8e` pointer.
  - active data-chain source: `0x782d76` points to the current frame;
    frame `+4 == -1` triggers end transition through `0xe22c`.
  - second pushback stack: `0x783e76` count and `0x783e78` pointer.
  - ring buffer: `0x783e54` count, `0x783e56` read pointer, and
    `0x783e5a` write pointer, wrapped between `0x783a4c` and
    `0x783e53`. `0xa6cc`/`0xa846` write this source before `0xa904`
    drains it.
  Evidence: disassembly `0xa92c..0xa9e0`; fixtures
  `0xa904 services pending work then prefers first LIFO source`,
  `0xa904 data-chain end marker retries before second LIFO source`, and
  `0xa904 buffered ring source wins before direct hardware in mode 0`,
  plus `0xa620/0xa668/0xa6cc engine shadow and byte bridge`.
- Canonical direct hardware sources:
  - mode `0x780e40 == 1`: status byte `0x8e01`, data byte `0x8801`,
    wait/ack byte `0x8c01`, handshake outputs `0xa601` and `0xaa01`.
  - alternate nonzero mode: status byte `0xfffee005`, data byte
    `0xfffee001`, handshake/control byte `0xfffee009`.
  Evidence: disassembly `0xa9e2..0xaa86` and `0xaaa6..0xab8a`;
  fixtures
  `0xa904 direct mode 1 preserves 0x1a and clears handshake state` and
  `0xa904 direct mode 2 reads ready byte and sets control-shadow bit 6`.
- Canonical alternate ring bridge:
  - `0xa6cc` reads status byte `0xfffe0001` and data byte `0xfffe0003`
    when `0x780e40 == 0`. Ready status bit 0 writes the ring unless a
    full-buffer service path wins; status bits `0x70` write escape bytes
    `0x1a,0x58` when capacity remains.
  Evidence: disassembly
  `generated/disasm/ic30_ic13_a801_a601_io_00a4e8.lst`
  `0xa6cc..0xa810` and fixture
  `0xa620/0xa668/0xa6cc engine shadow and byte bridge`.
- Derived/cache bridge fields:
  - ring capacity is derived as `0x400 - 0x783e54` at `0xa6f4`.
  - `0x783e5e` is the low-water threshold. When capacity is less than or
    equal to it, `0xa726..0xa73c` sets warning bit `0x780e2a.1`,
    marks service pending in `0x783e61`, and halves the threshold.
  - `0x783e62` is the sequence-dispatch cursor used by `0xa86a`.
    Status-escape paths reset it to table `0xa8a4`.
  Evidence: fixture low-water and status-escape cases in
  `0xa620/0xa668/0xa6cc engine shadow and byte bridge`.
- Firmware bookkeeping:
  - `0x7821cd`: service-needed flag checked before all byte sources.
  - `0x7821cc`: service-in-progress flag set around helper `0x10cc`.
  - `0x780e66`: source/pending flags. Observed bit roles are bit 3 for
    the no-byte gate set with `0x780e3b` by `0x4322` / `0x622c`, bit 2 for
    first pushback stack bytes appended by `0x9ec0`, bit 1 for active
    data-chain frames, and bit 0 for second pushback stack bytes appended by
    `0x9ec0`.
  - `0x780e3b`: no-byte gate that returns `D7 = -1` while
    `0x780e66 != 0`; the main parser loop observes and clears it at
    `0x117dc..0x117ee`.
  - `0x7821c4`: timeout/handshake state cleared after direct hardware
    reads.
  - `0x7828ec`: direct-mode active byte, cleared or set by hardware
    handshake paths.
  - `0x7828fa` and `0x7828fb`: direct-mode control shadows.
  - `0x780e2e`: status-error accumulator for alternate direct mode bits
    `7` and `6`.
  - `0x783e60`: service reason byte set to `8` by full/status bridge
    service paths.
  - `0x783e61`: bridge service-pending byte. When set, `0xa7c2..0xa810`
    writes `$aa01`, then signals `0x780202` if status bit 1 is set or
    `0x7801e2` otherwise.
  - `0x780e2a`: warning accumulator; `0xa726..0xa73c` ORs bit `1` on
    low-water capacity.
  - `0x780e2e`: error accumulator; `0xa708..0xa714` ORs bit `1` when
    no ring capacity remains.
  - `0x780e62`: status byte copy written with `0x13` when a service path
    observes status bit 1.
  - `0x780e49`: OR mask merged into `0x7828fa` before `$aa01` writes.
  Evidence: disassembly `0xa904..0xab8a`, `0xa6cc..0xa810`, and host
  fetch/bridge fixtures above.
- Parser scratch:
  - none owned by `0xa904`. Parser scratch starts after a returned byte
    enters `0xda9a`/`0x11774`, or when payload readers consume byte counts
    from already-restored command records.
- Unknown:
  - physical names for the `0x8e01`/`0x8801`/`0x8c01` bank and the
    `0xfffee005`/`0xfffee001`/`0xfffee009` bank.
  - exact RAM structure for the current data-chain frame beyond fields
    already used by macro replay fixtures.

### Writers

- `0xa904` decrements stack/ring counts, advances source pointers, clears
  bits in `0x780e66`, clears `0x7821c4`, updates `0x7828ec`, and toggles
  direct-mode control shadows.
- `0xa904` calls `0x10cc(0x780202)` when service/polling paths need work
  before retrying the byte fetch.
- `0xa904` calls `0xe22c` when a data-chain frame has end marker `-1` at
  frame `+4`, then retries source selection.
- `0xa6cc` and helper `0xa846` write the ring source consumed later by
  `0xa904`. `0xa6cc` also writes `0x780e2a`, `0x780e2e`, `0x783e60`,
  `0x783e61`, `0x783e62`, `0x780e62`, and `$aa01` during low-water,
  full-buffer, and status service paths.
- Macro setup helpers such as `0xe418` write data-chain frames later
  consumed by `0xa904`; the macro execute/call fixtures pin frame
  payload bytes `!\r` and mixed-control payload
  `ESC &k1G!\r!`.
- Pushback/log helper `0x9ec0` writes `0x783e76` / `0x783e78` and sets
  `0x780e66.0` when current frame byte `+9 == 0`; it writes `0x783e8c` /
  `0x783e8e` and sets `0x780e66.2` when current frame byte `+9 != 0`.
- Gate setters `0x4322..0x4332` and `0x622c..0x623c` write
  `0x780e3b = 1` and set `0x780e66.3`; `0x117dc..0x117ee` clears
  `0x780e3b` before entering the `0x10c8(0x780202)` wait/helper path.

### Readers And Consumers

- The main parser loop `0x11774` consumes `0xa904` bytes for normal host
  streams and routes them to handlers such as `0xd04a`, `0xf02c`,
  `0xedf8`, and raster/font command finals.
- Delayed payload readers consume bytes through `0xa904` or payload
  wrappers after `0x12218` restores the saved command record.
- Transparent text handler `0x12452` consumes `ESC &p#X` payload bytes
  through `0xa904`, routing printable bytes back to `0xd04a` and
  default-filtered C0/high-control payload bytes through fixed-space
  helper `0xd0f0`.
- Macro execute/call replay consumes data-chain bytes through `0xa904`,
  then re-enters the same parser/page-record path as direct host bytes.
- Font descriptor, resource-payload, downloaded-character, and combined
  downloaded-glyph streams are fixture-backed as modeled `0xa904` ring
  streams before they reach parser/object/render boundaries.

### Output Effect

`0xa904` has no pixels by itself. Its visible effect is that the same byte
sequence can reach parser handlers from host ring, direct hardware, or
data-chain replay with the same downstream page-record output. The macro
mixed-control fixture proves a stored `ESC &k1G!\r!` data-chain payload
replays through `0xa904`, reaches handlers `0xedf8`, `0xd04a`, `0xf02c`,
and `0xd04a`, then renders the same rows as direct host bytes. The
combined downloaded-glyph fixture proves one 2,215-byte `0xa904` ring
stream can cross font-control, payload, printable, page-record, bridge,
and render-entry boundaries. The bridge fixture proves `0xa6cc` can place
byte `0x41` into the ring and the next `0xa904` fetch returns it as
`D7 = 0x41`; low-water and full-buffer paths affect scheduler/status
state rather than pixels directly.

### Confidence

High for byte-source priority, no-byte gating, data-chain end retry,
ring/direct source selection, `0x1a` reporting, direct-mode state side
effects, and the software-visible `0xa6cc` ring/status bridge because
they are covered by executable fixtures and the `0xa904`/`0xa6cc`
disassembly. Medium for physical interface naming and full data-chain
frame ownership because those require board/manual correlation and
broader frame-lifetime tracing.

### Fixtures

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
- `host-fetched text rectangle raster FF publishes rendered page record`

### Disassembly Evidence

- `generated/disasm/ic30_ic13_host_byte_fetch_00a904.lst`:
  `0xa904..0xab8a`
- `generated/disasm/ic30_ic13_a801_a601_io_00a4e8.lst`:
  `0xa6cc..0xa810` for the alternate bridge and `0xa846..0xa8c8` for
  ring append / sequence dispatch helpers.
- `generated/disasm/ic30_ic13_main_parser_loop_011774.lst`:
  parser consumers of returned `D7`
- `generated/analysis/ic30_ic13_tokenizer_macro_callers.md` plus
  executable macro fixtures in
  [harness](/usr/home/admin/T400/ljII/tools/render_fixture_harness.py:15396)
  provide the current macro/data-chain evidence.
- `generated/disasm/ic30_ic13_payload_dispatch_011f82.lst` and
  `generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst`:
  delayed payload consumers.

### Unresolved Middle Edges

- `0xa9e2..0xaa86`: physical interface name and exact electrical
  handshake for the `0x8e01`/`0x8801`/`0x8c01` direct bank.
- `0xaaa6..0xab8a`: physical interface name and exact electrical
  handshake for the `0xfffee005`/`0xfffee001`/`0xfffee009` direct bank.
- `0xa6cc..0xa810`: software ring/status bridge effects are modeled, but
  the physical names and timing for `0xfffe0001`, `0xfffe0003`, and
  `$aa01` are not identified.
- `0x782d76 frame +0x00..+0x0d`: execute/call frames from `0xe418` and the
  non-replay page-finalization frame from `0xe4f4` are documented. Remaining
  uncertainty is any producer for frame byte `+9` values outside observed
  `2`, `3`, and `4`.
- `0x4322..0x4332` and `0x622c..0x623c`: the local no-byte gate writes are
  pinned, but the broader high-level routine names around those gate setters
  remain provisional.

## Parser Record And Delayed Payload State

Status: composed as the parser setup and stateful tokenizer-helper cluster
for `0x11ea4..0x11f4c`. The low-level ledger remains in
[pcl-parser-core.md](pcl-parser-core.md), with disassembly evidence in
`generated/disasm/ic30_ic13_parser_setup_handlers_011ea4.lst`,
`generated/disasm/ic30_ic13_tokenizer_stateful_helpers_011ba6.lst`, and
summary evidence in
`generated/analysis/ic30_ic13_tokenizer_macro_callers.md`.

Concept: the parser does not treat a command final and its payload bytes as
one event. Setup handlers select the active callback helper in `0x78299a` or
append synthetic primary/secondary font-designation records. Stateful helpers
then tokenize one or more six-byte records, rewind `0x78299e` when a lookahead
byte belongs to the current record, arm delayed handler wrapper `0x1228a` for
generic `W/w` payloads, and let `0x12218` restore the selected record before
payload consumption.

### Field Groups

- Canonical parser record state:
  - `0x78299e`: current six-byte command-record cursor.
  - six-byte command records: final byte, parsed signed word, and scratch
    words consumed by terminal handlers and payload readers.
  - `0x782999`: parser mode byte cleared by helper exits and tested by
    `0x11c6c` to bypass generic `W/w` scheduling in mode `4`.
  - `0x782c18`: normal versus alternate/data parser mode. Normal mode routes
    parser finals to terminal handlers; alternate/data mode redirects
    printable/payload bytes through append helpers such as `0xe002` and
    `0x12358`.
  Evidence: `pcl-parser-core.md` and the `0x11ba6`, `0x11c6c`,
  `0x11d0c`, and `0x11dd2` helper bodies.
- Parser scratch:
  - `0x782a26` and `0x782a2a..`: nonnumeric command-byte scratch collected by
    the tokenizer.
  - `0x782a3e` and `0x782a42..`: sign, digit, and fractional-token scratch
    used while deriving the canonical command-record words.
  - `0x783196..0x783199`: local matched-byte accumulation buffer used by the
    main parser loop.
  Evidence: tokenizer `0xdb74`, command combiner `0xdaf0`, and main parser
  loop `0x11774`.
- Firmware bookkeeping:
  - `0x78299a`: active callback helper pointer. Setup handler `0x11ea4`
    writes default callback `0x11b8e` for mode-0 `0x1a`, `0x11eb6` writes
    punctuation-prefixed helper `0x11ba6` for mode-0 `ESC`, `0x11ec8` writes
    generic helper `0x11c6c`, `0x11eda` writes callback continuation helper
    `0x11d0c`, and `0x11eec` writes font-refreshing continuation helper
    `0x11dd2`.
  - `0x782a1a`: delayed-payload pending flag.
  - `0x782a1c`: delayed handler pointer.
  - `0x782a20..0x782a25`: saved six-byte command record.
  - `0x782a56`: alternate/data terminal-append latch cleared by `0x11d0c` and
    `0x11dd2` before optional `0xe002` output.
  - local flag `D4`: distinguishes uppercase `W` terminal processing from
    other terminal bytes in `0x11d0c` and `0x11dd2`.
  Evidence: scheduler `0x121cc`, restore helper `0x12218`, and generic helper
  calls to `0x121cc(0x1228a)`.
- Derived parser records:
  - `0x11efe` appends a synthetic record byte `0x80` with word `1` for
    secondary `ESC )` font-designation parsing.
  - `0x11f26` appends a synthetic record byte `0x80` with word `0` for
    primary `ESC (` font-designation parsing.
  - `0x11f4c` rewinds `0x78299e` by six for lowercase chaining finals.
- Unknown:
  - no unresolved parser-record fields remain in this checkpoint. Remaining
    unknowns after the restored record reaches a terminal handler are owned by
    the command-family sections below.

### Writers

- `0xdb74` writes command-record fields and numeric scratch. `0xdaf0`
  combines records in one PCL escape family and rewinds the record cursor when
  lookahead still belongs to that family.
- `0x11ea4`, `0x11eb6`, `0x11ec8`, `0x11eda`, and `0x11eec` write the active
  callback helper pointer at `0x78299a`.
- `0x11efe` and `0x11f26` append synthetic primary/secondary selector records
  before `ESC )` and `ESC (` command-family tokenization.
- `0x11f4c` rewinds `0x78299e` for lowercase chaining finals.
- `0x11774` initializes parser state, dispatches by normal or alternate/data
  parser tables, writes parser mode transitions, and triggers `0x12218` when a
  state transition returns to mode zero.
- `0x11ba6` consumes one extra host byte through `0xda9a` for incoming
  `0x21..0x2f` punctuation-prefixed commands, echoes it through `0x9ec0`,
  then tokenizes at `0x11bdc` unless it is space.
- `0x11c6c` echoes the incoming command byte, tokenizes at `0x11c88`, arms
  `0x1228a` for `W/w` except in parser mode `4`, and rewinds `0x78299e` for
  continuation bytes.
- `0x11d0c` and `0x11dd2` arm `0x1228a` for lowercase `w` continuation and
  uppercase `W` terminal cases. `0x11dd2` also rewinds `0x78299e` and calls
  font-state refresh helper `0xc580` before terminal processing.
- `0x121cc` writes the pending flag, handler pointer, and saved command
  record; `0x12218` clears the pending flag and restores that record before
  dispatching the saved handler.

### Readers And Consumers

- Terminal command handlers consume the active six-byte record selected by the
  helper and cursor rewind behavior.
- Generic payload wrapper `0x1228a`, raster payload reader `0x105d0`,
  transparent payload reader `0x12452`, and downloaded-font payload readers
  depend on the same delayed-record restore contract.
- Downloaded-font payload handlers `0x15d0a` and `0x16c14` consume restored
  descriptor/resource records before installing or rejecting font data.
- Macro definition mode and alternate/data mode consume parser records but
  redirect payload bytes through `0xe002` / `0x12358` rather than immediate
  imaging.

### Output Effect

The helper cluster has no pixels by itself. Its output effect is preserving the
command/payload boundary that later pixel-producing handlers consume.

Fixture `0x11774 ROM dispatch table routes raster stream to delayed transfer`
proves the parser reaches `0x11f82` and stores the delayed raster transfer
record before payload bytes are consumed. Fixture `modeled raster command
stream parses ESC *t300R / ESC *r1A / ESC *b4W payload boundary` proves
`0x12218` restores that saved `W` record before the payload reader consumes the
following bytes. Fixture `raster chained transfer parser trace preserves
lowercase delayed record` proves a lowercase `w` record remains pending until
the uppercase terminator restores it.

Fixture `transparent data parser trace feeds page-record queue` proves delayed
transparent text restores through `0x12452` before routing payload bytes into
text/fixed-space output. Fixtures `resource payload stream ties ROM parser
dispatch to 0x16c14 install` and `downloaded character stream ties ROM parser
dispatch to rendered object` prove the same delayed-record contract feeds
downloaded-font payload handlers before visible glyph output.

If a reimplementation does not preserve the `0x78299e` rewind and `0x121cc` /
`0x12218` delayed snapshot behavior, streams such as `ESC *b4W`, `ESC &p#X`,
generic `W/w` payloads, downloaded-font payloads, and macro data-chain replay
will restore the wrong byte count or final byte before producing page objects.

### Confidence

High for tokenizer record layout, cursor rewind, helper selection, delayed
snapshot/restore, alternate/data redirection, the `0x11ea4` / `0x11eb6` /
`0x11ec8` / `0x11eda` / `0x11eec` callback selection stubs, the `0x11efe` /
`0x11f26` synthetic font-designation records, and the `0x11f4c` rewind helper
because these are direct disassembly reads and fixture-backed across raster,
transparent text, downloaded-font, and macro paths. Medium only for
command-family semantics beyond the restored-record boundary.

### Fixtures

- `0x11774 ROM dispatch table routes raster stream to delayed transfer`
- `modeled raster command stream parses ESC *t300R / ESC *r1A / ESC *b4W
  payload boundary`
- `raster chained transfer parser trace preserves lowercase delayed record`
- `transparent data parser trace feeds page-record queue`
- `resource payload stream ties ROM parser dispatch to 0x16c14 install`
- `downloaded character stream ties ROM parser dispatch to rendered object`
- `macro execute frame payload feeds 0xa904 data-chain bytes`
- Macro execute/call replay fixtures documented in
  [pcl-parser-firmware.md](pcl-parser-firmware.md).

### Evidence

- `generated/disasm/ic30_ic13_parser_setup_handlers_011ea4.lst`
- `generated/disasm/ic30_ic13_tokenizer_stateful_helpers_011ba6.lst`
- `generated/disasm/ic30_ic13_pcl_escape_parser_00da9a.lst`
- `generated/disasm/ic30_ic13_main_parser_loop_011774.lst`
- `generated/disasm/ic30_ic13_payload_dispatch_011f82.lst`
- `generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst`
- `generated/disasm/ic30_ic13_font_payload_readers_0168dc.lst`
- `generated/disasm/ic30_ic13_font_selector_setup_helpers_011ec8.lst`
- `generated/analysis/ic30_ic13_tokenizer_macro_callers.md`
- `generated/analysis/ic30_ic13_parser_dispatch_tables.md`
- `generated/analysis/ic30_ic13_active_symbol_set_flow.md`
- `notes/pcl-parser-core.md`
- fixtures named in raster, transparent-data, downloaded-font, and macro
  sections that pass through `0x121cc` / `0x12218` before visible output.

### Unresolved Middle Edges

- None for parser-record layout, tokenizer rewind, delayed scheduler
  snapshot, alternate/data payload redirection, or `0x12218`
  restore/dispatch. Open work after this boundary is command-family specific:
  terminal handler effects, page-object allocation, font/raster payload
  interpretation, macro data-chain lifecycle, and final rendered output.

## Display Functions ESC Y Reader

Status: composed as the `ESC Y` command-family reader from parser dispatch to
append/text-routing loop. The low-level ledger remains in
[pcl-parser-core.md](pcl-parser-core.md), with disassembly evidence in
`generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst`.

Concept: `ESC Y` is not a one-byte mode bit in this firmware. It enters an
`ESC Z`-terminated reader loop over subsequent host bytes. The normal parser
table dispatches `ESC Y` to `0x12536`, which routes normalized bytes into text
imaging. The alternate/data parser table dispatches `ESC Y` to `0x12120`,
which appends normalized bytes through `0xe002`.

### Field Groups

- Canonical reader state:
  - local flag `D4`: zero until the previous routed/appended value was `ESC`
    (`0x1b`), one after `ESC`, and tested when the current value is `Z`
    (`0x5a`) to terminate the loop.
  - normalized payload value `D5`: fetched through `0xa904`, with local
    `0x1a 0x58` normalized to `0x7f` after `0xd99a`.
  Evidence: disassembly `0x12128..0x1219c` and `0x1253e..0x1261e`.
- Parser scratch/filter state:
  - selected slot `0x782f06`, scaled by `0x332ee`.
  - selected context byte at `0x782eea + 0x10 * slot`, copied to `D3`.
  - fallback high-control filter byte `0x782efa`, used when `0x783132` and
    `0x783133` are clear.
  - local stack word `A6-2` in `0x12536`, holding the high-control filter.
  Evidence: disassembly `0x12540..0x12582`.
- Firmware bookkeeping:
  - `0xe002` append sink used by alternate/data handler `0x12120`.
  - `0xd99a` side effect for local `0x1a 0x58` control reporting.
  - `0xf054` CR post-handler called by `0x12536` after routed value `0x0d`.
  - macro/data-chain chunk `0x783988`, populated by `0xe002` in the append
    fixture for the byte stream preserved by alternate/data `ESC Y`.

### Writers

- `0x12120` writes the literal `ESC Y` prefix through `0xe002`, then appends
  each normalized loop value through `0xe002` until `ESC Z` or `D7 = -1`.
- `0x12536` writes visible text/fixed-space effects by calling `0xd04a` or
  `0xd0f0` for each normalized loop value until `ESC Z` or `D7 = -1`.
- Both handlers call `0xd99a` when local bytes `0x1a 0x58` are consumed and
  substituted with routed/appended value `0x7f`.

### Readers And Consumers

- `0xa904` supplies the raw loop bytes from host, pushback, or data-chain
  sources.
- `0x12120` consumes the raw bytes for append-only output through `0xe002`.
- `0x12536` consumes selected context/filter state, then routes C0 and
  high-control ranges through the same `0xd0f0` / `0xd04a` consumers used by
  transparent print data and direct text.
- Downstream consumers of the normal path are source-object mapping,
  cursor/spacing state, page-record queueing, bridge, and render entry.

### Output Effect

Alternate/data `0x12120` has no direct pixels in this checkpoint. It preserves
the displayed byte stream by appending `ESC Y` and all normalized values
through `0xe002`, with `0x1a 0x58` represented as `0x7f`, until `ESC Z`.
Fixture `0x12120 ESC Y alternate append stores normalized display bytes`
proves payload `21 1a 58 1b 5a` is stored as `1b 59 21 7f 1b 5a` in macro
chunk `0x783988`; the fixture records allocation plus six `0xe002` byte
appends with raw counts `4..10`.

Normal `0x12536` can produce pixels or spacing. Values `0x00..0x1f` route
through `0xd0f0` only when the selected context byte is zero; values
`0x80..0x9f` route through `0xd0f0` only when the high-control filter word is
zero; all other values route through `0xd04a`. Therefore `ESC Y ... ESC Z`
can expose control-looking bytes as visible text under nonzero filters, while
default-filtered controls become fixed-space behavior.

Fixture `ESC Y display-functions stream reaches page-record output` proves the
normal parser-to-page-record boundary for `ESC Y!\x05! ESC Z`: handler
`0x12536` consumes values `21 05 21 1b 5a`, routes them
`d04a d0f0 d04a d0f0 d04a`, treats the terminating `ESC Z` bytes as routed
values before exit, queues visible `!`, `!`, and `Z` entries at compact coords
`0x0001`, `0x0403`, and `0x0405`, and renders row digest
`c7d0fb0a66181acd591244aab0a7f450f895b3b89ea98d189a00a25c3de04d85`.
Fixture `ESC Y display-functions filter-on routes controls as printable`
proves the complementary normal branch: with selected-context byte `1` and
high-control filter `1`, stream `ESC Y\x05\x80\x1aX! ESC Z` normalizes
`0x1a 0x58` to `0x7f`, routes values `05 80 7f 21 1b 5a` through `0xd04a`,
queues six compact entries with object prefix
`00 00 00 00 00 00 00 06 04 0b 00 7f 0e 01 7e 1f 02 20 06 04 1a 53 05 59
06 06`, and renders row digest
`1cdd8203b43944801ec8d1d01c6ab4fa3808fc1f81a7ebfa4d04452369193b63`.

### Confidence

High for the loop terminator, local `0x1a 0x58` normalization, alternate/data
append behavior, normal-path C0/high-control routing predicates, and CR
post-handler call because these are direct disassembly reads and now have
dedicated fixtures for both `0x12120` and `0x12536`. High for the normal
`0x12536` parser-to-page-record boundary because the host-fetched fixture
drives `ESC Y ... ESC Z` through `0xd04a`, `0xd0f0`, compact object queueing,
bridge, and rendered rows. High for the alternate/data append boundary because
the append fixture drives `0x12120` loop output through `0xe002` into the
macro chunk payload.

### Fixtures

- `ESC Y display-functions stream reaches page-record output`
- `ESC Y display-functions filter-on routes controls as printable`
- `0x12120 ESC Y alternate append stores normalized display bytes`
- Downstream route controls are shared with fixtures in `Transparent Print
  Data` and `Text Cursor And Direct Controls`, including
  `transparent data control payloads advance through fixed-space path` and
  `transparent nonzero filters route controls through printable path`.

### Evidence

- `generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst`:
  `0x12120..0x1219c` and `0x12536..0x1261e`.
- `generated/analysis/ic30_ic13_parser_dispatch_tables.md`: normal and
  alternate/data mode-1 `ESC Y` dispatch entries.
- `notes/pcl-parser-core.md`: `ESC Y Display Functions Readers`.

### Unresolved Middle Edges

- None remaining for the `0x12536..0x1261e` normal page-output loop, its
  default-filter and filter-on route predicates, or the `0x12120..0x1219c`
  alternate/data append loop. Broader macro/data-chain ownership remains
  covered in `Macro Definition And Replay`, not reopened here.

## Text Cursor And Direct Controls

Status: composed as a parser-to-visible-output cluster for direct
controls, HMI, margins, cursor positioning, dot positioning, vertical
layout, transparent text, and cursor stack. The detailed handler ledger
is preserved in `notes/reverse-engineering-ledger.md` and generated
reports; this section groups the shared state that determines where the
next printable byte or raster start lands.

Concept: the parser updates a small canonical cursor/layout environment,
then printable handler `0xd04a`, transparent-data handler `0x12452`,
raster-start paths, and page-record producer `0x12f2e` consume that
environment. Host byte streams that differ only in cursor commands must
therefore reproduce the same `0x782c8a` / `0x782c8e` / margin / HMI /
VMI state before object queueing, then cross the same `0x1387c`,
`0x1edc6`, `0x1ed84`, and `0x1ef6a` boundaries.

### Field Groups

- Canonical placement state:
  - `0x782c8a`: horizontal cursor used by printable text, HT/BS,
    horizontal `ESC &a` / `ESC *p` positioning, and raster start.
  - `0x782c8e`: vertical cursor used by LF/FF, vertical `ESC &a` /
    `ESC *p` positioning, printable text bucketing, and raster start.
  - `0x782dd6`: left/default margin copied into `0x782c8a` by CR helper
    `0xf06e` and written by `ESC &a#L` handler `0xeb58`.
  - `0x782dda`: right margin / horizontal limit written by
    `ESC &a#M` handler `0xec0c` and consumed by HT and horizontal
    commit helper `0xf4ca`.
  - `0x78315c`: HMI/default horizontal motion written by `ESC &k#H`
    handler `0xca8c`, read by HT/BS, margin handlers, column
    positioning, and printable advance fixtures.
  - `0x783160`: VMI/line advance written by vertical-layout handlers
    `0xcb00` and `0xc992`, read by LF/FF, `ESC &a#R`, VFC, and
    page-length/top-margin fixtures.
  Evidence: generated direct-control report state scan entries for
  `0x782c8a`, `0x782c8e`, `0x782dd6`, `0x782dda`, `0x78315c`, and
  `0x783160`; fixtures `HMI parser trace feeds page-record queue`,
  `mixed printable/control parser trace feeds page-record queue`,
  `HT/BS parser trace feeds page-record queue`, `margin command parser
  trace feeds page-record queue`, `right margin command parser trace
  feeds page-record queue`, and the cursor-position parser traces.
- Canonical cursor stack:
  - `0x782c96..0x782d36`: PCL cursor-stack storage used by
    `ESC &f#S`.
  - `0x782d36`: next-free pointer and upper bound for the stack.
  - push selector `0` stores `0x782c8a` and `0x782c8e + 0x782dbe`;
    pop selector `1` restores x and `stored_y - 0x782dbe`, clamped to
    current extents.
  Evidence: generated direct-control report row for `0xf75e`; fixtures
  `0xf75e ESC &f0S pushes cursor with vertical offset`,
  `0xf75e ESC &f1S pops cursor and clears pending flags`,
  `0xf75e cursor stack bounds and pop clamps to current extents`, and
  `cursor stack parser trace feeds page-record queue`.
- Canonical vertical/page limits:
  - `0x782db8`: horizontal page extent used by HT and `0xf4ca` clamps.
  - `0x782dba`: page length / vertical extent written by page-length
    handler `0xf9e8`.
  - `0x782dc6`: vertical upper bound used by `0xf6e2`,
    `ESC &a#R/#V`, dot-position `ESC *p#Y`, and cursor-stack pop.
  - `0x782dca`: vertical lower bound used by `0xf6e2`.
  - `0x782dce`: top offset used by FF helper `0xf124`, absolute
    vertical positioning, top-margin handler `0xece2`, and VFC.
  Evidence: generated direct-control report state scan; fixtures
  `vertical cursor-position parser trace feeds page-record queue`,
  `vertical-decipoint parser trace feeds page-record queue`,
  `vertical layout parser trace feeds page-record queue`, and
  page-length `ESC &l66P!` and `ESC &l0P` notes in the ledger.
- Canonical/default page environment:
  - `0x782da6`: pending page-environment byte copied by the `ESC &l0P`
    zero-parameter branch when it differs from active byte `0x780e8e`.
  - `0x780e8e`: active page-environment byte compared at
    `0xfa74..0xfa86`.
  - `0x780e8f`: output page-environment byte written at `0xfa8a`.
  - `0x780e26`: output/control word signaled through `0x9b5e` at
    `0xfa94..0xfaa4`.
  - `0x780e97`: default page code used by the same branch at
    `0xfb4a..0xfb58`, with fallback code `2` when the byte is zero.
  Evidence: disassembly `0xfa62..0xfaa6` and `0xfb4a..0xfc52`, and
  fixture
  `0xf9e8 ESC &l#P converts VMI lines to page length and selects
  internal page code`, where `ESC &l0P` with `0x782da6 = 0x80`,
  `0x780e8e = 0`, and default code `0` emits `0x780e8f = 0x80`,
  sets control word `1`, chooses code `2`, and reloads extent `3300`.
- Canonical control modes:
  - `0x78318f`: line-termination mode written by `ESC &k#G` handler
    `0xedf8`; CR tests bit 7, LF tests bit 6, and FF tests bit 5.
  - `0x783190`: end-of-line wrap flag written by `ESC &s#C` handler
    `0xedb0` and consumed by printable overflow paths.
  - `0x783191`: perforation-skip byte written by `ESC &l#L` handler
    `0xee64` and consumed by `0xf36c`.
  Evidence: generated direct-control report line-termination and wrap
  sections; fixtures `control stream ESC &k1G then CR applies CR+LF`,
  `control stream ESC &k2G then LF applies CR+LF`,
  `control stream ESC &k2G then FF applies CR+page-eject`,
  `control stream ESC &k3G applies CR/LF/FF combined line termination`,
  and `host-fetched direct text/control streams reach page-record render`.
- Derived/cache placement state:
  - compact text coordinates are derived after cursor conversion and are
    queued into page-record text objects; examples include `0x3b00` for
    the post-CR/LF glyph, `0x0a01` for HT/BS, `0x0a02` for HMI-column
    moves, `0x9001` for vertical decipoint/top-margin cases, and
    `0x0001` after cursor-stack restore.
  - `0x783a20`, `0x783a22`, and `0x783a28` are active-render band
    caches derived by `0x1ed84` setup and consumed by `0x1ef6a`; they
    are not canonical cursor state.
  Evidence: fixtures `host-fetched cursor-row compact text splits at
  0x783a20 boundary`, `host-fetched direct text/control streams feed
  0x1ed84 and 0x1ef6a`, and generated render-entry notes.
- Parser scratch:
  - `0x78299e`: six-byte parsed command record cursor rewound by
    handlers such as `0xca8c`, `0xeb58`, `0xec0c`, `0xf39e`,
    `0xf416`, `0xf560`, `0xf60a`, `0xf75e`, and `0x11f5a`.
  - delayed transparent-text command records are saved/restored by
    `0x121cc` / `0x12218` before payload handler `0x12452` consumes
    `ESC &p#X` bytes through the byte-source path.
  Evidence: generated direct-control report state scan for `0x78299e`
  and transparent-data section; fixtures `host-fetched direct
  text/control streams reach page-record render` case `transparent` and
  `transparent data control payloads advance through fixed-space path`.
- Firmware bookkeeping:
  - `0x782a57`: right-limit latch set by right-margin and horizontal
    positioning paths.
  - `0x782a58`: previous-width / pending width latch cleared before
    span flushes and set by BS.
  - `0x782a5a`: latched previous width used by BS when `0x78318e` is
    set.
  - `0x782a6d`: printable/pending-text flag cleared by cursor moves and
    set to `0xff` by FF after page eject.
  - `0x783184`: pending text span flush enable tested by helper
    `0xf34a`.
  - `0x78318e`: alternate previous-width mode tested by BS.
  Evidence: generated direct-control report state scan and shared-helper
  table; fixtures for CR/LF/FF/HT/BS, cursor-stack pop, and horizontal
  commit helpers.
- Unknown:
  - exact manual-facing names for some pending-text latches
    `0x782a57`, `0x782a58`, `0x782a5a`, and `0x782a6d`.
  - complete live CPU/memory trace for every `0xd04a` source-object
    write before the modeled `0x12f2e` / `0x1387c` page-record object.

### Writers

- `0xedf8` writes line-termination byte `0x78318f` for `ESC &k#G`;
  CR `0xf02c`, LF `0xf08c`, and FF `0xf0f0` consume it at runtime.
- `0xca8c` writes HMI `0x78315c` for accepted `ESC &k#H` values; the
  `ESC &k6H!!` fixture stores packed HMI `15` and moves the second
  glyph to compact coord `0x0501`.
- `0xf02c`, `0xf08c`, `0xf0f0`, `0xf1cc`, and `0xf2a8` write cursor and
  pending-span state for CR/LF/FF/HT/BS.
- `0xeb58` and `0xec0c` write left/right margins and can move
  `0x782c8a`.
- `0xf39e`, `0xf416`, and `0xf48c` write horizontal cursor state
  through helper `0xf4ca`; `0xf560`, `0xf60a`, and `0xf692` write
  vertical cursor state through helper `0xf6e2`.
- `0xcb00`, `0xc992`, `0xece2`, `0xea9e`, `0xee64`, and `0xf9e8` write
  VMI, vertical layout, perforation skip, and page-length state.
- `0xf75e` writes cursor-stack entries and restores cursor state.
- `0x11f5a` arms transparent-text delayed payload state; `0x12452`
  consumes the payload and routes printable bytes back into `0xd04a`.

### Readers And Consumers

- `0xd04a` consumes cursor, HMI, font context, and pending-width state
  to create the next text source object before `0x12f2e` queues compact
  text.
- `0x12f2e`, `0x1387c`, and shared page-record storage consume the
  compact text coordinates produced from cursor state.
- Raster-start command paths consume `0x782c8a` or `0x782c8e` depending
  on orientation, as documented in `notes/pcl-parser-firmware.md`.
- `0x1edc6` bridges queued page-record text objects into render-record
  shape, and `0x1ed84` / `0x1ef6a` consume the active record to render
  the band rows.
- VFC handler `0x1280a` and vertical-layout handlers share VMI,
  top-offset, text-bottom, and vertical-cursor state with this cluster;
  see the `Vertical Forms Control Channels` section for its composed
  channel semantics.

### Output Effect

- `ESC &k1G!\r!` routes `0xedf8`, `0xd04a`, `0xf02c`, and `0xd04a`;
  the second glyph queues at compact coord `0x3b00` after CR+LF and
  renders the shifted rows through `0x1edc6`.
- `ESC &k2G!\n!` routes LF handler `0xf08c`, applies mode `0x60`
  CR+LF, and also queues the second glyph at `0x3b00`.
- `ESC &k0G HT BS !` routes `0xedf8`, `0xf1cc`, `0xf2a8`, and `0xd04a`;
  HT advances to x `21`, BS backs up to x `20`, and the glyph queues at
  compact coord `0x0a01` / pixel x `26`.
- `ESC &k6H!!` routes `0xca8c` and two `0xd04a` events; packed HMI
  `15` queues glyphs at `0x0600` and `0x0501`.
- `ESC &a1L!`, `ESC &a1M!`, and `ESC &a6l9M!` route margin handlers
  `0xeb58` / `0xec0c` into following `0xd04a` output at compact coords
  `0x0801`, `0x0a02`, and `0x0207`.
- `ESC &a2C!`, `ESC &a72H!`, `ESC &a1R!`, `ESC &a72V!`, and
  `ESC &a2c+1R!` route cursor-position handlers `0xf39e`, `0xf416`,
  `0xf560`, and `0xf60a` to compact coords `0x0a02`, `0x0402`,
  `0x1001`, `0x9001`, and `0x1a02`.
- `ESC *p30x30Y!` routes dot-position handlers `0xf48c` and `0xf692`
  to following `0xd04a` output at compact coord `0x9402`.
- `ESC &l3E!`, `ESC &l1L!`, and `ESC &l66P!` route vertical-layout,
  perforation-skip, and page-length state into following printable
  output; the top-margin case queues at `0x9001` in bucket `6`.
- `ESC &f0S ESC &a2C ESC &f1S!` routes `0xf75e`, `0xf39e`, `0xf75e`,
  and `0xd04a`; the pop restores the original cursor and the glyph
  queues at compact coord `0x0001`.
- The grouped host-fetch fixture drains the same streams from the
  modeled `0xa904` ring source, verifies the parser handlers, preserves
  the `0x1edc6` bridge contract, and feeds `0x1ed84` / `0x1ef6a`.

### Confidence

High for the command-family mapping, field roles, conversion effects,
page-record compact coordinates, and bridge/render-entry effects because
they are covered by generated disassembly reports plus executable
fixtures that start at `0xa904` and reach rendered rows. Medium for the
exact names of pending-text latches and every internal write between
`0xd04a` and `0x12f2e`, because several page-object fixtures still use
modeled source/object structures rather than a full live CPU-memory run.

### Fixtures

- `control stream ESC &k1G then CR applies CR+LF`
- `control stream ESC &k2G then LF applies CR+LF`
- `control stream ESC &k2G then FF applies CR+page-eject`
- `control stream ESC &k3G applies CR/LF/FF combined line termination`
- `control stream HT then BS updates tab and previous-width state`
- `0xca8c ESC &k#H stores packed HMI for in-range absolute values only`
- `HMI parser trace feeds page-record queue`
- `plain printable parser trace feeds page-record queue`
- `mixed printable/control parser trace feeds page-record queue`
- `LF parser-to-page-record boundary`
- `HT/BS parser trace feeds page-record queue`
- `margin command parser trace feeds page-record queue`
- `right margin command parser trace feeds page-record queue`
- `chained margin command parser trace feeds page-record queue`
- `cursor-position parser trace feeds page-record queue`
- `decipoint cursor parser trace feeds page-record queue`
- `vertical cursor-position parser trace feeds page-record queue`
- `vertical-decipoint cursor parser trace feeds page-record queue`
- `chained cursor-position parser trace feeds page-record queue`
- `cursor stack parser trace feeds page-record queue`
- `host-fetched direct text/control streams reach page-record render`
- `host-fetched direct text/control streams preserve 0x1edc6 bridge
  contract`
- `host-fetched direct text/control streams feed 0x1ed84 and 0x1ef6a`

### Disassembly Evidence

- `generated/disasm/ic30_ic13_control_code_handlers_00f02c.lst`:
  CR/LF/FF/HT/BS and shared helpers `0xf06e`, `0xf0b2`, `0xf124`,
  `0xf34a`, `0xf36c`, `0xf4ca`, and `0xf6e2`.
- `generated/disasm/ic30_ic13_hmi_vmi_handlers_00ca8c.lst`:
  HMI/VMI, vertical layout, margin, and line-termination handlers.
- `generated/disasm/ic30_ic13_dot_position_handlers_00f48c.lst`:
  dot-position and cursor-stack handlers.
- `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`:
  printable text consumers of cursor/font state.
- `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`:
  compact text page-record producer.
- `generated/analysis/ic30_ic13_direct_control_code_flow.md`:
  handler table, field-reference scan, shared-helper table, and current
  reproduction contract.
- `generated/analysis/ic30_ic13_printable_text_path.md`:
  parser-to-page-record fixture evidence and compact-coordinate outputs.

### Unresolved Middle Edges

- `0xd04a..0x12f2e`: source-object field semantics and compact bucket
  production are composed in `Text Source Objects And Compact Buckets`;
  remaining work is full live CPU-register/memory capture for dense
  parser-produced pages across every source class.
- `0xf34a..0x12714` and `0xf34a..0x126e2`: pending span flush and
  re-arm state are composed in `Text Span Flush And Fixed-Width Spans`;
  allocation-failure retry publication and nonempty fixed-list insertion are
  fixture-backed there. The real-CR entry is no longer open: fixture
  `live CR span flush materializes 0x12714 page object` drives
  `0xf02c -> 0xf06e -> 0xf34a -> 0x12714 -> 0x126e2` from parsed
  `ESC &k1G!\r`, queues the segment-list object, re-arms the span state,
  and renders the span rows beside the compact text object. The remaining
  direct-control span edge is narrower: host-fetched margin or cursor
  movement streams that cross the same `0xf34a` span branch are still
  represented by composed helper state rather than their own end-to-end
  parser fixtures.
- `0xd4ac..0xd8fc`: active font/context span update helpers are
  composed as watermark writers in `Text Span Flush And Fixed-Width
  Spans`; descriptor metric producer formulas are documented from `0x17430`,
  `0x1757a`, `0x1762a`, and `0x1719c`. Additional legal descriptor metric
  values are cross-products of those formulas and the documented consumer
  gates; remaining work is broader selected-font state combinations and
  external/manual naming for consumed-but-not-staged validation fields, as
  tracked in `notes/font-context-metrics.md`.
- `0x11f5a..0x12452`: transparent-text delayed payload restore, control
  filtering, printable re-entry, and fixed-space output are composed in
  `Transparent Print Data`. The C0 branch, `0x80..0x9f` branch, nonzero
  printable route, fixed-space route, primary tall bucket-crossing, and
  secondary segmented page-record boundaries are fixture-backed; remaining
  work is the secondary segment-57 fallback-row memory-map interpretation at
  bucket `456`, not primary high-control value cross-products or the
  command-family parser-to-page-record boundary.
- `0x10084..0x1387c`: first-root allocation and compact text queueing
  are fixture-backed for this cluster, but a dense live parser page that
  exercises same-chunk and rollover allocation for all cursor variants
  is still covered by the shared page-record storage checkpoint rather
  than this section.

## Transparent Print Data

Status: composed as the `ESC &p#X` delayed-payload cluster from parser command
record to transparent payload byte routing, page-record text output, fixed
spacing, and rendered rows. The low-level ledger remains in
[transparent-print-data.md](transparent-print-data.md).

Concept: transparent print data is a counted byte-stream splice, not an opaque
skip. Handler `0x11f5a` arms delayed handler `0x12452` through `0x121cc`.
When `0x12218` restores the saved six-byte `X` record, `0x12452` consumes the
following payload bytes through `0xa904`, normalizes its local `1a` probe
syntax, then routes each normalized value through printable handler `0xd04a`
or fixed-space helper `0xd0f0`.

### Field Groups

- Canonical command state:
  - restored command record `80 58 00 02 00 00` for `ESC &p2X`, or
    `80 58 00 04 00 00` for `ESC &p4X`.
  - restored command record `80 58 00 03 00 00` for high-control fixtures
    `ESC &p3X!\x81!`, `ESC &p3X!\x88!`, `ESC &p3X!\x90!`,
    `ESC &p3X!\x97!`, `ESC &p3X!\x98!`, `ESC &p3X!\x9f!`, and
    `SO ESC &p3X!\x80!`.
  - command record word `+2`: signed count converted to an absolute payload
    count by `0x12452`.
  - text cursor `0x782c8a`: consumed and advanced by routed `0xd04a` and
    `0xd0f0` payload values.
  Evidence: fixtures `0x11f5a/0x12452 transparent text restores and consumes
  counted bytes`, `transparent data parser trace feeds page-record queue`, and
  `transparent data control payloads advance through fixed-space path`.
- Parser scratch:
  - `0x782a1a`: delayed-payload pending flag.
  - `0x782a1c`: delayed handler pointer, set to `0x12452`.
  - `0x782a20..0x782a25`: saved six-byte command record.
  - snapshot for `ESC &p2X`: `01 00 01 24 52 80 58 00 02 00 00`.
  Evidence: `generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst`
  and the fixture above.
- Derived/cache filtering state:
  - selected slot `0x782f06` is scaled by helper `0x332ee`.
  - selected context byte `0x782eea + 0x10 * 0x782f06` is copied to `D3`.
  - fallback filtering byte `0x782efa` supplies the local filter word when
    high-character flags `0x783132` and `0x783133` are clear.
  - local stack word `A6-2` holds the high-control filtering word used by the
    `0x80..0x9f` branch.
  Evidence: `transparent-print-data.md` and fixtures with
  selected/local filtering words `0/0` and `1/1`.
- Canonical page-record output:
  - printable transparent bytes routed through `0xd04a` create compact text
    entries under page-root `+0x1c`.
  - default-filtered C0/high-control bytes routed through `0xd0f0` advance
    fixed spacing in the flagged built-in path and create no compact text
    entry.
  - default-filtered C0 bytes routed through `0xd0f0` in an unflagged
    inline/fixed-record context substitute host space and queue normal compact
    text entries through `0xd140` / `0xd3b2`.
  Evidence: fixture object prefixes
  `00 00 00 00 00 00 00 02 20 00 01 20 02 02`,
  `00 00 00 00 00 00 00 02 20 00 01 20 06 04`, and
  `00 00 00 00 00 00 00 04 20 00 01 04 0d 01 7f 00 03 20 06 04`.
  The unflagged default-filter object is
  `00 00 00 00 00 00 00 03 01 76 01 00 48 02 01 7a 03` plus trailing zeros.
  High-control `0x98` with nonzero filtering queues a separate taller glyph
  object in bucket `-1`:
  `00 00 00 00 00 00 00 01 97 fd 01`, while surrounding `!` entries remain
  in bucket `0`.
  Top-of-range high-control `0x9f` with nonzero filtering follows the same
  printable page-record shape, maps to glyph `0x9e`, queues compact coord
  `0xee01` in bucket `-1`, and renders a distinct selected-bucket digest
  `ec0f944207561c1b9c9139749c3e37d122aebf53e2a50849dd8703416545c719`.
  Interior high-control samples `0x81`, `0x88`, `0x90`, and `0x97` with
  nonzero filtering all route through `0xd04a`, map to glyphs `0x80`,
  `0x87`, `0x8f`, and `0x96`, queue the high-control glyph in bucket `-1`,
  and leave the surrounding `!` bytes in bucket `0`.
  Secondary high-control `0x80` after SO reads context `0xc00ae122` in source
  slot `1`, maps to glyph `0x5f`, and queues segmented selector `0x2001`
  objects across `157` segment buckets; selected bucket `0` begins
  `00 00 00 00 20 01 00 01 5f 00 1c 01 00 00 00 00`.
  The secondary segmented render-prefix fixture renders buckets `0..448`
  (`57` buckets) with aggregate digest
  `292eafb8b558bd36ca0caa5caa2771976c0e611456ac0b610ec8916b9d1f03f9`
  before reaching the current bitmap-source boundary at bucket `456`.
- Derived render state for segment `0x39`: fixture
  `transparent secondary segment-57 continuation policies diverge after verified
  bytes` proves the verified resource bytes determine the current-band digest
  `f0c1127f9e6b203f9829ab43f159b89c3f7dda687a47d4c09971077eac55c96e`, but
  fallback rows need `802` bytes past firmware address `0x0c0000`. The same
  fixture hashes the verified `0x0bfe22..0x0bffff` suffix as
  `e0a0fd34ce7a39f79ecd27c0ee288631554a0ff78359b72e27ea6087651bcf1f` and the
  mirror/code-pair/zero-fill continuation candidates as
  `e435e3b9d033e491b57282a88b0f321aa5fecae8128fa060844cc01379349563`,
  `90934acf59d9e8519c9149dc5df228f8fec2bff8451427be265489be967cdd16`, and
  `359f38eef400e2fa3924a3258652e74ee19cd46cb92e47bce91f1194fce25e9e`.
  Fixture `0x41a HEAD scanner would duplicate records under simple resource
  mirror` constrains the mirror hypothesis: a full `IC32,IC15` mirror at
  `0x0c0000` would expose a second `HEAD` chain to scanner `0x41a` and
  duplicate typed records before the scan terminates at `0x80000`.
- Unknown for this checkpoint:
  - manual-facing names for the selected context filtering byte, fallback
    filtering byte, and high-character flags remain provisional.
  - the board memory-map policy for firmware address `0x0c0000..0x0c0321`
    remains unknown; mirror, code-pair continuation, and zero-fill hypotheses
    produce different fallback row digests in the harness. A simple full mirror
    would also duplicate `HEAD` scanner input, so the proof targets are live
    startup candidate counters, direct bus reads around `0x0c0000`, emulator
    gate-array decode, or physical output matching one fallback digest. This is
    firmware-address-map state, not parser state: `data/rom_manifest.json`
    accounts for the installed ROMs as four 128K x 8 packages with a
    `0x40000`-byte `IC32,IC15` resource pair, while
    `notes/formatter-interface-pca.md` records a possible 1 MB HP 33440 ROM
    capacity and address-controller/jumper-controlled ROM regions.

### Writers

- `0x11f5a` writes delayed-payload state by scheduling `0x12452` through
  `0x121cc`.
- `0x12218` restores the saved command record and dispatches `0x12452`.
- `0x12452` decrements the counted payload, normalizes `1a 58` to routed value
  `0x7f`, treats `1a xx` with `xx != 0x58` as routed value `xx`, and chooses
  `0xd04a` or `0xd0f0`.
- `0xd04a` writes printable source/page-record objects through the normal text
  path.
- `0xd0f0` writes the fixed-space source for host byte `0x20`, clears source
  longword `+4` in the flagged built-in path, and advances spacing through
  `0xd550` without queueing a compact object in the covered fixture.
  In the unflagged fixture it does not clear a built-in glyph pointer; the
  substituted host-space source continues through `0xd140` / `0xd3b2` into
  `0x12f2e`.

### Readers And Consumers

- `0xa904` supplies transparent payload bytes from the current byte source.
- `0x12452` consumes restored record word `+2`, selected context state,
  filtering state, and payload bytes.
- `0xd04a` consumes routed printable values such as `0x21`, `0x41`, `0x05`,
  and `0x80` when filtering is nonzero.
- `0xd0f0` consumes default-filtered C0/high-control values and turns them
  into fixed spacing or substituted host-space text, depending on the current
  source class.
- `0x1387c`, `0x1edc6`, `0x1ed84`, and `0x1ef6a` consume the resulting
  page-record compact text objects for visible rows.

### Output Effect

Fixture `transparent data parser trace feeds page-record queue` proves
`ESC &p2X!!` restores handler `0x12452`, consumes payload bytes `21 21`,
routes both through `0xd04a`, queues compact coords `0x0001` and `0x0202`,
allocates one page root, preserves context slot `0x440946b4` through
`0x1edc6`, and renders the same rows as plain `!!`.

Fixture `transparent non-0x58 probe byte reaches page-record output` proves
`ESC &p2X\x1aA!` consumes raw payload slice `1a 41 21` as routed values
`41 21`. The byte `0x41` maps to glyph `0x40`, queues compact coord
`0x0a00`, and renders visible `A` before the following `!`.

Fixture `transparent data control payloads advance through fixed-space path`
proves default filtering for `ESC &p4X!\x05\x85!`: payload values route
`d04a d0f0 d0f0 d04a`, the C0 byte `0x05` and high-control byte `0x85`
advance spacing from packed x `28` to `46` and `46` to `64` without compact
entries, and the final object contains only two visible `!` entries at
coords `0x0001` and `0x0604`.

Fixture `transparent default-filtered control enters unflagged fixed-record
path` proves the unflagged side of the same `0xd0f0` entry for
`ESC &p3X!\x05!`: payload values route `d04a d0f0 d04a`; the C0 byte `0x05`
substitutes host `0x20`, maps to unflagged glyph `0`, uses inline record
`01 02 00 00 00 00 00 70`, positions x/y `40/20`, queues compact coord
`0x4802` in bucket `1`, and renders in the same selected bucket as surrounding
unflagged `!` glyphs at coords `0x7601` and `0x7a03`. The bridge context slots
begin `(0x00000100, 0, 0, 0)`, and selected bucket `1` renders row count `10`,
row width `74`, digest
`89629435e063529ce7150d603ed9be37a74658317db3e97a4ae01b1c8d64f9d9`.

Fixture `transparent nonzero filters route controls through printable path`
proves the opposite filtering polarity for `ESC &p4X!\x05\x80!`: selected
context byte `1` and local filtering word `1` route all four values through
`0xd04a`; C0 byte `0x05` maps to glyph `0x04`, high-control byte `0x80` maps
to glyph `0x7f`, and all four entries render.

Fixture `transparent nonzero high-control byte queues tall glyph bucket`
extends that nonzero high-control branch with `ESC &p3X!\x98!`. Payload byte
`0x98` routes through `0xd04a`, maps to glyph `0x97`, glyph entry `0x01781e`,
rows `29`, width `17`, and compact coord `0xfd01` in bucket `-1`; the
surrounding `!` bytes remain in bucket `0` at coords `0x0001` and `0x0403`.
The bucket `-1` render has row count `44`, width `46`, and digest
`bd7ad3016d15c1dc2ef12adaeb1091a58f26473c0ecfc7ac13bfaf268c383e90`;
bucket `0` renders row digest
`4bf2f0104b14bfa598b8acfcf8cfb69ccb4419c234f02f256781b6b236110300`.

Fixture `transparent nonzero high-control upper bound remains printable`
proves the top-of-range sibling `ESC &p3X!\x9f!`. Payload byte `0x9f` routes
through `0xd04a`, maps to glyph `0x9e`, glyph entry `0x016d1e`, rows `30`,
width `15`, and compact coord `0xee01` in bucket `-1`. The surrounding `!`
bytes again remain in bucket `0`; the bucket `-1` render has row count `44`,
width `45`, and digest
`ec0f944207561c1b9c9139749c3e37d122aebf53e2a50849dd8703416545c719`, while
bucket `0` keeps digest
`4bf2f0104b14bfa598b8acfcf8cfb69ccb4419c234f02f256781b6b236110300`.

Fixture `transparent nonzero high-control interior samples remain printable`
fills the primary interior range between the `0x80`, `0x98`, and `0x9f`
boundary checks. Payload bytes `0x81`, `0x88`, `0x90`, and `0x97` all route
`d04a d04a d04a`, map to glyphs `0x80`, `0x87`, `0x8f`, and `0x96`, queue
the high-control glyph in bucket `-1`, leave surrounding `!` entries in
bucket `0`, and render selected-bucket digests
`841384c82ec301334f603178a4ad28152c7818bab08c8b829bb769a356b27c04`,
`64ab78cb858eb0560f08304101c4a6870daee5a94144ce028e5807952d479850`,
`e99bffbc8e6c0c9179536c5c90927a72ba3047cf7f43e43355552f0e5aa4fae4`, and
`a97b85527284735826a97ef1998d72e5841bd4331c2f2aeea24d444a35179acd`.

Fixture `transparent secondary high-control byte enters segmented page-record
path` composes SO with the transparent branch for `SO ESC &p3X!\x80!`. SO
handler `0xc6b8` changes selector `0x782f06` from `0` to `1`; delayed handler
`0x12452` restores record `80 58 00 03 00 00`, consumes payload `21 80 21`,
and routes all three values through `0xd04a`. Both `!` bytes read source
context `0xc00ae122` slot `1`, map to glyph `0`, and queue short selector-1
coords `0xc5ff` and `0xc901`. The high-control byte `0x80` reads the same
source context, maps to glyph `0x5f`, reports glyph entry `0x02e122`, rows
`20062`, width `74`, compact coord `0x1c01`, and enters segmented page-record
storage with selector `0x2001`, first segment/bucket `156`/`1248`, and last
segment/bucket `0`/`0`. The bridge carries context slots
`(0x440946b4, 0xc00ae122)`, and selected bucket `0` renders row count `80`,
row width `256`, digest
`57bb3fd895be358ff325e26ae58a3b0dc526c5b08b382eb90e7273e6227fbfbb`.

Fixture `transparent secondary segmented render prefix exposes source
boundary` renders the produced secondary segmented buckets until the current
source model fails. Buckets `0..448` render as `57` buckets with aggregate
digest `292eafb8b558bd36ca0caa5caa2771976c0e611456ac0b610ec8916b9d1f03f9`;
bucket `448` is segment `56`, row count `32`, row width `102`, digest
`823854dc77b9234cf90f71bebcc3da7280c72dfed2bf05315e757b2d1c58c4e3`. The
first failure is bucket `456`, selector `0x2001`, glyph `0x5f`, segment
`0x39`, row skip `7296`, source `0x03fe22`, needing `1280` bytes with only
`478` bytes available. The resolved glyph source is entry/bitmap `0x02e122`,
delta `0`, mode `0`, rows `20062`, width `74`, and render span `10`.

Disassembly
`generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst` moves
this from a renderer-arithmetic uncertainty to a physical/resource-window
uncertainty. Helper `0x1f354` uses the bit-30 offset-table form and adds the
selected table entry directly; secondary `LINE_PRINTER` table index `0x5f` is
zero, so firmware reads the record header at file offset `0x02e122` as the
glyph entry. Segmented renderer `0x1f1f0` applies `segment << 7`, clamps to at
most `0x80` rows, multiplies by even byte span `10`, and advances the bitmap
pointer to file offset `0x03fe22`. Since `notes/resource-rom.md` maps resource
file offset `N` to firmware address `0x080000 + N`, the unresolved source read
is firmware address range `0x0bfe22..0x0c0321`; only `0x0bfe22..0x0bffff`
comes from the verified `IC32,IC15` pair. `notes/firmware-startup.md` verifies
scanner `0x41a` walking records through `0x0ae122` and terminating at
`0x0b2f80`, but the hardware mapping at `0x0c0000..0x0c0321` remains unknown.

Fixture `transparent secondary segment-57 continuation policies diverge after
verified bytes` makes that memory-map dependency executable. The segment-57
compact payload `00 01 5f 39 1c 01` has glyph `0x5f`, segment `0x39`, coord
`0x1c01`, row skip `7296`, row count `128`, span `10`, width `74`, and source
offset `72960`. The `0x40000`-byte verified resource image supplies the first
`478` bytes of the `1280`-byte segment read, so the current-band rows are
identical under tested continuation policies with digest
`f0c1127f9e6b203f9829ab43f159b89c3f7dda687a47d4c09971077eac55c96e`. The
fallback rows diverge: mirroring the resource pair gives digest
`75cc8b60cd33f5c659ad702530ebacdc7685f2b75d63e18b9ce055383153f142`,
appending the code pair gives
`dc58960aff83e718df147897de51944939626c4e8422a53da5443bca48a53df5`, and
zero-fill gives
`6373cecdf5f20d78b01abe5aa65c051d82ddef345b7cf7fe1504f93c9cb2c425`.
Fixture `0x41a HEAD scanner would duplicate records under simple resource
mirror` proves that the full-mirror continuation is scanner-visible: scanning
`IC32,IC15 + IC32,IC15` would see `HEAD` at offsets `0` and `0x40000`, walk
`48` typed records, and terminate at final probe `0x80000`.

### Confidence

High for delayed snapshot/restore, absolute payload count, `1a 58` and
`1a xx` probe handling, default filtering, nonzero filtering, fixed-space
cursor advance, page-record object bytes, bridge context slots, and rendered
rows, plus sampled primary high-control interior values and two taller primary
high-control bucket-crossing glyphs because each is fixture-pinned against
disassembly-backed helpers. High for the secondary selector/routing/page-record
boundary because the SO plus transparent fixture pins handler `0xc6b8`, source
context `0xc00ae122`, segmented selector `0x2001`, bridge context slots, and a
selected-bucket render digest; the secondary render-prefix fixture pins
buckets `0..448` and the first source-read boundary at bucket `456`. High for
the conclusion that segment-57 fallback rows depend on an unverified memory-map
policy, because the mirror, code-pair, and zero-fill continuation fixtures all
share the same current-band digest and diverge only in fallback row digests.
Medium for the actual hardware source interpretation after that boundary: the
verified `IC32,IC15` resource pair ends at `0x0bffff`, but
`notes/formatter-interface-pca.md` records formatter ROM capacity and
address-controller facts that allow a larger or altered ROM region. Medium also
for manual names for the filter bytes.

### Fixtures

- `0x11f5a/0x12452 transparent text restores and consumes counted bytes`
- `0x12452 transparent text probe keeps non-0x58 byte`
- `transparent data parser trace feeds page-record queue`
- `transparent non-0x58 probe byte reaches page-record output`
- `transparent data control payloads advance through fixed-space path`
- `transparent default-filtered control enters unflagged fixed-record path`
- `transparent nonzero filters route controls through printable path`
- `transparent nonzero high-control byte queues tall glyph bucket`
- `transparent nonzero high-control interior samples remain printable`
- `transparent nonzero high-control upper bound remains printable`
- `transparent secondary high-control byte enters segmented page-record path`
- `transparent secondary segmented render prefix exposes source boundary`
- `transparent secondary segment-57 continuation policies diverge after verified
  bytes`

### Disassembly Evidence

- `generated/disasm/ic30_ic13_transparent_data_handler_011f5a.lst`
- `generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst`
- `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`
- `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`
- `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`

### Unresolved Middle Edges

- `0x124f8..0x1252a`: high-control nonzero filtering is now fixture-backed for
  a short primary bucket (`0x80`), interior primary samples (`0x81`, `0x88`,
  `0x90`, and `0x97`), two taller primary bucket-crossing glyphs (`0x98` and
  top-of-range `0x9f`), and a secondary segmented page-record boundary
  (`SO ESC &p3X!\x80!`). Remaining work is the secondary segment-57
  physical/resource-window source interpretation at bucket `456`. The
  disassembly-backed compact path reaches glyph `0x5f`, segment `0x39`, file
  source `0x03fe22`, firmware source `0x0bfe22`, and required byte range
  `0x0bfe22..0x0c0321`, with only `478` bytes inside the verified resource-pair
  image. Fixture
  `transparent secondary segment-57 continuation policies diverge after verified
  bytes` proves mirror, code-pair continuation, and zero-fill all produce the
  same current-band digest but different fallback row digests, so the remaining
  requirement is board or emulator memory-map evidence for
  `0x0c0000..0x0c0321`. The simple mirror candidate is constrained by fixture
  `0x41a HEAD scanner would duplicate records under simple resource mirror`,
  because a full mirror would duplicate scanner records unless hardware/gating
  hides it from startup scanner reads. The edge is explicitly outside the verified
  `IC32,IC15` resource image in `data/rom_manifest.json`, and the hardware note
  in `notes/formatter-interface-pca.md` makes address-controller/jumper decode
  the candidate state to resolve. It is not primary route polarity, sampled
  primary interior values, or the renderable secondary prefix through bucket
  `448`.

## Text Source Objects And Compact Buckets

Status: composed as the shared source-object and compact-bucket cluster
between printable parser entry `0xd04a` and renderer-facing compact text
objects. This checkpoint covers multiple writers to the same source
fields: unflagged/inline handoff `0xd3b2`, flagged/built-in handoff
`0xd824`, shared producer `0x12f2e`, and span exits `0xd4ac`/`0xd8fc`.

Concept: `0xd04a` converts one printable host byte into scratch source
object `0x782d7e` through `0x1393a`. Source byte `+0x10` selects either
the unflagged inline/downloaded path or the flagged built-in path. Both
paths position the source by writing `+0x12`, `+0x14`, and `+0x16`, then
call `0x12f2e`; `0x12f2e` converts those fields plus glyph metrics into
short or segmented compact bucket entries consumed by `0x1387c`,
`0x1effe`, `0x1f034`, `0x1f0d2`, `0x1f1f0`, and `0x1f264`.

### Field Groups

- Canonical source object `0x782d7e`:
  - `+0x00`: selected current-font context pointer written by `0x1393a`.
  - `+0x04`: built-in glyph-entry pointer on flagged paths, or
    inline/downloaded fixed-record pointer on unflagged paths.
  - `+0x08`: signed horizontal source offset used by `0xd3b2` and
    `0xd824`.
  - `+0x0a/+0x0b`: mapped compact glyph index copied by `0x12f2e`.
  - `+0x10`: source class flag tested by `0xd04a`; zero selects
    `0xd140`/`0xd3b2`, nonzero selects `0xd550`/`0xd824`.
  - `+0x12`: positioned x-like source coordinate written by `0xd3b2`
    or `0xd824`.
  - `+0x14`: positioned y-like source coordinate written by `0xd3b2`
    or `0xd824`.
  - `+0x16`: page-root/render context slot written from `0x78297e` and
    consumed by `0x12f2e`.
  Evidence: `generated/analysis/ic30_ic13_printable_text_path.md`,
  `generated/analysis/ic30_ic13_text_cursor_span_flow.md`, and fixtures
  `0xd824-modeled positioned text source fields`,
  `0xd824-modeled negative-overflow positioned source fields`,
  `0xd3b2-modeled unflagged source fields`,
  `0xd3b2-modeled unflagged overflow source fields`, and
  `0x1393a-modeled selected inline source object fields`.
- Canonical cursor/metric inputs:
  - `0x782c8a`: current horizontal cursor read by `0xd140`,
    `0xd550`, `0xd3b2`, and `0xd824`, then committed after queue/limit
    handling.
  - `0x782c8e`: current vertical cursor used by positioning and span
    checks.
  - `0x782a58`: pending previous-width latch; when set, both paths
    center against `0x782a5a` / `0x782a5c`.
  - `0x782a5a`: latched previous width.
  - `0x782a5c`: latched previous advance.
  - `0x782a6e`: path precheck result from `0xd28a` or `0xd6bc`; a
    nonzero value suppresses queue and span-update side effects. The
    paired fixture `0xd28a and 0xd6bc prechecks share continue reject and
    wrap decisions` covers result `0` continue, result `1` reject, and
    wrap recovery through `0xf054`.
  - `0x78315c`: default HMI advance used when no source-specific
    advance is available.
  - `0x78318e`: alternate metrics / previous-width mode flag.
  Evidence: generated text-cursor report steps 1-4 and state scan;
  fixtures `two printable byte stream combines compact text entries`,
  `two printable byte stream with line-printer HMI renders subbyte
  entry`, `0xd824-positioned short bucket object fields`, and
  `0xd28a and 0xd6bc prechecks share continue reject and wrap decisions`.
- Canonical page/root publication inputs:
  - `0x78297a`: current page root ensured through `0x10084` before
    drawable source queueing.
  - `0x78297e`: selected page-root font slot index copied into source
    `+0x16`.
  - `0x78297f + slot`: live flag set by both `0xd3b2` and `0xd824`.
  - page-root flags word `+0x14` bit `0`: retry/finalization marker set
    by both text queue no-room paths before `0xff1e` publishes the old
    root.
  Evidence: disassembly `0xd458..0xd4a0` and `0xd8a8..0xd8f0`;
  fixtures `0x1387c page-record bucket allocator reuses matching short
  object`, `selected inline source queues and renders through unflagged
  path`, and `0xd3b2 and 0xd824 text queue no-room retry preserves source
  and rows`.
- Canonical span/bounds state:
  - `0x783184`: enables span/bounds updates in `0xd4ac` and `0xd8fc`.
  - `0x783185`: selects alternate y-offset handling.
  - `0x783186`: low-x flush threshold; crossing below it calls
    `0x12714` then `0x126e2`.
  - `0x783188`: high-x watermark updated after placement.
  - `0x78318a`: high-y watermark updated after placement.
  - flagged context fields `+0x16`, `+0x18`, and `+0x1a` are read by
    `0xd8fc`.
  - unflagged context fields `+0x2b`, `+0x2c`, and `+0x2d` are read by
    `0xd4ac`.
  Evidence: generated text-cursor report context table and disassembly
  `0xd4ac..0xd548`, `0xd8fc..0xd992`.
- Derived/cache producer state:
  - `0x782a7c`: bucket index derived by `0x12f2e` from source `+0x14`
    and segment height.
  - compact coordinate: source `+0x12` and `+0x14` become the packed
    coordinate word copied into short or segmented entries.
  - selector bits: source context slot forms low selector bits; width
    greater than threshold sets bit `0x1000`, tall rows set bit
    `0x2000`, and wide+tall rows set both.
  - short compact objects use object size `0x26`, capacity `0x0a`, and
    entries `glyph, coord`; segmented compact objects use object size
    `0x28`, capacity `0x08`, and entries `glyph, segment, coord`.
  Evidence: `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`
  and fixtures `0x12f2e-modeled unflagged short bucket object fields`,
  `0x12f2e-modeled unflagged width byte selects compact mode bit`,
  `0x12f2e-modeled unflagged tall inline bucket objects`, and
  `0x12f2e-modeled unflagged wide tall inline bucket objects`; addressed
  allocator/retry evidence is fixture-backed by
  `addressed 0x12f2e selector-mode matrix allocates and renders all compact
  modes`,
  `0xd3b2 and 0xd824 text queue no-room retry preserves source and rows`
  and `0xd3b2 and 0xd824 segmented text queue no-room retry preserves
  source and rows`.
- Parser scratch:
  - `D5` enters `0xd04a` as the printable host byte.
  - `0xd04a` normalizes bytes above `0xff` through `0xd99a`, masks
    high-bit bytes when `0x783132` and `0x783133` allow it, and wraps
    primary-map high-bit masking with `0xc6b8` / `0xc68a`.
  - `0x783132` and `0x783133` are high-character/symbol-state flags
    affecting whether bytes above `0x7f` are masked before `0x1393a`.
  Evidence: disassembly `0xd04a..0xd0e8` and generated printable-text
  path steps 6-9; fixture
  `0xd04a printable entry normalizes over-0xff and high-bit values`; fixture
  `0xd04a high-character flags and selected slot choose mask behavior`.
- Unknown:
  - live CPU register snapshots for every source class through the
    entire `0xd04a -> 0x1393a -> 0xd140/d550 -> 0x12f2e` chain.
  - complete semantic names for the span watermarks beyond their tested
    x/y threshold behavior.

### Writers

- `0xd04a` writes no final compact object directly; it normalizes the
  host byte, calls `0x1393a(host_byte, 0x782d7e)`, dispatches by source
  `+0x10`, and clears `0x782a6d` before returning.
- `0xd140` and `0xd550` run the path-specific precheck
  `0xd28a`/`0xd6bc`, write `0x782a6e`, compute cursor advance, and
  commit `0x782c8a` only after queue/clamp handling.
- `0xd3b2` writes unflagged source `+0x12/+0x14/+0x16`, sets the
  `0x78297f + 0x78297e` live flag, calls `0x12f2e`, and retries through
  `0xff1e` / `0x10084` when allocation fails.
- `0xd824` writes the same positioned source fields for flagged
  built-in glyph entries and shares the same `0x12f2e` retry path.
- `0x12f2e` writes `0x782a7c`, derives selector/coord fields, and calls
  `0x1387c` with either short-entry capacity `0x0a` / size `0x26` or
  segmented capacity `0x08` / size `0x28`.
- `0xd4ac` and `0xd8fc` update span watermarks and call `0x12714` /
  `0x126e2` when current x is below `0x783186`.

### Readers And Consumers

- `0x1393a` consumes current font context and symbol map state to write
  source `+0x00`, `+0x04`, `+0x0a`, and `+0x10`.
- `0xd28a` and `0xd6bc` consume source metrics, `0x783190` wrap state,
  page extents, and cursor state to decide whether queueing is allowed.
- `0x12f2e` consumes source `+0x04`, `+0x0a/+0x0b`, `+0x10`,
  `+0x12`, `+0x14`, and `+0x16`.
- `0x1387c` consumes the producer selector/key and current page root to
  reuse or allocate the compact bucket object.
- Renderers consume the compact bucket classes through `0x1effe` and
  dispatch to `0x1f034`, `0x1f0d2`, `0x1f1f0`, or `0x1f264`.

### Output Effect

- Flagged built-in `LINE_PRINTER` host byte `0x21` maps through
  `0x1393a` to glyph `0x20`, glyph-entry pointer `0x015330`, and flag
  `1`. With cursor `(10,21)`, `0xd824` applies glyph offsets x `6` and
  y `21`, writes source `(16,0)`, and `0x12f2e` emits short object
  `00 00 00 00 00 00 00 01 20 00 01`.
- The same flagged path with source x-offset `-26` returns overflow
  correction `0x00100000`, writes source `(32,0)`, and emits compact
  coord `0x0002`.
- Unflagged inline source with record `02 03 04`, cursor `(10,20)`,
  printable offset `7`, and source x-offset `5` writes source `(22,22)`,
  selector `0x0003`, bucket `1`, coord `0x6601`, and short object
  `00 00 00 00 00 03 00 01 01 66 01`.
- Unflagged width `0x11` sets selector `0x1003`; rows `0x81` sets
  selector `0x2003`; width `0x11` plus rows `0x81` sets selector
  `0x3003`. The segmented cases emit two objects for segment `1` and
  segment `0`, with bucket indices `9/1` or `8/0` depending on the
  positioned y coordinate.
- Fixture `addressed 0x12f2e selector-mode matrix allocates and renders all
  compact modes` runs the four unflagged selector modes through real
  addressed `0x1381c` storage in one page-record state block. Glyph `1`
  queues selector `0x0003` short object
  `00 00 00 00 00 03 00 01 01 66 01` at `0x00d09004`; glyph `2`
  queues selector `0x1003` wide object
  `00 d0 90 04 10 03 00 01 02 66 01` at `0x00d0902a`; glyph `3`
  queues selector `0x2003` segmented objects for buckets `9/1`; glyph `4`
  queues selector `0x3003` segmented-wide objects for buckets `9/1`.
  The resulting bucket heads are bucket `1 -> 0x00d090c8` and bucket
  `9 -> 0x00d090a0`; bucket word `1` dispatches object bytes
  `0x30`, `0x20`, `0x10`, and `0x00` through `0x1effe`, while bucket word
  `9` dispatches `0x30` and `0x20`. Render row digests are
  `c9de5a8a4ed4f2805e35e1a7c8bdad2f6f832fc129bd26f5ec49a82a6023b25b`
  for bucket `1` and
  `dfd0b3d07e16f8d06a8ef12c1c51dedac61149493fb1e90981866da521e98e58`
  for bucket `9`.
- The selected inline/downloaded fixture starts at `0x1393a`: host
  `0x21` maps to glyph `0x01`, record `02 03 04 00 00 00 00 80`,
  source flag `0`, then queues and renders through the unflagged path
  with context slot `3`.
- Fixture `unflagged printable d4ac low-watermark flush renders span`
  uses the same inline/downloaded source class with context bytes
  `+0x2b=7`, `+0x2c=0`, and `+0x2d=10`. It queues host byte `0x21`
  through `0x1393a` / `0xd3b2` into compact coord `0x7a00`, advances
  x to `28` through the `0xd140` cursor path, and then reaches
  `0xd4ac` before the shared `0x12714` span output.
- The two-printable stream fixture proves the ordinary flagged path can
  repeat: `!!` maps both host bytes through `0xd04a`/`0x1393a`,
  advances the cursor through `0xd550`, reuses the same short object,
  and renders compact entries at `0x0001` and `0x0002`; the initialized
  HMI fixture renders the second glyph from coord `0x0202`.
- Fixture `0xd04a printable entry normalizes over-0xff and high-bit
  values` pins the printable-entry normalization boundary before source
  placement. Entry value `0x100` with nonzero `0xd99a` result exits before
  `0x1393a`; entry value `0x100` with zero `0xd99a` result substitutes
  host `0x7f`, maps to glyph `0x7e`, and builds glyph entry `0x0166de`.
  Primary high byte `0xa1` with both high-character flags clear masks to
  host `0x21`, wraps source-object build with `0xc6b8` / `0xc68a`, and
  reaches the same glyph `0x20` / entry `0x015330` as ordinary `!`.
- Fixture `0xd04a high-character flags and selected slot choose mask
  behavior` closes the sibling flag/slot cases for the same high byte:
  either `0x783132` or `0x783133` set preserves host `0xa1`, maps to glyph
  `0xa0`, and builds glyph entry `0x017256`, while flags clear with selected
  secondary slot `1` still masks to host `0x21` but skips the primary
  `0xc6b8` / `0xc68a` wrapper.
- Fixture `0xd28a and 0xd6bc prechecks share continue reject and wrap
  decisions` covers the paired prequeue gate before `0xd3b2` or `0xd824`.
  With packed current x `0x00020000`, remaining limit `0x00060000`,
  measure `0x00040000`, y `5`, lower bound `2`, and extent `4`, both
  handlers return `0` and allow queueing. With current x `0x00050000`,
  remaining limit `0x00030000` is smaller than the same measure, so both
  handlers return `1` and suppress queueing when `0x783190` is clear.
  With `0x783190` set, the same horizontal reject calls `0xf054`, retries
  from recovered x `0`, and returns `0`. With y `18` and page extent `20`,
  both handlers return `1` from the vertical-extent check.
- Fixture `0xd3b2 and 0xd824 text queue no-room retry preserves source and
  rows` closes the paired short-text allocation-failure edge. For the
  flagged `0xd824` source, the first addressed `0x12f2e` queue tries to
  allocate object size `0x26`, receives pointer `0`, preserves source
  `(mapped=0x20, flag=1, x=16, y=0, slot=0)`, sets page-root flag
  `+0x14.0`, publishes the old bucket prefix
  `00 00 00 00 00 00 00 01 20 00 01` through `0xff1e`, ensures a fresh
  root through `0x10084`, retries at object pointer `0x00d06004`, and
  renders the same 22 rows through `0x1effe` with digest
  `235986bdd28abaaef315961960ac87d846cbb5228ca5c07ef560df56501a30e3`.
  For the unflagged `0xd3b2` source, the same retry sequence preserves
  `(mapped=0x01, flag=0, x=22, y=22, slot=3)`, publishes/retries bucket
  prefix `00 00 00 00 00 03 00 01 01 66 01`, dispatches bucket word `1`
  through `0x1effe`, and renders the same 22 rows with digest
  `d696456ad5c91a1a568d1b1c45fcf7e322fe15c12a3805783145ccc7074806e6`.
- Fixture `0xd3b2 and 0xd824 segmented text queue no-room retry preserves
  source and rows` closes the same no-room edge for segmented/tall compact
  objects. The unflagged `0xd3b2` source `(mapped=0x01, flag=0, x=22,
  y=22, slot=3)` fails first at bucket `9`, segment `1`, selector
  `0x2003`, object size `0x28`; retry emits bucket `9` object
  `00 00 00 00 20 03 00 01 01 01 66 01` and bucket `1` object
  `00 00 00 00 20 03 00 01 01 00 66 01`, and published/retried rows
  match for bucket words `9` and `1` with digests
  `ab4ebb802552dc6ad497da75344f369876cc9f0fabbffdfc7801213b9a7ff372`
  and `918ec4cca20024057ec1b82577b2ab5c039c6fc9a3f756be9bbb62a088bab7ac`.
  The flagged `0xd824` tall built-in source `(mapped=0x1f, flag=1, x=0,
  y=0, slot=0)` fails first at bucket `64`, segment `8`, selector
  `0x2000`; retry emits all nine bucket indexes
  `[0, 8, 16, 24, 32, 40, 48, 56, 64]`, with first prefix
  `00 00 00 00 20 00 00 01 1f 08 00 00` and last prefix
  `00 00 00 00 20 00 00 01 1f 00 00 00`. Published/retried rows match
  for bucket words `64` and `0` with digests
  `c2c1504836f113d5a2c89168702ccb008dcc93126cfcf55a57964ba889170318`
  and `15b6d4e1c1691ca7d6204259f3dfff5c96575588c0c71c8ff011898581be4f35`.

### Confidence

High for source field meanings, paired writer behavior, `0x12f2e`
short/segmented object shapes, selector bits, and rendered compact rows
because all are backed by disassembly and executable fixtures. Medium
for full live CPU/register continuity across the entire path because
the fixtures model selected source/page objects rather than running a
full 68000 interpreter through every source class and allocator branch.

### Fixtures

- `0xd824-modeled positioned text source fields`
- `0xd824-modeled negative-overflow positioned source fields`
- `0xd824-positioned short bucket object fields`
- `0xd824-negative-overflow short bucket object fields`
- `0xd04a printable entry normalizes over-0xff and high-bit values`
- `0xd04a high-character flags and selected slot choose mask behavior`
- `0xd28a and 0xd6bc prechecks share continue reject and wrap decisions`
- `0xd3b2 and 0xd824 text queue no-room retry preserves source and rows`
- `0xd3b2 and 0xd824 segmented text queue no-room retry preserves source
  and rows`
- `0xd3b2-modeled unflagged source fields`
- `0xd3b2-modeled unflagged overflow source fields`
- `addressed 0x12f2e selector-mode matrix allocates and renders all
  compact modes`
- `0x12f2e-modeled unflagged short bucket object fields`
- `0x12f2e-modeled unflagged width byte selects compact mode bit`
- `0x12f2e-modeled unflagged tall inline bucket objects`
- `0x12f2e-modeled unflagged wide tall inline bucket objects`
- `0x1393a-modeled selected inline source object fields`
- `selected inline source queues and renders through unflagged path`
- `selected inline page-record object preserves context through 0x1edc6
  bridge`
- `unflagged printable d4ac low-watermark flush renders span`
- `single printable byte stream builds positioned compact text object`
- `two printable byte stream combines compact text entries`
- `two printable byte stream with line-printer HMI renders subbyte
  entry`
- `0x1f0d2 renders wide inline compact payload row`
- `0x1f1f0 renders segmented inline compact payload row`
- `0x1f264 renders segmented wide inline compact payload row`

### Disassembly Evidence

- `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`:
  `0xd04a..0xd0e8`, `0xd140..0xd550`, `0xd550..0xd824`,
  `0xd824..0xd8fc`, and span helpers.
- `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`:
  compact coord, bucket index, selector-bit, short, and segmented
  producer logic.
- `generated/analysis/ic30_ic13_printable_text_path.md`:
  host-byte route, source object field table, and live parser entry
  evidence.
- `generated/analysis/ic30_ic13_text_cursor_span_flow.md`:
  paired text paths, source/context field use, state references, and
  reproduction contract.
- `generated/analysis/ic30_ic13_text_glyph_index_flow.md`:
  `0x1393a` map/context evidence upstream of this checkpoint.

### Unresolved Middle Edges

- `0xd04a..0x1393a`: byte normalization and source-object build are
  disassembled and fixture-backed for ordinary printable entry,
  over-`0xff` nonzero `0xd99a` exit, over-`0xff` fallback to `0x7f`,
  the primary high-bit mask wrapper, either high-character flag preserving
  a high byte, and selected secondary slot masking without the primary
  wrapper. Remaining risk is broader high-byte values and live CPU-register
  coverage around the modeled branch, not these specific normalization
  outcomes.
- `0xd28a..0xd3aa` and `0xd6bc..0xd81a`: precheck wrap/recovery paths
  are fixture-backed for the paired result semantics of `0x782a6e`: ordinary
  continue, horizontal reject with queue suppression, horizontal wrap recovery
  through `0xf054`, and vertical-extent reject. Remaining risk is the full
  live parser/output edge for every metric source, not the meaning of the
  precheck result or the shared reject/retry gate.
- `0xd47a..0xd4a0` and `0xd8ca..0xd8f0`: allocation failure retry via
  `0xff1e` / `0x10084` is fixture-backed for both paired short-text source
  writers. The covered canonical state before the retry is the positioned
  source object `0x782d7e`, selected slot byte `0x78297e`, live-slot byte
  `0x78297f + slot`, current root pointer `0x78297a`, and root retry flag
  `+0x14.0`. The covered derived state after success is the `0x12f2e`
  selector/key plus the compact bucket object under page-root `+0x1c`;
  the fixture proves the old published bucket prefix, fresh-root allocation,
  retried object pointer/bytes, `0x1effe` dispatch, and row digest match
  for flagged `0xd824` and unflagged `0xd3b2` short and segmented/tall
  objects. Remaining risk is a full live CPU-register trace and broader
  selector-mode cross-products, not the paired failure-return semantics for
  these object families.
- `0xd4ac..0xd548` and `0xd8fc..0xd992`: span watermark writes and the
  downstream `0x12714` / `0x126e2` handoff are composed in
  `Text Span Flush And Fixed-Width Spans`. That section covers
  downstream `0x12714` allocation-failure retry, `0x1354a` portrait
  split insertion, and `0x136d2` landscape nonempty fixed-list insertion
  with fixtures `0x12714 allocation failure publishes page and retries
  span`, `0x1354a portrait text span split queues adjacent buckets`, and
  `0x12714 landscape span inserts into nonempty fixed list`. The remaining
  unresolved edge here is broader span metric/source cross-products, not
  the earlier paired short-text source-handoff allocation failure path.
- `0x12f2e..0x1306e`: short, wide, segmented, and segmented-wide producer
  shapes are fixture-backed through both modeled object bytes and addressed
  `0x1381c` allocator storage. The addressed selector-mode matrix proves
  all four selector values `0x0003`, `0x1003`, `0x2003`, and `0x3003`
  share page-record storage, bridge/render dispatch through `0x1effe`,
  and stable row digests. Remaining risk is a full live CPU/register trace
  through dense parser-produced allocator memory and broader legal font
  descriptor cross-products, not the selector-mode object production
  contract.

## Built-In Resource Scan And Candidate Windows

Status: composed as the built-in resource producer state that feeds font
selection. The low-level record layout and glyph payload ledger remain in
[resource-rom.md](resource-rom.md); this section names the candidate-list
state consumed by `0x1569c`, `0x156de`, `0x1519a`, `0x153c6`, `0x14398`,
and the parsed font-selection checkpoints below.

Concept: the `IC32,IC15` resource ROM does not become visible pixels by
itself. Firmware first scans `HEAD`/typed records, classifies accepted
font records into candidate pointer windows, activates a class-specific
window, then filters and chooses one selected context longword. That
selected longword later feeds `0xc428`, `0x1393a`, `0xd824`, `0x12f2e`,
and the compact glyph renderers.

### Field Groups

- Canonical resource records:
  - verified built-in `HEAD` chain: 24 typed records from firmware
    address `0x08004c` through `0x0ae122`, terminating at `0x0b2f80`.
  - accepted `HEAD`-path records use byte `+0x0d` for candidate flag
    bits 28..29, set high flag `0x40000000`, and mirror byte
    `+0x0c == 2` into high flag `0x04000000`.
  - class/orientation byte `+0x20`, symbol word `+0x22`, spacing byte
    `+0x21`, HMI source longword `+0x24`, height-like words
    `+0x28/+0x2a`, and comparator bytes `+0x2f..+0x31` are the
    record fields consumed by the candidate filters and chooser.
- Canonical candidate-list state:
  - `0x782324`: shared candidate pointer-list base.
  - `0x78278e`: total accepted candidate count.
  - `0x782790..0x78279e`: candidate-list counts by class/range window.
  - `0x7827a0..0x7827b4`: candidate-list cursor/window starts.
  - `0x782884`: resource scan cursor.
  - `0x78288c` / `0x782890`: scan start/end, initially
    `0x00080000..0x000ffffe` for the built-in resource window.
  - `0x78287c`: active candidate-list pointer selected by `0x1569c`.
  - `0x7827b8`: active candidate-list count selected by `0x1569c`.
  - `0x7828a8`: selected candidate slot pointer after filtering and
    chooser steps.
- Derived/cache state:
  - class-one low/range counters are `0x782792 = 12` /
    `0x782794 = 0` for the verified built-ins.
  - class-zero low/range counters are `0x78279a = 12` /
    `0x78279c = 0` for the verified built-ins.
  - final cursor windows are `0x7827a0 = 0x782324`,
    `0x7827a4 = 0x782354`, `0x7827a8 = 0x782354`,
    `0x7827ac = 0x782354`, `0x7827b0 = 0x782384`, and
    `0x7827b4 = 0x782384`.
  - `0x1569c` derives active class-zero pointer/count
    `0x782354`/`12` when `0x782da3 == 0`, or class-one pointer/count
    `0x782324`/`12` otherwise, then marks selected list entries with
    high bit `0x80000000`.
- Parser scratch:
  - parsed font-selection request fields live in `0x782eec..0x782f04`
    and dirty flags `0x782f2c/2d`; they are consumers of the candidate
    windows, not part of the resource scan itself.
  - `ESC (` / `ESC )` symbol words are parser-produced inputs to
    `0x156de`, not resource-record fields.
- Firmware bookkeeping:
  - startup scanner `0x41a` and candidate scanner `0x1a616` both walk
    resource records but serve different phases. `0x41a` validates the
    `HEAD` chain and executable-record behavior; `0x1a616` /
    `0x1a9be` build font candidate windows.
  - initializer-cleared counters `0x782796` and `0x78279e` are not
    incremented by the decoded built-in `0x1a9be` body for the verified
    window; similarly named changes in downloaded-font fixtures belong
    to downloaded-font bookkeeping.
- Unknown:
  - cartridge/external resource behavior outside the verified built-in
    window `0x080000..0x0ffffe`.
  - final manual-facing names for record fields `+0x28..+0x31`; their ROM
    roles are pinned as decoded-height inputs and chooser tie-breakers.

### Writers

- `0x1a2e4` clears candidate counts, initializes the cursor windows at
  `0x782324`, sets scan bounds, and calls `0x1a616`.
- `0x1a616` scans resource regions, recognizes or skips signatures such
  as `HEAD`, `FONT`, `TABL`, `tabl`, and `DUMY`, and passes accepted
  font records to `0x1a9be`.
- `0x1a9be` writes candidate flags, increments `0x78278e`, partitions
  records by class/address range, and advances the relevant
  `0x7827a0..0x7827b4` cursor windows.
- `0x1569c` writes `0x78287c` / `0x7827b8` from the selected class
  window and sets active bit `0x80000000` in the chosen entries.
- `0x156de`, `0x1519a`, `0x153c6`, `0x14758`, and related filters
  mutate the active list by clearing the active bit on rejects, moving
  `0x78287c` to the first survivor, and shrinking `0x7827b8`.
- `0x14398` and comparator `0x13c06` choose `0x7828a8`, the selected
  candidate slot consumed by later context writers.

### Readers And Consumers

- `0x156de` reads active candidate symbol words through `0x15890` /
  `0x158be`, compares requested words from `0x782ef4` or `0x782f04`,
  and may fall back through `0x782f0c..0x782f18`.
- `0x1519a` reads requested heights from `0x782ef2` / `0x782f02` and
  decoded built-in heights through `0x13bca`.
- `0x153c6` reads requested spacing/pitch from `0x782eef` /
  `0x782eff` and `0x782ef0` / `0x782f00`, then reads resource byte
  `+0x21` and decoded pitch through `0x13b76`.
- `0x14398` consumes active survivors and uses `0x13c06` / `0x1428c`
  to rank resource window, decoded height, byte `+0x2f`, signed byte
  `+0x30`, and byte `+0x31`.
- `0x13eb8` consumes the selected candidate state and writes current
  context records `0x782ee6` / `0x782ef6`; `0x14c64` then rebuilds the
  active character map for printable text.

### Output Effect

The scan has no direct pixel output. Its visible effect is selection of
the built-in record whose metrics and glyph payloads are later rendered.
For the verified built-ins, parsed primary `0p10h12v0s0b3T` filters the
class-zero window to context `0xc008004c` and visible Courier rows.
Parsed secondary `0p16h8v0s0b0T` filters the class-one window to context
`0xc00ae122` and visible secondary Line Printer rows after SO. Symbol
miss fixtures prove fallback words `0x0115` and `0x000e` can still
select visible primary/secondary rows through these same windows.

### Confidence

High for the verified built-in scan, class/range counters, cursor
windows, active-window activation, concrete symbol/height/pitch filtering,
candidate chooser behavior, and downstream visible primary/secondary row
effects because the claims are backed by generated record reports,
disassembly, and executable fixtures. Medium for external cartridge
resources because no image is available in this repo.

### Fixtures

- `0x1a9be scanned font candidate list partitioning`
- `actual IC32/IC15 built-in records feed 0x1a9be partitions`
- `0x1569c activates concrete built-in candidate windows`
- `0x1519a filters concrete active candidates by height`
- `0x153c6 filters concrete active candidates by spacing and pitch`
- `parsed primary built-in font selection feeds visible page-record rows`
- `parsed secondary built-in font selection feeds visible SO page-record rows`
- `primary symbol miss falls back before visible page-record rows`
- `secondary symbol miss falls back before visible SO page-record rows`

### Disassembly Evidence

- `generated/disasm/ic30_ic13_font_resource_scan_01a2e4.lst`
- `generated/disasm/ic30_ic13_font_candidate_classify_01a9be.lst`
- `generated/disasm/ic30_ic13_font_candidate_activate_01569c.lst`
- `generated/disasm/ic30_ic13_font_candidate_filters_01519a.lst`
- `generated/analysis/ic32_ic15_font_records.md`
- `generated/analysis/ic32_ic15_resource_glyph_probe.md`

### Unresolved Middle Edges

- `0x1a616..0x1a9be`: verified for the built-in `IC32,IC15` low
  resource window; cartridge/external windows remain unverified until
  images are available.
- `0x14398..0x156de`: visible-output coverage exists for primary,
  secondary, two symbol-miss fallback streams, non-Roman symbol selections,
  the real final-`@` default-table/copy/default-font streams, and the
  final-`X` built-in and inline/downloaded font-ID streams. The `0x13eb8`
  transient/cache-hit exits are state-covered as preserved-output paths, while
  broader font-selection fallback/error combinations still need the same
  page-visible treatment when they change output.
- Record `+0x28/+0x2a` is pinned as the decoded-height input consumed by
  `0x1519a` through `0x13bca`; record `+0x2f..+0x31` is pinned as the
  same-class `0x1428c` chooser tie-breaker tuple. Final
  baseline/cell/manual terminology remains unresolved and is tracked in
  [resource-rom.md](resource-rom.md).

## Built-In Font Sample Printout Loop

Status: anchored as the firmware font-sample page generator from
resource candidate windows to printable sample bytes and an internal
page-object/rendered-surface checkpoint. It composes the ROM helpers that
replace the older direct `LASERJETII` smoke sample for built-in
baseline/cell correlation; the remaining boundary is physical comparison
against a known font/self-test page.

Concept: the sample printout is firmware-generated text, not host input.
Routine `0x1c204` checks whether font records exist, runs class-zero and
class-one passes, selects candidate rows, installs each selected resource
into the same current-font/page-root state as normal printing, then emits
labels, metric columns, and ROM sample byte runs through printable
handler `0xd04a`. This makes the sample page a built-in reference path
for how resource records become ordinary page-record text.

### Field Groups

- Canonical candidate/sample state:
  - `0x78278e`: accepted resource count checked by `0x1c204`.
  - `0x782798` and `0x782790`: class-zero and class-one pass counts
    tested by `0x1c28e..0x1c2c4`.
  - `0x78287c` / `0x7827b8`: active candidate window supplied to row
    helpers such as `0x1b50e`.
  - `0x7827ac` / `0x78279a`, `0x7827b0` / `0x78279c`,
    `0x7827b4` / `0x78279e`, `0x7827a0` / `0x782792`,
    `0x7827a4` / `0x782794`, and `0x7827a8` / `0x782796`:
    first- and second-window candidate pointer/count pairs selected by
    `0x1b50e` for modes `0..3`.
  - current and alternate selected contexts installed by `0x1c5e8` /
    `0x1cece` and consumed by `0xd04a`.
  - sample byte-run tables at `0x1c1cf` and `0x1c1e9`, emitted by
    `0x1cf34`.
  - source/category labels selected by `0x1ca2c` from table `0x1c170`.
  - page-record `context_slots`: durable page-object context identities used
    by `0x12f2e` and copied through the render bridge; the actual
    first-three-internal-rows fixture assigns slot 0 to `0x4008004c`, slot 1
    to `0x44080418`, and slot 2 to `0x44080868`.
- Canonical page/text environment:
  - current page root ensured through `0x10084`.
  - current vertical cursor `0x782c8e`, initialized by `0x1c916` to
    `0x0024`.
  - page-limit word `0x782db6`, checked by `0x1ca2c`, `0x1d050`,
    `0x1d868`, and `0x1dcf2`.
  - row-height/cache word `0x783f06`, written by `0x1ca2c` and
    adjusted by `0x1d050`.
  - current-font context record `0x782ee6`, page-root context slot, HMI,
    and VMI are installed through the same `0xc428` / `0x14c64`
    bridge used by parsed font selection.
- Derived/cache state:
  - `0x1c916` forces VMI/HMI defaults `0x0032` / `0x001e` and chooses
    portrait/landscape header text from `0x782da3`.
  - `0x1d050` derives the larger current/alternate row height and can
    start a continuation heading when the projected y would exceed
    `0x782db6`. Fixture
    `font sample page-limit branches trigger continuation calls` pins the
    shared page-limit state block for two consumers: `0x1ca2c` takes
    `0x1c9f6` when cursor y word `32` plus row height `13` equals limit `45`
    and fits at limit `95`; `0x1d050` advances first `COURIER` from
    `0x00520000` to `0x00900000`, takes continuation at limit `100`, calls
    `0x1ca2c(source=3,row=1,current=0x4008004c,selected=0x44080418)`, and fits
    at limit `1010`.
  - `0x1cf34` uses a fixed horizontal gap of `0x31` units before
    installing the alternate context and printing sample run 2 when
    `0x783132` is set.
  - `0x1d868` snapshots selected-font flag `0x783132` after
    `0x1cece(selected,row)` and before `0x1c5e8(current)`. Fixture
    `font sample alternate row fit gate follows 0x1d868` shows that a clear
    flag skips projection and returns D7 `0`; with the flag set, helper
    `0x1d8ba` projects first-`COURIER` y `0x00900000 -> 0x00ce0000`, derives
    projected bottom `219`, fits at page limit `300`, and returns D7 `1` when
    `0x782db6` equals `219`.
  - `0x1dcf2` uses shared calculator `0x1dc38` to probe current-y, optional
    second-selected-row, reset-y, and final selected-row placements. Fixture
    `font sample multi-probe preflight follows 0x1dcf2` pins mode `0`
    projections `0x00900000 -> 0x00ce0000 -> 0x010c0000`, reset raw subunits
    `0x1218` as packed y `0x01820000`, mode `1` reset projection
    `0x01820000 -> 0x01f20000`, and the D7 exits `0x1de1a`, `0x1dd8e`,
    `0x1de24`, and `0x1de16`.
  - `0x1d050` plus `0x1cfe4` derives row-to-row y advance from selected
    row line advance, current row height, prior `0x783f06`, and
    page-limit word `0x782db6`; the first-to-second named `COURIER` row
    fixture takes the no-continuation branch and advances y by `744`
    subunits.
  - `0x1cabe` derives visible row fields from the selected resource:
    `0x1cb26..0x1cb66` emits the `S/L/R/I` source prefix and two
    decimal row-index digits; `0x1d198` / `0x1d5fa` emits the built-in
    family/name column and pads it to 25 columns; `0x1cc6e` formats
    pitch and height with fixed-space calls through `0xd0f0`; and
    `0x1cd78` formats the symbol-set word into PCL-style notation such
    as `10U`.
  - `0x1d198` has a fallback table path for built-in records without an
    explicit name string: table `0x1c0a6` handles special symbol/family names,
    table `0x1c11a` maps family bytes to names, and strings at `0x1d17a`,
    `0x1d17c`, `0x1d183`, `0x1d18b`, and `0x1d192` add style/weight suffixes.
  - direct payload-render row hashes for the two ROM sample byte runs
    are evidence targets, not canonical runtime state.
- Parser scratch:
  - sample output is not fetched through `0xa904`; helpers such as
    `0x1d12e`, `0x1d6ea`, and `0x1d71e` call printable handler
    `0xd04a` directly for each emitted byte.
  - `0x1d76c` synthesizes a six-byte orientation command record at
    `0x78299e` before calling normal orientation handler `0x10220`.
  - `0x7828a0`, `0x7828a4`, and `0x78289f`: fast-probe selected slot,
    caller-visible candidate word, and primary/secondary selector used by
    `0x1b8ea` while `0x1b50e` resolves a row ordinal.
  - `0x7828ac` and requested symbol word `0x7821a0`: Roman-8
    substitution state used by `0x1b5a4..0x1b706` so the sample page
    may count a Roman-8 candidate twice; the duplicate ordinal passes
    the requested symbol word to `0x1cabe`.
- Firmware bookkeeping:
  - `0x783f0a`: recent-context list seeded by `0x1c9b8` and scanned by
    `0x1c540..0x1c5c6` after row emission; in the verified internal-font
    class-zero group it prevents re-appending already-seen contexts while
    still allowing duplicate Roman-8 substitution rows `I05` and `I10`
    to be visible.
  - `0x783f02..0x783f05`: per-source status bytes written when a source
    group has no more matching rows or when continuation gating is needed.
    Fixture `font sample non-internal source groups follow modes 0..2` writes
    `0x783f02 = 1`, `0x783f03 = 1`, and `0x783f04 = 1` for sources `0`, `1`,
    and `2`. The verified internal-font source group writes `0x783f05 = 14`
    in the class-zero pass through `0x1c5d6..0x1c5de`, then the class-one pass
    reads that byte through `0x1c41a..0x1c428` and later writes
    `0x783f05 = 29`.
  - `0x783f08`: recent-context count byte maintained by
    `0x1c540..0x1c5c6`.
  - local page-break word `-6(A6)`: receives the return flag from
    `0x1cf34`.
  - class-pass counter in the `0x1c28e..0x1c344` loop.
- Unknown:
  - exact continuation-page object bytes emitted by the full `0x1c204`
    printout loop have not yet been modeled from forced page-break cases
    across every source heading and both class passes. The internal-font
    class-zero
    source group is fixture-backed from request indexes `0..14`: `0x1b8ea`
    fast-probes class-zero row `I00`, `0x1b50e` scans later rows, `0x1c746`
    maps low-24 addresses back to candidate longwords, `0x1c710` finds
    request `14` is class one, and `0x1c3f8..0x1c400` branches directly to
    the source-status writer because class-zero `D5` is nonzero. `0x1cabe`
    emits 14 visible class-zero rows, and `0x1c540..0x1c5c6` leaves final
    recent contexts
    `0x4008004c,0x44080418,0x44080868,0x40080cb8,0x40089fb0,0x4408a37c,
    0x4408a7cc,0x4008ac1c,0x400942e4,0x440946b4,0x44094b08,0x40094f5c`.
    The class-one pass is fixture-backed with seed context `0x40099d18` from
    `0x1e9a0`: after visible row `I00`, `0x1c41a..0x1c428` reads the
    class-zero status byte `14`, resumes at request `14`, rejects requests
    `14` and `15` as class-zero rows, emits visible rows `I16..I28`, and
    leaves final recent contexts `0x40099d18,0x4409a0e4,0x4409a534,
    0x4009a984,0x400a3484,0x440a3850,0x440a3ca0,0x400a40f0,0x400ad4aa,
    0x440ad87a,0x440adcce,0x400ae122`.
    Source `0` fixture-backed mode `0` emits no rows in either pass and writes
    `0x783f02 = 1`; source `1` mode `1` emits only request-`0` rows `L00`
    from records `0x00004c` and `0x019d18` across the two class passes and
    writes `0x783f03 = 1`; source `2` mode `2` does the same for `R00` and
    writes `0x783f04 = 1`. Fixture
    `font sample source headings 0..2 compose page records` carries the source
    `0` heading-only output and source `1`/`2` single-row outputs through the
    page-record producer: source `0` bucket digest
    `89fb4143a293f80bb8c07bab86d5c94940ba73039f2bd9ba1e3de0c2c6c4fb4c`,
    source `1` class-zero/class-one digests
    `cc583ac71b083d3cf241a1a72ff6345e22d585a9eef1a0ba850427b6d43e2aba` /
    `51dade4f3a0af13cb533c9f62c5ea955a63f02046622e39a00b4ac8b072f63d6`,
    and source `2` class-zero/class-one digests
    `eaf10ca6b5b5716170b313ce542df82a6974c1ac22ee0e87308dead7be22c6a1` /
    `3d23d5c6c5320d406d1db34523d3ad01c819d4e938e3dee4fa0a5d20747ed152`.
    Forced continuation-page object bytes remain open for every source-heading
    and class-pass combination, but the normal full source/class placement is
    now composed as eight page-record segments.
  - record `+0x28/+0x2a` and `+0x2f..+0x31` are already correlated with
    emitted page objects for their ROM roles: `0x1519a` consumes
    `+0x28/+0x2a` as decoded-height inputs before `0x13bca`, and
    `0x1428c` consumes `+0x2f..+0x31` as same-class chooser tie-breakers
    after `0x14398` / `0x13c06`. What remains open here is only the
    HP/manual-facing baseline/cell terminology and comparison against a
    known printed sample.

### Writers

- `0x1c204` starts the sample printout and reports status `0xe3/0x51`
  if no font records exist.
- `0x1c28e..0x1c344` run class-zero and class-one passes, skipping empty
  classes and finalizing/ejecting between passes through FF handler
  `0xf0f0`.
- `0x1c2fe..0x1c332` iterates up to four source groups per pass,
  snapshots published pool pointer `0x780ea6` when the group index
  reaches `4`, clears a local page flag, and calls FF handler `0xf0f0`.
- `0x1c354..0x1c5e4` walks candidate rows for one source group: it emits
  the source heading through `0x1ca2c`, asks `0x1b50e` for row ordinals,
  class-filters candidates through `0x1c710`, starts continuation pages
  through `0x1c9f6` when needed, and advances the row index up to
  `0x63`.
- `0x1c5e8` installs the selected resource into current-font/page-root
  state, rebuilds the map through `0x14c64`, and refreshes page-root
  font slot state through `0xc428`.
- `0x1c916` initializes sample-page cursor and header state.
- `0x1ca2c` emits source/category headings, flushes text through
  `0x126e2` / `0x12714`, and writes row-height state.
- `0x1cabe` emits row prefix, metric columns, and sample text through
  `0xd04a`.
- `0x1cf34` emits sample byte runs, advances horizontally, installs the
  alternate context when needed, and writes the local page-break flag.
- `0x1d76c` writes a synthetic orientation command record and delegates
  to `0x10220`.

### Readers And Consumers

- `0x1b50e` supplies candidate rows from the active candidate windows.
  It first tries fast probe `0x1b8ea`; otherwise it scans the
  mode-specific first window, then the second window. Mode `3` uses the
  built-in-symbol windows, modes `1` and `2` use cartridge/external
  windows, and mode `0` uses downloaded-record windows.
- `0x1b750` / `0x1b7b2` classify candidate words before `0x1b50e`
  exposes them to the sample loop; the admissible ranges differ for
  built-in, cartridge/external, and downloaded records.
- `0x1c746`, `0x1c766`, `0x1c7a8`, and `0x1c710` normalize, extract
  flags, and classify candidate rows before row emission.
- `0x1b50e` duplicate handling is a semantic consumer of current selected
  slot `0x7828a0`, requested symbol word `0x7821a0`, and Roman-8
  substitution flag `0x7828ac`: non-selected Roman-8 candidates can count
  twice for non-special requested symbols, while the current selected
  slot is suppressed.
- `0x1d198` builds the font-name/style column and reads local lookup
  tables at `0x1c0a6` and `0x1c11a` for labels such as `UPC/EAN`,
  `OCR A`, `OCR B`, `LINE DRAW`, `COURIER`, and `LINE PRINTER`.
- `0x1d6ea` emits capped strings through `0xd04a`; `0x1d71e`
  sanitizes fixed-length name bytes before emission.
- `0x1d868` / `0x1d8ba` preflight the selected/alternate row gate against
  `0x782db6`; `0x1d964` consumes `0x1dcf2` to preflight current/alternate
  row placement before continuing row emission.
- `0xd04a`, `0x1393a`, `0xd824` / `0xd3b2`, `0x12f2e`, `0x1ed84`, and
  `0x1ef6a` are the downstream text/page/render consumers once the
  sample helper emits bytes.

### Output Effect

The path prints ROM-selected labels, metric columns, and sample byte runs
as ordinary text. The row order is not a linear ROM-record walk:
`0x1b50e` resolves each source-group row ordinal through fast probe,
two scan windows, class/range checks, and Roman-8 duplicate/substitution
rules before `0x1cabe` and `0x1cf34` emit the visible text. `0x1d12e`
proves ROM strings and sample bytes enter the same printable path as host
bytes. Direct payload rendering of the two sample byte runs through first
`COURIER` and first `LINE_PRINTER` produces stable row-hash pairs
documented in `generated/analysis/ic30_ic13_font_sample_page.md`; those
hashes are the current comparison targets for the later page-object
model. Fixture `font sample built-in row fields format through 0x1cabe`
now covers the row-field cluster before the sample bytes for concrete
resource records: first `COURIER` record `0x000418` / context
`0x44080418` emits prefix `I01`, name `COURIER`, pitch `10`, height
`12`, symbol `10U`, printable bytes `49 30 31 43 4f 55 52 49 45 52 31
30 31 32 31 30 55`, two fixed-space calls through `0xd0f0`, and twelve
explicit horizontal units through `0x1d152`; first `LINE_PRINTER` record
`0x0146b4` / context `0x440946b4` emits prefix `I07`, name
`LINE_PRINTER`, pitch `16.6`, height `8.5`, symbol `10U`, printable
bytes `49 30 37 4c 49 4e 45 5f 50 52 49 4e 54 45 52 31 36 2e 36 38
2e 35 31 30 55`, three fixed-space calls, and eight explicit horizontal
units. The fixture cites `0x1cb26..0x1cb66`, `0x1d198` / `0x1d5fa`,
`0x1cc6e`, and `0x1cd78`; it deliberately keeps `0xd0f0` fixed spaces
and `0x1d152` cursor advances separate from printable bytes because both
affect final pixel placement. Fixture `font sample Courier row fields
cross page-record placement` now carries the first `COURIER` row-field
sequence across `0x1393a`, `0xd824`, `0x12f2e`, `0x1ed84`, and
`0x1ef6a`: the seventeen printable row-field bytes queue into compact
bucket `0` as two objects with counts `[7, 10]`; the two `0xd0f0`
symbol-column fixed spaces advance the cursor but create no compact glyph
entries; the final cursor is `0x05be0000`; and the rendered bucket rows
hash to
`4756fe985af471915c3de75c4637c09e51c28a80af75989a1125f6d9cbf2347c`.
Fixture `font sample Courier row fields and run 1 share page-record state`
then appends sample run 1 bytes `41 42 43 44 45 66 67 68 69 6a 23 24 40
5b 5c 5d 5e 60 7b 7c 7d 7e 31 32 33` to that same carried page-record
state. It pins the sample-run event count `25`, final cursor
`0x08ac0000`, nonempty buckets `[-1, 0]`, bucket `-1` object count `[5]`
with row hash
`78d11b068621d9a47fcce073c9b5d1a591bdfc9368bf5d32f6e81186911d4428`,
and bucket `0` object counts `[7, 10, 10, 10]` with row hash
`975779b94eb6e9eefaaa0134e7ef5915d5471e16b6568315f612def3cb440949`.
Fixture `font sample Courier row fields carry run 1 through 0x1d050 to
run 2` now crosses the middle transition inside `0x1cf34`: `0xf06e`
resets `0x782c8a` from `0x08ac0000` to line anchor `0x00000000`,
`0x1d050` reads first `COURIER` record `+0x16 = 40` through `0x1c6a4`
and `+0x18 = 13` through `0x1c6da`, combines the prior `0x783f06 = 13`
with `0x1cfe4` to advance `744` subunits, and moves y from
`0x00200000` to `0x005e0000` without a continuation page. The following
`0x1d152(0x31)` starts sample run 2 at x `0x05be0000`; the carried run
queues bytes `a1 a2 b3 b4 b6 b8 b9 bb bd c1 c5 c8 c9 cd ce d0 d2 d4
d7 d8 db de e0 e3 e8` into buckets `[3, 4]`, extends the carried page
record bucket set to `[-1, 0, 3, 4]`, and ends at cursor
`0x08ac0000,0x005e0000`. Compact object hashes for the full carried row
are bucket `-1`
`9917ff7d8cf390817753aa4bd4e199622d7d91ec593529ff1a5a638d06c9cbe1`,
bucket `0`
`c7ee0c27ccc1fef0666e2eaca8330a3c2e2e84faff310d7c9f82e42a9898b388`,
`7e99a72f06b2b32c21bf0da80de005928b58ae8602c0bb5bcb4ad999430ca6bd`,
`8dc2c1c43fd8e67d554ee018595ad3715d1f7731f79cd42f3037e6d026733d32`,
`99a818922a85049e8edfabbc8d8ebe5317b1f676ab74cbee1717d64717b3219e`,
bucket `3`
`38ecdd4f968463692b9181e9f39b2b8f66850555ca6dfa1b2d8fd3043d80df87`,
`d5ebcb8ec98bac63f306729ef80239ccbfdd7d7e2e837bcc6ffa035fe314fdfd`,
and bucket `4`
`2e7a32816cfa8ffd670eb71e6d0443e26537f7d5e4d9f7e0d02dd111bbec8fca`.
Fixture `font sample carried run 2 buckets render through 0x1ed84 and
0x1ef6a` then renders the newly carried run-2 buckets with a wide
destination stride because the sample text starts around x `1470`.
Bucket `3` crosses `0x1ed84` / `0x1ef6a` with setup `dividend = 3`,
`remainder_783a22 = 3`, `band_rows_scaled_783a20 = 32`, and two compact
objects; its combined current-band row hash is
`823d26ff1ebdb3068224faa8dfc0679eef91cd959f1dd370d13f018eb21ce6a4`,
with object current hashes
`3164f17fedfe56328acceef9ac6a377ccca90e5ae3d398e34909b8715643ae3d`
and `81754b70e3932ba6465c1c85bbb1991d22efaaac9960b242824dd089da2079fd`.
Those two objects also prove fallback rows beyond the current band,
hashing to
`973d6e26612036125768dcc697900e150e57899007ff846da320c457913e6d51`
and `d989877c1640e33f8036c4882d504a01a8f884945759d4b886d7ce132c23356b`.
Bucket `4` crosses the same render path with setup `dividend = 4`,
`remainder_783a22 = 4`, `band_rows_scaled_783a20 = 16`, and one compact
object; its current-band row hash is
`5e71581663bd2a7c363a866b8bea232fb69f0524e2046da47fd54375cb800796`
and its fallback hash is
`06dc84fbb9421397716b0bfccb9b807942ba9a29671436503c91813626d87d5f`.
Fixture `font sample source heading carries into first Courier row` remains an
isolation checkpoint for the first named `COURIER` row, but the actual
internal source-group page order starts one row earlier. The real setup
context is not arbitrary: `0x1c2dc` calls `0x1e9a0`, and the expanded setup
disassembly at `0x1e9a8..0x1ea3e` saves `0x78289f` / `0x7821a0`, forces symbol
`0x0115`, calls `0x1ae7e`, copies the selected candidate longword through
`0x782ee6`, rebuilds maps via `0x14c64`, and installs the page-root context
slot through `0xc428`.

Fixture `font sample source heading carries default plus first two Courier
rows` composes the actual source-heading boundary and the first three emitted
internal-font rows. The caller at `0x1c386..0x1c38e` passes source group `D4`,
current context `A4`, row word `0`, and alternate context `0` into `0x1ca2c`.
`0x1ca86..0x1caa6` selects source table entry `0x1c170 + 3*4 = 0x1c180`,
emits `INTERNAL FONTS` through `0x1d12e`, and advances through `0x1cfb4` from
y `0x00200000` to `0x00520000`. The heading has fourteen printable bytes.
Request index `0` then takes the `0x1b8ea` fast-probe path and selects slot
`0x782354`, record `0x00004c`, context `0x4008004c`, and word `0x0115`.
Because that record has no explicit name prefix, `0x1d198` falls through table
`0x1c11a`: record byte `+0x18 == 0` prints `LINE PRINTER`. The visible row-0
field bytes are `49 30 30 4c 49 4e 45 20 50 52 49 4e 54 45 52 31 30 31 32
38 55` (`I00LINE PRINTER10128U`), with three `0xd0f0` fixed spaces in the
symbol column before `8U`.

The actual three-row fixture then carries row 1 and row 2 through the same
`0x1c470..0x1c488` / `0x1d050..0x1d0d8` no-continuation path. It assigns
page-record context slots `[0x4008004c, 0x44080418, 0x44080868]`, advances row
1 to y `0x00c90003`, advances row 2 to y `0x01450003`, and ends after row 2 at
cursor `0x08ac0000,0x01830003`. The carried bucket set is `[0, 2, 3, 4, 6, 7,
10, 11, 13, 14, 15, 18, 21, 22, 23]`. Selected bucket hashes pinned by the
fixture include bucket `0`
`51cf2deccad2c23bc20fea15974651c8a0accd40b98d04f08e7dae9b2b91ede7` and
`6bc8abff650c02ca198ee24c067f20e675a51df39e57c6c6de6deb920a68e3eb`, bucket
`3`
`cb5f8df2937e9030f6bfce652c5ac01b37cd0c1a2321f4e7c128d013b9b4b9a0`,
`a3d39e69341601268d819eb66ad2f652b65a92f6bb8911c0b6ca6ebc2c215535`,
`60ed5c45f6003bb57c9c01c60845233ea7d801bdf5c7da71f92eaca7949e0833`,
`2d29f5798597bb622e722202499732967392b2c04f6cc098311db3cfe930dbe5`, and
`ceaea30694a4ecc0f0397f0cd42d5454a763dedf0fe8a66b2e65c9cd61de042b`.
The named-row isolation fixture `font sample resolver carries first two
Courier rows` keeps the default row as current setup context and starts visible
emission at request indexes `1` and `2`. The sample loop call at
`0x1c398..0x1c3a0` invokes
`0x1b50e(source D4, requested row D5, out word -0xa)`. With mode `3`, the
resolver scans `0x7827ac` / `0x78279a` and then `0x7827a0` / `0x782792`
through the `0x1b568..0x1b5a4` window selection and `0x1b5a4..0x1b706`
Roman-8 handling; `0x1b8ea` fast-probe is not accepted for requested
indexes `1` or `2`. Both requests see the current Roman-8 slot
`0x782354` / record `0x00004c` / word `0x0115` and suppress it through
`0x1b8b6`. Request index `1` then selects slot `0x782358`, record
`0x000418`, context `0x44080418`, and word `0x0155`; request index `2`
counts the first named `COURIER` row without selecting it, then selects
slot `0x78235c`, record `0x000868`, context `0x44080868`, and word
`0x0175`.

The same fixture carries the first-row final state through the row-to-row
path at `0x1c470..0x1c488` and `0x1d050..0x1d0d8` before the second
`0x1cabe` call at `0x1c4f2..0x1c532`. `0xf06e` resets x from
`0x08ac0000` to line anchor `0x00000000`; `0x1d050` reads the selected
second-row extent as line advance `40` and row height `13`, reads the
current setup context extent as line advance `36` and row height `13`,
uses prior `0x783f06 = 13`, and takes the no-continuation branch because
`0x782db6 = 0x7fff`. `0x1cfe4` advances `744` subunits, moving y from
`0x00900000` to `0x00ce0000`. The second row then emits printable bytes
`49 30 32 43 4f 55 52 49 45 52 31 30 31 32 31 31 55`
(`I02COURIER101211U`), two `0xd0f0` fixed-space cursor events, sample
run 1, the `0x1cf34` run-2 transition, and sample run 2. Page-record
context slots are now `[0x44080418, 0x44080868]`; the final carried
bucket set is `[0, 2, 3, 6, 7, 8, 10, 11, 14, 15, 16, 24, 32, 40, 48,
56, 64]` and final cursor is `0x08ac0000,0x010c0000`. The newly added
second-row bucket hashes are bucket `10`
`eacd4a8a42aac5b5051ea6fa7ec4f110226f507b2d7553af4b603934797d2518`,
bucket `11`
`163c35cc4b32842d247d043fd52e13d3fbad0fd59226d7100b00565c1b6f84ea`,
`00cbd0627207e812bd605ba426ee57eb4fcad1ba01f9e871549142f27797d599`,
`cd56f7dd35740a68540e9a86ba961bb0c28591cad5bfee1d6e22fe10ca98debd`,
`a442f1745e42e19b43df41944423b533173a89d81c59d81ce08c7b89e2eeb531`,
bucket `14`
`99e41bc2de372db066e5309811f5056d2b3086d4f1d0c637f723a129a6d8bc1b`,
`c034baf0c58e41bebb209ffcee321436fb8d2a06ce9d7b7ab219aa2ff53a21a7`,
and bucket `15`
`1e4f535fe8a84513fe54a616ba4a24d1825564a6f62ad7eb3ba14129d3aa963f`.
Fixture `font sample run 1 prefix crosses page-record render entry` first
consumed bytes `41 42 43 44 45 66 67 68` (`ABCDEfgh`)
through the sample-page current context `0x44080418`, forced HMI
`0x001e`, the compact page-record bucket, `0x1ed84`, and `0x1ef6a`; it
pins row hash
`a954464fa31f122e8283a19f581c48dca3667ad637edb8b1f02d8d417e104bf2`.
Fixture `font sample run 1 full row spans compact buckets` now consumes
sample run 1 byte stream `41 42 43 44 45 66 67 68 69 6a 23 24 40 5b 5c
5d 5e 60 7b 7c 7d 7e 31 32 33`
(``ABCDEfghij#$@[\\]^`{|}~123``) through the same context and HMI. It
pins nonempty compact buckets `-1` and `0`, bucket object counts `1` and
`2`, compact dispatch target `0x1effe`, bucket `-1` glyphs `[104, 105,
35, 93, 123]` with row hash
`b6a0061f7de34c0fa1a0586263f3f167c84d95219e05437e74a286356409af37`,
and bucket `0` glyphs `[90, 91, 92, 95, 122, 124, 125, 48, 49, 50, 64,
65, 66, 67, 68, 101, 102, 103, 34, 63]` with row hash
`d7dfb89c8cff5e309b95aac43cd64e0f74f17db1dd9118253544343f17b4c1ce`.
Fixture `font sample run 2 full row spans compact buckets` consumes sample
run 2 table `0x1c1e9` bytes `a1 a2 b3 b4 b6 b8 b9 bb bd c1 c5 c8 c9 cd
ce d0 d2 d4 d7 d8 db de e0 e3 e8` through the same context and HMI. It
pins nonempty compact buckets `-1` and `0`, bucket object counts `2` and
`1`, compact dispatch target `0x1effe`, bucket `-1` glyphs `[211, 214,
215, 218, 221, 178, 179, 181, 184, 188, 192, 196, 199, 205, 207]` with
row hash
`c77bca7364adbda480c5a31fa4be469175c031bd5f14fc4a54a2e6fb09174be5`,
and bucket `0` glyphs `[160, 161, 183, 186, 200, 204, 209, 223, 226,
231]` with row hash
`b10556bfb02fbb6a2ffec2a82add396619bae3ace0ebab657113f4d3648c41b5`.
Fixture `font sample full printout source placement follows firmware order`
composes the `0x1c28e` class pass and `0x1c2fe` source iteration into
source/class segments `(0,0)..(0,3),(1,0)..(1,3)`. It preserves canonical
source-status writes `0x783f02..0x783f05`, derived page-record bucket counts
`[3, 13, 13, 142, 3, 12, 12, 122]`, context-slot counts
`[1, 1, 1, 12, 1, 1, 1, 12]`, row counts `[0, 1, 1, 14, 0, 1, 1, 14]`, total
row count `32`, and aggregate segment digest
`f4105538bd1506731f04810ed2f50cce23815751c4f979ed6f60efab4cde08c7`.
This checkpoint proves the producer, row-order, duplicate-suppression,
concrete built-in row-field formatting, carried sample-run placement, modeled
preflight branches, all-source page-record placement skeleton, and source/class
row reuse of the two ROM sample byte tables. Fixture `font sample full printout
rows reuse ROM sample byte runs` shows all 32 emitted rows queue the 25-byte
run-1 table at `0x1c1cf` and the 25-byte run-2 table at `0x1c1e9`, with
aggregate correlation digest
`4f664dc44f9ad98cbe25d4bdead651a2902bec1f90367c650bb2d1352d6f3e8a`.
Fixture `font sample full printout segments render through 0x1ed84 and
0x1ef6a` then renders the eight segment page records through the bridge and
band renderer, preserving render-bucket counts `[1, 6, 6, 65, 1, 5, 5, 50]`,
rendered bucket-row totals `[33, 210, 210, 2012, 33, 146, 146, 1257]`, and
surface digest `5e5e735b4fb2a2a4dff4794099a02eaf23fa2dd3e469df8d053db88a321ea6f2`.
It does not yet prove physical baseline/cell agreement against a known
printed/self-test sample.

### Confidence

High for helper roles, class-pass loop structure, candidate-row
traversal, current-font/page-root setup, printable byte emission,
continuation checks, local label tables, concrete default Roman-8 row,
first `COURIER`, and first `LINE_PRINTER` row-field formatting, first
`COURIER` row-field page-record placement, first `COURIER` carried row-field
plus sample-run-1 placement, actual internal source-heading through row 0,
row 1, and row 2 page-record composition, first two named `COURIER` row
resolutions and row-to-row composition, first
`COURIER` `0x1d050` run-1-to-run-2 transition, carried run-2
page-record object placement, carried run-2 bucket rendering through
`0x1ed84` / `0x1ef6a`, direct sample byte-run row hashes, full source/class
placement skeleton, and per-row reuse of sample byte tables `0x1c1cf` /
`0x1c1e9`, plus all-source rendered surface digests through `0x1ed84` /
`0x1ef6a`, because they are anchored by generated disassembly analysis and
`tools/render_fixture_harness.py`. Medium for baseline/cell interpretation
because physical/self-test comparison is still open.

### Fixtures And Reports

- `generated/analysis/ic30_ic13_font_sample_page.md`
- `generated/analysis/ic30_ic13_renderer_fixture_harness.md`
- `generated/analysis/ic32_ic15_builtin_font_samples.md`
- `generated/analysis/ic32_ic15_builtin_glyph_payloads.md`
- `generated/analysis/ic32_ic15_font_records.md`

### Disassembly Evidence

- `generated/disasm/ic30_ic13_font_resource_scan_01a2e4.lst`
- `generated/disasm/ic30_ic13_font_resource_object_lookup_01b4c0.lst`
- `generated/disasm/ic30_ic13_font_page_setup_alt_01e8e6.lst`
- `generated/disasm/ic30_ic13_font_sample_page_01c170.lst`
- `generated/disasm/ic30_ic13_font_sample_row_helpers_01d198.lst`
- `generated/disasm/ic30_ic13_font_candidate_activate_01569c.lst`
- `generated/disasm/ic30_ic13_font_candidate_filters_01519a.lst`
- `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`
- `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`
- `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`

### Unresolved Middle Edges

- `0x1c334..0x1c5e4`: row traversal is decoded, including source-group
  headings, `0x1b50e` two-window candidate resolution, class filtering,
  continuation-page entry, row-index advance/status writes, and the post-row
  recent-context scan. The verified internal-font mode-3 row sequence is
  documented in [resource-rom.md](resource-rom.md) for both class passes:
  class-zero emits `I00..I13`, class-one emits `I00` plus `I16..I28`, and
  the full-loop status chain is class-zero `0x783f05 = 14`, class-one resume
  through `0x1c41a..0x1c428`, and final class-one `0x783f05 = 29`. The
  non-internal source-index fixture covers source `0` mode `0` with no rows
  and sources `1`/`2` modes `1`/`2` with only request-`0` `L00`/`R00` rows,
  writing source status bytes `0x783f02..0x783f04 = 1`; the source-heading
  page-record fixture now carries those source `0..2` outputs to bucket lists
  and aggregate object digests. The
  `0x1c1cf` sample run 1 byte stream is now consumed both as a standalone
  page-object/render fixture and after first-`COURIER` row fields in the same
  carried page-record state. The
  `0x1c1e9` sample run 2 byte stream is now carried after run 1 through the
  no-continuation `0x1d050` branch for first `COURIER`.
  Full source/class placement is now composed as eight page-record segments
  with the modeled preflight branches integrated into the all-source row loop.
  Fixture `font sample full printout rows reuse ROM sample byte runs` proves
  each non-empty segment row reuses the ROM run tables at `0x1c1cf` and
  `0x1c1e9`, producing correlation digest
  `4f664dc44f9ad98cbe25d4bdead651a2902bec1f90367c650bb2d1352d6f3e8a`.
  Fixture `font sample full printout segments render through 0x1ed84 and
  0x1ef6a` renders those segment records through the output bridge and pins
  surface digest
  `5e5e735b4fb2a2a4dff4794099a02eaf23fa2dd3e469df8d053db88a321ea6f2`.
  Remaining gap is physical baseline/cell comparison against a known
  printed/self-test sample.
- `0x1c5e8..0x1ed84`: selected resource setup, row formatting,
  printable-byte emission, and downstream text/page/render consumers are
  identified. First `COURIER` and first `LINE_PRINTER` row-field
  formatting now crosses the `0x1cabe` boundary as printable bytes plus
  fixed-space/cursor-advance events, and the first `COURIER` row-field
  sequence crosses the page-record/render boundary as compact bucket `0`
  with object counts `[7, 10]`; appending sample run 1 in that same state
  extends the record to buckets `[-1, 0]`, and carrying sample run 2
  through `0x1d050` extends it to buckets `[-1, 0, 3, 4]`. The actual
  first-three-row composition checkpoint starts with default context
  `0x4008004c`, adds the first two named `COURIER` contexts, and extends the
  page record to buckets `[0, 2, 3, 4, 6, 7, 10, 11, 13, 14, 15, 18, 21,
  22, 23]`. The carried run-2 checkpoint pins page-record objects, compact
  coords, current-band render hashes, and fallback hashes for buckets `3`
  and `4`; the source-heading composition checkpoint pins the `INTERNAL
  FONTS` label, fallback row-0 name `LINE PRINTER`, and shifted y origins
  for the first three actual rows.
  The standalone run-2 render fixture remains useful as an isolation control
  with context `0x44080418`, HMI `0x001e`, compact buckets `-1` and `0`, and
  render-entry row hashes above. The complete font printout is now modeled as
  eight source/class page-record segments, and
  `font sample full printout segments render through 0x1ed84 and 0x1ef6a`
  pins the aggregate rendered-surface digest
  `5e5e735b4fb2a2a4dff4794099a02eaf23fa2dd3e469df8d053db88a321ea6f2`.
  The remaining sample-printout boundary is comparison against a known
  printed/self-test page.
- `record +0x28/+0x2a`: decoded-height input consumed by `0x1519a` through
  `0x13bca`; physical baseline/cell correlation remains open.
- `record +0x2f..+0x31`: same-class chooser tie-breakers consumed by
  `0x1428c` after `0x14398` / `0x13c06`; manual-facing names remain open.

## Built-In Font Selection To Visible Text

Status: composed as parsed command-family to visible-output checkpoints for
primary and secondary inline mixed streams, primary/secondary symbol-fallback,
primary/secondary live current-font-RAM handoff, and
parsed-selection-to-current-font-RAM handoff streams. The low-level
font-selection ledger remains in
[font-context-metrics.md](font-context-metrics.md); this section records the
renderer-facing semantic contract for the selected state.

Concept: `ESC (s0p10h12v0s0b3T` writes primary font request fields, refreshes
the active primary built-in context through `0x13eb8`, rebuilds the primary
glyph map through `0x14c64`, and supplies selected context `0xc008004c` to the
same printable/page-record/render path used by ordinary text. Appending `!!`
therefore queues two Courier glyph-0 compact entries and renders pixels from
the selected built-in resource record, not from the default Line Printer
context. `ESC )s0p16h8v0s0b0T SO !!` follows the secondary version of the
same contract: the secondary selection writes context `0xc00ae122`, SO selects
slot 1 through `0xc6b8`, and the two printable bytes render from that
class-one Line Printer context.
`ESC (1234U ESC (s0p10h12v0s0b3T!!` proves the primary fallback form:
the symbol-set request writes word `0x9a55`, no class-zero candidate matches,
`0x156de` takes fallback table word `0x0115`, and the later primary selection
plus printable output still render through context `0xc008004c`.
`ESC )1234U ESC )s0p16h8v0s0b0T SO !!` proves the fallback form of that
secondary contract: the symbol-set request writes word `0x9a55`, no class-one
candidate matches, `0x156de` takes fallback table word `0x000e`, and the later
secondary selection plus SO output still render through context `0xc00ae122`.
Fixture `live parser symbol-set streams select non-Roman built-ins` proves the
primary non-Roman form before visible text: `ESC (0N`, `ESC (10U`, and
`ESC (11U` pass through the ROM parser and selected-font refresh, select
distinct class-zero built-in records, and rebuild primary map `0x782f32`
through the non-Roman selected-symbol path rather than Roman-8 patching.
Fixture `non-Roman symbol streams select visible built-ins` carries those
symbols through visible output for both slots. The primary cases append
`ESC (s0p10h12v0s0b3T!!` and render from selected contexts `0xc0080cb8`,
`0xc4080418`, and `0xc4080868`; the secondary cases append
`ESC )s0p16h8v0s0b0T SO !!`, cross SO handler `0xc6b8`, and render from
selected contexts `0xc00ae122`, `0xc40ad87a`, and `0xc40adcce`.
The parser-exposed final-`@` variants are now a documented symbol-state
contract, not an unresolved parser curiosity. Fixture
`symbol-set parser trace covers X and @ special cases` proves that final `X`
and final `@` use the same terminal handler `0x120be` after setup
`0x1201e` / `0x12008`: `X` preserves the previous requested word while calling
font-id helper `0x17708`, `@0`/`@1` read the default-symbol table,
`@2` copies the current primary requested word to the target slot, and `@3`
uses the current default-font word. Fixture
`font-ID built-in selection feeds visible page-record rows` carries the final
`X` built-in success path through visible output: host-fetched `ESC (7X!!`
routes through parser handlers `0x11eb6`, `0x1201e`, and `0x120be`,
`0x17708` selects candidate pointer `0x782364` / context `0xc0089fb0`,
`0x14c64` rebuilds primary map `0x782f32`, and the printable `!!` tail queues
object `00 00 00 00 00 00 00 02 00 89 00 00 87 02` with rendered-row digest
`73cbb28bfab786807b9a3186eb3946efae550cde2e5448f0549f88ebf8c8a631`.
Fixture `font-ID inline/downloaded selection feeds visible page-record rows`
carries the bit-30-clear final-`X` success path through visible output:
host-fetched `ESC )4660X SO !` routes through parser handlers `0x11eb6`,
`0x12008`, and `0x120be`, `0x17708` selects candidate pointer `0x782900` /
context `0x00000100`, `0x14c64` rebuilds secondary map `0x783032`, SO handler
`0xc6b8` leaves secondary selected, and printable `!` queues object
`00 00 00 00 00 01 00 01 01 66 01 00 00 00` with rendered-row digest
`e0c6cbbf133aaaf522868ef7f28856f06b0d54b4dd9368a090fe7c85e7b1d563`.
Fixture `0x17708 font-ID non-selected exits preserve prior selection` covers
the helper exits that deliberately stop before map dispatch: record scan miss,
candidate-slot miss, class mismatch, and full page-root context table. These
paths restore `0x782f2e = 0x2222`, leave `0x7828a8 = 0` until a candidate slot
is actually accepted, and never call `0x14c64`. Fixture
`font-ID non-selected exits keep prior visible rows` carries host-fetched
`ESC (7X!!` through the same parser record and those four terminal helper
states, then renders the printable `!!` tail from the previously selected
primary context `0xc008004c`, object
`00 00 00 00 00 00 00 02 00 6a 00 00 68 02`, and row digest
`8b36cfd64d818c0982b172982156f8be9687388c9679cd83538c9d1098d9bb2c`.
Fixture
`real default-table caller stream uses ROM-backed words` then drives real
scanned built-in default words through `ESC (0@ ESC )0@ ESC )1@ ESC )2@
ESC (3@`: the stream requests `[0x0005, 0x000e, 0x0005, 0x0005, 0x000e]`,
leaves final requested words `[0x000e, 0x0005]`, and preserves the same active
words after five common-refresh calls.
Fixture `real final-@ default-table streams select visible built-ins` carries
that real-backed caller state through visible output. Appending
`ESC (s0p10h12v0s0b3T!!` selects primary context `0xc0080cb8`, queues object
`00 00 00 00 00 00 00 02 00 6a 00 00 68 02`, and renders the primary
non-Roman row digest
`8b36cfd64d818c0982b172982156f8be9687388c9679cd83538c9d1098d9bb2c`.
Appending `ESC )s0p16h8v0s0b0T SO !!` selects secondary context
`0xc00ad4aa`, crosses SO handler `0xc6b8`, queues object
`00 00 00 00 00 01 00 02 00 c9 00 00 cb 01`, and renders the secondary row
digest `b8ee0f8dd3e6ed70afa219bc00605d75249ae047a67fb67189693057d7936e6c`.
Fixture `live primary current-font RAM install feeds SI page-record rows`
proves the selected primary RAM record handoff: with
`0x782ee6 = 0xc008004c` and an existing page root whose secondary slot is
live, SI calls `0xc428(0)`, `0xc4fc` installs `0xc008004c` into page-root slot
`0`, and `0xd04a` / `0x1393a` consume that installed slot for the following
two printable bytes.
Fixture `parsed primary selection current-font RAM feeds SI visible rows`
composes those contracts for `ESC (s0p10h12v0s0b3T SI !!`: host-fetched
selection bytes produce `0x782ee6 = 0xc008004c` and map `0x782f32`; the `SI
!!` tail installs page-root slot `0` and renders the same primary rows.
Fixture `live secondary current-font RAM install feeds SO page-record rows`
then proves the selected secondary RAM record handoff: with
`0x782ef6 = 0xc00ae122` and an existing page root whose primary slot is live,
SO calls `0xc428(1)`, `0xc4fc` installs `0xc00ae122` into page-root slot `1`,
and `0xd04a` / `0x1393a` consume that installed slot for the following two
printable bytes.
Fixture `parsed secondary selection current-font RAM feeds SO visible rows`
does the same for `ESC )s0p16h8v0s0b0T SO !!`, producing
`0x782ef6 = 0xc00ae122`, map `0x783032`, page-root slot `1`, and the same
secondary rows.
Fixtures `inline primary font selection stream renders visible rows` and
`inline secondary font selection stream renders SO visible rows` remove the
split between parsed selection and printable queueing for the primary and
secondary visible streams. The primary fixture runs `ESC (s0p10h12v0s0b3T!!`
through one mixed-stream state: final handlers `0xc930`, `0xc89c`, `0xc6ec`,
`0xc780`, `0xc840`, and `0x1205a` write `0x782ee6 = 0xc008004c`, derive HMI
`30`, and the following `0xd04a` events read source context `0xc008004c`. The
secondary fixture runs `ESC )s0p16h8v0s0b0T SO !!` through the same shape:
selection writes `0x782ef6 = 0xc00ae122`, SO handler `0xc6b8` selects slot
`1`, HMI becomes `18`, and printable bytes read source context `0xc00ae122`.
Fixture `0x13eb8 transient and cache-hit exits avoid dispatch` documents the
two selected-font refresh exits that intentionally do not rebuild a visible
map. The transient-context path follows `0x148f8`, `0x1569c`, `0x156de`,
`0x153c6`, `0x1519a`, `0x147b2`, `0x14758`, and `0x14398`, records selected
context `0xc008004c` for the page-root refresh byte `0x78298f`, restores saved
active word `0x9999`, and stops before `0x144d2` / `0x14c64`. The cache-hit
path returns immediately after `0x148f8`, preserving active words
`[0x1111, 0x2222]`. Fixture
`0x13eb8 no-dispatch exits keep prior visible rows` carries both exits into
visible output. The transient path stages `0xc008004c` in `0x782992` but the
following `!!` tail still renders from prior context `0xc0089fb0`, object
`00 00 00 00 00 00 00 02 00 89 00 00 87 02`, and row digest
`73cbb28bfab786807b9a3186eb3946efae550cde2e5448f0549f88ebf8c8a631`. The
cache-hit path crosses SO and renders from prior secondary context
`0xc40ad87a`, object
`00 00 00 00 00 01 00 02 20 c9 00 20 cb 01`, and row digest
`b8ee0f8dd3e6ed70afa219bc00605d75249ae047a67fb67189693057d7936e6c`.

### Field Groups

- Canonical selection request fields:
  - primary request bytes under `0x782eec..0x782ef2`: typeface `3`, style `0`,
    stroke `0`, spacing `0`, pitch `0x03e8`, and height `0x04b0`.
  - primary symbol request word `0x9a55` from `ESC (1234U`; fallback active
    word `0x0115` before the primary `ESC (s...T` selection.
  - secondary symbol request word `0x9a55` from `ESC )1234U`; fallback active
    word `0x000e` before the secondary `ESC )s...T` selection.
  - primary non-Roman symbol request words `0x000e`, `0x0155`, and `0x0175`
    from `ESC (0N`, `ESC (10U`, and `ESC (11U`.
  - secondary non-Roman symbol request words `0x000e`, `0x0155`, and
    `0x0175` from `ESC )0N`, `ESC )10U`, and `ESC )11U`.
  - final-`@` parser records:
    `ESC (0@`, `ESC )0@`, `ESC )1@`, `ESC )2@`, and `ESC (3@` all route
    through terminal handler `0x120be`; their six-byte records are
    `80 40 00 00 00 00`, `80 40 00 00 00 01`,
    `80 40 00 01 00 01`, `80 40 00 02 00 01`, and
    `80 40 00 03 00 00`.
  - real-backed final-`@` requested words:
    `@0` reads table slots `0x0005` / `0x000e`, `@1` reads primary table word
    `0x0005`, `@2` copies the primary requested word `0x0005` to secondary,
    and `@3` reads current default-font word `0x000e`.
  - real-backed final-`@` visible streams:
    the primary stream carries final active words `[0x000e, 0x0005]` into
    `ESC (s0p10h12v0s0b3T!!`; the secondary stream carries the same final
    active words into `ESC )s0p16h8v0s0b0T SO !!`.
  - final-`X` font-ID request:
    `ESC (7X` routes through `0x120be`, preserves the previous requested
    symbol word, writes transient current font ID `7` through `0x782f2e`, and
    calls `0x17708`.
  - secondary inline/downloaded final-`X` font-ID request:
    `ESC )4660X` routes through `0x120be`, stores transient current font ID
    `0x1234` through `0x782f2e`, and calls `0x17708` for slot `1`.
  - final-`X` non-selected helper exits:
    `scan-miss`, `candidate-slot-miss`, `class-mismatch`, and `context-full`
    all restore saved font ID `0x2222` after the helper returns. In the
    visible preserved-state stream, the following `!!` bytes consume the
    previously selected primary context `0xc008004c`.
  - `0x13eb8` no-dispatch exit inputs:
    transient refresh uses selected slot `0`, requested primary `0x0115`,
    saved active primary word `0x9999`, and page-root transient flag
    `0x78298f = 1`; cache-hit uses selected slot `1` with active words
    `[0x1111, 0x2222]`.
  - dirty flags `0x782f2c` and `0x782f2d`, set by handlers `0xc930`,
    `0xc89c`, `0xc6ec`, `0xc780`, `0xc840`, and `0x1205a`.
  Evidence: fixture `parsed font-selection stream writes primary font-state
  fields`, fixture
  `primary symbol miss falls back before visible page-record rows`, and fixture
  `secondary symbol miss falls back before visible SO page-record rows`, plus
  fixtures `symbol-set parser trace covers X and @ special cases` and
  `real default-table caller stream uses ROM-backed words`; fixture
  `0x17708 font-ID non-selected exits preserve prior selection` pins the
  non-selected final-`X` helper exits, and fixture
  `font-ID non-selected exits keep prior visible rows` pins their following
  printable output.
- Canonical selected context:
  - `0x782ee6 +0x00`: selected longword `0xc008004c`.
  - `0x782ee6 +0x04`: bit-30-derived byte `1`.
  - `0x782ee6 +0x05`: bit-26-derived byte `0`.
  - `0x782ef6 +0x00`: secondary selected longword `0xc00ae122`.
  - `0x782ef6 +0x04`: bit-30-derived byte `1`.
  - `0x782ef6 +0x05`: bit-26-derived byte `0`.
  - built-in resource base `0x00004c`, first/last host range
    `0x21..0xfe`, glyph entry `0x001088` for host byte `0x21`.
  - secondary built-in resource base `0x02e122`, first/last host range
    `0x21..0xff`, glyph entry `0x02e4f6` for host byte `0x21`.
  - final-`X` inline/downloaded selected context:
    synthetic context `0x00000100`, selected candidate pointer `0x782900`,
    selected word `0x0115` from inline word `+0x14`, class byte `+0x16 = 0`,
    and selected flag byte `+0x0e = 1`.
  - non-Roman primary selected longwords `0xc0080cb8`, `0xc4080418`, and
    `0xc4080868` for records `0x000cb8`, `0x000418`, and `0x000868`.
  - non-Roman secondary selected longwords `0xc00ae122`, `0xc40ad87a`, and
    `0xc40adcce` for records `0x02e122`, `0x02d87a`, and `0x02dcce`.
  - non-Roman primary map ranges: `0N` uses `0x21..0xff`, while `10U` and
    `11U` use `0x01..0xff`.
  Evidence: fixtures `0x13eb8 refresh carries parsed primary font selection to
  dispatch`, `0x13eb8 refresh carries parsed secondary font selection to
  dispatch`, `parsed primary built-in font selection feeds visible
  page-record rows`, and
  `parsed secondary built-in font selection feeds visible SO page-record rows`;
  fallback fixture `primary symbol miss falls back before visible page-record
  rows` reaches the same primary context after active word `0x0115` is
  selected;
  fallback fixture
  `secondary symbol miss falls back before visible SO page-record rows` reaches
  the same secondary context after active word `0x000e` is selected.
- Canonical installed page-root font slots:
  - seeded primary current-font RAM: `0x782ee6 = 0xc008004c`.
  - seeded secondary current-font RAM: `0x782ef6 = 0xc00ae122`.
  - existing page root: `0x78297a`.
  - SI install result: `0xc428(0)` / `0xc4fc` selects page-root slot `0`,
    writes `0xc008004c`, and sets `0x78297e = 0`.
  - SO install result: `0xc428(1)` / `0xc4fc` selects page-root slot `1`,
    writes `0xc00ae122`, and sets `0x78297e = 1`.
  Evidence: fixtures
  `live primary current-font RAM install feeds SI page-record rows` and
  `live secondary current-font RAM install feeds SO page-record rows`.
- Canonical visible page-record fields:
  - primary compact text object prefix:
    `00 00 00 00 00 00 00 02 00 6a 00 00 68 02`.
  - secondary compact text object prefix:
    `00 00 00 00 00 01 00 02 00 c9 00 00 cb 01`.
  - render-record context slots: primary slot `0xc008004c`, secondary slot
    `0xc00ae122`.
  - primary compact coords: `0x6a00` and `0x6802`.
  - secondary compact coords after SO: `0xc900` and `0xcb01`.
  - `0x13eb8` transient preserved-output prefix:
    `00 00 00 00 00 00 00 02 00 89 00 00 87 02`, with prior primary context
    `0xc0089fb0` and row digest
    `73cbb28bfab786807b9a3186eb3946efae550cde2e5448f0549f88ebf8c8a631`.
  - `0x13eb8` cache-hit preserved-output prefix:
    `00 00 00 00 00 01 00 02 20 c9 00 20 cb 01`, with prior secondary context
    `0xc40ad87a` and row digest
    `b8ee0f8dd3e6ed70afa219bc00605d75249ae047a67fb67189693057d7936e6c`.
  - final-`X` non-selected preserved-output compact prefix:
    `00 00 00 00 00 00 00 02 00 6a 00 00 68 02`, with render-record context
    slot `0xc008004c` and row digest
    `8b36cfd64d818c0982b172982156f8be9687388c9679cd83538c9d1098d9bb2c`.
  - non-Roman primary compact prefixes:
    `0N` uses `00 00 00 00 00 00 00 02 00 6a 00 00 68 02`, while `10U` and
    `11U` use `00 00 00 00 00 00 00 02 20 6a 00 20 68 02`.
  - non-Roman secondary compact prefixes:
    `0N` uses `00 00 00 00 00 01 00 02 00 c9 00 00 cb 01`, while `10U` and
    `11U` use `00 00 00 00 00 01 00 02 20 c9 00 20 cb 01`.
  Evidence: fixtures `parsed primary built-in font selection feeds visible
  page-record rows`,
  `inline primary font selection stream renders visible rows`,
  `parsed secondary built-in font selection feeds visible SO page-record rows`,
  and `inline secondary font selection stream renders SO visible rows`;
  fallback fixture `primary symbol miss falls back before visible page-record
  rows` reaches the same primary visible page-record fields after symbol
  fallback;
  fallback fixture
  `secondary symbol miss falls back before visible SO page-record rows` reaches
  the same secondary visible page-record fields after symbol fallback; live
  handoff fixtures reach the same primary and secondary fields after reading
  context slots `0` and `1` from the page-root slot table; fixture
  `font-ID non-selected exits keep prior visible rows` reaches the same
  primary visible fields after failed final-`X` helper exits; fixture
  `0x13eb8 no-dispatch exits keep prior visible rows` pins the distinct
  transient and cache-hit preserved-output prefixes listed above.
- Derived/cache state:
  - `0x7828a8`: selected candidate slot `0x782354`.
  - secondary selected candidate slot `0x782350`.
  - final-`X` selected built-in candidate slot: `0x782364` for resource
    payload `0x089fb0` / selected longword `0xc0089fb0`.
  - final-`X` selected inline/downloaded candidate slot:
    `0x782900` for payload `0x000100` / selected longword `0x00000100`.
    With an existing page root, `0xc4fc` reuses context slot `1`.
  - transient `0x13eb8` selected context cache:
    `0x782992` receives selected longword `0xc008004c` after candidate slot
    `0x782354` / record `0x00004c` wins, but the normal current-font context
    record `0x782ee6` is not written by this exit; following printable output
    can therefore remain on prior context `0xc0089fb0`.
  - cache-hit `0x13eb8` derived state:
    no candidate-window activation or map rebuild occurs; the only confirmed
    call is `0x148f8`, and the active words remain `[0x1111, 0x2222]`;
    following SO output can therefore remain on prior secondary context
    `0xc40ad87a`.
  - final-`X` non-selected candidates:
    scan miss and candidate-slot miss leave selected pointer `0x7828a8 = 0`;
    class mismatch observes pointer `0x782364` and record class `0xff` but
    rejects wanted class `0x00`; context-full observes the same pointer but
    stops when `0xc4fc` returns `0x11`. None of these cases replaces the
    prior printable context `0xc008004c`.
  - primary fallback active-word source: fallback table word `0x0115` after
    the requested pass misses word `0x9a55`.
  - parser default-symbol table `0x782f1c/20/24/28`: built by `0x1ac0a` and
    consumed by final-`@` subdispatches `@0` and `@1`. In the real-backed
    caller fixture, the table words are `0x0005`, `0x000e`, `0x0155`, and
    `0x000e`.
  - primary fallback survivor slot pointers: `0x782354`, `0x782364`, and
    `0x782374`.
  - secondary fallback active-word source: fallback table word `0x000e` after
    the requested pass misses word `0x9a55`.
  - candidate fallback table `0x782f0c/10/14/18`: built by `0x1af36` and
    consumed by `0x156de` only after requested symbol candidates miss. It is
    not the final-`@` parser table.
  - secondary fallback survivor slot pointers: `0x782330`, `0x782340`, and
    `0x782350`.
  - `0x782f32`: rebuilt primary map, range `0x21..0xfe`, patch kind
    `unchanged`.
  - `0x782f32` for non-Roman primary selection: rebuilt map with patch kind
    `selected-symbol-not-roman8`; survivor record starts are
    `0x000cb8/0x00ac1c/0x014f5c` for `0N`,
    `0x000418/0x00a37c/0x0146b4` for `10U`, and
    `0x000868/0x00a7cc/0x014b08` for `11U`.
  - `0x783032`: rebuilt secondary map, range `0x21..0xff`, patch kind
    `selected-symbol-not-roman8`.
  - `0x783032` for non-Roman secondary selection: rebuilt map with patch kind
    `selected-symbol-not-roman8`; contexts are `0xc00ae122` for `0N`,
    `0xc40ad87a` for `10U`, and `0xc40adcce` for `11U`.
  - `0x783134`: primary mapped range register, `0x21..0xfe`.
  - HMI/default advance: built-in byte `+0x21 = 0`, long
    `+0x24 = 0x00780000`, converted by `0x10550` to packed advance `30`.
  - secondary HMI/default advance: built-in byte `+0x21 = 0`, long
    `+0x24 = 0x00480000`, converted by `0x10550` to packed advance `18`.
- Parser scratch:
  - fetched stream bytes are split at byte 20: selection bytes
    `ESC (s0p10h12v0s0b3T`, printable bytes `!!`.
  - the primary fallback fetched stream is split into symbol bytes
    `ESC (1234U`, selection bytes `ESC (s0p10h12v0s0b3T`, and printable
    bytes `!!`.
  - the secondary fetched stream is split into selection bytes
    `ESC )s0p16h8v0s0b0T` and printable/control bytes `SO !!`.
  - the fallback fetched stream is split into symbol bytes `ESC )1234U`,
    selection bytes `ESC )s0p16h8v0s0b0T`, and printable/control bytes
    `SO !!`.
  - non-Roman parser streams `ESC (0N`, `ESC (10U`, and `ESC (11U` all route
    through handlers `0x11eb6`, `0x1201e`, and `0x120be`; their terminal
    `0x120be` dispatch target is `0x1c0a4`.
  - non-Roman visible streams pair those primary commands with
    `ESC (s0p10h12v0s0b3T!!`, and pair secondary `ESC )0N`, `ESC )10U`, and
    `ESC )11U` with `ESC )s0p16h8v0s0b0T SO !!`.
  - final-`@` real-backed stream
    `ESC (0@ ESC )0@ ESC )1@ ESC )2@ ESC (3@` routes through
    `0x11774 -> 0x1201e/0x12008 -> 0x120be` for each command and then through
    final-`@` subdispatch targets
    `0x1bed4`, `0x1bed4`, `0x1bf0a`, `0x1bf36`, and `0x1bf74`.
  - final-`X` isolation stream `ESC (7X` routes through the same terminal
    handler and calls font-id helper `0x17708` without replacing the previous
    requested symbol word.
  - final-`X` visible stream `ESC (7X!!` ties that parser/helper boundary to
    selected context `0xc0089fb0` and two following `0xd04a` printable events.
  - final-`X` inline/downloaded visible stream `ESC )4660X SO !` ties the
    secondary parser/helper boundary to selected context `0x00000100`, SO
    handler `0xc6b8`, and one following `0xd04a` printable event.
  - direct final-`X` error-state fixture cases use the same `0x17708` helper
    boundary and now append a following printable tail: no matching `0x172c0`
    record, no matching `0x1b4c0` candidate slot, class mismatch at `+0x20`,
    and page-root context-full after `0xc4fc`, then two `0xd04a` printable
    events from prior context `0xc008004c`.
  - printable parser events are two `0xd04a` entries for the primary fixture,
    and `0xc6b8, 0xd04a, 0xd04a` for the secondary SO and fallback fixtures.
  - the live primary handoff stream is `SI !!` with current-font/page-root
    state preseeded from the `0x13eb8` results.
  - the live secondary handoff stream is `SO !!` with current-font/page-root
    state preseeded from the `0x13eb8` results.
  - the composed primary stream is `ESC (s0p10h12v0s0b3T SI !!`, split into
    selection bytes and a `SI !!` handoff tail.
  - the composed secondary stream is `ESC )s0p16h8v0s0b0T SO !!`, split into
    selection bytes and a `SO !!` handoff tail.
  - the inline primary stream keeps `ESC (s0p10h12v0s0b3T!!` in one
    mixed-stream state; the inline secondary stream keeps
    `ESC )s0p16h8v0s0b0T SO !!` in one mixed-stream state.
- Firmware bookkeeping:
  - `0x144d2` writes current-font context record `0x782ee6`.
  - `0x14c64` rebuilds map `0x782f32` and snapshots selected font state.
  - `0x156de` uses fallback table word `0x0115` before `0x14c64` rebuilds
    primary map `0x782f32` in the primary fallback stream.
  - `0x156de` uses fallback table word `0x000e` before `0x14c64` rebuilds
    secondary map `0x783032` in the fallback stream.
  - `0x14c64` rebuilds map `0x782f32` for the primary `0N`, `10U`, and `11U`
    selections without entering the `0x14f16` Roman-8 patch-table path.
  - `0x14c64` rebuilds map `0x783032` for the secondary `0N`, `10U`, and
    `11U` selections before SO makes slot `1` active for printable bytes.
  - `0x17708` non-selected bookkeeping:
    `scan-miss` calls only `0x172c0`; `candidate-slot-miss` calls
    `0x172c0` and `0x1b4c0`; `class-mismatch` calls the same scan/slot
    helpers and stops before reader `0x15890`; `context-full` adds `0xc4fc`
    and stops when selected page slot is `0x11`. The preserved-visible fixture
    confirms none of these statuses calls `0x14c64` before the printable tail.
  - `0x17708` inline/downloaded selected bookkeeping:
    the secondary final-`X` visible fixture calls `0x172c0`, `0x1b4c0`,
    `0xc4fc`, `0x158be`, `0x1b2fe`, and `0x14c64`; `0x158be` reads the active
    symbol from inline word `+0x14`, and `0x14c64` rebuilds map `0x783032`.
  - `0x13eb8` no-dispatch bookkeeping:
    transient refresh with `0x78298f = 1` runs the normal candidate filters
    through chooser `0x14398`, stores only selected context `0x782992`, and
    does not call `0x144d2` or `0x14c64`; cache-hit returns after `0x148f8`
    without activating candidate windows. Fixture
    `0x13eb8 no-dispatch exits keep prior visible rows` confirms both paths
    leave the following printable/SO tail on the prior render contexts.
  - `0x1ac0a` writes the parser default-symbol table
    `0x782f1c/20/24/28`; `0x1af36` writes the separate candidate fallback
    table `0x782f0c/10/14/18`.
  - final-`@` subdispatch target `0x1bed4` reads table slot `0`, target
    `0x1bf0a` reads the primary table word, target `0x1bf36` copies primary
    to secondary, and target `0x1bf74` uses the current default-font word from
    the `0x1b250` / `0x1b50e` / `0x1ab84` / `0x1b060` default-font path.
  - `0xc428` reads the selected longword from `0x782ee6` / `0x782ef6` and
    passes that longword to `0xc4fc`; `0xc4fc` stores the longword in the
    selected page-root slot.
  - page-root allocation count is `1` when the parsed-selection visible
    fixtures start without a root; it is `0` in the live secondary handoff
    fixture because the root already exists before SO.
- Unknown:
  - lower-level CPU-register fidelity inside the modeled `0x13eb8` refresh
    remains indirect; the primary and secondary parser-to-printable state edge
    is now covered by inline mixed-stream fixtures.
  - broader non-Roman command combinations remain open only if they expose
    different state boundaries; the primary and secondary visible-output paths
    for `0N`, `10U`, and `11U` are fixture-backed.

### Writers

- `0xc930`, `0xc89c`, `0xc6ec`, `0xc780`, `0xc840`, and `0x1205a` write the
  primary request fields and dirty flags.
- `0x120be` writes the requested symbol word `0x9a55` for `ESC (1234U` and
  `ESC )1234U`, and writes `0x000e`, `0x0155`, and `0x0175` for primary
  `ESC (0N`, `ESC (10U`, and `ESC (11U`, plus the same words for secondary
  `ESC )0N`, `ESC )10U`, and `ESC )11U`.
- `0x120be` / `0x1be22` also handle final `@`: `@0`/`@1` read
  `0x782f1c/20/24/28`, `@2` copies the primary requested symbol word, and
  `@3` writes the current default-font symbol word. The real-backed fixture
  drives `ESC (0@ ESC )0@ ESC )1@ ESC )2@ ESC (3@` to final active words
  primary `0x000e` and secondary `0x0005`.
- `0x120be` / `0x1be22` handle final `X` by restoring the previous requested
  symbol word, setting `0x78287b`, and calling `0x17708(slot, parameter)`.
  The visible fixture pins `ESC (7X` to helper calls `0x172c0`, `0x1b4c0`,
  `0xc4fc`, `0x15890`, `0x1b2fe`, and `0x14c64`, with active primary word
  `0x0115`.
- The final-`@` visible fixture then writes primary current-font context
  `0xc0080cb8` through `0x144d2` and secondary current-font context
  `0xc00ad4aa` through `0x144d2`; the secondary stream also crosses SO
  `0xc6b8` before printable consumption.
- `0x13eb8` filters active candidates through `0x1569c`, `0x156de`,
  `0x153c6`, `0x1519a`, `0x147b2`, `0x14758`, and `0x14398`.
- `0x13eb8` also has two no-dispatch consumers documented by fixture
  `0x13eb8 transient and cache-hit exits avoid dispatch`: the transient path
  consumes the same candidate-filter chain but leaves visible output to the
  already-selected map, while the cache-hit path consumes only the `0x148f8`
  cache probe and returns. Fixture
  `0x13eb8 no-dispatch exits keep prior visible rows` proves the following
  printable/SO consumers remain on those prior maps and contexts.
- `0x156de` writes fallback active word `0x0115` for the primary symbol miss
  and `0x000e` for the secondary symbol miss before pruning the active
  candidate window.
- `0x144d2` writes selected context state at `0x782ee6`.
- `0x144d2` writes secondary selected context state at `0x782ef6`.
- `0x14c64` rebuilds maps `0x782f32` and `0x783032`.
- `0xc428` / `0xc4fc` install selected longwords `0xc008004c` and
  `0xc00ae122` into page-root/render context slots; the live primary handoff
  fixture pins `0xc428(0)` selecting page-root slot `0`, and the live
  secondary handoff fixture pins `0xc428(1)` selecting page-root slot `1`.
- SI handler `0xc68a` selects primary slot 0 before the primary printable
  bytes are consumed, and in the live handoff fixture it performs the modeled
  `0xc428(0)` install before changing `0x782f06` to `0`.
- SO handler `0xc6b8` selects secondary slot 1 before the secondary printable
  bytes are consumed, and in the live handoff fixture it performs the modeled
  `0xc428(1)` install before changing `0x782f06` to `1`.
- Printable `0xd04a` / `0x1393a` write the source object, and `0x12f2e` /
  `0x1387c` write the compact page-record object.

### Readers And Consumers

- `0x1393a` consumes selected context `0xc008004c` and map `0x782f32` to map
  host byte `0x21` to glyph `0x00`; in the live primary handoff fixture it
  reaches that selected context by reading page-root context slot `0`, which
  `0xc428(0)` filled from `0x782ee6`.
- `0x156de` consumes candidate symbol words and fallback table word `0x0115`
  to convert the missed requested word `0x9a55` into the active primary symbol
  word.
- `0x156de` consumes candidate symbol words and fallback table word `0x000e`
  to convert the missed requested word `0x9a55` into the active secondary
  symbol word.
- After SO, `0x1393a` consumes selected context `0xc00ae122` and map
  `0x783032` to map host byte `0x21` to glyph `0x00`; the fallback fixture
  reaches this same consumer state after `0x156de` selects word `0x000e`.
- In the non-Roman visible fixture, `0x1393a` consumes primary contexts
  `0xc0080cb8`, `0xc4080418`, and `0xc4080868` through map `0x782f32`, and
  consumes secondary contexts `0xc00ae122`, `0xc40ad87a`, and `0xc40adcce`
  through map `0x783032` after SO.
- In the live handoff fixture, `0x1393a` reaches that same selected context by
  reading page-root context slot `1`, which `0xc428(1)` filled from
  `0x782ef6`.
- `0xd824` consumes built-in glyph offsets from entry `0x001088`, producing
  positioned sources `(10,-10)` and `(40,-10)`.
- `0xd824` also consumes secondary built-in glyph entry `0x02e4f6`, producing
  positioned sources `(9,12)` and `(27,12)` in the secondary fixture.
- `0x1edc6` copies context slots `0xc008004c` and `0xc00ae122` into the render
  record.
- `0x1f354` / compact renderer helper `0x1fe76` consume that selected context
  and glyph `0` to draw two Courier glyph rows.
- Compact renderer helper `0x207ac` consumes secondary context `0xc00ae122`
  and glyph `0` to draw two secondary Line Printer glyph rows.
- The same renderer helpers consume the non-Roman visible fixture outputs:
  `0x1fe76` renders the primary Courier rows for `0N`/`10U`/`11U`, and
  `0x207ac` renders the secondary Line Printer rows for `0N`/`10U`/`11U`.
- Final-`X` font-ID selection affects the selected context before later
  printable bytes. Fixture
  `font-ID built-in selection feeds visible page-record rows` proves
  `0x1393a` consumes context `0xc0089fb0`, maps host byte `0x21` to glyph
  `0x00`, and emits glyph entry `0x00afec`.
- Final-`X` inline/downloaded selection affects the secondary unflagged source
  path before later printable bytes. Fixture
  `font-ID inline/downloaded selection feeds visible page-record rows` proves
  `0x1393a` consumes context `0x00000100`, maps host byte `0x21` to glyph
  `0x01`, reads inline glyph record `02 03 04 00 00 00 00 80`, and emits
  glyph entry `0x00000148`.
- Final-`X` non-selected exits do not produce a new consumer context. Fixture
  `0x17708 font-ID non-selected exits preserve prior selection` proves the
  helper stops before `0x14c64`, and fixture
  `font-ID non-selected exits keep prior visible rows` proves the following
  `0xd04a` / `0x1393a` events consume prior context `0xc008004c`, map `!` to
  glyph `0x00`, and emit glyph entry `0x001088`.
- Final-`@` parser variants affect requested/active symbol words before later
  font selection. Fixture
  `real final-@ default-table streams select visible built-ins` proves those
  exact requested words feed primary `0x1393a` from context `0xc0080cb8` and
  secondary `0x1393a` from context `0xc00ad4aa`.

### Output Effect

The rendered output is not the default Line Printer `!`. It is two Courier
glyph-0 shapes at x `10` and x `40`, with the first nonblank row:

```text
.............###...........................###...
```

The final printable state has cursor x `60`, cursor y `21`, HMI `30`, and one
page-record root allocation.

The primary symbol-miss fixture has the same output effect after fallback:
requested word `0x9a55` is replaced by active word `0x0115`, then the final
object prefix, context slot, rendered rows, cursor x `60`, HMI `30`, and
page-root allocation count `1` match the primary visible fixture.

The secondary fixture renders two class-one Line Printer glyph-0 shapes after
SO selects slot 1. The first visible row is:

```text
.........################..################...###
```

The final secondary printable state has cursor x `66`, cursor y `21`, HMI
`18`, selector `1`, one `0xc6b8` install call, and one page-record root
allocation.

The secondary symbol-miss fixture has the same output effect after fallback:
requested word `0x9a55` is replaced by active word `0x000e`, then the final
object prefix, context slots, rendered rows, cursor x `66`, HMI `18`,
selector `1`, install count `1`, and page-root allocation count `1` match the
secondary SO fixture.

The live secondary current-font RAM handoff fixture has the same secondary
rows and compact object prefix, but uses an existing page root. Its SO event
records `0xc428(1)` / `0xc4fc` installing `0xc00ae122` from `0x782ef6` into
page-root context slot `1`; both printable bytes then report source context
`0xc00ae122` and source slot `1`. Final page-root allocation count is `0`
because the fixture starts after root creation.

The live primary current-font RAM handoff fixture has the same primary Courier
rows and compact object prefix as the parsed primary visible fixture, but uses
an existing page root. Its SI event records `0xc428(0)` / `0xc4fc` installing
`0xc008004c` from `0x782ee6` into page-root context slot `0`; both printable
bytes then report source context `0xc008004c` and source slot `0`. Final
page-root allocation count is `0` because the fixture starts after root
creation.

The parsed-selection-to-RAM composed fixtures do not duplicate the full row
tables; they assert that the RAM handoff rows match the already-pinned parsed
visible fixtures while preserving the combined host streams, selection
handlers, context updates, page-root install events, source contexts, object
prefixes, and page-root slots.
The inline fixtures assert the same final rows while preserving one evolving
mixed-stream state from selection handlers to printable source capture. The
primary inline stream writes `0x782ee6`, derives HMI `30`, queues object
`00 00 00 00 00 00 00 02 00 6a 00 00 68 02`, and renders the same Courier
rows. The secondary inline stream writes `0x782ef6`, processes SO `0xc6b8`,
derives HMI `18`, queues object
`00 00 00 00 00 01 00 02 00 c9 00 00 cb 01`, and renders the same secondary
Line Printer rows.

The non-Roman visible fixture extends that output contract across six streams.
Primary `0N`, `10U`, and `11U` all render two Courier glyphs from contexts
`0xc0080cb8`, `0xc4080418`, and `0xc4080868`, with rendered-row digest
`8b36cfd64d818c0982b172982156f8be9687388c9679cd83538c9d1098d9bb2c`.
Secondary `0N`, `10U`, and `11U` all render two Line Printer glyphs from
contexts `0xc00ae122`, `0xc40ad87a`, and `0xc40adcce` after SO, with
rendered-row digest
`b8ee0f8dd3e6ed70afa219bc00605d75249ae047a67fb67189693057d7936e6c`.

The real final-`@` visible fixture collapses onto those same visible row
families after proving the table/copy/default-font state transition. The
primary tail selects context `0xc0080cb8` and the same primary digest as
`ESC (0N`; the secondary tail selects context `0xc00ad4aa`, applies the
Roman Extension map path for active word `0x0005`, crosses SO `0xc6b8`, and
matches the secondary digest above.

The final-`X` visible fixture renders a distinct built-in record selected by
font ID. Host-fetched `ESC (7X!!` selects context `0xc0089fb0`, HMI `30`, glyph
entry `0x00afec`, object prefix
`00 00 00 00 00 00 00 02 00 89 00 00 87 02`, and rendered-row digest
`73cbb28bfab786807b9a3186eb3946efae550cde2e5448f0549f88ebf8c8a631`.

The final-`X` non-selected visible fixture renders the previous primary font,
not the requested font ID. After scan miss, candidate-slot miss,
class-mismatch, or context-full, no new map dispatch occurs; the following
`!!` tail consumes preserved context `0xc008004c`, queues object
`00 00 00 00 00 00 00 02 00 6a 00 00 68 02`, and renders row digest
`8b36cfd64d818c0982b172982156f8be9687388c9679cd83538c9d1098d9bb2c`.

The final-`X` inline/downloaded visible fixture renders a synthetic secondary
inline/downloaded record selected by font ID. Host-fetched `ESC )4660X SO !`
selects context `0x00000100`, maps `!` to glyph `0x01`, positions the
unflagged source at `(22,22)`, queues compact object prefix
`00 00 00 00 00 01 00 01 01 66 01 00 00 00`, leaves final cursor x `40`, and
renders row digest
`e0c6cbbf133aaaf522868ef7f28856f06b0d54b4dd9368a090fe7c85e7b1d563`.

The `0x13eb8` no-dispatch visible fixture renders the prior font state. The
transient path prepares `0x782992 = 0xc008004c` for a page-root refresh without
touching `0x782ee6` or rebuilding `0x782f32`; the following `!!` still
consumes prior context `0xc0089fb0`, queues object
`00 00 00 00 00 00 00 02 00 89 00 00 87 02`, and renders row digest
`73cbb28bfab786807b9a3186eb3946efae550cde2e5448f0549f88ebf8c8a631`. The
cache-hit path leaves the existing active words/maps in force; after SO the
following `!!` consumes prior secondary context `0xc40ad87a`, queues object
`00 00 00 00 00 01 00 02 20 c9 00 20 cb 01`, and renders row digest
`b8ee0f8dd3e6ed70afa219bc00605d75249ae047a67fb67189693057d7936e6c`.

### Confidence

High for parser handler routing, fallback table decision, selected built-in
context, secondary current-font RAM to page-root slot install, map rebuild
metadata, HMI, compact object bytes, render context slot, and final rows
because they are all fixture-pinned against ROM-derived helpers. High for the
primary and secondary parser-to-printable state edge because the inline
fixtures preserve one mixed-stream state from selection handlers through
following printable source capture and row comparison. Medium for lower-level
CPU-register fidelity inside the modeled `0x13eb8` refresh.
High for primary and secondary visible-output handling of `0N`, `10U`, and
`11U` because fixture `non-Roman symbol streams select visible built-ins`
preserves symbol-set parsing, font-selection refresh, SO for secondary,
compact object creation, bridge context slots, and rendered row digests.
High for final-`X` built-in visible output because fixture
`font-ID built-in selection feeds visible page-record rows` composes
host-fetched bytes, ROM parser handlers, `0x17708` helper calls, selected
context, printable source capture, object prefix, bridge context slots, and
rendered row digest.
High for final-`X` inline/downloaded visible output because fixture
`font-ID inline/downloaded selection feeds visible page-record rows` composes
host-fetched bytes, ROM parser handlers, the bit-30-clear `0x17708` helper
path, selected inline context, SO, unflagged printable source capture, object
prefix, bridge context slots, and rendered row digest.
High for the `0x13eb8` transient and cache-hit no-dispatch exits because
fixture `0x13eb8 transient and cache-hit exits avoid dispatch` pins call
lists, selected context cache, saved active word restoration, absence of
`0x144d2` / `0x14c64`, and cache-hit early return. High for their visible
output because fixture `0x13eb8 no-dispatch exits keep prior visible rows`
appends printable/SO tails and pins prior contexts, object prefixes, bridge
context slots, and rendered-row digests.
High for direct `0x17708` non-selected exits because fixture
`0x17708 font-ID non-selected exits preserve prior selection` pins all four
terminal statuses, call lists, restored font ID, selected pointer state, class
comparison, and `0xc4fc` full-table result. High for carrying those exits
through later visible output because fixture
`font-ID non-selected exits keep prior visible rows` appends the parsed
printable tail and pins prior context `0xc008004c`, object prefix, bridge
context slots, and row digest.
High for final-`@` parser/default-table behavior because the ROM parser
records, terminal handler, subdispatch targets, real built-in default words,
requested words, active words, and common-refresh count are fixture-pinned.
High for final-`@` visible output because fixture
`real final-@ default-table streams select visible built-ins` composes those
exact default-table requests with primary and secondary font-selection tails,
printable sources, object prefixes, bridge context slots, and rendered row
digests.

### Fixtures

- `parsed font-selection stream writes primary font-state fields`
- `0x13eb8 refresh carries parsed primary font selection to dispatch`
- `0x13eb8 refresh carries parsed secondary font selection to dispatch`
- `parsed primary built-in font selection feeds visible page-record rows`
- `inline primary font selection stream renders visible rows`
- `parsed secondary built-in font selection feeds visible SO page-record rows`
- `inline secondary font selection stream renders SO visible rows`
- `primary symbol miss falls back before visible page-record rows`
- `parsed primary selection current-font RAM feeds SI visible rows`
- `parsed secondary selection current-font RAM feeds SO visible rows`
- `live primary current-font RAM install feeds SI page-record rows`
- `live secondary current-font RAM install feeds SO page-record rows`
- `secondary symbol miss falls back before visible SO page-record rows`
- `live parser symbol-set streams select non-Roman built-ins`
- `non-Roman symbol streams select visible built-ins`
- `symbol-set parser trace covers X and @ special cases`
- `font-ID built-in selection feeds visible page-record rows`
- `font-ID inline/downloaded selection feeds visible page-record rows`
- `0x17708 font-ID non-selected exits preserve prior selection`
- `font-ID non-selected exits keep prior visible rows`
- `0x13eb8 transient and cache-hit exits avoid dispatch`
- `0x13eb8 no-dispatch exits keep prior visible rows`
- `real default-table caller stream uses ROM-backed words`
- `real final-@ default-table streams select visible built-ins`

### Disassembly Evidence

- `generated/disasm/ic30_ic13_main_parser_loop_011774.lst`: parser dispatch.
- `generated/disasm/ic30_ic13_font_candidate_activate_01569c.lst`: candidate
  activation.
- `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`: printable
  consumer path.
- `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`: compact object
  producer.
- `generated/analysis/ic30_ic13_renderer_fixture_harness.md`: fixture report.

### Unresolved Middle Edges

- `0x1205a..0x13eb8`: parsed request to refresh is behaviorally composed and
  the resulting current-font context now stays in one mixed-stream state for
  the primary and secondary visible paths. The `0x13eb8` transient and
  cache-hit no-dispatch exits are now carried through preserved visible tails:
  the transient path ends at prior primary context `0xc0089fb0`, and the
  cache-hit path ends at prior secondary context `0xc40ad87a`. Remaining risk
  is lower-level CPU-register fidelity inside the modeled refresh, plus broader
  font-selection variants that expose new state boundaries.
- `0x782ee6 +0x00..+0x0f` into `0xc68a..0xc428..0xc4fc..0xd04a..0x1393a`
  and `0x782ef6 +0x00..+0x0f` into
  `0xc6b8..0xc428..0xc4fc..0xd04a..0x1393a`: primary and secondary selected
  current-context RAM are now covered for existing page roots, and composed
  parser-selection-to-visible fixtures cover
  `ESC (s0p10h12v0s0b3T SI !!` and `ESC )s0p16h8v0s0b0T SO !!`. The inline
  fixtures now cover the primary and secondary no-root visible streams in one
  mixed-stream state.
- Other primary/secondary font-selection combinations and fallback/error
  branches still need the same visible-output treatment; the exact covered
  fallback boundaries are `ESC (1234U ESC (s0p10h12v0s0b3T!!` through
  `0x120be..0x156de..0x14c64..0xd04a`, and
  `ESC )1234U ESC )s0p16h8v0s0b0T SO !!` through
  `0x120be..0x156de..0x14c64..0xc6b8..0xd04a`. The covered font-ID boundary
  includes built-in `ESC (7X!!` through
  `0x120be..0x17708..0x14c64..0xd04a`, and inline/downloaded
  `ESC )4660X SO !` through
  `0x120be..0x17708..0x14c64..0xc6b8..0xd04a`; the covered direct font-ID
  non-selected boundaries now run from `0x120be..0x17708` statuses
  `scan-miss`, `candidate-slot-miss`, `class-mismatch`, and `context-full`
  into preserved-context `0xd04a` output. The `context-full` helper edge still
  ends at `0x17708..0xc4fc = 0x11` before the printable tail consumes prior
  context `0xc008004c`.
- Final-`@` parser variants are documented through requested/active
  symbol-state, real default-table words, and primary/secondary visible-output
  streams. No unresolved middle edge remains for `@0..@3` inside the current
  built-in font-selection model.

## Text Span Flush And Fixed-Width Spans

Status: composed as the shared pending-span cluster behind printable
span updates, direct-control flushes, and render-facing span objects.
This checkpoint covers the two watermark writers `0xd4ac` and `0xd8fc`,
the unflagged printable low-water path `0xd140` -> `0xd3b2` ->
`0xd4ac`, the flagged printable low-water path `0xd550` -> `0xd824` ->
`0xd8fc`, the parsed-CR flush path `0xf02c` -> `0xf06e` -> `0xf34a`,
the re-arm helper `0x126e2`, flush helper `0x12714`, portrait producer
`0x13520` / `0x135f0`, landscape producer `0x136d2`, and consumers
`0x1f812` and `0x1f756`.

Concept: text placement maintains a pending horizontal span in
`0x783184..0x78318a`. `0x126e2` opens a new pending span at the current
horizontal cursor. `0xd4ac` and `0xd8fc` extend its x/y watermarks from
font/context metrics. When text or a control movement crosses left of
`0x783186`, or when shared helper `0xf34a` sees a pending span,
`0x12714` packages the state as an 8-byte source. Portrait orientation
queues a segment-list mask span through `0x13520` / `0x135f0`; landscape
queues a fixed-width span through `0x136d2`.

### Field Groups

- Canonical pending-span state:
  - `0x783184`: enabled byte. `0x126e2` sets it when clear, and
    `0x12714` clears it before attempting output.
  - `0x783186`: low-x watermark / flush threshold. `0x126e2` seeds it
    from `0x782c8a`; `0xd4ac` and `0xd8fc` compare current x against it.
  - `0x783188`: high-x watermark. `0x126e2` seeds it from `0x782c8a`;
    `0xd4ac` and `0xd8fc` raise it after placement.
  - `0x78318a`: high-y watermark. `0x126e2` clears it; `0xd4ac` and
    `0xd8fc` raise it from context-record y bounds and offsets.
  Evidence: disassembly `0x126e2..0x12712`, printable-text disassembly
  `0xd4ac..0xd548` and `0xd8fc..0xd992`, and fixtures
  `0x12714 portrait text span flush queues segment-list span` and
  `0x12714 landscape text span flush queues fixed-width span`, plus
  `flagged printable d8fc low-watermark flush renders span` and
  `unflagged printable d4ac low-watermark flush renders span`.
- Canonical flush source fields:
  - local source `+0`: orientation byte copied from `0x782da3`.
  - local source `+1`: mode byte, initially zero and rewritten by
    `0x137a2` to `3` for portrait or `6` for landscape.
  - local source `+2`: portrait x is `0x783186`; landscape x is
    `0x78318a`.
  - local source `+4`: portrait y is `0x78318a`; landscape y is
    `0x782db2 - 0x783186 - ((0x783188 - 0x783186) - 1)`.
  - local source `+6`: span extent, `0x783188 - 0x783186`.
  Evidence: `generated/disasm/ic30_ic13_text_span_flush_012714.lst`
  `0x1274a..0x12808`, plus both `0x12714` fixtures.
- Canonical geometry inputs:
  - `0x782c8a`: current horizontal cursor copied by `0x126e2`.
  - `0x782da3`: orientation branch consumed by `0x12714`.
  - `0x782db2`: landscape orientation extent consumed by `0x12768`.
  - `0x782db6`: page extent gate; `0x12790..0x127a0` skips output when
    `0x78318a + 2` is beyond it.
  - `0x782dc0`: vertical offset added by `0x137a2` before key packing.
  Evidence: `0x126f6..0x1270a`, `0x12752..0x127a0`, and
  `generated/disasm/ic30_ic13_display_list_helpers_013386.lst`
  `0x137a2..0x1381a`.
- Canonical flagged context inputs:
  - context `+0x16`: lower y bound consumed at `0xd910..0xd920`.
  - context `+0x18`: y-height/page-extent contribution consumed at
    `0xd92a..0xd93e`.
  - context `+0x1a`: alternate y offset consumed at `0xd940..0xd954`
    when `0x783185` is set.
  - `0x783185`: alternate-offset selector tested at `0xd940`.
  Evidence: disassembly `0xd908..0xd992` and fixture
  `flagged printable d8fc low-watermark flush renders span`, where
  `cursor_y=21`, `+0x16=0`, `+0x18=10`, `+0x1a=18`, and
  `0x783185=1` produce `high_y=3`. The copied-field endpoints are
  fixture-backed by `legal descriptor metric value matrix drives d4ac and
  d8fc consumers` and
  `legal descriptor metric boundary values drive d4ac and d8fc consumers`:
  `+0x16 = 0x0015` is accepted at cursor y `21`, derived/cache `+0x18 =
  0x002b` reaches exact page extent `64`, and offset bytes `0xfe`, `0xff`,
  and `0x7f` become copied words `0xfffe`, `0xffff`, and `0x007f`.
- Canonical unflagged context inputs:
  - context `+0x2b`: alternate y offset added at `0xd4f8..0xd506`
    when `0x783185` is set and the byte is nonzero.
  - context `+0x2c`: lower y bound consumed at `0xd4c0..0xd4d0`.
  - context `+0x2d`: y-height/page-extent contribution consumed at
    `0xd4da..0xd4ee`.
  Evidence: disassembly `0xd4b8..0xd548` and fixture
  `unflagged printable d4ac low-watermark flush renders span`, where
  `cursor_y=21`, `+0x2b=7`, `+0x2c=0`, `+0x2d=10`, and
  `0x783185=1` produce `high_y=28`. The descriptor boundary fixture proves
  rounded input `0x0013` copies `+0x2c = 0x0014`, while inputs `0x1500`,
  `0x1508`, and `0x15ff` all copy `+0x2c = 0x0060` before `d4ac` exits
  `beyond-page-extent`. Fixture
  `legal descriptor metric low-nibble rounding drives d4ac and d8fc consumers`
  proves rounded inputs `0x0001`, `0x0003`, `0x0004`, `0x0005`, and `0x000f`
  copy to canonical `+0x2c` words `0x0000`, `0x0004`, `0x0004`, `0x0004`,
  and `0x0010`, matching the ROM-derived `min((value + 2) >> 2,
  word(+0x14)) << 2` transform for these low-nibble samples. Fixture
  `legal descriptor metric byte-boundary rounding drives d4ac and d8fc
  consumers` extends that transform across the byte boundary: rounded inputs
  `0x00fd`, `0x00fe`, `0x0101`, and `0x0102` copy to canonical `+0x2c`
  words `0x00fc`, `0x0100`, `0x0100`, and `0x0104`, while the same `0x0102`
  input caps at `0x0100` when `+0x14 = 0x0040`. The copied `0x00fc` case
  makes `d4ac` exit `beyond-page-extent`, but the `0x0100` byte-boundary copy
  changes the consumed bytes to lower `1` and height `0`, so `d4ac` emits the
  standard span digest
  `67554ea70d7cfd9b11c0777e3cf65d51600a44301a4f93bd4d9b0c0fbc23c00e`.
- Derived/cache producer state:
  - `0x782a7a` / `0x782a7b`: selector bytes for `0x1387c`; current
    fixtures pin `0x4000` for segment-list span objects.
  - `0x782a7c`: bucket index from y-like coordinate shifted by four.
    `0x1354a` increments it for the second portrait segment-list entry
    when a span crosses a 16-row bucket boundary.
  - `0x782a7d`: bucket byte written into fixed-list objects by
    `0x136d2`.
  - `0x782a7e`: packed key used by both `0x135f0` segment-list entries
    and `0x136d2` fixed-list entries. `0x1354a` clears its row bits
    with `andi.w #0x0fff` before emitting the second split entry.
  Evidence: `0x137a2..0x1381a`, fixture
  `0x137a2/0x136d2-modeled fixed-rule list object and bridge
  normalization`, both `0x12714` fixtures, and
  `0x1354a portrait text span split queues adjacent buckets`.
- Derived/cache render interpretation:
  - `0x1f812` word-aligns portrait segment-list x to a visible
    16-pixel boundary while preserving the source key/extent object.
  Evidence: fixture `flagged printable d8fc low-watermark flush renders
  span` queues source x `100`, key `0x3406`, and extent `20`; the
  rendered visible span occupies pixels `96..115` on rows `3..5`.
  Fixture `unflagged printable d4ac low-watermark flush renders span`
  queues source x `100`, key `0xc406`, and extent `20`; the rendered
  visible span occupies pixels `96..115` on rows `12..14`.
- Firmware bookkeeping:
  - current page root `0x78297a` is ensured by `0x10084` before
    `0x12714` queues output.
  - allocation failure at `0x13520` causes `0x127ae..0x127be` to set
    bit 0 in current page root byte `+0x15`, call `0xff1e`, ensure a
    page root again, rebuild the same local source at `0x127ca..0x12808`,
    and retry at `0x127a2`.
  - page-root flags word `+0x14` bit 0 is retry/finalization
    bookkeeping. Fixture
    `0x12714 allocation failure publishes page and retries span` sets
    it to `1` before publication and observes fresh-root `+0x14 = 0`.
  Evidence: `0x12788..0x12808`,
  `generated/analysis/ic30_ic13_page_root_finalization.md`, and fixture
  `0x12714 allocation failure publishes page and retries span`.
- Parser scratch:
  - none owned by this cluster. The scratch object at `A5` in
    `0x12714` is a local producer source, not parser record storage.
- Unknown:
  - selected-context metric ownership is no longer the middle edge for this
    cluster: `notes/font-context-metrics.md` documents the legal producer
    forms, copied-field endpoints, and consumer branches. Remaining gaps are
    additional legal descriptor combinations outside the pinned type-0/type-1/
    type-2, lower/equality/upper, clamped, midpoint, offset-boundary, and
    rounded-transform cases, plus external/manual naming for
    consumed-but-not-staged validation fields.

### Writers

- `0x126e2` sets `0x783184`, copies `0x782c8a.w` into `0x783188` and
  `0x783186`, and clears `0x78318a` when no pending span is active.
- `0xd4ac` and `0xd8fc` write `0x78318a` and `0x783188`, compare
  current x with `0x783186`, and call `0x12714` then `0x126e2` when the
  current x is below the low watermark.
- `0xd140` calls `0xd3b2` during unflagged printable placement and
  then calls `0xd4ac` after writing the updated cursor to `0x782c8a`.
  Evidence: `0xd23c..0xd25e` and fixture
  `unflagged printable d4ac low-watermark flush renders span`.
- `0xd550` calls `0xd824` during flagged printable placement and then,
  when the flagged path is active, calls `0xd8fc` after writing the
  updated cursor to `0x782c8a`. Evidence: `0xd66e..0xd690` and fixture
  `flagged printable d8fc low-watermark flush renders span`.
- `0xf34a` clears `0x782a58`; if `0x783184` is set, it calls `0x12714`
  then `0x126e2`.
- `0xf02c` handles CR by calling `0xf06e`, then `0xf34a`, then optional
  LF helper `0xf0b2` when line-termination bit 7 is set. Fixture
  `live CR span flush materializes 0x12714 page object` pins this
  order by re-arming `0x783186` / `0x783188` from the post-CR x cursor
  before the LF y advance is visible in final cursor state.
- `0x12714` clears `0x783184`, writes the local 8-byte source, calls
  `0x10084`, gates on `0x782db6`, calls `0x13520`, and retries after
  `0xff1e` on allocation failure. The retry path sets page-root
  `+0x14` bit 0 through byte `+0x15`, publishes the current root, calls
  `0x10084`, rebuilds the local source, and returns to the same
  `0x13520` call.
- `0x13520` selects portrait `0x1354a` or landscape `0x136d2` after
  `0x137a2` derives selector/key state.
- `0x1354a` emits one `0x135f0` segment-list entry when
  `row_low + row_count < 16`; otherwise it shortens the first row
  count, calls `0x135f0`, increments `0x782a7c`, clears row bits in
  `0x782a7e`, restores the remaining row count, and calls `0x135f0`
  again. Evidence: `0x13556..0x135de` and fixture
  `0x1354a portrait text span split queues adjacent buckets`.
- `0x135f0` appends a six-byte segment-list entry in a `0x26` object
  allocated through `0x1387c`.
- `0x136d2` inserts a fixed-width object under page-root `+0x28` using
  `0x1381c` storage. When the fixed list is nonempty, `0x13690` walks
  existing bucket bytes and `0x13748..0x1377c` links the new object
  before the first larger bucket byte or after the previous equal/lower
  node. Evidence: fixture
  `0x12714 landscape span inserts into nonempty fixed list`.

### Readers And Consumers

- `0xd4ac` consumes unflagged context fields `+0x2b`, `+0x2c`, and
  `+0x2d` after `0xd3b2` printable placement. Its branches are:
  disabled or before-lower exit at `0xd4b8..0xd4d8`, beyond-page exit
  at `0xd4da..0xd4ee`, alternate/default y update at
  `0xd4f0..0xd516`, low-water flush at `0xd51c..0xd536`, and high-x
  raise at `0xd53c..0xd548`.
- `0xd8fc` consumes flagged context fields `+0x16`, `+0x18`, and
  `+0x1a` after `0xd824` printable placement and after HT/BS/cursor
  helpers pick the active context. Its branches are: disabled or
  before-lower exit at `0xd908..0xd928`, beyond-page exit at
  `0xd92a..0xd93e`, alternate/default y update at `0xd940..0xd960`,
  low-water flush at `0xd966..0xd980`, and high-x raise at
  `0xd986..0xd992`.
- `0x1edc6` bridges page-root `+0x28` fixed-list objects to render
  offset `+0x20`, copying extent into render object word `+0x0a` and
  setting continuation bytes `+0x0c/+0x0d`.
- `0x1f812` consumes the portrait segment-list object from compact
  bucket storage and writes mask spans.
- `0x1f756` / `0x1f7b0` consume the landscape fixed-width object after
  bridge normalization and write repeated pattern spans.

### Output Effect

- Fixture `0x12714 portrait text span flush queues segment-list span`
  starts with pending state `low_x=2`, `high_x=18`, and `high_y=3`.
  `0x12714` clears `0x783184`, builds source `x=2`, `y=3`,
  `extent=16`, derives key `0x3200`, queues object
  `00 00 00 00 40 00 00 01 32 00 03 00 00 10 ...`, and `0x1f812`
  renders three full 16-pixel rows beginning at row index `3`.
- Fixture `0x12714 landscape text span flush queues fixed-width span`
  starts with pending state `low_x=2`, `high_x=5`, `high_y=3`,
  orientation `1`, and extent source `0x782db2=7`. `0x12714` builds
  source `x=3`, `y=3`, `extent=3`, derives key `0x3300`, queues fixed
  object `00 00 00 00 00 06 33 00 00 03 00 00 00 00`, the `0x1edc6`
  bridge normalizes it to `+0x20`, and `0x1f756` renders three shifted
  3-pixel rows.
- Fixture `live CR span flush materializes 0x12714 page object` drives
  `ESC &k1G!\r` through the mixed page-record parser model. The
  printable byte queues compact text object
  `00 00 00 00 00 00 00 01 20 00 01 ...`; CR then routes through
  `0xf02c` semantics, materializes pending state `2..18 @ y=3` through
  `0x12714`, inserts segment-list object
  `00 00 00 00 40 00 00 01 32 00 03 00 00 10 ...` ahead of the compact
  object in bucket `0`, re-arms `0x783186` and `0x783188` to x `5`,
  and renders rows where the three span rows occupy pixels `0..15`
  while the text glyph remains at pixels `16..19`.
- Fixture `flagged printable d8fc low-watermark flush renders span`
  drives byte `0x21` through the mixed page-record model with
  `cursor_x=10`, `cursor_y=21`, `low_x=100`, `high_x=120`, and flagged
  context `+0x16=0`, `+0x18=10`, `+0x1a=18`. Printable placement
  advances x to `28`, then `0xd8fc` computes `high_y=3`, sees current x
  below low watermark, calls the modeled `0x12714` / `0x126e2` path,
  and queues source `orientation=0`, `x=100`, `y=3`, `extent=20`. The
  queued segment-list object
  `00 00 00 00 40 00 00 01 34 06 03 00 00 14 ...` precedes the compact
  text object in bucket `0`, re-arm seeds `0x783186` / `0x783188` to
  x `28`, and `0x1f812` renders the span on rows `3..5` at pixels
  `96..115` while the text glyph stays at pixels `16..19`.
- Fixture `unflagged printable d4ac low-watermark flush renders span`
  drives byte `0x21` through the mixed page-record model with inline
  record `02 03 04 00 00 00 00 80`, `cursor_x=10`, `cursor_y=21`,
  `low_x=100`, `high_x=120`, and context bytes `+0x2b=7`,
  `+0x2c=0`, and `+0x2d=10`. `0xd3b2` queues compact text object
  `00 00 00 00 00 00 00 01 01 7a 00 ...`; `0xd140` advances x to
  `28`; `0xd4ac` computes `high_y=28`, sees current x below low
  watermark, calls the modeled `0x12714` / `0x126e2` path, and queues
  source `orientation=0`, `x=100`, `y=28`, `extent=20`. The queued
  segment-list object `00 00 00 00 40 00 00 01 c4 06 03 00 00 14 ...`
  precedes the compact text object in bucket `1`, re-arm seeds
  `0x783186` / `0x783188` to x `28`, and `0x1f812` renders the span on
  rows `12..14` at pixels `96..115` while the inline glyph stays at
  pixels `10..25` on rows `7..9`.
- Fixture `d4ac and d8fc span consumer branch family controls flush
  output` drives printable `!` through both selected source forms and
  covers the non-low-water branch family for the same pending state block.
  With `0x783184 = 0`, both consumers return disabled and leave only the
  compact text object. With current y `21` below lower bound `30`, both
  return `before-context-lower`; with current y `21`, height `50`, and
  page extent `64`, both return `beyond-page-extent`; neither case inserts
  a span object. With `low_x=0`, `high_x=20`, and printable advance to
  x `28`, the high-x path raises `0x783188`; the following CR flushes a
  segment-list object with source `x=0`, `extent=28`, ahead of the compact
  text object. The unflagged `d4ac` case uses default high-y `26` and
  renders bucket-relative rows `10..12`; the flagged `d8fc` case uses
  alternate offset `+0x1a = 18`, high-y `3`, and renders rows `3..5`.
- Fixture `0x1354a portrait text span split queues adjacent buckets`
  starts from a pending portrait span `low_x=2`, `high_x=22`, and
  `high_y=15`. `0x12714` builds source `x=2`, `y=15`, `extent=20`;
  `0x1354a` sees row low `15` plus row count `3` cross the bucket
  boundary, emits first object
  `00 00 00 00 40 00 00 01 f2 00 01 00 00 14 ...` in bucket `0`,
  then increments the bucket and clears the row bits to emit second
  object `00 00 00 00 40 00 00 01 02 00 02 00 00 14 ...` in bucket
  `1`. `0x1f812` renders the first bucket as one row at row `15` and
  the second bucket as two rows at rows `0..1`, each with 20 visible
  pixels.
- Fixture `0x12714 landscape span inserts into nonempty fixed list`
  seeds addressed fixed-list nodes at bucket bytes `2` and `6`, then
  drives a landscape pending span through `0x12714`. The packaged source
  is `orientation=1`, `x=7`, `y=0x40`, `extent=4`; `0x136d2` allocates
  object pointer `0x00d05020`, visits existing nodes
  `0x00d05004` and `0x00d05012`, and links the new object between them
  as chain `2 -> 4 -> 6`. The inserted raw object
  `00 d0 50 12 04 06 07 00 00 04 00 00 00 00` bridges to
  `00 d0 50 12 04 16 07 00 00 04 00 04 01 08`; `0x1f756` / `0x1f7b0`
  renders the bridged span at x `7`, rows `64..67`, with the selector-6
  fixed pattern.
- Fixture `0x12714 allocation failure publishes page and retries span`
  starts with an existing addressed compact text object under bucket
  `0`, then forces the landscape span allocation to fail. The first
  `0x136d2` attempt returns object pointer `0`, `allocation_failed=True`,
  and source `orientation=1`, `x=3`, `y=3`, `extent=3`. The retry path
  marks page-root `+0x14 = 1`, publishes the existing bucket object
  `00 00 00 00 00 00 00 01 20 00 01 ...` through `0xff1e`, creates a
  fresh root through `0x10084` with allocation count `2`, then retries
  the same source into fixed-list object
  `00 00 00 00 00 06 33 00 00 03 00 00 00 00` at pointer
  `0x00d07004`. The bridge emits
  `00 00 00 00 00 16 33 00 00 03 00 03 01 08`, and `0x1f756` /
  `0x1f7b0` renders three shifted 3-pixel rows at x `3`, y `3`.

### Confidence

High for pending-state initialization, unflagged `0xd4ac` low-water
success, flagged `0xd8fc` low-water success, disabled/lower-bound/page-extent
exits, high-x span extent updates, flush source packaging, portrait versus
landscape branch selection, portrait split output, landscape nonempty
insertion, allocation-failure retry publication, object byte shapes, bridge
shape, and visible row effects because each claim has disassembly and passing
fixtures.

### Fixtures

- `0x12714 portrait text span flush queues segment-list span`
- `0x12714 landscape text span flush queues fixed-width span`
- `0x137a2/0x136d2-modeled fixed-rule list object and bridge
  normalization`
- `0x1f756 fixed-width list renders bridged +0x20 object`
- `0x1f812 segment-list object renders counted mask spans`
- `0x136d2 address-aware fixed-list insertion uses 0x1381c storage`
- `0x1edc6 page-record bridge normalizes rule and fixed lists`
- `mixed printable/control page-record stream queues through 0x1387c`
- `live CR span flush materializes 0x12714 page object`
- `flagged printable d8fc low-watermark flush renders span`
- `unflagged printable d4ac low-watermark flush renders span`
- `d4ac and d8fc span consumer branch family controls flush output`
- `host-fetched type-2 0x1719c payload metrics feed d4ac and d8fc span rows`
- `host-fetched type-1 0x1719c payload metrics feed d4ac and d8fc span rows`
- `host-fetched metric variant changes d4ac gate and d8fc rows`
- `host-fetched clamped metric variant changes d4ac gate and d8fc rows`
- `host-fetched lower-bound metric variant suppresses d4ac and d8fc spans`
- `host-fetched upper-bound metric variant keeps d4ac span but suppresses d8fc`
- `legal descriptor metric value matrix drives d4ac and d8fc consumers`
- `legal descriptor metric boundary values drive d4ac and d8fc consumers`
- `legal descriptor metric range endpoints drive d4ac and d8fc consumers`
- `legal descriptor metric mixed values drive d4ac and d8fc consumers`
- `legal descriptor metric tight range values drive d4ac and d8fc consumers`
- `legal descriptor metric low-nibble rounding drives d4ac and d8fc consumers`
- `legal descriptor metric byte-boundary rounding drives d4ac and d8fc consumers`
- `0x1354a portrait text span split queues adjacent buckets`
- `0x12714 landscape span inserts into nonempty fixed list`
- `0x12714 allocation failure publishes page and retries span`

### Disassembly Evidence

- `generated/disasm/ic30_ic13_text_span_flush_012714.lst`:
  `0x12714..0x12808` for source packaging, page-extent gate, success
  queue call, and retry setup.
- `generated/disasm/ic30_ic13_text_span_state_0126e2.lst`:
  `0x126e2..0x12712` for re-arm helper initialization of `0x783184`,
  `0x783186`, `0x783188`, and `0x78318a`.
- `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`:
  `0xd23c..0xd25e` for unflagged printable placement into `0xd4ac`,
  `0xd66e..0xd690` for flagged printable placement into `0xd8fc`,
  plus `0xd4ac..0xd548` and `0xd8fc..0xd992` watermark writers.
- `generated/disasm/ic30_ic13_control_code_handlers_00f02c.lst`:
  `0xf02c..0xf050` for CR ordering and `0xf34a..0xf362` for the
  shared direct-control flush helper.
- `generated/disasm/ic30_ic13_display_list_helpers_013386.lst`:
  `0x13520..0x1381a` producer, insertion, split, and packed-key helpers.
- `generated/analysis/ic30_ic13_page_root_finalization.md`:
  `0xff1e` publication contract and the `0x127be` text-span retry
  call-site group.
- `generated/analysis/ic30_ic13_page_record_bridge.md` and
  `generated/analysis/ic30_ic13_render_dispatch_tables.md`:
  bridge and renderer consumers for fixed-width lists.

### Unresolved Middle Edges

- `0xd4ac..0xd548`: unflagged context fields `+0x2b`, `+0x2c`, and
  `+0x2d` are fixture-backed for the low-water success branch and tied
  to selected context records in `notes/font-context-metrics.md`. Fixture
  `host-fetched 0x1719c payload metrics feed d4ac span rows` proves one
  host-fetched type-0 downloaded payload copying descriptor bytes into this
  span consumer, and fixture
  `host-fetched type-2 0x1719c payload metrics feed d4ac and d8fc span rows`
  proves the same copied fields for a host-fetched type-2 payload. Fixture
  `host-fetched type-1 0x1719c payload metrics feed d4ac and d8fc span rows`
  proves the same copied fields for a host-fetched type-1 payload. All three
  change visible segment-list rows. Fixture
  `host-fetched metric variant changes d4ac gate and d8fc rows` changes
  copied word `+0x2c/+0x2d` from a parser-produced descriptor, proving that
  the old `+0x2d = 0x20` tight-page case exits as `beyond-page-extent` while
  the variant `+0x2d = 0x10` queues the same segment-list span. Fixture
  `host-fetched clamped metric variant changes d4ac gate and d8fc rows`
  lowers descriptor range/count word `+0x14` to `5`, clamps an oversized
  rounded-metric input into copied word `+0x2c = 0x0014`, proves byte `+0x2b`
  remains `0` for this `0x1719c` payload family, and flips a tight
  page-extent gate with `+0x2d = 0x14`. Fixture
  `host-fetched lower-bound metric variant suppresses d4ac and d8fc spans`
  raises copied lower byte `+0x2c` to `0x18` through descriptor word
  `+0x2c = 0x1800`, causing `0xd4ac` to exit `before-context-lower` at
  cursor y `21` while the compact glyph object remains queued. Fixture
  `host-fetched upper-bound metric variant keeps d4ac span but suppresses
  d8fc` expands descriptor range/count word `+0x14` to `0x0040`, leaves
  unflagged bytes `+0x2c/+0x2d = 0/0x20`, and proves `0xd4ac` still queues the
  default span at cursor y `21` / extent `64`. Fixture
  `d4ac and d8fc span consumer branch family controls flush output` covers
  the disabled, before-lower, beyond-page, and high-x-only consumer branches.
  Fixture `descriptor metric fields match across inline and resource contexts`
  proves inline/unflagged `d4ac` is legal and resource/unflagged `d4ac` is an
  invalid cross-form. Fixture
  `legal descriptor metric value matrix drives d4ac and d8fc consumers`
  adds the legal-value matrix: small, clamped, midpoint, and upper values
  leave `d4ac` span output visible, the zero-rounded-offset value preserves
  copied `+0x2c/+0x2d = 0/0` while still publishing the same `d4ac` span
  object, the negative-offset value copies `+0x2c/+0x2d = 0/8` while still
  publishing that span, and the lower-bound value makes `d4ac` exit before
  lower. Fixture
  `legal descriptor metric tight range values drive d4ac and d8fc consumers`
  proves the smallest legal range/count cross-products: range one copies
  `+0x14/+0x16/+0x18 = 0x0001/0x0000/0x0000`, range two copies
  `0x0002/0x0001/0x0000`, and the same producer path carries zero/clamped
  rounded words plus max positive/negative offset bytes to visible `d4ac` and
  `d8fc` rows. Additional metric values within legal forms are now
  cross-products of the documented producer formulas and consumer gates;
  bounded validation no-install branches are composed below under
  `Downloaded Resource Validation No-Install`.
- `0xd8fc..0xd992`: flagged context fields `+0x16`, `+0x18`, and `+0x1a` are
  fixture-backed for the low-water success branch and tied to selected context records
  in `notes/font-context-metrics.md`. Fixture `host-fetched 0x1719c payload metrics feed
  d8fc span rows` proves one host-fetched type-0 bit-30 downloaded payload copying
  descriptor words into this span consumer, and fixture `host-fetched type-2 0x1719c
  payload metrics feed d4ac and d8fc span rows` proves the same copied fields for a
  host-fetched type-2 payload. Fixture `host-fetched type-1 0x1719c payload metrics feed
  d4ac and d8fc span rows` proves the same copied fields for a host-fetched type-1
  payload. All three change visible segment-list rows. Fixture `host-fetched metric
  variant changes d4ac gate and d8fc rows` changes copied word `+0x1a` from a
  parser-produced descriptor, moving high-y from `16` to `19` and changing the rendered
  span object key from `0x0406` to `0x3406`. Fixture `host-fetched clamped metric
  variant changes d4ac gate and d8fc rows` changes copied words `+0x18` and `+0x1a` to
  `0` and `3`, moving high-y to `18` and changing the rendered span object key to
  `0x2406`. Fixture `host-fetched lower-bound metric variant suppresses d4ac and d8fc
  spans` raises copied lower word `+0x16` to `0x0018` and derived/cache count `+0x18` to
  `0x05e7`, causing `0xd8fc` to exit `before-context-lower` at cursor y `21` while the
  compact glyph object remains queued. Fixture `host-fetched upper-bound metric variant
  keeps d4ac span but suppresses d8fc` copies range/count `+0x14 = 0x0040` and
  derived/cache height `+0x18 = 0x003b`, causing `0xd8fc` to exit `beyond-page-extent`
  at cursor y `21` / extent `64` while the compact glyph object remains queued. Fixture
  `d4ac and d8fc span consumer branch family controls flush output` covers the disabled,
  before-lower, beyond-page, and high-x-only consumer branches. Fixture `descriptor
  metric fields match across inline and resource contexts` proves resource/flagged
  `d8fc` is legal and inline/flagged `d8fc` is an invalid cross-form. Fixture `legal
  descriptor metric value matrix drives d4ac and d8fc consumers` adds the legal-value
  matrix: small and clamped values publish `d8fc` span objects, midpoint copies
  `+0x18/+0x1a = 0x0013/0x0007` and updates high-y to `14` without a span object,
  zero-rounded-offset copies `+0x18/+0x1a = 0x0013/0x0000` and publishes high-y `21`
  with row digest `47361fc76bd6284f9d764c0377a3fda64edd3944b5cb2dff72acfd2224bc25e8`,
  negative-offset copies `+0x18/+0x1a = 0x0013/0xfffe`, consumes the offset as `65534`,
  computes high-y `-65513`, and renders digest
  `72bfa14c2a84532e2bdf6fb8fddf26ed6904c49dcf4fdcb322592471b5d5b281`, lower-bound exits
  before lower, and upper-bound exits beyond page extent. Fixture `legal descriptor
  metric boundary values drive d4ac and d8fc consumers` adds equality and offset
  endpoints: `d8fc` accepts copied lower word `+0x16 = 0x0015` at cursor y `21`, accepts
  exact page extent with copied height `+0x18 = 0x002b`, copies input offset byte `0x7f`
  as word `+0x1a = 0x007f` and computes high-y `-106`, copies input offset byte `0xff`
  as word `+0x1a = 0xffff` and computes high-y `-65514`, and proves rounded inputs
  `0x1500`, `0x1508`, and `0x15ff` all store `+0x2c = 0x0060` before `d4ac` exits beyond
  page extent. Fixture `legal descriptor metric range endpoints drive d4ac and d8fc
  consumers` adds first-code/range endpoint coverage for the `0x17430` derived-height
  formula: first-code zero copies `+0x14/+0x16/+0x18 = 0x0018/0x0000/0x0017`, and the
  range-minus-one endpoint copies `0x0015/0x0014/0x0000`. Both cases keep `d4ac` on the
  standard span digest through `+0x2c = 0x0008`, and keep `d8fc` on high-y `20` / digest
  `f830d30ea60a61f0b74a489c4b7df1bb25dc464b6765d170c19e7278a0267eab`. Fixture `legal
  descriptor metric mixed values drive d4ac and d8fc consumers` adds multi-field legal
  values that exercise `0x17430`, `0x1757a`, and `0x1762a` together. The middle-range
  row `first/range/rounded/offset = 0x0008/0x0030/0x002a/0x02` copies canonical
  `+0x14/+0x16 = 0x0030/0x0008`, derived/cache `+0x18 = 0x0027`, copied offset `+0x1a =
  0x0002`, and rounded word `+0x2c = 0x002c`; `d4ac` exits `beyond-page-extent` while
  `d8fc` renders digest
  `00c97b69bc50326e442dd060c88b710b8f00217d40809bed276d8ba48581fdc7`. The rounded
  `0x00ff` sibling keeps `+0x18/+0x1a = 0x0027/0x0002` but caps copied `+0x2c` to
  `0x00c0`. The offset-byte `0x80` sibling sign-extends to copied `+0x1a = 0xff80` and
  makes `d8fc` compute high-y `-65387`. The late first-code row
  `0x002f/0x0030/0x000c/0x00` derives `+0x18 = 0`, keeps `d4ac` on the standard span
  digest, and makes `d8fc` exit `before-context-lower`. Fixture `legal descriptor metric
  low-nibble rounding drives d4ac and d8fc consumers` adds low-nibble transform
  coverage: rounded inputs `0x0001`, `0x0003`, `0x0004`, `0x0005`, and `0x000f` copy to
  `+0x2c = 0x0000/0x0004/0x0004/0x0004/0x0010`, `d4ac` consumes those copied bytes while
  keeping the standard span digest, and `d8fc` keeps unchanged `+0x16/+0x18/+0x1a =
  0x0004/0x0013/0x0001`, high-y `20`, and digest
  `f830d30ea60a61f0b74a489c4b7df1bb25dc464b6765d170c19e7278a0267eab`. Fixture `legal
  descriptor metric extent fenceposts drive d4ac and d8fc consumers` combines
  `0x17430` and `0x1762a` at the `d8fc` page-extent gate. Canonical fields are
  first code `4`, range words `0x002f`, `0x0031`, and `0x0032`, rounded word
  `0x0020`, and offset bytes `0`, `1`, and `2`; derived/cache `+0x18` becomes
  `42`, `44`, and `45`, and copied offset word `+0x1a` becomes `0`, `1`, and
  `2`. The height-42 zero-offset case renders `d8fc` high-y `21` with digest
  `47361fc76bd6284f9d764c0377a3fda64edd3944b5cb2dff72acfd2224bc25e8`; the
  height-44 and height-45 cases exit `beyond-page-extent` even with offsets
  `1` and `2`, proving the page-extent gate uses the derived height before
  offset placement can recover a span. Fixture `legal
  descriptor metric byte-boundary rounding drives d4ac and d8fc consumers` adds the
  `0x1757a` byte-boundary submatrix: rounded inputs `0x00fd/0x00fe/0x0101/0x0102` with
  range/count `0x0042` copy `+0x2c = 0x00fc/0x0100/0x0100/0x0104`, and `0x0102` with
  range/count `0x0040` caps back to `0x0100`. The `0x00fd` case suppresses `d4ac` at
  `beyond-page-extent` with compact-only digest
  `86e3bb70d51c66ac608345dc3bff6476447ebc500d7c271808a53d6638d59ad6`, while crossing to
  `0x00fe` restores the standard `d4ac` span digest
  `67554ea70d7cfd9b11c0777e3cf65d51600a44301a4f93bd4d9b0c0fbc23c00e`. The same submatrix
  keeps `d8fc` at `beyond-page-extent` because derived/cache `+0x18 = 0x003d` or
  `0x003b` exceeds the page extent at cursor y `21`. Additional metric values outside
  the pinned legal matrix, boundary, extent-fence, range-endpoint, mixed-value,
  tight-range, low-nibble, and byte-boundary fixtures are cross-products of the
  documented producer formulas and consumer gates; bounded validation no-install
  branches are composed below under `Downloaded Resource Validation No-Install`.

## Downloaded Font Descriptor And Payload Chain

Status: documented as the soft-font command family from host parser records to
current downloaded-font records, payload allocation, installed glyph objects,
and visible compact text rows. The complete semantic note is
`notes/downloaded-fonts.md`.

Concept: `ESC *c#D`, `ESC *c#E`, `ESC *c#F`, and `ESC )s#W` / `ESC (s#W`
share a current downloaded-font state block. `0x11f96` selects descriptor
handler `0x15d0a` for zero `W` counts and payload handler `0x16c14` for
nonzero counts. The installed payload can become a font-resource candidate
selected by `0x14c64`, or a downloaded character object consumed by the
compact text renderer.

### Field Groups

- Canonical:
  - `0x782f2e`: current downloaded font id written by `0x15a56`.
  - `0x782f30`: current character/code word written by `0x15a18`.
  - `0x782640..0x782776`: 32 current downloaded-font records, each with id
    word `+0x00`, flags at `+0x02`, and payload pointer at `+0x06`.
  - `0x782782` and `0x782786`: unmarked and marked current-record counts
    updated by `0x17108` and `0x17150`.
  - candidate counters/cursors `0x78278e`, `0x782790`, `0x782796`,
    `0x782798`, `0x78279e`, `0x7827a0`, `0x7827ac`, `0x7827b0`, and
    `0x7827b4` updated by `0x16c14`/`0x1bc38`.
  - published downloaded-glyph page-record buckets copied by `0xff1e`: normal
    selector `0x0003` publishes bucket `1`, rows-`0x20` short selector
    `0x0003` publishes bucket `1`, rows-`0x40` short selector `0x0003`
    publishes bucket `1`, row-count matrix short rows `0x01`, `0x02`,
    `0x04`, `0x08`, `0x41`, and `0x7f` publish bucket `1`,
    linear-segmented selector `0x2003` publishes buckets `1` and `9` for rows
    `0x81` and rows `0x82`, row-count matrix segmented rows `0x83`, `0x84`,
    `0x85`, `0xc0`, `0xfd`, `0xfe`, and `0xff` publish buckets `1` and `9`,
    segmented-wide selector `0x3003` publishes buckets `1` and `9`, rows-`0x0102`
    downloaded installs publish only selector-`0x0003` bucket `1` because the
    printable inline source exposes row byte `0x02` to `0x12f2e`, and wide
    selector `0x1003` publishes bucket `1` for the even-span and
    payload-control odd-span streams.
- Parser scratch:
  - `0x78299e`: six-byte parsed-record cursor rewound by font handlers.
  - `0x783140`: payload byte budget used by descriptor and payload readers.
  - delayed `ESC )s#W` records restored by `0x11f96`/`0x16c14`: normal
    `80 57 00 06 00 00`, linear-segmented `80 57 01 02 00 00`, and even-span
    wide `80 57 00 12 00 00`; the rows-`0x0102` truncation fixture restores
    `80 57 02 04 00 00`; the row-count matrix restores records from
    `80 57 00 02 00 00` through `80 57 01 fe 00 00` for the thirteen short
    and segmented row-count siblings.
- Derived/cache:
  - `0x7827c6`, `0x7827ca`, `0x7827ce`, `0x7827d2`, `0x7827d6`,
    `0x7827d8`, `0x7827da`, and `0x7827c8`: continuation state for
    interrupted font payload reads.
  - `0x7827be`, `0x7827c2`, `0x7827c4`, and
    `0x7827de..0x7827e9`: downloaded-character descriptor scratch. `0x16336`
    fills the parsed byte count, row span, row count, and staged 12-byte
    character object record before `0x16498` allocates/copies the payload.
    Byte `+5` of that staged record is the descriptor/object mode byte; the
    ROM descriptor helper `0x16b1a` writes mode byte `1` for even byte spans
    and mode byte `2` for odd byte spans. Fixture `0x16b1a descriptor width
    helper emits only mode 1/2` samples accepted widths `1`, `8`, `9`, `16`,
    `17`, `24`, `25`, and `0x1068`, plus invalid widths `0` and `0x1069`,
    proving that the helper table produces only mode `1`/`2` on success and
    leaves scratch unchanged on width rejection. The mode-byte-`0` fixture is
    an artificial record-shape reject at the `0x16498` object boundary, not a
    value produced by the accepted `0x16336` helper table. This scratch buffer
    is reused by the `0x17026`/`0x1719c` resource-header route with a
    different interpretation.
  - downloaded-character width-span matrix: fixture `downloaded glyph
    width-span matrix publishes and renders all main helpers` installs
    canonical width words `0x0008..0x0080`, row word `0x0003`, mode bytes
    alternating `2/1` by span parity, and bitmap bytes for spans `1..16`.
    Odd spans above one are canonical split-plane glyph layout; restored
    `ESC )s#W` records and payload counts are parser scratch; bucket `0`,
    render word `+0x10 = 0`, and the `0x1f08e[D1]` helper are derived
    page/render state.
  - downloaded-character wide-remainder matrix: fixture `downloaded glyph
    wide-remainder matrix publishes and renders compact chunks` installs
    canonical width words `0x0088..0x0100`, row word `0x0003`, mode bytes
    alternating `2/1` by span parity, and bitmap bytes for matched spans
    `17..32`. Canonical install and publication metadata are also pinned for
    high-span probes `33`, `48`, `49`, `64`, and `255`. Derived/cache render
    state is selector `0x1003`, object byte `0x10`, bucket `0`, `0x2f27c`
    full-chunk helper, `0x1f1ac[1..15]` remainder helpers, and the span-`32`
    no-remainder two-chunk path; render width word `max(0x20, span)` and
    source-walk rows now match the installed bitmap above span `32`.
  - downloaded-character width-byte boundary: fixture `downloaded glyph
    width-byte boundary truncates page-record span` installs canonical width
    words `0x07f8`, `0x0800`, `0x0808`, and `0x1068` for spans `0x00ff`,
    `0x0100`, `0x0101`, and `0x020d`. Parser/page-record scratch is the
    current unflagged printable source record byte `+0`, which contains
    `0xff`, `0x00`, `0x01`, and `0x0d`. Derived/cache state is the `0x12f2e`
    selector choice: only span `0x00ff` remains selector `0x1003`; the wrapped
    spans queue selector `0x0003`. Derived render state now includes the first
    dispatch edge: `0x00ff` stays on compact-wide renderer `0x1f0d2`, while
    wrapped spans enter compact mode-0 at `0x1effe` and read helper-table
    entries `0x1f48e`, `0x1f492`, and `0x1f8c2`, targeting `0x20700000`,
    `0x4e90202c`, and `0x4e904cdf` outside decoded row-copy helper heads.
  - downloaded-character segmented-wide matrix: fixture `downloaded glyph
    segmented-wide matrix publishes and renders compact chunks` installs
    canonical width words `0x0088..0x0100`, row word `0x0081`, mode bytes
    alternating `2/1` by span parity, and bitmap bytes for matched spans
    `17..32`. Canonical install and publication metadata are also pinned for
    high-span probes `33`, `48`, `49`, and `64`. Derived/cache render state is
    selector `0x3003`, object byte `0x30`, buckets `0` and `8`, segment row
    skip `0x80`, A2/A3 source offsets, `0x2f27c` full-chunk helper,
    `0x1f1ac[1..15]` remainder helpers, and the span-`32` segmented
    no-remainder path; segment-1 source-walk rows now match the installed
    bitmap above span `32`.
  - downloaded-character segmented-wide row-byte boundary: fixture
    `downloaded segmented-wide row-byte boundary truncates page-record
    segments` installs canonical row words `0x0081`, `0x00ff`, `0x0100`,
    `0x0101`, and `0x0181` for span `0x11`. Parser/page-record scratch is the
    current unflagged printable source record byte `+1`, which contains
    `0x81`, `0xff`, `0x00`, `0x01`, and `0x81`. Derived/cache state is the
    `0x12f2e` selector and segment list: rows `0x0081` and `0x00ff` queue
    selector `0x3003` with segments `1` and `0`; rows `0x0100` and `0x0101`
    queue selector `0x1003`; row `0x0181` queues selector `0x3003` with only
    segments `1` and `0`. Derived render state uses the canonical installed row
    words after selector choice: rows `0x0100` and `0x0101` dispatch through
    `0x1f0d2` and split `80/176` and `80/177`; row `0x0181` dispatches only
    produced `0x1f264` segment objects, with segment `1` splitting `32/96` and
    segment `0` splitting `80/48`.
  - `0x782842..0x782851` and `0x782856`: optional symbol bytes and count
    staged by `0x16fae`.
  - `0x1ed84` render-record work words `+0x10/+0x16` copied from the
    published record and consumed by `0x1ef6a` bucket scheduling.
- Firmware bookkeeping:
  - `0x782862`: staging pointer set to `0x7827de`.
  - `0x7827ba`: payload unit count written by `0x17362`.
  - staged header `0x7827de`: copied into allocated payloads by `0x1719c`.
  - `0xff1e` clears the current page root, preserves empty rule/fixed lists
    and context slots, and sets the publication flag after copying the page
    record.
- Unknown:
  - exact HP manual labels for the `0x16fae` consumed-but-not-staged
    descriptor words/bytes.

### Writers

- `0x15a56` and `0x15a18` write current id and character state.
- `0x16df6` dispatches font-control values; `0x17108` and `0x17150` toggle
  current-record bit `6` and transfer counts.
- `0x15d0a` writes `0x783140`, reads descriptor bytes through `0x1599c`, and
  routes to `0x16498`, `0x16606`, `0x15b9a`, or `0x15c4c`.
- `0x16336` walks the downloaded-character descriptor helper table, writes
  parser scratch `0x7827be`/`0x7827c2`/`0x7827c4`, and stages the record bytes
  copied by `0x163b8`. Its helper pairs validate descriptor size, version,
  font-header compatibility byte `+0x20`, signed object words `+0/+2`,
  width, rows, and rounded word `+0x0a`; `0x15a94` performs the shared
  geometry/bounds check before `0x16396..0x163ae` drains extension bytes and
  subtracts them from the bitmap payload budget.
- `0x16c14` writes current-record ids/payloads, candidate flags/counters, and
  installed counts. For an existing-record replacement, it calls `0x1887a`
  before allocation; fixture
  `0x16c14 allocation failure releases existing payload through 0x1887a`
  proves that the old payload is released even when the later allocation exits
  through `skip-allocation-failed`.
- `0x1887a` clears the current-record id/payload and flag bits `4..7`,
  decrements marked/unmarked and class counters, shifts class-one cursors,
  clears matching continuation fields, marks matching context-stack bytes,
  deletes the candidate slot through `0x1bd2e`, refreshes matching active
  contexts through `0x179aa`, and finishes with `0x1b04c`.
- `0x16fae`, `0x17362`, `0x17026`, and `0x1719c` validate, stage, allocate,
  and initialize font-resource payload headers.
- `0x168dc` and `0x16942` copy downloaded glyph bitmap bytes and save
  continuation state.
- `0x16606` clears stale continuation state, writes bit-30-clear fixed-record
  table entries, copies bitmap bytes through `0x16874`, and refreshes selected
  contexts through `0x14c64` when the installed payload is active.
- `0x15c4c` resumes bit-30-clear fixed-record bitmap copies from continuation
  fields, including split-plane A4/A3 destinations and D4/D3 counters. On
  status `1` it clears continuation state and leaves the completed fixed-record
  payload consumable by the active context path. On status `0` it calls
  `0x17d7c` to release/rewrite the fixed-record entry, then clears
  continuation state.
- `0x17d7c` rewrites released bit-30-clear fixed-record entries, writes
  fallback side-table bytes, refreshes matching active contexts through
  `0x14c64`, and clears matching continuation state.
- `0x17a24` releases bit-30 offset-table entries delegated by `0x17d7c`,
  clears the selected 4-byte glyph/object pointer, refreshes matching active
  contexts through `0x14c64`, and clears matching continuation state.
- `0x16498` consumes the `0x16336` descriptor scratch for bit-30
  downloaded-character payloads. Its range branch `0x164f2..0x16540` treats
  high character codes as legal only when the font-header byte `+0x0c >= 1`;
  its copy/allocation branch `0x16558..0x16602` stores the object pointer only
  after allocation and `0x16874` return status. Accepted parser-produced
  descriptors stage mode byte `1` for even byte spans and mode byte `2` for
  odd byte spans through helper `0x16b1a`; resolver `0x1f354` consumes that
  byte on bit-30 offset-table glyphs to keep the odd-span trailing plane
  instead of padding the span. Fixture `0x16b1a descriptor width helper emits
  only mode 1/2` pins the helper write edges at `0x16b36..0x16b6a` and the
  invalid no-write edge at `0x16b26..0x16b34`. Fixtures
  `host-fetched even-span wide downloaded character renders through 0x1f0d2`,
  `host-fetched segmented downloaded character renders through 0x1f1f0`, and
  `host-fetched split-plane segmented downloaded character renders through
  0x1f1f0` cover the visible even-span and odd-span object paths. The
  mode-byte-`0` fixture exercises the pre-copy record-shape reject and leaves
  the table entry unchanged. Fixture `downloaded glyph width-span matrix
  publishes and renders all main helpers` carries accepted spans `1..16`
  through `0x16498` installs, including split-plane copies for odd spans above
  one. Fixture `downloaded glyph wide-remainder matrix publishes and renders
  compact chunks` carries accepted spans `17..32` through the same install and
  zero-drain return boundary before selector `0x1003` renders through
  `0x1f0d2`; the same fixture now probes accepted spans `33`, `48`, `49`,
  `64`, and `255` through the install/publication/dispatch boundary while
  leaving row equivalence open. Fixture `downloaded glyph segmented-wide
  matrix publishes and renders compact chunks` carries accepted spans `17..32`
  with rows `0x81` through the same install and zero-drain return boundary
  before selector `0x3003` renders segment `1` through `0x1f264`; the same
  fixture probes accepted spans `33`, `48`, `49`, and `64` through the
  upstream boundary while leaving segment-row equivalence open.

### Readers And Consumers

- `0x11f96` reads the parsed `W` count and schedules delayed font handlers.
- `0x172c0` scans the current-record pool by `0x782f2e`.
- `0x1b4c0` resolves payload pointers for descriptor routes.
- `0x16606` reads current character `0x782f30`, selected payload base
  `0x78285e`, byte budget `0x783140`, fixed-record entries, and continuation
  fields.
- `0x15c4c` reads saved payload `0x7827da`, saved glyph/table index
  `0x7827c8`, saved destination pointer `0x7827ca`, saved trailing-plane
  destination pointer `0x7827ce`, saved remaining count `0x7827d2`, saved
  split-plane counters `0x7827d6`/`0x7827d8`, and the fixed-record table entry
  in the selected payload.
- `0x17d7c` reads the selected payload base, fixed-record glyph/table index,
  payload word `+0x1a`, payload byte `+0x3c`, the base fixed-record entry
  `+0x40`, active primary/secondary context pointers, and continuation state.
- `0x17a24` reads bit-30 offset-table payload words `+0x08`, `+0x0e`, and
  `+0x10`, the selected 4-byte table entry, active primary/secondary context
  pointers, and continuation state.
- `0x1887a` reads the candidate longword from `0x1b4c0`, class bytes
  `+0x16` or `+0x20`, current-record flag bit `6`, continuation payload
  `0x7827da`, the eight-entry context stack at `0x782c1e`, default resolver
  state through `0x1b50e`, and active primary/secondary context pointers.
  Its helper branch reads fixed-record byte `+0x0e` through `0x18bf2` or
  offset-table range words `+0x0e/+0x10` through `0x18b92`.
- `0x1bc38` inserts installed payloads into the candidate list.
- `0x14c64` consumes installed candidate longwords and payload headers to
  build active maps.
- `0x1393a`, `0x12f2e`, `0x1387c`, `0x1edc6`, `0x1ed84`, and `0x1ef6a`
  consume the installed glyph path until visible compact text rows exist.

### Output Effect

The combined host-fetched stream `ESC *c4660d37e5F` plus `ESC )s2193W` payload plus `%`
sets current id `0x1234`, sets current character `0x25`, installs a split-plane
downloaded glyph object at record delta `0x0500`, queues printable `%` as segmented
compact selector `0x3003`, and renders the downloaded row through target `0x1effe`.
Fixture `combined font download FF publishes installed glyph page record` appends FF to
that same byte stream, routes `%` and FF through handlers `0xd04a` and `0xf0f0`,
publishes bucket array entries `9` and `1` through `0xff1e`, preserves empty rule/fixed
lists and context prefix `0,0,0,0`, and preserves the published segmented objects.
Fixture `published downloaded glyph segmented buckets render across bands` copies that
published record through `0x1ed84`, walks modeled band words `1` and `9` through
`0x1ef6a`, dispatches both compact objects to `0x1effe`, leaves the bucket-1 segment-0
band blank for this payload, and reproduces the same row from bucket `9`. Fixture
`0x1eba4 scheduler band words render published downloaded glyph` starts from the
`0xff1e`/`0x1ed84` seed where source `+0x18` has been cleared and render work
`+0x10/+0x16` are zero, lets the scheduler loop produce `0x1ef6a` calls for band words
`0..9`, and reaches the same bucket-9 visible row while only published buckets `1` and
`9` dispatch compact objects. Fixture `host-fetched even-span downloaded glyph FF
publishes rendered page record` adds the non-segmented wide publication sibling:
host-fetched `ESC )s18W` plus printable `)` and FF restores record `80 57 00 12 00 00`,
installs glyph `0x29` at table entry `0x00ee` / record delta `0x0780`, routes tail
handlers `0xd04a` and `0xf0f0`, publishes bucket array entry `1`, copies empty
rule/fixed lists and context prefix `0,0,0,0`, and renders the copied bucket-1 record
through `0x1ed84`/`0x1ef6a` to compact target `0x1effe` / renderer `0x1f0d2` with the
same 18-byte row. Fixture `downloaded normal row-0x80 and segmented glyph FF
publications render page records` adds three more publication siblings in the same
command family. The normal case drains host-fetched `ESC )s6W` plus printable `&` and
FF, restores record `80 57 00 06 00 00`, routes tail handlers `0xd04a` and `0xf0f0`,
publishes bucket `1` object `00 00 00 00 00 03 00 01 26 66 01`, clears the current root,
copies empty rule/fixed lists and context prefix `0,0,0,0`, and renders bucket word `1`
through `0x1ed84`/`0x1ef6a` to compact target `0x1effe` / renderer `0x1fe76`. The
row-threshold case drains host-fetched `ESC )s256W` plus printable `*` and FF, restores
record `80 57 01 00 00 00`, publishes bucket `1` object `00 00 00 00 00 03 00 01 2a 66
01`, keeps selector `0x0003`, and renders bucket word `1` through the same compact
target/helper with digest
`918ec4cca20024057ec1b82577b2ab5c039c6fc9a3f756be9bbb62a088bab7ac`. The non-boundary
short case drains host-fetched `ESC )s32W` plus printable `+` and FF, restores record
`80 57 00 20 00 00`, publishes bucket `1` object `00 00 00 00 00 03 00 01 2b 66 01`,
keeps selector `0x0003`, and renders bucket word `1` through the same compact
target/helper with digest
`28220dd2ecafaf07afc095fa0cc3cb6ed070984b3e3da6762b49ebda582d492b`. The rows-`0x20`
short case drains host-fetched `ESC )s64W` plus printable `1` and FF, restores record
`80 57 00 40 00 00`, installs record `00 00 00 00 0c 01 00 20 00 10 00 00`, publishes
bucket `1`, keeps selector `0x0003`, and renders bucket word `1` through
`0x1ed84`/`0x1ef6a` and compact target `0x1effe` / renderer `0x1fe76` with `38` visible
rows. The rows-`0x40` short case drains host-fetched `ESC )s128W` plus printable `2` and
FF, restores record `80 57 00 80 00 00`, installs record `00 00 00 00 0c 01 00 40 00 10
00 00`, publishes bucket `1`, keeps selector `0x0003`, and renders bucket word `1`
through `0x1ed84`/`0x1ef6a` and compact target `0x1effe` / renderer `0x1fe76` with `64`
blank current-band rows. The segmented case drains host-fetched `ESC )s258W` plus
printable `'` and FF, restores record `80 57 01 02 00 00`, publishes bucket `9` object
`00 00 00 00 20 03 00 01 27 01 66 01` plus the segment-0 bucket `1` entry, and renders
bucket word `9` through compact target `0x1effe` / renderer `0x1f1f0` from segment-1
source offset `0x0100`. Fixture `host-fetched rows-0x82 segmented downloaded glyph FF
publication renders page record` adds an interior segmented row count in the same
selector family. The host-fetched `ESC )s260W` plus printable `0` and FF restores record
`80 57 01 04 00 00`, installs record `00 00 00 00 0c 01 00 82 00 10 00 00`, publishes
bucket-array entries `1` and `9`, renders bucket word `9`, and emits two segment-1 rows
through `0x1ed84`/`0x1ef6a` and compact target `0x1effe` / renderer `0x1f1f0`. Fixture
`downloaded glyph width-span matrix publishes and renders all main helpers` covers the
downloaded-character width/span side of the same command family. Sixteen host-fetched
`ESC )s#W` streams install canonical widths `8..128`, row word `0x0003`, and mode bytes
`2` for odd spans or `1` for even spans. Parser scratch is the restored `80 57 #W`
record and payload byte count; canonical state is the installed table entry, record,
bitmap bytes, and split-plane flag; derived/cache state is the bucket-0 published page
record and the `0x1f08e[D1]` helper. All sixteen cases return through
`0x15dc6 -> 0x16498 -> 0x15dcc -> 0x12328` with copy status `1`, `0x783140 = 0`, no
drained bytes, and next handler `0xd04a`; `0x1ed84`/`0x1ef6a` dispatches object byte
`0x00` to compact target `0x1effe`. Rendered rows from helpers `0x1fa5c` through
`0x26910` match the installed bitmap rows in the fixture. Fixture
`downloaded glyph wide-remainder matrix publishes and renders compact chunks` covers
the compact-wide side of the same command family. Matched host-fetched `ESC )s#W`
streams install canonical widths `136..256`, row word `0x0003`, and mode bytes `2`
for odd spans or `1` for even spans. Canonical state is the installed table entry,
record, bitmap bytes, and split-plane flag; derived/cache state is selector `0x1003`,
object byte `0x10`, bucket `0`, full-chunk helper `0x2f27c`, row-skip caches, and the
selected remainder helper. Remainders `1..15` select `0x1f1ac[remainder]`, while span
`32` has remainder `0` and uses two full chunks with no remainder helper. All matched
cases return through `0x15dc6 -> 0x16498 -> 0x15dcc -> 0x12328` with copy status `1`,
`0x783140 = 0`, no drained bytes, and next handler `0xd04a`; `0x1ed84`/`0x1ef6a`
dispatches compact target `0x1effe` / `0x1f0d2`, and rendered rows match the installed
bitmap rows. The same fixture probes spans `33`, `48`, `49`, `64`, and `255` through
the same upstream metadata and return boundary, and those high-span rows match the
installed bitmap. Fixture
`downloaded glyph segmented-wide matrix publishes and renders compact chunks` covers
the segmented-wide side of the same command family. Matched host-fetched `ESC )s#W`
streams install canonical widths `136..256`, row word `0x0081`, and mode bytes `2` for
odd spans or `1` for even spans. Canonical state is the installed table entry, record,
bitmap bytes, and split-plane flag; derived/cache state is selector `0x3003`, segment-1
bucket `8`, segment-0 bucket `0`, object byte `0x30`, segment row skip `0x80`, A2/A3
source offsets, full-chunk helper `0x2f27c`, and the selected remainder helper.
Remainders `1..15` select `0x1f1ac[remainder]`, while span `32` has remainder `0` and
uses two full chunks with no remainder helper. All matched cases return through
`0x15dc6 -> 0x16498 -> 0x15dcc -> 0x12328` with copy status `1`, `0x783140 = 0`, no
drained bytes, and next handler `0xd04a`; `0x1ed84`/`0x1ef6a` dispatches compact target
`0x1effe` / `0x1f264`, and rendered segment-1 rows match the installed bitmap rows. The
same fixture probes spans `33`, `48`, `49`, and `64` at rows `0x81` through the same
upstream metadata and return boundary, and those segment-1 rows match the installed
bitmap.
Fixture
`downloaded glyph row-count matrix publishes and renders additional short/segmented
counts` adds thirteen more row-count siblings through the same fetched install,
printable, FF-publication, and render-entry chain. Rows `0x0001`, `0x0002`,
`0x0004`, `0x0008`, `0x0041`, and `0x007f` are canonical installed record
fields that derive selector `0x0003`, bucket `1`, object byte `0x00`, and
compact target `0x1effe`; rows `0x0083`, `0x0084`, `0x0085`, `0x00c0`,
`0x00fd`, `0x00fe`, and `0x00ff` derive selector `0x2003`, buckets `1` and
`9`, object byte `0x20`, and compact target `0x1effe` for render bucket word
`9`. Parser scratch is limited to the fetched `ESC )s#W` restored record and
payload byte count; derived/cache state is the `0xff1e` bucket array plus
`0x1ed84`/`0x1ef6a` dispatch. Published row counts for the thirteen cases are
`7`, `8`, `10`, `14`, `64`, `64`, `9`, `10`, `11`, `16`, `16`, `16`, and
`16`; rows `0x00c0`, `0x00fd`, `0x00fe`, and `0x00ff` intentionally share the
same rendered-row digest. Fixture `host-fetched rows-0x102 downloaded glyph FF
publication truncates page-record rows` adds the first nonzero-high-byte downloaded row
count in this family. The host-fetched `ESC )s516W` plus printable `3` and FF restores
record `80 57 02 04 00 00`, installs record `00 00 00 00 0c 01 01 02 00 10 00 00`, and
copies `0x0204` linear bytes into glyph `0x33`. The installed glyph table entry is
canonical downloaded-glyph state, but the printable source record is parser/page scratch
with only row byte `0x02`; `0x12f2e` therefore writes selector `0x0003` object `00 00 00
00 00 03 00 01 33 66 01`, publishes only bucket `1` through `0xff1e`, and leaves bucket
words `9` and `17` absent. This fixture does not claim rendered pixels: `0x1ef86`
computes `0x783a20 = 0x0040` and `0x783a28 = 0x00100800`, `0x1f414` splits coord
`0x6601` and rows `0x0102` into `58` current-band rows plus `200` fallback rows, and
span-2 row-copy helper `0x1fe76` has valid table entries only through index `128`;
fallback index `200` reads target `0x329ad3c0`. Fixture `split-plane segmented
downloaded glyph FF publication renders page record` adds the odd-span sibling:
host-fetched `ESC )s387W` plus printable `(` and FF restores record `80 57 01 83 00 00`,
publishes bucket `9` object `00 00 00 00 20 03 00 01 28 01 66 01` plus the segment-0
bucket `1` entry `00 00 00 00 20 03 00 01 28 00 66 01`, clears the current root, copies
empty rule/fixed lists and context prefix `0,0,0,0`, and renders bucket word `9` through
`0x1ed84`/`0x1ef6a` to compact target `0x1effe` / renderer `0x1f1f0` with A2 source
offset `0x0100` and A3 trailing offset `0x0080`. Fixture `host-fetched linear downloaded
character stream renders through 0x168dc` drives `ESC )s6W` through the same
parser-delayed `0x16c14` boundary, installs glyph `0x26` at table entry `0x00e2` with
even span `2`, copies bitmap bytes through the linear `0x168dc` reader, queues normal
compact selector `0x0003`, preserves the object through `0x1edc6`, and renders three
mode-0 rows through `0x1ed84` / `0x1ef6a`. Fixture `host-fetched 0x15d0a current-record
resource object feeds fixed-record render` also proves a host-fetched `ESC )s0W`
descriptor can route bit-30-clear current-record payload `0x000100` through `0x16606`,
install fixed-record glyph `0x21` at payload table entry `+0x48`, queue selector
`0x0003`, preserve context slot `3` through `0x1edc6`, and render three mode-0 rows.
Fixture `host-fetched 0x15d0a continuation resource object resumes fixed-record render`
proves the sibling status-`2` descriptor route through `0x15c4c`: a partial `0x16606`
copy saves payload `0x000100`, glyph/table index `0x21`, destination `0x000302`, and
remaining count `4`; `0x15c4c` copies bytes `f0 0f c3 3c`, clears the continuation
fields, and renders the same fixed record and rows. Fixture `host-fetched 0x15d0a
split-plane continuation resource object resumes fixed-record render` proves the
odd-width sibling: a partial `0x16606` copy of record `03 02 04 00 00 00 02 00` saves
payload `0x000100`, glyph/table index `0x21`, prefix destination `0x000303`, trailing
destination `0x000305`, and D4/D3 counters `0/0`; `0x15c4c` copies bytes `c1 d0`, clears
continuation state, leaves bitmap layout `a0 a1 c0 c1 b0 d0`, queues object prefix `00
00 00 00 00 03 00 01 01 76 01`, and renders rows reconstructed from `a0 a1 b0` and `c0
c1 d0`. Fixture `0x15c4c failed resource resume releases fixed-record object` proves the
status-`0` sibling: a partial `0x16606` copy saves the same payload and glyph/table
index, a short resume copies only bytes `f0 0f`, then `0x15c4c` calls `0x17d7c`. The
release helper rewrites payload `+0x48` from `02 03 04 00 00 00 02 00` to `01 02 00 fa
00 00 00 00`, writes side-table bytes `fa 00` at payload `+0x340`, records
active-primary refresh `0x7828de = 0`, and clears the matching continuation fields.
Fixture `0x17d7c releases extended fixed-record table with secondary refresh` proves the
direct extended fixed-record form: payload byte `+0x0e = 1` admits char `0xa1`, the
helper indexes table entry `payload + 0x40 + (0xa1 - 0x40) * 8`, rewrites it from `04 05
06 07 00 00 04 00` to `01 02 00 2c 00 00 03 00`, writes side-table bytes `2c 00` at
payload `+0x702`, records active-secondary refresh `0x7828de = 1`, and clears the
matching continuation fields. Fixture `0x17d7c delegates bit-30 release to offset-table
helper` proves the bit-30 sibling: `0x17d7c` dispatches to `0x17a24`, which validates
range words `+0x0e/+0x10 = 0x0020/0x007f`, uses table offset word `+0x08 = 0x004a`,
clears char `0x21` table entry `00 00 02 40` to zero at payload `+0x004a + 4 * 0x21`,
records active-secondary refresh `0x7828de = 1`, and clears the matching continuation
fields. Fixture `0x16c14 allocation failure releases existing payload through 0x1887a`
has no direct pixel output because it is a failed replacement path. Its output contract
is state cleanup: old current-record payload `0x123456` is cleared, candidate slot
`0x782328` is deleted, extended fixed-record cleanup runs through `0x18bf2`/`0x18090`
for characters `0x21..0x7f` and `0xa0..0xff`, continuation state is zeroed, context
stack bytes `+8` and `+9` are marked for matching primary/secondary entries, secondary
active context refreshes through `0x179aa(1)`, and no new candidate or payload is
installed. Fixture `0x16fae validation table semantic map covers staged and pass-through
entries` names all 32 validation-table entries by ROM effect. Fixture `0x16fae
table-driven validation predicates populate staged header fields` then proves the
success path plus two predicate failures: invalid resource type fails entry `2` after
four bytes with no symbols copied, and a reversed range fails entry `6` after words
`+0x16 = 10` and `+0x14 = 5`, leaving derived count word `+0x18 = 0`. Fixture `ESC )s80W
invalid resource type fails validation before allocation` connects that entry-2 failure
to the host-facing parser boundary: `0xa904` fetches the stream from the ring source,
parser dispatch walks `0x11eb6`, `0x12008`, `0x11ff6`, and `0x11f96`, delayed restore
reaches record `80 57 00 50 00 00`, `0x16fae` fails after descriptor bytes `00 01 02
03`, and `0x17026`/`0x16c14` skip allocation and install. The output effect is no
downloaded-font candidate or current-record mutation. Fixture `ESC )s80W reversed
resource range fails validation before allocation` connects the entry-6 range/count
failure to the same host-facing parser boundary. `0xa904` fetches `1b 29 73 38 30 57 00
01 00 00 00 00 00 0a 00 06 00 05...` from the ring source, parser dispatch again walks
`0x11eb6`, `0x12008`, `0x11ff6`, and `0x11f96`, delayed restore reaches record `80 57 00
50 00 00`, `0x16fae` fails after twelve descriptor bytes with staged words `+0x16 = 10`,
`+0x14 = 5`, and `+0x18 = 0`, and `0x17026`/`0x16c14` skip allocation and install. The
output effect is no downloaded-font candidate or current-record mutation. Fixture
`host-fetched metric variant changes d4ac gate and d8fc rows` starts from host-fetched
`ESC )s80W`, changes descriptor bytes copied by `0x1719c` into payload word `+0x2c =
0x0010` and word `+0x1a = 0x0002`, proves the default `+0x2d = 0x20` path fails a tight
`0xd4ac` extent check while the variant queues a span, and renders the `0xd8fc` span at
shifted key `0x3406`. Fixture `host-fetched clamped metric variant changes d4ac gate and
d8fc rows` adds the rounded-metric clamp sibling: descriptor range/count `+0x14 = 5`
caps an oversized rounded input so `0x1719c` copies `+0x2c = 0x0014`, leaves `+0x2b =
0`, flips a tight `0xd4ac` extent gate with `+0x2d = 0x14`, and renders the `0xd8fc`
span at shifted key `0x2406` from copied words `+0x18 = 0` and `+0x1a = 3`. Fixture
`host-fetched lower-bound metric variant suppresses d4ac and d8fc spans` adds the
lower-bound sibling: host-fetched descriptor bytes write canonical lower fields `+0x16 =
0x0018` and `+0x2c = 0x1800`, range/count `+0x14 = 0x0600`, and derived/cache count
`+0x18 = 0x05e7`. `0xd4ac` reads byte `+0x2c = 0x18`; `0xd8fc` reads word `+0x16 =
0x0018`; both return `before-context-lower` at cursor y `21`, and the fixture renders
only the compact glyph objects from the page-record buckets. Fixture `host-fetched
upper-bound metric variant keeps d4ac span but suppresses d8fc` adds the asymmetric
upper-bound sibling: host-fetched descriptor bytes write range/count `+0x14 = 0x0040`,
derive/cache `+0x18 = 0x003b`, and keep rounded word `+0x2c = 0x0020`. `0xd4ac` reads
bytes `+0x2c/+0x2d = 0/0x20` and still queues the default segment-list span; `0xd8fc`
reads word `+0x18 = 0x003b`, exits `beyond-page-extent` at cursor y `21`, and leaves
only the compact glyph object. Fixture `legal descriptor metric value matrix drives d4ac
and d8fc consumers` composes the legal metric cases into one state-block matrix. It
records parser input words, copied payload words, both consumer outcomes, queued page
objects, and row digests for small-rounded, clamped-rounded, midpoint-rounded,
zero-rounded-offset, negative-offset, lower-bound, and upper-bound descriptors. The
zero-rounded-offset row records parser range/count `0x0018`, rounded input `0x0000`, and
offset byte `0`; canonical fields `+0x14/+0x16 = 0x0018/0x0004`, derived/cache field
`+0x18 = 0x0013`, and consumer fields `+0x1a/+0x2c = 0x0000/0x0000` survive the
`0x16fae` / `0x1719c` copy. `0xd4ac` emits the same visible span digest
`67554ea70d7cfd9b11c0777e3cf65d51600a44301a4f93bd4d9b0c0fbc23c00e`, while `0xd8fc`
publishes high-y `21` and row digest
`47361fc76bd6284f9d764c0377a3fda64edd3944b5cb2dff72acfd2224bc25e8`. The midpoint row
records descriptor range/count `0x0018`, rounded input `0x0018`, and signed offset byte
`7`; `0xd8fc` updates high-y to `14` but leaves only compact glyph digest
`1a73b5e7454202d800c69f626bcf34e7d0d583b459e04c0bd4250010bf3ba28a`. The negative-offset
row records descriptor range/count `0x0018`, rounded input `0x0008`, and signed offset
byte `0xfe`; canonical fields `+0x14/+0x16 = 0x0018/0x0004`, derived/cache field `+0x18
= 0x0013`, and consumer fields `+0x1a/+0x2c = 0xfffe/0x0008` survive the `0x16fae` /
`0x1719c` copy. `0xd4ac` keeps the default visible span digest, while `0xd8fc` consumes
`+0x1a` as word `65534`, computes high-y `-65513`, queues span object prefix `00 00 00
00 40 00 00 01 04 06 03 00 00 14`, and renders digest
`72bfa14c2a84532e2bdf6fb8fddf26ed6904c49dcf4fdcb322592471b5d5b281`. Fixture `legal
descriptor metric range endpoints drive d4ac and d8fc consumers` adds the remaining
`0x17430` endpoint evidence in this cluster: first-code zero copies `+0x14/+0x16/+0x18 =
0x0018/0x0000/0x0017`, while first-code `range - 1` copies `0x0015/0x0014/0x0000`. Both
cases keep the rounded word `+0x2c = 0x0008`, keep the `d4ac` standard span digest, and
keep `d8fc` high-y `20` with digest
`f830d30ea60a61f0b74a489c4b7df1bb25dc464b6765d170c19e7278a0267eab`. Fixture `legal
descriptor metric low-nibble rounding drives d4ac and d8fc consumers` adds low-nibble
evidence for the rounded `+0x2c` producer transform. It varies parser rounded inputs
`0x0001`, `0x0003`, `0x0004`, `0x0005`, and `0x000f` while keeping the legal resource
and inline forms fixed. `0x16fae` / `0x1719c` copy those words to
`+0x2c = 0x0000/0x0004/0x0004/0x0004/0x0010`; `0xd4ac` consumes the copied `+0x2c/+0x2d`
bytes and keeps span digest
`67554ea70d7cfd9b11c0777e3cf65d51600a44301a4f93bd4d9b0c0fbc23c00e`, while `0xd8fc`
consumes unchanged `+0x16/+0x18/+0x1a = 0x0004/0x0013/0x0001`, keeps high-y `20`, queues
object prefix `00 00 00 00 40 00 00 01 44 06 03 00 00 14`, and renders digest
`f830d30ea60a61f0b74a489c4b7df1bb25dc464b6765d170c19e7278a0267eab`. Fixture
`host-fetched row-0x80 downloaded character remains short compact` pins the
downloaded-character row threshold immediately below segmented layout. Host fetch drains
`ESC )s256W`; parser dispatch walks `0x11eb6`, `0x12008`, `0x11ff6`, and `0x11f96`; the
restored record is `80 57 01 00 00 00`, payload offset is `7`, and payload length is
`256`. `0x16498` installs glyph `0x2a` at table entry `0x00f2`, record delta `0x0800`,
record `00 00 00 00 0c 01 00 80 00 10 00 00`, bitmap offset `0x080c`, rows `0x0080`,
width `0x0010`, span `2`, and split-plane flag `false` after copying the bytes through
`0x168dc`. `0x12f2e` keeps the glyph on short selector `0x0003` because the row test is
`rows > 0x80`; `0x1ef6a` dispatches compact target `0x1effe`; mode-0 helper `0x1fe76`
renders the bucket-1 band with digest
`918ec4cca20024057ec1b82577b2ab5c039c6fc9a3f756be9bbb62a088bab7ac`. Fixture `0x16498
replacement allocation failure partial and rejected downloaded character exits preserve
state` adds the replacement, allocator-failure, non-success, and continuation sibling
for the same object writer. The linear status-`2` branch copies four of six bytes
through `0x168dc`, writes table entry `0x00f6 -> 0x0840`, keeps record `00 00 00 00 0c
01 00 03 00 10 00 00`, and saves continuation fields `0x7827c6 = 1`, payload `0`, glyph
word `0x2b`, destination `0x0850`, and remaining count `2`. The split-plane status-`2`
branch copies prefix `a0 a1` and trailing `b0` through `0x16942`, writes table entry
`0x00fa -> 0x0880`, leaves bitmap layout `a0 a1 00 00 b0 00`, and saves prefix
destination `0x088e`, trailing destination `0x0891`, D4 counter `1`, and D3 counter `0`.
The replacement branch starts with table entry `0x0102` holding old record `00 00 02
00`; `0x1652a..0x1653e` calls `0x17a24`, which clears that old entry, clears the
matching continuation, refreshes the active primary context, and then `0x16498` writes
the new pointer `0x0900` plus bitmap `11 22 33 44 55 66`. The allocation-failure branch
computes a one-unit object allocation, receives zero from `0x170c`, reports
`0x9b5e(0x780e2e, 4)`, releases current payload `0x123456` through `0x1887a`, copies no
bitmap bytes, and leaves table entry `0x0106` zero. The `0x1887a` release clears
current-record canonical state, candidate slot `0x782328`, continuation fields, and
context-stack dirty bytes before the failed install returns with no replacement object.
The descriptor/object mode-byte-`0` shape reject returns status `0` with no table write
after the `0x16336` parse, while the header-type range reject for character `0xa0`
returns status `0` because `0x164f2..0x16540` accepts high character codes only when
font-header byte `+0x0c >= 1`. Disassembly evidence is `0x16336..0x163b6` for descriptor
parse/finalization, `0x164f2..0x16540` for range rejection, `0x1652a..0x1653e` for
replacement release, `0x1656e..0x165d8` for allocation failure and current-payload
release, `0x1658e..0x16602` for copy status and table-pointer storage,
`0x17a24..0x17b54` for old-pointer release, `0x1887a..0x18c4e` for current-payload
teardown, and `0x168dc` / `0x16942` for continuation state. Fixture `0x16498 no-install
exits preserve following printable output` carries those no-install exits through the
next visible byte. Host fetch drains each `ESC )s6W` payload plus printable `!` and
trailing FF; the resource side restores `80 57 00 06 00 00`, dispatches delayed handler
`0x16c14`, and returns reasons `allocation-failed`, `unsupported-record-shape`, or
`char-outside-header-type`. The following `!` then routes through `0xd04a`, queues the
baseline default-font compact object, and renders the same rows as the standalone
baseline `!`. The same fixture pins the no-install return boundary as `0x15dc6 ->
0x16498 -> 0x15dcc -> 0x12328` with `0x783140 = 6`; `0x12328` drains `de ad be ef ca fe`
for allocation failure and `f0 0f aa 55 3c c3` for mode/range reject before parser
handler `0xd04a` consumes `!`. Trailing FF routes through `0xf0f0`, publishes that
default-font bucket through `0xff1e`, clears the current page root, and renders the
published page record through `0x1ed84`/`0x1ef6a` with the same rows. Canonical renderer
state is therefore unchanged by those failed downloaded-character installs; the mutable
state is parser scratch plus firmware cleanup/bookkeeping from `0x1887a` for the
allocation failure case, and the published bucket/root is derived page-output state from
the unchanged default-font printable path. Fixture `0x16498 status-2 partial installs
remain printable` proves that copy status `2` takes the opposite visible contract. The
linear `ESC )s4W` case stores table entry `0x00f6 -> 0x0840`, bitmap `f0 0f aa 55 00
00`, and continuation destination `0x0850` with remaining count `2`; the following `+`
routes through `0xd04a`, resolves downloaded glyph `0x2b`, queues selector `0x0003`, and
renders rows from the partial bitmap plus zero-filled missing bytes. The split-plane
`ESC )s3W` case stores table `0x00fa -> 0x0880`, layout `a0 a1 00 00 b0 00`, and A4/A3
continuation destinations `0x088e`/`0x0891`; the following `,` resolves glyph `0x2c`,
queues selector `0x0003`, and renders the first row from prefix `a0 a1` plus trailing
`b0`. Both status-`2` cases return through `0x15dc6 -> 0x16498 -> 0x15dcc -> 0x12328`
with `0x783140 = 0`, a zero-byte `0x12328` drain, and next handler `0xd04a` for the
following printable byte. Canonical state includes the partially installed table
pointer, object record, and bitmap bytes; the continuation fields are firmware
bookkeeping needed to complete the same glyph later. The same fixture now carries both
status-`2` objects through trailing-FF publication: `0xff1e` copies bucket `1`, the
compact object root, empty rule/fixed lists, and context slots `(0,0,0,0)` into a
published pool record, clears the current page root, and `0x1ed84`/`0x1ef6a` render the
published rows from bucket word `1`. This classifies the published bucket root and
bucket array as derived page-output state from the canonical partial downloaded glyph;
the continuation fields remain firmware bookkeeping and are not consumed by the
published record. Fixture `host-fetched segmented downloaded character renders through
0x1f1f0` connects the downloaded-character linear reader to the remaining segmented
compact renderer shape. Host fetch drains `ESC )s258W`; parser dispatch walks `0x11eb6`,
`0x12008`, `0x11ff6`, and `0x11f96`; `0x16498` installs glyph `0x27` at table entry
`0x00e6` with record delta `0x0580`, rows `0x0081`, width `0x0010`, bitmap offset
`0x058c`, and `0x0102` bytes copied through `0x168dc`; `0x12f2e` queues selector
`0x2003`; `0x1edc6` preserves the segment-1 object; and `0x1ef6a` reaches compact
renderer `0x1f1f0`. The visible output is one segment-1 row from source offset `0x0100`,
rendered at x `22` as `####........####`. Fixture `downloaded normal row-0x80 and
segmented glyph FF publications render page records` now carries that linear segmented
install through the parser return and publication path: after `ESC )s258W`, the return
boundary is `0x15dc6 -> 0x16498 -> 0x15dcc -> 0x12328`, `0x783140 = 0`, zero drained
bytes, and next handler `0xd04a` for printable `'`; the derived published state is
bucket word `9` with bucket entries `1` and `9`, empty rule/fixed lists, and context
slots `(0,0,0,0)`. Fixture `host-fetched split-plane segmented downloaded character
renders through 0x1f1f0` adds the odd-span A2/A3 sibling. Host fetch drains `ESC
)s387W`; `0x16498` installs glyph `0x28` at table entry `0x00ea`, record delta `0x0700`,
rows `0x0081`, width `0x0018`, bitmap offset `0x070c`, and `0x0183` bytes copied through
`0x16942`. `0x12f2e` still queues selector `0x2003`, but `0x1f1f0` validates A2 source
offset `0x0100` and A3 trailing offset `0x0080` for segment `1`. The visible output is
`####........#####.#.#.#.` at x `22`. Fixture `split-plane segmented downloaded glyph FF
publication renders page record` pins the same return/publication contract for the
odd-span stream: `0x15dc6 -> 0x16498 -> 0x15dcc -> 0x12328`, `0x783140 = 0`, zero-byte
drain, and next handler `0xd04a` for printable `(` before `0xff1e` publishes bucket word
`9`. Fixture `host-fetched even-span wide downloaded character renders through 0x1f0d2`
covers the wide selector without payload-control normalization: `0xa904` fetches `ESC
)s18W`, parser dispatch reaches delayed handler `0x16c14` with restored record `80 57 00
12 00 00`, `0x16498` installs glyph `0x29` at table entry `0x00ee`, record delta
`0x0780`, rows `1`, width `0x0090`, bitmap offset `0x078c`, and split-plane flag
`false`, and `0x168dc` copies all 18 bytes with `control_hits = 0`. `0x12f2e` queues
selector `0x1003` and bucket object `00 00 00 00 10 03 00 01 29 66 01` plus allocator
padding; `0x1edc6` preserves it; and `0x1ef6a` reaches compact renderer `0x1f0d2`, where
the linear source row uses one full 16-byte chunk plus a 2-byte remainder and renders at
x `22`.

### Downloaded Resource Validation No-Install

Status: composed as the downloaded-resource error cluster from host-fetched
`ESC )s80W` and short-budget `ESC )s8W` bytes through parser restore,
descriptor validation, allocation skip, candidate no-install, and visible
default-font output. The low-level ledger remains in
`notes/downloaded-fonts.md` under `Descriptor Validation And Payload Header`.

Concept: `0x16fae` walks the 32-entry descriptor-validation table at
`0x16eae`. When a predicate returns failure, `0x17026` receives validation
status `0`, returns allocation status `0`, and `0x16c14` leaves the current
downloaded-font records and candidate list unchanged. Fixture
`ESC )s#W validation failures preserve following printable output` then
appends printable `!` and proves the parser resumes at `0xd04a`, queues the
baseline default-font compact object, and renders the same rows as a stream
without the failed font payload.

Field groups:

- Canonical downloaded-font state: current-record pool
  `0x782640..0x782776`, candidate count/cursors `0x78278e`,
  `0x782790`, `0x782796`, `0x782798`, `0x78279e`, `0x7827a0`,
  `0x7827ac`, `0x7827b0`, and `0x7827b4`, and selected installed
  candidate longword. Writers on success are `0x16c14` and `0x1bc38`; the
  eight validation-failure fixtures assert no install for this state.
- Parser scratch: restored records `80 57 00 50 00 00` and short-budget
  `80 57 00 08 00 00`, payload byte budget `0x783140`, parser record cursor
  `0x78299e`, host ring source `0xa904`, and parser handlers `0x11eb6`,
  `0x12008`, `0x11ff6`, and `0x11f96`.
- Parser-owned staged descriptor fields: staged header `0x7827de`, staged
  pointer `0x782862`, type byte `+0x0c`, first-code word `+0x16`,
  line/count word `+0x12`, range/count word `+0x14`, derived count word
  `+0x18`, and class byte `+0x20`. `0x16fae` writes only the fields reached
  before the failed predicate.
- Metric field grouping: canonical fields are first code/lower bound
  `+0x16`, range/count `+0x14`, and signed flagged offset `+0x1a`; derived
  or cache fields are `+0x18` and rounded unflagged word `+0x2c`; parser
  scratch is the staged base `0x782862`, validation cursor, payload budget
  `0x783140`, and optional symbol staging `0x782842..0x782856`; firmware
  bookkeeping includes type byte `+0x0c`, allocation units `0x7827ba`, and
  byte `+0x2b` for the covered metric family.
- Derived/cache state: `+0x18` is derived by validation entry `6` helper
  `0x17430..0x1749c` as range/count minus first code minus one. Rounded
  unflagged word `+0x2c` is derived by entry `12` helper `0x1757a..0x175b8`
  as `min((value + 2) >> 2, word(+0x14)) << 2`; the boundary,
  range-endpoint, and low-nibble metric fixtures prove the cap,
  derived-height endpoints, and rounding behavior in page-visible `0xd4ac` /
  `0xd8fc` output. Optional symbol bytes `0x782842..0x782851` and count
  `0x782856` remain empty on the covered failure exits because validation
  fails before `0x16fe4`.
- Firmware bookkeeping: allocation status `0`, install state `None`, and the
  fully drained host source are failure bookkeeping. They are not printable
  page state, but they gate whether the subsequent `!` uses a downloaded font
  or the unchanged default font.
- Unknown for this checkpoint: external HP manual names for descriptor fields
  that the table consumes but does not stage. The ROM-internal rejecting
  predicate helpers are all in entries `2`, `4`, `5`, `6`, and `7`; the other
  validation entries are pass-through, clamps, or field writers.

Writers and readers:

- `0x16fae` reads descriptor bytes/words through `0x1599c`, `0x159b6`,
  `0x159d4`, and `0x159f6`, dispatches predicates from table `0x16eae`,
  and writes staged fields only for accepted entries.
- `0x17362` is the entry-2 type writer/predicate. Invalid type byte `3`
  fails after four consumed bytes before allocation size exists.
- `0x173d0` is the entry-4 first-code predicate. Word `0x1068` fails after
  eight consumed bytes before writing payload word `+0x16`.
- `0x173fe` is the entry-5 line/count predicate. Zero and `0x1069` both
  fail after ten consumed bytes with no valid line/count payload. The
  short-budget `ESC )s8W` case also reaches this predicate but exhausts the
  byte budget before a line/count word exists, so the modeled reader supplies
  zero and validation fails after eight descriptor bytes.
- `0x17430` is the entry-6 range/count predicate. Reversed range
  `+0x16 = 10`, value `5`, and high value `0x1069` fail at the
  twelve-byte boundary; the reversed-range fixture leaves `+0x14 = 5` and
  derived `+0x18 = 0`.
- `0x1757a` is the entry-12 rounded-metric transform for unflagged
  `0xd4ac` fields. It rounds `(value + 2) >> 2`, caps that result to
  canonical range/count `+0x14`, shifts back left by two, and writes the word
  to `+0x2c`; fixtures prove `0x0013 -> 0x0014`,
  `0x1500/0x1508/0x15ff -> 0x0060`, and
  `0x0001/0x0003/0x0004/0x0005/0x000f ->
  0x0000/0x0004/0x0004/0x0004/0x0010`.
- `0x1762a` is the entry-21 signed-offset writer for flagged `0xd8fc`.
  It stores the signed-byte reader result as word `+0x1a`; fixtures prove
  offset bytes `0x7f`, `0xfe`, and `0xff` become copied words
  `0x007f`, `0xfffe`, and `0xffff`, which `0xd8fc` consumes directly.
- `0x1749e` is the entry-7 class predicate. Class byte `2` fails after
  thirteen consumed bytes, after staging `+0x16 = 4`, `+0x12 = 6`,
  `+0x14 = 9`, and `+0x18 = 4`, but before writing `+0x20`.
- `0x17026` consumes the validation status and skips allocation on status
  `0`; `0x16c14` consumes that allocation status and installs no candidate.
- `0xd04a`, `0x1393a`, `0x12f2e`, `0x1ed84`, and `0x1ef6a` consume the
  following printable `!` on the default-font path after each failed payload.

Output effect: invalid type, first-code overflow, zero line/count, high
line/count, short descriptor budget, reversed range/count, high range/count,
and invalid class all produce the same visible result for the following
printable byte. No downloaded-font candidate is installed, no current-record
payload is selected, the default-font compact object matches the baseline `!`,
and the final rendered rows match the baseline rows.

Confidence is high for the parser boundary, failed validation entries, last
staged fields, allocation skip, no-install result, resumed printable handler,
default compact object, and rendered rows because fixture
`ESC )s#W validation failures preserve following printable output` asserts
the seven bounded `ESC )s80W` no-install streams and short-budget
`ESC )s8W` stream. Confidence is high for ROM-internal rejecting validation
coverage because disassembly shows only predicate helpers `0x17362`,
`0x173d0`, `0x173fe`, `0x17430`, and `0x1749e` can return failure; the
remaining validation entries cannot create additional no-install error forms.

Fixtures:

- `0x16fae validation table semantic map covers staged and pass-through
  entries`
- `0x16fae table-driven validation predicates populate staged header fields`
- `ESC )s80W invalid resource type fails validation before allocation`
- `ESC )s80W reversed resource range fails validation before allocation`
- `ESC )s80W additional validation predicate failures skip allocation`
- `ESC )s#W validation failures preserve following printable output`

Disassembly evidence:

- `generated/disasm/ic30_ic13_font_resource_validate_016fae.lst`
- `generated/disasm/ic30_ic13_font_resource_validate_predicates_017358.lst`
- `generated/disasm/ic30_ic13_font_resource_find_017026.lst`
- `generated/disasm/ic30_ic13_font_resource_object_add_016c14.lst`
- `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`
- `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`

Unresolved middle edges: `0x16fae..0x17016` is fixture-backed for every
ROM-internal rejecting predicate family: entries `2`, `4`, `5`, `6`, and `7`
plus the short-budget `ESC )s8W` entry-5 failure, including resumed visible
output. There is no remaining ROM-internal validation no-install edge outside
those predicates; the remaining edge is external naming for
consumed-but-not-staged descriptor fields.

### Downloaded Glyph Rule/Raster Composition

Status: anchored as a composition checkpoint from a host-fetched downloaded
glyph install into a parser-driven heterogeneous page-record render. Fixture
`host-fetched downloaded glyph composes with rule and raster through 0x1ef6a`
starts with the same `ESC )s18W` host-fetch, parser handlers `0x11eb6`,
`0x12008`, `0x11ff6`, `0x11f96`, delayed `0x16c14` install, and glyph `0x29`
resource state documented above. It then queues the installed glyph, a
selector-7 rule, and a mode-0 raster object into one active page record and
renders the composed pixels through the shared `0x1ed84`/`0x1ef6a` entry.
Fixture `parser-driven downloaded glyph rule raster stream composes through
0x1ef6a` narrows that edge: the fetched stream is split at byte `24` after the
same font payload, then page bytes
`ESC *c12a3b0P ) ESC *t300R ESC *r0A ESC *b2W c3 3c` route through the mixed
parser/page-record runner before rendering.

Field groups:

- Canonical font resource state: downloaded glyph table entry `0x00ee`, record
  delta `0x0780`, bitmap offset `0x078c`, bitmap size `18`, glyph mode `1`,
  rows `1`, width `0x0090`, and source kind `downloaded-pointer`. Writer:
  `0x16498` using the linear `0x168dc` reader. Fixture
  `host-fetched even-span wide downloaded character renders through 0x1f0d2`
  pins the exact installed record bytes
  `00 00 00 00 0c 01 00 01 00 90 00 00` and bitmap bytes
  `f0 0f aa 55 3c c3 81 7e ff 00 18 e7 24 db 42 bd 66 99`. Consumer:
  `0x1393a` / `0x12f2e` during page-object production and compact renderer
  `0x1f0d2` after `0x1ef6a` dispatches target `0x1effe`.
- Canonical page-record state: bucket `5` chain contains mode-0 raster object
  `00 00 00 00 80 00 00 02 00 00 c3 3c` followed by downloaded glyph object
  `00 00 00 00 10 03 00 01 29 06 01...`; rule list contains queued selector-7
  object `00 00 00 00 05 07 08 01 00 0c 00 03 00 00`; context slots are
  `(0, 0, 0, 0)`. Writers: `0x12f2e` for the glyph object, `0x13386` for the
  rule object, and `0x13070` for the raster object.
- Derived/cache render fields: `0x1ed84` copies the active record and seeds
  render word `+0x10 = 5`; `0x1edc6` normalizes the rule to
  `00 00 00 00 05 17 08 01 00 0c 00 03 00 03`; `0x1ef86` derives per-band
  setup before dispatch. These fields are consumed by `0x1ef6a` and are not
  canonical parser state.
- Parser scratch: the font payload command record is `80 57 00 12 00 00` at
  payload offset `6`, and payload bytes are
  `f0 0f aa 55 3c c3 81 7e ff 00 18 e7 24 db 42 bd 66 99`. In the
  parser-driven page stream, rectangle handlers `0x10e68`, `0x10e22`, and
  `0x10898` consume `ESC *c12a3b0P`; printable handler `0xd04a` consumes byte
  `0x29`; raster handlers `0x10808`, `0x1075a`, and delayed `0x11f82` /
  `0x105d0` consume `ESC *t300R ESC *r0A ESC *b2W c3 3c`. The delayed raster
  record is `80 57 00 02 00 00`, snapshot
  `01 00 01 05 d0 80 57 00 02 00 00`, payload offset `28`, and payload
  `c3 3c`.
- Firmware bookkeeping: active-copy words reported by the fixture are
  zeroed source/render work words before the fixture sets render word `+0x10`
  for bucket `5`; no page publication or root clear occurs in this checkpoint.
- Unknown for this checkpoint: full-success return-boundary siblings outside
  the even-span downloaded-glyph plus rule/raster stream and outside the
  separate no-install/status-`2`, segmented-publication, and combined
  segmented-wide publication visible fixtures. The page stream itself now
  drives the glyph, rule, and raster producers together; the font payload
  install still enters the page phase as a modeled resource image.

The modeled resource image is now a pinned handoff, not an implicit fixture
shortcut. The page-stream runner uses exactly
`bytearray(downloaded_wide_even_install["header"])`, the header produced by the
host-fetched `0x16c14` / `0x16498` install fixture. With that header, printable
byte `0x29` resolves to glyph entry `0x0780`, bitmap `0x078c`, width `0x0090`,
rows `1`, inline record `12 01 00`, and context slot `3` before `0x12f2e`
queues selector `0x1003`. The formerly unresolved address boundary is the
live CPU continuation from the delayed install return at `0x16c14` / `0x16498`
after stream byte `24` back into parser loop `0x11774`, where the next page
byte starts the `0x10e68` rectangle handler; fixture `parser-driven
downloaded glyph rule raster stream composes through 0x1ef6a` now pins that
even-span boundary as `0x15dc6 -> 0x16498 -> 0x15dcc -> 0x12328`, with copy
status `1`, copy stream position `18`, remaining `0x783140 = 0`, a zero-byte
`0x12328` drain, and next handler `0x10e68`. The split-plane, segmented,
no-install, status-`2`, linear segmented, and split-plane segmented
return-boundary siblings are covered by separate visible-output fixtures only
where cited below. Fixture `combined font download FF publishes installed glyph
page record` now also pins the segmented-wide sibling: copied record
`00 00 00 00 0c 02 00 81 00 88 00 00`, table entry `0x00de`, bitmap size
`0x0891`, copy status `1`, copy stream position `0x0891`, remaining
`0x783140 = 0`, zero-byte `0x12328` drain, and next handler `0xd04a` for the
printable `%` before FF publication. Other full-success return siblings remain
open cross-products.

Readers and output effect: `0x1ef6a` runs call order `0x1ef86`, `0x1efc2`,
`0x1f446`, `0x1f756`. The bucket dispatcher sends the raster object to
`0x1f88e` and the glyph object to `0x1effe`; `0x1f446` renders the rule through
solid helper `0x1f596`. The fixture compares three final composed rows: row 0
contains raster payload `c3 3c`, the downloaded glyph row at x `22`, and the
rule from x `24` through x `35`; rows 1 and 2 contain the rule only.

Confidence is high for the installed glyph resource fields, page-record object
bytes, render call order, dispatch targets, rule helper, and composed rows
because they are asserted by fixture
`host-fetched downloaded glyph composes with rule and raster through 0x1ef6a`.
Confidence is high for the page-stream producer schedule because fixture
`parser-driven downloaded glyph rule raster stream composes through 0x1ef6a`
asserts fetch boundaries, page parser handlers, glyph source fields, delayed
raster scratch, queue bytes, dispatch targets, and final rows. Confidence is
medium for the live CPU memory handoff between the font-install phase and the
page-stream phase.

### Confidence

High for command dispatch, current-record state, existing-record release ordering before
allocation failure, staged header fields, payload allocation, installed
downloaded-character object, and visible row, because the fixtures tie host-fetched
streams to parser records, teardown state, and render rows. High for the
downloaded-character parser-to-page path for the normal, wide/control, even-span wide,
row-threshold, segmented, and segmented-wide compact selectors represented by fixtures
`host-fetched linear downloaded character stream renders through 0x168dc`, `host-fetched
downloaded character payload control reaches wide render`, `host-fetched even-span wide
downloaded character renders through 0x1f0d2`, `host-fetched row-0x80 downloaded
character remains short compact`, `0x16498 replacement allocation failure partial and
rejected downloaded character exits preserve state`, `0x16498 no-install exits preserve
following printable output`, `0x16498 status-2 partial installs remain printable`,
`host-fetched segmented downloaded character renders through 0x1f1f0`, `host-fetched
split-plane segmented downloaded character renders through 0x1f1f0`, and `host-fetched
downloaded character stream reaches rendered object`. High for the modeled FF
publication boundary of the combined downloaded-glyph stream because the fixture asserts
the full fetched stream boundaries, published bucket array entries `1` and `9`, selected
render bucket words `1` and `9`, dispatch target, and final rows. High for the even-span
wide publication sibling because fixture `host-fetched even-span downloaded glyph FF
publishes rendered page record` asserts the host-fetched `ESC )s18W` payload, tail
handlers `0xd04a` and `0xf0f0`, published bucket `1`, `0x1ed84` render word `1`, compact
dispatch target `0x1effe`, and final `0x1f0d2` rows. High for the payload-control
odd-span wide publication sibling because fixture `host-fetched payload-control
downloaded glyph FF publishes page record` asserts the `1a 58` normalized payload,
mode-byte-`2` record `00 00 00 00 0c 02 00 01 00 88 00 00`, nonzero return drain
`0x783140 = 1` consuming `&`, post-return FF handler `0xf0f0`, published bucket `1`,
`0x1ed84` render word `1`, compact dispatch target `0x1effe`, and final modeled
`0x1f0d2` rows. High for the normal, non-boundary short, rows-`0x20` short, rows-`0x40`
short, row-`0x80`, segmented, rows-`0x82` segmented, and split-plane segmented
publication siblings because fixtures `host-fetched nonboundary short downloaded glyph
FF publication renders page record`, `host-fetched rows-0x20 short downloaded glyph FF
publication renders page record`, `host-fetched rows-0x40 short downloaded glyph FF
publication renders page record`, `downloaded normal row-0x80 and segmented glyph FF
publications render page records`, `host-fetched rows-0x82 segmented downloaded glyph FF
publication renders page record`, and `split-plane segmented downloaded glyph FF
publication renders page record` assert fetched stream boundaries, parser-restored
records, tail handlers `0xd04a` and `0xf0f0`, published bucket entries `1` and `9`,
selected render bucket words, compact target `0x1effe`, row-`0x80` selector `0x0003`,
rows `0x20` selector `0x0003`, rows `0x40` selector `0x0003`, rows `0x82` selector
`0x2003`, split-plane A2/A3 source offsets, dispatch object bytes `0x00` and `0x20`, and
final `0x1fe76`/`0x1f1f0` rows. High for main downloaded width-span rendering because
fixture `downloaded glyph width-span matrix publishes and renders all main helpers`
asserts spans `1..16`, mode-byte parity, split-plane copies for odd spans above one,
zero-drain return boundaries, bucket-0 FF publication, `0x1ed84`/`0x1ef6a` dispatch,
helper targets `0x1fa5c..0x26910`, and rows matching the installed bitmap. High for
compact-wide downloaded rendering because fixture `downloaded glyph wide-remainder
matrix publishes and renders compact chunks` asserts spans `17..32`, mode-byte parity,
split-plane copies for odd spans, selector `0x1003`, object byte `0x10`, full-chunk
helper `0x2f27c`, `0x1f1ac` remainders `1..15`, the no-remainder span-`32` sibling,
zero-drain return boundaries, bucket-0 FF publication, `0x1ed84`/`0x1ef6a` dispatch, and
rows matching the installed bitmap; the same fixture makes high-span probes `33`, `48`,
`49`, `64`, and `255` high-confidence for upstream metadata and row equivalence.
High for the width-byte producer boundary because fixture `downloaded glyph
width-byte boundary truncates page-record span` asserts spans `0x00ff`,
`0x0100`, `0x0101`, and `0x020d`, the canonical installed width words, the
one-byte source records, the resulting `0x12f2e` selectors, and the first
render edge. The wrapped spans select compact mode-0 helper entries `0x1f48e`,
`0x1f492`, and `0x1f8c2`, whose targets are not decoded row-copy helper heads.
High for segmented-wide downloaded rendering because
fixture `downloaded glyph segmented-wide matrix publishes and renders compact chunks`
asserts spans `17..32`, rows `0x81`, mode-byte parity, split-plane copies for odd spans,
selector `0x3003`, object byte `0x30`, segment row skip `0x80`, A2/A3 source offsets,
full-chunk helper `0x2f27c`, `0x1f1ac` remainders `1..15`, the no-remainder span-`32`
sibling, zero-drain return boundaries, bucket-0/bucket-8 FF publication,
`0x1ed84`/`0x1ef6a` dispatch, and segment-1 rows matching the installed bitmap; the same
fixture makes high-span probes `33`, `48`, `49`, and `64` high-confidence for upstream
metadata and row equivalence. High for
publication-to-scheduler band progression because `0xff1e` disassembly at `0xffc8`
clears root `+0x18`, `0x1ed84` copies that word into render `+0x10/+0x16`, and fixture
`0x1eba4 scheduler band words render published downloaded glyph` proves `0x1eba4` emits
band words `0..9` through `0x1ef6a` and preserves the same visible row. High for
the segmented-wide row-byte producer boundary because fixture `downloaded
segmented-wide row-byte boundary truncates page-record segments` asserts row
words `0x0081`, `0x00ff`, `0x0100`, `0x0101`, and `0x0181`, the one-byte
source records, the resulting `0x12f2e` selectors/segments, the `0x1f0d2`
splits for rows `0x0100` and `0x0101`, and the produced `0x1f264` segment
splits for row `0x0181`. High for
downloaded-glyph/rule/raster render composition because fixture `host-fetched downloaded
glyph composes with rule and raster through 0x1ef6a` asserts the `ESC )s18W` install
fields, bucket-5 glyph/raster objects, bridged selector-7 rule object, `0x1ef6a` call
order, dispatch targets `0x1f88e` and `0x1effe`, rule helper `0x1f596`, and composed
output rows. High for parser-driven page-stream composition because fixture
`parser-driven downloaded glyph rule raster stream composes through 0x1ef6a` asserts the
post-font page bytes, handlers `0x10e68`, `0x10e22`, `0x10898`, `0xd04a`, `0x10808`,
`0x1075a`, and `0x11f82`, delayed raster record `80 57 00 02 00 00`, payload offset
`28`, bucket-5 chain, bridged rule list, and the same composed rows. High for the
ROM-effect names and failure behavior of every `0x16fae` validation-table entry,
including the host-fetched invalid-type, first-code overflow, zero/high line-count,
reversed/high range-count, and invalid-class no-install boundaries. Medium for the
complete soft-font grammar because exact HP manual labels for pass-through descriptor
fields and every legal metric combination have not been page-compared.

### Fixtures

- `combined host-fetched font download stream prints installed glyph`
- `combined font download FF publishes installed glyph page record`
- `host-fetched even-span downloaded glyph FF publishes rendered page record`
- `downloaded normal row-0x80 and segmented glyph FF publications render page records`
- `downloaded glyph width-span matrix publishes and renders all main helpers`
- `downloaded glyph wide-remainder matrix publishes and renders compact chunks`
- `downloaded glyph width-byte boundary truncates page-record span`
- `downloaded glyph segmented-wide matrix publishes and renders compact chunks`
- `downloaded segmented-wide row-byte boundary truncates page-record segments`
- `split-plane segmented downloaded glyph FF publication renders page record`
- `published downloaded glyph segmented buckets render across bands`
- `0x1eba4 scheduler band words render published downloaded glyph`
- `host-fetched downloaded glyph composes with rule and raster through 0x1ef6a`
- `parser-driven downloaded glyph rule raster stream composes through 0x1ef6a`
- `host-fetched font control stream feeds descriptor and character payload
  state`
- `ESC )s80W resource stream installs 0x1719c payload through 0x16c14`
- `host-fetched 0x15d0a current-record resource object feeds fixed-record
  render`
- `host-fetched 0x15d0a continuation resource object resumes fixed-record
  render`
- `0x15c4c failed resource resume releases fixed-record object`
- `0x17d7c releases extended fixed-record table with secondary refresh`
- `0x17d7c delegates bit-30 release to offset-table helper`
- `0x16c14 allocation failure releases existing payload through 0x1887a`
- `host-fetched 0x15d0a split-plane continuation resource object resumes
  fixed-record render`
- `ESC )s80W invalid resource type fails validation before allocation`
- `ESC )s80W reversed resource range fails validation before allocation`
- `ESC )s80W additional validation predicate failures skip allocation`
- `ESC )s#W validation failures preserve following printable output`
- `host-fetched type-2 0x1719c payload metrics feed d4ac and d8fc span rows`
- `host-fetched type-1 0x1719c payload metrics feed d4ac and d8fc span rows`
- `host-fetched metric variant changes d4ac gate and d8fc rows`
- `host-fetched clamped metric variant changes d4ac gate and d8fc rows`
- `host-fetched lower-bound metric variant suppresses d4ac and d8fc spans`
- `host-fetched upper-bound metric variant keeps d4ac span but suppresses d8fc`
- `0x16498-backed downloaded character object renders segmented-wide compact
  row`
- `host-fetched linear downloaded character stream renders through 0x168dc`
- `host-fetched downloaded character payload control reaches wide render`
- `host-fetched payload-control downloaded glyph FF publishes page record`
- `host-fetched rows-0x20 short downloaded glyph FF publication renders page
  record`
- `host-fetched rows-0x40 short downloaded glyph FF publication renders page
  record`
- `host-fetched rows-0x82 segmented downloaded glyph FF publication renders page
  record`
- `host-fetched rows-0x102 downloaded glyph FF publication truncates
  page-record rows`
- `host-fetched even-span wide downloaded character renders through 0x1f0d2`
- `host-fetched row-0x80 downloaded character remains short compact`
- `0x16498 replacement allocation failure partial and rejected downloaded character
  exits preserve state`
- `0x16498 no-install exits preserve following printable output`
- `0x16498 status-2 partial installs remain printable`
- `host-fetched segmented downloaded character renders through 0x1f1f0`
- `host-fetched split-plane segmented downloaded character renders through
  0x1f1f0`
- `0x16fae validation table semantic map covers staged and pass-through
  entries`
- `0x16fae table-driven validation predicates populate staged header fields`

### Disassembly Evidence

- `generated/disasm/ic30_ic13_font_control_dispatch_016df6.lst`
- `generated/disasm/ic30_ic13_font_payload_setup_015b80.lst`
- `generated/disasm/ic30_ic13_font_payload_object_path_016040.lst`
- `generated/disasm/ic30_ic13_font_payload_descriptor_helpers_016a10.lst`
- `generated/disasm/ic30_ic13_font_fixed_record_release_017a24.lst`
- `generated/disasm/ic30_ic13_font_resource_object_add_016c14.lst`
- `generated/disasm/ic30_ic13_font_resource_payload_link_01887a.lst`
- `generated/disasm/ic30_ic13_font_resource_release_018b92.lst`
- `generated/disasm/ic30_ic13_font_resource_release_alt_018bf2.lst`
- `generated/disasm/ic30_ic13_font_resource_validate_016fae.lst`
- `generated/disasm/ic30_ic13_font_resource_validate_predicates_017358.lst`
- `generated/disasm/ic30_ic13_font_resource_find_017026.lst`
- `generated/disasm/ic30_ic13_font_resource_payload_initializer_01719c.lst`
- `generated/disasm/ic30_ic13_font_payload_readers_016874.lst`

### Unresolved Middle Edges

- `0x16fae..0x17016`: all 32 validation slots now have ROM-effect names and
  concrete success/failure fixtures. Exact HP manual labels for consumed but
  not staged descriptor fields still need external correlation. The
  host-fetched invalid-type path proves no-install behavior for entry `2`, the
  host-fetched first-code overflow path proves entry `4`, the zero and high
  line/count paths prove entry `5`, the reversed and high range/count paths
  prove entry `6`, and the invalid-class path proves entry `7`. Fixture
  `ESC )s#W validation failures preserve following printable output` proves
  those seven `ESC )s80W` no-install exits plus the short-budget `ESC )s8W`
  entry-5 failure leave the next printable `!` on the unchanged default-font
  page-record path with matching rendered rows. Disassembly of the predicate
  helpers shows these are the complete ROM-internal rejecting families; the
  remaining validation edge is external HP manual naming for
  consumed-but-not-staged fields.
- `0x16498..0x16942`: split-plane segmented-wide, wide/control, even-span wide,
  row-threshold `0x80` short, linear normal, linear segmented, split-plane
  segmented, main width-span, compact-wide remainder, and segmented-wide
  matrix downloaded-character paths are page-visible.
  Fixture `host-fetched row-0x80 downloaded character remains short compact`
  closes the exact `0x80`/`0x81` selector boundary for even-span copied
  glyphs: `0x12f2e` leaves rows `0x80` on selector `0x0003`, while fixture
  `host-fetched segmented downloaded character renders through 0x1f1f0` puts
  rows `0x81` on selector `0x2003`. Fixture `downloaded glyph width-span
  matrix publishes and renders all main helpers` closes parser-produced spans
  `1..16` for the main `0x1f08e` helper table, including odd-span split-plane
  copies and bucket-0 FF publication. Fixture `downloaded glyph wide-remainder
  matrix publishes and renders compact chunks` closes parser-produced spans
  `17..32` for selector `0x1003`, including `0x2f27c` full chunks,
  `0x1f1ac` remainders `1..15`, span-`32` no-remainder rendering, odd-span
  split-plane copies, zero-drain returns, and bucket-0 FF publication. The
  same fixture now probes parser-produced compact-wide spans `33`, `48`,
  `49`, `64`, and `255`: canonical installed records, bucket-0 publication,
  selector `0x1003`, object byte `0x10`, `0x2f27c` full-chunk counts,
  remainder helpers, and zero-drain return boundaries are pinned, while row
  equivalence remains open above span `32`. Fixture `downloaded glyph
  segmented-wide matrix publishes and renders compact chunks` closes
  parser-produced spans `17..32` at rows `0x81` for selector `0x3003`,
  including buckets `0` and `8`, segment-1 row skip `0x80`, A2/A3 source
  offsets, `0x2f27c` full chunks, `0x1f1ac` remainders `1..15`, span-`32`
  no-remainder rendering, zero-drain returns, and bucket-8 FF publication. The
  same fixture now probes segmented-wide spans `33`, `48`, `49`, and `64`
  through the same parser/install/publication/dispatch metadata while leaving
  row equivalence open. Fixture
  `0x16498 replacement allocation failure
  partial and rejected downloaded character exits preserve state` covers old-pointer
  release through `0x17a24`, object allocation failure through
  `0x170c`/`0x9b5e`/`0x1887a`, status-`2` linear/split-plane continuation pointer
  writes, and the descriptor mode-byte-`0` plus high-character/header-type status-`0`
  rejects. Remaining parser-produced comparisons are narrowed by fixture `0x16498
  no-install exits preserve following printable output`, which proves those no-install
  exits leave the next printable on the baseline default-font object and rows. Fixture
  `0x16498 status-2 partial installs remain printable` proves the status-`2` linear and
  split-plane partial-install visibility contract, and now carries those two compact
  objects through trailing-FF `0xff1e` publication and `0x1ed84`/`0x1ef6a`
  published-record rendering. Still-open comparisons are bounded cross-products: row
  counts outside the covered short rows `0x01`, `0x02`, `0x03`, `0x04`, `0x08`,
  `0x10`, `0x20`, `0x40`, `0x41`, `0x7f`, and `0x80` and segmented rows
  `0x81`, `0x82`, `0x83`, `0x84`, `0x85`, `0xc0`, `0xfd`, `0xfe`, and `0xff`,
  visible behavior after printable downloaded spans `0x0100..0x020d` wrap in
  the current one-byte page source span field, visible behavior after
  segmented-wide row words above `0x00ff` wrap in the current one-byte page
  source row field, broader
  publication combinations beyond the documented normal, non-boundary short, rows-`0x20`
  short, rows-`0x40` short, row-`0x80`, row-count-matrix short/segmented, rows-`0x0102`
  low-byte-truncated table-limit boundary, linear-segmented, rows-`0x82` segmented,
  split-plane segmented, segmented-wide, compact-wide matrix,
  segmented-wide matrix, even-span wide, payload-control wide, no-install, and
  status-`2` compact bucket variants, and return-boundary siblings
  outside the covered normal even-span, no-install, status-`2`, linear segmented
  publication, split-plane segmented publication, and segmented-wide publication
  fixtures. The normal even-span fixture
  `parser-driven downloaded glyph rule raster stream composes through 0x1ef6a`
  pins
  `0x15dc6 -> 0x16498 -> 0x15dcc -> 0x12328` with zero remaining budget and next
  handler `0x10e68`; fixture `0x16498 no-install exits preserve following printable
  output` pins six-byte `0x12328` drains before handler `0xd04a`; fixture `0x16498
  status-2 partial installs remain printable` pins linear/split status-`2` zero-drain
  returns before handler `0xd04a`; fixture `downloaded normal row-0x80 and segmented
  glyph FF publications render page records` pins normal, row-`0x80`, and
  linear-segmented zero-drain publication returns before handler `0xd04a`; fixture
  `downloaded glyph row-count matrix publishes and renders additional short/segmented
  counts` pins row-count-matrix short/segmented zero-drain returns before handler
  `0xd04a`; fixture `downloaded glyph wide-remainder matrix publishes and renders
  compact chunks` pins compact-wide zero-drain returns before handler `0xd04a`;
  fixture `downloaded glyph segmented-wide matrix publishes and renders compact
  chunks` pins segmented-wide matrix zero-drain returns before handler `0xd04a`; fixture
  `split-plane segmented downloaded glyph FF publication renders page record` pins the
  split-plane segmented zero-drain return before handler `0xd04a`; fixture `combined
  font download FF publishes installed glyph page record` pins the segmented-wide
  zero-drain publication return before handler `0xd04a`; fixture
  `host-fetched payload-control downloaded glyph FF publishes page record` pins the
  payload-control wide nonzero drain that consumes `&` and leaves FF for handler
  `0xf0f0`. Other uncomposed full-success return siblings remain open cross-products.
  Accepted
  descriptor-record mode bytes are closed for the covered helper table by fixture
  `0x16b1a descriptor width helper emits only mode 1/2`: `0x16b36..0x16b6a` writes
  mode `1`/`2` from span parity, and `0x16b26..0x16b34` rejects invalid widths without
  writing scratch. The mode-byte-`0` and
  high-character header-type status-`0` exits are already documented no-install
  boundaries: fixture `0x16498 replacement allocation failure partial and rejected
  downloaded character exits preserve state` proves no table/header write at the object
  boundary, and fixture `0x16498 no-install exits preserve following printable output`
  proves the next printable and FF publication use the unchanged default-font page path.
- downloaded-glyph plus rule/raster producer schedule: fixture
  `parser-driven downloaded glyph rule raster stream composes through
  0x1ef6a` closes the page-stream boundary from parser-produced `0x10898` rule
  insertion, downloaded-current printable queue through `0x12f2e`, and delayed
  `0x105d0` / `0x13070` raster transfer into one bucket-5 render entry.
  Remaining risk is the earlier font-install-to-page handoff: the same fetched
  byte stream is split at byte `24`; the supplied memory image is now named as
  the exact `bytearray(downloaded_wide_even_install["header"])` emitted by the
  host-fetched `0x16c14` / `0x16498` install fixture, but it is still supplied
  to the page-stream runner instead of captured from one live CPU memory run.
- `0xff1e..0x1ed84`: the combined downloaded-glyph stream now publishes both segmented
  buckets; the normal, non-boundary short, row-threshold `0x80`, rows-`0x20` short,
  rows-`0x40` short, linear-segmented, rows-`0x82` segmented, split-plane segmented,
  main width-span, compact-wide remainder, segmented-wide matrix, even-span wide,
  payload-control odd-span wide, and rows-`0x0102` low-byte-truncated short siblings now
  publish through the same boundary. Fixture
  `downloaded glyph width-span matrix publishes and renders all main helpers` publishes
  bucket `0` for spans `1..16`, renders through `0x1ed84`/`0x1ef6a`, and verifies helper
  targets `0x1fa5c..0x26910` against installed bitmap rows. Fixture `downloaded glyph
  wide-remainder matrix publishes and renders compact chunks` publishes bucket `0` for
  spans `17..32`, dispatches selector `0x1003` object byte `0x10` through
  `0x1effe`/`0x1f0d2`, verifies full chunks through `0x2f27c`, remainders `1..15`
  through `0x1f1ac[remainder]`, and the no-remainder span-`32` sibling against
  installed bitmap rows; the same fixture publishes high-span probes `33`, `48`, `49`,
  `64`, and `255` with matching row comparisons. Fixture `downloaded glyph
  segmented-wide matrix publishes and renders compact chunks` publishes buckets `0` and
  `8` for spans `17..32` at rows
  `0x81`, dispatches selector `0x3003` object byte `0x30` through `0x1effe`/`0x1f264`,
  verifies full chunks through `0x2f27c`, remainders `1..15` through
  `0x1f1ac[remainder]`, and the no-remainder span-`32` segment-1 sibling against
  installed bitmap rows; the same fixture publishes high-span probes `33`, `48`, `49`,
  and `64` with matching segment-1 row comparisons. Fixture `host-fetched
  nonboundary short downloaded glyph FF publication renders page record` renders rows
  `0x10` on selector `0x0003` through `0x1ed84`/`0x1ef6a` and compact target
  `0x1effe`/`0x1fe76`, preserving digest
  `28220dd2ecafaf07afc095fa0cc3cb6ed070984b3e3da6762b49ebda582d492b`. Fixture
  `downloaded normal row-0x80 and segmented glyph FF publications render page records`
  renders the normal bucket-1 record through `0x1ed84`/`0x1ef6a` and compact target
  `0x1effe`/`0x1fe76`, renders the row-`0x80` bucket-1 record through the same
  target/helper while preserving selector `0x0003`, and renders the linear-segmented
  bucket-9 record through `0x1ed84`/`0x1ef6a` and compact target `0x1effe`/`0x1f1f0`.
  Fixture `split-plane segmented downloaded glyph FF publication renders page record`
  publishes the odd-span bucket-9 root `00 00 00 00 20 03 00 01 28 01 66 01`, preserves
  bucket-array entries `1` and `9`, and renders through `0x1ed84`/`0x1ef6a` and compact
  target `0x1effe`/`0x1f1f0`. Fixture `host-fetched rows-0x82 segmented downloaded glyph
  FF publication renders page record` publishes bucket-array entries `1` and `9` for
  `ESC )s260W`, preserves record `00 00 00 00 0c 01 00 82 00 10 00 00`, renders bucket
  word `9`, and emits two segment-1 rows through compact target `0x1effe`/`0x1f1f0`.
  Fixture `host-fetched rows-0x102 downloaded glyph FF publication truncates page-record
  rows` publishes bucket-array entry `1` for `ESC )s516W`, preserves installed record
  `00 00 00 00 0c 01 01 02 00 10 00 00`, but shows the printable source row byte as
  `0x02`, so `0x12f2e` writes selector `0x0003` object `00 00 00 00 00 03 00 01 33 66
  01`; `0x1f414` then splits rows `0x0102` into `58` current rows and `200` fallback
  rows, exceeding the `0x1fe76` row-copy table's valid maximum index `128` at fallback
  target `0x329ad3c0`. Fixture `host-fetched rows-0x20 short downloaded glyph FF
  publication renders page record` publishes bucket-array entry `1` for `ESC )s64W`,
  preserves record `00 00 00 00 0c 01 00 20 00 10 00 00`, renders bucket word `1`, and
  emits `38` visible rows through compact target `0x1effe`/`0x1fe76`. Fixture
  `host-fetched rows-0x40 short downloaded glyph FF publication renders page record`
  publishes bucket-array entry `1` for `ESC )s128W`, preserves record `00 00 00 00 0c 01
  00 40 00 10 00 00`, renders bucket word `1`, and emits `64` current-band rows through
  compact target `0x1effe`/`0x1fe76`. Fixture `downloaded glyph row-count matrix
  publishes and renders additional short/segmented counts` adds rows `0x01`, `0x02`,
  `0x04`, `0x08`, `0x41`, `0x7f`, `0x83`, `0x84`, `0x85`, `0xc0`, `0xfd`, `0xfe`, and
  `0xff` through the same printable+FF, `0xff1e`, and `0x1ed84`/`0x1ef6a` boundary, with
  short selector `0x0003` for the first six and segmented selector `0x2003` for the last
  seven. It also pins the shared full-success return boundary for all thirteen rows:
  `0x15dc6 -> 0x16498 -> 0x15dcc -> 0x12328`, copy status `1`, `0x783140 = 0`, no
  drained bytes, and next handler `0xd04a`. Fixture `host-fetched even-span downloaded
  glyph FF publishes rendered page record` renders the copied bucket-1 record through
  `0x1ed84`/`0x1ef6a` and compact target `0x1effe`/`0x1f0d2`. Fixture `host-fetched
  payload-control downloaded glyph FF publishes page record` separates two effects for
  the odd-span wide/payload-control sibling. Canonical state: `0x168dc` normalizes one
  `1a 58` escape, and `0x16498` installs table entry `0x00e2` with mode-byte-`2` record
  `00 00 00 00 0c 02 00 01 00 88 00 00`. Parser/firmware bookkeeping: copy leaves
  `0x783140 = 1`, so the return boundary `0x15dc6 -> 0x16498 -> 0x15dcc -> 0x12328`
  drains following byte `0x26` (`&`) and the post-return parser sees only FF at handler
  `0xf0f0`. Derived page-output state: the modeled page-record publication for that
  installed object publishes bucket `1`, and `0x1ed84`/`0x1ef6a` dispatches compact
  target `0x1effe`/`0x1f0d2`; this does not prove that `&` survives as printable in the
  same live byte stream. Fixture `published downloaded glyph segmented buckets render
  across bands` renders published bucket words `1` and `9` from the copied record.
  Fixture `0x1eba4 scheduler band words render published downloaded glyph` proves
  `0xff1e`/`0x1ed84` seed render work `+0x10/+0x16` from cleared source `+0x18 = 0`,
  then `0x1eba4` advances through band words `0..9` until the published bucket-9 row is
  visible. The earlier first-band seed edge is now closed for this published record.
- `0x15c4c`: the even-span and split-plane fixed-record resume routes are
  page-visible, and the status-0 fixed-record release exit is fixture-backed.
  The bit-30 offset-table release delegate is fixture-backed through
  `0x17a24`. Fixed-record secondary-context refresh and fixed-record
  extended-table release are fixture-backed together. Current-record
  allocation-failure release through `0x1887a` is fixture-backed for the
  bit-30-clear extended fixed-record case; the remaining release risk is
  broader variant coverage, not this control-flow edge.
- The span-metric bridge in `notes/font-context-metrics.md` now covers
  host-fetched type-0, type-1, and type-2 downloaded payloads for both span
  consumers, the shared consumer branch family, and a seven-case
  parser-produced legal metric-value matrix that flips tight `d4ac`
  page-extent gates, exercises rounded-metric clamping into `+0x2c/+0x2d`,
  preserves zero rounded/offset fields through visible `d4ac` and `d8fc` span
  objects, preserves negative offset byte `0xfe` as copied word `0xfffe`,
  moves `d8fc` visible rows, updates `d8fc` without a span object, suppresses
  both span consumers through copied lower-bound fields, and preserves `d4ac`
  span output while `d8fc` exits `beyond-page-extent`. Fixture
  `legal descriptor metric boundary values drive d4ac and d8fc consumers`
  adds `d8fc` lower-bound equality, exact page-extent equality, max positive
  offset byte `0x7f`, max negative offset byte `0xff`, normal rounded input
  `0x0013` storing `+0x2c = 0x0014`, and the rounded `0x1500`,
  `0x1508`, and `0x15ff` transforms to copied `+0x2c = 0x0060` that send
  `d4ac` to `beyond-page-extent`. Those high-byte rounded cases prove the
  descriptor transform discards the low byte; `d4ac` exits `beyond-page-extent`,
  while `d8fc` consumes `+0x16/+0x18/+0x1a = 0x0004/0x0013/0x0001` and renders digest
  `f830d30ea60a61f0b74a489c4b7df1bb25dc464b6765d170c19e7278a0267eab`.
  Fixture
  `legal descriptor metric range endpoints drive d4ac and d8fc consumers`
  proves first-code zero and first-code `range - 1` are legal parser-produced
  endpoints for the `0x17430` formula, copying derived/cache `+0x18` values
  `0x0017` and `0x0000` while both legal selected forms still feed the
  documented visible span paths.
  Fixture
  `legal descriptor metric low-nibble rounding drives d4ac and d8fc consumers`
  adds rounded inputs `0x0001`, `0x0003`, `0x0004`, `0x0005`, and `0x000f`;
  they copy to `+0x2c = 0x0000/0x0004/0x0004/0x0004/0x0010`, preserving
  `d4ac` span rows and `d8fc` high-y `20` / digest
  `f830d30ea60a61f0b74a489c4b7df1bb25dc464b6765d170c19e7278a0267eab`.
  Fixture
  `legal descriptor metric byte-boundary rounding drives d4ac and d8fc
  consumers` adds rounded inputs `0x00fd`, `0x00fe`, `0x0101`, and
  `0x0102`, copying `+0x2c = 0x00fc/0x0100/0x0100/0x0104`; the capped
  range sibling copies `0x0102` back to `0x0100` when `+0x14 = 0x0040`.
  It proves `d4ac` flips from compact-only digest
  `86e3bb70d51c66ac608345dc3bff6476447ebc500d7c271808a53d6638d59ad6`
  at copied `0x00fc` to the standard span digest
  `67554ea70d7cfd9b11c0777e3cf65d51600a44301a4f93bd4d9b0c0fbc23c00e`
  once copied `+0x2c` crosses to `0x0100`.
  Fixture `legal descriptor metric mixed values drive d4ac and d8fc consumers` adds
  middle-range combined producer cases: `0x0008/0x0030/0x002a/0x02` copies
  `+0x18/+0x1a/+0x2c = 0x0027/0x0002/0x002c`, suppresses `d4ac`, and renders
  `d8fc`; rounded `0x00ff` caps copied `+0x2c` to `0x00c0`; offset byte `0x80`
  sign-extends to `+0x1a = 0xff80`; and first-code `0x002f` derives `+0x18 = 0`.
  Fixture `legal descriptor metric tight range values drive d4ac and d8fc consumers`
  adds the smallest legal range/count cross-products: range one copies
  `+0x14/+0x16/+0x18 = 0x0001/0x0000/0x0000`, range two copies
  `0x0002/0x0001/0x0000`, and both still feed visible consumer rows while
  varying rounded outputs and max signed offsets.
  Fixture `legal descriptor metric extent fenceposts drive d4ac and d8fc
  consumers` proves the `d8fc` page-extent fence after the derived-height
  formula: range words `0x002f`, `0x0031`, and `0x0032` copy derived heights
  `42`, `44`, and `45`; height `42` with offset `0` renders high-y `21`,
  while heights `44` and `45` exit `beyond-page-extent` even with offsets
  `1` and `2`.
  Fixture
  `descriptor metric fields match across inline and resource contexts` now
  pins the legal inline/unflagged and resource/flagged producer forms plus the
  two invalid swapped forms. The producer formulas are documented from
  `0x17430`, `0x1757a`, `0x1762a`, and `0x1719c`; additional legal metric
  values are cross-products of those formulas and the covered matrix,
  boundary, range-endpoint, extent-fence, mixed-value, tight-range,
  low-nibble, and byte-boundary fixtures. Remaining descriptor work is broader
  selected-font state combinations plus external naming for
  consumed-but-not-staged validation fields.

## Macro Definition And Data-Chain Replay

Status: anchored as one command-family and end-to-end replay cluster.
The low-level handler ledger is preserved in
`notes/reverse-engineering-ledger.md`; this section composes the macro
ID/control handlers, alternate parser table, macro record pool, data-chain
frame builder, `0xa904` replay, parser dispatch, page-record queueing, and
render-entry effects into one semantic model.

Concept: `ESC &f#Y` selects a current macro id, and `ESC &f#X` interprets
the selector against a 32-record macro pool. Definition mode stores host
bytes instead of dispatching most controls. Execute and call selectors
convert a stored payload into a data-chain frame consumed by `0xa904`, so
macro bytes re-enter the same parser/page-record path as normal host bytes.

### Field Groups

- Canonical macro selection:
  - `0x783164`: current macro id word. Handler `0xe112` rewinds the
    six-byte parsed record, takes the absolute signed word at `record+2`,
    and stores it here.
  - parsed records for `ESC &f-123y0x1X`:
    `81 79 ff 85 00 00`, `80 78 00 00 00 00`, and
    `80 58 00 01 00 00`.
  Evidence: handler `0xe112`, ROM field `0x783164`, parser-table report
  `generated/analysis/ic30_ic13_parser_dispatch_tables.md`, and fixture
  `0xe112 stores absolute parsed macro id`.
- Canonical macro records:
  - 32 records rooted at `0x782a98`, each 12 bytes.
  - current macro record pointer `0x782d7a`.
  - record `+0x00`: payload/chunk pointer, observed by execute/call
    nonempty tests and stop-definition cleanup.
  - record `+0x04`: raw stored byte count. It includes payload bytes plus
    four bytes of header overhead for each allocated 0x100-byte chunk.
  - record `+0x08`: stored macro id written from `0x783164` on selector
    `0` start.
  - record `+0x0a`: permanence byte, cleared by selector `9` and set by
    selector `10`.
  - `0xe0a4(id)` scans all 32 records in order, comparing the requested
    id against record `+0x08` but accepting a match only when record
    `+0x00` is nonzero. A matching nonempty record writes `0x782d7a` to
    that slot and returns `D7 = 1`.
  - during the same scan, the first record with zero `+0x00` is retained
    as the free slot even if its stale `+0x08` id is nonzero. If no
    nonempty match is found, that first free slot receives the requested
    id at `+0x08`, `0x782d7a` points to it, and `D7 = 0`.
  - if every record has nonzero `+0x00` and none matches, `0xe0a4`
    writes `0x782d7a = 0` and returns `D7 = 2`.
  - `0xe0a4` does not inspect permanence byte `+0x0a`; temporary and
    permanent behavior is handled by selectors `7`, `9`, and `10`.
  Evidence: `notes/pcl-parser-firmware.md` macro selector table;
  disassembly `0xe0a4..0xe110`; fixtures
  `0xe0a4 macro record lookup uses head presence and first free slot`,
  start/stop, permanence, delete-temporary, delete-current, and
  delete-all.
- Canonical macro payload chunks:
  - `0xe002(byte)` appends only when active frame byte `+9` is zero and
    macro error byte `0x782c19` is clear.
  - current append chunk pointer `0x782c1a` names the active 0x100-byte
    chunk for the current record.
  - when `(record+0x04) & 0xff == 0`, `0xe002` allocates one zero-filled
    0x100-byte chunk through `0x170c(1, 1, 0x100)`. The new chunk becomes
    record `+0x00` if this is the first chunk, otherwise it is linked
    through the previous chunk's first longword.
  - after allocating a chunk, `0xe002` adds four to record `+0x04` for
    the chunk link/header and writes the byte at chunk `+0x04`.
  - within an existing chunk, `0xe002` writes at
    `chunk + 4 + ((record+0x04) & 0xff) - 4`, then increments
    record `+0x04`.
  - each 0x100-byte chunk therefore carries 252 payload bytes. The next
    append after raw count `0x100` allocates and links a second chunk,
    writes the byte at the new chunk's payload offset zero, and leaves
    raw count `0x105`.
  - selector `1` stop derives payload count as
    `raw_count - (((raw_count + 0xff) >> 8) * 4)`. A derived count of
    one clears the record; a derived count of three also clears if the
    first bytes are `1b 26 66` (`ESC &f`). Other payloads are kept.
  - if chunk allocation fails, `0xe002` sets `0x782c19`, reports the
    allocation failure through `0x9b5e(0x780e2e, 4)`, and clears the
    current record through `0xdfba`.
  Evidence: disassembly `0xe002..0xe0a2` and `0xde0c..0xde7a`; fixture
  `0xe002 appends macro definition bytes into 0x100 chunks`.
- Canonical data-chain replay frame:
  - current frame pointer `0x782d76`.
  - execute selector `2` calls `0xe418` from `0xde96`; call selector `3`
    calls it from `0xdebc`.
  - `0xe418` advances `0x782d76` by `0x0e` and writes the new frame.
  - frame `+0x00`: payload/chunk pointer copied from macro record
    `+0x00`.
  - frame `+0x04`: byte count copied from macro record `+0x04`.
  - frame byte `+8 == 4`.
  - frame byte `+9 == 2` for execute, `+9 == 3` for call.
  - frame `+0x0a`: environment snapshot pointer returned by `0xe8f0`.
    Execute snapshots use source `0x783192` and target `0x78319a`; call
    snapshots use source `0x782d9e` and target `0x78319a`.
  - executable fixtures pin payload `21 0d` and mixed-control payload
    `1b 26 6b 31 47 21 0d 21`.
  Evidence: `generated/analysis/ic30_ic13_parser_xrefs.md` shows
  `0xe418` called only from `0xde96` and `0xdebc`; disassembly
  `generated/disasm/ic30_ic13_macro_record_chain_helpers_00dfba.lst`
  covers `0xe418..0xe4f2`; fixtures
  `0xdd08 execute and call push macro data-chain frames` and
  `0xe418 frame metadata distinguishes execute and call context`.
- Canonical non-replay data-chain frame:
  - `0xe4f4` is called by page-root finalization `0xff8e` after
    `0xe0a4(0x782a94)` restores a saved command/data key and the selected
    record has nonzero `+0x00`.
  - `0xe4f4` pushes a 10-byte context entry from `0x782ee6` and
    `0x782ef6`, snapshots flat range `0x782d3a..0x78319a` to
    `0x7834c2` through `0xe996`, and saves cursor longword
    `0x782c8a` into `0x782c92`.
  - it restores baseline range `0x782ee2..0x78319a` from `0x7831a2`
    through `0xe972`, calls layout refresh helper `0xe5e2`, then writes a
    frame at `0x782d4c` and stores `0x782d76 = 0x782d4c`.
  - frame `+0x00/+0x04` copy selected macro record `+0x00/+0x04`,
    byte `+8 = 4`, byte `+9 = 4`, and longword `+0x0a = 0`.
  - if frame `+0x04` is positive, `0xe4f4` sets host gate bit 1 in
    `0x780e66`.
  Evidence: disassembly `0xe4f4..0xe5e0`; fixture
  `0xe4f4/0xe22c produce and end data-chain frames`.
- Canonical non-replay layout refresh:
  - `0xe5e2` is the shared page-layout refresh used before `0xe4f4`
    writes the frame at `0x782d4c`.
  - it writes top offset `0x782dce = 0x96 - 0x782dbe`, unless page
    extent `0x782dba <= 0x96`; the short-page branch writes
    `0x782dce = -0x782dbe`.
  - parser scratch/cache word `0x782dd0` is cleared before the helper
    calls and is not canonical layout state.
  - `0xea16` refreshes default text-bottom cache `0x782dd2`;
    `0xe9ba` clears left margin `0x782dd6`, copies page width
    `0x782db8` into right margin `0x782dda`, and clears
    `0x782ddc`.
  - `0xf8fc` refreshes pending vertical cursor from the new top offset
    and current VMI when the pending-text path needs it.
  - `0xfe54` writes VFC line-count caches `0x782edf`, `0x782ee0`, and
    `0x782ede`; `0x12b96` rebuilds default table
    `0x782dde..0x782edd`, copies `0x782dd2 -> 0x782dc2`, and clears
    modified-layout byte `0x782ee1`.
  - `0xe65c(1)` then consumes static context record `0x782c64` through
    the already modeled static font-context refresh path.
  Evidence: disassembly
  `generated/disasm/ic30_ic13_macro_record_chain_helpers_00dfba.lst`
  at `0xe5e2..0xe65a`, shared helper disassembly
  `generated/disasm/ic30_ic13_page_size_handler_00fc74.lst` at
  `0xfe54..0xfed2`,
  `generated/disasm/ic30_ic13_vertical_forms_control_01280a.lst` at
  `0x12b96..0x12cfc`, and fixture
  `0xe5e2 refreshes page layout, default VFC table, and static font
  context`.
- Canonical call context stack:
  - stack pointer `0x782c6e` is initialized to `0x782c1e` by `0xe146`.
  - `0xe146` clears eight 10-byte records at `0x782c1e..0x782c6d`.
  - call mode copies longwords from `0x782ee6` and `0x782ef6` into entry
    `+0x00` and `+0x04`, clears entry bytes `+0x08` and `+0x09`, then
    advances `0x782c6e` by `0x0a`.
  - execute mode does not push this context entry.
  - non-replay frame producer `0xe4f4` uses the same push shape.
  - no guard is visible in `0xe418`, `0xe4f4`, or `0xe65c(0)`: after
    eight pushes the next entry address is the pointer-storage field
    `0x782c6e`, and an empty `0xe65c(0)` pop would read from `0x782c14`.
  - this is separate from the PCL cursor-position stack at
    `0x782c96..0x782d36`, which has explicit push/pop bounds in
    `0xf75e`.
  Evidence: disassembly `0xe146..0xe1be`, `0xe4b2..0xe4e6`,
  `0xe4fc..0xe51e`, and `0xe66a..0xe676`; fixtures
  `0xe418 frame metadata distinguishes execute and call context` and
  `0xe146/e418/e4f4/e65c macro context stack has eight records and no
  guard`.
- Canonical environment snapshots:
  - `0xe8f0(start, end)` stores an inclusive longword range into a
    heap-backed linked chain.
  - each chain chunk is 0x100 bytes: a longword next pointer followed by
    63 longwords of payload.
  - `0xe8a2(dest_start, dest_end, chain)` restores an inclusive longword
    range from the chain and expects the chain to be exhausted when the
    range is filled; otherwise it reports error `0xe3` through `0x1284`.
  - `0xe972(dest_start, dest_end, source)` copies a flat inclusive
    longword range from source to destination.
  - `0xe996(source_start, source_end, dest)` copies a flat inclusive
    longword range from source to destination in the opposite call shape.
  Evidence: disassembly `0xe8a2..0xe9b8`; fixture
  `macro snapshot helpers copy linked and flat environment ranges`.
- Startup-derived heap inputs:
  - startup helper `0x0b18` stores heap start `0x783f4a` in `0x780efa`
    and stores available heap bytes in `0x780efe`.
  - with reset defaults `0x780e5a = 0x20` and `0x780e60 = 6`, `0x0b18`
    computes resource-window base `0x7e8000`, resource-window size
    `0x17ffe`, and available heap bytes `0x640b6`.
  - reset path `0x0370` calls allocator initializer `0x164a` before the
    later setup calls at `0x2feb6`, `0x3178`, and `0x31d6`.
  Evidence: disassembly `0x0320..0x0376`, `0x0b18..0x0b70`, and fixture
  `0x164a initializes heap allocator bitmap and payload base`.
- Canonical heap objects and chains:
  - allocator entries `0x170c` and `0x1710` both manage 64-byte heap
    allocation units. `0x170c` scans from the low side; `0x1710` scans
    from the high side.
  - alignment word `0x40` allocates the requested count as 64-byte units.
    Alignment word `0x100` multiplies the requested count by four units,
    which is why macro payload and snapshot chunks are 0x100 bytes.
  - a zero requested count is normalized to one object. A nonzero second
    argument enables zero-fill through `0x1886`, which clears 16 longwords
    per allocated 64-byte unit.
  - `0x18b4(ptr, count, alignment)` frees a contiguous run when count is
    nonzero. When count is zero, it frees one object and follows the
    first longword of the freed object as a next pointer until zero.
  - macro clear `0xdfba` and frame-end cleanup `0xe22c` use
    `0x18b4(ptr, 0, 0x100)` to free linked 0x100-byte chains. Font payload
    cleanup at `0x1659c..0x165a4` uses `0x18b4(ptr, count, 0x40)` for a
    contiguous run.
  Evidence: disassembly `0x170c..0x18b4`, macro callers
  `0xdfe6..0xdff0` and `0xe90c..0xe944`, font caller
  `0x16564..0x165a4`, and fixture
  `0x170c/0x1710 allocate and 0x18b4 frees heap units`.
- Derived/cache heap allocation state:
  - initializer `0x164a` fills any prefix below `0x784906` with `0xff`;
    default startup reserves `0x783f4a..0x784905`, a `0x09bc` byte range.
  - `0x164a` rounds the free allocation bitmap to an even byte count,
    reducing the 64-byte unit count until the bitmap fits in the low
    remainder space.
  - default startup writes free-unit count `0x18cf` to `0x780e86`, bitmap
    base pointer `0x784906` to `0x783972`, scan end `0x784c1f` to
    `0x783976`, low scan limit `0x784c15` to `0x78397a`, low and high
    scan cursors to `0x78397e` / `0x783982`, tracked bitmap byte count
    `0x031a` to `0x783986`, and payload base pointer `0x784c40` to
    `0x783988`.
  - the default bitmap write has `0x033a` bytes: the prefix is free
    zero bits and the tail is occupied `0xff` padding; a compact
    `heap_start=0x784906`, `available=0x1000` fixture produces free-unit
    count `0x003f`, tracked bitmap bytes `0x0008`, total bitmap write
    `0x0040`, and payload base `0x784946`.
  Evidence: `generated/disasm/ic30_ic13_heap_allocator_init_00164a.lst`
  covers `0x164a..0x170a`; fixture
  `0x164a initializes heap allocator bitmap and payload base`.
- Canonical frame-end paths:
  - `0xe22c` reads the active frame at `0x782d76` and dispatches by frame
    byte `+9`.
  - execute frame `+9 == 2` restores chain `+0x0a` into
    `0x783192..0x78319a`, frees the chain with `0x18b4`, clears frame
    `+0x0a`, rewinds `0x782d76` by `0x0e`, clears host gate bit 1 if the
    previous frame has no byte count, then calls `0x1240a`.
  - call frame `+9 == 3` first snapshots current page/font selector
    fields, restores chain `+0x0a` into `0x782d9e..0x78319a`, frees it,
    may copy cursor words through `0x783184`, pops one 10-byte context
    entry through `0xe65c(0)`, rewinds `0x782d76`, clears host gate bit 1
    when appropriate, then calls `0x1240a`.
  - non-execute/non-call frames use `0xe972` to copy 281 flat longwords
    from source `0x7834c2` into `0x782d3a..0x78319a`. They do not rewind
    `0x782d76`; they leave the same frame current, clear host gate bit 1
    when frame `+0x04` is zero, copy cursor longword `0x782c92` into
    `0x782c8a`, call `0xe65c(0)`, set `0x782a92 = 0x63`, then call
    `0x1240a` and final log helper `0x9ec0(0)`.
  Evidence: disassembly `0xe22c..0xe408`; fixture
  `0xe22c restores macro frames and consumes call context`.
- Canonical font context refresh:
  - `0xe65c(0)` pops one 10-byte call context entry by rewinding
    `0x782c6e` by `0x0a`, then uses entry bytes `+0x08` and `+0x09` as
    primary and secondary font-refresh flags.
  - a primary refresh flag calls `0x13eb8(0)`, copies active word
    `0x783144` into remembered word `0x782f08`, and sets dirty flag
    `0x782f2d` only when selected slot byte `0x782f06 == 0`.
  - a secondary refresh flag calls `0x13eb8(1)`, copies active word
    `0x783146` into remembered word `0x782f0a`, and sets `0x782f2d` only
    when `0x782f06 == 1`.
  - after flag handling, `0xe65c` clears the consumed entry or static
    record longwords and flag bytes, calls `0xc428(0x782f06)`, then exits
    through `0x1b04c` and clears `0x782f2d`.
  - if `0xc428` returns zero, the fallback path writes current context
    longword `0x782c80` into selected context record
    `0x782ee6 + 0x10 * 0x782f06`, writes current word `0x782c84` into
    selected active and remembered words, stores `0x7828de = 0x782f06`,
    stores `0x1b4c0(0x782c80)` into `0x7828a8`, calls `0x144d2` and
    `0x14c64`, sets `0x782f2d`, and probes `0xc428` again before the
    shared `0x1b04c` exit.
  - the composed bridge from `0xe65c` refresh slots to visible font state
    is pinned: primary refresh slot `0` follows
    `0x13eb8 -> 0x144d2 -> 0x14c64` into map `0x782f32`; secondary
    refresh slot `1` follows the same path into map `0x783032`; the
    final `0xc428(0x782f06)` installs the selected current-font context
    record into a page-root font slot.
  - `0xe65c(1)` uses static record `0x782c64`. Static bytes `+0x08` and
    `+0x09` directly force primary/secondary refresh; otherwise helper
    `0xe860(slot)` returns a class/orientation byte from the selected
    current-font context record, and mismatch with `0x782da3` forces the
    corresponding refresh flag.
  - `0xe860(slot)` selects `0x782ee6 + 0x10 * slot`; if context byte
    `+0x04` is zero it returns the inline/downloaded class selector at
    pointed record byte `+0x16`, otherwise it returns the bit-30
    offset-table/built-in class selector at pointed record byte `+0x20`.
  Evidence: `generated/disasm/ic30_ic13_macro_environment_snapshot_helpers_00e65c.lst`
  covers `0xe65c..0xe898`; fixture
  `0xe65c refreshes macro font context entries`; fixture
  `0xe860 reads inline +0x16 and offset-table +0x20 class bytes`; fixture
  `0xe65c refresh composes with font context bridge`; tracked bridge note
  `notes/font-context-metrics.md`.
- Parser scratch:
  - normal macro parser table mode 17 entries at `0x11262..0x11286`
    route `y/Y` to `0xe112` and `x/X` to `0xdd08`.
  - alternate/data parser table `0x116f6` keeps `x/X -> 0xdd08` while
    disabling normal macro-id parsing during definition payload storage.
  - definition-mode flags `0x782c18` and `0x782c19` gate start/stop
    behavior and auto-prefix cleanup.
  Evidence: `generated/analysis/ic30_ic13_tokenizer_macro_callers.md`;
  fixture `0x116f6 alternate parser routes macro stop but suppresses
  payload controls`.
- Firmware bookkeeping:
  - selector `4`/`5` update overlay state `0x782a92`; selector `4` also
    copies current id into `0x782a94` when the record exists.
  - `0xff1e` consumes overlay state when `0x782a92 == 1` and current-root
    flag bit `+0x14.0` is clear: it calls `0xe0a4(0x782a94)`, sets
    `0x782a92 = 2`, calls `0xe4f4`, re-enters parser loop `0x11774`, and
    ensures a page root through `0x10084` before normal publication.
  - active data-chain guard in `0xdd08` suppresses non-replay controls when
    frame byte `+9` is nonzero, while still allowing selectors `2` and `3`.
  - `0xe418` sets the host gate bit when the frame byte count is nonzero;
    `0xa904` later calls `0xe22c` at data-chain end before resuming an
    outer byte source.
  - if `0xe8f0` fails to allocate an environment snapshot, `0xe418`
    backs out to the previous frame and clears host gate bit 1 when the
    previous frame has no byte count.
  - frame-end paths free snapshot chains in 0x100-byte units through
    `0x18b4`, and `0xe8f0` reports allocation failure through
    `0x9b5e(0x780e2e, 4)`.
  - heap allocator bookkeeping uses bitmap-base pointer variable
    `0x783972`, payload-base pointer variable `0x783988`, free-unit count
    `0x780e86`, bitmap end/limit fields `0x783976` / `0x78397a`,
    tracked bitmap-byte count `0x783986`, and scan cursors
    `0x78397e` / `0x783982`; those fields are allocator-private caches,
    not PCL-visible state.
  Evidence: disassembly `0xdd4c..0xdd78`, `0xdee4..0xdefa`,
  `0xe418..0xe4e6`, and
  `generated/analysis/ic30_ic13_page_root_finalization.md` rows
  `0xff40..0xff9a`; host-byte section
  `Host Byte Fetch And Data-Chain Input`; fixture `macro overlay
  finalization replays before page publication`.
- Derived/cache:
  - execute and call replay of stored `!\r` produce the same compact text
    page-record object and rendered rows.
  - mixed-control replay of stored `ESC &k1G!\r!` sets line termination
    mode through `0xedf8`, routes printable bytes through `0xd04a`, CR
    through `0xf02c`, and renders rows matching the direct host stream.
  - macro replay rows cross the `0x1edc6` bucket/context bridge and
    `0x1ed84`/`0x1ef6a` render-entry path.
  - overlay publication of stored `!\r` uses a non-replay frame
    `+8 = 4`, `+9 = 4`, replays through `0xd04a` and `0xf02c`, queues the
    text object into an existing page record that already contains a
    selector-7 rectangle rule, and publishes/render-composes both layers
    through `0xff1e` and `0x1ed84`/`0x1ef6a`.
  - repeated overlay publication keeps the selector-4 overlay state live
    across two modeled `0xff1e` page boundaries. Both publications resolve
    record id `123` through `0xe0a4`, build the same non-replay `0xe4f4`
    frame for payload `!\r`, replay through `0xd04a`/`0xf02c`, and compose
    the replayed overlay text with each page's distinct selector-7 rule.
  - overlay skip gates preserve the base page publication when selector `5`
    has disabled overlay mode, when overlay id `123` has no nonempty macro
    record, or when page-root retry flag bit `+0x14.0` is set. In those cases
    `0xff1e` still publishes and renders the base printable/rule page record,
    but no `0xe4f4` frame or replayed `!\r` text is added.
  - mixed-control overlay publication uses the same selector-4 state, now
    with overlay id `125` and payload `ESC &k1G!\r!`. `0xff1e` resolves the
    record through `0xe0a4`, `0xe4f4` builds a non-replay frame
    `+8 = 4` / `+9 = 4`, parser loop `0x11774` routes the payload through
    `0xedf8`, `0xd04a`, `0xf02c`, and `0xd04a`, and the replay queues two
    compact text entries into the same published page record as a selector-7
    rectangle rule.
  - raster overlay publication uses overlay id `126` and payload
    `! ESC *t300R ESC *r0A ESC *b2W c3 3c`. The same `0xe0a4` / `0xe4f4`
    non-replay frame path feeds parser loop `0x11774`, queues one compact
    text object plus one delayed `0x105d0` mode-0 raster object, preserves
    the existing selector-7 rule, and publishes/renders all three layers
    through `0xff1e` and `0x1ed84`/`0x1ef6a`.
  Evidence: fixtures `macro execute data-chain parser trace feeds
  page-record stream`, `macro call data-chain parser trace feeds
  page-record stream`, `host-fetched macro replay payloads feed 0x1ed84
  and 0x1ef6a`, and `macro overlay finalization replays before page
  publication`, plus `macro overlay replays across repeated page
  publications`, `macro overlay skip gates preserve base page publication`,
  `macro overlay mixed-control payload publishes with page rule`, and
  `macro overlay raster payload publishes with page rule`.
- Unknown:
  - startup option source for the optional `0x80` addition to
    `0x780e5a` still needs board/config correlation, but the downstream
    `0x0b18` heap-limit math and `0x164a` allocator initialization are
    pinned for the default path.
  - no remaining macro execute/call replay, font-context, first
    overlay-publication, repeated enabled-overlay publication, mixed-control
    overlay payload, raster overlay payload, or overlay skip-gate middle edge
    in this checkpoint. The next high-value macro edges are broader overlay
    payload variants and
    final device-output validation. Descriptor metric validation is tracked
    separately as external/manual naming for consumed-but-not-staged fields,
    not as a macro-cluster middle edge.

### Writers

- `0xe112` writes `0x783164` from the absolute parsed `ESC &f#Y` value.
- `0xe0a4` writes `0x782d7a` to the existing nonempty record, the first
  free record, or zero for the full-pool miss. On the free path it also
  writes the requested id into record `+0x08`.
- `0xdd08` rewinds `0x78299e`, finds or allocates the selected macro
  record through `0xe0a4`, dispatches selectors `0..10`, and writes
  definition, overlay, delete, temporary, and permanent state.
- `0xdd86..0xde7a` start and stop definition mode, seed lowercase
  `ESC &f` auto-prefix bytes through `0xe002`, and clear empty or
  auto-prefix-only records through `0xdfba`.
- `0xe002` writes macro definition payload bytes into linked 0x100-byte
  chunks, links newly allocated chunks, updates raw record count `+0x04`,
  and sets `0x782c19` on allocation failure.
- `0xddfc..0xde7a` normalizes raw record count into payload byte count at
  selector `1` stop and clears empty or auto-prefix-only definitions.
- `0xde7c..0xdec4` validate execute/call records and call `0xe418`.
- `0xe418` writes the data-chain frame later consumed by `0xa904`, writes
  the environment snapshot pointer at frame `+0x0a`, and pushes the
  call-only context entry at `0x782c6e`.
- `0xe4f4` writes the non-replay frame at `0x782d4c`, writes
  `0x782d76`, saves/restores flat state through `0xe996`/`0xe972`,
  saves cursor longword `0x782c92`, and may set host gate bit 1.
- `0x0b18` writes startup-derived heap inputs `0x780efa` and `0x780efe`
  plus resource-window fields `0x7810b4` and `0x7810b8`.
- `0x164a` writes the allocator bitmap and fields `0x780e86`,
  `0x783972`, `0x783976`, `0x78397a`, `0x78397e`, `0x783982`,
  `0x783986`, and `0x783988`.
- `0x170c` / `0x1710` allocate heap objects in 64-byte units; `0xe8f0`
  allocates linked snapshot chunks; `0xe8a2` restores and checks them;
  `0xe972` and `0xe996` copy flat inclusive longword ranges.
- `0xe22c` consumes the current frame, frees snapshot chunks, rewinds
  `0x782d76` for execute/call frames, clears host gate bit 1 when the
  previous frame is empty, and calls `0x1240a` on return paths. For
  non-execute/non-call frames it leaves `0x782d76` unchanged, restores
  flat state through `0xe972`, writes `0x782c8a` from `0x782c92`, and
  writes `0x782a92 = 0x63`.
- `0x18b4` frees macro payload and snapshot linked chains when count is
  zero, and frees font payload contiguous runs when count is nonzero.
- `0xe65c(0)` pops the call-mode context stack entry, may copy active
  primary/secondary font words to remembered words, and clears its 10-byte
  slot before the shared font-context install exit.
- `0xe146` is the only observed initializer for the macro context stack:
  it clears `0x782c1e..0x782c6d` and stores base pointer `0x782c1e` in
  `0x782c6e`. `0xe418` and `0xe4f4` advance without a bounds test, and
  `0xe65c(0)` rewinds without a base test.
- `0xe65c(1)` consumes and clears static record `0x782c64`, using direct
  flag bytes or `0xe860` class mismatches to force primary/secondary
  refresh.
- `0xe65c` refresh slots write through `0x13eb8`, `0x144d2`, and
  `0x14c64` into current-font context records and glyph maps; its final
  `0xc428` call writes the selected page-root font slot.
- The alternate parser table at `0x116f6` writes stored definition payload
  bytes rather than dispatching ordinary control-code handlers.

### Readers And Consumers

- `0xdd08` reads `0x783164`, `0x782d7a`, `0x782d76`, frame byte `+9`,
  and definition-mode byte `0x782c18` before selector dispatch.
- `0xe0a4` reads each macro record `+0x00` head and `+0x08` id; it does
  not read record `+0x0a` permanence while selecting the current record.
- `0xe002` consumes active frame byte `+9`, macro error byte `0x782c19`,
  current record pointer `0x782d7a`, current append chunk `0x782c1a`,
  and record raw count `+0x04` before writing payload bytes.
- `0xa904` consumes the frame bytes as its active data-chain source,
  dispatches end transitions through `0xe22c`, and then returns replayed
  bytes to the parser.
- `0xe22c` consumes frame `+0x09`, frame `+0x0a`, `0x782c6e`, and
  environment buffers to unwind execute/call frames after replay. Its
  non-execute/non-call path consumes frame `+0x04`, flat source
  `0x7834c2`, cursor save `0x782c92`, and context-stack state used by
  `0xe65c(0)`.
- `0xff1e` consumes `0x782a92`, `0x782a94`, current root flag word
  `+0x14`, and current macro/data record pointer `0x782d7a` before the
  overlay parser re-entry detour. If the selected macro record exists,
  `0xe4f4` produces the non-replay frame and `0x11774` consumes the
  replayed payload before the same `0xff1e` publication boundary.
- `0x164a` consumes startup heap inputs `0x780efa` and `0x780efe`;
  `0x170c`, `0x1710`, and `0x18b4` then consume the initialized
  allocator bitmap, payload base pointer, free-unit count, and scan
  cursor fields.
- `0x170c` consumes request count, zero-fill flag, and alignment word to
  allocate heap units; `0x18b4` consumes pointer, count, and alignment to
  free either a linked chain or contiguous run.
- `0xe65c` consumes context-stack entry bytes `+8/+9` to decide whether
  primary/secondary font refresh helpers such as `0x13eb8` run before
  the slot is cleared.
- `0xe4f4` consumes current record pointer `0x782d7a`, selected context
  byte `0x782f06`, active context tables `0x782ee6..0x782ef6`, cursor
  longword `0x782c8a`, and flat state ranges before producing frame
  byte `+9 = 4`.
- `0xe65c` also consumes selected slot byte `0x782f06`, current context
  fields `0x782c80`/`0x782c84`, active words `0x783144`/`0x783146`, and
  remembered words `0x782f08`/`0x782f0a`; fallback install consumers are
  the already-modeled `0xc428`, `0x1b4c0`, `0x144d2`, and `0x14c64`.
- The composed `0xe65c` bridge consumes the same candidate-filter and
  page-root slot contracts as normal font selection: `0x13eb8` filters
  candidate windows, `0x14c64` rebuilds maps `0x782f32` / `0x783032`, and
  `0xc428` installs selected longwords copied from `0x782ee6` / `0x782ef6`
  into the current page root.
- Parser loop `0x11774` consumes replayed bytes and routes simple replay
  to `0xd04a` and `0xf02c`; mixed-control replay also reaches `0xedf8`.
- Page-record and render consumers use the shared allocation model:
  `0x1387c`/`0x1381c` build objects, `0x1edc6` bridges context/buckets,
  and `0x1ed84`/`0x1ef6a` render them.

### Output Effect

`ESC &f123Y ESC &f0X ! CR ESC &f1X ESC &f2X` stores `21 0d`, builds an
execute frame, drains it through `0xa904`, dispatches `0xd04a` then
`0xf02c`, queues the same text object as direct host bytes, and renders
the same rows. The call selector `3` does the same for the covered text
payload. A host-fetched mixed-control definition stores
`ESC &k1G!\r!`, builds an execute frame, replays through `0xedf8`,
`0xd04a`, `0xf02c`, and `0xd04a`, then matches the direct mixed-stream
rendered rows. Macro replay also composes with selector-7 rule and
mode-0 raster band output in the existing page-record fixture. Overlay
publication now has a first visible-output fixture: selector `4` stores
overlay id `123`, `0xff1e` resolves it through `0xe0a4`, `0xe4f4`
builds a non-replay frame for stored `!\r`, parser loop `0x11774` routes
the replayed bytes through `0xd04a`/`0xf02c`, and the published page
record renders both the overlay text rows and an existing selector-7
rectangle rule. Macro font-context refresh now composes through the
existing font bridge:
`0xe65c` refresh slots `0/1` rebuild maps `0x782f32` / `0x783032`, and
the final `0xc428` install exposes the selected context record through a
page-root font slot for later text objects.
Fixture `macro overlay replays across repeated page publications` now
reuses the same enabled overlay macro for two page-record publications:
the first page has selector-7 rule object
`00 00 00 00 01 07 88 01 00 0c 00 03 00 00`, the second has
`00 00 00 00 01 07 e4 00 00 08 00 04 00 00`, and both publications
replay `!\r` before `0xff1e` publishes. The composed row digests are
`0629159c6a0f5c4a23508d5bfab14b725e13f0bfa32b82efca091aec425fa4c0`
for the first page and
`2d52675c52b22b80e87a379e32894c7a9638596770093d2fd80b64e25559977e`
for the second.
Fixture `macro overlay skip gates preserve base page publication` covers the
other branch of the same `0xff1e` detour. A base page containing printable `?`
and selector-7 rule object
`00 00 00 00 01 07 a2 00 00 06 00 02 00 00` publishes to row digest
`425e0a2abf918906a45f655b589c615108f72ca6b89dc1b280b99121e4405e43`. That
same digest is preserved when overlay mode is disabled, when overlay id `123`
has no nonempty record, and when the page-root retry flag blocks overlay
re-entry.
Fixture `macro overlay mixed-control payload publishes with page rule` covers
the non-replay overlay path with stored payload `ESC &k1G!\r!`. The replayed
escape sequence stores line-termination mode `0x80`, then the two printable
bytes and CR produce compact text payload
`00 02 20 00 01 20 3b 00` plus the context slot copied by `0x1edc6`. The
same published page record carries selector-7 rule object
`00 00 00 00 01 07 cc 01 00 08 00 02 00 00`, rendered through `0x1f596` and
mutated to `00 00 00 00 01 07 cc 01 00 08 00 02 ff ce`. The composed page rows
have digest `04d32edf47d03c587abc0abaf750c6a2d634ceea80df9787681b618867136f52`.
Fixture `macro overlay raster payload publishes with page rule` covers a
delayed-payload overlay replay. Overlay id `126` stores
`! ESC *t300R ESC *r0A ESC *b2W c3 3c`; `0xe4f4` builds a 20-byte non-replay
frame with `+8 = 4` / `+9 = 4`, parser/page replay queues compact text object
`00 00 00 00 00 00 00 01 20 00 01 ...` and mode-0 raster object
`00 00 00 00 80 00 00 02 00 00 c3 3c`, and the preexisting selector-7 rule
`00 00 00 00 01 07 44 01 00 0a 00 02 00 00` mutates through `0x1f596` to
`00 00 00 00 01 07 44 01 00 0a 00 02 ff c6`. The composed page rows render
through `0x1ed84`/`0x1ef6a` with digest
`bc21050018fd3e992709c704fff732499aa9d06565de31d7ae0340869971c5b3`.

### Confidence

High for parser reachability, selector meanings, record count/stride,
current id storage, `0xe0a4` lookup/free/full status behavior, definition
stop behavior, execute/call and non-replay frame mode bytes, frame field offsets
`+0x00/+0x04/+0x08/+0x09/+0x0a`, call-only context-stack push, snapshot
chain chunk shape, execute/call frame-end restore, `0x164a` heap
initializer, `0x170c`/`0x1710` / `0x18b4` shared heap contract,
`0xe65c` branch contract, `0xe65c` bridge into `0x13eb8` / `0x144d2` /
`0x14c64` / `0xc428`, macro definition append/count bookkeeping,
`0xa904` replay, the `0xff1e` overlay detour, and page-record/render
effects because those are covered by disassembly, generated parser-table
reports, and executable fixtures.
High for the `0xe860` `+0x16` / `+0x20` class-selector distinction.

### Fixtures

- `0xe112 stores absolute parsed macro id`
- `0xdd08 starts and stops empty macro definitions`
- `0xe0a4 macro record lookup uses head presence and first free slot`
- `0x11774 ROM dispatch table routes chained ESC &f macro stream`
- `macro command stream defines payload and executes data-chain frame`
- `host-fetched macro execute stream builds replay frame`
- `host-fetched macro call stream builds replay frame`
- `0xe418 frame metadata distinguishes execute and call context`
- `macro snapshot helpers copy linked and flat environment ranges`
- `0x164a initializes heap allocator bitmap and payload base`
- `0x170c/0x1710 allocate and 0x18b4 frees heap units`
- `0xe002 appends macro definition bytes into 0x100 chunks`
- `0xe4f4/0xe22c produce and end data-chain frames`
- `0xe65c refreshes macro font context entries`
- `0xe860 reads inline +0x16 and offset-table +0x20 class bytes`
- `0xe65c refresh composes with font context bridge`
- `0xe5e2 refreshes page layout, default VFC table, and static font
  context`
- `0xe146/e418/e4f4/e65c macro context stack has eight records and no
  guard`
- `macro execute frame payload feeds 0xa904 data-chain bytes`
- `macro execute data-chain parser trace feeds page-record stream`
- `macro call data-chain parser trace feeds page-record stream`
- `host-fetched mixed-control macro execute stream builds replay frame`
- `macro mixed-control data-chain parser trace feeds page-record stream`
- `host-fetched macro replay payloads preserve 0x1edc6 bridge contract`
- `host-fetched macro replay payloads feed 0x1ed84 and 0x1ef6a`
- `macro execute page-record layer composes with rule and raster band`
- `macro overlay finalization replays before page publication`
- `macro overlay replays across repeated page publications`
- `macro overlay skip gates preserve base page publication`
- `macro overlay mixed-control payload publishes with page rule`
- `macro overlay raster payload publishes with page rule`

### Disassembly Evidence

- `generated/disasm/ic30_ic13_pcl_escape_parser_00da9a.lst`:
  `0xdd08..0xdfb8`, including selector dispatch, record pool scans, and
  execute/call calls to `0xe418`.
- `generated/disasm/ic30_ic13_macro_record_chain_helpers_00dfba.lst`:
  `0xdfba..0xe4f2`, including record clear, append, lookup/allocation,
  parser reset, frame cleanup, frame end, and `0xe418` frame creation.
  The lookup/free/full scan is specifically `0xe0a4..0xe110`.
  The non-replay frame producer and layout refresh are `0xe4f4..0xe65a`.
- `generated/disasm/ic30_ic13_macro_environment_snapshot_helpers_00e65c.lst`:
  `0xe65c..0xe9b8`, including context-stack pop, snapshot chain
  allocation, snapshot restore, and flat copy helpers.
- `notes/font-context-metrics.md`: `0x13eb8`, `0x144d2`, `0x14c64`,
  `0xc428`, page-root font slots, render-record context-slot bridge,
  printable source capture, and span-metric consumers.
- `generated/disasm/ic30_ic13_heap_allocator_init_00164a.lst`:
  `0x164a..0x18d8`, including heap bitmap initialization, low/high
  allocation entries, zero-fill, and free entry setup.
- `generated/disasm/ic30_ic13_main_parser_loop_011774.lst`:
  normal versus alternate parser table selection.
- `generated/analysis/ic30_ic13_parser_dispatch_tables.md`:
  normal mode 17 `y/Y/x/X` entries and alternate/data table `x/X`
  reachability.
- `generated/analysis/ic30_ic13_tokenizer_macro_callers.md`:
  `0xdd08` parser-table reachability with no direct `JSR` callers.
- `generated/analysis/ic30_ic13_parser_xrefs.md`:
  `0xe418` references from `0xde96` and `0xdebc`.
- `generated/analysis/ic30_ic13_renderer_fixture_harness.md`:
  macro command and data-chain fixture outputs.

### Unresolved Middle Edges

- None remaining for macro execute/call replay, macro font-context refresh,
  first overlay-publication, repeated enabled-overlay publication across two
  page boundaries, mixed-control overlay payload publication, raster overlay
  payload publication, or the disabled/missing-record/retry-flag overlay skip
  gates. Remaining macro risk is broader overlay payload variants beyond
  `!\r`, `ESC &k1G!\r!`, and the covered raster payload, plus final-device
  comparison, not the `0xdd08` selector-4 to `0xff1e` visible-output path or
  its skip gates.

## Raster Transfer Gate And Encoded Rows

Status: composed as the raster command-family checkpoint from parsed
`ESC *t#R`, `ESC *r#A`, delayed `ESC *b#W`, and payload bytes to encoded
page-record objects and `0x1f88e` rendered rows. The low-level ledger remains
in [raster-graphics.md](raster-graphics.md); this section records the semantic
state model needed by byte-stream reproduction.

Concept: raster commands update a state block at `0x783170`, but raster data
does not render directly. `0x11f82` stores a delayed transfer handler
`0x105d0` through `0x121cc`; `0x12218` later restores the six-byte
`ESC *b#W` record and calls `0x105d0` when payload bytes are available.
`0x105d0` gates the row, drains skipped payload through `0xdace`, ensures a
page root for queued rows, and passes the state block to `0x13070` /
`0x13250`, which builds encoded-span objects consumed later by `0x1f88e`.

### Field Groups

- Canonical raster state at `0x783170`:
  - `+0x00`: baseline word copied from `+0x0a`.
  - `+0x02`: current row coordinate used by `0x105d0` and `0x13070`.
  - `+0x04`: accepted byte count for the current transfer.
  - `+0x06`: overflow byte count beyond the accepted transfer.
  - `+0x08`: encoded raster mode, stored as scale minus one.
  - `+0x0a`: packed origin/baseline coordinate copied from cursor state.
  - `+0x0e`: raster scale, `1`, `2`, `3`, or `4`.
  - `+0x10`: maximum accepted row byte count after extent/scale clipping.
  - `+0x12`: raster-active flag.
  Evidence: fixtures
  `parser-derived ESC *t300R / ESC *r1A state queues mode-0 raster row`,
  `0x105d0-modeled raster transfer skip and cap gate`,
  `modeled raster command stream parses ESC *rB and re-enables resolution
  changes`, `raster active resolution parser trace preserves current mode`,
  and
  [raster-graphics.md](raster-graphics.md).
- Canonical page-record object:
  - object `+0x00`: next pointer in bucket chain.
  - object `+0x04`: class byte `0x80`, selecting encoded raster dispatch.
  - object `+0x05`: mode byte `0..3`, selecting the `0x1f88e` helper.
  - object `+0x06`: even-rounded payload capacity / accepted byte count.
  - object `+0x08`: packed x/y key from `0x13070`.
  - object `+0x0a..`: copied raster payload bytes.
  Evidence: fixtures `0x13070/0x13250 raster row queues encoded-span object`
  and the mode-1, mode-2, mode-3 sibling fixtures listed below.
- Parser scratch:
  - parsed records for the primary stream are
    `80 52 01 2c 00 00`, `80 41 00 01 00 00`, and
    `80 57 00 04 00 00`.
  - delayed snapshot for `ESC *b4W` is
    `01 00 01 05 d0 80 57 00 04 00 00`.
  - payload offset for the primary stream is byte `17`, payload
    `f0 0f aa 55`.
  - lower-resolution streams carry the same three-record command family but
    substitute `ESC *t150R`, `ESC *t100R`, or `ESC *t75R`; the restored
    transfer record still reaches `0x105d0` before payload consumption.
  - same-family lowercase chaining keeps parser mode live: `ESC *b2w2W`
    preserves delayed record `80 77 00 02 00 00` until uppercase `W` restores
    it at payload offset `19`.
  Evidence: fixture
  `0x11774 ROM dispatch table routes raster stream to delayed transfer`,
  `raster mode streams tie ROM parser dispatch to modeled queued objects`,
  and
  `raster chained transfer parser trace preserves lowercase delayed record`.
- Derived/cache producer keys:
  - `0x782a7c`: bucket index derived from row coordinate.
  - `0x782a7e`: packed x/y key copied into object `+0x08`.
  - `0x782a80`: allocation capacity selected by `0x132b6`.
  These are derived from current transfer state and consumed by `0x13250`,
  not persistent parser fields.
- Derived/cache command effects:
  - `ESC *t150R`, `ESC *t100R`, and `ESC *t75R` select encoded modes `1`, `2`,
    and `3`; each mode then flows through the same delayed-transfer and
    render-record path as the primary mode-0 stream.
  - Two consecutive uppercase `ESC *b2W` transfers restore independent
    records, consume payloads at offsets `17` and `24`, queue coordinates
    `0x0000` and `0x1000`, and advance modeled `row_y` to `2`.
  Evidence: fixtures
  `modeled raster command stream queues consecutive ESC *b#W rows`,
  `raster multi-row parser trace feeds consecutive queued objects`, and
  `host-fetched raster mode streams feed 0x1ed84 and 0x1ef6a`.
- Firmware bookkeeping:
  - `0x78297a`: current page root ensured by `0x10084` after the
    beyond-extent gate and before either negative-row drain or queued-row
    object insertion.
  - `0x782a70`, `0x782a72`, and `0x782a76`: stream allocator state consumed
    by addressed raster/page-record fixtures.
  - beyond-extent rows drain input and return before `0x10084`; negative rows
    store accepted/overflow counts, ensure a root, drain input, and advance
    without creating a raster object.
- Unknown for this checkpoint:
  - exact live CPU register/memory trace through `0x105d0` into the dense
    mixed text/rule/raster stream. Addressed `0x1381c` storage is fixture-backed
    for that stream, but it is still modeled rather than captured from one live
    68000 parser run.

### Writers

- `0x10808` writes raster scale/mode from `ESC *t#R` when raster active byte
  `+0x12` is clear.
- `0x1075a` writes origin/baseline, active byte, and byte limit from
  `ESC *r#A`; parameter `1` seeds from the active cursor axis, while other
  parameters clear the origin to the left edge.
- `0x107fa` clears only active byte `+0x12` for `ESC *r#B`.
  Fixture
  `modeled raster command stream parses ESC *rB and re-enables resolution
  changes` proves the later `ESC *t150R` can update mode and scale after
  this clear.
- `0x11f82` stores delayed transfer handler `0x105d0`; `0x12218` restores the
  delayed record and dispatches it.
- `0x105d0` writes active byte `+0x12`, current row `+0x02`, accepted count
  `+0x04`, overflow count `+0x06`, and post-transfer cursor state. It calls
  `0x10084` for rows that pass the beyond-extent gate; negative rows therefore
  ensure a root before draining without `0x13070`.
- `0x13070` computes bucket/key fields, and `0x13250` allocates and links the
  encoded-span object under page-root `+0x1c`.
- `0x138de` copies the accepted payload bytes into object `+0x0a` and
  decrements raster state field `+0x04`.

### Readers And Consumers

- Parser loop `0x11774` routes the primary raster stream through final
  handlers `0x10808`, `0x1075a`, and `0x11f82`.
- The same parser loop routes lower-resolution streams to `0x10808`,
  `0x1075a`, and `0x11f82`, and routes `ESC *rB` to `0x107fa`.
  Fixtures `host-fetched raster mode streams reach parser and rendered rows`
  and `raster end parser trace feeds active-clear and resolution re-enable`
  pin those handler sequences.
- `0x105d0` consumes the restored command record byte count and raster state
  fields. Beyond-extent rows drain the full count without queueing or row
  advance and return before `0x10084`; negative rows store the capped
  accepted count and overflow, ensure a root, drain the full count without
  queueing, and advance from `-1` to `0`; capped rows queue only the accepted
  bytes.
- `0x138de` consumes queued payload through `0xa904` and locally maps control
  pair `1a 58` to copied byte `00`.
- `0x1edc6` copies the queued bucket object into render-record bucket roots.
- `0x1efc2` sees object byte `+4 & 0xc0 == 0x80` and dispatches to
  `0x1f88e`.
- `0x1f88e` consumes object byte `+5`, key `+8`, and payload `+0x0a..` to
  select helpers `0x1f8da`, `0x1f8e6`, `0x1f920`, or `0x1f9c6`.

### Output Effect

The primary parser-derived stream queues object
`00 00 00 00 80 00 00 04 00 01 f0 0f aa 55` and renders:

```text
................####........#####.#.#.#..#.#.#.#
```

The capped transfer fixture proves byte count `4` with limit `2` stores
`+0x04 = 2`, stores overflow `+0x06 = 2`, queues payload `f0 0f`, and renders
`####........####`. The beyond-extent fixture drains four bytes, queues no
object, and leaves the root unensured; the negative-row fixture drains four
bytes, queues no object, stores the same capped count/overflow pair as the
in-range capped case, ensures a root, and advances to row zero. The mode
fixtures prove byte-aligned mode `0`, non-byte-aligned mode `0`, mode `1`,
mode `2`, shifted mode `2`, band-clipped mode `2`, and mode `3` object/render
contracts through `0x1f88e`.

Lower-resolution parser fixtures now prove the same host-fetched command/data
boundary for modes `1`, `2`, and `3`: each stream drains through the modeled
`0xa904` ring source, reaches parser handlers `0x10808`, `0x1075a`, and
`0x11f82`, restores the delayed transfer record, queues the mode-specific
encoded object, crosses `0x1ed84` / `0x1ef6a`, and renders rows through
`0x1f88e`.

The multi-row and chained-transfer fixtures cover the repeated-transfer state
block. Two uppercase `ESC *b2W` records restore independently, consume payloads
at offsets `17` and `24`, advance `row_y` to `2`, and queue objects at packed
coords `0x0000` and `0x1000`. The lowercase `ESC *b2w2W` stream keeps parser
mode in the `*b` family, preserves delayed record `80 77 00 02 00 00`, consumes
payload only after the uppercase terminator at offset `19`, and renders through
the same bucket/render entry path.

The raster-active fixtures split two related state effects. `ESC *rB` clears
active byte `+0x12`, so the following `ESC *t150R` changes mode/scale again.
While active, `ESC *t75R` is ignored: fixture
`raster active resolution parser trace preserves current mode` leaves the
current mode and scale unchanged before the next `ESC *b2W` queues a mode-0
object.

### Confidence

High for parser handler order, delayed snapshot bytes, `0x105d0` gate
outcomes, the corrected root boundary for beyond-extent versus negative rows,
encoded object layout, bridge preservation, mode dispatch helpers, and
rendered rows because those are asserted by named harness fixtures and by
disassembly addresses `0x1065c..0x106cc`. High for the covered raster-state
effects of `ESC *rB`, active-resolution ignore, lower-resolution mode
selection, consecutive transfers, and lowercase same-family `*b` chaining
because each has parser-dispatch, restored-record, object, and render-entry
fixtures. Medium for live CPU/register fidelity inside `0x105d0..0x13250`
during a dense parser-produced page because the current evidence is
modeled/address-aware rather than a full 68000 execution trace.

### Fixtures

- `0x11774 ROM dispatch table routes raster stream to delayed transfer`
- `modeled raster command stream parses ESC *t300R / ESC *r1A / ESC *b4W`
- `host-fetched raster stream reaches parser and queued pixels`
- `raster payload reader normalizes 0xdace controls before queueing pixels`
- `host-fetched raster control payload normalizes before queueing pixels`
- `parser-derived ESC *t300R / ESC *r1A state queues mode-0 raster row`
- `0x105d0-modeled raster transfer skip and cap gate`
- `modeled raster command stream applies 0x105d0 byte-count cap`
- `modeled raster command stream queues inclusive page-extent row`
- `modeled raster command stream drains beyond-extent transfer without
  queueing`
- `modeled raster command stream drains negative-row transfer and advances`
- `raster parser trace feeds capped and drained transfer gates`
- `host-fetched raster gate stream reaches capped and drained paths`
- `raster transfer ensures page root before queueing row object`
- `raster stream ties parser dispatch to queued page object`
- `0x13070/0x13250 raster row queues encoded-span object`
- `0x1f88e mode-0 raster object renders queued literal row`
- `0x1edc6 page-record bridge preserves queued raster object`
- `0x13070/0x13250 raster row queues non-byte-aligned encoded-span object`
- `0x1f88e mode-0 raster object renders sub-byte shifted literal row`
- `0x13070/0x13250 raster mode-1 row queues encoded-span object`
- `0x1f88e mode-1 raster object expands queued bytes into two rows`
- `0x13070/0x13250 raster mode-2 row queues encoded-span object`
- `0x1f88e mode-2 raster object expands queued byte pair into three rows`
- `0x13070/0x13250 raster mode-2 row queues non-byte-aligned encoded-span
  object`
- `0x1f88e mode-2 raster object renders sub-byte shifted expanded rows`
- `0x13070/0x13250 raster mode-2 row queues band-clipped encoded-span object`
- `0x1f88e mode-2 raster object clips current-band rows and continues in
  fallback buffer`
- `0x13070/0x13250 raster mode-3 row queues encoded-span object`
- `0x1f88e mode-3 raster object expands queued bytes into four rows`
- `raster mode streams tie ROM parser dispatch to modeled queued objects`
- `host-fetched raster mode streams reach parser and rendered rows`
- `host-fetched raster mode streams feed 0x1ed84 and 0x1ef6a`
- `modeled raster command stream queues consecutive ESC *b#W rows`
- `modeled raster command stream renders consecutive queued rows`
- `raster multi-row parser trace feeds consecutive queued objects`
- `host-fetched raster multi-row stream reaches consecutive queued rows`
- `modeled raster command stream parses ESC *rB and re-enables resolution
  changes`
- `raster end parser trace feeds active-clear and resolution re-enable`
- `host-fetched raster end stream clears active state and re-enables
  resolution`
- `raster active resolution parser trace preserves current mode`
- `host-fetched active raster resolution stream preserves current mode`
- `modeled raster command stream accepts lowercase same-group resolution
  chaining`
- `host-fetched raster chained resolution stays in same parser family`
- `modeled raster command stream defers lowercase ESC *b w payload until
  uppercase terminator`
- `raster chained transfer parser trace preserves lowercase delayed record`
- `host-fetched raster chained transfer preserves lowercase delayed record`
- `host-fetched raster multi-row and chained streams preserve 0x1edc6 bridge
  contract`
- `host-fetched raster streams feed 0x1ed84 and 0x1ef6a`

### Disassembly Evidence

- `generated/disasm/ic30_ic13_raster_handlers_0105d0.lst`
- `generated/disasm/ic30_ic13_raster_object_queue_013070.lst`
- `generated/disasm/ic30_ic13_display_list_helpers_013386.lst`
- `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`
- `generated/disasm/ic30_ic13_bitmap_encoded_span_modes_01f88e.lst`

### Unresolved Middle Edges

- `0x105d0..0x13250`: delayed record restore, gate outcomes, encoded object
  layout, rendered mode contracts, resolution-active interactions,
  consecutive transfers, and same-family lowercase chaining are
  fixture-backed. Parser scratch is the delayed `80 57 ...` record,
  snapshot, payload offset, and drained bytes; canonical output is the
  page-root `+0x1c` raster chain plus object bytes from `0x13070` /
  `0x13250`; derived/cache state is the bucket/key and render-record copy
  consumed by `0x1ed84` / `0x1ef6a`. The remaining edge is specifically live
  CPU/register memory across
  `0x12218 -> 0x105d0 -> 0x10084 -> 0x13070`, not parser dispatch,
  encoded-object layout, or mode renderer behavior.
- `0x13250..0x1381c`: addressed allocation is covered in the shared
  page-record allocator checkpoint and in the addressed text/rule/raster
  fixture, where the raster object lives at `0x00d0c038` and publishes as
  `00 d0 c0 04 80 00 00 02 00 00 c3 3c`. The remaining gap is not object
  layout or addressed storage; it is live 68000 heap/register capture for the
  complete parser-produced stream.

## Rectangle Rule Producer And Renderer

Status: composed as the `ESC *c` rectangle/rule command-family checkpoint
from parsed width/height/fill commands to rule-list page-record objects,
bridge normalization, no-room retry, and solid/pattern rendered rows. The
low-level ledger remains in [rectangle-graphics.md](rectangle-graphics.md).

Concept: rectangle commands accumulate persistent width, height, and fill
state until `ESC *c#P` asks the firmware to fill a rectangle. Handler
`0x10898` maps the requested fill mode to a selector, `0x10b80` clips the
current cursor-sized rectangle against page extents, and `0x13386` /
`0x133aa` inserts a 14-byte rule object under page-root `+0x24`. Rendering is
deferred until `0x1edc6` normalizes the rule list and `0x1f446` dispatches
selector `7` to `0x1f596` or non-solid selectors to `0x1f4e0`.

### Field Groups

- Canonical rectangle command state:
  - `0x78316a`: current rectangle width, written by `ESC *c#A` and
    `ESC *c#H`.
  - `0x783166`: current rectangle height, written by `ESC *c#B` and
    `ESC *c#V`.
  - `0x78316e`: current area-fill id, written by `ESC *c#G` and consumed by
    `ESC *c#P` modes `2` and `3`.
  Evidence: fixtures
  `0x10e68/0x10e22/0x10a40/0x10ae0 rectangle size commands update packed
  dimensions` and `0x10898 ESC *c#P maps fill selectors and queues rule
  object`.
- Canonical page/cursor inputs:
  - `0x782c8a` and `0x782c8e`: current x/y cursor used as rectangle origin.
  - `0x782da3`: orientation flag selecting portrait or landscape coordinate
    conversion.
  - `0x782db8` and `0x782db6`: horizontal and vertical page extents consumed
    by `0x10b80` reject/clip gates.
  - `0x78297a`: current page root ensured before queueing.
- Canonical rule source record at `0x782a88`:
  - `+0x00`: queued x.
  - `+0x02`: queued y.
  - `+0x04`: queued width.
  - `+0x06`: queued height.
  - `+0x08`: fill selector.
  Evidence: `0x10b80 rectangle fill clips right/top/bottom edges and ignores
  off-page fills`.
- Canonical rule-list object under page-root `+0x24`:
  - object `+0x00`: next pointer.
  - object `+0x04`: bucket byte from `0x782a7d`.
  - object `+0x05`: fill selector before bridge; bridged selector has bit
    `0x10` set.
  - object `+0x06`: packed key from `0x782a7e`.
  - object `+0x08`: width.
  - object `+0x0a`: height.
  - object `+0x0c`: continuation height, copied from height by `0x1edc6` and
    mutated across render bands.
  Evidence: fixture
  `0x13386/0x133aa-modeled rectangle/rule list object and bridge
  normalization`.
- Derived/cache producer keys:
  - `0x782a7c`: bucket index `source_y >> 4`.
  - `0x782a7d`: low bucket byte copied into object `+4`.
  - `0x782a7e`: packed key
    `((source_y << 12) & 0xf000) | (((source_x + 0x782dc0) & 0x0f) << 8)
    | (((source_x + 0x782dc0) >> 4) & 0x00ff)`.
  These keys are produced by `0x134d6` and consumed by `0x133aa` /
  `0x1f446`; they are not parser scratch.
- Firmware bookkeeping:
  - stream allocator fields `0x782a70`, `0x782a72`, and `0x782a76` are
    consumed by `0x1381c`.
  - page-root flag bit `+0x15.0` is set by the no-room retry path before
    `0xff1e` publishes the old root.
  - no-room retry uses `0xff1e` then `0x10084` before retrying the same source.
- Unknown for this checkpoint:
  - complete live 68000 parser-to-allocator trace for no-room retry and real
    heap/free-list memory.

### Writers

- `0x10e68` and `0x10e22` write dot width/height. Missing or nonpositive
  parameters clear the stored dimension.
- `0x10a40` and `0x10ae0` write decipoint width/height after multiplying by
  five 300-dpi subunits, rounding up fractional subunits, and adding the
  firmware `+11` subunit bias.
- `0x10dce` writes area-fill id `0x78316e`.
- `0x10898` maps `ESC *c#P` to fill selectors: `0`/missing to selector `7`,
  gray percentages to selectors `0..7`, and pattern ids to selectors `8..13`
  with the documented landscape remaps.
- `0x10b80` writes the clipped source record at `0x782a88`, ensures a page
  root through `0x10084`, and calls `0x13386`.
- `0x13386` calls `0x134d6`, and `0x133aa` allocates/links the rule object
  under page-root `+0x24` through `0x1381c`.
- `0x10d22..0x10d3e` handles no-room retry by setting page-root flag bit
  `+0x15.0`, publishing through `0xff1e`, allocating a fresh root through
  `0x10084`, and retrying `0x13386`.
- `0x1edc6` copies page-root `+0x24` into render-record `+0x1c`, ORs object
  byte `+5` with `0x10`, and copies height `+0x0a` into continuation
  `+0x0c`.

### Readers And Consumers

- Parser loop `0x11774` routes the chained `ESC *c12a5b0P` stream through
  handlers `0x10e68`, `0x10e22`, and `0x10898`.
- `0x10b80` consumes cursor, dimensions, extents, and orientation to reject,
  clip, or queue the source.
- `0x133aa` consumes page-root/stream allocator state and maintains ascending
  object byte `+4` order; equal bucket bytes insert after the existing equal
  node.
- `0x1f446` consumes bridged rule-list nodes for the active render band.
  Selector `7` dispatches to solid helper `0x1f596`; selectors `0..6` and
  `8..13` dispatch to pattern helper `0x1f4e0`.
- `0x1f596` and `0x1f4e0` consume packed key, width, and continuation height
  to write bitmap rows; continuation `+0x0c` carries remaining rows into later
  bands.

### Output Effect

Fixture `rectangle command stream queues chained ESC *c rule object` proves
`ESC *c12a5b0P` queues selector-7 rule object
`00 00 00 00 01 07 4a 00 00 0c 00 05 00 00`. Fixture
`0x11774 ROM dispatch table routes chained ESC *c rule stream` proves the same
parser modes and final handlers before bridge normalization to
`00 00 00 00 01 17 4a 00 00 0c 00 05 00 05`.

Fixture `0x1f446/0x1f596 renders solid black rectangle rule pixels` decodes
key `0x4a00` as x `10`, y `20`, width `12`, rows `5`, partial mask `0xfff0`,
and renders five solid rows. The band-crossing solid fixture starts at y `78`,
draws two rows in the first band, leaves three rows in object `+0x0c`, and
draws those remaining rows at y `0` in the next band.

Fixture `0x1f4e0 renders gray and HP pattern selector matrix` pins the
non-solid selector table and pattern starts. Selector `0` uses pattern base
`0x02ff3e`; shifted HP pattern selector `13` with key `0x3500` decodes x `5`,
y `3`, width `19`, row-low `3`, pattern start `0x0306c4`, left mask
`0x07ff`, and right mask `0xff00`.

Fixture `host-fetched alternate rectangle selectors feed full page records`
composes two non-solid selector paths with compact text and the page-record
renderer. Stream `! ESC *c12a5b50g2P` routes through `0xd04a`, `0x10e68`,
`0x10e22`, `0x10dce`, and `0x10898`; `50g` writes canonical fill state
`0x78316e = 50`, `2P` maps it to gray selector `4`, `0x1edc6` bridges object
`00 00 00 00 01 04 5c 01 00 0c 00 05 00 00` to
`00 00 00 00 01 14 5c 01 00 0c 00 05 00 05`, and `0x1f446` dispatches
selector `4` to `0x1f4e0`. Stream `! ESC *c12a5b2g3P` uses the same handlers;
`2g` writes fill state `2`, `3P` maps it to portrait HP-pattern selector `9`,
`0x1edc6` bridges `00 00 00 00 01 09 5c 01 00 0c 00 05 00 00` to
`00 00 00 00 01 19 5c 01 00 0c 00 05 00 05`, and `0x1f446` again dispatches
to `0x1f4e0`. The derived row digests are
`f7e8bc65420e95a1456db1f0673a164f8ae2f1919fb4b5b8964886354fc54fdf` for
selector `4` and
`c981832502ee7ed97b339959027448f878d591e3909519a3b9233e31200ac599` for
selector `9`.

Fixture `host-fetched rectangle selector matrix feeds full page records`
extends that composition to every non-solid selector id and the landscape
pattern remap. It covers portrait gray selectors `0..6` through
`! ESC *c12a5b#g2P`, portrait pattern selectors `8..13` through
`! ESC *c12a5b#g3P`, and landscape pattern remaps `1 -> 9`, `2 -> 8`,
`3 -> 11`, and `4 -> 10`. For each case, the fixture asserts parser handlers
`0xd04a`, `0x10e68`, `0x10e22`, `0x10dce`, and `0x10898`, the canonical page
rule object, the `0x1edc6` bridged rule object, `0x1f4e0` helper dispatch,
the mutated continuation object, and a composed page-row digest.

Fixture `0x10b80 rectangle fill clips right/top/bottom edges and ignores
off-page fills` proves negative-left clipping from start x `-3`, width `10`
to queued x `0`, width `7`, plus right-edge, top-edge, bottom-edge,
landscape-right-edge, horizontal-outside, vertical-outside, and
empty-after-clip outcomes.

Fixture `rectangle parser trace feeds no-room retry path` proves the parser
trace reaches `0x10e68`, `0x10e22`, and `0x10898`; the no-room path publishes
an existing compact text bucket, allocates a fresh root, retries the
selector-7 object, bridges it through `0x1edc6`, and renders the retried rule.

### Confidence

High for parser handler order, dimension/fill selector mapping, clipping and
ignore gates, rule object bytes, ordered insertion, bridge normalization,
solid and pattern dispatch, continuation mutation across bands, and no-room
retry output because each is fixture-pinned. Medium for live CPU/register
fidelity inside parser-to-allocator no-room retry because the current evidence
models allocator results rather than executing the full heap/free-list path.

### Fixtures

- `0x10e68/0x10e22/0x10a40/0x10ae0 rectangle size commands update packed
  dimensions`
- `0x10898 ESC *c#P maps fill selectors and queues rule object`
- `rectangle command stream queues chained ESC *c rule object`
- `0x11774 ROM dispatch table routes chained ESC *c rule stream`
- `host-fetched rectangle rule stream preserves 0x1edc6 bridge contract`
- `0x13386/0x133aa-modeled rectangle/rule list object and bridge
  normalization`
- `0x1f446/0x1f596 renders solid black rectangle rule pixels`
- `0x1f4e0 renders gray and HP pattern selector matrix`
- `host-fetched alternate rectangle selectors feed full page records`
- `host-fetched rectangle selector matrix feeds full page records`
- `0x10b80 rectangle fill clips right/top/bottom edges and ignores off-page
  fills`
- `0x10d22 rectangle/rule no-room retry finalizes root then retries span`
- `rectangle parser trace feeds no-room retry path`

### Disassembly Evidence

- `generated/disasm/ic30_ic13_rectangle_graphics_010898.lst`
- `generated/disasm/ic30_ic13_display_list_helpers_013386.lst`
- `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`
- `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`
- `generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`
- `generated/analysis/ic30_ic13_rectangle_graphics_flow.md`

### Unresolved Middle Edges

- `0x10898..0x133aa`: command routing, clipping, selector mapping, rule object
  bytes, bridge normalization, render rows, and no-room retry are
  fixture-backed. The remaining edge is full live 68000 execution through
  parser, `0x10b80`, `0x1381c`, and real allocator memory.
- Non-solid selectors `0..6` and `8..13` plus landscape pattern remaps
  `1 -> 9`, `2 -> 8`, `3 -> 11`, and `4 -> 10` now have page-visible
  comparisons through compact text, bridge normalization, `0x1f446`, and
  `0x1f4e0`. Remaining rectangle selector risk is broader cross-feature
  combinations with font selection, downloaded glyphs, geometry changes, and
  physical output, not the selector mapping or page-record render dispatch
  itself.

## Mixed Text/Rule/Raster Page Record

Status: anchored as a parser-to-render composition checkpoint, but still
modeled at the CPU live-state boundary. The byte stream
`! ESC *c12a5b0P ESC *t300R ESC *r0A ESC *b2W c3 3c FF` now has
host-fetched, addressed-storage, publication, and render-entry coverage.
The fixture proves the same semantic page record carries compact text,
a selector-7 rectangle rule, and one mode-0 raster row through `0xff1e`,
`0x1ed84`, and `0x1ef6a`.

Concept: page output is not a direct raster operation per command. The
parser first builds typed page-record lists under the current page root,
then `0xff1e` publishes the page/control pool record. The render path
copies that record through `0x1ed84`/`0x1edc6`, walks the bucket/rule
lists through `0x1ef6a`, and only then composes visible pixels.

### Field Groups

- Canonical page-record fields:
  - bucket array `+0x1c`: text object at `0x00d0c004`, raster object at
    `0x00d0c038`, bucket head `0x00d0c038`.
  - rule list `+0x24`: rectangle rule object at `0x00d0c02a`.
  - context slots `+0x2c`: slot 0 is `0x440946b4`. Evidence: fixture `addressed
    text/rule/raster field groups reach publication and render entry`; source fixture
    [harness](/usr/home/admin/T400/ljII/tools/render_fixture_harness.py:40084).
- Canonical published-record fields:
  - published bucket root `+0x1c` is
    `00 d0 c0 04 80 00 00 02 00 00 c3 3c`.
  - published rule list `+0x24` is
    `00 00 00 00 01 07 5c 01 00 0c 00 05 00 00`.
  Evidence: fixtures
  `addressed text rectangle raster FF publishes rendered page record`
  and
  `addressed text/rule/raster field groups reach publication and render
  entry`.
- Parser scratch:
  - raster parsed/restored record: `80 57 00 02 00 00`.
  - delayed snapshot: `01 00 01 05 d0 80 57 00 02 00 00`.
  - payload offset `28`, payload `c3 3c`.
  Evidence: handler `0x11f82` schedules `0x105d0` through `0x121cc`,
  restored by `0x12218`; fixture above.
- Firmware bookkeeping:
  - stream allocator state `0x782a70 = 0x00bc`,
    `0x782a72 = 0x00d0c000`, `0x782a76 = 0x00d0c044`.
  - one stream allocation, one page-record root allocation, one
    publication, one root clear, and page-publication flag `1`.
  Evidence: address-aware `0x1381c`/`0x1387c` fixtures and the
  addressed text/rule/raster field-group fixture.
- Derived/cache render fields:
  - `0x783a20 = 0x0050`, `0x783a22 = 0`,
    `0x783a28 = 0x00100000`.
  - crossing rule-list carry state: when `0x1f446` / `0x1f4e0`
    cannot finish a patterned rule in the current band, the mutated rule
    node is carried to the next band with its remaining row count
    reduced.
  Evidence: render-entry setup fixture
  `addressed text/rule/raster field groups reach publication and render
  entry`, with `0x1ef86` before `0x1efc2`, `0x1f446`, and `0x1f756`,
  plus fixture `0x1ef6a page-band walk merges text raster and crossing
  rule`.
- Unknown for this cluster:
  - the exact live CPU stack/register handoff between the modeled parser
    runner and real memory-backed page-root objects is still unknown.
  - no additional named semantic field is assigned to `0x782a70`,
    `0x782a72`, or `0x782a76` beyond stream allocator bookkeeping.

### Writers

- `0xd04a` consumes printable `!`, builds a source through `0x1393a`,
  positions it through `0xd824`, ensures the page root through `0x10084`,
  and queues compact text through `0x12f2e`/`0x1387c`.
- `0x10e68` and `0x10e22` write pending rectangle dimensions from
  `ESC *c12a5b`; `0x10898` queues the selector-7 rule object.
- `0x10808` writes raster mode/scale for `ESC *t300R`; `0x1075a`
  starts raster graphics for `ESC *r0A`.
- `0x11f82` records the delayed `ESC *b2W` transfer, `0x12218`
  restores handler `0x105d0`, and `0x105d0` queues the mode-0 raster
  object through the modeled `0x13070`/`0x13250` path.
- `0xf0f0` triggers the FF publication path. The modeled `0xff1e`
  copies the page-record lists into the published pool record and clears
  the current page root.
- `0x1ed84` copies active published-record header fields, and `0x1edc6`
  copies bucket/rule/context roots into the render record.

### Readers And Consumers

- The parser dispatch table at `0x11774` consumes the host-fetched stream
  through handlers `0xd04a`, `0x10e68`, `0x10e22`, `0x10898`,
  `0x10808`, `0x1075a`, `0x11f82`, and `0xf0f0`.
- `0x1381c` consumes `0x782a70`, `0x782a72`, and `0x782a76` while
  allocating text, rule, and raster stream objects.
- `0xff1e` consumes the current page root and page-record lists to build
  the published pool record.
- `0x1ef6a` consumes the render record in call order
  `0x1ef86`, `0x1efc2`, `0x1f446`, `0x1f756`. It dispatches the raster
  object to `0x1f88e` and the compact text object to `0x1effe`.

### Output Effect

The covered stream produces rows containing the first compact `!`, the
mode-0 raster row from payload `c3 3c`, and the rectangle rule. The
published render-entry fixture proves the same rows before and after the
`0xff1e` publication boundary, with dispatch targets `0x1f88e` and
`0x1effe`.
The page-band walker fixture extends this render-entry contract across
bands `0` and `5`: it dispatches compact text and mode-0 raster objects
from bucket array `+0x18`, carries a patterned rule's mutated node from
rule list `+0x1c` after the first band, then renders the remaining rule
rows in the second band with no leftover rule or fixed-list state.

### Confidence

High for parser handler order, delayed raster scratch, addressed stream
object addresses, published page-record fields, render-entry call order,
and visible rows because they are executable fixture assertions. Medium
for exact live CPU state at the page-root/display-list handoff because
the current fixture is address-aware but not a full 68000 run through
the parser and allocator.

### Fixtures

- `host-fetched text rectangle raster FF publishes rendered page record`
- `addressed text rectangle raster FF publishes rendered page record`
- `addressed text/rule/raster field groups reach publication and render
  entry`
- `0x1ef6a page-band walk merges text raster and crossing rule`
- Supporting fixtures:
  `host-fetched text rectangle and raster page record feeds 0x1ed84 and
  0x1ef6a`,
  `addressed text rectangle raster stream matches page-record output`,
  and
  `published text rectangle and raster page record feeds 0x1ed84 and
  0x1ef6a`

### Disassembly Evidence

- `generated/disasm/ic30_ic13_main_parser_loop_011774.lst`:
  parser mode dispatch and handler selection.
- `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`:
  printable source construction and queue entry.
- `generated/disasm/ic30_ic13_rectangle_graphics_010898.lst`:
  rectangle dimensions and fill rule producer.
- `generated/disasm/ic30_ic13_raster_handlers_0105d0.lst`:
  raster setup, delayed transfer, and row queue gates.
- `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst` and
  `generated/disasm/ic30_ic13_raster_object_queue_013070.lst`:
  producer shapes for compact text and encoded raster objects.
- `generated/disasm/ic30_ic13_display_list_helpers_013386.lst`:
  display-list allocator, bucket insertion, and rule-list insertion.
- `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst` and
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`:
  publication and render-record bridge.
- `generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`:
  render-entry call order and bucket/list consumers.

### Unresolved Middle Edges

- `0xd04a..0x12f2e`: source-object fields, paired queue handoffs, and
  compact producer semantics are composed in `Text Source Objects And
  Compact Buckets`; this mixed stream still lacks a full live
  CPU/register trace for the complete parser-produced dense page.
- `0x10898..0x133aa`: selector mapping, clipping, addressed rule insertion,
  bridge normalization, solid/pattern rendering, and no-room retry are
  composed in `Rectangle Rule Producer And Renderer`. The mixed stream still
  lacks full live parser-to-allocator CPU memory capture for this producer.
- `0x105d0..0x13250`: delayed restore, gate outcomes, encoded object layout,
  bridge preservation, and mode `0..3` render contracts are composed in
  `Raster Transfer Gate And Encoded Rows`. The mixed stream still lacks live
  CPU/register memory across
  `0x12218 -> 0x105d0 -> 0x10084 -> 0x13070`, but its addressed raster object
  storage is pinned by fixture `addressed text/rule/raster field groups reach
  publication and render entry`.
- `0x10084..0x1381c`: first root allocation and stream-chunk allocation
  are modeled with exact side effects, including a multi-writer chunk
  rollover fixture in the shared allocator checkpoint, but not captured
  from live CPU memory for the complete text/rule/raster stream.
- `0xff1e..0x1ed84`: publication and render-entry are modeled and
  fixture-checked. Active-record selection through `0x1eb2a..0x1ed84`
  is covered by the published-render scheduler checkpoint, and the
  modeled `0x1ef6a` per-band merge carries a patterned rule from band
  `0` to band `5`. Remaining gaps are live engine pacing and multi-band
  loop timing.

## Publication Commands To Rendered Page Records

Status: composed for six host-facing publication streams that carry an
already queued compact text object through parser dispatch, `0xff1e`
publication, `0x1ed84`/`0x1edc6` render-record copy, and `0x1ef6a` final row
rendering. The low-level queue and render mechanics are shared with
`Mixed Text/Rule/Raster Page Record`; this section names the command-family
publication contract.

Concept: reset, FF, page-size, orientation, paper-source, and copy-count
commands can all force publication of the current page record after a
printable byte has created a compact text bucket. The visible output is the
pre-command compact `!` page, while command-specific side effects update
firmware state around that publication. Fixtures pin this for direct modeled
streams, host-fetched `0xa904` streams, and addressed reset, FF, page-size,
orientation, paper-source, and copies records that materialize the compact
bucket through `0x1387c`/`0x1381c` before publication.

### Field Groups

- Canonical command streams:
  - reset: `! ESC E`, parser handlers `0xd04a`, `0xcc52`.
  - FF with line termination: `ESC &k2G! FF`, handlers `0xedf8`, `0xd04a`,
    `0xf0f0`.
  - page size: `! ESC &l1A`, handlers `0xd04a`, `0xfc74`.
  - orientation: `! ESC &l1O`, handlers `0xd04a`, `0x10220`.
  - paper source: `! ESC &l2H`, handlers `0xd04a`, `0xef62`.
  - copies: `! ESC &l2X FF`, handlers `0xd04a`, `0xeef0`, `0xf0f0`.
  Evidence: fixtures `publication streams tie parser handlers to page-record
  publication boundary` and `host-fetched publication streams reach parser and
  published rows`.
- Canonical published page-record fields:
  - bucket-root prefix for all six streams:
    `00 00 00 00 00 00 00 01 20 00 01`.
  - context-slot prefix for host-fetched publication streams:
    `(0x440946b4, 0)`.
  - published pool header defaults: state byte `+4 = 2`, environment byte
    `+7 = 0`, status bytes `+8/+0x0a = 0`, words `+0x16/+0x18/+0x1a = 0`,
    and published pointer `0x780ea6 = abstract page root`.
  - copy-count publication changes pool-header word `+0x0c` to `2`.
  Evidence: fixtures
  `host-fetched FF geometry and paper-source publications preserve 0xff1e pool
  header defaults` and
  `host-fetched copies publication preserves 0xeef0 pool header word`.
- Canonical addressed publication fields:
  - reset addressed stream `! ESC E` allocates one stream chunk at
    `0x00d08000`, links it from `root + 0x20`, and ends with
    `0x782a70 = 0x00d6`, `0x782a72 = 0x00d08000`,
    `0x782a76 = 0x00d0802a`.
  - FF addressed stream `ESC &k2G! FF` allocates one stream chunk at
    `0x00d09000`, links it from `root + 0x20`, and ends with
    `0x782a70 = 0x00d6`, `0x782a72 = 0x00d09000`,
    `0x782a76 = 0x00d0902a`.
  - page-size addressed stream `! ESC &l1A` allocates one stream chunk at
    `0x00d0a000`, links it from `root + 0x20`, and ends with
    `0x782a70 = 0x00d6`, `0x782a72 = 0x00d0a000`,
    `0x782a76 = 0x00d0a02a`.
  - orientation addressed stream `! ESC &l1O` allocates one stream chunk at
    `0x00d0b000`, links it from `root + 0x20`, and ends with
    `0x782a70 = 0x00d6`, `0x782a72 = 0x00d0b000`,
    `0x782a76 = 0x00d0b02a`.
  - paper-source addressed stream `! ESC &l2H` allocates one stream chunk at
    `0x00d0c000`, links it from `root + 0x20`, and ends with
    `0x782a70 = 0x00d6`, `0x782a72 = 0x00d0c000`,
    `0x782a76 = 0x00d0c02a`.
  - copies addressed stream `! ESC &l2X FF` allocates one stream chunk at
    `0x00d0d000`, links it from `root + 0x20`, and ends with
    `0x782a70 = 0x00d6`, `0x782a72 = 0x00d0d000`,
    `0x782a76 = 0x00d0d02a`.
  - all six addressed publication streams publish bucket object
    `00 00 00 00 00 00 00 01 20 00 01` followed by zero padding, preserve
    context slot `0x440946b4`, and render the same rows as the direct
    publication fixtures.
  Evidence: fixtures `addressed printable reset publishes rendered page
  record`, `addressed printable FF publishes rendered page record`, and
  `addressed page geometry publications render page records`, and
  `addressed paper-source and copies publications render page records`.
- Derived/cache command side effects:
  - page-size `ESC &l1A` leaves page code `6`, orientation `0`, active size
    `3030 x 2025`, top offset `90`, one pending text flush, one page
    finalization, page-change flag `1`, and print-engine status `0`.
  - orientation `ESC &l1O` leaves page code `6`, orientation `1`, active size
    `2025 x 3030`, vertical offset source `50`, top offset `100`, two pending
    text flushes, two page finalizations, page-change flag `1`, and
    print-engine status `0`.
  - paper-source selector `2` stores `0x80` at `0x782da6` and sets pending
    status byte `0x782998`; the addressed variant also leaves cursor x at
    packed `5`, cursor y at packed `92.1`, clears the current page root, and
    sets paper-source output/control bytes `0x780e8f = 0x80` and
    `0x780e26 = 1`.
  - copies selector `2` stores copy count `2` in `0x782da4`, then FF
    publication copies that value to pool-header word `+0x0c`; the addressed
    variant leaves cursor x/y at packed `28`/`21`, clears the current page
    root, keeps `page_root_present = 1`, and leaves `0x782990 = 0`.
  Evidence: fixtures `addressed page geometry publications render page
  records`, `host-fetched FF geometry and paper-source publications preserve
  0xff1e pool header defaults`,
  `addressed paper-source and copies publications render page records`, and
  `host-fetched copies publication preserves 0xeef0 pool header word`.
- Parser scratch:
  - all six host-fetched publication streams drain entirely from the modeled
    `0xa904` ring source and leave an empty ring.
  Evidence: fixture `host-fetched publication streams reach parser and
  published rows`.
- Unknown:
  - this cluster proves rendered rows, not physical printer output.

### Writers

- `0xd04a` writes the compact text page object before each publication
  command.
- `0xcc52`, `0xf0f0`, `0xfc74`, `0x10220`, `0xef62`, and `0xeef0` trigger
  command-family publication or state updates for reset, FF, page-size,
  orientation, paper source, and copies.
- `0xff1e` copies the current root into the published pool record, clears the
  current page root, writes state byte `+4 = 2`, and preserves command-specific
  pool-header fields such as copy count `+0x0c`.
- `0x1ed84` copies active published-record header fields, and `0x1edc6`
  copies bucket root, rule/fixed-list roots, and context slots into the render
  record.

### Readers And Consumers

- The parser dispatch table at `0x11774` routes the six streams to the handler
  lists above.
- `0xff1e` consumes the current page root and page-record bucket root.
- `0x1ed84`/`0x1edc6` consume the published pool record.
- `0x1ef6a` consumes the render record in call order
  `0x1ef86`, `0x1efc2`, `0x1f446`, `0x1f756`; each covered publication stream
  dispatches its compact bucket object to `0x1effe` with context slot `0`.

### Output Effect

All six publication streams render the same compact Line Printer `!` rows
from the pre-publication printable byte. Fixture
`published page records feed 0x1ed84 and 0x1ef6a render entry` asserts the
full row set, not just the prefix, for reset, FF, page-size, orientation,
paper-source, and copies. The reset, FF, page-size, orientation,
paper-source, and copies addressed fixtures also assert that their
materialized page records render those same rows after `0xff1e`.

### Confidence

High for parser handler order, `0xa904` host-fetch draining, published pool
header fields, command-specific page-size/orientation/copies/paper-source
side effects, render-record bridge fields, render-entry call order, and final
rows, including addressed allocator state for all six publication streams,
because each is fixture-pinned.

### Fixtures

- `publication streams tie parser handlers to page-record publication
  boundary`
- `host-fetched publication streams reach parser and published rows`
- `addressed printable reset publishes rendered page record`
- `addressed printable FF publishes rendered page record`
- `addressed page geometry publications render page records`
- `addressed paper-source and copies publications render page records`
- `host-fetched FF geometry and paper-source publications preserve 0xff1e pool
  header defaults`
- `host-fetched copies publication preserves 0xeef0 pool header word`
- `host-fetched publication streams preserve 0x1edc6 bridge contract`
- `published page records feed 0x1ed84 and 0x1ef6a render entry`

### Disassembly Evidence

- `generated/disasm/ic30_ic13_main_parser_loop_011774.lst`: parser dispatch.
- `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`: printable
  object path.
- `generated/disasm/ic30_ic13_esc_e_reset_00cc52.lst`: reset publication
  entry.
- `generated/disasm/ic30_ic13_page_size_handler_00fc74.lst`: page-size
  geometry and publication.
- `generated/disasm/ic30_ic13_orientation_handler_010220.lst`: orientation
  geometry and publication.
- `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`: publication.
- `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`:
  render-record bridge.
- `generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`: render-entry
  dispatch.

### Unresolved Middle Edges

- `0xff1e..0x1ed84`: final rows are fixture-backed for all six publication
  commands, but physical-device comparison remains outside the ROM-internal
  reproduction contract.

## Shared Page-Record Storage And Allocator

Status: anchored as the shared storage model beneath compact text, rule,
fixed-rule, raster, publication, and render-bridge fixtures. This section
collapses allocator concepts that were previously repeated in text,
rectangle, raster, and publication notes. The current checkpoint now
covers one state block with multiple writers crossing a stream-chunk
boundary before publication and render entry.

Concept: `0x10084` owns the current page/control root. `0x1381c` owns
the variable-size object stream under that root. `0x1387c`, `0x133aa`,
`0x136d2`, and the raster queue path consume the stream allocator and
link typed objects into canonical root fields. Publication and rendering
consume those root fields without changing their producer semantics.

### Field Groups

- Canonical page root:
  - `0x78297a`: current page/control root pointer.
  - root `+0x1c`: bucket-head array for compact text and raster objects.
  - root `+0x20`: head/link slot for 0x100-byte stream chunks.
  - root `+0x24`: rectangle/rule list head.
  - root `+0x28`: fixed-rule list head.
  - root `+0x2c..+0x68`: 16 current-font context slots.
  Evidence: fixtures
  `0x10084-modeled page-root allocation side effects`,
  `addressed stream page record materializes through 0xff1e and 0x1ed84`,
  `addressed page-record writers share 0x1381c across chunk rollover`,
  and disassembly `0x10084..0x1021e`.
- Firmware bookkeeping:
  - `0x782a70`: bytes remaining in the current stream chunk.
  - `0x782a72`: pointer to the current chunk link field.
  - `0x782a76`: next free byte in the current chunk.
  - `0x782c72`/`0x782c73`: pending latches cleared by first-root
    allocation after the `0x9ac2` wait hook.
  - `0x782990`: transient page-root byte cleared by `0x10084`.
  Evidence: fixture
  `0x1381c stream allocator chunks display-list storage`,
  `addressed page-record writers share 0x1381c across chunk rollover`,
  and disassembly
  `0x10096..0x100f8`, `0x1381c..0x13876`.
- Derived/cache producer keys:
  - `0x782a7c`: bucket index / list-order key.
  - `0x782a7d`: rule/fixed selector byte copied into object `+4`.
  - `0x782a7e`: compact coordinate or rule key copied into object `+6`.
  - `0x782a7a`/`0x782a7b`: compact text selector bytes used by
    `0x1387c` callers.
  Evidence: rule key writers `0x134d6`, fixed-rule key writer `0x137a2`,
  text bucket fixture `0x1387c address-aware bucket allocation uses
  0x1381c storage`, and rule-list fixtures for `0x133aa`/`0x136d2`.
- Canonical object fields:
  - compact/raster bucket objects: `+0` next pointer, `+4` selector or
    class byte, `+6` count/capacity, payload from `+8` or `+0a`.
  - rule/fixed objects: `+0` next pointer, `+4` bucket byte,
    `+5` selector/mode, `+6` key, dimensions or extent from `+8`.
  Evidence: fixtures
  `0x1387c address-aware bucket allocation uses 0x1381c storage`,
  `0x133aa address-aware rule-list insertion uses 0x1381c storage`,
  `0x136d2 address-aware fixed-list insertion uses 0x1381c storage`,
  `addressed page-record writers share 0x1381c across chunk rollover`,
  and `0x13070/0x13250 raster row queues encoded-span object`.
- Derived/cache render fields:
  - `0x783a20`, `0x783a22`, and `0x783a28` are render-band outputs of
    `0x1ef86`, not canonical page-record state.
  Evidence: fixture
  `0x1ef86 render band setup computes remainder and destination base`.
- Parser scratch:
  - none newly assigned in this allocator cluster. Parser scratch enters
    through upstream command records such as the raster delayed record
    documented in the mixed text/rule/raster section.
- Unknown:
  - exact ownership/lifetime of heap allocator `0x1710` chunks outside the
    page-record stream.
  - exact live scheduler handoff from a published pool record to the active
    render record.

### Writers

- `0x10084` writes `0x78297a`, clears `0x782a70`, seeds
  `0x782a72 = root + 0x20`, clears `0x782990`, and calls `0x10110`.
  It leaves `0x782a76` unchanged until `0x1381c` allocates a chunk.
- `0x10110` writes page code byte `+6`, status/flag fields
  `+8/+0a/+14`, dimension/band fields `+09/+16`, list heads
  `+20/+24/+28`, and selected current-font context slot `+2c`.
- `0x1381c` writes `0x782a70`, `0x782a72`, and `0x782a76`; on a new
  chunk it links the new chunk through the prior `0x782a72` target.
- `0x1387c` writes root `+0x1c` bucket heads and compact/raster bucket
  objects; it reuses matching selector objects while count `+6` is below
  capacity and links a new head when the matching object is full.
- `0x133aa` writes root `+0x24` and inserts rectangle/rule objects by
  bucket byte order. Equal bucket bytes insert after the existing equal
  node in the fixture.
- `0x136d2` writes root `+0x28` and inserts fixed-rule objects with the
  same ordered-list contract.
- `0xff1e` publishes these roots into pool-record fields, and `0x1edc6`
  copies them into render-record fields `+0x18`, `+0x1c`, and `+0x20`.

### Readers And Consumers

- Printable text queueing through `0xd04a`/`0x12f2e` consumes the current
  root and `0x1387c` bucket allocator.
- Rectangle fill through `0x10898` consumes the current root and inserts
  a rule node through `0x13386`/`0x133aa`.
- Raster transfer through `0x105d0` consumes the current root and queues
  encoded-span objects through the `0x13070`/`0x13250` producer shape.
- Publication through `0xff1e` consumes bucket/list/context root fields.
- Rendering through `0x1ed84`/`0x1edc6`/`0x1ef6a` consumes the published
  or active page record and dispatches compact, encoded-span, rule, and
  fixed-list objects.

### Output Effect

The allocator is not visible by itself. It determines object order,
bucket selection, and list roots consumed by visible rendering. The
addressed text/rule/raster fixture proves one chunk contains text object
`0x00d0c004`, rule object `0x00d0c02a`, and raster object `0x00d0c038`,
then the published render path composes those objects into the visible
rows. The separate allocator fixture proves first chunk allocation,
same-chunk reuse, and second-chunk linking.

The `addressed page-record writers share 0x1381c across chunk rollover`
fixture composes those allocator facts into one page-record state block:
`0x10084` seeds `0x782a72 = root + 0x20`, seven compact text writers
through `0x12f2e`/`0x1387c` allocate objects
`0x00d05004`, `0x00d0502a`, `0x00d05050`, `0x00d05076`,
`0x00d0509c`, `0x00d050c2`, and `0x00d05104`, then
`0x133aa` and `0x136d2` allocate rule/fixed objects at
`0x00d0512a` and `0x00d05138`. The stream links are
`root + 0x20 -> 0x00d05000 -> 0x00d05100`, and the final bookkeeping is
`0x782a70 = 0x00ba`, `0x782a72 = 0x00d05100`,
`0x782a76 = 0x00d05146`, with two stream-chunk allocations. Publication
through `0xff1e` preserves bucket index `0`; render entry
`0x1ef6a` dispatches all seven compact objects to `0x1effe` and produces
the `LINE_PRINTER` glyph-32 rows.

### Confidence

High for page-root creation side effects, stream allocator accounting,
bucket reuse/new-head behavior, rule/fixed insertion order, root
publication, and render-record field copies. Medium for heap allocator
chunk lifetime and scheduler handoff because fixtures model `0x1710`
results rather than executing the full heap and page scheduler.

### Fixtures

- `0x10084-modeled page-root allocation side effects`
- `0x10110 page-root initializer installs selected context slot`
- `0x10110 page-root initializer copies geometry fields`
- `0x1381c stream allocator chunks display-list storage`
- `0x1387c address-aware bucket allocation uses 0x1381c storage`
- `0x133aa address-aware rule-list insertion uses 0x1381c storage`
- `0x136d2 address-aware fixed-list insertion uses 0x1381c storage`
- `addressed stream page record materializes through 0xff1e and 0x1ed84`
- `addressed page-record writers share 0x1381c across chunk rollover`
- `addressed text/rule/raster field groups reach publication and render
  entry`

### Disassembly Evidence

- `generated/disasm/ic30_ic13_page_root_allocate_010084.lst`:
  `0x10084..0x1021e`
- `generated/disasm/ic30_ic13_display_list_helpers_013386.lst`:
  `0x13386..0x1387a` and `0x1387c..0x138de`
- `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`:
  compact text callers of `0x1387c`
- `generated/disasm/ic30_ic13_raster_object_queue_013070.lst`:
  encoded-span producer path
- `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst` and
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`:
  publication and render bridge consumers

### Unresolved Middle Edges

- `0x1710..0x1385e`: the heap allocation result is modeled; the internal
  heap free-list behavior behind `0x1710` is not lifted here.
- `0x10084..0x1381c`: first-root setup, same-chunk reuse, and
  second-chunk rollover are modeled, but not captured from live 68000
  memory during a dense parser-produced page.
- `0x13250..0x1381c`: raster encoded-span allocation is composed in `Raster
  Transfer Gate And Encoded Rows` and address-aware stream allocation is
  composed in this shared allocator checkpoint, but exact live
  register/memory state through the full raster producer remains unresolved.
  The exact closure boundary is `0x12218 -> 0x105d0 -> 0x10084 -> 0x13070`:
  parser scratch through the delayed `ESC *b#W` record and payload offset is
  known, and canonical output after `0x13070` is known, but the live CPU
  register/memory handoff into page-root allocation and encoded-row production
  still needs a trace or memory snapshot.
- `0x133aa..0x13472` and `0x136d2..0x13690`: ordered insertion is pinned
  for lower, higher, and equal bucket bytes; alternate no-room/failure
  returns need live CPU fixtures.
- `0xff1e..0x1ed84`: pool-record publication and render bridge are
  modeled, and `0x1eb2a..0x1ed84` active-record selection is now
  fixture-backed. Remaining scheduler work is engine pacing and
  multi-band loop timing around `0x1eba4..0x1ecd2`.

## Published Record To Active Render Scheduler

Status: anchored as a composition checkpoint from a published
page/control record to the active render-entry path. This checkpoint does
not claim full engine pacing; it pins the state handoff that selects the
source record, alternates render work records, prepares or reuses render
geometry, copies the selected source through `0x1ed84`/`0x1edc6`, and
reaches visible rows through `0x1ef6a`.

Concept: `0xff1e` publishes a page/control pool record through the
protected pool-head pointer `0x780ea6` and publication flag `0x782996`.
The scheduler cursor `0x780eaa` is initialized with the same pool base by
`0x3144..0x3162`, but later comes from the candidate-slot scan
`0x7ec6..0x7f90` and cursor-advance path `0x7722..0x779a`. The active
render scheduler copies `0x780eaa` into `0x780eae` at `0x1eb46`, selects
one of the two render work records at `0x7820c4` or `0x782128` through
`0x1ecd6`, stores that destination in `0x783a18`, then calls `0x1ed84`.
The render entry `0x1ef6a` later uses `0x783a18` as its current render
record.

### Field Groups

- Canonical source record fields:
  - `0x780ea6`: page/control pool-head pointer. It is written by
    `0xff1e` from source root longword `+0` and used by
    `0x7744..0x7750` as the protected head that `0x780eaa` cannot pass
    unless the current record is already state byte `+4 == 2`.
  - `0x780eaa`: scheduler cursor for the record selected for rendering.
    It is equal to `0x780ea6` only at pool init or when the linked cursor
    reaches the protected head again; candidate selection writes it from
    `0x780e6e[]` at `0x7f76..0x7f90`.
  - `0x780eae`: active source record consumed by `0x1ed84` and
    `0x1ee9e`.
  - source `+0x1c`, `+0x24`, `+0x28`, and `+0x2c..+0x68`: bucket array,
    rule list, fixed list, and context slots copied by `0x1edc6`.
  Evidence: fixtures
  `0x3144/0x7ec6/0x7712 page pool aliases feed scheduler cursor` and
  `0x1eb2a/0x1ecd6 selects published record for render entry`,
  disassembly `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`,
  `generated/disasm/ic30_ic13_page_pool_init_003100.lst`,
  `generated/disasm/ic30_ic13_page_pool_candidate_select_007ec6.lst`,
  `generated/disasm/ic30_ic13_page_pool_cursor_007612.lst`, and
  `generated/disasm/ic30_ic13_active_render_scheduler_01eb2a.lst`.
- Canonical render work fields:
  - `0x7820bc`: render work-record alternator. Zero selects previous
    `0x7820c4`, destination `0x782128`, then stores `1`; nonzero selects
    previous `0x782128`, destination `0x7820c4`, then clears it.
  - `0x783a18`: active render work-record pointer used by `0x1ef6a`.
  - active-pool render work record fields consumed through aliases made
    by `0x2126`: long `+0` source base, words `+4` width longwords,
    `+6` modulo divisor, `+8`/`+0a` delta inputs, `+0c` start row,
    `+10` end row, and `+16` current engine row.
  - active-render scheduler work fields consumed at `0x1eba4..0x1ecd2`:
    word `+6` capacity/divisor, word `+0c` cleanup bound, word `+0e`
    throttle counter, word `+10` render-band cursor, and word `+16`
    engine-side cursor.
  - render `+0x18`, `+0x1c`, `+0x20`, and `+0x24..+0x60`: copied bucket,
    rule, fixed, and context slots.
  Evidence: `0x1ecd6..0x1ed76`,
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`,
  and fixture
  `0x2126/0x1a4c/0x2038 active pool copy window feeds engine rows`.
- Derived/cache render fields:
  - `0x780ea4`: active render/scheduler flag set at `0x1eb38` and
    cleared on some loop exits at `0x1ebba` or `0x1ebee`.
  - `0x780ea5`: loop/control flag cleared at `0x1eb40`, tested at
    `0x1eba4`.
  - `0x783a1c`: render stride cache written by `0x1ee9e` from render
    word `+4 << 2`.
  - `0x7839f8..`: 16-word offset table initialized by `0x1ee9e` from
    active source byte `+9`.
  - same-geometry destination `+8`: remainder from helper `0x33238`
    over `(previous +0x10 - previous +0x0a + previous +0x08) /
    previous +0x06`.
  - `0x7839ae`, `0x7839ca`, `0x7839b2`, `0x7839b6`, `0x7839c2`,
    `0x7839be`, `0x7839ba`, and `0x7839c6`: pointer aliases written
    by `0x2126` to the active-pool render work record fields above.
  - `0x7839ce`: derived row-source delta, written by `0x2126` as
    work word `+8 - +0x0a` and consumed by `0x2456`.
  - `0x78398e`: scan/status threshold from `0x0e + 2 * work word +0x0a`;
    `0x783996`/`0x783998`: row limit and last-row cache from
    `0x1a4c..0x1c00`.
  - `0x7839a4`: row-copy jump offset, equal to
    `(0x80 - width_longs) * 2`; `0x7839a8`: destination tail stride,
    equal to `(0x80 - width_longs) * 4`; `0x7839a0`: full source-row
    stride, equal to `width_longs << 5`.
  - `0x78399a`: destination row base for the eight-row copy helper;
    `0x783992`: current source pointer, first seeded by `0x1a4c..0x1c00`
    and then recomputed by `0x2456` through `0x2038`.
  Evidence: `generated/disasm/ic30_ic13_bitmap_state_setup_01ee9e.lst`
  and fixture destination-work fields in the geometry-change and
  same-geometry scheduler cases, plus
  `generated/disasm/ic30_ic13_engine_copy_pass_0022f4.lst`.
- Parser scratch:
  - none newly assigned here. The source record has already been built by
    parser/page-record producers before `0xff1e`.
- Firmware bookkeeping:
  - `0x780e6e[]`: candidate pointer slots scanned by `0x7ec6..0x7f90`;
    `0x1fd4..0x2016` shifts slots 0 through 4 toward slots 1 through 5
    and inserts the new candidate in slot 0. Accepted candidates are
    cleared from the slot after `0x780eaa` and `0x780eb2` are written.
  - pool-record state byte `+4`: `0x1c04` stages the current record as
    state `3`, `0x1eea` changes it to selectable state `4` when word
    `+0x0e` decrements to zero or pending state `2` otherwise, and
    `0x7f76..0x7f90` writes state `2` for the selected candidate.
  - `0x7821fb`: candidate-slot mask. `0x7ece..0x7ee6` computes scan
    limit `(0x7821fb & 0x7e) >> 1`, capped at six slots.
  - `0x780eb2`: release/advance cursor paired with `0x780eaa`.
    `0x7f76..0x7f90` writes it to the accepted candidate; `0x7760..0x779a`
    marks a state-2 record reusable and advances it through record `+0`.
  - `0x780eb6`: pool alias initialized with the same base at
    `0x3144..0x3162`; no stronger role is assigned yet.
  - `0x780e04`: engine/status counter copied into released pool record
    word `+0x10` at `0x778c`.
  - `0x7839d2`: immediate ready flag consumed by `0x21b8` before
    `0x1c04` may stage and insert the current `0x780eb2` record.
  - `0x7820c0` participates in the render loop's A4/A5 work-record
    selection before `0x1ec34`.
  - `0x78398c`: interrupt/scan counter incremented by `0x0fa2`.
    `0x1a4c..0x1c00` clears it before an active-pool copy window.
  - `0x783990`: copy phase. `0x1a4c..0x1c00` seeds it to `1`; `0x2038`
    increments it around `0x22f4` and resets it to `1` after phase `2`
    advances work word `+16`.
  - `0x78399e` and `0x78399f`: interrupt/status bytes cleared by
    `0x1a4c..0x1c00`. `0x0fa2..0x101e` sets `0x78399e` when the scan
    counter reaches threshold with no pending status; when `0x78399e`
    is still set on a later threshold-or-after interrupt, it clears
    `0x78399e`, sets `0x78399f`, and sets `0x7828f9.6`. `0x1db0`
    consumes and clears `0x78399e` after the status-copy pass; `0x1e44`
    consumes `0x78399f` to signal `0x780e2e` and enter `0x2038`.
  - `0x7839ac`: source-tail longword count consumed by `0x22f4..0x2454`
    after each copied row body.
  - `0x7828f9`: engine I/O shadow byte written to `$a801` by the
    `0x0fa2` interrupt path. Bit 7 toggles after the threshold and bit 6
    is set on pending-status escalation or beyond-last status. Helpers
    `0xa620`/`0xa638` clear/set bit 1, `0xa650`/`0xa668` clear/set bit
    6, and `0xa680` returns `D7 = 0` when bit 6 is set or `D7 = 1` when
    bit 6 is clear.
  - `0x780e32`, `0x780e36`, and `0x7821f9.2`: wrapper attention sources
    tested at `0x1d62..0x1d82`. Any of `(0x780e32 & 5)`,
    `(0x780e36 & 3)`, or `0x7821f9.2` sends `0x1cf8` to the `0x1e80`
    attention variant.
  - `0x780e6d`: active-pool attention/status flag set by `0x1e44`,
    `0x1e80`, and `0x1ea8`; `0x780e67`: timeout-class status byte set
    to `1` by `0x1ea8`.
  - `0x7820bc`, `0x780ea4`, `0x780ea5`, `0x780eaa`, `0x780eae`, and
    `0x783a18` are scheduler/render bookkeeping, not page-object fields.
  - wait-object records signaled by `0x1036` and selected by `0x123a`:
    long `+0` next pointer, word `+8` priority, word `+0a` scheduler
    state, word `+0c` wait argument, long `+0x12` restart payload,
    long `+0x16` private stack base, and long `+0x1a` saved stack
    pointer.
  - `0x78017e`: scheduler pending/event bits. Bit 1 is the wait-object
    pending bit set by `0x1036` and cleared by `0x1064` or `0x108e`
    before `0x123a` dispatch; bits 0, 2, and 3 are set/cleared by the
    timer/status trampoline around `0x0d52..0x0e86`.
  - `0x78017a`: pending wait-object pointer chosen by `0x1036`;
    `0x780176`: active wait-object pointer updated by `0x123a`;
    `0x780174`: active priority word copied from selected object `+8`.
- Unknown:
  - `0x7839d4`: cleared by `0x1a4c..0x1c00`; no stable role is assigned
    yet beyond active-pool copy-window bookkeeping.
  - exact physical engine pacing behind trap veneers `0x10bc`,
    `0x10c4`, `0x10c8`, `0x10d0`, `0x10d8`, `0x10e0`, and `0x10ec`.
  - complete multi-band timing and stop conditions across
    `0x1eba4..0x1ecd2`.

### Writers

- `0x3144..0x3162` initializes `0x780ea6`, `0x780eaa`, `0x780eae`,
  `0x780eb2`, and `0x780eb6` to pool base `0x780f02`.
- `0xff1e` writes state byte `+4 = 2`, copies root longword `+0` to
  `0x780ea6`, sets `0x782996 = 1`, and clears `0x78297a`.
- `0x21b8..0x223c` gates candidate staging. A ready `0x7839d2` returns
  nonzero; a timeout sets `0x780ea5`, `0x780e6c`, `0x780e6d`, and
  `0x780e67 = 2`, then signals `0x780e36` through `0x9ba2`.
- `0x1c32..0x1c54` marks the current `0x780eb2` record state byte
  `+4 = 3`, sets `0x780e6d` when record word `+0x14` is nonzero, runs
  the `0x2280` cursor helper, passes that record pointer as the argument
  to `0x1fd4`, and then continues engine/status helper calls at
  `0x1c5a..0x1c90`.
- `0x1ca0..0x1cea` writes the current staged record word `+0x10` from
  `0x780e04` plus the page/mode deadline delta.
- `0x1fd4..0x2016` shifts `0x780e6e[0..4]` into `0x780e6e[1..5]`,
  drops the previous slot 5, and writes the passed record pointer to
  `0x780e6e[0]`.
- `0x1eea..0x1f34` decrements the current `0x780eb2` record word
  `+0x0e`; zero changes state byte `+4` to selectable state `4` and
  advances `0x780eb2` through record longword `+0`, while nonzero leaves
  the current record as pending state `2`.
- `0x7f76..0x7f90` accepts a candidate slot from `0x780e6e[]` when the
  candidate record has state byte `+4 == 4` or word `+0x0e != 0`. It
  writes candidate state byte `+4 = 2`, increments word `+0x0e`, stores
  the candidate in `0x780eb2` and `0x780eaa`, then clears the slot.
- `0x7722..0x775a` advances `0x780eaa` through record longword `+0`
  when it equals `0x780eb2`. The guard at `0x7744..0x7750` prevents
  advancing the protected head `0x780ea6` unless current state byte
  `+4 == 2`.
- `0x7760..0x779a` releases the `0x780eb2` record when state byte
  `+4 == 2`: it writes state byte `+4 = 4`, clears word `+0x0e`,
  copies `0x780e04` into word `+0x10`, and advances `0x780eb2` through
  record longword `+0`.
- `0x1eb32..0x1eb50` sets `0x780ea4 = 1`, clears `0x780ea5`, and copies
  `0x780eaa` to `0x780eae` under the `0x15a6`/`0x15ac` critical section.
- `0x1ecd6..0x1ed0e` toggles `0x7820bc`, chooses destination work record
  `0x7820c4` or `0x782128`, and writes `0x783a18`.
- `0x1ed14..0x1ed22` copies active source byte `+9` into destination
  render word `+4`.
- `0x1ed6c..0x1ed76` calls `0x1ee9e` when geometry changes, then calls
  `0x1ed84` for active-record copy and bridge.
- `0x1ed36..0x1ed6a` reuses prior geometry when destination word `+4`
  matches previous word `+4`: helper `0x33238` computes the remainder
  into destination word `+8`, then previous long `+0` and word `+6` are
  copied before the shared `0x1ed84` exit.
- `0x2126..0x218e` selects the active-pool render work record from
  `0x7820c0`, writes the `0x7839ae/ca/b2/b6/c2/be/ba/c6` pointer
  aliases, and stores `0x7839ce = work +0x08 - work +0x0a`.
- `0x1a4c..0x1c00` clears `0x78398c`, seeds `0x78398e`, `0x783990`,
  `0x783996`, `0x783998`, `0x7839a8`, `0x7839a4`, `0x7839ac`,
  `0x78399a`, `0x78399e`, `0x78399f`, `0x7839a0`, and `0x7839d4`,
  and snapshots the current work word `+16` through alias `0x7839c6`.
- `0x2038..0x211c` consumes copy phase `0x783990`, source pointer
  `0x783992`, stride `0x7839a0`, work word `+16`, and work word `+10`.
  On copy phases it calls `0x22f4`, increments phase, and after phase `2`
  increments work word `+16` and resets phase to `1`; on ready rows it
  calls `0x2456` and stores the next `0x783992`; on done-active-source
  it sets `0x780ea5`.
- `0x22f4..0x2454` copies eight destination rows from `0x783992` to
  `0x78399a`, using `0x7839a4` to enter the longword-copy jump table,
  `0x7839a8` as destination tail stride, and `0x7839ac` as source-tail
  longword consumption.
- `0x2456..0x247a` computes the next source pointer as
  `base + (((row + 0x7839ce) % work +0x06) * work +0x04 << 6)`.
- `0x0fa2..0x101e` increments `0x78398c`. At or after `0x78398e`, it
  signals `0x780182` through helper `0x1036`; before `0x783998`, it
  sets pending byte `0x78399e` when no pending status exists. If
  `0x78399e` is already set, it clears `0x78399e`, sets `0x78399f`,
  sets `0x7828f9.6`, writes `$a801`, and signals `0x780182`.
- `0x0fc4..0x0fcc` toggles `0x7828f9.7` and writes `$a801` when the
  scan counter is after the threshold but not beyond the last row.
- `0xa620..0xa680` are shared `$a801` shadow helpers. `0xa620` clears
  `0x7828f9.1`, `0xa638` sets it, `0xa650` clears `0x7828f9.6`,
  `0xa668` sets `0x7828f9.6`, and `0xa680` tests bit 6 without writing.
- `0x1c5a..0x1c90` calls the `$a801` helpers while staging a candidate
  record, and `0x1d42`, `0x1e80`, and `0x1ea8` consume helper
  `0xa680`/`0xa668` during wrapper/attention/timeout paths.
- `0x1036..0x1062` is the shared wait-object signal helper used by the
  scan/status and scheduler loops. When target word `+0x0a == 0x8006`,
  it writes `+0x0a = 2`, sets `0x78017e.1`, and writes `0x78017a` to
  the target pointer if no wait object was pending or if the new target
  pointer is lower than the existing `0x78017a`.
- `0x1064..0x108c` and `0x108e..0x10ba` are interrupt-exit drain paths.
  If the saved SR interrupt mask is zero and `0x78017e.1` was set, they
  clear bit 1, load `A1` from `0x78017a`, save all registers, and enter
  scheduler dispatch at `0x123a`.
- `0x123a..0x1282` is the wait-object priority switch. If
  `0x780174 < target +8`, it marks the current object from `0x780176`
  as state `2`, saves the current stack at current `+0x1a`, finds a
  state-2 object, writes `0x780176` and `0x780174`, marks selected
  `+0x0a = 0xff`, restores `A7` from selected `+0x1a`, and returns by
  `RTE`.
- `0x10bc..0x10f2` are trap veneers. `0x10bc`, `0x10c8`, `0x10e0`, and
  `0x10ec` load `A1` from the first stack argument; `0x10d0`,
  `0x10d8`, and `0x10e0` load `D0` from a word argument; the veneers
  execute traps `#0` through `#6`.
- Copied vector-table slots 32 through 39 route traps `#0..#7` to
  `0x1144`, `0x1154`, `0x1174`, `0x118a`, `0x11be`, `0x11ca`,
  `0x11e8`, and `0x11f8`.
- Trap `#0` handler `0x1144..0x1152` wakes a target in state
  `0x8006` by writing target word `+0x0a = 2`, then enters
  `0x123a`.
- Trap `#1` handler `0x1154..0x1170` blocks the current object from
  `0x780176` as state `0x8006`, writes `D0` to word `+0x0c`, saves
  `A7` at long `+0x1a`, and enters the `0x125a` ready-object scan.
- Trap `#2` handler `0x1174..0x1188` is the sibling block-current
  path for state `0x8007`, sharing the `D0` and saved-stack writes at
  `0x1168..0x1170`.
- Trap `#3` handler `0x118a..0x11ba` first changes a target in state
  `0x8006` to state `2`, then blocks the current object as state
  `0x8006` with `D0` in `+0x0c`, and enters `0x125a` starting from
  wait object `0x780182`.
- Trap `#5` handler `0x11ca..0x11e6` marks a nonzero, non-active target
  state as `9`; if the target is state `0xff`, it falls into the
  current-object yield path at `0x111c`.
- Trap `#6` handler `0x11e8..0x11f6` wakes a target in state `9` by
  entering the same `0x1230..0x123a` path used by trap `#0`.
- Trap `#7` handler `0x11f8..0x122e` clears a non-active target state
  to `0`, builds a stack frame from target `+0x12` and `+0x16`, writes
  target `+0x1a`, and returns; if the target is the current active
  object, it falls into the current-object yield path at `0x111c`.
- `0x1db0..0x1e40` consumes pending byte `0x78399e`: phase `1` with
  work word `+16 < +10` computes `0x783992` through `0x2456`, calls
  `0x22f4`, increments `0x783990`, and clears `0x78399e`; later phases
  add `0x7839a0`, call `0x22f4`, and after phase `2` increment work
  word `+16` and reset phase to `1`.
- `0x1e44..0x1e7c` consumes escalated byte `0x78399f`: when nonzero, it
  sets `0x780e6d`, signals bit `1` at `0x780e2e` through `0x9ba2`, and
  then enters `0x2038`.
- `0x1cf8..0x1dac` dispatches one active-pool wrapper cycle. Elapsed
  `0x780e04 - start >= 0x191` calls `0x1ea8` and returns `D7 = 0`;
  pending `0x78399e` calls `0x1db0` before continuing to the engine-ready
  decision; helper `0xa680` returning zero calls `0x1e44` and returns
  `D7 = 1`; attention bits call `0x1e80` and return `D7 = 0`; otherwise
  it waits through `0x10e0(0x7801a2, 3)` and loops.
- `0x1e80..0x1ea6` is the attention variant. It calls `0xa668`, sets
  `0x780e6d = 1`, then enters `0x2038`.
- `0x1ea8..0x1ee8` is the timeout variant. It calls `0xa668`, sets
  `0x780e6d = 1`, sets `0x780e67 = 1`, signals bit `1` at `0x780e36`
  through `0x9ba2`, then enters `0x2038`.
- `0x1eba4..0x1ecd2` runs the active-render scheduler loop. If
  `0x780ea5 == 1`, it calls `0x1ef38`, clears `0x780ea4`, and signals
  `0x780182` through `0x10c8` and `0x10c4`; if active work word
  `+0x0c < +0x10`, it repeats that clear/signal sequence.
- `0x1ec0c..0x1ec30` throttles the loop when active work word `+0x0e`
  exceeds `0x28`: it clears `+0x0e`, signals `0x780182`, calls
  `0x10d8(2)`, and loops.
- `0x1ec34..0x1ec8e` computes render capacity as active work
  `+6 - (+10 - +16)`, subtracting paired work `(+10 - +16)` when
  `0x7820bc != 0x7820c0`.
- `0x1ec98..0x1ecac` calls render entry `0x1ef6a` when computed
  capacity is at least `9`, then increments active work word `+0x10`
  and throttle word `+0x0e`.
- `0x1ecb0..0x1ecd2` handles computed capacity below `9`: it clears
  active work word `+0x0e`, signals `0x780182`, calls `0x10d0(2)`, and
  loops.

### Readers And Consumers

- `0x3bb8..0x3bd6` reads `0x780eaa + 4` for a state-byte status path.
- `0x3bf6..0x3c26` reads `0x780ea6 + 4` for the matching protected-head
  status path.
- `0x3cf0..0x3d5a` reads fields from the current `0x780eaa` record for
  status/environment propagation.
- `0x8066..0x80cc` reads `0x780eaa`, sets record byte `+8 = 1`, and
  walks linked records for a cleanup/status path.
- `0x1eb46` reads `0x780eaa` and writes it to `0x780eae`.
- `0x1958..0x1984` consumes the return from `0x1c04`; a nonzero return
  runs `0x1cf8` and `0x1eea`, while a zero return skips those release
  steps and goes directly to the `0x1fa2` cleanup/error path.
- `0x7ec6..0x7f90` consumes selectable records from `0x780e6e[]` after
  the staged record has been released to state `4` or has nonzero word
  `+0x0e`.
- `0x1ed84` reads `0x780eae`, source words `+0x18/+0x1a`, and source
  queues/context slots through `0x1edc6`.
- `0x1ee9e` reads active source byte `+9` through `0x780eae`, render
  word `+4`, and global bitmap buffer fields `0x7810b4`/`0x7810b8`.
- `0x1ef6a` reads `0x783a18`, then consumes the render work record
  through `0x1ef86`, `0x1efc2`, `0x1f446`, and `0x1f756`.
- `0x19d2..0x1a2e` waits on alias fields before entering
  `0x1a4c..0x1c00`: it compares work word `+6`, work word `+10`, and
  work word `+16` through the `0x7839b2/ba/c6` aliases.
- `0x0fa2..0x101e` reads `0x78398e`, `0x783998`, and pending byte
  `0x78399e` while producing the next status state.
- `0x1036..0x1062` reads the signaled object's word `+0x0a` and
  compares the target pointer against `0x78017a` when `0x78017e.1` was
  already set.
- `0x1064..0x108e` reads the saved SR mask and `0x78017e.1` to decide
  whether to return immediately or dispatch the queued object from
  `0x78017a`.
- `0x123a..0x1282` reads `0x780174`, `0x780176`, target word `+8`,
  object state word `+0x0a`, linked object `+0`, and saved stack
  longword `+0x1a` while selecting the active wait object.
- Trap veneers `0x10bc`, `0x10c8`, `0x10e0`, and `0x10ec` consume a
  target-object argument; `0x10d0`, `0x10d8`, and `0x10e0` consume a
  word argument before entering their trap.
- Trap handlers `0x1144..0x11f8` consume copied vector slots 32 through
  39 as traps `#0..#7`; traps `#0`, `#3`, and `#6` read target word
  `+0x0a` before deciding whether to wake it, trap `#4` returns target
  word `+0x0a` in `D7`, trap `#5` branches on target word `+0x0a`,
  and trap `#7` reads target `+0x0a`, `+0x12`, and `+0x16`.
- Trap handlers `#1`, `#2`, `#3`, `#5` in the `0xff` case, and `#7`
  in the active-target case read `0x780176` as the active wait object
  before blocking or yielding it through the shared `0x125a` scan.
- `0x1cf8..0x1d36` tests `0x78399e`; when it is nonzero, the wrapper
  drops the critical section and calls `0x1db0`.
- `0x1db0..0x1e40` is a sibling copy/pacing helper: it consumes
  `0x783990`, `0x783992`, `0x7839a0`, `0x7839c6`, `0x7839ba`, and
  status byte `0x78399e`, then calls the same `0x22f4` row-copy helper
  and clears `0x78399e`.
- `0x1e44..0x1e7c` reads escalated byte `0x78399f`; `0x1cf8..0x1d58`
  reaches it when the engine-ready helper `0xa680` returns zero.
- `0x1cf8..0x1dac` reads `0x780e04`, `0x78399e`, the return from
  `0xa680`, `0x780e32`, `0x780e36`, and `0x7821f9.2` to select
  `0x1db0`, `0x1e44`, `0x1e80`, `0x1ea8`, or the `0x10e0` wait loop.
- `0x1eba4..0x1ecd2` reads `0x780ea5`, `0x7820bc`, `0x7820c0`, and
  active/paired render work words `+6`, `+0c`, `+0e`, `+10`, and `+16`
  to select cleanup, throttle, render, or capacity-wait outcomes.

### Output Effect

The fixture `0x1eb2a/0x1ecd6 selects published record for render entry`
uses the addressed stream page/control record that contains one compact
bucket, one rule list, one fixed list, and context slot `0x440946b4`.
It selects source pointer `0x00d0eaa0`, copies it into `0x780eae`,
switches `0x7820bc` from `0` to `1`, selects render work record
`0x782128`, stores `0x783a18 = 0x782128`, marks geometry changed, and
then renders the same rows as the direct published-record
`0x1ed84`/`0x1ef6a` fixture.

The companion fixture `0x1ecd6 same-geometry render work reuse reaches
render entry` starts with `0x7820bc = 1`, selects previous record
`0x782128`, destination `0x7820c4`, and takes the `0x1ed36..0x1ed6a`
same-geometry branch. With previous `+0x10 = 17`, `+0x0a = 3`,
`+0x08 = 4`, and divisor `+0x06 = 5`, helper `0x33238` stores remainder
`3` in destination word `+8`; render setup then produces
`0x783a22 = 3`, `0x783a20 = 0x0020`, and
`0x783a28 = 0x00103800`, while still reaching the same composed rows.

The pool-cursor fixture
`0x3144/0x7ec6/0x7712 page pool aliases feed scheduler cursor` starts
with pool base `0x00780f02`, candidate slot `0x780e6e[0] =
0x00780f6e`, and scan mask `0x7821fb = 0x02`. It proves init stores the
base into `0x780ea6`, `0x780eaa`, `0x780eae`, `0x780eb2`, and
`0x780eb6`; candidate selection accepts slot zero, writes
`0x780eaa = 0x780eb2 = 0x00780f6e`, sets selected record byte `+4 = 2`,
and increments word `+0x0e` to `1`. The same fixture then proves
`0x7722..0x779a` advances both cursors to `0x00780fda`, releases the
selected record back to state byte `+4 = 4`, clears word `+0x0e`, and
copies `0x780e04 = 0x1234` into word `+0x10`. Its protected-head variant
keeps `0x780eaa = 0x780ea6 = 0x00780f02` when state byte `+4 = 1`.

The staged active-pool fixture
`0x1958/0x1c04/0x1eea staged candidate reaches render scheduler` starts
with current `0x780eb2 = 0x00d0f100`, record state byte `+4 = 2`, word
`+0x0e = 1`, word `+0x14 = 3`, engine counter `0x780e04 = 0x2000`,
ready flag `0x7839d2` asserted, and six candidate slots
`0x00d0f000..0x00d0f050`. It proves `0x1c04` marks the record state
byte `+4 = 3`, sets `0x780e6d = 1`, calls the `0x2280` cursor helper,
and inserts the candidate through `0x1fd4..0x2016`, producing slot
vector `0x00d0f100, 0x00d0f000, 0x00d0f010, 0x00d0f020,
0x00d0f030, 0x00d0f040`. It also proves the `0x1ca0` deadline write
`word +0x10 = 0x2114`. The modeled `0x1eea` release decrements
word `+0x0e` to zero, changes state byte `+4` to selectable state `4`,
and advances `0x780eb2` to `0x00d0f000`; `0x7ec6..0x7f90` then
promotes slot 0 into `0x780eaa = 0x780eb2 = 0x00d0f100`. The selected
pointer reaches `0x1eb46`, `0x1ecd6`, and the same `0x1ed84`/`0x1ef6a`
rows as the published-record render fixtures. The same fixture includes
the timeout side of `0x21b8`: elapsed `0x321` sets `0x780ea5`,
`0x780e6c`, `0x780e6d`, and `0x780e67 = 2`, signals `0x780e36`, returns
zero to `0x1c04`, and leaves `0x780e6e[]` unchanged.

The copy-window fixture
`0x2126/0x1a4c/0x2038 active pool copy window feeds engine rows` starts
with selector `0x7820c0 = 1`, so `0x2126` selects work record
`0x00782128`. Its work fields are long `+0 = 0x00102000`,
word `+4 = 0x20`, word `+6 = 5`, word `+8 = 4`, word `+0a = 2`,
word `+0c = 3`, word `+10 = 5`, and word `+16 = 3`. The fixture proves
`0x7839ce = 2`, `0x78398e = 0x12`, `0x783996 = 0x18`,
`0x783998 = 0x17`, `0x7839a8 = 0x180`, `0x7839a4 = 0xc0`,
`0x7839a0 = 0x400`, and both `0x78399e/9f` clear. The first
`0x2038` call takes the ready-for-copy path and computes
`0x783992 = 0x00102000` through `0x2456`. The phase-2 call advances
`0x783992` to `0x00102400`, calls `0x22f4`, copies eight rows of
`0x20` longwords from `0x00102400` to `0x00ffc000`, steps source rows
by `0x80`, steps destination rows by `0x200`, then increments work
word `+16` to `4` and recomputes `0x783992 = 0x00102800`. Row 0 is
source `0x00102400` to destination `0x00ffc000`; row 7 is source
`0x00102780` to destination `0x00ffce00`. With word `+16 = 5`,
elapsed `0xc9`, and `0x780eae == 0x780eb2`, the done path sets
`0x780ea5 = 1`.

The status-feedback fixture
`0x0fa2/0x1db0/0x1e44 status feedback drives copy and done flag` starts
from the same work-record geometry. With `0x78398c = 0x11`,
`0x78398e = 0x12`, `0x783998 = 0x17`, and no pending status,
`0x0fa2` increments the counter to `0x12`, sets `0x78399e = 1`, leaves
`0x78399f = 0`, leaves `0x7828f9 = 0`, and signals helper `0x1036`
with target `0x780182`. `0x1db0` then consumes that pending status:
phase `1`, work word `+16 = 3`, and work word `+10 = 5` compute
`0x783992 = 0x00102000`, call `0x22f4`, copy eight `0x20`-longword
rows from `0x00102000` to `0x00ffc000`, advance phase to `2`, leave
word `+16 = 3`, and clear `0x78399e`.

The same fixture covers the escalated status side. With
`0x78398c = 0x12`, `0x78399e = 1`, and `0x7828f9 = 0`, `0x0fa2`
increments to `0x13`, toggles `0x7828f9.7`, writes `$a801 = 0x80`,
clears `0x78399e`, sets `0x78399f = 1`, sets `0x7828f9.6`, writes
`$a801 = 0xc0`, and signals `0x780182`. `0x1e44` then sees
`0x78399f = 1`, sets `0x780e6d = 1`, signals bit `1` at `0x780e2e`
through `0x9ba2`, and enters `0x2038`; with work word `+16 = 5`,
elapsed `0xc9`, and `0x780eae == 0x780eb2`, that call sets
`0x780ea5 = 1`. The fixture intentionally leaves `0x78399f` set,
matching the observed `0x1e44` code, which tests but does not clear it.

The scheduler handoff fixture
`0x1036/0x108e/0x123a wait-object scheduler handoff` starts with wait
object `0x780182` in state word `+0x0a = 0x8006`, priority `3`, and
saved stack `0x00ff1000`; active object `0x7801a2` has priority `1`.
Helper `0x1036` changes `0x780182 +0x0a` to `2`, sets `0x78017e.1`,
and writes `0x78017a = 0x780182`.

The same fixture then runs the `0x108e` exit path with saved SR mask
zero. It clears `0x78017e.1`, dispatches `0x780182` through `0x123a`,
marks previous active object `0x7801a2 +0x0a = 2`, saves stack
`0x00ffe000` at `0x7801a2 +0x1a`, selects `0x780182` into
`0x780176`, raises `0x780174` from `1` to `3`, marks selected
`+0x0a = 0xff`, and restores stack `0x00ff1000`. The masked side uses
helper `0x1064` with saved SR mask `0x0700` and proves it leaves
`0x78017e.1` pending without dispatch. The trap-veneer side pins
`0x10c8(0x780182)` to trap `#2`, `0x10c4` to trap `#1`,
`0x10d0(2)` to trap `#3`, `0x10d8(2)` to trap `#4`, and
`0x10e0(0x7801a2, 3)` to trap `#5`.

The trap-handler fixture
`0x1144..0x11f8 scheduler trap handlers update wait objects` maps copied
vector-table slots 32 through 39 to handlers `0x1144`, `0x1154`,
`0x1174`, `0x118a`, `0x11be`, `0x11ca`, `0x11e8`, and `0x11f8`.
Trap `#0` wakes target `0x780202` from state `0x8006` and, through
`0x123a`, selects it as active with priority `4` and saved stack
`0x00ff3000`; the previous active object `0x7801a2` is left state `2`
with saved stack `0x00ffe000`.

In the same fixture, trap `#1` blocks current object `0x7801a2` as
state `0x8006`, stores wait argument `2`, saves stack `0x00ffe100`,
and selects ready object `0x780182`. Trap `#2` follows the same path but
uses state `0x8007` and wait argument `3`. Trap `#3` wakes target
`0x780202` from state `0x8006` to `2`, blocks current object
`0x7801a2` as state `0x8006` with argument `7`, then selects
`0x780182` from the hard-coded scan start.

Trap `#4` returns target state `9` in `D7`. Trap `#5` changes target
`0x780202` from state `0x8006` to state `9`. Trap `#6` wakes that
state-9 target and selects it through `0x123a`, leaving previous active
`0x7801a2` in state `2`. Trap `#7` clears non-active target
`0x780202` from state `0x8006` to `0` and writes saved stack
`0x00ff6fbe`, computed from target stack base `0x00ff7000` minus the
ROM's `4 + 2 + 0x3c` frame allocation.

The wrapper-dispatch fixture
`0x1cf8/0x1e80/0x1ea8 wrapper dispatch selects engine variants` composes
the status-copy path with the remaining wrapper exits. With elapsed
`0x10`, pending `0x78399e = 1`, helper `0xa680` modeled as nonzero, and
`0x780e32 = 4`, `0x1cf8` first calls `0x1db0`; that computes source
`0x00102000`, copies one eight-row pass, clears `0x78399e`, and advances
phase from `1` to `2`. The same wrapper pass then selects `0x1e80`,
calls `0xa668`, sets `0x780e6d = 1`, enters `0x2038`, copies the
phase-2 pass, increments work word `+16` from `3` to `4`, resets phase
to `1`, recomputes `0x783992 = 0x00102800`, and returns `D7 = 0`.

The timeout side starts with elapsed `0x191` and work word `+16 = 5`.
It selects `0x1ea8`, calls `0xa668`, sets `0x780e6d = 1`, sets
`0x780e67 = 1`, signals bit `1` at `0x780e36`, enters `0x2038`, and
sets `0x780ea5 = 1` on the done-active-source path before returning
`D7 = 0`. The bridge side models helper `0xa680` as zero with
`0x78399f = 1`; `0x1cf8` calls `0x1e44`, which signals `0x780e2e`,
enters `0x2038`, sets `0x780ea5 = 1`, and returns `D7 = 1`. The wait
side models helper `0xa680` as nonzero with `0x780e32 = 0`,
`0x780e36 = 0`, and `0x7821f9.2 = 0`; it calls
`0x10e0(0x7801a2, 3)` and loops without producing a terminal `D7` in the
bounded fixture.

The scheduler-loop fixture
`0x1eba4/0x1ef6a active render loop advances or yields bands` starts
with active selector `0x7820bc = 1`, so the active work record is
`0x00782128`, and paired selector `0x7820c0 = 0`, so the paired record is
`0x007820c4`. In the render case, active `+6 = 20`, active
`+10 - +16 = 3`, and paired `+10 - +16 = 3`, so computed capacity is
`14`. The loop calls `0x1ef6a`, increments active word `+10` from `3`
to `4`, and increments throttle word `+0e` from `7` to `8`.
The downloaded-glyph scheduler fixture
`0x1eba4 scheduler band words render published downloaded glyph` starts
from the `0xff1e`/`0x1ed84` seed where source `+0x18` and render words
`+0x10/+0x16` are zero, produces ten render calls with
`word_10_before = 0..9`, leaves the work record at `+0x10 = 10`, and feeds
those scheduler-produced band words into the copied published downloaded-glyph
record. Only published buckets `1` and `9` dispatch compact objects; bucket
`9` still produces page row `86`.

The capacity-wait side uses active `+6 = 10`, active remaining `4`, and
paired remaining `1`, producing capacity `5`. It clears active word
`+0e` from `6` to `0`, signals `0x780182` through `0x10c8`, and calls
`0x10d0(2)`. The cleanup/throttle side starts with `0x780ea5 = 1`,
active `+0c = 1`, active `+10 = 2`, and active `+0e = 0x29`. It records
the loop-flag cleanup through `0x1ef38`, clears `0x780ea4`, signals
`0x10c8`/`0x10c4`, records the row-bound cleanup and repeats that
signal pair, then clears active word `+0e` and calls `0x10d8(2)`.

### Confidence

High for the distinction between protected pool head `0x780ea6` and
scheduler cursor `0x780eaa`, the candidate selection stores into
`0x780eaa`/`0x780eb2`, the `0x1fd4` candidate-slot insertion shift, the
`0x1c04` state-3 staging boundary, the `0x1eea` state-4 release path,
the protected-head skip, `0x780eaa -> 0x780eae`, `0x780ea4/5`, the
two-work-record alternation, `0x783a18`, the `0x2126` pointer aliases,
the `0x1a4c` copy-window scalars, the `0x22f4` row-copy address pattern,
the `0x2456` source-address arithmetic, the `0x0fa2` threshold and
pending-status transitions, the `0x1036` wait-object signal helper, the
`0x1064`/`0x108e` pending-drain predicates, the `0x123a` priority-switch
state updates, the copied trap vector map for traps `#0..#7`, the
`0x10bc..0x10f2` trap-veneer argument shapes, the
`0x1144..0x11f8` trap-handler wait-state transitions, the
`0x1db0` status-copy path, the `0x1e44` escalated-status bridge, the
`0x1cf8` wrapper branch predicates, the `0x1e80` attention variant, the
`0x1ea8` timeout variant, the `0x1eba4` cleanup, throttle, capacity, and
render-call branch predicates, the `0x1ee9e` geometry-change boundary,
the `0x1ed36..0x1ed6a` same-geometry reuse branch, and the render-entry
output for the selected source. Medium for the surrounding engine pacing
loop because the fixture models firmware wait-state semantics but still
does not name the board-level source of the interrupt/MMIO events that
drive those states. High for `0x7828f9` bit 1/6 helper side effects,
`0xa668`, and `0xa680` return polarity because the fixture covers set,
clear, and test cases. Medium for the physical meaning of `$8000`,
`$a601`, `$a801`, and `$aa01` because the byte-level side effects and
branch returns are pinned but not tied to measured engine timing yet.
Medium for `0x780eb6` because only its initialization is currently
covered.

### Fixtures

- `0x1eb2a/0x1ecd6 selects published record for render entry`
- `0x1ecd6 same-geometry render work reuse reaches render entry`
- `0x3144/0x7ec6/0x7712 page pool aliases feed scheduler cursor`
- `0x1958/0x1c04/0x1eea staged candidate reaches render scheduler`
- `0x2126/0x1a4c/0x2038 active pool copy window feeds engine rows`
- `0x0fa2/0x1db0/0x1e44 status feedback drives copy and done flag`
- `0x1036/0x108e/0x123a wait-object scheduler handoff`
- `0x1144..0x11f8 scheduler trap handlers update wait objects`
- `0xa620/0xa668/0xa6cc engine shadow and byte bridge`
- `0x1cf8/0x1e80/0x1ea8 wrapper dispatch selects engine variants`
- `0x1eba4/0x1ef6a active render loop advances or yields bands`
- `0x1eba4 scheduler band words render published downloaded glyph`
- `addressed stream page record materializes through 0xff1e and 0x1ed84`
- `published page records feed 0x1ed84 and 0x1ef6a render entry`

### Disassembly Evidence

- `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`:
  `0x10060..0x10080`
- `generated/disasm/ic30_ic13_active_pool_cycle_001958.lst`:
  `0x1958..0x1fa2`
- `generated/disasm/ic30_ic13_scan_status_interrupt_000f84.lst`:
  `0x0f84..0x10f2`
- `generated/disasm/ic30_ic13_a801_a601_io_00a4e8.lst`:
  `0xa620..0xa680` for `$a801` bit helpers and `0xa6cc..0xa810` for
  the alternate ring/status bridge.
- `generated/disasm/ic30_ic13_scheduler_trap_handlers_00110c.lst`:
  `0x110c..0x1282`
- `generated/disasm/ic30_ic13_scheduler_dispatch_00123a.lst`:
  `0x123a..0x1282`
- `generated/disasm/ic30_ic13_page_pool_candidate_insert_001c04.lst`:
  `0x1c04..0x2016`
- `generated/disasm/ic30_ic13_active_pool_engine_gate_002038.lst`:
  `0x2038..0x223c`
- `generated/disasm/ic30_ic13_engine_copy_pass_0022f4.lst`:
  `0x22f4..0x247a`
- `generated/disasm/ic30_ic13_page_pool_init_003100.lst`:
  `0x3144..0x3162`
- `generated/disasm/ic30_ic13_page_pool_candidate_select_007ec6.lst`:
  `0x7ece..0x7f90`
- `generated/disasm/ic30_ic13_page_pool_cursor_007612.lst`:
  `0x7722..0x779a`
- `generated/disasm/ic30_ic13_active_render_scheduler_01eb2a.lst`:
  `0x1eb2a..0x1ed84`
- `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`:
  `0x1ed84..0x1ee9c`
- `generated/disasm/ic30_ic13_bitmap_state_setup_01ee9e.lst`:
  `0x1ee9e..0x1ef38`
- `generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`:
  `0x1ef6a..0x1effc`

### Unresolved Middle Edges

- `0x0f84..0x0fa0` and `0x1020..0x102e`: `$8000.4` selection between
  scan/status handling and helper `0xa6cc`, plus the physical effect and
  timing of `$a601 = 0xfd`, `$a801`, `$aa01`, `0xfffe0001`, and
  `0xfffe0003`, still need board-level engine correlation.
- `0x10bc..0x11f8` and `0x123a..0x1282`: trap veneers, copied trap
  vectors, wait-state transitions, and scheduler selection are modeled;
  the remaining gap is the timing relation between those firmware
  wait-states and the physical engine/MMIO events that wake them.
- `0x1cf8..0x1ea8`: helper return predicates around `0xa668` and
  `0xa680` are modeled; the unresolved edge is the external engine
  timing that makes `0x7828f9.6` ready or busy in real hardware.

## Vertical Forms Control

Status: anchored as a command-family checkpoint. The table definition path, its
immediate text-bottom effect, the forward in-text channel-jump path, the before-top
forward channel-jump normalization path, the selector-zero target-equal path, the
selector-zero top-of-form page-eject path, and one wrap-hit page-eject path are modeled.
The wrap no-hit top-of-form page eject path, one publishing target-after-text
bottom-recovery path, and one non-publishing target-after-text bottom-recovery path are
also modeled. The start-after-text no-wrap bottom-recovery path is modeled for start
line `64` with an empty table, the start-after-text wrap-after-text path is modeled for
default-table line-1 placement and line-63 bottom recovery, and selector-zero
start-after-text top-of-form recovery is modeled for start line `64`. Alternate
high-start entries are also modeled for start line `80`: no-hit bottom recovery, wrapped
line-70 bottom recovery, and selector-zero top-of-form recovery. The `0x12b96`
default-table bit convention is now pinned by channel selector. The tracked contract
note is `notes/vertical-forms-control.md`.

Concept: vertical forms control is a per-line, 16-channel stop table used
by `ESC &l#W` definitions and consumed by `ESC &l#V` vertical channel
jumps. It affects visible output by changing the text-length bottom cache,
moving the vertical cursor before later printable bytes are queued, and
publishing a current page record when selector zero reaches the
top-of-form page-eject path.

### Field Groups

- `0x782dde..0x782edd`: canonical VFC table.
  Semantic role: 128 16-bit VFC channel words, two payload bytes per
  line. `0x1280a` maps selector `n` to bit `n - 1`, so channel numbers
  are the PCL selector numbers. In the `0x12b96` default table, channel
  1 marks line `0`; channel 2 marks `text_last_line - 1` and
  `text_last_line`; channel 3 marks every active text line plus
  `last_line`; channel 4 marks even lines; channel 5 marks multiples of
  `3`; channel 6 marks line `0` and half-text line; channel 7 marks
  line `0`, half-text, quarter-text, and three-quarter-text lines;
  channel 8 marks multiples of `10`; channel 9 marks `text_last_line`;
  channels 10 and 11 are not set by this builder; channel 12 marks line
  `0`; and channels 13, 14, 15, and 16 mark multiples of `7`, `6`, `5`,
  and `4`.
  Evidence: writer `0x12cfe`, default builder `0x12b96`, refresh caller
  `0xe5e2`, consumer `0x1280a`; fixture
  `0x12cfe ESC &l#W loads vertical forms control state`; table-hit
  consumer fixture
  `mixed VFC start-after-text wraps to table hit before printable`; and
  bottom-recovery consumer fixture
  `mixed VFC start-after-text wraps to bottom recovery before printable`;
  macro-layout fixture
  `0xe5e2 refreshes page layout, default VFC table, and static font
  context`; and fixture
  `0x12b96 default VFC table channel convention`.
- `0x783160`: canonical VMI / line advance.
  Semantic role: converts between line numbers and packed cursor
  positions.
  Evidence: VMI writers `0xcb00`/`0xc992`; readers `0xfe54`,
  `0x1280a`, `0x12cfe`; fixture
  `0xf9e8 ESC &l#P converts VMI lines to page length and selects
  internal page code`.
- `0x782dce`: canonical top offset.
  Semantic role: origin for VFC line-to-cursor conversion.
  Evidence: writers `0xece2`, `0xf9e8`, `0x12cfe`, and `0xe5e2`;
  readers `0x1280a`, `0x12cfe`, `0xfe54`, and `0xf8fc`; fixture
  `0x12cfe ESC &l#W loads vertical forms control state` and
  `mixed VFC before-top channel jump normalizes start line before
  printable`; macro-layout fixture
  `0xe5e2 refreshes page layout, default VFC table, and static font
  context`.
- `0x782dd0`: parser scratch / layout cache.
  Semantic role: cleared by shared layout refresh before derived layout
  helpers run; no canonical PCL command state has been assigned to it.
  Evidence: writers `0xe5e2`, `0xcc70`, `0xfc74`, and `0xf9e8` clear it
  before `0xea16`/`0xe9ba`/`0xf8fc`/`0xfe54`/`0x12b96`; fixture
  `0xe5e2 refreshes page layout, default VFC table, and static font
  context`.
- `0x782c8e`: canonical vertical cursor.
  Semantic role: current y position read by `0x1280a` to choose a VFC
  start line, written by the forward channel-jump path before the next
  printable byte is placed, and recomputed by page-eject helper `0xf124`
  before a fresh post-eject printable byte is placed.
  Evidence: consumer/writer `0x1280a`; page-eject helper summary for
  `0xf124` in
  `generated/analysis/ic30_ic13_direct_control_code_flow.md`; fixtures
  `mixed VFC channel jump stream moves cursor before printable
  page-record queue`,
  `mixed VFC before-top channel jump normalizes start line before
  printable`, and
  `mixed VFC selector-zero page-eject publishes old page before fresh
  printable`.
- `0x782c8a`: canonical horizontal cursor.
  Semantic role: reset to the left margin by helper `0xf06e` on the
  modeled `0x1280a` forward jump path.
  Evidence: `0x1280a` calls `0xf06e` at `0x12aa6`; fixture
  `mixed VFC channel jump stream moves cursor before printable
  page-record queue`.
- `0x782db8`: canonical page width.
  Semantic role: page-geometry width used by `0xe9ba` to restore the
  right margin after geometry or macro-layout refresh.
  Evidence: page-size/orientation writers `0xfc74` and `0x10220`;
  reader `0xe9ba`; fixture
  `0xe5e2 refreshes page layout, default VFC table, and static font
  context`.
- `0x782dd6` / `0x782dda`: canonical left/right margins.
  Semantic role: horizontal text limits. `0xe9ba` resets left to zero and
  right to page width; margin handlers later update them from PCL
  columns.
  Evidence: writers `0xe9ba`, `0xeb4c`, and `0xec1e`; consumers include
  printable cursor placement and `0xf06e`; fixtures
  `0xe5e2 refreshes page layout, default VFC table, and static font
  context`, margin command parser fixtures, and VFC channel-jump fixtures.
- `0x782ddc`: derived/cache right-margin fraction.
  Semantic role: fractional margin companion cleared by `0xe9ba` when
  right margin resets to page width.
  Evidence: writer `0xe9ba`; fixture
  `0xe5e2 refreshes page layout, default VFC table, and static font
  context`.
- `0x782dd2`: derived/cache text-length bottom.
  Semantic role: text-bottom cache; `0x12cfe` copies VFC-derived limit
  here.
  Evidence: writers `0xea9e`, `0xea16`, `0x12cfe`, and `0xe5e2`
  through `0xea16`; consumers include vertical overflow helpers; fixture
  `mixed VFC definition stream consumes payload before printable
  page-record queue`; macro-layout fixture
  `0xe5e2 refreshes page layout, default VFC table, and static font
  context`.
- `0x782dc2`: derived/cache VFC limit.
  Semantic role: VFC-derived bottom/limit before it is copied to
  `0x782dd2`.
  Evidence: writer `0x12cfe`, default-table builder `0x12b96`, and
  `0xe5e2` through `0x12b96`; consumer `0xf36c`; long-reference scan
  lists `0xf372`, `0x12cec`, and `0x12f16`.
- `0x782ede`: derived/cache last VFC/page line index.
  Semantic role: payload count bound and channel-search limit.
  Evidence: writers `0xfe54`/`0x12cfe`; refresh caller `0xe5e2`;
  readers `0x1280a`, `0x12cfe`; fixture records `last_line = 63` for
  Letter at 6 LPI and `last_line = 3` for the macro-layout fixture.
- `0x782edf`: derived/cache last text line index.
  Semantic role: default VFC table builder `0x12b96` input.
  Evidence: writer `0xfe54`, refresh caller `0xe5e2`, reader
  `0x12b96`; disassembly `0xfe54..0xfe94` and `0x12b96..0x12bb6`;
  fixture `0xe5e2 refreshes page layout, default VFC table, and static
  font context`.
- `0x782ee0`: derived/cache last printable text line.
  Semantic role: clamps channel-derived bottom.
  Evidence: writer `0xfe54`, refresh caller `0xe5e2`; readers
  `0x1280a`, `0x12cfe`; fixtures record `text_last_line = 62` for
  Letter at 6 LPI and `2` for the macro-layout fixture.
- `0x782ee1`: firmware bookkeeping.
  Semantic role: modified-layout flag cleared after VFC table load.
  Evidence: writers `0xca8c`/`0xcb00`/`0x12cfe`; clear through
  `0x12b96` in the `0xe5e2` cluster; reader `0x1280a`; disassembly
  `0x1284c..0x12866` and `0x12f1e..0x12f24`.
- `0x782a58`/`0x782a6d`: firmware bookkeeping.
  Semantic role: pending text and cursor latches cleared by shared helpers
  on the `0x1280a` jump path; `0xf124` clears page-eject pending state
  after finalizing the page root.
  Evidence: helper summaries for `0xf06e`/`0xf34a` in
  `generated/analysis/ic30_ic13_direct_control_code_flow.md`; fixture
  records pending width cleared after `ESC &l2V!` and pending text `0`
  after `!\x1b&l0V!`.
- `0x783184`: firmware bookkeeping.
  Semantic role: pending text span flush enable tested by `0xf34a` before
  cursor/page-boundary changes.
  Evidence: direct-control helper summary lists `0xf34a` readers and the
  `mixed VFC selector-zero page-eject publishes old page before fresh
  printable` fixture records two `0xf34a` flushes on the
  `0x1299c..0x129c4` path.
- `0x78297a`: firmware bookkeeping.
  Semantic role: current page-root pointer ensured by `0x10084` and
  finalized/cleared by `0xff1e`, which is called by `0xf124`.
  Evidence:
  `generated/analysis/ic30_ic13_page_root_finalization.md` and
  fixture `mixed VFC selector-zero page-eject publishes old page before
  fresh printable`, which publishes the old compact-text page record then
  allocates a fresh page root for the following printable byte.
- `0x78299e`: parser scratch.
  Semantic role: parsed six-byte command record cursor rewound by
  command handlers and restored by delayed payload dispatch.
  Evidence: `0x11f6e` schedules delayed handler; `0x12cfe` rewinds and
  reads parsed count; fixture
  `mixed VFC lowercase delayed record survives until uppercase W` records
  lowercase snapshot `80 77 00 04 00 00` and restored lowercase record
  after uppercase `W`.

### Writers

- `0x11f6e` is the parser final for `ESC &l#W`; it schedules delayed
  handler `0x12cfe` through `0x121cc`. On lowercase `w`, the pending
  record remains live across the same `&l` command family until an
  uppercase `W` reaches `0x12218`; the uppercase command does not replace
  the pending record while `0x782a1a` is already set.
- `0x12cfe` is the VFC table payload handler. It rewinds parser scratch
  at `0x78299e`, reads the absolute byte count, consumes payload bytes
  through `0xdace`, stores bytes into `0x782dde`, clears unused table
  bytes, derives `0x782dc2`, copies it to `0x782dd2`, and clears
  `0x782ee1`.
- `0x12b96` builds the default VFC table from line-number divisibility
  and boundary rules. It writes `0x782dde` words and is called by
  `0x12cfe` zero-count/default handling and by page-geometry refresh
  paths such as `0xf9e8`. For `text_last_line = 62` and `last_line = 63`,
  the fixture pins line words `0: f8fd`, `32: 806c`, `61: 0006`,
  `62: 010e`, and `63: 0004`.
- `0xfe54` computes the VFC line-count caches `0x782edf`,
  `0x782ee0`, and `0x782ede` from VMI, top offset, text bottom, page
  extent, and vertical offset source.
- `0x1280a` writes cursor state on the modeled forward channel-jump path.
  It ensures the page root through `0x10084`, resets horizontal cursor
  through `0xf06e`, flushes pending text through `0xf34a`, and writes
  `0x782c8e` through the `0x12aa6..0x12af8` path.
- `0x1280a` also publishes the current page on the modeled selector-zero
  page-eject path. Branch `0x1299c..0x129c4` calls `0xf06e`, `0xf34a`,
  `0xf34a`, and `0xf124`; the fixture shows the first queued `!`
  published before a second `!` allocates a fresh page root.
- `0x1280a` publishes the current page on the modeled wrap-hit path.
  Branch `0x129c6..0x12af8` wraps the channel search to line `0`, finds
  selector 2 at line `1`, calls `0xf34a`, `0xf124`, `0xf06e`,
  `0xf34a`, `0xf06e`, and `0xf34a`, then writes `0x782c8e` through the
  normal commit math.
- `0x1280a` publishes the current page on the modeled target-after-text
  path. Branch `0x129ee..0x12b5a` finds selector 2 at line `63`, calls
  `0xf34a` and `0xf124`, then enters bottom recovery at `0x12afc`,
  calls `0xf06e` and `0xf34a`, and writes recovered cursor y `104`.
- `0x1280a` skips publication on the modeled start-line-zero
  target-after-text path. Branch `0x129fc..0x12afc` sees `D3 == 0`,
  skips `0x12a12..0x12a1e`, calls `0xf06e` and `0xf34a`, and writes
  recovered cursor y `104`.
- `0x1280a` skips wrap and publication on the modeled start-after-text
  empty-table path. Branch `0x12a02..0x12afc` sees start line `64`
  greater than `0x782ee0 + 1`, calls `0xf06e` and `0xf34a`, and writes
  recovered cursor y `54`.
- `0x1280a` wraps before committing the modeled start-after-text
  default-table path. Branch `0x12a7a..0x12af8` sees start line `64`,
  skips the `0x12a8a..0x12aa2` publication edge, finds selector 2 at
  line `1`, calls `0xf06e` and `0xf34a`, and writes cursor y `176`.
- `0x1280a` wraps into bottom recovery on the modeled start-after-text
  line-63 path. Branch `0x12a7a..0x12afc` sees start line `64`, skips the
  `0x12a8a..0x12aa2` publication edge, finds selector 2 at line `63`,
  enters `0x12afc..0x12b5a`, calls `0xf06e` and `0xf34a`, and writes
  recovered cursor y `104`.
- `0x1280a` uses bottom/top-of-form recovery on the modeled selector-zero
  start-after-text path. Branch `0x1299c..0x12b92` sees start line `64`
  greater than `0x782ee0 + 1`, skips `0xf124`, and writes top-of-form
  cursor y `126`.
- `0x1280a` publishes the current page on the modeled wrap-no-hit path.
  Branch `0x12a22..0x12a78` sees no selector-2 bit before wrap returns
  to start line `3`, calls `0xf34a`, `0xf124`, `0xf06e`, and `0xf34a`,
  then writes top-of-form cursor y `126`.
- `0x1280a` high-start alternate entries are modeled directly. For start
  line `80`, empty-table selector 2 takes `0x12a02..0x12afc` and writes
  recovered y `1104`; a wrapped selector-2 hit at line `70` takes
  `0x12a7a..0x12afc`, skips `0x12a8a..0x12aa2`, enters
  `0x12afc..0x12b5a`, and writes recovered y `1604`; selector zero
  takes `0x1299c..0x12b92`, enters `0x12b5e..0x12b92`, and writes
  top-of-form y `126`.

### Readers And Consumers

- `0x1280a` is the `ESC &l#V` consumer. It reads the absolute channel
  selector, current VMI, cursor y `0x782c8e`, top offset `0x782dce`,
  text-line caches `0x782ede`/`0x782ee0`, and channel words from
  `0x782dde`. It searches forward or backward depending on cursor
  position relative to top offset. The modeled before-top path takes
  `0x128ae..0x128f4`, computes a wrapped start line from
  `top_offset - cursor_y - 1`, then rejoins the same channel search. The
  modeled forward path searches `0x1292a..0x1295c`, then commits the
  in-text hit through `0x12aa6..0x12af8`. The modeled selector-zero
  target-equal path
  computes the same top-of-form target through `0x12966..0x12992`,
  compares it with `0x782c8e` at `0x12994`, and exits through
  `0x1295e` when they match. When the target differs and the computed
  start line is within `text_last_line + 1`, the modeled path continues
  through `0x1299c..0x129c4`, runs the CR/text-flush/page-eject helper
  sequence, and returns after `0xf124`. The modeled wrap-hit path starts
  at line `3`, misses channel 2 through `0x1295a..0x129c6`, wraps the
  search through `0x129d0..0x12a22`, finds line `1`, publishes the
  current page through `0x12a7a..0x12aa2`, then commits the found line
  through `0x12aa6..0x12af8`. The modeled target-after-text path finds
  channel 2 at line `63`, observes that line is past `0x782ee0 = 62`,
  takes `0x129ee..0x12a1e`, then enters bottom recovery at
  `0x12afc..0x12b5a`.
- The modeled before-top target-after-text path normalizes y `89` to
  start line `0` through `0x128ae..0x128f4`, finds channel 2 at line
  `63`, then takes `0x129fc..0x12afc` and skips the `0xf124`
  publication edge.
- The modeled empty-table start-after-text path starts with y `3290`,
  computes start line `64`, finds no selector 2 bit in the forward or
  wrapped scans, takes `0x12a02..0x12afc`, and skips publication.
- The modeled default-table start-after-text path starts with y `3290`,
  computes start line `64`, wraps to the selector-2 bit at line `1`, then
  takes `0x12a7a..0x12af8`; it skips the `0x12a8a..0x12aa2`
  publication edge and writes the line-1 target.
- The modeled line-63 start-after-text path starts with y `3290`,
  computes start line `64`, wraps to the selector-2 bit at line `63`,
  then takes `0x12a7a..0x12afc`; it skips the `0x12a8a..0x12aa2`
  publication edge and writes the bottom-recovered line-63 target through
  `0x12afc..0x12b5a`.
- The modeled selector-zero start-after-text path starts with y `3290`,
  computes the top-of-form target through `0x12966..0x12992`, then takes
  `0x1299c..0x12b92`; it skips the `0x129b8..0x129c4` publication edge
  and writes the same top-of-form target.
- The modeled wrap-no-hit path starts at line `3` with no selector-2 bit
  anywhere in `0x782dde..0x782e5d`; the wrap search returns to start
  line `3`, enters `0x12a22..0x12a78`, publishes the current page, and
  writes the top-of-form target.
- The modeled high-start alternate path starts at line `80` with
  `0x782ede = 100` and `0x782ee0 = 62`, so it proves the same
  branch predicates when the computed start is well past the text region:
  empty-table no-hit recovery uses `target_line = 80`, wrapped
  after-text recovery uses wrapped `target_line = 70`, and selector-zero
  recovery uses `0x12b5e..0x12b92`.
- `0xf36c` consumes the derived limit `0x782dc2` during vertical
  overflow/perforation handling.
- Printable output is indirectly affected: the `ESC &l4W 00 00 00 02 !`
  fixture proves payload bytes are consumed before printable parsing, then
  the following `!` still reaches the page-record queue at compact coord
  `0x9001`.
- Printable output is directly moved by the modeled channel jump:
  `ESC &l2V!` after the same table definition finds channel 2 at line 1,
  changes y from `126` to `176`, resets x from `40` to the left margin
  `10`, and queues `!` at compact coord `0xb001`.
- Printable output from before the top offset is normalized into the same
  channel search: `ESC &l2V!` with y `89` and top offset `90` takes
  `0x128ae..0x128f4`, normalizes the start line to `0`, finds channel 2
  at line `1`, writes y `176`, and queues `!` at compact coord `0xb001`.
- Printable output is preserved by the selector-zero target-equal path:
  `ESC &l0V!` computes target y `126`, finds it already equals the
  current vertical cursor, leaves x/y unchanged, and queues `!` at
  compact coord `0x9e02`.
- Printable output can be split across a VFC-driven page boundary:
  `!\x1b&l0V!` starts with a live queued `!` at compact coord `0xbe02`,
  takes `0x1299c..0x129c4`, publishes that old page through `0xf124`,
  resets x from `58` to `10`, recomputes y from `176` to `126`, and
  queues the post-eject `!` on a fresh page at compact coord `0x9001`.
- Printable output can also split across a wrapped VFC channel hit:
  `!\x1b&l2V!` starts with a queued `!` at compact coord `0xde02`, wraps
  from start line `3` to target line `1`, publishes the old page through
  `0xf124`, writes y `176`, and queues the post-wrap `!` on a fresh page
  at compact coord `0xb001`.
- Printable output can split across a target-after-text recovery:
  `!\x1b&l2V!` with channel 2 at line `63` starts with a queued `!` at
  absolute compact coord `0x4e02` in bucket `198`, publishes that old
  page, recovers cursor y to `104`, and queues the post-recovery `!` on a
  fresh page at compact coord `0x3001`.
- Printable output can also move through target-after-text recovery
  without publication: `ESC &l2V!` with y `89` and channel 2 at line `63`
  skips `0xf124`, recovers cursor y to `104`, and queues `!` at compact
  coord `0x3001`.
- Printable output can move through start-after-text recovery without
  wrap or publication when the table has no selector-2 bit:
  `ESC &l2V!` with y `3290` computes start line `64`, recovers cursor y
  to `54`, and queues `!` at compact coord `0x1001`.
- Printable output can move through start-after-text wrap recovery without
  publication: default-table `ESC &l2V!` with y `3290` computes start
  line `64`, wraps to line `1`, writes y `176`, and queues `!` at
  compact coord `0xb001`.
- Printable output can move through start-after-text wrap bottom recovery
  without publication: line-63-only `ESC &l2V!` with y `3290` computes
  start line `64`, wraps to line `63`, writes recovered y `104`, and
  queues `!` at compact coord `0x3001`.
- Printable output can move through selector-zero start-after-text
  recovery without publication: `ESC &l0V!` with y `3290` computes start
  line `64`, writes y `126`, and queues `!` at compact coord `0x9001`.
- Printable output can split across a wrap-no-hit recovery:
  `!\x1b&l2V!` with no channel 2 in the table starts with a queued `!` at
  compact coord `0xde02` in bucket `12`, publishes that old page, returns
  y to `126`, and queues the post-recovery `!` on a fresh page at compact
  coord `0x9001`.

### Output Effect

The anchored output effects are text-bottom recomputation, payload
boundary behavior, and one forward VFC channel jump. In the current
definition fixture, a Letter 6-LPI base state with top offset `90`, text
bottom `3240`, and VMI `50` receives `ESC &l4W 00 00 00 02`. Handler
`0x12cfe` stores the table prefix `00 00 00 02`, derives text bottom
`190`, and leaves the following printable `!` queued at compact coord
`0x9001`.

In the lowercase VFC definition fixture, the stream
`ESC &l4w4W 00 00 00 02 !` first schedules delayed handler `0x12cfe`
with snapshot bytes `01 00 01 2c fe 80 77 00 04 00 00` for lowercase
record `80 77 00 04 00 00`. The following uppercase `W` reaches
`0x11f6e` but does not reschedule while pending, then `0x12218` restores
the lowercase record, consumes the four payload bytes starting after the
uppercase `W`, loads the same table prefix, and queues the following `!`
at compact coord `0x9001`.

In the channel-jump fixture, the same table state receives `ESC &l2V!`.
Handler `0x1280a` uses cached line bounds `0x782ee0 = 62` and
`0x782ede = 63`, starts searching at line `1`, matches channel mask
`0x0002`, writes y `176`, resets x to `10`, and the following `!` renders
from compact coord `0xb001`.

In the before-top channel-jump fixture, the same table state receives
`ESC &l2V!` while y is `89`, below top offset `90`. Handler `0x1280a`
takes `0x128ae..0x128f4`: `top - y` is `12` subunits, the ROM subtracts
one before VMI division to get dividend `11`, divides by VMI `50`, and
maps normalized line `64` back to start line `0`. The following search
finds channel mask `0x0002` at line `1`, writes y `176`, resets x to
`10`, and the following `!` renders from compact coord `0xb001`.

In the selector-zero target-equal fixture, the same table state receives
`ESC &l0V!` while y is already `126`, the computed top-of-form target.
Handler `0x1280a` ensures the page root through `0x10084`, takes
`0x12966..0x1299a`, leaves x `40` and y `126` unchanged, and the
following `!` renders from compact coord `0x9e02`.

In the selector-zero page-eject fixture, the stream `!\x1b&l0V!` first
queues a printable at compact coord `0xbe02`. Handler `0x1280a` computes
the top-of-form target y `126`, sees current y `176` differs, and takes
`0x1299c..0x129c4`. The helper sequence `0x10084`, `0xf06e`, `0xf34a`,
`0xf34a`, `0xf124` publishes the old page record, records one page-root
clear and one page publication, leaves pending text `0`, and lets the
following printable allocate a new page root and render at compact coord
`0x9001`.

In the wrap-hit fixture, the stream `!\x1b&l2V!` first queues a printable
at compact coord `0xde02` while y is `226`. Handler `0x1280a` starts the
channel search at line `3`, reaches the bottom with no channel-2 word,
wraps through `0x129c6..0x12a22`, finds channel mask `0x0002` at line
`1`, and takes the page-boundary helper sequence `0xf34a`, `0xf124`,
`0xf06e`, `0xf34a`, `0xf06e`, `0xf34a`. The old page is published, the
fresh cursor lands at x `10`, y `176`, and the following printable
renders from compact coord `0xb001`.

In the target-after-text fixture, the stream `!\x1b&l2V!` uses a VFC
table with channel mask `0x0002` at line `63`, past text-last line
`62`. The first printable is queued at absolute compact coord `0x4e02`
in bucket `198`; the rendered page-band rows use local row `4`.
Handler `0x1280a` takes `0x129ee..0x12a1e`, publishes the old page
through `0xf124`, then takes bottom recovery `0x12afc..0x12b5a`.
Recovery resets x to `10`, writes y `104`, and the following printable
is queued on a fresh page at compact coord `0x3001`, bucket `5`, with
band-local row `3`.

In the before-top target-after-text fixture, the stream `ESC &l2V!` starts
at y `89` with channel mask `0x0002` only at line `63`. The
`0x128ae..0x128f4` normalization sets start line `0`; handler `0x1280a`
then takes `0x129fc..0x12afc`, skips the publication edge
`0x12a12..0x12a1e`, resets x to `10`, writes recovered y `104`, and
queues the following printable at compact coord `0x3001`, bucket `5`.

In the empty-table start-after-text fixture, the stream `ESC &l2V!`
starts at y `3290`, which computes start line `64` against text-last line
`62` and last line `63`. Handler `0x1280a` finds no selector-2 bit in
the forward or wrapped scans, takes `0x12a02..0x12afc`, skips
publication, resets x to `10`, writes recovered y `54`, and queues the
following printable at compact coord `0x1001`, bucket `2`.

In the default-table start-after-text fixture, the stream `ESC &l2V!`
starts at y `3290`, computes start line `64`, wraps to the selector-2 bit
at line `1`, and takes `0x12a7a..0x12af8`. It skips the publication edge
`0x12a8a..0x12aa2`, resets x to `10`, writes y `176`, and queues the
following printable at compact coord `0xb001`, bucket `9`.

In the line-63 start-after-text fixture, the stream `ESC &l2V!` starts at
y `3290`, computes start line `64`, wraps to the selector-2 bit at line
`63`, and takes `0x12a7a..0x12afc`. It skips the publication edge
`0x12a8a..0x12aa2`, enters bottom recovery `0x12afc..0x12b5a`, writes
recovered y `104`, and queues the following printable at compact coord
`0x3001`, bucket `5`.

In the selector-zero start-after-text fixture, the stream `ESC &l0V!`
starts at y `3290`, computes start line `64`, then takes
`0x1299c..0x12b92`. The `0x12b5e..0x12b92` recovery writes
top-of-form y `126` without publication, resets x to `10`, and queues
the following printable at compact coord `0x9001`, bucket `6`.

In the wrap-no-hit fixture, the stream `!\x1b&l2V!` uses an empty VFC
table while starting at y `226`, so start line is `3` and channel mask
`0x0002` is absent through line `63` and through the wrapped scan back to
line `3`. Handler `0x1280a` takes `0x12a22..0x12a78`, publishes the old
page at compact coord `0xde02`, resets x to `10`, writes top-of-form y
`126`, and queues the following printable on a fresh page at compact
coord `0x9001`, bucket `6`.

The direct high-start fixture uses the same `0x1280a` state model with
`0x782ee0 = 62`, `0x782ede = 100`, and computed start line `80`. With an
empty table, selector 2 takes `0x12a02..0x12afc`, skips publication, and
writes recovered y `1104`. With channel 2 at line `70`, selector 2 takes
`0x12a7a..0x12afc`, skips `0x12a8a..0x12aa2`, enters
`0x12afc..0x12b5a`, and writes recovered y `1604`. Selector zero with
the same start line takes `0x1299c..0x12b92`, enters
`0x12b5e..0x12b92`, and writes top-of-form y `126`.

The default-table fixture pins the ROM-generated channel convention for
`0x12b96` with `0x782ee0 = 62` and `0x782ede = 63`. Example words are
line `0 = f8fd`, line `32 = 806c`, line `48 = a05c`, line `61 = 0006`,
line `62 = 010e`, line `63 = 0004`, and line `64 = 0000`. Since
`0x1280a` converts selector `n` to mask `1 << (n - 1)`, those words mean
line 0 has channels `1,3,4,5,6,7,8,12,13,14,15,16`, line 61 has
channels `2,3`, line 62 has channels `2,3,4,9`, line 63 has channel `3`,
and line 64 has no default channel.

### Confidence

High for the `0x11f6e -> 0x12cfe` delayed payload boundary, lowercase
same-family `w...W` delayed-record preservation, table bytes, reject
cases, zero-count reset, text-bottom cache effect, and forward
`0x1280a` in-text channel hit. High for before-top normalization through
`0x128ae..0x128f4` when it rejoins the forward in-text hit path. High for
the selector-zero target-equal early exit and selector-zero page-eject
branch through `0x1299c..0x129c4` when
`start_line <= text_last_line + 1`. High for the wrap-hit branch through
`0x129c6..0x12af8` when a wrapped search finds a channel before the
original start line and `start_line <= text_last_line + 1`. High for the
target-after-text branch through `0x129ee..0x12b5a` when the found line
is `63` and `start_line <= text_last_line + 1`. High for the
non-publishing target-after-text branch through `0x129fc..0x12afc` when
before-top normalization sets start line `0`. High for the
start-after-text no-wrap branch through `0x12a02..0x12afc` when computed
start line is `64` and the table has no selector-2 bit. High for the
start-after-text wrap-after-text branch through `0x12a7a..0x12af8` when
computed start line is `64` and the default table has selector 2 at line
`1`. High for the start-after-text wrap bottom-recovery branch through
`0x12a7a..0x12afc` when computed start line is `64` and the table has
selector 2 only at line `63`. High for the selector-zero start-after-text
recovery through
`0x1299c..0x12b92` when computed start line is `64`. High for the
alternate high-start entries through `0x12a02..0x12afc`,
`0x12a7a..0x12afc`, `0x12afc..0x12b5a`, and `0x12b5e..0x12b92` because
the direct fixture uses start line `80`, wrapped target line `70`, and
selector zero from the same state block. High for the `0x12b96` default
table channel convention because the fixture ties selector masks to
generated table words and channel sets. Medium for the exact semantic
names of `0x782ede`/`0x782edf`/`0x782ee0`; the line-count interpretation
matches fixtures and disassembly, but the byte names remain inferred from
their use rather than from HP terminology.

### Fixtures

- `0x12cfe ESC &l#W loads vertical forms control state`
- `mixed VFC definition stream consumes payload before printable
  page-record queue`
- `mixed VFC lowercase delayed record survives until uppercase W`
- `mixed VFC channel jump stream moves cursor before printable page-record
  queue`
- `mixed VFC before-top channel jump normalizes start line before
  printable`
- `mixed VFC before-top target-after-text skips publication`
- `mixed VFC start-after-text skips wrap and publication`
- `mixed VFC start-after-text wraps to table hit before printable`
- `mixed VFC start-after-text wraps to bottom recovery before printable`
- `mixed VFC selector-zero top-of-form no-op reaches printable page-record
  queue`
- `mixed VFC selector-zero start-after-text returns to top`
- `mixed VFC selector-zero page-eject publishes old page before fresh
  printable`
- `mixed VFC wrap-hit publishes old page before fresh printable`
- `mixed VFC wrap-no-hit publishes old page and returns to top`
- `mixed VFC target-after-text recovers near top before fresh printable`
- `0x1280a VFC alternate high-start recovery entries`
- `0x12b96 default VFC table channel convention`
- Supporting existing fixtures:
  `0xc992 ESC &l#D accepts ROM LPI set and refreshes pending vertical
  cursor`, `0xf9e8 ESC &l#P converts VMI lines to page length and
  selects internal page code`

### Disassembly Evidence

- `generated/disasm/ic30_ic13_vertical_forms_control_01280a.lst`:
  `0x1280a..0x12b5e`, `0x12b96..0x12cfc`,
  `0x12cfe..0x12f28`
- `generated/analysis/ic30_ic13_direct_control_code_flow.md` and
  `generated/disasm/ic30_ic13_control_code_handlers_00f02c.lst`:
  direct vertical helpers `0xf054`, `0xf06e`, `0xf124`, and `0xf36c`
- `generated/disasm/ic30_ic13_hmi_vmi_handlers_00ca8c.lst`: VMI writers
  feeding the line-count math

### Unresolved Middle Edges

- None remaining for the VFC table and channel-jump checkpoint.
