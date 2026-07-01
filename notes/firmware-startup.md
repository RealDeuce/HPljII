# Firmware Startup Notes

Sources: `generated/roms/ic30_ic13.bin`;
`generated/analysis/ic30_ic13_vectors.txt`;
`generated/analysis/ic30_ic13_startup_tables.txt`; focused listings under
`generated/disasm/`.

Address values in this note are 68000 logical addresses decoded from the
`IC30,IC13` interleave. The first byte in each 16-bit word comes from
IC30 and the second from IC13.

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

## Configuration Inputs Seen Early

Early startup tests bits from low memory-mapped addresses:

- `btst #5, 0x8000`
- `btst #6, 0x8000`
- `btst #7, 0x8000`
- byte read from `0x8c01`

These likely represent formatter configuration, installed options,
panel/interface state, or board strapping. Their effect should be traced
before treating any startup defaults as fixed.

## Next RE Targets

- Name each MMIO address touched before `0x00000400`.
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
