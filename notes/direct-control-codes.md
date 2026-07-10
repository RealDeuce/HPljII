# Direct Control Codes And Cursor State

This note is the semantic contract for the LaserJet II direct control-code
cluster. It composes CR, LF, FF, HT, BS, `ESC &k#G`, HMI, cursor stack,
margin, cursor-position, dot-position, and adjacent vertical-layout helpers
where they affect later text, page-record, or render output.

Status: composed for the documented byte-stream-to-page-record paths. The
low-level ledger remains in `notes/reverse-engineering-ledger.md`,
`notes/pcl-parser-firmware.md`, and generated reports. This file is the
renderer-facing documentation checkpoint.

## Evidence

- `generated/analysis/ic30_ic13_direct_control_code_flow.md`
- `generated/analysis/ic30_ic13_pcl_command_map.md`
- `generated/analysis/ic30_ic13_renderer_fixture_harness.md`
- `generated/analysis/ic30_ic13_printable_text_path.md`
- `generated/analysis/ic30_ic13_text_cursor_span_flow.md`
- `generated/analysis/ic30_ic13_page_record_bridge.md`
- `generated/disasm/ic30_ic13_control_code_handlers_00f02c.lst`
- `generated/disasm/ic30_ic13_macro_environment_snapshot_helpers_00e65c.lst`
- `generated/disasm/ic30_ic13_page_length_handler_00f9e8.lst`
- `generated/disasm/ic30_ic13_hmi_vmi_handlers_00ca8c.lst`
- `generated/disasm/ic30_ic13_font_update_common_00c580.lst`
- `generated/disasm/ic30_ic13_font_selection_update_handlers_00c6ec.lst`
- `generated/disasm/ic30_ic13_perforation_skip_handler_00ee64.lst`
- `generated/disasm/ic30_ic13_wrap_mode_handler_00edb0.lst`
- `generated/disasm/ic30_ic13_dot_position_handlers_00f48c.lst`
- `notes/pcl-command-map.md`
- `notes/pcl-parser-firmware.md`
- `notes/page-raster-imaging.md`
- `notes/semantic-state-model.md`

Primary fixtures:

- `ESC &k#G line termination mode bits`
- `CR resets horizontal cursor and flushes pending text span`
- `CR line-termination mode 1 also advances vertical cursor`
- `LF line-termination mode 2 resets horizontal cursor`
- `FF line-termination mode 2 resets horizontal cursor and marks page eject`
- `HT advances to next eight-column stop`
- `HT clamps to page width when already beyond right limit`
- `BS subtracts HMI and sets pending previous-width latch`
- `BS clamps at left margin when crossing it`
- `BS alternate metrics subtracts previous width word`
- `control stream ESC &k1G then CR applies CR+LF`
- `control stream ESC &k2G then LF applies CR+LF`
- `control stream ESC &k2G then FF applies CR+page-eject`
- `control stream ESC &k3G applies CR/LF/FF combined line termination`
- `control stream HT then BS updates tab and previous-width state`
- `plain printable parser trace feeds page-record queue`
- `HMI parser trace feeds page-record queue`
- `mixed printable/control stream applies CR+LF before second glyph`
- `mixed printable/control stream renders post-CR glyph rows`
- `mixed printable/control parser trace feeds page-record queue`
- `mixed printable/control page-record stream queues through 0x1387c`
- `mixed printable/control page-record bridge renders post-CR glyph rows`
- `LF parser trace feeds page-record queue`
- `HT/BS parser trace feeds page-record queue`
- `ESC 9 clear margins feeds CR and page-record output`
- `ESC = half-line feed reaches shifted page-record output`
- `0xf75e ESC &f0S pushes cursor with vertical offset`
- `0xf75e ESC &f1S pops cursor and clears pending flags`
- `cursor stack stream ESC &f0S / ESC &f1S selects 0xf75e push/pop`
- `0xf75e cursor stack bounds and pop clamps to current extents`
- `cursor stack parser trace feeds page-record queue`
- `0xf39e ESC &a#C converts columns through HMI and relative flag`
- `0xf416 ESC &a#H converts decipoints and clamps horizontal cursor`
- `0xf560 ESC &a#R uses VMI with absolute top offset and relative cursor base`
- `cursor position stream ESC &a3.5c+1R selects 0xf39e then 0xf560`
- `0xf60a ESC &a#V converts decipoints and clamps vertical cursor`
- `0xf48c/0xf692 ESC *p#X/#Y use whole-dot packed cursor commits`
- `cursor position parser trace feeds page-record queue`
- `horizontal decipoint parser trace feeds page-record queue`
- `vertical cursor position parser trace feeds page-record queue`
- `vertical decipoint parser trace feeds page-record queue`
- `dot position parser trace feeds page-record queue`
- `chained cursor position parser trace feeds page-record queue`
- `0xeb58 ESC &a#L sets left margin and moves cursor only when needed`
- `0xec0c ESC &a#M applies plus-one column, clamps, and moves cursor at right edge`
- `margin stream ESC &a6l9M selects 0xeb58 then 0xec0c`
- `margin command parser trace feeds page-record queue`
- `right margin command parser trace feeds page-record queue`
- `chained margin command parser trace feeds page-record queue`
- `live CR span flush materializes 0x12714 page object`
- `left-margin parser span flush materializes 0x12714 page object`
- `vertical-cursor parser span flush materializes 0x12714 page object`
- `0xc992 ESC &l#D accepts ROM LPI set and refreshes pending vertical cursor`
- `0xcb00 ESC &l#C converts 1/48-inch VMI and keeps zero unmodified`
- `0xea9e ESC &l#F sets text length bottom or restores default`
- `0xece2 ESC &l#E sets top margin, default text length, and pending cursor`
- `0xee64 ESC &l#L toggles perforation skip for selectors 0 and 1 only`
- `0xcb00/0xc992/0xece2/0xea9e chained ESC &l stream selects vertical layout
  handlers`
- `vertical layout parser trace feeds page-record queue`
- `transparent data parser trace feeds page-record queue`
- `ESC &d underline selector materializes span output`
- `perforation skip parser trace feeds page-record queue`
- `0xedb0 ESC &s#C toggles end-of-line wrap for selectors 0 and 1 only`
- `0xd28a and 0xd6bc prechecks share continue reject and wrap decisions`

## Owner Summary

Concept: this note owns ordinary printable text and direct cursor/control
command state from parser terminal handlers to page-record effects. It covers
normal printable fallback `0xd04a`, CR, LF, FF, HT, BS, line termination,
SO/SI selected text context, HMI/VMI, cursor stack, margins,
absolute/relative cursor and dot positions, wrap and perforation state,
underline/span flush, and the handoff from cursor or context state to compact
text or span objects.

Primary route:

- Host/parser/dispatch owners deliver printable bytes to `0xd04a` or terminal
  handlers `0xf02c`, `0xf08c`, `0xf0f0`, `0xf1cc`, `0xf2a8`, `0xedf8`,
  `0xc68a`, `0xc6b8`, `0xca8c`, `0xedb0`, `0xeb58`, `0xec0c`, `0xe9ba`,
  `0xf176`, `0xf39e`, `0xf416`, `0xf560`, `0xf60a`, `0xf48c`, `0xf692`,
  `0xf75e`, `0x12622`, `0xcb00`, `0xc992`, `0xece2`, `0xea9e`,
  `0xee64`, or `0xf9e8`.
- Printable route:
  `0xd04a -> 0x1393a -> 0xd140/0xd550 -> 0xd3b2/0xd824 -> 0x12f2e
  -> 0x1387c -> page-record storage -> publication/render`.
- Direct controls mutate cursor, layout, margin, selected text context, span,
  or mode state. Their visible effects occur through a later printable byte,
  span flush `0x12714`, FF/VFC/page-eject publication `0xf124 -> 0xff1e`, or
  raster/rectangle consumers that read the same cursor state.
- Alternate/data mode suppresses those ordinary direct-control effects at the
  parser table. Mode-zero C0 rows for BS, HT, LF, FF, CR, SO, and SI append
  stored bytes instead of calling `0xf2a8`, `0xf1cc`, `0xf08c`, `0xf0f0`,
  `0xf02c`, `0xc6b8`, or `0xc68a`. Uppercase cursor/text-motion/layout rows
  in table `0x116f6` are blank, and lowercase chaining finals route only to
  `0x11f4c`; placement, line-termination, HMI/VMI, wrap, margin, cursor-stack,
  span, and selected-context fields remain unchanged until stored bytes replay
  through normal parser mode.
- Span flush route: direct controls call `0xf34a`, which can materialize a
  pending span through `0x12714 -> 0x126e2`.
- Pixel route after object creation belongs to
  [page-raster-imaging.md](page-raster-imaging.md#owner-summary),
  [active-render-scheduler.md](active-render-scheduler.md#owner-summary),
  and
  [page-raster-imaging.md](page-raster-imaging.md#pixel-generation-owner-summary).

Field groups:

- Canonical placement: `0x782c8a`, `0x782c8e`, `0x782dd6`, `0x782dda`,
  `0x78315c`, and `0x783160`.
- Canonical selected context: selected text slot `0x782f06`, current-font
  records `0x782ee6` / `0x782ef6`, page-root selected context slot
  `0x78297e`, and page-root context live flags `0x78297f+n`.
- Canonical control/layout modes: `0x78318f`, `0x783190`, `0x783191`,
  `0x782dba`, `0x782dc2`, `0x782dce`, `0x782db8`, `0x782dc6`, and
  `0x782dca`.
- Canonical stack/span state: cursor stack `0x782c96..0x782d36`, stack
  pointer `0x782d36`, span-enable byte `0x783184`, underline selector
  `0x783185`, and span watermarks `0x783186`, `0x783188`, and `0x78318a`.
- Canonical page output: current page root `0x78297a`, compact bucket objects
  under root `+0x1c`, and segment-list span objects produced by `0x12714`.
- Derived/cache: compact coordinates, source scratch `0x782d7e`, queue keys
  `0x782a7c..0x782a7e`, pending-width state, and render caches populated
  after publication.
- Parser scratch: parsed command cursor `0x78299e` and admitted host bytes
  before terminal handlers rewrite local command records.
  Alternate/data direct-control records that terminate at blank rows or
  `0x11f4c` remain parser scratch only and do not become canonical placement,
  stack, selected-context, layout, or span state.
- Firmware bookkeeping: `0x782a57`, `0x782a58`, `0x782a5a`, `0x782a5c`,
  `0x782a6d`, and `0x78318e`.
- Unknown: manual HP names for several latches are unknown, but their ROM
  roles are tied below to concrete writers, readers, and disassembly ranges.

Writers and readers:

- Writers are terminal handlers for line termination, CR/LF/FF/HT/BS, HMI/VMI,
  SO/SI selected text context, margins, cursor positioning, dot positioning,
  cursor stack, underline, perforation skip, wrap mode, and vertical layout.
  Their exact address ranges are listed in the sections below.
- Readers are printable text path `0xd04a`, printable prechecks `0xd28a` and
  `0xd6bc`, compact text/object queue `0x12f2e -> 0x1387c`, span materializer
  `0x12714 -> 0x126e2`, overflow helper `0xf36c`, page-record bridge
  `0x1edc6`, active render setup `0x1ed84`, row render `0x1ef6a`, and raster
  start handlers documented in `notes/raster-graphics.md`.

Output effect:

- Printable bytes queue compact text objects and can later render pixels after
  page-root publication and active-band scheduling.
- CR, LF, FF, HT, and BS primarily adjust cursor/span state. FF also publishes
  the current page root through the page-eject path.
- SO/SI, cursor, margin, wrap, perforation, and layout commands are state-only
  until a later printable, span, raster, rectangle, or publication consumer
  reads the mutated fields.
- Underline/span commands can materialize segment-list objects through
  `0x12714`.
- No direct-control handler writes final pixels before page-record
  publication and render dispatch.
- Alternate/data direct-control rows create no immediate page object, span
  object, publication, or render input. Their only output is stored input for
  later replay, except for active command families owned elsewhere such as
  macro control.

Evidence and boundaries:

- Disassembly evidence is in
  `generated/disasm/ic30_ic13_control_code_handlers_00f02c.lst`,
  `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`,
  `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`,
  `generated/disasm/ic30_ic13_hmi_vmi_handlers_00ca8c.lst`,
  `generated/disasm/ic30_ic13_dot_position_handlers_00f48c.lst`,
  `generated/disasm/ic30_ic13_page_length_handler_00f9e8.lst`, and the other
  focused listings named in the Evidence section.
- Fixture evidence is named in the Primary fixtures list above; each fixture
  anchors a parser route, state mutation, page-record queue entry, span object,
  or render bridge used by the semantic claims in this note.
- No unresolved ROM-local middle edge remains between normal printable entry
  `0xd04a` and compact bucket object creation at `0x12f2e..0x1306e` for the
  documented short and segmented source shapes.
- Remaining direct-control boundaries are exact variant boundaries named by
  the [Printable Source Outcome Matrix](#printable-source-outcome-matrix).
  New source variants belong here only when they change a field consumed by
  `0xd04a`, an allocation branch, compact object bytes, span-consumer state,
  or row-construction inputs; otherwise they are another instance of the
  documented source-to-object path.

## Direct-Control Output Decision Checkpoint

This checkpoint composes the direct-control family as output decisions rather
than isolated handlers. It starts after parser dispatch has selected a
terminal handler and ends at one of four outcomes: compact text object,
segment-list span object, page publication, or state-only mutation consumed by
a later byte stream.

Decision rules:

- Normal printable bytes reach `0xd04a`, build source scratch through
  `0x1393a`, choose flagged or unflagged text advance through `0xd550` or
  `0xd140`, and queue compact objects through `0x12f2e -> 0x1387c`.
  Publication and pixels then follow `0xff1e -> 0x1ed84 -> 0x1edc6 ->
  0x1ef6a -> 0x1effe`.
- `ESC &k#G` writes line-termination mode byte `0x78318f` through `0xedf8`.
  CR `0xf02c` consumes bit `7`, LF `0xf08c` consumes bit `6`, and FF
  `0xf0f0` consumes bit `5`; the bits decide whether those controls also run
  CR-style reset or LF-style vertical advance.
- CR and LF do not queue compact text by themselves. They reset or advance
  cursor fields `0x782c8a` / `0x782c8e`, flush pending spans through
  `0xf34a -> 0x12714` when `0x783184` is set, and make their effect visible
  when a later printable or graphics handler consumes the new cursor state.
- FF is both a cursor/layout consumer and a publication command. It optionally
  runs CR-style reset, flushes spans through `0xf34a`, ensures root
  `0x78297a`, calls `0xf124 -> 0xff1e`, and marks page-eject latch
  `0x782a6d = 0xff`.
- HT `0xf1cc` and BS `0xf2a8` are state-only placement commands. HT advances
  to the next eight-column stop from left margin `0x782dd6` using HMI
  `0x78315c`; BS subtracts HMI or previous-width state
  `0x782a58/0x782a5a/0x782a5c`. The next printable byte is the visible
  consumer.
- `ESC 9` handler `0xe9ba` resets horizontal margins without queueing a page
  object: `0xe9be` clears left margin `0x782dd6`, `0xe9c4` copies page width
  word `0x782db8` to right margin `0x782dda`, and `0xe9ce` clears fractional
  companion `0x782ddc`. The visible effect appears when CR, HT, margin checks,
  or a later printable consumes the reset margin state.
- SI `0xc68a` and SO `0xc6b8` are selected-context controls. Both set
  dirty-map byte `0x782f2d` before testing selected slot `0x782f06`. SI skips
  page-root context install when the selected slot is already primary; otherwise
  it calls `0xc428(0)` and clears `0x782f06` only after a nonzero return. SO
  skips the install when the selected slot is already secondary; otherwise it
  calls `0xc428(1)` and writes `0x782f06 = 1` only after a nonzero return.
  They create no page object directly, but the next printable byte consumes the
  selected slot, map, and page-root context slot through `0xd04a -> 0x1393a`.
- `ESC =` handler `0xf176` is a vertical-placement command. It ensures page
  root `0x78297a` through `0x10084`, flushes pending span state through
  `0xf34a`, converts VMI `0x783160` through `0x104fe`, halves it, normalizes
  the half-step through `0x104d8`, adds it to vertical cursor `0x782c8e`
  through `0x10518`, runs overflow/perforation helper `0xf36c`, optionally
  calls `0x1048c`, and clears pending text/cursor latch `0x782a6d`. It creates
  no text object by itself; the following printable, raster, or rectangle
  handler is the visible consumer of the shifted y position.
- Cursor, margin, and dot-position handlers `0xeb58`, `0xec0c`, `0xf39e`,
  `0xf416`, `0xf560`, `0xf60a`, `0xf48c`, and `0xf692` commit placement
  fields through `0xf4ca` or `0xf6e2`. If pending span state exists, they can
  materialize it through `0xf34a -> 0x12714` before overwriting the cursor
  boundary that defines the span.
- `ESC &d` handler `0x12622` writes underline/text-attribute selector
  `0x783185` and controls whether later printable span updates are armed.
  A terminal `&d@`, CR, margin change, or vertical cursor change can flush the
  pending span as a selector-`0x4000` segment-list object under page-root
  `+0x1c`.
- Layout and mode handlers `0xca8c`, `0xcb00`, `0xc992`, `0xece2`,
  `0xea9e`, `0xee64`, `0xedb0`, and `0xf9e8` write HMI, VMI, top/bottom
  limits, perforation skip, wrap mode, and page length. They are state-only
  until printable prechecks, LF/FF/perforation overflow, raster/rectangle
  placement, VFC, or publication reads the mutated fields.

## Direct-Control Outcome Matrix

This matrix is the command-family contract for direct controls and text
placement. It preserves the low-level ledgers below while grouping each
admitted byte or command by the next semantic object a renderer must model:
compact text object, segment-list span object, page publication, delayed
state-only mutation, or explicit no-output parser behavior.

- Printable byte:
  normal-mode no-row-match dispatch reaches `0xd04a`. The path captures source
  state through `0x1393a`, branches through unflagged `0xd140 -> 0xd3b2` or
  flagged `0xd550 -> 0xd824`, queues compact objects through
  `0x12f2e -> 0x1387c`, and later renders through publication, bridge, and
  compact dispatch. Canonical state is selected slot/context, cursor, current
  page root, source scratch `0x782d7e`, and compact bucket entries. Evidence:
  [Printable Source Outcome Matrix](#printable-source-outcome-matrix),
  `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`, and fixture
  `plain printable parser trace feeds page-record queue`.
- Line-termination mode:
  `ESC &k#G` reaches `0xedf8` and writes byte `0x78318f`: selector `1`
  writes `0x80`, selector `2` writes `0x60`, selector `3` writes `0xe0`, and
  selector `0` clears the byte. Readers are CR `0xf02c`, LF `0xf08c`, and FF
  `0xf0f0`. Output effect is delayed until those controls consume the bits;
  the concrete writer-to-consumer route is composed in
  [Line-Termination Route Checkpoint](#line-termination-route-checkpoint).
  Evidence: fixtures `control stream ESC &k3G applies CR/LF/FF combined line
  termination` and `control stream ESC &k2G then FF applies CR+page-eject`.
- CR and LF:
  CR `0xf02c` resets horizontal cursor through `0xf06e`, flushes pending spans
  through `0xf34a`, and can also run LF-style vertical movement when
  `0x78318f.7` is set. LF `0xf08c` optionally applies CR-style reset when
  `0x78318f.6` is set, then advances vertical cursor through VMI-scaled
  movement. Output effect is cursor/span state consumed by later printable,
  raster, rectangle, VFC, or publication paths. Evidence: fixtures
  `mixed printable/control parser trace feeds page-record queue` and
  `LF parser trace feeds page-record queue`.
- Half-line feed:
  `ESC =` reaches handler `0xf176`, which advances vertical cursor
  `0x782c8e` by half of current VMI `0x783160` and then runs the vertical
  overflow/perforation helper. It queues no object directly; the concrete
  writer-to-consumer path is composed in
  [Half-Line Feed Route Checkpoint](#half-line-feed-route-checkpoint).
- FF:
  FF `0xf0f0` optionally applies CR-style reset when `0x78318f.5` is set,
  flushes spans, calls page-eject path `0xf124 -> 0xff1e`, and writes pending
  page-eject latch `0x782a6d = 0xff`. Output effect is current-root
  publication when a root exists, or a no-publication reset/clear boundary when
  no root is active. Evidence: fixture `control stream ESC &k2G then FF
  applies CR+page-eject` and publication owner
  [publication-commands.md](publication-commands.md#publication-decision-checkpoint).
- HT and BS:
  HT `0xf1cc` advances to the next eight-column stop from left margin
  `0x782dd6` using HMI `0x78315c`; BS `0xf2a8` subtracts HMI or previous-width
  state `0x782a58/0x782a5a/0x782a5c`. Both update cursor/span state and create
  no page object directly. The following printable byte is the visible
  consumer. Evidence: fixture `HT/BS parser trace feeds page-record queue`.
- SI and SO:
  SI `0xc68a` and SO `0xc6b8` select primary or secondary text context by
  calling `0xc428(slot)` when a switch is needed, updating selected slot
  `0x782f06`, page-root selected slot `0x78297e`, and context slots
  `+0x2c..+0x68`. They create no page object directly. The following
  printable consumes the selected context through `0xd04a -> 0x1393a`.
  Evidence: [Selected Context Switch
  Checkpoint](#selected-context-switch-checkpoint) and fixtures
  `live primary current-font RAM install feeds SI page-record rows` and
  `live secondary current-font RAM install feeds SO page-record rows`.
- Margin reset and margin writers:
  `ESC 9` handler `0xe9ba` clears left margin `0x782dd6`, copies page width
  `0x782db8` to right margin `0x782dda`, and clears fractional companion
  `0x782ddc`. `ESC &a#L/#M` handlers `0xeb58` / `0xec0c` write left/right
  margins and may move horizontal cursor `0x782c8a`. Output effect is delayed
  placement, unless pending span state is flushed through `0xf34a -> 0x12714`.
  The concrete writer-to-consumer route is composed in
  [Margin Route Checkpoint](#margin-route-checkpoint). Evidence:
  [Span Flush Producers](#span-flush-producers).
- Cursor and dot positioning:
  `ESC &a#C/#H`, `ESC &a#R/#V`, and `ESC *p#X/#Y` reach
  `0xf39e`, `0xf416`, `0xf560`, `0xf60a`, `0xf48c`, and `0xf692`, then commit
  through horizontal helper `0xf4ca` or vertical helper `0xf6e2`. Canonical
  output is cursor state `0x782c8a/0x782c8e`; visible pixels appear only when
  later printable, raster start, rectangle clipping, VFC, or publication reads
  those fields. The concrete parser-to-consumer route is composed in
  [Cursor And Dot Position Route Checkpoint](#cursor-and-dot-position-route-checkpoint).
  Evidence: shared coordinate helper boundaries and cursor position fixtures
  in `Output Effect`.
- Cursor stack:
  `ESC &f#S` reaches `0xf75e`. Selector `0` pushes cursor plus vertical offset
  into stack `0x782c96..0x782d36`; selector `1` pops and clamps restored
  cursor to current extents; other selectors or full/empty stack cases return
  without output. Output effect is restored placement consumed by later
  printable, raster, or rectangle commands. Evidence:
  [Cursor Stack State Checkpoint](#cursor-stack-state-checkpoint).
- Underline/span state:
  `ESC &d` handler `0x12622` writes underline/text-attribute selector
  `0x783185` for accepted selector terminals and arms pending span state
  through `0x126e2`. Terminal flush paths, CR, margins, or vertical cursor
  changes can materialize selector-`0x4000` segment-list objects through
  `0xf34a -> 0x12714 -> 0x126e2`. Evidence:
  [Span Flush Producers](#span-flush-producers) and fixture
  `ESC &d underline selector materializes span output`.
- Layout, wrap, and perforation state:
  HMI/VMI/page-layout handlers `0xca8c`, `0xcb00`, `0xc992`, `0xece2`,
  `0xea9e`, `0xee64`, `0xedb0`, and `0xf9e8` write HMI, VMI, page extent,
  top/text limits, perforation skip `0x783191`, and wrap byte `0x783190`.
  They are delayed state until printable prechecks `0xd28a` / `0xd6bc`,
  overflow helper `0xf36c`, VFC, raster/rectangle placement, FF, or following
  printable bytes consume the fields. The HMI writer-to-consumer route is
  composed in
  [HMI Route Checkpoint](#hmi-route-checkpoint). Evidence:
  [Layout State To Output Checkpoint](#layout-state-to-output-checkpoint).
- Parser-only and no-handler rows: explicit zero-handler rows and lowercase chaining
  helpers keep parser state or report ignored bytes without page output. They belong to
  the parser owner unless a later terminal handler consumes the retained command-family
  record. Evidence:
  [pcl-parser-core.md](pcl-parser-core.md#no-output-and-reported-byte-checkpoint).

State grouping:

- Canonical:
  cursor fields, margins, HMI/VMI, selected text slot/context, page-root
  selected context slot, line-termination byte, wrap/perforation state,
  cursor-stack entries, pending span fields, current page root, compact bucket
  objects, and segment-list span objects.
- Derived/cache:
  printable source scratch, compact coordinates, previous-width latches,
  precheck result, span watermarks, queue keys, and render-band caches created
  after publication.
- Parser scratch:
  admitted C0 bytes, six-byte parsed command records, lowercase family
  chaining state, and lookahead bytes consumed by underline/parser helpers.
- Firmware bookkeeping:
  dirty-map byte, pending cursor/page latch `0x782a6d`, right-limit and
  previous-width latches, modified-layout byte, retry publication flag, and
  page-root allocation effects.
- Hardware/external:
  none for ROM-local direct-control behavior; physical paper timing begins
  after publication/render scheduling.
- Unknown:
  manual-facing names for some latches remain external, but the ROM-local
  writers, readers, object effects, and no-output boundaries above are pinned
  by disassembly and fixtures.

Unresolved boundaries:

- No ROM-local middle edge remains for the documented printable, CR/LF/FF,
  HT/BS, SI/SO, cursor/margin, cursor-stack, span-flush, wrap, perforation,
  or layout outcomes. New direct-control work should start only when a stream
  changes a named field, downstream consumer, page-object byte, publication
  state, bridge field, or render-helper input in the outcomes above.

### Selected Context Switch Checkpoint

SI and SO are state-only direct controls whose visible effect is delayed until
a later text consumer. The parser admits the C0 byte in the direct-control
route, then reaches SI handler `0xc68a..0xc6b6` or SO handler
`0xc6b8..0xc6e2`; neither handler queues a page object or calls publication.

SI `0xc68a` sets dirty-map byte `0x782f2d = 1`, tests selected slot
`0x782f06`, and returns immediately when the slot is already primary. On a
secondary-to-primary switch it calls `0xc428(0)`, and only a nonzero return
clears selected slot `0x782f06`. SO `0xc6b8` mirrors that path for slot `1`:
it sets `0x782f2d = 1`, skips work when `0x782f06` is already nonzero, calls
`0xc428(1)` on a primary-to-secondary switch, and writes `0x782f06 = 1` only
after `0xc428` succeeds.

The common install helper is `0xc428..0xc4fa`, with the page-root slot scan in
`0xc4fc..0xc57e`. Slot `0` reads current-font record longword `0x782ee6`;
slot `1` reads `0x782ef6`. When current page root `0x78297a` is present,
`0xc4fc` searches context longword slots at root `+0x2c + 4*n`, first
accepting a low-24-bit match, otherwise accepting the first slot whose live
flag `0x78297f+n` is not `1`. It returns `0x11` only when all 16 slots are
live and none match. On success, `0xc428` writes the selected page-root slot
byte `0x78297e`, refreshes metric/cache state from the selected context, and
may update HMI `0x78315c` when `0x782f2d` requested a metric refresh.

The visible consumer is the next printable route, not SI or SO itself.
`0xd04a..0xd0e8` calls `0x1393a(host_byte, 0x782d7e)`, and `0x1393a` selects
the active map/context pair from `0x782f06`: primary map `0x782f32` with
context longword `0x782ee6`, or secondary map `0x783032` with context longword
`0x782ef6`. The text queue paths `0xd3b2` and `0xd824` mark the selected
page-root font slot live before `0x12f2e -> 0x1387c` appends the compact text
object under current root `+0x1c`. Publication and render then carry both the
compact object and root context slots through `0xff1e`, `0x1ed84`, `0x1edc6`,
and compact render dispatch `0x1ef6a -> 0x1effe`.

Field grouping for this checkpoint:

- Canonical state: selected text slot `0x782f06`, current-font context
  records `0x782ee6` / `0x782ef6`, current page root `0x78297a`, selected
  page-root context slot `0x78297e`, page-root context live flags
  `0x78297f+n`, root context longword slots `+0x2c..+0x68`, primary map
  `0x782f32`, and secondary map `0x783032`.
- Derived/cache state: selected metric byte `0x78318e`, HMI `0x78315c`,
  printable source scratch `0x782d7e`, compact coordinates/object bytes, and
  render context cache populated after `0x1edc6`.
- Parser scratch: the admitted SI/SO byte and direct-control dispatch state;
  there is no delayed payload record for these controls.
- Firmware bookkeeping: dirty-map byte `0x782f2d`, page-root slot scan return
  `0x11`, and allocator/page-root ensure effects owned by downstream text
  queueing.
- Hardware/external and unknown: no hardware edge is involved in this
  ROM-local state switch. Manual-facing names for the HP primary/secondary
  context controls remain external labels, but the ROM field effects are
  named above.

Documented consumers and effects:

- `SI !!` with a seeded primary current-font record reaches
  `0xc68a -> 0xc428(0) -> 0xc4fc`, selects page-root slot `0`, and the two
  following printable bytes queue a primary compact object with prefix
  `00 00 00 00 00 00 00 02 00 6a 00 00 68 02`.
- `SO !!` with a seeded secondary current-font record reaches
  `0xc6b8 -> 0xc428(1) -> 0xc4fc`, selects page-root slot `1`, and the two
  following printable bytes queue a secondary compact object with prefix
  `00 00 00 00 00 01 00 02 00 c9 00 00 cb 01`.
- Parsed selection streams `ESC (s0p10h12v0s0b3T SI !!` and
  `ESC )s0p16h8v0s0b0T SO !!` compose the same state switch with upstream
  font-selection handlers. Those streams prove the direct-control byte is a
  context selector between parsed current-font state and later printable text,
  not a page-object producer.

Evidence: SI/SO handler bytes are in
`generated/disasm/ic30_ic13_font_update_common_00c580.lst`; page-root context
install is in
`generated/disasm/ic30_ic13_font_context_install_00c428.lst`; the printable
consumer is in `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`;
compact queueing is in
`generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`; the render bridge is
covered by `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`.
The detailed owner ledger and fixture claims are in
[font-context-metrics.md](font-context-metrics.md), especially the
`Page-Root Context Install`, `Printable Source Capture`, and
`Reproduction Contract` sections plus fixture anchors
`live primary current-font RAM install feeds SI page-record rows`,
`parsed primary selection current-font RAM feeds SI visible rows`,
`live secondary current-font RAM install feeds SO page-record rows`, and
`parsed secondary selection current-font RAM feeds SO visible rows`.

Unresolved boundary: no ROM-local SI/SO state-to-text edge remains open for
the documented primary/secondary paths. Future work belongs here only if a new
stream changes one of these exact boundaries: selected slot `0x782f06`,
current-font records `0x782ee6` / `0x782ef6`, page-root slot selection
`0xc428..0xc57e`, source capture `0x1393a`, compact queueing
`0xd3b2` / `0xd824`, or render bridge slot copy `0x1edc6`.

State classification:

- Canonical state: cursor `0x782c8a/0x782c8e`, margins `0x782dd6/0x782dda`,
  HMI/VMI `0x78315c/0x783160`, line-termination byte `0x78318f`, wrap byte
  `0x783190`, perforation skip `0x783191`, page/root state `0x78297a`, and
  pending span fields `0x783184..0x78318a`.
- Derived/cache state: source object `0x782d7e`, compact coordinates, queue
  key `0x782a7c`, previous-width latches, text-bottom/perforation limit
  `0x782dc2`, and render-band fields created after publication.
- Parser scratch: admitted control byte or six-byte parsed command record at
  `0x78299e`; those records are consumed by the terminal handler before
  page-object creation.
- Firmware bookkeeping: right-limit latch `0x782a57`, pending-width latch
  `0x782a58`, pending text/cursor latch `0x782a6d`, modified-layout byte
  `0x782ee1`, and publication retry/root flags.
- Hardware/external state: none for ROM-local direct-control decisions,
  except page-length zero/default can mirror paper-source state to
  `0x780e8f` / `0x780e26`; physical engine response is outside this
  checkpoint.
- Unknown: manual-facing latch names remain external. A new variant belongs
  here only when it changes one of the named cursor, span, page-object,
  bridge, or row-construction fields.

Evidence:

- Disassembly:
  `generated/disasm/ic30_ic13_control_code_handlers_00f02c.lst`,
  `generated/disasm/ic30_ic13_macro_environment_snapshot_helpers_00e65c.lst`,
  `generated/disasm/ic30_ic13_font_update_common_00c580.lst`,
  `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`,
  `generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`,
  `generated/disasm/ic30_ic13_hmi_vmi_handlers_00ca8c.lst`,
  `generated/disasm/ic30_ic13_dot_position_handlers_00f48c.lst`, and
  `generated/disasm/ic30_ic13_page_length_handler_00f9e8.lst`.
- Fixture anchors include `mixed printable/control page-record bridge renders
  post-CR glyph rows`, `LF parser trace feeds page-record queue`,
  `control stream ESC &k2G then FF applies CR+page-eject`,
  `HT/BS parser trace feeds page-record queue`,
  `live CR span flush materializes 0x12714 page object`,
  `left-margin parser span flush materializes 0x12714 page object`,
  `vertical-cursor parser span flush materializes 0x12714 page object`, and
  `ESC &d underline selector materializes span output`.

## Field Groups

Canonical placement state:

- `0x782c8a`: horizontal cursor consumed by printable text, HT, BS,
  `ESC &a#C/#H`, `ESC *p#X`, margin reset, and raster-start positioning.
- `0x782c8e`: vertical cursor consumed by LF, FF, `ESC &a#R/#V`,
  `ESC *p#Y`, `ESC =`, printable text bucketing, and raster-start
  positioning.
- `0x782dd6`: left/default margin copied into `0x782c8a` by CR helper
  `0xf06e`; written by `ESC &a#L` handler `0xeb58` and reset by `ESC 9`
  handler `0xe9ba`.
- `0x782dda`: right margin or horizontal limit written by `ESC &a#M`
  handler `0xec0c`, reset by `0xe9ba`, and consumed by HT plus horizontal
  commit helper `0xf4ca`.
- `0x78315c`: HMI/default horizontal motion written by `ESC &k#H` handler
  `0xca8c`, then consumed by HT, BS, margin commands, column positioning, and
  printable advance.
- `0x783160`: VMI/line advance written by `ESC &l#C/#D` handlers
  `0xcb00` and `0xc992`, then consumed by LF, FF, vertical positioning, VFC,
  `ESC =`, page length, and top-margin paths.

Canonical control modes:

- `0x78318f`: line-termination mode written by `ESC &k#G` handler `0xedf8`.
  CR `0xf02c` tests bit `7`, LF `0xf08c` tests bit `6`, and FF `0xf0f0`
  tests bit `5`.
- `0x783190`: end-of-line wrap flag written by `ESC &s#C` handler `0xedb0`.
  Selector `0` stores `1`, selector `1` clears it, and other selectors leave
  the byte unchanged. Printable prechecks `0xd28a` and `0xd6bc` consume the
  byte before deciding whether horizontal overflow rejects the glyph or
  recovers through `0xf054`.
- `0x783191`: perforation-skip byte written by `ESC &l#L` handler `0xee64`
  and consumed by `0xf36c`.

Canonical cursor stack:

- `0x782c96..0x782d36`: `ESC &f#S` cursor-stack storage.
- `0x782d36`: next-free stack pointer and upper bound.
- Selector `0` stores x plus `y + 0x782dbe`; selector `1` pops and restores
  x/y after active-extent clamps.

Canonical page and vertical bounds:

- `0x782db8`: horizontal page extent used by HT and `0xf4ca`.
- `0x782dba`: page length/vertical extent written by `0xf9e8`.
- `0x782dc2`: text-bottom/perforation limit consumed by `0xf36c`.
- `0x782dc6` and `0x782dca`: vertical upper and lower bounds used by
  `0xf6e2`.
- `0x782dce`: top offset used by FF helper `0xf124`, vertical positioning,
  VFC, and top-margin handling.

Derived/cache state:

- Compact text coordinates are derived from cursor state just before
  `0x12f2e` / `0x1387c` page-record queueing. Examples pinned by fixtures
  include `0x3b00` after CR+LF, `0x0a01` after HT/BS, `0x0600` after `ESC 9`
  plus CR, and `0x0001` after cursor-stack restore.
- `0x783a20`, `0x783a22`, and `0x783a28` are active-render band caches
  derived after publication by `0x1ed84`; they are not canonical cursor
  inputs.

Parser scratch:

- `0x78299e`: six-byte parsed command-record cursor rewound by handlers such
  as `0xca8c`, `0xeb58`, `0xec0c`, `0xf39e`, `0xf416`, `0xf560`, `0xf60a`,
  and `0xf75e`.
- Delayed payload state from `0x121cc` / `0x12218` is not part of CR/LF/FF
  handling, but direct-control streams share the same parser loop and host
  byte source before dispatch.

Firmware bookkeeping:

- `0x782a57`: right-limit latch set by right-margin and horizontal-position
  paths. `0xf06e`, `0xf2e6..0xf310`, and `0xf4ca` clear it when the
  committed cursor is no longer pinned to the right limit.
- `0x782a58`: pending previous-width latch. BS `0xf2a8..0xf310` sets it
  after backing up the horizontal cursor, shared flush helper `0xf34a` clears
  it before span publication, and printable text commits clear it after the
  next advance decision at `0xd24e` or `0xd680`.
- `0x782a5a`: latched previous text width. Printable text stores it at
  `0xd1c2` or `0xd5bc`; BS reads it at `0xf2c6` when alternate metrics byte
  `0x78318e` is set.
- `0x782a5c`: latched previous text advance. Printable text stores it at
  `0xd1b6` or `0xd5b6`; later printable advance uses it with
  `0x782a58/0x782a5a` to center the current source against the previous
  width.
- `0x782a6d`: pending text/cursor latch cleared by printable return paths and
  cursor-changing helpers including `0xf06e`, `0xf0b2`, `0xf124`,
  `0xf2e6..0xf310`, and `0xf4ca`; FF `0xf0f0` sets it to `0xff` after page
  eject helper `0xf124`.
- `0x783184`: pending text span flush enable tested by `0xf34a`.
- `0x783185`: underline/text-attribute y-offset selector written by
  `ESC &d` handler `0x12622` and consumed by span helpers `0xd4ac` /
  `0xd8fc`.
- `0x78318e`: alternate metric mode copied from font/context records by
  `0xc428`, `0xcbd4`, and `0x10220` paths. Printable advance, printable
  prechecks, and BS consume it at `0xd16a`, `0xd29e`, `0xd586`, `0xd6e0`,
  and `0xf2bc`.

Unknown:

- Manual-facing HP names for latches `0x782a57`, `0x782a58`, `0x782a5a`,
  `0x782a5c`, `0x782a6d`, `0x78318e`, and `0x783185` remain unknown. Their
  ROM-local roles above are not provisional for the cited handlers.
- Broader source-object variants should be added only when they expose new
  `0xd04a` field values, a new `0x12f2e` queueing shape, or different
  ROM-defined row-construction inputs. The existing direct-control byte
  streams already define the covered ROM contract from parsed command through
  page-record queueing and render entry.

## Writers

- `0xedf8` writes line-termination byte `0x78318f`. The bit map is
  `0 -> 0x00`, `1 -> 0x80`, `2 -> 0x60`, and `3 -> 0xe0`.
- `0xedb0` writes end-of-line wrap byte `0x783190` for `ESC &s#C`: absolute
  selector `0` enables wrap, selector `1` disables it, and all other selectors
  keep the previous mode.
- `0xf02c` handles CR by resetting x through `0xf06e`, flushing pending span
  state through `0xf34a`, and optionally calling LF helper `0xf0b2`.
- `0xf08c` handles LF by optionally applying CR-style x reset, then advancing
  y through VMI-scaled movement.
- `0xf0f0` handles FF by optionally applying CR-style reset, finalizing the
  page root, and marking page-eject pending state.
- `0xf1cc` handles HT by converting HMI `0x78315c` to whole units, advancing
  to the next eight-column stop relative to left margin `0x782dd6`, clamping
  against right margin/page width, and refreshing span metrics.
- `0xf2a8` handles BS by subtracting HMI or alternate previous-width state,
  clamping at the left margin or zero, setting previous-width latch
  `0x782a58`, and refreshing span metrics.
- `0xca8c` writes HMI `0x78315c` for accepted `ESC &k#H` values.
- `0xe9ba` implements `ESC 9` by clearing left margin, copying page width to
  the right margin, and clearing the right-margin fractional companion.
- `0xf176` implements `ESC =` by ensuring a page root, flushing pending span
  state, and advancing y by half the current VMI.
- `0xeb58` and `0xec0c` write left/right margins and can move `0x782c8a`.
- `0xf39e`, `0xf416`, and `0xf48c` write horizontal cursor state through
  helper `0xf4ca`.
- `0xf560`, `0xf60a`, and `0xf692` write vertical cursor state through helper
  `0xf6e2`.
- `0xcb00`, `0xc992`, `0xece2`, `0xea9e`, `0xee64`, and `0xf9e8` write VMI,
  vertical layout, perforation skip, text-bottom, and page-length state.
- `0xf75e` pushes or pops cursor-stack entries.
- `0x12622` tokenizes `ESC &d` underline/text-attribute commands and writes
  `0x783185` for the covered absolute `3D` selector path.

## Readers And Consumers

- `0xd04a` consumes current cursor, HMI, font context, and pending-width state
  to create the next text source object.
- `0xd28a` and `0xd6bc` consume `0x783190` inside the printable text
  prechecks. When horizontal overflow is detected, a clear flag returns
  precheck result `1` and suppresses queueing; a set flag calls `0xf054`,
  retries from the recovered cursor, and can return `0` so the glyph continues
  into the queue path.
- `0x12f2e`, `0x1387c`, and shared page-record storage consume compact
  coordinates derived from direct-control state.
- `0x12714` / `0x126e2` consume pending span state when CR, margin, vertical
  cursor movement, or underline terminal commands force a span publication.
- `0xf36c` consumes `0x782c8e`, `0x782dc2`, and `0x783191` to decide whether
  vertical overflow triggers page eject.
- `0x1edc6` bridges queued page-record text/span objects into render-record
  shape, and `0x1ed84` / `0x1ef6a` render the active band rows.
- Raster start consumes `0x782c8a` or `0x782c8e` depending on orientation, as
  documented in `notes/raster-graphics.md`.

## Printable Byte To Compact Object

The normal printable byte path is the first direct-control path that creates
page pixels from an ordinary host byte. It is not a fixture-only shortcut:
`0xd04a` builds source scratch, `0xd140` or `0xd550` advances and checks the
cursor, `0xd3b2` or `0xd824` positions the source, and `0x12f2e` writes the
compact bucket object later rendered through `0x1effe`.

Exact disassembly boundaries:

- `0xd04a..0xd0a8`: normalize the incoming printable value. Values above
  `0xff` call `0xd99a` and fall back to `0x7f` on failure; values above
  `0x7f` can be masked to seven bits when both high-character flags
  `0x783132/0x783133` are clear. Primary-context masking is wrapped by
  `0xc6b8` / `0xc68a`.
- `0xd0a8..0xd0e8`: call `0x1393a(host_byte, 0x782d7e)`, test source byte
  `+0x10`, branch to flagged path `0xd550` or unflagged path `0xd140`, clear
  printable bookkeeping byte `0x782a6d`, and return.
- `0xd0f0..0xd13e`: fixed-space printable helper. It builds source object
  `0x782d7e` for host space `0x20`, clears source longword `+0x04` before
  flagged handling when needed, then uses the same `0xd550` / `0xd140`
  branch and clears `0x782a6d`.
- `0xd140..0xd25e`: unflagged text advance. It calls precheck `0xd28a`,
  stores result `0x782a6e`, derives horizontal advance from source metrics,
  pending-width state, or HMI `0x78315c`, ensures current root `0x78297a`
  through `0x10084` when the source has drawable word `+0x0a`, and calls
  queue handoff `0xd3b2` when the precheck result is zero.
- `0xd25e..0xd288`: unflagged cursor commit. It clamps or wraps the local
  cursor candidate against text limits, writes `0x782c8a`, clears pending
  width flag `0x782a58`, and calls span update `0xd4ac` when queueing was not
  suppressed.
- `0xd3b2..0xd450`: unflagged queue handoff. It computes compact coordinates
  from current cursor, orientation byte `0x782da3`, printable offset
  `0x782dc0`, source record bytes, and context byte `+0x16`.
- `0xd450..0xd4aa`: unflagged source publication. It writes source words
  `+0x12/+0x14/+0x16`, marks page-root font-slot live byte
  `0x78297f + 0x78297e`, calls `0x12f2e`, and on allocation failure sets
  page-root flag bit `root+0x15.0`, publishes through `0xff1e`, ensures a
  fresh root through `0x10084`, and retries.
- `0xd550..0xd690`: flagged text advance. It calls precheck `0xd6bc`, stores
  result `0x782a6e`, derives advance from glyph/context metrics, pending-width
  state, or HMI `0x78315c`, ensures current root when source `+0x04` is
  nonzero, and calls queue handoff `0xd824` when the precheck result is zero.
- `0xd690..0xd6ba`: flagged cursor commit. It handles the same cursor-limit
  and pending-width state as `0xd140`, writes `0x782c8a`, clears
  `0x782a58`, and calls span update `0xd8fc` when queueing was not
  suppressed.
- `0xd824..0xd8a0`: flagged queue handoff. It computes compact coordinates
  from current cursor, source word `+0x08`, orientation byte `0x782da3`,
  printable offset `0x782dc0`, and glyph-entry words `+0x00/+0x02`.
- `0xd8a0..0xd8fa`: flagged source publication. It writes source words
  `+0x12/+0x14/+0x16`, marks page-root font-slot live byte
  `0x78297f + 0x78297e`, calls `0x12f2e`, and uses the same
  `0xff1e` / `0x10084` retry path as `0xd3b2` on allocation failure.
- `0x12f2e..0x12f6e`: compact object producer setup. It converts source words
  `+0x12/+0x14` into bucket/key state `0x782a7c` and packed coordinate word,
  and derives the low context selector from source word `+0x16`.
- `0x12f70..0x12fb8`: selector-shape decision. Flagged sources inspect the
  glyph-entry width word at source `+0x04 + 8`; unflagged sources inspect the
  low source width byte at source `+0x04`. Wide shapes set selector bit
  `0x1000`; row counts above `0x80` later set selector bit `0x2000`.
- `0x12fb8..0x13018`: allocate or reject the compact bucket object through
  `0x1387c`. Short objects request entry size `0x0a` and object size `0x26`;
  segmented objects request entry size `0x08` and object size `0x28`, adding
  eight to bucket/key state for each segment.
- `0x1301c..0x1303c`: segmented compact entry write. It appends glyph byte
  from source byte `+0x0b`, segment index, and packed coordinate word, then
  loops over remaining segments.
- `0x1303e..0x1306e`: short compact entry write. It appends glyph byte from
  source byte `+0x0b` and either a full coordinate word or its two coordinate
  bytes, depending on entry parity, then returns success.

### Printable Source Outcome Matrix

This matrix is the direct-control owner for a printable byte after parser
dispatch has selected `0xd04a` or an internal printable producer has selected
the fixed-space helper `0xd0f0`. It composes the byte normalization, source
record, placement branch, compact object, and delayed span consumer.

- Extended value service:
  when entry `D5 > 0xff`, `0xd04a..0xd070` calls `0xd99a`. A nonzero return
  exits before source record construction; a zero return replaces the value
  with `0x7f` and re-enters the normal printable path.
- High-bit printable normalization:
  when `0x80 <= D5 <= 0xff` and high-character flags `0x783132` and
  `0x783133` are both clear, `0xd084..0xd0a6` masks the byte to seven bits.
  If the selected text slot `0x782f06` is primary, the path calls SO handler
  `0xc6b8` before source capture and records a local restore flag; after
  placement it calls SI handler `0xc68a`.
- Source capture:
  `0xd0a8..0xd0b4` calls `0x1393a(host_byte, 0x782d7e)`. In
  `generated/disasm/ic30_ic13_display_list_helpers_013386.lst`,
  `0x1393a..0x1397a` selects `0x782f32/0x782ee6` or
  `0x783032/0x782ef6`, maps the host byte, writes source `+0x0a`, copies the
  selected context longword to source `+0x00`, and copies the context flag to
  source `+0x10`.
- Unflagged placement:
  source `+0x10 == 0` dispatches `0xd140 -> 0xd3b2 -> 0xd4ac`. The queue
  handoff writes source `+0x12/+0x14/+0x16`, marks live slot
  `0x78297f + 0x78297e`, calls `0x12f2e`, and then span consumer `0xd4ac`
  reads unflagged metric bytes `+0x2b/+0x2c/+0x2d` from the selected context.
- Flagged placement:
  source `+0x10 != 0` dispatches `0xd550 -> 0xd824 -> 0xd8fc`. The handoff
  writes the same source output fields and live slot, but derives placement
  from glyph-entry words and calls span consumer `0xd8fc`, which reads flagged
  metric words `+0x16/+0x18/+0x1a`.
- Precheck suppression:
  precheck result `0x782a6e != 0` skips the queue handoff. The handler still
  commits cursor state and clears pending-width flag `0x782a58`, but it does
  not call `0x12f2e` and therefore creates no compact page object for that
  byte.
- Allocation retry:
  if `0x12f2e -> 0x1387c` returns zero, both `0xd3b2` and `0xd824` set page
  root retry flag `root+0x15.0`, publish through `0xff1e`, ensure a fresh
  root through `0x10084`, and retry from the source publication point.
- Short compact object:
  when the selector-shape checks keep row count at or below `0x80`,
  `0x12ff4..0x1306e` requests object size `0x26`, appends source byte
  `+0x0b`, and stores the packed coordinate word as either a word or two
  bytes according to entry parity.
- Segmented compact object:
  when row count exceeds `0x80`, `0x12fc0..0x1303c` sets selector bit
  `0x2000`, requests object size `0x28`, emits segment entries containing
  source byte `+0x0b`, segment index, and packed coordinate word, and advances
  bucket/key state by eight per segment.

Field grouping for this route:

- Canonical state:
  selected text slot `0x782f06`, primary/secondary maps
  `0x782f32/0x783032`, primary/secondary current-font contexts
  `0x782ee6/0x782ef6`, current page root `0x78297a`, selected page-root slot
  `0x78297e`, live-slot bytes `0x78297f..`, compact bucket root `+0x1c`,
  source glyph byte `+0x0b`, positioned source words `+0x12/+0x14/+0x16`,
  and compact object payload entries.
- Derived/cache state:
  source scratch `0x782d7e`, source flag byte `+0x10`, high-character flags
  `0x783132/0x783133`, range caches `0x783134..0x78313c`, queue key
  `0x782a7c`, packed coordinate word, pending-width latch
  `0x782a58/0x782a5a/0x782a5c`, precheck result `0x782a6e`, and span
  watermarks `0x783184..0x78318a`.
- Parser scratch:
  the admitted printable byte and parser mode state before entry `0xd04a`.
  After `0x1393a`, compact object creation consumes source scratch rather
  than the parser record.
- Firmware bookkeeping:
  local SO/SI restore flag in `D4`, extended-value helper `0xd99a`, retry
  publication flag `root+0x15.0`, and post-printable latch `0x782a6d`.
- Unknown:
  no ROM-local middle edge remains for byte normalization, primary/secondary
  source selection, flagged/unflagged placement, short/segmented compact object
  creation, allocation retry, or span-consumer dispatch. Future printable work
  starts only from a stream that changes one of the fields above, an allocation
  outcome, or a compact-render helper input.

Evidence:
`generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`
`0xd04a..0xd8fc`,
`generated/disasm/ic30_ic13_display_list_helpers_013386.lst`
`0x1393a..0x13994`,
`generated/disasm/ic30_ic13_text_object_queue_012f2e.lst`
`0x12f2e..0x1306e`,
`generated/analysis/ic30_ic13_printable_text_path.md`,
`generated/analysis/ic30_ic13_text_cursor_span_flow.md`,
[font-context-metrics.md](font-context-metrics.md#printable-source-capture),
[page-record-storage.md](page-record-storage.md#page-assembly-decision-checkpoint),
and fixtures `plain printable parser trace feeds page-record queue`,
`host-fetched direct text/control streams feed 0x1ed84 and 0x1ef6a`,
`mixed printable/control parser trace feeds page-record queue`, `SO/SI
parser trace feeds selected context output`, `flagged printable d8fc
low-watermark flush renders span`, and `unflagged printable d4ac low-watermark
flush renders span`.

## Output Effect

### Line-Termination Route Checkpoint

This checkpoint composes `ESC &k#G` with the direct CR/LF/FF consumers. It
starts when parser dispatch reaches line-termination handler `0xedf8`, and it
ends at either the following printable object's compact coordinate or the page
publication edge reached by FF.

Route summary:

- `ESC &k#G` reaches `0xedf8`, which rewinds parser record cursor
  `0x78299e`, reads record word `+2`, normalizes negative selectors to their
  absolute value, and writes canonical line-termination mode byte `0x78318f`.
  Selector `0` writes `0x00`, selector `1` writes `0x80`, selector `2`
  writes `0x60`, and selector `3` writes `0xe0`.
- CR `0xf02c` always runs CR reset helper `0xf06e` and span helper `0xf34a`.
  It then consumes bit `0x78318f.7`; when set, CR also calls LF advance helper
  `0xf0b2`.
- LF `0xf08c` consumes bit `0x78318f.6`; when set, LF first calls
  `0xf06e` for CR-style horizontal reset. It then runs `0xf34a` and
  `0xf0b2`.
- FF `0xf0f0` consumes bit `0x78318f.5`; when set, FF first calls
  `0xf06e`. It then runs `0xf34a`, ensures a page root through `0x10084`,
  publishes through `0xf124 -> 0xff1e`, and writes pending page-eject latch
  `0x782a6d = 0xff`.

State classification for this route:

- Canonical state: line-termination byte `0x78318f`, horizontal cursor
  `0x782c8a`, vertical cursor `0x782c8e`, left margin `0x782dd6`, VMI
  `0x783160`, current page root `0x78297a`, and pending span fields consumed
  by `0xf34a`.
- Derived/cache state: printable compact coordinates after the next `0xd04a`,
  page-root publication records after `0xff1e`, and render-record copies
  created later by `0x1ed84` / `0x1edc6`.
- Parser scratch: six-byte `ESC &k#G` command record at `0x78299e`, the
  direct C0 byte that dispatches to `0xf02c`, `0xf08c`, or `0xf0f0`, and the
  following printable byte if present.
- Firmware bookkeeping: right-limit latch `0x782a57`, pending text/cursor
  latch `0x782a6d`, previous-width latch `0x782a58`, and span-enable byte
  `0x783184`.
- Unknown: no ROM-local middle edge remains for the documented
  line-termination selector map or CR/LF/FF consumers. Physical paper movement
  after publication is external.

Named byte-stream outcomes:

- `ESC &k1G!\r!` routes `0xedf8 -> 0xd04a -> 0xf02c -> 0xd04a`. The stored
  mode byte `0x80` makes CR reset x and apply LF/VMI before the second
  printable byte; the second compact coordinate is `0x3b00`, and bridge/render
  rows are downstream of the ordinary compact text path.
- `ESC &k2G!\n!` writes mode byte `0x60`, routes LF through `0xf08c`, applies
  CR+LF movement, and leaves the second printable byte to queue at compact
  coordinate `0x3b00`.
- `ESC &k2G!\f` writes mode byte `0x60`, routes FF through `0xf0f0`, applies
  CR-style horizontal reset, flushes spans, finalizes the current root through
  `0xff1e`, and sets pending page-eject state.
- `ESC &k3G` followed by CR, LF, and FF exercises all three stored mode bits:
  CR consumes bit `7`, LF consumes bit `6`, and FF consumes bit `5`.

Fixture names for these streams are listed in the evidence sections below;
they support the route above rather than defining it.

### HMI Route Checkpoint

This checkpoint composes `ESC &k#H` as a state-only horizontal-motion command.
It starts when parser dispatch reaches handler `0xca8c`, and it ends when a
later printable, HT, BS, margin, or cursor-position command consumes the stored
HMI.

Route summary:

- `ESC &k#H` and lowercase chaining form `ESC &k#h` reach terminal handler
  `0xca8c` through the normal parser table.
- `0xca8c..0xcaf2` rewinds parser record cursor `0x78299e`, reads integer
  word `+2` and fractional word `+4`, treats a negative integer as a signed
  integer/fraction pair by negating both words, and rejects integer values
  above `0x348`.
- Accepted values are scaled as HMI units: integer contribution
  `word(+2) * 30`, fractional contribution `word(+4) * 30 / 10000`, then
  helper `0x104d8` converts the sum before `0xcae4` stores packed HMI
  `0x78315c`.
- The command queues no page object. Its visible effect is delayed until
  consumers use `0x78315c`: printable source capture and placement in
  `0xd04a`, HT `0xf1cc`, BS `0xf2a8`, left/right margin writers
  `0xeb58` / `0xec0c`, and column-position handlers such as `0xf39e`.

State classification for this route:

- Canonical state: HMI/default horizontal motion word `0x78315c`, current
  horizontal cursor `0x782c8a`, margins `0x782dd6` / `0x782dda`, selected font
  context, and current page root `0x78297a` consumed later by printable text.
- Derived/cache state: compact coordinates produced by the next printable
  `0xd04a`, tab-stop candidates from `0xf1cc`, BS candidate x from `0xf2a8`,
  margin/cursor candidates from `0xeb58`, `0xec0c`, and `0xf39e`, and
  render-record copies after publication.
- Parser scratch: the six-byte `ESC &k#H/h` record and the parsed integer and
  fraction words consumed by `0xca8c`.
- Firmware bookkeeping: pending-width latches `0x782a58..0x782a5c`,
  alternate metric byte `0x78318e`, right-limit latch `0x782a57`, and pending
  text/cursor latch `0x782a6d`.
- Unknown: no ROM-local parser, HMI writer, delayed consumer, compact-object,
  or render-entry middle edge remains for the documented `ESC &k6H!!` route.
  New work should start only when a byte stream changes an HMI rejection case,
  consumer branch, page-object field, or row-construction input.

Named byte-stream outcome:

- `ESC &k6H!!` routes `0xca8c -> 0xd04a -> 0xd04a`. The accepted HMI value
  stores packed advance `15` in `0x78315c`; the second printable consumes that
  HMI and queues at compact coordinate `0x0501` through the ordinary compact
  text path.

`ESC &k0G HT BS !` routes `0xedf8`, `0xf1cc`, `0xf2a8`, and `0xd04a`. HT
advances x to `21`, BS backs it up to `20`, and the printable glyph queues at
compact coord `0x0a01` / pixel x `26`.

CR/LF/FF instruction boundaries:

- `0xedf8..0xee1e` rewinds the six-byte parser record, reads record word `+2`,
  and normalizes negative parameters to their absolute value before the
  line-termination selector map writes `0x78318f`. Generated flow
  `ic30_ic13_direct_control_code_flow.md` records the complete selector map:
  `0 -> 0x00`, `1 -> 0x80`, `2 -> 0x60`, and `3 -> 0xe0`.
- `0xf02c..0xf052` handles CR. It calls `0xf06e` to copy left margin
  `0x782dd6` into horizontal cursor `0x782c8a`, calls `0xf34a` to clear
  previous-width state and flush pending span output when enabled, then tests
  `0x78318f.7`. If that bit is set, CR also calls LF helper `0xf0b2`.
- `0xf054..0xf06c` is the unconditional CR+LF helper used by wrap recovery and
  display-functions CR post-handling. It runs `0xf06e`, `0xf34a`, and
  `0xf0b2` without consulting the line-termination mode byte.
- `0xf06e..0xf08a` is the CR reset helper. It writes
  `0x782c8a = 0x782dd6`, clears right-limit latch `0x782a57`, and clears
  pending text/cursor latch `0x782a6d`.
- `0xf08c..0xf0b0` handles LF. It tests `0x78318f.6`; when set, LF first
  calls `0xf06e` for CR-style horizontal reset. It always calls `0xf34a` and
  LF advance helper `0xf0b2`.
- `0xf0b2..0xf0ee` is the LF advance helper. It ensures a page root through
  `0x10084`, adds VMI `0x783160` to vertical cursor `0x782c8e` via `0x10518`,
  calls overflow/perforation helper `0xf36c`, optionally calls `0x1048c` when
  `0xf36c` returns nonzero, and clears `0x782a6d`.
- `0xf0f0..0xf122` handles FF. It tests `0x78318f.5`; when set, FF first
  calls `0xf06e`. It then calls `0xf34a`, ensures a page root through
  `0x10084`, calls page-eject helper `0xf124`, and writes
  `0x782a6d = 0xff` after the helper returns.
- `0xf124..0xf174` is the page-eject helper used by FF, VFC, macro/page
  finalize paths, and perforation overflow. It publishes the current root
  through `0xff1e`, derives a new vertical cursor from VMI `0x783160`,
  constants `0x12` and `0x19`, and top offset `0x782dce`, writes the result to
  `0x782c8e`, and clears `0x782a6d`.
- `0xf34a..0xf36a` is the shared span-flush helper. It clears
  previous-width latch `0x782a58`; when span-enable byte `0x783184` is
  nonzero, it materializes the pending span through `0x12714` and resets the
  span state through `0x126e2`.
- `0xf36c..0xf39c` is the vertical overflow/perforation helper. It compares
  text-bottom/perforation limit `0x782dc2` against vertical cursor
  `0x782c8e`; when the limit is nonzero, exceeded, and perforation-skip byte
  `0x783191` is set, it calls `0xf124` and returns `D7 = 0`. Otherwise it
  returns `D7 = 1`.

HT/BS instruction boundaries:

- `0xf1cc..0xf1e2` reads HMI `0x78315c` and converts it through `0x104fe`.
  If the converted HMI is zero, the handler returns immediately with no cursor
  write and no span refresh.
- `0xf1e4..0xf1f8` selects horizontal cursor `0x782c8a` and left margin
  `0x782dd6`. If current x is left of the margin, HT commits the margin as the
  new x through the shared commit path at `0xf26a`.
- `0xf202..0xf24c` subtracts left margin from current x, converts to whole
  HMI columns, rounds the column count up to the next multiple of eight, scales
  it back through HMI, adds the left margin, and leaves the candidate in `D4`.
- `0xf24e..0xf288` clamps the HT candidate against right margin `0x782dda`.
  If current x is already beyond the right margin, the clamp limit becomes page
  width `0x782db8 << 16`; otherwise it is the right margin.
- `0xf26a..0xf2a4` commits HT x to `0x782c8a`, selects the active font context
  from `0x782ee6 + 16 * byte(0x782f06)`, and refreshes span metrics through
  `0xd8fc` for flagged contexts or `0xd4ac` otherwise.
- `0xf2a8..0xf2e4` handles BS setup. It ensures a page root through `0x10084`,
  reads current x, then subtracts either latched previous-width word
  `0x782a5a << 16` when alternate metrics byte `0x78318e` is set, or HMI
  `0x78315c` otherwise.
- `0xf2e6..0xf310` clamps BS: if current x was at or beyond left margin and
  the candidate crosses below it, the candidate becomes left margin; any
  negative candidate is clamped to zero. The committed x is written to
  `0x782c8a`, previous-width latch `0x782a58` is set, and right-limit and
  pending-cursor latches `0x782a57` / `0x782a6d` are cleared.
- `0xf316..0xf342` uses the same active-context selection as HT and refreshes
  span metrics through `0xd8fc` or `0xd4ac`. Neither HT nor BS queues a compact
  object; the following printable byte consumes the committed x in `0xd04a`.

`ESC &s#C` has no immediate page object, but it changes the acceptance boundary
for later printable text. Disassembly `0xedb0..0xedf6` rewinds the parsed
record, normalizes the absolute selector, and writes only selectors `0` and
`1`. Fixture `0xedb0 ESC &s#C toggles end-of-line wrap for selectors 0 and 1
only` pins the command byte. Fixture `0xd28a and 0xd6bc prechecks share
continue reject and wrap decisions` then pins the downstream effect: horizontal
overflow with `0x783190` clear returns precheck result `1`, while the same
overflow with `0x783190` set calls `0xf054`, retries from recovered x `0`, and
returns `0` when the retried placement fits. Vertical extent failure still
returns `1`.

The plain and HMI parser streams share the baseline consumer path. A printable
byte reaches `0xd04a`, queues a compact text object through `0x1387c`, and
survives bridge/render entry. The HMI stream differs only before that shared
path: `0xca8c` writes `0x78315c`, and the following printable consumes the new
HMI to change compact coordinates without changing the downstream page-record
contract.

### Margin Route Checkpoint

This checkpoint composes `ESC 9`, `ESC &a#L`, and `ESC &a#M` as horizontal
layout commands. It starts at handlers `0xe9ba`, `0xeb58`, or `0xec0c`, and it
ends when CR, HT, BS, wrap prechecks, pending-span flush, or a following
printable byte consumes the rewritten margin state.

Route summary:

- `ESC 9` reaches `0xe9ba`. It clears left margin `0x782dd6`, copies page
  width `0x782db8` to right margin `0x782dda`, and clears right-margin
  fraction companion `0x782ddc`. It queues no page object.
- `ESC &a#L` reaches `0xeb58`. It rewinds parser record cursor `0x78299e`,
  converts the absolute column count through current HMI `0x78315c`, rejects
  values beyond `0x782dda - HMI`, and writes accepted values to left margin
  `0x782dd6`. If the accepted margin is right of current x `0x782c8a`, or
  pending text is marked, it also moves x and can flush pending spans through
  `0xf34a -> 0x12714 -> 0x126e2`.
- `ESC &a#M` reaches `0xec0c`. It converts `abs(parameter) + 1` columns
  through HMI `0x78315c`, rejects values before `0x782dd6 + HMI`, clamps
  beyond page width `0x782db8`, writes right margin `0x782dda`, sets
  right-limit latch `0x782a57`, and can move current x left.
- CR helper `0xf06e` later copies left margin `0x782dd6` into cursor x
  `0x782c8a`; HT `0xf1cc` and BS `0xf2a8` use the margins as tab-stop and
  clamp bounds; printable prechecks `0xd28a` / `0xd6bc` use the right margin
  and wrap byte to accept, reject, or recover horizontal overflow.

State classification for this route:

- Canonical state: left margin `0x782dd6`, right margin `0x782dda`,
  right-margin fraction companion `0x782ddc`, horizontal cursor `0x782c8a`,
  HMI `0x78315c`, page width `0x782db8`, current page root `0x78297a`, and
  pending span state.
- Derived/cache state: CR-reset x, HT tab-stop candidate, BS clamp candidate,
  compact coordinates from the next printable byte, and segment-list span
  objects materialized before a margin/cursor overwrite.
- Parser scratch: six-byte `ESC &a#L/#M` records, lowercase `l...M` family
  chaining state, and parsed integer/fraction words consumed by `0xeb58` or
  `0xec0c`.
- Firmware bookkeeping: right-limit latch `0x782a57`, pending cursor/text
  latch `0x782a6d`, pending-width latch `0x782a58`, span-enable byte
  `0x783184`, and publication/retry state only if a span flush allocates or
  publishes through `0x12714`.
- Unknown: no ROM-local middle edge remains for the documented margin reset,
  left/right margin writers, following-printable consumers, or pending-span
  materialization. New work should start only when a byte stream changes a
  margin rejection branch, span object, page-object coordinate, or render
  helper input.

Named byte-stream outcomes:

- `ESC 9 CR !` has visible effect only through later text: `0xe9ba` clears
  left margin to `0`, copies page width `120` into right margin, CR moves x
  from packed `50` to `0`, and the printable byte queues at compact coordinate
  `0x0600`.
- `ESC &a1L!`, `ESC &a1M!`, and `ESC &a6l9M!` route margin handlers
  `0xeb58` / `0xec0c` into following `0xd04a` output at compact coordinates
  `0x0801`, `0x0a02`, and `0x0207`.
- `ESC &a6L!` with pending span state shows the left-margin writer can
  materialize selector-`0x4000` segment-list output through `0x12714` before
  the following printable glyph queues.

### Half-Line Feed Route Checkpoint

This checkpoint composes `ESC =` as a vertical placement command. It starts
when parser dispatch reaches handler `0xf176`, and it ends when a later
printable, raster-start, rectangle/rule, VFC, or publication path consumes the
shifted vertical cursor.

Route summary:

- `ESC =` reaches `0xf176..0xf1ca` from the normal parser table.
- `0xf176` first ensures a current page root through `0x10084` and flushes
  pending span state through `0xf34a`.
- `0xf186..0xf19c` reads VMI `0x783160`, converts the packed value to signed
  subunits through `0x104fe`, halves that signed count, and converts the half
  step back to packed cursor form through `0x104d8`.
- `0xf19e..0xf1ac` adds the half-step to current vertical cursor `0x782c8e`
  through `0x10518` and stores the result back to `0x782c8e`.
- `0xf1b2..0xf1c2` runs vertical overflow/perforation helper `0xf36c`; if
  that helper returns nonzero, `0xf176` also calls `0x1048c`.
- `0xf1c2` clears pending text/cursor latch `0x782a6d`. The handler creates no
  compact text object, rule object, raster object, or pixels by itself.

State classification for this route:

- Canonical state: VMI `0x783160`, vertical cursor `0x782c8e`, current page
  root `0x78297a`, and pending span fields consumed by `0xf34a`.
- Derived/cache state: signed half-VMI subunit count, packed half-step from
  `0x104d8`, compact coordinates from the next printable byte, and any
  render-record copies created after later publication.
- Parser scratch: the `ESC =` parser dispatch row and transient stack
  arguments to coordinate helpers `0x104fe`, `0x104d8`, and `0x10518`.
- Firmware bookkeeping: pending text/cursor latch `0x782a6d`,
  overflow/perforation helper state from `0xf36c`, optional `0x1048c` recovery,
  and span-flush bookkeeping if `0xf34a` materializes pending output.
- Unknown: no ROM-local middle edge remains for the documented half-line feed
  writer or following-printable consumer. Physical paper motion after later
  publication remains external.

Named byte-stream outcome:

- `ESC = !` advances y from packed `21` to `22.6`, then the following
  printable byte consumes the shifted cursor through `0xd04a` and queues at
  compact coordinate `0x1001`.

`ESC &f0S ESC &a2C ESC &f1S!` proves cursor-stack state reaches visible
output. Fixture `cursor stack parser trace feeds page-record queue` routes
`0xf75e`, `0xf39e`, `0xf75e`, and `0xd04a`; the pop restores the original
cursor before the glyph queues at compact coord `0x0001`.

The direct helper fixtures bound the cursor-stack internals before visible
output: `0xf75e ESC &f0S pushes cursor with vertical offset`,
`0xf75e ESC &f1S pops cursor and clears pending flags`, and
`0xf75e cursor stack bounds and pop clamps to current extents` pin the stored
entry format, pointer bounds, vertical-offset subtraction, and clamp rules.

### Cursor Stack State Checkpoint

This checkpoint composes `ESC &f#S` as a state-only placement command with
later page-output consumers. It starts at parser terminal handler `0xf75e` and
ends when the restored cursor is consumed by printable text, raster start, or
rectangle/rule fill.

Route:

- Parser mode `17` for `ESC &f` dispatches `S/s` to `0xf75e`.
- `0xf766..0xf784` rewinds parser record cursor `0x78299e`, reads the parsed
  word at record `+2`, sign-extends it, and uses its absolute value as the
  cursor-stack selector.
- Selector `0` pushes when the next-free pointer stored at `0x782d36` is below
  literal upper-bound address `0x782d36`: it stores horizontal cursor
  `0x782c8a` and stores vertical cursor `0x782c8e + (0x782dbe << 16)` as an
  eight-byte entry under `0x782c96..0x782d36`.
- Selector `1` pops when the pointer is above base `0x782c96`: it restores x
  and y, subtracts `0x782dbe << 16` from stored y, clamps both positions to
  current extents minus the ROM's `1/12` guard, clears right-limit and
  pending-cursor latches, and flushes pending spans when `0x783184` is set.
- Other selectors, full-stack pushes, and empty-stack pops return without page
  output or stack mutation.

State grouping:

- Canonical state: stack storage `0x782c96..0x782d36`, next-free pointer
  `0x782d36`, cursor `0x782c8a/0x782c8e`, vertical offset source
  `0x782dbe`, page extents `0x782db8/0x782dc6`, and pending span state
  `0x783184..0x78318a`.
- Derived/cache state: stored y with vertical offset already added, popped y
  after subtracting that offset, and clamped x/y candidates.
- Parser scratch: the six-byte `ESC &f#S` command record rewound by
  `0xf75e`.
- Firmware bookkeeping: latch clears for `0x782a57` and `0x782a6d`, stack
  pointer movement, and optional span flush through `0xf34a` /
  `0x12714 -> 0x126e2`.
- Unknown: no ROM-local cursor-stack field is unknown for the documented
  push/pop, full-stack, empty-stack, clamp, and following-printable paths.

Readers and output effect:

- Cursor stack commands do not queue page objects or draw pixels by
  themselves.
- Printable text consumes the restored cursor through
  `0xd04a -> 0x1393a -> 0x12f2e`. The worked stream
  `ESC &f0S ESC &a2C ESC &f1S !` proves the intervening cursor move is undone
  before the printable queues at compact coordinate `0x0001`.
- Raster start `0x1075a` consumes the same cursor state as its origin source:
  portrait uses horizontal cursor `0x782c8a`, while landscape uses vertical
  cursor `0x782c8e`.
- Rectangle/rule clip helper `0x10b80` consumes cursor
  `0x782c8a/0x782c8e` as the rectangle origin before clipping and queueing a
  rule object through `0x13386 -> 0x133aa`.

Evidence:

- Disassembly:
  `generated/disasm/ic30_ic13_dot_position_handlers_00f48c.lst` for
  `0xf75e`, `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`,
  `generated/disasm/ic30_ic13_raster_handlers_0105d0.lst`, and
  `generated/disasm/ic30_ic13_rectangle_graphics_010898.lst`.
- Checked-in owners:
  [raster-graphics.md](raster-graphics.md#start-and-end-raster),
  [rectangle-graphics.md](rectangle-graphics.md#clip-and-queue-at-0x10b80),
  and this note's printable-output contract.
- Fixture anchors:
  `0xf75e ESC &f0S pushes cursor with vertical offset`,
  `0xf75e ESC &f1S pops cursor and clears pending flags`,
  `cursor stack stream ESC &f0S / ESC &f1S selects 0xf75e push/pop`,
  `0xf75e cursor stack bounds and pop clamps to current extents`, and
  `cursor stack parser trace feeds page-record queue`.

Unresolved boundary:

- No ROM-local middle edge remains for the documented cursor-stack writer,
  stack pointer, pop clamp, following-printable consumer, raster-origin
  consumer, or rectangle-origin consumer. New cursor-stack work should start
  only from byte streams that change stack entry bytes, clamp extents,
  pending-span output, following page-object fields, or render-helper inputs.

The cursor-position helper fixtures pin the conversion layer that feeds those
visible page-record streams. `0xf39e ESC &a#C converts columns through HMI and
relative flag` and `0xf416 ESC &a#H converts decipoints and clamps horizontal
cursor` cover the horizontal `ESC &a` family. `0xf560 ESC &a#R uses VMI with
absolute top offset and relative cursor base` and `0xf60a ESC &a#V converts
decipoints and clamps vertical cursor` cover the vertical family. Fixture
`cursor position stream ESC &a3.5c+1R selects 0xf39e then 0xf560` pins
lowercase chaining across horizontal and vertical handlers. Fixture
`0xf48c/0xf692 ESC *p#X/#Y use whole-dot packed cursor commits` covers the
dot-position siblings. The parser-to-page-record fixtures named above then
carry each converted cursor state through the following printable byte.

Shared coordinate helper boundaries:

- `0x104d8..0x104ee` converts a signed long subunit count into the packed
  cursor form used by `0x782c8a`, `0x782c8e`, HMI/VMI, rectangle decipoints,
  and raster origins. It first clamps the input through `0x104f0` to
  `-0x5ffff..0x5ffff`, divides by `12`, swaps the quotient/remainder into
  packed whole/fraction order, and normalizes negative remainders by borrowing
  one whole unit and adding `12` subunits through the `0x10548` fixup.
- `0x104f0..0x104fc` is the signed clamp helper. Callers supply the absolute
  clamp limit in `D6`; the helper clamps `D7` to `[-D6, +D6]`.
- `0x104fe..0x1050e` converts a packed whole/fraction pair back to signed
  subunits by multiplying the whole word by `12` and adding the fraction word.
  HT, cursor arithmetic, default line-spacing conversion, and page-layout math
  consume this form when they need integer subunit counts.
- `0x10510..0x1054e` is the shared add/subtract helper for packed
  whole/fraction pairs. Entry `0x10510` negates the second pair before
  falling into `0x10518`, so callers use it for subtraction. Entry `0x10518`
  adds whole words, clamps the whole part through `0x104f0` with limit
  `0x7ffe`, adds fraction words, carries fractions `>= 12` into the whole
  word, and borrows for negative fractions through the same `0x10548` fixup.
- `0x10550..0x10560` is a derived projection helper used by later layout
  code: it shifts its input right by two, multiplies the low word by `12`,
  swaps the product, and returns the high word in `D7`. Existing consumers use
  it as derived coordinate/cache math, not as parser state.

The coordinate helpers write no RAM by themselves. Their output becomes
canonical only when a caller stores the returned packed value into fields such
as `0x782c8a`, `0x782c8e`, `0x78315c`, `0x783160`, `0x78316a`, or
`0x783166`; otherwise it is scratch in `D7`.

Cursor commit helper boundaries:

- `0xf39e..0xf414`: `ESC &a#C` rewinds the parsed record, converts the integer
  and fractional parameter through current HMI `0x78315c`, reads record bit `0`
  as the relative flag, and calls horizontal commit helper `0xf4ca`.
- `0xf416..0xf48a`: `ESC &a#H` converts decipoints with multiplier `5` and
  denominator `10000`, reads record bit `0` as the relative flag, and calls
  `0xf4ca`.
- `0xf48c..0xf4c8`: `ESC *p#X` sign-extends the parsed word, shifts it left
  by 16 into a whole-dot packed x coordinate, reads record bit `0`, and calls
  `0xf4ca`.
- `0xf4ca..0xf55e`: horizontal commit. If the relative flag is set,
  `0xf4dc..0xf4ec` adds the candidate to current x `0x782c8a`. The helper then
  clamps negative values to zero, clamps values above page width `0x782db8`,
  writes `0x782c8a`, sets right-limit latch `0x782a57` only when the committed
  x equals right margin `0x782dda`, clears pending latch `0x782a6d`, and
  refreshes span metrics through `0xd8fc` or `0xd4ac` according to selected
  context byte `+4`.
- `0xf560..0xf608`: `ESC &a#R` ensures a page root, adds firmware absolute-row
  bias `0x1c20` when record bit `0` is clear, converts the integer and
  fractional parameter through VMI `0x783160`, calls vertical commit helper
  `0xf6e2`, then applies relative overflow recovery or absolute upper clamp
  against `0x782dc6`.
- `0xf60a..0xf690`: `ESC &a#V` converts decipoints with multiplier `5` and
  denominator `10000`, calls `0xf6e2`, and clamps committed y to `0x782dc6`.
- `0xf692..0xf6e0`: `ESC *p#Y` sign-extends the parsed word, shifts it left
  by 16 into a whole-dot packed y coordinate, calls `0xf6e2`, and clamps to
  `0x782dc6`.
- `0xf6e2..0xf75c`: vertical commit. The helper ensures a page root, clears
  pending latch `0x782a6d`, flushes pending spans through `0xf34a`, adds the
  candidate to current y `0x782c8e` for relative moves or to top offset
  `0x782dce` for absolute moves, clamps below lower bound `0x782dca`, writes
  `0x782c8e`, optionally materializes span output through `0x12714` /
  `0x126e2` when `0x783184` is set, and returns the committed y in `D7`.

The output effect of this cluster is delayed until a later printable byte,
raster start, rectangle, VFC jump, or page publication consumes the committed
cursor fields. For text streams, the following printable byte reaches
`0xd04a`, derives compact coordinates from `0x782c8a` / `0x782c8e`, queues
through `0x12f2e` / `0x1387c`, and renders through the normal page-record
bridge.

The margin helper fixtures named in the evidence list support the route above:
they exercise helper admission/rejection, lowercase chaining, following
printable output, and the `0x12714` span-materialization sibling.

### Cursor And Dot Position Route Checkpoint

This checkpoint composes `ESC &a#C/#H/#R/#V` and `ESC *p#X/#Y` as cursor
placement commands. It starts at parser terminal handlers `0xf39e`, `0xf416`,
`0xf560`, `0xf60a`, `0xf48c`, or `0xf692`, and it ends when a later printable,
raster-start, rectangle/rule, VFC, or publication path consumes the committed
cursor fields.

Route summary:

- Horizontal column command `ESC &a#C` reaches `0xf39e`, converts the parsed
  integer and fraction through current HMI `0x78315c`, uses parsed-record bit
  `0` as the relative flag, and commits through `0xf4ca`.
- Horizontal decipoint command `ESC &a#H` reaches `0xf416`, converts through
  the five-subunit decipoint scale, uses the same relative flag, and commits
  through `0xf4ca`.
- Horizontal dot command `ESC *p#X` reaches `0xf48c`, sign-extends the parsed
  word, shifts it into whole-dot packed coordinate form, uses the relative
  flag, and commits through `0xf4ca`.
- Vertical row command `ESC &a#R` reaches `0xf560`, ensures a page root, adds
  the ROM absolute-row bias when the relative flag is clear, converts through
  VMI `0x783160`, and commits through `0xf6e2` before relative overflow
  recovery or absolute upper clamp.
- Vertical decipoint command `ESC &a#V` reaches `0xf60a`, converts through the
  five-subunit decipoint scale, commits through `0xf6e2`, and clamps to
  vertical bound `0x782dc6`.
- Vertical dot command `ESC *p#Y` reaches `0xf692`, sign-extends the parsed
  word, shifts it into whole-dot packed coordinate form, commits through
  `0xf6e2`, and clamps to `0x782dc6`.
- Horizontal commit `0xf4ca` writes canonical x cursor `0x782c8a`, updates
  right-limit latch `0x782a57`, clears pending latch `0x782a6d`, and refreshes
  span metrics through `0xd8fc` or `0xd4ac`.
- Vertical commit `0xf6e2` ensures a page root, clears pending latch
  `0x782a6d`, flushes pending spans through `0xf34a`, writes canonical y
  cursor `0x782c8e`, and can materialize selector-`0x4000` segment-list
  output through `0x12714 -> 0x126e2` before the cursor move takes effect.

State classification for this route:

- Canonical state: x/y cursors `0x782c8a` / `0x782c8e`, HMI `0x78315c`, VMI
  `0x783160`, top offset `0x782dce`, vertical bounds `0x782dc6` /
  `0x782dca`, page width `0x782db8`, right margin `0x782dda`, current page
  root `0x78297a`, and pending span fields `0x783184..0x78318a`.
- Derived/cache state: packed coordinate candidates, relative-add results,
  decipoint and whole-dot conversions, compact coordinates from later
  printable output, raster origin words, rectangle/rule source coordinates,
  and render-record copies after publication.
- Parser scratch: mode `12` lowercase chaining state, six-byte command records
  at `0x78299e`, parsed numeric parameters, and parsed-record bit `0` used as
  the relative flag.
- Firmware bookkeeping: latches `0x782a57`, `0x782a58`, and `0x782a6d`,
  selected-context refresh through `0xd8fc` / `0xd4ac`, span re-arm state from
  `0x126e2`, allocation cursors if `0x12714` materializes a span, and later
  publication flag `0x782996`.
- Unknown: no ROM-local middle edge remains for the documented cursor/dot
  writer, commit helper, following-printable consumer, raster-origin consumer,
  rectangle-origin consumer, or span-flush sibling. New work should start only
  when a stream changes a clamp/recovery branch, page-object bytes, span object
  shape, or render-helper input.

Named byte-stream outcomes:

- `ESC &a2C!`, `ESC &a72H!`, `ESC &a1R!`, `ESC &a72V!`, and
  `ESC &a2c+1R!` commit cursor state and leave the following printable byte to
  queue compact coordinates `0x0a02`, `0x0402`, `0x1001`, `0x9001`, and
  `0x1a02`.
- `ESC *p30x30Y!` routes dot-position handlers `0xf48c` and `0xf692`, commits
  whole-dot packed coordinates, and leaves the following printable byte to
  queue compact coordinate `0x9402`.
- `ESC &a1R!` with pending span state shows the vertical cursor handler can
  materialize selector-`0x4000` segment-list output through `0x12714` before
  the following printable glyph is queued.

The cursor-position helper fixtures named in the evidence list support this
route by exercising unit conversion, relative flags, clamps, lowercase
chaining, dot-position commits, following printable output, and the
`0x12714` span-materialization sibling.

### Span Flush Producers

Several direct-control handlers are not just cursor writers. Before they
overwrite cursor/span bounds, they call `0xf34a`, which can materialize the
pending text span through `0x12714` and `0x126e2`. The shared object produced
by the covered portrait cases is:

```text
00 00 00 00 40 00 00 01 32 00 03 00 00 10
```

That is a segment-list object in page-root bucket `0` with selector `0x4000`,
one entry, packed key `0x3200`, y `3`, and extent `16`.

Producer cases:

- CR path: fixture `live CR span flush materializes 0x12714 page object`
  drives `ESC &k1G!\r` through `0xedf8`, `0xd04a`, and `0xf02c`. The printable
  first queues compact object `00 00 00 00 00 00 00 01 20 00 01`, then CR
  materializes pending span state `x=2..18, y=3`, inserts the selector-`0x4000`
  segment-list object ahead of the compact object in bucket `0`, re-arms
  `0x783186` and `0x783188` to x `5`, and renders the span rows beside the
  text glyph.
- Left-margin path: fixture
  `left-margin parser span flush materializes 0x12714 page object` drives
  host-fetched `ESC &a6L!` through parser handlers `0xeb58` and `0xd04a`.
  Handler `0xeb58` moves `0x782c8a` from packed `10` to packed `108`, flushes
  the same pending span object, re-arms span bounds to x `108`, and the
  following printable queues compact coord `0x0207`.
- Vertical-cursor path: fixture
  `vertical-cursor parser span flush materializes 0x12714 page object` drives
  host-fetched `ESC &a1R!` through parser handlers `0xf560` and `0xd04a`.
  Handler `0xf560` flushes the span before moving y to packed `95.1`, re-arms
  span bounds to x `10`, and the following printable queues compact coord
  `0xa001` in bucket `4`, leaving bucket `0` for the already materialized span
  rows.
- Underline/text-attribute path: fixture
  `ESC &d underline selector materializes span output` drives
  `ESC &d3D! ESC &d@` through `0x12622`, `0xd04a`, and `0x12622`. Selector
  `3D` writes `0x783185 = 1`, printable output lets the flagged text source
  update span high-y through alternate offset word `+0x1a`, and final `&d@`
  flushes selector-`0x4000` span object
  `00 00 00 00 40 00 00 01 3a 00 03 00 00 12`.

Underline/text-attribute instruction boundaries:

- `0x12622..0x12636` enters the local `ESC &d` handler, calls command combiner
  `0xdaf0` to tokenize the current six-byte record, then fetches one lookahead
  byte through parser wrapper `0xda9a`.
- `0x12638..0x12654` treats lookahead `W` or `w` as a generic counted-payload
  boundary by scheduling delayed handler `0x1228a` through `0x121cc`. This
  matches the stateful tokenizer helpers even though normal underline streams
  do not use a payload.
- `0x12654..0x12664` keeps lowercase finals in `0x60..0x7e` inside the `&d`
  family by looping back to `0xdaf0`. Uppercase or non-lowercase finals leave
  the loop.
- `0x12666..0x1266c` handles non-`W/w` lookahead by rewinding
  `0x78299e` by one six-byte record, so the terminal logic acts on the record
  already parsed by `0xdaf0`.
- `0x1266e..0x1268c` accepts terminal bytes `0x40..0x5e`; other values are
  reported through `0x9ec0` and return without changing span state.
- `0x1268e..0x126a0` restores any delayed payload through `0x12218`, then
  uses final-byte bit 2 as the split. If bit 2 is clear, the handler calls
  `0x12714` to flush pending span state and returns. The covered `ESC &d@`
  stream takes this terminal flush path.
- `0x126a2..0x126a8` is the selector-write guard. If span enable byte
  `0x783184` is already nonzero, the handler returns without changing
  selector byte `0x783185`.
- `0x126aa..0x126d4` reads the parsed parameter word from the current
  six-byte record, normalizes it to an absolute value, and writes
  `0x783185 = 1` only for final byte `D` with parameter `3`. Other accepted
  selector terminals write `0x783185 = 0`.
- `0x126da..0x126e0` calls `0x126e2` after a selector write. `0x126e2`
  initializes pending span state only when `0x783184` was clear: it writes
  `0x783184 = 1`, seeds low/high x words `0x783186` and `0x783188` from
  current horizontal cursor word `0x782c8a`, and clears high-y word
  `0x78318a`.

State classification for this cluster:

- canonical: pending span fields `0x783184`, `0x783186`, `0x783188`, and
  `0x78318a`; cursor fields `0x782c8a` / `0x782c8e`; segment-list object fields
  class byte `0x40`, count `+0x06`, key `+0x08`, y `+0x0a`, and extent
  `+0x0c`;
- derived/cache: packed compact coordinates such as `0x0207` and `0xa001`,
  plus the `0x12714` bucket/key result `0x3200`;
- parser scratch: normal six-byte records for `ESC &k#G`, `ESC &a#L`,
  `ESC &a#R`, and `ESC &d#D`; no delayed-payload state participates;
- firmware bookkeeping: re-armed span bounds after `0x126e2`, publication
  counters in the fixture harness, and page-root allocation state from
  `0x10084`;
- unknown: no ROM-local middle edge remains for these producers. Broader work
  should add only cursor/font/span variants that change the object bytes,
  bucket choice, bridge state, or row-construction inputs.

`ESC &d3D! ESC &d@` proves underline/text-attribute state crosses into the
same span machinery. Fixture `ESC &d underline selector materializes span
output` writes `0x783185 = 1`, lets the printable update the flagged text
span through alternate offset fields, and flushes a selector-`0x4000` span
object beside the compact glyph.

### Underline And Span Outcome Matrix

This matrix is the direct-control owner checkpoint for `ESC &d` and the shared
pending-span flush path. It starts at parser dispatch to `0x12622`, includes
the printable span consumers that update pending bounds, and ends at
segment-list or fixed-list page objects consumed by render entry.

- Selector write:
  `ESC &d#D` reaches `0x12622`. The handler tokenizes with `0xdaf0`, fetches
  the lookahead byte through `0xda9a`, rewinds `0x78299e` for non-`W/w`
  lookahead, restores pending delayed payload state through `0x12218`, and
  writes selector byte `0x783185`. Parameter `3` with final byte `D` writes
  `0x783185 = 1`; other accepted selector terminals write `0`. It then calls
  `0x126e2`, which arms pending span byte `0x783184`, seeds low/high x words
  `0x783186` / `0x783188` from cursor x `0x782c8a`, and clears high-y word
  `0x78318a`.
- Generic payload boundary:
  `0x12638..0x12654` treats `W/w` lookahead as a counted payload command by
  scheduling generic drain handler `0x1228a` through `0x121cc`. This is
  parser bookkeeping for the `&d` family; the normal underline streams covered
  here do not image a binary payload.
- Printable span update:
  After the selector is armed, a printable byte reaches
  `0xd04a -> 0x1393a`. The flagged source path uses
  `0xd550 -> 0xd824`, queues the compact glyph through `0x12f2e`, and then
  calls span consumer `0xd8fc` when `0x783184` is set. With selector
  `0x783185 = 1`, `0xd8fc` uses selected-context offset word `+0x1a` while
  updating pending span bounds `0x783186..0x78318a`.
- Terminal flush:
  Accepted final bytes whose bit 2 is clear take `0x1268e..0x126a0`; after
  `0x12218`, `0x12622` calls `0x12714`. The covered `ESC &d@` stream uses
  this path to convert pending bounds into a page object.
- Cursor/control flush:
  CR `0xf02c`, left margin `0xeb58`, and vertical cursor handler `0xf560`
  can flush the same pending span through `0xf34a -> 0x12714 -> 0x126e2`
  before changing the cursor boundary that defines the span. The output object
  is therefore tied to the pre-move span bounds, while `0x126e2` re-arms
  bounds for following text at the post-move cursor.
- Portrait page object:
  In portrait orientation, `0x12714 -> 0x13520 -> 0x135f0` stores
  selector-`0x4000` segment-list objects under page-root bucket `+0x1c`. The
  covered underline stream flushes object bytes
  `00 00 00 00 40 00 00 01 3a 00 03 00 00 12`: class byte `0x40`, one entry,
  packed key `0x3a00`, y `3`, and extent `18`.
- Landscape/fixed-list page object:
  In landscape orientation, the same pending source reaches `0x136d2` and is
  stored under page-root fixed-list root `+0x28`. Bridge `0x1edc6` exposes it
  at render root `+0x20`, copies source word `+8` to continuation word
  `+0x0a`, and initializes bytes `+0x0c = 1` and `+0x0d = 8`.
- Allocation retry:
  If fixed-list allocation fails, `0x12714` marks page-root flag word
  `+0x14`, publishes the old root through `0xff1e`, rebuilds the same local
  span source under a fresh root from `0x10084`, and retries insertion. The
  span is not silently dropped at the first no-room return.
- Render effect:
  Segment-list objects bridge through render root `+0x18` and dispatch via
  `0x1efc2 -> 0x1f812 -> 0x1f862`, where six-byte entries become counted mask
  spans using mask table `0x308f2`. Landscape fixed-list objects bridge
  through render root `+0x20` and dispatch via `0x1f756 -> 0x1f7b0`.

State grouping for this matrix:

- Canonical:
  selector byte `0x783185`, pending span byte `0x783184`, span bounds
  `0x783186` / `0x783188` / `0x78318a`, cursor x/y, current page root, compact
  glyph object, portrait segment-list object, and landscape fixed-list object.
- Derived/cache:
  packed span keys such as `0x3a00`, producer bucket/key fields
  `0x782a7c..0x782a7e`, selected-context metric words, render roots copied by
  `0x1edc6`, and render-band caches from `0x1ef86`.
- Parser scratch:
  six-byte `ESC &d` records, lookahead byte from `0xda9a`, lowercase family
  continuation state, and any generic `W/w` drain record.
- Firmware bookkeeping:
  delayed-restore call `0x12218`, span re-arm helper `0x126e2`, allocation
  cursors, retry publication flag, publication flag `0x782996`, and bridge
  continuation fields.
- Hardware/external:
  none for the ROM-local underline/span path after bytes are admitted.
- Unknown:
  no ROM-local middle edge remains for the documented selector write,
  printable span update, terminal/control flush, portrait segment-list,
  landscape fixed-list, retry, bridge, or render dispatch. New work belongs
  here only if a stream changes one of those fields, object bytes, bridge
  roots, or row-construction inputs.

Evidence:

- Handler and re-arm disassembly:
  `generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst`
  `0x12622..0x12712`.
- Span producer disassembly:
  `generated/disasm/ic30_ic13_text_span_flush_012714.lst` and
  `generated/disasm/ic30_ic13_display_list_helpers_013386.lst`.
- Render disassembly:
  `generated/disasm/ic30_ic13_page_record_to_render_record_01ed84.lst`,
  `generated/disasm/ic30_ic13_bitmap_bucket_walk_01ef6a.lst`, and
  `generated/disasm/ic30_ic13_bitmap_draw_core_01f3d4.lst`.
- Checked-in path:
  `Worked Path: Text Span Flush And Fixed-Width Spans` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md) and
  [page-record-storage.md](page-record-storage.md#segment-list-outcome-matrix).

Vertical-layout helper fixtures pin the shared VMI/text-boundary state that
feeds both direct controls and later printable placement. `0xc992 ESC &l#D
accepts ROM LPI set and refreshes pending vertical cursor` and
`0xcb00 ESC &l#C converts 1/48-inch VMI and keeps zero unmodified` pin the
VMI writers. In that fixture's zero case, the ROM-visible state is
`0x783160 = 0` with modified-layout byte `0x782ee1` still clear. The fixtures
`0xea9e ESC &l#F sets text length bottom or restores default`,
`0xece2 ESC &l#E sets top margin, default text length, and pending cursor`,
and `0xee64 ESC &l#L toggles perforation skip for selectors 0 and 1 only` pin
the vertical layout writers. Fixture
`0xcb00/0xc992/0xece2/0xea9e chained ESC &l stream selects vertical layout
handlers` pins same-family chaining; fixture
`vertical layout parser trace feeds page-record queue` carries the resulting
state into following printable output.

### Layout State To Output Checkpoint

This checkpoint covers layout commands whose immediate output is state, not
pixels. Their byte streams become visible only when a later printable,
vertical movement, VFC jump, FF, or page-eject path consumes the updated state.

Command route:

- `ESC &l#P` reaches page-length handler `0xf9e8`.
- `ESC &l#C` and `ESC &l#D` reach VMI/LPI handlers `0xcb00` and `0xc992`.
- `ESC &l#E` and `ESC &l#F` reach top-margin and text-length handlers
  `0xece2` and `0xea9e`.
- `ESC &l#L` reaches perforation-skip handler `0xee64`.
- `ESC &l#T` is the page-layout `T` table slot with no ROM handler. The
  lowercase chaining form `ESC &l#t` reaches generic rewind helper `0x11f4c`,
  leaving the `&l` family active for the following final byte.
- `ESC &s#C` reaches wrap-mode handler `0xedb0`.
- The following printable byte reaches `0xd04a`, then `0x12f2e` /
  `0x1387c`, publication, bridge, and render entry through the normal
  page-record path.

State handoff:

- Canonical layout state:
  VMI `0x783160`, page extent `0x782dba`, top offset `0x782dce`,
  text-length bottom `0x782dd2`, wrap byte `0x783190`, perforation-skip byte
  `0x783191`, and cursor y `0x782c8e`.
- Derived/cache state:
  perforation/text-bottom limit `0x782dc2`, refreshed compact coordinates for
  following printable bytes, page-geometry caches, and render-band fields
  created later by `0x1ed84` / `0x1ef86`.
- Parser scratch:
  six-byte command records for the `ESC &l` and `ESC &s` commands; those records
  are consumed by the handlers and are not later page-object state.
  The `ESC &l#t` chaining row is parser scratch only: `0x11f4c` subtracts six
  from `0x78299e` and returns so the next `&l` final can consume the retained
  record context.
- Firmware bookkeeping:
  modified-layout byte `0x782ee1`, pending text/cursor latch `0x782a6d`,
  pending publication/root-clear state for the `ESC &l0P` branch, and later
  scheduler progress after a following publication.
- Hardware/external state:
  only the `ESC &l0P` default-page branch can mirror paper-source state to
  ROM-visible output/control bytes `0x780e8f` / `0x780e26`; physical engine
  timing is outside this command-family checkpoint.

Page-length handler boundary:

- `0xf9e8..0xfa14` rewinds the six-byte parser record at `0x78299e`, reads
  parsed word `+2`, takes its absolute value into `D4`, and reads current VMI
  `0x783160`. A zero VMI exits immediately with no page geometry, publication,
  or cursor change.
- `0xfa26..0xfa48` handles nonzero line counts by multiplying current VMI by
  `D4`, converting the packed 12-subunit result back to whole dots through
  `0x104fe`, `0x332ee`, and `0x104d8`, and keeping that computed page extent
  in `D4`.
- `0xfa48..0xfb18` selects an internal page code from orientation-specific
  thresholds. Portrait mode tests `0x782daa`, `0x782dae`, `0x782dac`, and
  `0x782db0`, selecting codes `6`, `2`, `1`, or `5`. Landscape mode tests
  `0x782daa`, `0x782dac`, and `0x782dae`, selecting codes `6`, `1`, or `2`.
  If the computed extent exceeds every threshold, the handler exits without
  changing page geometry.
- `0xfa62..0xfaa6` is the zero-parameter branch. It flushes pending text
  through `0xf34a`, publishes the current root through `0xff1e`, waits through
  `0x9ac2`, compares current paper-source byte `0x782da6` with previous output
  byte `0x780e8e`, and when they differ mirrors `0x782da6` to `0x780e8f` and
  signals control word `0x780e26` through `0x9b5e`.
- `0xfb20..0xfb5a` commits the selected page code. It marks layout refresh byte
  `0x782997`, calls reset/layout helpers `0x15a6` and `0x15ac`, writes code
  byte `0x782da2`, and either restores the default page length through local
  helper `0xf9ac` for selector zero or writes the computed extent to
  `0x782dba` for nonzero selectors. When no default code exists at `0x780e97`,
  the zero branch falls back to page code `2`.
- `0xfb60..0xfc52` recomputes derived page geometry. It writes table-derived
  geometry words `0x782db2`, `0x782db4`, `0x782dc0`, refreshes orientation
  companion state through `0xf87e`, adjusts `0x782db6` when the previous length
  no longer fits, rebuilds top offset `0x782dce`, clears `0x782dd0`, restores
  default text length through `0xea16`, clears margins through `0xe9ba`,
  refreshes pending cursor through `0xf8fc`, updates line caches through
  `0xfe54`, and rebuilds the default VFC table through `0x12b96`.
- `0xfc58..0xfc6c` clears macro/overlay byte `0x782a92` unless it holds
  selector value `2`, then returns. This makes page-length changes part of the
  same environment-reset family that can invalidate overlay publication state.

Vertical-layout and mode handler boundaries:

- `0xca8c..0xcaf2` handles `ESC &k#H`. It rewinds the parser record, reads
  integer word `+2` and fractional word `+4`, treats a negative integer as a
  signed pair by negating both words, and rejects integer values above
  `0x348`. Accepted values are scaled by `30`: the integer contribution is
  `word(+2) * 30`, the fractional contribution is
  `word(+4) * 30 / 10000`, and `0x104d8` converts the sum before storing the
  packed HMI in `0x78315c`. No page object is queued here; printable text,
  HT/BS, margins, and cursor-position handlers consume the new HMI later.
- `0xcb00..0xcb7c` handles `ESC &l#C`. It rewinds the parser record, uses the
  absolute parsed integer/fraction words, rejects values above `0x150`, scales
  the value by `75`, converts it to packed line advance, rejects converted
  advances beyond current page extent `0x782dba`, and writes VMI `0x783160`.
  The store happens before the later zero check, so a converted value of zero
  writes `0x783160 = 0`.
- `0xcb82..0xcbca` is the `ESC &l#C` pending-cursor side effect. If pending
  byte `0x782a6d` is set, it computes `VMI * 18 / 25 + top_offset` and writes
  refreshed cursor y `0x782c8e`. A converted VMI of zero skips only modified
  layout byte `0x782ee1`; nonzero values set it.
- `0xc992..0xca0e` handles `ESC &l#D` selector admission. It rewinds the
  parser record, takes the absolute value, maps selector `0` to `12`, and
  accepts only `1`, `2`, `3`, `4`, `6`, `8`, `12`, `16`, `24`, and `48`.
- `0xca0e..0xca82` converts accepted LPI to packed line advance as
  `3600 / LPI`, rejects advances beyond page extent `0x782dba`, optionally
  refreshes pending cursor y by the same `VMI * 18 / 25 + top_offset` rule,
  writes `0x783160`, and sets modified-layout byte `0x782ee1`.
- `0xea9e..0xeb26` handles `ESC &l#F`. It rewinds the parser record, takes the
  absolute text-length line count, converts through current VMI, rejects zero
  VMI, computes the usable page region below current top offset `0x782dce`, and
  exits if the requested length does not fit.
- `0xeb2e..0xeb56` is the text-length commit path. Selector zero restores the
  default bottom through `0xea16`; nonzero accepted lengths write bottom state
  `0x782dd2 = top_offset + text_length`. Both branches refresh line caches
  through `0xfe54` and rebuild the default VFC table through `0x12b96`.
- `0xece2..0xed54` handles `ESC &l#E`. It rewinds the parser record, scales the
  absolute top-margin line count through current VMI, rejects zero VMI and
  top positions at or beyond page extent `0x782dba`, subtracts physical top
  offset `0x782dbe`, and writes top offset `0x782dce`.
- `0xed5a..0xedae` completes top-margin handling. It recomputes default text
  length through `0xea16`, optionally refreshes pending cursor y with the
  `VMI * 18 / 25 + top_offset` rule, refreshes line caches through `0xfe54`,
  and rebuilds the default VFC table through `0x12b96`.
- `0xedb0..0xedf6` handles `ESC &s#C`. It rewinds the parser record, takes the
  absolute selector, writes wrap byte `0x783190 = 1` for selector `0`, clears
  it for selector `1`, and leaves it unchanged for other selectors.
- `0xee64..0xeeaa` handles `ESC &l#L`. It rewinds the parser record, takes the
  absolute selector, clears perforation byte `0x783191` for selector `0`, sets
  it for selector `1`, and leaves it unchanged for other selectors.
- `ESC &l#T` has no terminal page-layout writer in the parser table. It
  returns through the normal terminal parser path without changing VMI, page
  extent, margins, perforation, cursor, page-root, publication, or render state.
  Its lowercase sibling `ESC &l#t` reaches `0x11f4c`, whose complete body is
  `subq.l #6, $78299e` and return; any later effect comes from the following
  chained `&l` final, not from `t` itself.
- `0xf36c..0xf39c` is the shared perforation consumer. It calls page-eject
  helper `0xf124` and returns `D7 = 0` only when cursor y `0x782c8e` is beyond
  nonzero limit `0x782dc2` and perforation byte `0x783191` is set. Otherwise
  it returns `D7 = 1` without publication.

Downstream consumers:

- Printable prechecks `0xd28a` and `0xd6bc` read wrap byte `0x783190` before
  queueing a glyph. Disabled wrap rejects horizontal overflow; enabled wrap
  calls `0xf054`, retries from recovered x `0`, and can continue to `0x12f2e`.
- Vertical overflow helper `0xf36c` reads cursor y `0x782c8e`, limit
  `0x782dc2`, and perforation-skip byte `0x783191`. Enabled overflow with a
  nonzero exceeded limit calls page-eject helper `0xf124`; disabled or
  below-limit cases return without publication.
- Cursor, VFC, and printable-placement paths read `0x783160`, `0x782dce`,
  `0x782dd2`, and `0x782dc2` when converting later command values into page
  coordinates.

Output boundary:

- `ESC &l66P!` writes page extent `0x782dba = 3300`, refreshes cursor-derived
  placement, then queues the following printable at compact coordinate
  `0x9001`.
- `ESC &l0P` can publish the current page before restoring the default page
  code. It has no glyph output by itself; when a root exists, the visible
  effect is the pre-command page publication at `0xff1e`, plus ROM-visible
  paper-source mirroring through `0x780e8f` / `0x780e26` when the current and
  previous source bytes differ.
- The chained vertical-layout stream reaches `0xcb00`, `0xc992`, `0xece2`, and
  `0xea9e` before the following printable object records that stored VMI,
  top-margin, and text-length state is consumed by page-record queueing.
- `ESC &l1L!` writes `0x783191 = 1`; the following printable still uses the
  normal compact page-record path, while later vertical overflow decisions use
  the new perforation-skip byte.
- `ESC &s#C` has no immediate object. Its output effect is the later
  `0xd28a` / `0xd6bc` accept/reject/retry decision before compact text
  queueing.
- `ESC &l#T` and `ESC &l#t` have no page-output effect. The uppercase slot is
  ignored at the command-family boundary; the lowercase slot only preserves
  parser chaining for the next `&l` final.

Evidence:

- Disassembly:
  `generated/disasm/ic30_ic13_page_length_handler_00f9e8.lst`,
  `generated/disasm/ic30_ic13_hmi_vmi_handlers_00ca8c.lst`,
  `generated/disasm/ic30_ic13_font_selection_update_handlers_00c6ec.lst`,
  `generated/disasm/ic30_ic13_perforation_skip_handler_00ee64.lst`,
  `generated/disasm/ic30_ic13_wrap_mode_handler_00edb0.lst`,
  `generated/disasm/ic30_ic13_parser_setup_handlers_011ea4.lst`, and
  `generated/disasm/ic30_ic13_printable_text_path_00d04a.lst`.
- Generated flow:
  `generated/analysis/ic30_ic13_direct_control_code_flow.md`,
  `generated/analysis/ic30_ic13_pcl_command_map.md`, and
  `generated/analysis/ic30_ic13_text_cursor_span_flow.md`.
- Fixture families:
  page-length, VMI/LPI, top-margin, text-length, perforation-skip,
  wrap/precheck, vertical-layout parser trace, and following-printable
  page-record queue fixtures named in the evidence list above.

No ROM-local middle edge remains for the documented layout-writer fields or
their following-printable / overflow consumers. Remaining work must expose a
new writer, consumer, object shape, publication state, or row-construction input
instead of rechecking the same state through another byte-stream variant.

## Reproduction Contract

A byte-stream renderer must preserve:

- normal-mode direct-control dispatch for CR, LF, FF, HT, BS, SO, and SI;
- the `ESC &k#G` mode byte and its per-control-bit consumption;
- SO/SI selected-context switching through `0xc6b8` / `0xc68a`,
  `0xc428` / `0xc4fc`, selected slot `0x782f06`, and page-root context slot
  `0x78297e`;
- the `ESC &s#C` wrap byte and its prequeue effect on `0xd28a` / `0xd6bc`
  horizontal overflow decisions;
- VMI/LPI, page-length, top-margin, text-length, and perforation-skip state as
  delayed inputs to following printable placement and vertical overflow;
- the `ESC &lT/t` no-output page-layout slot: uppercase ignores the command and
  lowercase only performs `0x11f4c` parser chaining;
- CR reset through left margin before optional LF movement;
- LF and FF optional CR-style reset behavior;
- HT eight-column stop arithmetic using left margin and HMI;
- BS HMI subtraction, left-margin clamp, and alternate previous-width mode;
- page-root creation/finalization and pending-state effects for FF;
- span flushes through `0xf34a` / `0x12714` before cursor-changing commands
  overwrite pending span bounds;
- cursor-stack push/pop storage including vertical offset `0x782dbe`;
- following printable object coordinates after every cursor or margin command;
- page-record bridging and render-entry rows after those objects are queued.

## Confidence

High for line-termination bits, CR/LF/FF/HT/BS cursor effects, HMI conversion,
page-record compact coordinates, and representative ROM-derived row
construction because the claims are backed by disassembly plus byte-stream
fixtures that start at modeled host byte fetch and reach `0x1387c`,
`0x1edc6`, `0x1ed84`, and `0x1ef6a`. The fixtures drive ROM-local branches;
they are not external rendered-output comparisons.

High for SO/SI selected-context switching, `ESC 9`, `ESC =`, cursor-stack,
underline/span, and perforation-skip representative output effects because
each has a named parser/page-record fixture and concrete handler evidence.

High for `ESC &s#C` selector handling and printable precheck consumption,
because the `0xedb0` writer and paired `0xd28a` / `0xd6bc` consumers are pinned
by fixtures and by disassembly reads of `0x783190`.

High for printable source capture and compact object publication from
`0xd04a` / `0xd0f0` through `0x1393a`, `0xd3b2` / `0xd824`, and `0x12f2e`,
because the source fields, branch decisions, compact object shapes, allocation
retry, and span-consumer handoff are now enumerated in the
[Printable Source Outcome Matrix](#printable-source-outcome-matrix).

Medium only for manual-facing latch names and byte-stream variants that would
change a named field, object byte, allocation outcome, or render-helper input
outside the documented matrix.

## Remaining Edges

- No ROM parser-to-page-record middle edge remains for the documented
  CR/LF/FF/HT/BS plus `ESC &k#G` control family.
- Remaining work is byte-stream cases that change a field or boundary named in
  the [Printable Source Outcome Matrix](#printable-source-outcome-matrix),
  span-flush state outside the documented `0xd4ac` / `0xd8fc` consumers, or a
  later render-dispatch input. Replaying already documented direct-control
  fields from another execution source is not a new ROM-local edge.
