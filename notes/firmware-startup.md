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

## RAM Trampoline Initialization

Routine `0x00000298` copies a table from ROM address `0x000004c0` into
`0x00780000`. Each entry appears to be a `JMP absolute long` stub:

- writes opcode word `0x4ef9`.
- copies the longword destination from the table.
- repeats for a count word loaded from `0x000004c0`.

This explains why the exception vectors point into `0x00780000` in
six-byte increments.

The table count word is `0x003d`, so 62 jump stubs are copied. Early
destinations include:

- `0x00780000`
  - Destination: `0x00000c7e`
  - Current interpretation: bus-error style exception path; sets code
    byte `1`, then branches to `0x128c`
- `0x00780006`
  - Destination: `0x00000c8c`
  - Current interpretation: address-error style exception path; sets
    code byte `2`, then branches to `0x128c`
- `0x0078000c`
  - Destination: `0x00000c9a`
  - Current interpretation: illegal-instruction style exception path;
    sets code byte `3`, then branches to `0x128c`
- `0x00780018`
  - Destination: `0x00000cb6`
  - Current interpretation: exception path; sets code byte `5` then
    branches to `0x128c`
- `0x00780024` and many unused vectors
  - Destination: `0x00000cd2`
  - Current interpretation: default exception path; sets code byte `7`
    then branches to `0x128c`
- `0x0078008a`
  - Destination: `0x00000ce6`
  - Current interpretation: saves registers and calls `0x0000a4e8`
    before
    returning
    through
    `0x1064`
- `0x00780096`
  - Destination: `0x00000cfc`
  - Current interpretation: tests `0x8e01`, updates state under
    `0x7839d2/0x7839d3`, and
    touches
    `0xa601`
- `0x0078009c`
  - Destination: `0x00000d52`
  - Current interpretation: status/tick-looking handler; polls `0x8000`
    bits and `0x8a01`, updates many `0x0078xxxx` state bytes

The exception-like paths write a severity/status byte to `0x783eef` and
branch to `0x128c`, which appears to emit or display a two-byte
error/status code through lower-level output routines.

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
- Extend the trampoline destination annotations beyond the early sampled
  handlers.
- Follow initialization calls `0x00000978`, `0x000008a2`, `0x000008dc`,
  `0x0000073a`, and `0x00000c24`.
- Extend the `HEAD`/`0x000000be` record model beyond the verified
  built-in resource window if cartridge or external resource images are
  available.
- Start a cross-reference table from writes into `0x0078xxxx`, because
  this range appears to hold early firmware state and copied handlers.
