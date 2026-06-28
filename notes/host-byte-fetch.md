# Host Byte Fetch Firmware

This note documents the 68000 host-byte fetch routine at `0x0000a904`.
It is the first firmware boundary for byte-stream reproduction: higher
parser and payload readers receive bytes from this routine in `D7`.

The routine is not a PCL parser. It multiplexes several possible byte
sources, performs hardware handshakes for direct I/O modes, runs service
work when the formatter is not ready, and returns either an unsigned byte
in `D7` or `D7 = -1` for one immediate no-byte/error branch.

Address names are provisional. The ROM proves the control flow and state
effects below; the exact Centronics/serial MMIO identity still needs board
or manual correlation.

## High-Level Behavior

`0xa904` chooses the next byte in this order:

1. If service flag `0x7821cd` is set, run service helper `0x10cc` and
   retry from the top.
2. If buffered-source flag `0x780e66` is set and gate byte `0x780e3b` is
   also set, return `D7 = -1`.
3. If first LIFO count `0x783e8c` is nonzero, predecrement pointer
   `0x783e8e`, read one byte, decrement the count, and return it.
4. If the active data-chain pointer `0x782d76` has a nonzero longword at
   offset `+4`, either call helper `0x9f6a` or consume an end marker and
   retry.
5. If second LIFO count `0x783e76` is nonzero, predecrement pointer
   `0x783e78`, read one byte, decrement the count, and return it.
6. If direct-input selector `0x780e40` is zero, read from the ring buffer
   at `0x783e56` when count `0x783e54` is nonzero.
7. If `0x780e40 == 1`, poll short MMIO status/data registers and perform
   the mode-1 handshake.
8. Otherwise, poll long MMIO status/data registers and perform the mode-2
   handshake.

This ordering matters for reproduction. Macro replay and other data-chain
sources can feed bytes before live host input, and the two LIFO sources can
override the ring or hardware sources.

The individual `0x780e66` bits are advisory pending flags, not the source
priority itself. `0xa904` still tests the concrete count/frame fields in the
order above. The bits keep the routine on the buffered-source path until the
producer state drains or a gate is cleared.

## Pseudocode

The following is intentionally close to the ROM branch structure:

```text
fetch_byte():
    if byte[0x7821cd] != 0:
        return service_and_retry_aa88()

    if byte[0x780e66] != 0:
        if byte[0x780e3b] != 0:
            return -1

        byte[0x780e66] &= 0xf7
        if word[0x783e8c] != 0:
            ptr = long[0x783e8e] - 1
            long[0x783e8e] = ptr
            word[0x783e8c] -= 1
            return byte[ptr]

        byte[0x780e66] &= 0xfb
        frame = long[0x782d76]
        if long[frame + 4] != 0:
            if long[frame + 4] == -1:
                long[frame + 4] = 0
                call 0xe22c
                return fetch_byte()
            return call 0x9f6a

        if word[0x783e76] != 0:
            ptr = long[0x783e78] - 1
            long[0x783e78] = ptr
            word[0x783e76] -= 1
            return byte[ptr]

        byte[0x780e66] &= 0xfe

    if byte[0x780e40] == 0:
        if word[0x783e54] == 0:
            return service_and_retry_aa88()
        ptr = long[0x783e56]
        value = byte[ptr]
        ptr += 1
        if ptr > 0x783e53:
            ptr = 0x783a4c
        long[0x783e56] = ptr
        word[0x783e54] -= 1
        return value

    if byte[0x780e40] == 1:
        return direct_mode_1()

    return direct_mode_2()
```

## Service Retry Paths

The common service path at `0xaa88` and the mode-2 service path at
`0xab70` both:

- set byte `0x7821cc = 1`;
- pass `A1 = 0x780202` to helper `0x10cc`;
- clear byte `0x7821cc`;
- branch back to `0xa904`.

This means a caller does not see a special service return. The routine
keeps trying until one of the byte sources produces a value or the
immediate `D7 = -1` branch is taken.

## Buffered Sources

### First LIFO Source

Branch `0xa92c..0xa94a` tests count word `0x783e8c`. When nonzero, it
loads pointer `0x783e8e`, reads `-(A2)`, writes the decremented pointer
back to `0x783e8e`, decrements `0x783e8c`, and returns the byte in `D7`.

The predecrement access means `0x783e8e` points one byte past the next byte
to be returned.

Helper `0x9ec0` is a producer for this stack. If `0x780e3b` is clear and the
current data-chain frame byte `+9` is nonzero, `0x9ec0` appends its byte
argument at `0x783e8e`, increments count `0x783e8c`, advances the pointer,
and sets `0x780e66.2` at `0x9f56`. The later `0xa904` consumer clears that
bit at `0xa94c` only after the first stack count has drained to zero.

### Active Data Chain

Branch `0xa954..0xa97c` loads `A2 = long[0x782d76]` and inspects
`long[A2 + 4]`.

- If the longword is zero, the routine skips this source.
- If the longword is nonzero and not `-1`, it calls `0x9f6a` and returns
  whatever that helper leaves in `D7`.
- If the longword is `-1`, it clears the longword, calls `0xe22c`, and
  restarts `0xa904`.

Macro/data-chain replay uses this mechanism: replay payload bytes are visible
to the parser as ordinary host bytes, and `0xe22c` runs when the frame reaches
its end marker. The known 14-byte frame classes are now tied to concrete
producers and consumers in `notes/semantic-state-model.md` under `Macro
Definition And Data-Chain Replay`: `0xe418` advances `0x782d76` and writes
execute/call frames with byte `+9 = 2` or `3`, while `0xe4f4` writes the
non-replay page-finalization frame at `0x782d4c` with byte `+9 = 4`.
Frame `+0x00/+0x04` hold the payload/chunk pointer and byte count consumed by
`0xa904` / `0x9f6a`; frame byte `+8` is `4`; frame `+0x0a` is the
environment-snapshot pointer for execute/call frames and zero for the
non-replay frame.

### Second LIFO Source

Branch `0xa980..0xa99e` is the same shape as the first LIFO source but
uses count `0x783e76` and pointer `0x783e78`.

The same helper `0x9ec0` is also the producer for this stack. If
`0x780e3b` is clear and the current data-chain frame byte `+9` is zero,
`0x9ec0` appends its byte argument at `0x783e78`, increments count
`0x783e76`, advances the pointer, and sets `0x780e66.0` at `0x9f1a`.
`0xa904` clears bit 0 at `0xa9a0` only after the second stack count is empty.

If `0x780e3b` is already set, `0x9ec0` returns `D7 = 1` immediately and does
not append to either stack. This prevents parser logging/replay helpers from
building more pushback state while the no-byte gate is active.

### No-Byte Gate Flag

The no-byte gate is a paired state: byte `0x780e3b` carries the gate itself,
and `0x780e66.3` keeps `0xa904` on the buffered-source branch long enough to
observe it. The two observed gate setters are `0x4322..0x4332` and
`0x622c..0x623c`; both write `0x780e3b = 1` and set `0x780e66.3`. While both
`0x780e66` and `0x780e3b` are nonzero, `0xa904` returns `D7 = -1` at
`0xa920` before checking any stack, data-chain, ring, or direct hardware
source. The main parser loop `0x117dc..0x117ee` is the observed consumer of
this gate: it tests `0x780e3b`, clears it at `0x117e8`, and then calls the
`0x10c8(0x780202)` wait/helper path.

### Ring Source

Branch `0xa9b2..0xa9e0` is used only when `0x780e40 == 0`. It tests
count word `0x783e54`, reads one byte from pointer `0x783e56`, advances
the pointer, wraps from after `0x783e53` back to `0x783a4c`, decrements
`0x783e54`, and returns the byte.

The ring source is the cleanest abstraction for a byte-stream renderer:
fixtures can seed the ring with a PCL byte stream and exercise parser,
page-object, and renderer behavior without modeling electrical I/O.

## Direct Mode 1

Direct mode 1 starts at `0xa9f0` when `0x780e40 == 1`.

The routine:

1. Initializes timeout counter `D0 = 0x2710`.
2. Polls byte register `0x8e01` until bit `0x10` is set.
3. On timeout, branches to the service retry path at `0xaa88`.
4. Reads one byte from `0x8801` into `D7`.
5. Masks `D7` to eight bits.
6. If the byte is `0x1a`, calls `0x9ec0` and restores `D7 = 0x1a`.
7. Waits until bit 0 of `0x8c01` clears.
8. Raises interrupt mask with `ori #0x700,SR` while toggling control.
9. If longword `0x780e0a` is zero, writes `0xdf` then `0xfb` to
   `0xa601`, writes two masked variants of shadow byte `0x7828fa` to
   `0xaa01`, clears byte `0x7828ec`, and clears longword `0x7821c4`.
10. Restores interrupt mask with `move #0x2000,SR` and returns `D7`.

If `0x780e0a` is nonzero, the path still writes `0xdf` to `0xa601` and
clears `0x7821c4`, but skips the `0xaa01` shadow toggles and the final
`0xfb` write to `0xa601`.

The physical identity of `0x8e01`, `0x8801`, `0x8c01`, `0xa601`, and
`0xaa01` is not assigned here. The firmware behavior is status poll,
data read, acknowledge wait, and control toggle.

## Direct Mode 2

Direct mode 2 starts at `0xaaa6` when `0x780e40` is nonzero and not `1`.

Before polling, the routine raises the interrupt mask. If longword
`0x780e0a` is zero and bit `0x20` of longword `0x780e26` is clear, it
clears bit `0x40` in shadow byte `0x7828fb`, writes the result to
`0xfffee009`, mirrors it back to `0x7828fb`, and clears `0x7828ec`.
It then restores the interrupt mask and begins polling.

The polling loop:

- initializes timeout counter `D0 = 0x2710`;
- reads status byte `0xfffee005`;
- if bit 7 is set, ORs `0x80` into longword `0x780e2e` and runs service;
- if bit 6 is set, ORs `0x40` into longword `0x780e2e` and runs service;
- if bit 0 is clear until timeout, runs service;
- if bit 0 is set, reads data byte from `0xfffee001`.

After a data byte is read, the routine masks `D7` to eight bits. The byte
`0x1a` is reported through `0x9ec0`, then restored as `D7 = 0x1a`, matching
direct mode 1.

The success handshake sets bit 6 in shadow byte `0x7828fb`, writes it to
`0xfffee009`, mirrors it in RAM, sets `0x7828ec = 1`, clears `0x7821c4`,
restores the interrupt mask, and returns `D7`.

## Cleanup Helper At 0xab8e

Routine `0xab8e` is not a byte source. It normalizes direct-input handshake
state after external code has run.

- If `0x780e40 == 1`, it repeats the mode-1 control toggle shape:
  clear `0x7828ec`, write two masked versions of `0x7828fa` to `0xaa01`,
  and write `0xfb` to `0xa601`.
- If `0x780e40 == 2`, it clears `0x7828ec`, clears bit `0x40` in
  `0x7828fb`, writes the result to `0xfffee009`, and mirrors it back to
  `0x7828fb`.
- Other selector values return without changing these handshake fields.

## Caller Semantics

`0xa904` is called by parser wrappers and by binary/text payload readers.
Those callers do not all interpret special cases the same way.

- Parser wrapper `0xda9a` uses `0xa904` as the normal next-byte source.
  If the byte is not `ESC`, it returns it to the main parser loop.
- The `0xdace` control probe fetches through `0xa904` and treats the exact
  sequence `0x1a 0x58` as a call to `0xd99a`, returning zero.
- Text repeat readers stop on negative `D7`. Their local `0x1a 0x58`
  probes call `0xd99a` and substitute `0x7f`.
- Raster payload and downloaded-font payload readers also have local
  `0x1a 0x58` probes, but they store zero for that sequence.
- Macro replay data-chain frames become visible through `0xa904`, so replayed
  macro bytes re-enter the same parser paths as host bytes.

For reproduction, do not normalize `0x1a 0x58` globally at the byte source.
The byte source returns bytes; each consumer family applies its own local
control-pair behavior.

## Semantic Checkpoint

This cluster is covered as the normalized byte-source boundary, not as a
physical I/O-board model. The firmware-observable contract is that all parser,
payload, transparent-text, macro, raster, and downloaded-font consumers see
bytes through the same `D7` return channel after the source-priority logic
above has run.

Field groups:

- Canonical byte-source state:
  - first pushback stack: count `0x783e8c`, pointer `0x783e8e`;
  - data-chain source: current frame pointer `0x782d76`, with frame
    `+4 == -1` meaning end transition through `0xe22c`; known frame byte
    `+9` values are execute `2`, call `3`, and non-replay page-finalization
    frame `4`;
  - second pushback stack: count `0x783e76`, pointer `0x783e78`;
  - ring source: count `0x783e54`, read pointer `0x783e56`, write
    pointer `0x783e5a`, and bounds `0x783a4c..0x783e53`.
- Canonical direct hardware state:
  - selector `0x780e40 == 1`: status `0x8e01`, data `0x8801`,
    acknowledge wait `0x8c01`, and control writes `0xa601`/`0xaa01`;
  - selector `0x780e40 != 0 && != 1`: status `0xfffee005`, data
    `0xfffee001`, and control write `0xfffee009`.
- Derived/cache bridge state:
  - `0x783e54` derives ring occupancy; `0xa6f4` derives free capacity as
    `0x400 - 0x783e54`;
  - `0x783e5e` is the low-water threshold adjusted by
    `0xa726..0xa73c`;
  - `0x783e62` is the status-escape sequence cursor reset to table
    `0xa8a4`.
- Firmware bookkeeping:
  - `0x7821cd` is the service-needed gate;
  - `0x7821cc` is set while `0x10cc(0x780202)` runs;
  - `0x780e66` gates stacked/data-chain sources. The observed source bits are
    bit 3 for the no-byte gate set by `0x4322` / `0x622c` with `0x780e3b`,
    bit 2 for the first pushback stack set by `0x9ec0` and cleared by
    `0xa904` after count `0x783e8c` drains, bit 1 for active data-chain
    frames set by `0xe418` / `0xe4f4` and cleared by `0xe22c` frame-end
    paths, and bit 0 for the second pushback stack set by `0x9ec0` and
    cleared by `0xa904` after count `0x783e76` drains;
  - `0x780e3b` forces the immediate `D7 = -1` return while
    `0x780e66` is set;
  - `0x7821c4`, `0x7828ec`, `0x7828fa`, `0x7828fb`, and `0x780e2e`
    record direct-mode timeout, active-byte, control-shadow, and
    status/error state.
- Parser scratch:
  - none is owned by `0xa904`. Parser scratch begins after a returned byte
    reaches `0xda9a`, `0x11774`, `0x12218`, or the payload readers.
- Unknown:
  - board-level names and timing for the direct MMIO banks;
  - data-chain frame-byte values outside the observed `+9 = 2`, `3`, and
    `4` producers, if any;
  - full high-level owner names for the two gate-setter routines at
    `0x4322..0x4332` and `0x622c..0x623c`.

Writers:

- `0xa904` consumes the first stack, data-chain source, second stack,
  ring, or direct hardware source; it updates counts, pointers, `0x780e66`,
  `0x7821c4`, `0x7828ec`, `0x7828fa`, `0x7828fb`, and `0x780e2e`.
- `0xa904` calls `0x10cc(0x780202)` on service or timeout paths and
  `0xe22c` when a data-chain frame end marker is reached.
- `0xa6cc` and `0xa846` feed the ring source consumed by `0xa904`.
  `0xa6cc` also writes low-water, full-buffer, and status-service fields
  including `0x780e2a`, `0x780e2e`, `0x783e60`, `0x783e61`,
  `0x783e62`, and `$aa01`.
- Macro setup helpers such as `0xe418` build data-chain frames that later
  replay through `0xa904`.
- `0x9ec0` writes the two pushback stacks: frame byte `+9 == 0` selects
  `0x783e76` / `0x783e78` and sets `0x780e66.0`; frame byte `+9 != 0`
  selects `0x783e8c` / `0x783e8e` and sets `0x780e66.2`.
- `0x4322..0x4332` and `0x622c..0x623c` set the no-byte gate pair
  `0x780e3b = 1` plus `0x780e66.3`; the main parser loop
  `0x117dc..0x117ee` observes and clears `0x780e3b`.

Readers and consumers:

- `0xda9a` and the parser dispatch loop at `0x11774` consume ordinary
  parser bytes and route printable/control streams to handlers such as
  `0xd04a`, `0xf02c`, and `0xedf8`.
- `0xdace` consumes bytes for its local `0x1a 0x58` control-pair probe.
- `0x12142`, `0x124bc`, and `0x12582` consume text-payload bytes and stop
  on negative `D7`.
- `0x138fa` copies raster payload bytes into queued raster objects.
- `0x168dc`, `0x168fe`, `0x16960`, `0x1697a`, `0x169ca`, and
  `0x169e0` consume downloaded-font payload bytes.
- Macro execute/call replay consumes data-chain bytes through `0xa904`,
  then re-enters the same parser/page-record path as direct host input.

Output effect:

- `0xa904` does not draw pixels. Its output effect is source equivalence:
  the same byte sequence can be supplied by ring input, data-chain replay,
  pushback stacks, or direct hardware and still enter the same parser and
  imaging handlers.
- Fixture `host-fetched mixed control stream reaches parser and page-record
  render` proves ring-sourced bytes route through `0xedf8`, `0xd04a`,
  `0xf02c`, and `0xd04a` before page-record rendering.
- Fixture `macro execute frame payload feeds 0xa904 data-chain bytes`
  proves replayed data-chain bytes enter through the same fetch routine.
- Fixture `combined host-fetched font download stream prints installed
  glyph` proves a long `0xa904` byte stream can cross font-control,
  payload, printable, publication, bridge, and render-entry boundaries.
- Fixture `0xa620/0xa668/0xa6cc engine shadow and byte bridge` proves
  the bridge can place byte `0x41` in the ring and the next `0xa904`
  fetch returns `D7 = 0x41`.

Confidence:

- High for source priority, service retry, no-byte return, stack/ring
  pointer movement, data-chain end retry, direct-mode `0x1a` reporting,
  mode-2 status accumulation, and software-visible bridge behavior.
- Medium for the physical signal names and timing attached to direct MMIO
  registers, because the ROM proves polling and handshake behavior but not
  board labels.

Fixture evidence:

- `0xa904 no-byte branch returns -1 before buffered sources`
- `0xa904 services pending work then prefers first LIFO source`
- `0xa904 data-chain end marker retries before second LIFO source`
- `0xa904 buffered ring source wins before direct hardware in mode 0`
- `0xa904 direct mode 1 preserves 0x1a and clears handshake state`
- `0xa904 direct mode 2 reads ready byte and sets control-shadow bit 6`
- `0xa620/0xa668/0xa6cc engine shadow and byte bridge`
- `macro execute frame payload feeds 0xa904 data-chain bytes`
- `host-fetched mixed control stream reaches parser and page-record render`
- `combined host-fetched font download stream prints installed glyph`

Disassembly evidence:

- `generated/disasm/ic30_ic13_host_byte_fetch_00a904.lst`:
  `0xa904..0xab8a`.
- `generated/disasm/ic30_ic13_a801_a601_io_00a4e8.lst`:
  `0xa6cc..0xa810` bridge behavior and `0xa846..0xa8c8` ring/sequence
  helpers.
- `generated/disasm/ic30_ic13_pcl_escape_parser_00da9a.lst`:
  parser wrapper consumers.
- `generated/disasm/ic30_ic13_payload_dispatch_011f82.lst`,
  `generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst`,
  and `generated/disasm/ic30_ic13_font_payload_readers_0168dc.lst`:
  payload consumers.

Unresolved middle edges:

- `0xa9e2..0xaa86`: physical interface name and exact electrical
  handshake for the `0x8e01`/`0x8801`/`0x8c01` bank.
- `0xaaa6..0xab8a`: physical interface name and exact electrical
  handshake for the `0xfffee005`/`0xfffee001`/`0xfffee009` bank.
- `0xa6cc..0xa810`: software ring/status bridge effects are modeled, but
  physical names and timing for `0xfffe0001`, `0xfffe0003`, and `$aa01`
  remain unassigned.
- `0x782d76 frame +0x00..+0x0d`: execute/call producers `0xe418` and
  non-replay page-finalization producer `0xe4f4` are documented. Remaining
  uncertainty is any producer for frame byte `+9` values outside observed
  `2`, `3`, and `4`.
- `0x4322..0x4332` and `0x622c..0x623c`: the local effect is proven as the
  no-byte gate pair `0x780e3b = 1` plus `0x780e66.3`. Their broader
  high-level caller names are still provisional.

## Reproduction Requirements

A byte-stream renderer can model this layer without electrical timing by
feeding bytes through the same source priority:

- preserve `D7 = -1` for callers that treat it as stop/error;
- preserve data-chain replay before live input;
- preserve both LIFO sources before the ring/direct sources;
- preserve ring wrap from after `0x783e53` to `0x783a4c`;
- preserve direct-mode `0x1a` reporting through `0x9ec0` while returning
  byte `0x1a`;
- preserve mode-2 status accumulation in `0x780e2e`;
- leave consumer-specific `0x1a 0x58` behavior to the payload/parser reader.

Hardware-accurate emulation would also need verified physical identities for
the MMIO registers. Pixel reproduction from a supplied byte stream does not
need that electrical detail as long as the byte source presents the same byte
sequence to the parser and payload readers.
