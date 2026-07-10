# Unresolved Boundaries

This note is the checked-in index for exact boundaries that remain after the
current ROM-local dataflow documentation. It is not a backlog of every untested
variant. A boundary belongs here only when the documented trace reaches a
specific address, field, helper, or external memory range and cannot make a
stronger claim from the ROM evidence currently available.

Use the classification column before continuing work:

- ROM-local invalid target/source: the ROM reaches an address or table/source
  calculation that is defined by instructions, but the calculated target or
  source is outside the documented valid helper/data range.
- Missing external resource data: the ROM asks for bytes outside the verified
  local resource image.
- Hardware/MMIO boundary: the ROM-visible polling, status, or handshake
  behavior is documented, but the physical device, connector, or timing
  identity is not.
- Optional external data: the ROM control flow is documented, but optional
  cartridge/resource-window contents are not available.
- Manual/physical correlation: the ROM behavior is documented, but user-facing
  names or service-manual labels are not assigned.

## Pixel-Affecting Boundaries

For ROM-local invalid render targets, the reproduction rule is to stop the pixel
contract at the exact computed jump or source-read boundary named below. The documented
upstream state still matters: installed glyph records, page objects, publication
buckets, render bucket words, row splits, and helper inputs remain ROM-derived evidence.
What is not documented is a final row image after the ROM has selected an unchecked
helper target or source address outside the valid table/source region. A byte-stream
reproducer should therefore model the upstream state and report the invalid render
boundary instead of inventing pixels beyond it. This rule is grounded in the
downloaded-glyph checkpoints in
[downloaded-fonts.md](downloaded-fonts.md#downloaded-glyph-row-count-publication-checkpoint)
and the render-helper boundary index in
[end-to-end-reproduction-map.md](end-to-end-reproduction-map.md#render-helper-boundary-index).

State classification for these pixel-affecting stops:

- Canonical upstream state is still ROM-defined: transparent payload command
  records, selected font contexts/maps, installed downloaded-glyph records,
  bitmap payload bytes copied before the stop, page-root bucket objects,
  published bucket arrays, render-record bucket roots, and compact selector
  words such as `0x0003`, `0x1003`, and `0x3003`.
- Derived/cache state is the compact helper input that exposes the stop:
  segment number, source row/span/width products, fallback row count, row-copy
  table index, source offset, and restored payload budget.
- Parser scratch is the delayed `ESC &p#X` or `ESC )s#W` record, saved
  delayed-payload fields `0x782a1a/0x782a1c/0x782a20..0x782a25`, and
  remaining budget `0x783140` when a payload-count cap stops before install.
- Firmware bookkeeping is allocation/release state around `0x16c14` /
  `0x16498`, publication flag `0x782996`, active render progress, and
  no-install or drain return state where the stream stops before page output.
- Hardware/external state appears only for the secondary segment-57 source:
  the required bytes are beyond the verified IC32/IC15 resource suffix and
  depend on physical decode or external resource data for
  `0x0c0000..0x0c0321`.
- Unknown state is deliberately bounded to the named invalid target, invalid
  source read, missing resource range, or exact parser-count stop. Parser
  dispatch, page-object publication, bridge roots, and render-helper entry are
  not generic unknowns for these entries.

### Secondary Segment-57 Resource Source

- Classification: missing external resource data.
- Exact boundary:
  firmware resource range `0x0c0000..0x0c0321`, reached after verified
  IC32/IC15 resource-pair suffix `0x0bfe22..0x0bffff`.
- Covered path:
  `ESC &p#X` transparent data enters `0x11f5a -> 0x121cc -> 0x12218 ->
  0x12452`, routes printable/high-control bytes through `0xd04a` / `0xd0f0`,
  queues compact text buckets, publishes through `0xff1e`, bridges through
  `0x1ed84 -> 0x1edc6`, and resolves compact glyph rows through
  `0x1ef6a -> 0x1effe -> 0x1f354`.
- Exact stopped state:
  secondary high-control glyph `0x5f`, segment `0x39`, and firmware source
  address `0x0bfe22` are documented through the verified suffix. Bucket `448`
  is covered. Bucket `456` needs bytes beyond `0x0bffff`, so row bytes depend
  on the physical decode for `0x0c0000..0x0c0321`.
- What is not unresolved:
  parser dispatch, transparent count handling, `0x1a 0x58` normalization,
  selected-context filtering, page-record allocation, bridge fields, compact
  dispatch, segment skip arithmetic, and zero-offset glyph-entry
  interpretation.
- Local probe evidence:
  `tools/probe_resource_window.py --quiet` verifies the committed ROM images
  and the byte-side choices for this stop. The segment-57 read is
  `0x0bfe22..0x0c0321` inclusive (`1280` bytes). Only the first `478` bytes
  are inside the verified IC32/IC15 resource image, with suffix hash
  `e0a0fd34ce7a39f79ecd27c0ee288631554a0ff78359b72e27ea6087651bcf1f`; the
  continuation need is `802` bytes. The three modeled continuations are:
  simple resource mirror, first longword `0x48454144`, hash
  `e435e3b9d033e491b57282a88b0f321aa5fecae8128fa060844cc01379349563`;
  firmware/code-pair continuation, first longword `0x00800000`, hash
  `90934acf59d9e8519c9149dc5df228f8fec2bff8451427be265489be967cdd16`;
  and zero-fill, first longword `0x00000000`, hash
  `359f38eef400e2fa3924a3258652e74ee19cd46cb92e47bce91f1194fce25e9e`.
  The same probe shows why this remains a decode question: a simple mirror
  exposes `HEAD` at offsets `0` and `0x40000` and doubles candidate counts
  to `48` with low class-one/class-zero counts `24/24`, while code-pair and
  zero-fill expose only `HEAD` at offset `0` and keep candidate counts at
  `24` with low class-one/class-zero counts `12/12`.
- Evidence:
  [transparent-print-data.md](transparent-print-data.md),
  [resource-rom.md](resource-rom.md),
  [built-in-resource-scan.md](built-in-resource-scan.md),
  `Boundary: Secondary Segment-57 Source` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md), and
  `Transparent Print Data` in
  [semantic-state-model.md](semantic-state-model.md).
- Needed to close:
  static board/emulator memory-map evidence for what the formatter sees at
  `0x0c0000..0x0c0321`, or recovered external resource bytes for that range.

### Short Compact Downloaded-Glyph High Rows

- Classification: ROM-local invalid target/source.
- Exact boundary:
  `0x1fe76..0x1fe88` uses table base `0x1fe8a`, shifts fallback row count
  `D3` by two, loads a longword target, and jumps. Valid helper entries end at
  index `128`; indices above that read code bytes beginning at `0x2008e` as
  pointer data.
- Covered path:
  downloaded-glyph payloads install canonical glyph records through
  `0x16c14 -> 0x16498`; later printable bytes queue compact objects through
  `0xd04a -> 0x1393a -> 0x12f2e`; publication and bridge reach
  `0x1ef6a -> 0x1effe`; short compact rows enter helper `0x1fe76`.
- Exact stopped state:
  installed row words such as `0x0101..0x0103` are preserved in glyph records,
  but `0x12f2e` consumes low row bytes `0x01..0x03` for the compact selector.
  The high fallback row count then indexes past the valid `0x1fe8a` jump
  table. The documented row-`0x0102` fallback count `200` reads target
  `0x329ad3c0`.
- What is not unresolved:
  parser payload restore, downloaded-character validation, glyph install,
  compact object selection, publication, bridge, and dispatch into the short
  helper.
- Evidence: `Downloaded-Glyph Render Decision Checkpoint` in
  [downloaded-fonts.md](downloaded-fonts.md#downloaded-glyph-render-decision-checkpoint),
  [page-raster-imaging.md](page-raster-imaging.md), `Downloaded Font Descriptor And
  Payload Chain`, `Downloaded Glyph Renderer Boundary State`, and `Bitmap Render
  Dispatch Contract` in [semantic-state-model.md](semantic-state-model.md), and `Render
  Helper Boundary Index` in
  [end-to-end-reproduction-map.md](end-to-end-reproduction-map.md).
- Needed to close:
  a ROM-local explanation for why those invalid jump-table indices should be
  unreachable or redirected, or an explicitly documented invalid-target
  behavior for the computed addresses.

### Wrapped Downloaded-Glyph Low Widths

- Classification: ROM-local invalid target/source.
- Exact boundary:
  `0x1f034 -> 0x1f08e` mode-0 wrapped-width path indexes the row-copy table
  with the full span word instead of a legal byte width. For span `0x0102`,
  entry address `0x1f08e + 0x0408 = 0x1f496` contains bytes
  `00 00 66 cc`, producing jump target `0x0066cc`.
- Covered path:
  downloaded glyphs with installed spans through `0x020d` reach the same
  parser, install, printable, publication, and compact-render dispatch as the
  normal downloaded-glyph path. High source width bytes select compact-wide
  helper `0x1f0d2` and are documented for sampled cases.
- Exact stopped state:
  low source width bytes `0x00..0x10` target helpers outside the decoded
  row-copy helper heads after the normal page-object path has already
  published bucket `0`. The installed full width word is still canonical
  glyph state, but `0x12f2e` chooses selector `0x0003` from the printable
  source low byte. `0x1f034` then uses the full span returned by `0x1f354` as
  the `0x1f08e` table index. Listing
  `generated/disasm/ic30_ic13_invalid_compact_mode0_target_0066c0.lst` shows
  the sample target is not a row-copy helper.
- What is not unresolved:
  parser payload restore, installed span preservation, low-byte selector
  choice, compact object fields, publication bucket `0`, render-record bridge,
  and helper selection/pixel derivation for legal high-width cases.
- Evidence: `Downloaded-Glyph Render Decision Checkpoint` in
  [downloaded-fonts.md](downloaded-fonts.md#downloaded-glyph-render-decision-checkpoint),
  [page-raster-imaging.md](page-raster-imaging.md), `Downloaded Glyph Renderer Boundary
  State` in [semantic-state-model.md](semantic-state-model.md), and `Downloaded Glyph
  Boundary Decision Rules` in [firmware-dataflow-model.md](firmware-dataflow-model.md).
- Needed to close:
  a ROM-local guard that prevents those low-width objects from reaching the
  invalid target, or a defensible invalid-target behavior for the computed
  address family.

### Segmented-Wide Fallback Source Offset

- Classification: ROM-local invalid target/source.
- Exact boundary:
  `0x1f264` segmented-wide fallback rows for span-31 high-row siblings are
  bounded at fallback source offset `+0xb50` for the documented row products.
- Covered path:
  below-cap segmented-wide downloaded glyphs install through
  `0x16c14 -> 0x16498`, queue selector `0x3003` compact objects, and render
  selected segments through `0x1f264`. The selected-segment render cases are
  documented for sampled rows through the payload-count cap.
- Exact stopped state:
  span-31 fallback siblings reach a source offset beyond the documented copied
  bitmap/source region. Larger row/span products stop earlier at the restored
  `ESC )s#W` payload budget cap and never install a glyph.
- What is not unresolved:
  selected-segment rendering, compact selector derivation, page-record bridge,
  and the arithmetic payload-count cap.
- Evidence: `Downloaded-Glyph Render Decision Checkpoint` in
  [downloaded-fonts.md](downloaded-fonts.md#downloaded-glyph-render-decision-checkpoint),
  [page-raster-imaging.md](page-raster-imaging.md), `Downloaded Glyph Renderer Boundary
  State`, and `Bitmap Render Dispatch Contract` in
  [semantic-state-model.md](semantic-state-model.md).
- Needed to close:
  a ROM-local source-region rule for the fallback offset, or a documented
  invalid-source behavior for these span-31 fallback cases.

### Segmented-Wide Payload Count Cap

- Classification: exact ROM stop, not a render-helper unknown.
- Exact boundary:
  restored `ESC )s#W` payload budget is capped at `0x7fff` before `0x16c14`
  can install oversized segmented-wide glyphs. With span `17`,
  `floor(0x7fff / 17) = 0x0787`; `0x0788 * 17` stops before `0x16498` can
  create a glyph object.
- Covered path:
  the parser and payload reader restore the command record and byte budget, but
  the oversized stream does not reach downloaded-glyph install, page-object
  creation, publication, or render dispatch.
- Evidence: `Downloaded-Glyph Render Decision Checkpoint` in
  [downloaded-fonts.md](downloaded-fonts.md#downloaded-glyph-render-decision-checkpoint)
  and `Downloaded Font Descriptor And Payload Chain` plus `Downloaded Glyph
  Renderer Boundary State` in
  [semantic-state-model.md](semantic-state-model.md).
- Needed to close:
  none for pixel reproduction. This is the documented stop point for that
  oversized byte-stream family.

## Host And Hardware Boundaries

### Direct Input Mode 1 Register Bank

- Classification: hardware/MMIO boundary.
- Exact boundary:
  `0xa9e2..0xaa86` in `0xa904`.
- ROM-visible behavior:
  `0x8e01.4` is polled as byte-ready, `0x8801` supplies the data byte,
  `0x8c01.0` is waited on after read, and `$a601` / `$aa01` receive
  phase/control-shadow writes from `0x7828fa`. The path preserves literal
  `0x1a` after reporting it through `0x9ec0`, clears `0x7828ec`, and clears
  `0x7821c4`.
- What remains:
  physical connector/interface name, signal timing, and board-level identity
  for `0x8e01`, `0x8801`, `0x8c01`, `$a601`, and `$aa01`.
- Evidence:
  [host-byte-fetch.md](host-byte-fetch.md),
  [io-interfaces.md](io-interfaces.md), and
  `Host Byte Fetch And Data-Chain Input` in
  [semantic-state-model.md](semantic-state-model.md).

### Direct Input Mode 2 Register Bank

- Classification: hardware/MMIO boundary.
- Exact boundary:
  `0xaaa6..0xab8a` in `0xa904`.
- ROM-visible behavior:
  `0xfffee005.0` is data-ready, `0xfffee001` supplies the data byte,
  `0xfffee005.6/.7` are accumulated into `0x780e2e` as `0x40` / `0x80`, and
  `0xfffee009.6` / `0x7828fb.6` are set after a successful byte read.
- What remains:
  physical connector/interface name, signal timing, and board-level identity
  for `0xfffee005`, `0xfffee001`, and `0xfffee009`.
- Evidence:
  [host-byte-fetch.md](host-byte-fetch.md),
  [io-interfaces.md](io-interfaces.md), and
  `Host Byte Fetch And Data-Chain Input` in
  [semantic-state-model.md](semantic-state-model.md).

### Ring/Status Bridge Registers

- Classification: hardware/MMIO boundary.
- Exact boundary:
  `0xa6cc..0xa810`.
- ROM-visible behavior:
  mode-zero bridge code reads `0xfffe0001` and `0xfffe0003`, writes ring input
  state `0x783e54` / `0x783e56` / `0x783e5a`, handles low-water/full-buffer
  status via `0x780e2a`, `0x780e2e`, `0x783e60`, and `0x783e61`, and can write
  `$aa01`.
- What remains:
  physical signal names, connector identity, and timing for the MMIO registers.
- Evidence:
  [host-byte-fetch.md](host-byte-fetch.md) and generated disassembly
  `generated/disasm/ic30_ic13_a801_a601_io_00a4e8.lst`.

### Host Quiesce/No-Byte Branch Labels

- Classification: manual/physical correlation.
- Exact boundary:
  `0x4218..0x44d2` and `0x61e4..0x6362`.
- ROM-visible behavior:
  both branches write no-byte gate `0x780e3b = 1`, set `0x780e66.3`, reset
  byte-source buffers through `0x3178`, clean selected page/control pool
  records, set service-needed bit `0x7821cd.0`, and cause the next `0xa904`
  fetch to return `D7 = -1` while the gate is active. Parser loop
  `0x117dc..0x117ee` observes and clears `0x780e3b`.
- What remains:
  user-facing or service-manual labels for the two quiesce/reset callers.
- Evidence:
  [host-byte-fetch.md](host-byte-fetch.md),
  `generated/disasm/ic30_ic13_no_byte_gate_setter_004300.lst`, and
  `generated/disasm/ic30_ic13_no_byte_gate_setter_006200.lst`.

## External Resource And Service Boundaries

### Optional Resource Windows

- Classification: optional external data.
- Exact boundary:
  optional windows `0x200000..0x3ffffe` and `0x400000..0x5ffffe`, scanned by
  the page/font scheduler path when `$8000.14/15` permit it.
- ROM-visible behavior:
  `0x19dd2 -> 0x19eb6` scans optional windows, helpers `0x1a042` and `0x19f08`
  compare scratch slots against canonical slots at `0x7828b6`, and adjacent
  helpers can update candidate lists, current-record state, canonical windows,
  and active contexts.
- What remains:
  physical optional-resource contents and board/emulator memory-map evidence.
- Evidence:
  [page-font-scheduler.md](page-font-scheduler.md),
  [resource-rom.md](resource-rom.md), and
  `Page/Font Scheduler Handoff` in
  [semantic-state-model.md](semantic-state-model.md).

### Retained Defaults And Service Persistence

- Classification: hardware/MMIO boundary plus manual/physical correlation.
- Exact boundary:
  retained/default paths through `$8000.w`, `$a400`, `$8c01`, retained
  commit/readback helper `0x96c4`, startup retained load
  `0x5a16 -> 0x97e4 -> 0x56c2 -> 0x1284`, and service paths that report
  `67 SERVICE` or `68 SERVICE`.
- ROM-visible behavior:
  default-record producers, reset consumers, retained-record bulk load,
  retained commit/readback failure, and service-status publication are
  documented. Commit/readback failure sets `0x780e39.3` through
  `0x571e -> 0x9bee(0x780e36, 0x00000008)`, and `0xc1c6` consumes that bit as
  non-returning `68 SERVICE`.
- What remains:
  physical retained-storage identity, serial pins, exact failure/content
  conditions on real hardware, and service-manual wording for those retained
  record failures.
- Evidence:
  [reset-default-environment.md](reset-default-environment.md),
  [firmware-startup.md](firmware-startup.md),
  [external-ready-service.md](external-ready-service.md), and
  `Default Environment Record Producers` in
  [semantic-state-model.md](semantic-state-model.md).

### Folded Status Category Names

- Classification: manual/physical correlation.
- Exact boundary:
  aggregate helper `0x36e4..0x37f2`, output status helper `0xaece`, and
  page-environment producer `0x2888`.
- ROM-visible behavior:
  `0x36e4` folds status sources `0x780e32`, `0x780e2e`, `0x780e36`,
  `0x780e2a`, and `0x780e68` into aggregate fields `0x780e12`,
  `0x780e0e`, `0x780e0a`, and `0x780e1a`. The normal return encodes bit `7`
  from `0x780e0a == 0`, bit `0` from `0x780e0e != 0`, and bit `1` from
  `0x780e12 != 0`. Helper `0xaece` uses related fields to emit host-visible
  status bytes: `0x780e12` or `0x780e90` sets host-status bit `0`,
  `0x780e2a` sets bit `1`, `0x780e0a` sets bit `2`, and reason byte
  `0x783e60` is ORed into the base `0x30` byte.
- What remains:
  HP/manual-facing names for the folded status categories and sibling service
  bits. The arithmetic, field writes, host-status byte composition, and
  no-page-output boundary are ROM-local and documented.
- Evidence: [errors-and-status.md](errors-and-status.md),
  `generated/disasm/ic30_ic13_interface_status_aggregate_0036e4.lst`,
  `generated/disasm/ic30_ic13_host_output_worker_00ae2c.lst`, and `Host/Status
  Side-Channel Decision Checkpoint` in
  [errors-and-status.md](errors-and-status.md#hoststatus-side-channel-decision-checkpoint).

### Active Render Device Handoff

- Classification: hardware/MMIO boundary.
- Exact boundary:
  active render scheduler and device handoff around `0x1eba4`, `0xa680`, wait
  objects, and status/control registers such as `$8000`, `$8a01`, `$a200`, and
  `$a400`.
- ROM-visible behavior:
  published records are copied through `0x1ed84 -> 0x1edc6`, scheduler band
  words feed `0x1ef6a`, and render-work/wait-object state is documented for
  software-visible scheduling and per-band merge behavior.
- What remains:
  physical engine timing, device names, and signal correlation. These matter
  only when they change ROM-visible ready/busy branches, wait-object wake
  order, selected page/control record, scheduler band words, or render inputs.
- Evidence:
  [active-render-scheduler.md](active-render-scheduler.md),
  [dc-controller-engine.md](dc-controller-engine.md#owner-summary), and
  `Published Record To Active Render Scheduler` in
  [semantic-state-model.md](semantic-state-model.md).

## Use In Future Tracing

When a new byte stream reaches one of these entries, do not document it as a
fresh generic unknown. Either:

- show that the stream stops at the same exact boundary with different input
  fields;
- show that it changes a named upstream field, object byte, bridge root,
  render helper input, or scheduler state before the boundary; or
- add a new boundary with the exact address/range, classification, covered
  upstream path, evidence, and evidence needed to close it.
