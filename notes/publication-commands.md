# Publication Commands To Rendered Page Records

This note documents the shared publication command family that turns a queued
current page record into rendered rows. It covers:

- `ESC E`: software reset
- `FF`: form feed / page eject
- `ESC &l#A`: page size
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

## Field Groups

Canonical page-record fields:

- `0x78297a`: current page root consumed by `0xff1e`.
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
- `0x782998`: pending paper-source/layout refresh byte. The addressed
  paper-source fixture pins it to `1` after selector `2`.
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
- Row SHA-256 values in selector and publication fixtures are output evidence,
  not firmware state.
- Page-size/orientation active extents, text-bottom values, and top offsets
  are derived from command state and page-geometry tables.

Parser scratch:

- Host-fetched publication streams drain entirely from the modeled `0xa904`
  ring source and leave an empty ring.
- `0x11774` parser traces prove the command handlers before publication; the
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

The canonical parser-to-publication streams are:

- `! ESC E`: handlers `0xd04a`, `0xcc52`; reset publishes queued text, then
  resets environment.
- `ESC &k2G! FF`: handlers `0xedf8`, `0xd04a`, `0xf0f0`; FF publishes queued
  text after line-termination CR behavior.
- `! ESC &l1A`: handlers `0xd04a`, `0xfc74`; page-size change publishes
  queued text before geometry update.
- `! ESC &l1O`: handlers `0xd04a`, `0x10220`; orientation change publishes
  queued text before landscape update.
- `! ESC &l2H`: handlers `0xd04a`, `0xef62`; paper-source change publishes
  queued text before source/output bytes.
- `! ESC &l2X FF`: handlers `0xd04a`, `0xeef0`, `0xf0f0`; copies word is
  stored before FF publication.

Fixtures `publication streams tie parser handlers to page-record publication
boundary` and `host-fetched publication streams reach parser and published
rows` prove these handlers from modeled byte streams. Fixtures `0x11774 parser
path routes mixed publication streams` and `0x11774 parser path routes
geometry publication streams` pin the parser table route for the same command
families.

## Writers

- `0xd04a` queues the printable `!` compact text object before each
  publication command.
- `0xcc52` handles reset and calls the reset publication path through `0xcc70`
  / `0xff1e`.
- `0xf0f0` handles FF and publishes the current root through `0xff1e`.
- `0xfc74` handles page size and publishes the current root before changing
  geometry.
- `0x10220` handles orientation and publishes the current root before changing
  orientation and active extents.
- `0xef62` handles paper source, publishing queued text and then writing
  paper-source state.
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
  parser/page state `0x782a92`, and root bucket/context fields.
- `0x1ed84` and `0x1edc6` consume the published pool record and produce a
  render record.
- `0x1ef6a` consumes the render record in call order
  `0x1ef86 -> 0x1efc2 -> 0x1f446 -> 0x1f756`; the covered streams dispatch
  one compact bucket object to `0x1effe` with context slot `0`.

## Output Effect

All six covered publication streams render the same compact Line Printer `!`
rows from the pre-command printable byte. Fixture `published page records feed
0x1ed84 and 0x1ef6a render entry` asserts the full row set for reset, FF,
page-size, orientation, paper-source, and copies. The addressed fixtures
`addressed printable reset publishes rendered page record`, `addressed
printable FF publishes rendered page record`, `addressed page geometry
publications render page records`, and `addressed paper-source and copies
publications render page records` prove those rows after materialized
`0x1387c`/`0x1381c` storage and `0xff1e` publication.

The mixed page-record fixtures separate command side effects from visible
output. Reset queues `!` through `0x1387c` before `0xcc52` clears or rebuilds
environment state. FF publishes after the line-termination mode has reset the
horizontal cursor. Page-size and orientation publish the queued page before
installing new geometry. Paper source publishes the queued page before setting
paper-source output/control bytes. Copies stores count `2` before FF
publication copies that value to pool-header word `+0x0c`.

The command-specific side effects are pinned at the same boundary:

- `! ESC &l1A` publishes the compact text object through the page-size
  handler's `0xf34a` / `0xff1e` edge before storing page code `6` and
  recomputing portrait geometry. The addressed variant uses stream chunk
  `0x00d0a000`.
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
- The synthetic nonzero `0xff1e` header fixture proves non-default
  status/environment/root header fields can change without changing the
  compact bucket root used by these row fixtures.

The missing-root reset fixture proves the opposite output boundary:
`host-fetched ESC E clears missing page root without publication` reaches
handler `0xcc52`, clears the missing current-root state, and does not create a
published page record.

## Reproduction Contract

A byte-stream renderer must preserve:

- publication before reset, page-size, orientation, and paper-source side
  effects mutate the environment;
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
- the final rendered compact rows for reset, FF, page-size, orientation,
  paper-source, and copies.

## Confidence

High for parser handler order, host-byte draining, page-record storage,
published pool headers, command side effects, render bridge fields, render
entry call order, and final rows because each is fixture-pinned.

Medium only for byte-stream variants that create a new publication-side field,
bucket shape, bridge state, or rendered row outside the six command streams
listed above. Physical printer correlation and engine timing remain outside
this ROM-internal publication contract.

## Remaining Edges

- `0xff1e..0x1ed84`: final rows are fixture-backed for all six publication
  commands. Physical-device comparison is optional correlation outside the
  ROM-internal reproduction contract, not a required oracle.
- No parser-to-publication or publication-to-render ROM middle edge remains for
  the covered reset, FF, page-size, orientation, paper-source, and copies
  streams. Additional ROM work should target streams that change page-record
  fields, command-specific pool-header words, bridge state, or rendered rows.
