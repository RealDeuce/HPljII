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
- `generated/disasm/ic30_ic13_timer_status_trampoline_000d52.lst`
- `generated/disasm/ic30_ic13_scan_status_interrupt_000f84.lst`
- `generated/disasm/ic30_ic13_scheduler_trap_handlers_00110c.lst`
- `generated/disasm/ic30_ic13_startup_render_work_init_02feb6.lst`
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
  `0x78399f`, `0x78398c`, `0x783990`, `0x7839ac`, `0x7828f9`,
  `0x780e32`, `0x780e36`, `0x780e6d`, and `0x780e67`.
- Firmware bookkeeping: active flags `0x780ea4` / `0x780ea5`, active-pool
  copy-window fields `0x7839d2` / `0x7839d4`, timer/status divider bytes
  `0x78017f..0x780181`, and wait-object records selected by `0x123a`.
- Parser scratch: none. Parser and command-family state has already become
  page-record storage before this owner runs.
- Hardware/external state: formatter/DC signal names and physical timing for
  MMIO-backed readiness, copy, and wait predicates.
- Unknown: stable semantic name for `0x7839d4` beyond active-pool copy-window
  bookkeeping.

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

Firmware bookkeeping:

- `0x780ea4` / `0x780ea5`: active render/scheduler flags written around
  `0x1eb32..0x1eb50`.
- `0x7839d2` and `0x7839d4`: active-pool copy-window bookkeeping.
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
- Stable semantic name for `0x7839d4` beyond active-pool copy-window
  bookkeeping.

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
  status latches that can delay or wake the next band call.
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

## Writers

- `0xff1e` publishes state byte `+4 = 2`, writes source root longword to
  `0x780ea6`, sets publication flag `0x782996`, and clears the current root.
- `0x3144..0x3162` initializes `0x780ea6`, `0x780eaa`, `0x780eae`,
  `0x780eb2`, and `0x780eb6` to pool base `0x780f02`.
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

Fixture `0x1eb2a/0x1ecd6 selects published record for render entry` checks the
documented branch with published source record `0x00d0eaa0`: the record is
copied to active source `0x780eae`, assigned render work record `0x782128`
through `0x783a18`, and reaches the same ROM-local render-entry path as a
direct `0x1ed84` / `0x1ef6a` setup.

Fixture `0x1ecd6 same-geometry render work reuse reaches render entry` checks
the sibling branch: it reuses prior geometry, computes destination word `+8`
through `0x33238`, and still reaches the documented render-entry path.

Fixture `0x1eba4/0x1ef6a active render loop advances or yields bands` checks
the render, capacity-wait, cleanup, and throttle outcomes. In the render case,
the documented branch calls `0x1ef6a`, increments render work word `+0x10`,
and increments throttle word `+0x0e`.

Fixture `0x1eba4 scheduler band words render published downloaded glyph`
checks scheduler-produced band words `0..9` against a published
downloaded-glyph record through `0x1ef6a`: only buckets `1` and `9` dispatch
compact objects, and bucket `9` reaches the ROM-derived row-write path for
page row `86`.

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

## Confidence

High for pool-head versus scheduler-cursor distinction, candidate-slot
staging/release, `0x780eaa -> 0x780eae`, work-record alternation,
`0x783a18`, same-geometry reuse, active-pool copy-window arithmetic,
wait-object state transitions, active-loop branch predicates, and render-entry
state handoff because each is backed by disassembly and checked by fixtures.

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
