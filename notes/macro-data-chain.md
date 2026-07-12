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
- `generated/disasm/ic30_ic13_data_chain_byte_reader_009f6a.lst`
- `generated/disasm/ic30_ic13_macro_environment_snapshot_helpers_00e65c.lst`
- `generated/disasm/ic30_ic13_font_context_install_00c428.lst`
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
- `notes/page-record-storage.md`
- `notes/semantic-state-model.md`

Primary byte-stream examples:

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

## Owner Summary

Concept: this note owns macro definition, macro record storage, execute/call
replay, overlay publication, data-chain frames, and macro context snapshots.
It documents how `ESC &f#Y` selects macro ids, how `ESC &f#X` selectors create
or consume stored payload bytes, how replay becomes a `0xa904` byte source,
and how overlay publication injects stored bytes before page output.

Primary route:

- Parser dispatch routes `ESC &f#Y` to `0xe112` and `ESC &f#X` to `0xdd08`.
- Definition route:
  `0xdd08 selector 0/1 -> macro record -> 0xe002 append sink -> linked
  0x100-byte chunks`.
- Execute/call route:
  `0xdd08 selector 2/3 -> 0xe418 frame builder -> 0x782d76 active frame
  -> 0xa904 data-chain source -> 0x11774 parser dispatch -> command-family
  handlers -> page records -> render`.
- Frame-end route:
  `0xa904 count-end marker -> 0xe22c -> optional context restore -> previous
  frame/source resumes`.
- Overlay route:
  `0xdd08 selector 4/5 -> overlay id/state -> page publication 0xff1e
  -> 0xe4f4 non-replay frame -> 0xa904/0x11774 stored payload replay
  -> page publication continues`.
- Macro replay has no separate renderer. Stored printable, direct-control,
  raster, rectangle, transparent, and span-producing payloads reuse their
  normal command-family owners after `0xa904` returns the replay bytes.

Field groups:

- Canonical macro records: current macro id `0x783164`, record pool
  `0x782a98`, selected record pointer `0x782d7a`, record head `+0x00`, raw
  byte count `+0x04`, macro id `+0x08`, and permanence byte `+0x0a`.
- Canonical data-chain frames: current frame pointer `0x782d76`, frame
  payload head/count at `+0x00/+0x04`, source offset byte `+0x08`, frame kind
  byte `+0x09`, and snapshot pointer `+0x0a`.
- Canonical overlay state: overlay state byte `0x782a92`, saved overlay id
  `0x782a94`, page-root retry gate in flags word `root+0x14` bit 0
  (written at byte `root+0x15.0`), and publication detour through `0xff1e`.
- Canonical context state: eight 10-byte macro context records
  `0x782c1e..0x782c6d`, stack pointer `0x782c6e`, static context record
  `0x782c64`, and primary/secondary refresh flags at entry bytes `+8/+9`.
- Canonical heap/payload-chain state: heap inputs `0x780efa` / `0x780efe`,
  free-unit count `0x780e86`, allocation bitmap pointer `0x783972`, payload
  base `0x783988`, and allocator cursors `0x783976`, `0x78397a`,
  `0x78397e`, `0x783982`, and `0x783986`.
- Derived/cache: normalized macro payload count, replay compact coordinates,
  overlay render outputs, and rule/raster/text row products created by normal
  downstream command owners.
- Parser scratch: definition-mode byte `0x782c18`, append-error byte
  `0x782c19`, parser record cursor `0x78299e`, alternate/data table routing,
  and replayed bytes returned by `0xa904`.
- Firmware bookkeeping: host gate bit 1, allocation-failure report
  `0xe8f0 -> 0x9b5e(0x780e2e, 4)`, frame-end cleanup `0xe22c`, and snapshot
  helpers `0xe996`, `0xe972`, and `0xe65c`.
- Unknown: manual-facing names for context-stack fields and overlay state are
  inferred from ROM effects. The over-deep macro context boundary is
  ROM-bounded but intentionally unsafe: reset clears eight 10-byte entries,
  the eighth push ends at pointer `0x782c6e`, the ninth push writes at the
  pointer word itself, and an empty `0xe65c(0)` pop reads from `0x782c14`.

Writers and readers:

- `0xe112` writes current macro id `0x783164`.
- `0xdd08` reads selector records, active frame state, definition state, and
  selected macro record state before dispatching selectors `0..10`.
- `0xe002` appends definition bytes into linked payload chunks and updates
  record count/head fields.
- `0xe418` writes execute/call data-chain frames; `0xe4f4` writes non-replay
  overlay frames; `0xe22c` consumes and unwinds ended frames.
- `0xa904` reads active data-chain frames as a byte source; helper `0x9f6a`
  consumes frame `+0x00/+0x04/+0x08` one payload byte at a time and feeds
  replayed bytes into the same parser wrapper and dispatch loop as live host
  bytes.
- `0xff1e` consumes overlay state during publication; downstream page-record,
  scheduler, and pixel owners consume the objects produced by replayed bytes.

Output effect:

- Macro definition selectors store bytes only; they do not create immediate
  page records or pixels.
- Execute and call selectors make stored bytes visible by turning them into a
  data-chain source for `0xa904`. The visible output is whatever the replayed
  byte stream does through ordinary parser and command-family owners.
- Overlay selectors affect page publication: the stored overlay payload can
  replay before the base page is finalized, unless the page-root retry gate
  suppresses the overlay detour.
- Delete, permanence, and id selectors mutate macro records only, except where
  later execute/call/overlay selectors observe the changed record set.

Evidence and boundaries:

- Disassembly evidence is in
  `generated/disasm/ic30_ic13_macro_record_chain_helpers_00dfba.lst`,
  `generated/disasm/ic30_ic13_macro_environment_snapshot_helpers_00e65c.lst`,
  `generated/disasm/ic30_ic13_pcl_escape_parser_00da9a.lst`, and
  `generated/disasm/ic30_ic13_main_parser_loop_011774.lst`.
- Generated table and xref evidence is in
  `generated/analysis/ic30_ic13_parser_dispatch_tables.md`,
  `generated/analysis/ic30_ic13_tokenizer_macro_callers.md`, and
  `generated/analysis/ic30_ic13_parser_xrefs.md`.
- Fixture evidence is named in the Primary byte-stream examples list above;
  those examples pin record creation, append storage, execute/call replay,
  frame construction/end, overlay publication, and downstream page-record/render
  reuse.
- No unresolved ROM-local middle edge remains for the documented route from
  macro selector parsing through record storage, execute/call replay via
  `0xa904`, page-record queueing, overlay publication, and render entry.
- Remaining boundaries are exact: manual names for macro context/overlay
  latches and physical behavior after an over-deep call stack are outside the
  documented ROM-local dataflow.

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
- Page-root flags word `+0x14` bit 0:
  retry gate that suppresses overlay replay while preserving base page
  publication; the disassembly writes it at byte `+0x15.0`.
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
  push one 10-byte entry; `0xe65c(0)` pops one entry. No guard is present:
  after the eighth reset-cleared slot, `0x782c6e == 0x782c6e`, so a ninth
  push starts by overwriting the pointer storage; an empty pop subtracts to
  `0x782c14` before reading flag bytes.
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
- Covered overlay example coords and rule decoder suffixes are derived/cache
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
- Non-replay overlay examples restore the stored payload bytes as parser
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
- The macro context push/pop paths have no bounds checks in ROM. The exact
  software boundary is known from disassembly and fixture evidence:
  `0xe146` clears eight slots at `0x782c1e..0x782c6d`, call-mode `0xe418`
  and overlay `0xe4f4` push by storing at `0x782c6e` and adding `0x0a`, and
  `0xe65c(0)` pops by subtracting `0x0a` before reading. The ninth push
  starts at `0x782c6e`; an empty pop reads `0x782c14`. What remains external
  is only the physical/user-visible failure symptom after adjacent RAM is
  corrupted.

## Selector Dispatch

`ESC &f#X` reaches `0xdd08`, which rewinds `0x78299e`, resolves the current
macro id through `0xe0a4`, and dispatches the absolute selector through the
ROM list below. The list is canonical command-family behavior; output pixels
appear only when the selected control builds or replays a payload that later
passes through `0xa904`, parser dispatch, page-record queueing, and render
entry.

Selector effects:

- `0`: handler `0xdd86` starts definition mode. Lowercase `x` seeds
  lowercase auto-prefix bytes through `0xe002`; uppercase `X` seeds one zero
  byte in the handler. After `0xdd08` returns, parser-loop branch
  `0x11a04..0x11a9c` can append another zero byte for selector-`0` uppercase
  `X` when the current macro record raw count `+0x04` is greater than `1`.
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

Guard behavior is part of the same selector contract. Disassembly
`0xdd4c..0xdd78` suppresses selector cases while definition mode is active or
an active data-chain frame is present; byte-stream example
`macro command stream respects definition and active-chain guards` exercises
those exits. The alternate/data parser table still routes `x/X` to `0xdd08`,
so selector `1` can stop a definition while payload bytes are otherwise
appended instead of dispatched.

The disassembly-backed selector boundary is:

- `0xdd08..0xdd2e`: reopen the six-byte command record by rewinding
  `0x78299e`, read record word `+2`, and convert the selector to its absolute
  value in `D5`.
- `0xdd2e..0xdd40`: call `0xe0a4` with current macro id `0x783164`; save
  lookup status in `D4`, current/selected record pointer `0x782d7a` in `A4`,
  and active data-chain frame pointer `0x782d76` in `A5`.
- `0xdd4c..0xdd78`: guard selector dispatch. When active frame byte `+9` is
  nonzero, selectors other than execute `2` and call `3` exit without action.
  When definition byte `0x782c18` is `1`, selector `1` may stop the definition
  but other selectors exit without action.
- `0xdd7a..0xdd80`: dispatch selector `D5` through the table at
  `0xdca8..0xdd04`. The table maps selectors `0..10` to
  `0xdd86`, `0xddfc`, `0xde7c`, `0xdea2`, `0xdec8`, `0xdef4`, `0xdefe`,
  `0xdf08`, `0xdf12`, `0xdf24`, and `0xdf36`.
- `0xdd86..0xddfa`: selector `0` starts definition mode. A missing/free record
  sets append-error byte `0x782c19` and definition byte `0x782c18`; an existing
  record is first cleared through `0xdfba`, assigned current id `0x783164`, and
  then put in definition mode. Lowercase final `x` seeds bytes `ESC & f` into
  the definition stream through `0xe002`; uppercase `X` seeds one zero byte
  inside the handler at `0xddf2..0xddf4`. The parser-loop post-handler branch
  `0x11a68..0x11a82` can append a further zero byte when record raw count
  `+0x04` is greater than `1`.
- `0xddfc..0xde7a`: selector `1` stops definition mode. It normalizes raw count
  `record[+4]` by subtracting four header bytes per 0x100-byte chunk, clears
  empty records and lowercase auto-prefix-only records through `0xdfba`, and
  clears `0x782c19` / `0x782c18`.
- `0xde7c..0xde9e` and `0xdea2..0xdec4`: selectors `2` and `3` require a
  selected nonempty record and available frame space before calling
  `0xe418(2)` for execute or `0xe418(3)` for call.
- `0xdec8..0xdefa`: selector `4` enables overlay only when lookup status
  `D4 == 1`, setting `0x782a92 = 1` and copying current id `0x783164` to
  `0x782a94`; otherwise it clears `0x782a92`. Selector `5` clears
  `0x782a92`.
- `0xdefe..0xdf20`: selector `6` calls delete-all helper `0xdf4e`; selector
  `7` calls delete-temporary helper `0xdf80`; selector `8` clears the selected
  current record through `0xdfba` when a record pointer exists.
- `0xdf24..0xdf46`: selectors `9` and `10` require lookup status `D4 == 1`,
  then clear or set record permanence byte `+0x0a`.
- `0xdf4e..0xdf7e`: delete-all iterates 32 records at `0x782a98`, clearing each
  through `0xdfba`.
- `0xdf80..0xdfb8`: delete-temporary iterates the same 32 records, clearing only
  records whose permanence byte `+0x0a` is zero.

## Macro Replay Outcome Matrix

This matrix is the command-family contract for `ESC &f#Y`, `ESC &f#X`,
alternate/data append, execute/call replay, and overlay publication. It
preserves the detailed selector ledger above while grouping outcomes by what a
byte-stream renderer must model next: stored input, replayed parser input,
page-publication mutation, record-only state, or an exact no-output/skip
boundary.

- Macro id selection:
  `ESC &f#Y` reaches `0xe112` and writes current macro id `0x783164`.
  It creates no macro record, frame, page object, or pixels by itself. Later
  `0xdd08`, `0xe0a4`, and overlay publication consume the selected id.
  State class is canonical macro selector state. Evidence:
  `generated/disasm/ic30_ic13_macro_record_chain_helpers_00dfba.lst` and
  parser-table rows in `generated/analysis/ic30_ic13_parser_dispatch_tables.md`.
- Definition start, selector `0`:
  `0xdd08 -> 0xdd86` starts definition mode by writing definition byte
  `0x782c18` and selecting or clearing the current macro record. Existing
  records are cleared through `0xdfba`, the current id `0x783164` is copied to
  record `+0x08`, lowercase `x` seeds `ESC & f` bytes through `0xe002`, and
  uppercase `X` seeds zero bytes through `0xddf2..0xddf4` plus the parser-loop
  branch `0x11a68..0x11a82` when the raw count is already greater than `1`.
  Output effect is stored input only. Evidence: selector disassembly
  `0xdd86..0xddfa` and examples `0xdd08 starts and stops empty macro
  definitions` and `0xe002 appends macro definition bytes into 0x100 chunks`.
- Definition append:
  while definition mode is active, alternate/data routes append bytes through
  `0xe002` instead of dispatching their normal handlers. `0xe002` writes
  payload bytes into linked 0x100-byte chunks, increments record raw count
  `+0x04`, and sets append-error byte `0x782c19` on allocation failure. The
  stored bytes are parser scratch until execute/call/overlay replay returns
  them through `0xa904`. Evidence: append disassembly `0xe002..0xe0a2` and
  examples `0xe002 appends macro definition bytes into 0x100 chunks` and
  `macro command stream respects definition and active-chain guards`.
- Definition stop, selector `1`:
  `0xdd08 -> 0xddfc` stops definition mode, normalizes raw count by subtracting
  four header bytes per chunk, clears empty or auto-prefix-only records through
  `0xdfba`, and clears `0x782c19` / `0x782c18`. Output effect is macro-record
  state only. Later execute/call/overlay selectors decide whether the retained
  payload becomes visible. Evidence: selector disassembly `0xddfc..0xde7a`.
- Execute and call, selectors `2` and `3`:
  `0xdd08 -> 0xde7c` or `0xdea2` requires a selected nonempty record and frame
  space, then calls `0xe418(2)` for execute or `0xe418(3)` for call. `0xe418`
  writes frame `+0x00/+0x04/+0x08/+0x09/+0x0a`, snapshots environment state,
  sets host gate bit `0x780e66.1` when byte count is positive, and pushes a
  10-byte macro context entry for call mode. Consumer `0xa904` gives the frame
  priority as a byte source and sends replayed bytes to parser loop `0x11774`.
  Output effect is whatever the replayed bytes do through their ordinary
  command-family owners. Evidence: `0xe418..0xe4f2`, examples
  `0xdd08 execute and call push macro data-chain frames`,
  `0xe418 frame metadata distinguishes execute and call context`, and
  `macro execute data-chain parser trace feeds page-record stream`.
- Execute/call guard exits:
  selector dispatch at `0xdd4c..0xdd78` suppresses most selector work while a
  data-chain frame is active or while definition mode is active. These exits
  preserve current record/frame state and create no page output. Evidence:
  example `macro command stream respects definition and active-chain guards`.
- Frame-end cleanup:
  when `0xa904` reaches a frame-end marker, `0xe22c..0xe408` unwinds the
  frame, frees snapshots, restores context, clears host gate bit when the
  previous frame has no bytes, and resumes the previous byte source. Call and
  overlay returns can run `0xe65c(0)` to refresh selected-font context state
  before later printable bytes. Output effect is firmware bookkeeping plus
  possible delayed selected-font changes, not immediate pixels. Evidence:
  `generated/disasm/ic30_ic13_macro_environment_snapshot_helpers_00e65c.lst`
  and example `0xe4f4/0xe22c produce and end data-chain frames`.
- Overlay enable and disable, selectors `4` and `5`:
  `0xdd08 -> 0xdec8` enables overlay only when current id lookup succeeds,
  writing overlay state byte `0x782a92 = 1` and saved id `0x782a94`;
  otherwise it clears `0x782a92`. Selector `5` clears `0x782a92`. These
  selectors do not replay bytes immediately. Output effect is delayed
  publication state consumed by `0xff1e`. Evidence: selector disassembly
  `0xdec8..0xdefa` and example `macro command stream enables and disables
  overlay state`.
- Overlay replay at publication:
  publication helper `0xff1e` consumes `0x782a92`, saved id `0x782a94`, root
  flags word `+0x14`, and selected record state. When overlay is enabled, the
  saved record exists, and the page-root retry flag is clear, it calls
  `0xe4f4` to create non-replay frame kind `+9 = 4` with source offset
  `+8 = 4`, then re-enters parser loop `0x11774` before publication
  continues. Output effect is page-object mutation by the replayed payload
  before the base page is published. Evidence: `0xe4f4..0xe5e0`, the
  `Macro Overlay Publication` worked path in
  [firmware-dataflow-model.md](firmware-dataflow-model.md), and examples
  `macro overlay finalization replays before page publication` and
  `macro overlay replays across repeated page publications`.
- Overlay skip gates:
  disabled overlay state, missing or empty record failure from
  `0xe0a4(0x782a94)`, or current page-root retry flag preserve the base page
  publication without creating a non-replay frame. Output effect is no overlay
  page-object mutation. Evidence: example `macro overlay skip gates preserve
  base page publication`.
- Record deletion and permanence, selectors `6..10`:
  selector `6` clears all 32 records through `0xdf4e..0xdf7e`, selector `7`
  clears only temporary records through `0xdf80..0xdfb8`, selector `8` clears
  the selected record through `0xdfba`, selector `9` clears permanence byte
  `+0x0a`, and selector `10` sets permanence byte `+0x0a`. Output effect is
  record-pool state only; later execute/call/overlay lookup observes the
  changed pool. Evidence: selector disassembly `0xdefe..0xdfb8` and example
  `0xdd08 overlay and temporary/permanent macro controls`.
- Overlay payload command families:
  replayed overlay bytes do not have a macro-specific renderer. Covered
  payloads re-enter ordinary owners for printable text, line termination,
  cursor positioning, margins, transparent data, raster rows, and span flush.
  Page objects then publish through `0xff1e`, bridge through
  `0x1ed84 -> 0x1edc6`, and render through `0x1ef6a`. Evidence: overlay
  examples listed in `Output Effect`, including mixed-control, cursor,
  vertical-decipoint, chained-margin, transparent, raster, multi-row raster,
  and span-flush payloads.

State grouping:

- Canonical:
  macro id `0x783164`, record pool `0x782a98`, selected record pointer
  `0x782d7a`, record fields `+0x00/+0x04/+0x08/+0x0a`, frame pointer
  `0x782d76`, frame fields `+0x00/+0x04/+0x08/+0x09/+0x0a`, overlay state
  `0x782a92`, saved overlay id `0x782a94`, and page-root retry flag
  `root+0x14.0`.
- Derived/cache:
  normalized payload count, replayed command-family page objects, selected
  context refresh results, and rendered row products created by downstream
  owners after replay.
- Parser scratch:
  definition-mode parser routing, command-record cursor `0x78299e`, replayed
  bytes from `0xa904`, delayed transparent/raster records, and payload
  counters active inside replayed commands.
- Firmware bookkeeping:
  append-error byte `0x782c19`, host gate bit `0x780e66.1`, heap allocation
  state, snapshot chains, frame cleanup through `0xe22c`, and context
  push/pop helpers.
- Hardware/external:
  none for the ROM-local macro replay model.
- Unknown:
  manual names for context-stack and overlay fields, plus physical symptoms of
  the exact unchecked over-deep context pointer boundary.

Unresolved boundaries:

- No ROM-local middle edge remains for documented definition, execute/call,
  overlay publication, overlay skip-gate, or listed overlay-payload families.
  New macro work should start only when a stream changes one of these exact
  fields: macro record layout, frame fields, skip-gate state, replayed parser
  dispatch, page-object bytes, bridge roots, continuation fields, selected
  context input, or ROM-derived row construction.

### Macro Replay To Visible Consumer Map

This map is the shortest checked-in route from a macro command byte stream to
the next visible consumer. It preserves the selector and frame ledger above
while avoiding a false macro-specific renderer: after `0xa904` returns a
payload byte, the ordinary parser and command-family owners are responsible for
page objects and pixels.

- Macro id and record selection:
  `ESC &f#Y -> 0xe112` writes current id `0x783164`; `ESC &f#X -> 0xdd08`
  and lookup helper `0xe0a4` consume that id and select record pointer
  `0x782d7a` under pool `0x782a98`. The first visible consumer is not a
  renderer; it is a later selector that either appends bytes, builds a frame,
  enables overlay, deletes a record, or marks permanence. Output effect is
  record-state only until selector `2`, `3`, or publication-time overlay
  replay observes the selected record. Evidence: selector ranges
  `0xdd08..0xdd80`, lookup range `0xe0a4..0xe110`, and examples
  `0xe112 stores absolute parsed macro id` and
  `0xe0a4 macro record lookup uses head presence and first free slot`.
- Definition storage:
  selector `0` reaches `0xdd86..0xddfa` and makes alternate/data payload bytes
  append through `0xe002..0xe0a2`. The canonical state is record
  `+0x00/+0x04/+0x08`, append chunk cursor `0x782c1a`, definition byte
  `0x782c18`, and append-error byte `0x782c19`. The first non-macro consumer is
  still absent: stored bytes are input data, not page objects. Selector `1`
  at `0xddfc..0xde7a` normalizes the count and either clears the record through
  `0xdfba` or leaves it available for replay. Boundary: no page/root/render
  edge exists before a replay frame or overlay publication consumes the
  retained record.
- Execute/call replay:
  selectors `2` and `3` reach `0xde7c` / `0xdea2`, then `0xe418..0xe4f2`
  writes active frame `0x782d76` with record head/count at `+0x00/+0x04`,
  source offset `+0x08 = 4`, kind `+0x09 = 2` or `3`, and snapshot pointer
  `+0x0a`. `0xa904` is the first consumer outside the macro selector layer;
  it gives that frame priority over live host input, and `0x9f6a` reads the
  payload bytes. The next boundary is exact:
  `0xa904 -> 0xda9a -> 0x11774`; from there, replayed bytes belong to normal
  owners such as printable `0xd04a`, CR `0xf02c`, line-termination `0xedf8`,
  raster payload `0x105d0`, rectangle/rule `0x10898`, or transparent data
  `0x12452`.
- Replay-created page objects:
  when the replayed stream reaches text owners, `0xd04a -> 0x1393a ->
  0xd3b2/d824 -> 0x12f2e -> 0x1387c` stores compact objects under current
  root `+0x1c`. Raster replay stores mode-0 raster objects through the raster
  owner; rectangle/rule replay stores selector-rule objects through
  `0x10898` / page-record storage; span-producing replay stores selector
  `0x4000` segment-list objects through `0xf34a -> 0x12714`. The first render
  consumers are shared with live bytes:
  `0xff1e -> 0x1ed84 -> 0x1edc6 -> 0x1ef6a`, then compact text `0x1effe`,
  encoded raster `0x1f88e`, segment list `0x1f812`, rule/fixed-list helpers,
  or row-store primitive `0x1effe`-family consumers named in
  [page-raster-imaging.md](page-raster-imaging.md#pixel-generation-owner-summary).
  Macro replay contributes no row writer beyond selecting the ordinary
  replayed command family.
- Overlay publication:
  selector `4` at `0xdec8..0xdefa` writes overlay state `0x782a92` and saved
  id `0x782a94`, but does not replay immediately. Publication helper `0xff1e`
  is the first visible consumer. If overlay state is enabled, lookup of saved
  id succeeds, and root flag `+0x14.0` is clear, `0xff1e` calls
  `0xe4f4..0xe5e0` to build kind-4 frame `0x782d4c`, re-enters
  `0xa904 -> 0x11774`, mutates the same current page-root object graph as live
  bytes, and then continues publication. Disabled state, missing/empty record,
  or retry flag preserve base publication without an overlay frame. Evidence:
  examples `macro overlay finalization replays before page publication`,
  `macro overlay replays across repeated page publications`, and
  `macro overlay skip gates preserve base page publication`.
- Frame cleanup and font-context effects:
  frame-end marker handling in `0xa904` calls `0xe22c..0xe408`. Execute cleanup
  restores snapshot data and resumes the previous source; call and overlay
  cleanup can run `0xe65c(0)` to refresh selected-font context before later
  printable bytes. The visible consumer of `0xe65c` is not the macro engine;
  it is `0xc428` page-root context-slot install followed by the next
  printable route `0xd04a -> 0x1393a -> 0x12f2e` and compact render
  `0x1effe -> 0x1f354`. Boundary: context refresh can change later glyph
  selection, but it creates no page object at `0xe65c`.

## Writers

- `0xe112` writes current macro id `0x783164`.
- `0xe0a4` writes `0x782d7a` to an existing nonempty record, first free
  record, or zero for full-pool miss. On a free path it writes requested id
  into record `+0x08`.
- `0xdd08` rewinds `0x78299e`, dispatches selectors `0..10`, and writes
  definition, execute/call, overlay, delete, temporary, and permanent state.
- Byte-stream examples `0xdd08 overlay and temporary/permanent macro controls`
  and `macro command stream respects definition and active-chain guards`
  exercise the selector branches and guard behavior described above.
- `0xdd86..0xde7a` starts/stops definition mode, seeds lowercase `ESC &f`
  auto-prefix bytes or uppercase zero bytes through `0xe002`, normalizes
  counts, and clears empty or auto-prefix-only records through `0xdfba`.
  The uppercase zero-byte case has two ROM sites: handler `0xddf2..0xddf4`
  and parser-loop branch `0x11a68..0x11a82` after `0xdd08` returns.
- `0xe002` appends definition bytes into linked 0x100-byte chunks, links new
  chunks, updates record raw count `+0x04`, and sets `0x782c19` on allocation
  failure.
- Byte-stream example `0xe002 appends macro definition bytes into 0x100 chunks`
  exercises the chunk format: a longword next pointer followed by 252 payload
  bytes, raw counts including four header bytes per chunk, and the transition
  to a linked second chunk after the first 252 payload bytes.
- `0xe418` writes execute/call data-chain frames, environment snapshot pointer
  `+0x0a`, and the call-only context-stack entry.
- Byte-stream examples `0xdd08 execute and call push macro data-chain frames`
  and `0xe418 frame metadata distinguishes execute and call context` exercise
  frame bytes `+8 = 4`, `+9 = 2` for execute, `+9 = 3` for call, and the
  call-only context push.
- `0xe4f4` writes the non-replay overlay frame at `0x782d4c`, writes
  `0x782d76`, saves cursor longword `0x782c92`, snapshots flat state, and may
  set host gate bit 1.
- `0xe22c` unwinds frames, frees snapshot chunks, rewinds `0x782d76` for
  execute/call frames, and writes `0x782a92 = 0x63` on non-execute/non-call
  frame return.
- Byte-stream example `0xe4f4/0xe22c produce and end data-chain frames`
  exercises the non-replay frame producer and the matching end-frame cleanup.
  Example `macro snapshot helpers copy linked and flat environment ranges`
  exercises the linked `0xe8f0` / `0xe8a2` snapshot chain and flat `0xe972` /
  `0xe996` copy helpers used by those frame paths.
- `0x164a` initializes the heap bitmap and allocator fields.
- `0x170c` / `0x1710` allocate 64-byte heap units; `0x18b4` frees linked
  macro/snapshot chains when count is zero.
- `0xe65c(0)` pops macro call-context entries; `0xe65c(1)` consumes static
  context record `0x782c64`.
- Examples `0xe65c refreshes macro font context entries` and `0xe65c refresh
  composes with font context bridge` exercise the bridge from macro context
  flags through `0x13eb8`, `0x144d2`, `0x14c64`, and final `0xc428` page-root
  font-slot install. Example `0xe146/e418/e4f4/e65c macro context stack has
  eight records and no guard` records the reset-cleared stack bounds and the
  lack of ROM-side push/pop guard checks.

## Replay Frame Boundaries

Macro replay turns stored bytes back into parser input through data-chain
frames:

- `0xe002..0xe0a2` appends definition bytes only when active frame byte `+9`
  is zero and append-error byte `0x782c19` is clear. It allocates a new
  0x100-byte chunk through `0x170c` when the current raw count low byte is zero,
  stores payload at chunk offset `4 + ((record[+4] & 0xff) - 4)`, increments
  raw count `record[+4]`, and links chunks through their first longword.
- `0xe0a4..0xe110` scans the 32-entry record pool. A matching id with nonzero
  head pointer selects that record and returns status `1`; otherwise the first
  empty record is remembered, assigned the requested id, selected, and returns
  status `0`; if no free record exists it clears `0x782d7a` and returns
  status `2`.
- `0xe418..0xe4f2` creates execute/call frames. It advances from the current
  `0x782d76` frame by 14 bytes, copies selected record head/count into frame
  `+0x00/+0x04`, writes byte-source offset `+0x08 = 4`, writes frame kind
  `+0x09` from the execute/call selector, creates a linked snapshot at
  `+0x0a` through `0xe8f0`, sets host gate bit `0x780e66.1` when byte count is
  positive, and for call mode pushes a 10-byte macro context entry under
  `0x782c6e`.
- `0xe4f4..0xe5e0` creates non-replay overlay frames. It pushes a macro context
  entry, snapshots selected context and flat state, saves cursor longword
  `0x782c92`, runs page/layout refresh helper `0xe5e2`, installs frame
  `0x782d4c` into `0x782d76`, copies selected record head/count, writes
  `+0x08 = 4`, `+0x09 = 4`, and `+0x0a = 0`, and sets host gate bit
  `0x780e66.1` if the frame has bytes.
- `0xe22c..0xe408` unwinds frames after the host byte source reaches their end.
  Execute frames restore linked environment snapshot data, free the snapshot,
  rewind `0x782d76`, and clear host gate bit if the previous frame has no byte
  count. Call and overlay returns restore saved context, may publish through
  `0xf124`, restore cursor/layout state, call `0xe65c(0)`, and for non-replay
  frames write `0x782a92 = 0x63`.

### Data-Chain Source-Equivalence Checkpoint

This checkpoint is the exact boundary where macro storage stops being record
state and becomes ordinary parser input again. It is the reproducer contract
for stored byte streams: once `0xa904` selects an active data-chain frame, the
returned payload bytes must be followed through the same `0xda9a` /
`0x11774` parser and command-family owners as live host bytes.

Decision route:

- Definition bytes enter storage through append helper `0xe002..0xe0a2`.
  `0xe002` refuses to append when the active frame kind byte at
  `0x782d76 + 9` is nonzero or append-error byte `0x782c19` is already set.
  Otherwise it uses current record pointer `0x782d7a`, current chunk pointer
  `0x782c1a`, and raw count `record+0x04` to allocate/link 0x100-byte chunks
  and store each byte at chunk offset `4 + ((record+0x04 & 0xff) - 4)`.
- Execute and call frames are built by `0xe418..0xe4f2` only after selector
  handler `0xdd08` has resolved a nonempty selected record. The frame copies
  record head/count to `+0x00/+0x04`, stores byte-source offset `+0x08 = 4`,
  stores frame kind `+0x09 = 2` for execute or `3` for call, stores snapshot
  pointer `+0x0a`, and installs the frame by writing `0x782d76`.
- Overlay frames are built by `0xe4f4..0xe5e0` from publication, not from a
  direct parser terminal. They snapshot context, install fixed frame base
  `0x782d4c` into `0x782d76`, copy the selected record head/count, store
  `+0x08 = 4`, store frame kind `+0x09 = 4`, clear `+0x0a`, and set host gate
  bit `0x780e66.1` when the frame count is positive.
- Host byte source `0xa904` owns the source switch. The macro note's frame
  contract starts before `0xa904` returns a payload byte and ends after that
  byte has re-entered `0xda9a` / `0x11774`; parser outcomes then belong to
  the same owner notes as live bytes. The exact source-priority behavior is in
  [host-byte-fetch.md](host-byte-fetch.md#active-data-chain).
- Data-chain byte reader `0x9f6a` is the byte-level consumer for the active
  frame after caller `0xa904` has proved frame count `+0x04` is nonzero and
  not the `-1` end marker. Range `0x9f72..0x9f84` loads current frame pointer
  `0x782d76`, reads chunk pointer `+0x00`, adds unsigned offset byte `+0x08`,
  and returns the payload byte from that chunk address in `D7`.
- Reader range `0x9f88..0x9fa8` advances the replay cursor. Offset `+0x08`
  increments while below `0xff`; when it reaches `0xff`, the helper resets
  `+0x08` to `4` and replaces frame `+0x00` with the longword stored at the
  start of the current chunk. That longword is therefore the next-chunk link,
  and payload bytes are the chunk bytes at offsets `4..0xff`.
- Reader range `0x9fac..0x9fb4` decrements remaining count `+0x04` after the
  byte has been fetched. A transition to zero writes `-1` back to `+0x04`
  instead of calling cleanup directly; the following `0xa904` pass clears that
  marker, calls `0xe22c`, and restarts source selection. Range
  `0x9fb8..0x9fca` reports literal payload `0x1a` through `0x9ec0` while
  preserving the same `0x1a` return byte in `D7`.
- Frame-end cleanup `0xe22c..0xe408` is the return boundary. Execute frames
  restore linked snapshot data and rewind `0x782d76`; call and overlay returns
  restore flat/context state, can run `0xf124` or `0xe65c(0)`, and then push a
  zero byte through `0x9ec0` at `0xe408..0xe410`. If the previous frame has no
  remaining count, cleanup clears host gate bit `0x780e66.1`.

State classification:

- Canonical macro state:
  record head/count/id/permanence fields `+0x00/+0x04/+0x08/+0x0a`, selected
  record pointer `0x782d7a`, active frame pointer `0x782d76`, and frame fields
  `+0x00/+0x04/+0x08/+0x09/+0x0a`.
- Parser scratch:
  definition routing byte `0x782c18`, append-error byte `0x782c19`, current
  chunk cursor `0x782c1a`, replayed payload bytes returned by `0xa904`, and
  the parser records built later by `0xdb74` / `0xdaf0` from those bytes.
- Firmware bookkeeping:
  host gate bit `0x780e66.1`, chunk-link longword at payload chunk offset
  `0`, end marker `frame+0x04 = -1`, linked snapshot allocation/free through
  `0xe8f0` / `0x18b4`, call-context pointer `0x782c6e`, overlay restore byte
  `0x782a92`, context refresh `0xe65c`, and the `0x9ec0(0)` cleanup report.
- Canonical page/render state:
  none is written by the source switch itself. Page objects appear only after
  replayed bytes dispatch to their ordinary owners, for example printable
  `0xd04a`, CR `0xf02c`, raster delayed transfer `0x105d0`, transparent data
  `0x12452`, or rectangle/rule handlers.
- Unknown:
  no ROM-local middle edge remains between stored macro payload bytes and the
  parser source contract. Remaining macro uncertainties are manual names for
  context/overlay latches and physical behavior after intentionally unsafe
  over-deep context-stack use.

Output effect:

- Definition append has no page output. It creates stored input bytes only.
- Execute and call output begins when `0xa904` returns the frame payload bytes
  and parser loop `0x11774` dispatches them. The visible result is therefore
  the same text, control, raster, rectangle, transparent, macro, or no-output
  outcome that the identical live byte stream would take.
- Overlay output is a publication-time mutation. `0xff1e` can build a kind-4
  frame through `0xe4f4`, replay stored bytes into the current page context,
  and then continue the normal publication/bridge/render route.

Evidence:

- Append and frame construction:
  `generated/disasm/ic30_ic13_macro_record_chain_helpers_00dfba.lst`
  ranges `0xe002..0xe0a2`, `0xe418..0xe4f2`, and `0xe4f4..0xe5e0`.
- Frame cleanup:
  the same listing range `0xe22c..0xe408`.
- Source selection:
  [host-byte-fetch.md](host-byte-fetch.md#active-data-chain) and the
  host-byte source listing `generated/disasm/ic30_ic13_host_byte_fetch_00a904.lst`.
- Byte-level replay:
  `generated/disasm/ic30_ic13_data_chain_byte_reader_009f6a.lst`, covering
  chunk pointer/offset reads at `0x9f72..0x9f84`, chunk advancement at
  `0x9f88..0x9fa8`, count/end-marker update at `0x9fac..0x9fb4`, and
  literal-`0x1a` reporting at `0x9fb8..0x9fca`.
- Parser re-entry and downstream owners:
  `generated/disasm/ic30_ic13_main_parser_loop_011774.lst`,
  [pcl-parser-core.md](pcl-parser-core.md#inbound-byte-outcome-contract),
  and the execute/call replay fixtures named below.

## Execute/Call Replay To Page Objects Checkpoint

This checkpoint composes the representative execute/call replay path from
stored macro bytes into visible page objects. It covers stored `!\r` and
stored `ESC &k1G!\r!`, which are broad enough to cross macro definition,
execute/call frame construction, replay byte fetch, line-termination state,
printable text, carriage return, page-record storage, publication bridge, and
render entry.

Byte streams:

- `ESC &f123Y ESC &f0X ! CR ESC &f1X ESC &f2X` selects macro id `123`,
  starts definition, stores bytes `21 0d`, stops definition, executes the
  selected record, and replays the payload as parser input.
- The call sibling replaces final selector `2` with selector `3`; it uses the
  same stored payload and page-object route after the call frame is active.
- `ESC &f125Y ESC &f0X ESC &k1G ! CR ! ESC &f1X ESC &f2X` stores a mixed
  line-termination payload, executes it, and replays it through both a
  state-only text-mode command and printable/CR handlers.

Writers:

- `0xe112` writes current macro id `0x783164` from `ESC &f#Y`.
- `0xdd08 -> 0xdd86` starts definition mode, assigns the selected record under
  `0x782d7a`, and allows alternate/data parser routing to append payload bytes.
- `0xe002` writes stored bytes into linked chunks, updates record head `+0x00`
  and raw byte count `+0x04`, and leaves those bytes invisible until replay.
- `0xdd08 -> 0xddfc` stops definition mode and normalizes the retained payload
  count.
- `0xdd08 -> 0xde7c` and `0xdd08 -> 0xdea2` build execute and call frames
  through `0xe418`, copying record head/count into frame `+0x00/+0x04` and
  writing source byte `+0x08 = 4`, frame kind `+0x09 = 2` or `3`, and snapshot
  pointer `+0x0a`.
- For call mode, `0xe418` also pushes one macro context record under
  `0x782c6e`; that context may later affect selected font state through
  `0xe65c`, but it does not create the page object for the covered stored
  `!\r` text by itself.

Readers and consumers:

- `0xa904` consumes active frame `0x782d76` before live host bytes, returns the
  stored payload bytes, and calls `0xe22c` at frame end.
- Parser loop `0x11774` treats replay bytes as normal parser input. For `!\r`,
  it dispatches printable `0x21` through `0xd04a` and CR through `0xf02c`.
- For `ESC &k1G!\r!`, `0x11774` reaches line-termination handler `0xedf8`,
  then dispatches printable, CR, and printable bytes through `0xd04a`,
  `0xf02c`, and `0xd04a`.
- Page-record consumers are the ordinary text pipeline:
  `0xd04a -> 0x1393a -> 0xd3b2/d824 -> 0x12f2e`, followed by page publication
  `0xff1e`, bridge `0x1ed84 -> 0x1edc6`, and render entry `0x1ef6a`.

Output effect:

- Definition selectors store bytes only. No page object or pixel is produced
  until selector `2`, selector `3`, or overlay publication replays the stored
  payload through `0xa904`.
- Execute replay of stored `!\r` queues the same compact text object and CR
  state transition as direct host bytes `21 0d`. The render route is the
  shared compact-text path; macro replay contributes no separate renderer.
- Call replay uses the same visible text route after the call frame has become
  the active data-chain source. Its additional context stack write is delayed
  font/context state, not a page-object writer for this payload.
- Mixed-control replay first changes line-termination state through `0xedf8`,
  then queues compact text from the replayed printable bytes and applies CR
  through the same page-record route as live input.

Field classification:

- Canonical state: current macro id `0x783164`, macro record pool
  `0x782a98`, selected record pointer `0x782d7a`, record head/count/id fields
  `+0x00/+0x04/+0x08`, active frame pointer `0x782d76`, frame fields
  `+0x00/+0x04/+0x08/+0x09/+0x0a`, line-termination mode written by `0xedf8`,
  page-root bucket/context fields consumed by `0x12f2e`, and published record
  fields copied by `0x1ed84` / `0x1edc6`.
- Derived/cache state: normalized payload count from selector `1`, replayed
  compact object coordinates, selected glyph/context cache, bridge-local
  render roots, and row products derived by compact text render helpers.
- Parser scratch: mode-17 `ESC &f` command records, alternate/data append
  routing, definition bytes `0x782c18` / `0x782c19`, command-record cursor
  `0x78299e`, replay bytes returned by `0xa904`, and the temporary command
  records for replayed `ESC &k1G`.
- Firmware bookkeeping: append allocation state, host gate bit
  `0x780e66.1`, snapshot chain pointer `+0x0a`, frame cleanup through
  `0xe22c`, and call-context push/pop bookkeeping.
- Hardware/external state: none for the ROM-local replay-to-page-object
  handoff. Physical host timing is upstream of stored bytes, and physical
  engine output is downstream of the ROM render entries named here.
- Unknown: no ROM-local middle edge remains for the documented `!\r` and
  `ESC &k1G!\r!` execute/call payloads. New work in this subpath must change
  a specific stored byte sequence, replay parser handler, page-object byte,
  publication/bridge field, context refresh input, or render helper input.

Evidence:

- Macro selector, definition, and frame disassembly:
  `generated/disasm/ic30_ic13_macro_record_chain_helpers_00dfba.lst`.
- Replay source and parser loop evidence:
  `generated/disasm/ic30_ic13_main_parser_loop_011774.lst` and parser-table
  rows in `generated/analysis/ic30_ic13_parser_dispatch_tables.md`.
- Font/context unwind evidence for the call-side delayed state:
  `generated/disasm/ic30_ic13_macro_environment_snapshot_helpers_00e65c.lst`.
- Page-object and render bridge evidence:
  [page-record-storage.md](page-record-storage.md),
  [page-raster-imaging.md](page-raster-imaging.md), and
  [semantic-state-model.md](semantic-state-model.md).
- Byte-stream evidence:
  `macro execute frame payload feeds 0xa904 data-chain bytes`,
  `macro execute data-chain parser trace feeds page-record stream`,
  `macro call data-chain parser trace feeds page-record stream`,
  `macro execute payload queues printable glyph then applies CR`,
  `macro execute payload page-record bridge renders queued glyph`,
  `macro execute mixed control payload replays through page-record stream`,
  `macro execute page-record layer composes with rule and raster band`,
  `host-fetched macro replay payloads preserve 0x1edc6 bridge contract`, and
  `host-fetched macro replay payloads feed 0x1ed84 and 0x1ef6a`.

Macro font-context refresh at `0xe65c` is the bridge from replay bookkeeping
back to the normal selected-font and printable-glyph model:

- `0xe65c..0xe6aa`: mode `0` pops one 10-byte context record. It subtracts
  `10` from stack pointer `0x782c6e`, reads popped flags `+8/+9`, and for
  primary flag `+8 == 1` calls `0x13eb8(0)`, copies `0x783144` to `0x782f08`,
  and sets dirty byte `0x782f2d` only when selected slot `0x782f06` is primary.
- `0xe6dc..0xe714`: the same popped-record path handles secondary flag
  `+9 == 1`: it calls `0x13eb8(1)`, copies `0x783146` to `0x782f0a`, and sets
  `0x782f2d` only when selected slot `0x782f06` is secondary.
- `0xe6ac..0xe6d8`, `0xe7d0..0xe7f2`, and `0xe7f2..0xe848`: mode `1` uses
  static record `0x782c64`. Flag byte `+8` forces primary refresh; otherwise
  helper `0xe860(0)` compares the selected primary context's stored orientation
  byte against current orientation `0x782da3` and refreshes on mismatch. Flag
  byte `+9` or `0xe860(1)` mismatch does the same for secondary refresh.
- `0xe714..0xe722`: after the slot-specific refresh decisions, the consumed
  record is cleared: longwords `+0/+4` and flag bytes `+8/+9` become zero.
- `0xe722..0xe84c`: selected-slot reinstall. The helper calls `0xc428` for
  current selected slot `0x782f06`. If that call returns zero, it restores
  context pointer `0x782c80` and metric word `0x782c84` into the selected
  `0x782ee6 + 0x10 * slot` and `0x783144 + 2 * slot`, writes `0x7828de`,
  resolves the active object through `0x1b4c0`, then calls `0x144d2`,
  `0x14c64`, and `0xc428` again.
- `0xe84c..0xe85e`: common exit calls `0x1b04c`, clears dirty byte
  `0x782f2d`, restores registers, and returns.
- `0xe860..0xe8a0`: orientation helper. It selects `0x782ee6 + 0x10 * slot`,
  reads byte `+0x16` from fixed-record contexts or byte `+0x20` from
  offset-table contexts, and returns that byte in `D7`.

The output effect is delayed: `0xe65c` creates no page object itself. It
refreshes selected-font state consumed by the next printable byte through
`0xd04a`, `0xd3b2` / `0xd824`, and the compact object path. Canonical state is
the selected context and metric fields; derived/cache state is the active object
lookup at `0x7828a8`; firmware bookkeeping is the macro context record and dirty
byte `0x782f2d`.

## Macro Context To Font Slot Checkpoint

This checkpoint composes the state block where macro call/overlay unwind can
change later printable glyph output. The macro engine does not have a private
font renderer. It restores or refreshes selected-font state through `0xe65c`,
then hands the result to the same page-root context-slot installer and compact
render path used by live host bytes.

Writers:

- Call-mode frame builder `0xe418` and non-replay overlay builder `0xe4f4`
  push one 10-byte macro context entry under `0x782c6e`. Entry bytes `+8` and
  `+9` are the primary and secondary refresh flags consumed by `0xe65c`.
- `0xe65c(0)` pops one entry at `0xe66a..0xe676`, reads flag byte `+8` at
  `0xe67c..0xe686`, and when set calls `0x13eb8(0)`, copies active symbol word
  `0x783144` to remembered word `0x782f08`, and marks dirty byte
  `0x782f2d` if primary is the selected slot `0x782f06`.
- The same popped-entry path reads flag byte `+9` at `0xe6dc..0xe6e6`; when
  set it calls `0x13eb8(1)`, copies `0x783146` to `0x782f0a`, and marks
  `0x782f2d` when secondary is selected.
- `0xe65c(1)` uses static context record `0x782c64`. It refreshes primary or
  secondary when flag bytes request it, or when orientation helper
  `0xe860(slot)` reports a selected context orientation byte different from
  current orientation `0x782da3`.
- `0xe722..0xe84c` calls `0xc428(0x782f06)` to install or reuse the selected
  page-root context slot. If the first install fails with zero, it restores
  `0x782c80` / `0x782c84` into the selected current-font RAM record and
  remembered metric word, runs `0x1b4c0`, `0x144d2`, and `0x14c64`, marks
  `0x782f2d`, and calls `0xc428` again.
- Common exit `0xe84c..0xe85e` calls `0x1b04c`, clears dirty byte
  `0x782f2d`, and returns to the frame-unwind or overlay path.

Readers and consumers:

- `0xc428 -> 0xc4fc` reads current-font RAM record `0x782ee6 + 0x10 * slot`
  and writes the selected context/resource longword into page-root slots
  `+0x2c..+0x68` when a current page root exists.
- The next printable byte consumes the selected slot through
  `0xd04a -> 0x1393a -> 0xd3b2/d824 -> 0x12f2e`, stores page-root slot
  `0x78297e` into the compact object/source state, and marks live flag
  `0x78297f + slot`.
- Publication and rendering consume the result through the shared route:
  `0xff1e` preserves page-root slots, `0x1edc6` copies them to render slots
  `+0x24..+0x60`, `0x1effe` loads one copied slot into `0x783a2c`, and
  `0x1f354` resolves glyph bitmap bytes from that selected context.

Output effect: macro context restore can change later glyph pixels only by
changing selected context records, remembered symbol words, map rebuild state,
page-root context slots, or printable object slot selectors. It does not draw
at `0xe65c`, and it does not create a macro-specific page-object or render
helper.

Field classification:

- Canonical macro context state: stack entries `0x782c1e..0x782c6d`, stack
  pointer `0x782c6e`, static context record `0x782c64`, and entry refresh
  flags `+8/+9`.
- Canonical font/context state: selected slot `0x782f06`, remembered symbol
  words `0x782f08` / `0x782f0a`, current-font RAM records
  `0x782ee6` / `0x782ef6`, selected object pointer `0x7828a8`, page-root slot
  byte `0x78297e`, page-root context slots `+0x2c..+0x68`, and render context
  slots `+0x24..+0x60`.
- Derived/cache state: dirty byte `0x782f2d`, active symbol words
  `0x783144` / `0x783146`, map rebuild output from `0x14c64`, orientation
  comparison result from `0xe860`, and compact render context cache
  `0x783a2c`.
- Parser scratch: none. Replay bytes and parser records have already selected
  execute/call or overlay frame unwinding before this context refresh runs.
- Firmware bookkeeping: context push/pop pointer arithmetic, frame kind bytes
  `+9`, snapshot/free bookkeeping, and common exit cleanup through `0x1b04c`.
- Unknown: no ROM-local middle edge remains for the documented context-refresh
  handoff into page-root context slots. The over-deep stack boundary remains
  the exact unchecked pointer range named in this note; physical symptoms of
  adjacent RAM corruption are outside the ROM-local pixel model.

Evidence and unresolved boundaries:

- Macro writer evidence:
  `generated/disasm/ic30_ic13_macro_environment_snapshot_helpers_00e65c.lst`
  `0xe65c..0xe85e` and `0xe860..0xe8a0`.
- Font/page-slot evidence: `generated/disasm/ic30_ic13_font_context_install_00c428.lst`
  `0xc428..0xc57e` and [Context Slot Preservation
  Checkpoint](page-record-storage.md#context-slot-preservation-checkpoint).
- End-to-end evidence:
  examples `0xe65c refresh composes with font context bridge`,
  `macro execute data-chain parser trace feeds page-record stream`,
  `macro call data-chain parser trace feeds page-record stream`, and the
  overlay payload examples listed above.
- Remaining work must change a concrete field in this handoff: context entry
  flags, selected slot `0x782f06`, restored context longword `0x782c80`,
  metric word `0x782c84`, `0xc428` slot-install result, page-root slot
  `0x78297e`, compact object selector, or `0x1f354` context input.

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
then `0xf02c`, and queues the same text object as direct host bytes. The call
selector `3` follows the same parser and page-record path for the covered text
payload.

The parser-facing macro command stream is documented at both the handler and
host-fetched levels. Example `0x11774 ROM dispatch table routes chained ESC &f
macro stream` records normal mode-17 dispatch to `0xe112` and `0xdd08`.
Example `macro command stream assigns id and starts/stops empty definition`
records `ESC &f#Y`, selector `0` start, selector `1` stop, and
empty-definition cleanup. Example `host-fetched macro command streams update
records and frames` runs the same state updates from a modeled `0xa904` ring
source.

Replay output is a consequence of replayed bytes re-entering the same parser
and page-record pipeline as live input. Example `macro execute payload queues
printable glyph then applies CR` records stored `!\r` re-entering `0xd04a` and
`0xf02c`. Example `macro execute payload page-record bridge renders queued
glyph` carries that queued object through `0x1edc6` and render entry. Example
`macro execute data-chain replay feeds page-record stream` records replayed
data-chain bytes feeding the same page-record stream as host bytes. Example
`macro execute mixed control payload replays through page-record stream` covers
the mixed-control sibling `ESC &k1G!\r!`. Example `macro execute page-record
layer composes with rule and raster band` records macro-replayed text composing
with selector-7 rule and mode-0 raster objects in one render band.

The mixed-control execute example stores `ESC &k1G!\r!`, builds an execute
frame, replays through `0xedf8`, `0xd04a`, `0xf02c`, and `0xd04a`, then follows
the direct mixed-stream bridge/render path through `0x1edc6`, `0x1ed84`, and
`0x1ef6a`.

Overlay publication enters from `0xff1e`, not from the host parser directly.
With selector `4` enabled, `0xff1e` resolves `0x782a94` through `0xe0a4`,
calls `0xe4f4`, re-enters parser loop `0x11774`, and publishes the replayed
payload into the same page record. Example `macro overlay finalization replays
before page publication` records stored `!\r` composing with an existing
selector-7 rectangle rule.

Example `macro overlay replays across repeated page publications` records the
enabled overlay state surviving two page boundaries; both pages replay `!\r`
before publication and compose with page-specific selector-7 rules.

Example `macro overlay skip gates preserve base page publication` records the
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

The byte-stream example matrix records these ROM-derived page-object and render
inputs:

- Repeated overlay publication replays `!\r` on two page boundaries. The first
  page composes with selector-7 rule object
  `00 00 00 00 01 07 88 01 00 0c 00 03 00 00`.
  Example row digest:
  `0629159c6a0f5c4a23508d5bfab14b725e13f0bfa32b82efca091aec425fa4c0`.
  The second page composes with selector-7 rule object
  `00 00 00 00 01 07 e4 00 00 08 00 04 00 00`.
  Example row digest:
  `2d52675c52b22b80e87a379e32894c7a9638596770093d2fd80b64e25559977e`.
- The skip-gate example publishes base printable `?` plus selector-7 rule
  `00 00 00 00 01 07 a2 00 00 06 00 02 00 00`. Disabled overlay mode,
  missing selected record, and page-root retry flag preserve the same example
  row digest:
  `425e0a2abf918906a45f655b589c615108f72ca6b89dc1b280b99121e4405e43`.
- Mixed-control overlay payload `ESC &k1G!\r!` writes line-termination mode
  `0x80`, queues compact text payload `00 02 20 00 01 20 3b 00`, and
  composes with selector-7 rule
  `00 00 00 00 01 07 cc 01 00 08 00 02 00 00`, mutated by `0x1f596` to
  `00 00 00 00 01 07 cc 01 00 08 00 02 ff ce`. Example row digest:
  `04d32edf47d03c587abc0abaf750c6a2d634ceea80df9787681b618867136f52`.
- Cursor-position overlay payload `ESC &a2C!` routes through `0xf39e`, moves
  packed horizontal cursor `10 -> 36`, queues compact text payload
  `00 01 20 0a 02`, and composes with selector-7 rule
  `00 00 00 00 01 07 82 02 00 07 00 02 00 00`, mutated to
  `00 00 00 00 01 07 82 02 00 07 00 02 ff ca`. Example row digest:
  `ba32af7d183a956b2abd821b2143e9c7c3eecf87a7b1403fa086cfe6bf89c8ae`.
- Vertical-decipoint overlay payload `ESC &a72V!` routes through `0xf60a`,
  moves packed vertical cursor `20 -> 30`, queues compact text payload
  `00 01 20 90 01` at coord `0x9001`, and composes with selector-7 rule
  `00 00 00 00 01 07 88 01 00 07 00 02 00 00`, mutated to
  `00 00 00 00 01 07 88 01 00 07 00 02 ff ca`. Example row digest:
  `7ef1cc5d5557fa5a30c57e8ad6918b09747c210daed2639e9d75ccfed727e964`.
- Chained cursor-position overlay payload `ESC &a2c+1R!` routes through
  `0xf39e`, parser mode `12`, `0xf560`, and `0xd04a`; moves packed cursor
  `(10, 21) -> (36, 24)`; queues compact text payload `00 01 20 3a 02`; and
  composes with selector-7 rule
  `00 00 00 00 01 07 a6 02 00 06 00 02 00 00`, mutated to
  `00 00 00 00 01 07 a6 02 00 06 00 02 ff cc`. Example row digest:
  `0275857ffbcc11aa5234644930ebcd31571c2178eaf52b79590989d31b39f653`.
- Chained margin overlay payload `ESC &a6l9M!` routes through `0xeb58`,
  parser mode `12`, `0xec0c`, and `0xd04a`; writes packed left/right margins
  `108` / `180`; queues compact text payload `00 01 20 02 07`; and composes
  with selector-7 rule `00 00 00 00 01 07 6c 02 00 05 00 02 00 00`, mutated
  to `00 00 00 00 01 07 6c 02 00 05 00 02 ff c8`. Example row digest:
  `ecae0043ee656ceba42d4d6e052e3d56a365eeb4a847b3b430f80eed72b5a199`.
- Transparent overlay payload `ESC &p2X!!` reaches `0x11f5a`, saves delayed
  record `80 58 00 02 00 00`, restores it through `0x12452`, routes raw
  bytes `21 21` through `0xd04a`, and queues compact text object prefix
  `00 00 00 00 00 00 00 02 20 00 01 20 02 02`. The selector-7 rule
  `00 00 00 00 01 07 e0 02 00 09 00 02 00 00` mutates to
  `00 00 00 00 01 07 e0 02 00 09 00 02 ff d0`. Example row digest:
  `1ee999b850b4a35aa2b01b72ae01da961ee4084f0369f4ded5c8e8152464dac8`.
- Raster overlay payload `! ESC *t300R ESC *r0A ESC *b2W c3 3c` builds a
  20-byte non-replay frame, queues compact text plus mode-0 raster object
  `00 00 00 00 80 00 00 02 00 00 c3 3c`, and mutates selector-7 rule
  `00 00 00 00 01 07 44 01 00 0a 00 02 00 00` to
  `00 00 00 00 01 07 44 01 00 0a 00 02 ff c6`. Example row digest:
  `bc21050018fd3e992709c704fff732499aa9d06565de31d7ae0340869971c5b3`.
- Multi-row raster overlay payload
  `! ESC *t300R ESC *r0A ESC *b2W f0 0f ESC *b2W 0f f0` builds a 27-byte
  non-replay frame, queues raster objects
  `00 00 00 00 80 00 00 02 00 00 f0 0f` and
  `00 00 00 00 80 00 00 02 10 00 0f f0`, advances raster `row_y` to `2`,
  and bridges the bucket chain as second raster row, first raster row, compact
  text. Example row digest:
  `58c2293bbc6b187db0e964571e5812ab2192d32d8e648a38d61e407a58538638`.
- Span-flush overlay payload `ESC &a6L!` routes through `0xeb58`, `0xf34a`,
  `0x12714`, `0x126e2`, and `0xd04a`. It writes packed left margin `108`,
  publishes selector-`0x4000` segment-list object
  `00 00 00 00 40 00 00 01 32 00 03 00 00 10`, re-arms
  `0x783186..0x78318a` to `108/108/0`, queues compact object prefix
  `00 00 00 00 00 00 00 01 20 02 07`, and mutates selector-7 rule
  `00 00 00 00 01 07 a4 02 00 07 00 02 00 00` to
  `00 00 00 00 01 07 a4 02 00 07 00 02 ff cc`. Example row digest:
  `6775414374ba3c31f7846a180d93cc9b68e230ea6981ae722b32eb39081f9bca`.

All covered overlay payloads publish through `0xff1e`, bridge through
`0x1edc6`, and render through `0x1ed84` / `0x1ef6a`. Remaining edges are no
longer inside the listed payload paths. A new overlay stream matters here only
if it exposes different ROM-local output fields or a different row derivation
path inside the ROM render helpers.

Overlay variant boundary map:

- Overlay selection is canonical macro/page state: `ESC &f4X` stores overlay
  mode in `0x782a92` and overlay id in `0x782a94`; `ESC &f5X` clears that
  mode. Page publication `0xff1e` consumes both fields plus current page-root
  flags word `+0x14` bit 0 before deciding whether overlay replay can run.
- Skip gates are exact: disabled overlay mode, missing/nonempty macro record
  lookup through `0xe0a4(0x782a94)`, and page-root retry flag all preserve the
  base page publication without producing a non-replay frame.
- `0xe4f4` produces the non-replay frame. Canonical replay-frame fields are
  frame `+0x00` source chunk pointer, frame `+0x04` byte count, frame
  `+0x08 = 4`, frame `+0x09 = 4`, frame `+0x0a = 0`, saved cursor
  `0x782c92`, selected context byte `0x782f06`, and host gate bit 1 in
  `0x780e66`. Snapshot helpers `0xe996` / `0xe972` are firmware
  bookkeeping, not page content.
- Replay parser scratch is the stored payload byte stream consumed through
  `0xa904`, parser mode in `0x782999`, alternate/data state when a replayed
  command enters a delayed payload mode, restored transparent record
  `80 58 ...`, restored raster record `80 57 ...`, and delayed payload
  counters/offsets. A new overlay variant is only a new parser edge if it
  reaches a handler or delayed-payload branch outside the listed payload
  matrix.
- Page-output fields are produced by the replayed handlers, not by the macro
  engine directly: compact text and encoded raster bucket objects under
  page-root `+0x1c`, selector-`0x4000` segment-list span objects under the
  same bucket root, rectangle/rule objects under `+0x24`, fixed-list objects
  under `+0x28`, context slots `+0x2c..+0x68`, and publication state through
  `0xff1e`.
- Render-visible boundaries are the same shared page pipeline as live host
  bytes: `0x1ed84` copies the published record, `0x1edc6` bridges bucket,
  rule, fixed-list, and context roots, `0x1ef6a` runs bucket/rule/fixed-list
  dispatch, and helpers such as `0x1effe`, `0x1f88e`, `0x1f596`, `0x1f4e0`,
  `0x1f756`, and `0x1f812` derive rows from those objects.

Remaining overlay work is therefore not "does overlay replay work"; it must
change at least one concrete boundary above: replay-frame fields, skip-gate
state, parser/delayed-payload dispatch, page-object fields, bridge roots,
continuation fields, or ROM-derived rows.

## Reproduction Contract

A byte-stream renderer must preserve:

- `ESC &f#Y` absolute id storage and `ESC &f#X` selector meanings `0..10`;
- the 32-entry macro record pool, including head-presence lookup semantics;
- raw record counts that include four header bytes per 0x100-byte chunk;
- 252 payload bytes per macro chunk after the longword next pointer;
- lowercase `ESC &f0x` auto-prefix seeding and stop-time empty-prefix cleanup;
- uppercase `ESC &f0X` zero-byte seeding at both `0xddf2..0xddf4` and the
  parser-loop post-handler branch `0x11a68..0x11a82`;
- alternate/data parser behavior that appends payload controls but still lets
  `ESC &f1X` stop definition;
- execute/call frame fields `+0x00/+0x04/+0x08/+0x09/+0x0a`;
- `0xa904` replay priority and `0xe22c` frame-end unwinding;
- call-only macro context push/pop and font-context refresh through `0xe65c`;
- overlay selector state and the `0xff1e -> 0xe0a4 -> 0xe4f4 -> 0x11774`
  replay detour;
- skip gates for disabled overlay, missing overlay record, and page-root retry
  flag;
- page-record publication and ROM-derived render output after replayed macro
  bytes.

## Confidence

High for parser reachability, selector meanings, record layout, chunk count
math, `0xe0a4` lookup/free/full behavior, execute/call and non-replay frame
field offsets, `0xa904` replay, `0xe22c` frame ending, heap unit allocation,
`0xe65c` font-context bridge, overlay detour, skip gates, and page-record
output because the claims are backed by disassembly ranges
`0xdd08..0xdfb8`, `0xdfba..0xe110`, `0xe002..0xe0a2`,
`0xe418..0xe4f2`, `0xe4f4..0xe5e0`, `0xe22c..0xe408`, `0xe65c..0xe85e`,
parser-table evidence, and the named byte-stream examples.

High for the covered overlay payload matrix because each documented stream
starts from a stored macro payload, re-enters parser handlers, preserves the
page-record bridge, and reaches the ROM helpers that derive rows from the
published objects. There is no external row oracle in this evidence standard.

Medium for external/manual names for macro context and overlay state fields.
High for the ROM-local over-deep macro context boundary: the reset, push, and
pop instructions identify the eight-slot storage range, ninth-push address,
and empty-pop address. Low for physical/user-visible failure symptoms after
adjacent RAM is corrupted, because that is outside the ROM-local replay
contract.

## Remaining Edges

- No ROM middle edge remains for macro execute/call replay, macro
  font-context refresh, first overlay publication, repeated enabled-overlay
  publication, mixed-control overlay payloads, cursor-position overlay
  payloads, vertical-decipoint overlay payloads, chained-margin overlay
  payloads, transparent-data overlay payloads, raster overlay payloads,
  multi-row raster overlay payloads, span-flush overlay payloads, or the
  disabled/missing-record/retry-flag overlay skip gates.
- Remaining macro work must change a concrete overlay boundary from the map
  above: replay-frame fields, skip-gate state, parser/delayed-payload
  dispatch, page-object fields, bridge roots, continuation fields, or
  ROM-derived row construction. External/manual naming remains separate.
- Over-deep call/overlay nesting is not an anonymous macro middle edge: it is
  bounded at the unchecked context pointer addresses above. Future work should
  revisit it only if a byte stream demonstrates a specific adjacent-field
  mutation that changes replay bytes, selected font context, page objects, or
  rendered rows.
