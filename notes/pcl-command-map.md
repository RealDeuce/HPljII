# PCL Command Map from Firmware

Sources: `generated/analysis/ic30_ic13_pcl_command_map.md`;
`generated/analysis/ic30_ic13_parser_dispatch_tables.md`;
`generated/analysis/ic30_ic13_font_control_flow.md`; focused listings under
`generated/disasm/`, including
`ic30_ic13_wrap_mode_handler_00edb0.lst`,
`ic30_ic13_dot_position_handlers_00f48c.lst`, and
`ic30_ic13_transparent_data_handler_011f5a.lst`;
`notes/pcl4-language.md`.

The generated command map flattens the main parser's mode-indexed
dispatch tables into PCL command sequences and handler addresses. It is
local-only because it is generated from ROM bytes, but it can be
regenerated with:

```sh
tools/analyze_roms.py
```

## Parser Tables

- Normal parser pointer table: `0x000112a4`.
- Alternate/data parser pointer table: `0x000116f6`.
- Each table entry is six bytes:

```text
byte_to_match, next_mode, handler_long
```

The alternate/data table keeps the same state transitions but suppresses
many final handlers. That is consistent with a mode that must still
parse or collect PCL syntax while deferring normal side effects.
For matched mode-zero C0 rows with blank handlers, alternate/data mode does
not treat the byte as a normal control command; it appends the byte through
`0xe002` after the shared scratch-flush helpers and then rejoins the terminal
parser reset path. Normal mode-zero blank C0 rows instead reset/finalize
without page-record output or alternate append.
Lowercase finals that keep the parser in the same command family are
reported as chaining forms of the matching uppercase PCL command.
Rows labeled as parser prefixes are setup/scaffolding entries, not terminal
imaging commands: the handler records the family transition and leaves the
final command byte to a later mode. Examples are `ESC`, `ESC &`, `ESC &l`,
`ESC *c`, and the primary/secondary font family prefixes. Rows labeled as
font-designation terminals are the `ESC (#A..^` / `ESC )#A..^` family handled
by `0x120be`; their command-specific effects are documented with the
symbol-set and font-selection state in `notes/semantic-state-model.md`.
The `ESC &lT/t` table slot is intentionally labeled as unimplemented: normal
uppercase `T` has no terminal handler, while lowercase `t` only reaches the
generic `0x11f4c` rewind used by lowercase chaining rows.

Two normal-table rows with blank handlers are parser artifacts rather than
undocumented imaging commands:

- `ESC ?` is handled inside the ESC-aware byte-fetch wrapper. After `0xda9a`
  sees `ESC`, wrapper fetch `0xdaa6` checks the next byte; when it is `?`,
  `0xdab2` fetches a third byte. Third byte `0x11` is swallowed and the wrapper
  loops; any other third byte is reported through `0x9ec0` and the wrapper
  returns `ESC` to the parser. The detailed caller classification is in
  [host-byte-fetch.md](host-byte-fetch.md).
- `ESC Z` is the local terminator for the `ESC Y ... ESC Z`
  display-functions readers, not a normal parser-table terminal. Normal handler
  `0x12536` and alternate/data handler `0x12120` both consume the terminating
  `ESC Z` bytes inside their direct `0xa904` reader loops before returning. The
  checked-in semantic contract is [display-functions.md](display-functions.md).

Normal mode-zero C0 rows `0x00`, `0x07`, and `0x0b` are also matched
zero-handler table rows, not unknown imaging commands. They enter the shared
terminal state-transition path in the main parser loop, restore any pending
delayed payload through `0x12218`, reset parser record and scratch cursors, and
produce no direct page-record output. Since they match explicit table rows,
they do not reach the selected-context unmatched-byte fallback that can send
other bytes to printable handler `0xd04a`. The low-level path is documented in
[pcl-parser-core.md](pcl-parser-core.md).

The alternate/data table has blank mode-zero C0 rows for `0x00` and
`0x07..0x0f`. Those rows preserve the current byte in the append stream
through `0xe002` before the same terminal reset path; they do not dispatch to
the normal control handlers for BS, HT, LF, FF, CR, SO, or SI.

Alternate/data mode is therefore not a blanket command ignore. It keeps parser
state and payload boundaries while suppressing most immediate page-state
effects:

- Direct page/text controls and most uppercase family terminals have blank
  alternate/data handlers, so their parsed command bytes do not immediately
  mutate cursor, geometry, selected-font, rectangle, raster-control, or dot
  position state.
- Lowercase chaining finals mostly use helper `0x11f4c`, which rewinds the
  six-byte parser record so the family can continue without running the normal
  command handler.
- Payload/record families that must be stored in macro/data streams still
  execute: `ESC &p#X` / `x`, `ESC &l#W` / `w`, `ESC *b#W` / `w`,
  `ESC (s#W` / `w`, `ESC )s#W` / `w`, and macro control `ESC &f#X` /
  `x`.
- `ESC Y` switches from normal reader `0x12536` to alternate append reader
  `0x12120`; local Control-Z terminals switch from printable output handlers
  to append/report handlers `0x1210c` and `0x121b2`.
- `ESC E` remains active through reset handler `0xcc52`, so alternate/data
  mode does not protect accumulated state from an explicit reset.

## Semantic Owners

Use the parser-table notes above and the checked-in handler anchors below as
the command index. The generated flat table is supporting evidence; the
owning notes below carry state, consumers, output effect, and unresolved
boundaries:

- Host fetch, parser selection, parser records, delayed payload restore, blank
  rows, `ESC ?`, `ESC Z`, and `ESC &lT/t`:
  [host-byte-fetch.md](host-byte-fetch.md),
  [pcl-parser-core.md](pcl-parser-core.md), and
  [firmware-dataflow-model.md](firmware-dataflow-model.md) worked paths
  `Host Byte Source Priority`, `Command Record And Payload Dispatch`, and
  `Explicit No-Output Parser Rows`.
- CR, LF, FF, HT, BS, `ESC &k#G`, HMI, wrap mode, cursor position, margins,
  dot position, cursor stack, underline/span flushing, and vertical layout
  helpers:
  [direct-control-codes.md](direct-control-codes.md).
- `ESC Y ... ESC Z`, local Control-Z siblings, alternate/data display append,
  and guarded `ESC z` status signaling:
  [display-functions.md](display-functions.md).
- Reset, FF publication, page size, orientation, paper source, and copies:
  [publication-commands.md](publication-commands.md) plus reset provenance in
  [reset-default-environment.md](reset-default-environment.md).
- Transparent print data `ESC &p#X`:
  [transparent-print-data.md](transparent-print-data.md).
- Raster resolution/start/end and delayed `ESC *b#W` raster rows:
  [raster-graphics.md](raster-graphics.md).
- Model-ID/status backchannel commands `ESC *r#K` and `ESC *s#^`, including
  the `0x12034 -> 0x122be` `33440A\r\n` producer and host-output FIFO:
  [errors-and-status.md](errors-and-status.md) and
  [host-byte-fetch.md](host-byte-fetch.md).
- Rectangle dimensions, fill selector, area-fill id, and rule publication:
  [rectangle-graphics.md](rectangle-graphics.md).
- Vertical forms control table payloads and channel jumps:
  [vertical-forms-control.md](vertical-forms-control.md).
- Font selection, symbol sets, font attributes, pitch mode, SO/SI selected
  context switches, metric producer/consumer behavior, and built-in resource
  selection:
  [font-context-metrics.md](font-context-metrics.md) and
  [built-in-resource-scan.md](built-in-resource-scan.md).
- Downloaded-font descriptors, downloaded glyph payloads, fixed/current
  resource objects, no-install exits, row/span publication, and compact
  downloaded-glyph render boundaries:
  [downloaded-fonts.md](downloaded-fonts.md).
- Macro ID/control commands, macro definition, execute/call replay, overlay
  publication, and data-chain byte replay:
  [macro-data-chain.md](macro-data-chain.md).
- External-ready service and page/font scheduler handoff:
  [external-ready-service.md](external-ready-service.md),
  [page-font-scheduler.md](page-font-scheduler.md), and
  `Worked Path: Page Font Scheduler Resource Handoff` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md).

The end-to-end spine that joins those owners from byte stream to rendered rows
is [firmware-dataflow-model.md](firmware-dataflow-model.md). The shorter
coverage map and current target list are in
[end-to-end-reproduction-map.md](end-to-end-reproduction-map.md).

## Inbound Byte Reading Contract

To read any supported host byte stream from this map, follow the byte through
these ROM-defined boundaries before jumping to command-family notes:

1. `0xa904..0xab8a` chooses the next normalized byte source. Live host input,
   ring-buffer input, data-chain replay, and direct hardware modes all reduce
   to the same `D7` byte contract before the parser sees the byte. Source
   priority and replay ownership are documented in
   [host-byte-fetch.md](host-byte-fetch.md) and
   [macro-data-chain.md](macro-data-chain.md).
2. `0xda9a` / `0xdaf0` / `0xdb74` maintain parser state byte `0x782999`,
   six-byte parser record `0x78299e..0x7829a3`, parser cursor
   `0x78299a`, parsed numeric value fields, and delayed-payload restore
   state. The parser core contract is in
   [pcl-parser-core.md](pcl-parser-core.md).
3. Parser loop `0x11774` indexes either normal table `0x112a4` or
   alternate/data table `0x116f6`. Prefix rows change the command-family mode;
   lowercase finals either keep the family mode or call rewind helper
   `0x11f4c`; uppercase or terminal finals usually return to mode zero after
   the handler or zero-handler terminal path runs.
4. Terminal handlers in the matrix below are the handoff from syntax to
   semantics. From that point, use the owner note named by the row to find
   field writers, readers/consumers, page-object effects, publication effects,
   render effects, confidence, and exact unresolved boundaries.
5. Delayed binary payload commands are two-stage. The table handler records a
   pending transfer (`0x11f5a`, `0x11f6e`, `0x11f82`, `0x11f96`), then
   restore path `0x121cc -> 0x12218` calls the payload consumer such as
   `0x12452`, `0x12cfe`, `0x105d0`, `0x15d0a`, or `0x16c14`. The family
   matrix in `Worked Path: Command Record And Payload Dispatch` maps those
   consumers to their state writes and page/output owners.

This contract is intentionally ROM-local. It documents what the firmware does
with admitted bytes and where those bytes become page/render state. Physical
bus timing, external memory decode, and formatter/DC signal naming are only
part of the command map when they change a ROM-visible byte, parser state,
page object, scheduler field, or render input.

## Table Coverage Note

The generated flat table in
`generated/analysis/ic30_ic13_pcl_command_map.md` is the audit source for the
two parser tables. The checked-in command map covers every normal-mode
terminal handler from that table either as a direct handler anchor below or as
one of these family entries:

- parser setup/prefix wrappers `0x11ea4`, `0x11eb6`, `0x11ec8`,
  `0x11eda`, `0x11eec`, `0x11ff6`, `0x12008`, and `0x1201e`;
- lowercase font-selection writers `0xc930`, `0xc89c`, `0xc6ec`,
  `0xc780`, `0xc840`, and `0xc7e0`;
- font-designation terminals collapsed under `0x120be`;
- local Control-Z terminal siblings collapsed under the Control-Z anchor.

The alternate/data table is covered by the policy above plus its active
exceptions: `ESC Y` append reader `0x12120`, Control-Z append/report handlers
`0x1210c` / `0x121b2`, delayed payload/storage handlers, macro control
`0xdd08`, and reset `0xcc52`. Blank alternate/data rows are meaningful:
they preserve syntax or bytes without running the normal page-state handler.

Checked-in dispatch audit, generated from
`generated/analysis/ic30_ic13_pcl_command_map.md`:

- Normal table `0x112a4`: `214` flattened rows, `78` unique nonzero handler
  addresses, and `5` zero-handler rows. The zero-handler rows are
  `0x00`, `0x07`, `0x0b`, `ESC ?`, and `ESC Z`. The first three are explicit
  no-output C0 parser rows; `ESC ?` is consumed by the `0xda9a` ESC-aware byte
  wrapper; `ESC Z` is consumed as the local terminator by display-functions
  readers.
- Normal table high-fanout rows are intentional family collapses, not missing
  owners: `0x120be` covers `62` primary/secondary font-designation terminals,
  `0x11eda` covers `12` parameterized family prefixes, and `0x11f96` covers
  `4` primary/secondary downloaded-font payload entries.
- Alternate/data table `0x116f6`: `216` flattened rows, `17` unique nonzero
  handler addresses, and `130` zero-handler rows. The large zero-handler count
  is expected: it suppresses immediate page-state side effects for direct C0
  controls, uppercase cursor/page/layout/rectangle/raster/font-selection
  terminals, font-designation terminals, and display-functions-off rows while
  preserving parser syntax, append behavior, or delayed-payload boundaries.
- Alternate/data nonzero high-fanout rows are also intentional: `0x11f4c`
  covers `50` lowercase chaining finals that rewind/retain the current family
  without running the normal uppercase terminal handler; `0x11eda` covers the
  same `12` family prefixes; `0x11f96` covers the `4` downloaded-font payload
  entries that must remain stored in data/macro contexts.

## Supported Stream Dispatch Matrix

Use this matrix with
[end-to-end-reproduction-map.md](end-to-end-reproduction-map.md#supported-stream-entry-points).
It names the parser route for the concrete supported stream families before the owner
notes take over field writes, page objects, and pixels. The generated table files remain
supporting evidence; the checked-in owner notes are the semantic source of truth.

- Printable text and direct C0 controls:
  mode-zero printable bytes go from `0x11774` to `0xd04a` in normal mode.
  Direct controls use normal mode-zero rows: BS `0xf2a8`, HT `0xf1cc`,
  LF `0xf08c`, FF `0xf0f0`, CR `0xf02c`, SO `0xc6b8`, and SI `0xc68a`.
  Explicit blank rows `0x00`, `0x07`, and `0x0b` take the zero-handler reset
  path through `0x12218` without page output. Owner notes:
  [pcl-parser-core.md](pcl-parser-core.md),
  [direct-control-codes.md](direct-control-codes.md), and
  [font-context-metrics.md](font-context-metrics.md).
- Cursor, margins, and text-motion commands:
  `ESC &` enters mode `5` through `0x11eb6` / `0x11ec8`; `&a` enters mode
  `12` through `0x11eda`. Terminals route to `0xf39e` (`C/c`), `0xf416`
  (`H/h`), `0xeb58` (`L/l`), `0xec0c` (`M/m`), `0xf560` (`R/r`), and
  `0xf60a` (`V/v`). Lowercase finals keep mode `12`; uppercase finals return
  to mode zero. Text-motion `&k` enters mode `11` and reaches `0xedf8`
  (`G/g`), `0xca8c` (`H/h`), and `0xc390` (`S/s`). Owner note:
  [direct-control-codes.md](direct-control-codes.md).
- Page layout, VFC, and publication commands:
  `&l` enters mode `10` through `0x11eda`. Page-size, VMI/LPI, margin, paper,
  orientation, copies, and VFC terminals route to `0xfc74`, `0xcb00`,
  `0xc992`, `0xece2`, `0xea9e`, `0xef62`, `0xee64`, `0x10220`,
  `0xf9e8`, `0x1280a`, `0x11f6e`, and `0xeef0`. `ESC &l#W` is delayed:
  `0x11f6e -> 0x121cc -> 0x12218 -> 0x12cfe`. FF and reset use direct
  terminals `0xf0f0` and `0xcc52`. Owner notes:
  [publication-commands.md](publication-commands.md) and
  [vertical-forms-control.md](vertical-forms-control.md).
- Transparent/display payload readers:
  `ESC &p#X` enters modes `5 -> 9`, reaches `0x11f5a`, and restores delayed
  handler `0x12452` through `0x121cc` / `0x12218`. `ESC Y ... ESC Z` enters
  mode `1` and dispatches normal reader `0x12536`; alternate/data mode uses
  `0x12120`. Control-Z mode `2` terminals use normal handlers `0x120d2` /
  `0x1219e` or alternate handlers `0x1210c` / `0x121b2`. Owner notes:
  [transparent-print-data.md](transparent-print-data.md) and
  [display-functions.md](display-functions.md).
- Rectangle and raster imaging:
  `ESC *` enters mode `3`. Rectangle `*c` enters mode `16`, with
  `A/a -> 0x10e68`, `B/b -> 0x10e22`, `G/g -> 0x10dce`, and
  `P/p -> 0x10898`; the covered `ESC *c12a5b0P` route is
  `0 -> 1 -> 3 -> 16 -> 16 -> 16 -> 0`. Raster resolution `*t#R` uses
  mode `15` and handler `0x10808`; raster start/end `*r#A/#B` use mode `7`
  and handlers `0x1075a` / `0x107fa`; raster payload `*b#W` uses mode `14`,
  `0x11f82 -> 0x121cc -> 0x12218 -> 0x105d0`. Owner notes:
  [rectangle-graphics.md](rectangle-graphics.md) and
  [raster-graphics.md](raster-graphics.md).
- Font selection and downloaded-font payloads:
  primary `ESC (` reaches prefix handler `0x1201e`; secondary `ESC )`
  reaches `0x12008`; designation terminals in mode `4` share `0x120be`.
  `(s` / `)s` enters mode `13` through `0x11ff6`. Lowercase attribute finals
  write request fields directly through `0xc930`, `0xc89c`, `0xc6ec`,
  `0xc780`, `0xc840`, and `0xc7e0`; uppercase wrappers reach `0x12082`,
  `0x12096`, `0x12046`, `0x1206e`, `0x120aa`, and `0x1205a`. Font/download
  `W/w` reaches `0x11f96`, which schedules `0x15d0a` for count `0` and
  `0x16c14` for nonzero counts. Successful downloaded-character payloads
  install records through `0x16498`; following printable bytes consume the
  selected glyph through `0xd04a` / `0x1393a` / `0x12f2e`, publish through
  `0xff1e`, and render through `0x1ed84` / `0x1ef6a`. Row-count streams have
  a documented selector boundary: low-byte rows `0x0001..0x00ff` are
  reproducible through the compact helpers, while high-row short compact
  siblings `0x0101..0x0103` stop at the unchecked `0x1fe76` fallback
  jump-table read. Owner notes:
  [font-context-metrics.md](font-context-metrics.md) and
  [downloaded-fonts.md](downloaded-fonts.md).
- Macro definition, replay, and overlay:
  `ESC &f` enters mode `17`. `Y/y` reaches macro-id handler `0xe112`;
  `X/x` reaches macro-control handler `0xdd08`; `S/s` reaches cursor-stack
  handler `0xf75e`. Normal and alternate/data tables both keep `X/x` active
  so selector `1` can stop macro definition while payload controls are
  appended rather than executed. Replay re-enters host byte fetch through the
  data-chain source consumed by `0xa904`. Owner note:
  [macro-data-chain.md](macro-data-chain.md).
- Status and model-response side channels:
  `ESC *r#K` enters mode `7` and `ESC *s#^` enters mode `6`; both dispatch
  wrapper `0x12034`, which appends setup record `0x11efe` and calls
  `0x122be` to emit `33440A\r\n` under the documented predicates. Owner note:
  [errors-and-status.md](errors-and-status.md).

## High-Value Normal-Mode Handlers

These command-to-handler anchors are the normal-mode landmarks used by the
semantic owners above. They are not all open tracing targets; each entry points
from a parsed command form to the handler whose state and output effects are
documented in the owner notes.

- `ESC E`, handler `0x00cc52`: PCL reset, partial-page finalization,
  environment/parser/raster reinitialization.
- CR `0x0d`, handler `0x00f02c`: horizontal cursor reset and
  line-termination interactions.
- LF `0x0a`, handler `0x00f08c`: vertical cursor movement.
- FF `0x0c`, handler `0x00f0f0`: page eject and page-buffer boundary.
- HT `0x09`, handler `0x00f1cc`: tab and horizontal cursor positioning.
- BS `0x08`, handler `0x00f2a8`: backspace cursor behavior.
- SO `0x0e`, handler `0x00c6b8`: selected text context switch to slot `1`;
  calls `0xc428(1)` / `0xc4fc`, sets `0x782f06 = 1` when the secondary
  context installs, and makes later printable bytes consume the secondary
  map/context documented in
  [font-context-metrics.md](font-context-metrics.md).
- SI `0x0f`, handler `0x00c68a`: selected text context switch to slot `0`;
  calls `0xc428(0)` / `0xc4fc`, clears `0x782f06` when the primary context
  installs, and makes later printable bytes consume the primary map/context
  documented in [font-context-metrics.md](font-context-metrics.md).
- Control-Z prefix `0x1a`, handler `0x011ea4`, with terminals `0x1a 0x1a`
  and `0x1a X`: normal handlers `0x120d2` / `0x1219e` conditionally feed
  printable text through `0xd04a`, while alternate/data handlers `0x1210c` /
  `0x121b2` append through `0xe002`; parser and display-function ownership is
  documented in [pcl-parser-core.md](pcl-parser-core.md) and
  [display-functions.md](display-functions.md).
- `ESC 9`, handler `0x00e9ba`: clear horizontal margins; clears left
  margin, copies page width to right margin, and clears the right-margin
  fractional companion.
- `ESC =`, handler `0x00f176`: half-line feed; ensures the page root,
  flushes pending text span state, and advances vertical cursor by half
  the current VMI.
- `ESC Y`, handlers `0x012536` normal and `0x012120` alternate/data:
  display-functions reader loop; the normal path routes normalized bytes
  into text/fixed-space output, while the alternate path appends them.
- `ESC z`, handler `0x00cd86`: display-functions off/reset terminal;
  tests the active data-chain frame byte at `0x782d76 + 9` and calls
  helper `0x9c2c` only when that byte is zero.
- `ESC &l#A`, handler `0x00fc74`: page size; maps PCL values to internal
  paper codes.
- `ESC &l#P`, handler `0x00f9e8`: page length in lines; converts current
  VMI times line count into page extent `0x782dba`.
- `ESC &l#W`, handler `0x011f6e`: vertical forms control payload
  boundary; delayed handler `0x12cfe` loads table `0x782dde`.
- `ESC &l#V`, handler `0x01280a`: vertical forms control channel jump;
  consumes table `0x782dde`.
- `ESC &l#O`, handler `0x010220`: orientation; rebuilds page geometry
  and cursor state.
- `ESC &l#C`, handler `0x00cb00`: VMI in 1/48-inch units into
  `0x783160`.
- `ESC &l#D`, handler `0x00c992`: lines per inch; accepted set maps to
  line advance `0x783160`.
- `ESC &l#E`, handler `0x00ece2`: top margin; writes top offset
  `0x782dce`.
- `ESC &l#F`, handler `0x00ea9e`: text length; writes bottom/text-length
  limit `0x782dd2`.
- `ESC &l#L`, handler `0x00ee64`: perforation skip; selector `0`
  clears `0x783191`, selector `1` sets it.
- `ESC &l#H`, handler `0x00ef62`: paper source and page eject.
- `ESC &l#X`, handler `0x00eef0`: copy count; stores absolute clamped
  `0x782da4`, which the following FF publication copies into pool-header word
  `+0x0c`.
- `ESC &a#L`, handler `0x00eb58`: left margin; absolute HMI columns into
  `0x782dd6`.
- `ESC &a#M`, handler `0x00ec0c`: right margin; `abs(parameter) + 1` HMI
  columns into `0x782dda`.
- `ESC &a#C`, handler `0x00f39e`: horizontal column position through
  current HMI and helper `0xf4ca`.
- `ESC &a#H`, handler `0x00f416`: horizontal decipoint position; five
  packed subunits per decipoint.
- `ESC &a#R`, handler `0x00f560`: vertical row position through current
  VMI, top offset, and helper `0xf6e2`.
- `ESC &a#V`, handler `0x00f60a`: vertical decipoint position; five
  packed subunits per decipoint.
- `ESC &k#H`, handler `0x00ca8c`: HMI; absolute value scaled as
  30 packed subunits per 1/120-inch unit into `0x78315c`.
- `ESC &k#G`, handler `0x00edf8`: CR/LF/FF line-termination mode.
- `ESC &k#S`, handler `0x00c390`: pitch mode; ROM-confirmed selectors
  `0`, `2`, and `4` synthesize pitch-update records and feed the existing
  `0xc89c` / `0xc580` font-selection refresh path.
- `ESC &f#S`, handler `0x00f75e`: cursor stack at `0x782c96..0x782d36`;
  selector `0` pushes, selector `1` pops.
- `ESC &f#Y`, handler `0x00e112`: macro ID; stores absolute parsed word
  in `0x783164`.
- `ESC &f#X`, handler `0x00dd08`: macro control; selectors `0..10`
  dispatch through the macro record/data-chain table.
- `ESC &p#X`, handler `0x011f5a`: transparent print data boundary.
- `ESC &d...`, handler `0x012622`: underline/text-attribute tokenizer;
  schedules `W/w` payloads, flushes pending span state for bit-2-clear
  terminal bytes, and writes selector `0x783185` before re-arming span
  bounds for the `3D` alternate-offset case.
- `ESC &s#C`, handler `0x00edb0`: end-of-line wrap mode.
- `ESC *t#R`, handler `0x010808`: raster resolution.
- `ESC *r#A`, handler `0x01075a`: start raster graphics.
- `ESC *r#B`, handler `0x0107fa`: end raster graphics.
- `ESC *r#K` and `ESC *s#^`, handler `0x012034`: model-ID response wrapper.
  The wrapper appends the `0x11efe` setup record and calls `0x122be`, which
  emits `33440A\r\n` through the interface-output FIFO only when the next
  parser byte is `0x11` and the active record word is `1` or `-1`.
- `ESC *b#W`, handler `0x011f82`: transfer raster row bytes.
- `ESC *p#X`, handler `0x00f48c`: horizontal dot position.
- `ESC *p#Y`, handler `0x00f692`: vertical dot position.
- `ESC *c#P`, handler `0x010898`: fill rectangle; consumes size state
  and queues rule object.
- `ESC *c#A`, handler `0x010e68`: rectangle width in dots into
  `0x78316a`.
- `ESC *c#B`, handler `0x010e22`: rectangle height in dots into
  `0x783166`.
- `ESC *c#G`, handler `0x010dce`: area fill id into `0x78316e`.
- `ESC *c#H`, handler `0x010a40`: rectangle width in decipoints into
  `0x78316a`.
- `ESC *c#V`, handler `0x010ae0`: rectangle height in decipoints into
  `0x783166`.
- `ESC *c#D`, handler `0x015a56`: assign font ID.
- `ESC *c#E`, handler `0x015a18`: select current downloaded
  character/code.
- `ESC *c#F`, handler `0x016df6`: font control.
- `ESC (#A..^`, handler `0x0120be`: primary font-designation family;
  symbol set, `#X` font ID, and `3@` default font.
- `ESC )#A..^`, handler `0x0120be`: secondary font-designation family;
  symbol set, `#X` font ID, and `3@` default font.
- `ESC (s#P` / `ESC )s#P`, handler `0x012082`: primary/secondary
  spacing.
- `ESC (s#H` / `ESC )s#H`, handler `0x012096`: primary/secondary pitch.
- `ESC (s#V` / `ESC )s#V`, handler `0x012046`: primary/secondary point
  size.
- `ESC (s#S` / `ESC )s#S`, handler `0x01206e`: primary/secondary style.
- `ESC (s#B` / `ESC )s#B`, handler `0x0120aa`: primary/secondary stroke
  weight.
- `ESC (s#T` / `ESC )s#T`, handler `0x01205a`: primary/secondary
  typeface.
- Lowercase font-selection chaining forms dispatch directly to request
  writers while parser mode `13` remains active: `p` -> `0xc930`,
  `h` -> `0xc89c`, `v` -> `0xc6ec`, `s` -> `0xc780`, `b` -> `0xc840`,
  and `t` -> `0xc7e0`. The uppercase `P/H/V/S/B/T` wrappers call the same
  writer family and then common refresh `0xc580`.
- `ESC (s#W` / `ESC )s#W`, handler `0x011f96`: delayed
  font/downloaded-character payload selector. Count `0` schedules
  `0x15d0a`; nonzero counts schedule `0x16c14`; successful glyph payloads
  later become printable page objects through `0x16498 -> 0x12f2e`.

## First Handler Observations

`ESC &l#A` at `0x00fc74` maps PCL page-size parameters into internal
page codes:

- `1` -> internal `6`
- `2` -> internal `2`
- `3` -> internal `5`
- `26` -> internal `1`
- `80` -> internal `0x88`
- `81` -> internal `0x87`
- `90` -> internal `0x89`
- `91` -> internal `0x8a`

It then rebuilds page-related state, including `0x782da2`, `0x782db2`,
`0x782db4`, `0x782dc0`, `0x782dce`, and `0x782dd0`, and calls shared
reset/layout helpers also seen in `ESC E`. Executable fixtures now pin
letter `ESC &l1A` as internal code `6`, width `3030`, height `2025`,
portrait margin `3150`, top offset `90`, and PCL `80` as internal code
`0x88` masking to geometry-table index `8`.

`ESC &l#O` at `0x010220` accepts orientation values below `2`, updates
`0x782da3`, rebuilds page geometry, updates `0x783160`, and reloads
current font/metrics state through tables rooted near `0x782ee6` /
`0x782ef6`. The letter landscape fixture pins active extents
`2025x3030`, landscape margin `2175`, printable extent `2125`, top
offset `100`, and the `0x103ea` threshold sequence
`2175, 2550, 2480, 2550`; a chained byte-stream fixture drives
`ESC &l1a1O` through `0xfc74` and `0x10220` with the same final
landscape state.

`ESC &l#P` at `0x00f9e8` handles page length in lines. The nonzero
parameter path reads current VMI from `0x783160`, multiplies it by the
absolute line count, converts the packed 12-subunit result back to whole
dots, then selects an internal page code from thresholds loaded by
`0x103ea`. Portrait checks internal codes `6`, `2`, `1`, then `5`;
landscape checks `6`, `1`, then `2`. Accepted values finalize pending
page state, store the selected code in `0x782da2`, store computed page
extent in `0x782dba`, recompute geometry, default text length, and cursor
state, and refresh the next text cursor through the same
`0x782dce + VMI * 18 / 25` rule. The fixture pins `ESC &l66P` at 6 LPI
as internal code `2`, page extent `3300`, top offset `90`, and following
printable `!` at compact coord `0x9001`. Zero VMI and too-long page
lengths are ignored. The zero-parameter branch is now modeled from
`0xfa62..0xfaa6` and `0xfb4a..0xfc52`: it flushes pending text through
`0xf34a`, publishes through `0xff1e`, waits through `0x9ac2`, copies
`0x782da6` to output byte `0x780e8f` and signals `0x780e26` through
`0x9b5e` when it differs from `0x780e8e`, then chooses default page code
`0x780e97` or fallback `2`. Fixture `0xf9e8 ESC &l#P converts VMI lines
to page length and selects internal page code` pins `ESC &l0P` with
fallback code `2`, extent `3300`, text bottom `3240`, output byte
`0x80`, and control word `1`.

`ESC &l#W` at `0x011f6e` is a delayed-payload boundary for vertical
forms control. It snapshots the six-byte parsed record through `0x121cc`
with delayed handler `0x12cfe`. The payload handler rewinds
`0x78299e`, reads the absolute byte count, consumes data through
`0xdace`, loads the VFC table rooted at `0x782dde`, derives bottom cache
`0x782dc2`, copies it into text-length bottom `0x782dd2`, and clears
modified-layout byte `0x782ee1`. The composed state model is in
`notes/semantic-state-model.md`. For the combined stream
`ESC &l4w4W 00 00 00 02 !`, lowercase `w` snapshots record
`80 77 00 04 00 00`, uppercase `W` leaves the pending snapshot intact,
`0x12218` restores the lowercase record, and the payload begins after
the uppercase terminator before `!` queues at compact coord `0x9001`.

`ESC &l#V` at `0x01280a` is the VFC table consumer. Disassembly shows it
uses current VMI `0x783160`, vertical cursor `0x782c8e`, top offset
`0x782dce`, line caches `0x782ede`/`0x782ee0`, and channel words from
`0x782dde` while searching for the requested channel. Fixture
`ESC &l2V!` anchors the forward in-text path: `0x1280a` searches channel
mask `0x0002`, finds line `1`, ensures a page root through `0x10084`,
resets horizontal cursor through `0xf06e`, flushes pending text through
`0xf34a`, writes y `176`, and queues the following `!` at compact coord
`0xb001`. A before-top `ESC &l2V!` fixture anchors
`0x128ae..0x128f4`: y `89` below top offset `90` normalizes to start line
`0`, then the same channel-2 search reaches line `1` and queues `!` at
compact coord `0xb001`. Fixture `ESC &l0V!` anchors the selector-zero
target-equal path through `0x12966..0x1299a`: it computes target y
`126`, leaves the current cursor unchanged, ensures the page root through
`0x10084`, and queues `!` at compact coord `0x9e02`. Fixture
`!\x1b&l0V!` anchors the selector-zero page-eject path through
`0x1299c..0x129c4`: it publishes the already queued `!` at compact coord
`0xbe02` through `0xf124`, resets x/y to `10`/`126`, and queues the
following `!` on a fresh page at compact coord `0x9001`. A selector-zero
start-after-text `ESC &l0V!` fixture anchors `0x1299c..0x12b92`: start
line `64` skips publication, writes top-of-form y `126`, and queues `!`
at compact coord `0x9001`. Fixture
`!\x1b&l2V!` anchors the wrap-hit path through `0x129c6..0x12af8`: it
publishes the old page at compact coord `0xde02`, wraps from start line
`3` to target line `1`, writes y `176`, and queues the following `!` on a
fresh page at compact coord `0xb001`. An empty-table `!\x1b&l2V!`
fixture anchors the wrap-no-hit path through `0x12a22..0x12a78`: it
publishes the old page at compact coord `0xde02`, writes top-of-form y
`126`, and queues the following `!` on a fresh page at compact coord
`0x9001`. A second `!\x1b&l2V!` fixture, with channel 2 at line `63`,
anchors the target-after-text bottom-recovery path through
`0x129ee..0x12b5a`: it publishes the old page at absolute compact coord
`0x4e02`, writes recovered y `104`, and queues the following `!` on a
fresh page at compact coord `0x3001`. A before-top `ESC &l2V!` fixture,
with channel 2 only at line `63`, anchors the non-publishing
target-after-text path through `0x129fc..0x12afc`: start line `0` skips
`0x12a12..0x12a1e`, writes recovered y `104`, and queues `!` at compact
coord `0x3001`. A start-after-text `ESC &l2V!` fixture anchors
`0x12a02..0x12afc` with an empty table: start line `64` skips
publication, writes recovered y `54`, and queues `!` at compact coord
`0x1001`. A default-table start-after-text `ESC &l2V!` fixture anchors
`0x12a7a..0x12af8`: start line `64` wraps to line `1`, skips
`0x12a8a..0x12aa2`, writes y `176`, and queues `!` at compact coord
`0xb001`. A line-63 start-after-text `ESC &l2V!` fixture anchors
`0x12a7a..0x12afc`: start line `64` wraps to line `63`, skips
`0x12a8a..0x12aa2`, writes recovered y `104`, and queues `!` at compact
coord `0x3001`. Direct high-start VFC fixtures also pin the alternate
start/recovery predicates away from the normal Letter page bottom:
`0x12a02..0x12afc` no-hit recovery, `0x12a7a..0x12afc` wrapped line-70
recovery, and selector-zero `0x12b5e..0x12b92` recovery. The composed
field groups, writers, readers, output effects, confidence, and
remaining ROM-local/external-boundary risk for this command family are tracked in
`notes/vertical-forms-control.md`.

`ESC &l#D` at `0x00c992` accepts absolute LPI values
`1,2,3,4,6,8,12,16,24,48`, treats zero as `12`, converts to packed line
advance as `3600 / LPI` twelfths, stores `0x783160`, and sets
modified-layout byte `0x782ee1`. `ESC &l#C` at `0x00cb00` converts
absolute VMI in 1/48-inch units using 75 packed subunits per unit,
accepts fractional values, stores `0x783160`, and leaves `0x782ee1`
clear when the converted VMI is zero. Both handlers reject values beyond
page extent `0x782dba` and, when pending text byte `0x782a6d` is set,
refresh vertical cursor `0x782c8e` to `0x782dce + VMI * 18 / 25`.

`ESC &l#E` at `0x00ece2` scales top-margin lines through current VMI,
rejects zero VMI or positions at/beyond page extent `0x782dba`, writes
top offset `0x782dce = top_margin - 0x782dbe`, recomputes default
text-length bottom via helper `0xea16`, and refreshes pending vertical
cursor with the same `VMI * 18 / 25` offset. `ESC &l#F` at `0x00ea9e`
scales text-length lines through VMI, rejects lengths beyond the remaining
page below current top margin, writes
`0x782dd2 = 0x782dce + text_length`, and uses `0xea16` to restore the
default bottom when the parameter is zero.

`ESC &l#L` at `0x00ee64` handles perforation skip. It rewinds to the
parser record, takes the absolute value of the parsed word, clears byte
`0x783191` for selector `0`, sets byte `0x783191` for selector `1`, and
leaves the byte unchanged for other selectors. The same byte is tested in
the vertical overflow/recovery path at `0xf36c`, making it part of page
advance behavior rather than printable glyph placement. Fixture
`0xf36c perforation skip gates vertical overflow page eject` pins the
consumer predicate: `0xf36c` calls `0xf124` and returns `D7 = 0` only
when `0x782c8e > 0x782dc2`, `0x782dc2` is nonzero, and `0x783191` is
nonzero. The `ESC &l1L!` fixture proves the normal parser reaches
`0xee64`, records `0x783191` changing from `0` to `1`, then queues the
following printable `!` through `0xd04a` at the unchanged origin.

`ESC &l#X` at `0x00eef0` handles number of copies. It rewinds to the
parser record, takes the absolute value of the parsed word, ignores zero,
clamps values above `99`, and stores the result in word `0x782da4`. The
`!\x1b&l2X\f` fixture proves that copy count `2` survives a later FF
publication: `0xff1e` copies `0x782da4` into published pool-header word
`+0x0c`, then `0x1edc6` and `0x1ed84`/`0x1ef6a` render the queued compact
text rows unchanged.

`ESC &l#H` at `0x00ef62` handles page eject and paper-source selection.
It rewinds to the parser record, normalizes the absolute selector, flushes
pending text through `0xf34a`, publishes the current page root through
`0xff1e`, and refreshes the cursor through `0xf8fc`. The selector table at
`0xef3a` maps `0` to the page-eject arm `0xefae`, `1` to `0xefb6`,
`2` to `0xefe8`, `3` to `0xeff0`, and other values to `0xeff8`. The
`!\x1b&l2H` fixture proves selector `2` writes manual-feed value `0x80`
to `0x782da6`, sets pending-status byte `0x782998`, ORs bit 0 into
`0x780e26` when the output path is available, clears the current page root,
and publishes the queued compact text bucket before the paper-source state
change.

`ESC &a#L` at `0x00eb58` converts the absolute parsed column count
through current HMI `0x78315c`, rejects values beyond `0x782dda - HMI`,
and writes the accepted value to left margin `0x782dd6`. When the
accepted margin is right of current cursor `0x782c8a` or pending text is
marked, it also moves the cursor and flushes pending spans through
`0x12714` / `0x126e2` when span flushing is enabled. `ESC &a#M` at
`0x00ec0c` converts `abs(parameter) + 1` columns through HMI, rejects
values before `0x782dd6 + HMI`, clamps beyond page width `0x782db8`,
writes right margin `0x782dda`, and can move `0x782c8a` left while
setting right-limit latch `0x782a57`.

`ESC &a#C` at `0x00f39e` and `ESC &a#H` at `0x00f416` both convert the
parsed decimal parameter into packed twelfths and commit through
`0xf4ca`, which applies relative moves when parsed-record bit 0 is set,
clamps between zero and `0x782db8`, updates the right-limit latch
against `0x782dda`, clears pending text, and updates active span state.
`ESC &a#C` scales through current HMI `0x78315c`; `ESC &a#H` uses five
packed subunits per decipoint.

`ESC &a#R` at `0x00f560` and `ESC &a#V` at `0x00f60a` commit through
vertical helper `0xf6e2`, which ensures a page root, clears/flushes
pending text state, adds either current vertical cursor `0x782c8e` for
relative moves or top offset `0x782dce` for absolute moves, clamps
against lower bound `0x782dca`, and writes `0x782c8e`. The row command
scales through VMI `0x783160` and adds fractional `0.7200` for absolute
row moves before conversion; the decipoint command uses five packed
subunits per decipoint and clamps to `0x782dc6`.

`ESC &k#H` at `0x00ca8c` handles horizontal motion index. It rewinds to
the parser record, takes the absolute integer/fraction pair, rejects
integer values above `0x348`, scales accepted values by 30 packed
subunits per HMI unit, and stores the packed result in `0x78315c`.
The `ESC &k6H!!` fixture proves `6H` stores packed HMI `15`, so two
following printable `!` bytes queue at compact coords `0x0600` and
`0x0501` rather than the initialized `LINE_PRINTER` `18`-pixel spacing.

`ESC *p#X` at `0x00f48c` and `ESC *p#Y` at `0x00f692` are the dot-unit
counterparts to the `ESC &a` cursor-position commands. Both rewind the
current parsed record, sign-extend the parsed word, shift it left 16
bits into a whole-dot packed coordinate, and use parsed-record bit 0 as
the relative flag. Horizontal dot positioning commits through `0xf4ca`;
vertical dot positioning commits through `0xf6e2` and clamps to
`0x782dc6`.

`ESC &s#C` at `0x00edb0` rewinds the parsed record and writes the
end-of-line wrap flag at `0x783190`: selector `0` stores `1`, selector
`1` clears it, and other values leave the previous state untouched.
Printable prechecks `0xd28a` and `0xd6bc` test this flag and call
`0xf054` for enabled-wrap horizontal recovery, so wrap mode is part of
the page text-layout state rather than parser-only metadata.

`ESC &p#X` at `0x011f5a` is a delayed transparent-print-data boundary.
It saves handler `0x12452` through `0x121cc`; after `0x12218` restores
the saved command record, `0x12452` consumes the absolute byte count
from the host byte source, stops on `D7=-1`, normalizes `0x1a 0x58` to
`0x7f`, sends printable bytes through `0xd04a`, and sends filtered
control bytes through `0xd0f0` depending on the active symbol/high-byte
state.
See [transparent-print-data.md](transparent-print-data.md) for the
tracked behavioral note and fixture evidence.

`ESC *r#A` at `0x01075a` starts raster graphics by setting state in the
block rooted at `0x783170`. Portrait raster origin seeds from horizontal
cursor `0x782c8a`; landscape raster origin seeds from vertical cursor
`0x782c8e`.

`ESC *b#W` at `0x011f82` routes through `0x121cc` with handler
`0x105d0`, so raster row byte transfer is tied into the same
parsed-command/data chain used by macro/download payload handling. The
full raster command/data, queue, and render-dispatch edge is documented
in [raster-graphics.md](raster-graphics.md).

`ESC *r#B` at `0x0107fa` clears raster active byte `0x783182`, leaving
raster origin/baseline/mode/scale/limit state intact so later resolution
commands can take effect. A host-fetched stream now proves `ESC *rB`
clears active state between a queued `ESC *b2W` row and a following
`ESC *t150R` mode/scale update. A separate host-fetched active-raster
stream proves an in-raster `ESC *t75R` still dispatches to `0x10808` but
leaves the current mode/scale/limit intact before the next `ESC *b2W`
row.

Rectangle graphics command edges are documented in
[rectangle-graphics.md](rectangle-graphics.md). `ESC *c#A/#B` store
explicit positive dot width/height in `0x78316a` / `0x783166`, while
missing or nonpositive values clear the corresponding state.
`ESC *c#H/#V` convert decipoints through five 300-dpi subunits per
decipoint, round up with the firmware's `+11` subunit bias, and store
the same width/height words. `ESC *c#G` stores absolute nonzero
area-fill id `0x78316e`; missing or zero clears it. A chained
`ESC *c12a5b0P` byte-stream fixture now queues the same black selector-7
rule object as the modeled command state, and the harness traces the
same stream through ROM parser modes
`0 -> 1 -> 3 -> 16 -> 16 -> 16 -> 0` to handlers `0x10e68`, `0x10e22`,
and `0x10898`; the stream now also drains from modeled `0xa904` ring
fetch before pinning the `0x1edc6` rule-list bridge contract and the
`0x1ed84`/`0x1ef6a` render-entry path. `ESC *c#P`
maps black rule, gray-scale, and HP-pattern selectors, clips the
current-cursor rectangle against page extents, and queues a 14-byte
rule-list object through `0x13386` / `0x133aa`; the black selector-7
path is rendered through `0x1f446` / `0x1f596`, including a
band-crossing continuation case, and gray selectors `0..6` plus HP
pattern selectors `8..13` are rendered through `0x1f446` / `0x1f4e0`,
including sub-byte shifted, band-crossing, and two-band page-assembly
HP-pattern cases. The harness also pins a parser-to-retry boundary for
the same `ESC *c12a5b0P` stream: after handlers `0x10e68`, `0x10e22`,
and `0x10898` select the rule object, the `0x10d22` no-room path marks
root flag bit 0, publishes through `0xff1e`, allocates a fresh root
through `0x10084`, retries the selector-7 rule through `0x13386`, and
renders the retried object after `0x1edc6`.

`ESC &f#Y` at `0x00e112` stores the absolute parsed signed word into
current macro id `0x783164`. `ESC &f#X` at `0x00dd08` uses that id with
the 32-entry macro record pool at `0x782a98`: selector `0` starts
definition, `1` stops definition, `2` executes, `3` calls, `4`/`5`
enable/disable overlay, `6` deletes all, `7` deletes temporary, `8`
deletes current id, and `9`/`10` mark temporary/permanent. Lookup helper
`0xe0a4` accepts an existing id only when record `+0` is nonzero,
otherwise remembers the first zero-head slot as reusable even if its id
word is stale; the helper returns status `1` for existing, `0` for
free-slot assignment, and `2` for a full-pool miss. Execute/call
route through `0xe418`, which builds a data-chain frame with byte
`+8 = 4`, byte `+9 = 2` or `3`, macro record `+0x00/+0x04` copied into
frame `+0x00/+0x04`, and an environment snapshot pointer at frame
`+0x0a`; call mode also pushes a 10-byte context-stack entry through
`0x782c6e`. The `0xe8f0`/`0xe8a2` helpers store and restore those
snapshots as 0x100-byte linked chunks, and `0xe22c` unwinds execute/call
frames after `0xa904` sees the frame-end marker. `0xe22c` also pins the
non-execute/call flat return: 281 longwords from `0x7834c2` restore
`0x782d3a..0x78319a`, `0x782d76` stays on the same frame, host gate bit
1 clears for zero count, cursor `0x782c92` restores to `0x782c8a`, and
`0x782a92` becomes `0x63`. Producer `0xe4f4`, reached from `0xff8e`,
builds that frame at `0x782d4c` with byte `+9 = 4` after snapshotting
`0x782d3a..0x78319a` to `0x7834c2`. The executable harness now pins
these command side effects, frame metadata, shared heap
allocation/free, and `0xe65c` font-context refresh paths. `0x170c` /
`0x1710` allocate 64-byte units, `0x100` requests consume four units,
and `0x18b4(ptr, 0, 0x100)` follows linked 0x100-byte chains through
their first longword. `0xe002` appends definition bytes into those chunks:
record `+0x04` is a raw count including four header bytes per chunk,
each 0x100-byte chunk stores 252 payload bytes after its next pointer,
and selector `1` stop subtracts that header overhead before deciding
whether to clear one-byte or auto-prefix-only definitions. `0xe65c(0)`
pops the call context stack at
`0x782c6e`, while `0xe65c(1)` consumes static record `0x782c64`. Entry
bytes `+8/+9` refresh primary/secondary slots through `0x13eb8(0/1)`,
copy active words `0x783144`/`0x783146` to remembered words
`0x782f08`/`0x782f0a`, pass selected slot `0x782f06` through `0xc428`,
optionally rebuild selected context `0x782ee6 + 0x10*slot` from
`0x782c80`/`0x782c84` through `0x1b4c0`, `0x144d2`, and `0x14c64`, then
exit through `0x1b04c` with dirty flag `0x782f2d` cleared. Fixture
`0xe65c refresh composes with font context bridge` now proves those
refresh decisions feed `0x13eb8` map rebuilds at `0x782f32` / `0x783032`
and the final `0xc428` page-root context install. The
non-replay producer calls `0xe5e2` before writing frame byte `+9 = 4`;
that helper refreshes top offset, text-bottom cache, margins, VFC line
counts, default VFC table, modified-layout byte, and static
font-context record `0x782c64`. `0xe146` clears exactly eight macro
context records at `0x782c1e..0x782c6d`; unlike the separate
`ESC &f#S` cursor stack at `0x782c96..0x782d36`, the macro call-context
push/pop paths have no observed bounds checks. Chained
`ESC &f-123y0x1X`,
`ESC &f123Y ESC &f0X ! CR ESC &f1X ESC &f2X`,
`ESC &f123Y ESC &f0X ! CR ESC &f1X ESC &f3X`,
`ESC &f123Y ESC &f0X ! CR ESC &f1X ESC &f4X ESC &f5X`,
permanence/delete, delete-current, delete-all, and guard-state
byte-stream fixtures that cover signed id assignment, definition payload
storage, stop-kept cleanup, execute/call frame creation, overlay
enable/disable state, selector `10` survival through delete-temporary,
selector `9` making the record removable, selector `8` clearing only the
current id, selector `6` clearing pool records, definition-mode and
active-data-chain guard suppression, the same definition stream draining
from modeled `0xa904` ring fetch before the alternate parser stores
payload and exits through `0xdd08`, the complete command streams
draining from modeled `0xa904` ring fetch into those records and frames,
the full define-and-execute and define-and-call streams draining from
modeled `0xa904` ring fetch through the ROM/alternate parser trace into
the execute/call data-chain frames, `0xa904` data-chain byte fetch and
end-marker outer-source resumption for stored execute/call payloads,
replayed `!\r` parser dispatch through `0xd04a`/`0xf02c`, modeled
printable/CR processing, the page-record allocator/bridge shape for that
payload, and a stored `ESC &k1G!\r!` mixed-control macro payload
replaying through a host-fetched ROM/alternate parser trace, `0xa904`
data-chain fetch, and `0xedf8`/`0xd04a`/`0xf02c`/`0xd04a` into rows that
match the direct mixed-stream model. The execute, call, and
mixed-control replay payloads now also preserve the `0x1edc6`
bucket/context bridge contract and feed `0x1ed84`/`0x1ef6a` before
rendering. Selector `4` overlay publication is also fixture-backed:
`0xff1e` resolves `0x782a94` through `0xe0a4`, builds a non-replay frame
with `0xe4f4`, re-enters `0x11774`, queues the stored `!\r` payload into
the current page record, and publishes/render-composes it with an existing
selector-7 rectangle rule. Evidence: fixture `macro overlay finalization
replays before page publication`. Overlay replay now also covers a payload
matrix across text/control, transparent-data, raster, and span-flush families:
`ESC &k1G!\r!`, `ESC &a2C!`, `ESC &a72V!`, `ESC &a2c+1R!`,
`ESC &a6l9M!`, `ESC &p2X!!`, `! ESC *t300R ESC *r0A ESC *b2W c3 3c`,
the multi-row raster sibling, and `ESC &a6L!`. Those fixtures prove
non-replay frames re-enter `0x11774`, route through the normal command
handlers, queue compact text, transparent printable bytes, raster objects, or
span-list objects as appropriate, preserve the existing selector-7 rule, and
publish/render through `0x1ed84` / `0x1ef6a`. Evidence: fixtures
`macro overlay mixed-control payload publishes with page rule`,
`macro overlay cursor-position payload publishes with page rule`,
`macro overlay vertical-decipoint payload publishes with page rule`,
`macro overlay chained cursor-position payload publishes with page rule`,
`macro overlay chained margin payload publishes with page rule`,
`macro overlay transparent payload publishes with page rule`,
`macro overlay raster payload publishes with page rule`,
`macro overlay multi-row raster payload publishes with page rule`, and
`macro overlay span-flush payload publishes with page rule`. The composed
semantic checkpoint is in
`notes/semantic-state-model.md` under
`Macro Definition And Data-Chain Replay`; no macro replay/font-context
middle edge remains in that checkpoint. Fixture
`0xe860 reads inline +0x16 and offset-table +0x20 class bytes` names the
last resource-format split: inline/downloaded records use `+0x16`, and
bit-30 offset-table/built-in records use `+0x20`.

The `ESC &f-123y0x1X` fixture is now also traced through ROM parser
modes `0 -> 1 -> 5 -> 17 -> 17 -> 17 -> 0`, selecting `0xe112`,
`0xdd08`, and `0xdd08` for records `81 79 ff 85 00 00`,
`80 78 00 00 00 00`, and `80 58 00 01 00 00`.

The macro-definition fixture also proves the alternate/data parser table
behavior after `ESC &f0X`: payload bytes `21 0d` are stored with no
alternate-table handlers, the normal CR handler `0xf02c` is suppressed,
and `ESC &f1X` still walks alternate table `0x116f6` to `0xdd08` to stop
definition mode.

`ESC &f#S` at `0x00f75e` uses the absolute parsed word as a cursor-stack
selector. Selector `0` pushes the current horizontal cursor `0x782c8a`
and the current vertical cursor plus `0x782dbe` as an 8-byte entry while
the next-free pointer is below `0x782d36`; selector `1` pops while above
stack base `0x782c96`, restores horizontal and vertical positions with
current page-extent clamps, clears pending/right-limit flags, and
flushes pending spans when enabled. Executable fixtures now pin push,
pop, clamp, full-stack, empty-stack, byte-stream `ESC &f0S`/`ESC &f1S`
selector-path cases, and `ESC &f0S ESC &a2C ESC &f1S!` restoring the
original cursor before printable `0xd04a` queues at compact coord
`0x0001`.

Primary and secondary font-selection commands share the same parser
shape, with the `ESC (` versus `ESC )` distinction preserved by setup
routines before mode 4. The harness now traces primary
`ESC (s0p10h12v0s0b3T` and secondary `ESC )s0p16h8v0s0b0T` through
ROM table `0x11774`: modes advance `0 -> 1 -> 4 -> 13`, lower-case
attribute finals stay in mode 13, and the upper-case typeface final
returns to mode 0. The lower-case finals route directly to spacing
`p` handler `0xc930`, pitch `h` handler `0xc89c`, point-size `v`
handler `0xc6ec`, style `s` handler `0xc780`, and stroke `b` handler
`0xc840`. Upper-case terminal wrappers refresh after one writer:
`V` routes through `0x12046 -> 0xc6ec -> 0xc580`, `S` through
`0x1206e -> 0xc780 -> 0xc580`, `P` through
`0x12082 -> 0xc930 -> 0xc580`, `H` through
`0x12096 -> 0xc89c -> 0xc580`, `B` through
`0x120aa -> 0xc840 -> 0xc580`, and final `T` through
`0x1205a -> 0xc7e0 -> 0xc580`. The primary/secondary selector is not the
terminal record
fraction word: `0x11f26` / `0x11efe` first create a setup record whose
word `+2` is slot `0` / `1`, and the update handlers recover that setup
word while the terminal record word `+4` remains the decimal fraction.
A bridge fixture now decodes the parsed primary records into concrete
filter inputs: `0p` -> spacing `0`, `10h` -> pitch `0x03e8`, and `12v`
-> height `0x04b0`. The same fixture pins the updater writes before
common refresh: typeface byte `0x782eec = 3`, style `0x782eed = 0`,
stroke `0x782eee = 0`, spacing `0x782eef = 0`, pitch
`0x782ef0 = 0x03e8`, height `0x782ef2 = 0x04b0`, dirty refresh flag
`0x782f2c = 1`, and metric dirty flag `0x782f2d = 1`. Feeding those
values into the real class-zero built-in candidate window after the
Roman-8 symbol filter narrows survivors from slots `0x782354`,
`0x782364`, and `0x782374` to `0x782354` / `0x782364`; that
chooser-only bridge still proves isolated `0x14398` behavior by selecting
built-in record `0x009fb0`. The fuller `0x13eb8` fixture now follows
`0x148f8`, `0x1569c`, `0x156de`, `0x153c6`, `0x1519a`, `0x147b2`,
`0x14758`, `0x14398`, `0x144d2`, and `0x14c64`: for the same parsed
primary request, stroke filter `0x14758` prunes `0x009fb0`, leaving
slot `0x782354` / record `0x00004c`; `0x144d2` writes context
`0x782ee6`, and `0x14c64` rebuilds the primary map. The secondary
fixture drives `ESC )s0p16h8v0s0b0T` through the same wrapper with class
selector `1`: symbol filtering keeps slots `0x782330`, `0x782340`, and
`0x782350`, nearest-pitch filtering selects `0x782350` / record
`0x02e122`, context `0x782ef6`, and map `0x783032`. The transient
`0x78298f` exit now proves selected-context staging plus active-word
restore without `0x144d2`/`0x14c64`; the `0x148f8` cache-hit exit returns
before list activation. Fixture
`0x13eb8 no-dispatch exits keep prior visible rows` carries those exits into
visible output: the transient path stages `0xc008004c` but following `!!`
renders from prior context `0xc0089fb0`, while the secondary cache-hit path
crosses SO and renders from prior context `0xc40ad87a`.

Primary and secondary font-designation commands use the normal parser
shape. `ESC (` calls setup `0x1201e`, which pushes slot word `0`;
`ESC )` calls setup `0x12008`, which pushes slot word `1`; final bytes
`@` through `^` dispatch to `0x120be`. In alternate/data mode, table entries
`0x11fe4` and `0x11fd2` only call generic setup `0x11ec8` and then tokenize
through `0xdaf0`; they do not append the synthetic primary/secondary slot
record before tokenization. The normal terminal wrapper calls `0x1be22`,
which computes the provisional PCL symbol word as
`(parameter << 5) + final_byte - 0x40` and stores it at
`0x782ef4 + 0x10*slot`. Normal symbol-set finals keep that word and call
common refresh `0xc580`; final `X` restores the previous requested symbol
word and calls `0x17708` for `ESC (#X` / `ESC )#X` font-ID selection;
final `@` runs a numeric table where `3@` is the documented default-font
command and `@0..@2` are firmware-supported table/copy variants. The
active selected words later consumed by glyph-map patching are `0x783144`
and `0x783146`; this path is detailed in
`generated/analysis/ic30_ic13_active_symbol_set_flow.md`.

The `ESC (7X` special-case fixture now exposes the upstream split before
common refresh: final `X` restores the previous requested word, sets
`0x78287b`, calls `0x17708(slot, parameter)`, and enters `0xc580` with
dirty flag `0x782f2c = 2`; normal symbol-set finals and final-`@`
subtable paths enter `0xc580` with dirty flag `1`.

The direct `0x17708` fixtures now pin the successful font-ID selection
side effects after that parser boundary. A bit-30 built-in current
record scans through `0x172c0`, resolves its candidate slot through
`0x1b4c0`, checks record byte `+0x20` against `0x782da3`, optionally
reuses a page-root slot through `0xc4fc`, writes selector `0x7828de`,
stores the candidate slot pointer at `0x7828a8`, writes active word
`0x783144` through `0x15890`, calls `0x1b2fe`, and dispatches
`0x14c64`. The bit-30-clear inline/downloaded path is the parallel
secondary-slot form: it checks byte `+0x16`, writes active word
`0x783146` through `0x158be`, and enters `0x14c64` for the secondary
glyph map. Fixture `font-ID built-in selection feeds visible page-record
rows` now carries the bit-30 built-in success path through visible output:
host-fetched `ESC (7X!!` reaches parser handlers `0x11eb6`, `0x1201e`, and
`0x120be`, selects context `0xc0089fb0` through `0x17708`, queues compact
object prefix `00 00 00 00 00 00 00 02 00 89 00 00 87 02`, and renders row
digest `73cbb28bfab786807b9a3186eb3946efae550cde2e5448f0549f88ebf8c8a631`.
Fixture `font-ID secondary built-in selection feeds visible SO page-record
rows` carries the class-one bit-30 built-in sibling through visible output:
host-fetched `ESC )8X SO !!` reaches parser handlers `0x11eb6`, `0x12008`,
and `0x120be`, selects context `0xc00ae122` through `0x17708`, reuses
page-root slot `1` through `0xc4fc`, crosses SO handler `0xc6b8`, queues
compact object prefix `00 00 00 00 00 01 00 02 00 c9 00 00 cb 01`, and
renders row digest
`b8ee0f8dd3e6ed70afa219bc00605d75249ae047a67fb67189693057d7936e6c`.
Fixture `font-ID inline/downloaded selection feeds visible page-record rows`
now carries the bit-30-clear success path through visible output too:
host-fetched `ESC )4660X SO !` reaches parser handlers `0x11eb6`, `0x12008`,
and `0x120be`, selects context `0x00000100` through `0x17708`, rebuilds
secondary map `0x783032`, crosses SO handler `0xc6b8`, queues compact object
prefix `00 00 00 00 00 01 00 01 01 66 01 00 00 00`, and renders row digest
`e0c6cbbf133aaaf522868ef7f28856f06b0d54b4dd9368a090fe7c85e7b1d563`.
Fixture `font-ID primary inline/downloaded selection feeds visible page-record
rows` covers the slot-0 sibling: host-fetched `ESC (4660X!` reaches parser
handlers `0x11eb6`, `0x1201e`, and `0x120be`, selects the same
bit-30-clear context `0x00000100` through `0x17708`, rebuilds primary map
`0x782f32`, queues compact object prefix
`00 00 00 00 00 00 00 01 01 66 01 00 00 00`, and renders the same row digest.
Fixture `0x17708 font-ID non-selected exits preserve prior selection` covers
the direct helper exits that stop before a new map is dispatched: scan miss
after `0x172c0` status `1`, candidate-slot miss for payload `0x089fb0` with
no `0x1b4c0` slot, class mismatch at pointer `0x782364` when record class
`0xff` does not match wanted class `0x00`, and context-full when `0xc4fc`
returns page slot `0x11`. In all four cases the helper restores saved
`0x782f2e = 0x2222` and does not call `0x14c64`, so following printable output
continues from the prior selected font rather than a newly selected font ID.
Fixture `font-ID non-selected exits keep prior visible rows` pins that
following output: host-fetched `ESC (7X!!` uses the same parser record and
then renders `!!` from prior context `0xc008004c`, compact object prefix
`00 00 00 00 00 00 00 02 00 6a 00 00 68 02`, and row digest
`8b36cfd64d818c0982b172982156f8be9687388c9679cd83538c9d1098d9bb2c`.
Fixture `font-ID secondary non-selected exits keep prior SO visible rows`
pins the slot-1 sibling: host-fetched `ESC )8X SO !!` takes the same
`0x17708` terminal states with no `0x14c64` dispatch, crosses SO handler
`0xc6b8`, and renders from prior secondary context `0xc40ad87a` with compact
object prefix `00 00 00 00 00 01 00 02 20 c9 00 20 cb 01` and row digest
`b8ee0f8dd3e6ed70afa219bc00605d75249ae047a67fb67189693057d7936e6c`.

The harness now pins the concrete common-refresh branch classes from `0xc580`.
With dirty flag `0x782f2c = 1`, parser/setup slot `D5 = 0`, current
selector `0x782f06 = 0`, a present page root, and no live page-root font
slots at `0x78297f..0x78298e`, the routine finds slot `0` available,
runs `0xc4fc(0x782992)`, calls candidate refresh `0x13eb8(0)`, and
then calls `0xc428(0)`. The same first-clear-slot path is pinned for
secondary slot `D5 = 1`, where `0xc428` selects context record
`0x782ef6` instead of `0x782ee6`. When all 16 live flags are set and
`0xc4fc` can match the existing context, `0xc580` briefly sets
`0x78298f = 1`,
calls `0x13eb8(0)`, clears `0x78298f`, reuses the existing page-root
context slot, calls `0x13eb8(0)` again, and then calls `0xc428(0)`.
When all 16 live flags are set and `0xc4fc` finds no matching context,
the helper returns `0x11`; `0xc580` skips the second `0x13eb8` and
`0xc428` install. A dirty-1 selector mismatch (`0x782f06 != D5`) takes
the short `0x13eb8(D5)` branch and also skips `0xc4fc` / `0xc428`.
For dirty flag `2`, `0xc580` does not call `0x13eb8`: selector match
calls only `0xc428(D5)` for both primary and secondary slots, while
selector mismatch only reaches the final active-to-remembered word copy.
The modeled `0xc4fc` scan accepts an existing low-24-bit context match
before looking for the first inactive slot, then writes or reuses the
current font-context record pointer in page-root slot `+0x2c + 4*n`.
`0xc428` selects that page-root context slot by writing `0x78297e`. It
does not mark `0x78297f+n` live; the printable producer path marks that
live flag when text is queued. Each non-returning branch ends by copying
active word `0x783144 + 2*D5` into remembered word `0x782f08 + 2*D5`
and clearing `0x782f2c`.

The harness now includes a concrete `ESC (2U` / `ESC )0E` stream fixture
that records the six-byte terminal records, refreshes active
primary/secondary words, and applies the resulting `0x0055` patch-table
and `0x0005` Roman Extension map rules to the `LINE_PRINTER` built-in
map. ROM parser traces prove that stream reaches setup handlers `0x1201e`
/ `0x12008` and terminal handler `0x120be`, and a second trace proves
host-visible `ESC (7X`, `ESC )0@`, `ESC (1@`, `ESC )2@`, `ESC (3@`, and
`ESC )3@` streams reach the same terminal handler before the model takes
the `X` font-ID and `@0..@3` special-case targets. The same harness now
pins `0x1a9be` scanner-side candidate-list partitioning for both
synthetic and real `IC32,IC15` built-in records, `0x1ac0a`
current-candidate and synthesized default-table writes plus `0x1af36`
fallback table writes, pins `0x1b250` disabled/resolved/remapped
current-default results, pins `0x1b50e` fast-probe/two-pass resolver
classes and Roman-8 duplicate ordinal behavior, pins `0x1ab84`
synthesized search, pins `0x1ad66` as a range-1, range-2, then
`0x1ae7e` fallback search, and models `0x1bbfe` / `0x1b060` from
candidate record fields. Parser-derived `ESC (1234U` and `ESC )1234U` misses
now feed `0x156de`: requested word `0x9a55` misses the class-zero candidates
and falls through to fallback-table word `0x0115` for the primary stream.
For the secondary stream, the same requested word misses class-one candidates
and is now covered both through remembered word `0x000e` at `0x782f0a` before
fallback and through fallback-table word `0x000e` when remembered recovery is
not available. Remaining default-font
uncertainty is narrowed further by real scanned built-in fallback
coverage: class-zero candidates feed `0x1b060` and choose record
`0x00004c` by Roman-8 fallback for requested `0x0005`, while class-one
candidates choose record `0x01a984` by exact symbol `0x000e`. Real
scanned windows also feed mode-3 `0x1b50e`: ordinal 1 selects slot
`0x782354` / record `0x08004c`, a non-Roman-8 duplicate ordinal 2
returns requested word `0x0005`, and current-slot duplicate suppression
advances to slot `0x782358` / record `0x080418`. The same real windows
feed `0x1ab84` after its orientation flip, selecting record `0x00004c`
by Roman-8 fallback and record `0x01a984` by exact `0x000e`; real
`0x1b50e` results also feed `0x1b250`, where `0x00004c` maps to slot
`0x782354` after boundary `0x7827ac` and `0x01a984` maps to slot
`0x782330` before it. A real-backed `@0`/`@1`/`@2`/`@3` caller stream
now routes through ROM terminal handler `0x120be` and consumes those
table/default-font words through the same default-table/copy/default-font
subdispatch. Fixture `real final-@ default-table streams select visible
built-ins` appends primary `ESC (s0p10h12v0s0b3T!!` and secondary
`ESC )s0p16h8v0s0b0T SO !!` tails to that caller stream. The final active
words `[0x000e, 0x0005]` select primary context `0xc0080cb8` and secondary
context `0xc00ad4aa`, queue the same compact object prefixes as the pinned
primary non-Roman and secondary SO streams, and render row digests
`8b36cfd64d818c0982b172982156f8be9687388c9679cd83538c9d1098d9bb2c` /
`b8ee0f8dd3e6ed70afa219bc00605d75249ae047a67fb67189693057d7936e6c`.

Downloaded-font command edges are now decoded in
`generated/analysis/ic30_ic13_font_control_flow.md`. `ESC *c#D`
normalizes the parsed signed word into current font id `0x782f2e`,
mapping `-32768` to `0x7fff`; `ESC *c#E` applies the same normalization
to current character/code word `0x782f30`. The executable harness now
traces chained `ESC *c17d25e5F` through the ROM `0x11774` dispatch
table, proving parser modes `0 -> 1 -> 3 -> 16 -> 16 -> 16 -> 0`,
records `ESC *c17d`, `25e`, and `5F`, and handlers `0x15a56`, `0x15a18`,
and `0x16df6` before the current-record mark side effect. A second
control-to-install fixture traces `ESC *c4660d37e5F` from the modeled
`0xa904` ring source, uses the resulting current font id `0x1234` and
current character `0x25` as the inputs to the descriptor and character
payload models, and proves the marked current record is the one
consulted by the following font `W` streams. `ESC (s#W` / `ESC )s#W`
reaches `0x11f96`: a zero count schedules delayed descriptor handler
`0x15d0a`, while any nonzero count schedules delayed payload installer
`0x16c14` with the absolute byte count in `0x783140`. The executable
harness also traces `ESC )s0W`, `ESC )s4W`, `ESC )s80W`, `ESC )s6W`, and the
full `ESC )s2193W` downloaded-character stream through the ROM `0x11774`
dispatch table, proving parser modes `0 -> 1 -> 4 -> 13 -> 0` and final
handler `0x11f96`; modeled descriptor and payload command/data wrappers
then restore six-byte records through `0x121cc` / `0x12218`, tie
`ESC )s0W` descriptor offsets and selector bytes to current-record and
continuation routes through `0x15d0a`, tie `ESC )s80W` to
resource-payload validation/allocation through `0x16c14` -> `0x16fae` ->
`0x17026` -> `0x1719c` plus candidate insertion through `0x1bc38`, and
tie the `ESC )s6W` and `ESC )s2193W` payload offsets, byte counts, linear
`0x168dc` bytes, split-plane tail, `0x16498` downloaded-pointer objects, and
rendered rows to the same parser trace. Fixture
`0x16c14 allocation failure releases existing payload through 0x1887a` pins
the replacement failure order: when `0x172c0` finds an existing current-record
payload, `0x16c14` releases it through `0x1887a` before the later allocation
failure skip, leaving no new candidate installed. The `ESC )s0W`, `ESC )s80W`,
`ESC )s6W`, and `ESC )s2193W` boundaries are now modeled as complete host
streams, with the larger descriptor/resource/downloaded-character streams also
ring-fed through modeled `0xa904`, proving their complete descriptor or payload
bytes reach the same parser handlers, delayed records, installed or rendered
objects, and rows where applicable; the fetched downloaded-pointer objects now
also preserve the `0x1edc6` bucket/context bridge contract and feed the
`0x1ed84`/`0x1ef6a` render-entry path before rendering.
A combined fetched `ESC *c4660d37e5F` + `ESC )s2193W` + printable `%`
stream now carries current character `0x25` through the installed glyph,
restores payload record `80 57 08 91 00 01`, queues segment buckets `9`
and `1`, preserves the segment-1 bucket root through `0x1edc6`, and
dispatches it through `0x1ed84`/`0x1ef6a`.
The `0x15d0a` descriptor stream must start with kind
byte `4`; selector byte zero scans the current downloaded-font record
and object flag bit 30 chooses `0x16498` downloaded-character allocation
when set or `0x16606` font-resource allocation when clear, while nonzero
selector bytes require continuation state `0x7827c6 == 1`, use saved
payload `0x7827da`, and choose resume helper `0x15b9a` or `0x15c4c` by
the same bit-30 test. The bit-30-clear `0x15c4c` path is fixture-backed for
both even fixed-record `02 03 04 00 00 00 02 00` and split-plane fixed-record
`03 02 04 00 00 00 02 00` continuation records, including saved A4/A3
destinations and D4/D3 counters; a status-0 resumed copy calls `0x17d7c` and
rewrites the released fixed-record entry to the fallback form
`01 02 00 fa 00 00 00 00` in the active-primary fixture. The bit-30 release
delegate is fixture-backed separately: `0x17d7c` calls `0x17a24`, which clears
the selected offset-table entry and refreshes the active secondary context.
The fixed-record `0xa0..0xff` release branch is fixture-backed for type byte
`+0x0e = 1`, with char `0xa1` rewriting the extended table entry and
refreshing the active secondary context.
`ESC *c#F` dispatches values `0..6` through the
table at `0x16db6`: values `0`, `1`, and `2` call all/current record
release helpers, value `3` uses the current character/code word
`0x782f30`, values `4` and `5` unmark/mark the current downloaded record
by moving counts between `0x782782` and `0x782786`, value `6` runs
active/current font-resource housekeeping, and other values no-op.

Page geometry and the first raster transfer path are tracked in
`notes/page-raster-imaging.md` and
`generated/analysis/ic30_ic13_raster_graphics_flow.md`. The important
anchors are that `0x105d0` clips/consumes raster payload bytes, ensures
the page/image root exists through `0x10084`, calls `0x13070` with the
raster state block rooted at `0x783170`, and then `0x138de` copies host
bytes into the queued raster object payload. Direct control-code
cursor/page effects are documented in
`generated/analysis/ic30_ic13_direct_control_code_flow.md`: `ESC &k#G`
stores line-termination bits in `0x78318f`, CR/LF/FF consume those bits,
and CR/LF/FF/HT/BS can update cursor coordinates, flush text spans,
ensure/finalize page roots, or call the same context span update
routines used by printable text. Normal printable text now has a live
parser bridge in `generated/analysis/ic30_ic13_printable_text_path.md`:
bytes flow through `0xa904` -> `0xda9a` -> `0x11774` -> `0xd04a`, then
`0x1393a` builds source object `0x782d7e`. The paired post-source paths
are documented in
`generated/analysis/ic30_ic13_text_cursor_span_flow.md`: unflagged text
uses `0xd140` / `0xd3b2` / `0xd4ac`, flagged text uses `0xd550` /
`0xd824` / `0xd8fc`, and the queue handoffs reach `0x12f2e`. Text and
rectangle/rule objects converge into the same page-object storage
through `0x12714` / `0x12f2e` and `0x13386` / `0x13520`;
`generated/analysis/ic30_ic13_page_root_allocation.md` decodes the
shared `0x10084` first-root allocation and `0x10110` selected-context
slot bootstrap, and
`generated/analysis/ic30_ic13_compact_bucket_allocator.md` decodes the
`0x1387c` compact bucket allocator under page-root `+0x1c`. The render
bridge now runs through page/control records copied by `0x1edc6` into
work records; its concrete queue/list/context-slot copy contract is
documented in `generated/analysis/ic30_ic13_page_record_bridge.md`.
`0x1efc2` classifies bucket objects so raster rows dispatch to
`0x1f88e`, compact text/glyph objects dispatch through `0x1effe`, and
rule lists render through `0x1f446` / `0x1f756`. Compact glyph and
encoded raster span modes are summarized in
`generated/analysis/ic30_ic13_render_subrenderers.md`; deterministic
encoded raster expansion fixtures are generated in
`generated/analysis/ic30_ic13_render_expansion_fixtures.md`;
destination/clipping fixtures are generated in
`generated/analysis/ic30_ic13_render_destination_fixtures.md`; compact
glyph row-copy fixtures are generated in
`generated/analysis/ic30_ic13_render_row_copy_fixtures.md`;
`tools/render_fixture_harness.py` executes these primitive fixtures
together, pins `0xa904` host byte fetch source-priority fixtures plus
the semantic host-input/data-chain field model,
ring-fed host-to-render boundaries for the direct text/control
page-record stream set through `0x1edc6` bridge fields, the
reset/FF/page-size/orientation/paper-source/copies publication streams,
addressed publication allocation variants for reset, FF, page-size,
orientation, paper-source, and copies, and the primary `ESC *t300R` /
`ESC *r1A` / `ESC *b4W`
raster stream through its raster bridge fields,
pins `0xdaf0`/`0xdb74` tokenizer records, `0x121cc`
delayed-payload snapshots, and `0x1228a`/`0x12358` alternate payload
byte-count consumers, pins synthetic direct control-code packed-state
behavior for `ESC &k#G` plus CR/LF/FF/HT/BS, adds direct-control
byte-stream fixtures for `ESC &k1G`+CR, `ESC &k2G`+LF, `ESC &k2G`+FF,
`ESC &k3G`+CR/LF/FF, `ESC &k0G`+HT/BS, `ESC &f0S`/`ESC &f1S`, chained
`ESC &l8c6d3e2F`, `ESC &l1L!`, `ESC &a3.5c+1R`, and `ESC &a6l9M`,
then groups the direct text/control family through host fetch,
page-record allocation, `0x1edc6`, `0x1ed84`, and `0x1ef6a`. It also
adds a cursor-stack page-record boundary for
`ESC &f0S ESC &a2C ESC &f1S!`, adds synthetic
`ESC E` reset byte-stream fixtures for valid-page-root publication and
missing-root clearing, ties missing-root `ESC E` to the modeled `0xa904`
ring source and ROM parser handler `0xcc52`, plus a ROM parser trace for
`!\x1bE`, `ESC &k2G!\f`, `!\x1b&l1A`, `!\x1b&l1O`, `!\x1b&l2H`, and
`!\x1b&l2X\f` through printable `0xd04a`, reset `0xcc52`,
line-termination `0xedf8`, FF `0xf0f0`, page-size `0xfc74`, orientation
`0x10220`, paper-source `0xef62`, and copies `0xeef0`, feeds four named real
built-in glyph bitmaps plus a ROM-scanned span matrix through the main
`0x1f08e` row-copy table, includes a producer-modeled short text bucket fixture
plus short and segmented `0x1387c` page-record allocator checks and a
`0x1edc6` page-record bridge fixture that copies the compact
bucket/context slots, normalizes the rule/fixed lists, pins
producer-shaped `0x13386`/`0x136d2` rule objects, and covers
text/rule/raster plus macro-payload rule/raster band composition, adds
parser-derived `ESC *t#R`/`ESC *r#A` raster state fixtures plus modeled
`ESC *t300R`/`ESC *r1A`/`ESC *b4W` with `0x10084` page-root allocation
before the primary queued row, `ESC *t150R`/`ESC *r0A`/`ESC *b2W`,
`ESC *t100R`/`ESC *r0A`/`ESC *b2W`, and
`ESC *t75R`/`ESC *r0A`/`ESC *b2W` command/data stream fixtures plus a
two-payload `ESC *t300R`/`ESC *r0A` multi-row stream through delayed
handler `0x0105d0`, a parser-to-gate edge check for
`ESC *t300R`/`ESC *r0A`/`ESC *b4W` capped and beyond-extent transfers,
an inclusive page-extent transfer check proving queue-and-advance
behavior, a negative-row transfer check proving drain-with-advance
behavior, a raster payload fixture proving `0xdace` turns host-fetched
raw bytes `1a 58` into a single queued `00` byte, same-group
lowercase-final chaining fixtures for host-fetched `ESC *t300r150R` and
host-fetched `ESC *b2w`/`2W` payloads, plus host-fetched `ESC *rB`
active-clear and following `ESC *t150R` mode/scale update, a
host-fetched active-raster `ESC *t75R` ignore check before `ESC *b2W`,
byte-aligned mode-0, non-byte-aligned mode-0, mode-1, byte-aligned
mode-2, non-byte-aligned mode-2, band-clipped mode-2, and mode-3 raster
row fixtures through `0x13070` / `0x13250` / `0x138de` / `0x1edc6` /
`0x1f88e`, covers normal and negative-left-overflow `0xd824` positioned
text bucket fixtures for the `0x14d9c` base-map -> `0x1393a`
source-object -> `0x12f2e` queue -> `0x1effe` / `0x1f034` render path,
adds one-byte and two-byte normal printable stream fixtures for host
byte `0x21` (`!`) through source mapping, positioning, packed default
cursor advance, same-bucket compact queueing, and rendering, pins
`0xd3b2` unflagged positioning arithmetic for both context-metric
branches, adds a selected inline/downloaded map/source fixture through
`0x14e24`/`0x14eb6` -> `0x1393a` -> `0xd3b2` -> `0x12f2e` -> `0x1edc6`
-> render plus `0x168dc`/`0x16942` font payload-reader fixtures
including a host-fetched `ESC )s18W` payload-control render-entry bridge,
an even-span wide `ESC )s18W` render-entry bridge with no control hits,
`0x172c0`/`0x16c14` downloaded-font record bookkeeping fixtures,
`0x170be`/`0x17108`/`0x17150` record lookup/mark/unmark fixtures,
`0x15a56`/`0x16df6` font-id/control dispatch fixtures, and
`0x16fae`/`0x17362`/`0x17026`/`0x1719c` validation-table/staged
header/payload-backed inline allocation fixtures, keeps synthetic
inline/downloaded `0x12f2e` short, page-record short, width-bit, and
segmented payload objects as isolation controls, constructs type-2
payload-backed selected inline `0x1f0d2` wide and `0x1f1f0` segmented
fixed-record payload rows, keeps a selected-memory `0x1f264`
segmented-wide isolation row, adds a `0x16498` downloaded-pointer
`0x1f264` segmented-wide row, pins even-span wide, even-span segmented, and
split-plane segmented downloaded-pointer producer/page-record objects through
`0x1f0d2` and `0x1f1f0`,
and adds a full built-in glyph coverage scan proving the verified ROM
resources contain no normal wide or non-mode-1 bitmap-entry cases for
`0x1f0d2`, `0x1f1f0`, or `0x1f264`.

The mixed text/control stream `ESC &k1G!\r!` now has an explicit
parser-to-page-record check: the ROM dispatch trace reaches handlers
`0xedf8`, `0xd04a`, `0xf02c`, and `0xd04a`, and the same byte stream
allocates one page-record root, reuses compact bucket `0`, bridges
through `0x1edc6`, and renders the expected post-CR rows.
`ESC &k6H!!`, `ESC &k2G!\n!`, `ESC &k0G HT BS !`, `ESC &a1L!`,
`ESC &a1M!`, `ESC &a6l9M!`, `ESC &a2C!`, `ESC &a72H!`,
`ESC &a1R!`, `ESC &a72V!`, `ESC *p30x30Y!`, `ESC &a2c+1R!`, and
`ESC &l3E!` now have the same boundary coverage for HMI handler
`0xca8c`, LF handler `0xf08c`, HT/BS direct-control handlers
`0xf1cc`/`0xf2a8`, left/right-margin handlers `0xeb58`/`0xec0c`,
chained lowercase-final margin handlers `0xeb58`/`0xec0c`,
cursor-position handlers `0xf39e`/`0xf416`/`0xf560`/`0xf60a`,
chained dot-position handlers `0xf48c`/`0xf692` in parser mode `18`,
chained lowercase-final `0xf39e`/`0xf560`, top-margin handler
`0xece2`, and perforation-skip handler `0xee64` followed by printable
`0xd04a`, queueing glyphs through the page-record allocator at compact
coords `0x0600/0x0501`, `0x3b00`, `0x0a01`, `0x0801`, `0x0a02`,
`0x0207`, `0x0a02`, `0x0402`, `0x1001`, `0x9001`, `0x9402`,
`0x1a02`, `0x9001`, and `0x0001`. A grouped host-fetch check now starts
that
direct text/control set from the modeled `0xa904` ring source and proves
the same parser handlers, delayed transparent-payload handler, bucket
indices, object prefixes, `0x1edc6` bridge fields, `0x1ed84` copy
fields, `0x1ef6a` setup/dispatch path, and rendered row counts.

The plain printable stream `!!` now has the same kind of check: both
bytes route through `0xd04a`, the initialized `LINE_PRINTER` HMI places
the second glyph at compact coord `0x0202`, and the page-record path
allocates one root, reuses bucket `0`, bridges through `0x1edc6`, and
renders the same rows.

The SI/SO stream `!\x0e!\x0f!` now pins both text-map polarities:
SO reaches handler `0xc6b8`, calls the modeled `0xc428(1)` install
success path, and sets `0x782f06 = 1`; SI reaches `0xc68a`, calls
`0xc428(0)`, and clears `0x782f06`. The following printable bytes queue
through `0xd04a` into selector-1 and selector-0 page-record objects, and
the `0x1ed84`/`0x1ef6a` dispatch renders those objects with context
slots `1` and `0`.

`ESC &p2X!!` now carries transparent print data into the same
page-record path: `ESC &p2X` routes through handler `0x11f5a`, restores
delayed handler `0x12452`, consumes the following two payload bytes
through `0xa904`, routes both payload bytes through `0xd04a`, queues
compact coords `0x0001` and `0x0202`, and renders the same rows as
plain `!!`. `ESC &p4X!\x05\x85!` now extends that evidence to the
default-filtered control route: C0 byte `0x05` and high-control byte
`0x85` route through `0xd0f0`, advance fixed spacing, queue no text
object, and leave the next visible `!` at compact coord `0x0604`.
`ESC &p3X!\x05!` now proves the same default-filtered C0 route in an
unflagged inline/fixed-record context: `0xd0f0` substitutes host `0x20`,
continues through `0xd140` / `0xd3b2`, maps glyph `0`, queues compact coord
`0x4802` in bucket `1` between surrounding unflagged `!` coords `0x7601` and
`0x7a03`, bridges context slot `0x00000100`, and renders digest
`89629435e063529ce7150d603ed9be37a74658317db3e97a4ae01b1c8d64f9d9`.
`ESC &p4X!\x05\x80!` covers the nonzero-filter route through `0xd04a`:
byte `0x05` maps to glyph `0x04`, byte `0x80` maps to glyph `0x7f`,
and both queue visible compact text entries. `ESC &p3X!\x98!` extends the
nonzero-filter high-control path to a taller bucket-crossing glyph: byte
`0x98` maps to glyph `0x97`, glyph entry `0x01781e`, rows `29`, width `17`,
queues bucket `-1` coord `0xfd01`, and renders row digest
`bd7ad3016d15c1dc2ef12adaeb1091a58f26473c0ecfc7ac13bfaf268c383e90`.
The top-of-range sibling `ESC &p3X!\x9f!` stays on that printable route too:
byte `0x9f` maps to glyph `0x9e`, glyph entry `0x016d1e`, rows `30`, width
`15`, queues bucket `-1` coord `0xee01`, and renders row digest
`ec0f944207561c1b9c9139749c3e37d122aebf53e2a50849dd8703416545c719`.
`SO ESC &p3X!\x80!` composes the same transparent high-control route with the
secondary text context: SO handler `0xc6b8` selects slot `1`, `0x12452`
restores record `80 58 00 03 00 00`, the high-control byte reads source
context `0xc00ae122`, maps to glyph `0x5f`, enters segmented selector
`0x2001` page-record storage with `157` segment objects, bridges slots
`(0x440946b4, 0xc00ae122)`, and selected bucket `0` renders digest
`57bb3fd895be358ff325e26ae58a3b0dc526c5b08b382eb90e7273e6227fbfbb`.
The secondary render-prefix fixture renders buckets `0..448` with aggregate
digest `292eafb8b558bd36ca0caa5caa2771976c0e611456ac0b610ec8916b9d1f03f9`
before the current source model reaches bucket `456`, glyph `0x5f`, segment
`0x39`, source `0x03fe22`, needing `1280` bytes with `478` available.
Disassembly pins the command-side unresolved edge more narrowly: `0x1f354`
accepts the zero table entry for glyph `0x5f` as the secondary `LINE_PRINTER`
record header at file offset `0x02e122`, and `0x1f1f0` advances segment `0x39`
to file offset `0x03fe22` / firmware address `0x0bfe22`. The remaining gap is
what resource bytes hardware supplies for `0x0bfe22..0x0c0321`, not the
transparent parser route or compact renderer row-skip arithmetic.
Fixture `transparent secondary segment-57 continuation policies diverge after
verified bytes` proves the current-band rows at bucket `456` no longer depend
on that unknown continuation: mirror, code-pair continuation, and zero-fill all
produce digest
`f0c1127f9e6b203f9829ab43f159b89c3f7dda687a47d4c09971077eac55c96e`. The
fallback rows diverge across those policies. The fixture hashes the verified
`0x0bfe22..0x0bffff` suffix as
`e0a0fd34ce7a39f79ecd27c0ee288631554a0ff78359b72e27ea6087651bcf1f` and the
mirror/code-pair/zero-fill continuation candidates as
`e435e3b9d033e491b57282a88b0f321aa5fecae8128fa060844cc01379349563`,
`90934acf59d9e8519c9149dc5df228f8fec2bff8451427be265489be967cdd16`, and
`359f38eef400e2fa3924a3258652e74ee19cd46cb92e47bce91f1194fce25e9e`, so the
unresolved command-map edge is specifically the memory map at
`0x0c0000..0x0c0321`. `data/rom_manifest.json` shows that range is beyond the
verified `IC32,IC15` resource image, and `notes/formatter-interface-pca.md`
records address-controller/jumper ROM-region behavior as the hardware state
that can resolve it. Startup checksum evidence does not choose a continuation:
`notes/firmware-startup.md` bounds the resource-pair byte-sum self-test at
`0x080000..0x0bffff`, before the fallback-row bytes at `0x0c0000`.
`ESC &p2X\x1aA!` covers the probe path where `1a 41` contributes payload byte
`0x41`, not `0x1a`.

`generated/analysis/ic30_ic13_esc_e_reset_flow.md` tracks the software
reset boundary: `ESC E` runs text flush/page-root finalization before
rebuilding environment state, refreshes current-font/HMI state through
`0xcbd4`, resets parser/data-chain state through `0xe146`, and
clears/reinitializes raster state at `0x783170`.
`generated/analysis/ic30_ic13_page_root_finalization.md` splits out the
`0xff1e` contract: active roots publish as state `2` through
`0x780ea6`/`0x782996`, including the finalized page/control pool-record
header fields and queue/context roots, while missing or inactive roots
only clear `0x78297a`. The host-fetched reset, FF, page-size, and
orientation publication fixtures now pin the default published pool
header and `0x1edc6` bucket/context copy fields after that boundary
before the bridged rows are rendered. The reset publication edge is also
page-record backed: fixtures `mixed printable/reset page-record stream queues
through 0x1387c before reset`, `mixed printable/reset page-record finalization
publishes bridged record`, and `addressed printable reset publishes rendered
page record` start from `! ESC E`, materialize the compact bucket through
`0x1387c`/`0x1381c`, publish via `0xff1e`, clear `0x78297a`, and render the
published record through `0x1ed84`/`0x1ef6a`.

For the raster shorthand above, `ESC *b2w`/`2W` means the combined
stream `ESC *b2w2W`: lowercase `w` records the delayed transfer and
leaves parser mode in the `*b` family, while uppercase `W` triggers the
`0x12218` restore and the single following payload.

## Next RE Targets

The next work should follow the dataflow checkpoints in
[semantic-state-model.md](semantic-state-model.md) and should start at
unresolved byte-stream-to-pixel edges, not already-composed handlers.

- Treat the dense raster handoff as documented for ROM semantics. The
  checkpoint `Raster Transfer Gate And Encoded Rows` documents parser scratch,
  field groups, writers, consumers, output rows, fixtures, and disassembly for
  `0x11f82 -> 0x121cc -> 0x12218 -> 0x105d0 -> 0x10084 -> 0x13070 ->
  0x13250 -> 0x1f88e`. Existing fixtures cover parser dispatch, delayed record
  restore, capped/drained rows, lower-resolution modes, consecutive rows,
  same-family lowercase `*b` chaining, bridge fields, and final rows. Continue
  raster work only for byte streams that change the ROM-visible gate result,
  encoded-row object fields, allocator chain, bridge bucket roots, or
  `0x1f88e` mode-specific row construction.
- Treat the downloaded-font install-to-page byte-24 handoff as documented for
  the covered rule/raster stream.
  `Downloaded Glyph
  Rule/Raster Composition` in [semantic-state-model.md](semantic-state-model.md)
  documents the current exact split: the `ESC )s18W` install fixture emits the
  resource image, and fixture `downloaded glyph byte-24 state handoff feeds
  following page handler` consumes `font_command_final_header` at byte `24`.
  It pins glyph `0x29`, table entry `0x00ee`, pointer bytes `00 00 07 80`,
  record delta `0x0780`, bitmap offset `0x078c`, the 18 copied bitmap bytes,
  next handler `0x10e68`, page object bytes, raster payload offset `28`, and
  the composed-row digest before page handlers `0x10e68`, `0x10e22`,
  `0x10898`, `0xd04a`, `0x10808`, `0x1075a`, and delayed `0x105d0` render
  through `0x1ef6a`. Remaining ROM-semantic work should focus on byte streams
  that change the `0x16c14` / `0x16498` return state, the byte-24 header,
  following parser dispatch at `0x11774`, page-object bytes, or rendered rows,
  rather than rediscovering byte-source identity, modeled resource bytes,
  rule/raster producers, or render-entry rows already documented here.
- Broaden visible-output compatibility only when a new selected-font state
  boundary is exposed. `Built-In Font Selection To Visible Text` already
  covers primary and secondary built-in selection, primary/secondary
  symbol-miss fallback, non-Roman `0N` / `10U` / `11U` streams, final-`X`
  primary built-in, secondary built-in, and inline/downloaded success,
  final-`X` non-selected exits, final-`@` default-table streams, `0x13eb8`
  transient/cache-hit no-dispatch exits, and the `0xc580` common-refresh
  branch cluster. New work should add command combinations that exercise
  different `0x13eb8`, `0x156de`, `0x17708`, or `0xc580` state transitions
  before visible output, not repeat the already documented six non-Roman
  streams or the current final-`X` / final-`@` cases.
- Treat `ESC &k#S/s` pitch-mode as already covered at the producer boundary
  unless it is paired with a stream that changes the selected context or
  rendered rows. [font-context-metrics.md](font-context-metrics.md) documents
  `0xc390` selectors `0`, `2`, and `4` rewriting synthetic pitch records and
  rejoining `0xc89c` / `0xc580`; [semantic-state-model.md](semantic-state-model.md)
  records the same writer path in `Built-In Font Selection To Visible Text`.
- Treat font metric producer behavior as regression expansion unless it
  exposes a new page-visible selected-font boundary. The metric formulas and
  producer/consumer cross-products are documented in
  [font-context-metrics.md](font-context-metrics.md) and composed under
  `Selected-Font Metric Producer/Consumer Contract` in
  [semantic-state-model.md](semantic-state-model.md). The exact remaining risk
  is selected-font state combinations that change a concrete consumed field:
  selected context records `0x782ee6/0x782ef6`, active maps
  `0x782f32/0x783032`, source-object fields
  `0x782d7e+0x00/+0x04/+0x0b/+0x10/+0x16`, unflagged metric bytes
  `+0x2b/+0x2c/+0x2d`, flagged metric words `+0x16/+0x18/+0x1a`, pending
  span fields `0x783184..0x78318a`, page-object fields, bridge context slots,
  or rendered rows. Manual-facing names for consumed-but-not-staged validation
  fields remain external; the rounding, range, offset, inline/resource,
  `d4ac`, and `d8fc` behavior is already pinned.
- Treat the built-in font sample printout as ROM-local documented through the
  covered source/page-record forms. [resource-rom.md](resource-rom.md)
  documents the candidate sequence and
  [semantic-state-model.md](semantic-state-model.md) composes the sample-page
  source placement, sample-run reuse, and `0x1ed84` / `0x1ef6a` rendered
  segments. Fixtures `font sample heading continuation emits fresh source
  heading page record` and
  `font sample cartridge heading continuations emit source-specific page
  records` cover internal and cartridge heading-preflight objects. Fixture
  `font sample row continuation emits fresh source heading page record`
  covers the row-overrun `I01` forced-continuation object; fixture
  `font sample class-one row continuation emits fresh source heading page
  record` covers the class-one `I16` sibling from `0x40099d18` to
  `0x4409a0e4` with bucket digest
  `842dd781a1093819f918e128999786f94f16cc3562ca25c3a82503ced74f3f3c`;
  fixture
  `font sample alternate-row continuation emits preadvanced row page record`
  covers the alternate-row caller sequence after `0x1d868` returns D7 `1`:
  `0x1c4a4 -> 0x1d868 -> 0x1c4b6 -> 0x1c9f6 -> 0x1c4ca -> 0x1ca2c ->
  0x1c4d4 -> 0xf06e -> 0x1c4e8 -> 0x1d050 -> 0x1c4f2 -> 0x1cabe`, emits
  `I01COURIER101210U` after pre-row y advance
  `0x00520000 -> 0x00900000`, and pins bucket digest
  `c6f0cbe07a7681d3ecfd3447b8296e97cbf8042d6d962d825f6018d980d5396b`.
  Additional row-overrun byte streams are regression cross-products unless
  they expose a page-record object form outside the covered heading-preflight,
  class-zero `I01`, class-one `I16`, and alternate-row `I01` forms. The record
  fields consumed by `0x1519a` and `0x1428c` are documented as decoded-height
  inputs and same-class chooser tie-breakers; only their external/manual names
  remain unknown.
- Keep resource-window work focused on the exact physical decode gap.
  [resource-rom.md](resource-rom.md) now composes the
  `0x1a2e4 -> 0x1a616 -> 0x1a9be` candidate windows and selection state. The
  remaining resource-ROM boundary is the firmware address window
  `0x0c0000..0x0c0321` used by the transparent secondary segment-57 fallback
  rows. Startup checksum evidence covers only `0x080000..0x0bffff`, so this
  boundary still needs board/emulator memory-map evidence for the actual
  decode source. The ROM-local choices remain the documented mirror,
  code-pair continuation, and zero-fill fallback-row digests.
- Continue active-render scheduler work only at the external device boundary.
  The software-visible scheduler, wait-object, trap, render-work, per-band
  merge, and page-record bridge states are already modeled. Remaining work is
  bounded to ROM-visible effects of the active-render/device handoff:
  formatter-signal correlation only matters when it changes ready/busy
  branches, wait-object wake order, selected page/control record, scheduler
  band words, or render inputs already recorded in the reproduction map.
