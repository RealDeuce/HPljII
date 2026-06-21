# Page Geometry and Raster Imaging Notes

Sources: `generated/analysis/ic30_ic13_page_geometry_tables.md`;
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
`generated/disasm/ic30_ic13_page_size_handler_00fc74.lst`;
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

These notes track firmware behavior that directly affects page pixels.
Names are provisional where the ROM state variables are not fully
cross-referenced yet.

## Page Size Tables

The page-size command handler `ESC &l#A` at `0x00fc74` maps PCL
page-size parameters into internal page codes, stores the code at
`0x782da2`, then rebuilds page geometry.

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

`tools/render_fixture_harness.py` now has executable page-geometry
fixtures for the `0x9d16`/`0x9d4e`/`0x9d86`/`0x9dbe` masked table
lookups, `ESC &l#A` page-size mapping, and `ESC &l#O` orientation
recomputation. The `ESC &l1A` fixture pins internal code `6`, width
`3030`, height `2025`, portrait margin `3150`, top offset `90`, and
printable extent `3090`; the PCL `80` fixture pins internal code `0x88`
masking to table index `8`; and a chained byte-stream fixture drives
`ESC &l1a1O` through handlers `0xfc74` and `0x10220`. A mixed
printable/page-size fixture now drives `!` followed by `ESC &l1A`,
allocates the page-record root on the printable queue step, publishes
the queued compact text bucket through the handler's `0xf34a`/`0xff1e`
boundary, then bridges and renders the published record before the new
geometry takes effect. The matching mixed printable/orientation fixture
starts from letter portrait, drives `!` followed by `ESC &l1O`,
allocates the page-record root on the printable queue step, publishes
the queued bucket at the `0x10220` handler's `0xf34a`/`0xff1e` boundary,
then verifies the published bridge renders before landscape geometry
takes effect.

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

The executable `ESC &l1O` fixture starts from letter portrait, changes
orientation to landscape, and pins active extents `2025x3030`, landscape
margin `2175`, printable extent `2125`, top offset `100`, and the
`0x103ea` landscape threshold sequence `2175, 2550, 2480, 2550`.

The coordinate helper group at `0x0104d8..0x010550` converts between
whole coordinates and a packed fixed-point form with 12 subunits per
whole unit. `0x10518` adds signed whole/fraction pairs and clamps the
whole part to `0x7ffe`.

## Raster Graphics State

Raster-related PCL handlers:

| Command | Handler | Current role |
| --- | --- | --- |
| `ESC *t#R` | `0x010808` | raster resolution |
| `ESC *r#A` | `0x01075a` | start raster graphics |
| `ESC *r#B` | `0x0107fa` | end raster graphics |
| `ESC *b#W` | `0x011f82` -> `0x0105d0` | transfer raster row bytes |

`generated/analysis/ic30_ic13_raster_graphics_flow.md` collects the
command edge, delayed `0x121cc` / `0x12218` payload handoff, page-root
queueing through `0x10084` / `0x13070` / `0x13250`, payload copy through
`0x138de`, and render dispatch through `0x1edc6` / `0x1efc2` /
`0x1f88e`.

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
and calls the saved handler when the data is ready. The executable
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
extent drains the full parsed byte count without queueing, a negative
row drains the full parsed byte count without queueing, and a byte count
larger than raster field `+0x10` ensures the modeled page root through
`0x10084`, stores the capped count in `+4` and the overflow count in
`+6`, then queues only the capped bytes. The parser-restored `ESC *b4W`
stream now also proves the off-page row-counter distinction:
`row_y == page_extent` queues and advances to `page_extent + 1`,
beyond-extent rows do not advance `row_y`, and a negative row drains the
payload and advances `row_y` from `-1` to `0`.

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
| `+0x2c..+0x68` | 16 current-font context record slots |

The current-font context slots are copied from the `0x782ee6` /
`0x782ef6` family.

`0x132b6` and `0x1381c` implement a small stream allocator over
0x100-byte chunks:

- `0x782a70`: bytes remaining in the current chunk.
- `0x782a72`: pointer to the link field of the current chunk.
- `0x782a76`: next free byte in the current chunk.
- new chunks are allocated via `0x1710` and chained through their first
  longword, leaving `0xfc` payload bytes.

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
| `+0x2c..+0x68` | `+0x24..+0x60` | 16 current-font context record pointers |

After copying, `0x1edc6` normalizes objects in the destination lists: it
sets flag bit `0x10` in object byte `+5`; for the `dest+0x1c` list it
copies word `+0x0a` to `+0x0c`; for the `dest+0x20` list it copies word
`+8` to `+0x0a` and sets bytes `+0x0c=1`, `+0x0d=8`.

`generated/analysis/ic30_ic13_font_context_bridge.md` refines the
`+0x2c` interpretation: `0xc428` / `0xc4fc` install pointers to
current-font context records in these 16 page-root slots, not raw glyph
pointers. `0x1edc6` copies them to render-record slots, and compact
text/glyph objects use byte `+5` low nibble to select one of the copied
render-record slots before `0x1f008` loads it into `0x783a2c`.

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

The executable render-band setup coverage now pins `0x1ef86`: it divides
`(render word +0x10 + word +0x08 - word +0x0a)` by word `+0x06`, stores
the remainder in `0x783a22`, stores `(word +0x06 - remainder) << 4` in
`0x783a20`, and stores `long +0x00 + ((remainder << 6) * word +0x04)` in
both `0x783a28` and render-record long `+0x12`.

The executable `0x1ef6a` coverage now feeds one synthetic render record
through that entry sequence, with compact text and encoded raster bucket
objects selected from render-record `+0x18`, a selector-7 rule list from
`+0x1c`, and a fixed-width list from `+0x20`. It verifies the firmware
call order (`0x1ef86`, `0x1efc2`, `0x1f446`, `0x1f756`) and composes
those layers without claiming the full parser-produced page-root merge
is decoded.

Published-record coverage now also takes the reset, FF, page-size, and
orientation `0xff1e` records from the host-fetched publication fixtures
through `0x1ed84` and the same `0x1ef6a` call order, proving those byte
streams reach the compact bucket renderer without hand-built
render-record layers.

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

### Object Class Dispatch

The bucket-chain dispatcher at `0x1efc2` walks render-record `+0x18`,
which is the page/control bucket array copied from source offset
`+0x1c`. For each bucket object, it advances `A1` to object offset `+4`,
masks object byte `+4` with `0xc0`, and uses the result as the first
class split:

- `0x00..0x3f`
  - Render path: compact branch `0x1effe`; table `0x1f024` selected by
    byte `+4` bits `0x10/0x20`
  - Current producer mapping: text/glyph bucket objects from `0x12f2e` /
    `0x1387c`
- `0x40..0x7f`
  - Render path: segment-list writer `0x1f812` / `0x1f862`
  - Current producer mapping: producer not yet pinned down
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

The executable segment-list coverage now pins the `0x1f812` object
layout for the `0x40..0x7f` bucket class: word `+0x06` is an entry
count; each six-byte entry supplies a coordinate word, a low-nibble row
count, one skipped byte, and a width/mask word. Helper `0x1f836` maps
the width low nibble through ROM table `0x308f2`, then `0x1f862` writes
full `0xffff` words plus the trailing mask for each row.

The executable fixed-width list coverage now pins the `0x1f756` consumer
of render-record `+0x20`: it runs only on five-band boundaries, filters
object byte `+4` against the current band, uses byte `+5 & 0x0f` to read
a pattern longword from ROM table `0x308de`, clears bridge flag bit
`0x10`, decrements remaining rows at object `+0x0a`, and writes the
selected low pattern word once per row through `0x1f7b0` / `0x1f626`.

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
The generated `ic30_ic13_active_symbol_set_flow.md` report traces
`ESC (` / `ESC )` through `0x120be` and `0x1be22`: normal symbol-set
finals compute PCL codes as `(parameter << 5) + suffix`, store requested
words at `0x782ef4` / `0x782f04`, select through `0x156de`, and consume
active words at `0x783144` / `0x783146`; final `X` is instead font-ID
selection through `0x17708`, and final `@` dispatches `3@` plus
firmware-supported table variants backed by `0x782f1c/20/24/28`. The
generated `ic30_ic13_symbol_set_patch_tables.md` report decodes all 18
`0x14fce` patch entries as `map[dst] = map[src]` byte-copy pairs and
labels them from the Technical Reference: ISO 2 IRV, ISO 4 United
Kingdom, ISO 25/69 French, HP/ISO German, ISO 15 Italian, ISO 14 JIS
ASCII, ISO 57 Chinese, ISO 10/11 Swedish, HP/ISO Spanish, ISO 16/84
Portuguese, and ISO 60/61 Norwegian. It also documents hard-coded `0E`
HP Roman Extension and `0U` ISO 6 ASCII cases.

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
  - Current behavior: renders each glyph through table `0x1f08e`
- `0x10`
  - Target: `0x1f0d2`
  - Payload entry shape: glyph byte, coordinate word
  - Current behavior: renders wide glyphs in 16-pixel chunks via
    `0x2f27c`, then a remainder through table `0x1f1ac`
- `0x20`
  - Target: `0x1f1f0`
  - Payload entry shape: glyph byte, vertical/plane byte, coordinate
    word
  - Current behavior: offsets glyph bitmap data by `byte*0x80`, clips
    height to `0x80`, then renders through table `0x1f08e`
- `0x30`
  - Target: `0x1f264`
  - Payload entry shape: glyph byte, vertical/plane byte, coordinate
    word
  - Current behavior: combines the `byte*0x80` plane adjustment with the
    wide-glyph chunk/remainder path

Encoded raster span mode behavior:

- 0
  - Target: `0x1f8da`
  - Payload behavior: copy literal words from payload to destination
- 1
  - Target: `0x1f8e6`
  - Payload behavior: expand each payload byte through word table
    `0x30914` and write the result to two adjacent row/band destinations
- 2
  - Target: `0x1f920`
  - Payload behavior: expand payload bytes through longword table
    `0x30b14` and write to up to three row/band destinations, with row
    selection driven by clipped `D3` state
- 3
  - Target: `0x1f9c6`
  - Payload behavior: expand each payload byte through table `0x30914`
    into a longword and write to four row/band destinations

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

The executable harness `tools/render_fixture_harness.py` combines the
host-byte fetch, tokenizer/delayed-payload, page-geometry,
macro/data-chain, direct-control, reset, text, rule, raster, bridge,
row-copy, built-in glyph, symbol-set, and downloaded-font fixture
families into one ROM-backed self-test. It emits
`generated/analysis/ic30_ic13_renderer_fixture_harness.md` and currently
verifies 354 checks. The raster coverage now includes ROM-table
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
queued object, bridge, rendered row, and row counter, and now also ties
the same bytes fetched through the modeled `0xa904` ring source to the
queued object, `0x1edc6` bucket-root bridge fields, empty rule/fixed
lists, and rendered row; the 150/100/75-dpi streams now start from the
modeled `0xa904` ring source and tie the same parser handlers, restored
`0x105d0` records, payload offsets, queued objects, and rendered
expansion rows to modes 1/2/3; the `ESC *t300R` / `ESC *r0A` /
`ESC *b4W` edge stream now starts from the modeled `0xa904` ring source
and ties the parser/restore path to capped queueing, inclusive
page-extent queue-and-advance, beyond-extent drain/no-row-advance, and
negative-row drain-with-advance transfer-gate outcomes; the
payload-control stream now starts from the modeled `0xa904` ring source
and proves raw payload `f0 1a 58 aa 55` queues as `f0 00 aa 55`; the
consecutive-row `ESC *b2W` stream now starts from the modeled `0xa904`
ring source and ties two restored `80 57 00 02 00 00` records to payload
offsets `17` and `24`, queued coords `0x0000` and `0x1000`, and final
row_y `2`; the multi-row and chained-transfer host-fetched streams now
also pin the `0x1edc6` bridge contract for their active raster chain
heads; the active-resolution stream now starts from the modeled `0xa904`
ring source and ties an in-raster `ESC *t75R` handler `0x10808` to
preserved mode 0/scale 1 state before queueing the next row; the
end-raster stream now starts from the modeled `0xa904` ring source and
ties `ESC *rB` handler `0x107fa` to active-clear state before
`ESC *t150R` updates mode/scale again; the chained-resolution
`ESC *t300r150R` stream now starts from the modeled `0xa904` ring
source, keeps the ROM parser in the `*t` family after lowercase `r`, and
exits at uppercase `R`; and the chained `ESC *b2w2W` stream now starts
from the modeled `0xa904` ring source and proves uppercase `W` restores
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
Page-root allocation coverage is now backed by
`generated/analysis/ic30_ic13_page_root_allocation.md` and pins the
`0x10110` selected-context slot bootstrap after `0x10084` first-root
allocation; page-root publication coverage now also pins the `0xff1e`
pool-record header fields for default reset publication and nonzero
status/environment copies before render bridging, and page-record bridge
coverage now pins the `0x1ed84` active-record header copies plus the
render-record destination offsets `+0x18/+0x1c/+0x20/+0x24` written by
`0x1edc6`. Direct plain text coverage now traces `!!` through two
`0xd04a` parser events and ties that stream to one page-record root
allocation, bucket-0 reuse, and real-HMI rows rendered after the
`0x1edc6` bridge. Direct mixed text/control coverage now also feeds
`ESC &k1G!\r!` through the modeled `0xa904` ring source before tracing
parser handlers `0xedf8`, `0xd04a`, `0xf02c`, and `0xd04a`, then ties
that same fetched stream to one page-record root allocation, bucket-0
reuse, and rows rendered after the `0x1edc6` bridge; `ESC &k2G!\n!`
routes line-termination handler `0xedf8`, LF handler `0xf08c`, and the
two printable bytes through `0xd04a`, proving mode `0x60` applies CR+LF
before the second glyph queues at compact coord `0x3b00`,
`ESC &k0G HT BS !` routes line-termination handler `0xedf8`, HT handler
`0xf1cc`, and BS handler `0xf2a8` into the page-record path and renders
after queueing through `0xd04a` at compact coord `0x0a01` / pixel x
`26`, `ESC &a1L!` now routes left-margin handler `0xeb58` into the same
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
`ESC &a2c+1R!` routes lowercase-final horizontal cursor handler
`0xf39e`, keeps parser mode `12` for relative vertical handler `0xf560`,
and renders after queueing through `0xd04a` at compact coord `0x1a02` /
bucket `3`, `ESC &l3E!` routes top-margin handler `0xece2` into the
page-record path and renders the vertically shifted glyph at compact
coord `0x9001` in bucket `6`, and `ESC &f0S ESC &a2C ESC &f1S!` routes
cursor-stack handlers `0xf75e` around cursor-position handler `0xf39e`,
restores the original cursor, then queues printable `!` through `0xd04a`
at compact coord `0x0001`. A grouped host-fetch direct text/control
fixture now starts the plain, CR/LF, HT/BS, margin, cursor-position,
vertical-layout, and cursor-stack page-record streams from the modeled
`0xa904` ring source, drains every byte, replays the same parser
handlers, and lands on the same `0x1387c` page-record objects and
rendered row counts; the same grouped check now pins that `0x1edc6`
preserves the bucket root, clears rule/fixed lists, and copies the
selected context slot into the render record. Direct publication-stream
coverage traces `!\x1bE`, `ESC &k2G!\f`, `!\x1b&l1A`, and `!\x1b&l1O`
through the ROM parser path, proving printable fallback to `0xd04a`,
reset dispatch to `0xcc52`, line-termination dispatch to `0xedf8`, FF
dispatch to `0xf0f0`, page-size dispatch to `0xfc74`, and orientation
dispatch to `0x10220` before the modeled page-record publication
fixtures run; the publication-boundary fixture ties those same streams
to one root allocation, one `0xff1e` publication, current-root clearing,
rendered rows after `0x1edc6`, and the same rows after the published
records pass through `0x1ed84` and `0x1ef6a`; the host-fetch publication
fixture now starts those same four streams from the modeled `0xa904`
ring source, drains the ring bytes, replays the same parser handlers,
lands on the same published rows, and now pins that the `0x1edc6` bridge
preserves the published bucket root, clears rule/fixed lists, and copies
the selected context slot into the render record. The host-fetched
reset, FF, page-size, and orientation cases also pin the pool header
after `0xff1e`: state byte `+4 = 2`, default status/environment fields,
published pointer `0x780ea6`, bucket-root prefix, and context-slot
prefix all match the modeled publication records before the bridged rows
are compared. Macro coverage now has the same ROM-table proof for
`ESC &f-123y0x1X`, walking modes `0 -> 1 -> 5 -> 17 -> 17 -> 17 -> 0` to
handlers `0xe112`, `0xdd08`, and `0xdd08` before applying the modeled
macro state effects; a second macro-definition trace proves alternate
table `0x116f6` leaves payload bytes unclaimed while still routing
`ESC &f1X` to `0xdd08`, simple execute and call payloads drain through
`0xa904`, route replayed `!\r` through parser handlers `0xd04a` and
`0xf02c`, and feed the same bridged page-record object and rows, and a
stored `ESC &k1G!\r!` macro payload now drains through `0xa904`, routes
replayed bytes through handlers `0xedf8`, `0xd04a`, `0xf02c`, and
`0xd04a`, and feeds the same page-record stream and rendered rows as the
direct mixed control-byte model; the execute, call, and mixed-control
replay payloads now also pin the `0x1edc6` bucket/context bridge
contract before rendering.

This is still not enough for pixel-perfect reproduction by itself. The
next unresolved step is to replace fixture-only source/bucket states
with fuller parser-produced page objects, replace the remaining modeled
font state with a full live parser-state run that populates current
records and source/page objects, then replace the producer-modeled
text/raster bucket objects with page objects captured or reproduced from
the full parser/imaging path. The reset, FF, page-size, and orientation
publication fixtures now start without a current page root and mark the
first printable queue step as the modeled page-record root allocation
point, but that is still not a full live parser allocation. Raster
coverage now has a named flow report plus ROM-table `0x11774` dispatch
traces for the primary, 150/100/75-dpi, consecutive-row, capped/drained,
active-resolution-ignore, end-raster, and host-fetched chained-lowercase
`ESC *t#R` / `ESC *r#A` / `ESC *b#W` streams. It still needs a full
CPU/parser-state fixture that executes through `0x121cc` / `0x105d0`
with real parser-produced page/control pool records. The constructed
`0x1f0d2` and `0x1f1f0` inline cases now also have type-2 `0x1719c`
payload-backed fixed-record coverage; the selected inline/downloaded
page-record object now crosses `0x1edc6` with context slot `3` intact
before compact rendering; the `0x1f264` segmented-wide case now has
selected-memory isolation plus host-fetched `ESC *c4660d37e5F`,
host-fetched `ESC )s0W`, host-fetched `ESC )s80W`, and host-fetched
`ESC )s2193W` parser boundaries, plus a host-fetched `ESC )s18W`
downloaded-character payload-control stream that normalizes `1a 58`
before wide glyph rendering and now crosses `0x1edc6` plus the
`0x1ed84`/`0x1ef6a` render-entry path before rendering the same wide row.
The fetched `ESC )s2193W` downloaded-pointer object
now also crosses `0x1edc6` plus the `0x1ed84`/`0x1ef6a` render-entry
path before rendering the same segmented-wide row. The fetched
font-control state now carries
current id `0x1234` and current character `0x25` into fetched
descriptor, resource-payload, and downloaded-character streams, tying
delayed record restoration through `0x121cc` / `0x12218`, descriptor or
payload offsets/lengths, `0x15d0a` current/continuation descriptor
routes, `0x16fae`/`0x1719c` resource-payload allocation and replacement
bookkeeping, `0x16498` downloaded-pointer allocation, and the rendered
segmented-wide row. The full built-in scan proves the verified ROM
resources do not contain a normal wide or non-mode-1 bitmap-entry case.

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
- The later `0x196c4` lead scans page-root `+0x2c` font slots and calls
  `0x1ba6c` if a slot matches; `0x1ba6c` flushes text, finalizes the
  current root through `0xff1e`, refreshes page/font state through
  `0xf8fc`, flushes again, and waits through `0x9ac2`. It is not a
  bucket-chain consumer.
- `0x780ea6` and nearby aliases are the fixed 0x6c-byte page/control
  record pool used by allocator `0x9a9a`. They are not independent final
  image buffers.

## Next Targets

- Replace the host-fetched font-control, descriptor, resource-payload,
  and downloaded-character boundaries with a full live parser-state run
  that populates current records/source objects; then replace
  producer-modeled text bucket fixtures with full parser-produced
  page-object payloads.
- Replace the remaining synthetic `ESC E` reset-state fixtures with
  parser-produced page-object fixtures so partial-page finalization and
  current-page-root clearing are proven from real queued objects,
  building on the host-fetched publication headers now pinned at the
  `0xff1e` boundary.
- Broaden the narrow direct-control byte-stream fixtures into the full
  firmware parser path now that cursor variables `0x782c8a` and
  `0x782c8e` are named as horizontal and vertical respectively.
- Finish rectangle handlers at `0x010898` and the width/height handlers
  around `0x010a40..0x010e68`; these now appear to share page-object
  storage with raster, not a direct framebuffer write.
- Compare physical engine/self-test placement against the now-matched
  ROM/manual logical page and printable-area dimensions.
