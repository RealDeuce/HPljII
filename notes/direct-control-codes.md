# Direct Control Codes And Cursor State

This note is the semantic contract for the LaserJet II direct control-code
cluster. It composes CR, LF, FF, HT, BS, `ESC &k#G`, HMI, cursor stack,
margin, cursor-position, dot-position, and adjacent vertical-layout helpers
where they affect later text, page-record, or render output.

Status: composed for the documented byte-stream-to-page-record paths. The
low-level ledger remains in `notes/reverse-engineering-ledger.md`,
`notes/pcl-parser-firmware.md`, and generated reports. This file is the
renderer-facing documentation checkpoint.

## Evidence

- `generated/analysis/ic30_ic13_direct_control_code_flow.md`
- `generated/analysis/ic30_ic13_renderer_fixture_harness.md`
- `generated/analysis/ic30_ic13_printable_text_path.md`
- `generated/analysis/ic30_ic13_text_cursor_span_flow.md`
- `generated/analysis/ic30_ic13_page_record_bridge.md`
- `generated/disasm/ic30_ic13_control_code_handlers_00f02c.lst`
- `generated/disasm/ic30_ic13_hmi_vmi_handlers_00ca8c.lst`
- `generated/disasm/ic30_ic13_wrap_mode_handler_00edb0.lst`
- `generated/disasm/ic30_ic13_dot_position_handlers_00f48c.lst`
- `notes/pcl-command-map.md`
- `notes/pcl-parser-firmware.md`
- `notes/page-raster-imaging.md`
- `notes/semantic-state-model.md`

Primary fixtures:

- `ESC &k#G line termination mode bits`
- `CR resets horizontal cursor and flushes pending text span`
- `CR line-termination mode 1 also advances vertical cursor`
- `LF line-termination mode 2 resets horizontal cursor`
- `FF line-termination mode 2 resets horizontal cursor and marks page eject`
- `HT advances to next eight-column stop`
- `HT clamps to page width when already beyond right limit`
- `BS subtracts HMI and sets pending previous-width latch`
- `BS clamps at left margin when crossing it`
- `BS alternate metrics subtracts previous width word`
- `control stream ESC &k1G then CR applies CR+LF`
- `control stream ESC &k2G then LF applies CR+LF`
- `control stream ESC &k2G then FF applies CR+page-eject`
- `control stream ESC &k3G applies CR/LF/FF combined line termination`
- `control stream HT then BS updates tab and previous-width state`
- `plain printable parser trace feeds page-record queue`
- `HMI parser trace feeds page-record queue`
- `mixed printable/control stream applies CR+LF before second glyph`
- `mixed printable/control stream renders post-CR glyph rows`
- `mixed printable/control parser trace feeds page-record queue`
- `mixed printable/control page-record stream queues through 0x1387c`
- `mixed printable/control page-record bridge renders post-CR glyph rows`
- `LF parser trace feeds page-record queue`
- `HT/BS parser trace feeds page-record queue`
- `ESC 9 clear margins feeds CR and page-record output`
- `ESC = half-line feed reaches shifted page-record output`
- `0xf75e ESC &f0S pushes cursor with vertical offset`
- `0xf75e ESC &f1S pops cursor and clears pending flags`
- `cursor stack stream ESC &f0S / ESC &f1S selects 0xf75e push/pop`
- `0xf75e cursor stack bounds and pop clamps to current extents`
- `cursor stack parser trace feeds page-record queue`
- `0xf39e ESC &a#C converts columns through HMI and relative flag`
- `0xf416 ESC &a#H converts decipoints and clamps horizontal cursor`
- `0xf560 ESC &a#R uses VMI with absolute top offset and relative cursor base`
- `cursor position stream ESC &a3.5c+1R selects 0xf39e then 0xf560`
- `0xf60a ESC &a#V converts decipoints and clamps vertical cursor`
- `0xf48c/0xf692 ESC *p#X/#Y use whole-dot packed cursor commits`
- `cursor position parser trace feeds page-record queue`
- `horizontal decipoint parser trace feeds page-record queue`
- `vertical cursor position parser trace feeds page-record queue`
- `vertical decipoint parser trace feeds page-record queue`
- `dot position parser trace feeds page-record queue`
- `chained cursor position parser trace feeds page-record queue`
- `0xeb58 ESC &a#L sets left margin and moves cursor only when needed`
- `0xec0c ESC &a#M applies plus-one column, clamps, and moves cursor at right edge`
- `margin stream ESC &a6l9M selects 0xeb58 then 0xec0c`
- `margin command parser trace feeds page-record queue`
- `right margin command parser trace feeds page-record queue`
- `chained margin command parser trace feeds page-record queue`
- `live CR span flush materializes 0x12714 page object`
- `left-margin parser span flush materializes 0x12714 page object`
- `vertical-cursor parser span flush materializes 0x12714 page object`
- `0xc992 ESC &l#D accepts ROM LPI set and refreshes pending vertical cursor`
- `0xcb00 ESC &l#C converts 1/48-inch VMI and keeps zero unmodified`
- `0xea9e ESC &l#F sets text length bottom or restores default`
- `0xece2 ESC &l#E sets top margin, default text length, and pending cursor`
- `0xee64 ESC &l#L toggles perforation skip for selectors 0 and 1 only`
- `0xcb00/0xc992/0xece2/0xea9e chained ESC &l stream selects vertical layout
  handlers`
- `vertical layout parser trace feeds page-record queue`
- `transparent data parser trace feeds page-record queue`
- `ESC &d underline selector materializes span output`
- `perforation skip parser trace feeds page-record queue`
- `0xedb0 ESC &s#C toggles end-of-line wrap for selectors 0 and 1 only`
- `0xd28a and 0xd6bc prechecks share continue reject and wrap decisions`

## Field Groups

Canonical placement state:

- `0x782c8a`: horizontal cursor consumed by printable text, HT, BS,
  `ESC &a#C/#H`, `ESC *p#X`, margin reset, and raster-start positioning.
- `0x782c8e`: vertical cursor consumed by LF, FF, `ESC &a#R/#V`,
  `ESC *p#Y`, printable text bucketing, and raster-start positioning.
- `0x782dd6`: left/default margin copied into `0x782c8a` by CR helper
  `0xf06e`; written by `ESC &a#L` handler `0xeb58` and reset by `ESC 9`
  handler `0xe9ba`.
- `0x782dda`: right margin or horizontal limit written by `ESC &a#M`
  handler `0xec0c`, reset by `0xe9ba`, and consumed by HT plus horizontal
  commit helper `0xf4ca`.
- `0x78315c`: HMI/default horizontal motion written by `ESC &k#H` handler
  `0xca8c`, then consumed by HT, BS, margin commands, column positioning, and
  printable advance.
- `0x783160`: VMI/line advance written by `ESC &l#C/#D` handlers
  `0xcb00` and `0xc992`, then consumed by LF, FF, vertical positioning, VFC,
  page length, and top-margin paths.

Canonical control modes:

- `0x78318f`: line-termination mode written by `ESC &k#G` handler `0xedf8`.
  CR `0xf02c` tests bit `7`, LF `0xf08c` tests bit `6`, and FF `0xf0f0`
  tests bit `5`.
- `0x783190`: end-of-line wrap flag written by `ESC &s#C` handler `0xedb0`.
  Selector `0` stores `1`, selector `1` clears it, and other selectors leave
  the byte unchanged. Printable prechecks `0xd28a` and `0xd6bc` consume the
  byte before deciding whether horizontal overflow rejects the glyph or
  recovers through `0xf054`.
- `0x783191`: perforation-skip byte written by `ESC &l#L` handler `0xee64`
  and consumed by `0xf36c`.

Canonical cursor stack:

- `0x782c96..0x782d36`: `ESC &f#S` cursor-stack storage.
- `0x782d36`: next-free stack pointer and upper bound.
- Selector `0` stores x plus `y + 0x782dbe`; selector `1` pops and restores
  x/y after active-extent clamps.

Canonical page and vertical bounds:

- `0x782db8`: horizontal page extent used by HT and `0xf4ca`.
- `0x782dba`: page length/vertical extent written by `0xf9e8`.
- `0x782dc2`: text-bottom/perforation limit consumed by `0xf36c`.
- `0x782dc6` and `0x782dca`: vertical upper and lower bounds used by
  `0xf6e2`.
- `0x782dce`: top offset used by FF helper `0xf124`, vertical positioning,
  VFC, and top-margin handling.

Derived/cache state:

- Compact text coordinates are derived from cursor state just before
  `0x12f2e` / `0x1387c` page-record queueing. Examples pinned by fixtures
  include `0x3b00` after CR+LF, `0x0a01` after HT/BS, `0x0600` after `ESC 9`
  plus CR, and `0x0001` after cursor-stack restore.
- `0x783a20`, `0x783a22`, and `0x783a28` are active-render band caches
  derived after publication by `0x1ed84`; they are not canonical cursor
  inputs.

Parser scratch:

- `0x78299e`: six-byte parsed command-record cursor rewound by handlers such
  as `0xca8c`, `0xeb58`, `0xec0c`, `0xf39e`, `0xf416`, `0xf560`, `0xf60a`,
  and `0xf75e`.
- Delayed payload state from `0x121cc` / `0x12218` is not part of CR/LF/FF
  handling, but direct-control streams share the same parser loop and host
  byte source before dispatch.

Firmware bookkeeping:

- `0x782a57`: right-limit latch set by right-margin and horizontal-position
  paths.
- `0x782a58`: previous-width or pending-width latch cleared by cursor moves
  and set by BS.
- `0x782a5a`: latched previous width used by BS when alternate metrics mode
  byte `0x78318e` is set.
- `0x782a6d`: pending text/cursor latch cleared by cursor-changing paths and
  set to `0xff` by FF after page eject.
- `0x783184`: pending text span flush enable tested by `0xf34a`.
- `0x783185`: underline/text-attribute selector written by `ESC &d` handler
  `0x12622` and consumed by span helpers `0xd4ac` / `0xd8fc`.

Unknown:

- Manual-facing names for latches `0x782a57`, `0x782a58`, `0x782a5a`,
  `0x782a6d`, `0x78318e`, and `0x783185` remain provisional.
- Broader source-object variants should be added only when they expose new
  `0xd04a` field values, a new `0x12f2e` queueing shape, or different visible
  rows. The existing direct-control byte streams already define the covered
  ROM contract from parsed command through page-record queueing and render
  entry.

## Writers

- `0xedf8` writes line-termination byte `0x78318f`. The bit map is
  `0 -> 0x00`, `1 -> 0x80`, `2 -> 0x60`, and `3 -> 0xe0`.
- `0xedb0` writes end-of-line wrap byte `0x783190` for `ESC &s#C`: absolute
  selector `0` enables wrap, selector `1` disables it, and all other selectors
  keep the previous mode.
- `0xf02c` handles CR by resetting x through `0xf06e`, flushing pending span
  state through `0xf34a`, and optionally calling LF helper `0xf0b2`.
- `0xf08c` handles LF by optionally applying CR-style x reset, then advancing
  y through VMI-scaled movement.
- `0xf0f0` handles FF by optionally applying CR-style reset, finalizing the
  page root, and marking page-eject pending state.
- `0xf1cc` handles HT by advancing to the next eight-column stop and clamping
  to page width.
- `0xf2a8` handles BS by subtracting HMI or alternate previous-width state,
  then clamping at the left margin.
- `0xca8c` writes HMI `0x78315c` for accepted `ESC &k#H` values.
- `0xe9ba` implements `ESC 9` by clearing left margin, copying page width to
  the right margin, and clearing the right-margin fractional companion.
- `0xf176` implements `ESC =` by ensuring a page root, flushing pending span
  state, and advancing y by half the current VMI.
- `0xeb58` and `0xec0c` write left/right margins and can move `0x782c8a`.
- `0xf39e`, `0xf416`, and `0xf48c` write horizontal cursor state through
  helper `0xf4ca`.
- `0xf560`, `0xf60a`, and `0xf692` write vertical cursor state through helper
  `0xf6e2`.
- `0xcb00`, `0xc992`, `0xece2`, `0xea9e`, `0xee64`, and `0xf9e8` write VMI,
  vertical layout, perforation skip, text-bottom, and page-length state.
- `0xf75e` pushes or pops cursor-stack entries.
- `0x12622` tokenizes `ESC &d` underline/text-attribute commands and writes
  `0x783185` for the covered absolute `3D` selector path.

## Readers And Consumers

- `0xd04a` consumes current cursor, HMI, font context, and pending-width state
  to create the next text source object.
- `0xd28a` and `0xd6bc` consume `0x783190` inside the printable text
  prechecks. When horizontal overflow is detected, a clear flag returns
  precheck result `1` and suppresses queueing; a set flag calls `0xf054`,
  retries from the recovered cursor, and can return `0` so the glyph continues
  into the queue path.
- `0x12f2e`, `0x1387c`, and shared page-record storage consume compact
  coordinates derived from direct-control state.
- `0x12714` / `0x126e2` consume pending span state when CR, margin, vertical
  cursor movement, or underline terminal commands force a span publication.
- `0xf36c` consumes `0x782c8e`, `0x782dc2`, and `0x783191` to decide whether
  vertical overflow triggers page eject.
- `0x1edc6` bridges queued page-record text/span objects into render-record
  shape, and `0x1ed84` / `0x1ef6a` render the active band rows.
- Raster start consumes `0x782c8a` or `0x782c8e` depending on orientation, as
  documented in `notes/raster-graphics.md`.

## Output Effect

`ESC &k1G!\r!` routes `0xedf8`, `0xd04a`, `0xf02c`, and `0xd04a`. The
stored mode byte is `0x80`, so CR resets x and applies LF/VMI before the
second printable byte. Fixture `mixed printable/control parser trace feeds
page-record queue` pins the second compact coord as `0x3b00`; fixture
`mixed printable/control page-record bridge renders post-CR glyph rows` pins
the bridged rows.

`ESC &k2G!\n!` routes LF through `0xf08c` after storing mode `0x60`. Fixture
`LF parser trace feeds page-record queue` proves LF applies CR+LF before the
second glyph, which also queues at compact coord `0x3b00`.

`ESC &k2G!\f` routes FF through `0xf0f0` after storing mode `0x60`. Fixture
`control stream ESC &k2G then FF applies CR+page-eject` proves the CR-style
horizontal reset, page-root finalization, span flush, and pending page-eject
state.

`ESC &k3G` followed by CR, LF, and FF proves all three line-termination bits
are consumed in sequence. Fixture `control stream ESC &k3G applies CR/LF/FF
combined line termination` pins that behavior.

`ESC &k0G HT BS !` routes `0xedf8`, `0xf1cc`, `0xf2a8`, and `0xd04a`. HT
advances x to `21`, BS backs it up to `20`, and the printable glyph queues at
compact coord `0x0a01` / pixel x `26`.

`ESC &k6H!!` routes `0xca8c` before two printable bytes. The accepted HMI
value stores packed advance `15` in `0x78315c`, moving the second glyph to
compact coord `0x0501`.

`ESC &s#C` has no immediate page object, but it changes the acceptance boundary
for later printable text. Disassembly `0xedb0..0xedf6` rewinds the parsed
record, normalizes the absolute selector, and writes only selectors `0` and
`1`. Fixture `0xedb0 ESC &s#C toggles end-of-line wrap for selectors 0 and 1
only` pins the command byte. Fixture `0xd28a and 0xd6bc prechecks share
continue reject and wrap decisions` then pins the downstream effect: horizontal
overflow with `0x783190` clear returns precheck result `1`, while the same
overflow with `0x783190` set calls `0xf054`, retries from recovered x `0`, and
returns `0` when the retried placement fits. Vertical extent failure still
returns `1`.

The plain and HMI parser fixtures pin the baseline consumer path. Fixture
`plain printable parser trace feeds page-record queue` proves a printable
byte reaches `0xd04a`, queues a compact text object through `0x1387c`, and
survives bridge/render entry. Fixture `HMI parser trace feeds page-record
queue` proves the `0xca8c` HMI writer changes the following compact
coordinates without changing the downstream page-record contract.

`ESC 9 CR !` has visible effect only through later text. Fixture `ESC 9 clear
margins feeds CR and page-record output` proves `0xe9ba` clears left margin
to `0`, copies page width `120` into the right margin, lets CR move x from
packed `50` to `0`, and queues the printable byte at compact coord `0x0600`.

`ESC = !` advances vertically by half of current VMI. Fixture `ESC = half-line
feed reaches shifted page-record output` proves `0xf176` advances y from
packed `21` to `22.6`, then the following printable queues at compact coord
`0x1001`.

`ESC &f0S ESC &a2C ESC &f1S!` proves cursor-stack state reaches visible
output. Fixture `cursor stack parser trace feeds page-record queue` routes
`0xf75e`, `0xf39e`, `0xf75e`, and `0xd04a`; the pop restores the original
cursor before the glyph queues at compact coord `0x0001`.

The direct helper fixtures bound the cursor-stack internals before visible
output: `0xf75e ESC &f0S pushes cursor with vertical offset`,
`0xf75e ESC &f1S pops cursor and clears pending flags`, and
`0xf75e cursor stack bounds and pop clamps to current extents` pin the stored
entry format, pointer bounds, vertical-offset subtraction, and clamp rules.

The cursor-position helper fixtures pin the conversion layer that feeds those
visible page-record streams. `0xf39e ESC &a#C converts columns through HMI and
relative flag` and `0xf416 ESC &a#H converts decipoints and clamps horizontal
cursor` cover the horizontal `ESC &a` family. `0xf560 ESC &a#R uses VMI with
absolute top offset and relative cursor base` and `0xf60a ESC &a#V converts
decipoints and clamps vertical cursor` cover the vertical family. Fixture
`cursor position stream ESC &a3.5c+1R selects 0xf39e then 0xf560` pins
lowercase chaining across horizontal and vertical handlers. Fixture
`0xf48c/0xf692 ESC *p#X/#Y use whole-dot packed cursor commits` covers the
dot-position siblings. The parser-to-page-record fixtures named above then
carry each converted cursor state through the following printable byte.

Margin helper fixtures similarly separate helper semantics from visible
output. `0xeb58 ESC &a#L sets left margin and moves cursor only when needed`
and `0xec0c ESC &a#M applies plus-one column, clamps, and moves cursor at
right edge` pin the left/right margin writers. Fixture `margin stream
ESC &a6l9M selects 0xeb58 then 0xec0c` pins lowercase chaining across the
margin family; the margin parser traces then prove following printable bytes
queue through the same compact text path.

`ESC &a6L!` and `ESC &a1R!` also have pending-span siblings. Fixtures
`left-margin parser span flush materializes 0x12714 page object` and
`vertical-cursor parser span flush materializes 0x12714 page object` prove
those cursor-changing handlers can publish selector-`0x4000` span objects
through `0x12714` before the following printable glyph is queued.

### Span Flush Producers

Several direct-control handlers are not just cursor writers. Before they
overwrite cursor/span bounds, they call `0xf34a`, which can materialize the
pending text span through `0x12714` and `0x126e2`. The shared object produced
by the covered portrait cases is:

```text
00 00 00 00 40 00 00 01 32 00 03 00 00 10
```

That is a segment-list object in page-root bucket `0` with selector `0x4000`,
one entry, packed key `0x3200`, y `3`, and extent `16`.

Producer cases:

- CR path: fixture `live CR span flush materializes 0x12714 page object`
  drives `ESC &k1G!\r` through `0xedf8`, `0xd04a`, and `0xf02c`. The printable
  first queues compact object `00 00 00 00 00 00 00 01 20 00 01`, then CR
  materializes pending span state `x=2..18, y=3`, inserts the selector-`0x4000`
  segment-list object ahead of the compact object in bucket `0`, re-arms
  `0x783186` and `0x783188` to x `5`, and renders the span rows beside the
  text glyph.
- Left-margin path: fixture
  `left-margin parser span flush materializes 0x12714 page object` drives
  host-fetched `ESC &a6L!` through parser handlers `0xeb58` and `0xd04a`.
  Handler `0xeb58` moves `0x782c8a` from packed `10` to packed `108`, flushes
  the same pending span object, re-arms span bounds to x `108`, and the
  following printable queues compact coord `0x0207`.
- Vertical-cursor path: fixture
  `vertical-cursor parser span flush materializes 0x12714 page object` drives
  host-fetched `ESC &a1R!` through parser handlers `0xf560` and `0xd04a`.
  Handler `0xf560` flushes the span before moving y to packed `95.1`, re-arms
  span bounds to x `10`, and the following printable queues compact coord
  `0xa001` in bucket `4`, leaving bucket `0` for the already materialized span
  rows.
- Underline/text-attribute path: fixture
  `ESC &d underline selector materializes span output` drives
  `ESC &d3D! ESC &d@` through `0x12622`, `0xd04a`, and `0x12622`. Selector
  `3D` writes `0x783185 = 1`, printable output lets the flagged text source
  update span high-y through alternate offset word `+0x1a`, and final `&d@`
  flushes selector-`0x4000` span object
  `00 00 00 00 40 00 00 01 3a 00 03 00 00 12`.

State classification for this cluster:

- canonical: pending span fields `0x783184`, `0x783186`, `0x783188`, and
  `0x78318a`; cursor fields `0x782c8a` / `0x782c8e`; segment-list object fields
  class byte `0x40`, count `+0x06`, key `+0x08`, y `+0x0a`, and extent
  `+0x0c`;
- derived/cache: packed compact coordinates such as `0x0207` and `0xa001`,
  plus the `0x12714` bucket/key result `0x3200`;
- parser scratch: normal six-byte records for `ESC &k#G`, `ESC &a#L`,
  `ESC &a#R`, and `ESC &d#D`; no delayed-payload state participates;
- firmware bookkeeping: re-armed span bounds after `0x126e2`, publication
  counters in the fixture harness, and page-root allocation state from
  `0x10084`;
- unknown: no ROM-local middle edge remains for these producers. Broader work
  should add only cursor/font/span variants that change the object bytes,
  bucket choice, bridge state, or rendered rows.

`ESC &d3D! ESC &d@` proves underline/text-attribute state crosses into the
same span machinery. Fixture `ESC &d underline selector materializes span
output` writes `0x783185 = 1`, lets the printable update the flagged text
span through alternate offset fields, and flushes a selector-`0x4000` span
object beside the compact glyph.

Vertical-layout helper fixtures pin the shared VMI/text-boundary state that
feeds both direct controls and later printable placement. `0xc992 ESC &l#D
accepts ROM LPI set and refreshes pending vertical cursor` and
`0xcb00 ESC &l#C converts 1/48-inch VMI and keeps zero unmodified` pin the
VMI writers. `0xea9e ESC &l#F sets text length bottom or restores default`,
`0xece2 ESC &l#E sets top margin, default text length, and pending cursor`,
and `0xee64 ESC &l#L toggles perforation skip for selectors 0 and 1 only`
pin the vertical layout writers. Fixture
`0xcb00/0xc992/0xece2/0xea9e chained ESC &l stream selects vertical layout
handlers` pins same-family chaining; fixture
`vertical layout parser trace feeds page-record queue` carries the resulting
state into following printable output.

## Reproduction Contract

A byte-stream renderer must preserve:

- normal-mode direct-control dispatch for CR, LF, FF, HT, and BS;
- the `ESC &k#G` mode byte and its per-control-bit consumption;
- the `ESC &s#C` wrap byte and its prequeue effect on `0xd28a` / `0xd6bc`
  horizontal overflow decisions;
- CR reset through left margin before optional LF movement;
- LF and FF optional CR-style reset behavior;
- HT eight-column stop arithmetic using left margin and HMI;
- BS HMI subtraction, left-margin clamp, and alternate previous-width mode;
- page-root creation/finalization and pending-state effects for FF;
- span flushes through `0xf34a` / `0x12714` before cursor-changing commands
  overwrite pending span bounds;
- cursor-stack push/pop storage including vertical offset `0x782dbe`;
- following printable object coordinates after every cursor or margin command;
- page-record bridging and render-entry rows after those objects are queued.

## Confidence

High for line-termination bits, CR/LF/FF/HT/BS cursor effects, HMI conversion,
page-record compact coordinates, and representative ROM-derived row
construction because the claims are backed by disassembly plus byte-stream
fixtures that start at modeled host byte fetch and reach `0x1387c`,
`0x1edc6`, `0x1ed84`, and `0x1ef6a`. The fixtures drive ROM-local branches;
they are not external rendered-output comparisons.

High for `ESC 9`, `ESC =`, cursor-stack, underline/span, and perforation-skip
representative output effects because each has a named parser/page-record
fixture and concrete handler evidence.

High for `ESC &s#C` selector handling and printable precheck consumption,
because the `0xedb0` writer and paired `0xd28a` / `0xd6bc` consumers are pinned
by fixtures and by disassembly reads of `0x783190`.

Medium only for manual-facing latch names and untested source-object variants
inside `0xd04a -> 0x12f2e`. The documented handlers and fixtures cover the
renderer contract for the byte-stream cases listed above.

## Remaining Edges

- No ROM parser-to-page-record middle edge remains for the documented
  CR/LF/FF/HT/BS plus `ESC &k#G` control family.
- Remaining work is byte-stream cases that create new `0xd04a` source-object
  fields, `0x12f2e` bucket shapes, span-flush state, or render-dispatch
  effects, not re-proving already documented direct-control fields from
  another execution source.
