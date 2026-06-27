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

These notes track firmware behavior that directly affects page pixels.
Names are provisional where the ROM state variables are not fully
cross-referenced yet.

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
`ESC &l4W 00 00 00 02 !` proves the four payload bytes are not parsed as
controls or printable bytes, and that the following `!` still reaches
the page-record queue at compact coord `0x9001`.
Fixture `ESC &l4w4W 00 00 00 02 !` proves the same boundary for the
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

An address-aware `0x136d2` fixture now pins the paired list rooted at
page offset `+0x28`. It uses the same 14-byte `0x1381c` allocation
contract, writes byte `+5` from the normalized fixed/rule mode, and
confirms the same bucket-byte ordering for lower, higher, and equal
entries before the `0x1edc6` bridge converts it into render-record
`+0x20` fixed-list shape.

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

A `0x1ef6a` page-band walker now merges compact text, mode-0 raster,
and a crossing patterned rule across bands `0` and `5`, carrying the
mutated rule node into the second band. The remaining gap is therefore
parser-produced heterogeneous page objects and final device-output
validation, not the modeled per-band merge itself.

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
read context slot `0`, and the rows match the pinned primary fixture. The
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
  - Current behavior: renders each glyph through table `0x1f08e`, with
    `0x1f414` splitting the row count at `0x783a20` and continuation rows
    written through the `0x7810b4 + D2` fallback buffer
- `0x10`
  - Target: `0x1f0d2`
  - Payload entry shape: glyph byte, coordinate word
  - Current behavior: renders wide glyphs in 16-pixel chunks via
    `0x2f27c`, then a remainder through table `0x1f1ac`; crossing rows
    rerun from `0x7810b4 + D2` after the `0x1f414` count split
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
allocation, plus root `+0x06`, `+0x09`, and `+0x16` geometry fields;
page-root publication coverage now also pins the `0xff1e` pool-record
header fields for default reset publication and nonzero
status/environment copies before render bridging, and page-record bridge
coverage now pins the `0x1ed84` active-record header copies plus the
render-record destination offsets `+0x18/+0x1c/+0x20/+0x24` written by
`0x1edc6`. Direct plain text coverage now traces `!!` through two
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
through `0xd04a` at the unchanged compact coord `0x0001`, and
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
lists, and copies the selected context slot into the render record. The
host-fetched
missing-root `ESC E` case drains from the same ring source, reaches
handler `0xcc52`, and lands on the no-publication reset state. The
host-fetched
reset, FF, page-size, orientation, paper-source, and copies cases also pin
the pool header
after `0xff1e`: state byte `+4 = 2`, status/environment fields including
copies word `+0x0c`, published pointer `0x780ea6`, bucket-root prefix,
and context-slot prefix all match the modeled publication records before
the bridged rows are compared. Macro coverage now has the same ROM-table
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
`0xd04a`, and feeds the same page-record stream and rendered rows as the
direct mixed control-byte model; the execute, call, and mixed-control
replay payloads now also pin the `0x1edc6` bucket/context bridge
contract before rendering. Macro overlay publication is now pinned for a
visible mixed page record as well: selector `4` state leads `0xff1e` to
resolve saved id `0x782a94`, build a non-replay `0xe4f4` frame, re-enter
`0x11774`, queue stored `!\r` into a page record that already contains a
selector-7 rectangle rule, publish through `0xff1e`, and render both
layers through `0x1ed84`/`0x1ef6a`.

This is still not enough for pixel-perfect reproduction by itself. The
mixed text/rule/raster/FF fixture is now the first complete byte-stream
page-image contract through host fetch, parser handlers, addressed
page-record storage, `0xff1e` publication, `0x1ed84` / `0x1edc6`, and
final row comparison. The suite has since been broadened with font
selection and downloaded-glyph page-image cases: primary/secondary
font-selection streams render visible compact rows, downloaded-glyph FF
publication renders through `0xff1e` / `0x1ed84` / `0x1ef6a`, and
fixture `parser-driven downloaded glyph rule raster stream composes
through 0x1ef6a` combines an installed downloaded glyph, selector-7 rule,
and mode-0 raster row in one parser-driven page stream. The next
unresolved step is therefore not adding those fixture families, but
replacing remaining modeled font-install and producer-state handoffs with
full live parser-state runs that populate current records, source/page
objects, and raster/text buckets in CPU memory before imaging. The reset,
FF, page-size, orientation, paper-source, and copies publication fixtures
now start without a current page root and mark the first printable queue
step as the modeled page-record root allocation point, but that is still
not a full live parser allocation. Those six publication paths now also
have addressed variants:
`!\x1bE`, `ESC &k2G!\f`, `!\x1b&l1A`, `!\x1b&l1O`, `!\x1b&l2H`, and
`!\x1b&l2X\f` queue the printable byte through addressed
`0x1387c`/`0x1381c`, materialize the page record, publish through the same
`0xff1e` boundaries, and render through `0x1ed84`/`0x1ef6a` with the same
rows. The host-fetched text/rule/raster fixture now also
publishes its full bucket
array, rule list, and context slots through modeled `0xff1e`, then
renders the published record through `0x1ed84` and `0x1ef6a` with the
same composed rows. That same fixture now runs text, `ESC *c`, and the
delayed `ESC *b#W` raster transfer through one mixed page-record stream
runner instead of attaching the raster row after the text/rule record.
Adding FF to that stream now publishes the heterogeneous page record
through the modeled `0xff1e` boundary and renders the published record
through `0x1ed84` and `0x1ef6a` with the same rows; the addressed
text/rule/raster stream now has the same trailing-FF publication check
with the raster object linked from addressed `0x1381c` storage. The
semantic checkpoint in `notes/semantic-state-model.md` now classifies
that same cluster: canonical page-record objects are at `0x00d0c004`,
`0x00d0c02a`, and `0x00d0c038`; parser scratch restores raster record
`80 57 00 02 00 00` and payload `c3 3c` at offset `28`; firmware
bookkeeping leaves `0x782a70 = 0x00bc`, `0x782a72 = 0x00d0c000`,
and `0x782a76 = 0x00d0c044`; derived render caches include
`0x783a20 = 0x0050`, `0x783a22 = 0`, and
`0x783a28 = 0x00100000`.
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
`ESC *t#R` / `ESC *r#A` / `ESC *b#W` streams. It still needs a full
CPU/parser-state fixture that executes through `0x121cc` / `0x105d0` in one
live 68000 memory image, but the dense text/rule/raster stream now has
addressed `0x1381c` page/control storage for the raster object and published
record fields. The constructed 150/100/75-dpi raster streams now start from
modeled `0xa904` host bytes,
cross the ROM parser table and delayed `0x105d0` restore, queue encoded
raster modes 1/2/3, then render through `0x1ed84` / `0x1ef6a`.
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
`0x1f596`, and compares the final three composed rows. The remaining
middle edge has now been narrowed by fixture `parser-driven downloaded glyph
rule raster stream composes through 0x1ef6a`: after the same fetched
`ESC )s18W` font-install bytes, page bytes
`ESC *c12a3b0P ) ESC *t300R ESC *r0A ESC *b2W c3 3c` route through parser
handlers `0x10e68`, `0x10e22`, `0x10898`, `0xd04a`, `0x10808`, `0x1075a`, and
`0x11f82`, then delayed `0x105d0` queues the raster object. That fixture
produces the same bucket-5 glyph/raster chain, the same bridged rule list, and
the same `0x1ef6a` rows. The remaining caveat is the font-install split: the
font payload phase still uses the modeled `0x16c14` install output as the
resource image for the parser-driven page phase. That split is now documented
as an exact handoff: the page phase consumes
`bytearray(downloaded_wide_even_install["header"])`, whose host-fetched
install fixture pins glyph `0x29`, table entry `0x00ee`, record delta
`0x0780`, bitmap offset `0x078c`, record bytes
`00 00 00 00 0c 01 00 01 00 90 00 00`, and the 18 copied bitmap bytes. The
remaining open edge is live CPU continuity from the `0x16c14` / `0x16498`
install return after byte `24` back to parser loop `0x11774` for the following
`0x10e68` rectangle handler.
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
interior segmented row count. The rows-`0x0102` sibling `ESC )s516W` +
printable `3` + FF also crosses `0xff1e`, but the page-record source exposes
row byte `0x02`; it publishes selector `0x0003` bucket `1` only and leaves the
visible render edge `0x1ed84`/`0x1ef6a -> 0x1effe` unresolved. The fetched
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
  that populates current records/source objects; then replace the
  remaining producer-modeled text bucket fixtures with full
  parser-produced page-object payloads. The downloaded-character path
  now has one combined fetched stream driving font-control state,
  payload install, and printable output into segmented page-record
  buckets, but it is still family-split modeling rather than a full
  live parser-state interpreter.
- Replace the remaining synthetic `ESC E` reset-state fixtures with
  parser-produced page-object fixtures so partial-page finalization and
  current-page-root clearing are proven from real queued objects,
  building on the host-fetched publication headers now pinned at the
  `0xff1e` boundary.
- Broaden the narrow direct-control byte-stream fixtures into the full
  firmware parser path now that cursor variables `0x782c8a` and
  `0x782c8e` are named as horizontal and vertical respectively.
- Extend rectangle/rule coverage from modeled handler state into
  parser-produced full-page comparisons and physical placement checks.
- Compare physical engine/self-test placement against the now-matched
  ROM/manual logical page and printable-area dimensions.
