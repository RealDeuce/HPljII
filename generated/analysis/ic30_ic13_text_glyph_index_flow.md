# IC30/IC13 Text Glyph-Index Flow

Generated from instruction windows around `0x1393a`, `0x12f2e`, and the
font-map initializers, plus byte scans of the verified firmware image. This
report tracks the byte that starts each compact text payload entry and becomes
the `D1` glyph index consumed by renderer helper `0x1f354`.

## Confirmed Flow

| Step | Firmware evidence | Meaning for reproduction |
| ---: | --- | --- |
| 1 | `0x14c64` dispatches selected font activation through `0x14d9c` for bit-30 offset-table resources, or `0x14e24` for bit-30-clear fixed-record resources, then `0x14f16` and `0x1440c` | selected font changes rebuild one of the 256-byte character-to-glyph maps before text is queued |
| 2 | `0x14d9c` chooses `0x782f32` or `0x783032` from `0x7828de`, reads selected record words `+0x0e` and `+0x10`, zero-fills before/after that range, and writes incrementing bytes through the range | built-in records get a base map where host character `first_char+n` maps to glyph index `n` before symbol-set patching |
| 3 | `0x14e24` clears/map-fills the same 256-byte table through `0x14eb6`, which validates fixed records at `context_base+0x40+8*glyph` | bit-30-clear fixed-record resources use the same map bytes, but only for glyph slots that have valid records |
| 4 | `0x14f16` applies symbol-set `0x0115` (`8U`, HP Roman-8) handling from `0x783144`/`0x783146`: copy upper 0x80 down for `0x0005` (`0E`, HP Roman Extension), leave lower half for `0x0015` (`0U`, ISO 6 ASCII), or apply named byte-pair patch tables from `0x14fce` | symbol-set aliases are not a renderer concern; they alter the map byte before text object creation |
| 5 | `0x1393a` selects map/context pair from `0x782f06`: primary `0x782f32` + `0x782ee6`, or secondary `0x783032` + `0x782ef6`; then reads `D6 = byte[map + original_char]` | original host character code is converted to a compact glyph index at text-object build time |
| 6 | `0x1393a` stores the mapped byte as word at text object `+0x0a`, copies the current context longword to text object `+0`, and copies the context flag byte to text object `+0x10` | text object byte `+0x0b` is the low byte of the mapped glyph index, and the object carries the selected font resource context |
| 7 | if the context flag byte is nonzero, `0x1393a` range-checks the original character and resolves text object `+4` through the same offset-table formula used by `0x1f354`: base + word `+8`, long table entry indexed by mapped byte, then add base | built-in text objects already point at the concrete resource glyph entry for metrics, proving the mapped byte indexes the same table used by the renderer |
| 8 | if the context flag byte is zero, `0x1393a` sets text object `+4 = context_base + 0x40 + 8*mapped_byte` | inline/downloaded text objects use the fixed-record layout later handled by `0x1f354` when bit 30 is clear |
| 9 | the paired queue handoffs `0xd3b2` / `0xd824` fill source positioning fields `+0x12`, `+0x14`, `+0x16`, mark the selected font slot live, then call `0x12f2e`; the paired span updates `0xd4ac` / `0xd8fc` operate on the selected context record afterward | positioned text source objects are converted into compact page-bucket objects, then text span/bounds state is updated separately |
| 10 | `0x12f2e` appends source byte `+0x0b` as the first byte of every compact payload entry at `0x1302a` and `0x1304e` | compact payload entry byte 0 is the glyph index byte produced by the character map |
| 11 | compact renderers `0x1f034`, `0x1f0d2`, `0x1f1f0`, and `0x1f264` call `0x1f354` with that byte in `D1` after loading a render-record context slot into `0x783a2c` | renderer glyph selection is fully keyed by `(selected context longword, mapped glyph byte)` |

## Absolute JSR Call-Site Scan

This scan finds `JSR absolute long` opcodes (`4eb9`) that target the named
routines. It does not include PC-relative calls.

| Target | Role | Absolute JSR references |
| ---: | --- | --- |
| `0x00d4ac` | built-in text metrics/span update | `0x00d25e`, `0x00ecd2`, `0x00f29e`, `0x00f33c`, `0x00f552` |
| `0x00d824` | text source object positioning and queue handoff | `0x00d670` |
| `0x00d8fc` | alternate text source object queue handoff | `0x00d690`, `0x00ecc8`, `0x00f292`, `0x00f332`, `0x00f548` |
| `0x012f2e` | compact text/glyph bucket producer | `0x00d47a`, `0x00d8ca` |
| `0x01393a` | character-code to glyph-index capture | `0x00d0ae`, `0x00d104` |
| `0x014d9c` | built-in range map initializer | `0x014d64` |
| `0x014e24` | inline/downloaded validity map initializer | `0x014d86` |
| `0x014eb6` | inline/downloaded glyph-validity probe | `0x014e48`, `0x014e92` |
| `0x014f16` | symbol-set map patcher | `0x014d8c` |
| `0x01f354` | renderer glyph/context resolver | (none) |

## Table and State References

| Absolute address | Role | Longword literal references |
| ---: | --- | --- |
| `0x00782f06` | primary/secondary text-map selector | `0x00c5dc`, `0x00c600`, `0x00c698`, `0x00c6aa`, `0x00c6c6`, `0x00c6de`, `0x00cbe4`, `0x00d094`, `0x00e2ae`, `0x00e2d0`, `0x00e528`, `0x00e54a`, ... (42 total) |
| `0x00782f32` | primary 256-byte character-to-glyph map | `0x013956`, `0x014d9e`, `0x014e2a`, `0x014f46` |
| `0x00783032` | secondary 256-byte character-to-glyph map | `0x013964`, `0x014f54` |
| `0x00782ee6` | primary current-font context record | `0x00c442`, `0x00cbde`, `0x00ce86`, `0x00e2c2`, `0x00e4bc`, `0x00e504`, `0x00e53c`, `0x00e750`, `0x00e87a`, `0x00eca4`, `0x00f26e`, `0x00f318`, ... (31 total) |
| `0x00782ef6` | secondary current-font context record | `0x00e50a`, `0x01396a`, `0x0144ec`, `0x01683e`, `0x01a954`, `0x01b3a0`, `0x01b462`, `0x01bfb4` |
| `0x00783132` | primary high-character/symbol-set flag | `0x00d07e`, `0x012498`, `0x012562`, `0x0139a4`, `0x014d3c`, `0x014d56`, `0x014d78`, `0x014fbe`, `0x01cf56`, `0x01d88a`, `0x01da94`, `0x01dd14` |
| `0x00783133` | secondary high-character/symbol-set flag | `0x00d086`, `0x0124a0`, `0x01256a`, `0x0139c4`, `0x014d44`, `0x014d60`, `0x014d82` |
| `0x00783134` | primary mapped character range | `0x01398e`, `0x014ccc`, `0x014d14` |
| `0x0078313a` | secondary mapped character range | `0x0139ae` |
| `0x00783144` | primary active symbol-set word | `0x00c67a`, `0x00cc38`, `0x00e2da`, `0x00e554`, `0x00e692`, `0x00e768`, `0x00e7da`, `0x0103aa`, `0x013ad6`, `0x013b3e`, `0x013eca`, `0x013faa`, ... (35 total) |
| `0x00783146` | secondary active symbol-set word | `0x00cc42`, `0x00e6f6`, `0x00e828`, `0x0103b4`, `0x0144ba`, `0x0149f0`, `0x014cee`, `0x014f5a`, `0x0157b6`, `0x01b340`, `0x01b3a6`, `0x01b468` |

## Built-In Base-Map Examples

These are the base mappings created by `0x14d9c` before `0x14f16` applies
symbol-set patches.

| Context | Record | Character range | Example mapped bytes |
| ---: | --- | --- | --- |
| `0x4008004c` | `(unnamed)` @`0x00004c` | `0x21`..`0xfe` | `0x21->0x00`, `0x22->0x01`, `0x23->0x02`, `0x24->0x03` |
| `0x44080418` | `COURIER` @`0x000418` | `0x01`..`0xff` | `0x01->0x00`, `0x02->0x01`, `0x03->0x02`, `0x04->0x03` |
| `0x440946b4` | `LINE_PRINTER` @`0x0146b4` | `0x01`..`0xff` | `0x01->0x00`, `0x02->0x01`, `0x03->0x02`, `0x04->0x03` |

## Current Reproduction Contract

- To render built-in text exactly, reproduce the firmware's active map table
  for the selected primary/secondary font slot, including `0x14f16` symbol-set
  patching.
- The compact glyph payload byte is not necessarily the original host byte. It
  is the mapped byte stored at text object `+0x0b` and copied by `0x12f2e`.
- The renderer-side glyph identity is `(context longword, mapped byte)`. ROM
  built-in context low 24 bits map to `IC32,IC15` offset `address - 0x80000`;
  bit 30 selects the offset-table resource form for both ROM and RAM-backed
  records, and each table entry is a relative 32-bit offset from the record
  start.
- The `0x14fce` symbol-set patch tables and their Technical Reference names
  are decoded in `ic30_ic13_symbol_set_patch_tables.md`; the harness now
  drives `ESC (2U` and `ESC )0E` through `0x120be`/`0x1be22`, traces the same
  stream through ROM parser setup handlers `0x1201e`/`0x12008` and terminal
  handler `0x120be`, applies the resulting `0x0055` patch table plus `0x0005`
  Roman Extension half-map to the `LINE_PRINTER` base map, separately traces
  `ESC (7X` plus `ESC )0@`/`ESC (1@`/`ESC )2@`/`ESC (3@`/`ESC )3@` through the
  same parser terminal path to pin the `X` font-ID and `@0..@3` special-case
  model, and now pins `0x1ac0a`/`0x1af36` default/fallback table-builder side
  effects that feed `@0`, `@1`, `@3`, and `0x156de` fallback selection; the
  live host parser path into `0x1393a` is documented in
  `ic30_ic13_printable_text_path.md`; paired cursor/queue/span paths after
  `0x1393a` are documented in `ic30_ic13_text_cursor_span_flow.md`;
  `tools/render_fixture_harness.py` now models a base-map -> `0x1393a`
  source-object -> `0xd824` positioning -> `0x12f2e` short bucket path for
  `LINE_PRINTER` host byte `0x21`, includes one-byte and two-byte normal
  printable stream fixtures for byte `0x21` through source mapping, `0xd550`
  default cursor advance, positioning, same-bucket queueing, and rendering,
  renders the initialized `LINE_PRINTER` HMI case where `0x10550(0x00480000)`
  produces advance `0x00120000` and compact coord `0x0202` / `$a001 = 0x12`,
  adds a mixed `ESC &k1G!\r!` fixture where CR+LF positions the second glyph
  at coord `0x3b00` / `$a001 = 0x1b` and proves full-byte shifted blank-row
  clearing, traces that same mixed stream through parser handlers `0xedf8`,
  `0xd04a`, `0xf02c`, and `0xd04a` before page-record `0x1387c`
  allocation/reuse and `0x1edc6` bridge/rendering, adds a margin stream `ESC
  &a1L!` that routes `0xeb58` -> `0xd04a` before queueing/rendering the glyph
  at compact coord `0x0801` / pixel x `24`, adds cursor-position streams `ESC
  &a2C!` and `ESC &a1R!` that route `0xf39e` and `0xf560` -> `0xd04a` before
  queueing/rendering glyphs at compact coords `0x0a02` / pixel x `42` and
  `0x1001` / bucket `4`, adds a vertical-layout stream `ESC &l3E!` that routes
  `0xece2` -> `0xd04a` before queueing/rendering the glyph at compact coord
  `0x9001` in bucket `6`, and adds a mixed `!\x1bE` fixture where reset
  publishes and clears a valid current page root after queued text and has the
  pre-reset object queued/bridged through page-record storage. It also covers
  the negative-left overflow branch, adds `0x1387c` page-record bucket
  allocator fixtures for short reuse, full-object new-head allocation, and
  segmented tall-glyph bucket allocation/reuse, adds a `0x1edc6` page-record
  bridge fixture for compact bucket/context-slot copying plus rule/fixed-list
  normalization, producer-shaped `0x13386`/`0x136d2` rule-list objects, and
  text/rule/raster plus simple execute/call and mixed-control macro execute
  parser-to-page-record checks and macro-payload rule/raster band composition,
  adds a selected inline/downloaded map/source fixture through
  `0x14e24`/`0x14eb6` -> `0x1393a` -> `0xd3b2` -> `0x12f2e` -> render plus
  `0x168dc`/`0x16942` font payload-reader fixtures, `0x172c0`/`0x16c14`
  downloaded-font record bookkeeping fixtures, `0x170be`/`0x17108`/`0x17150`
  record lookup/mark/unmark fixtures, `0x15a56`/`0x16df6` font-id/control
  dispatch fixtures, and `0x16fae`/`0x17362`/`0x17026`/`0x1719c`
  validation-table/staged-header/payload-backed inline allocation fixtures,
  keeps synthetic inline/downloaded records for `0x12f2e` short, page-record
  short, width-bit, segmented, and combined width+segmented payload shapes as
  isolation controls, constructs selected inline/downloaded wide, segmented,
  and segmented-wide fixed records for host bytes `0x23`, `0x24`, and `0x25`
  through `0x14e24`/`0x14eb6` -> `0x1393a` -> `0xd3b2` -> `0x12f2e`, renders
  those constructed records through `0x1f0d2`, `0x1f1f0`, and `0x1f264`, adds
  type-2 `0x1719c` payload-backed fixed-record coverage for the `0x1f0d2` and
  `0x1f1f0` cases, ties the `ESC *c4660d37e5F` ROM parser trace to the current
  id/current character used by the following descriptor and character payload
  fixtures, ties the `ESC )s0W` ROM parser trace to `0x15d0a` current-record
  and continuation descriptor routes, and ties the `ESC )s2193W` ROM parser
  trace to a `0x16498` downloaded character-object fixture that allocates the
  larger glyph `0x25` bitmap object, copies its split-plane payload through
  `0x16874`/`0x16942`, resolves it as a downloaded-pointer glyph, and renders
  the `0x1f264` segmented-wide row, models a segmented `0x2000` producer path
  for host byte `0x20`, adds a ROM-scanned built-in row-copy span matrix for
  spans 1, 2, 4, 6, and 8, and scans that all firmware-scanned built-in glyph
  records top out at mode-1 render span 8 for normal bitmaps, with the mode-0
  tall targets being zero-delta aliases rather than normal bitmap entries.
  Remaining work is to replace the synthetic allocator/bridge and constructed
  font-download object bytes with parser-produced page roots, live
  font-download parser-populated inline/downloaded records, and full
  parser-produced page-object payloads.
- The right-margin page-record boundary now covers `ESC &a1M!`: parser handler
  `0xec0c` moves the cursor/right margin to two initialized `LINE_PRINTER` HMI
  columns before printable `0xd04a` queues the glyph at compact coord `0x0a02`
  / pixel x `42` through the same bridge.
- The chained-margin page-record boundary now covers `ESC &a6l9M!`:
  lowercase-final `ESC &a6l` leaves parser mode `12` open after handler
  `0xeb58`, `9M` reaches handler `0xec0c`, then printable `0xd04a` queues the
  glyph at compact coord `0x0207` / pixel x `114` through the same bridge.
- The LF page-record boundary now covers `ESC &k2G!\n!`: line-termination
  handler `0xedf8` sets mode `0x60`, LF handler `0xf08c` applies CR+LF before
  the second printable `0xd04a`, and the glyph queues at compact coord
  `0x3b00` through the same bridge.
- The HT/BS page-record boundary now covers `ESC &k0G HT BS !`: parser handler
  `0xedf8` clears line-termination mode, HT reaches `0xf1cc`, BS reaches
  `0xf2a8`, then printable `0xd04a` queues the glyph at compact coord `0x0a01`
  / pixel x `26` through the same bridge.
- The horizontal-decipoint page-record boundary now covers `ESC &a72H!`:
  parser handler `0xf416` converts 72 decipoints into 30 packed cursor units
  before printable `0xd04a` queues the glyph at compact coord `0x0402` / pixel
  x `36` through the same bridge.
- The vertical-decipoint page-record boundary now covers `ESC &a72V!`: parser
  handler `0xf60a` converts 72 decipoints into packed cursor y `30` before
  printable `0xd04a` queues the glyph at compact coord `0x9001` in bucket `0`
  with nine blank rows before the bridged glyph body.
- The chained cursor-position page-record boundary now covers `ESC &a2c+1R!`:
  lowercase-final `ESC &a2c` leaves parser mode `12` open after handler
  `0xf39e`, relative `+1R` reaches handler `0xf560`, then printable `0xd04a`
  queues the glyph at compact coord `0x1a02` in bucket `3` through the same
  bridge.
- The cursor-stack page-record boundary now covers `ESC &f0S ESC &a2C ESC
  &f1S!`: parser handlers `0xf75e`, `0xf39e`, and `0xf75e` save, move, and
  restore the cursor before printable `0xd04a` queues the glyph at compact
  coord `0x0001` through the same page-record bridge.
