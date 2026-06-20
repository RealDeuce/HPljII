# PCL Command Map from Firmware

Sources: `generated/analysis/ic30_ic13_pcl_command_map.md`; `generated/analysis/ic30_ic13_parser_dispatch_tables.md`; `generated/analysis/ic30_ic13_font_control_flow.md`; focused listings under `generated/disasm/`; `notes/pcl4-language.md`.

The generated command map flattens the main parser's mode-indexed dispatch tables into PCL command sequences and handler addresses. It is local-only because it is generated from ROM bytes, but it can be regenerated with:

```sh
tools/analyze_roms.py
```

## Parser Tables

- Normal parser pointer table: `0x000112a4`.
- Alternate/data parser pointer table: `0x000116f6`.
- Each table entry is six bytes:

```text
byte_to_match, next_mode, handler_long
```

The alternate/data table keeps the same state transitions but suppresses many final handlers. That is consistent with a mode that must still parse or collect PCL syntax while deferring normal side effects.

## High-Value Normal-Mode Handlers

These command-to-handler anchors are current priorities for pixel-perfect rendering:

| Command | Handler | Why it matters |
| --- | --- | --- |
| `ESC E` | `0x00cc52` | PCL reset, partial-page finalization, environment/parser/raster reinitialization |
| CR `0x0d` | `0x00f02c` | horizontal cursor reset/line-termination interactions |
| LF `0x0a` | `0x00f08c` | vertical cursor movement |
| FF `0x0c` | `0x00f0f0` | page eject and page-buffer boundary |
| HT `0x09` | `0x00f1cc` | tab and horizontal cursor positioning |
| BS `0x08` | `0x00f2a8` | backspace cursor behavior |
| `ESC &l#A` | `0x00fc74` | page size; maps PCL values to internal paper codes |
| `ESC &l#O` | `0x010220` | orientation; rebuilds page geometry and cursor state |
| `ESC &l#C` | `0x00cb00` | VMI in 1/48-inch units into `0x783160` |
| `ESC &l#D` | `0x00c992` | lines per inch; accepted set maps to line advance `0x783160` |
| `ESC &l#E` | `0x00ece2` | top margin; writes top offset `0x782dce` |
| `ESC &l#F` | `0x00ea9e` | text length; writes bottom/text-length limit `0x782dd2` |
| `ESC &l#H` | `0x00ef62` | paper source and page eject |
| `ESC &a#L` | `0x00eb58` | left margin; absolute HMI columns into `0x782dd6` |
| `ESC &a#M` | `0x00ec0c` | right margin; `abs(parameter) + 1` HMI columns into `0x782dda` |
| `ESC &a#C` | `0x00f39e` | horizontal column position through current HMI and helper `0xf4ca` |
| `ESC &a#H` | `0x00f416` | horizontal decipoint position; five packed subunits per decipoint |
| `ESC &a#R` | `0x00f560` | vertical row position through current VMI, top offset, and helper `0xf6e2` |
| `ESC &a#V` | `0x00f60a` | vertical decipoint position; five packed subunits per decipoint |
| `ESC &k#H` | `0x00ca8c` | HMI |
| `ESC &k#G` | `0x00edf8` | CR/LF/FF line-termination mode |
| `ESC &f#S` | `0x00f75e` | cursor stack at `0x782c96..0x782d36`; selector `0` pushes, selector `1` pops |
| `ESC &f#Y` | `0x00e112` | macro ID; stores absolute parsed word in `0x783164` |
| `ESC &f#X` | `0x00dd08` | macro control; selectors `0..10` dispatch through the macro record/data-chain table |
| `ESC *t#R` | `0x010808` | raster resolution |
| `ESC *r#A` | `0x01075a` | start raster graphics |
| `ESC *r#B` | `0x0107fa` | end raster graphics |
| `ESC *b#W` | `0x011f82` | transfer raster row bytes |
| `ESC *c#P` | `0x010898` | fill rectangle; consumes size state and queues rule object |
| `ESC *c#A` | `0x010e68` | rectangle width in dots into `0x78316a` |
| `ESC *c#B` | `0x010e22` | rectangle height in dots into `0x783166` |
| `ESC *c#G` | `0x010dce` | area fill id into `0x78316e` |
| `ESC *c#H` | `0x010a40` | rectangle width in decipoints into `0x78316a` |
| `ESC *c#V` | `0x010ae0` | rectangle height in decipoints into `0x783166` |
| `ESC *c#D` | `0x015a56` | assign font ID |
| `ESC *c#F` | `0x016df6` | font control |
| `ESC (#A..^` | `0x0120be` | primary font-designation family: symbol set, `#X` font ID, and `3@` default font |
| `ESC )#A..^` | `0x0120be` | secondary font-designation family: symbol set, `#X` font ID, and `3@` default font |
| `ESC (s#P` / `ESC )s#P` | `0x012082` | primary/secondary spacing |
| `ESC (s#H` / `ESC )s#H` | `0x012096` | primary/secondary pitch |
| `ESC (s#V` / `ESC )s#V` | `0x012046` | primary/secondary point size |
| `ESC (s#S` / `ESC )s#S` | `0x01206e` | primary/secondary style |
| `ESC (s#B` / `ESC )s#B` | `0x0120aa` | primary/secondary stroke weight |
| `ESC (s#T` / `ESC )s#T` | `0x01205a` | primary/secondary typeface |

## First Handler Observations

`ESC &l#A` at `0x00fc74` maps PCL page-size parameters into internal page codes:

- `1` -> internal `6`
- `2` -> internal `2`
- `3` -> internal `5`
- `26` -> internal `1`
- `80` -> internal `0x88`
- `81` -> internal `0x87`
- `90` -> internal `0x89`
- `91` -> internal `0x8a`

It then rebuilds page-related state, including `0x782da2`, `0x782db2`, `0x782db4`, `0x782dc0`, `0x782dce`, and `0x782dd0`, and calls shared reset/layout helpers also seen in `ESC E`. Executable fixtures now pin letter `ESC &l1A` as internal code `6`, width `3030`, height `2025`, portrait margin `3150`, top offset `90`, and PCL `80` as internal code `0x88` masking to geometry-table index `8`.

`ESC &l#O` at `0x010220` accepts orientation values below `2`, updates `0x782da3`, rebuilds page geometry, updates `0x783160`, and reloads current font/metrics state through tables rooted near `0x782ee6` / `0x782ef6`. The letter landscape fixture pins active extents `2025x3030`, landscape margin `2175`, printable extent `2125`, top offset `100`, and the `0x103ea` threshold sequence `2175, 2550, 2480, 2550`.

`ESC &l#D` at `0x00c992` accepts absolute LPI values `1,2,3,4,6,8,12,16,24,48`, treats zero as `12`, converts to packed line advance as `3600 / LPI` twelfths, stores `0x783160`, and sets modified-layout byte `0x782ee1`. `ESC &l#C` at `0x00cb00` converts absolute VMI in 1/48-inch units using 75 packed subunits per unit, accepts fractional values, stores `0x783160`, and leaves `0x782ee1` clear when the converted VMI is zero. Both handlers reject values beyond page extent `0x782dba` and, when pending text byte `0x782a6d` is set, refresh vertical cursor `0x782c8e` to `0x782dce + VMI * 18 / 25`.

`ESC &l#E` at `0x00ece2` scales top-margin lines through current VMI, rejects zero VMI or positions at/beyond page extent `0x782dba`, writes top offset `0x782dce = top_margin - 0x782dbe`, recomputes default text-length bottom via helper `0xea16`, and refreshes pending vertical cursor with the same `VMI * 18 / 25` offset. `ESC &l#F` at `0x00ea9e` scales text-length lines through VMI, rejects lengths beyond the remaining page below current top margin, writes `0x782dd2 = 0x782dce + text_length`, and uses `0xea16` to restore the default bottom when the parameter is zero.

`ESC &a#L` at `0x00eb58` converts the absolute parsed column count through current HMI `0x78315c`, rejects values beyond `0x782dda - HMI`, and writes the accepted value to left margin `0x782dd6`. When the accepted margin is right of current cursor `0x782c8a` or pending text is marked, it also moves the cursor and flushes pending spans through `0x12714` / `0x126e2` when span flushing is enabled. `ESC &a#M` at `0x00ec0c` converts `abs(parameter) + 1` columns through HMI, rejects values before `0x782dd6 + HMI`, clamps beyond page width `0x782db8`, writes right margin `0x782dda`, and can move `0x782c8a` left while setting right-limit latch `0x782a57`.

`ESC &a#C` at `0x00f39e` and `ESC &a#H` at `0x00f416` both convert the parsed decimal parameter into packed twelfths and commit through `0xf4ca`, which applies relative moves when parsed-record bit 0 is set, clamps between zero and `0x782db8`, updates the right-limit latch against `0x782dda`, clears pending text, and updates active span state. `ESC &a#C` scales through current HMI `0x78315c`; `ESC &a#H` uses five packed subunits per decipoint.

`ESC &a#R` at `0x00f560` and `ESC &a#V` at `0x00f60a` commit through vertical helper `0xf6e2`, which ensures a page root, clears/flushes pending text state, adds either current vertical cursor `0x782c8e` for relative moves or top offset `0x782dce` for absolute moves, clamps against lower bound `0x782dca`, and writes `0x782c8e`. The row command scales through VMI `0x783160` and adds fractional `0.7200` for absolute row moves before conversion; the decipoint command uses five packed subunits per decipoint and clamps to `0x782dc6`.

`ESC *r#A` at `0x01075a` starts raster graphics by setting state in the block rooted at `0x783170`; it seeds a raster baseline from `0x782c8a` or `0x782c8e` depending on current mode.

`ESC *b#W` at `0x011f82` routes through `0x121cc` with handler `0x105d0`, so raster row byte transfer is tied into the same parsed-command/data chain used by macro/download payload handling.

`ESC *r#B` at `0x0107fa` clears raster active byte `0x783182`, leaving raster origin/baseline/mode/scale/limit state intact so later resolution commands can take effect.

Rectangle graphics command edges are decoded in `generated/analysis/ic30_ic13_rectangle_graphics_flow.md`. `ESC *c#A/#B` store explicit positive dot width/height in `0x78316a` / `0x783166`, while missing or nonpositive values clear the corresponding state. `ESC *c#H/#V` convert decipoints through five 300-dpi subunits per decipoint, round up with the firmware's `+11` subunit bias, and store the same width/height words. `ESC *c#G` stores absolute nonzero area-fill id `0x78316e`; missing or zero clears it. A chained `ESC *c12a5b0P` byte-stream fixture now queues the same black selector-7 rule object as the modeled command state. `ESC *c#P` maps black rule, gray-scale, and HP-pattern selectors, clips the current-cursor rectangle against page extents, and queues a 14-byte rule-list object through `0x13386` / `0x133aa`; the black selector-7 path is rendered through `0x1f446` / `0x1f596`, including a band-crossing continuation case, and gray selectors `0..6` plus HP pattern selectors `8..13` are rendered through `0x1f446` / `0x1f4e0`, including sub-byte shifted, band-crossing, and two-band page-assembly HP-pattern cases.

`ESC &f#Y` at `0x00e112` stores the absolute parsed signed word into current macro id `0x783164`. `ESC &f#X` at `0x00dd08` uses that id with the 32-entry macro record pool at `0x782a98`: selector `0` starts definition, `1` stops definition, `2` executes, `3` calls, `4`/`5` enable/disable overlay, `6` deletes all, `7` deletes temporary, `8` deletes current id, and `9`/`10` mark temporary/permanent. Execute/call route through `0xe418`, which builds a data-chain frame with byte `+8 = 4` and byte `+9 = 2` or `3`. The executable harness now pins these command side effects and frame metadata, plus chained `ESC &f-123y0x1X`, `ESC &f123Y ESC &f0X ! CR ESC &f1X ESC &f2X`, `ESC &f123Y ESC &f0X ! CR ESC &f1X ESC &f3X`, `ESC &f123Y ESC &f0X ! CR ESC &f1X ESC &f4X ESC &f5X`, permanence/delete, delete-current, delete-all, and guard-state byte-stream fixtures that cover signed id assignment, definition payload storage, stop-kept cleanup, execute/call frame creation, overlay enable/disable state, selector `10` survival through delete-temporary, selector `9` making the record removable, selector `8` clearing only the current id, selector `6` clearing pool records, definition-mode and active-data-chain guard suppression, `0xa904` data-chain byte fetch and end-marker outer-source resumption for the stored execute payload, modeled printable/CR processing, and the page-record allocator/bridge shape for that payload; full replay of macro payload bytes through the live parser is still open.

`ESC &f#S` at `0x00f75e` uses the absolute parsed word as a cursor-stack selector. Selector `0` pushes the current horizontal cursor `0x782c8a` and the current vertical cursor plus `0x782dbe` as an 8-byte entry while the next-free pointer is below `0x782d36`; selector `1` pops while above stack base `0x782c96`, restores horizontal and vertical positions with current page-extent clamps, clears pending/right-limit flags, and flushes pending spans when enabled. Executable fixtures now pin push, pop, clamp, full-stack, empty-stack, and byte-stream `ESC &f0S`/`ESC &f1S` selector-path cases.

Primary and secondary font-selection commands share the same final handler stubs, with the `ESC (` versus `ESC )` distinction preserved by setup routines before mode 4. The final handlers call lower-level font-state routines around `0xc6ec..0xc930` and then common routine `0xc580`.

Primary and secondary font-designation commands use the same parser shape. `ESC (` calls setup `0x1201e`, which pushes slot word `0`; `ESC )` calls setup `0x12008`, which pushes slot word `1`; final bytes `@` through `^` dispatch to `0x120be`. That wrapper calls `0x1be22`, which computes the provisional PCL symbol word as `(parameter << 5) + final_byte - 0x40` and stores it at `0x782ef4 + 0x10*slot`. Normal symbol-set finals keep that word and call common refresh `0xc580`; final `X` restores the previous requested symbol word and calls `0x17708` for `ESC (#X` / `ESC )#X` font-ID selection; final `@` runs a numeric table where `3@` is the documented default-font command and `@0..@2` are firmware-supported table/copy variants. The active selected words later consumed by glyph-map patching are `0x783144` and `0x783146`; this path is detailed in `generated/analysis/ic30_ic13_active_symbol_set_flow.md`.

Downloaded-font command edges are now decoded in `generated/analysis/ic30_ic13_font_control_flow.md`. `ESC *c#D` normalizes the parsed signed word into current font id `0x782f2e`, mapping `-32768` to `0x7fff`. `ESC *c#F` dispatches values `0..6` through the table at `0x16db6`: values `0`, `1`, and `2` call all/current record release helpers, value `3` uses the current character/code word `0x782f30`, values `4` and `5` unmark/mark the current downloaded record by moving counts between `0x782782` and `0x782786`, value `6` runs active/current font-resource housekeeping, and other values no-op.

Page geometry and the first raster transfer path are now tracked in `notes/page-raster-imaging.md`. The important anchors are that `0x105d0` clips/consumes raster payload bytes, ensures the page/image root exists through `0x10084`, calls `0x13070` with the raster state block rooted at `0x783170`, and then `0x138de` copies host bytes into the queued raster object payload. Direct control-code cursor/page effects are documented in `generated/analysis/ic30_ic13_direct_control_code_flow.md`: `ESC &k#G` stores line-termination bits in `0x78318f`, CR/LF/FF consume those bits, and CR/LF/FF/HT/BS can update cursor coordinates, flush text spans, ensure/finalize page roots, or call the same context span update routines used by printable text. Normal printable text now has a live parser bridge in `generated/analysis/ic30_ic13_printable_text_path.md`: bytes flow through `0xa904` -> `0xda9a` -> `0x11774` -> `0xd04a`, then `0x1393a` builds source object `0x782d7e`. The paired post-source paths are documented in `generated/analysis/ic30_ic13_text_cursor_span_flow.md`: unflagged text uses `0xd140` / `0xd3b2` / `0xd4ac`, flagged text uses `0xd550` / `0xd824` / `0xd8fc`, and the queue handoffs reach `0x12f2e`. Text and rectangle/rule objects converge into the same page-object storage through `0x12714` / `0x12f2e` and `0x13386` / `0x13520`; `generated/analysis/ic30_ic13_compact_bucket_allocator.md` decodes the `0x1387c` compact bucket allocator under page-root `+0x1c`. The render bridge now runs through page/control records copied by `0x1edc6` into work records; its concrete queue/list/context-slot copy contract is documented in `generated/analysis/ic30_ic13_page_record_bridge.md`. `0x1efc2` classifies bucket objects so raster rows dispatch to `0x1f88e`, compact text/glyph objects dispatch through `0x1effe`, and rule lists render through `0x1f446` / `0x1f756`. Compact glyph and encoded raster span modes are summarized in `generated/analysis/ic30_ic13_render_subrenderers.md`; deterministic encoded raster expansion fixtures are generated in `generated/analysis/ic30_ic13_render_expansion_fixtures.md`; destination/clipping fixtures are generated in `generated/analysis/ic30_ic13_render_destination_fixtures.md`; compact glyph row-copy fixtures are generated in `generated/analysis/ic30_ic13_render_row_copy_fixtures.md`; `tools/render_fixture_harness.py` executes these primitive fixtures together, pins `0xa904` host byte fetch source-priority fixtures, pins `0xdaf0`/`0xdb74` tokenizer records, `0x121cc` delayed-payload snapshots, and `0x1228a`/`0x12358` alternate payload byte-count consumers, pins synthetic direct control-code packed-state behavior for `ESC &k#G` plus CR/LF/FF/HT/BS, adds narrow direct-control byte-stream fixtures for `ESC &k1G`+CR, `ESC &k2G`+LF, `ESC &k2G`+FF, `ESC &k3G`+CR/LF/FF, `ESC &k0G`+HT/BS, `ESC &f0S`/`ESC &f1S`, chained `ESC &a3.5c+1R`, and `ESC &a6l9M`, adds synthetic `ESC E` reset byte-stream fixtures for valid-page-root publication and missing-root clearing, feeds four real built-in glyph bitmaps through the main `0x1f08e` row-copy table, includes a producer-modeled short text bucket fixture plus short and segmented `0x1387c` page-record allocator checks and a `0x1edc6` page-record bridge fixture that copies the compact bucket/context slots and normalizes the rule/fixed lists and pins producer-shaped `0x13386`/`0x136d2` rule objects, adds parser-derived `ESC *t#R`/`ESC *r#A` raster state fixtures plus modeled `ESC *t300R`/`ESC *r1A`/`ESC *b4W`, `ESC *t150R`/`ESC *r0A`/`ESC *b2W`, `ESC *t100R`/`ESC *r0A`/`ESC *b2W`, and `ESC *t75R`/`ESC *r0A`/`ESC *b2W` command/data stream fixtures plus a two-payload `ESC *t300R`/`ESC *r0A` multi-row stream through delayed handler `0x0105d0`, same-group lowercase-final chaining fixtures for `ESC *t300r150R` and chained `ESC *b2w`/`2W` payloads, plus a bare `ESC *rB` active-clear stream through handler `0x107fa`, byte-aligned mode-0, non-byte-aligned mode-0, mode-1, byte-aligned mode-2, non-byte-aligned mode-2, band-clipped mode-2, and mode-3 raster row fixtures through `0x13070` / `0x13250` / `0x138de` / `0x1edc6` / `0x1f88e`, covers normal and negative-left-overflow `0xd824` positioned text bucket fixtures for the `0x14d9c` base-map -> `0x1393a` source-object -> `0x12f2e` queue -> `0x1effe` / `0x1f034` render path, adds one-byte and two-byte normal printable stream fixtures for host byte `0x21` (`!`) through source mapping, positioning, packed default cursor advance, same-bucket compact queueing, and rendering, pins `0xd3b2` unflagged positioning arithmetic for both context-metric branches, adds a selected inline/downloaded map/source fixture through `0x14e24`/`0x14eb6` -> `0x1393a` -> `0xd3b2` -> `0x12f2e` -> render plus `0x168dc`/`0x16942` font payload-reader fixtures, `0x172c0`/`0x16c14` downloaded-font record bookkeeping fixtures, `0x170be`/`0x17108`/`0x17150` record lookup/mark/unmark fixtures, `0x15a56`/`0x16df6` font-id/control dispatch fixtures, and `0x16fae`/`0x17362`/`0x17026`/`0x1719c` validation-table/staged header/payload-backed inline allocation fixtures, keeps synthetic inline/downloaded `0x12f2e` short, page-record short, width-bit, and segmented payload objects, and renders synthetic `0x1f0d2` wide inline, `0x1f1f0` segmented inline, and `0x1f264` segmented-wide inline payload rows, pins the segmented `0x2000` producer/page-record objects for a real `LINE_PRINTER` `0x1f1f0` case, and verifies that all firmware-scanned tall built-in targets are mode-0/delta-0 record headers rather than normal bitmap entries.

`generated/analysis/ic30_ic13_esc_e_reset_flow.md` tracks the software reset boundary: `ESC E` runs text flush/page-root finalization before rebuilding environment state, refreshes current-font/HMI state through `0xcbd4`, resets parser/data-chain state through `0xe146`, and clears/reinitializes raster state at `0x783170`.

## Next RE Targets

- Feed the executable renderer harness with full parser-produced page-object payloads, building on the current one-byte, two-byte, and mixed printable/control/reset stream fixtures, mixed control/reset page-record allocator/bridge stream fixtures, parser-derived `ESC *t#R`/`ESC *r#A` raster state fixtures, modeled raster command/data stream fixtures for `ESC *t300R`, `ESC *t150R`, `ESC *t100R`, `ESC *t75R`, including a page-record bridge check for the first `ESC *b4W` object, a consecutive-row `ESC *t300R` stream, same-group lowercase-final chaining fixtures for `ESC *t300r150R` and `ESC *b2w`/`2W`, plus an `ESC *rB` active-clear stream, raster row page-record fixtures for byte-aligned mode 0, non-byte-aligned mode 0, mode 1, byte-aligned mode 2, non-byte-aligned mode 2, band-clipped mode 2, and mode 3, real-HMI sub-byte compact render fixture, producer-modeled short/segmented text bucket objects, short/segmented `0x1387c` allocator fixtures, `0x1edc6` page-record bridge fixture, `0xd824`-positioned text fixture, synthetic `0xd3b2` positioning and inline/downloaded `0x12f2e` payload fixtures including synthetic `0x1f0d2` wide inline, `0x1f1f0` segmented inline, and `0x1f264` segmented-wide inline render rows, resource-ROM glyph, and `0x1f08e` row-copy fixtures.
- Replace the synthetic `ESC E` fixtures with parser-produced page-object fixtures to prove partial-page finalization and reset-visible page/control state from real queued objects.
- Broaden the narrow direct-control byte-stream fixtures into the full firmware parser path, then compare those against page size, orientation, and raster behavior to finish naming `0x782c8a` and `0x782c8e`.
- Compare page geometry constants from `generated/analysis/ic30_ic13_page_geometry_tables.md` against manual printable-area figures.
- Trace font handler stubs `0x012046..0x0120aa` into built-in resource ROM font selection and metrics lookup.
- Confirm whether the firmware-supported `0x1be22` `@0..@2` variants are exposed by any host-visible command dialect.
- Replace the modeled `ESC &f#X` macro-control fixtures with full replay of stored macro payload bytes through the live parser/data-chain path.
