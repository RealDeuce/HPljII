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

Evidence:

- `generated/disasm/ic30_ic13_pitch_mode_handler_00c390.lst`: handler body
  `0xc390..0xc426`.
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
[symbol-map-patching.md](symbol-map-patching.md). It gates on the selected
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

## Visible Built-In Selection Boundary

Fixture `parsed primary built-in font selection feeds visible page-record rows`
now composes the primary font-selection command family into visible compact
text output. One modeled `0xa904` ring stream contains
`ESC (s0p10h12v0s0b3T!!`; the lowercase selection phase routes directly
through writers `0xc930`, `0xc89c`, `0xc6ec`, `0xc780`, and `0xc840` while
parser mode 13 stays active, then final uppercase `T` reaches wrapper
`0x1205a`, which calls `0xc7e0` and common refresh `0xc580`. The sibling
uppercase wrappers in
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
same 38 row strings pinned by the fixture. The first nonblank row is:

```text
.............###...........................###...
```

This checkpoint closes the semantic path from parsed built-in font-selection
bytes through `0x13eb8`, `0x144d2`, `0x14c64`, printable `0xd04a`,
page-record queueing, `0x1edc6`, and compact glyph rendering. Fixture
`inline primary font selection stream renders visible rows` now runs the same
host-fetched stream through one mixed-stream state: the font-selection event
writes current-font RAM `0x782ee6 = 0xc008004c`, installs context slot
`0xc008004c` in the page record, derives HMI `30`, and the following two
printable bytes read that context without a separate printable-phase injection.

Fixture `primary symbol miss falls back before visible page-record rows` adds
the primary symbol-set fallback leg before that same visible-output path. The
modeled stream is `ESC (1234U ESC (s0p10h12v0s0b3T!!`. Symbol-set parsing
routes through `0x11eb6`, `0x1201e`, and `0x120be`, producing requested word
`0x9a55`. The `0x156de` requested pass finds no class-zero match, so the
fallback table supplies active word `0x0115`; the prune pass keeps survivor
slot pointers `0x782354`, `0x782364`, and `0x782374`. The following primary
font-selection command reuses selected context `0xc008004c`, primary map
`0x782f32`, and HMI `30`. The two printable `!` bytes then produce the same
compact object prefix, render-record context slot, and rows as the primary
fixture above.

Fixture `live primary current-font RAM install feeds SI page-record rows`
narrows that handoff gap for the primary path. It seeds current-font RAM
records with primary `0x782ee6 = 0xc008004c` and secondary
`0x782ef6 = 0xc00ae122`, starts with an existing page root `0x78297a`,
page-root slot `1` live as the secondary context, and then feeds `SI !!`.
Handler `0xc68a` calls `0xc428(0)`, which reads `0x782ee6`, calls `0xc4fc`,
chooses page-root context slot `0` as the first inactive slot, writes
`0xc008004c`, and sets `0x78297e = 0`. The following `0xd04a` / `0x1393a`
printable events read context slot `0` from the page-root context slots, map
host `0x21` to glyph `0x00`, and produce the same primary compact object
prefix and visible Courier rows. Because the root already exists, this fixture
has page-root allocation count `0`; it is a current-font-RAM-to-page-root
handoff fixture, not a first-root-allocation fixture.

Fixture `parsed primary selection current-font RAM feeds SI visible rows`
composes the parsed primary selection stream with that handoff. The combined
host-fetched stream is `ESC (s0p10h12v0s0b3T SI !!`: the selection phase uses
the same handlers and `0x144d2` context update as the primary visible
selection fixture, producing `0x782ee6 = 0xc008004c` and map `0x782f32`; the
tail `SI !!` then follows the live primary handoff fixture through
`0xc68a`, `0xc428(0)`, `0xc4fc`, page-root slot `0`, and two printable
`0xd04a` events. It reaches the same documented compact-object fields and
model-derived visible rows as the pinned parsed primary visible path.

Fixture
`parsed secondary built-in font selection feeds visible SO page-record rows`
does the same for the secondary selection and SI/SO bridge. The modeled ring
stream contains `ESC )s0p16h8v0s0b0T SO !!`; the selection handlers are the
same lowercase writer family and final uppercase `0x1205a` refresh boundary,
but `0x13eb8` writes secondary context record `0x782ef6` with selected
longword `0xc00ae122`.

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

Fixture `live secondary current-font RAM install feeds SO page-record rows`
narrows the live handoff gap for that secondary path. It seeds current-font RAM
records with primary `0x782ee6 = 0xc008004c` and secondary
`0x782ef6 = 0xc00ae122`, starts with an existing page root `0x78297a`,
page-root slot `0` live as the primary context, and then feeds `SO !!`.
Handler `0xc6b8` calls `0xc428(1)`, which reads `0x782ef6`, calls `0xc4fc`,
chooses page-root context slot `1` as the first inactive slot, writes
`0xc00ae122`, and sets `0x78297e = 1`. The following `0xd04a` / `0x1393a`
printable events read context slot `1` from the page-root context slots, map
host `0x21` to glyph `0x00`, and produce the same secondary compact object
prefix and visible rows. Because the root already exists, this fixture has
page-root allocation count `0`; it is a current-font-RAM-to-page-root handoff
fixture, not a first-root-allocation fixture.

Fixture `parsed secondary selection current-font RAM feeds SO visible rows`
adds the secondary composed contract. The combined host-fetched stream is
`ESC )s0p16h8v0s0b0T SO !!`: the selection phase writes
`0x782ef6 = 0xc00ae122` and map `0x783032`, then the tail `SO !!` follows
`0xc6b8`, `0xc428(1)`, `0xc4fc`, page-root slot `1`, and two printable
`0xd04a` events. It reaches the same documented compact-object fields and
model-derived visible rows as the pinned parsed secondary visible path.

Fixture `inline secondary font selection stream renders SO visible rows` runs
that same secondary stream through one mixed-stream state instead of a split
selection/page phase: `ESC )s0p16h8v0s0b0T` writes current-font RAM
`0x782ef6 = 0xc00ae122`, updates page-record context slot `1`, SO selects
slot `1`, refreshes the active HMI to `18`, and both following printable bytes
queue the same `0xc00ae122` source context, compact object prefix, and rows as
the pinned secondary fixture.

Fixture
`secondary symbol miss falls back before visible SO page-record rows` adds
the secondary symbol-set fallback leg before that same visible-output path.
The modeled stream is `ESC )1234U ESC )s0p16h8v0s0b0T SO !!`.
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
secondary fixture above.

Fixture
`remembered secondary symbol feeds visible SO page-record rows` covers the
remembered source before that fallback table. The modeled stream is still
`ESC )1234U ESC )s0p16h8v0s0b0T SO !!`, but the fixture seeds remembered
secondary word `0x000e` at `0x782f0a`. The `0x156de` requested pass misses
word `0x9a55`; the remembered pass first probes slot pointer `0x782324`,
record `0x019d18`, candidate word `0x0115`, and rejects it, then matches
slot pointer `0x782330`, record `0x01a984`, candidate word `0x000e`. That
sets active secondary word `0x000e` at `0x783146`, keeps survivor slot
pointers `0x782330`, `0x782340`, and `0x782350`, writes selected context
`0xc00ae122` through `0x144d2`, rebuilds map `0x783032` through `0x14c64`,
crosses SO handler `0xc6b8`, and renders the same compact object prefix and
row digest
`b8ee0f8dd3e6ed70afa219bc00605d75249ae047a67fb67189693057d7936e6c` as the
secondary fixture above.

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
rendered rows. External/manual naming for consumed-but-not-staged validation
fields remains open.

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

- Fixtures `host-fetched 0x1719c payload metrics feed d4ac span rows` and
  `host-fetched 0x1719c payload metrics feed d8fc span rows` prove the
  type-0 host-fetched `ESC )s80W` payload reaches each legal consumer and
  changes visible span rows.
- Fixtures `host-fetched type-1 0x1719c payload metrics feed d4ac and d8fc
  span rows` and `host-fetched type-2 0x1719c payload metrics feed d4ac and
  d8fc span rows` prove the same metric contract survives type-1 and type-2
  payload forms.
- Fixture `host-fetched metric variant changes d4ac gate and d8fc rows` proves
  changing parser-produced `+0x2c` and `+0x1a` flips the tight `d4ac` page
  gate and moves the rendered `d8fc` span key.
- Fixture `host-fetched clamped metric variant changes d4ac gate and d8fc
  rows` proves a reduced range/count clamps `+0x2c` to `0x0014`, flips the
  `d4ac` gate, and changes `d8fc` high-y.
- Fixture `host-fetched lower-bound metric variant suppresses d4ac and d8fc
  spans` proves descriptor-owned lower-bound fields can suppress both span
  consumers while preserving compact glyph output.
- Fixture `host-fetched upper-bound metric variant keeps d4ac span but
  suppresses d8fc` proves a wider range/count can preserve unflagged span
  output while `d8fc` exits `beyond-page-extent`.
- Fixture `legal descriptor metric value matrix drives d4ac and d8fc
  consumers` covers small-rounded, clamped-rounded, midpoint-rounded,
  zero-rounded-offset, negative-offset, lower-bound, and upper-bound legal
  descriptor values behind the two legal selected forms.
- Fixture `legal descriptor metric boundary values drive d4ac and d8fc
  consumers` proves `d8fc` lower-bound equality, exact page-extent equality,
  max positive offset byte `0x7f`, max negative offset byte `0xff`, normal
  rounded `0x0013 -> +0x2c = 0x0014`, and the `0x1500` / `0x1508` /
  `0x15ff -> +0x2c = 0x0060` rounded-transform family.
- Fixture `legal descriptor metric extent fenceposts drive d4ac and d8fc
  consumers` proves derived heights `42`, `44`, and `45` around the `d8fc`
  page-extent gate. Height `42` with offset `0` renders; heights `44` and
  `45` exit `beyond-page-extent` even when offsets `1` and `2` would move the
  final high-y, proving the extent gate consumes derived height before offset
  placement can recover the span.
- Fixture `legal descriptor metric range endpoints drive d4ac and d8fc
  consumers` proves `0x17430` accepts first-code zero as
  `+0x14/+0x16/+0x18 = 0x0018/0x0000/0x0017` and the range-minus-one endpoint
  as `0x0015/0x0014/0x0000`, with both legal forms still feeding the same
  documented `d4ac` and `d8fc` visible output paths.
- Fixture `legal descriptor metric mixed values drive d4ac and d8fc
  consumers` proves multi-field legal combinations where `0x17430`,
  `0x1757a`, and `0x1762a` all change: middle-range
  `0x0008/0x0030/0x002a/0x02` copies `+0x18/+0x1a/+0x2c =
  0x0027/0x0002/0x002c`, suppresses `d4ac`, and renders `d8fc`; rounded
  `0x00ff` caps copied `+0x2c` to `0x00c0`; offset byte `0x80` sign-extends
  to `+0x1a = 0xff80`; and late first-code `0x002f` derives `+0x18 = 0`,
  keeping `d4ac` visible while `d8fc` exits before lower bound.
- Fixture `legal descriptor metric tight range values drive d4ac and d8fc
  consumers` proves the smallest legal range/count cross-products: range one
  copies `+0x14/+0x16/+0x18 = 0x0001/0x0000/0x0000`, range two copies
  `0x0002/0x0001/0x0000`, and both still feed visible `d4ac`/`d8fc` output
  while varying rounded output and signed offset endpoints.
- Fixture `legal descriptor metric low-nibble rounding drives d4ac and d8fc
  consumers` proves inputs `0x0001`, `0x0003`, `0x0004`, `0x0005`, and
  `0x000f` copy to `+0x2c = 0x0000/0x0004/0x0004/0x0004/0x0010` and keep
  both consumers on the documented visible output paths.
- Fixture `legal descriptor metric byte-boundary rounding drives d4ac and
  d8fc consumers` proves rounded inputs `0x00fd`, `0x00fe`, `0x0101`, and
  `0x0102` copy to `+0x2c = 0x00fc/0x0100/0x0100/0x0104`; a range/count
  `0x0040` sibling caps `0x0102` back to `0x0100`. The copied `0x00fc` case
  leaves `d4ac` on compact-only output, while crossing to `0x0100` restores
  the standard `d4ac` span digest. The same submatrix keeps `d8fc` at
  `beyond-page-extent` because the derived `+0x18` exceeds the page extent.

Confidence:

- High for the copied-field formulas, selected-context legal forms, consumer
  branch behavior, and visible span effects for the cited cases because each
  claim is backed by host-fetched descriptor fixtures, disassembly, and
  rendered row digests.
- Medium for full descriptor compatibility only where selected-font state
  combinations change selected context records, active maps, source-object
  fields, copied metric fields, pending span fields, page-object fields,
  bridge context slots, or rendered rows. Exact HP manual labels for
  non-staged fields remain open; additional legal metric values are
  cross-products of the documented producer formulas and consumer gates.

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
  capture, and low-water span effects are fixture-backed for the primary and
  secondary cases above. The primary built-in selection request
  `ESC (s0p10h12v0s0b3T!!` is driven from parser bytes to visible rows in one
  mixed-stream state by fixture
  `inline primary font selection stream renders visible rows`. The secondary
  built-in selection request `ESC )s0p16h8v0s0b0T SO !!` is also driven in one
  mixed-stream state by fixture
  `inline secondary font selection stream renders SO visible rows`, including
  SO handler `0xc6b8`, context `0xc00ae122`, and HMI `18`.
  Symbol-miss fallback is fixture-backed for primary
  `ESC (1234U ESC (s0p10h12v0s0b3T!!` from requested word `0x9a55` to fallback
  word `0x0115`, and for secondary
  `ESC )1234U ESC )s0p16h8v0s0b0T SO !!` through both remembered word
  `0x000e` and fallback-table word `0x000e`.
  Final-`X` now has the same visible-output treatment for primary built-in
  `ESC (7X!!`, secondary built-in `ESC )8X SO !!`, primary bit-30-clear
  `ESC (4660X!`, and secondary bit-30-clear `ESC )4660X SO !`; the direct
  `0x17708` non-selected exits are also carried into preserved primary and
  secondary visible tails.
  The primary current-font RAM handoff from seeded `0x782ee6` through
  `0xc428` / `0xc4fc` into existing page-root slot `0` is fixture-backed by
  `live primary current-font RAM install feeds SI page-record rows`. The
  secondary handoff from seeded `0x782ef6` into existing page-root slot `1` is
  fixture-backed by
  `live secondary current-font RAM install feeds SO page-record rows`.
  The composed fixtures `parsed primary selection current-font RAM feeds SI
  visible rows` and
  `parsed secondary selection current-font RAM feeds SO visible rows` tie
  host-fetched font-selection bytes to those RAM handoff fixtures and matching
  visible rows for existing page roots.
  Remaining handoff risk is exact selected-font field combinations, not an
  unknown parser-to-printable edge. New work must show a different value or
  branch for at least one documented boundary: `0x13eb8` refresh state,
  selected context longword `0x782ee6` / `0x782ef6`, selected target
  `0x7828de`, selected slot pointer `0x7828a8`, page-root font slot
  `0x78297e`, page-root context slots `+0x2c..+0x68`, primary/secondary maps
  `0x782f32` / `0x783032`, source-object fields
  `0x782d7e+0x00/+0x04/+0x0b/+0x10/+0x16`, compact selector class,
  HMI/cursor advance, or rendered rows.
- Broader metric producer work is now selected-font state expansion, not an
  unresolved parser-produced page boundary. Existing host-stream
  downloaded-font fixtures prove install, visible glyph rendering,
  and `0x1719c` type-0, type-1, and type-2 payloads feeding both `0xd4ac` and
  `0xd8fc` span rows; the shared span-consumer branch family is also
  fixture-backed. The legal descriptor metric matrix plus boundary fixture now
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
  fields, page-object fields, bridge context slots, or rendered rows, plus
  external/manual naming for consumed-but-not-staged fields.
