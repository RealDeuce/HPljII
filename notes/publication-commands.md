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
- `generated/analysis/ic30_ic13_pcl_command_map.md`
- `generated/disasm/ic30_ic13_parser_setup_handlers_011ea4.lst`
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

## Owner Summary

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
- Alternate/data page-environment rows suppress ordinary publication effects:
  uppercase `ESC &l#A/#C/#D/#E/#F/#H/#L/#O/#P/#T/#V/#X` rows in table
  `0x116f6` have no handler, while lowercase finals route only to `0x11f4c`.
  They do not call `0xfc74`, `0xcb00`, `0xc992`, `0xece2`, `0xea9e`,
  `0xef62`, `0xee64`, `0xf9e8`, `0x10220`, `0x1280a`, or `0xeef0`.
  `ESC E` remains active through reset handler `0xcc52`; VFC payload
  `ESC &l#W/w` remains a delayed payload exception owned by
  [vertical-forms-control.md](vertical-forms-control.md#owner-summary).
- `0xff1e` validates current root byte `+0x04`, optionally runs the macro
  overlay replay branch `0xff40..0xffb0`, composes header flags, marks the
  root published, writes pool head `0x780ea6`, sets publication flag
  `0x782996`, and clears current root pointer `0x78297a`.
- Scheduler and render handoff later consume that published pool state through
  `0x780eaa -> 0x780eae -> 0x1ed84 -> 0x1edc6 -> 0x1ef6a`, then
  object-class helpers write rows through the row-store primitives owned by
  [page-raster-imaging.md](page-raster-imaging.md#row-store-primitive-map).

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
  rule, and fixed-list render helpers produce the ROM-derived rows through the
  object-class row-store helpers documented in
  [page-raster-imaging.md](page-raster-imaging.md#row-store-primitive-map).

Output effect:

- Publication creates no pixels by itself. It snapshots the current page/image
  object graph and header state so later scheduler/render code can select it.
- Reset, FF, page-size, orientation, paper-source, page-length default, VFC,
  and no-room paths are visible because they decide which already-queued
  objects are published before environment changes or page-eject state take
  effect.
- Missing-root reset is a no-publication outcome: `0xff1e` takes the no-root
  exit and clears current-root state without producing a published page.
- Alternate/data page-environment rows have no immediate publication or render
  effect. They preserve parser/storage syntax for later replay, except for
  active exceptions such as `ESC E` reset and delayed VFC payload storage.

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
  Alternate/data page-environment records that end at blank rows or `0x11f4c`
  remain parser scratch only and do not become canonical page-control state.
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

### Publication State To Visible Consumer Map

This map composes reset, FF, page-environment, paper-source, copies, VFC page
eject, and no-room publication routes from parser-visible handlers to the
first render consumers of the published page/control record. It is the
page-boundary route for content already queued by text, span, raster, rule,
fixed-list, macro-overlay, or VFC owners.

- Publication-trigger writers:
  reset `0xcc52`, FF `0xf0f0`, page-size `0xfc74`, page-length `0xf9e8`,
  orientation `0x10220`, paper source `0xef62`, VFC/page-eject helper
  `0xf124`, and no-room retry paths can flush pending span state through
  `0xf34a` and then call `0xff1e`. Copies `0xeef0` writes copy count
  `0x782da4` for a later publication. These handlers decide which queued
  current-root content is finalized before environment or page-control state
  changes.
- Page-control state writers:
  page-control handlers write line-termination byte `0x78318f`, orientation
  `0x782da3`, copy count `0x782da4`, paper-source byte `0x782da6`, pending
  header bytes `0x782997/0x782998`, status byte `0x780e99`, and paper-source
  mirrors `0x780e8f/0x780e26`. These fields are either copied into published
  header state or consumed by later placement/environment owners.
- Publication boundary:
  `0xff1e` consumes current root `0x78297a`, root state byte `+0x04`,
  pending header/control fields, copy/paper-source state, and macro overlay
  state `0x782a92/0x782a94`. For an active root it writes root state
  `+0x04 = 2`, header bytes `+0x07/+0x08/+0x0a/+0x0c`, protected pool head
  `0x780ea6`, publication flag `0x782996`, and clears current root
  `0x78297a`. No-root reset takes the no-publication clear branch.
- Page-object consumers:
  the published source still contains the object graph built before
  publication: bucket root `+0x1c`, rule root `+0x24`, fixed root `+0x28`,
  and context slots `+0x2c..+0x68`. Publication itself does not interpret
  compact text, spans, raster objects, rules, fixed-list records, or context
  slots; those remain the consumers documented by the page-record and render
  owners.
- Scheduler and bridge consumers:
  scheduler promotion moves the published source through
  `0x780ea6 -> 0x780eaa -> 0x780eae`. `0x1ed84 -> 0x1edc6` copies source
  roots to render roots `+0x18/+0x1c/+0x20` and context slots to
  `+0x24..+0x60`. Only a capacity-approved active-loop branch calls
  `0x1ef6a`.
- Render consumers:
  `0x1ef6a` renders bucket-chain objects through `0x1efc2`, rule-list objects
  through `0x1f446`, and fixed-list objects through `0x1f756`. The final
  helper-to-row-store step is owned by
  [Row-Store Primitive Map](page-raster-imaging.md#row-store-primitive-map).
  Publication commands are therefore visible because they expose an existing
  page-object graph to scheduler/render code, not because reset, FF,
  page-size, paper source, or copies write pixels directly.
- No-output and alternate/data boundaries:
  missing-root reset has no published page record. Alternate/data
  page-environment rows in table `0x116f6` are blank or lowercase
  `0x11f4c` rows for ordinary `ESC &l` finals; they do not call page
  environment handlers or `0xff1e` except for active exceptions already owned
  by reset and delayed VFC payload storage.

State groups for this map:

- Canonical page/image state:
  current root `0x78297a`, root state byte `+0x04`, source roots
  `+0x1c/+0x24/+0x28`, context slots `+0x2c..+0x68`, published pool head
  `0x780ea6`, scheduler cursors `0x780eaa/0x780eae`, publication flag
  `0x782996`, and render roots copied by `0x1edc6`.
- Canonical page-control state:
  copy count `0x782da4`, paper-source byte `0x782da6`, orientation byte
  `0x782da3`, pending header bytes `0x782997/0x782998`, status byte
  `0x780e99`, pending page-eject byte `0x782a6d`, and paper-source mirrors
  `0x780e8f/0x780e26`.
- Derived/cache state:
  refreshed geometry, VMI/HMI-derived placement state, render-record roots,
  band caches `0x783a20/0x783a22/0x783a28`, and scheduler-selected active
  render pointer `0x783a18`.
- Parser scratch:
  six-byte command records consumed by `0xcc52`, `0xf0f0`, `0xfc74`,
  `0xf9e8`, `0x10220`, `0xef62`, and `0xeef0`; alternate/data `ESC &l`
  records that stop at blank or lowercase terminal rows remain parser scratch.
- Firmware bookkeeping:
  allocator cursors `0x782a70/0x782a72/0x782a76`, root retry state, macro
  overlay state `0x782a92/0x782a94`, wait helper `0x9ac2`, macro replay
  helpers `0xe0a4/e4f4`, scheduler cursors, and work-record alternation.
- Hardware/external and unknown:
  physical engine timing begins after ROM-visible rendered buffers exist. No
  ROM-local middle edge remains for the documented publication, bridge, or
  render-entry handoff. Remaining work must change a named current-root
  field, header flag, overlay predicate, scheduler pool field, bridge root,
  render input, or physical/MMIO boundary.

Evidence:
`generated/disasm/ic30_ic13_esc_e_reset_00cc52.lst`,
`generated/disasm/ic30_ic13_control_code_handlers_00f02c.lst`,
`generated/disasm/ic30_ic13_page_size_handler_00fc74.lst`,
`generated/disasm/ic30_ic13_page_length_handler_00f9e8.lst`,
`generated/disasm/ic30_ic13_orientation_handler_010220.lst`,
`generated/disasm/ic30_ic13_paper_source_handler_00ef62.lst`,
`generated/disasm/ic30_ic13_copies_handler_00eef0.lst`,
`generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`,
`generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`,
`generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`,
[Page Object To Visible Consumer
Map](page-record-storage.md#page-object-to-visible-consumer-map), and
[Scheduler Outcome Matrix](active-render-scheduler.md#scheduler-outcome-matrix).

## Publication Decision Checkpoint

This checkpoint composes the publication command family as branch decisions
over current-root state. It starts after parser dispatch reaches a
publication-adjacent command and ends either with a published page/control
record, a state-only update that affects a later publication, or an explicit
no-publication exit.

Decision rules:

- A command can publish only if current root `0x78297a` exists and root byte
  `+0x04` is active. `0xff1e` turns that root into a published pool record by
  writing root byte `+0x04 = 2`, updating pool head `0x780ea6`, setting
  publication flag `0x782996`, and clearing `0x78297a`.
- Reset `0xcc52` publishes queued content before rebuilding environment
  state. If no root exists, `0xff1e` takes the no-root exit and reset remains
  a state rebuild with no published page record.
- FF `0xf0f0` is an immediate page-eject publication. It first applies any
  line-termination CR-style reset from `0x78318f.5`, flushes pending spans
  through `0xf34a`, ensures a root, calls `0xf124 -> 0xff1e`, and leaves
  pending page-eject byte `0x782a6d = 0xff`.
- Page-size `0xfc74`, orientation `0x10220`, and paper-source `0xef62`
  publish the current root before changing geometry or source state. This
  preserves already-queued page objects under the old environment.
- Page-length `0xf9e8` has two distinct outcomes. Nonzero accepted values
  update page extent and derived geometry before later placement consumes the
  new state; selector zero can publish pending text, mirror paper-source state
  to `0x780e8f` / `0x780e26`, and restore default page code.
- Copies `0xeef0` does not publish by itself. It stores copy count
  `0x782da4`; a later FF or other publication copies that value into
  published pool-header word `+0x0c`.
- Macro overlay is a publication-time replay branch inside `0xff1e`, not a
  separate renderer. When overlay state `0x782a92` / `0x782a94` and root retry
  state permit it, `0xff1e` re-enters macro replay before exposing the final
  published root.
- After publication, the render route is shared: scheduler promotes
  `0x780ea6` through `0x780eaa` / `0x780eae`, `0x1ed84` selects the record,
  `0x1edc6` copies roots and context slots into the render record, and
  `0x1ef6a` walks bucket, rule, and fixed-list roots.

State classification:

- Canonical page/image state: current root `0x78297a`, root state byte
  `+0x04`, bucket/list roots `+0x1c/+0x24/+0x28`, context slots
  `+0x2c..+0x68`, published pool head `0x780ea6`, scheduler cursors
  `0x780eaa/0x780eae`, and publication flag `0x782996`.
- Canonical page-control state: copy count `0x782da4`, paper source
  `0x782da6`, orientation `0x782da3`, pending header bytes
  `0x782997/0x782998`, status byte `0x780e99`, and paper-source mirror fields
  `0x780e8f/0x780e26`.
- Derived/cache state: geometry refreshed by page-size, page-length, and
  orientation handlers; render-record roots from `0x1edc6`; and band caches
  populated by render entry.
- Parser scratch: six-byte command records and host bytes consumed by
  `0xcc52`, `0xf0f0`, `0xfc74`, `0xf9e8`, `0x10220`, `0xef62`, and `0xeef0`
  before `0xff1e` or later publication consumes their effects.
- Firmware bookkeeping: allocator cursors, root retry state, overlay replay
  state, pending byte `0x782a6d`, wait helper `0x9ac2`, and macro replay
  helpers `0xe0a4` / `0xe4f4`.
- Hardware/external state: physical engine timing begins after ROM-visible
  render buffers are produced; it is not a publication decision input for the
  documented byte streams.
- Unknown: new work belongs here only if it changes current-root state,
  header words, macro overlay predicates, pool/scheduler fields, bridge roots,
  or render helper inputs.

Evidence:

- Disassembly:
  `generated/disasm/ic30_ic13_esc_e_reset_00cc52.lst`,
  `generated/disasm/ic30_ic13_control_code_handlers_00f02c.lst`,
  `generated/disasm/ic30_ic13_page_size_handler_00fc74.lst`,
  `generated/disasm/ic30_ic13_page_length_handler_00f9e8.lst`,
  `generated/disasm/ic30_ic13_orientation_handler_010220.lst`,
  `generated/disasm/ic30_ic13_paper_source_handler_00ef62.lst`,
  `generated/disasm/ic30_ic13_copies_handler_00eef0.lst`,
  `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`,
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`, and
  `generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`.
- Supporting evidence names include `mixed printable/reset page-record
  finalization publishes bridged record`, `addressed printable FF publishes
  rendered page record`, `addressed page geometry publications render page
  records`, `addressed paper-source and copies publications render page
  records`, `host-fetched ESC E clears missing page root without publication`,
  and `published page records feed 0x1ed84 and 0x1ef6a render entry`.

## Publication Outcome Matrix

This matrix is the command-family contract for page-control bytes that can
freeze, clear, or modify the current page/image state. It starts after parser
dispatch reaches a publication-adjacent handler and ends at either state-only
environment change, no-publication clear, or the shared
`0xff1e -> 0x1ed84 -> 0x1edc6 -> 0x1ef6a` render handoff.

- Reset with active root:
  `ESC E` dispatches to `0xcc52`; reset helper `0xcc70` flushes pending text
  through `0xf34a`, calls `0xff1e` while current root `0x78297a` exists and
  root byte `+0x04` is active, waits through `0x9ac2`, then rebuilds
  environment state. Writers: `0xff1e` marks root byte `+0x04 = 2`, writes
  pool head `0x780ea6`, sets publication flag `0x782996`, and clears
  `0x78297a`. Output effect: queued pre-reset objects remain renderable on the
  published page; reset defaults affect later bytes.

- Reset with missing root:
  The same `0xcc52 -> 0xcc70 -> 0xff1e` route reaches the no-root/current-root
  clear exit when `0x78297a` is absent or inactive. Output effect: no
  published page/control record is produced, and no bridge or render entry is
  fed. Evidence: `host-fetched ESC E clears missing page root without
  publication`.

- FF page eject:
  FF reaches `0xf0f0`. It consumes line-termination mode `0x78318f`, applies
  CR-style horizontal reset when bit 5 is set, flushes pending spans through
  `0xf34a`, ensures or uses the active page root, calls `0xf124 -> 0xff1e`,
  and writes pending page-eject byte `0x782a6d = 0xff`. Output effect: the
  current page root is published before the next top-of-form state is used.

- Page-size and orientation changes:
  Page size `0xfc74` and orientation `0x10220` publish any active current root
  through `0xf34a -> 0xff1e` before writing the new page code, orientation
  byte `0x782da3`, and derived geometry fields. Output effect: queued objects
  are rendered under the old geometry; later objects use the new page geometry.

- Page-length changes:
  Page length `0xf9e8` has two visible outcomes. Accepted nonzero values
  refresh page extent, VMI-derived geometry, and cursor limits without
  immediate publication. Selector zero can publish pending text, mirror
  paper-source state to `0x780e8f` / `0x780e26`, and restore default page
  code. Output effect: nonzero values are state-only until later placement or
  publication; zero/default can be an immediate page boundary.

- Paper-source changes:
  Paper-source handler `0xef62` publishes any active current root before
  writing paper-source byte `0x782da6`, pending header byte `0x782998`, and
  paper-source output/control mirrors `0x780e8f` / `0x780e26`. Output effect:
  existing objects remain on the old published page, while later pages observe
  the new source/header state.

- Copies:
  Copies handler `0xeef0` stores absolute clamped copy count `0x782da4`.
  It does not publish by itself. A later publication, commonly FF, lets
  `0xff1e` copy `0x782da4` into published pool-header word `+0x0c`. Output
  effect: copies are a header effect on the next published page, not a page
  object or renderer.

- Macro overlay at publication:
  `0xff1e` tests overlay state `0x782a92` / `0x782a94` and root retry flag
  word `+0x14`. When enabled, it detours through `0xe0a4` / `0xe4f4` so
  overlay bytes replay through the ordinary parser before the final root is
  published. Output effect: overlay pixels come from ordinary command owners
  that run during the publication detour, not from a separate overlay
  renderer.

- Shared bridge/render handoff:
  After `0xff1e` publishes a valid root, scheduler pool fields
  `0x780ea6`, `0x780eaa`, and `0x780eae` feed `0x1ed84`. Bridge `0x1edc6`
  copies source roots `+0x1c/+0x24/+0x28/+0x2c..+0x68` into render roots
  `+0x18/+0x1c/+0x20/+0x24..+0x60`, and render entry `0x1ef6a` dispatches
  compact, raster, rule, and fixed-list objects. The selected object-class
  helper then writes current-band or fallback rows through the row-store
  primitives. Output effect: publication snapshots page/image state; pixel
  generation belongs to the render owners.

State grouping:

- Canonical page/image state: current root `0x78297a`, root byte `+0x04`,
  bucket/list/context roots `+0x1c/+0x24/+0x28/+0x2c..+0x68`, published pool
  head `0x780ea6`, scheduler cursors `0x780eaa/0x780eae`, and publication
  flag `0x782996`.
- Canonical page-control state: line-termination byte `0x78318f`, copy count
  `0x782da4`, paper-source byte `0x782da6`, orientation byte `0x782da3`,
  pending header bytes `0x782997` / `0x782998`, status byte `0x780e99`, and
  paper-source mirrors `0x780e8f` / `0x780e26`.
- Derived/cache state: refreshed page geometry, HMI/VMI and VFC caches,
  render-record roots from `0x1edc6`, and render-band caches
  `0x783a20/0x783a22/0x783a28`.
- Parser scratch: six-byte command records consumed by `0xcc52`, `0xf0f0`,
  `0xfc74`, `0xf9e8`, `0x10220`, `0xef62`, and `0xeef0`.
- Firmware bookkeeping: allocator cursors `0x782a70/0x782a72/0x782a76`,
  pending byte `0x782a6d`, wait helper `0x9ac2`, root retry and overlay
  state, and macro overlay helpers `0xe0a4` / `0xe4f4`.
- Hardware/external state: engine timing after ROM-visible render buffers.
- Unknown: no ROM-local publication, bridge, or render-entry middle edge is
  open for the documented reset, FF, page-size, page-length, orientation,
  paper-source, copies, missing-root, and overlay outcomes.

Evidence:

- Handler listings:
  `generated/disasm/ic30_ic13_esc_e_reset_00cc52.lst`,
  `generated/disasm/ic30_ic13_control_code_handlers_00f02c.lst`,
  `generated/disasm/ic30_ic13_page_size_handler_00fc74.lst`,
  `generated/disasm/ic30_ic13_page_length_handler_00f9e8.lst`,
  `generated/disasm/ic30_ic13_orientation_handler_010220.lst`,
  `generated/disasm/ic30_ic13_paper_source_handler_00ef62.lst`,
  `generated/disasm/ic30_ic13_copies_handler_00eef0.lst`, and
  `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`.
- Bridge/render listings:
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst` and
  `generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`.
- Field and object details: the field groups below, plus
  [page-record-storage.md](page-record-storage.md),
  [active-render-scheduler.md](active-render-scheduler.md), and
  [Render Entry Outcome
  Matrix](page-raster-imaging.md#render-entry-outcome-matrix).

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
- `0x782da6`: paper-source/environment byte. `0xef62` writes selector `1` as
  `0`, selector `2` as `0x80`, selector `3` as `0x90`, and other nonzero
  selectors from default byte `0x7821a2`. The addressed paper-source route
  can also mirror the selected byte to `0x780e8f`.
- `0x782997`: pending page-size/page-length header flag. `0xfc74` and
  `0xf9e8` set it after committing a new page code or page length, and
  environment reset `0xcda2` can also set it from default state.
- `0x780e99`: status/header pending byte consumed by `0xff1e` when no
  page-size/page-length pending flag clears it first.
- `0x782998`: pending paper-source/layout header flag. `0xef62` sets it after
  paper-source selection, and environment reset `0xcda2` can also set it from
  default state. The addressed paper-source route stores `1` after selector
  `2`.
- `0x780e8f` / `0x780e26`: paper-source output/control bytes. The addressed
  paper-source route stores `0x80` and `1` after publication.
- `0x782da3`: orientation byte, written by `0x10220`.
- Page geometry fields updated by `0xfc74` and `0x10220`, including active
  page size, top offset, and page-change flag.

### Publication Header Field Matrix

This matrix is the byte/word contract for the page/control header that
`0xff1e` writes after it accepts active current root `0x78297a` with root byte
`+0x04 == 1`. It starts at `0xffb0`, after the no-root and overlay-detour
predicates have resolved, and ends at the branch back to the current-root
clear path `0xffa2`.

- Root byte `+0x04`:
  writer `0x10066`; source literal `2`; marks the root as published before
  exposing it through the pool.
- Root byte `+0x07`:
  writer `0x1004a`; source paper-source byte `0x782da6`; records the
  page/control source value consumed by later status/scheduler paths.
- Root byte `+0x08`:
  writer `0x10012`; source status pending byte `0x780e99 == 1`; records a
  status/header condition when no page-size flag consumed it first.
- Root word/flags `+0x0a` bit `0`:
  writer `0xffe6`; source page-size/page-length pending byte
  `0x782997 == 1`; records pending page geometry change and clears
  `0x780e99` / `0x782997`.
- Root word/flags `+0x0a` bit `1`:
  writer `0x10032`; source paper-source pending byte `0x782998 == 1`;
  records pending paper-source/layout change and clears `0x782998`.
- Root word `+0x0c`:
  writer `0x10052`; source copy count `0x782da4`; carries `ESC &l#X` state
  into the published pool header.
- Root word `+0x18`:
  writer `0xffc8`; source literal zero; clears transient header state before
  publication.
- Root word `+0x1a`:
  writer `0xffcc`; source root word `+0x16`; preserves the source root's
  companion header word.
- Pool head `0x780ea6`:
  writer `0x1006c`; source root link longword `(A5)`; exposes the published
  record to scheduler selection.
- Publication flag `0x782996`:
  writer `0x10078`; source literal `1`; tells later code that a page/control
  record was published.
- Current root `0x78297a`:
  writer `0xffa2` via `0x10080`; source clear; ends parser-time ownership of
  this page image.

State grouping:

- Canonical page/control state:
  root `+0x04/+0x07/+0x08/+0x0a/+0x0c/+0x18/+0x1a`, pool head
  `0x780ea6`, and publication flag `0x782996`.
- Canonical command inputs:
  `0x782da4`, `0x782da6`, `0x782997`, `0x782998`, and `0x780e99`.
- Firmware bookkeeping:
  critical-section helpers `0x15a6` / `0x15ac`, current-root clear path
  `0xffa2`, and macro overlay detour state resolved before this matrix.
- Parser scratch:
  none. Parser command records have already been consumed by reset, FF,
  page-size, page-length, paper-source, copies, or other publication callers.
- Hardware/external state:
  none at this header-copy boundary.
- Unknown:
  manual-facing names for some header bits remain unknown, but the ROM writer,
  input byte, and later publication/scheduler visibility are documented.

Evidence:

- `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`:
  `0xffb0..0x10080`.
- `generated/disasm/ic30_ic13_copies_handler_00eef0.lst`:
  `0xeef0..0xef38` for copy-count source `0x782da4`.
- Fixture evidence:
  `mixed printable/copies/FF stream publishes copy count`,
  `host-fetched copies publication preserves 0xeef0 pool header word`,
  `mixed printable/reset publication records 0xff1e pool header defaults`,
  `host-fetched FF geometry and paper-source publications preserve 0xff1e
  pool header defaults`, and the synthetic nonzero `0xff1e` header fixture
  referenced below.

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

### Publication Header Copy Checkpoint

This checkpoint composes the header part of `0xff1e`. It starts after a
current root has survived the active-root test at `0xff26..0xff3e`, and ends
when `0x10060..0x10080` exposes the source record through published pool head
`0x780ea6`.

Writers:

- Page-size `0xfc74..0xfd88`, page-length `0xf9e8..0xfb34`, and reset
  environment helper `0xcda2` write pending page/header byte `0x782997`.
  The page-size and page-length commits also clear `0x780e99` after setting
  that pending byte.
- Reset/status paths can leave `0x780e99` as a pending header/status byte.
  `0xff1e` consumes it only if the earlier `0x782997` branch did not clear it.
- Paper-source `0xef62..0xf020` and reset environment helper `0xcda2` write
  pending paper/layout byte `0x782998`.
- Copies `0xeef0..0xef38` writes canonical copy count `0x782da4`; reset
  environment reload can also seed it from default byte `0x78219d`.
- Paper-source `0xef62..0xf020`, reset environment reload, and page-control
  default branches write page-environment byte `0x782da6`.
- The normal publication body at `0xffb0..0x10080` writes the root header:
  clear `+0x18`, copy `+0x16` to `+0x1a`, update `+0x07`, `+0x08`,
  `+0x0a`, `+0x0c`, mark `+0x04 = 2`, write `0x780ea6`, set
  `0x782996 = 1`, and clear current root `0x78297a`.

Readers and consumers:

- `0xffd2..0xfffe` reads `0x782997`. When it is `1`, the helper brackets the
  update with `0x15a6` / `0x15ac`, sets root byte `+0x0a.0`, clears
  `0x780e99`, and clears `0x782997`.
- `0x10000..0x1001e` reads remaining `0x780e99`. When it is `1`, the helper
  writes root byte `+0x08 = 1` without clearing `0x780e99`.
- `0x10020..0x1003e` reads `0x782998`. When it is `1`, the helper brackets
  the update with `0x15a6` / `0x15ac`, sets root byte `+0x0a.1`, and clears
  `0x782998`.
- `0x10044..0x1005a` always copies `0x782da6` to root byte `+0x07` and
  `0x782da4` to root word `+0x0c` before the root is exposed.
- The scheduler and render bridge consume the published root after
  `0x10060..0x10080`: scheduler state selects the pool record through
  `0x780eaa` / `0x780eae`, and `0x1ed84 -> 0x1edc6` copies the source header,
  bucket roots, rule/fixed roots, and context slots into render-work fields.

Output effect:

- Header publication changes which page/control metadata travels with the page
  object graph; it does not draw pixels by itself.
- Copy count affects the published pool header word `+0x0c`, as shown by
  `! ESC &l2X FF`: `0xeef0` stores `0x782da4 = 2`, and the later FF
  publication copies `2` to root `+0x0c`.
- Page-size/page-length/reset pending byte `0x782997` and paper-source/reset
  pending byte `0x782998` become root byte `+0x0a` bits before render
  scheduling can see the record.
- The compact, raster, rule, and fixed-list pixel effects still come from
  object roots such as `+0x1c`, `+0x24`, and `+0x28`; this checkpoint only
  records the root-header state carried alongside those roots.

Field classification:

- Canonical page/control state: `0x782997`, `0x780e99`, `0x782998`,
  `0x782da6`, `0x782da4`, root header bytes `+0x04`, `+0x07`, `+0x08`,
  `+0x0a`, root words `+0x0c`, `+0x16`, `+0x18`, `+0x1a`,
  published pool head `0x780ea6`, and publication flag `0x782996`.
- Derived/cache state: render-work header and root copies made later by
  `0x1ed84` / `0x1edc6`.
- Parser scratch: six-byte page-control command records already consumed by
  `0xfc74`, `0xf9e8`, `0xef62`, `0xeef0`, or reset before `0xff1e` reads the
  canonical fields.
- Firmware bookkeeping: `0x15a6` / `0x15ac` protection around root-header
  writes, transient root-adjacent bytes `0x78297e`, `0x782c72`, `0x782c73`,
  and current-root pointer `0x78297a`.
- Unknown: no ROM-local field owner remains unknown for the listed header
  bytes. New work belongs here only if it finds another writer to these fields
  or another root-header consumer before `0x1ed84`.

Evidence:

- Disassembly:
  `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`,
  `generated/disasm/ic30_ic13_page_size_handler_00fc74.lst`,
  `generated/disasm/ic30_ic13_page_length_handler_00f9e8.lst`,
  `generated/disasm/ic30_ic13_paper_source_handler_00ef62.lst`,
  `generated/disasm/ic30_ic13_copies_handler_00eef0.lst`, and
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`.
- Generated note:
  `generated/analysis/ic30_ic13_page_root_finalization.md` state-reference
  scan for `0x782997`, `0x780e99`, `0x782998`, `0x782da6`, `0x782da4`,
  `0x780ea6`, and `0x782996`.
- Supporting evidence names:
  `0xff1e-modeled publication copies status and environment header fields`,
  `host-fetched FF geometry and paper-source publications preserve 0xff1e
  pool header defaults`, `host-fetched reset publication preserves 0xff1e
  pool header defaults`, and
  `host-fetched copies publication preserves 0xeef0 pool header word`.

Unresolved boundary:

- No current ROM-local middle edge remains between the documented page-control
  field writers and the `0xff1e` header copies. The next useful unresolved
  work in this family must change an exact writer, root-header bit/word,
  scheduler-selected pool record, or `0x1ed84` consumer.

### Representative Parsed-Stream Outcomes

This checkpoint composes the parser-visible publication examples into the
semantic page-record model. The low-level ledger above remains the
authoritative field contract; this section is the reader-facing route from
byte stream to published record and render entry.

Common setup:

- Printable `!` reaches `0xd04a`, then the compact-object path queues one text
  object through `0x1393a`, `0x12f2e`, `0x1387c`, and `0x1381c` under the
  current page-root bucket array `+0x1c`.
- Publication commands that call `0xff1e` publish that current root only if
  `0x78297a` is nonzero and root byte `+0x04 == 1`. The publication body marks
  root byte `+0x04 = 2`, writes the pool head to `0x780ea6`, sets
  `0x782996 = 1`, and clears `0x78297a`.
- Render entry then treats the published record as the source record:
  `0x1ed84` selects it, `0x1edc6` copies source roots and context slots into
  render-work fields, and `0x1ef6a` dispatches bucket contents through
  `0x1efc2 -> 0x1effe -> 0x1f034 -> 0x1f354` to the selected compact
  row-copy helper.

Stream outcomes:

- `! ESC E`: parser routes `!` to `0xd04a` and reset to `0xcc52`. Reset calls
  `0xff1e` before rebuilding the environment, so the queued compact text object
  is published with the old root. The generated reset checkpoint records the
  header after publication as root byte `+0x04 = 2`, default environment byte
  `+0x07`, status bytes `+0x08/+0x0a`, copy word `+0x0c`, cleared word
  `+0x18`, copied word `+0x1a`, and published pointer `0x780ea6`.
- `ESC &k2G ! FF`: line-termination handler `0xedf8` sets mode field
  `0x78318f`; printable `!` queues compact text; FF handler `0xf0f0` applies
  the mode-2 CR-style horizontal reset before page eject and then publishes the
  queued root through `0xff1e`.
- `! ESC &l1A` and `! ESC &l1O`: page-size `0xfc74` and orientation
  `0x10220` publish the current root before committing new geometry. The
  visible object graph for the already-queued `!` therefore travels with the
  old root through `0xff1e`, `0x1ed84`, `0x1edc6`, and `0x1ef6a`; later bytes
  consume the refreshed geometry fields documented in `Page Geometry Refresh
  Checkpoint`.
- `! ESC &l2H`: paper-source handler `0xef62` rewinds the parser record,
  parses selector `2`, publishes the existing root at `0xef96`, refreshes
  cursor state through `0xf8fc`, selects value `0x80` at `0xefe8`, may mirror
  it to output/control bytes `0x780e8f = 0x80` and `0x780e26 = 1` through
  `0x9b1e` / `0x9b5e`, then writes canonical `0x782da6 = 0x80` and pending
  flag `0x782998 = 1`. The publication triggered inside `0xef62` carries the
  pre-change compact root; the new paper-source byte is canonical state for
  following publications.
- `! ESC &l2X FF`: copies handler `0xeef0` rewinds the parser record, stores
  nonzero count `2` in `0x782da4`, and returns without publication. The later
  FF through `0xf0f0 -> 0xff1e` copies `0x782da4` into published root word
  `+0x0c = 2`, so the copy count travels as page/control metadata alongside
  the compact bucket root.

Field grouping for these examples:

- Canonical state: current root `0x78297a`, bucket root `+0x1c`, published
  pool head `0x780ea6`, publication flag `0x782996`, line-termination mode
  `0x78318f`, paper-source byte `0x782da6`, pending paper-source flag
  `0x782998`, and copy count `0x782da4`.
- Derived/cache state: render-work root copies and band fields produced after
  `0x1ed84` / `0x1edc6`; page-geometry caches refreshed by page-size,
  orientation, and paper-source helpers.
- Parser scratch: the six-byte command records rewound by `0xef62` and
  `0xeef0`, plus the consumed command records for reset, FF, page-size, and
  orientation.
- Firmware bookkeeping: allocator stream fields `0x782a70`, `0x782a72`,
  `0x782a76`, transient root bytes cleared by `0xff1e`, and the protected
  write brackets `0x15a6` / `0x15ac`.
- Hardware/external state: `0x780e8f` and `0x780e26` are ROM-visible
  paper-source output/control bytes, but their physical engine meaning remains
  outside this parser-to-page-record route.

Evidence:

- Handler disassembly:
  `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`,
  `generated/disasm/ic30_ic13_esc_e_reset_00cc52.lst`,
  `generated/disasm/ic30_ic13_page_size_handler_00fc74.lst`,
  `generated/disasm/ic30_ic13_orientation_handler_010220.lst`,
  `generated/disasm/ic30_ic13_paper_source_handler_00ef62.lst`,
  `generated/disasm/ic30_ic13_copies_handler_00eef0.lst`,
  `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`,
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`, and
  `generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`.
- Supporting generated checkpoints:
  `generated/analysis/ic30_ic13_renderer_fixture_harness.md` section
  beginning "A ROM parser trace now anchors the publication streams" and
  `generated/analysis/ic30_ic13_page_root_finalization.md`.

Unresolved boundary:

- No ROM-local middle edge remains for these six stream examples between the
  parsed command handlers, `0xff1e` publication, and `0x1ed84` render-entry
  bridge. Future publication work must name a new stream whose parsed handler
  changes a different root header byte/word, root list, context slot, scheduler
  selection, or render helper input.

### Page Environment Outcome Matrix

This matrix is the publication owner for parser-dispatched page-environment
commands that either publish the current root, change geometry for later
objects, or stage header state for a later publication. It composes the
`ESC &l` page-size, page-length, orientation, paper-source, and copies family
with reset/FF publication timing and the shared `0xff1e` root finalizer.

- Missing-root publication:
  `0xff1e` exits at `0xff26..0xff2c` when current root `0x78297a` is zero.
  Reset `0xcc52` can still clear current-root state, but no pool record,
  render record, or compact bucket dispatch is created.
- Current-root publication:
  reset `0xcc52`, FF `0xf0f0`, page-size accepted/default paths, page-length
  zero/default or accepted nonzero paths, orientation changes, and
  paper-source `0xef62` all reach `0xf34a -> 0xff1e` before their post-command
  state belongs to the next page. `0xff1e` requires root byte `+0x04 == 1`,
  then writes root byte `+0x04 = 2`, updates pool head `0x780ea6`, sets
  publication flag `0x782996`, and clears current root `0x78297a`.
- Page-size no-op:
  invalid explicit selectors in `0xfce8..0xfd68` return through
  `0xfe4c..0xfe52` without geometry writes or publication. Accepted selectors
  first publish any old root at `0xfd68..0xfd6e`, then set pending layout byte
  `0x782997`, clear status/header byte `0x780e99`, write page code
  `0x782da2`, and refresh geometry for later consumers.
- Page-length no-op:
  `0xf9e8..0xfa24` exits without publication or geometry writes when VMI
  `0x783160` is zero. Nonzero extents that miss the orientation threshold
  ladder at `0xfa48..0xfb18` also return without changing the page model.
- Page-length geometry change:
  accepted nonzero `ESC &l#P` publishes any old root at `0xfb0a..0xfb16`,
  writes page code `0x782da2`, page extent `0x782dba`, pending layout byte
  `0x782997`, and refreshed cursor/margin/VFC state. The visible effect is
  delayed until a later printable, raster, rectangle, VFC, or publication path
  consumes the refreshed fields.
- Page-length default branch:
  zero `ESC &l0P` publishes pending text at `0xfa62..0xfaa6`, may mirror
  paper-source state to `0x780e8f` and signal `0x780e26`, then restores the
  default page code from `0x780e97` or fallback code `2`.
- Orientation no-op:
  `0x10246..0x1025a` rejects selectors `>= 2` and unchanged orientation
  without publishing or rewriting geometry. Accepted changes publish the old
  root at `0x1025c..0x10266`, write orientation byte `0x782da3`, refresh
  geometry, VMI/HMI, VFC tables, and selected font metrics for later objects.
- Paper-source state:
  `0xef62` publishes any current root before table dispatch. Selector `0`
  then only services status; selectors `1`, `2`, `3`, and default write or
  derive canonical paper-source byte `0x782da6`, set pending flag
  `0x782998`, and may mirror output/control bytes `0x780e8f` / `0x780e26`.
- Copies state:
  `0xeef0` clamps nonzero counts to `1..99` and writes copy count
  `0x782da4` without publishing. A later `0xff1e` copies that count into
  published root word `+0x0c`; count zero returns without changing the field.
- Bridge/render consumer:
  `0x1ed84` selects the published source record, `0x1edc6` copies bucket roots
  and context slots into render-work fields, and `0x1ef6a` dispatches compact,
  rule, fixed, and raster roots to their row-store helpers. Page-environment
  commands do not draw pixels directly; they either publish already queued
  objects or mutate state that later object producers consume.

Field grouping for this route:

- Canonical state:
  current root `0x78297a`, root state byte `+0x04`, published pool head
  `0x780ea6`, publication flag `0x782996`, page code `0x782da2`,
  orientation `0x782da3`, copy count `0x782da4`, paper-source byte
  `0x782da6`, page extent `0x782dba`, active extents
  `0x782db6/0x782db8`, margins `0x782dd6/0x782dda`, cursor
  `0x782c8a/0x782c8e`, VMI/HMI `0x783160/0x78315c`, and bucket/context roots
  copied by the bridge.
- Derived/cache state:
  pending header flags `0x782997/0x782998`, status/header byte `0x780e99`,
  table words `0x782db2/0x782db4`, phase word `0x782dc0`, text-bottom cache
  `0x782dd2`, VFC caches `0x782ede/0x782edf/0x782ee0`, orientation threshold
  words `0x782daa/0x782dac/0x782dae/0x782db0`, and render-work copies from
  `0x1ed84` / `0x1edc6`.
- Parser scratch:
  rewound six-byte command records consumed by `0xfc74`, `0xf9e8`,
  `0x10220`, `0xef62`, and `0xeef0`; normal reset and FF records are consumed
  before `0xff1e`.
- Firmware bookkeeping:
  protected write brackets `0x15a6` / `0x15ac`, macro/page state
  `0x782a92`, pending page-eject byte `0x782a6d`, allocator state behind
  page-root buckets, and publication/active-pool cursors.
- Hardware/external state:
  `0x780e8f` and `0x780e26` are ROM-visible paper-source output/control bytes;
  their physical engine meaning is outside this ROM-local route.
- Unknown:
  no ROM-local middle edge remains for the documented missing-root, reset, FF,
  page-size, page-length, orientation, paper-source, copies, publication,
  bridge, and render-entry outcomes. Future publication work starts only from
  a stream that changes a field above, a root topology, a bridge copy, or a
  render-helper input.

Evidence:
`generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`
`0xff1e..0x10080`,
`generated/disasm/ic30_ic13_page_size_handler_00fc74.lst`
`0xfc74..0xfe52`,
`generated/disasm/ic30_ic13_page_length_handler_00f9e8.lst`
`0xf9e8..0xfc52`,
`generated/disasm/ic30_ic13_orientation_handler_010220.lst`
`0x10220..0x103e6`,
`generated/disasm/ic30_ic13_paper_source_handler_00ef62.lst`
`0xef62..0xf02a`,
`generated/disasm/ic30_ic13_copies_handler_00eef0.lst`
`0xeef0..0xef38`,
`generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`
`0x1ed84..0x1ee0e`, fixtures
`host-fetched ESC E clears missing page root without publication`,
`host-fetched FF geometry and paper-source publications preserve 0xff1e pool
header defaults`, `host-fetched copies publication preserves 0xeef0 pool
header word`, `0xf9e8 ESC &l#P stream reaches page-length handler`,
`mixed page-length stream refreshes cursor before printable page-record
queue`, and `addressed paper-source and copies publications render page
records`.

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

### Page-Length Nonzero Placement Checkpoint

This checkpoint isolates the nonzero `ESC &l#P` path because it affects pixels
without drawing or necessarily publishing at the command boundary. It starts
with parser dispatch to `0xf9e8` and ends when the next printable byte consumes
the refreshed geometry and queues a compact page object.

Dataflow:

- Parser dispatch selects handler `0xf9e8` for `ESC &l#P`. The handler rewinds
  `0x78299e` by six bytes at `0xf9f6..0xf9fe`, reads record word `+2`, and
  uses the absolute value as the line count.
- `0xfa14..0xfa24` exits if VMI `0x783160` is zero. This is a no-state-change,
  no-publication boundary for nonzero parameters.
- `0xfa2a..0xfa46` multiplies current VMI by the line count, runs the packed
  result through `0x104fe`, `0x332ee`, and `0x104d8`, and shifts the result
  down to a whole-dot extent in `D4`.
- `0xfa48..0xfb18` selects the internal page code from orientation-specific
  thresholds. Portrait checks `0x782daa`, `0x782dae`, `0x782dac`, and
  `0x782db0`, yielding codes `6`, `2`, `1`, or `5`. Landscape checks
  `0x782daa`, `0x782dac`, and `0x782dae`, yielding codes `6`, `1`, or `2`.
  Values above all accepted thresholds return without changing page geometry.
- Accepted nonzero values flush pending span state and publish any current
  root at `0xfb0a..0xfb16` before committing the new layout. This preserves
  already-queued objects under the old page geometry.
- `0xfb20..0xfb5a` sets pending-layout byte `0x782997`, clears status/header
  byte `0x780e99` inside the `0x15a6` / `0x15ac` bracket, writes page code
  `0x782da2`, and writes computed page extent `0x782dba = D4`.
- `0xfb60..0xfc52` refreshes geometry for later consumers: table-derived
  words `0x782db2` / `0x782db4`, raster row-byte state under `0x783170`,
  phase word `0x782dc0`, active extents through `0xf87e`, top offset
  `0x782dce`, default text-bottom cache through `0xea16`, margins through
  `0xe9ba`, cursor placement through `0xf8fc`, VFC caches through `0xfe54`,
  and the default VFC table through `0x12b96`.

Consumers and output effect:

- The command itself creates no compact object. Its visible effect is deferred
  until a later printable, raster, rectangle, VFC, or publication path reads
  the refreshed fields.
- The direct next-printable path is
  `0xf9e8 -> 0xd04a -> 0xd824 -> 0x12f2e -> 0x1387c`. Stream
  `ESC &l66P!` reaches page-length handler `0xf9e8`, computes page extent
  `0x782dba = 3300`, sets internal page code `2`, refreshes vertical
  placement, and queues the following `!` at compact coordinate `0x9001`.
- Once that compact object exists, pixels follow the ordinary publication and
  render route:
  `0xff1e -> 0x1ed84 -> 0x1edc6 -> 0x1ef6a -> 0x1effe -> 0x1f034 -> 0x1f354`,
  then the selected compact row-copy helper writes the row. The page-length
  command has already done its work by changing the fields that determined the
  queued object coordinate.

State classification:

- Canonical state: VMI `0x783160`, orientation `0x782da3`, selected page code
  `0x782da2`, page extent `0x782dba`, active extents
  `0x782db6/0x782db8`, top offset `0x782dce`, margins
  `0x782dd6/0x782dda`, and cursor `0x782c8a/0x782c8e`.
- Derived/cache state: threshold words `0x782daa/0x782dac/0x782dae/0x782db0`,
  table words `0x782db2/0x782db4`, raster row-byte state rooted at
  `0x783170`, phase word `0x782dc0`, text-bottom cache `0x782dd2`, VFC caches
  `0x782ede/0x782edf/0x782ee0`, and compact coordinate `0x9001` derived for
  the following printable fixture.
- Parser scratch: the rewound six-byte `ESC &l#P` command record at
  `0x78299e` and local registers `D4/D5` while selecting the extent and page
  code.
- Firmware bookkeeping: pending-layout byte `0x782997`, status/header byte
  `0x780e99`, update bracket `0x15a6` / `0x15ac`, macro/page state
  `0x782a92`, and any old-root publication caused by `0xfb0a..0xfb16`.
- Unknown: no ROM-local middle edge remains for the documented
  `ESC &l66P!` path. New work must change the VMI-zero exit, threshold return,
  old-root publication, refreshed field set, or later object coordinate.

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

### Shared Geometry Refresh Consumer Checkpoint

This checkpoint connects page-control commands to later page-object and pixel
routes. It starts after `ESC &l#A`, `ESC &l#P`, or `ESC &l#O` has selected an
internal page code or orientation and ends when a later printable, raster,
rectangle, VFC, or publication path consumes the refreshed fields.

Writers:

- Page size `0xfc74..0xfe52` maps accepted selectors to internal page code
  `D5`, publishes the old root on explicit changes, sets pending layout byte
  `0x782997`, writes `0x782da2`, refreshes table-derived words
  `0x782db2` and `0x782db4`, recomputes phase word `0x782dc0`, writes top
  offset `0x782dce = 0x96 - 0x782dbe`, clears `0x782dd0`, then calls
  `0xea16`, `0xe9ba`, `0xf8fc`, `0xfe54`, and `0x12b96`.
- Page length `0xf9e8..0xfc52` converts nonzero line counts through VMI
  `0x783160`, writes page extent `0x782dba`, selects an orientation-dependent
  page code from thresholds `0x782daa/0x782dac/0x782dae/0x782db0`, and then
  runs the same geometry/VFC refresh. Its zero branch can first publish the
  current root, mirror paper-source state to `0x780e8f` / `0x780e26`, and then
  restore the default code from `0x780e97` or fallback code `2`.
- Orientation `0x10220..0x103e6` publishes the old root only for a changed
  selector below `2`, writes `0x782da3`, calls `0xf9ac`, `0xf87e`,
  `0xea16`, `0xe9ba`, `0xf8fc`, `0xfe54`, `0x12b96`, and `0x103ea`, then
  refreshes selected font-context metrics and HMI `0x78315c`.

Shared helper effects:

- Geometry lookup helpers `0x9d16`, `0x9d4e`, `0x9d86`, and `0x9dbe` mask the
  internal page code with `0x7f` before indexing table rows `0..10`.
  `0x9d4e` supplies the stored logical width word `0x782db2`, while `0x9d16`
  supplies the stored logical height word `0x782db4`. The orientation helper
  `0x103ea` uses `0x9dbe` for portrait thresholds and `0x9d86` for landscape
  thresholds before writing `0x782daa`, `0x782dae`, `0x782dac`, and
  `0x782db0`.
- `0xf9ac` writes page extent `0x782dba` from the portrait or landscape length
  table selected by orientation byte `0x782da3`.
- `0xf87e` writes orientation offset `0x782dbe`, then swaps table-derived
  words `0x782db2` / `0x782db4` into active extents
  `0x782db6` / `0x782db8` according to orientation.
- `0xea16` refreshes default text-bottom cache `0x782dd2`.
- `0xe9ba` resets horizontal margins by clearing `0x782dd6`, copying active
  page width `0x782db8` to `0x782dda`, and clearing `0x782ddc`.
- `0xfe54` recomputes VFC line-count caches `0x782edf`, `0x782ee0`, and
  `0x782ede` from VMI, top offset, and text-bottom state.
- `0x12b96` rebuilds the default VFC table at `0x782dde..0x782edd`, copies
  text-bottom cache `0x782dd2` to derived overflow limit `0x782dc2`, and
  clears modified-layout byte `0x782ee1`.

Readers and output consumers:

- Printable path `0xd04a` consumes refreshed cursor, margin, extent, and HMI
  state through prechecks `0xd28a` / `0xd6bc`, queueing compact text only after
  those geometry gates accept the byte.
- Direct cursor controls consume the same state: CR helper `0xf06e` copies
  `0x782dd6` to `0x782c8a`; horizontal commit `0xf4ca` clamps against
  `0x782db8` and right margin `0x782dda`; vertical commit `0xf6e2` uses top
  offset `0x782dce` and bounds `0x782dca` / `0x782dc6`.
- Raster start and transfer handlers consume logical width and active extents:
  `0x1061e`, `0x1064c`, `0x107bc`, and `0x1086e` read
  `0x782db2/0x782db4`, while encoded object production at `0x130ae` adds
  phase word `0x782dc0`.
- Rectangle/rule producers consume `0x782db8` / `0x782db6` for clipping and
  add `0x782dc0` before packing rule keys at `0x13386..0x133aa`.
- Text span and fixed-list production consume active extents: `0x12714`
  checks `0x782db2` and gates output against `0x782db6` before inserting
  segment-list or fixed-list objects.
- VFC and vertical overflow consumers use caches from the same refresh:
  `0x1280a` reads `0x782dce`, `0x782edf`, and `0x782ee0`, while overflow
  helper `0xf36c` tests derived limit `0x782dc2`.

Output effect:

- The refresh creates no pixels immediately. Its visible effect is to change
  how subsequent bytes are admitted, positioned, clipped, bucketed, and
  eventually rendered.
- If a current root exists, page-size, page-length zero/default, and
  orientation change paths publish the old page before rewriting geometry.
  Objects already queued under the old root therefore render with the old
  geometry through the normal
  `0xff1e -> 0x1ed84 -> 0x1edc6 -> 0x1ef6a -> object-class row-store helper`
  route. Later objects consume the new fields above.

Field classification:

- Canonical: page code `0x782da2`, orientation `0x782da3`, page extent
  `0x782dba`, active extents `0x782db6/0x782db8`, margins
  `0x782dd6/0x782dda`, top offset `0x782dce`, VMI/HMI
  `0x783160/0x78315c`, current cursor `0x782c8a/0x782c8e`, and VFC table
  `0x782dde..0x782edd`.
- Derived/cache: table words `0x782db2/0x782db4`, phase word `0x782dc0`,
  text-bottom cache `0x782dd2`, overflow limit `0x782dc2`, line-count caches
  `0x782ede/0x782edf/0x782ee0`, page-code masked lookup indexes, and
  threshold words `0x782daa/0x782dac/0x782dae/0x782db0`.
- Parser scratch: six-byte parsed records consumed after `0x78299e` is
  rewound by `0xfc74`, `0xf9e8`, or `0x10220`.
- Firmware bookkeeping: pending publication byte `0x782997`, layout scratch
  `0x782dd0`, modified-layout byte `0x782ee1`, macro/page state
  `0x782a92`, and helper status side effects around `0x9ac2` / `0x9b5e`.
- Unknown: no ROM-local writer-to-consumer edge remains unnamed for the shared
  geometry refresh above. New work must change one of the named fields,
  helper calls, consumer branches, or object/output fields.

Evidence:

- Disassembly:
  `generated/disasm/ic30_ic13_page_size_handler_00fc74.lst`,
  `generated/disasm/ic30_ic13_page_length_handler_00f9e8.lst`,
  `generated/disasm/ic30_ic13_orientation_handler_010220.lst`,
  `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`,
  `generated/disasm/ic30_ic13_raster_handlers_0105d0.lst`,
  `generated/disasm/ic30_ic13_raster_object_queue_013070.lst`,
  `generated/disasm/ic30_ic13_rectangle_graphics_010898.lst`,
  `generated/disasm/ic30_ic13_text_span_flush_012714.lst`, and
  `generated/disasm/ic30_ic13_vertical_forms_control_01280a.lst`.
- Checked-in explanations:
  `generated/analysis/ic30_ic13_page_geometry_tables.md`,
  [page-raster-imaging.md](page-raster-imaging.md#page-size-tables),
  [direct-control-codes.md](direct-control-codes.md#owner-summary),
  [raster-graphics.md](raster-graphics.md#owner-summary),
  [rectangle-graphics.md](rectangle-graphics.md#owner-summary), and
  [vertical-forms-control.md](vertical-forms-control.md).

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

### Paper Source Selector Matrix

This checkpoint composes every `ESC &l#H` selector class through publication
timing and the state consumed by a later page finalization. The command always
publishes any active current root before changing the paper-source state:
`0xef90 -> 0xf34a` flushes pending spans/text, `0xef96 -> 0xff1e` publishes
the current page root, and `0xef9c -> 0xf8fc` refreshes placement state before
the selector table dispatch at `0xef3a`.

Selector outcomes:

- Selector `0`:
  dispatches to `0xefae`, calls status/service helper `0x9ac2`, and returns
  at `0xf024` without writing `0x782da6`, `0x782998`, `0x780e8f`, or
  `0x780e26`. Its visible page effect is only the pre-selector publication,
  if a current root existed.
- Selector `1`:
  dispatches to `0xefb6`, clears `D5` to `0`, writes marker byte
  `0x782990 = 1`, and enters the common output path at `0xefc0`.
- Selector `2`:
  dispatches to `0xefe8`, writes `D5 = 0x80`, and enters the common output
  path. This is the addressed stream already covered by `! ESC &l2H`.
- Selector `3`:
  dispatches to `0xeff0`, writes `D5 = 0x90`, and enters the common output
  path.
- Other nonzero selectors:
  dispatch to `0xeff8`, load `D5` from default paper-source byte `0x7821a2`,
  write marker byte `0x782990 = 1`, and enter the common output path.

The common output path has two layers. First, `0xefc0..0xefe4` calls `0x9b1e`;
only when it returns `D7 == 1` does the ROM mirror `D5` to output byte
`0x780e8f` and signal `0x780e26` through `0x9b5e`. Second,
`0xf00a..0xf01c` always brackets the canonical write with `0x15a6` /
`0x15ac`, stores `0x782da6 = D5`, and sets pending publication byte
`0x782998 = 1`.

State grouping for this selector matrix:

- Canonical page-control state:
  paper-source byte `0x782da6`, pending publication/header byte `0x782998`,
  current page root `0x78297a`, and published pool record header byte `+0x07`
  later copied by `0xff1e` from `0x782da6`.
- Derived/cache state:
  selector-derived `D5`, default paper-source byte `0x7821a2`, placement
  refresh output from `0xf8fc`, and published/render records created from the
  pre-change root.
- Parser scratch:
  the six-byte `ESC &l#H` command record rewound at `0xef72..0xef7a`, with
  negative selectors converted to absolute values at `0xef80..0xef8e`.
- Firmware bookkeeping:
  marker byte `0x782990`, `0x15a6` / `0x15ac` critical-section calls,
  `0x9b1e` return in `D7`, publication flag `0x782996`, and root-clear state
  from `0xff1e`.
- Hardware/external state:
  `0x780e8f` and `0x780e26` are ROM-visible output/control bytes whose
  physical paper-source meaning remains a hardware boundary.
- Unknown:
  no ROM-local selector table, publication timing, canonical write, pending
  header, or mirror/signal branch remains unknown for `0xef62..0xf02a`.

Writers and consumers:

- `0xef62` writes `0x782da6`, `0x782998`, and sometimes `0x782990`,
  `0x780e8f`, and `0x780e26` after publishing any old root.
- `0xff1e` later consumes `0x782da6` and `0x782998`: `0x10044..0x1005a`
  copies the paper-source byte to root header `+0x07`, while
  `0x10032..0x1003a` records and clears pending paper-source/header state.
- `0x1ed84` / `0x1edc6` consume the published root produced before selector
  mutation; the paper-source update affects later page headers, not the
  already-published compact buckets.

Output effect:

- Pre-existing page objects are published before selector mutation.
- Selector `0` has no new canonical paper-source write after that publication.
- Selectors `1`, `2`, `3`, and default write paper-source state for following
  publications; the physical tray/source interpretation of `0`, `0x80`,
  `0x90`, and `0x7821a2` is outside the ROM-local pixel model.

Evidence: `generated/disasm/ic30_ic13_paper_source_handler_00ef62.lst`
`0xef62..0xf02a`, page-root finalizer
`generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`, fixture
`addressed paper-source and copies publications render page records`, and
fixture `host-fetched FF geometry and paper-source publications preserve
0xff1e pool header defaults`.

### Copy-Count Delayed Header Checkpoint

`ESC &l#X` is a state-only command until a later publication consumes its
result. The parser dispatch reaches `0xeef0`; the handler rewinds the
six-byte parser record and reads parameter word `+2` from the restored record.

Handler behavior:

- `0xeef8..0xef06` rewinds `0x78299e` by six bytes and loads parsed word
  `+2` into `D5`.
- `0xef0a..0xef14` sign-extends the parsed word and converts negative values
  to their absolute value.
- `0xef16..0xef26` clamps values above `99` by writing literal `99` to
  `0x782da4`.
- `0xef28..0xef32` leaves value `0` as no-change and writes nonzero in-range
  values to `0x782da4`.
- `0xef32..0xef38` returns without calling `0xff1e`, so no page object,
  publication, bridge, or row render happens at the copy-count command.

Consumers and output effect:

- `0xff1e` later accepts an active current root and reaches
  `0x10044..0x1005a`; writer `0x10052` copies `0x782da4` into published
  root header word `+0x0c`.
- `0x1ed84` copies published header words into the render work record before
  `0x1edc6` copies bucket/list/context roots.
- Render entry `0x1ef6a` still derives pixels only from page objects. Copy
  count is page/control metadata carried beside those objects; it does not
  change compact text, raster, rule, fixed-list, or glyph row helpers.

State grouping:

- Canonical page-control state: `0x782da4`, written by `0xeef0` and consumed
  by `0xff1e`.
- Canonical published state: root header word `+0x0c`, written by `0x10052`
  from `0x782da4`.
- Parser scratch: rewound six-byte command record at `0x78299e - 6`; parsed
  word `+2`; scratch register `D5`.
- Firmware bookkeeping: parser-record cursor `0x78299e`; publication helper
  critical section and current-root acceptance around `0xff1e`.
- Derived/cache state: render-work header copies made after `0x1ed84`; no
  pixel row cache derives from the copy count itself.
- Hardware/external state: physical copy-production behavior after the ROM
  publishes root word `+0x0c`.
- Unknown: no ROM-local middle edge remains for `ESC &l#X` to published
  header word `+0x0c`. Remaining uncertainty is physical engine behavior for
  multiple copies, not parser, page-object, bridge, or pixel-helper state.

Evidence: `generated/disasm/ic30_ic13_copies_handler_00eef0.lst`
`0xeef0..0xef38`, `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`
`0x10044..0x1005a`, fixtures `0xeef0 ESC &l#X stores absolute clamped copy
count`, `mixed printable/copies/FF stream publishes copy count`, and
`host-fetched copies publication preserves 0xeef0 pool header word`.

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
  one compact bucket object to `0x1effe` with context slot `0`, then through
  `0x1f034 -> 0x1f354` to the selected compact row-copy helper.

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
       -> 0x1f034/0x1f354 compact source resolver
       -> selected compact row-copy helper
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

A byte-stream renderer must model publication as a page snapshot boundary, not
as a pixel renderer.

- `0xff1e` is the exact snapshot boundary. It accepts only current root
  `0x78297a` with root byte `+0x04 == 1`; the no-root or inactive-root exit at
  `0xff26..0xff40` clears current-root state without producing a published
  page/control record.
- Successful publication writes root byte `+0x04 = 2`, root header bytes and
  words `+0x07/+0x08/+0x0a/+0x0c/+0x18/+0x1a`, pool head `0x780ea6`,
  publication flag `0x782996`, and cleared current root `0x78297a = 0`.
- Publication preserves object roots and context slots created before the
  boundary: compact/raster buckets under `+0x1c`, rules under `+0x24`,
  fixed-list objects under `+0x28`, and context slots under `+0x2c..+0x68`.
  Pixels are derived only after `0x1ed84` / `0x1edc6` copies those source roots
  into render-work fields and `0x1ef6a` dispatches the object renderers.
- Reset `0xcc52`, FF `0xf0f0`, page-size `0xfc74`, orientation `0x10220`, and
  paper-source `0xef62` must publish any active current root before their
  post-command environment changes are used by later bytes.
- Page-length `0xf9e8` has a split contract: accepted nonzero values update
  `0x782dba`, `0x782da2`, and refreshed cursor/geometry state for later
  placement, while the zero/default branch can publish pending text before it
  restores default page state.
- FF publication must occur after line-termination mode has applied the
  CR-style horizontal reset when `ESC &k2G` is active.
- Copies handler `0xeef0` is state-only until a later publication copies
  `0x782da4` into published root word `+0x0c`.
- Paper-source selector `2` publishes the pre-change page, then writes
  canonical and output/control state including `0x782da6`, `0x782998`,
  `0x780e8f`, and `0x780e26` for following pages or device-facing consumers.
- The macro overlay branch at `0xff40..0xffb0` replays overlay bytes through
  the ordinary parser before final publication. It creates visible pixels only
  through the normal command owners that run during replay and the later
  `0x1ed84 -> 0x1edc6 -> 0x1ef6a` render path.
- For the documented reset, FF, page-size, page-length, orientation,
  paper-source, and copies streams, ROM-derived compact rows come from the
  same published-record bridge and render helpers. There is no separate
  publication renderer.

## Evidence Status

Direct ROM evidence covers parser handler order, host-byte draining, page-record
storage, published pool headers, command side effects, render bridge fields, and render
entry call order because the claims are backed by handler ranges `0xcc52..0xcc98`,
`0xf0f0..0xf172`, `0xfc74..0xfe52`, `0xf9e8..0xfc52`, `0x10220..0x103e6`,
`0xef62..0xf02a`, `0xeef0..0xef38`, publication helper `0xff1e..0x10080`, bridge helpers
`0x1ed84` / `0x1edc6`, and the named byte-stream examples.

Remaining publication work starts only from byte-stream variants that create a
new publication-side field, bucket shape, bridge state, placement state, or
rendered row outside the covered command streams listed above. Physical printer
correlation and engine timing remain outside this ROM-internal publication
contract.

## Remaining Edges

- `0xff1e..0x1ed84`: final rows are ROM-derived for covered publication
  commands by tracing publication, bridge, and render helpers.
  Physical-device comparison is outside the current static ROM evidence
  standard and is not an oracle for these rows.
- No parser-to-publication or publication-to-render ROM middle edge remains for
  the covered reset, FF, page-size, page-length zero/default branch,
  orientation, paper-source, and copies streams. No parser-to-placement middle
  edge remains for the covered nonzero page-length stream. Additional ROM work
  should target streams that change a field or boundary named in the
  [Page Environment Outcome Matrix](#page-environment-outcome-matrix),
  page-record fields, command-specific pool-header words, bridge state,
  placement state, or row-construction inputs.
