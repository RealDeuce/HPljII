# PCL Parser Firmware Notes

Sources: `generated/disasm/ic30_ic13_host_byte_fetch_00a904.lst`;
`generated/disasm/ic30_ic13_main_parser_loop_011774.lst`;
`generated/disasm/ic30_ic13_pcl_escape_parser_00da9a.lst`;
`generated/disasm/ic30_ic13_macro_record_chain_helpers_00dfba.lst`;
`generated/disasm/ic30_ic13_macro_environment_snapshot_helpers_00e65c.lst`;
`generated/disasm/ic30_ic13_tokenizer_stateful_helpers_011ba6.lst`;
`generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst`;
`generated/disasm/ic30_ic13_esc_e_reset_00cc52.lst`;
`generated/disasm/ic30_ic13_esc_e_metric_refresh_00cbd4.lst`;
`generated/disasm/ic30_ic13_esc_e_environment_reset_00cda2.lst`;
`generated/disasm/ic30_ic13_esc_e_parser_state_reset_00e146.lst`;
`generated/disasm/ic30_ic13_control_code_handlers_00f02c.lst`;
`generated/analysis/ic30_ic13_host_byte_fetch_flow.md`;
`generated/analysis/ic30_ic13_direct_control_code_flow.md`;
`generated/analysis/ic30_ic13_esc_e_reset_flow.md`;
`generated/analysis/ic30_ic13_parser_dispatch_tables.md`;
`generated/analysis/ic30_ic13_tokenizer_macro_callers.md`;
`generated/analysis/ic30_ic13_parser_xrefs.md`;
`generated/analysis/ic30_ic13_cmpi_byte_candidates.md`.

These are current anchors for the path from host bytes into PCL command
records. Names are provisional until caller/callee cross-references are
broader.

## Host Byte Fetch Anchor

See [host-byte-fetch.md](host-byte-fetch.md) for the tracked explanation
of routine `0x0000a904`.

See [pcl-parser-core.md](pcl-parser-core.md) for the tracked explanation
of shared parser routines `0xda9a`, `0xdaf0`, `0xdb74`, `0x11774`,
`0x121cc`, and `0x12218`. The generated files listed above are evidence
inputs, not the documentation deliverable.

Summary: `0xa904` returns the next normalized input byte in `D7`, or
`D7 = -1` for the immediate no-byte/error branch where `0x780e66` and
`0x780e3b` are both set. Before live hardware input it checks service
state, two LIFO-like sources, active data-chain replay, and a ring
buffer. Direct mode `0x780e40 == 1` polls short MMIO registers and
toggles `0xa601` / `0xaa01`; other nonzero modes poll
`0xfffee005` / `0xfffee001` and update shadow `0x7828fb` through
`0xfffee009`.

Important parser consequence: `0xa904` itself returns bytes. It does not
globally interpret `0x1a 0x58`. Parser, text, raster, and font payload
readers each apply their own local handling of that pair, so reproduction
must model the consumer family as well as the byte-source order.

## ESC Byte Handling

Routine `0x0000da9a` calls the byte fetch routine at `0xa904` and
returns the next byte in `D7`, with special handling for escape-like
sequences:

- Compares fetched byte to `0x1b` (`ESC`).
- If the next byte after `ESC` is not `0x3f` (`?`), it pushes/logs that
  byte through `0x9ec0` and returns `D7 = 0x1b`.
- If it sees `ESC ? 0x11`, it skips that sequence and resumes fetching.

Routine `0x0000dace` recognizes `0x1a 0x58` and calls `0xd99a`. This may
be host-control or job-control behavior, not enough is known yet to name
it.

## Escape Sequence Tokenizer

Routine `0x0000daf0` builds escape-command records using:

- byte source function pointer `A3 = 0x0000da9a`;
- record cursor/root pointer at `0x78299e`;
- scratch text/parameter buffer at `0x782a42`;
- six-byte records advanced by `+6` in the tokenizer phase.

Observed behavior:

- Parses bytes in the PCL parameter/intermediate range `0x20..0x3f`.
- Handles `<...>` bracketed spans specially in helper `0x0000db46`.
- Skips leading spaces.
- Accepts optional `+` or `-`.
- Parses up to six decimal integer digits into word field `record+2`.
- Parses an optional fractional part after `.` with up to four digits
  into word field `record+4`.
- Stores the terminating byte at `record+1`.
- Treats `:` and `;` as command-combining continuation markers by
  returning `D7 = 0`.

This matches PCL escape syntax closely enough to treat `0xdaf0`/`0xdb74`
as the first confirmed PCL tokenizer anchor.
`tools/render_fixture_harness.py` now pins six-byte records for
`300r150R`, signed fractional values with four stored fractional digits,
semicolon continuation returning `D7 = 0`, `0x121cc`/`0x12218` delayed
payload snapshot/restore for a raster `ESC *b4W` record, and the
alternate/data-mode `0x1228a`/`0x12358` byte-count consumers including
`0xdace` handling of payload control `1a 58`. Raster parser coverage now
also ties the `ESC *t300R` / `ESC *r0A` / `ESC *b4W` dispatch/restore
path to the modeled `0x105d0` capped-transfer, inclusive page-extent
queue-and-advance, beyond-extent drain/no-advance, and negative-row
drain-with-advance gates, and proves the same `0xdace` normalization
applies before raster bytes are queued as pixels. Separate traces now
show active `ESC *t75R` still dispatches to `0x10808` without changing
current raster mode/scale, while `ESC *rB` dispatches to handler
`0x107fa`, clears active state, and lets a following `ESC *t150R` update
resolution.

## Main Parser Loop

Routine `0x00011774` is the current main parser loop anchor. It
initializes:

- `0x78299a` to handler `0x00011b8e`;
- `0x78299e` to tokenizer record cursor `0x7829a2`;
- `0x782a26` to `0x782a2a`;
- `0x782a3e` to text/parameter scratch buffer `0x782a42`;
- local text accumulation region `0x783196..0x783199`.

The loop repeatedly calls `0x0000da9a`, keeps the fetched byte in `D5`,
and dispatches through a mode-indexed six-byte table:

```text
byte_to_match, next_mode, handler_long
```

Normal parser pointer table: `0x000112a4`. Alternate/data parser pointer
table: `0x000116f6`.

Current parser mode is stored at `0x782999`. If `0x782c18` is clear, the
normal table is used. If `0x782c18` is set, the alternate/data table is
used; that table preserves state transitions but suppresses many command
handlers, consistent with a data collection or macro/download mode. A
macro-definition fixture now proves this split for
`ESC &f123Y ESC &f0X ! CR ESC &f1X`: after selector `0` sets alternate
mode, payload bytes `21 0d` are stored without alternate-table handlers,
normal CR's `0xf02c` handler is suppressed, and the stop command still
walks alternate table `0x116f6` through `ESC &f1X` to `0xdd08`. Delayed
payload restore in this mode routes through `0x12358`; the wrapper path
`0x1228a` consumes the absolute parsed count without echo, while the
direct `0x12358` path consumes only positive counts and echoes
normalized bytes through `0xe002`.

## Direct Control Codes

Normal mode 0 has these direct control-code entries:

| Byte | Meaning | Handler |
| --- | --- | --- |
| `0x1b` | `ESC` | next mode 1, setup handler `0x011eb6` |
| `0x1a` | control-Z host control | next mode 2, setup handler `0x011ea4` |
| `0x0f` | SI | `0x00c68a` |
| `0x0e` | SO | `0x00c6b8` |
| `0x0d` | CR | `0x00f02c` |
| `0x0c` | FF | `0x00f0f0` |
| `0x0b` | VT | no handler in table |
| `0x0a` | LF | `0x00f08c` |
| `0x09` | HT | `0x00f1cc` |
| `0x08` | BS | `0x00f2a8` |
| `0x07` | BEL | no handler in table |
| `0x00` | NUL | no handler in table |

`generated/analysis/ic30_ic13_direct_control_code_flow.md` now traces
these handlers into cursor/page-visible side effects. The
line-termination command `ESC &k#G` writes bit patterns to `0x78318f`:
`0` stores `0x00`, `1` stores `0x80`, `2` stores `0x60`, and `3` stores
`0xe0`. CR tests bit 7 to optionally also advance vertically, LF tests
bit 6 to optionally also reset horizontally, and FF tests bit 5 to
optionally also reset horizontally before page finalization.

The CR/LF/FF/HT/BS handlers update state around horizontal cursor
`0x782c8a`, vertical cursor `0x782c8e`, `0x782dd6`, `0x782dda`,
`0x78315c`, `0x783160`, and `0x78318f`, with helper calls into the
coordinate arithmetic block around `0x104d8..0x10518`. They can also
flush text spans through `0x12714` / `0x126e2`, ensure/finalize page
roots through `0x10084` / `0xff1e`, and update active font context spans
through `0xd4ac` / `0xd8fc`. Raster start now confirms the same names:
portrait `ESC *r1A` seeds from `0x782c8a`, landscape `ESC *r1A` seeds
from `0x782c8e`, and `ESC *r0A` clears the raster origin.

`ESC &f#S` reaches handler `0xf75e`, which treats the absolute parsed
parameter as a selector. Selector `0` pushes `0x782c8a` plus
`0x782c8e + 0x782dbe` as an 8-byte entry on the cursor stack at
`0x782c96..0x782d36`; selector `1` pops an entry, restores horizontal
position clamped to `0x782db8 - 1/12`, restores vertical position after
subtracting `0x782dbe` and clamping to `0x782dc6 - 1/12`, clears
pending/right-limit flags, and flushes pending spans when `0x783184` is
set.

`ESC &l#C/#D/#E/#F/#L/#P` are now traced as parser-produced vertical layout
commands. `ESC &l#D` accepts only the ROM LPI set and writes line
advance `0x783160`; `ESC &l#C` converts 1/48-inch VMI units into the
same line-advance word. `ESC &l#E` writes top offset `0x782dce` from
VMI-scaled lines minus vertical offset source `0x782dbe`, and `ESC &l#F`
writes text-length bottom `0x782dd2`. These paths reject out-of-page
values, refresh pending vertical cursor `0x782c8e` as
`0x782dce + VMI * 18 / 25` when text is pending, and are pinned from the
chained byte stream `ESC &l8c6d3e2F` through handlers `0xcb00`,
`0xc992`, `0xece2`, and `0xea9e`. `ESC &l#L` reaches handler `0xee64`;
selector `0` clears perforation-skip byte `0x783191`, selector `1` sets
it, and other selectors leave it unchanged. `ESC &l#P` reaches handler
`0xf9e8`, converts VMI lines to page extent `0x782dba`, chooses the
internal page code through the orientation thresholds, and refreshes the
following printable cursor before normal `0xd04a` text queueing.

`ESC &a#L/#M` are now traced as parser-produced margin commands.
`ESC &a#L` converts the absolute parsed column count through current HMI
`0x78315c`, rejects values beyond `0x782dda - HMI`, writes left margin
`0x782dd6`, and can move cursor `0x782c8a` with pending-span flush.
`ESC &a#M` converts `abs(parameter) + 1` columns through HMI, rejects
values before `0x782dd6 + HMI`, clamps beyond page width `0x782db8`,
writes right margin `0x782dda`, and can move the cursor left while
setting right-limit latch `0x782a57`.

`ESC &a#C/#H/#R/#V` are now traced as parser-produced cursor-positioning
commands. `ESC &a#C` converts the parsed decimal parameter through
current HMI `0x78315c`; `ESC &a#H` converts decipoints as five packed
subunits per decipoint; both commit through horizontal helper `0xf4ca`
using parsed-record bit 0 as the relative flag. `ESC &a#R` converts rows
through current VMI `0x783160`, adding fractional `0.7200` before VMI
scaling for absolute row moves, then commits through vertical helper
`0xf6e2`; `ESC &a#V` uses the same five-subunit decipoint conversion and
vertical helper. The vertical path uses top offset `0x782dce`, lower
bound `0x782dca`, and upper bound `0x782dc6`.

`ESC &k#H` is now traced as the parser-produced horizontal motion index
command. Handler `0xca8c` rewinds the six-byte parsed record, takes the
absolute integer/fraction pair, rejects integer values above `0x348`,
scales accepted values by 30 packed subunits per HMI unit, and stores
the result in HMI word `0x78315c`.

`tools/render_fixture_harness.py` now has synthetic packed-state
fixtures for the `ESC &k#G` bit map plus CR/LF/FF/HT/BS cursor/page
effects, `ESC &k#H` HMI conversion/bounds behavior, `ESC &f#S`
cursor-stack push/pop behavior, `ESC &l#C/#D/#E/#F`
vertical layout conversion/reject/default behavior, `ESC &a#L/#M` margin
conversion/reject/cursor-move behavior, and `ESC &a#C/#H/#R/#V`
cursor-position conversion, relative, and clamp behavior. It also has
narrow byte-stream fixtures for `ESC &k1G` followed by CR, `ESC &k2G`
followed by LF, `ESC &k2G` followed by FF, `ESC &k3G` followed by
CR/LF/FF, `ESC &k0G` followed by HT/BS, `ESC &f0S`/`ESC &f1S` through
handler `0xf75e`, chained `ESC &l8c6d3e2F` through handlers `0xcb00`,
`0xc992`, `0xece2`, and `0xea9e`, chained `ESC &a3.5c+1R` through
handlers `0xf39e` and `0xf560`, and chained `ESC &a6l9M` through
handlers `0xeb58` and `0xec0c`; the FF case proves the mode-2 CR-style
horizontal reset, page-root creation/finalization, span flush, and
`0xff` page-eject pending state from actual command/control bytes, while
the mode-3 stream proves CR/LF/FF consume all three stored bits in
sequence. A mixed stream fixture now drives `ESC &k1G`, printable `!`,
CR, printable `!` through one modeled pass, proving that the stored
line-termination mode applies before the second printable byte is
positioned; a page-record variant queues the same printable bytes
through `0x1387c` and bridges them through `0x1edc6`. `ESC &k2G!\n!` now
has the same parser-to-page-record boundary: `0xedf8` sets
line-termination mode `0x60`, LF reaches `0xf08c`, applies CR+LF, and
the second printable `0xd04a` queues at compact coord `0x3b00`.
`ESC &k0G HT BS !` also has that boundary: `0xedf8` clears
line-termination mode, HT reaches `0xf1cc`, BS reaches `0xf2a8`, and
printable `0xd04a` queues at compact coord `0x0a01` / pixel x `26`. A
cursor-stack page-record fixture now drives
`ESC &f0S ESC &a2C ESC &f1S!`, proving the `0xf75e` push/pop pair
brackets cursor-position handler `0xf39e` and restores the original
cursor before printable `0xd04a` queues at compact coord `0x0001`. A
second mixed fixture drives printable `!` followed by `ESC E`, proving
reset publication/clear state after a queued text object in the same
byte-stream model; its page-record variant queues the glyph through
`0x1387c` and bridges it through `0x1edc6`. The harness now also traces
`!\x1bE`, `ESC &k2G!\f`, `!\x1b&l1A`, `!\x1b&l1O`, `!\x1b&l2H`, and
`!\x1b&l2X\f` through `0x11774`, pinning printable `!` to the mode-0
`0xd04a` branch, `ESC E` to `0xcc52`, `ESC &k2G` to `0xedf8`, FF to
`0xf0f0`, page-size `ESC &l1A` to `0xfc74`, orientation `ESC &l1O` to
`0x10220`, paper-source `ESC &l2H` to `0xef62`, and copies `ESC &l2X`
to `0xeef0` before the modeled page-record publication layer.
These prove the direct-control/reset/page-geometry publication subset from
actual PCL/control bytes. The reset publication edge has since been broadened
from synthetic roots into page-record and addressed allocation fixtures:
`mixed printable/reset page-record stream queues through 0x1387c before
reset`, `mixed printable/reset page-record finalization publishes bridged
record`, and `addressed printable reset publishes rendered page record` cover
`! ESC E` from printable parse, compact bucket materialization, `0xff1e`
publication/current-root clearing, and `0x1ed84`/`0x1ef6a` rendered rows. The
remaining parser-firmware work is live CPU allocation/state capture for broader
heterogeneous streams, not this compact-text reset boundary.

For symbol-set selection, the harness now drives `ESC (2U` and `ESC )0E`
through `0x120be`/`0x1be22`/`0xc580`, records active words `0x0055` and
`0x0005`, and applies the corresponding `LINE_PRINTER` map patches
before host bytes become compact glyph bytes.

For normal printable text, the harness now drives a one-byte stream
`0x21` (`!`) through the modeled `0x1393a` source-object builder,
`0xd824` positioning handoff, `0x12f2e` compact queue producer, and
compact-glyph renderer. It also has a two-byte `!!` fixture that
advances the packed horizontal cursor through the simple `0xd550`
default-advance branch between bytes and combines the two entries into
one short compact text object. The initialized `LINE_PRINTER` metric
fixture derives HMI `0x00120000` from resource longword `0x00480000`
through the `0x10550` conversion path and renders the second glyph from
compact coord `0x0202`, which `0x1f3d4` decodes as `$a001 = 0x12` /
pixel x `34`. The same `!!` stream is now traced through two `0xd04a`
printable parser events and tied to page-record root allocation,
bucket-0 reuse, `0x1edc6` bridging, and those real-HMI rows. The mixed
`!\x0e!\x0f!` stream now routes SO through `0xc6b8` and SI through
`0xc68a`, proving those normal-mode controls switch `0x782f06` to the
secondary text context and back before subsequent printable `0xd04a`
events queue selector-1 and selector-0 compact page-record objects. The
bridged render record carries context slots `0x44094b08` and
`0x440946b4`, so the check reaches the `0x1ed84`/`0x1ef6a` dispatch
with both polarities visible in the bucket chain. The mixed
`ESC &k1G!\r!` fixture queues the post-CR glyph at coord `0x3b00` /
`$a001 = 0x1b`, records that blank shifted rows clear the full byte span
`x=11..18`, and now has a page-record allocator/bridge variant for the
same stream. `ESC &k6H!!` routes HMI handler `0xca8c` and two printable
handler `0xd04a` events into the page-record path, proving 6 HMI units
store packed advance `15` and queue the glyphs at compact coords
`0x0600` and `0x0501`; `ESC &k2G!\n!` routes line-termination handler
`0xedf8`, LF handler `0xf08c`, and two printable handler `0xd04a`
events into the page-record path, proving LF mode `0x60` applies CR+LF
before the second glyph queues at compact coord `0x3b00`;
`ESC &k0G HT BS !` routes line-termination handler `0xedf8`, HT handler
`0xf1cc`, BS handler `0xf2a8`, and printable handler `0xd04a` into the
page-record path, proving HT/BS move the queued glyph to compact coord
`0x0a01` / pixel x `26`; `ESC &a1L!` routes left-margin handler
`0xeb58` then printable
handler `0xd04a` into the page-record path, proving the initialized HMI
column margin moves the queued glyph to compact coord `0x0801` / pixel x
`24`; `ESC &a1M!` routes right-margin handler `0xec0c` then `0xd04a`,
proving right-margin cursor movement feeds the queued glyph at compact
coord `0x0a02` / pixel x `42`; `ESC &a6l9M!` routes lowercase-final
left-margin handler `0xeb58`, keeps parser mode `12` open for
right-margin handler `0xec0c`, and queues the glyph at compact coord
`0x0207` / pixel x `114`; `ESC &a2C!` routes cursor-position handler
`0xf39e` then `0xd04a`, proving two initialized HMI columns move the
queued glyph to compact coord `0x0a02` / pixel x `42`; `ESC &a72H!`
routes horizontal-decipoint handler `0xf416` then `0xd04a`, proving 72
decipoints convert to packed cursor x `30` and queue the glyph at
compact coord `0x0402` / pixel x `36`; `ESC &a1R!` routes vertical
cursor-position handler `0xf560` then `0xd04a`, proving one initialized
VMI row plus absolute-row bias moves the queued glyph to compact coord
`0x1001` in bucket `4`; `ESC &a72V!` routes vertical-decipoint handler
`0xf60a` then `0xd04a`, proving 72 decipoints convert to packed cursor y
`30` and queue the glyph at compact coord `0x9001` / bucket `0` with
nine blank rows before the glyph body; `ESC &a2c+1R!` routes
lowercase-final horizontal handler `0xf39e`, keeps parser mode `12` open
for relative vertical handler `0xf560`, and queues the glyph at compact
coord `0x1a02` in bucket `3`; `ESC &l3E!` routes top-margin handler
`0xece2` then `0xd04a`, proving the pending vertical cursor refresh
moves the queued glyph to compact coord `0x9001` in bucket `6`. The
mixed `!\x1bE` fixture keeps the pre-reset glyph renderable,
publishes/clears the valid current page root through reset, and now has
a page-record allocator/bridge/publication variant for the same stream.
`generated/analysis/ic30_ic13_page_root_allocation.md` now pins the
shared `0x10084` first-root allocation and `0x10110` selected-context
slot bootstrap, and
`generated/analysis/ic30_ic13_page_root_finalization.md` pins the shared
`0xff1e` publish-or-clear contract. `0x1387c` allocator fixtures now
queue short compact objects and segmented tall-glyph objects under the
page-record bucket-array shape, and a `0x1edc6` bridge fixture copies
that compact bucket/context slot into render-record shape, pins the
rule/fixed-list normalization side effects, and includes producer-shaped
`0x13386`/`0x136d2` rule-list objects. This is still a narrow
normal-mode fixture, not a full parser state emulator.

The direct text/control page-record streams are now tied back to host
fetch as well as the ROM parser dispatch path. The grouped host-fetch
check drains `!!`, `ESC &k1G!\r!`, `ESC &k2G!\n!`, `ESC &k0G HT BS !`,
the margin and cursor-position streams, `ESC &l3E!`, and
`ESC &f0S ESC &a2C ESC &f1S!` from the modeled `0xa904` ring source,
replays the expected parser handlers, and lands on the same page-record
allocations, object prefixes, rendered row counts, and `0x1edc6` bridge
fields for bucket root, empty rule/fixed lists, and context slot
copying. The same group now crosses `0x1ed84` active-record copy and
the `0x1ef6a` render-entry call order, including the nonzero bucket
selection used by the vertical cursor/layout cases. A host-fetched
`! ESC *c12a5b0P` fixture now extends that page-record stream model to a
combined compact-text bucket plus selector-7 rule list before the same
`0x1ed84`/`0x1ef6a` render-entry path composes the rows. A second
host-fetched fixture adds `ESC *t300R ESC *r0A ESC *b2W` and queues a
mode-0 raster row into the same page-record shape before the combined
bucket/rule/raster render-entry comparison.

Rectangle/rule command edges are now documented in
[rectangle-graphics.md](rectangle-graphics.md).
`ESC *c#A/#B/#H/#V` update rectangle width/height state `0x78316a` /
`0x783166`, `ESC *c#G` updates area-fill id `0x78316e`, and `ESC *c#P`
maps the current fill selector before `0x10b80` clips the current-cursor
rectangle and queues a rule-list object through `0x13386`. The harness
pins dot dimensions, decipoint rounding, gray/pattern selector mapping,
a chained `ESC *c12a5b0P` byte stream reaching the selector-7 rule
object, bridge normalization, solid black rendering through `0x1f446` /
`0x1f596`, solid-rule band-crossing continuation, gray selectors `0..6`
and HP pattern selectors `8..13` through `0x1f446` / `0x1f4e0`, sub-byte
shifted, band-crossing, two-band page-assembly HP-pattern cases, a
negative-left clipping case, right/top/bottom edge clipping,
landscape-edge clipping, off-page ignore reasons, and a parser-to-retry
boundary tying the same stream to `0x10d22` publication, fresh-root
allocation, retry queueing, bridge, and rendering.

## Top-Level ESC Dispatch

After `ESC`, parser mode 1 maps bytes to command families:

| Sequence | Next mode | Handler |
| --- | ---: | --- |
| `ESC E` | 0 | `0x00cc52` |
| `ESC *` | 3 | `0x011ec8` |
| `ESC )` | 4 | `0x012008` |
| `ESC (` | 4 | `0x01201e` |
| `ESC &` | 5 | `0x011ec8` |
| `ESC =` | 0 | `0x00f176` |
| `ESC 9` | 0 | `0x00e9ba` |
| `ESC z` | 0 | `0x00cd86` |
| `ESC Y` | 0 | `0x012536` |

`generated/analysis/ic30_ic13_esc_e_reset_flow.md` now traces `ESC E`
beyond the top-level dispatch. `0x00cc52` calls `0x00cc70`, `0x00cbd4`,
and `0x00e146`, then clears `0x782a93`. `0xcc70` flushes pending text
spans, calls page-root finalizer `0xff1e`, waits for active page/control
records through `0x9ac2`, rebuilds page/environment state, and
reinitializes raster block `0x783170`. `0xcbd4` refreshes HMI/default
text motion and active symbol snapshots from current-font context state.
`0xe146` resets parser/data-chain state, clears transient parser records
and text accumulation bytes, and prunes command/data pool records.
The reset report now also decodes the environment-default helper
`0xcda2`: it rebuilds the four 0x6c-byte page/control records rooted at
`0x780f02`, resets parser scratch `0x782a26`, resets cursor-stack top
`0x782d36` to `0x782c96`, restores display/page defaults from
`0x78219d` and `0x7821a2`, clears line-termination byte `0x78318f`,
recomputes HMI `0x78315c` from the primary current-font context, and
derives reset VMI `0x783160` from default line-spacing word `0x78219e`
with firmware clamps at `5` and `0x80`.
`generated/analysis/ic30_ic13_page_root_finalization.md` decodes the
`0xff1e` branch: active roots publish as state `2` through
`0x780ea6`/`0x782996`, while missing or inactive roots only clear
`0x78297a`. This is the firmware anchor for PCL software reset and its
partial-page finalization behavior.

`tools/render_fixture_harness.py` now has synthetic `ESC E` byte-stream
fixtures for both reset page-root cases: valid roots are published
before the current root is cleared, while missing/invalid roots clear
without publication. The missing-root case now also starts `ESC E` from
the modeled `0xa904` ring source, reaches ROM parser handler `0xcc52`,
and lands on the same no-publication reset state. The mixed `!\x1bE`
fixture exercises that valid-root reset path after queuing a printable
text object, and its page-record variant queues and bridges that object
under page-record storage rules, then publishes the same bucket through
a modeled `0xff1e` finalization record before reset clears the current
root. The reset, FF, page-size, orientation, paper-source, and copies
publication streams now start from real parser traces; `!\x1b&l2H`
reaches handler `0xef62`, publishes queued text through `0xff1e`, writes
paper-source value `0x80` to `0x782da6`, and sets pending-status byte
`0x782998`. `!\x1b&l2X\f` reaches `0xeef0`, stores copy count `2` in
`0x782da4`, then reaches FF handler `0xf0f0`, whose `0xff1e` publication
copies that word into pool-header `+0x0c`.
Reset, FF, page-size, orientation, paper-source, and copies also have
addressed allocator variants: `!\x1bE`, `ESC &k2G!\f`, `!\x1b&l1A`,
`!\x1b&l1O`, `!\x1b&l2H`, and `!\x1b&l2X\f` queue the printable byte
through `0x1387c`/`0x1381c`, materialize the compact bucket page record,
publish through the matching `0xff1e` boundary, and render through
`0x1ed84`/`0x1ef6a`. The host-fetched publication checks now start those
same publication streams from the modeled `0xa904` ring source and pin the
same published pool header after `0xff1e`: state byte `+4 = 2`,
status/environment fields including copies word `+0x0c`, `0x780ea6`,
bucket-root prefix, and context-slot prefix. The `0x1387c` allocator
fixtures queue short and segmented compact buckets under page-record storage
rules, and the `0x1edc6` bridge fixture proves the render-record copy contract
for that compact bucket. The addressed publication fixtures close the
software-visible compact-text reset/FF/geometry/copies path through
materialized page-record storage; the remaining parser-firmware gap is a live
CPU memory/register capture that proves the same allocation and publication
state without the modeled handoff layer.

## Parsed-Command Dispatch

After tokenization, routine `0x0000e112` implements `ESC &f#Y`: it
rewinds the parsed-record cursor by six bytes, reads the signed word at
`record+2`, stores its absolute value in current macro id word
`0x783164`, and returns.

Routine `0x0000dd08` implements `ESC &f#X`: it rewinds the parsed-record
cursor by six bytes, takes the absolute selector value from `record+2`,
looks up or allocates a 12-byte macro record through `0x0000e0a4`, and
jumps through a table at `0x0000dca8` via common dispatch helper
`0x00033298`. Current macro record pointer lives at `0x782d7a`; current
data-chain frame pointer lives at `0x782d76`.

The lookup helper `0xe0a4` is now pinned at the slot-policy level. It
scans the 32 records at `0x782a98` in 12-byte steps, compares the
requested id to record word `+8`, but returns an existing record only if
record longword `+0` is nonzero. The first zero-head record is remembered
as free even when its stale id word is nonzero. If no nonempty match is
found, that first free record receives the requested id at `+8`, becomes
`0x782d7a`, and returns status `0`; a nonempty match returns status `1`.
If every record has a nonzero head and none matches, `0xe0a4` clears
`0x782d7a` and returns status `2`. The helper does not inspect
permanence byte `+0x0a`; selectors `7`, `9`, and `10` own that policy.

The table maps selector values to handlers:

| Selector | Handler | Meaning |
| ---: | --- | --- |
| 0 | `0x0000dd86` | start macro definition |
| 1 | `0x0000ddfc` | stop macro definition |
| 2 | `0x0000de7c` | execute macro |
| 3 | `0x0000dea2` | call macro |
| 4 | `0x0000dec8` | enable overlay |
| 5 | `0x0000def4` | disable overlay |
| 6 | `0x0000defe` | delete all macros |
| 7 | `0x0000df08` | delete temporary macros |
| 8 | `0x0000df12` | delete current macro id |
| 9 | `0x0000df24` | make current macro temporary |
| 10 | `0x0000df36` | make current macro permanent |

Selector `0` starts definition mode. When invoked by lowercase-final
`ESC &f0x`, it seeds the stored byte stream with:

```text
ESC & f
```

Uppercase-final `ESC &f0X` seeds a single zero byte instead. Selector
`1` stops definition mode, normalizes chunk-header overhead out of the
stored byte count, and clears empty one-byte or auto-prefix-only
records; the auto-prefix-only check tests payload bytes `0x1b`, `0x26`,
and `0x66` at chunk offsets `+4`, `+5`, and `+6`.

The append/count path behind that storage is now pinned. `0xe002` only
appends when active frame byte `+9` is zero and macro error byte
`0x782c19` is clear. When the low byte of record `+0x04` is zero, it
allocates a zero-filled 0x100-byte chunk through `0x170c(1, 1, 0x100)`,
links it through record `+0x00` or the previous chunk's first longword,
stores the new current chunk in `0x782c1a`, adds four header bytes to
record `+0x04`, then writes the payload byte at chunk `+4`. Existing
chunks write at `chunk + 4 + low_count - 4`. Each chunk therefore stores
252 payload bytes; the next append after raw count `0x100` links a second
chunk and leaves raw count `0x105` after writing the 253rd byte. Stop
normalization derives payload bytes as
`raw_count - (((raw_count + 0xff) >> 8) * 4)`.

Selectors `2` and `3` require an existing record with payload bytes and
call `0x0000e418` with mode byte `2` for execute or `3` for call.
`0xe418` advances `0x782d76` by `0x0e` and builds the next 14-byte
data-chain frame: frame `+0x00/+0x04` copy macro record `+0x00/+0x04`,
byte `+8 = 4`, byte `+9 = mode`, and longword `+0x0a` receives the
environment snapshot pointer returned by `0xe8f0`. Execute mode snapshots
`0x783192 -> 0x78319a`; call mode snapshots `0x782d9e -> 0x78319a`.
Nonzero byte counts set host gate bit 1. Call mode additionally pushes a
10-byte context-stack entry at `0x782c6e`, copying longwords from
`0x782ee6` and `0x782ef6`, clearing bytes `+8/+9`, and advancing the
stack pointer by `0x0a`; execute mode does not push this entry.

The environment snapshot helpers behind frame `+0x0a` are now pinned:
`0xe8f0` copies an inclusive longword range into 0x100-byte linked chunks
with a longword next pointer plus 63 longwords of payload per chunk.
`0xe8a2` restores that chain into an inclusive destination range and
reports error `0xe3` through `0x1284` if data remains after the range is
filled. `0xe972` and `0xe996` are flat inclusive longword copy helpers in
opposite call shapes. `0xe22c` consumes the active frame after `0xa904`
sees frame `+4 == -1`: execute restores `0x783192..0x78319a`, call
restores `0x782d9e..0x78319a` and pops one 10-byte context entry through
`0xe65c(0)`, both free the snapshot chain, rewind `0x782d76` by `0x0e`,
clear host gate bit 1 when the previous frame has no bytes, and call
`0x1240a`. Other frame-byte values take the flat restore branch:
`0xe972` copies 281 longwords from `0x7834c2` into
`0x782d3a..0x78319a`, leaves `0x782d76` on the same frame, clears host
gate bit 1 when frame `+4` is zero, restores cursor longword
`0x782c92 -> 0x782c8a`, calls `0xe65c(0)`, sets `0x782a92 = 0x63`,
then calls `0x1240a` and `0x9ec0(0)`.

The producer for that non-replay frame is now pinned at `0xe4f4`.
Page-root finalization reaches it from `0xff8e` after `0xe0a4` restores
saved key `0x782a94` and the selected record has a nonzero head. `0xe4f4`
pushes a context entry, snapshots `0x782d3a..0x78319a` to `0x7834c2`,
saves cursor longword `0x782c8a` to `0x782c92`, restores baseline range
`0x782ee2..0x78319a` from `0x7831a2`, calls `0xe5e2`, then writes frame
`0x782d4c` with byte `+8 = 4`, byte `+9 = 4`, record payload/count in
`+0/+4`, and `+0x0a = 0`.

The `0xe5e2` helper is now composed into the layout/VFC/font model rather
than left as an isolated macro gap. It writes top offset
`0x782dce = 0x96 - 0x782dbe`, or `-0x782dbe` when page extent
`0x782dba <= 0x96`; clears scratch/cache word `0x782dd0`; refreshes
text-bottom cache through `0xea16`; resets margins through `0xe9ba`;
refreshes pending vertical cursor through `0xf8fc`; recomputes VFC
line-count caches through `0xfe54`; rebuilds the default VFC table through
`0x12b96`; and consumes static font-context record `0x782c64` through
`0xe65c(1)`. Fixture
`0xe5e2 refreshes page layout, default VFC table, and static font
context` pins the normal and short-page top-offset branches, margin reset,
VFC table prefix, modified-layout clear, and static secondary refresh.

The shared heap allocator used by those chunks is pinned at the contract
level. `0x170c` and `0x1710` allocate 64-byte units from opposite scan
directions; alignment `0x100` consumes four units per requested object,
and a nonzero zero-fill argument clears the allocated run. `0x18b4`
frees a contiguous run when count is nonzero, or follows the first
longword as a linked-chain pointer when count is zero. Macro record clear
`0xdfba` and snapshot cleanup use `0x18b4(ptr, 0, 0x100)`, while font
payload cleanup at `0x1659c..0x165a4` uses a counted `0x40` run.

The allocator initializer is now pinned for the default startup path.
Startup helper `0x0b18` writes heap start `0x783f4a` to `0x780efa` and
available bytes `0x640b6` to `0x780efe` when reset defaults
`0x780e5a = 0x20` and `0x780e60 = 6` are active. Reset helper `0x0370`
then calls `0x164a`, which reserves `0x783f4a..0x784905` as occupied,
sets free-unit count `0x18cf` at `0x780e86`, stores bitmap-base pointer
`0x784906` in variable `0x783972`, stores payload-base pointer
`0x784c40` in variable `0x783988`, and seeds scan fields
`0x783976`, `0x78397a`, `0x78397e`, `0x783982`, and `0x783986`.
Fixture `0x164a initializes heap allocator bitmap and payload base`
covers the default and compact sizing branches.

The `0xe65c` call-context refresh is now split into branch-contract
fields. Argument `0` pops the 10-byte context stack at `0x782c6e`;
argument `1` uses static record `0x782c64`. Entry bytes `+8/+9` refresh
primary/secondary slots through `0x13eb8(0/1)`, copy active words
`0x783144`/`0x783146` into remembered words `0x782f08`/`0x782f0a`,
and set dirty byte `0x782f2d` only when selector byte `0x782f06`
matches the refreshed slot. The common path clears the consumed record,
calls `0xc428(0x782f06)`, optionally rebuilds the selected current-font
context from `0x782c80`/`0x782c84` through `0x1b4c0`, `0x144d2`, and
`0x14c64`, then exits through `0x1b04c` and clears `0x782f2d`.
Helper `0xe860` supplies the static-record mismatch test from
`0x782ee6 + 0x10 * slot`. When context byte `+4` is zero it returns the
inline/downloaded class selector at pointed record byte `+0x16`; when
context byte `+4` is nonzero it returns the bit-30 offset-table/built-in
class selector at pointed record byte `+0x20`. Fixture
`0xe860 reads inline +0x16 and offset-table +0x20 class bytes` pins that
split.
The `0xe65c` refresh decisions are now composed with the existing font
bridge: primary refresh slot `0` runs through the modeled `0x13eb8`,
`0x144d2`, and `0x14c64` path to map `0x782f32`; secondary refresh slot
`1` runs through the same path to map `0x783032`; the final `0xc428`
call installs the selected current-font context record into a page-root
font slot. Fixture `0xe65c refresh composes with font context bridge`
pins that connection.

The macro context stack is now bounded by reset evidence rather than by
the cursor-stack field. `0xe146` clears eight 10-byte records at
`0x782c1e..0x782c6d` and stores stack pointer `0x782c1e` at
`0x782c6e`. `0xe418` call mode and `0xe4f4` non-replay setup both push
one entry by writing longwords sourced from `0x782ee6` and `0x782ef6`,
clearing bytes `+8/+9`, and adding `0x0a` to the pointer. No bounds
check is visible in those push paths or in the `0xe65c(0)` pop path; the
ninth push starts at the pointer-storage field `0x782c6e`, while an
empty pop would read from `0x782c14`. This is distinct from the
PCL-exposed cursor stack at `0x782c96..0x782d36`, which is handled by
`ESC &f#S` at `0xf75e` with explicit bounds.

`tools/render_fixture_harness.py` has executable fixtures for `0xe112`,
the `0xdd08` start/stop/delete/overlay/permanent selector behavior, and
the `0xe002` chunk append/count path, `0xe418` execute/call data-chain
frame shape, plus `0xe65c` stack, static, and empty-install refresh
paths. Chained
`ESC &f-123y0x1X`, `ESC &f123Y ESC &f0X ! CR ESC &f1X ESC &f2X`,
`ESC &f123Y ESC &f0X ! CR ESC &f1X ESC &f3X`,
`ESC &f123Y ESC &f0X ! CR ESC &f4X ESC &f5X`, permanence/delete,
delete-current, delete-all, and guard-state byte-stream fixtures now
prove signed macro-id normalization, lowercase start auto-prefix
behavior, plain definition-payload storage, stop-kept cleanup,
execute/call frame creation from command bytes, overlay enable/disable
state, selector `10` survival through delete-temporary, selector `9`
making the record removable, selector `8` clearing only the current id,
selector `6` clearing pool records, definition-mode and
active-data-chain guard suppression, and the same complete command
streams draining from modeled `0xa904` ring fetch into those records and
frames. The definition fixture now also drains the same
`ESC &f123Y ESC &f0X ! CR ESC &f1X` bytes from modeled `0xa904` ring
fetch before proving `ESC &f1X` remains enabled through alternate parser
table `0x116f6` while payload CR is not dispatched as a control code.
The full define-and-execute and define-and-call streams now drain from
modeled `0xa904` ring fetch through the ROM/alternate parser trace,
build the execute/call data-chain frames, and replay payload bytes
through `0xa904` into `0xd04a`/`0xf02c`. The fixtures also prove
end-marker outer-source resumption for execute/call frame payloads,
modeled printable/CR processing, and page-record allocator/bridge shape
for that payload. The empty chained macro fixture is also traced through
ROM parser modes `0 -> 1 -> 5 -> 17 -> 17 -> 17 -> 0` to final handlers
`0xe112`, `0xdd08`, and `0xdd08`. The execute/call payload page-record
fixture is now fed by a replay helper that drains the `0xe418` frame
through the `0xa904` data-chain source before handing those bytes to the
modeled printable/page-record path. The stored `ESC &k1G!\r!`
mixed-control execute payload now also starts from modeled `0xa904` ring
fetch through the ROM/alternate parser trace, stores the full mixed
payload, builds the execute frame, and replays through
`0xedf8`/`0xd04a`/`0xf02c`/`0xd04a` into page-record rows matching the
direct mixed-stream model. Execute, call, and mixed-control macro replay
payloads now also cross `0x1ed84` and `0x1ef6a` before rendering.
Overlay publication now has the same parser-to-output chain for the
covered selector-4 case: `0xff1e` resolves saved id `0x782a94` through
`0xe0a4`, builds a non-replay `0xe4f4` frame, re-enters parser loop
`0x11774`, and publishes the replayed `!\r` payload with an existing
selector-7 rectangle rule. Evidence: fixture `macro overlay finalization
replays before page publication`. Fixture `macro overlay replays across
repeated page publications` reuses the same enabled overlay state across two
modeled `0xff1e` page boundaries, proving that both publications replay
`!\r` and compose with their page-specific selector-7 rule before publication.
Fixture `macro overlay skip gates preserve base page publication` covers the
same `0xff1e` branch when overlay replay is not allowed: disabled overlay
mode, missing selected record, and page-root retry flag all publish the base
printable/rule page record without adding a non-replay frame.
Fixture `macro overlay mixed-control payload publishes with page rule` covers
the same non-replay overlay publication path for stored payload `ESC &k1G!\r!`:
`0xff1e` resolves overlay id `125`, `0xe4f4` builds the non-replay frame,
parser loop `0x11774` dispatches `0xedf8`, `0xd04a`, `0xf02c`, and `0xd04a`,
and publication renders the replayed compact text entries with an existing
selector-7 rectangle rule. The composed semantic checkpoint is
`Macro Definition And Data-Chain Replay` in `notes/semantic-state-model.md`;
no macro execute/call replay, font-context, first overlay-publication,
repeated enabled-overlay publication, mixed-control overlay payload, or overlay
skip-gate middle edge remains in that checkpoint.

Top-level `ESC &` enters mode 5. The normal table currently identifies
these subfamilies:

| Prefix | Next mode | Handler |
| --- | ---: | --- |
| `ESC &s` | 8 | `0x011eda` |
| `ESC &p` | 9 | `0x011eda` |
| `ESC &l` | 10 | `0x011eda` |
| `ESC &k` | 11 | `0x011eda` |
| `ESC &f` | 17 | `0x011eda` |
| `ESC &d` | 0 | `0x012622` |
| `ESC &a` | 12 | `0x011eda` |

This matches high-value PCL areas: page/layout (`&l`), font/text
attributes (`&k`, `&d`), cursor positioning (`&a`), and macros (`&f`).

## Record Pools and Output Chains

The parser uses a pool of 32 records at `0x782a98`, each apparently 12
bytes long:

- `0xdf4e` clears all 32 records by repeatedly calling `0xdfba`.
- `0xdf80` clears only records whose byte at offset `+0x0a` is zero.
- `0xdfba` clears fields at `+4`, `+8`, `+0x0a`, frees a `0x100` byte
  allocation via `0x18b4`, and clears the record pointer.
- `0xe002` appends a byte to a current data chain, allocating `0x100`
  byte chunks through `0x170c` as needed.
- `0xe0a4` scans the 32-entry pool keyed by macro id word `+8`: existing
  records with a nonzero payload pointer return status `1`, the first
  zero-head record is assigned the requested id and returns status `0`,
  and a full pool returns status `2`. Stale id words in zero-head slots
  do not prevent reuse.

These structures need full naming, but they are already concrete enough
to drive PCL parser fixture work.

## Tokenizer and Macro Dispatch Callers

`generated/analysis/ic30_ic13_tokenizer_macro_callers.md` now pins the
static caller map requested for parser work. `0xdaf0` has ten direct
absolute callers: the main parser callback restart at `0x11b28`, four
stateful helper/callback paths at `0x11bdc`, `0x11c88`, `0x11d64`, and
`0x11e2a`, four `ESC (` / `ESC )` font-selection wrappers at `0x11fda`,
`0x11fec`, `0x12014`, and `0x1202a`, and the `ESC &d` handler at
`0x1262a`.

The same report confirms that `0xdd08` has no direct absolute `JSR`
callers. It is reached through normal and alternate/data parser table
entries for mode 17: `ESC &f#x` remains in mode 17, and `ESC &f#X`
returns to mode 0. That matches the executable macro fixtures where
normal `ESC &f#Y` sets the macro id through `0xe112`, while `x/X`
records route to `0xdd08`; the alternate/data table keeps `x/X ->
0xdd08` but disables the normal macro-id handler.

The tokenizer report also classifies the stateful helper bodies at
`0x11ba6`, `0x11c6c`, `0x11d0c`, and `0x11dd2`. The important
reproduction contract is the repeated six-byte record rewind at
`0x78299e`, the shared `W/w` delayed-payload boundary through
`0x121cc(0x1228a)`, and the terminal restore through `0x12218`.
Helper `0x11dd2` adds a font-state refresh through `0xc580`, while the
callback helpers can append terminal bytes through `0xe002` in
alternate/data mode before restoring the delayed record.

## Rejected Lead

The `cmpi.w #0x000c` at `0x0001053a` is not the PCL form-feed handler.
The surrounding code is arithmetic/modulo-style helper code and
hexadecimal/decimal formatting, so it should not be used as a
control-code anchor.

## Next RE Targets

- Correlate the direct-input MMIO names for `0xa904` with board/manual
  evidence. The RAM byte-source structures and `0xa6cc` ring producer are
  documented in [host-byte-fetch.md](host-byte-fetch.md).
- Decode any remaining normal and alternate parser table handlers that are
  not already composed into command-family semantic notes.
- Treat the six-byte tokenizer records and the 12-byte macro/data-chain pool
  as documented structures: the shared record boundary is in
  [pcl-parser-core.md](pcl-parser-core.md), and the pool rooted at
  `0x782a98` is composed in `Macro Definition And Data-Chain Replay` in
  [semantic-state-model.md](semantic-state-model.md).
- Continue from parser-produced heterogeneous page-object rendering and
  final device-output validation now that the macro replay/font-context
  checkpoint is composed through `0xe65c`, `0xe860`, `0x13eb8`,
  `0x144d2`, `0x14c64`, and `0xc428`.
- Treat compact-text `ESC E` publication as covered through page-record and
  addressed allocation fixtures; keep pursuing live CPU allocation/state
  capture for broader heterogeneous streams. The current host-fetched
  publication fixtures already prove the modeled `0xff1e` publication
  headers, bridge, and rendered queued compact buckets before reset, FF,
  page-size, and orientation consume the current page root. The text/rule/raster
  page-record fixture now carries its full bucket array, rule list, and context
  slots through `0xff1e` before rendering after one mixed stream runner handles
  text, `ESC *c`, and delayed raster transfer commands. The trailing-FF variant
  now drives that publication from the host byte stream, and the addressed
  trailing-FF variant proves the same heterogeneous publication after text,
  rule, and raster objects materialize through addressed storage. A `0x1ef6a`
  page-band walker merges compact text, mode-0 raster, and a crossing patterned
  rule across bands `0` and `5`.
- Continue the mixed-stream page-record work at the remaining live
  CPU/register-memory boundary for parser-produced heterogeneous page objects.
  Parser-driven macro command/replay is no longer a separate target: the
  host-fetched macro definition, execute, call, mixed-control replay, overlay,
  repeated-overlay, skip-gate, and mixed-control overlay fixtures already route
  through the ROM/alternate parser traces and `0xa904` replay before reaching
  page-record and render-entry evidence.
