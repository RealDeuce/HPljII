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
- Compact/raster bucket object `+4`: selector or class byte.
- Compact/raster bucket object `+6`: count/capacity.
- Compact/raster payload begins at `+8` or `+0a`, depending on object class.
- Rule/fixed object `+0`: next pointer.
- Rule/fixed object `+4`: bucket byte.
- Rule/fixed object `+5`: selector or mode.
- Rule/fixed object `+6`: ordered key.
- Rule/fixed dimensions and extent fields begin at `+8`.

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

- Full live CPU-memory continuity for dense parser-produced pages that cross
  root allocation, multiple producer families, publication, and scheduler
  handoff in one trace.

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
- `0x133aa` writes ordered rectangle/rule nodes under root `+0x24`.
- `0x136d2` writes ordered fixed-rule nodes under root `+0x28`.
- `0xff1e` copies root fields into a published pool record, writes published
  state, clears the current root, and preserves command-specific pool header
  fields such as copy-count word `+0x0c`.
- `0x1ed84` writes active render-record header words from the selected source
  record, then delegates queue/list/context copying to `0x1edc6`.
- `0x1edc6` writes render-record bucket, rule, fixed-list, and context roots.

## Readers And Consumers

- Printable text through `0xd04a` / `0x12f2e` consumes the current root and
  `0x1387c` bucket allocator.
- Rectangle fill through `0x10898` consumes the current root and inserts rule
  nodes through `0x13386` / `0x133aa`.
- Raster transfer through `0x105d0` consumes the current root and queues
  encoded-span objects through `0x13070` / `0x13250`.
- Span flush through `0x12714` consumes the fixed-list path through
  `0x136d2`.
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

## Reproduction Contract

A byte-stream renderer must preserve:

- `0x10084` first-root creation versus root reuse;
- the root `+0x1c`, `+0x20`, `+0x24`, `+0x28`, and `+0x2c..+0x68` field
  meanings;
- `0x1381c` chunk accounting and link behavior;
- `0x1387c` bucket object reuse/new-head behavior;
- short versus segmented compact bucket object shapes;
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
backed by disassembly and named fixtures.

Medium for allocator provenance because current fixtures model the allocator
result and bridge state for dense pages. This is not a remaining
software-visible page-record edge. The shared `0x170c` / `0x1710` / `0x18b4`
heap contract itself is covered by the macro/parser firmware checkpoint.

## Remaining Edges

- No ROM middle edge remains for page-root field meanings, stream allocator
  accounting, compact/raster bucket object layout, rule/fixed list layout,
  local no-room returns, `0xff1e` publication fields, or `0x1ed84` /
  `0x1edc6` bridge fields.
- Remaining work is new byte-stream variants that expose different page-record
  state, plus physical engine/scheduler pacing after the render-record bridge.
