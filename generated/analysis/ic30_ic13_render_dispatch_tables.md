# IC30/IC13 Render Object Dispatch Tables

Generated from literal dispatch tables and confirmed producer/consumer
instructions in the firmware image. Field names are provisional, but the
branch conditions and table targets are direct code facts.

## Bucket Object Class Branch at `0x1efc2`

The bucket walker loads a bucket object, advances `A1` to object offset `+4`,
masks byte `+4` with `0xc0`, and dispatches as follows.

| Object byte `+4` high bits | Branch | Current role |
| --- | --- | --- |
| `0x00..0x3f` | `bsr 0x1effe` | compact object; byte `+4` bits `0x10/0x20` select table `0x1f024`; byte `+5` low nibble selects render-record context slot `+0x24 + 4*n` |
| `0x40..0x7f` | `jsr 0x1f812` | segment-list object |
| `0x80..0xff` | `jsr 0x1f88e` | encoded-span object; raster rows are born with byte `+4 = 0x80` |

`tools/render_fixture_harness.py` now has an executable `0x1efc2` bucket-chain
fixture that selects render-record bucket word `+0x10`, converts it to a
`+0x18` bucket-array slot offset, and pins the compact, segment-list, and
encoded-span branch targets plus the compact/encoded subtable entries.

## Segment-List Bucket Renderer `0x1f812`

The `0x40..0x7f` bucket class enters `0x1f812` with `A1` pointing at object
byte `+4`. The routine skips to object word `+6` for an entry count, then
consumes six bytes per entry: coordinate word, a row-count byte whose low
nibble becomes `D2`, one skipped byte, and a width/mask word. Helper `0x1f836`
decodes the coordinate through `0x1f3d4`, converts the width/mask word into a
full-word count plus a trailing mask from table `0x308f2`, and `0x1f862`
writes full `0xffff` words plus that trailing mask for each row.
`tools/render_fixture_harness.py` now has an executable `0x1f812` fixture that
renders one counted segment-list span through this layout and verifies the ROM
mask table value.

## Compact Bucket Sub-Dispatch Table `0x1f024`

Selected by `(object[4] & 0x30) >> 2`, which is a byte offset into a longword
table.

| Selector | Table entry | Target |
| --- | ---: | --- |
| `object+4 & 0x30 == 0x00` | `0x01f024` | `0x01f034` |
| `object+4 & 0x30 == 0x10` | `0x01f028` | `0x01f0d2` |
| `object+4 & 0x30 == 0x20` | `0x01f02c` | `0x01f1f0` |
| `object+4 & 0x30 == 0x30` | `0x01f030` | `0x01f264` |

## Render-Record `+0x1c` List Dispatch Table `0x1f4a0`

Routine `0x1f446` walks render-record list `+0x1c`, filters by the current
band, then uses `object[5] & 0x0f` to select this table.

| `object[5] & 0x0f` | Target |
| ---: | --- |
| 0 | `0x01f4e0` |
| 1 | `0x01f4e0` |
| 2 | `0x01f4e0` |
| 3 | `0x01f4e0` |
| 4 | `0x01f4e0` |
| 5 | `0x01f4e0` |
| 6 | `0x01f4e0` |
| 7 | `0x01f596` |
| 8 | `0x01f4e0` |
| 9 | `0x01f4e0` |
| 10 | `0x01f4e0` |
| 11 | `0x01f4e0` |
| 12 | `0x01f4e0` |
| 13 | `0x01f4e0` |
| 14 | `0x01f4e0` |
| 15 | `0x01f4e0` |

## Encoded-Span Sub-Dispatch Table `0x1f8ca`

Routine `0x1f88e` starts from bucket object `+4`, reads `object[5] & 0x03`,
and selects this table after setting up destination coordinates.

| `object[5] & 0x03` | Target |
| ---: | --- |
| 0 | `0x01f8da` |
| 1 | `0x01f8e6` |
| 2 | `0x01f920` |
| 3 | `0x01f9c6` |

## Producer-to-Renderer Mapping

| Producer | Queue/list | Selector fields written | Confirmed render path |
| --- | --- | --- | --- |
| `0x13070` / `0x13250` raster row objects | page-root `+0x1c` bucket array -> render-record `+0x18` | `object[4]=0x80`, `object[5]` is the low byte of the first `0x13250` argument sourced from raster-state word `+0x08`, `object[6]=capacity`, `object[8]=packed key`, payload at `+0x0a` | high-bit branch to `0x1f88e`, then table `0x1f8ca` |
| `0x12f2e` text/glyph bucket objects via `0x1387c` | page-root `+0x1c` bucket array -> render-record `+0x18` | word at `object+4` is the selector/key from `D5`; bits `0x1000`/`0x2000` become byte `+4` bits `0x10`/`0x20`; count word is at `+0x06`; entries start at `+0x08` | compact branch to `0x1effe`, then table `0x1f024` |
| `0x13386` / `0x133aa` rectangle/rule objects | page-root `+0x24` -> render-record `+0x1c` | `object[4]=0x782a7d`, `object[5] |= source[8]`, words `+6/+8/+0a` from packed key and dimensions; bridge copies `+0x0a` to `+0x0c` | list renderer `0x1f446`, then table `0x1f4a0` |
| `0x13520` / `0x136d2` second-mode rule/text-span objects | page-root `+0x28` -> render-record `+0x20` | `object[4]=0x782a7d`, `object[5]=source[1]`, words `+6/+8`; addressed fixture pins `+0` sorted links from `0x1381c` allocation; bridge copies `+8` to `+0x0a` and sets `+0x0c=1`, `+0x0d=8` | fixed-width/rule writer `0x1f756` / `0x1f7b0` |

`tools/render_fixture_harness.py` now has parser-derived raster state fixtures
for `0x10808` (`ESC *t#R`) and `0x1075a` (`ESC *r#A`), proving 300/150/100/75
dpi select encoded modes 0/1/2/3 before queueing a mode-0 transfer object. It
also has modeled raster command/data stream fixtures for `ESC *t300R` / `ESC
*r1A` / delayed `ESC *b4W`, `ESC *t150R` / `ESC *r0A` / delayed `ESC *b2W`,
`ESC *t100R` / `ESC *r0A` / delayed `ESC *b2W`, and `ESC *t75R` / `ESC *r0A` /
delayed `ESC *b2W` bytes that record handler `0x0105d0`, ensure the modeled
page root through `0x10084` before queued transfers, queue mode-0/1/2/3
objects, bridge the `ESC *b4W` page-record object through `0x1edc6`, and
render the literal, two-row, three-row, and four-row expansions; the primary
300-dpi stream now has a cross-boundary check tying the ROM parser handlers
and `0x12218` restore to the modeled payload offset, page-root allocation,
queued object, bridge, rendered row, and row counter, and the same bytes are
fetched through the modeled `0xa904` ring source before reaching that
parser/object/render boundary; the 150/100/75-dpi streams now have the same
ROM parser-handler, restored-record, payload-offset, queued-object, and
rendered-row boundary for modes 1/2/3; the `ESC *t300R` / `ESC *r0A` / `ESC
*b4W` edge stream ties the parser/restore path to capped queueing and
beyond-extent drain/no-row-advance transfer gates; a separate `ESC *t300R` /
`ESC *r0A` stream with two consecutive uppercase `ESC *b2W` payloads now has a
ROM parser trace for the independent restored records and payload offsets
while verifying row_y `0 -> 1 -> 2` and page-record chain objects at coords
`0x1000` then `0x0000`. Same-group lowercase-final chaining fixtures cover
`ESC *t300r150R` and chained `ESC *b2w2W`; the lowercase `w` records the
delayed transfer and keeps parser mode in the `*b` family, then the uppercase
`W` triggers `0x12218` restore/dispatch and consumes the single raster
payload. The chained transfer stream now has a ROM parser trace proving the
uppercase `W` does not overwrite the lowercase `80 77 00 02 00 00` delayed
record before the payload reaches the modeled queued object and rendered row.
A bare `ESC *rB` stream proves handler `0x107fa` clears only raster active
state and allows a following `ESC *t150R` mode change. Raster row fixtures
also queue byte-aligned mode-0 object `00 00 00 00 80 00 00 04 00 01 f0 0f aa
55`, non-byte-aligned mode-0 object `00 00 00 00 80 00 00 02 04 01 c3 3c`,
mode-1 object `00 00 00 00 80 01 00 02 00 01 f0 0f`, byte-aligned mode-2
object `00 00 00 00 80 02 00 02 00 01 f0 0f`, non-byte-aligned mode-2 object
`00 00 00 00 80 02 00 02 04 01 f0 0f`, band-clipped mode-2 object `00 00 00 00
80 02 00 02 f0 01 f0 0f` with fallback-buffer continuation rows, and mode-3
object `00 00 00 00 80 03 00 02 00 01 f0 0f` through the `0x13070` / `0x13250`
/ `0x138de` shape, bridge the byte-aligned mode-0 object through `0x1edc6`,
and render the rows through `0x1f88e` / `0x1f8da`, `0x1f8e6`, `0x1f920`, and
`0x1f9c6`.
