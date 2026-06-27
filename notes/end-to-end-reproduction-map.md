# End-To-End ROM Reproduction Map

Goal: reproduce LaserJet II output pixels from the same host byte stream by
using ROM-derived parser behavior, state fields, page-record formats, and
render routines. This note is the current top-level map from host input to
imaging; detailed ledgers remain in `notes/reverse-engineering-ledger.md` and
`notes/semantic-state-model.md`.

## Pipeline Contract

```text
host bytes
  -> 0xa904 normalized byte fetch
  -> 0xda9a / 0xdaf0 / 0xdb74 parser and six-byte command records
  -> command handlers and delayed payload handlers
  -> page-root/display-list objects
  -> 0xff1e publication
  -> 0x1ed84 / 0x1edc6 render-record bridge
  -> 0x1ef6a band render dispatch
  -> compact text, segment-list, rule, fixed-width, and raster renderers
```

Every reproduction claim below requires both a ROM address boundary and an
executable fixture or generated analysis note.

## Current End-To-End Coverage

- Host byte source priority:
  ROM evidence is `0xa904..0xabf0` in
  `generated/disasm/ic30_ic13_host_byte_fetch_00a904.lst`.
  Reproduction evidence is
  `generated/analysis/ic30_ic13_host_byte_fetch_flow.md` and fixtures
  for no-byte, service retry, LIFO, data-chain, ring, and direct modes.
- Parser byte and command records:
  ROM evidence is `0xda9a`, `0xdaf0`, `0xdb74`, and `0x11774`.
  Reproduction evidence is `generated/analysis/ic30_ic13_parser_xrefs.md`
  plus tokenizer and delayed-payload fixtures.
- Parser dispatch tables:
  ROM evidence is normal table `0x112a4` and alternate table `0x116f6`.
  Reproduction evidence is `generated/analysis/ic30_ic13_pcl_command_map.md`
  and ROM dispatch trace fixtures.
- Direct controls and cursor state:
  ROM evidence includes `0xf02c`, `0xf06e`, `0xf34a`, and cursor handlers.
  Reproduction evidence is `Text Cursor And Direct Controls` in
  `notes/semantic-state-model.md` and host-fetched direct-control fixtures.
- Text source object creation:
  ROM evidence is `0xd3b2`, `0xd824`, `0x12f2e`, and `0x1387c`.
  Reproduction evidence is `Text Source Objects And Compact Buckets` and
  compact text bucket render fixtures.
- Pending text span flushing:
  ROM evidence is `0xd4ac`, `0xd8fc`, `0x126e2`, `0x12714`, and
  `0x13520`.
  Reproduction evidence is `Text Span Flush And Fixed-Width Spans` plus
  CR, low-water, split, nonempty, and retry fixtures.
- Page-root storage:
  ROM evidence is `0x10084`, `0x10110`, `0x1381c`, and `0x1387c`.
  Reproduction evidence is `Shared Page-Record Storage And Allocator`,
  addressed storage fixtures, and chunk-rollover fixtures.
- Rule/rectangle producers:
  ROM evidence is `0x10898`, `0x10b80`, `0x13386`, and `0x133aa`.
  Reproduction evidence is `notes/rectangle-graphics.md` and
  parser-to-rule fixtures.
- Raster producers:
  ROM evidence is `0x10808`, `0x1075a`, `0x105d0`, `0x13070`, and
  `0x13250`.
  Reproduction evidence is `generated/analysis/ic30_ic13_raster_graphics_flow.md`
  and host-fetched raster stream fixtures.
- Page publication:
  ROM evidence is `0xff1e..0x10080`.
  Reproduction evidence is
  `generated/analysis/ic30_ic13_page_root_finalization.md` plus reset,
  FF, geometry, and retry publication fixtures.
- Render bridge:
  ROM evidence is `0x1ed84`, `0x1edc6`, and `0x1ef86`.
  Reproduction evidence is `generated/analysis/ic30_ic13_page_record_bridge.md`
  and published-record render-entry fixtures.
- Render dispatch:
  ROM evidence is `0x1ef6a`, `0x1efc2`, `0x1f446`, `0x1f756`,
  `0x1f812`, and `0x1f88e`.
  Reproduction evidence is
  `generated/analysis/ic30_ic13_render_dispatch_tables.md` plus
  text/rule/raster composition fixtures.
- Mixed page-image stream:
  ROM evidence crosses parser handlers `0xd04a`, `0x10e68`,
  `0x10e22`, `0x10898`, `0x10808`, `0x1075a`, `0x11f82`, and
  `0xf0f0`, then publication and render handlers `0xff1e`,
  `0x1ed84`, `0x1edc6`, and `0x1ef6a`.
  Reproduction evidence is `Mixed Text/Rule/Raster Page Record` in
  `notes/semantic-state-model.md` plus fixtures
  `host-fetched text rectangle raster FF publishes rendered page record`,
  `addressed text rectangle raster FF publishes rendered page record`,
  and `addressed text/rule/raster field groups reach publication and
  render entry`.
- Built-in glyph data:
  ROM evidence is the IC32/IC15 resource ROM tables and bitmap records.
  Reproduction evidence is
  `generated/analysis/ic32_ic15_builtin_glyph_payloads.md` and compact
  glyph fixtures.
- Downloaded font payloads:
  ROM evidence is `0x15d0a`, `0x168dc`, `0x16942`, `0x16c14`, and
  `0x1719c`.
  Reproduction evidence is the font descriptor, resource, and character
  fixtures in `tools/render_fixture_harness.py`.

## Reproducible Byte-Stream Families

- Plain printable text and text with direct controls are covered from host
  bytes through parser, compact bucket objects, bridge, and rendered rows.
  Evidence: fixtures `plain printable parser trace feeds page-record queue`,
  `host-fetched mixed control stream reaches parser and page-record render`,
  and `host-fetched direct text/control streams feed 0x1ed84 and 0x1ef6a`.
- Page-geometry streams are covered for page size, orientation, nonzero
  page length, and the `ESC &l0P` zero-length default-page branch. Evidence:
  fixture
  `0xf9e8 ESC &l#P converts VMI lines to page length and selects internal
  page code`, `0xf9e8 ESC &l#P stream reaches page-length handler`,
  `mixed printable/page-size page-record stream publishes queued text`,
  and `mixed printable/orientation page-record stream publishes queued text
  before landscape change`.
- Raster graphics streams are covered for `ESC *t#R`, `ESC *r#A`, delayed
  `ESC *b#W`, lowercase transfer chaining, active-raster resolution behavior,
  row caps, beyond-extent drains, and modes 0/1/2/3. Evidence:
  `generated/analysis/ic30_ic13_raster_graphics_flow.md` and host-fetched
  raster fixtures.
- Rectangle/rule streams are covered for size commands, fill selectors,
  clipping, no-room retry, bridge normalization, and solid/pattern rendering.
  Evidence: `notes/rectangle-graphics.md` and parser trace fixtures for
  `ESC *c` rule streams.
- Reset, FF, page-size, orientation, paper-source, copies, and VFC publication
  paths are covered through `0xff1e` for current modeled page records.
  Evidence: `generated/analysis/ic30_ic13_esc_e_reset_flow.md`,
  `generated/analysis/ic30_ic13_page_root_finalization.md`, and publication
  fixtures in the harness.
- The initial mixed page-image suite is covered for one complete
  host-fetched byte stream:
  `! ESC *c12a5b0P ESC *t300R ESC *r0A ESC *b2W c3 3c FF`.
  It drains through the modeled `0xa904` ring source, routes through the
  parser handlers above, queues compact text, a selector-7 rectangle
  rule, and a mode-0 raster object into addressed page-record storage,
  publishes through `0xff1e`, crosses the `0x1ed84` / `0x1edc6`
  render bridge, and compares the final composed rows. Evidence:
  `Mixed Text/Rule/Raster Page Record` in `notes/semantic-state-model.md`.
- The modeled per-band renderer now covers a crossing patterned rule
  together with compact text and a mode-0 raster row. Fixture
  `0x1ef6a page-band walk merges text raster and crossing rule`
  dispatches bucket-array compact/raster objects, carries the mutated
  rule node from band `0`, renders the remaining rule rows in band `5`,
  and leaves no rule/fixed-list residue. This closes the modeled
  per-band merge for that heterogeneous case; remaining render risk is
  live engine pacing and physical output comparison.
- A downloaded-glyph page-image stream is covered for
  `ESC *c4660d37e5F`, `ESC )s2193W <0x0891 payload bytes>`, printable
  `%`, and FF publication. The fixture drains the same modeled `0xa904`
  source, preserves the control/payload/printable/publication byte
  boundaries, installs glyph `0x25`, publishes segmented buckets `1` and
  `9` through `0xff1e`, walks those published bucket words through
  `0x1ed84`/`0x1ef6a` band rendering, proves `0x1eba4` scheduler progression
  through band words `0..9`, and compares the published rendered rows with
  bucket `9` producing the visible downloaded row. Evidence: fixtures
  `combined font download FF publishes installed glyph page record`,
  `published downloaded glyph segmented buckets render across bands`, and
  `0x1eba4 scheduler band words render published downloaded glyph`, plus
  `Downloaded Font Descriptor And Payload Chain` in
  `notes/semantic-state-model.md`.
- Downloaded-glyph/rule/raster render composition is covered for the
  host-fetched `ESC )s18W` even-span wide glyph install and a parser-driven
  page stream `ESC *c12a3b0P ) ESC *t300R ESC *r0A ESC *b2W c3 3c`. Evidence:
  fixture `parser-driven downloaded glyph rule raster stream composes through
  0x1ef6a`, which asserts the font/page fetch boundaries, page handlers
  `0x10e68`, `0x10e22`, `0x10898`, `0xd04a`, `0x10808`, `0x1075a`, and
  `0x11f82`, the `0x12f2e` glyph object, bridged selector-7 rule object,
  `0x13070` raster object, `0x1ed84`/`0x1ef6a` call order, dispatch targets
  `0x1f88e` and `0x1effe`, rule helper `0x1f596`, and final composed rows.
- Built-in and downloaded text rendering is covered for selected offset-table,
  inline/downloaded fixed records, segmented records, segmented-wide records,
  font descriptors, resource payloads, downloaded character payloads, and
  host-fetched font-control state. Evidence:
  `generated/analysis/ic30_ic13_text_glyph_index_flow.md`,
  `generated/analysis/ic30_ic13_font_control_flow.md`,
  `generated/analysis/ic32_ic15_builtin_glyph_payloads.md`, and font fixtures.

## Canonical State Groups

- Host/input canonical state: `0x780e40`, `0x780e66`, `0x780e3b`,
  `0x783e54`, `0x783e56`, `0x783e76`, `0x783e78`, `0x783e8c`,
  `0x783e8e`, and `0x782d76`. Evidence:
  `generated/analysis/ic30_ic13_host_byte_fetch_flow.md`.
- Parser scratch: six-byte command records at `0x78299e..0x7829a7`,
  delayed handler snapshots, payload counters, and alternate/data mode state.
  Evidence: tokenizer fixtures and `generated/analysis/ic30_ic13_parser_xrefs.md`.
- Canonical print environment: cursor words `0x782c8a` and `0x782c8e`,
  HMI/VMI words, margins, page geometry fields under `0x782da2..0x782dc0`,
  line-termination mode, cursor stack, and font slot state. Evidence:
  `Text Cursor And Direct Controls` and page-geometry fixtures.
- Canonical page model: current page root `0x78297a`, page-root class byte
  `+4`, bucket array `+0x1c`, rule list `+0x24`, fixed-width list `+0x28`,
  context slots `+0x2c`, and stream allocator fields `0x782a70`,
  `0x782a72`, `0x782a76`. Evidence:
  `Shared Page-Record Storage And Allocator`.
- Derived/cache state: bucket/key bytes `0x782a7a..0x782a7e`, render-band
  fields `0x783a20`, `0x783a22`, `0x783a28`, pending span watermarks
  `0x783184..0x78318a`, and raster mode/scale caches. Evidence:
  `Text Span Flush And Fixed-Width Spans`,
  `generated/analysis/ic30_ic13_page_record_bridge.md`, and raster fixtures.
- Firmware bookkeeping: publication flag `0x782996`, page/root transient
  bytes `0x78297e`, `0x782c72`, `0x782c73`, retry flag bit in page-root
  `+0x14`, macro/data-chain frames, and heap/resource allocation metadata.
  Evidence: page-finalization, macro, allocator, and font-resource notes.

## Pixel-Perfect Blockers

These are the highest-value unresolved edges because each can change rendered
pixels or byte-stream compatibility.

1. Font/context producer ownership for span metric fields remains incomplete.
   The consumers are known: unflagged `0xd4ac` reads context `+0x2b`,
   `+0x2c`, `+0x2d`; flagged `0xd8fc` reads `+0x16`, `+0x18`, `+0x1a`.
   The selected-context bridge and current metric evidence boundary are
   documented in `notes/font-context-metrics.md`, and the downloaded
   descriptor/payload producer side is documented in `notes/downloaded-fonts.md`.
   Host-fetched `0x1719c` type-0, type-1, and type-2 payloads now prove copied
   descriptor bytes feeding both `0xd4ac` and `0xd8fc` visible span rows.
   Fixture `d4ac and d8fc span consumer branch family controls flush output`
   covers disabled, lower-bound, page-extent, and high-x consumer outcomes for
   both source forms. Fixture `host-fetched metric variant changes d4ac gate
   and d8fc rows` proves one parser-produced metric-value variant: copied
   `+0x2c/+0x2d` flips a tight `0xd4ac` page-extent gate, and copied `+0x1a`
   moves `0xd8fc` visible rows. Fixture `host-fetched clamped metric variant
   changes d4ac gate and d8fc rows` proves a second parser-produced variant:
   range/count `+0x14 = 5` clamps an oversized rounded metric input into
   `+0x2c/+0x2d = 0x0014`, leaves `+0x2b = 0`, flips another tight `0xd4ac`
   gate, and moves `0xd8fc` rows through copied `+0x18 = 0` and
   `+0x1a = 3`. Fixture `host-fetched lower-bound metric variant suppresses
   d4ac and d8fc spans` proves a third parser-produced variant: first code
   `+0x16 = 0x0018`, range/count `+0x14 = 0x0600`, derived count
   `+0x18 = 0x05e7`, and rounded word `+0x2c = 0x1800` make both consumers
   exit `before-context-lower` at cursor y `21` while the compact glyph
   objects remain queued and render. Fixture
   `host-fetched upper-bound metric variant keeps d4ac span but suppresses
   d8fc` proves a fourth parser-produced variant: range/count
   `+0x14 = 0x0040` derives/cache `+0x18 = 0x003b`, leaves unflagged
   `+0x2c/+0x2d = 0/0x20`, keeps `0xd4ac` span output, and makes `0xd8fc`
   exit `beyond-page-extent` at cursor y `21`. Seven bounded validation
   no-install forms now prove parser-to-validation failure, allocation skip,
   no candidate install, resumed default-font printable output, and matching
   rows. Fixture `descriptor metric fields match across inline and resource
   contexts` now proves inline/unflagged `d4ac`, resource/flagged `d8fc`, and
   the two invalid swapped forms. Fixture
   `legal descriptor metric value matrix drives d4ac and d8fc consumers`
   composes the legal small-rounded, clamped-rounded, midpoint-rounded,
   zero-rounded-offset, negative-offset, lower-bound, and upper-bound values;
   the zero case copies `+0x14/+0x18/+0x1a/+0x2c =
   0x0018/0x0013/0x0000/0x0000`, preserves the `d4ac` span digest
   `67554ea70d7cfd9b11c0777e3cf65d51600a44301a4f93bd4d9b0c0fbc23c00e`,
   and makes `d8fc` publish high-y `21` / row digest
   `47361fc76bd6284f9d764c0377a3fda64edd3944b5cb2dff72acfd2224bc25e8`. The
   midpoint case copies `+0x14/+0x18/+0x1a/+0x2c =
   0x0018/0x0013/0x0007/0x0018` and makes `d8fc` update high-y `14` while
   leaving compact-only digest
   `1a73b5e7454202d800c69f626bcf34e7d0d583b459e04c0bd4250010bf3ba28a`.
   The negative-offset case copies `+0x14/+0x18/+0x1a/+0x2c =
   0x0018/0x0013/0xfffe/0x0008`; `d8fc` consumes the copied offset word as
   `65534`, computes high-y `-65513`, and renders digest
   `72bfa14c2a84532e2bdf6fb8fddf26ed6904c49dcf4fdcb322592471b5d5b281`.
   The open edge is additional metric-value combinations within the legal
   forms, plus validation/error forms beyond those bounded predicate branches.
   It is not the tested type-0/type-1/type-2 payloads, metric-variant,
   clamped-variant, lower-bound-variant, upper-bound-variant,
   legal-value-matrix, validation no-install, legal producer-form boundary, or
   shared consumer branch family. Evidence:
   `notes/semantic-state-model.md` under `Text Span Flush And Fixed-Width
   Spans`.
2. VFC table definition and channel jumps now have a tracked command-family
   contract in `notes/vertical-forms-control.md`. The remaining VFC risk is
   broader final-device image comparison, not an unresolved middle edge in the
   documented `ESC &l#W` / `ESC &l#V` path.
3. Macro replay and the first overlay-publication path are anchored. The
   covered overlay path is selector `4` state through `0xff1e` re-entry,
   `0xe0a4`, `0xe4f4`, parser loop `0x11774`, and rendered page-record
   composition with an existing selector-7 rectangle rule. Remaining macro
   risk is broader overlay interaction coverage, such as repeated overlays
   across page boundaries and physical output comparison. Evidence: `Macro
   Definition And Data-Chain Replay` in `notes/semantic-state-model.md` and
   fixture `macro overlay finalization replays before page publication`.
4. Downloaded font support now has tracked documentation for descriptor,
   resource-payload, current-record, bit-30-clear resource-object,
   bit-30-clear even-span and split-plane continuation resume, status-0
   fixed-record release, bit-30 offset-table release delegate, split-plane
   character-object, linear character-object, and downloaded-glyph render paths
   in `notes/downloaded-fonts.md`. The `0x16c14` existing-record
   allocation-failure teardown through `0x1887a` is fixture-backed for the
   bit-30-clear extended fixed-record case. The `0x16fae` validation table now
   has ROM-effect names for all 32 entries plus concrete success and failure
   fixtures, and host-fetched invalid-resource-type, first-code overflow, zero
   line/count, high line/count, reversed-range, high range/count, and
   invalid-class paths prove parser-to-validation no-install boundaries plus
   following-printable default output. Downloaded-character coverage now
   includes parser-produced normal, wide/control, even-span wide, segmented,
   split-plane segmented, and segmented-wide compact render shapes, and the
   combined downloaded-glyph stream now reaches FF publication with both
   segmented buckets preserved and scheduler-produced band words `0..9`
   rendered. The full soft-font descriptor grammar, remaining alternate
   character-mode cross-products, other release variants, and page-visible
   behavior for descriptor error forms beyond those no-install boundaries are
   still not proven against every PCL form. The even-span downloaded-glyph
   plus rule/raster composition now has an exact modeled install-to-page
   handoff: host-fetched `ESC )s18W` produces the resource image consumed by
   the parser-driven page stream, including glyph `0x29`, table entry
   `0x00ee`, record delta `0x0780`, bitmap offset `0x078c`, and the 18 copied
   bitmap bytes. The still-open boundary is live CPU continuity from the
   `0x16c14` / `0x16498` install return after stream byte `24` back into
   parser loop `0x11774` for the following page bytes.
5. Hardware-facing host modes are behaviorally modeled above `0xa904`, but
   MMIO identity and electrical timing for Centronics/serial/RS-422 are not
   board-confirmed. This does not block a byte-stream renderer, but it blocks
   claims about hardware-level emulation. Evidence:
   `generated/analysis/ic30_ic13_host_byte_fetch_flow.md`.
6. Final device-output validation is not yet a real printer comparison. The
   harness proves ROM-derived rows internally, but pixel-perfect confidence
   ultimately needs rendered page images compared against known LaserJet II
   output for representative byte streams. The initial mixed page-image
   stream above is a ROM-derived internal reproduction contract, not a
   physical-device comparison. The font-sample printout now has its own
   internal rendered-surface checkpoint: fixture `font sample full printout
   segments render through 0x1ed84 and 0x1ef6a` renders all eight source/class
   page-record segments with aggregate digest
   `5e5e735b4fb2a2a4dff4794099a02eaf23fa2dd3e469df8d053db88a321ea6f2`.
   The remaining sample-printout gap is physical baseline/cell placement
   comparison against a known font/self-test page.

## Next Disassembly Targets

The next work should follow dataflow, not isolated handlers:

1. Prove the remaining font metric-byte combinations with parser-produced
   pages. The selected-context bridge, metric consumers, downloaded
   descriptor/payload producer chain, and host-stream downloaded glyph output
   are now tracked. Host-fetched `0x1719c` type-0, type-1, and type-2 payloads
   reach both `d4ac` and `d8fc` span rows, and the shared
   disabled/lower/page/high-x consumer branch family is fixture-backed. The
   seven-case legal descriptor metric matrix covers tight `d4ac` page-extent
   gates, rounded-metric clamping into `+0x2c/+0x2d`, shifted `d8fc` visible
   rows, a zero rounded/offset case where both consumers publish spans, a
   negative-offset case where `d8fc` consumes copied word `0xfffe`, a midpoint
   case where `d8fc` updates state but leaves compact-only output, a
   lower-bound no-span output path for both consumers, and an upper-bound case
   where `d4ac` still renders a span while `d8fc` exits `beyond-page-extent`.
   Fixture
   `descriptor metric fields match across inline and resource contexts` now
   pins the legal producer-form boundary: inline/unflagged reaches `d4ac`,
   resource/flagged reaches `d8fc`, and the swapped forms fail at concrete
   map/render boundaries. The missing middle is now additional metric-value
   combinations within the legal forms, plus page-visible behavior for
   validation/error forms beyond the seven bounded predicate no-install
   fixtures.
2. Broaden the page-image fixture suite beyond the current complete
   text/rule/raster/publication stream, downloaded-glyph FF publication stream,
   parser-driven downloaded-glyph/rule/raster page stream, primary plus
   secondary built-in font-selection visible-output streams, inline primary
   and secondary parser-to-printable streams, the primary and secondary symbol
   fallbacks, plus primary/secondary current-font-RAM handoff and composed
   selection-to-RAM handoff visible-output streams. The primary
   built-in case proves `ESC (s0p10h12v0s0b3T!!` through parsed selection
   handlers, selected context `0xc008004c`, printable `0xd04a` entries, object
   prefix `00 00 00 00 00 00 00 02 00 6a 00 00 68 02`, render-record context
   slot `0xc008004c`, and final Courier glyph rows. The secondary case proves
   `ESC )s0p16h8v0s0b0T SO !!` through selected context `0xc00ae122`, SO
   handler `0xc6b8`, object prefix
   `00 00 00 00 00 01 00 02 00 c9 00 00 cb 01`, render-record context slots
   `(0xc008004c, 0xc00ae122)`, and final secondary Line Printer rows.
   The primary fallback case proves `ESC (1234U ESC (s0p10h12v0s0b3T!!`:
   requested word `0x9a55` misses in `0x156de`, fallback word `0x0115`
   survives, and the final selected context, map, object prefix, context slot,
   and rows match the primary case. The secondary fallback case proves
   `ESC )1234U ESC )s0p16h8v0s0b0T SO !!`: requested word `0x9a55` misses in
   `0x156de`, fallback word `0x000e` survives, and the final selected
   context, map, object prefix, context slots, and rows match the secondary SO
   case.
   The primary RAM handoff case proves seeded
   `0x782ee6 = 0xc008004c` through SI `0xc68a`, `0xc428(0)`, `0xc4fc`,
   page-root slot `0`, and following `!!` visible rows on an existing root.
   The secondary RAM handoff case proves seeded
   `0x782ef6 = 0xc00ae122` through SO `0xc6b8`, `0xc428(1)`, `0xc4fc`,
   page-root slot `1`, and following `!!` visible rows on an existing root.
   The composed handoff cases prove `ESC (s0p10h12v0s0b3T SI !!` and
   `ESC )s0p16h8v0s0b0T SO !!` from host-fetched selection bytes to selected
   current-font RAM, page-root slot install, and rows matching the pinned
   visible fixtures. The inline cases prove `ESC (s0p10h12v0s0b3T!!` and
   `ESC )s0p16h8v0s0b0T SO !!` in one mixed-stream state from selection
   handlers to printable source capture, HMI, object prefix, bridge context
   slots, and rows. Remaining suite cases should add other fallback/error
   font-selection visible-output variants beyond those two symbol misses and
   transparent-data high-control variants beyond the covered primary short
   `0x80`, primary tall bucket-crossing `0x98`, and secondary segmented
   page-record boundary from `SO ESC &p3X!\x80!`. They should also
   broaden downloaded-glyph publication cross-products beyond the documented
   segmented-wide, normal, linear-segmented, and even-span wide selector
   families, especially alternate row counts, character modes, and non-success
   exits. The publication-command checkpoint now covers host-fetched reset, FF,
   page-size, orientation, paper-source, and copies streams through parser
   dispatch, `0xff1e`, `0x1ed84`/`0x1edc6`, `0x1ef6a`, and final row
   comparison; reset, FF, page-size, orientation, paper-source, and copies
   also have addressed allocation variants.
