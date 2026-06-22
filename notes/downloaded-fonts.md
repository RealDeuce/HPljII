# Downloaded Font Descriptor And Payload Firmware

This note composes the downloaded-font command family from parsed host
commands to renderer-visible font resources. It keeps the low-level fixture
ledger intact, but names the state that a byte-stream renderer must preserve
when soft fonts, downloaded characters, and font-control commands are present.

The cluster includes multiple handlers in one command family, one shared
current-record state block with multiple writers and consumers, and an
end-to-end path from parsed font-control commands to a visible downloaded
glyph.

## Evidence

- `generated/analysis/ic30_ic13_font_control_flow.md`
- `generated/disasm/ic30_ic13_font_control_dispatch_016df6.lst`
- `generated/disasm/ic30_ic13_font_payload_setup_015b80.lst`
- `generated/disasm/ic30_ic13_font_payload_object_path_016040.lst`
- `generated/disasm/ic30_ic13_font_resource_object_add_016c14.lst`
- `generated/disasm/ic30_ic13_font_resource_validate_016fae.lst`
- `generated/disasm/ic30_ic13_font_resource_find_017026.lst`
- `generated/disasm/ic30_ic13_font_resource_payload_initializer_01719c.lst`
- `generated/disasm/ic30_ic13_font_payload_readers_016874.lst`
- `generated/disasm/ic30_ic13_font_payload_readers_0168dc.lst`
- `generated/disasm/ic30_ic13_font_resource_classify_0172c0.lst`
- `generated/disasm/ic30_ic13_font_resource_payload_record_lookup_0170be.lst`
- `generated/disasm/ic30_ic13_font_candidate_object_alloc_01bc38.lst`
- `notes/font-context-metrics.md`

Primary fixtures:

- `0x15d0a-modeled font descriptor route`
- `0x121cc/0x15d0a-modeled font descriptor command stream`
- `font descriptor stream ties ROM parser dispatch to 0x15d0a routes`
- `host-fetched font descriptor streams route through 0x15d0a`
- `host-fetched 0x15d0a current-record resource object feeds fixed-record render`
- `0x16c14-modeled downloaded font replacement bookkeeping`
- `0x16c14 routes installed font resource through 0x1bc38 slot`
- `0x16c14-modeled downloaded font free-slot bookkeeping`
- `0x16c14-modeled downloaded font no-slot budget skip`
- `0x16fae-modeled font resource validation and symbol-byte staging`
- `0x16fae table-driven validation predicates populate staged header fields`
- `0x17026/0x1719c-modeled font resource allocation and header initialization`
- `ESC )s80W resource stream installs 0x1719c payload through 0x16c14`
- `resource payload stream ties ROM parser dispatch to 0x16c14 install`
- `host-fetched resource payload stream installs selected 0x1719c font`
- `host-fetched font control state drives resource payload stream`
- `0x16c14-installed 0x1719c payload dispatches as bit-30 resource form`
- `0x1719c-backed inline payload dispatches through 0x14c64`
- `0x16fae/0x1719c-backed inline payload maps, queues, and renders one fixed record`
- `host-fetched 0x1719c payload metrics feed d4ac span rows`
- `host-fetched 0x1719c payload metrics feed d8fc span rows`
- `0x16fae/0x1719c-backed type-2 inline payload maps constructed compact renderer
  records`
- `host-fetched type-2 0x1719c payload metrics feed d4ac and d8fc span rows`
- `0x16498-backed downloaded character object renders segmented-wide compact row`
- `downloaded character stream ties ROM parser dispatch to rendered object`
- `host-fetched downloaded character stream reaches rendered object`
- `host-fetched downloaded character object feeds 0x1ed84 and 0x1ef6a`
- `host-fetched printable byte uses installed downloaded glyph page object`
- `combined host-fetched font download stream prints installed glyph`
- `host-fetched font control stream feeds descriptor and character payload state`

## Field Groups

Canonical command selection:

- `0x782f2e`: current downloaded font id. Handler `0x15a56` writes the
  absolute parsed `ESC *c#D` word and maps `-32768` and larger unsigned
  overflow to `0x7fff`.
- `0x782f30`: current character/code word. Handler `0x15a18` writes the
  absolute parsed `ESC *c#E` word with the same `0x7fff` clamp.
- `0x78299e`: parser record cursor. `0x15a56`, `0x15a18`, `0x15d0a`,
  `0x16c14`, and `0x16df6` rewind it by six bytes before reading the current
  six-byte parsed record.
- `0x782a92`: parser/device mode byte. When it equals `2`, `0x15d0a` rejects
  descriptor processing and `0x16c14` skips payload bytes; `0x16df6` also
  suppresses font-control values `0`, `1`, `2`, `3`, and `6`.

Canonical current-record pool:

- `0x782640..0x782776`: 32 downloaded-font records, 10 bytes each.
- record `+0x00`: current font/resource id.
- record `+0x02`: flag byte/word area. `0x16c14` clears bits `5`, `6`, and
  `7` on install. `0x17108` sets bit `6`, and `0x17150` clears bit `6`.
- record `+0x06`: allocated payload pointer.
- `0x782782`: unmarked/current downloaded-font count.
- `0x782786`: marked/current downloaded-font count.

Canonical candidate-list state:

- `0x78278e`: total candidate count. `0x16c14` increments it after a
  successful install.
- `0x782790` and `0x782796`: class-one counters incremented when installed
  payload byte `+0x20` equals `1`.
- `0x782798` and `0x78279e`: class-zero counters incremented when installed
  payload byte `+0x20` is not `1`.
- `0x7827a0`, `0x7827ac`, `0x7827b0`, and `0x7827b4`: candidate-window
  cursors shifted by `0x1bc38` and by the class-one branch of `0x16c14`.
- candidate longword bit `30`: renderer offset-table/resource form. The
  `ESC )s80W` fixture installs candidate longword `0x40000000`.
- candidate longword bit `26`: class/selection flag copied later into the
  current-font context by `0x144d2`.

Parser scratch and staged resource header:

- `0x783140`: remaining payload byte budget. `0x15d0a` and `0x16c14` load it
  from the parsed `W` count; `0x1599c`, `0x168dc`, and `0x16942` decrement it
  while consuming payload bytes.
- `0x782862`: staging-record pointer, set by `0x17026` to `0x7827de`.
- `0x7827de`: staged sparse font-resource header copied by `0x1719c`.
- `0x7827ba`: payload unit count. `0x17362(0)` writes `0x80`; `0x17362(1)`
  and `0x17362(2)` write `0x100`.
- `0x782842..0x782851`: optional symbol bytes copied by `0x16fae`.
- `0x782856`: optional symbol byte count.

Continuation/cache state:

- `0x7827c6`: continuation flag set to `1` when a payload reader exhausts
  the byte budget before the copy is complete.
- `0x7827ca`: saved destination pointer for a resumed copy.
- `0x7827ce`: saved trailing-plane destination pointer for split-plane copies.
- `0x7827d2`: saved linear remaining count.
- `0x7827d6` and `0x7827d8`: saved split-plane counters.
- `0x7827da`: saved payload pointer used by descriptor continuation selector
  status `2`.
- `0x7827c8`: saved glyph/table index used by continuation helpers
  `0x15b9a` and `0x15c4c`.

Renderer-facing allocated payload fields:

- payload `+0x00`: resource record type. `0x17026` writes long `0x15` before
  allocation; `0x1719c` copies it into the allocated payload.
- payload `+0x04`: allocation size in 64-byte units. The tested type-0 header
  allocates `10`; type-2 allocates `18`.
- payload `+0x08`: fixed word `0x004a`, the start of the glyph pointer table
  for offset-table resources.
- payload `+0x0c`: resource type/class byte written by `0x17362`.
- payload `+0x0e`, `+0x10`, `+0x12`, `+0x14`, `+0x16`, `+0x18`, `+0x1a`,
  `+0x20`, `+0x21`, `+0x22`, `+0x24`, `+0x26`, `+0x28`, `+0x2a`, `+0x2c`,
  `+0x2f`, `+0x30`, and `+0x31`: sparse descriptor fields copied by
  `0x1719c`.
- payload `+0x38`: optional-symbol block offset when `0x782856 != 0`.
- glyph pointer table entry: relative offset from payload base to a
  downloaded character object, for example table entry `0x00de` points to
  record delta `0x0500` in the `ESC )s2193W` fixture.
- fixed-record table entry: eight bytes at payload `+0x40 + 8 * glyph`. The
  `0x16606` current-record fixture installs glyph `0x21` at payload-relative
  offset `0x48` with record `02 03 04 00 00 00 02 00`, where bytes `+0/+1`
  are width/rows and long `+4` points to bitmap delta `0x0200`.
- payload bytes `+0x2b`, `+0x2c`, and `+0x2d`: unflagged span metrics
  consumed by `0xd4ac` when the installed payload is used as a fixed-record
  context. The `ESC )s80W` fixture leaves them as `0`, `0`, and `0x20`,
  producing high-y `26` and rendered text-span rows `10..12`.
- payload words `+0x16`, `+0x18`, and `+0x1a`: flagged span metrics consumed
  by `0xd8fc` when the installed bit-30 payload is used as a downloaded
  offset-table context. The same `ESC )s80W` fixture copies them as `4`, `4`,
  and `5`, producing high-y `16` and segment-list key `0x0406`.

Unknown:

- Manual names for every validation-table predicate feeding `0x16fae` are not
  complete, even though the table-driven fixture pins all staged field writes.
- Split-plane and error-exit variants for the `0x15c4c` downloaded-font-resource
  resume helper still need page-render fixtures. The even-span fixed-record
  resume path is now page-visible.
- The complete soft-font grammar is not exhaustively proven for every legal
  PCL descriptor form and every metric-byte combination.

## Command Dispatch And Descriptor Route

`0x11f96` is the `ESC )s#W` / `ESC (s#W` payload selector. It reads the parsed
count from the six-byte command record:

- count `0`: schedules delayed handler `0x15d0a`.
- nonzero count: schedules delayed handler `0x16c14`.

The parser trace fixtures show the same dispatch path for `ESC )s0W`,
`ESC )s80W`, and `ESC )s2193W`: handlers
`0x11eb6,0x12008,0x11ff6,0x11f96` with modes `1,4,13,0`.

`0x15d0a` treats zero-count `W` as a descriptor packet, not as an empty skip:

- `0x15d12..0x15d3a`: rewinds `0x78299e`, reads the parsed count, and stores
  the absolute byte budget in `0x783140`.
- `0x15d3a..0x15d54`: rejects budgets below `3` and parser mode `2`.
- `0x15d56..0x15d6a`: reads descriptor byte `0` through `0x1599c` and accepts
  only value `4` through validator `0x169f6`.
- `0x15d6c..0x15d7a`: reads descriptor byte `1`; helper `0x16a10` maps zero
  to status `1` and nonzero to status `2`.
- `0x15d84..0x15dc6`: status `1` scans the current-record pool through
  `0x172c0`, resolves the payload through `0x1b4c0`, tests object bit `30`,
  and dispatches bit-30 records to `0x16498`.
- `0x15e3c..0x15e46`: the same status `1` route sends bit-30-clear records
  to `0x16606`.
- `0x15de8..0x15e28`: status `2` requires continuation flag `0x7827c6 == 1`,
  resolves saved payload `0x7827da`, and dispatches bit-30 records to
  `0x15b9a`.
- `0x15e5c..0x15e68`: status `2` sends bit-30-clear records to `0x15c4c`.
- `0x15dcc..0x15dd2`: all exits drain the remaining `0x783140` bytes through
  `0x12328`.

Fixture values:

- descriptor `04 00 aa bb` with current id `0x1234` routes to current-record
  payload `0x456789`, sees object bit `30`, and dispatches handler `0x16498`.
- host-fetched descriptor `04 00 02 03 04 00 aa 55 f0 0f c3 3c ...` with
  current id `0x1234` routes to current-record payload `0x000100`, sees bit
  `30` clear, dispatches handler `0x16606`, installs fixed-record glyph
  `0x21`, and renders that glyph through the page-record bridge.
- descriptor `04 01 cc` with continuation flag set routes to saved payload
  `0x000100`, sees bit `30` clear, dispatches handler `0x15c4c`, resumes
  bitmap copy at saved destination `0x000302`, clears continuation state, and
  renders the completed fixed-record glyph.
- descriptor kind `3` is rejected by `0x169f6` and drained without routing.

## Resource Payload Installation

`0x16c14` owns the nonzero `W` resource/character payload path:

- `0x16c1c..0x16c3e`: rewinds `0x78299e`, stores the absolute count in
  `0x783140`.
- `0x16c44..0x16c68`: mode `0x782a92 == 2`, a full current-record scan, or a
  full candidate pool sends the path to budget skip through `0x12328`.
- `0x16c52..0x16c66`: `0x172c0` scans the 32 current records and returns
  status `0` existing, `1` free, or `2` no slot.
- `0x16c80..0x16c92`: existing records release the old payload through
  `0x1887a`.
- `0x16ca4..0x16cb6`: `0x17026` validates, allocates, and initializes a
  payload. Failure falls back to byte-budget skip.
- `0x16cb8..0x16cc8`: `0x1bc38` inserts the new payload into the candidate
  list and returns the candidate slot pointer in `D7`.
- `0x16cca..0x16cf8`: candidate flags are normalized: bit `3` is cleared,
  bits `28..29` are cleared by mask `0xcfffffff`, bit `6` is set, bit `7` is
  cleared, and bit `2` follows payload byte `+0x0c == 2`.
- `0x16cf8..0x16d5e`: payload byte `+0x20 == 1` increments class-one
  counters and shifts class-one cursors; other values increment class-zero
  counters.
- `0x16d6e..0x16d9c`: the current-record slot receives id `0x782f2e`, clears
  record flags bits `5`, `6`, and `7`, and stores the new payload pointer at
  record `+0x06`.
- `0x16da0..0x16dac`: installed counters `0x78278a` and `0x782782`
  increment, then `0x1b04c` refreshes font selection bookkeeping.

The `ESC )s80W` fixture proves the parser-to-install boundary:

- parsed record `80 57 00 50 00 00`.
- delayed handler `0x16c14`.
- payload offset `6`, length `80`, and budget `80`.
- `0x16fae` consumes `64` descriptor bytes and leaves budget `16`.
- `0x17026`/`0x1719c` allocate size `10`.
- `0x16c14` installs candidate longword `0x40000000` at the class-one
  candidate list head.
- `0x14c64` later dispatches that candidate as an offset-table resource,
  selecting symbol `0x1234` and range `0x0000..0x007f`.

The same fixture path from host fetch drains the full `ESC )s80W` stream from
the modeled `0xa904` ring source and reaches the same restored record,
validation status, allocation size, candidate longword, and selected
`0x14c64` dispatch.

The composed metric fixture reuses that host-fetched `ESC )s80W` payload as a
selected fixed-record context, prints `!`, and drives `0xd4ac` from the copied
payload bytes. A companion fixture uses the same host-fetched payload as a
bit-30 downloaded-offset-table context, installs a small glyph pointer for
printable `!`, and drives `0xd8fc` from the copied payload words. Together
they prove:

- parser handlers `0x11eb6`, `0x12008`, `0x11ff6`, and `0x11f96`;
- restored record `80 57 00 50 00 00`;
- payload length `80`;
- installed candidate longword `0x40000000`;
- payload metric bytes `+0x2b = 0`, `+0x2c = 0`, `+0x2d = 0x20`;
- `0xd4ac` high-y `26`;
- queued segment-list key `0xa406`; and
- visible segment-list rows `10..12`;
- payload metric words `+0x16 = 4`, `+0x18 = 4`, `+0x1a = 5`;
- downloaded-offset-table glyph pointer table entry `0x00ce`, record delta
  `0x0180`, and mode-1 glyph bitmap `f0 f0 f0`;
- `0xd8fc` high-y `16`;
- queued segment-list key `0x0406`; and
- bucket-1 render rows containing the span before the compact glyph.

A type-2 companion changes the setup byte in the host-fetched descriptor so
`0x17362` writes payload byte `+0x0c = 2`, payload units `0x100`, allocation
size `18`, and candidate longword `0x44000000`. The fixture
`host-fetched type-2 0x1719c payload metrics feed d4ac and d8fc span rows`
then reuses the copied payload metric fields with type-2 glyph shapes:

- unflagged host byte `#` maps to fixed-record glyph `3`, record
  `11 03 04 00 00 00 01 20`, selector `0x1000`, and visible wide glyph rows;
- the same payload bytes `+0x2b = 0`, `+0x2c = 0`, and `+0x2d = 0x20` feed
  `0xd4ac`, high-y `26`, segment-list key `0xa406`, and visible span rows
  `10..12`;
- flagged host byte `!` maps through a synthetic pointer-table entry
  `0x00ce -> 0x0300`, record `00 00 00 00 0c 01 00 03 00 04 00 00`, and
  bitmap `f0 f0 f0`; and
- the same payload words `+0x16 = 4`, `+0x18 = 4`, and `+0x1a = 5` feed
  `0xd8fc`, high-y `16`, segment-list key `0x0406`, and visible span rows
  before the compact glyph.

## Descriptor Validation And Payload Header

`0x16fae` is a table-driven descriptor validator:

- `0x16fb8`: starts at validation table `0x16eae`.
- `0x16fc0..0x16fd4`: each 8-byte entry calls a reader and predicate helper.
- `0x16fdc..0x16fe2`: after 32 accepted entries, descriptor validation is
  complete.
- `0x16fe4..0x17016`: copies up to 16 optional symbol bytes from `0x1599c`
  into `0x782842` while budget remains.
- `0x17016..0x1701c`: writes the copied symbol count to `0x782856` and
  returns success.

The table-driven fixture consumes 64 bytes and stages these renderer-facing
fields:

- `+0x0c = 0`
- `+0x10 = 0x007f`
- `+0x12 = 0x0006`
- `+0x14 = 0x0009`
- `+0x16 = 0x0004`
- `+0x18 = 0x0004`
- `+0x1a = 0x0005`
- `+0x20 = 1`
- `+0x21 = 1`
- `+0x22 = 0x1234`
- `+0x24 = 0x41a0`
- `+0x28 = 0x2aaa`
- `+0x2a = 0x80`
- `+0x2c = 0x0020`
- `+0x2f..+0x31 = ab f9 cd`
- optional symbols `41..50`

`0x17362` sets the staged type and payload units. Type `0` writes byte
`+0x0c = 0` and units `0x80`; type `2` writes byte `+0x0c = 2` and units
`0x100`; invalid type `3` returns failure.

`0x17026` writes staged long `+0 = 0x15`, computes allocation size
`((0x7827ba << 2) + 0x9b) >> 6`, allocates class `1` with `0x40` alignment,
and calls `0x1719c`. `0x1719c` copies the sparse header into the allocated
payload, writes word `+0x08 = 0x004a`, and, if symbols exist, writes payload
`+0x38 = 0x4a + 4 * 0x7827ba`, followed by count and bytes.

Fixture values:

- type-0 units `0x80` allocate size `10`.
- type-2 units `0x100` allocate size `18`.
- type-0 optional-symbol offset is `0x024a`.
- type-2 optional-symbol offset is `0x044a`.

## Downloaded Character Payload And Rendering

The character-object path uses `0x16498` after a descriptor/current-record
route or after a nonzero character payload. The current complete page-visible
fixture is `ESC )s2193W`:

- parser record `80 57 08 91 00 00`.
- delayed handler `0x16c14`.
- payload offset `8`, length `0x0891`, budget `0x0891`.
- current character from `0x782f30` is `0x25`.
- installed table entry is `0x00de`.
- downloaded character record delta is `0x0500`.
- glyph record bytes are `00 00 00 00 0c 01 00 81 00 88 00 00`.
- bitmap offset is `0x050c`.
- bitmap size is `0x0891`.
- span is `0x11`, width is `0x88`, rows are `0x81`, and the split-plane
  reader path is selected.

`0x168dc` is the linear payload reader. It consumes bytes through `0xa904`,
normalizes payload control `1a 58` through `0xd99a`, writes stored bytes to
`A4`, and saves continuation state when `0x783140` reaches zero before the
copy is complete.

`0x16942` is the split-plane reader. It writes row-prefix bytes through `A4`,
trailing-plane bytes through `A3`, also normalizes `1a 58`, and saves
`0x7827ca`, `0x7827ce`, `0x7827d6`, and `0x7827d8` for continuation.

The installed glyph resolves as source kind `downloaded-pointer`, entry
`0x0500`, bitmap `0x050c`, mode `1`, rows `0x81`, width `0x88`, span
`0x11`, and render span `0x11`. Rendering the segmented-wide compact object
selects:

- compact object prefix `00 00 00 00 30 03 00 01 25 01 66 01`.
- selector `0x3003`.
- context slot `3`.
- renderer target `0x1effe`.
- compact mode `3`.
- full chunk helper `0x2f27c`.
- one full 16-byte chunk and one remainder byte.
- destination x `22`, y `6`, and `$a001 = 0x16`.

## Downloaded Resource Object And Rendering

The bit-30-clear current-record path uses `0x16606` after a descriptor
status-1 route. The fixture
`host-fetched 0x15d0a current-record resource object feeds fixed-record
render` covers:

- host-fetched command prefix `ESC )s0W`;
- parser handlers `0x11eb6`, `0x12008`, `0x11ff6`, and `0x11f96`;
- restored descriptor record `80 57 00 00 00 00`;
- descriptor byte budget `0x14`;
- current-record payload `0x000100` with object bit `30` clear;
- descriptor route handler `0x16606`;
- stale continuation state cleared before the install;
- selected current character `0x21`;
- fixed-record table entry at payload `+0x48`;
- installed record `02 03 04 00 00 00 02 00`;
- copied bitmap bytes `aa 55 f0 0f c3 3c` at payload delta `0x0200`;
- active map dispatch through `0x14c64` / `0x14e24` / `0x14eb6`;
- source object glyph `1`, width `2`, rows `3`, context slot `3`;
- page-record object prefix `00 00 00 00 00 03 00 01 01 66 01`;
- `0x1edc6` context-slot prefix `(0, 0, 0, 0x000100)`; and
- rendered mode-0 fixed-record rows beginning at x `22`, y `6`.

This closes the current-record bit-30-clear `0x15e3c..0x15e46` middle edge for
one page-visible fixed-record resource object.

The companion fixture
`host-fetched 0x15d0a continuation resource object resumes fixed-record render`
starts with the same host-fetched descriptor but gives `0x16606` only budget
`0x10`. That copies bitmap bytes `aa 55`, writes the same fixed-record entry
`02 03 04 00 00 00 02 00` at payload `+0x48`, and saves continuation fields
equivalent to:

- `0x7827c6 = 1`;
- `0x7827da = 0x000100`;
- `0x7827c8 = 0x21`;
- `0x7827ca = 0x000302`; and
- `0x7827d2 = 4`.

The next host-fetched descriptor stream `ESC )s0W 04 01 cc` takes the
`0x15d0a` status-`2` route through `0x15e5c..0x15e68`, dispatches handler
`0x15c4c`, reloads the fixed-record table entry from payload `+0x48`, copies
the remaining bytes `f0 0f c3 3c` through the linear `0x16874`/`0x168dc` path
at destination `0x000302`, clears `0x7827c6`, `0x7827da`, `0x7827c8`,
`0x7827ca`, `0x7827ce`, `0x7827d2`, `0x7827d6`, and `0x7827d8`, then renders
the same source object, page-record object prefix, bridge context slots, and
three mode-0 rows as the one-piece `0x16606` fixture. This closes the
bit-30-clear continuation middle edge for one even-span fixed-record resource
object.

## End-To-End Downloaded Glyph Path

The strongest current byte-stream fixture is:

```text
ESC *c4660d37e5F
ESC )s2193W <0x0891 payload bytes>
%
```

The modeled `0xa904` ring source drains all bytes. The control part routes
through handlers `0x11eb6`, `0x11ec8`, `0x11eda`, `0x15a56`, `0x15a18`, and
`0x16df6`:

- `ESC *c4660d` stores current font id `0x1234`.
- `37e` stores current character `0x25`.
- `5F` dispatches to `0x16e86`, marks the current record through `0x17108`,
  and changes counters from `0x782782/0x782786 = 7/2` to `6/3`.

The payload part routes through `0x11eb6`, `0x12008`, `0x11ff6`, and
`0x11f96`, restores `0x16c14`, installs the `0x25` glyph object above, and
leaves the delayed pending record cleared.

The printable part is one byte `%` and handler `0xd04a`. The fixture maps
host byte `0x25` to glyph `0x25`, builds an unflagged source with glyph entry
`0x0500`, rows `0x81`, width byte `0x11`, x `22`, y `22`, and context slot
`3`. `0x12f2e`/`0x1387c` queues two segmented page-record objects:

- bucket `9`, segment `1`, object prefix
  `00 00 00 00 30 03 00 01 25 01 66 01`.
- bucket `1`, segment `0`, object prefix
  `00 00 00 00 30 03 00 01 25 00 66 01`.

The page-record bridge `0x1edc6` preserves the bucket root, leaves rule and
fixed lists empty, and copies the context-slot prefix. Render entry
`0x1ed84`/`0x1ef6a` uses call order `0x1ef86`, `0x1efc2`, `0x1f446`,
`0x1f756`, dispatches the compact object to `0x1effe`, and produces the same
downloaded segmented-wide row as the direct compact-object renderer.

## Writers

- `0x15a56` writes `0x782f2e`.
- `0x15a18` writes `0x782f30`.
- `0x16df6` dispatches font-control values and calls `0x17108`/`0x17150` for
  mark/unmark.
- `0x17108` sets current-record bit `6` and transfers one count from
  `0x782782` to `0x782786`.
- `0x17150` clears current-record bit `6` and transfers one count from
  `0x782786` to `0x782782`.
- `0x15d0a` writes `0x783140`, consumes descriptor bytes through `0x1599c`,
  and routes to `0x16498`, `0x16606`, `0x15b9a`, or `0x15c4c`.
- `0x16c14` writes `0x783140`, current-record ids/payload pointers,
  candidate flags, candidate counters, and installed counts.
- `0x16fae` writes staged descriptor fields, optional symbol bytes, and
  optional symbol count.
- `0x17362` writes staged type byte and payload units.
- `0x17026` writes staged type/size and allocates the payload.
- `0x1719c` writes allocated payload header fields and optional symbol block.
- `0x168dc` and `0x16942` write glyph bitmap bytes and continuation state.
- `0x16606` clears stale continuation state, writes fixed-record table entries
  in bit-30-clear resource payloads, copies bitmap bytes through `0x16874`,
  and refreshes selected contexts through `0x14c64` when the payload matches
  an active primary or secondary context.
- `0x15c4c` resumes bit-30-clear fixed-record bitmap copies from saved
  continuation fields, updates or clears that continuation state, and leaves
  the completed fixed-record payload renderable through the same active
  context path.
- `0x12f2e`/`0x1387c` write compact text bucket objects for the installed
  glyph.

## Readers And Consumers

- `0x11f96` reads the parsed `W` count and schedules delayed font handlers.
- `0x172c0` reads the current-record pool by current font id.
- `0x1b4c0` resolves payload pointers from current records or continuation
  state.
- `0x16606` reads `0x7827c6`, `0x7827da`, `0x7827c8`, `0x7827ca`,
  `0x7827ce`, `0x7827d2`, `0x7827d6`, `0x7827d8`, current character
  `0x782f30`, selected payload base `0x78285e`, and byte budget `0x783140`.
- `0x15c4c` reads saved payload `0x7827da`, saved glyph/table index
  `0x7827c8`, saved destination `0x7827ca`, saved remaining count `0x7827d2`,
  and the fixed-record table entry in the selected payload.
- `0x1bc38` reads payload class byte `+0x20` and inserts candidate longwords.
- `0x14c64` consumes installed candidate longwords and payload header fields
  to build active glyph maps.
- `0x1393a` consumes the active map and selected context to build printable
  source objects.
- `0x12f2e`, `0x1edc6`, `0x1ed84`, and `0x1ef6a` consume the installed glyph
  source and compact objects through the page-record/render pipeline.

## Output Effect

Downloaded font commands do not draw until a later printable byte selects an
installed glyph. The visible effect is that the same host byte can resolve to
a payload-backed glyph record instead of a built-in glyph. In the end-to-end
fixture, printable `%` draws glyph `0x25` from downloaded object record
`0x0500`, with a segmented-wide compact selector `0x3003` and one visible row
beginning at x `22`. In the `0x16606` current-record fixture, printable `!`
maps to fixed-record glyph `1` from payload record `0x48`, queues selector
`0x0003`, and renders three mode-0 rows beginning at x `22`. The companion
`0x15c4c` fixture proves that splitting the same bitmap across two descriptor
packets produces the same table entry, source object, page-record bridge, and
rendered rows after continuation state is cleared.

## Confidence

High for command dispatch, delayed-record restoration, current id/current
character ownership, current-record mark/unmark, `0x16c14` install
bookkeeping, table-driven descriptor staging, `0x17026`/`0x1719c` allocation
headers, the complete downloaded-character-to-rendered-row fixture, and the
`0x16606` and `0x15c4c` bit-30-clear resource-object-to-rendered-row fixtures.

Medium for the full PCL soft-font grammar because the validation table is
executable but not every predicate has a manual-facing semantic name, and not
every legal metric combination has a parser-produced page comparison.

Medium for bit-30-clear fixed-record dispatch from a `0x1719c` payload: the
isolation fixture proves `0x14e24`/`0x14eb6` map construction and rendering,
and the `0x16606` descriptor fixture proves a current-record bit-30-clear
resource object reaches the same fixed-record render path. The normal
integrated `0x16c14` resource install shown here still sets bit `30` and
therefore selects the offset-table path.

## Reproduction Contract

A byte-stream renderer must preserve:

- command-family parser state for `ESC *c#D`, `ESC *c#E`, `ESC *c#F`, and
  `ESC )s#W` / `ESC (s#W`;
- current font id `0x782f2e` and current character `0x782f30`;
- the 32 current downloaded-font records and record flag bit `6`;
- current-record counters `0x782782` and `0x782786`;
- candidate counters/cursors affected by `0x16c14` and `0x1bc38`;
- payload byte budget `0x783140` and payload control normalization
  `1a 58 -> 0x00`;
- staged descriptor fields copied by `0x16fae` and `0x1719c`;
- continuation state for partial payload reads;
- the `0x15c4c` resume contract for saved payload, glyph/table index,
  destination pointer, remaining byte count, and continuation clearing;
- bit `30` on candidate longwords, because it chooses offset-table resource
  rendering rather than fixed-record rendering;
- glyph table entry, glyph record bytes, bitmap offset, span, rows, width,
  split-plane layout, fixed-record layout, and compact selector bits;
- the page-record bridge through `0x1edc6` and active render entry
  `0x1ed84`/`0x1ef6a`.

## Remaining Edges

- `0x16fae..0x17016`: all 32 validation slots are executable, but
  manual-facing names for every predicate and descriptor field are still
  incomplete.
- `0x16498..0x16942`: the split-plane segmented-wide payload path is
  page-visible; linear and alternate mode combinations still need the same
  parser-produced page comparison.
- `0x15c4c`: the even-span fixed-record resume route is page-visible; the
  split-plane continuation counters and failure/release exits still need
  fixture coverage.
- `0x14c64..0x14eb6`: the `0x1719c` bit-30-clear fixed-record path is an
  isolation control. The integrated `ESC )s80W` install path currently proves
  the bit-30 offset-table form.
- The span-metric fields documented in `notes/font-context-metrics.md` are now
  tied to installed payload headers for the `0xd4ac` and `0xd8fc` type-0 and
  type-2 fixtures, but broader downloaded/inline metric-byte values and
  rejection/error forms still need parser-produced page evidence.
