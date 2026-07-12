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
  control cluster below.
- Still pending in this ledger:
  cursor and layout command families beyond direct C0 controls, publication
  and VFC, raster transfer, rectangle/rule imaging, font selection and
  downloaded glyphs, macro definition/replay, parser-only rows, and
  page/render owner crosswalk rows.

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
