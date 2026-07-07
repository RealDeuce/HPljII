# Resource ROM Notes

Sources: `generated/roms/ic32_ic15.bin`;
`generated/analysis/ic32_ic15_header.txt`;
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

The firmware-facing scan and candidate-window contract for these records
is documented in [built-in-resource-scan.md](built-in-resource-scan.md).

## Header

The generated header probe
`generated/analysis/ic32_ic15_header.txt` projects the first `0x180` bytes of
`generated/roms/ic32_ic15.bin`; its first line reconstructs a readable resource
header:

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

The firmware scan windows make the remaining high-address resource edge a
hardware decode question. `0x1a2e4` initializes the built-in font scan with
start `0x080000`, end `0x0ffffe`, and step `0x40000`, then calls
`0x1a616`. Optional cartridge/resource scans reuse the same `0x1a616`
walker with windows selected by `$8000.14` / `$8000.15`: `0x200000..0x3ffffe`
or `0x400000..0x5ffffe`. The earlier cartridge boot probe at `0x003e8` also
tests `$8000.6` / `$8000.7` before looking for `PROG` at `0x200000` or
`0x400000`. Those ROM paths prove that `0x0c0000..0x0ffffe` is inside the
built-in resource scan range, while cartridge windows live elsewhere.

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

The secondary `LINE_PRINTER` table also exposes a zero-offset edge through the
same formula. Table index `0x5f` has relative offset `0`, and disassembly
`generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst` shows
`0x1f354` adding that table value without rejecting it. The resulting glyph
entry is the record header at file offset `0x02e122`: bitmap delta `0`, mode
`0`, rows `20062`, width `74`. In the transparent secondary segmented fixture,
`0x1f1f0` then advances segment `0x39` to file offset `0x03fe22` / firmware
address `0x0bfe22` and needs bytes through `0x0c0321`. That crosses the
verified `IC32,IC15` image at `0x0c0000`, so the remaining question is
resource-window decode after the pair boundary, not glyph-entry field layout.
Fixture `transparent secondary segment-57 continuation policies diverge after
verified bytes` tests three explicit continuation policies for that same
bucket-456 compact payload. The verified bytes produce the same current-band
digest `f0c1127f9e6b203f9829ab43f159b89c3f7dda687a47d4c09971077eac55c96e`
under resource-pair mirror, code-pair continuation, and zero-fill; the
verified suffix at `0x0bfe22..0x0bffff` hashes to
`e0a0fd34ce7a39f79ecd27c0ee288631554a0ff78359b72e27ea6087651bcf1f`.
The mirror/code-pair/zero-fill continuation candidates hash to
`e435e3b9d033e491b57282a88b0f321aa5fecae8128fa060844cc01379349563`,
`90934acf59d9e8519c9149dc5df228f8fec2bff8451427be265489be967cdd16`, and
`359f38eef400e2fa3924a3258652e74ee19cd46cb92e47bce91f1194fce25e9e`, and
the fallback rows diverge with digests
`75cc8b60cd33f5c659ad702530ebacdc7685f2b75d63e18b9ce055383153f142`,
`dc58960aff83e718df147897de51944939626c4e8422a53da5443bca48a53df5`, and
`6373cecdf5f20d78b01abe5aa65c051d82ddef345b7cf7fe1504f93c9cb2c425`.
Tracked tool `tools/probe_resource_window.py` recomputes the byte-side
evidence from `data/rom_manifest.json` and the ignored local ROM images. Its
checked output verifies the `IC32,IC15` resource hash, the `IC30,IC13`
firmware hash, suffix length `478`, continuation length `802`, the three
continuation hashes above, and the second-probe longwords `HEAD`,
`0x00800000`, and `0x00000000`.

This is now a ROM/address-map boundary rather than a resource-record boundary.
`data/rom_manifest.json` accounts for the installed ROM set as four 128K x 8
TC531000P packages: the `IC30,IC13` firmware interleave and the `IC32,IC15`
resource interleave are each `0x40000` bytes. `notes/formatter-interface-pca.md`
records the service-manual-derived hardware facts that the HP 33440 ROM capacity
can be 1 MB, the address-controller gate array can change the ROM address region
through jumpers, and ROM is used in four separate sections. Therefore the three
continuation candidates above are fixture hypotheses for the unverified
`0x0c0000..0x0c0321` firmware-address window, not equivalent decoded glyph
formats.

Startup checksum coverage further narrows what can be inferred locally.
`notes/firmware-startup.md` documents the startup verifier byte-sum ranges as
`0x000000..0x03ffff` for the code pair and `0x080000..0x0bffff` for the
resource pair. The secondary segment-57 continuation starts at `0x0c0000`, so
the resource-pair checksum proves the verified suffix through `0x0bffff` but
does not validate, reject, or select among the mirror, code-pair, and zero-fill
continuation policies for the fallback rows.

The fixtures `0x41a HEAD scanner would duplicate records under simple resource
mirror` and `0x1a616 candidate scan continuation policy changes built-in
counts` add address-map constraints. If the whole `IC32,IC15` resource pair
were simply mirrored at firmware address `0x0c0000`, the `0x41a` scanner model
would see `HEAD` at offsets `0` and `0x40000`, walk `48` typed records, and
terminate at `0x80000`. The `0x1a2e4` / `0x1a616` font candidate scan explicitly
sets built-in bounds `0x080000..0x0ffffe`; under the same mirror hypothesis,
the modeled candidate scan sees `48` accepted built-in records instead of
`24`, doubles class-one low count `0x782792` from `12` to `24`, doubles
class-zero low count `0x78279a` from `12` to `24`, advances
`0x7827a4`/`0x7827a8`/`0x7827ac` to `0x782384`, and advances
`0x7827b0`/`0x7827b4` to `0x7823e4`. A full mirror in that range would
therefore not be only a local row-source detail: it would be visible to
candidate discovery unless hardware or gate-array state hides the mirror from
scanner reads. The separate `$8000.14` / `$8000.15` cartridge scan windows at
`0x200000..0x5ffffe` do not explain the `0x0c0000` read. Closing the fallback
rows therefore needs board/emulator evidence for that physical decode/window,
live startup candidate counters after `0x1a2e4`, a direct bus read around
`0x0c0000`, or physical output that selects one of the fallback-row digests.

Fixture `0x41a HEAD scanner rejects non-HEAD 0x40000 continuations` constrains
the other two local continuation hypotheses against the same startup scanner.
If the code pair follows `IC32,IC15`, the second probe at offset `0x40000`
sees marker `0x00800000`; if zero-fill follows it, the marker is
`0x00000000`. Both variants keep a single `HEAD` chain, walk the same 24 typed
records, and skip to final probe `0x80000` without duplicating scanner input.
The `0x1a616` continuation fixture shows the same candidate-list result for
both non-`HEAD` variants: total `0x78278e = 24`, class-one low
`0x782792 = 12`, class-zero low `0x78279a = 12`, final
`0x7827a4`/`0x7827a8`/`0x7827ac = 0x782354`, and final
`0x7827b0`/`0x7827b4 = 0x782384`.
`tools/probe_resource_window.py --quiet` checks those same consequences from
the local ROM files: mirror has heads `[0, 0x40000]`, `48` accepted candidates,
and low class-one/class-zero counts `24/24`; code-pair and zero-fill each keep
one head, `24` accepted candidates, and low counts `12/12`.

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
selector for bit-30 offset-table/built-in records, used by `0x1a9be`
partitioning, `0x1b060` default matching, `0x17708` font-ID selection,
and `0xe860` static-context refresh checks; the named records split
evenly between selector values `0` and `1`. For bit-30-clear
inline/downloaded records, `0xe860` and `0x17708` use byte `+0x16` as
the equivalent class selector. Fixture
`0xe860 reads inline +0x16 and offset-table +0x20 class bytes` pins that
branch split.
Byte `+0x21`, read by the `0x153c6` spacing filter, is `0` for every
named record. Symbols repeat as six records each for `0x0155`,
`0x0175`, and `0x000e`. Raw `+0x24/+0x26` pitch fields are
`0x0078/0x00` for `COURIER` and `0x0048/0x00` for `LINE_PRINTER`. Raw
`+0x28/+0x2a` height fields are `0x00c8/0x00` and `0x008d/0xab`.
Those words are no longer merely extracted columns: `0x1519a` consumes the
decoded value through `0x13bca`, producing the verified 1200-unit `COURIER`
height group and 850-unit `LINE_PRINTER` height group. Comparator bytes
`+0x2f..+0x31` are `(0,0,3)` or `(0,3,3)` for `COURIER`, and `(0,0,0)` for
`LINE_PRINTER`; same-class chooser `0x1428c`, reached from
`0x14398`/`0x13c06`, compares decoded height, byte `+0x2f`, signed byte
`+0x30`, then byte `+0x31`.

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
It also names the outer `0x1c204` / `0x1c28e` font-printout loop: the
firmware clears sample state, runs class-zero and class-one passes from
the firmware candidate counts, ensures a page root through `0x10084`,
tracks up to 16 recent contexts at `0x783f0a`, and calls FF handler
`0xf0f0` to finalize/eject between passes.
The same loop is now traced through candidate-row traversal:
`0x1b50e` supplies source rows, `0x1c746` / `0x1c766` / `0x1c7a8` /
`0x1c710` normalize and classify each candidate, `0x1d050` /
`0x1d868` decide continuation-page needs, `0x1cabe` emits row fields,
and `0x1cf34` emits the sample byte runs before the recent-context list
at `0x783f0a` suppresses duplicate rows.
The same report now renders the two ROM sample byte runs directly
through extracted payloads for first `COURIER` and first `LINE_PRINTER`,
producing row hashes
`da3a1e420d0c9eca0e2638e5eb38d9ec32d8fd795c5b5fef28d552a2ad843717` /
`53c9e83315109ee2422199a583579b9e7284157fdeb65dd4bb0ed855f4930049`
and
`d7bc5c7a8642f3c76724d037cfba7630ae23748419877533335acfebebb35ed0` /
`5b71982ce62609329dc9eb16d9aa9becece7ff79a3ed41a125fd38b1609f5f88`.
Those hashes are direct payload-render targets for the later `0x1c334`
page-object loop model.
The report now also pins the local placement sequence: `0x1c916`
initializes sample-page cursor state, `0x1ca2c` guards source headings
against page-limit word `0x782db6`, `0x1cabe` emits the `S/L/R/I` row
prefix and metric columns through `0xd04a`, and `0x1cf34` emits sample
run 1, advances horizontally by `0x31` units, installs the alternate
context, and emits sample run 2 when `0x783132` is set.
The actual first source-heading-to-row composition is now fixture-backed:
`font sample source heading carries default plus first two Courier rows`
follows the `0x1c386..0x1c38e` call into `0x1ca2c`, resolves source table
pointer `0x1c180` to `INTERNAL FONTS`, queues the heading bytes through
current context `0x4008004c`, advances y through `0x1cfb4`, and then carries
the default Roman-8 row plus the first two named `COURIER` rows in the same
page-record state. Request index `0` uses `0x1b8ea` fast-probe state to select
slot `0x782354`, record `0x00004c`, and word `0x0115`. Because that record has
no explicit name string, `0x1d198` falls through local family table `0x1c11a`;
record byte `+0x18 == 0` emits `LINE PRINTER`, so row 0 prints
`I00LINE PRINTER10128U`.
Fixture `font sample resolver carries first two Courier rows` extends
that composition across the next related resolver request and row
transition. The sample loop call at `0x1c398..0x1c3a0` invokes `0x1b50e`;
mode `3` scans `0x7827ac` / `0x78279a` then `0x7827a0` / `0x782792`, while
`0x1b8ea` fast probe only applies to request index `0`. With current slot
`0x782354`, request indexes `1` and `2` suppress the unnamed Roman-8
record `0x00004c`, then select first named `COURIER` record `0x000418`
with word `0x0155` and second named `COURIER` record `0x000868` with word
`0x0175`. The `0x1c470..0x1c488` / `0x1d050` row-to-row edge resets x to
the line anchor, advances y from `0x00900000` to `0x00ce0000` through
`0x1cfe4`, assigns page-record context slots `[0x44080418, 0x44080868]` in
the named-row isolation fixture, and emits second-row bytes
`I02COURIER101211U` before carrying both sample runs. The actual first-three
row fixture assigns context slots `[0x4008004c, 0x44080418, 0x44080868]`.
The row-helper window now names the lower formatting helpers: `0x1d198`
builds the 25-character font-name/style column, `0x1d6ea` emits capped
strings through `0xd04a`, `0x1d71e` sanitizes fixed-length name bytes,
`0x1d76c` synthesizes an orientation command record before calling
`0x10220`, and `0x1d964` / `0x1dcf2` preflight current/alternate row
placement against `0x782db6`.
It also decodes the `0x1d198` local lookup tables: symbol/variant pairs
at `0x1c0a6` select `UPC/EAN`, `CODE 3 OF 9`, `SPECIAL`, `OCR A`,
`OCR B`, and `LINE DRAW`, while family bytes at `0x1c11a` select
`PRESTIGE`, `GOTHIC`, `TMS RMN`, `HELV`, `COURIER`, and
`LINE PRINTER`.

## Renderer-Facing Field Classification

The resource fields that are now tied to visible text output should be
treated as semantic state, not just extraction columns:

- Canonical ROM fields:
  - record `+0x20`: built-in class/orientation selector consumed by
    `0x1a9be`, `0x1b060`, `0x17708`, and `0xe860`;
  - record `+0x21`: spacing/metric selector copied by `0xc428` into
    `0x78318e` on bit-30 built-in contexts and read by the `0x153c6`
    spacing filter;
  - record longword `+0x24`: built-in HMI/default-advance source. First
    Courier context `0xc008004c` uses `0x00780000`, which `0x10550`
    converts to packed advance `30`; Line Printer context
    `0x440946b4` uses `0x00480000`, which fixture
    `line-printer flagged HMI metric via 0x10550` converts to packed
    advance `18`;
  - glyph-entry word `+0`: signed x placement offset consumed by
    `0xd824`;
  - glyph-entry word `+2`: signed y placement offset consumed by
    `0xd824`;
  - glyph-entry byte `+4`, byte `+5`, word `+6`, and word `+8`: bitmap
    delta, mode, row count, and pixel width consumed by `0x1f354` and
    compact text renderers.
- Derived/cache fields:
  - `0xc428` derives `0x78318e` from record byte `+0x21` and derives
    `0x78315c` through `0x10550` from record longword `+0x24`.
  - `0x1393a` derives source object `+0x04` from the selected context
    longword and mapped glyph index, so the page-object producer and
    renderer do not reread the character map.
  - `0x12f2e` derives the compact coordinate and selector from the
    positioned source fields and page-root context slot.
- Parser scratch:
  - The host byte and active symbol map select the glyph index through
    `0x1393a`; those transient parser/map values are not fields in the
    resource record.
  - SI/SO and font-selection commands only choose which current-font
    context reaches `0xc428`; they do not mutate the extracted resource
    metadata.
- Firmware bookkeeping:
  - current-font records `0x782ee6` / `0x782ef6`, page-root context
    slots, and render-record `+0x24` slots carry selected context
    longwords such as `0xc008004c`, `0xc00ae122`, and `0x440946b4`.
  - The `0x783132` / `0x783133` selected-font flags and the
    `0x783134` / `0x78313a` range caches are map-selection state, not
    part of the resource payload.
- Still-open manual/physical naming:
  - record words `+0x28/+0x2a` are decoded-height inputs for `0x1519a`
    through `0x13bca`, with `COURIER` grouped at `1200` and `LINE_PRINTER`
    grouped at `850`; they still need correlation against observed
    baseline/cell placement on a known printed font/self-test sample.
  - record bytes `+0x2f..+0x31` are same-class chooser tie-breakers consumed
    by `0x1428c`; their ROM role is pinned, but their HP/manual-facing names
    remain unknown.

Writers are limited because these are ROM resource records. The firmware
writers are bridge/cache writers: `0x13eb8` selects a current-font record,
`0xc428` installs the page-root context slot and HMI cache, `0x1393a`
builds a printable source object, `0xd824` applies glyph-entry placement
offsets, `0x12f2e` queues compact text objects, and `0x1edc6` copies
page-root context slots into render records. Readers/consumers are the
candidate helpers above, the `0x10550` metric conversion path, the
`0xd824` positioned-source path, and the `0x1f354` built-in glyph
resolver.

Visible-output evidence is fixture-backed. The Courier parsed-selection
stream in [font-context-metrics.md](font-context-metrics.md) uses
selected context `0xc008004c`, record `+0x24 = 0x00780000`, HMI `30`,
glyph entry `0x001088`, and renders two `!` rows after the
`0x1edc6` bridge. The Line Printer HMI fixture uses context
`0x440946b4`, record `+0x24 = 0x00480000`, HMI `18`, and renders the
second `!` at compact coord `0x0202`. The positioned-text fixture uses
Line Printer glyph entry `0x015330`: glyph-entry x offset `6` and y
offset `21` transform cursor `(10,21)` into source `(16,0)`, then
`0x12f2e` emits compact coord `0x0001`.

No ROM-internal middle edge remains for these built-in metric consumers:
`0xc428`/`0x10550` covers record `+0x24`, `0xd824` covers glyph-entry
`+0/+2`, `0x1519a` consumes record `+0x28/+0x2a` as decoded-height
inputs before `0x13bca`, and `0x1428c` consumes `+0x2f..+0x31` as
same-class chooser tie-breakers after `0x14398` / `0x13c06`.
Parser-produced downloaded metric payloads are tracked separately in
[font-context-metrics.md](font-context-metrics.md), where the tested
`0x1719c -> d4ac/d8fc` copied-field paths are closed by legal matrix and
byte-boundary fixtures. The remaining boundary here is physical/manual
naming of the built-in height/baseline/cell fields against a known printed
font/self-test sample.

The `0x1c334..0x1c5e4` candidate traversal is now decoded through both
internal-font source-group class passes. Fixture
`font sample first internal source group follows 0x1c334 row loop` in
`tools/render_fixture_harness.py` resolves the class-zero request indexes
`0..14` through `0x1b8ea`, `0x1b50e`, `0x1c746`, `0x1c710`, `0x1cabe`, and the
`0x1c540..0x1c5c6` recent-list scan. The class-zero visible rows are:

- `I00` record `0x00004c`, context `0x4008004c`, word `0x0115`:
  `LINE PRINTER`, `10`, `12`, `8U`.
- `I01` record `0x000418`, context `0x44080418`, word `0x0155`:
  `COURIER`, `10`, `12`, `10U`.
- `I02` record `0x000868`, context `0x44080868`, word `0x0175`:
  `COURIER`, `10`, `12`, `11U`.
- `I03` record `0x000cb8`, context `0x40080cb8`, word `0x000e`:
  `COURIER`, `10`, `12`, `0N`.
- `I04` record `0x009fb0`, context `0x40089fb0`, word `0x0115`:
  `LINE PRINTER`, `10`, `12`, `8U`.
- `I05` repeats context `0x40089fb0` with substituted word `0x0005`:
  `LINE PRINTER`, `10`, `12`, `0E`.
- `I06` record `0x00a37c`, context `0x4408a37c`, word `0x0155`:
  `COURIER`, `10`, `12`, `10U`.
- `I07` record `0x00a7cc`, context `0x4408a7cc`, word `0x0175`:
  `COURIER`, `10`, `12`, `11U`.
- `I08` record `0x00ac1c`, context `0x4008ac1c`, word `0x000e`:
  `COURIER`, `10`, `12`, `0N`.
- `I09` record `0x0142e4`, context `0x400942e4`, word `0x0115`:
  `LINE PRINTER`, `16.6`, `8.5`, `8U`.
- `I10` repeats context `0x400942e4` with substituted word `0x0005`:
  `LINE PRINTER`, `16.6`, `8.5`, `0E`.
- `I11` record `0x0146b4`, context `0x440946b4`, word `0x0155`:
  `LINE_PRINTER`, `16.6`, `8.5`, `10U`.
- `I12` record `0x014b08`, context `0x44094b08`, word `0x0175`:
  `LINE_PRINTER`, `16.6`, `8.5`, `11U`.
- `I13` record `0x014f5c`, context `0x40094f5c`, word `0x000e`:
  `LINE_PRINTER`, `16.6`, `8.5`, `0N`.

Request `14` resolves to class-one record `0x019d18`. Because the class-zero
pass has nonzero `D5`, the mismatch does not continue scanning: the
`0x1c3f8..0x1c400` branch jumps to the `0x1c5d6..0x1c5de` status writer and
stores `0x783f05 = 14`. The recent list is seeded with `0x4008004c` by the
`0x1c9b8` setup path; rows `I05` and `I10` are visible duplicate Roman-8
substitutions, but the post-row `0x1c540..0x1c5c6` scan does not append their
already-present contexts. The fixture carries those 14 rows through one
page-record state with context slots ending at
`0x4008004c,0x44080418,0x44080868,0x40080cb8,0x40089fb0,0x4408a37c,
0x4408a7cc,0x4008ac1c,0x400942e4,0x440946b4,0x44094b08,0x40094f5c`.

Fixture `font sample internal class-one source group follows 0x1c334 row loop`
then covers the internal-font class-one pass seeded by `0x1e9a0` with
context `0x40099d18`. Request index `0` emits the seeded class-one Roman-8
`LINE PRINTER` row. After that row, control reaches the common
`0x1c404..0x1c428` advance path with `D5 == 0`; because this is class pass
`1`, it reads the previous source status byte `0x783f05 = 14` and resumes at
request `14`. Requests `14` and `15` resolve to class-zero records and are
rejected by the same `0x1c3e8..0x1c3f6` comparison; request indexes `16..28`
emit the class-one rows:

- `I16` record `0x01a0e4`, context `0x4409a0e4`, word `0x0155`:
  `COURIER`, `10`, `12`, `10U`.
- `I17` record `0x01a534`, context `0x4409a534`, word `0x0175`:
  `COURIER`, `10`, `12`, `11U`.
- `I18` record `0x01a984`, context `0x4009a984`, word `0x000e`:
  `COURIER`, `10`, `12`, `0N`.
- `I19` record `0x023484`, context `0x400a3484`, word `0x0115`:
  `LINE PRINTER`, `10`, `12`, `8U`.
- `I20` repeats context `0x400a3484` with substituted word `0x0005`:
  `LINE PRINTER`, `10`, `12`, `0E`.
- `I21` record `0x023850`, context `0x440a3850`, word `0x0155`:
  `COURIER`, `10`, `12`, `10U`.
- `I22` record `0x023ca0`, context `0x440a3ca0`, word `0x0175`:
  `COURIER`, `10`, `12`, `11U`.
- `I23` record `0x0240f0`, context `0x400a40f0`, word `0x000e`:
  `COURIER`, `10`, `12`, `0N`.
- `I24` record `0x02d4aa`, context `0x400ad4aa`, word `0x0115`:
  `LINE PRINTER`, `16.6`, `8.5`, `8U`.
- `I25` repeats context `0x400ad4aa` with substituted word `0x0005`:
  `LINE PRINTER`, `16.6`, `8.5`, `0E`.
- `I26` record `0x02d87a`, context `0x440ad87a`, word `0x0155`:
  `LINE_PRINTER`, `16.6`, `8.5`, `10U`.
- `I27` record `0x02dcce`, context `0x440adcce`, word `0x0175`:
  `LINE_PRINTER`, `16.6`, `8.5`, `11U`.
- `I28` record `0x02e122`, context `0x400ae122`, word `0x000e`:
  `LINE_PRINTER`, `16.6`, `8.5`, `0N`.

Request `29` is the terminal `0x1b50e` miss for the class-one pass, which
writes `0x783f05 = 29` through `0x1c5d6..0x1c5de`. The full-loop status
sequence for the internal source is therefore class-zero writer
`0x1c5d6..0x1c5de: 14`, class-one reader `0x1c41a..0x1c428: 14`, and
class-one writer `0x1c5d6..0x1c5de: 29`. The class-one page-record context
slots end at
`0x40099d18,0x4409a0e4,0x4409a534,0x4009a984,0x400a3484,0x440a3850,
0x440a3ca0,0x400a40f0,0x400ad4aa,0x440ad87a,0x440adcce,0x400ae122`.

Fixture `font sample non-internal source groups follow modes 0..2` covers the
same row loop for the other source indexes. Source `0` uses resolver mode `0`
for `"PERMANENT" SOFT FONTS`; in this built-in-only fixture state both class
passes miss at request `0`, advance through `0x1c404..0x1c42e`, miss again at
request `1`, and write `0x783f02 = 1`. Source `1` uses mode `1` for `LEFT
FONT CARTRIDGE`; source `2` uses mode `2` for `RIGHT FONT CARTRIDGE`. Both
cartridge sources take the request-`0` fast-probe path in each class pass, so
class-zero emits only `L00` / `R00` from record `0x00004c`, class-one emits
only `L00` / `R00` from record `0x019d18`, and request `1` is the terminal
miss. Their status chains are `0x783f03 = 1` and `0x783f04 = 1`; the
class-one pass reads that prior value through `0x1c41a..0x1c428` before the
request-`1` terminal miss.

Fixture `font sample source headings 0..2 compose page records` then carries
those source labels and single-row cartridge outputs through the page-record
producer. Source `0` queues the `"PERMANENT" SOFT FONTS` heading as a
heading-only page-record state: bucket list `[0]`, bucket count `{0: 3}`, and
aggregate object digest
`89fb4143a293f80bb8c07bab86d5c94940ba73039f2bd9ba1e3de0c2c6c4fb4c`.
Source `1` queues `LEFT FONT CARTRIDGE` plus `L00LINE PRINTER10128U`: the
class-zero record `0x00004c` reaches buckets `[0, 2, 3, 4, 6, 7]` with digest
`cc583ac71b083d3cf241a1a72ff6345e22d585a9eef1a0ba850427b6d43e2aba`, and
the class-one record `0x019d18` reaches buckets `[0, 3, 4, 6, 7]` with digest
`51dade4f3a0af13cb533c9f62c5ea955a63f02046622e39a00b4ac8b072f63d6`.
Source `2` queues `RIGHT FONT CARTRIDGE` plus `R00LINE PRINTER10128U`: the
class-zero digest is
`eaf10ca6b5b5716170b313ce542df82a6974c1ac22ee0e87308dead7be22c6a1`, and
the class-one digest is
`3d23d5c6c5320d406d1db34523d3ad01c819d4e938e3dee4fa0a5d20747ed152`.
Fixture `font sample full printout source placement follows firmware order`
then composes the eight source/class segments in the order driven by
`0x1c28e` and `0x1c2fe`: class-zero sources `0..3`, then class-one sources
`0..3`. Each pass performs the `0x1d76c`, `0x10084`, `0x1e9a0`, `0x1c9b8`,
`0x1c916`, and `0x1cfb4` setup sequence before source iteration. The segment
row counts are `[0, 1, 1, 14, 0, 1, 1, 14]`; source-status writes are
`0x783f02 = 1`, `0x783f03 = 1`, `0x783f04 = 1`, `0x783f05 = 14`, then
`0x783f02 = 1`, `0x783f03 = 1`, `0x783f04 = 1`, `0x783f05 = 29`. The
composed page-record surfaces have bucket counts `[3, 13, 13, 142, 3, 12,
12, 122]`, context-slot counts `[1, 1, 1, 12, 1, 1, 1, 12]`, total row count
`32`, and aggregate segment digest
`f4105538bd1506731f04810ed2f50cce23815751c4f979ed6f60efab4cde08c7`.

Fixture `font sample page-limit branches trigger continuation calls` covers
the page-limit state block shared by the heading and row-advance paths.
At heading entry, `0x1ca2c` compares cursor y word `32` plus row height `13`
against page-limit word `0x782db6`: limit `45` takes the `0x1c9f6`
continuation-page path, while limit `95` does not. At row advance,
`0x1d050` moves the first `COURIER` row from y `0x00520000` to
`0x00900000` by `744` subunits; with page limit `100`, it calls `0x1c9f6`,
then `0x1ca2c(source=3,row=1,current=0x4008004c,selected=0x44080418)`, and
schedules a second `0x1cfe4` advance of `744` subunits. With page limit
`1010`, the same row transition stays on the no-continuation path.
Fixture `font sample heading continuation emits fresh source heading page
record` now carries the heading-preflight overrun into the page-record producer.
The fresh continuation segment emits only the `INTERNAL FONTS` heading from
context `0x4008004c`, queues bucket `0`, ends at cursor
`0x00000000,0x00520000`, and pins bucket digest
`e43b602451f3f31ea84e49c7be1d12b34ae3d1b7369b5dd7096aa7e96db1268c`.
Fixture
`font sample cartridge heading continuations emit source-specific page records`
uses that same `0x1ca2c -> 0x1c9f6` pre-heading overrun for non-internal
source labels. Source `1` class-zero context `0x4008004c` emits
`LEFT FONT CARTRIDGE` with bucket digest
`a4c3a808dd2430bc463e091a57e0462bdff94e50a5e8a5b21f615764e9f6a63d`;
source `2` class-one context `0x40099d18` emits
`RIGHT FONT CARTRIDGE` with bucket digest
`03025c4239ec3d130bff4f4e05362b1c9730b9848e7e99a2934c4868b600badb`.
Fixture `font sample row continuation emits fresh source heading page record`
now carries that row-overrun branch into the page-record producer. The fresh
continuation segment emits the `INTERNAL FONTS` heading and row
`I01COURIER101210U` from context `0x44080418`, queues buckets
`[0, 2, 3, 6, 7, 8, 16, 24, 32, 40, 48, 56, 64]`, ends at cursor
`0x08ac0000,0x00900000`, and pins bucket digest
`2dc6c3326aad3118d2b96c44cf0ab727ee2926069c5035722cceef470db8b7ef`.
Fixture
`font sample class-one row continuation emits fresh source heading page record`
now carries the class-one row-overrun sibling into the page-record producer.
The trigger advances from current context `0x40099d18` to selected context
`0x4409a0e4`; the fresh continuation segment emits the `INTERNAL FONTS`
heading and row `I16COURIER101210U`, queues buckets
`[0, 3, 4, 7, 8, 16, 24, 32, 40, 48, 56, 64]`, ends at cursor
`0x08ac0000,0x00900000`, and pins bucket digest
`842dd781a1093819f918e128999786f94f16cc3562ca25c3a82503ced74f3f3c`.
Fixture `font sample alternate-row continuation emits preadvanced row page
record` carries the sibling `0x1d868` D7=1 branch into the page-record
producer. The caller sequence
`0x1c4a4 -> 0x1d868 -> 0x1c4b6 -> 0x1c9f6 -> 0x1c4ca -> 0x1ca2c ->
0x1c4d4 -> 0xf06e -> 0x1c4e8 -> 0x1d050 -> 0x1c4f2 -> 0x1cabe` emits the
same `I01COURIER101210U` row after pre-row y advance
`0x00520000 -> 0x00900000`, queues buckets
`[0, 7, 8, 16, 24, 32, 40, 48, 56, 64]`, and pins bucket digest
`c6f0cbe07a7681d3ecfd3447b8296e97cbf8042d6d962d825f6018d980d5396b`.
Fixture `font sample alternate row fit gate follows 0x1d868` covers the
separate selected/alternate gate at `0x1d868..0x1d8b8`. The disassembly reads
`0x783132` at `0x1d886..0x1d894` after calling `0x1cece(selected,row=1)` and
before installing the current context through `0x1c5e8`; if the flag is zero,
the routine skips `0x1d8ba` and returns D7 `0`. With `0x783132 = 1`,
`0x1d8ba..0x1d95c` projects the first `COURIER` selected row from y
`0x00900000` to `0x00ce0000` using a `744`-subunit advance, combines current
and selected row heights to `13`, and compares projected bottom `219` against
`0x782db6`: page limit `300` fits, while equality at limit `219` returns D7
`1` for the continuation path.
Fixture `font sample multi-probe preflight follows 0x1dcf2` covers the later
current/alternate preflight helper at `0x1dcf2..0x1de2c` and its shared
calculator `0x1dc38..0x1dcf0`. The calculator reads the selected line advance
and current/selected row heights, writes the caller's row-height output word,
and returns the projected packed y. `0x1dcf2` first probes current y with mode
`0`, optionally probes a second selected row when `0x783132` is set, and on
overflow converts raw subunits `0x1218` to reset y `0x01820000` before probing
mode `1` and possibly a final mode-`0` selected row. The first `COURIER` case
shows y `0x00900000 -> 0x00ce0000 -> 0x010c0000` fitting under limit `300`
and returning D7 `0`; with limit `250`, the second probe overflows and the
reset mode-`1` probe bottom `511` returns D7 `1` at `0x1de24`. A high-y case
starting at `0x01f40000` with limit `600` proves the reset mode-`1` and
mode-`0` probes can both fit and return D7 `0` at `0x1de16`.

Fixture `font sample full printout rows reuse ROM sample byte runs` now ties
the composed source/class rows back to the two ROM sample byte tables. Across
the eight `0x1c204` / `0x1c28e` / `0x1c2fe` source/class segments, the
non-empty row counts are source/class `(1,0)=1`, `(2,0)=1`, `(3,0)=14`,
`(1,1)=1`, `(2,1)=1`, and `(3,1)=14`, for the same `32` total rows as the
placement fixture. Every emitted row queues the 25-byte run-1 table at
`0x1c1cf` and the 25-byte run-2 table at `0x1c1e9`; the direct isolated
sample-run render hashes remain
`b6a0061f7de34c0fa1a0586263f3f167c84d95219e05437e74a286356409af37`,
`d7dfb89c8cff5e309b95aac43cd64e0f74f17db1dd9118253544343f17b4c1ce`,
`c77bca7364adbda480c5a31fa4be469175c031bd5f14fc4a54a2e6fb09174be5`, and
`b10556bfb02fbb6a2ffec2a82add396619bae3ace0ebab657113f4d3648c41b5`.
The aggregate correlation digest is
`4f664dc44f9ad98cbe25d4bdead651a2902bec1f90367c650bb2d1352d6f3e8a`.

Fixture `font sample full printout segments render through 0x1ed84 and
0x1ef6a` now renders each of those eight page-record segments through the
active-to-render-record bridge and per-band renderer. The eight segments
produce render-bucket counts `[1, 6, 6, 65, 1, 5, 5, 50]`, rendered bucket-row
totals `[33, 210, 210, 2012, 33, 146, 146, 1257]`, and aggregate surface
digest `5e5e735b4fb2a2a4dff4794099a02eaf23fa2dd3e469df8d053db88a321ea6f2`.
The modeled class-zero segments top out at row width `2219`; the modeled
class-one segments top out at row width `4097`, so that width/baseline
interpretation is now pinned but not yet validated against paper output.

The covered forced-continuation page-record objects now include internal and
cartridge heading-preflight forms, class-zero row-overrun `I01`, class-one
row-overrun `I16`, and alternate-row `I01` caller forms. Broader row-overrun
cross-products and physical comparison of the rendered source/class surfaces
against a known printed/self-test sample, including baseline and cell
placement agreement after `0x1ed84`, remain open.

The old high-word interpretation was wrong. The entries are not absolute
high words; they are full relative long offsets from the selected record
start. The selected context longword now maps directly to concrete
resource records and glyph-entry pointers; the text-object glyph index
and symbol-set patch mechanics are summarized below.

The firmware-side bridge to the renderer is now traced through the first
real glyph entries: selected candidate longwords are copied into
current-font context records at `0x782ee6` / `0x782ef6`, those
selected longwords are installed in page-root `+0x2c` slots, `0x1edc6`
copies the slots to render-record `+0x24`, the compact glyph renderer
loads a selected slot into `0x783a2c`, and `0x1f354` resolves the glyph
table relative to the selected `IC32,IC15` record. The tracked
bridge and span-metric contract is documented in
[font-context-metrics.md](font-context-metrics.md).
The tracked soft-font descriptor, downloaded payload, current-record, and
downloaded-glyph render contract is documented in
[downloaded-fonts.md](downloaded-fonts.md).

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
The same report now adds a verified built-in symbol inventory and real
map samples from the scanned resource records. The 24 built-ins expose
six records each for `0N` (`0x000e`, ISO 100: ECMA-94 / Latin 1), `8U`
Roman-8 (`0x0115`), `10U` (`0x0155`, PC-8), and `11U` (`0x0175`, PC-8
DIN). Roman-8 samples from record `0x00004c` now show the actual compact
glyph bytes for base `8U`, hard-coded `0U` and `0E`, plus selected
patch-table cases such as `2U`, `1E`, and `0G`. Separate base-map samples
for `0N`, `10U`, and `11U` make clear that those built-in alternatives are
selected as distinct font records rather than remapped by `0x14f16`.
Fixture `live parser symbol-set streams select non-Roman built-ins` now
drives primary host streams `ESC (0N`, `ESC (10U`, and `ESC (11U` through
parser handlers `0x11eb6`, `0x1201e`, and `0x120be`, then through the
`0x13eb8` selected-font refresh and `0x14c64` dispatch. The three streams
write requested words `0x000e`, `0x0155`, and `0x0175`; `0x156de` keeps
survivor record starts `0x000cb8/0x00ac1c/0x014f5c`,
`0x000418/0x00a37c/0x0146b4`, and `0x000868/0x00a7cc/0x014b08`;
`0x14398`/`0x13c06` choose records `0x000cb8`, `0x000418`, and
`0x000868`. `0x14c64` rebuilds map `0x782f32` with ranges `0x21..0xff`
for `0N` and `0x01..0xff` for `10U`/`11U`, using the
`selected-symbol-not-roman8` dispatch path rather than the `0x14f16`
Roman-8 patch-table path.
Fixture `non-Roman symbol streams select visible built-ins` now composes
both primary and secondary forms through visible output. Primary streams
`ESC (0N ESC (s0p10h12v0s0b3T!!`,
`ESC (10U ESC (s0p10h12v0s0b3T!!`, and
`ESC (11U ESC (s0p10h12v0s0b3T!!` select contexts `0xc0080cb8`,
`0xc4080418`, and `0xc4080868`, queue two Courier compact entries, and
render row digest
`8b36cfd64d818c0982b172982156f8be9687388c9679cd83538c9d1098d9bb2c`.
Secondary streams `ESC )0N ESC )s0p16h8v0s0b0T SO !!`,
`ESC )10U ESC )s0p16h8v0s0b0T SO !!`, and
`ESC )11U ESC )s0p16h8v0s0b0T SO !!` select contexts `0xc00ae122`,
`0xc40ad87a`, and `0xc40adcce`, cross SO handler `0xc6b8`, queue two Line
Printer compact entries from context slot `1`, and render row digest
`b8ee0f8dd3e6ed70afa219bc00605d75249ae047a67fb67189693057d7936e6c`.

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
dispatch. Visible-output fixtures carry both selected forms farther:
`font-ID built-in selection feeds visible page-record rows` renders
`ESC (7X!!` from context `0xc0089fb0`, while
`font-ID secondary built-in selection feeds visible SO page-record rows`
renders `ESC )8X SO !!` from class-one context `0xc00ae122`, and
`font-ID inline/downloaded selection feeds visible page-record rows`
renders `ESC )4660X SO !` from synthetic inline/downloaded context
`0x00000100`. A table-builder fixture now pins `0x1ac0a`
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
3. Compose visible-output fixtures for parser-exposed `@0..@3` only if they
   expose behavior not already covered by the symbol/fallback visible streams.
   The parser/default-table boundary itself is now documented: `@0`/`@1` read
   the `0x1ac0a` table at `0x782f1c/20/24/28`, `@2` copies the primary
   requested word, and `@3` uses the current default-font word. Fixture
   `real default-table caller stream uses ROM-backed words` routes
   `ESC (0@ ESC )0@ ESC )1@ ESC )2@ ESC (3@` through the ROM `0x120be`
   terminal handler and real-record-backed words from `0x1b250`, `0x1b50e`,
   `0x1ab84`, and `0x1b060`.
4. Add new downloaded-font streams only when they change installed records,
   source objects, page-record memory, or rendered rows. The current boundary
   coverage already chains fetched `ESC *c4660d37e5F` state into fetched
   `ESC )s0W`, `ESC )s80W`, and `ESC )s2193W` streams, with fetched
   `ESC )s2193W` now crossing `0x1ed84`/`0x1ef6a`; the fetched
   `ESC )s18W` payload-control path now crosses `0x1edc6` and
   `0x1ed84`/`0x1ef6a` before wide glyph rendering, and a combined
   fetched font-control / downloaded-character / printable stream now
   drives the installed downloaded glyph into segmented page-record
   buckets before `0x1ed84`/`0x1ef6a` rendering. That combined stream is
   pinned as a 2,215-byte single `0xa904` ring source with control,
   payload, and printable boundaries, restored record
   `80 57 08 91 00 00`, glyph `0x25`, selector `0x3003`, buckets `9`
   and `1`, and compact render dispatch target `0x1effe`. The even-span
   `ESC )s18W` rule/raster composition also has its
   `font_command_final_header` handoff pinned. The downloaded-font and
   metric checkpoints now cover descriptor validation, legal metric
   matrices, width/row/span/high-row matrices, no-install and status-2
   recovery, bit-30-clear fixed-record cases, payload-control returns,
   combined installed-glyph output, parser-driven rule/raster output, and
   FF publication variants. Remaining downloaded-font work should start
   only when a stream changes the installed header, current-record or
   candidate state, byte-24 handoff, `0x783140` remainder, `0x12328` drain
   status, next handler, page-record selector or bucket, render dispatch, or
   row digest.
5. Correlate the remaining built-in metadata names against physical sample
   placement. Record `+0x24` is pinned as the `0xc428` / `0x10550` HMI
   source, first-glyph placement offsets are pinned through the `0xd824`
   path, `+0x28/+0x2a` are pinned as decoded-height inputs for `0x1519a`,
   and `+0x2f..+0x31` are pinned as `0x1428c` chooser tie-breakers. What
   remains is their manual-facing baseline/cell terminology and agreement
   with observed paper output.
6. Compare the modeled font-printout surfaces against a known
   printed/self-test sample. The `0x1c334..0x1c5e4` row traversal is decoded,
   including `0x1b50e` two-window candidate resolution, class filtering,
   continuation-page entry, row-index status writes, and the post-row
   recent-context scan. The verified internal-font mode-3 candidate sequence
   is now documented below for both class passes, and both ROM sample byte
   runs are consumed through the `0x1c5e8..0x1ed84` page-object/render
   boundary. Fixture `font sample full printout source placement follows
   firmware order` composes all eight source/class segments with row counts
   `[0,1,1,14,0,1,1,14]` and aggregate segment digest
   `f4105538bd1506731f04810ed2f50cce23815751c4f979ed6f60efab4cde08c7`.
   Fixture `font sample full printout rows reuse ROM sample byte runs` proves
   every non-empty row queues both ROM sample tables at `0x1c1cf` and
   `0x1c1e9`, with correlation digest
   `4f664dc44f9ad98cbe25d4bdead651a2902bec1f90367c650bb2d1352d6f3e8a`.
   Fixture `font sample full printout segments render through 0x1ed84 and
   0x1ef6a` renders those eight segments through the bridge and band renderer,
   with aggregate surface digest
   `5e5e735b4fb2a2a4dff4794099a02eaf23fa2dd3e469df8d053db88a321ea6f2`.
   The remaining work is physical baseline/header/cell correlation against
   observed paper output, not ROM sample-run page-object construction.
7. Broaden the now-named `0N` / `10U` / `11U` parser/font-selection/output
   cases only where new command combinations expose different state
   boundaries; primary and secondary visible-output byte streams are now
   fixture-backed.

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

The widened `0x1b50e` resolver pins the source-row scan order used by
the font sample page and default-font lookup. Mode `3` scans
`0x7827ac` / `0x78279a`, then `0x7827a0` / `0x782792`; modes `1` and
`2` scan `0x7827b0` / `0x78279c`, then `0x7827a4` / `0x782794`; mode
`0` scans `0x7827b4` / `0x78279e`, then `0x7827a8` / `0x782796`. It
also preserves the Roman-8 duplicate/substitution state through
`0x7828ac`, requested word `0x7821a0`, classifier `0x1b750`, and
current-Roman-8 suppression helper `0x1b8b6`.

The verified internal-font mode-3 window order is now concrete enough to
feed the font-sample page model:

- Class-zero first window `0x782354..0x782380`: rows 1..12 are
  `0x782354` / `0x00004c` / `0x4008004c` / `8U`, `0x782358` /
  `0x000418` / `0x44080418` / `10U` `COURIER`, `0x78235c` /
  `0x000868` / `0x44080868` / `11U` `COURIER`, `0x782360` /
  `0x000cb8` / `0x40080cb8` / `0N` `COURIER`, `0x782364` /
  `0x009fb0` / `0x40089fb0` / `8U`, `0x782368` / `0x00a37c` /
  `0x4408a37c` / `10U` `COURIER`, `0x78236c` / `0x00a7cc` /
  `0x4408a7cc` / `11U` `COURIER`, `0x782370` / `0x00ac1c` /
  `0x4008ac1c` / `0N` `COURIER`, `0x782374` / `0x0142e4` /
  `0x400942e4` / `8U`, `0x782378` / `0x0146b4` / `0x440946b4` /
  `10U` `LINE_PRINTER`, `0x78237c` / `0x014b08` / `0x44094b08` /
  `11U` `LINE_PRINTER`, and `0x782380` / `0x014f5c` /
  `0x40094f5c` / `0N` `LINE_PRINTER`.
- Class-one second window `0x782324..0x782350`: rows 13..24 repeat the
  same symbol/name pattern at record starts `0x019d18`, `0x01a0e4`,
  `0x01a534`, `0x01a984`, `0x023484`, `0x023850`, `0x023ca0`,
  `0x0240f0`, `0x02d4aa`, `0x02d87a`, `0x02dcce`, and `0x02e122`, with
  context longwords `0x40099d18`, `0x4409a0e4`, `0x4409a534`,
  `0x4009a984`, `0x400a3484`, `0x440a3850`, `0x440a3ca0`,
  `0x400a40f0`, `0x400ad4aa`, `0x440ad87a`, `0x440adcce`, and
  `0x400ae122`.

Rows with symbol word `8U` (`0x0115`) are the only rows affected by the
Roman-8 duplicate/substitution branch. When requested word `0x7821a0` is
not one of `8U`, `10U`, `11U`, or `0N`, `0x1b50e` can count a Roman-8
row twice and return the requested word for the duplicate ordinal; when
the current selected slot matches the Roman-8 slot, `0x1b8b6` suppresses
that duplicate.

The primary live parser selection fixture confirms that `ESC (0N`,
`ESC (10U`, and `ESC (11U` consume the class-zero rows above directly:
records `0x000cb8`, `0x000418`, and `0x000868` become the selected built-in
records, and dispatch map `0x782f32` is rebuilt through the non-Roman-8
selected-symbol path. This is separate from Roman-8 base record `0x00004c`
plus `0x14f16` patching.
The visible-output fixture confirms the same for the secondary class-one rows:
`ESC )0N`, `ESC )10U`, and `ESC )11U` with the secondary Line Printer
selection consume records `0x02e122`, `0x02d87a`, and `0x02dcce`, rebuild
map `0x783032`, cross SO, and render from context slot `1`.

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
all class-one candidates, then either recovers through remembered word
`0x000e` at `0x782f0a` before fallback or falls through to fallback-table
word `0x000e`, keeping the three secondary symbol `0x000e` records. Fixture
`remembered secondary symbol feeds visible SO page-record rows` pins the
remembered pass: slot `0x782324` / record `0x019d18` rejects candidate
`0x0115`, slot `0x782330` / record `0x01a984` accepts candidate `0x000e`,
and the following selected context, SO path, compact object prefix, and row
digest match the secondary visible-output fixture.

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
cache-hit return that bypasses candidate-list activation; see
[font-context-metrics.md](font-context-metrics.md) for how those context
records feed page-root slots, printable source capture, and span metrics.

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

### Candidate-Window Composition Checkpoint

Semantic role: `0x1a2e4 -> 0x1a616 -> 0x1a9be` turns the scanned built-in
resource records into RAM candidate windows. `0x1569c`, `0x156de`,
`0x14398`, and `0x13eb8` then reduce one of those windows to the selected
primary or secondary context consumed by text imaging. This is a resource
selection checkpoint, not a page-object writer by itself.

Canonical fields:

- candidate pointer-list base `0x782324`;
- total candidate count `0x78278e`;
- class/range counts `0x782790`, `0x782792`, `0x782794`, `0x782798`,
  `0x78279a`, and `0x78279c`;
- cursor/window starts `0x7827a0`, `0x7827a4`, `0x7827a8`,
  `0x7827ac`, `0x7827b0`, and `0x7827b4`;
- active candidate window pointer/count `0x78287c` / `0x7827b8`;
- selected candidate slot pointer `0x7828a8`;
- primary and secondary selected context records `0x782ee6` and
  `0x782ef6`.

Derived/cache state:

- scan cursor `0x782884` and scan bounds `0x78288c` / `0x782890`;
- active symbol words `0x783144` and `0x783146`;
- candidate fallback table `0x782f0c`, `0x782f10`, `0x782f14`,
  and `0x782f18`, built by `0x1af36` and consumed by `0x156de`;
- parser default-symbol table `0x782f1c`, `0x782f20`, `0x782f24`,
  and `0x782f28`, built by `0x1ac0a` and consumed by final-`@`
  subdispatches;
- rebuilt maps `0x782f32` and `0x783032`;
- HMI/cache values derived from selected records, including built-in
  longword `+0x24` through `0x10550` and height words `+0x28/+0x2a`
  through `0x13bca`.

Parser scratch:

- requested primary/secondary symbol words in `0x782ef4` / `0x782f04`;
- font-selection request fields under `0x782eec..0x782f06`;
- final-`X` transient font ID saved around `0x17708`;
- final-`@` records routed through `0x120be` before they read table words
  or copy requested words.

Firmware bookkeeping:

- candidate high active bit `0x80000000`, set by `0x1569c` and cleared on
  rejected candidates by later filters;
- bit-30 built-in context flag from `HEAD`/typed records;
- bit-26 flag mirroring record byte `+0x0c == 2` for `HEAD`/typed records;
- dirty/refresh bytes `0x782f2c` and `0x782f2d`, consumed by `0xc580`;
- page-root context install state written by `0xc428` / `0xc4fc` after a
  selected context exists.

Unknown:

- manual-facing names for several record metadata fields remain open,
  especially the exact baseline/cell terminology behind `+0x28/+0x2a`
  and tie-breaker bytes `+0x2f..+0x31`;
- forced continuation-page variants beyond the covered heading-preflight,
  cartridge heading, internal class-zero `I01`, internal class-one `I16`, and
  alternate-row caller cases are broader regression cross-products unless they
  expose a different page-object form; physical output, if captured, would be
  optional correlation for the full internal-font sample page, while the
  ROM-side candidate order and rendered-surface digest are fixture-backed;
- optional cartridge/resource candidate windows are bounded by ROM addresses,
  but no physical cartridge image is present in this repo.

Writers:

- `0x1a2e4` clears candidate counters, seeds all cursor windows to
  `0x782324`, and sets built-in scan bounds `0x080000..0x0ffffe`.
- `0x1a616` scans records and calls `0x1a9be` for accepted font records.
- `0x1a9be` creates candidate entries, sets bit flags from the resource
  record shape, increments total count `0x78278e`, and advances the
  class/range cursor windows.
- `0x1569c` activates the selected class window, writes `0x78287c` /
  `0x7827b8`, and sets the active bit in each selected entry.
- `0x156de` filters symbol candidates, writes active symbol words, shrinks
  the active window, and uses `0x782f0c..0x782f18` only after requested
  candidates miss.
- `0x14398` writes the selected slot pointer after comparator `0x13c06`.
- `0x144d2` writes selected context records at `0x782ee6` and `0x782ef6`.
- `0x14c64` rebuilds the active glyph maps consumed by printable text.

Readers and consumers:

- `0x1b50e` consumes the candidate windows for default-font lookup and the
  font sample page, including the Roman-8 duplicate/substitution state
  through `0x7828ac`, `0x7821a0`, and `0x1b8b6`.
- `0x13eb8` consumes request fields, candidate windows, filters, chooser
  output, and selected context writers for normal primary/secondary font
  selection.
- `0x17708` consumes scanned record ids and candidate slots for final-`X`
  font-ID selection.
- `0xc580`, `0xc428`, and `0xc4fc` consume selected context records and
  decide whether they become page-root context slots for later printable
  bytes.
- `0x1393a`, `0xd824`, `0x12f2e`, `0x1ed84`, and `0x1ef6a` consume the
  selected context indirectly when printable bytes become compact objects
  and rendered rows.

Output effect:

This checkpoint changes pixels only by choosing which context longword and
glyph map later text uses. For the verified resource pair, the primary
Roman-8 selection for `ESC (s0p10h12v0s0b3T!!` resolves to slot `0x782354`
and context `0xc008004c`; secondary Line Printer selection for
`ESC )s0p16h8v0s0b0T SO !!` resolves to slot `0x782350` and context
`0xc00ae122`. Final-`@`, final-`X`, symbol fallback, and non-Roman symbol
streams are covered as separate visible-output fixtures in the semantic
model, but they all consume the same candidate-window state summarized here.

Confidence:

High for built-in scan bounds, candidate count/window partitioning,
verified `IC32,IC15` candidate order, active-window selection, symbol
fallback, final-`@` table consumption, final-`X` success/non-selected exits,
selected context writes, map rebuilds, and visible primary/secondary text
output because those are fixture-backed and cited in
[semantic-state-model.md](semantic-state-model.md). Medium for manual
metadata names and physical sample-page comparison.

Fixtures:

- `live parser symbol-set streams select non-Roman built-ins`
- `non-Roman symbol streams select visible built-ins`
- `real default-table caller stream uses ROM-backed words`
- `real final-@ default-table streams select visible built-ins`
- `font-ID built-in selection feeds visible page-record rows`
- `font-ID secondary built-in selection feeds visible SO page-record rows`
- `font-ID inline/downloaded selection feeds visible page-record rows`
- `0x17708 font-ID non-selected exits preserve prior selection`
- `font-ID non-selected exits keep prior visible rows`
- `0x13eb8 refresh carries parsed primary font selection to dispatch`
- `0x13eb8 refresh carries parsed secondary font selection to dispatch`
- `inline primary font selection stream renders visible rows`
- `inline secondary font selection stream renders SO visible rows`
- `font sample full printout source placement follows firmware order`
- `font sample full printout rows reuse ROM sample byte runs`
- `font sample full printout segments render through 0x1ed84 and 0x1ef6a`
- `font sample heading continuation emits fresh source heading page record`
- `font sample cartridge heading continuations emit source-specific page records`
- `font sample row continuation emits fresh source heading page record`
- `font sample class-one row continuation emits fresh source heading page record`
- `font sample alternate-row continuation emits preadvanced row page record`
- `0x1a616 candidate scan continuation policy changes built-in counts`

Disassembly evidence:

- `generated/disasm/ic30_ic13_font_resource_scan_01a2e4.lst`
- `generated/disasm/ic30_ic13_font_candidate_classify_01a9be.lst`
- `generated/disasm/ic30_ic13_font_candidate_activate_01569c.lst`
- `generated/disasm/ic30_ic13_font_candidate_filters_01519a.lst`
- `generated/disasm/ic30_ic13_font_id_select_017708.lst`
- `generated/disasm/ic30_ic13_default_font_tables_01ab84.lst`
- `generated/disasm/ic30_ic13_symbol_set_handler_01be22.lst`
- `generated/disasm/ic30_ic13_font_update_common_00c580.lst`

Unresolved middle edges:

- `0x1a616` optional cartridge windows `0x200000..0x5ffffe` remain
  software-bounded but physically unverified because no cartridge/resource
  image is present.
- `0x13eb8` lower-level refresh flow is modeled at fixture boundaries;
  parser-to-visible primary and secondary output is covered. Remaining useful
  ROM work is new selection/filter cases that change selected context, map
  rebuild, page-object bytes, or rendered rows.
- physical sample-page comparison is still needed to assign manual-facing
  baseline/cell names and validate paper placement outside the ROM-internal
  rendered-surface digest.
