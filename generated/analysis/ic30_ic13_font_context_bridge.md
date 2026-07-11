# IC30/IC13 Font Context Bridge

This report tracks the current evidence for the bridge from selected font
resource candidates to the compact glyph context longword consumed by renderer
helper `0x1f354`.

## Confirmed Context Flow

| Step | Address | Code fact | Current meaning |
| ---: | --- | --- | --- |
| 1 | `0x1e9a0` | saves `0x78289f`/`0x7821a0`, calls `0x1ae7e`, then loads `A5 = 0x7828a0` | selects a font candidate object under temporary orientation/typeface state |
| 2 | `0x1e9e6` | `move.l (A5), 0x782ee6` | copies the selected candidate longword into the primary current-font context record |
| 3 | `0x1e9ec..0x1ea12` | shifts the selected longword by bits 30 and 26 into `0x782eea` and `0x782eeb` | stores context flags adjacent to the primary context longword |
| 4 | `0x1ea18` | `move.l A5, 0x7828a8` | records the selected candidate slot pointer for later metric/table setup |
| 5 | `0x144d2` | chooses `0x782ee6` or `0x782ef6` based on `0x7828de`, then copies `(0x7828a8)` into that record | common active-object path updates primary or secondary current-font context records |
| 6 | `0xc428` | uses helper `0x332ee` with scale `0x10`, adds the result to `0x782ee6`, and treats the result as a current-font context record pointer | entry point for installing primary/secondary font context records into the page root |
| 7 | `0xc4fc` | scans 16 page-root font slots at `root+0x2c + 4*n`, comparing masked low 24-bit context addresses and `0x78297f+n` live flags | finds an existing slot or the first inactive slot; returns `0x11` if full |
| 8 | `0xc562..0xc574` | writes `A5` into `root+0x2c + 4*slot` and calls `0x15a6`/`0x15ac` around the update | page-root font slots store pointers to current-font context records, not raw glyph bitmap data |
| 9 | `0x1edc6` | copies source `+0x2c..+0x68` to render-record `+0x24..+0x60` | page-root font slots become render-record context slots |
| 10 | `0x1f008` | `move.l (0x24,A6,D0.w), 0x783a2c` | compact glyph object byte `+5` low nibble selects one render-record context slot |
| 11 | `0x1f354` | tests bit 30 of `0x783a2c`, masks to 24 bits, and resolves the glyph entry | final renderer-side interpretation of the context longword |

## Key Routines

| Routine | Role | Selected instruction facts |
| --- | --- | --- |
| `0x14398` | active candidate chooser | walks active list `0x78287c`/`0x7827b8`, chooses a negative/active entry, writes selected slot pointer to `0x7828a8` |
| `0x1440c` | current font metric/state snapshot | reads `0x7828a8`, masks selected candidate longword to a resource address, and snapshots resource bytes into `0x783148/0x783152` state records |
| `0x144d2` | primary/secondary context record updater | writes selected candidate longword and bit-derived flags into `0x782ee6` or `0x782ef6` |
| `0x14c64` | selected font object dispatcher | if no matching active object exists, reads `0x7828a8`; bit-30 offset-table resource records update `0x783134`/`0x78313a` range words and `0x783132`/`0x783133` flags before `0x14d9c`, while bit-30-clear fixed-record resources call `0x14e24`; both paths then call `0x14f16` and `0x1440c` |
| `0xc428` / `0xc4fc` | current-font context installer | maps the normalized current-font context record selected from the `0x782ee6` family to page-root `+0x2c` slots and keeps slot live flags at `0x78297f+n` |
| `0x1393a` | text object font-context capture | selects `0x782ee6`/`0x782ef6` using `0x782f06`, copies the current context longword into a text object, and stores the adjacent flag byte at object `+0x10` |

## Absolute Reference Counts

| Address | Role | Reference count | First references |
| ---: | --- | ---: | --- |
| `0x007828a0` | selected candidate object pointer source for `0x1e9a0` | 35 | `0x01ab98`, `0x01abaa`, `0x01abbe`, `0x01abe2`, `0x01abf6`, `0x01acd4`, `0x01acee`, `0x01ad24`, ... |
| `0x007828a8` | selected candidate slot pointer | 37 | `0x00e78e`, `0x013a68`, `0x013a76`, `0x013afe`, `0x013f92`, `0x0143fc`, `0x01442c`, `0x014438`, ... |
| `0x00782ee6` | primary current font context record | 31 | `0x00c442`, `0x00cbde`, `0x00ce86`, `0x00e2c2`, `0x00e4bc`, `0x00e504`, `0x00e53c`, `0x00e750`, ... |
| `0x00782ef6` | secondary current font context record | 8 | `0x00e50a`, `0x01396a`, `0x0144ec`, `0x01683e`, `0x01a954`, `0x01b3a0`, `0x01b462`, `0x01bfb4` |
| `0x0078297a` | current page-root pointer | 35 | `0x00c44a`, `0x00c50a`, `0x00c61c`, `0x00d204`, `0x00d48a`, `0x00d636`, `0x00d8da`, `0x00da68`, ... |
| `0x00783a2c` | active compact-glyph render context | 2 | `0x01f00c`, `0x01f356` |

## Current Interpretation

- A render context slot is a pointer to a current-font context record
  (`0x782ee6` or `0x782ef6` family), whose first longword is the selected
  candidate/resource longword plus flag bits.
- Page-root `+0x2c` does not hold raw glyph bitmap pointers. It holds up to 16
  current-font context record pointers, which are copied to render-record
  `+0x24` before compact glyph rendering.
- For built-in contexts, that bridge is now resolved: the selected context low
  24 bits map to an `IC32,IC15` offset by subtracting `0x80000`; for both
  built-in and RAM-backed font-resource records, bit 30 selects the
  offset-table form, and table entries are relative 32-bit glyph-entry offsets
  from the selected record start.
- The concrete `0x14c64` built-in cache-miss fixture selects record
  `0x009fb0`, narrows its `0x21..0xfe` base range to `0x21..0x7e` for active
  Roman Extension word `0x0005`, patches map byte `0x21` to glyph `0x80`,
  clears the upper half, and snapshots state at `0x783148` through `0x1440c`.
- The synthetic `0x14c64` fixed-record cache-miss fixture writes selected byte
  `+0x0e` to `0x783132`, rebuilds map `0x782f32` through `0x14e24` /
  `0x14eb6`, maps host `0x21` to glyph `1`, and snapshots inline state byte
  `+8 = 1` at `0x783148` through `0x1440c`.
- The payload-backed fixture now takes a table-validated `0x16fae` header
  allocated through `0x17026` / `0x1719c`; the `0x16c14` installed path
  selects it as a bit-30 offset-table resource through `0x14c64`/`0x14d9c` and
  `0x15890`, while a separate bit-30-clear control case proves the
  `0x14e24`/`0x14eb6` fixed-record form and `0x158be` `+0x17` encoded-symbol
  read.
- The remaining font/text gap is live parser/font-state selection for those
  allocated records and candidate filters, so host bytes select the same
  compact glyph index documented in `ic30_ic13_text_glyph_index_flow.md`
  without hand-selected records.
