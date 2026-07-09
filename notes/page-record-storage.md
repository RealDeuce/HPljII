# Page-Record Storage And Publication

This note is the semantic contract for the LaserJet II page-record root,
shared stream allocator, compact/raster bucket storage, rule/fixed lists,
publication through `0xff1e`, and the bridge into render records through
`0x1ed84` / `0x1edc6`.

Status: composed for the shared page-record state block used by compact text,
rules, fixed rules, raster rows, publication commands, and render-entry
fixtures. This file is the renderer-facing storage and publication checkpoint.
Bitmap class dispatch after the bridge remains in `notes/page-raster-imaging.md`
and `notes/semantic-state-model.md` under `Bitmap Render Dispatch Contract`.

## Evidence

- `generated/analysis/ic30_ic13_page_root_allocation.md`
- `generated/analysis/ic30_ic13_page_root_references.md`
- `generated/analysis/ic30_ic13_compact_bucket_allocator.md`
- `generated/analysis/ic30_ic13_page_record_bridge.md`
- `generated/disasm/ic30_ic13_page_root_allocate_010084.lst`
- `generated/disasm/ic30_ic13_display_list_helpers_013386.lst`
- `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`
- `generated/disasm/ic30_ic13_raster_object_queue_013070.lst`
- `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`
- `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`
- `notes/page-raster-imaging.md`
- `notes/semantic-state-model.md`

Primary fixtures:

- `0x10084-modeled page-root allocation side effects`
- `0x10110 page-root initializer installs selected context slot`
- `0x10110 page-root initializer copies geometry fields`
- `0x1381c stream allocator chunks display-list storage`
- `0x1387c address-aware bucket allocation uses 0x1381c storage`
- `0x1387c page-record bucket allocator links new head when full`
- `0x1387c page-record bucket allocator reuses matching short object`
- `0x1387c page-record unflagged short bucket object`
- `0x1387c page-record segmented allocator places tall glyph buckets`
- `0x1387c page-record segmented allocator reuses tall glyph buckets`
- `0x1387c page-record queued short object renders reused entries`
- `0x133aa address-aware rule-list insertion uses 0x1381c storage`
- `0x133aa no-room return preserves rule-list head`
- `0x136d2 address-aware fixed-list insertion uses 0x1381c storage`
- `0x136d2 no-room return preserves fixed-list head after search`
- `0x12714 portrait text span flush queues segment-list span`
- `0x12714 landscape text span flush queues fixed-width span`
- `live CR span flush materializes 0x12714 page object`
- `left-margin parser span flush materializes 0x12714 page object`
- `vertical-cursor parser span flush materializes 0x12714 page object`
- `addressed stream page record materializes through 0xff1e and 0x1ed84`
- `addressed page-record writers share 0x1381c across chunk rollover`
- `addressed text/rule/raster field groups reach publication and render entry`
- `0x1edc6 page-record bridge copies compact bucket and context slots`
- `0x1edc6 page-record bridge normalizes rule and fixed lists`
- `0x1edc6 bridge records render-record destination offsets`
- `0x1ed84 active page-record copy seeds render-record header words`

## Field Groups

Canonical page root:

- `0x78297a`: current page/control root pointer.
- Root `+0x1c`: bucket-head array for compact text and raster objects.
- Root `+0x20`: head/link slot for 0x100-byte stream chunks.
- Root `+0x24`: rectangle/rule list head.
- Root `+0x28`: fixed-rule list head.
- Root `+0x2c..+0x68`: 16 current-font context slots.
- Root byte `+4`: page-root state, initialized to `1` and published as state
  `2` by `0xff1e`.

Canonical stream allocator state:

- `0x782a70`: bytes remaining in the current stream chunk.
- `0x782a72`: pointer to the current chunk link field.
- `0x782a76`: next free byte in the current chunk.
- `0x782c72` / `0x782c73`: pending latches that make first-root allocation
  wait through `0x9ac2`.
- `0x782990`: transient page-root byte cleared by `0x10084`.

Derived producer keys:

- `0x782a7c`: compact bucket index or ordered-list key.
- `0x782a7d`: rule/fixed selector byte copied into object `+4`.
- `0x782a7e`: compact coordinate or rule key copied into object `+6`.
- `0x782a7a` / `0x782a7b`: compact selector bytes consumed by `0x1387c`
  callers.

Canonical object fields:

- Compact/raster bucket object `+0`: next pointer.
- Bucket object `+4`: class/selector byte. `0x00..0x3f` selects compact
  glyph/text rendering, `0x40..0x7f` selects segment-list rendering, and
  `0x80..0xff` selects encoded-raster rendering.
- Bucket object `+6`: count/capacity.
- Bucket payload begins at `+8` for compact objects and at `+0a` for
  segment-list or encoded-raster objects.
- Rule/fixed object `+0`: next pointer.
- Rule/fixed object `+4`: bucket byte.
- Rule/fixed object `+5`: selector or mode.
- Rule/fixed object `+6`: ordered key.
- Rule/fixed dimensions and extent fields begin at `+8`.

Renderer-facing object class map:

- Compact text and downloaded-glyph objects:
  producers `0xd04a -> 0x12f2e -> 0x1387c` write root `+0x1c` bucket
  objects with selector/class byte `+4` in `0x00..0x3f`. Bridge `0x1edc6`
  copies root `+0x1c` to render `+0x18`; renderer `0x1efc2 -> 0x1effe`
  dispatches compact helpers `0x1f034`, `0x1f0d2`, `0x1f1f0`, or
  `0x1f264` by object selector bits. Context slots copied from root
  `+0x2c..+0x68` to render `+0x24..+0x60` supply glyph/resource pointers.
- Text-span segment-list objects:
  producer `0x12714` reaches `0x13520` / `0x1354a` / `0x135f0` in portrait
  orientation and writes class-`0x40` objects under root `+0x1c` through
  `0x1387c`. Bridge `0x1edc6` again exposes them at render `+0x18`;
  renderer `0x1efc2` selects segment-list consumer `0x1f812`.
- Encoded raster objects:
  delayed raster handler `0x105d0` calls `0x13070 -> 0x13250`, writing
  class-`0x80` bucket objects under root `+0x1c`; dense rows may split through
  `0x132b6` and multiple `0x13070` loop iterations. Bridge `0x1edc6` copies
  the bucket root to render `+0x18`; renderer `0x1efc2 -> 0x1f88e` selects
  mode helpers `0x1f8da`, `0x1f8e6`, `0x1f920`, or `0x1f9c6` from object byte
  `+5 & 3`.
- Rectangle/rule objects:
  rectangle fill `0x10898` reaches `0x13386 -> 0x133aa`, writing ordered
  nodes under root `+0x24`. Bridge `0x1edc6` copies and normalizes that list
  into render `+0x1c`; renderer `0x1f446` consumes it and dispatches pattern
  helper `0x1f4e0` or solid helper `0x1f596` by the bridged selector byte.
- Landscape text-span fixed-list objects:
  producer `0x12714` reaches `0x136d2` in landscape orientation, writing
  fixed-width objects under root `+0x28`. Bridge `0x1edc6` copies and
  normalizes that list into render `+0x20`; renderer `0x1f756` consumes it on
  five-band boundaries.

This map is the storage-side join between command-family output and bitmap
dispatch. It does not replace the detailed renderer contracts in
[page-raster-imaging.md](page-raster-imaging.md); it identifies the canonical
page-root field a command writes and the exact render-root field and consumer
that later derives pixels from it.

Canonical publication and bridge state:

- `0xff1e` publishes a valid current root into a page/control pool record and
  clears `0x78297a`.
- `0x780ea6`: published page/control pool-head pointer written by `0xff1e`.
- `0x782996`: publication flag set by `0xff1e`.
- `0x1ed84`: active page-record copy entry that seeds render header words from
  the selected source record.
- `0x1edc6`: bridge that copies source bucket root `+0x1c` to render `+0x18`,
  rule list `+0x24` to render `+0x1c`, fixed list `+0x28` to render `+0x20`,
  and 16 context slots `+0x2c..+0x68` to render `+0x24..+0x60`.

Derived render bridge state:

- `0x783a20`, `0x783a22`, and `0x783a28`: render-band outputs derived later
  by `0x1ef86`; they are not canonical page-record fields.
- Render-record destination offsets copied by `0x1edc6` are bridge/cache
  fields consumed by render dispatch, not page-record producer state.

Unknown:

- Manual-facing names for some page/control pool header fields remain outside
  this storage checkpoint. Dense parser-produced pages should be added here
  only when they expose a new root field, stream-allocation transition,
  producer object shape, publication field, or bridge output not already
  covered by the fixtures above.

## Writers

- `0x10084` ensures the current root. It reuses nonzero `0x78297a`; otherwise
  it allocates a root, marks byte `+4 = 1`, seeds `0x782a72 = root + 0x20`,
  calls `0x10110`, clears `0x782990`, and zeroes the 256 bucket heads at
  root `+0x1c`.
- `0x10110` initializes page code, status/flag fields, dimension/band fields,
  list heads, and selected current-font context slot `+0x2c`.
- `0x1381c` allocates variable-size stream objects and updates
  `0x782a70`, `0x782a72`, and `0x782a76`. On a new chunk it links that chunk
  through the prior `0x782a72` target.
- Shared heap allocator entries `0x170c` and `0x1710` are documented in
  [pcl-parser-firmware.md](pcl-parser-firmware.md) and
  [semantic-state-model.md](semantic-state-model.md). Page-record storage
  uses the high-side `0x1710` path when `0x1381c` needs a fresh 0x100-byte
  stream chunk; this checkpoint owns the page-root link and stream bookkeeping
  after the allocation succeeds or fails.
- `0x1387c` writes compact/raster bucket heads under root `+0x1c`, reuses
  matching selector objects while count `+6` is below capacity, and links a new
  head when the matching object is full.
- `0x12714` packages pending text span state. In portrait orientation it
  reaches `0x13520` / `0x1354a` / `0x135f0`, writing segment-list bucket
  objects under root `+0x1c` through `0x1387c`; in landscape orientation it
  reaches `0x136d2`, writing fixed-list objects under root `+0x28`.
- `0x13070` / `0x13250` write encoded-raster bucket objects under root
  `+0x1c`. Helper `0x132b6` selects each raster object's payload capacity
  from `0x782a70` / `0x782a76` and can split a dense row across multiple
  encoded-span objects before `0x138de` copies payload bytes.
- `0x133aa` writes rectangle/rule nodes under root `+0x24` using the
  ordering algorithm documented below.
- `0x136d2` writes fixed-list nodes under root `+0x28` using the ordering
  algorithm documented below.
- `0xff1e` copies root fields into a published pool record, writes published
  state, clears the current root, and preserves command-specific pool header
  fields such as copy-count word `+0x0c`.
- `0x1ed84` writes active render-record header words from the selected source
  record, then delegates queue/list/context copying to `0x1edc6`.
- `0x1edc6` writes render-record bucket, rule, fixed-list, and context roots.

## Rule-List Insertion Order

`0x13386` is the rectangle/rule storage entry. It first calls `0x134d6` on the
source record, then calls `0x133aa` to allocate and link the page object.

The key builder at `0x134d6` writes derived/cache state, not canonical page
state:

- `0x782a7c = source word +2 >> 4`; this is the search key consumed by
  `0x13472`.
- `0x782a7e = (source word +2 << 12)
  | (((source word +0 + 0x782dc0) & 0x0f) << 8)
  | ((source word +0 + 0x782dc0) >> 4)`, truncated to the stored word.

`0x133aa` allocates a 14-byte object through `0x1381c`. If allocation fails at
`0x133c2..0x133d0`, it returns zero before modifying root `+0x24`, the
existing rule list, or stream bookkeeping. If root `+0x24` is empty, it stores
the new object as the head and clears object `+0`.

For a nonempty list, `0x133aa` calls `0x13472(head, local_status)`.
`0x13472` compares each existing object's byte `+4` with key `0x782a7c` and
returns both a candidate pointer in `D7` and a status word:

- status `1`: at least one earlier object byte was below the key. `0x133aa`
  inserts the new object after the returned predecessor by writing
  `new.+0 = predecessor.+0` and `predecessor.+0 = new`.
- status `2`: the scan reached the tail and the tail byte is less than or
  equal to the key. `0x133aa` appends after the returned tail and clears
  `new.+0`.
- status `0`: no earlier predecessor is accepted. `0x133aa` inserts at the
  head by writing `new.+0 = root.+0x24` and `root.+0x24 = new`.

After the link is chosen, `0x133aa` fills the canonical rule object:

- object `+4` gets byte `0x782a7d`;
- object `+5` ORs in the low byte of source word `+8`;
- object `+6` gets word `0x782a7e`;
- object `+8` gets source word `+4`;
- object `+0x0a` gets source word `+6`.

Output effect: the order of root `+0x24` is preserved through publication and
bridge. `0x1edc6` copies root `+0x24` to render `+0x1c`, and `0x1f446`
traverses that bridged list when drawing rule objects. The documented
algorithm, rather than any physical paper comparison, is the reproduction
contract for overlapping or same-band rules.

Evidence: `generated/disasm/ic30_ic13_display_list_helpers_013386.lst`
`0x13386..0x13470` for allocation, link cases, and object writes;
`0x13472..0x134d4` for the status-returning search; `0x134d6..0x1351e` for
derived key writes; fixture
`0x133aa address-aware rule-list insertion uses 0x1381c storage` for lower,
higher, and equal-key examples; fixture
`0x133aa no-room return preserves rule-list head` for the zero-allocation
branch; and fixture `0x1edc6 page-record bridge normalizes rule and fixed
lists` for the root-to-render bridge.

## Fixed-List Insertion Order

Landscape text-span storage enters through `0x1366c`: it calls `0x137a2` to
normalize the local span source and derive keys, then calls `0x136d2` to link
the fixed-list object.

`0x137a2` writes both source fields and derived/cache state:

- source byte `+1` becomes `3` when its low bit was clear, or `6` when its low
  bit was set;
- source word `+2` is rewritten as `source word +2 + 0x782dc0`;
- `0x782a7a = 0x40` and `0x782a7b = 0`, matching the segment-list selector
  state used by the portrait sibling;
- `0x782a7c = source word +4 >> 4`;
- `0x782a7e = (source word +4 << 12)
  | (((source word +2 + 0x782dc0) & 0x0f) << 8)
  | ((source word +2 + 0x782dc0) >> 4)`, truncated to the stored word.

If root `+0x28` is empty, `0x136d2` allocates 14 bytes through `0x1381c`,
stores the new object as the root `+0x28` head, and clears its next pointer.
If allocation fails at `0x136f8..0x13700`, it returns zero without modifying
root `+0x28`.

For a nonempty list, `0x136d2` first calls `0x13690(head, local_status)`.
`0x13690` walks existing object byte `+4` values against key `0x782a7c`:

- when it finds the first object whose byte `+4` is greater than the key, it
  returns the predecessor pointer, or zero when that object was the head, with
  status nonzero;
- when it reaches a tail whose byte `+4` is less than or equal to the key, it
  returns that tail with status zero.

Only after that search does `0x136d2` allocate the new object. If allocation
fails at `0x1371a..0x13734`, the prior search has no visible page effect:
root `+0x28`, existing nodes, and stream bookkeeping remain unchanged. On
success, `0x136d2` links by the search result:

- status zero appends after the returned tail and clears `new.+0`;
- status nonzero with a zero predecessor inserts at the head by copying the
  old root `+0x28` into `new.+0` and storing the new object as root `+0x28`;
- status nonzero with a nonzero predecessor inserts after that predecessor by
  copying `predecessor.+0` into `new.+0` and writing `predecessor.+0 = new`.

After linking, `0x136d2` fills the canonical fixed-list object:

- object `+4` gets byte `0x782a7d`, the low byte of derived key
  `0x782a7c`;
- object `+5` gets normalized source byte `+1`;
- object `+6` gets word `0x782a7e`;
- object `+8` gets source word `+6`.

Output effect: `0x1edc6` copies root `+0x28` to render `+0x20` and writes
fixed-list continuation fields before `0x1f756` consumes the bridged list on
five-band boundaries. The fixed-list order therefore controls the order of
landscape span objects presented to `0x1f756`.

Evidence: `generated/disasm/ic30_ic13_display_list_helpers_013386.lst`
`0x1366c..0x1381a` for key normalization, search, allocation, link cases, and
object writes; fixture
`0x136d2 address-aware fixed-list insertion uses 0x1381c storage` for lower,
higher, and equal-key list cases; fixture
`0x136d2 no-room return preserves fixed-list head after search` for the
post-search allocation-failure branch; fixture
`0x12714 landscape span inserts into nonempty fixed list` for parser-fed
landscape insertion; and fixture
`0x1edc6 page-record bridge normalizes rule and fixed lists` for the
root-to-render bridge.

## Render-Record Bridge Contract

`0x1ed84` and `0x1edc6` are the publication-to-render boundary for page
objects. They do not parse host bytes and they do not allocate new page
objects. Their job is to copy the scheduler-selected page/control record into
the render work record shape that `0x1ef6a` consumes.

Entry `0x1ed84` takes the destination render-record pointer from its stack
argument, loads the active source page/control record from `0x780eae`, and
copies source header words before calling `0x1edc6`:

- `0x1ed96`: source word `+0x18` to render word `+0x0a`.
- `0x1ed9c`: source word `+0x1a` to render word `+0x0c`.
- `0x1eda2`: source word `+0x18` to render word `+0x16`.
- `0x1eda8`: source word `+0x18` to render word `+0x10`.
- `0x1edae`: clear render word `+0x0e`.

Those fields are derived render-work state. The canonical page-image content
remains the source record's bucket roots, list roots, and context slots.

Helper `0x1edc6` returns immediately when the source record pointer is zero.
For a nonzero source it copies the three page-object roots without merging
them:

- `0x1ede2`: source bucket root `+0x1c` to render root `+0x18`.
- `0x1ede8`: source rule/list root `+0x24` to render root `+0x1c`.
- `0x1edee`: source fixed-list root `+0x28` to render root `+0x20`.

The bucket root is a pass-through pointer copy. Compact text, downloaded
glyph, segment-list span, and encoded-raster object bytes remain in their
producer-written object chains until `0x1efc2` dispatches them from render
root `+0x18`.

The rule and fixed-list roots are copied and then normalized in place for
rendering:

- `0x1edf4..0x1ee0e` walks render root `+0x1c`. Each rule node has selector
  byte `+0x05` ORed with `0x10`, and source height word `+0x0a` copied into
  render continuation word `+0x0c`.
- `0x1ee10..0x1ee5e` walks render root `+0x20`. Each fixed-list node has byte
  `+0x05` ORed with `0x10`, source height word `+0x08` copied into remaining
  rows word `+0x0a`, byte `+0x0c` set to `1`, and byte `+0x0d` set to `8`.

Those mutations are derived/cache render state. They are not new parser state
and they are not new page objects. They define the exact object shape later
seen by `0x1f446` for rule-list rendering and by `0x1f756` for fixed-list
rendering.

Finally, `0x1ee60..0x1ee94` copies 16 source context slots from
`+0x2c..+0x68` to render slots `+0x24..+0x60`. Compact renderer helpers such
as `0x1f008` and `0x1f354` consume those render slots when resolving selected
font or downloaded-glyph resources for bucket objects. The bridge therefore
preserves the context selected when the page object was queued; it does not
re-run font selection.

Output effect: the bridge determines which queued page roots are visible to
the render entry and which normalized continuation fields rule/fixed helpers
consume. Pixel order is still determined later by `0x1ef6a`: bucket root
`+0x18` first, rule root `+0x1c` second, and fixed root `+0x20` last.

Evidence: `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`
`0x1ed84..0x1ee9c`; generated report
`generated/analysis/ic30_ic13_page_record_bridge.md`; fixtures
`0x1ed84 active page-record copy seeds render-record header words`,
`0x1edc6 page-record bridge copies compact bucket and context slots`,
`0x1edc6 page-record bridge normalizes rule and fixed lists`, and
`0x1edc6 bridge records render-record destination offsets`.

## Readers And Consumers

- Printable text through `0xd04a` / `0x12f2e` consumes the current root and
  `0x1387c` bucket allocator.
- Rectangle fill through `0x10898` consumes the current root and inserts rule
  nodes through `0x13386` / `0x133aa`.
- Raster transfer through `0x105d0` consumes the current root and queues
  encoded-span objects through `0x13070` / `0x13250`.
- Span flush through `0x12714` consumes pending span state and then branches by
  orientation: portrait spans become root `+0x1c` segment-list bucket objects
  consumed by `0x1f812`, while landscape spans become root `+0x28` fixed-list
  objects consumed by `0x1f756`.
- Publication through `0xff1e` consumes bucket/list/context root fields.
- Rendering through `0x1ed84` / `0x1edc6` / `0x1ef6a` consumes the published or
  active page record and dispatches compact, encoded-span, rule, and fixed-list
  objects.

## Output Effect

The allocator has no pixels by itself. It determines which objects are visible,
their order, and the root fields later consumed by publication and rendering.

Fixture `addressed text/rule/raster field groups reach publication and render
entry` proves compact text, a selector-7 rule, and a mode-0 raster row share
one addressed page-record state, publish through `0xff1e`, bridge through
`0x1ed84` / `0x1edc6`, and render through `0x1ef6a`.

Fixture `addressed page-record writers share 0x1381c across chunk rollover`
proves the shared stream state across producer families. `0x10084` seeds
`0x782a72 = root + 0x20`; seven compact writers through
`0x12f2e` / `0x1387c` allocate objects in the stream; `0x133aa` and
`0x136d2` then allocate rule/fixed objects from the same stream. The root links
two chunks and publication preserves the bucket root before render entry
dispatches all compact objects.

The compact-bucket fixtures divide the shared `0x1387c` behavior into object
shapes and reuse rules. Fixture `0x1387c page-record bucket allocator reuses
matching short object` proves a matching short object is reused while count
`+6` is below capacity. Fixture `0x1387c page-record unflagged short bucket
object` pins the unflagged compact object shape. Fixtures `0x1387c page-record
segmented allocator places tall glyph buckets` and `0x1387c page-record
segmented allocator reuses tall glyph buckets` pin segmented/tall glyph
placement and reuse. Fixture `0x1387c page-record queued short object renders
reused entries` ties the reused short object to rendered rows, proving this is
canonical page content and not only allocator bookkeeping.

The no-room fixtures prove negative output behavior: if `0x1381c` returns zero
inside `0x133aa`, root `+0x24` and existing rule nodes remain unchanged; if
`0x1381c` returns zero inside `0x136d2`, root `+0x28` and existing fixed nodes
remain unchanged. Later publication therefore sees the prior visible objects,
not a partial failed insertion.

The span fixtures split `0x12714` storage by orientation and by producer. The
portrait fixture queues selector-`0x4000` segment-list objects under bucket
class `0x40`, copied through render root `+0x18` and consumed by `0x1f812`.
The landscape fixture queues fixed-width objects through `0x136d2`, copied
through render root `+0x20` and consumed by `0x1f756`. Direct-control fixtures
`live CR span flush materializes 0x12714 page object`,
`left-margin parser span flush materializes 0x12714 page object`, and
`vertical-cursor parser span flush materializes 0x12714 page object` prove
parsed CR, left-margin, and vertical-cursor commands can all materialize the
same portrait selector-`0x4000` segment-list object before following compact
text is queued.

Raster storage also has a per-object capacity split beneath the same root
`+0x1c` bucket array. `0x132b6` may return only the current chunk tail or a
fresh capped chunk payload capacity in `0x782a80`; `0x13070` then writes object
word `+0x06` from that capacity, copies payload through `0x138de`, advances
the packed key, and loops until the accepted transfer bytes are represented by
one or more encoded-span objects. The detailed dense-row split is documented
in [raster-graphics.md](raster-graphics.md#allocation-capacity-and-dense-rows).

The bridge fixtures split storage from rendering. `0x1edc6 page-record bridge
copies compact bucket and context slots` proves the compact bucket root and
selected-font context slots survive into render-record fields. `0x1ed84 active
page-record copy seeds render-record header words` proves the active-copy
header words consumed before `0x1ef6a`.
Fixture `0x1edc6 page-record bridge normalizes rule and fixed lists` proves
the rule list `+0x24` and fixed list `+0x28` are copied to render-record
`+0x1c` and `+0x20`, then normalized in place before rule/fixed dispatch.
Fixture `0x1edc6 bridge records render-record destination offsets` classifies
the copied destination offsets as derived bridge/cache state, not producer
state.

## Mixed Page Composition Checkpoint

This checkpoint is the page-image assembly rule for a supported mixed stream:
parser handlers build display-list objects first, and the renderer later
composes those objects into band pixels. The ROM does not allocate or maintain
a parser-time full-page bitmap.

Assembly sequence:

1. A producer calls `0x10084` to ensure current root `0x78297a`.
2. Compact text/downloaded glyphs, portrait spans, and encoded raster rows use
   root `+0x1c`, whose bucket array groups objects by vertical bucket and
   class byte.
3. Rectangle/rule objects use the ordered list at root `+0x24`; fixed-width or
   landscape span objects use the ordered list at root `+0x28`.
4. All variable-size object bodies come from the shared `0x1381c` stream. The
   stream chain starts at root `+0x20`, so compact, raster, rule, and fixed
   producers can share the same 0x100-byte chunks.
5. Publication `0xff1e` snapshots the root into the page/control pool, sets
   `0x782996`, and clears `0x78297a`.
6. Active copy `0x1ed84` selects a published source record, and bridge
   `0x1edc6` copies root `+0x1c/+0x24/+0x28/+0x2c..+0x68` to render-record
   `+0x18/+0x1c/+0x20/+0x24..+0x60`.
7. Render entry `0x1ef6a` derives band/destination state with `0x1ef86`, then
   calls bucket dispatcher `0x1efc2`, rule-list dispatcher `0x1f446`, and
   fixed-list dispatcher `0x1f756` in that order.

Composition and overlap rule:

- Bucket-chain output is written first. Within the selected render bucket,
  class byte `+0x04` sends compact text/downloaded glyphs to `0x1effe`,
  segment-list spans to `0x1f812`, and encoded raster rows to `0x1f88e`.
- Rule-list output is written second through `0x1f446`, using solid helper
  `0x1f596` for selector `7` or patterned helper `0x1f4e0` for other
  documented selectors.
- Fixed-list output is written last through `0x1f756` / `0x1f7b0` when the
  current band satisfies the five-band gate.
- Pixel composition at this shared layer is ordered direct writing. The
  renderer helpers compute destination addresses from `0x783a20`,
  `0x783a22`, `0x783a28`, and object coordinates, then store generated bytes,
  words, or longwords. There is no implicit page-wide OR/XOR/AND blend step
  between object classes; overlapping objects resolve by the `0x1ef6a` call
  order above.

Evidence and current boundary:

- Fixture `addressed text/rule/raster field groups reach publication and
  render entry` carries compact text, selector-7 rule, and mode-0 raster
  objects through one page root, `0xff1e`, `0x1ed84`, `0x1edc6`, and
  `0x1ef6a`.
- Fixture `0x1ef6a render entry composes bucket, rule, and fixed-width lists in
  call order` pins the render-entry ordering after the bridge.
- Fixture `0x1ef6a page-band walk merges text raster and crossing rule` covers
  the band-local mixed output case where bucket-chain rows and a crossing rule
  share the same render band.
- The supporting renderer details are in
  [page-raster-imaging.md](page-raster-imaging.md) under
  `Bitmap Object Dispatch Semantic Checkpoint`, with low-level storage evidence
  in `generated/disasm/ic30_ic13_page_root_allocate_010084.lst`,
  `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`,
  `generated/disasm/ic30_ic13_raster_object_queue_013070.lst`,
  `generated/disasm/ic30_ic13_display_list_helpers_013386.lst`,
  `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst`, and
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`.
- No ROM-local middle edge remains for the documented mixed-page storage,
  publication, bridge, or object-class render order. Remaining composition work
  must expose a new root field, object class, bridge field, render call order,
  or helper write rule; physical paper output is not an oracle for this
  checkpoint.

## Reproduction Contract

A byte-stream renderer must preserve:

- `0x10084` first-root creation versus root reuse;
- the root `+0x1c`, `+0x20`, `+0x24`, `+0x28`, and `+0x2c..+0x68` field
  meanings;
- `0x1381c` chunk accounting and link behavior;
- `0x1387c` bucket object reuse/new-head behavior;
- short versus segmented compact bucket object shapes;
- portrait text-span storage as class-`0x40` segment-list bucket objects under
  root `+0x1c`;
- landscape text-span storage as fixed-list objects under root `+0x28`;
- encoded-raster dense-row splitting through `0x132b6` and `0x13070`;
- ordered rule/fixed-list insertion through `0x133aa` and `0x136d2`;
- no-room returns that leave existing visible lists unchanged;
- publication through `0xff1e` before commands such as reset, FF, page-size,
  orientation, paper-source, and copies clear or mutate page state;
- render-record bridge copies through `0x1ed84` and `0x1edc6`;
- context-slot preservation from page record to render record.

## Confidence

High for page-root creation, initializer fields, stream allocator accounting,
bucket reuse/new-head behavior, rule/fixed insertion order, no-room returns,
publication root/header fields, and render-record bridge copies because each is
backed by disassembly and named fixtures. High for allocator provenance at the
page-record boundary because the addressed page-record fixtures prove the
`0x1381c` results and bridge state, while the shared `0x170c` / `0x1710` /
`0x18b4` heap contract is covered by the macro/parser firmware checkpoint.
This is not a remaining software-visible page-record edge.

## Remaining Edges

- No ROM middle edge remains for page-root field meanings, stream allocator
  accounting, compact/raster bucket object layout, rule/fixed list layout,
  local no-room returns, `0xff1e` publication fields, or `0x1ed84` /
  `0x1edc6` bridge fields.
- Remaining work is new byte-stream variants that expose different page-record
  state, plus physical engine/scheduler pacing after the render-record bridge.
