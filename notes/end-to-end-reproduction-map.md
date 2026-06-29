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

CPU clock source is outside the current logical byte-stream-to-pixels
contract except where it changes firmware-visible event order. The
bounded timing surfaces are host fetch/polling (`0xa904..0xab8a`),
scan/status interrupt and wait-object dispatch (`0x0f84..0x1282`), and
active render scheduling (`0x1eb2a..0x1ed84`). The current fixtures prove
the state effects after those events are observed: pending bytes
`0x78399e/0x78399f`, shadow byte `0x7828f9`, wait-object state, active
source `0x780eae`, active work pointer `0x783a18`, and band words.
Exact oscillator identity remains board-level work for cycle-accurate
host I/O, engine handshake, timeout, and physical registration fidelity.
The named physical formatter/DC edge is connector `J205`: `BD`, `VDO`,
`VSREQ`, `VSYNC`, `PRNT`, command/status strobes, and ready signals.
Current ROM evidence does not yet map those signals to exact MMIO bits;
the board-facing boundary is tracked in
[dc-controller-engine.md](dc-controller-engine.md).

## Current End-To-End Coverage

- Host byte source priority:
  ROM evidence is `0xa904..0xabf0` in
  `generated/disasm/ic30_ic13_host_byte_fetch_00a904.lst`.
  Reproduction evidence is
  `generated/analysis/ic30_ic13_host_byte_fetch_flow.md` and fixtures
  for no-byte, service retry, LIFO, data-chain, ring, and direct modes.
  The observed data-chain frame layout is now composed with the byte-source
  checkpoint: `0x782d76` points at frame `+0x00` payload/chunk pointer,
  `+0x04` byte count or `-1` end marker, byte `+0x08 = 4`, byte `+0x09`
  as execute `2`, call `3`, or non-replay page-finalization `4`, and
  longword `+0x0a` as snapshot pointer or zero. Remaining host-input risk is
  physical MMIO naming/timing and any producer for other frame `+0x09`
  values, not the normal byte-source priority or observed macro/data-chain
  replay path.
- External service/status preemption:
  ROM evidence is `0xba48..0xc36e` in
  `generated/disasm/ic30_ic13_external_ready_service_loop_00ba48.lst` and
  `generated/disasm/ic30_ic13_external_service_reset_00c06e.lst`.
  Reproduction evidence is `External Ready And Service Status Loop` in
  `notes/semantic-state-model.md`, plus fixtures for `0xc0ae` publishing
  `$fffee005.7/.6` through `0x9bee(0x780e2e, 0x80/0x40)`, `0xc1c6`
  entering non-returning `68 SERVICE` at `0x85c0` from
  `0x780e36 & 0x00000008`, and `0xc1c6` replaying pending buffer
  `0x782312` through `0x8c7a` when no status bits are active. This cluster
  is not a page-imaging producer, but it can stop or defer normal parsing
  before page objects are generated. The teardown handoff through
  `0xc108 -> 0x19dd2 -> 0x36e4` is now bounded in
  `Page/Font Scheduler Handoff`: `0x19dd2` publishes scratch pointer
  `0x782894`, `0x19eb6` scans optional windows `0x200000..0x3ffffe` and
  `0x400000..0x5ffffe` when `$8000.14/15` permit it, `0x1a042` and
  `0x19f08` compare those scratch slots against canonical slots at
  `0x7828b6`, and the status branch can raise
  `0x9bee(0x780e2e, 0x00000200)` with byte `0x780e8d`. Remaining risk is the
  board-level external-register identity, one live execution of
  `0x571e -> 0x9bee -> 0xc1c6 -> 0x85c0`, and nested-helper composition below
  the now-pinned handoffs into `0x1887a`, `0x1a616`, `0x1b04c`, `0x1b4c0`,
  and `0x179aa`, not the documented consumer branch behavior. Candidate-slot
  deletion/compaction through `0x1bd2e` is now folded into the shared
  candidate-list model.
- Parser byte and command records:
  ROM evidence is `0xda9a`, `0xdaf0`, `0xdb74`, and `0x11774`.
  Reproduction evidence is `generated/analysis/ic30_ic13_parser_xrefs.md`
  plus tokenizer and delayed-payload fixtures. The composed state contract is
  `Parser Record And Delayed Payload State` in
  `notes/semantic-state-model.md`: command finals and payload bytes are
  separate events, six-byte records are saved through `0x121cc`, restored
  through `0x12218`, and then consumed by raster, transparent text,
  downloaded-font, generic payload, macro, and alternate/data handlers.
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
  CR, left-margin parser, vertical-cursor parser, low-water, split,
  nonempty, and retry fixtures.
- Page-root storage:
  ROM evidence is `0x10084`, `0x10110`, `0x1381c`, and `0x1387c`.
  Reproduction evidence is `Shared Page-Record Storage And Allocator`,
  addressed storage fixtures, and chunk-rollover fixtures.
- Rule/rectangle producers:
  ROM evidence is `0x10898`, `0x10b80`, `0x13386`, and `0x133aa`.
  Reproduction evidence is `notes/rectangle-graphics.md` and
  parser-to-rule fixtures, including
  `host-fetched alternate rectangle selectors feed full page records` and
  `host-fetched rectangle selector matrix feeds full page records`.
- Raster producers:
  ROM evidence is `0x10808`, `0x1075a`, `0x105d0`, `0x13070`, and
  `0x13250`.
  Reproduction evidence is `generated/analysis/ic30_ic13_raster_graphics_flow.md`
  and host-fetched raster stream fixtures. The current raster command-family
  checkpoint covers lower-resolution modes `1..3`, consecutive uppercase
  `ESC *b#W` transfers, lowercase `ESC *b#w` same-family chaining, `ESC *rB`
  active-byte clear, active-resolution ignore, `0x105d0` cap/drain gates,
  page-record object bytes, bridge dispatch, and rendered rows. The current
  handoff ledger also pins the field ownership across `0x105d0`, `0x10084`,
  `0x13070`, `0x13250`, and `0x132b6`: `A4 = 0x783170`, restored record
  `A5 = 0x78299e - 6`, accepted/overflow words `+0x04/+0x06`, row word
  `+0x02`, current root `0x78297a`, bucket/key caches `0x782a7c/0x782a7e`,
  stream chunk state `0x782a70/0x782a76/0x782a80`, and copy-stop flag
  `0x782996`. The remaining raster gap is live-trace confirmation of those
  values in one dense parser-produced text/rule/raster page, not discovery of
  another raster object field.
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
  `addressed text/rule/raster field groups reach publication and render
  entry`,
  `host-fetched text rectangle multi-row raster FF publishes rendered page
  record`, and
  `addressed text/rule/multi-row raster publication preserves bucket
  chain`.
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
  `generated/analysis/ic30_ic13_raster_graphics_flow.md`, `notes/raster-graphics.md`,
  `Raster Transfer Gate And Encoded Rows` in `notes/semantic-state-model.md`,
  and host-fetched raster fixtures.
- Rectangle/rule streams are covered for size commands, fill selectors,
  clipping, no-room retry, bridge normalization, solid/pattern rendering,
  selector-7 text/rule page records, all non-solid selector IDs in text/rule
  page records, and the landscape pattern remaps. Evidence:
  `notes/rectangle-graphics.md` and parser trace fixtures for `ESC *c` rule
  streams.
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
  Fixture `segmented downloaded glyph composes with raster through 0x1ef6a`
  extends the composition evidence to the `ESC )s258W` selector-`0x2003`
  segmented glyph family: bucket `9` contains the segment-1 object plus a
  mode-0 raster object, dispatches through `0x1f88e` and `0x1f1f0`, and
  renders digest
  `0b5440d6733ab9a072e0c14d1a470e6bc944dc98ddbf789152cf65c945dd0f01`.
  Fixture `split-plane segmented downloaded glyph composes with raster through
  0x1ef6a` covers the split-plane `ESC )s387W` sibling with glyph `0x28`,
  buckets `9` and `1`, the same bucket-9 raster object, dispatch targets
  `0x1f88e` and `0x1f1f0`, and digest
  `a380045041433910619b809637eda41e81842a3516acb83b488d07f1d3c68872`.
  Fixture `segmented downloaded glyph raster FF publications render page
  records` then publishes both segmented+raster records through `0xff1e`,
  preserves bucket `9` raster plus segment-1 objects and bucket `1`
  segment-0 objects, and renders the published records with the same two
  digests.
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
  `0x783e8e`, and `0x782d76` frame fields `+0x00`, `+0x04`, `+0x08`,
  `+0x09`, and `+0x0a`. Evidence:
  `generated/analysis/ic30_ic13_host_byte_fetch_flow.md` and
  `Host Byte Fetch And Data-Chain Input` in
  `notes/semantic-state-model.md`.
- Parser scratch: six-byte command records at `0x78299e..0x7829a7`,
  delayed handler snapshots, payload counters, and alternate/data mode state.
  Evidence: `Parser Record And Delayed Payload State` in
  `notes/semantic-state-model.md`, tokenizer fixtures, and
  `generated/analysis/ic30_ic13_parser_xrefs.md`. The parser-record checkpoint
  classifies canonical state (`0x782999`, `0x78299e`, `0x782c18`), tokenizer
  scratch (`0x782a26`, `0x782a2a..`, `0x782a3e`, `0x782a42..`,
  `0x783196..0x783199`), firmware bookkeeping (`0x78299a`, `0x782a1a`,
  `0x782a1c`, `0x782a20..0x782a25`, `0x782a56`), and derived font-designation
  records from `0x11efe` / `0x11f26`.
- Canonical print environment: cursor words `0x782c8a` and `0x782c8e`,
  HMI/VMI words, margins, page geometry fields under `0x782da2..0x782dc0`,
  line-termination mode, cursor stack, and font slot state. Evidence:
  `Text Cursor And Direct Controls` and page-geometry fixtures, including
  the `ESC *p#X/#Y` dot-position path through handlers `0xf48c` and
  `0xf692`. Those handlers convert parsed integer dot units to packed
  whole-dot cursor coordinates with `parameter << 16`, then share the
  `0xf4ca` / `0xf6e2` commit helpers before printable output is queued.
- Canonical page model: current page root `0x78297a`, page-root class byte
  `+4`, bucket array `+0x1c`, rule list `+0x24`, fixed-width list `+0x28`,
  context slots `+0x2c`, and stream allocator fields `0x782a70`,
  `0x782a72`, `0x782a76`. Evidence:
  `Shared Page-Record Storage And Allocator`.
- Derived/cache state: bucket/key bytes `0x782a7a..0x782a7e`, render-band
  fields `0x783a20`, `0x783a22`, `0x783a28`, pending span watermarks
  `0x783184..0x78318a`, raster mode/scale caches, delayed raster row
  coordinates, and mode-selected encoded raster object bytes. Evidence:
  `Text Span Flush And Fixed-Width Spans`,
  `generated/analysis/ic30_ic13_page_record_bridge.md`, and raster fixtures.
- Firmware bookkeeping: publication flag `0x782996`, page/root transient
  bytes `0x78297e`, `0x782c72`, `0x782c73`, retry flag bit in page-root
  `+0x14`, macro/data-chain frames, and heap/resource allocation metadata.
  Evidence: page-finalization, macro, allocator, and font-resource notes.

## Pixel-Perfect Blockers

These are the highest-value unresolved edges or residual risks because each
can change rendered pixels, byte-stream compatibility, or final confidence.

1. Font/context span metric producer ownership is documented, and the
   parser-produced legal value space is now represented by ROM formulas plus
   fixture-backed partitions rather than isolated per-value tracing. The
   consumers are known: unflagged `0xd4ac` reads context `+0x2b`, `+0x2c`,
   `+0x2d`; flagged `0xd8fc` reads `+0x16`, `+0x18`, `+0x1a`. The selected-context
   bridge and current metric evidence boundary are documented in
   `notes/font-context-metrics.md`, and the downloaded descriptor/payload producer side
   is documented in
   `notes/downloaded-fonts.md`. Host-fetched `0x1719c` type-0, type-1, and type-2
   payloads now prove copied descriptor bytes feeding both `0xd4ac` and `0xd8fc`
   visible span rows. Fixture `d4ac and d8fc span consumer branch family controls flush
   output`
   covers disabled, lower-bound, page-extent, and high-x consumer outcomes for both
   source forms. Fixture `host-fetched metric variant changes d4ac gate and d8fc rows`
   proves one parser-produced metric-value variant: copied `+0x2c/+0x2d` flips a tight
   `0xd4ac` page-extent gate, and copied `+0x1a` moves `0xd8fc` visible rows. Fixture
   `host-fetched clamped metric variant changes d4ac gate and d8fc rows` proves a second
   parser-produced variant: range/count `+0x14 = 5` clamps an oversized rounded metric
   input into `+0x2c/+0x2d = 0x0014`, leaves `+0x2b = 0`, flips another tight `0xd4ac`
   gate, and moves `0xd8fc` rows through copied `+0x18 = 0` and `+0x1a = 3`. Fixture
   `host-fetched lower-bound metric variant suppresses d4ac and d8fc spans` proves a
   third parser-produced variant: first code `+0x16 = 0x0018`, range/count `+0x14 =
   0x0600`, derived count `+0x18 = 0x05e7`, and rounded word `+0x2c = 0x1800` make both
   consumers exit `before-context-lower` at cursor y `21` while the compact glyph
   objects remain queued and render. Fixture `host-fetched upper-bound metric variant
   keeps d4ac span but suppresses d8fc` proves a fourth parser-produced variant:
   range/count `+0x14 = 0x0040` derives/cache `+0x18 = 0x003b`, leaves unflagged
   `+0x2c/+0x2d = 0/0x20`, keeps `0xd4ac` span output, and makes `0xd8fc` exit
   `beyond-page-extent` at cursor y `21`. Seven bounded validation no-install forms plus
   the short-budget `ESC )s8W` entry-5 failure now prove parser-to-validation failure,
   allocation skip, no candidate install, resumed default-font printable output, and
   matching rows. Fixture `descriptor metric fields match across inline and resource
   contexts` now proves inline/unflagged `d4ac`, resource/flagged `d8fc`, and the two
   invalid swapped forms. Fixture `legal descriptor metric value matrix drives d4ac and
   d8fc consumers` composes the legal small-rounded, clamped-rounded, midpoint-rounded,
   zero-rounded-offset, negative-offset, lower-bound, and upper-bound values; the zero
   case copies `+0x14/+0x18/+0x1a/+0x2c = 0x0018/0x0013/0x0000/0x0000`, preserves the
   `d4ac` span digest
   `67554ea70d7cfd9b11c0777e3cf65d51600a44301a4f93bd4d9b0c0fbc23c00e`, and makes `d8fc`
   publish high-y `21` / row digest
   `47361fc76bd6284f9d764c0377a3fda64edd3944b5cb2dff72acfd2224bc25e8`. The midpoint case
   copies `+0x14/+0x18/+0x1a/+0x2c = 0x0018/0x0013/0x0007/0x0018` and makes `d8fc`
   update high-y `14` while leaving compact-only digest
   `1a73b5e7454202d800c69f626bcf34e7d0d583b459e04c0bd4250010bf3ba28a`. The
   negative-offset case copies `+0x14/+0x18/+0x1a/+0x2c = 0x0018/0x0013/0xfffe/0x0008`;
   `d8fc` consumes the copied offset word as `65534`, computes high-y `-65513`, and
   renders digest `72bfa14c2a84532e2bdf6fb8fddf26ed6904c49dcf4fdcb322592471b5d5b281`.
   Fixture `legal descriptor metric boundary values drive d4ac and d8fc consumers` adds
   max positive and max negative copied offset words `0x007f` and `0xffff`, lower-bound
   equality, exact page-extent equality, rounded input `0x0013` copying `+0x2c =
   0x0014`, and high-byte rounded inputs `0x1500`, `0x1508`, and `0x15ff` all copying
   `+0x2c = 0x0060` before `d4ac` exits `beyond-page-extent`. Fixture `legal descriptor
   metric low-nibble rounding drives d4ac and d8fc consumers` proves rounded inputs
   `0x0001`, `0x0003`, `0x0004`, `0x0005`, and `0x000f` copy to `+0x2c =
   0x0000/0x0004/0x0004/0x0004/0x0010`, keep the standard `d4ac` span digest, and keep
   `d8fc` high-y `20` / digest
   `f830d30ea60a61f0b74a489c4b7df1bb25dc464b6765d170c19e7278a0267eab`. Fixture `legal
   descriptor metric byte-boundary rounding drives d4ac and d8fc consumers` proves
   rounded inputs `0x00fd`, `0x00fe`, `0x0101`, and `0x0102` copy to `+0x2c =
   0x00fc/0x0100/0x0100/0x0104`, with a range-cap sibling forcing `0x0102` back to
   `0x0100` when `+0x14 = 0x0040`. The copied `0x00fc` case leaves `d4ac` on
   compact-only digest
   `86e3bb70d51c66ac608345dc3bff6476447ebc500d7c271808a53d6638d59ad6`, while the
   `0x0100` boundary copy restores the standard `d4ac` span digest
   `67554ea70d7cfd9b11c0777e3cf65d51600a44301a4f93bd4d9b0c0fbc23c00e`; the same
   large-range cases keep `d8fc` at `beyond-page-extent`. Fixture `legal descriptor
   metric mixed values drive d4ac and d8fc consumers` now covers multi-field legal
   descriptors where the first code, range/count, rounded word, and signed offset all
   vary together. The middle-range `0x0008/0x0030/0x002a/0x02` case copies
   `+0x18/+0x1a/+0x2c = 0x0027/0x0002/0x002c`, suppresses `d4ac` as
   `beyond-page-extent`, and renders `d8fc` digest
   `00c97b69bc50326e442dd060c88b710b8f00217d40809bed276d8ba48581fdc7`. Its
   rounded-`0x00ff` sibling caps copied `+0x2c` to `0x00c0`; its offset byte `0x80`
   sibling sign-extends to `+0x1a = 0xff80` and computes `d8fc` high-y `-65387`; its
   late-first-code sibling derives `+0x18 = 0`, keeps `d4ac` visible, and makes `d8fc`
   exit `before-context-lower`. Fixture `legal descriptor metric tight range values
   drive d4ac and d8fc consumers` covers range-one zero/clamped rounded outputs and
   range-two max positive/negative offset words at derived height zero. The producer
   formula is documented from disassembly: `0x17430` derives `+0x18 = +0x14 - +0x16 -
   1`, `0x1757a` writes `+0x2c = min((value + 2) >> 2, word(+0x14)) << 2`, `0x1762a`
   writes signed offset word `+0x1a`, and `0x1719c` copies those staged fields into the
   allocated payload. The remaining metric work is no longer an unresolved middle edge
   for the copied-field formulas: `notes/font-context-metrics.md` classifies additional
   legal metric values as cross-products, and `notes/downloaded-fonts.md` says the
   remaining validation work is external HP/manual naming for consumed-but-not-staged
   fields. Future metric work should therefore be regression expansion or selected-font
   cross-products only when they expose a new state boundary. It is not the tested
   type-0/type-1/type-2 payloads, metric-variant, clamped-variant, lower-bound-variant,
   upper-bound-variant, legal-value-matrix, low-nibble rounding submatrix,
   byte-boundary rounding submatrix, extent-fence matrix, validation no-install, legal
   producer-form boundary, mixed-value matrix, tight-range matrix, or shared consumer
   branch family. Evidence: `notes/semantic-state-model.md` under `Text Span Flush And
   Fixed-Width Spans`.
2. VFC table definition and channel jumps now have a tracked command-family
   contract in `notes/vertical-forms-control.md`. The remaining VFC risk is
   broader final-device image comparison, not an unresolved middle edge in the
   documented `ESC &l#W` / `ESC &l#V` path.
3. Macro replay, overlay publication, repeated enabled-overlay publication,
   mixed-control, raster, multi-row raster, and span-flush overlay payloads, and overlay
   skip gates are anchored. The covered overlay path is selector `4` state through
   `0xff1e` re-entry, `0xe0a4`, `0xe4f4`, parser loop `0x11774`, and rendered
   page-record composition with selector-7 rectangle rules on two page boundaries. The
   mixed-control overlay fixture stores `ESC &k1G!\r!`, replays it through
   `0xedf8`/`0xd04a`/`0xf02c`/`0xd04a`, queues two compact text entries, and publishes
   them with a selector-7 rule. The raster overlay fixture stores `! ESC *t300R ESC *r0A
   ESC *b2W c3 3c`, replays it through the non-replay frame, queues compact text plus a
   mode-0 raster object, preserves the existing selector-7 rule, and renders digest
   `bc21050018fd3e992709c704fff732499aa9d06565de31d7ae0340869971c5b3`. The multi-row
   raster overlay fixture stores `! ESC *t300R ESC *r0A ESC *b2W f0 0f ESC *b2W 0f f0`,
   replays two delayed `0x105d0` transfers, queues compact text plus two mode-0 raster
   objects, advances raster `row_y` to `2`, and renders digest
   `58c2293bbc6b187db0e964571e5812ab2192d32d8e648a38d61e407a58538638`. The span-flush
   overlay fixture stores `ESC &a6L!`, replays it through `0xeb58`/`0xd04a`,
   materializes selector-`0x4000` span object `00 00 00 00 40 00 00 01 32 00 03 00 00 10
   ...`, preserves the existing selector-7 rule, and renders digest
   `6775414374ba3c31f7846a180d93cc9b68e230ea6981ae722b32eb39081f9bca`. The skip path is
   covered for disabled overlay mode, missing selected record, and page-root retry flag.
   Remaining macro risk is broader overlay payload variants beyond `!\r`, `ESC
   &k1G!\r!`, the covered raster payloads, and `ESC &a6L!`, plus physical output
   comparison. Evidence: `Macro Definition And Data-Chain Replay` in
   `notes/semantic-state-model.md`, fixture `macro overlay finalization replays before
   page publication`, fixture `macro overlay replays across repeated page publications`,
   and fixture `macro overlay skip gates preserve base page publication`, fixture `macro
   overlay mixed-control payload publishes with page rule`, and fixture `macro overlay
   raster payload publishes with page rule`, fixture `macro overlay multi-row raster
   payload publishes with page rule`, and fixture `macro overlay span-flush payload
   publishes with page rule`.
4. Active-record selection and render-band scheduling are documented as a
   ROM-internal reproduction boundary, rather than a page-object gap. Fixture
   `0x1eb2a/0x1ecd6 selects published record for render entry` proves
   `0x780eaa -> 0x780eae`, work-record alternation through `0x7820bc`, active render
   pointer `0x783a18`, and `0x1ed84`/`0x1ef6a` output for a published page/control
   record. Fixture `0x1958/0x1c04/0x1eea staged candidate reaches render scheduler`
   proves candidate staging, `0x1fd4` slot insertion, state-4 release, candidate
   promotion through `0x7ec6..0x7f90`, and the same rendered rows. Fixture
   `0x1eba4/0x1ef6a active render loop advances or yields bands` covers cleanup,
   throttle, capacity-wait, and render-call branches, while fixture `0x1eba4 scheduler
   band words render published downloaded glyph` proves scheduler-produced band words
   `0..9` against a published downloaded-glyph record. The remaining scheduler risk is
   not a ROM object/rendering middle edge: it is board-level timing for `$8000.4`
   selection at `0x0f84..0x0fa0` and `0x1020..0x102e`, MMIO effects around `$a601 =
   0xfd`, `$a801`, `$aa01`, `0xfffe0001`, and `0xfffe0003`, and the physical event
   timing that drives modeled wait-object/trap states through `0x10bc..0x11f8` and
   `0x123a..0x1282`. Evidence: `Published Record To Active Render Scheduler` in
   `notes/semantic-state-model.md` and `Active Render Scheduler` in
   `notes/page-raster-imaging.md`.
5. Downloaded font support now has tracked documentation for descriptor,
   resource-payload, current-record, bit-30-clear resource-object, bit-30-clear
   even-span and split-plane continuation resume, status-0 fixed-record release, bit-30
   offset-table release delegate, split-plane character-object, linear character-object,
   and downloaded-glyph render paths in `notes/downloaded-fonts.md`. The `0x16c14`
   existing-record allocation-failure teardown through `0x1887a` is fixture-backed for
   the bit-30-clear extended fixed-record case. The `0x16fae` validation table now has
   ROM-effect names for all 32 entries plus concrete success and failure fixtures, and
   host-fetched invalid-resource-type, first-code overflow, zero line/count, high
   line/count, reversed-range, high range/count, and invalid-class paths prove
   parser-to-validation no-install boundaries plus following-printable default output.
   Downloaded-character coverage now includes parser-produced normal, wide/control,
   even-span wide, segmented, split-plane segmented, and segmented-wide compact render
   shapes, and the combined downloaded-glyph stream now reaches FF publication with both
   segmented buckets preserved and scheduler-produced band words `0..9` rendered. The
   combined segmented-wide publication fixture now also pins the full-success return
   boundary: `combined font download FF publishes installed glyph page record` leaves
   `0x783140 = 0`, drains zero bytes through `0x12328`, and resumes at handler
   `0xd04a` for printable `%` before FF publication. The payload-control wide sibling
   now has its nonzero return drain pinned: fixture
   `host-fetched payload-control downloaded glyph FF publishes page record` carries
   normalized `1a 58`, selector `0x1003`, bucket `1`, `0xff1e`, `0x1ed84`, and
   `0x1ef6a` to the same `0x1f0d2` modeled row, while the live return leaves
   `0x783140 = 1`, drains the following `&` through `0x12328`, and leaves FF for
   handler `0xf0f0`. The rows-`0x82` segmented sibling now publishes through FF as well:
   fixture `host-fetched rows-0x82 segmented downloaded glyph FF publication renders
   page record` carries `ESC )s260W`, selector `0x2003`, buckets `1` and `9`, `0xff1e`,
   `0x1ed84`, and `0x1ef6a` to two `0x1f1f0` segment-1 rows. The rows-`0x20` short
   sibling now publishes through FF too: fixture `host-fetched rows-0x20 short
   downloaded glyph FF publication renders page record` carries `ESC )s64W`, selector
   `0x0003`, bucket `1`, `0xff1e`, `0x1ed84`, and `0x1ef6a` to `38` visible `0x1fe76`
   rows. The rows-`0x40` short sibling now publishes through FF as well: fixture
   `host-fetched rows-0x40 short downloaded glyph FF publication renders page record`
   carries `ESC )s128W`, selector `0x0003`, bucket `1`, `0xff1e`, `0x1ed84`, and
   `0x1ef6a` to `64` blank current-band `0x1fe76` rows. The accepted
   descriptor-record mode-byte boundary for this helper table is now documented by
   fixture `0x16b1a descriptor width helper emits only mode 1/2`: `0x16b36..0x16b6a`
   writes only mode `1`/`2` from span parity, and `0x16b26..0x16b34` rejects invalid
   widths without scratch writes. The full soft-font descriptor grammar, other release
   variants and full-success return-boundary siblings outside the even-span rule/raster
   path and outside the segmented, split-plane segmented, segmented-wide, and
   payload-control publication fixtures are still not proven against every PCL form.
   ROM-internal descriptor-validation error visibility is documented at the rejecting
   predicate boundary instead: fixture `ESC )s#W validation failures preserve following
   printable output` carries the seven `ESC )s80W` predicate failures plus the
   short-budget `ESC )s8W` entry-`5` failure through the following default-font page
   path. The remaining descriptor-validation gap is external HP/manual naming for
   consumed-but-not-staged fields. The mode-byte-`0` no-install boundary is
   documented separately: fixture `0x16498 replacement allocation failure partial and
   rejected downloaded character exits preserve state` proves the unchanged table/header
   at object boundary `0x16498`, and fixture `0x16498 no-install exits preserve
   following printable output` proves the following printable and FF publication stay on
   the unchanged default-font page path. The even-span
   downloaded-glyph plus rule/raster composition now has an exact modeled
   install-to-page handoff: host-fetched `ESC )s18W` produces the resource image
   consumed by the parser-driven page stream, including glyph `0x29`, table entry
   `0x00ee`, record delta `0x0780`, bitmap offset `0x078c`, and the 18 copied bitmap
   bytes. The same fixture proves the byte source is one 54-byte `0xa904` ring fetch:
   font bytes `0..24`, page bytes `24..54`, and no remaining ring bytes. ROM control
   flow now narrows the post-install return boundary: disassembly
   `generated/disasm/ic30_ic13_font_payload_setup_015b80.lst` shows
   `0x15dc6 -> 0x16498 -> 0x15dcc -> 0x12328`, where `0x15dcc` passes the remaining
   `0x783140` count to `0x12328`; the fixture pins this instance with copy status `1`,
   copy stream position `18`, remaining `0x783140 = 0`, zero-byte drain, and next parser
   handler `0x10e68`.
   The no-install visible-output fixture pins the same return edges with
   `0x783140 = 6`, six drained rejected-payload bytes, and next handler `0xd04a`;
   the status-`2` partial-install fixture pins the linear/split returns with
   `0x783140 = 0`, zero drain, and next handler `0xd04a`.
   The downloaded-glyph publication fixtures now also pin normal, row-`0x80`,
   linear-segmented, and split-plane segmented full-success publication returns with
   `0x783140 = 0`, zero drain, and next handler `0xd04a`.
   The combined segmented-wide publication fixture pins the same zero-drain return for
   selector `0x3003`: `0x783140 = 0`, zero drain, and next handler `0xd04a`.
   The payload-control wide publication fixture pins the nonzero return sibling:
   `0x783140 = 1`, drained byte `0x26`, and post-return handler `0xf0f0`.
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

1. Continue reset/default provenance from the composed `ESC E` consumer path.
   Semantic checkpoint `ESC E Reset And Default Environment` now covers
   `0xcc52 -> 0xcc70 -> 0xcda2`, page-root finalization through `0xff1e`,
   font-derived HMI refresh through `0xcbd4`, parser/data-chain reset through
   `0xe146`, valid-page publication fixtures, missing-root reset fixtures, and
   addressed compact-bucket publication through `0x1387c`/`0x1381c`. The
   reset-consumed defaults through `Default Environment Record Producers`: the
   selected `0x780eda` backing records feed `0x78219d`, `0x7821a2`, and
   `0x78219e` through loader `0x5e80`, while menu/update handlers `0x5060`,
   `0x50be`, and `0x52ba` update the same records and canonical defaults; the
   executable fixtures now cover those producer writes and dirty-flag slots.
   Fixture `0x5e80 -> 0xcda2 reset consumes default record outputs` now joins
   that producer side to the reset consumer, including the reset-gate behavior
   for `0x7821a2 -> 0x782da6` and the `0x78219e -> 0x783160` line-spacing
   conversion. Fixture `0xcfea/0xcf52/0x104d8 convert default line spacing to
   reset VMI` covers the direct, low-clamp, high-clamp, fallback-status, and
   landscape-table branches of that conversion.
   Record-maintenance helpers `0x56c2`, `0x571e`, and `0x5a62` now cover
   active-bank selection, three-word record-group copy, dirty-flag maintenance,
   and ROM-table fallback from `0xba3e`/`0xba44` into `0x780eda`, with fixture
   coverage for the `0x56c2` active-record and `67 SERVICE` boundaries.
   Panel/service entry points `0x2c84`, `0x3dae`, and `0x4922` now identify
   the cold-reset/menu-reset byte paths that reach `0x5a62`, `0x4162`, and
   `0x4fb0`; byte-source helper `0xa3ca` now identifies `$8000.w & 0xff` as
   the debounced service/panel byte source. Dirty-record commit/readback helpers
   `0x96c4` and `0x97e4` now identify the retained-storage serial interface
   through `$a400` writes and `$8c01.1` reads; `0x9a4a` now identifies the
   software-visible phase pairs for zero, one, and deassert. The remaining
   middle edge is not the software-reset consumer path, immediate default-byte
   writer, ROM-table fallback, panel/service dispatch, `0xa3ca`, generic NVRAM
   persistence, `$a400` phase encoding, startup retained-record bulk load
   through `0x5a16 -> 0x97e4`, or invalid active-record reporting through
   `0x56c2 -> 0x1284` (`67 SERVICE`); the fixture harness now covers the
   default-record producer boundary, the startup read-mask behavior, and the
   active-record/error scan. The remaining middle edge is the external
   device/protocol that drives `$8000.w`, the physical retained-storage device
   and board-level serial pin names behind `$a400`/`$8c01`, reconciling the
   manual NVRAM-failure fallback wording with the ROM paths found so far, and
   physical engine/self-test placement against known output.
2. Treat font metric-byte combinations as regression expansion unless a new
   state boundary appears. The selected-context bridge, metric consumers, downloaded
   descriptor/payload producer chain, and host-stream downloaded glyph output are now
   tracked. Host-fetched
   `0x1719c` type-0, type-1, and type-2 payloads reach both `d4ac` and `d8fc` span rows,
   and the shared disabled/lower/page/high-x consumer branch family is fixture-backed.
   The seven-case legal descriptor metric matrix plus boundary fixture covers tight
   `d4ac` page-extent gates, rounded-metric clamping into `+0x2c/+0x2d`, shifted `d8fc`
   visible rows, a zero rounded/offset case where both consumers publish spans, negative
   and max-positive copied offset words `0xfffe`/`0xffff`/`0x007f`, `d8fc` lower-bound
   and exact page-extent equality, rounded transform inputs `0x1500`/`0x1508`/`0x15ff`,
   the low-nibble rounded inputs `0x0001`/`0x0003`/`0x0004`/`0x0005`/`0x000f`, a
   byte-boundary rounded submatrix around `0x00fd..0x0102`, `0x17430` first-code-zero
   endpoint and first-code-`range - 1` endpoint, a page-extent fencepost matrix where
   derived heights `42`, `44`, and `45` combine with offset bytes `0`, `1`, and `2`,
   mixed-value matrix that combines first-code/range/rounded/offset changes, a
   tight-range matrix that combines range one/range two with zero/clamped rounded
   outputs and max signed offsets, midpoint case where `d8fc` updates state but leaves
   compact-only output, a lower-bound no-span output path for both consumers, and an
   upper-bound case where `d4ac` still renders a span while `d8fc` exits
   `beyond-page-extent`. Fixture `descriptor metric fields match across inline and
   resource contexts` now pins the legal producer-form boundary: inline/unflagged
   reaches `d4ac`, resource/flagged reaches `d8fc`, and the swapped forms fail at
   concrete map/render boundaries. The producer formulas are no longer the missing
   middle: `0x17430`, `0x1757a`, `0x1762a`, and `0x1719c` now define the canonical,
   derived/cache, and copied metric fields. Additional legal metric values outside the
   pinned legal matrix, boundary, extent-fence, range-endpoint, mixed-value,
   tight-range, low-nibble, and byte-boundary fixtures are cross-products of those
   formulas and consumer gates, not a new semantic middle edge by themselves. Remaining
   metric-related work is external/manual naming for consumed-but-not-staged validation
   fields or broader selected-font combinations that expose different state boundaries.
3. Broaden the page-image fixture suite beyond the current complete
   text/rule/raster/publication stream, downloaded-glyph FF publication stream,
   parser-driven downloaded-glyph/rule/raster page stream, primary plus secondary
   built-in font-selection visible-output streams, inline primary and secondary
   parser-to-printable streams, the primary and secondary symbol fallbacks, plus
   primary/secondary current-font-RAM handoff and composed selection-to-RAM handoff
   visible-output streams. Downloaded-font live-continuity work is now narrowed:
   fixtures `combined host-fetched font download stream prints installed glyph` and
   `combined font download FF publishes installed glyph page record` already drive one
   2,215-byte `0xa904` stream through font-control state, `ESC )s2193W` install,
   printable `%`, FF, bucket entries `1` and `9`, and `0x1ed84`/`0x1ef6a`. The remaining
   ROM-side continuity edge is the even-span `ESC )s18W` rule/raster composition case,
   where `parser-driven downloaded glyph rule raster stream composes through 0x1ef6a`
   already proves one 54-byte `0xa904` ring fetch and the shared `0x15dc6 -> 0x16498 ->
   0x15dcc -> 0x12328` post-install drain. It now also proves the modeled memory-image
   handoff: the page phase consumes `font_command_final_header` from the same
   font-command helper, asserts it matches the install event header, and reports pointer
   bytes `00 00 07 80`, record bytes, and bitmap bytes. What remains is the stronger
   live-68000 capture of the same memory state from stream byte `24` into the following
   `0x10e68` page handler. The primary built-in case proves `ESC (s0p10h12v0s0b3T!!`
   through parsed selection handlers, selected context `0xc008004c`, printable `0xd04a`
   entries, object prefix `00 00 00 00 00 00 00 02 00 6a 00 00 68 02`, render-record
   context slot `0xc008004c`, and final Courier glyph rows. The secondary case proves
   `ESC )s0p16h8v0s0b0T SO !!` through selected context `0xc00ae122`, SO handler
   `0xc6b8`, object prefix `00 00 00 00 00 01 00 02 00 c9 00 00 cb 01`, render-record
   context slots `(0xc008004c, 0xc00ae122)`, and final secondary Line Printer rows. The
   primary fallback case proves `ESC (1234U ESC (s0p10h12v0s0b3T!!`: requested word
   `0x9a55` misses in `0x156de`, fallback word `0x0115` survives, and the final selected
   context, map, object prefix, context slot, and rows match the primary case. The
   secondary fallback case proves `ESC )1234U ESC )s0p16h8v0s0b0T SO !!`: requested word
   `0x9a55` misses in `0x156de`, fallback word `0x000e` survives, and the final selected
   context, map, object prefix, context slots, and rows match the secondary SO case. The
   primary RAM handoff case proves seeded `0x782ee6 = 0xc008004c` through SI `0xc68a`,
   `0xc428(0)`, `0xc4fc`, page-root slot `0`, and following `!!` visible rows on an
   existing root. The secondary RAM handoff case proves seeded `0x782ef6 = 0xc00ae122`
   through SO `0xc6b8`, `0xc428(1)`, `0xc4fc`, page-root slot `1`, and following `!!`
   visible rows on an existing root. The composed handoff cases prove `ESC
   (s0p10h12v0s0b3T SI !!` and `ESC )s0p16h8v0s0b0T SO !!` from host-fetched selection
   bytes to selected current-font RAM, page-root slot install, and rows matching the
   pinned visible fixtures. The inline cases prove `ESC (s0p10h12v0s0b3T!!` and `ESC
   )s0p16h8v0s0b0T SO !!` in one mixed-stream state from selection handlers to printable
   source capture, HMI, object prefix, bridge context slots, and rows. The non-Roman
   symbol cluster is now part of the visible-output suite too: fixture `live parser
   symbol-set streams select non-Roman built-ins` proves primary `ESC (0N`, `ESC (10U`,
   and `ESC (11U` through parser handlers `0x11eb6`, `0x1201e`, and `0x120be`,
   selected-font refresh, record choices `0x000cb8`, `0x000418`, and `0x000868`, and map
   rebuild path `selected-symbol-not-roman8`. Fixture `non-Roman symbol streams select
   visible built-ins` then carries primary `0N`/`10U`/`11U` streams through matching
   `ESC (s0p10h12v0s0b3T!!` tails and secondary `ESC )0N`/`10U`/`11U` streams through
   matching `ESC )s0p16h8v0s0b0T SO !!` tails, crossing SO handler `0xc6b8` for
   secondary, preserving compact object prefixes, bridge context slots, and rendered-row
   digests. Fixture `real final-@ default-table streams select visible built-ins` closes
   the parser-exposed `@0`/`@1`/`@2`/`@3` edge: after the real-backed default-table
   caller stream leaves active words `[0x000e, 0x0005]`; the primary tail renders from
   context `0xc0080cb8` with the primary non-Roman row digest, while the secondary tail
   renders from context `0xc00ad4aa` after SO with the secondary row digest. Remaining
   suite cases should add other fallback/error font-selection visible-output variants
   beyond the two symbol misses, the `0N`/`10U`/`11U` primary/secondary streams, the
   real final-`@` primary/secondary streams, and the covered final-`X` streams. Fixture
   `font-ID built-in selection feeds visible page-record rows` covers that final-`X`
   stream: host-fetched `ESC (7X!!` reaches `0x120be`, selects context `0xc0089fb0`
   through `0x17708`, and renders row digest
   `73cbb28bfab786807b9a3186eb3946efae550cde2e5448f0549f88ebf8c8a631`. Fixture `font-ID
   inline/downloaded selection feeds visible page-record rows` covers the parallel
   bit-30-clear final-`X` stream: host-fetched `ESC )4660X SO !` reaches `0x120be`,
   selects context `0x00000100` through `0x17708`, crosses SO `0xc6b8`, and renders row
   digest `e0c6cbbf133aaaf522868ef7f28856f06b0d54b4dd9368a090fe7c85e7b1d563`. Fixture
   `0x17708 font-ID non-selected exits preserve prior selection` covers the direct
   final-`X` helper exits for scan miss, candidate-slot miss, class mismatch, and
   context-full through the exact `0x17708` terminal status, with no `0x14c64` map
   dispatch. Fixture `font-ID non-selected exits keep prior visible rows` appends the
   same host-fetched `ESC (7X!!` printable tail to those preserved-state outcomes:
   following `!!` consumes prior context `0xc008004c`, queues object prefix `00 00 00 00
   00 00 00 02 00 6a 00 00 68 02`, and renders row digest
   `8b36cfd64d818c0982b172982156f8be9687388c9679cd83538c9d1098d9bb2c`. Fixture `0x13eb8
   transient and cache-hit exits avoid dispatch` covers the selected-font refresh exits
   that stop before `0x144d2`/`0x14c64`: transient `0x78298f` stores selected context
   `0xc008004c`, while cache-hit returns after `0x148f8`. Fixture `0x13eb8 no-dispatch
   exits keep prior visible rows` carries both exits into visible output: the transient
   path leaves following `!!` on prior context `0xc0089fb0`, object `00 00 00 00 00 00
   00 02 00 89 00 00 87 02`, and digest
   `73cbb28bfab786807b9a3186eb3946efae550cde2e5448f0549f88ebf8c8a631`; the cache-hit
   secondary path crosses SO and leaves following `!!` on prior context `0xc40ad87a`,
   object `00 00 00 00 00 01 00 02 20 c9 00 20 cb 01`, and digest
   `b8ee0f8dd3e6ed70afa219bc00605d75249ae047a67fb67189693057d7936e6c`. The common
   refresh gate `0xc580` is now a composed branch cluster rather than a hidden
   font-selection middle edge: dirty-1 primary/secondary first-clear installs,
   full-live matching-context reuse, full-live/no-match `0xc4fc = 0x11` skip,
   dirty-1 selector-mismatch refresh-only, dirty-2 primary/secondary
   selector-match installs, and dirty-2 selector-mismatch remembered-word-only
   paths are documented in `notes/semantic-state-model.md` with fixture names
   and field groups. Remaining font-selection work is broader variants that expose new
   state boundaries; the named
   high-value unresolved edge is now the transparent secondary segment-57 bitmap source
   interpretation beyond the covered transparent data paths. Current transparent
   coverage includes the default-filtered C0/high-control fixed-space path, nonzero C0
   plus high-control `0x80` printable path, primary interior samples `0x81`, `0x88`,
   `0x90`, and `0x97`, primary tall bucket-crossing `0x98`, primary top-of-range `0x9f`,
   the secondary segmented page-record boundary from `SO ESC &p3X!\x80!`, and the
   secondary renderable prefix through bucket `448`. The first unresolved secondary
   bucket is `456`, glyph `0x5f`, segment `0x39`, file source `0x03fe22`, firmware
   source `0x0bfe22`, and required byte range `0x0bfe22..0x0c0321`; only `478` bytes are
   inside the verified `IC32,IC15` resource-pair image. Disassembly of `0x1f354` and
   `0x1f1f0` makes the unresolved part a physical/resource-window mapping question after
   `0x0c0000`, not a transparent parser or row-skip question. The current-band
   segment-57 rows are now pinned across mirror, code-pair, and zero-fill continuation
   hypotheses with digest
   `f0c1127f9e6b203f9829ab43f159b89c3f7dda687a47d4c09971077eac55c96e`; the fallback rows
   diverge. The same fixture hashes the verified `0x0bfe22..0x0bffff` suffix as
   `e0a0fd34ce7a39f79ecd27c0ee288631554a0ff78359b72e27ea6087651bcf1f` and the three
   continuation candidates as
   `e435e3b9d033e491b57282a88b0f321aa5fecae8128fa060844cc01379349563`,
   `90934acf59d9e8519c9149dc5df228f8fec2bff8451427be265489be967cdd16`, and
   `359f38eef400e2fa3924a3258652e74ee19cd46cb92e47bce91f1194fce25e9e`, so the remaining
   requirement is board/emulator memory-map evidence for `0x0c0000..0x0c0321`. That
   range is outside the verified `IC32,IC15` resource-pair image described by
   `data/rom_manifest.json`. Disassembly of `0x1a2e4` / `0x1a616` shows the built-in
   resource scanner covers `0x080000..0x0ffffe` in `0x40000` steps, while optional
   cartridge/resource scans are separate `$8000.14/15`-gated windows at
   `0x200000..0x5ffffe`; the segment-57 read is therefore a built-in decode question
   after the verified pair, not a cartridge-window read. Fixture `0x41a HEAD scanner
   would duplicate records under simple resource mirror` now constrains one candidate: a
   full resource-pair mirror at `0x0c0000` would make scanner `0x41a` see a second
   `HEAD` chain and walk `48` typed records, so mirror cannot be treated as only a local
   fallback-row source unless hardware/gating hides it from scanner reads. Fixture
   `0x41a HEAD scanner rejects non-HEAD 0x40000 continuations` constrains the code-pair
   and zero-fill candidates: their second-probe markers are `0x00800000` and
   `0x00000000`, so neither duplicates `HEAD` records for startup scanning. The hardware
   evidence in `notes/formatter-interface-pca.md` leaves address-controller/jumper ROM
   decode as the unresolved physical state. The `ESC Y ... ESC Z` display-functions loop
   is now documented in `notes/pcl-parser-core.md` and `notes/semantic-state-model.md`;
   fixture `ESC Y display-functions stream reaches page-record output` covers the
   default-filter normal `0x12536..0x1261e` page-output path, fixture `ESC Y
   display-functions filter-on routes controls as printable` covers the complementary
   nonzero context/filter route through `0xd04a`, and fixture `0x12120 ESC Y alternate
   append stores normalized display bytes` covers the alternate/data append-only
   `0x12120..0x1219c` path around `0xe002`. Remaining display-functions risk is broader
   physical/page comparison, not the command-family loop boundary or the documented
   filter predicates. They should also broaden downloaded-glyph publication
   cross-products beyond the documented segmented-wide, normal, nonboundary-short,
   rows-`0x20` short, rows-`0x40` short, linear-segmented, rows-`0x82` segmented,
   split-plane segmented, row-threshold `0x80` short, rows-`0x0101..0x0103`
   low-byte-truncated short publication, even-span wide, and payload-control wide
   selector families, especially row counts outside the covered short rows `0x01`,
   `0x02`, `0x03`, `0x04`, `0x05`, `0x06`, `0x07`, `0x08`, `0x09`, `0x0a`, `0x0b`,
   `0x0c`, `0x0d`, `0x0e`, `0x0f`, `0x10`, `0x11`, `0x12`, `0x13`, `0x14`, `0x15`,
   `0x16`, `0x17`, `0x18`, `0x19`, `0x1a`, `0x1b`, `0x1c`, `0x1d`, `0x1e`, `0x1f`,
   `0x20`, `0x3e`, `0x3f`, `0x40`, `0x41`, `0x42`, `0x7f`, and `0x80` and segmented rows
   `0x81`, `0x82`, `0x83`, `0x84`, `0x85`, `0x86`, `0xbf`, `0xc0`, `0xc1`, `0xfd`,
   `0xfe`, and `0xff`, descriptor grammar forms outside the covered helper-table path,
   full pixel-row behavior past the wrapped-width invalid helper entries, broader
   physical comparison for segmented-wide row words above `0x00ff`, and full-success
   return-boundary siblings beyond the covered normal even-span, no-install, status-`2`,
   row-count-matrix short/segmented, linear-segmented publication, split-plane segmented
   publication, segmented-wide publication, wide-remainder-matrix, and
   segmented-wide-matrix zero-drain cases plus the payload-control wide nonzero-drain
   `0x15dc6 -> 0x16498 -> 0x15dcc -> 0x12328` case. The accepted mode-byte boundary
   itself is covered by fixture `0x16b1a descriptor width helper emits only mode 1/2`,
   which pins `0x16b36..0x16b6a` accepted writes and `0x16b26..0x16b34` invalid
   no-writes. Fixture `downloaded glyph width-byte boundary truncates page-record span`
   pins the current printable source-byte wrap for spans `0x00ff`, `0x0100`, `0x0101`,
   and `0x020d`: canonical width words survive in the installed object, but `0x12f2e`
   sees width bytes `0xff`, `0x00`, `0x01`, and `0x0d`, so only `0x00ff` remains
   selector `0x1003`. The same fixture now carries all four page objects through
   `0xff1e` publication with bucket `0`, root clear, empty rule/fixed lists, and the
   queued object preserved as published bucket root; the wrapped spans then dispatch
   through `0x1effe` and read helper entries `0x1f48e`, `0x1f492`, and `0x1f8c2`, which
   target non-helper longwords `0x20700000`, `0x4e90202c`, and `0x4e904cdf`. Fixture
   `downloaded segmented-wide row-byte boundary truncates page-record segments` pins the
   row-byte sibling for span `0x11`: canonical row words `0x0081`, `0x00ff`, `0x0100`,
   `0x0101`, and `0x0181` survive in the installed object, but `0x12f2e` sees row bytes
   `0x81`, `0xff`, `0x00`, `0x01`, and `0x81`; rows `0x0100` and `0x0101` become
   selector `0x1003`, publish bucket key `[0]`, and split through `0x1f0d2` as `80/176`
   and `80/177`, while row `0x0181` queues only segments `1` and `0`, publishes bucket
   keys `[0, 8]` with selected bucket `8`, and splits through `0x1f264` as `32/96` and
   `80/48`. Fixture `downloaded glyph width-span matrix publishes and renders all main
   helpers` now covers parser-produced spans `1..16`: host-fetched `ESC )s#W`
   descriptors install width words `0x0008..0x0080`, preserve odd-span split-plane
   copies, publish bucket `0` through FF, dispatch object byte `0x00` through
   `0x1ed84`/`0x1ef6a`, and render rows matching installed bitmaps through helpers
   `0x1fa5c..0x26910`. The `downloaded glyph wide-remainder matrix publishes and renders
   compact chunks` fixture now covers matched parser-produced spans `17..32`:
   host-fetched `ESC )s#W` descriptors install width words `0x0088..0x0100`, publish
   bucket `0` as selector `0x1003`, dispatch object byte `0x10` through
   `0x1ed84`/`0x1ef6a` and compact target `0x1effe` / `0x1f0d2`, render full chunks
   through `0x2f27c`, render remainders `1..15` through `0x1f1ac[remainder]`, and cover
   span `32` as the no-remainder two-full-chunk sibling. The same fixture now probes
   compact-wide spans `33`, `48`, `49`, `64`, and `255` through the same upstream
   metadata and return boundary, including matched installed bitmap rows. The
   `downloaded glyph segmented-wide matrix publishes and renders compact chunks` fixture
   now covers matched parser-produced spans `17..32` with rows `0x81`: host-fetched `ESC
   )s#W` descriptors install width words `0x0088..0x0100`, publish buckets `0` and `8`
   as selector `0x3003`, dispatch segment `1` object byte `0x30` through
   `0x1ed84`/`0x1ef6a` and compact target `0x1effe` / `0x1f264`, render full chunks
   through `0x2f27c`, render remainders `1..15` through `0x1f1ac[remainder]`, and cover
   span `32` as the segmented no-remainder sibling. The same fixture probes
   segmented-wide spans `33`, `48`, `49`, and `64` through the same upstream metadata
   and return boundary, including matched segment-1 rows. The nonboundary-short fixture
   now publishes rows `0x10` on selector `0x0003` through FF, `0xff1e`, and
   `0x1ed84`/`0x1ef6a` with digest
   `28220dd2ecafaf07afc095fa0cc3cb6ed070984b3e3da6762b49ebda582d492b`. The rows-`0x20`
   short fixture now carries `ESC )s64W` plus printable `1` and FF through `0xff1e`,
   preserves bucket `1`, and renders bucket word `1` through `0x1ed84`/`0x1ef6a` to `38`
   visible `0x1fe76` rows. The rows-`0x40` short fixture now carries `ESC )s128W` plus
   printable `2` and FF through `0xff1e`, preserves bucket `1`, and renders bucket word
   `1` through `0x1ed84`/`0x1ef6a` to `64` blank current-band `0x1fe76` rows. The
   row-threshold fixture closes the `0x80`/`0x81` selector boundary by keeping rows
   `0x80` on selector `0x0003`, comparing it with the rows-`0x81` selector `0x2003`
   fixture, and now publishing the row-`0x80` bucket-1 record through FF, `0xff1e`, and
   `0x1ed84`/`0x1ef6a`. The split-plane segmented fixture now carries `ESC )s387W` plus
   printable `(` and FF through `0xff1e`, preserves buckets `1` and `9`, and renders
   bucket word `9` through `0x1ed84`/`0x1ef6a`. The rows-`0x82` segmented fixture now
   carries `ESC )s260W` plus printable `0` and FF through `0xff1e`, preserves buckets
   `1` and `9`, and renders bucket word `9` through `0x1ed84`/`0x1ef6a` to two `0x1f1f0`
   segment-1 rows. The downloaded-glyph row-count matrix now adds short rows `0x01`,
   `0x02`, `0x03`, `0x04`, `0x05`, `0x06`, `0x07`, `0x08`, `0x09`, `0x0a`, `0x0b`,
   `0x0c`, `0x0d`, `0x0e`, `0x0f`, `0x10`, `0x11`, `0x12`, `0x13`, `0x14`, `0x15`,
   `0x16`, `0x17`, `0x18`, `0x19`, `0x1a`, `0x1b`, `0x1c`, `0x1d`, `0x1e`, `0x1f`,
   `0x3e`, `0x3f`, `0x41`, `0x42`, and `0x7f` on selector `0x0003`/bucket `1`, plus
   segmented rows `0x83`, `0x84`, `0x85`, `0x86`, `0xbf`, `0xc0`, `0xc1`, `0xfd`,
   `0xfe`, and `0xff` on selector `0x2003`/buckets `1` and `9`, all through
   printable+FF, `0xff1e`, and `0x1ed84`/`0x1ef6a`; published row counts are `7`, `8`,
   `9`, `10`, `11`, `12`, `13`, `14`, `15`, `16`, `17`, `18`, `19`, `20`, `21`, `22`,
   `23`, `24`, `25`, `26`, `27`, `28`, `29`, `30`, `31`, `32`, `33`, `34`, `35`, `36`,
   `37`, `64`, `64`, `64`, `64`, `64`, `9`, `10`, `11`, `12`, `16`, `16`, `16`, `16`,
   `16`, and `16`. All forty-six row-count matrix cases now also pin `0x15dc6 -> 0x16498
   -> 0x15dcc -> 0x12328` with copy status `1`, `0x783140 = 0`, zero drained bytes, and
   next handler `0xd04a`. The `0x16498` replacement/allocation-failure/partial/reject
   fixture now has a high-row truncation matrix for rows `0x0101`, `0x0102`, and
   `0x0103`: `ESC )s#W` installs canonical records ending in row words `0x0101`,
   `0x0102`, and `0x0103`, but the printable page source exposes low row bytes `0x01`,
   `0x02`, and `0x03`, so `0x12f2e` queues selector `0x0003` and publishes only bucket
   `1`; `0x1f414` then splits the full installed rows into `58` current rows plus
   fallback rows `199`, `200`, and `201`, exceeding the `0x1fe76` table's valid maximum
   index `128`. The `0x16498` replacement/allocation-failure/partial/reject fixture now
   also covers old-pointer release through `0x17a24`, object allocation failure through
   `0x170c`/`0x9b5e`/`0x1887a`, status-`2` linear and split-plane continuation pointer
   writes, descriptor mode-byte-`0` status-`0` reject, and high-character/header-type
   status-`0` reject. The `0x16498` no-install visible-output fixture now proves those
   failed installs leave the following printable byte on the default-font compact object
   and rows, then publishes that default-font bucket through trailing FF, `0xff1e`, and
   `0x1ed84`/`0x1ef6a`. The status-`2` partial-install fixture now proves linear and
   split-plane partial glyphs remain printable through their stored table pointers and
   zero-filled missing bytes, then publishes both bucket-1 compact objects through
   trailing FF, `0xff1e`, and `0x1ed84`/`0x1ef6a` with the same rows. Remaining
   downloaded-character publication risk is broader publication combinations beyond
   these payload-control, width-span-matrix, wide-remainder-matrix,
   segmented-wide-matrix, row-count-matrix, rows-`0x20` short, rows-`0x40` short,
   rows-`0x82` segmented, segmented-glyph plus raster, split-plane segmented-glyph plus
   raster, segmented-glyph/raster FF publication, no-install, and status-`2` compact
   bucket variants, plus full-success return-boundary siblings outside the now-pinned
   row-count-matrix, wide-remainder-matrix, segmented-wide-matrix, normal, row-`0x80`,
   linear-segmented, split-plane segmented, segmented-wide, and payload-control cases.
   It is not the documented mode-byte-`0` visible recovery boundary. The
   publication-command checkpoint now covers host-fetched reset, FF, page-size,
   orientation, paper-source, and copies streams through parser dispatch, `0xff1e`,
   `0x1ed84`/`0x1edc6`, `0x1ef6a`, and final row comparison; reset, FF, page-size,
   orientation, paper-source, and copies also have addressed allocation variants.
