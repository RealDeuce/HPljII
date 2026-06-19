# Reverse-Engineering Ledger

Goal: track the ROM facts needed to reproduce LaserJet II output from the same host byte stream, down to pixel placement and built-in raster data.

## Current Anchors

| Area | Current evidence | Status |
| --- | --- | --- |
| Raw ROM identity | Four verified TC531000P dumps with stable hashes | Anchored |
| ROM interleave | `IC30,IC13` is executable; `IC32,IC15` is resource/data | Anchored |
| CPU entry | 68000 reset PC `0x00000110` in `IC30,IC13` | Anchored |
| Exception handling | vector table targets RAM trampolines at `0x00780000` | Early hypothesis |
| Extension probing | firmware checks `0x200000` and `0x400000` for `PROG`; scans for `HEAD` records | Anchored, format unknown |
| Host byte fetch | routine `0x0000a904` returns bytes in `D7`; direct I/O path polls `0x8e01`, reads `0x8801`, waits on `0x8c01` | Anchored, register roles unknown |
| Main PCL parser | routine `0x00011774` dispatches bytes through mode-indexed parser tables at `0x112a4` and `0x116f6` | Anchored |
| PCL tokenizer | routines `0x0000da9a`, `0x0000daf0`, and `0x0000db74` parse ESC sequences, `0x20..0x3f` parameter/intermediate bytes, signs, decimal values, fractions, and continuation markers | Anchored |
| Direct control codes | parser mode 0 maps CR/LF/FF/HT/BS to handlers `0xf02c`, `0xf08c`, `0xf0f0`, `0xf1cc`, `0xf2a8`; `ESC E` maps to reset handler `0xcc52` | Anchored, handler internals incomplete |
| PCL command map | flattened generated map links high-value PCL commands to handlers for page geometry, raster, rectangles, font selection, and macros | Anchored, handlers need deeper annotation |
| Page geometry tables | page-size helpers at `0x9d16`, `0x9d4e`, `0x9d86`, and `0x9dbe` decode internal page codes into logical/physical 300 dpi extents | Anchored, variable names provisional |
| Raster/text/page-object path | `ESC *t#R`, `ESC *r#A`, `ESC *r#B`, and `ESC *b#W` map to handlers `0x10808`, `0x1075a`, `0x107fa`, and delayed handler `0x105d0` via `0x121cc`; raster bytes are copied by `0x138de` into queued page objects built by `0x13070`; text spans enter the same storage through `0x12714` / `0x12f2e`; rectangle/rule handlers share page-root queues through `0x13386` and related helpers; `0x1edc6` copies queued record pointers into render work records; `0x1efc2` classifies bucket objects; raster maps to `0x1f88e`, compact text/glyph buckets map through `0x1effe`, and rule lists map through `0x1f446` / `0x1f756`; compact glyph objects select render-record context slots copied from page-root `+0x2c` and traced in `generated/analysis/ic30_ic13_font_context_bridge.md`; compact and encoded-span payload modes are named in `generated/analysis/ic30_ic13_render_subrenderers.md`; deterministic encoded raster expansion fixtures are generated in `generated/analysis/ic30_ic13_render_expansion_fixtures.md`; destination/clipping fixtures are generated in `generated/analysis/ic30_ic13_render_destination_fixtures.md`; compact glyph row-copy fixtures are generated in `generated/analysis/ic30_ic13_render_row_copy_fixtures.md`; `tools/render_fixture_harness.py` executes those primitive models plus real built-in glyph-resource resolutions and emits `generated/analysis/ic30_ic13_renderer_fixture_harness.md` | Anchored through render dispatch plus executable expansion/destination/row-copy/resource-resolution fixtures; full glyph bitmap rendering and page-object integration incomplete |
| Resource ROM role | `IC32,IC15` contains `HEAD`, HP copyright, `COURIER`, `LINE_PRINTER`, dense font tables, and firmware-scanned `0x1f354` glyph entries documented in `generated/analysis/ic32_ic15_resource_glyph_probe.md`; built-in context examples `0x4008004c`, `0x44080418`, and `0x440946b4` resolve to concrete glyph entries and bitmaps in `tools/render_fixture_harness.py` | Anchored as font/resource source; character/symbol-set index mapping incomplete |
| Font candidate selection | resource scanner `0x1a2e4..0x1ab82` builds font candidate lists; selectors around `0x14398..0x156de` choose/filter current font resources via `0x78287c`, `0x7827b8`, and `0x7828a8`; selected candidate longwords are copied into current-font context records at `0x782ee6` / `0x782ef6`, installed into page-root `+0x2c` slots, copied to render-record `+0x24`, and loaded into `0x783a2c` before `0x1f354`; built-in selected-context low 24-bit addresses map to `IC32,IC15` offsets by subtracting `0x80000`, and table entries are relative 32-bit glyph-entry offsets from that record start | Anchored as font/resource path and render-context bridge, rejected as raster compositor |
| Formatter manuals | Existing notes summarize PCL Level IV, I/O, formatter, NVRAM, page geometry, and errors | Anchored |

## Host Interface to Parser

Known from manuals:

- Host input can arrive through Centronics, RS-232C, or RS-422 paths.
- The renderer target can normalize these to a byte stream once flow control and status side effects are out of scope.
- PCL Level IV parser behavior is the main host-facing compatibility target.

ROM work needed:

- Trace callers of byte-fetch routine `0x0000a904` and name the host I/O registers `0x8801`, `0x8c01`, and `0x8e01`.
- Trace the handler at `0x00000d52`, which polls low MMIO/status addresses and updates many `0x0078xxxx` state bytes.
- Identify input buffer structures in RAM.
- Decode tokenizer records rooted at `0x78299e` and the 32-entry command/data pool at `0x782a98`.
- Expand normal parser table `0x112a4` and alternate parser table `0x116f6` into named PCL commands.
- Trace CR/LF/FF/HT/BS and `ESC E` handlers into cursor/page state and renderer-visible effects.
- Trace binary payload modes, especially raster graphics and downloaded font data.
- Use `notes/pcl-command-map.md` to prioritize page geometry, raster, rectangle, font, and macro handlers.
- Record malformed/combined escape behavior that is not explicit in the manuals.

## Print Environment and Page Model

Known from manuals:

- The renderer model needs factory defaults, user defaults, modified print environment, cursor stack, font state, macro state, logical page, printable area, and 300 dpi bitmap placement.

ROM work needed:

- Locate default environment tables.
- Compare ROM geometry constants in `notes/page-raster-imaging.md` against Technical Reference figures 2-2 and 2-3.
- Trace reset paths for `ESC E`, panel reset, power-on reset, and NVRAM/user defaults.
- Trace cursor push/pop and primary/secondary font fallback interactions.

## Fonts and Glyph Imaging

Expected resource ROM contents:

- Built-in bitmap font rasters.
- Metrics, pitches, baselines, cell sizes, offsets, style metadata.
- Symbol-set maps and internal character conversions.

ROM work needed:

- Finish decoding the resource scanner around `0x1a2e4`, `0x1a616`, and `0x1a9be`.
- Trace font candidate selection/filtering around `0x14398`, `0x14c64`, `0x1519a`, `0x153c6`, and `0x1569c`.
- Decode the `HEAD` record scanner at firmware routine `0x0000041a`.
- Use the repeated `COURIER` and `LINE_PRINTER` records as first built-in font extraction fixtures.
- Trace the character-code and symbol-set mapping that produces the compact object glyph index byte consumed by `0x1f354`.
- Extend real glyph fixtures from resource resolution to complete row-copy bitmap rendering.
- Extract glyph metrics and render a known self-test/font sample.
- Confirm symbol-set mapping for ASCII, Roman-8, line draw, and any built-in alternatives.
- Build extraction scripts that emit deterministic fixture data for the renderer.

## Raster and Final Imaging

Known renderer boundary:

- We need page pixels/PDF output, not full DC controller mechanics.

ROM work needed:

- Extend `tools/render_fixture_harness.py` from real glyph-resource resolution to full rendered glyph row comparisons.
- Integrate executable row-copy behavior with real page objects from the parser/imaging path.
- Trace text-object glyph-index production enough to feed realistic selected-context longwords and glyph indices to those fixtures.
- Treat direct `0x78297a` references and pool aliases documented in `generated/analysis/ic30_ic13_page_root_references.md` as checked leads; the active render bridge is documented in `generated/analysis/ic30_ic13_render_path_references.md`.
- Keep `0x78287c`, `0x7827b8`, `0x7828a8`, and dispatch around `0x14398..0x156de` under font/resource selection unless later evidence proves a separate imaging role.
- Trace how text, rules, raster data, and macros merge into final page pixels.
- Determine clipping and off-page behavior exactly.
- Identify any banding/compression structures used internally; reproduce final pixel result rather than formatter timing.

## Working Rules

- Keep raw ROMs and generated disassembly local-only.
- Track manifests, scripts, and annotated findings.
- When a ROM-derived behavior is implemented in a renderer, add a fixture byte stream and expected pixel/hash result.
- Prefer narrow extraction scripts over one-off manual tables so every claim can be regenerated from the verified ROM hashes.
