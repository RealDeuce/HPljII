# End-To-End ROM Reproduction Map

Goal: reproduce LaserJet II output pixels from the same host byte stream by
using ROM-derived parser behavior, state fields, page-record formats, and
render routines. The primary explanatory spine is
[firmware-dataflow-model.md](firmware-dataflow-model.md). This note is the
current coverage/evidence map for that pipeline; detailed ledgers remain in
`notes/reverse-engineering-ledger.md` and `notes/semantic-state-model.md`.

## Pipeline Contract

```text
host bytes
  -> 0xa904 normalized byte fetch
  -> 0xda9a / 0xdaf0 / 0xdb74 parser and six-byte command records
  -> command handlers and delayed payload handlers
  -> page-root/display-list objects
  -> 0xff1e publication
  -> 0x1ed84 / 0x1edc6 render-record bridge
  -> 0x1ef6a band render dispatch
  -> compact text, segment-list, rule, fixed-width, and raster renderers
```

Every reproduction claim below requires a checked-in note that names the ROM
address boundary and cites either executable fixture evidence, focused
disassembly, or a generated analysis report used as supporting material. The
checked-in note is the deliverable; ignored generated reports are supporting
evidence, not the only documentation.

Coverage means a checked-in note names the ROM address range, field
writers, field readers/consumers, visible or state output, fixtures, and
disassembly evidence for that edge. For example, host byte-source coverage
means `0xa904..0xabf0` and its fixtures define which firmware byte source
feeds parser `0xda9a` / `0xdaf0` / `0xdb74`; it does not mean every
physical bus signal has been named. Render coverage means
`0x1ed84` / `0x1edc6` / `0x1ef6a` plus the compact, segment-list, rule,
fixed-list, and raster helpers define the byte-to-bitmap state for the cited
fixtures; it does not require formatter/DC timing proof.

The physical timing boundary is separate from ROM-local reproduction
coverage. Timing-sensitive surfaces are host fetch/polling
(`0xa904..0xab8a`), scan/status interrupt and wait-object dispatch
(`0x0f84..0x1282`), and active render scheduling
(`0x1eb2a..0x1ed84`). The current fixtures prove the state effects after
those events are observed: pending bytes `0x78399e/0x78399f`, shadow byte
`0x7828f9`, wait-object state, active source `0x780eae`, active work pointer
`0x783a18`, and band words. Board evidence is only needed when a claim
depends on mapping physical formatter/DC connector signals or MMIO bits that
the ROM treats as external events. The named physical formatter/DC edge is
connector `J205`: `BD`, `VDO`, `VSREQ`, `VSYNC`, `PRNT`, command/status
strobes, and ready signals. Current ROM evidence does not yet map those
signals to exact MMIO bits; the board-facing boundary is tracked in
[dc-controller-engine.md](dc-controller-engine.md).

## Current End-To-End Coverage

- Host byte source priority and callers:
  ROM evidence is `0xa904..0xabf0` in
  `generated/disasm/ic30_ic13_host_byte_fetch_00a904.lst`; the checked-in
  semantic checkpoint is [host-byte-fetch.md](host-byte-fetch.md), with
  primary entry point `Worked Path: Host Byte Source Priority` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md).
  Reproduction evidence includes fixtures for no-byte, service retry, LIFO,
  data-chain, ring, and direct modes, plus the all-caller classification
  promoted from `generated/analysis/ic30_ic13_host_byte_fetch_flow.md`.
  All `19` direct `JSR 0xa904` sites are grouped there by parser wrapper,
  `0x1a 0x58` probe, display/text readers, raster payload, downloaded-font
  payload, and macro replay data-chain behavior. The observed data-chain frame
  layout is composed with the byte-source checkpoint: `0x782d76` points at
  frame `+0x00` payload/chunk pointer, `+0x04` byte count or `-1` end marker,
  byte `+0x08 = 4`, byte `+0x09` as execute `2`, call `3`, or non-replay
  page-finalization `4`, and longword `+0x0a` as snapshot pointer or zero.
  Remaining host-input risk is physical MMIO naming/timing and any producer
  for other frame `+0x09` values, not byte-source priority, direct caller
  classification, or observed macro/data-chain replay.
- External service/status preemption:
  ROM evidence is `0xba48..0xc36e` in
  `generated/disasm/ic30_ic13_external_ready_service_loop_00ba48.lst` and
  `generated/disasm/ic30_ic13_external_service_reset_00c06e.lst`.
  Reproduction evidence is
  [external-ready-service.md](external-ready-service.md),
  `External Ready And Service Status Loop` in `notes/semantic-state-model.md`,
  and `Worked Path: External Ready Service Preemption` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md), plus fixtures for
  `0xc0ae` publishing
  `$fffee005.7/.6` through `0x9bee(0x780e2e, 0x80/0x40)`, `0xc1c6`
  entering non-returning `68 SERVICE` at `0x85c0` from
  `0x780e36 & 0x00000008`, and `0xc1c6` replaying pending buffer
  `0x782312` through `0x8c7a` when no status bits are active. This cluster
  is not a page-imaging producer, but it can stop or defer normal parsing
  before page objects are generated. The teardown handoff through
  `0xc108 -> 0x19dd2 -> 0x36e4` is now bounded in
  [page-font-scheduler.md](page-font-scheduler.md) and
  `Page/Font Scheduler Handoff`: `0x19dd2` publishes scratch pointer
  `0x782894`, `0x19eb6` scans optional windows `0x200000..0x3ffffe` and
  `0x400000..0x5ffffe` when `$8000.14/15` permit it, `0x1a042` and
  `0x19f08` compare those scratch slots against canonical slots at
  `0x7828b6`, and the status branch can raise
  `0x9bee(0x780e2e, 0x00000200)` with byte `0x780e8d`. Remaining risk is the
  board-level external-register identity, hardware/emulator evidence for
  `0x571e -> 0x9bee -> 0xc1c6 -> 0x85c0`, and physical optional-resource
  contents for the changed optional-window scheduler sequence now modeled by
  fixture
  `0x19dd2 optional-window change composes refresh helpers`. That fixture drives
  `0x19dd2 -> 0x1ba92/0x178fa/0x19d9c/0x1a4fa/0x1a900` and proves candidate-list,
  current-record, canonical-window, and active-context effects for synthetic
  inputs; fixture `0x19dd2 modeled unchanged and status branch exits` pins the
  both-zero and `0x72a2 == 0` status-return contracts for modeled predicates.
  Physical optional-window contents remain open. Candidate-slot
  deletion/compaction through `0x1bd2e`, scanner behavior through `0x1a616`,
  teardown through `0x1887a`, active-context lookup through `0x1b4c0`, and
  font/default refresh through `0x1b04c` / `0x179aa` are documented in sibling
  semantic checkpoints. Fixture `0x447a/0x4760 consume scheduler return
  differently` now pins the host-quiesce caller contract: `0x447a` ignores
  `D7`, while `0x4760` returns immediately for `D7 = 0` and enters menu/default
  state setup for `D7 != 0`. Fixture `0xbb0a external-ready teardown ignores
  scheduler return` pins the external-ready caller contract:
  `0xc108 -> 0x19dd2 -> 0x36e4` ignores scheduler `D7` and writes `0x780e08`
  from the following status aggregate. Fixture
  `0x1a2e4 font scan ignores scheduler return` pins the font-resource-scan
  caller contract: `0x1a3b8` snapshots `0x78278e` into `0x782780`,
  `0x1a3c2` ignores scheduler `D7`, `0x1a3c8..0x1a3e0` passes
  `0x78219b/0x78219c` plus local `A6-0x02` to `0x1b50e`, and only resolver
  `D7 == 0` reaches `0x6364`.
- Host/status side channels:
  ROM evidence is `0x12034`, `0x122be..0x12326`,
  `0xb022..0xb0c0`, `0xae2c..0xaece`, and `0x2888..0x2c3a`.
  Checked-in documentation is [errors-and-status.md](errors-and-status.md),
  [io-interfaces.md](io-interfaces.md), [host-byte-fetch.md](host-byte-fetch.md),
  and the semantic checkpoints `Host Interface Output FIFO` and
  `Page Environment Status And Pool Cursor Gate` in
  [semantic-state-model.md](semantic-state-model.md), surfaced first as
  `Worked Path: Host Interface Output FIFO And Model-ID Backchannel` and
  `Worked Path: Page Environment Status Bridge` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md). This cluster has
  no direct page-object or pixel effect: `ESC *r1K 11` and the `ESC *s#^`
  sibling enqueue literal `33440A\r\n` through host-output FIFO helpers, and
  status producers such as `0x2888` feed outbound status bytes through
  `0xaece`. It still belongs in byte-stream reproduction because a full FIFO
  can stall producer `0xb090`, and a bidirectional host can react to the
  backchannel bytes by sending different future input.
- Parser byte and command records:
  ROM evidence is `0xda9a`, `0xdaf0`, `0xdb74`, and `0x11774`.
  The checked-in contracts are [pcl-parser-core.md](pcl-parser-core.md) and
  `Parser Record And Delayed Payload State` in
  [semantic-state-model.md](semantic-state-model.md), surfaced first as
  `Worked Path: Command Record And Payload Dispatch` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md). Supporting evidence
  is `generated/analysis/ic30_ic13_parser_xrefs.md` plus tokenizer and
  delayed-payload fixtures. Command finals and payload bytes are separate
  events, six-byte records are saved through `0x121cc`, restored through
  `0x12218`, and then consumed by raster, transparent text, downloaded-font,
  generic payload, macro, and alternate/data handlers.
- Ignored and no-output parser rows:
  ROM evidence is parser loop `0x11774`, terminal reset path
  `0x11912..0x119bc`, delayed restore helper `0x12218`, normal parser table
  `0x112a4`, and alternate/data parser table `0x116f6`. Checked-in
  documentation is [pcl-parser-core.md](pcl-parser-core.md),
  [pcl-command-map.md](pcl-command-map.md), and `Parser Record And Delayed
  Payload State` in [semantic-state-model.md](semantic-state-model.md),
  surfaced first as `Worked Path: Explicit No-Output Parser Rows` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md). Normal mode-zero
  bytes `0x00`, `0x07`, and `0x0b` are explicit zero-handler rows: they write
  next mode `0`, run pending delayed restore through `0x12218`, reset
  `0x78299e`, `0x782a26`, `0x782a3e`, `0x782a56`, and matched-byte scratch,
  and do not allocate a page root, queue a page object, publish a record, or
  schedule render work. Alternate/data blank C0 rows `0x00` and `0x07..0x0f`
  append through `0xe002` before the same terminal reset path instead of
  running normal BS/HT/LF/FF/CR/SO/SI handlers. Related parser artifacts are
  bounded separately: `ESC ?` is consumed in wrapper `0xda9a`, `ESC Z`
  terminates the direct display-functions reader, and `ESC &lT/t` has no
  standalone page-output effect.
- Transparent print data:
  ROM evidence is `0x11f5a`, `0x12452`, `0xd04a`, `0xd0f0`, and `0xd550`,
  plus disassembly
  `generated/disasm/ic30_ic13_transparent_data_handler_011f5a.lst`.
  Reproduction evidence is [transparent-print-data.md](transparent-print-data.md).
  The tracked semantic contract is that `ESC &p#X` is a counted delayed
  byte-stream splice, not an opaque skip. Handler `0x11f5a` schedules
  `0x12452` through `0x121cc`; `0x12218` restores command record
  `80 58 ...`; `0x12452` consumes the absolute record word `+2` count from
  `0xa904`, preserves local `1a 58 -> 7f` and `1a xx -> xx` behavior, and
  routes normalized payload bytes through `0xd04a` or `0xd0f0` according to
  context filtering. Canonical fields are the command-record count, selected
  context slot `0x782f06`, and text cursor `0x782c8a`; parser scratch is
  `0x782a1a`, `0x782a1c`, and `0x782a20..0x782a25`; derived/filtering state
  is `0x782eea + 0x10 * 0x782f06`, `0x782efa`, and high-byte flags
  `0x783132`/`0x783133`. Remaining risk is the secondary segment-57
  resource-window continuation, tracked by
  `Boundary: Secondary Segment-57 Source` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md): fixture
  `transparent secondary segment-57 continuation policies diverge after
  verified bytes` pins glyph `0x5f`, segment `0x39`, firmware source
  `0x0bfe22`, required range `0x0bfe22..0x0c0321`, and the first `478`
  bytes inside the verified `IC32,IC15` resource-pair image. Scanner fixtures
  `0x41a HEAD scanner would duplicate records under simple resource mirror`
  and `0x41a HEAD scanner rejects non-HEAD 0x40000 continuations` constrain
  the physical continuation hypotheses. Startup checksum evidence narrows but
  does not close the edge: [firmware-startup.md](firmware-startup.md) records
  the resource-pair byte-sum range as `0x080000..0x0bffff`, so it covers the
  verified suffix but not the `0x0c0000` continuation bytes.
- Display functions:
  ROM evidence is normal handler `0x12536..0x1261e`, alternate/data handler
  `0x12120..0x1219c`, and parser-table entries in normal table `0x112a4`
  and alternate table `0x116f6`. Reproduction evidence is
  [display-functions.md](display-functions.md),
  `Display Functions ESC Y Reader` in `notes/semantic-state-model.md`,
  `ESC Y Display Functions Readers` in `notes/pcl-parser-core.md`, surfaced
  first as `Worked Path: Display Functions Direct Reader` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md), and disassembly
  `generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst`.
  The covered command-family contract is `ESC Y ... ESC Z` as a direct
  `0xa904` reader loop with local `1a 58 -> 7f` normalization, loop-local
  `ESC`-seen scratch in `D4`, normalized payload byte in `D7`, and termination
  when routed/appended `ESC Z` is seen or fetch returns `-1`. Normal handler
  `0x12536` routes normalized bytes through `0xd04a` or `0xd0f0` according to
  selected-context filtering state: canonical `0x782c18`, `0x782f06`, and
  parser dispatch state; derived/filtering state
  `0x782eea + 0x10 * 0x782f06`, `0x782efa`, `0x783132`, and `0x783133`; and
  parser scratch stack word `A6-2`. Alternate/data handler `0x12120` appends
  literal `ESC Y` plus normalized loop bytes through firmware bookkeeping sink
  `0xe002` into macro/data-chain chunk `0x783988`; normal CR output also uses
  bookkeeping helper `0xf054`. Fixtures
  `ESC Y display-functions stream reaches page-record output`,
  `ESC Y display-functions filter-on routes controls as printable`, and
  `0x12120 ESC Y alternate append stores normalized display bytes` cover the
  default-filter page-output path, nonzero context/filter page-output path,
  and alternate/data append-only path. No unresolved middle edge remains for
  this command-family loop.
- Parser dispatch tables:
  ROM evidence is normal table `0x112a4` and alternate table `0x116f6`.
  Checked-in documentation is [pcl-command-map.md](pcl-command-map.md),
  [pcl-parser-core.md](pcl-parser-core.md), and the command-family checkpoints
  in [semantic-state-model.md](semantic-state-model.md), surfaced first as
  `Worked Path: Command Record And Payload Dispatch` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md). Supporting evidence
  is `generated/analysis/ic30_ic13_pcl_command_map.md` and ROM dispatch trace
  fixtures. The `Checked-In Semantic Anchors` section in
  [pcl-command-map.md](pcl-command-map.md) is the current command-family index:
  it maps parser rows to the checked-in notes that already carry field groups,
  writers, readers/consumers, output effects, fixtures, and disassembly
  evidence.
- Direct controls and cursor state:
  ROM evidence includes `0xf02c`, `0xf06e`, `0xf34a`, cursor handlers
  `0xf39e` / `0xf416` / `0xf48c` / `0xf560` / `0xf60a` / `0xf692`, page
  length handler `0xf9e8`, wrap handler `0xedb0`, and perforation-skip handler
  `0xee64`.
  Reproduction evidence is `Text Cursor And Direct Controls` in
  `notes/semantic-state-model.md`, surfaced first as
  `Worked Path: Mixed Direct Controls` and
  `Worked Path: Cursor And Margin Placement` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md), plus host-fetched
  direct-control fixtures. Layout-control evidence is surfaced first as
  `Worked Path: Page Length, Wrap, And Perforation Controls`: `ESC &l#P`
  writes page extent `0x782dba`, `ESC &s#C` writes end-of-line wrap flag
  `0x783190`, and `ESC &l#L` writes perforation-skip byte `0x783191`.
  Those commands normally do not draw immediately; their visible effect is
  through later printable prechecks `0xd28a` / `0xd6bc`, vertical overflow
  helper `0xf36c`, or the following printable path `0xd04a -> 0x12f2e`.
- Text source object creation:
  ROM evidence is `0xd3b2`, `0xd824`, `0x12f2e`, and `0x1387c`.
  Reproduction evidence is `Text Source Objects And Compact Buckets` in
  `notes/semantic-state-model.md`, surfaced first as
  `Worked Path: Text Source Objects And Compact Buckets` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md), plus compact text
  bucket render fixtures.
- Pending text span flushing:
  ROM evidence is `0xd4ac`, `0xd8fc`, `0x126e2`, `0x12714`, and
  `0x13520`.
  Reproduction evidence is `Text Span Flush And Fixed-Width Spans` in both
  `notes/semantic-state-model.md` and `Worked Path: Text Span Flush And
  Fixed-Width Spans` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md), plus CR,
  left-margin parser, vertical-cursor parser, low-water, split, nonempty, and
  retry fixtures.
- Page-root storage:
  ROM evidence is `0x10084`, `0x10110`, `0x1381c`, and `0x1387c`.
  Reproduction evidence is `Shared Page-Record Storage And Allocator`,
  surfaced first as `Worked Path: Shared Page-Record Storage And Allocator` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md), addressed storage
  fixtures, and chunk-rollover fixtures.
- Rule/rectangle producers:
  ROM evidence is `0x10898`, `0x10b80`, `0x13386`, and `0x133aa`.
  Reproduction evidence is `notes/rectangle-graphics.md` and
  parser-to-rule fixtures, surfaced first as `Worked Path: Rectangle Rule` and
  `Worked Path: Rectangle Rule Selectors And Clipping` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md), including
  `host-fetched alternate rectangle selectors feed full page records` and
  `host-fetched rectangle selector matrix feeds full page records`.
- Raster producers:
  ROM evidence is `0x10808`, `0x1075a`, `0x105d0`, `0x13070`, and
  `0x13250`.
  The checked-in command-family checkpoint is
  [raster-graphics.md](raster-graphics.md), with semantic checkpoint
  `Raster Transfer Gate And Encoded Rows` in
  [semantic-state-model.md](semantic-state-model.md), surfaced first as
  `Worked Path: Raster Row` and
  `Worked Path: Raster Transfer Gates And Modes` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md). Supporting evidence
  is `generated/analysis/ic30_ic13_raster_graphics_flow.md` and host-fetched
  raster stream fixtures. The checkpoint covers lower-resolution modes `1..3`,
  consecutive uppercase `ESC *b#W` transfers, lowercase `ESC *b#w` same-family
  chaining, `ESC *rB` active-byte clear, active-resolution ignore, `0x105d0`
  cap/drain gates, page-record object bytes, bridge dispatch, and rendered rows.

  The mixed page-image cluster is now composed in `Mixed Text/Rule/Raster Page
  Record`: fixture
  `host-fetched text rectangle raster FF publishes rendered page record`
  drives `! ESC *c12a5b0P ESC *t300R ESC *r0A ESC *b2W c3 3c FF` from the
  modeled `0xa904` host source through parser handlers, delayed `0x105d0`,
  `0xff1e`, `0x1ed84`/`0x1edc6`, and final row comparison. Fixture
  `addressed text/rule/raster field groups reach publication and render entry`
  names the same materialized objects: text object `0x00d0c004`, rule object
  `0x00d0c02a`, raster object `0x00d0c038`, restored raster record
  `80 57 00 02 00 00`, payload `c3 3c` at offset `28`, stream allocator
  bookkeeping `0x782a70 = 0x00bc`, `0x782a72 = 0x00d0c000`,
  `0x782a76 = 0x00d0c044`, and render caches `0x783a20 = 0x0050`,
  `0x783a22 = 0`, `0x783a28 = 0x00100000`. Fixture
  `addressed text/rule/multi-row raster publication preserves bucket chain`
  covers the sibling with two delayed raster transfers, raster objects
  `0x00d0d038` and `0x00d0d044`, bucket chain
  `0x00d0d044 -> 0x00d0d038 -> 0x00d0d004`, allocator bookkeeping
  `0x782a70 = 0x00b0`, `0x782a72 = 0x00d0d000`,
  `0x782a76 = 0x00d0d050`, and final raster row counter `2`.

  The current handoff ledger pins field ownership across `0x105d0`,
  `0x10084`, `0x13070`, `0x13250`, and `0x132b6`: `A4 = 0x783170`,
  restored record `A5 = 0x78299e - 6`, accepted/overflow words
  `+0x04/+0x06`, row word `+0x02`, current root `0x78297a`, bucket/key caches
  `0x782a7c/0x782a7e`, stream chunk state `0x782a70/0x782a76/0x782a80`, and
  copy-stop flag `0x782996`. No remaining ROM semantic boundary is assigned to
  that handoff. Further ROM work should target streams that change the
  `0x105d0 -> 0x10084 -> 0x13070 -> 0x13250 -> 0x132b6` gate outcome,
  raster-object fields, bridge state, render dispatch, or reproduction
  contract.
- Page publication:
  ROM evidence is `0xff1e..0x10080`.
  Checked-in documentation is
  [publication-commands.md](publication-commands.md) and
  `Publication Commands To Rendered Page Records` in
  [semantic-state-model.md](semantic-state-model.md), surfaced first as
  `Worked Path: Reset And Default Environment`, `Worked Path: FF Publication`,
  and `Worked Path: Publication Commands To Rendered Page Records` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md). Supporting evidence
  is `generated/analysis/ic30_ic13_page_root_finalization.md` plus reset, FF,
  geometry, and retry publication fixtures.
- Macro/data-chain replay:
  ROM evidence is `0xe112`, `0xdd08`, `0xe0a4`, `0xe002`, `0xe418`,
  `0xe4f4`, `0xe22c`, `0xe65c`, byte-source multiplexer `0xa904`, parser loop
  `0x11774`, and publication branch `0xff1e..0xff8e`. Checked-in
  documentation is [macro-data-chain.md](macro-data-chain.md) and
  `Macro Definition And Data-Chain Replay` in
  [semantic-state-model.md](semantic-state-model.md), surfaced first as
  `Worked Path: Macro Execute Replay` and
  `Worked Path: Macro Overlay Replay Publication` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md). The covered
  execute/call path defines macro id `123`, stores payload `21 0d`, builds a
  data-chain frame with `+8 = 4` and frame kind `+9 = 2` or `3`, lets
  `0xa904` replay the stored bytes ahead of live input, and routes them back
  through normal parser handlers `0xd04a` and `0xf02c` to the same compact text
  page object and render path as live host bytes. The overlay path stores
  selector state `0x782a92/0x782a94`; `0xff1e` resolves the saved record,
  builds a non-replay frame through `0xe4f4`, re-enters parser loop `0x11774`,
  and queues replayed text, controls, transparent payloads, spans, or raster
  objects before the page is published.
- Render bridge:
  ROM evidence is `0x1ed84`, `0x1edc6`, and `0x1ef86`.
  Checked-in documentation is [page-record-storage.md](page-record-storage.md),
  [page-raster-imaging.md](page-raster-imaging.md), and the publication/render
  entries in [semantic-state-model.md](semantic-state-model.md), surfaced first
  as `Worked Path: Published Record To Active Bands` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md). Supporting evidence
  is `generated/analysis/ic30_ic13_page_record_bridge.md` and published-record
  render-entry fixtures.
- Active render scheduler:
  ROM evidence is `0x1eb2a`, `0x1ecd6`, `0x1ed84`, and `0x1eba4`.
  Reproduction evidence is
  [active-render-scheduler.md](active-render-scheduler.md), surfaced first as
  `Worked Path: Published Record To Active Bands` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md), plus
  scheduler-produced band-word fixtures.
- Render dispatch:
  ROM evidence is `0x1ef6a`, `0x1ef86`, `0x1efc2`, `0x1f446`,
  `0x1f756`, `0x1f812`, and `0x1f88e`, plus destination helpers
  `0x1f3d4` and `0x1f626`.
  Checked-in documentation is the `Bitmap Object Dispatch Semantic Checkpoint`
  in [page-raster-imaging.md](page-raster-imaging.md) and
  `Bitmap Render Dispatch Contract` in
  [semantic-state-model.md](semantic-state-model.md), surfaced first as
  `Worked Path: Render Dispatch And Pixel Composition` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md).
  The shared render contract starts from active render pointer `0x783a18`.
  `0x1ef6a` calls `0x1ef86 -> 0x1efc2 -> 0x1f446 -> 0x1f756`: band-cache
  setup, bucket-chain dispatch from render `+0x18`, rule-list dispatch from
  render `+0x1c`, and fixed-list dispatch from render `+0x20`.
  Bucket object byte `+0x04` splits compact `0x00..0x3f` objects through
  `0x1effe` and compact helpers `0x1f034/0x1f0d2/0x1f1f0/0x1f264`,
  segment-list `0x40..0x7f` objects through `0x1f812`, and encoded raster
  `0x80..0xff` objects through `0x1f88e` modes `0..3`.
  Pixel writers compute destinations from packed coordinates, band state
  `0x783a20`, destination base `0x783a28`, stride `0x783a1c`, offset table
  `0x7839f8..`, fallback base `0x7810b4`, and phase byte `$a001`.
  Rule selectors dispatch through `0x1f446` to solid writer `0x1f596` or
  pattern writer `0x1f4e0`; fixed-list rows use `0x1f756/0x1f7b0`.
  Supporting evidence is
  `generated/analysis/ic30_ic13_render_dispatch_tables.md`, fixtures for
  `0x1ef6a` render entry and page-band composition, segment-list object
  rendering through `0x1f812`, fixed-list object rendering through `0x1f756`,
  solid and patterned rule rendering through `0x1f596` and `0x1f4e0`, and
  encoded raster modes through `0x1f88e`.
- Mixed page-image stream:
  ROM evidence crosses parser handlers `0xd04a`, `0x10e68`,
  `0x10e22`, `0x10898`, `0x10808`, `0x1075a`, `0x11f82`, and
  `0xf0f0`, then publication and render handlers `0xff1e`,
  `0x1ed84`, `0x1edc6`, and `0x1ef6a`.
  Reproduction evidence is `Mixed Text/Rule/Raster Page Record` in
  `notes/semantic-state-model.md`, surfaced first as
  `Worked Path: Mixed Text/Rule/Raster Page Record` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md), plus fixtures
  `host-fetched text rectangle raster FF publishes rendered page record`,
  `addressed text rectangle raster FF publishes rendered page record`,
  `addressed text/rule/raster field groups reach publication and render
  entry`,
  `host-fetched text rectangle multi-row raster FF publishes rendered page
  record`, and
  `addressed text/rule/multi-row raster publication preserves bucket
  chain`.
- Built-in glyph data:
  ROM evidence is the IC32/IC15 resource ROM tables and bitmap records.
  Checked-in documentation is [resource-rom.md](resource-rom.md),
  [built-in-resource-scan.md](built-in-resource-scan.md),
  [font-context-metrics.md](font-context-metrics.md), and
  [font-sample-page.md](font-sample-page.md), surfaced first as
  `Worked Path: Built-In Resource Scan And Candidate Windows`,
  `Worked Path: Font Selection To Visible Glyphs`,
  `Worked Path: Firmware Font Sample Page`, and
  `Worked Path: Compact Glyph Row-Copy Helpers` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md). Supporting evidence
  includes `generated/analysis/ic32_ic15_builtin_glyph_payloads.md` and compact
  glyph fixtures.
  IC32/IC15 file offset `N` maps to firmware resource address `0x80000 + N`.
  Header-like font records such as first `COURIER` record `0x080418`
  / context `0x44080418` and first `LINE_PRINTER` record `0x0946b4`
  / context `0x440946b4` carry bit-30 offset-table form. Font selection and
  sample-page paths install those contexts into current-font state
  `0x782ee6` / `0x782ef6`, rebuild maps `0x782f32` / `0x783032`, and refresh
  page-root slots through `0xc428` / `0xc4fc`.
  Printable bytes then flow through `0xd04a -> 0x1393a -> 0x12f2e` into
  compact page objects. Publication/rendering copies page-root context slots
  through `0x1ed84` / `0x1edc6`; compact dispatch
  `0x1ef6a -> 0x1efc2 -> 0x1effe -> 0x1f354` resolves the selected resource
  offset table. `0x1f354` consumes glyph-entry byte `+4` as bitmap delta,
  byte `+5` as small mode/plane, word `+6` as row count, and word `+8` as
  pixel width before the row-copy helpers emit pixels.
  Firmware-generated sample pages enter the same path after `0x1e0b2`,
  `0x1c204`, resolver `0x1b50e`, installer `0x1c5e8`, row formatter
  `0x1cabe`, and sample-run helper `0x1cf34`. Fixture
  `font sample full printout segments render through 0x1ed84 and 0x1ef6a`
  pins eight class/source segments, render-bucket counts
  `[1, 6, 6, 65, 1, 5, 5, 50]`, and aggregate rendered-surface digest
  `5e5e735b4fb2a2a4dff4794099a02eaf23fa2dd3e469df8d053db88a321ea6f2`.
- Font selection to visible glyphs:
  ROM evidence is parser terminal handler `0x120be`, symbol/default helper
  `0x1be22`, common refresh `0xc580`, candidate filter/selection path
  `0x13eb8 -> 0x156de`, font-ID helper `0x17708`, map rebuild `0x14c64`,
  printable source path `0xd04a -> 0x1393a -> 0x12f2e`, and render dispatch
  through `0x1ef6a -> 0x1efc2 -> 0x1effe -> 0x1f354`. Checked-in
  documentation is [font-context-metrics.md](font-context-metrics.md) and
  `Built-In Font Selection To Visible Text` in
  [semantic-state-model.md](semantic-state-model.md), surfaced first as
  `Worked Path: Font Selection To Visible Glyphs` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md). The covered
  primary and secondary streams update request fields, select contexts
  `0xc008004c` and `0xc00ae122`, rebuild maps `0x782f32` and `0x783032`,
  install page-root context slots through `0xc428` / `0xc4fc`, and make later
  printable bytes render from those selected contexts. Symbol-miss fallback,
  remembered-symbol recovery, non-Roman symbols, final-`@` defaults, final-`X`
  font-ID success, final-`X` no-selection exits, and bit-30-clear
  inline/downloaded context selection are all documented as visible-output
  variants.
- Downloaded font payloads:
  ROM evidence is `0x15d0a`, `0x168dc`, `0x16942`, `0x16c14`, and
  `0x1719c`, with font-control writers `0x15a56`, `0x15a18`, and
  `0x16df6`.
  Checked-in documentation is [downloaded-fonts.md](downloaded-fonts.md) and
  the downloaded-font checkpoints in
  [semantic-state-model.md](semantic-state-model.md), surfaced first as
  `Worked Path: Downloaded Glyph`, `Worked Path: Nonzero Resource Payload`,
  and `Worked Path: Fixed-Record Resource Object` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md). Supporting evidence
  is the font descriptor, resource, and character fixtures in
  `tools/render_fixture_harness.py`.
  Font-control commands write canonical selection state: current font id
  `0x782f2e`, current character `0x782f30`, parser cursor `0x78299e`, and
  current-record pool `0x782640..0x782776`. Nonzero `ESC )s#W` schedules
  delayed handler `0x16c14`, which loads byte budget `0x783140`, finds the
  current record, and installs downloaded character or resource payload state.
  Linear bitmap copies use `0x168dc`; split-plane copies use `0x16942`.
  Resource-header payloads validate through `0x16fae`, allocate through
  `0x17026`, initialize `0x1719c` payload headers, and install bit-30
  candidate longwords through `0x16c14` / `0x1bc38`.
  Printable bytes then use the installed payload through
  `0xd04a -> 0x1393a -> 0xd824/0xd3b2 -> 0x12f2e`. The documented
  segmented-wide stream installs glyph `%` with record bytes
  `00 00 00 00 0c 02 00 81 00 88 00 00`, queues selector `0x3003` in buckets
  `9` and `1`, publishes through `0xff1e`, copies through `0x1ed84` /
  `0x1edc6`, and renders through
  `0x1ef6a -> 0x1efc2 -> 0x1effe -> 0x1f1f0/0x1f264`.
  Covered variants also include short selector `0x0003` through `0x1fe76`,
  wide selector `0x1003` through `0x1f0d2`, segmented selector `0x2000` /
  `0x2003` through `0x1f1f0`, and segmented-wide selector `0x3003` through
  `0x1f264`, including mixed rule/raster composition before `0x1ef6a`.

## Reproducible Byte-Stream Families

- Plain printable text and text with direct controls are covered from host
  bytes through parser, compact bucket objects, bridge, and rendered rows.
  Evidence: fixtures `plain printable parser trace feeds page-record queue`,
  `host-fetched mixed control stream reaches parser and page-record render`,
  `host-fetched direct text/control streams feed 0x1ed84 and 0x1ef6a`,
  `ESC 9 clear margins feeds CR and page-record output`,
  `ESC = half-line feed reaches shifted page-record output`, and
  `ESC &d underline selector materializes span output`.
  The representative control path is `ESC &k1G ! CR !`: host bytes enter
  `0xa904 -> 0xda9a -> 0x11774`, command handler `0xedf8` writes
  line-termination byte `0x78318f = 0x80`, the first `!` reaches `0xd04a`,
  CR handler `0xf02c` resets horizontal cursor `0x782c8a` from left margin
  `0x782dd6`, flushes pending span state through `0xf34a`, and calls LF helper
  `0xf0b2` because bit 7 is set. The second `!` then queues at compact coord
  `0x3b00` through `0xd04a -> 0xd824 -> 0x12f2e -> 0x1387c`, publishes through
  `0xff1e`, crosses `0x1ed84` / `0x1edc6`, and renders through `0x1ef6a`.
  Direct-control variants share the same canonical placement fields:
  horizontal cursor `0x782c8a`, vertical cursor `0x782c8e`, margins
  `0x782dd6` / `0x782dda`, HMI `0x78315c`, VMI `0x783160`, wrap byte
  `0x783190`, and perforation-skip byte `0x783191`. `ESC 9` handler `0xe9ba`
  clears margins before later CR/text consumes them; `ESC =` handler `0xf176`
  advances by half VMI before later text; `ESC &d` handler `0x12622` writes
  underline selector `0x783185` and can flush selector-`0x4000` span objects
  through `0x12714`, which later render through segment-list path `0x1f812`.
- Layout-control streams are covered where command bytes alter later visible
  output without drawing immediately. Evidence:
  `Worked Path: Page Length, Wrap, And Perforation Controls` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md),
  [direct-control-codes.md](direct-control-codes.md), fixtures
  `0xf9e8 ESC &l#P stream reaches page-length handler`,
  `mixed page-length stream refreshes cursor before printable page-record
  queue`, `0xedb0 ESC &s#C toggles end-of-line wrap for selectors 0 and 1
  only`, `0xd28a and 0xd6bc prechecks share continue reject and wrap
  decisions`, `0xee64 ESC &l#L toggles perforation skip for selectors 0 and 1
  only`, `0xf36c perforation skip gates vertical overflow page eject`, and
  `perforation skip parser trace feeds page-record queue`. The reproduction
  effect is later placement, queue suppression/recovery, or page-eject
  behavior through the same page-record and render pipeline as ordinary text.
- Built-in font-selection streams are covered for primary and secondary
  visible output, symbol fallback, remembered-symbol recovery, non-Roman
  symbol sets, real final-`@` default-symbol table streams, final-`X` font-ID
  success, final-`X` preserved-output exits, bit-30-clear inline/downloaded
  context selection, and selected current-font RAM handoff through SI/SO.
  Evidence: [font-context-metrics.md](font-context-metrics.md),
  `Worked Path: Font Selection To Visible Glyphs` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md), and fixtures
  `inline primary font selection stream renders visible rows`,
  `inline secondary font selection stream renders SO visible rows`,
  `primary symbol miss falls back before visible page-record rows`,
  `remembered secondary symbol feeds visible SO page-record rows`,
  `non-Roman symbol streams select visible built-ins`,
  `real final-@ default-table streams select visible built-ins`,
  `font-ID built-in selection feeds visible page-record rows`,
  `font-ID secondary built-in selection feeds visible SO page-record rows`,
  `font-ID primary inline/downloaded selection feeds visible page-record rows`,
  and `font-ID non-selected exits keep prior visible rows`. The reproduction
  effect is context/map selection before ordinary printable bytes queue compact
  objects; font-selection commands have no separate renderer.
- Explicit no-output parser rows are covered for normal `NUL BEL VT` and for
  alternate/data blank C0 append-preserving rows. Evidence:
  `Worked Path: Explicit No-Output Parser Rows` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md),
  [pcl-parser-core.md](pcl-parser-core.md),
  [pcl-command-map.md](pcl-command-map.md), and generated parser table extract
  `generated/analysis/ic30_ic13_parser_dispatch_tables.md`. The reproduction
  effect is absence of page objects in normal mode while preserving pending
  delayed restore at `0x12218`; in alternate/data mode the bytes are stored
  through `0xe002` before parser reset.
- Transparent print data streams are covered for printable bytes,
  default-filtered C0/high-control bytes, nonzero-filtered C0/high-control
  bytes, `1a 58` and non-`0x58` probe handling, primary high-control samples
  `0x81`, `0x88`, `0x90`, `0x97`, `0x98`, and `0x9f`, and the secondary
  segmented page-record boundary. Evidence: fixtures
  `transparent data parser trace feeds page-record queue`,
  `transparent non-0x58 probe byte reaches page-record output`,
  `transparent data control payloads advance through fixed-space path`,
  `transparent default-filtered control enters unflagged fixed-record path`,
  `transparent nonzero filters route controls through printable path`,
  `transparent nonzero high-control byte queues tall glyph bucket`,
  `transparent nonzero high-control interior samples remain printable`,
  `transparent nonzero high-control upper bound remains printable`, and
  `transparent secondary high-control byte enters segmented page-record path`.
  The renderer-visible secondary prefix is covered through bucket `448`;
  bucket `456` is bounded as the physical resource-window continuation issue
  above.
- Display-functions streams are covered for normal page output and
  alternate/data append. Normal fixture `ESC Y display-functions stream
  reaches page-record output` drives `ESC Y!\x05! ESC Z` through handler
  `0x12536`, queues visible text including the terminating `Z`, and renders
  the resulting page records. Fixture `ESC Y display-functions filter-on routes
  controls as printable` sets nonzero context/high-control filters, normalizes
  `1a 58` to `7f`, routes `05 80 7f 21 1b 5a` through `0xd04a`, queues six
  compact entries, and renders digest
  `1cdd8203b43944801ec8d1d01c6ab4fa3808fc1f81a7ebfa4d04452369193b63`.
  Alternate/data fixture `0x12120 ESC Y alternate append stores normalized
  display bytes` proves append-only output `1b 59 21 7f 1b 5a` through
  `0xe002` without text imaging.
- Page-geometry streams are covered for page size, orientation, nonzero
  page length, and the `ESC &l0P` zero-length default-page branch. Evidence:
  fixture
  `0xf9e8 ESC &l#P converts VMI lines to page length and selects internal
  page code`, `0xf9e8 ESC &l#P stream reaches page-length handler`,
  `mixed printable/page-size page-record stream publishes queued text`,
  and `mixed printable/orientation page-record stream publishes queued text
  before landscape change`.
  Page-size handler `0xfc74` writes internal page code `0x782da2` and reloads
  table-backed geometry. Orientation handler `0x10220` writes orientation byte
  `0x782da3`, publishes any queued page first, then swaps active extents and
  margin bases. The ROM lookup helpers `0x9d16`, `0x9d4e`, `0x9d86`, and
  `0x9dbe` read tables `0x00a112`, `0x00a128`, `0x00a13e`, and `0x00a154`;
  they mask page code with `0x7f`, accept indexes `0..10`, and supply table
  outputs such as `0x782db2` and `0x782db4` before orientation refresh.
  Page-length handler `0xf9e8` writes page length/vertical extent `0x782dba`.
  Its zero-parameter branch compares pending page-environment byte `0x782da6`
  against active byte `0x780e8e`, can mirror output byte `0x780e8f`, signal
  control word `0x780e26`, and select default page code from `0x780e97` with
  fallback code `2`. These fields are consumed later by printable placement,
  VFC, perforation skip, raster origin, rectangle clipping, span orientation,
  publication, and render scheduling; the geometry commands have no separate
  pixel renderer.
- Raster graphics streams are covered for `ESC *t#R`, `ESC *r#A`, delayed
  `ESC *b#W`, lowercase transfer chaining, active-raster resolution behavior,
  row caps, beyond-extent drains, and modes 0/1/2/3. Evidence:
  [raster-graphics.md](raster-graphics.md),
  `Raster Transfer Gate And Encoded Rows` in
  [semantic-state-model.md](semantic-state-model.md), host-fetched raster
  fixtures, and supporting report
  `generated/analysis/ic30_ic13_raster_graphics_flow.md`.
  The primary stream
  `ESC *t300R ESC *r1A ESC *b4W f0 0f aa 55` reaches parser handlers
  `0x10808`, `0x1075a`, and `0x11f82`. `0x11f82` schedules delayed transfer
  handler `0x105d0` through `0x121cc`; `0x12218` restores record
  `80 57 00 04 00 00` and calls `0x105d0` when payload bytes are available.
  Canonical raster state is rooted at `0x783170`: mode `+0x08`, scale `+0x0e`,
  active flag `+0x12`, row coordinate `+0x02`, accepted count `+0x04`,
  overflow count `+0x06`, origin `+0x0a`, and maximum row byte count `+0x10`.
  Accepted rows pass through `0x10084`, `0x13070`, `0x13250`, and `0x138de` to
  queue encoded raster objects such as
  `00 00 00 00 80 00 00 04 00 01 f0 0f aa 55`: class byte `0x80`, mode byte
  `0`, capacity `4`, packed key `0x0001`, and payload bytes at `+0x0a`.
  Publication and rendering copy the bucket chain through `0xff1e`,
  `0x1ed84`, and `0x1edc6`; `0x1ef6a -> 0x1efc2 -> 0x1f88e` renders the object.
  Mode `0` copies literal words, while modes `1`, `2`, and `3` expand payload
  bytes into two, three, or four output rows through ROM expansion tables.
  The gate fixtures classify capped transfers, beyond-extent drains, negative
  rows, consecutive transfers, and active-resolution ignore as object or
  no-object outcomes before this same render path.
- Rectangle/rule streams are covered for size commands, fill selectors,
  clipping, no-room retry, bridge normalization, solid/pattern rendering,
  selector-7 text/rule page records, all non-solid selector IDs in text/rule
  page records, and the landscape pattern remaps. Evidence:
  `notes/rectangle-graphics.md` and parser trace fixtures for `ESC *c` rule
  streams.
  The primary chained stream `ESC *c12a5b0P` reaches handlers `0x10e68`,
  `0x10e22`, and `0x10898`: width field `0x78316a`, height field
  `0x783166`, and fill selector `7` for solid black. `0x10898` then calls
  clip/queue helper `0x10b80`, which consumes cursor `0x782c8a` /
  `0x782c8e`, extents `0x782db8` / `0x782db6`, orientation `0x782da3`, and
  current page root `0x78297a` to populate source record `0x782a88`.
  `0x13386` / `0x133aa` derive bucket/key fields `0x782a7c..0x782a7e`, allocate
  a 14-byte rule object through `0x1381c`, and insert it under page-root
  `+0x24`. The selector-7 object for the primary stream is
  `00 00 00 00 01 07 4a 00 00 0c 00 05 00 00`: bucket byte `+4`, fill
  selector `+5`, packed key `+6`, width `+8`, height `+0a`, and continuation
  `+0c`.
  Bridge `0x1edc6` copies page-root `+0x24` to render-record `+0x1c`, ORs
  selector byte `+5` with `0x10`, and copies height `+0x0a` into continuation
  `+0x0c`. `0x1ef6a` renders rule lists after bucket objects: `0x1f446`
  dispatches selector `7` to solid helper `0x1f596`, while gray selectors
  `0..6` and HP pattern selectors `8..13` dispatch to `0x1f4e0`.
  The selector matrix fixtures cover gray percent mapping, portrait pattern
  ids, and landscape remaps `1 -> 9`, `2 -> 8`, `3 -> 11`, and `4 -> 10`,
  including continuation across render bands.
- Reset, FF, page-size, orientation, paper-source, copies, and VFC publication
  paths are covered through `0xff1e` for current modeled page records. VFC
  coverage includes `ESC &l#W` delayed table payloads, lowercase
  same-family delayed-record preservation, channel-2 forward and before-top
  jumps, selector-zero top-of-form, selector-zero page eject, wrap hit,
  wrap no-hit, target-after-text publication, and non-publishing recovery
  paths. Evidence is tracked in `notes/vertical-forms-control.md` with
  branch boundaries `0x128ae..0x128f4`, `0x12966..0x129c4`,
  `0x129c6..0x12af8`, `0x12a22..0x12a78`, and `0x129ee..0x12b5a`.
  Related publication evidence is checked in under
  [publication-commands.md](publication-commands.md) and
  `Publication Commands To Rendered Page Records` in
  [semantic-state-model.md](semantic-state-model.md), with supporting reports
  `generated/analysis/ic30_ic13_esc_e_reset_flow.md` and
  `generated/analysis/ic30_ic13_page_root_finalization.md`.
  The shared publication path consumes current page root `0x78297a` through
  `0xff1e`, writes published pool pointer `0x780ea6`, sets publication flag
  `0x782996`, copies compact bucket root `+0x1c` and context slot `+0x2c`, and
  clears the current root before `0x1ed84` / `0x1edc6` bridge the published
  record into `0x1ef6a`.
  Covered parser-to-publication streams are `! ESC E` through reset handler
  `0xcc52`, `ESC &k2G ! FF` through `0xedf8` and `0xf0f0`, `! ESC &l1A`
  through page-size handler `0xfc74`, `! ESC &l1O` through orientation handler
  `0x10220`, `! ESC &l2H` through paper-source handler `0xef62`, and
  `! ESC &l2X FF` through copy-count handler `0xeef0` before FF publication.
  The command-side fields are copy count `0x782da4`, paper-source byte
  `0x782da6`, pending paper-source refresh `0x782998`, output bytes
  `0x780e8f` / `0x780e26`, orientation `0x782da3`, and geometry fields updated
  after page-size/orientation publication.
  VFC table load `ESC &l#W` uses `0x11f6e -> 0x121cc -> 0x12218 -> 0x12cfe`
  to consume delayed payload bytes into table `0x782dde..0x782edd`, derive
  VFC limit `0x782dc2`, copy text-bottom cache `0x782dd2`, and clear modified
  layout flag `0x782ee1`. VFC channel jumps through `0x1280a` consume that
  table, VMI `0x783160`, top offset `0x782dce`, current y `0x782c8e`, and
  line caches `0x782ede` / `0x782edf` / `0x782ee0`.
  Non-publishing VFC paths only reset x/y before the next `0xd04a` printable;
  publishing VFC paths call `0xf124 -> 0xff1e` so the pre-VFC printable renders
  from the old page and the following printable queues on a fresh page.
- Macro replay streams are covered for definition, execute/call replay,
  mixed-control replay, overlay publication, repeated overlay publication,
  overlay skip gates, and overlay payloads that cross cursor, margin,
  transparent-data, raster, multi-row raster, and span-flush command families.
  Evidence: [macro-data-chain.md](macro-data-chain.md),
  `Worked Path: Macro Execute Replay` and
  `Worked Path: Macro Overlay Replay Publication` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md), and fixtures
  `macro execute data-chain replay feeds page-record stream`,
  `host-fetched macro replay payloads feed 0x1ed84 and 0x1ef6a`,
  `macro execute page-record layer composes with rule and raster band`,
  `macro overlay finalization replays before page publication`,
  `macro overlay replays across repeated page publications`,
  `macro overlay skip gates preserve base page publication`, and the overlay
  mixed-control, cursor-position, chained-margin, transparent, raster,
  multi-row raster, and span-flush publication fixtures. The reproduction
  effect is that replayed macro bytes become normal parser input through
  `0xa904`/`0x11774`; macro replay has no separate renderer.
  Macro command state starts with current macro id `0x783164` from handler
  `0xe112` and a 32-entry macro record pool at `0x782a98`. Each record stores
  payload-chain head `+0x00`, raw byte count `+0x04`, id word `+0x08`, and
  temporary/permanent byte `+0x0a`; selected record pointer `0x782d7a` is
  written by lookup helper `0xe0a4`.
  `ESC &f#X` handler `0xdd08` dispatches selectors `0..10`: definition start
  and stop, execute, call, overlay enable/disable, delete, and permanence
  controls. Definition appends payload through `0xe002` into linked `0x100`
  byte chunks. Execute/call selectors build data-chain frames through `0xe418`
  at active pointer `0x782d76`, with frame `+0x00/+0x04` copied from the macro
  record, byte `+0x08 = 4`, frame kind `+0x09 = 2` for execute or `3` for call,
  and snapshot pointer `+0x0a`.
  `0xa904` gives those frame bytes priority over live host bytes, so replayed
  payloads re-enter parser loop `0x11774` and route through the ordinary
  handlers such as `0xd04a`, `0xf02c`, `0xedf8`, cursor/margin handlers,
  transparent handler `0x12452`, raster transfer `0x105d0`, and span flush
  `0x12714`. Page objects, publication, bridge, and render dispatch are then
  the normal `0x1387c` / `0x1381c`, `0xff1e`, `0x1ed84` / `0x1edc6`, and
  `0x1ef6a` path.
  Overlay state uses `0x782a92` and saved overlay id `0x782a94`. During
  publication, `0xff1e` consumes that state and page-root retry bit `+0x14.0`;
  when the enabled overlay record exists, `0xe4f4` builds a non-replay frame
  with kind `+0x09 = 4`, replays the stored payload before the same publication
  boundary, and `0xe22c` restores parser/page state afterward. Disabled,
  missing-record, or retry-flag skip gates preserve the base page publication.
- The initial mixed page-image suite is covered for one complete
  host-fetched byte stream:
  `! ESC *c12a5b0P ESC *t300R ESC *r0A ESC *b2W c3 3c FF`.
  It drains through the modeled `0xa904` ring source, routes through the
  parser handlers above, queues compact text, a selector-7 rectangle
  rule, and a mode-0 raster object into addressed page-record storage,
  publishes through `0xff1e`, crosses the `0x1ed84` / `0x1edc6`
  render bridge, and compares the final composed rows. Evidence:
  `Mixed Text/Rule/Raster Page Record` in `notes/semantic-state-model.md`.
- The modeled per-band renderer now covers a crossing patterned rule
  together with compact text and a mode-0 raster row. Fixture
  `0x1ef6a page-band walk merges text raster and crossing rule`
  dispatches bucket-array compact/raster objects, carries the mutated
  rule node from band `0`, renders the remaining rule rows in band `5`,
  and leaves no rule/fixed-list residue. This closes the modeled
  per-band merge for that heterogeneous case; remaining render risk is
  live engine pacing and physical output comparison.
- A downloaded-glyph page-image stream is covered for
  `ESC *c4660d37e5F`, `ESC )s2193W <0x0891 payload bytes>`, printable
  `%`, and FF publication. The fixture drains the same modeled `0xa904`
  source, preserves the control/payload/printable/publication byte
  boundaries, installs glyph `0x25`, publishes segmented buckets `1` and
  `9` through `0xff1e`, walks those published bucket words through
  `0x1ed84`/`0x1ef6a` band rendering, proves `0x1eba4` scheduler progression
  through band words `0..9`, and compares the published rendered rows with
  bucket `9` producing the visible downloaded row. Evidence: fixtures
  `combined font download FF publishes installed glyph page record`,
  `published downloaded glyph segmented buckets render across bands`, and
  `0x1eba4 scheduler band words render published downloaded glyph`, plus
  `Downloaded Font Descriptor And Payload Chain` in
  `notes/semantic-state-model.md`.
- Downloaded-glyph/rule/raster render composition is covered for the
  host-fetched `ESC )s18W` even-span wide glyph install and a parser-driven
  page stream `ESC *c12a3b0P ) ESC *t300R ESC *r0A ESC *b2W c3 3c`. Evidence:
  fixture `parser-driven downloaded glyph rule raster stream composes through
  0x1ef6a`, which asserts the font/page fetch boundaries, page handlers
  `0x10e68`, `0x10e22`, `0x10898`, `0xd04a`, `0x10808`, `0x1075a`, and
  `0x11f82`, the `0x12f2e` glyph object, bridged selector-7 rule object,
  `0x13070` raster object, `0x1ed84`/`0x1ef6a` call order, dispatch targets
  `0x1f88e` and `0x1effe`, rule helper `0x1f596`, and final composed rows.
  Fixture `segmented downloaded glyph composes with raster through 0x1ef6a`
  extends the composition evidence to the `ESC )s258W` selector-`0x2003`
  segmented glyph family: bucket `9` contains the segment-1 object plus a
  mode-0 raster object, dispatches through `0x1f88e` and `0x1f1f0`, and
  renders digest
  `0b5440d6733ab9a072e0c14d1a470e6bc944dc98ddbf789152cf65c945dd0f01`.
  Fixture `split-plane segmented downloaded glyph composes with raster through
  0x1ef6a` covers the split-plane `ESC )s387W` sibling with glyph `0x28`,
  buckets `9` and `1`, the same bucket-9 raster object, dispatch targets
  `0x1f88e` and `0x1f1f0`, and digest
  `a380045041433910619b809637eda41e81842a3516acb83b488d07f1d3c68872`.
  Fixture `segmented downloaded glyph raster FF publications render page
  records` then publishes both segmented+raster records through `0xff1e`,
  preserves bucket `9` raster plus segment-1 objects and bucket `1`
  segment-0 objects, and renders the published records with the same two
  digests.
- Built-in and downloaded text rendering is covered for selected offset-table,
  inline/downloaded fixed records, segmented records, segmented-wide records,
  font descriptors, resource payloads, downloaded character payloads, and
  host-fetched font-control state. Evidence:
  [font-context-metrics.md](font-context-metrics.md),
  [resource-rom.md](resource-rom.md),
  [downloaded-fonts.md](downloaded-fonts.md), font fixtures, and supporting
  reports `generated/analysis/ic30_ic13_text_glyph_index_flow.md`,
  `generated/analysis/ic30_ic13_font_control_flow.md`, and
  `generated/analysis/ic32_ic15_builtin_glyph_payloads.md`.

## Canonical State Groups

- Host/input canonical state: `0x780e40`, `0x780e66`, `0x780e3b`,
  `0x783e54`, `0x783e56`, `0x783e76`, `0x783e78`, `0x783e8c`,
  `0x783e8e`, and `0x782d76` frame fields `+0x00`, `+0x04`, `+0x08`,
  `+0x09`, and `+0x0a`. Evidence:
  [host-byte-fetch.md](host-byte-fetch.md),
  `Host Byte Fetch And Data-Chain Input` in
  [semantic-state-model.md](semantic-state-model.md), and supporting report
  `generated/analysis/ic30_ic13_host_byte_fetch_flow.md`.
- Parser scratch: six-byte command records at `0x78299e..0x7829a7`,
  delayed handler snapshots, payload counters, and alternate/data mode state.
  Evidence: `Parser Record And Delayed Payload State` in
  [semantic-state-model.md](semantic-state-model.md), tokenizer fixtures, and
  `generated/analysis/ic30_ic13_parser_xrefs.md`. The parser-record checkpoint
  classifies canonical state (`0x782999`, `0x78299e`, `0x782c18`), tokenizer
  scratch (`0x782a26`, `0x782a2a..`, `0x782a3e`, `0x782a42..`,
  `0x783196..0x783199`), firmware bookkeeping (`0x78299a`, `0x782a1a`,
  `0x782a1c`, `0x782a20..0x782a25`, `0x782a56`), and derived font-designation
  records from `0x11efe` / `0x11f26`.
- Canonical print environment: cursor words `0x782c8a` and `0x782c8e`,
  HMI/VMI words, margins, page geometry fields under `0x782da2..0x782dc0`,
  line-termination mode, cursor stack, and font slot state. Evidence:
  [direct-control-codes.md](direct-control-codes.md),
  `Text Cursor And Direct Controls`, and page-geometry fixtures, including
  the `ESC *p#X/#Y` dot-position path through handlers `0xf48c` and
  `0xf692`. Those handlers convert parsed integer dot units to packed
  whole-dot cursor coordinates with `parameter << 16`, then share the
  `0xf4ca` / `0xf6e2` commit helpers before printable output is queued.
- Canonical page model: current page root `0x78297a`, page-root class byte
  `+4`, bucket array `+0x1c`, rule list `+0x24`, fixed-width list `+0x28`,
  context slots `+0x2c`, and stream allocator fields `0x782a70`,
  `0x782a72`, `0x782a76`. Evidence:
  [page-record-storage.md](page-record-storage.md) and
  `Shared Page-Record Storage And Allocator`.
- Derived/cache state: bucket/key bytes `0x782a7a..0x782a7e`, render-band
  fields `0x783a20`, `0x783a22`, `0x783a28`, pending span watermarks
  `0x783184..0x78318a`, raster mode/scale caches, delayed raster row
  coordinates, and mode-selected encoded raster object bytes. Evidence:
  `Text Span Flush And Fixed-Width Spans`,
  [page-raster-imaging.md](page-raster-imaging.md),
  `Bitmap Render Dispatch Contract` in
  [semantic-state-model.md](semantic-state-model.md), raster fixtures, and
  supporting report `generated/analysis/ic30_ic13_page_record_bridge.md`.
- Firmware bookkeeping: publication flag `0x782996`, page/root transient
  bytes `0x78297e`, `0x782c72`, `0x782c73`, retry flag bit in page-root
  `+0x14`, macro/data-chain frames, and heap/resource allocation metadata.
  Evidence: page-finalization, macro, allocator, and font-resource notes.

## Pixel-Perfect Coverage And Residual Risks

These are the highest-value coverage areas and residual risks because each can
change rendered pixels, byte-stream compatibility, or final confidence. Most
entries below are composed ROM contracts with bounded remaining variants rather
than open middle edges.

1. Font/context span metric producer ownership is documented, and the
   parser-produced legal value space is now represented by ROM formulas plus
   fixture-backed partitions rather than isolated per-value tracing. The
   consumers are known: unflagged `0xd4ac` reads context `+0x2b`, `+0x2c`,
   `+0x2d`; flagged `0xd8fc` reads `+0x16`, `+0x18`, `+0x1a`. The selected-context
   bridge and current metric evidence boundary are documented in
   `notes/font-context-metrics.md`, and the downloaded descriptor/payload producer side
   is documented in
   `notes/downloaded-fonts.md`. Host-fetched `0x1719c` type-0, type-1, and type-2
   payloads now prove copied descriptor bytes feeding both `0xd4ac` and `0xd8fc`
   visible span rows. Fixture `d4ac and d8fc span consumer branch family controls flush
   output`
   covers disabled, lower-bound, page-extent, and high-x consumer outcomes for both
   source forms. Fixture `host-fetched metric variant changes d4ac gate and d8fc rows`
   proves one parser-produced metric-value variant: copied `+0x2c/+0x2d` flips a tight
   `0xd4ac` page-extent gate, and copied `+0x1a` moves `0xd8fc` visible rows. Fixture
   `host-fetched clamped metric variant changes d4ac gate and d8fc rows` proves a second
   parser-produced variant: range/count `+0x14 = 5` clamps an oversized rounded metric
   input into `+0x2c/+0x2d = 0x0014`, leaves `+0x2b = 0`, flips another tight `0xd4ac`
   gate, and moves `0xd8fc` rows through copied `+0x18 = 0` and `+0x1a = 3`. Fixture
   `host-fetched lower-bound metric variant suppresses d4ac and d8fc spans` proves a
   third parser-produced variant: first code `+0x16 = 0x0018`, range/count `+0x14 =
   0x0600`, derived count `+0x18 = 0x05e7`, and rounded word `+0x2c = 0x1800` make both
   consumers exit `before-context-lower` at cursor y `21` while the compact glyph
   objects remain queued and render. Fixture `host-fetched upper-bound metric variant
   keeps d4ac span but suppresses d8fc` proves a fourth parser-produced variant:
   range/count `+0x14 = 0x0040` derives/cache `+0x18 = 0x003b`, leaves unflagged
   `+0x2c/+0x2d = 0/0x20`, keeps `0xd4ac` span output, and makes `0xd8fc` exit
   `beyond-page-extent` at cursor y `21`. Seven bounded validation no-install forms plus
   the short-budget `ESC )s8W` entry-5 failure now prove parser-to-validation failure,
   allocation skip, no candidate install, resumed default-font printable output, and
   matching rows. Fixture `descriptor metric fields match across inline and resource
   contexts` now proves inline/unflagged `d4ac`, resource/flagged `d8fc`, and the two
   invalid swapped forms. Fixture `legal descriptor metric value matrix drives d4ac and
   d8fc consumers` composes the legal small-rounded, clamped-rounded, midpoint-rounded,
   zero-rounded-offset, negative-offset, lower-bound, and upper-bound values; the zero
   case copies `+0x14/+0x18/+0x1a/+0x2c = 0x0018/0x0013/0x0000/0x0000`, preserves the
   `d4ac` span digest
   `67554ea70d7cfd9b11c0777e3cf65d51600a44301a4f93bd4d9b0c0fbc23c00e`, and makes `d8fc`
   publish high-y `21` / row digest
   `47361fc76bd6284f9d764c0377a3fda64edd3944b5cb2dff72acfd2224bc25e8`. The midpoint case
   copies `+0x14/+0x18/+0x1a/+0x2c = 0x0018/0x0013/0x0007/0x0018` and makes `d8fc`
   update high-y `14` while leaving compact-only digest
   `1a73b5e7454202d800c69f626bcf34e7d0d583b459e04c0bd4250010bf3ba28a`. The
   negative-offset case copies `+0x14/+0x18/+0x1a/+0x2c = 0x0018/0x0013/0xfffe/0x0008`;
   `d8fc` consumes the copied offset word as `65534`, computes high-y `-65513`, and
   renders digest `72bfa14c2a84532e2bdf6fb8fddf26ed6904c49dcf4fdcb322592471b5d5b281`.
   Fixture `legal descriptor metric boundary values drive d4ac and d8fc consumers` adds
   max positive and max negative copied offset words `0x007f` and `0xffff`, lower-bound
   equality, exact page-extent equality, rounded input `0x0013` copying `+0x2c =
   0x0014`, and high-byte rounded inputs `0x1500`, `0x1508`, and `0x15ff` all copying
   `+0x2c = 0x0060` before `d4ac` exits `beyond-page-extent`. Fixture `legal descriptor
   metric low-nibble rounding drives d4ac and d8fc consumers` proves rounded inputs
   `0x0001`, `0x0003`, `0x0004`, `0x0005`, and `0x000f` copy to `+0x2c =
   0x0000/0x0004/0x0004/0x0004/0x0010`, keep the standard `d4ac` span digest, and keep
   `d8fc` high-y `20` / digest
   `f830d30ea60a61f0b74a489c4b7df1bb25dc464b6765d170c19e7278a0267eab`. Fixture `legal
   descriptor metric byte-boundary rounding drives d4ac and d8fc consumers` proves
   rounded inputs `0x00fd`, `0x00fe`, `0x0101`, and `0x0102` copy to `+0x2c =
   0x00fc/0x0100/0x0100/0x0104`, with a range-cap sibling forcing `0x0102` back to
   `0x0100` when `+0x14 = 0x0040`. The copied `0x00fc` case leaves `d4ac` on
   compact-only digest
   `86e3bb70d51c66ac608345dc3bff6476447ebc500d7c271808a53d6638d59ad6`, while the
   `0x0100` boundary copy restores the standard `d4ac` span digest
   `67554ea70d7cfd9b11c0777e3cf65d51600a44301a4f93bd4d9b0c0fbc23c00e`; the same
   large-range cases keep `d8fc` at `beyond-page-extent`. Fixture `legal descriptor
   metric mixed values drive d4ac and d8fc consumers` now covers multi-field legal
   descriptors where the first code, range/count, rounded word, and signed offset all
   vary together. The middle-range `0x0008/0x0030/0x002a/0x02` case copies
   `+0x18/+0x1a/+0x2c = 0x0027/0x0002/0x002c`, suppresses `d4ac` as
   `beyond-page-extent`, and renders `d8fc` digest
   `00c97b69bc50326e442dd060c88b710b8f00217d40809bed276d8ba48581fdc7`. Its
   rounded-`0x00ff` sibling caps copied `+0x2c` to `0x00c0`; its offset byte `0x80`
   sibling sign-extends to `+0x1a = 0xff80` and computes `d8fc` high-y `-65387`; its
   late-first-code sibling derives `+0x18 = 0`, keeps `d4ac` visible, and makes `d8fc`
   exit `before-context-lower`. Fixture `legal descriptor metric tight range values
   drive d4ac and d8fc consumers` covers range-one zero/clamped rounded outputs and
   range-two max positive/negative offset words at derived height zero. The producer
   formula is documented from disassembly: `0x17430` derives `+0x18 = +0x14 - +0x16 -
   1`, `0x1757a` writes `+0x2c = min((value + 2) >> 2, word(+0x14)) << 2`, `0x1762a`
   writes signed offset word `+0x1a`, and `0x1719c` copies those staged fields into the
   allocated payload. The remaining metric work is no longer an unresolved middle edge
   for the copied-field formulas: `notes/font-context-metrics.md` classifies additional
   legal metric values as cross-products, and `notes/downloaded-fonts.md` names the
   consumed-but-not-staged validation entries by ROM effect. The remaining validation
   work is external HP/manual field naming, not hidden firmware state. Future metric
   work should therefore be regression expansion or selected-font
   cross-products only when they expose a new state boundary. It is not the tested
   type-0/type-1/type-2 payloads, metric-variant, clamped-variant, lower-bound-variant,
   upper-bound-variant, legal-value-matrix, low-nibble rounding submatrix,
   byte-boundary rounding submatrix, extent-fence matrix, validation no-install, legal
   producer-form boundary, mixed-value matrix, tight-range matrix, or shared consumer
   branch family. Evidence: `notes/semantic-state-model.md` under `Text Span Flush And
   Fixed-Width Spans`.
2. VFC table definition and channel jumps now have a tracked command-family
   contract in `notes/vertical-forms-control.md`. That contract groups
   canonical VFC state `0x782dde..0x782edd`, canonical layout inputs
   `0x783160`, `0x782dce`, `0x782c8e`, `0x782c8a`, and margins
   `0x782dd6`/`0x782dda`; derived line caches `0x782dd2`, `0x782dc2`,
   `0x782ede`, `0x782edf`, and `0x782ee0`; parser scratch `0x78299e`;
   and firmware bookkeeping `0x782ee1`, `0x782a58`, `0x782a6d`,
   `0x783184`, and `0x78297a`. The documented output effects cover delayed
   payload consumption before printable text, cursor-only channel jumps,
   top-of-form no-op, selector-zero publication, wrap-hit publication,
   wrap-no-hit publication, target-after-text publication, and
   non-publishing recovery. The remaining VFC risk is broader final-device
   image comparison and HP/manual names for the derived line-count fields,
   not an unresolved middle edge in the documented `ESC &l#W` / `ESC &l#V`
   path.
   The adjacent perforation-skip command is also no longer only a parser-state
   toggle: `ESC &l#L` writes `0x783191` through handler `0xee64`, and fixture
   `0xf36c perforation skip gates vertical overflow page eject` proves the
   visible consumer at `0xf36c`. Page ejection through `0xf124` occurs only
   when `0x782c8e > 0x782dc2`, `0x782dc2` is nonzero, and `0x783191` is
   nonzero; below-limit, zero-limit, and disabled-skip cases return `D7 = 1`
   without publication.
3. Macro replay, overlay publication, repeated enabled-overlay publication,
   mixed-control, vertical-decipoint, chained cursor-position, chained margin,
   transparent-data, raster, multi-row raster, and span-flush overlay payloads,
   and overlay skip gates are anchored. The covered overlay path is selector
   `4` state through `0xff1e` re-entry, `0xe0a4`, `0xe4f4`, parser loop `0x11774`, and
   rendered page-record composition with selector-7 rectangle rules on two page
   boundaries. The mixed-control overlay fixture stores `ESC &k1G!\r!`, replays it
   through `0xedf8`/`0xd04a`/`0xf02c`/`0xd04a`, queues two compact text entries, and
   publishes them with a selector-7 rule. The cursor-position overlay fixture stores
   `ESC &a2C!`, replays `0xf39e` then `0xd04a`, queues compact text at coord `0x0a02`,
   preserves selector-7 rule object `00 00 00 00 01 07 82 02 00 07 00 02 00 00`, and
   renders digest `ba32af7d183a956b2abd821b2143e9c7c3eecf87a7b1403fa086cfe6bf89c8ae`.
   The vertical-decipoint overlay fixture stores `ESC &a72V!`, replays `0xf60a` then
   `0xd04a`, moves packed vertical cursor `20 -> 30`, queues compact text at coord
   `0x9001`, preserves selector-7 rule object
   `00 00 00 00 01 07 88 01 00 07 00 02 00 00`, and renders digest
   `7ef1cc5d5557fa5a30c57e8ad6918b09747c210daed2639e9d75ccfed727e964`.
   The chained cursor-position overlay fixture stores `ESC &a2c+1R!`, replays `0xf39e`,
   `0xf560`, and `0xd04a`, queues compact text at coord `0x3a02`, preserves selector-7
   rule object `00 00 00 00 01 07 a6 02 00 06 00 02 00 00`, and renders digest
   `0275857ffbcc11aa5234644930ebcd31571c2178eaf52b79590989d31b39f653`. The
   chained margin overlay fixture stores `ESC &a6l9M!`, replays `0xeb58`, `0xec0c`,
   and `0xd04a`, writes packed left/right margins `108`/`180`, queues compact text at
   coord `0x0207`, preserves selector-7 rule object
   `00 00 00 00 01 07 6c 02 00 05 00 02 00 00`, and renders digest
   `ecae0043ee656ceba42d4d6e052e3d56a365eeb4a847b3b430f80eed72b5a199`. The
   transparent-data overlay fixture stores `ESC &p2X!!`, replays command handler
   `0x11f5a`, restores delayed handler `0x12452`, routes payload `21 21` through
   `0xd04a`, queues compact text object `00 00 00 00 00 00 00 02 20 00 01 20 02 02 ...`,
   preserves the selector-7 rule, and renders digest
   `1ee999b850b4a35aa2b01b72ae01da961ee4084f0369f4ded5c8e8152464dac8`. The raster
   overlay fixture stores `! ESC *t300R ESC *r0A ESC *b2W c3 3c`, replays it through the
   non-replay frame, queues compact text plus a mode-0 raster object, preserves the
   existing selector-7 rule, and renders digest
   `bc21050018fd3e992709c704fff732499aa9d06565de31d7ae0340869971c5b3`. The multi-row
   raster overlay fixture stores `! ESC *t300R ESC *r0A ESC *b2W f0 0f ESC *b2W 0f f0`,
   replays two delayed `0x105d0` transfers, queues compact text plus two mode-0 raster
   objects, advances raster `row_y` to `2`, and renders digest
   `58c2293bbc6b187db0e964571e5812ab2192d32d8e648a38d61e407a58538638`. The span-flush
   overlay fixture stores `ESC &a6L!`, replays it through `0xeb58`/`0xd04a`,
   materializes selector-`0x4000` span object `00 00 00 00 40 00 00 01 32 00 03 00 00 10
   ...`, preserves the existing selector-7 rule, and renders digest
   `6775414374ba3c31f7846a180d93cc9b68e230ea6981ae722b32eb39081f9bca`. The skip path is
   covered for disabled overlay mode, missing selected record, and page-root retry flag.
   Remaining macro risk is broader overlay payload variants beyond `!\r`, `ESC
   &k1G!\r!`, `ESC &a2C!`, `ESC &a72V!`, `ESC &a2c+1R!`, `ESC &a6l9M!`,
   `ESC &p2X!!`, the covered raster payloads, and `ESC &a6L!`, plus physical output
   comparison. Evidence:
   [macro-data-chain.md](macro-data-chain.md), `Macro Definition And Data-Chain
   Replay` in `notes/semantic-state-model.md`,
   fixture `macro overlay finalization replays before page publication`, fixture
   `macro overlay replays across repeated page publications`, fixture `macro overlay
   skip gates preserve base page publication`, fixture `macro overlay mixed-control
   payload publishes with page rule`, fixture `macro overlay cursor-position payload
   publishes with page rule`, fixture `macro overlay vertical-decipoint payload
   publishes with page rule`, fixture `macro overlay chained cursor-position payload
   publishes with page rule`, fixture `macro overlay chained margin payload publishes
   with page rule`, fixture `macro overlay transparent payload publishes with page
   rule`, fixture `macro overlay raster payload publishes with page rule`, fixture
   `macro overlay multi-row raster payload publishes with page rule`, and fixture
   `macro overlay span-flush payload publishes with page rule`.
4. Active-record selection and render-band scheduling are documented as a
   ROM-internal reproduction boundary, rather than a page-object gap. Fixture
   `0x1eb2a/0x1ecd6 selects published record for render entry` proves
   `0x780eaa -> 0x780eae`, work-record alternation through `0x7820bc`, active render
   pointer `0x783a18`, and `0x1ed84`/`0x1ef6a` output for a published page/control
   record. Fixture `0x1958/0x1c04/0x1eea staged candidate reaches render scheduler`
   proves candidate staging, `0x1fd4` slot insertion, state-4 release, candidate
   promotion through `0x7ec6..0x7f90`, and the same rendered rows. Fixture
   `0x1eba4/0x1ef6a active render loop advances or yields bands` covers cleanup,
   throttle, capacity-wait, and render-call branches, while fixture `0x1eba4 scheduler
   band words render published downloaded glyph` proves scheduler-produced band words
   `0..9` against a published downloaded-glyph record. The remaining scheduler risk is
   not a ROM object/rendering middle edge: it is board-level timing for `$8000.4`
   selection at `0x0f84..0x0fa0` and `0x1020..0x102e`, MMIO effects around `$a601 =
   0xfd`, `$a801`, `$aa01`, `0xfffe0001`, and `0xfffe0003`, and the physical event
   timing that drives modeled wait-object/trap states through `0x10bc..0x11f8` and
   `0x123a..0x1282`. Evidence: `Published Record To Active Render Scheduler` in
   `notes/semantic-state-model.md` and `Active Render Scheduler` in
   `notes/page-raster-imaging.md`.
5. Downloaded font support now has tracked documentation for descriptor,
   resource-payload, current-record, bit-30-clear resource-object, bit-30-clear
   resource-object no-install exits, even-span and split-plane continuation resume,
   status-0 fixed-record release, bit-30 offset-table release delegate, release reject
   no-rewrite exits, split-plane character-object, linear character-object, and
   downloaded-glyph render paths in `notes/downloaded-fonts.md`. The `0x16c14`
   existing-record allocation-failure teardown through `0x1887a` is fixture-backed for
   the bit-30-clear extended fixed-record case, and the direct `0x1887a` release variant
   matrix now covers bit-30-set class-one, bit-30-set class-zero, and bit-30-clear
   class-zero cleanup branches. The `0x16fae` validation table now has ROM-effect names
   for all 32 entries plus concrete success and failure fixtures, and host-fetched
   invalid-resource-type, first-code overflow, zero line/count, high line/count,
   reversed-range, high range/count, and invalid-class paths prove parser-to-validation
   no-install boundaries plus following-printable default output. The nonzero `ESC )s#W`
   resource-payload path is composed in `notes/semantic-state-model.md` under `Nonzero
   Resource Payload Checkpoint`: the documented state now spans ROM parser restore,
   `0x16fae` validation, `0x17026`/`0x1719c` allocation, `0x16c14`/`0x1bc38` candidate
   insertion, `0x14c64` consumption, integrated `ESC )s3W` downloaded-pointer glyph
   install, and page-visible `d4ac`/`d8fc` metric consumers. Fixture `host-fetched
   resource header plus glyph payload renders offset-table downloaded glyph` closes the
   basic type-0 `ESC )s80W` plus linear three-row glyph boundary without fixture-side
   mutation. Fixture `type-1 and type-2 resource headers accept downloaded glyph payload
   stream` closes the same fetched-glyph boundary for legal type-1 and type-2 headers.
   Fixture `type-1 and type-2 resource glyph FF publications render page records` now
   adds the legal type-1/type-2 publication sibling: `ESC )s3W` plus printable `!` and
   FF publishes bucket `1`, preserves candidate contexts `0x40000000` and `0x44000000`,
   dispatches the span through `0x1f812` and the glyph through `0x1effe`, and renders
   the same rows. Fixture `type-1 and type-2 resource wide glyph FF publications render
   page records` adds the legal wide sibling: `ESC )s18W` plus printable `!` and FF
   publishes bucket `1`, preserves the same candidate contexts, dispatches the span
   through `0x1f812`, dispatches compact-wide object byte `0x10` through `0x1effe` to
   `0x1f0d2`, and renders digest
   `3985c4c7f33d361e0673e7361ce58aa1b9ba12bd003a2b9166eaddb93888e11e`. Fixture `type-1
   and type-2 resource segmented glyph FF publications render page records` adds the
   legal segmented sibling: `ESC )s258W` plus printable `!` and FF publishes bucket `9`,
   preserves bucket `1` as span plus segment `0`, dispatches compact object byte `0x20`
   through `0x1effe` to `0x1f1f0`, and renders digest
   `f449349d69d7acaff44a3f753253e4ef626057d41a5c8f6d827ce871bfc089b4`. Remaining work
   for this cluster is now broader glyph row/span/continuation shapes beyond the covered
   short, wide, and segmented glyphs and publication variants outside those legal
   type-1/type-2 span+glyph page-record shapes. Downloaded-character coverage now
   includes parser-produced normal, wide/control, even-span wide, segmented, split-plane
   segmented, and segmented-wide compact render shapes, and the combined
   downloaded-glyph stream now reaches FF publication with both segmented buckets
   preserved and scheduler-produced band words `0..9` rendered. The combined
   segmented-wide publication fixture now also pins the full-success return boundary:
   `combined font download FF publishes installed glyph page record` leaves `0x783140 =
   0`, drains zero bytes through `0x12328`, and resumes at handler `0xd04a` for
   printable `%` before FF publication. The payload-control wide sibling now has its
   nonzero return drain pinned: fixture `host-fetched payload-control downloaded glyph
   FF publishes page record` carries normalized `1a 58`, selector `0x1003`, bucket `1`,
   `0xff1e`, `0x1ed84`, and `0x1ef6a` to the same `0x1f0d2` modeled row, while the
   same-stream return leaves `0x783140 = 1`, drains the following `&` through `0x12328`,
   and leaves FF for handler `0xf0f0`. The rows-`0x82` segmented sibling now publishes
   through FF as well: fixture `host-fetched rows-0x82 segmented downloaded glyph FF
   publication renders page record` carries `ESC )s260W`, selector `0x2003`, buckets `1`
   and `9`, `0xff1e`, `0x1ed84`, and `0x1ef6a` to two `0x1f1f0` segment-1 rows. The
   rows-`0x20` short sibling now publishes through FF too: fixture `host-fetched
   rows-0x20 short downloaded glyph FF publication renders page record` carries `ESC
   )s64W`, selector `0x0003`, bucket `1`, `0xff1e`, `0x1ed84`, and `0x1ef6a` to `38`
   visible `0x1fe76` rows. The rows-`0x40` short sibling now publishes through FF as
   well: fixture `host-fetched rows-0x40 short downloaded glyph FF publication renders
   page record` carries `ESC )s128W`, selector `0x0003`, bucket `1`, `0xff1e`,
   `0x1ed84`, and `0x1ef6a` to `64` blank current-band `0x1fe76` rows. The accepted
   descriptor-record mode-byte boundary for this helper table is now documented by
   fixture `0x16b1a descriptor width helper emits only mode 1/2`: `0x16b36..0x16b6a`
   writes only mode `1`/`2` from span parity, and `0x16b26..0x16b34` rejects invalid
   widths without scratch writes. Fixture `0x15d0a descriptor grammar exits and handler
   matrix` covers the zero-count descriptor route's early drains and all four
   current-record/continuation by bit-30 handler polarities. The bit-30-clear
   fixed-record current-record and linear/split-plane continuation full-success
   boundaries now pin `0x15e42 -> 0x16606 -> 0x15dcc -> 0x12328` and `0x15e64 -> 0x15c4c
   -> 0x15dcc -> 0x12328` with zero drains before handler `0xd04a`. The field grouping,
   writers, consumers, output effect, and exact unresolved variant boundaries for those
   resource-object fixtures are composed in `notes/semantic-state-model.md` under
   `Fixed-Record Resource Object Checkpoint`. Other release variants and full-success
   return-boundary siblings are now classified as regression cross-products unless they
   expose a different `0x783140` remainder, `0x12328` drain status, next handler, or
   page-record selector from the even-span rule/raster path, row-count matrix,
   wide-remainder matrix, segmented-wide matrix, high-row segmented-wide matrix,
   segmented, split-plane segmented, segmented-wide publication, payload-control
   publication, and bit-30-clear fixed-record fixtures. The wrapped source-width-byte
   branch is now fully classified for `0x00..0x10` and `0x11..0xff`; remaining work
   there is physical/device behavior after the documented invalid compact-mode-0 helper
   targets, not parser-state discovery. Fixture `0x15c4c partial resource resumes update
   continuation state` covers the fixed-record continuation route's status-`2` resave
   behavior for linear and split-plane bit-30-clear resource objects. ROM-internal
   descriptor-validation error visibility is documented at the rejecting predicate
   boundary instead: fixture `ESC )s#W validation failures preserve following printable
   output` carries the seven `ESC )s80W` predicate failures plus the short-budget `ESC
   )s8W` entry-`5` failure through the following default-font page path. The remaining
   descriptor-validation gap is external HP/manual naming for consumed-but-not-staged
   fields. The mode-byte-`0` no-install boundary is documented separately: fixture
   `0x16498 replacement allocation failure partial and rejected downloaded character
   exits preserve state` proves the unchanged table/header at object boundary `0x16498`,
   and fixture `0x16498 no-install exits preserve following printable output` proves the
   following printable and FF publication stay on the unchanged default-font page path.
   The even-span downloaded-glyph plus rule/raster composition now has an exact modeled
   install-to-page handoff: host-fetched `ESC )s18W` produces the resource image
   consumed by the parser-driven page stream, including glyph `0x29`, table entry
   `0x00ee`, record delta `0x0780`, bitmap offset `0x078c`, and the 18 copied bitmap
   bytes. The same fixture proves the byte source is one 54-byte `0xa904` ring fetch:
   font bytes `0..24`, page bytes `24..54`, and no remaining ring bytes. ROM control
   flow now narrows the post-install return boundary: disassembly
   `generated/disasm/ic30_ic13_font_payload_setup_015b80.lst` shows `0x15dc6 -> 0x16498
   -> 0x15dcc -> 0x12328`, where `0x15dcc` passes the remaining `0x783140` count to
   `0x12328`; the fixture pins this instance with copy status `1`, copy stream position
   `18`, remaining `0x783140 = 0`, zero-byte drain, and next parser handler `0x10e68`.
   The no-install visible-output fixture pins the same return edges with `0x783140 = 6`,
   six drained rejected-payload bytes, and next handler `0xd04a`; the status-`2`
   partial-install fixture pins the linear/split returns with `0x783140 = 0`, zero
   drain, and next handler `0xd04a`. The downloaded-glyph publication fixtures now also
   pin normal, row-`0x80`, linear-segmented, and split-plane segmented full-success
   publication returns with `0x783140 = 0`, zero drain, and next handler `0xd04a`. The
   combined segmented-wide publication fixture pins the same zero-drain return for
   selector `0x3003`: `0x783140 = 0`, zero drain, and next handler `0xd04a`. The
   payload-control wide publication fixture pins the nonzero return sibling: `0x783140 =
   1`, drained byte `0x26`, and post-return handler `0xf0f0`.
6. Hardware-facing host modes are behaviorally modeled above `0xa904`, but
   MMIO identity and electrical timing for Centronics/serial/RS-422 are not
   board-confirmed. This does not block the documented byte-stream renderer;
   it only blocks hardware-level emulation claims. Evidence:
   [host-byte-fetch.md](host-byte-fetch.md) and supporting report
   `generated/analysis/ic30_ic13_host_byte_fetch_flow.md`.
7. Final device-output validation is not yet a real printer comparison. The
   harness proves ROM-derived rows internally, but pixel-perfect confidence
   ultimately needs rendered page images compared against known LaserJet II
   output for representative byte streams. That is a validation boundary, not
   a reason to defer ROM-local host, parser, page-record, or imaging
   documentation. The initial mixed page-image stream above is a ROM-derived
   internal reproduction contract, not a physical-device comparison. The
   font-sample printout now has its own
   internal rendered-surface checkpoint: fixture `font sample full printout
   segments render through 0x1ed84 and 0x1ef6a` renders all eight source/class
   page-record segments with aggregate digest
   `5e5e735b4fb2a2a4dff4794099a02eaf23fa2dd3e469df8d053db88a321ea6f2`.
   Fixtures `font sample heading continuation emits fresh source heading page
   record` and
   `font sample cartridge heading continuations emit source-specific page
   records` now cover internal and cartridge heading-preflight
   page-record objects. Fixture `font sample row continuation emits fresh
   source heading page record` covers the row-overrun `I01` forced
   page-record object; fixture
   `font sample class-one row continuation emits fresh source heading page
   record` covers the class-one `I16` sibling from `0x40099d18` to
   `0x4409a0e4` with bucket digest
   `842dd781a1093819f918e128999786f94f16cc3562ca25c3a82503ced74f3f3c`.
   Fixture
   `font sample alternate-row continuation emits preadvanced row page record`
   now covers the alternate-row caller edge after `0x1d868` returns D7 `1`:
   `0x1c4a4 -> 0x1d868 -> 0x1c4b6 -> 0x1c9f6 -> 0x1c4ca -> 0x1ca2c ->
   0x1c4d4 -> 0xf06e -> 0x1c4e8 -> 0x1d050 -> 0x1c4f2 -> 0x1cabe`.
   It emits `I01COURIER101210U` after pre-row y advance
   `0x00520000 -> 0x00900000` and pins bucket digest
   `c6f0cbe07a7681d3ecfd3447b8296e97cbf8042d6d962d825f6018d980d5396b`.
   Broader row-overrun cross-products and physical baseline/cell placement
   comparison against a known font/self-test page remain separate gaps.

## Next Disassembly Targets

The next work should follow dataflow, not isolated handlers:

1. Resolve or further constrain the transparent secondary segment-57 resource
   decode boundary. The parser, filtering, page-record, bridge, and renderer
   sides are already documented in `notes/transparent-print-data.md` and
   `Transparent Print Data` above. The remaining pixel-affecting boundary is
   physical/resource-window data for firmware addresses `0x0c0000..0x0c0321`
   after the verified `IC32,IC15` suffix at `0x0bfe22..0x0bffff`. The next
   useful evidence is one of: board/emulator decode evidence for that range, a
   live startup candidate-counter trace after `0x1a2e4`, a direct bus/memory
   read around `0x0c0000`, or physical output matching one of the
   mirror/code-pair/zero-fill fallback-row digests already recorded in
   `notes/resource-rom.md`. The modeled `0x41a` / `0x1a616` continuation
   fixtures now define the expected candidate-counter split: a visible mirror
   would double total `0x78278e` to `48` and low class counts `0x782792` /
   `0x78279a` to `24` each, while code-pair and zero-fill continuations keep
   the verified `24` / `12` / `12` state. Do not re-trace `0x12452`, sampled
   primary high-control bytes, secondary buckets through `448`, or compact
   renderer arithmetic unless new decode evidence contradicts the current
   fixture boundaries.
2. Do not treat reset/default provenance as an open ROM-internal tracing
   target unless new evidence contradicts the composed checkpoints. Semantic
   checkpoint [reset-default-environment.md](reset-default-environment.md)
   covers
   `0xcc52 -> 0xcc70 -> 0xcda2`, page-root finalization through `0xff1e`,
   font-derived HMI refresh through `0xcbd4`, parser/data-chain reset through
   `0xe146`, valid-page publication fixtures, missing-root reset fixtures, and
   addressed compact-bucket publication through `0x1387c`/`0x1381c`.
   `Default Environment Record Producers` covers the selected `0x780eda`
   backing records feeding `0x78219d`, `0x7821a2`, and `0x78219e` through
   loader `0x5e80`; update handlers `0x5060`, `0x50be`, and `0x52ba` writing
   the same backing records and canonical defaults; record-maintenance helpers
   `0x56c2`, `0x571e`, and `0x5a62`; ROM-table fallback from `0xba3e` /
   `0xba44`; panel/service entry points `0x2c84`, `0x3dae`, and `0x4922`;
   debounced `$8000.w & 0xff` byte source `0xa3ca`; retained-record
   commit/readback helpers `0x96c4` and `0x97e4`; and software-visible
   `$a400` phase pairs from `0x9a4a`. Fixture
   `0x5e80 -> 0xcda2 reset consumes default record outputs` joins the producer
   side to the reset consumer, including the reset-gate behavior for
   `0x7821a2 -> 0x782da6` and line-spacing conversion
   `0x78219e -> 0x783160`. Fixture
   `0xcfea/0xcf52/0x104d8 convert default line spacing to reset VMI` covers
   direct, low-clamp, high-clamp, fallback-status, and landscape-table
   branches. The remaining work is external: the device/protocol that drives
   `$8000.w`, physical retained-storage identity and board-level serial pin
   names behind `$a400`/`$8c01`, reconciling manual NVRAM-failure wording with
   the ROM paths found so far, and physical engine/self-test placement against
   known output.
3. Treat font metric-byte combinations as regression expansion unless a new
   state boundary appears. The selected-context bridge, metric consumers, downloaded
   descriptor/payload producer chain, and host-stream downloaded glyph output are now
   tracked. Host-fetched
   `0x1719c` type-0, type-1, and type-2 payloads reach both `d4ac` and `d8fc` span rows,
   and the shared disabled/lower/page/high-x consumer branch family is fixture-backed.
   The seven-case legal descriptor metric matrix plus boundary fixture covers tight
   `d4ac` page-extent gates, rounded-metric clamping into `+0x2c/+0x2d`, shifted `d8fc`
   visible rows, a zero rounded/offset case where both consumers publish spans, negative
   and max-positive copied offset words `0xfffe`/`0xffff`/`0x007f`, `d8fc` lower-bound
   and exact page-extent equality, rounded transform inputs `0x1500`/`0x1508`/`0x15ff`,
   the low-nibble rounded inputs `0x0001`/`0x0003`/`0x0004`/`0x0005`/`0x000f`, a
   byte-boundary rounded submatrix around `0x00fd..0x0102`, `0x17430` first-code-zero
   endpoint and first-code-`range - 1` endpoint, a page-extent fencepost matrix where
   derived heights `42`, `44`, and `45` combine with offset bytes `0`, `1`, and `2`,
   mixed-value matrix that combines first-code/range/rounded/offset changes, a
   tight-range matrix that combines range one/range two with zero/clamped rounded
   outputs and max signed offsets, midpoint case where `d8fc` updates state but leaves
   compact-only output, a lower-bound no-span output path for both consumers, and an
   upper-bound case where `d4ac` still renders a span while `d8fc` exits
   `beyond-page-extent`. Fixture `descriptor metric fields match across inline and
   resource contexts` now pins the legal producer-form boundary: inline/unflagged
   reaches `d4ac`, resource/flagged reaches `d8fc`, and the swapped forms fail at
   concrete map/render boundaries. The producer formulas are no longer the missing
   middle: `0x17430`, `0x1757a`, `0x1762a`, and `0x1719c` now define the canonical,
   derived/cache, and copied metric fields. Additional legal metric values outside the
   pinned legal matrix, boundary, extent-fence, range-endpoint, mixed-value,
   tight-range, low-nibble, and byte-boundary fixtures are cross-products of those
   formulas and consumer gates, not a new semantic middle edge by themselves. Remaining
   metric-related work is external/manual naming for consumed-but-not-staged validation
   fields or broader selected-font combinations that expose different state boundaries.
4. Keep page-image expansion focused on new pixel-affecting state boundaries,
   not on re-running already-composed visible streams. The current suite covers
   the complete text/rule/raster/publication stream, downloaded-glyph FF
   publication stream, parser-driven downloaded-glyph/rule/raster page stream,
   primary plus secondary built-in font-selection visible-output streams,
   inline primary and secondary parser-to-printable streams, the primary and
   secondary symbol fallbacks, non-Roman symbol streams, real final-`@`
   default-table streams, final-`X` built-in, final-`X` inline/downloaded,
   final-`X` preserved-output exits, primary/secondary current-font-RAM
   handoff, and composed selection-to-RAM handoff visible-output streams.
   The bounded downloaded-character matrix has one ROM-facing expansion rule:
   add a case only when it exposes a new publication selector, a new `0x783140`
   remainder, a new `0x12328` drain status, or a new next handler beyond the
   named row-count, wide-remainder, segmented-wide, high-row segmented-wide,
   no-install, status-`2`, payload-control, type-1/type-2
   short/wide/segmented publication, and bit-30-clear fixed-record cases.
   The wrapped source-width-byte cases are already classified by fixture
   `downloaded glyph width-byte boundary truncates page-record span`: low
   source bytes `0x00..0x10` choose compact mode-0 helper entries outside
   decoded row-copy helper heads, while high source bytes `0x11..0xff` render
   through compact-wide `0x1f0d2`. The remaining invalid-helper question is
   physical/device behavior after those bad targets are selected, not another
   ROM parser or page-record tracing target.
   Downloaded-font install-to-page continuity is already a documented ROM
   contract for the covered streams: fixtures `combined host-fetched font
   download stream prints installed glyph` and `combined font download FF
   publishes installed glyph page record` drive one 2,215-byte `0xa904` stream
   through font-control state, `ESC )s2193W` install, printable `%`, FF, bucket
   entries `1` and `9`, and `0x1ed84`/`0x1ef6a`. Fixture `parser-driven
   downloaded glyph rule raster stream composes through 0x1ef6a` proves one
   54-byte `0xa904` ring fetch and the shared
   `0x15dc6 -> 0x16498 -> 0x15dcc -> 0x12328` post-install drain. Fixture
   `downloaded glyph byte-24 state handoff feeds following page handler` pins
   the byte-24 handoff: the page phase consumes `font_command_final_header`
   from the same font-command helper, asserts it matches the install event
   header, reports pointer bytes `00 00 07 80`, record bytes, bitmap bytes,
   next handler `0x10e68`, and the composed-row digest. Remaining
   downloaded-font work should add cases only when they change the byte-24
   header, installed record, `0x783140` remainder, `0x12328` drain status, next
   handler, bucket assignment, render dispatch, or rows. Fixture `even-span
   downloaded glyph rule raster FF publication renders page record` carries
   the same bucket `5` raster+glyph chain and selector-7 rule through
   `0xff1e`, then renders the published pool record with digest
   `84762454e8bba9ce22aa5922b598fc5aed7c3ef9dfe9e55223a178c567f612d3`. Fixture
   `parser-driven downloaded glyph rule raster FF publishes page record` adds the
   parser-produced sibling: the 55-byte fetched stream keeps font bytes
   `0..24`, page bytes `24..54`, FF byte `54..55`, bucket `5` raster+glyph
   chain, raw selector-7 rule publication, and matching published rows.
   The primary built-in case proves `ESC (s0p10h12v0s0b3T!!` through parsed selection
   handlers, selected context `0xc008004c`, printable `0xd04a` entries, object prefix
   `00 00 00 00 00 00 00 02 00 6a 00 00 68 02`, render-record context slot `0xc008004c`,
   and final Courier glyph rows. The secondary case proves `ESC )s0p16h8v0s0b0T SO !!`
   through selected context `0xc00ae122`, SO handler `0xc6b8`, object prefix `00 00 00
   00 00 01 00 02 00 c9 00 00 cb 01`, render-record context slots `(0xc008004c,
   0xc00ae122)`, and final secondary Line Printer rows. The primary fallback case proves
   `ESC (1234U ESC (s0p10h12v0s0b3T!!`: requested word `0x9a55` misses in `0x156de`,
   fallback word `0x0115` survives, and the final selected context, map, object prefix,
   context slot, and rows match the primary case. The remembered-primary case proves the
   middle source between requested and fallback: with requested word `0x9a55` and
   remembered word `0x0115`, fixture `remembered primary symbol feeds visible
   page-record rows` takes the `0x156de` remembered branch, selects context
   `0xc008004c`, rebuilds map `0x782f32`, queues object prefix `00 00 00 00 00 00 00 02
   00 6a 00 00 68 02`, and renders digest
   `8b36cfd64d818c0982b172982156f8be9687388c9679cd83538c9d1098d9bb2c`. The secondary
   remembered case proves the parallel middle source for `ESC )1234U ESC )s0p16h8v0s0b0T
   SO !!`: requested word `0x9a55` misses in `0x156de`, remembered word `0x000e` first
   rejects slot `0x782324` / record `0x019d18`, then matches slot `0x782330` / record
   `0x01a984`, selects context `0xc00ae122`, crosses SO `0xc6b8`, queues object prefix
   `00 00 00 00 00 01 00 02 00 c9 00 00 cb 01`, and renders digest
   `b8ee0f8dd3e6ed70afa219bc00605d75249ae047a67fb67189693057d7936e6c`. The secondary
   fallback case proves the fallback-table sibling for the same stream: requested word
   `0x9a55` misses in `0x156de`, fallback word `0x000e` survives, and the final selected
   context, map, object prefix, context slots, and rows match the secondary SO case. The
   primary RAM handoff case proves seeded `0x782ee6 = 0xc008004c` through SI `0xc68a`,
   `0xc428(0)`, `0xc4fc`, page-root slot `0`, and following `!!` visible rows on an
   existing root. The secondary RAM handoff case proves seeded `0x782ef6 = 0xc00ae122`
   through SO `0xc6b8`, `0xc428(1)`, `0xc4fc`, page-root slot `1`, and following `!!`
   visible rows on an existing root. The composed handoff cases prove `ESC
   (s0p10h12v0s0b3T SI !!` and `ESC )s0p16h8v0s0b0T SO !!` from host-fetched selection
   bytes to selected current-font RAM, page-root slot install, and rows matching the
   pinned visible fixtures. The inline cases prove `ESC (s0p10h12v0s0b3T!!` and `ESC
   )s0p16h8v0s0b0T SO !!` in one mixed-stream state from selection handlers to printable
   source capture, HMI, object prefix, bridge context slots, and rows. The non-Roman
   symbol cluster is now part of the visible-output suite too: fixture `live parser
   symbol-set streams select non-Roman built-ins` proves primary `ESC (0N`, `ESC (10U`,
   and `ESC (11U` through parser handlers `0x11eb6`, `0x1201e`, and `0x120be`,
   selected-font refresh, record choices `0x000cb8`, `0x000418`, and `0x000868`, and map
   rebuild path `selected-symbol-not-roman8`. Fixture `non-Roman symbol streams select
   visible built-ins` then carries primary `0N`/`10U`/`11U` streams through matching
   `ESC (s0p10h12v0s0b3T!!` tails and secondary `ESC )0N`/`10U`/`11U` streams through
   matching `ESC )s0p16h8v0s0b0T SO !!` tails, crossing SO handler `0xc6b8` for
   secondary, preserving compact object prefixes, bridge context slots, and rendered-row
   digests. Fixture `real final-@ default-table streams select visible built-ins` closes
   the parser-exposed `@0`/`@1`/`@2`/`@3` edge: after the real-backed default-table
   caller stream leaves active words `[0x000e, 0x0005]`; the primary tail renders from
   context `0xc0080cb8` with the primary non-Roman row digest, while the secondary tail
   renders from context `0xc00ad4aa` after SO with the secondary row digest. Remaining
   suite cases should add other fallback/error font-selection visible-output variants
   beyond the remembered primary/secondary paths, the two symbol misses, the
   `0N`/`10U`/`11U` primary/secondary streams, the real final-`@` primary/secondary
   streams, and the covered final-`X` streams. Fixture `font-ID built-in selection feeds
   visible page-record rows` covers that final-`X` stream: host-fetched `ESC (7X!!`
   reaches `0x120be`, selects context `0xc0089fb0` through `0x17708`, and renders row
   digest `73cbb28bfab786807b9a3186eb3946efae550cde2e5448f0549f88ebf8c8a631`. Fixture
   `font-ID secondary built-in selection feeds visible SO page-record rows` covers the
   class-one built-in final-`X` sibling: host-fetched `ESC )8X SO !!` reaches `0x120be`,
   selects context `0xc00ae122` through `0x17708`, reuses page-root slot `1` through
   `0xc4fc`, crosses SO `0xc6b8`, and renders row digest
   `b8ee0f8dd3e6ed70afa219bc00605d75249ae047a67fb67189693057d7936e6c`. Fixture `font-ID
   primary inline/downloaded selection feeds visible page-record rows` covers the
   primary bit-30-clear final-`X` stream: host-fetched `ESC (4660X!` reaches `0x120be`,
   selects context `0x00000100` through `0x17708`, reuses page-root slot `0`, queues
   object prefix `00 00 00 00 00 00 00 01 01 66 01 00 00 00`, and renders row digest
   `e0c6cbbf133aaaf522868ef7f28856f06b0d54b4dd9368a090fe7c85e7b1d563`. Fixture `font-ID
   inline/downloaded selection feeds visible page-record rows` covers the secondary
   sibling: host-fetched `ESC )4660X SO !` reaches `0x120be`, selects the same context
   through `0x17708`, reuses page-root slot `1`, crosses SO `0xc6b8`, queues object
   prefix `00 00 00 00 00 01 00 01 01 66 01 00 00 00`, and renders the same row digest.
   Fixture `0x17708 font-ID non-selected exits preserve prior selection` covers the
   direct final-`X` helper exits for scan miss, candidate-slot miss, class mismatch, and
   context-full through the exact `0x17708` terminal status, with no `0x14c64` map
   dispatch. Fixture `font-ID non-selected exits keep prior visible rows` appends the
   same host-fetched `ESC (7X!!` printable tail to those preserved-state outcomes:
   following `!!` consumes prior context `0xc008004c`, queues object prefix `00 00 00 00
   00 00 00 02 00 6a 00 00 68 02`, and renders row digest
   `8b36cfd64d818c0982b172982156f8be9687388c9679cd83538c9d1098d9bb2c`. Fixture `font-ID
   secondary non-selected exits keep prior SO visible rows` covers the slot-1 sibling:
   host-fetched `ESC )8X SO !!` reaches the same four terminal `0x17708` statuses, no
   `0x14c64` dispatch occurs, and the SO/printable tail consumes preserved secondary
   context `0xc40ad87a`, queues object prefix `00 00 00 00 00 01 00 02 20 c9 00 20 cb
   01`, and renders digest
   `b8ee0f8dd3e6ed70afa219bc00605d75249ae047a67fb67189693057d7936e6c`. Fixture `0x13eb8
   transient and cache-hit exits avoid dispatch` covers the selected-font refresh exits
   that stop before `0x144d2`/`0x14c64`: transient `0x78298f` stores selected context
   `0xc008004c`, while cache-hit returns after `0x148f8`. Fixture `0x13eb8 no-dispatch
   exits keep prior visible rows` carries both exits into visible output: the transient
   path leaves following `!!` on prior context `0xc0089fb0`, object `00 00 00 00 00 00
   00 02 00 89 00 00 87 02`, and digest
   `73cbb28bfab786807b9a3186eb3946efae550cde2e5448f0549f88ebf8c8a631`; the cache-hit
   secondary path crosses SO and leaves following `!!` on prior context `0xc40ad87a`,
   object `00 00 00 00 00 01 00 02 20 c9 00 20 cb 01`, and digest
   `b8ee0f8dd3e6ed70afa219bc00605d75249ae047a67fb67189693057d7936e6c`. The common
   refresh gate `0xc580` is now a composed branch cluster rather than a hidden
   font-selection middle edge: dirty-1 primary/secondary first-clear installs, full-live
   matching-context reuse, full-live/no-match `0xc4fc = 0x11` skip, dirty-1
   selector-mismatch refresh-only, dirty-2 primary/secondary selector-match installs,
   and dirty-2 selector-mismatch remembered-word-only paths are documented in
   `notes/semantic-state-model.md` with fixture names and field groups. Remaining
   font-selection work is broader variants that expose new state boundaries; the named
   high-value unresolved edge is now the transparent secondary segment-57 bitmap source
   interpretation beyond the covered transparent data paths. Current transparent
   coverage includes the default-filtered C0/high-control fixed-space path, nonzero C0
   plus high-control `0x80` printable path, primary interior samples `0x81`, `0x88`,
   `0x90`, and `0x97`, primary tall bucket-crossing `0x98`, primary top-of-range `0x9f`,
   the secondary segmented page-record boundary from `SO ESC &p3X!\x80!`, and the
   secondary renderable prefix through bucket `448`. The first unresolved secondary
   bucket is `456`, glyph `0x5f`, segment `0x39`, file source `0x03fe22`, firmware
   source `0x0bfe22`, and required byte range `0x0bfe22..0x0c0321`; only `478` bytes are
   inside the verified `IC32,IC15` resource-pair image. Disassembly of `0x1f354` and
   `0x1f1f0` makes the unresolved part a physical/resource-window mapping question after
   `0x0c0000`, not a transparent parser or row-skip question. The current-band
   segment-57 rows are now pinned across mirror, code-pair, and zero-fill continuation
   hypotheses with digest
   `f0c1127f9e6b203f9829ab43f159b89c3f7dda687a47d4c09971077eac55c96e`; the fallback rows
   diverge. The same fixture hashes the verified `0x0bfe22..0x0bffff` suffix as
   `e0a0fd34ce7a39f79ecd27c0ee288631554a0ff78359b72e27ea6087651bcf1f` and the three
   continuation candidates as
   `e435e3b9d033e491b57282a88b0f321aa5fecae8128fa060844cc01379349563`,
   `90934acf59d9e8519c9149dc5df228f8fec2bff8451427be265489be967cdd16`, and
   `359f38eef400e2fa3924a3258652e74ee19cd46cb92e47bce91f1194fce25e9e`, so the remaining
   requirement is board/emulator memory-map evidence for `0x0c0000..0x0c0321`. That
   byte-side evidence is now reproducible with tracked tool
   `tools/probe_resource_window.py --quiet`, which verifies the local ROM
   hashes, the `478`-byte verified suffix, the `802`-byte continuation
   candidates, and the mirror/code-pair/zero-fill `0x41a` / `0x1a616` scanner
   consequences from ignored local ROM inputs. The contested
   range is outside the verified `IC32,IC15` resource-pair image described by
   `data/rom_manifest.json`, and startup byte-sum evidence only covers
   `0x080000..0x0bffff`. Disassembly of `0x1a2e4` / `0x1a616` shows the built-in
   resource scanner covers `0x080000..0x0ffffe` in `0x40000` steps, while optional
   cartridge/resource scans are separate `$8000.14/15`-gated windows at
   `0x200000..0x5ffffe`; the segment-57 read is therefore a built-in decode question
   after the verified pair, not a cartridge-window read. Fixture `0x41a HEAD scanner
   would duplicate records under simple resource mirror` now constrains one candidate: a
   full resource-pair mirror at `0x0c0000` would make scanner `0x41a` see a second
   `HEAD` chain and walk `48` typed records, so mirror cannot be treated as only a local
   fallback-row source unless hardware/gating hides it from scanner reads. Fixture
   `0x41a HEAD scanner rejects non-HEAD 0x40000 continuations` constrains the code-pair
   and zero-fill candidates: their second-probe markers are `0x00800000` and
   `0x00000000`, so neither duplicates `HEAD` records for startup scanning. The hardware
   evidence in `notes/formatter-interface-pca.md` leaves address-controller/jumper ROM
   decode as the unresolved physical state. The `ESC Y ... ESC Z` display-functions loop
   is now documented in `notes/pcl-parser-core.md` and `notes/semantic-state-model.md`;
   fixture `ESC Y display-functions stream reaches page-record output` covers the
   default-filter normal `0x12536..0x1261e` page-output path, fixture `ESC Y
   display-functions filter-on routes controls as printable` covers the complementary
   nonzero context/filter route through `0xd04a`, and fixture `0x12120 ESC Y alternate
   append stores normalized display bytes` covers the alternate/data append-only
   `0x12120..0x1219c` path around `0xe002`. Remaining display-functions risk is broader
   physical/page comparison, not the command-family loop boundary or the documented
   filter predicates. Downloaded-glyph publication is now composed as a bounded matrix
   rather than a generic open edge. Fixture `0x16b1a descriptor width helper emits only
   mode 1/2` pins the accepted mode-byte writer at `0x16b36..0x16b6a` and the invalid
   no-write branch at `0x16b26..0x16b34`. Fixture `downloaded glyph width-span matrix
   publishes and renders all main helpers` covers parser-produced spans `1..16`,
   odd-span split-plane copies, bucket-0 FF publication, and all main `0x1f08e` helpers
   `0x1fa5c..0x26910`. Fixture `downloaded glyph wide-remainder matrix publishes and
   renders compact chunks` covers matched spans `17..32`, `0x2f27c` full chunks,
   `0x1f1ac` remainders `1..15`, the span-`32` no-remainder sibling, zero-drain returns,
   and probes spans `33`, `48`, `49`, `64`, and `255` with matched rows. Fixture
   `downloaded glyph segmented-wide matrix publishes and renders compact chunks` covers
   matched spans `17..32` at rows `0x81`, buckets `0` and `8`, segment-1 object byte
   `0x30`, `0x2f27c` full chunks, `0x1f1ac` remainders `1..15`, the span-`32`
   no-remainder sibling, zero-drain returns, and probes segmented-wide spans `33`, `48`,
   `49`, and `64`. Fixture `downloaded glyph width-byte boundary truncates page-record
   span` pins source-width wrapping for spans `0x00ff`, every span `0x0100..0x0111`,
   `0x017f`, `0x0180`, `0x01fe`, and `0x020d`: installed width words survive, but
   `0x12f2e` sees only the low width byte. Source width bytes `0x11..0xff` select
   compact-wide `0x1f0d2` and now render rows matching the installed bitmap for spans
   `0x00ff`, `0x0111`, `0x017f`, `0x0180`, and `0x01fe`; every source width byte
   `0x00..0x10` selects compact mode-0 helper entries outside decoded row-copy helper
   heads. The fixture now records the exact derived helper target class for those
   wrapped cases: all sampled low-byte cases except `0x0102` leave firmware address
   space, and `0x0102` targets firmware address `0x0066cc` with opcode `0x4a39`
   instead of a row-copy helper head. Fixture
   `downloaded segmented-wide row-byte boundary truncates page-record segments` pins the
   row-byte sibling for installed row words `0x0002`, `0x007f`, `0x0080`, `0x0081`,
   `0x0083`, `0x00fe`, `0x00ff`, `0x0100`, `0x0101`, `0x0181`, `0x0182`, `0x01ff`,
   `0x0200`, and `0x0201`: `0x12f2e` sees only the low source row byte. Low row bytes
   above `0x80` produce segment `1` in bucket `8` and segment `0` in bucket `0`; low row
   bytes `0x00..0x80` select wide bucket `0`. The short/segmented row-count matrix now
   covers short rows `0x01..0x1f`, `0x21..0x3f`, and `0x41..0x7f`, plus segmented rows
   `0x83..0xff`; the named rows-`0x20`, rows-`0x40`, row-`0x80`, linear-segmented
   row-`0x81`, and rows-`0x82` publication fixtures cover their boundary siblings
   through FF, `0xff1e`, `0x1ed84`, and `0x1ef6a`. The same row-count matrix pins
   `0x15dc6 -> 0x16498 -> 0x15dcc -> 0x12328` with copy status `1`, `0x783140 = 0`, zero
   drained bytes, and next handler `0xd04a`. The high-row truncation matrix covers rows
   `0x0101`, `0x0102`, and `0x0103`: installed row words remain canonical, but the
   printable source exposes low row bytes `0x01`, `0x02`, and `0x03`, queues selector
   `0x0003`, and exceeds the `0x1fe76` table's valid maximum index `128` after `0x1f414`
   splits fallback rows `199`, `200`, and `201`. No-install and partial-install recovery
   are page-visible: fixture `0x16498 no-install exits preserve following printable
   output` proves allocation failure, descriptor mode-byte-`0`, and
   high-character/header-type status-`0` rejects leave the next printable byte on the
   default-font path and publish that default bucket through trailing FF; fixture
   `0x16498 status-2 partial installs remain printable` proves linear and split-plane
   status-`2` partial glyphs remain printable and publish the same rows, fixture
   `0x15b9a resumes downloaded-character continuation objects` proves that the saved
   continuation state can complete those linear and split-plane object bitmaps and that
   the `0x15e22 -> 0x15b9a -> 0x15e28 -> 0x15dcc -> 0x12328` success return boundary
   drains zero bytes before the next printable byte, and fixture `0x15b9a partial and
   failed resumes update continuation or release object` proves status-`2` resave and
   status-`0` offset-table release from the same continuation state. Row-count
   publication coverage for parser-produced rows `0x0001..0x00ff` is now closed by the
   row-count matrix plus named `0x0020`, `0x0040`, `0x0080`, `0x0081`, and `0x0082`
   fixtures. The `0x15d0a` descriptor route is not a remaining syntax hole: fixture
   `0x15d0a descriptor grammar exits and handler matrix` covers early drains and all
   four current-record/continuation by bit-30 polarities, while fixture `0x16b1a
   descriptor width helper emits only mode 1/2` covers the accepted helper-table
   mode-byte writer and invalid-width no-write branch. The sampled nonzero-high-byte row
   publication boundary is now classified rather than remaining generic: `downloaded
   segmented-wide row-byte boundary truncates page-record segments` covers span-`0x11`
   row words `0x0100`, `0x0101`, `0x0181`, `0x0182`, `0x01ff`, `0x0200`, and `0x0201`
   through install, `0x12f2e`, `0xff1e`, and the first render split; `host-fetched
   rows-0x102 downloaded glyph FF publication truncates page-record rows` plus
   `downloaded glyph high-row truncation matrix preserves installed rows` cover short
   span-`2` row words `0x0101..0x0103` through the same source-byte truncation and
   identify the exact `0x1fe76` helper-table overflow boundary. Fixture `downloaded
   segmented-wide row-span cross-products render selected segment` now covers
   segmented-wide rows `0x0082` and `0x0083` crossed with spans `17`, `18`, `31`, and
   `32` through selected segment `1`, bucket `8`, `0x1f264`, and installed-bitmap row
   comparison. Fixtures `downloaded segmented-wide high-row fallback renders selected
   segment`, `downloaded segmented-wide high-row even-span fallback renders selected
   segment`, and `downloaded segmented-wide high-row span-32 fallback renders selected
   segment` now cover sampled higher-row fallback cases, row `0x0181` at spans `17`,
   `18`, and `32`, through segment `1`, bucket `8`, `0x1f264`, a `32/96`
   current/fallback split, and installed-bitmap row comparison; fixture `downloaded
   segmented-wide high-row span-31 fallback hits source boundary` pins the adjacent
   large-remainder source-read boundary at fallback A2 offset `+0xb50`. Fixtures
   `downloaded segmented-wide row-0x0182 fallbacks render selected segment` and
   `downloaded segmented-wide row-0x0182 span-31 fallback hits source boundary` repeat
   that success/boundary split for row `0x0182`: spans `17`, `18`, and `32` render the
   selected segment with the same `32/96` split, while span `31` stops at fallback A2
   offset `+0xb50`. Fixtures `downloaded segmented-wide row-0x01ff fallbacks render
   selected segment` and `downloaded segmented-wide row-0x01ff span-31 fallback hits
   source boundary` repeat that split for row `0x01ff`, the highest sampled
   `0x01xx` low-byte-above-`0x80` row. Fixtures `downloaded segmented-wide
   row-0x0281 fallbacks render selected segment` and `downloaded segmented-wide
   row-0x0281 span-31 fallback hits source boundary` repeat that split after the
   installed row word advances beyond `0x01ff`: the installed glyph preserves row
   `0x0281`, the printable source row byte is `0x81`, `0x12f2e` emits only segments
   `1` and `0`, and selected segment `1` renders the same `32/96` current/fallback
   rows for spans `17`, `18`, and `32`, while span `31` stops at fallback A2 offset
   `+0xb50`. Fixtures `downloaded segmented-wide high-row 0x02xx matrix renders
   selected segment` and `downloaded segmented-wide high-row 0x02xx span-31 matrix hits
   source boundary` repeat that selected-segment success/source-boundary split for row
   words `0x0282` and `0x02ff`: spans `17`, `18`, and `32` render the same `32/96`
   current/fallback rows, while span `31` stops at fallback A2 offset `+0xb50`.
   Fixtures `downloaded segmented-wide high-row 0x03xx matrix renders selected segment`
   and `downloaded segmented-wide high-row 0x03xx span-31 matrix hits source boundary`
   extend that split to row words `0x0381`, `0x0382`, and `0x03ff`: spans `17`,
   `18`, and `32` render the same `32/96` selected segment, while span `31` stops at
   fallback A2 offset `+0xb50`. Fixtures `downloaded segmented-wide high-row 0x04xx
   matrix renders selected segment` and `downloaded segmented-wide high-row 0x04xx
   oversized payload counts stop before renderer` split the next high-byte range:
   row words `0x0481`, `0x0482`, and `0x04ff` at spans `17`, `18`, and `24` render the
   same selected-segment `32/96` split, while spans `31` and `32` exceed the `ESC )s#W`
   parser numeric cap `0x7fff` and stop inside bitmap payload before `0x16498` renderer
   entry. The fixture records exact command-prefix length, parser stop offset, and full
   payload end offset for each oversized case. Fixtures
   `downloaded segmented-wide high-row 0x05xx matrix renders selected segment` and
   `downloaded segmented-wide high-row 0x05xx oversized payload counts stop before
   renderer` continue that cap split: rows `0x0581` and `0x0582` render spans `17`,
   `18`, and `23`; row `0x05ff` renders spans `17`, `18`, and `21`; adjacent
   `0x0581`/`0x0582` span-24/span-32 and `0x05ff` span-22/span-32 payloads exceed
   `0x7fff` before renderer entry. Fixtures
   `downloaded segmented-wide high-row parser-limit matrix renders selected segment`
   and `downloaded segmented-wide high-row parser-limit oversized counts stop before
   renderer` close the same family at the absolute span-17 byte-count limit:
   `0x0681`/`0x0682` render spans `17`, `18`, and `19`; `0x06ff` renders spans
   `17` and `18`; `0x0781`, `0x0782`, and `0x0787` render span `17`; and
   `0x0788*17` stops before renderer entry. Rows above `0x0787` therefore cannot
   reach segmented-wide rendering in this host-fetched `ESC )s#W` shape.
   `notes/downloaded-fonts.md` now classifies the unsampled below-cap
   segmented-wide high-row variants as regression cross-products, not an
   unresolved semantic middle edge: the canonical installed row word is
   preserved by `0x16498`, `0x12f2e` consumes only the low row byte for
   selector choice, span selects renderer helper/remainder metadata, and the
   parser count cap cuts off the remaining high rows/spans before renderer
   entry.
   Remaining downloaded-character publication work is therefore limited to
   physical/pixel behavior after the fully documented wrapped source-byte mode-0
   invalid-helper boundaries, publication combinations that introduce a new
   page-record selector, and return-boundary siblings that introduce a new
   `0x783140` remainder, drain status, or next handler outside the named
   row-count, wide-remainder, segmented-wide matrix, high-row segmented-wide
   matrix, normal, row-`0x80`, linear-segmented, split-plane segmented,
   segmented-wide publication, no-install, status-`2`, bit-30-clear
   fixed-record, and payload-control cases. It is not the
   documented mode-byte-`0` visible recovery boundary. The
   publication-command checkpoint in `notes/publication-commands.md` now
   covers host-fetched reset, FF, page-size, orientation, paper-source, and
   copies streams through parser dispatch, `0xff1e`,
   `0x1ed84`/`0x1edc6`, `0x1ef6a`, and final row comparison; reset, FF,
   page-size, orientation, paper-source, and copies also have addressed
   allocation variants. The exact command-side state at that boundary is:
   page-size `! ESC &l1A` publishes before page code `6` / portrait geometry,
   orientation `! ESC &l1O` publishes before orientation `1` / landscape
   geometry, paper-source `! ESC &l2H` publishes before `0x782da6 = 0x80`,
   `0x782998 = 1`, `0x780e8f = 0x80`, and `0x780e26 = 1`, and copies
   `! ESC &l2X FF` stores `0x782da4 = 2` before FF publication writes
   pool-header word `+0x0c = 2`.
