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
  - `transparent non-0x58 probe byte reaches page-record output`
  - `transparent data control payloads advance through fixed-space path`
  - `transparent default-filtered control enters unflagged fixed-record path`
  - `transparent nonzero filters route controls through printable path`
  - `transparent nonzero high-control byte queues tall glyph bucket`
  - `transparent nonzero high-control interior samples remain printable`
  - `transparent nonzero high-control upper bound remains printable`
  - `transparent secondary high-control byte enters segmented page-record path`
  - `transparent secondary segmented render prefix exposes source boundary`

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
handling. Disassembly `0xd0f0..0xd124` calls `0x1393a(0x20, 0x782d7e)`. In the
flagged built-in branch it then clears source longword `+4` before entering
`0xd550`, so the `0xd62e..0xd644` test sees no glyph pointer, skips page-root
allocation and `0xd824` queueing, and advances the cursor as spacing. `0xd04a`
is the normal printable text path into character mapping, cursor placement,
compact text object creation, page-record storage, bridge, and render dispatch.
When `0x1393a(0x20)` returns an unflagged inline/fixed-record source, the same
`0xd0f0` entry continues through `0xd140` and `0xd3b2`, so the substituted
space can queue a normal unflagged compact text object.

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
- selected context byte: `0`
- local filtering word: `0`
- consumed values: `41 7f 05 85 42`
- routes: `d04a d04a d0f0 d0f0 d04a`
- control hits: `1`

A second isolated reader fixture uses saved record `80 58 00 02 00 00` and
payload bytes `1a 41 21`. It consumes three host bytes for two transparent
payload values:

- byte count: `2`
- consumed values: `41 21`
- routes: `d04a d04a`
- control hits: `0`

This pins disassembly `0x124cc..0x124e8`: when the byte after `0x1a` is not
`0x58`, that second byte is the routed payload value. The original `0x1a` is
only the probe prefix.

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

The visible probe fixture uses stream:

```text
1b 26 70 32 58 1a 41 21
```

That is `ESC &p2X\x1aA!`. The restored record count is `2`, but the raw payload
slice is `1a 41 21` because the non-`0x58` probe consumes both `1a` and `41`
for one routed payload value. The queued values are `41 21`; byte `0x41` maps
to glyph `0x40`, queues compact coord `0x0a00`, and renders visible `A` before
the following `!` at compact coord `0x0202`.

The control-payload page-record fixture uses stream:

```text
1b 26 70 34 58 21 05 85 21
```

That is `ESC &p4X!\x05\x85!` under the default zero filtering state. It proves
one command can mix both transparent routing exits:

- restored record: `80 58 00 04 00 00`
- raw payload: `21 05 85 21`
- values: `21 05 85 21`
- routes: `d04a d0f0 d0f0 d04a`
- first printable payload byte `0x21`: queues compact coord `0x0001`
- C0 payload byte `0x05`: maps fixed-space host byte `0x20` to glyph `0x1f`,
  clears the glyph pointer from `0x0146b4` to `0`, advances cursor from
  `pack12(28)` to `pack12(46)`, and queues no page-record text object
- high-control payload byte `0x85`: repeats the same fixed-space route,
  advances cursor from `pack12(46)` to `pack12(64)`, and queues no page-record
  text object
- final printable payload byte `0x21`: queues compact coord `0x0604`
- page-record object prefix: `00 00 00 00 00 00 00 02 20 00 01 20 06 04`
- final cursor x: `pack12(82)`
- render entry: the bridged rows contain only the two visible `!` glyphs,
  separated by the two fixed-space advances

The unflagged fixed-record fixture uses stream:

```text
1b 26 70 33 58 21 05 21
```

That is `ESC &p3X!\x05!` under the default zero filtering state, but with an
inline/fixed-record font context where both host space and `!` are valid
unflagged records. It proves the `0xd0f0` entry does not stop at cursor-only
spacing for all source classes:

- restored record: `80 58 00 03 00 00`
- raw payload: `21 05 21`
- selected context byte: `0`
- local filtering word: `0`
- values: `21 05 21`
- routes: `d04a d0f0 d04a`
- first `!`: unflagged source host `0x21`, mapped glyph `1`, inline record
  `02 03 04 00 00 00 00 80`, positioned x/y `22/23`, compact coord `0x7601`
- C0 payload byte `0x05`: routes through `0xd0f0`, substitutes host byte
  `0x20`, reads unflagged inline record `01 02 00 00 00 00 00 70`, maps glyph
  `0`, positions x/y `40/20`, queues compact coord `0x4802`, and reuses bucket
  `1`
- final `!`: queues unflagged glyph `1` at compact coord `0x7a03`
- bucket `1` object:
  `00 00 00 00 00 00 00 03 01 76 01 00 48 02 01 7a 03` plus trailing zeros
- bridge context slots begin `(0x00000100, 0, 0, 0)`
- selected bucket render: row count `10`, row width `74`, digest
  `89629435e063529ce7150d603ed9be37a74658317db3e97a4ae01b1c8d64f9d9`
- final cursor x: `pack12(64)`

The nonzero-filter fixture uses stream:

```text
1b 26 70 34 58 21 05 80 21
```

That is `ESC &p4X!\x05\x80!` with selected context byte `1` and local
filtering word `1`. It proves the other side of both filter branches:

- restored record: `80 58 00 04 00 00`
- raw payload: `21 05 80 21`
- selected context byte: `1`
- local filtering word: `1`
- values: `21 05 80 21`
- routes: `d04a d04a d04a d04a`
- C0 payload byte `0x05`: maps through `0xd04a` to glyph `0x04`, glyph entry
  `0x0186c6`, and compact coord `0x0d01`
- high-control payload byte `0x80`: maps through `0xd04a` to glyph `0x7f`,
  glyph entry `0x016aca`, and compact coord `0x0003`
- page-record object prefix:
  `00 00 00 00 00 00 00 04 20 00 01 04 0d 01 7f 00 03 20 06 04`
- final cursor x: `pack12(82)`
- render entry: all four routed payload values contribute compact text entries
  and visible rows

The high-control nonzero-filter fixture uses stream:

```text
1b 26 70 33 58 21 98 21
```

That is `ESC &p3X!\x98!` with selected context byte `1` and local filtering
word `1`. It keeps the high-control byte on the `0xd04a` printable path and
proves that transparent data can queue a taller high-control glyph into a
different bucket from surrounding printable bytes:

- restored record: `80 58 00 03 00 00`
- raw payload: `21 98 21`
- selected context byte: `1`
- local filtering word: `1`
- values: `21 98 21`
- routes: `d04a d04a d04a`
- payload byte `0x98`: maps to glyph `0x97`, glyph entry `0x01781e`, rows
  `29`, width `17`, positioned x/y `29/-1`, compact coord `0xfd01`, and bucket
  `-1`
- surrounding `!` bytes remain in bucket `0` at compact coords `0x0001` and
  `0x0403`
- bucket `-1` object:
  `00 00 00 00 00 00 00 01 97 fd 01` plus trailing zeros
- bucket `0` object:
  `00 00 00 00 00 00 00 02 20 00 01 20 04 03` plus trailing zeros
- selected high-control bucket render: row count `44`, row width `46`, digest
  `bd7ad3016d15c1dc2ef12adaeb1091a58f26473c0ecfc7ac13bfaf268c383e90`
- surrounding printable bucket render: row count `22`, row width `56`, digest
  `4bf2f0104b14bfa598b8acfcf8cfb69ccb4419c234f02f256781b6b236110300`

The upper-bound high-control fixture uses stream:

```text
1b 26 70 33 58 21 9f 21
```

That is `ESC &p3X!\x9f!` with selected context byte `1` and local filtering
word `1`. It proves the top value in the filtered `0x80..0x9f` range stays on
the same printable route as `0x98`, while selecting a different glyph:

- restored record: `80 58 00 03 00 00`
- raw payload: `21 9f 21`
- values: `21 9f 21`
- routes: `d04a d04a d04a`
- payload byte `0x9f`: maps to glyph `0x9e`, glyph entry `0x016d1e`, rows
  `30`, width `15`, positioned x/y `30/-2`, compact coord `0xee01`, and
  bucket `-1`
- surrounding `!` bytes remain in bucket `0` at compact coords `0x0001` and
  `0x0403`
- selected high-control bucket render: row count `44`, row width `45`, digest
  `ec0f944207561c1b9c9139749c3e37d122aebf53e2a50849dd8703416545c719`
- surrounding printable bucket render matches the `0x98` fixture digest
  `4bf2f0104b14bfa598b8acfcf8cfb69ccb4419c234f02f256781b6b236110300`

The interior high-control sample fixture drives `ESC &p3X!#!` for payload
bytes `0x81`, `0x88`, `0x90`, and `0x97` with the same selected context byte
`1` and local filtering word `1`. All four samples route
`d04a d04a d04a`; their payload bytes map to glyphs `0x80`, `0x87`,
`0x8f`, and `0x96`, queue the high-control glyph in bucket `-1`, keep the
surrounding `!` bytes in bucket `0`, and render selected-bucket digests
`841384c82ec301334f603178a4ad28152c7818bab08c8b829bb769a356b27c04`,
`64ab78cb858eb0560f08304101c4a6870daee5a94144ce028e5807952d479850`,
`e99bffbc8e6c0c9179536c5c90927a72ba3047cf7f43e43355552f0e5aa4fae4`, and
`a97b85527284735826a97ef1998d72e5841bd4331c2f2aeea24d444a35179acd`.

The secondary high-control fixture uses stream:

```text
0e 1b 26 70 33 58 21 80 21
```

That is `SO ESC &p3X!\x80!`. It composes the text-map selector with the same
transparent payload path:

- SO reaches handler `0xc6b8`, calls the modeled `0xc428(1)` install success
  path, and changes selector `0x782f06` from `0` to `1`.
- restored record: `80 58 00 03 00 00`
- raw payload: `21 80 21`
- selected context byte: `1`
- local filtering word: `1`
- values: `21 80 21`
- routes: `d04a d04a d04a`
- both `!` payload bytes read source context `0xc00ae122`, source slot `1`,
  map to glyph `0`, and queue short selector-1 entries at compact coords
  `0xc5ff` and `0xc901`
- high-control payload byte `0x80` reads the same secondary source context and
  source slot, maps to glyph `0x5f`, reports glyph entry `0x02e122`, rows
  `20062`, width `74`, and compact coord `0x1c01`
- the high-control byte enters the segmented page-record path with selector
  `0x2001`, `157` segment objects, first segment/bucket `156`/`1248`, and last
  segment/bucket `0`/`0`
- bridged context slots are `(0x440946b4, 0xc00ae122)`
- selected bucket `0` object prefix:
  `00 00 00 00 20 01 00 01 5f 00 1c 01 00 00 00 00`
- selected bucket render: row count `80`, row width `256`, digest
  `57bb3fd895be358ff325e26ae58a3b0dc526c5b08b382eb90e7273e6227fbfbb`
- final selector remains `1`; final cursor x is `pack12(64)`

The secondary segmented render-prefix fixture renders the produced buckets
until the current source model reaches a concrete bitmap-source boundary:

- renderable prefix: buckets `0..448`, `57` buckets, aggregate digest
  `292eafb8b558bd36ca0caa5caa2771976c0e611456ac0b610ec8916b9d1f03f9`
- sample bucket `0`: object count `2`, segment `0`, row count `80`, row width
  `256`, digest
  `57bb3fd895be358ff325e26ae58a3b0dc526c5b08b382eb90e7273e6227fbfbb`
- sample bucket `448`: segment `56`, row count `32`, row width `102`, digest
  `823854dc77b9234cf90f71bebcc3da7280c72dfed2bf05315e757b2d1c58c4e3`
- first failure: bucket `456`, selector `0x2001`, glyph `0x5f`, segment
  `0x39`, row skip `7296`, source `0x03fe22`, needing `1280` bytes with
  `478` available
- resolved glyph source: entry/bitmap `0x02e122`, delta `0`, mode `0`, rows
  `20062`, width `74`, render span `10`

The segment-57 failure is no longer an unresolved compact-renderer arithmetic
edge. Disassembly
`generated/disasm/ic30_ic13_bitmap_compact_object_renderers_01f024.lst` shows
`0x1f354` taking the bit-30 offset-table form, adding the selected table entry
without checking for zero, then reading row count, width, mode, and bitmap delta
from the resulting entry. For the secondary `LINE_PRINTER` table, index `0x5f`
has relative offset `0`, so firmware resolves the glyph entry to the record
header at file offset `0x02e122`. Segmented renderer `0x1f1f0` then computes
`segment << 7`, subtracts that row skip from the row count, clamps the remaining
rows to `0x80`, multiplies by even byte span `10`, and advances `A2` to file
offset `0x03fe22`.

The unresolved edge is therefore the physical/resource-window source supplied
for the read crossing the verified `IC32,IC15` pair boundary. The built-in
resource window maps file offset `N` to firmware address `0x080000 + N`, so the
computed read starts at firmware address `0x0bfe22`. It needs bytes
`0x0bfe22..0x0c0321`; only `0x0bfe22..0x0bffff` are inside the verified
`0x40000`-byte resource-pair image. Firmware startup notes show scanner `0x41a`
walking resource records through `0x0ae122` and terminating at `0x0b2f80`
before the next `0x40000` probe, but they do not yet prove whether the physical
decode wraps, mirrors, or maps another source at `0x0c0000..0x0c0321`.

## Semantic Composition

Concept: transparent print data is a counted byte-stream splice, not a binary
skip. Handler `0x11f5a` schedules the delayed payload reader, `0x12452`
normalizes and classifies each byte, `0xd04a` emits visible text objects, and
`0xd0f0` substitutes host space before following the current source class:
flagged built-ins advance cursor-only, while unflagged fixed records can queue
compact text objects.

Field groups:

- Canonical: command record `+2` byte count and text cursor `0x782c8a`.
- Derived/cache: selected-slot context byte at `0x782eea + 0x10 * 0x782f06`,
  fallback filtering byte `0x782efa`, high-byte state flags
  `0x783132`/`0x783133`, and compact coords such as `0x0001` and `0x0604`.
- Parser scratch: delayed fields `0x782a1a`, `0x782a1c`, and
  `0x782a20..0x782a25`.
- Firmware bookkeeping: local filtering word at `A6-2`.
- Unknown: manual-facing names for the filtering/context bytes remain
  provisional.

Writers:

- `0x121cc` writes the delayed snapshot.
- `0x12218` restores the saved command record.
- `0x12452` decrements the payload count and selects `0xd04a` or `0xd0f0`.
- `0xd04a`/`0xd824` write compact page-record text objects.
- `0xd0f0` writes the source object for host space. In the flagged built-in
  path it clears source `+4` before `0xd550` advances spacing; in the covered
  unflagged path it continues through `0xd140` / `0xd3b2` and queues the
  substituted host-space source.

Readers/consumers:

- `0xa904` supplies transparent payload bytes.
- `0x12452` reads command record `+2`, selected context state, fallback
  filtering state, and payload bytes.
- `0x1387c`, `0x1edc6`, `0x1ed84`, and `0x1ef6a` consume the page-record result
  for visible text output.

Output effect:

- Printable transparent bytes produce the same compact text objects and rows as
  normal printable host bytes.
- Default-filtered C0 and `0x80..0x9f` transparent bytes enter `0xd0f0`. In
  the flagged built-in fixture they advance cursor spacing without compact
  glyph entries; in the unflagged fixed-record fixture, the substituted host
  space queues a compact glyph entry.
- Nonzero filtered C0 and `0x80..0x9f` transparent bytes route through `0xd04a`
  and become normal compact text entries after symbol-set mapping.
- Secondary-context high-control bytes follow the same `0x12452` route decision
  after SO; fixture `SO ESC &p3X!\x80!` proves the downstream page-record form
  can be segmented rather than a short compact object.
- A non-`0x58` byte after `0x1a` is not lost and does not route as `0x1a`; it is
  the payload value consumed by `0xd04a` or `0xd0f0`.

Confidence: high for the delayed payload boundary, transparent probe handling,
both filtering polarities, printable output, and flagged fixed-space output
because the claims are backed by disassembly `0x11f5a`, `0x12452`, `0xd0f0`,
`0xd550`, and fixtures
`0x11f5a/0x12452 transparent text restores and consumes counted bytes`,
`transparent data parser trace feeds page-record queue`, `transparent non-0x58
probe byte reaches page-record output`, `transparent data control payloads
advance through fixed-space path`, `transparent default-filtered control enters
unflagged fixed-record path`, `transparent nonzero filters route controls
through printable path`, and
`transparent nonzero high-control byte queues tall glyph bucket`, the interior
sample fixture, and the upper-bound `0x9f` fixture. High for the secondary
selector/routing/page-record boundary because fixture `transparent
secondary high-control byte enters segmented page-record path` pins SO handler
`0xc6b8`, source context `0xc00ae122`, segmented selector `0x2001`, bridge
context slots, and a selected-bucket render digest. The render-prefix fixture
pins buckets `0..448` and the first source-read boundary at bucket `456`.

Unresolved middle edges:

- `0x124f8..0x1252a`: high-control nonzero filtering is now page-visible for a
  short primary bucket (`0x80`), interior primary samples (`0x81`, `0x88`,
  `0x90`, and `0x97`), two primary bucket-crossing glyphs (`0x98` and
  top-of-range `0x9f`), and a secondary segmented page-record boundary
  (`SO ESC &p3X!\x80!`). The remaining high-control edge is the secondary
  segment-57 physical/resource-window source interpretation at bucket `456`.
  The compact renderer path is disassembly-backed through `0x1f354` and
  `0x1f1f0`: glyph `0x5f`, segment `0x39`, file source `0x03fe22`, firmware
  source `0x0bfe22`, and required byte range `0x0bfe22..0x0c0321`. Only the
  first `478` bytes are inside the verified `IC32,IC15` resource-pair image.
  It is not primary route polarity, sampled primary interior values, or the
  renderable secondary prefix through bucket `448`.

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
- Let default-filtered C0 and `0x80..0x9f` bytes advance spacing through
  `0xd0f0` without appending compact text entries in the flagged built-in path.
- Let default-filtered C0 and `0x80..0x9f` bytes also queue substituted host
  space if the current source class is an unflagged fixed-record font with a
  valid space record.
- Let nonzero-filtered C0 and `0x80..0x9f` bytes enter `0xd04a` and emit normal
  mapped text entries.
- Treat `1a xx` with `xx != 58` as routed payload byte `xx`, not `1a`.

## Remaining Edges

- The visible-output fixtures now cover printable payload bytes, default-zero
  filtering for C0 and `0x80..0x9f`, the unflagged fixed-record `0xd0f0`
  branch, nonzero filtering for one C0/high-control pair, a primary tall
  high-control bucket plus the top-of-range `0x9f` high-control glyph, a
  secondary segmented high-control page-record path, and the `1a` non-`0x58`
  probe case.
- The default-filtered fixed-space route is page-visible for the flagged
  built-in branch, where `0xd0f0` clears source `+4`, enters `0xd550`, advances
  spacing, and queues no compact text object. It is also page-visible for the
  unflagged/fixed-record branch, where `0xd0f0` calls
  `0x1393a(0x20, 0x782d7e)`, enters `0xd140` / `0xd3b2`, queues substituted
  host-space glyph `0`, and renders the selected bucket digest
  `89629435e063529ce7150d603ed9be37a74658317db3e97a4ae01b1c8d64f9d9`.
- Broader nonzero-filtering coverage now includes primary high-control samples
  `0x81`, `0x88`, `0x90`, and `0x97`, plus the tall primary bucket-crossing
  cases `ESC &p3X!\x98!` and `ESC &p3X!\x9f!`. The secondary segmented
  mapping has a page-record boundary and renderable prefix; the remaining risk
  is the segment-57 bitmap source interpretation named above.
- The names for the active context filtering byte, fallback byte, and high-byte
  flags remain provisional.
