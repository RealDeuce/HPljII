# Active Render Scheduler

This note documents the ROM-visible scheduler handoff from a published
page/control record to active render work and band rendering. It is the
checkpoint after page-record producers and `0xff1e` publication, and before
the bitmap object dispatchers consume render records.

Status: composed for the software-visible scheduler state, active source
selection, two-work-record alternation, per-band render loop, wait-object
handoff, and rendered output fixtures. Physical formatter/DC timing remains a
separate board-facing boundary.

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

Fixture `0x1eb2a/0x1ecd6 selects published record for render entry` proves
published source record `0x00d0eaa0` is copied to active source `0x780eae`,
assigned render work record `0x782128` through `0x783a18`, and rendered to the
same rows as the direct `0x1ed84` / `0x1ef6a` fixture.

Fixture `0x1ecd6 same-geometry render work reuse reaches render entry` proves
the sibling branch reuses prior geometry, computes destination word `+8`
through `0x33238`, and still reaches the same composed rows.

Fixture `0x1eba4/0x1ef6a active render loop advances or yields bands` proves
the render, capacity-wait, cleanup, and throttle outcomes. In the render case,
it calls `0x1ef6a`, increments render work word `+0x10`, and increments
throttle word `+0x0e`.

Fixture `0x1eba4 scheduler band words render published downloaded glyph`
proves scheduler-produced band words `0..9` drive a published downloaded-glyph
record through `0x1ef6a`: only buckets `1` and `9` dispatch compact objects,
and bucket `9` produces visible row `86`.

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

Fixture `0x1eba4/0x1ef6a active render loop advances or yields bands` pins
these branch effects against the render-work fields. Fixture
`0x1eba4 scheduler band words render published downloaded glyph` composes the
render branch with a published page record: ten successive render calls use
band words `0..9`, and the visible output remains tied to the buckets selected
by `0x1ef6a`, not to any external timing source.

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
- per-band active loop behavior at `0x1eba4..0x1ecd2`;
- wait-object and trap state transitions that can wake or stall active work;
- derived band fields consumed by `0x1ef6a`.

## Confidence

High for pool-head versus scheduler-cursor distinction, candidate-slot
staging/release, `0x780eaa -> 0x780eae`, work-record alternation,
`0x783a18`, same-geometry reuse, active-pool copy-window arithmetic,
wait-object state transitions, active-loop branch predicates, and
render-entry output because each is backed by disassembly and fixtures.

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
