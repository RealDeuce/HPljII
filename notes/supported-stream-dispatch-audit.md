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
  below.
- Still pending in this ledger:
  raster transfer, rectangle/rule imaging, font selection and downloaded
  glyphs, macro definition/replay, parser-only rows, and page/render owner
  crosswalk rows.

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
