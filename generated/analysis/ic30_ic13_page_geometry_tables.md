# IC30/IC13 Page Geometry Lookup Tables

The lookup routines at `0x009d16`, `0x009d4e`, `0x009d86`, and `0x009dbe` mask
the page-code argument with `0x7f` and accept indexes `0..10`. Values are
decoded as big-endian words from the firmware image. Table names are
provisional until each consumer is fully traced.

| Internal index | PCL mapping note | a112 / `0x9d16` | a128 / `0x9d4e` | a13e / `0x9d86` | a154 / `0x9dbe` |
| ---: | --- | ---: | ---: | ---: | ---: |
| 0 | default/legacy; also PCL 80 maps to internal `0x88`, masked here to 8 | 2400 | 3180 | 2550 | 3300 |
| 1 | PCL page size 26 | 2338 | 3389 | 2480 | 3507 |
| 2 | PCL page size 2 | 2400 | 3180 | 2550 | 3300 |
| 3 |  | 2007 | 2917 | 2149 | 3035 |
| 4 |  | 1500 | 2430 | 1642 | 2548 |
| 5 | PCL page size 3 | 2400 | 4080 | 2550 | 4200 |
| 6 | PCL page size 1 | 2025 | 3030 | 2175 | 3150 |
| 7 | PCL 81 maps to internal `0x87`, masked here to 7 | 1087 | 2730 | 1237 | 2850 |
| 8 | PCL 80 maps to internal `0x88`, masked here to 8 | 1012 | 2130 | 1162 | 2250 |
| 9 | PCL 90 maps to internal `0x89`, masked here to 9 | 1157 | 2480 | 1299 | 2598 |
| 10 | PCL 91 maps to internal `0x8a`, masked here to 10 | 1771 | 2586 | 1913 | 2704 |

## Manual Logical-Dimension Cross-Check

The Technical Reference figure values in `notes/pcl4-language.md` match the
ROM logical page dimensions as follows: `0x9d16` is portrait logical width,
`0x9dbe` is portrait logical length, `0x9d4e` is landscape logical width, and
`0x9d86` is landscape logical length.

| Paper | PCL | Index | Portrait W | Portrait L | Landscape W | Landscape L | Result |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Executive | 1 | 6 | 2025 / 2025 | 3150 / 3150 | 3030 / 3030 | 2175 / 2175 | match |
| Letter | 2 | 2 | 2400 / 2400 | 3300 / 3300 | 3180 / 3180 | 2550 / 2550 | match |
| Legal | 3 | 5 | 2400 / 2400 | 4200 / 4200 | 4080 / 4080 | 2550 / 2550 | match |
| A4 | 26 | 1 | 2338 / 2338 | 3507 / 3507 | 3389 / 3389 | 2480 / 2480 | match |
| Monarch | 80 | 8 | 1012 / 1012 | 2250 / 2250 | 2130 / 2130 | 1162 / 1162 | match |
| COM-10 | 81 | 7 | 1087 / 1087 | 2850 / 2850 | 2730 / 2730 | 1237 / 1237 | match |
| DL | 90 | 9 | 1157 / 1157 | 2598 / 2598 | 2480 / 2480 | 1299 / 1299 | match |
| C5 | 91 | 10 | 1771 / 1771 | 2704 / 2704 | 2586 / 2586 | 1913 / 1913 | match |

- Result: all supported `ESC &l#A` page-size values with manual figure entries
match the ROM logical page dimensions.

## Printable-Area Margin Cross-Check

The same four ROM tables also recover the manual printable-area margins. In
portrait, `0x9d86 - 0x9d16` gives the horizontal margin sum and `0x9dbe -
0x9d4e - 60` gives the bottom margin. In landscape, `0x9dbe - 0x9d4e` gives
the horizontal margin sum and `0x9d86 - 0x9d16 - 50` gives the bottom margin.

| Paper | Portrait H Sum | Portrait Bottom | Landscape H Sum | Landscape Bottom | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| Executive | 150 / 150 | 60 / 60 | 120 / 120 | 100 / 100 | match |
| Letter | 150 / 150 | 60 / 60 | 120 / 120 | 100 / 100 | match |
| Legal | 150 / 150 | 60 / 60 | 120 / 120 | 100 / 100 | match |
| A4 | 142 / 142 | 58 / 58 | 118 / 118 | 92 / 92 | match |
| Monarch | 150 / 150 | 60 / 60 | 120 / 120 | 100 / 100 | match |
| COM-10 | 150 / 150 | 60 / 60 | 120 / 120 | 100 / 100 | match |
| DL | 142 / 142 | 58 / 58 | 118 / 118 | 92 / 92 | match |
| C5 | 142 / 142 | 58 / 58 | 118 / 118 | 92 / 92 | match |

- Result: all supported `ESC &l#A` page-size values recover the manual
printable-area margin sums and bottom margins: match.

## Consumers

- `height_or_vertical_extent` @`0x00a112`: read by `0x009d16`, stored at
`0x782db4` by `ESC &l#A`.
- `width_or_horizontal_extent` @`0x00a128`: read by `0x009d4e`, stored at
`0x782db2` by `ESC &l#A`.
- `landscape_margin_table` @`0x00a13e`: read by `0x009d86`; used when
orientation byte `0x782da3` is nonzero.
- `portrait_margin_table` @`0x00a154`: read by `0x009dbe`; used when
orientation byte `0x782da3` is zero.
- `ESC &l#A` handler `0x00fc74` maps PCL page-size values `1`, `2`, `3`, `26`,
`80`, `81`, `90`, and `91` to internal page codes, writes `0x782da2`, stores
width at `0x782db2` through `0x009d4e`, stores height at `0x782db4` through
`0x009d16`, and then recomputes orientation-dependent extents.
- `ESC &l#O` handler `0x010220` accepts only absolute values `0` and `1`,
writes orientation byte `0x782da3`, calls the same margin/extent helpers, and
reloads four orientation threshold words through `0x0103ea`;
`tools/render_fixture_harness.py` now drives chained `ESC &l1a1O` through
page-size handler `0xfc74` and orientation handler `0x10220`.
- `ESC &l#D` handler `0x00c992` takes absolute lines-per-inch, treats `0` as
`12`, accepts only `1,2,3,4,6,8,12,16,24,48`, converts to packed line advance
as `3600 / LPI` twelfths, rejects values beyond `0x782dba`, stores `0x783160`,
sets `0x782ee1`, and refreshes pending vertical cursor `0x782c8e = 0x782dce +
VMI * 18 / 25` when text is pending.
- `ESC &l#C` handler `0x00cb00` takes absolute VMI in 1/48-inch units with
fractional support, rejects integer parts above `0x150` or converted values
beyond `0x782dba`, stores `0x783160`, refreshes pending vertical cursor with
the same `VMI * 18 / 25` offset, and sets `0x782ee1` only when the converted
VMI is nonzero.
- `ESC &l#E` handler `0x00ece2` scales top margin lines through current VMI,
rejects zero-VMI or positions at/beyond `0x782dba`, stores `0x782dce =
top_margin - 0x782dbe`, recomputes default text-length bottom through helper
`0xea16`, refreshes pending vertical cursor, then calls `0xfe54` and
`0x12b96`.
- `ESC &l#F` handler `0x00ea9e` scales text length lines through current VMI,
rejects zero-VMI and lengths beyond the remaining page after current top
margin, stores `0x782dd2 = 0x782dce + text_length`, and uses helper `0xea16`
to restore the default text-length bottom when the parameter is zero.
- `0x009e56` computes `(0x051f - floor(argument / 2)) mod 16` through signed
remainder helper `0x033238`; `ESC &l#A` feeds it the `0x782db4` table value
and stores the result at `0x782dc0`.
- Coordinate helpers at `0x0104d8..0x010550` convert between a packed
12-subunit fixed-point form and integer coordinates; raster code uses these
helpers around `0x0105d0..0x010758`.
