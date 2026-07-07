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
  - `0x10808 ESC *t#R selects raster mode and scale thresholds`
  - `0x1075a ESC *r#A seeds raster baseline from cursor or left edge`
  - `0x1075a raster origin source follows orientation`
  - `0x107fa ESC *r#B clears raster active flag only`
  - `0x105d0-modeled raster transfer skip and cap gate`
  - `0x11774 ROM dispatch table routes raster stream to delayed transfer`
  - `modeled raster command stream parses ESC *t300R / ESC *r1A /
    ESC *b4W payload boundary`
  - `modeled raster command stream queues and renders ESC *b4W payload`
  - `modeled raster command stream bridges queued ESC *b4W page object`
  - `raster stream ties parser dispatch to queued page object`
  - `host-fetched raster stream reaches parser and queued pixels`
  - `host-fetched raster stream preserves 0x1edc6 bridge contract`
  - `raster payload reader normalizes 0xdace controls before queueing pixels`
  - `modeled raster command stream applies 0x105d0 byte-count cap`
  - `modeled raster command stream queues inclusive page-extent row`
  - `modeled raster command stream drains beyond-extent transfer without
    queueing`
  - `modeled raster command stream drains negative-row transfer and advances`
  - `raster parser trace feeds capped and drained transfer gates`
  - `raster mode streams tie ROM parser dispatch to modeled queued objects`
  - `host-fetched raster mode streams reach parser and rendered rows`
  - `host-fetched raster mode streams feed 0x1ed84 and 0x1ef6a`
  - `modeled raster command stream selects 150-dpi mode-1 state`
  - `modeled raster command stream queues and renders 150-dpi mode-1 payload`
  - `modeled raster command stream selects 100-dpi mode-2 state`
  - `modeled raster command stream queues and renders 100-dpi mode-2 payload`
  - `modeled raster command stream selects 75-dpi mode-3 state`
  - `modeled raster command stream queues and renders 75-dpi mode-3 payload`
  - `modeled raster command stream queues consecutive ESC *b#W rows`
  - `modeled raster command stream renders consecutive queued rows`
  - `modeled raster command stream parses ESC *rB and re-enables resolution
    changes`
  - `modeled raster command stream accepts lowercase same-group resolution
    chaining`
  - `modeled raster command stream defers lowercase ESC *b w payload until
    uppercase terminator`
  - `host-fetched raster multi-row and chained streams preserve 0x1edc6 bridge
    contract`
  - `host-fetched raster streams feed 0x1ed84 and 0x1ef6a`
  - `raster end parser trace feeds active-clear and resolution re-enable`
  - `host-fetched raster end stream clears active state and re-enables
    resolution`
  - `raster active resolution parser trace preserves current mode`
  - `host-fetched active raster resolution stream preserves current mode`
  - `host-fetched raster gate stream reaches capped and drained paths`
  - `host-fetched text rectangle and raster page record feeds 0x1ed84 and
    0x1ef6a`
  - `host-fetched text rectangle raster FF publishes rendered page record`
  - `addressed text rectangle raster FF publishes rendered page record`
  - `addressed text/rule/raster field groups reach publication and render
    entry`
  - `0x13070/0x13250 raster row queues encoded-span object`
  - `0x1f88e mode-0 raster object renders queued literal row`
  - `0x13070/0x13250 raster row queues non-byte-aligned encoded-span object`
  - `0x1f88e mode-0 raster object renders sub-byte shifted literal row`
  - `0x13070/0x13250 raster mode-1 row queues encoded-span object`
  - `0x1f88e mode-1 raster object expands queued bytes into two rows`
  - `0x13070/0x13250 raster mode-2 row queues encoded-span object`
  - `0x1f88e mode-2 raster object expands queued byte pair into three rows`
  - `0x13070/0x13250 raster mode-2 row queues non-byte-aligned encoded-span
    object`
  - `0x1f88e mode-2 raster object renders sub-byte shifted expanded rows`
  - `0x13070/0x13250 raster mode-2 row queues band-clipped encoded-span
    object`
  - `0x1f88e mode-2 raster object clips current-band rows and continues in
    fallback buffer`
  - `0x13070/0x13250 raster mode-3 row queues encoded-span object`
  - `0x1f88e mode-3 raster object expands queued bytes into four rows`
  - `addressed text rectangle raster stream matches page-record output`

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
Fixtures `modeled raster command stream parses ESC *t300R / ESC *r1A /
ESC *b4W payload boundary`, `modeled raster command stream queues and renders
ESC *b4W payload`, and `raster stream ties parser dispatch to queued page
object` bind this boundary to the queued object and rendered row for the same
byte stream. `host-fetched raster stream preserves 0x1edc6 bridge contract`
then checks that the object still crosses the page-record-to-render-record
copy before `0x1ef6a` dispatch.

The delayed handoff is now pinned at the instruction level rather than only by
fixture bytes:

- `0x121cc` rewinds `0x78299e` by six, sets pending byte `0x782a1a = 1`,
  stores the handler longword at `0x782a1c`, and copies the six-byte parsed
  command record into `0x782a20..0x782a25`.
- `0x12218` requires pending byte `0x782a1a == 1`, clears it, copies
  `0x782a20..0x782a25` back to the current `0x78299e` record slot, advances
  `0x78299e` by six, and directly calls the saved handler longword when
  `0x782c18 == 0`.
- The direct raster case therefore reaches `0x105d0` through `jsr (A2)` from
  `0x12262`, not through a separate parser table lookup. `0x105d0` immediately
  rewinds `0x78299e` by six again and reads record word `+2` as the transfer
  byte count.

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
- `0x782a1a`: delayed-payload pending byte set by `0x121cc` and cleared by
  `0x12218`.
- `0x782a1c`: saved handler longword; raster transfer stores `0x105d0`.
- `0x782a20..0x782a25`: saved six-byte parsed command record restored before
  the payload handler consumes bytes.

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

Fixture `0x10808 ESC *t#R selects raster mode and scale thresholds` pins the
threshold table at the handler boundary. The lower-resolution parser fixtures
`modeled raster command stream selects 150-dpi mode-1 state`, `modeled raster
command stream selects 100-dpi mode-2 state`, and `modeled raster command
stream selects 75-dpi mode-3 state` check those same handler writes as the
state consumed by later `ESC *b#W` transfers.

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
Fixtures `0x1075a ESC *r#A seeds raster baseline from cursor or left edge` and
`0x1075a raster origin source follows orientation` pin both origin sources and
the left-edge fallback.

`0x107fa` handles `ESC *r#B`. It clears only active byte `0x783182`
(`state+0x12`). It leaves origin, mode, scale, limit, and row state intact.
That is why a following `ESC *t150R` can update resolution after `ESC *rB`,
while an in-raster `ESC *t75R` is ignored.
Fixtures `0x107fa ESC *r#B clears raster active flag only` and `modeled raster
command stream parses ESC *rB and re-enables resolution changes` cover the
clear-and-reenable case.

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
  `0xdace` at `0x1065c..0x10698` and return before the `0x10084`
  ensure-root call. It does not queue or advance the row.
- If the row is in range and byte count is larger than limit `+0x10`, store the
  capped count in `+0x04`, store overflow in `+0x06`, and queue only the capped
  bytes.
- If the row is in range and byte count fits, store the full count in `+0x04`,
  clear `+0x06`, and queue the row.
- If the row is negative, this test occurs after the count stores and after
  `0x10084`: `0x106a4` ensures the root, `0x106ae` writes the row word, and
  `0x106b2..0x106c8` drains the parsed byte count through `0xdace` without
  calling `0x13070`. The later cursor-update path still advances the modeled
  row from `-1` to `0`.

Fixtures `0x105d0-modeled raster transfer skip and cap gate`, `modeled raster
command stream applies 0x105d0 byte-count cap`, `modeled raster command stream
queues inclusive page-extent row`, `modeled raster command stream drains
beyond-extent transfer without queueing`, `modeled raster command stream
drains negative-row transfer and advances`, and `raster parser trace feeds
capped and drained transfer gates` divide these outcomes at the handler
boundary. The writer set is therefore `0x105d0` for `+0x02`, `+0x04`,
`+0x06`, and `+0x12`; the consumers are `0xdace` for discarded bytes,
`0x10084` for page-root availability, and `0x13070` for accepted rows.

For rows that pass the beyond-extent test, `0x105d0` ensures a page root through
`0x10084`, writes current row word `+0x02`, and either drains a negative row or
calls `0x13070` with the raster state block. If `0x13070` reports no room, it
marks the current page root, publishes through `0xff1e`, ensures a fresh root,
and continues.

This removes one ambiguous middle edge: the restored command record is not
passed to `0x105d0` through volatile registers. `0x12218` materializes it back
into the parser-record buffer, and `0x105d0` re-opens that buffer at
`0x105e4..0x105f2`. The live state that crosses into the page object producer
is the raster state block at `0x783170`, the current payload source consumed by
`0xa904` / `0xdace`, and the page-root allocator state rooted at `0x78297a`.

Instruction-level transfer outline:

- `0x105d8..0x10600`: select raster state block `0x783170`, flush text through
  `0xf34a`, rewind `0x78299e` by six bytes, load absolute byte count, and set
  active byte `+0x12`.
- `0x10606..0x10632`: choose the orientation-specific row coordinate source.
  Portrait uses `0x782c8e`; landscape derives it from `0x782c8a` and
  `0x782db2` through helper `0x10510`.
- `0x10634..0x10658`: add scale `+0x0e` through `0x10518` and compare against
  `(0x782db2 + 1) << 16`.
- `0x10670..0x106a0`: store accepted count `+0x04` and overflow `+0x06`
  before the root allocation boundary.
- `0x106a4..0x106cc`: ensure root, store row word `+0x02`, skip negative rows,
  or call `0x13070`.
- `0x106d2..0x106f2`: on `0x13070` no-room return, mark current root
  `+0x15.0`, publish through `0xff1e`, and ensure a fresh root.
- `0x106f8..0x10752`: update portrait or landscape cursor state unless the
  transfer failed with `D5 = -1`.

Register and memory handoff across the producer boundary:

- `0x105d8..0x105f2`: `A4` is raster state block `0x783170`; `A5` is the
  restored parser record at `0x78299e - 6`; `D5` is the absolute byte count
  from record word `+2`; and `0x78299e` is rewound to that restored record.
- `0x10606..0x10658`: `D4` is the long row coordinate. Portrait reads
  vertical cursor `0x782c8e`; landscape derives the row from horizontal
  cursor `0x782c8a`, page width `0x782db2 << 16`, and helper `0x10510`.
  Helper `0x10518` applies raster scale `+0x0e` before the page-extent
  comparison.
- `0x10670..0x106a0`: accepted count `+0x04` and overflow count `+0x06` are
  committed before any page-root mutation.
- `0x106a4..0x106cc`: `0x10084` is called only after the beyond-extent gate.
  The row word stored at state `+0x02` is `D4 >> 16`; negative rows drain
  payload through `0xdace` and skip `0x13070`; nonnegative rows pass `A4` as
  the sole `0x13070` argument.
- `0x10084..0x1010e`: an existing `0x78297a` root returns unchanged. A missing
  root optionally publishes/services through `0x9ac2`, allocates through
  `0x9a9a`, marks root byte `+0x04 = 1`, clears `0x782a70`, seeds
  `0x782a72 = root + 0x20`, stores `0x78297a`, calls `0x10110`, clears
  `0x782990`, and zeroes 256 bucket heads through the pointer at root
  `+0x1c`.
- `0x10110..0x10218`: root initialization clears publication/retry fields,
  caches geometry words, clears 16 context slots and their byte flags, and
  copies the selected-font context from `0x782ee6 + 16 * byte(0x782f06)` into
  root slot `+0x2c`.
- `0x13070..0x1313c`: `0x13070` consumes the same state pointer. State `+0x02`
  selects bucket `0x782a7c = row >> 4`; state `+0x00` plus page x-offset
  `0x782dc0` and row low bits form packed key `0x782a7e`; state `+0x04` is
  rounded up if odd, then size `accepted + 0x0a` and mode state `+0x08` are
  passed to `0x13250`.
- `0x13250..0x132ae`: `0x13250` calls allocator helper `0x132b6`, links the
  returned object into page-root bucket array `root+0x1c[0x782a7c]`, writes
  class byte `+0x04 = 0x80`, copies the mode byte to `+0x05`, and returns the
  object pointer in `D7`.
- `0x13146..0x13220`: after allocation, `0x13070` writes object `+0x06` from
  `0x782a80`, writes object `+0x08` from `0x782a7e`, calls `0x138de`, then
  loops for remaining bytes unless `0x782996 == 1` or `0x138de` returns `-1`.
- `0x1317e..0x1324e`: zero-length, no-room, or copy-stop exits drain the
  remaining transfer through `0x12328` using state words `+0x04 + +0x06`.

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

The row-object fixtures extend this layout beyond the primary byte-aligned
mode-0 row. `0x13070/0x13250 raster row queues non-byte-aligned encoded-span
object` checks that the packed coordinate and payload capacity still describe a
shifted row. `0x13070/0x13250 raster mode-1 row queues encoded-span object`,
`0x13070/0x13250 raster mode-2 row queues encoded-span object`, and
`0x13070/0x13250 raster mode-3 row queues encoded-span object` check that
object byte `+0x05` carries the encoded mode selected earlier by `0x10808`.
The mode-2 clipped fixture,
`0x13070/0x13250 raster mode-2 row queues band-clipped encoded-span object`,
keeps the same object contract while the renderer clips destination rows.

### Allocation Capacity And Dense Rows

`0x13250` delegates byte storage to `0x132b6`, so dense raster rows can be
split by stream-chunk capacity before `0x138de` copies payload bytes:

- `0x132be..0x13320`: if the requested object size fits in remaining stream
  bytes `0x782a70`, `0x132b6` stores payload capacity
  `requested_size - 0x0a` in `0x782a80`, advances next-free pointer
  `0x782a76`, and subtracts from `0x782a70`.
- `0x132ce..0x132fc`: if the request does not fit but at least `12` bytes
  remain, the helper uses the current chunk tail. It stores capacity
  `0x782a70 - 0x0a` in `0x782a80`, clears `0x782a70`, and returns the
  current `0x782a76` without allocating a fresh chunk.
- `0x13328..0x13382`: if fewer than `12` bytes remain, the helper allocates a
  new `0x100`-byte chunk through `0x1710`, links it through `0x782a72`, seeds
  `0x782a76 = chunk + 4`, and then either allocates the requested object from
  the fresh chunk or, for requests above `0xfc`, returns a capped object with
  capacity `0x00f2` and clears remaining space.

After allocation, `0x13070` writes object word `+0x06` from `0x782a80`, writes
object word `+0x08` from `0x782a7e`, and calls `0x138de` with copy count
`min(accepted_count, 0x782a80)`. If bytes remain, `0x1319e..0x131d0`
subtracts the copied capacity from raster state `+0x04`, advances the packed
key by `0x332ee(0x782a80, mode + 1)`, and loops back to allocate the next
encoded-span object. The zero-length, no-room, and copy-stop exits at
`0x1317e..0x1324e` drain the remaining accepted plus overflow byte counts
through `0x12328`.

Field grouping for this dense-row split:

- canonical: one or more encoded raster objects under page-root `+0x1c`, each
  with class byte `0x80`, mode byte `+0x05`, capacity word `+0x06`, packed key
  `+0x08`, and copied payload bytes at `+0x0a`;
- derived/cache: `0x782a7c`, `0x782a7e`, and `0x782a80`, which choose bucket,
  packed coordinate, and per-object payload capacity;
- parser scratch: the restored delayed `ESC *b#W` record and current payload
  source consumed through `0xa904` / `0x138de` or drained through `0x12328`;
- firmware bookkeeping: stream allocator state `0x782a70`, `0x782a72`, and
  `0x782a76`, plus copy-stop/publication flag `0x782996`;
- unknown: no instruction-level split branch remains unlocated at `0x132b6`.
  Capped-new-chunk and current-tail object-chain derivations are documented
  below. Remaining dense-row work starts from byte streams that change accepted
  count or drain result, allocator pre-state `0x782a70/0x782a72/0x782a76`,
  split capacity `0x782a80`, copy-stop byte `0x782996`, packed-key advance
  through `0x332ee`, bridge bucket roots, or mode-specific `0x1f88e` row
  construction.

### Dense-Row Split Composition Checkpoint

This checkpoint is the semantic contract for a raster row that is too large
for one stream object. It is separate from the `0x1f88e` bitmap renderer: the
split happens while building page-record bucket objects, before publication
and before render scheduling.

Writers and branch boundaries:

- `0x105d0` writes accepted byte count `+0x04`, overflow count `+0x06`, row
  word `+0x02`, and active byte `+0x12` in raster state block `0x783170`.
  These fields decide whether `0x13070` is called at all.
- `0x13070..0x13136` computes bucket index `0x782a7c`, packed key
  `0x782a7e`, odd-byte rounding, requested object size `accepted + 0x0a`, and
  mode argument from raster state `+0x08` before calling `0x13250`.
- `0x13250..0x132ae` links each returned object at the head of the selected
  page-root `+0x1c` bucket chain, writes class byte `+0x04 = 0x80`, and copies
  the mode byte into object `+0x05`.
- `0x132be..0x13320` is the same-chunk branch: when requested size fits
  remaining stream bytes `0x782a70`, it writes `0x782a80 = size - 0x0a`,
  advances `0x782a76`, subtracts the requested size from `0x782a70`, and
  returns the old free pointer.
- `0x132ce..0x132fc` is the current-tail branch: when the request does not fit
  but at least `12` bytes remain, it writes tail capacity
  `0x782a80 = 0x782a70 - 0x0a`, clears `0x782a70`, and returns the current
  free pointer without allocating a fresh chunk.
- `0x13328..0x13382` is the new-chunk branch: it allocates a `0x100`-byte
  stream chunk through `0x1710`, links it through `0x782a72`, seeds
  `0x782a76 = chunk + 4`, and either falls back to the same-chunk branch or,
  for oversized requests, returns a capped object with
  `0x782a80 = 0x00f2` and no remaining chunk space.
- If allocation fails and `0x132b6` returns zero, `0x13070` does not publish a
  partial encoded object. The caller drains the remaining accepted plus
  overflow count through `0x12328`.

Consumers and output effect:

- `0x13146..0x13220` writes object word `+0x06` from `0x782a80`, writes object
  word `+0x08` from `0x782a7e`, copies up to `0x782a80` bytes through
  `0x138de`, and loops while accepted bytes remain.
- `0x1319e..0x131d0` subtracts the copied capacity from raster state `+0x04`,
  advances the packed key through `0x332ee(0x782a80, mode + 1)`, and returns
  to `0x130ea` to allocate the next encoded object.
- Publication and rendering consume the resulting bucket chain through
  `0xff1e`, `0x1ed84`, `0x1edc6`, `0x1ef6a`, `0x1efc2`, and `0x1f88e`. The
  split therefore changes page-image object topology and bucket traversal
  before the encoded-span renderer sees the row.

Static large-payload walkthrough:

- For a parser-restored mode-0 transfer whose accepted count at raster state
  `+0x04` is `0x012c` bytes and whose current stream chunk has fewer than
  `12` bytes free, `0x13070` asks `0x13250` for object size
  `0x012c + 0x0a = 0x0136`. `0x132b6` allocates a new `0x100`-byte chunk at
  `0x13328..0x1335c`, sees that `0x0136 > 0x00fc` at `0x13364..0x1336a`,
  writes `0x782a80 = 0x00f2`, clears `0x782a70`, and returns the new payload
  cursor.
- `0x13146..0x13220` writes the first encoded object with class `0x80`, mode
  `0`, capacity word `+0x06 = 0x00f2`, packed key from the initial
  `0x782a7e`, and payload bytes `0x0000..0x00f1` from the `ESC *b#W` data.
  `0x1319e..0x131d0` subtracts `0x00f2` from accepted count, advances the
  packed key through `0x332ee(0x00f2, 1)`, and loops with `0x003a` bytes
  remaining.
- The second loop asks for object size `0x003a + 0x0a = 0x0044`. Because the
  previous capped object cleared `0x782a70`, `0x132b6` allocates another
  chunk, takes the same-chunk branch, records `0x782a80 = 0x003a`, advances
  `0x782a76` by `0x0044`, leaves `0x782a70 = 0x00b8`, and copies payload
  bytes `0x00f2..0x012b`.
- Each `0x13250` call inserts its returned object at the head of the selected
  page-root `+0x1c` bucket. For this two-object row, the later `0x003a` object
  is therefore the bucket head and points at the earlier `0x00f2` object. The
  renderer still receives both segments through the normal publication bridge:
  `0xff1e -> 0x1ed84 -> 0x1edc6 -> 0x1ef6a -> 0x1efc2 -> 0x1f88e`.

Static current-tail walkthrough:

- If prior page objects leave `0x782a70 = 0x0014` and a later accepted raster
  count needs object size `0x0028`, `0x132be..0x132cc` rejects the same-chunk
  branch, while `0x132d6..0x132dc` accepts the current-tail branch because
  `0x0014 >= 0x000c`.
- `0x132de..0x132f6` writes `0x782a80 = 0x0014 - 0x0a = 0x000a`, clears
  `0x782a70`, and returns the old `0x782a76`. `0x13070` then emits one
  encoded object for the first ten payload bytes, advances the packed key
  through `0x332ee(0x000a, mode + 1)`, and loops for the remaining accepted
  bytes. The next iteration follows the new-chunk or same-chunk rules above.

Field classification:

- Canonical: raster state `0x783170 +0x02/+0x04/+0x06/+0x08/+0x12`, encoded
  object bytes under page-root `+0x1c`, and the page-root bucket heads that
  preserve those objects until publication.
- Derived/cache: bucket index `0x782a7c`, packed key `0x782a7e`, split
  capacity `0x782a80`, and the render-record bucket root copied by `0x1edc6`.
- Parser scratch: restored delayed `80 57 ...` record, payload cursor, and
  bytes consumed by `0x138de` or drained by `0x12328`.
- Firmware bookkeeping: stream cursors `0x782a70`, `0x782a72`, `0x782a76`,
  allocator return pointer, and publication/copy-stop byte `0x782996`.
- Unknown: no branch target or state field is unknown inside
  `0x13070..0x13382`. The remaining dense-row work is byte streams that change
  accepted count or drain result at `0x105d0`, allocator pre-state
  `0x782a70/0x782a72/0x782a76`, split capacity `0x782a80`, copy-stop byte
  `0x782996`, packed-key advance through `0x332ee`, bridge bucket roots, or
  mode-specific `0x1f88e` row construction beyond the static split cases
  above.

Evidence and confidence:

- Disassembly:
  `generated/disasm/ic30_ic13_raster_object_queue_013070.lst` at
  `0x13070..0x13250` for producer setup, `0x13250..0x132ae` for bucket linking,
  `0x132b6..0x13382` for split allocation, and `0x138de` for payload copy.
- Fixtures:
  `0x13070/0x13250 raster row queues encoded-span object`,
  `0x13070/0x13250 raster row queues non-byte-aligned encoded-span object`,
  the mode-`1` through mode-`3` row-object fixtures, `0x1381c stream allocator
  chunks display-list storage`, and `addressed page-record writers share
  0x1381c across chunk rollover`.
- Confidence is high for the ROM-local split algorithm and object fields
  because the branch boundaries, field writes, and static large-payload
  walkthrough are direct disassembly. Pixel output is documented by tracing the
  ROM render helpers and deriving rows from the queued object bytes; there is
  no external row image to compare against. Broader dense-row documentation
  remains open only where a new byte stream changes accepted count or drain
  result, allocator pre-state, split capacity, copy-stop behavior, packed-key
  advance, bridge bucket root, or `0x1f88e` mode-specific row construction.

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

Fixture `0x1f88e mode-0 raster object renders sub-byte shifted literal row` checks that
mode 0 still uses literal payload bytes when the packed x coordinate is not
byte-aligned. Fixtures `0x1f88e mode-1 raster object expands queued bytes into two
rows`, `0x1f88e mode-2 raster object expands queued byte pair into three rows`, `0x1f88e
mode-2 raster object renders sub-byte shifted expanded rows`, `0x1f88e mode-2 raster
object clips current-band rows and continues in fallback buffer`, and `0x1f88e mode-3
raster object expands queued bytes into four rows` bind each expansion helper to visible
output rows.

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
- unknown: byte-stream variants that change the `0x105d0..0x13250..0x1381c`
  gate result, raster object fields, publication bridge state, or rendered
  rows.

Writers are the parser handlers and page producers listed above, plus `0xff1e`
when fixture `host-fetched text rectangle raster FF publishes rendered page
record` finalizes the heterogeneous page record. Readers are `0x1ed84` /
`0x1edc6`, `0x1ef6a`, `0x1efc2`, raster dispatch `0x1f88e`, compact text
dispatch `0x1effe`, and rule dispatch `0x1f446`. The output effect is one
published text/rule/raster page image using the same ROM-derived row path as
the non-published current-page render for the same byte stream. Fixture
`addressed text rectangle raster stream matches page-record output` records
the addressed storage model and page-record renderer composition.

## Additional Command-Family Coverage

The same raster command/data model is checked beyond the primary 300-dpi
mode-0 stream by fixture scripts that exercise the static interpretation.

Lower-resolution streams check the resolution thresholds through visible rows:

- `ESC *t150R ESC *r0A ESC *b#W` selects encoded mode `1`;
- `ESC *t100R ESC *r0A ESC *b#W` selects encoded mode `2`;
- `ESC *t75R ESC *r0A ESC *b#W` selects encoded mode `3`.

The specific render fixtures are `modeled raster command stream queues and
renders 150-dpi mode-1 payload`, `modeled raster command stream queues and
renders 100-dpi mode-2 payload`, and `modeled raster command stream queues and
renders 75-dpi mode-3 payload`.

Fixtures `raster mode streams tie ROM parser dispatch to modeled queued
objects`, `host-fetched raster mode streams reach parser and rendered rows`,
and `host-fetched raster mode streams feed 0x1ed84 and 0x1ef6a` check each
stream drains from the modeled `0xa904` ring source, routes through
`0x10808`, `0x1075a`, and `0x11f82`, restores the delayed transfer record,
queues the expected encoded object, and renders through the page-record bridge.
Those modes are therefore part of the command-family contract, not separate
untraced raster variants.

Multi-row and chained-transfer fixtures cover repeated use of the same state
block. Fixtures `modeled raster command stream queues consecutive ESC *b#W
rows` and `modeled raster command stream renders consecutive queued rows`
check that two uppercase `ESC *b2W` commands restore independent
`80 57 00 02 00 00` records, consume payloads at offsets `17` and `24`,
advance modeled `row_y` to `2`, and queue objects at coords `0x0000` and
`0x1000`. Fixture `modeled raster command stream accepts lowercase same-group
resolution chaining` covers lowercase same-family command accumulation before
an uppercase final byte. The lowercase stream `ESC *b2w2W` stays in the `*b`
parser family, preserves delayed record `80 77 00 02 00 00`, and consumes
payload only after the uppercase terminator at offset `19`. Fixture `modeled
raster command stream defers lowercase ESC *b w payload until uppercase
terminator` covers that delayed payload boundary. Fixtures
`host-fetched raster multi-row and chained streams preserve 0x1edc6 bridge
contract` and `host-fetched raster streams feed 0x1ed84 and 0x1ef6a` check both
bucket chains survive render-record copying and dispatch through `0x1ef6a`.

The active-state fixtures separate two resolution effects. `ESC *rB` clears
only active byte `+0x12`, so a later `ESC *t150R` can update mode and scale
again. While the active byte is still set, `ESC *t75R` is ignored, and the
following `ESC *b2W` queues a mode-0 object. The fixture checks are
`raster end parser trace feeds active-clear and resolution re-enable`,
`host-fetched raster end stream clears active state and re-enables resolution`,
`raster active resolution parser trace preserves current mode`, and
`host-fetched active raster resolution stream preserves current mode`.

## Reproduction Contract

A byte-stream reproduction must preserve these behaviors:

- `ESC *b#W` is delayed. The command record and payload bytes are separate
  pieces of state until `0x12218` restores the record and calls `0x105d0`.
- Raster resolution commands are ignored while raster active byte `+0x12` is
  set.
- `ESC *r#B` clears only active byte `+0x12`; it does not reset mode, scale,
  origin, or byte limit.
- Lowercase same-family `ESC *b#w` records remain pending until an uppercase
  terminator restores that record and consumes payload bytes.
- Consecutive uppercase `ESC *b#W` commands restore separate records and
  advance the raster row for each queued transfer.
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

- `0x105d0..0x13250`: no unresolved ROM-local raster object layout or dispatch
  edge remains for the covered streams. The parser edge is exact through
  `0x11f82` scheduling, `0x121cc` snapshot layout, `0x12218` restore and
  direct dispatch, and `0x105d0` re-reading the restored six-byte record from
  `0x78299e - 6`.
- The disassembly-derived handoff is documented above with exact boundaries:
  `0x105d8..0x10752`, `0x10084..0x10218`, `0x13070..0x13250`, and
  `0x132b6..0x13382`. That handoff pins the state pointer `A4 = 0x783170`,
  restored parser record `A5 = 0x78299e - 6`, absolute byte count `D5`,
  orientation-derived row longword `D4`, accepted count `+0x04`, overflow
  `+0x06`, stored row `+0x02`, root pointer `0x78297a`, bucket/key fields
  `0x782a7c` / `0x782a7e`, stream allocator fields `0x782a70` /
  `0x782a76` / `0x782a80`, and payload copy through `0x138de`.
- The dense-row split rule through `0x132b6` is documented in `Allocation Capacity And
  Dense Rows`. The composed semantic ledger is in
  [semantic-state-model.md](semantic-state-model.md#raster-transfer-gate-and-encoded-rows).
- Additional work through `0x105d0`, `0x10084`, `0x13070`, `0x13250`, and
  `0x132b6` should target new byte streams that change the raster chain,
  encoded object bytes, allocator state, bridge bucket roots, copy-stop byte
  `0x782996`, packed-key advance, or mode-specific `0x1f88e` rows. Canonical
  output state is documented as the page-root `+0x1c` raster chain and object
  bytes written by `0x13070`/`0x13250`; derived/cache state is the bucket/key and
  render-record copy used by `0x1ed84`/`0x1ef6a`; parser scratch is the delayed
  `80 57 ...` command record, snapshot, payload offset, and drained payload
  bytes; firmware bookkeeping is the modeled allocation result and
  stream-storage cursor.
- `0x13250..0x1381c` addressed storage is documented by the mixed
  text/rule/raster publication fixture. The allocator result is a modeled
  addressed fixture result, which is acceptable for the documented ROM contract
  unless a later byte stream exposes a conflicting allocation or row-output
  behavior.
- Page-image coverage is no longer missing only because the raster fixture is
  isolated: checked-in fixtures now include mixed text/rule/raster publication,
  geometry-changing publication streams, font-selection streams, downloaded
  glyph FF publication, and a parser-driven downloaded-glyph/rule/raster page.
  The remaining page-image gap is new byte-stream variants that expose
  different ROM state, not the
  software-visible raster object layout or render dispatch.
