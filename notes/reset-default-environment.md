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
- `0xcc52` calls `0xcc70`, `0xcbd4`, and `0xe146`, then clears `0x782a93`.
- `0xcc70` flushes pending text through `0xf34a`, publishes or clears the
  current page root through `0xff1e`, waits through `0x9ac2`, clears
  orientation byte `0x782da3`, calls `0xcda2`, and rebuilds raster/page-derived
  state.
- `0xcda2` rebuilds page/control records, default environment copies, parser
  scratch, VMI/HMI, and reset bookkeeping bytes.
- `0xcbd4` refreshes HMI and active-symbol snapshots from current-font context
  state.
- `0xe146` resets parser/data-chain records and clears parser/text
  accumulation state.
- `0x5e80` copies selected default-record fields into `0x78219d`, `0x78219e`,
  and `0x7821a2`.
- `0x5060`, `0x50be`, and `0x52ba` update backing records and canonical
  defaults.
- `0x56c2`, `0x571e`, and `0x5a62` maintain default-record banks and ROM-table
  fallback records.
- `0x96c4` commits dirty retained records; `0x97e4` reads retained records;
  `0x9a4a` emits software-visible serial phase pairs to `$a400`.

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

`ESC E` can publish pixels. With a valid active page root, `0xcc70` calls
`0xff1e` before the reset rebuild. Fixture
`ESC E stream publishes valid page root and resets environment/parser state`
pins that publication and the subsequent environment/parser side effects.
Fixtures `mixed printable/reset page-record stream queues through 0x1387c
before reset`, `mixed printable/reset page-record finalization publishes
bridged record`, and `addressed printable reset publishes rendered page record`
carry `! ESC E` from byte stream through compact bucket materialization,
publication, `0x1edc6`, `0x1ed84`, and `0x1ef6a`.

With no current page root, reset does not invent output. Fixtures
`ESC E stream clears missing page root without publication` and
`host-fetched ESC E clears missing page root without publication` pin the
missing-root path from modeled `0xa904` host bytes to handler `0xcc52`.

The default producer side is joined to reset by fixture
`0x5e80 -> 0xcda2 reset consumes default record outputs`: selected backing
record fields become canonical defaults, then `0xcda2` consumes them as the
environment word, gated environment byte, pending status bytes, and reset VMI.

Fixture `0xcfea/0xcf52/0x104d8 convert default line spacing to reset VMI`
pins the line-spacing arithmetic: `0xcfea` computes a line count from
`(page_table_value - 0x12c) * 12 / 0x78219e`, `0xcda2` clamps outside
`5..128` lines through `0xcf52`, and `0x104d8` converts the selected
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
- HMI refresh from current-font context and VMI conversion from default
  line-spacing;
- parser/data-chain reset through `0xe146`;
- raster-state reset fields in `0x783170`;
- selected default-record load/update semantics that feed later reset.

## Confidence

High for `ESC E` handler order, valid-root publication, missing-root clearing,
page-record pool header fields, compact-bucket rendering before reset,
default-record load into reset-consumed fields, line-spacing-to-VMI arithmetic,
and parser/data-chain clearing because each is backed by disassembly and named
fixtures.

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
  physical/reference page-output comparison.
