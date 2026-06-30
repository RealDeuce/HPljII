# Macro Definition And Data-Chain Replay

This note is the semantic contract for LaserJet II macro definition,
execute/call replay, overlay publication, data-chain frames, and the macro
heap/context helpers that affect page output.

Status: composed for the documented command streams and overlay paths from
host byte fetch through parser replay, page-record publication, and rendered
rows. The low-level ledger remains in `notes/reverse-engineering-ledger.md`,
`notes/pcl-parser-firmware.md`, and generated disassembly. This file is the
renderer-facing macro checkpoint.

## Evidence

- `generated/disasm/ic30_ic13_pcl_escape_parser_00da9a.lst`
- `generated/disasm/ic30_ic13_macro_record_chain_helpers_00dfba.lst`
- `generated/disasm/ic30_ic13_macro_environment_snapshot_helpers_00e65c.lst`
- `generated/disasm/ic30_ic13_heap_allocator_init_00164a.lst`
- `generated/disasm/ic30_ic13_main_parser_loop_011774.lst`
- `generated/analysis/ic30_ic13_parser_dispatch_tables.md`
- `generated/analysis/ic30_ic13_tokenizer_macro_callers.md`
- `generated/analysis/ic30_ic13_parser_xrefs.md`
- `generated/analysis/ic30_ic13_renderer_fixture_harness.md`
- `notes/host-byte-fetch.md`
- `notes/pcl-parser-core.md`
- `notes/pcl-parser-firmware.md`
- `notes/page-raster-imaging.md`
- `notes/semantic-state-model.md`

Primary fixtures:

- `0xe112 stores absolute parsed macro id`
- `0xe0a4 macro record lookup uses head presence and first free slot`
- `0xdd08 starts and stops empty macro definitions`
- `0x116f6 alternate parser routes macro stop but suppresses payload controls`
- `host-fetched macro definition stream routes alternate parser table`
- `macro command stream defines payload and executes data-chain frame`
- `macro command stream defines payload and calls data-chain frame`
- `host-fetched macro execute stream builds replay frame`
- `host-fetched macro call stream builds replay frame`
- `macro execute frame payload feeds 0xa904 data-chain bytes`
- `macro execute data-chain parser trace feeds page-record stream`
- `macro call data-chain parser trace feeds page-record stream`
- `host-fetched mixed-control macro execute stream builds replay frame`
- `macro mixed-control data-chain parser trace feeds page-record stream`
- `host-fetched macro replay payloads preserve 0x1edc6 bridge contract`
- `host-fetched macro replay payloads feed 0x1ed84 and 0x1ef6a`
- `macro overlay finalization replays before page publication`
- `macro overlay replays across repeated page publications`
- `macro overlay skip gates preserve base page publication`
- `macro overlay mixed-control payload publishes with page rule`
- `macro overlay cursor-position payload publishes with page rule`
- `macro overlay chained cursor-position payload publishes with page rule`
- `macro overlay chained margin payload publishes with page rule`
- `macro overlay transparent payload publishes with page rule`
- `macro overlay raster payload publishes with page rule`
- `macro overlay multi-row raster payload publishes with page rule`
- `macro overlay span-flush payload publishes with page rule`

## Field Groups

Canonical macro records:

- `0x783164`: current macro id written by `ESC &f#Y` handler `0xe112` from
  the absolute parsed parameter.
- `0x782a98`: 32-entry macro record pool, with 12-byte entries.
- Record `+0x00`: head pointer for linked 0x100-byte payload chunks. A
  nonzero head makes a record selectable by `0xe0a4`.
- Record `+0x04`: raw byte count including four header bytes per allocated
  chunk.
- Record `+0x08`: macro id word compared by `0xe0a4`.
- Record `+0x0a`: temporary/permanent byte owned by selectors `7`, `9`, and
  `10`; lookup does not inspect it.
- `0x782d7a`: current macro record pointer selected by `0xe0a4` and consumed
  by `0xdd08`, `0xe002`, `0xe418`, and overlay publication.

Canonical data-chain frames:

- `0x782d76`: current data-chain frame pointer.
- Frame `+0x00/+0x04`: payload chain head and raw count copied from the macro
  record.
- Frame `+0x08`: byte-source stride/offset byte, pinned as `4` for macro
  execute/call and overlay replay frames.
- Frame `+0x09`: frame kind. Covered values are `2` execute, `3` call, and
  `4` non-replay overlay publication.
- Frame `+0x0a`: environment snapshot chain pointer for execute/call frames;
  zero for the non-replay overlay frame.

Canonical overlay state:

- `0x782a92`: overlay/page-parser state. Selector `4` enables overlay, selector
  `5` disables it, and `0xff1e` consumes state `1` when the page-root retry
  bit is clear.
- `0x782a94`: saved overlay macro id copied from the current id by selector
  `4`.
- Page-root flag bit `+0x14.0`: retry gate that suppresses overlay replay
  while preserving base page publication.

Canonical macro context and font refresh:

- `0x782c1e..0x782c6d`: eight 10-byte macro call-context records cleared by
  reset helper `0xe146`.
- `0x782c6e`: macro context-stack pointer. `0xe418` call mode and `0xe4f4`
  push one 10-byte entry; `0xe65c(0)` pops one entry.
- `0x782c64`: static macro context record consumed by `0xe65c(1)`.
- Entry bytes `+8/+9`: primary/secondary refresh flags consumed by `0xe65c`
  before the selected context is installed through the normal font bridge.

Canonical heap and payload-chain state:

- `0x780efa` and `0x780efe`: startup-derived heap start and available-byte
  inputs consumed by `0x164a`.
- `0x780e86`: free 64-byte unit count.
- `0x783972`: heap allocation bitmap base pointer.
- `0x783988`: payload base pointer; also the default chunk base used by macro
  payload storage in the modeled memory layout.
- `0x783976`, `0x78397a`, `0x78397e`, `0x783982`, and `0x783986`: allocator
  scan end, limits, cursors, and tracked bitmap-byte count.

Derived/cache state:

- The normalized macro payload count is derived at selector `1` stop as
  `raw_count - (((raw_count + 0xff) >> 8) * 4)`.
- Replay output rows and compact object coordinates are derived from the same
  parser, page-record, and render paths as live host bytes. Macro replay does
  not have a separate renderer.
- Non-replay overlay setup snapshots and restores flat environment state
  before replaying the stored payload against the page being published.

Parser scratch:

- Normal parser mode 17 routes `ESC &f#Y` to `0xe112` and `ESC &f#X` to
  `0xdd08`.
- Alternate/data parser table `0x116f6` keeps `x/X -> 0xdd08`, so a macro
  definition can stop, while ordinary payload controls are appended rather
  than dispatched.
- `0x782c18` and `0x782c19` gate definition mode and macro append errors.
- `0x78299e` is rewound by `0xdd08` before selector dispatch.

Firmware bookkeeping:

- Host gate bit 1 is set when a data-chain frame has bytes and cleared by
  `0xe22c` when the previous frame has no byte count.
- `0xe8f0` allocation failure reports status through `0x9b5e(0x780e2e, 4)`
  and backs out frame setup.
- `0xe22c` calls `0x1240a` after execute/call and non-replay frame endings.

Unknown:

- Manual-facing names for macro context-stack bytes and overlay state
  `0x782a92` are inferred from ROM effects.
- The macro context push/pop paths have no observed bounds checks. The eighth
  reset-cleared record is documented, but physical failure behavior after an
  over-deep call stack has not been externally validated.

## Writers

- `0xe112` writes current macro id `0x783164`.
- `0xe0a4` writes `0x782d7a` to an existing nonempty record, first free
  record, or zero for full-pool miss. On a free path it writes requested id
  into record `+0x08`.
- `0xdd08` rewinds `0x78299e`, dispatches selectors `0..10`, and writes
  definition, execute/call, overlay, delete, temporary, and permanent state.
- `0xdd86..0xde7a` starts/stops definition mode, seeds lowercase `ESC &f`
  auto-prefix bytes through `0xe002`, normalizes counts, and clears empty or
  auto-prefix-only records through `0xdfba`.
- `0xe002` appends definition bytes into linked 0x100-byte chunks, links new
  chunks, updates record raw count `+0x04`, and sets `0x782c19` on allocation
  failure.
- `0xe418` writes execute/call data-chain frames, environment snapshot pointer
  `+0x0a`, and the call-only context-stack entry.
- `0xe4f4` writes the non-replay overlay frame at `0x782d4c`, writes
  `0x782d76`, saves cursor longword `0x782c92`, snapshots flat state, and may
  set host gate bit 1.
- `0xe22c` unwinds frames, frees snapshot chunks, rewinds `0x782d76` for
  execute/call frames, and writes `0x782a92 = 0x63` on non-execute/non-call
  frame return.
- `0x164a` initializes the heap bitmap and allocator fields.
- `0x170c` / `0x1710` allocate 64-byte heap units; `0x18b4` frees linked
  macro/snapshot chains when count is zero.
- `0xe65c(0)` pops macro call-context entries; `0xe65c(1)` consumes static
  context record `0x782c64`.

## Readers And Consumers

- `0xdd08` consumes `0x783164`, `0x782d7a`, `0x782d76`, frame byte `+9`, and
  definition-mode byte `0x782c18`.
- `0xe0a4` consumes each macro record head `+0x00` and id `+0x08`, but not
  permanence byte `+0x0a`.
- `0xe002` consumes current record pointer `0x782d7a`, current append chunk
  `0x782c1a`, raw count `+0x04`, frame byte `+9`, and append-error byte
  `0x782c19`.
- `0xa904` consumes active data-chain frame bytes as a byte source and calls
  `0xe22c` at the frame-end marker before resuming the outer source.
- Parser loop `0x11774` consumes replayed bytes and routes them to the same
  handlers used for live host bytes, including `0xd04a`, `0xf02c`,
  `0xedf8`, `0xf39e`, `0xf560`, `0xeb58`, `0xec0c`, `0x11f5a`, and
  delayed payload handler `0x105d0`.
- `0xff1e` consumes `0x782a92`, `0x782a94`, current root flag word `+0x14`,
  and macro record state before the overlay replay detour.
- `0xe65c` consumes macro context bytes `+8/+9`, selected slot byte
  `0x782f06`, and current font context fields before calling the existing
  `0x13eb8` / `0x144d2` / `0x14c64` / `0xc428` bridge.
- Page-record consumers are shared: `0x1387c` / `0x1381c` build objects,
  `0x1edc6` bridges context/buckets, and `0x1ed84` / `0x1ef6a` render rows.

## Output Effect

`ESC &f123Y ESC &f0X ! CR ESC &f1X ESC &f2X` defines payload `21 0d`, builds
an execute frame, drains replay bytes through `0xa904`, dispatches `0xd04a`
then `0xf02c`, queues the same text object as direct host bytes, and renders
the same rows. The call selector `3` follows the same visible path for the
covered text payload.

The mixed-control execute fixture stores `ESC &k1G!\r!`, builds an execute
frame, replays through `0xedf8`, `0xd04a`, `0xf02c`, and `0xd04a`, then
matches the direct mixed-stream rows after `0x1edc6`, `0x1ed84`, and
`0x1ef6a`.

Overlay publication enters from `0xff1e`, not from the host parser directly.
With selector `4` enabled, `0xff1e` resolves `0x782a94` through `0xe0a4`,
calls `0xe4f4`, re-enters parser loop `0x11774`, and publishes the replayed
payload into the same page record. Fixture `macro overlay finalization replays
before page publication` proves stored `!\r` composes with an existing
selector-7 rectangle rule.

Fixture `macro overlay replays across repeated page publications` proves the
enabled overlay state survives two page boundaries; both pages replay `!\r`
before publication and compose with page-specific selector-7 rules.

Fixture `macro overlay skip gates preserve base page publication` proves the
opposite branch: disabled overlay mode, missing selected record, and page-root
retry flag publish the base printable/rule page record without adding a
non-replay frame.

The overlay payload matrix now crosses multiple command families:

- `ESC &k1G!\r!` stores line-termination mode and queues two compact text
  entries with a selector-7 rule.
- `ESC &a2C!` queues compact text at coord `0x0a02` after replayed horizontal
  cursor positioning.
- `ESC &a2c+1R!` crosses lowercase chaining through `0xf39e`, relative row
  positioning through `0xf560`, and printable text through `0xd04a`.
- `ESC &a6l9M!` writes left/right margins through `0xeb58` and `0xec0c`
  before printable text.
- `ESC &p2X!!` enters delayed transparent-data handler `0x12452`, then routes
  both payload bytes through `0xd04a`.
- `! ESC *t300R ESC *r0A ESC *b2W c3 3c` queues compact text plus one mode-0
  raster object.
- `! ESC *t300R ESC *r0A ESC *b2W f0 0f ESC *b2W 0f f0` queues compact text
  plus two raster rows and advances raster `row_y` to `2`.
- `ESC &a6L!` materializes a selector-`0x4000` span object through `0x12714`
  before queuing the following printable glyph.

All covered overlay payloads publish through `0xff1e`, bridge through
`0x1edc6`, and render through `0x1ed84` / `0x1ef6a` with fixture-pinned row
digests in `notes/semantic-state-model.md`.

## Reproduction Contract

A byte-stream renderer must preserve:

- `ESC &f#Y` absolute id storage and `ESC &f#X` selector meanings `0..10`;
- the 32-entry macro record pool, including head-presence lookup semantics;
- raw record counts that include four header bytes per 0x100-byte chunk;
- 252 payload bytes per macro chunk after the longword next pointer;
- lowercase `ESC &f0x` auto-prefix seeding and stop-time empty-prefix cleanup;
- alternate/data parser behavior that appends payload controls but still lets
  `ESC &f1X` stop definition;
- execute/call frame fields `+0x00/+0x04/+0x08/+0x09/+0x0a`;
- `0xa904` replay priority and `0xe22c` frame-end unwinding;
- call-only macro context push/pop and font-context refresh through `0xe65c`;
- overlay selector state and the `0xff1e -> 0xe0a4 -> 0xe4f4 -> 0x11774`
  replay detour;
- skip gates for disabled overlay, missing overlay record, and page-root retry
  flag;
- page-record publication and render output after replayed macro bytes.

## Confidence

High for parser reachability, selector meanings, record layout, chunk count
math, `0xe0a4` lookup/free/full behavior, execute/call and non-replay frame
field offsets, `0xa904` replay, `0xe22c` frame ending, heap unit allocation,
`0xe65c` font-context bridge, overlay detour, skip gates, and page-record
output because each is backed by disassembly and named fixtures.

High for the covered overlay payload matrix because each fixture starts from a
stored macro payload, re-enters parser handlers, preserves the page-record
bridge, and renders rows.

Medium for external/manual names for macro context and overlay state fields.
Medium for behavior beyond the eight reset-cleared macro context records
because the ROM push/pop paths do not show bounds checks and no external
failure case is validated.

## Remaining Edges

- No ROM middle edge remains for macro execute/call replay, macro
  font-context refresh, first overlay publication, repeated enabled-overlay
  publication, mixed-control overlay payloads, cursor-position overlay
  payloads, chained-margin overlay payloads, transparent-data overlay
  payloads, raster overlay payloads, multi-row raster overlay payloads,
  span-flush overlay payloads, or the disabled/missing-record/retry-flag
  overlay skip gates.
- Remaining macro work is broader overlay payload variants beyond the listed
  command-family matrix, external/manual naming, and final physical/reference
  output comparison.
