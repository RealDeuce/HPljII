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
- `generated/disasm/ic30_ic13_font_payload_descriptor_helpers_016a10.lst`
- `generated/disasm/ic30_ic13_font_resource_object_add_016c14.lst`
- `generated/disasm/ic30_ic13_font_resource_validate_016fae.lst`
- `generated/disasm/ic30_ic13_font_resource_find_017026.lst`
- `generated/disasm/ic30_ic13_font_resource_payload_initializer_01719c.lst`
- `generated/disasm/ic30_ic13_font_payload_readers_016874.lst`
- `generated/disasm/ic30_ic13_font_payload_readers_0168dc.lst`
- `generated/disasm/ic30_ic13_font_resource_payload_link_01887a.lst`
- `generated/disasm/ic30_ic13_font_resource_release_018b92.lst`
- `generated/disasm/ic30_ic13_font_resource_release_alt_018bf2.lst`
- `generated/disasm/ic30_ic13_font_resource_classify_0172c0.lst`
- `generated/disasm/ic30_ic13_font_resource_payload_record_lookup_0170be.lst`
- `generated/disasm/ic30_ic13_font_fixed_record_release_017a24.lst`
- `generated/disasm/ic30_ic13_font_candidate_object_alloc_01bc38.lst`
- `notes/font-context-metrics.md`

Primary fixtures:

- `0x15d0a-modeled font descriptor route`
- `0x15d0a descriptor grammar exits and handler matrix`
- `0x121cc/0x15d0a-modeled font descriptor command stream`
- `font descriptor stream ties ROM parser dispatch to 0x15d0a routes`
- `host-fetched font descriptor streams route through 0x15d0a`
- `host-fetched 0x15d0a current-record resource object feeds fixed-record render`
- `0x16606 no-install exits clear stale continuation without payload writes`
- `host-fetched 0x15d0a continuation resource object resumes fixed-record render`
- `0x15c4c failed resource resume releases fixed-record object`
- `0x15c4c partial resource resumes update continuation state`
- `0x17d7c releases extended fixed-record table with secondary refresh`
- `0x17d7c delegates bit-30 release to offset-table helper`
- `0x17d7c release reject exits preserve table and continuation state`
- `host-fetched 0x15d0a split-plane continuation resource object resumes
  fixed-record render`
- `0x16c14-modeled downloaded font replacement bookkeeping`
- `0x16c14 routes installed font resource through 0x1bc38 slot`
- `0x1887a release variant matrix covers cleanup branches`
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
- `legal descriptor metric extent fenceposts drive d4ac and d8fc consumers`
- `legal descriptor metric range endpoints drive d4ac and d8fc consumers`
- `legal descriptor metric mixed values drive d4ac and d8fc consumers`
- `legal descriptor metric tight range values drive d4ac and d8fc consumers`
- `legal descriptor metric low-nibble rounding drives d4ac and d8fc consumers`
- `legal descriptor metric byte-boundary rounding drives d4ac and d8fc consumers`
- `0x16498-backed downloaded character object renders segmented-wide compact row`
- `downloaded character stream ties ROM parser dispatch to rendered object`
- `host-fetched downloaded character stream reaches rendered object`
- `host-fetched downloaded character object feeds 0x1ed84 and 0x1ef6a`
- `host-fetched linear downloaded character stream renders through 0x168dc`
- `host-fetched downloaded character payload control reaches wide render`
- `host-fetched payload-control downloaded glyph FF publishes page record`
- `host-fetched even-span wide downloaded character renders through 0x1f0d2`
- `host-fetched row-0x80 downloaded character remains short compact`
- `0x16b1a descriptor width helper emits only mode 1/2`
- `downloaded glyph width-span matrix publishes and renders all main helpers`
- `downloaded glyph wide-remainder matrix publishes and renders compact chunks`
- `downloaded glyph width-byte boundary truncates page-record span`
- `downloaded glyph segmented-wide matrix publishes and renders compact chunks`
- `downloaded segmented-wide row-byte boundary truncates page-record segments`
- `0x16498 replacement allocation failure partial and rejected downloaded character
  exits preserve state`
- `0x16498 no-install exits preserve following printable output`
- `0x16498 status-2 partial installs remain printable`
- `0x15b9a resumes downloaded-character continuation objects`
- `0x15b9a partial and failed resumes update continuation or release object`
- `host-fetched even-span downloaded glyph FF publishes rendered page record`
- `host-fetched rows-0x20 short downloaded glyph FF publication renders page
  record`
- `host-fetched rows-0x40 short downloaded glyph FF publication renders page
  record`
- `host-fetched rows-0x82 segmented downloaded glyph FF publication renders page
  record`
- `host-fetched rows-0x102 downloaded glyph FF publication truncates
  page-record rows`
- `downloaded normal row-0x80 and segmented glyph FF publications render page records`
- `split-plane segmented downloaded glyph FF publication renders page record`
- `host-fetched downloaded glyph composes with rule and raster through 0x1ef6a`
- `parser-driven downloaded glyph rule raster stream composes through 0x1ef6a`
- `host-fetched segmented downloaded character renders through 0x1f1f0`
- `segmented downloaded glyph composes with raster through 0x1ef6a`
- `host-fetched split-plane segmented downloaded character renders through
  0x1f1f0`
- `split-plane segmented downloaded glyph composes with raster through 0x1ef6a`
- `segmented downloaded glyph raster FF publications render page records`
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
- `0x7827be`: parsed downloaded-character bitmap byte count. `0x16336`
  accumulates it from the descriptor helpers before `0x16498` rounds
  `(0x7827be + 0x4b) >> 6` into the class-1 object allocation request at
  `0x16558..0x1656e`.
- `0x7827c2`: parsed byte span per row. `0x16050` writes the rounded
  `(width + 7) >> 3` span; `0x16874` later chooses the linear reader
  `0x168dc` or split-plane reader `0x16942` from this span.
- `0x7827c4`: parsed row count copied by `0x16096` and consumed by
  `0x16874`/`0x16942`.
- `0x7827de..0x7827e9`: descriptor scratch records used by `0x16336` and
  copied into the allocated character object by `0x163b8`. The covered
  `0x16498` fixtures produce record bytes such as
  `00 00 00 00 0c 01 00 03 00 10 00 00`; byte `+5` is the downloaded
  bitmap-record mode byte, not the font-header type byte. This is the same
  scratch buffer reused below by the `0x17026`/`0x1719c` resource-header path;
  the active interpretation is selected by the parser route.
- `0x782f30`: current character code/index written before descriptor
  dispatch and used by `0x16498` for the object-table entry
  `0x4a + 4 * char`.

Downloaded-character descriptor helper table:

- `0x16336` initializes `0x78286e = 0x7827de`, then walks nine reader/helper
  pairs from table `0x162ee..0x16332`. Each reader value is passed to the
  paired helper; any helper returning other than `1` exits status `0` at
  `0x16384`. After all nine helpers succeed, `0x15a94` performs the shared
  geometry/bounds check, then `0x16396..0x163ae` drains
  `0x782848 = descriptor_size - 14` extension bytes through `0x12328` and
  subtracts that count from `0x783140`.
- Slot 1, reader `0x1599c`, helper `0x16a26`: the descriptor size byte must
  be at least `14`; accepted values write the extension-byte count
  `value - 14` to `0x782848`.
- Slot 2, reader `0x1599c`, helper `0x16a4c`: accepts only value `1`. This is
  a descriptor version/form guard; it writes no staged object byte.
- Slot 3, reader `0x1599c`, helper `0x16a66`: masks the value with `3`, then
  accepts only when the masked value is `0` or `1` and matches font-header
  byte `+0x20`. It writes no staged object byte; the mismatch is a
  descriptor/header compatibility reject.
- Slot 4, reader `0x1599c`, helper `0x17358`: pass-through byte consumed and
  not staged for the covered object forms.
- Slots 5 and 6, reader `0x159f6`, helpers `0x16aa0` and `0x16adc`: signed
  words clamped to `[-0x1068, 0x1068]`, written to scratch words `+0` and
  `+2`, and copied by `0x163b8` to object words `+0` and `+2`.
- Slot 7, reader `0x159d4`, helper `0x16b1a`: width must be
  `1..0x1068`. It writes scratch word `+8`, writes rounded span
  `(width + 7) >> 3` to `0x7827c2`, and sets scratch byte `+5` to mode byte
  `1` for even spans or `2` for odd spans. Fixture `0x16b1a descriptor
  width helper emits only mode 1/2` samples widths `1`, `8`, `9`, `16`, `17`,
  `24`, `25`, and `0x1068`, proves the accepted mode set is `{1, 2}`, and
  proves invalid widths `0` and `0x1069` return through `0x16b26..0x16b34`
  without rewriting the staged scratch record.
- Slot 8, reader `0x159d4`, helper `0x16b74`: row count must be
  `1..0x1068`. It writes scratch word `+6`, writes `0x7827c4`, computes
  `0x7827be = rows * span` through `0x332ee`, and increments that byte count
  when `0x7827c1.0` is set.
- Slot 9, reader `0x159f6`, helper `0x16bd2`: signed word clamped to
  `0..0x41a0`, rounded by `(value + 2) >> 2 << 2`, and written to scratch
  word `+0x0a`, which becomes object word `+0x0a`.
- `0x163b8` copies scratch words `+0/+2/+6/+8/+0x0a` into the allocated
  object, forces object byte `+4 = 0x0c`, and copies scratch byte `+5` as the
  object mode byte. It then updates selected font-header extent words
  `+0x1c/+0x1e` from the staged row/width fields, with the comparison order
  controlled by font-header byte `+0x20`.
- `0x782862`: staging-record pointer, set by `0x17026` to `0x7827de`.
- `0x7827de`: staged sparse font-resource header copied by `0x1719c` on the
  resource-header route.
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
  buckets `1` and `9`; split-plane segmented selector `0x2003` publishes
  buckets `1` and `9`; rows-`0x0102` installs publish only bucket `1` because
  the printable source record exposes row byte `0x02` to `0x12f2e`;
  segmented-wide selector `0x3003` publishes buckets `1` and `9` for the
  positioned single case and buckets `0` and `8` for the origin-positioned
  segmented-wide matrix; wide selector `0x1003` publishes bucket `1` for both
  the even-span and payload-control odd-span streams, and bucket `0` for the
  width/remainder matrix's origin-positioned spans `17..32` plus high-span
  probes `33`, `48`, `49`, `64`, and `255`.
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
- Unknown for this checkpoint: downloaded-glyph publication cross-products outside the
  documented normal bucket-1, rows-`0x01`/`0x04`/`0x20`/`0x40`/`0x7f` short bucket-1,
  row-`0x80` short bucket-1, rows-`0x0101..0x0103` low-byte-truncated bucket-1
  publication, linear-segmented bucket-9, rows-`0x82`/`0x83`/`0x84`/`0xfe`/`0xff`
  segmented bucket-1/bucket-9, split-plane segmented bucket-9, segmented-wide
  bucket-1/bucket-9, even-span wide bucket-1, and payload-control odd-span wide bucket-1
  streams. The remaining row-count risk is no longer the `0x80`/`0x81` selector boundary
  itself or the newly covered short/segmented matrix; it is row counts outside those
  sampled selector-family fixtures, broader publication cross-products, and live CPU
  continuity for full-success return siblings outside the pinned normal even-span,
  no-install, status-`2`, row-count-matrix, linear-segmented publication, split-plane
  segmented publication, segmented-wide, and payload-control publication return
  fixtures. Accepted descriptor-record mode bytes are no longer a vague open edge for
  this helper table: fixture `0x16b1a descriptor width helper emits only mode 1/2`
  proves `0x16b1a` writes only mode `1`/`2`, while mode-byte-`0` is documented as an
  unchanged-output object-boundary reject, not a parser-produced renderer mode. Fixture
  `downloaded normal row-0x80 and segmented glyph FF publications render page records`
  covers the row-`0x80` bucket-1 publication sibling for the `0x80`/`0x81` selector
  threshold. Fixture `downloaded glyph width-span matrix publishes and renders all main
  helpers` closes the main compact helper indexes for downloaded-character widths:
  host-fetched spans `1..16` install canonical widths `8..128`, mode bytes alternate
  `2/1` by span parity, odd spans above one use the `0x16942` split-plane copy path, all
  cases publish bucket `0` through FF, and `0x1ed84`/`0x1ef6a` renders rows matching the
  installed bitmap through the `0x1f08e` helper selected by `D1`. Fixture `downloaded
  glyph wide-remainder matrix publishes and renders compact chunks` extends this to
  spans `17..32`: selector `0x1003` publishes bucket `0`, object byte `0x10` dispatches
  to compact target `0x1effe` / `0x1f0d2`, full 16-byte chunks render through `0x2f27c`,
  remainders `1..15` select `0x1f1ac[remainder]`, and span `32` proves the no-remainder
  two-chunk case. The same fixture probes compact-wide spans `33`, `48`, `49`, `64`, and
  `255` through the parser/install/publication and chunk metadata boundary, with matched
  rendered rows for those sampled high spans. Fixture `downloaded glyph width-byte
  boundary truncates page-record span` classifies the next handoff: installed spans from
  `0x00ff` through sampled wrapped spans up to `0x020d` keep canonical width words, but
  the current printable source record gives `0x12f2e` only byte `+0`. Source width bytes
  `0x00..0x10` queue selector `0x0003`; source width bytes `0x11..0xff` queue selector
  `0x1003`. The first `0xff1e` publication edge is pinned too: all cases publish bucket
  `0`, clear the current root, preserve empty rule/fixed lists and context prefix
  `(0, 0, 0, 0)`, and keep the published bucket root equal to the queued page object.
  The first render edge is also pinned: high source bytes stay on compact-wide
  `0x1f0d2`, while low source bytes enter compact mode-0 at `0x1effe` and read helper
  entries outside decoded row-copy helper heads. The model therefore makes no pixel-row
  claim past that wrapped-width source-byte boundary. Fixture `downloaded glyph
  segmented-wide matrix publishes and renders compact chunks` carries the matched span
  set through rows `0x81`: selector `0x3003` publishes buckets `0` and `8`, segment `1`
  dispatches object byte `0x30` to compact target `0x1effe` / `0x1f264`, full chunks
  render through `0x2f27c`, remainders `1..15` select `0x1f1ac[remainder]`, and span
  `32` proves the segmented no-remainder sibling. The same fixture probes segmented-wide
  spans `33`, `48`, `49`, and `64` through the same upstream boundary and compares the
  segment-1 rendered rows with the installed bitmap rows. The covered publication
  fixture set is the primary fixture ledger above, now including the width-span matrix,
  wide-remainder matrix, segmented-wide matrix, row-count matrix, row-`0x80`,
  split-plane segmented, segmented-wide, payload-control wide, no-install, status-`2`,
  and scheduler band-walk siblings.

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
- Descriptor metric producer model: `0x16fae..0x17016` walks the validation
  table at `0x16eae`, using `0x1599c`/`0x159b6`/`0x159d4`/`0x159f6` to read
  unsigned bytes, signed bytes, unsigned words, and signed words. Accepted
  table entries write staging storage under `0x782862`; `0x1719c..0x1725c`
  then copies the sparse staged fields into the allocated payload. In this
  payload family, canonical metric fields are `+0x14` range/count,
  `+0x16` first-code/lower bound, and `+0x1a` signed flagged offset;
  derived/cache fields are `+0x18 = +0x14 - +0x16 - 1` and rounded
  unflagged word `+0x2c`; parser scratch is the validation table cursor,
  `0x783140` payload budget, staged base `0x782862`, and optional symbol
  staging `0x782842..0x782856`; firmware bookkeeping includes type byte
  `+0x0c`, allocation units `0x7827ba`, and byte `+0x2b`, which remains `0`
  in the covered `0x1719c` metric fixtures.
- Metric writer formulas: `0x17430..0x1749c` writes canonical `+0x14`, rejects
  reversed or out-of-range values, and on success derives `+0x18 = value -
  word(+0x16) - 1`; the reversed-range no-install fixture proves the rejected
  branch can leave `+0x14 = 5` while `+0x18` remains `0`. `0x1757a..0x175b8`
  computes `+0x2c = min((value + 2) >> 2, word(+0x14)) << 2`; the boundary,
  low-nibble, and byte-boundary fixtures prove the cap (`0x1500`, `0x1508`,
  and `0x15ff` all become `0x0060` when `+0x14 = 0x0018`; `0x0102` caps to
  `0x0100` when `+0x14 = 0x0040`), low-nibble rounding
  (`0x0001/0x0003/0x0004/0x0005/0x000f` become
  `0x0000/0x0004/0x0004/0x0004/0x0010`), and the `0x00fd..0x0102`
  byte-boundary outputs `0x00fc/0x0100/0x0100/0x0104`. `0x1762a..0x1763c` writes the
  signed byte reader result into payload word `+0x1a`; fixtures prove bytes
  `0x7f`, `0x80`, `0xfe`, and `0xff` copy as `0x007f`, `0xff80`, `0xfffe`, and
  `0xffff` and are consumed by `0xd8fc` as words. Fixture `legal descriptor metric
  mixed values drive d4ac and d8fc consumers` proves the formulas together for
  middle-range `first/range/rounded/offset = 0x0008/0x0030/0x002a/0x02`, copied
  `+0x18/+0x1a/+0x2c = 0x0027/0x0002/0x002c`, the rounded-`0x00ff` cap to
  `+0x2c = 0x00c0`, the offset-byte `0x80` sign extension, and the late first-code
  `0x002f` case deriving `+0x18 = 0`.
- payload `+0x38`: optional-symbol block offset when `0x782856 != 0`.
- glyph pointer table entry: relative offset from payload base to a
  downloaded character object, for example table entry `0x00de` points to
  record delta `0x0500` in the `ESC )s2193W` fixture.
- downloaded character object `+0x04`: bitmap delta `0x0c` written by
  `0x16498`.
- downloaded character object `+0x05`: glyph bitmap mode. Parser-produced
  descriptors reach this byte through `0x16b1a`, where fixture `0x16b1a
  descriptor width helper emits only mode 1/2` proves accepted widths write
  only mode `1` for even byte spans and mode `2` for odd byte spans. Fixture
  `0x16498 replacement allocation failure partial and rejected downloaded
  character exits preserve state` proves the artificial object-boundary mode
  `0` record exits as `unsupported-record-shape` without changing the header.
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
- legal metric low-nibble rounding: fixture
  `legal descriptor metric low-nibble rounding drives d4ac and d8fc consumers`
  varies rounded inputs `0x0001`, `0x0003`, `0x0004`, `0x0005`, and `0x000f`
  while leaving canonical `+0x14/+0x16 = 0x0018/0x0004`, derived/cache
  `+0x18 = 0x0013`, and copied offset `+0x1a = 0x0001` fixed. `0x1719c`
  copies the rounded words to `+0x2c =
  0x0000/0x0004/0x0004/0x0004/0x0010`; `d4ac` consumes those
  `+0x2c/+0x2d` bytes and keeps the default span digest, while `d8fc` keeps
  high-y `20` and row digest
  `f830d30ea60a61f0b74a489c4b7df1bb25dc464b6765d170c19e7278a0267eab`.
- legal metric byte-boundary rounding: fixture
  `legal descriptor metric byte-boundary rounding drives d4ac and d8fc
  consumers` varies rounded inputs `0x00fd`, `0x00fe`, `0x0101`, and
  `0x0102` with range/count `+0x14 = 0x0042`, then repeats `0x0102` with
  range/count `+0x14 = 0x0040`. `0x1719c` copies `+0x2c =
  0x00fc/0x0100/0x0100/0x0104`, while the capped range copies `0x0100`.
  The `0x00fd` case leaves `d4ac` at `beyond-page-extent` with compact-only
  row digest `86e3bb70d51c66ac608345dc3bff6476447ebc500d7c271808a53d6638d59ad6`.
  Crossing to `0x00fe` changes the byte consumers to `+0x2c/+0x2d = 1/0`,
  so `d4ac` emits the standard span digest
  `67554ea70d7cfd9b11c0777e3cf65d51600a44301a4f93bd4d9b0c0fbc23c00e`; the
  `0x0101`, uncapped `0x0102`, and capped `0x0102` cases keep that digest.
  The same fixture proves the large derived/cache heights
  `+0x18 = 0x003d` or `0x003b` make `d8fc` exit `beyond-page-extent` with
  compact-only digest
  `1a73b5e7454202d800c69f626bcf34e7d0d583b459e04c0bd4250010bf3ba28a`.

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

Fixture `0x15d0a descriptor grammar exits and handler matrix` pins the
parser-front exits before any object handler runs:

- `count-below-three`: byte budget `2` is drained without reading descriptor
  bytes.
- `parser-mode-2`: byte budget `3` is drained while `0x782a92 == 2`.
- `source-exhausted-before-descriptor`: descriptor byte `0` is fetched, then
  the remaining two budget bytes drain when descriptor byte `1` is unavailable.
- `current-record-not-found`: descriptor `04 00 aa` consumes the descriptor
  prefix, `0x172c0` reports scan status `2`, and the final byte drains.
- `missing-continuation`: descriptor `04 01 cc` consumes the descriptor
  prefix, finds no continuation state, and drains the final byte.

The same fixture pins all four route polarities:

- current-record selector `0`, object bit `30` set: payload `0x456789` routes
  to `0x16498`.
- current-record selector `0`, object bit `30` clear: payload `0x456789`
  routes to `0x16606`.
- continuation selector nonzero, object bit `30` set: saved payload
  `0x654321` routes to `0x15b9a`.
- continuation selector nonzero, object bit `30` clear: saved payload
  `0x654321` routes to `0x15c4c`.

In each fixture case the remaining budget reaches `0` at the route/drain
boundary, so the next parser byte is not consumed by the descriptor route.

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

Fixture `0x1887a release variant matrix covers cleanup branches` extends the
same shared exit beyond the allocation-failure fixture. A bit-30-set class-one
payload `0x40123456` with range words `+0x0e/+0x10 = 0x0030/0x0032` dispatches
through `0x18b92`, calls `0x17fa2` for chars `0x30..0x32`, decrements the
unmarked-record count `0x782782`, total counters `0x78278e`/`0x78278a`,
class-one counters `0x782796`/`0x782790`, shifts cursors
`0x7827ac/0x7827b0/0x7827b4` by four, clears matching continuation state,
marks context-stack primary byte `+8`, refreshes the active primary context
through `0x179aa(0)`, and joins `0x1b04c`. A bit-30-set class-zero marked
payload `0x40234567` with reversed range `0x0044..0x0042` still routes through
`0x18b92` but has zero character cleanup calls, decrements marked-record count
`0x782786`, total counters `0x78278e`/`0x78278a`, and class-zero counters
`0x78279e`/`0x782798`, leaves class-one cursors unchanged, leaves nonmatching
continuation state intact, marks context-stack secondary byte `+9`, and joins
`0x1b04c` without active refresh. A bit-30-clear class-zero payload
`0x00345678` with payload byte `+0x0e = 0` dispatches through `0x18bf2`, calls
`0x18090` for fixed-record chars `0x21..0x7f`, decrements unmarked-record,
total, and class-zero counters, leaves class-one cursors unchanged, refreshes
the active secondary context through `0x179aa(1)`, and joins `0x1b04c`.
Canonical state is the cleared current-record id/payload and released
payload-table entries. Derived/cache state is the active-context refresh.
Parser scratch is the continuation record, which is cleared only when
`0x7827da` matches the released payload. Firmware bookkeeping is the
candidate/counter/cursor/context-stack/default-refresh work. No direct output
pixels change on this release path; the visible effect is preventing later
printable bytes from selecting the released payload.

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

For reproduction, the consumed-but-not-staged entries are not hidden state:
their ROM effect is complete when the reader advances the descriptor stream and
the pass predicate returns success. They remain unknown only as HP/manual field
names.

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

### Downloaded Resource Validation No-Install Checkpoint

This checkpoint composes the downloaded-resource validation error cluster from
host-fetched `ESC )s80W` and short-budget `ESC )s8W` streams to visible
default-font output. It covers the bounded parser-produced failure cases where
`0x16fae` rejects the descriptor before `0x17026` can allocate a resource
payload.

Field groups:

- Canonical downloaded-font state:
  - current-record pool `0x782640..0x782776`;
  - candidate count/cursor fields `0x78278e`, `0x782790`, `0x782796`,
    `0x782798`, `0x78279e`, `0x7827a0`, `0x7827ac`, `0x7827b0`, and
    `0x7827b4`;
  - selected candidate longword installed by `0x16c14` / `0x1bc38` on
    success.
  The validation-failure fixtures assert that these canonical install fields
  are not changed.
- Parser scratch:
  - restored records `80 57 00 50 00 00` for the normal failed `ESC )s80W`
    streams and `80 57 00 08 00 00` for the short-budget stream;
  - payload budget `0x783140`, parser record cursor `0x78299e`, host byte
    source `0xa904`, and parser handlers `0x11eb6`, `0x12008`, `0x11ff6`,
    and `0x11f96`.
- Parser-owned staged descriptor fields:
  - staged header `0x7827de` and staged payload base `0x782862`;
  - type byte `+0x0c`, first-code word `+0x16`, line/count word `+0x12`,
    range/count word `+0x14`, derived count word `+0x18`, and class byte
    `+0x20`;
  - optional symbol bytes `0x782842..0x782851` and count `0x782856`, which
    remain empty for the covered failures because validation stops before the
    optional-symbol tail.
- Derived/cache descriptor state:
  - `+0x18` is derived by entry-6 helper `0x17430` as range/count minus
    first code minus one when entry 6 is reached and accepted far enough;
  - rounded unflagged metric `+0x2c` is not owned by these no-install cases,
    but its successful entry-12 formula is documented in
    [font-context-metrics.md](font-context-metrics.md).
- Firmware bookkeeping:
  - validation status `0`, allocation status `0`, install state `None`, and
    drained host source are failure bookkeeping. They gate the next printable
    byte back to the unchanged default-font path.
- Unknown:
  - HP manual labels for consumed-but-not-staged descriptor fields.

Writers:

- `0x16fae` stages descriptor fields as each validation entry succeeds.
- `0x17362` writes type byte `+0x0c` and payload units for entry `2`; invalid
  type byte `3` fails before allocation size exists.
- `0x173d0` handles entry `4`; first-code word `0x1068` fails before writing
  payload word `+0x16`.
- `0x173fe` handles entry `5`; zero and high line/count values fail with no
  valid line/count payload. The short-budget `ESC )s8W` case reaches the same
  predicate after byte-budget exhaustion.
- `0x17430` handles entry `6`; reversed and high range/count values fail at
  the twelve-byte boundary.
- `0x1749e` handles entry `7`; class byte `2` fails after staging previous
  range fields but before writing class byte `+0x20`.

Readers and consumers:

- `0x17026` consumes validation status `0` and skips payload allocation.
- `0x16c14` consumes allocation status `0` and installs no candidate.
- After the failed resource command drains, `0xd04a`, `0x1393a`, `0x12f2e`,
  `0x1ed84`, and `0x1ef6a` consume the following printable `!` through the
  unchanged default-font compact path.

Output effect:

- Invalid resource type, first-code overflow, zero line/count, high
  line/count, short descriptor budget, reversed range/count, high range/count,
  and invalid class all produce the same visible output for the following
  printable byte.
- No downloaded-font candidate is installed, no current-record payload is
  selected, the queued compact object matches the baseline default-font `!`,
  and the rendered rows match the baseline rows.

Confidence:

- High for the covered parser boundaries, failed entries, last staged fields,
  allocation skip, no-install result, resumed printable handler, default
  compact object, and rendered rows because
  `ESC )s#W validation failures preserve following printable output` asserts
  all eight visible recovery cases.
- High for ROM-internal rejecting validation coverage because only entries
  `2`, `4`, `5`, `6`, and `7` can return failure; the remaining validation
  table entries are pass-through, clamps, or field writers.

Fixture evidence:

- `0x16fae validation table semantic map covers staged and pass-through
  entries`
- `0x16fae table-driven validation predicates populate staged header fields`
- `ESC )s80W invalid resource type fails validation before allocation`
- `ESC )s80W reversed resource range fails validation before allocation`
- `ESC )s80W additional validation predicate failures skip allocation`
- `ESC )s#W validation failures preserve following printable output`

Disassembly evidence:

- `generated/disasm/ic30_ic13_font_resource_validate_016fae.lst`
- `generated/disasm/ic30_ic13_font_resource_validate_predicates_017358.lst`
- `generated/disasm/ic30_ic13_font_resource_find_017026.lst`
- `generated/disasm/ic30_ic13_font_resource_object_add_016c14.lst`
- `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`
- `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`

Unresolved middle edges:

- `0x16fae..0x17016`: fixture-backed for the seven bounded `ESC )s80W`
  no-install exits and the short-budget `ESC )s8W` entry-5 failure, including
  resumed visible output. This covers every ROM-internal rejecting predicate
  family. No ROM-internal validation no-install edge remains; the remaining
  validation work is external HP manual naming for consumed-but-not-staged
  fields already named by ROM effect in the table above.

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
- glyph record bytes are `00 00 00 00 0c 02 00 81 00 88 00 00`.
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

Fixture `segmented downloaded glyph composes with raster through 0x1ef6a`
extends the same composition contract to the segmented selector family. It
reuses the host-fetched `ESC )s258W` install for glyph `0x27`: table entry
`0x00e6`, record delta `0x0580`, bitmap offset `0x058c`, and bitmap size
`0x0102`. `0x12f2e` queues selector `0x2003` segment objects in bucket `9`
(`00 00 00 00 20 03 00 01 27 01 66 01...`) and bucket `1`
(`00 00 00 00 20 03 00 01 27 00 66 01...`). The same page record also carries
mode-0 raster object `00 00 00 00 80 00 00 02 00 00 c3 3c` in bucket `9`.
Render entry `0x1ed84`/`0x1ef6a` for bucket word `9` dispatches the raster
object to `0x1f88e`, then dispatches the segment-1 downloaded glyph object to
`0x1effe` / `0x1f1f0`, and compares the seven composed rows with digest
`0b5440d6733ab9a072e0c14d1a470e6bc944dc98ddbf789152cf65c945dd0f01`. This
closes the segmented-glyph plus raster composition edge; selector-7 rule
composition remains covered by the even-span wide fixture and by separate
rectangle/rule render fixtures.

Fixture `split-plane segmented downloaded glyph composes with raster through
0x1ef6a` proves the same composition for the split-plane reader. It reuses the
host-fetched `ESC )s387W` install for glyph `0x28`: table entry `0x00ea`,
record delta `0x0700`, bitmap offset `0x070c`, bitmap size `0x0183`, span `3`,
and split-plane copy layout with prefix bytes ending `f0 0f` plus trailing
byte `aa`. `0x12f2e` queues selector `0x2003` segment objects in bucket `9`
(`00 00 00 00 20 03 00 01 28 01 66 01...`) and bucket `1`
(`00 00 00 00 20 03 00 01 28 00 66 01...`). The same page record also carries
mode-0 raster object `00 00 00 00 80 00 00 02 00 00 c3 3c` in bucket `9`.
Render entry `0x1ed84`/`0x1ef6a` for bucket word `9` dispatches the raster
object to `0x1f88e`, then dispatches the split-plane segment-1 glyph object to
`0x1effe` / `0x1f1f0`, and compares the seven composed rows with digest
`a380045041433910619b809637eda41e81842a3516acb83b488d07f1d3c68872`.

Fixture `segmented downloaded glyph raster FF publications render page records`
then carries both segmented+raster page records through `0xff1e`. For the
linear case, `0xff1e` publishes bucket `9` with raster object
`00 00 00 00 80 00 00 02 00 00 c3 3c` followed by segment-1 object
`00 00 00 00 20 03 00 01 27 01 66 01...`, preserves bucket `1` segment-0
object `00 00 00 00 20 03 00 01 27 00 66 01...`, and renders the published
bucket word `9` with digest
`0b5440d6733ab9a072e0c14d1a470e6bc944dc98ddbf789152cf65c945dd0f01`. For the
split-plane case, the same publication path preserves bucket `9` raster plus
segment-1 object `00 00 00 00 20 03 00 01 28 01 66 01...`, preserves bucket
`1` segment-0 object `00 00 00 00 20 03 00 01 28 00 66 01...`, and renders
digest `a380045041433910619b809637eda41e81842a3516acb83b488d07f1d3c68872`.

Fixture `parser-driven downloaded glyph rule raster stream composes through
0x1ef6a` then makes the rule and raster producers parser-driven in the same
page stream. The fetched stream is 54 bytes: font bytes `0..24` are the
`ESC )s18W` command and payload above, and page bytes `24..54` are
`ESC *c12a3b0P ) ESC *t300R ESC *r0A ESC *b2W c3 3c`. The whole 54-byte stream
is fetched through one `0xa904` ring source, with source set `["ring"]` and no
remaining ring bytes, so the byte-source side is continuous across the font/page
boundary. The page parser routes through `0x10e68`, `0x10e22`, `0x10898`,
`0xd04a`, `0x10808`, `0x1075a`, and delayed raster handler `0x11f82` /
`0x105d0`. It queues the same bucket-5 downloaded glyph object
`00 00 00 00 10 03 00 01 29 06 01...`, the same bridged selector-7 rule
`00 00 00 00 05 17 08 01 00 0c 00 03 00 03`, and the same mode-0 raster object
`00 00 00 00 80 00 00 02 00 00 c3 3c`. Render entry `0x1ed84`/`0x1ef6a`
dispatches the raster object to `0x1f88e`, the glyph object to
`0x1effe`/`0x1f0d2`, the rule to `0x1f596`, and compares the same three composed
rows. The remaining limitation is not byte fetch; the modeled font-install
memory boundary is now explicit. The fixture uses the font-command helper's
`final_header` as the parser-driven page memory image and asserts that it matches
the install event header before resolving the printable downloaded glyph.

The modeled install-to-page handoff is now documented as a concrete resource
image contract rather than a vague fixture split. In fixture
`host-fetched even-span wide downloaded character renders through 0x1f0d2`,
the host-fetched `ESC )s18W` bytes enter delayed handler `0x16c14` through
parser handlers `0x11eb6`, `0x12008`, `0x11ff6`, and `0x11f96`. Handler
`0x16498` installs glyph `0x29` by writing table entry `0x00ee`, record delta
`0x0780`, record bytes `00 00 00 00 0c 01 00 01 00 90 00 00`, bitmap offset
`0x078c`, bitmap size `18`, and the 18 linear bitmap bytes
`f0 0f aa 55 3c c3 81 7e ff 00 18 e7 24 db 42 bd 66 99`. Fixture
`parser-driven downloaded glyph rule raster stream composes through 0x1ef6a`
then uses `font_command_final_header` from that same host-fetched font-command
helper as its resource image. The fixture asserts that `final_header` matches
the install event header and contains pointer bytes `00 00 07 80` at table entry
`0x00ee`, the installed record at `0x0780`, and the bitmap bytes at `0x078c`.
With that image, printable byte `0x29` resolves to glyph entry `0x0780`, bitmap
`0x078c`, width `0x0090`, rows `1`, source kind `downloaded-pointer`, inline
record `12 01 00`, and context slot `3` before `0x12f2e` queues selector
`0x1003`.

That handoff divides canonical state from parser scratch. Canonical resource
state is the installed glyph table entry, record, bitmap, and copied bitmap
bytes above. Parser scratch is the restored font payload record
`80 57 00 12 00 00`, payload offset `6`, and stream byte range `0..24`, plus
the later page parser range `24..54` and raster scratch record
`80 57 00 02 00 00` at payload offset `28`. Derived/cache state is the page
bucket chain, normalized rule object, `0x1ed84` active copy, and `0x1ef6a`
dispatch fields. The return boundary is now fixture-pinned for this even-span
path: fixture `parser-driven downloaded glyph rule raster stream composes
through 0x1ef6a` records call edge `0x15dc6 -> 0x16498`, return edge
`0x16498 -> 0x15dcc`, drain edge `0x15dcc -> 0x12328`, font end byte `24`,
copy status `1`, copy stream position `18`, remaining `0x783140 = 0`, a
zero-byte `0x12328` drain, next stream prefix `ESC *c12a`, and the next parser
handler `0x10e68`.

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
status-`2` case parses a mode-byte-`1` bitmap descriptor through `0x16336`,
copies four of six bitmap bytes through `0x168dc`, stores
table entry `0x00f6 -> 0x0840`, writes record
`00 00 00 00 0c 01 00 03 00 10 00 00`, leaves bitmap bytes
`f0 0f aa 55 00 00`, and saves continuation fields equivalent to
`0x7827c6 = 1`, `0x7827da = 0`, `0x7827c8 = 0x2b`,
`0x7827ca = 0x0850`, `0x7827d2 = 2`, and zero split-plane counters. The
split-plane status-`2` case parses a mode-byte-`2` descriptor for odd span
`3`, copies prefix bytes `a0 a1` and trailing byte `b0` through `0x16942`,
stores table entry `0x00fa -> 0x0880`, writes record
`00 00 00 00 0c 02 00 02 00 18 00 00`, leaves bitmap layout
`a0 a1 00 00 b0 00`, and saves `0x7827ca = 0x088e`,
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
downloaded-character object.

The no-install rejects split into two different field families. A synthetic
descriptor/object mode byte outside the parser-produced `1`/`2` set is
rejected by the pre-copy record-shape guard after the `0x16336` descriptor
parse, so the mode-`0` fixture returns status `0`, reason
`unsupported-record-shape`, and leaves table entry `0x00fe` at zero. A high
character code is checked against the font-header type byte:
`0x164f2..0x16540` allows `0x80..0xff` only when header byte `+0x0c >= 1`, so
the `0xa0` fixture with header byte `+0x0c = 0` returns status `0`, reason
`char-outside-header-type`, and leaves table entry `0x02ca` at zero. Both
reject families return before `0x1658e..0x16602` stores the allocated-object
pointer, so they are parser scratch/firmware bookkeeping exits rather than
canonical renderer-state changes.

Fixture `0x16498 no-install exits preserve following printable output` carries
the three no-install branches above to visible output. Each case starts from a
host-fetched `ESC )s6W` command plus six payload bytes, restores record
`80 57 00 06 00 00`, dispatches delayed handler `0x16c14`, appends printable
`!`, and now appends trailing FF. The allocation-failure case returns reason
`allocation-failed`, the mode-0 case returns `unsupported-record-shape`, and
the `0xa0`/header-type case returns `char-outside-header-type`. In all three
cases the following printable byte routes through `0xd04a`, queues the same
default-font compact object as baseline `!`, and renders identical rows. The
return boundary is also pinned for all three cases: the path records
`0x15dc6 -> 0x16498`, `0x16498 -> 0x15dcc`, and `0x15dcc -> 0x12328`,
leaves `0x783140 = 6`, drains the rejected payload bytes through `0x12328`
(`de ad be ef ca fe` for allocation failure and `f0 0f aa 55 3c c3` for
mode/range reject), then resumes at printable handler `0xd04a` for `!`. The
trailing FF routes through `0xf0f0`, publishes the default-font bucket through
`0xff1e`, clears the current page root, and renders the published record
through `0x1ed84`/`0x1ef6a` with the same rows. This classifies the failed
downloaded-character command as firmware bookkeeping and parser scratch, not
canonical renderer state; the published page-record bucket is derived output
state from the unchanged default-font printable path.

Fixture `0x16498 status-2 partial installs remain printable` covers the
opposite non-success branch: status `2` is a partial install, not a no-install.
The linear case starts from host-fetched `ESC )s4W f0 0f aa 55`, restores
record `80 57 00 04 00 00`, stores table entry `0x00f6 -> 0x0840`, leaves
bitmap bytes `f0 0f aa 55 00 00`, and saves continuation state with
destination `0x0850` and remaining count `2`. A following printable `+`
resumes after `0x15dc6 -> 0x16498 -> 0x15dcc -> 0x12328` with
`0x783140 = 0`, a zero-byte drain, and handler `0xd04a`; it resolves glyph
`0x2b`, queues short selector `0x0003`, and renders rows from the copied bytes
plus the zero-filled missing row. The same page-record object
now finalizes through `0xff1e` on a trailing FF: publication keeps bucket `1`,
copies compact object `00 00 00 00 00 03 00 01 2b 66 01`, clears the current
page root, and renders the published record through `0x1ed84`/`0x1ef6a` with
the same rows.

The split-plane case starts from `ESC )s3W a0 a1 b0`, stores table entry
`0x00fa -> 0x0880`, leaves layout `a0 a1 00 00 b0 00`, saves A4/A3
continuation destinations `0x088e`/`0x0891`, and a following printable `,`
resumes through the same return edges with `0x783140 = 0`, a zero-byte
`0x12328` drain, and handler `0xd04a`; it resolves glyph `0x2c`, exposes
inline record `04 02 00`, queues selector `0x0003` with width `4`, and renders
from prefix bytes `a0 a1` plus trailing byte `b0`. Its trailing-FF publication
also keeps bucket `1`, copies compact
object `00 00 00 00 00 03 00 01 2c 66 01`, clears the current page root, and
renders the published record through `0x1ed84`/`0x1ef6a` with the same rows.

Fixture `0x15b9a resumes downloaded-character continuation objects` covers the
descriptor-selected continuation success sibling. The linear case starts from
the previous `0x16498` status-`2` object at table entry `0x00f6 -> 0x0840`:
`0x15b9a` reloads saved glyph `0x2b`, reads record
`00 00 00 00 0c 01 00 03 00 10 00 00`, derives span `2` from width `0x0010`,
copies resume bytes `c3 3c` through `0x168dc` into destination `0x0850`, and
clears continuation state after completing bitmap `f0 0f aa 55 c3 3c`.

The split-plane case starts from table entry `0x00fa -> 0x0880`: `0x15b9a`
reloads saved glyph `0x2c`, reads record
`00 00 00 00 0c 02 00 02 00 18 00 00`, derives byte span `3` and prefix span
`2`, resumes through `0x16942` with saved destinations `0x088e`/`0x0891` and
D4/D3 counters `1/0`, copies prefix bytes `c0 c1` plus trailing byte `d0`, and
clears continuation state after completing layout `a0 a1 c0 c1 b0 d0`.
Disassembly evidence is `0x15b9a..0x15bdc` for table/object lookup and scratch
span/row writes, `0x15bdc..0x15bec` for the resume-mode `0x16874` call,
`0x15bee..0x15c18` for status dispatch, and `0x15c18..0x15c4a` for
continuation clearing.

Fixture `0x15b9a partial and failed resumes update continuation or release
object` covers the other copy-status exits from the same handler. A second
linear partial copies only resume byte `c3`, leaves bitmap
`f0 0f aa 55 c3 00`, advances destination from `0x0850` to `0x0851`, and
resaves remaining count `1`. A split-plane partial copies only prefix byte
`c0`, leaves layout `a0 a1 c0 00 b0 00`, advances prefix destination from
`0x088e` to `0x088f`, keeps trailing destination `0x0891`, and resaves D4/D3
counters `0/0`.

The failure sibling copies the same single linear byte `c3` but then exhausts
the source before completing the remaining byte, so `0x15bee..0x15c18` takes
the status-`0` release path. `0x17a24` clears offset-table entry `0x00f6`
from old record `00 00 08 40` to `00 00 00 00`, records an active-primary
refresh through `0x1b4c0`/`0x14c64`, and clears the matching continuation
fields. That makes the partially rewritten object body unreachable from the
font table.

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
the return boundary through `0x15dc6 -> 0x16498 -> 0x15dcc -> 0x12328` with
`0x783140 = 0`, a zero-byte `0x12328` drain, and next handler `0xd04a` for
printable `'`. Tail handlers `0xd04a` and `0xf0f0` publish bucket `9` object
`00 00 00 00 20 03 00 01 27 01 66 01`, and also preserves the segment-0 bucket
`1` entry. The published record has empty rule/fixed lists, context slots
`(0, 0, 0, 0)`, cleared current root, render bucket word `9`, compact target
`0x1effe`, object byte `0x20`, context slot `3`, and renderer `0x1f1f0`, which
reads the segment-1 source row from offset `0x0100`.

Fixture `host-fetched rows-0x82 segmented downloaded glyph FF publication
renders page record` covers an interior segmented row count in the same
selector family, not just the `0x80`/`0x81` threshold. The stream is
`ESC )s260W` plus printable `0` and FF. The font phase restores record
`80 57 01 04 00 00`, installs glyph `0x30` at table entry `0x010a`, writes
record `00 00 00 00 0c 01 00 82 00 10 00 00`, copies `0x0104` linear bytes,
and queues selector `0x2003`. Publication copies bucket array entries `1` and
`9`; rendering bucket word `9` through `0x1ed84`/`0x1ef6a` and compact target
`0x1effe`/`0x1f1f0` produces two segment-1 rows, `####........####` and
`#.#.#.#..#.#.#.#`, at x `22`.

Fixture `downloaded glyph width-span matrix publishes and renders all main
helpers` covers the downloaded-character width/span side of the same command
family. It drives sixteen host-fetched `ESC )s#W` streams whose descriptor
widths produce spans `1..16`, canonical installed width words `0x0008..0x0080`,
row word `0x0003`, and mode bytes `2` for odd spans or `1` for even spans.
Parser scratch is the restored `80 57 #W` record and payload byte count;
canonical state is the installed table entry, record, bitmap bytes, and
split-plane flag; derived/cache state is the bucket-0 published page record and
the `0x1f08e[D1]` helper. All sixteen cases return through
`0x15dc6 -> 0x16498 -> 0x15dcc -> 0x12328` with copy status `1`,
`0x783140 = 0`, no drained bytes, and next handler `0xd04a`; `0x1ed84` /
`0x1ef6a` then dispatches object byte `0x00` to compact target `0x1effe`.
Rows rendered by helpers `0x1fa5c`, `0x1fe76`, `0x20290`, `0x207ac`,
`0x20cc8`, `0x212e4`, `0x21900`, `0x2201c`, `0x22738`, `0x22f54`,
`0x23770`, `0x24090`, `0x249b0`, `0x253d0`, `0x25df0`, and `0x26910` match
the installed bitmap rows in the fixture.

Fixture `downloaded glyph wide-remainder matrix publishes and renders compact
chunks` covers the compact-wide sibling of that width/span matrix. It drives
host-fetched `ESC )s#W` streams whose descriptor widths produce spans `17..32`,
canonical installed width words `0x0088..0x0100`, row word `0x0003`, and mode
bytes `2` for odd spans or `1` for even spans. Canonical state is the
installed table entry, record, bitmap bytes, and split-plane flag.
Derived/cache state is selector `0x1003`, object byte `0x10`, bucket `0`,
full-chunk helper `0x2f27c`, `full_row_skip`, `remainder_row_skip`, and the
selected remainder helper. Remainders `1..15` select
`0x1f1ac[remainder]`; span `32` has remainder `0` and therefore uses two full
16-byte chunks with no remainder helper. All matched cases return through
`0x15dc6 -> 0x16498 -> 0x15dcc -> 0x12328` with copy status `1`,
`0x783140 = 0`, no drained bytes, and next handler `0xd04a`; `0x1ed84` /
`0x1ef6a` then dispatches compact target `0x1effe` / `0x1f0d2`, and rendered
rows match the installed bitmap rows.

The same fixture now adds compact-wide high-span probes `33`, `48`, `49`,
`64`, and `255`. These probes keep the same canonical fields and return
boundary, prove additional full-chunk counts `2`, `3`, `4`, and `15`, and keep
the expected remainder/no-remainder helper choices. The fixture now replays the
`0x2f27c` full-chunk source walk and `0x1f1ac[remainder]` tail into row bytes,
passes render width word `max(0x20, span)`, and matches the installed bitmap
rows for those high spans. Width helper fixture
`0x16b1a descriptor width helper emits only mode 1/2` still proves accepted
descriptor width `0x1068` rounds to span `0x020d`.

Fixture `downloaded glyph width-byte boundary truncates page-record span`
turns that upper range into an explicit source-byte boundary. It installs
downloaded spans `0x00ff`, `0x0100`, `0x0101`, `0x0102`, `0x010f`,
`0x0110`, `0x0111`, `0x017f`, `0x0180`, `0x01fe`, and `0x020d` through
`0x16498`, preserving canonical width words in the object record at `+8`. The
current unflagged printable source record presented to `0x12f2e` still exposes
only byte `+0`: source width bytes `0x00..0x10` queue selector `0x0003`, while
source width bytes `0x11..0xff` queue selector `0x1003`. All cases then
publish bucket `0` through `0xff1e`; the current root clears, rule/fixed lists
stay empty, context prefix stays `(0, 0, 0, 0)`, and the published bucket root
matches the queued page object. The render edge is now pinned for the same
cases: source width bytes `0x11..0xff` remain compact-wide through `0x1f0d2`,
but source width bytes `0x00..0x10` enter compact mode-0 at `0x1effe` and read
helper-table entries outside decoded row-copy helper heads, including
`0x20700000`, `0x4e90202c`, and `0x4e904cdf`. The model makes no pixel-row
claim past the wrapped-width source-byte boundary.

Fixture `downloaded glyph segmented-wide matrix publishes and renders compact
chunks` covers the segmented-wide sibling. It drives host-fetched `ESC )s#W`
streams whose descriptor widths produce spans `17..32`, row word `0x0081`,
selector `0x3003`, and mode bytes `2` for odd spans or `1` for even spans.
Canonical state is the installed table entry, record, bitmap bytes, and
split-plane flag. Derived/cache state is segment-1 bucket `8`, segment-0
bucket `0`, object byte `0x30`, segment row skip `0x80`, A2/A3 source offsets,
full-chunk helper `0x2f27c`, and the selected remainder helper. Remainders
`1..15` select `0x1f1ac[remainder]`; span `32` has remainder `0` and uses two
full chunks with no remainder helper. All matched cases return through
`0x15dc6 -> 0x16498 -> 0x15dcc -> 0x12328` with copy status `1`,
`0x783140 = 0`, no drained bytes, and next handler `0xd04a`; `0x1ed84` /
`0x1ef6a` then dispatches compact target `0x1effe` / `0x1f264`, and rendered
segment-1 rows match the installed bitmap rows.

The same fixture now adds segmented-wide high-span probes `33`, `48`, `49`,
and `64` at rows `0x81`. They prove bucket `8` / segment `1`, bucket `0` /
segment `0`, object byte `0x30`, segment row skip `0x80`, A2/A3 offsets, and
full-chunk/remainder metadata through the same zero-drain return boundary.
Their segment-1 rendered rows now match installed bitmap rows through
`0x1f264`, `0x2f27c`, and the selected `0x1f1ac` remainder helper, so the
remaining segmented-wide gaps are broader row-count/segment cross-products, not
the sampled high-span source walk.

Fixture `downloaded segmented-wide row-byte boundary truncates page-record
segments` classifies the row-count side of that cross-product for span `0x11`.
It installs canonical row words `0x0002`, `0x007f`, `0x0080`, `0x0081`,
`0x0083`, `0x00fe`, `0x00ff`, `0x0100`, `0x0101`, `0x0181`, `0x0182`,
`0x01ff`, `0x0200`, and `0x0201` through `0x16498`, preserving those words in
the object record at `+6`. The current unflagged printable source record
presented to `0x12f2e` exposes only byte `+1`: low row bytes above `0x80`
queue selector `0x3003` for segments `1` and `0`, while low row bytes
`0x00..0x80` queue selector `0x1003`. The same cases publish through
`0xff1e`: segmented cases publish buckets `0` and `8` with selected bucket
`8`, while compact-wide cases publish only bucket `0`; all preserve empty
rule/fixed lists and context prefix `(0, 0, 0, 0)`. The render edge keeps the
canonical installed row word after selector choice: rows `0x0100` and
`0x0101` dispatch to `0x1f0d2` and split as `80/176` and `80/177`
current/fallback rows. Row `0x0181` dispatches only the produced `0x1f264`
segment objects: segment `1` in bucket `8` splits `32/96`, segment `0` in
bucket `0` splits `80/48`, and no segment above `1` is present for rendering.

Fixture `downloaded glyph row-count matrix publishes and renders additional
short/segmented counts` broadens the same command family. Short rows `0x0001`,
`0x0002`, `0x0003`, `0x0004`, `0x0005`, `0x0006`, `0x0007`, `0x0008`,
`0x0009`, `0x000a`, `0x000b`, `0x000c`, `0x000d`, `0x000e`, `0x000f`,
`0x0010`, `0x0011`, `0x0012`, `0x0013`, `0x0014`, `0x0015`, `0x0016`,
`0x0017`, `0x0018`, `0x0019`, `0x001a`, `0x001b`, `0x001c`, `0x001d`,
`0x001e`, `0x001f`, `0x003e`, `0x003f`, `0x0041`, `0x0042`, and `0x007f`
restore fetched `ESC )s#W` records, install mode-byte-`1` records ending in
matching row words, publish only bucket `1`, keep selector `0x0003`, and
dispatch compact target `0x1effe` with object byte `0x00`. Segmented rows
`0x0083`, `0x0084`, `0x0085`, `0x0086`, `0x00bf`, `0x00c0`, `0x00c1`,
`0x00fd`, `0x00fe`, and `0x00ff` install matching mode-byte-`1` records,
publish buckets `1` and `9`, keep selector `0x2003`, and render bucket word
`9` through compact target `0x1effe` with object byte `0x20`.
The published-row counts are `7`, `8`, `9`, `10`, `11`, `12`, `13`, `14`, `15`,
`16`, `17`, `18`, `19`, `20`, `21`, `22`, `23`, `24`, `25`, `26`, `27`, `28`,
`29`, `30`, `31`, `32`, `33`, `34`, `35`, `36`, `37`, `64`, `64`, `64`, `64`,
`64`, `9`, `10`, `11`, `12`, `16`, `16`, `16`, `16`, `16`, and `16`.
All forty-six cases now also pin the full-success return boundary
`0x15dc6 -> 0x16498 -> 0x15dcc -> 0x12328`: copy status is `1`, `0x783140` is
`0`, `0x12328` drains no bytes, and the next parser handler is `0xd04a` for
printable bytes `0x38`, `0x3b`, `0x41`, `0x34`, `0x43`, `0x4a`, `0x4b`,
`0x3c`, `0x44`, `0x4c`, `0x4d`, `0x4e`, `0x4f`, `0x50`, `0x51`, `0x45`,
`0x52`, `0x53`, `0x54`, `0x55`, `0x56`, `0x57`, `0x58`, `0x59`, `0x5a`,
`0x5b`, `0x5c`, `0x5d`, `0x5e`, `0x5f`, `0x60`, `0x61`, `0x42`, `0x3d`,
`0x46`, `0x35`, `0x36`, `0x39`, `0x3e`, `0x47`, `0x48`, `0x3f`, `0x49`,
`0x40`, `0x3a`, and `0x37`. Rows `0x0006` and `0x0007` render `12` and
`13` rows with digests
`b791b24072d4758b9a4e40ae7600cd7e0b2bbbe3757dd001f8819dc6d94a5b7a` and
`d2beea9dbf9a604abeb5fe8cc87636002405da8f46d6cbbf585af7e7481cd088`; rows
`0x000a` through `0x000f` render `16` through `21` rows with digests
`a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932`,
`3830ca130052dd9f7ce79cf1c1e427cd3b5f992534e55ae45baebed3c84f9465`,
`12afecf01d69fbaf6a6b6798528fd1fd5855067537b9122b4643eb9736325e5d`,
`d85196db9e646951a3df3ae39725bda5d759fc37a54885e6ea7b87c697c52198`,
`bc0243b6594c80656ae2a00f04d072afaba854c4b892a73893a4df144b55f40c`, and
`4fb2a253d67451397844fa77e3f41949a6ef5d7542d64609710f0dfdd371fd0e`. Rows
`0x0010` through `0x001f` render `22` through `37` rows with digests
`f7c5a4f154a9515a9787f30676de81c1b248f2aacc0b7c2df0f66042689e7900`,
`f0bcf79ee5c12cfb0b1e02660e080073f58b6a24aca83943fb81ba01330358ce`,
`75ad70f7657d7d88bfad58baa76c0dd1597e4807a5e5c7f469e2060153133e4d`,
`87d3ee023ae18013588aa0fce57a9fc87cc3371e24aa97e72abb29339dd3deb1`,
`ec555b603447b8cd160cad7fd11441bc102f2b7ec2dc411d4b0681c53de68115`,
`ae1590bd859a8a26f066f72cb2813185cc07539d0d0f9a83ef07c02209ed9b46`,
`578b85379140fee69877d7cf26219aa9adf3435f4cd8a1a02c888025ca635bb5`,
`7bc251b074515f3ba67f8023b9b229db47e3b5e345f3eeedb00177d7c300696d`,
`124edc88ff7756abf3c5a7a141b8efcab5b974eb3938cc67f74d336c27a0fbe1`,
`915780de2b3b4aa763ddf64cf93e5fd701c2174f3c748b822445c8ac92594988`,
`1dc650da3d15d919c8b0c1b35de9347c5543c728ec06c55177258f2180ad5cca`,
`6961ed6d2c76089849c830e2461cf07ccd67d72090b1ef72040a9357a83e7096`,
`ee5e29521c7ce7aed815bb985c73e28ac1bce501cf996d50ec0f5215a1d206c2`,
`862c30777fd3a9ff4311ee3b0d0ce10720cd7d55adc14774b0d9f4307ebc7f92`,
`51fd53d04461a766dc36438634c2d908bc6d5681d9419fab6d2dcc0e9b37e0ed`, and
`1b5d7f126bba9cf60712a0d75804b68cea26419e49c5240fe3592546902ce283`. Rows
`0x0083`, `0x0084`, `0x0085`, and `0x0086` differ by one rendered row each; rows
`0x00bf`, `0x00c0`, `0x00c1`, `0x00fd`, `0x00fe`, and `0x00ff` share the same
16-row digest
`a3dd16ea6b4509770b6c7859de6c059de5af91c05c9136e90f8daccc8acf5932`.

Fixture `host-fetched rows-0x102 downloaded glyph FF publication truncates
page-record rows` covers the first row count whose high byte is nonzero. The
stream is `ESC )s516W` plus printable `3` and FF. The font phase restores
record `80 57 02 04 00 00`, installs glyph `0x33` at table entry `0x0116`,
writes record `00 00 00 00 0c 01 01 02 00 10 00 00`, and copies `0x0204`
linear bytes. The page-record producer does not carry that 16-bit row count
forward through the printable inline source record: `text_source_metrics_via_12f2e`
reads row byte `0x02`, so `0x12f2e` queues selector `0x0003`, short object
`00 00 00 00 00 03 00 01 33 66 01` plus allocator padding, and bucket `1`
instead of selector `0x2003` buckets `1`, `9`, and `17`. The trailing FF routes
tail handlers `0xd04a` and `0xf0f0`, and `0xff1e` publishes only bucket `1`.
The visible-output boundary is now exact: `0x1ed84`/`0x1ef6a` set render word
`+0x10 = 1`, `0x1ef86` derives `0x783a20 = 0x0040` and
`0x783a28 = 0x00100800`, `0x1f414` splits glyph rows `0x0102` at coord
`0x6601` into `58` current-band rows and `200` fallback rows, and the
span-2 row-copy helper `0x1fe76` has valid table entries only through index
`128`. The fallback index `200` reads table target `0x329ad3c0`, so the
fixture proves parser/install/page-record publication plus the exact invalid
render boundary, not pixel output for rows `0x0102`.

Fixture `downloaded glyph high-row truncation matrix preserves installed rows`
composes the adjacent nonzero-high-byte siblings. Rows `0x0101`, `0x0102`,
and `0x0103` restore fetched `ESC )s#W` records with byte budgets `0x0202`,
`0x0204`, and `0x0206`, install mode-byte-`1` records ending in the matching
16-bit row words, and keep those installed row words as canonical downloaded
glyph state. The printable/page source still carries only the low row byte:
`0x12f2e` sees rows `0x01`, `0x02`, and `0x03`, derives selector `0x0003`,
and publishes only bucket `1` through `0xff1e`. The render split uses the full
installed glyph row words: `0x1f414` splits all three at coord `0x6601` into
`58` current-band rows plus fallback rows `199`, `200`, and `201`. Those
fallback counts exceed the span-2 row-copy helper `0x1fe76` valid maximum
index `128`, so the matrix deliberately documents the same unresolved
visible-output boundary instead of claiming pixels for these high-row cases.

Fixture `host-fetched split-plane segmented downloaded character renders
through 0x1f1f0` covers the odd-span sibling. The host-fetched `ESC )s387W`
stream uses parser record `80 57 01 83 00 00`, delayed handler `0x16c14`,
payload offset `7`, and byte budget `0x0183`. `0x16498` installs glyph `0x28`
at table entry `0x00ea`, record delta `0x0700`, record
`00 00 00 00 0c 02 00 81 00 18 00 00`, bitmap offset `0x070c`, span `3`, and
split-plane layout. `0x16942` copies prefix bytes through A4 and trailing
bytes through A3; for segment `1`, `0x1f1f0` reads row skip `0x80` from A2
offset `0x0100` and A3 offset `0x0080`, then renders
`####........#####.#.#.#.` beginning at x `22`.

Fixture `split-plane segmented downloaded glyph FF publication renders page
record` carries the same odd-span stream through the page-publication boundary.
The host-fetched `ESC )s387W` stream plus printable `(` and FF restores record
`80 57 01 83 00 00`, starts the payload at offset `7`, returns through
`0x15dc6 -> 0x16498 -> 0x15dcc -> 0x12328` with `0x783140 = 0`, a zero-byte
`0x12328` drain, and handler `0xd04a` for printable `(`. Tail handlers
`0xd04a` and `0xf0f0` publish bucket `9` through `0xff1e`. The
published bucket root is `00 00 00 00 20 03 00 01 28 01 66 01` plus allocator
padding, and the bucket array preserves both bucket `1`
`00 00 00 00 20 03 00 01 28 00 66 01` and bucket `9`
`00 00 00 00 20 03 00 01 28 01 66 01`. Rule and fixed lists remain empty,
context slots remain `(0, 0, 0, 0)`, `0xff1e` clears the current page root and
sets the publication flag, and `0x1ed84`/`0x1ef6a` render bucket word `9`
through compact target `0x1effe` with the same split-plane row
`####........#####.#.#.#.` at x `22`.

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

The same fixture now also pins the full-success return boundary:
`0x15e42 -> 0x16606 -> 0x15dcc -> 0x12328`, copy status `1`, copy stream
position `6`, remaining `0x783140 = 0`, zero drained bytes, and next parser
handler `0xd04a` for following printable `!`. This closes the current-record
bit-30-clear `0x15e3c..0x15e46` middle edge for one page-visible fixed-record
resource object and one full-success return sibling.

Fixture
`0x16606 no-install exits clear stale continuation without payload writes`
covers the front-end no-install exits for the same handler. Disassembly
`generated/disasm/ic30_ic13_font_payload_object_path_016040.lst` clears stale
continuation state at `0x16612..0x1664e` before range validation and before
the object-prefix/copy exits. The fixture proves five no-install cases: char
`0xa0` with payload type byte `+0x0e = 0` exits as
`char-outside-resource-range`; a two-byte prefix exits as
`short-resource-record-prefix`; byte budget `0x0d` exits as
`budget-below-0x16606-object-minimum`; prefix `00 01 04 00` exits as
`zero-resource-span`; and a short bitmap stream for prefix `02 02 04 00` exits
as `payload-copy-failed` after copying only `aa` with three bytes still
remaining. In every case the stale continuation record is cleared and the
resource payload memory remains byte-for-byte unchanged. Canonical table/object
state is therefore unchanged, parser scratch is the cleared continuation
record, firmware bookkeeping is the failed branch reason, and output effect is
no new glyph becoming visible.

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
three mode-0 rows as the one-piece `0x16606` fixture. Its return boundary is
`0x15e64 -> 0x15c4c -> 0x15dcc -> 0x12328`, copy status `1`, copy stream
position `4`, remaining `0x783140 = 0`, zero drained bytes, and next parser
handler `0xd04a`. This closes the bit-30-clear continuation middle edge for
one even-span fixed-record resource object and one linear continuation
full-success return sibling.

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
y `7`. The split-plane success returns through the same
`0x15e64 -> 0x15c4c -> 0x15dcc -> 0x12328` boundary with copy status `1`,
copy stream position `2`, remaining `0x783140 = 0`, zero drained bytes, and
next parser handler `0xd04a`. This closes the split-plane
continuation-counter middle edge for one bit-30-clear fixed-record resource
object and one split-plane continuation full-success return sibling.

Fixture `0x15c4c partial resource resumes update continuation state` covers the
status-`2` sibling for the same continuation handler. The linear partial starts
from saved destination `0x000302` and remaining count `4`, copies one byte
`f0`, advances destination to `0x000303`, and resaves remaining count `3`.
The split-plane partial starts from saved prefix destination `0x000303`,
trailing destination `0x000305`, and D4/D3 counters `0/0`, copies only prefix
byte `c1`, advances prefix destination to `0x000304`, keeps trailing
destination `0x000305`, and resaves D4/D3 counters `1/0`. Both cases return
status `2` from `0x16874`, leave `0x7827c6 = 1`, and preserve the payload and
glyph/table index for a later descriptor-selected resume.

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

Fixture `0x17d7c release reject exits preserve table and continuation state`
covers the no-rewrite release exits. A base outside the modeled payload returns
`base-outside-header`. Fixed-record char `0x20` with type byte `0`, and
extended char `0xa1` with type byte `0`, both return
`char-outside-fixed-record-range`. The bit-30 delegate case enters `0x17a24`
with range `0x20..0x7f` and char `0x80`, returning
`char-outside-offset-table-range`. In all four cases the fixture keeps the
release input memory and continuation state unchanged, so no table entry is
cleared and no active-context refresh is requested.

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
`2215..2216`. Fixture `combined font download FF publishes installed glyph page
record` now pins the segmented-wide full-success return boundary too: after the
payload copy, `0x15dc6 -> 0x16498 -> 0x15dcc -> 0x12328` leaves
`0x783140 = 0`, drains zero bytes, and resumes at handler `0xd04a` for the
printable `%` before FF reaches `0xf0f0`. Publication keeps bucket root
`00 00 00 00 30 03 00 01 25 01 66 01...`, publishes bucket array entries `9`
and `1`, leaves rule and fixed lists empty, copies context slots `0,0,0,0`,
clears the current root, and sets publication flag `1`. Fixture
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

The payload-control wide downloaded-glyph publication sibling proves the same
published-object boundary for the odd-span wide compact branch after data normalization.
The fetched stream is `ESC )s18W` plus payload beginning `1a 58`, candidate printable
byte `&`, and FF, with the same byte boundaries `0..24`, `24..25`, and `25..26`.
`0x168dc` normalizes `1a 58` to one zero payload byte, so `0x16498` installs glyph
`0x26` at table entry `0x00e2` with mode-byte-`2` record `00 00 00 00 0c 02 00 01 00 88
00 00`, bitmap size `17`, and span `0x11`. The return boundary is not a zero-drain
sibling: `0x783140 = 1`, so `0x15dcc -> 0x12328` drains the following byte `0x26` (`&`)
as the final payload byte, leaving only FF for the post-return parser at handler
`0xf0f0`. The modeled page-record publication part of fixture `host-fetched
payload-control downloaded glyph FF publishes page record` still copies bucket array
entry `1`, preserves empty rule/fixed lists and context slots `0,0,0,0`, clears the
current root, and renders bucket word `1` through `0x1ed84`/`0x1ef6a`, compact target
`0x1effe`, and `0x1f0d2`; it is evidence for the installed object and publication
renderer, while the live same-stream printable handoff is the nonzero `0x12328` drain
described above.

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
Fixture
`host-fetched nonboundary short downloaded glyph FF publication renders page record`
adds an interior short-row sibling: `ESC )s32W` plus printable `+` and FF
restores record `80 57 00 20 00 00`, installs glyph `0x2b` with rows `0x10`,
keeps selector `0x0003`, publishes bucket `1`, dispatches object byte `0x00`
through `0x1effe`/`0x1fe76`, and preserves row digest
`28220dd2ecafaf07afc095fa0cc3cb6ed070984b3e3da6762b49ebda582d492b` across
the direct and published-record render entries.
Fixture `host-fetched rows-0x20 short downloaded glyph FF publication renders
page record` covers a second interior short-row count in the same selector
family. The stream is `ESC )s64W` plus printable `1` and FF. The font phase
restores record `80 57 00 40 00 00`, installs glyph `0x31` at table entry
`0x010e`, writes record `00 00 00 00 0c 01 00 20 00 10 00 00`, copies `64`
linear bytes, and keeps selector `0x0003`. Publication copies bucket array
entry `1`; rendering bucket word `1` through `0x1ed84`/`0x1ef6a` and compact
target `0x1effe`/`0x1fe76` produces `38` visible rows, with the final row
`####........####` at x `22`.
Fixture `host-fetched rows-0x40 short downloaded glyph FF publication renders
page record` covers a taller interior short-row count before the `0x80`
threshold. The stream is `ESC )s128W` plus printable `2` and FF. The font
phase restores record `80 57 00 80 00 00`, installs glyph `0x32` at table
entry `0x0112`, writes record `00 00 00 00 0c 01 00 40 00 10 00 00`, copies
`128` linear bytes, and keeps selector `0x0003`. Publication copies bucket
array entry `1`; rendering bucket word `1` through `0x1ed84`/`0x1ef6a` and
compact target `0x1effe`/`0x1fe76` produces `64` current-band rows. Because
the only nonzero payload row is glyph row `63` and the compact object begins
at current-band y `6`, the current-band output stays blank; later band
scheduling remains a separate render-scheduler edge.
Fixture `host-fetched rows-0x82 segmented downloaded glyph FF publication
renders page record` covers an interior segmented row count: `ESC )s260W`
installs rows `0x82`, record `00 00 00 00 0c 01 00 82 00 10 00 00`, publishes
buckets `1` and `9`, and renders bucket word `9` through compact target
`0x1effe`/`0x1f1f0` with two segment-1 rows.

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
  and routes to `0x16498`, `0x16606`, `0x15b9a`, or `0x15c4c`. Fixture
  `0x15d0a descriptor grammar exits and handler matrix` covers early drains
  for short budgets, parser mode `2`, exhausted descriptor input, missing
  current records, and missing continuation state, plus all four
  current-record/continuation and bit-30-set/clear handler polarities.
- `0x16c14` writes `0x783140`, current-record ids/payload pointers,
  candidate flags, candidate counters, and installed counts.
- `0x1887a` clears released current-record ids/payload pointers and flag bits
  `4..7`, decrements marked/unmarked and class counters, shifts class-one
  cursors for class-one payloads, clears matching continuation state, marks
  matching context-stack primary/secondary dirty bytes, deletes matching
  candidate slots, refreshes matching active contexts, and finishes at
  `0x1b04c`. Fixture
  `0x1887a release variant matrix covers cleanup branches` proves bit-30-set
  class-one, bit-30-set class-zero, and bit-30-clear class-zero variants.
- `0x16fae` writes staged descriptor fields, optional symbol bytes, and
  optional symbol count.
- `0x17362` writes staged type byte and payload units.
- `0x17026` writes staged type/size and allocates the payload.
- `0x1719c` writes allocated payload header fields and optional symbol block.
- `0x168dc` and `0x16942` write glyph bitmap bytes and continuation state.
- `0x15b9a` resumes bit-30 downloaded-character bitmap copies from saved
  continuation fields. On status `1` it clears continuation state after
  completing the object bitmap. On status `2` it resaves the advanced
  destination/counter state. On status `0` it calls `0x17a24` to clear the
  offset-table entry, then clears continuation state.
- `0x16606` clears stale continuation state, writes fixed-record table entries
  in bit-30-clear resource payloads, copies bitmap bytes through `0x16874`,
  and refreshes selected contexts through `0x14c64` when the payload matches
  an active primary or secondary context. Fixture
  `0x16606 no-install exits clear stale continuation without payload writes`
  proves its range, short-prefix, short-budget, zero-span, and copy-failure
  exits clear stale continuation state without changing payload memory.
- `0x15c4c` resumes bit-30-clear fixed-record bitmap copies from saved
  continuation fields, including split-plane A4/A3 destinations and D4/D3
  counters. On status `1` it clears continuation state and leaves the completed
  fixed-record payload renderable through the same active context path. On
  status `2` it resaves advanced continuation state. On status `0` it calls
  `0x17d7c` to release/rewrite the fixed-record entry, then clears
  continuation state.
- `0x17d7c` rewrites released bit-30-clear fixed-record entries, writes the
  side-table bytes used by the fallback record, refreshes matching active
  primary/secondary contexts through `0x14c64`, and clears matching
  continuation state. Its range/base reject exits leave table and continuation
  state unchanged.
- `0x17a24` releases bit-30 offset-table entries delegated by `0x17d7c`,
  clears the selected 4-byte glyph/object pointer, refreshes matching active
  primary/secondary contexts through `0x14c64`, and clears matching
  continuation state. Its offset-table range reject leaves table and
  continuation state unchanged.
- `0x12f2e`/`0x1387c` write compact text bucket objects for the installed
  glyph.

## Readers And Consumers

- `0x11f96` reads the parsed `W` count and schedules delayed font handlers.
- `0x172c0` reads the current-record pool by current font id.
- `0x1b4c0` resolves payload pointers from current records or continuation
  state.
- `0x15b9a` reads `0x7827c6`, `0x7827da`, `0x7827c8`, `0x7827ca`,
  `0x7827ce`, `0x7827d2`, `0x7827d6`, `0x7827d8`, and the selected bit-30
  object-table entry plus downloaded-character record.
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
target `0x1effe`, and final `0x1f0d2` rows. High for the payload-control wide
publication sibling because fixture
`host-fetched payload-control downloaded glyph FF publishes page record`
asserts the host-fetched `ESC )s18W` stream with `1a 58` normalization,
mode-byte-`2` record `00 00 00 00 0c 02 00 01 00 88 00 00`, nonzero return
drain `0x783140 = 1` consuming `&`, post-return FF handler `0xf0f0`,
published bucket `1`, `0x1ed84` render word `1`, compact dispatch target
`0x1effe`, and final modeled `0x1f0d2` rows. High for the modeled normal,
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

High for the covered parser-produced metric combinations because the type-0, type-1,
type-2, metric-variant, clamped, lower-bound, upper-bound, legal matrix, boundary,
low-nibble rounding, and byte-boundary rounding fixtures all start from host-fetched
`ESC )s80W`, run through `0x16fae`/`0x1719c`, and compare page-visible `0xd4ac`/`0xd8fc`
output effects. Medium for the full PCL soft-font grammar because the validation table
is executable but not every predicate has a manual-facing semantic name, and not every
legal metric combination has a parser-produced page comparison.

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
- `0x16498..0x16942`: split-plane segmented-wide, wide/control, even-span wide,
  compact-wide matrix, segmented-wide matrix, row-threshold `0x80` short, linear normal,
  linear segmented, and split-plane segmented downloaded-character paths are
  page-visible. Fixture `host-fetched row-0x80 downloaded character remains short
  compact` closes the even-span `0x80`/`0x81` selector boundary: rows `0x80` stay on
  selector `0x0003`, while rows `0x81` enter selector `0x2003` in fixture `host-fetched
  segmented downloaded character renders through 0x1f1f0`. Fixture `0x16498 replacement
  allocation failure partial and rejected downloaded character exits preserve state`
  covers old-pointer release through `0x17a24`, object allocation failure through
  `0x170c`/`0x9b5e`/`0x1887a`, status-`2` linear/split-plane continuation pointer
  writes, and descriptor mode-byte-`0` plus high-character/header-type rejects. Fixture
  `0x16498 no-install exits preserve following printable output` closes page-visible
  recovery for those no-install exits by proving the following printable byte stays on
  the default-font object and rows. Fixture `0x16498 status-2 partial installs remain
  printable` covers the linear and split-plane status-`2` visible-output siblings and
  now carries both through trailing-FF `0xff1e` publication and published-record
  rendering. Remaining parser-produced comparisons are bounded cross-products: row
  counts outside the covered short rows `0x01`, `0x02`, `0x03`, `0x04`, `0x05`,
  `0x06`, `0x07`, `0x08`, `0x09`, `0x0a`, `0x0b`, `0x0c`, `0x0d`, `0x0e`,
  `0x0f`, `0x10`, `0x11`, `0x12`, `0x13`, `0x14`, `0x15`, `0x16`, `0x17`,
  `0x18`, `0x19`, `0x1a`, `0x1b`, `0x1c`, `0x1d`, `0x1e`, `0x1f`, `0x20`,
  `0x3e`, `0x3f`, `0x40`, `0x41`, `0x42`, `0x7f`, and `0x80` and segmented
  rows `0x81`, `0x82`, `0x83`, `0x84`, `0x85`, `0x86`,
  `0xbf`, `0xc0`, `0xc1`, `0xfd`, `0xfe`, and `0xff`,
  visible behavior after
  segmented-wide row words above `0x00ff` wrap through the current one-byte printable
  source row field, broader publication combinations beyond the documented normal,
  nonboundary-short, rows-`0x20` short, rows-`0x40` short, row-`0x80`, row-count-matrix
  short/segmented, rows-`0x0102` truncated, linear-segmented, rows-`0x82` segmented,
  split-plane segmented, segmented-glyph plus raster, split-plane segmented-glyph plus
  raster, segmented-glyph/raster FF publication, segmented-wide, even-span wide,
  payload-control wide, wide-remainder matrix, segmented-wide matrix, no-install, and
  status-`2` compact bucket variants, and return-boundary variants beyond the covered
  normal even-span, no-install, status-`2`, row-count-matrix short/segmented,
  linear-segmented publication, split-plane segmented publication, and segmented-wide
  publication fixtures. The normal even-span fixture pins the `0x15dc6 -> 0x16498 ->
  0x15dcc -> 0x12328` boundary with zero remaining budget and next handler `0x10e68`;
  fixture `0x16498 no-install exits preserve following printable output` pins six-byte
  `0x12328` drains before handler `0xd04a`; fixture `0x16498 status-2 partial installs
  remain printable` pins the linear/split status-`2` zero-drain returns before handler
  `0xd04a`; fixture `downloaded glyph row-count matrix publishes and renders additional
  short/segmented counts` pins rows `0x01`, `0x02`, `0x03`, `0x04`, `0x08`, `0x3f`,
  `0x41`, `0x7f`, `0x83`, `0x84`, `0x85`, `0xc0`, `0xfd`, `0xfe`, and `0xff` zero-drain
  returns before handler `0xd04a`; fixture `downloaded glyph wide-remainder matrix
  publishes and renders compact chunks` pins spans `17..32`, selector `0x1003`, object
  byte `0x10`, compact target `0x1effe` / `0x1f0d2`, remainders `1..15`, and the
  no-remainder span-`32` case through the same zero-drain return boundary, and probes
  spans `33`, `48`, `49`, `64`, and `255` through the same upstream boundary with
  matching rendered rows; fixture `downloaded glyph segmented-wide matrix publishes and
  renders compact chunks` pins spans `17..32`, rows `0x81`, selector `0x3003`, buckets
  `0` and `8`, object byte `0x30`, compact target `0x1effe` / `0x1f264`, segment-1 row
  skip `0x80`, A2/A3 source offsets, remainders `1..15`, and the no-remainder span-`32`
  case through the same zero-drain return boundary, and probes spans `33`, `48`, `49`,
  and `64` through the same upstream boundary with matching segment-1 rows; fixture
  `downloaded normal row-0x80 and segmented glyph FF publications render page records`
  pins normal, row-`0x80`, and linear-segmented zero-drain returns before handler
  `0xd04a`; fixture `split-plane segmented downloaded glyph FF publication renders page
  record` pins the split-plane segmented zero-drain return before handler `0xd04a`;
  fixture `combined font download FF publishes installed glyph page record` pins the
  segmented-wide zero-drain return before handler `0xd04a`; fixture `host-fetched
  payload-control downloaded glyph FF publishes page record` pins the payload-control
  wide nonzero drain where `0x12328` consumes `&` and leaves FF for handler `0xf0f0`.
  Other uncomposed full-success return siblings are still bounded cross-products.
  Accepted descriptor-record mode bytes are closed for the covered helper table by
  fixture `0x16b1a descriptor width helper emits only mode 1/2`: disassembly
  `0x16b36..0x16b6a` writes mode `1`/`2` from span parity, and `0x16b26..0x16b34`
  rejects invalid widths without writing scratch. The mode-byte-`0` no-install boundary
  itself is no longer a vague open edge: fixture `0x16498 no-install exits preserve
  following printable output` proves status `0`/`unsupported-record-shape` plus
  unchanged visible output, and fixture `0x16498 replacement allocation failure partial
  and rejected downloaded character exits preserve state` proves the same table/header
  no-write boundary at the object level.
- `0xff1e..0x1ed84`: the combined downloaded-glyph stream now publishes both segmented
  buckets; the normal, rows-`0x20` short, rows-`0x40` short, linear-segmented,
  rows-`0x82` segmented, split-plane segmented, compact-wide matrix,
  segmented-wide matrix, even-span wide, payload-control odd-span wide, and
  rows-`0x0101..0x0103` low-byte-truncated short siblings now publish through the same
  boundary. Fixture `downloaded
  normal row-0x80 and segmented glyph FF publications render page records` renders the
  normal bucket-1 record through `0x1ed84`/`0x1ef6a` and compact target
  `0x1effe`/`0x1fe76`, renders the row-`0x80` bucket-1 record through the same
  target/helper while preserving selector `0x0003`, and renders the linear-segmented
  bucket-9 record through `0x1ed84`/`0x1ef6a` and compact target `0x1effe`/`0x1f1f0`.
  Fixture `split-plane segmented downloaded glyph FF publication renders page record`
  publishes the odd-span bucket-9 root `00 00 00 00 20 03 00 01 28 01 66 01`, preserves
  bucket-array entries `1` and `9`, and renders through `0x1ed84`/`0x1ef6a` and compact
  target `0x1effe`/`0x1f1f0`. Fixture `host-fetched rows-0x82 segmented downloaded glyph
  FF publication renders page record` publishes bucket-array entries `1` and `9` for
  `ESC )s260W`, preserves record `00 00 00 00 0c 01 00 82 00 10 00 00`, renders bucket
  word `9`, and emits two segment-1 rows through compact target `0x1effe`/`0x1f1f0`.
  Fixture `host-fetched rows-0x102 downloaded glyph FF publication truncates page-record
  rows` publishes bucket-array entry `1` for `ESC )s516W`, preserves installed record
  `00 00 00 00 0c 01 01 02 00 10 00 00`, but shows the printable source row byte as
  `0x02`, so `0x12f2e` writes selector `0x0003` object
  `00 00 00 00 00 03 00 01 33 66 01`; `0x1f414` then splits rows `0x0102`
  into `58` current rows and `200` fallback rows, exceeding the `0x1fe76`
  row-copy table's valid maximum index `128` at fallback target `0x329ad3c0`.
  Fixture `downloaded glyph high-row truncation matrix preserves installed rows`
  covers rows `0x0101`, `0x0102`, and `0x0103`: installed row words are canonical,
  printable/page source rows are low bytes `0x01`, `0x02`, and `0x03`, `0x12f2e`
  publishes selector `0x0003` bucket `1`, and `0x1f414` splits full installed rows
  into `58` current rows plus fallback rows `199`, `200`, and `201`, all beyond the
  `0x1fe76` valid index `128`.
  Fixture `host-fetched rows-0x20 short downloaded glyph FF publication renders page
  record` publishes bucket-array entry `1` for `ESC )s64W`, preserves record `00 00 00
  00 0c 01 00 20 00 10 00 00`, renders bucket word `1`, and emits `38` visible rows
  through compact target `0x1effe`/`0x1fe76`. Fixture `host-fetched rows-0x40 short
  downloaded glyph FF publication renders page record` publishes bucket-array entry `1`
  for `ESC )s128W`, preserves record `00 00 00 00 0c 01 00 40 00 10 00 00`, renders
  bucket word `1`, and emits `64` current-band rows through compact target
  `0x1effe`/`0x1fe76`. Fixture `downloaded glyph row-count matrix publishes and renders
  additional short/segmented counts` adds short rows `0x01`, `0x02`, `0x03`,
  `0x04`, `0x05`, `0x06`, `0x07`, `0x08`, `0x09`, `0x0a`, `0x0b`, `0x0c`,
  `0x0d`, `0x0e`, `0x0f`, `0x10`, `0x11`, `0x12`, `0x13`, `0x14`, `0x15`,
  `0x16`, `0x17`, `0x18`, `0x19`, `0x1a`, `0x1b`, `0x1c`, `0x1d`, `0x1e`,
  `0x1f`, `0x3e`, `0x3f`, `0x41`, `0x42`, and `0x7f` on selector `0x0003`/bucket
  `1`, and segmented rows `0x83`, `0x84`, `0x85`, `0x86`, `0xbf`, `0xc0`,
  `0xc1`, `0xfd`, `0xfe`, and `0xff` on selector `0x2003`/buckets `1` and `9`,
  all through printable+FF, `0xff1e`, and `0x1ed84`/`0x1ef6a`. Fixture
  `host-fetched even-span downloaded glyph FF publishes
  rendered page record` renders the copied bucket-1 record through `0x1ed84`/`0x1ef6a`
  and compact target `0x1effe`/`0x1f0d2`. Fixture `downloaded glyph segmented-wide
  matrix publishes and renders compact chunks` publishes bucket-array entries `0` and
  `8` for matched spans `17..32` with rows `0x81`, renders bucket word `8`, dispatches
  object byte `0x30` to compact target `0x1effe`/`0x1f264`, and compares segment-1 rows
  against the installed bitmap; the same fixture probes spans `33`, `48`, `49`, and
  `64` with matching row comparisons. Fixture `host-fetched payload-control
  downloaded glyph FF publishes page record` covers the odd-span wide sibling:
  host-fetched `ESC )s18W` normalizes one `1a 58` payload escape through the font
  payload reader, stores mode-byte-`2` record `00 00 00 00 0c 02 00 01 00 88 00 00`,
  leaves `0x783140 = 1`, drains following byte `&` through `0x12328`, and leaves FF for
  handler `0xf0f0`. Its modeled page-record publication publishes bucket `1` and
  renders the installed object through `0x1ed84`/`0x1ef6a` and compact target
  `0x1effe`/`0x1f0d2`. Fixture `published downloaded glyph segmented buckets render
  across bands` renders published bucket words `1` and `9` from the copied record.
  Fixture `0x1eba4 scheduler band words render published downloaded glyph` proves
  `0xff1e`/`0x1ed84` seed render work `+0x10/+0x16` from cleared source `+0x18 = 0`,
  then `0x1eba4` advances through band words `0..9` until the published bucket-9 row is
  visible. The earlier first-band seed edge is now closed for this published record.
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
- The span-metric fields documented in `notes/font-context-metrics.md` are now tied to
  installed payload headers for the `0xd4ac` and `0xd8fc` type-0, type-1, and type-2
  fixtures, and the shared consumer branch family is fixture-backed. The
  invalid-resource-type, first-code overflow, zero line/count, high line/count,
  reversed-range, high range/count, and invalid-class resource paths now have
  host-fetched parser/validation/no-install boundaries and following-printable page
  output. The seven-case legal descriptor metric matrix plus the boundary-value fixture
  now prove copied descriptor fields can flip the `0xd4ac` page-extent gate, exercise
  rounded-metric clamping into `+0x2c/+0x2d`, preserve zero rounded/offset fields
  through visible `0xd4ac` and `0xd8fc` span objects, preserve negative and max-positive
  flagged offset bytes as copied words `0xfffe`, `0xffff`, and `0x007f`, accept `d8fc`
  lower-bound equality and exact page-extent equality, move `d8fc` rendered rows, update
  `0xd8fc` without publishing a span object, suppress both span consumers through
  parser-owned lower-bound fields, suppress only `0xd8fc` through parser-owned
  upper-bound fields while preserving `0xd4ac` span output and compact glyph output,
  round `0x0013` up to copied `+0x2c = 0x0014`, and show rounded inputs `0x1500`,
  `0x1508`, and `0x15ff` all transform to copied `+0x2c = 0x0060` before `d4ac` exits
  beyond page extent. Fixture `legal descriptor metric low-nibble rounding drives d4ac
  and d8fc consumers` proves rounded inputs `0x0001`, `0x0003`, `0x0004`, `0x0005`, and
  `0x000f` copy to `+0x2c = 0x0000/0x0004/0x0004/0x0004/0x0010`, while preserving `d4ac`
  span output and `d8fc` high-y `20` output. Fixture `legal descriptor metric range
  endpoints drive d4ac and d8fc consumers` proves first-code zero and the
  range-minus-one first-code copy `+0x14/+0x16/+0x18 = 0x0018/0x0000/0x0017` and
  `0x0015/0x0014/0x0000` while preserving the documented visible span paths. Fixture
  `legal descriptor metric extent fenceposts drive d4ac and d8fc consumers` pins the
  `d8fc` page-extent gate after the `0x17430` derived-height formula: first code `4`,
  range words `0x002f`, `0x0031`, and `0x0032`, rounded word `0x0020`, and offsets `0`,
  `1`, and `2` copy derived heights `42`, `44`, and `45`. The height-42 zero-offset case
  renders high-y `21` with digest
  `47361fc76bd6284f9d764c0377a3fda64edd3944b5cb2dff72acfd2224bc25e8`, while the
  height-44 and height-45 cases exit `beyond-page-extent`, proving the gate uses derived
  height before copied offset can recover a span. Fixture `legal descriptor metric mixed
  values drive d4ac and d8fc consumers` proves the combined middle-range, range-capped,
  sign-extended-offset, and zero-derived-height copied-field cases described above.
  Fixture `legal descriptor metric tight range values drive d4ac and d8fc consumers`
  proves the smallest legal range/count cross-products: range one copies
  `+0x14/+0x16/+0x18 = 0x0001/0x0000/0x0000` with zero and clamped rounded `+0x2c`
  values, while range two copies `0x0002/0x0001/0x0000` with max positive and max
  negative signed offsets. Fixture `descriptor metric fields match across inline and
  resource contexts` now proves the legal producer forms and the two invalid swapped
  forms. Additional legal descriptor combinations outside the pinned
  lower/equality/upper, clamp, offset endpoint, range endpoint, extent-fence,
  rounded-transform, mixed-value, tight-range, low-nibble, and byte-boundary cases are
  cross-products of the documented producer formulas and consumer gates, not new
  copied-field endpoints. All ROM-internal validation no-install predicate families are
  already parser-produced and page-visible; remaining validation work is external HP
  manual naming for consumed-but-not-staged fields.
