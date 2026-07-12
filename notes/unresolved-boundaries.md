# Unresolved Boundaries

This note is the checked-in index for exact boundaries that remain after the
current ROM-local dataflow documentation. It is not a backlog of every untested
variant. A boundary belongs here only when the documented trace reaches a
specific address, field, helper, or external memory range and cannot make a
stronger claim from the ROM evidence currently available.

## Owner Summary

This note owns the residual stop points for the ROM dataflow model. Command
owners and route maps should link here only after they have already documented
the upstream parser route, command handler, fields, page/image objects, bridge
state, and render-helper entry. A boundary here is therefore the exact point
where the checked-in model must stop, not a license to leave the earlier route
vague.

Boundary classes:

- ROM-local invalid target/source:
  computed helper targets or source reads that leave the documented valid
  table or bitmap/source range, such as downloaded-glyph compact helper
  over-indexing after `0x1fe76`, wrapped mode-0 target selection through
  `0x1f034 -> 0x1f08e`, or segmented-wide fallback source reads after
  `0x1f264`.
- ROM-local unresolved caller:
  decoded helper bodies whose field effects are documented, but whose direct
  caller, computed target, trap/vector entry, or scheduler entry is not located
  in the current ROM evidence.
- Missing external resource data:
  ROM-visible reads beyond the verified IC32/IC15 resource suffix, currently
  the secondary segment-57 source range `0x0c0000..0x0c0321`.
- Exact ROM stop:
  byte-stream families where the ROM reaches a documented terminal limit before
  the later page-object or render route exists. The current example is the
  restored `ESC )s#W` payload-count cap: parser/tokenizer state, delayed
  restore, and payload budget are fully documented, and no downloaded-glyph
  object or pixel helper is created for the oversized stream.
- Hardware/MMIO boundary:
  ROM-visible polling, wait-object, status, or output-side behavior where the
  physical device identity or connector timing is not proven.
- Optional external data:
  optional cartridge/resource windows whose ROM control flow is documented but
  whose contents are not present.
- Manual/physical correlation:
  ROM behavior whose service-manual or user-facing name is not assigned.

State classification:

- Canonical upstream state:
  the handler records, command-family fields, installed resources, page roots,
  page objects, publication records, render roots, and helper inputs already
  documented before the stop.
- Derived/cache state:
  computed indexes, row/span products, fallback counts, table offsets,
  resource addresses, and scheduler/cache fields that expose the stop.
- Parser scratch:
  restored six-byte records, delayed-payload state, payload budgets, and
  transient query or drain state consumed before the boundary.
- Firmware bookkeeping:
  allocator/release state, retry or publication flags, wait-object state,
  FIFO/status state, and active render progress that controls how the ROM
  reaches the stop.
- Hardware/external state:
  physical resource decode, MMIO identity, connector timing, optional
  cartridge contents, retained-storage identity, or panel/sensor provenance.
- Unknown:
  only the named invalid target, missing range, physical identity, optional
  contents, or manual-facing label. Upstream parser dispatch, page-object
  production, bridge roots, and render dispatch are not unknown unless a
  specific entry says they are.

Use the classification column before continuing work:

- ROM-local invalid target/source: the ROM reaches an address or table/source
  calculation that is defined by instructions, but the calculated target or
  source is outside the documented valid helper/data range.
- ROM-local unresolved caller: the helper body and its fields are decoded, but
  the checked-in model lacks the ROM entry provenance needed to treat it as an
  ordinary parser-to-render route.
- Missing external resource data: the ROM asks for bytes outside the verified
  local resource image.
- Exact ROM stop: the ROM consumes the stream into a documented terminal state
  before a later command-family object or render helper can exist.
- Hardware/MMIO boundary: the ROM-visible polling, status, or handshake
  behavior is documented, but the physical device, connector, or timing
  identity is not.
- Optional external data: the ROM control flow is documented, but optional
  cartridge/resource-window contents are not available.
- Manual/physical correlation: the ROM behavior is documented, but user-facing
  names or service-manual labels are not assigned.

## Unresolved Boundary Outcome Matrix

This matrix is the audit entry point for the exact places where the checked-in
ROM model intentionally stops. Each entry keeps the upstream route documented
and limits the unknown to a named address, range, physical identity, optional
data source, or manual label.

ROM-local invalid render target/source:

- Boundary class:
  ROM-local invalid target/source.
- Exact stops:
  `0x1fe76..0x1fe88` compact downloaded-glyph high-row jump-table over-index;
  `0x1f034 -> 0x1f08e` wrapped mode-0 width target selection; and
  `0x1f264` segmented-wide fallback source offset `+0xb50`.
- Covered upstream state:
  downloaded-font parser payload restore, glyph install, compact object
  queueing, publication, render-record bridge, and dispatch to the named
  compact helper are documented before these stops.
- Output effect:
  a reproducer should report the invalid computed target/source instead of
  inventing final pixels after the ROM selects an unchecked helper address or
  source range.
- Evidence:
  [downloaded-fonts.md](downloaded-fonts.md#downloaded-glyph-render-decision-checkpoint),
  [page-raster-imaging.md](page-raster-imaging.md#render-entry-outcome-matrix), and
  `Render Helper Boundary Index` in
  [end-to-end-reproduction-map.md](end-to-end-reproduction-map.md).
- Needed to close:
  ROM-local guard evidence, a valid target/source rule, or a documented
  invalid-target behavior for the computed address family.

Missing built-in resource continuation:

- Boundary class:
  missing external resource data.
- Exact stop:
  verified resource suffix `0x0bfe22..0x0bffff`, then required firmware range
  `0x0c0000..0x0c0321`.
- Covered upstream state:
  transparent `ESC &p#X` parser dispatch, payload handling, selected context,
  page-record allocation, publication, render bridge, compact dispatch, and
  verified suffix rows.
- Output effect:
  rows needing bytes after `0x0bffff` remain unresolved until the physical
  byte source is known.
- Evidence: [resource-rom.md](resource-rom.md#resource-rom-outcome-matrix),
  [transparent-print-data.md](transparent-print-data.md#transparent-payload-outcome-matrix),
  [built-in-resource-scan.md](built-in-resource-scan.md#resource-scan-outcome-matrix),
  and `tools/probe_resource_window.py`.
- Needed to close:
  static board, emulator, gate-array, or recovered resource evidence for
  `0x0c0000..0x0c0321`.

Exact parser payload-count stop:

- Boundary class:
  exact ROM stop, not a render-helper unknown.
- Exact stop:
  tokenizer cap `0xdb74 -> 0x7fff`, delayed restore
  `0x121cc -> 0x12218`, payload budget `0x783140`, and
  span-17 row count `0x0788` requiring more bytes than the restored budget.
- Covered upstream state:
  parser record creation, delayed restore, descriptor/resource payload routing,
  and below-cap downloaded-glyph neighbor paths.
- Output effect:
  no glyph object, page-root bucket, publication record, or render work exists
  for the oversized stream; reproduction stops at parser payload state.
- Evidence:
  [downloaded-fonts.md](downloaded-fonts.md#segmented-wide-payload-count-cap-checkpoint)
  and [pcl-parser-firmware.md](pcl-parser-firmware.md#parser-firmware-outcome-matrix).
- Needed to close:
  none for pixel reproduction. This is a documented terminal ROM behavior.

Host and formatter/MMIO boundaries:

- Boundary class:
  hardware/MMIO boundary.
- Exact stops:
  direct input mode 1 `0xa9e2..0xaa86`, direct input mode 2 `0xaaa6..0xab8a`,
  ring/status bridge `0xa6cc..0xa810`, timer/status and scan/status paths
  `0x0d52..0x0f7a` / `0x0f84..0x10f2`, wait-object/trap paths
  `0x10bc..0x1282`, active-pool wrapper `0x1cf8..0x1ea8`, and active render
  device handoff around `0x1eba4`.
- Covered upstream state:
  byte-source priority, parser-visible return values, wait-object effects,
  scheduler state, active source selection, render work records, and band
  words are documented.
- Output effect:
  physical timing or device identity matters only if it changes admitted byte
  order, status branch, wait-object wake order, selected page/control record,
  render band word, or render input.
- Evidence:
  [host-byte-fetch.md](host-byte-fetch.md#host-byte-source-outcome-matrix),
  [dc-controller-engine.md](dc-controller-engine.md#dc-boundary-outcome-matrix),
  [active-render-scheduler.md](active-render-scheduler.md#scheduler-outcome-matrix),
  and [io-interfaces.md](io-interfaces.md#interface-outcome-matrix).
- Needed to close:
  board/register-to-connector evidence and physical timing evidence for the
  named MMIO registers and formatter/DC signals.

### Optional Active-Pool Pattern Helper Caller

- Boundary class:
  ROM-local unresolved caller.
- Exact stop:
  direct entry provenance for helper bodies `0x247c..0x2746`. The current xref scan
  does not locate an absolute `0x0000247c` target; the adjacent copy-pass
  listing returns at `0x2330` and the coordinate helper returns at `0x247a`
  before the separate `0x247c` body. A broad disassembly search for `247c`,
  `26de`, and `270c` finds the helper body, existing documentation, and
  unrelated `movea.l` opcodes or resource-data values, but no decoded branch,
  jump, trap/vector entry, or computed-target table naming those addresses.
  No current evidence proves an entry into sibling bodies `0x26de` or
  `0x270c`.
- Covered upstream state:
  active-pool scheduling, work-record selection, source pointer `0x783992`,
  destination row base `0x78399a`, row-copy jump offset `0x7839a4`,
  destination stride `0x7839a8`, accumulator `0x7839d4`, and pattern-pointer
  cache `0x7839d8..0x7839f7` are documented before the stop. The expanded
  helper listing shows `0x247c..0x26dc` copying eight destination rows and
  accumulating their longword sum into `0x7839d4`, `0x26de..0x270a` deriving
  eight pattern pointers from accumulator nibbles, and `0x270c..0x2746`
  writing seven words per pattern column into the destination rooted at
  `0x78399a`. Ordinary active rendering still reaches page-band objects
  through `0x1ef6a` and copied rows through `0x22f4`.
- State provenance:
  `0x1a9c..0x1abe` and `0x1b2c..0x1b46` write `0x7839a8` and
  `0x7839a4` from the active-pool width calculation; `0x1bd0` writes
  destination row base `0x78399a`; and `0x1bf6` clears accumulator
  `0x7839d4` before the copy window. Later active-pool copy loops
  `0x1db0..0x1e2e` and `0x2038..0x211c` either advance `0x783992` by
  `0x7839a0`, recompute it through `0x2456`, or call ordinary copy helper
  `0x22f4`. The unresolved optional helper would read the same state at
  `0x247c` (`0x783992`, `0x78399a`, `0x7839a4`, `0x7839a8`), update
  `0x7839d4` at `0x26c4`, fill `0x7839d8..0x7839f7` at `0x26de..0x270a`,
  and consume that cache at `0x270c..0x2746`.
- Output effect:
  do not treat `0x247c..0x2746` as an ordinary page-object pixel route unless
  a caller is located. If later ROM evidence proves an entry into `0x247c`,
  `0x26de`, or `0x270c`, model the decoded accumulator, pattern-pointer, and
  destination writes from those helper bodies; otherwise it remains a bounded
  side path outside the supported parser-to-pixels route.
- Evidence:
  [active-render-scheduler.md](active-render-scheduler.md#scheduler-outcome-matrix),
  [semantic-state-model.md](semantic-state-model.md#published-record-to-active-render-scheduler),
  `generated/disasm/ic30_ic13_engine_copy_pass_0022f4.lst`,
  `generated/disasm/ic30_ic13_engine_copy_pattern_00247c.lst`, and
  `generated/analysis/ic30_ic13_long_reference_scan.md`.
- Needed to close:
  static caller/xref evidence, a computed jump target, a trap/vector entry, or
  scheduler-entry evidence proving ROM control flow into `0x247c`, `0x26de`,
  or `0x270c`.

Optional external resource windows:

- Boundary class:
  optional external data.
- Exact stop:
  optional resource windows `0x200000..0x3ffffe` and
  `0x400000..0x5ffffe`.
- Covered upstream state:
  page/font scheduler handoff, optional-window scan control flow, candidate
  table updates, and font-resource caller return behavior are documented.
- Output effect:
  optional data can change font/resource candidates and later glyph rows, but
  absent cartridge contents cannot be inferred from the base ROM.
- Evidence:
  [page-font-scheduler.md](page-font-scheduler.md#page-font-scheduler-outcome-matrix),
  [resource-rom.md](resource-rom.md#resource-rom-outcome-matrix), and
  `Page/Font Scheduler Handoff` in
  [semantic-state-model.md](semantic-state-model.md).
- Needed to close:
  physical cartridge/resource images or emulator memory-map data for those
  windows.

Manual and service-name correlation:

- Boundary class:
  manual/physical correlation.
- Exact stops:
  host quiesce/no-byte callers `0x4218..0x44d2` and `0x61e4..0x6362`,
  retained default/service paths through `$8000.w`, `$a400`, `$8c01`,
  folded status aggregation `0x36e4..0x37f2`, output status helper `0xaece`,
  and page-environment producer `0x2888`.
- Covered upstream state:
  ROM-visible status fields, no-byte gates, retained/default records, service
  bits, host-output status byte composition, and no-page-output boundaries are
  documented.
- Output effect:
  firmware behavior is reproducible from fields; the unresolved part is the
  HP/manual name, physical storage identity, or service wording.
- Evidence:
  [host-byte-fetch.md](host-byte-fetch.md#host-byte-source-outcome-matrix),
  control-panel default outcome matrix in
  [control-panel-nvram-selftest.md](control-panel-nvram-selftest.md),
  [external-ready-service.md](external-ready-service.md#external-ready-outcome-matrix),
  and [errors-and-status.md](errors-and-status.md#hoststatus-outcome-matrix).
- Needed to close:
  service-manual correlation, board-level retained-storage evidence, or
  physical failure-condition evidence.

State grouping for this matrix:

- Canonical:
  documented upstream handler records, resource/glyph records, page roots,
  publication records, render roots, status fields, and scheduler state.
- Derived/cache:
  computed helper indexes, source offsets, row/span products, resource ranges,
  active-pool helper offsets, optional pattern-pointer caches, wait-object
  predicates, status folds, and continuation hashes.
- Parser scratch:
  restored six-byte records, delayed payload state, payload budgets, alternate
  drains, and query/no-byte parser state that reach a boundary.
- Firmware bookkeeping:
  allocation/release state, publication flags, retry state, wait objects,
  FIFO/status bytes, retained dirty flags, and render progress words.
- Hardware/external:
  physical resource decode, optional cartridge contents, MMIO identity,
  connector timing, retained-storage identity, panel/sensor provenance, and
  service-manual labels.
- Unknown:
  only the specific invalid target/source, missing range, physical identity,
  unresolved helper caller, optional contents, timing source, or manual name
  listed above. Earlier parser dispatch, page-object production, bridge roots,
  and render dispatch remain documented by their owner notes.

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

## Renderer Stop Contract

This checkpoint turns the pixel-affecting boundaries into the rule a byte-stream
reproducer should apply after the upstream command path is modeled. Each row
keeps the detailed owner notes as evidence; the contract here is the exact
handoff from documented ROM state to a bounded non-pixel result.

- Short compact downloaded-glyph high rows:
  preserve the restored `ESC )s#W` record, installed glyph record from
  `0x16c14 -> 0x16498`, compact object from
  `0xd04a -> 0x1393a -> 0x12f2e`, published bucket/root state from `0xff1e`,
  render bridge state from `0x1ed84 -> 0x1edc6`, and helper entry
  `0x1ef6a -> 0x1effe -> 0x1fe76`. Stop when fallback count `D3 > 128`
  would read beyond the valid `0x1fe8a` row-target table. Report the computed
  table read, for example row `0x0102` fallback count `200` reading target
  `0x329ad3c0`, rather than inventing fallback pixels.
- Wrapped downloaded-glyph low widths:
  preserve the installed full width word, the low-byte compact selector chosen
  by `0x12f2e`, bucket `0` publication, render-record bridge, and dispatch to
  compact mode-0 helper `0x1f034`. Stop when `0x1f034` indexes table
  `0x1f08e` with the full span word rather than legal width `1..16`. Report
  the computed target, for example span `0x0102` reading
  `0x1f08e + 0x0408 = 0x1f496` and target `0x0066cc`.
- Segmented-wide span-31 fallback source:
  preserve selector `0x3003` compact objects, selected segment `1`, the
  `0x1f264` segmented-wide dispatch, current-band rows, and neighboring
  successful fallback rows. Stop at the fallback A2 source read when the
  segmented-wide span-31 sibling reaches modeled bitmap offset `+0xb50`.
  Report the source-read boundary instead of deriving bytes beyond the copied
  glyph payload.
- Segmented-wide payload-count cap:
  preserve parser/tokenizer state only: `0xdb74` clamped count `0x7fff`,
  delayed snapshot `0x121cc`, restored record `0x12218`, and payload budget
  `0x783140` consumed by `0x16c14`. Stop before glyph install when the needed
  byte count exceeds the restored budget, such as row `0x0788` at span `17`
  requiring `0x7ff8` bytes. This case has no glyph object, page-root bucket,
  publication record, render bridge, or pixel helper entry to model.

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
- Triggering stream family:
  the documented page-visible stream is secondary transparent data such as
  `SO ESC &p3X ! 80 !`. `SO` selects secondary context slot `1` through
  `0xc6b8`; `ESC &p3X` installs a delayed transparent-data record; payload byte
  `0x80` enters the high-control printable route and maps through the secondary
  `LINE_PRINTER` context to glyph `0x5f`.
- Writers:
  `0x12452` restores the transparent-data payload record and returns normalized
  bytes to the ordinary printable path; `0xd04a` / `0x1393a` resolve the selected
  context and glyph; `0x12f2e` writes compact bucket objects under page-root
  `+0x1c`; `0xff1e` publishes that page root; and `0x1ed84 -> 0x1edc6` copies
  the published bucket root and context slots into render state.
- Readers/consumers:
  `0x1ef6a -> 0x1effe -> 0x1f354` consumes the bridged compact object and
  secondary context. `0x1f354` accepts the zero offset-table entry for glyph
  `0x5f` as a record header at file offset `0x02e122`; segmented helper
  `0x1f1f0` then advances to segment `0x39` and source file offset `0x03fe22`.
- Exact stopped state:
  secondary high-control glyph `0x5f`, segment `0x39`, and firmware source
  address `0x0bfe22` are documented through the verified suffix. Bucket `448`
  is covered. Bucket `456` needs bytes beyond `0x0bffff`, so row bytes depend
  on the physical decode for `0x0c0000..0x0c0321`.
- Output effect:
  a reproducer should render or otherwise derive only the rows backed by verified
  bytes `0x0bfe22..0x0bffff`. Fallback rows that require bytes
  `0x0c0000..0x0c0321` must stop at this boundary unless external board,
  emulator, gate-array, or recovered-resource evidence supplies the byte source.
- What is not unresolved:
  parser dispatch, transparent count handling, `0x1a 0x58` normalization,
  selected-context filtering, page-record allocation, bridge fields, compact
  dispatch, segment skip arithmetic, and zero-offset glyph-entry
  interpretation.
- Local probe evidence:
  `tools/probe_resource_window.py --quiet` verifies the local ROM images selected
  by `data/rom_manifest.json` and the byte-side choices for this stop. The
  segment-57 read is `0x0bfe22..0x0c0321` inclusive (`1280` bytes). Only the
  first `478` bytes are inside the verified IC32/IC15 resource image, with
  suffix hash
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
  bitmap/source region. `0x1f264` has already selected segment `1`, adjusted
  A2/A3 by the `0x80` row skip, split the selected segment through `0x1f414`,
  and saved fallback source state in `0x783a48`; the stop is the fallback A2
  source read at offset `+0xb50`. Larger row/span products stop earlier at the
  restored `ESC )s#W` payload budget cap and never install a glyph.
- What is not unresolved:
  parser payload restore, installed row/span preservation, compact selector
  derivation, bucket `8` selected-segment publication, page-record bridge,
  `0x1f264` dispatch, current-band rows, neighboring successful fallback rows,
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
  tokenizer `0xdb74` clamps the `ESC )s#W` numeric record word to `0x7fff`;
  delayed restore through `0x121cc` / `0x12218` preserves that record, and
  `0x15d0a` / `0x16c14` load the capped absolute count into `0x783140`. With
  span `17`, `floor(0x7fff / 17) = 0x0787`; `0x0788 * 17` stops before a
  completed downloaded-glyph object can feed page-object creation.
- Covered path:
  the parser and payload reader restore the command record and byte budget, but
  the oversized stream does not reach downloaded-glyph install, page-object
  creation, publication, or render dispatch.
- Exact stopped state:
  `0xdb74` has already stored the capped count in parsed record word `+2`;
  `0x121cc` has saved that six-byte record; `0x12218` has restored it; and
  `0x16c14` has copied the absolute count into payload budget `0x783140`.
  The bitmap readers under `0x16498` would need `row_word * span` accepted
  bytes before a complete downloaded-character record exists. For row
  `0x0788` and span `17`, the required `0x7ff8` bytes exceed the restored
  budget, so the stream stops with parser payload state and no canonical glyph
  record, page-root bucket, publication record, or render work.
- What is not unresolved:
  tokenizer clamp, delayed-record restore, payload-budget storage, descriptor
  and resource drain exits, and the below-cap neighbor path through
  `0x16498`, `0x12f2e`, selector `0x3003`, and renderer `0x1f264`.
- Evidence: `Downloaded-Glyph Render Decision Checkpoint` in
  [downloaded-fonts.md](downloaded-fonts.md#downloaded-glyph-render-decision-checkpoint)
  and `Segmented-Wide Payload Count Cap Checkpoint` in
  [downloaded-fonts.md](downloaded-fonts.md#segmented-wide-payload-count-cap-checkpoint),
  plus `Downloaded Font Descriptor And Payload Chain` and `Downloaded Glyph Renderer
  Boundary State` in [semantic-state-model.md](semantic-state-model.md). Disassembly
  evidence is `generated/disasm/ic30_ic13_pcl_escape_parser_00da9a.lst`,
  `generated/disasm/ic30_ic13_font_payload_setup_015b80.lst`,
  `generated/disasm/ic30_ic13_font_resource_object_add_016c14.lst`,
  `generated/disasm/ic30_ic13_font_stream_byte_helpers_01599c.lst`, and
  `generated/disasm/ic30_ic13_font_payload_readers_0168dc.lst`.
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
  [dc-controller-engine.md](dc-controller-engine.md), and
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
