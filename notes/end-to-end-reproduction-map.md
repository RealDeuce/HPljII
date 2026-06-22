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
   One host-fetched `0x1719c` type-0 payload now proves copied descriptor
   bytes feeding both `0xd4ac` and `0xd8fc` visible span rows. The open edge
   is broader descriptor metric-byte and rejection/error combinations, not the
   tested type-0 middle edge. Evidence: `notes/semantic-state-model.md` under
   `Text Span Flush And Fixed-Width Spans`.
2. VFC table definition and channel jumps now have a tracked command-family
   contract in `notes/vertical-forms-control.md`. The remaining VFC risk is
   broader final-device image comparison, not an unresolved middle edge in the
   documented `ESC &l#W` / `ESC &l#V` path.
3. Macro replay is anchored, but macro overlay/page composition remains short
   of a pixel-complete overlay model. Evidence: `Macro Definition And
   Data-Chain Replay` and macro fixtures.
4. Downloaded font support now has tracked documentation for descriptor,
   resource-payload, current-record, character-object, and downloaded-glyph
   render paths in `notes/downloaded-fonts.md`. The full soft-font descriptor
   grammar and all validation/error behaviors are still not proven against
   every PCL form.
5. Hardware-facing host modes are behaviorally modeled above `0xa904`, but
   MMIO identity and electrical timing for Centronics/serial/RS-422 are not
   board-confirmed. This does not block a byte-stream renderer, but it blocks
   claims about hardware-level emulation. Evidence:
   `generated/analysis/ic30_ic13_host_byte_fetch_flow.md`.
6. Final device-output validation is not yet a real printer comparison. The
   harness proves ROM-derived rows internally, but pixel-perfect confidence
   ultimately needs rendered page images compared against known LaserJet II
   output for representative byte streams.

## Next Disassembly Targets

The next work should follow dataflow, not isolated handlers:

1. Prove the remaining font metric-byte combinations with parser-produced
   pages. The selected-context bridge, metric consumers, downloaded
   descriptor/payload producer chain, and host-stream downloaded glyph output
   are now tracked. One host-fetched `0x1719c` type-0 payload reaches both
   `d4ac` and `d8fc` span rows; the missing middle is broader descriptor
   metric combinations and rejection/error behavior.
2. Build a small page-image fixture suite from complete byte streams that mix
   text, rules, raster, geometry, font selection, and publication, then compare
   the final bitmap rows as the primary reproduction contract.
