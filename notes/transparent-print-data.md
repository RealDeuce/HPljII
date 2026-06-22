# Transparent Print Data Firmware

This note documents the `ESC &p#X` transparent print data path. It is an
end-to-end parser cluster: a parsed PCL command schedules a delayed payload
handler, the handler consumes raw host bytes, and printable payload bytes re-enter
the normal text imaging path.

Evidence:

- `generated/disasm/ic30_ic13_transparent_data_handler_011f5a.lst`
- `generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst`
- `tools/render_fixture_harness.py`, fixtures:
  - `0x11f5a/0x12452 transparent text restores and consumes counted bytes`
  - `transparent data parser trace feeds page-record queue`

## Command Boundary

`ESC &p#X` reaches handler `0x11f5a`. The handler is only an arming stub:

1. Push handler pointer `0x12452`.
2. Call the shared delayed-payload scheduler `0x121cc`.
3. Return.

`0x121cc` rewinds `0x78299e` by six, saves the current six-byte command
record, and stores the delayed handler pointer in `0x782a1c`. Later, when the
parser returns to mode zero, `0x12218` restores that saved record and calls
`0x12452` in normal parser mode.

For `ESC &p2X`, the saved record is:

```text
80 58 00 02 00 00
```

The delayed snapshot stored by `0x121cc` is:

```text
01 00 01 24 52 80 58 00 02 00 00
```

That snapshot means: pending flag `1`, handler `0x00012452`, then the saved
six-byte command record.

## State Classification

Canonical fields:

- `0x78299e`: six-byte command-record cursor. `0x12452` rewinds it by six
  before reading the restored record.
- command record `+2`: signed byte count. `0x12452` takes the absolute value.
- `0x782f06`: selected font/context slot used to choose the payload control
  filtering state.

Derived/cache fields:

- `0x782eea + 0x10 * selected_slot`: context byte copied to `D3` after helper
  `0x332ee` scales the selected slot.
- `0x782efa`: fallback filtering byte used when high-character flags are clear.
- `0x783132` and `0x783133`: high-character state flags that choose whether the
  local filtering word comes from the context byte or `0x782efa`.

Parser scratch:

- `0x782a1a`: delayed-payload pending flag.
- `0x782a1c`: delayed handler pointer.
- `0x782a20..0x782a25`: saved six-byte command record.

Firmware bookkeeping:

- local stack word at `A6-2`: the control-byte filtering word selected before
  the payload loop.

Unknown:

- Manual-facing names for the context byte at `0x782eea + 0x10 * slot`, the
  fallback byte `0x782efa`, and high-character flags `0x783132`/`0x783133`.

## Payload Reader At 0x12452

`0x12452` is a counted reader. It does not use `0xdace`. It calls `0xa904`
directly and implements its own handling for the `0x1a 0x58` host-control pair.

Setup behavior:

1. Rewind `0x78299e` by six.
2. Read signed word record `+2`.
3. Convert it to an absolute byte count in `D4`.
4. Read selected context slot `0x782f06`.
5. Call helper `0x332ee` with scale/count `0x10`.
6. Read context byte at `0x782eea + scaled_slot`.
7. If both `0x783132` and `0x783133` are clear, use byte `0x782efa` as the
   local filtering word.
8. Otherwise use the selected context byte as the local filtering word.

Loop behavior:

1. If count `D4 <= 0`, return.
2. Fetch one byte through `0xa904`.
3. If the byte is `-1`, return early.
4. If the byte is not `0x1a`, classify it.
5. If the byte is `0x1a`, fetch one more byte through `0xa904`.
6. If the second byte is `0x58`, call `0xd99a` and replace the payload value
   with `0x7f`.
7. If the second byte is not `0x58`, classify that second byte. The original
   `0x1a` is consumed by the probe.
8. Route the resulting value through either `0xd0f0` or `0xd04a`.
9. Decrement `D4` once per routed payload value.
10. Repeat until the absolute count is consumed or `0xa904` returns `-1`.

The control probe matters for reproduction. A byte stream containing `1a 58`
contributes one transparent payload value, `0x7f`, while consuming two host
bytes. A byte stream containing `1a 41` contributes `0x41`, not `0x1a`.

## Payload Routing

After normalization, `0x12452` chooses between fixed-space/control handling and
printable text handling:

- Values `0x00..0x1f` call `0xd0f0` only when the selected context byte in `D3`
  is zero. If `D3` is nonzero, they call `0xd04a`.
- Values `0x80..0x9f` call `0xd0f0` only when the local filtering word at
  `A6-2` is zero. If the local filtering word is nonzero, they call `0xd04a`.
- All other values call `0xd04a`.

`0xd0f0` is the same fixed-space source-object path used by direct text
handling. `0xd04a` is the normal printable text path into character mapping,
cursor placement, compact text object creation, page-record storage, bridge,
and render dispatch.

## Fixture Evidence

The isolated transparent reader fixture uses saved record:

```text
80 58 00 05 00 00
```

and payload bytes:

```text
41 1a 58 05 85 42
```

The ROM-modeled result is:

- byte count: `5`
- consumed values: `41 7f 05 85 42`
- routes: `d04a d04a d0f0 d0f0 d04a`
- control hits: `1`

The visible-output fixture uses stream:

```text
1b 26 70 32 58 21 21
```

That is `ESC &p2X!!`. The parser trace has one command event:

- handler: `0x11f5a`
- final mode: `0`
- restored handler: `0x12452`
- restored record: `80 58 00 02 00 00`
- raw payload: `21 21`
- routes: `d04a d04a`

The two payload bytes queue as normal printable text:

- first payload byte `0x21`: cursor before `pack12(10)`, compact coord `0x0001`
- second payload byte `0x21`: compact coord `0x0202`
- page-record root allocation count: `1`
- page-record bridge: `0x1edc6` copies the selected context slot
- render entry: the bridged rows match the plain `!!` text fixture

## Reproduction Contract

A byte-stream renderer must not treat transparent data as an opaque binary skip.
For `ESC &p#X`:

- Parse and save the six-byte `X` command record through the shared
  `0x121cc`/`0x12218` delayed-payload mechanism.
- Use the absolute value of record word `+2` as the transparent payload count.
- Consume payload bytes through the same priority byte source as `0xa904`.
- Preserve the local `1a 58 -> 7f` behavior in `0x12452`.
- Route each normalized payload value through `0xd0f0` or `0xd04a` according to
  the control-byte filtering rules above.
- Let printable transparent bytes update cursor, page-record text objects, and
  rendered rows exactly like normal printable host bytes.

## Remaining Edges

- The visible-output fixture covers printable transparent payload bytes. The
  control-byte routing rules are fixture-backed by the isolated `0x12452` model,
  but not yet by a page-record fixture containing C0 or `0x80..0x9f` payload
  bytes.
- The names for the active context filtering byte, fallback byte, and high-byte
  flags remain provisional.
