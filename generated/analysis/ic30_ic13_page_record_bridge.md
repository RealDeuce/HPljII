# IC30/IC13 Page-Record to Render-Record Bridge

Generated from focused disassembly of `0x1ed84..0x1ee9c` in the verified
firmware image. This report records the concrete field-copy contract between
queued page/control records and the render work record consumed by `0x1ef6a`
and its bucket/list dispatchers.

## Active Record Copy Entry `0x1ed84`

| Address | Instruction fact | Current meaning |
| --- | --- | --- |
| `0x1ed8c` | loads destination render record pointer from stack argument into `A5` | caller selects which render work record is being prepared |
| `0x1ed90` | loads source active page/control record from `0x780eae` into `A4` | source record is the active page/control record selected by the scheduler |
| `0x1ed96..0x1eda8` | copies source words `+0x18/+0x1a` into destination words `+0x0a/+0x0c/+0x10/+0x16` and clears destination word `+0x0e` | band/page dimensions and starting row state are initialized before object-list copying |
| `0x1edb2..0x1edb6` | calls `0x1edc6(destination, source)` | queue/list pointers and font/context slots are copied by the helper below |

## Render Band Setup `0x1ef86`

Before the bucket/list dispatchers run, `0x1ef6a` calls `0x1ef86` with the
current render record in `A6`. The helper computes `(word +0x10 + word +0x08 -
word +0x0a) / word +0x06` using unsigned word division, stores the remainder
in `0x783a22`, stores `(word +0x06 - remainder) << 4` in `0x783a20`, and
stores `long +0x00 + ((remainder << 6) * word +0x04)` in both `0x783a28` and
render-record long `+0x12`. `tools/render_fixture_harness.py` now has an
executable `0x1ef86` fixture that pins those four outputs before the `0x1efc2`
bucket-chain dispatch check.

## Render Entry Call Order `0x1ef6a`

The render entry calls `0x1ef86`, `0x1efc2`, `0x1f446`, and `0x1f756` in that
order for the current render record. The executable fixture now feeds one
synthetic render record containing compact text and encoded raster bucket
objects at `+0x18`, a selector-7 rule list at `+0x1c`, and a fixed-width list
at `+0x20`, then verifies the layer composition in that same call order.

## Queue/List Copy Helper `0x1edc6`

| Address | Instruction fact | Render-record contract |
| --- | --- | --- |
| `0x1edd6..0x1ede0` | returns immediately if source record is null | null active records produce no copied queue/list state |
| `0x1ede2` | `move.l (0x1c,A4),(0x18,A5)` | page/control bucket array root `+0x1c` becomes render-record bucket root `+0x18` |
| `0x1ede8` | `move.l (0x24,A4),(0x1c,A5)` | page/control rule/list chain `+0x24` becomes render-record list `+0x1c` for `0x1f446` |
| `0x1edee` | `move.l (0x28,A4),(0x20,A5)` | page/control second-mode/fixed-width chain `+0x28` becomes render-record list `+0x20` for `0x1f756` |
| `0x1edf4..0x1ee0e` | walks render-record `+0x1c`; ORs byte `object+5` with `0x10`; copies word `object+0x0a` to `object+0x0c` | rule/list objects are marked and receive a duplicated dimension/band word before dispatch |
| `0x1ee10..0x1ee5e` | walks render-record `+0x20`; ORs byte `object+5` with `0x10`; copies word `object+8` to `object+0x0a`; writes byte `+0x0c=1`, byte `+0x0d=8` | fixed-width/text-span-like objects are normalized to the shape expected by the fixed-width writer |
| `0x1ee60..0x1ee94` | loops `D7=0..15`, copying longwords from source `+0x2c+4*D7` to destination `+0x24+4*D7` | 16 page-root font/context slots become render-record context slots selected by compact bucket byte `+5` |

## Fixed-Width List Renderer `0x1f756`

After bucket and rule-list rendering, `0x1ef6a` calls `0x1f756` for
render-record list `+0x20`. It runs only when render word `+0x10` is on a
five-band boundary, filters objects by byte `+4 <= band+4`, skips objects
whose word `+0x0a` is non-positive, uses byte `+5 & 0x0f` as an index into
longword table `0x308de`, then calls `0x1f7b0`. The helper clears bridge flag
bit `0x10`, uses word `+6` as the packed coordinate, subtracts the available
rows from word `+0x0a`, clips the current draw count, and writes the selected
low pattern word once per row through the `0x1f626` destination helper.
`tools/render_fixture_harness.py` now has an executable `0x1f756` fixture that
renders one normalized `+0x20` object, verifies the table longword, and checks
the post-render object mutation.

## Renderer Consumers

| Render-record field | Consumer | Current role |
| --- | --- | --- |
| `+0x18` | `0x1efc2` bucket-chain dispatcher | compact text/glyph buckets from `0x12f2e` and encoded raster row objects from `0x13070` / `0x13250` |
| `+0x1c` | `0x1f446` special/rule-list dispatcher | rectangle/rule objects from `0x13386` / `0x133aa` after bridge normalization |
| `+0x20` | `0x1f756` fixed-width/rule writer | second-mode rule/text-span objects from `0x13520` / `0x136d2` after bridge normalization |
| `+0x24..+0x60` | `0x1f008` / `0x1f354` compact glyph context resolver | compact object byte `+5` low nibble selects one of the 16 copied context slots |

## Reproduction Contract

- A page-object reproduction model must preserve the three page/control record
  queues separately until the `0x1edc6` bridge copies them into render-record
  fields `+0x18`, `+0x1c`, and `+0x20`.
- The compact text/glyph path is the least transformed by the bridge: the
  bucket root pointer is copied, and the renderer then selects context slots
  copied from source `+0x2c..+0x68`.
- The rule/list and fixed-width chains are not pass-through. Their object
  bytes are normalized by `0x1edc6` before the render dispatchers see them, so
  fixtures must compare the post-bridge object shape when validating these
  paths.
- `tools/render_fixture_harness.py` now has a `0x1ed84`/`0x1edc6` fixture that
  copies source words `+0x18/+0x1a` into render-record header words
  `+0x0a/+0x0c/+0x10/+0x16`, clears render word `+0x0e`, bridges a compact
  text bucket, verifies the copied context slot can render the same glyph
  rows, pins the render-record destination offsets `+0x18/+0x1c/+0x20/+0x24`,
  pins both list-normalization side effects, pins `0x1ef86` render-band
  remainder/base-pointer setup, `0x1efc2` selected-bucket class dispatch,
  `0x1f812` segment-list rendering, `0x1f756` fixed-width list rendering, and
  the `0x1ef6a` call order over bucket/rule/fixed-width consumers, composes a
  non-overlapping compact text bucket plus selector-7 rule from the same
  bridged render record into one page band, overlays a separately bridged
  mode-0 raster row into that same band, traces simple execute/call and
  mixed-control macro execute payloads from the `0xa904` data-chain through
  parser handlers into the same page-record streams, composes a macro execute
  payload page-record layer with the same selector-7 rule and mode-0 raster
  row, and carries reset/FF/page-size/orientation `0xff1e` published records
  through `0x1ed84` and `0x1ef6a`. The remaining gap is fuller live-parser
  page-object allocation and the true heterogeneous bucket-chain/full-page
  merge.
