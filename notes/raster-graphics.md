# Raster Graphics Firmware

This note documents the PCL raster graphics path from parser command records to
queued page objects and encoded-span rendering. It covers the command family:

- `ESC *t#R`: raster resolution
- `ESC *r#A`: start raster graphics
- `ESC *r#B`: end raster graphics
- `ESC *b#W`: transfer raster row bytes

Evidence:

- `generated/disasm/ic30_ic13_raster_handlers_0105d0.lst`
- `generated/disasm/ic30_ic13_raster_object_queue_013070.lst`
- `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`
- `tools/render_fixture_harness.py`, fixtures:
  - `0x11774 ROM dispatch table routes raster stream to delayed transfer`
  - `modeled raster command stream parses ESC *t300R / ESC *r1A / ESC *b4W`
  - `host-fetched raster stream reaches parser and queued pixels`
  - `raster payload reader normalizes 0xdace controls before queueing pixels`
  - `host-fetched raster gate stream reaches capped and drained paths`
  - `host-fetched text rectangle and raster page record feeds 0x1ed84 and
    0x1ef6a`
  - `host-fetched text rectangle raster FF publishes rendered page record`
  - `addressed text rectangle raster FF publishes rendered page record`
  - `addressed text/rule/raster field groups reach publication and render
    entry`
  - `0x13070/0x13250 raster row queues encoded-span object`
  - `0x1f88e mode-0 raster object renders queued literal row`

## Parser Boundary

The primary byte-stream fixture is:

```text
1b 2a 74 33 30 30 52 1b 2a 72 31 41 1b 2a 62 34 57 f0 0f aa 55
```

That is:

```text
ESC *t300R ESC *r1A ESC *b4W f0 0f aa 55
```

The parser loop `0x11774` routes it through:

| Sequence | Record | Handler |
| --- | --- | --- |
| `ESC *t300R` | `80 52 01 2c 00 00` | `0x10808` |
| `ESC *r1A` | `80 41 00 01 00 00` | `0x1075a` |
| `ESC *b4W` | `80 57 00 04 00 00` | `0x11f82` |

`0x11f82` does not consume row bytes immediately. It schedules delayed handler
`0x105d0` through `0x121cc`. The saved snapshot is:

```text
01 00 01 05 d0 80 57 00 04 00 00
```

When parser mode returns to zero, `0x12218` restores the saved record and calls
`0x105d0`. The raw payload begins at byte offset `17` in the fixture stream.

## Raster State Block

Raster handlers use the state block rooted at `0x783170`.

Canonical fields:

- `+0x00`: baseline word copied from `+0x0a`.
- `+0x02`: current row coordinate word used by transfer and queueing.
- `+0x04`: accepted byte count for the current transfer.
- `+0x06`: overflow byte count beyond the accepted transfer count.
- `+0x08`: encoded raster mode, stored as scale minus one.
- `+0x0a`: packed baseline/origin coordinate.
- `+0x0e`: raster scale, stored as `1`, `2`, `3`, or `4`.
- `+0x10`: maximum row byte count after page extent and scale clipping.
- `+0x12`: raster-active flag.

Related canonical page/cursor fields:

- `0x782c8a`: horizontal cursor, used as raster origin in portrait.
- `0x782c8e`: vertical cursor, used as raster origin in landscape.
- `0x782da3`: orientation flag used by the raster transfer cursor update.
- `0x782db4`: active page extent used to compute row byte limit.
- `0x782dc6`: vertical cursor clamp after row transfer.
- `0x78297a`: current page root pointer.

Parser scratch:

- `0x78299e`: command-record cursor rewound by raster handlers.
- `0x782a1a`, `0x782a1c`, `0x782a20..0x782a25`: delayed transfer state for
  `ESC *b#W`.

Derived/cache fields:

- `0x782a7c`: bucket index computed by `0x13070` from row coordinate.
- `0x782a7e`: packed row/x key computed by `0x13070`.
- `0x782a80`: allocation payload capacity selected by `0x132b6`.

## Resolution At 0x10808

`0x10808` handles `ESC *t#R`. If raster active byte `+0x12` is already set,
the handler returns without changing mode, scale, or limit.

When raster is not active, it takes the absolute parsed parameter and maps it:

| Requested value | Scale `+0x0e` | Mode `+0x08` |
| ---: | ---: | ---: |
| `> 150` | `1` | `0` |
| `101..150` | `2` | `1` |
| `76..100` | `3` | `2` |
| `<= 75` | `4` | `3` |

It then computes the row byte limit at `+0x10` from active page extent,
baseline word, and `scale * 8`.

## Start And End Raster

`0x1075a` handles `ESC *r#A`. It rewinds the current command record, reads the
absolute parsed parameter, and initializes the raster state only when active
byte `+0x12` is clear.

Parameter behavior:

- parameter `1`: seed the origin from the active cursor axis;
- any other parameter: clear origin `+0x0a` to the left edge.

The active cursor axis depends on orientation:

- portrait: source `0x782c8a`;
- landscape: source `0x782c8e`.

After origin selection, `0x1075a` copies the origin word to `+0x00` and
computes byte limit `+0x10`.

`0x107fa` handles `ESC *r#B`. It clears only active byte `0x783182`
(`state+0x12`). It leaves origin, mode, scale, limit, and row state intact.
That is why a following `ESC *t150R` can update resolution after `ESC *rB`,
while an in-raster `ESC *t75R` is ignored.

## Transfer Gate At 0x105d0

`0x105d0` is the delayed transfer handler for `ESC *b#W`.

Setup behavior:

1. Flush pending text through `0xf34a`.
2. Rewind `0x78299e` by six.
3. Read the absolute parsed byte count from record `+2`.
4. Set raster active byte `+0x12 = 1`.
5. Compute the transfer row coordinate.
6. Compare the row against the page extent and byte limit.

Gate behavior:

- If the row is beyond the page extent, drain the parsed byte count through
  `0xdace` and return without queueing or advancing the row.
- If the row is negative, drain the parsed byte count through `0xdace`, return
  without queueing, and advance the row from `-1` to `0`.
- If the row is in range and byte count is larger than limit `+0x10`, store the
  capped count in `+0x04`, store overflow in `+0x06`, and queue only the capped
  bytes.
- If the row is in range and byte count fits, store the full count in `+0x04`,
  clear `+0x06`, and queue the row.

For queued rows, `0x105d0` ensures a page root through `0x10084`, writes current
row word `+0x02`, and calls `0x13070` with the raster state block. If `0x13070`
reports no room, it marks the current page root, publishes through `0xff1e`,
ensures a fresh root, and continues.

After a non-`-1` transfer result, `0x105d0` advances cursor state:

- portrait path restores horizontal cursor from raster origin `+0x0a` and adds
  scale `+0x0e` to vertical cursor `0x782c8e`;
- landscape path subtracts scale `+0x0e` from horizontal cursor, clamps it at
  zero, and restores vertical cursor from raster origin `+0x0a`;
- vertical cursor is clamped to `0x782dc6`.

## Payload Copy At 0x138de

`0x13070` calls `0x138de` to copy queued raster bytes into the allocated row
object. This reader calls `0xa904` directly, not `0xdace`, but it implements the
same local `1a 58` control-pair shape for queued bytes:

1. Fetch one byte through `0xa904`.
2. If it is not `0x1a`, copy it.
3. If it is `0x1a`, fetch one more byte through `0xa904`.
4. If the second byte is `0x58`, call `0xd99a` and copy `0x00`.
5. If the second byte is not `0x58`, copy that second byte.

The copied byte count is subtracted from raster state field `+0x04`. If a
negative fetch result occurs, the routine returns `D7 = -1`.

Concrete control-pair fixture:

```text
ESC *t300R ESC *r0A ESC *b4W f0 1a 58 aa 55
```

The raw payload is `f0 1a 58 aa 55`, but the queued payload is
`f0 00 aa 55`.

## Row Object At 0x13070 / 0x13250

`0x13070` converts raster state into a bucket object under page-root `+0x1c`.
`0x13250` allocates and links the object at the head of bucket `0x782a7c`.

Object layout:

| Offset | Meaning |
| ---: | --- |
| `+0x00` | next pointer in bucket chain |
| `+0x04` | class byte, set to `0x80` for encoded raster rows |
| `+0x05` | encoded raster mode byte from state `+0x08` |
| `+0x06` | stored payload capacity, rounded up to an even byte count |
| `+0x08` | packed coordinate/key from `0x782a7e` |
| `+0x0a` | raster payload bytes |

The primary fixture queues this object:

```text
00 00 00 00 80 00 00 04 00 01 f0 0f aa 55
```

Fields:

- next pointer: `0`
- class byte: `0x80`
- mode: `0`
- payload capacity: `4`
- packed coordinate: `0x0001`
- payload: `f0 0f aa 55`

## Render Dispatch

Raster transfer does not draw directly into the final bitmap. It creates a page
record bucket object. The bridge and renderer consume it later:

1. `0x1ed84` calls `0x1edc6`.
2. `0x1edc6` copies source page-root `+0x1c` to render-record `+0x18`.
3. `0x1ef6a` calls `0x1efc2` for the bucket array.
4. `0x1efc2` sees object byte `+4 & 0xc0 == 0x80`.
5. The high-bit class dispatch calls encoded-span writer `0x1f88e`.
6. `0x1f88e` selects an expansion helper from table `0x1f8ca` using
   `object[5] & 0x03`.

Encoded raster modes:

| Mode | Target | Behavior |
| ---: | --- | --- |
| `0` | `0x1f8da` | copy literal payload words |
| `1` | `0x1f8e6` | expand each byte through word table `0x30914` into two rows |
| `2` | `0x1f920` | expand byte pairs through long table `0x30b14` into three rows |
| `3` | `0x1f9c6` | expand each byte through `0x30914` cascaded into four rows |

For the primary mode-0 object above, the rendered row is:

```text
................####........#####.#.#.#..#.#.#.#
```

## Mixed Page-Record Composition

The raster transfer path has now been composed with adjacent page producers
instead of only isolated raster rows. Fixture `host-fetched text rectangle and
raster page record feeds 0x1ed84 and 0x1ef6a` drains this byte stream through
the modeled `0xa904` host source:

```text
21 1b 2a 63 31 32 61 35 62 30 50 1b 2a 74 33 30 30 52
1b 2a 72 30 41 1b 2a 62 32 57 c3 3c
```

That is printable `!`, selector-7 rule command `ESC *c12a5b0P`,
`ESC *t300R`, `ESC *r0A`, and delayed raster transfer
`ESC *b2W c3 3c`. The stream runner queues all three visible producer
classes into one current page record before bridge/render:

- compact text through `0xd04a` / `0x12f2e` / `0x1387c`;
- selector-7 rectangle through `0x10898` / `0x133aa`;
- mode-0 raster through delayed `0x11f82` / `0x12218` / `0x105d0` /
  `0x13070` / `0x13250`.

The addressed publication fixture `addressed text/rule/raster field groups
reach publication and render entry` pins the canonical storage shape for the
same cluster:

- text object at `0x00d0c004`;
- rule object at `0x00d0c02a`;
- raster object at `0x00d0c038`;
- bucket head `page_root+0x1c = 0x00d0c038`;
- rule head `page_root+0x24 = 0x00d0c02a`;
- context slot 0 copied as `0x440946b4`.

Field classes for reproduction:

- canonical fields: the three page-record objects, bucket head, rule head,
  context slot, and raster object bytes
  `00 d0 c0 04 80 00 00 02 00 00 c3 3c`;
- parser scratch: restored raster record `80 57 00 02 00 00`, delayed
  snapshot `01 00 01 05 d0 80 57 00 02 00 00`, payload offset `28`, and
  payload `c3 3c`;
- derived/cache fields: raster bucket/key from `0x782a7c` / `0x782a7e`,
  allocation capacity from `0x782a80`, render band height
  `0x783a20 = 0x0050`, band base `0x783a22 = 0`, and active row origin
  `0x783a28 = 0x00100000`;
- firmware bookkeeping: stream allocator state
  `0x782a70 = 0x00bc`, `0x782a72 = 0x00d0c000`,
  `0x782a76 = 0x00d0c044`, one page-root allocation, one stream
  allocation, one publication, one root clear, and publication flag `1`;
- unknown: the exact live 68000 register/heap-memory trace for this complete
  mixed stream as it crosses `0x105d0..0x13250..0x1381c`.

Writers are the parser handlers and page producers listed above, plus `0xff1e`
when fixture `host-fetched text rectangle raster FF publishes rendered page
record` finalizes the heterogeneous page record. Readers are `0x1ed84` /
`0x1edc6`, `0x1ef6a`, `0x1efc2`, raster dispatch `0x1f88e`, compact text
dispatch `0x1effe`, and rule dispatch `0x1f446`. The output effect is one
published text/rule/raster page image whose rows match the non-published
current-page render for the same byte stream.

## Reproduction Contract

A byte-stream reproduction must preserve these behaviors:

- `ESC *b#W` is delayed. The command record and payload bytes are separate
  pieces of state until `0x12218` restores the record and calls `0x105d0`.
- Raster resolution commands are ignored while raster active byte `+0x12` is
  set.
- `ESC *r#B` clears only active byte `+0x12`; it does not reset mode, scale,
  origin, or byte limit.
- Off-page transfer bytes are still consumed. Beyond-extent rows drain without
  row advance; negative rows drain and advance to row zero.
- Queued payload bytes use the `0x138de` local `1a 58 -> 00` behavior.
- Row objects must be stored under page-root `+0x1c`, not rendered immediately.
- Encoded row object byte `+4 = 0x80` is what sends the renderer through
  `0x1efc2 -> 0x1f88e`.
- Object byte `+5` selects raster expansion mode `0..3`.
- Object word `+8` controls destination x/y packing; object bytes at `+0x0a`
  are the source span payload.

## Remaining Edges

- `0x105d0..0x13250` is modeled and address-aware, but the mixed
  text/rule/raster stream still lacks a full live 68000 execution trace through
  `0x105d0` into allocator memory. The covered parser edge is exact through
  `0x11f82` scheduling, `0x12218` restore, delayed handler `0x105d0`, and the
  modeled calls into `0x10084` and `0x13070`; the uncovered middle edge is the
  live register/memory handoff from the restored command record and payload
  pointer into the page-root allocation and encoded-row producer. Canonical
  output state is already fixture-pinned as the page-root `+0x1c` raster chain
  and object bytes written by `0x13070`/`0x13250`; derived/cache state is the
  bucket/key and render-record copy used by `0x1ed84`/`0x1ef6a`; parser scratch
  is the delayed `80 57 ...` command record, snapshot, payload offset, and
  drained payload bytes; firmware bookkeeping is the modeled allocation result
  and stream-storage cursor. Closing this edge requires a live CPU trace or
  memory snapshot across `0x12218 -> 0x105d0 -> 0x10084 -> 0x13070`, not more
  isolated mode-0 row-render evidence.
- `0x13250..0x1381c` addressed storage is documented by the mixed
  text/rule/raster publication fixture, but the heap allocator result is still
  a modeled fixture result rather than a memory snapshot from one live parser
  run.
- Page-image coverage is no longer missing only because the raster fixture is
  isolated: checked-in fixtures now include mixed text/rule/raster publication,
  geometry-changing publication streams, font-selection streams, downloaded
  glyph FF publication, and a parser-driven downloaded-glyph/rule/raster page.
  The remaining page-image gap is broader physical/device comparison and live
  CPU continuity, not the software-visible raster object layout or render
  dispatch.
