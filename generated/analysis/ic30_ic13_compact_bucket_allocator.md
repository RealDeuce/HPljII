# IC30/IC13 Compact Bucket Allocator

Generated from focused disassembly of `0x12f2e`, `0x1387c`, and the shared
stream allocator at `0x1381c` in the verified firmware image. This report
records how compact text/glyph objects are found, allocated, and linked under
the page-root `+0x1c` bucket array before the `0x1edc6` render-record bridge
copies that array into the renderer.

## Producer Inputs from `0x12f2e`

| Address | Instruction fact | Current meaning |
| --- | --- | --- |
| `0x12f3c..0x12f60` | reads source words `+0x12/+0x14`, stores `source_y >> 4` in `0x782a7c`, and packs y/subbyte/x pieces into a word on the stack | `0x782a7c` is the page-root bucket index; the stack word becomes the compact coordinate payload |
| `0x12f68..0x12f6e` | masks source word `+0x16` to four bits and starts selector `D5` with that value | low selector bits are the render context slot used later by compact rendering |
| `0x12f70..0x12fbe` | selects flagged or unflagged source metrics and sets selector bit `0x1000` for wide glyphs | flagged sources compare glyph-entry word `+8` against `0x80` and use word `+6` as row count; unflagged sources compare inline-record byte `+0` against `0x10` and use byte `+1` as row count; selector byte `+4` bit `0x10` chooses compact render mode 1 when width exceeds the path threshold |
| `0x12fc0..0x12fd4` | sets selector bit `0x2000` when rows exceed `0x80`; computes segment `(rows - 1) >> 7`; adds `segment * 8` to `0x782a7c` | tall glyphs are stored as multiple segment entries across bucket indices spaced by 8 |
| `0x12fd6..0x12fe0` | calls `0x1387c(selector, capacity=8, object_size=0x28)` for segmented entries | segmented compact objects have four-byte entries |
| `0x12ff4..0x12ffe` | calls `0x1387c(selector, capacity=10, object_size=0x26)` for short entries | short compact objects have three-byte entries |
| `0x1301c..0x13034` | increments object count at `+6`; writes mapped glyph byte, segment byte, and compact coord | segmented payload entry is `glyph, segment, coord_hi, coord_lo` |
| `0x1303e..0x13068` | increments object count at `+6`; writes mapped glyph byte and compact coord | short payload entry is `glyph, coord_hi, coord_lo` |

## Find-or-Allocate Helper `0x1387c`

| Address | Instruction fact | Current meaning |
| --- | --- | --- |
| `0x13884` | loads selector argument into `D5` | selector is the word written to object `+4` for compact text/glyph objects |
| `0x13888..0x1389c` | loads current page root `0x78297a`, follows root `+0x1c`, indexes by `0x782a7c * 4`, and loads the bucket head | compact text/glyph objects are chained from the page-root bucket array |
| `0x138a2..0x138b2` | compares existing object word `+4` with selector and returns it if count word `+6` is below the capacity argument at stack `+0x0e` | matching objects are reused until their entry count reaches capacity |
| `0x138d6..0x138dc` | walks `object+0` next pointers until a match or end of chain | different selector objects can coexist in the same bucket chain |
| `0x138b6..0x138ca` | calls `0x1381c(object_size)`, copies old bucket head to new object `+0`, stores new object into the bucket head, and writes selector at `+4` | new compact objects are inserted at the bucket head |

## Shared Stream Allocator `0x1381c`

| Address | Instruction fact | Current meaning |
| --- | --- | --- |
| `0x13820..0x13834` | compares requested byte count against remaining bytes `0x782a70` | uses the current 0x100-byte chunk when enough payload space remains |
| `0x13836..0x13860` | allocates a new 0x100-byte chunk via `0x1710`, links it through `0x782a72`, sets next-free pointer to chunk `+4`, and sets remaining bytes to `0xfc` | chunk first longword is the next-chunk link; the remaining 252 bytes are object storage |
| `0x13864..0x13874` | returns the old next-free pointer, advances `0x782a76`, and subtracts the requested size from `0x782a70` | compact/raster/rule objects share the same page-root stream-storage pool |

## Reproduction Contract

- A page-object model must keep `0x782a7c` as the bucket index, not as part of
  the object payload. `0x1387c` uses it to choose one entry in the page-root
  `+0x1c` bucket-head array.
- Compact object identity for reuse is the selector word at object `+4`;
  capacity is supplied by the producer (`10` for short entries, `8` for
  segmented entries) and compared against count word `+6`.
- When no reusable object exists, new compact objects are linked at the head
  of the selected bucket chain and receive selector word `+4`; payload count
  starts at zero until the producer increments it.
- The executable `0x1381c` stream-allocator fixture now pins first-chunk
  allocation, same-chunk reuse, second-chunk linking through the previous
  chunk's first longword, `0x782a70` remaining-byte accounting, `0x782a72`
  link-field movement, and `0x782a76` next-free updates. The addressed
  `0x133aa` and `0x136d2` fixtures now use the same allocator for 14-byte
  rectangle/rule entries under page-root `+0x24` and `+0x28`, pinning
  bucket-byte ordered insertion, including equal-bucket insertion after the
  existing equal entry.
- The address-aware `0x1387c` fixture now pins how that stream allocation
  becomes a bucket object: first allocation writes selector `+4` and bucket
  head `root+0x1c[0x782a7c]`, reuse returns the same object while count `+6`
  is below capacity, and a full matching object forces a new head whose
  longword `+0` points to the prior object.
- A composed addressed page-record fixture now materializes one `+0x1c`
  compact bucket, one `+0x24` rule list, and one `+0x28` fixed list by
  following the allocated objects' `+0` links, then carries those bytes
  through `0xff1e`, `0x1ed84`, and `0x1edc6` to prove the addressed stream
  objects match the existing render-record bridge contract.
- `tools/render_fixture_harness.py` now has executable `0x1387c` fixtures for
  short reuse, full-object new-head allocation, segmented tall-glyph bucket
  allocation/reuse, and printable, mixed printable/control, printable/reset,
  left/right-margin-positioned printable, horizontal/vertical
  cursor-positioned printable, horizontal/vertical-decipoint-positioned
  printable, chained cursor-positioned printable, vertical-layout-positioned
  printable, simple macro execute, and mixed-control macro execute byte
  streams that queue through page-record storage before bridging through
  `0x1edc6`; the plain `!!` path is tied to two ROM parser `0xd04a` events,
  the mixed `ESC &k1G!\r!` path is tied to ROM parser handlers `0xedf8`,
  `0xd04a`, `0xf02c`, and `0xd04a`, the margin `ESC &a1L!` and `ESC &a1M!`
  paths are tied to `0xeb58`/`0xec0c` then `0xd04a`, the cursor-position `ESC
  &a2C!`, `ESC &a72H!`, `ESC &a1R!`, `ESC &a72V!`, and `ESC &a2c+1R!` paths
  are tied to `0xf39e`/`0xf416`/`0xf560`/`0xf60a` plus lowercase-chain
  `0xf39e`/`0xf560` then `0xd04a`, the top-margin `ESC &l3E!` path is tied to
  `0xece2` then `0xd04a`, the macro execute replayed `!\r` path is tied to
  parser handlers `0xd04a` and `0xf02c`, the macro execute replayed `ESC
  &k1G!\r!` path is tied to `0xedf8`, `0xd04a`, `0xf02c`, and `0xd04a`, and
  the harness also renders a short object queued through that page-record
  allocator before bridging it through `0x1edc6`.
- The same page-record coverage now includes cursor-stack-positioned text:
  `ESC &f0S ESC &a2C ESC &f1S!` routes through `0xf75e`/`0xf39e`/`0xf75e`
  before printable `0xd04a`, proving the pop restores compact coord `0x0001`
  before queue/bridge/render.
- The same page-record coverage now includes chained margin-positioned text:
  `ESC &a6l9M!` routes lowercase-final `0xeb58` and final `0xec0c` before
  printable `0xd04a`, proving compact coord `0x0207` / pixel x `114` before
  queue/bridge/render.
- The same page-record coverage now includes LF-positioned text: `ESC
  &k2G!\n!` routes through `0xedf8`/`0xd04a`/`0xf08c`/`0xd04a`, proving LF
  mode `0x60` applies CR+LF before queueing the second glyph at compact coord
  `0x3b00`.
- The same page-record coverage now includes HT/BS-positioned text: `ESC &k0G
  HT BS !` routes through `0xedf8`/`0xf1cc`/`0xf2a8` before printable
  `0xd04a`, proving compact coord `0x0a01` / pixel x `26` before
  queue/bridge/render.
