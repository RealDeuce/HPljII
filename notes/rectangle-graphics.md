# Rectangle And Rule Graphics Firmware

This note documents the PCL rectangle/rule graphics path from `ESC *c`
parser command records to rule-list objects and rendered solid/pattern pixels.
It covers this command family:

- `ESC *c#A`: rectangle width in dots
- `ESC *c#B`: rectangle height in dots
- `ESC *c#H`: rectangle width in decipoints
- `ESC *c#V`: rectangle height in decipoints
- `ESC *c#G`: area-fill id
- `ESC *c#P`: fill rectangle

Evidence:

- `generated/analysis/ic30_ic13_pcl_command_map.md`
- `generated/disasm/ic30_ic13_parser_setup_handlers_011ea4.lst`
- `generated/disasm/ic30_ic13_rectangle_graphics_010898.lst`
- `generated/disasm/ic30_ic13_display_list_helpers_013386.lst`
- `generated/analysis/ic30_ic13_rectangle_graphics_flow.md`
- `tools/render_fixture_harness.py`, fixtures:
  - `0x10e68/0x10e22/0x10a40/0x10ae0 rectangle size commands update
    packed dimensions`
  - `0x10898 ESC *c#P maps fill selectors and queues rule object`
  - `rectangle command stream queues chained ESC *c rule object`
  - `0x11774 ROM dispatch table routes chained ESC *c rule stream`
  - `host-fetched rectangle rule stream preserves 0x1edc6 bridge contract`
  - `host-fetched rectangle rule feeds 0x1ed84 and 0x1ef6a`
  - `0x13386/0x133aa-modeled rectangle/rule list object and bridge
    normalization`
  - `0x133aa address-aware rule-list insertion uses 0x1381c storage`
  - `0x133aa no-room return preserves rule-list head`
  - `0x1edc6 page-record bridge normalizes rule and fixed lists`
  - `0x137a2/0x136d2-modeled fixed-rule list object and bridge
    normalization`
  - `0x1f446/0x1f596 renders solid black rectangle rule pixels`
  - `0x1f596 carries solid rule remainder across render bands`
  - `0x1f4e0 renders gray and HP pattern selector matrix`
  - `0x1f4e0 carries patterned rule remainder across render bands`
  - `0x1f446 page-band walk assembles patterned rule rows`
  - `0x1f446/0x1f4e0 renders gray selector pattern pixels`
  - `0x1f4e0 renders sub-byte shifted HP pattern rule pixels`
  - `0x10b80 rectangle fill clips negative left edge before queueing`
  - `0x10b80 rectangle fill clips right/top/bottom edges and ignores
    off-page fills`
  - `0x10d22 rectangle/rule no-room retry finalizes root then retries span`
  - `rectangle parser trace feeds no-room retry path`
  - `bridged compact text and rule objects compose into one page band`
  - `bridged text, rule, and raster layers compose into one page band`
  - `0x1ef6a render entry composes bucket, rule, and fixed-width lists in call
    order`
  - `0x1ef6a page-band walk merges text raster and crossing rule`
  - `host-fetched text plus rectangle page record feeds 0x1ed84 and 0x1ef6a`
  - `addressed text plus rectangle stream matches page-record output`
  - `host-fetched alternate rectangle selectors feed full page records`
  - `host-fetched rectangle selector matrix feeds full page records`
  - `host-fetched text rectangle and raster page record feeds 0x1ed84 and
    0x1ef6a`
  - `addressed text rectangle raster stream matches page-record output`
  - `addressed text rectangle raster publication renders rows`
  - `published text rectangle and raster page record feeds 0x1ed84 and
    0x1ef6a`
  - `host-fetched text rectangle raster FF publishes rendered page record`
  - `addressed text rectangle raster FF publishes rendered page record`
  - `addressed text/rule/raster field groups reach publication and render
    entry`
  - `host-fetched text rectangle multi-row raster FF publishes rendered page
    record`
  - `addressed text/rule/multi-row raster publication preserves bucket
    chain`

## Owner Summary

Concept: this note owns the `ESC *c` rectangle/rule graphics family from
parsed command records to rule-list objects and rendered solid or patterned
pixels. It covers dot and decipoint size state, area-fill state, fill selector
mapping, page/cursor clipping, rule object allocation, no-room retry
publication, page-record bridge normalization, render-list dispatch, and band
continuation state.

Primary route:

- Parser setup handlers `0x11eb6`, `0x11ec8`, and `0x11eda` keep the
  `ESC *c` command family active across chained lowercase finals.
- Size/fill state route:
  `0x10e68/0x10e22/0x10a40/0x10ae0/0x10dce -> 0x78316a/0x783166/0x78316e`.
- Fill route:
  `0x10898 -> 0x10b80 -> 0x13386 -> 0x133aa -> page-root rule list +0x24`.
- No-room route:
  `0x10d22 -> root+0x15.0 -> 0xff1e -> 0x10084 -> retry clipped source`.
- Render route:
  `0xff1e -> 0x1ed84 -> 0x1edc6 -> 0x1ef6a -> 0x1f446
  -> 0x1f596/0x1f4e0`.

Field groups:

- Canonical rectangle state: width `0x78316a`, height `0x783166`, and
  area-fill id `0x78316e`.
- Canonical page/cursor inputs: horizontal cursor `0x782c8a`, vertical cursor
  `0x782c8e`, orientation `0x782da3`, page extents `0x782db8` / `0x782db6`,
  and current page root `0x78297a`.
- Canonical rule source: staging record `0x782a88`, including x, y, width,
  height, and fill selector.
- Canonical page output: page-root rule-list head `root+0x24`, 14-byte rule
  objects from `0x133aa`, bridge-normalized render list `+0x1c`, selector
  byte `+0x05`, packed key `+0x06`, width `+0x08`, height `+0x0a`, and
  continuation word `+0x0c`.
- Derived/cache: rule bucket index `0x782a7c`, low bucket byte `0x782a7d`,
  packed rule key `0x782a7e`, and horizontal phase `0x782dc0`.
- Parser scratch: parser record cursor `0x78299e` and current six-byte
  command record consumed by each handler.
- Firmware bookkeeping: stream allocator state `0x782a70`, `0x782a72`, and
  `0x782a76`, plus page-root retry flag `root+0x15.0`.
- Unknown: new streams are unknown only if they change clipped source records,
  `0x1381c` allocation state, rule object bytes, bridge-normalized lists,
  no-room publication state, render dispatch, or ROM-derived row construction.

Writers and readers:

- `0x10e68`, `0x10e22`, `0x10a40`, and `0x10ae0` write rectangle dimensions.
- `0x10dce` writes area-fill id; `0x10898` maps `#P` and fill id to a rule
  selector or exits without output.
- `0x10b80` consumes cursor/orientation/page extents, clips the rectangle, and
  writes source record `0x782a88`.
- `0x13386` / `0x133aa` consume the source record and allocator state to link
  a rule object.
- `0x1edc6` consumes page-root rule list `+0x24` and normalizes it into the
  active render record.
- `0x1f446` consumes render-list objects and dispatches solid selector `7` to
  `0x1f596` or gray/pattern selectors to `0x1f4e0`.

Output effect:

- Size and area-fill commands are state-only until `ESC *c#P` consumes them.
- A valid, nonempty on-page `ESC *c#P` queues a rule-list object, not pixels.
- Pixels appear after publication/render scheduling when `0x1f446` walks the
  normalized rule list for the active band.
- Rules crossing a band mutate continuation word `+0x0c` so later band walks
  continue from the same ROM-defined rule object.

Evidence and boundaries:

- Disassembly evidence is in
  `generated/disasm/ic30_ic13_rectangle_graphics_010898.lst` and
  `generated/disasm/ic30_ic13_display_list_helpers_013386.lst`.
- Generated flow evidence is in
  `generated/analysis/ic30_ic13_rectangle_graphics_flow.md`.
- Fixture evidence is named in the Evidence list above; those streams pin
  parser routing, clipping, rule object creation, bridge normalization,
  no-room retry, solid/pattern render helpers, and composition with text and
  raster objects.
- No unresolved ROM-local middle edge remains for documented `ESC *c`
  size/fill, clipped queue, bridge, solid/pattern render, and no-room retry
  paths. Remaining work must change one of the exact unknown boundaries named
  above.

## Parser Boundary

The primary chained stream fixture is:

```text
1b 2a 63 31 32 61 35 62 30 50
```

That is:

```text
ESC *c12a5b0P
```

The ROM parser trace walks modes:

```text
0 -> 1 -> 3 -> 16 -> 16 -> 16 -> 0
```

It selects setup handlers `0x11eb6`, `0x11ec8`, `0x11eda`, then rectangle
handlers:

| Sequence | Handler | Effect |
| --- | ---: | --- |
| `ESC *c12a` | `0x10e68` | stores dot width `12` |
| `5b` | `0x10e22` | stores dot height `5` |
| `0P` | `0x10898` | selects solid fill and queues rule object |

The host-fetched fixture starts from the modeled `0xa904` ring source and
drains the same bytes before reaching these handlers and the same
page-record/render bridge.

## Field Groups

Canonical rectangle command fields:

- `0x78316a`: current rectangle width. Written by `ESC *c#A` and
  `ESC *c#H`; consumed by `ESC *c#P`.
- `0x783166`: current rectangle height. Written by `ESC *c#B` and
  `ESC *c#V`; consumed by `ESC *c#P`.
- `0x78316e`: current area-fill id. Written by `ESC *c#G`; consumed by
  `ESC *c#P` modes `2` and `3`.

Canonical page/cursor inputs:

- `0x782c8a`: current horizontal cursor, used as rectangle start x.
- `0x782c8e`: current vertical cursor, used as rectangle start y.
- `0x782da3`: orientation flag, used by the landscape coordinate path.
- `0x782db8`: horizontal page extent for reject and clipping checks.
- `0x782db6`: vertical page extent for reject and clipping checks.
- `0x78297a`: current page root pointer.

Canonical rule source record:

- `0x782a88 + 0x00`: queued rule x.
- `0x782a88 + 0x02`: queued rule y.
- `0x782a88 + 0x04`: queued rule width.
- `0x782a88 + 0x06`: queued rule height.
- `0x782a88 + 0x08`: fill selector.

Derived/cache fields:

- `0x782a7c`: rule bucket index derived from y by `0x134d6`.
- `0x782a7d`: low bucket byte copied into object byte `+4`.
- `0x782a7e`: packed rule key derived by `0x134d6`.
- `0x782dc0`: horizontal page/raster phase added to source x before rule
  key packing.

Firmware bookkeeping:

- page root `+0x24`: rectangle/rule linked-list head.
- `0x782a70`, `0x782a72`, `0x782a76`: stream allocator state consumed by
  `0x1381c` while `0x133aa` allocates 14-byte rule objects.
- page root `+0x15.0`: retry/publication flag set by the `0x10d22` no-room
  path before `0xff1e`.

Parser scratch:

- `0x78299e`: command-record cursor rewound by each rectangle handler before
  it reads the six-byte parsed command record.

Unknown:

- New rectangle byte streams are unknown only when they change a
  pixel-affecting boundary not already covered by the fixtures below: clipped
  source record, `0x1381c` allocation/rollover state, rule object bytes,
  bridge-normalized rule list, no-room retry publication state, render
  dispatch, or ROM-derived row construction.

## Command-To-Pixel Owner Summary

The `ESC *c` family is a delayed drawing model. Size and fill commands write
persistent rectangle state; only `ESC *c#P` consumes that state to build a
rule-list object. Pixels appear later when publication and render scheduling
copy that object into the active render record.

Writers:

- Parser setup handlers `0x11eb6`, `0x11ec8`, and `0x11eda` keep the
  `ESC *c` family active while chained lowercase finals are parsed.
- Dot-size handlers `0x10e68` and `0x10e22` write width `0x78316a` and height
  `0x783166`; decipoint handlers `0x10a40` and `0x10ae0` write the same fields
  after ROM unit conversion and rounding.
- Area-fill handler `0x10dce` writes fill id `0x78316e`.
- Fill handler `0x10898` maps the current `#P` selector and `0x78316e` to the
  rule selector byte: solid selector `7`, gray selectors `0..7`, or pattern
  selectors `8..13` with landscape remaps.
- Clip/queue helper `0x10b80` writes source record `0x782a88`, ensures current
  page root `0x78297a` through `0x10084`, and calls `0x13386` only for
  nonempty on-page rectangles.
- Producer `0x13386 -> 0x133aa` derives bucket/key fields through `0x134d6`,
  allocates a 14-byte rule object through `0x1381c`, and links it under
  page-root rule list `+0x24`.
- Retry path `0x10d22..0x10d3e` sets page-root flag `+0x15.0`, publishes the
  old root through `0xff1e`, ensures a fresh root, and retries the same
  already-clipped source record when `0x13386` reports no room.
- Bridge `0x1edc6` copies page-root `+0x24` to render-record `+0x1c`, ORs
  object byte `+0x05` with `0x10`, and copies object height `+0x0a` into
  continuation word `+0x0c`.

Readers and consumers:

- `0x10898` consumes width `0x78316a`, height `0x783166`, fill id
  `0x78316e`, and the parsed `#P` command record. Zero dimensions or invalid
  selector/id combinations exit without queueing.
- `0x10b80` consumes cursor `0x782c8a/0x782c8e`, orientation `0x782da3`, and
  page extents `0x782db8/0x782db6` to reject, clip, or transform the rule
  source.
- `0x133aa` consumes stream allocator state
  `0x782a70/0x782a72/0x782a76` and preserves ascending object byte `+0x04`
  order in the rule list; equal buckets insert after the existing equal node.
- Publication `0xff1e` freezes the current root. `0x1ed84` selects the
  published source, and `0x1edc6` normalizes the rule list for rendering.
- Render entry `0x1ef6a` calls rule-list walker `0x1f446` after compact bucket
  dispatch `0x1efc2` and before fixed-list dispatch `0x1f756`.
- `0x1f446` dispatches selector `7` to solid helper `0x1f596`; selectors
  `0..6` and `8..13` dispatch to pattern helper `0x1f4e0`.
- Solid and pattern helpers consume packed key `+0x06`, width `+0x08`, and
  continuation word `+0x0c`; they mutate `+0x0c` when the rule crosses render
  bands.

Output effect:

- `ESC *c12a5b0P` queues selector-7 object
  `00 00 00 00 01 07 4a 00 00 0c 00 05 00 00`; after `0x1edc6`, the object is
  `00 00 00 00 01 17 4a 00 00 0c 00 05 00 05`.
- `! ESC *c12a5b50g2P` writes fill state `50`, maps `2P` to gray selector
  `4`, bridges selector byte `0x04` to `0x14`, and renders through
  `0x1f4e0`.
- `! ESC *c12a5b2g3P` writes fill state `2`, maps `3P` to portrait pattern
  selector `9`, bridges selector byte `0x09` to `0x19`, and renders through
  `0x1f4e0`.
- Mixed page streams keep this rule object separate from compact/raster
  buckets: compact and raster objects live under root `+0x1c`, while rectangle
  rules live under root `+0x24` and render through the rule walker.

Field classification for this owner:

- Canonical state:
  rectangle width/height/fill fields `0x78316a`, `0x783166`, and `0x78316e`;
  source record `0x782a88`; current root `0x78297a`; rule list `+0x24`;
  rule object bytes; published source record; and render-record rule list
  `+0x1c`.
- Derived/cache state:
  bucket/key fields `0x782a7c`, `0x782a7d`, and `0x782a7e`; horizontal phase
  `0x782dc0`; bridged selector bit `0x10`; continuation word `+0x0c`; render
  band fields; and destination mask state in `0x1f596`, `0x1f4e0`, and
  `0x1f6ee`.
- Parser scratch:
  parser modes, command-record cursor `0x78299e`, parsed numeric parameters,
  and relative parser state consumed by the size/fill handlers.
- Firmware bookkeeping:
  stream allocator fields `0x782a70/0x782a72/0x782a76`, page-root retry bit
  `+0x15.0`, publication flag `0x782996`, pool cursors, and render-work
  scheduler state.
- Hardware/external state:
  none for the ROM-local rectangle object and renderer contract after the same
  normalized host bytes and publication boundary exist.
- Unknown:
  only streams that change clipping, allocator/rollover, no-room retry fields,
  rule object bytes, bridge normalization, selector dispatch, or row
  construction create new ROM-local work.

## Size Commands

`0x10e68` handles `ESC *c#A`; `0x10e22` handles `ESC *c#B`. Both rewind
`0x78299e` by six, require an explicit positive integer parameter, and store
the dot value as a packed word in the corresponding longword field. Missing
or nonpositive values clear the stored size.

`0x10a40` handles `ESC *c#H`; `0x10ae0` handles `ESC *c#V`. These handlers
accept explicit nonnegative decipoint values, multiply by five 300-dpi
subunits per decipoint, round fractional subunits up, add the firmware's
`+11` subunit bias, and store the packed result. Missing, negative, or zero
values clear the stored size.

Fixture-pinned examples:

- `ESC *c72H` stores `0x001e000b`.
- `ESC *c1.5V` stores `0x00010007`.

## Command Handler Boundaries

The ROM-local command boundary for this family is:

- `0x10e68..0x10eac` handles dot width `ESC *c#A`; `0x10e22..0x10e66`
  handles dot height `ESC *c#B`. Both rewind `0x78299e`, require an explicit
  positive integer in parser record word `+2`, clear the target longword for
  missing or nonpositive values, and otherwise store the word in
  `0x78316a` or `0x783166` while clearing the fractional companion word.
- `0x10a40..0x10ade` handles decipoint width `ESC *c#H`;
  `0x10ae0..0x10b7e` handles decipoint height `ESC *c#V`. Both reject missing,
  negative, or zero parsed values, convert integer/fraction words through
  `value * 5 / 10000`, round up when helper `0x33238` reports a remainder, add
  the ROM bias `+0x0b`, convert through `0x104d8`, and write the packed
  dimension to `0x78316a` or `0x783166`.
- `0x10dce..0x10e20` handles area-fill id `ESC *c#G`. It rewinds
  `0x78299e`, treats missing or zero explicit values as `0`, takes the absolute
  value for negative explicit values, and writes word `0x78316e`.
- `0x10898..0x108f2` handles fill selector `ESC *c#P` setup. It rewinds
  `0x78299e`, reads area-fill state `0x78316e`, records missing/zero selector
  as solid selector `7`, and normalizes an explicit negative selector to its
  absolute value.
- `0x10910..0x109fc` maps selector `2` through percent-fill thresholds from
  `0x78316e`: `1..2 -> 0`, `3..10 -> 1`, `11..20 -> 2`, `21..35 -> 3`,
  `36..55 -> 4`, `56..80 -> 5`, `81..99 -> 6`, and `100 -> 7`. A percent id
  below `1` or above `100` exits without queueing.
- `0x10928..0x10a34` maps selector `3` through pattern ids `1..6` to
  selectors `8..13`. In landscape orientation byte `0x782da3 == 1`, ids
  `1..4` are remapped to selectors `9`, `8`, `11`, and `10`.
- `0x108f2..0x1090c` is the shared queue gate after selector mapping. Width
  `0x78316a` and height `0x783166` must both be nonzero before the handler
  calls clip/queue helper `0x10b80`; otherwise the selector state is recorded
  in scratch `0x782a88+8` but no page object is allocated.
- `0x10b80..0x10c10` reads cursor x/y, page extents, and stored dimensions,
  rejects starts past the right or bottom page edge, rejects negative starts
  whose rectangle does not cross back onto the page, and clips negative x/y by
  reducing the effective source origin to zero while preserving the original
  cursor value for later width/height calculation.
- `0x10c10..0x10d0a` is the portrait queue path. It writes source x/y at
  `0x782a88+0/+2`, computes clipped width/height at `+4/+6`, rejects empty
  clipped results, ensures a page root through `0x10084`, and calls
  `0x13386`.
- `0x10c74..0x10dcc` is the landscape queue path. It swaps axes, derives the
  queued x from the portrait y axis, derives queued y from the clipped right
  edge of the portrait x extent, computes clipped dimensions in swapped order,
  then shares the `0x10084 -> 0x13386` page-object insertion path.
- `0x10d22..0x10d3e` is the no-room retry path. If `0x13386` returns zero,
  it sets page-root flag `+0x15.0`, publishes the current root through
  `0xff1e`, allocates a fresh root through `0x10084`, and retries the same
  source record at `0x782a88`.
- `0x13386..0x133a8` derives ordered-list key fields through `0x134d6` and
  then calls `0x133aa`.
- `0x133aa..0x13470` allocates a 14-byte rule object through `0x1381c`,
  inserts it under current root `+0x24` in ascending bucket order, writes
  object bytes from derived fields `0x782a7d` / `0x782a7e`, copies selector
  word `0x782a88+8`, width `+4`, and height `+6`, and returns zero without
  changing the list if allocation fails.

### Rectangle Outcome Matrix

This matrix is the owner-level routing table for new rectangle/rule streams.
A new `ESC *c` trace belongs here only when it changes one of these selector
predicates, clipped source records, allocation outcomes, rule object bytes,
bridge fields, render helpers, continuation mutations, or row-construction
inputs.

- Size or fill state only:
  `ESC *c#A/#B/#H/#V/#G` stops after handlers `0x10e68`, `0x10e22`,
  `0x10a40`, `0x10ae0`, or `0x10dce` write rectangle state
  `0x78316a`, `0x783166`, or `0x78316e`. No page root is ensured, no rule
  object is allocated, and the visible consumer is a later `ESC *c#P`.
- Alternate/data rectangle boundary:
  when alternate/data table `0x116f6` is active, uppercase `ESC *c`
  terminals `A/B/G/H/P/V` have no handler and lowercase
  `a/b/g/h/p/v` route only to rewind helper `0x11f4c`. The normal rectangle
  writers `0x10e68`, `0x10e22`, `0x10a40`, `0x10ae0`, `0x10dce`, and
  producer `0x10898` are not called. Width `0x78316a`, height `0x783166`,
  area-fill id `0x78316e`, clipped source record `0x782a88`, page-root
  rule-list head `+0x24`, publication state, and render inputs remain
  unchanged. Any later visible effect must come from replaying the stored
  bytes through normal parser mode, not from the alternate/data parse itself.
- Selector maps to no output:
  `0x10898..0x109fc` exits without queueing when selector `2` sees area-fill
  id outside `1..100`, selector `3` sees pattern id outside `1..6`, or the
  normalized selector is not one of the ROM-supported forms. The handler may
  have read `0x78316e` and parser record `+2`, but no canonical page/image
  state changes.
- Zero dimension gate:
  after selector mapping, `0x108f2..0x1090c` requires nonzero width
  `0x78316a` and height `0x783166`. If either is zero, selector scratch
  `0x782a88+8` can be written, but `0x10b80` is not called and no page object
  exists for publication or rendering.
- Off-page or empty-after-clip gate:
  `0x10b80..0x10c10` rejects starts to the right or below the page extents,
  rejects negative starts whose rectangle does not cross back onto the page,
  and later rejects clipped width or height `<= 0`. These paths create no
  rule object and do not call `0x13386`.
- Portrait queue:
  `0x10c42..0x10d0a` writes clipped source x/y/width/height to
  `0x782a88+0/+2/+4/+6`, preserves selector `0x782a88+8`, ensures current
  root `0x78297a` through `0x10084`, and calls `0x13386`. The canonical page
  object, if allocation succeeds, is a 14-byte rule node under root `+0x24`.
- Landscape queue:
  `0x10c74..0x10dcc` uses the same reject/clip gates but swaps axes for the
  queued source record: queued x comes from the portrait y axis, queued y
  comes from the clipped portrait right edge, and queued width/height are the
  swapped effective dimensions. The downstream `0x10084 -> 0x13386 ->
  0x133aa` object path is the same as portrait.
- Rule-list allocation success:
  `0x13386..0x133aa` derives bucket/key fields through `0x134d6` and
  `0x133aa..0x13470` links an allocated object into page-root rule list
  `+0x24` in ascending bucket order. Object byte `+0x04` is the bucket byte,
  `+0x05` is the fill selector, `+0x06` is the packed key, `+0x08` is width,
  and `+0x0a` is height. The next visible consumer is publication `0xff1e`
  followed by bridge `0x1ed84 -> 0x1edc6`.
- Rule-list allocation failure and retry:
  if `0x13386` returns zero, `0x10d22..0x10d3e` sets retry bit
  `root+0x15.0`, publishes the current root through `0xff1e`, ensures a fresh
  root through `0x10084`, and retries the same already-clipped source record
  at `0x782a88`. The failed `0x133aa` call preserves the old rule-list head;
  any later object bytes belong to the retry on the fresh root.
- Bridge normalization:
  `0x1edc6` copies page-root rule list `+0x24` to render-record list `+0x1c`,
  ORs selector byte `+0x05` with `0x10`, and copies object height `+0x0a` to
  continuation word `+0x0c`. After this point, selector byte and continuation
  word are render state, not parser scratch.
- Solid render:
  render entry `0x1ef6a` calls rule walker `0x1f446`; low selector nibble `7`
  dispatches to solid helper `0x1f596`. The helper consumes key `+0x06`,
  width `+0x08`, continuation `+0x0c`, destination split from `0x1f626`, and
  writes black mask words. Band-crossing rules mutate continuation `+0x0c`.
- Pattern render:
  all other pinned selector nibbles `0..6` and `8..13` dispatch from
  `0x1f446` to pattern helper `0x1f4e0`. The helper consumes the same key,
  width, and continuation fields plus pattern table `0x2fefe` and mask helper
  `0x1f6ee`; shifted and band-crossing pattern rows are therefore part of the
  rectangle pixel contract.

State classification for the matrix:

- Canonical command state is width `0x78316a`, height `0x783166`, and area-fill
  id `0x78316e`.
- Canonical page/image state is the clipped source record `0x782a88`, current
  root `0x78297a`, rule-list head `root+0x24`, 14-byte rule object fields,
  published source record, and render-record rule list `+0x1c`.
- Derived/cache state is bucket byte/key `0x782a7c..0x782a7e`, horizontal
  phase `0x782dc0`, bridged selector bit `0x10`, continuation word `+0x0c`,
  render band fields, and solid/pattern destination masks.
- Parser scratch is the six-byte `ESC *c` command record at `0x78299e - 6`,
  parser modes for lowercase chaining, and selector scratch before
  `0x10b80` accepts a nonzero on-page rectangle.
  Alternate/data `ESC *c` records that terminate at blank table rows or
  `0x11f4c` remain parser scratch only and do not become canonical rectangle
  command state.
- Firmware bookkeeping is stream allocator state `0x782a70/0x782a72/0x782a76`,
  no-room retry bit `root+0x15.0`, publication flag `0x782996`, and render
  scheduler progress.
- Unknown: no ROM-local outcome in this matrix is unknown for the documented
  selector-7, gray, pattern, landscape-remap, clipping, no-room, bridge, and
  render paths. Future work must change a named predicate, source field,
  object byte, retry field, bridge field, helper dispatch, continuation
  mutation, or row construction before this matrix changes.

## Fill Selector At 0x10898

`0x10898` handles `ESC *c#P`. It rewinds the parsed record and maps the fill
selector before it validates width/height:

| `ESC *c#P` parameter | Area-fill source | Selector result |
| --- | --- | --- |
| missing or `0` | ignored | `7` solid black |
| `2` | `0x78316e` percent `1..2` | `0` |
| `2` | percent `3..10` | `1` |
| `2` | percent `11..20` | `2` |
| `2` | percent `21..35` | `3` |
| `2` | percent `36..55` | `4` |
| `2` | percent `56..80` | `5` |
| `2` | percent `81..99` | `6` |
| `2` | percent `100` | `7` |
| `3` | pattern id `1..6` | selector `8..13` |

For portrait orientation, pattern ids `1..6` map directly to selectors
`8..13`. For landscape orientation, pattern ids `1..4` are remapped:

| Pattern id | Landscape selector |
| ---: | ---: |
| `1` | `9` |
| `2` | `8` |
| `3` | `11` |
| `4` | `10` |

Invalid mode/id combinations return without queueing. If either
`0x78316a` or `0x783166` is zero, the handler records the selector but does
not queue an object.

Fixture-pinned selector examples:

- black fill selector: `7`
- gray-fill id `50`: selector `4`
- landscape pattern id `2`: selector `8`

## Clip And Queue At 0x10b80

`0x10b80` converts current cursor, stored dimensions, page extents, and
orientation into the source record at `0x782a88`.

The instruction-level flow is:

- `0x10b80..0x10b9e` clears the saved negative-origin compensation slots,
  loads current x from `0x782c8a` into `D4`, and loads current y from
  `0x782c8e` into `D3`.
- `0x10ba0..0x10bcc` computes the last valid x coordinate from
  `0x782db8 - 1`. Starts to the right of that coordinate return immediately.
  Negative starts are accepted only when `x + width >= 0`; accepted negative
  starts save the original x in the local compensation slot and continue with
  effective x `0`.
- `0x10bd4..0x10c0e` repeats the same reject/negative-crossing test for y
  using `0x782db6 - 1` and rectangle height `0x783166`. Accepted negative y
  starts save the original y and continue with effective y `0`.
- `0x10c10..0x10c40` prepares the shared source record and branches on
  orientation byte `0x782da3`. Zero selects the portrait queue path; nonzero
  selects the landscape queue path.
- `0x10c42..0x10d0a` is the portrait path. It writes clipped x/y to
  `0x782a88+0/+2`, subtracts any negative-origin compensation from stored
  width/height, clips right and bottom edges against page extents, rejects
  empty results, then writes width/height to `+4/+6`.
- `0x10c74..0x10dcc` is the landscape path. It writes queued x from the
  clipped portrait y axis, derives queued y from the clipped portrait right
  edge, swaps the effective height into queued width and effective width into
  queued height, and applies the same empty-result rejection before queueing.
- `0x10d0a..0x10d1e` ensures a page root through `0x10084` and queues
  `0x782a88` through `0x13386`. A nonzero return exits with the object linked
  under page-root rule list `+0x24`.
- `0x10d22..0x10d3e` is the allocation retry path. A zero return from
  `0x13386` sets page-root flag `+0x15.0`, publishes the current root through
  `0xff1e`, ensures a fresh root through `0x10084`, and retries the same
  already-clipped source record.

Portrait path:

- Reject if start x is beyond `page_width - 1`.
- Reject if start x is negative and `x + width` is still negative.
- Clip negative x by reducing width and queueing x `0`.
- Reject if start y is beyond `page_height - 1`.
- Reject if start y is negative and `y + height` is still negative.
- Clip negative y by reducing height and queueing y `0`.
- Clip right and bottom edges to page extent.
- Queue source x/y/width/height in the same axes.

Landscape path:

- Uses the same reject and clip gates.
- Stores source x from the portrait y axis.
- Computes source y from the right edge of the portrait x extent.
- Swaps the queued dimensions so portrait height becomes rule width and
  portrait width becomes rule height.

For queued rectangles, `0x10b80` ensures a page root through `0x10084` and
calls `0x13386` with source record `0x782a88`.

Concrete negative-left clipping fixture:

- start x `-3`, width `10`
- queued x `0`, width `7`
- queued object before bridge:

```text
00 00 00 00 00 07 40 00 00 07 00 05 00 00
```

The harness also pins right-edge, top-edge, bottom-edge, landscape
right-edge, horizontal-outside, vertical-outside, and empty-after-clip cases.
Fixture `0x10b80 rectangle fill clips negative left edge before queueing`
separates the negative-left source-record case from later rule-list insertion.
Fixture `0x10b80 rectangle fill clips right/top/bottom edges and ignores
off-page fills` covers the remaining clipping and reject outcomes.

## Rule Object At 0x13386 / 0x133aa

`0x13386` computes derived fields through `0x134d6`, then calls `0x133aa`.
`0x134d6` computes:

- `0x782a7c = source_y >> 4`
- `0x782a7e = ((source_y << 12) & 0xf000)
  | (((source_x + 0x782dc0) & 0x0f) << 8)
  | (((source_x + 0x782dc0) >> 4) & 0x00ff)`

`0x133aa` allocates 14 bytes through `0x1381c` and inserts the object under
page root `+0x24` by ascending object byte `+4`. Equal bucket bytes insert
after the existing equal node in the address-aware fixture.

Rule object layout:

| Offset | Meaning |
| ---: | --- |
| `+0x00` | next pointer |
| `+0x04` | bucket byte from `0x782a7d` |
| `+0x05` | fill selector |
| `+0x06` | packed key from `0x782a7e` |
| `+0x08` | width |
| `+0x0a` | height |
| `+0x0c` | render continuation height, set by bridge |

The primary black-rule fixture queues this object before bridge:

```text
00 00 00 00 01 07 4a 00 00 0c 00 05 00 00
```

After the `0x1edc6` bridge, the object is:

```text
00 00 00 00 01 17 4a 00 00 0c 00 05 00 05
```

Bridge behavior:

- `0x1edc6` copies page-root `+0x24` to render-record `+0x1c`.
- It ORs object byte `+5` with `0x10`.
- It copies height word `+0x0a` into continuation word `+0x0c`.

Address-aware storage fixture:

- `0x133aa` uses `0x1381c` storage.
- The first object can become root `+0x24`.
- A smaller bucket inserts at the head.
- A larger bucket inserts at the tail.
- An equal bucket inserts after the existing equal bucket.

Fixture `0x133aa address-aware rule-list insertion uses 0x1381c storage`
pins the allocator state and ordered insertion cases. Fixture `0x133aa
no-room return preserves rule-list head` covers the failure return consumed by
the `0x10d22` retry path: the old `+0x24` head remains canonical until the
retry publishes the old root and allocates a fresh one.

The shared bridge fixture `0x1edc6 page-record bridge normalizes rule and
fixed lists` proves that page-root rule list `+0x24` is copied to
render-record `+0x1c` and normalized in place. It also covers the sibling
fixed-list normalization path; fixture `0x137a2/0x136d2-modeled fixed-rule
list object and bridge normalization` keeps that sibling list out of
rectangle semantics except where `0x1ef6a` must walk both lists in a fixed
call order.

## No-Room Retry At 0x10d22

If `0x13386` returns zero, `0x10b80` enters the `0x10d22..0x10d3e` retry
path:

1. Set page-root flag bit `root+0x15.0`.
2. Publish the current root through `0xff1e`.
3. Ensure a fresh page root through `0x10084`.
4. Retry the same source record through `0x13386`.

The parser-to-retry fixture uses the same `ESC *c12a5b0P` parser trace. It
starts with an existing compact text bucket, marks retry flag `0x0001`,
publishes that bucket, allocates a fresh root, retries the selector-7 object,
bridges it through `0x1edc6`, and renders the retried rule rows.

Retried object:

```text
00 00 00 00 01 07 4a 00 00 0c 00 05 00 00
```

## Render Dispatch

Rule rendering is separate from compact text and raster bucket rendering.
`0x1ef6a` calls `0x1f446` for the rule list after `0x1edc6` has copied and
normalized page-root `+0x24`.

`0x1f446` walks the bridged rule list for each five-bucket render band:

- If `object[4] > band_word + 4`, the walker stops for this band.
- If continuation word `+0x0c` is not positive, the object is skipped.
- Selector `7` dispatches to solid helper `0x1f596`.
- Other selectors dispatch to pattern helper `0x1f4e0`.

The bridged current-band flag is object byte `+5 & 0x10`. On the first band,
the renderer clears that flag, uses the original bucket delta and row-low
bits, and subtracts the available row count from continuation word `+0x0c`.
On continuation bands, it clears the upper row bits from the key and resumes
from y `0` of the new band.

### Solid Rules

`0x1f596` handles selector `7`. It decodes key `0x4a00` as:

- x `10`
- y `20`
- width `12`
- rows `5`
- partial mask `0xfff0`

Rendered black-rule visible rows:

```text
......................
..........############
..........############
..........############
..........############
..........############
```

Band-crossing solid fixture:

- starts at y `78`
- height `5`
- first band draws `2` rows
- object `+0x0c` carries `3` remaining rows
- next band draws `3` rows from y `0`

Fixture `0x1f596 carries solid rule remainder across render bands` pins the
mutated continuation object and the second-band rows. The continuation word is
canonical render state after `0x1edc6`, not parser scratch.

### Pattern Rules

`0x1f4e0` handles non-solid selectors through the pointer table at
`0x2fefe`. The full fixture-pinned selector table is:

| Selector | Pattern base |
| ---: | ---: |
| `0` | `0x02ff3e` |
| `1` | `0x02ffde` |
| `2` | `0x03007e` |
| `3` | `0x03011e` |
| `4` | `0x0301be` |
| `5` | `0x03025e` |
| `6` | `0x0302fe` |
| `8` | `0x03039e` |
| `9` | `0x03043e` |
| `10` | `0x0304de` |
| `11` | `0x03057e` |
| `12` | `0x03061e` |
| `13` | `0x0306be` |

Sub-byte masks come from `0x1f6ee` using mask tables near
`0x3089e` and `0x308be`.

Gray selector `0` fixture:

- pattern base `0x02ff3e`
- first words `0x8080, 0x0000, 0x0000, 0x0000`
- left mask `0xff00`
- right mask `0x0000`

Rendered gray-rule rows:

```text
#.......
........
........
........
```

Shifted HP-pattern selector `13` fixture:

- key `0x3500`
- decoded x `5`, y `3`
- width `19`
- row-low `3`
- pattern start `0x0306c4`
- left mask `0x07ff`
- right mask `0xff00`

Rendered shifted HP-pattern rows:

```text
........................
........................
........................
.......###......###....#
........###....###......
.........###..###.......
..........######........
...........####.........
...........####.........
```

Fixture `0x1f446/0x1f4e0 renders gray selector pattern pixels` isolates the
gray-selector helper path, while `0x1f4e0 renders sub-byte shifted HP pattern
rule pixels` isolates the shifted HP-pattern path. Fixtures `0x1f4e0 carries
patterned rule remainder across render bands` and `0x1f446 page-band walk
assembles patterned rule rows` prove that non-solid rule continuation mutates
the bridged node between bands and that the walker resumes from the carried
node on the next band.

### Rule Destination And Row Writes

The solid and patterned helpers share the same destination setup contract in
`generated/disasm/ic30_ic13_bitmap_draw_core_01f3d4.lst`.

At `0x1f4e8..0x1f514` and `0x1f59e..0x1f5ca`, the helper reads packed
coordinate word `object[+6]` into `D1`, clears bridged current-band flag
`object[+5].4`, computes the current-band row count in `D3`, subtracts that
count from continuation word `object[+0x0c]`, and shortens `D3` if the
continuation word goes nonpositive. A first-band object uses the row-high bits
from `object[+6]` and the bucket delta from walker `0x1f446`; a continuation
object masks `D1` to the low twelve row bits and clears the walker delta.

Helper `0x1f626..0x1f6ec` then converts the packed coordinate into a concrete
destination:

- `0x1f626..0x1f63e` writes destination phase byte `$a001` from the
  coordinate's sub-byte bits, setting bit `0x10` for a nonzero phase.
- `0x1f642..0x1f648` converts the coordinate low byte to byte-pair offset
  `A2`.
- `0x1f64a..0x1f688` selects `0x783a28 + row_offsets[row] + A2` for objects
  that start in the active band without a bucket-delta carry.
- `0x1f68a..0x1f6ce` selects the active band with an added
  `0x783a1c * delta_rows` stride when the bucket delta still fits within
  `0x783a20`; if the requested row count crosses that active-band boundary,
  `D3` is returned with rows for the active band in the low word and rows for
  the fallback buffer in the high word.
- `0x1f6d2..0x1f6ec` selects fallback buffer `0x7810b4 + A2` plus
  `0x783a1c * adjusted_row` when the bucket delta starts outside the active
  band.

Solid helper `0x1f596` consumes that destination as a run of black words.
After `0x1f5d0..0x1f5e6` derives full-word count and right-edge mask from
`object[+8]`, loop `0x1f5f4..0x1f60a` writes `0xffff` for each full word,
writes the masked tail word, and advances one output row by stride
`0x783a1c`. If `0x1f626` returned fallback rows in the high word of `D3`,
`0x1f60e..0x1f61e` resets `A1` to `0x7810b4 + A2` and repeats the same row
loop for the remaining rows.

Pattern helper `0x1f4e0` uses the same destination split, but
`0x1f51a..0x1f54c` first calls mask helper `0x1f6ee` and selects the pattern
row table through pointer table `0x2fefe`. Loop `0x1f558..0x1f57a` writes the
left-masked pattern word, any full interior pattern words, and the
right-masked tail word for each row, then advances by `0x783a1c`.
`0x1f57e..0x1f58e` repeats from `0x7810b4 + A2` when the high word of `D3`
contains fallback rows.

Mask helper `0x1f6ee..0x1f754` is therefore part of the pixel contract for
non-solid rectangle output. It builds the left and right masks in `D2` from
the coordinate phase and requested width using mask tables at `0x3089e` and
`0x308be`; the patterned helper consumes the low word as the left mask and
the high word as the right mask.

## Mixed Page-Record Composition

The rectangle/rule producer has been composed with adjacent page producers in
the checked-in fixture suite, not only as an isolated rule object. Fixture
`host-fetched text plus rectangle page record feeds 0x1ed84 and 0x1ef6a`
drains:

```text
21 1b 2a 63 31 32 61 35 62 30 50
```

That is printable `!` followed by `ESC *c12a5b0P`. The resulting page record
contains a compact text bucket and selector-7 rule list; `0x1ed84` /
`0x1edc6` bridge the record, and `0x1ef6a` calls bucket dispatch `0x1efc2`,
rule dispatch `0x1f446`, and fixed-list dispatch `0x1f756` in the pinned
order.
Fixture `addressed text plus rectangle stream matches page-record output`
adds the addressed storage form for the same stream: compact text is in bucket
array `+0x1c`, the selector-7 rule is in rule list `+0x24`, context slot 0 is
`0x440946b4`, and the rendered rows are derived through the page-record runner.

Fixture `host-fetched alternate rectangle selectors feed full page records`
keeps the same compact `!` text producer and rectangle origin, then drives two
additional full page-record streams through fetched host bytes, parser
dispatch, rule production, bridge normalization, and render rows:

- `21 1b 2a 63 31 32 61 35 62 35 30 67 32 50` =
  `! ESC *c12a5b50g2P`. Parser handlers are `0xd04a`, `0x10e68`,
  `0x10e22`, `0x10dce`, and `0x10898`. `50g` writes area-fill id `50`, and
  `2P` maps it to gray selector `4`. The page rule object is
  `00 00 00 00 01 04 5c 01 00 0c 00 05 00 00`; after `0x1edc6` bridge
  normalization it is `00 00 00 00 01 14 5c 01 00 0c 00 05 00 05`.
  `0x1f446` dispatches selector `4` to pattern helper `0x1f4e0`; the full
  26-row composed page digest is
  `f7e8bc65420e95a1456db1f0673a164f8ae2f1919fb4b5b8964886354fc54fdf`.
- `21 1b 2a 63 31 32 61 35 62 32 67 33 50` =
  `! ESC *c12a5b2g3P`. The same parser handlers run, `2g` writes area-fill id
  `2`, and `3P` maps it to HP-pattern selector `9` in portrait orientation.
  The page rule object is `00 00 00 00 01 09 5c 01 00 0c 00 05 00 00`; after
  bridge normalization it is `00 00 00 00 01 19 5c 01 00 0c 00 05 00 05`.
  `0x1f446` dispatches selector `9` to `0x1f4e0`; the full 26-row composed
  page digest is
  `c981832502ee7ed97b339959027448f878d591e3909519a3b9233e31200ac599`.

For both alternate selector streams, `0x1ef6a` executes call order
`0x1ef86 -> 0x1efc2 -> 0x1f446 -> 0x1f756`, decodes rule key `0x5c01` as
x `28`, y `21`, row-low `5`, subbyte `12`, byte-pair offset `2`, width `12`,
and draws five rule rows into the same 40-pixel-wide composed page band as the
compact text rows.

Fixture `host-fetched rectangle selector matrix feeds full page records`
extends the same page-record path to every non-solid selector id. Portrait
streams `! ESC *c12a5b#g2P` cover gray selectors `0..6` with area-fill ids
`2`, `10`, `20`, `35`, `50`, `80`, and `99`. Portrait streams
`! ESC *c12a5b#g3P` cover pattern selectors `8..13` with pattern ids `1..6`.
Landscape streams for pattern ids `1..4` pin the ROM remap as
`1 -> 9`, `2 -> 8`, `3 -> 11`, and `4 -> 10`. Each case asserts the fetched
stream, parser handlers `0xd04a`, `0x10e68`, `0x10e22`, `0x10dce`, and
`0x10898`, the pre-bridge rule object, the `0x1edc6` bridged rule object,
`0x1f4e0` helper dispatch, mutated continuation object, rendered row count,
rendered row width, and composed row SHA-256.

Fixture `host-fetched text rectangle and raster page record feeds 0x1ed84 and
0x1ef6a` extends that stream with `ESC *t300R ESC *r0A ESC *b2W c3 3c`, so
the same current page record contains:

- compact text through `0xd04a` / `0x12f2e` / `0x1387c`;
- selector-7 rectangle rule through `0x10898` / `0x10b80` /
  `0x13386` / `0x133aa`;
- mode-0 raster through delayed `0x11f82` / `0x12218` / `0x105d0` /
  `0x13070` / `0x13250`.

The lower-level composition fixtures prove the same renderer layering without
the full parser front end. `bridged compact text and rule objects compose into
one page band` composes compact text with a selector-7 rule after the
`0x1edc6` bridge. `bridged text, rule, and raster layers compose into one page
band` adds the mode-0 raster layer. `0x1ef6a render entry composes bucket,
rule, and fixed-width lists in call order` pins the dispatcher order as
`0x1ef86 -> 0x1efc2 -> 0x1f446 -> 0x1f756`; the fixed-list slot may be empty
for rectangle-only streams, but it is still part of the render-entry contract.

The addressed FF publication fixtures pin the page-record storage for that
mixed stream. Fixture `addressed text/rule/raster field groups reach
publication and render entry` classifies these fields:

- canonical fields: text object `0x00d0c004`, rule object `0x00d0c02a`,
  raster object `0x00d0c038`, bucket head `+0x1c = 0x00d0c038`, rule head
  `+0x24 = 0x00d0c02a`, context slot 0 `0x440946b4`, and published rule list
  `00 00 00 00 01 07 5c 01 00 0c 00 05 00 00`;
- parser scratch: rectangle records for `ESC *c12a`, `5b`, and `0P`, plus
  restored raster record `80 57 00 02 00 00`, delayed raster snapshot
  `01 00 01 05 d0 80 57 00 02 00 00`, payload offset `28`, and payload
  `c3 3c`;
- derived/cache fields: rule bucket/key from `0x782a7c` / `0x782a7e`,
  render band height `0x783a20 = 0x0050`, band base `0x783a22 = 0`, and
  active row origin `0x783a28 = 0x00100000`;
- firmware bookkeeping: stream allocator state
  `0x782a70 = 0x00bc`, `0x782a72 = 0x00d0c000`,
  `0x782a76 = 0x00d0c044`, one page-root allocation, one stream allocation,
  one publication, one root clear, and publication flag `1`;
- unknown: parser-to-allocator variants that change clipping output, allocator
  retry state, rule object bytes, bridge state, or row-construction inputs.

Fixture `addressed text rectangle raster stream matches page-record output`
checks the addressed current-page form before FF publication. Fixture
`addressed text rectangle raster publication renders rows` checks the
published addressed form after modeled `0xff1e`. Fixture `published text
rectangle and raster page record feeds 0x1ed84 and 0x1ef6a` verifies that the
published record crosses the same render-entry bridge as the current-page
form.

The alternate selector fixtures classify `0x78316e` as canonical fill state:
`0x10dce` writes it from `#g`, and `0x10898` consumes it for `2P` and `3P`.
The selector byte in each page rule object is canonical page content before
bridge normalization and derived render content after `0x1edc6` ORs bit
`0x10` and copies height into continuation word `+0x0c`. The SHA-256 row
digests are derived/cache evidence for the composed software-visible output,
not firmware state.

Fixture `host-fetched text rectangle multi-row raster FF publishes rendered
page record` broadens the same mixed stream to two delayed raster transfers:

```text
21 1b 2a 63 31 32 61 35 62 30 50 1b 2a 74 33 30 30 52
1b 2a 72 30 41 1b 2a 62 32 57 f0 0f 1b 2a 62 32 57 0f f0 0c
```

That is printable `!`, selector-7 rule `ESC *c12a5b0P`, raster setup
`ESC *t300R ESC *r0A`, two delayed `ESC *b2W` transfers, and FF. The modeled
publication preserves bucket `0` as newest-first raster row, prior raster row,
then compact text; the bridged rule list is the same selector-7 rule path
documented above. Fixture
`addressed text/rule/multi-row raster publication preserves bucket chain`
pins the addressed storage shape:

- raster objects at `0x00d0d038` and `0x00d0d044`;
- bucket chain `0x00d0d044 -> 0x00d0d038 -> 0x00d0d004`;
- published raster objects
  `00 d0 d0 38 80 00 00 02 10 00 0f f0` and
  `00 d0 d0 04 80 00 00 02 00 00 f0 0f`;
- parser scratch records `80 57 00 02 00 00` at payload offsets `28`
  and `35`;
- allocator bookkeeping ending at `0x782a70 = 0x00b0`,
  `0x782a72 = 0x00d0d000`, and `0x782a76 = 0x00d0d050`;
- raster `row_y = 2` and render dispatch targets `0x1f88e`, `0x1f88e`,
  and `0x1effe`, with the selector-7 rule rendered in the same published
  page record.

Fixture `0x1ef6a page-band walk merges text raster and crossing rule` extends
this mixed composition across render bands. It carries a mutated patterned
rule node from band `0` to band `5`, while compact text and mode-0 raster
bucket entries continue to dispatch through `0x1efc2`.

## Covered Boundary

The rectangle/rule checkpoint is covered from parser dispatch through visible
rows for these concrete clusters:

- `ESC *c12a5b0P`: parser modes `0 -> 1 -> 3 -> 16 -> 16 -> 16 -> 0`, handlers
  `0x11eb6`, `0x11ec8`, `0x11eda`, `0x10e68`, `0x10e22`, and `0x10898`, and
  the selector-7 rule object under page-root `+0x24`.
- `! ESC *c12a5b0P`: host-fetched compact text plus selector-7 rule, bridged
  through `0x1ed84` / `0x1edc6` and rendered through `0x1ef6a`.
- `! ESC *c12a5b#g2P` and `! ESC *c12a5b#g3P`: gray selectors `0..6`,
  pattern selectors `8..13`, and landscape pattern remaps `1 -> 9`,
  `2 -> 8`, `3 -> 11`, and `4 -> 10`.
- `! ESC *c12a5b0P ESC *t300R ESC *r0A ESC *b2W c3 3c`: compact text,
  selector-7 rule, one mode-0 raster object, addressed storage, FF
  publication, and published render rows.
- The two-transfer sibling ending in `ESC *b2W f0 0f ESC *b2W 0f f0 FF`:
  newest-first raster bucket chain, the same selector-7 rule list, addressed
  storage, publication, and render dispatch.
- The no-room retry path at `0x10d22`: an existing compact text bucket is
  published through `0xff1e`, a fresh root is allocated through `0x10084`, and
  the preserved selector-7 source record is retried through `0x13386`.

These streams cover multiple handlers in the same command family, the shared
`0x10b80 -> 0x13386 -> 0x133aa` producer path, the shared no-room exit, and
end-to-end parser-to-render output. New rectangle work should start only from
a stream that changes one of those fields or rows, not from another proof of
the same selector/object/bridge path.

Writers are the parser handlers and producers listed above, plus `0xff1e`
when fixtures `host-fetched text rectangle raster FF publishes rendered page
record` and `addressed text rectangle raster FF publishes rendered page
record` finalize the heterogeneous current page. The multi-row sibling uses
the same writers but calls the delayed raster transfer path twice before FF.
Readers are `0x1ed84` /
`0x1edc6`, `0x1ef6a`, compact bucket dispatch `0x1efc2`, rule dispatch
`0x1f446`, raster dispatch `0x1f88e`, compact text dispatch `0x1effe`, solid
rule helper `0x1f596`, and pattern rule helper `0x1f4e0`.

## Reproduction Contract

A byte-stream reproduction must preserve these behaviors:

- Rectangle width, height, and area-fill id persist in firmware state until a
  later command changes or clears them.
- Dot dimensions store positive integers directly; missing and nonpositive
  parameters clear the dimension.
- Decipoint dimensions use five 300-dpi subunits per decipoint, round
  fractional subunits up, then add the firmware's `+11` subunit bias.
- `ESC *c#P` parameter `0` or missing means solid selector `7`.
- `ESC *c2P` maps `0x78316e` percentage thresholds to selectors `0..7`.
- `ESC *c3P` maps pattern ids `1..6` to selectors `8..13`, with landscape
  remaps for ids `1..4`.
- Invalid selector inputs and zero dimensions do not queue an object.
- `0x10b80` clips against page extents before queueing and drops off-page or
  empty-after-clip rectangles.
- Rule objects are linked under page-root `+0x24`, not under the compact
  text/raster bucket array.
- `0x1edc6` must OR selector byte `+5` with `0x10` and copy height into
  continuation word `+0x0c`.
- Selector `7` renders through `0x1f596`; every other pinned selector renders
  through `0x1f4e0`.
- Continuation word `+0x0c` is mutated across render bands and must be
  carried between bands for pixel-perfect output.

## Remaining Edges

- `0x10898..0x133aa`: no unresolved software-visible middle edge remains for
  the covered selector-7, gray-selector, pattern-selector, landscape-remap,
  clipping, no-room retry, addressed-storage, publication, and mixed
  text/rule/raster streams listed in `Covered Boundary`. Remaining ROM-local
  work is limited to byte streams that change clipping output, `0x1381c`
  rollover/allocation state, retry publication fields, rule object bytes,
  bridge state, render dispatch, or ROM-derived row construction.
- Pattern rendering is fixture-pinned for selectors, masks, shifted rows, and
  band crossing. The initial mixed text/rule/raster/FF byte stream now provides
  a complete parser-produced page-record/render composition with selector-7
  rule output, mode-0 raster output, compact text, publication, and
  render-entry rows;
  `host-fetched alternate rectangle selectors feed full page records` adds
  detailed page-record fixtures for gray selector `4` from `50g2P` and
  portrait pattern selector `9` from `2g3P`, and `host-fetched rectangle
  selector matrix feeds full page records` extends that coverage to non-solid
  selectors `0..6` and `8..13` plus the landscape pattern remaps for ids
  `1..4`; the multi-row mixed text/rule/raster sibling now also proves the
  same rule list can be published with two delayed raster objects in the
  bucket chain;
  checked-in coverage also includes font-selection streams, downloaded-glyph
  FF publication, geometry-changing publication streams, and a parser-driven
  downloaded-glyph/rule/raster page. Remaining rectangle work is limited to
  cross-feature full-page combinations that expose new ROM-derived page-object
  fields, bridge state, render dispatch, continuation mutation, or rows; it is
  not the software-visible rectangle selector ids or landscape remap logic.
