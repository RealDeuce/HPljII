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
- `0x782d76 frame +0x00..+0x0d`: non-macro data-chain owners and frame
  lifecycle outside the `0xe418` macro replay fields already pinned.
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
  `0xe65c refresh composes with font context bridge`; report
  `generated/analysis/ic30_ic13_font_context_bridge.md`.
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
  - heap allocator bookkeeping uses bitmap-base pointer variable
    `0x783972`, payload-base pointer variable `0x783988`, free-unit count
    `0x780e86`, bitmap end/limit fields `0x783976` / `0x78397a`,
    tracked bitmap-byte count `0x783986`, and scan cursors
    `0x78397e` / `0x783982`; those fields are allocator-private caches,
    not PCL-visible state.
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
  - startup option source for the optional `0x80` addition to
    `0x780e5a` still needs board/config correlation, but the downstream
    `0x0b18` heap-limit math and `0x164a` allocator initialization are
    pinned for the default path.
  - no remaining macro replay/font-context middle edge in this checkpoint.
    The next high-value edges are in parser-produced heterogeneous
    page-object rendering and final device-output validation.

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
  `0xc428` installs `0x782ee6` / `0x782ef6` context records into the
  current page root.
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
mode-0 raster band output in the existing page-record fixture. Macro
font-context refresh now composes through the existing font bridge:
`0xe65c` refresh slots `0/1` rebuild maps `0x782f32` / `0x783032`, and
the final `0xc428` install exposes the selected context record through a
page-root font slot for later text objects.

### Confidence

High for parser reachability, selector meanings, record count/stride,
current id storage, `0xe0a4` lookup/free/full status behavior, definition
stop behavior, execute/call and non-replay frame mode bytes, frame field offsets
`+0x00/+0x04/+0x08/+0x09/+0x0a`, call-only context-stack push, snapshot
chain chunk shape, execute/call frame-end restore, `0x164a` heap
initializer, `0x170c`/`0x1710` / `0x18b4` shared heap contract,
`0xe65c` branch contract, `0xe65c` bridge into `0x13eb8` / `0x144d2` /
`0x14c64` / `0xc428`, macro definition append/count bookkeeping,
`0xa904` replay, and page-record/render effects because those are covered
by disassembly, generated parser-table reports, and executable fixtures.
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
- `generated/analysis/ic30_ic13_font_context_bridge.md`:
  `0x13eb8`, `0x144d2`, `0x14c64`, `0xc428`, page-root font slots, and
  render-record context-slot bridge.
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

- None remaining for the macro replay/font-context checkpoint.

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
  are modeled with exact side effects, including a multi-writer chunk
  rollover fixture in the shared allocator checkpoint, but not captured
  from live CPU memory for the complete text/rule/raster stream.
- `0xff1e..0x1ed84`: publication and render-entry are modeled and
  fixture-checked. Active-record selection through `0x1eb2a..0x1ed84`
  is covered by the published-render scheduler checkpoint; remaining
  gaps are live engine pacing and multi-band loop timing.

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
- `0x13250..0x1381c`: raster encoded-span allocation is modeled and
  render-checked, but exact live register/memory state through the full
  raster producer remains unresolved.
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
    is set on pending-status escalation or beyond-last status.
  - `0x780e32`, `0x780e36`, and `0x7821f9.2`: wrapper attention sources
    tested at `0x1d62..0x1d82`. Any of `(0x780e32 & 5)`,
    `(0x780e36 & 3)`, or `0x7821f9.2` sends `0x1cf8` to the `0x1e80`
    attention variant.
  - `0x780e6d`: active-pool attention/status flag set by `0x1e44`,
    `0x1e80`, and `0x1ea8`; `0x780e67`: timeout-class status byte set
    to `1` by `0x1ea8`.
  - `0x7820bc`, `0x780ea4`, `0x780ea5`, `0x780eaa`, `0x780eae`, and
    `0x783a18` are scheduler/render bookkeeping, not page-object fields.
- Unknown:
  - `0x7839d4`: cleared by `0x1a4c..0x1c00`; no stable role is assigned
    yet beyond active-pool copy-window bookkeeping.
  - exact physical engine pacing around calls to `0x10c8`, `0x10c4`,
    `0x10d0`, and `0x10d8`.
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
pending-status transitions, the `0x1db0` status-copy path, the `0x1e44`
escalated-status bridge, the `0x1cf8` wrapper branch predicates, the
`0x1e80` attention variant, the `0x1ea8` timeout variant, the
`0x1eba4` cleanup, throttle, capacity, and render-call branch
predicates, the `0x1ee9e` geometry-change boundary, the
`0x1ed36..0x1ed6a` same-geometry reuse branch, and the render-entry
output for the selected source. Medium for the surrounding engine pacing
loop because the fixture bounds wait/yield helpers instead of executing
them to later interrupt states, and because it does not model the
physical timing of `0x10c8`, `0x10c4`, `0x10d0`, or `0x10d8`. Medium for
the physical meaning of `$8000`, `$a601`, `$a801`, `0x7828f9`,
`0xa668`, and `0xa680` because the byte-level side effects and branch
returns are pinned but not tied to measured engine timing yet. Medium
for `0x780eb6` because only its initialization is currently covered.

### Fixtures

- `0x1eb2a/0x1ecd6 selects published record for render entry`
- `0x1ecd6 same-geometry render work reuse reaches render entry`
- `0x3144/0x7ec6/0x7712 page pool aliases feed scheduler cursor`
- `0x1958/0x1c04/0x1eea staged candidate reaches render scheduler`
- `0x2126/0x1a4c/0x2038 active pool copy window feeds engine rows`
- `0x0fa2/0x1db0/0x1e44 status feedback drives copy and done flag`
- `0x1cf8/0x1e80/0x1ea8 wrapper dispatch selects engine variants`
- `0x1eba4/0x1ef6a active render loop advances or yields bands`
- `addressed stream page record materializes through 0xff1e and 0x1ed84`
- `published page records feed 0x1ed84 and 0x1ef6a render entry`

### Disassembly Evidence

- `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`:
  `0x10060..0x10080`
- `generated/disasm/ic30_ic13_active_pool_cycle_001958.lst`:
  `0x1958..0x1fa2`
- `generated/disasm/ic30_ic13_scan_status_interrupt_000f84.lst`:
  `0x0f84..0x1032`
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

- `0x0f84..0x0fa0`, `0x1020..0x108e`, and MMIO/helper calls from the
  wrapper and scheduler loops: the software branch predicates and
  selected variants are modeled, but the physical interrupt entry/exit,
  `$8000`, `$a601`, `$a801`, helper `0xa6cc`, helper `0xa668`, helper
  `0xa680`, and wait/yield helpers `0x10c4`, `0x10c8`, `0x10d0`,
  `0x10d8`, and `0x10e0` still need exact engine-interface meaning.

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
  Evidence: writer `0x12cfe`, default builder `0x12b96`, refresh caller
  `0xe5e2`, consumer `0x1280a`; fixture
  `0x12cfe ESC &l#W loads vertical forms control state`; table-hit
  consumer fixture
  `mixed VFC start-after-text wraps to table hit before printable`; and
  bottom-recovery consumer fixture
  `mixed VFC start-after-text wraps to bottom recovery before printable`;
  macro-layout fixture
  `0xe5e2 refreshes page layout, default VFC table, and static font
  context`.
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
