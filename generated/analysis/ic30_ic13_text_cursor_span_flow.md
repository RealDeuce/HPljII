# IC30/IC13 Text Cursor and Span Flow

Generated from the printable-text window around `0xd140..0xd8fc` plus
absolute-call and state-literal scans of the verified firmware image. This
report narrows the text reproduction boundary after `0x1393a`: how
source-object metrics advance the text cursor, produce compact page buckets,
and update text span watermarks.

## Paired Text Paths

| Path | Entry | Precheck | Queue handoff | Span/bounds update | Current role |
| --- | ---: | ---: | ---: | ---: | --- |
| unflagged / inline | `0xd140` | `0xd28a` | `0xd3b2` | `0xd4ac` | used when source object byte `+0x10` is clear |
| flagged / built-in | `0xd550` | `0xd6bc` | `0xd824` | `0xd8fc` | used when source object byte `+0x10` is nonzero |

## Confirmed Arithmetic and Side Effects

| Step | Firmware evidence | Reproduction meaning |
| ---: | --- | --- |
| 1 | Both `0xd140` and `0xd550` call a path-specific precheck (`0xd28a` or `0xd6bc`) and store its result in `0x782a6e` | a nonzero precheck suppresses queue and span-update side effects for the current character |
| 2 | Both entries seed `D5` from current cursor `0x782c8a` and derive an advance `D4` either from the active text metrics, from the latched previous width/advance pair `0x782a5a/0x782a5c`, or from default advance `0x78315c` | horizontal cursor movement is metric-driven, with special centering/kerning behavior when `0x78318e` and `0x782a58` are active |
| 3 | When `0x782a58` is set, both entries add half of `(latched_width - current_width)` to `0x782c8a`, rounding the arithmetic right shift toward zero for odd negative deltas | repeated text can be centered against the previous character width before the main advance is applied |
| 4 | Both entries add `D4` to cursor `D5`, then if the low 16 bits are `>= 12`, subtract `12` from `D5` | text cursor coordinates use a 12-subunit fixed-point-like residue; crossing the residue boundary normalizes the whole cursor value |
| 5 | If the source has drawable content (`source+4` nonzero for `0xd550`, source word `+0x0a` nonzero for `0xd140`), the code ensures page root `0x78297a` through `0x10084` before queueing | printable text only allocates compact page objects when a drawable source record/glyph word is present |
| 6 | If `0x782a6e == 0`, `0xd140` calls `0xd3b2` and `0xd550` calls `0xd824`; each handoff writes source `+0x12/+0x14/+0x16`, marks `0x78297f + slot`, and calls `0x12f2e`, retrying via `0xff1e` / `0x10084` on allocation failure | both source-object classes converge into the same compact text bucket producer |
| 7 | `0xd3b2` handles unflagged source positioning with byte metrics at source record `+1/+2` and the context-record byte at context `+0x16`; `0xd824` handles flagged source positioning with word metrics at source record `+0/+2` | the two paths use different source-record layouts before producing the same `0x12f2e` source coordinate fields |
| 8 | Both handoffs account for negative left overflow by returning a fixed-point correction in `D7`; the caller adds that value back into the local cursor candidate before repeating limit checks | clipped-left text changes the queued source coordinate and the cursor update together |
| 9 | After final cursor clamping, both entries write `0x782c8a = D5` and clear `0x782a58` | the text cursor is committed only after queue/limit handling has stabilized |
| 10 | If `0x782a6e == 0`, `0xd140` calls `0xd4ac((source+0))` and `0xd550` calls `0xd8fc((source+0))`; both check the current y coordinate against context-record lower-bound/height fields and `0x782db6`, update `0x78318a` and `0x783188`, and flush through `0x12714` / `0x126e2` when current x is below `0x783186` | span/bounds state is maintained from the selected context record after successful printable text placement and can force pending span emission |

## Source Field Use

| Field | Unflagged path | Flagged path |
| ---: | --- | --- |
| `+0x00` | context pointer; `0xd3b2` reads context byte `+0x16` | context pointer; `0xd824` does not test context byte `+0x16` |
| `+0x04` | inline/fixed source record pointer used by `0xd140`, `0xd28a`, and `0xd3b2` | concrete built-in glyph-entry pointer used by `0xd550`, `0xd6bc`, and `0xd824` |
| `+0x08` | signed horizontal offset/advance contribution used by `0xd3b2` | signed horizontal offset/advance contribution used by `0xd824` |
| `+0x0a/+0x0b` | glyph index word/byte; word zero suppresses page-root allocation in `0xd140` | glyph index word/byte; copied by `0x12f2e` after `0xd824` |
| `+0x12` | written by `0xd3b2` as the x-like source coordinate | written by `0xd824` as the x-like source coordinate |
| `+0x14` | written by `0xd3b2` as the y-like source coordinate | written by `0xd824` as the y-like source coordinate |
| `+0x16` | written by `0xd3b2` as context slot for `0x12f2e` | written by `0xd824` as context slot for `0x12f2e` |

## Context Record Field Use

The span-update calls pass `(source+0)`, not the source object itself, so
these fields belong to the selected context record.

| Context field | Reader | Current interpretation |
| ---: | --- | --- |
| `+0x16` | `0xd8fc` | y-like lower bound for flagged/built-in span update |
| `+0x18` | `0xd8fc` | height/extent contribution checked against page extent `0x782db6` |
| `+0x1a` | `0xd8fc` | optional offset subtracted from y watermark when `0x783185` is set |
| `+0x2b` | `0xd4ac` | optional offset added to y watermark when `0x783185` is set and nonzero |
| `+0x2c` | `0xd4ac` | y-like lower bound for unflagged/inline span update |
| `+0x2d` | `0xd4ac` | height/extent contribution checked against page extent `0x782db6` |

## Absolute JSR Call-Site Scan

This scan finds `JSR absolute long` opcodes (`4eb9`) that target the named
routines. It does not include PC-relative calls.

| Target | Role | Absolute JSR references |
| ---: | --- | --- |
| `0x00d140` | unflagged/inline text advance entry | `0x00d0d2`, `0x00d130` |
| `0x00d28a` | unflagged text bounds precheck | `0x00d14e` |
| `0x00d3b2` | unflagged positioned source queue handoff | `0x00d23e` |
| `0x00d4ac` | unflagged text span/bounds update | `0x00d25e`, `0x00ecd2`, `0x00f29e`, `0x00f33c`, `0x00f552` |
| `0x00d550` | flagged/built-in text advance entry | `0x00d0c6`, `0x00d124` |
| `0x00d6bc` | flagged text bounds precheck | `0x00d55e` |
| `0x00d824` | flagged positioned source queue handoff | `0x00d670` |
| `0x00d8fc` | flagged text span/bounds update | `0x00d690`, `0x00ecc8`, `0x00f292`, `0x00f332`, `0x00f548` |
| `0x010510` | fixed-point compare/subtract helper | `0x00d2ec`, `0x00d75c`, `0x00ea52`, `0x00eb1a`, `0x00ebaa`, `0x00ed4c`, `0x00f206`, `0x00f2dc`, `0x00f7e4`, `0x00f834`, `0x00f850`, `0x00fe78`, ... (18 total) |
| `0x010518` | fixed-point add helper | `0x00ca64`, `0x00cbae`, `0x00d324`, `0x00d37a`, `0x00d794`, `0x00d7e8`, `0x00ea32`, `0x00ea88`, `0x00eafc`, `0x00eb48`, `0x00ec60`, `0x00ed8a`, ... (33 total) |
| `0x010550` | fixed-point metric conversion helper | `0x00c4e6`, `0x00cc2a`, `0x00cebc`, `0x00d578`, `0x00d6f2`, `0x01039c` |
| `0x00f054` | conditional page/text state recovery helper | `0x00d308`, `0x00d344`, `0x00d778`, `0x00d7b4`, `0x0125f4`, `0x012922`, `0x01e212`, `0x01e238`, `0x01e270`, `0x01e2b6`, `0x01e2cc`, `0x01e2dc`, ... (22 total) |
| `0x010084` | ensure page root | `0x00d20a`, `0x00d49a`, `0x00d63c`, `0x00d8ea`, `0x00d9ec`, `0x00da4c`, `0x00f0b6`, `0x00f10c`, `0x00f17a`, `0x00f2b0`, `0x00f576`, `0x00f6ee`, ... (25 total) |
| `0x0126e2` | post-flush text state reset/update | `0x00d536`, `0x00d980`, `0x00ebe4`, `0x00f362`, `0x00f74e`, `0x00f874`, `0x0103ca`, `0x0126da`, `0x01ca86` |
| `0x012714` | pending text span flush | `0x00d530`, `0x00d97a`, `0x00ebd8`, `0x00f35c`, `0x00f748`, `0x00f86e`, `0x01269a`, `0x01caa0` |
| `0x012f2e` | compact text/glyph bucket producer | `0x00d47a`, `0x00d8ca` |

## State References

| Absolute address | Role | Longword literal references |
| ---: | --- | --- |
| `0x0078297a` | current page-root pointer | `0x00c44a`, `0x00c50a`, `0x00c61c`, `0x00d204`, `0x00d48a`, `0x00d636`, `0x00d8da`, `0x00da68`, `0x00ff28`, `0x00ff30`, `0x00ff56`, `0x00ffa4`, ... (35 total) |
| `0x0078297e` | current page-root font slot index | `0x00c478`, `0x00ce4e`, `0x00d45c`, `0x00d46e`, `0x00d8ac`, `0x00d8be`, `0x00ffb8` |
| `0x0078297f` | page-root font slot live flags | `0x00c544`, `0x00c5f2`, `0x00d466`, `0x00d8b6`, `0x0101fe`, `0x01970a` |
| `0x00782a58` | text pending-width latch flag | `0x00d174`, `0x00d1b0`, `0x00d250`, `0x00d5b0`, `0x00d5c8`, `0x00d682`, `0x00f306`, `0x00f350` |
| `0x00782a5a` | latched previous text width | `0x00d184`, `0x00d1c4`, `0x00d5c0`, `0x00d5d8`, `0x00f2c8` |
| `0x00782a5c` | latched previous text advance | `0x00d17c`, `0x00d1b8`, `0x00d5b8`, `0x00d5d0` |
| `0x00782a6e` | text precheck result word | `0x00d156`, `0x00d236`, `0x00d256`, `0x00d566`, `0x00d668`, `0x00d688` |
| `0x00782c8a` | current text cursor x-like coordinate | `0x00d15c`, `0x00d19a`, `0x00d1a2`, `0x00d228`, `0x00d24a`, `0x00d2d4`, `0x00d310`, `0x00d34c`, `0x00d3c4`, `0x00d51e`, `0x00d56c`, `0x00d5ee`, ... (110 total) |
| `0x00782c8e` | current text cursor y-like coordinate | `0x00ca6e`, `0x00cbb8`, `0x00d364`, `0x00d3ec`, `0x00d402`, `0x00d4c2`, `0x00d7d0`, `0x00d86c`, `0x00d882`, `0x00d912`, `0x00ed94`, `0x00f0c4`, ... (83 total) |
| `0x00782da3` | orientation byte | `0x00ccd8`, `0x00d3e4`, `0x00d864`, `0x00e298`, `0x00e390`, `0x00e6ce`, `0x00e810`, `0x00f884`, `0x00f9be`, `0x00fa4a`, `0x010254`, `0x010268`, ... (38 total) |
| `0x00782db2` | orientation/page extent used by positioned text | `0x00d3f8`, `0x00d878`, `0x00f894`, `0x00f8bc`, `0x00f976`, `0x00fb6a`, `0x00fda2`, `0x01015e`, `0x010620`, `0x01064e`, `0x012772`, `0x0127f2` |
| `0x00782db6` | page vertical extent for text bounds | `0x00d3a0`, `0x00d4e8`, `0x00d810`, `0x00d938`, `0x00f898`, `0x00f8b6`, `0x00fbda`, `0x00fbf6`, `0x010bd8`, `0x01279a`, `0x01ca4c`, `0x01d0dc`, ... (29 total) |
| `0x00782db8` | page horizontal extent for text wrap/clip | `0x00d26a`, `0x00d334`, `0x00d38a`, `0x00d69c`, `0x00d7a4`, `0x00d7f8`, `0x00e9c6`, `0x00e9e4`, `0x00ec70`, `0x00ec80`, `0x00f25e`, `0x00f4f8`, ... (29 total) |
| `0x00782dc0` | top/left printable offset used by text queue handoff | `0x00d40c`, `0x00d88c`, `0x00f99a`, `0x00fbbe`, `0x00fdf6`, `0x010194`, `0x0130b0`, `0x0134ea`, `0x0137d2` |
| `0x00782dda` | fixed-point current line/text limit | `0x00d214`, `0x00d2e8`, `0x00d646`, `0x00d758`, `0x00e9ca`, `0x00ea00`, `0x00ea0a`, `0x00eba6`, `0x00ebfc`, `0x00ecba`, `0x00f250`, `0x00f510`, ... (13 total) |
| `0x0078315c` | default text advance | `0x00c4bc`, `0x00c4ee`, `0x00caf4`, `0x00cc14`, `0x00cc32`, `0x00ceae`, `0x00cec4`, `0x00d1aa`, `0x00d1de`, `0x00d5aa`, `0x00d610`, `0x00eb80`, ... (29 total) |
| `0x00783184` | text vertical-bounds update enable flag | `0x00ce60`, `0x00d4ba`, `0x00d90a`, `0x00e32a`, `0x00ebd2`, `0x00f356`, `0x00f742`, `0x00f868`, `0x0103be`, `0x0103c6`, `0x01175a`, `0x0126a4`, ... (15 total) |
| `0x00783185` | text descent/offset adjustment flag | `0x00ce66`, `0x00d4f2`, `0x00d942`, `0x0126d6` |
| `0x00783186` | text span low-x flush threshold | `0x00d528`, `0x00d972`, `0x00e344`, `0x012706` |
| `0x00783188` | text span high-x watermark | `0x00d540`, `0x00d54a`, `0x00d98a`, `0x00d994`, `0x00e33a`, `0x00e340`, `0x0126fc`, `0x012702` |
| `0x0078318a` | text span high-y watermark | `0x00d50e`, `0x00d518`, `0x00d958`, `0x00d962`, `0x00e34a`, `0x01270c` |
| `0x0078318e` | alternate metrics/kerning mode flag | `0x00c488`, `0x00c4c8`, `0x00cbf4`, `0x00cc20`, `0x00d16c`, `0x00d2a0`, `0x00d588`, `0x00d6e2`, `0x00f2be`, `0x010366`, `0x010392` |
| `0x00783190` | text auto-recovery/clip retry flag | `0x00ce78`, `0x00d302`, `0x00d33e`, `0x00d772`, `0x00d7ae`, `0x00eddc`, `0x00edec`, `0x01c22c`, `0x01e0dc`, `0x01e910`, `0x030f3c` |

## Current Reproduction Contract

- A faithful text model must run the active source object through the same
  paired path selected by source byte `+0x10`; feeding `0x12f2e` directly is
  only a producer-level fixture.
- The cursor `0x782c8a` is updated after path-specific metric extraction,
  fixed-point residue normalization by 12 subunits, optional left/right
  clipping correction, and queue retry handling.
- The compact text bucket payload still depends on the mapped glyph byte from
  `0x1393a`, but exact pixel placement also depends on source fields
  `+0x12/+0x14/+0x16` produced by `0xd3b2` or `0xd824` and on context-record
  span flush side effects in `0xd4ac` / `0xd8fc`.
- The active symbol-set stream fixture now carries `ESC (2U` and `ESC )0E`
  through ROM parser setup handlers `0x1201e`/`0x12008`, terminal handler
  `0x120be`, `0x1be22`, and `0xc580`, applies the resulting `LINE_PRINTER` map
  patches, and keeps the mapped-byte dependency upstream of positioning. The
  flagged `0xd824` positioning path, including the negative-left overflow
  branch, has executable queue/render fixtures in
  `tools/render_fixture_harness.py`, and printable stream fixtures now carry
  host byte `0x21` through `0x1393a`, `0xd824`, the simple `0xd550`
  default-advance branch for a second byte, `0x12f2e`, and rendering. The
  initialized `LINE_PRINTER` HMI case renders through the same path and proves
  compact coord `0x0202` as `$a001 = 0x12` / pixel x `34`; the mixed `ESC
  &k1G!\r!` case proves CR+LF repositioning before the second printable byte,
  exposes full-byte shifted blank-row clearing, and now has a parser-traced
  page-record allocator/bridge variant for the same byte stream; `ESC &a1L!`
  ties the left-margin parser handler to a shifted compact text object at
  coord `0x0801`; `ESC &a2C!` and `ESC &a1R!` tie cursor-position parser
  handlers to shifted compact text objects at coords `0x0a02` and `0x1001`;
  `ESC &l3E!` ties the top-margin parser handler to a vertically shifted
  compact text object at coord `0x9001`; the mixed `!\x1bE` case proves reset
  publication/clear state after queued text and now has a page-record
  allocator/bridge/publication variant for the pre-reset object. A `0x1387c`
  fixture queues short and segmented compact buckets into page-record shape,
  and a `0x1edc6` fixture bridges that compact bucket into render-record
  shape, pins rule/fixed-list normalization, and now includes producer-shaped
  `0x13386`/`0x136d2` rule-list objects. The `0xd3b2` fixtures now cover both
  unflagged positioning branches, a selected inline/downloaded map/source path
  through `0x14e24`/`0x14eb6` -> `0x1393a`, `0x168dc`/`0x16942` font
  payload-reader copying and continuation, `0x172c0` current-record scanning,
  `0x16c14` replacement/free-slot/no-slot bookkeeping, `0x170be`
  payload-record lookup, `0x17108`/`0x17150` current-record mark/unmark count
  transfer, `0x15a56`/`0x16df6` font-id/control dispatch, `0x16fae`
  validation-table and symbol-byte staging, `0x17362` setup-type handling,
  `0x17026` allocation-size/header staging, `0x1719c` sparse header
  initialization, synthetic inline/downloaded `0x12f2e`
  short/page-record/wide/segmented/combined payloads, type-2 payload-backed
  selected inline `0x1f0d2` wide and `0x1f1f0` segmented render rows, a
  selected-memory `0x1f264` segmented-wide isolation row, an `ESC
  *c4660d37e5F` parser/current-state boundary check feeding font install
  state, an `ESC )s0W` parser/route boundary check for `0x15d0a`, and an `ESC
  )s2193W` parser/object boundary check that reaches the `0x16498`
  downloaded-pointer `0x1f264` segmented-wide row. Remaining work is to use
  fuller parser-produced source/page objects and name the coordinate axes by
  comparing orientation, CR/LF/FF, and raster placement behavior.
- The right-margin stream `ESC &a1M!` now proves `0xec0c` can move the
  horizontal cursor through the margin limit path and still feed printable
  `0xd04a` into page-record output at compact coord `0x0a02`.
- The chained-margin stream `ESC &a6l9M!` now proves lowercase-final `0xeb58`
  can preserve parser mode for `0xec0c` and still feed printable `0xd04a` into
  page-record output at compact coord `0x0207` / pixel x `114`.
- The LF stream `ESC &k2G!\n!` now proves direct-control handler `0xf08c`
  consumes line-termination mode `0x60`, applies CR+LF movement, and feeds the
  next printable `0xd04a` into page-record output at compact coord `0x3b00`.
- The HT/BS stream `ESC &k0G HT BS !` now proves direct-control handlers
  `0xf1cc` and `0xf2a8` can update the cursor/span state before printable
  `0xd04a` feeds page-record output at compact coord `0x0a01` / pixel x `26`.
- The horizontal-decipoint stream `ESC &a72H!` now proves `0xf416` can convert
  decipoints through the horizontal cursor path and feed printable `0xd04a`
  into page-record output at compact coord `0x0402`.
- The vertical-decipoint stream `ESC &a72V!` now proves `0xf60a` can convert
  decipoints through the vertical cursor path and feed printable `0xd04a` into
  page-record output at compact coord `0x9001` / bucket `0`.
- The chained cursor-position stream `ESC &a2c+1R!` now proves lowercase-final
  horizontal positioning can keep parser mode `12` active for relative
  vertical positioning and still feed printable `0xd04a` into page-record
  output at compact coord `0x1a02` / bucket `3`.
- The cursor-stack stream `ESC &f0S ESC &a2C ESC &f1S!` now proves the
  `0xf75e` push/pop path can bracket a cursor-position command and still feed
  printable `0xd04a` into page-record output at the restored compact coord
  `0x0001`.
