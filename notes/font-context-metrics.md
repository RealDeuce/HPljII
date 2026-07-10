# Font Context And Text Metrics Firmware

This note documents the bridge from font selection to the current-font context
records consumed by text queueing, span metrics, and compact glyph rendering.
It covers:

- active primary/secondary font selection through `0x13eb8`;
- selected context update through `0x144d2`;
- character-to-glyph map rebuild through `0x14c64`;
- page-root context-slot install through `0xc428` / `0xc4fc`;
- printable source capture through `0x1393a`;
- span-metric consumers `0xd4ac` and `0xd8fc`.

Evidence:

- `generated/disasm/ic30_ic13_payload_dispatch_011f82.lst`
- `generated/disasm/ic30_ic13_font_context_install_00c428.lst`
- `generated/disasm/ic30_ic13_font_update_common_00c580.lst`
- `generated/disasm/ic30_ic13_pitch_mode_handler_00c390.lst`
- `generated/disasm/ic30_ic13_font_candidate_activate_01569c.lst`
- `generated/disasm/ic30_ic13_active_object_dispatch_014ba4.lst`
- `generated/disasm/ic30_ic13_font_id_select_017708.lst`
- `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`
- `generated/analysis/ic30_ic13_font_context_bridge.md`
- `generated/analysis/ic30_ic13_text_glyph_index_flow.md`
- `tools/render_fixture_harness.py`, fixtures:
  - `0xc580 dirty primary branch installs page-root font context`
  - `0xc580 dirty secondary branch installs page-root font context`
  - `0xc580 full live-slot branch reuses matching page-root font context`
  - `0xc580 full live-slot branch skips install when c4fc reports full`
  - `0xc580 selector-mismatch branch refreshes candidate without context install`
  - `0xc580 dirty-2 selector-match branch installs current context only`
  - `0xc580 dirty-2 secondary selector-match branch installs current context only`
  - `0xc580 dirty-2 selector-mismatch branch only copies remembered word`
  - `0x13eb8 refresh carries parsed primary font selection to dispatch`
  - `0x13eb8 refresh carries parsed secondary font selection to dispatch`
  - `parsed primary built-in font selection feeds visible page-record rows`
  - `inline primary font selection stream renders visible rows`
  - `parsed secondary built-in font selection feeds visible SO page-record rows`
  - `inline secondary font selection stream renders SO visible rows`
  - `primary symbol miss falls back before visible page-record rows`
  - `remembered secondary symbol feeds visible SO page-record rows`
  - `parsed primary selection current-font RAM feeds SI visible rows`
  - `parsed secondary selection current-font RAM feeds SO visible rows`
  - `live primary current-font RAM install feeds SI page-record rows`
  - `live secondary current-font RAM install feeds SO page-record rows`
  - `secondary symbol miss falls back before visible SO page-record rows`
  - `font-ID built-in selection feeds visible page-record rows`
  - `font-ID secondary built-in selection feeds visible SO page-record rows`
  - `font-ID primary inline/downloaded selection feeds visible page-record rows`
  - `font-ID inline/downloaded selection feeds visible page-record rows`
  - `0x17708 font-ID non-selected exits preserve prior selection`
  - `font-ID non-selected exits keep prior visible rows`
  - `font-ID secondary non-selected exits keep prior SO visible rows`
  - `0x13eb8 transient and cache-hit exits avoid dispatch`
  - `0x13eb8 no-dispatch exits keep prior visible rows`
  - `0xe65c refresh composes with font context bridge`
  - `flagged printable d8fc low-watermark flush renders span`
  - `unflagged printable d4ac low-watermark flush renders span`
  - `d4ac and d8fc span consumer branch family controls flush output`
  - `host-fetched 0x1719c payload metrics feed d4ac span rows`
  - `host-fetched 0x1719c payload metrics feed d8fc span rows`
  - `host-fetched type-2 0x1719c payload metrics feed d4ac and d8fc span rows`
  - `host-fetched type-1 0x1719c payload metrics feed d4ac and d8fc span rows`
  - `host-fetched metric variant changes d4ac gate and d8fc rows`
  - `host-fetched clamped metric variant changes d4ac gate and d8fc rows`
  - `host-fetched lower-bound metric variant suppresses d4ac and d8fc spans`
  - `host-fetched upper-bound metric variant keeps d4ac span but suppresses d8fc`
  - `descriptor metric fields match across inline and resource contexts`
  - `legal descriptor metric value matrix drives d4ac and d8fc consumers`
  - `legal descriptor metric boundary values drive d4ac and d8fc consumers`
  - `legal descriptor metric extent fenceposts drive d4ac and d8fc consumers`
  - `legal descriptor metric range endpoints drive d4ac and d8fc consumers`
  - `legal descriptor metric mixed values drive d4ac and d8fc consumers`
  - `legal descriptor metric tight range values drive d4ac and d8fc consumers`
  - `legal descriptor metric low-nibble rounding drives d4ac and d8fc consumers`
  - `legal descriptor metric byte-boundary rounding drives d4ac and d8fc consumers`

## Owner Summary

This note owns the firmware bridge between parsed font-related commands and
text pixels. The parser handlers do not draw text. They update requested font,
symbol, pitch, or slot state; the refresh path chooses a primary or secondary
font resource; the selected resource is installed into current-font and
page-root context slots; printable bytes then consume those context slots to
queue compact text and update span bounds. Render-time code later copies the
page-root context into render records and resolves the stored glyph indices
into bitmap rows.

Primary routes:

- Parser font request route:
  font-attribute terminals and wrappers enter `0xc580`; compatibility
  pitch-mode handler `0xc390` first rewrites the active parser record and then
  calls `0xc89c -> 0xc580`.
  Alternate/data `ESC (s` / `ESC )s` reaches setup wrapper `0x11ff6`, but
  ordinary attribute terminal rows either have no handler or use lowercase
  rewind helper `0x11f4c`; they do not call the attribute writers or
  `0xc580`.
- Selection and map route:
  `0xc580 -> 0x13eb8 -> 0x14398 -> 0x144d2 -> 0x14c64 -> 0x14f16 -> 0x1440c`
  chooses a candidate, writes `0x782ee6` or `0x782ef6`, rebuilds
  `0x782f32` or `0x783032`, applies symbol-map patches, and writes selected
  snapshots.
- Page-root context route:
  `0xc580` or SI/SO handlers `0xc68a` / `0xc6b8` call `0xc428`, which calls
  `0xc4fc` to install the selected context under root `+0x2c..+0x68` and set
  selected page-root slot `0x78297e`.
- Printable route:
  `0xd04a -> 0x1393a -> 0xd140/0xd550 -> 0xd3b2/0xd824 -> 0x12f2e`
  converts one host printable byte into source fields at `0x782d7e` and then
  queues compact text through `0x1387c`.
- Span route:
  `0xd4ac` and `0xd8fc` consume selected glyph metric fields and update
  pending span state `0x783184..0x78318a`; later flush
  `0xf34a -> 0x12714 -> 0x126e2` turns that state into page records.
- Render route:
  publication `0xff1e` and bridge `0x1edc6` copy page-root font slots into
  render-record slots `+0x24..+0x60`; compact text dispatch
  `0x1ef6a -> 0x1efc2 -> 0x1effe -> 0x1f354` resolves the stored context,
  mapped glyph byte, and source-class flag to glyph bitmap data.

Canonical state:

- Selection/context: selected slot `0x782f06`, current-font records
  `0x782ee6` / `0x782ef6`, context fields `+0x00`, `+0x04`, and `+0x05`,
  selected candidate `0x7828a8`, and selected target `0x7828de`.
- Maps/symbols: maps `0x782f32` / `0x783032`, active symbol words
  `0x783144` / `0x783146`, remembered symbol words `0x782f08` / `0x782f0a`,
  and snapshots `0x783148` / `0x783152`.
- Page/render output: page-root context slots `+0x2c..+0x68`, live flags
  `0x78297f+n`, selected page slot `0x78297e`, render context slots
  `+0x24..+0x60`, active render context `0x783a2c`, and compact text objects
  under root `+0x1c`.
- Source/span state: source object `0x782d7e` fields
  `+0x00/+0x04/+0x0a/+0x0b/+0x10/+0x16`, pending span state
  `0x783184..0x78318a`, unflagged metrics `+0x2b/+0x2c/+0x2d`, and flagged
  metrics `+0x16/+0x18/+0x1a`.

Derived/cache state includes selected-font snapshots, transient probe record
`0x782992`, range flags `0x783132..`, and rebuilt maps. Parser scratch
includes `0x78299e`, request records, and the synthetic record written by
`0xc390`. Firmware bookkeeping includes dirty flags `0x782f2c/0x782f2d`,
active-object predicates, live-slot flags, and the `0xc4fc` full-root return.
No hardware/MMIO edge is involved in this owner; remaining uncertainty is
limited to the ROM-local routes listed in `Remaining Edges`.

Output effect:

- Font, symbol, pitch, SI/SO, and final-`X` commands have delayed pixel
  effects. They alter context, map, metric, or selected-slot state.
- Printable bytes, transparent/display paths, macro replay, or downloaded
  glyph paths are the consumers that create visible text objects.
- The original PCL font request is not what the renderer reads. The renderer
  reads page-root/render context slots, mapped glyph bytes, source-class flags,
  and resource or downloaded glyph records.

## Font Request Outcome Matrix

This matrix composes the delayed-output font request family from parsed command
handlers to later printable pixels. It covers multiple writers that share
common refresh `0xc580`, page-root context install `0xc428`, printable source
capture `0x1393a`, and compact render dispatch. It starts after parser
dispatch has reached the command-family handler and stops at the first
page-object producer or explicit no-output outcome.

- Font attribute writer:
  wrappers `0x12046`, `0x1206e`, `0x12082`, `0x12096`, `0x120aa`, and
  `0x1205a` route to attribute writers `0xc6ec`, `0xc780`, `0xc930`,
  `0xc89c`, `0xc840`, and `0xc7e0`. They write requested point, style,
  spacing, pitch, stroke, or typeface fields under the primary/secondary
  request block, then mark dirty flags `0x782f2c` / `0x782f2d`. The output
  effect is pending font state; no page object is queued.
- Alternate/data attribute boundary:
  in alternate/data mode, `ESC (s` / `ESC )s` uses parser wrapper `0x11ff6`.
  Uppercase ordinary attribute finals `B/H/P/S/T/V` are blank terminal rows,
  and lowercase ordinary finals `b/h/p/s/t/v` route only to `0x11f4c`.
  Neither path calls `0xc6ec`, `0xc780`, `0xc930`, `0xc89c`, `0xc840`,
  `0xc7e0`, or `0xc580`; requested font fields, dirty flags, current
  contexts, maps, page-root context slots, page objects, publication state,
  and render inputs remain unchanged. `W/w` is the exception and remains a
  downloaded-font delayed payload route through `0x11f96`, owned by
  [downloaded-fonts.md](downloaded-fonts.md#owner-summary).
- Pitch-mode compatibility writer:
  `0xc390` handles `ESC &k#S/s` selectors `0`, `2`, and `4` by rewriting the
  active parser record into synthetic pitch records and calling
  `0xc89c -> 0xc580`. Selector `0` performs two synthetic updates; selectors
  `2` and `4` perform one; all other selectors return through `0xc420`
  without changing pitch or refreshing font state.
- Symbol/font designation writer:
  `0x120be -> 0x1be22` writes requested symbol/default/font-id state, with
  detailed outcomes owned by the [Symbol/Font Designation Outcome
  Matrix](symbol-set-selection.md#symbolfont-designation-outcome-matrix).
  Its output joins the same `0xc580`, `0x13eb8`, `0x144d2`, `0x14c64`, and
  later printable path as ordinary font attributes.
- Common refresh:
  `0xc580` consumes dirty flags, selected text slot `0x782f06`, page-root live
  flags `0x78297f..0x78298e`, current contexts, and transient record
  `0x782992`. Dirty-1 selector matches can refresh and install; dirty-1
  selector mismatches refresh only; full-root paths may reuse or skip install;
  dirty-2 final-`X` selector matches install the already selected context
  without another `0x13eb8` refresh.
- Candidate, context, and map selection:
  `0x13eb8` filters candidates; `0x14398` selects a candidate slot;
  `0x144d2` writes current-font context `0x782ee6` or `0x782ef6`; `0x14c64`
  rebuilds map `0x782f32` or `0x783032`; `0x14f16` applies symbol-map patches;
  and `0x1440c` snapshots selected-font state. These are canonical or
  derived font state, not page objects.
- Page-root context install:
  `0xc428` selects primary or secondary context, and `0xc4fc` either reuses a
  matching root slot or installs the context under current page-root
  `+0x2c..+0x68`. It writes selected page-root slot `0x78297e`. The live flag
  is marked later by printable queueing, so a context install alone still has
  no pixels.
- Later printable object:
  `0xd04a -> 0x1393a` reads selected slot `0x782f06`, current context,
  active map, cursor state, and page-root context slot. It writes source
  fields under `0x782d7e`; `0xd3b2` or `0xd824` positions the source and marks
  the selected root slot live; `0x12f2e -> 0x1387c` queues compact text under
  page-root `+0x1c`. This is the first page-object output for the font request
  family.
- Span side effect:
  while printable bytes are placed, `0xd4ac` or `0xd8fc` can update pending
  span state from selected context metrics. A later flush through
  `0xf34a -> 0x12714 -> 0x126e2` turns that state into segment-list or
  fixed-list page objects.
- Render consumer:
  publication `0xff1e`, bridge `0x1edc6`, and render entry `0x1ef6a` carry
  compact text and copied context slots to `0x1effe -> 0x1f354`. The renderer
  consumes the captured mapped glyph byte plus copied context slot; it does
  not re-run the original PCL font request.

State classification for this matrix:

- Canonical state:
  requested font fields under the primary/secondary request blocks, selected
  slot `0x782f06`, current contexts `0x782ee6/0x782ef6`, selected maps
  `0x782f32/0x783032`, page-root context slots, source record `0x782d7e`,
  compact text objects, and span objects emitted by `0x12714`.
- Derived/cache state:
  selected candidate `0x7828a8`, selected target `0x7828de`, transient context
  `0x782992`, selected-font snapshots `0x783148/0x783152`, map flags
  `0x783132..`, HMI `0x78315c`, compact coordinates, pending span bounds, and
  render-band fields after publication.
- Parser scratch:
  command records at `0x78299e`, synthetic pitch records written by `0xc390`,
  symbol/designation setup records, parsed integer/fraction fields, and the
  cursor advances that let shared writers consume synthetic records.
  Alternate/data `ESC (s` / `ESC )s` records that end at blank or `0x11f4c`
  terminal rows are parser scratch only; they do not become canonical font
  request state.
- Firmware bookkeeping:
  dirty flags `0x782f2c/0x782f2d`, page-root live flags
  `0x78297f..0x78298e`, transient full-root flag `0x78298f`, `0xc4fc`
  full-status result, publication flag `0x782996`, and scheduler progress
  after a page is published.
- Hardware/external state:
  none after the byte stream has reached these ROM handlers. Optional
  resource-window contents can change candidate records but not the documented
  writer/refresh/printable control flow.
- Unknown:
  no ROM-local output edge remains for the documented font-attribute,
  pitch-mode, symbol/designation, SI/SO, final-`X`, current-RAM handoff, or
  span-metric paths. New work must change a concrete refresh branch, selected
  context/map, source field, page-root object, bridge slot, or render helper
  input.

Evidence:
`generated/disasm/ic30_ic13_payload_dispatch_011f82.lst`,
`generated/disasm/ic30_ic13_font_update_common_00c580.lst`,
`generated/disasm/ic30_ic13_font_context_install_00c428.lst`,
`generated/disasm/ic30_ic13_font_candidate_activate_01569c.lst`,
`generated/disasm/ic30_ic13_pitch_mode_handler_00c390.lst`,
`generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`,
`generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`,
[Symbol/Font Designation Outcome
Matrix](symbol-set-selection.md#symbolfont-designation-outcome-matrix), and
fixtures named in this note's Evidence list.

## Concept

The firmware does not render text directly from the current PCL font request.
It first chooses a primary or secondary resource candidate, writes the selected
candidate longword into a current-font context record, rebuilds a 256-byte
host-character-to-glyph map, installs the context record into a page-root
font slot, and only then lets printable bytes create page objects.

The same selected resource record also supplies the metric bytes used by
`0xd4ac` and `0xd8fc` to extend pending text-span bounds. These span metrics
are visible because they determine the segment-list or fixed-width span that
is eventually rendered by `0x1f812` or `0x1f756`.

## Field Groups

Canonical selection state:

- `0x782f06`: selected text slot byte, `0` for primary and nonzero for
  secondary. It chooses the map/context pair used by `0x1393a`, and is also
  the argument family for `0xc428`.
- `0x782ee6`: primary current-font context record.
- `0x782ef6`: secondary current-font context record.
- context record `+0x00`: selected resource/candidate longword.
- context record `+0x04`: selected-resource class flag derived from bit 30
  by `0x144d2`; nonzero means offset-table/built-in style.
- context record `+0x05`: adjacent flag derived from bit 26 by `0x144d2`.

Canonical glyph maps:

- `0x782f32`: primary 256-byte host-character-to-glyph map.
- `0x783032`: secondary 256-byte host-character-to-glyph map.
- `0x783144`: primary active symbol-set word.
- `0x783146`: secondary active symbol-set word.
- `0x782f08`: remembered primary symbol-set word.
- `0x782f0a`: remembered secondary symbol-set word.

Canonical selected-font snapshots:

- `0x783148`: primary selected-resource snapshot written by `0x1440c` and
  compared by `0x13a48`.
- `0x783152`: secondary selected-resource snapshot written by `0x1440c` and
  compared by `0x13a48`.
- Snapshot byte `+0`: record form, `1` for bit-30 offset-table/resource
  records and `0` for bit-30-clear inline/downloaded records.
- Snapshot word `+0x02`: selected symbol word returned by `0x15890` or
  `0x158be` when the map was last rebuilt.
- Snapshot word `+0x04`: active symbol word copied from `0x783144` or
  `0x783146`.
- Resource snapshot bytes `+0x06/+0x07`: copies of selected resource record
  words `+0x0e/+0x10` truncated to bytes by `0x1440c`.
- Inline/downloaded snapshot byte `+0x08`: copy of selected inline record
  byte `+0x0e` by `0x1440c`.
- Snapshot byte `+0x09`: ROM/RAM provenance flag. `0x1440c` writes `1` when
  the selected record address is below `0x780efa`, otherwise `0`.

Canonical page-root/render context fields:

- page root `+0x2c..+0x68`: 16 font context slots. These hold selected
  context/resource longwords copied from current-font records, not pointers to
  the `0x782ee6` / `0x782ef6` records themselves.
- `0x78297e`: selected page-root font slot written by `0xc428`.
- `0x78297f+n`: live flag for page-root font slot `n`.
- render record `+0x24..+0x60`: copy of the 16 page-root context slots
  created by `0x1edc6`.
- `0x783a2c`: active compact-glyph render context loaded from a render-record
  slot before `0x1f354` resolves glyph data.

Canonical printable source fields:

- source `+0x00`: selected context/resource longword copied by `0x1393a`.
- source `+0x04`: glyph-entry pointer or fixed-record pointer computed by
  `0x1393a`.
- source `+0x0a/+0x0b`: mapped glyph word/byte; byte `+0x0b` is copied into
  compact payload entries by `0x12f2e`.
- source `+0x10`: context flag byte copied by `0x1393a`; nonzero selects the
  flagged path `0xd550` / `0xd824` / `0xd8fc`, zero selects the unflagged path
  `0xd140` / `0xd3b2` / `0xd4ac`.
- source `+0x16`: page-root font slot copied from `0x78297e` by `0xd3b2` or
  `0xd824`.

Canonical span-metric consumers:

- unflagged record `+0x2b`: alternate y offset consumed by `0xd4ac`.
- unflagged record `+0x2c`: lower y bound consumed by `0xd4ac`.
- unflagged record `+0x2d`: height / page-extent contribution consumed by
  `0xd4ac`.
- flagged record `+0x16`: lower y bound consumed by `0xd8fc`.
- flagged record `+0x18`: height / page-extent contribution consumed by
  `0xd8fc`.
- flagged record `+0x1a`: alternate y offset consumed by `0xd8fc`.

Parser-produced downloaded-font metric fields:

- `0x16fae..0x17016` reads a 32-entry descriptor table at `0x16eae` and
  writes staged fields under `0x782862`; `0x1719c..0x1725c` copies those
  staged fields into the allocated `0x1719c` payload. The table readers are
  `0x1599c` unsigned byte, `0x159b6` signed byte, `0x159d4` unsigned word,
  and `0x159f6` signed word.
- Canonical producer fields for the covered metric family are
  `+0x16` first code/lower bound, `+0x14` range/count, and `+0x1a` signed
  flagged offset. `0x17430..0x1749c` writes `+0x14` and derives/cache
  `+0x18 = +0x14 - +0x16 - 1`; `0x1762a..0x1763c` writes the signed-byte
  offset result into word `+0x1a`.
- Derived unflagged field `+0x2c` is written by `0x1757a..0x175b8` as
  `min((value + 2) >> 2, word(+0x14)) << 2`. Fixtures
  `legal descriptor metric boundary values drive d4ac and d8fc consumers`,
  `legal descriptor metric range endpoints drive d4ac and d8fc consumers`, and
  `legal descriptor metric low-nibble rounding drives d4ac and d8fc consumers`
  prove the cap, derived-height endpoints, and rounding outcomes through
  visible `0xd4ac` and `0xd8fc` rows.
- Parser scratch for this producer path is the staged base `0x782862`,
  validation cursor, payload budget `0x783140`, and optional symbol staging
  `0x782842..0x782856`. Firmware bookkeeping includes type byte `+0x0c`,
  allocation units `0x7827ba`, and byte `+0x2b`, which remains `0` in the
  covered `0x1719c` metric fixtures.

Derived/cache state:

- `0x7828de`: selected primary/secondary target used by `0x144d2` and
  `0x14c64`.
- `0x7828a8`: selected candidate slot pointer used by `0x144d2`,
  `0x14c64`, and `0x1440c`.
- `0x782992`: transient selected context record used by `0xc580` when a
  page root is full or needs a pre-refresh context probe.
- `0x783132` / `0x783133`: primary/secondary selected-font flags maintained
  during map rebuild.
- `0x783134` / `0x78313a`: primary/secondary mapped character ranges.

Parser scratch:

- `0x78299e`: command-record cursor rewound by font request/update handlers
  such as `0xc580`, `0x15a56`, and `0x15a18`.
- `ESC &k#S/s` pitch-mode handler `0xc390` treats the active parsed record
  as scratch: it reads the absolute selector from the previous record word,
  rewrites record words `+2/+4` with a synthetic pitch value, advances
  `0x78299e` to let `0xc89c` read that synthetic record, and then refreshes
  through `0xc580`.
- For selector `0`, `0xc390` synthesizes pitch `10.0000`; for selector `2`,
  pitch `16.6600`; for selector `4`, pitch `12.0000`. The jump table at
  `0xc370` falls through to `0xc420` for other selectors without calling
  `0xc89c` or `0xc580`.

Unknown:

- The bridge from selected context records to span metrics is documented for
  concrete built-in, synthetic inline/downloaded, and host-fetched `0x1719c`
  downloaded payload fixtures for both `0xd4ac` and `0xd8fc`. The
  producer-form boundary is now fixture-backed: inline/unflagged feeds
  `0xd4ac`, resource/flagged feeds `0xd8fc`, and the swapped forms fail at
  concrete map/render boundaries. Broader legal metric values are documented
  as cross-products of those producer formulas and consumer gates; remaining
  work is regression breadth for additional selected-font state combinations
  and validation/error forms beyond the bounded predicate and short-budget
  no-install cases.

## Writers

Font selection reaches this owner through parser terminal handlers, but the
parser table is only the route into the state machine. The semantic writers
are the handlers that update requested font fields, choose a current context,
rebuild maps, install page-root slots, or create source objects:

- Parser font-request writers:
  lowercase and uppercase font-attribute terminals update the requested font
  state before the common refresh. The covered primary stream
  `ESC (s0p10h12v0s0b3T` writes through `0xc930`, `0xc89c`, `0xc6ec`,
  `0xc780`, `0xc840`, and uppercase wrapper `0x1205a`; sibling wrappers
  `0x12046`, `0x1206e`, `0x12082`, `0x12096`, and `0x120aa` have the same
  single-attribute-plus-refresh shape.
- Pitch-mode compatibility writer:
  `0xc390` handles `ESC &k#S/s` selectors `0`, `2`, and `4` by rewriting the
  active six-byte parser record into synthetic pitch records, then calling
  `0xc89c -> 0xc580`. Other selectors exit through `0xc420` without a refresh.
- Common refresh writer:
  `0xc580` consumes dirty flags `0x782f2c/0x782f2d`, selected slot
  `0x782f06`, current contexts `0x782ee6/0x782ef6`, page-root live flags
  `0x78297f..`, and transient record `0x782992`. Depending on those fields,
  it calls candidate refresh `0x13eb8`, context installer `0xc428`, both, or
  neither.
- Candidate and map writers:
  `0x13eb8` filters candidate windows, `0x14398` writes selected slot pointer
  `0x7828a8`, `0x144d2` copies the selected candidate longword into
  `0x782ee6` or `0x782ef6`, `0x14c64` rebuilds glyph map `0x782f32` or
  `0x783032`, `0x14f16` patches Roman-8-compatible maps, and `0x1440c` writes
  selected-font snapshots `0x783148` or `0x783152`.
- Font-ID and active-object writers:
  `0x17708` implements final-`X` selection and either reaches the same
  `0x14c64` map rebuild path or exits without changing the prior selected
  context. Predicate helper `0x14ba4..0x14c5c` only classifies active-object
  compatibility; it writes no map or page object.
- Page-root context writers:
  SI/SO handlers `0xc68a` and `0xc6b8` select primary or secondary slot
  through `0xc428(0/1)`. `0xc4fc` chooses or reuses a page-root context slot,
  writes the selected context longword into root `+0x2c..+0x68`, sets live flag
  `0x78297f+n`, and updates selected page-root slot byte `0x78297e`.
- Printable source writers:
  printable handler `0xd04a` calls `0x1393a`, which writes source object
  `0x782d7e` from the selected context and glyph map. The unflagged path
  `0xd140 -> 0xd3b2` or flagged path `0xd550 -> 0xd824` writes positioned
  source fields and passes the source object to `0x12f2e`.
- Span-metric writers:
  `0xd4ac` consumes unflagged metric fields `+0x2b/+0x2c/+0x2d`; `0xd8fc`
  consumes flagged metric words `+0x16/+0x18/+0x1a`. They update pending span
  state `0x783184..0x78318a`, which later flushes through `0x12714`.
- Downloaded metric producers:
  `0x16fae..0x17016`, `0x1719c..0x1725c`, `0x17430..0x1749c`,
  `0x1757a..0x175b8`, and `0x1762a..0x1763c` stage and copy descriptor metric
  fields into downloaded payload records. Those records become metric inputs
  when later selected contexts route printable bytes to `0xd4ac` or `0xd8fc`.

## Readers And Consumers

The main consumers are printable text, span flush, publication, and compact
rendering. A font command has no complete output path until one of those later
consumers reads the selected state.

- Parser dispatch consumers:
  [pcl-command-map.md](pcl-command-map.md) maps font-selection, symbol-set,
  final-`X`, pitch-mode, SI/SO, and downloaded-font parser handlers into this
  note. Its matrix is the address index; this file owns what those handlers
  do to font state and how later bytes consume it.
- Printable source consumer:
  `0xd04a -> 0x1393a` reads selected slot `0x782f06`, current context
  `0x782ee6` or `0x782ef6`, active map `0x782f32` or `0x783032`, cursor
  state, and the page-root context slot installed by `0xc428`. It outputs
  source fields `+0x00/+0x04/+0x0b/+0x10/+0x16` that `0x12f2e` turns into
  compact text objects.
- Span consumers:
  `0xd4ac` and `0xd8fc` read selected glyph metrics while printable bytes are
  being placed. Their output is pending span state, not immediate pixels; the
  later flush path `0xf34a -> 0x12714 -> 0x126e2` creates segment-list or
  fixed-list page objects.
- Page-root and bridge consumers:
  `0x12f2e -> 0x1387c` writes compact text entries under page-root `+0x1c`,
  carrying the page-root font slot number. Publication `0xff1e` snapshots the
  root, and bridge `0x1edc6` copies page-root context slots
  `+0x2c..+0x68` into render-record slots `+0x24..+0x60`.
- Compact renderer consumers:
  `0x1ef6a -> 0x1efc2 -> 0x1effe` dispatches compact text. Resolver `0x1f354`
  reads the copied render context slot, mapped glyph byte, source-class flag,
  and glyph/fixed-record pointer to derive bitmap rows from built-in resource
  records or downloaded/current records.
- Cache and skip consumers:
  `0x13a48` reads selected-font snapshots to decide whether map rebuild can be
  skipped. `0x14ba4` reads active-object signatures to decide whether an
  existing selected object remains compatible. These exits preserve prior
  visible rows only because later printable bytes keep consuming the already
  installed context/map.

## Output Effect

Font-selection, symbol-set, pitch-mode, and final-`X` commands are delayed
pixel effects. They do not queue compact objects on their own. They change the
context and map that a later printable byte, transparent/display reader, macro
replay, or downloaded-glyph path consumes.

Concrete output paths are documented by the existing fixtures and listings:

- Built-in primary stream `ESC (s0p10h12v0s0b3T!!` selects context
  `0xc008004c`, rebuilds primary map `0x782f32`, derives HMI `30`, and queues
  compact object
  `00 00 00 00 00 00 00 02 00 6a 00 00 68 02` through
  `0xd04a -> 0x1393a -> 0x12f2e -> 0x1387c`.
- Built-in secondary stream `ESC )s0p16h8v0s0b0T SO !!` selects context
  `0xc00ae122`, rebuilds secondary map `0x783032`, crosses SO handler
  `0xc6b8`, and queues compact object
  `00 00 00 00 00 01 00 02 00 c9 00 00 cb 01`.
- Final-`X` streams such as `ESC (7X!!` and `ESC )8X SO !!` enter helper
  `0x17708`; success selects a concrete candidate and rebuilds the selected
  map, while scan-miss, candidate-miss, class-mismatch, and context-full exits
  deliberately preserve the prior selected context for the following
  printable bytes.
- Pitch-mode streams only affect output after `0xc390 -> 0xc89c -> 0xc580`
  changes selected-font/HMI state and later printable bytes consume the
  refreshed context.
- Span-metric streams affect pixels when `0xd4ac` or `0xd8fc` expands pending
  span bounds and a later flush queues a segment-list or fixed-list object.
- Downloaded metric streams affect pixels only after a selected downloaded
  context makes printable bytes consume the installed payload record and its
  metric fields.

The pixel-producing boundary for all of these paths is the same compact text
and span route used by ordinary printable bytes: page-root objects are
published through `0xff1e`, context slots are copied by `0x1edc6`, and render
entry `0x1ef6a` dispatches compact, segment-list, or fixed-list helpers.

## Remaining Edges

No ROM-local middle edge remains for the covered primary/secondary built-in
selection streams, primary/secondary symbol fallback and remembered-symbol
streams, final-`X` built-in and inline/downloaded success paths, final-`X`
non-selected exits, final-`@` default-table streams, pitch-mode selectors
`0/2/4`, live current-font-RAM SI/SO handoff, or the documented `0xd4ac` and
`0xd8fc` span-metric producer/consumer paths.

Remaining font-context work should start only from byte streams or selected
records that change one of these concrete boundaries: `0xc580` refresh
decision, `0x13eb8` candidate filters, `0x14398` selected slot pointer,
`0x14c64` map rebuild/cache decision, `0x14f16` map patch, `0x17708` final-`X`
exit, `0xc428` page-root context slot install, `0x1393a` source-class fields,
span-metric consumers `0xd4ac` / `0xd8fc`, page-root object bytes, bridge
context slots, or compact-renderer glyph source inputs.

## Pitch Mode Command

`ESC &k#S/s` is a compatibility pitch-mode command, not an independent
metric store. Handler `0xc390` reads the absolute selector from the parsed
record behind `0x78299e`, dispatches through the table at `0xc370`, and for
selectors `0`, `2`, or `4` rewrites the active parser record into the same
numeric form consumed by the normal pitch handler `0xc89c`.

Selector effects:

| Selector | Synthetic pitch record | Writer path |
| ---: | --- | --- |
| `0` | integer `10`, fraction `0` | `0xc390 -> 0xc89c -> 0xc580` |
| `2` | integer `16`, fraction `0x19c8` | `0xc390 -> 0xc89c -> 0xc580` |
| `4` | integer `12`, fraction `0` | `0xc390 -> 0xc89c -> 0xc580` |
| other | unchanged | default exit `0xc420` |

The extra record manipulation in the selector-`0` path matters for
reproduction. After writing `10.0000`, `0xc390` clears an adjacent synthetic
record word, calls `0xc89c` and `0xc580`, then writes word `1` into the next
record and calls the same pair again after advancing `0x78299e` by `0x0c`.
Selectors `2` and `4` take only the first synthetic-record path. The visible
effect is therefore still the same selected-font refresh pipeline documented
below: changed pitch state can alter candidate selection, HMI, printable
cursor advance, page-root context slots, and rendered compact text rows only
after `0xc580` lets the updated font request reach `0x13eb8` and `0xc428`.

Instruction boundaries:

- `0xc398..0xc3b4` opens the parsed command cursor `0x78299e`, reads selector
  word `-4(A5)`, folds negative values positive, and dispatches the absolute
  selector through jump table `0xc370`.
- `0xc3ba..0xc404` is selector `0`: it writes synthetic pitch integer
  `10` and fraction `0` into the active record at `+2/+4`, clears word
  `0x78299e - 10`, advances `0x78299e` by six bytes, calls
  `0xc89c -> 0xc580`, writes word `1` into the next synthetic record,
  advances `0x78299e` by `0x0c`, and calls `0xc89c -> 0xc580` again.
- `0xc406..0xc412` is selector `2`: it writes synthetic pitch integer
  `16` and fraction `0x19c8`, then falls into the shared
  `0xc3c4 -> 0xc89c -> 0xc580` path.
- `0xc414..0xc41e` is selector `4`: it writes synthetic pitch integer
  `12` and fraction `0`, then falls into the same shared path.
- `0xc420..0xc426` is the default/nonselected exit. Selectors other than
  `0`, `2`, or `4` restore registers and return without calling the pitch
  writer or common refresh.

The common refresh boundary that pitch mode rejoins is `0xc580..0xc686`.
`0xc580` rewinds `0x78299e` by one six-byte record before testing dirty byte
`0x782f2c`; if no dirty state is pending it exits at `0xc5c2`. Otherwise it
uses the record selector word `+2`, validates selector `0` or `1`, and takes
the same branch cluster used by ordinary font-selection commands: selected-slot
match can call `0xc428`, selected-slot mismatch can call `0x13eb8`, existing
page-root/live-font state can force `0x13eb8` with transient byte `0x78298f`,
and fallback scan can call `0xc4fc`, `0x13eb8`, and `0xc428`. The final
`0xc666..0xc680` copy updates remembered word table `0x782f08` from
`0x783144` and clears dirty byte `0x782f2c`.

Field classification for this pitch-mode bridge:

- Canonical state: pitch request word `0x782ef0 + 0x10*slot`, selected slot
  `0x782f06`, current font context records `0x782ee6` / `0x782ef6`, selected
  maps `0x782f32` / `0x783032`, page-root context slots, and later compact
  text objects created by `0xd04a`.
- Derived/cache state: synthetic record integer/fraction words, selected
  candidate pointer `0x7828a8`, selected target `0x7828de`, transient context
  record `0x782992`, HMI `0x78315c`, compact coordinates, and render-band
  fields after publication.
- Parser scratch: the original six-byte `ESC &k#S/s` record, the mutated
  synthetic pitch records, and `0x78299e` cursor advances used only to make
  `0xc89c` consume those synthetic records.
- Firmware bookkeeping: dirty bytes `0x782f2c` / `0x782f2d`, transient
  refresh byte `0x78298f`, page-root live-font flags, `0xc4fc` slot-scan
  state, publication flag `0x782996`, and render scheduler progress.
- Hardware/external state: none after the host byte stream has reached parser
  dispatch.
- Unknown: no ROM-local pitch-mode parser, writer, refresh, or printable
  handoff edge remains for selectors `0`, `2`, and `4`. New work should start
  only from a byte stream whose surrounding font state changes `0xc580` branch
  choice, selected context/map, HMI, compact object shape, bridge state, or
  ROM-derived rows.

Evidence:

- `generated/disasm/ic30_ic13_pitch_mode_handler_00c390.lst`: handler body
  `0xc390..0xc426`.
- `generated/disasm/ic30_ic13_font_update_common_00c580.lst`: common refresh
  body `0xc580..0xc686`, including `0xc428`, `0xc4fc`, and `0x13eb8` branch
  calls.
- ROM table bytes at firmware address `0xc370`:
  `0000 c414 0000 0004 0000 c406 0000 0002
  0000 c3ba 0000 0000 0000 0000 0000 c420`.
  These encode jump-table entries `0xc414 <- 4`, `0xc406 <- 2`,
  `0xc3ba <- 0`, and default `0xc420`.
- `notes/semantic-state-model.md`: `Built-In Font Selection To Visible Text`
  field groups and writer/consumer model for `0xc89c` and `0xc580`.

## Selection And Map Rebuild

`0x13eb8` is the high-level refresh path for a primary or secondary font slot.
The primary fixture for parsed request `0p10h12v0s0b3T` follows this call
sequence:

```text
0x148f8 -> 0x1569c -> 0x156de -> 0x153c6 -> 0x1519a
-> 0x147b2 -> 0x14758 -> 0x14398 -> 0x144d2 -> 0x14c64
```

Fixture-pinned primary result:

- symbol survivors: `0x782354`, `0x782364`, `0x782374`;
- spacing/pitch survivors: `0x782354`, `0x782364`;
- height survivors: `0x782354`, `0x782364`;
- stroke filter keeps slot `0x782354`;
- selected longword: `0xc008004c`;
- selected record start: `0x00004c`;
- `0x144d2` writes context record `0x782ee6`;
- `0x14c64` rebuilds map `0x782f32`;
- map range: `0x21..0xfe`;
- patch kind: unchanged.

The secondary fixture for parsed request `0p16h8v0s0b0T` follows:

```text
0x148f8 -> 0x1569c -> 0x156de -> 0x153c6
-> 0x14398 -> 0x144d2 -> 0x14c64
```

Fixture-pinned secondary result:

- symbol survivors: `0x782330`, `0x782340`, `0x782350`;
- nearest-pitch filter keeps slot `0x782350`;
- selected longword: `0xc00ae122`;
- selected record start: `0x02e122`;
- `0x144d2` writes context record `0x782ef6`;
- `0x14c64` rebuilds map `0x783032`;
- map range: `0x21..0xff`;
- patch kind: selected symbol is not Roman-8.

### Candidate Attribute Filters

`0x1519a..0x1562c` is the attribute-pruning cluster between symbol-set
filtering and final candidate choice. It consumes the active candidate window
created by `0x1569c` and narrowed by `0x156de`; it has no direct pixel output,
but it changes which font record `0x14398` can select and therefore changes
the context copied by `0x144d2`, the character map rebuilt by `0x14c64`, and
the glyph rows reached by later printable bytes.

Height filtering is driven by `0x1519a`:

- `0x151a0..0x151b6` selects requested height from canonical primary field
  `0x782ef2` or secondary field `0x782f02`, using selected slot flag
  `0x7828de`.
- `0x151ba..0x151cc` builds a derived inclusive tolerance window of
  requested height +/- `0x19`, clamped to `0x0000..0xffff`.
- `0x151f0` tests whether any active candidate has a decoded height inside
  that window. Bit-30 candidate records decode height through `0x13bca` from
  record word `+0x28` and byte `+0x2a`; bit-30-clear records read word
  `+0x20`.
- If the test succeeds, `0x15246` is the range pruner. It keeps candidates
  inside the window, clears active bit 7 in rejected list entries, writes the
  retained count to `0x7827b8`, and moves `0x78287c` to the first survivor.
- If no candidate is inside the window, `0x1533e` scans the same decoded
  heights and returns nearest lower and/or upper exact bounds in `D1/D2`.
  `0x152c2` then keeps only candidates whose height equals either returned
  bound and performs the same active-bit, pointer, and count updates.

Spacing and pitch filtering are driven by `0x153c6`:

- `0x153ca..0x153e2` selects requested spacing from canonical primary field
  `0x782eef` or secondary field `0x782eff`.
- `0x15456` tests for a candidate with that spacing. Bit-30 records read byte
  `+0x21`; bit-30-clear records read byte `+0x19`.
- `0x15488` is the spacing pruner. It keeps candidates with matching spacing,
  clears active bit 7 in rejected entries, then writes `0x7827b8` and
  `0x78287c`.
- The wrapper treats requested spacing `1` specially: when no matching
  spacing exists it skips pitch filtering, while a matching spacing is pruned
  and exits. For other spacing requests, no match exits with no
  spacing/pitch pruning; a match prunes spacing and then continues into pitch.
- `0x15406..0x1542e` selects requested pitch from `0x782ef0` or `0x782f00`
  and builds a derived inclusive tolerance window of pitch +/- `5`, clamped
  to `0x0000..0xffff`.
- `0x154e4` tests whether any active candidate has comparable pitch inside
  that window. Bit-30 records decode pitch through `0x13b76` from record word
  `+0x24` and byte `+0x26`; bit-30-clear records read word `+0x1a`.
- If the pitch test succeeds, `0x1553a` prunes to candidates inside the pitch
  window and updates `0x7827b8` / `0x78287c`.
- If no pitch is inside the window, `0x1562c` chooses the nearest exact pitch
  value used by `0x155b6`. The selector tracks the largest pitch at or below
  the request and the smallest pitch above it; the observed return path
  prefers the upper value when present, otherwise the lower value.

State classification for this cluster:

- Canonical request state: `0x782ef2` / `0x782f02` height,
  `0x782eef` / `0x782eff` spacing, and `0x782ef0` / `0x782f00` pitch.
- Canonical candidate state: active window pointer/count `0x78287c` /
  `0x7827b8`, active bit 7 in each list entry, and record fields
  `+0x28/+0x2a` or `+0x20` height, `+0x21` or `+0x19` spacing, and
  `+0x24/+0x26` or `+0x1a` pitch.
- Derived/cache state: the height and pitch tolerance windows and nearest
  fallback bounds returned by `0x1533e` and `0x1562c`.
- Firmware bookkeeping: rejected-entry active-bit clears plus rewritten
  active pointer/count after each pruning pass.
- Unknown: manual-facing names for the two candidate record layouts remain
  unresolved; the ROM-local use of each field above is pinned by
  `generated/disasm/ic30_ic13_font_candidate_filters_01519a.lst`.

The primary and secondary fixtures above exercise both range and fallback
outcomes. Primary height and pitch requests keep candidates in range before
stroke/typeface selection. Secondary selection reaches the nearest-pitch path
and keeps slot `0x782350`. The unresolved boundary after this cluster is not
inside `0x1519a..0x1562c`; it is the next consumer boundary at
`0x14398..0x14406`, where filtered survivors are ranked and written to
selected candidate pointer `0x7828a8`.

### Active Candidate Chooser

`0x14398` is the selection boundary between filtered candidate windows and the
current-font context record that printable bytes later use:

- The filtered window enters as pointer `0x78287c` and count `0x7827b8`.
  Filter stages `0x1569c`, `0x156de`, `0x153c6`, `0x1519a`, `0x147b2`, and
  `0x14758` have already cleared the active bit on rejected candidate slots
  and shrunk the window.
- `0x143a0..0x143b6` reports status `(0xe7, 0x36)` through `0x1284` when the
  active count is zero. The covered visible streams enter the chooser with a
  nonzero count.
- `0x143b8..0x143f8` walks longword slots from `0x78287c`, treating negative
  longwords as active survivors. The first active survivor seeds the current
  best slot in `A4`.
- `0x143d8..0x143f4` compares each later active survivor against the current
  best by calling `0x13c06(challenger, best)`. When that comparator returns
  `D7 = 1`, the challenger replaces the current best.
- `0x143fa..0x14406` writes the winning slot pointer to `0x7828a8`.

Comparator `0x13c06` classifies both records by address window and, for
same-class records, delegates tie-breaking through `0x1428c`. The tie-breaker
inputs include decoded height and candidate bytes `+0x2f..+0x31`, as composed
in [semantic-state-model.md](semantic-state-model.md). The chooser's output is
canonical selected-font state: `0x144d2` copies the selected longword from
`0x7828a8` into current-font record `0x782ee6` or `0x782ef6`, and `0x14c64`
rebuilds the selected character map consumed by later `0xd04a` printable
bytes. A different `0x7828a8` therefore changes the selected context slot,
mapped glyph byte, compact object, and rendered text rows.

The same-class tie-breaker is now resolved to helper bodies:

- `0x13c06` masks each candidate longword to a 24-bit record address and
  assigns a resource class: `0x080000..0x0ffffd`, then
  `0x200000..0x5ffffd`, then RAM/downloaded range
  `0x780efa..0x7810b3`. A challenger with a higher class returns `D7 = 1`
  and replaces the current best; a lower class returns `D7 = -1`.
- When both records are bit-30 offset-table form, `0x1428c` compares
  challenger versus best by decoded height from `0x13bca(+0x28,+0x2a)`,
  then unsigned byte `+0x2f`, signed byte `+0x30`, and unsigned byte
  `+0x31`.
- When both records are bit-30-clear fixed form, `0x13fc6` compares word
  `+0x20`, unsigned byte `+0x26`, signed byte `+0x27`, and unsigned byte
  `+0x18`.
- When challenger is fixed form and current best is offset-table form,
  `0x140a4` maps fixed fields `+0x20/+0x26/+0x27/+0x18` against
  offset-table fields decoded height, `+0x2f`, `+0x30`, and `+0x31`.
- When challenger is offset-table form and current best is fixed form,
  `0x14198` uses the same field mapping in the opposite direction.

All four helpers return `D7 = 1` when the challenger tuple is greater,
`D7 = -1` when it is smaller, and `D7 = 0` when the tuple is equal. The
generated evidence window is
`generated/disasm/ic30_ic13_object_compare_helpers_013fc6.lst`; the checked-in
generator window is in `tools/generate_rom_artifacts.py`.

`0x14c64` chooses the map-building path from the selected context form:

- bit-30 set / offset-table form: rebuilds a base range through `0x14d9c`,
  then applies `0x14f16` symbol-set patching and `0x1440c` state snapshot.
- bit-30 clear / fixed-record form: rebuilds through `0x14e24` and
  `0x14eb6`, then applies the same `0x14f16` / `0x1440c` tail.

For bit-30 offset-table records, `0x14d9c..0x14e10` is the base-map builder.
It selects primary map `0x782f32` or secondary map `0x783032` from
`0x7828de`, reads selected record words `+0x0e` and `+0x10` through
`0x7828a8`, and treats them as inclusive first and last character codes. It
zeros every map byte before the first code, writes sequential glyph indexes
`0, 1, 2, ...` from first through last, then zeros every byte after the last
code through `0xff`. If the last word is below the first word, the helper
reports error/status `(0xe7, 0x91)` through `0x128c` at `0x14e12..0x14e1e`.
The resulting map is derived/cache state: `0x1393a` later consumes the map to
turn a host byte into a compact glyph byte, while the selected record and its
offset table remain canonical font state.

The `0x14f16` patcher is documented in
[symbol-map-patching.md](symbol-map-patching.md#owner-summary). It gates on the selected
font's normalized Roman-8 word, then uses active symbol words
`0x783144` / `0x783146` to select hard-coded half-map behavior or one of the
`0x14fce` patch tables.

`0x1440c` writes the selected-font snapshot after a map rebuild. It chooses
snapshot block `0x783148` for primary when `0x7828de == 0`, or `0x783152`
for secondary when `0x7828de != 0`. For bit-30 resource records,
`0x14436..0x14470` masks the selected address from `0x7828a8`, calls
`0x15890`, writes snapshot word `+0x02`, stores form byte `+0 = 1`, copies
record bytes `+0x0f` and `+0x11` into snapshot bytes `+0x06/+0x07`, and sets
provenance byte `+0x09` only when the selected address is below `0x780efa`.
For bit-30-clear inline/downloaded records, `0x14472..0x144ac` calls
`0x158be`, writes snapshot word `+0x02`, stores form byte `+0 = 0`, copies
record byte `+0x0e` into snapshot byte `+0x08`, and uses the same provenance
test. The shared tail at `0x144b0..0x144ca` copies active symbol word
`0x783144` or `0x783146` into snapshot word `+0x04`.

The snapshot is the cache key for skipping redundant map rebuilds. Helper
`0x13a48` selects `0x783148` or `0x783152` from `0x7828de`, loads selected
candidate slot `0x7828a8`, and compares the selected record against the
snapshot before `0x14c64` rebuilds anything.

For bit-30 resource records, `0x13a48` requires snapshot form byte `+0 == 1`,
resource words `+0x0e/+0x10` matching snapshot bytes `+0x06/+0x07`, selected
record address not above `0x780efa`, snapshot provenance byte `+0x09 == 1`,
active symbol word `0x783144` or `0x783146` matching snapshot word `+0x04`,
and `0x15890(selected_record)` matching snapshot word `+0x02`. For bit-30
clear inline/downloaded records, it requires snapshot form byte `+0 == 0`,
record byte `+0x0e` matching snapshot byte `+0x08`, the same address
provenance and active-symbol checks, and `0x158be(selected_record)` matching
snapshot word `+0x02`.

If every check passes, `0x14c64` exits after `0x13a48`; the prior glyph map
and selected context remain canonical. If any check fails, `0x14c64` rebuilds
the selected map through the resource or inline path, calls `0x14f16`, then
`0x1440c` records the new cache key. This means a renderer must not treat
`0x782f32` and `0x783032` as pure parser outputs. They are derived caches
validated against selected candidate `0x7828a8`, active symbol words, and the
snapshot fields above.

The adjacent active-object predicate at `0x14ba4..0x14c5c` is a narrower
cache-match test over a caller-supplied active-object signature. It reads the
candidate record pointer from the slot passed in `A1`, walks a signature tuple
from `A2`, and returns the slot pointer in `D7` only when every field matches.
The tested record fields are byte `+0x18`, bytes `+0x26/+0x27`, byte `+0x19`,
an optional word-range check around word `+0x1a` when `+0x19` is zero, word
`+0x20` within a `+/-0x19` tolerance, and the `0x158be(selected_record)`
symbol word. A selected symbol mismatch can still pass when the selected word
is Roman-8 `0x0115` and `0x783f00` is nonzero, or when the `(selected,
requested)` word pair appears in the four-entry compatibility table at
`0x15840`. Otherwise the helper returns zero.

That predicate does not write the selected maps or page objects. It classifies
whether an already-active record is compatible enough for the caller to keep
existing selected-font state. Its field groups are:

- canonical inputs:
  selected active-object slot and record fields
  `+0x18/+0x19/+0x1a/+0x20/+0x26/+0x27`, requested signature bytes from the
  caller, and the symbol word returned by `0x158be`;
- derived/cache inputs:
  the four compatibility pairs at `0x15840` and flag `0x783f00`;
- firmware bookkeeping:
  tuple cursor `A2`, local record pointer `A0`, and return value `D7`;
- output effect:
  no immediate pixels, but a nonzero return preserves the current map/cache
  path that later `0xd04a -> 0x1393a` printable bytes consume.

The exact unresolved boundary for this helper is not a renderer edge: callers
that build new `A2` signature tuples can expose additional compatibility
cases, but the predicate body itself is bounded by
`generated/disasm/ic30_ic13_active_object_dispatch_014ba4.lst`.

## Active Candidate And Map Cache Checkpoint

This checkpoint composes the selected-font state block that sits between parsed
font requests and later printable bytes. It starts when common refresh has
reached candidate selection and ends when `0x14c64` either preserves the
current glyph map through a cache hit or rebuilds the selected primary or
secondary map for later `0xd04a -> 0x1393a` printable consumption.

Writers:

- Candidate filters reached through `0x13eb8` build the active candidate list
  and call chooser `0x14398`. The chooser walks active list
  `0x78287c` / count `0x7827b8`, skips nonnegative entries, compares active
  negative entries through `0x13c06`, and writes selected slot pointer
  `0x7828a8`.
- `0x144d2` reads selected slot `0x7828a8`, copies the selected candidate
  longword into primary context record `0x782ee6` or secondary context record
  `0x782ef6`, and writes adjacent flag bytes from selected-longword bits 30
  and 26.
- `0x14c64` first calls `0x13a48`. A nonzero return means the snapshot still
  matches the selected record and active symbol word, so the selected map is
  preserved. A zero return rebuilds either primary map `0x782f32` or secondary
  map `0x783032`.
- Bit-30 resource records take `0x14c8c..0x14d64`: the helper derives active
  range words in `0x783134` or `0x78313a`, writes high-character flag
  `0x783132` or `0x783133`, and calls `0x14d9c`.
- Bit-30-clear inline/downloaded records take `0x14d6c..0x14d86`: the helper
  copies record byte `+0x0e` to `0x783132` or `0x783133`, then calls
  `0x14e24`.
- Both map rebuild paths call symbol patcher `0x14f16` and snapshot writer
  `0x1440c`.

Readers and consumers:

- `0x13a48` reads selected slot `0x7828a8`, active symbol word `0x783144` or
  `0x783146`, and snapshot record `0x783148` or `0x783152` to decide whether
  `0x14c64` can keep the existing map.
- `0x14d9c` reads selected resource range words `+0x0e/+0x10` and fills
  contiguous map bytes so host code `first_char+n` maps to glyph index `n`.
- `0x14e24` / `0x14eb6` rebuild the selected map by probing fixed-record
  entries; accepted entries store the candidate index, and rejected entries
  store zero.
- `0x14f16` reads active symbol words and mutates only the rebuilt selected
  map for Roman-8-compatible symbol behavior.
- `0xc428` / `0xc4fc` later copy the selected context longword from
  `0x782ee6` or `0x782ef6` into page-root context slot `+0x2c + 4*n`.
  The slot value is the selected context/resource longword, not the address of
  the RAM context record.
- `0x1393a` later reads selected slot `0x782f06`, current context record
  `0x782ee6` or `0x782ef6`, and selected map `0x782f32` or `0x783032` to
  build printable source object `0x782d7e`. The compact object created after
  that source capture carries a slot selector byte that render dispatch later
  uses against the page-root/render context slots.

Output effect:

- This checkpoint creates no pixels and queues no page object by itself.
- Its visible effect is delayed until a later printable byte maps the original
  host byte through `0x782f32` or `0x783032`, captures the selected context
  longword, queues a compact object through `0x12f2e`, and renders through
  `0x1effe -> 0x1f354`.
- Cache-hit and cache-miss paths are both pixel-affecting because they decide
  whether the active map bytes consumed by later printable text are preserved
  or rebuilt from the selected record and symbol word.

Field classification:

- Canonical selection state:
  active candidate list `0x78287c`, active count `0x7827b8`, selected slot
  `0x7828a8`, selected target `0x7828de`, and current context records
  `0x782ee6` / `0x782ef6`.
- Canonical map/symbol state:
  primary map `0x782f32`, secondary map `0x783032`, active symbol words
  `0x783144` / `0x783146`, range words `0x783134` / `0x78313a`, and
  high-character flags `0x783132` / `0x783133`.
- Derived/cache state:
  selected-font snapshots `0x783148` / `0x783152`, map bytes rebuilt by
  `0x14d9c` or `0x14e24`, and Roman-8 patch results from `0x14f16`.
- Parser scratch:
  parsed font-selection request records and dirty flags that have already
  driven `0xc580` before this checkpoint runs.
- Firmware bookkeeping:
  active-object comparator locals, `0x14ba4` signature tuple cursor `A2`, and
  the `D7` cache/compatibility return values.
- Unknown:
  no ROM-local writer or reader inside `0x14398 -> 0x144d2 -> 0x14c64` is
  unknown for the documented built-in, inline/downloaded, final-`X`, and
  current-RAM handoff streams. Remaining work must change selected candidate
  filters, cache predicate input, map rebuild form, symbol patch, page-root
  context slot, printable source fields, or compact row-helper inputs.

Evidence:

- Disassembly:
  `generated/disasm/ic30_ic13_active_object_scan_014398.lst`,
  `generated/disasm/ic30_ic13_active_object_dispatch_014ba4.lst`,
  `generated/disasm/ic30_ic13_font_selection_update_handlers_00c6ec.lst`,
  `generated/disasm/ic30_ic13_font_context_install_00c428.lst`, and
  `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`.
- Generated analyses:
  `generated/analysis/ic30_ic13_font_context_bridge.md`,
  `generated/analysis/ic30_ic13_text_glyph_index_flow.md`, and
  `generated/analysis/ic30_ic13_active_symbol_set_flow.md`.
- Fixture anchors:
  `0x13eb8 refresh carries parsed primary font selection to dispatch`,
  `0x13eb8 refresh carries parsed secondary font selection to dispatch`,
  `parsed primary built-in font selection feeds visible page-record rows`,
  `parsed secondary built-in font selection feeds visible SO page-record rows`,
  `font-ID primary inline/downloaded selection feeds visible page-record rows`,
  `font-ID inline/downloaded selection feeds visible page-record rows`,
  `0x13eb8 no-dispatch exits keep prior visible rows`,
  `live primary current-font RAM install feeds SI page-record rows`, and
  `live secondary current-font RAM install feeds SO page-record rows`.

Unresolved boundary:

- The next useful work here is not another cache-hit replay. It must expose a
  different selected candidate, selected symbol word, map-rebuild branch,
  `0x14ba4` compatibility tuple, page-root context slot value, or printable
  source object field.

## Visible Built-In Selection Boundary

Primary built-in selection route: stream `ESC (s0p10h12v0s0b3T!!` composes
the primary font-selection command family into visible compact text output.
The lowercase selection phase routes directly through writers `0xc930`,
`0xc89c`, `0xc6ec`, `0xc780`, and `0xc840` while parser mode 13 stays active.
Final uppercase `T` reaches wrapper `0x1205a`, which calls `0xc7e0` and
common refresh `0xc580`. The sibling uppercase wrappers in
`generated/disasm/ic30_ic13_payload_dispatch_011f82.lst` have the same
single-writer-plus-refresh shape: `0x12046` for point size, `0x1206e` for
style, `0x12082` for spacing, `0x12096` for pitch, and `0x120aa` for stroke
weight. The refresh chooses selected longword `0xc008004c`.

That selected built-in record is the first Courier offset-table record at
resource base `0x00004c`. Its HMI source is byte `+0x21 = 0` and long
`+0x24 = 0x00780000`, which `0x10550` converts to packed advance `30`.
The following printable stream `!!` routes both bytes through `0xd04a`.
Using the selected context, `0x1393a` maps host byte `0x21` to glyph `0x00`,
source glyph entry `0x001088`, rows `32`, width `9`, and context slot `0`.

The page-record producer then queues one short compact object in bucket `-1`:

```text
00 00 00 00 00 00 00 02 00 6a 00 00 68 02
```

The two entries use compact coords `0x6a00` and `0x6802`. The `0x1edc6`
bridge copies render-record context slot `0` as `0xc008004c`; compact render
dispatch resolves both glyphs through that selected context and renders the
same 38 ROM-derived row strings. The first nonblank row is:

```text
.............###...........................###...
```

This checkpoint closes the semantic path from parsed built-in font-selection
bytes through `0x13eb8`, `0x144d2`, `0x14c64`, printable `0xd04a`,
page-record queueing, `0x1edc6`, and compact glyph rendering.

Inline primary stream route: the same host-fetched stream can run through one
mixed-stream state. The font-selection event writes current-font RAM
`0x782ee6 = 0xc008004c`, installs context slot `0xc008004c` in the page
record, derives HMI `30`, and the following two printable bytes read that
context without a separate printable-phase injection.

Primary symbol-miss route: stream `ESC (1234U ESC (s0p10h12v0s0b3T!!` adds
the symbol-set fallback leg before the same visible-output path. Symbol-set
parsing routes through `0x11eb6`, `0x1201e`, and `0x120be`, producing
requested word `0x9a55`. The `0x156de` requested pass finds no class-zero
match, so the fallback table supplies active word `0x0115`; the prune pass
keeps survivor slot pointers `0x782354`, `0x782364`, and `0x782374`. The
following primary font-selection command reuses selected context `0xc008004c`,
primary map `0x782f32`, and HMI `30`. The two printable `!` bytes then produce
the same compact object prefix, render-record context slot, and rows as the
primary route above.

Live primary current-font RAM handoff: seeded current-font RAM records contain
primary `0x782ee6 = 0xc008004c` and secondary
`0x782ef6 = 0xc00ae122`. The route starts with an existing page root
`0x78297a`, page-root slot `1` live as the secondary context, and then feeds
`SI !!`.
Handler `0xc68a` calls `0xc428(0)`, which reads `0x782ee6`, calls `0xc4fc`,
chooses page-root context slot `0` as the first inactive slot, writes
`0xc008004c`, and sets `0x78297e = 0`. The following `0xd04a` / `0x1393a`
printable events read context slot `0` from the page-root context slots, map
host `0x21` to glyph `0x00`, and produce the same primary compact object
prefix and visible Courier rows. Because the root already exists, this route
has page-root allocation count `0`; it is a current-font-RAM-to-page-root
handoff route, not a first-root-allocation route.

Parsed-primary plus SI route: stream `ESC (s0p10h12v0s0b3T SI !!` composes
the parsed primary selection stream with that handoff. The selection phase
uses the same handlers and `0x144d2` context update as the primary visible
selection route, producing `0x782ee6 = 0xc008004c` and map `0x782f32`; the
tail `SI !!` then follows the live primary handoff route through
`0xc68a`, `0xc428(0)`, `0xc4fc`, page-root slot `0`, and two printable
`0xd04a` events. It reaches the same documented compact-object fields and
model-derived visible rows as the parsed primary visible path.

Secondary built-in selection route: stream `ESC )s0p16h8v0s0b0T SO !!` uses
the same lowercase writer family and final uppercase `0x1205a` refresh
boundary as the primary route, but `0x13eb8` writes secondary context record
`0x782ef6` with selected longword `0xc00ae122`.

That selected record is the class-one Line Printer offset-table record at
resource base `0x02e122`. Its HMI source is byte `+0x21 = 0` and long
`+0x24 = 0x00480000`, which converts to packed advance `18`. SO reaches
handler `0xc6b8`, installs/selects secondary slot `1`, and the following two
printable bytes map host `0x21` to glyph `0x00`, source glyph entry
`0x02e4f6`, rows `4`, width `22`, and context slot `1`.

The secondary compact object prefix is:

```text
00 00 00 00 00 01 00 02 00 c9 00 00 cb 01
```

The `0x1edc6` bridge carries context slots `(0xc008004c, 0xc00ae122)`.
Compact helper `0x207ac` renders two secondary glyphs from coords `0xc900`
and `0xcb01`; the first visible row is:

```text
.........################..################...###
```

Live secondary current-font RAM handoff: seeded current-font RAM records
contain primary `0x782ee6 = 0xc008004c` and secondary
`0x782ef6 = 0xc00ae122`. The route starts with an existing page root
`0x78297a`, page-root slot `0` live as the primary context, and then feeds
`SO !!`.
Handler `0xc6b8` calls `0xc428(1)`, which reads `0x782ef6`, calls `0xc4fc`,
chooses page-root context slot `1` as the first inactive slot, writes
`0xc00ae122`, and sets `0x78297e = 1`. The following `0xd04a` / `0x1393a`
printable events read context slot `1` from the page-root context slots, map
host `0x21` to glyph `0x00`, and produce the same secondary compact object
prefix and visible rows. Because the root already exists, this route has
page-root allocation count `0`; it is a current-font-RAM-to-page-root handoff
route, not a first-root-allocation route.

Parsed-secondary plus SO route: stream `ESC )s0p16h8v0s0b0T SO !!` writes
`0x782ef6 = 0xc00ae122` and map `0x783032`, then the tail `SO !!` follows
`0xc6b8`, `0xc428(1)`, `0xc4fc`, page-root slot `1`, and two printable
`0xd04a` events. It reaches the same documented compact-object fields and
model-derived visible rows as the parsed secondary visible path.

Inline secondary stream route: the same secondary stream can run through one
mixed-stream state instead of a split selection/page phase.
`ESC )s0p16h8v0s0b0T` writes current-font RAM
`0x782ef6 = 0xc00ae122`, updates page-record context slot `1`, SO selects slot
`1`, refreshes the active HMI to `18`, and both following printable bytes
queue the same `0xc00ae122` source context, compact object prefix, and rows as
the secondary route.

Secondary symbol-miss route: stream
`ESC )1234U ESC )s0p16h8v0s0b0T SO !!` adds the secondary symbol-set fallback
leg before the same visible-output path.
Symbol-set parsing routes through `0x11eb6`, `0x12008`, and `0x120be`,
producing requested word `0x9a55`. The `0x156de` requested pass finds no
class-one candidate with that word; its last requested probe is slot pointer
`0x782350`, record `0x02e122`, candidate word `0x000e`, and `matched =
False`.

The fallback table then supplies active word `0x000e`; the prune pass keeps
survivor slot pointers `0x782330`, `0x782340`, and `0x782350`, with the last
prune event matching record `0x02e122`. The following secondary font-selection
command reuses the same selected context `0xc00ae122`, secondary map
`0x783032`, and HMI `18`. SO and two printable `!` bytes then produce the same
compact object prefix, context slots, coords, and first visible row as the
secondary route above.

Remembered secondary symbol route: the same stream
`ESC )1234U ESC )s0p16h8v0s0b0T SO !!` can take the remembered source before
the fallback table when remembered secondary word `0x000e` is present at
`0x782f0a`. The `0x156de` requested pass misses word `0x9a55`; the remembered
pass first probes slot pointer `0x782324`, record `0x019d18`, candidate word
`0x0115`, and rejects it, then matches slot pointer `0x782330`, record
`0x01a984`, candidate word `0x000e`. That sets active secondary word `0x000e`
at `0x783146`, keeps survivor slot pointers `0x782330`, `0x782340`, and
`0x782350`, writes selected context `0xc00ae122` through `0x144d2`, rebuilds
map `0x783032` through `0x14c64`, crosses SO handler `0xc6b8`, and renders
the same compact object prefix and row digest
`b8ee0f8dd3e6ed70afa219bc00605d75249ae047a67fb67189693057d7936e6c` as the
secondary route above.

Supporting evidence names for this boundary are `parsed primary built-in font
selection feeds visible page-record rows`, `inline primary font selection
stream renders visible rows`, `primary symbol miss falls back before visible
page-record rows`, `live primary current-font RAM install feeds SI page-record
rows`, `parsed primary selection current-font RAM feeds SI visible rows`,
`parsed secondary built-in font selection feeds visible SO page-record rows`,
`live secondary current-font RAM install feeds SO page-record rows`, `parsed
secondary selection current-font RAM feeds SO visible rows`, `inline secondary
font selection stream renders SO visible rows`, `secondary symbol miss falls
back before visible SO page-record rows`, and `remembered secondary symbol
feeds visible SO page-record rows`.

## Page-Root Context Install

`0xc428(slot)` maps slot `0` or `1` to the selected longword stored in the
current-font context record:

- slot `0`: longword at `0x782ee6`;
- slot `1`: longword at `0x782ef6`.

If there is no current page root at `0x78297a`, it returns success without
installing a page-root slot. With a current root, it calls `0xc4fc` using the
selected context/resource longword.

`0xc4fc` scans the 16 slots at page root `+0x2c + 4*n`:

- It compares the low 24 bits of each existing context longword with the
  selected context longword.
- It accepts an existing matching context before testing whether the slot is
  live.
- If no existing context matches, it accepts the first slot where
  `0x78297f+n != 1`.
- It returns `0x11` only when all 16 slots are live and none match.
- On success, it writes the selected context longword into the selected root
  slot and returns the slot number.

Dirty-map fixture results:

- Dirty primary refresh with no live page-root slots installs selected
  longword `0xc008004c` in page-root slot `0`, sets `0x78297e = 0`, and calls
  `0x13eb8(0)`.
- Dirty secondary refresh installs selected longword `0xc00ae122` in
  page-root slot `0`, sets `0x78297e = 0`, and calls `0x13eb8(1)`.
- Full-live matching-context refresh reuses existing slot `3` for
  `0xc008004c`, temporarily toggles the transient refresh path, calls
  `0x13eb8(0)` twice, and leaves `0xc428` selecting slot `3`.
- Full-live/no-match refresh sees `0xc4fc` return `0x11`, leaves the existing
  16 live page-root slots unchanged, skips the second `0x13eb8` call, and
  skips `0xc428`.
- Dirty-1 selector mismatch calls only `0x13eb8(D5)`, copies the refreshed
  active word to the remembered word, and installs no page-root context.
- Dirty-2 selector match skips `0x13eb8`, calls only `0xc428(D5)`, installs
  the current selected context, and copies the active word to the remembered
  word.
- Dirty-2 selector mismatch skips both `0x13eb8` and `0xc428`; it only copies
  the active word to the remembered word and clears the dirty flags.

Common-refresh branch ledger:

- `0xc580..0xc5c8`: rewind the parser record and return immediately when
  dirty flag `0x782f2c` is zero. No candidate refresh, page-root install,
  remembered-word copy, or map rebuild occurs.
- `0xc59e..0xc5ca`: load the parsed slot selector from record word `+2`,
  accept only slots `0` and `1`, and report other selectors through
  `0x1284(0x00e3, 0x0034)` before continuing through the common refresh
  exit.
- `0xc5d8..0xc5fa`: dirty flag `1` with selector match scans live flags
  `0x78297f+n` for an inactive page-root context slot. If an inactive slot is
  found or there is no current root, control reaches the install path at
  `0xc646`.
- `0xc61a..0xc640`: dirty flag `1` with all 16 live flags set and a current
  root sets transient byte `0x78298f`, calls `0x13eb8(D5)`, clears
  `0x78298f`, then attempts context reuse through `0xc4fc`.
- `0xc646..0xc662`: install/reuse path calls `0xc4fc(0x782992)`. If
  `0xc4fc` returns `0x11`, the page-root context table is full and no second
  `0x13eb8` or `0xc428` call runs. Otherwise the path calls `0x13eb8(D5)`,
  then `0xc428(D5)` to select the installed/reused page-root slot.
- `0xc610..0xc618`: dirty flag `1` with selector mismatch calls only
  `0x13eb8(D5)`. It refreshes active font state for that target slot but does
  not call `0xc4fc` or `0xc428`, so it does not select a page-root context for
  later printable bytes.
- `0xc5fc..0xc60e`: dirty flag not equal to `1` with selector match is the
  dirty-`2`/font-ID/default-symbol shortcut. It calls only `0xc428(D5)`, using
  the current-font record already present in `0x782ee6` or `0x782ef6`; it does
  not call `0x13eb8`.
- `0xc666..0xc680`: all non-early refresh paths copy active symbol word
  `0x783144 + 2*D5` into remembered word `0x782f08 + 2*D5`, clear dirty flag
  `0x782f2c`, and return. This remembered-word copy happens even for
  selector-mismatch paths that did not install a page-root context.

`0xc428` also refreshes HMI/cache state from the selected context:

- If context byte `+0x04` is zero, it treats context `+0x00` as an
  inline/fixed-record pointer, reads selected record byte `+0x19` into
  `0x78318e`, and may derive `0x78315c` from selected record word `+0x1a`.
- If context byte `+0x04` is nonzero, it treats context `+0x00` as an
  offset-table/built-in pointer, reads selected record byte `+0x21` into
  `0x78318e`, and may derive `0x78315c` through `0x10550` from selected
  record longword `+0x24`.

The separate `0x196c4..0x19730` helper scans an already-built current page
root for a resource/context longword. It masks the caller argument to low
24 bits, returns to wait/service path `0x9ac2` if `0x78297a` is null, then
walks root context slots `+0x2c + 4*n` for `n = 0..15`. A match requires both
the masked slot longword to equal the masked caller argument and live flag
`0x78297f+n == 1`. On the first live match, it calls `0x1ba6c`; if no slot
matches, it calls `0x9ac2` directly.

Helper `0x1ba6c` is a publication/default-refresh sequence, not a glyph
renderer: `0xf34a -> 0xff1e -> 0xf8fc -> 0xf34a -> 0x9ac2`. Its output effect
is to flush pending text, publish the current root when applicable, refresh
page/font defaults, flush again, and wait/service. It does not inspect compact
buckets or render glyph rows directly, but it can decide when page-root
context-slot state is finalized before later rendering.

## Printable Source Capture

`0x1393a` captures the selected font state before printable placement:

1. Select map/context pair from `0x782f06`.
2. Map the original host character through `0x782f32` or `0x783032`.
3. Store the mapped glyph word at source `+0x0a`.
4. Copy the selected context longword into source `+0x00`.
5. Copy the context flag byte into source `+0x10`.
6. Compute source `+0x04` as either an offset-table glyph entry or a
   fixed-record glyph pointer.

For bit-30 offset-table contexts, `0x1393a` range-checks the original
character and resolves source `+0x04` through the same table formula later
used by renderer helper `0x1f354`. For bit-30-clear contexts, it uses
`context_base + 0x40 + 8 * mapped_byte`.

`0xd04a` then branches on source byte `+0x10`:

- nonzero: `0xd550` -> `0xd824` -> `0xd8fc`;
- zero: `0xd140` -> `0xd3b2` -> `0xd4ac`.

Both `0xd3b2` and `0xd824` store page-root context slot `0x78297e` into
source `+0x16`, mark live flag `0x78297f + slot`, and queue compact text
through `0x12f2e`.

### Printable Source Capture Checkpoint

This checkpoint is the byte-to-page-object boundary for ordinary printable
text. It starts after a host byte has reached `0xd04a` and ends when the
positioned source object has either queued compact text through `0x12f2e` or
failed at the same page-record allocation boundary used by other compact
objects.

Normal printable byte:

- ROM path:
  `0xd04a -> 0x1393a`.
- State category:
  parser-produced byte input, canonical current-font state, and canonical
  printable source state.
- Writers:
  `0xd04a` stores source base `0x782d7e`, passes the host byte to `0x1393a`,
  and later branches on source byte `+0x10`.
- Readers / consumers:
  `0x1393a` reads selected slot `0x782f06`, current context record
  `0x782ee6` or `0x782ef6`, and active map `0x782f32` or `0x783032`.
- Output effect:
  no page object yet; it converts the original host byte into a mapped glyph
  byte and source record.
- Evidence:
  `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`
  `0xd04a..0xd0e8`; `generated/analysis/ic30_ic13_text_glyph_index_flow.md`
  steps 5 and 6.

High printable byte with no high-character map:

- ROM path:
  `0xd072..0xd0a8`.
- State category:
  parser-produced byte input and firmware bookkeeping.
- Writers:
  if host byte is `0x80..0xff`, both high-character flags
  `0x783132/0x783133` are clear, and selected slot `0x782f06` is primary,
  `0xd04a` masks the byte to seven bits, records a temporary SO switch in
  `D4`, and calls `0xc6b8`.
- Readers / consumers:
  `0x1393a` consumes the masked byte after the temporary secondary install.
  After placement, `0xd04a` calls `0xc68a` when `D4` is set.
- Output effect:
  routes the byte through secondary map/context for the source capture, then
  restores primary selection after queueing.
- Evidence:
  `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`
  `0xd072..0xd0e2`; SI/SO bridge behavior in
  [direct-control-codes.md](direct-control-codes.md#selected-context-switch-checkpoint).

Unsupported host byte above `0xff`:

- ROM path:
  `0xd05e..0xd0a6`.
- State category:
  firmware bookkeeping.
- Writers:
  `0xd04a` calls `0xd99a`; when that helper returns zero, the byte is
  replaced with `0x7f` and retried through the normal printable path.
- Readers / consumers:
  `0x1393a` consumes the substituted byte.
- Output effect:
  queues the substituted glyph rather than the original byte.
- Evidence:
  `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`
  `0xd05e..0xd0a6`.

Source capture fields:

- ROM path:
  `0x1393a`.
- State category:
  canonical printable source state and derived/cache map state.
- Writers:
  writes source `+0x00` with the selected context longword, source `+0x0a`
  with the mapped glyph word, source `+0x10` with the context flag byte, and
  source `+0x04` with either a resource offset-table glyph entry or fixed
  record pointer.
- Readers / consumers:
  `0xd140` / `0xd550`, `0xd3b2` / `0xd824`, `0xd4ac` / `0xd8fc`, and
  `0x12f2e` consume the populated source.
- Output effect:
  determines both compact payload glyph identity and the resource/fixed
  record used for metrics.
- Evidence:
  `generated/analysis/ic30_ic13_text_glyph_index_flow.md` steps 5 through 8;
  current source field list in `Canonical printable source fields`.

Unflagged placement and queue:

- ROM path:
  `0xd0ce -> 0xd140 -> 0xd3b2 -> 0x12f2e`.
- State category:
  canonical source/page state and derived cursor state.
- Writers:
  `0xd3b2` writes source `+0x12/+0x14` positioned coordinates, copies
  selected page-root context slot `0x78297e` into source `+0x16`, marks live
  flag `0x78297f + slot`, and calls `0x12f2e`.
- Readers / consumers:
  `0x12f2e` reads source `+0x0b`, `+0x10`, `+0x12`, `+0x14`, and `+0x16`
  before appending compact payload entries through `0x1387c`.
- Output effect:
  queues compact text for bit-30-clear/fixed-record contexts and then lets
  `0xd4ac` update span state from unflagged metric bytes.
- Evidence:
  `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`
  `0xd140..0xd4aa`; `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`
  `0x12f2e..0x1306e`.

Flagged placement and queue:

- ROM path:
  `0xd0c2 -> 0xd550 -> 0xd824 -> 0x12f2e`.
- State category:
  canonical source/page state and derived cursor state.
- Writers:
  `0xd824` writes source `+0x12/+0x14`, copies `0x78297e` into source
  `+0x16`, marks live flag `0x78297f + slot`, and calls `0x12f2e`.
- Readers / consumers:
  `0x12f2e` consumes the same source fields; `0xd8fc` then updates span state
  from flagged metric words.
- Output effect:
  queues compact text for bit-30 resource/offset-table contexts.
- Evidence:
  `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`
  `0xd824..0xd8fa`; `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`
  `0x12f2e..0x1306e`.

Compact payload identity:

- ROM path:
  `0x12f2e`.
- State category:
  canonical page object state and firmware bookkeeping.
- Writers:
  creates or reuses compact text bucket objects through `0x1387c`; writes
  source byte `+0x0b` as the first compact payload byte at `0x1302a` or
  `0x1304e`; writes compact coordinate bits from source `+0x12/+0x14`;
  derives selector bits from source `+0x10`, width, row count, and context
  slot low nibble.
- Readers / consumers:
  publication and bridge carry the compact object and context slots to render
  records; compact dispatch later calls `0x1f354`.
- Output effect:
  this is the first checked page-object form for printable text. The renderer
  glyph identity is the compact payload glyph byte plus the copied render
  context slot, not the original host byte alone.
- Evidence:
  `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`
  `0x12f2e..0x1306e`; `generated/analysis/ic30_ic13_text_glyph_index_flow.md`
  steps 9 through 11.

Field grouping for this checkpoint:

- Canonical state:
  source record `0x782d7e`, selected slot `0x782f06`, current-font context
  records `0x782ee6` / `0x782ef6`, active maps `0x782f32` / `0x783032`,
  page-root slot `0x78297e`, live flags `0x78297f+n`, root compact bucket
  list `+0x1c`, and source fields
  `+0x00/+0x04/+0x0a/+0x0b/+0x10/+0x12/+0x14/+0x16`.
- Derived/cache state:
  mapped glyph byte, compact coordinate word, selector bits, map high-character
  flags `0x783132/0x783133`, and temporary high-byte SI/SO switch flag in
  `D4`.
- Parser scratch:
  original host byte passed to `0xd04a`; substituted byte `0x7f` and masked
  seven-bit byte are local to this path.
- Firmware bookkeeping:
  `0xd99a` substitution helper, page-root allocation/publication retry after
  a zero return from `0x12f2e`, and live-slot flag maintenance.
- Unknown:
  no ROM-local source-capture edge remains for the documented built-in and
  inline/downloaded text forms. Remaining work must change the selected map,
  context form, source field values, `0x12f2e` selector/object shape, or
  later render helper inputs.

Unresolved middle edges:

- `0xd04a -> 0x1393a -> 0x12f2e` is documented for normal printable bytes,
  high-byte secondary fallback, built-in offset-table contexts, and
  bit-30-clear inline/downloaded contexts.
- Compact object publication and render helpers for segmented downloaded-glyph shapes
  are no longer an open source-capture gap. They are owned by
  [downloaded-fonts.md](downloaded-fonts.md#remaining-edges) and summarized by `Page
  Object Shape Route Index` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md#page-object-shape-route-index):
  parser-produced `ESC )s#W` payloads now cover normal, wide, segmented, and
  segmented-wide compact selectors through install, `0x12f2e` object creation, `0xff1e`
  publication, render dispatch, and the exact compact-helper boundaries for high-row or
  wrapped-width cases.
- Exact remaining work downstream of this checkpoint must change the selected
  map/context consumed by `0x1393a`, the source fields passed to `0x12f2e`, a
  compact selector/object shape not covered by the downloaded-font owner, or a
  render-helper input or boundary named in
  [unresolved-boundaries.md](unresolved-boundaries.md#pixel-affecting-boundaries).

### Selected-Font Residual Routing Checkpoint

This checkpoint narrows the remaining "selected-font state combination" work
to exact field-changing routes. It is the routing point after font selection
has rebuilt a current context and before printable text becomes a compact page
object.

- Map/context producer route:
  `0x14c64 -> 0x14d9c/0x14e24 -> 0x14f16 -> 0x1440c` writes the active map
  `0x782f32` or `0x783032`, current context `0x782ee6` or `0x782ef6`, selected
  slot `0x782f06`, and high-character flags `0x783132/0x783133`. These fields
  are canonical selected-font state. New work belongs here only when a command
  changes one of those bytes/longwords before the next printable reaches
  `0x1393a`.
- Printable source producer route:
  `0xd04a -> 0x1393a` converts the original host byte through the active map
  and writes source `0x782d7e+0x00/+0x04/+0x0a/+0x0b/+0x10`. The source record
  is canonical printable state; the mapped glyph byte and resolved glyph
  pointer are derived/cache state. New work belongs here only when the map,
  context form, high-byte fallback, or substituted-byte path changes one of
  these source fields.
- Placement and page-object route:
  `0xd140 -> 0xd3b2 -> 0x12f2e` and
  `0xd550 -> 0xd824 -> 0x12f2e` write source
  `0x782d7e+0x12/+0x14/+0x16`, page-root live flags `0x78297f+n`, and compact
  bucket objects under root `+0x1c`. These fields are canonical page-object
  state; compact coordinate and selector bits are derived/cache state. New
  work belongs here only when positioning, live-slot selection, retry
  publication, or `0x12f2e` selector/object bytes change.
- Span-consumer route:
  `0xd4ac` reads unflagged context bytes `+0x2b/+0x2c/+0x2d`;
  `0xd8fc` reads flagged context words `+0x16/+0x18/+0x1a`; both update
  pending span fields `0x783184..0x78318a` and may flush through `0x12714`.
  The context metric fields are canonical selected-font metric state, while
  pending span watermarks are firmware bookkeeping until `0x12714` emits a
  segment-list or fixed-list object. New work belongs here only when selected
  context metrics change a span flush/no-flush decision or object bytes.
- Render-consumer route:
  publication and bridge copy compact bucket objects and context slots to
  `0x1ed84 -> 0x1edc6`, then compact render dispatch reaches `0x1effe` and
  glyph resolver `0x1f354`. New work belongs here only when the selected
  context slot, compact payload byte, selector class, row-copy helper input, or
  exact boundary in `unresolved-boundaries.md` changes.

Evidence:

- Disassembly:
  `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`,
  `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`, and the listed
  `0xd4ac` / `0xd8fc` call sites in
  `generated/analysis/ic30_ic13_text_cursor_span_flow.md`.
- Generated analysis used as support:
  `generated/analysis/ic30_ic13_text_glyph_index_flow.md` steps 1 through 11
  and `generated/analysis/ic30_ic13_text_cursor_span_flow.md` source/context
  field tables.
- Checked-in owners:
  `Printable Source Capture Checkpoint` above owns `0xd04a -> 0x1393a ->
  0x12f2e`; `Span Metric Consumers` below owns `0xd4ac` / `0xd8fc`;
  [page-record-storage.md](page-record-storage.md) owns the compact bucket
  storage; and [page-raster-imaging.md](page-raster-imaging.md) owns compact
  render dispatch and helper boundaries.

Unresolved boundary:

- No ROM-local middle edge is left open by the generic phrase
  "selected-font state combinations." The actionable boundary is a future
  byte stream or table state that changes one of the named selected-font,
  source, page-object, span, bridge, or render-helper fields before the first
  consumer listed above.

## Span Metric Consumers

The pending span state is documented in
[semantic-state-model.md](semantic-state-model.md) under
`Text Span Flush And Fixed-Width Spans`. The font-context side of the
contract is:

- `0xd4ac` is called with the unflagged selected context/resource pointer from
  source `+0x00`. It reads bytes `+0x2b`, `+0x2c`, and `+0x2d`.
- `0xd8fc` is called with the flagged selected context/resource pointer from
  source `+0x00`. It reads words `+0x16`, `+0x18`, and `+0x1a`.

`0xd4ac` behavior:

- returns immediately if pending-span byte `0x783184` is clear;
- rejects before-lower when current y is below byte `+0x2c`;
- rejects beyond-page when current y plus byte `+0x2d` exceeds
  `0x782db6`;
- when `0x783185` is set and byte `+0x2b` is nonzero, raises high-y using
  current y plus `+0x2b`;
- otherwise raises high-y using current y plus five;
- flushes through `0x12714` / `0x126e2` when current x is below
  `0x783186`;
- raises high-x `0x783188` when current x exceeds it.

`0xd8fc` behavior:

- returns immediately if pending-span byte `0x783184` is clear;
- rejects before-lower when current y is below word `+0x16`;
- rejects beyond-page when current y plus word `+0x18` exceeds
  `0x782db6`;
- when `0x783185` is set, raises high-y using current y minus word `+0x1a`;
- otherwise raises high-y using current y plus five;
- flushes through `0x12714` / `0x126e2` when current x is below
  `0x783186`;
- raises high-x `0x783188` when current x exceeds it.

Fixture-pinned metric effects:

- Flagged path: cursor y `21`, `+0x16 = 0`, `+0x18 = 10`,
  `+0x1a = 18`, and `0x783185 = 1` produce high-y `3`; low-water flush
  queues a segment-list object rendered on rows `3..5`.
- Unflagged path: cursor y `21`, `+0x2b = 7`, `+0x2c = 0`,
  `+0x2d = 10`, and `0x783185 = 1` produce high-y `28`; low-water flush
  queues a segment-list object rendered on rows `12..14`.
- Host-fetched downloaded-resource path: `ESC )s80W` validates a sparse
  descriptor through `0x16fae`, copies it into a `0x1719c` payload, and
  leaves payload bytes `+0x2b = 0`, `+0x2c = 0`, and `+0x2d = 0x20`.
  Printing `!` from that selected payload enters `0xd4ac`, produces high-y
  `26`, and queues a segment-list object rendered on rows `10..12`.
- Host-fetched flagged downloaded-resource path: the same `ESC )s80W`
  payload supplies words `+0x16 = 4`, `+0x18 = 4`, and `+0x1a = 5`.
  Printing `!` from a bit-30 downloaded-offset-table context enters `0xd8fc`,
  produces high-y `16`, queues segment-list key `0x0406`, and renders the
  span before the compact glyph in bucket `1`.
- Host-fetched metric-variant path: changing the descriptor bytes consumed by
  `0x16fae` makes `0x1719c` copy payload word `+0x2c = 0x0010` and word
  `+0x1a = 0x0002`. The old `+0x2d = 0x20` value fails a tight `0xd4ac`
  page-extent gate at extent `40`; the new `+0x2d = 0x10` value queues the
  same segment-list span. The changed `+0x1a` moves `0xd8fc` high-y from `16`
  to `19`, changing the rendered span object key from `0x0406` to `0x3406`.
- Host-fetched clamped metric path: reducing descriptor range/count word
  `+0x14` to `5` and supplying an oversized rounded-metric input makes
  `0x16fae` clamp copied payload word `+0x2c` to `0x0014`, leaving
  `+0x2b = 0` for this `0x1719c` payload family. The default `+0x2d = 0x20`
  fails a tight `0xd4ac` page-extent gate at extent `41`; clamped
  `+0x2d = 0x14` queues the span. The same descriptor changes `+0x18` to `0`
  and `+0x1a` to `3`, moving `0xd8fc` high-y to `18` and the rendered span
  object key to `0x2406`.
- Host-fetched lower-bound metric path: fixture
  `host-fetched lower-bound metric variant suppresses d4ac and d8fc spans`
  changes descriptor first-code bytes to `0x0018`, range/count bytes to
  `0x0600`, and rounded-metric input to `0x1800`. `0x16fae` and `0x1719c`
  copy canonical span lower fields `+0x16 = 0x0018` and `+0x2c = 0x1800`,
  derive/cache `+0x18 = 0x05e7`, and leave firmware-bookkeeping byte
  `+0x2b = 0`. At cursor y `21`, `0xd4ac` reads byte `+0x2c = 0x18` and
  exits `before-context-lower`; `0xd8fc` reads word `+0x16 = 0x0018` and
  exits the same way. The compact text objects still queue and render, but no
  segment-list span object is emitted by either consumer.
- Host-fetched upper-bound metric path: fixture
  `host-fetched upper-bound metric variant keeps d4ac span but suppresses d8fc`
  changes descriptor range/count bytes to `0x0040`. `0x16fae` and
  `0x1719c` copy canonical range/count `+0x14 = 0x0040` and derive/cache
  flagged height `+0x18 = 0x003b`, while the rounded unflagged word remains
  `+0x2c = 0x0020`. At cursor y `21` and page extent `64`, `0xd4ac` still
  reads bytes `+0x2c/+0x2d = 0/0x20`, queues the same span object rendered on
  rows `10..12`, but `0xd8fc` reads word `+0x18 = 0x003b` and exits
  `beyond-page-extent`; its compact glyph object still queues and renders.
- Descriptor producer-form cross-product: fixture
  `descriptor metric fields match across inline and resource contexts` uses
  the same copied metric-variant payload to pin the legal selected forms.
  Inline/unflagged context `0x00000000` feeds `0xd4ac`, consumes
  `+0x2b/+0x2c/+0x2d = 0/0/0x10`, and renders row digest
  `67554ea70d7cfd9b11c0777e3cf65d51600a44301a4f93bd4d9b0c0fbc23c00e`.
  Resource/flagged context `0x40000000` feeds `0xd8fc`, consumes
  `+0x16/+0x18/+0x1a = 0x0004/0x0004/0x0002`, and renders row digest
  `00c97b69bc50326e442dd060c88b710b8f00217d40809bed276d8ba48581fdc7`.
  The swapped forms are not alternate valid paths: resource/unflagged `d4ac`
  fails when the renderer treats compact glyph `1` as an offset-table glyph
  for context `0x40000000`, and inline/flagged `d8fc` fails because context
  `0x00000000` does not select the offset-table form.
- Legal descriptor metric value matrix: fixture
  `legal descriptor metric value matrix drives d4ac and d8fc consumers`
  groups seven parser-produced descriptor cases behind the same two legal
  selected forms. Small-rounded, clamped-rounded, lower-bound, and
  upper-bound cases match the individual fixtures above. The
  zero-rounded-offset case changes host descriptor range/count bytes to
  `0x0018`, rounded-metric input to `0x0000`, and flagged offset byte to `0`;
  `0x16fae` / `0x1719c` copy canonical fields
  `+0x14/+0x16 = 0x0018/0x0004`, derived/cache field
  `+0x18 = 0x0013`, and consumer fields `+0x1a/+0x2c =
  0x0000/0x0000`. `0xd4ac` consumes `+0x2c/+0x2d = 0/0`, still queues the
  span digest
  `67554ea70d7cfd9b11c0777e3cf65d51600a44301a4f93bd4d9b0c0fbc23c00e`, and
  `0xd8fc` consumes `+0x16/+0x18/+0x1a = 0x0004/0x0013/0x0000`, publishes
  high-y `21`, queues span object prefix
  `00 00 00 00 40 00 00 01 54 06 03 00 00 14`, and renders row digest
  `47361fc76bd6284f9d764c0377a3fda64edd3944b5cb2dff72acfd2224bc25e8`.
  The midpoint-rounded case changes host descriptor range/count bytes to
  `0x0018`, rounded-metric input to `0x0018`, and flagged offset byte to `7`;
  `0x16fae` / `0x1719c` copy canonical fields
  `+0x14/+0x16/+0x18/+0x1a/+0x2c =
  0x0018/0x0004/0x0013/0x0007/0x0018`. `0xd4ac` consumes
  `+0x2c/+0x2d = 0/0x18`, queues the same span digest
  `67554ea70d7cfd9b11c0777e3cf65d51600a44301a4f93bd4d9b0c0fbc23c00e`,
  and `0xd8fc` consumes `+0x16/+0x18/+0x1a =
  0x0004/0x0013/0x0007`, updates high-y to `14`, but because no flush object
  is published for that state it leaves the compact glyph digest
  `1a73b5e7454202d800c69f626bcf34e7d0d583b459e04c0bd4250010bf3ba28a`.
  The negative-offset case changes host flagged offset byte to `0xfe`;
  `0x1719c` copies that input as word `+0x1a = 0xfffe`, while rounded
  metric word `+0x2c = 0x0008` feeds `d4ac`. `d4ac` keeps the default span
  digest, but `d8fc` consumes `+0x1a` as `65534`, computes high-y `-65513`,
  queues object prefix `00 00 00 00 40 00 00 01 04 06 03 00 00 14`, and
  renders row digest
  `72bfa14c2a84532e2bdf6fb8fddf26ed6904c49dcf4fdcb322592471b5d5b281`.
- Legal descriptor metric boundary values: fixture
  `legal descriptor metric boundary values drive d4ac and d8fc consumers`
  adds parser-produced descriptors behind the same legal forms. The
  `d8fc-lower-equal` case copies `+0x16/+0x18/+0x1a =
  0x0015/0x0002/0x0001`; at cursor y `21`, `0xd8fc` treats lower equality as
  in range, publishes high-y `20`, queues object prefix
  `00 00 00 00 40 00 00 01 44 06 03 00 00 14`, and renders digest
  `f830d30ea60a61f0b74a489c4b7df1bb25dc464b6765d170c19e7278a0267eab`.
  The `rounded-0x0013-up` case proves normal, unclamped rounding: input
  `0x0013` stores `+0x2c = 0x0014`, so `d4ac` consumes height byte `0x14` and
  publishes the standard segment-list span while `d8fc` consumes
  `+0x16/+0x18/+0x1a = 0x0004/0x0004/0x0001`, publishes high-y `20`, and
  renders digest
  `f830d30ea60a61f0b74a489c4b7df1bb25dc464b6765d170c19e7278a0267eab`.
  The `extent-equal` case copies `+0x18 = 0x002b`; at cursor y `21`,
  `0xd8fc` accepts the exact page extent `64` boundary, publishes high-y
  `21`, and renders the same digest as the zero-offset span. The
  `positive-offset-max` case copies input offset byte `0x7f` as word
  `+0x1a = 0x007f`; `0xd8fc` consumes it as `127`, computes high-y `-106`,
  and renders the same three-row digest as the negative-offset boundary. The
  `rounded-0x1500-transform` case shows rounded input `0x1500` is not copied
  as a high-byte lower bound for `d4ac`: `0x1719c` stores `+0x2c = 0x0060`,
  so `0xd4ac` exits `beyond-page-extent` and leaves the compact glyph digest
  `86e3bb70d51c66ac608345dc3bff6476447ebc500d7c271808a53d6638d59ad6`. The
  `rounded-0x1508-transform` case proves the low byte is discarded by the same
  transform: input `0x1508` also stores `+0x2c = 0x0060`, so `d4ac` takes the
  same beyond-page exit while `d8fc` still consumes `+0x16/+0x18/+0x1a =
  0x0004/0x0013/0x0001` and renders digest
  `f830d30ea60a61f0b74a489c4b7df1bb25dc464b6765d170c19e7278a0267eab`.
- Legal descriptor metric extent fenceposts: fixture
  `legal descriptor metric extent fenceposts drive d4ac and d8fc consumers`
  combines the `0x17430` derived-height writer with the `0x1762a`
  signed-offset writer at the `0xd8fc` page-extent gate. Range word `0x002f`
  with first code `4` copies derived/cache `+0x18 = 42`; with offset byte
  `0`, `d8fc` accepts the span at high-y `21` and renders digest
  `47361fc76bd6284f9d764c0377a3fda64edd3944b5cb2dff72acfd2224bc25e8`. Range
  word `0x0031` copies `+0x18 = 44` and exits `beyond-page-extent` with
  offset byte `0`; changing the offset byte to `1` still exits before a span
  object is queued. Range word `0x0032` copies `+0x18 = 45` and also exits
  `beyond-page-extent` with offset byte `2`. In all four cases the legal
  inline/unflagged form still feeds `d4ac` copied word `+0x2c = 0x0020` and
  the standard span digest
  `67554ea70d7cfd9b11c0777e3cf65d51600a44301a4f93bd4d9b0c0fbc23c00e`.
- Legal descriptor metric range endpoints: fixture
  `legal descriptor metric range endpoints drive d4ac and d8fc consumers`
  holds the rounded metric and signed offset stable while varying the
  `0x17430` first-code/range pair. The first-code-zero case copies
  `+0x14/+0x16/+0x18 = 0x0018/0x0000/0x0017`, proving the derived/cache word
  is range minus one when the lower bound is zero. The range-minus-one case
  copies `+0x14/+0x16/+0x18 = 0x0015/0x0014/0x0000`, proving the same helper
  accepts the tightest legal derived height. In both cases `d4ac` consumes
  `+0x2c = 0x0008`, queues object prefix
  `00 00 00 00 40 00 00 01 a4 06 03 00 00 14`, and renders digest
  `67554ea70d7cfd9b11c0777e3cf65d51600a44301a4f93bd4d9b0c0fbc23c00e`;
  `d8fc` consumes the copied `+0x16/+0x18/+0x1a` fields, keeps high-y `20`,
  queues object prefix `00 00 00 00 40 00 00 01 44 06 03 00 00 14`, and
  renders digest
  `f830d30ea60a61f0b74a489c4b7df1bb25dc464b6765d170c19e7278a0267eab`.
- Legal descriptor metric tight ranges: fixture
  `legal descriptor metric tight range values drive d4ac and d8fc consumers`
  combines the smallest legal range/count forms with rounded and signed-offset
  variation. Range one with first code zero copies
  `+0x14/+0x16/+0x18 = 0x0001/0x0000/0x0000`; rounded input `0x0000`
  copies `+0x2c = 0x0000`, while rounded input `0xffff` clamps to
  `+0x2c = 0x0004`. Range two with first code one copies
  `+0x14/+0x16/+0x18 = 0x0002/0x0001/0x0000`; offset bytes `0x7f` and
  `0xff` copy to `+0x1a = 0x007f` and `0xffff`. All four cases keep the
  legal inline/unflagged `d4ac` span digest
  `67554ea70d7cfd9b11c0777e3cf65d51600a44301a4f93bd4d9b0c0fbc23c00e`.
  The zero-offset range-one cases keep `d8fc` high-y `21` and digest
  `47361fc76bd6284f9d764c0377a3fda64edd3944b5cb2dff72acfd2224bc25e8`;
  the max-offset range-two cases compute high-y `-106` and `-65514` and
  render digest
  `72bfa14c2a84532e2bdf6fb8fddf26ed6904c49dcf4fdcb322592471b5d5b281`.
- Legal descriptor metric low-nibble rounding: fixture
  `legal descriptor metric low-nibble rounding drives d4ac and d8fc consumers`
  holds the legal resource/flagged and inline/unflagged forms steady while
  varying the rounded-metric input word through `0x0001`, `0x0003`, `0x0004`,
  `0x0005`, and `0x000f`. `0x16fae` / `0x1719c` copy those inputs to
  `+0x2c` words `0x0000`, `0x0004`, `0x0004`, `0x0004`, and `0x0010`,
  matching the ROM-derived `min((value + 2) >> 2, word(+0x14)) << 2`
  transform for these low-nibble samples.
  In all five cases canonical fields `+0x14/+0x16/+0x18/+0x1a` remain
  `0x0018/0x0004/0x0013/0x0001`. `0xd4ac` consumes the copied
  `+0x2c/+0x2d` word and still renders span digest
  `67554ea70d7cfd9b11c0777e3cf65d51600a44301a4f93bd4d9b0c0fbc23c00e`;
  `0xd8fc` consumes `+0x16/+0x18/+0x1a`, keeps high-y `20`, queues object
  prefix `00 00 00 00 40 00 00 01 44 06 03 00 00 14`, and renders digest
  `f830d30ea60a61f0b74a489c4b7df1bb25dc464b6765d170c19e7278a0267eab`.
- Span-consumer branch family: fixture
  `d4ac and d8fc span consumer branch family controls flush output` drives
  printable `!` through both selected source forms. For both `0xd4ac` and
  `0xd8fc`, clear `0x783184` returns `updated=False` and leaves only the
  compact text object; lower-bound failure at current y `21` versus lower
  `30` returns `before-context-lower` with no span object; page-extent failure
  at current y `21`, height `50`, and extent `64` returns
  `beyond-page-extent` with no span object. The high-x-only case starts with
  `low_x=0`, `high_x=20`, and printable advance to x `28`, raises
  `0x783188`, and the following CR materializes a 28-pixel segment-list span
  through `0x12714`; `d4ac` renders bucket-relative rows `10..12`, while
  `d8fc` uses its alternate offset to render rows `3..5`.

## Metric Evidence Matrix

This list is the current coverage boundary for metric-producing state. It
separates parser-produced evidence from synthetic context fixtures so future
work can close the right gap instead of re-tracing already-covered consumers.

- Claim: PCL font request bytes become concrete selection filter values.
  Evidence: fixture `parsed font-selection metrics feed concrete candidate
  filters`, generated from request `0p10h12v0s0b3T`; handlers `0xc930`,
  `0xc89c`, `0xc6ec`, `0xc780`, `0xc840`, and `0x1205a`; filters
  `0x156de`, `0x153c6`, `0x1519a`, and `0x14398`. Status:
  parser-produced and selected to a resource candidate.
- Claim: parsed built-in font-selection bytes can determine visible compact
  text rows. Evidence: fixture
  `inline primary font selection stream renders visible rows`; stream
  `ESC (s0p10h12v0s0b3T!!`; selected context `0xc008004c`; HMI `30`;
  selection final handlers `0xc930`, `0xc89c`, `0xc6ec`, `0xc780`, `0xc840`,
  and `0x1205a`; printable handlers `0xd04a, 0xd04a`; queued object prefix
  `00 00 00 00 00 00 00 02 00 6a 00 00 68 02`; render-record context slot
  `0xc008004c`; first visible row
  `.............###...........................###...`. Status: one
  mixed-stream state from parser-produced selection through printable source
  capture and visible rows.
- Claim: a primary symbol-set miss can fall back to the firmware table word
  before visible primary output. Evidence: fixture
  `primary symbol miss falls back before visible page-record rows`; stream
  `ESC (1234U ESC (s0p10h12v0s0b3T!!`; requested word `0x9a55`; symbol
  parser handlers `0x11eb6`, `0x1201e`, and `0x120be`; fallback active word
  `0x0115`; survivor slots `0x782354`, `0x782364`, and `0x782374`; selected
  context `0xc008004c`; map `0x782f32`; queued object prefix
  `00 00 00 00 00 00 00 02 00 6a 00 00 68 02`; rows use the pinned primary
  visible path. Status: parser-produced symbol fallback plus modeled
  selected-context handoff to visible-output fixture.
- Claim: parsed secondary built-in font-selection bytes can determine visible
  compact text rows after SO selects the secondary context. Evidence: fixture
  `inline secondary font selection stream renders SO visible rows`; stream
  `ESC )s0p16h8v0s0b0T SO !!`; selected context `0xc00ae122`; HMI `18`;
  selection final handlers `0xc930`, `0xc89c`, `0xc6ec`, `0xc780`, `0xc840`,
  and `0x1205a`; handlers `0xc6b8, 0xd04a, 0xd04a`; queued object prefix
  `00 00 00 00 00 01 00 02 00 c9 00 00 cb 01`; render-record context slots
  `(0xc008004c, 0xc00ae122)`; first visible row
  `.........################..################...###`. Status: one
  mixed-stream state from parser-produced selection through SO, printable
  source capture, and visible rows.
- Claim: the primary current-font RAM record can feed visible SI output
  through the page-root context slot path. Evidence: fixture
  `live primary current-font RAM install feeds SI page-record rows`; seeded
  records `0x782ee6 = 0xc008004c` and `0x782ef6 = 0xc00ae122`; stream
  `SI !!`; handler `0xc68a`; install helper `0xc428(0)` / `0xc4fc`; selected
  page-root context slot `0`; page-root slots
  `(0xc008004c, 0xc00ae122)`; `0xd04a` source context `0xc008004c`; queued
  object prefix `00 00 00 00 00 00 00 02 00 6a 00 00 68 02`; first nonblank
  row `.............###...........................###...`. Status:
  modeled current-font RAM handoff to existing page-root slot and visible
  output.
- Claim: parsed primary font-selection bytes can compose with the primary
  current-font RAM handoff into visible output. Evidence: fixture
  `parsed primary selection current-font RAM feeds SI visible rows`; stream
  `ESC (s0p10h12v0s0b3T SI !!`; selection context update
  `0x782ee6 = 0xc008004c`; map `0x782f32`; SI handler `0xc68a`; install
  helper `0xc428(0)` / `0xc4fc`; page-root slots
  `(0xc008004c, 0xc00ae122)`; printable source contexts `0xc008004c`;
  object prefix `00 00 00 00 00 00 00 02 00 6a 00 00 68 02`; rows use the
  pinned parsed primary visible path. Status: composed parser-selection to
  current-font RAM to existing page-root slot and visible output.
- Claim: the secondary current-font RAM record can feed visible SO output
  through the page-root context slot path. Evidence: fixture
  `live secondary current-font RAM install feeds SO page-record rows`; seeded
  records `0x782ee6 = 0xc008004c` and `0x782ef6 = 0xc00ae122`; stream
  `SO !!`; handler `0xc6b8`; install helper `0xc428(1)` / `0xc4fc`; selected
  page-root context slot `1`; page-root slots
  `(0xc008004c, 0xc00ae122)`; `0xd04a` source context `0xc00ae122`; queued
  object prefix `00 00 00 00 00 01 00 02 00 c9 00 00 cb 01`; first visible
  row `.........################..################...###`. Status:
  modeled current-font RAM handoff to existing page-root slot and visible
  output.
- Claim: parsed secondary font-selection bytes can compose with the secondary
  current-font RAM handoff into visible output. Evidence: fixture
  `parsed secondary selection current-font RAM feeds SO visible rows`; stream
  `ESC )s0p16h8v0s0b0T SO !!`; selection context update
  `0x782ef6 = 0xc00ae122`; map `0x783032`; SO handler `0xc6b8`; install
  helper `0xc428(1)` / `0xc4fc`; page-root slots
  `(0xc008004c, 0xc00ae122)`; printable source contexts `0xc00ae122`;
  object prefix `00 00 00 00 00 01 00 02 00 c9 00 00 cb 01`; rows use the
  pinned parsed secondary visible path. Status: composed parser-selection
  to current-font RAM to existing page-root slot and visible output.
- Claim: a secondary symbol-set miss can fall back to the firmware table word
  before visible SO output. Evidence: fixture
  `secondary symbol miss falls back before visible SO page-record rows`; stream
  `ESC )1234U ESC )s0p16h8v0s0b0T SO !!`; requested word `0x9a55`; `0x156de`
  requested pass misses candidate word `0x000e` at slot pointer `0x782350` /
  record `0x02e122`; fallback active word `0x000e`; surviving slots
  `0x782330`, `0x782340`, and `0x782350`; selected context `0xc00ae122`; map
  `0x783032`; queued object prefix
  `00 00 00 00 00 01 00 02 00 c9 00 00 cb 01`; first visible row
  `.........################..################...###`. Status:
  parser-produced symbol fallback and selection plus modeled selected-context
  handoff to visible-output fixture.
- Claim: a secondary symbol-set miss can recover from remembered word
  `0x782f0a` before using the fallback table and still reach visible SO
  output. Evidence: fixture
  `remembered secondary symbol feeds visible SO page-record rows`; stream
  `ESC )1234U ESC )s0p16h8v0s0b0T SO !!`; requested word `0x9a55`;
  remembered word `0x000e`; first remembered probe slot `0x782324` / record
  `0x019d18` rejects candidate `0x0115`; first remembered match slot
  `0x782330` / record `0x01a984` accepts candidate `0x000e`; selected context
  `0xc00ae122`; map `0x783032`; SO handler `0xc6b8`; queued object prefix
  `00 00 00 00 00 01 00 02 00 c9 00 00 cb 01`; row digest
  `b8ee0f8dd3e6ed70afa219bc00605d75249ae047a67fb67189693057d7936e6c`.
  Status: parser-produced symbol recovery and selection plus modeled
  selected-context handoff to visible-output fixture.
- Claim: selected built-in context supplies HMI/default advance. Evidence:
  fixture `line-printer flagged HMI metric via 0x10550`; selected context
  `0x440946b4`, resource base `0x0146b4`, byte `+0x21 = 0x00`, long
  `+0x24 = 0x00480000`, result `18` dots. Status: parser-independent
  context fixture, but the source fields are concrete built-in resource bytes.
- Claim: HMI changes compact text object coordinates and visible rows.
  Evidence: fixtures `two printable byte stream with line-printer HMI renders
  subbyte entry` and `two printable byte stream with line-printer HMI renders
  subbyte rows`; stream `!!` advances x from `10` to `28` to `46`, producing
  payload `00 02 20 00 01 20 02 02`. Status: visible-output fixture through
  compact text render.
- Claim: flagged span metrics control pending-span high-y and flush rows.
  Evidence: fixture `flagged printable d8fc low-watermark flush renders span`;
  `0xd8fc` consumes context `+0x16`, `+0x18`, `+0x1a`; flush queues selector
  `0x4000` object key `0x3406`. Status: synthetic context fixture through
  visible segment-list rows.
- Claim: unflagged span metrics control pending-span high-y and flush rows.
  Evidence: fixture `unflagged printable d4ac low-watermark flush renders
  span`; `0xd4ac` consumes context `+0x2b`, `+0x2c`, `+0x2d`; flush queues
  selector `0x4000` object key `0xc406`. Status: synthetic
  inline/downloaded-style context fixture through visible segment-list rows.
- Claim: downloaded-font payload can be installed and printed from a host
  stream. Evidence: fixtures `host-fetched printable byte uses installed
  downloaded glyph page object` and `combined host-fetched font download stream
  prints installed glyph`; documented in
  [downloaded-fonts.md](downloaded-fonts.md#owner-summary).
  Status: parser-produced host stream to visible downloaded glyph rows.
- Claim: a downloaded-resource descriptor can feed `0xd4ac` span rows.
  Evidence: fixture `host-fetched 0x1719c payload metrics feed d4ac span
  rows`; host-fetched `ESC )s80W` reaches `0x16c14`, `0x16fae`, `0x17026`,
  and `0x1719c`; the selected payload bytes `+0x2b`, `+0x2c`, and `+0x2d`
  are consumed by `0xd4ac` and change rendered segment-list rows. Status:
  parser-produced resource payload to visible unflagged span rows.
- Claim: a downloaded-resource descriptor can feed `0xd8fc` span rows.
  Evidence: fixture `host-fetched 0x1719c payload metrics feed d8fc span
  rows`; host-fetched `ESC )s80W` reaches the installed bit-30 resource form,
  a synthetic downloaded glyph pointer makes printable `!` visible, payload
  words `+0x16`, `+0x18`, and `+0x1a` are consumed by `0xd8fc`, and the bucket
  renders both the span rows and compact glyph rows. Status: parser-produced
  resource payload to visible flagged span rows.
- Claim: the same metric producer contract survives the type-2 payload form.
  Evidence: fixture
  `host-fetched type-2 0x1719c payload metrics feed d4ac and d8fc span rows`;
  host-fetched `ESC )s80W` validates a descriptor whose setup byte produces
  payload byte `+0x0c = 2`, payload units `0x100`, allocation size `18`, and
  installed candidate longword `0x44000000`. The fixture then renders an
  unflagged wide fixed-record glyph while `0xd4ac` consumes `+0x2b`,
  `+0x2c`, and `+0x2d`, and renders a flagged pointer glyph while `0xd8fc`
  consumes `+0x16`, `+0x18`, and `+0x1a`. Status: parser-produced type-2
  resource payload to visible unflagged and flagged span rows.
- Claim: the type-1 payload form uses the same copied metric fields and
  consumer contracts. Evidence: fixture
  `host-fetched type-1 0x1719c payload metrics feed d4ac and d8fc span rows`;
  host-fetched `ESC )s80W` validates a descriptor whose setup byte produces
  payload byte `+0x0c = 1`, payload units `0x100`, allocation size `18`, and
  installed candidate longword `0x40000000`. The fixture installs a fixed-record
  glyph for the unflagged `0xd4ac` path and a pointer-table glyph for the
  flagged `0xd8fc` path, then proves the same payload fields `+0x2b`,
  `+0x2c`, `+0x2d`, `+0x16`, `+0x18`, and `+0x1a` affect visible span rows.
  Status: parser-produced type-1 resource payload to visible unflagged and
  flagged span rows.
- Claim: parser-produced descriptor metric values can change both consumer
  gates and visible rows. Evidence: fixture `host-fetched metric variant
  changes d4ac gate and d8fc rows`; the host-fetched `ESC )s80W` variant
  copies `+0x2c = 0x0010` and `+0x1a = 0x0002` through `0x16fae`/`0x1719c`.
  With page extent `40`, the default `+0x2d = 0x20` path returns
  `beyond-page-extent`, while the variant `+0x2d = 0x10` queues a visible
  `0xd4ac` span. The same payload moves `0xd8fc` high-y to `19` and renders
  the segment-list rows at the shifted bucket key `0x3406`. Status:
  parser-produced metric-value variant to visible unflagged and flagged span
  effects.
- Claim: parser-produced descriptor metric clamping changes copied fields and
  visible rows. Evidence: fixture `host-fetched clamped metric variant changes
  d4ac gate and d8fc rows`; host-fetched `ESC )s80W` validates a descriptor
  whose range/count word `+0x14 = 5` clamps an oversized rounded metric input
  into copied payload word `+0x2c = 0x0014`. The fixture proves byte
  `+0x2b` remains `0` in this `0x1719c` payload family, flips the `d4ac`
  page-extent gate at extent `41`, copies flagged metrics `+0x18 = 0` and
  `+0x1a = 3`, and renders `d8fc` span rows at object key `0x2406`. Status:
  parser-produced metric clamp and copied-field cross-product to visible
  unflagged and flagged span effects.
- Claim: parser-produced descriptor lower-bound values suppress both span
  consumers without suppressing the compact glyph. Evidence: fixture
  `host-fetched lower-bound metric variant suppresses d4ac and d8fc spans`;
  host-fetched `ESC )s80W` copies first code `+0x16 = 0x0018`, range/count
  `+0x14 = 0x0600`, derived count `+0x18 = 0x05e7`, and rounded metric word
  `+0x2c = 0x1800`. `0xd4ac` consumes byte `+0x2c = 0x18`, `0xd8fc`
  consumes word `+0x16 = 0x0018`, both return `before-context-lower` at
  cursor y `21`, and the page-record still contains the compact text object
  rendered by the fixture. Status: parser-produced lower-bound cross-product
  to no-span output effect for both selected source forms.
- Claim: parser-produced descriptor upper-bound values can suppress only the
  flagged span consumer while preserving unflagged span output. Evidence:
  fixture
  `host-fetched upper-bound metric variant keeps d4ac span but suppresses d8fc`;
  host-fetched `ESC )s80W` copies range/count `+0x14 = 0x0040`, first code
  `+0x16 = 0x0004`, derived count/height `+0x18 = 0x003b`, and rounded word
  `+0x2c = 0x0020`. `0xd4ac` consumes bytes `+0x2c/+0x2d = 0/0x20`, queues
  the span object `00 00 00 00 40 00 00 01 a4 06 03 00 00 14 ...`, and
  renders the same rows as the default metric path. `0xd8fc` consumes word
  `+0x18 = 0x003b`, returns `beyond-page-extent` at cursor y `21`, and leaves
  only the compact glyph object. Status: parser-produced upper-bound
  cross-product to asymmetric visible output for both selected source forms.
- Claim: legal parser-produced descriptor metric values now cover a seven-case
  consumer matrix. Evidence: fixture
  `legal descriptor metric value matrix drives d4ac and d8fc consumers`;
  small-rounded copies `+0x14/+0x18/+0x1a/+0x2c =
  0x0009/0x0004/0x0002/0x0010`, clamped-rounded copies
  `0x0005/0x0000/0x0003/0x0014`, midpoint-rounded copies
  `0x0018/0x0013/0x0007/0x0018`, zero-rounded-offset copies
  `0x0018/0x0013/0x0000/0x0000`, negative-offset copies
  `0x0018/0x0013/0xfffe/0x0008`, lower-bound copies
  `0x0600/0x05e7/0x0005/0x1800`, and upper-bound copies
  `0x0040/0x003b/0x0005/0x0020`. The same fixture records both legal
  consumers for each case: `d4ac` span output stays visible for small,
  clamped, midpoint, zero, negative-offset, and upper values, `d4ac` exits
  `before-context-lower` for lower-bound, `d8fc` emits visible span objects
  for small, clamped, zero, and negative-offset, updates high-y `14` but
  leaves compact-only rows for midpoint, exits `before-context-lower` for
  lower-bound, and exits `beyond-page-extent` for upper-bound. The
  negative-offset row is the copied signed-byte boundary: input byte `0xfe`
  becomes word `0xfffe` and `d8fc` computes high-y `-65513`. Status:
  parser-produced legal metric value cross-product to consumer state, queued
  object, and rendered row digest.
- Claim: legal parser-produced descriptor metric boundary values now cover
  equality and signed-offset endpoints. Evidence: fixture
  `legal descriptor metric boundary values drive d4ac and d8fc consumers`;
  `d8fc-lower-equal` proves current y `21` equals copied lower word
  `+0x16 = 0x0015` and still publishes a span; `extent-equal` proves
  current y `21` plus copied height `+0x18 = 0x002b` reaches page extent `64`
  without taking the beyond-page exit; `positive-offset-max` proves input
  byte `0x7f` copies as word `+0x1a = 0x007f` and computes high-y `-106`;
  `rounded-0x0013-up` proves normal rounded input stores `+0x2c = 0x0014`;
  `rounded-0x1500-transform` proves rounded input `0x1500` stores
  `+0x2c = 0x0060` and drives `d4ac` to `beyond-page-extent`; and
  `rounded-0x1508-transform` and `rounded-0x15ff-transform` prove the
  descriptor transform discards that full low-byte range and stores the same
  `+0x2c = 0x0060`. `negative-offset-max` proves input byte `0xff` copies as
  word `+0x1a = 0xffff`; `d8fc` consumes that copied word as `65535`,
  computes high-y `-65514`, and collapses to the same rendered row digest as
  the `0xfe` case. Status: parser-produced legal boundary values to consumer
  state, queued object prefix, and rendered row digest.
- Claim: legal parser-produced descriptor metric range endpoints now cover the
  `0x17430` derived-height extremes. Evidence: fixture
  `legal descriptor metric range endpoints drive d4ac and d8fc consumers`;
  first-code zero copies `+0x14/+0x16/+0x18 = 0x0018/0x0000/0x0017`, and
  first-code `range - 1` copies `0x0015/0x0014/0x0000`. Both cases keep
  rounded word `+0x2c = 0x0008`, preserve the standard `d4ac` span digest,
  and drive `d8fc` through high-y `20` with digest
  `f830d30ea60a61f0b74a489c4b7df1bb25dc464b6765d170c19e7278a0267eab`.
  Status: parser-produced legal range endpoint to copied field, consumer
  state, queued object prefix, and rendered row digest.
- Claim: legal parser-produced descriptor metric low-nibble samples follow the
  ROM-derived rounded-word transform and reach both span consumers. Evidence: fixture
  `legal descriptor metric low-nibble rounding drives d4ac and d8fc consumers`;
  rounded inputs `0x0001`, `0x0003`, `0x0004`, `0x0005`, and `0x000f` copy to
  `+0x2c = 0x0000/0x0004/0x0004/0x0004/0x0010`. For every case, `d4ac`
  consumes the copied `+0x2c/+0x2d` fields and renders the standard segment
  span digest, while `d8fc` consumes unchanged `+0x16/+0x18/+0x1a =
  0x0004/0x0013/0x0001`, keeps high-y `20`, and renders digest
  `f830d30ea60a61f0b74a489c4b7df1bb25dc464b6765d170c19e7278a0267eab`.
  Status: parser-produced legal low-nibble transform to copied field,
  consumer state, queued object prefix, and rendered row digest.
- Claim: descriptor metric producer forms are disjoint at the selected-context
  boundary. Evidence: fixture
  `descriptor metric fields match across inline and resource contexts`;
  inline/unflagged `0x00000000` reaches `0xd4ac` and visible span rows,
  resource/flagged `0x40000000` reaches `0xd8fc` and visible span rows,
  resource/unflagged fails at compact offset-table glyph resolution, and
  inline/flagged fails before source creation because the context does not
  select offset-table form. Status: parser-produced metric payload to legal
  form cross-product and invalid cross-form boundaries.
- Claim: the two span consumers have the same documented branch contract
  around the metric fields. Evidence: fixture
  `d4ac and d8fc span consumer branch family controls flush output`; handlers
  `0xd4ac..0xd548` and `0xd8fc..0xd992`; disabled, before-lower, and
  beyond-page exits leave only the compact text object, while the high-x path
  updates `0x783188` and later CR flush produces a 28-pixel segment-list span.
  Status: parser printable to page-record/render fixture with synthetic
  metric values for both source forms.

There is no unresolved middle edge in the tested `0x1719c` type-0, type-1, or
type-2 metric paths into either `0xd4ac` or `0xd8fc`: all three payload forms
now have host-fetched evidence through visible span rows, and the consumer-side
disabled, lower-bound, page-extent, and high-x branches are fixture-backed for
both selected source forms. The legal metric matrix and boundary fixture now
prove copied descriptor values can flip the `d4ac` page-extent gate, exercise
rounded-metric clamping into `+0x2c/+0x2d`, preserve zero rounded/offset fields
through visible `d4ac` and `d8fc` span objects, preserve negative and
max-positive flagged offset bytes as copied words `0xfffe` and `0x007f`,
accept `d8fc` lower-bound equality and exact page-extent equality, move
`d8fc` visible rows, update `d8fc` without publishing a span object, suppress
both span consumers through descriptor-owned lower-bound fields, and suppress
only `d8fc` through descriptor-owned upper-bound fields while preserving
`d4ac` span output and compact glyph output. Fixture
`descriptor metric fields match across inline and resource contexts` now pins
the selected-context producer-form boundary: inline/unflagged `d4ac` and
resource/flagged `d8fc` are visible, while resource/unflagged and
inline/flagged are invalid cross-forms. The remaining producer-side work is
selected-font state combinations that change selected context records
`0x782ee6/0x782ef6`, active maps `0x782f32/0x783032`, source-object fields
`0x782d7e+0x00/+0x04/+0x0b/+0x10/+0x16`, unflagged metric bytes
`+0x2b/+0x2c/+0x2d`, flagged metric words `+0x16/+0x18/+0x1a`, pending span
fields `0x783184..0x78318a`, page-object fields, bridge context slots, or
row-construction helper inputs. External/manual naming for
consumed-but-not-staged validation fields remains open.

## Descriptor Metric Semantic Checkpoint

This checkpoint covers the parser-produced downloaded-resource metric fields
that feed the two text-span consumers. It composes the broad metric cluster
from host-fetched `ESC )s#W` descriptor bytes through `0x16fae`, `0x1719c`,
selected context form, `0xd4ac` / `0xd8fc`, page-record span objects, and
visible rows.

Field groups:

- Canonical descriptor payload fields:
  - payload `+0x14`: range/count word staged by the descriptor validator and
    copied by `0x1719c`.
  - payload `+0x16`: first-code/lower-bound word consumed by `0xd8fc`.
  - payload `+0x18`: derived height/count cache, computed as
    `+0x14 - +0x16 - 1` by `0x17430`, copied by `0x1719c`, and consumed by
    `0xd8fc`.
  - payload `+0x1a`: signed flagged offset word written by `0x1762a`, copied
    by `0x1719c`, and consumed by `0xd8fc`.
  - payload `+0x2c`: rounded/clamped unflagged metric word written by
    `0x1757a`, copied by `0x1719c`, and consumed as bytes `+0x2c/+0x2d` by
    `0xd4ac`.
  - payload `+0x2b`: unflagged alternate-offset byte. It remains zero in the
    covered `0x1719c` metric fixtures and is therefore firmware bookkeeping
    for this checkpoint, not a proved canonical descriptor input.
- Canonical selected-context forms:
  - bit-30-clear inline/fixed-record context is the legal producer form for
    unflagged `0xd4ac`.
  - bit-30-set resource/offset-table context is the legal producer form for
    flagged `0xd8fc`.
  - fixture `descriptor metric fields match across inline and resource
    contexts` proves the swapped resource/unflagged and inline/flagged forms
    are invalid boundaries, not equivalent fallbacks.
- Derived/cache state:
  - staged descriptor base `0x782862` and optional symbol staging
    `0x782842..0x782856` are temporary producer storage before `0x1719c`
    allocation.
  - `0x783184..0x78318a` are pending-span state updated by `0xd4ac` and
    `0xd8fc` after metric consumption.
  - page-record segment-list or fixed-list objects are derived output from
    `0x12714`, not canonical descriptor state.
- Parser scratch:
  - restored `ESC )s#W` command records, payload budget `0x783140`, validation
    cursor state, and consumed-but-not-staged descriptor bytes are parser
    scratch for this checkpoint.
- Firmware bookkeeping:
  - payload type byte `+0x0c`, allocation units `0x7827ba`, and resource
    allocation/free-list state control whether a payload exists; they do not
    change the metric consumer formulas once the payload is installed.
- Unknown:
  - exact HP manual names for every consumed-but-not-staged descriptor table
    field are still not correlated.

Writers:

- `0x16fae..0x17016` walks the 32-entry descriptor validation table at
  `0x16eae`, reads bytes/words through `0x1599c`, `0x159b6`, `0x159d4`, and
  `0x159f6`, and stages fields under `0x782862`.
- `0x17430..0x1749c` writes canonical `+0x14` and derived/cache `+0x18`,
  including the `+0x18 = +0x14 - +0x16 - 1` formula.
- `0x1757a..0x175b8` writes `+0x2c` as
  `min((value + 2) >> 2, word(+0x14)) << 2`.
- `0x1762a..0x1763c` writes signed-byte offset input into word `+0x1a`.
- `0x1719c..0x1725c` copies the staged sparse header and metric fields into
  the allocated payload.
- `0xd4ac` and `0xd8fc` consume the copied fields and update pending-span
  state or exit through disabled, lower-bound, or page-extent branches.

Readers and consumers:

- `0xd4ac..0xd548` consumes unflagged bytes `+0x2b`, `+0x2c`, and `+0x2d`.
  Visible effects include high-y changes, page-extent acceptance/rejection,
  and later segment-list output through `0x12714` and `0x1f812`.
- `0xd8fc..0xd992` consumes flagged words `+0x16`, `+0x18`, and `+0x1a`.
  Visible effects include lower-bound equality, exact page-extent equality,
  signed-offset high-y changes, and compact-only outcomes when no span object
  is published.
- `0x12714`, `0x13520` / `0x135f0`, `0x136d2`, `0x1f812`, and `0x1f756`
  consume the pending-span result and turn it into rendered segment-list or
  fixed-list rows.

Output effect:

- Host-fetched `ESC )s80W` type-0, type-1, and type-2 descriptor payloads enter
  `0x16fae`, stage validated metric fields below `0x782862`, and copy the
  accepted sparse header through `0x1719c..0x1725c`. Once selected, the legal
  inline/unflagged form reaches `0xd4ac`; the legal resource/flagged form
  reaches `0xd8fc`. Swapping those forms fails at the selected-map/render
  boundary instead of creating a third metric path.
- `0xd4ac` uses copied bytes `+0x2b/+0x2c/+0x2d` to gate and update pending-span
  high-y for inline/unflagged text. The documented metric variants change the
  ROM inputs that matter to this consumer: copied `+0x2c` can suppress the span
  on the page-extent gate, restore the standard span when rounding crosses a
  byte boundary, or leave compact glyph output without a span object.
- `0xd8fc` uses copied words `+0x16/+0x18/+0x1a` to gate and update pending-span
  high-y for resource/flagged text. Lower-bound equality is accepted, exact
  page-extent equality is accepted, and the page-extent comparison consumes the
  derived height before the alternate y offset can recover an overlarge span.
- The producer formulas that feed those consumers are fixed by ROM helpers:
  `0x17430` derives range/count fields and `+0x18`, `0x1757a` derives rounded
  and clamped `+0x2c`, `0x1762a` sign-extends the alternate offset, and
  `0x1719c` copies the staged values into the installed payload.
- The legal value matrix covers the semantic classes behind those formulas:
  first-code zero, range-minus-one, range one/two, lower-bound and upper-bound
  gates, exact page-extent fenceposts, low-nibble rounding, byte-boundary
  rounding, clamped rounding, midpoint rounding, signed positive and negative
  offsets, and mixed cases where all three producer helpers change copied
  fields together. Additional legal values are cross-products of these formulas
  and consumer gates unless they change a named copied field or branch product.
- Accepted consumer updates flow into pending span state `0x783184..0x78318a`.
  A low-water flush calls `0x12714`; portrait output becomes segment-list span
  records through `0x13520` / `0x135f0`, while landscape output becomes
  fixed-list records through `0x136d2`. The render side consumes those records
  through `0x1edc6`, `0x1ef6a`, and the span render helpers.

Confidence:

- High for the copied-field formulas, selected-context legal forms, consumer
  branch behavior, and page-record/span effects named above because each claim
  is backed by ROM disassembly and host-fetched descriptor routes. Fixture row
  digests are supporting branch anchors, not an independent rendered-row oracle.
- Medium for broader descriptor compatibility only where a new byte stream
  changes a named ROM input to the documented path: selected context records,
  active maps, source-object fields, copied metric fields, pending span
  fields, page-object fields, bridge context slots, or row-construction
  helper inputs. Exact HP manual labels for non-staged fields remain open;
  additional legal metric values are cross-products of the documented producer
  formulas and consumer gates.

Fixture evidence:

- `host-fetched 0x1719c payload metrics feed d4ac span rows`
- `host-fetched 0x1719c payload metrics feed d8fc span rows`
- `host-fetched type-2 0x1719c payload metrics feed d4ac and d8fc span rows`
- `host-fetched type-1 0x1719c payload metrics feed d4ac and d8fc span rows`
- `host-fetched metric variant changes d4ac gate and d8fc rows`
- `host-fetched clamped metric variant changes d4ac gate and d8fc rows`
- `host-fetched lower-bound metric variant suppresses d4ac and d8fc spans`
- `host-fetched upper-bound metric variant keeps d4ac span but suppresses d8fc`
- `descriptor metric fields match across inline and resource contexts`
- `legal descriptor metric value matrix drives d4ac and d8fc consumers`
- `legal descriptor metric boundary values drive d4ac and d8fc consumers`
- `legal descriptor metric extent fenceposts drive d4ac and d8fc consumers`
- `legal descriptor metric range endpoints drive d4ac and d8fc consumers`
- `legal descriptor metric mixed values drive d4ac and d8fc consumers`
- `legal descriptor metric tight range values drive d4ac and d8fc consumers`
- `legal descriptor metric low-nibble rounding drives d4ac and d8fc consumers`
- `legal descriptor metric byte-boundary rounding drives d4ac and d8fc
  consumers`
- `d4ac and d8fc span consumer branch family controls flush output`

Disassembly evidence:

- `generated/disasm/ic30_ic13_font_resource_validate_016fae.lst`:
  descriptor table driver `0x16fae..0x17016`.
- `generated/disasm/ic30_ic13_font_resource_validate_predicates_017358.lst`:
  metric writers `0x17430`, `0x1757a`, and `0x1762a`.
- `generated/disasm/ic30_ic13_font_resource_payload_initializer_01719c.lst`:
  staged payload copy `0x1719c..0x1725c`.
- `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`:
  span consumers `0xd4ac..0xd548` and `0xd8fc..0xd992`.
- `generated/disasm/ic30_ic13_active_object_scan_014398.lst`:
  active-candidate scan and selected-slot write `0x14398..0x14406`.
- `generated/disasm/ic30_ic13_object_compare_013a48.lst`:
  selected-font snapshot check `0x13a48` and active survivor comparator
  `0x13c06`.
- `generated/disasm/ic30_ic13_text_span_flush_012714.lst` and
  `generated/disasm/ic30_ic13_display_list_helpers_013386.lst`:
  pending-span output into page-record span objects.

Unresolved middle edges:

- `0x16fae..0x1719c`: seven bounded validation no-install forms and the
  short-budget entry-5 failure preserve following printable output. These
  cover every ROM-internal predicate helper that can reject a descriptor;
  remaining validation work is external/manual naming for
  consumed-but-not-staged fields.
- `0x17430..0x1763c`: the covered legal matrix proves the main range/count,
  first-code-zero and range-minus-one endpoints, rounded/clamped,
  signed-offset, equality, low-nibble, byte-boundary, and low-byte-discard
  behavior.
  Additional legal metric values remain cross-products rather than new
  semantic edges.
- `0xd4ac..0xd992`: disabled, lower-bound, page-extent, high-x, exact extent,
  and visible span branches are fixture-backed. Remaining risk is selected
  source/metric combinations that change one of the consumed fields or branch
  products: unflagged `+0x2b/+0x2c/+0x2d`, flagged
  `+0x16/+0x18/+0x1a`, span enable `0x783184`, pending bounds
  `0x783186..0x78318a`, `0x12714` page-extent gate, orientation branch, or
  resulting segment-list/fixed-list object fields. The consumer contract for
  the copied fields is documented.
- Manual descriptor labels: several consumed-but-not-staged fields are named
  by ROM effect only; external HP documentation correlation remains open.

## Macro And Control Re-entry

Macro replay shares this font-context bridge. `0xe65c` consumes either a
call-context entry or static record, uses refresh bytes to call
`0x13eb8(0)` and/or `0x13eb8(1)`, then calls `0xc428(0x782f06)`.

The composed fixture drives refresh slots `0` and `1` through `0x13eb8`,
rebuilds maps `0x782f32` and `0x783032`, then installs context record
`0x782ef6` into page-root font slot `0` through `0xc428`.

SO/SI direct controls also use the bridge:

- SO reaches `0xc6b8`, attempts `0xc428(1)`, and sets `0x782f06 = 1` on
  success.
- SI reaches `0xc68a`, attempts `0xc428(0)`, and clears `0x782f06` on
  success.

The mixed SO/SI fixture proves printable bytes after those controls queue
selector-1 and selector-0 compact objects through the same page-root and
render-record context slots.

## Reproduction Contract

A byte-stream reproduction must preserve these behaviors:

- Font selection updates the active primary/secondary context record before
  printable bytes are queued.
- The selected context/resource longword, not raw bitmap data and not the
  `0x782ee6` / `0x782ef6` record address, is what page-root `+0x2c` stores.
- `0x1393a` maps original host bytes through the active 256-byte map before
  text object creation; compact payload byte 0 is the mapped glyph byte.
- The renderer glyph identity is `(selected context longword, mapped glyph
  byte)`, not `(PCL font request, original host byte)`.
- Text source byte `+0x10` chooses the flagged or unflagged placement/span
  path.
- `0xd3b2` and `0xd824` must mark the selected page-root font slot live before
  queueing compact text.
- Span metrics come from the selected context/resource record and can change
  visible pixels by changing pending-span high-y, flush timing, and rendered
  segment-list rows.
- Metric source form matters: bit-30-clear inline/unflagged contexts feed
  `0xd4ac`, while bit-30 resource/flagged contexts feed `0xd8fc`; swapped
  forms are invalid and must not be treated as equivalent fallbacks.
- `0xc428` may fail with `0x11` when all 16 page-root font slots are live and
  none match; that path must not silently install a new context.

## Remaining Edges

- `0x13eb8` selection, map rebuild, page-root install, printable source
  capture, and low-water span effects are documented in the checked-in
  checkpoints above:
  `Active Candidate And Map Cache Checkpoint`, `Page-Root Context Install`,
  `Printable Source Capture`, `Selected-Font Residual Routing Checkpoint`, and
  `Span Metric Consumers`. Those checkpoints name the parser records, request
  fields, dirty flags, selected context records, map fields, page-root slot
  fields, source-object bytes, later consumers, output effects, and exact
  residual boundaries. Fixtures remain supporting checks for representative
  streams, not the owner of the semantic route.
- The documented primary built-in selection request
  `ESC (s0p10h12v0s0b3T!!` and secondary request
  `ESC )s0p16h8v0s0b0T SO !!` run from parser bytes through `0xc580`,
  `0x13eb8`, `0x144d2`, `0x14c64`, page-root context install, source capture
  `0x1393a`, compact object producer `0x12f2e`, bridge `0x1edc6`, and compact
  renderer `0x1effe -> 0x1f354`. The secondary route additionally crosses SO
  handler `0xc6b8`, context `0xc00ae122`, and HMI `18`.
  Symbol-miss fallback is documented for primary
  `ESC (1234U ESC (s0p10h12v0s0b3T!!` from requested word `0x9a55` to fallback
  word `0x0115`, and for secondary
  `ESC )1234U ESC )s0p16h8v0s0b0T SO !!` through remembered word `0x000e` or
  fallback-table word `0x000e`.
  Final-`X` follows the same visible-output route for primary built-in
  `ESC (7X!!`, secondary built-in `ESC )8X SO !!`, primary bit-30-clear
  `ESC (4660X!`, and secondary bit-30-clear `ESC )4660X SO !`; direct
  `0x17708` non-selected exits preserve prior primary or secondary visible
  tails instead of installing a new context.
- Current-font RAM handoff is documented as the same page-root slot route:
  primary seeded `0x782ee6` crosses `0xc428` / `0xc4fc` into existing
  page-root slot `0`, and secondary seeded `0x782ef6` crosses into existing
  slot `1`. The parser-fed SI/SO streams compose those RAM handoff states with
  host-fetched font-selection bytes and later printable rows.
  Remaining handoff risk is exact selected-font field combinations, not an
  unknown parser-to-printable edge. New work must show a different value or
  branch for at least one documented boundary: `0x13eb8` refresh state,
  selected context longword `0x782ee6` / `0x782ef6`, selected target
  `0x7828de`, selected slot pointer `0x7828a8`, page-root font slot
  `0x78297e`, page-root context slots `+0x2c..+0x68`, primary/secondary maps
  `0x782f32` / `0x783032`, source-object fields
  `0x782d7e+0x00/+0x04/+0x0b/+0x10/+0x16`, compact selector class,
  HMI/cursor advance, or compact row-helper inputs.
- Broader metric producer work is now selected-font state expansion, not an
  unresolved parser-produced page boundary. Existing host-stream
  downloaded-font owner routes document install, visible glyph rendering,
  and `0x1719c` type-0, type-1, and type-2 payloads feeding both `0xd4ac` and
  `0xd8fc` span rows; fixture coverage is a supporting consistency check for
  those documented branches. The legal descriptor metric matrix plus boundary
  fixture now
  covers visible extent flips, clamping, zero rounded/offset span publication,
  normal rounded input `0x0013` storing `+0x2c = 0x0014`, negative and
  max-positive offset copied words `0xfffe`/`0x007f`, `d8fc` lower-bound and
  page-extent equality, a midpoint `d8fc` state update without a span object,
  low-nibble rounded inputs `0x0001`, `0x0003`, `0x0004`, `0x0005`, and
  `0x000f` storing `+0x2c = 0x0000/0x0004/0x0004/0x0004/0x0010`, rounded
  low-byte discard for `0x1508`, lower-bound
  suppression for both consumers, and asymmetric upper-bound suppression of
  `0xd8fc` while `0xd4ac` still renders a span. The extent-fence matrix
  proves derived heights `42`, `44`, and `45` at the `d8fc` page-extent gate:
  height `42` with offset `0` renders high-y `21`, while heights `44` and
  `45` exit `beyond-page-extent` even with offsets `1` and `2`.
  Fixture `descriptor metric fields match across inline and resource contexts`
  now pins the legal producer-form boundary and both invalid swapped forms.
  The producer formulas are documented from disassembly: `0x17430` derives
  `+0x18 = +0x14 - +0x16 - 1`, `0x1757a` writes
  `+0x2c = min((value + 2) >> 2, word(+0x14)) << 2`, `0x1762a` writes signed
  offset word `+0x1a`, and `0x1719c` copies those staged fields into the
  allocated payload.
  Seven bounded `0x16fae` validation no-install forms plus the short-budget
  `ESC )s8W` entry-5 failure now preserve following printable output and cover
  every ROM-internal rejecting predicate family. Additional legal metric values
  inside the inline/unflagged and resource/flagged forms are cross-products of
  the pinned matrix, boundary, extent-fence, range-endpoint, mixed-value,
  tight-range, low-nibble, and byte-boundary fixtures. The remaining gap is
  selected-font state combinations that change selected context records,
  active maps, source-object fields, copied metric fields, pending span
  fields, page-object fields, bridge context slots, or row-construction helper
  inputs, plus external/manual naming for consumed-but-not-staged fields.
