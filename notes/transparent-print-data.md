# Transparent Print Data Firmware

This note documents the `ESC &p#X` transparent print data path. It is an
end-to-end parser cluster: a parsed PCL command schedules a delayed payload
handler, the handler consumes raw host bytes, and printable payload bytes
re-enter the normal text imaging path.

Evidence:

- `generated/disasm/ic30_ic13_transparent_data_handler_011f5a.lst`
- `generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst`
- `generated/disasm/ic30_ic13_payload_control_helper_00d99a.lst`
- `tools/render_fixture_harness.py`, fixtures:
  - `0x11f5a/0x12452 transparent text restores and consumes counted bytes`
  - `transparent data parser trace feeds page-record queue`
  - `transparent non-0x58 probe byte reaches page-record output`
  - `transparent data control payloads advance through fixed-space path`
  - `transparent default-filtered control enters unflagged fixed-record path`
  - `transparent nonzero filters route controls through printable path`
  - `transparent nonzero high-control byte queues tall glyph bucket`
  - `transparent nonzero high-control interior samples remain printable`
  - `transparent nonzero high-control upper bound remains printable`
  - `transparent secondary high-control byte enters segmented page-record path`
  - `transparent secondary segmented render prefix exposes source boundary`
  - `transparent secondary segment-57 continuation policies diverge after
    verified bytes`
  - `0x41a HEAD scanner would duplicate records under simple resource mirror`
  - `0x41a HEAD scanner rejects non-HEAD 0x40000 continuations`

Status: composed for parser dispatch through transparent payload consumption,
normal text/fixed-space routing, compact page-record output, and the secondary
segmented render boundary. The detailed byte-stream fixtures below preserve the
low-level ledger; this owner summary is the canonical semantic model for this
command family.

## Owner Summary

Concept: transparent print data is a counted byte-stream splice, not an opaque
binary skip. `ESC &p#X` reaches `0x11f5a`, which schedules delayed reader
`0x12452` through `0x121cc`; restore path `0x12218` reopens the saved six-byte
record. In normal parser mode, `0x12218` calls `0x12452`, which consumes raw
bytes through `0xa904`, normalizes local `0x1a 0x58` to `0x7f`, routes each
payload value through `0xd04a` or `0xd0f0`, and then leaves page-record
construction, bridge, and rendering to the ordinary text path. In
alternate/data mode, `0x12218` diverts the restored record through `0x12358`;
because the saved transparent handler is not wrapper `0x1228a`, positive
counts are drained through `0xdace` and appended through `0xe002` instead of
calling `0x12452`.

Primary route:

- Parser command: `ESC &p#X -> 0x11f5a`.
- Delayed record: `0x11f5a -> 0x121cc -> 0x12218 -> 0x12452`.
- Printable output: `0x12452 -> 0xd04a -> 0x1393a -> 0x12f2e ->
  0x1387c -> 0xff1e -> 0x1ed84 -> 0x1edc6 -> 0x1ef6a -> 0x1efc2 ->
  0x1effe`, followed by the compact row-store helper selected by the queued
  object.
- Fixed-space/control output: `0x12452 -> 0xd0f0`, which can either advance
  spacing only in the flagged built-in path or queue substituted host-space
  text in the documented unflagged fixed-record path.
- Alternate/data append output:
  `0x12218 -> 0x12358 -> 0xdace -> 0xe002` for positive delayed counts when
  `0x782c18` is set and saved handler `0x782a1c != 0x1228a`.

Field groups:

- Canonical parser state: command record `+2` byte count, live command-record
  cursor `0x78299e`, delayed pending flag `0x782a1a`, delayed handler pointer
  `0x782a1c`, and saved command record `0x782a20..0x782a25`.
- Canonical text/page state: selected context slot `0x782f06`, selected C0
  filter byte `0x782eea + 0x10 * slot`, fallback high-control filter byte
  `0x782efa`, high-character flags `0x783132` / `0x783133`, text cursor
  `0x782c8a`, current page root `0x78297a`, compact bucket root `+0x1c`,
  short compact object fields `+0x04` class, `+0x05` context slot, `+0x06`
  entry count, payload entries from `+0x0a`, and downstream publication /
  bridge fields consumed by `0xff1e`, `0x1ed84`, `0x1edc6`, `0x1ef6a`, and
  the compact row-store helpers.
- Derived/cache state: local filter word `A6-2`, normalized payload value
  `D5`, selected-slot scale result from `0x332ee`, text source scratch
  `0x782d7e`, compact coordinates such as `0x0001` and `0x0604`, and renderer
  segment/bucket caches.
- Parser scratch: fetched payload bytes from `0xa904`, local payload count
  `D4`, and the temporary `0x1a` probe byte.
- Firmware bookkeeping:
  `0xd99a` side effect for local `0x1a 0x58` normalization, payload-control
  counter `0x782c72`, status accumulator `0x780e2e.5`, and the
  alternate/data restore redirect
  `0x1226e..0x1227e -> 0x12358(0x1228a)`, whose non-wrapper branch drains
  positive counts through `0xdace` and appends normalized bytes through
  `0xe002`.
- Hardware/external state: secondary segment-57 fallback rows require bytes
  from firmware `0x0c0000..0x0c0321` after verified resource suffix
  `0x0bfe22..0x0bffff`.
- Unknown: manual-facing names for the filtering/context bytes
  `0x782eea + 0x10 * slot`, `0x782efa`, `0x783132`, and `0x783133`.

Writers:

- `0x121cc..0x12210` writes the delayed snapshot.
- `0x12218..0x12264` restores the saved command record and calls the delayed
  handler in normal parser mode.
- `0x1226e..0x1227e` redirects restored delayed payloads through
  `0x12358(0x1228a)` when alternate/data flag `0x782c18` is set.
- `0x12358..0x123ac` calls `0x1228a` only when saved handler `0x782a1c`
  equals wrapper argument `0x1228a`; otherwise it drains positive record counts
  through `0xdace` and writes each normalized byte through `0xe002`.
- `0x14d3a..0x14d7e` writes high-character flags `0x783132` and `0x783133`
  during primary or secondary font/map activation.
- `0x1c604`, `0x1ceea`, and `0x1e9fc` write primary selected-context filter
  byte `0x782eea` from font/sample-page setup paths.
- `0x12452..0x12534` decrements payload count `D4`, applies the local probe,
  and selects `0xd04a` or `0xd0f0`.
- `0xd99a` is called only after `0x12452` has consumed local pair
  `0x1a 0x58`. In normal transparent mode, saved handler `0x782a1c` is
  `0x12452`, so `0xd99a` takes its normal branch: ensure current root
  `0x78297a` through `0x10084`, increment `0x782c72`, signal
  `0x780e2e.5` on first use, and publish through `0xf34a -> 0xff1e` if the
  counter overflows. In alternate/data mode, `0x12218` redirects through
  `0x12358` and `0x12452` is not called, so this normal branch is not part of
  the append-only path.
- `0xd04a` / `0xd824` write compact page-record text objects; `0x12f2e` and
  `0x1387c` allocate or merge those records under current root bucket `+0x1c`.
- `0xd0f0` writes the source object for substituted host space; the flagged
  built-in path clears source `+4` before `0xd550`, while the unflagged
  fixed-record path continues through `0xd140` / `0xd3b2`.
- `0xff1e` publishes the current root, `0x1ed84` selects the render source
  through `0x780eae`, and `0x1edc6` copies the source bucket root into render
  record `+0x18`.

Readers and consumers:

- `0xa904` supplies transparent payload bytes.
- `0x12452` reads command record `+2`, selected-context C0 filter state,
  fallback high-control filter state, high-character flags, and payload bytes.
- `0xd04a` / `0x1393a` consume the routed printable value, current font/map
  context, source record, and cursor state.
- `0xd0f0` consumes filtered control/high-control bytes as substituted host
  space under the current source class.
- `0x12f2e` and `0x1387c` consume compact source/object state and current root
  topology. `0xff1e`, `0x1ed84`, `0x1edc6`, and `0x1ef6a` consume queued text
  objects for publication, bridge, and compact text rendering through the
  selected compact row-store helper.

Output effect:

- Transparent payload bytes are not parsed as commands while the count is
  active.
- `0x1a 0x58` consumes two host bytes and contributes routed value `0x7f`;
  `0x1a xx` with `xx != 0x58` contributes `xx`. The `0x7f` substitution and
  the `0xd99a` side effect are separate: the routed byte still follows the
  `0xd04a` / `0xd0f0` filter decision, while the helper may also update
  `0x782c72`, signal `0x780e2e.5`, or publish an existing root in normal
  transparent mode.
- Printable payload values use the same compact text object and render path as
  normal printable host bytes. In the pinned short compact cases, object byte
  `+0x04` is compact class `0`, `+0x05` is the selected context slot, `+0x06`
  is the entry count, and entries from `+0x0a` pair glyph bytes with compact
  coordinates such as `0x0001`, `0x0202`, or `0x0604`.
- Default-filtered C0 and `0x80..0x9f` values enter `0xd0f0`. In the flagged
  built-in path they advance spacing without compact glyph entries; in the
  unflagged fixed-record path the substituted host space can queue a compact
  glyph entry.
- Nonzero filtered C0 and `0x80..0x9f` values enter `0xd04a` and become normal
  mapped text entries.
- Secondary-context high-control bytes use the same `0x12452` decision point
  after `SO`; the documented `SO ESC &p3X!\x80!` path changes the compact
  selector to segmented class `0x2001`, bridges the secondary context roots,
  and stops only at the exact external resource boundary below.

Evidence strength:

- The delayed payload boundary is supported by disassembly
  `0x11f5a..0x11f6c`, `0x121cc..0x12210`, and `0x12218..0x1227e`.
- Probe handling and both filter polarities are supported by
  `0x12452..0x12534`.
- Printable and fixed-space page effects are supported by the documented
  downstream paths through `0xd04a`, `0xd0f0`, `0xd550`, `0xd140`, `0xd3b2`,
  `0x12f2e`, and `0x1387c`, plus the byte-stream fixtures listed above.
- The remaining middle edge is not parser routing, page-record storage,
  bridge, or compact-render arithmetic. It is the physical/resource-window
  byte source for firmware range `0x0c0000..0x0c0321` in the secondary
  segment-57 fallback rows. The ROM path reaches that range through
  `0x1f354` and `0x1f1f0` with glyph `0x5f`, segment `0x39`, file source
  `0x03fe22`, firmware source `0x0bfe22`, and required read window
  `0x0bfe22..0x0c0321`.

## Transparent Payload Outcome Matrix

This matrix is the reader-facing contract for `ESC &p#X`. It preserves the
low-level ledger below, but groups the command family by observable firmware
outcome: how the parsed command is armed, where its bytes are consumed, which
state is read or written, and what page or pixel effect follows.

- Arming command:
  `ESC &p#X` reaches normal-table mode `9` handler `0x11f5a`. The handler
  stores delayed reader `0x12452` through `0x121cc..0x12210`, rewinds the
  six-byte command record from live cursor `0x78299e`, sets pending flag
  `0x782a1a`, writes handler pointer `0x782a1c`, and copies the record to
  `0x782a20..0x782a25`. Output effect: no payload byte is consumed and no
  page object is built at the arming command.

- Normal delayed restore:
  `0x12218..0x12264` clears pending flag `0x782a1a`, restores the saved
  six-byte record to live cursor `0x78299e`, advances the cursor by six, and
  calls `0x12452` when alternate/data flag `0x782c18` is clear. Consumers:
  the restored record word `+2` becomes the transparent payload count, and
  `0xa904` becomes the byte source for the counted payload. Output effect:
  later branches in this matrix decide whether each routed payload value
  becomes printable text, substituted fixed-space output, or no page object.

- Alternate/data restore:
  `0x1226e..0x1227e` redirects a restored delayed payload through
  `0x12358(0x1228a)` when `0x782c18` is set. Because the saved transparent
  handler `0x12452` differs from wrapper argument `0x1228a`, `0x12358` rewinds
  the restored record, returns without consuming nonpositive counts, and for
  positive counts drains bytes through `0xdace` and appends each normalized
  byte through `0xe002`. State class: firmware bookkeeping plus parser scratch
  and canonical macro/data-chain stored input, not text/page canonical state.
  Output effect: `0x12452`, `0xd04a`, `0xd0f0`, page-record storage, bridge,
  and rendering are not reached from this branch; any pixels can only come if
  the appended bytes are replayed later.

- Counted payload loop:
  `0x12452..0x12474` reads absolute count from command-record word `+2`,
  keeps local countdown `D4`, and fetches bytes through `0xa904`. If `0xa904`
  returns `-1`, `0x124e8..0x124f6` exits the reader before routing another
  value. Output effect: only values actually returned by `0xa904` can affect
  text, spacing, or page objects; the count does not cause parser dispatch
  while the transparent reader is active.

- Local `0x1a` probe:
  `0x124d6..0x124e6` gives probe byte `0x1a` special local meaning. Pair
  `0x1a 0x58` consumes two host bytes, calls bookkeeping helper `0xd99a`,
  and contributes routed value `0x7f`; pair `0x1a xx` with `xx != 0x58`
  contributes `xx`. Output effect: the normalized value then rejoins the same
  printable or fixed-space branch as an ordinary payload value.

- Filter and high-character selector:
  `0x12496..0x124b8` chooses local filter word `A6-2` from high-character
  flags `0x783132` / `0x783133`, fallback high-control filter byte
  `0x782efa`, selected context slot `0x782f06`, and selected C0 filter byte
  `0x782eea + 0x10 * slot`. Writers for the flags are
  `0x14d3a..0x14d7e`; writers for selected filter byte `0x782eea` include
  `0x1c604`, `0x1ceea`, and `0x1e9fc`. Output effect: the selected filter
  state decides whether C0 and `0x80..0x9f` payload values become fixed-space
  substitutions or printable text entries.

- Printable payload:
  `0x12452..0x12534` sends values outside the filtered control ranges, and
  filtered controls with nonzero filter state, to `0xd04a`. Consumers
  continue through `0x1393a -> 0x12f2e -> 0x1387c` under the current page
  root. Output effect: payload values queue compact text objects whose short
  form carries class/context/count in `+0x04/+0x05/+0x06` and glyph/coordinate
  pairs from `+0x0a`; publication copies current root bucket `+0x1c` through
  `0xff1e -> 0x1ed84 -> 0x1edc6`, and compact rendering continues through
  `0x1ef6a -> 0x1efc2 -> 0x1effe` to the compact row-store helper selected by
  the object.

- Fixed-space payload:
  Default-filtered C0 and `0x80..0x9f` values call `0xd0f0`. In a flagged
  built-in source path, `0xd0f0 -> 0xd550` advances spacing and clears source
  `+4` without queuing compact glyph data. In an unflagged fixed-record path,
  `0xd0f0 -> 0xd140 -> 0xd3b2` can substitute host space and queue a compact
  text object. Output effect: the same payload byte can be spacing-only or a
  visible compact space depending on current source/font state.

- Secondary high-control render boundary:
  After `SO` selects secondary context, `SO ESC &p3X ! 80 !` reaches the same
  delayed reader, routes high-control payload `0x80` through the printable
  branch when secondary filter state permits it, queues a segmented compact
  object, and renders until resource read `0x1f354 -> 0x1f1f0` requires
  firmware bytes `0x0c0000..0x0c0321`. Output effect: parser dispatch,
  payload count, filter choice, page-object queueing, bridge, and compact
  render dispatch are ROM-local documented through the segmented compact
  row-store route; the remaining pixel boundary is missing external
  resource-window data.

State grouping:

- Canonical parser state: command record `+2`, `0x78299e`, `0x782a1a`,
  `0x782a1c`, and saved record `0x782a20..0x782a25`.
- Canonical text/page state: `0x782f06`, `0x782eea + 0x10 * slot`,
  `0x782efa`, `0x783132`, `0x783133`, `0x782c8a`, page root `0x78297a`,
  page-root bucket `+0x1c`, short compact object fields
  `+0x04/+0x05/+0x06/+0x0a`, and downstream bridge/render roots consumed by
  `0xff1e`, `0x1ed84`, `0x1edc6`, `0x1ef6a`, and the compact row-store
  helpers.
- Derived/cache state: local filter word `A6-2`, routed value `D5`,
  selected-slot scale result from `0x332ee`, source scratch `0x782d7e`,
  compact coordinates, and render segment/bucket caches.
- Parser scratch: fetched payload bytes from `0xa904`, local countdown `D4`,
  and the local `0x1a` probe byte.
- Firmware bookkeeping: delayed restore through `0x121cc..0x1227e`, generic
  drain helpers `0x1228a` / `0x12328`, alternate/data redirect `0x12358`,
  append sink `0xe002`, and local normalization helper `0xd99a`.
- Hardware/external state: resource-window bytes after verified firmware
  suffix `0x0bfe22..0x0bffff`.
- Unknown: manual-facing names for selected filter/context fields and the
  physical decode for firmware range `0x0c0000..0x0c0321`.

Evidence:

- Parser and delayed-reader evidence:
  `generated/disasm/ic30_ic13_transparent_data_handler_011f5a.lst` and
  `generated/disasm/ic30_ic13_payload_dispatch_011f82.lst`.
- Payload loop and filter evidence:
  `generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst`,
  especially `0x12452..0x12534`.
- Page and render consumers: `0xd04a`, `0xd0f0`, `0xd550`, `0xd140`,
  `0xd3b2`, `0x12f2e`, `0x1387c`, `0xff1e`, `0x1ed84`, `0x1edc6`,
  `0x1ef6a`, `0x1efc2`, `0x1effe`, and the compact row-store helpers, with
  fixture names listed in this note's evidence block.
- Unresolved boundary: secondary segment-57 source bytes `0x0c0000..0x0c0321` are
  missing external resource-window data. This is not an unresolved parser, page-object,
  bridge, or compact-render dispatch edge. The global stop-point owner is
  [unresolved-boundaries.md](unresolved-boundaries.md#secondary-segment-57-resource-source),
  and the resource-byte owner is
  [resource-rom.md](resource-rom.md#continuation-decision-rule).

## Transparent Payload Decision Checkpoint

This checkpoint composes the `ESC &p#X` command family from parsed command to
visible output. It starts when the parser table selects arming handler
`0x11f5a` and ends with either fixed-space state, compact text page objects,
or the explicit secondary segment-57 resource boundary reached by compact
rendering.

Decision route:

- Parser dispatch: normal table mode `9` maps `ESC &p#X` / `x` to `0x11f5a`.
  The handler does not consume payload bytes; it stores delayed handler
  `0x12452` through `0x121cc`.
- Payload restore: terminal parser boundary `0x12218` restores saved command
  record `0x782a20..0x782a25` into the live record cursor `0x78299e` and calls
  `0x12452` when alternate/data flag `0x782c18` is clear.
- Alternate/data restore: if `0x782c18` is set at restore time,
  `0x1226e..0x1227e` redirects the saved count through `0x12358(0x1228a)`
  instead of calling `0x12452`. Because the saved handler is transparent
  reader `0x12452` rather than wrapper `0x1228a`, `0x12358` takes its
  non-wrapper branch: record word `+2 <= 0` returns without consuming data,
  while positive counts fetch normalized bytes through `0xdace` and append
  each byte through `0xe002`. This is stored macro/data-chain input, not
  immediate page output.
- Payload reader: `0x12452` reads absolute record word `+2`, then consumes
  that many bytes through `0xa904`. Local pair `0x1a 0x58` contributes
  `0x7f`; `0x1a xx` with `xx != 0x58` contributes the probe byte `xx`.
- Printable branch: payload values outside the filtered control ranges, or
  filtered controls with nonzero filter state, call `0xd04a`; text then flows
  through `0x1393a -> 0x12f2e -> 0x1387c` under page-root `+0x1c`. The short
  compact object contract is the ordinary text contract: `+0x04` is compact
  class, `+0x05` is context slot, `+0x06` is entry count, and payload entries
  from `+0x0a` hold glyph/coordinate pairs.
- Fixed-space branch: default-filtered C0 or `0x80..0x9f` values call
  `0xd0f0`. In flagged built-in contexts this advances spacing without a
  compact object; in unflagged fixed-record contexts the substituted host-space
  source can continue through `0xd140` / `0xd3b2` and queue a compact object.
- Render branch: any queued compact object publishes through `0xff1e`, bridges
  through `0x1ed84 -> 0x1edc6` by copying current-root bucket `+0x1c` to
  render-record `+0x18`, and renders through `0x1ef6a -> 0x1efc2 ->
  0x1effe` using the same compact renderer contracts and row-store helpers as
  ordinary printable bytes.

State classification:

- Canonical parser state: restored six-byte command record at `0x78299e`,
  delayed pending flag `0x782a1a`, handler pointer `0x782a1c`, and saved
  record `0x782a20..0x782a25`.
- Canonical text/page state: selected context slot `0x782f06`, filter bytes
  `0x782eea + 0x10 * slot` and `0x782efa`, high-character flags `0x783132` /
  `0x783133`, text cursor `0x782c8a`, page root `0x78297a`, page-root bucket
  `+0x1c`, short compact object fields `+0x04/+0x05/+0x06/+0x0a`, and render
  bucket `+0x18`.
- Derived/cache state: local selected filter word, normalized payload value,
  source object scratch `0x782d7e`, compact keys `0x782a7a..0x782a7e`, copied
  render bucket root `+0x18`, and compact render segment/bucket caches.
- Parser scratch: the fetched payload byte stream and the local `0x1a` probe
  state while `0x12452` is consuming the counted payload.
- Firmware bookkeeping: delayed-restore redirect through `0x1226e..0x1227e`,
  generic drain helpers `0x1228a` / `0x12328`, and local normalization helper
  `0xd99a`.
- Hardware/external state: firmware source range `0x0c0000..0x0c0321` for the
  documented secondary segment-57 fallback rows after compact rendering reaches
  beyond the verified resource suffix.
- Unknown: manual-facing names for the filter/high-character state fields and
  physical resource-window decode for `0x0c0000..0x0c0321`.

Writers, readers, and output effect:

- Writers are `0x11f5a` / `0x121cc` for delayed handler state, `0x12218` for
  restored parser records, `0x12452` for local payload normalization and
  routing, `0xd04a` / `0xd0f0` for text or fixed-space source state,
  `0x12f2e` / `0x1387c` for compact page objects, and `0x1edc6` for the
  render-record bucket copy.
- Readers and consumers are `0xa904` for payload bytes, `0x12452` for the
  restored count and filter fields, `0xd04a` / `0xd0f0` for text-state
  consumers, `0xff1e` / `0x1ed84` / `0x1edc6` for page publication and bridge,
  and `0x1ef6a` / `0x1effe` for compact rendering.
- The visible output is either no page object for drained alternate/data
  payloads, spacing-only motion for filtered built-in controls, compact text
  objects for printable or unflagged substituted-space paths, or the exact
  secondary segment-57 resource boundary when compact rendering requires bytes
  past `0x0bffff`.

Evidence and unresolved boundary:

- Parser and delayed-restore evidence is
  `generated/disasm/ic30_ic13_transparent_data_handler_011f5a.lst` and
  `generated/disasm/ic30_ic13_payload_dispatch_011f82.lst`.
- Payload reader evidence is `0x12452..0x12534` in
  `generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst`.
- Output-path evidence is the downstream text/page/render listings cited in
  this note plus fixtures `transparent data parser trace feeds page-record
  queue`, `transparent data control payloads advance through fixed-space
  path`, `transparent nonzero filters route controls through printable path`,
  and `transparent secondary high-control byte enters segmented page-record
  path`.
- No ROM-local middle edge remains for `0x11f5a -> 0x12452`, payload
  normalization, filter polarity, fixed-space versus printable routing,
  compact object queueing, or bridge/render dispatch. The remaining pixel
  boundary is only the physical/resource-window data for
  `0x0c0000..0x0c0321`.

### Transparent Payload To Visible Consumer Map

This map is the short route from a counted transparent byte to the first
state, page-object, or render consumer. It keeps the detailed decision
checkpoint above but makes the payload splice followable as a byte stream.

- Arming and restore:
  `ESC &p#X -> 0x11f5a -> 0x121cc` writes delayed-payload state
  `0x782a1a`, saved handler `0x782a1c = 0x12452`, and saved record
  `0x782a20..0x782a25`. Restore `0x12218` copies the record back to
  `0x78299e` and calls `0x12452` in normal parser mode. No payload byte is
  consumed and no page root, compact object, bridge field, or render input
  changes before this restore boundary.
- Alternate/data append:
  with alternate/data flag `0x782c18` set, restore redirects to
  `0x12358(0x1228a)`. Because saved handler `0x782a1c` is transparent reader
  `0x12452`, not wrapper `0x1228a`, positive counts are consumed through
  `0xdace` and appended through `0xe002`. The first visible consumer is a
  later macro/data-chain replay frame that returns those stored bytes through
  `0xa904`; this handler instance itself does not call `0x12452`, `0xd04a`,
  `0xd0f0`, `0x12f2e`, `0xff1e`, or a renderer.
- Payload byte normalization:
  `0x12452..0x12534` reads count word `+2`, fetches bytes through `0xa904`,
  and treats local pair `0x1a 0x58` as routed value `0x7f`. Pair `0x1a xx`
  with `xx != 0x58` routes `xx`. Helper `0xd99a` is firmware bookkeeping for
  the local `0x1a 0x58` case; it does not replace the later printable or
  fixed-space routing decision.
- Printable consumer:
  bytes outside the filtered control ranges, and filtered control bytes with
  nonzero filter state, call `0xd04a`. The first page-image consumer is the
  ordinary text path `0xd04a -> 0x1393a -> 0xd3b2/d824 -> 0x12f2e ->
  0x1387c`, which writes compact objects under page-root `+0x1c`. Publication
  and rendering then follow `0xff1e -> 0x1ed84 -> 0x1edc6 -> 0x1ef6a ->
  0x1efc2 -> 0x1effe` and the selected compact row-store helper.
- Fixed-space consumer:
  default-filtered C0 and high-control values call `0xd0f0`. In flagged
  built-in contexts, the visible effect is spacing/cursor movement without a
  compact glyph object. In unflagged fixed-record contexts, `0xd0f0 -> 0xd140
  -> 0xd3b2` can queue a substituted host-space compact object under the same
  page-root bucket `+0x1c` and render through the same compact row-store path.
- Secondary high-control boundary:
  after `SO` selects secondary context, high-control payload values can route
  through printable handling into segmented compact objects. The ROM-local
  consumer path is documented through `0xd04a`, `0x12f2e`, bridge, and compact
  dispatch; the exact pixel stop is external resource-window bytes
  `0x0c0000..0x0c0321` after verified suffix `0x0bfe22..0x0bffff`.
- State grouping:
  canonical parser state is the delayed record and handler fields
  `0x782a1a/0x782a1c/0x782a20..0x782a25`; canonical text/page state is
  selected slot `0x782f06`, filter bytes, current root `0x78297a`, compact
  bucket `+0x1c`, and compact object fields; derived/cache state is the
  selected filter word, normalized routed value, source scratch `0x782d7e`,
  compact coordinates, and copied render bucket roots; parser scratch is the
  fetched payload byte stream and local `0x1a` probe; firmware bookkeeping is
  delayed restore, `0xd99a`, `0x12358`, drain helpers, and append sink
  `0xe002`; hardware/external state is only the secondary segment-57 resource
  window.

## Command Boundary

`ESC &p#X` reaches handler `0x11f5a`. The handler is only an arming stub:

1. Push handler pointer `0x12452`.
2. Call the shared delayed-payload scheduler `0x121cc`.
3. Return.

The disassembly boundary is:

- `0x11f5a..0x11f6c`: push longword `0x00012452` and call `0x121cc`.
- `0x121cc..0x12210`: rewind `0x78299e` by six bytes, set pending byte
  `0x782a1a`, store the delayed handler longword at `0x782a1c`, and copy the
  six-byte command record into `0x782a20..0x782a25`.
- `0x12218..0x12264`: when pending byte `0x782a1a` is set, clear it, copy the
  saved six-byte record back to the live parser record at `0x78299e`, advance
  `0x78299e` by six, and call the saved handler through `jsr (A2)` if
  alternate/data flag `0x782c18` is clear.
- `0x1226e..0x1227e`: if alternate/data flag `0x782c18` is set at restore
  time, call `0x12358(0x1228a)` instead of directly calling `0x12452`, then
  clear the saved handler longword.

For `ESC &p2X`, the saved record is:

```text
80 58 00 02 00 00
```

The delayed snapshot stored by `0x121cc` is:

```text
01 00 01 24 52 80 58 00 02 00 00
```

That snapshot means: pending flag `1`, handler `0x00012452`, then the saved
six-byte command record.

## State Classification

Canonical fields:

- `0x78299e`: six-byte command-record cursor. `0x12452` rewinds it by six
  before reading the restored record.
- command record `+2`: signed byte count. `0x12452` takes the absolute value.
- `0x782f06`: selected font/context slot used to choose the payload control
  filtering state.

Derived/cache fields:

- `0x782eea + 0x10 * selected_slot`: selected-context C0 filter byte copied to
  `D3` after helper `0x332ee` scales the selected slot. At
  `0x124f8..0x1250a`, zero routes transparent C0 bytes through fixed-space
  helper `0xd0f0`; nonzero lets them fall through to printable handler
  `0xd04a`.
- `0x782efa`: fallback high-control filter byte used only when both
  high-character flags are clear. At `0x1250c..0x12528`, zero routes
  transparent `0x80..0x9f` bytes through `0xd0f0`; nonzero lets them fall
  through to `0xd04a`.
- `0x783132` and `0x783133`: primary and secondary high-character/symbol-set
  flags. Font activation writes them at `0x14d3a..0x14d7e`; `0x12496..0x124b8`
  uses them to choose the local high-control filter source, and printable path
  `0xd07c..0xd086` uses them when deciding whether high bytes are masked to
  seven bits before `0x1393a`.

Parser scratch:

- `0x782a1a`: delayed-payload pending flag.
- `0x782a1c`: delayed handler pointer.
- `0x782a20..0x782a25`: saved six-byte command record.

Firmware bookkeeping:

- local stack word at `A6-2`: the control-byte filtering word selected before
  the payload loop.
- `0xd99a`: payload-control side-effect helper for local `0x1a 0x58`.
  Listing `generated/disasm/ic30_ic13_payload_control_helper_00d99a.lst`
  shows that normal transparent mode is not one of the status-only cases: it
  can ensure root `0x78297a`, increment `0x782c72`, and publish through
  `0xf34a -> 0xff1e` when the counter exceeds `0xff`. Status-only cases are
  alternate/data mode or saved handlers `0x12cfe`, `0x1228a`, `0x15d0a`, and
  `0x16c14`.

Hardware/external state:

- Secondary segmented high-control fallback rows can require firmware reads
  beyond the verified resource-pair image. The exact boundary is
  `0x0c0000..0x0c0321`, reached by the `SO ESC &p3X ! 80 !` path after the
  compact renderer resolves glyph `0x5f`, segment `0x39`, and firmware source
  range `0x0bfe22..0x0c0321`. Bytes `0x0bfe22..0x0bffff` are verified in the
  `IC32,IC15` pair; bytes from `0x0c0000` onward require board/emulator
  memory-map evidence.

Unknown:

- Manual-facing HP names for the selected-context C0 filter byte at
  `0x782eea + 0x10 * slot`, fallback high-control filter byte `0x782efa`, and
  high-character flags `0x783132`/`0x783133`. Their ROM-local routing roles are
  documented above.

## High-Character Flag Producer/Consumer Checkpoint

The high-character flags are shared state between font/map activation,
transparent data, and the ordinary printable path. Their manual-facing names
remain external, but their ROM-local routing role is bounded by the writer and
consumer instructions below.

Writers:

- `0x14d28..0x14d64` handles one selected-font/map activation form. It reads
  selected record byte `+0x0c`; when that byte is zero it writes `0` to
  `0x783132` for the primary slot or `0x783133` for the secondary slot,
  depending on selected target word `0x7828de`. When record byte `+0x0c` is
  nonzero, it writes `1` to the same slot-specific flag. It then rebuilds the
  selected map through `0x14d9c`.
- `0x14d6c..0x14d86` handles the sibling selected-record form. It copies
  selected record byte `+0x0e` directly into primary flag `0x783132` or
  secondary flag `0x783133`, again selected by `0x7828de`, then rebuilds
  through `0x14e24`.
- Both paths finish through `0x14f16` and `0x1440c`, so the flag write is part
  of the same selected-font/map activation that later printable bytes consume.

Consumers:

- Transparent reader `0x12496..0x124b8` tests both `0x783132` and `0x783133`.
  If both are clear, it copies fallback high-control filter byte `0x782efa`
  into local word `A6-2`. If either flag is set, it copies the
  selected-context filter byte `D3`, derived from
  `0x782eea + 0x10 * selected_slot`, into `A6-2`.
- The transparent high-control routing test `0x1250c..0x12528` then uses
  `A6-2`: zero sends payload bytes `0x80..0x9f` through fixed-space handler
  `0xd0f0`; nonzero sends them to printable handler `0xd04a`.
- Printable entry `0xd07c..0xd0a8` uses the same flags for ordinary high
  bytes. When both flags are clear, high bytes are masked to seven bits and,
  in primary slot `0`, can switch to the secondary slot through `0xc6b8`
  before source construction. If either flag is set, the byte reaches
  `0x1393a` without that seven-bit mask/switch path.

Field classification:

- Canonical: primary/secondary high-character flags `0x783132` and
  `0x783133`, selected slot `0x782f06`, selected font context/map state, and
  later compact text objects created by `0xd04a` or fixed-space effects from
  `0xd0f0`.
- Derived/cache: selected-context filter byte `D3`, transparent-local
  high-control filter word `A6-2`, fallback byte `0x782efa`, and compact
  source-object fields written by `0x1393a`.
- Parser scratch: transparent payload count and restored command record while
  `0x12452` is active; ordinary printable high-byte handling has no delayed
  payload scratch.
- Firmware bookkeeping: selected-map rebuild state after `0x14d9c` /
  `0x14e24`, map patching through `0x14f16`, source-object scratch
  `0x782d7e`, and page-root allocation/publication state if later text objects
  are queued.
- Hardware/external: none for this ROM-local routing decision.
- Unknown: only the manual-facing names of the selected-record bytes and flags
  remain unknown. Their ROM-local effects on transparent routing and ordinary
  printable high-byte handling are the branch decisions above.

Output effect:

- The flags do not draw by themselves. They choose whether high-control
  transparent/display bytes take fixed-space handling or printable handling,
  and whether ordinary high bytes are masked/switch selected slot before
  source construction.
- Visible output appears only after `0xd04a` queues compact text through
  `0x12f2e -> 0x1387c` or after `0xd0f0` advances/substitutes fixed-space
  state; publication and rendering still proceed through `0xff1e`,
  `0x1ed84`, `0x1edc6`, `0x1ef6a`, compact dispatch, and the selected
  row-store helper.

Evidence:

- Writer listing:
  `generated/disasm/ic30_ic13_active_object_dispatch_014ba4.lst` at
  `0x14d28..0x14d86`.
- Transparent consumer listing:
  `generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst` at
  `0x12496..0x12528`.
- Printable consumer listing:
  `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst` at
  `0xd07c..0xd0a8`.
- Visible-output checks are the transparent high-control fixtures named in
  the owner summary and the selected-font/high-byte checks named in
  [font-context-metrics.md](font-context-metrics.md).

## Payload Reader At 0x12452

`0x12452` is a counted reader. It does not use `0xdace`. It calls `0xa904`
directly and implements its own handling for the `0x1a 0x58` host-control pair.

Setup behavior:

- `0x1245a..0x12462`: reopen the restored six-byte command record by rewinding
  `0x78299e` by six bytes.
- `0x12468..0x12476`: read signed record word `+2`, sign-extend it, and
  convert negative counts to their absolute value in `D4`.
- `0x12476..0x12494`: read selected context slot `0x782f06`, scale it through
  `0x332ee(0x10)`, and copy context byte `0x782eea + scaled_slot` into `D3`.
- `0x12496..0x124b8`: if both high-character flags `0x783132` and `0x783133`
  are clear, copy fallback byte `0x782efa` into local word `A6-2`; otherwise
  copy selected context byte `D3` into `A6-2`.

Loop behavior:

- `0x124b8..0x124c2`: if count `D4 <= 0`, return; otherwise fetch one byte
  through `0xa904` and copy `D7` to `D5`.
- `0x124c4..0x124e8`: if `D5` is `0x1a`, fetch a second byte through
  `0xa904`. A second byte of `0x58` calls `0xd99a` and replaces the routed
  payload value with `0x7f`; any other second byte becomes the routed payload
  value. The original `0x1a` is consumed by the probe.
- `0x124e8..0x124f6`: if the routed value is `-1`, return early.
- `0x124f8..0x12532`: route the value through the control/high-control filter
  matrix documented below.
- `0x12532..0x12534`: decrement `D4` once for each routed payload value and
  loop back to `0x124b8`.

The control probe matters for reproduction. A byte stream containing `1a 58`
contributes one transparent payload value, `0x7f`, while consuming two host
bytes. A byte stream containing `1a 41` contributes `0x41`, not `0x1a`.

## Payload Routing

After normalization, `0x12452` chooses between fixed-space/control handling and
printable text handling:

- `0x124f8..0x1250a`: values `0x00..0x1f` call `0xd0f0` only when selected
  context byte `D3` is zero. If `D3` is nonzero, they fall through toward
  `0xd04a`.
- `0x1250c..0x12528`: values `0x80..0x9f` call `0xd0f0` only when local
  filtering word `A6-2` is zero. If `A6-2` is nonzero, they fall through to
  `0xd04a`.
- `0x1252a..0x1252c`: all other values, plus filtered C0/high-control values,
  are passed to `0xd04a` as the printable payload byte.

`0xd0f0` is the same fixed-space source-object path used by direct text
handling. Disassembly `0xd0f0..0xd124` calls `0x1393a(0x20, 0x782d7e)`. In the
flagged built-in branch it then clears source longword `+4` before entering
`0xd550`, so the `0xd62e..0xd644` test sees no glyph pointer, skips page-root
allocation and `0xd824` queueing, and advances the cursor as spacing. `0xd04a`
is the normal printable text path into character mapping, cursor placement,
compact text object creation, page-record storage, bridge, and render dispatch.
When `0x1393a(0x20)` returns an unflagged inline/fixed-record source, the same
`0xd0f0` entry continues through `0xd140` and `0xd3b2`, so the substituted
space can queue a normal unflagged compact text object.

## Byte-Stream Branch Examples

The isolated transparent reader fixture uses saved record:

```text
80 58 00 05 00 00
```

and payload bytes:

```text
41 1a 58 05 85 42
```

The ROM-modeled result is:

- byte count: `5`
- selected context byte: `0`
- local filtering word: `0`
- consumed values: `41 7f 05 85 42`
- routes: `d04a d04a d0f0 d0f0 d04a`
- control hits: `1`

A second isolated reader fixture uses saved record `80 58 00 02 00 00` and
payload bytes `1a 41 21`. It consumes three host bytes for two transparent
payload values:

- byte count: `2`
- consumed values: `41 21`
- routes: `d04a d04a`
- control hits: `0`

This pins disassembly `0x124cc..0x124e8`: when the byte after `0x1a` is not
`0x58`, that second byte is the routed payload value. The original `0x1a` is
only the probe prefix.

The visible-output fixture uses stream:

```text
1b 26 70 32 58 21 21
```

That is `ESC &p2X!!`. The parser trace has one command event:

- handler: `0x11f5a`
- final mode: `0`
- restored handler: `0x12452`
- restored record: `80 58 00 02 00 00`
- raw payload: `21 21`
- routes: `d04a d04a`

The two payload bytes queue as normal printable text:

- first payload byte `0x21`: cursor before `pack12(10)`, compact coord `0x0001`
- second payload byte `0x21`: compact coord `0x0202`
- page-record root allocation count: `1`
- page-record bridge: `0x1edc6` copies the selected context slot
- render entry: the bridged rows use the same ROM-derived path as plain `!!`

The visible probe fixture uses stream:

```text
1b 26 70 32 58 1a 41 21
```

That is `ESC &p2X\x1aA!`. The restored record count is `2`, but the raw payload
slice is `1a 41 21` because the non-`0x58` probe consumes both `1a` and `41`
for one routed payload value. The queued values are `41 21`; byte `0x41` maps
to glyph `0x40`, queues compact coord `0x0a00`, and renders visible `A` before
the following `!` at compact coord `0x0202`.

The control-payload page-record fixture uses stream:

```text
1b 26 70 34 58 21 05 85 21
```

That is `ESC &p4X!\x05\x85!` under the default zero filtering state. It
exercises one command that mixes both transparent routing exits:

- restored record: `80 58 00 04 00 00`
- raw payload: `21 05 85 21`
- values: `21 05 85 21`
- routes: `d04a d0f0 d0f0 d04a`
- first printable payload byte `0x21`: queues compact coord `0x0001`
- C0 payload byte `0x05`: maps fixed-space host byte `0x20` to glyph `0x1f`,
  clears the glyph pointer from `0x0146b4` to `0`, advances cursor from
  `pack12(28)` to `pack12(46)`, and queues no page-record text object
- high-control payload byte `0x85`: repeats the same fixed-space route,
  advances cursor from `pack12(46)` to `pack12(64)`, and queues no page-record
  text object
- final printable payload byte `0x21`: queues compact coord `0x0604`
- page-record object prefix: `00 00 00 00 00 00 00 02 20 00 01 20 06 04`
- final cursor x: `pack12(82)`
- render entry: the bridged rows contain only the two visible `!` glyphs,
  separated by the two fixed-space advances

The unflagged fixed-record fixture uses stream:

```text
1b 26 70 33 58 21 05 21
```

That is `ESC &p3X!\x05!` under the default zero filtering state, but with an
inline/fixed-record font context where both host space and `!` are valid
unflagged records. It exercises the `0xd0f0` entry that continues past
cursor-only spacing for this source class:

- restored record: `80 58 00 03 00 00`
- raw payload: `21 05 21`
- selected context byte: `0`
- local filtering word: `0`
- values: `21 05 21`
- routes: `d04a d0f0 d04a`
- first `!`: unflagged source host `0x21`, mapped glyph `1`, inline record
  `02 03 04 00 00 00 00 80`, positioned x/y `22/23`, compact coord `0x7601`
- C0 payload byte `0x05`: routes through `0xd0f0`, substitutes host byte
  `0x20`, reads unflagged inline record `01 02 00 00 00 00 00 70`, maps glyph
  `0`, positions x/y `40/20`, queues compact coord `0x4802`, and reuses bucket
  `1`
- final `!`: queues unflagged glyph `1` at compact coord `0x7a03`
- bucket `1` object:
  `00 00 00 00 00 00 00 03 01 76 01 00 48 02 01 7a 03` plus trailing zeros
- bridge context slots begin `(0x00000100, 0, 0, 0)`
- selected bucket render: row count `10`, row width `74`, digest
  `89629435e063529ce7150d603ed9be37a74658317db3e97a4ae01b1c8d64f9d9`
- final cursor x: `pack12(64)`

The nonzero-filter fixture uses stream:

```text
1b 26 70 34 58 21 05 80 21
```

That is `ESC &p4X!\x05\x80!` with selected context byte `1` and local
filtering word `1`. It exercises the other side of both filter branches:

- restored record: `80 58 00 04 00 00`
- raw payload: `21 05 80 21`
- selected context byte: `1`
- local filtering word: `1`
- values: `21 05 80 21`
- routes: `d04a d04a d04a d04a`
- C0 payload byte `0x05`: maps through `0xd04a` to glyph `0x04`, glyph entry
  `0x0186c6`, and compact coord `0x0d01`
- high-control payload byte `0x80`: maps through `0xd04a` to glyph `0x7f`,
  glyph entry `0x016aca`, and compact coord `0x0003`
- page-record object prefix:
  `00 00 00 00 00 00 00 04 20 00 01 04 0d 01 7f 00 03 20 06 04`
- final cursor x: `pack12(82)`
- render entry: all four routed payload values contribute compact text entries
  and visible rows

The high-control nonzero-filter fixture uses stream:

```text
1b 26 70 33 58 21 98 21
```

That is `ESC &p3X!\x98!` with selected context byte `1` and local filtering
word `1`. It keeps the high-control byte on the `0xd04a` printable path and
records a taller high-control glyph in a different bucket from surrounding
printable bytes:

- restored record: `80 58 00 03 00 00`
- raw payload: `21 98 21`
- selected context byte: `1`
- local filtering word: `1`
- values: `21 98 21`
- routes: `d04a d04a d04a`
- payload byte `0x98`: maps to glyph `0x97`, glyph entry `0x01781e`, rows
  `29`, width `17`, positioned x/y `29/-1`, compact coord `0xfd01`, and bucket
  `-1`
- surrounding `!` bytes remain in bucket `0` at compact coords `0x0001` and
  `0x0403`
- bucket `-1` object:
  `00 00 00 00 00 00 00 01 97 fd 01` plus trailing zeros
- bucket `0` object:
  `00 00 00 00 00 00 00 02 20 00 01 20 04 03` plus trailing zeros
- selected high-control bucket render: row count `44`, row width `46`, digest
  `bd7ad3016d15c1dc2ef12adaeb1091a58f26473c0ecfc7ac13bfaf268c383e90`
- surrounding printable bucket render: row count `22`, row width `56`, digest
  `4bf2f0104b14bfa598b8acfcf8cfb69ccb4419c234f02f256781b6b236110300`

The upper-bound high-control fixture uses stream:

```text
1b 26 70 33 58 21 9f 21
```

That is `ESC &p3X!\x9f!` with selected context byte `1` and local filtering
word `1`. It exercises the top value in the filtered `0x80..0x9f` range on the
same printable route as `0x98`, while selecting a different glyph:

- restored record: `80 58 00 03 00 00`
- raw payload: `21 9f 21`
- values: `21 9f 21`
- routes: `d04a d04a d04a`
- payload byte `0x9f`: maps to glyph `0x9e`, glyph entry `0x016d1e`, rows
  `30`, width `15`, positioned x/y `30/-2`, compact coord `0xee01`, and
  bucket `-1`
- surrounding `!` bytes remain in bucket `0` at compact coords `0x0001` and
  `0x0403`
- selected high-control bucket render: row count `44`, row width `45`, digest
  `ec0f944207561c1b9c9139749c3e37d122aebf53e2a50849dd8703416545c719`
- surrounding printable bucket render matches the `0x98` fixture digest
  `4bf2f0104b14bfa598b8acfcf8cfb69ccb4419c234f02f256781b6b236110300`

The interior high-control sample fixture drives `ESC &p3X!#!` for payload
bytes `0x81`, `0x88`, `0x90`, and `0x97` with the same selected context byte
`1` and local filtering word `1`. All four samples route
`d04a d04a d04a`; their payload bytes map to glyphs `0x80`, `0x87`,
`0x8f`, and `0x96`, queue the high-control glyph in bucket `-1`, keep the
surrounding `!` bytes in bucket `0`, and render selected-bucket digests
`841384c82ec301334f603178a4ad28152c7818bab08c8b829bb769a356b27c04`,
`64ab78cb858eb0560f08304101c4a6870daee5a94144ce028e5807952d479850`,
`e99bffbc8e6c0c9179536c5c90927a72ba3047cf7f43e43355552f0e5aa4fae4`, and
`a97b85527284735826a97ef1998d72e5841bd4331c2f2aeea24d444a35179acd`.

The secondary high-control fixture uses stream:

```text
0e 1b 26 70 33 58 21 80 21
```

That is `SO ESC &p3X!\x80!`. It composes the text-map selector with the same
transparent payload path:

- SO reaches handler `0xc6b8`, calls the modeled `0xc428(1)` install success
  path, and changes selector `0x782f06` from `0` to `1`.
- restored record: `80 58 00 03 00 00`
- raw payload: `21 80 21`
- selected context byte: `1`
- local filtering word: `1`
- values: `21 80 21`
- routes: `d04a d04a d04a`
- both `!` payload bytes read source context `0xc00ae122`, source slot `1`,
  map to glyph `0`, and queue short selector-1 entries at compact coords
  `0xc5ff` and `0xc901`
- high-control payload byte `0x80` reads the same secondary source context and
  source slot, maps to glyph `0x5f`, reports glyph entry `0x02e122`, rows
  `20062`, width `74`, and compact coord `0x1c01`
- the high-control byte enters the segmented page-record path with selector
  `0x2001`, `157` segment objects, first segment/bucket `156`/`1248`, and last
  segment/bucket `0`/`0`
- bridged context slots are `(0x440946b4, 0xc00ae122)`
- selected bucket `0` object prefix:
  `00 00 00 00 20 01 00 01 5f 00 1c 01 00 00 00 00`
- selected bucket render: row count `80`, row width `256`, digest
  `57bb3fd895be358ff325e26ae58a3b0dc526c5b08b382eb90e7273e6227fbfbb`
- final selector remains `1`; final cursor x is `pack12(64)`

The secondary segmented render-prefix fixture renders the produced buckets
until the current source model reaches a concrete bitmap-source boundary:

- renderable prefix: buckets `0..448`, `57` buckets, aggregate digest
  `292eafb8b558bd36ca0caa5caa2771976c0e611456ac0b610ec8916b9d1f03f9`
- sample bucket `0`: object count `2`, segment `0`, row count `80`, row width
  `256`, digest
  `57bb3fd895be358ff325e26ae58a3b0dc526c5b08b382eb90e7273e6227fbfbb`
- sample bucket `448`: segment `56`, row count `32`, row width `102`, digest
  `823854dc77b9234cf90f71bebcc3da7280c72dfed2bf05315e757b2d1c58c4e3`
- first failure: bucket `456`, selector `0x2001`, glyph `0x5f`, segment
  `0x39`, row skip `7296`, source `0x03fe22`, needing `1280` bytes with
  `478` available
- resolved glyph source: entry/bitmap `0x02e122`, delta `0`, mode `0`, rows
  `20062`, width `74`, render span `10`

The segment-57 failure is no longer an unresolved compact-renderer arithmetic
edge. Disassembly
`generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst` shows
`0x1f354` taking the bit-30 offset-table form, adding the selected table entry
without checking for zero, then reading row count, width, mode, and bitmap delta
from the resulting entry. For the secondary `LINE_PRINTER` table, index `0x5f`
has relative offset `0`, so firmware resolves the glyph entry to the record
header at file offset `0x02e122`. Segmented renderer `0x1f1f0` then computes
`segment << 7`, subtracts that row skip from the row count, clamps the remaining
rows to `0x80`, multiplies by even byte span `10`, and advances `A2` to file
offset `0x03fe22`.

The unresolved edge is therefore the physical/resource-window source supplied
for the read crossing the verified `IC32,IC15` pair boundary. The built-in
resource window maps file offset `N` to firmware address `0x080000 + N`, so the
computed read starts at firmware address `0x0bfe22`. It needs bytes
`0x0bfe22..0x0c0321`; only `0x0bfe22..0x0bffff` are inside the verified
`0x40000`-byte resource-pair image. Firmware startup notes show scanner `0x41a`
walking resource records through `0x0ae122` and terminating at `0x0b2f80`
before the next `0x40000` probe. The same startup notes bound byte-sum
self-test coverage to `0x080000..0x0bffff` for the resource pair, so the
checksum proves the verified suffix but does not validate or reject the
continuation bytes starting at `0x0c0000`. The mirror-scanner fixture below now
exercises the scanner-visible result of a simple full mirror, but startup notes
still do not prove whether the physical decode hides that mirror from scanner
reads, zero-fills, exposes program ROM, or maps another source at
`0x0c0000..0x0c0321`.

Fixture `transparent secondary segment-57 continuation policies diverge after
verified bytes` now makes the boundary policy-dependent rather than vaguely
unknown. Rendering the bucket-456 compact payload `00 01 5f 39 1c 01` with
three explicit continuation policies records that the first current-band rows
are already fixed by verified bytes: mirror, code-pair continuation, and
zero-fill all produce current-band digest
`f0c1127f9e6b203f9829ab43f159b89c3f7dda687a47d4c09971077eac55c96e`. The
fixture also pins the exact byte-source boundary: the read window is
`0x0bfe22..0x0c0321`, the verified suffix is `478` bytes with digest
`e0a0fd34ce7a39f79ecd27c0ee288631554a0ff78359b72e27ea6087651bcf1f`, and the
remaining `802` bytes after firmware address `0x0c0000` only affect fallback
rows. The candidate continuation sources hash differently: mirror
`e435e3b9d033e491b57282a88b0f321aa5fecae8128fa060844cc01379349563`,
code-pair
`90934acf59d9e8519c9149dc5df228f8fec2bff8451427be265489be967cdd16`, and
zero-fill
`359f38eef400e2fa3924a3258652e74ee19cd46cb92e47bce91f1194fce25e9e`. The
fallback rows diverge there: mirror digest
`75cc8b60cd33f5c659ad702530ebacdc7685f2b75d63e18b9ce055383153f142`,
code-pair digest
`dc58960aff83e718df147897de51944939626c4e8422a53da5443bca48a53df5`, and
zero-fill digest
`6373cecdf5f20d78b01abe5aa65c051d82ddef345b7cf7fe1504f93c9cb2c425`.

The state class for that remaining edge is physical ROM decode, not transparent
parser state. `data/rom_manifest.json` proves the verified local image contains
only the four installed 128K x 8 ROM packages, with `IC32,IC15` providing the
`0x40000`-byte resource pair that ends at firmware address `0x0bffff`.
`notes/formatter-interface-pca.md` separately records that the formatter ROM
capacity can be 1 MB and that the address-controller gate array can alter ROM
address regions through jumpers. Those hardware facts explain why the fixture
keeps mirror, code-pair continuation, and zero-fill as named hypotheses instead
of choosing one from disassembly alone. The mirror hypothesis is now constrained
by fixture `0x41a HEAD scanner would duplicate records under simple resource
mirror`: a full `IC32,IC15` mirror at `0x0c0000` would make scanner `0x41a`
walk a second `HEAD` chain and `48` typed records, and `0x1a2e4` sets
candidate-scan bounds through `0x0ffffe`. The exact unresolved boundary is
`0x0c0000..0x0c0321`: closing it requires a static board, emulator, or
gate-array memory-map explanation. The ROM/disassembly evidence can name the
candidate continuations and their consequences, but it cannot choose which
byte source the formatter address bus sees at `0x0c0000`.
Fixture `0x41a HEAD scanner rejects non-HEAD 0x40000 continuations` constrains
the other two continuation hypotheses at the same scanner boundary:
code-pair-after-resource presents marker `0x00800000` at probe offset
`0x40000`, while zero-fill-after-resource presents marker `0x00000000`. Both
variants keep one `HEAD` chain, walk the same `24` typed records as the
verified `IC32,IC15` image, and continue to final probe `0x80000`. Therefore
mirror is the only modeled local continuation that would change startup
candidate discovery unless hardware hides it from scanner reads; code-pair and
zero-fill remain possible physical decode policies for the fallback rows, not
additional resource records.

`0x1a2e4` / `0x1a616` make the built-in side of that boundary exact: built-in
resource discovery starts at `0x080000`, ends at `0x0ffffe`, and scans in
`0x40000` steps. Optional cartridge/resource scans are separate windows selected
by `$8000.14` / `$8000.15`, using `0x200000..0x3ffffe` and
`0x400000..0x5ffffe`; the cartridge boot probe at `0x003e8` likewise looks for
`PROG` at `0x200000` or `0x400000` after testing `$8000.6` / `$8000.7`. Those
paths do not supply a ROM-only answer for `0x0c0000`; they instead prove that
the segment-57 read falls inside the built-in resource scan range but beyond
the verified `IC32,IC15` pair.

## Reproduction Contract

A byte-stream renderer must not treat transparent data as an opaque binary skip.
For `ESC &p#X`:

- Parse and save the six-byte `X` command record through the shared
  `0x121cc`/`0x12218` delayed-payload mechanism.
- In normal parser mode, call delayed handler `0x12452`, use the absolute value
  of record word `+2` as the transparent payload count, consume payload bytes
  through the same priority byte source as `0xa904`, preserve the local
  `1a 58 -> 7f` behavior in `0x12452`, and route each normalized payload value
  through `0xd0f0` or `0xd04a` according to the control-byte filtering rules
  above.
- In alternate/data mode, do not call `0x12452`: route the restored record
  through `0x12358(0x1228a)`. For transparent data, the saved handler
  `0x12452` differs from wrapper `0x1228a`, so positive record counts consume
  bytes through `0xdace` and append each normalized byte through `0xe002`;
  nonpositive counts return without consuming payload. This branch creates no
  page root, page object, bridge record, render dispatch, or pixels unless the
  appended bytes are replayed later.
- On the normal `0x12452` branch, let printable transparent bytes update
  cursor, page-record text objects, and rendered rows exactly like normal
  printable host bytes.
- On the normal `0x12452` branch, let default-filtered C0 and `0x80..0x9f`
  bytes advance spacing through `0xd0f0` without appending compact text entries
  in the flagged built-in path.
- On the normal `0x12452` branch, let default-filtered C0 and `0x80..0x9f`
  bytes also queue substituted host space if the current source class is an
  unflagged fixed-record font with a valid space record.
- On the normal `0x12452` branch, let nonzero-filtered C0 and `0x80..0x9f`
  bytes enter `0xd04a` and emit normal mapped text entries.
- On the normal `0x12452` branch, treat `1a xx` with `xx != 58` as routed
  payload byte `xx`, not `1a`.
- For the secondary `SO ESC &p3X ! 80 !` segmented high-control path, preserve
  the page-record and renderer state through glyph `0x5f`, segment `0x39`,
  source `0x0bfe22`, and read window `0x0bfe22..0x0c0321`. Rows backed by
  verified bytes `0x0bfe22..0x0bffff` are ROM-derived; fallback rows that need
  bytes at `0x0c0000..0x0c0321` must stop at the physical/resource-window
  decode boundary unless a board/emulator memory map supplies those bytes. The
  canonical unresolved-boundary entry is
  [Secondary Segment-57 Resource
  Source](unresolved-boundaries.md#secondary-segment-57-resource-source).

## Remaining Edges

- The visible-output fixtures now cover printable payload bytes, default-zero
  filtering for C0 and `0x80..0x9f`, the unflagged fixed-record `0xd0f0`
  branch, nonzero filtering for one C0/high-control pair, a primary tall
  high-control bucket plus the top-of-range `0x9f` high-control glyph, a
  secondary segmented high-control page-record path, and the `1a` non-`0x58`
  probe case.
- The default-filtered fixed-space route is page-visible for the flagged
  built-in branch, where `0xd0f0` clears source `+4`, enters `0xd550`, advances
  spacing, and queues no compact text object. It is also page-visible for the
  unflagged/fixed-record branch, where `0xd0f0` calls
  `0x1393a(0x20, 0x782d7e)`, enters `0xd140` / `0xd3b2`, queues substituted
  host-space glyph `0`, and renders the selected bucket digest
  `89629435e063529ce7150d603ed9be37a74658317db3e97a4ae01b1c8d64f9d9`.
- Broader nonzero-filtering examples now include primary high-control samples
  `0x81`, `0x88`, `0x90`, and `0x97`, plus the tall primary bucket-crossing
  cases `ESC &p3X!\x98!` and `ESC &p3X!\x9f!`. The secondary segmented
  mapping has a page-record boundary and renderable prefix. The remaining risk
  is the segment-57 fallback-row source interpretation named above; the
  current-band rows are already pinned across mirror, code-pair, and zero-fill
  continuation policies, and the startup scanner consequence is pinned for all
  three policies.
- Manual-facing names for the active context filtering byte, fallback byte, and
  high-character flags remain unknown. Their ROM-local writer/consumer contract
  is documented in `High-Character Flag Producer/Consumer Checkpoint` above.
