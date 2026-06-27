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
- `generated/disasm/ic30_ic13_font_fixed_record_release_017a24.lst`
- `generated/disasm/ic30_ic13_font_candidate_object_alloc_01bc38.lst`
- `notes/font-context-metrics.md`

Primary fixtures:

- `0x15d0a-modeled font descriptor route`
- `0x121cc/0x15d0a-modeled font descriptor command stream`
- `font descriptor stream ties ROM parser dispatch to 0x15d0a routes`
- `host-fetched font descriptor streams route through 0x15d0a`
- `host-fetched 0x15d0a current-record resource object feeds fixed-record render`
- `host-fetched 0x15d0a continuation resource object resumes fixed-record render`
- `0x15c4c failed resource resume releases fixed-record object`
- `0x17d7c releases extended fixed-record table with secondary refresh`
- `0x17d7c delegates bit-30 release to offset-table helper`
- `host-fetched 0x15d0a split-plane continuation resource object resumes
  fixed-record render`
- `0x16c14-modeled downloaded font replacement bookkeeping`
- `0x16c14 routes installed font resource through 0x1bc38 slot`
- `0x16c14-modeled downloaded font free-slot bookkeeping`
- `0x16c14-modeled downloaded font no-slot budget skip`
- `0x16fae-modeled font resource validation and symbol-byte staging`
- `0x16fae table-driven validation predicates populate staged header fields`
- `0x17026/0x1719c-modeled font resource allocation and header initialization`
- `ESC )s80W resource stream installs 0x1719c payload through 0x16c14`
- `ESC )s80W invalid resource type fails validation before allocation`
- `ESC )s80W reversed resource range fails validation before allocation`
- `ESC )s80W additional validation predicate failures skip allocation`
- `ESC )s#W validation failures preserve following printable output`
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
- `host-fetched type-1 0x1719c payload metrics feed d4ac and d8fc span rows`
- `host-fetched metric variant changes d4ac gate and d8fc rows`
- `host-fetched clamped metric variant changes d4ac gate and d8fc rows`
- `host-fetched lower-bound metric variant suppresses d4ac and d8fc spans`
- `host-fetched upper-bound metric variant keeps d4ac span but suppresses d8fc`
- `descriptor metric fields match across inline and resource contexts`
- `legal descriptor metric value matrix drives d4ac and d8fc consumers`
- `legal descriptor metric boundary values drive d4ac and d8fc consumers`
- `0x16498-backed downloaded character object renders segmented-wide compact row`
- `downloaded character stream ties ROM parser dispatch to rendered object`
- `host-fetched downloaded character stream reaches rendered object`
- `host-fetched downloaded character object feeds 0x1ed84 and 0x1ef6a`
- `host-fetched linear downloaded character stream renders through 0x168dc`
- `host-fetched downloaded character payload control reaches wide render`
- `host-fetched even-span wide downloaded character renders through 0x1f0d2`
- `host-fetched row-0x80 downloaded character remains short compact`
- `0x16498 replacement allocation failure partial and rejected downloaded character
  exits preserve state`
- `0x16498 no-install exits preserve following printable output`
- `0x16498 status-2 partial installs remain printable`
- `host-fetched even-span downloaded glyph FF publishes rendered page record`
- `downloaded normal row-0x80 and segmented glyph FF publications render page records`
- `host-fetched downloaded glyph composes with rule and raster through 0x1ef6a`
- `parser-driven downloaded glyph rule raster stream composes through 0x1ef6a`
- `host-fetched segmented downloaded character renders through 0x1f1f0`
- `host-fetched split-plane segmented downloaded character renders through
  0x1f1f0`
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

Published page-record state:

- Canonical bucket array copied by `0xff1e`: normal downloaded selector
  `0x0003` publishes bucket `1`; linear-segmented selector `0x2003` publishes
  buckets `1` and `9`; segmented-wide selector `0x3003` publishes buckets
  `1` and `9`; even-span wide selector `0x1003` publishes bucket `1`.
- Canonical side lists copied by `0xff1e`: the covered downloaded-glyph
  publication fixtures leave rule and fixed lists empty.
- Canonical context slots copied by `0xff1e`: the covered downloaded-glyph
  publication fixtures preserve `(0, 0, 0, 0)`.
- Parser scratch: delayed `ESC )s#W` records restored by
  `0x11f96`/`0x16c14`, including `80 57 00 06 00 00`,
  `80 57 01 02 00 00`, and `80 57 00 12 00 00`.
- Derived/cache render state: `0x1ed84` copies published-record work words
  into render words `+0x10/+0x16`; `0x1ef6a` consumes those words to choose
  bucket `1` or `9` and derive band rows and destination base.
- Firmware bookkeeping: `0xff1e` clears the current page root and sets the
  publication flag after copying the record.
- Unknown for this checkpoint: downloaded-glyph publication cross-products
  outside the documented normal bucket-1, row-`0x80` short bucket-1,
  linear-segmented bucket-9, segmented-wide bucket-1/bucket-9, and even-span
  wide bucket-1 streams. The remaining row-count risk is no longer the
  `0x80`/`0x81` selector boundary itself; it is non-boundary row counts inside
  the same selector families, character modes other than the covered mode-1
  bitmap records, and no-install/partial-install publication siblings.
  Fixture `downloaded normal row-0x80 and segmented glyph FF publications
  render page records` covers the row-`0x80` bucket-1 publication sibling for
  the `0x80`/`0x81` selector threshold.
  The covered publication fixtures are
  `downloaded normal row-0x80 and segmented glyph FF publications render page records`,
  `host-fetched even-span downloaded glyph FF publishes rendered page record`,
  `published downloaded glyph segmented buckets render across bands`, and
  `0x1eba4 scheduler band words render published downloaded glyph`.

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
- downloaded character object `+0x04`: bitmap delta `0x0c` written by
  `0x16498`.
- downloaded character object `+0x05`: glyph bitmap mode. The modeled page-visible
  downloaded-character fixtures use mode `1`; fixture `0x16498 replacement allocation
  failure partial and rejected downloaded character exits preserve state` proves mode
  `0` exits as `unsupported-record-shape` without changing the header.
- downloaded character object `+0x06/+0x08`: row count and width copied from
  the current character descriptor; the `ESC )s258W` segmented fixture uses
  rows `0x0081` and width `0x0010`.
- downloaded character object `+0x0c..`: copied bitmap bytes. The `ESC )s258W`
  fixture copies `0x0102` linear bytes through `0x168dc`, with the final
  row bytes `f0 0f` at bitmap delta `0x0100`.
- split-plane downloaded character object bitmap layout: `0x16942` stores all
  row-prefix bytes first, followed by one trailing byte per row. The
  `ESC )s387W` fixture installs row `128` as A2 bytes `f0 0f` at offset
  `0x0100` and A3 byte `aa` at trailing offset `0x0080`.
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
- metric-variant descriptor bytes: fixture `host-fetched metric variant
  changes d4ac gate and d8fc rows` changes the descriptor stream so `0x16fae`
  and `0x1719c` copy payload word `+0x2c = 0x0010` and word `+0x1a =
  0x0002`. The default payload's `+0x2d = 0x20` fails the `0xd4ac`
  page-extent gate at extent `40`; the variant `+0x2d = 0x10` queues the
  span, and the changed `+0x1a` moves `0xd8fc` high-y to `19` with
  segment-list key `0x3406`.
- clamped metric-variant descriptor bytes: fixture `host-fetched clamped
  metric variant changes d4ac gate and d8fc rows` lowers range/count word
  `+0x14` to `5`, sends an oversized rounded-metric input through `0x1757a`,
  and makes `0x1719c` copy payload word `+0x2c = 0x0014`. Byte `+0x2b`
  remains `0` for this payload family. The default `+0x2d = 0x20` fails the
  `0xd4ac` page-extent gate at extent `41`; clamped `+0x2d = 0x14` queues the
  span. The same descriptor copies `+0x18 = 0` and `+0x1a = 3`, moving
  `0xd8fc` high-y to `18` with segment-list key `0x2406`.
- lower-bound metric-variant descriptor bytes: fixture `host-fetched
  lower-bound metric variant suppresses d4ac and d8fc spans` writes first
  code `+0x16 = 0x0018`, range/count `+0x14 = 0x0600`, derived count
  `+0x18 = 0x05e7`, and rounded word `+0x2c = 0x1800`. These are
  parser-owned metric fields copied by `0x1719c`, with `+0x18` acting as a
  derived/cache value from `0x17430` and byte `+0x2b` remaining firmware
  bookkeeping at `0`. At cursor y `21`, `0xd4ac` reads byte `+0x2c = 0x18`,
  `0xd8fc` reads word `+0x16 = 0x0018`, and both exit
  `before-context-lower`; the compact glyph objects still queue and render.
- upper-bound metric-variant descriptor bytes: fixture `host-fetched
  upper-bound metric variant keeps d4ac span but suppresses d8fc` writes
  range/count `+0x14 = 0x0040`, derives `+0x18 = 0x003b`, and keeps rounded
  word `+0x2c = 0x0020`. At cursor y `21` and page extent `64`, unflagged
  `0xd4ac` still queues the default span object and rows, but flagged
  `0xd8fc` exits `beyond-page-extent` because `21 + 0x003b` crosses the page
  extent; its compact glyph remains queued and renderable.
- legal metric-value matrix: fixture
  `legal descriptor metric value matrix drives d4ac and d8fc consumers`
  groups small-rounded, clamped-rounded, midpoint-rounded, zero-rounded-offset,
  negative-offset, lower-bound, and upper-bound parser-produced descriptors.
  The zero-rounded-offset descriptor copies canonical `+0x14/+0x16 =
  0x0018/0x0004`, derived/cache `+0x18 = 0x0013`, and consumer fields
  `+0x1a/+0x2c = 0x0000/0x0000`; `d4ac` still emits the default span digest
  `67554ea70d7cfd9b11c0777e3cf65d51600a44301a4f93bd4d9b0c0fbc23c00e`,
  while `d8fc` publishes high-y `21` and row digest
  `47361fc76bd6284f9d764c0377a3fda64edd3944b5cb2dff72acfd2224bc25e8`. The
  midpoint descriptor copies `+0x14/+0x16/+0x18/+0x1a/+0x2c =
  0x0018/0x0004/0x0013/0x0007/0x0018`; `d8fc` updates high-y to `14` and
  leaves the compact-only glyph digest
  `1a73b5e7454202d800c69f626bcf34e7d0d583b459e04c0bd4250010bf3ba28a`.
  The negative-offset descriptor accepts input byte `0xfe`, which `0x1719c`
  copies as word `+0x1a = 0xfffe`; `d4ac` still emits the default span digest,
  while `d8fc` consumes that word as `65534`, computes high-y `-65513`, and
  renders row digest
  `72bfa14c2a84532e2bdf6fb8fddf26ed6904c49dcf4fdcb322592471b5d5b281`.

Unknown:

- Exact HP manual labels for the consumed-but-not-staged descriptor fields in
  the `0x16fae` table are still not all correlated, but every table entry now
  has a ROM-effect name in the validation ledger below.
- The `0x15c4c` status-0 copy-failure exit is fixture-backed through
  fixed-record release helper `0x17d7c`; the `0x17d7c` bit-30 delegate to
  `0x17a24` is fixture-backed for one active-secondary offset-table release.
  Fixed-record extended-table and secondary-refresh release are fixture-backed
  together. Current-record allocation-failure release through `0x1887a` is
  fixture-backed for the bit-30-clear extended fixed-record case.
- The complete soft-font grammar is not exhaustively proven for every legal
  PCL descriptor form. The metric producer-form boundary is now fixture-backed:
  inline/unflagged feeds `0xd4ac`, resource/flagged feeds `0xd8fc`, and the
  swapped forms fail at concrete map/render boundaries.

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
- split-plane descriptor `04 01 cc` with saved continuation counters reloads
  payload `0x000100`, sees fixed-record entry `03 02 04 00 00 00 02 00`,
  resumes the prefix destination `0x000303` and trailing-plane destination
  `0x000305` through `0x15c4c`, clears continuation state, and renders the
  odd-width fixed-record glyph.
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
  payload. Failure falls back to byte-budget skip after any existing-record
  release has already run.
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

The allocation-failure fixture
`0x16c14 allocation failure releases existing payload through 0x1887a` starts
with a current-record hit for id `0x1234`, record flags `0x40`, old payload
`0x123456`, and `allocation_ok = False`. Disassembly
`generated/disasm/ic30_ic13_font_resource_object_add_016c14.lst` places the
existing-record call to `0x1887a` at `0x16c80..0x16c92`, before the allocation
failure skip at `0x16ca4..0x16cb6`; the fixture therefore releases the old
payload and only then returns budget action `skip-allocation-failed`.

The release helper evidence is
`generated/disasm/ic30_ic13_font_resource_payload_link_01887a.lst`,
`generated/disasm/ic30_ic13_font_resource_release_018b92.lst`, and
`generated/disasm/ic30_ic13_font_resource_release_alt_018bf2.lst`. For the
bit-30-clear class-one fixture, `0x1887a` dispatches to `0x18bf2`, which calls
`0x18090` for 191 fixed-record characters because payload byte `+0x0e = 1`.
It clears the current-record id and payload, clears flag bits `4..7`,
decrements marked-record count `0x782786`, total counters `0x78278e` and
`0x78278a`, class-one counters `0x782796` and `0x782790`, and class-one
cursors `0x7827ac`, `0x7827b0`, and `0x7827b4` by four. It deletes the
matching candidate slot through `0x1bd2e`, clears matching continuation fields
`0x7827c6/da/c8/ca/ce/d2/d6/d8`, marks matching context-stack primary byte
`+8` and secondary byte `+9`, refreshes the matching secondary active context
through `0x179aa(1)`, and calls `0x1b04c`. No new candidate or record payload
is installed on this failure exit.

The same fixture path from host fetch drains the full `ESC )s80W` stream from
the modeled `0xa904` ring source and reaches the same restored record,
validation status, allocation size, candidate longword, and selected
`0x14c64` dispatch.

The invalid-resource-type sibling uses a full host-fetched `ESC )s80W` stream
whose descriptor bytes begin `00 01 02 03`. Parser dispatch walks `0x11eb6`,
`0x12008`, `0x11ff6`, and `0x11f96`; delayed restore reaches record
`80 57 00 50 00 00`; `0x16fae` fails validation entry `2` after four bytes;
`0x17026` reports allocation status `0`; and `0x16c14` leaves install state
`None`. No candidate or current-record payload is installed on this exit.

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

A type-1 companion follows the same parser-produced boundary with setup byte
`+0x0c = 1`, payload units `0x100`, allocation size `18`, and candidate
longword `0x40000000`. Fixture
`host-fetched type-1 0x1719c payload metrics feed d4ac and d8fc span rows`
uses the same fixed-record and pointer-table glyph shapes as the type-2 metric
fixture, but proves the type-1 header still feeds `0xd4ac` from bytes
`+0x2b`, `+0x2c`, and `+0x2d`, and `0xd8fc` from words `+0x16`, `+0x18`, and
`+0x1a`, with visible span rows.

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

The validation table at `0x16eae` is now named by ROM effect. The reader
helpers are `0x1599c` for unsigned bytes, `0x159b6` for signed bytes,
`0x159d4` for unsigned words, and `0x159f6` for signed words:

- Entry `0`, table `0x16eae`, `D5 = 1`: `0x159f6` plus pass predicate
  `0x17358` consumes signed descriptor word 1 without staging it.
- Entry `1`, table `0x16eb6`, `D5 = 2`: `0x1599c` plus `0x17358` consumes
  descriptor byte 3 without staging it.
- Entry `2`, table `0x16ebe`, `D5 = 3`: `0x1599c` plus `0x17362` validates
  font resource type, writes payload byte `+0x0c`, and sets payload units to
  `0x80` for type `0` or `0x100` for types `1` and `2`.
- Entry `3`, table `0x16ec6`, `D5 = 4`: `0x159f6` plus `0x17358` consumes a
  signed descriptor word without staging it.
- Entry `4`, table `0x16ece`, `D5 = 5`: `0x159d4` plus `0x173d0` writes
  payload word `+0x16` and rejects values greater than `0x1067`.
- Entry `5`, table `0x16ed6`, `D5 = 6`: `0x159d4` plus `0x173fe` writes
  payload word `+0x12` and accepts only `1..0x1068`.
- Entry `6`, table `0x16ede`, `D5 = 7`: `0x159d4` plus `0x17430` writes
  payload word `+0x14`, requires word `+0x16 <= value - 1`, and writes
  derived word `+0x18 = value - word(+0x16) - 1`.
- Entry `7`, table `0x16ee6`, `D5 = 8`: `0x1599c` plus `0x1749e` writes
  class byte `+0x20` and rejects values greater than `1`.
- Entry `8`, table `0x16eee`, `D5 = 9`: `0x1599c` plus `0x174cc` writes
  payload byte `+0x21` as `0` for zero input or `1` for any nonzero input.
- Entry `9`, table `0x16ef6`, `D5 = 10`: `0x159d4` plus `0x17502` writes
  symbol-set word `+0x22`.
- Entry `10`, table `0x16efe`, `D5 = 11`: `0x159d4` plus `0x1751a` writes
  payload word `+0x24`, capped at `0x41a0`.
- Entry `11`, table `0x16f06`, `D5 = 12`: `0x159d4` plus `0x1754a` writes
  payload word `+0x28`, capped at `0x2aaa`.
- Entry `12`, table `0x16f0e`, `D5 = 13`: `0x159d4` plus `0x1757a` writes
  payload word `+0x2c = min((value + 2) >> 2, word(+0x14)) << 2`.
- Entry `13`, table `0x16f16`, `D5 = 14`: `0x1599c` plus `0x17358` consumes
  a descriptor byte without staging it.
- Entry `14`, table `0x16f1e`, `D5 = 15`: `0x1599c` plus `0x175c2` copies
  the input byte to payload byte `+0x2f`.
- Entry `15`, table `0x16f26`, `D5 = 16`: `0x159b6` plus `0x175da` writes
  signed payload byte `+0x30`, clamped to `-7..7`.
- Entry `16`, table `0x16f2e`, `D5 = 17`: `0x1599c` plus `0x17612` copies
  the input byte to payload byte `+0x31`.
- Entries `17..20`, tables `0x16f36..0x16f4e`, `D5 = 18..21`: four
  `0x1599c` byte reads plus `0x17358` consume descriptor bytes without
  staging them.
- Entry `21`, table `0x16f56`, `D5 = 22`: `0x159b6` plus `0x1762a`
  sign-extends one byte and writes it to payload word `+0x1a`.
- Entry `22`, table `0x16f5e`, `D5 = 23`: `0x1599c` plus `0x17358` consumes
  a descriptor byte without staging it.
- Entries `23..24`, tables `0x16f66..0x16f6e`, `D5 = 24..25`: two
  `0x159f6` signed-word reads plus `0x17358` consume descriptor words without
  staging them.
- Entry `25`, table `0x16f76`, `D5 = 26`: `0x159d4` plus `0x17642` ignores
  the input value, clears payload word `+0x0e`, and writes range limit
  `+0x10 = 0x007f` for type `0` or `0x00ff` for nonzero type.
- Entry `26`, table `0x16f7e`, `D5 = 27`: `0x159d4` plus `0x17358` consumes
  a descriptor word without staging it.
- Entry `27`, table `0x16f86`, `D5 = 28`: `0x1599c` plus `0x17690` writes
  payload byte `+0x26`, but forces zero when capped word `+0x24 >= 0x41a0`.
- Entry `28`, table `0x16f8e`, `D5 = 29`: `0x1599c` plus `0x176c2` writes
  payload byte `+0x2a`, but clamps to `0x80` when word `+0x28 >= 0x2aaa`
  and the input is greater than `0x80`.
- Entries `29..31`, tables `0x16f96..0x16fa6`, `D5 = 30..32`: three
  `0x159d4` word reads plus `0x17358` consume descriptor words without
  staging them.

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

Failure fixtures now cover seven concrete predicate exits. Invalid type byte
`3` fails entry `2` after four consumed bytes, leaves byte `+0x0c = 0`, copies
no optional symbols, and returns status `0`. A reversed range with word
`+0x16 = 10` and entry-6 value `5` fails entry `6` after twelve consumed
bytes; it has written word `+0x14 = 5`, leaves derived word `+0x18 = 0`, and
copies no optional symbols. Fixture
`ESC )s80W additional validation predicate failures skip allocation` adds
five more parser-produced exits: entry `4` rejects first-code word `0x1068`
after eight consumed bytes before writing payload word `+0x16`; entry `5`
rejects zero line/count word after ten consumed bytes, leaving `+0x16 = 4` and
`+0x12 = 0`; entry `5` also rejects high line/count word `0x1069` at the same
ten-byte boundary; entry `6` rejects high range/count word `0x1069` after
twelve consumed bytes with `+0x12 = 6` and no `+0x14` write; and entry `7`
rejects class byte `2` after thirteen consumed bytes after staging
`+0x16 = 4`, `+0x12 = 6`, `+0x14 = 9`, and `+0x18 = 4`, but before writing
class byte `+0x20`.

Fixture `ESC )s80W invalid resource type fails validation before allocation`
ties the entry-2 failure to the parser and allocation boundary. The
host-fetched stream begins with `1b 29 73 38 30 57 00 01 02 03`, restores
record `80 57 00 50 00 00`, fails validation before any allocation size is
computed, drains entirely from the `0xa904` ring source, and leaves no
installed candidate.

Fixture `ESC )s80W reversed resource range fails validation before allocation`
ties the entry-6 failure to the same parser and allocation boundary. The
host-fetched stream begins with
`1b 29 73 38 30 57 00 01 00 00 00 00 00 0a 00 06 00 05`, restores record
`80 57 00 50 00 00`, and fails after twelve descriptor bytes. At failure time
the staged first-code word `+0x16` is `10`, the range/count word `+0x14` is
`5`, and derived word `+0x18` remains `0`. `0x17026` receives validation
status `0`, returns allocation status `0`, and `0x16c14` installs no
candidate. The host-fetched source drains entirely from the `0xa904` ring.

The additional validation-failure fixture ties entries `4`, `5`, `6`, and `7`
to the same parser/allocation boundary. Each stream restores record
`80 57 00 50 00 00`, reaches parser handlers `0x11eb6`, `0x12008`,
`0x11ff6`, and `0x11f96`, receives validation status `0`, returns allocation
status `0`, installs no candidate, and drains entirely from the `0xa904` ring.
Its output effect is no downloaded-font state change; the fixture records the
last staged fields before the no-install exit so later page-visible error
comparisons can start from exact byte boundaries.

Fixture `ESC )s#W validation failures preserve following printable output`
then appends printable `!` to the seven `ESC )s80W` no-install streams above
and the short-budget `ESC )s8W` stream. The `ESC )s80W` cases restore record
`80 57 00 50 00 00`; the short-budget case restores record
`80 57 00 08 00 00`, exhausts the eight-byte descriptor budget before the
entry-5 line/count word, and fails after eight descriptor bytes. In each case
the resource command returns allocation status `0`, leaves install `None`,
then the following printable byte routes through handler `0xd04a`, queues the
same default-font compact object as baseline `!`, and renders identical page
rows. Status: parser-produced validation error to visible default-font output
for those eight forms.

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
- type-1 units `0x100` allocate size `18`.
- type-2 units `0x100` allocate size `18`.
- type-0 optional-symbol offset is `0x024a`.
- type-1 optional-symbol offset is `0x044a`.
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

The sibling linear payload fixture
`host-fetched linear downloaded character stream renders through 0x168dc`
drives a complete `ESC )s6W` command through the same parser-delayed
`0x16c14` boundary with glyph `0x26`, rows `3`, width `0x10`, and six bitmap
bytes `f0 0f aa 55 3c c3`. `0x16498` selects the linear `0x168dc` reader
because the span is even (`2`), installs table entry `0x00e2`, record delta
`0x0500`, record `00 00 00 00 0c 01 00 03 00 10 00 00`, and bitmap offset
`0x050c`. The queued page object uses normal compact selector `0x0003`
because the source width seen by `0x12f2e` is span byte count `2`; the
`0x1edc6` bridge preserves that object, and `0x1ed84` / `0x1ef6a` render it
through compact target `0x1effe` and mode-0 helper `0x1fe76` as three visible
rows beginning at x `22`.
- destination x `22`, y `6`, and `$a001 = 0x16`.

Fixture `downloaded normal row-0x80 and segmented glyph FF publications
render page records` adds the publication siblings for the normal and
row-threshold short selectors. The host-fetched `ESC )s6W` stream plus
printable `&` and FF restores record `80 57 00 06 00 00`, starts the payload
at offset `5`, routes tail handlers `0xd04a` and `0xf0f0`, publishes bucket
`1` object `00 00 00 00 00 03 00 01 26 66 01`, leaves rule/fixed lists empty,
copies context slots `(0, 0, 0, 0)`, clears the current root, and renders the
copied record through bucket word `1`, compact target `0x1effe`, object byte
`0x00`, context slot `3`, and mode-0 helper `0x1fe76`. The row-`0x80`
sibling uses host-fetched `ESC )s256W`, printable `*`, and FF, restores record
`80 57 01 00 00 00`, starts payload at offset `7`, publishes the bucket-1
object `00 00 00 00 00 03 00 01 2a 66 01`, and renders the copied record
through the same bucket word `1`, compact target `0x1effe`, object byte
`0x00`, context slot `3`, and mode-0 helper `0x1fe76`.

Fixture
`host-fetched even-span wide downloaded character renders through 0x1f0d2`
covers the clean wide sibling without payload-control normalization. The
host-fetched `ESC )s18W` stream drains through `0xa904`, parser dispatch walks
`0x11eb6`, `0x12008`, `0x11ff6`, and `0x11f96`, and delayed restore reaches
record `80 57 00 12 00 00` at payload offset `6`. `0x16498` installs glyph
`0x29` at table entry `0x00ee`, record delta `0x0780`, record
`00 00 00 00 0c 01 00 01 00 90 00 00`, bitmap offset `0x078c`, span `18`,
and split-plane flag `false`. `0x168dc` copies the 18 payload bytes
`f0 0f aa 55 3c c3 81 7e ff 00 18 e7 24 db 42 bd 66 99` linearly, consumes
the full byte budget, and records zero control hits. `0x12f2e` queues the
short page-record object
`00 00 00 00 10 03 00 01 29 66 01` plus allocator padding under selector
`0x1003`; `0x1edc6` preserves that bucket object; and `0x1ed84` / `0x1ef6a`
dispatch compact target `0x1effe` to `0x1f0d2`. The renderer sees one full
16-byte chunk, a 2-byte remainder, full-row skip `2`, linear source layout,
and renders the single row at x `22`.

Fixture `host-fetched downloaded glyph composes with rule and raster through
0x1ef6a` reuses that same host-fetched `ESC )s18W` install, then carries the
installed glyph into a heterogeneous active page record. `0x12f2e` queues glyph
`0x29` at x `22`, y `80` as bucket `5` object
`00 00 00 00 10 03 00 01 29 06 01` plus allocator padding. The same page
record also contains selector-7 rule object
`00 00 00 00 05 07 08 01 00 0c 00 03 00 00`, normalized by `0x1edc6` to
`00 00 00 00 05 17 08 01 00 0c 00 03 00 03`, and mode-0 raster object
`00 00 00 00 80 00 00 02 00 00 c3 3c`. Render entry `0x1ed84`/`0x1ef6a` runs
call order `0x1ef86`, `0x1efc2`, `0x1f446`, `0x1f756`, dispatches the raster
object to `0x1f88e`, dispatches the downloaded glyph object to `0x1effe` /
`0x1f0d2`, renders the rule through selector helper `0x1f596`, and compares the
three composed output rows. This closes the downloaded-glyph plus rule/raster
composition fixture gap for the even-span wide downloaded glyph path.

Fixture `parser-driven downloaded glyph rule raster stream composes through
0x1ef6a` then makes the rule and raster producers parser-driven in the same
page stream. The fetched stream is 54 bytes: font bytes `0..24` are the
`ESC )s18W` command and payload above, and page bytes `24..54` are
`ESC *c12a3b0P ) ESC *t300R ESC *r0A ESC *b2W c3 3c`. The page parser routes
through `0x10e68`, `0x10e22`, `0x10898`, `0xd04a`, `0x10808`, `0x1075a`, and
delayed raster handler `0x11f82` / `0x105d0`. It queues the same bucket-5
downloaded glyph object `00 00 00 00 10 03 00 01 29 06 01...`, the same bridged
selector-7 rule `00 00 00 00 05 17 08 01 00 0c 00 03 00 03`, and the same
mode-0 raster object `00 00 00 00 80 00 00 02 00 00 c3 3c`. Render entry
`0x1ed84`/`0x1ef6a` dispatches the raster object to `0x1f88e`, the glyph object
to `0x1effe`/`0x1f0d2`, the rule to `0x1f596`, and compares the same three
composed rows. The remaining limitation is the modeled font install boundary:
the fixture fetches one stream and uses the existing font-payload model to
produce the installed memory image before the parser-driven page stream runs.

The modeled install-to-page handoff is now documented as a concrete resource
image contract rather than a vague fixture split. In fixture
`host-fetched even-span wide downloaded character renders through 0x1f0d2`,
the host-fetched `ESC )s18W` bytes enter delayed handler `0x16c14` through
parser handlers `0x11eb6`, `0x12008`, `0x11ff6`, and `0x11f96`. Handler
`0x16498` installs glyph `0x29` by writing table entry `0x00ee`, record delta
`0x0780`, record bytes `00 00 00 00 0c 01 00 01 00 90 00 00`, bitmap offset
`0x078c`, bitmap size `18`, and the 18 linear bitmap bytes
`f0 0f aa 55 3c c3 81 7e ff 00 18 e7 24 db 42 bd 66 99`. The page-stream
fixture then uses exactly `bytearray(downloaded_wide_even_install["header"])`
as its resource image: printable byte `0x29` resolves to glyph entry `0x0780`,
bitmap `0x078c`, width `0x0090`, rows `1`, source kind
`downloaded-pointer`, inline record `12 01 00`, and context slot `3` before
`0x12f2e` queues selector `0x1003`.

That handoff divides canonical state from parser scratch. Canonical resource
state is the installed glyph table entry, record, bitmap, and copied bitmap
bytes above. Parser scratch is the restored font payload record
`80 57 00 12 00 00`, payload offset `6`, and stream byte range `0..24`, plus
the later page parser range `24..54` and raster scratch record
`80 57 00 02 00 00` at payload offset `28`. Derived/cache state is the page
bucket chain, normalized rule object, `0x1ed84` active copy, and `0x1ef6a`
dispatch fields. The unresolved middle edge is therefore exact: live CPU
continuity from the `0x16c14` / `0x16498` install return after byte `24` back
to the `0x11774` parser loop for the following `0x10e68` rectangle handler is
not captured; the bytes and installed resource image on both sides of that
boundary are fixture-pinned.

Fixture `host-fetched row-0x80 downloaded character remains short compact`
pins the row-count threshold just below the segmented path. The host-fetched
`ESC )s256W` stream restores record `80 57 01 00 00 00`, starts payload at
offset `7`, and copies `256` linear bytes through `0x168dc`. `0x16498`
installs glyph `0x2a` at table entry `0x00f2`, record delta `0x0800`, record
`00 00 00 00 0c 01 00 80 00 10 00 00`, bitmap offset `0x080c`, rows
`0x0080`, width `0x0010`, span `2`, and split-plane flag `false`. Because
`0x12f2e` tests `rows > 0x80`, not `rows >= 0x80`, the copied glyph stays on
short page-record selector `0x0003` instead of segmented selector `0x2003`.
The queued object is
`00 00 00 00 00 03 00 01 2a 66 01` plus allocator padding, `0x1ef6a`
dispatches compact target `0x1effe`, and mode-0 helper `0x1fe76` renders the
bucket-1 band with digest
`918ec4cca20024057ec1b82577b2ab5c039c6fc9a3f756be9bbb62a088bab7ac`.

Fixture `0x16498 replacement allocation failure partial and rejected
downloaded character exits preserve state` pins the downloaded-character
replacement, allocator-failure, partial-copy, and reject branches. The linear
status-`2` case copies four of six bitmap bytes through `0x168dc`, stores
table entry `0x00f6 -> 0x0840`, writes record
`00 00 00 00 0c 01 00 03 00 10 00 00`, leaves bitmap bytes
`f0 0f aa 55 00 00`, and saves continuation fields equivalent to
`0x7827c6 = 1`, `0x7827da = 0`, `0x7827c8 = 0x2b`,
`0x7827ca = 0x0850`, `0x7827d2 = 2`, and zero split-plane counters. The
split-plane status-`2` case copies prefix bytes `a0 a1` and trailing byte
`b0` through `0x16942`, stores table entry `0x00fa -> 0x0880`, leaves bitmap
layout `a0 a1 00 00 b0 00`, and saves `0x7827ca = 0x088e`,
`0x7827ce = 0x0891`, `0x7827d6 = 1`, and `0x7827d8 = 0`. The replacement
case starts with table entry `0x0102` holding old record `00 00 02 00`;
`0x1652a..0x1653e` calls `0x17a24`, which validates range
`0x0020..0x007f`, clears the old record, clears the matching continuation,
refreshes the active primary context, and returns before `0x16498` stores the
new table pointer `0x0900` and bitmap `11 22 33 44 55 66`. The allocation
failure case reaches the allocator branch after object-size computation:
`0x1656e` asks `0x170c` for one 64-byte unit aligned to `0x40`, receives
zero, reports `0x9b5e(0x780e2e, 4)`, calls `0x1887a` on current payload
`0x123456`, copies no bitmap bytes, and leaves table entry `0x0106` at zero.
That payload release clears the current-record id/payload, removes candidate
slot `0x782328`, clears the matching continuation, marks primary/secondary
context-stack bytes, refreshes the active secondary context, and leaves no new
downloaded-character object. The mode-`0` record-shape reject and the `0xa0`
character with header type `0` both return status `0` before writing a table
pointer, matching the `0x164f2..0x16540` range branch and the pre-copy shape
guard.

Fixture `0x16498 no-install exits preserve following printable output` carries
the three no-install branches above to visible output. Each case starts from a
host-fetched `ESC )s6W` command plus six payload bytes, restores record
`80 57 00 06 00 00`, dispatches delayed handler `0x16c14`, and then appends
printable `!`. The allocation-failure case returns reason
`allocation-failed`, the mode-0 case returns `unsupported-record-shape`, and
the `0xa0`/header-type case returns `char-outside-header-type`. In all three
cases the following printable byte routes through `0xd04a`, queues the same
default-font compact object as baseline `!`, and renders identical rows. This
classifies the failed downloaded-character command as firmware bookkeeping and
parser scratch, not canonical renderer state.

Fixture `0x16498 status-2 partial installs remain printable` covers the
opposite non-success branch: status `2` is a partial install, not a no-install.
The linear case starts from host-fetched `ESC )s4W f0 0f aa 55`, restores
record `80 57 00 04 00 00`, stores table entry `0x00f6 -> 0x0840`, leaves
bitmap bytes `f0 0f aa 55 00 00`, and saves continuation state with
destination `0x0850` and remaining count `2`. A following printable `+`
resolves glyph `0x2b`, queues short selector `0x0003`, and renders rows from
the copied bytes plus the zero-filled missing row. The same page-record object
now finalizes through `0xff1e` on a trailing FF: publication keeps bucket `1`,
copies compact object `00 00 00 00 00 03 00 01 2b 66 01`, clears the current
page root, and renders the published record through `0x1ed84`/`0x1ef6a` with
the same rows.

The split-plane case starts from `ESC )s3W a0 a1 b0`, stores table entry
`0x00fa -> 0x0880`, leaves layout `a0 a1 00 00 b0 00`, saves A4/A3
continuation destinations `0x088e`/`0x0891`, and a following printable `,`
resolves glyph `0x2c`, queues selector `0x0003`, and renders the first row
from prefix bytes `a0 a1` plus trailing byte `b0`. Its trailing-FF publication
also keeps bucket `1`, copies compact object `00 00 00 00 00 03 00 01 2c 66
01`, clears the current page root, and renders the published record through
`0x1ed84`/`0x1ef6a` with the same rows.

Fixture `host-fetched segmented downloaded character renders through
0x1f1f0` adds the even-span tall sibling. The host-fetched `ESC )s258W` stream
uses parser record `80 57 01 02 00 00`, delayed handler `0x16c14`, payload
offset `7`, and byte budget `0x0102`. `0x16498` installs glyph `0x27` at
table entry `0x00e6`, record delta `0x0580`, record
`00 00 00 00 0c 01 00 81 00 10 00 00`, bitmap offset `0x058c`, and span `2`.
Because the copied glyph has rows `0x81` and width byte count `2`, `0x12f2e`
queues selector `0x2003` with segment objects for buckets `9` and `1`. The
segment-1 object `00 00 00 00 20 03 00 01 27 01 66 01` is preserved by
`0x1edc6`; `0x1ef6a` dispatches it as compact text; and `0x1f1f0` renders the
row at source offset `0x0100` as `####........####` beginning at x `22`.

The same publication fixture covers the FF sibling for this linear-segmented
selector. The host-fetched `ESC )s258W` stream plus printable `'` and FF
restores record `80 57 01 02 00 00`, starts the payload at offset `7`, routes
tail handlers `0xd04a` and `0xf0f0`, publishes bucket `9` object
`00 00 00 00 20 03 00 01 27 01 66 01`, and also preserves the segment-0 bucket
`1` entry. The published record has empty rule/fixed lists, context slots
`(0, 0, 0, 0)`, cleared current root, render bucket word `9`, compact target
`0x1effe`, object byte `0x20`, context slot `3`, and renderer `0x1f1f0`, which
reads the segment-1 source row from offset `0x0100`.

Fixture `host-fetched split-plane segmented downloaded character renders
through 0x1f1f0` covers the odd-span sibling. The host-fetched `ESC )s387W`
stream uses parser record `80 57 01 83 00 00`, delayed handler `0x16c14`,
payload offset `7`, and byte budget `0x0183`. `0x16498` installs glyph `0x28`
at table entry `0x00ea`, record delta `0x0700`, record
`00 00 00 00 0c 01 00 81 00 18 00 00`, bitmap offset `0x070c`, span `3`, and
split-plane layout. `0x16942` copies prefix bytes through A4 and trailing
bytes through A3; for segment `1`, `0x1f1f0` reads row skip `0x80` from A2
offset `0x0100` and A3 offset `0x0080`, then renders
`####........#####.#.#.#.` beginning at x `22`.

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

The split-plane companion fixture
`host-fetched 0x15d0a split-plane continuation resource object resumes
fixed-record render` uses fixed-record prefix `03 02 04 00` and host bitmap
stream `a0 a1 b0 c0 c1 d0`. The first `0x16606` pass receives budget `0x12`,
leaving copy budget `4`; it writes prefix bytes `a0 a1 c0` at payload delta
`0x0200`, writes trailing byte `b0` at delta `0x0204`, stores record
`03 02 04 00 00 00 02 00` at payload `+0x48`, and saves continuation fields:

- `0x7827c6 = 1`;
- `0x7827da = 0x000100`;
- `0x7827c8 = 0x21`;
- `0x7827ca = 0x000303`;
- `0x7827ce = 0x000305`;
- `0x7827d2 = 0`;
- `0x7827d6 = 0`; and
- `0x7827d8 = 0`.

The continuation descriptor `ESC )s0W 04 01 cc` again routes through
`0x15e5c..0x15e68` to `0x15c4c`. `0x15c4c` reloads raw width `3`, row count
`2`, prefix span `2`, saved A4/A3 destinations, and saved D4/D3 counters; the
`0x16874` split-plane resume path then copies remaining prefix byte `c1` to
`0x000303` and trailing byte `d0` to `0x000305`. The completed bitmap layout is
`a0 a1 c0 c1 b0 d0`, which `glyph_source_bytes_for_rows` reconstructs as
rows `a0 a1 b0` and `c0 c1 d0`. The page path maps host `!` to glyph `1`,
queues object prefix `00 00 00 00 00 03 00 01 01 76 01`, preserves context
slot `3` through `0x1edc6`, and renders two mode-0 rows beginning at x `22`,
y `7`. This closes the split-plane continuation-counter middle edge for one
bit-30-clear fixed-record resource object.

The failure companion fixture
`0x15c4c failed resource resume releases fixed-record object` starts from the
same partial even-span install but supplies only two of the four remaining
bitmap bytes. The linear reader `0x168dc` returns status `0` with partial bytes
`f0 0f`, so `0x15c4c` takes the `0x15cb8..0x15ccc` failure exit through
`0x17d7c` before clearing the continuation fields at `0x15cd6..0x15d08`.
`0x17d7c` verifies the bit-30-clear fixed-record range, rewrites glyph `0x21`
at payload `+0x48` from `02 03 04 00 00 00 02 00` to
`01 02 00 fa 00 00 00 00`, writes side-table bytes `fa 00` at payload
`+0x340`, refreshes the active primary context with `0x7828de = 0`, and clears
matching continuation state. The replacement byte `0xfa` is the low byte of
`0x7530 / payload_word_0x1a`, with the fixture setting word `+0x1a = 0x0078`;
the final longword comes from the base fixed-record entry at payload `+0x40`.
This covers the `0x15c4c` status-0 release exit for one active-primary
bit-30-clear fixed-record payload.

The fixed-record extended-table fixture
`0x17d7c releases extended fixed-record table with secondary refresh` enters
the same helper directly with payload byte `+0x0e = 1` and char `0xa1`.
Disassembly `0x17de2..0x17dfc` admits the `0xa0..0xff` range only for that
type byte, and `0x17e12..0x17e20` subtracts `0x20` before the table-index
math. The fixture therefore rewrites table entry
`payload + 0x40 + (0xa1 - 0x40) * 8` from `04 05 06 07 00 00 04 00` to
`01 02 00 2c 00 00 03 00`, writes side-table bytes `2c 00` at
`payload + 0x702`, refreshes the active secondary context with `0x7828de = 1`,
and clears matching continuation state. The replacement byte `0x2c` is the
low byte of `0x7530 / payload_word_0x1a`, with the fixture setting
`+0x1a = 0x0064`.

The delegated bit-30 fixture
`0x17d7c delegates bit-30 release to offset-table helper` enters `0x17d7c`
with payload longword bit 30 set, so `0x17dc4..0x17dce` calls `0x17a24`
instead of the fixed-record rewrite body. The fixture sets payload word `+8 =
0x004a`, range words `+0x0e/+0x10 = 0x0020/0x007f`, and char `0x21`;
`0x17a24` validates the range at `0x17a44..0x17a60`, clears the offset-table
entry at payload `+0x004a + 4 * 0x21` from `00 00 02 40` to
`00 00 00 00`, refreshes the matching active secondary context with
`0x7828de = 1`, and clears matching continuation state.

The current-record allocation-failure release fixture named above covers the
remaining `0x1887a` teardown edge for a bit-30-clear extended fixed-record
payload: it proves record clearing, candidate deletion, continuation clearing,
context-stack dirty marking, active-context refresh, counter/cursor decrement,
and the final `0x1b04c` refresh even when `0x16c14` installs no replacement.

## End-To-End Downloaded Glyph Path

The strongest current byte-stream fixture is:

```text
ESC *c4660d37e5F
ESC )s2193W <0x0891 payload bytes>
% FF
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

The FF publication variant proves the same installed-glyph page object across
`0xff1e`. The fetched stream length is `2216` bytes, with control bytes
`0..14`, payload bytes `14..2214`, printable byte `2214..2215`, and FF at
`2215..2216`. The tail `% FF` routes to handlers `0xd04a` and `0xf0f0`.
Publication keeps bucket root `00 00 00 00 30 03 00 01 25 01 66 01...`,
publishes bucket array entries `9` and `1`, leaves rule and fixed lists empty,
copies context slots `0,0,0,0`, clears the current root, and sets publication
flag `1`. Fixture
`published downloaded glyph segmented buckets render across bands` copies that
published record through `0x1ed84`, walks modeled band words `1` and `9`
through `0x1ef6a`, dispatches both compact objects to `0x1effe`, leaves the
bucket-1 segment-0 band blank for this payload, and reproduces the downloaded
segment-1 row from bucket `9` at page row `86`. Fixture
`0x1eba4 scheduler band words render published downloaded glyph` starts from
the `0xff1e`/`0x1ed84` seed where source `+0x18` has been cleared and render
work `+0x10/+0x16` are zero, lets the scheduler loop produce `0x1ef6a` calls
for band words `0..9`, and reaches the same bucket-9 visible row while only
published buckets `1` and `9` dispatch compact objects.

The even-span wide downloaded-glyph publication sibling proves the same
`0xff1e` boundary for the non-segmented wide compact branch. The fetched stream
is `ESC )s18W` plus payload, printable `)`, and FF, with font bytes
`0..24`, printable byte `24..25`, and FF at `25..26`. The font phase restores
record `80 57 00 12 00 00`, installs glyph `0x29` at table entry `0x00ee`
with record delta `0x0780`, bitmap offset `0x078c`, bitmap size `18`, and
linear mode-1 span `18`. The tail `) FF` routes to handlers `0xd04a` and
`0xf0f0`. Publication keeps bucket root
`00 00 00 00 10 03 00 01 29 66 01...`, publishes bucket array entry `1`,
leaves rule and fixed lists empty, copies context slots `0,0,0,0`, clears the
current root, and sets publication flag `1`. The copied record renders with
bucket word `1`: `0x1ef86` computes remainder `1`, current-band rows
`0x0040`, and destination base `0x00100800`; `0x1efc2` dispatches object byte
`0x10` to compact branch target `0x1effe`; `0x1f0d2` emits the same 18-byte
linear downloaded-glyph row as the direct even-span fixture. Evidence: fixture
`host-fetched even-span downloaded glyph FF publishes rendered page record`.

Fixture `downloaded normal row-0x80 and segmented glyph FF publications
render page records` extends that publication concept to the normal,
row-threshold, and linear-segmented branches. The normal stream is
`ESC )s6W` plus payload, printable `&`, and FF; the font phase restores
`80 57 00 06 00 00`, the tail routes through `0xd04a`/`0xf0f0`, `0xff1e`
publishes bucket `1`, and `0x1ed84`/`0x1ef6a` dispatch object byte `0x00` to
`0x1effe`/`0x1fe76`. The row-threshold stream is `ESC )s256W` plus payload,
printable `*`, and FF; the font phase restores `80 57 01 00 00 00`, `0xff1e`
publishes bucket `1`, and the copied row-`0x80` selector `0x0003` record
renders through the same compact target/helper with digest
`918ec4cca20024057ec1b82577b2ab5c039c6fc9a3f756be9bbb62a088bab7ac`. The
segmented stream is `ESC )s258W` plus payload, printable `'`, and FF; the font
phase restores `80 57 01 02 00 00`, `0xff1e` publishes buckets `1` and `9`,
and render bucket word `9` dispatches object byte `0x20` to
`0x1effe`/`0x1f1f0`, reading the visible row from source offset `0x0100`.

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
  continuation fields, including split-plane A4/A3 destinations and D4/D3
  counters. On status `1` it clears continuation state and leaves the completed
  fixed-record payload renderable through the same active context path. On
  status `0` it calls `0x17d7c` to release/rewrite the fixed-record entry, then
  clears continuation state.
- `0x17d7c` rewrites released bit-30-clear fixed-record entries, writes the
  side-table bytes used by the fallback record, refreshes matching active
  primary/secondary contexts through `0x14c64`, and clears matching
  continuation state.
- `0x17a24` releases bit-30 offset-table entries delegated by `0x17d7c`,
  clears the selected 4-byte glyph/object pointer, refreshes matching active
  primary/secondary contexts through `0x14c64`, and clears matching
  continuation state.
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
  `0x7827c8`, saved destination `0x7827ca`, saved trailing-plane destination
  `0x7827ce`, saved remaining count `0x7827d2`, saved split-plane counters
  `0x7827d6`/`0x7827d8`, and the fixed-record table entry in the selected
  payload.
- `0x17a24` reads bit-30 offset-table payload words `+0x08`, `+0x0e`, and
  `+0x10`, the selected 4-byte table entry, active primary/secondary context
  pointers, and continuation state.
- `0x1bc38` reads payload class byte `+0x20` and inserts candidate longwords.
- `0x14c64` consumes installed candidate longwords and payload header fields
  to build active glyph maps.
- `0x1393a` consumes the active map and selected context to build printable
  source objects.
- `0x12f2e`, `0x1387c`, `0xff1e`, `0x1edc6`, `0x1ed84`, and `0x1ef6a`
  consume the installed glyph source and compact objects through the
  page-record publication/render pipeline.

## Output Effect

Downloaded font commands do not draw until a later printable byte selects an
installed glyph. The visible effect is that the same host byte can resolve to
a payload-backed glyph record instead of a built-in glyph. In the end-to-end
fixture, printable `%` draws glyph `0x25` from downloaded object record
`0x0500`, with a segmented-wide compact selector `0x3003` and one visible row
beginning at x `22`. The FF publication variant proves the same row after
`0xff1e` publishes both segmented buckets; fixture
`published downloaded glyph segmented buckets render across bands` then walks
published bucket words `1` and `9` through `0x1ed84`/`0x1ef6a`, with bucket
`1` blank in this payload and bucket `9` producing the visible row. Fixture
`0x1eba4 scheduler band words render published downloaded glyph` proves the
same visible row when `0x1eba4` advances render work word `+0x10` from the
zero seed through band words `0..9`. The linear downloaded-character fixture
draws glyph
`0x26` from the same object delta using selector `0x0003` and renders three
mode-0 rows beginning at x `22`. In the `0x16606` current-record fixture,
printable `!` maps to fixed-record glyph `1` from payload record `0x48`,
queues selector `0x0003`, and renders three mode-0 rows beginning at x `22`.
The companion `0x15c4c` fixture proves that splitting the same bitmap across
two descriptor packets produces the same table entry, source object,
page-record bridge, and rendered rows after continuation state is cleared.
The split-plane `0x15c4c` fixture proves the same for an odd fixed-record
width: saved prefix/trailing destinations and D4/D3 counters resume into a
split A2/A3 bitmap layout, and the later compact renderer reconstructs rows
`a0 a1 b0` and `c0 c1 d0`.
The failed-resume fixture proves that a short resumed payload does not leave
the half-copied fixed record installed: `0x15c4c` calls `0x17d7c`, replaces the
table entry with `01 02 00 fa 00 00 00 00`, updates side-table bytes `fa 00`,
refreshes the active primary context, and clears the same continuation fields.
The extended fixed-record fixture proves the direct release form for type-byte
`1` extended characters: char `0xa1` rewrites the extended table entry to
`01 02 00 2c 00 00 03 00`, writes side-table bytes `2c 00`, refreshes the
active secondary context, and clears continuation fields.
The bit-30 delegate fixture proves the sibling offset-table release form:
`0x17d7c` calls `0x17a24`, which clears one 4-byte offset-table entry from
`00 00 02 40` to zero, refreshes the active secondary context, and clears the
matching continuation fields.

## Confidence

High for command dispatch, delayed-record restoration, current id/current
character ownership, current-record mark/unmark, `0x16c14` install
bookkeeping, table-driven descriptor staging, `0x17026`/`0x1719c` allocation
headers, the split-plane and linear downloaded-character-to-rendered-row
fixtures, and the `0x16606` and `0x15c4c` bit-30-clear
resource-object-to-rendered-row fixtures.

High for the modeled `0xff1e` publication fields of the combined downloaded
glyph stream because fixture
`combined font download FF publishes installed glyph page record` asserts the
published bucket root, bucket array entries `1` and `9`, empty rule/fixed
lists, context prefix, and FF parser handler. High for the even-span wide
publication sibling because fixture
`host-fetched even-span downloaded glyph FF publishes rendered page record`
asserts the host-fetched `ESC )s18W` payload, tail handlers `0xd04a` and
`0xf0f0`, published bucket `1`, `0x1ed84` render word `1`, compact dispatch
target `0x1effe`, and final `0x1f0d2` rows. High for the modeled normal,
row-`0x80`, and segmented publication siblings because fixture
`downloaded normal row-0x80 and segmented glyph FF publications render page records`
asserts host-fetched `ESC )s6W` plus `&`/FF, `ESC )s256W` plus `*`/FF, and
`ESC )s258W` plus `'`/FF, tail handlers `0xd04a` and `0xf0f0`, published
buckets `1` and `9`, render bucket words `1` and `9`, compact target
`0x1effe`, row-`0x80` selector `0x0003`, object bytes `0x00` and `0x20`, and
final `0x1fe76`/`0x1f1f0` rows. High for the modeled
published-record multi-bucket render because fixture
`published downloaded glyph segmented buckets render across bands` walks
bucket words `1` and `9`, proves the `0x1effe` dispatch for both compact
objects, and compares the page rows. High for publication-to-scheduler band
progression because `0xff1e` disassembly at `0xffc8` clears root `+0x18`,
`0x1ed84` copies that word into render `+0x10/+0x16`, and fixture
`0x1eba4 scheduler band words render published downloaded glyph` proves
`0x1eba4` emits band words `0..9` through `0x1ef6a` and preserves the same
visible row.

High for the covered parser-produced metric combinations because the type-0,
type-1, type-2, metric-variant, clamped, lower-bound, and upper-bound fixtures
all start from host-fetched `ESC )s80W`, run through `0x16fae`/`0x1719c`, and
compare page-visible `0xd4ac`/`0xd8fc` output effects. Medium for the full PCL
soft-font grammar because the validation table is executable but not every
predicate has a manual-facing semantic name, and not every legal metric
combination has a parser-produced page comparison.

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
  destination pointer, trailing-plane destination pointer, remaining byte
  count, split-plane counters, and continuation clearing;
- bit `30` on candidate longwords, because it chooses offset-table resource
  rendering rather than fixed-record rendering;
- glyph table entry, glyph record bytes, bitmap offset, span, rows, width,
  split-plane layout, fixed-record layout, and compact selector bits;
- the page-record bridge through `0x1edc6` and active render entry
  `0x1ed84`/`0x1ef6a`.

## Remaining Edges

- `0x16fae..0x17016`: all 32 validation slots now have ROM-effect names and
  concrete success/failure fixtures. Host-fetched invalid-type, first-code
  overflow, zero line/count, high line/count, reversed-range, high range/count,
  and invalid-class streams prove seven parser-produced no-install boundaries
  and preserve following default printable output. Exact HP manual labels for
  the consumed-but-not-staged descriptor fields still need external
  correlation.
- `0x16498..0x16942`: split-plane segmented-wide, wide/control, even-span
  wide, row-threshold `0x80` short, linear normal, linear segmented, and
  split-plane segmented downloaded-character paths are page-visible. Fixture
  `host-fetched row-0x80 downloaded character remains short compact` closes
  the even-span `0x80`/`0x81` selector boundary: rows `0x80` stay on
  selector `0x0003`, while rows `0x81` enter selector `0x2003` in fixture
  `host-fetched segmented downloaded character renders through 0x1f1f0`.
  Fixture `0x16498 replacement allocation failure partial and rejected downloaded
  character exits preserve state` covers old-pointer release through
  `0x17a24`, object allocation failure through `0x170c`/`0x9b5e`/`0x1887a`,
  status-`2` linear/split-plane continuation pointer writes, and
  mode/header-type rejects. Fixture
  `0x16498 no-install exits preserve following printable output` closes
  page-visible recovery for those no-install exits by proving the following
  printable byte stays on the default-font object and rows. Fixture
  `0x16498 status-2 partial installs remain printable` covers the linear and
  split-plane status-`2` visible-output siblings and now carries both through
  trailing-FF `0xff1e` publication and published-record rendering. Remaining
  parser-produced comparisons are bounded cross-products: non-boundary row
  counts inside the already-covered short and segmented selector families,
  character modes other than the covered mode-1 bitmap records, and
  publication behavior for the no-install variants rather than the next
  printable byte alone.
- `0xff1e..0x1ed84`: the combined downloaded-glyph stream now publishes both
  segmented buckets; the normal, linear-segmented, and even-span wide siblings
  now publish through the same boundary. Fixture
  `downloaded normal row-0x80 and segmented glyph FF publications render page records`
  renders the normal bucket-1 record through `0x1ed84`/`0x1ef6a` and compact
  target `0x1effe`/`0x1fe76`, renders the row-`0x80` bucket-1 record through
  the same target/helper while preserving selector `0x0003`, and renders the
  linear-segmented bucket-9 record through `0x1ed84`/`0x1ef6a` and compact
  target `0x1effe`/`0x1f1f0`. Fixture
  `host-fetched even-span downloaded glyph FF publishes rendered page record`
  renders the copied bucket-1 record through `0x1ed84`/`0x1ef6a` and compact
  target `0x1effe`/`0x1f0d2`. Fixture
  `published downloaded glyph segmented buckets render across bands` renders
  published bucket words `1` and `9` from the copied record. Fixture
  `0x1eba4 scheduler band words render published downloaded glyph` proves
  `0xff1e`/`0x1ed84` seed render work `+0x10/+0x16` from cleared source
  `+0x18 = 0`, then `0x1eba4` advances through band words `0..9` until the
  published bucket-9 row is visible. The earlier first-band seed edge is now
  closed for this published record.
- `0x15c4c`: the even-span and split-plane fixed-record resume routes are
  page-visible, and the status-0 fixed-record release exit is fixture-backed.
  The bit-30 offset-table release delegate is fixture-backed through
  `0x17a24`. Fixed-record secondary-context refresh and fixed-record
  extended-table release are fixture-backed together. Current-record
  allocation-failure teardown through `0x1887a` is fixture-backed for the
  bit-30-clear extended fixed-record case.
- `0x14c64..0x14eb6`: the `0x1719c` bit-30-clear fixed-record path is an
  isolation control. The integrated `ESC )s80W` install path currently proves
  the bit-30 offset-table form.
- The span-metric fields documented in `notes/font-context-metrics.md` are now
  tied to installed payload headers for the `0xd4ac` and `0xd8fc` type-0,
  type-1, and type-2 fixtures, and the shared consumer branch family is
  fixture-backed. The invalid-resource-type, first-code overflow, zero
  line/count, high line/count, reversed-range, high range/count, and
  invalid-class resource paths now have host-fetched
  parser/validation/no-install boundaries and following-printable page output.
  The seven-case legal descriptor metric matrix plus the boundary-value
  fixture now prove copied descriptor fields can flip the `0xd4ac`
  page-extent gate, exercise rounded-metric clamping into `+0x2c/+0x2d`,
  preserve zero rounded/offset fields through visible `0xd4ac` and `0xd8fc`
  span objects, preserve negative and max-positive flagged offset bytes as
  copied words `0xfffe` and `0x007f`, accept `d8fc` lower-bound equality and
  exact page-extent equality, move `d8fc` rendered rows, update `0xd8fc`
  without publishing a span object, suppress both span consumers through
  parser-owned lower-bound fields, suppress only `0xd8fc` through
  parser-owned upper-bound fields while preserving `0xd4ac` span output and
  compact glyph output, and show rounded input `0x1500` transforms to copied
  `+0x2c = 0x0060` before `d4ac` exits beyond page extent. Fixture
  `descriptor metric fields match across inline and resource contexts` now
  proves the legal producer forms and the two invalid swapped forms. The
  remaining producer gap is additional metric-value combinations within those
  legal forms, plus validation/error forms beyond the bounded predicate and
  short-budget branches that still need parser-produced page evidence.
