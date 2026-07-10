# Built-In Resource Scan And Candidate Windows

This note documents the firmware path that turns the `IC32,IC15`
resource ROM into selectable built-in font candidates. The byte-level
record and bitmap ledger remains in
[resource-rom.md](resource-rom.md#resource-rom-outcome-matrix); this file
records the state contract used by font selection and visible text output.

## Owner Summary

This note owns the ROM path that turns the `IC32,IC15` built-in resource image
into selectable font candidates. The resource scan does not parse PCL and does
not draw pixels directly. It builds candidate windows and records the selected
resource fields that font-selection handlers later consume before printable
bytes resolve glyph rows.

Primary routes:

- Resource verification:
  startup scanner `0x41a` verifies the `HEAD` chain and executable-record
  behavior for the built-in resource image.
- Candidate scan:
  `0x1a2e4` seeds built-in scan bounds `0x080000..0x0ffffe`; `0x1a616` walks
  resource records, classifies signatures through `0x1b9c0`, and passes
  accepted font records to `0x1a9be`.
- Candidate partition:
  `0x1a9be` writes candidate pointers under `0x782324`, increments accepted
  count `0x78278e`, partitions records into class/range counters
  `0x782790..0x78279e`, and advances window cursors `0x7827a0..0x7827b4`.
- Selection consumers:
  `0x1569c` activates a class window, `0x156de` filters by requested,
  remembered, or fallback symbol word, `0x1519a` filters by height, `0x153c6`
  filters by spacing/pitch, and `0x14398` chooses selected slot `0x7828a8`.
- Font/render handoff:
  selected candidate state feeds `0x144d2`, `0x14c64`, `0xc428`,
  `0x1393a`, compact queueing, and compact glyph renderers. Glyph table and
  bitmap bytes remain canonical resource data owned by the dumped resource
  image and decoded in the resource reports.

Field groups:

- Canonical resource data:
  `HEAD` records, named `COURIER` and `LINE_PRINTER` font records, record
  bytes `+0x0c/+0x0d/+0x20/+0x21/+0x22/+0x24/+0x28/+0x2a/+0x2f..+0x31`,
  glyph table entries, and bitmap payload rows.
- Canonical candidate state:
  candidate pointer list `0x782324`, total count `0x78278e`, class/range
  counters `0x782790..0x78279e`, window cursors `0x7827a0..0x7827b4`, scan
  cursor `0x782884`, scan bounds `0x78288c` / `0x782890`, active list pointer
  `0x78287c`, active count `0x7827b8`, and selected slot `0x7828a8`.
- Derived/cache state:
  verified built-in counters and cursors, active class-zero or class-one
  pointer/count from `0x1569c`, high-bit candidate marks, and selected context
  longwords consumed by font-context refresh.
- Parser scratch:
  font request fields and symbol words are parser-produced inputs to
  selection; they are not produced by the resource scan.
- Firmware bookkeeping:
  startup scanner state, resource signature classifier `0x1b9c0`, candidate
  insert/delete helpers `0x1bc38` / `0x1bd2e`, continuation policy probes, and
  optional-window scanner behavior shared with the page/font scheduler.
- Hardware/external state:
  cartridge or external resource windows outside the verified built-in image,
  plus the physical decode source after verified address `0x0bffff`.
- Unknown:
  the exact continuation/decode source at `0x0c0000..0x0c0321`, external
  cartridge contents, and manual-facing names for some resource-record fields.
  The ROM-local scan, partition, filter, chooser, and glyph-consumer addresses
  are documented.

Output effect:

- The scan changes future pixels only by changing which candidate context and
  glyph payload later font selection and printable bytes consume.
- It does not queue compact objects, publish pages, schedule render work, or
  write bitmap rows.
- A byte-stream renderer must preserve the candidate windows, selected context
  selection, glyph table entry interpretation, and explicit physical resource
  continuation boundary.

## Evidence

Primary disassembly:

- `generated/disasm/ic30_ic13_font_resource_scan_01a2e4.lst`
- `generated/disasm/ic30_ic13_font_candidate_classify_01a9be.lst`
- `generated/disasm/ic30_ic13_font_candidate_activate_01569c.lst`
- `generated/disasm/ic30_ic13_font_candidate_filters_01519a.lst`
- `generated/disasm/ic30_ic13_object_compare_013a48.lst`
- `generated/disasm/ic30_ic13_active_object_scan_014398.lst`
- `generated/disasm/ic30_ic13_font_candidate_object_alloc_01bc38.lst`
- `generated/disasm/ic30_ic13_font_resource_object_lookup_01b4c0.lst`

Primary generated reports:

- `generated/analysis/ic32_ic15_header.txt`
- `generated/analysis/ic32_ic15_resource_markers.txt`
- `generated/analysis/ic32_ic15_strings.txt`
- `generated/analysis/ic32_ic15_font_records.md`
- `generated/analysis/ic32_ic15_resource_glyph_probe.md`
- `generated/analysis/ic32_ic15_builtin_glyph_payloads.md`

Primary fixtures:

- `0x41a HEAD scanner walks verified IC32/IC15 resource chain`
- `0x41a HEAD scanner advances next probe after 0x40000 boundary`
- `0x41a HEAD scanner handles 0xbe executable records`
- `0x1a9be scanned font candidate list partitioning`
- `actual IC32/IC15 built-in records feed 0x1a9be partitions`
- `0x1a616 candidate scan continuation policy changes built-in counts`
- `0x1569c activates concrete built-in candidate windows`
- `0x156de filters concrete active candidate windows`
- `0x1519a filters concrete active candidates by height`
- `0x153c6 filters concrete active candidates by spacing and pitch`
- `0x14398 chooses concrete active built-in candidate`
- `0x1bc38-modeled candidate insertion branches`
- `named COURIER and LINE_PRINTER records expose deterministic metadata`
- `named built-in records expose firmware selection fields`
- `named built-in first glyphs expose positioning offsets`
- `firmware-scanned built-in glyph coverage summary`
- `firmware-scanned tall built-in glyph target summary`
- `resource glyph row-copy span matrix matches direct decode`

## Resource Scan Model

The `IC32,IC15` resource ROM does not directly produce pixels. Startup
scanner `0x41a` verifies the `HEAD` record chain and executable-record
behavior. Font-resource scanner `0x1a616`, initialized by `0x1a2e4`,
then walks the built-in resource window and passes accepted font records
to classifier `0x1a9be`.

The verified built-in chain contains 24 typed records from firmware
address `0x08004c` through `0x0ae122`, terminating at `0x0b2f80`.
Classifier `0x1a9be` partitions accepted records into the candidate
pointer list at `0x782324`. The verified built-ins produce 24 total
candidates: 12 class-one low-window entries and 12 class-zero low-window
entries.

The generated resource header and string reports are supporting ROM
evidence for that scan, not a separate parser path. File offset `0x000000`
contains `HEAD`, which maps to firmware address `0x080000`; the first
resource string at offset `0x00001f` is the HP copyright text. The marker
index finds structured `COURIER` records at offsets `0x000410`,
`0x000860`, `0x000cb0`, `0x00a374`, `0x00a7c4`, `0x00ac14`,
`0x01a0dc`, `0x01a52c`, `0x01a97c`, `0x023848`, `0x023c98`, and
`0x0240e8`; it finds structured `LINE_PRINTER` records at offsets
`0x0146a8`, `0x014afc`, `0x014f50`, `0x02d86e`, `0x02dcc2`, and
`0x02e116`. Those offsets correspond to firmware resource addresses by
adding `0x080000`, and they are the named-record subset later decoded by
the font-record and glyph-probe reports. The interleaved tail string at
file offset `0x03ffe0`, `SSHH77--99223334--0011`, remains dump identity
evidence for the IC32/IC15 pair, not a firmware-scanned resource record.

The scan output is a set of candidate windows, not a selected font.
Activator `0x1569c` chooses a class-specific active window from those
lists. Filters `0x156de`, `0x1519a`, and `0x153c6` then reduce the
active list by symbol set, height, spacing, and pitch. Chooser `0x14398`
selects the final slot at `0x7828a8`. The selected context longword
then feeds the established font/render path through `0xc428`,
`0x1393a`, `0xd824`, `0x12f2e`, and compact glyph renderers.

## Resource Scan Outcome Matrix

This matrix records the ROM outcomes that matter to a byte-stream
renderer. The resource scanner itself is not a PCL parser, but the
candidate windows it builds are later consumed by parsed font-selection
commands and printable bytes.

Built-in scan seed:

- ROM path:
  `0x1a2e4`.
- State category:
  canonical candidate state and firmware bookkeeping.
- Writers:
  clears `0x78278e` and `0x782790..0x78279e`; seeds
  `0x7827a0..0x7827b4` to `0x782324`; writes bounds
  `0x78288c = 0x080000`, `0x782890 = 0x0ffffe`, and stride
  `0x782888 = 0x40000`.
- Readers / consumers:
  `0x1a616` consumes the bounds and cursor state.
- Output effect:
  no pixels yet; the outcome chooses which resource records can become
  future glyph sources.
- Evidence:
  `generated/disasm/ic30_ic13_font_resource_scan_01a2e4.lst` at
  `0x1a2e4..0x1a39a`; fixture
  `actual IC32/IC15 built-in records feed 0x1a9be partitions`.

Empty built-in list:

- ROM path:
  `0x1a3a0..0x1a3b6`.
- State category:
  firmware bookkeeping.
- Writers:
  if `0x78278e == 0`, calls `0x1284` with arguments `0x39` and
  `0xe7`.
- Readers / consumers:
  startup/default-font setup observes the reported failure path before
  continuing through `0x1a3b8`.
- Output effect:
  indirect pixel effect only; no selectable built-in font candidates
  exist.
- Evidence:
  `generated/disasm/ic30_ic13_font_resource_scan_01a2e4.lst` at
  `0x1a3a0..0x1a3b8`; startup behavior summarized in
  [firmware-startup.md](firmware-startup.md#startup-outcome-matrix).

`HEAD` classifier result:

- ROM path:
  `0x1a616 -> 0x1a6a4` when `0x1b9c0` returns `1`.
- State category:
  canonical resource data and firmware bookkeeping.
- Writers:
  `0x1a6a4` walks the chain under cursor `0x782884`; validated type
  `0x14/0x15` records pass through `0x1a3f8` and then to
  `0x1a9be(1)`.
- Readers / consumers:
  `0x1a9be` consumes the accepted record pointer and caller class.
- Output effect:
  accepted records become candidate slots that later select glyph
  payloads.
- Evidence:
  `generated/disasm/ic30_ic13_font_resource_scan_01a2e4.lst` at
  `0x1a632..0x1a646`; fixture
  `0x41a HEAD scanner walks verified IC32/IC15 resource chain`.

Container classifier result:

- ROM path:
  `0x1a616 -> 0x1a856` when `0x1b9c0` returns `0`.
- State category:
  firmware bookkeeping.
- Writers:
  `0x1a856` skips recognized `FONT`, `font`, `DUMY`, `TABL`, and
  `tabl` containers or hands a boundary to `0x1a766`.
- Readers / consumers:
  the next `0x1a616` loop consumes the updated `0x782884` cursor.
- Output effect:
  no pixel effect unless a later accepted font record is reached.
- Evidence:
  `generated/disasm/ic30_ic13_font_resource_scan_01a2e4.lst` at
  `0x1a64e..0x1a65e`; classifier behavior listed under
  `Firmware bookkeeping`.

Unknown classifier result:

- ROM path:
  `0x1a616` when `0x1b9c0` returns `-1`.
- State category:
  unknown and firmware bookkeeping.
- Writers:
  bypasses the `HEAD` and container helpers and advances toward the next
  scan segment.
- Readers / consumers:
  the next segment probe consumes `0x782884` and scan bounds.
- Output effect:
  pixel effect depends on whether later bytes expose additional font
  records.
- Evidence:
  `generated/disasm/ic30_ic13_font_resource_scan_01a2e4.lst` at
  `0x1a632..0x1a660`; continuation boundary below.

Accepted built-in candidate:

- ROM path:
  `0x1a9be(1)`.
- State category:
  canonical candidate state and derived/cache state.
- Writers:
  `0x1bc38` inserts the pointer; `0x1a9be` copies bits from record
  bytes `+0x0c/+0x0d`, increments `0x78278e`, updates class/range
  counters, and advances window cursors.
- Readers / consumers:
  `0x1569c`, `0x156de`, `0x1519a`, `0x153c6`, and `0x14398` consume
  the resulting windows.
- Output effect:
  determines which built-in record can supply metrics, glyph table
  entries, and bitmap rows.
- Evidence:
  `generated/disasm/ic30_ic13_font_candidate_classify_01a9be.lst` at
  `0x1a9be..0x1ab82`; fixtures
  `0x1a9be scanned font candidate list partitioning` and
  `actual IC32/IC15 built-in records feed 0x1a9be partitions`.

Verified built-in partition:

- ROM path:
  `0x1a9be` with verified `IC32,IC15` records.
- State category:
  canonical candidate state and derived/cache state.
- Writers:
  produces `0x78278e = 24`, class-one low count `0x782792 = 12`,
  class-zero low count `0x78279a = 12`, and cursor windows ending at
  `0x782354` and `0x782384`.
- Readers / consumers:
  activator `0x1569c` chooses class-one or class-zero active windows.
- Output effect:
  pixel effect begins only after a parsed command selects a context and
  printable bytes request glyphs.
- Evidence:
  resource model above; generated reports `ic32_ic15_font_records.md`
  and `ic32_ic15_builtin_glyph_payloads.md`.

Class activation:

- ROM path:
  `0x1569c`.
- State category:
  derived/cache state.
- Writers:
  if `0x782da3 == 0`, writes active pointer/count from `0x7827ac` and
  `0x782798`; otherwise from `0x7827a0` and `0x782790`; sets high active
  bits in each selected entry.
- Readers / consumers:
  `0x156de`, `0x1519a`, `0x153c6`, and `0x14398` consume
  `0x78287c` and `0x7827b8`.
- Output effect:
  chooses primary or secondary candidate class before symbol/metric
  filtering.
- Evidence:
  `generated/disasm/ic30_ic13_font_candidate_activate_01569c.lst` at
  `0x1569c..0x156dc`; fixture
  `0x1569c activates concrete built-in candidate windows`.

Symbol filtering:

- ROM path:
  `0x156de`.
- State category:
  parser scratch and derived/cache state.
- Writers:
  reads parsed symbol words from `0x782ef4` or `0x782f04`, remembered
  words from `0x782f08/0x782f0a`, and fallback words under `0x782f0c`;
  clears inactive candidate marks and rewrites `0x78287c` /
  `0x7827b8`.
- Readers / consumers:
  height, spacing, pitch, and chooser filters consume the reduced
  window.
- Output effect:
  selects which glyph map can resolve printable bytes.
- Evidence:
  `generated/disasm/ic30_ic13_font_candidate_activate_01569c.lst` at
  `0x156de..0x1583e`; symbol-set fixtures named in `Parser scratch`.

Height filtering:

- ROM path:
  `0x1519a`.
- State category:
  parser scratch and derived/cache state.
- Writers:
  reads requested heights from `0x782ef2` or `0x782f02`; compares
  built-in fields `+0x28/+0x2a` through `0x13bca`; rewrites
  `0x78287c` / `0x7827b8`.
- Readers / consumers:
  `0x153c6` and `0x14398` consume the surviving candidates.
- Output effect:
  narrows the candidate used to compute glyph metrics and source object
  state.
- Evidence:
  `generated/disasm/ic30_ic13_font_candidate_filters_01519a.lst` at
  `0x1519a..0x1533c`; fixture
  `0x1519a filters concrete active candidates by height`.

Spacing and pitch filtering:

- ROM path:
  `0x153c6`.
- State category:
  parser scratch and derived/cache state.
- Writers:
  reads spacing from `0x782eef` or `0x782eff`, pitch from `0x782ef0` or
  `0x782f00`, and candidate fields `+0x21/+0x24`; clears inactive marks
  and updates active pointer/count.
- Readers / consumers:
  chooser `0x14398` consumes the reduced active list.
- Output effect:
  narrows proportional/fixed and pitch-compatible records before final
  selection.
- Evidence:
  `generated/disasm/ic30_ic13_font_candidate_filters_01519a.lst` at
  `0x153c6` onward; fixture
  `0x153c6 filters concrete active candidates by spacing and pitch`.

Final candidate choice:

- ROM path:
  `0x14398`.
- State category:
  canonical selected state and derived/cache state.
- Writers:
  chooses selected slot `0x7828a8` from the active list using comparator
  fields `+0x2f..+0x31` and active object comparison helpers.
- Readers / consumers:
  `0x144d2`, `0x14c64`, `0xc428`, and printable-byte path `0x1393a`
  consume the chosen context.
- Output effect:
  establishes the resource context from which later glyph rows are read.
- Evidence:
  `generated/disasm/ic30_ic13_active_object_scan_014398.lst`; fixture
  `0x14398 chooses concrete active built-in candidate`.

Glyph/render handoff:

- ROM path:
  `0x144d2 -> 0x14c64 -> 0xc428 -> 0x1393a`.
- State category:
  canonical selected-resource state, canonical page/text state, and
  derived/cache state.
- Writers:
  `0x144d2` copies the selected candidate longword from slot pointer
  `0x7828a8` into current-font context record `0x782ee6` or `0x782ef6`.
  `0x14c64` rebuilds active map `0x782f32` or `0x783032` and selected-font
  snapshots. `0xc428 -> 0xc4fc` installs the current context under page-root
  slots `+0x2c..+0x68` and writes selected page-root slot `0x78297e`.
  `0xd04a -> 0x1393a` writes printable source fields
  `+0x00/+0x04/+0x0a/+0x10` from the current context, active map, and mapped
  glyph.
- Readers / consumers:
  `0xd3b2` / `0xd824` copy selected page-root slot `0x78297e` into source
  `+0x16`, mark live flag `0x78297f + slot`, and call `0x12f2e`.
  Publication and bridge copy root context slots to render-record
  `+0x24..+0x60`; compact glyph renderers consume the compact payload glyph
  byte and copied context slot.
- Output effect:
  this is the field bridge from selected resource candidate to compact text
  page object. Visible text rows later come from the selected resource bitmap
  rows rendered through `0x1f354`.
- Evidence:
  [font-context-metrics.md](font-context-metrics.md#printable-source-capture),
  [resource-rom.md](resource-rom.md#resource-rom-outcome-matrix),
  [page-record-storage.md](page-record-storage.md#context-slot-preservation-checkpoint),
  `generated/analysis/ic30_ic13_font_context_bridge.md`, and
  `generated/analysis/ic30_ic13_text_glyph_index_flow.md`.

Unresolved middle edges:

- `0x1a616..0x1a9be` is ROM-local and documented for verified
  `0x080000..0x0bffff` bytes. The exact physical source for
  `0x0c0000..0x0ffffe` remains outside the dumped resource image.
- `0x1a616` optional cartridge scans over `0x200000..0x5ffffe` are
  decoded at the handler level but lack cartridge image data, so their
  candidate contents remain an external-resource boundary.
- `0x14398 -> 0x144d2 -> 0x1393a` is no longer an unresolved middle edge for
  the documented primary and secondary built-in paths. Remaining variants only
  matter when they change selected context longword, active map, page-root
  slot, printable source fields, compact selector class, or downstream render
  inputs.

## Field Groups

Canonical resource records:

- `HEAD`-path records carry scanner length and type fields. Fixture
  `0x41a HEAD scanner walks verified IC32/IC15 resource chain` pins the
  verified 24-record chain.
- The verified image starts with `HEAD` at file offset `0x000000`
  / firmware address `0x080000`; generated reports
  `ic32_ic15_header.txt`, `ic32_ic15_resource_markers.txt`, and
  `ic32_ic15_strings.txt` provide the ROM-byte evidence for the header,
  copyright text, named Courier/Line Printer marker offsets, and tail
  interleave marker.
- Accepted font records use byte `+0x0d` for candidate flag bits
  28..29, set high flag `0x40000000`, and mirror byte `+0x0c == 2`
  into high flag `0x04000000`.
- Class/orientation byte `+0x20`, spacing byte `+0x21`, symbol word
  `+0x22`, HMI source longword `+0x24`, height-like words
  `+0x28/+0x2a`, and comparator bytes `+0x2f..+0x31` are the
  ROM fields consumed by `0x156de`, `0x1519a`, `0x153c6`, and
  `0x14398`.
- Glyph table entries and bitmap payloads are canonical resource data.
  Fixtures cover contexts `0x4008004c`, `0x44080418`, and
  `0x440946b4` for glyph `0`, plus context `0x440946b4` glyph `32`,
  including entry pointer, bitmap pointer, delta, mode, row count,
  width, render span, and decoded bitmap rows.

Canonical candidate-list state:

- `0x782324`: shared candidate pointer-list base.
- `0x78278e`: total accepted candidate count.
- `0x782790..0x78279e`: candidate-list counts by class/range window.
- `0x7827a0..0x7827b4`: candidate-list cursor/window starts.
- `0x782884`: resource scan cursor.
- `0x78288c` / `0x782890`: scan start/end, initialized to
  `0x080000..0x0ffffe` for built-in resources.
- `0x78287c`: active candidate-list pointer selected by `0x1569c`.
- `0x7827b8`: active candidate-list count selected by `0x1569c`.
- `0x7828a8`: selected candidate slot after filters and chooser.

Derived/cache state:

- For the verified built-ins, class-one low/range counters are
  `0x782792 = 12` and `0x782794 = 0`.
- For the verified built-ins, class-zero low/range counters are
  `0x78279a = 12` and `0x78279c = 0`.
- Final cursor windows are `0x7827a0 = 0x782324`,
  `0x7827a4 = 0x782354`, `0x7827a8 = 0x782354`,
  `0x7827ac = 0x782354`, `0x7827b0 = 0x782384`, and
  `0x7827b4 = 0x782384`.
- `0x1569c` derives active class-zero pointer/count
  `0x782354`/`12` when `0x782da3 == 0`, or class-one
  pointer/count `0x782324`/`12` otherwise. It then marks selected
  entries with high bit `0x80000000`.

Parser scratch:

- Parsed font-selection request fields live in `0x782eec..0x782f04`
  and dirty flags `0x782f2c/2d`. They consume candidate windows but are
  not produced by the resource scan.
- `ESC (` / `ESC )` symbol words are parser-produced inputs to
  `0x156de`. Fixtures `0x120be/0x1be22 symbol-set stream updates active
  words and 0x14f16 glyph maps` and
  `symbol-set parser trace feeds active map patches` cover that input
  path.

Firmware bookkeeping:

- `0x41a` and `0x1a616` both walk resource records, but for different
  purposes. `0x41a` validates startup-visible chains and executable
  handoffs. `0x1a616` builds font candidate windows.
- `0x1b9c0` is the resource-record signature classifier used by `0x1a616`
  and optional-window scanner `0x1a0f2`. It returns `1` when the current
  cursor longword is `HEAD`; returns `0` when the current longword is
  `FONT`, `font`, `DUMY`, `TABL`, or `tabl`, or when one of
  `FONT`, `font`, `DUMY`, `TABL`, or `tabl` appears at cursor `+8`; and
  returns `-1` when neither the current cursor nor cursor `+8` matches those
  signatures.
- In the built-in scan caller `0x1a616`, classifier return `1` calls
  `0x1a6a4`, which walks record chains and passes accepted type
  `0x14/0x15` records through validator `0x1a3f8` and candidate classifier
  `0x1a9be(1)`. Return `0` calls `0x1a856`, which skips `TABL`, `tabl`,
  `DUMY`, `font`, and `FONT` containers before either stopping or handing a
  non-container boundary to helper `0x1a766`. Return `-1` bypasses both
  helpers and advances to the next scan segment.
- In the optional-window table scanner `0x1a0f2`, classifier return `1`
  calls `0x1a220` to copy record byte `+0x0c` into `0x782898`, advance by
  record longword `+0x04`, and append record word `+0x0e`. Return `0` calls
  `0x1a254` to skip `TABL`, `tabl`, `DUMY`, `FONT`, and `font` containers,
  copy byte `+0x05` into `0x782898`, advance eight bytes, and append word
  `+0x06`. Return `-1` appends a zero word and advances to the next
  `0x20000` grid point in the selected optional-resource window.
- `0x1a616` recognizes and skips resource container signatures before
  passing accepted font records to `0x1a9be`.
- `0x1a616 candidate scan continuation policy changes built-in counts`
  constrains the unresolved continuation range. A visible mirror at the
  next resource segment doubles `0x78278e` to `48` and low class counts
  `0x782792/0x78279a` to `24`; code-pair and zero-fill continuations
  keep the verified `24` / `12` / `12` state.
- `0x782796` and `0x78279e` are initialized or cleared but not
  incremented by decoded built-in `0x1a9be` for the verified window.
  Downloaded-font analogs are documented separately.

Unknown:

- Cartridge or external resource behavior outside the verified built-in
  window `0x080000..0x0ffffe`.
- Manual-facing names for record fields `+0x28..+0x31`. The ROM roles
  are pinned as decoded-height inputs and chooser tie-breakers, but the
  service-manual terminology remains unresolved.
- Manual-facing names for non-signature optional-resource boundary records
  reached after `0x1b9c0` returns `-1`. The ROM branch behavior is
  documented, but no physical cartridge image has supplied those records.

## Writers

- `0x1a2e4` clears candidate counts, initializes cursor windows at
  `0x782324`, sets scan bounds, and calls `0x1a616`.
- `0x1a616` scans resource regions, recognizes/skips resource container
  records, and passes accepted font records to `0x1a9be`.
- `0x1a9be` writes candidate flags, increments `0x78278e`, partitions by
  class/address range, and advances `0x7827a0..0x7827b4`.
- `0x1bc38` inserts inline or downloaded payload candidates into the
  same pointer list. It rejects full lists at `0x78278e >= 0x00c0`,
  chooses class from payload byte `+0x20` for flagged/resource records
  or byte `+0x16` for inline/downloaded records, shifts the class tail,
  and returns the inserted slot pointer in `D7`.
- `0x1bd2e` deletes one candidate slot from the shared list. It receives
  the slot pointer through argument `+8`, computes the last occupied slot
  as `0x782324 + 4 * 0x78278e - 4`, copies later longwords down, and
  clears the old tail. Callers such as `0x1ba92` and `0x1887a` handle
  counter/window decrements.

## Readers And Consumers

- `0x1569c` activates the class-zero or class-one candidate window.
- `0x156de` consumes symbol words and filters the active list by symbol
  set, including remembered and fallback-word branches.
- `0x1519a` filters active candidates by height.
- `0x153c6` filters active candidates by spacing and pitch.
- `0x14398` chooses the final candidate slot.
- `0x13a48`, `0x13eb8`, and `0x14c64` compare active object and
  context records during selection and refresh.
- `0x1bd2e` consumes candidate-list layout when deleting a slot.

## Output Effect

The resource scan has no direct pixel output. Its visible effect is the
candidate context selected for later glyph lookup and compact row
rendering.

The primary fixture stream `ESC (s0p10h12v0s0b3T!!` filters class-zero
candidates to context `0xc008004c` and renders Courier rows. The
secondary fixture stream `ESC )s0p16h8v0s0b0T SO !!` filters class-one
candidates to context `0xc00ae122` after SO and renders the secondary
rows. Symbol miss fixtures prove fallback words `0x0115` and `0x000e`;
remembered-symbol fixtures prove the middle branch between requested
word and fallback word.

The font-sample generator consumes the same candidate windows when
printing built-in resource listings. That path is documented in
[font-sample-page.md](font-sample-page.md#owner-summary) and uses fixtures such as
`font sample class-one row continuation emits fresh source heading page
record`.

## Continuation Boundary

The verified local resource image covers firmware addresses
`0x080000..0x0bffff`. The built-in scan range seeded by `0x1a2e4` extends to
`0x0ffffe`, so the ROM-local scanner model can describe consequences for bytes
after the dumped `IC32,IC15` pair, but it cannot choose the physical decode
source for those bytes.

That boundary is pixel-affecting for the transparent secondary segment-57
case documented in [transparent-print-data.md](transparent-print-data.md).
The compact renderer resolves bucket `456` to firmware read
`0x0bfe22..0x0c0321`: the first `478` bytes are verified from `IC32,IC15`, and
the remaining `802` bytes start at `0x0c0000`. Fixture
`transparent secondary segment-57 continuation policies diverge after verified
bytes` proves mirror, code-pair continuation, and zero-fill all preserve the
same current-band rows but produce different fallback-row digests.

The scanner consequences of those continuation policies are also pinned.
Fixture `0x41a HEAD scanner would duplicate records under simple resource
mirror` proves a full `IC32,IC15` mirror at the next segment would expose a
second `HEAD` chain. Fixture
`0x1a616 candidate scan continuation policy changes built-in counts` proves
that same mirror would double total candidates to `48` and low class-one /
class-zero counts to `24` / `24`; code-pair and zero-fill continuations keep
the verified `24` / `12` / `12` state. Tracked tool
`tools/probe_resource_window.py --quiet` verifies those suffix hashes,
continuation hashes, and scanner-count consequences from
`data/rom_manifest.json` plus the ignored local ROM images.

## Reproduction Contract

A renderer that wants byte-for-byte agreement with these ROM paths must:

- parse the built-in `HEAD` chain into the same 24 candidate records;
- preserve the candidate-list counters, windows, and high-bit flags
  described above;
- apply the same active-window, symbol, height, spacing, pitch, and
  chooser steps before glyph lookup;
- use the selected context longword when resolving glyph table entries
  and bitmap payload rows;
- treat the unresolved `0x0c0000..0x0c0321` resource continuation as a
  separate physical decode boundary, not as a parser or glyph-field
  ambiguity.

## Confidence

Confidence is high for the verified built-in scan, counters/windows,
activation, filters, chooser, primary/secondary visible output streams, and
the modeled scanner consequences of the three tested `0x0c0000` continuation
policies. Confidence is medium for the actual hardware decode source at
`0x0c0000..0x0c0321` and for external cartridge/resource windows because the
decoded handlers are known, but no matching board decode, cartridge image, or
ROM image evidence has been captured for those ranges.

## Remaining Edges

- `0x1a616..0x1a9be`: verified `IC32,IC15` scan behavior is fixture-backed
  through `0x0bffff`. The exact remaining built-in continuation boundary is
  firmware address `0x0c0000..0x0c0321`, where board/emulator decode or a
  matching ROM/cartridge image must choose among the recorded mirror,
  code-pair, and zero-fill fallback-row candidates.
- `0x14398..0x156de`: many visible output streams are covered, but
  broader fallback/error combinations should only be added when they produce a
  different selected context, active map, page-root slot, printable source
  field, compact selector class, or rendered row.
- Resource fields `+0x28/+0x2a` and `+0x2f..+0x31`: decoded roles are
  documented as height inputs and chooser tie-breakers, while precise
  manual terminology remains open in
  [resource-rom.md](resource-rom.md#resource-rom-outcome-matrix).
