# IC30/IC13 Font Sample Page Path

This report covers the first ROM facts behind the control-panel font
printout/self-test sample path. It is not a full placement proof yet; it names
the firmware strings, print helpers, and font-context setup that feed the same
`0xd04a` printable path used by host text.

## Literal Strings and Samples

| Address | Text |
| ---: | --- |
| `0x01c7ea` | `---- ------------------------- ----- ----- ------ ------------------------` |
| `0x01c82d` | `-------` |
| `0x01c836` | `ID            NAME            PITCH SIZE   SET       PRINT SAMPLE` |
| `0x01c878` | `FONT                                 POINT SYMBOL` |
| `0x01c8ad` | `                 -------- PORTRAIT FONTS --------` |
| `0x01c8df` | `                    -------- LANDSCAPE FONTS --------` |

Source/category pointer table at `0x1c170`:

| Index | Pointer | Text |
| ---: | ---: | --- |
| 0 | `0x01c1b8` | `"PERMANENT" SOFT FONTS` |
| 1 | `0x01c1a4` | `LEFT FONT CARTRIDGE` |
| 2 | `0x01c18f` | `RIGHT FONT CARTRIDGE` |
| 3 | `0x01c180` | `INTERNAL FONTS` |

Style labels used by the font-row formatter:

| Address | Text |
| ---: | --- |
| `0x01d17c` | ` SLANT` |
| `0x01d184` | `ITALIC` |
| `0x01d18c` | `LIGHT` |
| `0x01d193` | `BOLD` |

- Sample byte run 1 at `0x1c1cf`: `0x41 0x42 0x43 0x44 0x45 0x66 0x67 0x68
  0x69 0x6a 0x23 0x24 0x40 0x5b 0x5c 0x5d 0x5e 0x60 0x7b 0x7c 0x7d 0x7e 0x31
  0x32 0x33`.
- Sample byte run 2 at `0x1c1e9`: `0xa1 0xa2 0xb3 0xb4 0xb6 0xb8 0xb9 0xbb
  0xbd 0xc1 0xc5 0xc8 0xc9 0xcd 0xce 0xd0 0xd2 0xd4 0xd7 0xd8 0xdb 0xde 0xe0
  0xe3 0xe8`.

## Outer Loop and Page Boundaries

| Address | Fact |
| ---: | --- |
| `0x1c204` | Entry checks accepted-resource count `0x78278e`, reports status `0xe3/0x51` if no font records exist, then calls setup helper `0xe9ba`. |
| `0x1c22a..0x1c236` | Clears display-function bytes `0x783190/0x783191` and sets `0x782da4 = 1` before printing. |
| `0x1c23e..0x1c26c` | Clears four per-source status bytes at `0x783f02..0x783f05`. |
| `0x1c26e..0x1c28a` | Clears row-height word `0x783f06` and local counters before the font pass loop. |
| `0x1c28e..0x1c2c4` | Runs two font-class passes: pass `0` requires class-zero count `0x782798`, pass `1` requires class-one count `0x782790`. Empty passes skip to the next pass. |
| `0x1c2cc..0x1c2f2` | For a nonempty pass, calls `0x1d76c`, ensures a page root through `0x10084`, selects initial candidate state through `0x1e9a0`, and prints the first headers before advancing vertically through `0x1cfb4`. |
| `0x1c2fe..0x1c332` | Prints up to four source groups for a pass. When the group index reaches `4`, snapshots published pool pointer `0x780ea6`, clears a local page flag, and calls FF handler `0xf0f0`. |
| `0x1c344..0x1c350` | Increments the class-pass counter and loops back to `0x1c28e`; after both passes, returns the saved pool pointer. |
| `0x1c540..0x1c5c6` | Maintains a 16-entry recent-font list at `0x783f0a` with count byte `0x783f08`, preventing duplicate candidate rows and appending new selected contexts until full. |

The loop therefore reaches the existing page-object machinery before sample
text is emitted: `0x10084` creates/ensures the page root, `0x1c5e8` installs
each selected font into the current-font/page-root state, `0x1ca2c` and
helpers print labels/sample bytes through `0xd04a`, and `0xf0f0`
finalizes/ejects between class passes.

## Candidate Row Traversal

| Address | Fact |
| ---: | --- |
| `0x1c354..0x1c386` | After the first header pass, clears the one-shot header flag. If the recent-context list has reached 16 entries, calls `0x1d79c(source)` and starts a continuation page through `0x1c9f6` when another printable source row remains. |
| `0x1c386..0x1c3aa` | Emits the source/category heading with `0x1ca2c(source, 0, current-context, 0)`, then asks `0x1b50e(source, row-index, &next-index)` for the first candidate row in that source group. |
| `0x1c3be..0x1c3e4` | Normalizes the returned candidate through `0x1c746`, reads selector/flag bytes via `0x1c766` and `0x1c7a8`, and reads class/orientation through `0x1c710` for comparison with the current class pass. |
| `0x1c3e8..0x1c42e` | If the candidate class does not match the current pass, either retries candidate lookup or marks the current source status byte at `0x783f02 + source`. |
| `0x1c432..0x1c470` | For a matching candidate, installs its context through `0x1c5e8`; if the recent list is full and the candidate is not the last list entry at `0x783f46`, starts a continuation page and reprints the source heading. |
| `0x1c470..0x1c4f2` | Flushes pending text, calls `0x1d050` to advance/check current row height, and calls `0x1d868` to test whether an alternate sample row needs its own continuation-page heading. |
| `0x1c4f2..0x1c53c` | Emits the formatted font row through `0x1cabe`; if no continuation happened, installs the candidate via `0x1cece` and emits sample byte runs through `0x1cf34`, storing the return flag in local page-break word `-6(A6)`. |
| `0x1c540..0x1c5c6` | Scans recent-context entries at `0x783f0a`; duplicates jump back to the source-pass decision path, while a new context is appended and count byte `0x783f08` is incremented. |
| `0x1c5ca..0x1c5e4` | Advances candidate row index `D5` up to `0x63`; when exhausted, stores the final per-source status byte at `0x783f02 + source`, increments source group `D4`, clears row index, and returns to the source loop at `0x1c2fe`. |

This pins the row traversal around the previously open `0x1c334` region. The
missing executable model is now narrow: reproduce the `0x1b50e` candidate
sequence and feed these row decisions into the already identified
printable/page-object path.

## Candidate Resolver `0x1b50e`

| Address | Fact |
| ---: | --- |
| `0x1b516..0x1b558` | Requested ordinal `0xff` disables lookup, clears the caller output word, and returns no resource address. Otherwise `0x1b8ea(mode, ordinal)` is tried first; on fast-probe success, the selected resource comes from `0x7828a0` and the output word from `0x7828a4`. |
| `0x1b568..0x1b5a4` | Selects the first scan window. Mode `3` uses pointer/count `0x7827ac` / `0x78279a`; modes `1` and `2` use `0x7827b0` / `0x78279c`; mode `0` uses `0x7827b4` / `0x78279e`. Other modes miss. |
| `0x1b5a4..0x1b60c` | Sets Roman-8 substitution flag `0x7828ac = 1` unless requested symbol word `0x7821a0` is one of `0x0115`, `0x0175`, `0x0155`, or `0x000e`. |
| `0x1b61a..0x1b650` | For each first-window candidate, reads its candidate word through `0x1bbfe`, classifies it through `0x1b750(mode, slot, word)`, and advances pointer/count when the classifier returns zero. |
| `0x1b650..0x1b74e` | When the first window is exhausted, selects the second scan window. Mode `3` uses `0x7827a0` / `0x782792`; modes `1` and `2` use `0x7827a4` / `0x782794`; mode `0` uses `0x7827a8` / `0x782796`. |
| `0x1b66e..0x1b6ec` | Classifier return `2` marks a pending duplicate Roman-8 candidate. When the requested ordinal is reached and candidate word is Roman-8 with substitution enabled and a duplicate is pending, the output word is the requested symbol `0x7821a0`; otherwise it is the candidate word. |
| `0x1b6b2..0x1b706` | Non-selected Roman-8 candidates can count twice for non-special requested symbols, unless the current selected slot `0x7828a0` is the same slot; this is the duplicate-suppression branch used by the printout row traversal. |
| `0x1b750..0x1b7ac` | Candidate classifier accepts only candidates passing `0x1b7b2` range/special/downloaded checks and `0x1b8b6` current-Roman-8 suppression; it returns `2` for the current selected slot in modes `1` or `2`, otherwise `1`. |
| `0x1b7b2..0x1b8b4` | Admissibility checks are mode-specific: mode `3` accepts the built-in symbol words above, mode `1` accepts `0x200000..0x3ffffe`, mode `2` accepts `0x400000..0x5ffffe`, and mode `0` accepts downloaded records whose `0x170be` record flags include bit 30. |
| `0x1b8ea..0x1b98c` | Fast probe clears `0x7828a0`; mode `3` searches fallback via `0x1ae7e`, modes `1` and `2` call `0x1adaa` first with primary selector `0x78289f = 0` and then with secondary selector `0x78289f = 1`. It succeeds only for requested ordinal zero and a nonzero `0x7828a0`. |

For the font sample page, source-group mode and row ordinal therefore drive
exactly which candidate record enters `0x1c746` and later `0x1cabe` /
`0x1cf34`. Reproducing the printed rows must preserve the two-window order and
the Roman-8 duplicate/substitution cases, not just iterate the candidate slots
once.

## Direct Glyph Payload Hashes

These hashes render the ROM sample byte runs directly through the extracted
built-in glyph payloads for the first `COURIER` and first `LINE_PRINTER`
records. They still bypass the surrounding `0x1c334` page-object loop.

| Font | Sample | Record | Context | Row hash | Glyph count |
| --- | --- | ---: | ---: | --- | ---: |
| `COURIER` | sample run 1 | `0x000418` | `0x44080418` | `da3a1e420d0c9eca0e2638e5eb38d9ec32d8fd795c5b5fef28d552a2ad843717` | 25 |
| `COURIER` | sample run 2 | `0x000418` | `0x44080418` | `53c9e83315109ee2422199a583579b9e7284157fdeb65dd4bb0ed855f4930049` | 25 |
| `LINE_PRINTER` | sample run 1 | `0x0146b4` | `0x440946b4` | `d7bc5c7a8642f3c76724d037cfba7630ae23748419877533335acfebebb35ed0` | 25 |
| `LINE_PRINTER` | sample run 2 | `0x0146b4` | `0x440946b4` | `5b71982ce62609329dc9eb16d9aa9becece7ff79a3ed41a125fd38b1609f5f88` | 25 |

## Print and Placement Helpers

| Routine | Observed behavior |
| ---: | --- |
| `0x1d12e` | Reads a null-terminated ROM string and calls printable handler `0xd04a` for each byte, so sample-page labels enter the same text path as host bytes. |
| `0x1d152` | Advances horizontal cursor `0x782c8a` by the caller value scaled through `0x332ee(..., 0x1e)`. |
| `0x1cfb4` | Advances vertical cursor `0x782c8e` by converting current position through `0x104fe`, adding `0x0258`, then converting back through `0x104d8`. |
| `0x1cfe4` | Computes a line advance from current font/sample state and clamps it to at least `0x0258` before updating `0x782c8e`. |
| `0x1ca2c` | Emits source labels and sample rows, calls `0x1d964`/`0x1d12e`, flushes spans through `0x126e2`/`0x12714`, and stores row-height state in `0x783f06`. |
| `0x1cabe` | Formats a font row prefix: source code bytes `S`, `L`, `R`, or `I`; two decimal digits; style/spacing/pitch/height details; then sample text. |

## Header, Row, and Sample Sequencing

| Address | Fact |
| ---: | --- |
| `0x1c916` | Resets sample-page VMI/HMI, initializes vertical cursor word `0x782c8e = 0x0024`, clears `0x782c90`, selects portrait/landscape header text from `0x782da3`, then prints column headers with repeated `0x1cfb4` line advances. |
| `0x1c9b8` | Clears all 16 recent-context slots at `0x783f0a`, sets count byte `0x783f08 = 1`, and seeds the first slot with the active context. |
| `0x1c9f6` | Starts a continuation page by calling FF handler `0xf0f0`, ensuring a page root through `0x10084`, reinstalling the active context through `0x1c5e8`, rerunning header setup `0x1c916`, and reseeding the recent list. |
| `0x1ca2c` | Before printing a source heading, compares `0x782c8e + current-row-height` against page-limit word `0x782db6`; if it would overrun, it enters the continuation path at `0x1c9f6`. |
| `0x1ca86..0x1caa6` | Flushes pending text with `0x126e2`, prints the selected source/category label from table `0x1c170` via `0x1d12e`, flushes with `0x12714`, advances one line, and stores the row-height word in `0x783f06`. |
| `0x1cb26..0x1cb66` | Builds and prints row prefix bytes: source code `S/L/R/I`, two decimal digits from the row number, a terminator, then advances `0x782c8a` by two horizontal units. |
| `0x1cb6e..0x1cc5e` | Prints style, pitch, height, and symbol-set fields from the selected record, using `0x1d198`, `0x13b76`, `0x13bca`, `0x1cc6e`, and `0x1cd78`, with one- or two-unit `0x1d152` horizontal advances between columns. |
| `0x1cf34..0x1cf9a` | Emits sample run 1 from `0x1c1cf`; if `0x783132` is nonzero, it flushes, updates row/overflow state via `0x1d050`, advances horizontally by `0x31` units, installs the alternate context via `0x1cece`, then emits sample run 2 from `0x1c1e9`. |
| `0x1d050` | Chooses the larger current/alternate row height, may update `0x783f06`, advances by `0x1cfe4`, and if the page limit `0x782db6` would be exceeded, starts a continuation heading via `0x1ca2c` before advancing again. |

These addresses move the sample printout closer to a reproducible page model:
the source label, row prefix, metric columns, and both sample byte runs are
now tied to cursor state (`0x782c8a`, `0x782c8e`), page-limit state
(`0x782db6`), and explicit flush points.

## Row Formatting and Fit Helpers

| Routine | Observed behavior |
| ---: | --- |
| `0x1d198` | Formats the font-name/style column. It resolves built-in and downloaded names differently, appends spacing/style labels from the local string table, numeric style digits when needed, then pads through `0x1d152` so the column occupies 25 emitted characters. |
| `0x1d460` | Walks resource subrecords tagged `FONT`/`font`, `TABL`/`tabl`, or `DUMY`/`DUMY`-like data by adding embedded offsets, then reads the word at `+6` from the resolved font record. |
| `0x1d4ee` | Searches 32 downloaded-font slots at `0x782640` for a payload pointer matching the selected record and returns status `1`, status `0x15`, or reports `0xe3/0x52` if no slot matches. |
| `0x1d5fa` | For a built-in record, follows the relative name pointer at `+0x38`, reads the stored length word, and emits either a trimmed name or a 25-character-capped name depending on the caller flag. |
| `0x1d6ea` | Emits a null-terminated string through `0xd04a` while tracking the current column width and suppressing output after the width reaches 26. |
| `0x1d71e` | Emits fixed-length name bytes through `0xd04a`, replacing C0 controls and bytes `0x80..0x9f` with spaces. |
| `0x1d76c` | Writes a six-byte parsed-command record at `0x78299e` with flag byte `0x80` and the requested orientation word, then calls the normal orientation handler `0x10220`. |
| `0x1d79c` | Probes up to two candidates from `0x1b50e`, compares their orientation/class through `0x1c710` against `0x782da3`, and consults the per-source byte at `0x783f02 + source` for landscape/source gating. |
| `0x1d868` / `0x1dcf2` | Temporarily installs current and alternate contexts, uses `0x1dc38` to simulate one or two sample-row advances, and compares the projected y plus row height against page-limit word `0x782db6`. |
| `0x1d964` | Resolves a candidate for a source group when none is passed in, checks fit with `0x1dcf2`, installs the selected context through `0x1cece`, and tests alternate-row placement when `0x783132` is set. |

The font-name and fit helpers show that the printout is not just a linear
string dump. It reuses the parser's orientation handler, applies the same
printable-byte sanitizer for names, and performs preflight page-fit tests
before emitting the source heading or alternate sample row.

### Row Formatter Lookup Tables

`0x1d198` uses two local lookup tables before falling back to style/numeric
formatting. The first table matches the derived symbol byte and variant word,
and the second matches the family byte from the selected resource record.

Symbol/variant substitutions at `0x1c0a6`:

| Variant word | Symbol byte | Label pointer | Label |
| ---: | ---: | ---: | --- |
| `0x0000` | `0x42` (`B`) | `0x01c110` | `LINE DRAW` |
| `0x0000` | `0x4c` (`L`) | `0x01c106` | `LINE DRAW` |
| `0x0000` | `0x4f` (`O`) | `0x01c100` | `OCR A` |
| `0x0001` | `0x4f` (`O`) | `0x01c0fa` | `OCR B` |
| `0xffff` | `0x51` (`Q`) | `0x01c0f2` | `SPECIAL` |
| `0x0000` | `0x59` (`Y`) | `0x01c0e6` | `CODE 3 OF 9` |
| `0x0008` | `0x59` (`Y`) | `0x01c0de` | `UPC/EAN` |

Family-name substitutions at `0x1c11a`:

| Family byte | Label pointer | Label |
| ---: | ---: | --- |
| `0x0000` | `0x01c163` | `LINE PRINTER` |
| `0x0003` | `0x01c15b` | `COURIER` |
| `0x0004` | `0x01c156` | `HELV` |
| `0x0005` | `0x01c14e` | `TMS RMN` |
| `0x0006` | `0x01c147` | `GOTHIC` |
| `0x0008` | `0x01c13e` | `PRESTIGE` |

## Font Context Setup

`0x1c5e8` installs the selected candidate into the primary current-font state
before sample text is printed:

- writes selected context longword to `0x782ee6`;
- stores context flag bits into `0x782eea` and `0x782eeb`;
- maps the selected resource back to candidate slot `0x7828a8` via `0x1b4c0`;
- clears primary/secondary selector `0x7828de` to primary;
- reads active symbol word through `0x15890` or `0x158be` into `0x783144`;
- runs selected-font activation/map rebuild through `0x14c64`;
- marks current-font dirty byte `0x782f2d = 1`;
- installs the current-font context into the page root through `0xc428`;
- forces VMI words `0x783160/0x783162 = 0x0032/0x0000`;
- forces HMI words `0x78315c/0x78315e = 0x001e/0x0000`.

This ties the font printout path to the same resource-selection, symbol-map,
page-root font-slot, and printable text machinery already used by the
host-byte fixtures. The remaining placement work is to model the surrounding
`0x1c334` loop and compare the produced page objects against these direct
payload hashes and a known printed/self-test sample.
