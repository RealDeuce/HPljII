# Symbol Map Patching Firmware

This note documents the checked-in behavior of map patcher `0x14f16`. It is
the last symbol-set stage before later printable bytes are mapped into glyph
indexes by `0xd04a -> 0x1393a`.

`0x14f16` does not parse PCL and does not draw pixels. It mutates the selected
256-byte character-to-glyph map after `0x14c64` has rebuilt the map from the
selected font record. The patched map is then consumed by following printable
bytes.

Primary evidence:

- `generated/disasm/ic30_ic13_active_object_dispatch_014ba4.lst`:
  `0x14f16..0x14fcc` and the beginning of ROM table `0x14fce`.
- `generated/analysis/ic30_ic13_symbol_set_patch_tables.md`:
  complete extracted patch-table index and byte pairs through final target
  `0x15184`.
- [symbol-set-selection.md](symbol-set-selection.md#owner-summary):
  parser path that writes requested and active symbol words.
- [font-context-metrics.md](font-context-metrics.md#owner-summary):
  `0x14c64` refresh and map rebuild context.

## Owner Summary

This note owns map patcher `0x14f16`, the last selected-symbol stage before
printable bytes map host characters to glyph indices. The patcher is not a
parser, page-object allocator, or renderer. It mutates the selected 256-byte
primary or secondary character map after `0x14c64` has built the base map and
before `0xd04a -> 0x1393a` consumes the map for later text.

Primary route:

- Entry:
  `0x14c64` calls `0x14f16` after the bit-30 resource builder `0x14d9c` or
  bit-30-clear inline/downloaded builders `0x14e24` / `0x14eb6`.
- Roman-8 gate:
  `0x14f16` reads selected candidate `0x7828a8`; candidate byte bit 6 chooses
  symbol reader `0x15890` or `0x158be`. If the normalized selected-font symbol
  is not `0x0115`, the patcher returns without changing the rebuilt map.
- Slot selection:
  selected slot `0x7828de` chooses primary map `0x782f32` and active word
  `0x783144`, or secondary map `0x783032` and active word `0x783146`.
- Patch cases:
  active word `0x0005` copies the upper map half down and clears the upper
  half; active word `0x0015` preserves the lower half and clears the upper
  half; active words in table `0x14fce` apply `(dst, src)` byte-pair copies
  and then clear the upper half; table misses leave the rebuilt map unchanged.
- Downstream consumer:
  later printable bytes read the patched map through `0xd04a -> 0x1393a`.
  Compact renderers consume the captured glyph index and do not know whether
  it came from a base map or a patch.

Field groups:

- Canonical selected state:
  selected candidate `0x7828a8`, selected slot `0x7828de`, active symbol words
  `0x783144` / `0x783146`, and maps `0x782f32` / `0x783032`.
- Derived/cache state:
  selected-slot map flags `0x783132` / `0x783133` and selected-font snapshots
  `0x783148` / `0x783152`.
- Parser scratch:
  none inside `0x14f16`; parser state has already been reduced to active
  symbol words by `0x120be`, `0x1be22`, `0xc580`, and `0x156de`.
- Firmware bookkeeping:
  ROM table cursor and pair loop state local to `0x14f16`, plus candidate
  bit-6 helper selection.
- Unknown:
  no ROM-local branch target is unknown in `0x14f16..0x14fcc`. Remaining
  variation is data variation in selected font records, active symbol words,
  and ROM table pairs.

Output effect:

- The patcher changes future text pixels only by changing the glyph index that
  a later host byte maps to.
- It does not alter compact text already queued before the patch.
- It does not emit page records, publish pages, schedule render work, or draw
  into output buffers.

## Entry Conditions

`0x14c64` calls `0x14f16` after one of the selected-map builders has run:

- bit-30 resource/offset-table contexts use `0x14d9c`;
- bit-30-clear inline/downloaded contexts use `0x14e24` and `0x14eb6`.

`0x14f16` loads selected candidate pointer `0x7828a8` into `A0`, pushes the
candidate longword, and tests bit 6 of the candidate byte:

- bit 6 set: call `0x15890`;
- bit 6 clear: call `0x158be`.

Those helpers return the selected font record's normalized symbol word in
`D7`. If `D7 != 0x0115`, `0x14f16` returns without changing the map. In other
words, the ROM patch-table path applies only to selected fonts whose own
normalized symbol is `8U` / HP Roman-8.

This distinction matters: non-Roman built-in records such as `0N`, `10U`, and
`11U` are selected as different font records. They are not Roman-8 maps patched
through `0x14f16`.

## Map And Active Word Selection

After the Roman-8 gate, `0x14f16` chooses the active map from slot selector
`0x7828de`:

| `0x7828de` | Map base | Active symbol word |
| ---: | ---: | ---: |
| `0` | `0x782f32` | `0x783144` |
| nonzero | `0x783032` | `0x783146` |

The active symbol word is the requested/selected symbol that survived
`0x156de` candidate filtering. It decides whether the Roman-8 base map is left
alone, hard-patched, or table-patched.

## Patch Cases

`0x14f16` has four map outcomes:

- Active word `0x0005` (`0E`, HP Roman Extension):
  copy the upper 128 bytes of the map down over the lower 128 bytes, then
  clear the upper 128 bytes.
- Active word `0x0015` (`0U`, ISO 6 ASCII):
  leave the lower 128 bytes unchanged and clear the upper 128 bytes.
- Active word found in table `0x14fce`:
  apply the selected table's byte pairs, then clear the upper 128 bytes.
- No table hit:
  return without changing the map that `0x14d9c` or `0x14e24` built.

The table-patch loop reads a word count at the patch table target, subtracts
one for the `dbra` loop, then consumes byte pairs:

```text
dst = next byte
src = next byte
map[dst] = map[src]
```

The pair copies an already-initialized glyph index from source character
`src` to destination character `dst`. It does not copy bitmap bytes and it does
not queue any page object.

Whenever the hard-patch or table-patch path reaches the common clear tail,
`0x14f16` clears 128 upper-half map bytes and then writes zero to
`0x783132 + 0x7828de`. That byte is the selected-slot font/map flag updated by
the surrounding `0x14c64` activation path.

## Patch Table Index

`0x14fce` is an 18-entry table of `(symbol word, patch pointer)` pairs. Each
patch pointer starts with a word count followed by `(dst, src)` byte pairs.

| Entry | Word | PCL | Manual name | Target | Pairs |
| ---: | ---: | --- | --- | ---: | ---: |
| 0 | `0x0055` | `2U` | ISO 2 IRV | `0x1503a` | 4 |
| 1 | `0x0025` | `1E` | ISO 4 United Kingdom | `0x15044` | 4 |
| 2 | `0x0006` | `0F` | ISO 25 French | `0x1504e` | 11 |
| 3 | `0x0026` | `1F` | ISO 69 French | `0x15066` | 11 |
| 4 | `0x0007` | `0G` | HP German | `0x1507e` | 11 |
| 5 | `0x0027` | `1G` | ISO 21 German | `0x15096` | 10 |
| 6 | `0x0009` | `0I` | ISO 15 Italian | `0x150ac` | 11 |
| 7 | `0x000b` | `0K` | ISO 14 JIS ASCII | `0x150c4` | 4 |
| 8 | `0x004b` | `2K` | ISO 57 Chinese | `0x150ce` | 4 |
| 9 | `0x0073` | `3S` | ISO 10 Swedish | `0x150d8` | 10 |
| 10 | `0x0013` | `0S` | ISO 11 Swedish | `0x150ee` | 11 |
| 11 | `0x0033` | `1S` | HP Spanish | `0x15106` | 7 |
| 12 | `0x0053` | `2S` | ISO 17 Spanish | `0x15116` | 11 |
| 13 | `0x00d3` | `6S` | ISO 85 Spanish | `0x1512e` | 10 |
| 14 | `0x0093` | `4S` | ISO 16 Portuguese | `0x15144` | 10 |
| 15 | `0x00b3` | `5S` | ISO 84 Portuguese | `0x1515a` | 10 |
| 16 | `0x0004` | `0D` | ISO 60 Norwegian v1 | `0x15170` | 9 |
| 17 | `0x0024` | `1D` | ISO 61 Norwegian v2 | `0x15184` | 10 |

The full `(dst, src)` pairs are data, not control flow. They are extracted in
`generated/analysis/ic30_ic13_symbol_set_patch_tables.md`; the authoritative
ROM table begins at `0x14fce`, and the complete extracted pair data runs
through the final `1D` target at `0x15184`.

## Field Groups

Canonical state:

- `0x7828a8`: selected candidate pointer consumed by `0x14f16`.
- `0x7828de`: selected primary/secondary slot.
- `0x783144` / `0x783146`: active symbol words for primary/secondary slot.
- `0x782f32` / `0x783032`: selected character-to-glyph map bytes consumed by
  later text mapping.

Derived/cache state:

- `0x783132` / `0x783133`: selected-slot font/map flags cleared after a patch
  path modifies and upper-clears the map.
- `0x783148` / `0x783152`: selected-font snapshots written later by `0x1440c`;
  these include active-symbol/map identity so `0x13a48` can skip redundant
  rebuilds.

Parser scratch:

- none inside `0x14f16`. Parser scratch has already been resolved into active
  symbol words by `0x120be`, `0x1be22`, `0xc580`, and `0x156de`.

Firmware bookkeeping:

- selected candidate bit 6 chooses symbol reader `0x15890` or `0x158be`;
- ROM table cursor `A1`, map pointer `A0`, and pair registers `D7`/`D1` are
  local patcher bookkeeping.

Unknown:

- no ROM-local branch target remains unknown in `0x14f16..0x14fcc`;
- physical output is not involved at this boundary;
- remaining variations are data variations in the selected font record,
  active symbol word, or ROM patch pairs.

## Writers, Readers, And Output Effect

Writers:

- `0x14d9c`, `0x14e24`, and `0x14eb6` build the base map before `0x14f16`.
- `0x14f16` copies map bytes, clears upper-half bytes, and clears
  `0x783132 + 0x7828de` on patch paths.
- `0x1440c` later snapshots the selected-font state after the patcher returns.

Readers and consumers:

- `0x14f16` reads selected candidate `0x7828a8`, slot `0x7828de`, active words
  `0x783144` / `0x783146`, and the map selected by the slot.
- `0xd04a -> 0x1393a` later reads `0x782f32` or `0x783032` to convert a host
  byte into the compact glyph index stored in queued text objects.
- Compact renderers later consume that glyph index; they do not know whether
  it came from a base map, a hard patch, or a patch-table pair.

Output effect:

- The patcher changes future text pixels by changing which glyph index a later
  host byte maps to.
- It does not change already queued compact objects.
- It does not emit page records, publish a page, schedule render work, or draw
  into bitmap buffers.

Concrete example:

- A Roman-8 selected built-in record with active word `0x0005` uses the hard
  HP Roman Extension path. The upper map half is copied down, so a later host
  byte such as `0x21` can map to a high-half glyph index before compact text
  queuing. This effect is documented in [resource-rom.md](resource-rom.md#owner-summary)
  and [page-raster-imaging.md](page-raster-imaging.md).

## Reproduction Contract

For a supplied byte stream, this boundary is reproduced when the same selected
font state entering `0x14f16` produces the same primary or secondary
character-to-glyph map consumed by later printable bytes. The required
ROM-visible behavior is:

- `0x14f16` only runs after `0x14c64` has rebuilt a base map through
  `0x14d9c`, `0x14e24`, or `0x14eb6`. It is not a parser, page-object, or
  renderer entry point.
- The selected candidate at `0x7828a8` decides which symbol-reader helper is
  used: candidate byte bit 6 selects `0x15890`; the clear case selects
  `0x158be`. If the returned normalized selected-font symbol is not
  `0x0115`, the patcher returns without changing the rebuilt map.
- Slot `0x7828de` selects both the map and active symbol word:
  primary uses map `0x782f32` with active word `0x783144`; secondary uses
  map `0x783032` with active word `0x783146`.
- Active word `0x0005` copies the upper half of the selected map down over
  the lower half, then clears the upper half. Active word `0x0015` leaves the
  lower half unchanged and clears the upper half.
- Active words found in ROM table `0x14fce` apply `(dst, src)` byte pairs
  from the selected target table, then clear the upper half. A table miss
  leaves the rebuilt base map unchanged.
- Patch paths that reach the common clear tail also clear
  `0x783132 + 0x7828de`. That byte is derived/cache state used by surrounding
  selected-font logic, not a page object.
- The patcher changes future pixels only through later text mapping.
  `0xd04a -> 0x1393a` reads the selected map and stores the derived glyph
  index in queued compact text objects. Objects already queued before the map
  patch keep their previously captured glyph index.

ROM table bytes beginning at `0x14fce` are part of the firmware image and must
be preserved as data. Physical output timing and page publication are outside
this boundary; they start after later printable bytes have consumed the map and
queued page objects.

## Evidence

Disassembly:

- `0x14f16..0x14f38`: selected candidate read, bit-6 symbol-reader choice,
  and Roman-8 gate.
- `0x14f3c..0x14f5e`: primary/secondary map and active-word choice.
- `0x14f5e..0x14f72`: HP Roman Extension upper-half copy.
- `0x14f74..0x14f7e`: ISO 6 ASCII lower-half preserve / upper-half clear.
- `0x14f80..0x14fae`: patch-table lookup and `(dst, src)` pair loop.
- `0x14fae..0x14fc8`: upper-half clear and selected-slot flag clear.
- `0x14fce`: ROM table root. The complete pair data is extracted in
  `generated/analysis/ic30_ic13_symbol_set_patch_tables.md` through final
  target `0x15184`.

Supporting checked-in notes:

- [symbol-set-selection.md](symbol-set-selection.md#owner-summary)
- [font-context-metrics.md](font-context-metrics.md#owner-summary)
- [built-in-resource-scan.md](built-in-resource-scan.md#owner-summary)
- [resource-rom.md](resource-rom.md#owner-summary)
- [page-raster-imaging.md](page-raster-imaging.md)
