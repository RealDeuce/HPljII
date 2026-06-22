# Reverse-Engineering Ledger

Goal: track the ROM facts needed to reproduce LaserJet II output from
the same host byte stream, down to pixel placement and built-in raster
data.

## Current Anchors

### Raw ROM identity

Status: Anchored

Evidence: Four verified TC531000P dumps with stable hashes

### ROM interleave

Status: Anchored

Evidence: `IC30,IC13` is executable; `IC32,IC15` is resource/data

### CPU entry

Status: Anchored

Evidence: 68000 reset PC `0x00000110` in `IC30,IC13`

### Exception handling

Status: Early hypothesis

Evidence: vector table targets RAM trampolines at `0x00780000`

### Extension probing

Status: Anchored, format unknown

Evidence: firmware checks `0x200000` and `0x400000` for `PROG`; scans
for `HEAD` records

### Host byte fetch

Status: Anchored as normalized byte source with executable priority
fixtures; physical interface names still need board/manual correlation

Evidence: routine `0x0000a904` returns normalized bytes in `D7` from
stacked pushback buffers, a data-chain source, a ring buffer, or one of
two direct hardware paths, as documented in
`generated/analysis/ic30_ic13_host_byte_fetch_flow.md`; mode
`0x780e40 == 1` polls `0x8e01.4`, reads `0x8801`, waits on `0x8c01.0`,
and handshakes through `0xa601` / `0xaa01`; the alternate nonzero mode
polls `0xfffee005`, reads `0xfffee001`, reports status bits into
`0x780e2e`, and handshakes through `0xfffee009`. The semantic model now
classifies the source fields, firmware bookkeeping, downstream
consumers, output effect, and unresolved physical-interface edges under
`Host Byte Fetch And Data-Chain Input`.

### Main PCL parser

Status: Anchored

Evidence: routine `0x00011774` dispatches bytes through mode-indexed
parser tables at `0x112a4` and `0x116f6`

### PCL tokenizer

Status: Anchored

Evidence: routines `0x0000da9a`, `0x0000daf0`, and `0x0000db74` parse
ESC sequences, `0x20..0x3f` parameter/intermediate bytes, signs, decimal
values, fractions, and continuation markers; executable fixtures pin
six-byte records for lowercase-final chaining, signed fractions,
semicolon continuation, and delayed payload record restore, and
alternate/data-mode payload count consumption through
`0x1228a`/`0x12358`

### Direct control and reset

Status: Anchored for direct control-code side effects, vertical layout,
margin and cursor-position conversions, narrow byte streams, mixed
text/control, LF, HT/BS, left/right-margin, lowercase-chained margin,
horizontal-column, horizontal-decipoint, vertical-row,
vertical-decipoint, and lowercase-chained cursor-position, top-margin,
perforation-skip, page-length, HMI, and cursor-stack parser-to-page-record
boundaries, reset sequencing, ROM
parser dispatch of publication streams, host-fetched publication header
fields for reset, FF, page-size, and orientation, addressed
text/rule/raster FF publication, and synthetic mixed reset fixtures,
with `0xcda2` reset/default environment state now decoded for
page/control pool setup, cursor-stack reset, HMI/VMI recompute,
line-termination clearing, and default bytes
`0x78219d`/`0x78219e`/`0x7821a2`; full firmware parser/reset fixtures
incomplete

Evidence: parser mode 0 maps CR/LF/FF/HT/BS to handlers `0xf02c`,
`0xf08c`, `0xf0f0`, `0xf1cc`, `0xf2a8`; `ESC &k#G` stores
line-termination mode bits in `0x78318f`; `ESC &k#H` maps to `0xca8c`
and stores packed HMI in `0x78315c`; `ESC &f#S` maps to `0xf75e` and
pushes/pops the cursor stack at `0x782c96..0x782d36`;
`ESC &l#C/#D/#E/#F/#L` map to
`0xcb00`/`0xc992`/`0xece2`/`0xea9e`/`0xee64` and update VMI
`0x783160`, top offset `0x782dce`, text-length bottom `0x782dd2`,
perforation-skip byte `0x783191`, and pending vertical cursor state;
`ESC &l#P` maps to `0xf9e8` and converts current VMI lines into page
extent `0x782dba` with orientation-threshold internal page-code
selection;
`ESC &l#W` maps to `0x11f6e` and schedules delayed vertical-forms-control
handler `0x12cfe`, which writes the table rooted at `0x782dde` and
updates text-bottom cache `0x782dd2`; lowercase `ESC &l#w...#W` preserves
the first delayed snapshot through uppercase restore; `ESC &l#V` maps to
`0x1280a` and consumes that table for channel jumps; its forward in-text
path is now
anchored through channel search, `0x10084`, `0xf06e`, and `0xf34a`, while
its before-top normalization path is anchored through `0x128ae..0x128f4`,
its selector-zero target-equal path is anchored through
`0x12966..0x1299a`, and its selector-zero page-eject path is anchored
through `0x1299c..0x129c4`, and one wrap-hit page-eject path is anchored
through `0x129c6..0x12af8`, the wrap-no-hit page-eject path is anchored
through `0x12a22..0x12a78`, and one target-after-text bottom-recovery
path is anchored through `0x129ee..0x12b5a`, while the start-line-zero
non-publishing target-after-text path is anchored through
`0x129fc..0x12afc`, and the start-after-text no-wrap path is anchored
through `0x12a02..0x12afc`, while the start-after-text wrap-after-text
paths are anchored through `0x12a7a..0x12af8` and
`0x12a7a..0x12afc`; selector-zero start-after-text recovery is anchored
through `0x1299c..0x12b92`; alternate wrap-recovery and page-recovery
branches remain unresolved;
`ESC &a#L/#M` map to
`0xeb58`/`0xec0c` and convert HMI margin columns into
`0x782dd6`/`0x782dda` with reject/clamp/cursor-move cases;
`ESC &a#C/#H/#R/#V` map to `0xf39e`/`0xf416`/`0xf560`/`0xf60a` and
convert HMI/VMI/decipoint positions through helpers `0xf4ca` and
`0xf6e2`; CR/LF/FF/HT/BS, cursor-stack, vertical-layout, margin, and
cursor-position side effects are documented in generated reports;
`tools/render_fixture_harness.py` now pins synthetic packed-state
fixtures for those effects plus `ESC &f#S` push/pop/clamp/bounds cases,
`ESC &k#H` conversion/bounds cases,
`ESC &l#C/#D/#E/#F` conversion/reject/default cases,
`ESC &l#L` selector cases, `ESC &a#L/#M`
conversion/reject/cursor-move cases, `ESC &a#C/#H/#R/#V`
conversion/relative/clamp cases, and narrow direct-control byte-stream
fixtures for `ESC &k1G`+CR, `ESC &k2G`+LF, `ESC &k2G`+FF,
`ESC &k3G`+CR/LF/FF, `ESC &k0G`+HT/BS, `ESC &k6H!!`,
`ESC &f0S`/`ESC &f1S`, chained `ESC &l8c6d3e2F`,
chained `ESC &a3.5c+1R`, and chained `ESC &a6l9M`;
mixed printable/control fixture `ESC &k1G!\r!` proves CR+LF before the
second glyph and now ties ROM parser handlers
`0xedf8`/`0xd04a`/`0xf02c`/`0xd04a` to the page-record allocator/bridge
result; `ESC &k6H!!`, `ESC &k2G!\n!`, `ESC &k0G HT BS !`,
`ESC &a1L!`, `ESC &a1M!`, `ESC &a6l9M!`, `ESC &a2C!`,
`ESC &a72H!`, `ESC &a1R!`, `ESC &a72V!`, `ESC &a2c+1R!`,
`ESC &l3E!`, and `ESC &l1L!` now tie HMI, LF, HT/BS, left/right-margin,
lowercase-chained margin, horizontal-column, horizontal-decipoint,
vertical-row, vertical-decipoint, lowercase-chained cursor-position,
top-margin, and perforation-skip handlers to shifted or unchanged
page-record text output; `ESC &l66P!` now ties page-length handler
`0xf9e8` to page extent `3300`, refreshed cursor y `126`, and following
printable `!` at compact coord `0x9001`;
`ESC &l4W 00 00 00 02 !` now ties parser handler `0x11f6e`, delayed
payload handler `0x12cfe`, data-byte reader `0xdace`, VFC table prefix
`00 00 00 02`, derived text bottom `190`, and following printable `!`
at compact coord `0x9001`;
`ESC &l4w4W 00 00 00 02 !` now ties parser handler sequence
`0x11f6e`, no-dispatch continuation, `0x11f6e`, lowercase delayed
snapshot `80 77 00 04 00 00`, unchanged pending state after uppercase
`W`, restored lowercase record, payload offset after uppercase `W`, and
following printable `!` at compact coord `0x9001`;
`ESC &l2V!`, starting from that VFC table state, now ties parser handler
`0x1280a`, channel mask `0x0002`, line `1`, page-root helper `0x10084`,
CR helper `0xf06e`, text-flush helper `0xf34a`, cursor move
`x 40 -> 10` and `y 126 -> 176`, and following printable `!` at compact
coord `0xb001`;
before-top `ESC &l2V!`, starting from y `89` with top offset `90`, now
ties parser handler `0x1280a`, branch `0x128ae..0x128f4`, start-line
normalization `64 -> 0`, channel mask `0x0002`, target line `1`, cursor
move `x 40 -> 10` and `y 89 -> 176`, and following printable `!` at
compact coord `0xb001`;
`ESC &l0V!`, starting from the same VFC table state at top-of-form target
y `126`, now ties parser handler `0x1280a`, branch `0x12966..0x1299a`,
page-root helper `0x10084`, unchanged cursor `x 40, y 126`, and
following printable `!` at compact coord `0x9e02`;
`!\x1b&l0V!`, starting from the same VFC table state after a queued
printable at y `176`, now ties parser handler `0x1280a`, branch
`0x1299c..0x129c4`, helper sequence `0x10084`, `0xf06e`, `0xf34a`,
`0xf34a`, `0xf124`, old-page publication at compact coord `0xbe02`,
cursor reset `x 58 -> 10`, vertical reset `y 176 -> 126`, and fresh
post-eject printable output at compact coord `0x9001`;
selector-zero start-after-text `ESC &l0V!`, starting at y `3290`, now
ties parser handler `0x1280a`, branch `0x1299c..0x12b92`, recovery edge
`0x12b5e..0x12b92`, skipped publication, helper sequence `0x10084`,
`0xf06e`, `0xf34a`, cursor move `x 40 -> 10` and `y 3290 -> 126`, and
following printable output at compact coord `0x9001`;
`!\x1b&l2V!`, starting from the same VFC table state after a queued
printable at y `226`, now ties parser handler `0x1280a`, wrap-hit branch
`0x129c6..0x12af8`, helper sequence `0x10084`, `0xf34a`, `0xf124`,
`0xf06e`, `0xf34a`, `0xf06e`, `0xf34a`, old-page publication at compact
coord `0xde02`, wrapped target line `1`, cursor reset `x 58 -> 10`,
vertical move `y 226 -> 176`, and fresh post-wrap printable output at
compact coord `0xb001`;
empty-table `!\x1b&l2V!`, starting after a queued printable at y `226`,
now ties parser handler `0x1280a`, wrap-no-hit branch
`0x12a22..0x12a78`, helper sequence `0x10084`, `0xf34a`, `0xf124`,
`0xf06e`, `0xf34a`, old-page publication at compact coord `0xde02`,
wrapped search stop at line `3`, cursor reset `x 58 -> 10`, vertical
move `y 226 -> 126`, and fresh post-recovery printable output at compact
coord `0x9001`;
before-top `ESC &l2V!`, with channel 2 only at VFC line `63`, now ties
parser handler `0x1280a`, normalization `0x128ae..0x128f4`, start-line
zero target-after-text branch `0x129fc..0x12afc`, skipped publication
edge `0x12a12..0x12a1e`, helper sequence `0x10084`, `0xf06e`,
`0xf34a`, cursor move `x 40 -> 10` and `y 89 -> 104`, and following
printable output at compact coord `0x3001`;
empty-table start-after-text `ESC &l2V!`, starting at y `3290`, now ties
parser handler `0x1280a`, start line `64`, branch `0x12a02..0x12afc`,
skipped publication, helper sequence `0x10084`, `0xf06e`, `0xf34a`,
cursor move `x 40 -> 10` and `y 3290 -> 54`, and following printable
output at compact coord `0x1001`;
default-table start-after-text `ESC &l2V!`, starting at y `3290`, now
ties parser handler `0x1280a`, start line `64`, wrap hit at VFC line
`1`, branch `0x12a7a..0x12af8`, skipped publication edge
`0x12a8a..0x12aa2`, helper sequence `0x10084`, `0xf06e`, `0xf34a`,
cursor move `x 40 -> 10` and `y 3290 -> 176`, and following printable
output at compact coord `0xb001`;
line-63 start-after-text `ESC &l2V!`, starting at y `3290`, now ties
parser handler `0x1280a`, start line `64`, wrap hit at VFC line `63`,
branch `0x12a7a..0x12afc`, bottom recovery edge `0x12afc..0x12b5a`,
skipped publication edge `0x12a8a..0x12aa2`, helper sequence `0x10084`,
`0xf06e`, `0xf34a`, cursor move `x 40 -> 10` and `y 3290 -> 104`, and
following printable output at compact coord `0x3001`;
`!\x1b&l2V!`, with channel 2 at VFC line `63` and a queued printable at y
`3193`, now ties parser handler `0x1280a`, target-after-text branch
`0x129ee..0x12b5a`, helper sequence `0x10084`, `0xf34a`, `0xf124`,
`0xf06e`, `0xf34a`, old-page publication at compact coord `0x4e02` in
bucket `198`, bottom recovery `y 3193 -> 104`, and fresh post-recovery
printable output at compact coord `0x3001`;
`ESC &f0S ESC &a2C ESC &f1S!` now ties cursor-stack push/pop and
cursor-position handlers to restored page-record text output at compact
coord `0x0001`; `ESC E` maps to reset handler `0xcc52`, reset flow is
documented in `generated/analysis/ic30_ic13_esc_e_reset_flow.md`,
synthetic `ESC E` byte-stream fixtures cover valid-page-root publication
and missing-root clearing, host-fetched missing-root `ESC E` now drains
from modeled `0xa904` ring bytes to parser handler `0xcc52`, mixed
publication streams `!\x1bE`, `ESC &k2G!\f`, `!\x1b&l1A`,
`!\x1b&l1O`, `!\x1b&l2H`, and `!\x1b&l2X\f` are traced through
`0x11774` to printable branch `0xd04a`, reset `0xcc52`,
line-termination `0xedf8`, FF `0xf0f0`, page-size `0xfc74`,
orientation `0x10220`, paper-source `0xef62`, and copies `0xeef0`, and
mixed
printable/reset fixture `!\x1bE` proves reset publication after queued
text in the same byte-stream model and now has page-record
allocator/bridge/publication coverage, with the host-fetched reset, FF,
page-size, orientation, paper-source, and copies cases pinning the
`0xff1e` published pool
header fields plus the `0x1edc6` published bucket/context copy before
render, and with addressed reset, FF, page-size, and orientation
allocation variants now proving the same compact bucket materialization
through `0x1387c`/`0x1381c`;
`generated/analysis/ic30_ic13_esc_e_reset_flow.md` now also
names `0xcda2` environment-default writes, including four 0x6c-byte
page/control records rooted at `0x780f02`, bucket backings at
`0x7810bc + 0x400*n`, parser scratch `0x782a26`, cursor-stack top
`0x782d36`, HMI `0x78315c`, reset VMI `0x783160`, line-termination byte
`0x78318f`, and default inputs `0x78219d`/`0x78219e`/`0x7821a2`

### PCL command map

Status: Anchored, handlers need deeper annotation and macro allocator/frame
internals

Evidence: flattened generated map links high-value PCL commands to
handlers for page geometry, raster, rectangles, font selection,
downloaded-font control, and macros;
`generated/analysis/ic30_ic13_rectangle_graphics_flow.md` decodes
`ESC *c#A/#B/#H/#V/#G/#P` into rectangle size, area-fill id, selector
mapping, clipping, `0x13386` rule-list queueing, including a chained
`ESC *c12a5b0P` byte-stream fixture and ROM parser dispatch trace for
selector-7 rule creation, modeled `0xa904` ring fetch and `0x1edc6`
rule-list bridge coverage plus `0x1ed84`/`0x1ef6a` render-entry
coverage, selector-7 solid rendering and band-crossing continuation
through `0x1f446` / `0x1f596`, gray selectors `0..6`, HP pattern
selectors `8..13`, sub-byte shifted, band-crossing, and two-band
page-assembly HP-pattern cases rendering through `0x1f446` / `0x1f4e0`,
plus a parser-to-retry boundary for `ESC *c12a5b0P` where the `0x10d22`
no-room path publishes the old root through `0xff1e`, allocates a fresh
root through `0x10084`, and retries the selector-7 rule through
`0x13386`; `generated/analysis/ic30_ic13_font_control_flow.md` decodes
`ESC *c#D` current font-id normalization and `ESC *c#F` values `0..6`
into release/character cleanup/mark/unmark/housekeeping helpers, and the
harness now traces chained `ESC *c17d25e5F` through ROM parser modes
`0/1/3/16` to handlers `0x15a56`, `0x15a18`, and `0x16df6`; macro ID
`ESC &f#Y` at `0xe112` stores absolute current id `0x783164`, macro
control `ESC &f#X` at `0xdd08` dispatches selectors `0..10` for
start/stop/execute/call/overlay/delete/temp/permanent through the macro
record pool and `0xe418` data-chain frame builder, the harness now
traces `ESC &f-123y0x1X` through ROM parser modes `0/1/5/17` to handlers
`0xe112` and `0xdd08`, proves alternate table `0x116f6` stores
macro-definition payload bytes while still routing `ESC &f1X` to
`0xdd08`, and macro command-stream fixtures now drive id/start/stop plus
plain and mixed-control payload definition, execute/call frame creation,
overlay enable/disable state, delete-current/all, guard-state
suppression, and permanence/delete state, and now drain those definition
and command streams from modeled `0xa904` ring fetch before reaching the
same alternate parser trace, macro records, and data-chain frames. The
harness also covers full host-fetched define-and-execute and
define-and-call streams through the ROM/alternate parser trace into
execute/call data-chain frames, `0xa904` data-chain byte fetch and
end-marker outer-source resumption, execute/call replayed `!\r` dispatch
through `0xd04a`/`0xf02c` into page-record output with the `0x1edc6`
bridge contract and `0x1ed84`/`0x1ef6a` render-entry path pinned,
host-fetched `ESC &k1G!\r!` mixed-control macro replay through
`0xedf8`/ `0xd04a`/`0xf02c`/`0xd04a` into page-record output with the
same bridge/render-entry path pinned, and macro-payload rule/raster band
composition from command bytes

### Page geometry tables

Status: Anchored, variable names provisional

Evidence: page-size helpers at `0x9d16`, `0x9d4e`, `0x9d86`, and
`0x9dbe` decode internal page codes into manual-matched logical 300 dpi
page dimensions; executable fixtures now pin masked table lookup, the
full Technical Reference logical-dimension and printable-area margin
cross-checks for supported `ESC &l#A` sizes, `ESC &l#A` handler `0xfc74`
mapping for letter and PCL `80`, and `ESC &l#O` handler `0x10220`
landscape active-extent swap, vertical offset source, printable extent,
top offset, `0x103ea` threshold reloads, and chained `ESC &l1a1O`
byte-stream selector coverage

`ESC &l#P` handler `0xf9e8` is now modeled for nonzero page lengths:
6-LPI `ESC &l66P` selects internal code `2`, stores page extent `3300`,
recomputes top/text bounds, and the parser-to-page-record fixture proves
the following printable byte uses the refreshed text cursor. The
zero-parameter publication/default-page branch is identified but still
needs a dedicated fixture.

Vertical forms control is now a composed semantic state block in
`notes/semantic-state-model.md`. The canonical table is
`0x782dde..0x782edd`; derived/cache fields include `0x782dc2`,
`0x782dd2`, `0x782ede`, `0x782edf`, and `0x782ee0`; `0x782ee1` is
firmware bookkeeping and `0x78299e` remains parser scratch. The table
writer cluster `0x11f6e -> 0x12cfe`, default builder `0x12b96`, and
consumer `0x1280a` are identified. The `0x1280a` forward in-text hit path
is anchored through `0x1292a..0x1295c` search and `0x12aa6..0x12af8`
cursor commit. The selector-zero target-equal path is anchored through
`0x12966..0x1299a`; the selector-zero page-eject path is anchored through
`0x1299c..0x129c4`, including page publication through `0xf124`. The
before-top start-line path is anchored through `0x128ae..0x128f4`. The
wrap-hit page-eject path is anchored through `0x129c6..0x12af8`. The
wrap-no-hit page-eject path is anchored through `0x12a22..0x12a78` for
the empty-table fixture. The target-after-text bottom-recovery path is
anchored through `0x129ee..0x12b5a` for the line-63 fixture, and the
start-line-zero no-publish variant is anchored through `0x129fc..0x12afc`.
The start-after-text no-wrap path is anchored through `0x12a02..0x12afc`
for start line `64` with an empty table, and the start-after-text
wrap-after-text path is anchored through `0x12a7a..0x12af8` for the
default line-1 selector hit, plus `0x12a7a..0x12afc` for the line-63
selector hit. The selector-zero start-after-text recovery path is
anchored through `0x1299c..0x12b92`. The highest-value unresolved middle
edges are alternate-entry `0x12a02..0x12a10`, alternate-entry
`0x12a22..0x12a78`, alternate-entry `0x12afc..0x12b5a`, and wrap-entry
`0x12b5e..0x12b92`.

### Raster/text/page-object path

Status: Anchored through parser bridge, render dispatch, executable
allocator/bridge, executable queued raster rows, and executable
expansion/destination/row-copy/resource-resolution/glyph-row/producer-modeled
bucket/positioning/font-record/font-allocation fixtures, plus
host-fetched primary, lower-resolution, capped/drained, consecutive-row,
active-resolution, end-raster/re-enable, chained-resolution, and
chained-transfer raster streams, plus modeled `0xff1e` publication of
the combined text/rule/raster page record before `0x1ed84`/`0x1ef6a`
rendering after one mixed stream runner handles text, `ESC *c`, and
delayed raster transfer commands, including a trailing-FF publication
variant; a combined 2,215-byte host-fetched font-download printable
stream now carries `ESC *c4660d37e5F`, `ESC )s2193W`, and printable `%`
into a downloaded glyph `0x25` segmented page object before `0x1edc6`,
`0x1ed84`, and `0x1ef6a`; full parser-produced page-object integration,
font-download parser-populated inline/downloaded source records,
remaining full live-parser raster, parser-populated font-download
records, and full parser-produced page-object coverage incomplete

Evidence: `generated/analysis/ic30_ic13_raster_graphics_flow.md`
collects the raster command edge: `ESC *t#R`, `ESC *r#A`, `ESC *r#B`,
and `ESC *b#W` map to handlers `0x10808`, `0x1075a`, `0x107fa`, and
delayed handler `0x105d0` via `0x121cc`; raster bytes are copied by
`0x138de` into queued page objects built by `0x13070`; normal printable
text bytes flow through `0xa904` -> `0xda9a` -> `0x11774` -> `0xd04a`,
where `0x1393a` builds source object `0x782d7e`, as documented in
`generated/analysis/ic30_ic13_printable_text_path.md`; paired
post-source text paths are documented in
`generated/analysis/ic30_ic13_text_cursor_span_flow.md`, with cursor
`0x782c8a` named as horizontal and `0x782c8e` named as vertical by
text/control handlers plus the raster-origin fixture; unflagged text
uses `0xd140` / `0xd3b2` / `0xd4ac`, flagged text uses `0xd550` /
`0xd824` / `0xd8fc`, and the queue handoffs reach compact bucket
producer `0x12f2e`; compact bucket allocator `0x1387c` is decoded in
`generated/analysis/ic30_ic13_compact_bucket_allocator.md`; text spans
enter the same storage through `0x12714` / `0x12f2e`; rectangle/rule
handlers share page-root queues through `0x13386` and related helpers;
`0x1edc6` copies queued record pointers into render work records, with
its queue/list/context-slot contract decoded in
`generated/analysis/ic30_ic13_page_record_bridge.md`; `0x1efc2`
classifies bucket objects; raster maps to `0x1f88e`, compact text/glyph
buckets map through `0x1effe`, and rule lists map through `0x1f446` /
`0x1f756`; compact glyph objects select render-record context slots
copied from page-root `+0x2c` and traced in
`generated/analysis/ic30_ic13_font_context_bridge.md`; compact text
payload glyph bytes are mapped through `0x782f32` / `0x783032` and
documented in `generated/analysis/ic30_ic13_text_glyph_index_flow.md`;
active symbol-set flow from `ESC (` / `ESC )` to `0x783144` / `0x783146`
is documented in
`generated/analysis/ic30_ic13_active_symbol_set_flow.md`; symbol-set
patch tables and Technical Reference names are decoded in
`generated/analysis/ic30_ic13_symbol_set_patch_tables.md`; compact and
encoded-span payload modes are named in
`generated/analysis/ic30_ic13_render_subrenderers.md`; deterministic
encoded raster expansion fixtures are generated in
`generated/analysis/ic30_ic13_render_expansion_fixtures.md`;
destination/clipping fixtures are generated in
`generated/analysis/ic30_ic13_render_destination_fixtures.md`; compact
glyph row-copy fixtures are generated in
`generated/analysis/ic30_ic13_render_row_copy_fixtures.md`;
`tools/render_fixture_harness.py` executes those primitive models plus
`0xa904` host byte fetch source-priority fixtures, ring-fed
reset/FF/page-size/orientation/paper-source/copies publication streams
through parser handlers and published rows, addressed reset/FF publication
allocation variants, real built-in glyph-resource resolutions, full decoded
mode-1
glyph-row fixtures, main `0x1f08e` row-copy
rendering for four named glyphs plus a ROM-scanned render-span matrix
covering spans 1, 2, 4, 6, and 8, one symbol-set stream/map fixture for
`ESC (2U` / `ESC )0E` through ROM parser setup handlers
`0x1201e`/`0x12008`, terminal handler `0x120be`, `0x1be22`, `0xc580`,
and `0x14f16`, one producer-modeled short text bucket object from
`0x14d9c` base-map through `0x1393a` / `0x12f2e`, `0x1387c` allocator
fixtures that reuse a matching short bucket object, allocate a new head
when full, render an allocator-queued short object, and allocate/reuse
the segmented `0x2000` tall-glyph buckets from `64/8` down to `0/0`, a
`0x1edc6` bridge fixture that copies the compact bucket/context slots,
normalizes rule/fixed lists, pins producer-shaped `0x13386`/`0x136d2`
rule objects, and covers text/rule/raster plus macro-payload rule/raster
band composition, parser-derived `ESC *t#R`/`ESC *r#A` raster state
fixtures, modeled `ESC *t300R`/`ESC *r1A`/`ESC *b4W`,
`ESC *t150R`/`ESC *r0A`/`ESC *b2W`, `ESC *t100R`/`ESC *r0A`/`ESC *b2W`,
and `ESC *t75R`/`ESC *r0A`/`ESC *b2W` raster command/data stream
fixtures, with the first host-fetched `ESC *b4W` object carried through
the `0x1edc6` bridge contract, plus a host-fetched two-payload
`ESC *t300R`/`ESC *r0A` multi-row stream through delayed handler
`0x0105d0`, the `0x1edc6` bridge contract, and `0x1ed84`/`0x1ef6a`
render-entry coverage, a parser-to-gate edge check for host-fetched
`ESC *t300R`/`ESC *r0A`/`ESC *b4W` capped, page-extent, beyond-extent,
and negative-row transfers, host-fetched `0xdace` payload-control
normalization, same-group lowercase-final chaining fixtures for
`ESC *t300r150R` and host-fetched chained `ESC *b2w`/`2W`
payload/bridge/render-entry boundaries, now with host-fetched
`ESC *t300r150R` parser-family evidence, plus a host-fetched active
`ESC *t75R` stream proving handler `0x10808` leaves current mode/scale
intact, plus a host-fetched `ESC *rB` stream proving handler `0x107fa`
clears only raster active state and allows a later `ESC *t150R` mode
change, byte-aligned mode-0/non-byte-aligned mode-0/mode-1/ byte-aligned
mode-2/non-byte-aligned mode-2/band-clipped mode-2/mode-3 raster row
fixtures that queue objects `00 00 00 00 80 00 00 04 00 01 f0 0f aa 55`,
`00 00 00 00 80 00 00 02 04 01 c3 3c`,
`00 00 00 00 80 01 00 02 00 01 f0 0f`,
`00 00 00 00 80 02 00 02 00 01 f0 0f`,
`00 00 00 00 80 02 00 02 04 01 f0 0f`,
`00 00 00 00 80 02 00 02 f0 01 f0 0f`, and
`00 00 00 00 80 03 00 02 00 01 f0 0f` through `0x13070` / `0x13250` /
`0x138de`, bridge the mode-0 object through `0x1edc6`, and render them
through `0x1f88e`, two `0xd824`-positioned short text bucket objects
covering normal positioning and negative-left overflow, one-byte and
two-byte normal printable stream fixtures for host byte `0x21` (`!`)
through `0x1393a` / `0xd824` / `0xd550` default advance / `0x12f2e` /
render, an initialized `LINE_PRINTER` HMI fixture that renders real
sub-byte coord `0x0202` as `$a001 = 0x12` / pixel x `34`, a plain `!!`
parser-to-page-record fixture tying two `0xd04a` events to one root
allocation, bucket-0 reuse, bridge, and rendered rows, a mixed
`ESC &k1G!\r!` fixture that queues the post-CR glyph at coord `0x3b00`,
shows full-byte shifted blank-row clearing, and has a host-fetched
page-record allocator/bridge variant, a grouped host-fetched direct
text/control fixture tying the plain, CR/LF, HT/BS, margin,
cursor-position, vertical-layout, and cursor-stack page-record streams
to modeled `0xa904` ring fetch, parser handlers, object prefixes,
`0x1edc6` bridge fields, `0x1ed84`/`0x1ef6a` render-entry dispatch,
and rendered row counts, a host-fetched `! ESC *c12a5b0P` fixture that
renders compact text plus a selector-7 rule from one combined page
record through `0x1ed84`/`0x1ef6a`, a host-fetched `! ESC *c12a5b0P
ESC *t300R ESC *r0A ESC *b2W` fixture that adds a mode-0 raster object
to the same bucket/rule page-record shape, an addressed text/rule/raster
field-group checkpoint that pins canonical objects `0x00d0c004`,
`0x00d0c02a`, and `0x00d0c038`, parser scratch record
`80 57 00 02 00 00`, allocator state `0x782a70 = 0x00bc`,
`0x782a72 = 0x00d0c000`, and `0x782a76 = 0x00d0c044`, a mixed
`!\x1bE` fixture that
publishes and clears a valid current page root after queued text and has
a page-record allocator/bridge/publication variant,
selected inline/downloaded `0x14e24`/`0x14eb6` map and `0x1393a`
source-object fixture now crossing `0x1edc6` with context slot `3`
intact, plus type-2 payload-backed `0x1f0d2`/`0x1f1f0`, selected-memory
`0x1f264` isolation, and `0x16498` downloaded-pointer `0x1f264` render
fixtures now crossing `0x1edc6` plus `0x1ed84`/`0x1ef6a`,
`0x168dc`/`0x16942` font payload-reader
fixtures plus a host-fetched `ESC )s18W` payload-control
`0x1ed84`/`0x1ef6a` render-entry bridge,
fetched printable-byte selection of the installed `ESC )s2193W`
downloaded glyph into segmented `0x12f2e`/`0x1387c` page-record buckets
and `0x1ed84`/`0x1ef6a` render-entry output, plus a combined fetched
font-control / downloaded-character / printable stream proving the same
installed glyph path, `0x1edc6` bucket-root bridge, and
`0x1ed84`/`0x1ef6a` segment render from one host byte stream,
`0x172c0`/`0x16c14` downloaded-font record bookkeeping fixtures,
`0x170be`/`0x17108`/`0x17150` record lookup/mark/unmark fixtures,
`0x15a56`/`0x16df6` font-id/control dispatch fixtures,
`0x16fae`/`0x17362`/`0x17026`/`0x1719c` validation-table/staged
header/payload-backed inline allocation fixtures, plus synthetic
`0xd3b2` unflagged positioning fixtures covering both context-metric
branches, inline/downloaded `0x12f2e` short, page-record short,
width-bit, and segmented payload objects as isolation controls, and
constructed selected-inline `0x1f0d2` wide, `0x1f1f0` segmented, and
`0x1f264` segmented-wide render rows, one segmented `0x2000` text bucket
sequence for a real `LINE_PRINTER` tall glyph case through both producer
and page-record allocator shapes, and a full built-in glyph coverage
scan proving no normal wide/segmented bitmap entries, then emits
`generated/analysis/ic30_ic13_renderer_fixture_harness.md`

### Resource ROM role

Status: Anchored as font/resource source; built-in glyph payload
extraction deterministic for the verified ROM image

Evidence: `IC32,IC15` contains `HEAD`, HP copyright, `COURIER`,
`LINE_PRINTER`, dense font tables, and firmware-scanned `0x1f354` glyph
entries documented in
`generated/analysis/ic32_ic15_resource_glyph_probe.md`; built-in context
examples `0x4008004c`, `0x44080418`, and `0x440946b4` resolve to
concrete glyph entries and bitmaps in `tools/render_fixture_harness.py`;
`generated/analysis/ic32_ic15_builtin_glyph_payloads.json` now extracts
5,310 mode-1 glyph payloads, 468,534 payload bytes, and 1,664 unique
payload hashes from all 24 firmware-scanned built-in records;
`generated/analysis/ic32_ic15_builtin_font_samples.md` directly renders
`LASERJETII` rows from first `COURIER` and first `LINE_PRINTER` payloads;
`generated/analysis/ic30_ic13_font_sample_page.md` anchors the ROM
font-printout path, including the font-list headers, sample byte runs,
`0x1d12e` printable-byte helper, `0x1c5e8` current-font/page-root setup,
forced VMI/HMI defaults `0x0032` / `0x001e`, and direct row hashes for
the two ROM sample byte runs rendered through first `COURIER` and first
`LINE_PRINTER`; the outer loop is now anchored from `0x1c204`, including
class-zero/class-one passes, `0x10084` page-root creation, recent-context
tracking at `0x783f0a`, and `0xf0f0` pass finalization; candidate-row
traversal now follows `0x1b50e` lookup, `0x1c746` normalization,
`0x1c766` / `0x1c7a8` flag extraction, `0x1c710` class comparison,
`0x1d050` / `0x1d868` continuation checks, `0x1cabe` row emission,
and `0x1cf34` sample-byte emission before duplicate suppression through
the recent-context list; the report also
pins sample-page cursor and row sequencing through `0x1c916`,
`0x1ca2c`, `0x1cabe`, `0x1cf34`, and `0x1d050`, including page-limit
checks against `0x782db6`, source/metric text emission through `0xd04a`,
and the `0x31` horizontal-unit gap between the two ROM sample runs; the
row helper listing now names `0x1d198` font-name/style formatting,
`0x1d6ea` capped string emission, `0x1d71e` fixed-name sanitization,
`0x1d76c` orientation-command synthesis, and `0x1d964` / `0x1dcf2`
page-fit preflight for current and alternate sample rows; `0x1d198` local
tables now decode symbol/variant names including `UPC/EAN`,
`CODE 3 OF 9`, `OCR A/B`, and `LINE DRAW`, plus family names
`PRESTIGE`, `GOTHIC`, `TMS RMN`, `HELV`, `COURIER`, and
`LINE PRINTER`;
the startup/resource scanner `0x41a` is modeled for the verified
built-in `HEAD` chain, walking 24 typed records from `0x08004c` through
`0x0ae122`, terminating at `0x0b2f80`, adjusting the next probe step
after a cumulative `0x40000` crossing, and jumping or erroring on
`0x000000be` executable records according to their length;
`tools/render_fixture_harness.py` now extracts all named header-like
records in the verified window, proving twelve `COURIER` and six
`LINE_PRINTER` records with deterministic context, length, class,
symbol, decoded pitch/height, character range, nonzero table-entry
count, size-word tuple, first glyph entry, and firmware selection fields
including `+0x20`, `+0x21`, raw pitch/height pairs, and comparator bytes
`+0x2f..+0x31`; the first-nonzero named glyph entries are also grouped
by signed `+0/+2` positioning offsets, rows, and width, matching the
`0xd824` flagged-source placement model;
text object glyph index bytes are mapped before queuing by `0x1393a` and
initialized by `0x14d9c` / `0x14e24` / `0x14f16`; `0x1be22` computes
normal PCL symbol words from host `ESC (` / `ESC )` commands, handles
`X` as font-ID selection through `0x17708`, handles `@` through a
default-font/table subdispatch backed by `0x782f1c/20/24/28`, exposes
final `X` as dirty flag `2` with `0x78287b` set while normal/default
symbol paths are dirty flag `1`, `0x1ac0a` and `0x1af36` table-builder
writes are harness-pinned for
default/fallback symbol words, `0x1ad66` list/range/fallback
candidate-search control flow and `0x1bbfe` / `0x1b060` record-field
helper behavior are harness-pinned, `0x156de` selects active words and
can fall back through `0x782f0c/10/14/18`, and `0x14fce` symbol-set
patch records decode as named `map[dst] = map[src]` byte-copy pairs, and
the harness traces `ESC (2U` / `ESC )0E` through ROM parser
setup/terminal handlers before updating `LINE_PRINTER` map bytes through
the patch-table and Roman Extension cases

### Font candidate selection

Status: Anchored as font/resource path and render-context bridge,
rejected as raster compositor

Evidence: resource scanner `0x1a2e4..0x1ab82` builds font candidate
lists; `0x1a9be` now has executable coverage for its accepted-record
high-byte flag updates and class/range counter partitioning across
`0x782790/92/94/98/9a/9c` plus cursor-window advances at
`0x7827a0..0x7827b4`; the verified `IC32,IC15` built-in scan contributes
24 concrete `HEAD`-path records, split into twelve class `0` and twelve
class `1` low-window entries; `0x1569c` activates class-zero
pointer/count `0x782354`/`12` or class-one pointer/count `0x782324`/`12`
into `0x78287c` / `0x7827b8` and sets active bit `0x80000000`; `0x156de`
symbol filtering is executable over those concrete windows, including
requested-word matches, fallback-table selection, active-bit clearing on
rejects, first-survivor pointer update, and count shrink; `0x1519a`
height filtering is executable over the concrete class-zero window,
including +/-`0x19` range pruning, `0x1533e` nearest-height fallback,
`0x13bca` decoded built-in heights, first-survivor pointer update, and
count shrink; `0x153c6` spacing/pitch filtering is executable over the
same window, including spacing byte pruning, `0x13b76` decoded built-in
pitch, +/-`5` pitch range pruning, `0x1562c` next-upper fallback,
first-survivor pointer update, and count shrink; `0x14398` active
chooser is executable over the concrete class-zero Roman-8 survivors,
with `0x13c06`/`0x1428c` selecting slot `0x782364` / record `0x009fb0`
by decoded tuple `[1200, 0, 3, 3]`; `0x14c64` dispatch is executable for
the selected built-in offset-table record, the `0x16c14`-installed
RAM-backed `0x16fae` / `0x1719c` offset-table payload through `0x14d9c`
/ `0x15890`, and separate bit-30-clear fixed-record controls through
`0x14e24` / `0x14eb6` / `0x158be`, covering range-table writes, selected
flags, map rebuilds, Roman Extension patching, and state snapshot
`0x783148`; selected candidate longwords are copied into current-font
context records at `0x782ee6` / `0x782ef6`, installed into page-root
`+0x2c` slots, copied to render-record `+0x24`, and loaded into
`0x783a2c` before `0x1f354`; built-in selected-context low 24-bit
addresses map to `IC32,IC15` offsets by subtracting `0x80000`, and
bit-30 offset-table entries are relative 32-bit glyph-entry offsets from
the selected record start; `0x11774` now traces chained primary and
secondary font-selection streams through `(s` / `)s` mode 13, proving
spacing `0xc930`, pitch `0xc89c`, point-size `0xc6ec`, style `0xc780`,
stroke `0xc840`, and typeface wrapper `0x1205a` routing while preserving
slot setup records distinct from terminal fraction words; a modeled
bridge now feeds parsed primary `0p10h12v0s0b3T` updater writes at
`0x782eec..0x782ef2` plus dirty flags `0x782f2c/2d` into the concrete
class-zero built-in candidate filters as an isolation control; the full
`0x13eb8` primary refresh now follows `0x148f8`, `0x1569c`, `0x156de`,
`0x153c6`, `0x1519a`, `0x147b2`, `0x14758`, `0x14398`, `0x144d2`, and
`0x14c64`, with stroke filtering selecting slot `0x782354` / record
`0x00004c` while the older chooser-only bridge still selects
`0x009fb0`; the secondary `0x13eb8` path now selects class-one slot
`0x782350` / record `0x02e122` through nearest-pitch filtering, and the
transient `0x78298f` plus `0x148f8` cache-hit exits are pinned as
dispatch-skipping branches; one `0xc580` dirty-refresh branch is now
pinned through the first-clear-slot `0xc4fc` scan, and the all-live
matching-context branch is pinned through the transient `0x78298f` toggle, two
`0x13eb8` calls, `0xc428` page-root context-slot selection, and final
active-to-remembered word copy; all-live no-match and selector-mismatch
outcomes are pinned as visible branch shortcuts that skip context
installation after the documented refresh call(s); dirty-flag-2 selector
match and mismatch outcomes are pinned as `0xc428`-only or
remembered-copy-only paths with no `0x13eb8` call, including secondary
slot `0x782ef6` context selection

### Formatter manuals

Status: Anchored

Evidence: Existing notes summarize PCL Level IV, I/O, formatter, NVRAM,
page geometry, and errors Raster lowercase-final shorthand note:
references to `ESC *b2w`/`2W` mean the combined stream `ESC *b2w2W`,
where lowercase `w` records the delayed transfer while parser mode stays
in the `*b` family, and the raster payload is consumed only after the
uppercase `W` terminator triggers the `0x12218` restore/dispatch
boundary.

## Host Interface to Parser

Known from manuals:

- Host input can arrive through Centronics, RS-232C, or RS-422 paths.
- The renderer target can normalize these to a byte stream once flow
  control and status side effects are out of scope.
- PCL Level IV parser behavior is the main host-facing compatibility
  target.

ROM work needed:

- Expand named roles for byte-fetch routine `0x0000a904` callers and
  correlate the host I/O register banks `0x8e01/0x8801/0x8c01` and
  `0xfffee005/0xfffee001/0xfffee009` with the physical board interfaces.
- Trace the handler at `0x00000d52`, which polls low MMIO/status
  addresses and updates many `0x0078xxxx` state bytes.
- Identify input buffer structures in RAM.
- Decode tokenizer records rooted at `0x78299e` and the 32-entry
  command/data pool at `0x782a98`.
- Expand normal parser table `0x112a4` and alternate parser table
  `0x116f6` into named PCL commands.
- Broaden the narrow direct-control and printable stream fixtures into
  the full firmware parser path and replace synthetic `ESC E` roots with
  fuller parser-allocated page-object fixtures.
- Trace binary payload modes, especially raster graphics and downloaded
  font data.
- Use `notes/pcl-command-map.md` to prioritize page geometry, raster,
  rectangle, font, and macro handlers.
- Record malformed/combined escape behavior that is not explicit in the
  manuals.

## Print Environment and Page Model

Known from manuals:

- The renderer model needs factory defaults, user defaults, modified
  print environment, cursor stack, font state, macro state, logical
  page, printable area, and 300 dpi bitmap placement.

ROM work needed:

- Continue locating default environment tables. The `ESC E` path now
  names the reset/default environment helper `0xcda2`, including
  page/control pool setup, cursor-stack reset, HMI/VMI recompute,
  line-termination clearing, and default bytes
  `0x78219d`/`0x78219e`/`0x7821a2`; the remaining work is broader
  panel/power-on/NVRAM provenance for those defaults.
- Compare physical engine/self-test placement against the matched
  ROM/manual logical page and printable-area dimensions.
- Trace reset paths for `ESC E`, panel reset, power-on reset, and
  NVRAM/user defaults.
- Trace remaining parser-produced cursor-stack interactions and
  primary/secondary font fallback interactions.

## Fonts and Glyph Imaging

Expected resource ROM contents:

- Built-in bitmap font rasters.
- Metrics, pitches, baselines, cell sizes, offsets, style metadata.
- Symbol-set maps and internal character conversions.

ROM work needed:

- Extend the pinned visible `0xc580` branch outcomes into fuller
  upstream `0x1be22` parser-state coverage around the now-pinned
  `0x17708` success paths, broaden the parser-derived `0x156de` fallback
  fixture into live parser/font-state coverage, and extend `0x13eb8` if
  later inline/downloaded or error-return branches surface.
- Extend the modeled `HEAD` record scanner beyond the verified built-in
  resource window if cartridge or external resource images become
  available.
- Finish semantic naming of the remaining built-in record fields now
  extracted from the repeated `COURIER` and `LINE_PRINTER` fixtures,
  especially ambiguous header size words and header-level baseline
  semantics.
- Decide whether the parser-exposed `@0..@2` table/copy variants need
  compatibility-facing documentation. The default-font candidate and
  caller path is now real-record backed through `0x1b250`, `0x1b50e`,
  `0x1ab84`, `0x1b060`, and the ROM `0x120be` terminal path.
  The widened `0x1b50e` resolver now pins first/second scan windows for
  modes `0..3`, fast-probe fallback through `0x1b8ea`, and Roman-8
  duplicate/substitution state through `0x7828ac` and `0x7821a0`.
- Replace the host-fetched font-control, descriptor, resource-payload,
  and downloaded-character boundaries with a full live parser-state run
  that populates current records/source objects, then replace
  producer-modeled fixtures with full parser/page-object rendering.
  Current boundary coverage already chains fetched `ESC *c4660d37e5F`
  state into fetched `ESC )s0W` and `ESC )s80W` and `ESC )s2193W`
  streams, and a combined fetched font-control / downloaded-character /
  printable stream now drives the installed downloaded glyph into
  segmented page-record buckets and through the `0x1edc6` /
  `0x1ed84` / `0x1ef6a` render boundary. The combined stream is pinned
  as one 2,215-byte `0xa904` ring source with restored record
  `80 57 08 91 00 00`, glyph `0x25`, selector `0x3003`, buckets `9`
  and `1`, and compact dispatch target `0x1effe`.
- Model the `0x1c204` font-printout loop's emitted page objects from the
  ROM sample byte runs, then compare those rows against the direct
  payload hashes and a known printed/self-test sample to correlate
  remaining baseline/header semantics against placement.
- Identify the manual-facing names for the currently unidentified
  built-in symbol words `0N`, `10U`, and `11U`, and broaden the
  now-pinned real symbol-map samples into more live parser/font-selection
  byte-stream cases where needed. The generated symbol-set report now
  inventories all 24 built-in records and shows actual compact glyph
  bytes for Roman-8 base `8U`, hard-coded `0U`/`0E`, selected patch-table
  cases, and separate `0N`/`10U`/`11U` base records.
- Promote the generated glyph payload manifest into renderer fixture
  inputs once the renderer-side data format is chosen.

## Raster and Final Imaging

Known renderer boundary:

- We need page pixels/PDF output, not full DC controller mechanics.

ROM work needed:

- Replace the host-fetched font-control, descriptor, resource-payload,
  and downloaded-character boundaries with a full live parser-state run
  that populates current records/source objects. Current boundary
  coverage already chains fetched `ESC *c4660d37e5F` state into fetched
  `ESC )s0W`, `ESC )s80W`, and `ESC )s2193W` streams, and a combined
  fetched font-control / downloaded-character / printable stream now
  drives the installed downloaded glyph into segmented page-record
  buckets and through the `0x1edc6` / `0x1ed84` / `0x1ef6a` render
  boundary. The combined stream is pinned as one 2,215-byte `0xa904`
  ring source with restored record `80 57 08 91 00 00`, glyph `0x25`,
  selector `0x3003`, buckets `9` and `1`, and compact dispatch target
  `0x1effe`; the verified built-in scan does not provide normal built-in
  entries for these renderer modes.
- Integrate executable row-copy behavior with real page objects from the
  parser/imaging path.
- Broaden the documented printable and inline/downloaded `0x1393a` /
  `0xd824` / `0xd3b2` / `0xd550` / `0x12f2e` text-object glyph-index
  fixtures into real font-download parser records, real HMI/font
  metrics, glyph indices, and parser-produced page objects, building on
  the current host-fetched plain `!!`, mixed `ESC &k1G!\r!`,
  LF-positioned `ESC &k2G!\n!`, HT/BS-positioned `ESC &k0G HT BS !`,
  left/right-margin-positioned `ESC &a1L!` / `ESC &a1M!`,
  lowercase-chained margin-positioned `ESC &a6l9M!`, horizontal-column,
  horizontal-decipoint, vertical-row, vertical-decipoint, and
  lowercase-chained cursor-positioned `ESC &a2C!` / `ESC &a72H!` /
  `ESC &a1R!` / `ESC &a72V!` / `ESC &a2c+1R!`, top-margin-positioned
  `ESC &l3E!`, and cursor-stack `ESC &f0S ESC &a2C ESC &f1S!`
  parser-to-page-record boundaries.
- Treat direct `0x78297a` references and pool aliases documented in
  `generated/analysis/ic30_ic13_page_root_references.md` as checked
  leads; the shared `0x10084` first-root allocation and `0x10110`
  context-slot bootstrap are documented in
  `generated/analysis/ic30_ic13_page_root_allocation.md`; the shared
  `0xff1e` publish-or-clear boundary is documented in
  `generated/analysis/ic30_ic13_page_root_finalization.md`; the active
  render bridge is documented in
  `generated/analysis/ic30_ic13_render_path_references.md`.
- Keep `0x78287c`, `0x7827b8`, `0x7828a8`, and dispatch around
  `0x14398..0x156de` under font/resource selection unless later evidence
  proves a separate imaging role.
- Broaden the current text/rule/raster and macro-payload page-band
  composition fixtures into fuller parser-produced heterogeneous
  page-object rendering and final device-output pixel validation. For
  macros, continue from the composed
  `Macro Definition And Data-Chain Replay` semantic checkpoint by
  naming the resource-format fields read by `0xe860..0xe898` at bytes
  `+0x16` and `+0x20`; the full CPU-state bridge from pinned `0xe65c`
  branch effects into `0x13eb8`, `0x144d2`, `0x14c64`, and `0xc428` is
  now composed. Heap initialization `0x164a..0x170a` is now composed with
  startup helper `0x0b18`, allocator entries `0x170c`/`0x1710`, and free
  entry `0x18b4`. The `0xe5e2` layout/VFC/static-font refresh and the
  eight-record macro context stack are now composed with `0xe4f4`
  production and `0xe35a..0xe3e8` flat return semantics. The modeled
  `0x1ef6a`
  page-band merge now covers compact text, mode-0 raster, and a crossing
  patterned rule across bands `0` and `5`; modeled rectangle fill
  clipping now covers left/right/top/bottom, landscape-edge, and
  off-page ignore cases; compact mode-0 text now also has current-band
  and fallback-row coverage through `0x1f414` and `0x7810b4 + D2`, and
  synthetic wide/segmented compact text now covers the same fallback
  split for `0x1f0d2`, `0x1f1f0`, and `0x1f264`; host-fetched
  150/100/75-dpi raster streams now carry encoded modes 1/2/3 through
  `0x1ed84` and `0x1ef6a`.
- Determine the remaining live-parser wide/segmented text, raster
  edge-case, and final device-output clipping behavior exactly.
- Identify any banding/compression structures used internally; reproduce
  final pixel result rather than formatter timing.

## Working Rules

- Keep raw ROMs and generated disassembly local-only.
- Track manifests, scripts, and annotated findings.
- When a ROM-derived behavior is implemented in a renderer, add a
  fixture byte stream and expected pixel/hash result.
- Prefer narrow extraction scripts over one-off manual tables so every
  claim can be regenerated from the verified ROM hashes.
