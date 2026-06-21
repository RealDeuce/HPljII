# Resource ROM Notes

Sources: `generated/roms/ic32_ic15.bin`;
`generated/analysis/ic32_ic15_strings.txt`;
`generated/analysis/ic32_ic15_resource_markers.txt`;
`generated/analysis/ic32_ic15_font_records.md`;
`generated/analysis/ic32_ic15_resource_glyph_probe.md`;
`generated/analysis/ic30_ic13_font_context_bridge.md`;
`generated/analysis/ic30_ic13_text_glyph_index_flow.md`;
`generated/analysis/ic30_ic13_active_symbol_set_flow.md`;
`generated/analysis/ic30_ic13_symbol_set_patch_tables.md`;
`generated/disasm/ic30_ic13_font_resource_scan_01a2e4.lst`;
`generated/disasm/ic30_ic13_font_candidate_classify_01a9be.lst`;
`generated/disasm/ic30_ic13_font_candidate_activate_01569c.lst`;
`generated/disasm/ic30_ic13_font_candidate_filters_01519a.lst`;
`generated/disasm/ic30_ic13_active_object_dispatch_014ba4.lst`;
`generated/disasm/ic30_ic13_font_id_select_017708.lst`;
`generated/disasm/ic30_ic13_default_font_tables_01ab84.lst`;
`generated/disasm/ic30_ic13_symbol_set_handler_01be22.lst`;
`generated/disasm/ic30_ic13_font_update_common_00c580.lst`.

The `IC32,IC15` interleave is not the reset firmware pair. It begins
with a `HEAD` signature and contains repeated built-in font names and
dense offset tables. Treat it as the current source for built-in font
directories, metrics, and glyph data.

## Header

The first bytes reconstruct a readable resource header:

```text
HEAD ... Copyright (C) Hewlett-Packard Company, 1986
```

Firmware routine `0x0000041a` scans memory for the same `HEAD`
signature, so this is not just an incidental string. The scanner probes
`0x40000` windows, walks length-delimited records after `HEAD`, treats
null or `0xffffffff` records as chain terminators, and treats type
`0x000000be` as an executable handoff whose payload starts at
`record + 8` when the record length is greater than `7`. Lengths of `7`
or below report `D0 = 0xe0`, `D1 = 0x10` through helper `0x128c`.

The verified `IC32,IC15` image has `HEAD` at offset `0x000000`, then 24
typed records from `0x00004c` through `0x02e122`; the chain terminates
on a null record at `0x032f80`. The harness also pins the scanner's
boundary behavior: if the cumulative walked length crosses `0x40000`,
the next probe step becomes `0x80000` instead of the default `0x40000`.

At the end of the resource interleave, the chip tail markers overlap as
interleaved bytes:

```text
SSHH77--99223334--0011
```

That is consistent with IC32 carrying `SH7-9233-01` and IC15 carrying
`SH7-9234-01`.

## Font Name Markers

`COURIER` appears 16 times. Twelve of those hits currently look like
structured font headers; four appear to be embedded in bitmap/data
payloads because the expected header word is absent.

| Group | Offsets |
| --- | --- |
| 0 | `0x000410`, `0x000860`, `0x000cb0`, `0x001080` |
| 1 | `0x00a374`, `0x00a7c4`, `0x00ac14`, `0x00afe4` |
| 2 | `0x01a0dc`, `0x01a52c`, `0x01a97c`, `0x01ad4c` |
| 3 | `0x023848`, `0x023c98`, `0x0240e8`, `0x0244b8` |

Header-like `COURIER` offsets:

```text
0x000410 0x000860 0x000cb0
0x00a374 0x00a7c4 0x00ac14
0x01a0dc 0x01a52c 0x01a97c
0x023848 0x023c98 0x0240e8
```

Embedded/data-looking `COURIER` hits:

```text
0x001080 0x00afe4 0x01ad4c 0x0244b8
```

`LINE_PRINTER` appears 8 times. Six currently look like structured font
headers; two appear to be embedded/data hits.

| Group | Offsets |
| --- | --- |
| 0 | `0x0146a8`, `0x014afc`, `0x014f50`, `0x015324` |
| 1 | `0x02d86e`, `0x02dcc2`, `0x02e116`, `0x02e4ea` |

Header-like `LINE_PRINTER` offsets:

```text
0x0146a8 0x014afc 0x014f50
0x02d86e 0x02dcc2 0x02e116
```

Embedded/data-looking `LINE_PRINTER` hits:

```text
0x015324 0x02e4ea
```

The header-like records share these traits:

- the firmware record start is the even address immediately after the
  name/padding;
- the record begins with longword `0x00000014` or `0x00000015`;
- longword `record+4` is the scanner length for the small named records,
  such as `0x450` for the first two `COURIER` records;
- word `record+8` is the offset-table delta, normally `0x004a`;
- table entries are full 32-bit offsets relative to the selected record
  start.

For example, the first `COURIER` name starts at `0x000410`, but the
firmware-selected record starts at `0x000418`. Its firmware address is
`0x080418`, context longword is `0x44080418`, length is `0x450`, and its
offset table starts at `0x000462`. The first table entry is
`0x00007792`, which resolves to glyph entry `0x007baa` by adding the
selected record start.

The third header in each local group often has a larger length field,
such as `0x000092f8` at record start `0x000cb8`. These larger records
contain many relative table entries and should be treated as part of the
firmware-scanned font set, not as simple same-size repeats.

The first `LINE_PRINTER` name starts at `0x0146a8`; its firmware record
starts at `0x0146b4`, firmware address is `0x0946b4`, context longword
is `0x440946b4`, and its table starts at `0x0146fe`.

## Glyph/Bitmap Probe

The generated report
`generated/analysis/ic32_ic15_resource_glyph_probe.md` now follows the
same built-in resource scan as the firmware and probes each table
against the field layout consumed by renderer helper `0x1f354`.

Current confirmed record facts:

- the built-in resource window maps `IC32,IC15` file offset `N` to
  firmware address `0x80000 + N`;
- built-in font candidates set bit 30 in the selected context longword,
  selecting the `0x1f354` offset-table form;
- the first two `COURIER` records at record starts `0x000418` and
  `0x000868` each have length `0x450` and 253 nonzero relative table
  entries;
- the first two `LINE_PRINTER` records at record starts `0x0146b4` and
  `0x014b08` each have length `0x454` and 253 nonzero relative table
  entries;
- `COURIER` size-like words are `30x54` and `30x50`; `LINE_PRINTER`
  size-like words are `18x39` and `18x38`;
- glyph-entry headers now resolve directly through the firmware formula:
  byte `+4` is a bitmap delta, byte `+5` is a small mode/plane value,
  word `+6` is row count, and word `+8` is pixel width.

The executable harness now extracts deterministic metadata for all named
header-like built-in records in the verified resource window: twelve
`COURIER` records and six `LINE_PRINTER` records. The `COURIER` records
decode to pitch `1000` and height `1200`; the `LINE_PRINTER` records
decode to pitch `1666` and height `850`. The small full-table records
start at character `0x01` and have 253 nonzero entries. The larger
records start at character `0x21` and have 190 nonzero entries. The
first named `COURIER` record has context `0x44080418` and first glyph
entry `0x007baa`; the first named `LINE_PRINTER` record has context
`0x440946b4` and first glyph entry `0x018730`.

The same named-record summary now pins selection-facing metadata fields
consumed by firmware helpers. Byte `+0x20` is the class/orientation
selector used by `0x1a9be` partitioning and `0x1b060` default matching;
the named records split evenly between selector values `0` and `1`.
Byte `+0x21`, read by the `0x153c6` spacing filter, is `0` for every
named record. Symbols repeat as six records each for `0x0155`,
`0x0175`, and `0x000e`. Raw `+0x24/+0x26` pitch fields are
`0x0078/0x00` for `COURIER` and `0x0048/0x00` for `LINE_PRINTER`. Raw
`+0x28/+0x2a` height fields are `0x00c8/0x00` and `0x008d/0xab`.
Comparator bytes `+0x2f..+0x31` are `(0,0,3)` or `(0,3,3)` for
`COURIER`, and `(0,0,0)` for `LINE_PRINTER`.

First-nonzero named glyph entries also have their positioning fields
summarized against the `0xd824` model. Glyph-entry word `+0` is the
signed x offset added to the queued source x coordinate; word `+2` is
the signed y offset subtracted from the queued source y coordinate. For
the first named glyphs, bitmap delta is always `10` and mode is always
`1`. Selector `0` first glyphs have positive x offsets in the range
`1..10`; selector `1` first glyphs have negative x offsets in the range
`-31..-18`.

Example candidate entries from the probe:

- Context `0x4008004c`, glyph `0`, relative offset `0x0000103c`, entry
  `0x001088`, bitmap `0x001092`, height `32`, width `9`, render span
  `2`, sample bytes `1c 00 3e 00 3e 00 3e 00`.
- Context `0x44080418`, glyph `0`, relative offset `0x00007792`, entry
  `0x007baa`, bitmap `0x007bb4`, height `29`, width `28`, render span
  `4`, sample bytes `00 1f 80 00 00 ff f0 00`.
- Context `0x440946b4`, glyph `0`, relative offset `0x0000407c`, entry
  `0x018730`, bitmap `0x01873a`, height `16`, width `16`, render span
  `2`, sample bytes `03 c0 0f f0 38 1c 30 0c`.

`generated/analysis/ic32_ic15_builtin_glyph_payloads.md` and the local
JSON companion `generated/analysis/ic32_ic15_builtin_glyph_payloads.json`
now make that probe deterministic for the full verified built-in window.
The extractor walks all 24 firmware-scanned font records, resolves 5,310
nonzero offset-table entries, and emits 468,534 bytes of exact mode-1
bitmap payload data with per-glyph offsets, dimensions, render spans,
placement offsets, payload hashes, and hex payload bytes. The JSON stays
under ignored `generated/` output with the interleaved ROMs.
`generated/analysis/ic32_ic15_builtin_font_samples.md` consumes those
payloads directly for a `LASERJETII` smoke sample in first `COURIER`
and first `LINE_PRINTER`, producing stable row hashes
`8e004fa1e6351e909224c8ae5ddd7f4e0d96f47b413c2514f93cba8daaca4834`
and
`81e38bb45d5520c7a7f572a277371a55648b0b121ebd3c48f5e3db675dfed38d`.
That sample is only direct glyph composition; firmware cursor, baseline,
and self-test placement remain separate targets.
`generated/analysis/ic30_ic13_font_sample_page.md` now anchors the ROM
font-printout path that should replace the direct smoke sample: it finds
the font-list headers, source labels, style labels, and sample byte runs,
then shows that helper `0x1d12e` prints those bytes through normal
printable handler `0xd04a`. Its setup helper `0x1c5e8` installs the
selected resource through the same `0x782ee6` current-font context,
`0x14c64` map rebuild, `0xc428` page-root font-slot install, and forced
VMI/HMI defaults `0x0032` / `0x001e`.

The old high-word interpretation was wrong. The entries are not absolute
high words; they are full relative long offsets from the selected record
start. The selected context longword now maps directly to concrete
resource records and glyph-entry pointers; the text-object glyph index
and symbol-set patch mechanics are summarized below.

The firmware-side bridge to the renderer is now traced through the first
real glyph entries: selected candidate longwords are copied into
current-font context records at `0x782ee6` / `0x782ef6`, those
context-record pointers are installed in page-root `+0x2c` slots,
`0x1edc6` copies the slots to render-record `+0x24`, the compact glyph
renderer loads a selected slot into `0x783a2c`, and `0x1f354` resolves
the glyph table relative to the selected `IC32,IC15` record.

## Character to Glyph Index

The compact renderer does not index built-in font tables directly with
the incoming host byte. Routine `0x1393a` maps the original character
through one of two 256-byte tables:

| Selector | Map table | Context record |
| --- | --- | --- |
| `0x782f06 == 0` | `0x782f32` | `0x782ee6` |
| `0x782f06 != 0` | `0x783032` | `0x782ef6` |

The mapped byte is stored as text object word `+0x0a`; its low byte at
object `+0x0b` is later copied by `0x12f2e` into each compact payload
entry. That byte is the glyph index consumed by `0x1f354`.

For bit-30 offset-table resource contexts, `0x14c64` takes the selected
slot pointer from `0x7828a8`, handles a cache miss by updating the
primary or secondary range table at `0x783134` / `0x78313a`, records a
selected-font flag at `0x783132` / `0x783133`, calls `0x14d9c` to
initialize the active map from selected record words `+0x0e` and
`+0x10`, calls `0x14f16`, and snapshots state through `0x1440c`. The
concrete selected class-zero Roman-8 record `0x009fb0` has base range
`0x21..0xfe`; with active symbol `0x0005` (`0E`, HP Roman Extension),
the dispatcher narrows the range-table end to `0x007e`, patches map byte
`0x21` to glyph `0x80`, clears the upper half, and snapshots state at
`0x783148`. For bit-30-clear fixed-record contexts, the same dispatcher
writes selected record byte `+0x0e` directly to `0x783132` / `0x783133`,
calls `0x14e24` to rebuild the map by probing fixed records through
`0x14eb6`, then runs `0x14f16` and snapshots fixed-record state through
`0x1440c`; the executable synthetic selected-inline fixture maps host
`0x21` to glyph `1`, enables extended-half probing from `+0x0e`, and
snapshots inline byte `+8 = 1` at `0x783148`. The `0x16c14`-installed
`0x1719c` payload now exercises the bit-30 RAM-backed offset-table path
through `0x14d9c` / `0x15890`; the older bit-30-clear payload-backed
case remains a fixed-record isolation control through `0x14e24` /
`0x158be`. `0x14f16` applies symbol-set-specific remaps only when the
selected font's normalized symbol is `0x0115` (`8U`, Roman-8), using
active symbol-set words at `0x783144` / `0x783146`.

The generated `generated/analysis/ic30_ic13_symbol_set_patch_tables.md`
report decodes the `0x14fce` table into 18 patch records. Each record is
keyed by a PCL symbol-set code and Technical Reference name: ISO 2 IRV
(`2U`), ISO 4 United Kingdom (`1E`), ISO 25/69 French (`0F`/`1F`),
HP/ISO German (`0G`/`1G`), ISO 15 Italian (`0I`), ISO 14 JIS ASCII
(`0K`), ISO 57 Chinese (`2K`), ISO 10/11 Swedish (`3S`/`0S`), HP/ISO
Spanish (`1S`/`2S`/`6S`), ISO 16/84 Portuguese (`4S`/`5S`), and ISO
60/61 Norwegian (`0D`/`1D`). The patch records contain byte pairs
applied as `map[dst] = map[src]`. Special active values `0x0005` (`0E`,
HP Roman Extension) and `0x0015` (`0U`, ISO 6 ASCII) use hard-coded
half-map behavior instead of a patch table.

The generated `generated/analysis/ic30_ic13_active_symbol_set_flow.md`
report traces those active words back to the host parser. `ESC (` uses
setup handler `0x1201e` and slot word `0`; `ESC )` uses `0x12008` and
slot word `1`; both terminal paths call `0x120be`, which calls `0x1be22`
and then the common refresh `0xc580`. For normal symbol-set finals,
`0x1be22` computes the PCL word as
`(parameter << 5) + final_byte - 0x40`, so `ESC (8U` becomes requested
word `0x0115` at `0x782ef4`, while the secondary slot uses `0x782f04`.
Final `X` restores the previous requested symbol word and calls
`0x17708` for font-ID selection. Final `@` uses a numeric subtable: the
manual-documented `3@` takes the default-font path, while
firmware-supported `@0..@2` read/copy requested words from the
four-entry table at `0x782f1c/20/24/28`. The similar table at
`0x782f0c/10/14/18` is built separately and consumed by `0x156de` only
as a candidate-selection fallback. Font activation at `0x156de` turns
requested words into active selected words at `0x783144` / `0x783146`,
after fallback/default handling and candidate compatibility checks. The
executable harness now drives `ESC (2U` and `ESC )0E` through this
stream model, proving active words `0x0055` and `0x0005` before applying
the ISO 2 IRV patch table and HP Roman Extension half-map rule to the
`LINE_PRINTER` base map. It also traces the same byte stream through ROM
parser table `0x11774`, proving primary setup `0x1201e`, secondary setup
`0x12008`, and terminal handler `0x120be` before those active map
patches are applied. A companion trace drives `ESC (7X`, `ESC )0@`,
`ESC (1@`, `ESC )2@`, `ESC (3@`, and `ESC )3@` through the same parser
terminal path, then checks the `X` font-ID call boundary and `@0..@3`
table/copy/default-font target selection. Direct `0x17708` fixtures now
cover successful font-ID selection for both bit-30 built-in and
bit-30-clear inline/downloaded current records, including the `0x172c0`
scan, `0x1b4c0` candidate-slot lookup, class-byte check, active-word
write through `0x15890` or `0x158be`, `0x1b2fe`, and `0x14c64`
dispatch. A table-builder fixture now pins `0x1ac0a`
current-candidate and synthesized writes to
`0x782f1c/20/24/28` plus `0x1af36` fallback writes to
`0x782f0c/10/14/18`; candidate-search fixtures pin `0x1b250`
disabled/resolved/remapped current-default results, `0x1b50e`
fast-probe/two-pass resolver classes and Roman-8 duplicate ordinal
behavior, `0x1ab84` synthesized search, `0x1ad66` range-1, range-2, and
`0x1ae7e` fallback control flow, plus `0x1bbfe` / `0x1b060` helper
behavior from candidate record fields. The `0x1b060` fallback path now
also runs against real scanned built-in class windows: class zero selects
record `0x00004c` by Roman-8 fallback for requested `0x0005`, and class
one selects record `0x01a984` by exact symbol `0x000e`. The same scanned
windows now feed mode-3 `0x1b50e`: ordinal 1 selects slot `0x782354` /
record `0x08004c`, a non-Roman-8 duplicate ordinal 2 returns requested
word `0x0005`, and current-slot duplicate suppression advances to slot
`0x782358` / record `0x080418`. The same real windows feed `0x1ab84`
after its orientation flip, selecting record `0x00004c` by Roman-8
fallback and record `0x01a984` by exact `0x000e`; real `0x1b50e`
results also feed `0x1b250`, where `0x00004c` maps to slot `0x782354`
after boundary `0x7827ac` and `0x01a984` maps to slot `0x782330` before
it. A real-backed `@0`/`@1`/`@2`/`@3` caller stream now routes through
ROM terminal handler `0x120be` and consumes those table/default-font
words through the same default-table/copy/default-font subdispatch.

This makes the current renderer identity
`(context longword, mapped glyph byte)`. For example, the unnamed
built-in record at context `0x4008004c` has a base range `0x21..0xfe`,
so before `0x14f16` patching, host byte `0x21` maps to glyph index `0`.
The first `COURIER` and `LINE_PRINTER` records have base ranges
`0x01..0xff`, so their pre-patch base mapping starts at byte
`0x01 -> glyph 0`.

## Extraction Targets

1. Extend the modeled `HEAD` scanner beyond the verified built-in window
   if cartridge or external resource images become available.
2. Finish naming the firmware-scanned record metadata fields rather than
   relying on string labels alone.
3. Decide how to document the undocumented but parser-exposed `@0..@2`
   table/copy variants. The default-font candidate and caller path is
   now real-record backed through `0x1b250`, `0x1b50e`, `0x1ab84`,
   `0x1b060`, and the ROM `0x120be` terminal path.
4. Replace the host-fetched font-control, descriptor, resource-payload,
   and downloaded-character boundaries with a full live parser-state run
   that populates current records/source objects; then replace
   producer-modeled text bucket fixtures with full parser-produced
   page-object payloads. The current boundary coverage already chains
   fetched `ESC *c4660d37e5F` state into fetched `ESC )s0W`,
   `ESC )s80W`, and `ESC )s2193W` streams, with fetched `ESC )s2193W`
   now crossing `0x1ed84`/`0x1ef6a`; the fetched
   `ESC )s18W` payload-control path now crosses `0x1edc6` and
   `0x1ed84`/`0x1ef6a` before wide glyph rendering, and a combined
   fetched font-control / downloaded-character / printable stream now
   drives the installed downloaded glyph into segmented page-record
   buckets before `0x1ed84`/`0x1ef6a` rendering.
5. Finish semantic naming of the remaining built-in metadata fields,
   especially the ambiguous header size words now extracted for every
   named `COURIER` and `LINE_PRINTER` record. The first-glyph placement
   offsets are now pinned through the `0xd824` path, but the header-level
   baseline semantics still need broader correlation.
6. Model the surrounding `0x1c334` font-printout loop far enough to
   produce parser/page objects from the ROM sample byte runs, then
   compare those rows against a known printed/self-test sample and
   correlate the remaining baseline/header fields against observed
   placement.

These are high-value targets for pixel-perfect output because the
manuals describe PCL behavior but do not provide the built-in font
rasters and exact per-glyph metrics.

## Firmware Font Candidate Lists

The routines around `0x1a2e4..0x1ab82` build candidate lists for
font/resource selection, not page raster compositing.

`0x1a2e4` initializes the candidate-list state:

- clears counts `0x782790`, `0x782792`, `0x782794`, `0x782796`,
  `0x782798`, `0x78279a`, `0x78279c`, and `0x78279e`;
- sets list cursors `0x7827a0`, `0x7827a4`, `0x7827a8`, `0x7827ac`,
  `0x7827b0`, and `0x7827b4` to a shared base at `0x782324`;
- sets resource scan bounds at `0x78288c` / `0x782890`, initially
  `0x00080000..0x000ffffe`, then calls `0x1a616`.

`0x1a616` scans resource regions, using `0x782884` as the current scan
cursor. It recognizes or skips records with signatures including `HEAD`,
`FONT`, `TABL`, `tabl`, and `DUMY`. `0x1a9be` classifies accepted font
records, sets flags on the candidate object returned by `0x1bc38`, and
increments the candidate-list counts/cursors according to
orientation/class and address range.

`0x1a9be` uses the caller argument to distinguish two accepted-record
shapes. For `FONT` records (`arg == 0`), byte `+0x32` supplies candidate
flag bits 28..29 and high-byte flags `0x40000000` / `0x04000000` are
cleared. For records reached through the `HEAD`/typed path (`arg != 0`),
byte `+0x0d` supplies bits 28..29, high-byte flag `0x40000000` is set,
and `0x04000000` mirrors whether byte `+0x0c == 2`. It always increments
total count `0x78278e`.

The class byte then partitions the shared pointer-list window:

- Class `1`, any accepted address: increments `0x782790`; advances no
  cursors by itself.
- Class `1`, `0x080000..0x0ffffe`: increments `0x782792`; advances
  `0x7827a4`, `0x7827a8`, `0x7827ac`, `0x7827b0`, and `0x7827b4`.
- Class `1`, `0x200000..0x5ffffe`: increments `0x782794`; advances
  `0x7827a8`, `0x7827ac`, `0x7827b0`, and `0x7827b4`.
- Class `0`, any accepted address: increments `0x782798`; advances no
  cursors by itself.
- Class `0`, `0x080000..0x0ffffe`: increments `0x78279a`; advances
  `0x7827b0` and `0x7827b4`.
- Class `0`, `0x200000..0x5ffffe`: increments `0x78279c`; advances
  `0x7827b4`.

Other class values are retained in the total count but do not advance
these class/range windows. In the decoded `0x1a9be` body,
initializer-cleared counters `0x782796` and `0x78279e` are not
incremented; similarly named increments in the harness belong to
downloaded-font bookkeeping rather than this built-in resource scan
path.

For the verified `IC32,IC15` built-in resource image, the concrete
`HEAD`-path scan accepts 24 records: twelve class `0` records and twelve
class `1` records, all in the low built-in resource window
`0x080000..0x0ffffe`. The resulting counter state is total
`0x78278e = 24`, class-one low/range `0x782792 = 12` / `0x782794 = 0`,
and class-zero low/range `0x78279a = 12` / `0x78279c = 0`; final cursor
windows are `0x7827a0 = 0x782324`, `0x7827a4 = 0x782354`,
`0x7827a8 = 0x782354`, `0x7827ac = 0x782354`, `0x7827b0 = 0x782384`, and
`0x7827b4 = 0x782384`.

`0x1569c` activates one of those windows. If `0x782da3 == 0`, it copies
class-zero pointer/count `0x7827ac` / `0x782798` into `0x78287c` /
`0x7827b8`, giving pointer `0x782354` and count `12` for the verified
built-ins. Otherwise it copies class-one pointer/count `0x7827a0` /
`0x782790`, giving pointer `0x782324` and count `12`. It then sets the
high active bit `0x80000000` in each selected list entry before later
filters clear that bit on rejected entries.

Current candidate-list state:

| RAM | Role |
| --- | --- |
| `0x782324` | shared candidate pointer-list base |
| `0x782790..0x78279e` | candidate-list counts |
| `0x7827a0..0x7827b4` | candidate-list cursors / list starts |
| `0x782884` | resource scan cursor |
| `0x78288c` / `0x782890` | scan start/end |
| `0x78287c` | active candidate-list pointer selected from one of the lists |
| `0x7827b8` | active candidate-list count |
| `0x7828a8` | selected candidate slot pointer |

`0x156de` then filters the active list against current font criteria.
For symbol sets, it reads requested words from `0x782ef4` or `0x782f04`,
uses `0x783f00` as the initial normalized-symbol flag, compares
candidate words returned by `0x15890` / `0x158be`, accepts the small
compatibility table at `0x15840`, and falls back through remembered
words `0x782f08` / `0x782f0a` and then the `0x782f0c..0x782f18` table.
After selecting the active word, it writes `0x783144` or `0x783146`,
makes a second pass over the active list, clears the active bit on
rejected entries, moves `0x78287c` to the first survivor, and shrinks
`0x7827b8`. The verified built-in class windows expose `+0x22` symbol
words `0x0115`, `0x0155`, `0x0175`, and `0x000e` repeating; a primary
`0x0115` filter keeps the three Roman-8 entries in the selected class
window. A parser-derived miss now drives the fallback side:
`ESC )1234U` reaches `0x120be`, produces requested word `0x9a55`, misses
all class-one candidates, then falls through to fallback-table word
`0x000e` and keeps the three secondary symbol `0x000e` records.

`0x14398` chooses the selected active slot. It seeds the first
still-negative active slot, then calls comparator `0x13c06` for each
later active slot and replaces the current choice only when the
comparator returns `1`. The comparator first ranks resource windows as
low built-in, extension, then RAM/download; same-class built-ins fall
through to `0x1428c`, which compares decoded height, byte `+0x2f`,
signed byte `+0x30`, then byte `+0x31`. Over the concrete class-zero
Roman-8 survivors, the harness now selects slot `0x782364` / record
`0x009fb0`: tuple `[1200, 0, 3, 3]` beats the first survivor
`[1200, 0, 0, 3]`, while the later 16.66-pitch survivor has lower tuple
`[850, 0, 0, 0]`.

That chooser-only result is intentionally isolated. In the full
`0x13eb8` refresh for parsed primary `0p10h12v0s0b3T`, symbol,
spacing/pitch, and height filtering leave slots `0x782354` and
`0x782364`, then `0x14758` stroke exact matching keeps `0x782354` /
record `0x00004c`. `0x144d2` writes primary context `0x782ee6`, and
`0x14c64` dispatches the unchanged Roman-8 map for that selected record.
The secondary parsed request `0p16h8v0s0b0T` uses the class-one window:
symbol filtering keeps three symbol `0x000e` records, and nearest-pitch
filtering chooses slot `0x782350` / record `0x02e122` before writing
context `0x782ef6` and secondary map `0x783032`. The same `0x13eb8`
model now pins the transient context-only exit and the `0x148f8`
cache-hit return that bypasses candidate-list activation.

Filtering helpers around `0x1519a`, `0x153c6`, `0x147b2`, `0x14758`,
`0x147f4`, and `0x148f8` prune the active list by attributes such as
pitch, style, stroke, typeface, symbol set, and current
orientation-specific state. `0x1519a` is now pinned as the
height filter: it reads primary/secondary requested height from
`0x782ef2` / `0x782f02`, first keeps active candidates within +/-`0x19`,
and if none match uses `0x1533e` to choose the nearest lower and/or
upper decoded height. Built-in heights are decoded through `0x13bca`
from record `+0x28/+0x2a`; the verified class-zero window splits into
eight `1200`-unit candidates and four `850`-unit candidates. `0x153c6`
is pinned as the spacing/pitch filter: it probes/prunes
primary/secondary spacing from `0x782eef` / `0x782eff` against built-in
byte `+0x21`, then filters primary/secondary pitch from `0x782ef0` /
`0x782f00` through `0x13b76` using +/-`5`; if no pitch is in range,
`0x1562c` selects the smallest pitch above the request, or the largest
pitch below when no upper value exists. The verified class-zero window
has spacing `0` throughout and splits into eight `1000`-unit pitch
candidates and four `1666`-unit pitch candidates. `0x147b2` filters
style, `0x14758` filters stroke with exact matching pinned so far, and
`0x147f4` filters typeface. This directly affects text rendering because
it determines the built-in font record used for glyph metrics and
bitmaps.
