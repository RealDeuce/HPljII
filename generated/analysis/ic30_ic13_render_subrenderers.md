# IC30/IC13 Render Subrenderer Notes

Generated from focused renderer tables and instruction-level field use. This
names byte/word consumption and write patterns, not final high-level PCL
semantics.

## Glyph/Context Resolver `0x1f354`

The compact branch stores one render-record context longword into `0x783a2c`
before calling a compact renderer. `0x1f354` resolves a glyph/resource entry
from that context and the glyph index in `D1`.

| Context form | Test | Resulting fields |
| --- | --- | --- |
| offset-table form | bit 30 of `0x783a2c` set | clears high byte, uses context base plus word `+8` as offset table, indexes long offsets by `D1`, and reads glyph fields from the selected entry |
| fixed-record form | bit 30 clear | clears high byte, uses context base plus `0x40 + 8*D1`, reads inline glyph fields, and adds a long bitmap offset from that record |

Observed outputs from `0x1f354`: `A2` points at glyph bitmap data, `D1` is a
byte/word span count derived from glyph width, `D3` is a row/count field, and
`A3` may point at an alternate glyph plane/row when the glyph has more than
one row/plane.

## Compact Glyph Object Modes

The compact renderers all start with a word count at the object payload
pointer, then process that many entries. Each entry begins with a
glyph/resource index byte consumed by `0x1f354`; the remaining bytes differ by
mode.

| Selector bits from object byte `+4` | Target | Payload entry shape | Current write behavior |
| --- | --- | --- | --- |
| `0x00` | `0x1f034` | glyph byte, coordinate word | resolves glyph, computes destination with `0x1f3d4`/`0x1f414`, then uses table `0x1f08e` indexed by glyph span/count to copy glyph rows; if clipped across a band, repeats from `0x7810b4 + D2` |
| `0x10` | `0x1f0d2` | glyph byte, coordinate word | like `0x1f034`, but splits wide glyphs into full 16-pixel chunks via helper `0x2f27c` and a remainder through table `0x1f1ac`; uses scratch `0x783a40..0x783a48` |
| `0x20` | `0x1f1f0` | glyph byte, vertical/plane byte, coordinate word | adjusts glyph bitmap pointers by `byte*0x80`, clips height to `0x80`, then uses table `0x1f08e` |
| `0x30` | `0x1f264` | glyph byte, vertical/plane byte, coordinate word | combines the vertical/plane adjustment of `0x1f1f0` with the chunk/remainder loop of `0x1f0d2` |

## Compact Glyph Row Tables

Table `0x1f08e` is selected by the glyph span/count returned in `D5`; table
`0x1f1ac` is selected by a remainder count for wide glyph chunks.

### Table `0x1f08e`

| Index | Entry | Target |
| ---: | --- | --- |
| 0 | `0x01f08e` | `0x01f438` |
| 1 | `0x01f092` | `0x01fa5c` |
| 2 | `0x01f096` | `0x01fe76` |
| 3 | `0x01f09a` | `0x020290` |
| 4 | `0x01f09e` | `0x0207ac` |
| 5 | `0x01f0a2` | `0x020cc8` |
| 6 | `0x01f0a6` | `0x0212e4` |
| 7 | `0x01f0aa` | `0x021900` |
| 8 | `0x01f0ae` | `0x02201c` |
| 9 | `0x01f0b2` | `0x022738` |
| 10 | `0x01f0b6` | `0x022f54` |
| 11 | `0x01f0ba` | `0x023770` |
| 12 | `0x01f0be` | `0x024090` |
| 13 | `0x01f0c2` | `0x0249b0` |
| 14 | `0x01f0c6` | `0x0253d0` |
| 15 | `0x01f0ca` | `0x025df0` |
| 16 | `0x01f0ce` | `0x026910` |

### Table `0x1f1ac`

| Index | Entry | Target |
| ---: | --- | --- |
| 0 | `0x01f1ac` | `0x01f438` |
| 1 | `0x01f1b0` | `0x027430` |
| 2 | `0x01f1b4` | `0x027850` |
| 3 | `0x01f1b8` | `0x027d84` |
| 4 | `0x01f1bc` | `0x0283ba` |
| 5 | `0x01f1c0` | `0x0289f0` |
| 6 | `0x01f1c4` | `0x029126` |
| 7 | `0x01f1c8` | `0x02985c` |
| 8 | `0x01f1cc` | `0x02a092` |
| 9 | `0x01f1d0` | `0x02a8c8` |
| 10 | `0x01f1d4` | `0x02b1fe` |
| 11 | `0x01f1d8` | `0x02bb34` |
| 12 | `0x01f1dc` | `0x02c56e` |
| 13 | `0x01f1e0` | `0x02cfa8` |
| 14 | `0x01f1e4` | `0x02dae2` |
| 15 | `0x01f1e8` | `0x02e62e` |
| 16 | `0x01f1ec` | `0x02f27c` |

## Encoded Raster Span Modes

Routine `0x1f88e` enters with `A1` at bucket object `+4`; it skips object byte
`+4`, uses `object[5] & 0x03` as mode, reads word `object+6` into `D5`, reads
word `object+8` into `D1`, computes destination with `0x1f3d4`/`0x1f414`, then
sets `D2 = D5` before mode dispatch.

| Mode | Target | Payload consumed after object `+0x0a` | Write pattern |
| ---: | --- | --- | --- |
| 0 | `0x1f8da` | words | copies `D2` bytes as literal words from payload to consecutive destination words |
| 1 | `0x1f8e6` | bytes | expands each byte through 16-bit table `0x30914` and writes the same word to the current destination and one adjacent row/band destination |
| 2 | `0x1f920` | bytes, one skipped byte between table lookups | expands bytes through 32-bit table `0x30b14` and writes each longword to up to three row/band destinations selected by clipped row remainder state |
| 3 | `0x1f9c6` | bytes | expands each byte through two levels of table `0x30914` into a longword and writes it to four row/band destinations selected by clipped row remainder state |

## Encoded Raster Expansion Tables

The mode-1 and mode-3 byte expansion table begins at `0x30914`; mode 2 uses
longword table `0x30b14`. First entries are enough to identify the expansion
pattern.

| Table | Entry size | First 16 decoded values |
| --- | --- | --- |
| `0x30914` | word | `0x0000`, `0x0003`, `0x000c`, `0x000f`, `0x0030`, `0x0033`, `0x003c`, `0x003f`, `0x00c0`, `0x00c3`, `0x00cc`, `0x00cf`, `0x00f0`, `0x00f3`, `0x00fc`, `0x00ff` |
| `0x30b14` | long | `0x00000000`, `0x00000700`, `0x00003800`, `0x00003f00`, `0x0001c000`, `0x0001c700`, `0x0001f800`, `0x0001ff00`, `0x000e0000`, `0x000e0700`, `0x000e3800`, `0x000e3f00`, `0x000fc000`, `0x000fc700`, `0x000ff800`, `0x000fff00` |

## Row-Copy Helper Tables

Helper `0x2f27c` uses `D3` as an index into table `0x2f2ac`, after offsetting
`A1` and `A2` by `0x783a46`; its table targets are descending unrolled
row-copy routines that copy glyph words and advance by stride `0x783a1c -
0x0e`. Helper `0x1fa5c` and `0x1fe76` use similar table-driven byte/word row
writers. Generated fixture report `ic30_ic13_render_row_copy_fixtures.md`
decodes the main width table `0x1f08e`, the wide-glyph remainder table
`0x1f1ac`, and the `0x2f27c` chunk helper into synthetic A1/A2/A3 write
traces. Odd byte-width spans copy the trailing byte from `A3`; even byte-width
spans are all word copies from `A2`.

### Table `0x2f2ac` first 16 targets

| Index | Entry | Target |
| ---: | --- | --- |
| 0 | `0x02f2ac` | `0x02feb0` |
| 1 | `0x02f2b0` | `0x02fe9c` |
| 2 | `0x02f2b4` | `0x02fe88` |
| 3 | `0x02f2b8` | `0x02fe74` |
| 4 | `0x02f2bc` | `0x02fe60` |
| 5 | `0x02f2c0` | `0x02fe4c` |
| 6 | `0x02f2c4` | `0x02fe38` |
| 7 | `0x02f2c8` | `0x02fe24` |
| 8 | `0x02f2cc` | `0x02fe10` |
| 9 | `0x02f2d0` | `0x02fdfc` |
| 10 | `0x02f2d4` | `0x02fde8` |
| 11 | `0x02f2d8` | `0x02fdd4` |
| 12 | `0x02f2dc` | `0x02fdc0` |
| 13 | `0x02f2e0` | `0x02fdac` |
| 14 | `0x02f2e4` | `0x02fd98` |
| 15 | `0x02f2e8` | `0x02fd84` |

### Table `0x1fa70` first 16 targets

| Index | Entry | Target |
| ---: | --- | --- |
| 0 | `0x01fa70` | `0x01fe74` |
| 1 | `0x01fa74` | `0x01fe70` |
| 2 | `0x01fa78` | `0x01fe6c` |
| 3 | `0x01fa7c` | `0x01fe68` |
| 4 | `0x01fa80` | `0x01fe64` |
| 5 | `0x01fa84` | `0x01fe60` |
| 6 | `0x01fa88` | `0x01fe5c` |
| 7 | `0x01fa8c` | `0x01fe58` |
| 8 | `0x01fa90` | `0x01fe54` |
| 9 | `0x01fa94` | `0x01fe50` |
| 10 | `0x01fa98` | `0x01fe4c` |
| 11 | `0x01fa9c` | `0x01fe48` |
| 12 | `0x01faa0` | `0x01fe44` |
| 13 | `0x01faa4` | `0x01fe40` |
| 14 | `0x01faa8` | `0x01fe3c` |
| 15 | `0x01faac` | `0x01fe38` |

### Table `0x1fe8a` first 16 targets

| Index | Entry | Target |
| ---: | --- | --- |
| 0 | `0x01fe8a` | `0x02028e` |
| 1 | `0x01fe8e` | `0x02028a` |
| 2 | `0x01fe92` | `0x020286` |
| 3 | `0x01fe96` | `0x020282` |
| 4 | `0x01fe9a` | `0x02027e` |
| 5 | `0x01fe9e` | `0x02027a` |
| 6 | `0x01fea2` | `0x020276` |
| 7 | `0x01fea6` | `0x020272` |
| 8 | `0x01feaa` | `0x02026e` |
| 9 | `0x01feae` | `0x02026a` |
| 10 | `0x01feb2` | `0x020266` |
| 11 | `0x01feb6` | `0x020262` |
| 12 | `0x01feba` | `0x02025e` |
| 13 | `0x01febe` | `0x02025a` |
| 14 | `0x01fec2` | `0x020256` |
| 15 | `0x01fec6` | `0x020252` |
