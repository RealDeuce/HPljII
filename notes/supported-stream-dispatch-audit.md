# Supported Stream Dispatch Audit

This note is the checked-in audit ledger for the supported stream dispatch
rows named by [pcl-command-map.md](pcl-command-map.md#supported-stream-dispatch-matrix)
and routed into the owner notes indexed by
[pcl4-language.md](pcl4-language.md#rom-semantic-index-for-quick-reference).
It is not a generated table. Each audited row passes only when the checked-in
owner documentation names the admitted bytes, parser or direct-reader state,
handler address, RAM fields read or written, downstream consumer,
output/no-output effect, evidence, and any exact residual boundary.

Audit state:

- Complete in this ledger:
  transparent/display/status byte-reader cluster below; printable/direct C0
  control cluster below; cursor, motion, margin, and span command cluster
  below; page environment, publication, VFC, raster transfer, rectangle/rule,
  font/downloaded-glyph, macro replay, parser-only/no-output, and page/render
  crosswalk clusters below.
- Still pending in this ledger:
  none. Further work should start from streams that change an owner note,
  page-object field, bridge field, render helper, or unresolved boundary.

## Transparent, Display, And Status Byte Readers

This cluster is broad enough because it covers multiple command-table
handlers, the shared direct-reader loops that fetch bytes outside the normal
one-byte parser handoff, alternate/data append variants, local Control-Z
siblings, and host/status side channels. It starts at parser dispatch from
host bytes and stops at one of four semantic outcomes: ordinary text imaging,
fixed-space/control handling, stored append bytes for later replay, or
host/status output with no page object.

### Audited Rows

- `ESC &p#X` / `ESC &p#x`, transparent print data:
  parser mode `5 -> 9` selects handler `0x11f5a`. The handler schedules a
  delayed payload through `0x121cc`; restore `0x12218` reopens saved command
  record `0x782a20..0x782a25` and calls reader `0x12452` in normal mode.
  Canonical parser fields are `0x78299e`, delayed flag `0x782a1a`, delayed
  handler pointer `0x782a1c`, and command-record count word `+2`. The reader
  consumes host bytes through `0xa904`, filter/context fields
  `0x782f06`, `0x782eea + 0x10 * slot`, `0x782efa`, `0x783132`, and
  `0x783133`, then calls `0xd04a` or `0xd0f0`. Page-producing consumers are
  the ordinary compact/fixed text path
  `0xd04a -> 0x1393a -> 0x12f2e -> 0x1387c`, publication `0xff1e`, bridge
  `0x1ed84 -> 0x1edc6`, and compact render dispatch
  `0x1ef6a -> 0x1efc2 -> 0x1effe`. Alternate/data restore diverts positive
  counts through `0x12358 -> 0xdace -> 0xe002`, so it stores bytes for replay
  instead of calling `0x12452`. Owner evidence is
  [transparent-print-data.md](transparent-print-data.md#owner-summary),
  `generated/disasm/ic30_ic13_transparent_data_handler_011f5a.lst`, and
  fixture `0x11f5a/0x12452 transparent text restores and consumes counted
  bytes`.

- `ESC Y ... ESC Z`, normal display-functions reader:
  parser mode `1` selects handler `0x12536`. The direct reader fetches loop
  bytes through `0xa904`, tracks the local previous-`ESC` flag in register
  `D4`, normalizes local `0x1a 0x58` through `0xd99a`, and routes each
  normalized value through `0xd04a` or `0xd0f0` according to selected filter
  fields `0x782eea + 0x10 * slot`, `0x782efa`, `0x783132`, and `0x783133`.
  Local `ESC Z` terminates after the terminating bytes have followed the same
  routed-value rules. Visible output is therefore compact text or fixed-space
  state through the shared direct-control/page-record owners, not a separate
  display-specific page object. Owner evidence is
  [display-functions.md](display-functions.md#display-functions-decision-checkpoint),
  [Display-Functions Outcome
  Matrix](display-functions.md#display-functions-outcome-matrix),
  `generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst`, and
  fixtures `ESC Y display-functions stream reaches page-record output` and
  `ESC Y display-functions filter-on routes controls as printable`.

- `ESC Y ... ESC Z`, alternate/data display-functions append: alternate/data table
  `0x116f6` maps mode-`1` `ESC Y` to handler `0x12120`. It writes literal `ESC Y` and
  each normalized loop byte through append sink `0xe002` until local `ESC Z` or no-byte
  return. Canonical state is the append/data-chain destination, including
  fixture-visible chunk `0x783988`, rather than page root `0x78297a` or render inputs.
  Its first downstream consumer is the macro/data-chain replay source, which later feeds
  stored bytes back through `0xa904` and the normal parser. It creates no immediate page
  object and has no row-store endpoint until replay. Owner evidence is
  [display-functions.md](display-functions.md#append-state-reentry-boundary),
  [macro-data-chain.md](macro-data-chain.md#owner-summary), and fixture `0x12120 ESC Y
  alternate append stores normalized display bytes`.

- Local Control-Z terminals:
  parser mode `2` has table-dependent siblings. Normal `0x1a 0x1a` dispatches
  `0x120d2`, which reads selected slot `0x782f06`, derives
  `0x10 * slot`, tests context byte `0x782eeb + 0x10 * slot`, and calls
  `0xd04a(0x1a)` only when that byte is `1`; otherwise it returns with no
  page object. Normal `0x1a X` dispatches `0x1219e`, which calls
  `0xd04a(0x100)`. Alternate/data `0x1a 0x1a` dispatches `0x1210c` and
  appends literal `0x1a` through `0xe002`; alternate/data `0x1a X` dispatches
  `0x121b2`, calls `0xd99a`, and appends normalized `0x7f` through `0xe002`.
  The page-producing siblings consume the same compact text downstream route
  as printable bytes; the alternate siblings stop at append/replay state.
  Owner evidence is
  [display-functions.md](display-functions.md#display-functions-outcome-matrix),
  [Display-Functions Outcome
  Matrix](display-functions.md#display-functions-outcome-matrix), and
  `generated/disasm/ic30_ic13_control_z_handlers_0120d2.lst`.

- `ESC z`, display-functions off/status:
  parser mode `1` selects handler `0xcd86`. It reads active data-chain frame
  pointer `0x782d76` and frame byte `+9`; only the zero-frame case calls
  status helper `0x9c2c`. That helper writes markers `0x7821cc` and
  `0x7822db`, ORs bit `0x8` into status accumulator `0x780e2a` through
  `0x9b5e`, and clears the marker. This route creates no page root, compact
  object, publication request, bridge record, render helper input, or row
  store. Owner evidence is
  [display-functions.md](display-functions.md#display-functions-outcome-matrix),
  [errors-and-status.md](errors-and-status.md#owner-summary), and
  `generated/disasm/ic30_ic13_status_signal_helpers_009b5e.lst`.

- `ESC *r#K` and `ESC *s#^`, model/status host backchannel:
  parser modes `7` and `6` both dispatch wrapper `0x12034`. The wrapper calls
  `0x11efe`, appends a synthetic six-byte command record with word `+2 = 1`,
  and enters producer `0x122be..0x12326`. The producer rewinds parser cursor
  `0x78299e`, fetches the following query byte through `0xda9a`, and emits
  literal `33440A\r\n` from `0x12280..0x12288` through FIFO helper `0xb090`
  only for query byte `0x11` with active word `1` or `-1`. FIFO fields are
  `0x783ed2`, `0x783ed4`, `0x783ed8`, and `0x783e92..0x783ed1`. This route
  is host-visible protocol output, not page/image output; it can affect pixels
  only if the host reacts by sending a different later byte stream or if FIFO
  fullness stalls the producer. Owner evidence is
  [errors-and-status.md](errors-and-status.md#model-id-command-stream),
  [errors-and-status.md](errors-and-status.md#reproduction-contract), and
  fixture `0x12034/0x122be model-ID response emits FIFO literal`.

### Field Classification

- Canonical parser/direct-reader state:
  mode byte `0x782999`, alternate/data flag `0x782c18`, parser command cursor
  `0x78299e`, delayed flag `0x782a1a`, delayed handler pointer `0x782a1c`,
  saved delayed record `0x782a20..0x782a25`, transparent count word `+2`,
  display-reader previous-`ESC` flag `D4`, normalized loop value `D5`, and
  direct byte source `0xa904`.
- Canonical text/page state:
  selected slot `0x782f06`, selected C0 filter byte
  `0x782eea + 0x10 * slot`, Control-Z context byte
  `0x782eeb + 0x10 * slot`, fallback high-control filter `0x782efa`,
  high-character flags `0x783132` / `0x783133`, current page root
  `0x78297a`, compact bucket root `+0x1c`, and text object state consumed by
  `0xd04a`, `0xd0f0`, `0x12f2e`, and `0x1387c`.
- Canonical append/status/host-output state:
  append sink `0xe002`, data-chain frame pointer `0x782d76`, fixture-visible
  append chunk `0x783988`, status markers `0x7821cc` and `0x7822db`, status
  accumulator `0x780e2a.3`, host FIFO fields `0x783ed2`, `0x783ed4`,
  `0x783ed8`, and `0x783e92..0x783ed1`.
- Derived/cache state:
  selected-slot scale product from `0x332ee`, display/transparent local
  high-control filter word, compact coordinates and bucket keys produced after
  `0xd04a`, and render-band products after publication.
- Parser scratch:
  temporary loop bytes, local `0x1a` probe state, synthetic command record
  installed by `0x11efe`, and the query byte consumed by `0x122be..0x12326`.
- Firmware bookkeeping:
  `0xd99a` normalization/reporting side effect, payload-control counter
  `0x782c72`, delayed restore `0x12218`, alternate restore wrapper
  `0x12358`, status helper `0x9c2c`, host FIFO helper `0xb090`, and blocking
  wait on `0x7801e2` when the FIFO is full.
- Hardware/external state:
  host-output backend selected by `0x780e40`, panel/service consumers of
  status bits, and secondary resource-window bytes beyond the verified ROM
  suffix.
- Unknown:
  manual-facing names for several filter and status fields, the physical
  identity of host-output backend registers under `0x780e40`, and secondary
  resource-window bytes `0x0c0000..0x0c0321`.

### Output And Boundary Result

The ROM-local parser and direct-reader edges in this cluster are audited.
Normal transparent and display bytes reach the documented compact/fixed text
owners; alternate/data bytes stop at append storage until replay; `ESC z`
stops at status markers; and `ESC *r#K` / `ESC *s#^` stop at host FIFO
output. No audited route in this cluster has an unresolved parser handler,
missing command-family owner, unnamed first consumer, or unclassified
page/no-page effect.

Exact residual boundaries:

- Transparent secondary high-control rendering can require resource bytes
  `0x0c0000..0x0c0321` after verified suffix `0x0bfe22..0x0bffff`. This is tracked as a
  missing-resource-data boundary in
  [unresolved-boundaries.md](unresolved-boundaries.md#secondary-segment-57-resource-source).
- `ESC z` and the broader status helpers have external panel/service consumer
  names that remain hardware/status-domain unknowns. The ROM-local writes are
  documented in [errors-and-status.md](errors-and-status.md#owner-summary).
- Model/status backchannel output after FIFO helper `0xb090` reaches a
  hardware/backend selector rooted at `0x780e40`. This is a host-interface
  boundary, not a page-object or render-engine boundary.

## Printable Bytes And Direct C0 Controls

This cluster covers the normal mode-zero parser rows that either create the
first ordinary text page objects or mutate immediately adjacent text state.
It starts when parser loop `0x11774` admits a normal host byte with
alternate/data flag `0x782c18` clear, and it ends at compact text objects,
span/publication effects, delayed cursor/context state, or explicit
no-output parser rows.

### Audited Rows

- Plain printable bytes:
  normal mode-zero no-match dispatch sends bytes `>= 0x20` to `0xd04a`.
  `0xd04a` normalizes the admitted value, builds printable source scratch
  through `0x1393a`, consumes selected text context, cursor
  `0x782c8a` / `0x782c8e`, HMI `0x78315c`, and previous-width latches, then
  selects unflagged `0xd140 -> 0xd3b2` or flagged
  `0xd550 -> 0xd824`. The compact object writer is
  `0x12f2e -> 0x1387c` under current page-root bucket `+0x1c`; publication
  and pixels then flow through `0xff1e`, `0x1ed84 -> 0x1edc6`,
  `0x1ef6a`, compact dispatcher `0x1efc2 -> 0x1effe`, and the selected
  row-store helper. Owner evidence is
  [direct-control-codes.md](direct-control-codes.md#printable-byte-to-compact-object),
  [Printable Source Outcome
  Matrix](direct-control-codes.md#printable-source-outcome-matrix),
  [page-record-storage.md](page-record-storage.md#page-object-storage-outcome-matrix),
  and `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`.

- CR and LF:
  normal C0 rows dispatch CR `0x0d` to `0xf02c` and LF `0x0a` to `0xf08c`.
  CR copies left margin `0x782dd6` into horizontal cursor `0x782c8a`
  through helper `0xf06e`, flushes pending spans through `0xf34a`, and can
  apply LF movement when line-termination byte `0x78318f.7` is set. LF can
  apply CR-style reset when `0x78318f.6` is set, then advances vertical
  cursor `0x782c8e` by VMI `0x783160` through helper `0xf0b2`. Neither row
  queues compact glyph bytes by itself; the visible consumers are pending
  span flush `0x12714 -> 0x126e2`, later printable `0xd04a`, VFC placement,
  raster or rectangle placement, or page-boundary publication after overflow.
  Owner evidence is
  [Direct-Control Output Decision
  Checkpoint](direct-control-codes.md#direct-control-output-decision-checkpoint),
  [Line-Termination Route
  Checkpoint](direct-control-codes.md#line-termination-route-checkpoint), and
  `generated/disasm/ic30_ic13_control_code_handlers_00f02c.lst`.

- FF:
  normal C0 row `0x0c` dispatches `0xf0f0`. FF optionally applies
  CR-style reset from `0x78318f.5`, flushes pending spans, marks page-eject
  state in `0x782a6d`, and reaches page-eject helper
  `0xf124 -> 0xff1e` when a current page root exists. Its first page-image
  effect is publication of already queued page objects, not a new printable
  object. Publication consumers are documented by the page-record and render
  owners after `0xff1e`. Owner evidence is
  [direct-control-codes.md](direct-control-codes.md#line-termination-route-checkpoint),
  [publication-commands.md](publication-commands.md#owner-summary), and
  `generated/disasm/ic30_ic13_control_code_handlers_00f02c.lst`.

- HT and BS:
  normal C0 rows dispatch HT `0x09` to `0xf1cc` and BS `0x08` to `0xf2a8`.
  HT reads HMI `0x78315c`, left margin `0x782dd6`, right margin
  `0x782dda`, and page width `0x782db8` to commit the next eight-column tab
  x into `0x782c8a`. BS ensures a root through `0x10084`, subtracts HMI or
  previous-width state from `0x782a58` / `0x782a5a` / `0x782a5c`, clamps at
  left margin, and refreshes span metrics. Both rows are delayed-output
  cursor writers; the next printable byte consumes the committed x through
  `0xd04a`, or a later span flush can materialize segment-list output.
  Owner evidence is
  [Previous-Width Backspace
  Checkpoint](direct-control-codes.md#previous-width-backspace-checkpoint),
  [Readers And Consumers](direct-control-codes.md#readers-and-consumers), and
  `generated/disasm/ic30_ic13_control_code_handlers_00f02c.lst`.

- SO and SI:
  normal C0 rows dispatch SO `0x0e` to `0xc6b8` and SI `0x0f` to
  `0xc68a`. Both call selected-context installer `0xc428(slot)`, update
  selected text slot `0x782f06`, and can install page-root context slot state
  through `0xc4fc`. They create no page object directly; the next printable
  byte consumes the selected primary or secondary context through
  `0xd04a -> 0x1393a` and queues compact objects under the matching page-root
  context. Owner evidence is
  [Selected Context Switch
  Checkpoint](direct-control-codes.md#selected-context-switch-checkpoint),
  [font-context-metrics.md](font-context-metrics.md#owner-summary), and
  fixtures `live primary current-font RAM install feeds SI page-record rows`
  and `live secondary current-font RAM install feeds SO page-record rows`.

- Explicit no-output C0 rows:
  normal table rows `0x00`, `0x07`, and `0x0b` are zero-handler rows. They
  reach the parser terminal reset path through `0x12218` without calling
  `0xd04a`, a direct-control handler, page-root creation, publication, or a
  render helper. Owner evidence is
  [pcl-parser-core.md](pcl-parser-core.md#parser-core-outcome-matrix) and the
  dispatch audit in [pcl-command-map.md](pcl-command-map.md#table-coverage-note).

### Field Classification

- Canonical parser state:
  mode byte `0x782999`, alternate/data flag `0x782c18`, admitted printable
  byte, and direct C0 table rows that select `0xf02c`, `0xf08c`, `0xf0f0`,
  `0xf1cc`, `0xf2a8`, `0xc6b8`, or `0xc68a`.
- Canonical text/page state:
  current page root `0x78297a`, compact bucket root `+0x1c`, selected context
  slot `0x782f06`, page-root context slot `0x78297e`, live context flags
  `0x78297f..`, horizontal and vertical cursors `0x782c8a` / `0x782c8e`,
  margins `0x782dd6` / `0x782dda`, HMI `0x78315c`, VMI `0x783160`, and
  line-termination byte `0x78318f`.
- Derived/cache state:
  printable source scratch `0x782d7e`, compact bucket/key fields
  `0x782a7a..0x782a7e`, previous-width latches `0x782a58..0x782a5c`,
  pending span watermarks `0x783184..0x78318a`, and render-band products
  after publication.
- Firmware bookkeeping:
  pending byte/page-eject state `0x782a6d`, page-root retry flag
  `root+0x15.0`, allocator state `0x782a70`, `0x782a72`, and `0x782a76`,
  span flush `0xf34a -> 0x12714 -> 0x126e2`, and selected-context installer
  `0xc428 -> 0xc4fc`.
- Hardware/external state:
  none for the ROM-local parser-to-page-object edge. Physical paper movement
  after FF publication and formatter/DC timing are outside this audit row set.
- Unknown:
  no ROM-local handler, consumer, page-object, or render-entry middle edge is
  unknown for the audited printable/direct C0 rows.

### Output And Boundary Result

This cluster now has a checked-in route from supported host bytes to ordinary
compact text objects, direct cursor/context/page-publication side effects, or
explicit no-output parser reset. The first pixel-producing route is the
ordinary compact path after `0xd04a`; CR/LF/HT/BS/SO/SI become visible only
when later printable, span, raster, rectangle, VFC, overflow, or publication
consumers read their state; FF publishes existing page objects through
`0xff1e`.

No ROM-local unresolved middle edge remains for these audited rows. Remaining
work in this area belongs to broader cursor/layout command families that use
parameterized ESC handlers, or to byte streams that change compact selector
shape, selected context, span object bytes, page-publication fields, or render
inputs.

## Cursor, Motion, Margin, And Span Commands

This cluster covers parameterized placement and text-state commands whose
first semantic effect is delayed state, plus the span path that can turn that
state into a segment-list page object. It starts after parser dispatch has
selected a normal table handler for `ESC &k`, `ESC &s`, `ESC &a`, `ESC *p`,
`ESC 9`, `ESC =`, `ESC &f#S`, or `ESC &d`, and it ends when later printable,
span, raster, rectangle, VFC, or publication paths consume the updated state.
Page-environment commands that own paper size, page length, copies, VFC table
payloads, or page-root publication remain in the publication/VFC audit cluster.

### Audited Rows

- `ESC &k#G`, line termination mode:
  parser dispatch reaches handler `0xedf8`, which rewinds command record
  cursor `0x78299e`, reads record word `+2`, normalizes negative selectors to
  absolute values, and writes canonical mode byte `0x78318f`. Selector `0`
  writes `0x00`, selector `1` writes `0x80`, selector `2` writes `0x60`, and
  selector `3` writes `0xe0`. CR `0xf02c` consumes bit `7`, LF `0xf08c`
  consumes bit `6`, and FF `0xf0f0` consumes bit `5`; the visible result is
  either a later compact coordinate after `0xd04a`, pending-span publication,
  or page-root publication through `0xf124 -> 0xff1e`. Owner evidence is
  [Line-Termination Route
  Checkpoint](direct-control-codes.md#line-termination-route-checkpoint),
  [Direct-Control Outcome
  Matrix](direct-control-codes.md#direct-control-outcome-matrix), and
  `generated/disasm/ic30_ic13_control_code_handlers_00f02c.lst`.

- `ESC &k#H`, HMI:
  parser dispatch reaches handler `0xca8c`. It consumes the six-byte
  `ESC &k#H/h` record at `0x78299e`, reads integer word `+2` and fractional
  word `+4`, rejects integer values above `0x348`, scales the accepted value,
  and stores packed HMI in `0x78315c`. The command queues no page object.
  First consumers are printable placement `0xd04a`, HT `0xf1cc`, BS
  `0xf2a8`, margin writers `0xeb58` / `0xec0c`, and cursor-position handler
  `0xf39e`; raster and rectangle can observe the change only after one of
  those consumers has committed cursor or margin fields. Owner evidence is
  [HMI Route Checkpoint](direct-control-codes.md#hmi-route-checkpoint) and
  `generated/disasm/ic30_ic13_hmi_vmi_handlers_00ca8c.lst`.

- `ESC &s#C`, wrap mode:
  parser dispatch reaches handler `0xedb0`. It reads record word `+2`,
  writes wrap byte `0x783190 = 1` for selector `0`, clears `0x783190` for
  selector `1`, and leaves the byte unchanged for other selectors. Unflagged
  precheck `0xd28a` and flagged precheck `0xd6bc` consume that byte before
  compact object queueing; wrap clear rejects horizontal overflow, while wrap
  set calls recovery helper `0xf054` and can allow the same printable source
  to continue into `0x12f2e -> 0x1387c`. Owner evidence is
  [Wrap Mode Route Checkpoint](direct-control-codes.md#wrap-mode-route-checkpoint),
  `generated/disasm/ic30_ic13_wrap_mode_handler_00edb0.lst`, and
  `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`.

- `ESC 9` and `ESC &a#L/#M`, margin reset and margin writers:
  direct `ESC 9` reaches `0xe9ba`, clears left margin `0x782dd6`, copies page
  width `0x782db8` to right margin `0x782dda`, and clears fraction companion
  `0x782ddc`. `ESC &a#L` reaches `0xeb58`, converts the absolute column count
  through HMI `0x78315c`, and writes accepted left margin `0x782dd6`.
  `ESC &a#M` reaches `0xec0c`, converts `abs(parameter) + 1` columns through
  HMI, writes right margin `0x782dda`, and may set right-limit latch
  `0x782a57` or move current x `0x782c8a`. Visible consumers are CR helper
  `0xf06e`, HT/BS, printable prechecks, following printable `0xd04a`, and
  pending span flush `0xf34a -> 0x12714 -> 0x126e2`. Owner evidence is
  [Margin Route Checkpoint](direct-control-codes.md#margin-route-checkpoint),
  [Span Flush Producers](direct-control-codes.md#span-flush-producers), and
  `generated/disasm/ic30_ic13_control_code_handlers_00f02c.lst`.

- `ESC =`, half-line feed:
  parser dispatch reaches handler `0xf176`. The handler ensures current page
  root `0x78297a` through `0x10084`, flushes pending spans through `0xf34a`,
  converts VMI `0x783160` through `0x104fe`, halves it, converts the half-step
  through `0x104d8`, adds it to vertical cursor `0x782c8e` through
  `0x10518`, runs overflow/perforation helper `0xf36c`, and clears
  `0x782a6d`. It creates no object directly; following printable, raster,
  rectangle, VFC, or publication paths consume the shifted y. Owner evidence is
  [Half-Line Feed Route
  Checkpoint](direct-control-codes.md#half-line-feed-route-checkpoint) and
  `generated/disasm/ic30_ic13_control_code_handlers_00f02c.lst`.

- `ESC &a#C/#H/#R/#V` and `ESC *p#X/#Y`, cursor and dot positioning:
  horizontal column `0xf39e`, horizontal decipoint `0xf416`, and horizontal
  dot `0xf48c` commit through helper `0xf4ca` into horizontal cursor
  `0x782c8a`. Vertical row `0xf560`, vertical decipoint `0xf60a`, and
  vertical dot `0xf692` commit through helper `0xf6e2` into vertical cursor
  `0x782c8e`. Parser record bit `0` is the relative flag for these handlers.
  `0xf4ca` clamps against page width `0x782db8` and right margin
  `0x782dda`; `0xf6e2` ensures a root, flushes pending spans, adds absolute
  positions to top offset `0x782dce` or relative positions to current y,
  clamps against vertical bounds, and can materialize span output. First
  visible consumers are following printable `0xd04a`, raster start `0x1075a`,
  rectangle clipper `0x10b80`, VFC jumps, or publication. Owner evidence is
  [Cursor And Dot Position Route
  Checkpoint](direct-control-codes.md#cursor-and-dot-position-route-checkpoint)
  and `generated/disasm/ic30_ic13_dot_position_handlers_00f48c.lst`.

- `ESC &f#S`, cursor stack:
  parser mode `17` dispatches `S/s` to `0xf75e` in the normal table.
  Selector `0` pushes cursor words into stack storage `0x782c96..0x782d36`;
  selector `1` pops, subtracts vertical offset source `0x782dbe`, clamps the
  restored x/y against current extents, clears latches, and can flush pending
  spans. Other selectors, full-stack pushes, and empty-stack pops return
  without page output. Alternate/data table rows suppress the stack mutation
  until replay: uppercase `S` is blank and lowercase `s` only rewinds through
  `0x11f4c`. First visible consumers are following printable `0xd04a`, raster
  start `0x1075a`, or rectangle clipper `0x10b80`. Owner evidence is
  [Cursor Stack State
  Checkpoint](direct-control-codes.md#cursor-stack-state-checkpoint) and
  `generated/disasm/ic30_ic13_dot_position_handlers_00f48c.lst`.

- `ESC &d#D` and `ESC &d@`, underline/span state:
  parser dispatch reaches handler `0x12622`, which writes underline/text
  attribute selector `0x783185` for accepted terminal forms and arms pending
  span state through `0x126e2`. Printable consumers `0xd4ac` and `0xd8fc`
  update pending span fields `0x783184..0x78318a`; terminal `&d@`, CR, margin
  changes, or vertical cursor changes can flush the pending span through
  `0xf34a -> 0x12714 -> 0x126e2`. The page effect is a selector-`0x4000`
  segment-list object under page-root `+0x1c`, later bridged and rendered by
  the segment-list renderer. Owner evidence is
  [Span Flush Producers](direct-control-codes.md#span-flush-producers),
  [Underline And Span Outcome
  Matrix](direct-control-codes.md#underline-and-span-outcome-matrix), and
  `generated/disasm/ic30_ic13_text_span_flush_012714.lst`.

### Field Classification

- Canonical parser state:
  mode byte `0x782999`, active six-byte command record at `0x78299e`,
  command-family lowercase chaining state, parsed integer/fraction words,
  final byte, and record bit `0` for relative cursor positioning.
- Canonical placement and text state:
  horizontal cursor `0x782c8a`, vertical cursor `0x782c8e`, margins
  `0x782dd6` / `0x782dda`, page width `0x782db8`, top offset `0x782dce`,
  vertical bounds `0x782dc6` / `0x782dca`, HMI `0x78315c`, VMI `0x783160`,
  line-termination byte `0x78318f`, wrap byte `0x783190`, current page root
  `0x78297a`, and selected text context used by following printable output.
- Canonical span/stack state:
  cursor-stack storage `0x782c96..0x782d36`, cursor-stack pointer
  `0x782d36`, pending span fields `0x783184..0x78318a`, and underline/span
  selector byte `0x783185`.
- Derived/cache state:
  converted packed coordinates from helpers `0x104d8`, `0x104fe`, and
  `0x10518`, tab-stop and margin candidates, compact coordinates produced
  after `0xd04a`, segment-list span object bytes after `0x12714`, and
  render-band products after publication.
- Firmware bookkeeping:
  right-limit latch `0x782a57`, previous-width latches `0x782a58..0x782a5c`,
  pending text/cursor latch `0x782a6d`, span flush helper `0xf34a`, page-root
  ensure helper `0x10084`, and lowercase command-record rewind helper
  `0x11f4c` for alternate/data stored command forms.
- Hardware/external state:
  none for these ROM-local parser-to-state and state-to-page-object edges.
  Physical paper motion after later publication remains external.
- Unknown:
  manual-facing HP names for latches `0x782a57`, `0x782a58..0x782a5c`,
  `0x782a6d`, and `0x783185` remain unknown; their ROM-local writers and
  consumers are documented by the cited handlers.

### Output And Boundary Result

This cluster has no direct raster row-store endpoint at handler entry. Its
ROM-local contract is delayed state: the handlers write cursor, margin, HMI,
wrap, line-termination, stack, or span fields; following printable, span,
raster, rectangle, VFC, overflow, or publication paths consume those fields.
The one page object created inside this cluster is the pending-span
segment-list route through `0x12714 -> 0x126e2`; text pixels otherwise enter
through the already audited compact path after `0xd04a`.

No ROM-local middle edge remains for the documented cursor/motion/margin/span
rows. Remaining work starts only when a byte stream changes page-environment
fields, VFC tables/channels, raster transfer objects, rectangle/rule objects,
font/downloaded-glyph selection, macro replay, parser-only behavior, or final
page/render crosswalk evidence.

## Page Environment, Publication, And VFC

This cluster covers supported `ESC &l` page-environment rows, reset/FF
publication, VFC table payloads, and VFC channel jumps. It starts at parser
dispatch or delayed restore for the relevant command family and ends at one of
four outcomes: delayed page/layout state, current-root publication through
`0xff1e`, VFC table installation, or VFC cursor/page movement consumed by
later printable and render paths.

### Audited Rows

- Reset `ESC E` and FF:
  reset handler `0xcc52` remains active even in alternate/data table
  selection. For active current roots it flushes pending span/text state
  through `0xf34a`, calls publication helper `0xff1e`, then rebuilds the
  default environment. Missing-root reset reaches the documented no-root
  `0xff1e` exit without producing a published page. FF handler `0xf0f0`
  optionally applies CR-style reset from `0x78318f.5`, flushes spans, ensures
  root `0x78297a`, reaches page-eject helper `0xf124 -> 0xff1e`, and writes
  pending page-eject latch `0x782a6d = 0xff`. Owner evidence is
  [Publication State To Visible Consumer
  Map](publication-commands.md#publication-state-to-visible-consumer-map),
  [Publication Helper At
  0xff1e](publication-commands.md#publication-helper-at-0xff1e), and
  `generated/disasm/ic30_ic13_esc_e_reset_00cc52.lst`.

- `ESC &l#A`, `ESC &l#O`, and `ESC &l#H`, page size, orientation, and paper
  source:
  page-size handler `0xfc74`, orientation handler `0x10220`, and paper-source
  handler `0xef62` all publish any active current root before their new
  environment belongs to later bytes. Page size and orientation call
  `0xf34a -> 0xff1e` before rebuilding geometry, margins, VMI/HMI, VFC, and
  font-context state. Paper source calls `0xf34a -> 0xff1e`, writes
  paper-source byte `0x782da6`, sets pending header byte `0x782998`, and can
  mirror or signal `0x780e8f` / `0x780e26`. First render consumers after
  publication are scheduler pool `0x780ea6 -> 0x780eaa -> 0x780eae`, bridge
  `0x1ed84 -> 0x1edc6`, and render dispatch `0x1ef6a`. Owner evidence is
  [Page Environment Outcome
  Matrix](publication-commands.md#page-environment-outcome-matrix),
  [Shared Geometry Refresh Consumer
  Checkpoint](publication-commands.md#shared-geometry-refresh-consumer-checkpoint),
  and [Paper Source Selector
  Matrix](publication-commands.md#paper-source-selector-matrix).

- `ESC &l#P`, page length:
  handler `0xf9e8` rewinds the six-byte command record, takes the absolute
  parameter, and has two audited outcomes. Accepted nonzero values convert
  line count through VMI `0x783160`, write page extent `0x782dba`, set pending
  header byte `0x782997`, refresh geometry/VFC fields, and create no immediate
  page object; following printable, raster, rectangle, VFC, or publication
  paths consume the new extent. Zero/default can first flush and publish the
  active root through `0xf34a -> 0xff1e`, then restore default page state.
  Owner evidence is [Page-Length Nonzero Placement
  Checkpoint](publication-commands.md#page-length-nonzero-placement-checkpoint),
  [Page Length Handler
  Details](publication-commands.md#page-length-handler-details), and
  `generated/disasm/ic30_ic13_page_length_handler_00f9e8.lst`.

- `ESC &l#X`, copies:
  copies handler `0xeef0` rewinds the command record, accepts absolute
  nonzero counts, clamps them to `1..99`, and writes copy count
  `0x782da4`. It does not call `0xff1e` and creates no page object at handler
  time. The first publication consumer is a later FF, reset, page-size,
  orientation, paper-source, VFC page eject, or no-room path; `0xff1e` then
  copies `0x782da4` into published pool-header word `+0x0c`. Owner evidence is
  [Copy-Count Delayed Header
  Checkpoint](publication-commands.md#copy-count-delayed-header-checkpoint)
  and `generated/disasm/ic30_ic13_copies_handler_00eef0.lst`.

- `ESC &l#C/#D/#E/#F/#L`, vertical layout and perforation state:
  VMI handler `0xcb00`, LPI handler `0xc992`, top-margin handler `0xece2`,
  text-length handler `0xea9e`, and perforation-skip handler `0xee64` write
  delayed layout state rather than page objects. Canonical fields include VMI
  `0x783160`, top offset `0x782dce`, text-bottom cache `0x782dd2`, VFC limit
  `0x782dc2`, last-line caches `0x782ede..0x782ee0`, and perforation byte
  `0x783191`. Consumers are LF/FF, overflow helper `0xf36c`, VFC channel
  handler `0x1280a`, printable placement, raster/rectangle placement, and
  later publication. Owner evidence is
  [Layout State To Output
  Checkpoint](direct-control-codes.md#layout-state-to-output-checkpoint),
  [vertical-forms-control.md](vertical-forms-control.md#owner-summary), and
  `generated/disasm/ic30_ic13_hmi_vmi_handlers_00ca8c.lst`.

- `ESC &l#W/#w`, VFC table payload:
  parser final `0x11f6e` schedules delayed handler `0x12cfe` through
  `0x121cc`; normal restore `0x12218 -> 0x12cfe` loads VFC table words
  `0x782dde..0x782edd`, derives bottom caches `0x782dc2` / `0x782dd2`, and
  clears modified-layout flag `0x782ee1`. Count zero or layout refresh can
  build the default table through `0x12b96`. In alternate/data mode, restore
  diverts through `0x12358(0x1228a)`; because saved handler `0x12cfe` is not
  wrapper `0x1228a`, positive payload bytes drain through `0xdace` and append
  through `0xe002` instead of writing VFC state. Owner evidence is
  [VFC State To Visible Consumer
  Map](vertical-forms-control.md#vfc-state-to-visible-consumer-map) and
  `generated/disasm/ic30_ic13_vertical_forms_control_01280a.lst`.

- `ESC &l#V`, VFC channel jump:
  handler `0x1280a` consumes selector, VMI `0x783160`, top offset
  `0x782dce`, current cursor `0x782c8e`, left margin `0x782dd6`, line-bound
  caches, and VFC table words. Non-publishing paths reset x through
  `0xf06e`, flush spans through `0xf34a`, write cursor state, and leave the
  following printable to queue under the current root. Publishing branches
  call `0xf124 -> 0xff1e`, so pre-VFC page objects remain on the old published
  root while post-VFC printable bytes allocate or queue on a fresh root. Owner
  evidence is [vertical-forms-control.md](vertical-forms-control.md#owner-summary)
  and [VFC State To Visible Consumer
  Map](vertical-forms-control.md#vfc-state-to-visible-consumer-map).

### Field Classification

- Canonical parser/delayed state:
  six-byte command record `0x78299e`, delayed flag `0x782a1a`, saved handler
  pointer `0x782a1c`, saved delayed record `0x782a20..0x782a25`, and
  alternate/data flag `0x782c18`.
- Canonical page/image state:
  current root `0x78297a`, root state byte `+0x04`, current-root bucket/list
  fields `+0x1c/+0x24/+0x28`, context slots `+0x2c..+0x68`, published pool
  head `0x780ea6`, scheduler cursors `0x780eaa` / `0x780eae`, and
  publication flag `0x782996`.
- Canonical page-control/environment state:
  copy count `0x782da4`, paper-source byte `0x782da6`, orientation byte
  `0x782da3`, pending header bytes `0x782997` / `0x782998`, status byte
  `0x780e99`, paper-source mirrors `0x780e8f` / `0x780e26`, page length
  `0x782dba`, top offset `0x782dce`, text-bottom cache `0x782dd2`,
  perforation byte `0x783191`, and VMI/HMI fields `0x783160` / `0x78315c`.
- Canonical VFC state:
  table words `0x782dde..0x782edd`, VFC limit `0x782dc2`, last-line caches
  `0x782ede`, `0x782edf`, and `0x782ee0`, modified-layout flag
  `0x782ee1`, and selector mask `1 << (n - 1)` used by `0x1280a`.
- Derived/cache state:
  refreshed page geometry, VFC line-count caches, render-record roots copied
  by `0x1ed84` / `0x1edc6`, and band caches produced after scheduler/render
  selection.
- Firmware bookkeeping:
  allocator cursors `0x782a70`, `0x782a72`, and `0x782a76`, pending byte
  `0x782a6d`, root retry/overlay state `0x782a92` / `0x782a94`, delayed
  alternate/data redirect `0x12358`, append sink `0xe002`, service wait
  helper `0x9ac2`, and macro overlay frame helpers `0xe0a4` / `0xe4f4`.
- Hardware/external state:
  physical engine consumption after rendered band buffers and board-facing
  service/status timing. These are outside the ROM-local publication/VFC
  parser-to-render-entry route.
- Unknown:
  manual-facing names for VFC line caches `0x782ede`, `0x782edf`, and
  `0x782ee0`, plus physical paper movement after publication. Their ROM-local
  writer and consumer roles are documented by the cited handlers.

### Output And Boundary Result

Publication creates no pixels by itself. It snapshots the current page/image
object graph and header state so scheduler and render code can later select
the page/control record. VFC commands also draw nothing at handler entry: they
install table state, move cursor state, or split pages through `0xff1e`.
Pixel generation begins only after earlier page objects or later printable,
raster, rectangle, fixed-list, or span objects pass through the published
record and render path.

No ROM-local parser-to-publication, VFC-table, VFC-channel, or
publication-to-render-entry middle edge remains for the documented reset, FF,
page-size, page-length, orientation, paper-source, copies-through-FF,
vertical-layout, VFC table-definition, and VFC channel-jump rows. Remaining
work in this audit ledger starts from raster transfer objects,
rectangle/rule objects, font/downloaded-glyph selection, macro replay,
parser-only behavior, or final page/render crosswalk evidence.

## Raster Transfer And Encoded Rows

This cluster covers the supported `ESC *t`, `ESC *r`, and `ESC *b#W` raster
family from parser dispatch through encoded raster objects and render helper
selection. It starts at normal table handlers for raster setup or delayed
restore for the transfer payload and ends at raster state mutation,
append-only alternate/data storage, drained payload bytes, encoded objects
under page-root `+0x1c`, or encoded-raster row-store helpers after
publication.

### Audited Rows

- `ESC *t#R`, raster resolution:
  parser dispatch reaches handler `0x10808`. When raster active byte
  `0x783182` is clear, the handler rewinds command record cursor
  `0x78299e`, reads the absolute parameter, maps thresholds to scale
  `+0x0e` and encoded mode `+0x08`, and recomputes row byte limit `+0x10`
  from page extent and baseline. Requests above `150` store scale `1` and
  mode `0`; `101..150` stores scale `2` and mode `1`; `76..100` stores scale
  `3` and mode `2`; `<= 75` stores scale `4` and mode `3`. If raster is
  already active, `0x10808` exits without rewriting mode, scale, or limit.
  First visible consumer is later transfer `0x105d0`. Owner evidence is
  [raster-graphics.md](raster-graphics.md#resolution-at-0x10808) and
  [Raster Transfer Decision
  Checkpoint](raster-graphics.md#raster-transfer-decision-checkpoint).

- `ESC *r#A/#B`, start and end raster:
  start handler `0x1075a` rewinds the parsed record, reads the absolute
  parameter, and initializes raster state only when active byte `+0x12` is
  clear. It sets active byte `0x783182`, seeds origin `+0x0a` from the active
  cursor axis for selector `1` or from the left edge otherwise, copies baseline
  `+0x00`, and recomputes row byte limit `+0x10`. End handler `0x107fa`
  clears only active byte `0x783182`; it leaves mode, scale, origin,
  baseline, row, and limit fields unchanged until later start/resolution/reset
  paths rewrite them. Owner evidence is
  [Start And End Raster](raster-graphics.md#start-and-end-raster) and
  `generated/disasm/ic30_ic13_raster_handlers_0105d0.lst`.

- `ESC *b#W/#w`, delayed transfer setup:
  parser mode `14` has `W/w` transfer rows that call setup handler `0x11f82`.
  `0x11f82` schedules delayed handler `0x105d0` through `0x121cc`, storing
  pending byte `0x782a1a`, saved handler `0x782a1c = 0x105d0`, and saved
  six-byte command record `0x782a20..0x782a25`. Normal restore `0x12218`
  copies the record back to `0x78299e`, advances the cursor, and calls
  `0x105d0`; payload bytes are not consumed at parser-table dispatch time.
  Owner evidence is [Parser Boundary](raster-graphics.md#parser-boundary),
  [Transfer Gate At 0x105d0](raster-graphics.md#transfer-gate-at-0x105d0),
  and `generated/disasm/ic30_ic13_payload_dispatch_011f82.lst`.

- Alternate/data raster rows:
  with alternate/data flag `0x782c18` set, `ESC *t#R`, `ESC *r#A`, and
  `ESC *r#B` do not reach `0x10808`, `0x1075a`, or `0x107fa`; uppercase
  terminal rows are blank and lowercase finals route only to rewind helper
  `0x11f4c`. `ESC *b#W/w` still schedules delayed setup, but restore
  `0x12218` diverts through `0x12358(0x1228a)`. Because saved handler
  `0x105d0` is not wrapper `0x1228a`, positive payload bytes drain through
  `0xdace` and append through `0xe002`. No raster block field, page root,
  encoded object, bridge field, or renderer input changes until replay.
  Owner evidence is [Alternate/Data Raster Payload
  Checkpoint](raster-graphics.md#alternatedata-raster-payload-checkpoint).

- Transfer gate `0x105d0`:
  the restored transfer handler flushes pending spans, rewinds the restored
  command record, reads absolute byte count, sets raster active byte `+0x12`,
  and derives the orientation-specific row coordinate. Beyond-extent
  transfers drain payload through `0xdace` and return before current-root
  allocation. Negative-row transfers ensure a root and update row state but
  skip `0x13070`, draining payload instead of queueing an object. In-range
  transfers store accepted count `+0x04` and overflow/drain count `+0x06`;
  if the raw count exceeds row byte limit `+0x10`, the accepted bytes can
  become object payload and the overflow drains later. Owner evidence is
  [Transfer Gate Outcome
  Matrix](raster-graphics.md#transfer-gate-outcome-matrix) and
  `generated/disasm/ic30_ic13_raster_handlers_0105d0.lst`.

- Encoded object creation:
  accepted nonnegative rows call `0x13070`. `0x13070` computes bucket index
  `0x782a7c` and packed key `0x782a7e`; `0x13250` links one or more high-bit
  class objects under current page-root bucket `+0x1c`; and `0x138de` copies
  accepted payload bytes into object `+0x0a..`. Object byte `+0x04 = 0x80`
  selects encoded-raster dispatch, byte `+0x05` carries mode bits, word
  `+0x06` records payload capacity/count, and word `+0x08` carries the packed
  destination key. Dense rows can split into multiple objects before
  publication. Owner evidence is
  [Encoded Raster Object Outcome
  Matrix](raster-graphics.md#encoded-raster-object-outcome-matrix),
  [page-record-storage.md](page-record-storage.md#page-object-storage-outcome-matrix),
  and `generated/disasm/ic30_ic13_raster_object_queue_013070.lst`.

- Encoded raster rendering:
  after publication `0xff1e`, bridge `0x1ed84 -> 0x1edc6` copies bucket root
  `+0x1c` into render root `+0x18`. Render dispatch
  `0x1ef6a -> 0x1efc2` routes high-bit objects to `0x1f88e`. `0x1f88e`
  parses object byte `+0x05 & 3`, count `+0x06`, key `+0x08`, and payload
  bytes. Mode `0` dispatches helper `0x1f8da` for literal rows; mode `1`
  dispatches `0x1f8e6` for two-row expansion; mode `2` dispatches
  `0x1f920` with shared loop `0x1f9a0` for three-row expansion and fallback
  split behavior; mode `3` dispatches `0x1f9c6` for four-row expansion.
  Owner evidence is [Render Dispatch](raster-graphics.md#render-dispatch),
  [Row-Store Primitive
  Map](page-raster-imaging.md#row-store-primitive-map), and
  `generated/disasm/ic30_ic13_bitmap_encoded_span_modes_01f88e.lst`.

### Field Classification

- Canonical parser/delayed state:
  command-record cursor `0x78299e`, delayed pending byte `0x782a1a`, saved
  handler `0x782a1c`, saved transfer record `0x782a20..0x782a25`, and
  alternate/data flag `0x782c18`.
- Canonical raster state:
  raster block `0x783170`, including baseline `+0x00`, current row `+0x02`,
  accepted count `+0x04`, overflow/drain count `+0x06`, encoded mode `+0x08`,
  origin `+0x0a`, scale `+0x0e`, row byte limit `+0x10`, and active byte
  `+0x12`.
- Canonical page/image state:
  current page root `0x78297a`, bucket root `+0x1c`, encoded object class
  byte `+0x04`, mode byte `+0x05`, count/capacity word `+0x06`, key word
  `+0x08`, and copied payload bytes `+0x0a..`.
- Derived/cache state:
  bucket index `0x782a7c`, packed key `0x782a7e`, allocation capacity
  `0x782a80`, render-record bucket root `+0x18`, active band caches, stride
  `0x783a1c`, and fallback storage rooted at `0x7810b4`.
- Firmware bookkeeping:
  allocator cursors `0x782a70`, `0x782a72`, and `0x782a76`, copy-stop flag
  `0x782996`, root retry flag `+0x15.0`, alternate/data redirect `0x12358`,
  append sink `0xe002`, and no-room publication/retry state.
- Hardware/external state:
  none inside this command-family edge after payload bytes have been admitted
  by `0xa904` / `0xdace`; physical engine consumption begins after shared
  render buffers are written.
- Unknown:
  no ROM-local middle edge remains for the audited setup, accepted row, drain,
  dense split, encoded object, bridge, or modes `0..3` render paths. No
  separate ROM parser row for `ESC *b#M` or another host-selected raster
  compression method is present in the supported table.

### Output And Boundary Result

Resolution and start/end commands are state-only until a later transfer uses
them. Accepted `ESC *b#W` rows create encoded raster objects under page-root
`+0x1c`; beyond-extent and negative-row transfers consume payload without
queueing encoded objects. Pixel generation begins after publication and bridge
when `0x1efc2` selects encoded raster renderer `0x1f88e` and its mode helper.

No ROM-local raster dispatch, object-layout, bridge, or row-store helper edge
remains unresolved for the documented raster cluster. Remaining work in this
audit ledger starts from rectangle/rule objects, font/downloaded-glyph
selection, macro replay, parser-only behavior, or final page/render crosswalk
evidence.

## Rectangle And Rule Imaging

This cluster covers the supported `ESC *c` rectangle/rule graphics family from
parser dispatch through rule-list page objects and solid/pattern rendering. It
starts at normal table handlers for rectangle size, area-fill, and fill
commands, and ends at delayed rectangle state, no-output selector/clip gates,
rule-list objects under page-root `+0x24`, no-room retry publication, or
rule-list row helpers after publication.

### Audited Rows

- `ESC *c#A/#B/#H/#V`, rectangle width and height:
  parser mode `16` dispatches dot width `A/a` to `0x10e68`, dot height `B/b`
  to `0x10e22`, decipoint width `H/h` to `0x10a40`, and decipoint height
  `V/v` to `0x10ae0`. These handlers rewind command record cursor
  `0x78299e`, consume parsed numeric words, and write canonical dimension
  fields `0x78316a` and `0x783166`. Dot handlers require positive explicit
  integer parameters; decipoint handlers convert accepted values through ROM
  subunit math before storing packed dimensions. They queue no page object;
  first visible consumer is fill handler `0x10898`. Owner evidence is
  [Size Commands](rectangle-graphics.md#size-commands) and
  [Rectangle State To Visible Consumer
  Map](rectangle-graphics.md#rectangle-state-to-visible-consumer-map).

- `ESC *c#G`, area-fill id:
  parser mode `16` dispatches `G/g` to `0x10dce`. The handler rewinds
  `0x78299e`, treats missing or zero explicit values as `0`, takes absolute
  value for negative explicit values, and writes area-fill id `0x78316e`.
  This is delayed command state consumed only by later `ESC *c#P` selector
  mapping. Owner evidence is
  [Command Handler Boundaries](rectangle-graphics.md#command-handler-boundaries)
  and [Rectangle Outcome Matrix](rectangle-graphics.md#rectangle-outcome-matrix).

- `ESC *c#P`, fill selector and no-output gates:
  parser mode `16` dispatches `P/p` to `0x10898`. The handler rewinds the
  command record, reads current width `0x78316a`, height `0x783166`, area-fill
  id `0x78316e`, orientation `0x782da3`, and selector parameter. Missing or
  zero selector maps to solid selector `7`; selector `2` maps percent-fill ids
  to selectors `0..7`; selector `3` maps pattern ids `1..6` to selectors
  `8..13`, with landscape remaps for ids `1..4`. Invalid selector/id
  combinations, zero dimensions, off-page starts, and empty-after-clip paths
  return before `0x13386`, so they create no rule object, publication state,
  bridge field, or render input. Owner evidence is
  [Fill Selector At 0x10898](rectangle-graphics.md#fill-selector-at-0x10898)
  and [Rectangle Outcome Matrix](rectangle-graphics.md#rectangle-outcome-matrix).

- Clip and queue at `0x10b80`:
  accepted fill selectors call `0x10b80`, which consumes current cursor
  `0x782c8a` / `0x782c8e`, orientation byte `0x782da3`, page extents
  `0x782db8` / `0x782db6`, and stored dimensions. It rejects starts to the
  right or below the page, rejects negative starts that do not cross onto the
  page, clips negative x/y and right/top/bottom edges, writes clipped source
  record `0x782a88`, ensures current root `0x78297a` through `0x10084`, and
  calls `0x13386` only for nonempty on-page rectangles. Owner evidence is
  [Clip And Queue At 0x10b80](rectangle-graphics.md#clip-and-queue-at-0x10b80)
  and `generated/disasm/ic30_ic13_rectangle_graphics_010898.lst`.

- Rule-list object creation and retry:
  `0x13386` derives bucket/key fields through `0x134d6` from source record
  `0x782a88`, then calls `0x133aa`. `0x133aa` allocates a 14-byte rule object
  through stream allocator `0x1381c`, inserts it under page-root rule list
  `+0x24` in ascending bucket order, and writes object byte `+0x04`, selector
  byte `+0x05`, packed key `+0x06`, width `+0x08`, height `+0x0a`, and
  continuation word `+0x0c`. If allocation fails, it returns zero without
  changing the rule-list head; caller `0x10d22..0x10d3e` sets retry bit
  `root+0x15.0`, publishes through `0xff1e`, ensures a fresh root, and retries
  the same clipped source record. Owner evidence is
  [Rule Storage And Bridge
  Route](rectangle-graphics.md#rule-storage-and-bridge-route) and
  [Rule-List Outcome Matrix](page-record-storage.md#rule-list-outcome-matrix).

- Alternate/data rectangle rows:
  with alternate/data table `0x116f6` active, uppercase `ESC *c`
  terminals `A/B/G/H/P/V` have no handler and lowercase `a/b/g/h/p/v` route
  only to rewind helper `0x11f4c`. Normal rectangle writers `0x10e68`,
  `0x10e22`, `0x10a40`, `0x10ae0`, `0x10dce`, and producer `0x10898` are not
  called. Width `0x78316a`, height `0x783166`, area-fill id `0x78316e`,
  clipped source `0x782a88`, root `+0x24`, publication state, and render
  inputs remain unchanged until replay through normal parser mode. Owner
  evidence is [Rectangle Outcome
  Matrix](rectangle-graphics.md#rectangle-outcome-matrix).

- Bridge and render:
  publication preserves page-root rule list `+0x24`; bridge `0x1edc6` copies
  that list to render-record list `+0x1c`, ORs selector byte `+0x05` with
  `0x10`, and copies object height `+0x0a` into continuation word `+0x0c`.
  Render entry `0x1ef6a` calls rule walker `0x1f446`; selector low nibble `7`
  dispatches to solid helper `0x1f596`, and selector nibbles `0..6` or
  `8..13` dispatch to pattern helper `0x1f4e0`. Both helpers consume packed
  key `+0x06`, width `+0x08`, continuation `+0x0c`, destination helper
  `0x1f626`, and, for patterned rules, mask helper `0x1f6ee` plus pattern
  table `0x2fefe`. Owner evidence is
  [Render Dispatch](rectangle-graphics.md#render-dispatch),
  [Rule Destination And Row
  Writes](rectangle-graphics.md#rule-destination-and-row-writes), and
  [Render Selector Dispatch
  Checkpoint](page-raster-imaging.md#render-selector-dispatch-checkpoint).

### Field Classification

- Canonical parser state:
  parser mode `16`, active six-byte command record at `0x78299e`, lowercase
  chaining state, parsed numeric parameters, and final byte.
- Canonical rectangle command state:
  width `0x78316a`, height `0x783166`, and area-fill id `0x78316e`.
- Canonical page/image state:
  current root `0x78297a`, clipped source record `0x782a88`, page-root
  rule-list head `+0x24`, 14-byte rule object fields, published source record,
  and render-record rule list `+0x1c`.
- Derived/cache state:
  bucket index and key fields `0x782a7c..0x782a7e`, horizontal phase
  `0x782dc0`, bridge selector bit `0x10`, continuation word `+0x0c`, render
  band fields, destination masks, and pattern-base selection.
- Firmware bookkeeping:
  stream allocator fields `0x782a70`, `0x782a72`, and `0x782a76`, no-room
  retry bit `root+0x15.0`, publication flag `0x782996`, pool cursors, and
  render scheduler progress.
- Hardware/external state:
  none for the ROM-local rectangle object and renderer contract after the same
  normalized host bytes and publication boundary exist.
- Unknown:
  no ROM-local middle edge remains for documented selector-7, gray, pattern,
  landscape-remap, clipping, no-room, bridge, solid, and pattern render paths.
  New work must change a named selector predicate, clipped source field,
  allocator outcome, rule object byte, retry field, bridge field, helper
  dispatch, continuation mutation, or row construction.

### Output And Boundary Result

Size and area-fill commands are delayed state until `ESC *c#P` consumes them.
A valid nonempty on-page fill queues a rule-list object under page-root
`+0x24`; invalid selectors, zero dimensions, off-page rectangles, and
alternate/data rows create no page object. Pixel generation starts only after
publication and bridge when `0x1ef6a` reaches rule walker `0x1f446` and then
solid helper `0x1f596` or pattern helper `0x1f4e0`.

No ROM-local rectangle/rule dispatch, object-layout, bridge, retry, or
row-store helper edge remains unresolved for the documented rectangle cluster.
Remaining work in this audit ledger starts from font/downloaded-glyph
selection, macro replay, parser-only behavior, or final page/render crosswalk
evidence.

## Font Selection And Downloaded Glyphs

This cluster covers delayed font selection, symbol/map state, downloaded-font
payloads, printable-byte consumption, compact text/downloaded-glyph page
objects, and compact render dispatch. It starts at supported parser rows for
font attributes, symbol/font designation, current downloaded font/character,
font control, and `W` payloads. It ends at delayed state with no immediate
page object, compact text/downloaded-glyph objects under page-root `+0x1c`,
span objects from metric consumers, selected-map/no-install boundaries, or
compact row helpers after publication.

### Audited Rows

- Font attribute and pitch request rows:
  parser terminal wrappers `0x12046`, `0x1206e`, `0x12082`, `0x12096`,
  `0x120aa`, and `0x1205a` call writers `0xc6ec`, `0xc780`, `0xc930`,
  `0xc89c`, `0xc840`, and `0xc7e0`. Compatibility pitch handler `0xc390`
  rewrites the active parser record and then calls `0xc89c -> 0xc580` for
  accepted `ESC &k#S/s` selectors. These rows write requested font fields and
  dirty flags `0x782f2c` / `0x782f2d`; they queue no page object until a later
  printable byte consumes the selected context. Owner evidence is
  [Font Request Outcome
  Matrix](font-context-metrics.md#font-request-outcome-matrix) and
  `generated/disasm/ic30_ic13_font_selection_update_handlers_00c6ec.lst`.

- Symbol-set, final-`@`, and final-`X` rows:
  normal `ESC (` and `ESC )` setup handlers `0x1201e -> 0x11f26` and
  `0x12008 -> 0x11efe` append primary or secondary slot records. Terminal
  wrapper `0x120be` calls `0x1be22 -> 0xc580`. Ordinary finals write
  requested symbol words `0x782ef4` / `0x782f04`; final `@` uses table
  `0x1bde2`; final `X` uses `0x1c066 -> 0x17708` to select a font-id
  candidate or preserve the previous context on documented miss paths. These
  commands are delayed map/context state, not page objects. Owner evidence is
  [Symbol/Font Designation Outcome
  Matrix](symbol-set-selection.md#symbolfont-designation-outcome-matrix).

- Shared refresh, context, and map route:
  common refresh `0xc580` consumes dirty flags, selected slot `0x782f06`,
  page-root live flags `0x78297f..0x78298e`, and transient context
  `0x782992`. Candidate and selected-map selection flows through
  `0x13eb8 -> 0x14398 -> 0x144d2 -> 0x14c64 -> 0x14f16 -> 0x1440c`, writing
  current contexts `0x782ee6` / `0x782ef6`, active maps
  `0x782f32` / `0x783032`, selected candidate `0x7828a8`, selected target
  `0x7828de`, active symbol words `0x783144` / `0x783146`, and snapshots
  `0x783148` / `0x783152`. Roman-8 map patcher `0x14f16` mutates maps only
  before later printable capture; it does not rewrite existing page objects.
  Owner evidence is
  [Font State To Visible Consumer
  Map](font-context-metrics.md#font-state-to-visible-consumer-map) and
  [Map Patch To Visible Consumer
  Map](symbol-map-patching.md#map-patch-to-visible-consumer-map).

- Page-root context install and SI/SO selection:
  `0xc580` and direct SI/SO handlers `0xc68a` / `0xc6b8` call `0xc428`, which
  calls `0xc4fc` to reuse or install the selected current-font context under
  page-root slots `+0x2c..+0x68` and write selected page-root slot
  `0x78297e`. A context install alone has no pixels; placement helpers later
  mark live byte `0x78297f + slot` when a printable byte is queued. Owner
  evidence is [Page-Root Context
  Install](font-context-metrics.md#page-root-context-install) and
  `generated/disasm/ic30_ic13_font_context_install_00c428.lst`.

- Printable byte to compact text object:
  printable entry `0xd04a` calls `0x1393a`, which reads selected slot
  `0x782f06`, current context `0x782ee6` or `0x782ef6`, and active map
  `0x782f32` or `0x783032`. It writes source record `0x782d7e`, including
  selected context/resource longword `+0x00`, glyph entry or fixed-record
  pointer `+0x04`, mapped glyph word/byte `+0x0a/+0x0b`, class flag `+0x10`,
  and page-root slot `+0x16`. Placement path `0xd140 -> 0xd3b2` or
  `0xd550 -> 0xd824` then calls `0x12f2e -> 0x1387c`, which queues compact
  text/downloaded-glyph objects under page-root bucket `+0x1c`. Owner evidence
  is [Byte-To-Glyph Flow](font-context-metrics.md#byte-to-glyph-flow) and
  [Printable Source Outcome
  Matrix](direct-control-codes.md#printable-source-outcome-matrix).

- Span metric side path:
  printable placement helpers `0xd4ac` and `0xd8fc` consume selected record
  metric fields behind source `+0x04`, including unflagged
  `+0x2b/+0x2c/+0x2d` and flagged `+0x16/+0x18/+0x1a`. They update pending
  span state `0x783184..0x78318a`; later flush
  `0xf34a -> 0x12714 -> 0x126e2` emits segment-list or fixed-list page
  objects. Owner evidence is
  [Span Metric Consumers](font-context-metrics.md#span-metric-consumers).

- Downloaded-font command state and payload rows:
  `ESC *c#D` reaches `0x15a56` and writes current downloaded font id
  `0x782f2e`; `ESC *c#E` reaches `0x15a18` and writes current character word
  `0x782f30`; `ESC *c#F` reaches `0x16df6` and then mark, unmark, or release
  helpers. `ESC )s#W` and `ESC (s#W` enter delayed arming handler `0x11f96`;
  restore `0x121cc -> 0x12218` calls `0x15d0a` for zero-count descriptor or
  current-record payloads and `0x16c14` for nonzero resource/header payloads.
  These paths install or preserve downloaded resource state, but draw only
  when later printable bytes select the installed glyph. Owner evidence is
  [Downloaded-Font Outcome
  Matrix](downloaded-fonts.md#downloaded-font-outcome-matrix) and
  `generated/disasm/ic30_ic13_font_control_dispatch_016df6.lst`.

- Downloaded-character bitmap and installed-resource use:
  descriptor path `0x15d0a` routes current-record and continuation payloads
  to `0x16498`, `0x16606`, `0x15b9a`, or `0x15c4c`; completed downloaded
  character bitmaps are copied by
  `0x16498 -> 0x16874 -> 0x168dc/0x16942`. Resource/header install
  `0x16c14 -> 0x16fae -> 0x17026 -> 0x1719c` validates staged fields, writes
  current records `0x782640..0x782776`, candidate counters, payload pointers,
  and selected-resource records. `0x17708`, `0x14c64`, and `0x14e24` make
  those installed glyphs visible to the same `0x1393a -> 0x12f2e` printable
  object path. Owner evidence is
  [Downloaded Font To Visible Consumer
  Map](downloaded-fonts.md#downloaded-font-to-visible-consumer-map).

- Compact text/downloaded-glyph rendering:
  publication `0xff1e -> 0x1ed84 -> 0x1edc6` copies compact bucket root
  `+0x1c` to render root `+0x18` and copies page-root context slots
  `+0x2c..+0x68` to render slots `+0x24..+0x60`. Render entry
  `0x1ef6a -> 0x1efc2 -> 0x1effe` loads the copied context slot into
  `0x783a2c`. Built-in/short compact output reaches `0x1f034 -> 0x1f354`;
  downloaded-glyph selector classes `0x0003`, `0x1003`, `0x2003`, and
  `0x3003` route to `0x1f034`, `0x1f0d2`, `0x1f1f0`, or `0x1f264`.
  Row bytes come from copied context/resource longwords, compact glyph bytes,
  installed glyph records, and row-copy helper tables. Owner evidence is
  [Compact Selector Outcome
  Matrix](downloaded-fonts.md#compact-selector-outcome-matrix) and
  [Render Entry Outcome
  Matrix](page-raster-imaging.md#render-entry-outcome-matrix).

- Alternate/data and no-install boundaries:
  alternate/data `ESC (s` and `ESC )s` ordinary attribute rows end at blank
  terminal rows or lowercase rewind helper `0x11f4c`, so they do not call
  font writers or `0xc580`. Alternate/data positive `W` restore routes
  through `0x12358 -> 0xdace -> 0xe002`, preserving bytes without descriptor
  validation, downloaded-character copy, selected-map refresh, page object, or
  render input until replay. Validation failures, no-slot exits, no-install
  exits, failed resumes, and final-`X` miss paths preserve following printable
  output on the prior/default context. Owner evidence is
  [Downloaded Font To Visible Consumer
  Map](downloaded-fonts.md#downloaded-font-to-visible-consumer-map) and
  [Font State To Visible Consumer
  Map](font-context-metrics.md#font-state-to-visible-consumer-map).

### Field Classification

- Canonical parser/request state:
  active command record `0x78299e`, synthetic pitch and symbol setup records,
  selected text slot `0x782f06`, requested font fields, requested symbol words
  `0x782ef4` / `0x782f04`, current downloaded font id `0x782f2e`, current
  character word `0x782f30`, and restored `W` command records.
- Canonical selected font state:
  current contexts `0x782ee6` / `0x782ef6`, context fields `+0x00`,
  `+0x04`, and `+0x05`, active maps `0x782f32` / `0x783032`, selected
  candidate `0x7828a8`, selected target `0x7828de`, active symbol words
  `0x783144` / `0x783146`, and selected-font snapshots
  `0x783148` / `0x783152`.
- Canonical downloaded-resource state:
  current records `0x782640..0x782776`, record counts
  `0x782782` / `0x782786`, record id `+0x00`, flags `+0x02`, payload pointer
  `+0x06`, candidate counters, candidate longword bits, glyph pointer tables,
  downloaded-character records, and bitmap payload bytes.
- Canonical page/image state:
  page-root context slots `+0x2c..+0x68`, selected page-root slot
  `0x78297e`, source record `0x782d7e`, compact objects under root `+0x1c`,
  span/fixed-list objects from `0x12714`, render root `+0x18`, render context
  slots `+0x24..+0x60`, and compact selector families
  `0x0003/0x1003/0x2003/0x3003`.
- Derived/cache state:
  rebuilt map bytes, Roman-8 patch bytes, selected-font snapshots, transient
  context `0x782992`, pending span bounds `0x783184..0x78318a`, compact
  coordinates and bucket keys, render work words, row-copy helper indexes,
  segment source offsets, and wide-mode caches.
- Parser scratch:
  delayed payload state `0x782a1a`, saved handler `0x782a1c`, saved records
  `0x782a20..0x782a25`, payload budget `0x783140`, staged descriptor/header
  bytes `0x7827de..0x7827e9`, staging pointer `0x782862`, optional symbol
  bytes `0x782842..0x782856`, bitmap parse fields
  `0x7827be/0x7827c2/0x7827c4`, and alternate/data append records that have
  not replayed through the normal parser route.
- Firmware bookkeeping:
  dirty flags `0x782f2c/0x782f2d`, page-root live flags
  `0x78297f..0x78298e`, full-root flag `0x78298f`, `0xc4fc` full-status
  return, candidate insertion helper `0x1bc38`, release helpers
  `0x1887a`, `0x18b92`, `0x18bf2`, `0x17a24`, and `0x17d7c`, continuation
  fields `0x7827c6..0x7827da`, publication flag `0x782996`, and render
  scheduler progress.
- Hardware/external state:
  none inside the ROM-local built-in or downloaded-glyph route after bytes
  reach these handlers. Optional cartridge/resource contents are external data
  for candidate records, not a different parser-to-render control path.
- Unknown:
  no ROM-local middle edge remains for the documented built-in, inline,
  installed downloaded-glyph, symbol, final-`@`, final-`X`, printable-source,
  span-metric, page-root context, publication, bridge, and compact selector
  routes. Exact residual stop points are the downloaded-font owner boundaries:
  manual labels for validation fields `0x16fae..0x17016`, invalid compact
  helper targets, segmented-wide source-offset limits, parser payload-count
  caps, and missing external resource bytes.

### Output And Boundary Result

Font selection, symbol designation, font-id selection, current downloaded
font/character, descriptor, install, control, release, and continuation
commands are delayed state. They change the context/map/resource data that a
later printable byte sees; they do not draw pixels directly.

The first page-image effect for the normal text path is `0xd04a -> 0x1393a`
followed by `0x12f2e -> 0x1387c`, which queues compact text or
downloaded-glyph objects under page-root `+0x1c`. Span metrics can create
additional segment-list or fixed-list objects only after the pending span
flush path reaches `0x12714`.

Pixel generation starts after publication and bridge when `0x1ef6a` dispatches
compact bucket objects through `0x1effe` and the selected compact helper.
Remaining audit-ledger work starts from macro replay, parser-only behavior, or
the final page/render owner crosswalk rather than from font/downloaded-glyph
dispatch.

## Macro Definition And Data-Chain Replay

This cluster covers the supported `ESC &f` macro family from parsed macro id
and selector rows through definition storage, execute/call replay, overlay
publication replay, data-chain byte-source equivalence, context refresh, and
ordinary page-object/render consumers. It starts at parser dispatch for
`ESC &f#Y` and `ESC &f#X`, and ends at record-only state, stored input,
replayed parser input through `0xa904 -> 0x11774`, overlay skip/publication
boundaries, or the normal command-family page objects created by replayed
bytes.

### Audited Rows

- Macro id selection:
  `ESC &f#Y` reaches handler `0xe112`, rewinds the six-byte command record at
  `0x78299e`, takes the absolute parsed parameter, and writes current macro id
  `0x783164`. It creates no macro record, frame, page object, or pixels by
  itself. Later selector handler `0xdd08`, lookup helper `0xe0a4`, and
  overlay publication consume the selected id. Owner evidence is
  [Macro Replay Outcome
  Matrix](macro-data-chain.md#macro-replay-outcome-matrix) and
  `generated/disasm/ic30_ic13_macro_record_chain_helpers_00dfba.lst`.

- Macro selector dispatch:
  `ESC &f#X` reaches handler `0xdd08`. The selector consumes current id
  `0x783164`, selected record pointer `0x782d7a`, active data-chain frame
  `0x782d76`, frame kind byte `+0x09`, definition byte `0x782c18`, and parser
  record state. Selectors `0..10` route to definition start/stop,
  execute/call frame creation, overlay enable/disable, delete-all,
  delete-temporary, delete-current, and permanence writes. Guard exits while
  definition or active-chain state is incompatible preserve macro state and
  produce no page output. Owner evidence is
  [Macro Replay Outcome
  Matrix](macro-data-chain.md#macro-replay-outcome-matrix).

- Definition storage:
  selector `0` starts definition mode at `0xdd86..0xddfa`, writes definition
  byte `0x782c18`, selects or clears a record, copies current id into record
  `+0x08`, and may seed lowercase `ESC &f` or uppercase zero bytes through
  `0xe002` / `0xddf2..0xddf4`. While definition mode is active,
  alternate/data routing appends bytes through `0xe002`; `0xe002` allocates
  linked 0x100-byte chunks, stores 252 payload bytes per chunk after the next
  pointer, updates record raw count `+0x04`, and sets append-error byte
  `0x782c19` on allocation failure. Selector `1` at `0xddfc..0xde7a`
  normalizes the count, clears empty or auto-prefix-only records through
  `0xdfba`, and clears `0x782c18` / `0x782c19`. Output effect is stored input
  only. Owner evidence is [Macro Replay To Visible Consumer
  Map](macro-data-chain.md#macro-replay-to-visible-consumer-map).

- Record lookup, delete, and permanence:
  lookup helper `0xe0a4` scans 32 records at `0x782a98`, matching id word
  `+0x08` only when record head `+0x00` is nonzero; otherwise it selects the
  first free head-zero slot or reports a full-pool miss by clearing
  `0x782d7a`. Selectors `6..10` clear all records, clear temporary records,
  clear the selected record, clear permanence byte `+0x0a`, or set
  permanence byte `+0x0a`. These paths mutate record-pool state only; later
  execute/call/overlay selectors observe the changed pool. Owner evidence is
  [Field Groups](macro-data-chain.md#field-groups) and
  `generated/disasm/ic30_ic13_macro_record_chain_helpers_00dfba.lst`.

- Execute and call replay:
  selectors `2` and `3` require a selected nonempty record and frame space,
  then call `0xe418(2)` or `0xe418(3)`. `0xe418` writes active frame
  `0x782d76` with record head/count at `+0x00/+0x04`, source offset
  `+0x08 = 4`, kind `+0x09 = 2` for execute or `3` for call, and snapshot
  pointer `+0x0a`; call mode also pushes macro context state. `0xa904` gives
  that frame priority over live input, and data-chain reader `0x9f6a` returns
  stored payload bytes to the same parser wrapper and dispatch loop as live
  host bytes. Owner evidence is
  [Data-Chain Source-Equivalence
  Checkpoint](macro-data-chain.md#data-chain-source-equivalence-checkpoint).

- Frame-end cleanup and macro font context:
  when `0xa904` reaches frame count marker `+0x04 = -1`, cleanup
  `0xe22c..0xe408` unwinds frames, frees snapshots, restores context, clears
  host gate bit `0x780e66.1` when appropriate, and resumes the previous byte
  source. Call and overlay returns can run `0xe65c(0)`: `0xe65c` consumes
  macro context bytes `+8/+9`, refreshes selected font state through
  `0x13eb8`, `0x144d2`, and `0x14c64`, and calls `0xc428` to install the
  selected page-root context slot. This can change later printable glyphs, but
  creates no page object at `0xe65c`. Owner evidence is
  [Macro Context To Font Slot
  Checkpoint](macro-data-chain.md#macro-context-to-font-slot-checkpoint).

- Replayed byte consumers:
  after `0xa904 -> 0xda9a -> 0x11774`, macro payload bytes belong to ordinary
  owners. Printable replay uses `0xd04a -> 0x1393a -> 0x12f2e -> 0x1387c`;
  direct-control replay uses the direct-control owner; transparent replay uses
  delayed handler `0x12452`; raster replay uses `0x105d0`; rectangle replay
  uses `0x10898`; span-producing replay uses `0xf34a -> 0x12714`. Macro replay
  therefore creates compact, raster, rule, segment-list, fixed-list, or no
  page objects only by reaching those normal handlers. Owner evidence is
  [Macro Replay To Visible Consumer
  Map](macro-data-chain.md#macro-replay-to-visible-consumer-map).

- Overlay enable, skip, and replay at publication:
  selector `4` enables overlay only when current-id lookup succeeds, writing
  overlay state `0x782a92 = 1` and saved id `0x782a94`; selector `5` clears
  `0x782a92`. Publication helper `0xff1e` is the first visible consumer. When
  overlay state is enabled, saved-record lookup succeeds, and page-root retry
  flag `root+0x14.0` is clear, `0xff1e` calls `0xe4f4` to create kind-4
  non-replay frame `0x782d4c`, re-enters `0xa904 -> 0x11774`, lets replayed
  bytes mutate the current page-root object graph, and then continues
  publication. Disabled state, missing/empty record, or retry flag preserve
  base publication without overlay page-object mutation. Owner evidence is
  [Macro Replay Outcome
  Matrix](macro-data-chain.md#macro-replay-outcome-matrix).

- Publication and render after replay:
  replay-produced objects use the shared page pipeline:
  `0xff1e -> 0x1ed84 -> 0x1edc6 -> 0x1ef6a`. Compact text/downloaded glyphs
  dispatch through `0x1effe`, encoded raster through `0x1f88e`, rules through
  `0x1f446`, segment lists through `0x1f812`, and fixed lists through
  `0x1f756`. Macro has no private renderer or row writer; it only selects
  ordinary command-family paths by replaying stored bytes. Owner evidence is
  [Macro Replay To Visible Consumer
  Map](macro-data-chain.md#macro-replay-to-visible-consumer-map) and
  [Row-Store Primitive
  Map](page-raster-imaging.md#row-store-primitive-map).

### Field Classification

- Canonical macro state:
  current id `0x783164`, 32-record pool `0x782a98`, selected record pointer
  `0x782d7a`, record fields `+0x00/+0x04/+0x08/+0x0a`, active frame pointer
  `0x782d76`, frame fields `+0x00/+0x04/+0x08/+0x09/+0x0a`, overlay state
  `0x782a92`, saved overlay id `0x782a94`, and page-root retry flag
  `root+0x14.0`.
- Canonical context/font state:
  macro context records `0x782c1e..0x782c6d`, context stack pointer
  `0x782c6e`, static context record `0x782c64`, selected slot `0x782f06`,
  selected current-font context records `0x782ee6` / `0x782ef6`, selected
  page-root slot `0x78297e`, and page-root context slots `+0x2c..+0x68`.
- Canonical page/image state:
  only the downstream owner-created objects are page/image state: compact,
  raster, span, and text buckets under root `+0x1c`, rule list `+0x24`,
  fixed-list root `+0x28`, context slots `+0x2c..+0x68`, and their published
  and bridged render roots.
- Derived/cache state:
  normalized macro payload counts, replay cursor address
  `frame(+0x00) + frame(+0x08)`, selected context refresh results, replayed
  command-family page objects, and row products produced by normal render
  helpers after replay.
- Parser scratch:
  definition-mode byte `0x782c18`, append-error byte `0x782c19`, append chunk
  cursor `0x782c1a`, parser record cursor `0x78299e`, alternate/data table
  routing, replayed `D7` bytes returned by `0xa904`, and parser records or
  delayed-payload counters built later by `0xdaf0` / `0xdb74`.
- Firmware bookkeeping:
  host gate bit `0x780e66.1`, heap allocation state, allocation-failure report
  `0xe8f0 -> 0x9b5e(0x780e2e, 4)`, snapshot chains, frame cleanup
  `0xe22c`, context helpers `0xe996`, `0xe972`, and `0xe65c`, publication
  flag `0x782996`, and scheduler progress after publication.
- Hardware/external state:
  none for the ROM-local macro replay model once stored bytes re-enter the
  parser through `0xa904`.
- Unknown:
  no ROM-local middle edge remains for documented definition, execute/call
  replay, source equivalence, overlay publication, overlay skip gates, macro
  font-context refresh, and listed overlay payload families. Remaining exact
  macro boundaries are external/manual names for context-stack and overlay
  latches and the unchecked over-deep context pointer range; physical symptoms
  after adjacent RAM corruption are outside the ROM-local pixel contract.

### Output And Boundary Result

Macro id, record delete, permanence, and definition selectors are record or
stored-input state only. Execute and call selectors become visible only by
building frames consumed by `0xa904`, which returns stored bytes to the normal
parser and command-family owners. Overlay selectors become visible only at
publication when `0xff1e` builds a kind-4 frame and replays stored bytes before
continuing page publication.

No macro-specific page image or renderer exists. The first page-image effect
is whichever ordinary replayed handler queues an object; pixel generation
starts only after the shared publication/bridge/render path reaches
`0x1ef6a`. Remaining audit-ledger work starts from parser-only rows or the
final page/render owner crosswalk rather than from macro replay.

## Parser-Only And Explicit No-Output Rows

This cluster covers admitted bytes and parser table rows that do not
immediately enter a page-producing command owner. It starts at byte wrapper
`0xda9a`, parser loop `0x11774`, normal table `0x112a4`, alternate/data table
`0x116f6`, delayed restore `0x12218`, no-match paths, and generic drains. It
ends at parser scratch reset, swallowed wrapper bytes, append-only stored
input, delayed-handler restore, parser-external service return, or an explicit
no-page-output boundary.

### Audited Rows

- Private wrapper and reported-byte paths:
  byte wrapper `0xda9a` owns parser-visible byte normalization after `0xa904`
  has admitted a byte. `ESC ? 0x11` is swallowed entirely inside the wrapper:
  the third byte check at `0xdab2..0xdabe` restarts without returning `ESC`,
  `?`, or `0x11` to parser loop `0x11774`. Other `ESC ? X` siblings rejoin
  the first-byte comparison, and non-question ESC lookahead bytes are reported
  through `0x9ec0` before the parser receives `ESC`. Owner evidence is
  [No-Output And Reported-Byte
  Checkpoint](pcl-parser-core.md#no-output-and-reported-byte-checkpoint) and
  `generated/disasm/ic30_ic13_pcl_escape_parser_00da9a.lst`.

- Normal zero-handler C0 rows:
  normal mode-zero C0 bytes `0x00`, `0x07`, and `0x0b` match explicit rows in
  table `0x112a4` with zero handler longwords. They take
  `0x119a6..0x119f4`, write the row's next mode, call delayed restore
  `0x12218` when the row returns to mode zero, and reset command-record cursor
  `0x78299e`, nonnumeric scratch `0x782a26`, numeric scratch `0x782a3e`, and
  alternate echo latch `0x782a56`. They do not fall through to printable
  handler `0xd04a` or neighboring C0 handlers. Owner evidence is
  [Parser Artifact And No-Output
  Boundary](firmware-dataflow-model.md#parser-artifact-and-no-output-boundary).

- Alternate/data blank rows and no-match append:
  when alternate/data selector `0x782c18` is set, table `0x116f6` handles
  mode-zero blank C0 rows `0x00` and `0x07..0x0f` through
  `0x11930..0x11ab8`. That path flushes byte scratch through `0x123ae`,
  numeric scratch through `0x123de`, appends the matched byte through
  macro/data sink `0xe002`, and rejoins terminal reset. Alternate/data
  mode-zero no-match bytes append through `0x11b82..0x11b8a -> 0xe002`.
  These bytes are stored input; they can affect pixels only if macro/data
  replay later returns them through `0xa904`. Owner evidence is
  [Alternate/Data Dispatch Decision
  Checkpoint](pcl-command-map.md#alternatedata-dispatch-decision-checkpoint)
  and [Macro Replay Outcome
  Matrix](macro-data-chain.md#macro-replay-outcome-matrix).

- Delayed restore and generic drains:
  delayed scheduler `0x121cc` stores flag `0x782a1a`, handler pointer
  `0x782a1c`, and saved record `0x782a20..0x782a25`; restore `0x12218`
  either calls the saved handler in normal mode or routes alternate/data
  payloads through `0x1228a` / `0x12358`. Generic drain
  `0x1228a -> 0x12328` consumes absolute payload counts through `0xdace`
  without echoing printable bytes or queueing page objects. Normal restored
  handlers are owned by their command-family notes; alternate/data drains are
  append or synchronization state. Owner evidence is
  [Parser Core Outcome
  Matrix](pcl-parser-core.md#parser-core-outcome-matrix) and
  [Binary Payload Lifecycle](firmware-dataflow-model.md#binary-payload-lifecycle).

- Display-reader terminator and unimplemented parser artifacts:
  `ESC Z` is not a standalone parser-table output command. It is consumed by
  display readers `0x12536` and `0x12120` inside their direct `0xa904` loops
  before returning to the main parser. `ESC &lT/t` is a parser-table artifact:
  uppercase `T` has no terminal handler, and lowercase `t` reaches lowercase
  rewind helper `0x11f4c` without writing page environment, page objects, or
  render inputs. Owner evidence is
  [No-Output And Reported-Byte
  Checkpoint](pcl-parser-core.md#no-output-and-reported-byte-checkpoint) and
  [Inbound Byte Outcome
  Classes](pcl-command-map.md#inbound-byte-outcome-classes).

- No-match and callback continuations:
  normal mode-zero no-match path `0x118b2..0x11900` reads selected context byte
  `0x782ee6 + 16 * 0x782f06 + 5`. Value `1` routes the byte to printable
  `0xd04a`; any other value ignores the byte and fetches again without page
  object output. Nonzero-mode no-match path `0x11b32..0x11b7e` calls active
  callback pointer `0x78299a`; callback return to mode zero clears parser
  cursors and pending delayed byte `0x782a1a`, while nonzero return keeps the
  parser in the command-family mode. Owner evidence is
  [Main Parser Branch
  Boundaries](pcl-parser-core.md#main-parser-branch-boundaries).

- Parser-external service return:
  no-byte path `0x117d2..0x11818` clears service latch `0x780e3b`, services
  wait object `0x780202` through `0x10c8`, rewrites macro/page state byte
  `0x782a92` from `0x63` to `1` when that predicate matches, and returns from
  the parser loop instead of dispatching a command byte. It produces no
  parser-dispatched page state. Owner evidence is
  [Parser Core Outcome
  Matrix](pcl-parser-core.md#parser-core-outcome-matrix) and
  [Host/Status Outcome
  Matrix](errors-and-status.md#hoststatus-outcome-matrix).

### Field Classification

- Canonical parser state:
  mode byte `0x782999`, alternate/data selector `0x782c18`, command-record
  cursor `0x78299e`, six-byte records rooted at `0x7829a2`, table roots
  `0x112a4` / `0x116f6`, selected context index `0x782f06`, and delayed fields
  `0x782a1a`, `0x782a1c`, and `0x782a20..0x782a25`.
- Parser scratch:
  byte scratch cursor `0x782a26`, numeric scratch cursor `0x782a3e`, scratch
  buffers `0x782a2a..` and `0x782a42..`, matched-byte buffer
  `0x783196..0x783199`, tokenizer local digits, lookahead bytes, and
  alternate/data append scratch.
- Derived/cache state:
  saved delayed handler pointer, restored record copies, payload budget
  `0x783140`, alternate/data echo latch `0x782a56`, and generated table
  extracts used to name rows.
- Firmware bookkeeping:
  reported-byte helper `0x9ec0`, append sink `0xe002`, terminal restore
  helper `0x12218`, scratch flush helpers `0x123ae` / `0x123de`, payload
  reader `0xdace`, generic drain helpers `0x1228a` / `0x12328` / `0x12358`,
  active callback pointer `0x78299a`, no-byte latch `0x780e3b`, wait object
  `0x780202`, macro/page byte `0x782a92`, and setup-handler state.
- Canonical page/render state:
  none for the rows in this cluster. Page roots, page objects, publication,
  render roots, and row buffers can only be written by a restored saved
  handler, later replayed appended bytes, a no-match byte that reaches
  `0xd04a`, or following parser input.
- Hardware/external state:
  none after `0xa904` has admitted a byte into parser-local code. Direct host
  MMIO and service-preemption details remain in host/status owner notes.
- Unknown:
  no ROM-local branch remains anonymous for the documented zero-handler rows,
  alternate/data append rows, `ESC ? 0x11`, display terminator `ESC Z`,
  `ESC &lT/t`, generic counted drains, no-match fallback, callback
  continuation, or parser-external service return.

### Output And Boundary Result

Parser-only rows produce no immediate page root, page object, publication,
render work, or pixels. Their output is one of: swallowed input, reported
lookahead, parser scratch reset, delayed-handler restore, append-only stored
input, counted drain, no-match ignore, callback continuation, or parser
service return.

The only routes from this cluster to pixels are explicit later routes: a
restored saved handler can enter its command-family owner; alternate/data
stored bytes can replay through `0xa904`; normal no-match can call `0xd04a`
only when the selected context predicate accepts it; or later host bytes can
enter a page-producing owner. Remaining audit-ledger work is the final
page/render owner crosswalk.

## Page And Render Owner Crosswalk

This final checkpoint connects the audited dispatch clusters above to the
shared page-image and render owners. It starts after a command-family owner has
either produced page state or explicitly stopped at no-output/status/stored
input, and ends at the first render helper or exact non-render boundary. It
does not replace family notes; it names the common page roots, bridge roots,
dispatch order, and row-store routes a reader should follow after any
supported byte stream reaches page-image state.

### Audited Rows

- Compact text, transparent printable bytes, macro-replayed printable bytes,
  and downloaded glyphs:
  first page-image state is a compact bucket object under page-root `+0x1c`,
  produced through `0xd04a -> 0x1393a -> 0x12f2e -> 0x1387c`. The object
  carries class/selector/count/key fields `+0x04/+0x05/+0x06/+0x08` and
  compact payload bytes at `+0x0a..`; font context lives in page-root slots
  `+0x2c..+0x68`. Publication and bridge copy bucket root `+0x1c` to render
  root `+0x18` and context slots to render slots `+0x24..+0x60`. First render
  consumer is `0x1ef6a -> 0x1efc2 -> 0x1effe`; row-store helpers are
  `0x1f034`, `0x1f0d2`, `0x1f1f0`, or `0x1f264` plus row-copy tables. Owner
  evidence is [Command-Family To Page-Object
  Crosswalk](firmware-dataflow-model.md#command-family-to-page-object-crosswalk)
  and [Row-Store Primitive
  Map](page-raster-imaging.md#row-store-primitive-map).

- Segment-list and fixed-list text spans:
  pending span flush reaches `0xf34a -> 0x12714`. Portrait spans become
  segment-list bucket objects under root `+0x1c` through
  `0x13520/0x135f0`; landscape/fixed spans become fixed-list objects under
  root `+0x28` through `0x136d2`. Bridge maps root `+0x1c` to render `+0x18`
  and root `+0x28` to render `+0x20`. First render consumers are
  `0x1efc2 -> 0x1f812 -> 0x1f862` for segment lists and
  `0x1ef6a -> 0x1f756 -> 0x1f7b0` for fixed lists. Owner evidence is
  [Page Object Shape Route
  Index](firmware-dataflow-model.md#page-object-shape-route-index) and
  [Render Entry Outcome
  Matrix](page-raster-imaging.md#render-entry-outcome-matrix).

- Encoded raster rows:
  accepted delayed `ESC *b#W` payloads reach
  `0x105d0 -> 0x13070 -> 0x13250`, creating encoded raster bucket objects
  under root `+0x1c`. The object carries high-bit class byte `+0x04`, mode
  byte `+0x05`, count/capacity `+0x06`, key `+0x08`, and payload bytes
  `+0x0a..`. Bridge maps root `+0x1c` to render `+0x18`. First render
  consumer is `0x1efc2 -> 0x1f88e`; mode helpers are `0x1f8da`, `0x1f8e6`,
  `0x1f920`, and `0x1f9c6`. Owner evidence is [Raster State To Visible
  Consumer Map](raster-graphics.md#raster-state-to-visible-consumer-map) and
  [Row-Store Primitive
  Map](page-raster-imaging.md#row-store-primitive-map).

- Rectangle/rule objects:
  valid `ESC *c#P` paths reach
  `0x10898 -> 0x10b80 -> 0x13386 -> 0x133aa`, creating ordered rule-list
  objects under page-root `+0x24`. Rule fields include selector `+0x05`, key
  `+0x06`, width `+0x08`, height `+0x0a`, and continuation `+0x0c`. Bridge
  maps root `+0x24` to render root `+0x1c`, ORs selector byte `+0x05` with
  `0x10`, and copies height into continuation. First render consumer is
  `0x1ef6a -> 0x1f446`, then solid helper `0x1f596` or pattern helper
  `0x1f4e0`. Owner evidence is
  [Rectangle State To Visible Consumer
  Map](rectangle-graphics.md#rectangle-state-to-visible-consumer-map) and
  [Render Entry Outcome
  Matrix](page-raster-imaging.md#render-entry-outcome-matrix).

- Publication, bridge, and band scheduling:
  publication helper `0xff1e` turns current root state into protected
  page/control pool state rooted at `0x780ea6`, sets publication flag
  `0x782996`, and clears current root `0x78297a` as appropriate. Scheduler
  paths select source record `0x780eae`; work-record selection writes active
  render pointer `0x783a18`; bridge `0x1ed84 -> 0x1edc6` copies bucket,
  rule, fixed, and context roots into render roots `+0x18/+0x1c/+0x20` and
  slots `+0x24..+0x60`. Band entry `0x1eba4` calls `0x1ef6a` only on render
  outcomes; cleanup/throttle/capacity-wait outcomes do not render rows. Owner
  evidence is [Band Scheduling Route
  Index](firmware-dataflow-model.md#band-scheduling-route-index) and
  [Render Entry Outcome
  Matrix](page-raster-imaging.md#render-entry-outcome-matrix).

- Render dispatch and pixel composition order:
  `0x1ef6a` derives band caches through `0x1ef86`, renders bucket-chain root
  `+0x18` first through `0x1efc2`, rule root `+0x1c` second through
  `0x1f446`, and fixed root `+0x20` last through `0x1f756`. Within bucket
  objects, class byte `+0x04` selects compact/text `0x00..0x3f`,
  segment-list `0x40..0x7f`, or encoded raster `0x80..0xff`. The ROM-local
  composition model is direct stores in this call order; there is no hidden
  shared blend layer outside the object helpers. Owner evidence is
  [Pixel Generation Owner
  Summary](page-raster-imaging.md#pixel-generation-owner-summary) and
  [Pixel Composition
  Checkpoint](page-raster-imaging.md#pixel-composition-checkpoint).

- Explicit non-render outcomes:
  host/status side channels, parser-only rows, alternate/data append-only
  rows, generic drains, font/map state before printable consumption, raster
  setup before transfer, rectangle size/fill state before `ESC *c#P`, macro
  definition state before execute/call/overlay replay, and failed validation
  or no-install exits have no page-object root, bridge root, first render
  consumer, or row-store endpoint at that byte. Their owner notes name the
  exact state that remains for a later byte or replay path to consume.

### Field Classification

- Canonical page/image state:
  current root `0x78297a`, compact/raster/span bucket root `+0x1c`, rule root
  `+0x24`, fixed-list root `+0x28`, font context slots `+0x2c..+0x68`,
  published page/control pool rooted at `0x780ea6`, source record
  `0x780eae`, active render pointer `0x783a18`, render roots
  `+0x18/+0x1c/+0x20`, and render context slots `+0x24..+0x60`.
- Canonical object state:
  bucket object fields `+0x04/+0x05/+0x06/+0x08/+0x0a`, rule fields
  `+0x05/+0x06/+0x08/+0x0a/+0x0c`, fixed-list fields `+0x04..+0x0d`, compact
  payload glyph/resource bytes, raster payload bytes, and copied context
  longwords.
- Derived/cache state:
  bucket/key fields `0x782a7c..0x782a7e`, render band row count `0x783a20`,
  remainder `0x783a22`, destination base `0x783a28`, destination stride
  `0x783a1c`, compact context cache `0x783a2c`, row-offset tables, phase
  bytes, fallback buffer base `0x7810b4 + byte_pair_offset`, and object
  continuation fields normalized by `0x1edc6`.
- Parser scratch:
  none after a page object has been published and bridged. Parser records,
  delayed payload snapshots, and replay bytes have already become owner state,
  page objects, status/no-output outcomes, or stored input.
- Firmware bookkeeping:
  allocator cursors, retry bits, publication flag `0x782996`, scheduler source
  and work-record selection fields, render-work alternation, throttle/capacity
  state, and cleanup/release cursors.
- Hardware/external state:
  physical consumption after ROM row-buffer writes is outside this ROM-local
  crosswalk. Physical timing does not change which parser owner, page root,
  bridge root, render dispatcher, or row-store helper the documented byte
  stream reaches.
- Unknown:
  no crosswalk edge remains unresolved for the documented page-object classes,
  bridge roots, render dispatch order, or row-store primitive families.
  Remaining exact boundaries are the object-owner boundaries already named in
  their notes, such as invalid compact helper targets, missing external
  resource bytes, or hardware after ROM row writes.

### Output And Boundary Result

For any audited supported stream, the page/render path is now explicit:
command-family owner writes either no page state or one of the canonical page
roots; publication and bridge copy those roots into render roots; `0x1ef6a`
dispatches bucket, rule, and fixed-list roots in ROM order; and row-store
helpers derive pixels from object fields plus copied context/resource state.

This dispatch audit ledger has no remaining named pending row class. The full
ROM documentation goal still requires any future completion claim to audit the
broader checked-in documentation against the objective, but this ledger's
supported-stream dispatch composition is closed until new disassembly evidence
changes a named owner boundary.
