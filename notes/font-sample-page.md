# Font Sample Page Generator

This note documents the LaserJet II firmware font-sample printout path as a
semantic checkpoint. It covers the internal generator from resource candidate
windows through printable row bytes, page-record objects, and rendered segment
surfaces.

Status: composed for the normal source/class printout loop and the major
continuation-page object forms. This is firmware-generated text, not host
input: the path calls the ordinary printable handler `0xd04a` directly after
selecting and formatting ROM/resource records.

## Evidence

- `generated/analysis/ic30_ic13_font_sample_page.md`
- `generated/analysis/ic30_ic13_renderer_fixture_harness.md`
- `generated/analysis/ic32_ic15_builtin_font_samples.md`
- `generated/analysis/ic32_ic15_builtin_glyph_payloads.md`
- `generated/analysis/ic32_ic15_font_records.md`
- `generated/disasm/ic30_ic13_font_sample_page_01c170.lst`
- `generated/disasm/ic30_ic13_font_sample_row_helpers_01d198.lst`
- `generated/disasm/ic30_ic13_font_page_setup_01e0b2.lst`
- `generated/disasm/ic30_ic13_font_resource_object_lookup_01b4c0.lst`
- `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`
- `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`
- `notes/semantic-state-model.md` section
  `Built-In Font Sample Printout Loop`
- `notes/resource-rom.md`

Primary fixtures:

- `font sample built-in row fields format through 0x1cabe`
- `font sample Courier row fields cross page-record placement`
- `font sample Courier row fields and run 1 share page-record state`
- `font sample Courier row fields carry run 1 through 0x1d050 to run 2`
- `font sample carried run 2 buckets render through 0x1ed84 and 0x1ef6a`
- `font sample source heading carries default plus first two Courier rows`
- `font sample resolver carries first two Courier rows`
- `font sample run 1 prefix crosses page-record render entry`
- `font sample run 1 full row spans compact buckets`
- `font sample run 2 full row spans compact buckets`
- `font sample non-internal source groups follow modes 0..2`
- `font sample source headings 0..2 compose page records`
- `font sample full printout source placement follows firmware order`
- `font sample full printout rows reuse ROM sample byte runs`
- `font sample full printout segments render through 0x1ed84 and 0x1ef6a`
- `font sample first internal source group follows 0x1c334 row loop`
- `font sample internal class-one source group follows 0x1c334 row loop`
- `font sample page-limit branches trigger continuation calls`
- `font sample heading continuation emits fresh source heading page record`
- `font sample cartridge heading continuations emit source-specific page records`
- `font sample row continuation emits fresh source heading page record`
- `font sample class-one row continuation emits fresh source heading page record`
- `font sample alternate row fit gate follows 0x1d868`
- `font sample multi-probe preflight follows 0x1dcf2`
- `font sample alternate-row continuation emits preadvanced row page record`

## Field Groups

Canonical candidate/sample state:

- `0x78278e`: accepted resource count checked by `0x1c204`.
- `0x782798` / `0x782790`: class-zero and class-one pass counts tested by
  `0x1c28e..0x1c2c4`.
- `0x7827ac` / `0x78279a`, `0x7827b0` / `0x78279c`, `0x7827b4` /
  `0x78279e`, `0x7827a0` / `0x782792`, `0x7827a4` / `0x782794`, and
  `0x7827a8` / `0x782796`: first- and second-window candidate pointer/count
  pairs selected by `0x1b50e`.
- Current and alternate selected contexts installed by `0x1c5e8` /
  `0x1cece` and consumed by `0xd04a`.
- Sample run tables `0x1c1cf` and `0x1c1e9`, emitted by `0x1cf34`.
- Source/category labels selected by `0x1ca2c` from pointer table `0x1c170`.

Canonical page/text environment:

- Current page root ensured by `0x10084`.
- Page-root context slots written through `0xc428` and consumed by
  `0x12f2e`.
- Current vertical cursor `0x782c8e`, initialized by `0x1c916`.
- Page-limit word `0x782db6`, checked by `0x1ca2c`, `0x1d050`, `0x1d868`,
  and `0x1dcf2`.
- Row-height/cache word `0x783f06`, written by `0x1ca2c` and adjusted by
  `0x1d050`.
- Sample-page VMI/HMI defaults forced by `0x1e0b2` and `0x1c916` through
  `0x783160` / `0x78315c`.

Parser scratch:

- `0x1d76c` synthesizes a six-byte orientation command record at `0x78299e`
  before calling normal orientation handler `0x10220`.
- `0x7828a0`, `0x7828a4`, and `0x78289f`: fast-probe selected slot,
  caller-visible candidate word, and primary/secondary selector scratch used
  by `0x1b8ea` and `0x1b50e`.
- `0x7828ac` and requested symbol word `0x7821a0`: Roman-8 substitution
  scratch used by `0x1b5a4..0x1b706`.

Firmware bookkeeping:

- `0x783f02..0x783f05`: per-source status bytes written by the row loop.
- `0x783f08`: recent-context count byte.
- `0x783f0a`: recent-context list maintained by `0x1c9b8` and
  `0x1c540..0x1c5c6`.
- Local page-break word `-6(A6)`: receives the return flag from `0x1cf34`.

Derived/cache state:

- `0x1d050` derives row-to-row y advance from selected line advance, current
  row height, prior `0x783f06`, and `0x782db6`.
- `0x1cf34` derives the run-2 x origin by resetting x through `0xf06e`,
  advancing vertically through `0x1d050`, then adding `0x31` horizontal units
  through `0x1d152`.
- `0x1d868` derives the selected/alternate row fit flag consumed by the
  `0x1c4a4..0x1c4f2` continuation caller. Fixture
  `font sample alternate row fit gate follows 0x1d868` pins clear
  `0x783132` as D7 `0` and set `0x783132` as a projected-bottom comparison
  against `0x782db6`.
- `0x1dcf2` derives the later multi-probe current/alternate fit decision
  through shared calculator `0x1dc38`, including reset-y mode `1` probing
  before returning to the caller at `0x1d964`.
- Page-record bucket sets and object hashes are derived render-facing
  artifacts, not canonical firmware fields.

Unknown:

- Full physical comparison against a known printed/self-test sample.
- Forced continuation variants remain future regression work unless they
  expose a page-object form different from the covered heading-preflight,
  cartridge heading, class-zero/class-one row-overrun, and alternate-row
  continuation forms.
- Manual-facing names for record `+0x28/+0x2a` and `+0x2f..+0x31`; their ROM
  roles are known from `0x1519a` and `0x1428c`.

## Writers

- `0x1e0b2` is the normal setup entry. It checks font-record availability,
  clears copy/wrap/perforation state, rebuilds orientation and page-root state,
  writes sample-page VMI/HMI defaults, chooses the starting vertical cursor,
  and passes a derived remaining-row count to `0x1ea4e`.
- `0x1c204` starts the printout and reports status `0xe3/0x51` when no font
  records exist.
- `0x1c28e..0x1c344` run class-zero and class-one passes, skipping empty
  classes and ejecting between passes through `0xf0f0`.
- `0x1c2fe..0x1c332` iterate source groups `0..3` for each pass.
- `0x1c354..0x1c5e4` walk one source group: emit the source heading, ask
  `0x1b50e` for row ordinals, filter class/orientation through `0x1c710`,
  start continuation pages through `0x1c9f6`, and advance row index up to
  `0x63`.
- `0x1c5e8` installs the selected resource into current-font/page-root state,
  rebuilds maps through `0x14c64`, and refreshes the page-root font slot
  through `0xc428`.
- `0x1ca2c` emits source/category headings and writes row-height state.
- `0x1cabe` emits row prefix, name/style, pitch/height, symbol-set text, and
  sample columns through `0xd04a`, `0xd0f0`, and `0x1d152`.
- `0x1cf34` emits sample run 1, optionally moves to the alternate sample row,
  emits sample run 2, and writes the caller's page-break flag.

## Readers And Consumers

- `0x1b50e` consumes source mode and row ordinal, first tries fast probe
  `0x1b8ea`, then scans mode-specific first and second candidate windows.
- `0x1b750` / `0x1b7b2` classify candidates before `0x1b50e` exposes them.
- `0x1c746`, `0x1c766`, `0x1c7a8`, and `0x1c710` normalize candidates,
  extract flags, and test class/orientation before visible row emission.
- `0x1d198`, `0x1d5fa`, `0x1d6ea`, and `0x1d71e` consume resource/name fields
  and local lookup tables to produce sanitized printable bytes.
- `0x1d868`, `0x1d8ba`, `0x1d964`, and `0x1dcf2` consume cursor and page-limit
  state to preflight current and alternate sample-row placement.
- `0xd04a`, `0x1393a`, `0xd824` / `0xd3b2`, `0x12f2e`, `0x1ed84`, and
  `0x1ef6a` consume the emitted bytes as ordinary text objects and rendered
  rows.

## Output Effect

The sample page prints source headings, row IDs, font names, pitch/height,
symbol-set labels, and two ROM sample byte runs for each selected candidate
row. It is not a linear dump of resource records. `0x1b50e` applies fast
probe, two-window scanning, class filters, current-slot suppression, and
Roman-8 duplicate/substitution rules before a row reaches `0x1cabe`.

Fixture `font sample source heading carries default plus first two Courier
rows` pins the actual internal-source start: `INTERNAL FONTS`, row
`I00LINE PRINTER10128U`, row `I01COURIER101210U`, row
`I02COURIER101211U`, context slots `[0x4008004c, 0x44080418, 0x44080868]`,
and page-record buckets `[0, 2, 3, 4, 6, 7, 10, 11, 13, 14, 15, 18, 21,
22, 23]`.

Fixture `font sample built-in row fields format through 0x1cabe` covers the
row-field formatting cluster before the sample bytes for both a named
`COURIER` row and a named `LINE_PRINTER` row. The first `LINE_PRINTER` record
`0x0146b4` / context `0x440946b4` emits prefix `I07`, name `LINE_PRINTER`,
pitch `16.6`, height `8.5`, symbol `10U`, printable bytes
`49 30 37 4c 49 4e 45 5f 50 52 49 4e 54 45 52 31 36 2e 36 38 2e 35 31 30 55`,
three fixed-space calls through `0xd0f0`, and eight explicit horizontal units
through `0x1d152`. The height value is rounded by the mode-1 `0x1cc6e`
add-five path.

Fixture `font sample non-internal source groups follow modes 0..2` covers
the other source selectors in the same `0x1c334..0x1c5e4` row loop. Source
`0` uses resolver mode `0` for `"PERMANENT" SOFT FONTS`, emits no rows in
either class pass, and writes `0x783f02 = 1`. Source `1` uses mode `1` for
`LEFT FONT CARTRIDGE`; source `2` uses mode `2` for `RIGHT FONT CARTRIDGE`.
Both cartridge sources emit only request-`0` rows in each class pass, then
write `0x783f03 = 1` and `0x783f04 = 1`.

Fixture `font sample source headings 0..2 compose page records` carries
those source labels through page-record production. Source `0` queues a
heading-only record with aggregate object digest
`89fb4143a293f80bb8c07bab86d5c94940ba73039f2bd9ba1e3de0c2c6c4fb4c`.
Source `1` queues `LEFT FONT CARTRIDGE` plus `L00LINE PRINTER10128U`, with
class-zero/class-one digests
`cc583ac71b083d3cf241a1a72ff6345e22d585a9eef1a0ba850427b6d43e2aba` /
`51dade4f3a0af13cb533c9f62c5ea955a63f02046622e39a00b4ac8b072f63d6`.
Source `2` queues `RIGHT FONT CARTRIDGE` plus `R00LINE PRINTER10128U`, with
digests
`eaf10ca6b5b5716170b313ce542df82a6974c1ac22ee0e87308dead7be22c6a1` /
`3d23d5c6c5320d406d1db34523d3ad01c819d4e938e3dee4fa0a5d20747ed152`.

Fixture `font sample full printout source placement follows firmware order`
composes all eight source/class segments `(0,0)..(1,3)`: row counts
`[0, 1, 1, 14, 0, 1, 1, 14]`, context-slot counts
`[1, 1, 1, 12, 1, 1, 1, 12]`, page-record bucket counts
`[3, 13, 13, 142, 3, 12, 12, 122]`, and aggregate segment digest
`f4105538bd1506731f04810ed2f50cce23815751c4f979ed6f60efab4cde08c7`.

Fixture `font sample full printout rows reuse ROM sample byte runs` proves
every emitted row in those non-empty segments queues run table `0x1c1cf` and
run table `0x1c1e9`, with aggregate correlation digest
`4f664dc44f9ad98cbe25d4bdead651a2902bec1f90367c650bb2d1352d6f3e8a`.

Fixture `font sample full printout segments render through 0x1ed84 and
0x1ef6a` renders all eight page-record segments through the bridge and band
renderer. It pins render-bucket counts `[1, 6, 6, 65, 1, 5, 5, 50]`,
rendered bucket-row totals `[33, 210, 210, 2012, 33, 146, 146, 1257]`, and
surface digest
`5e5e735b4fb2a2a4dff4794099a02eaf23fa2dd3e469df8d053db88a321ea6f2`.

Fixture `font sample page-limit branches trigger continuation calls` pins
the shared page-limit state block before the forced page-object cases. At
heading entry, `0x1ca2c` compares cursor y word `32` plus row height `13`
against `0x782db6`: limit `45` calls `0x1c9f6`, while limit `95` stays on
the current page. At row advance, `0x1d050` moves first `COURIER` from y
`0x00520000` to `0x00900000`; limit `100` calls `0x1c9f6` and then
`0x1ca2c(source=3,row=1,current=0x4008004c,selected=0x44080418)`, while
limit `1010` does not.

Fixture `font sample alternate-row continuation emits preadvanced row page
record` covers the `0x1d868` D7 `1` caller path
`0x1c4a4 -> 0x1d868 -> 0x1c4b6 -> 0x1c9f6 -> 0x1c4ca -> 0x1ca2c ->
0x1c4d4 -> 0xf06e -> 0x1c4e8 -> 0x1d050 -> 0x1c4f2 -> 0x1cabe`. It emits
`I01COURIER101210U` after pre-row y advance
`0x00520000 -> 0x00900000` and pins bucket digest
`c6f0cbe07a7681d3ecfd3447b8296e97cbf8042d6d962d825f6018d980d5396b`.

## Reproduction Contract

A byte-stream-to-pixels renderer that also supports firmware-generated sample
pages must preserve:

- `0x1e0b2` setup side effects before `0x1c204` printing;
- source/class pass order `0x1c28e..0x1c344`;
- source-group iteration and per-source status bytes `0x783f02..0x783f05`;
- `0x1b50e` fast-probe, two-window scan, current-slot suppression, and
  Roman-8 duplicate/substitution behavior;
- selected context install through `0x1c5e8`, `0x14c64`, and `0xc428`;
- row-field formatting through `0x1cabe` and its printable/fixed-space/cursor
  split;
- sample run tables `0x1c1cf` and `0x1c1e9`;
- row-to-row and alternate-row placement through `0x1d050`, `0x1d868`, and
  `0x1dcf2`;
- source `0..3` resolver modes and source-status writes
  `0x783f02..0x783f05`;
- page-record and render bridge consumption through `0x12f2e`, `0x1ed84`,
  and `0x1ef6a`.

## Confidence

High for helper roles, loop order, candidate-row traversal, current-font setup,
printable byte emission, source `0..3` behavior, page-record placement,
rendered segment surfaces, and the major forced-continuation object forms
because each is backed by named fixtures and disassembly. Medium for physical
baseline/cell interpretation because comparison against a known printed/self-test
sample remains open.

## Remaining Edges

- `0x1c334..0x1c5e4`: no unresolved middle edge remains for the normal
  source/class row traversal currently modeled. Additional forced-continuation
  streams should be treated as regression cross-products unless they expose a
  page-object form outside the covered heading-preflight, cartridge heading,
  internal class-zero row-overrun, internal class-one row-overrun, and
  alternate-row cases.
- `0x1c5e8..0x1ef6a`: selected resource setup, row formatting,
  printable-byte emission, page-record queueing, bridge, and render dispatch
  are documented for the composed segments. Remaining work is external
  comparison against a known physical/self-test page.
- Record `+0x28/+0x2a`: consumed by `0x1519a` through `0x13bca` as decoded
  height inputs; manual-facing baseline/cell naming remains open.
- Record `+0x2f..+0x31`: consumed by `0x1428c` after `0x14398` / `0x13c06`
  as same-class chooser tie-breakers; manual-facing names remain open.
