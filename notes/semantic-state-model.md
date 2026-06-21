# Semantic State Model

This file composes broad-enough ROM clusters into renderer-facing state
concepts. It complements the low-level ledger in
`notes/reverse-engineering-ledger.md`; it does not replace address-level
notes, disassembly windows, or executable fixtures.

## Vertical Forms Control

Status: partially anchored. The table definition path, its immediate
text-bottom effect, the forward in-text channel-jump path, the
before-top forward channel-jump normalization path, the selector-zero
target-equal path, the selector-zero top-of-form page-eject path, and one
wrap-hit page-eject path are modeled. One target-after-text path through
bottom recovery is also modeled. The wrap no-hit and alternate
bottom-recovery branches inside the channel-jump consumer still need
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
  `0x12cfe ESC &l#W loads vertical forms control state`.
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
  command handlers.
  Evidence: `0x11f6e` schedules delayed handler; `0x12cfe` rewinds and
  reads parsed count.

### Writers

- `0x11f6e` is the parser final for `ESC &l#W`; it schedules delayed
  handler `0x12cfe` through `0x121cc`.
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

### Output Effect

The anchored output effects are text-bottom recomputation, payload
boundary behavior, and one forward VFC channel jump. In the current
definition fixture, a Letter 6-LPI base state with top offset `90`, text
bottom `3240`, and VMI `50` receives `ESC &l4W 00 00 00 02`. Handler
`0x12cfe` stores the table prefix `00 00 00 02`, derives text bottom
`190`, and leaves the following printable `!` queued at compact coord
`0x9001`.

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

### Confidence

High for the `0x11f6e -> 0x12cfe` delayed payload boundary, table bytes,
reject cases, zero-count reset, text-bottom cache effect, and forward
`0x1280a` in-text channel hit. High for before-top normalization through
`0x128ae..0x128f4` when it rejoins the forward in-text hit path. High for
the selector-zero target-equal early exit and selector-zero page-eject
branch through `0x1299c..0x129c4` when
`start_line <= text_last_line + 1`. High for the wrap-hit branch through
`0x129c6..0x12af8` when a wrapped search finds a channel before the
original start line and `start_line <= text_last_line + 1`. High for the
target-after-text branch through `0x129ee..0x12b5a` when the found line
is `63` and `start_line <= text_last_line + 1`. Medium for the exact
semantic names of `0x782ede`/`0x782edf`/`0x782ee0`; the line-count
interpretation matches fixtures and disassembly, but wrap no-hit and
alternate bottom recovery branches still need complete lifting.

### Fixtures

- `0x12cfe ESC &l#W loads vertical forms control state`
- `mixed VFC definition stream consumes payload before printable
  page-record queue`
- `mixed VFC channel jump stream moves cursor before printable page-record
  queue`
- `mixed VFC before-top channel jump normalizes start line before
  printable`
- `mixed VFC selector-zero top-of-form no-op reaches printable page-record
  queue`
- `mixed VFC selector-zero page-eject publishes old page before fresh
  printable`
- `mixed VFC wrap-hit publishes old page before fresh printable`
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

- `0x129fc..0x12a10`: target-after-text alternate entrances skip the
  `0xf124` publication when start line is `0` or greater than
  `text_last_line + 1`; exact output effect needs fixtures.
- `0x12a22..0x12a78`: wrap no-hit or hit-at/after-start path calls
  `0xf34a`, `0xf124`, `0xf06e`, and writes the top-of-form target;
  triggering conditions and publication effect need fixtures.
- `0x12afc..0x12b5a`: bottom/page-recovery placement is modeled for the
  target-after-text line-63 case; alternate entrances and target-line
  values still need fixtures.
- `0x12b5e..0x12b92`: bottom/page-recovery placement after the selector-zero
  and wrap branches writes `0x782c8e`; triggering conditions and final
  cursor positions need fixtures.
- `0x12b96..0x12cfc`: default table bit meanings are known by bit
  positions but not fully named by PCL channel convention.
- Lowercase `ESC &l#w...#W` delayed-record preservation is inferred from
  the shared `0x121cc` boundary but not yet covered by a VFC-specific
  fixture.
