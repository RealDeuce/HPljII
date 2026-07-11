# Raster Graphics Firmware

This note documents the PCL raster graphics path from parser command records to
queued page objects and encoded-span rendering. It covers the command family:

- `ESC *t#R`: raster resolution
- `ESC *r#A`: start raster graphics
- `ESC *r#B`: end raster graphics
- `ESC *b#W`: transfer raster row bytes

Evidence:

- `generated/analysis/ic30_ic13_pcl_command_map.md`
- `generated/disasm/ic30_ic13_payload_dispatch_011f82.lst`
- `generated/disasm/ic30_ic13_parser_setup_handlers_011ea4.lst`
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

## Owner Summary

This note owns the `ESC *t`, `ESC *r`, and `ESC *b` path from parsed command
records to encoded raster page objects. It does not own parser table matching
before `0x11f82`, nor the shared render scheduler after a published record has
entered `0x1ef6a`; those boundaries are linked below.

The route for accepted raster rows is:

- `0x10808` handles `ESC *t#R` and writes raster scale/mode state when raster
  active byte `0x783182` is clear.
- `0x1075a` handles `ESC *r#A`, sets active byte `0x783182`, seeds origin and
  baseline fields, and recomputes the row byte limit.
- `0x11f82 -> 0x121cc -> 0x12218` delays `ESC *b#W` until the payload phase
  and restores the six-byte transfer record.
- `0x105d0` gates the transfer, drains skipped payload bytes, writes transfer
  counts in the `0x783170` block, ensures a current page root through
  `0x10084`, and calls `0x13070` for accepted rows.
- `0x13070 -> 0x13250 -> 0x138de` computes the bucket/key, allocates one or
  more encoded raster objects under page-root `+0x1c`, and copies payload
  bytes into object `+0x0a..`.
- `0xff1e -> 0x1ed84 -> 0x1edc6 -> 0x1ef6a -> 0x1efc2 -> 0x1f88e` publishes,
  bridges, dispatches, and renders the encoded objects.

Concrete route for the primary supported stream:

- `ESC *t300R ESC *r1A ESC *b4W f0 0f aa 55` enters parser loop `0x11774`,
  calls `0x10808`, `0x1075a`, and delayed setup handler `0x11f82`, then
  restores transfer record `80 57 00 04 00 00` through `0x12218`.
- `0x10808` stores scale `1` and encoded mode `0`; `0x1075a` starts raster
  state and seeds the origin from the active cursor axis; `0x105d0` accepts
  four row bytes and calls `0x13070`.
- `0x13070 -> 0x13250 -> 0x138de` writes encoded object
  `00 00 00 00 80 00 00 04 00 01 f0 0f aa 55` under page-root `+0x1c`.
  Class byte `+0x04 = 0x80` selects encoded-raster dispatch, mode byte
  `+0x05 = 0` selects literal mode, count `+0x06 = 4` records the copied
  payload capacity, and key `+0x08 = 0x0001` supplies the packed destination.
- Publication and bridge copy the bucket root to render-record `+0x18`; render
  entry `0x1ef6a -> 0x1efc2 -> 0x1f88e` consumes object byte `+0x05 & 3` and
  dispatches literal mode through helper `0x1f8da`.

Writers:

- `0x10808` writes raster block `+0x08`, `+0x0e`, and `+0x10` from the parsed
  resolution and page extent.
- `0x1075a` writes active byte `+0x12`, origin/baseline fields `+0x0a` and
  `+0x00`, and limit `+0x10`; `0x107fa` clears only active byte `+0x12`.
- `0x11f82` schedules delayed transfer handler `0x105d0` through
  `0x121cc`; `0x12218` restores the saved command record before payload
  consumption.
- Alternate/data table rows suppress ordinary raster state writers:
  `ESC *t#R`, `ESC *r#A`, and `ESC *r#B` uppercase finals have no handler in
  table `0x116f6`, while lowercase `r`, `a`, and `b` finals route only to
  rewind helper `0x11f4c`. `ESC *b#W/w` is the exception because the counted
  payload must remain representable in stored data; it still reaches
  `0x11f82`, but delayed restore `0x12218` sees alternate/data flag
  `0x782c18` and calls `0x12358` instead of saved handler `0x105d0`.
- `0x105d0` writes current row `+0x02`, accepted count `+0x04`, overflow/drain
  count `+0x06`, and retry/publication state when `0x13070` reports no room.
- `0x13070` writes derived bucket index `0x782a7c`, packed key `0x782a7e`, and
  object words `+0x06/+0x08`; `0x13250` links object class `0x80..0xff`;
  `0x138de` writes copied payload bytes.

Readers and consumers:

- `0x105d0` consumes restored command record word `+2`, active raster state
  `0x783170`, page extent/clamp fields `0x782db4` and `0x782dc6`, current root
  `0x78297a`, and payload bytes through `0xdace` for drains.
- `0x138de` consumes accepted payload bytes through direct `0xa904` reads with
  local `0x1a 0x58` handling before storing object payload bytes.
- `0xff1e`, `0x1ed84`, and `0x1edc6` consume the page-root bucket chain and
  copy it into render root `+0x18`.
- `0x1efc2` routes high-bit bucket objects to `0x1f88e`; `0x1f88e` consumes
  object byte `+0x05 & 3`, payload count `+0x06`, packed key `+0x08`, and
  payload bytes `+0x0a..`.

Output effect:

- Resolution and start/end commands are state-only until a later transfer uses
  them. `ESC *r#B` clears active state and re-enables later `ESC *t#R` changes.
- Accepted `ESC *b#W` rows create encoded raster objects under page-root
  `+0x1c`. Beyond-extent and negative-row transfers consume payload through
  `0xdace` but skip `0x13070`, so they produce no page object.
- Encoded raster pixels come from object fields plus `0x1f88e` helper choice:
  mode `0` renders literal rows, mode `1` expands bytes into two rows, mode
  `2` expands byte pairs into three rows and can split into fallback storage,
  and mode `3` expands bytes into four rows.

Field classification:

- Canonical raster state: block `0x783170`, including baseline `+0x00`, row
  `+0x02`, accepted count `+0x04`, overflow/drain count `+0x06`, encoded mode
  `+0x08`, origin `+0x0a`, scale `+0x0e`, row byte limit `+0x10`, and active
  byte `+0x12`.
- Canonical page/image state: current root `0x78297a`, bucket root `+0x1c`,
  encoded object class byte `+0x04`, mode byte `+0x05`, count `+0x06`, key
  `+0x08`, and payload bytes `+0x0a..`.
- Derived/cache state: bucket index `0x782a7c`, packed key `0x782a7e`,
  allocation capacity `0x782a80`, copied render root `+0x18`, band caches
  `0x783a20/0x783a22/0x783a28`, destination stride `0x783a1c`, and fallback
  storage rooted at `0x7810b4`.
- Parser scratch: delayed payload byte `0x782a1a`, saved handler
  `0x782a1c`, saved record `0x782a20..0x782a25`, restored command-record
  cursor `0x78299e`, and the live `ESC *b#W` record until `0x105d0` reads it.
  Alternate/data raster-control and resolution records that end at blank
  terminal rows or `0x11f4c` are parser scratch only; alternate/data
  `ESC *b#W/w` payload records are restored only far enough for `0x12358`,
  `0xdace`, `0xe002`, or wrapper drain `0x1228a -> 0x12328` to drain or
  append bytes without calling `0x105d0`.
- Firmware bookkeeping: allocator state `0x782a70/0x782a72/0x782a76`, copy-stop
  flag `0x782996`, root retry flag `+0x15.0`, and chunk allocator behavior in
  `0x132b6..0x13382`.
- Hardware/external state: none inside this command-family edge after payload
  bytes have been admitted by `0xa904` / `0xdace`; physical engine consumption
  begins after shared render buffers are written.
- Unknown: no ROM-local middle edge remains for the documented `ESC *t#R`,
  `ESC *r#A/#B`, accepted row, drain, dense split, and modes `0..3` render
  paths. Future work starts only from byte streams that change a concrete
  transfer gate, allocator split, object field, payload-copy stop, packed-key
  advance, or `0x1f88e` helper input named here.

Evidence is the sections below, [pcl-command-map.md](pcl-command-map.md),
[page-raster-imaging.md](page-raster-imaging.md), and
[semantic-state-model.md](semantic-state-model.md), with disassembly listings
`generated/disasm/ic30_ic13_raster_handlers_0105d0.lst`,
`generated/disasm/ic30_ic13_raster_object_queue_013070.lst`, and
`generated/disasm/ic30_ic13_bitmap_encoded_span_modes_01f88e.lst`. The primary
stream example is `ESC *t300R ESC *r1A ESC *b4W f0 0f aa 55`, which queues the
encoded object `00 00 00 00 80 00 00 04 00 01 f0 0f aa 55` and renders through
mode-0 `0x1f88e`.

## Raster Transfer Decision Checkpoint

This checkpoint composes the raster command family as transfer decisions. It
starts after parser dispatch has selected `ESC *t`, `ESC *r`, or delayed
`ESC *b#W`, and ends either with raster state mutation, encoded page objects,
drained payload bytes, or rendered encoded-span rows after publication.

Decision rules:

- Resolution command `ESC *t#R` reaches `0x10808`. If raster active byte
  `0x783182` is clear, it writes scale `+0x0e`, encoded mode `+0x08`, and row
  byte limit `+0x10` in raster block `0x783170`. If raster is already active,
  it exits without changing existing raster mode or limits.
- Start command `ESC *r#A` reaches `0x1075a`. If raster is inactive, it sets
  active byte `+0x12`, seeds origin `+0x0a` from the active cursor axis for
  selector `1` or the left edge for other selectors, copies baseline `+0x00`,
  and recomputes byte limit `+0x10`. If raster is already active, it exits
  before origin or limit writes.
- End command `ESC *r#B` reaches `0x107fa` and clears only active byte
  `0x783182`. Existing origin, baseline, mode, scale, row, and limit fields
  remain available until a later start/resolution/reset path rewrites them.
- Transfer command `ESC *b#W` reaches `0x11f82`, which schedules delayed
  handler `0x105d0` through `0x121cc`. `0x12218` later restores the saved
  six-byte record and calls `0x105d0`; the payload bytes are not consumed at
  parser-table dispatch time.
- Alternate/data raster boundary:
  with alternate/data flag `0x782c18` set, `ESC *t#R`, `ESC *r#A`, and
  `ESC *r#B` do not reach `0x10808`, `0x1075a`, or `0x107fa`.
  Uppercase terminal rows are blank in table `0x116f6`; lowercase chaining
  finals route only to `0x11f4c`, which subtracts one six-byte command record
  from `0x78299e` and returns. No raster block fields, current page root,
  bucket objects, publication state, or render inputs change.
- Alternate/data raster payload boundary:
  `ESC *b#W/w` still arms `0x11f82 -> 0x121cc`, but restore
  `0x12218..0x12274` tests `0x782c18` before calling the saved handler. In
  alternate/data mode it calls `0x12358`; if the saved handler matches wrapper
  `0x1228a`, that wrapper drains the absolute payload count through
  `0x12328`, otherwise positive counts are drained through `0xdace` and
  appended through `0xe002`. In either case `0x105d0`, `0x13070`,
  `0x13250`, and `0x138de` are not called, so no encoded raster row exists
  until stored bytes later replay through the normal parser route.
- `0x105d0` first flushes pending text spans, rewinds the restored record,
  reads absolute byte count, sets raster active byte `+0x12`, and derives the
  orientation-specific row coordinate.
- Beyond-extent transfers drain positive payload bytes through `0xdace` and
  return before current-root allocation. They create no page object and do not
  advance row state.
- In-range transfers store accepted count `+0x04` and overflow/drain count
  `+0x06`. If the raw count exceeds row byte limit `+0x10`, only the capped
  accepted bytes can become object payload; the overflow is drained later.
- Negative-row transfers ensure a root and write row word `+0x02`, but skip
  `0x13070`. They drain payload through `0xdace`; if the drain completes, the
  later cursor-update path advances the modeled row toward zero.
- Accepted nonnegative rows call `0x13070`. `0x13070 -> 0x13250 -> 0x138de`
  writes one or more encoded raster objects under page-root `+0x1c`; dense
  rows split by stream allocator capacity before publication.
- The render outcome is selected later from object byte `+0x05 & 3` through
  `0x1f88e`: mode `0` renders literal rows, mode `1` expands bytes into two
  rows, mode `2` expands byte pairs into three rows and can split into
  fallback storage, and mode `3` expands bytes into four rows.

State classification:

- Canonical raster state: block `0x783170`, including baseline `+0x00`, row
  `+0x02`, accepted count `+0x04`, overflow/drain count `+0x06`, encoded mode
  `+0x08`, origin `+0x0a`, scale `+0x0e`, row byte limit `+0x10`, and active
  byte `+0x12`.
- Canonical page/image state: current root `0x78297a`, bucket root `+0x1c`,
  encoded object class byte `+0x04 = 0x80`, mode byte `+0x05`, count `+0x06`,
  packed key `+0x08`, payload bytes `+0x0a..`, and published/bridged bucket
  roots.
- Derived/cache state: bucket index `0x782a7c`, packed key `0x782a7e`,
  allocation capacity `0x782a80`, packed-key advance through `0x332ee`,
  render-record bucket root `+0x18`, band caches, destination stride
  `0x783a1c`, and fallback storage `0x7810b4`.
- Parser scratch: delayed-payload byte `0x782a1a`, saved handler
  `0x782a1c`, saved record `0x782a20..0x782a25`, restored command-record
  cursor `0x78299e`, and payload bytes consumed by `0x138de`, `0xdace`, or
  `0x12328`.
  Alternate/data `ESC *t` and `ESC *r` records remain scratch-only when their
  terminal rows are blank or lowercase `0x11f4c`; alternate/data `ESC *b`
  records remain delayed-payload scratch unless replay later returns them to
  normal parser mode.
- Firmware bookkeeping: allocator cursors `0x782a70`, `0x782a72`, and
  `0x782a76`, copy-stop/publication byte `0x782996`, root retry flag
  `+0x15.0`, and no-room publication/retry state.
- Hardware/external state: none for the ROM-local raster command and render
  decisions after payload bytes have been admitted through `0xa904` /
  `0xdace`.
- Unknown: new raster work belongs here only when a byte stream changes the
  transfer gate, accepted/drained counts, allocator split, object bytes,
  bridge bucket roots, copy-stop behavior, packed-key advance, or `0x1f88e`
  mode-specific row construction.

Evidence:

- Disassembly:
  `generated/disasm/ic30_ic13_raster_handlers_0105d0.lst`,
  `generated/disasm/ic30_ic13_raster_object_queue_013070.lst`,
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`, and
  `generated/disasm/ic30_ic13_bitmap_encoded_span_modes_01f88e.lst`.
- Evidence streams include `0x10808 ESC *t#R selects raster mode and scale
  thresholds`, `0x1075a ESC *r#A seeds raster baseline from cursor or left
  edge`, `0x107fa ESC *r#B clears raster active flag only`,
  `raster parser trace feeds capped and drained transfer gates`,
  `modeled raster command stream queues and renders ESC *b4W payload`,
  `modeled raster command stream queues consecutive ESC *b#W rows`, and the
  `0x1f88e mode-0` through `0x1f88e mode-3` render fixtures named above.

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
`0x105d0`. The raw payload begins at byte offset `17` in the evidence stream.
Evidence streams `modeled raster command stream parses ESC *t300R / ESC *r1A /
ESC *b4W payload boundary`, `modeled raster command stream queues and renders
ESC *b4W payload`, and `raster stream ties parser dispatch to queued page
object` bind this boundary to the queued object and rendered row for the same
byte stream. `host-fetched raster stream preserves 0x1edc6 bridge contract`
then checks that the object still crosses the page-record-to-render-record
copy before `0x1ef6a` dispatch.

The delayed handoff is instruction-level ROM behavior, not a fixture-only
assertion:

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

Instruction boundary:

- `0x10808..0x1083a` rewinds `0x78299e`, exits without changes when raster
  active byte `+0x12` is set, and otherwise reads the absolute parsed
  resolution from record word `+2`.
- `0x10842..0x10868` maps the requested resolution to scale values
  `1`, `2`, `3`, or `4` using thresholds `150`, `100`, and `75`.
- `0x10868..0x10896` writes scale `+0x0e`, recomputes row byte limit `+0x10`
  from page extent `0x782db4`, baseline word `+0x00`, and `scale * 8`, then
  writes encoded mode byte `+0x08 = scale - 1`.

Evidence stream `0x10808 ESC *t#R selects raster mode and scale thresholds`
records the threshold table at the handler boundary. The lower-resolution
parser evidence streams
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
Evidence streams `0x1075a ESC *r#A seeds raster baseline from cursor or left
edge` and `0x1075a raster origin source follows orientation` record both
origin sources and the left-edge fallback.

Instruction boundary:

- `0x1075a..0x1078a` rewinds the parser record, takes the absolute parsed
  selector, exits if raster active byte `+0x12` is already set, and otherwise
  sets active byte `+0x12 = 1`.
- `0x10790..0x107b6` handles origin selection. Selector `1` copies the active
  cursor axis into origin `+0x0a`: portrait uses horizontal cursor
  `0x782c8a`, while landscape uses vertical cursor `0x782c8e`. Other selectors
  clear origin `+0x0a`.
- `0x107b6..0x107ee` copies origin word `+0x0a` to baseline word `+0x00` and
  recomputes row byte limit `+0x10` from page extent `0x782db4`, baseline, and
  encoded scale `+0x08`.
- `0x107fa..0x10806` is the raster-end handler. It clears only active byte
  `0x783182` and leaves origin, baseline, scale, mode, byte limit, and row
  fields unchanged.

The active-start exit is an ignored-command boundary, not a second
initialization path. If `ESC *r#A` reaches `0x1075a` while active byte
`0x783182` is nonzero, `0x10784..0x107aa` returns before selector testing,
origin writes, baseline copy, or row-limit recomputation. A byte-stream
renderer must therefore keep existing raster fields `+0x00`, `+0x08`,
`+0x0a`, `+0x0e`, and `+0x10`; only a prior `ESC *r#B` or reset/default path
can reopen those start/resolution writes.

`0x107fa` handles `ESC *r#B`. It clears only active byte `0x783182`
(`state+0x12`). It leaves origin, mode, scale, limit, and row state intact.
That is why a following `ESC *t150R` can update resolution after `ESC *rB`,
while an in-raster `ESC *t75R` is ignored.
Evidence streams `0x107fa ESC *r#B clears raster active flag only` and
`modeled raster command stream parses ESC *rB and re-enables resolution
changes` cover the clear-and-reenable case.

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

- If the row is beyond the page extent, `0x1065c..0x10698` drains only while
  the remaining parsed byte count in `D5` is positive. `D5 <= 0` returns
  immediately, and a `0xdace` `-1` return exits early. This path returns
  before the `0x10084` ensure-root call, so it does not allocate a root, queue
  an object, or advance the row.
- If the row is in range and byte count is larger than limit `+0x10`, store the
  capped count in `+0x04`, store overflow in `+0x06`, and queue only the capped
  bytes.
- If the row is in range and byte count fits, store the full count in `+0x04`,
  clear `+0x06`, and queue the row.
- If the row is negative, this test occurs after the count stores and after
  `0x10084`: `0x106a4` ensures the root, `0x106ae` writes the row word, and
  `0x106b6..0x106f6` drains while remaining count `D5` is positive, without
  calling `0x13070`. A `0xdace` `-1` return exits before cursor update;
  otherwise the later cursor-update path advances the modeled row from `-1`
  to `0`.

Branch-outcome ledger:

- `0x1065c..0x10698`, beyond extent:
  consumes discarded payload through `0xdace` only while `D5 > 0`; returns
  before `0x10084`, so it writes no current-root state, queues no object, and
  does not run the cursor-update block at `0x106f8..0x10752`.
- `0x10670..0x1068e`, in range with raw count above limit:
  writes accepted count `+0x04 = +0x10`, writes overflow `+0x06 = raw -
  limit`, then continues through `0x10084` and queues only accepted bytes.
  The overflow bytes are drained by `0x13070` through `0x12328` after object
  copy or copy-stop.
- `0x1069c..0x106a0`, in range with raw count within limit:
  writes accepted count `+0x04 = raw`, clears overflow `+0x06`, then
  continues through the same root/object path as the capped case.
- `0x106a4..0x106c8`, negative row:
  ensures a root and writes row word `+0x02`, but branches around `0x13070`.
  It drains positive payload through `0xdace`; unless the drain returns `-1`,
  the cursor-update block still advances the modeled raster position.
- `0x106ca..0x106d2`, accepted nonnegative row:
  passes `A4 = 0x783170` to `0x13070`. The page object boundary is therefore
  the raster state block plus the live payload source, not the parser command
  record.
- `0x106d2..0x106f2`, object allocation failure:
  treats `D7 == 0` from `0x13070` as no room, marks current root byte
  `+0x15.0`, publishes through `0xff1e`, ensures a fresh root through
  `0x10084`, and leaves transfer completion to the following shared exit
  block.
- `0x106f8..0x10752`, successful or drained transfer exit:
  skips only when transfer state is `D5 = -1`. Portrait restores horizontal
  cursor from origin `+0x0a` and advances vertical cursor by scale `+0x0e`;
  landscape subtracts scale from horizontal cursor, clamps it at zero, and
  restores vertical cursor from origin `+0x0a`. Both orientations clamp final
  vertical cursor against `0x782dc6`.

### Transfer Gate Outcome Matrix

This matrix is the owner-level routing table for new raster-transfer streams.
A new `ESC *b#W` trace belongs here only when it changes one of these
predicates, field writes, payload outcomes, object outcomes, cursor outcomes,
or downstream consumers.

- Beyond page extent:
  predicate is the coordinate comparison at `0x10634..0x10658` producing
  `D7 > ((0x782db2 + 1) << 16)`. Handler range `0x1065c..0x10698` drains
  only positive remaining count `D5` through `0xdace`; `D5 <= 0` or
  `0xdace == -1` returns immediately. Canonical raster fields `+0x02`,
  `+0x04`, and `+0x06` are not written, no page root is ensured, no
  page-object byte is produced, and cursor state is not advanced. The first
  downstream consumer is only the next parser byte after the drain or early
  return.
- In-range capped transfer:
  predicate is raw count `D5` greater than row byte limit `+0x10`. Handler
  range `0x10670..0x1068e` writes accepted count `+0x04 = +0x10` and overflow
  count `+0x06 = raw - +0x10`; `0x106a4..0x106cc` ensures root `0x78297a`,
  writes row word `+0x02`, and calls `0x13070`. The queued object uses class
  byte `+0x04 = 0x80`, mode byte from raster state `+0x08`, count word
  `+0x06 = accepted`, packed key `+0x08`, and accepted payload bytes
  `+0x0a..`; overflow bytes are drained by the `0x13070` exit through
  `0x12328`. Later consumers are publication `0xff1e`, bridge `0x1ed84 ->
  0x1edc6`, bucket dispatch `0x1efc2`, and encoded-span renderer `0x1f88e`.
- In-range full transfer:
  predicate is raw count `D5 <= +0x10`. Handler range `0x1069c..0x106a0`
  writes accepted count `+0x04 = raw` and clears overflow count `+0x06`; the
  same `0x10084 -> 0x13070 -> 0x13250 -> 0x138de` producer path queues the
  encoded object. The object count word and payload length equal the restored
  command count unless later allocation or copy-stop state splits the row.
- Negative row:
  predicate is stored row word from `D4 >> 16` being negative at
  `0x106ae..0x106b4`. The handler has already stored accepted/overflow counts
  and ensured root `0x78297a`, but `0x106b6..0x106f6` drains positive payload
  through `0xdace` and skips `0x13070`. No encoded raster object is linked.
  If the drain does not return `-1`, exit `0x106f8..0x10752` still advances
  the modeled raster cursor; the representative negative-row stream advances
  row state from `-1` to `0`.
- Accepted nonnegative row with no allocation failure:
  predicate is `D4 >= 0` and `0x13070` returns a nonzero object pointer.
  `0x13070..0x13250` derives bucket index `0x782a7c`, packed key
  `0x782a7e`, allocation capacity `0x782a80`, and one or more class-`0x80`
  objects under page-root bucket root `+0x1c`. The visible output is deferred
  until `0xff1e -> 0x1ed84 -> 0x1edc6 -> 0x1ef6a -> 0x1efc2 -> 0x1f88e`.
- Accepted nonnegative row with allocation failure:
  predicate is `0x13070` returning `D7 = 0`. Handler range
  `0x106d2..0x106f2` sets current root retry flag `root+0x15.0`, publishes
  the current root through `0xff1e`, and ensures a fresh root through
  `0x10084`. The gate outcome changes publication/retry state rather than
  the encoded object format; any later object bytes must be attributed to the
  post-retry producer state.
- Transfer failure during drain or copy:
  predicate is `0xdace == -1` in a drain path or `0x138de == -1` after object
  allocation. `0x105d0` skips cursor advancement when transfer state is
  `D5 = -1`; object and publication state depend on which producer boundary
  had already been crossed. New traces in this class must name whether the
  stop occurs before `0x10084`, after root ensure but before `0x13070`, or
  after `0x13250` allocated an object.

State classification for the matrix:

- Canonical raster state is the `0x783170` block: row `+0x02`, accepted count
  `+0x04`, overflow count `+0x06`, mode `+0x08`, origin `+0x0a`, scale
  `+0x0e`, row byte limit `+0x10`, and active byte `+0x12`.
- Canonical page/image state begins only after the root boundary
  `0x10084`: current root `0x78297a`, encoded objects under root `+0x1c`,
  object class/mode/count/key/payload bytes, and retry flag `root+0x15.0`.
- Derived/cache state is bucket index `0x782a7c`, packed key `0x782a7e`,
  split capacity `0x782a80`, copied render root `+0x18`, and row-construction
  caches consumed by `0x1f88e`.
- Parser scratch is the restored six-byte `ESC *b#W` record at
  `0x78299e - 6`, delayed handler state from `0x121cc` / `0x12218`, and
  remaining payload count while `0xdace`, `0x138de`, or `0x12328` consumes
  bytes.
- Firmware bookkeeping is allocator state `0x782a70/0x782a72/0x782a76`,
  copy-stop byte `0x782996`, retry publication state, and cursor advancement
  after non-`-1` completion.
- Unknown: no ROM-local gate outcome is unknown for the documented branches.
  Future work must change a named predicate, field, object byte, retry state,
  bridge root, cursor update, or `0x1f88e` input before this matrix changes.

Fixtures `0x105d0-modeled raster transfer skip and cap gate`, `modeled raster
command stream applies 0x105d0 byte-count cap`, `modeled raster command stream
queues inclusive page-extent row`, `modeled raster command stream drains
beyond-extent transfer without queueing`, `modeled raster command stream
drains negative-row transfer and advances`, and `raster parser trace feeds
capped and drained transfer gates` divide these outcomes at the handler
boundary. The writer set is therefore `0x105d0` for `+0x02`, `+0x04`,
`+0x06`, and `+0x12`; the consumers are `0xdace` for discarded bytes,
`0x10084` for page-root availability, and `0x13070` for accepted rows.

Representative parser-fed gate outcomes:

- Capped queue:
  the `ESC *t300R` / `ESC *r0A` / `ESC *b4W f0 0f aa 55` gate path reaches
  `0x10808`, `0x1075a`, `0x11f82`, `0x12218`, and `0x105d0`. With byte limit
  `2`, `0x105d0` stores accepted count `+0x04 = 2`, overflow
  `+0x06 = 2`, and queues only the first two payload bytes as object
  `00 00 00 00 80 00 00 02 00 00 f0 0f`; the remaining two bytes are drain
  input, not object payload.
- Inclusive page-extent queue:
  when the computed row equals page extent `15`, the same delayed record path
  still queues the row, advances the modeled row state to `16`, and emits
  encoded object `00 00 00 00 80 00 00 02 f0 00 f0 0f`. The final rendered
  row for that object is `####........####`.
- Beyond-extent drain:
  when the row is already beyond extent, `0x1065c..0x10698` drains all four
  payload bytes through `0xdace`, returns before `0x10084`, leaves the gate
  unqueued, and does not advance row state.
- Negative-row drain:
  when the row is `-1`, the count/overflow stores still occur
  (`+0x04 = 2`, `+0x06 = 2` for the capped four-byte stream) and `0x10084`
  still ensures a root, but `0x106b6..0x106f6` drains all four payload bytes
  without calling `0x13070`. The exit path advances the modeled row state to
  `0`, and object length remains zero.

The host-fetched gate fixture starts from the same admitted byte stream through
`0xa904` before these outcomes, so the parser-to-family boundary is not only a
modeled state setup. The documentation claim is still ROM-local: the evidence
is the restored record, gate stores, object bytes or no-object outcome, and
handler addresses above, not a comparison to a physical printed raster row.

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
- `0x1065c..0x10698`: for beyond-extent rows, drain positive remaining count
  through `0xdace`; nonpositive count returns immediately, and `0xdace == -1`
  returns early.
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
  positive remaining payload through `0xdace` and skip `0x13070`; nonnegative
  rows pass `A4` as the sole `0x13070` argument.
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
  `0x13070..0x13382`. Remaining dense-row work belongs here only when a byte
  stream changes a named ROM input to the documented path: accepted count or
  drain result at `0x105d0`, allocator pre-state
  `0x782a70/0x782a72/0x782a76`, split capacity `0x782a80`, copy-stop byte
  `0x782996`, packed-key advance through `0x332ee`, bridge bucket roots, or
  mode-specific `0x1f88e` row-construction inputs.

Evidence and ROM-local status:

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
- The ROM-local split algorithm and object fields are grounded in the branch
  boundaries, field writes, and static large-payload
  walkthrough are direct disassembly. Pixel output is documented by tracing the
  ROM render helpers and deriving rows from the queued object bytes. There is
  no external rendered-row image to compare against. Parser-fed fixtures are
  only branch/path drivers and state-shape checks; they do not establish pixel
  truth beyond the ROM helper behavior they exercise. The covered dense-row
  contract therefore stops at named ROM inputs, not at an unspecified
  documentation gap: additional tracing belongs here only when a byte stream
  changes the accepted count or drain result at `0x105d0`, allocator pre-state
  `0x782a70/0x782a72/0x782a76`, split capacity `0x782a80`, copy-stop byte
  `0x782996`, packed-key advance through `0x332ee`, bridge bucket roots, or
  mode-specific `0x1f88e` row-construction inputs.

### Encoded Raster Object Outcome Matrix

This matrix owns the accepted-row object shape after the transfer gate has
called `0x13070`. It is the checkpoint for streams that keep the same
parser-to-transfer route but change encoded object fields, allocator split
state, payload copy outcome, packed-key advance, bridge bucket roots, or
`0x1f88e` mode inputs.

- Single encoded object:
  `0x13070` computes bucket index `0x782a7c` and packed key `0x782a7e`, then
  calls `0x13250` with object size `accepted_count + 0x0a` and mode byte from
  raster state `+0x08`. `0x13250` links the object at the selected page-root
  bucket head, writes class byte `+0x04 = 0x80`, and writes mode byte `+0x05`.
  `0x13146..0x13220` writes count word `+0x06`, key word `+0x08`, and payload
  bytes at `+0x0a..`.
- Split encoded objects:
  when allocator capacity `0x782a80` is smaller than remaining accepted count,
  `0x13070` emits one capped object, subtracts capacity from raster state
  `+0x04`, advances the local packed-key row through `0x332ee`, and loops.
  Each later `0x13250` call inserts at the same bucket head, so the last
  object in the split becomes the first object seen by bucket walk `0x1efc2`.
- Allocation failure:
  if `0x132b6` returns zero through `0x13250`, `0x13070` drains accepted plus
  overflow count through `0x12328` and returns zero to `0x105d0`. The encoded
  object format is unchanged; the visible outcome is the transfer-gate
  publication/retry path, not a partial object claim.
- Payload copy stop:
  after object allocation, `0x138de == -1` makes `0x13070` return `-1`.
  If copy-stop byte `0x782996` is set after a non-`-1` copy, `0x13070` drains
  accepted plus overflow count through `0x12328` and exits. New traces in
  this class must name whether object bytes were already allocated and which
  payload prefix was copied.
- Mode `0` render:
  `0x1f88e` masks object byte `+0x05 & 3`, dispatches table `0x1f8ca` entry
  `0` to `0x1f8da`, and copies payload words directly to the current-band
  destination. There is no separate odd-byte tail helper in this ROM path.
- Mode `1` render:
  table entry `1` reaches `0x1f8e6`. Each payload byte indexes word table
  `0x30914`; the expanded word is written to the current row and either the
  adjacent current-band row or fallback row `0x7810b4 + byte_pair_offset`.
- Mode `2` render:
  table entry `2` reaches `0x1f920`. Even and odd payload streams are expanded
  through longword table `0x30b14`; row pointers `A1`, `A4`, and `A5` are
  selected from current-band or fallback storage according to the split high
  word returned by `0x1f414`. The second pass rewrites `$a001` for the shifted
  phase.
- Mode `3` render:
  table entry `3` reaches `0x1f9c6`. Each payload byte expands through
  `0x30914` twice to form one longword written to four row pointers selected
  from current-band and fallback storage.

Field grouping for this route:

- Canonical state:
  raster state `0x783170 +0x02/+0x04/+0x06/+0x08`, page-root bucket `+0x1c`,
  encoded object link `+0x00`, class byte `+0x04`, mode byte `+0x05`, count
  word `+0x06`, packed key `+0x08`, and payload bytes `+0x0a..`.
- Derived/cache state:
  bucket index `0x782a7c`, packed key `0x782a7e`, split capacity
  `0x782a80`, allocator cursors `0x782a70/0x782a72/0x782a76`, render root
  `+0x18`, row stride `0x783a1c`, band split from `0x1f414`, byte-pair
  fallback offset, and expansion tables `0x30914` / `0x30b14`.
- Parser scratch:
  restored delayed `ESC *b#W` record, accepted and overflow counts while
  `0x138de` copies payload bytes or `0x12328` drains them, and any payload
  bytes not yet admitted into the object.
- Firmware bookkeeping:
  copy-stop byte `0x782996`, success/zero/`-1` return in `D7`, root retry
  flag set by the caller on no-room, and mode-`2` phase rewrite through
  `$a001`.
- Unknown:
  no ROM-local object-layout or mode-dispatch branch remains unknown for the
  documented accepted-row paths. Remaining raster work starts only when a
  stream changes accepted count, allocator pre-state, split capacity, copied
  payload prefix, packed-key advance, bridge bucket root, or mode-specific row
  construction.

Evidence: producer listing
`generated/disasm/ic30_ic13_raster_object_queue_013070.lst`
`0x13070..0x13250`, allocator listing in the same file `0x132b6..0x13382`,
encoded renderer listing
`generated/disasm/ic30_ic13_bitmap_encoded_span_modes_01f88e.lst`
`0x1f88e..0x1fa5a`, table examples in
`generated/analysis/ic30_ic13_render_expansion_fixtures.md`, and fixtures
`0x13070/0x13250 raster row queues encoded-span object`,
`0x13070/0x13250 raster row queues non-byte-aligned encoded-span object`,
mode-`1` through mode-`3` row-object fixtures, and the `0x1f88e mode-0`
through `0x1f88e mode-3` render fixtures named in the Evidence list.

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

The disassembly contract for `0x1f88e..0x1fa5a` is:

- Shared entry `0x1f88e` receives `A1` at object byte `+4`, advances `A2` to
  byte `+5`, masks `object[5] & 3` into mode `D4`, reads object word `+6` as
  byte count `D5`, sets scaled row count `D3 = mode + 1`, reads object word
  `+8` as packed coordinate `D1`, calls `0x1f3d4`, preserves the byte-pair
  fallback offset in `A3`, calls split helper `0x1f414`, then dispatches
  through table `0x1f8ca`.
- Mode `0`, target `0x1f8da`, copies literal words from payload cursor `A2` to
  destination `A1`, subtracting two from the remaining count. There is no
  separate odd-byte tail in this helper.
- Mode `1`, target `0x1f8e6`, expands each payload byte through word table
  `0x30914` and stores the same word to the current row and one adjacent row.
  The adjacent row is `A1 + 0x783a1c` when both rows fit the current band, or
  `0x7810b4 + A3` when `0x1f414` reports a fallback row.
- Mode `2`, target `0x1f920` with shared loop `0x1f9a0`, expands even and odd
  payload bytes through longword table `0x30b14`. The high word of split `D3`
  selects which of three row pointers stay in the current band and which start
  at `0x7810b4 + A3`. The second pass rewrites `$a001` with adjusted phase
  before processing odd-indexed payload bytes.
- Mode `3`, target `0x1f9c6`, expands each payload byte through `0x30914`
  twice to form one longword, then writes that longword to four row pointers.
  The split high word again selects current-band rows versus fallback rows
  rooted at `0x7810b4 + A3`.

The detailed row-pointer cases and field grouping for these helpers are in
[page-raster-imaging.md](page-raster-imaging.md#bitmap-object-dispatch-semantic-checkpoint).
The controlling evidence is
`generated/disasm/ic30_ic13_bitmap_encoded_span_modes_01f88e.lst`, not an external
rendered-row comparison.

For the primary mode-0 object above, the rendered row is:

```text
................####........#####.#.#.#..#.#.#.#
```

This row is the ROM-derived result for the documented mode-0 object fields and
payload bytes. Fixtures named `0x1f88e mode-0 raster object renders queued
literal row`, `0x1f88e mode-0 raster object renders sub-byte shifted literal
row`, `0x1f88e mode-1 raster object expands queued bytes into two rows`,
`0x1f88e mode-2 raster object expands queued byte pair into three rows`,
`0x1f88e mode-2 raster object renders sub-byte shifted expanded rows`,
`0x1f88e mode-2 raster object clips current-band rows and continues in
fallback buffer`, and `0x1f88e mode-3 raster object expands queued bytes into
four rows` are path and transcription checks for the static helper contract
above.

## Mixed Page-Record Composition

This cluster documents the raster transfer path inside a heterogeneous page
record, not as an isolated row object. The host byte stream is:

```text
21 1b 2a 63 31 32 61 35 62 30 50 1b 2a 74 33 30 30 52
1b 2a 72 30 41 1b 2a 62 32 57 c3 3c
```

That is printable `!`, selector-7 rule command `ESC *c12a5b0P`,
`ESC *t300R`, `ESC *r0A`, and delayed raster transfer
`ESC *b2W c3 3c`. It queues all three visible producer classes into one
current page record before bridge/render:

- compact text through `0xd04a` / `0x12f2e` / `0x1387c`;
- selector-7 rectangle through `0x10898` / `0x133aa`;
- mode-0 raster through delayed `0x11f82` / `0x12218` / `0x105d0` /
  `0x13070` / `0x13250`.

The canonical page-record storage shape for the same cluster is:

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
when the FF path finalizes the heterogeneous page record. Readers are
`0x1ed84` / `0x1edc6`, `0x1ef6a`, `0x1efc2`, raster dispatch `0x1f88e`,
compact text dispatch `0x1effe`, and rule dispatch `0x1f446`. The output
effect is one published text/rule/raster page image using the same ROM-derived
row path as the non-published current-page render for the same byte stream.

Supporting evidence names for this route are `host-fetched text rectangle and
raster page record feeds 0x1ed84 and 0x1ef6a`, `host-fetched text rectangle
raster FF publishes rendered page record`, `addressed text/rule/raster field
groups reach publication and render entry`, and `addressed text rectangle
raster stream matches page-record output`.

## Additional Command-Family Variants

The same raster command/data model extends beyond the primary 300-dpi mode-0
stream.

Lower-resolution streams use the same parser, delayed-transfer, object-queue,
bridge, and render path with a different `0x10808` mode/scale result:

- `ESC *t150R ESC *r0A ESC *b#W` selects encoded mode `1`;
- `ESC *t100R ESC *r0A ESC *b#W` selects encoded mode `2`;
- `ESC *t75R ESC *r0A ESC *b#W` selects encoded mode `3`.

For each lower-resolution stream, `0x10808` writes mode byte `+0x08` and scale
word `+0x0e`, `0x1075a` starts raster state, `0x11f82` delays the transfer,
`0x12218` restores the transfer record, `0x105d0` gates the payload,
`0x13070` / `0x13250` queues the encoded object with object byte `+0x05` set
to the mode, and `0x1efc2 -> 0x1f88e` dispatches the corresponding mode
helper.
Supporting evidence names are `modeled raster command stream queues and
renders 150-dpi mode-1 payload`, `modeled raster command stream queues and
renders 100-dpi mode-2 payload`, `modeled raster command stream queues and
renders 75-dpi mode-3 payload`, `raster mode streams tie ROM parser dispatch
to modeled queued objects`, `host-fetched raster mode streams reach parser and
rendered rows`, and `host-fetched raster mode streams feed 0x1ed84 and
0x1ef6a`.

Repeated transfers reuse the same canonical raster state block while restoring
independent delayed records. Two uppercase `ESC *b2W` commands restore
separate `80 57 00 02 00 00` records, consume payloads at offsets `17` and
`24`, advance raster row state to `2`, and queue encoded objects at packed
coords `0x0000` and `0x1000`. Lowercase same-family command accumulation stays
inside the `*b` parser family: stream `ESC *b2w2W` preserves delayed record
`80 77 00 02 00 00` and consumes payload only after the uppercase terminator
at offset `19`. Supporting evidence names are `modeled raster command stream
queues consecutive ESC *b#W rows`, `modeled raster command stream renders
consecutive queued rows`, `modeled raster command stream accepts lowercase
same-group resolution chaining`, `modeled raster command stream defers
lowercase ESC *b w payload until uppercase terminator`, `host-fetched raster
multi-row and chained streams preserve 0x1edc6 bridge contract`, and
`host-fetched raster streams feed 0x1ed84 and 0x1ef6a`.

Active-state behavior has two distinct outcomes. `ESC *rB` clears only active
byte `+0x12`, so a later `ESC *t150R` can update mode and scale again. While
active byte `+0x12` is still set, `ESC *t75R` is ignored, and the following
`ESC *b2W` queues a mode-0 object using the earlier raster mode. Supporting
evidence names are `raster end parser trace feeds active-clear and resolution
re-enable`, `host-fetched raster end stream clears active state and re-enables
resolution`, `raster active resolution parser trace preserves current mode`,
and `host-fetched active raster resolution stream preserves current mode`.

## Reproduction Contract

A byte-stream reproduction must preserve these behaviors:

- `ESC *b#W` is delayed. The command record and payload bytes are separate
  pieces of state until `0x12218` restores the record and calls `0x105d0`.
- Raster resolution commands are ignored while raster active byte `+0x12` is
  set.
- Raster start commands are also ignored while raster active byte `+0x12` is
  set; `0x1075a` preserves the previous origin, baseline, scale, mode, and
  byte limit until `ESC *r#B` clears the active byte.
- `ESC *r#B` clears only active byte `+0x12`; it does not reset mode, scale,
  origin, or byte limit.
- Lowercase same-family `ESC *b#w` records remain pending until an uppercase
  terminator restores that record and consumes payload bytes.
- Consecutive uppercase `ESC *b#W` commands restore separate records and
  advance the raster row for each queued transfer.
- Off-page transfer bytes are still consumed. Beyond-extent rows drain without
  row advance; negative rows drain and advance to row zero.
- In-range transfers larger than row limit `+0x10` must split raw count into
  accepted count `+0x04 = +0x10` and overflow `+0x06 = raw - +0x10`.
  `0x13070` / `0x138de` copy only accepted bytes into encoded row objects;
  remaining accepted plus overflow bytes are consumed through the `0x12328`
  drain exits without becoming object payload.
- Queued payload bytes use the `0x138de` local `1a 58 -> 00` behavior.
- Row objects must be stored under page-root `+0x1c`, not rendered immediately.
- Encoded row object byte `+4 = 0x80` is what sends the renderer through
  `0x1efc2 -> 0x1f88e`.
- Object byte `+5` selects raster expansion mode `0..3`.
- Object word `+8` controls destination x/y packing; object bytes at `+0x0a`
  are the source span payload.
- `0x1f88e` must parse the encoded object before helper dispatch: it reads
  mode from `+0x05 & 3`, byte count from word `+0x06`, packed key from
  word `+0x08`, derives destination position through `0x1f3d4`, and runs
  split helper `0x1f414` before selecting table `0x1f8ca`.
- Mode `0` target `0x1f8da` copies payload bytes as literal words. Mode `1`
  target `0x1f8e6` expands each payload byte through table `0x30914` into
  two rows. Mode `2` target `0x1f920` expands even/odd payload bytes through
  table `0x30b14` into three rows, including the `$a001` phase rewrite for
  odd-indexed bytes. Mode `3` target `0x1f9c6` expands each payload byte
  through `0x30914` twice and writes four rows.
- Current-band versus fallback-row placement is part of the pixel contract.
  `0x1f414` decides whether expanded rows stay under the current destination
  rooted at `0x783a28` or continue in fallback storage rooted at
  `0x7810b4 + byte_pair_offset`; reproducing only the encoded object bytes is
  insufficient without this split state.

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
- The dense-row split rule through `0x132b6` is documented in
  `Allocation Capacity And Dense Rows`. The composed semantic ledger is in
  [semantic-state-model.md](semantic-state-model.md), section
  `Raster Transfer Gate And Encoded Rows`.
- Additional work through `0x105d0`, `0x10084`, `0x13070`, `0x13250`, and
  `0x132b6` should target new byte streams that change the raster chain,
  encoded object bytes, allocator state, bridge bucket roots, copy-stop byte
  `0x782996`, packed-key advance, or mode-specific `0x1f88e`
  row-construction paths. Canonical output state is documented as the page-root
  `+0x1c` raster chain and object bytes written by `0x13070`/`0x13250`;
  derived/cache state is the bucket/key and render-record copy used by
  `0x1ed84`/`0x1ef6a`; parser scratch is the delayed `80 57 ...` command
  record, snapshot, payload offset, and drained payload bytes; firmware
  bookkeeping is the modeled allocation result and
  stream-storage cursor.
- `0x13250..0x1381c` addressed storage is owned by the page-record storage
  contract, not by a fixture-only assertion. `0x13250` calls allocator helper
  `0x132b6`, links each returned object at the selected root `+0x1c` bucket
  head, and fills object class/mode/count/key fields before `0x138de` copies
  accepted payload bytes. The shared stream allocator `0x1381c` owns updates to
  `0x782a70`, `0x782a72`, and `0x782a76`; page-record bridge `0x1ed84` /
  `0x1edc6` then copies root `+0x1c` to render `+0x18`, where `0x1efc2`
  dispatches class `0x80..0xff` objects to `0x1f88e`. Mixed text/rule/raster
  fixtures are supporting checks for that documented owner route, not the
  primary explanation.
- Page-image coverage is no longer missing only because the raster fixture is
  isolated: checked-in fixtures now include mixed text/rule/raster publication,
  geometry-changing publication streams, font-selection streams, downloaded
  glyph FF publication, and a parser-driven downloaded-glyph/rule/raster page.
  New ROM-local raster/page-image work should start only from byte-stream
  variants that expose different raster state fields, page-root bucket/object
  bytes, allocator or bridge fields, or `0x1f88e` row-construction inputs. It is
  not a gap in the software-visible raster object layout or render dispatch
  documented above.
