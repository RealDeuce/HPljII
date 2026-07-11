# IC30/IC13 Active Symbol-Set Flow

Generated from focused firmware windows around the PCL parser, symbol-set
handler `0x1be22`, common font refresh `0xc580`, and font candidate activation
`0x156de`. This report tracks how host commands such as `ESC (8U` and `ESC
)0B` become the active symbol-set words that rebuild the primary/secondary
character-to-glyph maps.

## Parser Entry Points

| Host command family | Setup handler | Slot setup evidence | Terminal dispatch |
| --- | ---: | --- | --- |
| `ESC (` primary font-designation family | `0x1201e` | calls `0x11f26`, which pushes parser record byte `0x80` and word `0` | final bytes `@`..`^` dispatch to `0x120be` |
| `ESC )` secondary font-designation family | `0x12008` | calls `0x11efe`, which pushes parser record byte `0x80` and word `1` | final bytes `@`..`^` dispatch to `0x120be` |
| terminal wrapper | `0x120be` | calls `0x1be22`, then common refresh `0xc580` | shared path for normal symbol-set selection, `X` font-ID selection, and `@` default/table variants |

## Symbol-Set Word Construction

Routine `0x1be22` pops the parsed command record, reads the final byte into
`D3`, reads the numeric parameter into `D5`, and reads the slot word into
`D4`. For ordinary symbol-set final letters, it computes:

```text
symbol_word = (abs(parameter) << 5) + final_byte - 0x40
requested_slot = 0x782ef4 + 0x10 * slot
word[requested_slot] = symbol_word
```

The `0x10 * slot` stride makes `0x782ef4` the primary requested symbol-set
word and `0x782f04` the secondary requested symbol-set word. This matches
PCL's symbol-set notation: the number is the high component and `A..Z` maps to
suffix values `1..26`.

| PCL code | Parameter | Final byte | Computed word | Manual name in current table |
| --- | ---: | ---: | ---: | --- |
| `0U` | `0` | `0x55` | `0x0015` | ISO 6: ASCII |
| `8U` | `8` | `0x55` | `0x0115` | HP Roman-8 |
| `0E` | `0` | `0x45` | `0x0005` | HP Roman Extension |
| `2U` | `2` | `0x55` | `0x0055` | ISO 2: International Reference Version |

The computed word is intentionally provisional for two final-byte cases. Final
`X` restores the previous requested symbol word and selects a font by ID.
Final `@` runs a numeric sub-dispatch whose documented `3@` case selects
default font characteristics.

## Final-Byte Special Cases

The common dispatch helper `0x33298` reads `{target, match}` longword pairs
until a zero target, then jumps to the default target that follows. The
final-byte table at `0x1be0a` decodes as:

| Match | Target | Firmware effect |
| ---: | ---: | --- |
| `0x58` | `0x01c066` | final `X`: restore the saved requested symbol word, set `0x78287b`, call `0x17708(slot, parameter)` for font-ID selection, then set dirty flag `0x782f2c = 2` and `0x782f2d = 1` |
| `0x40` | `0x01bec8` | final `@`: dispatch the numeric parameter through table `0x1bde2` |
| default | `0x01c0a4` | mark `0x782f2c`/`0x782f2d` dirty using the requested symbol word already stored at `0x782ef4 + 0x10*slot` |

The final `@` numeric table at `0x1bde2` decodes as:

| Parameter | Target | Firmware effect |
| ---: | ---: | --- |
| `3` | `0x01bf74` | default-font path: use `0x1b250`/`0x1ad66` to find or synthesize a candidate, temporarily install `0x7828a4` as the active symbol word for the slot, call `0x1b2fe`, restore the previous active/context state, then mark maps dirty |
| `2` | `0x01bf36` | for primary slot, restore the old requested word; for secondary slot, copy primary requested word `0x782ef4`; then mark maps dirty |
| `1` | `0x01bf0a` | set requested word from `0x782f1c + 8*orientation`, ignoring the primary/secondary slot offset, then mark maps dirty |
| `0` | `0x01bed4` | set requested word from `0x782f1c + 8*orientation + 4*slot`, then mark maps dirty |
| default | `0x01c034` | restore the old requested word and return without setting the dirty flags |

## Default and Fallback Symbol Tables

The LaserJet II Technical Reference documents `ESC (3@` / `ESC )3@` as the
Default Font command and states that it sets all font characteristics except
orientation to the user default font. The same manual text does not name `@0`,
`@1`, or `@2`; the behavior below is therefore firmware-derived.

| Table | Builder | Consumer | Layout | Firmware meaning |
| --- | ---: | ---: | --- | --- |
| `0x782f0c`, `0x782f10`, `0x782f14`, `0x782f18` | `0x1af36` | `0x156de` fallback at `0x1577e` | orientation 0 primary, orientation 0 secondary, orientation 1 primary, orientation 1 secondary | candidate-selection fallback words used after remembered active words `0x782f08`/`0x782f0a` do not satisfy current selection |
| `0x782f1c`, `0x782f20`, `0x782f24`, `0x782f28` | `0x1ac0a` | `0x1be22` final-`@` table | same four-entry orientation/slot layout | default-font command words used by `@0` and `@1`; `@3` uses the candidate found by `0x1b250`/`0x1ad66` more directly |

When `0x1b250` finds a current default candidate, `0x1ac0a` clones its scratch
word `0x7828a4` into all four `0x782f1c..0x782f28` entries. Otherwise it
toggles temporary orientation/list selectors `0x78289f` and `0x78289e`, calls
`0x1ab84`, and records one word per orientation/slot. `0x1af36` performs the
parallel setup for the `0x782f0c..0x782f18` fallback table using `0x1ad66`.
The executable harness now models both `0x1ac0a` branches and both `0x1af36`
fallback branches: current-candidate mode copies `0x7828a4` into the relevant
slots, while synthesized mode records one word per `0x78289f` orientation and
`0x78289e` primary/secondary selector. It also pins the `0x1b250` outer
current-default candidate path: `0x78219c == 0xff` disables it, otherwise
`0x1b50e` supplies a resource address and word, `0x1b4c0` maps that low-24
address back to a canonical candidate slot, and `0x7827ac` decides the
restored `0x78289f` orientation flag. `0x1b50e` is now pinned as a
fast-probe-or-two-pass resolver: requested index `0` can accept `0x1b8ea`,
while the scan path uses `0x1b750`/`0x1b7b2`/`0x1b8b6` to classify range,
special-symbol, and downloaded candidates and to suppress the already-current
Roman-8 slot; non-special requested words can count a Roman-8 candidate twice,
with the duplicate ordinal writing the requested word instead of candidate
word `0x0115`. `0x1ab84` is now pinned as the synthesized default search that
tries `0x1adaa(1)` and `0x1adaa(2)` under the current orientation, flips
`0x78289f` only after both miss, repeats both range searches, and finally
falls through to `0x1ae7e`. It also pins the `0x1ad66` control flow: try
`0x1adaa(1)` for `0x200000..0x3ffffe`, try `0x1adaa(2)` for
`0x400000..0x5ffffe`, and fall back through `0x1ae7e` to either a `0x1b060`
match or the bit-30-selected `0x15890`/`0x158be` base-candidate reader.
`0x1bbfe` is now modeled as the bit-30 dispatcher into `0x15890`/`0x158be`,
and `0x1b060` is modeled as the default-candidate predicate over orientation,
pitch `0x03e8`, height `0x04b0`, style bytes, spacing byte `3`, and
requested-symbol fallback rules. The remaining live-state gap is selection and
filtering over the concrete `0x1a9be` candidate windows, not the table writes,
`@` parser exposure, scanner partitioning, built-in record identities,
`0x1b250`/`0x1b50e` result plumbing, `0x1ab84`/`0x1ad66` list/range/fallback
control flow, or the `0x1bbfe`/`0x1b060` helper logic.

## Refresh and Active Selection

| Step | Firmware evidence | Reproduction meaning |
| ---: | --- | --- |
| 1 | `0x1be22` writes the requested word into `0x782ef4 + 0x10*slot` and marks `0x782f2c`/`0x782f2d` | host symbol-set command changes the requested font-selection criteria, not just a renderer flag |
| 2 | `0x120be` immediately calls `0xc580` | symbol-set commands run the same common refresh used by other font-selection commands |
| 3 | `0xc580` reads the slot from the parser record, checks dirty flag `0x782f2c`, and calls `0x13eb8` and/or `0xc428` depending on current slot state | requested symbol-set changes can rebuild selected font context and reinstall it into page-root font slots |
| 4 | `0x156de` reads `0x782ef4` for primary or `0x782f04` for secondary, uses `0x783f00` as the initial normalized-symbol flag, and scans the active candidate list | the requested PCL word becomes the filter key for built-in/downloaded font candidates |
| 5 | If the requested word has no active match, `0x156de` retries the remembered word from `0x782f08`/`0x782f0a`; if that is unchanged or still misses, it loads the `0x782f0c..18` fallback-table word and normalizes that fallback through `0x15850` | fallback/default handling changes the active word before final pruning |
| 6 | `0x156de` writes the selected active word to `0x783144` for primary or `0x783146` for secondary, then makes a second active-list pass that clears bit 31 on rejects, moves `0x78287c` to the first survivor, and shrinks `0x7827b8` | these are the active words and surviving candidates consumed later by character-map setup |
| 7 | `0x1440c` snapshots `0x783144`/`0x783146` into selected-font state records at `0x783148`/`0x783152` offset `+4` | active object comparison can reject cached state when the symbol set changes |
| 8 | `0x14f16` reads `0x783144` or `0x783146` after base map initialization | Roman-8 built-in maps are patched according to the active requested symbol set before text objects are queued |
| 9 | `0xc580` and the orientation handler `0x10220` copy active words into `0x782f08`/`0x782f0a` | these remembered values are fallback/default inputs if current candidate selection cannot satisfy the requested word |

## Compatibility Pair Table

At `0x15742`, candidate symbol word `D7` is swapped into the high word and
requested symbol word `D3` is copied into the low word, then compared against
longwords at `0x15840`. These pairs allow a candidate with one symbol-set word
to satisfy a related requested word.

| Entry | Candidate word | Candidate code | Requested word | Requested code |
| ---: | ---: | --- | ---: | --- |
| 0 | `0x0001` | `0A` | `0x000d` | `0M` |
| 1 | `0x000d` | `0M` | `0x0001` | `0A` |
| 2 | `0x0002` | `0B` | `0x000c` | `0L` |

## Absolute JSR Call-Site Scan

| Target | Role | Absolute JSR references |
| ---: | --- | --- |
| `0x0120be` | symbol-set terminal wrapper | (none) |
| `0x01be22` | PCL symbol-set word handler | `0x0120c2` |
| `0x017708` | primary/secondary font ID selection | `0x01c08a` |
| `0x01ac0a` | default-font command symbol table builder | `0x01b056` |
| `0x01af36` | font-selection fallback symbol table builder | `0x01b050` |
| `0x01b04c` | default/fallback symbol table refresh wrapper | `0x00e84c`, `0x016dac`, `0x016ea2`, `0x018b84`, `0x019e16`, `0x01a908`, `0x01ad5c` |
| `0x00c580` | common font/symbol update refresh | `0x00c3dc`, `0x00c3fe`, `0x011e38`, `0x012050`, `0x012064`, `0x012078`, `0x01208c`, `0x0120a0`, `0x0120b4`, `0x0120c8`, ... (12 total) |
| `0x013eb8` | selected font/object refresh from common updater | `0x00c612`, `0x00c634`, `0x00c65a`, `0x00e68a`, `0x00e6ec`, `0x00e7d2`, `0x00e81e`, `0x01032a`, `0x010334` |
| `0x00c428` | current-font context installer | `0x00e72c`, `0x00e7c8`, `0x01c67a`, `0x01cf26`, `0x01ea3e`, `0x031734`, `0x031832` |
| `0x0156de` | font candidate filter against requested symbol set | `0x013f08` |
| `0x015850` | requested symbol-set normalizer | `0x014916`, `0x015702`, `0x01579c` |
| `0x015890` | built-in candidate symbol-set reader | `0x013aea`, `0x014448`, `0x014b5e`, `0x014c96`, `0x014cde`, `0x014f24`, `0x015724`, `0x0157da`, `0x0177e8`, `0x01949a`, ... (16 total) |
| `0x0158be` | inline/downloaded candidate symbol-set reader | `0x013b52`, `0x014484`, `0x014c1e`, `0x014f2c`, `0x01572c`, `0x0157e2`, `0x01781e`, `0x0191bc`, `0x019740`, `0x01af22`, ... (13 total) |
| `0x014f16` | active character-map symbol patcher | `0x014d8c` |

## State Address References

| Address | Role | Longword literal references |
| ---: | --- | --- |
| `0x0078299a` | parser continuation handler pointer | `0x011788`, `0x011af8`, `0x011b06`, `0x011b36`, `0x011eae`, `0x011ec0`, `0x011ed2`, `0x011ee4`, `0x011ef6` |
| `0x0078299e` | parser command-record stack pointer | `0x002f18`, `0x00c39a`, `0x00c3ca`, `0x00c3d0`, `0x00c3e4`, `0x00c3f4`, `0x00c58a`, `0x00c592`, `0x00c6f6`, `0x00c6fe`, ... (146 total) |
| `0x00782ef4` | primary requested symbol-set word | `0x0149e0`, `0x0156ec`, `0x01be94`, `0x01beac`, `0x01bee4`, `0x01bf1a`, `0x01bf4a`, `0x01bf66`, `0x01bf6c`, `0x01c044`, ... (11 total) |
| `0x00782f04` | secondary requested symbol-set word | `0x0149ec`, `0x0156f4` |
| `0x0078289e` | temporary primary/secondary default-font slot selector | `0x01ac4a`, `0x01ac62`, `0x01ac80`, `0x01ac98`, `0x01ad0e`, `0x01ad36`, `0x01ade0`, `0x01af90`, `0x01afb8`, `0x01afe6`, ... (17 total) |
| `0x0078289f` | temporary orientation/font-list selector | `0x01ab8e`, `0x01abd0`, `0x01ac44`, `0x01ac7a`, `0x01acc0`, `0x01ad08`, `0x01adba`, `0x01ae8a`, `0x01aeca`, `0x01af48`, ... (32 total) |
| `0x007828a0` | temporary or selected candidate-list pointer | `0x01ab98`, `0x01abaa`, `0x01abbe`, `0x01abe2`, `0x01abf6`, `0x01acd4`, `0x01acee`, `0x01ad24`, `0x01ad4c`, `0x01ad70`, ... (35 total) |
| `0x007828a4` | candidate/default symbol-set word scratch | `0x01ac1a`, `0x01ac24`, `0x01ac2e`, `0x01ac38`, `0x01ac56`, `0x01ac6e`, `0x01ac8c`, `0x01aca4`, `0x01accc`, `0x01ace6`, ... (32 total) |
| `0x007828a8` | selected candidate slot pointer | `0x00e78e`, `0x013a68`, `0x013a76`, `0x013afe`, `0x013f92`, `0x0143fc`, `0x01442c`, `0x014438`, `0x014474`, `0x0144f2`, ... (37 total) |
| `0x00783144` | primary active selected symbol-set word | `0x00c67a`, `0x00cc38`, `0x00e2da`, `0x00e554`, `0x00e692`, `0x00e768`, `0x00e7da`, `0x0103aa`, `0x013ad6`, `0x013b3e`, ... (35 total) |
| `0x00783146` | secondary active selected symbol-set word | `0x00cc42`, `0x00e6f6`, `0x00e828`, `0x0103b4`, `0x0144ba`, `0x0149f0`, `0x014cee`, `0x014f5a`, `0x0157b6`, `0x01b340`, ... (12 total) |
| `0x00782f08` | primary remembered active symbol-set fallback | `0x00c66e`, `0x00cc3c`, `0x00e696`, `0x00e7ac`, `0x00e7de`, `0x0103ae`, `0x01576a` |
| `0x00782f0a` | secondary remembered active symbol-set fallback | `0x00cc46`, `0x00e6fa`, `0x00e82c`, `0x0103b8`, `0x015772` |
| `0x00782f0c` | font-selection fallback symbol table: orientation 0 primary | `0x015780`, `0x01af56`, `0x01afaa`, `0x01aff6` |
| `0x00782f10` | font-selection fallback symbol table: orientation 0 secondary | `0x01af70`, `0x01afd2`, `0x01b00e` |
| `0x00782f14` | font-selection fallback symbol table: orientation 1 primary | `0x01b02c` |
| `0x00782f18` | font-selection fallback symbol table: orientation 1 secondary | `0x01b044` |
| `0x00782f1c` | `@0`/`@1` default-font table: orientation 0 primary | `0x01ac1e`, `0x01ac5a`, `0x01bef6`, `0x01bf2c` |
| `0x00782f20` | `@0`/`@1` default-font table: orientation 0 secondary | `0x01ac28`, `0x01ac72` |
| `0x00782f24` | `@0`/`@1` default-font table: orientation 1 primary | `0x01ac32`, `0x01ac90` |
| `0x00782f28` | `@0`/`@1` default-font table: orientation 1 secondary | `0x01ac3c`, `0x01aca8` |
| `0x00782f2c` | font/symbol update dirty flag | `0x00c598`, `0x00c5ce`, `0x00c682`, `0x00c76c`, `0x00c7d4`, `0x00c834`, `0x00c890`, `0x00c91c`, `0x00c97e`, `0x00ce6c`, ... (14 total) |
| `0x00782f2d` | font/symbol update in-progress flag | `0x00c468`, `0x00c490`, `0x00c49c`, `0x00c4d0`, `0x00c4dc`, `0x00c692`, `0x00c6b0`, `0x00c6c0`, `0x00c6e4`, `0x00c774`, ... (27 total) |
| `0x00782f06` | primary/secondary selected text slot | `0x00c5dc`, `0x00c600`, `0x00c698`, `0x00c6aa`, `0x00c6c6`, `0x00c6de`, `0x00cbe4`, `0x00d094`, `0x00e2ae`, `0x00e2d0`, ... (42 total) |
| `0x007828de` | font-selection slot currently being rebuilt | `0x00e77c`, `0x013a52`, `0x013acc`, `0x013b34`, `0x013ec0`, `0x013ed6`, `0x013fa0`, `0x014416`, `0x0144b2`, `0x0144dc`, ... (48 total) |

## Current Reproduction Contract

- Parse primary `ESC (` and secondary `ESC )` symbol-set commands into PCL
  words with `(number << 5) + suffix`, where suffix `A..Z` is `1..26`, except
  for final `X` and `@` special cases.
- Treat `ESC (#X` / `ESC )#X` as font-ID selection through `0x17708`; it
  restores the prior requested symbol word rather than accepting the
  provisional `X` symbol word.
- Treat `ESC (3@` / `ESC )3@` as default-font selection; the firmware also
  implements `@` parameters `0..2` as table/copy variants documented above.
- `tools/render_fixture_harness.py` now traces host-visible `ESC (7X`, `ESC
  )0@`, `ESC (1@`, `ESC )2@`, `ESC (3@`, and `ESC )3@` streams through parser
  setup handlers `0x1201e`/`0x12008` and terminal handler `0x120be`, then
  checks the modeled `0x1be22` special-case targets `0x1c066`, `0x1bed4`,
  `0x1bf0a`, `0x1bf36`, and `0x1bf74`.
- Reproduce `0x1ac0a` and `0x1af36` table writes before applying `@0`/`@1` or
  font-selection fallback behavior; the harness now checks the
  current-candidate and synthesized-candidate table shapes.
- Reproduce `0x1a9be` scanner-side candidate-list partitioning before
  default-font searches: every accepted record increments `0x78278e`; class
  `1` increments `0x782790` and splits low built-in-resource candidates into
  `0x782792` and cartridge/extension-range candidates into `0x782794`; class
  `0` increments `0x782798` and splits the same ranges into `0x78279a` and
  `0x78279c`; the cursor windows at `0x7827a0..0x7827b4` advance cumulatively
  across those partitions.
- For the verified `IC32,IC15` resource ROM, the built-in scan contributes 24
  concrete `HEAD`-path records: twelve class `0` and twelve class `1`, all in
  the low built-in resource window. The extension-range counters stay zero
  until cartridge/external resource ranges are scanned.
- Reproduce `0x1569c` active-list setup: `0x782da3 == 0` selects class-zero
  pointer/count `0x7827ac`/`0x782798`, while nonzero selects class-one
  pointer/count `0x7827a0`/`0x782790`; for the verified built-ins these become
  `0x782354`/`12` and `0x782324`/`12`, and selected entries are marked with
  active bit `0x80000000`.
- Reproduce `0x156de` as a two-pass active-list filter: find a satisfiable
  requested/remembered/fallback symbol word using exact match, normalized
  Roman-8 match, or the compatibility pairs at `0x15840`; then clear the
  active bit on rejected entries, move `0x78287c` to the first retained slot,
  and write the retained count to `0x7827b8`. The harness now pins class-zero
  primary `0x0115` over the real built-ins as slots
  `0x782354/0x782364/0x782374`, and a class-one secondary miss falling through
  to fallback word `0x000e` as slots `0x782330/0x782340/0x782350`.
- Reproduce `0x1ad66` as a three-stage default-font candidate search: range
  class 1, then range class 2, then `0x1ae7e` fallback. Range hits filter
  candidate high-nibble flags by primary/secondary slot mask and low-24-bit
  resource address range before `0x1bbfe` dispatches symbol-word reads to
  `0x15890` for bit-30 offset-table resources or `0x158be` for bit-30-clear
  fixed-record resources. Fallback first accepts a `0x1b060` match, where the
  helper validates orientation, pitch, height, style, and spacing, then
  accepts either exact requested-symbol matches or Roman-8 fallback for
  non-excluded requested words; accepted `0x1b060` candidates write the
  requested word from `0x7821a0` to `0x7828a4`.
- Treat `0x782ef4`/`0x782f04` as requested criteria and `0x783144`/`0x783146`
  as the active post-selection words.
- Rebuild the selected primary/secondary character-to-glyph map after
  symbol-set changes, then apply the `0x14f16` patch rules documented in
  `ic30_ic13_symbol_set_patch_tables.md`; `tools/render_fixture_harness.py`
  now drives `ESC (2U` and `ESC )0E` through both the ROM parser trace and
  symbol-set stream model, then applies the resulting `0x0055` patch-table and
  `0x0005` Roman Extension map rules to the `LINE_PRINTER` base map.
- Do not feed host bytes directly to `0x1f354`; the queued compact glyph byte
  must come from the active map selected by this flow.
