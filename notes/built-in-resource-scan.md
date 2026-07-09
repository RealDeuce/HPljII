# Built-In Resource Scan And Candidate Windows

This note documents the firmware path that turns the `IC32,IC15`
resource ROM into selectable built-in font candidates. The byte-level
record and bitmap ledger remains in [resource-rom.md](resource-rom.md);
this file records the state contract used by font selection and visible
text output.

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
[font-sample-page.md](font-sample-page.md) and uses fixtures such as
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
  broader fallback/error combinations should only be added when they
  produce a different selected context, map, object prefix, or rendered
  row.
- Resource fields `+0x28/+0x2a` and `+0x2f..+0x31`: decoded roles are
  documented as height inputs and chooser tie-breakers, while precise
  manual terminology remains open in [resource-rom.md](resource-rom.md).
