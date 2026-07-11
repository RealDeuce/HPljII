# Active Render Scheduler

This note documents the ROM-visible scheduler handoff from a published
page/control record to active render work and band rendering. It is the
checkpoint after page-record producers and `0xff1e` publication, and before
the bitmap object dispatchers consume render records.

Status: composed for the software-visible scheduler state, active source
selection, two-work-record alternation, per-band render loop, wait-object
handoff, and ROM-derived row-construction checks. Physical formatter/DC timing
remains a separate board-facing boundary.

## Evidence

- `generated/disasm/ic30_ic13_active_render_scheduler_01eb2a.lst`
- `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`
- `generated/disasm/ic30_ic13_bitmap_state_setup_01ee9e.lst`
- `generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`
- `generated/disasm/ic30_ic13_page_pool_init_003100.lst`
- `generated/disasm/ic30_ic13_page_pool_candidate_select_007ec6.lst`
- `generated/disasm/ic30_ic13_page_pool_cursor_007612.lst`
- `generated/disasm/ic30_ic13_active_pool_cycle_001958.lst`
- `generated/disasm/ic30_ic13_page_pool_candidate_insert_001c04.lst`
- `generated/disasm/ic30_ic13_active_pool_engine_gate_002038.lst`
- `generated/disasm/ic30_ic13_engine_copy_pass_0022f4.lst`
- `generated/disasm/ic30_ic13_engine_copy_pattern_00247c.lst`
- `generated/disasm/ic30_ic13_timer_status_trampoline_000d52.lst`
- `generated/disasm/ic30_ic13_scan_status_interrupt_000f84.lst`
- `generated/disasm/ic30_ic13_scheduler_trap_handlers_00110c.lst`
- `generated/disasm/ic30_ic13_startup_render_work_init_02feb6.lst`
- `generated/analysis/ic30_ic13_long_reference_scan.md`
- `generated/analysis/ic30_ic13_page_record_bridge.md`
- `generated/analysis/ic30_ic13_render_path_references.md`
- `notes/page-raster-imaging.md` section
  `Active Render Scheduler Semantic Checkpoint`
- `notes/semantic-state-model.md` section
  `Published Record To Active Render Scheduler`
- `notes/dc-controller-engine.md`

Primary fixtures:

- `0x1eb2a/0x1ecd6 selects published record for render entry`
- `0x1ecd6 same-geometry render work reuse reaches render entry`
- `0x3144/0x7ec6/0x7712 page pool aliases feed scheduler cursor`
- `0x1958/0x1c04/0x1eea staged candidate reaches render scheduler`
- `0x2126/0x1a4c/0x2038 active pool copy window feeds engine rows`
- `0x0fa2/0x1db0/0x1e44 status feedback drives copy and done flag`
- `0x1036/0x108e/0x123a wait-object scheduler handoff`
- `0x1144..0x11f8 scheduler trap handlers update wait objects`
- `0x1cf8/0x1e80/0x1ea8 wrapper dispatch selects engine variants`
- `0x1eba4/0x1ef6a active render loop advances or yields bands`
- `0x1eba4 scheduler band words render published downloaded glyph`

## Owner Summary

Concept: this note owns the scheduler handoff after `0xff1e` has published a
page/control record and before bitmap object helpers interpret render roots.
It selects the published source record, chooses one of two render work records,
copies source page roots into render-record roots through
`0x1ed84 -> 0x1edc6`, advances the band word, and calls `0x1ef6a` only on the
capacity-approved render branch.

Primary route:

- Publication owner `0xff1e` leaves a published page/control pool chain at
  `0x780ea6`.
- Candidate selection `0x7ec6..0x7f90` and cursor advance
  `0x7722..0x779a` promote a source into scheduler cursor `0x780eaa`.
- Scheduler entry `0x1eb32..0x1eb50` copies the selected source to active
  source pointer `0x780eae`.
- Work-record selector `0x1ecd6..0x1ed76` chooses `0x7820c4` or `0x782128`,
  writes active render pointer `0x783a18`, and calls `0x1ed84`.
- Bridge `0x1ed84 -> 0x1edc6` copies source bucket/rule/fixed/context roots to
  render roots.
- Active loop `0x1eba4..0x1ecd2` presents render work `+0x10` as the current
  band word and calls `0x1ef6a` only when the render branch is eligible.

Field groups:

- Canonical scheduler state: protected pool head `0x780ea6`, scheduler cursor
  `0x780eaa`, active source `0x780eae`, release/advance cursor `0x780eb2`,
  render-work selector bytes `0x7820bc` / `0x7820c0`, paired work records
  `0x7820c4` / `0x782128`, active render pointer `0x783a18`, active band word
  render `+0x10`, and throttle/progress word render `+0x0e`.
- Canonical render-record state after bridge: render bucket root `+0x18`, rule
  root `+0x1c`, fixed-list root `+0x20`, and context slots `+0x24..+0x60`.
- Derived/cache state: band setup outputs `0x783a20`, `0x783a22`,
  `0x783a28`, destination stride `0x783a1c`, candidate-slot array
  `0x780e6e[]`, and status/engine latches such as `0x78399e`,
  `0x78399f`, `0x78398c`, `0x783990`, `0x7839ac`, row-copy accumulator
  `0x7839d4`, pattern-pointer cache `0x7839d8..0x7839f7`, `0x7828f9`,
  `0x780e32`, `0x780e36`, `0x780e6d`, and `0x780e67`.
- Firmware bookkeeping: active flags `0x780ea4` / `0x780ea5`, active-pool
  copy-window ready flag `0x7839d2`, timer/status divider bytes
  `0x78017f..0x780181`, and wait-object records selected by `0x123a`.
- Parser scratch: none. Parser and command-family state has already become
  page-record storage before this owner runs.
- Hardware/external state: formatter/DC signal names and physical timing for
  MMIO-backed readiness, copy, and wait predicates.
- Unknown: no ROM-local field-meaning unknown remains for the active-pool
  row-copy accumulator. Direct call sites for the optional
  `0x247c..0x2746` pattern helper bodies are not located in the current xrefs:
  `generated/analysis/ic30_ic13_long_reference_scan.md` lists accumulator
  `0x7839d4` references at `0x001bf8`, `0x0026c6`, and `0x0026ea`, but no
  absolute long target for `0x0000247c`; the adjacent copy-pass listing
  returns at `0x2330` and the coordinate helper returns at `0x247a` before the
  separate `0x247c` body. The helper is therefore documented as a bounded side
  path, not as an ordinary active-render row source.

Writers and readers:

- `0x3144..0x3162` initializes page/control pool cursors.
- `0x7ec6..0x7f90`, `0x7722..0x779a`, and `0x1eb32..0x1eb50` select and copy
  the published source record into scheduler state.
- `0x2feb6` initializes paired render-work selector state.
- `0x1ecd6..0x1ed76` writes active render pointer `0x783a18` and calls
  `0x1ed84`.
- `0x1ed84` / `0x1edc6` read source roots and write render roots.
- `0x1eba4..0x1ecd2` reads active flags, capacity predicates, and band word,
  then either calls `0x1ef6a`, waits, throttles, or cleans up.
- `0x1ef6a`, `0x1efc2`, `0x1f446`, and `0x1f756` are downstream renderer
  consumers; object interpretation and row writes are owned by
  [page-raster-imaging.md](page-raster-imaging.md).

Output effect:

- The scheduler does not create page objects and does not choose compact,
  segment-list, encoded-raster, rule, or fixed-list helper variants.
- Its output is the active render context: which published record is selected,
  which work record receives copied roots, which render roots are visible, and
  which band word reaches `0x1ef6a`.
- Hardware and wait-object paths can pace, stall, or wake scheduler execution,
  but they do not change the page-object model unless they mutate one of the
  ROM-visible scheduler or render-record fields above.

Evidence:

- `generated/disasm/ic30_ic13_active_render_scheduler_01eb2a.lst` anchors
  source selection, work-record choice, active-loop predicates, and band
  advancement.
- `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst` anchors
  the bridge fields written by `0x1ed84` / `0x1edc6`.
- `generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst` anchors the first
  renderer consumers after scheduler handoff.
- The fixtures listed above exercise selected-record handoff, same-geometry
  reuse, candidate promotion, wait-object scheduling, active-loop branch
  outcomes, and scheduler-produced band words reaching a published downloaded
  glyph.

## Field Groups

Canonical page/control pool state:

- `0x780ea6`: protected published pool-head pointer written by `0xff1e` and
  initialized by `0x3144..0x3162`.
- `0x780eaa`: scheduler cursor for the selected page/control record.
- `0x780eae`: active source record consumed by `0x1ed84`.
- `0x780eb2`: release/advance cursor paired with `0x780eaa`.
- `0x780e04`: engine/status counter copied into active-pool records and used
  by status/copy pacing helpers.

Canonical render-work state:

- `0x7820bc` and `0x7820c0`: two-work-record selector state initialized by
  `0x2feb6` and toggled by `0x1ecd6`.
- `0x7820c4` and `0x782128`: paired render work records.
- `0x7820c8` and `0x78212c`: work-record header words cleared by `0x2feb6`.
- `0x783a18`: active render work-record pointer consumed by `0x1ef6a`.
- Render work `+0x10`: active band word advanced by `0x1eba4` and used by
  `0x1ef6a`.
- Render work `+0x0e`: throttle/progress word incremented by the active loop.

Derived/cache state:

- `0x783a20`, `0x783a22`, and `0x783a28`: render-band rows, remainder, and
  destination base derived by `0x1ef86`.
- `0x783a1c`: destination stride used by bitmap writers after render setup.
- `0x780e6e[]`: candidate-slot array populated before selection by
  `0x7ec6..0x7f90`.
- `0x78399e`, `0x78399f`, `0x78398c`, `0x783990`, `0x7839ac`,
  `0x7828f9`, `0x780e32`, `0x780e36`, `0x780e6d`, and `0x780e67`:
  status, pending-byte, and engine-shadow latches consumed by the scheduler
  and status wrappers.
- `0x7839d4`: row-copy longword accumulator for the optional pattern helper.
  Setup `0x1a4c..0x1c00` clears it, `0x26c4` adds the row-copy body sum
  accumulated by the `0x24c4..0x26c2` copy table, and `0x26de..0x270a`
  rotates its nibbles into eight pattern pointers under `0x7839d8..0x7839f7`.
- `0x7839d8..0x7839f7`: eight pattern-table pointers built from accumulator
  nibbles by `0x26de..0x270a`; `0x270c..0x2746` writes seven words per
  pattern column into the destination row base `0x78399a`.

Optional pattern helper body:

- Entry `0x247c` seeds copy-table pointer `A0 = 0x24c4 + 2 * 0x7839a4`,
  source pointer `A1 = 0x783992`, destination row base `A2 = 0x78399a`, and
  row stride `D7 = 0x7839a8`.
- `0x247c..0x24be` calls local thunk `0x24c0` eight times. Between calls it
  advances `A2` by stride `0x7839a8`, so the helper targets eight destination
  rows from the same source stream.
- `0x24c0` clears `D0` and jumps through `A0` into the unrolled table
  `0x24c4..0x26c2`. Each selected table pair copies one longword from
  `(A1)+` to `(A2)`, advances `A2`, and adds the written longword into `D0`.
  The `0x7839a4` offset therefore selects how many leading table pairs are
  skipped, matching the active-copy width contract used by ordinary helper
  `0x22f4`.
- `0x26c4` adds the row-copy sum in `D0` into accumulator `0x7839d4`.
  `0x26ca..0x26dc` consumes `0x7839ac` source-tail longwords and returns.
- `0x26de..0x270a` rotates accumulator `0x7839d4` by four bits eight times,
  masks the low nibble, multiplies it by `0x0e`, and stores eight pattern
  table pointers from base `0x2748` into `0x7839d8..0x7839f7`.
- `0x270c..0x2746` walks those eight pointers. For each pointer it writes
  seven words into destination memory starting at `0x78399a`, advancing the
  row address by `0x200` between words and advancing the column destination by
  two bytes between pointers.
- No current xref proves ROM control flow into `0x247c`, `0x26de`, or
  `0x270c`. These bodies are decoded for a future caller proof, but they are
  not part of the ordinary published-page render route unless that entry edge
  is found.

Firmware bookkeeping:

- `0x780ea4` / `0x780ea5`: active render/scheduler flags written around
  `0x1eb32..0x1eb50`.
- `0x7839d2`: immediate ready flag consumed by `0x21b8` before
  candidate staging.
- `0x78017f`, `0x780180`, and `0x780181`: periodic status/timer divider
  bytes for the `$8000`, `$a200`, and `$a400` phases.
- Wait-object records signaled by `0x1036` and selected by `0x123a`: next
  pointer `+0`, priority `+8`, scheduler state `+0a`, wait argument `+0c`,
  restart payload `+0x12`, private stack base `+0x16`, and saved stack
  pointer `+0x1a`.

Parser scratch:

- None. Parser and page-record producers have already built and published the
  source page/control record before this scheduler checkpoint starts.

Unknown:

- Physical mapping from formatter/DC connector signals to ROM MMIO bits and
  latches.
- Physical engine timing that decides when modeled ready/busy and wait-object
  predicates become true.
- Direct caller into the optional `0x247c..0x2746` accumulator-to-pattern
  helper is not located. The field writes and consumers are documented from
  disassembly; ordinary active rendering still uses `0x22f4` and `0x1ef6a`.
  Evidence for the caller boundary is the absence of a `0x0000247c` target in
  `generated/analysis/ic30_ic13_long_reference_scan.md`, plus the local
  returns at `0x2330` and `0x247a` in
  `generated/disasm/ic30_ic13_engine_copy_pass_0022f4.lst`. A wider decoded
  disassembly search for `247c`, `26de`, and `270c` finds only the helper body
  itself, existing documentation, and unrelated opcode/data hits; it does not
  expose a branch, jump, trap/vector entry, or computed-target table into the
  helper.

## Band Render Model

The ROM does not build one full-page bitmap before imaging. After publication,
the scheduler selects a source page/control record and renders it in successive
band calls:

- `0xff1e` publishes the page/control record and leaves the page roots in pool
  state under protected head `0x780ea6`.
- `0x7ec6..0x7f90` and `0x7722..0x779a` promote a selectable pool record into
  scheduler cursor `0x780eaa`; `0x1eb32..0x1eb50` copies it to active source
  `0x780eae`.
- `0x1ecd6..0x1ed76` selects one of the two render work records, writes active
  render pointer `0x783a18`, initializes or reuses geometry, and calls
  `0x1ed84`.
- `0x1ed84 -> 0x1edc6` copies the source bucket/rule/fixed/context roots into
  the active render record.
- Active loop `0x1eba4..0x1ecd2` uses render work word `+0x10` as the current
  band word. When capacity is sufficient, it calls `0x1ef6a`, then increments
  `+0x10` and throttle word `+0x0e`.
- `0x1ef86` derives per-band caches `0x783a20`, `0x783a22`, `0x783a28`, and
  stride/offset state before object dispatch. These are derived render caches,
  not page-record fields.
- `0x1ef6a` renders that band in fixed order: bucket-chain dispatch
  `0x1efc2`, rule-list dispatch `0x1f446`, then fixed-list dispatch
  `0x1f756`.

Continuation is explicit ROM state. Rule objects carry remaining rows in
bridged field `+0x0c`; fixed-list objects carry remaining rows in `+0x0a`;
compact glyph and encoded raster helpers may split rows between the current
band and fallback buffer `0x7810b4 + byte_pair_offset`. The next scheduler
band call resumes from those mutated object or fallback states. Physical
formatter/DC timing can wake, stall, or pace this loop, but it does not create
a different page-object model unless it changes the ROM-visible scheduler
fields above.

## Active Copy And Bridge

`0x1ed84..0x1ee96` is the exact software boundary where the active published
record becomes render-record state. The source is always the active source
pointer `0x780eae`; the destination is the render work record passed by
`0x1ecd6` and later selected through `0x783a18`.

Active-copy entry `0x1ed84`:

- `0x1ed8c..0x1ed96` loads destination work record `A5` from the call
  argument and source page/control record `A4` from `0x780eae`.
- `0x1ed96..0x1edae` copies source header words `+0x18/+0x1a` into render
  work words `+0x0a/+0x0c`, seeds current band word `+0x10` from source
  `+0x18`, mirrors that start into `+0x16`, and clears throttle word `+0x0e`.
- `0x1edb2..0x1edbc` calls bridge helper `0x1edc6(source, destination)`.

Bridge helper `0x1edc6`:

- `0x1edce..0x1ede0` returns immediately if the source pointer is zero.
- `0x1ede2..0x1edee` copies source bucket root `+0x1c` to render `+0x18`,
  source rule-list root `+0x24` to render `+0x1c`, and source fixed-list root
  `+0x28` to render `+0x20`.
- `0x1edf4..0x1ee0e` walks the copied rule list at render `+0x1c`. Each rule
  node has selector byte `+0x05` ORed with `0x10`, and height word `+0x0a`
  copied to continuation word `+0x0c`.
- `0x1ee10..0x1ee5e` walks the copied fixed-list at render `+0x20`. Each
  fixed node has byte `+0x05` ORed with `0x10`, word `+0x08` copied to
  continuation word `+0x0a`, byte `+0x0c` set to `1`, and byte `+0x0d` set
  to `8`.
- `0x1ee60..0x1ee96` copies 16 context/resource slots from source
  `+0x2c..+0x68` to render `+0x24..+0x60`.

These writes are canonical render-record state, not parser scratch. They are
the fields consumed by `0x1ef6a`: bucket root `+0x18` by `0x1efc2`, rule root
`+0x1c` by `0x1f446`, fixed-list root `+0x20` by `0x1f756`, and context slots
`+0x24..+0x60` by compact-glyph and segment renderers.

## Scheduler To Renderer Ownership

This checkpoint joins the scheduler state above to the page-object and bitmap
dispatch documentation. The scheduler owns selection, work-record choice, and
band pacing. The renderer owns object interpretation and pixel writes after
the active record has reached `0x1ef6a`.

The pixel-affecting handoff is:

- Published source selection: `0xff1e` leaves the published pool head in
  `0x780ea6`; `0x7ec6..0x7f90` and `0x7722..0x779a` move a selected pool
  record into `0x780eaa`; `0x1eb32..0x1eb50` copies it to active source
  `0x780eae`.
- Work-record selection: `0x1ecd6..0x1ed76` selects `0x7820c4` or
  `0x782128`, writes the chosen pointer to `0x783a18`, and calls `0x1ed84`.
- Root bridge: `0x1ed84` copies source header words into the selected work
  record, and `0x1edc6` copies source root `+0x1c` to render `+0x18`,
  source root `+0x24` to render `+0x1c`, source root `+0x28` to render
  `+0x20`, and source context slots `+0x2c..+0x68` to render
  `+0x24..+0x60`.
- Band dispatch: `0x1eba4..0x1ecd2` uses render work `+0x10` as the active
  band word. Only the capacity-satisfied branch calls `0x1ef6a`; wait,
  cleanup, stale-work, and throttle exits do not interpret page objects.
- Renderer input: `0x1ef6a` derives current-band caches through `0x1ef86`,
  then dispatches render `+0x18` through `0x1efc2`, render `+0x1c` through
  `0x1f446`, and render `+0x20` through `0x1f756`.

Field ownership after this handoff:

- Canonical page/image state: source roots `+0x1c`, `+0x24`, `+0x28`, and
  `+0x2c..+0x68` before `0x1edc6`; render roots `+0x18`, `+0x1c`, `+0x20`,
  and `+0x24..+0x60` after `0x1edc6`.
- Canonical scheduler state: pool cursors `0x780ea6`, `0x780eaa`,
  `0x780eae`, and `0x780eb2`; render-work selector bytes `0x7820bc` and
  `0x7820c0`; active render pointer `0x783a18`; active band word
  render `+0x10`.
- Derived/cache render state: `0x783a20`, `0x783a22`, `0x783a28`,
  `0x783a1c`, and `0x7839f8..`, all written after the work record has been
  selected and before or during object dispatch.
- Firmware bookkeeping: throttle/progress word render `+0x0e`, active flags
  `0x780ea4` and `0x780ea5`, wait object `0x780182`, and the MMIO-facing
  status latches that can delay or wake the next band call. `0x780eb6` is an
  initialized-only pool alias: the long-reference scan finds only the
  `0x3164` initialization store, with no ROM-local reader.
- Parser scratch: none. Parser-family scratch has already been converted into
  page-record objects before `0xff1e` publication.

Output effect:

- The scheduler decides which published page/control record reaches the
  bitmap renderer, which of the two render work records receives the copied
  roots, and which band word is presented to `0x1ef6a`.
- The scheduler does not choose compact-glyph, segment-list, encoded-raster,
  rule, or fixed-list subrenderers. Those choices are made from object fields
  under render roots `+0x18`, `+0x1c`, and `+0x20`, as documented in
  [page-raster-imaging.md](page-raster-imaging.md) under
  `Bitmap Object Dispatch Semantic Checkpoint`.
- The storage-side producer of those roots is documented in
  [page-record-storage.md](page-record-storage.md) under
  `Mixed Page Composition Checkpoint`: compact text/downloaded glyphs,
  portrait spans, and encoded raster rows use source root `+0x1c`;
  rectangle/rule objects use source root `+0x24`; fixed-width and landscape
  span objects use source root `+0x28`.

Evidence:

- `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst` for source-root
  publication.
- `generated/disasm/ic30_ic13_active_render_scheduler_01eb2a.lst` for
  `0x780eaa -> 0x780eae`, render-work selection, active-loop branch
  predicates, and band advancement.
- `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst` for
  the bridge fields copied by `0x1ed84` and `0x1edc6`.
- `generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst` for the first
  renderer consumers after scheduler handoff.
- Fixtures `0x1eb2a/0x1ecd6 selects published record for render entry`,
  `0x1eba4/0x1ef6a active render loop advances or yields bands`, and
  `0x1ef6a render entry composes bucket, rule, and fixed-width lists in call
  order` for the selected-record, band-loop, and renderer-call-order
  branches.

Unresolved middle edges:

- No ROM-local middle edge remains between `0xff1e` publication and
  `0x1ef6a` object dispatch for the documented roots, work-record selection,
  or scheduler-produced band word.
- Remaining scheduler uncertainty is hardware/external: the MMIO and
  wait-object events that pace when the next documented band call occurs.
  Those events can change time and readiness, but they do not define another
  page-object class unless they mutate one of the ROM-visible fields listed
  above.

## Scheduler Outcome Matrix

This matrix composes the branch ledger above into the states a reproducer must
carry between page publication and bitmap dispatch. Each outcome is grounded in
`generated/disasm/ic30_ic13_active_render_scheduler_01eb2a.lst` unless a bridge
or renderer file is named.

- Published-source promotion:
  `0xff1e`, `0x7ec6..0x7f90`, `0x7722..0x779a`, and `0x1eb32..0x1eb50`
  move a published page/control record from protected pool head `0x780ea6` to
  scheduler cursor `0x780eaa`, then active source `0x780eae`. Canonical state
  is the selected source record and pool cursors; derived state is the
  candidate-slot choice under `0x780e6e[]`; firmware bookkeeping is the
  protected-pool lock and release cursor `0x780eb2`. No page objects are
  interpreted and no pixels are produced in this outcome. Evidence is
  `0x3144/0x7ec6/0x7712 page pool aliases feed scheduler cursor` and
  `0x1eb2a/0x1ecd6 selects published record for render entry`.
- Candidate-slot selection details:
  `0x7ec6..0x7f90` derives the slot count from
  `(0x7821fb & 0x7e) >> 1`, caps it at `6`, and walks longword slots
  `0x780e6e[]`. Empty slots and slots equal to the prior survivor are cleared.
  A nonempty candidate whose state byte `+0x04` is `4`, or whose word `+0x0e`
  is nonzero, is promoted by writing byte `+0x04 = 2`, incrementing word
  `+0x0e`, and copying the record pointer to both release cursor `0x780eb2`
  and scheduler cursor `0x780eaa`. A no-candidate or invalid-candidate path
  reports through `0x6f32(0x5d)`, sets status masks on `0x780e32` and
  `0x780e2e`, and leaves no page-object/render side effect.
- Release-cursor advance details:
  `0x7722..0x779a` only advances release state when scheduler cursor
  `0x780eaa` still equals release cursor `0x780eb2`. If the release record's
  state byte is `2`, the helper marks it `4`, clears word `+0x0e`, copies
  engine/status counter `0x780e04` into longword `+0x10`, and advances
  `0x780eb2` to the next pool record. If cursor and release diverge, or the
  selected cursor still equals protected head `0x780ea6` in a non-state-`2`
  case, the helper leaves the cursors unchanged.
- Active candidate staging:
  `0x1c04..0x1c98` starts from release cursor `0x780eb2`. If ready predicate
  `0x21b8` fails, it waits on object `0x7801c2` through `0x10c8` and returns
  `D7 = 0`. If ready, it marks the release record state byte `+0x04 = 3`,
  raises latch `0x780e6d` when record word `+0x14` is nonzero, runs the
  active-pool copy/status helpers, and returns `D7 = 1`. This is scheduler
  bookkeeping that can make a published record eligible for later render
  selection; it does not interpret object classes or write pixels.
- New-geometry work selection:
  `0x1ecde..0x1ed34` toggles selector `0x7820bc`, chooses `0x7820c4` or
  `0x782128`, writes active render pointer `0x783a18`, copies source byte
  `active_source+9` into work word `+0x04`, and branches to geometry setup
  `0x1ee9e` when previous work `+0x04` differs. Canonical state is the chosen
  work record plus `0x783a18`; derived/cache state is the geometry written by
  `0x1ee9e`; parser scratch is absent. The output effect is a render work
  record ready for the `0x1ed84` bridge, not pixel output. Evidence is
  `0x1eb2a/0x1ecd6 selects published record for render entry` and
  `generated/disasm/ic30_ic13_bitmap_state_setup_01ee9e.lst`.
- Same-geometry work reuse:
  `0x1ed36..0x1ed6a` reuses previous geometry when work words `+0x04` match.
  It computes new work `+0x08` through `0x33238(previous+0x06,
  previous+0x10 - previous+0x0a + previous+0x08)`, copies previous longword
  `+0x00`, and copies previous word `+0x06`. Canonical state remains the
  selected work record and active source; derived/cache state is the reused
  destination/offset. The output effect is the same bridge input as the
  new-geometry branch. Evidence is
  `0x1ecd6 same-geometry render work reuse reaches render entry`.
- Root and context bridge:
  `0x1ed74..0x1ed76` calls `0x1ed84(new_work)`, then
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`
  documents `0x1ed84 -> 0x1edc6`. Canonical render state written here is
  render roots `+0x18`, `+0x1c`, `+0x20`, context slots `+0x24..+0x60`,
  header words `+0x0a/+0x0c`, active band word `+0x10`, start word `+0x16`,
  and cleared throttle word `+0x0e`. Readers are `0x1ef6a`, `0x1efc2`,
  `0x1f446`, `0x1f756`, and the compact/segment renderers documented in
  [page-raster-imaging.md](page-raster-imaging.md). This bridge creates the
  renderer-visible object roots, but it still does not interpret object
  classes or write pixels.
- Cleanup flag outcome:
  `0x1eba4..0x1ebd2` handles `0x780ea5 == 1`. It calls `0x1ef38`, clears
  active flag `0x780ea4`, signals wait object `0x780182` through `0x10c8`,
  and calls `0x10c4`. Firmware bookkeeping changes; canonical page/render
  roots are unchanged; `0x1ef6a` is not called. Evidence is
  `0x1eba4/0x1ef6a active render loop advances or yields bands`.
- Stale-work cleanup:
  `0x1ebd8..0x1ec06` compares active work word `+0x0c` with active band word
  `+0x10`. If the work is stale, it clears `0x780ea4` and signals
  `0x780182` through the same cleanup path. The output effect is no pixel
  output for that iteration, and no render root is consumed.
- Throttle yield:
  `0x1ec0c..0x1ec30` clears throttle word `+0x0e`, signals `0x780182`, and
  yields through `0x10d8(2)` when `+0x0e > 0x28`. This is firmware
  scheduling state only. It does not call `0x1ef6a` and does not change the
  page-object graph.
- Capacity-approved render:
  `0x1ec34..0x1ec8e` computes available capacity from active work `+0x06`,
  active remaining rows `(+0x10 - +0x16)`, and paired remaining rows when
  `0x7820bc != 0x7820c0`. `0x1ec8e..0x1ecac` releases the scheduler lock
  through `0x15ac`, calls `0x1ef6a`, increments active band word `+0x10`,
  and increments throttle word `+0x0e` when capacity is at least `9`. This is
  the only scheduler outcome in this matrix that produces renderer input for
  pixels. Renderer interpretation after the call is owned by
  [page-raster-imaging.md](page-raster-imaging.md) and anchored by
  `generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`.
- Capacity wait:
  `0x1ecb0..0x1ecd2` clears `+0x0e`, releases the lock, signals wait object
  `0x780182`, and waits through `0x10d0(2)` when computed capacity is less
  than `9`. Canonical roots and the active band word are preserved for a later
  iteration; no object dispatcher runs.

State classification for these outcomes:

- Canonical state:
  pool cursors `0x780ea6/0x780eaa/0x780eae/0x780eb2`, selector bytes
  `0x7820bc/0x7820c0`, work records `0x7820c4/0x782128`, active render
  pointer `0x783a18`, render roots `+0x18/+0x1c/+0x20`, context slots
  `+0x24..+0x60`, active band word `+0x10`, and start word `+0x16`.
- Derived/cache state:
  candidate slots `0x780e6e[]`, geometry setup outputs, reused destination
  word `+0x08`, band caches produced after `0x1ef6a` enters `0x1ef86`, and
  destination stride/base fields such as `0x783a1c`, `0x783a20`,
  `0x783a22`, and `0x783a28`.
- Parser scratch:
  none in this matrix. Host bytes, escape parameters, and payload state have
  already been converted into page records before `0xff1e`.
- Firmware bookkeeping:
  active flags `0x780ea4/0x780ea5`, throttle word `+0x0e`, protected-lock
  calls, wait object `0x780182`, and wait/yield calls `0x10c4`, `0x10d0`,
  and `0x10d8`.
- Hardware/external state:
  only the MMIO and physical engine events that decide when wait objects wake
  or capacity changes. The ROM-visible branches above define what happens once
  those predicates are observed.
- Unknown:
  no ROM-local software edge remains from published record selection through a
  capacity-approved `0x1ef6a` call. Unknowns are limited to the hardware timing
  boundary and any renderer-local invalid helper/source boundaries listed in
  [unresolved-boundaries.md](unresolved-boundaries.md).

## Writers

- `0xff1e` publishes state byte `+4 = 2`, writes source root longword to
  `0x780ea6`, sets publication flag `0x782996`, and clears the current root.
- `0x3144..0x3162` initializes `0x780ea6`, `0x780eaa`, `0x780eae`,
  `0x780eb2`, and `0x780eb6` to pool base `0x780f02`; no later firmware
  reference to `0x780eb6` is present in
  `generated/analysis/ic30_ic13_long_reference_scan.md`.
- `0x2feb6` initializes render work selector state by writing
  `0x7820bc = 1` and `0x7820c0 = 1`, then clearing `0x7820c8` and
  `0x78212c`.
- `0x1c04..0x2016` stages a current pool record, writes deadline/status
  fields, inserts it into `0x780e6e[]`, and releases it through `0x1eea`.
- `0x7ec6..0x7f90` promotes a selectable candidate into scheduler cursors
  `0x780eaa` and `0x780eb2`.
- `0x7722..0x779a` advances or releases scheduler cursors while protecting
  pool head `0x780ea6`.
- `0x1eb32..0x1eb50` copies `0x780eaa` into active source `0x780eae`.
- `0x1ecd6..0x1ed76` alternates render work records, writes `0x783a18`,
  initializes geometry when needed, or reuses same-geometry fields before
  calling `0x1ed84`.
- `0x1ed84` writes render-record header words from the active source and
  delegates queue/list/context copying to `0x1edc6`.
- `0x1eba4..0x1ecd2` advances active render bands, calls `0x1ef6a` when
  capacity is sufficient, yields or throttles when it is not, and cleans up
  when active work is done.
- `0x0d52..0x0f7a`, `0x0f84..0x10f2`, `0x1036..0x1282`, and
  `0x1144..0x11f8` update timer/status latches and wait-object scheduler
  state that can wake, stall, or dispatch work.

## Readers And Consumers

- `0x1ed84` consumes active source `0x780eae`, source header words, and source
  bucket/list/context roots.
- `0x1edc6` consumes source page-record queue roots and writes render-record
  bucket, rule, fixed-list, and context roots.
- `0x1ef86` consumes render work geometry and derives `0x783a20`,
  `0x783a22`, and `0x783a28`.
- `0x1ef6a` consumes active render work pointer `0x783a18`, dispatches bucket
  objects through `0x1efc2`, rule objects through `0x1f446`, and fixed-list
  objects through `0x1f756`.
- `0x1cf8..0x1ea8` consume `0x780e04`, `0x78399e`, `0xa680` readiness,
  attention flags, and active work fields to choose copy/status/wait variants.
- `0x1036`, `0x1064`, `0x108e`, `0x123a`, and trap handlers consume
  wait-object state to wake, block, yield, or dispatch scheduler objects.

## Output Effect

The scheduler does not create page objects. Its output effect is deciding
which published source record becomes active, which render work record receives
the copied page roots, and which band words reach `0x1ef6a`.

Published-source route: source record `0x00d0eaa0` can be copied to active
source `0x780eae`, assigned render work record `0x782128` through active
render pointer `0x783a18`, and then reach the same ROM-local render-entry path
as a direct `0x1ed84` / `0x1ef6a` setup.

Same-geometry route: the sibling branch reuses prior geometry, computes
destination word `+8` through `0x33238`, and still reaches the documented
render-entry path.

### Work-Record Selector Branches

`0x1ecd6..0x1ed76` is the bridge-side scheduler gate between the selected
published source and the active render record. It does not inspect page-object
classes; it chooses the render-work record and decides whether geometry can be
reused before `0x1ed84` copies page roots.

Branch effects:

- `0x1ecde..0x1ed0e`: toggle render-work selector `0x7820bc`. If the selector
  was zero, previous work is `0x7820c4`, new active work is `0x782128`, and
  `0x7820bc` becomes `1`. If the selector was nonzero, previous work is
  `0x782128`, new active work is `0x7820c4`, and `0x7820bc` is cleared.
- `0x1ed0e..0x1ed24`: write active render pointer `0x783a18 = new_work`, then
  copy source byte `active_source+9` from `0x780eae` into new work word
  `+0x04`. This source byte is the geometry/class comparison key for the next
  branch.
- `0x1ed26..0x1ed34`: compare previous work `+0x04` with new work `+0x04`.
  A mismatch calls geometry setup `0x1ee9e(new_work)` at `0x1ed6c..0x1ed74`.
- `0x1ed36..0x1ed6a`: same-geometry reuse branch. It computes a new
  destination/offset word through `0x33238(previous+0x06,
  previous+0x10 - previous+0x0a + previous+0x08)`, stores the result in new
  work `+0x08`, copies previous longword `+0x00`, and copies previous word
  `+0x06`.
- `0x1ed74..0x1ed76`: both geometry branches call `0x1ed84(new_work)`.
  `0x1ed84` then copies the active source page/control roots into the selected
  render work record, so later `0x1ef6a` sees the same page-object graph with
  scheduler-selected band geometry.

Active-loop route: `0x1eba4..0x1ecd2` splits into render, capacity-wait,
cleanup, and throttle outcomes. In the render case, the branch calls
`0x1ef6a`, increments render work word `+0x10`, and increments throttle word
`+0x0e`.

Scheduler-produced band words `0..9` can feed a published downloaded-glyph
record through `0x1ef6a`: only buckets `1` and `9` dispatch compact objects,
and bucket `9` reaches the ROM-derived row-write path for page row `86`.

Supporting evidence names for these routes are `0x1eb2a/0x1ecd6 selects
published record for render entry`, `0x1ecd6 same-geometry render work reuse
reaches render entry`, `0x1eba4/0x1ef6a active render loop advances or yields
bands`, and `0x1eba4 scheduler band words render published downloaded glyph`.

### Active Loop Branches

The active render loop at `0x1eba4..0x1ecd2` is a software scheduler over the
selected render work record, not a bitmap dispatcher by itself. The selected
record is `0x782128` when `0x7820bc` is nonzero and `0x7820c4` when it is
zero; the paired record is selected the same way from `0x7820c0`.

Branch effects:

- If `0x780ea5 == 1`, the loop calls `0x1ef38`, clears active-render flag
  `0x780ea4`, and signals wait object `0x780182` through `0x10c8` /
  `0x10c4` before continuing.
- If active work word `+0x0c` is less than active band word `+0x10`, the loop
  takes the same cleanup/signal path. This is a stale/out-of-range work
  cleanup, not a render call.
- If throttle word `+0x0e > 0x28`, the loop clears `+0x0e`, signals
  `0x780182` through `0x10c8`, and yields through `0x10d8(2)`.
- Otherwise it computes available capacity as work `+0x06` minus the active
  remaining rows `(+0x10 - +0x16)`, and subtracts the paired record's
  remaining rows when `0x7820bc != 0x7820c0`.
- If that available count is at least `9`, the loop calls `0x1ef6a`, then
  increments active work `+0x10` and throttle word `+0x0e`.
- If available count is less than `9`, the loop clears `+0x0e`, signals
  `0x780182` through `0x10c8`, and waits through `0x10d0(2)`.

The disassembly-backed active-loop contract is:

- `0x1eb78..0x1eb9e` selects the active work record from selector
  `0x7820bc`: nonzero selects `0x782128`, zero selects `0x7820c4`. It selects
  the paired record from `0x7820c0` by the same rule.
- `0x1eba4..0x1ebd2` handles loop-flag cleanup. When byte `0x780ea5` is `1`,
  the loop calls `0x1ef38`, clears active-render flag `0x780ea4`, signals wait
  object `0x780182` through `0x10c8`, and immediately calls `0x10c4`.
- `0x1ebd8..0x1ec06` handles stale work. If active work word `+0x0c` is less
  than active band word `+0x10`, it clears `0x780ea4` and signals the same wait
  object through `0x10c8` / `0x10c4`, without rendering.
- `0x1ec0c..0x1ec30` handles throttle yield. If active word `+0x0e` is greater
  than `0x28`, it clears `+0x0e`, signals `0x780182`, yields through
  `0x10d8(2)`, and returns to the top of the loop.
- `0x1ec34..0x1ec8e` computes capacity as active work `+0x06` minus active
  remaining rows `(+0x10 - +0x16)`. When active and paired selectors differ,
  it also subtracts paired remaining rows `(+0x10 - +0x16)`. The resulting
  capacity is stored in the loop local at `A6-4`.
- `0x1ec8e..0x1ecac` is the render branch. Capacity `>= 9` releases the
  scheduler lock through `0x15ac`, calls `0x1ef6a`, increments active band word
  `+0x10`, increments throttle word `+0x0e`, and loops.
- `0x1ecb0..0x1ecd2` is the capacity-wait branch. Capacity `< 9` clears
  `+0x0e`, releases the scheduler lock, signals wait object `0x780182`, waits
  through `0x10d0(2)`, and loops without calling `0x1ef6a`.

Fixtures `0x1eba4/0x1ef6a active render loop advances or yields bands` and
`0x1eba4 scheduler band words render published downloaded glyph` check these
branches against concrete render-work records. They are not an external pixel
oracle: the row-write path remains tied to the buckets selected by `0x1ef6a`
and the render helpers documented in [page-raster-imaging.md](page-raster-imaging.md).

## Reproduction Contract

A pixel-accurate ROM-derived renderer must preserve:

- `0xff1e` publication state before scheduling;
- pool-head and scheduler-cursor distinction between `0x780ea6`,
  `0x780eaa`, `0x780eae`, and `0x780eb2`;
- candidate staging and cursor promotion through `0x1c04`, `0x1eea`,
  `0x7ec6`, and `0x7722`;
- render work selector initialization at `0x2feb6` and alternation through
  `0x1ecd6`;
- active render work pointer `0x783a18`;
- same-geometry reuse versus geometry-initialization behavior before
  `0x1ed84`;
- active-copy bridge through `0x1ed84` and `0x1edc6`;
- per-band active loop behavior at `0x1eba4..0x1ecd2`: cleanup and wait exits
  must not call `0x1ef6a`, throttle word `+0x0e > 0x28` yields through
  `0x10d8(2)`, and the render branch requires capacity `>= 9` after
  subtracting active and, when selectors differ, paired remaining rows;
- wait-object and trap state transitions that can wake or stall active work;
- derived band fields consumed by `0x1ef6a`.

Supported stream rendering rule:

- Treat render work word `+0x10` as the scheduler-produced band selector
  presented to `0x1ef6a`. The scheduler may reach that word through candidate
  promotion, same-geometry reuse, or new geometry setup, but object
  interpretation starts only after `0x783a18` points at the selected work
  record and `0x1ed84 -> 0x1edc6` has copied the source roots.
- A capacity-approved branch at `0x1ec8e..0x1ecac` is the only branch in
  `0x1eba4..0x1ecd2` that renders rows. It releases the scheduler lock, calls
  `0x1ef6a`, increments active band word `+0x10`, and increments throttle word
  `+0x0e`.
- Cleanup, stale-work, throttle-yield, and capacity-wait branches are
  no-pixel scheduler outcomes for the current iteration. They can signal wait
  object `0x780182`, clear or reset progress fields, or yield through
  `0x10c4`, `0x10d0`, or `0x10d8`, but they do not interpret bucket, rule, or
  fixed-list roots.
- Pixel derivation for a supported byte stream therefore follows the sequence
  of rendered band words that actually reach `0x1ef6a`. Within each call,
  [page-raster-imaging.md](page-raster-imaging.md) owns row construction from
  render roots `+0x18`, `+0x1c`, `+0x20`, copied context slots, current-band
  caches, and fallback-buffer state.
- Physical wait timing is outside this ROM-local rule unless it changes one of
  the ROM-visible fields named above. It can decide when the next scheduler
  iteration happens, but not what a documented `0x1ef6a` call does with a given
  render work record.
- The optional pattern helper bodies at `0x247c..0x2746` are not a supported
  byte-stream-to-pixel route until a ROM caller, computed target, trap/vector,
  or scheduler entry into them is found. If such an entry is proven, preserve
  the copy-table sum into `0x7839d4`, the pattern-pointer cache
  `0x7839d8..0x7839f7`, and the seven-row column writes from `0x270c..0x2746`;
  otherwise ordinary active rendering still follows `0x22f4` for engine row
  copies and `0x1ef6a` for page-object rendering.

## Confidence

High for pool-head versus scheduler-cursor distinction, candidate-slot
staging/release, `0x780eaa -> 0x780eae`, work-record alternation,
`0x783a18`, same-geometry reuse, active-pool copy-window arithmetic,
wait-object state transitions, active-loop branch predicates, render-entry
state handoff, and classifying `0x780eb6` as initialized-only bookkeeping
because each is backed by disassembly, reference scans, or checked fixtures.

Medium for physical engine pacing because the firmware-visible wait states and
MMIO-facing predicates are modeled, but connector-signal timing and exact
register-to-signal names are still board-level evidence.

## Remaining Edges

- `0x0d52..0x0f7a`, `0x0f84..0x0fa0`, and `0x1020..0x102e`: timer/status
  latches, output strobes, wait-object effects, and scheduler selection are
  modeled. Remaining work is mapping `$8000`, `$8a01`, `$a200`, `$a400`,
  `0xffff2000`, `$a601`, `$a801`, `$aa01`, `0xfffe0001`, and `0xfffe0003`
  to formatter/DC signals such as `BD`, `VDO`, `VSREQ`, `VSYNC`, `PRNT`,
  `CMND`, `CCLK`, `CBSY`, `STATS`, `PCLK`, `SBSY`, `RDY`, `PPRDY`, and
  `CPRDY`.
- `0x10bc..0x11f8` and `0x123a..0x1282`: trap veneers, copied trap vectors,
  wait-state transitions, and scheduler selection are modeled. Remaining work
  is timing relation to physical engine/MMIO events.
- `0x1cf8..0x1ea8`: helper return predicates around `0xa668` and `0xa680`
  are modeled. Remaining work is the external engine timing that makes
  `0x7828f9.6` ready or busy.
- `0xff1e..0x1ed84`: no unresolved software-visible middle edge remains for
  publication-to-active-render selection, render-work alternation, bridge
  fields, or scheduler-produced band words in the covered fixtures.
- `0x247c..0x2746`: helper semantics are decoded, but entry provenance is not.
  Current evidence stops at the absence of a `0x0000247c` target in
  `generated/analysis/ic30_ic13_long_reference_scan.md`, local returns at
  `0x2330` and `0x247a` before the separate helper body in
  `generated/disasm/ic30_ic13_engine_copy_pass_0022f4.lst`, and the expanded
  helper body in
  `generated/disasm/ic30_ic13_engine_copy_pattern_00247c.lst`. The broader
  decoded-search result does not add a caller: hits outside the helper body
  are unrelated opcodes or data values, not control-flow entries. Closing this
  edge requires a static caller, computed target, trap/vector entry, or
  scheduler-entry proof into `0x247c`, `0x26de`, or `0x270c`.
