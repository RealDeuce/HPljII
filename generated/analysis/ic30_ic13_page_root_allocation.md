# IC30/IC13 Page-Root Allocation Flow

Generated from the focused disassembly window
`generated/disasm/ic30_ic13_page_root_allocate_010084.lst` plus
cross-reference scans of the verified firmware image. This report pins the
page/control record allocation boundary that text, raster, rules, direct
controls, and reset/finalization all depend on before the `0x1edc6`
render-record bridge.

## `0x10084` Ensure-Root Contract

| Address | Instruction fact | Reproduction consequence |
| ---: | --- | --- |
| `0x1008c..0x10094` | loads current root `0x78297a` into `A5`/`D7` and branches to return when nonzero | existing page roots are reused without reinitializing queues, font slots, or stream-storage state |
| `0x10096..0x100a6` | tests pending bytes `0x782c73` and `0x782c72`; if either is set, calls `0x9ac2` at `0x100b0` | pending active-record/page work can run before the first root allocation |
| `0x100b6..0x100bc` | clears `0x782c73` and `0x782c72` after the wait/helper path | the allocation boundary consumes those pending latches |
| `0x100c2` | calls allocator `0x9a9a`; returned `D7` becomes the new root pointer | page roots are allocated from the page/control record pool, not from the later 0x100-byte display-list chunks |
| `0x100ca..0x100d6` | wraps root byte `+4 = 1` with `0x15a6` / `0x15ac` | new roots start as active class/state `1` before the initializer runs |
| `0x100dc..0x100e6` | clears stream byte count `0x782a70`, computes `A2 = root + 0x20`, and stores it in `0x782a72` | the root's `+0x20` longword is the head link for display-list storage chunks |
| `0x100ec..0x100f8` | stores the root in `0x78297a`, calls initializer `0x10110`, and clears `0x782990` | subsequent producers see the initialized current root and a cleared transient byte |
| `0x100fe..0x1010e` | loads `A4 = root+0x1c`, clears 256 longwords, then loops back to the fast-return path | compact/raster bucket heads are a 256-entry array at root `+0x1c`; allocation itself does not seed `0x782a76` |

## `0x10110` Root Initializer

| Root field | Instruction fact | Current interpretation |
| ---: | --- | --- |
| `+0x06` | `0x1013a` copies page-code byte `0x782da2` | root records the current page size code |
| `+0x08`, `+0x0a` | `0x10142..0x10146` clear both bytes | root-local publication/status flags start clear |
| `+0x0e`, `+0x10` | `0x10124..0x1012a` stores longword `-1` at `+0x10` and clears word `+0x0e` | page-band/start fields are reset before render scheduling |
| `+0x14` | `0x1014a` clears the root flags word | finalize/retry flags start clear on a fresh root |
| `+0x16` | `0x10158..0x10174` divides extent word `0x782db2` by `0x10` via `0x3324a` and stores the result | render/page width bucket count or band extent is derived from active horizontal extent |
| `+0x20` | `0x1014e` clears the display-list chunk head | the stream allocator will link 0x100-byte object-storage chunks here later |
| `+0x24`, `+0x28` | `0x10178..0x1017c` clears both list heads | rule/list and fixed-list queues start empty until producers insert objects |
| `+0x09` | `0x10186..0x101ae` adds `0x782db4 + 0x782dc0 + 0x20`, divides by `0x20`, and stores the low byte | vertical/band extent derives from page height plus printable offset |
| `+0x2c..+0x68` | `0x101d6..0x10212` clears all 16 context slots/live flags, then copies the current selected font-context longword into slot 0 | a fresh root has exactly one active render context until printable/font setup installs more slots |

## Call-Site Groups

Absolute `JSR` references to `0x10084`: `0x00d20a`, `0x00d49a`, `0x00d63c`,
`0x00d8ea`, `0x00d9ec`, `0x00da4c`, `0x00f0b6`, `0x00f10c`, `0x00f17a`,
`0x00f2b0`, `0x00f576`, `0x00f6ee`, ... (25 total).

| Producer family | Observed call sites | Reproduction implication |
| --- | --- | --- |
| printable text, unflagged and flagged handoffs | `0x00d20a`, `0x00d49a`, `0x00d63c`, `0x00d8ea` | these producers share the same root allocation and bucket/list initialization boundary |
| display-function/text fallback and post-finalize parser recovery | `0x00d9ec`, `0x00da4c`, `0x00ff9a` | these producers share the same root allocation and bucket/list initialization boundary |
| direct controls and cursor-positioning page advances | `0x00f0b6`, `0x00f10c`, `0x00f17a`, `0x00f2b0`, `0x00f576`, `0x00f6ee` | these producers share the same root allocation and bucket/list initialization boundary |
| raster and rectangle producers | `0x0106a4`, `0x0106ec`, `0x010d0a`, `0x010d38` | these producers share the same root allocation and bucket/list initialization boundary |
| text span flush and font/page setup paths | `0x012788`, `0x0127c4`, `0x012912`, `0x01c2d2`, `0x01ca08`, `0x01e0ee`, `0x01e922` | these producers share the same root allocation and bucket/list initialization boundary |

## Current Reproduction Contract

- A byte-stream reproduction must call the root-allocation boundary before any
  text/raster/rule producer writes under root `+0x1c`, `+0x24`, or `+0x28`;
  otherwise object identity and render ordering will not match the firmware.
- `0x10084` initializes the root and bucket array, but display-list object
  payload storage is still allocated later through `0x1381c`; the harness
  fixture therefore deliberately leaves `0x782a76` unchanged after first-root
  creation.
- The existing `tools/render_fixture_harness.py` checks `0x10084-modeled
  page-root allocation side effects`, `0x10110 page-root initializer installs
  selected context slot`, and `0x10110 page-root initializer copies geometry
  fields` pin these side effects in executable form before queueing short
  compact text through `0x1387c` and bridging through `0x1edc6`; the raster
  transfer fixture now also carries the same modeled allocation record through
  `0x105d0` before `0x13070` / `0x13250` queue the primary row object.
- The remaining fidelity gap is a live parser-state run that lets
  `0xd04a`/`0xd824`, `0x105d0`, or `0x10b80` call this allocator with real
  page/control pool records instead of the current abstract root pointer.
