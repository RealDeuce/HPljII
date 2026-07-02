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
- `0x11774 ROM dispatch table routes chained ESC &f macro stream`
- `macro command stream assigns id and starts/stops empty definition`
- `0x116f6 alternate parser routes macro stop but suppresses payload controls`
- `host-fetched macro definition stream routes alternate parser table`
- `macro command stream defines payload and executes data-chain frame`
- `macro command stream defines payload and calls data-chain frame`
- `macro command stream enables and disables overlay state`
- `macro command stream toggles permanence before delete-temporary`
- `macro command stream deletes current record or all records`
- `macro command stream respects definition and active-chain guards`
- `host-fetched macro command streams update records and frames`
- `0xdd08 overlay and temporary/permanent macro controls`
- `host-fetched macro execute stream builds replay frame`
- `host-fetched macro call stream builds replay frame`
- `0xdd08 execute and call push macro data-chain frames`
- `0xe418 frame metadata distinguishes execute and call context`
- `0xe146/e418/e4f4/e65c macro context stack has eight records and no guard`
- `macro snapshot helpers copy linked and flat environment ranges`
- `0xe002 appends macro definition bytes into 0x100 chunks`
- `0xe4f4/0xe22c produce and end data-chain frames`
- `0xe65c refreshes macro font context entries`
- `0xe65c refresh composes with font context bridge`
- `macro execute frame payload feeds 0xa904 data-chain bytes`
- `macro execute data-chain parser trace feeds page-record stream`
- `macro call data-chain parser trace feeds page-record stream`
- `macro execute payload queues printable glyph then applies CR`
- `macro execute payload page-record bridge renders queued glyph`
- `macro execute data-chain replay feeds page-record stream`
- `macro execute mixed control payload replays through page-record stream`
- `macro execute page-record layer composes with rule and raster band`
- `host-fetched mixed-control macro execute stream builds replay frame`
- `macro mixed-control data-chain parser trace feeds page-record stream`
- `host-fetched macro replay payloads preserve 0x1edc6 bridge contract`
- `host-fetched macro replay payloads feed 0x1ed84 and 0x1ef6a`
- `macro overlay finalization replays before page publication`
- `macro overlay replays across repeated page publications`
- `macro overlay skip gates preserve base page publication`
- `macro overlay mixed-control payload publishes with page rule`
- `macro overlay cursor-position payload publishes with page rule`
- `macro overlay vertical-decipoint payload publishes with page rule`
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
- Covered overlay payloads reuse canonical print-state fields rather than
  inventing an overlay-specific renderer. `0xf39e` writes horizontal cursor
  `0x782c8a`; `0xf60a` writes vertical cursor `0x782c8e`; `0xeb58` and
  `0xec0c` write left/right margins `0x782dd6` / `0x782dda`; and raster
  payload handlers queue the same mode-0 raster records documented in
  `notes/raster-graphics.md`.
- Span-flush overlay payloads reuse canonical pending-span fields
  `0x783186..0x78318a`: `0xf34a` / `0x12714` publish a selector-`0x4000`
  segment-list object, and `0x126e2` re-arms the pending span for following
  text.

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
- Covered overlay fixture coords and rule decoder suffixes are derived/cache
  evidence: compact text coords such as `0x0a02`, `0x9001`, `0x3a02`, and
  `0x0207`, and rule mutations such as tail words `ff ca`, `ff cc`, and
  `ff d0`, are products of page-record bridge/render consumers rather than
  host-visible parser state.

Parser scratch:

- Normal parser mode 17 routes `ESC &f#Y` to `0xe112` and `ESC &f#X` to
  `0xdd08`.
- Alternate/data parser table `0x116f6` keeps `x/X -> 0xdd08`, so a macro
  definition can stop, while ordinary payload controls are appended rather
  than dispatched.
- `0x782c18` and `0x782c19` gate definition mode and macro append errors.
- `0x78299e` is rewound by `0xdd08` before selector dispatch.
- Non-replay overlay fixtures restore the stored payload bytes as parser
  scratch under `0xa904` / `0x11774`; examples include `ESC &a72V!`,
  `ESC &a2c+1R!`, delayed transparent record `80 58 00 02 00 00`, and the
  delayed raster `ESC *b#W` payload bytes.

Firmware bookkeeping:

- Host gate bit 1 is set when a data-chain frame has bytes and cleared by
  `0xe22c` when the previous frame has no byte count.
- `0xe8f0` allocation failure reports status through `0x9b5e(0x780e2e, 4)`
  and backs out frame setup.
- `0xe22c` calls `0x1240a` after execute/call and non-replay frame endings.
- The non-replay overlay frame byte count and frame mode bytes are firmware
  bookkeeping. Covered overlay frames use source byte `+8 = 4` and frame kind
  `+9 = 4`, then `0xe22c` restores parser/page state after replay.

Unknown:

- Manual-facing names for macro context-stack bytes and overlay state
  `0x782a92` are inferred from ROM effects.
- The macro context push/pop paths have no observed bounds checks. The eighth
  reset-cleared record is documented, but physical failure behavior after an
  over-deep call stack has not been externally validated.

## Selector Dispatch

`ESC &f#X` reaches `0xdd08`, which rewinds `0x78299e`, resolves the current
macro id through `0xe0a4`, and dispatches the absolute selector through the
ROM list below. The list is canonical command-family behavior; output pixels
appear only when the selected control builds or replays a payload that later
passes through `0xa904`, parser dispatch, page-record queueing, and render
entry.

Selector effects:

- `0`: handler `0xdd86` starts definition mode. Lowercase `x` seeds
  lowercase auto-prefix bytes through `0xe002`; uppercase `X` seeds a single
  zero byte.
- `1`: handler `0xddfc` stops definition mode, normalizes raw chunk counts,
  clears empty or auto-prefix-only records, and leaves nonempty payload records
  selectable.
- `2`: handler `0xde7c` executes the selected macro through an `0xe418`
  data-chain frame with frame byte `+9 = 2`.
- `3`: handler `0xdea2` calls the selected macro through an `0xe418`
  data-chain frame with frame byte `+9 = 3` and a pushed macro context entry.
- `4`: handler `0xdec8` enables overlay state `0x782a92` and saves current
  macro id in `0x782a94` when the record exists.
- `5`: handler `0xdef4` disables overlay state.
- `6`: handler `0xdefe` deletes all macro records.
- `7`: handler `0xdf08` deletes temporary macro records by testing permanence
  byte `+0x0a`.
- `8`: handler `0xdf12` deletes the current macro record selected by id.
- `9`: handler `0xdf24` marks the current record temporary by clearing byte
  `+0x0a`.
- `10`: handler `0xdf36` marks the current record permanent by setting byte
  `+0x0a`.

Guard behavior is part of the same selector contract. Fixture
`macro command stream respects definition and active-chain guards` proves the
selector cases that the ROM suppresses while definition mode is active or an
active data-chain frame is present. The alternate/data parser table still
routes `x/X` to `0xdd08`, so selector `1` can stop a definition while payload
bytes are otherwise appended instead of dispatched.

## Writers

- `0xe112` writes current macro id `0x783164`.
- `0xe0a4` writes `0x782d7a` to an existing nonempty record, first free
  record, or zero for full-pool miss. On a free path it writes requested id
  into record `+0x08`.
- `0xdd08` rewinds `0x78299e`, dispatches selectors `0..10`, and writes
  definition, execute/call, overlay, delete, temporary, and permanent state.
- Fixture `0xdd08 overlay and temporary/permanent macro controls` pins the
  selector branches that enable/disable overlay, mark a record permanent, clear
  temporary records, and delete current/all records. Fixture `macro command
  stream respects definition and active-chain guards` pins the guard behavior:
  definition-mode and active data-chain state suppress the selectors that the
  ROM refuses to run in those states.
- `0xdd86..0xde7a` starts/stops definition mode, seeds lowercase `ESC &f`
  auto-prefix bytes through `0xe002`, normalizes counts, and clears empty or
  auto-prefix-only records through `0xdfba`.
- `0xe002` appends definition bytes into linked 0x100-byte chunks, links new
  chunks, updates record raw count `+0x04`, and sets `0x782c19` on allocation
  failure.
- Fixture `0xe002 appends macro definition bytes into 0x100 chunks` pins the
  chunk format: a longword next pointer followed by 252 payload bytes, raw
  counts including four header bytes per chunk, and the transition to a linked
  second chunk after the first 252 payload bytes.
- `0xe418` writes execute/call data-chain frames, environment snapshot pointer
  `+0x0a`, and the call-only context-stack entry.
- Fixtures `0xdd08 execute and call push macro data-chain frames` and
  `0xe418 frame metadata distinguishes execute and call context` pin frame
  bytes `+8 = 4`, `+9 = 2` for execute, `+9 = 3` for call, and the call-only
  context push.
- `0xe4f4` writes the non-replay overlay frame at `0x782d4c`, writes
  `0x782d76`, saves cursor longword `0x782c92`, snapshots flat state, and may
  set host gate bit 1.
- `0xe22c` unwinds frames, frees snapshot chunks, rewinds `0x782d76` for
  execute/call frames, and writes `0x782a92 = 0x63` on non-execute/non-call
  frame return.
- Fixture `0xe4f4/0xe22c produce and end data-chain frames` pins the
  non-replay frame producer and the matching end-frame cleanup. Fixture
  `macro snapshot helpers copy linked and flat environment ranges` pins the
  linked `0xe8f0` / `0xe8a2` snapshot chain and flat `0xe972` / `0xe996`
  copy helpers used by those frame paths.
- `0x164a` initializes the heap bitmap and allocator fields.
- `0x170c` / `0x1710` allocate 64-byte heap units; `0x18b4` frees linked
  macro/snapshot chains when count is zero.
- `0xe65c(0)` pops macro call-context entries; `0xe65c(1)` consumes static
  context record `0x782c64`.
- Fixtures `0xe65c refreshes macro font context entries` and `0xe65c refresh
  composes with font context bridge` pin the bridge from macro context flags
  through `0x13eb8`, `0x144d2`, `0x14c64`, and final `0xc428` page-root
  font-slot install. Fixture `0xe146/e418/e4f4/e65c macro context stack has
  eight records and no guard` pins the reset-cleared stack bounds and the lack
  of ROM-side push/pop guard checks.

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

The parser-facing macro command stream is fixture-backed at both the handler
and host-fetched levels. Fixture
`0x11774 ROM dispatch table routes chained ESC &f macro stream` pins normal
mode 17 dispatch to `0xe112` and `0xdd08`. Fixture `macro command stream
assigns id and starts/stops empty definition` pins `ESC &f#Y`, selector `0`
start, selector `1` stop, and empty-definition cleanup. Fixture
`host-fetched macro command streams update records and frames` proves the same
state updates from a real `0xa904` ring source.

Replay output is also fixture-backed in page terms, not only frame terms.
Fixture `macro execute payload queues printable glyph then applies CR` proves
stored `!\r` re-enters `0xd04a` and `0xf02c`. Fixture `macro execute payload
page-record bridge renders queued glyph` carries that queued object through
`0x1edc6` and render entry. Fixture `macro execute data-chain replay feeds
page-record stream` proves the replayed data-chain bytes feed the same
page-record stream as host bytes. Fixture `macro execute mixed control payload
replays through page-record stream` covers the mixed-control sibling
`ESC &k1G!\r!`. Fixture `macro execute page-record layer composes with rule
and raster band` proves macro-replayed text can compose with selector-7 rule
and mode-0 raster output in one rendered band.

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
- `ESC &a72V!` routes vertical decipoint positioning through `0xf60a`, writes
  vertical cursor state, then queues compact text at coord `0x9001`.
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

The fixture-backed render contract for that matrix is:

- Repeated overlay publication replays `!\r` on two page boundaries. The first
  page composes with selector-7 rule object
  `00 00 00 00 01 07 88 01 00 0c 00 03 00 00`.
  Digest:
  `0629159c6a0f5c4a23508d5bfab14b725e13f0bfa32b82efca091aec425fa4c0`.
  The second page composes with selector-7 rule object
  `00 00 00 00 01 07 e4 00 00 08 00 04 00 00`.
  Digest:
  `2d52675c52b22b80e87a379e32894c7a9638596770093d2fd80b64e25559977e`.
- The skip-gate fixture publishes base printable `?` plus selector-7 rule
  `00 00 00 00 01 07 a2 00 00 06 00 02 00 00`. Disabled overlay mode,
  missing selected record, and page-root retry flag preserve the same digest:
  `425e0a2abf918906a45f655b589c615108f72ca6b89dc1b280b99121e4405e43`.
- Mixed-control overlay payload `ESC &k1G!\r!` writes line-termination mode
  `0x80`, queues compact text payload `00 02 20 00 01 20 3b 00`, and
  composes with selector-7 rule
  `00 00 00 00 01 07 cc 01 00 08 00 02 00 00`, mutated by `0x1f596` to
  `00 00 00 00 01 07 cc 01 00 08 00 02 ff ce`. Digest:
  `04d32edf47d03c587abc0abaf750c6a2d634ceea80df9787681b618867136f52`.
- Cursor-position overlay payload `ESC &a2C!` routes through `0xf39e`, moves
  packed horizontal cursor `10 -> 36`, queues compact text payload
  `00 01 20 0a 02`, and composes with selector-7 rule
  `00 00 00 00 01 07 82 02 00 07 00 02 00 00`, mutated to
  `00 00 00 00 01 07 82 02 00 07 00 02 ff ca`. Digest:
  `ba32af7d183a956b2abd821b2143e9c7c3eecf87a7b1403fa086cfe6bf89c8ae`.
- Vertical-decipoint overlay payload `ESC &a72V!` routes through `0xf60a`,
  moves packed vertical cursor `20 -> 30`, queues compact text payload
  `00 01 20 90 01` at coord `0x9001`, and composes with selector-7 rule
  `00 00 00 00 01 07 88 01 00 07 00 02 00 00`, mutated to
  `00 00 00 00 01 07 88 01 00 07 00 02 ff ca`. Digest:
  `7ef1cc5d5557fa5a30c57e8ad6918b09747c210daed2639e9d75ccfed727e964`.
- Chained cursor-position overlay payload `ESC &a2c+1R!` routes through
  `0xf39e`, parser mode `12`, `0xf560`, and `0xd04a`; moves packed cursor
  `(10, 21) -> (36, 24)`; queues compact text payload `00 01 20 3a 02`; and
  composes with selector-7 rule
  `00 00 00 00 01 07 a6 02 00 06 00 02 00 00`, mutated to
  `00 00 00 00 01 07 a6 02 00 06 00 02 ff cc`. Digest:
  `0275857ffbcc11aa5234644930ebcd31571c2178eaf52b79590989d31b39f653`.
- Chained margin overlay payload `ESC &a6l9M!` routes through `0xeb58`,
  parser mode `12`, `0xec0c`, and `0xd04a`; writes packed left/right margins
  `108` / `180`; queues compact text payload `00 01 20 02 07`; and composes
  with selector-7 rule `00 00 00 00 01 07 6c 02 00 05 00 02 00 00`, mutated
  to `00 00 00 00 01 07 6c 02 00 05 00 02 ff c8`. Digest:
  `ecae0043ee656ceba42d4d6e052e3d56a365eeb4a847b3b430f80eed72b5a199`.
- Transparent overlay payload `ESC &p2X!!` reaches `0x11f5a`, saves delayed
  record `80 58 00 02 00 00`, restores it through `0x12452`, routes raw
  bytes `21 21` through `0xd04a`, and queues compact text object prefix
  `00 00 00 00 00 00 00 02 20 00 01 20 02 02`. The selector-7 rule
  `00 00 00 00 01 07 e0 02 00 09 00 02 00 00` mutates to
  `00 00 00 00 01 07 e0 02 00 09 00 02 ff d0`. Digest:
  `1ee999b850b4a35aa2b01b72ae01da961ee4084f0369f4ded5c8e8152464dac8`.
- Raster overlay payload `! ESC *t300R ESC *r0A ESC *b2W c3 3c` builds a
  20-byte non-replay frame, queues compact text plus mode-0 raster object
  `00 00 00 00 80 00 00 02 00 00 c3 3c`, and mutates selector-7 rule
  `00 00 00 00 01 07 44 01 00 0a 00 02 00 00` to
  `00 00 00 00 01 07 44 01 00 0a 00 02 ff c6`. Digest:
  `bc21050018fd3e992709c704fff732499aa9d06565de31d7ae0340869971c5b3`.
- Multi-row raster overlay payload
  `! ESC *t300R ESC *r0A ESC *b2W f0 0f ESC *b2W 0f f0` builds a 27-byte
  non-replay frame, queues raster objects
  `00 00 00 00 80 00 00 02 00 00 f0 0f` and
  `00 00 00 00 80 00 00 02 10 00 0f f0`, advances raster `row_y` to `2`,
  and bridges the bucket chain as second raster row, first raster row, compact
  text. Digest:
  `58c2293bbc6b187db0e964571e5812ab2192d32d8e648a38d61e407a58538638`.
- Span-flush overlay payload `ESC &a6L!` routes through `0xeb58`, `0xf34a`,
  `0x12714`, `0x126e2`, and `0xd04a`. It writes packed left margin `108`,
  publishes selector-`0x4000` segment-list object
  `00 00 00 00 40 00 00 01 32 00 03 00 00 10`, re-arms
  `0x783186..0x78318a` to `108/108/0`, queues compact object prefix
  `00 00 00 00 00 00 00 01 20 02 07`, and mutates selector-7 rule
  `00 00 00 00 01 07 a4 02 00 07 00 02 00 00` to
  `00 00 00 00 01 07 a4 02 00 07 00 02 ff cc`. Digest:
  `6775414374ba3c31f7846a180d93cc9b68e230ea6981ae722b32eb39081f9bca`.

All covered overlay payloads publish through `0xff1e`, bridge through
`0x1edc6`, and render through `0x1ed84` / `0x1ef6a`. Remaining edges are no
longer inside the listed payload paths; they are broader overlay payload
variants outside this matrix and final device-output comparison.

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
  payloads, vertical-decipoint overlay payloads, chained-margin overlay
  payloads, transparent-data overlay payloads, raster overlay payloads,
  multi-row raster overlay payloads, span-flush overlay payloads, or the
  disabled/missing-record/retry-flag overlay skip gates.
- Remaining macro work is broader overlay payload variants beyond the listed
  command-family matrix, external/manual naming, and final physical/reference
  output comparison.
