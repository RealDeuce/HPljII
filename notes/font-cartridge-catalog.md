# Font Cartridge Catalog

Sources:
the HP cartridge inventory at
<https://www.nefec.org/upm/printers/chp.htm>, retrieved 2026-07-15;
`92286PC.pdf` in the local working tree for the ProCollection manual.

## Scope

This is a catalog index for the bitmap font cartridges applicable to the
LaserJet II family. It is intended to answer which product supplies a
published face, metric, style, orientation, or symbol-set combination.

It is not a ROM inventory. The catalog gives human-facing names and aggregate
coverage, but not a cartridge ROM image, PCL font number, typeface ID, full
font descriptor, or glyph data. A catalog row therefore does not prove that
two identically named rows from different cartridges are byte-identical.

The catalog separates the later `C2050*` scalable cartridges from bitmap
cartridges. Scalable cartridges are not included here: the LaserJet II does
not implement the later scalable-font interface. The two front-panel slots
can expose only two cartridge windows at once; this is an index for a
collection to swap, not a claim that all listed resources can be installed
simultaneously.

## How To Read The Tables

The source identifies a font with a displayed tuple resembling:

`typeface, point/pitch, style, weight, orientation, symbol set`.

For catalog purposes, those fields distinguish advertised offerings. For PCL
or pixel-identity work, retain the cartridge product number and obtain the
cartridge ROM or a descriptor dump before treating two rows as the same
resource.

`P&L` means that the catalog advertises portrait and landscape versions.
Similarly, a footnote such as "all fonts available in Roman-8 and PC-8" is
coverage metadata, not a list of ROM addresses.

The PCL style request `ESC (s1S` asks for an italic font attribute. It does
not establish a firmware shear transform for the current glyph bitmap. The
formatter's resource records carry `ITALIC` and `SLANT` style values; physical
italic cartridge faces should be treated as separately stored font resources
until a cartridge dump proves otherwise. See
[font-sample-page.md](font-sample-page.md#row-text-helper-ledger).

## Bitmap Cartridge Sets

The 35 rows below are distinct catalog resource sets. `C2053A #C02` and
`92286Z` are one set: the catalog explicitly calls them identical.

| Product | Catalog name | Principal catalog content |
| --- | --- | --- |
| `92286A` | Courier 1 | Courier and light Line Printer |
| `92286B` | TmsRmn Proportional 1 | Helv, TmsRmn, light Line Printer |
| `92286C` | International | Courier and Line Printer international sets |
| `92286D` | Prestige Elite | Prestige Elite 10/12 |
| `92286E` | Letter Gothic | Letter Gothic 12/12 |
| `92286F` | TmsRmn 2 | Helv, TmsRmn, Line Printer |
| `92286G` | Legal Elite | Prestige Elite and Line Draw |
| `92286H` | Legal Courier | Courier, Prestige Elite, Line Draw |
| `92286J` | Math Elite | Prestige Elite mathematical symbol sets |
| `92286K` | Math TmsRmn | TmsRmn, TMS Math, TMS PI Font |
| `92286L` | Courier P&L | Courier and Line Printer in Roman-8 |
| `92286M` | Prestige Elite P&L | Prestige Elite 12/10 in Roman-8 |
| `92286N` | Letter Gothic P&L | Letter Gothic 12/12 in Roman-8 |
| `92286P` | TmsRmn P&L | TmsRmn 10-point in Roman-8 |
| `92286Q` | Memo 1 | Courier and Gothic |
| `92286R` | Presentations 1 | Presentation, Letter Gothic, PC Line, Line Draw |
| `92290S1` | Courier Document 1 | Courier with PC-8 and ECMA-94 Latin 1 |
| `92290S2` | TmsRmn/Helv Report 1 | TmsRmn and Helv report fonts |
| `92286T` | Tax 1 | Helv and Tax Line-Draw |
| `92286U` | Forms Portrait | Helv, Letter Gothic, Line Draw portrait fonts |
| `92286V` | Forms Landscape | Helv, Letter Gothic, Line Draw landscape fonts |
| `92286W1` | Bar Code 3 of 9/OCR-A | Code 39, OCR-A, Line Draw |
| `92286X` | EAN/UPC/OCR-B | EAN/UPC, OCR-B, Line Draw |
| `92286Y` | PC Courier 1 | Courier and Line Printer in PC Set 1/PC Extension |
| `92286PC` | ProCollection | 65-font standard document collection |
| `C2055A #C01` | Great Start | Letter Gothic and CG Times |
| `C2053A #C01` | WordPerfect | CG Times and Univers Desktop fonts |
| `C2053A #C02` / `92286Z` | Microsoft / Microsoft 1A | Helv, TmsRmn, Line Printer |
| `C2053A #C03` | Polished Worksheets | Letter Gothic, Prestige Elite, Presentation |
| `C2053A #C04` | Persuasive Presentations | Presentation, Helv Outline, Serifa |
| `C2053A #C05` | Forms, Etc. | Univers, Tax Line Draw, OCR-A |
| `C2053A #C06` | Bar Codes & More | Code 39, EAN/UPC, OCR-A/B, USPS ZIP |
| `C2053A #C07` | TextEquations | Prestige Elite and CG Times mathematics |
| `C2053A #C08` | Global Text | CG Century Schoolbook and CG Triumvirate |
| `C2053A #C09` | Pretty Faces | Microstyle, Hobo, Thunderbird, Signet, Dingbats |

The two `#C01` entries are different products. `C2055A #C01` is Great Start;
`C2053A #C01` is WordPerfect. Preserve the full base product number when
recording a cartridge.

### Verified `C2053A #C06` Dump

The local cartridge contains two `TC531001CP-F076` 128K x 8 mask ROMs. Each
anonymous package was read twice with matching results. Package B on the even
byte lane and package A on the odd byte lane produces a 256 KiB logical image
with SHA-256
`b5d002e54b3e572458770c7507958f48ce35a17e3f54f05b29042079314681c9`.

This lane order is established by firmware resource structure, not merely by
printable strings: the image starts with `HEAD`, contains 16 consecutive
type-`0x14` records, and terminates at `0x03f91c`. The package-B lane contains
the strings `ORA` and `ORB` at raw offsets `0x008462` and `0x009cc2`,
consistent with the cataloged OCR-A and OCR-B resources. Those lane-local
strings do not imply separate OCR-A and OCR-B packages; both occur in package
B while package A contains complementary bytes at the same logical records.
Dump provenance and raw hashes are in
[rom-dump-manifest.md](rom-dump-manifest.md#c2053a-c06-cartridge-resource-interleave).

The resource offset tables carry a two-byte name length followed by the
stored font name. Walking those tables gives this exact record inventory:

- `LtrGothic`: `0x0000a2`, `0x003076`, `0x0092fc`, `0x0298b2`, `0x02c826`,
  and `0x0319e0`;
- `OCR A`: `0x0106fc`; `OCR B`: `0x013614`;
- `Line Draw`: `0x016a86` and `0x038036`;
- `Code 3of9`: `0x019020` and `0x01d84e`;
- `UPC 13mil`: `0x020f4c`; `UPC 10mil`: `0x022cfa`;
- `USPS ZIP`: `0x024a44` and `0x03a664`.

`tools/extract_resource_fonts.py` converts the logical ROM into a versioned,
slot-independent emulator asset. The verified extraction contains 2,242
table slots: 1,729 mode-1 glyphs with 235,965 exact bitmap bytes and 513
explicitly absent slots. The JSON also retains the raw selection fields,
complete glyph-entry prefixes, signed glyph placement, dimensions, row
padding, per-payload hashes, and the complete zero/nonzero table layout.

### Verified `92286PC` Dump

The four local 128K x 8 package dumps interleave into two 256 KiB fixed-font
banks. Bank 0 uses `1818-4521` on the even lane and `1818-4519` on the odd
lane; bank 1 uses `1818-4522` even and `1818-4520` odd. The canonical
bank-0-then-bank-1 image has SHA-256
`8cdddc5f62b92a734dcabcdc0350d5814c2c0e669d4dc200ead92875133003b7`.
Raw hashes, repeated-read evidence, and bank hashes are in
[rom-dump-manifest.md](rom-dump-manifest.md#92286pc-procollection-cartridge).

The image supplies 65 real `FONT` records, followed by one `FONTDUMMY`
terminal in each bank. That is an exact ROM count, not the result of expanding
the manual's `P&L` abbreviations. The fixed record inventory is:

| Stored name | Count | Record offsets in combined image |
| --- | ---: | --- |
| `TmsRmn` | 14 | `0x000000`, `0x000340`, `0x0041de`, `0x00451e`, `0x0082d8`, `0x008618`, `0x00c462`, `0x00c7a2`, `0x00f4f2`, `0x00f832`, `0x0124bc`, `0x0127fc`, `0x01555e`, `0x01589e` |
| `LtrGothic` | 12 | `0x01796e`, `0x01a3b2`, `0x01cb9e`, `0x01f20a`, `0x02082e`, `0x02188a`, `0x040000`, `0x042bc4`, `0x045654`, `0x047f76`, `0x04959a`, `0x04a774` |
| `Pres Elite` | 12 | `0x022480`, `0x0227c0`, `0x024f58`, `0x025298`, `0x02780e`, `0x027b4e`, `0x02a0d2`, `0x02a412`, `0x04b28a`, `0x04d6e4`, `0x04fa4e`, `0x051d7e` |
| `Courier` | 16 | `0x02baee`, `0x02be2e`, `0x02ef22`, `0x02f262`, `0x032370`, `0x03502c`, `0x03536c`, `0x037728`, `0x037a68`, `0x039cb6`, `0x039ff6`, `0x053242`, `0x055d5e`, `0x05887c`, `0x05a954`, `0x05c9b8` |
| `Line Print` | 2 | `0x05e9e6`, `0x05ff14` |
| `Helv` | 9 | `0x061536`, `0x061876`, `0x066bc4`, `0x06a5fc`, `0x06e112`, `0x071988`, `0x07459e`, `0x077270`, `0x079d78` |

Each record has a 64-byte header and 96 eight-byte glyph entries. The ROM
selection paths consume header byte `+0x16`, symbol byte `+0x17`, typeface
byte `+0x18`, spacing byte `+0x19`, pitch word `+0x1a`, height word `+0x20`,
style byte `+0x26`, and signed weight byte `+0x27`. In this dump the family
IDs are `0` Line Print, `3` Courier, `4` Helv, `5` TmsRmn, `6` LtrGothic,
and `8` Pres Elite. Style is `0` upright or `1` italic; observed weight is
`0` medium or `3` bold. The extractor preserves those raw fields rather than
deriving resources by name.

The fixed glyph-table route is concrete in the formatter disassembly.
`0x14eb6` tests entry bytes `+0/+1` and the low 24 bits of longword `+4`;
`0x1f3a0..0x1f3d2` consumes those as row span, row count, and a bitmap offset
relative to the record. The extracted emulator asset contains all 6,240
slots, 6,175 glyph payloads, 65 absent slots, and 576,866 exact bitmap bytes.
Its SHA-256 is
`3cb93d9b474f2fc96d307521248c119603dddd5220f34c4ea57f7546079861f6`.

## Resident-Font Comparison

The built-in resource ROM is a separate source from all cartridge entries.
The verified resident records include upright medium and bold Courier at
12 point/10 cpi in portrait and landscape, plus Line Printer at
8.5 point/16.6 cpi. Their symbol sets are Roman-8, PC-8, PC-8
Danish/Norwegian, and ECMA-94 Latin 1. See
[resource-rom.md](resource-rom.md#character-to-glyph-index).

`92286Y` overlaps the PC-oriented symbol-set purpose and the Line Printer
metric, but it is not a copy of the resident set: its advertised Courier is
12 point/10 cpi and includes upright, bold, and italic faces.

## Follow-Up Evidence Needed

To promote catalog entries into exact PCL resource claims, preserve for each
physical cartridge:

- a byte-verified ROM dump and dump manifest;
- its PCL font directory and per-font descriptor fields;
- typeface IDs, symbol-set IDs, metrics, and glyph data; and
- the observed firmware scan/candidate-window records for the installed slot.

That evidence can then establish exact duplication, font selection precedence,
and pixel identity rather than relying on catalog labels.
