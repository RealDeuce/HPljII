# IC30/IC13 Direct Control-Code Flow

Generated from handlers `0xf02c..0xf55e`, line-termination handler `0xedf8`,
wrap handler `0xedb0`, dot-position handlers `0xf48c`/`0xf692`,
transparent-data handler `0x11f5a`, and state-reference scans of the verified
firmware image. This report tracks parser commands that change
cursor/page/text state before text or raster objects are queued.

## Line-Termination Mode

PCL `ESC &k#G` reaches handler `0xedf8`, which stores absolute values into
`0x78318f`:

| `#` | Stored byte | Firmware effect bits | PCL meaning |
| ---: | ---: | --- | --- |
| 0 | `0x00` | no extra CR/LF/FF coupling | CR=CR, LF=LF, FF=FF |
| 1 | `0x80` | CR tests bit 7 and also calls LF advance | CR=CR+LF |
| 2 | `0x60` | LF tests bit 6 and FF tests bit 5, both also call CR reset | LF=CR+LF, FF=CR+FF |
| 3 | `0xe0` | bits 7, 6, and 5 all set | CR=CR+LF, LF=CR+LF, FF=CR+FF |

## Wrap and Transparent Data

PCL `ESC &s#C` reaches handler `0xedb0`, which rewinds the parsed six-byte
record and uses the absolute parsed value:

| `#` | Firmware state | Reproduction meaning |
| ---: | --- | --- |
| 0 | writes `0x783190 = 1` | end-of-line wrap is enabled for printable text overflow paths |
| 1 | clears `0x783190` | end-of-line wrap is disabled |
| other | leaves `0x783190` unchanged | unsupported selector is ignored after record rewind |

PCL `ESC &p#X` reaches handler `0x11f5a`, which only arms delayed payload
handler `0x12452` through `0x121cc`; the payload bytes are consumed later
after `0x12218` restores the saved command record. Consumer `0x12452` uses the
absolute byte count, stops on `D7=-1`, applies the same `0x1a 0x58 -> 0x7f`
normalization as other text repeat readers, routes printable bytes through
`0xd04a`, and filters control bytes through `0xd0f0` depending on the active
symbol/high-byte state.

## Direct Control Handlers

| Byte | Handler | Confirmed side effects | Pixel-reproduction consequence |
| ---: | ---: | --- | --- |
| CR `0x0d` | `0xf02c` | calls CR helper `0xf06e`, then `0xf34a`; if `0x78318f.7` is set, calls LF helper `0xf0b2` | resets horizontal text cursor to left/default margin and may also advance vertically depending on `ESC &k#G` |
| LF `0x0a` | `0xf08c` | if `0x78318f.6` is set, calls CR helper `0xf06e`; always calls `0xf34a` and LF helper `0xf0b2` | advances vertical cursor by line advance `0x783160`, with optional horizontal reset |
| FF `0x0c` | `0xf0f0` | if `0x78318f.5` is set, calls CR helper `0xf06e`; calls `0xf34a`, ensures page root through `0x10084`, calls page/eject helper `0xf124`, then writes `0x782a6d = 0xff` | finalizes current page/root state and recomputes vertical cursor for the next page context, with optional horizontal reset |
| HT `0x09` | `0xf1cc` | converts default HMI `0x78315c`; computes next eight-column stop from `0x782c8a - 0x782dd6`, clamps against `0x782dda` or `0x782db8 << 16`, writes `0x782c8a`, then calls `0xd8fc` or `0xd4ac` for active context span update | horizontal cursor jumps to firmware tab stop and can flush/update text span bounds before the next printable byte |
| BS `0x08` | `0xf2a8` | subtracts either previous width `0x782a5a << 16` when `0x78318e` is set or default HMI `0x78315c`; clamps at `0` and crossing `0x782dd6`; writes `0x782c8a`, sets `0x782a58=1`, clears `0x782a57/0x782a6d`, then calls `0xd8fc` or `0xd4ac` | horizontal cursor backs up using current text metrics while preserving a pending previous-width state for the following printable character |
| `ESC &a#L` | `0xeb58` | takes absolute parsed columns, scales through current HMI `0x78315c`, rejects values beyond `0x782dda - HMI`, writes `0x782dd6`, and moves `0x782c8a` with pending-span flush when the new margin is right of the cursor or pending text is marked | left margin directly changes CR reset position, HT/BS clamps, and the next printable text origin |
| `ESC &a#M` | `0xec0c` | takes `abs(parameter) + 1` columns, scales through HMI, rejects values before `0x782dd6 + HMI`, clamps beyond `0x782db8`, writes `0x782dda`, and when the new margin is left of the cursor moves `0x782c8a`, updates the active span, and sets `0x782a57` | right margin limits horizontal positioning and can force the current cursor to the new line limit |
| `ESC &a#C` | `0xf39e` | converts parsed decimal columns through current HMI `0x78315c`, scales through helpers `0x332ee`/`0x3324a`/`0x104d8`, and commits through `0xf4ca` using parsed-record bit 0 as the relative flag | column positioning changes horizontal text/raster placement in HMI units with the same horizontal clamps/span updates as HT/BS |
| `ESC &a#H` | `0xf416` | converts parsed decipoints as five packed subunits per decipoint, then commits through `0xf4ca` using parsed-record bit 0 as the relative flag | horizontal decipoint positioning maps host coordinates into 300 dpi twelfths before object placement |
| `ESC &a#R` | `0xf560` | ensures a page root, masks the parsed flag to bit 0, adds fractional `0.7200` before VMI scaling for absolute rows, converts through current VMI `0x783160`, commits through `0xf6e2`, calls overflow recovery helper `0x1048c` for relative moves, and clamps absolute rows to `0x782dc6` | row positioning uses VMI units and has a firmware absolute-row bias that must be reproduced before text/raster queuing |
| `ESC &a#V` | `0xf60a` | converts parsed decipoints as five packed subunits per decipoint, commits through `0xf6e2` using parsed-record bit 0 as the relative flag, and clamps to `0x782dc6` | vertical decipoint positioning maps host coordinates into the same vertical cursor used by text and raster start state |
| `ESC *p#X` | `0xf48c` | sign-extends the parsed word, shifts it left 16 bits to a whole-dot packed coordinate, then commits through `0xf4ca` using parsed-record bit 0 as the relative flag | horizontal dot positioning shares the same clamp, right-limit latch, pending-text clear, and active-span update path as `ESC &a#C/#H` |
| `ESC *p#Y` | `0xf692` | sign-extends the parsed word, shifts it left 16 bits, commits through `0xf6e2` using parsed-record bit 0 as the relative flag, then clamps to `0x782dc6` | vertical dot positioning shares the same page-root, pending-span flush, top/relative base, and vertical-bound behavior as `ESC &a#R/#V` |
| `ESC &f0S` / `ESC &f1S` | `0xf75e` | selector `0` pushes `0x782c8a` plus `0x782c8e + 0x782dbe` as an 8-byte stack entry while `0x782d36` is below the upper bound; selector `1` pops while the pointer is above `0x782c96`, restores horizontal position clamped to `0x782db8 - 1/12`, restores vertical position after subtracting `0x782dbe` and clamping to `0x782dc6 - 1/12`, clears `0x782a57/0x782a6d`, and flushes pending spans when `0x783184` is set | cursor push/pop is part of placement state and can change subsequent text/raster coordinates after page size, orientation, or margins have changed |

## Shared Helpers

| Helper | Confirmed behavior |
| ---: | --- |
| `0xf06e` | copies `0x782dd6` to `0x782c8a`, clears `0x782a57` and `0x782a6d` |
| `0xf34a` | clears `0x782a58`; if `0x783184` is nonzero, flushes pending text span through `0x12714` and `0x126e2` |
| `0xf0b2` | ensures page root through `0x10084`, adds `0x783160` to `0x782c8e` via `0x10518`, calls `0xf36c`, optionally calls `0x1048c`, and clears `0x782a6d` |
| `0xf124` | calls page-root finalize `0xff1e`, derives a fixed-point vertical value from `0x783160`, constants `0x12` and `0x19`, and `0x782dce`, writes `0x782c8e`, and clears `0x782a6d` |
| `0xf36c` | compares vertical cursor `0x782c8e` against limit/state `0x782dc2`; when `0x783191` is set and limit is exceeded, calls `0xf124` and returns zero |
| `0xf4ca` | shared horizontal-position commit helper used by ESC-positioning handlers; optionally adds to `0x782c8a`, clamps between `0` and `0x782db8 << 16`, writes `0x782c8a`, updates `0x782a57`, clears `0x782a6d`, and calls `0xd8fc` or `0xd4ac` |
| `0xf6e2` | shared vertical-position commit helper used by `ESC &a#R/#V`; ensures a page root, clears/flushes pending text state through `0xf34a`, adds either the current vertical cursor or top offset `0x782dce`, clamps against lower bound `0x782dca`, writes `0x782c8e`, and returns the written cursor |

## State Reference Scan

| Address | Current role | Longword literal references |
| ---: | --- | --- |
| `0x0078299e` | parser six-byte record cursor rewound by parsed cursor-position handlers | `0x002f18`, `0x00c39a`, `0x00c3ca`, `0x00c3d0`, `0x00c3e4`, `0x00c3f4`, `0x00c58a`, `0x00c592`, `0x00c6f6`, `0x00c6fe`, `0x00c78a`, `0x00c792`, `0x00c7ea`, `0x00c7f2`, `0x00c84a`, `0x00c852`, ... (146 total) |
| `0x00782a57` | right-margin/line-limit latch set when horizontal cursor reaches `0x782dda` | `0x00ec06`, `0x00ecdc`, `0x00f07e`, `0x00f30c`, `0x00f51a`, `0x00f522`, `0x00f818`, `0x00f820`, `0x00f90c` |
| `0x00782a58` | pending previous-width latch cleared before text span flushes and set by BS | `0x00d174`, `0x00d1b0`, `0x00d250`, `0x00d5b0`, `0x00d5c8`, `0x00d682`, `0x00f306`, `0x00f350` |
| `0x00782a5a` | latched previous text width used by BS when alternate metrics flag is set | `0x00d184`, `0x00d1c4`, `0x00d5c0`, `0x00d5d8`, `0x00f2c8` |
| `0x00782a6d` | printable/pending text flag cleared by control-code cursor moves; FF sets it to `0xff` after page eject | `0x00ca3a`, `0x00cb84`, `0x00ce48`, `0x00d0e4`, `0x00d138`, `0x00ebc0`, `0x00ed60`, `0x00f084`, `0x00f0e8`, `0x00f11c`, `0x00f16e`, `0x00f1c4`, `0x00f312`, `0x00f528`, `0x00f6f6`, `0x00f826` |
| `0x00782c8a` | current horizontal text cursor, reset by CR and changed by HT/BS | `0x00d15c`, `0x00d19a`, `0x00d1a2`, `0x00d228`, `0x00d24a`, `0x00d2d4`, `0x00d310`, `0x00d34c`, `0x00d3c4`, `0x00d51e`, `0x00d56c`, `0x00d5ee`, `0x00d5f6`, `0x00d65a`, `0x00d67c`, `0x00d744`, ... (110 total) |
| `0x00782c8e` | current vertical text cursor, advanced by LF and reset/recomputed by FF | `0x00ca6e`, `0x00cbb8`, `0x00d364`, `0x00d3ec`, `0x00d402`, `0x00d4c2`, `0x00d7d0`, `0x00d86c`, `0x00d882`, `0x00d912`, `0x00ed94`, `0x00f0c4`, `0x00f0d2`, `0x00f168`, `0x00f1a0`, `0x00f1ae`, ... (83 total) |
| `0x00782c96` | bottom of the `ESC &f#S` cursor stack | `0x00cde8`, `0x00f7ca` |
| `0x00782d36` | next-free pointer and upper bound for the `ESC &f#S` cursor stack | `0x00cdec`, `0x00f786`, `0x00f790`, `0x00f7fa` |
| `0x00782db8` | horizontal page extent used to clamp HT and horizontal positioning | `0x00d26a`, `0x00d334`, `0x00d38a`, `0x00d69c`, `0x00d7a4`, `0x00d7f8`, `0x00e9c6`, `0x00e9e4`, `0x00ec70`, `0x00ec80`, `0x00f25e`, `0x00f4f8`, `0x00f7da`, `0x00f8a2`, `0x00f8c0`, `0x010ba4`, ... (29 total) |
| `0x00782dc6` | vertical upper bound used by `ESC &a#R/#V` and cursor-stack pop clamps | `0x00f5f2`, `0x00f5fa`, `0x00f67a`, `0x00f682`, `0x00f6ca`, `0x00f6d2`, `0x00f830`, `0x00f8ee`, `0x01049c`, `0x010742`, `0x01074a` |
| `0x00782dca` | vertical lower bound used by helper `0xf6e2` | `0x00f72e`, `0x00f736`, `0x00f8d0`, `0x0104b8` |
| `0x00782dce` | top/vertical offset added by FF helper `0xf124` and absolute `ESC &a#R/#V` positioning | `0x00ca60`, `0x00cbaa`, `0x00cd06`, `0x00e5fe`, `0x00e620`, `0x00ea2e`, `0x00ea84`, `0x00eaf8`, `0x00eb44`, `0x00ed56`, `0x00ed86`, `0x00f15a`, `0x00f71c`, `0x00f93c`, `0x00fc18`, `0x00fc32`, ... (30 total) |
| `0x00782dd6` | left-margin/default horizontal cursor copied into `0x782c8a` by CR helper `0xf06e` and written by `ESC &a#L` | `0x00e9c0`, `0x00e9f0`, `0x00e9fa`, `0x00ebee`, `0x00ec5c`, `0x00f074`, `0x00f1ec`, `0x00f2e8`, `0x00f902` |
| `0x00782dda` | right-margin/current horizontal limit used by HT/helper `0xf4ca` and written by `ESC &a#M` | `0x00d214`, `0x00d2e8`, `0x00d646`, `0x00d758`, `0x00e9ca`, `0x00ea00`, `0x00ea0a`, `0x00eba6`, `0x00ebfc`, `0x00ecba`, `0x00f250`, `0x00f510`, `0x00f80e` |
| `0x0078315c` | default horizontal motion / HMI value used by HT and BS | `0x00c4bc`, `0x00c4ee`, `0x00caf4`, `0x00cc14`, `0x00cc32`, `0x00ceae`, `0x00cec4`, `0x00d1aa`, `0x00d1de`, `0x00d5aa`, `0x00d610`, `0x00eb80`, `0x00eba0`, `0x00ec36`, `0x00ec56`, `0x00f1d6`, ... (29 total) |
| `0x00783160` | line advance / VMI value added by LF and FF helpers | `0x00ca7e`, `0x00cb7e`, `0x00cef8`, `0x00cf1c`, `0x00cf34`, `0x00eac6`, `0x00ed0a`, `0x00f0be`, `0x00f130`, `0x00f188`, `0x00f58a`, `0x00f912`, `0x00fa16`, `0x00fe5e`, `0x0102cc`, `0x0102f8`, ... (23 total) |
| `0x00783184` | pending text span flush enable tested by `0xf34a` | `0x00ce60`, `0x00d4ba`, `0x00d90a`, `0x00e32a`, `0x00ebd2`, `0x00f356`, `0x00f742`, `0x00f868`, `0x0103be`, `0x0103c6`, `0x01175a`, `0x0126a4`, `0x0126e8`, `0x0126f2`, `0x012724` |
| `0x0078318e` | alternate previous-width mode tested by BS | `0x00c488`, `0x00c4c8`, `0x00cbf4`, `0x00cc20`, `0x00d16c`, `0x00d2a0`, `0x00d588`, `0x00d6e2`, `0x00f2be`, `0x010366`, `0x010392` |
| `0x0078318f` | line-termination mode byte written by `ESC &k#G` and tested by CR/LF/FF | `0x00ce72`, `0x00ee22`, `0x00ee34`, `0x00ee4c`, `0x00ee5e`, `0x00f040`, `0x00f094`, `0x00f0f8` |
| `0x00783190` | end-of-line wrap flag written by `ESC &s#C` and tested by printable text overflow paths | `0x00ce78`, `0x00d302`, `0x00d33e`, `0x00d772`, `0x00d7ae`, `0x00eddc`, `0x00edec`, `0x01c22c`, `0x01e0dc`, `0x01e910`, `0x030f3c` |
| `0x00783191` | vertical overflow recovery enable tested by `0xf36c` | `0x00ce80`, `0x00ee8e`, `0x00eea0`, `0x00f388`, `0x01c232`, `0x01e0e2`, `0x01e916`, `0x030f42` |

## Current Reproduction Contract

- A byte-stream model must apply `ESC &k#G` before interpreting CR/LF/FF
  because the firmware stores the mode as bit flags in `0x78318f` and the
  direct control handlers test those bits at runtime.
- `ESC &s#C` is not only parser metadata: selector `0` writes wrap flag
  `0x783190=1` and selector `1` clears it. Printable text overflow paths test
  this flag, so wrap mode has to be part of the text layout state.
- `ESC &p#X` transparent data is not opaque to rendering. It uses
  delayed-payload restore through `0x121cc`/`0x12218`, then handler `0x12452`
  feeds each consumed byte through the same printable/control text pipeline as
  repeat text, including `0x1a 0x58` normalization to `0x7f`.
- `ESC *p#X/#Y` dot positioning converts host dots to whole-dot packed cursor
  coordinates with `parameter << 16`, then uses the same horizontal and
  vertical commit helpers as the `ESC &a` cursor-position commands.
- CR/LF/FF/HT/BS do not only change cursor coordinates; they can flush pending
  text spans, ensure/finalize page roots, and invoke the same context span
  update routines `0xd4ac` / `0xd8fc` used after printable text.
- Axis names remain provisional, but `tools/render_fixture_harness.py` now has
  synthetic state fixtures for the line-termination map plus CR/LF/FF/HT/BS
  cursor/page effects, `ESC &f#S` cursor stack push/pop and clamp behavior,
  `ESC &a#C/#H/#R/#V` cursor-position conversion/relative/clamp behavior, `ESC
  &a#L/#M` margin conversion/reject/cursor-move behavior, narrow byte-stream
  fixtures for `ESC &k1G`+CR, `ESC &k2G`+LF, `ESC &k2G`+FF, `ESC
  &k3G`+CR/LF/FF, `ESC &k0G`+HT/BS, `ESC &f0S`/`ESC &f1S` through selector
  handler `0xf75e`, chained `ESC &l8c6d3e2F` through vertical-layout handlers
  `0xcb00`/`0xc992`/`0xece2`/`0xea9e`, chained `ESC &a3.5c+1R` through
  cursor-position handlers `0xf39e` and `0xf560`, and chained `ESC &a6l9M`
  through margin handlers `0xeb58` and `0xec0c`, a mixed `ESC &k1G!\r!`
  fixture that applies CR+LF before queueing the second printable glyph and
  ties the ROM parser handlers to the page-record allocator/bridge result, an
  `ESC &a1L!` fixture that ties left-margin handler `0xeb58` to shifted
  page-record text output, `ESC &a2C!` and `ESC &a1R!` fixtures that tie
  cursor-position handlers `0xf39e` and `0xf560` to shifted page-record text
  output, an `ESC &l3E!` fixture that ties top-margin handler `0xece2` to
  vertically shifted page-record text output, a mixed `!\x1bE` fixture that
  applies reset publication/clear state after queued text and has a
  page-record allocator/bridge/publication variant for the pre-reset glyph,
  and a publication-boundary fixture tying reset, FF, page-size, and
  orientation parser-handler sequences to one-root allocation, one `0xff1e`
  publication, current-root clearing, and rendered rows after `0x1edc6`. The
  remaining step is expanding this into the full firmware parser path with
  real page-object allocation.
- The direct-control/page-record boundary fixtures now also drive `ESC &a1M!`,
  tying right-margin handler `0xec0c` to cursor movement and restored
  page-record text output through printable handler `0xd04a` at compact coord
  `0x0a02`.
- The direct-control/page-record boundary fixtures now also drive `ESC
  &a6l9M!`, tying lowercase-final left-margin handler `0xeb58` and
  right-margin handler `0xec0c` to text output through printable handler
  `0xd04a` at compact coord `0x0207` / pixel x `114`.
- The direct-control/page-record boundary fixtures now also drive `ESC
  &k2G!\n!`, tying LF handler `0xf08c` to line-termination mode `0x60`, CR+LF
  cursor movement, and text output through printable handler `0xd04a` at
  compact coord `0x3b00`.
- The direct-control/page-record boundary fixtures now also drive `ESC &k0G HT
  BS !`, tying line-termination handler `0xedf8`, HT handler `0xf1cc`, and BS
  handler `0xf2a8` to text output through printable handler `0xd04a` at
  compact coord `0x0a01` / pixel x `26`.
- The direct-control/page-record boundary fixtures now also drive `ESC
  &a72H!`, tying horizontal-decipoint handler `0xf416` to cursor conversion
  and restored page-record text output through printable handler `0xd04a` at
  compact coord `0x0402`.
- The direct-control/page-record boundary fixtures now also drive `ESC
  &a72V!`, tying vertical-decipoint handler `0xf60a` to cursor conversion and
  restored page-record text output through printable handler `0xd04a` at
  compact coord `0x9001` / bucket `0`.
- The direct-control/page-record boundary fixtures now also drive `ESC
  &a2c+1R!`, tying lowercase-final horizontal cursor-position handler `0xf39e`
  and relative vertical handler `0xf560` to text output through printable
  handler `0xd04a` at compact coord `0x1a02` / bucket `3`.
- A new direct-control/page-record boundary fixture drives `ESC &f0S ESC &a2C
  ESC &f1S!`, tying cursor-stack handlers `0xf75e` and cursor-position handler
  `0xf39e` to restored text output through printable handler `0xd04a` at
  compact coord `0x0001`.
