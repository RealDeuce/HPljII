# Page Geometry and Raster Imaging Notes

Sources: `generated/analysis/ic30_ic13_page_geometry_tables.md`;
`generated/disasm/ic30_ic13_page_geometry_tables_009d16.lst`;
`generated/analysis/ic30_ic13_parser_xrefs.md`;
`generated/analysis/ic30_ic13_page_root_references.md`;
`generated/analysis/ic30_ic13_page_root_allocation.md`;
`generated/analysis/ic30_ic13_page_root_finalization.md`;
`generated/analysis/ic30_ic13_render_path_references.md`;
`generated/analysis/ic30_ic13_render_dispatch_tables.md`;
`generated/analysis/ic30_ic13_render_subrenderers.md`;
`generated/analysis/ic30_ic13_render_expansion_fixtures.md`;
`generated/analysis/ic30_ic13_render_destination_fixtures.md`;
`generated/analysis/ic30_ic13_render_row_copy_fixtures.md`;
`generated/analysis/ic30_ic13_font_context_bridge.md`;
`generated/analysis/ic30_ic13_text_glyph_index_flow.md`;
`generated/analysis/ic30_ic13_font_control_flow.md`;
`generated/analysis/ic30_ic13_direct_control_code_flow.md`;
`generated/analysis/ic30_ic13_esc_e_reset_flow.md`;
`generated/analysis/ic30_ic13_printable_text_path.md`;
`generated/analysis/ic30_ic13_text_cursor_span_flow.md`;
`generated/analysis/ic30_ic13_active_symbol_set_flow.md`;
`generated/analysis/ic30_ic13_symbol_set_patch_tables.md`;
`notes/symbol-set-selection.md`;
`notes/symbol-map-patching.md`;
`generated/disasm/ic30_ic13_page_size_handler_00fc74.lst`;
`generated/disasm/ic30_ic13_vertical_forms_control_01280a.lst`;
`generated/disasm/ic30_ic13_orientation_handler_010220.lst`;
`generated/disasm/ic30_ic13_page_root_allocate_010084.lst`;
`generated/disasm/ic30_ic13_coordinate_math_0104d8.lst`;
`generated/disasm/ic30_ic13_raster_handlers_0105d0.lst`;
`generated/disasm/ic30_ic13_payload_dispatch_011f82.lst`;
`generated/disasm/ic30_ic13_text_span_flush_012714.lst`;
`generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`;
`generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`;
`generated/disasm/ic30_ic13_raster_object_queue_013070.lst`;
`generated/disasm/ic30_ic13_display_list_helpers_013386.lst`;
`generated/disasm/ic30_ic13_active_object_dispatch_014ba4.lst`;
`generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`;
`generated/disasm/ic30_ic13_page_root_font_slot_scan_0196c4.lst`;
`generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`;
`generated/disasm/ic30_ic13_bitmap_state_setup_01ee9e.lst`;
`generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`;
`generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst`;
`generated/disasm/ic30_ic13_bitmap_draw_core_01f3d4.lst`;
`generated/disasm/ic30_ic13_bitmap_encoded_span_modes_01f88e.lst`;
`generated/disasm/ic30_ic13_bitmap_row_copy_tables_01fa5c.lst`;
`generated/disasm/ic30_ic13_glyph_row_copy_helper_02f27c.lst`;
`generated/disasm/ic30_ic13_assign_font_id_015a56.lst`;
`generated/disasm/ic30_ic13_font_control_dispatch_016df6.lst`;
`generated/disasm/ic30_ic13_font_id_select_017708.lst`;
`generated/disasm/ic30_ic13_default_font_tables_01ab84.lst`;
`generated/disasm/ic30_ic13_symbol_set_handler_01be22.lst`;
`generated/disasm/ic30_ic13_font_update_common_00c580.lst`;
`notes/pcl-command-map.md`; `notes/resource-rom.md`.

These notes track firmware behavior that directly affects page pixels. Field
roles in this file are address-level ROM contracts: writer/reader addresses,
object offsets, render roots, and row-helper inputs are the authoritative
model. Manual-facing names are provisional only where an HP term has not been
correlated to an already documented field.

## Owner Summary

This note owns the page/imaging layer that turns command-family side effects
into page objects, published records, render work, and ROM-local row writes.
It is the join point after parser and command owners have produced geometry,
cursor, font, raster, rectangle, span, or publication state. It does not own
host-byte parsing itself; it owns the page-root fields and render helpers that
make those parsed commands visible.

Primary routes:

- Page-root allocation:
  `0x10084` creates or returns current page root `0x78297a`, initializes
  bucket/list roots and context slots, and is the common prerequisite for
  text, raster, rule, fixed-list, and span producers.
- Geometry and motion:
  page-size handler `0xfc74`, page-length handler `0xf9e8`, orientation
  handler `0x10220`, coordinate helpers `0x104d8..0x10550`, and VFC handler
  `0x1280a` update page geometry, text bounds, cursor position, and
  publication-before-change behavior.
- Object producers:
  compact text queues through `0xd04a -> 0x1393a -> 0x12f2e -> 0x1387c`;
  span objects through `0xf34a -> 0x12714`; raster rows through
  `0x105d0 -> 0x138de -> 0x13070` / `0x13250`; and rule/rectangle objects
  through `0x10898 -> 0x10b80 -> 0x13386` / `0x133aa`.
- Publication and render bridge:
  `0xff1e` publishes the current page/control record, `0x1ed84` copies the
  selected published record into render-work state, and `0x1edc6` copies page
  roots into render roots and context slots.
- Render scheduling and dispatch:
  active scheduler `0x1eba4` reaches render entry `0x1ef6a`; `0x1ef86`
  derives band and destination caches; `0x1efc2`, `0x1f446`, and `0x1f756`
  dispatch bucket, rule, and fixed-list roots.
- Pixel generation:
  compact text/downloaded glyphs dispatch through `0x1effe`; segment lists
  through `0x1f812`; encoded raster through `0x1f88e`; rules through
  `0x1f596` or `0x1f4e0`; fixed lists through `0x1f7b0`; and row helpers
  under `0x1fa5c..0x207ac` and `0x2f27c` write the ROM-local output rows.

Field groups:

- Canonical page/image state:
  current page root `0x78297a`, root `+0x1c` compact/raster bucket heads,
  root `+0x24` rule list, root `+0x28` fixed list, and root
  `+0x2c..+0x68` font/context slots.
- Canonical object state:
  compact/raster bucket object link `+0`, class byte `+4`, selector/mode byte
  `+5`, count/capacity word `+6`, coordinate/key word `+8`, and payload from
  `+0x0a`; rule and fixed-list selector, dimension, key, and continuation
  fields are owned by the rule/fixed sections below.
- Canonical render state:
  render roots `+0x18`, `+0x1c`, `+0x20`, render context slots
  `+0x24..+0x60`, active render pointer `0x783a18`, and render work band word
  `+0x10`.
- Derived/cache state:
  render-band row caches `0x783a20` and `0x783a22`, destination base
  `0x783a28`, destination stride `0x783a1c`, compact context cache
  `0x783a2c`, phase byte `0xa001`, and row-helper offset tables.
- Parser scratch:
  none at this layer. Parser scratch has been consumed into command state,
  delayed payload records, or page objects before publication/rendering.
- Firmware bookkeeping:
  root allocation cursors, object stream allocator fields, publication pool
  records, render-work alternation, scheduler throttle/capacity words, and
  continuation fields mutated for multi-band rule or fixed-list rendering.
- Hardware/external state:
  physical formatter/DC consumption after ROM row-buffer writes. This note
  documents the ROM-local row writes and records hardware behavior only where
  ROM code reads or writes a concrete RAM/MMIO field.
- Unknown:
  remaining unresolved edges must name a command/object field, bridge field,
  dispatch helper, row-helper input, or hardware/MMIO boundary. There is no
  requirement for live printer comparison to document the ROM-local routes.

Output effect:

- Parser and command handlers build page state; they do not directly write the
  final rendered rows.
- Publication freezes page-root state into records; render bridge copies those
  records into render roots; render dispatch walks object classes in ROM order.
- Pixels come from decoded object fields, selected font/context slots, raster
  payload bytes, rule dimensions/pattern selectors, span/fixed-list fields,
  and the row-copy helpers documented in the sections below.

## Reproduction Contract

For documented supported streams, this layer is reproduced when the same
parser-visible command effects produce the same page-root fields, queued page
objects, published records, render work records, object dispatch order, and
ROM-derived row writes. The required ROM-visible behavior is:

- Page/image objects are rooted at current page root `0x78297a`. Helper
  `0x10084` creates the first root, initializes bucket/list roots and context
  fields, and is the common prerequisite for text, raster, rule, and span
  object producers.
- Object producers do not render immediately. Compact text queues through
  `0xd04a -> 0x1393a -> 0x12f2e`; pending spans flush through `0x12714`;
  raster rows queue through `0x105d0 -> 0x138de -> 0x13070` / `0x13250`; and
  rectangle/rule objects queue through `0x10898 -> 0x10b80 -> 0x13386` /
  `0x133aa`.
- Publication is the page-root boundary. `0xff1e` copies root fields, bucket
  roots, list roots, context slots, and status/header fields into a published
  page/control record. It may publish, clear, or retry according to the root
  state documented in the page-record storage checkpoint.
- Render entry starts from published records, not from parser commands.
  `0x1ed84` copies the active page/control record into render-record state,
  `0x1edc6` bridges page roots into render roots, and `0x1ef6a` walks the
  active band work record.
- Object-class dispatch order is part of the pixel contract. `0x1ef6a` calls
  `0x1ef86`, bucket root `+0x18` through `0x1efc2`, rule root `+0x1c`
  through `0x1f446`, and fixed-list root `+0x20` through `0x1f756`.
- Bucket object class byte `+0x04` selects the first pixel writer family:
  `0x00..0x3f` reaches compact dispatch `0x1effe`, `0x40..0x7f` reaches
  segment-list renderer `0x1f812`, and `0x80..0xff` reaches encoded-raster
  renderer `0x1f88e`.
- Compact helper bits `+0x04 & 0x30` select `0x1f034`, `0x1f0d2`,
  `0x1f1f0`, or `0x1f264`; encoded-raster mode bits `+0x05 & 3` select
  `0x1f8da`, `0x1f8e6`, `0x1f920`, or `0x1f9c6`; rule selector low nibble
  selects solid `0x1f596` for selector `7` or patterned `0x1f4e0` through
  table `0x1f4a0`.
- Current-band and fallback placement is part of pixel reproduction.
  Destination helpers `0x1f3d4` and `0x1f626` use band caches `0x783a20`,
  `0x783a22`, destination base `0x783a28`, stride `0x783a1c`, offset table
  `0x7839f8..`, and fallback base `0x7810b4 + byte_pair_offset`; object bytes
  alone do not identify the final destination rows.
- Pixel composition at this layer is direct store in ROM call order. Compact,
  encoded-raster, segment-list, rule, and fixed-list helpers write generated
  words/bytes to the selected destination; no shared hidden destination
  read-modify-write blend combines earlier object classes with later ones.
- Compact text pixels depend on the selected font context and map that were
  installed before `0xd04a` queued the object. Raster pixels depend on the
  queued encoded mode and copied payload bytes. Rule pixels depend on clipped
  source dimensions, fill selector, and pattern/solid dispatch. These
  producer fields are the canonical state; rendered rows are derived from
  them by the ROM helpers.
- Scheduler and MMIO events only matter to reproduction when they change a
  ROM-visible page object, published record, band word, render call, or
  destination buffer. Physical formatter/DC signal names remain external
  boundaries unless the ROM code consumes their values into those fields.

This contract is intentionally scoped to the object classes and command
families documented below. Remaining work starts from byte streams that change
specific object fields, selected-font state, publication fields, helper
dispatch, or row-construction inputs, not from broad claims about live printer
timing.

## Render Selector Dispatch Checkpoint

This checkpoint records the canonical selector fields that turn bridged page
objects into pixel-writer families. It starts after `0x1edc6` has copied
page-root object lists into render-record roots and after `0x1ef86` has
derived current-band caches.

Canonical selector inputs:

- Bucket-chain root `+0x18` contains compact text/downloaded-glyph,
  segment-list, and encoded-raster objects. Dispatcher `0x1efc2` selects the
  active bucket from render work word `+0x10`, then reads object byte `+0x04`.
- Compact objects use byte `+0x04 & 0x30` as the helper selector and byte
  `+0x05 & 0x0f` as the render context slot copied from `+0x24 + 4*n` into
  `0x783a2c` by `0x1effe`.
- Encoded-raster objects use byte `+0x05 & 0x03` as the expansion-mode
  selector, word `+0x06` as payload byte count, word `+0x08` as packed
  coordinate, and payload bytes from `+0x0a`.
- Rule-list root `+0x1c` contains bridged rule objects. Dispatcher `0x1f446`
  uses `object[5] & 0x0f` as table index and consumes continuation word
  `+0x0c` across bands.
- Fixed-list root `+0x20` has no computed dispatch table in this checkpoint;
  `0x1f756` consumes the bridged fixed-list fields directly on its five-band
  cadence.

Dispatch table facts:

- Bucket class branch `0x1efdc..0x1eff2` masks object byte `+0x04` with
  `0xc0`: class `0x00` calls compact dispatcher `0x1effe`, class `0x40`
  calls segment-list renderer `0x1f812`, and classes with the high bit set
  call encoded-raster renderer `0x1f88e`.
- Compact table `0x1f024` maps selector bits to helper targets:
  `0x00 -> 0x1f034`, `0x10 -> 0x1f0d2`, `0x20 -> 0x1f1f0`, and
  `0x30 -> 0x1f264`.
- Rule table `0x1f4a0` maps selector `7` to solid writer `0x1f596`; every
  other low-nibble entry in the ROM table points at patterned writer
  `0x1f4e0`.
- Encoded-raster table `0x1f8ca` maps mode `0` to literal helper `0x1f8da`,
  mode `1` to two-row expansion `0x1f8e6`, mode `2` to three-row expansion
  `0x1f920`, and mode `3` to four-row expansion `0x1f9c6`.

Producer ownership:

- Compact selector fields are written by `0x12f2e -> 0x1387c` from the
  printable-text/downloaded-glyph queue path. The word stored at object
  `+0x04` carries selector bits `0x1000` and `0x2000` into byte bits
  `0x10` and `0x20`; word `+0x06` is the compact entry count and entries
  start at `+0x08`.
- Segment-list class objects are written by pending text-span flush paths
  `0x12714 -> 0x13520/0x135f0` and later consumed as six-byte span entries by
  `0x1f812 -> 0x1f862`.
- Encoded-raster fields are written by `0x13070 -> 0x13250`: byte `+0x04`
  is born as `0x80`, byte `+0x05` carries the low byte of the queued raster
  mode argument, word `+0x06` is capacity/count, word `+0x08` is the packed
  key, and payload bytes start at `+0x0a`.
- Rule selector and continuation fields are written by `0x13386` /
  `0x133aa` and normalized by bridge `0x1edc6`, which copies source word
  `+0x0a` into render continuation word `+0x0c`.
- Fixed-list fields are written by `0x136d2` and normalized by `0x1edc6`
  before `0x1f756` consumes `+0x04..+0x0d`.

Field grouping:

- Canonical state: render roots `+0x18/+0x1c/+0x20`, context slots
  `+0x24..+0x60`, object selector bytes `+0x04/+0x05`, object counts and
  dimensions, packed coordinate/key words, payload bytes, and continuation
  words copied by `0x1edc6`.
- Derived/cache state: current-band caches `0x783a20`, `0x783a22`,
  `0x783a28`, stride `0x783a1c`, offset table `0x7839f8..`, active compact
  context cache `0x783a2c`, phase byte `$a001`, and fallback base
  `0x7810b4`.
- Parser scratch: none. Parser command records and payload cursors have
  already been reduced to page objects before this checkpoint.
- Firmware bookkeeping: linked-list next pointers, active bucket index,
  rule/fixed continuation mutation, and computed table indexes.
- Hardware/external state: physical consumption after the ROM has stored band
  rows. No table entry above depends on live formatter timing evidence.
- Unknown: only the exact helper boundaries named in this file, such as
  compact invalid row-copy targets, missing external resource-window bytes,
  or physical consumption after row buffers exist.

Output effect:

- The dispatch tables choose the pixel-writer family. Compact and
  segment-list writers consume font/span source rows; encoded-raster writers
  consume queued payload bytes; rule and fixed-list writers consume bridged
  dimensions and pattern selectors.
- Pixels are stored in ROM call order: bucket-chain objects first, rule-list
  objects second, fixed-list objects third. The shared dispatch layer does not
  imply a hidden destination blend mode.

Evidence: `generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`
anchors `0x1ef6a`, `0x1efc2`, and compact table `0x1f024`;
`generated/disasm/ic30_ic13_bitmap_draw_core_01f3d4.lst` anchors rule table
`0x1f4a0`; `generated/disasm/ic30_ic13_bitmap_encoded_span_modes_01f88e.lst`
anchors encoded-raster table `0x1f8ca`; and
`generated/analysis/ic30_ic13_render_dispatch_tables.md` records the
producer-to-renderer mapping summarized here.

## Page Image Assembly Checkpoint

This checkpoint composes the page-image lifetime used by the renderer. The ROM
does not build independent parser-time strips for supported streams. Parser
and command handlers build one logical page/control object graph, publication
freezes that graph, and the active scheduler later renders capacity-approved
bands from the published record.

Writers and readers:

- `0x10084` creates or returns current page root `0x78297a`.
- Object producers write page content under that root: compact/raster bucket
  objects at root `+0x1c`, rule objects at root `+0x24`, fixed-list objects at
  root `+0x28`, and context slots at root `+0x2c..+0x68`.
- `0xff1e` publishes active roots into the page/control pool, updates
  publication state, and clears current root `0x78297a`.
- `0x1ed84 -> 0x1edc6` copies published source roots into render roots
  `+0x18`, `+0x1c`, and `+0x20`, plus render context slots `+0x24..+0x60`.
- `0x1eba4` presents render work word `+0x10` as a band selector only after
  scheduler/capacity predicates allow a call to `0x1ef6a`.
- `0x1ef86` derives band-local caches `0x783a20`, `0x783a22`, `0x783a28`, and
  `0x783a1c`; these are render destinations for the current band, not
  canonical page-object storage.

State classification:

- Canonical page/image state:
  current root `0x78297a`, root object heads `+0x1c/+0x24/+0x28`, context
  slots `+0x2c..+0x68`, published page/control records, and render roots
  copied by `0x1edc6`.
- Derived/cache state:
  active render pointer `0x783a18`, render work band word `+0x10`,
  `0x783a20/0x783a22/0x783a28`, stride `0x783a1c`, phase byte `0xa001`, and
  helper-specific continuation state.
- Parser scratch:
  none at this checkpoint. Parser records and delayed payload state have
  either become page objects or have been consumed before publication.
- Firmware bookkeeping:
  stream allocator cursors, publication flag `0x782996`, scheduler cursors,
  work-record alternation, throttle/capacity fields, and bridge-normalized
  rule/fixed continuation fields.
- Hardware/external state:
  physical formatter/DC consumption after ROM row-buffer writes. It is outside
  the ROM-local page-image assembly model unless it changes a named
  ROM-visible field.

Output effect:

- A supported byte stream first changes parser/command state, then queued page
  objects. It does not directly create final pixels at command parse time.
- Page publication and render bridge preserve the queued object graph for
  later band rendering.
- Pixel rows come from the sequence of scheduler-approved `0x1ef6a` calls.
  Within each call, object dispatch and row helpers interpret the copied render
  roots in ROM order.

Evidence:

- Page-root lifetime evidence is
  [page-record-storage.md](page-record-storage.md#page-object-lifetime-and-band-boundary).
- Scheduler evidence is
  [active-render-scheduler.md](active-render-scheduler.md#reproduction-contract).
- Render dispatch evidence is the `Render Entry Owner Summary` and
  `Pixel Generation Owner Summary` below, plus disassembly
  `generated/disasm/ic30_ic13_page_root_allocate_010084.lst`,
  `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`,
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`, and
  `generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`.

## Render Entry Owner Summary

The render entry path is the checked-in join between page/image object
producers and pixel writers. The route is:

- `0xff1e` publishes the current page/control record.
- `0x1ed84` copies the selected published record into the active render work
  record.
- `0x1edc6` bridges source page roots into render roots.
- `0x1eba4` advances the active band loop.
- `0x1ef6a` renders one capacity-approved band.
- `0x1ef86` derives per-band row and destination caches before object-class
  dispatch.

Writers feeding this checkpoint are the page object producers already
documented in this note: compact text through `0x12f2e` and `0x1387c`,
segment/span objects through `0x12714`, `0x13520`, and `0x135f0`, raster
objects through `0x13070`, `0x13250`, and `0x138de`, rule objects through
`0x13386` and `0x133aa`, fixed-list objects through `0x136d2`, publication
through `0xff1e`, render-root bridge `0x1edc6`, and band setup `0x1ef86`.

Readers and consumers are the render dispatchers and row helpers:
`0x1ef6a` consumes the active render work record, `0x1efc2` walks compact
bucket chains, `0x1f446` walks rule lists, `0x1f756` walks fixed lists,
`0x1effe` routes compact objects to `0x1f034`, `0x1f0d2`, `0x1f1f0`, and
`0x1f264`, `0x1f812` renders segment objects, `0x1f88e` renders encoded
raster spans, `0x1f596` and `0x1f4e0` render solid and patterned rules,
`0x1f3d4`, `0x1f414`, and `0x1f626` choose destination spans, and row-copy
helpers from `0x1fa5c..0x207ac` write the selected band or fallback buffer.

The output effect is not a parser-time bitmap. Parser and command handlers
build page roots and object records; render entry copies those roots into
render records; object dispatch interprets the copied records and writes rows.
Compact text and downloaded glyph output depend on the queued compact object
fields plus the copied font/context slots. Raster output depends on encoded
mode and payload bytes in queued raster records. Rectangle and rule output
depends on queued dimensions, clipping, fill selector, and pattern/solid
dispatch. Segment and fixed-list output depends on the object fields consumed
by `0x1f812` and `0x1f756`. The physical engine consumes rendered band data
after this ROM-local checkpoint.

Field ownership:

- Canonical page/image state: source page roots `+0x1c`, `+0x24`, `+0x28`,
  context slots `+0x2c..+0x68`, render roots `+0x18`, `+0x1c`, `+0x20`, and
  render context slots `+0x24..+0x60`.
- Derived/cache state: render-band rows `0x783a20`, remainder `0x783a22`,
  destination base `0x783a28`, destination stride `0x783a1c`, phase byte
  `0xa001`, and glyph/cache pointer `0x783a2c`.
- Parser scratch: none at this checkpoint; parser scratch has already been
  consumed into page objects or discarded before publication.
- Firmware bookkeeping: continuation fields in rule and fixed objects, active
  render pointer `0x783a18`, render work band word `+0x10`, work throttle word
  `+0x0e`, scheduler cursors, and work-record selection fields.
- Hardware/external state: physical formatter and DC behavior after ROM row
  buffer writes.
- Unknown: new byte streams that change root fields, object fields, dispatch
  selection, row-helper inputs, or the physical mapping after ROM output
  remain exact follow-up edges rather than assumptions about this checkpoint.

Concrete evidence lives in the sections below and in
`notes/active-render-scheduler.md`: `Render/Banding Bridge` documents
`0x1ed84` and `0x1edc6`, `Active Render Scheduler Semantic Checkpoint`
documents `0x1eba4`, `0x1ef6a`, and `0x1ef86`, `Pixel Writer And Buffer Map`
documents destination helpers, and `Object Class Dispatch` documents the class
routes from render roots to row writers. There is no additional ROM-local
middle edge between copied render roots and class dispatch for the object
classes named here. Remaining unresolved edges are object-class-specific and
are listed under those sections with their address boundaries.

## Render Entry Outcome Matrix

This matrix is the page/image-to-pixel contract after publication and active
scheduling have selected a render work record. It starts at the published
record bridge and ends at the ROM-local row helpers or exact object-specific
boundaries.

- Published record copy:
  `0x1ed84` consumes scheduler-selected source record `0x780eae`, copies
  header words into the active render work record, and calls `0x1edc6`.
  Output effect: no rows are written yet; this is the selected published
  page/control record becoming render state.

- Render-root bridge:
  `0x1edc6` copies source compact/raster bucket root `+0x1c` to render root
  `+0x18`, rule root `+0x24` to render root `+0x1c`, fixed-list root
  `+0x28` to render root `+0x20`, and context slots `+0x2c..+0x68` to render
  slots `+0x24..+0x60`. It also normalizes copied rule and fixed-list nodes
  for render-time continuation. Output effect: parser/page-object state is now
  frozen as render roots; later pixels come only from these copied roots and
  derived band caches.

- Band setup:
  Active scheduler `0x1eba4` calls render entry `0x1ef6a` only after capacity
  predicates allow it. `0x1ef6a` calls `0x1ef86`, which derives current-band
  row count `0x783a20`, remainder `0x783a22`, destination base `0x783a28`,
  destination stride `0x783a1c`, and render work copy fields. Output effect:
  destination caches are derived/cache state for this band, not canonical page
  storage.

- Bucket-chain render:
  `0x1ef6a -> 0x1efc2` consumes render root `+0x18` in linked-list order.
  Object byte `+4` selects compact/text objects in `0x00..0x3f`, segment-list
  objects in `0x40..0x7f`, or encoded-raster objects in `0x80..0xff`. Output
  effect: bucket-chain stores run before rule-list and fixed-list stores, so
  later object classes can overwrite overlapping rows.

- Compact text and downloaded glyphs:
  Compact objects dispatch through `0x1effe` to `0x1f034`, `0x1f0d2`,
  `0x1f1f0`, or `0x1f264`, then use glyph/row-copy helpers such as
  `0x1fa5c..0x207ac` and `0x2f27c`. Readers are compact object fields
  `+5/+6/+8/+0x0a`, copied context slots, selected map/font records, and
  compact context cache `0x783a2c`. Output effect: glyph rows are written to
  the selected current-band or fallback destination. Exact unresolved edges
  remain only for invalid computed helper targets and resource-window bytes
  named in downloaded-font/resource notes.

- Segment-list objects:
  Segment objects dispatch through `0x1f812` and row helper `0x1f862`,
  consuming bridged segment-list fields and the same destination split helpers
  as compact/raster bucket objects. Output effect: segment rows are written
  from queued object fields; the documented secondary segment-57 path stops
  only at missing external resource bytes `0x0c0000..0x0c0321`.

- Encoded raster objects:
  Raster objects dispatch through `0x1f88e`, with mode helpers `0x1f8da`,
  `0x1f8e6`, `0x1f920`, and `0x1f9c6` selected by object byte `+5 & 3`.
  Readers are encoded object mode, coordinate/key, count/capacity, and copied
  payload bytes. Output effect: raster rows are decoded and written into the
  current-band or fallback destination after any earlier compact bucket stores
  in the same chain order.

- Rule-list render:
  `0x1ef6a -> 0x1f446` consumes render rule root `+0x1c` on the documented
  five-band boundary pattern. Object byte `+5 & 0x0f` selects solid helper
  `0x1f596` or patterned helper `0x1f4e0`; destination helper `0x1f626`
  applies displacement and current-band/fallback clipping. Output effect:
  rule rows are written after bucket-chain rows and before fixed-list rows.

- Fixed-list render:
  `0x1ef6a -> 0x1f756` consumes render fixed-list root `+0x20` on the same
  boundary pattern and writes pattern rows through `0x1f7b0`. Output effect:
  fixed-list stores are last in the top-level render-entry order.

- Pixel composition order:
  The ROM uses direct stores in this render path. It does not apply a hidden
  destination read/modify/write blend at the shared dispatch layer. Overlap is
  resolved by call order: bucket chain first, rule list second, fixed list
  third, with linked-list order inside each class.

State grouping:

- Canonical render state: active source record `0x780eae`, active render
  pointer `0x783a18`, render roots `+0x18/+0x1c/+0x20`, render context slots
  `+0x24..+0x60`, and render work band word `+0x10`.
- Canonical object state: bucket object `+0/+4/+5/+6/+8/+0x0a`, rule/fixed
  selector and continuation fields, and copied page-root object links.
- Derived/cache state: band rows `0x783a20`, remainder `0x783a22`,
  destination base `0x783a28`, stride `0x783a1c`, offset tables, compact
  context cache `0x783a2c`, phase byte `0xa001`, and fallback buffer base
  `0x7810b4 + byte_pair_offset`.
- Parser scratch: none. Parser records and delayed payloads have already
  become page objects, state-only effects, or no-output parser outcomes.
- Firmware bookkeeping: scheduler capacity/throttle fields, work-record
  alternation, rule/fixed continuation fields initialized by `0x1edc6`, and
  invalid computed-jump boundaries for compact helper out-of-range cases.
- Hardware/external state: physical formatter/DC consumption after ROM row
  buffers are written.
- Unknown: object-class-specific invalid targets, missing resource-window
  bytes, and hardware/MMIO mapping after ROM row writes. No unresolved
  ROM-local middle edge remains for selecting copied render roots, dispatch
  order, or shared destination cache derivation.

Evidence:

- Bridge and entry listings:
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`,
  `generated/disasm/ic30_ic13_bitmap_state_setup_01ee9e.lst`, and
  `generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`.
- Object render listings:
  `generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst`,
  `generated/disasm/ic30_ic13_bitmap_draw_core_01f3d4.lst`,
  `generated/disasm/ic30_ic13_bitmap_encoded_span_modes_01f88e.lst`,
  `generated/disasm/ic30_ic13_bitmap_row_copy_tables_01fa5c.lst`, and
  `generated/disasm/ic30_ic13_glyph_row_copy_helper_02f27c.lst`.
- Checked-in owner notes:
  [page-record-storage.md](page-record-storage.md),
  [active-render-scheduler.md](active-render-scheduler.md#scheduler-outcome-matrix),
  [raster-graphics.md](raster-graphics.md),
  [rectangle-graphics.md](rectangle-graphics.md),
  [downloaded-fonts.md](downloaded-fonts.md), and
  [resource-rom.md](resource-rom.md#resource-rom-outcome-matrix).

## Pixel Generation Owner Summary

Concept: this note owns the ROM-local pixel-generation layer after active
render scheduling presents a render work record to `0x1ef6a`. It maps copied
render roots to object-class dispatchers, selects compact/text, segment-list,
encoded-raster, rule, and fixed-list helpers, derives current-band or fallback
destinations, and documents the direct row stores those helpers perform.

Primary route:

- Scheduler owner selects active render work pointer `0x783a18` and band word
  render `+0x10`.
- `0x1ef6a` calls `0x1ef86`, which derives current-band caches
  `0x783a20`, `0x783a22`, `0x783a28`, and destination stride `0x783a1c`.
- `0x1ef6a` then dispatches in fixed order: bucket chain through `0x1efc2`,
  rule list through `0x1f446`, and fixed list through `0x1f756`.
- Bucket objects at render `+0x18` split by object byte `+4`: compact
  `0x00..0x3f` enters `0x1effe`, segment-list `0x40..0x7f` enters
  `0x1f812`, and encoded raster `0x80..0xff` enters `0x1f88e`.
- Compact objects dispatch through `0x1f034`, `0x1f0d2`, `0x1f1f0`, or
  `0x1f264`; rule objects dispatch to solid helper `0x1f596` or pattern
  helper `0x1f4e0`; fixed-list objects render through `0x1f7b0`.

Field groups:

- Canonical render roots: bucket root `+0x18`, rule root `+0x1c`, fixed-list
  root `+0x20`, and context/resource slots `+0x24..+0x60`, all copied by
  `0x1edc6`.
- Canonical object state: bucket object class byte `+4`, selector/mode byte
  `+5`, count/capacity word `+6`, packed coordinate/key word `+8`, and payload
  bytes from `+0x0a`; rule/fixed-list selector, key, dimension, and
  continuation fields documented in the object dispatch checkpoint.
- Derived/cache state: band split and destination caches `0x783a20`,
  `0x783a22`, `0x783a28`, destination stride `0x783a1c`, offset table
  `0x7839f8..`, compact context cache `0x783a2c`, phase byte `0xa001`, and
  fallback buffer base `0x7810b4 + byte_pair_offset`.
- Parser scratch: none. Parser records and delayed payload state have already
  been reduced to page-record objects before publication.
- Firmware bookkeeping: compact phase byte `0x783a46`, wide-mode caches
  `0x783a40..0x783a48`, object continuation fields such as rule `+0x0c` and
  fixed-list `+0x0a`, and exact invalid computed-jump boundaries for compact
  helper out-of-range cases.
- Hardware/external state: physical consumption of the already-rendered band by
  formatter/DC hardware after ROM row-buffer writes.

Writers and readers:

- Page-record producers and bridge write the object roots consumed here:
  `0x12f2e` / `0x1387c`, `0x12714` / `0x13520` / `0x135f0`, `0x13070` /
  `0x13250`, `0x13386` / `0x133aa`, `0x136d2`, and `0x1edc6`.
- `0x1ef86` writes per-band derived caches.
- `0x1efc2`, `0x1effe`, `0x1f812`, `0x1f88e`, `0x1f446`, and `0x1f756` read
  class roots and object fields to choose row helpers.
- `0x1f3d4`, `0x1f414`, and `0x1f626` derive destination pointers and split
  rows between the current band and fallback buffer.
- Row-copy helpers from `0x1fa5c..0x207ac`, compact-wide helper `0x2f27c`,
  encoded-raster mode helpers `0x1f8da`, `0x1f8e6`, `0x1f920`, and `0x1f9c6`,
  segment-list helper `0x1f862`, and rule/fixed helpers write the actual ROM
  row data.

Output effect:

- Pixel composition is direct store in dispatch order, not a hidden
  destination read-modify-write blend. Bucket-chain objects render first,
  rule-list objects render second, and fixed-list objects render third.
- Compact text/downloaded glyph pixels come from the copied render context
  slot plus compact object selector/glyph fields.
- Encoded raster pixels come from queued raster object mode and payload bytes.
- Rule pixels come from queued dimensions, selector/pattern state, and clipped
  continuation rows.
- Segment-list and fixed-list pixels come from their bridged object fields and
  continuation counters.

### Row-Store Primitive Map

- Compact text / downloaded glyph mode `0x00`:
  `0x1effe -> 0x1f034` uses destination helpers `0x1f3d4` /
  `0x1f414`. Row-copy table `0x1f08e` selects byte/word writers under
  `0x1fa5c..0x207ac`; odd widths take the trailing byte from `A3`. Canonical
  inputs are compact entries, selected context `0x783a2c`, glyph fields from
  `0x1f354`, and the coordinate word.
- Compact wide mode `0x10`:
  `0x1effe -> 0x1f0d2` uses the same destination helpers. Full 16-byte chunks
  render through `0x2f27c`, and the remainder renders through table
  `0x1f1ac`. Additional inputs are wide-copy caches `0x783a40..0x783a48` and
  phase `0x783a46`.
- Compact segmented modes `0x20` and `0x30`:
  `0x1effe -> 0x1f1f0` uses `0x1f08e` after vertical/plane pointer adjustment;
  `0x1effe -> 0x1f264` combines that adjustment with `0x2f27c` chunks and
  `0x1f1ac` remainder writes. Inputs are compact entry fields, selected source
  plane, coordinate word, and wide-copy caches for mode `0x30`.
- Segment-list spans:
  `0x1efc2 -> 0x1f812 -> 0x1f862` uses `0x1f3d4` / `0x1f414`. It writes full
  words plus a trailing mask from table `0x308f2`, using six-byte span entries
  from `0x12714 -> 0x13520/0x135f0`.
- Encoded raster:
  `0x1efc2 -> 0x1f88e -> 0x1f8da` copies mode-0 payload words to consecutive
  destination words. Modes `1..3` select `0x1f8e6`, `0x1f920`, or `0x1f9c6`,
  expand payload bytes through tables `0x30914` or `0x30b14`, and store two,
  three, or four destination rows. Canonical inputs are object mode byte
  `+0x05`, count word `+0x06`, coordinate word `+0x08`, and payload `+0x0a`.
- Rule / rectangle:
  `0x1ef6a -> 0x1f446 -> 0x1f596/0x1f4e0` uses destination helper `0x1f626`.
  It stores solid or pattern words after clipping and displacement. Inputs are
  rule selector `+0x05 & 0x0f`, dimensions, key word, and continuation
  `+0x0c`.
- Fixed-list spans:
  `0x1ef6a -> 0x1f756 -> 0x1f7b0` uses destination helper `0x1f626`. It stores
  pattern rows on the fixed-list cadence from bridged fixed-list fields
  `+0x04..+0x0d` and continuation state.

The destination helper column is part of the reproduction contract. Helpers
`0x1f3d4` and `0x1f626` decode the packed coordinate into destination base
`0x783a28`, row-offset table `0x7839f8..`, byte-pair offset, and phase byte
`0xa001`; `0x1f414` and `0x1f626` split rows against current-band count
`0x783a20` and fallback base `0x7810b4`. A supported renderer therefore
derives pixels from object records and these store primitives. It does not
compare rows to an external oracle or infer a separate graphics blend mode.

Evidence:

- `generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst` anchors
  `0x1ef6a`, `0x1efc2`, and compact class dispatch.
- `generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst`
  anchors compact text/downloaded-glyph helper selection.
- `generated/disasm/ic30_ic13_bitmap_draw_core_01f3d4.lst` anchors
  destination, rule, segment-list, and fixed-list helpers.
- `generated/disasm/ic30_ic13_bitmap_encoded_span_modes_01f88e.lst` anchors
  encoded raster modes.
- `generated/disasm/ic30_ic13_bitmap_row_copy_tables_01fa5c.lst` and
  `generated/disasm/ic30_ic13_glyph_row_copy_helper_02f27c.lst` anchor compact
  row-copy tables and wide-glyph row copying.
- The `Bitmap Object Dispatch Semantic Checkpoint`, `Compact Glyph Row-Copy
  Semantic Checkpoint`, encoded-raster helper sections, and fixtures named
  below provide concrete object fields, helper addresses, row-write behavior,
  and exact unresolved computed-jump boundaries.

## Render Helper Boundary Index

This index is the renderer-owner lookup from a bridged page object to the
first helper that can write pixels or stop at an exact ROM-local boundary. It
starts after `0x1edc6` has copied source roots into render roots and after
`0x1ef86` has derived the current-band destination caches. It is not a parser
or command-family index; parser records, payload counts, and command scratch
have already become page objects or selected font/resource state.

Helper routes:

- Compact text and downloaded glyph objects:
  render root `+0x18` contains bucket objects with class byte `+0x04` in
  `0x00..0x3f`. Dispatcher `0x1efc2 -> 0x1effe` loads the selected copied
  context slot into `0x783a2c`, resolves glyph/source rows through `0x1f354`,
  and selects compact helpers `0x1f034`, `0x1f0d2`, `0x1f1f0`, or `0x1f264`.
  Row writes then use `0x1f3d4`, `0x1f414`, row-copy tables rooted at
  `0x1fa5c..0x207ac`, and wide helper `0x2f27c`.
- Segment-list span objects:
  render root `+0x18` also carries class `0x40..0x7f` bucket objects from
  `0x12714 -> 0x13520/0x135f0`. Dispatcher `0x1efc2` selects
  `0x1f812 -> 0x1f862`, which consumes six-byte segment entries and writes
  full words plus a trailing mask from table `0x308f2`.
- Encoded raster objects:
  render root `+0x18` carries class `0x80..0xff` bucket objects from
  `0x105d0 -> 0x13070 -> 0x13250`. Dispatcher `0x1efc2` selects
  `0x1f88e`; object byte `+0x05 & 3` selects literal helper `0x1f8da`,
  two-row expansion `0x1f8e6`, three-row expansion `0x1f920`, or four-row
  expansion `0x1f9c6`.
- Rectangle/rule objects:
  render root `+0x1c` carries the bridged rule list from source root `+0x24`.
  `0x1edc6` has already set selector bit `+0x05.4` and copied height word
  `+0x0a` into continuation word `+0x0c`. Rule dispatcher `0x1f446` sends
  selector `7` to solid helper `0x1f596`; other documented selector lows route
  through pattern helper `0x1f4e0`.
- Fixed-list and landscape span objects:
  render root `+0x20` carries the bridged fixed-list from source root `+0x28`.
  `0x1edc6` has already normalized its continuation fields. Dispatcher
  `0x1f756` runs on the fixed-list cadence and writes rows through
  `0x1f7b0` / `0x1f626`.

Field grouping:

- Canonical render inputs:
  render roots `+0x18/+0x1c/+0x20`, render context slots `+0x24..+0x60`,
  bucket class/selector/count/key fields `+0x04/+0x05/+0x06/+0x08`, bucket
  payload bytes from `+0x0a..`, rule fields `+0x05/+0x06/+0x08/+0x0a/+0x0c`,
  fixed-list fields `+0x04..+0x0d`, selected context longword `0x783a2c`,
  glyph/source records, and raster payload bytes.
- Derived/cache state:
  current-band row count `0x783a20`, remainder `0x783a22`, destination base
  `0x783a28`, stride `0x783a1c`, offset table `0x7839f8..`, phase byte
  `$a001`, fallback base `0x7810b4 + byte_pair_offset`, wide-copy caches
  `0x783a40..0x783a48`, and split counts from `0x1f414` / `0x1f626`.
- Parser scratch:
  none in this index. Delayed payload records and six-byte command records are
  consumed before the page-object producers run.
- Firmware bookkeeping:
  object links, segment counters, rule/fixed continuation mutation, row-copy
  table targets, and invalid computed targets when compact helper indexes move
  outside valid row-copy tables.
- Hardware/external state:
  physical formatter/DC consumption after ROM row-buffer writes. It is not a
  helper input for the ROM-local pixel rows.
- Unknown:
  only the exact residual boundaries named below: compact invalid target or
  source-read stops, missing resource-window bytes, or hardware consumption
  after row buffers already exist.

Writers and readers:

- Writers upstream of this index are page-object producers `0x12f2e`,
  `0x12714`, `0x13070`, `0x13386`, `0x133aa`, `0x136d2`, and bridge
  `0x1edc6`.
- Readers are `0x1efc2`, `0x1effe`, `0x1f812`, `0x1f88e`, `0x1f446`,
  `0x1f756`, destination helpers `0x1f3d4` / `0x1f626`, split helper
  `0x1f414`, and row-copy or expansion helpers selected by each class.
- Output effect is direct ROM row stores to the current-band buffer rooted at
  `0x783a28` or fallback storage rooted at `0x7810b4 + byte_pair_offset`.
  These helpers do not read destination words to perform an implicit
  OR/XOR/AND blend with earlier object classes; overlap is resolved by the
  `0x1ef6a` call order and linked-list order.

Exact residual helper boundaries:

- `0x1f034 -> 0x1f08e`:
  wrapped-width compact mode-0 objects can use an out-of-range span word as a
  row-copy table index; documented examples reach invalid target `0x0066cc`.
- `0x1fe76..0x1fe8a`:
  short compact high-row fallback counts above valid index `128` read code
  bytes as target longwords; documented row `0x0102` reaches target
  `0x329ad3c0`.
- `0x1f264`:
  segmented-wide span-31 high-row fallback can select a source offset beyond
  the modeled payload at `+0xb50`.
- Transparent secondary segment-57 rows:
  the compact renderer route is documented through `0x1f354 -> 0x1f1f0`, but
  rows needing firmware address `0x0c0000..0x0c0321` stop at the missing
  external resource-window boundary.

Evidence:

- Render entry and bridge:
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`,
  `generated/disasm/ic30_ic13_bitmap_state_setup_01ee9e.lst`, and
  `generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`.
- Helper listings:
  `generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst`,
  `generated/disasm/ic30_ic13_bitmap_draw_core_01f3d4.lst`,
  `generated/disasm/ic30_ic13_bitmap_encoded_span_modes_01f88e.lst`,
  `generated/disasm/ic30_ic13_bitmap_row_copy_tables_01fa5c.lst`,
  `generated/disasm/ic30_ic13_glyph_row_copy_helper_02f27c.lst`, and
  `generated/disasm/ic30_ic13_invalid_compact_mode0_target_0066c0.lst`.
- Owner checkpoints:
  [Page Object Storage Outcome
  Matrix](page-record-storage.md#page-object-storage-outcome-matrix),
  [Raster Transfer Decision
  Checkpoint](raster-graphics.md#raster-transfer-decision-checkpoint),
  [Rectangle Outcome Matrix](rectangle-graphics.md#rectangle-outcome-matrix),
  [Downloaded Glyph Boundary Decision
  Rules](firmware-dataflow-model.md#downloaded-glyph-boundary-decision-rules),
  and [Unresolved Boundary Outcome
  Matrix](unresolved-boundaries.md#unresolved-boundary-outcome-matrix).

## Pixel Composition Checkpoint

This checkpoint composes the shared pixel path from an active render record to
ROM-local row stores. It is the practical answer to "where do pixels come
from" after the parser and page-object owners have already produced visible
objects.

Execution order:

- `0x1ef6a` loads active render pointer `0x783a18`, calls setup helper
  `0x1ef86`, then calls bucket dispatcher `0x1efc2`, rule dispatcher
  `0x1f446`, and fixed-list dispatcher `0x1f756` in that order.
- `0x1ef86` derives current-band caches from render work fields:
  row count `0x783a20`, remainder `0x783a22`, destination base
  `0x783a28`, and render work copy at `+0x12`.
- `0x1efc2` reads render root `+0x18` and dispatches bucket objects by class
  byte `+4`: compact/text `0x00..0x3f`, segment-list `0x40..0x7f`, and
  encoded raster `0x80..0xff`.
- `0x1f446` reads rule root `+0x1c` only on five-band boundaries, then
  dispatches solid or patterned rule helpers by object byte `+5 & 0x0f`.
- `0x1f756` reads fixed-list root `+0x20` on the same five-band boundary
  pattern and writes pattern rows through `0x1f7b0`.

Destination selection:

- Compact, segment-list, and encoded-raster helpers use destination helper
  `0x1f3d4`; rule and fixed-list helpers use `0x1f626`.
- `0x1f3d4` decodes packed coordinate `D1`, sets phase byte `$a001`, chooses
  current-band address `0x783a28 + row_offset[coord_high_nibble] +
  byte_pair_offset`, and preserves the byte-pair offset for fallback rows.
- `0x1f414` clips a requested row count against current-band rows
  `0x783a20`; if rows extend beyond the current band, it returns a split
  count with fallback rows in the high word of `D3`.
- `0x1f626` performs the same coordinate and clipping job for rule/fixed
  objects, but also handles vertical displacement before selecting either the
  current-band buffer or fallback base `0x7810b4`.

Composition rule:

- These helpers write generated row words, bytes, or longwords directly to the
  selected destination. The disassembly path uses `move` stores; it does not
  read the old destination word and combine it with a raster operation.
- Overlap is therefore resolved by call order: bucket objects first, rules
  second, fixed-list objects third. Within a bucket chain or list, linked-list
  order controls later stores.
- Fallback rows are not a separate page. They are continuation storage for
  rows that did not fit the current band and are resumed by later render-band
  calls using the same object fields and byte-pair offset.

Evidence:

- `generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`:
  `0x1ef6a..0x1ef7c`, `0x1ef86..0x1efbc`, and `0x1efc2..0x1eff8`.
- `generated/disasm/ic30_ic13_bitmap_draw_core_01f3d4.lst`:
  `0x1f3d4..0x1f436`, `0x1f446..0x1f620`, `0x1f626..0x1f6ec`,
  and `0x1f756..0x1f88c`.
- `generated/disasm/ic30_ic13_bitmap_encoded_span_modes_01f88e.lst`:
  encoded-raster stores selected by object byte `+5 & 3`.
- `generated/disasm/ic30_ic13_bitmap_row_copy_tables_01fa5c.lst` and
  `generated/disasm/ic30_ic13_glyph_row_copy_helper_02f27c.lst`:
  compact and wide glyph row-copy stores selected by compact helpers.

## Page Size Tables

The page-size command handler `ESC &l#A` at `0x00fc74` maps PCL
page-size parameters into internal page codes, stores the code at
`0x782da2`, then rebuilds page geometry.

The page-length command handler `ESC &l#P` at `0x00f9e8` uses the
current line advance `0x783160` to convert line count into a page extent
stored at `0x782dba`. For nonzero lengths it selects an internal page
code from the current orientation thresholds, recomputes geometry, text
length, and cursor state, and refreshes the next printable cursor. A
6-LPI `ESC &l66P!` fixture now reaches parser handlers `0xf9e8` and
`0xd04a`, stores page extent `3300`, and queues `!` at compact text coord
`0x9001`.
The zero-length path now has executable coverage: `ESC &l0P` takes
`0xfa62..0xfaa6`, publishes pending page state through `0xf34a` /
`0xff1e`, waits through `0x9ac2`, optionally emits paper-source output
byte `0x780e8f` and control word `0x780e26`, then enters the shared
geometry refresh at `0xfb4a..0xfc52`. Fixture
`0xf9e8 ESC &l#P converts VMI lines to page length and selects internal
page code` pins fallback default code `2`, `0xf9ac` page extent `3300`,
text bottom `3240`, output byte `0x80`, and control word `1`.

Vertical forms control is now tracked as a composed state block in
`notes/semantic-state-model.md`. The `ESC &l#W` parser final at
`0x011f6e` schedules delayed payload handler `0x12cfe`, which consumes
payload bytes through `0xdace`, loads the table at `0x782dde`, and
updates text-bottom cache `0x782dd2`. The fixture
`ESC &l4W 00 00 00 02 !` checks that the four payload bytes are not parsed as
controls or printable bytes, and that the following `!` still reaches
the page-record queue at compact coord `0x9001`.
Fixture `ESC &l4w4W 00 00 00 02 !` checks the same boundary for the
lowercase-final form: lowercase `w` snapshots record
`80 77 00 04 00 00`, the uppercase `W` does not replace that pending
record, `0x12218` restores the lowercase record, and the payload is
consumed after the uppercase terminator before `!` queues at `0x9001`.

The forward `ESC &l#V` consumer path is now anchored from parser to
visible output. Fixture `ESC &l2V!`, starting from the same VFC table,
routes through handler `0x1280a`, searches channel mask `0x0002` at line
`1`, calls the shared page-root/text helpers `0x10084`, `0xf06e`, and
`0xf34a`, moves y from `126` to `176`, resets x from `40` to left margin
`10`, and queues `!` at compact coord `0xb001`.

The before-top `ESC &l#V` normalization path is anchored into the same
visible output. Fixture `ESC &l2V!` with y `89` below top offset `90`
takes `0x128ae..0x128f4`, computes start line `0`, then finds channel
mask `0x0002` at line `1`. It reaches the same helper sequence
`0x10084`, `0xf06e`, `0xf34a`, moves y to `176`, resets x to `10`, and
queues `!` at compact coord `0xb001`.

The selector-zero target-equal path is also anchored. Fixture
`ESC &l0V!` takes `0x12966..0x1299a`, computes the top-of-form target y
`126`, sees it already equals current y, leaves x/y unchanged, ensures the
page root through `0x10084`, and queues `!` at compact coord `0x9e02`.

The selector-zero top-of-form page-eject path is anchored from queued text
to the next visible page. Fixture `!\x1b&l0V!` starts with a printable
bucket at compact coord `0xbe02`, then routes `ESC &l0V` through
`0x1299c..0x129c4`. The helper sequence `0x10084`, `0xf06e`, `0xf34a`,
`0xf34a`, `0xf124` publishes the old page record, clears the current page
root, resets x from `58` to `10`, recomputes y from `176` to `126`, and
lets the following `!` allocate a fresh page root at compact coord
`0x9001`.

The selector-zero start-after-text recovery path is anchored without
publication. Fixture `ESC &l0V!`, with y `3290`, computes start line
`64`, routes through `0x1299c..0x12b92`, skips `0xf124`, resets x from
`40` to `10`, writes top-of-form y `126`, and queues the following `!`
at compact coord `0x9001`, bucket `6`.

The wrap-hit `ESC &l#V` path is now anchored through publication and fresh
output. Fixture `!\x1b&l2V!` starts at y `226`, queues a printable bucket
at compact coord `0xde02`, misses channel 2 from start line `3` to the
bottom, wraps to line `0`, and finds channel 2 at line `1`. The
`0x129c6..0x12af8` path publishes the old page through `0xf124`, resets x
to `10`, writes y `176`, and queues the following `!` on the fresh page at
compact coord `0xb001`.

The wrap-no-hit `ESC &l#V` path is anchored through publication and fresh
top-of-form output. Fixture `!\x1b&l2V!` starts at y `226` with an empty
VFC table, queues the first printable at compact coord `0xde02`, scans
line `3` through `63`, wraps, and reaches line `3` without a channel-2
hit. The `0x12a22..0x12a78` path publishes the old page through
`0xf124`, resets x from `58` to `10`, writes top-of-form y `126`, and
queues the following `!` on the fresh page at compact coord `0x9001`.

The target-after-text `ESC &l#V` recovery path is anchored through
publication and fresh output. Fixture `!\x1b&l2V!`, with channel 2 at VFC
line `63`, starts with the queued printable at absolute compact coord
`0x4e02` in bucket `198`. Handler `0x1280a` takes
`0x129ee..0x12b5a`, publishes the old page through `0xf124`, enters
bottom recovery, resets x from `58` to `10`, and writes recovered y
`104`. The following printable allocates a fresh page record at compact
coord `0x3001`, bucket `5`. The raster fixture confirms the old published
row is rendered band-local at row `4`, not as `3172` blank rows before
the glyph, while the fresh page renders at band-local row `3`.

The before-top target-after-text `ESC &l#V` recovery path is anchored
without publication. Fixture `ESC &l2V!`, with y `89` and channel 2 at
line `63`, normalizes the search start to line `0`, takes
`0x129fc..0x12afc`, skips the `0xf124` edge at `0x12a12..0x12a1e`,
resets x from `40` to `10`, writes recovered y `104`, and queues the
following `!` at compact coord `0x3001`, bucket `5`.

The empty-table start-after-text `ESC &l#V` recovery path is anchored
without wrap or publication. Fixture `ESC &l2V!`, with y `3290` and no
selector-2 bit in the table, computes start line `64`, takes
`0x12a02..0x12afc`, skips `0xf124`, resets x from `40` to `10`, writes
recovered y `54`, and queues the following `!` at compact coord
`0x1001`, bucket `2`.

The default-table start-after-text `ESC &l#V` path wraps before visible
output. Fixture `ESC &l2V!`, with y `3290`, computes start line `64`,
wraps to the selector-2 bit at line `1`, takes `0x12a7a..0x12af8`, skips
the `0x12a8a..0x12aa2` publication edge, resets x from `40` to `10`,
writes y `176`, and queues the following `!` at compact coord `0xb001`,
bucket `9`.

The line-63 start-after-text `ESC &l#V` path wraps into bottom recovery
without publication. Fixture `ESC &l2V!`, with y `3290` and channel 2
only at line `63`, computes start line `64`, takes `0x12a7a..0x12afc`,
skips the `0x12a8a..0x12aa2` publication edge, writes recovered y `104`,
and queues the following `!` at compact coord `0x3001`, bucket `5`.

The lookup helpers at `0x009d16`, `0x009d4e`, `0x009d86`, and `0x009dbe`
mask the internal code with `0x7f` and index eleven word entries. The
generated table report records all current values. Its manual
cross-check now matches all supported Technical Reference logical page
dimensions: `0x9d16` is portrait logical width, `0x9dbe` is portrait
logical length, `0x9d4e` is landscape logical width, and `0x9d86` is
landscape logical length. The same report also recovers the manual
printable-area margin sums and bottom margins from those four tables for
every supported page size.

Important confirmed mappings:

| PCL size | Code | Index | `0x9d16` | `0x9d4e` | `0x9d86` | `0x9dbe` |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `0x06` | 6 | 2025 | 3030 | 2175 | 3150 |
| 2 | `0x02` | 2 | 2400 | 3180 | 2550 | 3300 |
| 3 | `0x05` | 5 | 2400 | 4080 | 2550 | 4200 |
| 26 | `0x01` | 1 | 2338 | 3389 | 2480 | 3507 |
| 80 | `0x88` | 8 | 1012 | 2130 | 1162 | 2250 |
| 81 | `0x87` | 7 | 1087 | 2730 | 1237 | 2850 |
| 90 | `0x89` | 9 | 1157 | 2480 | 1299 | 2598 |
| 91 | `0x8a` | 10 | 1771 | 2586 | 1913 | 2704 |

Current interpretation:

- `0x9d4e` writes `0x782db2`; the manual match identifies it as
  landscape logical width. Raster transfer bounds check against this
  value.
- `0x9d16` writes `0x782db4`; the manual match identifies it as portrait
  logical width. Raster-start code uses this value while computing a
  remaining byte/line limit.
- `0x9d86` is landscape logical length and `0x9dbe` is portrait logical
  length. These feed the orientation-specific extent and margin
  recomputation paths.
- The complementary orientation width table recovers the current
  orientation's printable length; for example, portrait
  `0x9dbe - 0x9d4e - 60` gives the manual portrait bottom margin.
- `0x9e56` stores the signed remainder of
  `(0x051f - floor(height / 2)) / 16` at `0x782dc0`; for `ESC &l1A`
  letter portrait this yields `11`.

The parser-facing geometry commands compose these table helpers into the page
state later consumed by printable and raster paths. `ESC &l#A` at `0xfc74`
maps the parsed page-size parameter to an internal page code, publishes any
already queued page through `0xf34a`/`0xff1e`, then stores `0x782da2` and
rebuilds the derived geometry caches through `0xf9ac`, `0x9d4e`, `0x9d16`,
`0x9e56`, `0xf87e`, `0xea16`, `0xe9ba`, `0xf8fc`, `0xfe54`, and `0x12b96`.
`ESC &l#O` at `0x10220` uses the same publication-before-change rule before
writing `0x782da3`, recomputing orientation-sensitive fields, reloading
thresholds through `0x103ea`, deriving VMI `0x783160`, and refreshing current
font metrics. `ESC &l#P` at `0xf9e8` either selects a page code from VMI-scaled
line count thresholds or, for parameter `0`, selects `0x780e97` / fallback
`2`; both accepted paths enter the same geometry refresh block. Evidence
anchors in `tools/render_fixture_harness.py` record `ESC &l1A` as page code
`6` with width `3030`, height `2025`, portrait margin `3150`, top offset
`90`, and printable extent `3090`; PCL page size `80` as internal code
`0x88` masked to table index `8`; `ESC &l1a1O` through handlers `0xfc74` and
`0x10220`; and `ESC &l66P` as computed extent `3300`.

The visible-output rule for these commands is also ROM-local: if a printable
byte has already allocated a compact text bucket, the geometry handler
publishes that current root before installing new page state. The mixed
`! ESC &l1A` and `! ESC &l1O` evidence streams allocate the page-record root
on the printable step, publish the queued bucket at the geometry handler's
`0xf34a`/`0xff1e` boundary, and only then apply the new page-size or landscape
fields. The pixels for that published record therefore come from the
pre-command page root and render bridge; subsequent bytes consume the updated
geometry caches.

## Orientation

`ESC &l#O` at `0x010220` accepts values below `2`. If the requested
orientation differs from `0x782da3`, it updates `0x782da3`, rebuilds
page geometry, and refreshes current cursor/font state.

Orientation-sensitive geometry work includes:

- `0xf9ac`: chooses table `0x9dbe` for orientation 0 and table `0x9d86`
  for orientation 1, storing the result at `0x782dba`.
- `0xf87e`: sets `0x782dbe` to `0x003c` in orientation 0 and `0x0032` in
  orientation 1, then swaps `0x782db2` / `0x782db4` into `0x782db6` /
  `0x782db8` depending on orientation.
- `0x103ea`: reloads orientation-specific values into `0x782daa`,
  `0x782dac`, `0x782dae`, and `0x782db0`.

The `ESC &l1O` evidence stream starts from letter portrait, changes
orientation to landscape, and records active extents `2025x3030`, landscape
margin `2175`, printable extent `2125`, top offset `100`, and the `0x103ea`
landscape threshold sequence `2175, 2550, 2480, 2550`.

The coordinate helper group at `0x0104d8..0x010550` converts between
whole coordinates and a packed fixed-point form with 12 subunits per
whole unit. `0x104d8` clamps signed subunits to `-0x5ffff..0x5ffff`,
divides by `12`, and normalizes negative remainders into packed
whole/fraction form. `0x104fe` reverses that representation by multiplying
the whole word by `12` and adding the fraction word. `0x10510` subtracts
packed pairs by negating the second pair before entering `0x10518`; `0x10518`
adds whole/fraction pairs, clamps the whole part through `0x104f0` with limit
`0x7ffe`, carries fractions `>= 12`, and borrows negative fractions through
the `0x10548` fixup. `0x10550` is derived projection math used by HMI/default
advance code; it does not read parser state or page objects directly.

These helpers write no RAM by themselves. Their return values become pixel-affecting
only when callers store them into canonical placement fields: cursor x/y `0x782c8a` /
`0x782c8e`, HMI/VMI `0x78315c` / `0x783160`, rectangle and raster-origin fields such as
`0x783170+0x0a`, or page-layout bounds used by later queueing. Direct-control formulas
and caller evidence are owned by
[direct-control-codes.md](direct-control-codes.md#cursor-and-dot-position-route-checkpoint).
The raster owner consumes the same packed-coordinate contract when `0x1075a` seeds
raster origin from the current cursor and when `0x105d0` advances the active row
position before `0x13070` queues encoded raster objects.

## Raster Graphics State

Raster-related PCL handlers:

| Command | Handler | Current role |
| --- | --- | --- |
| `ESC *t#R` | `0x010808` | raster resolution |
| `ESC *r#A` | `0x01075a` | start raster graphics |
| `ESC *r#B` | `0x0107fa` | end raster graphics |
| `ESC *b#W` | `0x011f82` -> `0x0105d0` | transfer raster row bytes |

[raster-graphics.md](raster-graphics.md) documents the command edge,
delayed `0x121cc` / `0x12218` payload handoff, page-root queueing through
`0x10084` / `0x13070` / `0x13250`, payload copy through `0x138de`, and
render dispatch through `0x1edc6` / `0x1efc2` / `0x1f88e`.

The raster state block is rooted at `0x783170` in the handlers.

Observed fields:

| Offset | Access | Current interpretation |
| ---: | --- | --- |
| `+0x00` | word | start/baseline coordinate word copied from field `+0x0a` |
| `+0x02` | word | whole coordinate during row transfer |
| `+0x04` | word | bytes accepted or clipped for current row |
| `+0x06` | word | excess bytes beyond accepted row count |
| `+0x08` | word | resolution scale minus one |
| `+0x0a` | long | start/baseline coordinate copied from current cursor state |
| `+0x0e` | word | raster scale: 1, 2, 3, or 4 |
| `+0x10` | word | max byte count from page extent and raster scale |
| `+0x12` | byte | raster-active / initialized flag |

`ESC *t#R` maps the requested resolution into a scale:

| Requested value range | Stored scale |
| --- | ---: |
| `> 150` | 1 |
| `101..150` | 2 |
| `76..100` | 3 |
| `<= 75` | 4 |

This is consistent with a `300 dpi / requested dpi` scale for 300, 150,
100, and 75 dpi raster modes.

`ESC *r#A` initializes the state block only if field `+0x12` is clear.
With parameter `1`, it seeds field `+0x0a` from one current cursor
coordinate; otherwise it clears it. This pins the cursor variable names
used elsewhere:

- orientation 0: seed from horizontal cursor `0x782c8a`;
- orientation 1: seed from vertical cursor `0x782c8e`.

The executable raster-origin fixture now pins this explicitly: portrait
`ESC *r1A` uses `0x782c8a`, landscape `ESC *r1A` uses `0x782c8e`, and
`ESC *r0A` clears the origin to the left edge. It then computes field
`+0x10` from page extent, the baseline word, and `scale * 8`; this is
the clipped maximum byte count for subsequent row transfers.

`ESC *b#W` does not call the transfer routine immediately. Handler
`0x011f82` stores delayed handler pointer `0x0105d0` through `0x0121cc`;
the later payload dispatcher restores the parsed six-byte command record
and either calls the saved handler in normal mode or diverts alternate/data
payloads through `0x12358 -> 0xdace -> 0xe002`. The executable
harness now pins the standalone `0x121cc` snapshot bytes for a parsed
`ESC *b4W` record and the `0x12218` restore/dispatch contract. It also
walks the primary `ESC *t300R` / `ESC *r1A` / `ESC *b4W` byte stream
through the ROM dispatch table used by parser loop `0x11774`, proving
the final handlers `0x10808`, `0x1075a`, and `0x011f82` are selected
before `0x12218` restores and dispatches `0x0105d0`. The modeled raster
command/data stream then carries the same parsed-record, snapshot-byte,
and restore-dispatch evidence on its `ESC *b4W` transfer event before
queueing the payload row. A second parser-to-gate edge check uses
`ESC *t300R` / `ESC *r0A` / `ESC *b4W` to tie the same ROM parser
handlers and restored `0x0105d0` command record to both capped queueing
and beyond-extent drain/no-row-advance outcomes. The delayed raster
payload path now uses the same `0x12328` / `0xdace` normalized-byte
reader as the generic payload fixtures: a raw row payload
`f0 1a 58 aa 55` for `ESC *b4W` contributes four queued bytes
`f0 00 aa 55`, with `1a 58` counted as one control hit before
page-object queueing and rendering.

The restore handoff is no longer an opaque register edge. Disassembly
`generated/disasm/ic30_ic13_payload_dispatch_011f82.lst` shows `0x121cc`
storing pending byte `0x782a1a`, handler longword `0x782a1c`, and saved
record bytes `0x782a20..0x782a25`. `0x12218` restores those bytes to the
parser-record buffer, advances `0x78299e`, and directly calls the saved
handler through `jsr (A2)` when wrapper byte `0x782c18` is clear. The
handler `0x105d0` then rewinds `0x78299e` by six at `0x105e4..0x105ec`
and reads the restored record word `+2` as the byte count at `0x105f2`.

The transfer routine at `0x0105d0`:

- reads the byte count parameter from the parsed command record;
- sets raster field `+0x12`;
- clips or skips input bytes by repeatedly calling `0xdace`;
- calls `0x10084` to ensure a page/image buffer is allocated;
- calls `0x13070` with the raster state block when row data is in
  bounds;
- advances current cursor state after the row transfer and clamps
  against `0x782dc6`.

The executable harness now pins four `0x105d0` gate cases before the
`0x13070` queue call: a row at the inclusive page extent still queues
and renders before advancing to the next row, a row beyond the page
extent enters the positive-count `0xdace` drain loop without queueing, a
negative row ensures the root and uses the same positive-count drain
loop without queueing, and a byte count larger than raster field `+0x10`
ensures the modeled page root through `0x10084`, stores the capped count
in `+4` and the overflow count in `+6`, then queues only the capped
bytes. At `0x1065c..0x10698` and `0x106b6..0x106f6`, nonpositive counts
return without payload reads, and a `0xdace` `-1` return exits early. The
parser-restored `ESC *b4W` stream now also checks the off-page
row-counter distinction: `row_y == page_extent` queues and advances to
`page_extent + 1`, beyond-extent rows do not advance `row_y`, and a
negative row advances `row_y` from `-1` to `0` only after a non-`-1`
drain result.

## Page Object Queues

The transfer routine does not draw directly into a final bitmap. It
queues a raster row object under the current page root at `0x78297a`.

`generated/analysis/ic30_ic13_page_root_allocation.md` now details the
`0x10084` / `0x10110` allocation boundary, and
`generated/analysis/ic30_ic13_page_root_finalization.md` details the
shared `0xff1e` publish-or-clear boundary used by reset, FF,
page-geometry changes, text retry, and raster page-boundary paths. The
modeled `0xff1e` publication now carries the concrete page/control
pool-record header fields for state byte `+4`, environment byte/word
`+7/+0x0c`, status byte/bits `+8/+0x0a`, copied root word
`+0x16 -> +0x1a`, cleared word `+0x18`, queue roots, and context slots
before the `0x1edc6` render bridge. `0x10084` ensures the current page
object root exists. On first allocation, it:

- returns without reinitialization when `0x78297a` already names a
  current root;
- runs helper `0x9ac2` first when pending bytes `0x782c73` or `0x782c72`
  are set, then clears both latches;
- calls allocator `0x9a9a`;
- stores the root pointer in `0x78297a`;
- clears stream-allocation state `0x782a70`;
- seeds stream link pointer `0x782a72` to page-root `+0x20`;
- initializes page-root fields through `0x10110`, including page code
  `+6`, root flags `+8/+0xa/+0x14`, list heads `+0x20/+0x24/+0x28`, and
  dimension/band fields `+0x09/+0x16`;
- clears the 16 font context slots and installs the selected
  current-font context longword into root slot `+0x2c`;
- leaves stream next-free pointer `0x782a76` to the later 0x100-byte
  chunk allocator path;
- clears 256 longwords through the pointer at page-root offset `+0x1c`.

Current page-root fields:

| Root offset | Current interpretation |
| ---: | --- |
| `+0x1c` | array of bucket heads indexed by `0x782a7c` |
| `+0x20` | start of display-list 0x100-byte chunk chain |
| `+0x24` | linked-list head used by rectangle/rule-like objects |
| `+0x28` | second linked-list head used by another rectangle/rule mode |
| `+0x2c..+0x68` | 16 selected context/resource longword slots |

The context slots are copied from the selected longwords stored in the
`0x782ee6` / `0x782ef6` current-font records.

`0x132b6` and `0x1381c` implement a small stream allocator over
0x100-byte chunks:

- `0x782a70`: bytes remaining in the current chunk.
- `0x782a72`: pointer to the link field of the current chunk.
- `0x782a76`: next free byte in the current chunk.
- new chunks are allocated via `0x1710` and chained through their first
  longword, leaving `0xfc` payload bytes.

The executable harness now pins the `0x1381c` accounting directly: first
allocation links a new chunk through `0x782a72`, returns `chunk+4`, and
leaves `0xfc - size` bytes; same-chunk reuse advances only `0x782a76` /
`0x782a70`; crossing the remaining-byte limit links the next chunk
through the prior chunk's first longword.

An address-aware `0x1387c` fixture now ties that storage to bucket
objects: first allocation writes the selector at object `+4` and stores
the object pointer in the `+0x1c` bucket head, reuse returns the same
object while count `+6` is below capacity, and a full matching object
allocates a new head whose longword `+0` points at the prior object.

An address-aware `0x133aa` fixture now ties the same stream storage to
the rectangle/rule list rooted at page offset `+0x24`. It allocates
14-byte objects through `0x1381c`, writes the `+0` next pointers, and
pins the bucket-byte insertion order observed in `0x13472`: lower
buckets insert before the current head, higher buckets append after
lower entries, and equal-bucket entries are inserted after the existing
equal entry.

Fixture `0x133aa no-room return preserves rule-list head` pins the local
allocation-failure branch at `0x133c2..0x133d0`: when `0x1381c` returns
zero, `D7` returns zero, root `+0x24` stays at `0x00d02f00`, the existing
14-byte node is unchanged, and stream bookkeeping
`0x782a70`/`0x782a72`/`0x782a76` is unchanged.

An address-aware `0x136d2` fixture now pins the paired list rooted at
page offset `+0x28`. It uses the same 14-byte `0x1381c` allocation
contract, writes byte `+5` from the normalized fixed/rule mode, and
confirms the same bucket-byte ordering for lower, higher, and equal
entries before the `0x1edc6` bridge converts it into render-record
`+0x20` fixed-list shape.

Fixture `0x136d2 no-room return preserves fixed-list head after search`
pins the paired local failure branch at `0x1371a..0x13734`: the
non-empty list is searched first through `0x13690`, visiting
`0x00d03f00` and `0x00d03f10`; when `0x1381c` then returns zero, `D7`
returns zero, root `+0x28` stays at `0x00d03f00`, both existing nodes
are unchanged, and stream bookkeeping remains unchanged.

The addressed storage fixtures now also compose into a single page-record
shape before publication: one compact text bucket under `+0x1c`, one
rectangle/rule object under `+0x24`, and one fixed/rule object under
`+0x28` are allocated from the same `0x1381c` chunk, materialized by
following their `+0` links, published through `0xff1e`, and bridged
through `0x1ed84` / `0x1edc6` into render-record `+0x18`, `+0x1c`,
and `+0x20` fields. `notes/semantic-state-model.md` now composes this
as the shared page-record storage model instead of repeating the
allocator concepts separately for text, rule, fixed-rule, and raster
producers.

### Page-Record Storage Semantic Checkpoint

This checkpoint covers the shared page-record state block used by compact
text, rule, fixed-rule, raster, publication, and render-entry paths. It is a
software-visible boundary: it documents how producers build canonical page
objects, not how the engine eventually clocks paper.

See [page-record-storage.md](page-record-storage.md) for the standalone
renderer-facing storage and publication contract.

Field groups:

- Canonical page root:
  - `0x78297a`: current page/control root pointer.
  - root `+0x1c`: bucket-head array for compact text and raster objects.
  - root `+0x20`: head/link slot for 0x100-byte stream chunks.
  - root `+0x24`: rectangle/rule list head.
  - root `+0x28`: fixed-rule list head.
  - root `+0x2c..+0x68`: sixteen current-font context slots.
- Canonical object fields:
  - bucket objects: `+0` next pointer, `+4` selector/class byte, `+6`
    count/capacity, payload from `+8` or `+0a`.
  - rule and fixed-rule objects: `+0` next pointer, `+4` bucket byte,
    `+5` selector/mode, `+6` key, dimensions or extent from `+8`.
- Derived/cache producer keys:
  - `0x782a7c`: bucket index / list-order key.
  - `0x782a7d`: rule/fixed selector byte copied into object `+4`.
  - `0x782a7e`: compact coordinate or rule key copied into object `+6`.
  - `0x782a7a` and `0x782a7b`: compact text selector bytes used by
    `0x1387c` callers.
- Firmware bookkeeping:
  - `0x782a70`: bytes remaining in the current stream chunk.
  - `0x782a72`: pointer to the current chunk link field.
  - `0x782a76`: next free byte in the current chunk.
  - `0x782c72` and `0x782c73`: pending latches cleared by first-root
    allocation after the `0x9ac2` wait hook.
  - `0x782990`: transient page-root byte cleared by `0x10084`.
- Derived/cache render fields:
  - `0x783a20`, `0x783a22`, and `0x783a28` are render-band outputs of
    `0x1ef86`; they are not canonical page-record fields.
- Parser scratch:
  - none newly assigned in this allocator cluster. Parser scratch enters
    through command records such as the raster delayed record restored by
    `0x12218`.
- Unknown:
  - physical/MMIO timing that decides when scheduler wait objects wake or
    capacity changes. The ROM-visible published-record, bridge, and render
    handoff fields are documented below.

The heap allocator itself is not an unresolved page-record edge here.
`0x1381c` owns the page-root stream-link side effects after `0x1710` succeeds
or fails; the shared allocator bitmap/free contract for `0x170c`, `0x1710`,
and `0x18b4` is composed in `Macro Definition And Data-Chain Replay` in
[semantic-state-model.md](semantic-state-model.md).

Writers:

- `0x10084` creates the current root when `0x78297a` is empty, clears
  `0x782a70`, seeds `0x782a72 = root + 0x20`, clears `0x782990`, and calls
  initializer `0x10110`.
- `0x10110` writes root page code byte `+6`, status/flag fields
  `+8/+0a/+14`, geometry/band fields `+09/+16`, list heads `+20/+24/+28`,
  and selected current-font context slot `+2c`.
- `0x1381c` allocates variable-sized stream objects, updating
  `0x782a70`, `0x782a72`, and `0x782a76`; when the current chunk cannot
  satisfy a request, it links a new chunk through the prior link field.
- `0x1387c` writes root `+0x1c` bucket heads and bucket objects for compact
  text and raster producers.
- `0x133aa` writes root `+0x24` and inserts rectangle/rule nodes by bucket
  byte order.
- `0x136d2` writes root `+0x28` and inserts fixed-rule nodes with the same
  ordered-list contract.
- `0xff1e` publishes the root fields into pool-record fields, and
  `0x1edc6` copies the published bucket/rule/fixed/context roots into
  render-record fields `+0x18`, `+0x1c`, `+0x20`, and `+0x24`.

Readers and consumers:

- Printable text through `0xd04a` / `0x12f2e` consumes the current root and
  `0x1387c` bucket allocator.
- Rectangle fill through `0x10898` consumes the current root and inserts a
  rule node through `0x13386` / `0x133aa`.
- Raster transfer through `0x105d0` consumes the current root and queues
  encoded-span objects through `0x13070` / `0x13250`.
- Publication through `0xff1e` consumes bucket, list, and context root fields.
- Rendering through `0x1ed84` / `0x1edc6` / `0x1ef6a` consumes the published
  or active page record and dispatches compact, encoded-span, rule, and
  fixed-list objects.

Output effect:

- The allocator does not draw pixels by itself. It determines object order,
  bucket selection, and list roots consumed by visible rendering.
- Fixture `addressed text/rule/raster field groups reach publication and
  render entry` checks text object `0x00d0c004`, rule object `0x00d0c02a`,
  and raster object `0x00d0c038` share the addressed page-record state, then
  publish and render into the expected mixed rows.
- Fixture `addressed text/rule/multi-row raster publication preserves
  bucket chain` extends that addressed state to two consecutive raster
  objects at `0x00d0d038` and `0x00d0d044`, preserving bucket-chain order
  through publication and render.
- Fixture `addressed page-record writers share 0x1381c across chunk
  rollover` checks one page-root stream crossing a chunk boundary:
  `root + 0x20 -> 0x00d05000 -> 0x00d05100`, final bookkeeping
  `0x782a70 = 0x00ba`, `0x782a72 = 0x00d05100`, and
  `0x782a76 = 0x00d05146`, followed by publication and compact rendering.

Evidence status:

- Page-root creation side effects, stream allocator accounting,
  bucket reuse/new-head behavior, rule/fixed insertion order, root
  publication, render-record field copies, active-record handoff, and
  ROM-derived row construction are grounded in the cited ROM paths.
- Physical scheduler pacing is a hardware/MMIO boundary, not a gap in the
  page-record storage contract. The ROM-visible scheduler
  branch fields are owned by
  [active-render-scheduler.md](active-render-scheduler.md). The shared
  `0x170c` / `0x1710` / `0x18b4` heap contract is covered in
  [pcl-parser-firmware.md](pcl-parser-firmware.md) and the semantic model.

Fixture evidence:

- `0x10084-modeled page-root allocation side effects`
- `0x10110 page-root initializer installs selected context slot`
- `0x10110 page-root initializer copies geometry fields`
- `0x1381c stream allocator chunks display-list storage`
- `0x1387c address-aware bucket allocation uses 0x1381c storage`
- `0x133aa address-aware rule-list insertion uses 0x1381c storage`
- `0x133aa no-room return preserves rule-list head`
- `0x136d2 address-aware fixed-list insertion uses 0x1381c storage`
- `0x136d2 no-room return preserves fixed-list head after search`
- `addressed stream page record materializes through 0xff1e and 0x1ed84`
- `addressed page-record writers share 0x1381c across chunk rollover`
- `addressed text/rule/raster field groups reach publication and render
  entry`
- `addressed text/rule/multi-row raster publication preserves bucket chain`

Disassembly evidence:

- `generated/disasm/ic30_ic13_page_root_allocate_010084.lst`:
  `0x10084..0x1021e`.
- `generated/disasm/ic30_ic13_display_list_helpers_013386.lst`:
  `0x13386..0x1387a` and `0x1387c..0x138de`.
- `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`:
  compact text callers of `0x1387c`.
- `generated/disasm/ic30_ic13_raster_object_queue_013070.lst`:
  encoded-span producer path.
- `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst` and
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`:
  publication and render bridge consumers.

Unresolved middle edges:

- `0x10084..0x1381c`: first-root setup, same-chunk reuse, and second-chunk
  rollover are documented from the disassembly and exercised by fixtures.
  New ROM-local page-record work here starts only from byte streams that expose
  a new page-root topology, allocator transition, object byte shape,
  publication field, bridge field, or render input.
- `0x13250..0x1381c`: raster encoded-span allocation is composed here and in
  [raster-graphics.md](raster-graphics.md). Parser dispatch, delayed record
  restore, gate outcomes, addressed `0x13250` storage, and render-entry rows
  are documented by tracing the ROM path and exercised by fixtures. The
  parser-to-handler record handoff is disassembly-pinned through `0x121cc`,
  `0x12218`, and `0x105d0` re-reading `0x78299e - 6`; the dense split branch
  rule is disassembly-pinned through
  `0x132b6..0x13382`, including the static `0x00f2 + 0x003a`
  capped-new-chunk chain and `0x000a` current-tail capacity example in
  [raster-graphics.md](raster-graphics.md#dense-row-split-composition-checkpoint).
  The remaining closure boundary is byte streams that change a concrete
  raster field or branch: accepted count or drain result at `0x105d0`,
  encoded object fields `+0x04/+0x05/+0x06/+0x08/+0x0a..`, split allocator
  state `0x782a70/0x782a72/0x782a76/0x782a80`, bridge bucket roots,
  copy-stop byte `0x782996`, packed-key advance through `0x332ee`, or
  mode-specific `0x1f88e` row construction.
- `0x133aa..0x13472` and `0x136d2..0x13734`: ordered insertion is pinned for
  lower, higher, and equal bucket bytes, and local no-room returns are
  fixture-backed for both root `+0x24` and root `+0x28`. The parser-produced
  selector path is no longer a generic allocation-chain gap: `0x10898` through
  `0x13386` / `0x133aa` is composed in
  [rectangle-graphics.md](rectangle-graphics.md) for selector-7, gray,
  pattern, landscape-remap, clipping, no-room retry, addressed storage,
  publication, and mixed text/rule/raster streams. New ROM-local rectangle/list
  work starts only from byte streams that change clipped source fields, list
  ordering, object bytes, `0x1381c` rollover/allocation state, retry
  publication fields, bridge fields, render dispatch, or ROM-derived row
  construction beyond the documented selector matrices.
- `0xff1e..0x1ed84`: pool-record publication, render bridge, and the
  scheduler-produced multi-band render loop are modeled. Fixture
  `0x1eba4/0x1ef6a active render loop advances or yields bands` covers render,
  capacity-wait, throttle, and cleanup branches around `0x1eba4..0x1ecd2`, and
  fixture `0x1eba4 scheduler band words render published downloaded glyph` feeds
  scheduler-produced band words `0..9` into `0x1ef6a`. Residual scheduler work
  is hardware/MMIO event source and pacing correlation for the events that wake
  or stall those modeled branches, not a render-record bridge gap.

`0x13070` converts the raster state block into bucket coordinates:

- stores a bucket/index value at `0x782a7c`;
- stores a packed coordinate/key at `0x782a7e`;
- allocates a bucket object through `0x13250`;
- links that object under `page_root+0x1c + 4 * 0x782a7c`;
- stores raster row payload bytes immediately after the object header.

The bucket object layout, as currently observed for raster rows:

| Object offset | Meaning |
| ---: | --- |
| `+0x00` | next pointer in bucket chain |
| `+0x04` | object class/key byte, initialized to `0x80` by `0x13250` |
| `+0x05` | row scale/type byte copied from the raster state argument |
| `+0x06` | allocator chunk byte count or payload capacity marker |
| `+0x08` | packed coordinate/key from `0x782a7e` |
| `+0x0a` | start of raster payload bytes copied from the host stream |

`0x138de` is the first confirmed payload-storage routine for raster
data. It reads bytes through host byte routine `0xa904`, handles
embedded `0x1a 0x58` by calling `0xd99a`, writes bytes to the object
payload pointer, and decrements the source raster-state byte count at
offset `+0x04`.

Rectangle/rule-like graphics share the same storage system but use the
linked lists rooted at page offsets `+0x24` and `+0x28`. The entry
`0x13386` calls `0x134d6` to compute the same packed ordering keys, then
inserts an object via `0x133aa`. If that insert reports no room, the
rectangle path at `0x10d22..0x10d3e` marks page-root flag bit
`root+0x15.0`, finalizes through `0xff1e`, ensures a fresh root through
`0x10084`, and retries the same source record. Follow-up routines around
`0x13520..0x1381c` handle the second rectangle/rule mode and allocate
entries through the same 0x100-byte stream allocator.

Text also enters the page-object queue layer rather than drawing
directly. The text-span flush path at `0x12714` packages a pending span
into the rectangle/rule-like queue by calling `0x13520`; if insertion
reports no room it marks page-root flags at `root+0x14` and retries
after `0xff1e` / `0x10084`. The text object builder at `0x12f2e`
computes the same `0x782a7c` bucket index and packed coordinate key,
then allocates queue entries through `0x1387c`.
`generated/analysis/ic30_ic13_compact_bucket_allocator.md` decodes that
helper: it indexes the page-root `+0x1c` bucket array by `0x782a7c`,
reuses an object with matching selector word `+4` while count `+6` is
below capacity, or allocates and links a new head object through the
shared stream allocator. Its entries store mapped glyph payload data
after a short object header, parallel to raster row payload storage.
The paired text-source allocation boundary is now fixture-backed for
both source writers. Unflagged writer `0xd3b2` and flagged writer
`0xd824` both call `0x12f2e` with positioned source object `0x782d7e`,
and both retry after a no-room return through `0xd47a..0xd4a0` /
`0xd8ca..0xd8f0`. Fixture `0xd3b2 and 0xd824 text queue no-room retry
preserves source and rows` forces the addressed `0x12f2e` allocation
failure, sets page-root retry flag `+0x14.0`, publishes the old compact
bucket through `0xff1e`, ensures a fresh root through `0x10084`, retries
the preserved source pointer `0x00d06004`, and renders rows from the published
bucket through `0x1effe`.

The short-object retry contract is exact for both source families:

- flagged `0xd824` source tuple
  `(mapped=0x20, flag=1, x=16, y=0, slot=0)` first tries to allocate
  object size `0x26`, receives pointer `0`, publishes old bucket prefix
  `00 00 00 00 00 00 00 01 20 00 01`, retries at object pointer
  `0x00d06004`, and renders the same 22 rows with digest
  `235986bdd28abaaef315961960ac87d846cbb5228ca5c07ef560df56501a30e3`.
- unflagged `0xd3b2` source tuple
  `(mapped=0x01, flag=0, x=22, y=22, slot=3)` uses the same retry sequence,
  publishes/retries bucket prefix `00 00 00 00 00 03 00 01 01 66 01`,
  dispatches bucket word `1` through `0x1effe`, and renders the same 22 rows
  with digest
  `d696456ad5c91a1a568d1b1c45fcf7e322fe15c12a3805783145ccc7074806e6`.

Fixture `0xd3b2 and 0xd824 segmented text queue no-room retry preserves
source and rows` extends the same retry contract to tall/segmented text
objects. The unflagged rows-`0x81` case retries bucket words `9` and
`1`; the flagged tall built-in space-glyph case retries all nine bucket
indexes `0..64`. Selected published and retried buckets render the same
ROM-derived rows through `0x1effe`. The remaining uncertainty is selector-mode
cross-products only when they change source fields, allocator retry behavior,
bucket shapes, helper dispatch, fallback split, or ROM-derived
row-construction inputs; it is not the paired no-room return semantics or row
contract for these source families.

The segmented retry contract is also exact:

- unflagged `0xd3b2` segmented source
  `(mapped=0x01, flag=0, x=22, y=22, slot=3)` fails first at bucket `9`,
  segment `1`, selector `0x2003`, object size `0x28`; retry emits bucket
  `9` object `00 00 00 00 20 03 00 01 01 01 66 01` and bucket `1`
  object `00 00 00 00 20 03 00 01 01 00 66 01`. Published and retried
  rows use the same bucket-word paths `9` and `1` with digests
  `ab4ebb802552dc6ad497da75344f369876cc9f0fabbffdfc7801213b9a7ff372` and
  `918ec4cca20024057ec1b82577b2ab5c039c6fc9a3f756be9bbb62a088bab7ac`.
- flagged `0xd824` tall built-in source
  `(mapped=0x1f, flag=1, x=0, y=0, slot=0)` fails first at bucket `64`,
  segment `8`, selector `0x2000`; retry emits bucket indexes
  `[0, 8, 16, 24, 32, 40, 48, 56, 64]`, with first prefix
  `00 00 00 00 20 00 00 01 1f 08 00 00` and last prefix
  `00 00 00 00 20 00 00 01 1f 00 00 00`. Published and retried rows use the
  same bucket-word paths `64` and `0` with digests
  `c2c1504836f113d5a2c89168702ccb008dcc93126cfcf55a57964ba889170318` and
  `15b6d4e1c1691ca7d6204259f3dfff5c96575588c0c71c8ff011898581be4f35`.

`generated/analysis/ic30_ic13_printable_text_path.md` anchors the live
normal parser path into that source-object builder. Routine `0x11774`
fetches bytes through `0xda9a`, and when parser state `0x782999` is
zero, alternate/data mode `0x782c18` is clear, and the byte is not
claimed by a command table, it calls printable entry `0xd04a`. `0xd04a`
builds scratch source object `0x782d7e` by calling
`0x1393a(host_byte, 0x782d7e)`, then branches to `0xd550` when source
byte `+0x10` is nonzero or `0xd140` when it is zero.

`generated/analysis/ic30_ic13_text_cursor_span_flow.md` splits the
post-`0x1393a` path into paired cursor/queue/span routines. The
unflagged path is `0xd140` -> `0xd28a` -> `0xd3b2` -> `0xd4ac`; the
flagged path is `0xd550` -> `0xd6bc` -> `0xd824` -> `0xd8fc`. The queue
handoffs `0xd3b2` and `0xd824` write source fields `+0x12`, `+0x14`, and
`+0x16`, mark the current page-root font slot live at `0x78297f + slot`,
and call `0x12f2e`. The span updates `0xd4ac` and `0xd8fc` are separate
context-record updates that can flush pending text through `0x12714` /
`0x126e2`.

`generated/analysis/ic30_ic13_text_glyph_index_flow.md` pins down the
compact glyph byte inside that path. Routine `0x1393a` maps the original
character byte through either `0x782f32` or `0x783032`, selected by
`0x782f06`, and stores the mapped byte as the low byte of text object
word `+0x0a`. The later queue builder `0x12f2e` copies source byte
`+0x0b` into the first byte of each compact payload entry. Therefore the
byte consumed by `0x1f354` is the active character-map result, not
necessarily the original host byte.

This confirms a common page-object model:

- raster rows
  - Entry routine: `0x13070`
  - Queue root: page-root `+0x1c` bucket array
- text / glyph spans
  - Entry routine: `0x12714`, `0x12f2e`
  - Queue root: page-root `+0x1c` bucket array plus shared
    display-list storage
- rectangles / rules
  - Entry routine: `0x13386`, `0x13520`
  - Queue root: page-root `+0x24` / `+0x28` linked lists plus shared
    display-list storage

## Render/Banding Bridge

The first confirmed bridge from queued page/control records toward the
bitmap renderer is `0x1ed84..0x1ee9c`.

`0x1ed84` copies metadata from the active page/control record at
`0x780eae` into a selected work record, then calls `0x1edc6`. The
surrounding alternator at `0x1ecd6` publishes the selected work record
at `0x783a18` and calls `0x1ee9e` when record geometry changes.

`0x1edc6` copies queue/list pointers from the source record into the
destination render record:

| Source offset | Render-record offset | Current interpretation |
| ---: | ---: | --- |
| `+0x1c` | `+0x18` | bucket-head array copied from page/control record |
| `+0x24` | `+0x1c` | linked object list copied from page/control record |
| `+0x28` | `+0x20` | second linked object list from page/control record |
| `+0x2c..+0x68` | `+0x24..+0x60` | 16 selected context/resource longwords |

After copying, `0x1edc6` normalizes objects in the destination lists: it
sets flag bit `0x10` in object byte `+5`; for the `dest+0x1c` list it
copies word `+0x0a` to `+0x0c`; for the `dest+0x20` list it copies word
`+8` to `+0x0a` and sets bytes `+0x0c=1`, `+0x0d=8`.

[font-context-metrics.md](font-context-metrics.md) documents the `+0x2c`
interpretation: `0xc428` / `0xc4fc` install selected context/resource
longwords copied from current-font records in these 16 page-root slots, not
raw glyph bitmap pointers. `0x1edc6` copies them to render-record slots, and
compact text/glyph objects use byte `+5` low nibble to select one of the
copied render-record slots before `0x1f008` loads it into `0x783a2c`.

`0x1ee9e` initializes bitmap render state. It stores the active record
width word times four into `0x783a1c`, which is used later as a line
stride. It also stores buffer base `0x7810b4` into the render record,
derives a band/row value from `0x7810b8`, and fills a 16-word offset
table at `0x7839f8`.

The render entry `0x1ef6a` temporarily loads the current render record
from `0x783a18` into `A6`. It then:

- calls `0x1ef86` to compute `0x783a22`, `0x783a20`, and the current
  band destination base `0x783a28`;
- calls `0x1efc2` to index the bucket-head array at render-record
  `+0x18` by the current band/row word, walk the object chain, and
  dispatch object classes;
- calls `0x1f446`, a table-driven special-object dispatcher;
- calls `0x1f756`, which walks the render-record `+0x20` list and writes
  fixed-width/rule-like bitmap spans.

Render-band setup helper `0x1ef86` derives the destination state consumed by
every per-band object renderer. It divides
`(render word +0x10 + word +0x08 - word +0x0a)` by word `+0x06`, stores the
remainder in `0x783a22`, stores `(word +0x06 - remainder) << 4` in
`0x783a20`, and stores `long +0x00 + ((remainder << 6) * word +0x04)` in both
`0x783a28` and render-record long `+0x12`. Evidence anchor:
`0x1ef86 render-band setup computes destination rows and base`.

The render-entry route consumes render records with bucket objects selected
from render-record `+0x18`, selector-7 rule lists from `+0x1c`, and
fixed-width lists from `+0x20`. The firmware call order is `0x1ef86`,
`0x1efc2`, `0x1f446`, then `0x1f756`; that order is the per-band composition
rule for overlapping object classes.

Heterogeneous page evidence is now parser/page-record-backed. The addressed
compact/rule/raster route stores compact text, selector-7 rule, and mode-0
raster objects through `0x1387c` / `0x1381c` page-record storage, publishes the
page record, bridges it through `0x1ed84` / `0x1edc6`, and renders it through
`0x1ef6a`. The two-raster-row sibling preserves the bucket chain before the
same bridge. The crossing-rule route merges compact text, mode-0 raster, and a
patterned rule across bands `0` and `5`, carrying the mutated rule node into
the second band. Supporting fixture anchors:
`addressed text/rule/raster field groups reach publication and render entry`,
`addressed text/rule/multi-row raster publication preserves bucket chain`, and
`0x1ef6a page-band walk merges text raster and crossing rule`. The remaining
edge is therefore parser/page-record producer variants that change object
shapes, bridge fields, or ROM-derived row construction. It is not
parser-produced heterogeneous page objects, real-device row comparison, or the
modeled per-band merge itself.

Published-record routes for reset, FF, page-size, and orientation also pass
their `0xff1e` records through `0x1ed84` and the same `0x1ef6a` call order, so
those byte streams reach the compact bucket renderer through real page/control
records rather than hand-built render-record layers.

### Active Render Scheduler Semantic Checkpoint

See [active-render-scheduler.md](active-render-scheduler.md) and its
[Scheduler Outcome Matrix](active-render-scheduler.md#scheduler-outcome-matrix)
for the standalone published-record-to-band-render contract. This section
preserves the full low-level ledger and fixture list.

This checkpoint covers the scheduler handoff from a published page/control
pool record to active render work. It is the boundary after page-record
publication and before object-class bitmap dispatch: `0xff1e` has already
published a source record, and the scheduler chooses when that record becomes
`0x780eae` and which render work record becomes `0x783a18`.

Field groups:

- Canonical source-record state:
  - `0x780ea6`: protected page/control pool-head pointer written by
    `0xff1e` from source root longword `+0`.
  - `0x780eaa`: scheduler cursor for the record selected for rendering.
  - `0x780eae`: active source record consumed by `0x1ed84` and `0x1ee9e`.
  - source `+0x1c`, `+0x24`, `+0x28`, and `+0x2c..+0x68`: bucket array,
    rule list, fixed list, and context slots copied by `0x1edc6`.
- Canonical render work state:
  - `0x7820bc`: render work-record alternator between `0x7820c4` and
    `0x782128`.
  - `0x783a18`: active render work-record pointer used by `0x1ef6a`.
  - render work fields `+0`, `+4`, `+6`, `+8`, `+0a`, `+0c`, `+10`, and
    `+16`: source base, width, divisor, row deltas, cleanup bound,
    render-band cursor, and engine-side cursor.
  - render `+0x18`, `+0x1c`, `+0x20`, and `+0x24..+0x60`: bucket, rule,
    fixed, and context roots copied by `0x1edc6`.
- Derived/cache render state:
  - `0x780ea4`: active render/scheduler flag.
  - `0x780ea5`: active loop-control/done flag.
  - `0x783a1c`: render stride cache from render word `+4 << 2`.
  - `0x7839f8..`: 16-word offset table initialized by `0x1ee9e`.
  - `0x7839ae`, `0x7839ca`, `0x7839b2`, `0x7839b6`, `0x7839c2`,
    `0x7839be`, `0x7839ba`, and `0x7839c6`: aliases to active-pool render
    work fields written by `0x2126`.
  - `0x7839ce`, `0x78398e`, `0x783996`, `0x783998`, `0x7839a4`,
    `0x7839a8`, `0x7839a0`, `0x78399a`, and `0x783992`: row-copy and
    source-pointer caches used by `0x1a4c`, `0x2038`, `0x22f4`, and
    `0x2456`.
- Firmware bookkeeping:
  - `0x780e6e[]`: candidate pointer slots scanned by `0x7ec6..0x7f90`.
  - pool-record state byte `+4`: staged state `3`, selectable state `4`,
    selected state `2`.
  - `0x7821fb`: candidate-slot scan mask.
  - `0x780eb2`: release/advance cursor paired with `0x780eaa`.
  - `0x780eb6`: initialized-only pool alias. `0x3144..0x3162` stores pool
    base `0x780f02` to it, and
    `generated/analysis/ic30_ic13_long_reference_scan.md` finds no later
    ROM-local reader.
  - `0x780e04`: engine/status counter copied into released pool record
    word `+0x10`.
  - `0x7839d2`, `0x78398c`, `0x783990`, `0x78399e`, `0x78399f`,
    `0x7839ac`, `0x7828f9`, `0x780e32`, `0x780e36`, `0x7821f9.2`,
    `0x780e6d`, and `0x780e67`: active-pool copy/status and engine-shadow
    bookkeeping.
  - `0x78017f`, `0x780180`, and `0x780181`: timer/status trampoline
    dividers for the `$8000.6/7`, `$8000.5`, and `$a200`/`$a400` phases.
  - `0x783edc`, `0x783edd`, `0x780e35`, `0x780e69`, `0x782900`,
    `0x782914`, `0x78296c`, `0x7828fe`, `0x782904`, and `0x7828f6`:
    software-visible timer/status latches and output-table cursors written by
    `0x0d52..0x0f7a`.
  - manual-correlated formatter/DC timing signals: `BD`, `VDO`,
    `VSREQ`, `VSYNC`, `PRNT`, `CMND`, `CCLK`, `CBSY`, `STATS`,
    `PCLK`, `SBSY`, `RDY`, `PPRDY`, and `CPRDY` on connector `J205`.
    These are not yet mapped one-to-one to `$8000`, `$8a01`, `$a200`,
    `$a400`, `$a601`, `$a801`, `$aa01`, `0xfffe0001`, or
    `0xfffe0003`.
  - `0x2feb6` seeds `0x7820bc = 1` and `0x7820c0 = 1` at startup before
    the active render scheduler starts toggling those selectors. It also
    clears header words `0x7820c8` and `0x78212c` in the paired render
    work records.
  - wait-object records signaled by `0x1036` and selected by `0x123a`:
    next pointer `+0`, priority `+8`, scheduler state `+0a`, wait argument
    `+0c`, restart payload `+0x12`, private stack base `+0x16`, and saved
    stack pointer `+0x1a`.
- Parser scratch:
  - none. Parser/page-record producers have already built the published
    source record before this scheduler runs.
- Unknown:
  - physical engine timing behind trap veneers and MMIO/status helpers
    remains board-level work.
  - direct caller into optional pattern helper bodies `0x247c..0x2746` is not
    located. The helper's accumulator `0x7839d4`, pattern-pointer cache
    `0x7839d8..0x7839f7`, and destination writes to `0x78399a` are
    documented in [active-render-scheduler.md](active-render-scheduler.md).
    The caller boundary is exact: the long-reference scan lists
    `0x7839d4` refs at `0x001bf8`, `0x0026c6`, and `0x0026ea`, but no
    `0x0000247c` target, and the adjacent copy-pass listing returns at
    `0x2330` / `0x247a` before the separate `0x247c` body. A broad decoded
    disassembly search for `247c`, `26de`, and `270c` adds no branch, jump,
    trap/vector entry, or computed table into the helper; non-helper hits are
    opcode/data false positives. Ordinary active rendering still reaches
    copied rows through `0x22f4` and page bands through `0x1ef6a`.

Writers:

- `0xff1e` writes state byte `+4 = 2`, copies the source root longword to
  `0x780ea6`, sets publication flag `0x782996`, and clears the current root.
- `0x3144..0x3162` initializes `0x780ea6`, `0x780eaa`, `0x780eae`,
  `0x780eb2`, and `0x780eb6` to pool base `0x780f02`.
- `0x2feb6` initializes render-work selector state by writing
  `0x7820bc = 1` and `0x7820c0 = 1`, then clearing `0x7820c8` and
  `0x78212c`.
- `0x1c04..0x2016` stages a current pool record, writes deadline/status
  fields, inserts it into `0x780e6e[]`, and releases it to selectable state
  through `0x1eea`.
- `0x7ec6..0x7f90` promotes a selectable candidate into
  `0x780eaa`/`0x780eb2`.
- `0x7722..0x779a` advances or releases scheduler cursors while respecting
  protected head `0x780ea6`.
- `0x1eb32..0x1eb50` copies `0x780eaa` into active source `0x780eae`.
- `0x1ecd6..0x1ed76` alternates render work records, writes `0x783a18`,
  initializes geometry when needed, or reuses same-geometry fields before
  calling `0x1ed84`.
- `0x2126..0x218e`, `0x1a4c..0x1c00`, `0x2038..0x211c`,
  `0x22f4..0x2454`, and `0x2456..0x247a` prepare and consume the active-pool
  copy window.
- `0x0fa2..0x101e`, `0x1db0..0x1e40`, `0x1e44..0x1e7c`, and
  `0x1cf8..0x1ea8` update status/copy pacing and engine-shadow state.
- `0x1036..0x1282` and trap handlers `0x1144..0x11f8` update wait-object
  scheduler state.
- `0x0d52..0x0f7a` acknowledges the periodic status tick through
  `0xffff2000`, increments `0x780e04`, debounces `$8000.6`/`$8000.7` into
  `0x783edc`/`0x783edd` plus `0x78017e.2/3`, latches `$8a01.4` and
  `$8000.5` conditions into `0x78017e.0`, `0x780e35.0`, and `0x780e69`, rotates
  `$a200`/`$a400` output tables, and updates wait-object countdowns before the
  shared `0x1064` exit.
- `0x1eba4..0x1ecd2` advances active render bands, calls `0x1ef6a` when
  capacity is sufficient, throttles/yields when it is not, and performs
  cleanup when active work is done.

Readers and consumers:

- `0x1ed84` consumes `0x780eae`, source header words, and source
  bucket/list/context roots.
- `0x1ef6a` consumes `0x783a18` and the render work record, then dispatches
  bucket, rule, and fixed-list consumers.
- `0x1cf8..0x1ea8` consume `0x780e04`, `0x78399e`, `0xa680` readiness,
  attention flags, and active work fields to choose copy/status/wait
  variants.
- `0x1036`, `0x1064`, `0x108e`, `0x123a`, and trap handlers consume
  wait-object state to wake, block, yield, or dispatch scheduler objects.

Output effect:

- Fixture `0x1eb2a/0x1ecd6 selects published record for render entry` checks
  the addressed published page/control record being selected as source
  `0x00d0eaa0`, copied into `0x780eae`, assigned render work record
  `0x782128` through `0x783a18`, and rendered to the same rows as the direct
  `0x1ed84`/`0x1ef6a` fixture.
- Fixture `0x1ecd6 same-geometry render work reuse reaches render entry`
  checks the sibling branch reusing previous geometry, computing destination
  word `+8` via `0x33238`, and still reaches the same composed rows.
- Fixture `0x1eba4/0x1ef6a active render loop advances or yields bands`
  covers render-capacity, capacity-wait, cleanup, and throttle outcomes. In
  the render case it calls `0x1ef6a`, increments active word `+10`, and
  increments throttle word `+0e`.
- Fixture `0x1eba4 scheduler band words render published downloaded glyph`
  checks scheduler-produced band words `0..9` driving published downloaded-glyph
  buckets through the copied render record; only buckets `1` and `9` dispatch
  compact objects, and bucket `9` still produces visible row `86`.
- Service-manual evidence puts beam detect `BD`, formatter video `VDO`,
  vertical sync request/pulse, and print command `PRNT` at the physical
  formatter/DC boundary. It describes `BD` as horizontal sync for one
  scan line, says video transfer follows beam-detect synchronization,
  and defines the print period as beginning when the DC Controller
  receives formatter `VDO`. Current ROM evidence documents the
  software-visible consequences of those events; it does not yet map
  each physical signal to an MMIO bit.

Evidence status:

- Direct ROM evidence covers pool-head versus scheduler-cursor distinction,
  candidate-slot staging/release, `0x780eaa -> 0x780eae`, two-work-record alternation,
  `0x783a18`, same-geometry reuse, active-pool copy-window arithmetic, wait-object state
  transitions, active-loop branch predicates, and render-entry output. Direct ROM
  evidence covers `0x780eb6` as initialized-only bookkeeping because the reference scan
  finds only the pool-base initialization store.
- The remaining boundary is physical engine pacing because the firmware wait-state and
  MMIO side effects are modeled, but the board-level event timing is not named.

Fixture evidence:

- `0x1eb2a/0x1ecd6 selects published record for render entry`
- `0x1ecd6 same-geometry render work reuse reaches render entry`
- `0x3144/0x7ec6/0x7712 page pool aliases feed scheduler cursor`
- `0x1958/0x1c04/0x1eea staged candidate reaches render scheduler`
- `0x2126/0x1a4c/0x2038 active pool copy window feeds engine rows`
- `0x0fa2/0x1db0/0x1e44 status feedback drives copy and done flag`
- `0x1036/0x108e/0x123a wait-object scheduler handoff`
- `0x1144..0x11f8 scheduler trap handlers update wait objects`
- `0x1cf8/0x1e80/0x1ea8 wrapper dispatch selects engine variants`
- `0x1eba4/0x1ef6a active render loop advances or yields bands`
- `0x1eba4 scheduler band words render published downloaded glyph`

Disassembly evidence:

- `generated/disasm/ic30_ic13_active_pool_cycle_001958.lst`:
  `0x1958..0x1fa2`.
- `generated/disasm/ic30_ic13_scan_status_interrupt_000f84.lst`:
  `0x0f84..0x10f2`.
- `generated/disasm/ic30_ic13_timer_status_trampoline_000d52.lst`:
  `0x0d52..0x0f7a`.
- `generated/disasm/ic30_ic13_scheduler_trap_handlers_00110c.lst`:
  `0x110c..0x1282`.
- `generated/disasm/ic30_ic13_page_pool_candidate_insert_001c04.lst`:
  `0x1c04..0x2016`.
- `generated/disasm/ic30_ic13_active_pool_engine_gate_002038.lst`:
  `0x2038..0x223c`.
- `generated/disasm/ic30_ic13_engine_copy_pass_0022f4.lst`:
  `0x22f4..0x247a`.
- `generated/disasm/ic30_ic13_page_pool_init_003100.lst`:
  `0x3144..0x3162`.
- `generated/disasm/ic30_ic13_startup_render_work_init_02feb6.lst`:
  `0x2feb6..0x2fefc`.
- `generated/disasm/ic30_ic13_page_pool_candidate_select_007ec6.lst`:
  `0x7ece..0x7f90`.
- `generated/disasm/ic30_ic13_page_pool_cursor_007612.lst`:
  `0x7722..0x779a`.
- `generated/disasm/ic30_ic13_active_render_scheduler_01eb2a.lst`:
  `0x1eb2a..0x1ed84`.
- `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`:
  `0x1ed84..0x1ee9c`.
- `generated/disasm/ic30_ic13_bitmap_state_setup_01ee9e.lst`:
  `0x1ee9e..0x1ef38`.
- `generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`:
  `0x1ef6a..0x1effc`.
- [dc-controller-engine.md](dc-controller-engine.md): formatter/DC
  connector signals and beam-detect/video timing boundary from the
  service manual.

Unresolved middle edges:

- `0x0d52..0x0f7a`, `0x0f84..0x0fa0`, and `0x1020..0x102e`: the
  software-visible timer/status latches, output strobes, wait-object effects,
  and scheduler selection are modeled; mapping `$8000` bits, `$8a01`,
  `$a200`, `$a400`, `0xffff2000`, `$a601`, `$a801`, `$aa01`,
  `0xfffe0001`, and `0xfffe0003` to connector signals such as `BD`,
  `VDO`, `VSREQ`, `VSYNC`, `PRNT`, `CMND`, `CCLK`, `CBSY`, `STATS`,
  `PCLK`, `SBSY`, `RDY`, `PPRDY`, and `CPRDY` still needs
  board-level correlation.
- `0x10bc..0x11f8` and `0x123a..0x1282`: trap veneers, copied trap vectors,
  wait-state transitions, and scheduler selection are modeled; the remaining
  gap is their timing relation to physical engine/MMIO events.
- `0x1cf8..0x1ea8`: helper return predicates around `0xa668` and `0xa680`
  are modeled; the unresolved edge is external engine timing that makes
  `0x7828f9.6` ready or busy.

Board-timing boundary: the scheduler and renderer are covered as
ROM-visible state machines, not as physical signal timing. The timing-sensitive
paths `0x0f84..0x10f2`, `0x1036`, and `0x1cf8..0x1ea8` can change when
external status is observed, when wait objects are signaled, or when a
ready/busy predicate returns. The scheduler fixtures above check the
ROM-visible effects after those events occur: pending bytes
`0x78399e/0x78399f`, shadow byte `0x7828f9`, wait-object state, active source
`0x780eae`, work pointer `0x783a18`, and band words are the fields that
determine whether `0x1ef6a` renders, yields, throttles, or cleans up. Board
evidence is therefore not a blocker for byte-stream-to-bitmap documentation
unless the claim depends on a different sequence of those ROM-visible fields,
such as a dropped host byte, a timeout branch, a different ready/busy result,
or an engine handoff that changes which published record reaches the active
render path. The board-facing signal boundary is recorded in
[dc-controller-engine.md](dc-controller-engine.md).

The first confirmed bitmap-writing routines are in `0x1f4e0..0x1fa5a`.
They write 16-bit words to destinations derived from `0x783a28` or
`0x7810b4`, advance rows by stride `0x783a1c`, and use mask/expansion
tables around `0x2fefe..0x30b14`.

Key current anchors:

- `0x1f626`: computes destination pointer `A1` from object coordinates,
  `0x783a20`, `0x783a28`, `0x7839f8`, `0x783a1c`, and `0x7810b4`
- `0x1f4e0`: word/mask bitmap writer selected by table `0x1f4a0`
- `0x1f596`: solid-mask bitmap writer selected by table `0x1f4a0`
- `0x1f756` / `0x1f7b0`: fixed-width/rule-like list writer from
  render-record `+0x20`
- `0x1f812` / `0x1f862`: segment-list writer selected from
  bucket-chain objects
- `0x1f88e`: encoded-span writer selected from bucket-chain objects

### Pixel Writer And Buffer Map

The ROM renderers write into one of two software-visible destinations before
any physical engine handoff:

- Current band buffer:
  destination base `0x783a28`, line stride `0x783a1c`, and row-offset table
  `0x7839f8..` are derived by `0x1ee9e` / `0x1ef86`. Destination helpers
  `0x1f3d4` and `0x1f626` combine those fields with packed object
  coordinates. Subbyte phase is written to MMIO byte `0xa001`; nonzero phases
  are stored with bit `0x10` set.
- Fallback/continuation buffer:
  helpers restart continuation rows at `0x7810b4` plus the horizontal
  byte-pair offset decoded from the packed coordinate. Helper `0x1f3d4`
  leaves that offset in `D2`; helper `0x1f626` leaves it in `A2`. The split
  count comes from `0x1f414` or the matching split block inside `0x1f626`,
  which returns rows-in-current-band in the low word and
  remaining-after-band in the high word.

Destination helper disassembly contract:

- `0x1f3d4..0x1f412` decodes packed coordinate `D1`. The coordinate low byte
  becomes `byte_pair_offset = (D1 & 0xff) * 2`; that value is added to
  current-band pointer `A1` and preserved in `D2` for later fallback writes.
  Coordinate bits `12..15` become a row index into word table `0x7839f8..`;
  the selected table word is added to `0x783a28 + byte_pair_offset`.
  Coordinate bits `8..11` become the subbyte phase written to `$a001`, with
  bit `0x10` set when the phase is nonzero.
- `0x1f414..0x1f436` does not recompute the destination pointer. It uses the
  row index already packed into the high word of `D1`, clips requested row
  count `D3` against `0x783a20 - row_index`, and returns either unchanged
  `D3` or a split longword with fallback rows in the high word and
  current-band rows in the low word.
- `0x1f626..0x1f6ec` repeats the coordinate decode for rule/fixed-list style
  writers and moves the byte-pair offset into address register `A2`. It then
  converts incoming `D2` to a vertical row displacement with `lsl.w #4,D2`.
  If the displacement is zero, it behaves like the current-band case above.
  If the shifted displacement is still before `0x783a20`, it starts at
  `0x783a28 + 0x783a1c * D2_rows + row_offset[row_index] +
  byte_pair_offset` and clips `D3` against the remaining current-band rows.
  Otherwise it subtracts `0x783a20` from the shifted displacement and starts
  at `0x7810b4 + 0x783a1c * (row_index + adjusted_displacement) +
  byte_pair_offset`.

Writer families:

- Compact text and downloaded glyphs:
  `0x1effe` selects `0x1f034`, `0x1f0d2`, `0x1f1f0`, or `0x1f264`.
  Row-copy helpers under `0x1fa5c..0x207ac` and wide helper `0x2f27c` perform
  direct word/byte stores from decoded glyph rows into the selected current or
  fallback destination.
- Segment-list spans:
  `0x1f812 -> 0x1f862` writes full `0xffff` words plus a trailing mask from
  table `0x308f2` for each counted span row. It writes generated mask words;
  it does not read and blend the previous destination word.
- Rule and fixed-list objects:
  `0x1f446` dispatches selector `7` to solid helper `0x1f596` and non-solid
  selectors to pattern helper `0x1f4e0`; fixed-list helper `0x1f756` writes
  pattern words through `0x1f7b0` / `0x1f626`. Solid and segment writers
  write full words plus edge masks; patterned helpers mask the generated
  pattern word before storing it.
- Encoded raster:
  `0x1f88e` selects `0x1f8da`, `0x1f8e6`, `0x1f920`, or `0x1f9c6`.
  Mode `0` stores literal payload words; modes `1`, `2`, and `3` expand
  payload bytes through ROM tables `0x30914` or `0x30b14` before direct
  stores to current-band or fallback destinations.

Composition is therefore ordered overwrite within the ROM-defined call order:
bucket-chain objects first, then rule-list objects, then fixed-list objects.
No documented helper performs destination read-modify-write blending against
previous pixels. Physical video output starts after these software buffers are
rendered and is tracked as the formatter/DC boundary, not as a parser or
bitmap-helper requirement.

### Object Class Dispatch

The bucket-chain dispatcher at `0x1efc2` walks render-record `+0x18`,
which is the page/control bucket array copied from source offset
`+0x1c`. For each bucket object, it advances `A1` to object offset `+4`,
masks object byte `+4` with `0xc0`, and uses the result as the first
class split:

Within the selected bucket, the walk is head-to-tail through object `+0x00`
links. Producer order is therefore part of the pixel contract, not an
unspecified renderer policy: `0x1387c` reuses a matching compact/segment object
until its count reaches the producer-supplied capacity, otherwise it links a
new object at the bucket head; raster helper `0x13250` also links each new
encoded object at the bucket head. `0x1edc6` copies the page-root bucket array
to render `+0x18` without reordering, so `0x1efc2` sees the exact head order
created by those producers. Evidence:
`generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`,
`generated/disasm/ic30_ic13_raster_object_queue_013070.lst`,
`generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`, and
`generated/analysis/ic30_ic13_compact_bucket_allocator.md`.

- `0x00..0x3f`
  - Render path: compact branch `0x1effe`; table `0x1f024` selected by
    byte `+4` bits `0x10/0x20`
  - Current producer mapping: text/glyph bucket objects from `0x12f2e` /
    `0x1387c`
- `0x40..0x7f`
  - Render path: segment-list writer `0x1f812` / `0x1f862`
  - Current producer mapping: portrait text-span objects from pending
    state `0x783184..0x78318a` through `0x12714` -> `0x13520` /
    `0x135f0`, stored under the page-root `+0x1c` bucket array and
    copied to render-record `+0x18`
- `0x80..0xff`
  - Render path: encoded-span writer `0x1f88e`; table `0x1f8ca` selected
    by byte `+5 & 0x03`
  - Current producer mapping: raster rows from `0x13070` / `0x13250`,
    because `0x13250` initializes byte `+4` to `0x80`

Confirmed producer-to-renderer mappings:

- raster rows
  - Queue/list path: page-root `+0x1c` bucket array -> render-record
    `+0x18`
  - Selector fields: `0x13250` writes `object[4]=0x80`; `object[5]` is
    the low byte of the first `0x13250` argument sourced from
    raster-state word `+0x08`;
    `object[6]=capacity`; `object[8]=packed key`; payload starts at `+0x0a`
  - Renderer path: `0x1efc2` high-bit branch -> `0x1f88e` encoded-span
    renderer
- text/glyph buckets
  - Queue/list path: page-root `+0x1c` bucket array -> render-record
    `+0x18`
  - Selector fields: `0x1387c` writes the selector word at `object+4`;
    `0x12f2e`
    sets bits `0x1000`/`0x2000`, which become byte `+4` bits `0x10`/`0x20`;
    byte `+5` low nibble selects a render-record context slot copied from source
    `+0x2c` to render `+0x24`
  - Renderer path: `0x1efc2` compact branch -> `0x1effe` -> table
    `0x1f024`
- portrait text-span segment-list buckets
  - Queue/list path: pending span `0x783184..0x78318a` -> `0x12714`
    local source -> `0x13520` / `0x135f0` -> page-root `+0x1c`
    bucket array -> render-record `+0x18`
  - Selector fields: `0x137a2` derives selector word `0x4000` for the
    portrait span producer; `0x135f0` writes byte `+4 = 0x40`, word
    `+6` as the segment count, then six-byte entries containing the
    packed coordinate/key word, row count low nibble, skipped byte, and
    span width. Fixture `0x12714 portrait text span flush queues
    segment-list span` queues object prefix
    `00 00 00 00 40 00 00 01 32 00 03 00 00 10`.
  - Renderer path: `0x1efc2` segment-list branch -> `0x1f812` ->
    `0x1f862`
- rectangle/rule list
  - Queue/list path: page-root `+0x24` -> render-record `+0x1c`
  - Selector fields: `0x133aa` writes byte `+4` from `0x782a7d`, ORs
    source word
    `+8` into byte `+5`, and stores dimensions at `+8/+0x0a`; bridge `0x1edc6`
    copies word `+0x0a` to `+0x0c`
  - Renderer path: list renderer `0x1f446`; table `0x1f4a0` selected by
    `object[5] & 0x0f`
- second rule/text-span list
  - Queue/list path: page-root `+0x28` -> render-record `+0x20`
  - Selector fields: `0x136d2` writes byte `+4` from `0x782a7d`, byte
    `+5` from
    source `+1`, word `+6` from packed key, and word `+8`; bridge `0x1edc6`
    copies `+8` to `+0x0a` and sets `+0x0c=1`, `+0x0d=8`
  - Renderer path: fixed-width/rule writer `0x1f756` / `0x1f7b0`

The executable bucket-chain dispatcher coverage now pins `0x1efc2`
selected-bucket indexing from render-record word `+0x10` into the
`+0x18` bucket array, and verifies the compact, segment-list, and
encoded-span class branches plus compact/encoded subtable targets.

The rule-list disassembly contract is:

- `0x1f446` reads render-record rule-list root `+0x1c`. A zero root exits the
  rule pass.
- Like fixed-list rendering, it reads render word `+0x10`, divides by `5`, and
  runs only when the remainder is zero. Non-five-band render rows do not
  consume or mutate rule objects.
- For an active five-band row, it walks the linked rule list and filters each
  object by `object[4] <= render_band + 4`.
- Objects with continuation word `+0x0c <= 0` are ignored. Otherwise
  `object[4] - render_band` becomes row displacement `D2`, and
  `object[5] & 0x0f` indexes dispatch table `0x1f4a0`.
- Selector `7` dispatches to solid helper `0x1f596`. All other low-nibble
  selectors in the table dispatch to patterned helper `0x1f4e0`.
- Both helpers clear bridge flag bit `0x10` from object byte `+0x05`, derive
  a draw count from the bridged form or continuation form, subtract that count
  from continuation word `+0x0c`, and call destination helper `0x1f626`.
- Pattern helper `0x1f4e0` uses mask helper `0x1f6ee`, selector table
  `0x2fefe`, and row phase from the packed coordinate to write masked pattern
  words. Solid helper `0x1f596` writes full `0xffff` words plus a trailing
  mask from table `0x308be`.
- When helper `0x1f626` reports fallback rows in the high word of `D3`, both
  rule helpers restart at fallback buffer `0x7810b4 + A2` and continue the
  same row-store loop.

The exact rule-list instruction boundaries are:

- `0x1f446..0x1f44e`: load render-record rule-list root `+0x1c`; a zero root
  exits this render pass.
- `0x1f450..0x1f460`: load render band word `+0x10`, divide it by `5`, and
  exit unless the remainder is zero.
- `0x1f462..0x1f470`: set the inclusive band window to `band + 4`, load the
  current rule node, and stop the pass when node byte `+0x04` is beyond that
  window.
- `0x1f472..0x1f492`: skip nodes with continuation word `+0x0c <= 0`;
  otherwise compute row displacement from node byte `+0x04 - band`, select a
  helper from table `0x1f4a0` using node byte `+0x05 & 0x0f`, and call it.
- `0x1f494..0x1f49a`: advance through the node `+0x00` link and repeat until
  the list ends.
- `0x1f4e0..0x1f514`: patterned-rule setup. It seeds draw count `0x50`, reads
  packed coordinate word `+0x06`, clears bridge bit `0x10`, derives or
  normalizes the draw count, mutates continuation word `+0x0c`, clips the
  current draw count, and calls destination helper `0x1f626`.
- `0x1f51a..0x1f55a`: read width word `+0x08`, call mask helper `0x1f6ee`,
  clear `$a001`, load stride `0x783a1c`, select pattern source from table
  `0x2fefe`, and prepare leading/full/trailing masks.
- `0x1f55c..0x1f57a`: for each current-band row, read the next pattern word,
  write its leading masked word, write any full middle words, write the
  trailing masked word, then advance by stride.
- `0x1f57e..0x1f590`: if helper `0x1f626` split rows into the fallback half of
  `D3`, restart the same patterned row loop at `0x7810b4 + A2`.
- `0x1f596..0x1f5ca`: solid-rule setup. It mirrors the bridge-bit,
  draw-count, continuation-word, clipping, and destination-helper sequence
  used by `0x1f4e0`.
- `0x1f5d0..0x1f5f6`: derive full-word count from width word `+0x08`, map the
  low-nibble tail through mask table `0x308be`, load full-word pattern
  `0xffff`, load stride `0x783a1c`, and enter the current-band loop.
- `0x1f5f8..0x1f60a`: for each current-band row, write zero or more full
  `0xffff` words, write the trailing mask word, then advance by stride.
- `0x1f60e..0x1f620`: if helper `0x1f626` split rows into the fallback half of
  `D3`, restart the same solid row loop at `0x7810b4 + A2`.

The segment-list disassembly contract is:

- `0x1f812` receives `A1` at object byte `+4` for bucket class `0x40..0x7f`,
  copies it to `A4`, skips to object word `+0x06`, reads that word as an entry
  count, and loops over six-byte entries.
- Each entry supplies packed coordinate word `D1`, a row-count/phase byte
  loaded into `D2`, one skipped byte, and span-width word `D3`.
- Helper `0x1f836` saves the outer entry counter, calls `0x1f3d4` to compute
  the current-band destination, restores the row-count byte into `D2`, maps
  the span-width low nibble through ROM table `0x308f2`, and stores the result
  in the high word of `D3`.
- Writer `0x1f862` loads stride `0x783a1c`, seeds full-word pattern `0xffff`,
  and writes each row as zero or more full `0xffff` words followed by the
  trailing mask from `D3`. It advances to the next destination row by the
  stride and does not read the prior destination word.

The exact segment-list instruction boundaries are:

- `0x1f812..0x1f81e`: copy the bucket object pointer to `A4`, advance past
  object bytes `+0x04/+0x05`, read object word `+0x06` as entry count, and
  exit when the decremented count is negative.
- `0x1f820..0x1f82c`: consume one six-byte segment entry: coordinate word
  into `D1`, row-count/phase byte into `D2`, one skipped byte, and span-width
  word into `D3`; then call helper `0x1f836` and writer `0x1f862`.
- `0x1f836..0x1f840`: preserve the outer object-entry counter in `D4`, move
  the row-count/phase byte through `D4`, and call destination helper
  `0x1f3d4`.
- `0x1f840..0x1f85c`: restore the row-count/phase byte into `D2`, derive the
  number of rows from its low nibble, split the span-width word into full-word
  count and low-nibble tail, and map that tail through mask table `0x308f2`
  into the high word of `D3`.
- `0x1f862..0x1f872`: load stride `0x783a1c`, seed destination base in `D7`,
  and set full-word fill pattern `0xffff`.
- `0x1f874..0x1f884`: for each output row, write `D3` low-word count full
  `0xffff` words, then write the trailing-mask high word of `D3`.
- `0x1f886..0x1f88c`: decrement the row counter, advance the destination base
  by stride, and loop until all segment rows are written.

The fixed-width list disassembly contract is:

- `0x1f756` reads render-record list `+0x20`. If it is zero, the fixed-list
  pass is skipped.
- It reads render word `+0x10`, divides by `5`, and runs only when the
  remainder is zero. Non-five-band render rows do not consume or mutate
  fixed-list objects.
- For an active five-band row, it walks the linked list and filters each object
  by `object[4] <= render_band + 4`. Objects after that window are skipped for
  this pass.
- Objects with word `+0x0a <= 0` are ignored. Otherwise `object[4] -
  render_band` becomes row displacement `D2`, `object[5] & 0x0f` indexes the
  pattern table at `0x308de`, and the selected longword is passed to
  `0x1f7b0`.
- `0x1f7b0` copies the selected pattern longword to `D4`, reads packed
  coordinate word `+0x06`, clears bridge flag bit `0x10` in object byte
  `+0x05`, and computes the draw count from either the initial bridge form or
  the already-normalized continuation form.
- It subtracts the draw count from remaining-row word `+0x0a`, clips the
  current draw count if the subtraction reaches or crosses zero, and calls
  destination helper `0x1f626`.
- It writes the low pattern word to the current-band destination once per row,
  advancing by stride `0x783a1c`. If the split count has fallback rows, it
  restarts at `0x7810b4 + A2` and continues the same stores.

The exact fixed-list instruction boundaries are:

- `0x1f756..0x1f75e`: load render-record fixed-list root `+0x20`; a zero root
  exits this render pass.
- `0x1f760..0x1f770`: load render band word `+0x10`, divide it by `5`, and
  exit unless the remainder is zero. Fixed-list objects are therefore consumed
  only on five-band boundaries.
- `0x1f772..0x1f780`: set the inclusive band window to `band + 4`, load the
  current fixed-list node, and stop the pass when node byte `+0x04` is beyond
  that window.
- `0x1f782..0x1f7a4`: skip nodes with remaining word `+0x0a <= 0`; otherwise
  compute row displacement from node byte `+0x04 - band`, select the pattern
  longword from table `0x308de` using node byte `+0x05 & 0x0f`, and call
  `0x1f7b0`.
- `0x1f7a4..0x1f7aa`: advance through the node `+0x00` link and repeat until
  the list ends.
- `0x1f7b4..0x1f7dc`: fixed writer setup. It copies the selected pattern
  longword into `D4`, reads packed coordinate word `+0x06`, clears bridge flag
  bit `0x10` in node byte `+0x05`, and derives the current draw count from
  either the initial bridged form or the already-normalized continuation form.
- `0x1f7dc..0x1f7e6`: subtract the draw count from remaining-row word `+0x0a`
  and clip the current draw count when the subtraction crosses zero.
- `0x1f7e6..0x1f7fc`: call destination helper `0x1f626`, then write the low
  pattern word to the current-band destination once per row, stepping by
  stride `0x783a1c`.
- `0x1f7fc..0x1f80c`: if helper `0x1f626` split rows into the fallback half of
  `D3`, restart the same pattern stores at fallback buffer `0x7810b4 + A2`.

The controlling evidence is
`generated/disasm/ic30_ic13_bitmap_draw_core_01f3d4.lst` at
`0x1f446..0x1f620` for rule-list rendering, `0x1f756..0x1f810` for fixed-list
rendering, and `0x1f812..0x1f88c` for segment-list rendering. Fixtures named
`0x1f446/0x1f596 renders solid black rectangle rule pixels`, `0x1f4e0 renders
gray and HP pattern selector matrix`, `0x1f812 segment-list object renders
counted mask spans`, `0x1f756 fixed-width list renders bridged +0x20 object`,
and `0x1ef6a render entry composes bucket, rule, and fixed-width lists in call
order` are branch and transcription checks for this static contract.

The pixel-composition operation at this shared layer is order-dependent direct
writing, not an implicit OR/XOR/AND blend with the previous destination word.
The helpers compute a destination pointer with `0x1f3d4` or `0x1f626`, then
store generated words, bytes, or longwords to that address. Compact row-copy
helpers and encoded-raster modes use direct `move` stores. Segment-list and
solid-rule helpers write full words plus trailing mask words. Patterned-rule
helper `0x1f4e0` applies masks to the generated pattern word before storing
the result; it does not first read the previous destination word and combine
with it. Overlaps therefore resolve by the render order below: bucket-chain
objects, then rule-list objects, then fixed-list objects.

### Bitmap Object Dispatch Semantic Checkpoint

This checkpoint covers the first complete shared render-dispatch layer after
`0x1ef6a` has selected an active render record. It composes the bucket-chain,
rule-list, and fixed-list consumers that turn copied page-record objects into
bitmap writes: `0x1efc2`, `0x1effe`, `0x1f034`, `0x1f0d2`, `0x1f1f0`,
`0x1f264`, `0x1f446`, `0x1f4e0`, `0x1f596`, `0x1f756`, `0x1f812`, and
`0x1f88e`.

Field groups:

- Canonical render-record roots:
  - render `+0x18`: bucket-head array copied from page/control source
    `+0x1c` by `0x1edc6`; consumed by `0x1efc2`.
  - render `+0x1c`: rule-list root copied from source `+0x24`; consumed by
    `0x1f446`.
  - render `+0x20`: fixed-list root copied from source `+0x28`; consumed by
    `0x1f756`.
  - render `+0x24..+0x60`: selected context/resource longwords copied from
    source `+0x2c..+0x68`; compact text uses object byte `+5` low nibble to
    select one slot before `0x1f008` writes `0x783a2c`.
- Canonical bucket object fields:
  - object `+0x00`: next pointer in the selected bucket chain.
  - object byte `+0x04`: class selector. `0x00..0x3f` enters compact glyph
    dispatch, `0x40..0x7f` enters segment-list dispatch, and `0x80..0xff`
    enters encoded raster dispatch.
  - object byte `+0x05`: compact context selector or encoded raster mode.
    Raster mode bits `+5 & 0x03` select `0x1f8da`, `0x1f8e6`, `0x1f920`, or
    `0x1f9c6`.
  - object word `+0x06`: compact entry count/capacity or segment-list entry
    count, depending on class.
  - object word `+0x08`: packed coordinate/key consumed by destination
    helpers.
  - object `+0x0a..`: compact glyph entries, segment-list entries, or encoded
    raster payload bytes.
- Canonical rule/fixed-list fields:
  - rule object `+0x05`: bridged fill selector with flag bit `0x10` set by
    `0x1edc6`; low nibble selects solid helper `0x1f596` for selector `7` or
    pattern helper `0x1f4e0` through table `0x1f4a0`.
  - rule object `+0x06`, `+0x08`, `+0x0a`, and `+0x0c`: packed key, width,
    original height, and continuation height consumed by `0x1f446`.
  - fixed-list object `+0x04`, `+0x05`, `+0x06`, `+0x08`, `+0x0a`,
    `+0x0c`, and `+0x0d`: band byte, selector/pattern byte, packed key,
    width, remaining rows, bridge count, and bridge width marker consumed by
    `0x1f756` / `0x1f7b0`.
- Derived/cache render state:
  - `0x783a18`: active render-record pointer loaded by `0x1ef6a`.
  - `0x783a20`, `0x783a22`, and `0x783a28`: current-band split count,
    remainder, and destination base written by `0x1ef86`.
  - `0x783a1c`: line stride written by `0x1ee9e`.
  - `0x7839f8..`: 16-word offset table written by `0x1ee9e` and consumed by
    destination helpers.
  - `0x783a2c`: compact glyph context/resource cache written by `0x1f008`.
  - `0x7810b4 + byte_pair_offset`: fallback buffer position used by compact
    glyph and encoded raster helpers when current-band clipping carries rows
    beyond the active band. `0x1f3d4` preserves the byte-pair offset in `D2`;
    `0x1f626` preserves it in `A2`.
- Parser scratch:
  - none in the shared dispatch layer. Parser-family scratch has already been
    converted into page-record objects by `0x12f2e`, `0x13070`, `0x133aa`,
    `0x13520`, `0x135f0`, or `0x136d2`.
- Firmware bookkeeping:
  - `0x783a46`: horizontal phase used by the compact row-copy chunk helper
    `0x2f27c`.
  - object continuation fields such as rule `+0x0c` and fixed-list `+0x0a`
    are mutated by render helpers so later bands can resume the same object.
- Unknown:
  - exact physical engine consumption of the already-rendered band buffer
    remains outside this checkpoint. The active scheduler checkpoint covers
    the engine-facing copy/status wrappers, but not board-level timing.

Writers:

- `0x1edc6` copies source roots into render roots, normalizes rule-list and
  fixed-list fields, and copies context slots.
- `0x1ef86` writes current-band destination caches before any object class
  dispatch runs.
- `0x12f2e` / `0x1387c` write compact bucket objects for text and glyphs.
- `0x12714` / `0x13520` / `0x135f0` write `0x40..0x7f` segment-list bucket
  objects for flushed text spans.
- `0x13070` / `0x13250` write `0x80..0xff` encoded raster bucket objects.
- `0x13386` / `0x133aa` write rule-list objects under page-root `+0x24`.
- `0x136d2` writes fixed-list objects under page-root `+0x28`.
- `0x1f446`, `0x1f4e0`, `0x1f596`, `0x1f756`, `0x1f812`, and compact
  helpers mutate continuation/count fields while rendering rows.

Readers and consumers:

- `0x1ef6a` reads `0x783a18` and calls consumers in order: `0x1ef86`,
  `0x1efc2`, `0x1f446`, and `0x1f756`.
- `0x1efc2` reads render `+0x18`, indexes the active bucket from render word
  `+0x10`, walks each bucket object, and dispatches by object byte
  `+0x04 & 0xc0`.
- `0x1effe` handles compact class objects and selects `0x1f034`, `0x1f0d2`,
  `0x1f1f0`, or `0x1f264` from byte `+0x04` bits `0x10` and `0x20`.
- `0x1f812` consumes segment-list objects. Each six-byte entry supplies a
  coordinate word, row-count nibble, skipped byte, and width/mask word before
  `0x1f862` writes full words plus a trailing mask from table `0x308f2`.
- `0x1f88e` consumes encoded raster objects. Byte `+0x05 & 0x03` selects
  literal mode `0`, doubled-row mode `1`, tripled-row mode `2`, or four-row
  mode `3`.
- `0x1f446` consumes rule-list objects from render `+0x1c` and dispatches
  selector `7` to `0x1f596`; selectors `0..6` and `8..13` go to `0x1f4e0`.
- `0x1f756` consumes fixed-list objects from render `+0x20` on five-band
  boundaries and writes pattern words through `0x1f7b0` / `0x1f626`.

Output effect:

- The layer merge uses direct destination stores. Compact glyph, encoded
  raster, segment-list, rule, and fixed-list helpers write generated source
  words into the active band or fallback buffer in the call order above; no
  documented helper performs a destination read-modify-write blend with earlier
  pixels.
- Shared call-order evidence uses bucket, rule, and fixed-list roots copied by
  `0x1edc6`, then consumed by `0x1ef6a` in order. Supporting fixture anchor:
  `0x1ef6a render entry composes bucket, rule, and fixed-width lists in call
  order`.
- Band-crossing evidence uses compact text, mode-0 raster, and a patterned rule
  across bands `0` and `5`; the rule continuation field carries state between
  band calls. Supporting fixture anchor:
  `0x1ef6a page-band walk merges text raster and crossing rule`.
- Parser-shaped mixed-object evidence uses bridged bucket, rule, and
  encoded-raster objects after `0x1edc6`. Supporting fixture anchor:
  `bridged text, rule, and raster layers compose into one page band`.
- Parser-driven downloaded-glyph composition routes host-fetched bytes through
  handlers `0x10e68`, `0x10e22`, `0x10898`, `0xd04a`, `0x10808`, `0x1075a`,
  and `0x11f82`, queues bucket/rule objects, then renders through the dispatch
  layer. Supporting fixture anchor:
  `parser-driven downloaded glyph rule raster stream composes through 0x1ef6a`.
- Segment-list output uses `0x1f812` and writes counted rows with full-word and
  trailing-mask behavior. Supporting fixture anchor:
  `0x1f812 segment-list object renders counted mask spans`.
- Fixed-list output uses the bridged `+0x20` list and decrements the
  remaining-row field. Supporting fixture anchor:
  `0x1f756 fixed-width list renders bridged +0x20 object`.
- Fixtures `0x1f446/0x1f596 renders solid black rectangle rule pixels` and
  `0x1f4e0 renders gray and HP pattern selector matrix` cover solid and
  patterned rule selectors.
- Fixtures `0x1f88e mode-0 raster object renders queued literal row`,
  `0x1f88e mode-1 raster object expands queued bytes into two rows`,
  `0x1f88e mode-2 raster object expands queued byte pair into three rows`, and
  `0x1f88e mode-3 raster object expands queued bytes into four rows` cover the
  encoded-raster expansion modes.
- Fixtures `0x1f034 compact text splits current band and fallback rows`,
  `0x1f0d2 renders wide inline compact payload row`,
  `0x1f1f0 renders segmented inline compact payload row`, and
  `0x1f264 renders segmented wide inline compact payload row` cover the four
  compact glyph subrenderers.

Evidence status:

- Render-root ownership, `0x1ef6a` call order, bucket class split, compact
  subdispatch, segment-list layout, encoded raster mode split, rule-list
  selector dispatch, fixed-list consumption, and row-level output are grounded
  in the cited fixtures and ROM paths.
- Parser-produced raster and rule objects are grounded in command-family
  checkpoints that trace handlers to page-record objects and then to
  ROM-derived row construction.
- The documented compact downloaded-glyph producer families are grounded in
  the downloaded-font matrices that carry normal, wide, segmented,
  segmented-wide, row-count, width-byte, row-byte, high-row, no-install,
  status-2, and FF-publication streams through parser install, page-record
  publication, `0x1ed84` / `0x1ef6a` dispatch, and documented row output where
  the helper target is valid. Remaining selected-font combinations are broader
  ROM-local coverage work, not a reduced-evidence statement about the
  documented producer contracts.
- Hardware-facing timing is a bounded external edge because the bitmap bands
  are ROM-derived before the engine-facing copy path. That timing is outside
  the pixel model unless it changes ROM-visible scheduler, wait-object, or
  publication state.

Fixture evidence:

- `0x1ef86 render band setup computes remainder and destination base`
- `0x1efc2 bucket-chain dispatcher selects bucket and object classes`
- `0x1ef6a render entry composes bucket, rule, and fixed-width lists in call
  order`
- `0x1ef6a page-band walk merges text raster and crossing rule`
- `bridged compact text and rule objects compose into one page band`
- `bridged text, rule, and raster layers compose into one page band`
- `parser-driven downloaded glyph rule raster stream composes through
  0x1ef6a`
- `0x1f812 segment-list object renders counted mask spans`
- `0x1f756 fixed-width list renders bridged +0x20 object`
- `0x1f446/0x1f596 renders solid black rectangle rule pixels`
- `0x1f4e0 renders gray and HP pattern selector matrix`
- `0x1f88e mode-0 raster object renders queued literal row`
- `0x1f88e mode-1 raster object expands queued bytes into two rows`
- `0x1f88e mode-2 raster object expands queued byte pair into three rows`
- `0x1f88e mode-2 raster object clips current-band rows and continues in
  fallback buffer`
- `0x1f88e mode-3 raster object expands queued bytes into four rows`
- `0x1f034 compact text splits current band and fallback rows`
- `0x1f0d2 renders wide inline compact payload row`
- `0x1f1f0 renders segmented inline compact payload row`
- `0x1f264 renders segmented wide inline compact payload row`

#### Compact Render Dispatch Outcome Matrix

This matrix owns the compact-class render branch after page publication and
bridge. It is the render-side counterpart to the compact selector producer
matrix in [downloaded-fonts.md](downloaded-fonts.md#compact-selector-outcome-matrix)
and the printable source-capture checkpoint in
[font-context-metrics.md](font-context-metrics.md#printable-source-capture-checkpoint).

Compact entry dispatch:

- ROM path:
  `0x1efc2 -> 0x1effe`.
- State category:
  canonical render-record object state and derived context cache.
- Writers:
  `0x1edc6` copies page-root compact bucket heads to render root `+0x18` and
  context slots to render `+0x24..+0x60`; `0x1ef86` has already written
  band-local destination caches.
- Readers / consumers:
  `0x1efc2` selects the bucket from render root `+0x18` using render word
  `+0x10`, walks each object, and routes class byte `+0x04 & 0xc0 == 0` to
  `0x1effe`. `0x1effe` reads selector byte `+0x04`, context-slot byte `+0x05`,
  loads the selected render context into `0x783a2c`, and dispatches through
  table `0x1f024`.
- Output effect:
  no pixels yet; this selects the glyph helper family and active context used
  by the row-copy layer.
- Evidence:
  `generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`
  `0x1efc2..0x1f024`; fixture
  `0x1efc2 bucket-chain dispatcher selects bucket and object classes`.

Short compact selector:

- ROM path:
  `0x1f024 -> 0x1f034`.
- State category:
  canonical compact object state and derived row-copy state.
- Writers:
  `0x12f2e` writes selector class `0x0000 | context_slot` and compact entries
  containing glyph byte, packed coordinate bytes, and count word `+0x06`.
- Readers / consumers:
  `0x1f034` reads the entry count, resolves each glyph through `0x1f354`,
  decodes the packed coordinate through `0x1f3d4`, splits rows through
  `0x1f414`, and indexes main helper table `0x1f08e` by span byte count.
- Output effect:
  renders built-in short text and downloaded glyphs whose span index reaches a
  valid row-copy helper.
- Evidence:
  `generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst`
  `0x1f034..0x1f08c`; fixtures
  `0x1f034 compact text splits current band and fallback rows` and
  `host-fetched linear downloaded character stream renders through 0x168dc`.

Wide compact selector:

- ROM path:
  `0x1f024 -> 0x1f0d2`.
- State category:
  canonical compact object state and derived wide-row caches.
- Writers:
  `0x12f2e` writes selector bit `0x1000` when the printable source exposes a
  wide span; `0x1f0d2` writes caches `0x783a40`, `0x783a42`, `0x783a44`,
  `0x783a46`, and `0x783a48`.
- Readers / consumers:
  `0x1f0d2` resolves each glyph through `0x1f354`, renders full 16-byte chunks
  through `0x2f27c`, and dispatches any trailing remainder through table
  `0x1f1ac`.
- Output effect:
  renders valid wide glyph rows from the installed bitmap source; no-remainder
  spans use only full chunk copies.
- Evidence:
  `generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst`
  `0x1f0d2..0x1f1aa`; fixtures
  `host-fetched even-span wide downloaded character renders through 0x1f0d2`
  and `downloaded glyph wide-remainder matrix publishes and renders compact
  chunks`.

Segmented compact selector:

- ROM path:
  `0x1f024 -> 0x1f1f0`.
- State category:
  canonical compact object state and derived segment-plane state.
- Writers:
  `0x12f2e` writes selector bit `0x2000` and four-byte segment entries
  containing glyph byte, segment byte, and packed coordinate word.
- Readers / consumers:
  `0x1f1f0` resolves the glyph through `0x1f354`, applies the segment byte as
  a `0x80`-row plane offset, clamps the segment row count to at most `0x80`,
  adjusts A2/A3 source planes, and selects `0x1f08e` row-copy helpers.
- Output effect:
  renders the selected segment of tall glyphs, including odd-span split-plane
  layouts.
- Evidence:
  `generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst`
  `0x1f1f0..0x1f262`; fixture
  `host-fetched split-plane segmented downloaded character renders through
  0x1f1f0`.

Segmented-wide compact selector:

- ROM path:
  `0x1f024 -> 0x1f264`.
- State category:
  canonical compact object state and derived segment/wide caches.
- Writers:
  `0x12f2e` writes selector bits `0x3000` and segmented-wide entries;
  `0x1f264` writes the same wide caches as `0x1f0d2` after applying segment
  source offsets.
- Readers / consumers:
  `0x1f264` applies the segment byte, resolves current-band/fallback split
  through `0x1f414`, renders full 16-byte chunks through `0x2f27c`, and uses
  `0x1f1ac` for any remainder.
- Output effect:
  renders selected wide segments when source rows and bitmap payload are
  inside the installed glyph boundaries.
- Evidence:
  `generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst`
  `0x1f264..0x1f352`; fixtures
  `0x16498-backed downloaded character object renders segmented-wide compact
  row` and `downloaded glyph segmented-wide matrix publishes and renders
  compact chunks`.

Context and glyph resolver:

- ROM path:
  `0x1f354`.
- State category:
  canonical font/resource state and derived glyph source pointers.
- Writers:
  none in this checkpoint; `0x1effe` has already loaded `0x783a2c`.
- Readers / consumers:
  bit-30-set contexts use the selected resource offset table and glyph
  metadata bytes/words `+4/+5/+6/+8`; bit-30-clear contexts use fixed
  eight-byte entries at `context + 0x40 + 8 * glyph_index`.
- Output effect:
  returns A2, optional A3, span byte count, and row count used by the helper
  selected above.
- Evidence:
  `generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst`
  `0x1f354..0x1f3d2`; generated analysis
  `generated/analysis/ic30_ic13_text_glyph_index_flow.md`.

Field grouping for this matrix:

- Canonical state:
  render bucket root `+0x18`, render context slots `+0x24..+0x60`, compact
  object bytes `+0x04/+0x05`, count word `+0x06`, compact payload entries,
  selected context longword, glyph table entries, fixed glyph records, and
  bitmap payload bytes.
- Derived/cache state:
  active context cache `0x783a2c`, destination caches from `0x1ef86`, split
  result from `0x1f414`, wide caches `0x783a40..0x783a48`, A2/A3 source
  planes, and row-copy table targets.
- Parser scratch:
  none. Host byte and downloaded payload parser scratch has already become
  current-font state, installed glyph records, and compact page objects.
- Firmware bookkeeping:
  bucket-chain links, entry counters, segment loop counters, and computed-jump
  table targets.
- Hardware/external state:
  none inside this matrix. Physical engine consumption occurs after ROM row
  buffers are written.
- Unknown:
  valid compact selector outcomes above are documented. The remaining
  ROM-local boundaries are invalid computed targets when wrapped low-byte
  selectors index outside decoded helper heads, and high-row fallback counts
  index past valid row-count tables.

Unresolved middle edges:

- `0x1f034 -> 0x1f08e` wrapped-width invalid targets are exact ROM-local
  computed-jump boundaries, such as span `0x0102` selecting target
  `0x0066cc` from table bytes at `0x1f496`.
- `0x1fe76 -> 0x1fe8a` high-row short fallback targets are exact ROM-local
  row-count table boundaries; row `0x0102` fallback index `200` reads target
  `0x329ad3c0`.
- New work in this cluster should start only from object fields that change
  selector byte `+0x04`, context slot byte `+0x05`, glyph index, row/span
  metadata, segment byte, current-band split, or row-copy table index.

Disassembly evidence:

- `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`:
  `0x1ed84..0x1ee9c`.
- `generated/disasm/ic30_ic13_bitmap_state_setup_01ee9e.lst`:
  `0x1ee9e..0x1ef38`.
- `generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`:
  `0x1ef6a..0x1effc`.
- `generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst`:
  compact dispatch and renderers `0x1effe..0x1f3d2`.
- `generated/disasm/ic30_ic13_bitmap_draw_core_01f3d4.lst`:
  destination, rule, segment-list, and fixed-list helpers.
- `generated/disasm/ic30_ic13_bitmap_encoded_span_modes_01f88e.lst`:
  encoded raster mode helpers.
- `generated/disasm/ic30_ic13_bitmap_row_copy_tables_01fa5c.lst`:
  compact glyph row-copy helper tables.

Unresolved middle edges:

- `0x12f2e..0x1f264`: compact built-in and downloaded glyph objects are
  composed for the documented selector classes: short `0x0003`, wide
  `0x1003`, segmented `0x2003`, and segmented-wide `0x3003`, including
  current-band/fallback splitting and the downloaded width/row matrices.
  Remaining compact-glyph work starts only from selected-font combinations or
  wrapped-width streams that change source object bytes, selector class,
  helper dispatch, fallback split, or row-construction inputs.
- `0x12714..0x1f812` / `0x1f756`: pending text-span output is connected for
  both orientation branches. Portrait state `0x783184..0x78318a` is packaged
  by `0x12714`, inserted through `0x13520` / `0x1354a` / `0x135f0` as
  class-`0x40` segment-list objects under page-root `+0x1c`, bridged to
  render-record `+0x18`, and consumed by `0x1f812`. Landscape state is
  transformed by the same `0x12714` source package, inserted through
  `0x136d2` as fixed-list objects under page-root `+0x28`, bridged to
  render-record `+0x20`, and consumed by `0x1f756` / `0x1f7b0`. The
  allocation-failure retry edge is explicit at `0x127ae..0x12808`: set bit 0
  in the page-root flags word at `+0x14` (written at byte `+0x15.0`),
  publish through `0xff1e`, rebuild the local source, and retry `0x13520`.
  Remaining work starts only from byte streams or selected metric/orientation
  states that change the `0x12790..0x127a0` page-extent gate,
  segment-list/fixed-list object fields, bridge roots, or render dispatch.
- `0x13070..0x1f88e`: raster mode producers and encoded renderers are
  connected for modes `0..3`; dense split object-chain rules are documented for
  capped-new-chunk and current-tail allocation. Remaining work must change a
  concrete raster boundary: accepted count or drain result at `0x105d0`,
  encoded object fields `+0x04/+0x05/+0x06/+0x08/+0x0a..`, split allocator
  state `0x782a70/0x782a72/0x782a76/0x782a80`, bridge bucket roots,
  copy-stop byte `0x782996`, packed-key advance, or mode-specific `0x1f88e`
  rows.
- `0x13386..0x1f4e0` and `0x136d2..0x1f756`: rule and fixed-list output is
  pinned for the selector fixtures above. Remaining work must change a
  concrete ROM-visible field or branch: clipped source record `0x782a88`,
  rule object `+0x05/+0x06/+0x08/+0x0a/+0x0c`, fixed-list object
  `+0x04/+0x05/+0x06/+0x08/+0x0a/+0x0c/+0x0d`, bridge-normalized
  rule/fixed roots, selector dispatch between `0x1f596` and `0x1f4e0`,
  fixed-list band gating in `0x1f756`, continuation mutation, or rendered
  rows.
- `0x1fa5c..0x207ac`: compact row-copy table targets are composed in the
  compact glyph row-copy checkpoint below. The downloaded row-count family now
  renders parser-produced rows `0x0001..0x00ff`; segmented-wide high-row
  below-cap cases are documented as cross-products of preserved installed row
  words, low-byte selector truncation, span-selected helper choice, and the
  parser payload-count cap. The exact ROM-local visible-output boundary is
  the unchecked `0x1fe76` row-count table read above valid index `128`, where
  `0x1fe8a + 4 * D3` enters row-copy code bytes beginning at `0x2008e`.
  Remaining row-copy work is new streams that change helper dispatch or rows.

### Subrenderer Payloads

The compact text/glyph branch resolves a font/glyph context through
`0x783a2c`. That value is loaded from a render-record context slot
copied from page-root `+0x2c`; the slot points at a current-font context
record whose first longword is the selected resource address plus flag
bits. Helper `0x1f354` tests bit 30 of that context longword to
distinguish two resource layouts:

- bit 30 set: context base plus word `+8` points to an offset table; the
  glyph index selects a long offset into a glyph entry;
- bit 30 clear: context base plus `0x40 + 8*glyph_index` is an inline
  glyph record with a long bitmap offset.

Both forms return a glyph bitmap pointer in `A2`, a byte/word span count
in `D1`, a row/count field in `D3`, and sometimes a secondary plane/row
pointer in `A3`.

The active character maps are rebuilt during font activation. Built-in
contexts use `0x14d9c` to create a base range map from selected font
record words `+0x0e` / `+0x10`, then `0x14f16` applies
symbol-set-specific remaps. Inline/downloaded contexts use `0x14e24` and
`0x14eb6` to populate the same map shape from valid fixed glyph records.
Fixture `parsed primary built-in font selection feeds visible page-record rows`
now ties parsed primary selection bytes `ESC (s0p10h12v0s0b3T` to visible
compact rows: `0x13eb8` selects context `0xc008004c`, `0x14c64` rebuilds map
`0x782f32`, following printable bytes `!!` queue object prefix
`00 00 00 00 00 00 00 02 00 6a 00 00 68 02`, and the `0x1edc6` render
record carries context slot `0xc008004c` before compact helper `0x1fe76`
renders two Courier glyph-0 shapes. Fixture
`inline primary font selection stream renders visible rows` now carries that
same host-fetched stream through one mixed-stream state: `0x1205a`/`0x13eb8`
write `0x782ee6 = 0xc008004c`, HMI becomes `30`, the following `!!` bytes
read context slot `0`, and the rows use the pinned primary path. The
current-font-RAM handoff is now narrower:
fixture `live primary current-font RAM install feeds SI page-record rows`
starts from seeded `0x782ee6 = 0xc008004c` and `0x782ef6 = 0xc00ae122`, then
proves SI `0xc68a` calling `0xc428(0)` / `0xc4fc`, installing page-root slot
`0`, and rendering the following `!!` from that installed slot. Fixture
`live secondary current-font RAM install feeds SO page-record rows` starts
from the same seeded records, proves SO `0xc6b8` calling `0xc428(1)` /
`0xc4fc`, installing page-root slot `1`, and rendering the following `!!`
from that installed slot.
Composed fixtures `parsed primary selection current-font RAM feeds SI visible
rows` and `parsed secondary selection current-font RAM feeds SO visible rows`
tie those handoffs back to host-fetched selection streams
`ESC (s0p10h12v0s0b3T SI !!` and `ESC )s0p16h8v0s0b0T SO !!`; their
page-root install events, source contexts, compact object prefixes, and rows
match the pinned primary and secondary visible fixtures.
Fixture `inline secondary font selection stream renders SO visible rows` does
the same for `ESC )s0p16h8v0s0b0T SO !!`: secondary selection writes
`0x782ef6 = 0xc00ae122`, SO selects slot `1`, HMI becomes `18`, and the
following printable bytes render the same secondary Line Printer rows.
Fixture
`parsed secondary built-in font selection feeds visible SO page-record rows`
adds the secondary mirror: `ESC )s0p16h8v0s0b0T` selects context
`0xc00ae122`, SO handler `0xc6b8` selects slot `1`, printable bytes `!!`
queue object prefix `00 00 00 00 00 01 00 02 00 c9 00 00 cb 01`, and the
render record carries context slots `(0xc008004c, 0xc00ae122)` before compact
helper `0x207ac` renders two secondary Line Printer glyph rows.
Fixture
`primary symbol miss falls back before visible page-record rows` proves the
primary visible rows after `ESC (1234U` requests symbol word `0x9a55`,
`0x156de` misses that word in the class-zero candidates, uses fallback table
word `0x0115`, keeps slots `0x782354`, `0x782364`, and `0x782374`, then
selects the same context `0xc008004c`, map `0x782f32`, and compact object
prefix as the primary fixture.
Fixture
`secondary symbol miss falls back before visible SO page-record rows` proves
the same secondary visible rows after `ESC )1234U` requests symbol word
`0x9a55`, `0x156de` misses that word in the class-one candidates, uses
fallback table word `0x000e`, keeps slots `0x782330`, `0x782340`, and
`0x782350`, then selects the same context `0xc00ae122`, map `0x783032`, and
compact object prefix as the secondary SO fixture.

Fixture
`remembered secondary symbol feeds visible SO page-record rows` proves the
same secondary visible rows when remembered word `0x000e` at `0x782f0a`
recovers before the fallback table. The requested word `0x9a55` still misses
in `0x156de`; the remembered pass rejects slot `0x782324` / record
`0x019d18`, then matches slot `0x782330` / record `0x01a984`. The following
selection reaches context `0xc00ae122`, map `0x783032`, SO handler `0xc6b8`,
compact object prefix `00 00 00 00 00 01 00 02 00 c9 00 00 cb 01`, and row
digest `b8ee0f8dd3e6ed70afa219bc00605d75249ae047a67fb67189693057d7936e6c`.
Checked-in note [symbol-set-selection.md](symbol-set-selection.md)
documents `ESC (` / `ESC )` through `0x120be` and `0x1be22`: normal
symbol-set finals compute PCL codes as `(parameter << 5) + suffix`, store
requested words at `0x782ef4` / `0x782f04`, select through `0x156de`, and
consume active words at `0x783144` / `0x783146`; final `X` is instead
font-ID selection through `0x17708`, and final `@` dispatches `3@` plus
firmware-supported table variants backed by `0x782f1c/20/24/28`.
Checked-in note [symbol-map-patching.md](symbol-map-patching.md)
documents `0x14f16`: the ROM gates patching on selected Roman-8 font word
`0x0115`, handles hard-coded `0E` HP Roman Extension and `0U` ISO 6 ASCII
cases, and applies `0x14fce` patch-table pairs as `map[dst] = map[src]`.

Downloaded-font host command state is anchored in
`generated/analysis/ic30_ic13_font_control_flow.md`: `ESC *c#D` writes
normalized current font id `0x782f2e`, and `ESC *c#F` values `0..6`
dispatch through the table at `0x16db6` to all/current record release
helpers, current character/glyph record cleanup via `0x782f30`,
downloaded-record mark/unmark count transfers between `0x782782` and
`0x782786`, or active/current font-resource housekeeping. The harness
now also traces chained `ESC *c17d25e5F` through ROM parser modes
`0/1/3/16`, proving the parser table selects `0x15a56`, `0x15a18`, and
`0x16df6` before the modeled state updates.

Compact object mode behavior:

- `0x00`
  - Target: `0x1f034`
  - Payload entry shape: glyph byte, coordinate word
  - Current behavior: renders each glyph through table `0x1f08e`, with
    `0x1f414` splitting the row count at `0x783a20` and continuation rows
    written through `0x7810b4 + byte_pair_offset`, where `0x1f3d4`
    preserved the coordinate low-byte offset in `D2`
- `0x10`
  - Target: `0x1f0d2`
  - Payload entry shape: glyph byte, coordinate word
  - Current behavior: renders wide glyphs in 16-pixel chunks via
    `0x2f27c`, then a remainder through table `0x1f1ac`; crossing rows
    rerun from `0x7810b4 + byte_pair_offset` after the `0x1f414` count split
- `0x20`
  - Target: `0x1f1f0`
  - Payload entry shape: glyph byte, vertical/plane byte, coordinate
    word
  - Current behavior: offsets glyph bitmap data by `byte*0x80`, clips
    height to `0x80`, then renders through table `0x1f08e`; crossing
    rows rerun through the same table into the fallback buffer
- `0x30`
  - Target: `0x1f264`
  - Payload entry shape: glyph byte, vertical/plane byte, coordinate
    word
  - Current behavior: combines the `byte*0x80` plane adjustment with the
    wide-glyph chunk/remainder path and the same fallback rerun shape

Compact object disassembly contract:

- `0x1effe` enters with `A1` at compact object byte `+0x04`. It reads byte
  `+0x04` as the compact mode selector, reads byte `+0x05` low nibble as a
  render-record context-slot index, copies that slot from render
  `+0x24 + 4*n` into active context cache `0x783a2c`, and dispatches through
  table `0x1f024`.
- Table `0x1f024` maps selector bits `+0x04 & 0x30` to four renderers:
  `0x00 -> 0x1f034`, `0x10 -> 0x1f0d2`, `0x20 -> 0x1f1f0`, and
  `0x30 -> 0x1f264`.
- The four renderers all begin with object word `+0x06` as entry count. Each
  entry resolves a glyph byte through `0x1f354`, reads a packed coordinate
  word, calls `0x1f3d4` to compute the current-band destination, and calls
  `0x1f414` to split rows into current-band and fallback counts.
- Normal compact `0x1f034` and segmented compact `0x1f1f0` select row-copy
  table `0x1f08e` using the span byte count returned by `0x1f354`.
- Wide compact `0x1f0d2` and segmented-wide compact `0x1f264` split the span
  into full 16-byte chunks rendered by `0x2f27c` and a remainder rendered by
  table `0x1f1ac`.
- Segmented modes `0x1f1f0` and `0x1f264` consume the extra segment byte in
  each entry, move glyph source pointers by `segment * 0x80`, clamp the
  segment row count to at most `0x80`, and then use the same normal or wide
  row-copy path.
- If `0x1f414` reports fallback rows in the high word of `D3`, the compact
  renderer restarts the same row-copy path at fallback buffer `0x7810b4 + D2`.

The exact compact-renderer instruction boundaries are:

- `0x1effe..0x1f022`: compact object dispatch. It loads the context slot into
  `0x783a2c`, maps selector bits `+0x04 & 0x30` through table `0x1f024`, and
  calls the selected renderer.
- `0x1f034..0x1f03e`: normal compact setup. It reads object word `+0x06` as
  entry count, points `A4` at entries, and exits when the decremented count is
  negative.
- `0x1f040..0x1f066`: normal compact entry render. It resolves the glyph byte
  through `0x1f354`, reads the packed coordinate word, calls `0x1f3d4` and
  `0x1f414`, and dispatches through `0x1f08e[span]`.
- `0x1f068..0x1f088`: normal compact fallback and loop. If split `D3` has
  fallback rows, it restarts at `0x7810b4 + D2` and calls the same
  `0x1f08e[span]` helper before advancing to the next entry.
- `0x1f0d2..0x1f0dc`: wide compact setup. It reads object word `+0x06` as
  entry count, points `A4` at entries, and exits when the decremented count is
  negative.
- `0x1f0e0..0x1f0f4`: wide compact entry setup. It resolves the glyph byte,
  reads the packed coordinate word, and calls `0x1f3d4` and `0x1f414`.
- `0x1f0f8..0x1f148`: wide compact chunk planning. It splits span count into
  full 16-byte chunks and low-nibble remainder, then seeds
  `0x783a40/42/44/48` when fallback rows require a resumed source pointer.
- `0x1f148..0x1f180`: wide compact current-band writes. It clears phase
  `0x783a46`, calls `0x2f27c` for each full chunk, advances phase by `0x10`,
  and calls `0x1f1ac[remainder]` when a remainder exists.
- `0x1f180..0x1f1a6`: wide compact fallback and loop. If split `D3` has
  fallback rows, it restarts at `0x7810b4 + D2`, restores cached source state,
  and repeats the chunk/remainder path before advancing to the next entry.
- `0x1f1f0..0x1f204`: segmented compact setup and glyph resolution. It reads
  entry count, resolves the glyph byte, and saves the returned span in `D5`.
- `0x1f206..0x1f228`: segmented compact plane setup. It consumes the segment
  byte, applies the `segment * 0x80` source-plane offset, clamps rows to
  `0x80`, adjusts `A2/A3`, and reads the packed coordinate word.
- `0x1f22a..0x1f25e`: segmented compact destination, current-band, fallback,
  and loop. It calls `0x1f3d4` / `0x1f414`, dispatches through
  `0x1f08e[span]`, reruns the helper at `0x7810b4 + D2` for fallback rows,
  and advances to the next entry.
- `0x1f264..0x1f27a`: segmented-wide setup and glyph resolution. It reads
  entry count, resolves the glyph byte, and saves the returned span in `D5`.
- `0x1f27c..0x1f298`: segmented-wide plane setup. It consumes the segment
  byte, applies the `segment * 0x80` source-plane offset, clamps rows to
  `0x80`, adjusts `A2/A3`, and reads the packed coordinate word.
- `0x1f29a..0x1f2f2`: segmented-wide destination and chunk planning. It calls
  `0x1f3d4` / `0x1f414`, splits span into full chunks and remainder, and seeds
  wide-mode fallback caches.
- `0x1f2f2..0x1f328`: segmented-wide current-band writes. It calls `0x2f27c`
  for each full chunk, advances `0x783a46`, and calls `0x1f1ac[remainder]`
  when a remainder exists.
- `0x1f328..0x1f352`: segmented-wide fallback and loop. It restarts at
  `0x7810b4 + D2` for fallback rows, restores cached source state, repeats the
  chunk/remainder path, and advances to the next entry.

The shared glyph resolver boundaries are:

- `0x1f354..0x1f35e`: load active context cache `0x783a2c` and branch on
  bit `30`.
- `0x1f360..0x1f39e`: bit-30-set offset-table form. The resolver masks the
  context base to 24 bits, uses context word `+0x08` as the glyph-offset table
  base, indexes it by glyph byte, reads glyph fields `+0x04/+0x05/+0x06/+0x08`,
  derives bitmap pointer `A2`, span count `D1`, row count `D3`, and optional
  trailing-plane pointer `A3`.
- `0x1f3a0..0x1f3d2`: bit-30-clear fixed-record form. The resolver uses
  `context + 0x40 + 8*glyph`, reads inline row/span fields and the bitmap
  offset, derives `A2`, and sets optional trailing-plane pointer `A3` for
  multi-plane odd-span layouts.

The controlling disassembly evidence is
`generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst` at
`0x1effe..0x1f022` and
`generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst` at
`0x1f024..0x1f3d2`. Row-copy table targets are decoded in
`generated/analysis/ic30_ic13_render_row_copy_fixtures.md` and summarized in
the compact glyph row-copy checkpoint below.

Encoded raster span mode behavior:

- 0
  - Target: `0x1f8da`
  - Payload behavior: copy literal words from payload to consecutive
    destination words
- 1
  - Target: `0x1f8e6`
  - Payload behavior: expand each payload byte through word table
    `0x30914` and write the result to the current row plus one adjacent
    current or fallback row
- 2
  - Target: `0x1f920`
  - Payload behavior: expand even-indexed and odd-indexed payload bytes
    through longword table `0x30b14` in two passes and write each longword to
    up to three current/fallback row destinations, with row selection driven
    by clipped `D3` state
- 3
  - Target: `0x1f9c6`
  - Payload behavior: expand each payload byte through table `0x30914`
    twice to form one longword, then write to four current/fallback row
    destinations

Encoded raster mode disassembly contract:

- `0x1f88e..0x1f8c8` is the shared encoded-raster object consumer. `A1`
  arrives at object byte `+4`; the helper advances a payload cursor `A2` to
  byte `+5`, masks `object[5] & 0x03` into mode `D4`, reads object word `+6`
  into byte count `D5`, sets initial row count `D3 = mode + 1`, reads object
  word `+8` into packed coordinate `D1`, then calls `0x1f3d4` and `0x1f414`.
  The byte-pair offset preserved by `0x1f3d4` is copied to `A3` before the
  band split so fallback row pointers can use `0x7810b4 + A3`.
- `0x1f8da..0x1f8e4` is literal mode `0`. If byte count `D2` is nonzero, it
  repeatedly copies one word from payload cursor `A2` to destination `A1`,
  advances both pointers by two bytes, subtracts two from `D2`, and loops
  while the unsigned result remains positive. The ROM does not have a separate
  odd-byte tail path in this helper.
- `0x1f8e6..0x1f91e` is mode `1`. It builds row pointer `A4` as
  `A1 + 0x783a1c` when all two scaled rows fit the current band; if the split
  word from `0x1f414` has a nonzero high word, it instead sets
  `A4 = 0x7810b4 + A3`. It then reads each payload byte, indexes word table
  `0x30914`, and writes the expanded word to both `A1` and `A4`.
- `0x1f920..0x1f9c4` is mode `2`. It uses the high word of split `D3` as a
  fallback-row count to choose three row pointers: all current rows, row 2 in
  fallback, rows 1..2 in fallback, or fallback rows beginning at
  `0x7810b4 + A3`. Shared loop `0x1f9a0..0x1f9c4` reads every other payload
  byte, indexes longword table `0x30b14`, writes the longword to `A1`, `A4`,
  and `A5`, then advances each row pointer by six bytes. After the first pass,
  `0x1f96c..0x1f98a` advances destination pointers by two or four bytes based
  on the low nibble of `$a001`, rewrites `$a001` with bit `0x10` set, skips
  the payload cursor by one byte, and runs the same loop for the odd-indexed
  payload bytes when any remain.
- `0x1f9c6..0x1fa5a` is mode `3`. It chooses four row pointers from the split
  high word: all current rows, row 3 in fallback, rows 2..3 in fallback, or
  rows 1..3 in fallback beginning at `0x7810b4 + A3`. For each payload byte,
  it reads `0x30914[byte]`, expands the high and low bytes of that word
  through `0x30914` again to form one longword, writes that longword to `A1`,
  `A4`, `A5`, and `A6`, and advances each row pointer by four bytes.

The exact encoded-raster instruction boundaries are:

- `0x1f88e..0x1f8a4`: parse the encoded object header. Starting from object
  byte `+0x04`, it reads `object[5] & 0x03` as mode `D4`, object word `+0x06`
  as payload byte count `D5`, sets requested row count `D3 = mode + 1`, reads
  packed coordinate word `+0x08` into `D1`, and calls destination helper
  `0x1f3d4`.
- `0x1f8aa..0x1f8c8`: copy byte-pair offset `D2` to `A3`, call `0x1f414` to
  split rows between current band and fallback buffer, restore byte count
  into `D2`, select table `0x1f8ca[mode]`, and dispatch to the mode helper.
- `0x1f8da..0x1f8e4`: mode `0` literal copy. A zero byte count returns;
  otherwise the helper copies payload words from `A2` to consecutive
  destination words at `A1`, subtracting two bytes from `D2` per store.
- `0x1f8e6..0x1f900`: mode `1` row setup. It seeds second row pointer `A4`
  as `A1 + 0x783a1c`, or switches it to fallback `0x7810b4 + A3` when split
  `D3` has a nonzero high word.
- `0x1f900..0x1f91e`: mode `1` expansion. It indexes word table `0x30914` by
  each payload byte and writes the expanded word to both `A1` and `A4`.
- `0x1f920..0x1f964`: mode `2` setup. It loads stride `0x783a1c`, derives the
  even-byte pass count from payload byte count `D2`, and chooses row pointers
  `A1`, `A4`, and `A5` from the current band or fallback buffer based on split
  `D3` high word.
- `0x1f964..0x1f99e`: mode `2` two-pass expansion. The first pass uses table
  `0x30b14` and shared loop `0x1f9a0`; the second pass shifts all row pointers
  by two or four bytes from `$a001`, rewrites `$a001` with bit `0x10`, skips
  to the odd payload byte stream, and repeats the same loop when bytes remain.
- `0x1f9a0..0x1f9c4`: shared mode-`2` loop. It reads every other payload byte,
  indexes longword table `0x30b14`, writes that longword to `A1`, `A4`, and
  `A5`, and advances each row pointer by six bytes.
- `0x1f9c6..0x1fa26`: mode `3` setup. It loads stride `0x783a1c`, rejects an
  empty byte count, and chooses row pointers `A1`, `A4`, `A5`, and `A6` from
  the current band or fallback buffer based on split `D3` high word.
- `0x1fa26..0x1fa5a`: mode `3` expansion. It indexes `0x30914` with each
  payload byte, expands both bytes of the resulting word through `0x30914`
  again, combines those words into one longword, and writes it to all four row
  pointers.

Encoded raster field groups:

- Canonical object fields:
  - object byte `+0x04`: class byte `0x80..0xff`, dispatching to `0x1f88e`
    through the bucket walker.
  - object byte `+0x05`: encoded mode in bits `0..1`.
  - object word `+0x06`: payload byte count consumed as `D5` / `D2`.
  - object word `+0x08`: packed coordinate consumed by `0x1f3d4`.
  - object `+0x0a..`: payload bytes or literal words consumed by the selected
    mode helper.
- Derived/cache state:
  - `0x783a1c`: row stride used to derive adjacent current-band row pointers.
  - `0x783a20`, `0x783a28`, `0x7839f8..`, and `$a001`: destination state
    consumed or updated through `0x1f3d4` / `0x1f414`.
  - `0x7810b4 + byte_pair_offset`: fallback row base used by modes `1..3`
    when split `D3` reports rows beyond the current band.
  - ROM tables `0x30914` and `0x30b14`: expansion tables for modes `1` / `3`
    and mode `2`, respectively.
- Parser scratch:
  - none in the mode helpers. The delayed `ESC *b#W` command record has
    already been reduced to encoded raster object fields by `0x105d0` /
    `0x13070` / `0x13250`.
- Firmware bookkeeping:
  - mode `2` rewrites `$a001` between its even-byte and odd-byte passes so
    the second pass uses the shifted subbyte phase.
- Unknown:
  - no ROM-local mode dispatch or row-pointer branch remains unknown for
    `0x1f88e..0x1fa5a`. Physical engine consumption of the rendered band is
    outside this helper family.

Writers and consumers:

- Writers are raster producers `0x13070` / `0x13250` / `0x138de`, which create
  object bytes `+0x04..+0x0a` from raster state and copied payload bytes.
- Consumers are `0x1efc2`, which dispatches the `0x80..0xff` object class,
  `0x1f88e`, which parses the object and selects the mode helper, and helpers
  `0x1f8da`, `0x1f8e6`, `0x1f920`, `0x1f9a0`, and `0x1f9c6`, which perform
  the actual destination stores.
- Output effect is direct stores to current-band or fallback destinations in
  the order selected by the bucket chain. The encoded raster helpers do not
  read destination words before writing expanded payload data.

Evidence and boundaries:

- Disassembly evidence:
  `generated/disasm/ic30_ic13_bitmap_encoded_span_modes_01f88e.lst` at
  `0x1f88e..0x1fa5a`.
- ROM table evidence:
  `generated/analysis/ic30_ic13_render_expansion_fixtures.md` for decoded
  examples from `0x30914` and `0x30b14`.
- Fixture evidence:
  encoded-raster fixtures named `0x1f88e mode-0 raster object renders queued
  literal row`, `0x1f88e mode-1 raster object expands queued bytes into two
  rows`, `0x1f88e mode-2 raster object expands queued byte pair into three
  rows`, `0x1f88e mode-2 raster object renders sub-byte shifted expanded
  rows`, `0x1f88e mode-2 raster object clips current-band rows and continues
  in fallback buffer`, and `0x1f88e mode-3 raster object expands queued bytes
  into four rows`.
- Unresolved boundary:
  streams that change accepted payload count or object splitting before
  `0x1f88e` start back at `0x105d0..0x13250`; streams that reach
  `0x1f88e` with the same object fields use the helper contract above.

The generated fixture report
`generated/analysis/ic30_ic13_render_expansion_fixtures.md` now pins
down deterministic sample expansions for these encoded raster modes:

- mode 0 literal word-copy payloads;
- mode 1 byte-to-word expansion through `0x30914`;
- mode 2 byte-to-long expansion through `0x30b14`;
- mode 3 cascaded byte expansion through `0x30914`.

The generated fixture report
`generated/analysis/ic30_ic13_render_destination_fixtures.md` now pins
down synthetic-state expectations for:

- `0x1f3d4` packed coordinate decode into row index, byte-pair offset,
  `0xa001` sub-byte flag, and destination pointer;
- `0x1f414` count splitting at the current band boundary;
- the main `0x1f626` destination branches: current band, shifted current
  band, and fallback buffer.

The generated fixture report
`generated/analysis/ic30_ic13_render_row_copy_fixtures.md` now decodes
the compact glyph row-copy tables into deterministic A1/A2/A3 write
traces:

- `0x1f08e` maps glyph byte widths 1..16 to helper routines and
  row-count tables;
- `0x1f1ac` maps wide-glyph remainder widths 1..16 after full 16-byte
  chunks;
- `0x2f27c` renders full 16-byte chunks using `0x2f2ac`, with `0x783a46`
  as the current horizontal phase;
- odd byte widths copy the trailing byte from `A3`, while even byte
  widths are word copies from `A2`.

Generated reference-lead classification:

- `generated/analysis/ic30_ic13_render_path_references.md` uses
  "unclassified alias/reference lead" for some references that land inside a
  helper body or jump-table tail instead of at a named routine entry. These
  are not separate command-family or render-route gaps once the owning helper
  is known.
- Examples in `0x1f626` and the encoded-raster helpers are interior field
  reads: `0x1f6e2` is the fallback-buffer branch of destination helper
  `0x1f626`, `0x1f8ec` is mode-1 stride use inside `0x1f8e6`, and
  `0x1f926`, `0x1f9cc`, `0x1f9fc`, `0x1fa0a`, and `0x1fa18` are setup or
  row-pointer branches inside mode-2/mode-3 encoded-raster helpers.
- Examples in the compact row-copy range are row-helper table interiors:
  `0x1fa5e`, `0x1fe78`, `0x20292`, `0x207ae`, and later entries through
  `0x2f294` are reached through tables `0x1f08e`, `0x1f1ac`, row-count
  subtables, or the wide helper `0x2f27c`. Their semantic owners are the
  compact glyph row-copy tables below, not standalone parser or page-object
  paths.
- A new gap should therefore start from a changed selector, span, row count,
  band split, or invalid target/source boundary. A generated alias/reference
  lead alone is only evidence to map back to the owning helper.

### Compact Glyph Row-Copy Semantic Checkpoint

This checkpoint covers the compact glyph pixel-copy layer under the compact
object modes documented above. It connects parser-produced built-in and
downloaded font records to the unrolled row-copy helpers selected through
tables `0x1f08e` and `0x1f1ac`, including the A2/A3 split-plane layout needed
for odd byte spans.

Field groups:

- Canonical font/context state:
  - render-record context slot selected by compact object byte `+5` low nibble
    and copied by `0x1edc6` from page-root `+0x2c..+0x68`.
  - `0x783a2c`: active context/resource longword loaded by `0x1f008` before
    `0x1f354` resolves each glyph.
  - bit-30-set resource form: `0x1f354` masks the context base to 24 bits,
    adds context word `+8` to find an offset table, reads the glyph longword
    offset, then reads glyph bytes/words `+4`, `+5`, `+6`, and `+8` to derive
    bitmap start, layout mode, row count, and width.
  - bit-30-clear inline form: `0x1f354` reads fixed eight-byte glyph entries at
    `context + 0x40 + 8 * glyph_index`, deriving row count, span byte count,
    and bitmap offset from the inline record.
- Canonical glyph payload layout:
  - `A2`: prefix/word plane consumed by all even-span row-copy helpers and by
    the word portion of odd-span helpers.
  - `A3`: trailing-byte plane used when span byte count is odd. `0x1f354`
    points `A3` at the trailing plane for inline odd spans; downloaded
    split-plane reader `0x16942` stores this same layout.
  - `D1`: span byte count returned by `0x1f354` and used as the
    table-selection index.
  - `D3`: row count returned by `0x1f354`, then split by `0x1f414` into
    current-band rows and fallback rows.
- Derived/cache row-copy state:
  - `0x1f08e`: main width table. Indexes `1..16` select helpers
    `0x1fa5c`, `0x1fe76`, `0x20290`, `0x207ac`, `0x20cc8`, `0x212e4`,
    `0x21900`, `0x2201c`, `0x22738`, `0x22f54`, `0x23770`, `0x24090`,
    `0x249b0`, `0x253d0`, `0x25df0`, and `0x26910`.
  - `0x1f1ac`: wide-glyph remainder table. Indexes `1..16` select helpers
    `0x27430`, `0x27850`, `0x27d84`, `0x283ba`, `0x289f0`, `0x29126`,
    `0x2985c`, `0x2a092`, `0x2a8c8`, `0x2b1fe`, `0x2bb34`, `0x2c56e`,
    `0x2cfa8`, `0x2dae2`, `0x2e62e`, and `0x2f27c`.
  - Wrapped width-byte invalid targets are produced by the same mode-0 table
    when the full span word is used as an index instead of a small byte-width
    index. For span `0x0102`, `0x1f034` shifts `D5` left by two and reads
    table entry `0x1f08e + 0x0408 = 0x1f496`; bytes `00 00 66 cc` jump to
    `0x0066cc`. Listing
    `generated/disasm/ic30_ic13_invalid_compact_mode0_target_0066c0.lst`
    shows that address is unrelated control code (`tst.b $7821b9.l`,
    scheduler/wait helper calls, and stack-frame unwind), not a row-copy
    helper head. The compact renderer therefore has a precise invalid target
    boundary for this low-byte case and no pixel contract after the jump.
  - row-count jump tables under each helper map `D3` rows to an unrolled copy
    tail. Fixture report
    `generated/analysis/ic30_ic13_render_row_copy_fixtures.md` decodes the
    representative row-count targets and final A1/A2/A3 deltas.
  - span-2 helper `0x1fe76` is an unchecked row-count jump table over `D3`:
    `0x1fe76..0x1fe88` loads table base `0x1fe8a`, shifts `D3` left by two,
    reads a longword target, and jumps. The valid entries are `0..128`; entry
    `0` at `0x1fe8a` points to `0x2028e`, entry `127` at `0x20086` points
    to `0x20092`, and entry `128` at `0x2008a` points to `0x2008e`, which is
    the first row-copy instruction rather than another pointer. Entries above
    `128` read executable code bytes as pointer data; the row-`0x0102`
    fallback index `200` reads target longword `0x329ad3c0`.
  - `0x783a40`, `0x783a42`, `0x783a44`, `0x783a46`, and `0x783a48`: wide-mode
    row-skip, fallback row-skip, remainder row-skip, current 16-byte chunk
    phase, and fallback source pointer caches written by `0x1f0d2` and
    `0x1f264`.
  - `0x7810b4 + byte_pair_offset`: fallback destination base used when
    `0x1f414` reports rows past the current band. For compact helpers,
    `0x1f3d4` leaves this offset in `D2`; for `0x1f626` callers, the helper
    leaves the same offset in `A2`.
- Parser scratch:
  - downloaded-character command records such as `80 57 00 06 00 00`,
    `80 57 00 12 00 00`, `80 57 01 83 00 00`, and
    `80 57 08 91 00 00` are parser/delayed-payload scratch. They prove how
    resource images are installed, but are not consumed by row-copy helpers.
  - font-selection command records and symbol-set parser state are scratch
    once `0x13eb8`, `0x14c64`, `0x14f16`, `0xc428`, and `0xc4fc` have
    installed page-root context slots.
- Firmware bookkeeping:
  - continuation fields for partial downloaded payload copies
    `0x7827ca`, `0x7827ce`, `0x7827d6`, and `0x7827d8` preserve future
    canonical glyph payload layout, but are not read by row-copy helpers.
  - invalid overlarge row-count table targets, such as the row-`0x0102`
    fallback index through helper `0x1fe76`, are firmware failure boundaries
    rather than pixel output. For row `0x0102`, fallback count `200` reads
    bytes `32 9a d3 c0` from the row-copy code region as target
    `0x329ad3c0`.
- Unknown:
  - no unresolved middle edge remains for documented downloaded-descriptor
    metric formulas, legal selected-context forms, `0xd4ac` / `0xd8fc`
    consumer gates, or segment-list render handoff.
  - the remaining ROM-local compact-helper boundaries are exact computed-jump
    boundaries, not parser/page-record/render-dispatch uncertainty: wrapped
    low-width mode-0 targets selected through `0x1f034 -> 0x1f08e`, and short
    compact high-row fallback targets selected through `0x1fe76 -> 0x1fe8a`.
  - exact HP manual names for consumed-but-not-staged validation fields remain
    external/manual naming work.

Writers:

- `0x13eb8`, `0x14c64`, `0x14d9c`, `0x14e24`, `0x14eb6`, and `0x14f16` build
  or refresh character maps and selected built-in/inline context records that
  later become page-root context slots.
- `0xc428` and `0xc4fc` install active current-font records into page-root
  context slots copied by `0x1edc6`.
- `0x16498` installs downloaded glyph table entries, glyph records, bitmap
  offsets, and bitmap bytes. `0x168dc` writes linear bitmap payloads; `0x16942`
  writes split-plane prefix bytes plus trailing A3 bytes.
- `0x12f2e` writes compact page-record objects whose selector bits choose
  normal, wide, segmented, or segmented-wide compact modes.
- `0x1f0d2` and `0x1f264` write wide-mode caches `0x783a40`,
  `0x783a42`, `0x783a44`, `0x783a46`, and `0x783a48` before calling
  `0x2f27c` and `0x1f1ac` helpers.

Readers and consumers:

- `0x1effe` dispatches compact objects to `0x1f034`, `0x1f0d2`, `0x1f1f0`, or
  `0x1f264`.
- `0x1f354` consumes the active context and glyph index, then returns `A2`,
  optional `A3`, span `D1`, and rows `D3`.
- `0x1f034` and `0x1f1f0` select `0x1f08e[D1]` for normal and segmented
  compact glyphs; `0x1f1f0` first applies the segment byte as a `0x80`-row
  plane offset and clamps each segment to at most `0x80` rows.
- `0x1f0d2` and `0x1f264` render full 16-byte chunks through `0x2f27c`, then
  select `0x1f1ac[remainder]` for the trailing width. `0x1f264` combines this
  with the segmented `0x80`-row plane offset.
- Row-copy helpers consume `0x783a1c` as the destination stride. Even widths
  copy only A2 words; odd widths copy A2 words plus one A3 trailing byte per
  row.

Output effect:

- Fixture `parsed primary built-in font selection feeds visible page-record
  rows` checks that a host-fetched primary font-selection stream installs context
  `0xc008004c`, queues compact object
  `00 00 00 00 00 00 00 02 00 6a 00 00 68 02`, and renders Courier rows
  through helper `0x1fe76`.
- Fixture `parsed secondary built-in font selection feeds visible SO
  page-record rows` checks that secondary context `0xc00ae122` reaches compact
  helper `0x207ac`.
- Fixture `non-Roman symbol streams select visible built-ins` checks that the
  primary `0N` / `10U` / `11U` symbol streams render from selected contexts
  `0xc0080cb8`, `0xc4080418`, and `0xc4080868`, while the secondary
  `0N` / `10U` / `11U` streams cross SO and render from contexts
  `0xc00ae122`, `0xc40ad87a`, and `0xc40adcce`.
- Fixture `real final-@ default-table streams select visible built-ins`
  checks that the ROM-backed `@0` / `@1` / `@2` / `@3` symbol defaults feed later
  font-selection tails into visible compact rows: the primary tail renders
  from context `0xc0080cb8`, and the secondary tail renders from context
  `0xc00ad4aa` after SO.
- Fixtures `font-ID built-in selection feeds visible page-record rows`,
  `font-ID primary inline/downloaded selection feeds visible page-record rows`,
  and `font-ID inline/downloaded selection feeds visible page-record rows`
  check that final-`X` font-ID selection reaches compact output for the bit-30
  built-in path and both primary/secondary bit-30-clear inline/downloaded
  paths.
- Fixtures `font-ID non-selected exits keep prior visible rows` and
  `font-ID secondary non-selected exits keep prior SO visible rows` check that the
  corresponding final-`X` helper exits preserve prior primary/secondary
  selected contexts before the following printable/SO tail reaches compact
  rendering. The secondary preserved path renders object prefix
  `00 00 00 00 00 01 00 02 20 c9 00 20 cb 01` from context `0xc40ad87a`.
- Fixture `0x13eb8 no-dispatch exits keep prior visible rows` checks that the
  selected-font-refresh exits preserve the prior selected context before the
  following printable/SO tail reaches compact rendering.
- Fixture `host-fetched linear downloaded character stream renders through
  0x168dc` checks that parser-produced `ESC )s6W` installs glyph `0x26`, queues
  selector `0x0003`, and renders three rows through mode-0 helper `0x1fe76`.
- Fixture `host-fetched even-span wide downloaded character renders through
  0x1f0d2` checks that parser-produced `ESC )s18W` installs glyph `0x29`, queues
  selector `0x1003`, renders one full 16-byte chunk through `0x2f27c`, then
  renders a two-byte remainder through `0x1f1ac`.
- Fixture `host-fetched split-plane segmented downloaded character renders
  through 0x1f1f0` proves odd-span split-plane layout: `0x16942` writes prefix
  bytes and trailing bytes, then `0x1f1f0` renders segment `1` from A2 offset
  `0x0100` and A3 trailing offset `0x0080`.
- Fixture `0x16498-backed downloaded character object renders segmented-wide
  compact row` proves selector `0x3003` reaches `0x1f264`, uses one full
  16-byte chunk through `0x2f27c`, and uses a one-byte remainder.
- Fixture `downloaded glyph width-span matrix publishes and renders all main
  helpers` proves parser-produced downloaded-character spans `1..16` install
  widths `8..128`, preserve odd-span split-plane copies where required, publish
  bucket `0` through FF, and derive rows from the installed bitmap through all
  sixteen main `0x1f08e` helpers from `0x1fa5c` through `0x26910`.
- Fixture `downloaded glyph wide-remainder matrix publishes and renders
  compact chunks` proves parser-produced downloaded-character spans `17..32`
  install widths `136..256`, publish bucket `0` as selector `0x1003`, dispatch
  object byte `0x10` through `0x1effe` to `0x1f0d2`, render full chunks through
  `0x2f27c`, render remainders `1..15` through `0x1f1ac[remainder]`, and
  derive rows from the installed bitmap. Span `32` is the no-remainder
  two-full-chunk sibling and does not select a remainder helper. The same
  fixture now probes
  compact-wide spans `33`, `48`, `49`, `64`, and `255`; parser install,
  selector `0x1003`, object byte `0x10`, bucket-0 publication, zero-drain
  returns, full-chunk/remainder metadata, `0x2f27c` A2 source-walk rows, and
  render-record width words `>= span` are pinned, and the high-span rendered
  rows are derived from those installed bitmap rows.
- Fixture `downloaded glyph width-byte boundary truncates page-record span`
  proves descriptor-accepted spans `0x00ff`, every span `0x0100..0x0111`,
  `0x017f`, `0x0180`, `0x01fe`, and `0x020d` keep canonical installed width
  words, but the current unflagged printable source record supplies only byte
  `+0` to `0x12f2e`. Source width bytes `0x00..0x10` queue selector `0x0003`;
  source width bytes `0x11..0xff` queue
  selector `0x1003`. The same fixture now carries valid compact-wide wrapped
  cases to pixels: spans `0x00ff`, `0x0111`, `0x017f`, `0x0180`, and `0x01fe`
  render through `0x1f0d2` using the installed bitmap rows. Low source
  bytes `0x00..0x10` still dispatch through compact mode-0 at `0x1effe`,
  reading helper entries outside decoded row-copy helper heads. The fixture
  records exact target classes: `0x0102` is the only sampled low-byte case that
  stays in firmware, at address `0x0066cc` with opcode `0x4a39`; the other
  sampled low-byte cases target out-of-firmware longwords including
  `0x20700000`, `0x4e90202c`, `0x4cdf1030`, `0x4e750001`, `0xf4e00001`,
  `0xf5960001`, and `0x4e904cdf`.
- Fixture `downloaded glyph segmented-wide matrix publishes and renders
  compact chunks` proves parser-produced downloaded-character spans `17..32`
  with rows `0x81` install widths `136..256`, publish buckets `0` and `8` as
  selector `0x3003`, dispatch segment `1` object byte `0x30` through
  `0x1effe` to `0x1f264`, render full chunks through `0x2f27c`, render
  remainders `1..15` through `0x1f1ac[remainder]`, and derive output from the
  installed segment-1 bitmap rows. Span `32` is the segmented no-remainder
  sibling. The same fixture now probes segmented-wide spans `33`, `48`, `49`,
  and `64` at rows `0x81`; segment bucket/object metadata and chunk/remainder
  state are pinned, and segment-1 rendered rows are derived from the installed
  bitmap rows above span `32`.
- Fixture `downloaded segmented-wide row-span cross-products render selected
  segment` extends that path beyond row `0x81`: row words `0x0082` and
  `0x0083` crossed with spans `17`, `18`, `31`, and `32` publish selector
  `0x3003` buckets `0` and `8`, dispatch segment `1` through `0x1f264`, and
  derive selected segment rows from the installed bitmap.
- Fixtures `downloaded segmented-wide high-row fallback renders selected
  segment` and `downloaded segmented-wide high-row even-span fallback renders
  selected segment` prove sampled higher-row fallback siblings: row word
  `0x0181` at spans `17` and `18` publishes selector `0x3003`, dispatches
  bucket `8` segment `1` through `0x1f264`, splits through `0x1f414` into
  `32` current rows and `96` fallback rows, and matches both row groups to the
  installed bitmap.
- Fixture `downloaded segmented-wide high-row span-32 fallback renders
  selected segment` proves the no-remainder large-span sibling for the same
  row word `0x0181`: span `32` dispatches bucket `8` segment `1` through
  `0x1f264`, uses two full chunks with no remainder helper, splits into `32`
  current rows and `96` fallback rows, and matches both row groups to the
  installed bitmap.
- Fixture `downloaded segmented-wide high-row span-31 fallback hits source
  boundary` pins the adjacent large-remainder boundary: the same selected
  segment path reaches `validate_wide_compact_row_copy`, which reports
  fallback A2 source read past the modeled bitmap at `+0xb50`.
- Fixtures `downloaded segmented-wide row-0x0182 fallbacks render selected
  segment` and `downloaded segmented-wide row-0x0182 span-31 fallback hits
  source boundary` repeat that higher-row fallback split for the next row word.
  Row `0x0182` succeeds at spans `17`, `18`, and `32` through bucket `8`
  segment `1`, `0x1f264`, and the `0x1f414` `32/96` current/fallback split;
  the adjacent span-31 case reaches the same selected segment path and stops at
  fallback A2 source offset `+0xb50`.
- Fixtures `downloaded segmented-wide row-0x01ff fallbacks render selected
  segment` and `downloaded segmented-wide row-0x01ff span-31 fallback hits
  source boundary` repeat that split for row word `0x01ff`, the highest
  sampled low-byte-above-`0x80` row. Spans `17`, `18`, and `32` render bucket
  `8` segment `1` with the same `32/96` split; span `31` stops at fallback A2
  source offset `+0xb50`.
- Fixtures `downloaded segmented-wide row-0x0281 fallbacks render selected
  segment`, `downloaded segmented-wide high-row 0x02xx matrix renders selected
  segment`, `downloaded segmented-wide high-row 0x03xx matrix renders selected
  segment`, and `downloaded segmented-wide high-row 0x04xx matrix renders
  selected segment`, plus `downloaded segmented-wide high-row 0x05xx matrix
  renders selected segment` and `downloaded segmented-wide high-row
  parser-limit matrix renders selected segment`, extend the selected-segment
  render evidence through row words `0x0281`, `0x0282`, `0x02ff`, `0x0381`,
  `0x0382`, `0x03ff`, `0x0481`, `0x0482`, `0x04ff`, `0x0581`, `0x0582`,
  `0x05ff`, `0x0681`, `0x0682`, `0x06ff`, `0x0781`, `0x0782`, and `0x0787`.
  The corresponding `0x0281`, `0x02xx`, and `0x03xx` span-31 fixtures stop at
  fallback A2 offset `+0xb50`; fixtures
  `downloaded segmented-wide high-row 0x04xx oversized payload counts stop
  before renderer` and
  `downloaded segmented-wide high-row 0x05xx oversized payload counts stop
  before renderer`, plus `downloaded segmented-wide high-row parser-limit
  oversized counts stop before renderer`, classify the `0x04xx` span-31/span-32,
  `0x05xx` span-24-or-above, and final span-17 parser-limit cases as
  payload-count boundaries before renderer entry.
- Fixture `downloaded segmented-wide row-byte boundary truncates page-record
  segments` proves span-`0x11` downloaded glyphs keep canonical installed row
  words `0x0002`, `0x007f`, `0x0080`, `0x0081`, `0x0083`, `0x00fe`,
  `0x00ff`, `0x0100`, `0x0101`, `0x0181`, `0x0182`, `0x01ff`, `0x0200`,
  and `0x0201`, but the current unflagged printable source record supplies
  only byte `+1` to `0x12f2e`. Low row bytes above `0x80` queue selector
  `0x3003` for segments `1` and `0`; low row bytes `0x00..0x80` queue
  selector `0x1003`. The same fixture now pins the first render split:
  `0x0100` and `0x0101` dispatch through `0x1f0d2` with canonical row words,
  splitting `80/176` and `80/177`; `0x0181` reaches `0x1f264` only for
  produced segment `1` (`32/96`) and segment `0` (`80/48`).
- Fixture `host-fetched rows-0x102 downloaded glyph FF publication truncates
  page-record rows` proves the failure boundary: installed row count `0x0102`
  reaches `0x1f414`, but fallback row count `200` indexes past the valid
  helper `0x1fe76` row-count table, so no pixel-output claim is made.

#### Invalid Compact Helper Boundary Composition

This checkpoint composes the two invalid compact-helper families that remain
after parser, installed-glyph, page-object, publication, bridge, and compact
dispatch are already documented. Both are ROM-local computed jumps inside the
compact renderer. They are not evidence gaps in the host parser, downloaded
glyph installer, page-record allocator, publication path, or `0x1ef6a`
dispatch.

Field groups:

- Canonical state:
  installed downloaded-glyph records written by `0x16498`, including 16-bit
  row words and width words; bitmap payload bytes; current page root; compact
  bucket objects; published bucket roots; and render-record bucket roots.
- Derived/cache state:
  low row/width bytes exposed by the printable source record to `0x12f2e`,
  compact selector `0x0003` or `0x1003`, active compact target selected by
  `0x1effe`, row split from `0x1f414`, and table targets read from
  `0x1f08e` or `0x1fe8a`.
- Parser scratch:
  delayed `ESC )s#W` command records, payload byte budgets, drain status, and
  next parser handler. These prove how the installed glyph exists, but they
  are no longer consumed once compact rendering begins.
- Firmware bookkeeping:
  stream allocator state, publication flag `0x782996`, render progress, and
  invalid computed targets used only as failure boundaries.
- Hardware/external state:
  none. These are ROM table/control-flow boundaries.
- Unknown:
  no pixel contract is claimed after the invalid computed target. The known
  facts stop at the table read and target longword.

Writers:

- `0x16498` preserves canonical installed row and width words in the
  downloaded-glyph record.
- `0x12f2e` writes the compact page object from the printable source record,
  using low row/width bytes for selector and object shape.
- `0xff1e` publishes the page root, and `0x1ed84` / `0x1edc6` copy the
  published bucket roots into render-record state.

Readers and consumers:

- `0x1ef6a` / `0x1efc2` walk the active bucket and call `0x1effe`.
- `0x1effe` selects compact mode-0 `0x1f034` for selector `0x0003`, or
  compact-wide `0x1f0d2` for selector `0x1003`.
- Wrapped low-width mode-0 cases enter `0x1f034`, index main helper table
  `0x1f08e` with the full span word, and can jump to non-helper targets.
- Short high-row fallback cases enter span-2 row helper `0x1fe76`, index
  row-count table `0x1fe8a` with fallback row count `D3`, and can read
  executable copy-tail bytes as a target.

Exact boundaries:

- Wrapped width low bytes:
  span `0x0102` reaches `0x1f034`, shifts full span word `D5` left by two,
  reads `0x1f08e + 0x0408 = 0x1f496`, and jumps to target `0x0066cc` from
  bytes `00 00 66 cc`. Listing
  `generated/disasm/ic30_ic13_invalid_compact_mode0_target_0066c0.lst` shows
  this is unrelated control code, not a row-copy helper head: `0x0066cc`
  starts with `tst.b $7821b9.l`, branches to `0x66e2`, can wait on
  `0x10c8(0x780202)`, calls control/status helpers `0x15a6`, `0x15ac`,
  `0x9ac2`, and `0x6722`, and then unwinds a normal stack frame through
  `movem.l (A7)+, D0/D5/A4-A5`, `unlk A6`, and `rts`. Other sampled
  low-byte spans select out-of-firmware or non-helper longwords such as
  `0x20700000`, `0x4e90202c`, `0x4cdf1030`, `0x4e750001`, `0xf4e00001`,
  `0xf5960001`, and `0x4e904cdf`.
- Short compact high rows:
  installed rows `0x0101..0x0103` preserve canonical row words, but
  `0x12f2e` sees low row bytes `0x01..0x03` and publishes selector `0x0003`
  bucket `1`. `0x1f414` splits those installed row words at coord `0x6601`
  into `58` current-band rows plus fallback counts `199`, `200`, and `201`.
  Helper `0x1fe76..0x1fe88` loads row-count table base `0x1fe8a`, shifts
  `D3` left by two, reads an unchecked target, and jumps. Valid entries end at
  index `128` (`0x2008a -> 0x2008e`). Indexes `199..201` read copy-tail code
  bytes, and row `0x0102` fallback index `200` reads target `0x329ad3c0`.

Output effect:

- The valid sibling sides remain reproducible. Width source bytes `0x11..0xff`
  dispatch through `0x1f0d2`, and row words `0x0001..0x00ff` dispatch through
  documented short or segmented helpers.
- The invalid sibling sides have no documented pixels after the computed
  target. A reproducer should preserve all state up to the target selection and
  then report the exact invalid compact-helper boundary.

Evidence status:

- Direct ROM evidence covers the boundary addresses and target longwords because they
  are direct disassembly/table reads from
  `generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst`,
  `generated/disasm/ic30_ic13_bitmap_row_copy_tables_01fa5c.lst`, and
  `generated/disasm/ic30_ic13_invalid_compact_mode0_target_0066c0.lst`.
- Direct ROM evidence covers the producer and bridge state because the downloaded-glyph
  notes cite parser-produced command families that install the records, publish the
  compact objects, and reach `0x1effe`. Fixture evidence is only supporting path
  evidence; it is not an external pixel oracle.

Evidence status:

- Direct ROM evidence covers `0x1f354` context-form split, A2/A3 source layout, table
  selection, even/odd span copy behavior, wide chunk/remainder behavior, and
  segmented row-plane offsets because these are pinned by disassembly plus
  generated row-copy fixtures.
- Direct ROM evidence covers parser-produced built-in, normal downloaded, even-span wide
  downloaded, split-plane segmented, and segmented-wide examples because the
  named fixtures tie host bytes to installed records, queued compact objects,
  dispatch targets, and row-construction inputs.
- Direct ROM evidence covers the documented symbol-selection variants because non-Roman
  `0N` / `10U` / `11U`, real final-`@` default-table streams, final-`X`
  success paths, final-`X` non-selected exits, and `0x13eb8` no-dispatch exits
  all carry host-fetched parser state through selected contexts, compact
  object prefixes, bridge context slots, and ROM-helper row-construction
  inputs. Row digests in the fixtures are consistency checks for those
  ROM-derived rows, not independent rendered-output evidence.
- The remaining boundary is exhaustive descriptor/font-width coverage because downloaded
  spans `1..32`, high-span compact-wide row checks through span `255`, segmented-wide
  row checks through span `64`, the legal metric matrix, and many downloaded row-count
  cases are fixture-backed. The span `0x0100..0x020d` printable handoff is now
  classified as an 8-bit source-record producer boundary whose wrapped cases select
  non-helper mode-0 row-copy entries. Remaining renderer risk starts only when a byte
  stream changes a named field in [Selected-Font Residual Routing
  Checkpoint](font-context-metrics.md#selected-font-residual-routing-checkpoint), helper
  dispatch, or object shape.

Fixture evidence:

- `parsed primary built-in font selection feeds visible page-record rows`
- `parsed secondary built-in font selection feeds visible SO page-record rows`
- `non-Roman symbol streams select visible built-ins`
- `real final-@ default-table streams select visible built-ins`
- `font-ID built-in selection feeds visible page-record rows`
- `font-ID primary inline/downloaded selection feeds visible page-record rows`
- `font-ID inline/downloaded selection feeds visible page-record rows`
- `font-ID non-selected exits keep prior visible rows`
- `font-ID secondary non-selected exits keep prior SO visible rows`
- `0x13eb8 no-dispatch exits keep prior visible rows`
- `compact text bucket object fixture metadata`
- `compact text bucket object fixture rendered rows`
- `0x1f034 compact text splits current band and fallback rows`
- `host-fetched linear downloaded character stream renders through 0x168dc`
- `host-fetched even-span wide downloaded character renders through 0x1f0d2`
- `host-fetched split-plane segmented downloaded character renders through
  0x1f1f0`
- `0x16498-backed downloaded character object renders segmented-wide compact
  row`
- `0x1f0d2 renders wide inline compact payload row`
- `0x1f1f0 renders segmented inline compact payload row`
- `0x1f264 renders segmented wide inline compact payload row`
- `downloaded glyph width-span matrix publishes and renders all main helpers`
- `downloaded glyph wide-remainder matrix publishes and renders compact chunks`
- `downloaded glyph width-byte boundary truncates page-record span`
- `downloaded glyph segmented-wide matrix publishes and renders compact chunks`
- `downloaded segmented-wide row-span cross-products render selected segment`
- `downloaded segmented-wide high-row fallback renders selected segment`
- `downloaded segmented-wide high-row even-span fallback renders selected
  segment`
- `downloaded segmented-wide high-row span-31 fallback hits source boundary`
- `downloaded segmented-wide high-row span-32 fallback renders selected segment`
- `downloaded segmented-wide row-0x0182 span-31 fallback hits source boundary`
- `downloaded segmented-wide row-0x0182 fallbacks render selected segment`
- `downloaded segmented-wide row-0x01ff span-31 fallback hits source boundary`
- `downloaded segmented-wide row-0x01ff fallbacks render selected segment`
- `downloaded segmented-wide row-0x0281 span-31 fallback hits source boundary`
- `downloaded segmented-wide row-0x0281 fallbacks render selected segment`
- `downloaded segmented-wide high-row 0x02xx matrix renders selected segment`
- `downloaded segmented-wide high-row 0x02xx span-31 matrix hits source boundary`
- `downloaded segmented-wide high-row 0x03xx matrix renders selected segment`
- `downloaded segmented-wide high-row 0x03xx span-31 matrix hits source boundary`
- `downloaded segmented-wide high-row 0x04xx matrix renders selected segment`
- `downloaded segmented-wide high-row 0x04xx oversized payload counts stop before
  renderer`
- `downloaded segmented-wide row-byte boundary truncates page-record segments`
- `downloaded glyph row-count matrix publishes and renders additional
  short/segmented counts`
- `host-fetched rows-0x102 downloaded glyph FF publication truncates
  page-record rows`

Disassembly evidence:

- `generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst`:
  `0x1f024..0x1f3d2`, including compact dispatch, `0x1f08e`, `0x1f1ac`,
  `0x1f354`, and wide-mode cache writes.
- `generated/disasm/ic30_ic13_bitmap_row_copy_tables_01fa5c.lst`:
  `0x1fa5c..0x2feb0`, including row-count jump tables and unrolled A1/A2/A3
  copy tails.
- `generated/analysis/ic30_ic13_render_row_copy_fixtures.md`: decoded
  width-table, remainder-table, multi-row, and A2/A3 write traces.
- [font-context-metrics.md](font-context-metrics.md): parser-produced
  built-in and resource-context metric fixtures.
- [semantic-state-model.md](semantic-state-model.md), `Descriptor Metric
  Semantic Checkpoint`: field grouping and writers/readers for
  `0x16fae..0x1719c` descriptor metrics through `0xd4ac` / `0xd8fc`.
- [downloaded-fonts.md](downloaded-fonts.md): parser-produced downloaded
  glyph installs, publications, and compact render fixtures.

Unresolved middle edges:

- `0x14c64..0x1f354`: primary/secondary built-in selection, symbol-miss
  fallback, non-Roman `0N` / `10U` / `11U`, real final-`@` defaults, final-`X`
  built-in and inline/downloaded success, final-`X` non-selected exits, and
  `0x13eb8` no-dispatch exits are page-visible through compact rendering.
  Remaining ROM-internal work starts only when a command combination changes
  selected context records `0x782ee6/0x782ef6`, active maps
  `0x782f32/0x783032`, page-root context slots `+0x2c..+0x68`, compact source
  fields produced by `0x1393a`, or helper inputs consumed by `0x1f354` before
  row-copy dispatch.
- `0x16498..0x1f354`: normal, wide, segmented, split-plane, segmented-wide, partial,
  no-install, row-count boundary, main width-span, and compact-wide remainder cases are
  documented; the segmented-wide matrix now covers spans `17..32` at rows `0x81`.
  High-span probes now carry compact-wide spans `33`, `48`, `49`, `64`, and `255` plus
  segmented-wide spans `33`, `48`, `49`, and `64` through
  parser/install/publication/dispatch metadata and documented row-construction inputs.
  Fixture `downloaded segmented-wide row-span cross-products render selected segment`
  covers segmented-wide rows `0x0082` and `0x0083` crossed with spans `17`, `18`, `31`,
  and `32` through selected segment rows. Fixture `downloaded glyph width-byte boundary
  truncates page-record span` now classifies descriptor-accepted spans `0x00ff`, every
  wrapped low-byte span `0x0100..0x0111`, and high siblings through `0x020d` at the
  current printable handoff: canonical installed width words survive, but `0x12f2e`
  consumes only the low source byte. Source width bytes `0x00..0x10` queue selector
  `0x0003` and read compact mode-0 helper entries outside decoded row-copy helper heads,
  with exact target classes now recorded by the fixture; source width bytes `0x11..0xff`
  queue selector `0x1003` and stay on compact-wide `0x1f0d2`. Fixture `downloaded
  segmented-wide row-byte boundary truncates page-record segments` now classifies the
  sampled row side: row words `0x0100`, `0x0101`, and `0x0181` survive in the installed
  glyph, but the current source row byte causes selector `0x1003`, `0x1003`, and
  `0x3003` with only segments `1` and `0`; the first render splits for those sampled
  rows are also documented. The high-row fallback fixtures now extend that
  selected-segment render evidence across installed row words `0x0181`, `0x0182`,
  `0x01ff`, `0x0281`, `0x0282`, `0x02ff`, `0x0381`, `0x0382`, `0x03ff`, `0x0481`,
  `0x0482`, `0x04ff`, `0x0581`, `0x0582`, `0x05ff`, `0x0681`, `0x0682`, `0x06ff`,
  `0x0781`, `0x0782`, and `0x0787`: spans `17`, `18`, and `32` through `0x03ff`, spans
  `17`, `18`, and `24` for `0x04xx`, spans `17`, `18`, and `23` for `0x0581`/`0x0582`,
  spans `17`, `18`, and `21` for `0x05ff`, spans `17`, `18`, and `19` for
  `0x0681`/`0x0682`, spans `17` and `18` for `0x06ff`, and span `17` for `0x0781`,
  `0x0782`, and `0x0787` render bucket-8 segment `1` as `32` current rows and `96`
  fallback rows derived from the installed bitmap. The span-31 siblings through `0x03ff`
  are explicit A2 source boundaries at `+0xb50`; higher oversized siblings stop at the
  parser payload-count cap before renderer entry, including `0x0788*17`. Remaining
  renderer work starts only when byte streams change boundary object fields, helper
  dispatch, or a selected-font/source/page/render field named in [Selected-Font Residual
  Routing
  Checkpoint](font-context-metrics.md#selected-font-residual-routing-checkpoint).
- `0x1fa5c..0x2feb0`: all sixteen main `0x1f08e` helper indexes now have
  parser-produced downloaded-glyph page rows, and compact-wide spans `17..32`
  plus segmented-wide spans `17..32` now cover selectors `0x1003` and
  `0x3003`, `0x2f27c`, remainders `1..15`, and their no-remainder two-chunk
  siblings. High-span probes now cover additional full-chunk counts through
  `0x2f27c`, A2/A3 source-walk rows, and documented row output above span
  `32`.
  The downloaded-glyph row-count checkpoint now narrows helper risk further:
  rows `0x0001..0x00ff` are published and rendered for the documented
  short/segmented family, and segmented-wide high-row below-cap cases are
  semantic cross-products of preserved 16-bit row words, low-byte selector
  truncation, span-selected helper choice, and parser payload-count cap. The
  exact ROM-local visible-output boundary is the unchecked `0x1fe76`
  row-count table read above valid index `128`, where `0x1fe8a + 4 * D3`
  enters row-copy code bytes beginning at `0x2008e`. Remaining ROM-local work
  is new streams that change helper dispatch or rows, not the main helper
  aliases or sampled matched wide paths.
- `0x1f414..0x7810b4`: current-band/fallback splitting is documented with
  fixture checks, including the row-`0x0102` invalid fallback boundary;
  device-level behavior after such invalid table targets is intentionally not
  claimed.

The executable harness `tools/render_fixture_harness.py` combines the
host-byte fetch, tokenizer/delayed-payload, page-geometry,
macro/data-chain, direct-control, reset, text, rule, raster, bridge,
row-copy, built-in glyph, symbol-set, and downloaded-font fixture
families into one ROM-backed self-test. It emits
`generated/analysis/ic30_ic13_renderer_fixture_harness.md` and currently
verifies 371 checks. The raster coverage now includes ROM-table
`0x11774` dispatch traces for the primary `ESC *t300R` / `ESC *r1A` /
`ESC *b4W` stream, the 150/100/75-dpi mode streams, the consecutive-row
`ESC *b2W` stream, the active-resolution-ignore `ESC *t75R` stream, the
end-raster `ESC *rB` / re-enabled `ESC *t150R` stream, the chained
`ESC *t300r150R` resolution stream, and the chained `ESC *b2w2W`
delayed-transfer stream, modeled delayed `0x121cc` / `0x12218` transfer
records, command/data-stream transfer events routed through the modeled
`0x105d0` gate including capped-byte, inclusive page-extent
queue-and-advance, beyond-extent drain/no-row-advance, negative-row
drain-with-advance, and host-fetched `0xdace` control-byte normalization
cases before queueing, page-record queue/bridge/render checks for modes
0..3, render-band setup coverage for `0x1ef86`, render-entry call-order
coverage for `0x1ef6a`, published-record render-entry coverage through
`0x1ed84`/`0x1ef6a`, bucket-chain dispatcher coverage for `0x1efc2`,
segment-list rendering coverage for `0x1f812`, fixed-width list coverage
for `0x1f756`, and raster object rendering through `0x13070` / `0x13250`
/ `0x138de` / `0x1edc6` / `0x1f88e`. The primary 300-dpi raster stream
has a cross-boundary check tying the ROM parser handlers and `0x12218`
restore to the modeled payload offset, `0x10084` page-root allocation,
queued object, bridge, ROM-derived row, and row counter, and now also ties
the same bytes fetched through the modeled `0xa904` ring source to the
queued object, `0x1edc6` bucket-root bridge fields, empty rule/fixed
lists, and row-construction input; the 150/100/75-dpi streams now start from the
modeled `0xa904` ring source and tie the same parser handlers, restored
`0x105d0` records, payload offsets, queued objects, and rendered
expansion rows to modes 1/2/3; the `ESC *t300R` / `ESC *r0A` /
`ESC *b4W` edge stream now starts from the modeled `0xa904` ring source
and ties the parser/restore path to capped queueing, inclusive
page-extent queue-and-advance, beyond-extent drain/no-row-advance, and
negative-row drain-with-advance transfer-gate outcomes; the
payload-control stream now starts from the modeled `0xa904` ring source
and checks that raw payload `f0 1a 58 aa 55` queues as `f0 00 aa 55`; the
consecutive-row `ESC *b2W` stream now starts from the modeled `0xa904`
ring source and ties two restored `80 57 00 02 00 00` records to payload
offsets `17` and `24`, queued coords `0x0000` and `0x1000`, and final
row_y `2`; the multi-row and chained-transfer host-fetched streams now
also pin the `0x1edc6` bridge contract and feed their active raster
bucket chains through `0x1ed84` and `0x1ef6a`; the active-resolution
stream now starts from the modeled `0xa904` ring source and ties an
in-raster `ESC *t75R` handler `0x10808` to preserved mode 0/scale 1
state before queueing the next row; the
end-raster stream now starts from the modeled `0xa904` ring source and
ties `ESC *rB` handler `0x107fa` to active-clear state before
`ESC *t150R` updates mode/scale again; the chained-resolution
`ESC *t300r150R` stream now starts from the modeled `0xa904` ring
source, keeps the ROM parser in the `*t` family after lowercase `r`, and
exits at uppercase `R`; and the chained `ESC *b2w2W` stream now starts
from the modeled `0xa904` ring source and checks that uppercase `W` restores
the lowercase `80 77 00 02 00 00` delayed record before consuming the
payload. Symbol-set coverage now traces `ESC (2U` / `ESC )0E` through
ROM parser setup handlers `0x1201e` / `0x12008` and terminal handler
`0x120be` before the modeled `0x1be22` / `0xc580` active-word refresh
and `0x14f16` map patching, separately traces `ESC (7X` plus `ESC )0@` /
`ESC (1@` / `ESC )2@` / `ESC (3@` / `ESC )3@` through that same parser
terminal path before checking the `X` font-ID and `@0..@3` model
targets, now pins `0x1ac0a`/`0x1af36` default/fallback table-builder
writes that feed `@0`, `@1`, `@3`, and `0x156de` fallback selection, and
now pins `0x1ad66` range-1/range-2/`0x1ae7e` fallback candidate-search
control flow. Downloaded-font coverage now includes an `ESC )s80W`
ROM-parser-traced payload boundary through restored `0x16c14`, `0x16fae`
validation, `0x17026`/`0x1719c` allocation, and `0x1bc38` candidate
insertion before the existing `0x14c64` bit-30 resource dispatch, and
now starts that complete command/payload stream from the modeled
`0xa904` ring source, plus the `ESC )s2193W` character-object boundary
through `0x16498`. The `ESC )s2193W` case also starts from the modeled
`0xa904` ring source, drains the complete command/payload stream,
replays the same parser handlers, restores the same delayed record, and
renders the same compact object rows. Rectangle coverage now also has a
ROM-table `0x11774` dispatch trace for `ESC *c12a5b0P`, proving the
parser selects `0x10e68`, `0x10e22`, and `0x10898` before queueing and
rendering the selector-7 rule object. That same rectangle stream now
starts from the modeled `0xa904` ring source and pins the `0x1edc6`
rule-list bridge contract, then feeds the parser-derived rule record
through `0x1ed84` and `0x1ef6a` before solid rendering. It also has a
parser-to-retry boundary for that same stream: the `0x10d22` no-room
path publishes an existing compact text bucket through `0xff1e`,
allocates a fresh root through `0x10084`, retries the selector-7 rule
object, bridges it through `0x1edc6`, and renders the retried rule rows.
Page-root allocation and publication are the source-side half of the render
handoff. `0x10084` / `0x10110` allocate the first root, bootstrap the selected
context slot, and write geometry fields `+0x06`, `+0x09`, and `+0x16`;
`0xff1e` accepts only an active root whose byte `+0x04` is `1`, copies
status/environment bytes into the root header, writes publication state
`+0x04 = 2`, links the source through protected pool head `0x780ea6`, sets
publication flag `0x782996`, and clears current root `0x78297a`. The scheduler
later promotes that published record to active source `0x780eae`.

Page-record bridge `0x1ed84 -> 0x1edc6` is the render-side handoff.
`0x1ed84` copies active source words `+0x18` and `+0x1a` into the selected
render work record, initializes work words `+0x0a`, `+0x0c`, `+0x10`, and
`+0x16`, clears throttle word `+0x0e`, then calls `0x1edc6`. The bridge copies
source bucket root `+0x1c` to render `+0x18`, source rule-list root `+0x24` to
render `+0x1c`, source fixed-list root `+0x28` to render `+0x20`, and source
context slots `+0x2c..+0x68` to render `+0x24..+0x60`. Evidence anchors:
`generated/analysis/ic30_ic13_page_root_allocation.md`,
`generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`, and
`generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`.

Direct plain text coverage now traces `!!` through two
`0xd04a` parser events and ties that stream to one page-record root
allocation, bucket-0 reuse, and real-HMI rows rendered after the
`0x1edc6` bridge. The `!\x0e!\x0f!` stream now carries normal-mode
SO/SI through `0xc6b8` and `0xc68a`: SO switches `0x782f06` to context
slot `1`, SI switches it back to slot `0`, and the resulting bucket
chain renders selector-1 and selector-0 compact objects through
`0x1ed84`/`0x1ef6a`. Direct mixed text/control coverage now also feeds
`ESC &k1G!\r!` through the modeled `0xa904` ring source before tracing
parser handlers `0xedf8`, `0xd04a`, `0xf02c`, and `0xd04a`, then ties
that same fetched stream to one page-record root allocation, bucket-0
reuse, and rows rendered after the `0x1edc6` bridge; `ESC &k2G!\n!`
routes line-termination handler `0xedf8`, LF handler `0xf08c`, and the
two printable bytes through `0xd04a`, proving mode `0x60` applies CR+LF
before the second glyph queues at compact coord `0x3b00`,
`ESC &k6H!!` routes HMI handler `0xca8c` into the page-record path,
stores packed advance `15`, and renders the two following printable
bytes at compact coords `0x0600` and `0x0501`, `ESC &k0G HT BS !`
routes line-termination handler `0xedf8`, HT handler `0xf1cc`, and BS
handler `0xf2a8` into the page-record path and renders after queueing
through `0xd04a` at compact coord `0x0a01` / pixel x `26`,
`ESC &a1L!` now routes left-margin handler `0xeb58` into the same
page-record path and renders the shifted glyph at compact coord `0x0801`
/ pixel x `24`, `ESC &a1M!` routes right-margin handler `0xec0c` into
the page-record path and renders after right-margin cursor movement at
compact coord `0x0a02` / pixel x `42`, `ESC &a6l9M!` routes
lowercase-final margin handler `0xeb58`, keeps parser mode `12` for
right-margin handler `0xec0c`, and renders after queueing through
`0xd04a` at compact coord `0x0207` / pixel x `114`, `ESC &a2C!` and
`ESC &a1R!` route cursor-position handlers `0xf39e` and `0xf560` into
the page-record path and render shifted glyphs at compact coords
`0x0a02` / pixel x `42` and `0x1001` / bucket `4`, `ESC &a72H!` routes
horizontal-decipoint handler `0xf416` into the page-record path and
renders after decipoint cursor conversion at compact coord `0x0402` /
pixel x `36`, `ESC &a72V!` routes vertical-decipoint handler `0xf60a`
into the page-record path and renders after decipoint cursor conversion
at compact coord `0x9001` / bucket `0` with nine blank rows first,
`ESC *p30x30Y!` routes lowercase-final horizontal dot-position handler
`0xf48c`, keeps parser mode `18` for vertical dot-position handler
`0xf692`, and renders after queueing through `0xd04a` at compact coord
`0x9402` / bucket `0` with nine blank rows first,
`ESC &a2c+1R!` routes lowercase-final horizontal cursor handler
`0xf39e`, keeps parser mode `12` for relative vertical handler `0xf560`,
and renders after queueing through `0xd04a` at compact coord `0x1a02` /
bucket `3`, `ESC &l3E!` routes top-margin handler `0xece2` into the
page-record path and renders the vertically shifted glyph at compact
coord `0x9001` in bucket `6`, `ESC &l1L!` routes perforation-skip
handler `0xee64`, sets byte `0x783191`, and then queues printable `!`
through `0xd04a` at the unchanged compact coord `0x0001`. The pixel-affecting
consumer is later vertical overflow helper `0xf36c`: fixture
`0xf36c perforation skip gates vertical overflow page eject` proves that
`0xf36c` calls `0xf124` and returns `D7 = 0` only when cursor y
`0x782c8e` exceeds nonzero limit/cache `0x782dc2` while `0x783191` is
nonzero; below-limit, zero-limit, and disabled-skip cases continue with
`D7 = 1`.
`ESC &f0S ESC &a2C ESC &f1S!` routes cursor-stack handlers `0xf75e`
around cursor-position handler `0xf39e`, restores the original cursor,
then queues printable `!` through `0xd04a` at compact coord `0x0001`. A
grouped host-fetch direct text/control fixture now starts the plain,
HMI, CR/LF, HT/BS, margin, cursor-position, dot-position,
vertical-layout, perforation-skip, and cursor-stack page-record streams
from the modeled `0xa904` ring source, drains every byte, replays the
same parser handlers, and lands on the same `0x1387c` page-record
objects and rendered row counts; the same grouped check now pins that `0x1edc6`
preserves the bucket root, clears rule/fixed lists, and copies the
selected context slot into the render record. `ESC &p2X!!` now extends
that direct set through transparent print data: handler `0x11f5a`
restores delayed payload handler `0x12452`, consumes the following two
payload bytes through `0xa904`, routes both bytes through `0xd04a`,
queues compact coords `0x0001` and `0x0202`, and renders the same rows
as plain `!!`. `ESC &p4X!\x05\x85!` now covers the default-filtered
transparent control payload path: bytes `0x05` and `0x85` route through
`0xd0f0`, map fixed-space host byte `0x20` to glyph `0x1f`, clear the
glyph pointer before `0xd550`, advance the cursor without queuing text
objects, and leave only the two visible `!` entries at compact coords
`0x0001` and `0x0604`. `ESC &p4X!\x05\x80!` covers the nonzero-filter
control path through `0xd04a`, queueing C0 glyph `0x04` at compact coord
`0x0d01` and high-control glyph `0x7f` at compact coord `0x0003`.
`ESC &p3X!\x05!` covers the default-filtered unflagged fixed-record path:
`0xd0f0` substitutes host `0x20`, queues unflagged glyph `0` at compact coord
`0x4802` between surrounding unflagged `!` coords `0x7601` and `0x7a03`,
bridges context slot `0x00000100`, and renders bucket `1` with digest
`89629435e063529ce7150d603ed9be37a74658317db3e97a4ae01b1c8d64f9d9`.
`ESC &p3X!\x98!` extends that same nonzero-filter path to a taller
high-control glyph: byte `0x98` maps to glyph `0x97`, queues bucket `-1`
coord `0xfd01`, leaves surrounding `!` entries in bucket `0`, and renders
bucket digests
`bd7ad3016d15c1dc2ef12adaeb1091a58f26473c0ecfc7ac13bfaf268c383e90` and
`4bf2f0104b14bfa598b8acfcf8cfb69ccb4419c234f02f256781b6b236110300`.
`SO ESC &p3X!\x80!` composes transparent data with the secondary text context:
SO selects slot `1`, the high-control byte reads context `0xc00ae122`, maps to
glyph `0x5f`, queues segmented selector `0x2001` page-record objects across
`157` segment buckets, bridges slots `(0x440946b4, 0xc00ae122)`, and selected
bucket `0` renders row digest
`57bb3fd895be358ff325e26ae58a3b0dc526c5b08b382eb90e7273e6227fbfbb`.
`ESC &p2X\x1aA!` covers the transparent `1a` probe path by consuming raw
payload `1a 41 21`, routing values `0x41` and `0x21` through `0xd04a`,
and rendering visible `A!`. That direct page-record group now also crosses
`0x1ed84` active-record copy and the `0x1ef6a` render-entry call order,
including nonzero bucket selection for the vertical cursor/layout cases. A
host-fetched `! ESC *c12a5b0P` fixture
now queues compact text and a selector-7 rectangle rule in the same page
record before carrying the combined bucket/rule record through `0x1ed84`
and `0x1ef6a`. The same text/rectangle stream now also has an addressed
allocation variant: printable `!` queues through addressed `0x1387c`, the
chained rectangle queues through addressed `0x133aa`, and the materialized
page record matches the older byte-list bridge/render output. A host-fetched
`! ESC *c12a5b0P ESC *t300R ESC *r0A ESC *b2W` fixture now adds a mode-0
raster row to that combined page-record shape before rendering the
bucket/rule/raster record through the same entry path. Its addressed variant
now allocates the raster row through addressed `0x13070`/`0x13250` storage
after the addressed text and rule objects, preserving the real bucket link
pointer while rendering the same rows; that materialized addressed record now
also publishes through modeled `0xff1e` and renders the published rows through
`0x1ed84`/`0x1ef6a`. Adding FF to the addressed text/rule/raster stream
now drives that same heterogeneous addressed page record through the
publication boundary from the byte stream, clears the current root, and
renders the published rows through `0x1ed84`/`0x1ef6a`.
Direct publication-stream coverage traces `!\x1bE`, `ESC &k2G!\f`,
`!\x1b&l1A`, `!\x1b&l1O`, `!\x1b&l2H`, and `!\x1b&l2X\f` through the ROM
parser path, proving printable fallback to `0xd04a`, reset dispatch to
`0xcc52`, line-termination dispatch to `0xedf8`, FF dispatch to
`0xf0f0`, page-size dispatch to `0xfc74`, orientation dispatch to
`0x10220`, paper-source dispatch to `0xef62`, and copies dispatch to
`0xeef0` before the modeled page-record publication fixtures run. The
publication-boundary fixture ties those same streams to one root
allocation, one `0xff1e` publication, current-root clearing, rendered
rows after `0x1edc6`, and the same rows after the published records pass
through `0x1ed84` and `0x1ef6a`. The paper-source stream also pins
selector `2` to value `0x80`, stores it in `0x782da6`, sets `0x782998`,
and refreshes the cursor through the `0xf8fc` layout path. The copies
stream pins `ESC &l2X` as copy count `2`, stores it in `0x782da4`, and
proves FF publication copies that value to pool-header word `+0x0c`.
The host-fetch publication fixture now starts those same six streams from
the modeled `0xa904` ring source, drains the ring bytes, replays the same
parser handlers, lands on the same published rows, and now pins that the
`0x1edc6` bridge preserves the published bucket root, clears rule/fixed
lists, and copies the selected context slot into the render record. Fixture
`macro overlay cursor-position payload publishes with page rule` carries
`ESC &a2C!` through the overlay replay path: `0xff1e` resolves macro id `130`,
`0xe4f4` builds the non-replay frame, `0x11774` routes `0xf39e` then `0xd04a`,
and the published page record composes coord `0x0a02` compact text with
selector-7 rule `00 00 00 00 01 07 82 02 00 07 00 02 00 00`, rendering digest
`ba32af7d183a956b2abd821b2143e9c7c3eecf87a7b1403fa086cfe6bf89c8ae`. The
fixture `macro overlay chained cursor-position payload publishes with page rule`
carries `ESC &a2c+1R!` through the same overlay path: `0x11774` routes
`0xf39e`, parser-mode continuation bytes, `0xf560`, then `0xd04a`; the
published page record composes coord `0x3a02` compact text with selector-7 rule
`00 00 00 00 01 07 a6 02 00 06 00 02 00 00`, rendering digest
`0275857ffbcc11aa5234644930ebcd31571c2178eaf52b79590989d31b39f653`. The
fixture `macro overlay chained margin payload publishes with page rule` carries
`ESC &a6l9M!` through the same overlay path: `0x11774` routes `0xeb58`, a
mode-12 continuation byte, `0xec0c`, then `0xd04a`; the margin commands write
packed left/right margins `108`/`180`, and the published page record composes
coord `0x0207` compact text with selector-7 rule
`00 00 00 00 01 07 6c 02 00 05 00 02 00 00`, rendering digest
`ecae0043ee656ceba42d4d6e052e3d56a365eeb4a847b3b430f80eed72b5a199`. The
host-fetched
missing-root `ESC E` case drains from the same ring source, reaches
handler `0xcc52`, and lands on the no-publication reset state. The
host-fetched
reset, FF, page-size, orientation, paper-source, and copies cases also pin
the pool header
after `0xff1e`: state byte `+4 = 2`, status/environment fields including
copies word `+0x0c`, published pointer `0x780ea6`, bucket-root prefix,
and context-slot prefix all match the modeled publication records before
the bridge/render path derives ROM-local rows. Macro coverage now has the same ROM-table
proof for
`ESC &f-123y0x1X`, walking modes `0 -> 1 -> 5 -> 17 -> 17 -> 17 -> 0` to
handlers `0xe112`, `0xdd08`, and `0xdd08` before applying the modeled
macro state effects; a second macro-definition trace proves alternate
table `0x116f6` leaves payload bytes unclaimed while still routing
`ESC &f1X` to `0xdd08`, simple execute and call payloads drain through
`0xa904`, route replayed `!\r` through parser handlers `0xd04a` and
`0xf02c`, and feed the same bridged page-record object and rows, and a
stored `ESC &k1G!\r!` macro payload now drains through `0xa904`, routes
replayed bytes through handlers `0xedf8`, `0xd04a`, `0xf02c`, and
`0xd04a`, and feeds the same page-record stream and row-construction inputs as the
direct mixed control-byte model; the execute, call, and mixed-control
replay payloads now also pin the `0x1edc6` bucket/context bridge
contract before rendering. Macro overlay publication is now pinned for a
visible mixed page record as well: selector `4` state leads `0xff1e` to
resolve saved id `0x782a94`, build a non-replay `0xe4f4` frame, re-enter
`0x11774`, queue stored `!\r` into a page record that already contains a
selector-7 rectangle rule, publish through `0xff1e`, and render both
layers through `0x1ed84`/`0x1ef6a`.

The mixed text/rule/raster/FF route is the first complete byte-stream
page-image contract through host fetch, parser handlers, addressed page-record
storage, `0xff1e` publication, `0x1ed84` / `0x1edc6`, and ROM-derived row
construction. The route family has since broadened with font-selection and
downloaded-glyph page-image cases: primary/secondary font-selection streams
render visible compact rows, downloaded-glyph FF publication renders through
`0xff1e` / `0x1ed84` / `0x1ef6a`, and the parser-driven downloaded-glyph
composition route combines an installed downloaded glyph, selector-7 rule, and
mode-0 raster row in one parser-driven page stream. Remaining work should
target byte streams or ROM paths that expose different output state; repeating
the same addressed route with a different proof source is not an unresolved
raster/imaging semantic edge. The separate resource-window decode gap at
`0x0c0000..0x0c0321` is not a blocker for the ROM-local
host-fetch-to-page-image path covered here. The reset, FF, page-size,
orientation, paper-source, and copies publication routes now start without a
current page root and mark the first printable queue step as the modeled
page-record root allocation point. Those six publication paths now also have
addressed variants:
`!\x1bE`, `ESC &k2G!\f`, `!\x1b&l1A`, `!\x1b&l1O`, `!\x1b&l2H`, and
`!\x1b&l2X\f` queue the printable byte through addressed
`0x1387c`/`0x1381c`, materialize the page record, publish through the same
`0xff1e` boundaries, and render through `0x1ed84`/`0x1ef6a` with the same
rows. That closes the software-visible compact-text publication contract while
leaving only provenance and optional physical-output correlation outside the
ROM contract.

The host-fetched text/rule/raster route publishes its full bucket array, rule
list, and context slots through `0xff1e`, then renders the published record
through `0x1ed84` and `0x1ef6a` with the same composed rows. The same stream
runs text, `ESC *c`, and delayed `ESC *b#W` raster transfer through one mixed
page-record runner instead of attaching the raster row after the text/rule
record. Adding FF publishes the heterogeneous page record through `0xff1e` and
renders the published record through `0x1ed84` and `0x1ef6a`; the addressed
text/rule/raster route has the same trailing-FF publication check with the
raster object linked from addressed `0x1381c` storage. The semantic checkpoint
in `notes/semantic-state-model.md` classifies that cluster: canonical
page-record objects are at `0x00d0c004`, `0x00d0c02a`, and `0x00d0c038`;
parser scratch restores raster record `80 57 00 02 00 00` and payload `c3 3c`
at offset `28`; firmware bookkeeping leaves `0x782a70 = 0x00bc`,
`0x782a72 = 0x00d0c000`, and `0x782a76 = 0x00d0c044`; derived render caches
include `0x783a20 = 0x0050`, `0x783a22 = 0`, and `0x783a28 = 0x00100000`.

The same mixed stream cluster has a consecutive-raster-row sibling. Stream
`! ESC *c12a5b0P ESC *t300R ESC *r0A ESC *b2W f0 0f ESC *b2W 0f f0 FF`
publishes bucket `0` as second raster row, first raster row, then compact text,
and renders both encoded-span dispatches before the compact glyph. The
addressed storage form allocates raster objects at `0x00d0d038` and
`0x00d0d044`; the bucket chain is
`0x00d0d044 -> 0x00d0d038 -> 0x00d0d004`; allocator bookkeeping ends at
`0x782a70 = 0x00b0`, `0x782a72 = 0x00d0d000`, and
`0x782a76 = 0x00d0d050`; and the final raster row counter is `2`.
A `0x1ef6a` page-band walker now also merges compact text, mode-0
raster, and a crossing patterned rule across bands `0` and `5`, carrying
the mutated rule node into the second band.
The direct compact text path now includes a mode-0 band split fixture, and
the host-fetched `ESC &a1R!` cursor-row page-record stream carries bucket
word `4` through `0x1ef86`, yielding `0x783a20 = 16`, current-band compact
rows, and fallback continuation rows.
Synthetic inline/downloaded fixtures now also force `0x1f0d2`, `0x1f1f0`,
and `0x1f264` objects to cross row `14` of a 16-row band, pinning their
current-band rows and fallback continuation rows.

Raster coverage now has a named flow report plus ROM-table `0x11774` dispatch
traces for the primary, 150/100/75-dpi, consecutive-row, capped/drained,
active-resolution-ignore, end-raster, and host-fetched chained-lowercase
`ESC *t#R` / `ESC *r#A` / `ESC *b#W` streams. Those command-family semantics
are composed in [raster-graphics.md](raster-graphics.md): lower-resolution
streams now start from modeled `0xa904` host bytes, cross the ROM parser table
and delayed `0x105d0` restore, queue encoded raster modes 1/2/3, then render
through `0x1ed84` / `0x1ef6a`. The dense text/rule/raster stream already has
addressed `0x1381c` page/control storage for the raster object and published
record fields, so the documented raster edge is now closed for those
software-visible fields. Further work belongs on new byte-stream variants,
or resource-window data.
The `0x1f0d2` and `0x1f1f0` inline cases now also have type-2 `0x1719c`
payload-backed fixed-record coverage; the selected inline/downloaded
page-record object now crosses `0x1edc6` with context slot `3` intact
before compact rendering; the `0x1f1f0` downloaded-pointer path has both
even-span `ESC )s258W` and split-plane `ESC )s387W` parser-produced
fixtures; the `0x1f264` segmented-wide case now has selected-memory isolation
plus host-fetched `ESC *c4660d37e5F`, host-fetched `ESC )s0W`, host-fetched
`ESC )s80W`, and host-fetched `ESC )s2193W` parser boundaries, plus a
host-fetched `ESC )s18W`
downloaded-character payload-control stream that normalizes `1a 58`
before wide glyph rendering and now crosses `0x1edc6` plus the
`0x1ed84`/`0x1ef6a` render-entry path before rendering the same wide row.
The clean even-span wide `ESC )s18W` downloaded-character fixture now also
copies 18 linear bytes through `0x168dc` with no payload-control hits, queues
selector `0x1003`, crosses `0x1edc6`, and renders through `0x1f0d2` with one
full 16-byte chunk plus a 2-byte remainder.
That same host-fetched even-span wide glyph now participates in a
heterogeneous page-image composition fixture. Fixture
`host-fetched downloaded glyph composes with rule and raster through 0x1ef6a`
installs glyph `0x29` from `ESC )s18W`, queues it at x `22`, y `80` as bucket
`5` object `00 00 00 00 10 03 00 01 29 06 01...`, adds selector-7 rule object
`00 00 00 00 05 07 08 01 00 0c 00 03 00 00`, and adds mode-0 raster object
`00 00 00 00 80 00 00 02 00 00 c3 3c`. The `0x1ed84`/`0x1ef6a` render entry
dispatches the raster chain item to `0x1f88e`, the downloaded glyph chain item
to `0x1effe`/`0x1f0d2`, renders the bridged rule through selector helper
`0x1f596`, and records the final three ROM-derived composed rows. The remaining
middle edge has now been narrowed by fixture `parser-driven downloaded glyph
rule raster stream composes through 0x1ef6a`: after the same fetched
`ESC )s18W` font-install bytes, page bytes
`ESC *c12a3b0P ) ESC *t300R ESC *r0A ESC *b2W c3 3c` route through parser
handlers `0x10e68`, `0x10e22`, `0x10898`, `0xd04a`, `0x10808`, `0x1075a`, and
`0x11f82`, then delayed `0x105d0` queues the raster object. That fixture
produces the same bucket-5 glyph/raster chain, the same bridged rule list, and
the same `0x1ef6a` rows. The modeled font-install split is now documented as
an exact memory handoff: the page phase consumes
`font_command_final_header`, the final resource image returned by the same
host-fetched `0x16c14` / `0x16498` font-command helper, and the fixture asserts
that image matches the install event header. It pins glyph `0x29`, table entry
`0x00ee` with pointer bytes `00 00 07 80`, record delta `0x0780`, bitmap offset
`0x078c`, record bytes `00 00 00 00 0c 01 00 01 00 90 00 00`, and the 18 copied
bitmap bytes. The residual edge is byte streams that change the byte-`24`
handoff state, installed resource record, following `0x10e68` rectangle
state, or row-construction inputs.
The fetched `ESC )s2193W` downloaded-pointer object
now also crosses `0x1edc6` plus the `0x1ed84`/`0x1ef6a` render-entry
path before rendering the same segmented-wide row. A fetched printable
`%` byte now selects that installed downloaded glyph `0x25`, queues the
two segmented page-record objects through the `0x12f2e`/`0x1387c`
producer shape, and renders the segment-1 bucket through `0x1ed84` /
`0x1ef6a`. A combined fetched stream now drains
`ESC *c4660d37e5F`, the `ESC )s2193W` payload, and printable `%`, carrying
current character `0x25` into the installed glyph before rendering the
same segmented page-record bucket; the same check now pins restored
payload record `80 57 08 91 00 00`, segment objects in buckets `9` and
`1`, the `0x1edc6` bucket-root copy, the `0x1ed84` active-record copy,
and the `0x1ef6a` compact dispatch for segment `1`. Appending FF to that
combined stream now publishes both segmented buckets through `0xff1e`. The
published-record band fixture then walks modeled bucket words `1` and `9`
through `0x1ed84`/`0x1ef6a`, leaves the bucket-1 segment-0 band blank for this
payload, and renders the published downloaded-glyph row from bucket `9`. The
downloaded-glyph scheduler fixture then starts from the `0xff1e`/`0x1ed84`
zero seed for active work word `+0x10`, lets `0x1eba4` produce render-call band
words `0..9`, dispatches only published buckets `1` and `9`, and preserves the
same bucket-9 row. The even-span wide downloaded-glyph sibling now publishes
the host-fetched `ESC )s18W` + printable `)` + FF stream through the same
`0xff1e` boundary: bucket `1` is copied into the published record, rendered
through `0x1ed84`/`0x1ef6a`, dispatched to `0x1effe`, and decoded by
`0x1f0d2` into the same 18-byte row. The payload-control wide sibling now
does the same for `ESC )s18W` + printable `&` + FF after `1a 58`
normalization and mode-byte-`2` record
`00 00 00 00 0c 02 00 01 00 88 00 00`. The normal `ESC )s6W` + `&` + FF and
segmented `ESC )s258W` + `'` + FF siblings now publish through the same
boundary: the normal case copies bucket `1` and renders through `0x1fe76`,
while the segmented case copies buckets `1` and `9` and renders bucket `9`
through `0x1f1f0` from source offset `0x0100`; both pass through `0xff1e`,
`0x1ed84`, `0x1ef6a`, and compact target `0x1effe`. The rows-`0x20` short
sibling `ESC )s64W` + printable `1` + FF also copies bucket `1`; render
bucket word `1` passes through `0x1ed84`, `0x1ef6a`, compact target
`0x1effe`, and `0x1fe76`, producing `38` visible rows from the interior short
row count. The rows-`0x40` short sibling `ESC )s128W` + printable `2` + FF
also copies bucket `1`; render bucket word `1` follows the same path and
produces `64` blank current-band rows because the nonzero glyph row is below
the first band. The rows-`0x82`
segmented sibling `ESC )s260W` + printable `0` + FF also copies buckets `1`
and `9`; render bucket word `9` passes through `0x1ed84`, `0x1ef6a`, compact
target `0x1effe`, and `0x1f1f0`, producing two segment-1 rows from the
interior segmented row count. The downloaded-glyph row-count matrix adds
short rows `0x01`, `0x02`, `0x04`, `0x08`, `0x41`, and `0x7f` on selector
`0x0003`/bucket `1`, plus segmented rows `0x83`, `0x84`, `0x85`, `0xc0`,
`0xfd`, `0xfe`, and `0xff` on selector `0x2003`/buckets `1` and `9`, all
through printable+FF publication and `0x1ed84`/`0x1ef6a`; rendered row counts
are `7`, `8`, `10`, `14`, `64`, `64`, `9`, `10`, `11`, `16`, `16`, `16`, and
`16`. The
rows-`0x0102` sibling `ESC )s516W` +
printable `3` + FF also crosses `0xff1e`, but the page-record source exposes
row byte `0x02`; it publishes selector `0x0003` bucket `1` only, then
  `0x1f414` splits rows `0x0102` into `58` current rows and `200` fallback rows.
  The fallback exceeds `0x1fe76`'s valid table maximum index `128`: entry
  `128` at `0x2008a` is the last valid pointer, entry `129` begins reading
  row-copy code at `0x2008e`, and fallback index `200` reads target
  `0x329ad3c0`. The fetched
font-control
state now carries current id
`0x1234` and current character `0x25` into fetched descriptor,
resource-payload, and downloaded-character streams, tying delayed record
restoration through `0x121cc` / `0x12218`, descriptor or payload
offsets/lengths, `0x15d0a` current/continuation descriptor routes,
`0x16fae`/`0x1719c` resource-payload allocation and replacement
bookkeeping, `0x16498` downloaded-pointer allocation, and the rendered
segmented-wide row. The full built-in scan proves the verified ROM
resources do not contain a normal wide or non-mode-1 bitmap-entry case.

That combined downloaded-glyph stream is now a first-class boundary in
the harness report rather than only a split family of fixtures. The
single modeled `0xa904` ring stream is 2,215 bytes: control bytes
`0..14`, downloaded-character payload bytes `14..2214`, and printable
byte `2214..2215`. It routes the control phase through handlers
`0x11eb6`, `0x11ec8`, `0x11eda`, `0x15a56`, `0x15a18`, and `0x16df6`;
routes the payload phase through `0x11eb6`, `0x12008`, `0x11ff6`, and
`0x11f96`; and routes printable `%` through `0xd04a`. The resulting
page object has selector `0x3003`, coord `0x6601`, glyph `0x25`, rows
`0x0081`, width `0x11`, segment-1 object prefix
`00 00 00 00 30 03 00 01 25 01 66 01`, and segment-0 object prefix
`00 00 00 00 30 03 00 01 25 00 66 01`. Both the `0x1edc6` bucket copy
and render-record bucket root preserve the segment-1 object before
`0x1ef6a` dispatches compact target `0x1effe`.

## Rejected Compositor Lead

The `0x78287c` / `0x7827b8` / `0x7828a8` path is not the page-object
compositor. It is a font/resource candidate selector.

Why this lead is rejected for raster/page imaging:

- `0x1a2e4` initializes candidate-list counts `0x782790..0x78279e` and
  candidate-list pointers `0x7827a0..0x7827b4`.
- `0x1a616` scans resource address ranges and looks for resource records
  such as `HEAD`, `FONT`, `TABL`, `tabl`, and `DUMY`.
- `0x1a9be` classifies font resources and updates the candidate-list
  counts/pointers.
- `0x1569c` copies one font candidate-list pointer/count pair into
  `0x78287c` / `0x7827b8`.
- `0x14398`, `0x1440c`, and `0x14c64` select and snapshot current
  font-resource candidates, updating font range/state tables around
  `0x783132..0x78313c`.

This path is still important for text rendering and built-in font
selection, but it does not consume the page-root raster/rectangle queues
described above.

Other checked leads:

- `ESC E` reaches page imaging through reset helper `0xcc70`, documented
  in `generated/analysis/ic30_ic13_esc_e_reset_flow.md`: it calls text
  flush helper `0xf34a`, page-root finalizer `0xff1e`, and active record
  wait helper `0x9ac2` before resetting environment/raster/parser state.
  This makes software reset a page boundary that can finalize a partial
  page before clearing `0x78297a`.
- Reset helper `0xcda2` now names the page/control pool setup before new
  page objects are queued: four 0x6c-byte records rooted at `0x780f02`
  get bucket-array backings at `0x7810bc + 0x400*n`, while parser
  scratch, cursor stack, line-termination mode, HMI `0x78315c`, and VMI
  `0x783160` are restored from current-font/default state.
- `0xff1e` finalizes or resets the current page root as decoded in
  `generated/analysis/ic30_ic13_page_root_finalization.md`: active roots
  with byte `+4 == 1` can be promoted to state `2`, copied through their
  backing pool record to `0x780ea6`, marked with publication flag
  `0x782996`, and cleared from `0x78297a`; missing or inactive roots
  only clear the current-root pointer. The executable model now
  snapshots the finalized pool-record header fields and queue/context
  roots, but `0xff1e` itself does not walk queue roots `+0x1c`, `+0x24`,
  or `+0x28`.
- Direct `0x78297a` references are now indexed in
  `generated/analysis/ic30_ic13_page_root_references.md`;
  `generated/analysis/ic30_ic13_page_root_allocation.md` decodes the
  `0x10084` first-root allocation contract, and
  `generated/analysis/ic30_ic13_page_root_finalization.md` decodes the
  `0xff1e` publication contract. The known direct references resolve to
  page-object producers, page-root initialization/finalization,
  font-slot handling at root `+0x2c`, or pool management. The bridge to
  rendering is instead through page/control records copied by `0x1edc6`;
  `generated/analysis/ic30_ic13_page_record_bridge.md` decodes the
  queue/list/context-slot copy contract.
- The later `0x196c4` lead scans page-root `+0x2c` font slots by masked
  low-24-bit resource/context value and live flags `0x78297f+n`, then calls
  `0x1ba6c` only for a live match. `0x1ba6c` flushes text, finalizes the
  current root through `0xff1e`, refreshes page/font state through
  `0xf8fc`, flushes again, and waits through `0x9ac2`. Missing root or no
  live match waits through `0x9ac2` without publication. It is not a
  bucket-chain consumer.
- `0x780ea6` and nearby aliases are the fixed 0x6c-byte page/control
  record pool used by allocator `0x9a9a`. They are not independent final
  image buffers.

## Next Targets

Use this section as render-documentation guidance, not as a request for more
standalone fixture output. A new render/imaging slice belongs here only when
the checked-in owner note can state the producer handler, page-root object
fields, publication/bridge roots, render helper, row-store primitive, state
classification, disassembly evidence, and exact residual boundary. The compact
handoff after a render helper is [Row-Store Primitive
Map](#row-store-primitive-map): if a new stream reaches the same object fields,
destination helper, row-copy table, fallback split, and row-store operation as
an existing row, it should be treated as the same documented semantic path.

- Keep downloaded-font work focused on byte streams that change installed
  records, source/page objects, bridge state, or ROM-derived row-construction
  inputs, not selector-family rediscovery. Fixtures
  `combined host-fetched font download stream prints
  installed glyph` and `combined font download FF publishes installed glyph
  page record` already run one `0xa904` fetched stream through font-control
  state, `ESC )s2193W` downloaded-character install, printable `%`, FF
  publication, bucket entries `1` and `9`, and `0x1ed84`/`0x1ef6a` rendering.
  Fixture `parser-driven downloaded glyph rule raster stream composes through
  0x1ef6a` closes the page-stream side for the even-span rule/raster case and now
  consumes `font_command_final_header` from the same host-fetched font-command
  helper as the page memory image. The byte-source, post-install return, and
  modeled memory handoff are no longer the open parts: the same fixture checks
  one 54-byte `0xa904` ring fetch, asserts the final-header table pointer
  `00 00 07 80`, installed record, and bitmap bytes, and disassembly plus
  fixture evidence pins the shared `0x15dc6 -> 0x16498 -> 0x15dcc -> 0x12328`
  drain. The
  byte-`24` boundary is no longer a ROM-semantic gap for the covered
  rule/raster stream. Broader physical/full-page validation remains separate.
- Treat the `ESC E` reset publication boundary as covered for
  parser-produced compact text page objects. Fixtures
  `mixed printable/reset page-record stream queues through 0x1387c before
  reset`, `mixed printable/reset page-record finalization publishes bridged
  record`, and `addressed printable reset publishes rendered page record`
  now start from `! ESC E`, allocate/materialize the compact bucket through
  the page-record path, publish through `0xff1e`, clear the current page
  root, and render through `0x1ed84`/`0x1ef6a`. Remaining reset work is
  additional reset byte streams that expose new publication fields or
  ROM-derived pixel output. It is not the software-visible reset-to-render
  contract for this compact-text case.
- Treat the direct-control command family as composed from host fetch to
  ROM-derived row construction for the currently named cursor/layout variants.
  The `Text Cursor And Direct Control State` checkpoint in
  `notes/semantic-state-model.md` groups canonical cursor state
  `0x782c8a` / `0x782c8e`, margins, HMI, VMI, page limits, control
  modes, parser scratch `0x78299e`, derived compact coordinates, and
  render-entry caches. Fixtures `host-fetched direct text/control streams
  reach page-record render`, `host-fetched direct text/control streams
  preserve 0x1edc6 bridge contract`, and `host-fetched direct
  text/control streams feed 0x1ed84 and 0x1ef6a` now start those streams
  at `0xa904`, replay the ROM parser handlers, queue compact page-record
  objects through `0x1387c`, bridge through `0x1edc6`, and render through
  `0x1ed84` / `0x1ef6a`. Remaining work is additional cursor-state
  cross-products that produce new `0xd04a` source-object fields, `0x12f2e`
  bucket shapes, or ROM-derived row-construction inputs, not the
  command-family parser-to-render boundary.
- Treat selector-7 rectangle/rule composition as covered for mixed
  text/rule/raster page records, and the non-solid selector matrix as covered
  for text/rule page records:
  `notes/rectangle-graphics.md` now cites
  `host-fetched text plus rectangle page record feeds 0x1ed84 and 0x1ef6a`,
  `host-fetched alternate rectangle selectors feed full page records`,
  `host-fetched rectangle selector matrix feeds full page records`,
  `host-fetched text rectangle raster FF publishes rendered page record`, and
  `addressed text/rule/raster field groups reach publication and render
  entry`; the same mixed cluster now also includes
  `host-fetched text rectangle multi-row raster FF publishes rendered page
  record` and
  `addressed text/rule/multi-row raster publication preserves bucket
  chain`. Remaining rectangle work is cross-feature full-page combinations
  only when they expose new ROM-derived page-object or row behavior.
- Physical engine/self-test placement, if available, is optional correlation
  against the documented ROM/manual logical page and printable-area dimensions;
  it is not an oracle for rendered rows.
