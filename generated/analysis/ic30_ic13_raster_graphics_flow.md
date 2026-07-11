# IC30/IC13 Raster Graphics Flow

This report collects the raster command edge, delayed payload handoff,
page-object queueing, and bitmap render dispatch from the verified firmware
image.

## Command and Payload Edge

- `ESC *t#R`
  - Handler: `0x10808`
  - Firmware behavior: Maps the parsed resolution to raster mode/scale state
    at `0x783170`. The
executable stream fixtures pin 300/150/100/75 dpi as modes `0..3`.
- `ESC *r#A`
  - Handler: `0x1075a`
  - Firmware behavior: Starts raster graphics, captures the current
    cursor-derived origin/baseline,
and computes the row limit used by later transfers.
- `ESC *r#B`
  - Handler: `0x107fa`
  - Firmware behavior: Clears only the active raster state; a later `ESC *t#R`
    can still change
mode.
- `ESC *b#W`
  - Handler: `0x11f82 -> 0x121cc -> 0x105d0`
  - Firmware behavior: Records a delayed payload handler. `0x12218` restores
    the six-byte command
record and dispatches `0x105d0` after the payload begins.

## Queue and Render Path

- `0x105d0`: Restored raster-transfer handler. It checks active state and row
  limits, caps the
stored byte count to the printable gate, drains any overflow bytes, and
advances the raster row only for accepted transfers.
- `0x10084`: Ensures the current page/control root before an accepted row
  object is queued.
- `0x13070`: Builds the raster row source object from raster x/y, mode, byte
  count, and payload
metadata.
- `0x13250`: Allocates and links the encoded-span bucket object under
  page-root `+0x1c`; raster
objects are born with byte `+4 = 0x80` and byte `+5` selecting encoded mode.
- `0x138de`: Copies the accepted host payload bytes into the queued object
  starting at `+0x0a`.
- `0x1edc6`: Copies the page-root bucket array to render-record `+0x18`
  without normalizing raster
objects.
- `0x1efc2 -> 0x1f88e`: Dispatches the high-bit encoded-span object to the
  raster renderer. The low
two bits of object byte `+5` select modes `0..3` through table `0x1f8ca`.

## Parser/Data Boundary

- Normal parser table entries route `ESC *t#R`, `ESC *r#A`, and `ESC *b#W`
  through `0x10808`,
`0x1075a`, and `0x11f82` respectively.
- `0x11f82` does not copy raster bytes directly. It snapshots the delayed
  handler `0x105d0` through
`0x121cc`, so payload bytes are consumed only after `0x12218` restores the
command record.
- Lowercase-final `ESC *b#w` preserves parser mode in the `*b` family. The
  uppercase `W` terminator
replaces the delayed snapshot and starts exactly one payload transfer.
- The harness ties this to ROM parser traces for 300/150/100/75-dpi streams,
  consecutive rows,
capped transfers, beyond-extent drains, and same-group lowercase-final
transfer boundaries.

## State Reference Scan

- `0x00783170`
  - Role: raster graphics state block base used by reset, mode, start, and
    transfer paths
  - Longword literal references: `0x00cc7a`, `0x00f9f2`, `0x00fc7e`,
    `0x0105da`, `0x010764`,
`0x010812`
- `0x00782c8a`
  - Role: current horizontal cursor word captured as raster start axis/source
    x
  - Longword literal references: `0x00d15c`, `0x00d19a`, `0x00d1a2`,
    `0x00d228`, `0x00d24a`,
`0x00d2d4`, `0x00d310`, `0x00d34c`, `0x00d3c4`, `0x00d51e`, `0x00d56c`,
`0x00d5ee`, ... (110 total)
- `0x00782c8e`
  - Role: current vertical cursor word captured as raster start axis/source y
  - Longword literal references: `0x00ca6e`, `0x00cbb8`, `0x00d364`,
    `0x00d3ec`, `0x00d402`,
`0x00d4c2`, `0x00d7d0`, `0x00d86c`, `0x00d882`, `0x00d912`, `0x00ed94`,
`0x00f0c4`, ... (83 total)
- `0x00782db4`
  - Role: page extent/input used while computing raster transfer limits
  - Longword literal references: `0x00cd4e`, `0x00f89e`, `0x00f8b2`,
    `0x00f984`, `0x00f98c`,
`0x00fb78`, `0x00fb86`, `0x00fbb0`, `0x00fdb0`, `0x00fdbe`, `0x00fde8`,
`0x01018c`, ... (14 total)
- `0x00782db6`
  - Role: vertical page extent used by geometry/raster clipping paths
  - Longword literal references: `0x00d3a0`, `0x00d4e8`, `0x00d810`,
    `0x00d938`, `0x00f898`,
`0x00f8b6`, `0x00fbda`, `0x00fbf6`, `0x010bd8`, `0x01279a`, `0x01ca4c`,
`0x01d0dc`, ... (29 total)
- `0x00782db8`
  - Role: horizontal page extent used by geometry/raster clipping paths
  - Longword literal references: `0x00d26a`, `0x00d334`, `0x00d38a`,
    `0x00d69c`, `0x00d7a4`,
`0x00d7f8`, `0x00e9c6`, `0x00e9e4`, `0x00ec70`, `0x00ec80`, `0x00f25e`,
`0x00f4f8`, ... (29 total)
- `0x0078297a`
  - Role: current page-root pointer ensured before queuing accepted raster
    rows
  - Longword literal references: `0x00c44a`, `0x00c50a`, `0x00c61c`,
    `0x00d204`, `0x00d48a`,
`0x00d636`, `0x00d8da`, `0x00da68`, `0x00ff28`, `0x00ff30`, `0x00ff56`,
`0x00ffa4`, ... (35 total)
- `0x00782a70`
  - Role: remaining object-storage bytes reset by `0x10084` and consumed by
    allocators
  - Longword literal references: `0x0100de`, `0x0132c6`, `0x0132d2`,
    `0x0132e4`, `0x0132f2`,
`0x013314`, `0x013360`, `0x013376`, `0x01382e`, `0x01386a`
- `0x00782a72`
  - Role: current object-storage chunk link pointer seeded from root `+0x20`
  - Longword literal references: `0x0100e8`, `0x013346`, `0x01334e`,
    `0x013852`, `0x01385a`
- `0x00782a76`
  - Role: next-free object-storage pointer used by the shared allocator
  - Longword literal references: `0x0132f8`, `0x01330e`, `0x01331a`,
    `0x013358`, `0x01337c`,
`0x013822`, `0x013870`

## Call-Site Anchors

- `0x10084` ensure-root calls from raster transfer sites: `0x0106a4`,
  `0x0106ec`.
- `0xff1e` finalization calls from raster page-boundary site: `0x0106e6`.
- `0x13070` raster row builder references: `0x0106cc`.
- `0x13250` bucket object allocator references: `0x013136`.
- `0x138de` raster payload copy references: `0x01320c`.

## Current Reproduction Contract

- A byte-stream reproduction must preserve the delayed `ESC *b#W` payload
  boundary: the six-byte
parsed record and the payload bytes are separate pieces of state until
`0x12218` restores and dispatches `0x105d0`.
- Accepted transfers must ensure a page root before `0x13070` / `0x13250`
  queue the row object.
Drained transfers beyond the page extent consume host bytes but do not queue
an object or advance the row counter.
- Raster row objects share the page-root `+0x1c` bucket array with compact
  text buckets, but render
through the encoded-span high-bit branch rather than the compact glyph branch.
- `tools/render_fixture_harness.py` currently proves parser dispatch, delayed
  restore, root
allocation, object bytes, bridge copying, and final rendered rows for the
primary `ESC *t300R` / `ESC *r1A` / `ESC *b4W` stream, plus mode, cap/drain,
multi-row, lowercase-final, and end-raster variants. The mixed
`!\x1b*c12a5b0P\x1b*t300R\x1b*r0A\x1b*b2W` fixture now also has an addressed
allocation variant where the raster row queues through addressed `0x13070` /
`0x13250` storage after the addressed text and rule objects, then renders the
same bucket/rule/raster rows and publishes the materialized addressed record
through the modeled `0xff1e` pool-record boundary.
- Remaining work is a fuller CPU/parser-state fixture that replaces modeled
  state with real
page/control pool records while preserving the same byte-stream-to-pixel
boundary.
