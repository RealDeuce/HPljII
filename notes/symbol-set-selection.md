# Symbol-Set And Font-Designation Firmware

This note documents the checked-in command-family path for primary and
secondary font-designation commands:

- `ESC (` primary symbol-set / font-designation commands
- `ESC )` secondary symbol-set / font-designation commands
- ordinary symbol-set finals such as `ESC (8U`
- final `X` font-ID selection
- final `@` default-symbol/default-font variants

These commands do not draw pixels immediately. Their visible effect is to
change the requested font/symbol state, refresh the selected font context,
rebuild the character-to-glyph map, and thereby change what later printable
bytes queue through `0xd04a`.

Primary evidence:

- `generated/disasm/ic30_ic13_payload_dispatch_011f82.lst`
- `generated/disasm/ic30_ic13_symbol_set_handler_01be22.lst`
- `generated/disasm/ic30_ic13_font_update_common_00c580.lst`
- `generated/disasm/ic30_ic13_font_context_install_00c428.lst`
- `generated/disasm/ic30_ic13_font_candidate_activate_01569c.lst`
- `generated/disasm/ic30_ic13_font_id_select_017708.lst`
- [font-context-metrics.md](font-context-metrics.md#owner-summary)
- [built-in-resource-scan.md](built-in-resource-scan.md)

The generated report
`generated/analysis/ic30_ic13_active_symbol_set_flow.md` remains supporting
table/cross-reference evidence. This file is the checked-in behavioral note.

## Owner Summary

This note owns the parsed `ESC (` and `ESC )` symbol/font-designation command
family. These commands write requested symbol or font-id state, then enter the
shared font refresh bridge. They do not queue page objects directly. Their
pixel effect is delayed until later printable bytes consume the selected
current-font context and character map through `0xd04a -> 0x1393a`.

Primary routes:

- Parser entry:
  normal `ESC (` uses `0x1201e -> 0x11f26` to append a slot-0 setup record;
  normal `ESC )` uses `0x12008 -> 0x11efe` to append a slot-1 setup record.
  Terminal wrapper `0x120be` calls `0x1be22` and then `0xc580`.
- Ordinary symbol-set finals:
  `0x1be22` computes
  `(abs(parameter) << 5) + final_byte - 0x40`, writes `0x782ef4` or
  `0x782f04`, and sets dirty flags `0x782f2c = 1` and `0x782f2d = 1`.
- Final `X`:
  `0x1be22 -> 0x1c066 -> 0x17708` treats the parameter as a font id, restores
  the prior requested symbol word, and marks dirty value `2`. Successful
  helper paths select a built-in or inline/downloaded candidate; non-selected
  exits preserve the prior selected context.
- Final `@`:
  `0x1be22 -> 0x1bec8` dispatches through table `0x1bde2`. Parameters `0`,
  `1`, and `2` copy default/requested symbol words; parameter `3` runs the
  default-font helper path; other values restore the previous word and return.
- Refresh and map route:
  `0xc580` decides whether to call `0x13eb8` and/or `0xc428`. Candidate
  refresh consumes requested, remembered, and fallback symbol words through
  `0x156de`; `0x144d2` writes current-font context records, `0x14c64`
  rebuilds maps, and `0x14f16` applies Roman-8-compatible patch rules.
- Output route:
  SI/SO handlers `0xc68a` / `0xc6b8` choose primary or secondary selected
  slot `0x782f06`. Later printable bytes read the selected context and map,
  queue compact text, and reach rendering through the font-context owner.

Field groups:

- Canonical parser/request state:
  synthetic slot records from `0x11f26` / `0x11efe`, active parser cursor
  `0x78299e`, requested symbol words `0x782ef4` / `0x782f04`, and selected
  text slot `0x782f06`.
- Canonical selected state:
  active symbol words `0x783144` / `0x783146`, current-font contexts
  `0x782ee6` / `0x782ef6`, rebuilt maps `0x782f32` / `0x783032`, and
  page-root context slot `0x78297e`.
- Derived/cache state:
  remembered symbol words `0x782f08` / `0x782f0a`, fallback/default tables
  `0x782f0c..0x782f28`, selected-font snapshots `0x783148` / `0x783152`,
  candidate list counts/cursors `0x78278e..0x7827b4`, active window
  `0x78287c` / `0x7827b8`, and transient context `0x782992`.
- Parser scratch:
  final byte, integer parameter, optional fractional parameter, and slot setup
  words parsed by `0xdaf0` and consumed by `0x1be22` / `0xc580`.
- Firmware bookkeeping:
  dirty flags `0x782f2c` / `0x782f2d`, transient full-root flag `0x78298f`,
  font-id/default side-effect marker `0x78287b`, and selected candidate
  helpers `0x7828de` / `0x7828a8`.
- Unknown/external:
  the built-in resource window is documented for the listed `0N`, `10U`,
  `11U`, final-`@`, and final-`X` streams. Cartridge or other absent resource
  record contents are external data boundaries, but the ROM-local selection
  addresses remain `0x13eb8`, `0x156de`, `0x17708`, `0x14c64`, and `0x14f16`.

Output effect:

- The command family changes requested symbol/font-id state and derived maps.
- It does not alter compact text objects already queued on the page.
- Later printable bytes are the visible consumers: they read the selected map
  and context through the font-context bridge, then publication/render code
  turns the resulting compact text objects into pixels.

## Parser Entry

Normal `ESC (` and `ESC )` setup is in
`generated/disasm/ic30_ic13_payload_dispatch_011f82.lst`.

- `0x1201e` handles normal `ESC (` setup. It calls `0x11ec8`, calls
  `0x11f26` to append a synthetic six-byte setup record with slot word `0`,
  and then tokenizes through `0xdaf0`.
- `0x12008` handles normal `ESC )` setup. It calls `0x11ec8`, calls
  `0x11efe` to append a synthetic six-byte setup record with slot word `1`,
  and then tokenizes through `0xdaf0`.
- `0x120be` is the terminal wrapper for final bytes `@..^`. It calls
  `0x1be22`, then calls common refresh `0xc580`.

Alternate/data-mode wrappers `0x11fe4` and `0x11fd2` only call generic setup
`0x11ec8` and tokenize through `0xdaf0`; they do not append the synthetic slot
record. Normal symbol-set semantics therefore depend on the normal parser
wrapper, not only on the final byte.

## Requested Symbol Word

Handler `0x1be22` rewinds parser record cursor `0x78299e` by six bytes,
loads the final byte from record `+1` into `D3`, loads the integer parameter
from record `+2` into `D5`, and loads the synthetic slot word from the previous
setup record into `D4`.

`0x1be22` first takes the absolute value of the parameter. A parsed value of
`-32768` becomes `0x7fff`. For non-`X` finals, values above `0x07ff` return
without changing the requested word. Final `X` is allowed through this limit
check because its parameter is a font id, not a symbol-set number.

For ordinary symbol-set final letters, `0x1be22` computes:

```text
symbol_word = (abs(parameter) << 5) + final_byte - 0x40
requested_slot = 0x782ef4 + 0x10 * slot
word[requested_slot] = symbol_word
```

Important fields:

- `0x782ef4`: primary requested symbol word.
- `0x782f04`: secondary requested symbol word.
- `0x782f2c`: font/symbol dirty flag.
- `0x782f2d`: font/symbol refresh-in-progress flag.

Examples pinned by the ROM formula:

| PCL code | Parameter | Final | Word |
| --- | ---: | ---: | ---: |
| `0U` | `0` | `0x55` | `0x0015` |
| `8U` | `8` | `0x55` | `0x0115` |
| `0E` | `0` | `0x45` | `0x0005` |
| `2U` | `2` | `0x55` | `0x0055` |

Ordinary finals branch to `0x1c0a4 -> 0x1c04e`, setting
`0x782f2c = 1` and `0x782f2d = 1`. `0x120be` then calls `0xc580`, so the
symbol-set command immediately enters the same refresh gate used by pitch,
point-size, style, stroke, spacing, and typeface commands.

## Final-Byte Special Cases

`0x1be22` dispatches final-byte cases through the table at `0x1be0a` using
common helper `0x33298`.

- Final `X` (`0x58`) dispatches to `0x1c066`: restore the previous requested
  word, set `0x78287b`, call `0x17708(slot, parameter)`, then set
  `0x782f2c = 2` and `0x782f2d = 1`.
- Final `@` (`0x40`) dispatches to `0x1bec8`: dispatch the numeric parameter
  through table `0x1bde2`.
- Other finals dispatch to `0x1c0a4`: keep the computed requested word and
  mark dirty flags.

Final `X` deliberately does not accept the ordinary-final computed word
`(parameter << 5) + 'X' - 0x40`. It restores the saved requested word from
stack local `-4(A6)`, then calls `0x17708` with the slot and font id.
The exact instruction boundary is `0x1c066..0x1c09a`: scale slot `D4` through
`0x332ee(0x10)`, restore word `-4(A6)` into `0x782ef4 + 0x10*slot`, set
`0x78287b = 1`, call `0x17708(slot, font_id)`, then set
`0x782f2c = 2` and `0x782f2d = 1`.
Successful `0x17708` paths select a built-in or inline/downloaded font record
and rebuild the selected map through `0x14c64`; documented non-selected exits
stop before map rebuild, so following printable bytes use the prior context.

Final `@` uses table `0x1bde2`:

- Parameter `0` dispatches to `0x1bed4`: copy table word
  `0x782f1c + 8*orientation + 4*slot` into the requested slot.
- Parameter `1` dispatches to `0x1bf0a`: copy table word
  `0x782f1c + 8*orientation` into the requested slot.
- Parameter `2` dispatches to `0x1bf36`: primary restores the old requested
  word; secondary copies primary requested word `0x782ef4`.
- Parameter `3` dispatches to `0x1bf74`: run the default-font path through
  `0x1b250` or `0x1ad66`, temporarily install the active word, call
  `0x1b2fe`, then restore.
- Other parameters dispatch to `0x1c034`: restore the old requested word and
  return without dirty flags.

The ROM table makes `@0..@2` real firmware behaviors, even though the manual
names only `3@` as the default-font command.

## Refresh And Map Consumers

The requested symbol word is not the glyph map by itself.

`0xc580` is the command-family bridge from the parsed terminal record to
active font state. `0x120be` calls it immediately after `0x1be22`, so the
same host byte sequence that writes the requested symbol word also decides
whether later printable bytes see a refreshed selected context and map.

The exact refresh gate in
`generated/disasm/ic30_ic13_font_update_common_00c580.lst` is:

- `0xc588..0xc590` rewinds parser cursor `0x78299e` by six bytes to the
  terminal record that `0x1be22` just consumed.
- `0xc596..0xc5c8` returns immediately when dirty flag `0x782f2c` is zero.
- `0xc59e..0xc5c0` reads the setup slot word from record `+2`. Slots other
  than `0` or `1` report `0xe3,0x34` through `0x1284`, but the routine still
  continues to the refresh decision.
- `0xc5ca..0xc5d6` splits dirty flag `1` from all other dirty values. Normal
  symbol-set finals and final-`@` enter with dirty `1`; final `X` enters with
  dirty `2`.
- `0xc5d8..0xc618` handles dirty `1` when the parsed slot differs from
  selected slot `0x782f06`: it calls candidate refresh `0x13eb8(slot)` and
  then skips page-root context installation.
- `0xc5e4..0xc666` handles dirty `1` when the parsed slot is selected. It
  scans live page-root flags `0x78297f..0x78298e`; when all 16 flags are set,
  it can set transient flag `0x78298f`, call `0x13eb8(slot)`, clear
  `0x78298f`, probe context availability through `0xc4fc(0x782992)`, and
  either call `0x13eb8(slot)` plus `0xc428(slot)` or skip both that second
  refresh and the install when `0xc4fc` returns full status `0x11`.
- `0xc5fc..0xc60e` handles dirty `2`. It skips `0x13eb8`; if the parsed slot
  is currently selected, it calls only `0xc428(slot)`. If the parsed slot is
  not selected, it installs no page-root context.
- `0xc666..0xc686` is the common exit for non-returning refresh branches. It
  copies active word `0x783144 + 2*slot` into remembered word
  `0x782f08 + 2*slot`, clears `0x782f2c`, and returns.

For this command family, `0x13eb8` is the consumer that resolves the requested
symbol word against candidate font records and rebuilds the selected map.
`0xc428` is the consumer that makes the selected current-font context visible
through the current page root. These branches do not mark a page-root slot
live and do not draw; the printable producer marks the live flag later when
text is queued.

The symbol-specific consumer chain is:

1. `0x156de` reads requested word `0x782ef4` or `0x782f04`.
2. If no active candidate satisfies the requested word, `0x156de` retries the
   remembered word `0x782f08` or `0x782f0a`.
3. If that still misses, it uses fallback table words
   `0x782f0c..0x782f18`.
4. The selected active word is written to `0x783144` for primary or
   `0x783146` for secondary.
5. `0x144d2` writes the selected current-font context record at `0x782ee6`
   or `0x782ef6`.
6. `0x14c64` rebuilds map `0x782f32` or `0x783032`.
7. `0x14f16` applies active-symbol patch rules before printable bytes are
   mapped by `0x1393a`.

The `0x14f16` patch algorithm is documented in
[symbol-map-patching.md](symbol-map-patching.md#owner-summary). It only table-patches
maps when the selected font normalizes to Roman-8 (`0x0115`), then uses active symbol
words `0x783144` / `0x783146` to select hard-coded `0E` / `0U` behavior or a `0x14fce`
patch table.

The printable path then consumes this derived map:

- `0xd04a` handles a later printable byte.
- `0x1393a` maps the original host byte through the selected map.
- `0x12f2e` queues compact text objects.
- `0x1ed84 -> 0x1edc6 -> 0x1ef6a -> 0x1effe` carries those objects to compact
  glyph rendering.

Thus a symbol-set command changes future glyph selection and row bytes. It
does not mutate compact text objects already queued on a page.

## Concrete Candidate Windows

The requested word above is resolved against the firmware candidate lists,
not against a flat font table. The checked-in resource notes now pin the
verified built-in window that the symbol-set refresh consumes.

`0x1a2e4 -> 0x1a616 -> 0x1a9be` scans the `IC32,IC15` resource image and builds the
candidate pointer list at `0x782324`. For the verified built-ins, `0x1a9be` accepts 24
`HEAD`-path records: 12 class-zero records and 12 class-one records in the low built-in
resource window. The resulting candidate counters and cursors are documented in
[resource-rom.md](resource-rom.md) and
[built-in-resource-scan.md](built-in-resource-scan.md):

- total accepted candidate count `0x78278e = 24`;
- class-one low/range count `0x782792 = 12`, extension count
  `0x782794 = 0`;
- class-zero low/range count `0x78279a = 12`, extension count
  `0x78279c = 0`;
- cursor windows `0x7827a0 = 0x782324`, `0x7827a4 = 0x782354`,
  `0x7827a8 = 0x782354`, `0x7827ac = 0x782354`,
  `0x7827b0 = 0x782384`, and `0x7827b4 = 0x782384`.

Refresh helper `0x1569c` then chooses the active window. With
`0x782da3 == 0`, class-zero selection copies pointer/count
`0x7827ac` / `0x782798` into `0x78287c` / `0x7827b8`, giving
`0x782354` / `12` for the verified built-ins. With nonzero `0x782da3`,
class-one selection copies `0x7827a0` / `0x782790`, giving
`0x782324` / `12`. `0x156de` filters that active window by the requested,
remembered, or fallback symbol word, clears rejected active bits, writes the
retained count back to `0x7827b8`, and leaves selected candidate slot
`0x7828a8` for the chooser path.

The concrete primary parser streams `ESC (0N`, `ESC (10U`, and `ESC (11U`
write requested words `0x000e`, `0x0155`, and `0x0175` at `0x782ef4`.
Over the verified class-zero window, `0x156de` keeps survivor record starts:

- `0x000cb8`, `0x00ac1c`, `0x014f5c` for `0N`;
- `0x000418`, `0x00a37c`, `0x0146b4` for `10U`;
- `0x000868`, `0x00a7cc`, `0x014b08` for `11U`.

The chooser chain `0x14398` / `0x13c06` selects records `0x000cb8`,
`0x000418`, and `0x000868` for those primary streams. `0x144d2` writes the
primary current-font context, and `0x14c64` rebuilds primary map `0x782f32`
through the selected-symbol-not-Roman-8 path. These selections are distinct
built-in resource records; they are not Roman-8 record `0x00004c` plus a
`0x14f16` patch.

The checked-in visible-output fixture composes the same selection with later
font-selection and printable bytes. Primary streams
`ESC (0N ESC (s0p10h12v0s0b3T!!`,
`ESC (10U ESC (s0p10h12v0s0b3T!!`, and
`ESC (11U ESC (s0p10h12v0s0b3T!!` select contexts `0xc0080cb8`,
`0xc4080418`, and `0xc4080868`, then queue Courier compact entries from the
selected context. Secondary streams `ESC )0N`, `ESC )10U`, and `ESC )11U`
follow the same parser formula through `0x782f04`, select class-one contexts
`0xc00ae122`, `0xc40ad87a`, and `0xc40adcce`, cross SO handler `0xc6b8`,
and queue Line Printer compact entries from page-root context slot `1`.

That closes this semantic edge for the verified built-in resource window:
host symbol-set bytes produce canonical requested words, the candidate-window
scan supplies concrete selectable records, refresh selects current-font
contexts and derived maps, and later printable bytes consume those maps and
contexts. Cartridge or other external resource windows remain bounded by the
same `0x1a9be`, `0x1569c`, `0x156de`, `0x14398`, and `0x14c64` addresses, but
their record contents are not present in the dumped built-in ROM image.

## Field Groups

Canonical state:

- `0x782ef4` / `0x782f04`: requested primary/secondary symbol words.
- `0x783144` / `0x783146`: active selected primary/secondary symbol words.
- `0x782ee6` / `0x782ef6`: selected primary/secondary current-font context
  records.
- `0x782f06`: selected primary/secondary text slot consumed by SI/SO and text
  mapping.

Derived/cache state:

- `0x782f08` / `0x782f0a`: remembered active symbol words.
- `0x782f0c..0x782f18`: fallback symbol table used by candidate refresh.
- `0x782f1c..0x782f28`: final-`@` default-symbol table.
- `0x782f32` / `0x783032`: primary/secondary character-to-glyph maps rebuilt
  by `0x14c64`.
- `0x783148` / `0x783152`: selected-font snapshot/cache records used by map
  reuse checks.
- `0x78278e`, `0x782790..0x78279e`, and `0x7827a0..0x7827b4`: candidate-list
  count/cursor state derived by the resource scanner before selection.
- `0x78287c` / `0x7827b8`: active candidate-window pointer/count derived by
  `0x1569c` and narrowed by `0x156de`.
- `0x78297e`: selected page-root font-context slot written by `0xc428`.
- `0x78297f..0x78298e`: page-root font-context live flags read by `0xc580`
  before it decides whether to take the transient full-root branch.
- `0x782992`: transient selected context record passed to `0xc4fc` by
  `0xc580`.

Parser scratch:

- synthetic slot records pushed by `0x11f26` and `0x11efe`;
- active six-byte command record at `0x78299e`;
- final byte, integer word, and optional fractional word parsed by `0xdaf0`.

Firmware bookkeeping:

- `0x782f2c` / `0x782f2d`: dirty and refresh-in-progress flags.
- `0x78298f`: transient full-page-root refresh flag set and cleared inside
  `0xc580`.
- `0x78287b`: font-id/default-symbol side-effect marker set by final `X` and
  default-font paths.
- `0x7828de` / `0x7828a8`: selected slot and selected candidate pointer used
  during font-id/default refresh helpers.

Unknown:

- no parser-to-symbol-word middle edge remains for normal `ESC (` / `ESC )`,
  ordinary finals, final `X`, or final `@`;
- the verified built-in candidate-window path is pinned for primary and
  secondary `0N`, `10U`, `11U`, and fallback cases named above;
- remaining uncertainty is limited to absent cartridge/external resource data
  or untraced variants that change `0x13eb8`, `0x156de`, `0x17708`, or
  `0x14c64` outcomes.

## Writers, Readers, And Output Effect

Writers:

- `0x1201e` and `0x12008` write the slot setup records consumed by `0x1be22`.
- `0x1be22` writes requested symbol words and dirty flags.
- `0x1be22 -> 0x1c066 -> 0x17708` handles font-id selection without accepting
  the ordinary-final computed `X` word.
- `0x1be22 -> 0x1bec8` handles final-`@` table/default-font variants.
- `0x156de` writes active symbol words `0x783144` / `0x783146`.
- `0xc580` copies active symbol words into remembered words and clears
  `0x782f2c` at the common refresh exit.
- `0x1a9be` writes the candidate pointer-list count/cursor state consumed by
  symbol refresh over built-in resources.
- `0x1569c` writes the active candidate-window pointer/count.
- `0x144d2` writes current-font context records.
- `0x14c64` rebuilds maps `0x782f32` / `0x783032`.
- `0xc4fc` and `0xc428` write or select the page-root context slot used by
  later printable text.

Readers and consumers:

- `0xc580` consumes the dirty flags and parser slot after `0x120be`.
- `0xc580` also consumes selected slot `0x782f06` and page-root live flags
  `0x78297f..0x78298e` before choosing refresh-only, install, full-root, or
  remembered-word-only exits.
- `0x1569c` consumes candidate-list cursors and counts to select a class
  window.
- `0x156de` consumes requested/remembered/fallback words.
- `0x14f16` consumes active words while patching maps.
- [symbol-map-patching.md](symbol-map-patching.md#owner-summary) documents the patcher
  branches and table index.
- `0xd04a` / `0x1393a` consume the selected slot, current context, and map for
  later printable bytes.
- `0xc68a` and `0xc6b8` switch `0x782f06` for SI/SO; they select which map a
  later printable byte uses, but do not change queued objects.

Output effect:

- Ordinary symbol-set finals and final-`@` forms can change the context and map
  used by later text.
- Final `X` can select a font by id or preserve prior output when `0x17708`
  exits without a selected record.
- None of these handlers draw immediately; pixels appear only after later
  printable bytes pass through `0xd04a`, compact object queueing, publication,
  and render dispatch.

## Reproduction Contract

For a supplied byte stream, this command family is reproduced when the same
`ESC (` / `ESC )` records produce the same requested symbol words, dirty
flags, active font contexts, character maps, and later printable-byte glyph
selection. The required ROM-visible behavior is:

- Normal primary and secondary commands depend on the synthetic slot records.
  `0x1201e` pushes slot word `0` through `0x11f26` for `ESC (`, while
  `0x12008` pushes slot word `1` through `0x11efe` for `ESC )`. Terminal
  wrapper `0x120be` then calls `0x1be22` and refresh helper `0xc580`.
- Ordinary final bytes compute the requested word exactly as
  `(abs(parameter) << 5) + final - 0x40`, capped by the `0x07ff` parameter
  limit. Slot `0` writes `0x782ef4`; slot `1` writes `0x782f04`. Successful
  ordinary finals set dirty flags `0x782f2c = 1` and `0x782f2d = 1`.
- Final `X` is font-id selection, not an ordinary symbol-set word. `0x1be22`
  restores the previous requested word, sets `0x78287b`, calls
  `0x17708(slot, parameter)`, and enters refresh with dirty flag
  `0x782f2c = 2`. Non-selected exits from `0x17708` preserve the prior
  printable output context.
- Final `@` dispatches by parameter through table `0x1bde2`. Parameters
  `0`, `1`, `2`, and `3` are real ROM behaviors that copy default-symbol
  words or run the default-font path; other parameters restore the previous
  requested word and return without dirty flags.
- Refresh is conditional on `0xc580`, not implied by the parser table alone.
  Dirty flag `1` can call candidate refresh `0x13eb8`; dirty flag `2` skips
  that candidate refresh. Only the currently selected slot `0x782f06` can
  install a page-root context through `0xc428`.
- Candidate refresh resolves requested words against the active resource
  window. `0x1569c` selects the candidate window, `0x156de` filters by
  requested, remembered, or fallback symbol words, `0x144d2` writes current
  context `0x782ee6` or `0x782ef6`, and `0x14c64` rebuilds map `0x782f32` or
  `0x783032`.
- The command family has no immediate pixel output. Later printable bytes use
  selected slot `0x782f06`, current context, and rebuilt map through
  `0xd04a -> 0x1393a -> 0x12f2e`; only that later text path queues compact
  objects and reaches render dispatch.
- SI/SO are consumers of this selected state, not alternate symbol-set
  parsers. `0xc68a` and `0xc6b8` switch `0x782f06`, deciding whether later
  printable bytes use the primary or secondary context and map.

The built-in resource window is pinned for the concrete streams documented
above (`0N`, `10U`, `11U`, final-`@`, and final-`X` cases). Cartridge or
other absent resource records remain external data boundaries; the ROM-local
selection addresses and state transitions are still the same.

## Evidence And Boundaries

Disassembly evidence:

- `generated/disasm/ic30_ic13_payload_dispatch_011f82.lst`:
  `0x12008`, `0x1201e`, and `0x120be`.
- `generated/disasm/ic30_ic13_symbol_set_handler_01be22.lst`:
  `0x1be22..0x1c0a4`, final-byte table `0x1be0a`, and final-`@` table
  `0x1bde2`.
- `generated/disasm/ic30_ic13_font_update_common_00c580.lst`:
  common refresh gate after terminal wrappers.
- `generated/disasm/ic30_ic13_font_context_install_00c428.lst`:
  page-root context slot scan, install, and selected-slot write.
- `generated/disasm/ic30_ic13_font_candidate_activate_01569c.lst`:
  requested/remembered/fallback symbol filtering and active-word writes.
- `generated/disasm/ic30_ic13_font_id_select_017708.lst`:
  final-`X` font-id selection.

Checked-in documentation that composes the downstream path:

- [font-context-metrics.md](font-context-metrics.md#owner-summary)
- [symbol-map-patching.md](symbol-map-patching.md#owner-summary)
- [built-in-resource-scan.md](built-in-resource-scan.md)
- [page-record-storage.md](page-record-storage.md)
- [page-raster-imaging.md](page-raster-imaging.md)

Fixtures named in those notes pin representative streams:

- `0x120be/0x1be22 symbol-set stream updates active words and 0x14f16 glyph maps`
- `symbol-set parser trace feeds active map patches`
- `live parser symbol-set streams select non-Roman built-ins`
- `real final-@ default-table streams select visible built-ins`
- `font-ID built-in selection feeds visible page-record rows`
- `font-ID inline/downloaded selection feeds visible page-record rows`

These fixtures are branch and state-shape evidence for the ROM-derived model.
They are not external printer-output comparisons.
