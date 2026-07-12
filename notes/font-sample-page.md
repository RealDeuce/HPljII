# Font Sample Page Generator

This note documents the LaserJet II firmware font-sample printout path as a
semantic checkpoint. It covers the internal generator from resource candidate
windows through printable row bytes, page-record objects, and rendered segment
surfaces.

Status: composed for the normal source/class printout loop and the major
continuation-page object forms. This is firmware-generated text, not host
input: the path calls the ordinary printable handler `0xd04a` directly after
selecting and formatting ROM/resource records.

## Owner Summary

This note owns the firmware-generated font sample printout path. Unlike normal
PCL input, the source bytes are created by ROM helpers after candidate/resource
selection. Once generated, they intentionally rejoin the ordinary printable
text path through `0xd04a`, page-record queueing, publication, render bridge,
and compact text row rendering.

Primary routes:

- Setup:
  `0x1e0b2` prepares normal sample-page state, forces sample-page VMI/HMI
  defaults, and reaches printout entry `0x1c204`. Alternate setup
  `0x1e8e6` shares the same page/font helper chain but writes copy sentinel
  `0xffff` and derives the row budget directly from page limit
  `0x782db6 - 1`.
- Source/class loops:
  `0x1c28e..0x1c344` run class-zero and class-one passes; `0x1c2fe..0x1c332`
  iterate source groups `0..3`; `0x1c354..0x1c5e4` walks rows within one
  source group.
- Candidate resolution:
  `0x1b50e` resolves request indexes through fast probe `0x1b8ea`, mode
  windows, current-slot suppression, and Roman-8 substitution before exposing
  a selected candidate row.
- Context install and row formatting:
  `0x1c5e8` installs selected context through `0x14c64` and `0xc428`;
  `0x1cabe` emits row prefix, font name/style, pitch/height, symbol text, and
  sample columns through printable/fixed-space helpers.
- Sample byte runs:
  `0x1cf34` emits run table `0x1c1cf`, optionally advances to the alternate
  context/sample row, and emits run table `0x1c1e9`.
- Page/render route:
  emitted bytes flow through `0xd04a`, `0x1393a`, `0x12f2e`, publication,
  `0x1ed84`, `0x1edc6`, `0x1ef6a`, and compact text renderers.

Field groups:

- Canonical sample state:
  candidate counts/windows `0x78278e`, `0x782798`, `0x782790`,
  `0x7827a0..0x7827b4`, selected current/alternate contexts, source labels
  at `0x1c170`, and sample run tables `0x1c1cf` / `0x1c1e9`.
- Canonical page/text state:
  current page root, page-root context slots, cursor `0x782c8e`, page limit
  `0x782db6`, row-height word `0x783f06`, copy count/sentinel
  `0x782da4`, wrap/perforation bytes `0x783190` / `0x783191`, and VMI/HMI
  defaults `0x783160` / `0x78315c`.
- Parser scratch:
  synthetic orientation record at `0x78299e` from `0x1d76c`, fast-probe
  fields `0x7828a0`, `0x7828a4`, `0x78289f`, and Roman-8 substitution scratch
  `0x7828ac` / `0x7821a0`.
- Firmware bookkeeping:
  per-source status bytes `0x783f02..0x783f05`, recent-context count
  `0x783f08`, recent-context list `0x783f0a`, and local page-break word
  `-6(A6)`.
- Derived/cache state:
  row-to-row placement from `0x1d050`, alternate-row fit from `0x1d868`,
  multi-probe fit from `0x1dcf2`, and page-record/render bucket digests used
  only as evidence.
- Hardware/external state:
  none required for the ROM-local sample-page path once resource bytes and
  initial firmware state are fixed.
- Unknown:
  manual-facing baseline/cell terminology for resource fields, and future
  forced-continuation cross-products that might expose new page-object forms.

Output effect:

- The sample generator creates visible text using the same compact text path as
  host printable bytes, but the bytes are ROM-generated from resource/candidate
  metadata and sample tables.
- It produces page objects and rendered segment surfaces through the normal
  page/render pipeline; it is not a direct resource-ROM dump.
- A reproducer must preserve source/class order, candidate row resolution,
  context installs, sample run bytes, continuation decisions, and the ordinary
  compact-text rendering path.

## Evidence

- `generated/analysis/ic30_ic13_font_sample_page.md`
- `generated/analysis/ic30_ic13_renderer_fixture_harness.md`
- `generated/analysis/ic32_ic15_builtin_font_samples.md`
- `generated/analysis/ic32_ic15_builtin_glyph_payloads.md`
- `generated/analysis/ic32_ic15_font_records.md`
- `generated/disasm/ic30_ic13_font_sample_page_01c170.lst`
- `generated/disasm/ic30_ic13_font_sample_row_helpers_01d198.lst`
- `generated/disasm/ic30_ic13_font_page_setup_01e0b2.lst`
- `generated/disasm/ic30_ic13_font_page_setup_alt_01e8e6.lst`
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
- Copy count/sentinel word `0x782da4`: normal setup `0x1e0b2` writes `1`,
  while alternate setup `0x1e8e6` writes `0xffff`.
- Wrap and perforation bytes `0x783190` / `0x783191`, cleared by both setup
  entries before generated sample text is emitted.
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

## Candidate Resolver Checkpoint

This checkpoint owns resolver `0x1b50e` as the source-row selector for the
font sample page. It starts with a source mode and row ordinal from the
`0x1c334..0x1c5e4` row loop, and it ends with either no row or a selected
candidate slot plus caller-visible symbol word for later normalization,
context install, row formatting, and printable output. It does not emit text
or queue page objects directly.

Route:

- `0x1b516..0x1b558` handles the requested ordinal. Ordinal `0xff`
  disables lookup, clears the caller output word, and returns no resource.
  Otherwise the resolver tries fast probe `0x1b8ea(mode, ordinal)` first.
  On fast-probe success, selected slot `0x7828a0` and output word
  `0x7828a4` become the row candidate returned to the caller.
- `0x1b568..0x1b5a4` selects the first scan window when fast probe misses:
  mode `3` uses `0x7827ac` / `0x78279a`, modes `1` and `2` use
  `0x7827b0` / `0x78279c`, mode `0` uses `0x7827b4` / `0x78279e`, and other
  modes miss.
- `0x1b5a4..0x1b60c` sets Roman-8 substitution flag `0x7828ac = 1` unless
  requested symbol word `0x7821a0` is one of `0x0115`, `0x0175`,
  `0x0155`, or `0x000e`.
- `0x1b61a..0x1b650` scans first-window candidates. Each candidate word is
  read through `0x1bbfe`, classified by `0x1b750(mode, slot, word)`, and
  skipped while the classifier returns zero.
- `0x1b650..0x1b74e` selects the second scan window after first-window
  exhaustion: mode `3` uses `0x7827a0` / `0x782792`, modes `1` and `2` use
  `0x7827a4` / `0x782794`, and mode `0` uses `0x7827a8` / `0x782796`.
- `0x1b66e..0x1b706` owns the Roman-8 duplicate/substitution decision.
  Classifier return `2` marks a pending duplicate Roman-8 candidate.
  When the requested ordinal is reached, a Roman-8 candidate with
  substitution enabled and duplicate pending returns requested symbol word
  `0x7821a0`; otherwise it returns the candidate word.
- `0x1b6b2..0x1b706` lets non-selected Roman-8 candidates count twice for
  non-special requested symbols, except when current selected slot
  `0x7828a0` is the same slot.
- `0x1b750..0x1b7ac` accepts only candidates that pass admissibility helper
  `0x1b7b2` and current-Roman-8 suppression `0x1b8b6`. It returns `2` for
  the current selected slot in modes `1` or `2`, and `1` for other accepted
  candidates.
- `0x1b7b2..0x1b8b4` is mode-specific admissibility: mode `3` accepts the
  built-in symbol words above, mode `1` accepts optional window
  `0x200000..0x3ffffe`, mode `2` accepts optional window
  `0x400000..0x5ffffe`, and mode `0` accepts downloaded records whose
  `0x170be` record flags include bit `30`.
- `0x1b8ea..0x1b98c` is the fast probe. It clears `0x7828a0`; mode `3`
  searches fallback through `0x1ae7e`, while modes `1` and `2` call
  `0x1adaa` first with primary selector `0x78289f = 0` and then with
  secondary selector `0x78289f = 1`. It succeeds only for requested ordinal
  zero and a nonzero selected slot.

State grouping:

- Canonical sample/resource state:
  candidate window pointer/count pairs `0x7827a0..0x7827b4` and
  `0x782792..0x78279e`, selected candidate slot `0x7828a0`, caller-visible
  output word `0x7828a4`, requested symbol word `0x7821a0`, and the accepted
  downloaded-record state tested through `0x170be`.
- Derived/cache state:
  current source mode, requested ordinal, classifier return, pending duplicate
  Roman-8 marker, Roman-8 substitution flag `0x7828ac`, fast-probe selector
  scratch `0x78289f`, and the final candidate slot/word pair handed back to
  the row loop.
- Parser scratch:
  none. The font sample generator is firmware-produced; resolver inputs come
  from row-loop state, not host parser records.
- Firmware bookkeeping:
  scan window cursors and counts, duplicate/suppression decisions, and
  optional-window/downloaded-record predicate calls.
- Hardware/external state:
  optional cartridge bytes for modes `1` and `2` remain external data if a
  physical optional window is present; the base ROM-local resolver route is
  still fully defined.
- Unknown:
  no ROM-local resolver branch remains unnamed for the documented source
  modes. Optional cartridge contents can change which candidates exist, but
  not the `0x1b50e` scan and substitution rules.

Output effect:

- A successful resolver result selects which candidate enters
  `0x1c746` / `0x1c766` / `0x1c7a8` / `0x1c710`, then context install
  `0x1c5e8`, row formatter `0x1cabe`, sample-run helper `0x1cf34`, and the
  ordinary compact text path. A miss suppresses that row before any printable
  byte, page object, publication record, bridge root, or render input exists.

Evidence:

- `generated/analysis/ic30_ic13_font_sample_page.md`, section
  `Candidate Resolver 0x1b50e`.
- `generated/disasm/ic30_ic13_font_resource_object_lookup_01b4c0.lst`, covering
  `0x1b50e`, classifier `0x1b750`, admissibility helper `0x1b7b2`, and fast
  probe `0x1b8ea`.
- Fixtures `font sample resolver carries first two Courier rows`,
  `font sample non-internal source groups follow modes 0..2`, and
  `font sample full printout rows reuse ROM sample byte runs`.

## Multi-Probe Continuation Preflight

`0x1dcf2` is the later font-sample fit gate used before selected row output is
committed. It does not emit text or allocate page objects itself. It installs
candidate contexts, asks shared calculator `0x1dc38` to project one or more
sample-row positions, compares each projected bottom against page-limit word
`0x782db6`, and returns D7 as the caller's continuation decision.

The shared calculator `0x1dc38..0x1dcf0` receives current and selected context
pointers, an output row-height pointer, a starting packed y, and a mode word.
It reads selected line-advance and row-height inputs through `0x1c6a4` and
`0x1c6da`, writes the caller's row-height word, converts between packed cursor
units through `0x332ee`, `0x3324a`, `0x104fe`, and `0x104d8`, and returns the
projected packed y in D7. Mode `1` adds the reset-row offset used after an
overflowed first pass; mode `0` preserves the normal current-row projection.

`0x1dcf2..0x1de2c` has four observable branches:

- Initial fit:
  `0x1dd1e..0x1dd54` probes current y with calculator mode `0`. If projected
  y plus the row-height word is below `0x782db6` and alternate-row flag
  `0x783132` is clear, it exits D7 `0` at `0x1de1a`.
- Alternate second-row fit:
  when `0x783132` is set, `0x1dd5a..0x1dd8e` probes the second row from the
  first projected y. If the second projected bottom still fits, it exits D7
  `0` at `0x1dd8e`.
- Reset-row continuation:
  after an overflow, `0x1dd98..0x1dde0` converts raw subunits `0x1218` to a
  reset packed y through `0x104d8`, probes mode `1`, and returns D7 `1` at
  `0x1de24` when the reset-row projected bottom is still outside the limit.
- Reset-row recovery:
  if the mode-`1` reset row fits, then `0x1dde2..0x1de16` optionally probes a
  final mode-`0` selected row when `0x783132` is set. It returns D7 `0` at
  `0x1de16` when both reset probes fit, or D7 `1` at `0x1de2c` when the final
  selected-row bottom still crosses the page limit.

State grouping for this checkpoint:

- Canonical page/text state:
  current y `0x782c8e`, page limit `0x782db6`, alternate-row flag
  `0x783132`, selected current/alternate contexts passed by the caller, and
  the caller row-height word written by `0x1dc38`.
- Derived/cache state:
  projected packed y in local `-6(A6)`, row-height word in local `-2(A6)`,
  reset packed y derived from raw `0x1218`, and the D7 fit/continuation return.
- Parser scratch:
  none. The sample generator is firmware-produced; no host byte or parser
  record is consumed by this fit gate.
- Firmware bookkeeping:
  temporary context installation through `0x1cece` and `0x1c5e8` so the
  calculator reads the same metrics that later printable row emission will use.
- Unknown:
  no ROM-local branch, field, or page-output side effect remains unknown for
  `0x1dcf2`. Manual-facing names for the row-height and baseline components
  remain external terminology, not a sample-page dataflow gap.

Writers and readers:

- `0x1dcf2` writes only local projection state and the D7 return flag.
- `0x1cece` and `0x1c5e8` install the current and selected contexts before the
  probes.
- `0x1dc38` reads the installed context metrics, writes the caller row-height
  word, and returns projected y.
- The caller at `0x1d964` consumes D7 to decide whether to continue on the
  current page or run the existing continuation path before row emission.

Output effect:

- D7 `0` is a no-publication preflight result: later `0x1cabe` and `0x1cf34`
  emit row bytes on the current page through `0xd04a`.
- D7 `1` is a page-boundary decision for the caller. The visible effect occurs
  only after the caller invokes the already documented continuation/page-record
  path; `0x1dcf2` itself creates no compact object, source heading, or rendered
  row.

Evidence:

- Disassembly:
  `generated/disasm/ic30_ic13_font_sample_row_helpers_01d198.lst`
  `0x1dc38..0x1dcf0` and `0x1dcf2..0x1de2c`.
- Fixture:
  `font sample multi-probe preflight follows 0x1dcf2` records the first
  `COURIER` case with `0x783132 = 0` returning D7 `0` at `0x1de1a`, the
  `0x783132 = 1` two-row case projecting y
  `0x00900000 -> 0x00ce0000 -> 0x010c0000` under limit `300`, the tightened
  limit `250` returning D7 `1` at `0x1de24`, and the high-y reset case
  starting at `0x01f40000` with limit `600` returning D7 `0` at `0x1de16`.

## Row Text Helper Ledger

`0x1cabe` emits the visible row columns, but the lower helper cluster at
`0x1d198..0x1d79c` decides which printable name bytes reach `0xd04a`.
This cluster is part of the reproduction model because it converts selected
resource records into the row text that later becomes compact page objects.

- `0x1d198` is the 25-column name/style formatter. For fixed-form records
  passed without an explicit name pointer, it masks the selected context to a
  24-bit record address, reads bytes `+0x26` and `+0x27`, and either uses
  resource-chain helper `0x1d4ee` or fallback helper `0x1d460`.
  For explicit-name callers, `0x1d1d6..0x1d20a` first emits the name through
  `0x1d5fa`, then reads the same two formatter roles from record bytes
  `+0x2f` and `+0x30`. The first role byte controls the trailing style text:
  value `1` emits local string `0x1d183` (`ITALIC`), value `2` emits
  `0x1d17c` (`SLANT`), and other nonzero values are converted to decimal
  digits at `0x1d38a..0x1d448`. The second role byte controls the weight
  suffix: positive values emit `0x1d192` (`BOLD`), negative values emit
  `0x1d18b` (`LIGHT`), and zero emits no weight suffix. These strings are
  emitted through `0x1d6ea`, so they become ordinary compact text objects via
  `0xd04a`.
- `0x1d460` walks resource container records starting at the masked record
  address. It follows `FONT` and lowercase `font` records by adding longword
  `+0x2e`, follows `TABL`, lowercase `tabl`, and `DUMY` records by adding
  longword `+0x04`, and returns the word at the final record plus `6`.
- `0x1d4ee` scans 32 ten-byte rows at `0x782640`. It matches the masked
  selected record address against row longword `+0x06`. If the row's word
  `+0x02` has bit 29 set, it returns `1`; otherwise it returns `0x15`.
  Exhausting the table reports status `(0xe3, 0x52)` through `0x1284`.
- `0x1d572` copies ten name bytes from record `+0x04`, trims trailing bytes
  that are `<= 0x20` or in the control range `0x80..0x9f`, sanitizes the
  surviving fixed-length string through `0x1d71e`, and returns the retained
  length.
- `0x1d5fa` is the explicit-name path used when a caller supplies the name
  pointer. It reads a name table at record `+0x38`: with display mode `0` it
  emits through `0x1d65e`; otherwise it caps the stored length at 25 and
  emits through `0x1d71e`.
- `0x1d65e` copies a caller-length string, trims the same trailing control or
  whitespace bytes as `0x1d572`, emits the sanitized bytes through `0x1d71e`,
  and returns the retained length.
- `0x1d6ea` emits a zero-terminated string through printable handler `0xd04a`
  until it reaches NUL or the 25-column cap.
- `0x1d71e` emits a fixed-length string through `0xd04a`, replacing bytes
  `<= 0x1f` and bytes `0x80..0x9f` with space before emission.
- `0x1d79c` probes up to two candidate rows for a source group by calling
  `0x1b50e`, normalizing with `0x1c746`, and checking class/orientation with
  `0x1c710` against `0x782da3`. It also consults source-status byte
  `0x783f02 + source` when class pass `1` needs to resume after the prior
  pass. Its return is a row-availability flag for callers such as the sample
  page setup and continuation paths, not printable output by itself.
- The apparent call targets `0x1df11`, `0x1df48`, `0x1df80`, `0x1dfba`,
  `0x1dfc1`, `0x1dfd0`, `0x1e202`, `0x1e20c`, and `0x1e210` are not ROM
  control-flow edges in this path. They are `unidasm` interpretations of
  embedded data after the helper bodies: text/table bytes around
  `0x1de78..0x1dfff` and `0x1e18e..0x1e1a0`, including status/menu strings
  and symbol-set lookup entries. Treat them as data boundaries, not
  undocumented handlers.

State classification for this helper cluster:

- Canonical ROM/resource state: fixed-form record bytes `+0x04..+0x0d`,
  `+0x18`, `+0x26`, `+0x27`, explicit name table pointer `+0x38`, and
  resource-chain signatures `FONT`, `font`, `TABL`, `tabl`, and `DUMY`.
- Canonical firmware state: name-status table `0x782640`, active class byte
  `0x782da3`, and per-source resume/status bytes `0x783f02..0x783f05`.
- Canonical ROM table state: row-helper local strings and tables under
  `0x1de78..0x1dfff`, plus setup text/table bytes under
  `0x1e18e..0x1e1a0`.
- Derived/cache state: the masked 24-bit record address, trimmed fixed-length
  strings, fallback family/style names from tables `0x1c0a6` and `0x1c11a`,
  local suffix strings `0x1d17c`, `0x1d183`, `0x1d18b`, and `0x1d192`, numeric
  style digits derived at `0x1d38a..0x1d448`, and the 25-column cap enforced
  before the next row field.
- Parser scratch: no host byte is fetched; all helper output rejoins the
  ordinary printable path by calling `0xd04a` directly.
- Firmware bookkeeping: local retained-length counters and row-availability
  flags returned in `D7`.
- Unknown: manual-facing names for bytes `+0x26`, `+0x27`, `+0x2f`,
  `+0x30`, and the `0x782640` row flags remain unresolved. Their ROM-local
  formatting roles are pinned by `0x1d1b6..0x1d260`,
  `0x1d1f6..0x1d20a`, `0x1d2f8..0x1d448`, and
  `generated/disasm/ic30_ic13_font_sample_row_helpers_01d198.lst`.

Unknown:

- Manual-facing baseline/cell names remain open; a known printed/self-test
  sample would be optional correlation, not evidence required for the
  ROM-derived page-image model.
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

Full-printout rendered segment contract:

- Source `0`, class `0`, row count `0`: `1` render bucket, `33` rendered
  bucket rows, maximum width `656`, digest
  `105c04604475622eb5b4511ca69b95634bd2d9c5ddefcb0cb07e12ef45b234d1`.
- Source `1`, class `0`, row count `1`: `6` render buckets, `210` rendered
  bucket rows, maximum width `2219`, digest
  `1e99e81ad52be89b8551089ff87d6852ec69bb3f5d61fa0fbb1d01b94f88541f`.
- Source `2`, class `0`, row count `1`: `6` render buckets, `210` rendered
  bucket rows, maximum width `2219`, digest
  `940ec458086cb0917da3c2de65b52d2bfec0e57f1d334e8f5ba83946c9739419`.
- Source `3`, class `0`, row count `14`: `65` render buckets, `2012`
  rendered bucket rows, maximum width `2219`, digest
  `dd7e19b1aa077ccb794e73051e68c54e11e335ffcd110e92dc01b39132c638af`.
- Source `0`, class `1`, row count `0`: `1` render bucket, `33` rendered
  bucket rows, maximum width `4083`, digest
  `9a71cdb0b6f8b1365d439119b2b8e1d3d4b3b6a720f729ac94065edef5ba4d2f`.
- Source `1`, class `1`, row count `1`: `5` render buckets, `146` rendered
  bucket rows, maximum width `4097`, digest
  `018cdd48ede556dc439d5c5434f775aa7a10dd38321b4645e697542a9c7b825e`.
- Source `2`, class `1`, row count `1`: `5` render buckets, `146` rendered
  bucket rows, maximum width `4097`, digest
  `76b22e4a81d534146a094b0f432909cbb5623d333d29cd373a63e7adb600f786`.
- Source `3`, class `1`, row count `14`: `50` render buckets, `1257`
  rendered bucket rows, maximum width `4097`, digest
  `3bffa7214d9a478ec5fb5fd47ccb3458e9079daea12d77443437dd9ff11b4224`.

These eight segment records are the current ROM-derived pixel contract for the
sample printout. They are produced from page-record segments, not from a direct
resource-ROM dump: each segment has already crossed `0x1ed84` / `0x1edc6`,
`0x1ef6a`, and the compact text row-copy helpers. Physical paper comparison
can validate placement, but it is not needed to reproduce these ROM-visible
surfaces from the same firmware state.

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

## Font-Sample Outcome Matrix

This matrix is the owner-level route for firmware-generated font sample pages.
The source bytes are not fetched from `0xa904`; ROM helpers synthesize row text
and then intentionally rejoin the ordinary printable/page-record/render path.

- No font records:
  entry `0x1c204` checks accepted resource count `0x78278e`. A zero count
  reports status `(0xe3, 0x51)` and produces no sample page objects.
- Sample setup:
  `0x1e0b2` prepares page/font state, clears copy/wrap/perforation state,
  forces sample-page VMI/HMI defaults in `0x783160` / `0x78315c`, initializes
  cursor/page state, and reaches printout entry `0x1c204`. This is canonical
  page/text setup state, not visible text by itself.
- Alternate sample setup:
  `0x1e8e6` checks the same accepted class-zero count `0x782798`, reports
  status `(0xe3, 0x51)` when it is zero, writes copy sentinel
  `0x782da4 = 0xffff`, clears wrap/perforation bytes `0x783190` /
  `0x783191`, runs `0x1d76c`, `0x10084`, and `0x1e9a0`, forces the same
  VMI/HMI defaults, starts cursor y at `0x0024`, and calls `0x1ea4e` with a
  row budget derived from `0x782db6 - 1`. It is an alternate setup route into
  the same sample-page generator, not a renderer.
- Source/class traversal:
  `0x1c28e..0x1c344` run class-zero and class-one passes, while
  `0x1c2fe..0x1c332` iterate source groups `0..3`. Per-source status bytes
  `0x783f02..0x783f05` record whether a source has no rows or has resumed
  after a prior pass. Empty groups produce heading-only page records or no
  row records according to the source fixture.
- Candidate resolution:
  `0x1b50e`, `0x1b750`, and `0x1b7b2` select candidate rows from first/second
  windows, fast probes, class filters, current-slot suppression, and Roman-8
  substitution. The result is selected context state for the row, not printable
  bytes until `0x1c5e8` and `0x1cabe` consume it.
- Selected context install:
  `0x1c5e8` installs the selected resource into current-font/page-root state,
  rebuilds maps through `0x14c64`, and refreshes page-root font slot state
  through `0xc428`. Later `0xd04a -> 0x1393a -> 0x12f2e` consumes those
  context slots exactly like host printable bytes.
- Source heading output:
  `0x1ca2c` selects labels from table `0x1c170`, writes row-height state
  `0x783f06`, checks page limit `0x782db6`, and emits heading text through
  printable helpers. The output is compact text bucket objects, not a direct
  bitmap.
- Row field output:
  `0x1cabe` emits row prefix, font name/style, pitch/height, symbol-set text,
  fixed-space gaps, and cursor advances. Helper cluster `0x1d198..0x1d79c`
  converts resource/name fields into sanitized printable bytes before
  `0xd04a` queues compact text objects.
- Sample run output:
  `0x1cf34` emits ROM sample run table `0x1c1cf`, may move to the alternate
  sample row, emits run table `0x1c1e9`, and writes the caller page-break flag
  at local `-6(A6)`. These bytes reach the same compact page-object path as
  the row fields.
- Continuation pages:
  `0x1ca2c`, `0x1d050`, `0x1d868`, and `0x1dcf2` compare projected row
  placement against page limit `0x782db6`. Continuation helper `0x1c9f6`
  creates fresh heading/source page records for the fixture-backed
  heading-preflight, cartridge heading, row-overrun, class-one row-overrun, and
  alternate-row cases.
- Publication and rendering:
  every visible sample byte rejoins `0xd04a -> 0x1393a -> 0x12f2e`, publishes
  page-record segments, bridges through `0x1ed84 -> 0x1edc6`, and renders
  through `0x1ef6a` compact text helpers. There is no font-sample-specific
  renderer.

State grouping for this matrix:

- Canonical sample state:
  candidate windows/counts `0x78278e`, `0x782798`, `0x782790`,
  `0x7827a0..0x7827b4`, current/alternate selected contexts, source labels
  at `0x1c170`, and run tables `0x1c1cf` / `0x1c1e9`.
- Canonical page/text state:
  page root, page-root context slots, cursor `0x782c8e`, page limit
  `0x782db6`, row-height word `0x783f06`, copy count/sentinel
  `0x782da4`, wrap/perforation bytes `0x783190` / `0x783191`, and VMI/HMI
  defaults `0x783160` / `0x78315c`.
- Derived/cache state:
  row-to-row y advance from `0x1d050`, alternate-row fit from `0x1d868`,
  multi-probe fit from `0x1dcf2`, and compact page-record/render bucket
  products created by the ordinary text renderer.
- Parser scratch:
  no host byte is fetched. The only parser-like scratch is the synthetic
  orientation record at `0x78299e` from `0x1d76c`; row text enters the
  printable path by direct calls to `0xd04a`.
- Firmware bookkeeping:
  per-source status bytes `0x783f02..0x783f05`, recent-context count/list
  `0x783f08` / `0x783f0a`, and local page-break word `-6(A6)`.
- Unknown:
  no ROM-local selected-resource, row-formatting, page-record, bridge, or
  render middle edge is unknown for the documented sample segments. Remaining
  unknowns are manual-facing names for baseline/cell fields and future
  continuation cross-products that create a different page-object form.

Evidence for this matrix is
`generated/disasm/ic30_ic13_font_sample_page_01c170.lst`,
`generated/disasm/ic30_ic13_font_sample_row_helpers_01d198.lst`,
`generated/disasm/ic30_ic13_font_page_setup_01e0b2.lst`,
`generated/disasm/ic30_ic13_font_page_setup_alt_01e8e6.lst`,
`generated/disasm/ic30_ic13_font_resource_object_lookup_01b4c0.lst`,
`generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`, and fixtures
`font sample source heading carries default plus first two Courier rows`,
`font sample built-in row fields format through 0x1cabe`,
`font sample full printout rows reuse ROM sample byte runs`,
`font sample full printout segments render through 0x1ed84 and 0x1ef6a`,
`font sample page-limit branches trigger continuation calls`, and
`font sample alternate-row continuation emits preadvanced row page record`.

## Reproduction Contract

A byte-stream-to-pixels renderer that also supports firmware-generated sample
pages must preserve:

- `0x1e0b2` setup side effects before `0x1c204` printing;
- `0x1e8e6` alternate setup side effects when that entry is used: copy
  sentinel `0xffff`, cleared wrap/perforation state, shared page/font helper
  chain, forced HMI/VMI, y cursor `0x0024`, and row budget from
  `0x782db6 - 1`;
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

## Evidence Boundary

The helper roles, loop order, candidate-row traversal, current-font setup,
printable byte emission, source `0..3` behavior, page-record placement,
rendered segment surfaces, and major forced-continuation object forms are tied
to the disassembly and named fixtures above. Manual-facing baseline/cell
terminology remains outside the ROM-local evidence currently documented here.

## Remaining Edges

- `0x1c334..0x1c5e4`: no unresolved middle edge remains for the normal
  source/class row traversal currently modeled. Additional forced-continuation
  streams should be treated as regression cross-products unless they expose a
  page-object form outside the covered heading-preflight, cartridge heading,
  internal class-zero row-overrun, internal class-one row-overrun, and
  alternate-row cases.
- `0x1c5e8..0x1ef6a`: selected resource setup, row formatting,
  printable-byte emission, page-record queueing, bridge, and render dispatch
  are documented for the composed segments. Remaining work is manual-facing
  naming of baseline/cell fields, not external row comparison.
- Record `+0x28/+0x2a`: consumed by `0x1519a` through `0x13bca` as decoded
  height inputs; manual-facing baseline/cell naming remains open.
- `0x1e8e6`: no ROM-local middle edge remains for the alternate setup route
  currently documented. It rejoins the same `0x1ea4e` sample-row budget path
  after its distinct copy sentinel and cursor/budget setup.
- Record `+0x2f..+0x31`: consumed by `0x1428c` after `0x14398` / `0x13c06`
  as same-class chooser tie-breakers; manual-facing names remain open.
