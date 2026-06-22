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
- `0x782d76 frame +0x00..+0x0d`: non-macro data-chain owners and frame
  lifecycle outside the `0xe418` macro replay fields already pinned.
- `0x780e66` bit meanings: source-empty/active bits are observed by
  behavior, but not yet fully named.

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
  page-length `ESC &l66P!` notes in the ledger.
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
  and transparent-data section; fixture `host-fetched direct
  text/control streams reach page-record render` case `transparent`.
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
  remaining work is the allocator-failure retry branch and live
  nonempty-list insertion coverage.
- `0xd4ac..0xd8fc`: active font/context span update helpers are
  composed as watermark writers in `Text Span Flush And Fixed-Width
  Spans`; remaining work is exhaustive context-record naming for every
  font class.
- `0x11f5a..0x12452`: transparent-text delayed payload restore,
  control filtering, and printable re-entry are documented in
  `notes/transparent-print-data.md`. Printable payload re-entry is
  host-fetched and render-checked for `ESC &p2X!!`; page-record output
  coverage for C0 and `0x80..0x9f` transparent payload bytes remains
  open.
- `0x10084..0x1387c`: first-root allocation and compact text queueing
  are fixture-backed for this cluster, but a dense live parser page that
  exercises same-chunk and rollover allocation for all cursor variants
  is still covered by the shared page-record storage checkpoint rather
  than this section.

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
    nonzero value suppresses queue and span-update side effects.
  - `0x78315c`: default HMI advance used when no source-specific
    advance is available.
  - `0x78318e`: alternate metrics / previous-width mode flag.
  Evidence: generated text-cursor report steps 1-4 and state scan;
  fixtures `two printable byte stream combines compact text entries`,
  `two printable byte stream with line-printer HMI renders subbyte
  entry`, and `0xd824-positioned short bucket object fields`.
- Canonical page/root publication inputs:
  - `0x78297a`: current page root ensured through `0x10084` before
    drawable source queueing.
  - `0x78297e`: selected page-root font slot index copied into source
    `+0x16`.
  - `0x78297f + slot`: live flag set by both `0xd3b2` and `0xd824`.
  Evidence: disassembly `0xd458..0xd47a` and `0xd8a8..0xd8ca`;
  fixtures `0x1387c page-record bucket allocator reuses matching short
  object` and `selected inline source queues and renders through
  unflagged path`.
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
  `0x12f2e-modeled unflagged wide tall inline bucket objects`.
- Parser scratch:
  - `D5` enters `0xd04a` as the printable host byte.
  - `0xd04a` normalizes bytes above `0xff` through `0xd99a`, masks
    high-bit bytes when `0x783132` and `0x783133` allow it, and wraps
    primary-map high-bit masking with `0xc6b8` / `0xc68a`.
  - `0x783132` and `0x783133` are high-character/symbol-state flags
    affecting whether bytes above `0x7f` are masked before `0x1393a`.
  Evidence: disassembly `0xd04a..0xd0e8` and generated printable-text
  path steps 6-9.
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
- `0xd3b2-modeled unflagged source fields`
- `0xd3b2-modeled unflagged overflow source fields`
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
  disassembled and fixture-backed, but high-character masking and every
  `0xd99a` fallback path are not live-stream covered here.
- `0xd28a..0xd3aa` and `0xd6bc..0xd81a`: precheck wrap/recovery paths
  are understood from disassembly, but not every reject/retry branch has
  a visible page-output fixture.
- `0xd47a..0xd4a0` and `0xd8ca..0xd8f0`: allocation failure retry via
  `0xff1e` / `0x10084` is identified in both source handoffs; broad
  dense live-parser coverage remains under page-record allocator work.
- `0xd4ac..0xd548` and `0xd8fc..0xd992`: span watermark writes and the
  downstream `0x12714` / `0x126e2` handoff are composed in
  `Text Span Flush And Fixed-Width Spans`; remaining unresolved edges
  are the allocator-failure retry and split/nonempty insertion branches.
- `0x12f2e..0x1306e`: short and segmented producer shapes are
  fixture-backed, but a full live CPU/register trace through every
  selector mode into real allocator memory remains open.

## Built-In Font Selection To Visible Text

Status: composed as parsed command-family to visible-output checkpoints for
primary and secondary built-in selection streams. The low-level font-selection ledger
remains in [font-context-metrics.md](font-context-metrics.md); this section
records the renderer-facing semantic contract for the selected state.

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

### Field Groups

- Canonical selection request fields:
  - primary request bytes under `0x782eec..0x782ef2`: typeface `3`, style `0`,
    stroke `0`, spacing `0`, pitch `0x03e8`, and height `0x04b0`.
  - dirty flags `0x782f2c` and `0x782f2d`, set by handlers `0xc930`,
    `0xc89c`, `0xc6ec`, `0xc780`, `0xc840`, and `0x1205a`.
  Evidence: fixture `parsed font-selection stream writes primary font-state
  fields`.
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
  Evidence: fixtures `0x13eb8 refresh carries parsed primary font selection to
  dispatch`, `0x13eb8 refresh carries parsed secondary font selection to
  dispatch`, `parsed primary built-in font selection feeds visible
  page-record rows`, and
  `parsed secondary built-in font selection feeds visible SO page-record rows`.
- Canonical visible page-record fields:
  - primary compact text object prefix:
    `00 00 00 00 00 00 00 02 00 6a 00 00 68 02`.
  - secondary compact text object prefix:
    `00 00 00 00 00 01 00 02 00 c9 00 00 cb 01`.
  - render-record context slots: primary slot `0xc008004c`, secondary slot
    `0xc00ae122`.
  - primary compact coords: `0x6a00` and `0x6802`.
  - secondary compact coords after SO: `0xc900` and `0xcb01`.
  Evidence: fixtures `parsed primary built-in font selection feeds visible
  page-record rows` and
  `parsed secondary built-in font selection feeds visible SO page-record rows`.
- Derived/cache state:
  - `0x7828a8`: selected candidate slot `0x782354`.
  - secondary selected candidate slot `0x782350`.
  - `0x782f32`: rebuilt primary map, range `0x21..0xfe`, patch kind
    `unchanged`.
  - `0x783032`: rebuilt secondary map, range `0x21..0xff`, patch kind
    `selected-symbol-not-roman8`.
  - `0x783134`: primary mapped range register, `0x21..0xfe`.
  - HMI/default advance: built-in byte `+0x21 = 0`, long
    `+0x24 = 0x00780000`, converted by `0x10550` to packed advance `30`.
  - secondary HMI/default advance: built-in byte `+0x21 = 0`, long
    `+0x24 = 0x00480000`, converted by `0x10550` to packed advance `18`.
- Parser scratch:
  - fetched stream bytes are split at byte 20: selection bytes
    `ESC (s0p10h12v0s0b3T`, printable bytes `!!`.
  - the secondary fetched stream is split into selection bytes
    `ESC )s0p16h8v0s0b0T` and printable/control bytes `SO !!`.
  - printable parser events are two `0xd04a` entries for the primary fixture,
    and `0xc6b8, 0xd04a, 0xd04a` for the secondary SO fixture.
- Firmware bookkeeping:
  - `0x144d2` writes current-font context record `0x782ee6`.
  - `0x14c64` rebuilds map `0x782f32` and snapshots selected font state.
  - page-root allocation count is `1` when the printable phase queues the
    compact object.
- Unknown:
  - the live CPU-memory continuity from `0x782ee6` / `0x782ef6` after
    `0x13eb8` into the page-record runner is not yet captured; the fixtures
    inject the pinned selected longwords into the printable phase.

### Writers

- `0xc930`, `0xc89c`, `0xc6ec`, `0xc780`, `0xc840`, and `0x1205a` write the
  primary request fields and dirty flags.
- `0x13eb8` filters active candidates through `0x1569c`, `0x156de`,
  `0x153c6`, `0x1519a`, `0x147b2`, `0x14758`, and `0x14398`.
- `0x144d2` writes selected context state at `0x782ee6`.
- `0x144d2` writes secondary selected context state at `0x782ef6`.
- `0x14c64` rebuilds maps `0x782f32` and `0x783032`.
- SO handler `0xc6b8` selects secondary slot 1 before the secondary printable
  bytes are consumed.
- Printable `0xd04a` / `0x1393a` write the source object, and `0x12f2e` /
  `0x1387c` write the compact page-record object.

### Readers And Consumers

- `0x1393a` consumes selected context `0xc008004c` and map `0x782f32` to map
  host byte `0x21` to glyph `0x00`.
- After SO, `0x1393a` consumes selected context `0xc00ae122` and map
  `0x783032` to map host byte `0x21` to glyph `0x00`.
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

### Output Effect

The rendered output is not the default Line Printer `!`. It is two Courier
glyph-0 shapes at x `10` and x `40`, with the first nonblank row:

```text
.............###...........................###...
```

The final printable state has cursor x `60`, cursor y `21`, HMI `30`, and one
page-record root allocation.

The secondary fixture renders two class-one Line Printer glyph-0 shapes after
SO selects slot 1. The first visible row is:

```text
.........################..################...###
```

The final secondary printable state has cursor x `66`, cursor y `21`, HMI
`18`, selector `1`, one `0xc6b8` install call, and one page-record root
allocation.

### Confidence

High for parser handler routing, selected built-in context, map rebuild
metadata, HMI, compact object bytes, render context slot, and final rows
because they are all fixture-pinned against ROM-derived helpers. Medium for
the live current-font-record handoff because the fixture composes the pinned
`0x13eb8` output into the printable runner rather than capturing one
continuous CPU-state execution.

### Fixtures

- `parsed font-selection stream writes primary font-state fields`
- `0x13eb8 refresh carries parsed primary font selection to dispatch`
- `0x13eb8 refresh carries parsed secondary font selection to dispatch`
- `parsed primary built-in font selection feeds visible page-record rows`
- `parsed secondary built-in font selection feeds visible SO page-record rows`

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

- `0x1205a..0x13eb8`: parsed request to refresh is behaviorally composed, but
  a continuous CPU-state trace has not been captured for this stream.
- `0x782ee6 +0x00..+0x0f` and `0x782ef6 +0x00..+0x0f` into
  `0xd04a..0x1393a`: selected current-context RAM is injected from the pinned
  refresh results; live handoff remains open.
- Additional primary/secondary font-selection combinations and fallback/error
  branches still need the same visible-output treatment.

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
  `0x783185=1` produce `high_y=3`.
- Canonical unflagged context inputs:
  - context `+0x2b`: alternate y offset added at `0xd4f8..0xd506`
    when `0x783185` is set and the byte is nonzero.
  - context `+0x2c`: lower y bound consumed at `0xd4c0..0xd4d0`.
  - context `+0x2d`: y-height/page-extent contribution consumed at
    `0xd4da..0xd4ee`.
  Evidence: disassembly `0xd4b8..0xd548` and fixture
  `unflagged printable d4ac low-watermark flush renders span`, where
  `cursor_y=21`, `+0x2b=7`, `+0x2c=0`, `+0x2d=10`, and
  `0x783185=1` produce `high_y=28`.
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
  - selected-context ownership for unflagged context fields `+0x2b`,
    `+0x2c`, and `+0x2d` is documented in
    `notes/font-context-metrics.md`; the remaining gap is proving every
    built-in/downloaded metric-byte form from parser-produced pages.
  - selected-context ownership for flagged context fields `+0x16`,
    `+0x18`, and `+0x1a` is documented in
    `notes/font-context-metrics.md`; the remaining gap is proving every
    built-in/downloaded metric-byte form from parser-produced pages.

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
  `d4ac and d8fc span consumer branch family controls flush output` covers
  the disabled, before-lower, beyond-page, and high-x-only consumer branches.
  Broader metric-byte cross-products and producer-side validation/error
  branches remain uncovered.
- `0xd8fc..0xd992`: flagged context fields `+0x16`, `+0x18`, and
  `+0x1a` are fixture-backed for the low-water success branch and tied
  to selected context records in `notes/font-context-metrics.md`. Fixture
  `host-fetched 0x1719c payload metrics feed d8fc span rows` proves one
  host-fetched type-0 bit-30 downloaded payload copying descriptor words
  into this span consumer, and fixture
  `host-fetched type-2 0x1719c payload metrics feed d4ac and d8fc span rows`
  proves the same copied fields for a host-fetched type-2 payload. Fixture
  `host-fetched type-1 0x1719c payload metrics feed d4ac and d8fc span rows`
  proves the same copied fields for a host-fetched type-1 payload. All three
  change visible segment-list rows. Fixture
  `host-fetched metric variant changes d4ac gate and d8fc rows` changes
  copied word `+0x1a` from a parser-produced descriptor, moving high-y from
  `16` to `19` and changing the rendered span object key from `0x0406` to
  `0x3406`. Fixture
  `host-fetched clamped metric variant changes d4ac gate and d8fc rows`
  changes copied words `+0x18` and `+0x1a` to `0` and `3`, moving high-y to
  `18` and changing the rendered span object key to `0x2406`. Fixture
  `host-fetched lower-bound metric variant suppresses d4ac and d8fc spans`
  raises copied lower word `+0x16` to `0x0018` and derived/cache count
  `+0x18` to `0x05e7`, causing `0xd8fc` to exit `before-context-lower` at
  cursor y `21` while the compact glyph object remains queued. Fixture
  `d4ac and d8fc span consumer branch family controls flush output` covers
  the disabled, before-lower, beyond-page, and high-x-only consumer branches.
  Broader metric-byte cross-products and producer-side validation/error
  branches remain uncovered.

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
- Parser scratch:
  - `0x78299e`: six-byte parsed-record cursor rewound by font handlers.
  - `0x783140`: payload byte budget used by descriptor and payload readers.
- Derived/cache:
  - `0x7827c6`, `0x7827ca`, `0x7827ce`, `0x7827d2`, `0x7827d6`,
    `0x7827d8`, `0x7827da`, and `0x7827c8`: continuation state for
    interrupted font payload reads.
  - `0x782842..0x782851` and `0x782856`: optional symbol bytes and count
    staged by `0x16fae`.
- Firmware bookkeeping:
  - `0x782862`: staging pointer set to `0x7827de`.
  - `0x7827ba`: payload unit count written by `0x17362`.
  - staged header `0x7827de`: copied into allocated payloads by `0x1719c`.
- Unknown:
  - exact HP manual labels for the `0x16fae` consumed-but-not-staged
    descriptor words/bytes.

### Writers

- `0x15a56` and `0x15a18` write current id and character state.
- `0x16df6` dispatches font-control values; `0x17108` and `0x17150` toggle
  current-record bit `6` and transfer counts.
- `0x15d0a` writes `0x783140`, reads descriptor bytes through `0x1599c`, and
  routes to `0x16498`, `0x16606`, `0x15b9a`, or `0x15c4c`.
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

The combined host-fetched stream `ESC *c4660d37e5F` plus `ESC )s2193W`
payload plus `%` sets current id `0x1234`, sets current character `0x25`,
installs a split-plane downloaded glyph object at record delta `0x0500`,
queues printable `%` as segmented compact selector `0x3003`, and renders the
downloaded row through target `0x1effe`. Fixture
`combined font download FF publishes installed glyph page record` appends FF
to that same byte stream, routes `%` and FF through handlers `0xd04a` and
`0xf0f0`, publishes bucket array entries `9` and `1` through `0xff1e`,
preserves empty rule/fixed lists and context prefix `0,0,0,0`, and preserves
the published segmented objects. Fixture
`published downloaded glyph segmented buckets render across bands` copies that
published record through `0x1ed84`, walks modeled band words `1` and `9`
through `0x1ef6a`, dispatches both compact objects to `0x1effe`, leaves the
bucket-1 segment-0 band blank for this payload, and reproduces the same row
from bucket `9`. Fixture
`0x1eba4 scheduler band words render published downloaded glyph` starts from
the `0xff1e`/`0x1ed84` seed where source `+0x18` has been cleared and render
work `+0x10/+0x16` are zero, lets the scheduler loop produce `0x1ef6a` calls
for band words `0..9`, and reaches the same bucket-9 visible row while only
published buckets `1` and `9` dispatch compact objects. Fixture
`host-fetched linear downloaded character stream renders through 0x168dc`
drives `ESC )s6W` through the same parser-delayed `0x16c14` boundary, installs
glyph `0x26` at table entry `0x00e2` with even span `2`, copies bitmap bytes
through the linear `0x168dc` reader, queues normal compact selector `0x0003`,
preserves the object through `0x1edc6`, and renders three mode-0 rows through
`0x1ed84` / `0x1ef6a`. Fixture
`host-fetched 0x15d0a current-record resource object feeds fixed-record
render` also proves a host-fetched `ESC )s0W` descriptor can route bit-30-clear
current-record payload `0x000100` through `0x16606`, install fixed-record glyph
`0x21` at payload table entry `+0x48`, queue selector `0x0003`, preserve
context slot `3` through `0x1edc6`, and render three mode-0 rows. Fixture
`host-fetched 0x15d0a continuation resource object resumes fixed-record
render` proves the sibling status-`2` descriptor route through `0x15c4c`: a
partial `0x16606` copy saves payload `0x000100`, glyph/table index `0x21`,
destination `0x000302`, and remaining count `4`; `0x15c4c` copies bytes
`f0 0f c3 3c`, clears the continuation fields, and renders the same fixed
record and rows.
Fixture `host-fetched 0x15d0a split-plane continuation resource object resumes
fixed-record render` proves the odd-width sibling: a partial `0x16606` copy of
record `03 02 04 00 00 00 02 00` saves payload `0x000100`, glyph/table index
`0x21`, prefix destination `0x000303`, trailing destination `0x000305`, and
D4/D3 counters `0/0`; `0x15c4c` copies bytes `c1 d0`, clears continuation
state, leaves bitmap layout `a0 a1 c0 c1 b0 d0`, queues object prefix
`00 00 00 00 00 03 00 01 01 76 01`, and renders rows reconstructed from
`a0 a1 b0` and `c0 c1 d0`.
Fixture `0x15c4c failed resource resume releases fixed-record object` proves
the status-`0` sibling: a partial `0x16606` copy saves the same payload and
glyph/table index, a short resume copies only bytes `f0 0f`, then `0x15c4c`
calls `0x17d7c`. The release helper rewrites payload `+0x48` from
`02 03 04 00 00 00 02 00` to `01 02 00 fa 00 00 00 00`, writes side-table
bytes `fa 00` at payload `+0x340`, records active-primary refresh
`0x7828de = 0`, and clears the matching continuation fields.
Fixture `0x17d7c releases extended fixed-record table with secondary refresh`
proves the direct extended fixed-record form: payload byte `+0x0e = 1` admits
char `0xa1`, the helper indexes table entry
`payload + 0x40 + (0xa1 - 0x40) * 8`, rewrites it from
`04 05 06 07 00 00 04 00` to `01 02 00 2c 00 00 03 00`, writes side-table
bytes `2c 00` at payload `+0x702`, records active-secondary refresh
`0x7828de = 1`, and clears the matching continuation fields.
Fixture `0x17d7c delegates bit-30 release to offset-table helper` proves the
bit-30 sibling: `0x17d7c` dispatches to `0x17a24`, which validates range words
`+0x0e/+0x10 = 0x0020/0x007f`, uses table offset word `+0x08 = 0x004a`,
clears char `0x21` table entry `00 00 02 40` to zero at payload
`+0x004a + 4 * 0x21`, records active-secondary refresh `0x7828de = 1`, and
clears the matching continuation fields.
Fixture `0x16c14 allocation failure releases existing payload through
0x1887a` has no direct pixel output because it is a failed replacement path.
Its output contract is state cleanup: old current-record payload `0x123456`
is cleared, candidate slot `0x782328` is deleted, extended fixed-record
cleanup runs through `0x18bf2`/`0x18090` for characters `0x21..0x7f` and
`0xa0..0xff`, continuation state is zeroed, context stack bytes `+8` and `+9`
are marked for matching primary/secondary entries, secondary active context
refreshes through `0x179aa(1)`, and no new candidate or payload is installed.
Fixture `0x16fae validation table semantic map covers staged and pass-through
entries` names all 32 validation-table entries by ROM effect. Fixture
`0x16fae table-driven validation predicates populate staged header fields`
then proves the success path plus two predicate failures: invalid resource
type fails entry `2` after four bytes with no symbols copied, and a reversed
range fails entry `6` after words `+0x16 = 10` and `+0x14 = 5`, leaving
derived count word `+0x18 = 0`.
Fixture `ESC )s80W invalid resource type fails validation before allocation`
connects that entry-2 failure to the host-facing parser boundary:
`0xa904` fetches the stream from the ring source, parser dispatch walks
`0x11eb6`, `0x12008`, `0x11ff6`, and `0x11f96`, delayed restore reaches
record `80 57 00 50 00 00`, `0x16fae` fails after descriptor bytes
`00 01 02 03`, and `0x17026`/`0x16c14` skip allocation and install. The
output effect is no downloaded-font candidate or current-record mutation.
Fixture `ESC )s80W reversed resource range fails validation before allocation`
connects the entry-6 range/count failure to the same host-facing parser
boundary. `0xa904` fetches
`1b 29 73 38 30 57 00 01 00 00 00 00 00 0a 00 06 00 05...` from the ring
source, parser dispatch again walks `0x11eb6`, `0x12008`, `0x11ff6`, and
`0x11f96`, delayed restore reaches record `80 57 00 50 00 00`, `0x16fae`
fails after twelve descriptor bytes with staged words `+0x16 = 10`,
`+0x14 = 5`, and `+0x18 = 0`, and `0x17026`/`0x16c14` skip allocation and
install. The output effect is no downloaded-font candidate or current-record
mutation.
Fixture `host-fetched metric variant changes d4ac gate and d8fc rows` starts
from host-fetched `ESC )s80W`, changes descriptor bytes copied by `0x1719c`
into payload word `+0x2c = 0x0010` and word `+0x1a = 0x0002`, proves the
default `+0x2d = 0x20` path fails a tight `0xd4ac` extent check while the
variant queues a span, and renders the `0xd8fc` span at shifted key `0x3406`.
Fixture `host-fetched clamped metric variant changes d4ac gate and d8fc rows`
adds the rounded-metric clamp sibling: descriptor range/count `+0x14 = 5`
caps an oversized rounded input so `0x1719c` copies `+0x2c = 0x0014`, leaves
`+0x2b = 0`, flips a tight `0xd4ac` extent gate with `+0x2d = 0x14`, and
renders the `0xd8fc` span at shifted key `0x2406` from copied words
`+0x18 = 0` and `+0x1a = 3`.
Fixture `host-fetched lower-bound metric variant suppresses d4ac and d8fc
spans` adds the lower-bound sibling: host-fetched descriptor bytes write
canonical lower fields `+0x16 = 0x0018` and `+0x2c = 0x1800`, range/count
`+0x14 = 0x0600`, and derived/cache count `+0x18 = 0x05e7`. `0xd4ac` reads
byte `+0x2c = 0x18`; `0xd8fc` reads word `+0x16 = 0x0018`; both return
`before-context-lower` at cursor y `21`, and the fixture renders only the
compact glyph objects from the page-record buckets.
Fixture `host-fetched segmented downloaded character renders through 0x1f1f0`
connects the downloaded-character linear reader to the remaining segmented
compact renderer shape. Host fetch drains `ESC )s258W`; parser dispatch walks
`0x11eb6`, `0x12008`, `0x11ff6`, and `0x11f96`; `0x16498` installs glyph
`0x27` at table entry `0x00e6` with record delta `0x0580`, rows `0x0081`,
width `0x0010`, bitmap offset `0x058c`, and `0x0102` bytes copied through
`0x168dc`; `0x12f2e` queues selector `0x2003`; `0x1edc6` preserves the
segment-1 object; and `0x1ef6a` reaches compact renderer `0x1f1f0`. The
visible output is one segment-1 row from source offset `0x0100`, rendered at
x `22` as `####........####`.
Fixture `host-fetched split-plane segmented downloaded character renders
through 0x1f1f0` adds the odd-span A2/A3 sibling. Host fetch drains
`ESC )s387W`; `0x16498` installs glyph `0x28` at table entry `0x00ea`, record
delta `0x0700`, rows `0x0081`, width `0x0018`, bitmap offset `0x070c`, and
`0x0183` bytes copied through `0x16942`. `0x12f2e` still queues selector
`0x2003`, but `0x1f1f0` validates A2 source offset `0x0100` and A3 trailing
offset `0x0080` for segment `1`. The visible output is
`####........#####.#.#.#.` at x `22`.
Fixture `host-fetched even-span wide downloaded character renders through
0x1f0d2` covers the wide selector without payload-control normalization:
`0xa904` fetches `ESC )s18W`, parser dispatch reaches delayed handler
`0x16c14` with restored record `80 57 00 12 00 00`, `0x16498` installs glyph
`0x29` at table entry `0x00ee`, record delta `0x0780`, rows `1`, width
`0x0090`, bitmap offset `0x078c`, and split-plane flag `false`, and
`0x168dc` copies all 18 bytes with `control_hits = 0`. `0x12f2e` queues
selector `0x1003` and bucket object
`00 00 00 00 10 03 00 01 29 66 01` plus allocator padding; `0x1edc6`
preserves it; and `0x1ef6a` reaches compact renderer `0x1f0d2`, where the
linear source row uses one full 16-byte chunk plus a 2-byte remainder and
renders at x `22`.

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
  `0x16498` using the linear `0x168dc` reader. Consumer: compact renderer
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
- Unknown for this checkpoint: exact live parser scheduling between the font
  download and the page stream inside real CPU memory. The page stream itself
  now drives the glyph, rule, and raster producers together; the font payload
  install still enters the page phase as a modeled resource image.

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

High for command dispatch, current-record state, existing-record release
ordering before allocation failure, staged header fields, payload allocation,
installed downloaded-character object, and visible row, because the fixtures
tie host-fetched streams to parser records, teardown state, and render rows.
High for the downloaded-character parser-to-page path for the normal,
wide/control, even-span wide, segmented, and segmented-wide compact selectors
represented by fixtures `host-fetched linear downloaded character stream
renders through 0x168dc`, `host-fetched downloaded character payload control
reaches wide render`, `host-fetched even-span wide downloaded character
renders through 0x1f0d2`, `host-fetched segmented downloaded character renders
through 0x1f1f0`, `host-fetched split-plane segmented downloaded character
renders through 0x1f1f0`, and `host-fetched downloaded character stream
reaches rendered object`. High for the modeled FF publication boundary of the
combined downloaded-glyph stream because the fixture asserts the full fetched
stream boundaries, published bucket array entries `1` and `9`, selected render
bucket words `1` and `9`, dispatch target, and final rows. High for
publication-to-scheduler band progression because `0xff1e` disassembly at
`0xffc8` clears root `+0x18`, `0x1ed84` copies that word into render
`+0x10/+0x16`, and fixture
`0x1eba4 scheduler band words render published downloaded glyph` proves
`0x1eba4` emits band words `0..9` through `0x1ef6a` and preserves the same
visible row.
High for downloaded-glyph/rule/raster render composition because fixture
`host-fetched downloaded glyph composes with rule and raster through 0x1ef6a`
asserts the `ESC )s18W` install fields, bucket-5 glyph/raster objects, bridged
selector-7 rule object, `0x1ef6a` call order, dispatch targets `0x1f88e` and
`0x1effe`, rule helper `0x1f596`, and composed output rows.
High for parser-driven page-stream composition because fixture
`parser-driven downloaded glyph rule raster stream composes through 0x1ef6a`
asserts the post-font page bytes, handlers `0x10e68`, `0x10e22`, `0x10898`,
`0xd04a`, `0x10808`, `0x1075a`, and `0x11f82`, delayed raster record
`80 57 00 02 00 00`, payload offset `28`, bucket-5 chain, bridged rule list,
and the same composed rows.
High for the ROM-effect names and failure behavior of every `0x16fae`
validation-table entry, including the host-fetched invalid-type, first-code
overflow, zero/high line-count, reversed/high range-count, and invalid-class
no-install boundaries. Medium for the complete soft-font grammar because exact
HP manual labels for pass-through descriptor fields and every legal metric
combination have not been page-compared.

### Fixtures

- `combined host-fetched font download stream prints installed glyph`
- `combined font download FF publishes installed glyph page record`
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
- `ESC )s80W validation failures preserve following printable output`
- `host-fetched type-2 0x1719c payload metrics feed d4ac and d8fc span rows`
- `host-fetched type-1 0x1719c payload metrics feed d4ac and d8fc span rows`
- `host-fetched metric variant changes d4ac gate and d8fc rows`
- `host-fetched clamped metric variant changes d4ac gate and d8fc rows`
- `host-fetched lower-bound metric variant suppresses d4ac and d8fc spans`
- `0x16498-backed downloaded character object renders segmented-wide compact
  row`
- `host-fetched linear downloaded character stream renders through 0x168dc`
- `host-fetched downloaded character payload control reaches wide render`
- `host-fetched even-span wide downloaded character renders through 0x1f0d2`
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
  `ESC )s80W validation failures preserve following printable output` proves
  those seven no-install exits leave the next printable `!` on the unchanged
  default-font page-record path with matching rendered rows. Remaining
  descriptor error-form risk is now variants beyond those bounded predicate
  branches, plus external HP manual naming for consumed-but-not-staged fields.
- `0x16498..0x16942`: split-plane segmented-wide, wide/control, even-span
  wide, linear normal, linear segmented, and split-plane segmented
  downloaded-character paths are page-visible. Remaining parser-produced
  comparisons are the cross-product variants not covered by those shapes,
  especially alternate row counts, character modes, and non-success exits for
  the same selector families.
- downloaded-glyph plus rule/raster producer schedule: fixture
  `parser-driven downloaded glyph rule raster stream composes through
  0x1ef6a` closes the page-stream boundary from parser-produced `0x10898` rule
  insertion, downloaded-current printable queue through `0x12f2e`, and delayed
  `0x105d0` / `0x13070` raster transfer into one bucket-5 render entry.
  Remaining risk is the earlier font-install-to-page handoff: the same fetched
  byte stream is split at byte `24`, and the `0x16c14` installed memory image
  is supplied to the page-stream runner instead of captured from a live CPU
  memory run.
- `0xff1e..0x1ed84`: the combined downloaded-glyph stream now publishes both
  segmented buckets, and fixture
  `published downloaded glyph segmented buckets render across bands` renders
  published bucket words `1` and `9` from the copied record. Fixture
  `0x1eba4 scheduler band words render published downloaded glyph` proves
  `0xff1e`/`0x1ed84` seed render work `+0x10/+0x16` from cleared source
  `+0x18 = 0`, then `0x1eba4` advances through band words `0..9` until the
  published bucket-9 row is visible. The earlier first-band seed edge is now
  closed for this published record.
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
  consumers, the shared consumer branch family, and three parser-produced
  metric-value variants that flip tight `d4ac` page-extent gates, exercise
  rounded-metric clamping into `+0x2c/+0x2d`, move `d8fc` visible rows, and
  suppress both span consumers through copied lower-bound fields while
  preserving compact glyph output. It still needs broader metric-byte
  cross-products and producer-side validation/error page evidence beyond the
  documented validation no-install and following-printable boundaries.

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
  Evidence: fixtures `macro execute data-chain parser trace feeds
  page-record stream`, `macro call data-chain parser trace feeds
  page-record stream`, `host-fetched macro replay payloads feed 0x1ed84
  and 0x1ef6a`, and `macro overlay finalization replays before page
  publication`.
- Unknown:
  - startup option source for the optional `0x80` addition to
    `0x780e5a` still needs board/config correlation, but the downstream
    `0x0b18` heap-limit math and `0x164a` allocator initialization are
    pinned for the default path.
  - no remaining macro execute/call replay, font-context, or first
    overlay-publication middle edge in this checkpoint. The next
    high-value edges are broader overlay page-boundary interactions,
    descriptor metric producer validation, and final device-output
    validation.

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
  or the first overlay-publication path. Remaining macro risk is broader
  overlay interaction coverage, such as multiple overlays across page
  boundaries and final-device comparison, not the `0xdd08` selector-4 to
  `0xff1e` visible-output path pinned by fixture `macro overlay
  finalization replays before page publication`.

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

- `0xd04a..0x12f2e`: source-object fields, paired queue handoffs, and
  compact producer semantics are composed in `Text Source Objects And
  Compact Buckets`; this mixed stream still lacks a full live
  CPU/register trace for the complete parser-produced dense page.
- `0x10898..0x133aa`: the addressed rule insertion is modeled from
  disassembly and fixtures and documented in
  `notes/rectangle-graphics.md`, but the exact live no-room/retry edge is
  not covered in this mixed stream.
- `0x105d0..0x13250`: the raster object queue and render contract are
  documented in `notes/raster-graphics.md`; the queue is address-aware,
  but the mixed stream still lacks a full 68000 execution through
  `0x105d0` into real allocator memory.
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
