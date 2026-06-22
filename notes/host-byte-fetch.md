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

### Active Data Chain

Branch `0xa954..0xa97c` loads `A2 = long[0x782d76]` and inspects
`long[A2 + 4]`.

- If the longword is zero, the routine skips this source.
- If the longword is nonzero and not `-1`, it calls `0x9f6a` and returns
  whatever that helper leaves in `D7`.
- If the longword is `-1`, it clears the longword, calls `0xe22c`, and
  restarts `0xa904`.

Macro execute/call replay uses this mechanism: replay payload bytes are
visible to the parser as ordinary host bytes, and `0xe22c` runs when the
frame reaches its end marker.

### Second LIFO Source

Branch `0xa980..0xa99e` is the same shape as the first LIFO source but
uses count `0x783e76` and pointer `0x783e78`.

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
