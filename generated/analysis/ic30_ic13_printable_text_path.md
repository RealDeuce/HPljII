# IC30/IC13 Printable Text Path

Generated from instruction windows around `0x11774`, `0xda9a`, and `0xd04a`,
plus absolute-call and state-literal scans of the verified firmware image.
This report tracks how a normal host printable byte reaches the text
source-object builder and, for the flagged built-in path, the compact
page-object producer.

## Confirmed Host-Byte Route

| Step | Firmware evidence | Meaning for reproduction |
| ---: | --- | --- |
| 1 | `0x11774` initializes its byte-source pointer to `0xda9a`, then repeatedly calls it at `0x117d2` and saves the returned byte in `D5` | the normal PCL parser works from bytes fetched through the `0xda9a` wrapper |
| 2 | `0xda9a` calls raw byte fetch `0xa904`; if the byte is not ESC (`0x1b`), it returns it directly in `D7` | ordinary printable bytes flow from the host interface to the parser without command-token decoding |
| 3 | if `0xda9a` sees ESC, it fetches the following byte; `ESC ? 0x11` is skipped, otherwise the following byte is echoed/recorded through `0x9ec0` and `D7` is forced back to `0x1b` | command parsing begins from an ESC token, while printable data remains a single returned byte |
| 4 | in parser state `0x782999 == 0`, if the command-dispatch table does not claim the byte and alternate/data mode `0x782c18` is clear, the normal printable branch calls `0xd04a` at `0x11880` | unescaped text bytes in the normal parser mode enter the printable text routine |
| 5 | the high-character/symbol path at `0x118d6..0x11900` also calls `0xd04a` when the selected context flag byte at `0x782eeb + 0x10*0x782f06` equals `1` | some non-ASCII/active-symbol bytes can still route through the same printable text builder |
| 6 | `0xd04a` uses scratch text source object `0x782d7e`; for bytes above `0xff` it calls `0xd99a` and falls back to `0x7f` on failure | the source-object entry always receives a bounded character code |
| 7 | for bytes above `0x7f`, if both high-character flags `0x783132` and `0x783133` are clear, `0xd04a` masks the byte to 7 bits; on the primary map it wraps the operation with `0xc6b8` / `0xc68a` | high-bit input can be normalized before character-map lookup, depending on active symbol/font state |
| 8 | `0xd04a` calls `0x1393a(host_byte, 0x782d7e)` at `0xd0ae` | this is the live parser path into the previously documented host-byte to glyph-index source-object builder |
| 9 | after `0x1393a`, `0xd04a` tests source byte `+0x10`; zero branches to `0xd140`, nonzero branches to `0xd550`; both paths clear `0x782a6d` before return | source-object context flags select the following text metrics/queue path |
| 10 | `0xd550` calls `0xd6bc`, updates cursor arithmetic, ensures a page root through `0x10084` when source `+4` is nonzero, and when `0x782a6e == 0` calls `0xd824` at `0xd66e` | the flagged/built-in path has a confirmed pre-advance compact page-object handoff |
| 11 | `0xd824` writes source words `+0x12` and `+0x14` from current cursor/page geometry, writes source word `+0x16 = byte[0x78297e]`, marks `0x78297f + slot`, and calls `0x12f2e` at `0xd47a`; on allocation failure it marks page-root `+0x15.0`, calls `0xff1e` and `0x10084`, then retries | a live printable source object can become the same compact text/glyph bucket object consumed by the renderer |
| 12 | after cursor update, `0xd550` calls `0xd8fc((source+0))` at `0xd690` when `0x782a6e == 0`; `0xd8fc` checks context fields `+0x16/+0x18/+0x1a` against current y, page extent `0x782db6`, and span watermarks `0x783186/0x783188/0x78318a`, flushing through `0x12714` / `0x126e2` if the current x falls below the low threshold | the flagged printable path queues through `0xd824` and then updates text span/bounds state through the selected context record |
| 13 | the fixed-space helper `0xd0f0` calls `0x1393a(0x20, 0x782d7e)`; if the source flag is nonzero it clears source `+4` before entering `0xd550`, otherwise it uses `0xd140` | firmware has a space-specific source-object path that shares the same branch structure but suppresses the built-in glyph-entry pointer in one case |

## Source Object Fields Touched by the Live Path

| Field | Writer | Current interpretation |
| ---: | --- | --- |
| `+0x00` | `0x1393a` | selected current-font context longword |
| `+0x04` | `0x1393a`, `0xd0f0` | built-in glyph-entry pointer or inline fixed-record pointer; `0xd0f0` can clear it before `0xd550` |
| `+0x0a/+0x0b` | `0x1393a` | mapped compact glyph index word/low byte copied later by `0x12f2e` |
| `+0x10` | `0x1393a` | context flag byte tested by `0xd04a` to select `0xd140` or `0xd550` |
| `+0x12` | `0xd824` | x-like positioned source coordinate used by `0x12f2e` |
| `+0x14` | `0xd824` | y-like positioned source coordinate used by `0x12f2e` |
| `+0x16` | `0xd824` | page-root/render context slot index copied from `0x78297e` and consumed by `0x12f2e`; this is distinct from context record `+0x16` read by `0xd8fc` |

## Context Record Fields Touched by Span Updates

| Field | Reader | Current interpretation |
| ---: | --- | --- |
| `+0x16` | `0xd8fc` | y-like lower bound for flagged/built-in span update |
| `+0x18` | `0xd8fc` | height/extent contribution checked against page extent `0x782db6` |
| `+0x1a` | `0xd8fc` | optional offset subtracted from the y watermark when `0x783185` is set |
| `+0x2b` | `0xd4ac` | optional offset added to the y watermark when `0x783185` is set and nonzero |
| `+0x2c` | `0xd4ac` | y-like lower bound for unflagged/inline span update |
| `+0x2d` | `0xd4ac` | height/extent contribution checked against page extent `0x782db6` |

## Absolute JSR Call-Site Scan

This scan finds `JSR absolute long` opcodes (`4eb9`) that target the named
routines. It does not include PC-relative calls.

| Target | Role | Absolute JSR references |
| ---: | --- | --- |
| `0x00a904` | raw host byte fetch | `0x00da9a`, `0x00daa6`, `0x00dab2`, `0x00dace`, `0x00dada`, `0x012142`, `0x012152`, `0x0124bc`, `0x0124cc`, `0x012582`, `0x012592`, `0x0138fa`, ... (19 total) |
| `0x00da9a` | normal parser byte fetch / ESC wrapper | `0x0117d2`, `0x011bc2`, `0x011be2`, `0x011c8e`, `0x0122da`, `0x012630` |
| `0x011774` | main parser loop | `0x00ff94`, `0x01176c` |
| `0x00d04a` | printable text entry | `0x0105a6`, `0x0105c4`, `0x011880`, `0x011900`, `0x012100`, `0x0121a8`, `0x01252c`, `0x0125e6`, `0x01cd1c`, `0x01cd2a`, `0x01cd3a`, `0x01cd50`, ... (60 total) |
| `0x01393a` | host byte to text source object | `0x00d0ae`, `0x00d104` |
| `0x00d140` | flag-zero text advance/metrics path | `0x00d0d2`, `0x00d130` |
| `0x00d550` | built-in/flagged text advance and queue path | `0x00d0c6`, `0x00d124` |
| `0x00d824` | positioned source object queue handoff | `0x00d670` |
| `0x00d8fc` | post-advance context span/bounds update path | `0x00d690`, `0x00ecc8`, `0x00f292`, `0x00f332`, `0x00f548` |
| `0x012f2e` | compact text/glyph bucket producer | `0x00d47a`, `0x00d8ca` |

## State References

| Absolute address | Role | Longword literal references |
| ---: | --- | --- |
| `0x00782999` | main parser mode/state byte | `0x01177e`, `0x01181c`, `0x01184c`, `0x011860`, `0x01188e`, `0x0118a2`, `0x0118c4`, `0x011942`, `0x011952`, `0x011978`, `0x011982`, `0x0119b4`, ... (21 total) |
| `0x00782c18` | alternate/data parser mode flag | `0x00cc88`, `0x00d9ac`, `0x00dd66`, `0x00dd96`, `0x00ddb0`, `0x00ddfe`, `0x00de38`, `0x00e16c`, `0x011830`, `0x011842`, `0x0118ce`, `0x011934`, ... (15 total) |
| `0x00782d7e` | printable text source-object scratch buffer | `0x00d058`, `0x00d0f6` |
| `0x00782f06` | primary/secondary text-map selector | `0x00c5dc`, `0x00c600`, `0x00c698`, `0x00c6aa`, `0x00c6c6`, `0x00c6de`, `0x00cbe4`, `0x00d094`, `0x00e2ae`, `0x00e2d0`, `0x00e528`, `0x00e54a`, ... (42 total) |
| `0x00783132` | primary high-character/symbol-set flag | `0x00d07e`, `0x012498`, `0x012562`, `0x0139a4`, `0x014d3c`, `0x014d56`, `0x014d78`, `0x014fbe`, `0x01cf56`, `0x01d88a`, `0x01da94`, `0x01dd14` |
| `0x00783133` | secondary high-character/symbol-set flag | `0x00d086`, `0x0124a0`, `0x01256a`, `0x0139c4`, `0x014d44`, `0x014d60`, `0x014d82` |
| `0x00782a6d` | printable text pending/spacing flag cleared by `0xd04a` | `0x00ca3a`, `0x00cb84`, `0x00ce48`, `0x00d0e4`, `0x00d138`, `0x00ebc0`, `0x00ed60`, `0x00f084`, `0x00f0e8`, `0x00f11c`, `0x00f16e`, `0x00f1c4`, ... (16 total) |
| `0x00782a6e` | text clipping/queue precheck result word | `0x00d156`, `0x00d236`, `0x00d256`, `0x00d566`, `0x00d668`, `0x00d688` |
| `0x00782c8a` | current text cursor x-like coordinate | `0x00d15c`, `0x00d19a`, `0x00d1a2`, `0x00d228`, `0x00d24a`, `0x00d2d4`, `0x00d310`, `0x00d34c`, `0x00d3c4`, `0x00d51e`, `0x00d56c`, `0x00d5ee`, ... (110 total) |
| `0x00782c8e` | current text cursor y-like coordinate | `0x00ca6e`, `0x00cbb8`, `0x00d364`, `0x00d3ec`, `0x00d402`, `0x00d4c2`, `0x00d7d0`, `0x00d86c`, `0x00d882`, `0x00d912`, `0x00ed94`, `0x00f0c4`, ... (83 total) |
| `0x00783184` | text vertical-bounds update enable flag | `0x00ce60`, `0x00d4ba`, `0x00d90a`, `0x00e32a`, `0x00ebd2`, `0x00f356`, `0x00f742`, `0x00f868`, `0x0103be`, `0x0103c6`, `0x01175a`, `0x0126a4`, ... (15 total) |
| `0x00783185` | text descent/offset adjustment flag | `0x00ce66`, `0x00d4f2`, `0x00d942`, `0x0126d6` |
| `0x00783186` | text span low-x flush threshold | `0x00d528`, `0x00d972`, `0x00e344`, `0x012706` |
| `0x00783188` | text span high-x watermark | `0x00d540`, `0x00d54a`, `0x00d98a`, `0x00d994`, `0x00e33a`, `0x00e340`, `0x0126fc`, `0x012702` |
| `0x0078318a` | text span high-y watermark | `0x00d50e`, `0x00d518`, `0x00d958`, `0x00d962`, `0x00e34a`, `0x01270c` |
| `0x0078297a` | current page-root pointer | `0x00c44a`, `0x00c50a`, `0x00c61c`, `0x00d204`, `0x00d48a`, `0x00d636`, `0x00d8da`, `0x00da68`, `0x00ff28`, `0x00ff30`, `0x00ff56`, `0x00ffa4`, ... (35 total) |
| `0x0078297e` | current page-root font slot index | `0x00c478`, `0x00ce4e`, `0x00d45c`, `0x00d46e`, `0x00d8ac`, `0x00d8be`, `0x00ffb8` |
| `0x0078297f` | page-root font slot live flags | `0x00c544`, `0x00c5f2`, `0x00d466`, `0x00d8b6`, `0x0101fe`, `0x01970a` |

## Current Reproduction Contract

- A normal printable host byte reaches `0x1393a` through `0xa904` -> `0xda9a`
  -> `0x11774` -> `0xd04a` when parser state `0x782999` is zero and
  alternate/data parser mode `0x782c18` is clear.
- The live parser path uses the same mapped glyph byte and context fields
  documented in `ic30_ic13_text_glyph_index_flow.md`; the symbol-set stream
  fixture now proves `ESC (2U`/`ESC )0E` route through ROM parser setup
  handlers `0x1201e`/`0x12008` and terminal handler `0x120be`, then update
  active primary/secondary words before `0x14f16` patches the `LINE_PRINTER`
  map; the next byte-to-pixel model must therefore drive `0xd04a`/`0x1393a`,
  not feed renderer glyph bytes directly from the host stream.
- The paired cursor/queue/span behavior after `0x1393a` is detailed in
  `ic30_ic13_text_cursor_span_flow.md`; `tools/render_fixture_harness.py` now
  has one-byte and two-byte normal printable stream fixtures for `0x21` ->
  glyph `0x20` through `0xd824`, the simple `0xd550` default-advance branch,
  `0x12f2e`, and rendering. It also renders the initialized `LINE_PRINTER` HMI
  case, where `0x10550(0x00480000)` produces advance `0x00120000` and the
  second glyph compact coord `0x0202` decodes to `$a001 = 0x12` / pixel x
  `34`. The plain `!!` stream now has a ROM-parser trace through two `0xd04a`
  printable events tied to a page-record variant that allocates/reuses the
  compact object through `0x1387c` and bridges it through `0x1edc6`. The mixed
  `ESC &k1G!\r!` fixture proves that line-termination mode is applied before
  the second printable byte is positioned, queueing it at coord `0x3b00` after
  CR+LF; the same stream now has a ROM-parser trace through `0xedf8`,
  `0xd04a`, `0xf02c`, and `0xd04a` tied to a page-record variant that
  allocates/reuses the compact object through `0x1387c` and bridges it through
  `0x1edc6`; `ESC &a1L!` now ties margin handler `0xeb58` to page-record
  queueing and renders the shifted glyph at compact coord `0x0801`; `ESC
  &a2C!` and `ESC &a1R!` tie cursor-position handlers `0xf39e` and `0xf560` to
  page-record queueing and render shifted glyphs at compact coords `0x0a02`
  and `0x1001`; `ESC &l3E!` ties top-margin handler `0xece2` to page-record
  queueing and renders the vertically shifted glyph at compact coord `0x9001`
  in bucket `6`; the mixed `!\x1bE` fixture proves reset publication/clear
  state after queued text and has a page-record allocator/bridge/publication
  variant for the pre-reset object. The `0x1387c` allocator fixture now queues
  a short compact object into page-record bucket-array shape and covers the
  segmented tall-glyph page-record bucket sequence, and the `0x1edc6` bridge
  fixture proves how that compact bucket and context slot are copied into the
  render record. The remaining integration gap is to replace fixture-only
  state with fuller parser-allocated page roots before replacing the current
  producer-modeled text bucket fixtures.
- `ESC &a1M!` now ties right-margin handler `0xec0c` to page-record queueing
  and proves right-margin cursor movement feeds the next printable `0xd04a` at
  compact coord `0x0a02`.
- `ESC &a6l9M!` now ties lowercase-final margin chaining to page-record
  queueing: handler `0xeb58` leaves parser mode `12` active for `0xec0c`, and
  the next printable `0xd04a` lands at compact coord `0x0207` / pixel x `114`.
- `ESC &k2G!\n!` now ties LF handler `0xf08c` to page-record queueing:
  line-termination mode `0x60` causes CR+LF movement before the second
  printable `0xd04a`, which lands at compact coord `0x3b00`.
- `ESC &k0G HT BS !` now ties direct HT/BS handlers to page-record queueing:
  `0xedf8` clears line termination, HT handler `0xf1cc` moves the cursor to x
  `21`, BS handler `0xf2a8` backs it up to x `20`, and printable `0xd04a`
  lands at compact coord `0x0a01` / pixel x `26`.
- `ESC &a72H!` now ties horizontal-decipoint handler `0xf416` to page-record
  queueing and proves decipoint positioning feeds the next printable `0xd04a`
  at compact coord `0x0402`.
- `ESC &a72V!` now ties vertical-decipoint handler `0xf60a` to page-record
  queueing and proves decipoint positioning feeds the next printable `0xd04a`
  at compact coord `0x9001` / bucket `0`.
- `ESC &a2c+1R!` now ties lowercase-final cursor-position chaining to
  page-record queueing: handler `0xf39e` leaves parser mode `12` active for
  relative `0xf560`, and the next printable `0xd04a` lands at compact coord
  `0x1a02` / bucket `3`.
- `ESC &f0S ESC &a2C ESC &f1S!` now ties the cursor-stack handler path to
  page-record queueing: the middle cursor move is undone by `0xf75e` pop
  before printable `0xd04a`, so the bridged glyph renders at restored-origin
  compact coord `0x0001`.
