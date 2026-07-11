# Firmware Startup Notes

Sources: `generated/roms/ic30_ic13.bin`;
`generated/analysis/ic30_ic13_vectors.txt`;
`generated/analysis/ic30_ic13_startup_tables.txt`; focused listings under
`generated/disasm/`.

Address values in this note are 68000 logical addresses decoded from the
`IC30,IC13` interleave. The first byte in each 16-bit word comes from
IC30 and the second from IC13.

## Owner Summary

This note owns the power-on startup baseline that must exist before a supplied
host byte stream can be interpreted. Startup does not parse PCL and does not
queue page objects. It initializes RAM, heap/resource windows, byte-source
buffers, host-output FIFO, wait-object scheduler state, render-work seeds, and
default-environment fields that later parser/page/render owners consume.

Primary routes:

- Reset and RAM setup:
  reset entry `0x0110..0x0240` masks interrupts, performs early MMIO writes,
  runs RAM tests through `0x08a2` and `0x08dc`, clears RAM, and copies
  exception/trap stubs into `0x00780000`.
- Startup config and defaults:
  `0x02b2..0x031e`, `0x071c`, and `0x05ba` derive startup memory/config
  fields; `0x2c84` reads retained/default records and seeds default
  environment fields.
- Verification and allocator setup:
  `0x073a..0x0c22` verifies ROM/RAM/resource windows, computes heap/resource
  bounds through `0x099e` / `0x0b18`, and feeds heap initializer `0x164a`.
- I/O and render seeds:
  `0x2feb6` initializes render-work selectors, `0x3178` initializes host
  input ring/LIFO byte-source buffers, and `0x31d6` initializes the 64-byte
  host-output FIFO.
- Scheduler bootstrap:
  `0x0c24` builds wait-object records from table `0x15d0`, allocates private
  stacks, stores restart PCs, links the scheduler ring, and enters priority
  switch `0x1266`.

Field groups:

- Canonical startup memory/config:
  `0x780e59`, `0x780e5a`, `0x780e60`, `0x780e4c`, heap inputs
  `0x780efa` / `0x780efe`, and resource/fallback window fields
  `0x7810b4` / `0x7810b8`.
- Canonical heap/allocation state:
  free-unit count `0x780e86`, allocator bitmap/payload cursors
  `0x783972..0x783988`, and payload base consumed by page, macro, raster, and
  downloaded-font allocation.
- Canonical byte I/O state:
  host input ring/LIFO fields `0x783e54..0x783e8e`, mirror `0x7821c4`, and
  host-output FIFO fields `0x783ed2`, `0x783ed4`, and `0x783ed8`.
- Canonical scheduler/render state:
  wait-object records `0x780182..0x780262`, restart PCs from table `0x15d0`,
  render-work selector seeds `0x7820bc`, `0x7820c0`, `0x7820c8`, and
  `0x78212c`.
- Derived/cache state:
  MMIO shadows `0x7828fa`, `0x7828f9`, `0x7828f6`, timer divider bytes
  `0x78017f..0x780181`, debounce/status bytes, and startup-test gate
  `0x783eee`.
- Parser scratch:
  none at reset entry. Parser records and payload scratch are initialized by
  parser/reset paths after startup has created the scheduler and byte-source
  baseline.
- Firmware bookkeeping:
  RAM trampoline stubs, retained/default-environment startup bytes, startup
  diagnostic failure codes, and private scheduler stack frames.
- Hardware/external state:
  early MMIO reads/writes at `$8000`, `$8c01`, `$a200`, `$a400`, `$a601`,
  `$a801`, `$aa01`, `$ff8000`, `$fffe0001`, `$ffff3800`, optional `PROG`
  extension contents, and resource continuation decode after `0x0bffff`.
- Unknown:
  no software field ownership gap remains for the startup baseline fields
  documented here. Remaining uncertainty is physical MMIO naming, optional
  extension contents, and external memory-map/resource continuation behavior.

Output effect:

- Startup creates the baseline for later byte-stream reproduction: empty host
  input/output buffers, initialized heap allocator, render-work selectors,
  wait-object restart PCs, and default-environment state.
- It does not itself admit host bytes, parse commands, build page roots, or
  render pixels.
- A reproducer may assume this baseline only when it also preserves the
  documented startup fields or explicitly documents a different startup memory
  configuration.

## Reset Vectors

- Initial SSP: `0x00800000`.
- Reset PC: `0x00000110`.
- Most exception vectors point to the `0x00780000` region, spaced six
  bytes apart.
- The early code copies jump stubs into `0x00780000`, so the exception
  table appears to target RAM trampolines rather than ROM handlers
  directly.

## Reset Entry at 0x00000110

Observed sequence:

1. Four `NOP`s.
2. `SR = 0x2700`, masking interrupts.
3. 68000 `RESET`.
4. Delay loop from `D0 = 0x553`.
5. `SR = 0x2700` again.
6. Early hardware writes:
   - byte `0x00` to `0x0000a200`.
   - word `0x0000` to `0xffff3800`.
   - byte `0x03` to `0xfffe0001`.
   - byte `0xf1` to `0x0000aa01`.
   - byte `0x00` to `0x0000a601`.
   - byte `0x7e` to `0x0000a801`.
7. Timing/control loop driven by a table at `0x0000048e`, writing words
   to `0x0000a400`.

The timing/control table starts with count word `0x0007`, meaning eight
writes. Each table row supplies a word written to `0xa400`, then a
longword delay count:

| Entry | Table address | `0xa400` value | Delay |
| ---: | --- | --- | --- |
| 0 | `0x000490` | `0xcfe8` | `0x00000c00` |
| 1 | `0x000496` | `0xcfe8` | `0x0000009b` |
| 2 | `0x00049c` | `0xcfe8` | `0x0000009b` |
| 3 | `0x0004a2` | `0xc7e8` | `0x00000027` |
| 4 | `0x0004a8` | `0xf7e8` | `0x00000027` |
| 5 | `0x0004ae` | `0xfee8` | `0x00000600` |
| 6 | `0x0004b4` | `0xf9e8` | `0x00000027` |
| 7 | `0x0004ba` | `0xf348` | `0x00000027` |

The `0xa200`, `0xa400`, `0xa601`, `0xa801`, `0xaa01`, `0xfffe0001`, and
`0xffff3800` accesses are current MMIO candidates. Their exact device
roles need board correlation and later code tracing.

## RAM Tests and Setup

The first RAM test starts at `0x00ffe000`:

- Base: `A0 = 0x00ffe000`.
- Count: `D0 = 0x03ff`.
- Pattern: `0x5555aaaa`, swapped between passes.
- Failure branch: `0x0000022c`.

The next test writes increasing words every `0x100` bytes, then reads
them back. After the tests pass, the code clears the tested region and
sets:

- Stack pointer: `A7 = 0x00ffe100`.
- RAM trampoline base: `A0/A2 = 0x00780000`.

The startup then calls routines at:

- `0x00000978`
- `0x000008a2`
- `0x000008dc`

On success it clears `0x2000` longwords at `0x00780000`, then enters the
next initialization phase at `0x00000240`.

The three formerly opaque calls are now classified from focused listings
`generated/disasm/ic30_ic13_startup_memory_probe_00073a.lst` and
`generated/disasm/ic30_ic13_startup_memory_tests_0008a2.lst`:

- `0x0978(A0)` maps a tested RAM address back to an address-control
  register: it subtracts `0x4000`, shifts right by 13, ORs
  `0x00ff0000`, and writes word `0xffff` to that computed address. The
  reset path first calls it with `A0 = 0x00c00000`, so the computed
  write is `0xffff` to `0x00ffffe0`.
- `0x08a2(A0, D0)` is a destructive longword RAM test over `D0 >> 2`
  longwords, run twice with swapped pattern `0x5555aaaa` /
  `0xaaaa5555`. Failure sets `D7 = 0x0000b407`.
- `0x08dc(A0, D0)` is an address-line/style byte test. It writes and
  verifies 256 sequential bytes from base `A0`, 255 bytes spaced by
  `0x100`, and seven bytes spaced by `0x10000`, seeded from input byte
  `D0`. Failure also sets `D7 = 0x0000b407`.

The second initialization phase starts at `0x0240`:

- `0x0266..0x0296` seeds MMIO shadow defaults
  `0x7828fa = 0xf1`, `0x7828f9 = 0x7e`, and `0x7828f6 = 0xf348`, copies
  the RAM trampoline table through `0x0298`, probes optional `PROG`
  extension signatures through `0x03e8`, calls `0x071c`, derives
  board/config memory defaults through `0x02b2`, and calls `0x2c84`.
- `0x2c84` is the startup/default-environment entry cross-linked in
  [semantic-state-model.md](semantic-state-model.md) under
  `Default Environment Record Producers`. It calls `0x5a16` to bulk-read
  retained default records through `0x97e4`, samples the debounced
  panel/service byte through `0xa3ca`, enters the cold-reset fallback
  through `0x5a62` when that byte is `0xdf`, optionally checks the
  `0x9d` service path through `0x5d2a`, displays `0xb15f` or `0xb1a3`
  through `0x9182`, calls `0x5f96` to load/validate the active default
  record, and seeds environment bytes `0x780e44`, `0x780e45`,
  `0x780e46`, `0x780e47`, `0x780e4e..0x780e55`, `0x780e57`, and
  `0x780e58` at `0x02cd4..0x02d3c`.
- `0x071c` reads word `$ff8000`, inverts it, extracts bits `0x0f00`, shifts
  them down, and stores the resulting nibble in `0x780e4c`.
- `0x02b2..0x031e` derives startup memory-size fields. It writes
  `0x780e59` from `$8000.5`, initializes `0x780e5a = 0x20` and
  `0x780e60 = 6`, reads `$8c01 >> 3`, optionally calls `0x05ba` when
  `0x780e4c.3` is clear, and adds `0x80`, `0x40`, or `0x100` to
  `0x780e5a` for selected nonzero/strap values.
- `0x05ba` is the optional startup config probe. It reconstructs an encoded
  probe word through `0x19a78`, uses constants `0xd6`, `0x50`, `0xad`, and
  the reconstructed byte as four `$800000 + 2 * value` probe addresses,
  samples `$8c01 >> 3` twelve times into a 24-bit shift register, decodes a
  selector through the lookup table at `0x070c`, and returns either low-two
  bits or `-1`. `0x02b2` masks that result with `3` before deciding whether
  to add `0x80`, `0x40`, `0x100`, or no increment to `0x780e5a`.
- `0x0320..0x038c` calls `0xa16a`, acknowledges interrupt/status
  registers through `0x0336`, then calls allocator/reset helpers
  `0x164a`, `0x2feb6`, `0x3178`, and `0x31d6`.
- `0x038e..0x03e6` initializes timer/status divider state:
  `0x78017f = 4`, `0x780180 = 2`, `0x780181 = 5`, clears
  `0x782900` and `0x7828fe`, and seeds debounce bytes `0x783edc` and
  `0x783edd` from `$8000.6/.7`.

Startup verifier `0x073a` then runs with `0x783eee.5` set. It clears
`$a200`, optionally checks ROM/data byte sums at `0x000000..0x03ffff`
and `0x080000..0x0bffff`, tests RAM/resource windows, sets up heap and
resource bounds through `0x099e` / `0x0b18`, and finally returns through
`D7`. Failure code `0x0000b3e5` identifies the code-pair byte-sum
check, `0x0000b3f6` identifies the resource-pair byte-sum check,
`0x0000b407` identifies memory/address-line tests, `0x0000b418`
identifies the `0xffc000` scratch/video-memory test, and `0x0000b429`
identifies resource-window alias/pattern tests.

Routine `0x0c24` is the scheduler bootstrap, not parser code. It reads
an eight-record table at `0x15d0`, writes wait-object links and
metadata into `0x780182..0x780262`, allocates private stacks downward
from `0x00ffe000`, stores restart PCs in each stack frame, closes the
ring by pointing the final record back to `0x780182`, and tail-enters
the priority switch at `0x1266` with `A1 = 0x780262`.

Decoded `0x15d0` wait-object rows:

| Record | Priority | Stack bytes | Restart PC |
| --- | ---: | ---: | --- |
| `0x780182` | 7 | `0x0180` | `0x001958` |
| `0x7801a2` | 6 | `0x0180` | `0x01eb2a` |
| `0x7801c2` | 5 | `0x0200` | `0x002828` |
| `0x7801e2` | 4 | `0x0180` | `0x00ae2c` |
| `0x780202` | 3 | `0x0200` | `0x002de4` |
| `0x780222` | 2 | `0x0280` | `0x00645a` |
| `0x780242` | 1 | `0x0200` | `0x01174e` |
| `0x780262` | 0 | `0x0080` | `0x0015b2` |

The later setup helpers immediately after `0x164a` are now classified
from focused listings
`generated/disasm/ic30_ic13_startup_render_work_init_02feb6.lst`,
`generated/disasm/ic30_ic13_startup_byte_source_init_003178.lst`, and
`generated/disasm/ic30_ic13_startup_status_ring_init_0031d6.lst`:

- `0x2feb6` walks the resource/fallback window
  `0x7810b4..0x7810b4 + 0x7810b8` once, then seeds render work selectors
  `0x7820bc = 1` and `0x7820c0 = 1`, and clears words
  `0x7820c8` and `0x78212c`.
- `0x3178` initializes the host byte-source buffers: it clears ring
  count `0x783e54`, second LIFO count `0x783e76`, and first LIFO count
  `0x783e8c`; sets ring read/write pointers `0x783e56` and `0x783e5a`
  to `0x783a4c`; sets ring low-water threshold `0x783e5e = 0x40`;
  sets sequence cursor `0x783e62 = 0xa8a4`; mirrors the ring write
  pointer into `0x7821c4`; sets second LIFO pointer `0x783e78` to
  `0x783e66`; and sets first LIFO pointer `0x783e8e` to `0x783e7c`.
- `0x31d6` initializes a 64-byte interface-output FIFO by clearing count
  `0x783ed2` and setting both pointers `0x783ed4` and `0x783ed8` to
  `0x783e92`.

Later setup calls `0x00000b18` before reset subroutine `0x00000370`
enters the heap allocator initializer at `0x0000164a`. With the observed
reset defaults `0x780e5a = 0x20` and `0x780e60 = 6`, `0x0b18` writes:

- `0x780efa = 0x783f4a`, the heap start input.
- `0x780efe = 0x000640b6`, the available heap byte count.
- `0x7810b4 = 0x007e8000`, the resource/window base.
- `0x7810b8 = 0x00017ffe`, the resource/window size minus two.

Initializer `0x164a` consumes `0x780efa`/`0x780efe`, reserves the prefix
`0x783f4a..0x784905` as occupied, seeds allocator free-unit count
`0x18cf` at `0x780e86`, stores bitmap-base pointer `0x784906` in
variable `0x783972`, stores payload-base pointer `0x784c40` in variable
`0x783988`, and initializes the low/high scan fields consumed by
`0x170c`, `0x1710`, and `0x18b4`. Evidence is the focused listing
`generated/disasm/ic30_ic13_heap_allocator_init_00164a.lst` and fixture
`0x164a initializes heap allocator bitmap and payload base`.

## Startup Baseline Composition Checkpoint

This checkpoint names the ROM-local baseline that later host-byte, parser,
page-record, and render notes assume exists before a supported PCL byte stream
is interpreted. It is the power-on/default-state counterpart to the software
reset checkpoint in [reset-default-environment.md](reset-default-environment.md).

Field groups:

- Canonical startup memory fields:
  `0x780e59`, `0x780e5a`, `0x780e60`, and `0x780e4c` describe startup memory
  and strap/config state derived by `0x02b2..0x031e`, `0x071c`, and optional
  probe `0x05ba`. `0x780efa` and `0x780efe` are heap start/count inputs from
  `0x0b18`; `0x7810b4` and `0x7810b8` are the startup resource/fallback window
  base and size-minus-two.
- Canonical heap and resource allocation state:
  `0x780e86`, `0x783972`, `0x783976`, `0x78397a`, `0x78397e`, `0x783982`,
  `0x783986`, and `0x783988` are written by `0x164a` and consumed by
  allocation/free helpers `0x170c`, `0x1710`, and `0x18b4`.
- Canonical byte I/O state:
  `0x783e54..0x783e8e` and `0x7821c4` are the host ring/LIFO byte-source
  buffers initialized by `0x3178` and later consumed by `0xa904`.
  `0x783ed2`, `0x783ed4`, and `0x783ed8` are the 64-byte interface-output FIFO
  initialized by `0x31d6` and consumed by `0xb022`, `0xb090`, and `0xb0c0`.
- Canonical scheduler state:
  wait-object records `0x780182..0x780262` are built by `0x0c24` from table
  `0x15d0`; their links, priorities, private stacks, restart PCs, and saved
  stack pointers are consumed by `0x1036`, `0x108e`, `0x123a`, and the copied
  trap handlers.
- Derived/cache state:
  MMIO shadows `0x7828fa`, `0x7828f9`, and `0x7828f6`; timer/status divider
  bytes `0x78017f`, `0x780180`, and `0x780181`; debounce/output bytes
  `0x782900`, `0x7828fe`, `0x783edc`, and `0x783edd`; and render-work selector
  seeds `0x7820bc`, `0x7820c0`, `0x7820c8`, and `0x78212c`.
- Parser scratch:
  none in the reset-entry startup block. Parser records and payload scratch are
  initialized by parser/reset paths such as `0xe146` and `0x11774`.
- Firmware bookkeeping:
  RAM trampoline stubs `0x780000..0x780173`, startup-test gate `0x783eee`,
  retained/default-environment startup bytes `0x780e44..0x780e58`, and the
  wait-object private stack frames created by `0x0c24`.
- Hardware/external state:
  early MMIO writes and reads at `$8000`, `$8c01`, `$a200`, `$a400`, `$a601`,
  `$a801`, `$aa01`, `$ff8000`, `$fffe0001`, and `$ffff3800` are hardware
  boundaries. The software-visible RAM fields written from those probes are
  documented here; board-level signal names remain outside this ROM-local
  checkpoint.
- Unknown:
  no unresolved software field ownership remains for the startup baseline
  fields listed above. Unknowns are physical MMIO/device naming, optional
  extension contents, and the physical memory-map continuation after the
  verified built-in resource pair.

Writers and readers:

- `0x0110..0x0240` masks interrupts, performs early hardware writes, runs RAM
  tests through `0x08a2` and `0x08dc`, and copies the RAM trampoline table
  through `0x0298`.
- `0x02b2..0x031e`, `0x071c`, and `0x05ba` write startup memory/config fields
  consumed by `0x0b18`, heap setup, and optional resource scans.
- `0x2c84` seeds default-environment startup fields and is semantically owned
  by `Default Environment Record Producers` in
  [semantic-state-model.md](semantic-state-model.md).
- `0x073a..0x0c22` verifies ROM/RAM/resource windows, computes heap/resource
  bounds through `0x099e` / `0x0b18`, and supplies `0x164a` and `0x2feb6`.
- `0x164a` consumes `0x780efa` / `0x780efe` and writes heap allocator state for
  later parser, macro, page-object, raster, and downloaded-font allocations.
- `0x2feb6` consumes the resource/fallback window once, seeds render work
  selectors, and clears paired render header words before active rendering.
- `0x3178` initializes the host byte-source buffers; `0x31d6` initializes the
  host-output FIFO.
- `0x0c24` builds the wait-object scheduler ring and tail-enters priority
  switch `0x1266`.

Output effect:

- Startup does not parse PCL bytes and does not create page objects. Its output
  effect is the initialized baseline for later reproduction: byte-source
  buffers are empty, host-output FIFO is empty, heap allocation state is ready,
  render work alternators are seeded, wait objects have restart PCs, and
  default-environment fields are available for reset/page layout consumers.
- Later visible output depends on these fields: `0xa904` needs the byte-source
  buffers, page/raster/font/macro allocation needs `0x164a` heap state,
  publication-to-render scheduling needs `0x2feb6` and `0x0c24`, and host
  status responses need the `0x31d6` FIFO.

### Startup Outcome Matrix

This matrix is the owner-level route from reset/startup code to the baseline
state consumed by host-byte, parser, page-record, and render owners. Startup
is successful for byte-stream reproduction when these software-visible
outcomes are present; early hardware probes remain boundaries only when they
change one of the fields listed here.

- Reset diagnostics and RAM trampoline setup:
  `0x0110..0x0240` masks interrupts, performs early MMIO writes, runs RAM
  tests through `0x08a2` and `0x08dc`, clears RAM, and copies RAM trampoline
  stubs through `0x0298` into `0x780000..0x780173`. The outcome is firmware
  bookkeeping and scheduler/trap entry plumbing, not parser state or page
  output. Failure codes `0xb407`, `0xb418`, and related verifier codes are
  diagnostic exits.
- Startup memory/config fields:
  `0x02b2..0x031e`, `0x071c`, and optional probe `0x05ba` write
  `0x780e59`, `0x780e5a`, `0x780e60`, and `0x780e4c`. These are canonical
  startup configuration fields consumed by `0x0b18` and resource/window setup.
  The physical meaning of `$8000`, `$8c01`, and `$ff8000` bits is external;
  the RAM fields written from those reads are ROM-local state.
- Default-environment startup handoff:
  `0x2c84` bulk-reads retained/default records, handles cold-reset/service
  fallback, and seeds default-environment bytes `0x780e44..0x780e58`. Those
  fields are firmware bookkeeping and canonical defaults for later reset,
  page-layout, paper-source, and font/context owners.
- Verifier and heap/resource window:
  `0x073a..0x0c22` verifies code/resource/RAM windows, then `0x099e` /
  `0x0b18` derive heap inputs `0x780efa` / `0x780efe` and resource/fallback
  window `0x7810b4` / `0x7810b8`. These fields are canonical allocator and
  resource-window inputs. The exact continuation after verified resource pair
  `0x0bffff` remains a physical memory-map boundary.
- Heap allocator baseline:
  `0x164a` consumes heap inputs and writes free-unit count `0x780e86`,
  allocator bitmap pointer `0x783972`, scan cursors `0x783976..0x783986`, and
  payload base `0x783988`. Page-root stream storage, macro chunks, raster
  rows, and downloaded-font payloads later consume this canonical allocator
  state through `0x170c`, `0x1710`, and `0x18b4`.
- Render-work seeds:
  `0x2feb6` consumes the resource/fallback window once, writes
  `0x7820bc = 1` and `0x7820c0 = 1`, and clears `0x7820c8` / `0x78212c`.
  This is derived render-work baseline state consumed by the active render
  scheduler before it alternates between work records.
- Host byte-source buffers:
  `0x3178` clears ring and pushback counts `0x783e54`, `0x783e76`, and
  `0x783e8c`, initializes ring pointers `0x783e56` / `0x783e5a`, LIFO
  pointers `0x783e78` / `0x783e8e`, and mirror `0x7821c4`. This is canonical
  input state consumed by `0xa904`; startup does not admit bytes itself.
- Host-output FIFO:
  `0x31d6` clears output count `0x783ed2` and initializes FIFO read/write
  pointers `0x783ed4` / `0x783ed8` to storage `0x783e92`. This is canonical
  host-output state consumed by `0xb022`, `0xb090`, `0xb0c0`, and `0xae2c`.
  It does not affect pixels except by possible host backchannel behavior.
- Wait-object scheduler ring:
  `0x0c24` builds records `0x780182..0x780262` from table `0x15d0`, allocates
  private stacks, stores restart PCs, closes the linked ring, and enters
  scheduler switch `0x1266`. This is canonical scheduler state consumed by
  wait/trap helpers, parser scheduling, interface output, and active render
  scheduling.

State grouping for this matrix:

- Canonical state:
  startup memory/config fields, heap/resource inputs, allocator cursors,
  byte-source buffers, output FIFO fields, wait-object records, and
  retained/default-environment startup fields.
- Derived/cache state:
  MMIO shadows `0x7828fa`, `0x7828f9`, `0x7828f6`, timer divider bytes
  `0x78017f..0x780181`, debounce bytes, render-work selector seeds, and
  startup-test gate `0x783eee`.
- Parser scratch:
  none. Parser records, delayed-payload state, and command-family scratch are
  created after startup by parser/reset owners.
- Firmware bookkeeping:
  RAM trampoline stubs, diagnostic failure codes, private scheduler stack
  frames, and retained/default loader scratch.
- Hardware/external state:
  early MMIO source identities, optional `PROG` extension contents, retained
  storage identity, and resource continuation decode beyond verified bytes.
- Unknown:
  no ROM-local startup writer/consumer edge is unknown for the documented
  baseline. Remaining unknowns are physical names/timing for MMIO inputs and
  outputs, optional external code/resource contents, and board memory-map
  policy for resource continuation.

Evidence and unresolved boundary:

- Detailed semantic composition is mirrored in
  [semantic-state-model.md](semantic-state-model.md) under `Firmware Startup
  And Allocator`.
- Focused disassembly:
  `generated/disasm/ic30_ic13_reset_000110.lst`,
  `generated/disasm/ic30_ic13_startup_retained_load_000266.lst`,
  `generated/disasm/ic30_ic13_startup_memory_probe_00073a.lst`,
  `generated/disasm/ic30_ic13_startup_memory_tests_0008a2.lst`,
  `generated/disasm/ic30_ic13_startup_config_init_00071c.lst`,
  `generated/disasm/ic30_ic13_startup_config_probe_0005ba.lst`,
  `generated/disasm/ic30_ic13_startup_config_code_019a78.lst`,
  `generated/disasm/ic30_ic13_startup_heap_window_000b18.lst`,
  `generated/disasm/ic30_ic13_heap_allocator_init_00164a.lst`,
  `generated/disasm/ic30_ic13_startup_render_work_init_02feb6.lst`,
  `generated/disasm/ic30_ic13_startup_byte_source_init_003178.lst`,
  `generated/disasm/ic30_ic13_startup_status_ring_init_0031d6.lst`, and
  `generated/disasm/ic30_ic13_startup_scheduler_bootstrap_000c24.lst`.
- Generated evidence:
  `generated/analysis/ic30_ic13_vectors.txt` and
  `generated/analysis/ic30_ic13_startup_tables.txt`.
- Remaining edges are exact hardware/resource boundaries, not ROM-local
  startup field gaps: direct MMIO bit-to-signal naming, optional `PROG`
  extension contents at `0x200000` / `0x400000`, and the physical decode policy
  for resource continuation `0x0c0000..0x0c0321`.

## Reproduction Contract

For a supplied host byte stream, startup is reproduced when later parser,
allocator, page-object, scheduler, and render code see the same ROM-visible
baseline state. The required software behavior is:

- Reset entry `0x0110..0x0240` must reach the same post-test initialization
  path. RAM-test failure codes and early MMIO writes are startup diagnostics;
  they do not create parser bytes, page objects, or pixels.
- Startup config helpers `0x02b2..0x031e`, `0x071c`, and `0x05ba` write the
  memory/config fields consumed by `0x0b18`. A renderer that assumes the
  verified local baseline should preserve the documented `0x780efa`,
  `0x780efe`, `0x7810b4`, and `0x7810b8` values or explicitly document a
  different memory configuration.
- Startup config code `0x19a78..0x19b40` reconstructs an encoded value from
  `0x780ef4`, `0x780ef6`, and `0x780ef8` by packing the high selector bits,
  low bit run, and bit-transition position. Its result is startup
  configuration state used by later memory/resource setup, not parser
  command state.
- Heap initializer `0x164a` owns the allocation baseline. Page objects,
  macro/data-chain chunks, raster payloads, and downloaded-font payloads later
  depend on allocator fields `0x780e86`, `0x783972..0x783986`, and payload base
  `0x783988`.
- Host byte and interface-output buffers start empty. `0x3178` initializes
  ring/LIFO state `0x783e54..0x783e8e` and `0x7821c4`; `0x31d6` initializes
  output FIFO state `0x783ed2`, `0x783ed4`, and `0x783ed8`.
- Render-work and scheduler baselines are part of pixel reproduction.
  `0x2feb6` seeds render selectors and counters, while `0x0c24` builds
  wait-object records `0x780182..0x780262` with restart PCs including
  interface output, parser, and active render scheduler entries.
- Default-environment startup call `0x2c84` is the handoff into retained/default
  records. Its parser/page effects are consumed later by reset, page layout,
  and font/context notes; physical retained-storage identity remains an
  external boundary.
- Startup retained-load caller `0x0266..0x0296` seeds MMIO/control shadows
  `0x7828fa = 0xf1`, `0x7828f9 = 0x7e`, and `0x7828f6 = 0xf348`, installs
  RAM trampolines through `0x0298`, samples startup config through `0x071c`
  and `0x02b2`, then calls `0x2c84`. These writes form initial firmware
  bookkeeping and retained/default state before any host byte is admitted.

Physical names for reset MMIO registers are not required for byte-stream
pixel reproduction unless their sampled values change one of the software
fields above. Optional extension contents and the `0x0c0000..0x0c0321`
resource continuation remain explicit external memory-map boundaries.

## Startup `0x0078xxxx` Write Cross-Reference

This section is the startup-state write ledger for the ROM paths above. It
groups the early `0x0078xxxx` fields by writer and semantic class, so later
parser/render notes can cite the initialized state without rediscovering the
reset sequence.

- `0x780000..0x780173`: firmware bookkeeping. Writer
  `0x0298..0x02ac` copies table `0x04c0`; destinations are decoded in
  `generated/analysis/ic30_ic13_startup_tables.txt`. These are RAM
  exception/trap stubs, so vectors enter six-byte `JMP absolute` records
  instead of ROM directly.
- `0x7828fa`, `0x7828f9`, `0x7828f6`: derived/cache MMIO shadows.
  Writer `0x0266..0x027e` seeds defaults for later `$aa01`, `$a801`,
  and `$a400` output paths; `0x0b78` also toggles `0x7828f9.7` during
  scratch/video RAM tests.
- `0x783eee`: firmware bookkeeping. Writers `0x0244`, `0x0740`,
  `0x0770`, and `0x0b78..0x0bb6` use it as startup-test gate and
  expanded-memory-test flag before parser entry.
- `0x780e4c`: canonical startup config. Writer `0x071c..0x0734`
  stores the inverted `$ff8000` nibble; `0x02de..0x02ea` tests bit `3`
  to decide whether optional probe `0x05ba` supplies the memory selector.
- `0x780e59`, `0x780e5a`, `0x780e60`: canonical startup config.
  Writer `0x02b2..0x031e`, optionally using `0x05ba`, derives formatter
  memory/resource sizing. `0x0b18` consumes `0x780e5a` and `0x780e60`
  to derive heap and resource-window bounds.
- `0x780e44..0x780e58`: firmware bookkeeping. Writer `0x2c84..0x2d3c`
  seeds default-environment startup flags after `0x5f96`; the semantic
  consumer side is composed in `Default Environment Record Producers`.
- `0x78017f`, `0x780180`, `0x780181`: derived/cache timer divider
  seeds. Writer `0x038e..0x03a4`; consumer is the periodic trampoline at
  `0x0d52`.
- `0x782900`, `0x7828fe`, `0x783edc`, `0x783edd`: derived/cache
  output/debounce state. Writer `0x03a6..0x03e6`; consumers are later
  `$a200`/`$a400` rotation and `$8000.6/.7` status handling.
- `0x780efa`, `0x780efe`, `0x7810b4`, `0x7810b8`: canonical startup
  memory fields. Writer `0x0b18..0x0b5c` computes heap start/count and
  resource/fallback window base/span. `0x164a` consumes heap inputs;
  `0x2feb6` scans the resource window.
- `0x780e86`, `0x783972`, `0x783976`, `0x78397a`, `0x78397e`,
  `0x783982`, `0x783986`, `0x783988`: canonical heap allocator state.
  Writer `0x164a..0x1700` stores the free-unit count plus allocator
  bitmap/payload cursors consumed by `0x170c`, `0x1710`, and `0x18b4`.
- `0x7820bc`, `0x7820c0`, `0x7820c8`, `0x78212c`: derived/cache
  render-work state. Writer `0x2feb6..0x2ff0` seeds selectors and clear
  counters before the active render scheduler starts.
- `0x783e54..0x783e8e`, `0x7821c4`: canonical host input state.
  Writer `0x3178..0x31c8` initializes the host ring and two LIFO
  byte-source buffers consumed by `0xa904` and the byte-source helpers.
- `0x783ed2`, `0x783ed4`, `0x783ed8`: canonical host output state.
  Writer `0x31d6..0x31ea` initializes the 64-byte interface-output FIFO
  consumed by `0xb022`, `0xb090`, and `0xb0c0`.
- `0x780182..0x780262` wait-object records: canonical scheduler state.
  Writer `0x0c24..0x0c7a` uses table `0x15d0` to build the eight-record
  scheduler ring. `0x1266`, `0x1036`, `0x108e`, and `0x123a` consume
  the links, priorities, stack pointers, and restart PCs.

Parser scratch: none in this startup block. The first PCL parser scratch
fields are initialized later by parser/reset paths such as `0xe146` and
`0x11774`, not by reset entry `0x0110`.

Unknowns: this section does not name the physical devices behind `$8000`,
`$8c01`, `$a200`, `$a400`, `$a601`, `$a801`, `$aa01`, `$ff8000`, or the
computed address-control writes. Those remain board/MMIO correlation tasks,
not unresolved software field ownership inside `0x0078xxxx`.

## RAM Trampoline Initialization

Routine `0x00000298` copies a table from ROM address `0x000004c0` into
`0x00780000`. Each entry appears to be a `JMP absolute long` stub:

- writes opcode word `0x4ef9`.
- copies the longword destination from the table.
- repeats for a count word loaded from `0x000004c0`.

This explains why the exception vectors point into `0x00780000` in
six-byte increments.

The table count word is `0x003d`, so 62 jump stubs are copied. The full
destination ledger from
`generated/analysis/ic30_ic13_startup_tables.txt` and focused listings
`generated/disasm/ic30_ic13_trampoline_handlers_000c7e.lst`,
`generated/disasm/ic30_ic13_a801_a601_io_00a4e8.lst`,
`generated/disasm/ic30_ic13_timer_status_trampoline_000d52.lst`, and
`generated/disasm/ic30_ic13_scheduler_trap_handlers_00110c.lst` is:

- `0x780000 -> 0x000c7e`: exception/status report with `D1 = 1`,
  `0x783eef = 0xc0`, then `D0 = 0xe0` and `0x128c`.
- `0x780006 -> 0x000c8c`: exception/status report with `D1 = 2`,
  `0x783eef = 0xc0`, then `D0 = 0xe0` and `0x128c`.
- `0x78000c -> 0x000c9a`: exception/status report with `D1 = 3`,
  `0x783eef = 0x80`, then `D0 = 0xe0` and `0x128c`.
- `0x780012 -> 0x000ca8`: exception/status report with `D1 = 4`,
  `0x783eef = 0x80`, then `D0 = 0xe0` and `0x128c`.
- `0x780018 -> 0x000cb6`: exception/status report with `D1 = 5`,
  `0x783eef = 0x80`, then `D0 = 0xe0` and `0x128c`.
- `0x78001e -> 0x000cc4`: exception/status report with `D1 = 6`,
  `0x783eef = 0x80`, then `D0 = 0xe0` and `0x128c`.
- `0x780024..0x780084` and `0x780114..0x78016e -> 0x000cd2`:
  default exception/status report with `D1 = 7`, `0x783eef = 0x80`,
  then `D0 = 0xe0` and `0x128c`.
- `0x78008a -> 0x000ce6`: saves all registers, calls host/interface
  helper `0xa4e8`, restores all registers, then exits through `0x1064`.
- `0x780090 -> 0x000cf8`: explicit no-op interrupt, `NOP; RTE`.
- `0x780096 -> 0x000cfc`: tests `$8e01.2`; on the asserted path it
  gates `0x7839d3` into `0x7839d2`, signals wait object `0x780182`,
  writes `$a601 = 0xef`, and exits through `0x1064`. The other path
  calls `0xac88` and exits through `0x1064`.
- `0x78009c -> 0x000d52`: periodic timer/status trampoline. It
  acknowledges through `0xffff2000`, increments `0x780e04`, divides
  work through `0x78017f`/`0x780180`/`0x780181`, debounces
  `$8000.6/.7` and `$8a01.4`, rotates `$a200`/`$a400` output tables,
  and feeds wait-object scheduling before the shared `0x1064` exit.
- `0x7800a2 -> 0x00a812`: direct interface-status interrupt. It writes
  `$a601 = 0x9f` when `0x780e40 != 1`, writes `$a601 = 0xbf` when
  `$8e01.5` is set, otherwise writes `$a601 = 0xdf`, ORs `0x20` into
  `0x780e2e`, and returns with `RTE`.
- `0x7800a8 -> 0x000f84`: scan/status interrupt entry documented in
  `Published Record To Active Render Scheduler`; it drives `0x78398c`,
  pending bytes `0x78399e/0x78399f`, `$a801` shadow updates, and
  wait-object signals before the scheduler exit.
- `0x7800ae` and `0x7800f0..0x78010e -> 0x001032`: shared
  wait/scheduler entry around `0x1036`, currently documented by the
  `0x1036/0x108e/0x123a` fixture and semantic model.
- `0x7800b4 -> 0x00110c`: trap/status check. It raises the interrupt
  mask, returns immediately unless wait-object word `+0x0a` is zero,
  then enters the `0x1230` scheduler path.
- `0x7800ba -> 0x00111c`: wait-object restart path. It clears the
  active object's state word `+0x0a`, pushes saved restart payload and
  SR on its private stack, stores stack pointer `+0x1a`, then enters
  `0x125a`.
- `0x7800c0 -> 0x001144`: trap/status check. It returns unless
  wait-object word `+0x0a == 0x8006`, then enters the `0x1230`
  scheduler path.
- `0x7800c6 -> 0x001154`: saves all registers, writes active
  wait-object state `0x8006`, saves `D0` in word `+0x0c`, saves stack
  pointer `+0x1a`, then enters `0x125a`.
- `0x7800cc -> 0x001174`: saves all registers, writes active
  wait-object state `0x8007`, then shares the `0x1154` save path.
- `0x7800d2 -> 0x00118a`: saves all registers, normalizes an existing
  `0x8006` state to `2`, writes active wait-object state `0x8006`,
  saves `D0` and stack pointer, targets wait object `0x780182`, then
  enters `0x125a`.
- `0x7800d8 -> 0x0011be`: raises interrupt mask, returns wait-object
  word `+0x0a` in `D7`, then `RTE`.
- `0x7800de -> 0x0011ca`: raises interrupt mask; zero state returns,
  state `0xff` branches to the `0x111c` restart path, and any other
  state writes `9` and returns.
- `0x7800e4 -> 0x0011e8`: raises interrupt mask; state `9` enters the
  `0x1230` scheduler path, and other states return.
- `0x7800ea -> 0x0011f8`: raises interrupt mask; zero state returns,
  nonzero inactive objects are reset to state `0` and get a
  private-stack restart frame, and the active object redirects to
  `0x111c`.

The exception-like paths write a severity/status byte to `0x783eef` and
branch to `0x128c`, which emits or displays a two-byte error/status code
through lower-level output routines. The software-visible scheduler and
wait-object effects are composed in `Published Record To Active Render
Scheduler` in [semantic-state-model.md](semantic-state-model.md); the
unresolved part is still the board-level identity and timing of the
physical IRQ/MMIO sources that enter these copied stubs.

## Extension and Resource Probing

Routine `0x000003e8` reads `0x8000` and probes optional address spaces:

- If bit 6 allows it, it checks `0x00200000` for ASCII signature `PROG`,
  then jumps through the following longword.
- If bit 7 allows it, it checks `0x00400000` for ASCII signature `PROG`,
  then jumps through the following longword.

Routine `0x0000041a` scans a memory range for `HEAD` records. It probes
from the caller's `A1` base up to `A1 + 0x1ffff0`; a missed probe steps
by `0x40000`. Once it finds `HEAD`, it walks length-delimited records.
Null and `0xffffffff` records terminate the current chain and advance to
the next probe. If the cumulative walked length crosses the `0x40000`
boundary, the next probe step grows to `0x80000`, matching the
`D1` increment and `swap`/`lsl #2` sequence at `0x450..0x452` and
`0x42e..0x432`.

Type `0x000000be` is the executable handoff record. A length greater
than `7` jumps to the payload at `record + 8`; a length of `7` or below
reports `D0 = 0xe0`, `D1 = 0x10` through error/status helper `0x128c`.
The verified `IC32,IC15` built-in resource window has `HEAD` at
`0x080000`, walks 24 typed records from `0x08004c` through `0x0ae122`,
and terminates at `0x0b2f80` before the next `0x40000` probe. This
links the firmware's extension/resource probing to the same `HEAD`
signature found at the start of the resource ROM pair.
The scanner constraint fixtures also compare candidate bytes after the verified
resource pair: a simple resource-pair mirror would expose a second `HEAD` at
offset `0x40000`, while code-pair and zero-fill continuations present markers
`0x00800000` and `0x00000000` and therefore skip that probe.

## Early MMIO Cross-Reference

This ledger names the ROM-visible role of every direct MMIO access in the
reset path through `0x03ff`, plus the startup helpers that the same path calls
before scheduler entry. Physical device names remain unresolved unless a later
note cites board/manual evidence.

- `$a200`: reset writes byte `0` at `0x0132`, and verifier helper `0x077a`
  repeats that clear while startup tests run. Later timer/external-service
  paths rotate or assert it: `0x0d52..0x0f7a` is documented as rotating
  `$a200`/`$a400`, and `0xba9e` writes `$a200 = 0xff00` in the external-ready
  service loop.
- `$a400`: reset table `0x048e` drives eight word writes at
  `0x0164`/`0x016c`, each original word followed by bit-4 set. Retained-record
  helpers reuse the same output through shadow `0x7828f6`: `0x09a4a` masks
  low three bits, writes one phase to `$a400`, masks again, then writes a
  second phase. Startup seeds the shadow to `0xf348` at `0x0276`.
- `$a601`: reset writes byte `0` at `0x014e`. Later interface helpers write
  `$a601 = 0xf7` in `0xa4e8`, `$a601 = 0xfd` in scan/status interrupt
  `0x0f8e`, and `$a601 = 0x9f`/`0xbf`/`0xdf` in `0xa812..0xa834`.
- `$a801`: reset writes byte `0x7e` at `0x0154` and startup mirrors that
  default into shadow `0x7828f9` at `0x026e`. Later helpers mutate the shadow
  and rewrite `$a801`: `0xa42c`/`0xa444` bit 0, `0xa5c2`/`0xa5da` bit 2,
  `0xa620`/`0xa638` bit 1, `0xa650`/`0xa668` bit 6, `0xa69c` bit 7, and
  `0xbc88` low-three-bit status mirroring from `$fffee00b`.
- `$aa01`: reset writes byte `0xf1` at `0x0148` and startup mirrors that
  default into shadow `0x7828fa` at `0x0266`. Host-input helper
  `0xa6cc..0xa7ce` later combines shadow `0x7828fa` with status byte
  `0x780e49`, writes `$aa01`, and updates `0x7828fa`.
- `$8000.w`: reset/config code reads it directly for option/strap gates.
  `0x02b6` tests bit 5 before writing `0x780e59`; `0x03b2` and `0x03cc` test
  bits 6 and 7 before seeding debounce bytes `0x783edc`/`0x783edd`; `0x03e8`
  reads the byte and uses bits 6/7 to gate optional `PROG` probes at
  `0x200000` and `0x400000`. Helper `0xa3ca` later debounces the low byte for
  panel/default-environment entry, and `0x19dd2` uses bits 14/15 for optional
  resource-window scans.
- `$8c01`: reset reads it at `0x02d8`, shifts right three, and uses the
  low-two-bit result to adjust `0x780e5a` unless `0x780e4c.3` suppresses the
  optional probe. Helper `0x05ba` also samples `$8c01 >> 3` twelve times
  through encoded `$800000 + 2*n` probes; retained-record helper `0x994e`
  reads `$8c01` while building serial/default words.
- `$ff8000`: startup helper `0x071c` reads the word, inverts it, extracts
  bits `0x0f00`, shifts them down, and writes canonical config word
  `0x780e4c`. The reset path calls this helper at `0x0286`.
- `$fffe0001` / `$fffe0003`: reset writes `$fffe0001 = 3` at `0x0140`.
  Later host I/O helpers treat `$fffe0001` as a status register and
  `$fffe0003` as data: `0xa1b0` writes a byte to `$fffe0003` when
  `$fffe0001.1` is set, and `0xa6cc` reads `$fffe0003` into host input,
  first testing `$fffe0001.0` on the ring-producer path.
- `$ffff1020` / `$ffff2000`: reset helper `0x0336` writes `0xffff` to both
  addresses, optionally writes a computed `$ffff1020 + (0x780e3f >> 3 & 0x0e)`
  address, and writes `$ffff2000` again. The timer/status trampoline also
  acknowledges through `$ffff2000`.
- `$ffff3800`: reset writes word `0` at `0x0138`. No later focused listing in
  the current note assigns a software-visible shadow to it, so its physical
  role remains board/MMIO evidence rather than parser state.
- `$fffee005`, `$fffee003`, `$fffee001`, and related `$fffee00*` registers:
  not written before `0x0400`, but later host/output and external-service
  paths use them as the alternate MMIO bank when `0x780e40` selects that mode.
  Evidence is in `ic30_ic13_interface_output_mmio_00a1b0.lst`,
  `ic30_ic13_a801_a601_io_00a4e8.lst`, and
  `ic30_ic13_external_ready_service_loop_00ba48.lst`.

Unresolved physical names: `$8000`, `$8c01`, `$8e01`, `$8801`, `$a200`,
`$a400`, `$a601`, `$a801`, `$aa01`, `$ff8000`, `$fffe0001`, `$fffe0003`,
`$ffff1020`, `$ffff2000`, `$ffff3800`, and the `$fffee00*` bank still need
board/manual correlation. The ROM-side state ownership and consumers above are
documented; the remaining gap is physical identity and timing.

## Next RE Targets

- Correlate the ROM-visible early-MMIO ledger above with physical
  board/manual names.
- Correlate the now-classified copied trampoline entries with the physical
  IRQ/MMIO sources that select each RAM stub.
- Keep startup cross-linked to the default-environment checkpoint for
  `0x00002c84`. Startup helpers `0x000005ba`, `0x0000071c`,
  `0x0000073a`, `0x000008a2`, `0x000008dc`, `0x00000978`,
  `0x00000b18`, and `0x00000c24` are documented as
  config/memory/resource/scheduler setup; startup helpers `0x0002feb6`,
  `0x00003178`, and `0x000031d6` are documented as render-work and
  byte/status-buffer setup. The remaining startup boundary is physical
  naming for MMIO/config inputs and retained-storage/control-panel
  devices, not an untraced software callee in this cluster.
- Extend the `HEAD`/`0x000000be` record model beyond the verified
  built-in resource window if cartridge or external resource images are
  available.
