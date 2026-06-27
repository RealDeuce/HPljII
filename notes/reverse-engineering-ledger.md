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

Status: Built-in `HEAD` chain anchored; external cartridge/resource
formats still unavailable

Evidence: firmware checks `0x200000` and `0x400000` for `PROG`, and scans
for `HEAD` records. The verified `IC32,IC15` resource image has `HEAD` at
offset `0x000000`; startup scanner `0x41a` walks the built-in chain through
24 typed records from `0x08004c` through `0x0ae122`, terminates at
`0x0b2f80`, and has modeled boundary behavior for `0x40000` crossings and
`0x000000be` executable records. Candidate scanner `0x1a616` / `0x1a9be`
accepts those same 24 built-in records as twelve class `0` and twelve class
`1` low-window records. Tracked detail lives in
`notes/resource-rom.md`; extending the scanner beyond this verified built-in
window still needs cartridge or external resource images.

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
`Host Byte Fetch And Data-Chain Input`. The alternate `0xa6cc` bridge
from `0xfffe0001`/`0xfffe0003` into the `0x783e54` ring is now
composed with low-water, full-service, status-escape, and `0xa904`
consumer fixture coverage.

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
fields for reset, FF, page-size, orientation, paper-source, and copies,
addressed publication allocation variants for those six streams, addressed
text/rule/raster FF publication, and synthetic mixed reset fixtures,
with the first complete page-image byte-stream contract now documented
under `Mixed Text/Rule/Raster Page Record` for
`! ESC *c12a5b0P ESC *t300R ESC *r0A ESC *b2W c3 3c FF`,
with the shared page-record allocator now composed through one
multi-writer `0x1381c` chunk rollover state,
with the published-record to active-render handoff now pinned through
`0x1eb2a..0x1ed84`,
with the direct text cursor/control family now composed in
`notes/semantic-state-model.md` under `Text Cursor And Direct Controls`,
with the printable source-object and compact bucket producer now composed
under `Text Source Objects And Compact Buckets`,
with pending text span re-arm, watermark update, flush packaging,
portrait segment-list output, and landscape fixed-width output now
composed under `Text Span Flush And Fixed-Width Spans`, including a
parsed CR / `0xf34a` end-to-end span flush to visible page-record output,
and flagged printable `0xd550` -> `0xd824` -> `0xd8fc` low-water span
flush to visible segment-list output,
and unflagged printable `0xd140` -> `0xd3b2` -> `0xd4ac` low-water span
flush to visible segment-list output,
and portrait `0x1354a` split text-span output across adjacent compact
buckets,
and landscape `0x12714` text-span output through nonempty addressed
`0x136d2` fixed-list insertion,
and `0x12714` allocation-failure recovery through `0xff1e` publication
and fresh-root retry,
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
through `0x1299c..0x12b92`; alternate high-start recovery entries are
anchored by fixture `0x1280a VFC alternate high-start recovery entries`
with start line `80`: no-hit recovery through `0x12a02..0x12afc`,
wrapped line-70 bottom recovery through `0x12a7a..0x12afc` and
`0x12afc..0x12b5a`, and selector-zero top-of-form recovery through
`0x12b5e..0x12b92`;
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
render, and with addressed reset, FF, page-size, orientation,
paper-source, and copies allocation variants now proving the same compact
bucket materialization through `0x1387c`/`0x1381c`;
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
downloaded-font control, and macros; [rectangle-graphics.md](rectangle-graphics.md)
documents `ESC *c#A/#B/#H/#V/#G/#P` into rectangle size, area-fill id,
selector mapping, clipping, `0x13386` rule-list queueing, including a
chained `ESC *c12a5b0P` byte-stream fixture and ROM parser dispatch trace
for selector-7 rule creation, modeled `0xa904` ring fetch and `0x1edc6`
rule-list bridge coverage plus `0x1ed84`/`0x1ef6a` render-entry coverage,
selector-7 solid rendering and band-crossing continuation through
`0x1f446` / `0x1f596`, gray selectors `0..6`, HP pattern selectors
`8..13`, sub-byte shifted, band-crossing, and two-band page-assembly
HP-pattern cases rendering through `0x1f446` / `0x1f4e0`, plus a
parser-to-retry boundary for `ESC *c12a5b0P` where the `0x10d22` no-room
path publishes the old root through `0xff1e`, allocates a fresh root
through `0x10084`, and retries the selector-7 rule through `0x13386`;
`generated/analysis/ic30_ic13_font_control_flow.md` decodes
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
zero-parameter publication/default-page branch is now fixture-backed:
`ESC &l0P` follows `0xfa62..0xfaa6` through `0xf34a`, `0xff1e`,
`0x9ac2`, optional paper-source output byte `0x780e8f`, and
`0x9b5e(0x780e26, 1)`, then enters `0xfb4a..0xfc52` to choose default
page code `0x780e97` or fallback `2`, reload `0x782dba` through
`0xf9ac`, and recompute text bottom. The fixture pins fallback code `2`,
extent `3300`, text bottom `3240`, output byte `0x80`, and control word
`1`.

Vertical forms control is now a composed semantic state block in
`notes/semantic-state-model.md`. The canonical table is
`0x782dde..0x782edd`; derived/cache fields include `0x782dc2`,
`0x782dd2`, `0x782ede`, `0x782edf`, and `0x782ee0`; `0x782ee1` is
firmware bookkeeping and `0x78299e` remains parser scratch. The table
writer cluster `0x11f6e -> 0x12cfe`, default builder `0x12b96`, and
consumer `0x1280a` are composed in `notes/vertical-forms-control.md`. The
`0x1280a` forward in-text hit path
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
anchored through `0x1299c..0x12b92`. Alternate high-start entries are
now fixture-covered for start line `80`: empty-table no-hit recovery
through `0x12a02..0x12afc`, wrapped line-70 bottom recovery through
`0x12a7a..0x12afc` and `0x12afc..0x12b5a`, and selector-zero
top-of-form recovery through `0x12b5e..0x12b92`. The remaining VFC
semantic gap is also closed: fixture
`0x12b96 default VFC table channel convention` ties `0x1280a` selector
`n` to bit `n - 1` and names the ROM default table channel rules from
line `0`, text boundary lines, half/quarter/three-quarter text lines,
divisor-pattern lines, and page-last line `0x782ede`.

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
variant; active-pool render-work aliases, copy-window setup, `0x2456`
source selection, `0x22f4` eight-row copy passes, and the
`0x78399e/9f` active-pool status feedback into `0x1db0`/`0x1e44` are
now composed, with `0x1cf8` wrapper dispatch through `0x1e80` and
`0x1ea8` variants also pinned, and `0x1eba4..0x1ecd2` scheduler-loop
render/yield predicates covered; `0x1036`, `0x1064`/`0x108e`,
`0x123a`, and `0x10bc..0x10f2` now pin the wait-object scheduler
handoff and trap-veneer argument shapes, with `0x1144..0x11f8` now
pinning the copied trap handlers' wait-state transitions; tracked note
`notes/downloaded-fonts.md` now composes the combined 2,215-byte
host-fetched font-download printable stream that carries
`ESC *c4660d37e5F`, `ESC )s2193W`, and printable `%` into downloaded
glyph `0x25` segmented page objects before `0x1edc6`, `0x1ed84`, and
`0x1ef6a`; `ESC )s80W` validation no-install evidence now covers
invalid type, first-code overflow, zero line/count, high line/count,
reversed range, high range/count, and invalid class through the parser
restore and `0x16c14` allocation boundary, and the same seven failed
streams plus the short-budget `ESC )s8W` entry-5 failure followed by
printable `!` now preserve the default-font page-record object and rendered
rows; fixture
`descriptor metric fields match across inline and resource contexts` now
pins the legal metric producer forms and the two invalid swapped forms.
Fixture `legal descriptor metric value matrix drives d4ac and d8fc consumers`
now covers small-rounded, clamped-rounded, midpoint-rounded, zero-rounded-offset,
negative-offset, lower-bound, and upper-bound legal metric values. The
negative-offset row accepts descriptor byte `0xfe`, preserves it as copied word
`+0x1a = 0xfffe`, and pins the resulting `d8fc` high-y `-65513` / render
digest `72bfa14c2a84532e2bdf6fb8fddf26ed6904c49dcf4fdcb322592471b5d5b281`.
Fixture `legal descriptor metric boundary values drive d4ac and d8fc consumers`
now covers `d8fc` lower-bound equality, exact page-extent equality, max
positive offset byte `0x7f`, normal rounded input `0x0013` storing copied
`+0x2c = 0x0014`, and rounded input `0x1500` transforming to copied
`+0x2c = 0x0060` before `d4ac` exits beyond page extent; it now also proves
rounded input `0x1508` stores the same `+0x2c = 0x0060`, so the descriptor
transform discards that low byte before the same `d4ac` exit.
Remaining work is additional metric-value combinations within the legal
forms, validation/error page behavior beyond those bounded predicate and
short-budget no-install branches, no-install publication variants for
downloaded-character failures, remaining alternate character-mode/release
variants, full live-parser raster edge cases, and final device-output page
comparison. The status-`2` downloaded-character partial-install branch is now
carried through trailing-FF `0xff1e` publication and published-record
rendering for both linear and split-plane compact objects.

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
copied from page-root `+0x2c`, and the selected font context, span
metrics, and compact glyph byte bridge are documented in
[font-context-metrics.md](font-context-metrics.md); compact text payload
glyph bytes are mapped through `0x782f32` / `0x783032`;
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
through parser handlers and published rows, addressed publication allocation
variants for those six streams, real built-in glyph-resource resolutions,
full decoded mode-1
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
`0x782a72 = 0x00d0c000`, and `0x782a76 = 0x00d0c044`, an addressed
allocator composition fixture where `0x10084` seeds `0x782a72 =
root + 0x20`, seven compact text objects force stream links
`root + 0x20 -> 0x00d05000 -> 0x00d05100`, `0x133aa` and
`0x136d2` add rule/fixed objects at `0x00d0512a` and `0x00d05138`,
and `0x1ef6a` renders all seven compact objects through `0x1effe`, an
active-render scheduler fixture where `0x1eb32..0x1eb50` sets
`0x780ea4 = 1`, clears `0x780ea5`, copies `0x780eaa` to `0x780eae`,
`0x1ecd6..0x1ed0e` switches `0x7820bc` and stores `0x783a18`, and the
selected record reaches the same `0x1ed84`/`0x1ef6a` rows, plus the
same-geometry `0x1ed36..0x1ed6a` branch that carries previous render
base/divisor and writes remainder `3` to destination word `+8`, a pool
cursor fixture where `0x3144..0x3162` initializes `0x780ea6`,
`0x780eaa`, `0x780eae`, `0x780eb2`, and `0x780eb6`,
`0x7f76..0x7f90` selects a candidate from `0x780e6e[]` into
`0x780eaa`/`0x780eb2`, and `0x7722..0x779a` advances or protects the
cursor against `0x780ea6`, a staged active-pool fixture where `0x21b8`
gates `0x1c04`, `0x1c32..0x1c54` marks current `0x780eb2` state `3`,
`0x1fd4..0x2016` shifts `0x780e6e[]`, `0x1eea` releases the staged
record to selectable state `4`, `0x7ec6..0x7f90` promotes it back into
`0x780eaa`, and the selected pointer reaches `0x1eb46`/`0x1ecd6`
render scheduling, an active-pool copy-window fixture where `0x2126`
aliases work record `0x00782128`, `0x1a4c` seeds `0x78398c..0x7839d4`,
`0x2038` computes ready and done paths, `0x2456` produces source pointer
`0x00102000` and then `0x00102800`, and `0x22f4` copies eight
`0x20`-longword rows from `0x00102400` to `0x00ffc000` with destination
stride `0x200`, an active-pool status-feedback fixture where `0x0fa2`
sets `0x78399e` at threshold `0x12`, `0x1db0` consumes it and copies
eight rows from `0x00102000` to `0x00ffc000`, a later `0x0fa2`
escalates pending status into `0x78399f` plus `$a801 = 0xc0`, and
`0x1e44` signals `0x780e2e` before `0x2038` sets `0x780ea5`, a wrapper
dispatch fixture where `0x1cf8` selects pending-status copy plus
attention, timeout, bridge, and wait-loop paths from `0x78399e`,
`0xa680`, `0x780e32`, `0x780e36`, `0x7821f9.2`, and elapsed `0x191`, a
wait-object scheduler fixture where `0x1036` queues `0x780182`,
`0x108e` drains `0x78017e.1`, `0x123a` selects the higher-priority
object, and `0x10c8`/`0x10c4`/`0x10d0`/`0x10d8`/`0x10e0` have their
trap numbers and argument registers pinned, a trap-handler fixture where
copied vector slots 32..39 route traps `#0..#7` to
`0x1144`/`0x1154`/`0x1174`/`0x118a`/`0x11be`/`0x11ca`/`0x11e8`/
`0x11f8` and those handlers wake, block, mark, read, or clear
wait-object states `0`, `2`, `9`, `0xff`, `0x8006`, and `0x8007`, a
render-loop fixture where `0x1eba4` selects cleanup, throttle,
capacity-wait, or `0x1ef6a` render-call advance from work words `+6`,
`+0c`, `+0e`, `+10`, and `+16`, a
mixed
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
an even-span `ESC )s18W` downloaded glyph composition fixture where bucket
`5` contains both the downloaded glyph object
`00 00 00 00 10 03 00 01 29 06 01...` and mode-0 raster object
`00 00 00 00 80 00 00 02 00 00 c3 3c`, the bridged rule list contains
`00 00 00 00 05 17 08 01 00 0c 00 03 00 03`, and `0x1ef6a` dispatches
`0x1f88e`, `0x1effe`/`0x1f0d2`, and `0x1f596` before comparing composed rows,
a parser-driven page-stream variant where fetched bytes `24..54` are
`ESC *c12a3b0P ) ESC *t300R ESC *r0A ESC *b2W c3 3c`, handlers
`0x10e68`/`0x10e22`/`0x10898`/`0xd04a`/`0x10808`/`0x1075a`/`0x11f82` produce
the same bucket-5 glyph/raster chain and bridged rule list before `0x1ef6a`
compares the same rows,
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
and `0x1cf34` sample-byte emission before the post-row recent-context
scan; the committed resource note now documents both internal-font class
passes, with class-zero visible rows `I00..I13`, class-one visible rows
`I00` and `I16..I28`, duplicate Roman-8 substitution rows
`I05`/`I10`/`I20`/`I25`, and the full-loop source-status chain
`0x783f05 = 14` from class-zero, class-one resume through
`0x1c41a..0x1c428`, then `0x783f05 = 29`; the non-internal source-index
fixture also pins source `0` as no-row/status `0x783f02 = 1` and sources
`1`/`2` as single request-`0` `L00`/`R00` rows with
`0x783f03 = 1` / `0x783f04 = 1`; the source-heading page-record fixture then
queues source `0` as a heading-only page-record digest
`89fb4143a293f80bb8c07bab86d5c94940ba73039f2bd9ba1e3de0c2c6c4fb4c` and
source `1`/`2` single-row page-record digests
`cc583ac71b083d3cf241a1a72ff6345e22d585a9eef1a0ba850427b6d43e2aba` /
`51dade4f3a0af13cb533c9f62c5ea955a63f02046622e39a00b4ac8b072f63d6` and
`eaf10ca6b5b5716170b313ce542df82a6974c1ac22ee0e87308dead7be22c6a1` /
`3d23d5c6c5320d406d1db34523d3ad01c819d4e938e3dee4fa0a5d20747ed152`; the
report also
pins sample-page cursor and row sequencing through `0x1c916`,
`0x1ca2c`, `0x1cabe`, `0x1cf34`, and `0x1d050`, including page-limit
checks against `0x782db6`, source/metric text emission through `0xd04a`,
and the `0x31` horizontal-unit gap between the two ROM sample runs; the
page-limit branch fixture now pins `0x1ca2c` heading preflight at limits
`45`/`95` and the `0x1d050` row-continuation call chain at limits
`100`/`1010`, including `0x1c9f6`,
`0x1ca2c(source=3,row=1,current=0x4008004c,selected=0x44080418)`, and the
second `0x1cfe4` advance; fixture
`font sample alternate row fit gate follows 0x1d868` now pins the
selected/alternate gate at `0x1d868..0x1d95c`: clear `0x783132` skips
`0x1d8ba`, while set `0x783132` projects first-`COURIER` y
`0x00900000 -> 0x00ce0000`, compares bottom `219` against page limits `300`
and `219`, and returns D7 `1` only at equality/overrun; fixture
`font sample multi-probe preflight follows 0x1dcf2` now pins the later
`0x1d964` current/alternate preflight through shared calculator
`0x1dc38`: first `COURIER` projections `0x00900000 -> 0x00ce0000 ->
0x010c0000` fit under limit `300`, limit `250` overflows the second probe and
returns D7 `1` at `0x1de24` after reset y `0x01820000`, and a high-y
limit-`600` case proves the reset mode-1/mode-0 fit exit at `0x1de16`; the
row helper listing now names `0x1d198` font-name/style formatting,
`0x1d6ea` capped string emission, `0x1d71e` fixed-name sanitization,
`0x1d76c` orientation-command synthesis, and `0x1d964` / `0x1dcf2`
page-fit preflight for current and alternate sample rows; `0x1d198` local
tables now decode symbol/variant names including `UPC/EAN`,
`CODE 3 OF 9`, `OCR A/B`, and `LINE DRAW`, plus family names
`PRESTIGE`, `GOTHIC`, `TMS RMN`, `HELV`, `COURIER`, and
`LINE PRINTER`;
`tools/render_fixture_harness.py` now carries the first `COURIER` row
fields and sample run 1 through the `0x1cf34` middle transition into
sample run 2. Fixture `font sample Courier row fields carry run 1 through
0x1d050 to run 2` cites `0xf06e` resetting `0x782c8a` from
`0x08ac0000` to `0x00000000`, `0x1d050` reading first `COURIER` record
`+0x16 = 40` and `+0x18 = 13` through `0x1c6a4` / `0x1c6da`, `0x1cfe4`
advancing y by `744` subunits from `0x00200000` to `0x005e0000`, and
`0x1d152(0x31)` starting run 2 at x `0x05be0000`. The carried page-record
state now ends at cursor `0x08ac0000,0x005e0000` with buckets
`[-1, 0, 3, 4]`. Fixture `font sample carried run 2 buckets render through
0x1ed84 and 0x1ef6a` then renders buckets `3` and `4` through the band
entry path with wide stride `0x0180`, pinning bucket-3 current/fallback
hashes
`823d26ff1ebdb3068224faa8dfc0679eef91cd959f1dd370d13f018eb21ce6a4` /
`973d6e26612036125768dcc697900e150e57899007ff846da320c457913e6d51`
and bucket-4 current/fallback hashes
`5e71581663bd2a7c363a866b8bea232fb69f0524e2046da47fd54375cb800796` /
`06dc84fbb9421397716b0bfccb9b807942ba9a29671436503c91813626d87d5f`;
fixture `font sample source heading carries default plus first two Courier
rows` now adds the actual preceding source-heading edge. Disassembly
`0x1c386..0x1c38e` passes source group `D4`, current context `A4`, zero row
word, and zero alternate context into `0x1ca2c`; `0x1ca86..0x1caa6` flushes
pending text, loads source table pointer `0x1c180` from `0x1c170 + 3*4`,
emits `INTERNAL FONTS` through `0x1d12e`, calls `0x12714`, advances through
`0x1cfb4`, and stores row-height cache `0x783f06`. The fixture pins
request-index `0` through `0x1b8ea` fast probe to slot `0x782354` / record
`0x00004c` / word `0x0115`; `0x1d198` then uses family table `0x1c11a` to
format `LINE PRINTER`, so the row-0 field bytes are
`I00LINE PRINTER10128U`. The same fixture assigns context slots
`[0x4008004c, 0x44080418, 0x44080868]`, advances rows 1 and 2 through
`0x1d050`, and carries buckets `[0, 2, 3, 4, 6, 7, 10, 11, 13, 14, 15, 18,
21, 22, 23]`. The widened `0x1e8e6` disassembly window now
also shows `0x1e9a0` saving `0x78289f` / `0x7821a0`, forcing symbol
`0x0115`, calling `0x1ae7e`, copying the selected candidate into
`0x782ee6`, rebuilding via `0x14c64`, and installing the current page-root
font context through `0xc428`;
fixture `font sample resolver carries first two Courier rows` now adds the
next related resolver and row-transition edge. `0x1c398..0x1c3a0` calls
`0x1b50e` for request indexes `1` and `2`; the mode-3 scan suppresses
current Roman-8 slot `0x782354` / record `0x00004c`, selects slot
`0x782358` / record `0x000418` / word `0x0155` for the first named
`COURIER` row, then selects slot `0x78235c` / record `0x000868` / word
`0x0175` for the second named row. `0x1c470..0x1c488` then crosses the
shared `0xf06e` / `0x1d050` no-continuation path: x resets to
`0x00000000`, `0x1cfe4` advances y from `0x00900000` to `0x00ce0000`,
page-record context slots become `[0x44080418, 0x44080868]`, and second
row bytes `I02COURIER101211U` plus both sample runs extend the carried
bucket set to `[0, 2, 3, 6, 7, 8, 10, 11, 14, 15, 16, 24, 32, 40, 48,
56, 64]`;
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
`tools/render_fixture_harness.py` now models the `0x1cabe` row-field
cluster for first `COURIER` and first `LINE_PRINTER`: `0x1cb26..0x1cb66`
emits internal-source prefixes `I01` and `I07`, `0x1d198` / `0x1d5fa`
emits the built-in names, `0x1cc6e` formats pitch/height as `10`/`12`
and `16.6`/`8.5` with `0xd0f0` fixed-space accounting, and `0x1cd78`
formats symbol word `0x0155` as `10U`; the first `COURIER` row-field
fixture now also queues those bytes through `0x1393a` / `0xd824` /
`0x12f2e` into compact bucket `0` as object counts `[7, 10]`, keeps the
two symbol-column `0xd0f0` fixed spaces as cursor-only events, and
renders rows with hash
`4756fe985af471915c3de75c4637c09e51c28a80af75989a1125f6d9cbf2347c`;
the carried-state fixture `font sample Courier row fields and run 1 share
page-record state` appends the `0x1c1cf` sample run 1 byte stream to that
same record, producing buckets `[-1, 0]`, final cursor `0x08ac0000`, and
render hashes
`78d11b068621d9a47fcce073c9b5d1a591bdfc9368bf5d32f6e81186911d4428`
/ `975779b94eb6e9eefaaa0134e7ef5915d5471e16b6568315f612def3cb440949`;
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
selected-longword context selection; fixture `parsed primary built-in font
selection feeds visible page-record rows` now composes the parsed primary
selection stream `ESC (s0p10h12v0s0b3T!!` into visible output by taking the
pinned `0x13eb8` selected context `0xc008004c`, HMI `30`, and rebuilt primary
map `0x782f32`, then routing the following printable bytes through `0xd04a`
into compact object prefix `00 00 00 00 00 00 00 02 00 6a 00 00 68 02`,
`0x1edc6` context slot `0xc008004c`, and compact helper `0x1fe76` Courier
glyph rows; fixture
`live primary current-font RAM install feeds SI page-record rows` pins the
primary existing-root handoff by seeding `0x782ee6 = 0xc008004c` and
`0x782ef6 = 0xc00ae122`, routing SI through `0xc68a`, `0xc428(0)`, and
`0xc4fc`, installing page-root context slot `0`, and rendering the following
`!!` from source context `0xc008004c` / source slot `0`; fixture
`parsed secondary built-in font selection feeds visible SO page-record rows`
mirrors that boundary for `ESC )s0p16h8v0s0b0T SO !!`, selected context
`0xc00ae122`, secondary map `0x783032`, SO handler `0xc6b8`, compact object
prefix `00 00 00 00 00 01 00 02 00 c9 00 00 cb 01`, `0x1edc6` context slots
`(0xc008004c, 0xc00ae122)`, and compact helper `0x207ac` secondary Line
Printer rows; fixture
`primary symbol miss falls back before visible page-record rows` extends the
primary boundary through `ESC (1234U ESC (s0p10h12v0s0b3T!!`, where requested
word `0x9a55` misses in `0x156de`, fallback table word `0x0115` survives,
survivor slots `0x782354`, `0x782364`, and `0x782374` remain active, and the
final selected context, primary map, object prefix, render-context slot, and
rows match the primary case; fixture
`secondary symbol miss falls back before visible SO page-record rows` now
extends that boundary through `ESC )1234U ESC )s0p16h8v0s0b0T SO !!`, where
requested word `0x9a55` misses in `0x156de`, fallback table word `0x000e`
survives, and the final selected context, secondary map, object prefix,
render-context slots, and rows match the secondary SO case; fixture
`live secondary current-font RAM install feeds SO page-record rows` pins the
secondary existing-root handoff by seeding `0x782ee6 = 0xc008004c` and
`0x782ef6 = 0xc00ae122`, routing SO through `0xc6b8`, `0xc428(1)`, and
`0xc4fc`, installing page-root context slot `1`, and rendering the following
`!!` from source context `0xc00ae122` / source slot `1`; fixtures
`parsed primary selection current-font RAM feeds SI visible rows` and
`parsed secondary selection current-font RAM feeds SO visible rows` compose
the host-fetched selection streams `ESC (s0p10h12v0s0b3T SI !!` and
`ESC )s0p16h8v0s0b0T SO !!` into those RAM handoff paths, preserving
selection handlers, `0x144d2` context updates, `0xc428` / `0xc4fc` install
events, page-root slots, source contexts, compact object prefixes, and rows
matching the pinned parsed visible fixtures

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
- Broaden the direct-control and printable stream fixtures into fuller
  live parser/register traces, the transparent secondary segment-57 bitmap
  physical/resource-window source interpretation beyond the page-record and
  render-prefix boundary pinned by fixtures `transparent secondary high-control
  byte enters segmented page-record path` and `transparent secondary segmented
  render prefix exposes source boundary`, and dense parser-allocated
  page-object fixtures. The transparent segment-57 compact path is now narrowed
  by disassembly to `0x1f354` accepting glyph `0x5f` table offset zero as entry
  `0x02e122`, then `0x1f1f0` reading firmware range `0x0bfe22..0x0c0321`;
  the unknown is what hardware maps after the verified resource-pair byte
  range ends at `0x0bffff`.
  Command-family state is composed in `Text Cursor And Direct Controls`, and
  the
  printable source-object fields are composed in `Text Source Objects And
  Compact Buckets`.
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
- Cursor-stack push/pop, bounds, and restored-origin text output are now
  composed in `Text Cursor And Direct Controls`; remaining print
  environment work is reset/default provenance and primary/secondary font
  fallback interactions.

## Fonts and Glyph Imaging

Expected resource ROM contents:

- Built-in bitmap font rasters.
- Metrics, pitches, baselines, cell sizes, offsets, style metadata.
- Symbol-set maps and internal character conversions.

ROM work needed:

- Extend the pinned visible `0xc580` branch outcomes into fuller
  upstream `0x1be22` parser-state coverage around the now-pinned
  `0x17708` success paths, turn the parser-derived `0x156de` primary and
  secondary fallback fixtures into single uninterrupted parser-to-page
  CPU-state traces, add other fallback/error font-selection visible-output
  streams beyond the now-pinned primary `ESC (s0p10h12v0s0b3T!!`, secondary
  `ESC )s0p16h8v0s0b0T SO !!`, primary fallback
  `ESC (1234U ESC (s0p10h12v0s0b3T!!`, secondary fallback
  `ESC )1234U ESC )s0p16h8v0s0b0T SO !!`, primary
  `ESC (s0p10h12v0s0b3T SI !!`, and secondary
  `ESC )s0p16h8v0s0b0T SO !!` composed handoff cases, and extend `0x13eb8`
  if later inline/downloaded or error-return branches surface.
- Extend the modeled `HEAD` record scanner beyond the verified built-in
  resource window if cartridge or external resource images become
  available.
- Finish physical/manual naming of the built-in record fields whose ROM roles
  are already pinned by the repeated `COURIER` and `LINE_PRINTER` fixtures.
  Record `+0x24` is the `0xc428` / `0x10550` HMI/default-advance source,
  glyph-entry `+0/+2` placement offsets are pinned through the `0xd824` path,
  record `+0x28/+0x2a` is consumed by `0x1519a` as decoded-height inputs
  before `0x13bca`, and record `+0x2f..+0x31` is consumed by `0x1428c` as
  same-class chooser tie-breakers after `0x14398` / `0x13c06`. What remains
  is the HP/manual-facing baseline/cell terminology and comparison against a
  known printed font/self-test sample.
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
- Model the font-printout loop's emitted page objects from the ROM sample
  byte runs. The internal-font source group is decoded for both class passes
  and documented in `notes/resource-rom.md`: request index `0` fast-probes or
  uses the `0x1e9a0` seed, `0x1b50e` scans row ordinals, `0x1c746`
  normalizes selected addresses to candidate longwords, `0x1c710` rejects the
  opposite class, class-zero request `14` writes `0x783f05 = 14`, class-one
  reads that byte through `0x1c41a..0x1c428`, request `29` terminates on
  resolver miss for class one, and
  rows `I05`/`I10`/`I20`/`I25` prove duplicate Roman-8 substitutions are
  visible before the post-row `0x1c540..0x1c5c6` recent-list scan. The final
  class-one status write is `0x783f05 = 29` through `0x1c5d6..0x1c5de`.
  Sources `0..2` are now fixture-backed too: source `0` mode `0` emits no
  rows and writes `0x783f02 = 1`, while source `1` / `2` modes `1` / `2` emit
  only the request-`0` `L00` / `R00` rows in each class pass and write
  `0x783f03 = 1` / `0x783f04 = 1`.
  The source-heading page-record checkpoint now carries `"PERMANENT" SOFT
  FONTS`, `LEFT FONT CARTRIDGE`, and `RIGHT FONT CARTRIDGE` through `0x1ca2c`
  label printing and the row producer for the `L00` / `R00` cases, with
  aggregate object digests documented in `notes/resource-rom.md`.
  Fixture `font sample full printout source placement follows firmware order`
  now composes the firmware-order source/class segments
  `(0,0)..(0,3),(1,0)..(1,3)` after each pass's `0x1d76c` / `0x10084` /
  `0x1e9a0` / `0x1c9b8` / `0x1c916` / `0x1cfb4` setup sequence: row counts
  `[0,1,1,14,0,1,1,14]`, bucket counts `[3,13,13,142,3,12,12,122]`,
  context-slot counts `[1,1,1,12,1,1,1,12]`, status writes
  `0x783f02=1`, `0x783f03=1`, `0x783f04=1`, `0x783f05=14`, then
  `0x783f02=1`, `0x783f03=1`, `0x783f04=1`, `0x783f05=29`, and aggregate
  segment digest
  `f4105538bd1506731f04810ed2f50cce23815751c4f979ed6f60efab4cde08c7`.
  Fixture `font sample run 1 full row spans compact buckets` carries byte stream
  ``ABCDEfghij#$@[\\]^`{|}~123`` through context `0x44080418`, compact
  buckets `-1` and `0`, `0x1ed84` / `0x1ef6a`, and row hashes
  `b6a0061f7de34c0fa1a0586263f3f167c84d95219e05437e74a286356409af37`
  and
  `d7dfb89c8cff5e309b95aac43cd64e0f74f17db1dd9118253544343f17b4c1ce`.
  Fixture `font sample run 2 full row spans compact buckets` carries
  bytes from table `0x1c1e9` through the same context, compact buckets
  `-1` and `0`, `0x1ed84` / `0x1ef6a`, and row hashes
  `c77bca7364adbda480c5a31fa4be469175c031bd5f14fc4a54a2e6fb09174be5`
  and
  `b10556bfb02fbb6a2ffec2a82add396619bae3ace0ebab657113f4d3648c41b5`.
  The source-heading composition fixtures now carry `INTERNAL FONTS` through
  all 14 visible class-zero rows and all 14 visible class-one rows in separate
  page-record states. The page-limit continuation checkpoint now covers
  `0x1ca2c` heading preflight, `0x1d050` row-continuation call targets, and
  the `0x1d868` selected/alternate fit gate, plus the `0x1d964` /
  `0x1dcf2..0x1de2c` multi-probe preflight. Fixture `font sample full printout
  rows reuse ROM sample byte runs` now proves all 32 composed rows consume the
  ROM sample tables at `0x1c1cf` and `0x1c1e9`, with correlation digest
  `4f664dc44f9ad98cbe25d4bdead651a2902bec1f90367c650bb2d1352d6f3e8a`.
  Fixture `font sample full printout segments render through 0x1ed84 and
  0x1ef6a` now carries all eight source/class page-record segments through the
  bridge and band renderer, with aggregate rendered-surface digest
  `5e5e735b4fb2a2a4dff4794099a02eaf23fa2dd3e469df8d053db88a321ea6f2`. The
  next boundary is physical baseline/cell comparison against a known
  printed/self-test sample.
- Fixture `live parser symbol-set streams select non-Roman built-ins` now
  broadens the named `0N` / `10U` / `11U` samples from static map evidence
  into primary parser/font-selection evidence. Streams `ESC (0N`,
  `ESC (10U`, and `ESC (11U` route through handlers `0x11eb6`, `0x1201e`,
  and `0x120be`, write requested words `0x000e`, `0x0155`, and `0x0175`,
  select records `0x000cb8`, `0x000418`, and `0x000868`, and rebuild map
  `0x782f32` through the `selected-symbol-not-roman8` path. Fixture
  `non-Roman symbol streams select visible built-ins` now carries the primary
  and secondary `0N` / `10U` / `11U` byte streams through matching
  font-selection commands, SO for secondary, compact text objects, bridge
  context slots, and rendered-row digests. The remaining edge is broader
  command combinations only where they expose different state boundaries.
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
  `0xd824` / `0xd3b2` / `0xd550` / `0x12f2e` source-object and compact
  bucket fixtures into full live parser/register runs with real
  font-download parser records, real HMI/font metrics, glyph indices,
  and parser-produced page objects, building on the current host-fetched
  plain `!!`, mixed `ESC &k1G!\r!`,
  LF-positioned `ESC &k2G!\n!`, HT/BS-positioned `ESC &k0G HT BS !`,
  left/right-margin-positioned `ESC &a1L!` / `ESC &a1M!`,
  lowercase-chained margin-positioned `ESC &a6l9M!`, horizontal-column,
  horizontal-decipoint, vertical-row, vertical-decipoint, and
  lowercase-chained cursor-positioned `ESC &a2C!` / `ESC &a72H!` /
  `ESC &a1R!` / `ESC &a72V!` / `ESC &a2c+1R!`, top-margin-positioned
  `ESC &l3E!`, and cursor-stack `ESC &f0S ESC &a2C ESC &f1S!`
  parser-to-page-record boundaries now composed in
  `Text Cursor And Direct Controls` and `Text Source Objects And Compact
  Buckets`.
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
  moving back to parser-produced page-object rendering; no macro
  replay/font-context middle edge remains in that checkpoint. The full
  CPU-state bridge from pinned `0xe65c` branch effects into `0x13eb8`,
  `0x144d2`, `0x14c64`, and `0xc428` is now composed, and
  `0xe860..0xe898` now names inline/downloaded class byte `+0x16` versus
  offset-table/built-in class byte `+0x20`. Heap initialization
  `0x164a..0x170a` is now composed with startup helper `0x0b18`,
  allocator entries `0x170c`/`0x1710`, and free entry `0x18b4`. The
  `0xe5e2` layout/VFC/static-font refresh and the eight-record macro
  context stack are now composed with `0xe4f4` production and
  `0xe35a..0xe3e8` flat return semantics. The modeled
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
- Continue the active-render scheduler from the remaining physical
  feedback and pacing edges: `$8000.4` selection at `0x0f84..0x0f8e`
  and `0x1020..0x102e`, physical meaning and timing for `$a601 = 0xfd`,
  `$a801`, `$aa01`, `0xfffe0001`, and `0xfffe0003`, and the timing
  relation between those MMIO/helper events and the now-modeled
  wait-object states behind traps `#0..#7`. The software-visible
  `0xa620`/`0xa638`/`0xa650`/`0xa668`/`0xa680` `$a801` shadow helper
  effects and `0xa6cc` ring/status bridge effects are now fixture
  covered and composed into the semantic model.
  Candidate-slot insertion, active-pool staging, pool-cursor alias
  movement, same-geometry work-record reuse, copy-window setup, `0x2456`
  source selection, `0x22f4` row-copy semantics, `0x78399e/9f` status
  feedback, `0x1036`/`0x108e`/`0x123a` wait-object handoff, `0x1cf8`
  wrapper predicate selection, `0x1144..0x11f8` trap-handler wait-state
  transitions, and `0x1eba4..0x1ecd2` render-loop predicate selection
  are now fixture-covered.
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
