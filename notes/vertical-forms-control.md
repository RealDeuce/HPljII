# Vertical Forms Control Firmware

This note is the tracked command-family contract for LaserJet II vertical
forms control. It composes the `ESC &l#W` VFC table-definition payload path,
the `ESC &l#V` channel-jump consumer, the default-table builder, and the
visible output effects through cursor movement and page publication.

Status: composed for the documented `ESC &l#W` and `ESC &l#V`
command-family paths. The low-level ledger is preserved in
`notes/reverse-engineering-ledger.md`; this note is the semantic contract
for byte-stream reproduction.

The detailed low-level ledger remains in
`notes/reverse-engineering-ledger.md`, and the field inventory is mirrored in
`notes/semantic-state-model.md` under `Vertical Forms Control`.

## Evidence

- `generated/disasm/ic30_ic13_vertical_forms_control_01280a.lst`
- `generated/analysis/ic30_ic13_renderer_fixture_harness.md`
- `generated/analysis/ic30_ic13_direct_control_code_flow.md`
- `generated/disasm/ic30_ic13_control_code_handlers_00f02c.lst`
- `generated/disasm/ic30_ic13_hmi_vmi_handlers_00ca8c.lst`
- `generated/disasm/ic30_ic13_macro_record_chain_helpers_00dfba.lst`
- `notes/page-raster-imaging.md`
- `notes/semantic-state-model.md`

Primary fixtures:

- `0xe5e2 refreshes page layout, default VFC table, and static font context`
- `0x12cfe ESC &l#W loads vertical forms control state`
- `mixed VFC definition stream consumes payload before printable page-record queue`
- `mixed VFC lowercase delayed record survives until uppercase W`
- `mixed VFC channel jump stream moves cursor before printable page-record queue`
- `mixed VFC before-top channel jump normalizes start line before printable`
- `mixed VFC before-top target-after-text skips publication`
- `mixed VFC start-after-text skips wrap and publication`
- `mixed VFC start-after-text wraps to table hit before printable`
- `mixed VFC start-after-text wraps to bottom recovery before printable`
- `mixed VFC selector-zero top-of-form no-op reaches printable page-record queue`
- `mixed VFC selector-zero start-after-text returns to top`
- `mixed VFC selector-zero page-eject publishes old page before fresh printable`
- `mixed VFC wrap-hit publishes old page before fresh printable`
- `mixed VFC wrap-no-hit publishes old page and returns to top`
- `mixed VFC target-after-text recovers near top before fresh printable`
- `0x1280a VFC alternate high-start recovery entries`
- `0x12b96 default VFC table channel convention`

## Owner Summary

Concept: this note owns the vertical forms control command family from parser
dispatch to table state, cursor movement, and page-boundary effects. It covers
delayed `ESC &l#W` table-definition payloads, lowercase same-family delayed
record preservation, default-table rebuilds, `ESC &l#V` channel jumps,
selector-zero behavior, wrap/recovery branches, and the publication split
where pre-VFC page objects remain renderable on the old page.

Primary route:

- Parser final `0x11f6e` schedules delayed `ESC &l#W` handler `0x12cfe`
  through `0x121cc`; restore `0x12218` later calls `0x12cfe` with the saved
  six-byte command record.
- Table-load route:
  `0x12cfe -> 0xdace payload bytes -> 0x782dde table words
  -> 0x782dc2/0x782dd2 text-bottom caches`.
- Default-table route:
  `0x12cfe count 0` or layout refresh `0xe5e2 -> 0x12b96
  -> 0x782dde..0x782edd`.
- Channel-jump route:
  `0x1280a -> VMI/top/current-y line computation -> 0x782dde scan
  -> 0xf06e/0xf34a -> 0x782c8a/0x782c8e`.
- Page-boundary route:
  selected `0x1280a` branches call `0xf124 -> 0xff1e` before the following
  printable byte allocates a fresh page root.
- Visible output then follows the ordinary printable/page-record/render owners
  after VFC has changed cursor state or published the old page.

Field groups:

- Canonical VFC table: 128 16-bit words at `0x782dde..0x782edd`; selectors
  are one-based and map to bit `1 << (selector - 1)`.
- Canonical layout inputs: VMI `0x783160`, top offset `0x782dce`, vertical
  cursor `0x782c8e`, horizontal cursor `0x782c8a`, left margin `0x782dd6`,
  and right margin `0x782dda`.
- Canonical line bounds: VFC bottom cache `0x782dc2`, text-bottom cache
  `0x782dd2`, last VFC/page line `0x782ede`, last text line `0x782edf`, and
  last printable text line `0x782ee0`.
- Canonical page output: current root `0x78297a`, publication helper
  `0xf124`, and page-root finalizer `0xff1e`.
- Derived/cache: line numbers derived from VMI/top/current-y, text-bottom
  conversions through coordinate helpers, and default-table channel patterns
  from `0x12b96`.
- Parser scratch: command-record cursor `0x78299e`, delayed payload state
  from `0x121cc`, restored `ESC &l#W` records, and bytes consumed by `0xdace`.
- Firmware bookkeeping: modified-layout flag `0x782ee1`, pending-width latch
  `0x782a58`, pending cursor/text latch `0x782a6d`, and pending span-enable
  byte `0x783184`.
- Unknown: manual HP names for `0x782ede`, `0x782edf`, and `0x782ee0` remain
  inferred, but their ROM roles are tied to the cited writers and consumers.

Writers and readers:

- `0x12cfe` writes table bytes, clears unused words, derives VFC/text-bottom
  caches, and clears `0x782ee1`.
- `0x12b96` writes the complete default 128-word VFC table and VFC bottom
  cache.
- `0xe5e2` writes refreshed page layout, default VFC table state, and static
  font context before VFC, printable, or macro replay consumers run.
- `0xfe54` writes line-bound caches consumed by table load and channel jumps.
- `0x1280a` reads selector, VMI, top offset, current cursor, line-bound
  caches, and table words, then writes cursor state or calls page publication.
- `0xf06e`, `0xf34a`, and `0xf124` consume margin, span, and page-root state
  for VFC cursor reset, span flush, and page publication.

Output effect:

- `ESC &l#W` has no immediate pixels; it changes the table and bottom caches
  consumed by later `ESC &l#V`, vertical overflow, and printable placement.
- `ESC &l#V` does not draw directly; it moves the cursor before the next
  printable byte queues a page object.
- Selector-zero, wrap, and target-after-text branches can publish the current
  page before the next printable byte starts a fresh page.
- Non-publishing recovery branches only rewrite cursor state and leave the
  current page root active.

Evidence and boundaries:

- Disassembly evidence is in
  `generated/disasm/ic30_ic13_vertical_forms_control_01280a.lst` and the
  direct-control/page-publication listings named above.
- Fixture evidence is named in the Primary fixtures list above; those streams
  pin delayed table load, default-table construction, channel convention,
  cursor-only moves, recovery, wrap, and page-publication splits.
- No unresolved ROM-local middle edge remains for the documented `ESC &l#W`
  table-definition or `ESC &l#V` channel-jump contract. Remaining boundaries
  are manual naming of line-count fields and external physical correlation,
  not parser, table, page-record, or render-dispatch behavior.

## Field Groups

Canonical VFC table:

- `0x782dde..0x782edd`: 128 16-bit VFC channel words. `0x12cfe` writes this
  table from `ESC &l#W`; `0x12b96` builds the default table; `0x1280a` scans
  it for `ESC &l#V`.
- Channel selectors are one-based. `0x1280a` maps selector `n` to mask
  `1 << (n - 1)`, so selector `2` searches for bit `0x0002`.
- The default-table fixture pins example words for Letter at 6 LPI:
  line `0 = f8fd`, line `32 = 806c`, line `48 = a05c`, line `61 = 0006`,
  line `62 = 010e`, line `63 = 0004`, and line `64 = 0000`.

Canonical layout inputs:

- `0x783160`: VMI / line advance. It converts line numbers to cursor
  positions and is read by `0x1280a`, `0x12cfe`, and page-length logic.
- `0x782dce`: top offset. It is the origin for VFC line-to-cursor conversion.
- `0x782c8e`: vertical cursor. `0x1280a` reads it to compute the start line
  and writes it before the next printable byte is queued.
- `0x782c8a`: horizontal cursor. `0x1280a` resets it through `0xf06e` on
  modeled jump and recovery paths.
- `0x782dd6` and `0x782dda`: left and right text margins. `0xf06e` uses the
  left margin when VFC resets x.

Derived/cache line bounds:

- `0x782dd2`: text-bottom cache. `0x12cfe` copies the VFC-derived limit here.
- `0x782dc2`: VFC-derived bottom/limit before it is copied to `0x782dd2`.
- `0x782ede`: last VFC/page line index. The Letter fixture uses `63`.
- `0x782edf`: last text line index used by `0x12b96`.
- `0x782ee0`: last printable text line. The Letter fixture uses `62`.

Layout-refresh fields:

- `0xe5e2` writes top offset `0x782dce`, clears layout scratch `0x782dd0`,
  resets left/right margins `0x782dd6` / `0x782dda`, clears right-margin
  fraction `0x782ddc`, refreshes cursor y `0x782c8e`, recomputes text bottom
  `0x782dd2`, and rebuilds the default VFC table through `0x12b96`.
- The same fixture pins the normal-page line caches as
  `0x782edf = 2`, `0x782ee0 = 2`, `0x782ede = 3`, and
  `0x782dc2 = pack12(240)`. The short-page case pins negative top/text-bottom
  outputs, `0x782edf = 0`, and `0x782ede = 2`.
- The static-font side of this helper refreshes remembered secondary symbol
  `0x782f0a = 5`, dirties and clears `0x782f2d`, clears the static context,
  and calls the context helpers represented by fixture events `call-13eb8`,
  `call-c428`, and `call-1b04c`.

Parser scratch and firmware bookkeeping:

- `0x78299e`: parsed six-byte command record cursor. `0x12cfe` rewinds it
  before reading the delayed `ESC &l#W` count.
- `0x782ee1`: modified-layout flag cleared after table load/default rebuild.
- `0x782a58` and `0x782a6d`: pending text/cursor latches cleared by direct
  control helpers on VFC cursor-changing paths.
- `0x783184`: pending text-span flush enable tested by `0xf34a` before
  VFC cursor or page-boundary changes.
- `0x78297a`: current page-root pointer. `0x10084` ensures it before a VFC
  jump; `0xf124`/`0xff1e` publishes and clears it on page-eject paths.

External/manual naming:

- `0x782ede`, `0x782edf`, and `0x782ee0` have line-count roles proven by use
  and fixtures, but their HP manual names are still inferred. This is not an
  unresolved ROM-local parser, table-load, channel-jump, page-publication, or
  render boundary for the documented VFC streams.

## Table Definition

`0x11f6e` is the parser final for `ESC &l#W`. It schedules delayed handler
`0x12cfe` through `0x121cc`.

`0x12cfe` is the payload handler:

- rewinds parser scratch at `0x78299e`;
- reads the absolute byte count from the restored six-byte record;
- consumes payload bytes through the `0xdace` data reader;
- stores accepted table payload bytes into `0x782dde`;
- clears unused table words after the loaded payload;
- derives `0x782dc2`, copies it to `0x782dd2`, and clears `0x782ee1`.

The payload-count branch matrix at `0x12cfe..0x12f24` is part of the table
definition contract:

- Count `0`:
  `0x12d38..0x12dc8` takes the default-table path when the VMI conversion
  helper returns nonzero. It rebuilds top offset state, calls `0xea16`,
  refreshes line-count caches through `0xfe54`, rebuilds the default VFC table
  through `0x12b96`, and returns without consuming payload bytes.
- Odd counts:
  `0x12da0..0x12dca` rejects table installation for odd byte counts. It drains
  exactly the absolute count through `0xdace` and returns without writing
  `0x782dde` or changing the VFC bottom cache.
- Even counts larger than the current table window:
  after `0xfe54`, `0x12d92..0x12dae` computes
  `2 * (0x782ede + 1)`. If the absolute count is larger than that window,
  the handler drains the payload through `0xdace` and returns without writing
  the table.
- Even counts within the current table window:
  `0x12de8..0x12e5c` stores payload bytes directly into the byte-addressed
  VFC table at `0x782dde`. Counts up to `0x100` write at most 256 bytes, then
  clear every remaining 16-bit table word from `count / 2` through index
  `127`.
- Even counts above `0x100`:
  `0x12e0e..0x12f12` stores only the first `0x100` payload bytes into
  `0x782dde..0x782edd` and drains any remaining payload bytes through
  `0xdace` without storing them.

After a successful nondefault table write, `0x12e5c..0x12f24` initializes
`0x782dc2` from `0x782dba - 0x782dbe`, scans the loaded table for channel-2
bit `0x0002` through line `0x782ee0`, converts the first matching line into a
cursor limit through helpers `0x332ee`, `0x104d8`, and `0x10518`, copies
`0x782dc2` to `0x782dd2`, and clears modified-layout flag `0x782ee1`.

Fixture `ESC &l4W 00 00 00 02 !` proves that the four payload bytes are
consumed before the following printable byte is parsed. It stores table prefix
`00 00 00 02`, derives text-bottom cache `0x00be0000`, and leaves the
following `!` queued at compact coord `0x9001`.

The lowercase-delayed fixture `ESC &l4w4W 00 00 00 02 !` proves same-family
payload preservation. Lowercase `w` records snapshot
`80 77 00 04 00 00`; the following uppercase `W` reaches `0x11f6e` but does
not replace the pending delayed record while the pending flag is set. The
restore then uses the lowercase record and consumes payload bytes after the
uppercase final.

## Default Table

`0x12b96` builds the default VFC table from cached line bounds. It is called
by zero-count/default VFC handling and by page/layout refresh paths such as
`0xf9e8` and `0xe5e2`.

For `0x782ee0 = 62` and `0x782ede = 63`, the default-table fixture proves:

- channel 1 marks line `0`;
- channel 2 marks lines `61` and `62`;
- channel 3 marks each active text line plus line `63`;
- channel 4 marks even lines;
- channel 5 marks multiples of `3`;
- channel 6 marks line `0` and the half-text line;
- channel 7 marks line `0`, half-text, quarter-text, and three-quarter lines;
- channel 8 marks multiples of `10`;
- channel 9 marks line `62`;
- channels 10 and 11 are not set by this builder;
- channel 12 marks line `0`;
- channels 13, 14, 15, and 16 mark multiples of `7`, `6`, `5`, and `4`.

Fixture `0xe5e2 refreshes page layout, default VFC table, and static font
context` proves the default builder is part of the shared page-layout refresh,
not only the explicit VFC command family. For the normal-page case the default
table prefix is `f8 fd 00 46 01 6e 00 44 00 00 00 00 00 00 00 00`; for the
short-page case it is `f9 ff 00 60 00 04 00 00 00 00 00 00 00 00 00 00`.
These bytes are canonical VFC table state consumed later by `0x1280a`.

The builder algorithm is pinned by
`generated/disasm/ic30_ic13_vertical_forms_control_01280a.lst`:

- `0x12b9e..0x12c32` iterates line index `D5` from `0` through
  `0x782edf`, stopping at line `0x80`. It starts each active text-line word
  with channel-3 bit `0x0004`, then ORs in channel bits for line multiples:
  channel 4 for even lines, channel 5 for multiples of `3`, channel 8 for
  multiples of `10`, channels 13/14/15 for multiples of `7`/`6`/`5`, and
  channel 16 for multiples of `4`.
- `0x12c36..0x12c42` clears every remaining table word through index `127`.
  This makes the default table a complete 128-word canonical state block, not
  a partial overlay on a previous table.
- `0x12c44..0x12c48` ORs line `0` with `0x0861`, adding channels 1, 6, 7,
  and 12 to the loop-generated line-zero bits.
- `0x12c4a..0x12c72` marks channel 2 on lines `0x782edf - 1` and
  `0x782edf`, and marks channel 9 on line `0x782edf`.
- `0x12c76..0x12ccc` adds channel 6 at the half-text line, channel 7 at the
  quarter and three-quarter text lines, and channel 3 at final VFC line
  `0x782ede`.
- `0x12ce6..0x12cf0` copies text-bottom cache `0x782dd2` into VFC bottom
  cache `0x782dc2` and clears modified-layout flag `0x782ee1`.

The default builder's writers are therefore `0x12b96` for table
`0x782dde..0x782edd`, VFC bottom cache `0x782dc2`, and modified-layout flag
`0x782ee1`. Its readers are zero-count `0x12cfe`, shared layout refresh
`0xe5e2`, page-length/layout helpers that call `0x12b96`, and channel-jump
consumer `0x1280a`. The output effect is indirect: it defines the canonical
channel table that later `ESC &l#V` searches before cursor movement or page
publication.

## Channel Jump Consumer

`0x1280a` is the `ESC &l#V` consumer. It reads the absolute selector, current
VMI, current y, top offset, line-bound caches, and channel words from
`0x782dde`.

The modeled forward in-text path searches from the current line through
`0x1292a..0x1295c`, then commits the target through `0x12aa6..0x12af8`.
Fixture `ESC &l2V!` with channel 2 at line `1` moves y from `126` to `176`,
resets x from `40` to `10`, and queues `!` at compact coord `0xb001`.

The before-top path takes `0x128ae..0x128f4`. Fixture `ESC &l2V!` starting at
y `89` with top offset `90` normalizes the start line to `0`, finds channel 2
at line `1`, writes y `176`, and queues `!` at compact coord `0xb001`.

Selector zero computes the top-of-form target through `0x12966..0x12992`.
Fixture `ESC &l0V!` with y already `126` exits through `0x1295e` with x/y
unchanged and queues `!` at compact coord `0x9e02`.

## Page Boundary Paths

VFC can publish the current page before the next printable byte:

- Selector-zero page eject: `!\x1b&l0V!` takes `0x1299c..0x129c4`, publishes
  the old page at compact coord `0xbe02`, resets x/y to `10`/`126`, and
  queues the next `!` on a fresh page at compact coord `0x9001`.
- Wrap hit: `!\x1b&l2V!` starts at y `226`, wraps through
  `0x129c6..0x12af8`, publishes the old page at compact coord `0xde02`,
  lands at y `176`, and queues the next `!` at compact coord `0xb001`.
- Wrap no-hit: `!\x1b&l2V!` with no channel 2 takes `0x12a22..0x12a78`,
  publishes the old page at compact coord `0xde02`, returns to top-of-form
  y `126`, and queues the next `!` at compact coord `0x9001`.
- Target after text: `!\x1b&l2V!` with channel 2 only at line `63` takes
  `0x129ee..0x12b5a`, publishes the old page at compact coord `0x4e02`,
  recovers y to `104`, and queues the next `!` at compact coord `0x3001`.

VFC can also recover or wrap without publication:

- Before-top target-after-text starts at y `89`, takes `0x129fc..0x12afc`,
  skips publication at `0x12a12..0x12a1e`, writes y `104`, and queues `!` at
  compact coord `0x3001`.
- Empty-table start-after-text starts at y `3290`, takes
  `0x12a02..0x12afc`, writes y `54`, and queues `!` at compact coord
  `0x1001`.
- Default-table start-after-text starts at y `3290`, wraps to line `1`
  through `0x12a7a..0x12af8`, writes y `176`, and queues `!` at compact coord
  `0xb001`.
- Line-63 start-after-text starts at y `3290`, wraps to line `63` through
  `0x12a7a..0x12afc`, enters bottom recovery `0x12afc..0x12b5a`, writes
  y `104`, and queues `!` at compact coord `0x3001`.
- Selector-zero start-after-text starts at y `3290`, takes
  `0x1299c..0x12b92`, enters `0x12b5e..0x12b92`, writes top-of-form y `126`,
  and queues `!` at compact coord `0x9001`.

The direct high-start fixture uses start line `80` with `0x782ee0 = 62` and
`0x782ede = 100`, proving the same branch predicates away from the normal
Letter page bottom. Empty-table selector 2 writes recovered y `1104`; wrapped
selector 2 at line `70` writes recovered y `1604`; selector zero writes
top-of-form y `126`.

The `0x1280a` branch matrix for the fixture-backed paths is:

- `0x128ae..0x128f4`: before-top normalization. It rewrites the computed
  start line before the ordinary forward scan. It does not publish the current
  page by itself.
- `0x1292a..0x1295c` then `0x12aa6..0x12af8`: forward in-text hit. It resets
  x through `0xf06e`, flushes pending text through `0xf34a`, writes the target
  y, and leaves the next printable on the current page.
- `0x12966..0x1299a`: selector-zero target-equal exit. It computes the
  top-of-form target and leaves x/y unchanged when the cursor is already
  there.
- `0x1299c..0x129c4`: selector-zero page eject. It runs
  `0xf06e -> 0xf34a -> 0xf34a -> 0xf124`, publishes the old page, and leaves
  the next printable on a fresh page.
- `0x129c6..0x12af8`: wrap hit. It scans after wrapping to line `0`; when the
  wrapped hit is before the original start line, it publishes through
  `0xf124` before committing the target y.
- `0x129ee..0x12b5a`: publishing target-after-text recovery. It finds a channel
  after `0x782ee0`, publishes the old page, then recovers y through
  `0x12afc..0x12b5a`.
- `0x129fc..0x12afc`: non-publishing target-after-text recovery. It is the
  before-top sibling where start line `0` skips the `0xf124` edge and only
  recovers x/y.
- `0x12a02..0x12afc`: start-after-text no-wrap recovery. With no matching
  channel bit, it skips publication and writes the recovered y.
- `0x12a22..0x12a78`: wrap-no-hit page eject. With no matching bit through the
  forward and wrapped scans, it publishes the old page and returns to
  top-of-form y.
- `0x12a7a..0x12af8`: start-after-text wrapped in-text hit. It wraps from a
  start line past text bottom to an in-text channel and commits without
  publication.
- `0x12a7a..0x12afc`: start-after-text wrapped bottom recovery. It wraps to a
  line after `0x782ee0`, skips publication, and writes the recovered y.
- `0x1299c..0x12b92`: selector-zero start-after-text recovery. It skips the
  page-eject edge when the computed start line is already past text bottom and
  writes the top-of-form target.

## Writers

- `0x11f6e` schedules delayed payload handler `0x12cfe`.
- `0x12cfe` writes `0x782dde`, clears unused table bytes, derives `0x782dc2`,
  copies `0x782dd2`, and clears `0x782ee1`.
- `0x12b96` writes the default VFC table at `0x782dde`.
- `0xe5e2` is a shared page-layout refresh writer. It recomputes top offset,
  margins, cursor y, text-bottom cache, VFC line caches, default VFC table,
  modified-layout flag, and static secondary font context before later VFC or
  macro consumers run.
- `0xfe54` writes `0x782edf`, `0x782ee0`, and `0x782ede`.
- `0x1280a` writes cursor state through forward, wrap, recovery, and
  selector-zero paths.
- `0xf06e`, `0xf34a`, and `0xf124` reset x, flush pending text, and publish
  the current page on the modeled page-boundary paths.

## Readers And Consumers

- `0x1280a` consumes selector, VMI, top offset, current y, line-bound caches,
  and the VFC table.
- `0xe5e2` output is consumed by `0x1280a`, `0xf36c`, printable placement,
  and macro replay paths that need a refreshed default layout before rendering
  or publication.
- `0xf36c` consumes `0x782dc2` during vertical overflow/perforation handling.
- Printable text consumes the resulting x/y cursor state through `0xd04a` and
  page-record queueing.
- Page publication consumes the current page root through `0xf124` and
  `0xff1e` before the next printable byte allocates a fresh page root.

## Output Effect

VFC does not draw by itself. Its visible effects are:

- refreshing default layout state and VFC table through `0xe5e2` before later
  page-record producers consume the state;
- changing text-bottom cache after `ESC &l#W`;
- consuming delayed payload before later printable bytes;
- moving x/y before a printable byte is queued;
- publishing the current page when selector-zero, wrap, or target-after-text
  paths cross a page boundary.

The covered fixtures prove both non-publishing movement and publishing splits
where the pre-VFC printable remains renderable on the old page and the
post-VFC printable is queued on a fresh page.

The `0xe5e2` layout-refresh fixture has no immediate page-record output. Its
output effect is state preparation: normal-page refresh produces top offset
`pack12(90)`, text bottom `pack12(240)`, margins `0..240`, cursor y
`pack12(126)`, VFC limit `pack12(240)`, clears modified-layout state, and
rebuilds the default VFC table prefix listed above. Those fields are then read
by VFC jumps, vertical overflow handling, printable placement, and macro
layout replay.

The canonical output effects are fixture-backed as follows:

- `ESC &l4W 00 00 00 02 !`: delayed payload bytes are consumed by
  `0x12cfe` / `0xdace` before printable parsing resumes; `!` queues at
  compact coord `0x9001`.
- `ESC &l2V!`: `0x1280a` finds channel 2 at line `1`, resets x through
  `0xf06e`, writes y `176`, and queues `!` at compact coord `0xb001`.
- before-top `ESC &l2V!`: `0x128ae..0x128f4` normalizes y `89` against top
  offset `90`, then reaches the same line-1 output at compact coord
  `0xb001`.
- `ESC &l0V!`: `0x12966..0x1299a` computes the top-of-form target, leaves
  the already-matching cursor in place, and queues `!` at compact coord
  `0x9e02`.
- `!\x1b&l0V!`: `0x1299c..0x129c4` publishes the old compact-text page
  through `0xf124` / `0xff1e`, resets to top of form, and queues the next
  `!` on a fresh page at compact coord `0x9001`.
- `!\x1b&l2V!` wrap hit: `0x129c6..0x12af8` publishes the old page, wraps to
  line `1`, writes y `176`, and queues the next `!` at compact coord
  `0xb001`.
- `!\x1b&l2V!` wrap no-hit: `0x12a22..0x12a78` publishes the old page and
  returns to top-of-form output at compact coord `0x9001`.
- target-after-text `!\x1b&l2V!`: `0x129ee..0x12b5a` publishes the old page
  from bucket `198`, recovers y to `104`, and queues the next `!` at compact
  coord `0x3001`.
- non-publishing recovery fixtures cover before-top target-after-text,
  empty-table start-after-text, default-table wrap, line-63 recovery,
  selector-zero start-after-text, and the alternate high-start entries without
  adding a new page-root publication edge.

## Confidence

High for the `0x11f6e -> 0x12cfe` delayed payload boundary, lowercase
same-family preservation, table bytes, text-bottom cache effect, default-table
channel convention, forward in-text hits, before-top normalization,
selector-zero early exit, selector-zero page eject, wrap hit, wrap no-hit,
target-after-text publication, and start-after-text recovery paths. Each claim
is backed by named fixtures and disassembly ranges above.

Medium for the manual-facing names of the derived line-count fields
`0x782ede`, `0x782edf`, and `0x782ee0`.

## Reproduction Contract

A byte-stream renderer must preserve:

- delayed `ESC &l#W` record restoration, including lowercase `w...W`
  behavior;
- shared `0xe5e2` layout refresh when page/macro paths rebuild default VFC
  and static font-context state;
- `0xdace` payload-byte normalization during VFC table load;
- the `0x12cfe` payload-count branches: count `0` rebuilds the default table
  when VMI conversion succeeds, odd counts and counts larger than
  `2 * (0x782ede + 1)` drain through `0xdace` without installing a new table,
  counts up to `0x100` install byte-addressed table data and clear the
  remaining words, and larger accepted counts store only the first `0x100`
  bytes before draining the rest;
- the 128-word VFC table and selector-to-bit convention;
- VMI, top offset, current x/y, and line-bound caches before `ESC &l#V`;
- page-root existence and pending-text flush behavior around VFC jumps;
- the distinction between cursor-only recovery and page-publication paths;
- post-VFC printable queueing coordinates and page-root identity.

## Remaining Edges

- None remaining for the documented VFC table-definition and channel-jump
  command-family contract.
- Broader physical-output correlation is outside this ROM-local VFC contract.
  It can correlate the documented model with a device if physical samples ever
  exist, but it is not a parser, table, page-record, or render-dispatch
  dependency.
