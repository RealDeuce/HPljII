# PCL Command Map from Firmware

Sources: `generated/analysis/ic30_ic13_pcl_command_map.md`; `generated/analysis/ic30_ic13_parser_dispatch_tables.md`; focused listings under `generated/disasm/`; `notes/pcl4-language.md`.

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
| `ESC E` | `0x00cc52` | PCL reset and environment reinitialization |
| CR `0x0d` | `0x00f02c` | horizontal cursor reset/line-termination interactions |
| LF `0x0a` | `0x00f08c` | vertical cursor movement |
| FF `0x0c` | `0x00f0f0` | page eject and page-buffer boundary |
| HT `0x09` | `0x00f1cc` | tab and horizontal cursor positioning |
| BS `0x08` | `0x00f2a8` | backspace cursor behavior |
| `ESC &l#A` | `0x00fc74` | page size; maps PCL values to internal paper codes |
| `ESC &l#O` | `0x010220` | orientation; rebuilds page geometry and cursor state |
| `ESC &l#C` | `0x00cb00` | VMI |
| `ESC &l#D` | `0x00c992` | lines per inch |
| `ESC &l#E` | `0x00ece2` | top margin |
| `ESC &l#F` | `0x00ea9e` | text length |
| `ESC &l#H` | `0x00ef62` | paper source and page eject |
| `ESC &a#L` | `0x00eb58` | left margin |
| `ESC &a#M` | `0x00ec0c` | right margin |
| `ESC &a#C` | `0x00f39e` | horizontal column position |
| `ESC &a#H` | `0x00f416` | horizontal decipoint position |
| `ESC &a#R` | `0x00f560` | vertical row position |
| `ESC &a#V` | `0x00f60a` | vertical decipoint position |
| `ESC &k#H` | `0x00ca8c` | HMI |
| `ESC &k#G` | `0x00edf8` | CR/LF/FF line-termination mode |
| `ESC &f#S` | `0x00f75e` | cursor push/pop |
| `ESC &f#Y` | `0x00e112` | macro ID |
| `ESC &f#X` | `0x00dd08` | macro control |
| `ESC *t#R` | `0x010808` | raster resolution |
| `ESC *r#A` | `0x01075a` | start raster graphics |
| `ESC *r#B` | `0x0107fa` | end raster graphics |
| `ESC *b#W` | `0x011f82` | transfer raster row bytes |
| `ESC *c#P` | `0x010898` | fill rectangle |
| `ESC *c#A` | `0x010e68` | rectangle width in dots |
| `ESC *c#B` | `0x010e22` | rectangle height in dots |
| `ESC *c#H` | `0x010a40` | rectangle width in decipoints |
| `ESC *c#V` | `0x010ae0` | rectangle height in decipoints |
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

It then rebuilds page-related state, including `0x782da2`, `0x782db2`, `0x782db4`, `0x782dc0`, `0x782dce`, and `0x782dd0`, and calls shared reset/layout helpers also seen in `ESC E`.

`ESC &l#O` at `0x010220` accepts orientation values below `2`, updates `0x782da3`, rebuilds page geometry, updates `0x783160`, and reloads current font/metrics state through tables rooted near `0x782ee6` / `0x782ef6`.

`ESC *r#A` at `0x01075a` starts raster graphics by setting state in the block rooted at `0x783170`; it seeds a raster baseline from `0x782c8a` or `0x782c8e` depending on current mode.

`ESC *b#W` at `0x011f82` routes through `0x121cc` with handler `0x105d0`, so raster row byte transfer is tied into the same parsed-command/data chain used by macro/download payload handling.

Primary and secondary font-selection commands share the same final handler stubs, with the `ESC (` versus `ESC )` distinction preserved by setup routines before mode 4. The final handlers call lower-level font-state routines around `0xc6ec..0xc930` and then common routine `0xc580`.

Primary and secondary font-designation commands use the same parser shape. `ESC (` calls setup `0x1201e`, which pushes slot word `0`; `ESC )` calls setup `0x12008`, which pushes slot word `1`; final bytes `@` through `^` dispatch to `0x120be`. That wrapper calls `0x1be22`, which computes the provisional PCL symbol word as `(parameter << 5) + final_byte - 0x40` and stores it at `0x782ef4 + 0x10*slot`. Normal symbol-set finals keep that word and call common refresh `0xc580`; final `X` restores the previous requested symbol word and calls `0x17708` for `ESC (#X` / `ESC )#X` font-ID selection; final `@` runs a numeric table where `3@` is the documented default-font command and `@0..@2` are firmware-supported table/copy variants. The active selected words later consumed by glyph-map patching are `0x783144` and `0x783146`; this path is detailed in `generated/analysis/ic30_ic13_active_symbol_set_flow.md`.

Page geometry and the first raster transfer path are now tracked in `notes/page-raster-imaging.md`. The important anchors are that `0x105d0` clips/consumes raster payload bytes, ensures the page/image root exists through `0x10084`, calls `0x13070` with the raster state block rooted at `0x783170`, and then `0x138de` copies host bytes into the queued raster object payload. Text and rectangle/rule objects converge into the same page-object storage through `0x12714` / `0x12f2e` and `0x13386` / `0x13520`. The render bridge now runs through page/control records copied by `0x1edc6` into work records; `0x1efc2` classifies bucket objects so raster rows dispatch to `0x1f88e`, compact text/glyph objects dispatch through `0x1effe`, and rule lists render through `0x1f446` / `0x1f756`. Compact glyph and encoded raster span modes are summarized in `generated/analysis/ic30_ic13_render_subrenderers.md`; deterministic encoded raster expansion fixtures are generated in `generated/analysis/ic30_ic13_render_expansion_fixtures.md`; destination/clipping fixtures are generated in `generated/analysis/ic30_ic13_render_destination_fixtures.md`; compact glyph row-copy fixtures are generated in `generated/analysis/ic30_ic13_render_row_copy_fixtures.md`; `tools/render_fixture_harness.py` executes these primitive fixtures together.

## Next RE Targets

- Feed the executable renderer harness with real resource-ROM glyph records and page-object payloads.
- Name cursor variables `0x782c8a` and `0x782c8e` by comparing CR/LF/FF, page size, orientation, and raster behavior.
- Compare page geometry constants from `generated/analysis/ic30_ic13_page_geometry_tables.md` against manual printable-area figures.
- Trace font handler stubs `0x012046..0x0120aa` into built-in resource ROM font selection and metrics lookup.
- Confirm whether the firmware-supported `0x1be22` `@0..@2` variants are exposed by any host-visible command dialect.
- Trace macro control handler `0x00dd08` into `ESC &f#X` behavior and interaction with the alternate/data parser table.
