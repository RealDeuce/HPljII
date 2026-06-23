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
- `generated/disasm/ic30_ic13_font_candidate_activate_01569c.lst`
- `generated/disasm/ic30_ic13_font_id_select_017708.lst`
- `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`
- `generated/analysis/ic30_ic13_font_context_bridge.md`
- `generated/analysis/ic30_ic13_text_glyph_index_flow.md`
- `tools/render_fixture_harness.py`, fixtures:
  - `0xc580 dirty primary branch installs page-root font context`
  - `0xc580 dirty secondary branch installs page-root font context`
  - `0xc580 full live-slot branch reuses matching page-root font context`
  - `0x13eb8 refresh carries parsed primary font selection to dispatch`
  - `0x13eb8 refresh carries parsed secondary font selection to dispatch`
  - `parsed primary built-in font selection feeds visible page-record rows`
  - `parsed secondary built-in font selection feeds visible SO page-record rows`
  - `live primary current-font RAM install feeds SI page-record rows`
  - `live secondary current-font RAM install feeds SO page-record rows`
  - `secondary symbol miss falls back before visible SO page-record rows`
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

Unknown:

- The bridge from selected context records to span metrics is documented for
  concrete built-in, synthetic inline/downloaded, and host-fetched `0x1719c`
  downloaded payload fixtures for both `0xd4ac` and `0xd8fc`, but every
  possible built-in/downloaded metric-byte combination is not yet proven by
  parser-produced page comparisons.

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

`0x14c64` chooses the map-building path from the selected context form:

- bit-30 set / offset-table form: rebuilds a base range through `0x14d9c`,
  then applies `0x14f16` symbol-set patching and `0x1440c` state snapshot.
- bit-30 clear / fixed-record form: rebuilds through `0x14e24` and
  `0x14eb6`, then applies the same `0x14f16` / `0x1440c` tail.

## Visible Built-In Selection Boundary

Fixture `parsed primary built-in font selection feeds visible page-record rows`
now composes the primary font-selection command family into visible compact
text output. One modeled `0xa904` ring stream contains
`ESC (s0p10h12v0s0b3T!!`; the selection phase routes through handlers
`0xc930`, `0xc89c`, `0xc6ec`, `0xc780`, `0xc840`, and `0x1205a`, then the
existing `0x13eb8` refresh chooses selected longword `0xc008004c`.

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
page-record queueing, `0x1edc6`, and compact glyph rendering. It does not yet
claim live CPU memory continuity between the command parser's current-font RAM
record and the page-record runner; the fixture injects the selected context
longword from the pinned `0x13eb8` result into the printable/page-record
phase.

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

Fixture
`parsed secondary built-in font selection feeds visible SO page-record rows`
does the same for the secondary selection and SI/SO bridge. The modeled ring
stream contains `ESC )s0p16h8v0s0b0T SO !!`; the selection handlers are the
same `0xc930`, `0xc89c`, `0xc6ec`, `0xc780`, `0xc840`, and `0x1205a` family,
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
- It skips live slots where `0x78297f+n == 1`.
- It accepts an existing matching context or the first inactive slot.
- It returns `0x11` if all 16 slots are live and none match.
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

`0xc428` also refreshes HMI/cache state from the selected context:

- If context byte `+0x04` is zero, it treats context `+0x00` as an
  inline/fixed-record pointer, reads selected record byte `+0x19` into
  `0x78318e`, and may derive `0x78315c` from selected record word `+0x1a`.
- If context byte `+0x04` is nonzero, it treats context `+0x00` as an
  offset-table/built-in pointer, reads selected record byte `+0x21` into
  `0x78318e`, and may derive `0x78315c` through `0x10550` from selected
  record longword `+0x24`.

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
  `parsed primary built-in font selection feeds visible page-record rows`;
  stream `ESC (s0p10h12v0s0b3T!!`; selected context `0xc008004c`; HMI
  `30`; printable handlers `0xd04a, 0xd04a`; queued object prefix
  `00 00 00 00 00 00 00 02 00 6a 00 00 68 02`; render-record context slot
  `0xc008004c`; first visible row
  `.............###...........................###...`. Status:
  parser-produced selection plus modeled selected-context handoff to
  visible-output fixture.
- Claim: parsed secondary built-in font-selection bytes can determine visible
  compact text rows after SO selects the secondary context. Evidence: fixture
  `parsed secondary built-in font selection feeds visible SO page-record rows`;
  stream `ESC )s0p16h8v0s0b0T SO !!`; selected context `0xc00ae122`; HMI
  `18`; handlers `0xc6b8, 0xd04a, 0xd04a`; queued object prefix
  `00 00 00 00 00 01 00 02 00 c9 00 00 cb 01`; render-record context slots
  `(0xc008004c, 0xc00ae122)`; first visible row
  `.........################..################...###`. Status:
  parser-produced selection plus modeled selected-context handoff to
  visible-output fixture.
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
  prints installed glyph`; documented in [downloaded-fonts.md](downloaded-fonts.md).
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
- Claim: the two span consumers have the same documented branch contract
  around the metric fields. Evidence: fixture
  `d4ac and d8fc span consumer branch family controls flush output`; handlers
  `0xd4ac..0xd548` and `0xd8fc..0xd992`; disabled, before-lower, and
  beyond-page exits leave only the compact text object, while the high-x path
  updates `0x783188` and later CR flush produces a 28-pixel segment-list span.
  Status: parser printable to page-record/render fixture with synthetic
  metric values for both source forms.

The remaining unresolved middle edge is therefore not the tested `0x1719c`
type-0, type-1, or type-2 metric paths into either `0xd4ac` or `0xd8fc`: all
three payload forms now have host-fetched evidence through visible span rows,
and the consumer-side disabled, lower-bound, page-extent, and high-x branches
are fixture-backed for both selected source forms. Three parser-produced
metric-value variants now prove copied descriptor values can flip the `d4ac`
page-extent gate, exercise rounded-metric clamping into `+0x2c/+0x2d`, move
`d8fc` visible rows, and suppress both span consumers through descriptor-owned
lower-bound fields while preserving compact glyph output. The open
producer-side work is broader descriptor coverage: more metric-byte
cross-products and validation/error forms driven from parser bytes to page
rows.

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
- `0xc428` may fail with `0x11` when all 16 page-root font slots are live and
  none match; that path must not silently install a new context.

## Remaining Edges

- `0x13eb8` selection, map rebuild, page-root install, printable source
  capture, and low-water span effects are fixture-backed for the primary and
  secondary cases above. The primary built-in selection request
  `ESC (s0p10h12v0s0b3T!!` is now driven from parser bytes to visible rows,
  with the selected `0xc008004c` context injected at the printable phase. Not
  every PCL font request combination has been driven from parser bytes to
  visible rows. The secondary built-in selection request
  `ESC )s0p16h8v0s0b0T SO !!` is also driven to visible rows through SO
  handler `0xc6b8` and context `0xc00ae122`. The secondary current-font RAM
  handoff from seeded `0x782ef6` through `0xc428` / `0xc4fc` into existing
  page-root slot `1` is now fixture-backed by
  `live secondary current-font RAM install feeds SO page-record rows`.
  The primary current-font RAM handoff from seeded `0x782ee6` through
  `0xc428` / `0xc4fc` into existing page-root slot `0` is now fixture-backed
  by `live primary current-font RAM install feeds SI page-record rows`.
  Remaining handoff work is a continuous parser-to-page CPU-state trace that
  carries the parser-produced current-font records directly into later SI/SO
  and printable queueing.
- The exact metric-byte provenance for all downloaded/inline forms remains
  incomplete at the parser-produced page boundary. Existing host-stream
  downloaded-font fixtures prove install, visible glyph rendering, and
  `0x1719c` type-0, type-1, and type-2 payloads feeding both `0xd4ac` and
  `0xd8fc` span rows; the shared span-consumer branch family is also
  fixture-backed. Seven bounded `0x16fae` validation no-install forms now
  preserve following printable output. The remaining gap is broader descriptor
  metric-byte values and validation/error forms beyond those bounded predicate
  branches.
