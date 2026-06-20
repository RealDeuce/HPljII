# Page Geometry and Raster Imaging Notes

Sources: `generated/analysis/ic30_ic13_page_geometry_tables.md`; `generated/analysis/ic30_ic13_parser_xrefs.md`; `generated/analysis/ic30_ic13_page_root_references.md`; `generated/analysis/ic30_ic13_render_path_references.md`; `generated/analysis/ic30_ic13_render_dispatch_tables.md`; `generated/analysis/ic30_ic13_render_subrenderers.md`; `generated/analysis/ic30_ic13_render_expansion_fixtures.md`; `generated/analysis/ic30_ic13_render_destination_fixtures.md`; `generated/analysis/ic30_ic13_render_row_copy_fixtures.md`; `generated/analysis/ic30_ic13_font_context_bridge.md`; `generated/analysis/ic30_ic13_text_glyph_index_flow.md`; `generated/analysis/ic30_ic13_font_control_flow.md`; `generated/analysis/ic30_ic13_direct_control_code_flow.md`; `generated/analysis/ic30_ic13_esc_e_reset_flow.md`; `generated/analysis/ic30_ic13_printable_text_path.md`; `generated/analysis/ic30_ic13_text_cursor_span_flow.md`; `generated/analysis/ic30_ic13_active_symbol_set_flow.md`; `generated/analysis/ic30_ic13_symbol_set_patch_tables.md`; `generated/disasm/ic30_ic13_page_size_handler_00fc74.lst`; `generated/disasm/ic30_ic13_orientation_handler_010220.lst`; `generated/disasm/ic30_ic13_coordinate_math_0104d8.lst`; `generated/disasm/ic30_ic13_raster_handlers_0105d0.lst`; `generated/disasm/ic30_ic13_payload_dispatch_011f82.lst`; `generated/disasm/ic30_ic13_text_span_flush_012714.lst`; `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`; `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`; `generated/disasm/ic30_ic13_raster_object_queue_013070.lst`; `generated/disasm/ic30_ic13_display_list_helpers_013386.lst`; `generated/disasm/ic30_ic13_active_object_dispatch_014ba4.lst`; `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`; `generated/disasm/ic30_ic13_page_root_font_slot_scan_0196c4.lst`; `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`; `generated/disasm/ic30_ic13_bitmap_state_setup_01ee9e.lst`; `generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`; `generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst`; `generated/disasm/ic30_ic13_bitmap_draw_core_01f3d4.lst`; `generated/disasm/ic30_ic13_bitmap_encoded_span_modes_01f88e.lst`; `generated/disasm/ic30_ic13_bitmap_row_copy_tables_01fa5c.lst`; `generated/disasm/ic30_ic13_glyph_row_copy_helper_02f27c.lst`; `generated/disasm/ic30_ic13_assign_font_id_015a56.lst`; `generated/disasm/ic30_ic13_font_control_dispatch_016df6.lst`; `generated/disasm/ic30_ic13_font_id_select_017708.lst`; `generated/disasm/ic30_ic13_default_font_tables_01ab84.lst`; `generated/disasm/ic30_ic13_symbol_set_handler_01be22.lst`; `generated/disasm/ic30_ic13_font_update_common_00c580.lst`; `notes/pcl-command-map.md`; `notes/resource-rom.md`.

These notes track firmware behavior that directly affects page pixels. Names are provisional where the ROM state variables are not fully cross-referenced yet.

## Page Size Tables

The page-size command handler `ESC &l#A` at `0x00fc74` maps PCL page-size parameters into internal page codes, stores the code at `0x782da2`, then rebuilds page geometry.

The lookup helpers at `0x009d16`, `0x009d4e`, `0x009d86`, and `0x009dbe` mask the internal code with `0x7f` and index eleven word entries. The generated table report records all current values.

Important confirmed mappings:

| PCL page size | Internal code | Masked index | a112 / `0x9d16` | a128 / `0x9d4e` | a13e / `0x9d86` | a154 / `0x9dbe` |
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

- `0x9d4e` writes `0x782db2`; raster transfer bounds check against this value.
- `0x9d16` writes `0x782db4`; raster-start code uses this value while computing a remaining byte/line limit.
- `0x9d86` and `0x9dbe` feed orientation-specific physical or margin extents. For letter, they produce 2550 and 3300, matching 8.5 by 11 inches at 300 dpi.
- The `a112` and `a128` values are smaller than physical paper and currently look like logical/printable extents.
- `0x9e56` stores the signed remainder of `(0x051f - floor(height / 2)) / 16` at `0x782dc0`; for `ESC &l1A` letter portrait this yields `11`.

`tools/render_fixture_harness.py` now has executable page-geometry fixtures for the `0x9d16`/`0x9d4e`/`0x9d86`/`0x9dbe` masked table lookups, `ESC &l#A` page-size mapping, and `ESC &l#O` orientation recomputation. The `ESC &l1A` fixture pins internal code `6`, width `3030`, height `2025`, portrait margin `3150`, top offset `90`, and printable extent `3090`; the PCL `80` fixture pins internal code `0x88` masking to table index `8`.

## Orientation

`ESC &l#O` at `0x010220` accepts values below `2`. If the requested orientation differs from `0x782da3`, it updates `0x782da3`, rebuilds page geometry, and refreshes current cursor/font state.

Orientation-sensitive geometry work includes:

- `0xf9ac`: chooses table `0x9dbe` for orientation 0 and table `0x9d86` for orientation 1, storing the result at `0x782dba`.
- `0xf87e`: sets `0x782dbe` to `0x003c` in orientation 0 and `0x0032` in orientation 1, then swaps `0x782db2` / `0x782db4` into `0x782db6` / `0x782db8` depending on orientation.
- `0x103ea`: reloads orientation-specific values into `0x782daa`, `0x782dac`, `0x782dae`, and `0x782db0`.

The executable `ESC &l1O` fixture starts from letter portrait, changes orientation to landscape, and pins active extents `2025x3030`, landscape margin `2175`, printable extent `2125`, top offset `100`, and the `0x103ea` landscape threshold sequence `2175, 2550, 2480, 2550`.

The coordinate helper group at `0x0104d8..0x010550` converts between whole coordinates and a packed fixed-point form with 12 subunits per whole unit. `0x10518` adds signed whole/fraction pairs and clamps the whole part to `0x7ffe`.

## Raster Graphics State

Raster-related PCL handlers:

| Command | Handler | Current role |
| --- | --- | --- |
| `ESC *t#R` | `0x010808` | raster resolution |
| `ESC *r#A` | `0x01075a` | start raster graphics |
| `ESC *r#B` | `0x0107fa` | end raster graphics |
| `ESC *b#W` | `0x011f82` -> delayed handler `0x0105d0` | transfer raster row bytes |

The raster state block is rooted at `0x783170` in the handlers.

Observed fields:

| Offset | Access | Current interpretation |
| ---: | --- | --- |
| `+0x00` | word | start/baseline coordinate word copied from field `+0x0a` |
| `+0x02` | word | whole coordinate derived from current packed coordinate during row transfer |
| `+0x04` | word | bytes accepted or clipped for current row |
| `+0x06` | word | excess bytes beyond accepted row count |
| `+0x08` | word | resolution scale minus one |
| `+0x0a` | long | start/baseline coordinate copied from current cursor state |
| `+0x0e` | word | raster scale: 1, 2, 3, or 4 |
| `+0x10` | word | maximum accepted byte count derived from page extent and raster scale |
| `+0x12` | byte | raster-active / initialized flag |

`ESC *t#R` maps the requested resolution into a scale:

| Requested value range | Stored scale |
| --- | ---: |
| `> 150` | 1 |
| `101..150` | 2 |
| `76..100` | 3 |
| `<= 75` | 4 |

This is consistent with a `300 dpi / requested dpi` scale for 300, 150, 100, and 75 dpi raster modes.

`ESC *r#A` initializes the state block only if field `+0x12` is clear. With parameter `1`, it seeds field `+0x0a` from one current cursor coordinate; otherwise it clears it. Which cursor variable is used depends on orientation:

- orientation 0: seed from `0x782c8a`;
- orientation 1: seed from `0x782c8e`.

It then computes field `+0x10` from page extent, the baseline word, and `scale * 8`. This looks like a clipped maximum byte count for subsequent row transfers, but the exact axis naming is still open.

`ESC *b#W` does not call the transfer routine immediately. Handler `0x011f82` stores delayed handler pointer `0x0105d0` through `0x0121cc`; the later payload dispatcher restores the parsed six-byte command record and calls the saved handler when the data is ready. The executable harness now pins the corresponding `0x121cc` snapshot bytes for a parsed `ESC *b4W` record and the `0x12218` restore/dispatch contract.

The transfer routine at `0x0105d0`:

- reads the byte count parameter from the parsed command record;
- sets raster field `+0x12`;
- clips or skips input bytes by repeatedly calling `0xdace`;
- calls `0x10084` to ensure a page/image buffer is allocated;
- calls `0x13070` with the raster state block when row data is in bounds;
- advances current cursor state after the row transfer and clamps against `0x782dc6`.

## Page Object Queues

The transfer routine does not draw directly into a final bitmap. It queues a raster row object under the current page root at `0x78297a`.

`0x10084` ensures the current page object root exists. On first allocation, it:

- calls allocator `0x9a9a`;
- stores the root pointer in `0x78297a`;
- clears stream-allocation state `0x782a70`;
- seeds stream cursor pointers `0x782a72` and `0x782a76`;
- clears 256 longwords through the pointer at page-root offset `+0x1c`.

Current page-root fields:

| Root offset | Current interpretation |
| ---: | --- |
| `+0x1c` | array of bucket heads indexed by `0x782a7c` |
| `+0x20` | start of the 0x100-byte chunk chain used by display-list object storage |
| `+0x24` | linked-list head used by rectangle/rule-like objects |
| `+0x28` | second linked-list head used by another rectangle/rule mode |
| `+0x2c..+0x68` | 16 current-font context record slots copied from the `0x782ee6` / `0x782ef6` family |

`0x132b6` and `0x1381c` implement a small stream allocator over 0x100-byte chunks:

- `0x782a70`: bytes remaining in the current chunk.
- `0x782a72`: pointer to the link field of the current chunk.
- `0x782a76`: next free byte in the current chunk.
- new chunks are allocated via `0x1710` and chained through their first longword, leaving `0xfc` payload bytes.

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

`0x138de` is the first confirmed payload-storage routine for raster data. It reads bytes through host byte routine `0xa904`, handles embedded `0x1a 0x58` by calling `0xd99a`, writes bytes to the object payload pointer, and decrements the source raster-state byte count at offset `+0x04`.

Rectangle/rule-like graphics share the same storage system but use the linked lists rooted at page offsets `+0x24` and `+0x28`. The entry `0x13386` calls `0x134d6` to compute the same packed ordering keys, then inserts an object via `0x133aa`. Follow-up routines around `0x13520..0x1381c` handle the second rectangle/rule mode and allocate entries through the same 0x100-byte stream allocator.

Text also enters the page-object queue layer rather than drawing directly. The text-span flush path at `0x12714` packages a pending span into the rectangle/rule-like queue by calling `0x13520`; if insertion reports no room it marks page-root flags at `root+0x14` and retries after `0xff1e` / `0x10084`. The text object builder at `0x12f2e` computes the same `0x782a7c` bucket index and packed coordinate key, then allocates queue entries through `0x1387c`. `generated/analysis/ic30_ic13_compact_bucket_allocator.md` decodes that helper: it indexes the page-root `+0x1c` bucket array by `0x782a7c`, reuses an object with matching selector word `+4` while count `+6` is below capacity, or allocates and links a new head object through the shared stream allocator. Its entries store mapped glyph payload data after a short object header, parallel to raster row payload storage.

`generated/analysis/ic30_ic13_printable_text_path.md` anchors the live normal parser path into that source-object builder. Routine `0x11774` fetches bytes through `0xda9a`, and when parser state `0x782999` is zero, alternate/data mode `0x782c18` is clear, and the byte is not claimed by a command table, it calls printable entry `0xd04a`. `0xd04a` builds scratch source object `0x782d7e` by calling `0x1393a(host_byte, 0x782d7e)`, then branches to `0xd550` when source byte `+0x10` is nonzero or `0xd140` when it is zero.

`generated/analysis/ic30_ic13_text_cursor_span_flow.md` splits the post-`0x1393a` path into paired cursor/queue/span routines. The unflagged path is `0xd140` -> `0xd28a` -> `0xd3b2` -> `0xd4ac`; the flagged path is `0xd550` -> `0xd6bc` -> `0xd824` -> `0xd8fc`. The queue handoffs `0xd3b2` and `0xd824` write source fields `+0x12`, `+0x14`, and `+0x16`, mark the current page-root font slot live at `0x78297f + slot`, and call `0x12f2e`. The span updates `0xd4ac` and `0xd8fc` are separate context-record updates that can flush pending text through `0x12714` / `0x126e2`.

`generated/analysis/ic30_ic13_text_glyph_index_flow.md` pins down the compact glyph byte inside that path. Routine `0x1393a` maps the original character byte through either `0x782f32` or `0x783032`, selected by `0x782f06`, and stores the mapped byte as the low byte of text object word `+0x0a`. The later queue builder `0x12f2e` copies source byte `+0x0b` into the first byte of each compact payload entry. Therefore the byte consumed by `0x1f354` is the active character-map result, not necessarily the original host byte.

This confirms a common page-object model:

| Producer | Entry routine | Queue root |
| --- | --- | --- |
| raster rows | `0x13070` | page-root `+0x1c` bucket array |
| text / glyph spans | `0x12714`, `0x12f2e` | page-root `+0x1c` bucket array and shared display-list storage |
| rectangles / rules | `0x13386`, `0x13520` | page-root `+0x24` / `+0x28` linked lists plus shared display-list storage |

## Render/Banding Bridge

The first confirmed bridge from queued page/control records toward the bitmap renderer is `0x1ed84..0x1ee9c`.

`0x1ed84` copies metadata from the active page/control record at `0x780eae` into a selected work record, then calls `0x1edc6`. The surrounding alternator at `0x1ecd6` publishes the selected work record at `0x783a18` and calls `0x1ee9e` when record geometry changes.

`0x1edc6` copies queue/list pointers from the source record into the destination render record:

| Source record offset | Destination render-record offset | Current interpretation |
| ---: | ---: | --- |
| `+0x1c` | `+0x18` | bucket-head array copied from page/control record |
| `+0x24` | `+0x1c` | linked object list copied from page/control record |
| `+0x28` | `+0x20` | second linked object list copied from page/control record |
| `+0x2c..+0x68` | `+0x24..+0x60` | 16 current-font context record pointers |

After copying, `0x1edc6` normalizes objects in the destination lists: it sets flag bit `0x10` in object byte `+5`; for the `dest+0x1c` list it copies word `+0x0a` to `+0x0c`; for the `dest+0x20` list it copies word `+8` to `+0x0a` and sets bytes `+0x0c=1`, `+0x0d=8`.

`generated/analysis/ic30_ic13_font_context_bridge.md` refines the `+0x2c` interpretation: `0xc428` / `0xc4fc` install pointers to current-font context records in these 16 page-root slots, not raw glyph pointers. `0x1edc6` copies them to render-record slots, and compact text/glyph objects use byte `+5` low nibble to select one of the copied render-record slots before `0x1f008` loads it into `0x783a2c`.

`0x1ee9e` initializes bitmap render state. It stores the active record width word times four into `0x783a1c`, which is used later as a line stride. It also stores buffer base `0x7810b4` into the render record, derives a band/row value from `0x7810b8`, and fills a 16-word offset table at `0x7839f8`.

The render entry `0x1ef6a` temporarily loads the current render record from `0x783a18` into `A6`. It then:

- calls `0x1ef86` to compute `0x783a22`, `0x783a20`, and the current band destination base `0x783a28`;
- calls `0x1efc2` to index the bucket-head array at render-record `+0x18` by the current band/row word, walk the object chain, and dispatch object classes;
- calls `0x1f446`, a table-driven special-object dispatcher;
- calls `0x1f756`, which walks the render-record `+0x20` list and writes fixed-width/rule-like bitmap spans.

The first confirmed bitmap-writing routines are in `0x1f4e0..0x1fa5a`. They write 16-bit words to destinations derived from `0x783a28` or `0x7810b4`, advance rows by stride `0x783a1c`, and use mask/expansion tables around `0x2fefe..0x30b14`.

Key current anchors:

| Routine | Current role |
| --- | --- |
| `0x1f626` | computes destination pointer `A1` from object coordinates, `0x783a20`, `0x783a28`, `0x7839f8`, `0x783a1c`, and `0x7810b4` |
| `0x1f4e0` | word/mask bitmap writer selected by table `0x1f4a0` |
| `0x1f596` | solid-mask bitmap writer selected by table `0x1f4a0` |
| `0x1f756` / `0x1f7b0` | fixed-width/rule-like list writer from render-record `+0x20` |
| `0x1f812` / `0x1f862` | segment-list writer selected from bucket-chain objects |
| `0x1f88e` | encoded-span writer selected from bucket-chain objects |

### Object Class Dispatch

The bucket-chain dispatcher at `0x1efc2` walks render-record `+0x18`, which is the page/control bucket array copied from source offset `+0x1c`. For each bucket object, it advances `A1` to object offset `+4`, masks object byte `+4` with `0xc0`, and uses the result as the first class split:

| Object byte `+4` high bits | Render path | Current producer mapping |
| --- | --- | --- |
| `0x00..0x3f` | compact branch `0x1effe`; table `0x1f024` selected by byte `+4` bits `0x10/0x20` | text/glyph bucket objects from `0x12f2e` / `0x1387c` |
| `0x40..0x7f` | segment-list writer `0x1f812` / `0x1f862` | producer not yet pinned down |
| `0x80..0xff` | encoded-span writer `0x1f88e`; table `0x1f8ca` selected by byte `+5 & 0x03` | raster rows from `0x13070` / `0x13250`, because `0x13250` initializes byte `+4` to `0x80` |

Confirmed producer-to-renderer mappings:

| Producer | Queue/list path | Selector fields | Renderer path |
| --- | --- | --- | --- |
| raster rows | page-root `+0x1c` bucket array -> render-record `+0x18` | `0x13250` writes `object[4]=0x80`; `object[5]` is the low byte of the first `0x13250` argument sourced from raster-state word `+0x08`; `object[6]=capacity`; `object[8]=packed key`; payload starts at `+0x0a` | `0x1efc2` high-bit branch -> `0x1f88e` encoded-span renderer |
| text/glyph buckets | page-root `+0x1c` bucket array -> render-record `+0x18` | `0x1387c` writes the selector word at `object+4`; `0x12f2e` sets bits `0x1000`/`0x2000`, which become byte `+4` bits `0x10`/`0x20`; byte `+5` low nibble selects a render-record context slot copied from source `+0x2c` to render `+0x24` | `0x1efc2` compact branch -> `0x1effe` -> table `0x1f024` |
| rectangle/rule list | page-root `+0x24` -> render-record `+0x1c` | `0x133aa` writes byte `+4` from `0x782a7d`, ORs source word `+8` into byte `+5`, and stores dimensions at `+8/+0x0a`; bridge `0x1edc6` copies word `+0x0a` to `+0x0c` | list renderer `0x1f446`; table `0x1f4a0` selected by `object[5] & 0x0f` |
| second rule/text-span list | page-root `+0x28` -> render-record `+0x20` | `0x136d2` writes byte `+4` from `0x782a7d`, byte `+5` from source `+1`, word `+6` from packed key, and word `+8`; bridge `0x1edc6` copies `+8` to `+0x0a` and sets `+0x0c=1`, `+0x0d=8` | fixed-width/rule writer `0x1f756` / `0x1f7b0` |

### Subrenderer Payloads

The compact text/glyph branch resolves a font/glyph context through `0x783a2c`. That value is loaded from a render-record context slot copied from page-root `+0x2c`; the slot points at a current-font context record whose first longword is the selected resource address plus flag bits. Helper `0x1f354` tests bit 30 of that context longword to distinguish two resource layouts:

- bit 30 set: context base plus word `+8` points to an offset table; the glyph index selects a long offset into a glyph entry;
- bit 30 clear: context base plus `0x40 + 8*glyph_index` is an inline glyph record with a long bitmap offset.

Both forms return a glyph bitmap pointer in `A2`, a byte/word span count in `D1`, a row/count field in `D3`, and sometimes a secondary plane/row pointer in `A3`.

The active character maps are rebuilt during font activation. Built-in contexts use `0x14d9c` to create a base range map from selected font record words `+0x0e` / `+0x10`, then `0x14f16` applies symbol-set-specific remaps. Inline/downloaded contexts use `0x14e24` and `0x14eb6` to populate the same map shape from valid fixed glyph records. The generated `ic30_ic13_active_symbol_set_flow.md` report traces `ESC (` / `ESC )` through `0x120be` and `0x1be22`: normal symbol-set finals compute PCL codes as `(parameter << 5) + suffix`, store requested words at `0x782ef4` / `0x782f04`, select through `0x156de`, and consume active words at `0x783144` / `0x783146`; final `X` is instead font-ID selection through `0x17708`, and final `@` dispatches `3@` plus firmware-supported table variants backed by `0x782f1c/20/24/28`. The generated `ic30_ic13_symbol_set_patch_tables.md` report decodes all 18 `0x14fce` patch entries as `map[dst] = map[src]` byte-copy pairs and labels them from the Technical Reference: ISO 2 IRV, ISO 4 United Kingdom, ISO 25/69 French, HP/ISO German, ISO 15 Italian, ISO 14 JIS ASCII, ISO 57 Chinese, ISO 10/11 Swedish, HP/ISO Spanish, ISO 16/84 Portuguese, and ISO 60/61 Norwegian. It also documents hard-coded `0E` HP Roman Extension and `0U` ISO 6 ASCII cases.

Downloaded-font host command state is anchored in `generated/analysis/ic30_ic13_font_control_flow.md`: `ESC *c#D` writes normalized current font id `0x782f2e`, and `ESC *c#F` values `0..6` dispatch through the table at `0x16db6` to all/current record release helpers, current character/glyph record cleanup via `0x782f30`, downloaded-record mark/unmark count transfers between `0x782782` and `0x782786`, or active/current font-resource housekeeping.

Compact object mode behavior:

| Selector bits from object byte `+4` | Target | Payload entry shape | Current behavior |
| --- | --- | --- | --- |
| `0x00` | `0x1f034` | glyph byte, coordinate word | renders each glyph through table `0x1f08e` |
| `0x10` | `0x1f0d2` | glyph byte, coordinate word | renders wide glyphs in 16-pixel chunks via `0x2f27c`, then a remainder through table `0x1f1ac` |
| `0x20` | `0x1f1f0` | glyph byte, vertical/plane byte, coordinate word | offsets glyph bitmap data by `byte*0x80`, clips height to `0x80`, then renders through table `0x1f08e` |
| `0x30` | `0x1f264` | glyph byte, vertical/plane byte, coordinate word | combines the `byte*0x80` plane adjustment with the wide-glyph chunk/remainder path |

Encoded raster span mode behavior:

| `object[5] & 0x03` | Target | Payload behavior |
| ---: | --- | --- |
| 0 | `0x1f8da` | copy literal words from payload to destination |
| 1 | `0x1f8e6` | expand each payload byte through word table `0x30914` and write the result to two adjacent row/band destinations |
| 2 | `0x1f920` | expand payload bytes through longword table `0x30b14` and write to up to three row/band destinations, with row selection driven by clipped `D3` state |
| 3 | `0x1f9c6` | expand each payload byte through table `0x30914` into a longword and write to four row/band destinations |

The generated fixture report `generated/analysis/ic30_ic13_render_expansion_fixtures.md` now pins down deterministic sample expansions for these encoded raster modes:

- mode 0 literal word-copy payloads;
- mode 1 byte-to-word expansion through `0x30914`;
- mode 2 byte-to-long expansion through `0x30b14`;
- mode 3 cascaded byte expansion through `0x30914`.

The generated fixture report `generated/analysis/ic30_ic13_render_destination_fixtures.md` now pins down synthetic-state expectations for:

- `0x1f3d4` packed coordinate decode into row index, byte-pair offset, `0xa001` sub-byte flag, and destination pointer;
- `0x1f414` count splitting at the current band boundary;
- the main `0x1f626` destination branches: current band, shifted current band, and fallback buffer.

The generated fixture report `generated/analysis/ic30_ic13_render_row_copy_fixtures.md` now decodes the compact glyph row-copy tables into deterministic A1/A2/A3 write traces:

- `0x1f08e` maps glyph byte widths 1..16 to helper routines and row-count tables;
- `0x1f1ac` maps wide-glyph remainder widths 1..16 after full 16-byte chunks;
- `0x2f27c` renders full 16-byte chunks using `0x2f2ac`, with `0x783a46` as the current horizontal phase;
- odd byte widths copy the trailing byte from `A3`, while even byte widths are word copies from `A2`.

The executable harness `tools/render_fixture_harness.py` combines the `0xa904` host byte fetch source-priority fixtures, `0xdaf0`/`0xdb74` tokenizer, `0x121cc` delayed-payload, and `0x1228a`/`0x12358` alternate payload-consumption fixtures, page-geometry command fixtures, macro id/control and execute/call data-chain fixtures, encoded-raster expansion, destination/clipping arithmetic, row-copy behavior, direct control-code cursor/page effects, `ESC E` reset effects, real resource-glyph resolutions, complete mode-1 resource bitmap row decoding, main row-copy rendering of those resource rows, and compact text bucket producer fixtures into a single ROM-backed self-test. It emits `generated/analysis/ic30_ic13_renderer_fixture_harness.md` and currently verifies 204 checks covering host-byte fetch source-priority behavior for `0xa904`, six-byte tokenizer records from `0xdaf0`/`0xdb74`, delayed payload snapshot/restore through `0x121cc`/`0x12218` plus alternate payload consumption through `0x1228a`/`0x12358`, macro id assignment through `0xe112`, macro control dispatch through `0xdd08`, chained macro command-stream start/stop plus modeled definition-payload execute/call frame creation, overlay enable/disable, delete-current/all, guard-state suppression, and permanence/delete state, `0xa904` data-chain byte fetch, printable/CR payload processing, and page-record bridge rendering, execute/call data-chain frames through `0xe418`, page-geometry table lookups through `0x9d16`/`0x9d4e`/`0x9d86`/`0x9dbe`, page-size mapping through `0xfc74`, orientation recomputation through `0x10220`, expansion modes 0..3, destination helper cases, the `ESC &k#G` line-termination map, CR/LF/FF/HT/BS packed-state cursor/page behavior, `ESC &f#S` cursor-stack push/pop/clamp/bounds behavior, `ESC &l#C/#D/#E/#F` vertical layout conversion/reject/default behavior, `ESC *c#A/#B/#H/#V/#G/#P` rectangle size/fill selector/clip/queue behavior plus chained byte-stream selector-7 rule creation, solid, solid/patterned band-crossing, two-band HP-pattern page assembly, gray/HP pattern, and sub-byte HP-pattern rule rendering, `ESC &a#L/#M` margin conversion/reject/cursor-move behavior, `ESC &a#C/#H/#R/#V` cursor-position conversion/relative/clamp behavior, narrow direct-control byte streams, synthetic `ESC E` reset publication/clear paths, main compact glyph rows, wide-glyph remainder rows, the `0x2f27c` full-width chunk helper, built-in `0x1f354` glyph resolution, full decoded glyph rows, `0x1f08e` main row-copy destination rows for four real glyphs across contexts `0x4008004c`, `0x44080418`, and `0x440946b4`, and text bucket objects produced by the modeled `0x14d9c` base-map -> `0x1393a` source-object -> `0x12f2e` queue path. The short producer-modeled fixture uses `LINE_PRINTER` host byte `0x21`, mapped glyph byte `0x20`, source context `0x440946b4`, glyph entry `0x015330`, selector word `0x0000`, count `1`, and coord `0x0000`, then renders through `0x1effe` / `0x1f034`. A `0x1387c` page-record compact bucket allocator fixture now proves same-selector object reuse, count/capacity behavior, full-object new-head allocation, rendering of a short object queued through the page-root bucket-array shape, and allocation/reuse of the segmented `0x2000` tall-glyph objects across buckets `64/8` down to `0/0`. A `0x1edc6` page-record bridge fixture copies that allocator-produced compact bucket from page/control `+0x1c` to render-record `+0x18`, copies context slot `0` into render-record `+0x24`, renders the same rows through the bridged render record, pins the normalization applied to page/control `+0x24` and `+0x28` rule/fixed lists, and includes producer-shaped `0x13386`/`0x136d2` rule objects plus `ESC *c#P` rectangle command-edge objects, a chained rectangle byte-stream object, and selector-7 solid-rule pixels plus solid and patterned band-crossing continuation, two-band HP-pattern page-row assembly, gray selector matrix, HP pattern matrix, and sub-byte HP-pattern pixels. A parser-derived raster state fixture models `ESC *t#R` handler `0x10808` thresholds, proving parameters `300`, `150`, `100`, and `75` select encoded modes `0`, `1`, `2`, and `3`, and models `ESC *r1A` handler `0x1075a` seeding baseline word `16` from cursor-axis longword `0x00100000` before queueing the same mode-0 raster object. Modeled raster command/data streams now start from bytes for `ESC *t300R` / `ESC *r1A` / `ESC *b4W`, `ESC *t150R` / `ESC *r0A` / `ESC *b2W`, `ESC *t100R` / `ESC *r0A` / `ESC *b2W`, and `ESC *t75R` / `ESC *r0A` / `ESC *b2W`; these record handler `0x0105d0`, queue mode-0/1/2/3 objects, bridge the `ESC *b4W` page-record object through `0x1edc6`, and render the literal, two-row, three-row, and four-row expansions selected from the byte stream; a multi-row `ESC *t300R` / `ESC *r0A` stream then queues two consecutive `ESC *b2W` payloads at row_y `0` and `1`, yielding packed coords `0x0000` and `0x1000` in newest-first page-record chain order. Same-group lowercase-final chaining fixtures now cover `ESC *t300r150R` and chained `ESC *b2w` / `2W`, proving continued parser mode and payload-boundary placement while producing the same two-row page-record chain shape as the separate-command stream. A raster-end stream adds bare `ESC *rB` after a queued row, proves handler `0x107fa` only clears the active byte while preserving mode/scale/limit/row_y, and then accepts a subsequent `ESC *t150R` resolution change. Raster row fixtures now model `0x13070` / `0x13250` / `0x138de`: raster state x `16`, y `0`, mode `0`, byte count `4`, and payload `f0 0f aa 55` queue byte-aligned object bytes `00 00 00 00 80 00 00 04 00 01 f0 0f aa 55` under page-root `+0x1c`; after the `0x1edc6` bridge, `0x1f88e` mode 0 renders the literal row at coord `0x0001`. A non-byte-aligned mode-0 object, `00 00 00 00 80 00 00 02 04 01 c3 3c`, pins coord `0x0401` as pixel x `20` and renders `....................##....##..####..`. A mode-1 queued raster object, `00 00 00 00 80 01 00 02 00 01 f0 0f`, proves `0x1f88e` mode 1 expands bytes through table `0x30914` into two rendered rows. A byte-aligned mode-2 object, `00 00 00 00 80 02 00 02 00 01 f0 0f`, proves `0x1f920` expands the queued byte pair through `0x30b14` into three interleaved rows; a non-byte-aligned mode-2 object, `00 00 00 00 80 02 00 02 04 01 f0 0f`, pins coord `0x0401` as pixel x `20` after mode-2 expansion; a band-clipped mode-2 object, `00 00 00 00 80 02 00 02 f0 01 f0 0f`, pins one current-band row and two fallback-buffer continuation rows; and a mode-3 object, `00 00 00 00 80 03 00 02 00 01 f0 0f`, proves mode 3 cascaded expansion into four rendered rows. A second flagged text fixture now models the `0xd824` positioning handoff before `0x12f2e`: cursor `(10,21)` plus real glyph-entry offsets `(6,21)` produces source coordinates `(16,0)`, compact coord `0x0001`, object bytes `00 00 00 00 00 00 00 01 20 00 01`, and rendered rows shifted 16 pixels right. A one-byte normal printable stream fixture starts from host byte `0x21` (`!`) under the documented parser conditions, maps it through `0x1393a`, applies the same `0xd824` positioning, queues through `0x12f2e`, and renders the positioned rows. A two-byte printable stream fixture repeats that path for `!!`: the byte-aligned renderer-control version combines two same-bucket compact entries (`glyph 0x20` at coords `0x0001` and `0x0002`) and renders both glyphs from one compact text object, while the initialized `LINE_PRINTER` HMI version derives `0x00120000` from resource longword `0x00480000` through the `0x10550` metric-conversion path and renders the second glyph from sub-byte coord `0x0202` / `$a001 = 0x12` at pixel x `34`. A mixed stream fixture for `ESC &k1G`, printable `!`, CR, printable `!` proves the line-termination-controlled CR+LF cursor transition before the second text object: the second glyph queues at compact coord `0x3b00` / `$a001 = 0x1b`, and the rendered rows show that shifted blank glyph rows clear the full one-byte span `x=11..18`; a page-record variant of the same stream queues both glyphs through `0x1387c`, bridges the full `0x26` object through `0x1edc6`, and renders identical rows. A mixed printable/reset fixture for `!\x1bE` keeps the pre-reset compact text object renderable, then applies the reset publication path: pending text is flushed, the valid current page root is published and cleared, HMI is refreshed, and reset state is rebuilt; its page-record variant queues the glyph through `0x1387c`, bridges the full `0x26` object through `0x1edc6`, and renders the pre-reset rows. The same model covers the negative-left overflow branch: cursor x `10` plus source x-offset `-26` returns correction `0x00100000`, queues source x `32`, emits compact coord `0x0002`, and renders the glyph shifted 32 pixels right. A selected inline/downloaded fixture now models `0x14e24`/`0x14eb6` map construction for fixed records, `0x1393a` inline source-object construction, `0xd3b2` unflagged positioning, `0x12f2e` short queueing, page-record allocation, and mode-0 rendering from the fixed-record bitmap; font payload-reader fixtures model `0x168dc` linear copies and `0x16942` split-plane copies, including `0x1a 0x58` control handling and continuation state; `0x172c0`/`0x16c14` fixtures model current-record scanning, existing-payload replacement with continuation clearing, free-slot insertion, candidate flag/counter/cursor updates, and the no-slot budget-skip path; `0x170be`/`0x17108`/`0x17150`/`0x15a56`/`0x16df6` fixtures model low-24-bit payload lookup, current-record mark/unmark count transfers, assign-font-id normalization, and font-control dispatch suppression for parser mode `2`; `0x16fae`/`0x17362`/`0x17026`/`0x1719c` fixtures now model validation-table traversal, concrete predicate side effects, optional symbol-byte staging, staged type setup, allocation-size calculation, sparse header copying, payload-backed inline fixed-record map/render, and optional symbol-byte append offsets; synthetic `0xd3b2` fixtures still pin both context-metric branches and the left-overflow clear-to-zero behavior, then queue synthetic inline/downloaded short, page-record short, width-bit, segmented, and combined width+segmented compact payloads through `0x12f2e` and render synthetic `0x1f0d2` wide inline, `0x1f1f0` segmented inline, and `0x1f264` segmented-wide inline payload rows. The direct control-code fixtures pin the `ESC &k#G` mode bits, CR horizontal reset and optional LF, LF optional CR plus vertical advance, FF page-eject state, HT tab/clamp behavior, and BS HMI/previous-width behavior, plus `ESC &f#S` cursor-stack push/pop/clamp/bounds behavior, `ESC &l#C/#D/#E/#F` vertical layout conversion/reject/default behavior, `ESC *c#A/#B/#H/#V/#G/#P` rectangle size/fill selector/clip/queue behavior plus chained byte-stream selector-7 rule creation, solid, solid/patterned band-crossing, two-band HP-pattern page assembly, gray/HP pattern, and sub-byte HP-pattern rule rendering, `ESC &a#L/#M` margin conversion/reject/cursor-move behavior, and `ESC &a#C/#H/#R/#V` cursor-position conversion/relative/clamp behavior. Narrow byte-stream fixtures now drive the same model from actual PCL/control bytes: `ESC &k1G` plus CR, `ESC &k2G` plus LF, and `ESC &k0G` plus HT/BS. Synthetic `ESC E` byte-stream fixtures pin the valid-page-root publication path and missing-root clear path documented in `generated/analysis/ic30_ic13_esc_e_reset_flow.md`; they still need to be replaced with fixtures that start from parser-produced page objects. The segmented producer-modeled fixture uses `LINE_PRINTER` host byte `0x20`, mapped glyph byte `0x1f`, source glyph entry `0x0146b4`, height `0x0454`, selector word `0x2000`, and bucket/segment entries from `64/8` down to `0/0`; this pins the `0x12f2e` producer encoding for the `0x1f1f0` render mode. A firmware-scanned built-in target check finds 420 tall table targets across 24 records, all with delta `0`, mode `0`, and width `74`, so the verified built-in resources do not provide a normal bitmap-entry fixture for rendering `0x1f1f0`. The decoded real glyph render fixtures cover mode-1 render spans 1, 2, and 4.

This is still not enough for pixel-perfect reproduction by itself. The next unresolved step is to replace fixture-only source/bucket/page-root states with parser-produced page objects and compare the finalized page/control records, replace the selected inline fixed-record memory with records populated by the real font-download parser, then replace the producer-modeled text/raster bucket objects with page objects captured or reproduced from the full parser/imaging path. Raster coverage still needs a full live-parser `ESC *t#R` / `ESC *r#A` / `ESC *b#W` fixture through `0x121cc` / `0x105d0`. In parallel, the renderer still needs a real bitmap-entry fixture for `0x1f1f0`/`0x1f264` and broader complete glyph-row fixtures for wide/non-mode-1 cases. The firmware-scanned built-in tables checked so far do not expose a mode-2 glyph that would exercise the `A3` trailing-plane row-copy path.

## Rejected Compositor Lead

The `0x78287c` / `0x7827b8` / `0x7828a8` path is not the page-object compositor. It is a font/resource candidate selector.

Why this lead is rejected for raster/page imaging:

- `0x1a2e4` initializes candidate-list counts `0x782790..0x78279e` and candidate-list pointers `0x7827a0..0x7827b4`.
- `0x1a616` scans resource address ranges and looks for resource records such as `HEAD`, `FONT`, `TABL`, `tabl`, and `DUMY`.
- `0x1a9be` classifies font resources and updates the candidate-list counts/pointers.
- `0x1569c` copies one font candidate-list pointer/count pair into `0x78287c` / `0x7827b8`.
- `0x14398`, `0x1440c`, and `0x14c64` select and snapshot current font-resource candidates, updating font range/state tables around `0x783132..0x78313c`.

This path is still important for text rendering and built-in font selection, but it does not consume the page-root raster/rectangle queues described above.

Other checked leads:

- `ESC E` reaches page imaging through reset helper `0xcc70`, documented in `generated/analysis/ic30_ic13_esc_e_reset_flow.md`: it calls text flush helper `0xf34a`, page-root finalizer `0xff1e`, and active record wait helper `0x9ac2` before resetting environment/raster/parser state. This makes software reset a page boundary that can finalize a partial page before clearing `0x78297a`.
- `0xff1e` finalizes or resets the current page root, tests page-root flags at `root+0x14`, calls parser/scheduler helpers, updates root state fields, and can clear `0x78297a`. It does not walk queue roots `+0x1c`, `+0x24`, or `+0x28`.
- Direct `0x78297a` references are now indexed in `generated/analysis/ic30_ic13_page_root_references.md`. The known direct references resolve to page-object producers, page-root initialization/finalization, font-slot handling at root `+0x2c`, or pool management. The bridge to rendering is instead through page/control records copied by `0x1edc6`; `generated/analysis/ic30_ic13_page_record_bridge.md` decodes the queue/list/context-slot copy contract.
- The later `0x196c4` lead scans page-root `+0x2c` font slots and calls `0x1ba6c` if a slot matches; it is not a bucket-chain consumer.
- `0x780ea6` and nearby aliases are the fixed 0x6c-byte page/control record pool used by allocator `0x9a9a`. They are not independent final image buffers.

## Next Targets

- Find or construct a real bitmap-entry fixture for `0x1f1f0` / `0x1f264`, replace producer-modeled text bucket fixtures with full parser-produced page-object payloads, then broaden beyond the four current mode-1 built-in examples.
- Replace the synthetic `ESC E` reset fixtures with parser-produced page-object fixtures so partial-page finalization and current-page-root clearing are proven from real queued objects.
- Broaden the narrow direct-control byte-stream fixtures into the full firmware parser path, then use those plus raster start/transfer behavior to finish naming cursor coordinate variables `0x782c8a` and `0x782c8e`.
- Finish rectangle handlers at `0x010898` and the width/height handlers around `0x010a40..0x010e68`; these now appear to share page-object storage with raster, not a direct framebuffer write.
- Compare the page geometry constants against manual printable-area diagrams and self-test output.
