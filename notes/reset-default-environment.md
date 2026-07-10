# Reset And Default Environment

This note is the semantic contract for LaserJet II software reset, default
environment records, retained-record producers, and the reset-to-publication
boundary that affects rendered output.

Status: composed for `ESC E` reset from parser dispatch through current-page
publication, environment rebuild, parser/data-chain reset, default-record
consumption, and representative rendered output. It also composes the
producer side for the reset-consumed defaults `0x78219d`, `0x78219e`, and
`0x7821a2`. The low-level ledger remains in
`generated/analysis/ic30_ic13_esc_e_reset_flow.md`,
`notes/semantic-state-model.md`, and the generated disassembly files listed
below.

## Evidence

- `generated/analysis/ic30_ic13_esc_e_reset_flow.md`
- `generated/disasm/ic30_ic13_esc_e_reset_00cc52.lst`
- `generated/disasm/ic30_ic13_esc_e_environment_reset_00cda2.lst`
- `generated/disasm/ic30_ic13_esc_e_metric_refresh_00cbd4.lst`
- `generated/disasm/ic30_ic13_esc_e_parser_state_reset_00e146.lst`
- `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`
- `generated/disasm/ic30_ic13_default_env_load_005e80.lst`
- `generated/disasm/ic30_ic13_default_env_menu_update_004fb0.lst`
- `generated/disasm/ic30_ic13_default_env_record_maintenance_0056c2.lst`
- `generated/disasm/ic30_ic13_retained_record_bulk_load_005a16.lst`
- `generated/disasm/ic30_ic13_nvram_default_record_commit_0096c4.lst`
- `generated/disasm/ic30_ic13_nvram_serial_bit_helpers_009860.lst`
- `notes/page-raster-imaging.md`
- `notes/pcl-parser-firmware.md`
- `notes/semantic-state-model.md`

Primary fixtures:

- `ESC E stream publishes valid page root and resets environment/parser state`
- `ESC E stream clears missing page root without publication`
- `host-fetched ESC E clears missing page root without publication`
- `mixed printable/reset page-record stream queues through 0x1387c before reset`
- `mixed printable/reset page-record finalization publishes bridged record`
- `addressed printable reset publishes rendered page record`
- `mixed printable/reset publication records 0xff1e pool header defaults`
- `host-fetched reset publication preserves 0xff1e pool header defaults`
- `0x5e80 -> 0xcda2 reset consumes default record outputs`
- `0xcfea/0xcf52/0x104d8 convert default line spacing to reset VMI`

## Owner Summary

Concept: this note owns `ESC E` software reset and its default-environment
inputs from parser dispatch to page-root publication, environment rebuild,
parser/data-chain reset, default-record consumption, and representative
rendered output. It also owns the ROM producers for the reset-consumed default
fields `0x78219d`, `0x78219e`, and `0x7821a2`.

Primary route:

- Parser dispatch sends `ESC E` to `0xcc52`.
- Reset route:
  `0xcc52 -> 0xcc70 -> 0xf34a -> 0xff1e/no-root clear -> 0x9ac2
  -> 0xcda2 -> 0xcbd4 -> 0xe146`.
- Default-consumer route:
  `0x5e80/default producer -> 0x78219d/0x78219e/0x7821a2 -> 0xcda2`.
- Environment rebuild route:
  `0xcda2 -> page/control records 0x780f02 -> HMI/VMI/top/margin/parser
  defaults -> raster/page-derived state`.
- Parser/data-chain reset route:
  `0xe146 -> 0x782d76/0x782d7a/0x782c1e..0x782c6d/0x783196..0x783199`.
- Visible output then belongs to the publication/render owners if a valid
  current root existed before reset; missing-root reset creates no published
  page record.

Field groups:

- Canonical reset inputs: defaults `0x78219d`, `0x78219e`, `0x7821a2`, and
  reset/environment gate `0x7810b2`.
- Canonical default producers: selector `0x7822d5`, compact backing records
  under `0x780eda`, staged bytes `0x782283` / `0x782290`, and menu/update
  writers `0x5060`, `0x50be`, and `0x52ba`.
- Canonical page/control pool: records at `0x780f02`, bucket-array pointers
  `+0x1c`, current root `0x78297a`, published root `0x780ea6`, and
  publication flag `0x782996`.
- Canonical parser/data-chain reset state: scratch pointer `0x782a26`,
  cursor-stack pointer `0x782d36`, data-chain frame pointer `0x782d76`,
  current macro record pointer `0x782d7a`, parser/control records
  `0x782c1e..0x782c6d`, and text accumulation bytes `0x783196..0x783199`.
- Derived/cache reset state: HMI `0x78315c`, VMI `0x783160`, top offset
  `0x782dce`, layout scratch `0x782dd0`, and raster block `0x783170`.
- Retained/default bookkeeping: retained-record flags `0x780eba..0x780ed8`,
  maintenance counters `0x780ef0`, buffers `0x782252..0x782270`, and serial
  retained-storage helpers using `$a400` and `$8c01`.
- Firmware bookkeeping: reset pending bytes `0x782997` / `0x782998`,
  reset-cleared latches, reset-set latches `0x782a6d` / `0x783191`, active
  symbol snapshots, and reset completion byte `0x782a93`.
- Unknown: physical retained-storage identity behind `$a400` / `$8c01`,
  external panel/service protocol for `$8000.w`, and manual-facing names for
  reset latches.

Writers and readers:

- `0xcc52` calls reset publication/environment helper `0xcc70`, metric refresh
  `0xcbd4`, and parser/data-chain reset `0xe146`, then clears `0x782a93`.
- `0xcc70` flushes pending text, publishes or clears the current page root,
  waits through `0x9ac2`, handles the reset gate, calls `0xcda2`, and rebuilds
  raster/page-derived state.
- `0xcda2` consumes defaults and current-font context, rebuilds page/control
  records, copies default environment fields, recomputes HMI/VMI, and resets
  bookkeeping bytes.
- `0xcbd4` consumes current-font context and active symbol words to refresh
  HMI and active-symbol snapshots.
- `0xe146` consumes and resets parser/data-chain records, freeing active
  data-chain chunks where needed.
- `0x5e80`, menu/update handlers, retained-record maintenance, and NVRAM
  helpers produce or preserve the default fields consumed by later reset.

Output effect:

- `ESC E` publishes ROM-derived rows only when a valid active page root exists
  before reset.
- Missing-root reset takes the `0xff1e` no-root/current-root clear exit and
  produces no published page record.
- Reset environment changes affect later output by replacing HMI, VMI, page
  geometry, paper/source header state, parser/data-chain state, raster state,
  and font/context snapshots before following bytes are parsed.
- Default-record producers have no direct pixels; their visible effect occurs
  when a later reset consumes `0x78219d`, `0x78219e`, or `0x7821a2`.

Evidence and boundaries:

- Disassembly evidence is in `ic30_ic13_esc_e_reset_00cc52.lst`,
  `ic30_ic13_esc_e_environment_reset_00cda2.lst`,
  `ic30_ic13_esc_e_metric_refresh_00cbd4.lst`,
  `ic30_ic13_esc_e_parser_state_reset_00e146.lst`,
  `ic30_ic13_page_root_finalize_00ff1e.lst`, and the default/retained-record
  listings named above.
- Fixture evidence is named in the Primary fixtures list above; those streams
  pin valid-root publication, missing-root no-publication, page-record bridge,
  default-field production/consumption, and VMI conversion.
- No unresolved ROM-local middle edge remains for `ESC E` reset from parser
  dispatch through publication/no-publication, environment rebuild, parser
  reset, and default-field consumption. Remaining boundaries are external
  retained-storage identity, panel/service protocol, and manual names for
  reset latches.

## Reset Default Outcome Matrix

This matrix composes reset/default behavior into the byte-stream-to-output
model. It separates the `ESC E` page-boundary effect from the default
producers and rebuilt state that later commands consume.

`ESC E` with a valid current page root:

- ROM path:
  parser dispatch reaches `0xcc52`; reset helper `0xcc70` calls `0xf34a` and
  `0xff1e` before environment rebuild.
- State category:
  canonical page/control pool state, firmware bookkeeping, and derived render
  state after publication.
- Writers:
  `0xff1e` publishes the valid root from `0x78297a` into protected pool state
  `0x780ea6`, sets publication flag `0x782996`, and clears current-root state
  before `0xcda2` rebuilds defaults.
- Readers / consumers:
  publication bridge `0x1ed84 -> 0x1edc6`, active render entry `0x1ef6a`,
  and later scheduler/render owners consume the published pre-reset page
  record.
- Output effect:
  pre-reset page objects can produce ROM-derived pixels. The reset command is
  the boundary that finalizes those objects before clearing/rebuilding parser
  and environment state.
- Evidence:
  `generated/disasm/ic30_ic13_esc_e_reset_00cc52.lst`,
  `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`, fixtures
  `ESC E stream publishes valid page root and resets environment/parser state`,
  `mixed printable/reset page-record finalization publishes bridged record`,
  and `addressed printable reset publishes rendered page record`.

`ESC E` with no current page root:

- ROM path:
  `0xcc52 -> 0xcc70 -> 0xf34a -> 0xff1e`.
- State category:
  firmware bookkeeping and canonical reset state.
- Writers:
  `0xff1e` takes its no-root/current-root clear exit; `0xcda2`, `0xcbd4`, and
  `0xe146` still rebuild reset state afterward.
- Readers / consumers:
  later parser, font, geometry, and raster handlers consume the rebuilt state;
  no publication or render consumer receives a new page record from this
  branch.
- Output effect:
  no pixels are produced by the reset itself when there is no valid root to
  publish.
- Evidence:
  fixtures `ESC E stream clears missing page root without publication` and
  `host-fetched ESC E clears missing page root without publication`;
  publication behavior in
  [publication-commands.md](publication-commands.md#publication-outcome-matrix).

Environment rebuild:

- ROM path:
  `0xcc70 -> 0xcda2 -> 0xcbd4`.
- State category:
  canonical reset inputs, derived/cache reset state, and firmware
  bookkeeping.
- Writers:
  `0xcda2` rebuilds four page/control records at `0x780f02`, bucket-array
  pointers `+0x1c`, scratch/cursor-stack pointers, reset environment word
  `0x782da4`, gated byte `0x782da6`, reset pending bytes
  `0x782997/0x782998`, HMI `0x78315c`, VMI `0x783160`, top offset
  `0x782dce`, and raster state block `0x783170`. `0xcbd4` refreshes HMI and
  active-symbol snapshots.
- Readers / consumers:
  later printable placement, font selection, VFC/layout, raster transfer,
  rectangle/rule setup, and publication paths consume the rebuilt fields.
- Output effect:
  no immediate pixels unless a pre-reset root was already published; the
  rebuilt defaults change how following host bytes are parsed, positioned,
  queued, and rendered.
- Evidence:
  `generated/disasm/ic30_ic13_esc_e_environment_reset_00cda2.lst`,
  `generated/disasm/ic30_ic13_esc_e_metric_refresh_00cbd4.lst`, and fixture
  `0x5e80 -> 0xcda2 reset consumes default record outputs`.

Parser/data-chain reset:

- ROM path:
  `0xcc52 -> 0xe146`.
- State category:
  canonical parser/data-chain reset state and firmware bookkeeping.
- Writers:
  `0xe146` resets data-chain pointer `0x782d76`, clears macro/current record
  pointer `0x782d7a`, macro id `0x783164`, alternate/data bytes
  `0x782c18/0x782c19`, overlay/parser byte `0x782a92`, text accumulation bytes
  `0x783196..0x783199`, parser/control records `0x782c1e..0x782c6d`, and
  parser/control cursor `0x782c6e`.
- Readers / consumers:
  host-byte parser loop, macro/data-chain replay, transparent/raster/font
  delayed payload setup, and command-family handlers consume the cleared
  parser state after reset returns.
- Output effect:
  no direct pixels; the visible effect is that following bytes start from the
  reset parser and replay state instead of inherited parser/data-chain state.
- Evidence:
  `generated/disasm/ic30_ic13_esc_e_parser_state_reset_00e146.lst`,
  parser ownership in
  [pcl-parser-core.md](pcl-parser-core.md#reproduction-contract), and macro
  replay ownership in
  [macro-data-chain.md](macro-data-chain.md#macro-replay-outcome-matrix).

Default record production:

- ROM path:
  `0x5e80`, menu/update handlers `0x5060`, `0x50be`, `0x52ba`, retained-record
  maintenance `0x56c2`, `0x571e`, and `0x5a62`.
- State category:
  canonical default producers, retained/default bookkeeping, and
  hardware/external state for retained storage.
- Writers:
  selected backing records under `0x780eda`, staged bytes `0x782283` /
  `0x782290`, and reset-consumed defaults `0x78219d`, `0x78219e`, and
  `0x7821a2`.
- Readers / consumers:
  `0xcda2` consumes the defaults during reset; retained-record commit/read
  paths consume dirty flags and buffers when preserving those defaults.
- Output effect:
  no direct pixels. Defaults become visible only through a later reset that
  copies them into layout, paper/environment, VMI, status, and parser state
  consumed by following page-building commands.
- Evidence:
  `generated/disasm/ic30_ic13_default_env_load_005e80.lst`,
  `generated/disasm/ic30_ic13_default_env_menu_update_004fb0.lst`,
  `generated/disasm/ic30_ic13_default_env_record_maintenance_0056c2.lst`,
  `generated/disasm/ic30_ic13_retained_record_bulk_load_005a16.lst`, and
  fixture `0x5e80 -> 0xcda2 reset consumes default record outputs`.

State grouping for this matrix:

- Canonical state:
  defaults `0x78219d/0x78219e/0x7821a2`, reset gate `0x7810b2`,
  page/control records `0x780f02`, current root `0x78297a`, published root
  `0x780ea6`, parser/data-chain records, and default backing records under
  `0x780eda`.
- Derived/cache state:
  HMI `0x78315c`, VMI `0x783160`, top offset `0x782dce`, layout scratch,
  raster block `0x783170`, and published render-record state after `0x1ed84`.
- Parser scratch:
  parser/control records `0x782c1e..0x782c6d`, parser/control cursor
  `0x782c6e`, alternate/data bytes, delayed payload state, and macro/data-chain
  frame pointers cleared by `0xe146`.
- Firmware bookkeeping:
  publication flag `0x782996`, reset pending bytes `0x782997/0x782998`,
  reset latches, retained-record dirty flags, maintenance counters, and reset
  completion byte `0x782a93`.
- Hardware/external state:
  physical retained-storage identity behind `$a400` / `$8c01` and the external
  panel/service source behind `$8000.w`.
- Unknown:
  only manual-facing names for several reset latches and external device
  identities remain unknown. No ROM-local reset/default producer, consumer,
  publication, parser-reset, or later-output middle edge remains open for the
  documented paths.

## Field Groups

Canonical reset inputs:

- `0x78219d`: default byte copied to reset environment word `0x782da4` by
  `0xcda2`.
- `0x78219e`: default line-spacing word converted into reset VMI
  `0x783160`.
- `0x7821a2`: default environment/paper byte copied to `0x782da6` when reset
  gate `0x7810b2` permits it; `0xcc70` also copies it to `0x780e8f` when
  `0x780e3c == 1`.
- `0x7810b2`: reset/environment gate controlling the `0x7821a2 -> 0x782da6`
  reload and early parser-mode clearing.

Canonical default producers:

- `0x7822d5`: selector for compact default records. The ROM scales it through
  `0x332ee(..., 3)` and selects backing record
  `0x780eda + 2 * scaled_index`.
- Backing record byte `+0`: source for staged byte `0x782283` and canonical
  default `0x78219d`.
- Backing record word `+2`: source for staged line spacing `0x782290` and
  canonical word `0x78219e`.
- Backing record byte `+5`: bit 2 derives canonical byte `0x7821a2` as
  `0x80` or `0`.
- Menu/update handlers `0x5060`, `0x50be`, and `0x52ba` write the selected
  backing record and the canonical defaults.

Canonical page/control pool:

- `0x780f02`: four 0x6c-byte page/control records rebuilt by `0xcda2`.
- Record `+0x1c`: bucket-array pointer rebuilt as `0x7810bc + 0x400*n`.
- `0x78297a`: current page-root pointer consumed by `0xff1e`.
- `0x780ea6`: published page/control record pointer written by `0xff1e`.
- `0x782996`: publication flag set by `0xff1e`.

Canonical parser/data-chain reset state:

- `0x782a26`: reset to scratch base `0x782a2a`.
- `0x782d36`: reset to cursor-stack base `0x782c96`.
- `0x782d76`: reset to data-chain base `0x782d3e`; `0x782d7a` is cleared.
- `0x782c1e..0x782c6d`: eight 10-byte parser/control records cleared by
  `0xe146`; `0x782c6e` is reset to `0x782c1e`.
- `0x783196..0x783199`: text accumulation bytes cleared by `0xe146`.

Derived/cache reset state:

- `0x78315c`: reset HMI recomputed from current-font context `0x782ee6` by
  `0xcda2` and refreshed again by `0xcbd4`.
- `0x783160`: reset VMI derived from `0x78219e` through `0xcfea`, `0xcf52`,
  and `0x104d8`.
- `0x782dce`: top offset recomputed as `0x96 - 0x782dbe`; `0x782dd0` is
  cleared.
- `0x783170`: raster state block reinitialized by `0xcc70`; byte `+0x12`,
  word `+0x00`, and long `+0x0a` are cleared, scale-minus-one `+0x08 = 3`,
  scale `+0x0e = 4`, and word `+0x10` derives from page extent.

Retained/default-record maintenance state:

- `0xba3e` and `0xba44`: ROM fallback tables used by record maintenance and
  cold-reset paths.
- `0x780ede`: bank/status word scanned by `0x56c2` for bit 15.
- `0x780ef0`: packed rotation/maintenance counter updated by `0x571e`.
- `0x780eba..0x780ed8`: dirty flags for retained records.
- `0x782252..0x782270`: readback buffer used by `0x96c4` / `0x97e4`.
- `$a400`: serial control/output register written by `0x9a4a`.
- `$8c01`: serial input/status byte read by `0x994e`.
- `$8000.w & 0xff`: debounced panel/service byte source read by `0xa3ca`.

Firmware bookkeeping:

- `0x782997` and `0x782998`: set when the gated `0x7821a2 -> 0x782da6`
  reload runs.
- `0x782990`, `0x78297e`, `0x782c72`, `0x782c73`, `0x783184`, `0x783185`,
  `0x782f2c`, `0x78318f`, and `0x783190`: cleared during reset.
- `0x782a6d` and `0x783191`: set during reset.
- `0x782f06`: cleared by `0xcbd4`.
- `0x783144` and `0x783146`: active symbol words copied to snapshots
  `0x782f08` and `0x782f0a`.
- `0x783164`, `0x782c18`, `0x782c19`, and `0x782a92`: cleared by `0xe146`.
- `0x782a93`: reset completion/status byte cleared by top-level `0xcc52`.

Unknown/provenance:

- The physical retained-storage device behind `$a400` / `$8c01` remains
  unidentified.
- The external protocol or device that supplies the debounced `$8000.w` panel
  byte is board-facing, not ROM-resolved.
- Manual-facing names for several reset latches are inferred from ROM effects.

## Writers

- Parser dispatch sends `ESC E` to handler `0xcc52`.
- `0xcc52..0xcc6e` calls `0xcc70`, `0xcbd4`, and `0xe146`, then clears
  `0x782a93`.
- `0xcc70..0xcd7a` flushes pending text through `0xf34a`, publishes or clears
  the current page root through `0xff1e`, waits through `0x9ac2`, handles the
  `0x7810b2` reset gate, calls `0xcda2`, and rebuilds raster/page-derived
  state.
- `0xcda2..0xcf50` rebuilds page/control records, default environment copies,
  parser scratch, VMI/HMI, and reset bookkeeping bytes.
- `0xcbd4..0xcc50` refreshes HMI and active-symbol snapshots from current-font
  context state.
- `0xe146..0xe1e2` resets parser/data-chain records and clears parser/text
  accumulation state.
- `0x5e80..0x5f94` copies selected default-record fields into `0x78219d`,
  `0x78219e`, and `0x7821a2`.
- `0x5060`, `0x50be`, and `0x52ba` update backing records and canonical
  defaults.
- `0x56c2`, `0x571e`, and `0x5a62` maintain default-record banks and ROM-table
  fallback records.
- `0x96c4` commits dirty retained records; `0x97e4` reads retained records;
  `0x9a4a` emits software-visible serial phase pairs to `$a400`.

## Reset Handler Boundaries

The software reset path is ordered by disassembly, not by fixture output:

- `0xcc52..0xcc6e`: top-level `ESC E` handler. It calls reset publication and
  environment rebuild helper `0xcc70`, refreshes selected-font metrics through
  `0xcbd4`, resets parser/data-chain state through `0xe146`, clears
  `0x782a93`, and returns.
- `0xcc70..0xcc98`: if reset gate `0x7810b2` is clear, clear alternate/data
  byte `0x782c18`; flush pending text through `0xf34a`; publish or clear the
  current page root through `0xff1e`; then call `0x9ac2`.
- `0xcc9e..0xccd2`: when `0x7810b2` is clear and status byte `0x780e3c` is
  `1`, copy default environment byte `0x7821a2` to `0x780e8f` and signal
  `0x780e26` through `0x9b5e`.
- `0xccd6..0xcd7a`: clear orientation byte `0x782da3`, call environment reset
  `0xcda2`, refresh page length/geometry helpers, rebuild top offset, margins,
  VFC caches, default VFC table, orientation geometry, and reset raster state
  block `0x783170`.
- `0xcd7c..0xcd82`: if the gate/status branch requires the font/resource path,
  call `0x1bba6` before rejoining the `0xccd6` rebuild.

`0xcda2` is the reset environment writer:

- `0xcdaa..0xcddc`: iterate four page/control records at `0x780f02`, writing
  each record's bucket-array pointer `+0x1c` to `0x7810bc + 0x400 * index`.
- `0xcddc..0xce02`: reset scratch/cursor-stack pointers and clear rectangle
  width, height, and fill selector.
- `0xce02..0xce10`: copy default byte `0x78219d` to reset environment word
  `0x782da4`.
- `0xce10..0xce3e`: when reset gate `0x7810b2` is clear, copy default
  environment byte `0x7821a2` to `0x782da6` and set pending bytes
  `0x782997` and `0x782998`.
- `0xce3e..0xce84`: clear or set reset bookkeeping bytes including `0x782990`,
  `0x782a6d`, `0x78297e`, `0x782c72`, `0x782c73`, `0x783184`, `0x783185`,
  `0x782f2c`, `0x78318f`, `0x783190`, and `0x783191`.
- `0xce84..0xcec8`: recompute HMI `0x78315c` from current-font context
  `0x782ee6`, using the inline/fixed-record branch or the alternate metric
  branch selected by context byte `+4`.
- `0xcec8..0xcf38`: convert default line-spacing word `0x78219e` through
  `0xcfea`, clamp outside `5..128` through `0xcf52`, convert the selected
  line spacing through `0x104d8`, and write VMI `0x783160`.
- `0xcf38..0xcf50`: clear `0x780e99` under scheduler lock.

`0xe146` is the parser/data-chain reset writer:

- `0xe14e..0xe17c`: reset `0x782d76` to `0x782d3e`, free active data-chain
  chunks through `0xe1e4`, clear `0x782d7a`, `0x783164`, alternate/data bytes
  `0x782c18` / `0x782c19`, page/parser byte `0x782a92`, and text accumulation
  bytes `0x783196..0x783199`.
- `0xe194..0xe1be`: reset parser/control record cursor `0x782c6e` to
  `0x782c1e` and clear eight 10-byte records at `0x782c1e..0x782c6d`.
- `0xe1be..0xe1dc`: call `0xe996` and `0xdf80` to restore font/context
  parser-side state after the record clear.

## Readers And Consumers

- `0xff1e` consumes current page root `0x78297a`, root state byte `+4`,
  parser/page state `0x782a92`, and saved overlay key `0x782a94` before
  publication or clear.
- `0xcda2` consumes defaults `0x78219d`, `0x78219e`, `0x7821a2`, reset gate
  `0x7810b2`, and current-font context `0x782ee6`.
- `0xcbd4` consumes current-font context `0x782ee6` plus active symbol words
  `0x783144` and `0x783146`.
- `0xe146` consumes parser/data-chain records while freeing any 0x100-byte
  allocations through `0x18b4`.
- `0x5e80` consumes the active record selected by `0x7822d5`.
- `0x96c4` and `0x97e4` consume dirty flags `0x780eba..0x780ed8` and retained
  record buffers.
- Later parser, geometry, text, raster, and font handlers consume the rebuilt
  environment and derived HMI/VMI values.

## Output Effect

`ESC E` can publish ROM-derived rows when a valid active page root exists. With
a valid root, `0xcc70..0xcc98` calls `0xf34a` and `0xff1e` before any reset
environment rebuild. The `! ESC E` byte-stream examples carry the pre-reset
printable byte through compact bucket materialization, publication, `0x1edc6`,
`0x1ed84`, and `0x1ef6a`; those examples exercise the documented branch path,
not an external rendered-output comparison.

With no current page root, reset does not invent output. The missing-root
examples reach handler `0xcc52`, enter `0xff1e`, take the no-root/current-root
clear exit documented in [publication-commands.md](publication-commands.md),
and create no published page record.

The default producer side joins reset at concrete RAM fields. `0x5e80..0x5f94`
selects a backing default record through `0x7822d5`, writes canonical defaults
`0x78219d`, `0x78219e`, and `0x7821a2`, and `0xcda2` later consumes those
fields as the environment word, gated environment byte, pending status bytes,
and reset VMI source.

The line-spacing arithmetic is at `0xcec8..0xcf38`: `0xcfea` computes a line
count from `(page_table_value - 0x12c) * 12 / 0x78219e`, `0xcda2` clamps
outside `5..128` lines through `0xcf52`, and `0x104d8` converts the selected
line-spacing longword into packed 12-subunit VMI.

## Reproduction Contract

A byte-stream renderer must preserve:

- `ESC E` as a page boundary that finalizes a valid current page before
  rebuilding the environment;
- the missing-root reset path that clears state without publication;
- `0xff1e` pool-header defaults and bucket/context bridge fields for published
  reset pages;
- reset consumption of canonical defaults `0x78219d`, `0x78219e`, and
  `0x7821a2`;
- the gated `0x7821a2 -> 0x782da6` behavior controlled by `0x7810b2`;
- the reset status side effect at `0xcc9e..0xccd2`: when `0x7810b2` is
  clear and `0x780e3c == 1`, the ROM copies `0x7821a2` to `0x780e8f`
  and signals `0x780e26` through `0x9b5e`;
- HMI refresh from current-font context and VMI conversion from default
  line-spacing;
- parser/data-chain reset through `0xe146`;
- raster-state reset fields in `0x783170`;
- selected default-record load/update semantics that feed later reset.

## Confidence

High for `ESC E` handler order, valid-root publication, missing-root clearing,
page-record pool header fields, compact-bucket rendering before reset,
default-record load into reset-consumed fields, line-spacing-to-VMI arithmetic,
and parser/data-chain clearing because the claims are backed by disassembly
`0xcc52..0xcd7a`, `0xcda2..0xcf50`, `0xcbd4..0xcc50`,
`0xe146..0xe1e2`, `0x5e80..0x5f94`, publication helper `0xff1e`, and the named
byte-stream examples.

High for the immediate default producer edge from selected backing records to
`0x78219d`, `0x78219e`, and `0x7821a2`.

Medium for manual-facing names of reset/default latches. Low for physical
retained-storage identity and board-level serial pin names behind `$a400` /
`$8c01`.

## Remaining Edges

- No ROM middle edge remains for the software-visible `ESC E` reset path,
  reset publication/missing-root split, default record load into reset
  consumers, line-spacing-to-VMI arithmetic, or compact-text reset publication
  through `0x1ed84` / `0x1ef6a`.
- Remaining reset/default work is external: physical retained-storage identity,
  board-level serial pin names, the external producer of `$8000.w` panel/service
  bytes, reconciling manual NVRAM-failure wording with the ROM paths, and
  optional physical correlation of reset/default behavior.
