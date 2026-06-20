# Resource ROM Notes

Sources: `generated/roms/ic32_ic15.bin`; `generated/analysis/ic32_ic15_strings.txt`; `generated/analysis/ic32_ic15_resource_markers.txt`; `generated/analysis/ic32_ic15_font_records.md`; `generated/analysis/ic32_ic15_resource_glyph_probe.md`; `generated/analysis/ic30_ic13_font_context_bridge.md`; `generated/analysis/ic30_ic13_text_glyph_index_flow.md`; `generated/analysis/ic30_ic13_active_symbol_set_flow.md`; `generated/analysis/ic30_ic13_symbol_set_patch_tables.md`; `generated/disasm/ic30_ic13_font_resource_scan_01a2e4.lst`; `generated/disasm/ic30_ic13_font_candidate_classify_01a9be.lst`; `generated/disasm/ic30_ic13_font_candidate_activate_01569c.lst`; `generated/disasm/ic30_ic13_font_candidate_filters_01519a.lst`; `generated/disasm/ic30_ic13_active_object_dispatch_014ba4.lst`; `generated/disasm/ic30_ic13_font_id_select_017708.lst`; `generated/disasm/ic30_ic13_default_font_tables_01ab84.lst`; `generated/disasm/ic30_ic13_symbol_set_handler_01be22.lst`; `generated/disasm/ic30_ic13_font_update_common_00c580.lst`.

The `IC32,IC15` interleave is not the reset firmware pair. It begins with a `HEAD` signature and contains repeated built-in font names and dense offset tables. Treat it as the current source for built-in font directories, metrics, and glyph data.

## Header

The first bytes reconstruct a readable resource header:

```text
HEAD ... Copyright (C) Hewlett-Packard Company, 1986
```

Firmware routine `0x0000041a` scans memory for the same `HEAD` signature, so this is not just an incidental string. The record scanner should be mapped before extracting font tables by hand.

At the end of the resource interleave, the chip tail markers overlap as interleaved bytes:

```text
SSHH77--99223334--0011
```

That is consistent with IC32 carrying `SH7-9233-01` and IC15 carrying `SH7-9234-01`.

## Font Name Markers

`COURIER` appears 16 times. Twelve of those hits currently look like structured font headers; four appear to be embedded in bitmap/data payloads because the expected header word is absent.

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

`LINE_PRINTER` appears 8 times. Six currently look like structured font headers; two appear to be embedded/data hits.

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

- the firmware record start is the even address immediately after the name/padding;
- the record begins with longword `0x00000014` or `0x00000015`;
- longword `record+4` is the scanner length for the small named records, such as `0x450` for the first two `COURIER` records;
- word `record+8` is the offset-table delta, normally `0x004a`;
- table entries are full 32-bit offsets relative to the selected record start.

For example, the first `COURIER` name starts at `0x000410`, but the firmware-selected record starts at `0x000418`. Its firmware address is `0x080418`, context longword is `0x44080418`, length is `0x450`, and its offset table starts at `0x000462`. The first table entry is `0x00007792`, which resolves to glyph entry `0x007baa` by adding the selected record start.

The third header in each local group often has a larger length field, such as `0x000092f8` at record start `0x000cb8`. These larger records contain many relative table entries and should be treated as part of the firmware-scanned font set, not as simple same-size repeats.

The first `LINE_PRINTER` name starts at `0x0146a8`; its firmware record starts at `0x0146b4`, firmware address is `0x0946b4`, context longword is `0x440946b4`, and its table starts at `0x0146fe`.

## Glyph/Bitmap Probe

The generated report `generated/analysis/ic32_ic15_resource_glyph_probe.md` now follows the same built-in resource scan as the firmware and probes each table against the field layout consumed by renderer helper `0x1f354`.

Current confirmed record facts:

- the built-in resource window maps `IC32,IC15` file offset `N` to firmware address `0x80000 + N`;
- built-in font candidates set bit 30 in the selected context longword, selecting the `0x1f354` offset-table form;
- the first two `COURIER` records at record starts `0x000418` and `0x000868` each have length `0x450` and 253 nonzero relative table entries;
- the first two `LINE_PRINTER` records at record starts `0x0146b4` and `0x014b08` each have length `0x454` and 253 nonzero relative table entries;
- `COURIER` size-like words are `30x54` and `30x50`; `LINE_PRINTER` size-like words are `18x39` and `18x38`;
- glyph-entry headers now resolve directly through the firmware formula: byte `+4` is a bitmap delta, byte `+5` is a small mode/plane value, word `+6` is row count, and word `+8` is pixel width.

Example candidate entries from the probe:

| Context | Glyph index | Relative offset | Entry | Bitmap | Height | Width | Render span | Sample bytes |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `0x4008004c` | 0 | `0x0000103c` | `0x001088` | `0x001092` | 32 | 9 | 2 | `1c 00 3e 00 3e 00 3e 00` |
| `0x44080418` | 0 | `0x00007792` | `0x007baa` | `0x007bb4` | 29 | 28 | 4 | `00 1f 80 00 00 ff f0 00` |
| `0x440946b4` | 0 | `0x0000407c` | `0x018730` | `0x01873a` | 16 | 16 | 2 | `03 c0 0f f0 38 1c 30 0c` |

The old high-word interpretation was wrong. The entries are not absolute high words; they are full relative long offsets from the selected record start. The selected context longword now maps directly to concrete resource records and glyph-entry pointers; the text-object glyph index and symbol-set patch mechanics are summarized below.

The firmware-side bridge to the renderer is now traced through the first real glyph entries: selected candidate longwords are copied into current-font context records at `0x782ee6` / `0x782ef6`, those context-record pointers are installed in page-root `+0x2c` slots, `0x1edc6` copies the slots to render-record `+0x24`, the compact glyph renderer loads a selected slot into `0x783a2c`, and `0x1f354` resolves the glyph table relative to the selected `IC32,IC15` record.

## Character to Glyph Index

The compact renderer does not index built-in font tables directly with the incoming host byte. Routine `0x1393a` maps the original character through one of two 256-byte tables:

| Selector | Map table | Context record |
| --- | --- | --- |
| `0x782f06 == 0` | `0x782f32` | `0x782ee6` |
| `0x782f06 != 0` | `0x783032` | `0x782ef6` |

The mapped byte is stored as text object word `+0x0a`; its low byte at object `+0x0b` is later copied by `0x12f2e` into each compact payload entry. That byte is the glyph index consumed by `0x1f354`.

For bit-30 built-in contexts, `0x14d9c` initializes the active map from selected record words `+0x0e` and `+0x10`: characters before the first code map to zero, characters in range map to incrementing glyph indices starting at zero, and characters after the last code map to zero. `0x14f16` then applies symbol-set-specific remaps for normalized symbol set `0x0115` (`8U`, Roman-8), using active symbol-set words at `0x783144` / `0x783146`.

The generated `generated/analysis/ic30_ic13_symbol_set_patch_tables.md` report decodes the `0x14fce` table into 18 patch records. Each record is keyed by a PCL symbol-set code and Technical Reference name: ISO 2 IRV (`2U`), ISO 4 United Kingdom (`1E`), ISO 25/69 French (`0F`/`1F`), HP/ISO German (`0G`/`1G`), ISO 15 Italian (`0I`), ISO 14 JIS ASCII (`0K`), ISO 57 Chinese (`2K`), ISO 10/11 Swedish (`3S`/`0S`), HP/ISO Spanish (`1S`/`2S`/`6S`), ISO 16/84 Portuguese (`4S`/`5S`), and ISO 60/61 Norwegian (`0D`/`1D`). The patch records contain byte pairs applied as `map[dst] = map[src]`. Special active values `0x0005` (`0E`, HP Roman Extension) and `0x0015` (`0U`, ISO 6 ASCII) use hard-coded half-map behavior instead of a patch table.

The generated `generated/analysis/ic30_ic13_active_symbol_set_flow.md` report traces those active words back to the host parser. `ESC (` uses setup handler `0x1201e` and slot word `0`; `ESC )` uses `0x12008` and slot word `1`; both terminal paths call `0x120be`, which calls `0x1be22` and then the common refresh `0xc580`. For normal symbol-set finals, `0x1be22` computes the PCL word as `(parameter << 5) + final_byte - 0x40`, so `ESC (8U` becomes requested word `0x0115` at `0x782ef4`, while the secondary slot uses `0x782f04`. Final `X` restores the previous requested symbol word and calls `0x17708` for font-ID selection. Final `@` uses a numeric subtable: the manual-documented `3@` takes the default-font path, while firmware-supported `@0..@2` read/copy requested words from the four-entry table at `0x782f1c/20/24/28`. The similar table at `0x782f0c/10/14/18` is built separately and consumed by `0x156de` only as a candidate-selection fallback. Font activation at `0x156de` turns requested words into active selected words at `0x783144` / `0x783146`, after fallback/default handling and candidate compatibility checks. The executable harness now drives `ESC (2U` and `ESC )0E` through this stream model, proving active words `0x0055` and `0x0005` before applying the ISO 2 IRV patch table and HP Roman Extension half-map rule to the `LINE_PRINTER` base map.

This makes the current renderer identity `(context longword, mapped glyph byte)`. For example, the unnamed built-in record at context `0x4008004c` has a base range `0x21..0xfe`, so before `0x14f16` patching, host byte `0x21` maps to glyph index `0`. The first `COURIER` and `LINE_PRINTER` records have base ranges `0x01..0xff`, so their pre-patch base mapping starts at byte `0x01 -> glyph 0`.

## Extraction Targets

1. Decode the `HEAD` record scanner in firmware routine `0x0000041a`.
2. Finish naming the firmware-scanned record metadata fields rather than relying on string labels alone.
3. Confirm whether the firmware-supported `0x1be22` `@0..@2` variants are exposed by any host-visible command dialect, or are only internal-compatible table variants.
4. Find or construct a real bitmap-entry fixture for `0x1f1f0` / `0x1f264`, replace producer-modeled text bucket fixtures with full parser-produced page-object payloads, and broaden coverage beyond the four current mode-1 built-in examples.
5. Extract enough metadata for each `COURIER` and `LINE_PRINTER` record to identify point size, pitch, orientation, style, symbol set, cell size, and baseline.
6. Locate the glyph bitmap payloads and write a deterministic extractor from the verified `IC32,IC15` hash.

These are high-value targets for pixel-perfect output because the manuals describe PCL behavior but do not provide the built-in font rasters and exact per-glyph metrics.

## Firmware Font Candidate Lists

The routines around `0x1a2e4..0x1ab82` build candidate lists for font/resource selection, not page raster compositing.

`0x1a2e4` initializes the candidate-list state:

- clears counts `0x782790`, `0x782792`, `0x782794`, `0x782796`, `0x782798`, `0x78279a`, `0x78279c`, and `0x78279e`;
- sets list cursors `0x7827a0`, `0x7827a4`, `0x7827a8`, `0x7827ac`, `0x7827b0`, and `0x7827b4` to a shared base at `0x782324`;
- sets resource scan bounds at `0x78288c` / `0x782890`, initially `0x00080000..0x000ffffe`, then calls `0x1a616`.

`0x1a616` scans resource regions, using `0x782884` as the current scan cursor. It recognizes or skips records with signatures including `HEAD`, `FONT`, `TABL`, `tabl`, and `DUMY`. `0x1a9be` classifies accepted font records, sets flags on the candidate object returned by `0x1bc38`, and increments the candidate-list counts/cursors according to orientation/class and address range.

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

`0x1569c` activates one of the candidate lists by copying a pointer/count pair to `0x78287c` / `0x7827b8` and setting bit 15 in each list entry. `0x156de` then filters the active list against current font criteria. For symbol sets, it reads requested words from `0x782ef4` or `0x782f04`, normalizes them through `0x15850`, compares candidate words returned by `0x15890` / `0x158be`, accepts the small compatibility table at `0x15840`, and stores the active selected word into `0x783144` or `0x783146`.

Filtering helpers around `0x1519a`, `0x153c6`, `0x147f4`, and `0x148f8` prune the active list by attributes such as pitch, style, symbol set, and current orientation-specific state. This directly affects text rendering because it determines the built-in font record used for glyph metrics and bitmaps.
