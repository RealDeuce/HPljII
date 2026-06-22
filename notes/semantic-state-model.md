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
  - ring buffer: `0x783e54` count and `0x783e56` pointer, wrapped
    between `0x783a4c` and `0x783e53`.
  Evidence: disassembly `0xa92c..0xa9e0`; fixtures
  `0xa904 services pending work then prefers first LIFO source`,
  `0xa904 data-chain end marker retries before second LIFO source`, and
  `0xa904 buffered ring source wins before direct hardware in mode 0`.
- Canonical direct hardware sources:
  - mode `0x780e40 == 1`: status byte `0x8e01`, data byte `0x8801`,
    wait/ack byte `0x8c01`, handshake outputs `0xa601` and `0xaa01`.
  - alternate nonzero mode: status byte `0xfffee005`, data byte
    `0xfffee001`, handshake/control byte `0xfffee009`.
  Evidence: disassembly `0xa9e2..0xaa86` and `0xaaa6..0xab8a`;
  fixtures
  `0xa904 direct mode 1 preserves 0x1a and clears handshake state` and
  `0xa904 direct mode 2 reads ready byte and sets control-shadow bit 6`.
- Firmware bookkeeping:
  - `0x7821cd`: service-needed flag checked before all byte sources.
  - `0x7821cc`: service-in-progress flag set around helper `0x10cc`.
  - `0x780e66`: source/pending flags cleared as stacked sources empty.
  - `0x780e3b`: no-byte gate that returns `D7 = -1` while
    `0x780e66 != 0`.
  - `0x7821c4`: timeout/handshake state cleared after direct hardware
    reads.
  - `0x7828ec`: direct-mode active byte, cleared or set by hardware
    handshake paths.
  - `0x7828fa` and `0x7828fb`: direct-mode control shadows.
  - `0x780e2e`: status-error accumulator for alternate direct mode bits
    `7` and `6`.
  Evidence: disassembly `0xa904..0xab8a`; host fetch fixtures above.
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
- Macro setup helpers such as `0xe418` write data-chain frames later
  consumed by `0xa904`; the macro execute/call fixtures pin frame
  payload bytes `!\r` and mixed-control payload
  `ESC &k1G!\r!`.

### Readers And Consumers

- The main parser loop `0x11774` consumes `0xa904` bytes for normal host
  streams and routes them to handlers such as `0xd04a`, `0xf02c`,
  `0xedf8`, and raster/font command finals.
- Delayed payload readers consume bytes through `0xa904` or payload
  wrappers after `0x12218` restores the saved command record.
- Transparent text handler `0x12452` consumes `ESC &p#X` payload bytes
  through `0xa904`, routing printable bytes back to `0xd04a`.
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
and render-entry boundaries.

### Confidence

High for byte-source priority, no-byte gating, data-chain end retry,
ring/direct source selection, `0x1a` reporting, and direct-mode state
side effects because they are covered by executable fixtures and the
`0xa904` disassembly. Medium for physical interface naming and full
data-chain frame ownership because those require board/manual
correlation and broader frame-lifetime tracing.

### Fixtures

- `0xa904 no-byte branch returns -1 before buffered sources`
- `0xa904 services pending work then prefers first LIFO source`
- `0xa904 data-chain end marker retries before second LIFO source`
- `0xa904 buffered ring source wins before direct hardware in mode 0`
- `0xa904 direct mode 1 preserves 0x1a and clears handshake state`
- `0xa904 direct mode 2 reads ready byte and sets control-shadow bit 6`
- `macro execute frame payload feeds 0xa904 data-chain bytes`
- `host-fetched mixed control stream reaches parser and page-record render`
- `combined host-fetched font download stream prints installed glyph`
- `host-fetched text rectangle raster FF publishes rendered page record`

### Disassembly Evidence

- `generated/disasm/ic30_ic13_host_byte_fetch_00a904.lst`:
  `0xa904..0xab8a`
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
- `0x782d76 frame +0x00..+0x??`: full data-chain frame layout and owner
  lifecycle outside the macro replay fields already fixture-backed.
- `0x780e66` bit meanings: source-empty/active bits are observed by
  behavior, but not yet fully named.

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
  - record `+0x04`: stored byte count with chunk-header adjustment during
    selector `1` stop.
  - record `+0x08`: stored macro id written from `0x783164` on selector
    `0` start.
  - record `+0x0a`: permanence byte, cleared by selector `9` and set by
    selector `10`.
  Evidence: `notes/pcl-parser-firmware.md` macro selector table;
  disassembly `0xdd86..0xdfb8`; fixtures for start/stop, permanence,
  delete-temporary, delete-current, and delete-all.
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
- Canonical call context stack:
  - stack pointer `0x782c6e` is initialized to `0x782c1e` by `0xe146`.
  - each entry is 10 bytes.
  - call mode copies longwords from `0x782ee6` and `0x782ef6` into entry
    `+0x00` and `+0x04`, clears entry bytes `+0x08` and `+0x09`, then
    advances `0x782c6e` by `0x0a`.
  - execute mode does not push this context entry.
  Evidence: disassembly `0xe146..0xe1be` and `0xe4b2..0xe4e6`;
  fixture `0xe418 frame metadata distinguishes execute and call context`.
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
  - non-execute/non-call frames copy `0x782d3a..0x7834c2` from a flat
    snapshot at `0x7834c2`, then run a shorter return path.
  Evidence: disassembly `0xe22c..0xe408`; fixture
  `0xe22c restores macro frames and consumes call context`.
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
  Evidence: disassembly `0xdd4c..0xdd78`, `0xdee4..0xdefa`, and
  `0xe418..0xe4e6`; host-byte section
  `Host Byte Fetch And Data-Chain Input`.
- Derived/cache:
  - execute and call replay of stored `!\r` produce the same compact text
    page-record object and rendered rows.
  - mixed-control replay of stored `ESC &k1G!\r!` sets line termination
    mode through `0xedf8`, routes printable bytes through `0xd04a`, CR
    through `0xf02c`, and renders rows matching the direct host stream.
  - macro replay rows cross the `0x1edc6` bucket/context bridge and
    `0x1ed84`/`0x1ef6a` render-entry path.
  Evidence: fixtures `macro execute data-chain parser trace feeds
  page-record stream`, `macro call data-chain parser trace feeds
  page-record stream`, and `host-fetched macro replay payloads feed
  0x1ed84 and 0x1ef6a`.
- Unknown:
  - exact in-RAM chunk allocation layout behind macro record `+0x00` and
    the adjusted count at `+0x04`.
  - allocator `0x170c` and free helper `0x18b4` internals beyond the
    0x100-byte chunk contract observed through macro snapshots.
  - detailed font-context refresh side effects inside `0xe65c` after the
    context entry is popped.
  - non-execute/non-call frame producer and semantics for the `0xe972`
    flat restore path.

### Writers

- `0xe112` writes `0x783164` from the absolute parsed `ESC &f#Y` value.
- `0xdd08` rewinds `0x78299e`, finds or allocates the selected macro
  record through `0xe0a4`, dispatches selectors `0..10`, and writes
  definition, overlay, delete, temporary, and permanent state.
- `0xdd86..0xde7a` start and stop definition mode, seed lowercase
  `ESC &f` auto-prefix bytes through `0xe002`, and clear empty or
  auto-prefix-only records through `0xdfba`.
- `0xde7c..0xdec4` validate execute/call records and call `0xe418`.
- `0xe418` writes the data-chain frame later consumed by `0xa904`, writes
  the environment snapshot pointer at frame `+0x0a`, and pushes the
  call-only context entry at `0x782c6e`.
- `0xe8f0` allocates linked snapshot chunks; `0xe8a2` restores and checks
  them; `0xe972` and `0xe996` copy flat inclusive longword ranges.
- `0xe22c` consumes the current frame, frees snapshot chunks, rewinds
  `0x782d76`, clears host gate bit 1 when the previous frame is empty, and
  calls `0x1240a` on the execute/call return paths.
- `0xe65c(0)` pops the call-mode context stack entry and clears its
  10-byte slot before running font-context refresh helpers.
- The alternate parser table at `0x116f6` writes stored definition payload
  bytes rather than dispatching ordinary control-code handlers.

### Readers And Consumers

- `0xdd08` reads `0x783164`, `0x782d7a`, `0x782d76`, frame byte `+9`,
  and definition-mode byte `0x782c18` before selector dispatch.
- `0xa904` consumes the frame bytes as its active data-chain source,
  dispatches end transitions through `0xe22c`, and then returns replayed
  bytes to the parser.
- `0xe22c` consumes frame `+0x09`, frame `+0x0a`, `0x782c6e`, and
  environment buffers to unwind execute/call frames after replay.
- `0xe65c` consumes context-stack entry bytes `+8/+9` to decide whether
  primary/secondary font refresh helpers such as `0x13eb8` run before
  the slot is cleared.
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
mode-0 raster band output in the existing page-record fixture.

### Confidence

High for parser reachability, selector meanings, record count/stride,
current id storage, definition stop behavior, execute/call frame mode
bytes, frame field offsets `+0x00/+0x04/+0x08/+0x09/+0x0a`, call-only
context-stack push, snapshot chain chunk shape, execute/call frame-end
restore, `0xa904` replay, and page-record/render effects because those
are covered by disassembly, generated parser-table reports, and
executable fixtures. Medium for macro chunk allocator internals,
`0xe65c` font refresh side effects, and non-execute/non-call frame-end
semantics because only the fields needed by current replay fixtures are
pinned.

### Fixtures

- `0xe112 stores absolute parsed macro id`
- `0xdd08 starts and stops empty macro definitions`
- `0x11774 ROM dispatch table routes chained ESC &f macro stream`
- `macro command stream defines payload and executes data-chain frame`
- `host-fetched macro execute stream builds replay frame`
- `host-fetched macro call stream builds replay frame`
- `0xe418 frame metadata distinguishes execute and call context`
- `macro snapshot helpers copy linked and flat environment ranges`
- `0xe22c restores macro frames and consumes call context`
- `macro execute frame payload feeds 0xa904 data-chain bytes`
- `macro execute data-chain parser trace feeds page-record stream`
- `macro call data-chain parser trace feeds page-record stream`
- `host-fetched mixed-control macro execute stream builds replay frame`
- `macro mixed-control data-chain parser trace feeds page-record stream`
- `host-fetched macro replay payloads preserve 0x1edc6 bridge contract`
- `host-fetched macro replay payloads feed 0x1ed84 and 0x1ef6a`
- `macro execute page-record layer composes with rule and raster band`

### Disassembly Evidence

- `generated/disasm/ic30_ic13_pcl_escape_parser_00da9a.lst`:
  `0xdd08..0xdfb8`, including selector dispatch, record pool scans, and
  execute/call calls to `0xe418`.
- `generated/disasm/ic30_ic13_macro_record_chain_helpers_00dfba.lst`:
  `0xdfba..0xe4f2`, including record clear, append, lookup/allocation,
  parser reset, frame cleanup, frame end, and `0xe418` frame creation.
- `generated/disasm/ic30_ic13_macro_environment_snapshot_helpers_00e65c.lst`:
  `0xe65c..0xe9b8`, including context-stack pop, snapshot chain
  allocation, snapshot restore, and flat copy helpers.
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

- `0xdfba..0xe110`: macro record free/clear and allocator details,
  including exact ownership of payload chunks referenced by record `+0x00`.
- `0xe002..0xe080`: definition-byte append helper, chunk growth, and
  count update rules behind record `+0x04`.
- `0xe0a4..0xe110`: record lookup/allocation policy for the 32-entry pool
  when ids collide, records are temporary/permanent, or allocation fails.
- `0x170c` and `0x18b4`: allocator/free internals for 0x100-byte chains.
- `0xe65c..0xe84c`: full font-context refresh side effects after
  context-stack pop, especially entry bytes `+8/+9` branches.
- `0xe35a..0xe3e8`: producer and full semantics for non-execute/non-call
  frames restored through `0xe972`.
- `0x782c6e..0x782d36`: context stack capacity and overflow policy around
  macro call replay.

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
  - context slots `+0x2c`: slot 0 is `0x440946b4`.
  Evidence: fixture
  `addressed text/rule/raster field groups reach publication and render
  entry`; source fixture [harness](/usr/home/admin/T400/ljII/tools/render_fixture_harness.py:40084).
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
  Evidence: render-entry setup fixture
  `addressed text/rule/raster field groups reach publication and render
  entry`, with `0x1ef86` before `0x1efc2`, `0x1f446`, and `0x1f756`.
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

- `0xd04a..0x12f2e`: the printable source and queue path is fixture-backed
  but still not a full live CPU/register trace for this mixed stream.
- `0x10898..0x133aa`: the addressed rule insertion is modeled from
  disassembly and fixtures, but the exact live no-room/retry edge is not
  covered in this mixed stream.
- `0x105d0..0x13250`: the raster object queue is address-aware, but the
  mixed stream still lacks a full 68000 execution through `0x105d0` into
  real allocator memory.
- `0x10084..0x1381c`: first root allocation and stream-chunk allocation
  are modeled with exact side effects, but not captured from live CPU
  memory for the complete text/rule/raster stream.
- `0xff1e..0x1ed84`: publication and render-entry are modeled and
  fixture-checked; scheduler timing between the published pool record and
  active render selection remains outside this cluster.

## Shared Page-Record Storage And Allocator

Status: anchored as the shared storage model beneath compact text, rule,
fixed-rule, raster, publication, and render-bridge fixtures. This section
collapses allocator concepts that were previously repeated in text,
rectangle, raster, and publication notes.

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
  and disassembly `0x10084..0x1021e`.
- Firmware bookkeeping:
  - `0x782a70`: bytes remaining in the current stream chunk.
  - `0x782a72`: pointer to the current chunk link field.
  - `0x782a76`: next free byte in the current chunk.
  - `0x782c72`/`0x782c73`: pending latches cleared by first-root
    allocation after the `0x9ac2` wait hook.
  - `0x782990`: transient page-root byte cleared by `0x10084`.
  Evidence: fixture
  `0x1381c stream allocator chunks display-list storage` and disassembly
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
- `0x13250..0x1381c`: raster encoded-span allocation is modeled and
  render-checked, but exact live register/memory state through the full
  raster producer remains unresolved.
- `0x133aa..0x13472` and `0x136d2..0x13690`: ordered insertion is pinned
  for lower, higher, and equal bucket bytes; alternate no-room/failure
  returns need live CPU fixtures.
- `0xff1e..0x1ed84`: pool-record publication and render bridge are
  modeled, but scheduler selection timing is outside this checkpoint.

## Vertical Forms Control

Status: partially anchored. The table definition path, its immediate
text-bottom effect, the forward in-text channel-jump path, the
before-top forward channel-jump normalization path, the selector-zero
target-equal path, the selector-zero top-of-form page-eject path, and one
wrap-hit page-eject path are modeled. The wrap no-hit top-of-form page
eject path, one publishing target-after-text bottom-recovery path, and
one non-publishing target-after-text bottom-recovery path are also
modeled. The start-after-text no-wrap bottom-recovery path is modeled for
start line `64` with an empty table, the start-after-text wrap-after-text
path is modeled for default-table line-1 placement and line-63 bottom
recovery, and selector-zero start-after-text top-of-form recovery is
modeled for start line `64`. Alternate bottom-recovery and alternate
wrap-recovery entrances inside the channel-jump consumer still need
fixtures.

Concept: vertical forms control is a per-line, 16-channel stop table used
by `ESC &l#W` definitions and consumed by `ESC &l#V` vertical channel
jumps. It affects visible output by changing the text-length bottom cache,
moving the vertical cursor before later printable bytes are queued, and
publishing a current page record when selector zero reaches the
top-of-form page-eject path.

### Field Groups

- `0x782dde..0x782edd`: canonical VFC table.
  Semantic role: 128 16-bit VFC channel words, two payload bytes per
  line.
  Evidence: writer `0x12cfe`, default builder `0x12b96`, consumer
  `0x1280a`; fixture
  `0x12cfe ESC &l#W loads vertical forms control state`; table-hit
  consumer fixture
  `mixed VFC start-after-text wraps to table hit before printable`; and
  bottom-recovery consumer fixture
  `mixed VFC start-after-text wraps to bottom recovery before printable`.
- `0x783160`: canonical VMI / line advance.
  Semantic role: converts between line numbers and packed cursor
  positions.
  Evidence: VMI writers `0xcb00`/`0xc992`; readers `0xfe54`,
  `0x1280a`, `0x12cfe`; fixture
  `0xf9e8 ESC &l#P converts VMI lines to page length and selects
  internal page code`.
- `0x782dce`: canonical top offset.
  Semantic role: origin for VFC line-to-cursor conversion.
  Evidence: writers `0xece2`, `0xf9e8`, `0x12cfe`; readers `0x1280a`,
  `0x12cfe`; fixture
  `0x12cfe ESC &l#W loads vertical forms control state` and
  `mixed VFC before-top channel jump normalizes start line before
  printable`.
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
- `0x782dd2`: derived/cache text-length bottom.
  Semantic role: text-bottom cache; `0x12cfe` copies VFC-derived limit
  here.
  Evidence: writers `0xea9e`, `0xea16`, `0x12cfe`; consumers include
  vertical overflow helpers; fixture
  `mixed VFC definition stream consumes payload before printable
  page-record queue`.
- `0x782dc2`: derived/cache VFC limit.
  Semantic role: VFC-derived bottom/limit before it is copied to
  `0x782dd2`.
  Evidence: writer `0x12cfe`; consumer `0xf36c`; long-reference scan
  lists `0xf372`, `0x12cec`, and `0x12f16`.
- `0x782ede`: derived/cache last VFC/page line index.
  Semantic role: payload count bound and channel-search limit.
  Evidence: writers `0xfe54`/`0x12cfe`; readers `0x1280a`, `0x12cfe`;
  fixture records `last_line = 63` for Letter at 6 LPI.
- `0x782edf`: derived/cache last text line index.
  Semantic role: default VFC table builder `0x12b96` input.
  Evidence: writer `0xfe54`; reader `0x12b96`; disassembly
  `0xfe54..0xfe94` and `0x12b96..0x12bb6`.
- `0x782ee0`: derived/cache last printable text line.
  Semantic role: clamps channel-derived bottom.
  Evidence: writer `0xfe54`; readers `0x1280a`, `0x12cfe`; fixture
  records `text_last_line = 62` for Letter at 6 LPI.
- `0x782ee1`: firmware bookkeeping.
  Semantic role: modified-layout flag cleared after VFC table load.
  Evidence: writers `0xca8c`/`0xcb00`/`0x12cfe`; reader `0x1280a`;
  disassembly `0x1284c..0x12866` and `0x12f1e..0x12f24`.
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
  paths such as `0xf9e8`.
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
`0x1299c..0x12b92` when computed start line is `64`. Medium for the exact
semantic names of `0x782ede`/`0x782edf`/`0x782ee0`; the line-count
interpretation matches fixtures and disassembly, but alternate
wrap-recovery and alternate bottom-recovery entrances still need complete
lifting.

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

- `0x12a02..0x12a10`: start-after-text bottom recovery is modeled for
  start line `64` only when the table has no wrapped selector hit; higher
  start-line values still need fixtures.
- `0x12a22..0x12a78`: no-hit publication is modeled for the empty-table
  line-3 case, and wrap-after-text line-1 placement is modeled through
  `0x12a7a..0x12af8`; alternate direct entrances where the wrapped scan
  reaches or hits at/after the original start line still need fixtures.
- `0x12afc..0x12b5a`: bottom/page-recovery placement is modeled for the
  target-after-text line-63 case and the start-after-text wrapped line-63
  case; alternate direct entrances and target-line values still need
  fixtures.
- `0x12b5e..0x12b92`: selector-zero start-after-text recovery is modeled
  for start line `64`; wrap-branch entrants into this recovery still need
  fixtures.
- `0x12b96..0x12cfc`: default table bit meanings are known by bit
  positions but not fully named by PCL channel convention.
