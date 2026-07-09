# Publication Commands To ROM-Derived Page Rows

This note documents the shared publication command family that turns a queued
current page record into published records and ROM-derived row construction. It
covers:

- `ESC E`: software reset
- `FF`: form feed / page eject
- `ESC &l#A`: page size
- `ESC &l#P`: page length in lines and default-page branch
- `ESC &l#O`: orientation
- `ESC &l#H`: paper source
- `ESC &l#X` followed by `FF`: copies

The low-level allocator and bridge contract is in
[page-record-storage.md](page-record-storage.md). Reset-specific environment
rebuilds are in [reset-default-environment.md](reset-default-environment.md).

## Evidence

- `generated/disasm/ic30_ic13_main_parser_loop_011774.lst`
- `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`
- `generated/disasm/ic30_ic13_esc_e_reset_00cc52.lst`
- `generated/disasm/ic30_ic13_control_code_handlers_00f02c.lst`
- `generated/disasm/ic30_ic13_page_size_handler_00fc74.lst`
- `generated/disasm/ic30_ic13_page_length_handler_00f9e8.lst`
- `generated/disasm/ic30_ic13_orientation_handler_010220.lst`
- `generated/disasm/ic30_ic13_paper_source_handler_00ef62.lst`
- `generated/disasm/ic30_ic13_copies_handler_00eef0.lst`
- `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`
- `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`
- `generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`
- `tools/render_fixture_harness.py`, fixtures:
  - `publication streams tie parser handlers to page-record publication
    boundary`
  - `host-fetched publication streams reach parser and published rows`
  - `host-fetched publication streams preserve 0x1edc6 bridge contract`
  - `published page records feed 0x1ed84 and 0x1ef6a render entry`
  - `0x11774 parser path routes mixed publication streams`
  - `0x11774 parser path routes geometry publication streams`
  - `mixed printable/reset stream publishes page root after text`
  - `mixed printable/reset stream keeps pre-reset text rows renderable`
  - `mixed printable/reset page-record stream queues through 0x1387c before
    reset`
  - `mixed printable/reset page-record bridge keeps pre-reset rows renderable`
  - `mixed printable/reset page-record finalization publishes bridged record`
  - `addressed printable reset publishes rendered page record`
  - `mixed printable/reset publication records 0xff1e pool header defaults`
  - `host-fetched reset publication preserves 0xff1e pool header defaults`
  - `host-fetched ESC E clears missing page root without publication`
  - `mixed printable/FF page-record stream publishes queued text`
  - `mixed printable/FF page-record finalization publishes bridged record`
  - `addressed printable FF publishes rendered page record`
  - `mixed printable/paper-source page-record stream publishes queued text`
  - `mixed printable/copies/FF stream publishes copy count`
  - `mixed printable/page-size page-record stream publishes queued text before
    geometry change`
  - `mixed printable/page-size page-record finalization publishes bridged
    record`
  - `mixed printable/orientation page-record stream publishes queued text
    before landscape change`
  - `mixed printable/orientation page-record finalization publishes bridged
    record`
  - `addressed page geometry publications render page records`
  - `addressed paper-source and copies publications render page records`
  - `host-fetched FF geometry and paper-source publications preserve 0xff1e
    pool header defaults`
  - `host-fetched copies publication preserves 0xeef0 pool header word`
  - `mixed printable/copies/FF stream publishes copy count`
  - `0xeef0 ESC &l#X stores absolute clamped copy count`
  - `0xf9e8 ESC &l#P converts VMI lines to page length and selects internal
    page code`
  - `0xf9e8 ESC &l#P stream reaches page-length handler`
  - `mixed page-length stream refreshes cursor before printable page-record
    queue`

## Publication Owner Summary

This note owns the page-control boundary where parser-visible commands stop
mutating the current page root and publish a page/control record for later
rendering. It does not own object construction before the current root exists,
nor band rendering after the scheduler has selected the published record.

The publication route is:

- `0xd04a`, `0x12714`, `0x13070`, and `0x13386` / `0x133aa` queue page objects
  under current root `0x78297a`.
- Reset `0xcc52`, FF `0xf0f0`, page-size `0xfc74`, page-length `0xf9e8`,
  orientation `0x10220`, paper-source `0xef62`, VFC/page-eject helper
  `0xf124`, and no-room retry paths can call `0xf34a` and then `0xff1e`.
- `0xff1e` validates current root byte `+0x04`, optionally runs the macro
  overlay replay branch `0xff40..0xffb0`, composes header flags, marks the
  root published, writes pool head `0x780ea6`, sets publication flag
  `0x782996`, and clears current root pointer `0x78297a`.
- Scheduler and render handoff later consume that published pool state through
  `0x780eaa -> 0x780eae -> 0x1ed84 -> 0x1edc6 -> 0x1ef6a`.

Writers feeding this checkpoint:

- Object producers write current-root bucket/list/context fields before
  publication: compact text under `+0x1c`, spans under `+0x1c`, raster under
  `+0x1c`, rules under `+0x24`, fixed-list objects under `+0x28`, and context
  slots under `+0x2c..+0x68`.
- Page-control handlers write publication-adjacent state: line-termination
  byte `0x78318f`, copy count `0x782da4`, paper-source byte `0x782da6`,
  pending header bytes `0x782997` / `0x782998`, status byte `0x780e99`,
  orientation byte `0x782da3`, and geometry fields consumed by later objects.
- `0xff1e` writes published-root state: root byte `+0x04 = 2`, root header
  bytes `+0x07/+0x08/+0x0a/+0x0c`, pool head `0x780ea6`, publication flag
  `0x782996`, and cleared current root `0x78297a = 0`.

Readers and consumers:

- `0xff1e` consumes current root `0x78297a`, active-state byte `+0x04`,
  pending page/header bytes, copy/paper-source state, and macro overlay state
  `0x782a92` / `0x782a94`.
- The scheduler consumes published pool head `0x780ea6` and promotes records
  through `0x780eaa` and `0x780eae`.
- `0x1ed84` and `0x1edc6` consume the selected published page/control record
  and copy source roots `+0x1c/+0x24/+0x28/+0x2c..+0x68` into render roots
  `+0x18/+0x1c/+0x20/+0x24..+0x60`.
- `0x1ef6a` consumes the bridged render record; compact, segment, raster,
  rule, and fixed-list render helpers produce the ROM-derived rows.

Output effect:

- Publication creates no pixels by itself. It snapshots the current page/image
  object graph and header state so later scheduler/render code can select it.
- Reset, FF, page-size, orientation, paper-source, page-length default, VFC,
  and no-room paths are visible because they decide which already-queued
  objects are published before environment changes or page-eject state take
  effect.
- Missing-root reset is a no-publication outcome: `0xff1e` takes the no-root
  exit and clears current-root state without producing a published page.

Field classification:

- Canonical page/image state: current root `0x78297a`, root byte `+0x04`,
  bucket/list roots `+0x1c/+0x24/+0x28`, context slots `+0x2c..+0x68`,
  published pool head `0x780ea6`, scheduler cursors `0x780eaa/0x780eae`, and
  publication flag `0x782996`.
- Canonical page-control state: copy count `0x782da4`, paper-source byte
  `0x782da6`, orientation byte `0x782da3`, pending header bytes
  `0x782997/0x782998`, status byte `0x780e99`, and paper-source mirrors
  `0x780e8f/0x780e26`.
- Derived/cache state: refreshed page geometry, HMI/VMI, VFC caches,
  render-record roots, and band caches `0x783a20/0x783a22/0x783a28`.
- Parser scratch: six-byte command records and host-byte traces consumed by
  the command handlers before `0xff1e` runs.
- Firmware bookkeeping: allocator cursors `0x782a70/0x782a72/0x782a76`, root
  retry and overlay state, pending byte `0x782a6d`, status/service wait
  helper `0x9ac2`, and macro overlay frame helpers `0xe0a4` / `0xe4f4`.
- Hardware/external state: physical engine consumption after rendered band
  buffers, and board-facing timing for status/service events.
- Unknown: no ROM-local publication, bridge, or render-entry middle edge
  remains for the documented reset, FF, page-size, page-length, orientation,
  paper-source, copies, missing-root reset, and macro-overlay publication
  paths. Remaining work must change a named header flag, current-root field,
  overlay branch predicate, scheduler pool field, or render input.

Evidence is the sections below,
[page-record-storage.md](page-record-storage.md),
[active-render-scheduler.md](active-render-scheduler.md), and
[page-raster-imaging.md](page-raster-imaging.md#render-entry-owner-summary),
with disassembly listings `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`,
`generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`, and
`generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`.

## Field Groups

Canonical page-record fields:

- `0x78297a`: current page root consumed by `0xff1e`.
- Page root byte `+0x04`: publication state. `0x10084` creates active roots
  with `+4 = 1`; `0xff1e` publishes only roots whose byte `+4` is `1`, then
  writes `+4 = 2` before exposing the pool record through `0x780ea6`.
- Page root `+0x1c`: compact bucket array. The covered publication streams
  publish a compact Line Printer `!` object with prefix
  `00 00 00 00 00 00 00 01 20 00 01`.
- Page root `+0x2c`: context slot 0, preserved as `0x440946b4` in the covered
  host-fetched and addressed publication streams.
- `0x780ea6`: published page/control pool-record pointer written by `0xff1e`.
- `0x782996`: publication flag set by `0xff1e`.

Canonical command state:

- `0x78318f`: line-termination mode. In the FF stream, `ESC &k2G` sets the
  mode that makes FF apply CR-style horizontal reset before page eject.
- `0x782da4`: copy count. `0xeef0` writes it for `ESC &l#X`; `0xff1e`
  copies it into published pool-header word `+0x0c`.
- `0x782da6`: paper-source/environment byte. `0xef62` writes selector `2` as
  `0x80`, and the addressed fixture also mirrors it to `0x780e8f`.
- `0x782997`: pending page-size/page-length header flag. `0xfc74` and
  `0xf9e8` set it after committing a new page code or page length, and
  environment reset `0xcda2` can also set it from default state.
- `0x780e99`: status/header pending byte consumed by `0xff1e` when no
  page-size/page-length pending flag clears it first.
- `0x782998`: pending paper-source/layout header flag. `0xef62` sets it after
  paper-source selection, and environment reset `0xcda2` can also set it from
  default state. The addressed paper-source fixture pins it to `1` after
  selector `2`.
- `0x780e8f` / `0x780e26`: paper-source output/control bytes. The addressed
  paper-source fixture pins them to `0x80` and `1` after publication.
- `0x782da3`: orientation byte, written by `0x10220`.
- Page geometry fields updated by `0xfc74` and `0x10220`, including active
  page size, top offset, and page-change flag.

Canonical addressed publication fields:

- Reset stream `! ESC E`: one stream chunk at `0x00d08000`, ending with
  `0x782a70 = 0x00d6`, `0x782a72 = 0x00d08000`,
  `0x782a76 = 0x00d0802a`.
- FF stream `ESC &k2G! FF`: one stream chunk at `0x00d09000`, ending with
  `0x782a70 = 0x00d6`, `0x782a72 = 0x00d09000`,
  `0x782a76 = 0x00d0902a`.
- Page-size stream `! ESC &l1A`: one stream chunk at `0x00d0a000`, ending
  with `0x782a70 = 0x00d6`, `0x782a72 = 0x00d0a000`,
  `0x782a76 = 0x00d0a02a`.
- Orientation stream `! ESC &l1O`: one stream chunk at `0x00d0b000`, ending
  with `0x782a70 = 0x00d6`, `0x782a72 = 0x00d0b000`,
  `0x782a76 = 0x00d0b02a`.
- Paper-source stream `! ESC &l2H`: one stream chunk at `0x00d0c000`, ending
  with `0x782a70 = 0x00d6`, `0x782a72 = 0x00d0c000`,
  `0x782a76 = 0x00d0c02a`.
- Copies stream `! ESC &l2X FF`: one stream chunk at `0x00d0d000`, ending
  with `0x782a70 = 0x00d6`, `0x782a72 = 0x00d0d000`,
  `0x782a76 = 0x00d0d02a`.

Derived/cache fields:

- `0x783a20`, `0x783a22`, and `0x783a28`: render-band outputs produced by
  `0x1ef86` after `0x1ed84` / `0x1edc6` bridge the published record.
- Row SHA-256 values in selector and publication fixtures are check artifacts,
  not firmware state and not external printer-output evidence.
- Page-size/orientation active extents, text-bottom values, and top offsets
  are derived from command state and page-geometry tables.

Parser scratch:

- Host-fetched publication streams drain entirely from the modeled `0xa904`
  ring source and leave an empty ring.
- `0x11774` parser traces record the command handlers before publication; the
  parser records themselves are temporary inputs to those handlers.

Firmware bookkeeping:

- `0x782a70`, `0x782a72`, and `0x782a76` track the page-record stream chunk.
- `0x782990` is cleared after publication/reset paths as part of page-root
  bookkeeping.
- Publication pool-header state byte `+4` becomes `2`; environment/status
  header fields remain default for the covered reset/FF/geometry streams unless
  the copies command changes word `+0x0c`.
- Synthetic nonzero `0xff1e` header state copies pending status bits to
  `+8/+0x0a`, environment state to `+7/+0x0c`, and root word `+0x16` to
  `+0x1a`, while preserving the bucket root at `+0x1c`.

Hardware/external state:

- Physical engine timing after the rendered band leaves the ROM-visible render
  path is outside this publication-command checkpoint.

Unknown:

- No ROM-local publication, bridge, or render-entry field remains unknown for
  the covered reset, FF, page-size, orientation, paper-source, and copies
  streams. The remaining boundary is hardware/external engine timing after
  ROM-visible rendering, not parser or page-record behavior.

## Command Streams

The canonical parser-to-publication and publication-adjacent layout streams
are:

- `! ESC E`: handlers `0xd04a`, `0xcc52`; reset publishes queued text, then
  resets environment.
- `ESC &k2G! FF`: handlers `0xedf8`, `0xd04a`, `0xf0f0`; FF publishes queued
  text after line-termination CR behavior.
- `! ESC &l1A`: handlers `0xd04a`, `0xfc74`; page-size change publishes
  queued text before geometry update.
- `ESC &l66P!`: handlers `0xf9e8`, `0xd04a`; page length refreshes geometry
  and cursor state before the following printable queues.
- `! ESC &l0P`: handlers `0xd04a`, `0xf9e8`; the zero-parameter default-page
  branch can publish queued text before restoring default page state.
- `! ESC &l1O`: handlers `0xd04a`, `0x10220`; orientation change publishes
  queued text before landscape update.
- `! ESC &l2H`: handlers `0xd04a`, `0xef62`; paper-source change publishes
  queued text before source/output bytes.
- `! ESC &l2X FF`: handlers `0xd04a`, `0xeef0`, `0xf0f0`; copies word is
  stored before FF publication.

Fixtures `publication streams tie parser handlers to page-record publication
boundary` and `host-fetched publication streams reach parser and published
rows` exercise these handlers from modeled byte streams. Fixtures
`0x11774 parser path routes mixed publication streams` and `0x11774 parser path
routes geometry publication streams` record the parser table route for the
same command families.

## Publication Helper At 0xff1e

`0xff1e` is the shared current-root publication boundary:

- `0xff26..0xff40`: return after clearing `0x78297a` if there is no current
  page root or if current root byte `+4` is not `1`.
- `0xff40..0xffb0`: if page state byte `0x782a92` is `1`, root word `+0x14`
  bit `0` is clear, and macro/data-chain state at `0x782d7a` is nonempty,
  `0xff1e` calls `0xe0a4`, sets `0x782a92 = 2`, starts a data-chain frame
  through `0xe4f4`, runs parser loop `0x11774`, and ensures a fresh root
  through `0x10084` before continuing publication.
- `0xffb0..0xffcc`: select current root `A5`, clear root-adjacent bytes
  `0x78297e`, `0x782c72`, and `0x782c73`, clear root word `+0x18`, and copy
  root word `+0x16` to `+0x1a`.
- `0xffd2..0xfffe`: if pending byte `0x782997` is `1`, set root byte
  `+0x0a.0`, clear `0x780e99`, and clear `0x782997`.
- `0x10000..0x1001e`: if `0x780e99` is `1`, set root byte `+0x08 = 1`.
- `0x10020..0x1003e`: if pending paper/layout byte `0x782998` is `1`, set
  root byte `+0x0a.1` and clear `0x782998`.
- `0x10044..0x1005a`: copy environment byte `0x782da6` to root byte `+0x07`
  and copy count word `0x782da4` to root word `+0x0c`.
- `0x10060..0x10080`: mark root byte `+0x04 = 2`, publish root next pointer
  through `0x780ea6`, set publication flag `0x782996 = 1`, then branch to
  `0xffa2` to clear current root pointer `0x78297a`.

The helper does not construct pixels directly. It freezes the current page-root
record so the `0x1ed84` / `0x1edc6` bridge can later copy buckets, rule lists,
fixed lists, and context slots into a render record.

### Published Header Flags

The `0xff1e` header flag branches compose command-state bytes into published
page-root fields before the root is marked ready:

- Page-size and page-length changes set `0x782997 = 1` at `0xfd74` and
  `0xfb20`. Environment reset can also set it at `0xce2e`. The publication
  helper consumes it at `0xffd2..0xfffe`, sets root byte `+0x0a` bit `0`,
  clears `0x780e99`, and clears `0x782997`.
- If `0x780e99 == 1` remains set after the `0x782997` branch, `0xff1e`
  writes root byte `+0x08 = 1` at `0x10000..0x1001e`. The branch does not clear
  `0x780e99`; page-size, page-length, and reset paths clear that byte through
  `0xfd7c..0xfd88`, `0xfb28..0xfb34`, and `0xcf38..0xcf44`.
- Paper-source changes set `0x782998 = 1` at `0xf01c`. Environment reset can
  also set it at `0xce36`. The publication helper consumes it at
  `0x10020..0x1003e`, sets root byte `+0x0a` bit `1`, and clears `0x782998`.
- Every non-early publication copies environment byte `0x782da6` to root byte
  `+0x07` and copy count `0x782da4` to root word `+0x0c` at
  `0x10044..0x1005a`.

These fields are canonical page-header state, not rendered row data. They do
not change the bucket root at `+0x1c`; they change the published page/control
record that downstream page services and the render bridge receive alongside
the bucket, fixed-list, rule-list, and context-slot roots.

## Command Handler Boundaries

The publication-command handlers call the shared helper before mutating state
that belongs to the next page or environment:

- Reset `0xcc52..0xcc6e` calls `0xcc70`; `0xcc70..0xcc98` clears
  alternate/data mode when allowed, flushes pending text through `0xf34a`, calls
  `0xff1e`, and services status through `0x9ac2` before the broader reset
  rebuild continues.
- FF `0xf0f0..0xf122` optionally applies CR-style horizontal reset through
  `0xf06e` when line-termination byte `0x78318f.5` is set, flushes pending
  text through `0xf34a`, ensures a root through `0x10084`, calls `0xf124`, and
  sets pending byte `0x782a6d = 0xff`. Helper `0xf124..0xf172` calls `0xff1e`
  before computing the next top-of-form cursor position.
- Page size `0xfc74..0xfe52` rewinds the six-byte parser record, takes the
  absolute parameter, publishes through `0xf34a` / `0xff1e` on the explicit
  change path, maps accepted page-size selectors to page code `D5`, then
  rewrites page geometry and VFC-derived limits for the next page.
- Page length `0xf9e8..0xfc52` rewinds the six-byte parser record, takes the
  absolute line count, converts nonzero counts through current VMI
  `0x783160`, selects an internal page code from orientation-specific
  thresholds, sets pending header flag `0x782997`, writes page extent
  `0x782dba`, and refreshes geometry. Its zero-parameter branch flushes and
  publishes pending text through `0xf34a` / `0xff1e` before restoring default
  page length and paper-source output state for following pages.
- Orientation `0x10220..0x103e6` rewinds the parser record, rejects parameters
  `>= 2` and unchanged orientation, publishes through `0xf34a` / `0xff1e`, then
  writes `0x782da3` and rebuilds orientation-dependent geometry, VMI/HMI, font
  context, and VFC tables.
- Paper source `0xef62..0xf02a` rewinds the parser record, flushes and
  publishes through `0xf34a` / `0xff1e`, maps selector values through the ROM
  table at `0xef3a`, writes canonical paper-source byte `0x782da6`, and sets
  pending publication byte `0x782998 = 1`.
- Copies `0xeef0..0xef38` rewinds the parser record, takes the absolute
  parameter, clamps values above `99` to `99`, ignores zero, and writes
  `0x782da4`. It does not publish by itself; the following FF publication
  copies that word into root `+0x0c` at `0x10052`.

### Page Size Handler Details

`ESC &l#A` enters `0xfc74` with the parsed six-byte parameter record still in
the parser buffer. The handler does not interpret the host stream directly; it
rewinds `0x78299e` by six bytes at `0xfc82..0xfc8a`, reads parameter word
`+2`, sign-extends it, and converts negative values to their absolute value at
`0xfc90..0xfc9e`.

The command record byte at `(A4)` selects the default-page branch. When it is
zero, `0xfca0..0xfce6` flushes pending text through `0xf34a`, publishes the
current root through `0xff1e`, services status with `0x9ac2`, then compares
current environment byte `0x782da6` with output byte `0x780e8e`. If they differ,
it copies `0x782da6` to `0x780e8f` and signals control byte `0x780e26` through
`0x9b5e(0x780e26, 1)`. The default page code then comes from `0x780e97`; zero
falls back to page code `2` at `0xfcf4..0xfd02`.

The explicit selector ladder at `0xfce8..0xfd68` accepts these parameter to
page-code mappings:

- `1 -> 6`
- `2 -> 2`
- `3 -> 5`
- `0x1a -> 1`
- `0x50 -> 0x88`
- `0x51 -> 0x87`
- `0x5a -> 0x89`
- `0x5b -> 0x8a`

Any other explicit selector branches to the common return at `0xfe4c` without
rewriting geometry. Accepted explicit selectors call `0xf34a` and `0xff1e` at
`0xfd68..0xfd6e` before changing the page-size state for following output.

The geometry commit starts at `0xfd74`. It sets pending layout byte
`0x782997 = 1`, brackets a clear of `0x780e99` with `0x15a6` / `0x15ac`,
writes active page code `0x782da2 = D5`, then calls `0xf9ac` to refresh the
default page length. `0xfd98..0xfdf4` derives geometry words through ROM table
helpers: `0x9d4e` writes `0x782db2`, `0x9d16` writes `0x782db4`, the raster
origin fields rooted at `0x783170` are cleared, the row-byte limit at
`0x783180` is recomputed with `0x3324a`, `0x9e56` writes `0x782dc0`, and
`0xf87e` refreshes related layout state.

The final layout refresh at `0xfdfe..0xfe32` writes top offset
`0x782dce = 0x96 - 0x782dbe`, clears `0x782dd0`, and calls `0xea16`,
`0xe9ba`, `0xf8fc`, `0xfe54`, and `0x12b96`. The return path at
`0xfe38..0xfe52` clears macro/page state byte `0x782a92` unless it already
equals `2`.

### Page Length Handler Details

`ESC &l#P` enters `0xf9e8` with the parsed six-byte parameter record still in
the parser buffer. `0xf9e8..0xfa14` rewinds `0x78299e`, reads record word `+2`,
converts negative values to absolute values, and reads current VMI
`0x783160`. If VMI is zero, the handler exits without changing geometry,
publication state, or cursor placement.

For nonzero line counts, `0xfa26..0xfa48` multiplies current VMI by the line
count and converts the packed result to a whole-dot page extent. The selector
ladder at `0xfa48..0xfb18` compares that extent against
orientation-dependent thresholds: portrait checks `0x782daa`, `0x782dae`,
`0x782dac`, and `0x782db0`, selecting codes `6`, `2`, `1`, or `5`; landscape
checks `0x782daa`, `0x782dac`, and `0x782dae`, selecting codes `6`, `1`, or
`2`. Values beyond all thresholds return without changing page geometry.

The zero-parameter branch at `0xfa62..0xfaa6` is the publication-affecting
side of this handler. It flushes pending text through `0xf34a`, publishes the
current root through `0xff1e`, waits through `0x9ac2`, compares current
paper-source byte `0x782da6` with previous output byte `0x780e8e`, and when
they differ mirrors `0x782da6` to output byte `0x780e8f` and signals control
word `0x780e26` through `0x9b5e`.

The shared commit at `0xfb20..0xfb5a` sets pending layout byte
`0x782997`, brackets the update with `0x15a6` / `0x15ac`, writes internal page
code `0x782da2`, and either restores default page length through `0xf9ac`
for the zero branch or writes the computed extent to `0x782dba` for nonzero
selectors. If default code `0x780e97` is zero, the zero branch falls back to
page code `2`. The geometry refresh at `0xfb60..0xfc52` rewrites table-derived
geometry words, top offset `0x782dce`, text-bottom state, margins, and cursor
state through the same helpers consumed by later printable, raster, rectangle,
VFC, and publication paths.

### Orientation Handler Details

`ESC &l#O` enters `0x10220`. `0x10228..0x10244` rewinds the parser record by
six bytes, reads word `+2`, sign-extends it, and converts negative values to
their absolute value. `0x10246..0x1025a` rejects selectors `>= 2` and rejects
the command if the selector equals current orientation byte `0x782da3`.

For an accepted change, `0x1025c..0x10266` flushes pending text, publishes the
current page root, and writes the new orientation to `0x782da3`. The first
geometry pass at `0x1026c..0x10296` calls `0xf9ac` and `0xf87e`, recomputes
`0x782dce = 0x96 - 0x782dbe`, clears `0x782dd0`, and calls `0xea16` and
`0xe9ba`.

`0x1029c..0x10314` rebuilds VMI fixed-point state in `0x783160` from line-count
word `0x78219e`. The handler calls `0xcfea` to convert the word into a working
value. Values below `5` are clamped by calling `0xcf52(5)`, values above
`0x80` are clamped by calling `0xcf52(0x80)`, and in-range values use
`0x78219e` directly. All three paths pass the chosen value through `0x104d8`
before writing `0x783160`.

`0x10314..0x10330` refreshes cursor and form state through `0xf8fc`, `0xfe54`,
`0x12b96`, and threshold helper `0x103ea`, then calls `0x13eb8` for font
contexts `0` and `1`. The threshold helper at `0x103ea..0x10488` writes
`0x782daa`, `0x782dae`, `0x782dac`, and `0x782db0`, using portrait lookup
helper `0x9dbe` when `0x782da3 == 0` and landscape lookup helper `0x9d86`
otherwise.

The active font-context refresh starts at `0x1033c`. The selected context is
`0x782ee6 + 16 * 0x782f06`. If context byte `+4` is zero, `0x10360..0x1038a`
uses the fixed-record form: it copies font byte `+0x19` to `0x78318e` and
computes HMI `0x78315c` from `0x57e40 / word(+0x1a)` through `0x3324a` and
`0x104d8`. If context byte `+4` is nonzero, `0x1038c..0x103a2` uses the
offset-table form: it copies byte `+0x21` to `0x78318e`, reads pointer `+0x24`,
calls `0x10550`, and writes the resulting HMI to `0x78315c`.

`0x103a8..0x103e6` copies current font metric words `0x783144` and `0x783146`
to `0x782f08` and `0x782f0a`. If span byte `0x783184` is set, it clears that
byte and calls `0x126e2`. Like the page-size handler, the final return path
clears `0x782a92` unless it already equals `2`.

### Paper Source And Copies Details

`ESC &l#H` enters `0xef62`. `0xef6a..0xef8e` saves current source byte
`0x782da6` in `D5`, rewinds the parser record by six bytes, reads word `+2`,
sign-extends it, and converts negative selectors to absolute values.
`0xef90..0xefa8` flushes text, publishes the current root, refreshes cursor
state through `0xf8fc`, then dispatches through the ROM table at `0xef3a` with
helper `0x33298`.

The table routes selector `0` to `0xefae`, selector `1` to `0xefb6`, selector
`2` to `0xefe8`, selector `3` to `0xeff0`, and all other values to `0xeff8`.
The selector-zero path only services status through `0x9ac2` and returns.
Selector `1` sets `D5 = 0` and `0x782990 = 1`; selector `2` sets `D5 = 0x80`;
selector `3` sets `D5 = 0x90`; the default path loads `D5` from default source
byte `0x7821a2` and sets `0x782990 = 1`.

The common paper-source output path starts at `0xefc0`. It calls `0x9b1e`; if
that helper returns `D7 == 1`, `0xefce..0xefe4` copies `D5` to output byte
`0x780e8f` and signals control byte `0x780e26` through
`0x9b5e(0x780e26, 1)`. `0xf00a..0xf01c` protects the canonical write with
`0x15a6` / `0x15ac`, writes `0x782da6 = D5`, and sets pending publication byte
`0x782998 = 1`.

`ESC &l#X` enters `0xeef0`. `0xeef8..0xef14` rewinds the parser record by six
bytes, reads word `+2`, sign-extends it, and converts negative counts to their
absolute value. `0xef16..0xef32` clamps counts above `99` to `99`, ignores
zero, and writes nonzero in-range counts to `0x782da4`. The handler returns at
`0xef32..0xef38` without publishing; `0xff1e` later copies `0x782da4` into the
published page-root header word `+0x0c`.

## Writers

- `0xd04a` queues the printable `!` compact text object before each
  publication command.
- `0xcc52` handles reset and calls the reset publication path through `0xcc70`
  / `0xff1e`.
- `0xf0f0` handles FF and publishes the current root through `0xff1e`.
- `0xfc74` handles page size and publishes the current root before changing
  geometry, then sets pending header flag `0x782997`.
- `0xf9e8` handles page length. Nonzero values write `0x782dba` and
  `0x782997` before refreshing geometry; zero publishes pending text before
  restoring the default page code and paper-source output state.
- `0x10220` handles orientation and publishes the current root before changing
  orientation and active extents.
- `0xef62` handles paper source, publishing queued text and then writing
  paper-source state and pending header flag `0x782998`.
- `0xeef0` handles copies, storing the copy count that a following FF
  publication copies into pool-header word `+0x0c`.
- `0xff1e` writes the published pool record and clears the current page root.
- `0x1ed84` writes render-record header words from the selected published
  record; `0x1edc6` copies bucket roots and context slots into the render
  record.

## Readers And Consumers

- `0x11774` consumes the host byte stream and dispatches to the command
  handlers listed above.
- `0xff1e` consumes current page root `0x78297a`, page-root state byte `+4`,
  parser/page state `0x782a92`, pending header flags `0x782997` and
  `0x782998`, status/header byte `0x780e99`, and root bucket/context fields.
- `0x1ed84` and `0x1edc6` consume the published pool record and produce a
  render record.
- `0x1ef6a` consumes the render record in call order
  `0x1ef86 -> 0x1efc2 -> 0x1f446 -> 0x1f756`; the covered streams dispatch
  one compact bucket object to `0x1effe` with context slot `0`.

## Output Effect

The covered publication streams publish the compact Line Printer `!` object
queued before the publication command. The nonzero page-length stream is the
publication-adjacent sibling: it refreshes geometry and cursor state before
the following printable queues through the same compact text path. The ROM
path for streams that publish already queued text is:

```text
0xd04a -> 0x1387c/0x1381c page-root storage
       -> 0xff1e published root
       -> 0x1ed84/0x1edc6 render-record bridge
       -> 0x1ef6a compact bucket dispatch
       -> 0x1effe text/compact render helper
```

The named byte-stream and addressed examples exercise that path for reset, FF,
page-size, page-length zero/default, orientation, paper-source, and copies.
Their row digests are checks of the documented ROM-derived row construction,
not comparisons to external printer output.

The mixed page-record fixtures separate command side effects from visible
output. Reset queues `!` through `0x1387c` before `0xcc52` clears or rebuilds
environment state. FF publishes after the line-termination mode has reset the
horizontal cursor. Page-size and orientation publish the queued page before
installing new geometry. Page-length zero can publish before restoring default
page state, while nonzero page length changes later placement without drawing
immediately. Paper source publishes the queued page before setting
paper-source output/control bytes. Copies stores count `2` before FF
publication copies that value to pool-header word `+0x0c`.

The command-specific side effects are pinned at the same boundary:

- `! ESC &l1A` publishes the compact text object through the page-size
  handler's `0xf34a` / `0xff1e` edge before storing page code `6` and
  recomputing portrait geometry. The addressed variant uses stream chunk
  `0x00d0a000`.
- `ESC &l66P !` stores page extent `0x782dba = 3300`, selects internal page
  code `2`, marks pending layout byte `0x782997`, refreshes cursor placement,
  and queues the following `!` compact object at coordinate `0x9001`.
- `ESC &l0P` takes the default-page branch: it can publish pending text
  through `0xff1e`, mirror `0x782da6` to `0x780e8f`, signal `0x780e26`, and
  restore the default page code from `0x780e97` or fallback `2`.
- `! ESC &l1O` publishes the compact text object through the orientation
  handler's `0xf34a` / `0xff1e` edge before storing orientation `1` and
  switching to landscape geometry. The addressed variant uses stream chunk
  `0x00d0b000`.
- `! ESC &l2H` publishes before `0xef62` leaves selected value `0x80`,
  `0x782da6 = 0x80`, `0x782998 = 1`, `0x780e8f = 0x80`, and
  `0x780e26 = 1`. The addressed variant uses stream chunk `0x00d0c000`.
- `! ESC &l2X FF` stores `0x782da4 = 2` at `0xeef0`; the following FF
  publication through `0xf0f0` / `0xff1e` writes pool-header word
  `+0x0c = 2`. The addressed variant uses stream chunk `0x00d0d000`.
- The synthetic nonzero `0xff1e` header example records that non-default
  status/environment/root header fields can change without changing the compact
  bucket root consumed by the render bridge.

The missing-root reset example records the opposite output boundary:
`host-fetched ESC E clears missing page root without publication` reaches
handler `0xcc52`; `0xff1e` takes the `0xff26..0xff2c` no-root exit, clears the
current-root state at `0xffa2`, and does not create a published page record.

## Reproduction Contract

A byte-stream renderer must preserve:

- publication before reset, page-size, orientation, and paper-source side
  effects mutate the environment;
- page-length nonzero updates before later placement consumes `0x782dba`,
  `0x782da2`, and refreshed cursor state, plus page-length zero publishing
  pending text before restoring default page state;
- FF publication after line-termination mode has applied CR-style horizontal
  reset when `ESC &k2G` is active;
- copies state written by `0xeef0` before a later FF publication copies it
  into pool-header word `+0x0c`;
- paper-source selector `2` side effects after publication, including
  `0x782da6`, `0x782998`, `0x780e8f`, and `0x780e26`;
- non-default `0xff1e` status/environment/root header copies independently
  from the bucket root and rendered compact rows;
- missing-root reset with no publication;
- `0xff1e` pool-header defaults, publication flag, and current-root clearing;
- `0x1ed84` / `0x1edc6` bridge preservation of compact bucket and context
  slot state;
- ROM-derived compact row construction through the same render helpers for
  reset, FF, page-size, page-length, orientation, paper-source, and copies.

## Confidence

High for parser handler order, host-byte draining, page-record storage,
published pool headers, command side effects, render bridge fields, and render
entry call order because the claims are backed by handler ranges
`0xcc52..0xcc98`, `0xf0f0..0xf172`, `0xfc74..0xfe52`,
`0xf9e8..0xfc52`, `0x10220..0x103e6`, `0xef62..0xf02a`,
`0xeef0..0xef38`, publication helper `0xff1e..0x10080`, bridge helpers
`0x1ed84` / `0x1edc6`, and the named byte-stream examples.

Medium only for byte-stream variants that create a new publication-side field,
bucket shape, bridge state, placement state, or rendered row outside the
covered command streams listed above. Physical printer correlation and engine
timing remain outside this ROM-internal publication contract.

## Remaining Edges

- `0xff1e..0x1ed84`: final rows are ROM-derived for covered publication
  commands by tracing publication, bridge, and render helpers.
  Physical-device comparison is outside the current static ROM evidence
  standard and is not an oracle for these rows.
- No parser-to-publication or publication-to-render ROM middle edge remains for
  the covered reset, FF, page-size, page-length zero/default branch,
  orientation, paper-source, and copies streams. No parser-to-placement middle
  edge remains for the covered nonzero page-length stream. Additional ROM work
  should target streams that change page-record fields, command-specific
  pool-header words, bridge state, placement state, or row-construction inputs.
