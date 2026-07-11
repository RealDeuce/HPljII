# IC30/IC13 Rectangle Graphics Flow

This report tracks the PCL rectangle/rule command edge into the
already-modeled page-record rule-list producer. Names remain provisional where
exact pattern rendering is still open.

## Command Handlers

| Command | Handler | Firmware behavior | Reproduction consequence |
| --- | ---: | --- | --- |
| `ESC *c#A` | `0x10e68` | requires an explicit positive integer dot width, stores it as packed word `0x78316a`, otherwise clears width | dot width state is integer pixels before clipping |
| `ESC *c#B` | `0x10e22` | requires an explicit positive integer dot height, stores it as packed word `0x783166`, otherwise clears height | dot height state is integer pixels before clipping |
| `ESC *c#H` | `0x10a40` | converts explicit nonnegative decipoints through five 300-dpi subunits per decipoint, rounds up to a pixel by adding eleven subunits before packed conversion, and stores `0x78316a`; missing, negative, or zero values clear width | decipoint width is rounded up before the fill command sees the integer word |
| `ESC *c#V` | `0x10ae0` | same decipoint conversion as width and stores `0x783166` | decipoint height is rounded up before clipping/queuing |
| `ESC *c#G` | `0x10dce` | stores absolute nonzero area-fill id in `0x78316e`; missing or zero clears it | `ESC *c2P` and `ESC *c3P` use this id as their selector input |
| `ESC *c#P` | `0x10898` | maps fill mode `0`/missing to selector `7`; mode `2` maps area-fill percentages through threshold selectors `0..7`; mode `3` maps pattern ids `1..6` to selectors `8..13`, with portrait/landscape remaps for ids `1..4`; if width/height are nonzero, calls `0x10b80` | fill command validates selector, clips the rectangle to page extents, and queues a rule-list object through `0x13386` |

## Queue Path

- `0x10b80` rejects rectangles starting beyond the printable extents, clips
  negative starts and overlong width/height, handles landscape coordinate
  swapping, ensures a page root through `0x10084`, then queues source record
  `0x782a88` through `0x13386`.
- If `0x13386` reports no room, `0x10d22..0x10d3e` sets page-root flag bit
  `root+0x15.0`, finalizes the current root through `0xff1e`, ensures a fresh
  root through `0x10084`, and retries the same source record. This is the
  rectangle/rule counterpart to the text queue retry paths.
- `0x13386` runs `0x134d6` to compute bucket word `0x782a7c` and compact rule
  key `0x782a7e` from source x/y plus `0x782dc0`; `0x133aa` stores the low
  bucket byte at object `+4` and inserts a 14-byte object under page-root
  `+0x24`. The executable addressed fixture now allocates these objects
  through `0x1381c`, verifies the `+0` next links, and pins sorted insertion
  for earlier, later, and equal bucket bytes.
- `0x1edc6` later copies page-root `+0x24` to render-record `+0x1c`, ORs
  object byte `+5` with `0x10`, and copies height word `+0x0a` to `+0x0c`
  before `0x1f446` dispatch.
- `0x1f446` walks the bridged rule list for each five-bucket render band.
  Selector `7` dispatches to solid helper `0x1f596`, which decodes the packed
  key through `0x1f626`/`$a001` sub-byte positioning and writes full `0xffff`
  words plus a trailing mask from table `0x308be`; the other selectors
  dispatch to pattern helper `0x1f4e0`, which uses the pointer table at
  `0x2fefe` and the same mask helper `0x1f6ee`.

## State Reference Scan

| Address | Current role | Longword literal references |
| ---: | --- | --- |
| `0x00782c8a` | current horizontal cursor word used as rectangle start x | `0x00d15c`, `0x00d19a`, `0x00d1a2`, `0x00d228`, `0x00d24a`, `0x00d2d4`, `0x00d310`, `0x00d34c`, `0x00d3c4`, `0x00d51e`, `0x00d56c`, `0x00d5ee`, ... (110 total) |
| `0x00782c8e` | current vertical cursor word used as rectangle start y | `0x00ca6e`, `0x00cbb8`, `0x00d364`, `0x00d3ec`, `0x00d402`, `0x00d4c2`, `0x00d7d0`, `0x00d86c`, `0x00d882`, `0x00d912`, `0x00ed94`, `0x00f0c4`, ... (83 total) |
| `0x00782db6` | vertical page extent used to reject/clip rectangle height | `0x00d3a0`, `0x00d4e8`, `0x00d810`, `0x00d938`, `0x00f898`, `0x00f8b6`, `0x00fbda`, `0x00fbf6`, `0x010bd8`, `0x01279a`, `0x01ca4c`, `0x01d0dc`, ... (29 total) |
| `0x00782db8` | horizontal page extent used to reject/clip rectangle width | `0x00d26a`, `0x00d334`, `0x00d38a`, `0x00d69c`, `0x00d7a4`, `0x00d7f8`, `0x00e9c6`, `0x00e9e4`, `0x00ec70`, `0x00ec80`, `0x00f25e`, `0x00f4f8`, ... (29 total) |
| `0x00782dc0` | horizontal page/raster phase added into rectangle object key by `0x134d6` | `0x00d40c`, `0x00d88c`, `0x00f99a`, `0x00fbbe`, `0x00fdf6`, `0x010194`, `0x0130b0`, `0x0134ea`, `0x0137d2` |
| `0x00783166` | current rectangle height, written by `ESC *c#B/#V` | `0x00cdf8`, `0x0108fe`, `0x010b24`, `0x010c04`, `0x010c34`, `0x010e4c`, `0x010e5c`, `0x01e86a`, `0x01e882`, `0x01e89c`, `0x01e8ce`, `0x030fc8`, ... (15 total) |
| `0x0078316a` | current rectangle width, written by `ESC *c#A/#H` | `0x00cdf2`, `0x0108f4`, `0x010a84`, `0x010bc2`, `0x010c2c`, `0x010c80`, `0x010e92`, `0x010ea2`, `0x01e870`, `0x01e888`, `0x01e8a2`, `0x01e8d4`, ... (16 total) |
| `0x0078316e` | current area-fill id, written by `ESC *c#G` and consumed by `ESC *c#P` | `0x00cdfe`, `0x0108b6`, `0x010e16` |

## Current Reproduction Contract

- A byte-stream model must preserve rectangle width/height state across
  commands until `ESC *c#P` consumes it; reset/rebuild paths clear `0x78316a`,
  `0x783166`, and `0x78316e`.
- Dot sizes and decipoint sizes are not interchangeable at fractional
  boundaries: decipoint handlers round up with the firmware's `+11` subunit
  bias before storing the packed value.
- `tools/render_fixture_harness.py` now pins dot/decipoint size stores, `ESC
  *c#G` absolute/clear behavior, `ESC *c#P` selector mapping, a chained `ESC
  *c12a5b0P` byte stream queueing the selector-7 rule object plus a ROM
  `0x11774` dispatch trace for the same stream, portrait rule-list object
  queueing/bridge normalization, solid black selector-7 rendering through
  `0x1f446`/`0x1f596`, solid and patterned rule band-crossing continuation, a
  two-band page-row assembly for a crossing HP-pattern rule, gray selectors
  `0..6` and HP pattern selectors `8..13` through `0x1f446`/`0x1f4e0`,
  sub-byte HP pattern masks/pixels, left/right/top/bottom and landscape edge
  clipping plus off-page ignore reasons, and a parser-to-retry boundary that
  ties the same `ESC *c12a5b0P` handlers `0x10e68`/`0x10e22`/`0x10898` to the
  `0x10d22` no-room path through `0xff1e`, `0x10084`, `0x13386`, `0x1edc6`,
  and rule rendering. Remaining work is parser-produced full-page comparisons
  for these rule paths.
- The mixed `!\x1b*c12a5b0P` fixture now has an addressed allocation
variant: printable `!` queues through addressed `0x1387c`, the chained
rectangle queues through addressed `0x133aa`, and the materialized record
matches the older byte-list bridge/render output.
