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
  - `0x13386/0x133aa-modeled rectangle/rule list object and bridge
    normalization`
  - `0x1f446/0x1f596 renders solid black rectangle rule pixels`
  - `0x1f4e0 renders gray and HP pattern selector matrix`
  - `0x10b80 rectangle fill clips right/top/bottom edges and ignores
    off-page fills`
  - `0x10d22 rectangle/rule no-room retry finalizes root then retries span`
  - `rectangle parser trace feeds no-room retry path`
  - `host-fetched text plus rectangle page record feeds 0x1ed84 and 0x1ef6a`
  - `host-fetched alternate rectangle selectors feed full page records`
  - `host-fetched text rectangle and raster page record feeds 0x1ed84 and
    0x1ef6a`
  - `host-fetched text rectangle raster FF publishes rendered page record`
  - `addressed text rectangle raster FF publishes rendered page record`
  - `addressed text/rule/raster field groups reach publication and render
    entry`

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

- The live heap allocator path beneath `0x1381c` is modeled by fixtures, but
  the complete 68000 parser-to-allocator run for no-room retry has not been
  captured from live CPU memory.

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

Fixture `host-fetched text rectangle and raster page record feeds 0x1ed84 and
0x1ef6a` extends that stream with `ESC *t300R ESC *r0A ESC *b2W c3 3c`, so
the same current page record contains:

- compact text through `0xd04a` / `0x12f2e` / `0x1387c`;
- selector-7 rectangle rule through `0x10898` / `0x10b80` /
  `0x13386` / `0x133aa`;
- mode-0 raster through delayed `0x11f82` / `0x12218` / `0x105d0` /
  `0x13070` / `0x13250`.

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
- unknown: exact live 68000 heap/register continuity for the full
  parser-to-allocator path.

The alternate selector fixture classifies `0x78316e` as canonical fill state:
`0x10dce` writes it from `50g` and `2g`, and `0x10898` consumes it for `2P`
and `3P`. The selector byte in each page rule object is canonical page content
before bridge normalization and derived render content after `0x1edc6` ORs
bit `0x10` and copies height into continuation word `+0x0c`. The SHA-256 row
digests are derived/cache evidence for the composed software-visible output,
not firmware state.

Writers are the parser handlers and producers listed above, plus `0xff1e`
when fixtures `host-fetched text rectangle raster FF publishes rendered page
record` and `addressed text rectangle raster FF publishes rendered page
record` finalize the heterogeneous current page. Readers are `0x1ed84` /
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

- `0x10898..0x133aa` is documented and fixture-backed, including host-fetched
  streams and no-room retry, but a full live 68000 execution through parser,
  `0x10b80`, `0x1381c`, and real allocator memory has not been captured.
- Pattern rendering is fixture-pinned for selectors, masks, shifted rows, and
  band crossing. The initial mixed text/rule/raster/FF byte stream now provides
  a complete parser-produced page comparison with selector-7 rule output,
  mode-0 raster output, compact text, publication, and render-entry rows;
  `host-fetched alternate rectangle selectors feed full page records` adds
  page-record comparisons for gray selector `4` from `50g2P` and portrait
  pattern selector `9` from `2g3P`;
  checked-in coverage also includes font-selection streams, downloaded-glyph
  FF publication, geometry-changing publication streams, and a parser-driven
  downloaded-glyph/rule/raster page. The remaining comparison gap is broader
  physical/reference-output validation and full-page combinations for the
  other non-solid selector ids/orientations, not the software-visible
  selector-7, selector-4, or selector-9 rule objects.
