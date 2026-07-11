# PCL4 / PCL Level IV Notes

Sources:
`33440-90905_HP_LaserJet_series_II_Technical_Reference_Manual_Aug1989.pdf`,
especially ch. 1-3, ch. 13, appendix A.

## Owner Summary

This note owns the manual PCL Level IV command vocabulary as an index into the
ROM dataflow model. It does not prove command behavior by manual syntax alone:
each command family below is tied to parser records, handler addresses, RAM
fields, page-object producers, render consumers, and owner notes that carry the
evidence.

Primary route from syntax to ROM behavior:

- Host bytes enter through the
  [Host Byte Source Outcome
  Matrix](host-byte-fetch.md#host-byte-source-outcome-matrix), parser wrapper
  `0xda9a`, tokenizer helpers `0xdaf0` / `0xdb74`, and main dispatch loop
  `0x11774`.
- Command combining is represented by parser modes, lowercase finals, and
  six-byte records rooted at the parser record cursor `0x78299e`; counted
  payloads use delayed snapshot/restore `0x121cc -> 0x12218`.
- Manual control-code, two-character escape, and parameterized escape forms
  map into the command-family owners listed in the ROM Semantic Index:
  publication commands, direct controls, VFC, transparent/display readers,
  raster, rectangle/rules, font selection/downloads, macro/data-chain replay,
  and status/model side channels.
- Pixel-producing families converge through page root `0x78297a`, publication
  `0xff1e`, bridge `0x1ed84 -> 0x1edc6`, active scheduler state, and render
  entry `0x1ef6a`.

Field groups:

- Canonical parser state:
  mode byte `0x782999`, alternate/data selector `0x782c18`, six-byte command
  records, delayed-payload fields `0x782a1a..0x782a25`, and payload budget
  `0x783140`.
- Canonical command/page state:
  cursor, HMI/VMI, page geometry, copy count, paper source, font contexts,
  symbol maps, raster state, rectangle state, macro state, and current page
  root fields named in the ROM Semantic Index.
- Derived/cache state:
  compact bucket keys, pending-span watermarks, selected-font/map caches,
  raster capacity, rule selector state, render-band caches, and row-helper
  products.
- Parser scratch:
  numeric accumulation, lowercase chaining records, delayed payload snapshots,
  alternate/data append bytes, no-output parser reset rows, service/no-byte
  turns, and no-match callback handoffs.
- Firmware bookkeeping:
  parser callback pointer, page allocator cursors, macro heap/data-chain
  frames, no-byte latch `0x780e3b`, macro/page state byte `0x782a92`,
  publication flag, host-output FIFO, and scheduler work records.
- Hardware/external state:
  live host buses, retained storage, optional resource windows, and
  formatter/DC timing only after the ROM reduces them to bytes, fields,
  page objects, selected resources, or render inputs.
- Unknown:
  no parser-table mapping gap remains for the quick-reference command
  clusters. Residuals are exact resource, invalid-target/source,
  unresolved-caller, hardware/MMIO, optional external-data, manual/physical,
  or broader-variant boundaries documented in the owner notes.

Output effect:

- Some PCL commands produce visible output only by changing later consumers:
  cursor, font, symbol, VMI/HMI, macro, raster-control, and layout commands
  are stateful even when they do not immediately queue a page object.
- Commands that publish or queue page objects are visible only after the page
  storage, publication, scheduler, and render owners consume their state.
- Unsupported or no-output commands are still ROM behavior: they consume the
  documented syntax and take explicit no-output parser, handler, or status
  paths.
- Raw-byte traces can also stop at parser-control outcomes that are not manual
  commands: service/return `0x117d2..0x11818`, no-match normal fallback
  `0x118b2..0x11900`, alternate/data no-match append `0x11b82..0x11b8a`, or
  nonzero-mode callback `0x11b32..0x11b7e`. These are parser routing outcomes
  and only become page behavior when they explicitly reach `0xd04a`, a
  callback owner, or later replay of bytes appended through `0xe002`.

## PCL Level

LaserJet Series II is a PCL Level IV device. PCL levels are
upward-compatible supersets:

- Level I: print and space.
- Level II: EDP/transaction.
- Level III: office word processing.
- Level IV: page formatting.

PCL commands set printer features and normally remain in effect until
changed by another command or reset.

Unsupported PCL commands should be ignored.

In the ROM model, "ignored" is not a single behavior:

- Normal C0 bytes `0x00`, `0x07`, and `0x0b` are explicit zero-handler parser
  rows. They still enter `0xa904 -> 0xda9a -> 0x11774`, run the terminal
  parser reset path through `0x119a6..0x119f4`, and preserve the delayed
  payload restore boundary at `0x12218`; they do not call a page-output
  handler.
- `ESC ? 0x11` is consumed by the `0xda9a` ESC-aware byte wrapper before the
  parser table sees a command. It restarts byte fetching rather than creating
  a page object or command record.
- `ESC &lT/t` is an unimplemented `&l` table slot. Uppercase `T` has no
  terminal handler, while lowercase `t` uses the lowercase chaining helper
  path; neither form writes page environment, page objects, publication state,
  or render inputs by itself.
- In alternate/data mode, many zero-handler rows are byte-preserving. The
  alternate table rooted at `0x116f6` appends matched C0 bytes through
  `0xe002` instead of running their normal control-code handlers, so they can
  matter later if macro/data-chain replay feeds them back to the parser.
- Parser-control outcomes can also consume a byte-stream turn without being
  manual commands. Service path `0x117d2..0x11818` handles no-byte latch
  `0x780e3b` and parser return state `0x782a92 == 0x63`; normal no-match path
  `0x118b2..0x11900` either calls `0xd04a` or ignores the byte according to
  selected context byte `0x782ee6 + 16 * 0x782f06 + 5`; alternate/data
  no-match path `0x11b82..0x11b8a` appends through `0xe002`; and nonzero-mode
  no-match path `0x11b32..0x11b7e` delegates to callback `0x78299a`.

Evidence: [pcl-parser-core.md](pcl-parser-core.md#parser-core-outcome-matrix),
[pcl-command-map.md](pcl-command-map.md), the ignored/no-output walkthrough in
[end-to-end-reproduction-map.md](end-to-end-reproduction-map.md), and table
extracts in `generated/analysis/ic30_ic13_parser_dispatch_tables.md` and
`generated/analysis/ic30_ic13_pcl_command_map.md`.

## ROM-Backed Level IV Boundary

The firmware command tables and semantic notes support the manual claim that
this is a PCL Level IV/page-formatting device rather than only a PCL Level III
word-processing target.

ROM-backed Level IV command families include:

- page environment and publication: `ESC E`, FF, page size `ESC &l#A`,
  orientation `ESC &l#O`, paper source `ESC &l#H`, copies `ESC &l#X`, and
  page-root publication through `0xff1e`;
- cursor and text layout: HMI/VMI, margins, line termination, cursor
  positioning, cursor stack, VFC table definition `ESC &l#W`, and VFC channel
  jumps `ESC &l#V`;
- raster graphics: `ESC *t#R`, `ESC *r#A/B`, delayed raster transfer
  `ESC *b#W`, encoded page objects, and render target `0x1f88e`;
- rectangle/rule graphics: rectangle dimensions, fill selector
  `ESC *c#P`, rule-list storage, and solid/pattern render helpers;
- font selection and glyph sources: primary/secondary font selectors,
  symbol-set handling, built-in resource records, downloaded-font descriptors,
  downloaded-character payloads, and compact glyph renderers;
- macros and alternate/data parsing: macro id/control commands, data-chain
  replay, overlay publication, and display-functions append behavior.

Concrete evidence is in [pcl-command-map.md](pcl-command-map.md),
[pcl-parser-core.md](pcl-parser-core.md#parser-core-outcome-matrix),
[semantic-state-model.md](semantic-state-model.md), and the command-family
notes cited from those files.

## Level IV Command-Family Outcome Matrix

This matrix is the top-level route from manual PCL categories to the ROM
owners that document actual behavior. It is intentionally not a syntax-only
quick reference: each row identifies the parser/handler boundary, the state
owner, and whether visible pixels can result.

- Reset, FF, page size, orientation, paper source, copies:
  handlers `0xcc52`, `0xf0f0`, `0xfc74`, `0x10220`, `0xef62`, and
  `0xeef0`; owner [Publication Outcome
  Matrix](publication-commands.md#publication-outcome-matrix).
  These handlers either publish the old current root through snapshot boundary
  `0xff1e` before mutating page environment, or stage page-control fields
  such as `0x782da2`, `0x782da3`, `0x782da4`, and `0x782da6` for a later
  publication. Rendered rows come only after the published record crosses
  `0x1ed84`, `0x1edc6`, and `0x1ef6a`; publication itself is not a pixel
  renderer.
- Direct controls and text placement:
  C0 rows `0xf02c`, `0xf08c`, `0xf0f0`, `0xf1cc`, and `0xf2a8`; SO/SI
  `0xc6b8` / `0xc68a`; and cursor/margin helpers are owned by
  [Direct-Control Outcome
  Matrix](direct-control-codes.md#direct-control-outcome-matrix).
  These commands change cursor, selected text slot, line-termination, span,
  HMI/VMI, wrap, or margin state unless they explicitly publish through FF.
  Visible output occurs when a later consumer, such as printable text,
  underline span flush, raster origin, rectangle clipping, VFC, or
  publication, reads those fields and queues or publishes page objects. The
  span-producing branch is concrete: underline/text-attribute handler
  `0x12622` writes selector byte `0x783185`, printable text updates pending
  bounds `0x783184..0x78318a`, and flush producers such as CR `0xf02c`, left
  margin `0xeb58`, vertical cursor `0xf560`, or `ESC &d@` run
  `0xf34a -> 0x12714 -> 0x126e2`. Portrait spans become class-`0x40`
  segment-list objects under page-root `+0x1c` through `0x13520` / `0x135f0`
  and render through `0x1efc2 -> 0x1f812 -> 0x1f862`; landscape spans become
  fixed-list objects under root `+0x28` through `0x136d2` and render through
  `0x1f756 -> 0x1f7b0`.
- Printable text and font/symbol selection:
  printable fallback `0xd04a`; owners
  [Font Request Outcome Matrix](font-context-metrics.md#font-request-outcome-matrix),
  [Resource ROM Outcome Matrix](resource-rom.md#resource-rom-outcome-matrix),
  [symbol-set-selection.md](symbol-set-selection.md), and
  [symbol-map-patching.md](symbol-map-patching.md). Selection commands update
  font contexts, candidate/resource selection, symbol maps, HMI, and map patch
  state. Built-in resource candidates come from startup scan
  `0x1a2e4 -> 0x1a616 -> 0x1a9be`, while parser-visible font commands consume
  those candidates through selectors such as `0x1569c`, `0x156de`,
  `0x14398`, `0x144d2`, and `0x14c64`. Printable bytes then consume the
  selected map/context to create compact text objects under page-root bucket
  `+0x1c`; render path `0x1ef6a -> 0x1efc2 -> 0x1effe -> 0x1f354` resolves
  built-in glyph rows from the selected IC32/IC15 resource bytes.
- Transparent and display readers:
  delayed transparent handler `0x11f5a -> 0x12452` and display readers
  `0x12536` / `0x12120`; owners
  [Transparent Payload Outcome
  Matrix](transparent-print-data.md#transparent-payload-outcome-matrix) and
  [display-functions.md](display-functions.md). These are direct byte readers:
  normal transparent payload restores through
  `0x11f5a -> 0x121cc -> 0x12218 -> 0x12452`, while normal `ESC Y` reaches
  loop reader `0x12536`. In both normal cases, payload values are not parsed
  as commands; the reader routes each normalized byte to printable `0xd04a` or
  fixed-space/control `0xd0f0`. Printable results then use the ordinary text
  route `0xd04a -> 0x1393a -> 0x12f2e -> 0x1387c`, publish through `0xff1e`,
  bridge bucket root `+0x1c` to render root `+0x18`, and render through
  `0x1efc2 -> 0x1effe`. In alternate/data mode, transparent restore diverts
  through `0x12358 -> 0xdace -> 0xe002`, and alternate display reader
  `0x12120` appends literal `ESC Y` plus normalized loop bytes through
  `0xe002`; those stored bytes affect pixels only if later macro/data replay
  returns them through `0xa904`.
- Raster graphics:
  `ESC *t#R`, `ESC *r#A/B`, delayed `ESC *b#W` through `0x105d0`, and object
  producer `0x13070`; owner [Raster Transfer Decision
  Checkpoint](raster-graphics.md#raster-transfer-decision-checkpoint). Raster
  commands set resolution/mode state and queue encoded raster row objects under
  page-root bucket `+0x1c` through `0x13070 -> 0x13250 -> 0x138de`. Publication
  and bridge preserve that bucket chain as render-record root `+0x18`; bucket
  walker `0x1efc2` dispatches class-`0x80` raster objects to `0x1f88e`, whose
  mode branches use `0x1f8da`, `0x1f8e6`, `0x1f920`, or `0x1f9c6`.
- Rectangle/rule graphics:
  rectangle dimension and fill handlers `0x10e68`, `0x10e22`, `0x10a40`,
  `0x10ae0`, `0x10dce`, and `0x10898`; object insertion
  `0x13386` / `0x133aa`; owner
  [Rectangle Outcome Matrix](rectangle-graphics.md#rectangle-outcome-matrix).
  Width/height and selector state become ordered rule-list objects under
  page-root `+0x24`. Bridge `0x1edc6` copies that list to render-record
  `+0x1c` and initializes continuation word `+0x0c`; render entry consumes
  rule nodes through `0x1f446`, solid selector helper `0x1f596`, or patterned
  helper `0x1f4e0`.
- VFC and vertical layout: VMI/LPI, page length, VFC table load, and channel jumps;
  owners [VFC Outcome Matrix](vertical-forms-control.md#vfc-outcome-matrix) and the
  shared geometry refresh consumer in
  [publication-commands.md](publication-commands.md#shared-geometry-refresh-consumer-checkpoint).
  `ESC &l#W` schedules delayed payload handler `0x12cfe` through `0x11f6e -> 0x121cc ->
  0x12218`; normal restore consumes bytes through `0xdace`, writes VFC table
  `0x782dde..0x782edd`, and updates bottom caches `0x782dc2/0x782dd2`, while
  alternate/data restore diverts through `0x12358 -> 0xdace -> 0xe002` and leaves the
  table unchanged. `ESC &l#V` handler `0x1280a` consumes selector, VMI `0x783160`, top
  offset `0x782dce`, cursor `0x782c8a/0x782c8e`, line caches, and table masks; it either
  rewrites cursor state for a following printable object or publishes the old page
  through `0xf124 -> 0xff1e` before the next printable creates a fresh root. Perforation
  skip `0xee64` writes `0x783191`; later overflow helper `0xf36c` consumes it with VFC
  limit `0x782dc2` to decide whether to publish.
- Macros and alternate/data replay:
  macro controls under `0xdd08`, data-chain builders `0xe418` / `0xe4f4`,
  and replay through `0xa904`; owner
  [Macro Replay Outcome Matrix](macro-data-chain.md#macro-replay-outcome-matrix).
  Definition selector `0` changes parser source behavior: ordinary payload
  bytes append through `0xe002` into macro chunks rooted at record pool
  `0x782a98`, so handlers such as printable `0xd04a` or CR `0xf02c` do not
  run while bytes are being defined. Execute/call selectors `2/3` build
  data-chain frames through `0xe418`, set active frame pointer `0x782d76`,
  and make `0xa904` return stored bytes to parser loop `0x11774` as ordinary
  input. Overlay selectors `4/5` set publication state `0x782a92/0x782a94`;
  `0xff1e` can build a non-replay frame through `0xe4f4` before finalizing
  the page. Macro replay has no special page-object or pixel writer: replayed
  bytes create text, spans, raster rows, rules, VFC moves, or publication
  effects only by re-entering their normal command-family routes.
- Downloaded fonts and characters:
  downloaded-font control writers `0x15a56`, `0x15a18`, and `0x16df6`,
  descriptor/character payload readers `0x15d0a` and `0x16c14`, plus active
  object dispatch around `0x14ba4`; owner
  [Downloaded-Font Outcome
  Matrix](downloaded-fonts.md#downloaded-font-outcome-matrix).
  `ESC *c#D/#E/#F` sets current id `0x782f2e`, current character
  `0x782f30`, and current-record control state. `ESC (s#W` / `ESC )s#W`
  schedule delayed descriptor or resource handlers through `0x11f96 ->
  0x121cc -> 0x12218`; zero-count payloads call `0x15d0a`, while nonzero
  character/resource payloads restore into `0x16c14`. Successful downloaded
  characters pass through `0x15dc6 -> 0x16498 -> 0x15dcc -> 0x12328`, where
  `0x16498` writes the canonical glyph record, glyph-table entry, and bitmap
  payload. No pixels appear at install time. A later printable byte must reach
  `0xd04a`, select the installed glyph through active map/context state, and
  queue compact objects through `0xd824 -> 0x12f2e -> 0x1387c`; publication
  and bridge then expose bucket root `+0x1c` as render root `+0x18`, where
  `0x1efc2 -> 0x1effe` selects short, wide, segmented, or segmented-wide
  helpers `0x1f034`, `0x1f0d2`, `0x1f1f0`, or `0x1f264`.
- Host/status side channels:
  model/status wrapper `0x12034`, FIFO helpers `0xb0c0` / `0xb022`, worker
  `0xae2c`, and terminal report sinks `0x1284` / `0x128c`; owner [Host/Status Outcome
  Matrix](errors-and-status.md#hoststatus-outcome-matrix). These paths produce
  host-visible protocol bytes, panel/status state, or panel/MMIO report state,
  not page pixels. Model query commands `ESC *r#K` and `ESC *s#^` dispatch through
  `0x12034 -> 0x11efe -> 0x122be..0x12326`; accepted query byte `0x11` with
  active record word `+2 = 1` or `-1` emits literal `33440A\r\n` from
  `0x12280..0x12288` through blocking FIFO helper `0xb090`. FIFO storage
  `0x783e92..0x783ed1`, count/pointers
  `0x783ed2/0x783ed4/0x783ed8`, service/status latches
  `0x783e61/0x783e60`, and pending status count `0x780e22` are later consumed
  by worker `0xae2c` and status builder `0xaece`. Terminal reports consume a
  two-byte code at `0x1284` / `0x128c`, select a status string through
  `0x158c`, display it through `0x8c7a`, cache first message bytes in
  `0x783ef0..0x783ef1`, and stop at the hardware-facing loop
  `0x12d4..0x13b0`. No page root, page object, publication record, render
  record, or pixel helper is written by these paths. Pixel reproduction changes
  only if a bidirectional host sends different future bytes after observing the
  backchannel, if FIFO fullness stalls a producer, or if an implementation
  models panel/MMIO status effects.

Common render convergence for pixel-producing rows is:
page-root storage under `0x78297a`, publication `0xff1e`, active/render
record bridge `0x1ed84 -> 0x1edc6`, and bucket/list walking through
`0x1ef6a`. Bridge `0x1edc6` copies source bucket root `+0x1c` to render root
`+0x18`, rule/list root `+0x24` to render root `+0x1c`, fixed-list root
`+0x28` to render root `+0x20`, and context slots `+0x2c..+0x68` to render
slots `+0x24..+0x60`. Render entry then walks bucket objects through
`0x1efc2`, rule objects through `0x1f446`, and fixed-list objects through
`0x1f756`. Rows that say "no immediate page object" still matter to exact
reproduction because they update fields consumed by a later row in this
matrix.

The current ROM notes do not treat LaserJet III / PCL5-only features as part
of the LaserJet II reproduction target. Scalable typefaces, RET, HP-GL/2,
PCL5 font selection behavior, and LaserJet III-specific page-protection
behavior should remain outside the model unless a ROM handler in these dumps
is tied to a LaserJet II-visible byte-stream effect.

## Command Types

PCL has three command types:

- Control codes: single ASCII control characters such as CR, LF, FF.
- Two-character escape sequences: `ESC X`.
- Parameterized escape sequences.

`ESC` is ASCII 27 / hex `1B`. The manuals print it as `Ec` or similar
OCR variants.

## Two-Character Escape Sequences

Form:

```text
ESC X
```

Examples:

- `ESC E`: printer reset.
- `ESC 9`: clear left and right margins.

`X` is an ASCII character in decimal range 48-126.

## Parameterized Escape Sequences

General form:

```text
ESC X Y # z ... # Z [binary data]
```

Where:

- `X`: parameterized character, ASCII 33-47 (`!` through `/`).
- `Y`: group character, ASCII 96-126.
- `#`: ASCII numeric value, optional sign and decimal fraction.
- `z`: parameter character, ASCII 96-126. Used while combining commands.
- `Z`: termination character, ASCII 64-94. Ends the command.
- `[binary data]`: immediate bytes after terminator, length usually
  given by value field.

If a required value field is omitted, value 0 is assumed.

## Combining Commands

Commands with the same parameterized and group characters can be
combined. In a combined sequence, previous terminators become lowercase
parameter characters until the final uppercase terminator.

Example concept:

```text
ESC &l1O
ESC &l2A
```

Can combine to:

```text
ESC &l1o2A
```

Parser implication: the same final letter in different case can mean
"parameter continues" versus "command terminates".

ROM implementation details:

- The parser loop at `0x11774` uses six-byte table records:
  byte-to-match, next parser mode, and handler longword.
- Lowercase finals keep the parser in the same command family by selecting a
  nonzero next mode; uppercase finals usually return the parser to mode zero
  after the terminal handler runs.
- The current command-record cursor `0x78299e` is rewound by six when a
  helper needs the just-parsed record again. This matters for chained
  families such as raster `ESC *b2w2W`, macro/font tokenizer helpers, and
  delayed payload readers.
- Counted payload commands are not just syntax tokens. Helpers store the
  pending handler and a copy of the six-byte record at
  `0x782a1a..0x782a25`; `0x12218` later restores that record before calling
  the payload handler.

Evidence:
[pcl-parser-core.md](pcl-parser-core.md) documents the parser table,
stateful helper, and delayed-payload contracts. Command-family effects are
composed in [raster-graphics.md](raster-graphics.md),
[downloaded-fonts.md](downloaded-fonts.md),
[macro-data-chain.md](macro-data-chain.md), and
[vertical-forms-control.md](vertical-forms-control.md).

## Coordinate System

External PCL coordinate units:

- Dots.
- Decipoints.
- Columns for X.
- Rows for Y.

Constants:

- Printer dot: 1/300 inch.
- Decipoint: 1/720 inch.
- Internal unit: 1/3600 inch.

The printer tracks positions internally in 1/3600 inch units and
truncates to physical dot positions when printing.

Columns are based on HMI. Rows are based on VMI or lines per inch.

## ROM Coordinate Conversion Contract

The firmware does not carry manual PCL units directly into page objects. Parser
records hold the parsed integer and fractional command values; terminal
handlers convert those values into ROM cursor and layout fields before any
printable, raster, rectangle, or publication path consumes them.

Conversion routes:

- Whole-dot positioning:
  `ESC *p#X` and `ESC *p#Y` enter `0xf48c` and `0xf692`. Each rewinds
  parser record cursor `0x78299e`, reads parsed word `+2`, shifts it into the
  high word of a cursor longword, and commits it through `0xf4ca` for X or
  `0xf6e2` for Y. Relative forms are selected by command-record byte bit `0`.
- Decipoint positioning:
  `ESC &a#H` / `ESC &a#V` and cursor row/column forms enter the direct-control
  handlers documented in [direct-control-codes.md](direct-control-codes.md).
  They scale parsed integer/fraction words through helpers such as `0x332ee`,
  `0x3324a`, and `0x104d8` before writing cursor fields.
- Column and row positioning:
  `ESC &a#C` consumes HMI `0x78315c`; `ESC &a#R` consumes VMI `0x783160` and
  top offset `0x782dce`. The resulting coordinates are committed through the
  same X/Y commit helpers used by dot and decipoint forms.
- Layout conversion:
  HMI handler `0xca8c`, VMI handler `0xcb00`, lines-per-inch handler
  `0xc992`, page-length handler `0xf9e8`, top-margin handler `0xece2`, and
  text-length handler `0xea9e` write the canonical motion and page-bound
  fields that later cursor conversions read.

State classification:

- Canonical placement state:
  horizontal cursor `0x782c8a`, vertical cursor `0x782c8e`, left/right
  margins `0x782dd6` / `0x782dda`, top offset `0x782dce`, page extent
  `0x782dba`, text bottom `0x782dd2`, and bottom/perforation limit
  `0x782dc2`.
- Canonical motion state:
  HMI `0x78315c`, VMI `0x783160`, line-termination mode `0x78318f`,
  wrap byte `0x783190`, and perforation-skip byte `0x783191`.
- Parser scratch:
  six-byte command records at `0x78299e` and parsed integer/fraction words.
  The records are consumed by terminal handlers and do not become page objects.
- Derived/cache state:
  packed cursor values, compact object coordinates derived later by
  `0xd04a -> 0x1393a -> 0x12f2e`, and render-band caches after publication.
- Firmware bookkeeping:
  pending cursor/text byte `0x782a6d`, previous-width latches
  `0x782a58..0x782a5c`, pending span byte `0x783184`, and modified-layout
  byte `0x782ee1`.

Output effect:

Coordinate commands are state producers, not pixel writers. Their visible
effect appears when a later printable byte, raster row, rectangle/rule, VFC
jump, span flush, FF, or reset consumes the updated placement fields and
creates or publishes page objects. Printable text reaches
`0xd04a -> 0x1393a -> 0x12f2e`; raster and rectangle paths read the same
cursor/layout fields before writing page-root objects. The render layer then
derives pixels from those object fields after publication, active-copy,
bridge, and render entry:
`0xff1e -> 0x1ed84 -> 0x1edc6 -> 0x1ef6a`.

Evidence:

- `generated/disasm/ic30_ic13_coordinate_math_0104d8.lst` anchors the shared
  coordinate helpers, including `0x104d8`, `0x104fe`, `0x10518`, and
  `0x10550`.
- `generated/disasm/ic30_ic13_dot_position_handlers_00f48c.lst` anchors dot,
  row, column, and decipoint cursor commits through `0xf4ca` and `0xf6e2`.
- `generated/disasm/ic30_ic13_hmi_vmi_handlers_00ca8c.lst` and
  `generated/disasm/ic30_ic13_page_length_handler_00f9e8.lst` anchor HMI/VMI,
  LPI, top-margin, text-length, and page-length writers.
- Checked-in semantic detail and fixtures are in
  [direct-control-codes.md](direct-control-codes.md) and
  [publication-commands.md](publication-commands.md#owner-summary).

## Logical Page and Printable Area

The logical page is the addressable area in which the PCL cursor can be
positioned. The cursor cannot move outside logical page bounds. The
printable area is the part of the physical page where the engine can
place dots.

`(0,0)` is at the left edge of the logical page at the current top
margin position. Changing top margin changes the physical position of
`(0,0)`.

All dimensions below are 300 dpi dots from Technical Reference figures
2-2 and 2-3. Columns `A`/`B` are physical dimensions, `C`/`D` are
logical dimensions, and `E`/`F`/`G`/`H` are left/right/top/bottom
unprintable margins.

Portrait:

| Paper | Phys W | Phys L | Log W | Log L | Left | Right | Top | Bottom |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Letter | 2550 | 3300 | 2400 | 3300 | 50 | 100 | 60 | 60 |
| Legal | 2550 | 4200 | 2400 | 4200 | 50 | 100 | 60 | 60 |
| Executive | 2175 | 3150 | 2025 | 3150 | 50 | 100 | 60 | 60 |
| A4 | 2480 | 3507 | 2338 | 3507 | 50 | 92 | 60 | 58 |
| COM-10 | 1237 | 2850 | 1087 | 2850 | 50 | 100 | 60 | 60 |
| Monarch | 1162 | 2250 | 1012 | 2250 | 50 | 100 | 60 | 60 |
| C5 | 1913 | 2704 | 1771 | 2704 | 50 | 92 | 60 | 58 |
| DL | 1299 | 2598 | 1157 | 2598 | 50 | 92 | 60 | 58 |

Landscape:

| Paper | Phys L | Phys W | Log W | Log L | Left | Right | Top | Bottom |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Letter | 3300 | 2550 | 3180 | 2550 | 60 | 60 | 50 | 100 |
| Legal | 4200 | 2550 | 4080 | 2550 | 60 | 60 | 50 | 100 |
| Executive | 3150 | 2175 | 3030 | 2175 | 60 | 60 | 50 | 100 |
| A4 | 3507 | 2480 | 3389 | 2480 | 60 | 58 | 50 | 92 |
| COM-10 | 2850 | 1237 | 2730 | 1237 | 60 | 60 | 50 | 100 |
| Monarch | 2250 | 1162 | 2130 | 1162 | 60 | 60 | 50 | 100 |
| C5 | 2704 | 1913 | 2586 | 1913 | 60 | 58 | 50 | 92 |
| DL | 2598 | 1299 | 2480 | 1299 | 60 | 58 | 50 | 92 |

Printable length is `B - (G + H)`.

Clipping behavior:

- Text: if any part of the character cell falls outside the printable
  area, the whole character is clipped, even if the out-of-area portion
  has no set dots.
- Raster graphics and rules: if the cursor starts inside the printable
  area, only the portion extending outside the printable area is
  clipped.

## Print Environments

### Factory Default Environment

ROM-stored defaults. See
[control-panel-nvram-selftest.md](control-panel-nvram-selftest.md).

### User Default Environment

Control-panel-selected defaults, retained across power-off. LaserJet II
user defaults:

- Copies.
- Paper source.
- Font source/font number.
- Form length.

### Modified Print Environment

Current runtime state changed by PCL commands. Includes:

- Copies, paper source, page size/length, orientation.
- Margins, top margin, text length.
- HMI, VMI/line spacing, perforation skip.
- Primary and secondary font characteristics.
- Primary and secondary fonts.
- Underline mode.
- Font ID and character code.
- Raster graphics resolution and left margin.
- Area fill ID and rectangle sizes.
- Macro ID.
- Line termination.
- End-of-line wrap.

Not included:

- Current cursor position.
- Cursor position stack.

## Reset Semantics

`ESC E`:

- Restores user default environment.
- Deletes temporary fonts and macros.
- Prints any partial page.

Control-panel reset:

- Restores user defaults.
- Deletes temporary fonts/macros.
- Discards formatted but unprinted pages.

Menu reset:

- Restores factory defaults for Printing Menu.
- Deletes temporary fonts/macros.
- Discards formatted but unprinted pages.

## Memory Usage

Technical Reference ch. 13:

- Standard user memory: 395 KB.
- Rule, underline, or pattern: 15 bytes each.
- Printed character: 4.25 bytes each.
- Raster line: raster data bytes plus 10 bytes.
- All optional memory becomes user memory.

Approximate soft font formula and macro formula are in the Technical
Reference; verify from PDF before coding an exact memory-accounting
test.

## Common PCL Errors

- `20 ERROR`: memory overflow during font download, macro creation,
  raster graphics download, or page composition.
- `21 ERROR`: page too complex to print at engine pace.
- `22 ERROR`: I/O protocol problem.
- `40 ERROR`: data transfer problem, often baud mismatch or host power
  transition.

## Command Quick Reference

This is an emulator-oriented subset from appendix A. `#` is an ASCII
decimal value.

### Control Codes

| Function | Byte |
| --- | --- |
| Explicit no-output row | `NUL` / `0x00` |
| Explicit no-output row | `BEL` / `0x07` |
| Backspace | `BS` / `0x08` |
| Horizontal tab | `HT` / `0x09` |
| Line feed | `LF` / `0x0a` |
| Explicit no-output row | `VT` / `0x0b` |
| Form feed | `FF` / `0x0c` |
| Carriage return | `CR` / `0x0d` |
| Shift out, select secondary font | `SO` / `0x0e` |
| Shift in, select primary font | `SI` / `0x0f` |
| Control-Z local prefix/probe | `SUB` / `0x1a` |

### Job and Paper

| Function | Command |
| --- | --- |
| Reset | `ESC E` |
| Number of copies, 1-99 | `ESC &l#X` |
| Eject page | `ESC &l0H` |
| Feed from tray | `ESC &l1H` |
| Manual feed | `ESC &l2H` |
| Manual envelope feed | `ESC &l3H` |

### Page Size and Orientation

| Function | Command |
| --- | --- |
| Executive | `ESC &l1A` |
| Letter | `ESC &l2A` |
| Legal | `ESC &l3A` |
| A4 | `ESC &l26A` |
| Monarch envelope | `ESC &l80A` |
| COM10 envelope | `ESC &l81A` |
| DL envelope | `ESC &l90A` |
| C5 envelope | `ESC &l91A` |
| Page length in lines | `ESC &l#P` |
| Portrait | `ESC &l0O` |
| Landscape | `ESC &l1O` |

### Margins and Spacing

| Function | Command |
| --- | --- |
| Top margin in lines | `ESC &l#E` |
| Text length in lines | `ESC &l#F` |
| Left margin in columns | `ESC &a#L` |
| Right margin in columns | `ESC &a#M` |
| Clear horizontal margins | `ESC 9` |
| Perforation skip off | `ESC &l0L` |
| Perforation skip on | `ESC &l1L` |
| Define vertical forms table | `ESC &l#W` followed by data |
| Jump to VFC channel | `ESC &l#V` |
| HMI in 1/120 inch increments | `ESC &k#H` |
| Pitch mode compatibility | `ESC &k#S` |
| VMI in 1/48 inch increments | `ESC &l#C` |
| Lines per inch | `ESC &l#D` |
| End-of-line wrap on | `ESC &s0C` |
| End-of-line wrap off | `ESC &s1C` |

### Cursor Position

| Function | Command |
| --- | --- |
| Horizontal column | `ESC &a#C` |
| Horizontal dots | `ESC *p#X` |
| Horizontal decipoints | `ESC &a#H` |
| Vertical row | `ESC &a#R` |
| Vertical dots | `ESC *p#Y` |
| Vertical decipoints | `ESC &a#V` |
| Half-line feed | `ESC =` |
| Push cursor position | `ESC &f0S` |
| Pop cursor position | `ESC &f1S` |

### Line Termination

| Function | Command |
| --- | --- |
| CR=CR, LF=LF, FF=FF | `ESC &k0G` |
| CR=CR+LF | `ESC &k1G` |
| LF=CR+LF, FF=CR+FF | `ESC &k2G` |
| CR/LF/FF all advance with CR behavior shown in manual | `ESC &k3G` |

### Font Selection

| Function | Command |
| --- | --- |
| Primary symbol set | `ESC (...` family, e.g. Roman-8 `ESC (8U` |
| Primary spacing proportional | `ESC (s1P` |
| Primary spacing fixed | `ESC (s0P` |
| Primary pitch | `ESC (s#H` |
| Primary point size | `ESC (s#V` |
| Primary style upright | `ESC (s0S` |
| Primary style italic | `ESC (s1S` |
| Primary stroke medium | `ESC (s0B` |
| Primary stroke bold | `ESC (s3B` |
| Primary typeface Courier | `ESC (s3T` |
| Primary typeface Line Printer | `ESC (s0T` |
| Default primary font | `ESC (3@` |
| Default secondary font | `ESC )3@` |
| Enable fixed underline | `ESC &d0D` |
| Enable floating underline | `ESC &d3D` |
| Disable underline | `ESC &d@` |
| Assign font ID | `ESC *c#D` |
| Set downloaded character code | `ESC *c#E` |
| Delete all fonts | `ESC *c0F` |
| Delete temporary fonts | `ESC *c1F` |
| Delete last specified font ID | `ESC *c2F` |
| Make font temporary | `ESC *c4F` |
| Make font permanent | `ESC *c5F` |
| Select primary font by ID | `ESC (#X` |
| Select secondary font by ID | `ESC )#X` |
| Download primary/secondary font data | `ESC (s#W` / `ESC )s#W` followed by data |

### Raster Graphics and Fills

| Function | Command |
| --- | --- |
| Raster resolution | `ESC *t#R` |
| Start raster at left graphics margin | `ESC *r0A` |
| Start raster at current cursor | `ESC *r1A` |
| Transfer raster row bytes | `ESC *b#W` followed by data |
| End raster graphics | `ESC *rB` |
| Rectangle width dots | `ESC *c#A` |
| Rectangle width decipoints | `ESC *c#H` |
| Rectangle height dots | `ESC *c#B` |
| Rectangle height decipoints | `ESC *c#V` |
| Area-fill ID for gray/pattern fills | `ESC *c#G` |
| Fill rectangle as rule | `ESC *c0P` |
| Fill rectangle gray scale | `ESC *c2P` |
| Fill rectangle HP pattern | `ESC *c3P` |

### Macros and Transparent Data

| Function | Command |
| --- | --- |
| Macro ID | `ESC &f#Y` |
| Start macro definition | `ESC &f0X` |
| Stop macro definition | `ESC &f1X` |
| Execute macro | `ESC &f2X` |
| Call macro | `ESC &f3X` |
| Enable overlay | `ESC &f4X` |
| Disable overlay | `ESC &f5X` |
| Delete all macros | `ESC &f6X` |
| Delete temporary macros | `ESC &f7X` |
| Delete macro ID | `ESC &f8X` |
| Make macro temporary | `ESC &f9X` |
| Make macro permanent | `ESC &f10X` |
| Display functions on | `ESC Y` |
| Display-functions local terminator / blank parser row | `ESC Z` |
| Display-functions off/status edge | `ESC z` |
| Transparent print data | `ESC &p#X` followed by data |

ROM routing note: the generated flat table preserves the manual-style
`Display functions off` label for `ESC Z`, but the checked-in ROM route treats
standalone `ESC Z` as a blank parser-table terminal with no page effect. Inside
`ESC Y ... ESC Z`, normal reader `0x12536` and alternate/data reader `0x12120`
consume the `ESC Z` pair locally through their direct `0xa904` loops. Lowercase
`ESC z` is the guarded status/off edge at `0xcd86`; it can write status markers
through `0x9c2c` and creates no page object.

### Status Queries

| Function | Command |
| --- | --- |
| Model/status side-channel query | `ESC *r#K` followed by query byte |
| Model/status side-channel query sibling | `ESC *s#^` followed by query byte |

## Emulator Takeaways

- Treat the appendix command names as entry points into the ROM dataflow, not
  as the evidence source. The firmware evidence path for supported streams is
  `0xa904` byte source, `0xda9a` / `0xdaf0` / `0xdb74` tokenizer,
  `0x11774` parser table dispatch, command-family handler, page/root producer,
  `0xff1e` publication when needed, `0x1ed84` / `0x1edc6` bridge, and
  `0x1ef6a` render dispatch.
- Build the parser around command syntax and environment mutation, not
  isolated strings.
- Implement command combining correctly early; real drivers use it.
- `ESC E` must differ from panel reset in page-buffer behavior.
- Internal positioning should use 1/3600 inch units if you want
  command-compatible cursor math.
- Unsupported commands should consume the correct syntax and then no-op.

## Reproduction Contract

For a supported PCL Level IV byte stream, this language layer is reproduced
when the manual command form routes to the same ROM parser records, command
handlers, state fields, page objects, and render inputs named by the owner
notes. The required ROM-visible behavior is:

- Host bytes enter through `0xa904`, parser wrapper `0xda9a`, tokenizer
  helpers `0xdaf0` / `0xdb74`, and main parser loop `0x11774`; the manual
  command spelling is only a readable label for those parsed bytes.
- Command combining and delayed payload scheduling must preserve six-byte
  parser records, lowercase-final chaining, saved delayed records, and
  payload consumers before command-family semantics are applied.
- A command-family claim is complete only when its owner note identifies the
  parsed inputs, RAM fields written, downstream readers, output/page effect,
  evidence, and unresolved boundaries. The quick-reference table below is an
  index, not the behavioral proof.
- State-only commands are still reproduced when their later consumers see the
  same state. Cursor, font, symbol, page-layout, macro, and raster-control
  commands often change later printable/page behavior without drawing
  immediately.
- Pixel-producing streams must pass through page-object publication and render dispatch
  where applicable: current page root `0x78297a`, publication `0xff1e`, active-record
  bridge `0x1ed84` / `0x1edc6`, and render entry `0x1ef6a`. The shared
  command-family-to-render join is indexed in `Command-Family To Render Route Table` in
  [end-to-end-reproduction-map.md](end-to-end-reproduction-map.md).
- After a command family queues page output, the reader should follow the ROM object
  root, not the manual command name: root `+0x1c` bucket objects carry compact
  text/downloaded glyphs, segment spans, and encoded raster rows; root `+0x24` carries
  rectangle/rule objects; root `+0x28` carries fixed-list/landscape span objects; root
  `+0x2c..+0x68` carries font context slots. Bridge `0x1edc6` copies those to render
  roots `+0x18/+0x1c/+0x20` and context slots `+0x24..+0x60`; bucket class byte `+0x04`
  then selects compact dispatch `0x1effe`, segment-list dispatch `0x1f812`, or
  encoded-raster dispatch `0x1f88e`, while rule and fixed roots dispatch through
  `0x1f446` and `0x1f756`. The render-owner lookup is [Render Helper Boundary
  Index](page-raster-imaging.md#render-helper-boundary-index).
- Unsupported or no-output rows are reproduced by consuming exactly the ROM
  syntax and then following the documented no-output path; they should not be
  treated as unknown imaging commands.

This contract is ROM-local. Manual names, physical timing, host-interface
signals, and cartridge/resource contents matter only when the disassembly
reduces them to a parser byte, RAM field, page object, selected resource, or
render input.

## ROM Semantic Index For Quick Reference

This checkpoint ties the manual quick-reference commands above to the
checked-in firmware model. It does not replace the command-family notes; it
names the first ROM boundary a reader should follow from a host byte stream.

Field groups for this index:

- Canonical parser state:
  normalized byte `D7` from `0xa904`, mode byte `0x782999`,
  alternate/data flag `0x782c18`, parser record cursor `0x78299e`, six-byte
  command records under `0x78299e..`, delayed-payload flag and handler
  `0x782a1a` / `0x782a1c`, saved delayed record `0x782a20..0x782a25`, and
  payload budget `0x783140`.
- Canonical print/page state:
  cursor words `0x782c8a` / `0x782c8e`, HMI/VMI `0x78315c` /
  `0x783160`, page geometry and margins `0x782da2..0x782dc0`,
  `0x782dd2`, `0x782dd6`, `0x782dda`, copy count `0x782da4`, paper source
  byte `0x782da6`, wrap/perforation flags `0x783190` / `0x783191`, page root
  `0x78297a`, font contexts and maps rooted around `0x782ee6`,
  `0x782f32`, and `0x783032`, raster state `0x783170..0x783182`,
  rectangle state `0x783166..0x78316e`, and macro state
  `0x783164`, `0x782a92`, `0x782a94`, `0x782a98`, and `0x782d76`.
- Derived/cache state:
  compact bucket/key state `0x782a7a..0x782a7e`, selected context slot
  `0x78297e`, pending span watermarks `0x783184..0x78318a`, raster
  mode/scale/capacity fields, rule-pattern selector state, render-band words
  rooted at `0x783a20`, and row-helper products consumed by
  `0x1effe`, `0x1f446`, `0x1f756`, `0x1f812`, and `0x1f88e`.
- Parser scratch:
  numeric scratch and matched-byte buffers used by `0xdb74` / `0xdaf0`,
  lowercase chaining records rewound by `0x11f4c`, delayed binary-payload
  snapshots, and alternate/data append bytes stored by `0xe002`.
- Firmware bookkeeping:
  current parser callback `0x78299a`, page-root retry flag `+0x14.0`,
  allocator cursors `0x782a70`, `0x782a72`, `0x782a76`, publication/copy-stop
  flag `0x782996`, macro heap chunks, data-chain frames, `0x12328` drain
  state, and scheduler/work-record state after publication.
- Hardware/external:
  live host bus, direct host modes, host-output FIFO, retained-storage,
  optional resource windows, and formatter/DC timing. These are outside this
  command index unless the ROM has already reduced them to a byte, status
  field, page object, or render input.
- Unknown:
  no ROM-local parser-table unknown remains for the quick-reference command
  clusters listed below. Exact residuals are the secondary segment-57 physical
  decode at `0x0c0000..0x0c0321`, with suffix and continuation evidence in
  [Secondary Segment-57 Resource
  Source](unresolved-boundaries.md#secondary-segment-57-resource-source),
  compact downloaded-glyph helper targets above the valid `0x1fe76` table,
  broader byte-stream variants that change a named field/object/helper, and
  hardware/MMIO timing or physical naming.

State-only consumer index:

- `ESC &k#G`: writer `0xedf8` stores line-termination byte `0x78318f`.
  First visible consumers are CR/LF/FF handlers `0xf02c`, `0xf08c`, and
  `0xf0f0`.
- `ESC &k#H`: writer `0xca8c` stores HMI word `0x78315c`. First visible
  consumers are printable placement `0xd04a`, HT/BS `0xf1cc` / `0xf2a8`,
  and column-based margin/cursor handlers.
- `ESC &l#C/#D`: writers `0xcb00` and `0xc992` store VMI word `0x783160`.
  First visible consumers are LF/FF, `ESC =`, VFC jumps, row positioning,
  and page-length conversion.
- `ESC &l#P`: writer `0xf9e8` stores page length/vertical extent
  `0x782dba` for nonzero selectors and refreshes derived geometry. First
  visible consumers are printable placement, vertical overflow, raster bounds,
  rectangle clipping, and publication/page-control branches. Selector `0`
  can publish an existing root through `0xff1e` while restoring default page
  state.
- `ESC &l#E/#F`: writers `0xece2` and `0xea9e` store top offset
  `0x782dce` and text-bottom state `0x782dd2`. First visible consumers are
  printable placement, LF/FF, `ESC =`, VFC channel jumps, overflow helper
  `0xf36c`, raster origin/bounds, and rectangle clipping.
- `ESC &s#C`: writer `0xedb0` stores wrap byte `0x783190`. First visible
  consumers are printable prechecks `0xd28a` and `0xd6bc`.
- `ESC &l#L`: writer `0xee64` stores perforation byte `0x783191`. First
  visible consumer is overflow helper `0xf36c` before page eject.
- `ESC &l#W/#V`: table writer `0x12cfe` stores VFC words
  `0x782dde..0x782edd` plus bottom caches `0x782dc2` / `0x782dd2`; channel
  consumer `0x1280a` reads those fields with VMI, top offset, and current y.
  First visible effects are cursor movement before the next printable object
  or a page-boundary publication through `0xf124 -> 0xff1e`.
- `ESC 9`: writer `0xe9ba` resets left/right margin state
  `0x782dd6` / `0x782dda`. First visible consumers are CR reset, HT,
  printable placement, and margin/cursor limit checks.
- `ESC =`: writer `0xf176` advances vertical cursor `0x782c8e` by a half-line
  step derived from VMI `0x783160`. First visible consumers are following
  printable placement, raster origin, rectangle clipping, VFC, and overflow
  helper `0xf36c`.
- `SI` / `SO`: writers `0xc68a` and `0xc6b8` store selected slot
  `0x782f06`. First visible consumer is printable source capture
  `0xd04a -> 0x1393a`.
- `ESC &a#L/#M`: writers `0xeb58` and `0xec0c` store margin fields
  `0x782dd6` / `0x782dda` and may move horizontal cursor `0x782c8a`. First
  visible consumers are CR, printable placement, span flush, raster origin,
  and rectangle clipping.
- `ESC &a#C/#H/#R/#V` and `ESC *p#X/#Y`: cursor handlers store
  `0x782c8a` / `0x782c8e`. First visible consumers are printable placement,
  raster origin, rectangle clipping, VFC, or publication.
- `ESC &f#S`: writer `0xf75e` stores cursor stack
  `0x782c96..0x782d36`. First visible consumers are following placement after
  pop, raster origin, or rectangle clipping.
- `ESC &d#D`: writer `0x12622` stores underline/span selector `0x783185`.
  First visible consumer is span flush `0xf34a -> 0x12714`.
- `ESC &f#Y/#X`: writers `0xe112` and `0xdd08` store macro id, records, and
  frames. First visible consumers are replay byte source `0xa904` and overlay
  publication `0xff1e`.

These rows are delayed-output routes, not no-ops. A stream reproduces them
only when the named writer field reaches the listed consumer with the same
value and the owner note documents any later page-object, publication, or
render effect. Evidence is in
[direct-control-codes.md](direct-control-codes.md#direct-control-outcome-matrix),
[macro-data-chain.md](macro-data-chain.md#macro-replay-outcome-matrix), and
[publication-commands.md](publication-commands.md#page-environment-outcome-matrix).

Delayed state-to-output resolution:

- Placement, margin, HMI, and selected-context rows resolve at the next text
  producer when `0xd04a -> 0x1393a` reads cursor fields `0x782c8a` /
  `0x782c8e`, HMI `0x78315c`, selected slot `0x782f06`, current-font records,
  and page-root context slots. The text path then queues compact bucket objects
  through `0xd3b2` or `0xd824` into `0x12f2e -> 0x1387c`, publishes through
  `0xff1e`, bridges through `0x1ed84 -> 0x1edc6`, and renders through
  `0x1ef6a -> 0x1efc2 -> 0x1effe`.
- Pending span and underline rows resolve when a terminal consumer calls
  `0xf34a`. If span flag `0x783184` is set, `0xf34a -> 0x12714 -> 0x126e2`
  materializes a selector-`0x4000` segment-list object under page-root `+0x1c`;
  bridge `0x1ed84 -> 0x1edc6` copies that root to render `+0x18`, and
  `0x1ef6a -> 0x1efc2 -> 0x1f812` renders the span object.
- Vertical-layout, perforation, and VFC rows resolve through the same cursor
  and publication consumers. `0xf36c` reads cursor y `0x782c8e`, bottom limit
  `0x782dc2`, and perforation byte `0x783191` before page eject
  `0xf124 -> 0xff1e`; VFC channel consumer `0x1280a` reads VFC table words
  with VMI `0x783160`, top offset `0x782dce`, and current y before deciding
  cursor movement or page-boundary publication.
- Raster and rectangle commands consume the delayed placement fields before
  page-object storage. Raster setup and transfer use the current cursor/raster
  block before delayed reader `0x105d0 -> 0x13070 -> 0x13250` queues class
  `0x80` bucket objects. Rectangle setup and fill use the same layout bounds
  before `0x10898 -> 0x10b80 -> 0x13386 -> 0x133aa` queues rule-list objects.
  Those objects then follow the common bridge/render routes named in the page
  object handoff matrix.
- Macro state rows resolve by replay, not by a separate imaging path. `0xdd08`
  / `0xe112` create macro records and frames; replay feeds bytes back through
  `0xa904`, so the visible output is whatever owner receives the replayed
  bytes, including printable `0xd04a`, direct controls, raster payloads,
  rectangle handlers, or publication commands.

- Host byte source and parser admission:
  byte-source multiplexer `0xa904..0xab8a` reduces live host input, LIFO
  buffers, data-chain replay frames, ring input, and direct hardware modes to
  one normalized `D7` byte or `-1`. The observed source priority is service
  gate, first LIFO stack, active data-chain frame `0x782d76`, second LIFO
  stack, ring source, and direct hardware source. Data-chain frame `+0x00`
  supplies the payload head, `+0x04` the remaining byte count, `+0x08` the
  byte-source offset, and `+0x09` the frame kind; execute/call frames built by
  `0xe418` use kinds `2` / `3`, while overlay publication frame builder
  `0xe4f4` uses kind `4`. When a frame reaches its end marker, `0xa904` calls
  `0xe22c` and restarts source selection. Parser wrapper `0xda9a` and parser
  loop `0x11774` consume the resulting byte; transparent, display, raster, and
  downloaded-font payload readers also call `0xa904` directly when their
  command family owns subsequent raw bytes.
  Evidence:
  [Host Byte Source Outcome
  Matrix](host-byte-fetch.md#host-byte-source-outcome-matrix),
  [macro-data-chain.md](macro-data-chain.md), and
  [pcl-command-map.md](pcl-command-map.md).
- Parser records and delayed payload admission:
  parser loop `0x11774` indexes the normal table `0x112a4` or alternate/data
  table `0x116f6` using mode byte `0x782999`. Tokenizers `0xdb74` and
  `0xdaf0` build six-byte command records rooted at `0x78299e`: flags at
  `+0`, final byte at `+1`, signed integer parameter at `+2`, and signed
  fractional parameter at `+4`. Lowercase finals can leave a family record
  pending or rewind through helper `0x11f4c` instead of running a terminal
  semantic handler immediately. Delayed-payload setup `0x121cc` rewinds the
  active record cursor, sets pending byte `0x782a1a`, stores handler pointer
  `0x782a1c`, and saves the current six-byte record at `0x782a20..0x782a25`.
  Terminal restore `0x12218` copies that saved record back to the live parser
  record, clears the pending flag, and calls the saved handler in normal mode.
  In alternate/data mode it routes through `0x12358`, which calls wrapper
  `0x1228a` only when that exact generic wrapper was armed; otherwise positive
  payload counts append through `0xe002`. This shared boundary is why
  transparent data `0x12452`, VFC table load `0x12cfe`, raster transfer
  `0x105d0`, downloaded descriptor `0x15d0a`, and downloaded payload
  `0x16c14` all reopen restored parser records before consuming raw bytes.
  Evidence:
  [pcl-parser-firmware.md](pcl-parser-firmware.md),
  [pcl-command-map.md](pcl-command-map.md), and
  `Command Record And Payload Dispatch` in
  [end-to-end-reproduction-map.md](end-to-end-reproduction-map.md).
- Printable bytes and C0 controls:
  mode-zero `0x11774` dispatches printable bytes to `0xd04a`; CR/LF/FF/HT/BS
  use `0xf02c`, `0xf08c`, `0xf0f0`, `0xf1cc`, and `0xf2a8`. `0xd04a` /
  `0x1393a` build text source state, `0x12f2e` writes compact bucket
  objects, and controls mutate cursor and pending-span state. Compact text
  reaches `0xff1e`, `0x1ed84`, `0x1edc6`, `0x1ef6a`, and compact renderers.
  Normal-table `NUL`, `BEL`, and `VT` rows (`0x00`, `0x07`, `0x0b`) are
  explicit zero-handler parser entries: they reset parser mode and create no
  page object, state mutation, publication request, or render work.
  Alternate/data blank C0 rows `0x00` and `0x07..0x0f` append the byte through
  `0xe002` instead of page output. Control-Z byte `0x1a` enters local setup
  `0x11ea4` and mode `2`; normal nested `0x1a` reaches `0x120d2` and calls
  `0xd04a(0x1a)` only when context byte `0x782eeb + 0x10 * 0x782f06` is `1`,
  while normal `0x1a X` reaches `0x1219e` and calls `0xd04a(0x100)`.
  Alternate/data siblings `0x1210c` and `0x121b2` append literal `0x1a` or
  normalized `0x7f` through `0xe002`. `ESC ?` is consumed inside wrapper
  `0xda9a`; `ESC Z` belongs to the local `ESC Y ... ESC Z` direct readers, not
  a global drawing command.
  The concrete baseline `!!` stream maps bytes `21 21` to built-in
  `LINE_PRINTER` glyph `0x20`, compact object
  `00 00 00 00 00 00 00 02 20 00 01 20 02 02`, bridge context slot `0`, and
  render route `0x1ef6a -> 0x1efc2 -> 0x1effe -> 0x1f034 -> 0x1f354`;
  command-family variants should be compared against that spine when they
  change cursor state, selected context/map, object shape, or row helper
  inputs.
  Evidence:
  [direct-control-codes.md](direct-control-codes.md),
  [display-functions.md](display-functions.md),
  [pcl-command-map.md](pcl-command-map.md),
  [font-context-metrics.md](font-context-metrics.md),
  `Minimal Stream Walkthrough: !!` in
  [end-to-end-reproduction-map.md](end-to-end-reproduction-map.md), and
  [page-raster-imaging.md](page-raster-imaging.md).
- Reset, FF, page size, orientation, paper, and copies:
  `ESC E` uses `0xcc52`, FF uses `0xf0f0`, and `ESC &l` mode `10` terminals
  include `0xfc74`, `0x10220`, `0xef62`, and `0xeef0`. Reset/default
  producers restore canonical environment; `0xef62` publishes before
  paper-source changes; `0xeef0` writes `0x782da4`; page geometry writers
  update `0x782da2..0x782dc0`. These commands either publish a queued page,
  change later page defaults, or both. Concrete stream `! ESC E` queues
  compact object `00 00 00 00 00 00 00 01 20 00 01`, then reset publishes
  through `0xff1e`, stores the published pointer in `0x780ea6`, sets
  publication flag `0x782996`, clears current root `0x78297a`, and renders
  the preserved page through `0x1ed84 -> 0x1edc6 -> 0x1ef6a`. Paper-source
  stream `! ESC &l2H` reaches `0xef62`, publishes the queued compact object
  before state mutation, then writes selector value `0x80` to paper-source
  byte `0x782da6`, mirrors `0x780e8f = 0x80`, signals `0x780e26`, and sets
  pending refresh byte `0x782998 = 1`. Copy-count stream `! ESC &l2X FF`
  reaches `0xeef0`, stores `0x782da4 = 2` without publishing, and the
  following FF publication copies that value into pool-header word `+0x0c`
  before the same `0x1ed84 -> 0x1edc6 -> 0x1ef6a` render path.
  Evidence:
  [publication-commands.md](publication-commands.md),
  [Paper Source Selector Matrix](publication-commands.md#paper-source-selector-matrix),
  [reset-default-environment.md](reset-default-environment.md), and
  `Worked Path: Publication Commands` in
  [firmware-dataflow-model.md](firmware-dataflow-model.md).
- Cursor, margins, HMI/VMI, line termination, wrap, underline, and cursor
  stack:
  `ESC &a` mode `12`, `ESC &k` mode `11`, `ESC *p` dot-position handlers, and
  `ESC &f#S` `0xf75e` route to handlers `0xf39e`, `0xf416`, `0xf560`,
  `0xf60a`, `0xeb58`, `0xec0c`, `0xca8c`, `0xc992`, `0xcb00`, `0xedf8`,
  `0xedb0`, and `0xf75e`. They write cursor/layout flags and pending-span
  state. Most are state-only until a following printable byte, span flush, VFC
  jump, or publication consumes the updated state. Concrete stream
  `ESC &k1G!\r!` writes line-termination byte `0x78318f` through `0xedf8`;
  CR handler `0xf02c` applies CR+LF and makes the following printable queue at
  compact coordinate `0x3b00`. Cursor stream `ESC &a2C!` commits x through
  `0xf4ca` before the following printable queues at compact coordinate
  `0x0a02`. Cursor-stack stream `ESC &f0S ESC &a2C ESC &f1S!` uses
  `0xf75e`, `0xf39e`, `0xf75e`, and `0xd04a`: selector `0` pushes cursor x
  `0x782c8a` and `y + 0x782dbe` into stack `0x782c96..0x782d36`; selector
  `1` pops when above base `0x782c96`, restores x/y with extent clamps, clears
  pending/right-limit latches, and lets the following printable queue from the
  restored cursor instead of the intervening `ESC &a2C` position.
  Underline stream `ESC &d3D! ESC &d@` uses handler `0x12622`, printable path
  `0xd04a`, and handler `0x12622` again. `ESC &d3D` writes underline/span
  selector `0x783185 = 1` and re-arms pending span state through `0x126e2`;
  the printable updates pending span fields `0x783184`, `0x783186`,
  `0x783188`, and `0x78318a` through `0xd4ac` / `0xd8fc`; final `ESC &d@`
  flushes through `0x12714 -> 0x126e2`, materializing a selector-`0x4000`
  segment-list object under page-root `+0x1c` that publishes and renders
  through `0x1edc6 -> 0x1f812`.
  Evidence:
  [direct-control-codes.md](direct-control-codes.md) and
  `Text Cursor And Direct Controls` in
  [semantic-state-model.md](semantic-state-model.md).
- Vertical layout, VFC table definition, VFC channel jumps, and perforation
  skip:
  `ESC &l#W` schedules `0x11f6e -> 0x121cc`; normal restore reaches
  `0x12cfe`, while alternate/data restore reaches
  `0x12358 -> 0xdace -> 0xe002` and leaves the VFC table unchanged.
  `ESC &l#V` uses `0x1280a`; `ESC &l#L` uses `0xee64`; page length and
  vertical-layout terminals use `0xf9e8`, `0xcb00`, `0xc992`, `0xece2`, and
  `0xea9e`. Nonzero `ESC &l#P` converts line counts through VMI `0x783160`,
  writes page extent `0x782dba`, sets pending header byte `0x782997`, and
  refreshes geometry/default text length; selector `0P` restores the
  default-page branch. `ESC &l#C` writes VMI `0x783160` from accepted
  1/48-inch values; `ESC &l#D` maps accepted LPI selectors to the same VMI
  field and sets modified-layout byte `0x782ee1`; `ESC &l#E` writes top
  offset `0x782dce`; `ESC &l#F` writes text-bottom state `0x782dd2` or
  restores the default bottom for selector `0`. Normal table load writes
  `0x782dde..0x782edd` and line caches; channel jumps consume VMI, current y,
  top offset, and channel masks; perforation skip writes `0x783191`. Output
  is cursor-only movement, page publication/recovery, later printable
  placement, raster-origin/bounds state, rectangle clipping state, or later
  overflow page eject; no separate renderer exists. The first concrete
  page-image state is whichever later consumer fires: following printable bytes
  queue compact objects under root `+0x1c` through
  `0xd04a -> 0x12f2e -> 0x1387c`; overflow or VFC page-boundary paths publish
  a page/control record through `0xf36c` or `0xf124 -> 0xff1e`; raster
  consumers reach `0x1075a` or `0x105d0 -> 0x13070 -> 0x13250` before encoded
  raster objects exist under root `+0x1c`; rectangle consumers reach `0x10b80`
  and `0x13386 -> 0x133aa` before rule-list objects exist under root `+0x24`.
  Concrete stream
  `ESC &l4W 00 00 00 02 !` stores the four table bytes at `0x782dde`,
  derives VFC/text-bottom cache state before printable parsing resumes, and
  the following `!` queues at compact coordinate `0x9001`. Channel stream
  `ESC &l2V!` scans the table through `0x1280a`, writes y `176`, resets x to
  left margin `10`, and queues the following `!` at compact coordinate
  `0xb001`. Perforation stream `ESC &l1L!` dispatches to `0xee64`, sets
  perforation-skip byte `0x783191`, and leaves the following printable on the
  ordinary `0xd04a -> 0x12f2e` compact-text route; later vertical overflow
  helper `0xf36c` consumes `0x782c8e`, VFC/perforation limit `0x782dc2`, and
  `0x783191` to decide whether to publish through `0xf124 -> 0xff1e`.
  Evidence:
  [vertical-forms-control.md](vertical-forms-control.md),
  [publication-commands.md](publication-commands.md), and
  [pcl-command-map.md](pcl-command-map.md).
- Transparent and display-function data:
  `ESC &p#X` schedules `0x11f5a -> 0x121cc -> 0x12218 -> 0x12452`;
  `ESC Y ... ESC Z` uses normal direct reader `0x12536` or alternate/data
  reader `0x12120`. In normal parser mode, `0x12218` restores delayed
  transparent record state and calls `0x12452`; the reader consumes the
  absolute record count through direct `0xa904` fetches, normalizes local
  `0x1a 0x58 -> 0x7f`, applies the selected-context filter matrix, and
  re-enters `0xd04a` or `0xd0f0`, so printable transparent bytes can create
  compact text objects. In alternate/data mode, the same delayed
  `ESC &p#X` / `x` record does not call `0x12452`: `0x12218` diverts to
  `0x12358`, which drains positive payload counts through `0xdace` and
  appends normalized bytes through `0xe002`, leaving no immediate page
  object until later replay. Normal display-functions reader `0x12536` is
  also page-affecting: it fetches loop bytes through `0xa904` until local
  `ESC Z` termination, routes values through `0xd04a` or `0xd0f0`, and
  consumes the terminating pair as routed values before exit. Alternate/data
  reader `0x12120` appends literal `ESC Y` and loop values through `0xe002`
  with no immediate page object. Concrete stream
  `ESC &p2X!!` restores delayed record `80 58 00 02 00 00`, consumes payload
  bytes `21 21`, routes both through `0xd04a`, and queues the same compact
  coordinates `0x0001` and `0x0202` as the direct printable `!!` baseline
  before publication/render. Concrete stream `ESC Y!\x05! ESC Z` reaches
  `0x12536`, routes loop values `21 05 21 1b 5a` as
  `d04a d0f0 d04a d0f0 d04a`, and queues compact entries at `0x0001`,
  `0x0403`, and `0x0405`.
  `ESC z` is the display-functions-off status edge at `0xcd86..0xcda0`:
  it reads the active data-chain frame kind byte at `0x782d76 + 9`, calls
  `0x9c2c` only when that byte is zero, writes status/service fields
  `0x7821cc`, `0x7822db`, and `0x780e2a`, and creates no page object.
  The current pixel-affecting transparent-data residual is the secondary
  segment-57 source boundary: the ROM path is traced through `0x12452`,
  `0xd04a`, compact segmented page objects, bridge, and
  `0x1f354 -> 0x1f1f0`, but fallback rows need bytes from
  `0x0c0000..0x0c0321` after verified suffix `0x0bfe22..0x0bffff`.
  The exact checked-in stop is
  [Secondary Segment-57 Resource
  Source](unresolved-boundaries.md#secondary-segment-57-resource-source),
  including the suffix length, continuation length, and
  mirror/code-pair/zero-fill probe consequences.
  Evidence:
  [transparent-print-data.md](transparent-print-data.md#owner-summary) and
  [display-functions.md](display-functions.md).
- Raster graphics:
  `ESC *t#R` uses `0x10808`, `ESC *r#A/#B` use `0x1075a` / `0x107fa`, and
  delayed `ESC *b#W` uses
  `0x11f82 -> 0x121cc`; normal restore reaches `0x105d0`, while
  alternate/data restore reaches `0x12358 -> 0xdace -> 0xe002` and leaves the
  raster block and page objects unchanged. Raster handlers write
  `0x783170..0x783182`, gate transfer counts, allocate encoded-span objects
  through `0x13070` / `0x13250`, and copy payload via `0x138de`. Encoded
  raster objects publish through page roots and render via
  `0x1ef6a -> 0x1efc2 -> 0x1f88e`; dense split allocation is bounded at
  `0x132b6..0x13382`. Resolution handler `0x10808` updates encoded mode
  `0x783178` and scale `0x78317e` only while active byte `0x783182` is clear.
  Start handler `0x1075a` also exits early while `0x783182` is set; otherwise
  it sets the active byte, seeds origin `0x78317a` from portrait x cursor
  `0x782c8a`, landscape y cursor `0x782c8e`, or left edge depending on the
  `*r#A` selector, copies that origin to baseline `0x783170`, and recomputes
  row byte limit `0x783180`. End handler `0x107fa` clears only `0x783182`,
  leaving origin, baseline, mode, scale, limit, and row state for later
  transfers or resolution changes. Concrete stream
  `ESC *t300R ESC *r1A ESC *b4W f0 0f aa 55` queues encoded raster object
  `00 00 00 00 80 00 00 04 00 01 f0 0f aa 55`; byte `+0x04 = 0x80`
  selects raster dispatch, byte `+0x05 = 0` selects mode-0 literal helper
  `0x1f8da`, word `+0x06 = 4` is the copied payload capacity, and key
  `+0x08 = 0x0001` is the packed coordinate consumed after publication.
  Evidence:
  [raster-graphics.md](raster-graphics.md) and
  [page-raster-imaging.md](page-raster-imaging.md).
- Rectangle/rule graphics:
  `ESC *c` mode `16` routes width/height/fill writers `0x10e68`, `0x10e22`,
  `0x10dce`, and fill command `0x10898`. Size/id handlers write
  `0x783166..0x78316e`; `0x10898` clips the active rectangle and queues
  rule-list objects through `0x13386` / `0x133aa`. Solid and patterned rules
  render through `0x1f446`, `0x1f596`, and `0x1f4e0`, including
  band-crossing continuation. Area-fill stream `ESC *c50g2P` writes
  `0x78316e = 50` through `0x10dce`; `0x10898` maps `2P` gray percentages
  from `0x78316e` to selectors `0..7`, maps `3P` pattern ids `1..6` to
  selectors `8..13`, and applies landscape remaps for pattern ids `1..4`.
  Selector `7` renders through solid helper `0x1f596`; gray selectors `0..6`
  and HP-pattern selectors `8..13` render through pattern helper `0x1f4e0`.
  Concrete stream `ESC *c12a5b0P` queues selector-7 rule object
  `00 00 00 00 01 07 4a 00 00 0c 00 05 00 00` under page-root `+0x24`;
  bridge `0x1edc6` copies the rule list to render-record `+0x1c`, and
  `0x1f446` dispatches selector `7` to solid helper `0x1f596`.
  Evidence:
  [rectangle-graphics.md](rectangle-graphics.md) and
  [page-raster-imaging.md](page-raster-imaging.md).
- Direct margin and vertical-placement controls: manual `ESC 9` reaches handler
  `0xe9ba`, clears left margin `0x782dd6`, copies page width `0x782db8` into right
  margin `0x782dda`, and clears fractional margin companion `0x782ddc`. Its page effect
  is delayed until a later consumer such as CR `0xf02c`, HT `0xf1cc`, printable text
  `0xd04a`, rectangle setup, or raster-start placement reads the updated limits. Manual
  `ESC =` reaches handler `0xf176`, ensures page root `0x10084`, flushes pending
  text/span state through `0xf34a`, converts VMI `0x783160` through `0x104fe` /
  `0x104d8` / `0x10518`, advances vertical cursor `0x782c8e` by half the current VMI,
  then clears pending page-eject byte `0x782a6d`. The documented visible streams are
  `ESC 9 CR !` and `ESC = !`, where later handlers consume the margin or vertical-cursor
  state before queueing compact text through `0x12f2e`. Evidence:
  [direct-control-codes.md](direct-control-codes.md#owner-summary),
  [pcl-command-map.md](pcl-command-map.md), and
  [end-to-end-reproduction-map.md](end-to-end-reproduction-map.md#supported-stream-entry-points).
- Font selection and downloaded fonts:
  primary/secondary setup `0x1201e` / `0x12008`, designation terminal
  `0x120be`, attribute wrappers around `0xc930`, `0xc89c`, `0xc6ec`,
  `0xc780`, `0xc840`, `0xc7e0`, and downloaded `W` handler `0x11f96` are the
  first route boundaries. Selection updates requested fields and maps via
  `0xc580`, `0x13eb8`, `0x144d2`, and `0x14c64`; downloaded
  descriptors/payloads use `0x15d0a`, `0x16c14`, `0x1719c`, and `0x16498`.
  Pitch-mode `ESC &k#S/s` is routed through handler `0xc390`, which accepts
  selectors `0`, `2`, and `4`, rewrites synthetic pitch records, and rejoins
  `0xc89c -> 0xc580` before any later printable output. SO/SI are the
  control-code bridge into those selected font slots: SO handler `0xc6b8`
  calls `0xc428(1)` / `0xc4fc`, installs page-root context slot `1`, and sets
  selected slot `0x782f06 = 1`; SI handler `0xc68a` does the same for slot
  `0`. Composed primary stream `ESC (s0p10h12v0s0b3T SI !!` writes primary
  context `0x782ee6` and map `0x782f32` before the following printables queue
  through `0xd04a`. Composed secondary stream
  `ESC )s0p16h8v0s0b0T SO !!` writes secondary context `0x782ef6`, map
  `0x783032`, and then queues SO-selected compact rows from page-root slot
  `1`.
  Symbol-set and font-designation terminals are not drawing commands. Normal
  finals store requested symbol words through `0x120be -> 0x1be22`,
  final-`@` dispatches through the ROM default-symbol table, and final-`X`
  calls `0x17708(slot, parameter)` for font-id selection. Those paths rejoin
  `0xc580`, selected-context rebuild, and map rebuild before any pixel effect.
  In alternate/data mode, `ESC (` reaches `0x11fe4` and `ESC )` reaches
  `0x11fd2`; those wrappers call `0x11ec8 -> 0xdaf0` without the normal
  primary/secondary slot-record helpers `0x11f26` / `0x11efe`, and ordinary
  final rows are blank instead of `0x120be`. Stored macro/data streams
  therefore preserve the bytes without immediately changing requested symbol
  words, selected maps, page-root context slots, or glyph render inputs.
  The `0x14f16` patcher mutates only the rebuilt active map, so the output
  contract remains: track the requested/active symbol words, selected context,
  and `0x782f32` / `0x783032` until later printable bytes reach
  `0xd04a -> 0x1393a`. The owner notes are
  [Symbol/Font Designation Outcome
  Matrix](symbol-set-selection.md#symbolfont-designation-outcome-matrix) and
  [symbol-map-patching.md](symbol-map-patching.md).
  Font-control rows in the `ESC *c` family are state/resource controls:
  `ESC *c#D` reaches `0x15a56` and writes current downloaded-font id
  `0x782f2e`, `ESC *c#E` reaches `0x15a18` and writes current character word
  `0x782f30`, and `ESC *c#F` reaches dispatcher `0x16df6`. Selector `5`
  runs `0x16e86 -> 0x17108` to mark the current record, selector `4` uses
  `0x17150` to unmark it, selectors `0..3` and `6` release or refresh
  current-record/resource state when mode byte `0x782a92 != 2`, and other
  selectors return without page output. These rows create no page object by
  themselves; later `ESC (s#W` / `ESC )s#W` descriptor or payload handlers
  consume the selected id/character/current-record state before printable text
  can queue a downloaded-glyph compact object. In alternate/data mode, delayed
  font `W/w` payload restore reaches `0x12358 -> 0xdace -> 0xe002` instead of
  `0x15d0a` or `0x16c14`, so no descriptor validation, current-record install,
  selected-map refresh, page object, or render input is produced until appended
  bytes replay later. Concrete chain
  `ESC *c4660d37e5F` stays in parser mode `16` across lowercase finals:
  `4660d` writes `0x782f2e = 0x1234` through `0x15a56`, `37e` writes
  `0x782f30 = 0x25` through `0x15a18`, and `5F` dispatches through
  `0x16df6 -> 0x16e86 -> 0x17108` to mark the current downloaded-font record
  by moving flag/count state between `0x782782` and `0x782786`. A following
  nonzero `ESC )s#W` payload handler `0x16c14` consumes `0x782f2e`,
  `0x782f30`, current-record pool `0x782640..0x782776`, and payload budget
  `0x783140` before a later printable can select the installed glyph.
  Successful downloaded-character copies return through
  `0x15dc6 -> 0x16498 -> 0x15dcc -> 0x12328`; the usual full-success case
  leaves `0x783140 = 0`, drains zero bytes, and resumes at the next parser
  handler. Rejected or partial payloads use the same boundary with a nonzero
  remaining budget or status-`2` continuation state, so reproduction must
  distinguish an installed glyph from a payload drain before interpreting the
  following byte.
  Selected maps affect later printable bytes; downloaded glyphs install
  records that later queue compact objects and render through `0x1effe` /
  `0x1f0d2` / `0x1f1f0` / `0x1f264`. Concrete final-`X` stream
  `ESC (7X!!` selects built-in context `0xc0089fb0` and queues prefix
  `00 00 00 00 00 00 00 02 00 89 00 00 87 02`. Concrete downloaded glyph
  stream `ESC )s80W ... ESC )s3W f0 f0 f0 !` installs glyph `0x21`, queues
  compact object `00 00 00 00 00 00 00 01 21 5a 00`, and renders through the
  same publication/bridge/compact-render pipeline.
  Downloaded-glyph row and width boundary streams stay on that same route, but
  split the state a reader must track. Writer `0x16498` preserves canonical
  downloaded-glyph record fields such as mode byte `+5`, 16-bit row word `+6`,
  width word `+8`, and bitmap bytes at `+0x0c`; later printable handling
  through `0xd04a -> 0x1393a -> 0x12f2e` consumes the selected glyph as a
  page-source object and derives compact selector/bucket state. Publication
  `0xff1e`, bridge `0x1ed84` / `0x1edc6`, and render dispatch `0x1ef6a ->
  0x1effe` then feed helper `0x1fe76` for short compact rows, `0x1f0d2` for
  wide compact rows, `0x1f1f0` for segmented rows, or `0x1f264` for
  segmented-wide rows. The exact ROM-local output boundaries are the unchecked
  short-helper fallback table read `0x1fe76 -> 0x1fe8a` above valid index
  `128`, wrapped low-width mode-0 helper targets through `0x1f034 ->
  0x1f08e`, segmented-wide span-31 fallback source offset `+0xb50`, and
  oversized segmented-wide payloads that exceed the restored `ESC )s#W` count
  cap `0x7fff` before `0x16498` can install a glyph.
  Evidence:
  [font-context-metrics.md](font-context-metrics.md),
  [pcl-command-map.md](pcl-command-map.md),
  [built-in-resource-scan.md](built-in-resource-scan.md), and
  [downloaded-fonts.md](downloaded-fonts.md); row-copy helper details are in
  [page-raster-imaging.md](page-raster-imaging.md).
- Macro definition, replay, overlay, and data-chain input:
  `ESC &f#Y` uses `0xe112`, `ESC &f#X` uses `0xdd08`, alternate append uses
  `0xe002`, execute/call frames come from `0xe418`, and overlay frame
  production uses `0xe4f4` from `0xff1e`. Macro records live at `0x782a98`,
  current id at `0x783164`, data-chain frames at `0x782d76`, and overlay
  id/state at `0x782a94` / `0x782a92`.

  Macro-control selector `0` starts definition mode and stores following bytes
  through `0xe002`; selector `1` stops definition mode; selectors `2` and `3`
  execute/call the selected record through `0xe418`; selectors `4` and `5`
  enable/disable overlay state; selectors `6`, `7`, and `8` delete all,
  temporary, or current records; and selectors `9` / `10` clear or set record
  permanence byte `+0x0a`. Definition/delete/permanence controls create no
  page object by themselves; their output effect appears when stored payload
  bytes later replay or when overlay state is consumed by publication.

  Definition storage is a linked chunk stream, not an immediate parser
  side-effect: `0xe002` appends only when the active frame kind byte `+9` is
  zero and append-error byte `0x782c19` is clear, allocates 0x100-byte chunks
  through `0x170c`, uses the first longword as the next pointer, and counts
  four header bytes per chunk in record word `+0x04`. Stop selector `1`
  normalizes that raw count by subtracting the per-chunk headers. Execute and
  call selectors build replay frames through `0xe418..0xe4f2`: the new frame
  is 14 bytes after the current `0x782d76` frame, copies selected record
  head/count into `+0x00/+0x04`, writes byte-source offset `+0x08 = 4`, writes
  frame kind `+0x09 = 2` for execute or `3` for call, stores a linked
  environment snapshot at `+0x0a`, sets host gate bit `0x780e66.1` when the
  count is positive, and pushes a 10-byte context entry for call mode.

  The host-byte source makes replay ordinary input: `0xa904` gives active
  data-chain frame bytes priority over live ring input, so the stored payload
  re-enters wrapper `0xda9a`, parser loop `0x11774`, the same command-family
  handlers, the same page objects, and the same render path as live bytes.
  When a replay frame reaches its end, `0xa904` calls `0xe22c..0xe408`.
  Execute frames restore/free linked snapshots, rewind `0x782d76`, and clear
  the host gate bit if the previous frame has no bytes; call and overlay
  returns restore context, call `0xe65c(0)`, and may publish through `0xf124`.

  Overlay replay is a publication-time detour, not a separate renderer.
  Selector `4` stores enabled state in `0x782a92` and saved id `0x782a94`.
  During `0xff1e`, an eligible overlay record causes `0xe4f4..0xe5e0` to push
  a macro context entry, snapshot flat state, save cursor longword
  `0x782c92`, install non-replay frame `0x782d4c` into `0x782d76`, copy
  record head/count, write `+0x08 = 4`, `+0x09 = 4`, and `+0x0a = 0`, then
  replay overlay bytes before final root publication. Overlay can add text,
  transparent data, raster, rule/span payloads before publication.
  Concrete overlay stream
  `ESC &f123Y ESC &f0X ! CR ESC &f1X ESC &f4X` stores payload `21 0d`;
  publication replays it before root copy, queues compact text object
  `00 00 00 00 00 00 00 01 20 00 01`, and lets CR mutate cursor/page state
  without adding a second visible object.
  Evidence:
  [Macro Replay Outcome Matrix](macro-data-chain.md#macro-replay-outcome-matrix).
- Status/model side channels:
  `ESC *r#K` and `ESC *s#^` route through `0x12034 -> 0x122be` and
  host-output helper `0xb090`. They consume status/model predicates and output
  bytes through the host FIFO. They emit host-visible response bytes such as
  `33440A\r\n`; they do not create page roots or pixels. Concrete stream
  `ESC *r1K 0x11` reaches wrapper `0x12034`, setup helper `0x11efe`, and
  producer `0x122be..0x12326`; active record word `+2 = 1` plus query byte
  `0x11` makes the producer walk literal `33440A\r\n` at `0x12280..0x12288`
  and enqueue each byte through `0xb090`. The `ESC *s#^ 0x11` sibling reaches
  the same producer from parser mode `6`. Canonical host-output state is FIFO
  count `0x783ed2`, read pointer `0x783ed4`, write pointer `0x783ed8`, and
  storage `0x783e92..0x783ed1`; a full FIFO can stall this parser-side
  producer, but no FIFO/status consumer feeds page roots or render helpers.
  Terminal report exits such as `0x1284` / `0x128c` are the same owner class:
  they consume a two-byte code, select/display a status string through
  `0x158c -> 0x8c7a`, cache bytes at `0x783ef0..0x783ef1`, and enter the
  `0x12d4..0x13b0` hardware-report loop without page output.
  Evidence:
  [Host/Status Outcome Matrix](errors-and-status.md#hoststatus-outcome-matrix) and
  [host-byte-fetch.md](host-byte-fetch.md).
- Shared page/render/output convergence:
  all pixel-producing families above converge after command-family page-object
  production. Current page root `0x78297a` owns compact bucket roots at
  `+0x1c`, rule roots at `+0x24`, fixed-list roots at `+0x28`, and context
  slots at `+0x2c..+0x68`. Helper `0x10084` ensures the root and shared
  allocator `0x1381c` advances stream cursors `0x782a70`, `0x782a72`, and
  `0x782a76`. Compact text, downloaded glyphs, portrait spans, and encoded
  raster rows write bucket objects under root `+0x1c` through `0x12f2e` /
  `0x1387c`, `0x12714` / `0x13520` / `0x135f0`, and `0x13070` / `0x13250`.
  Rectangle/rule objects write the ordered list at root `+0x24` through
  `0x13386 -> 0x133aa`; fixed-list or landscape span objects write root
  `+0x28` through `0x136d2`. Publication `0xff1e` freezes the active root into
  a page/control pool record. Pool state then carries that record to the
  renderer: protected published head `0x780ea6`, scheduler cursor `0x780eaa`,
  active source `0x780eae`, and release cursor `0x780eb2` are initialized by
  `0x3144..0x3162`, populated through candidate paths `0x1c04..0x2016`,
  selected by `0x7ec6..0x7f90`, advanced by `0x7722..0x779a`, and copied from
  `0x780eaa` to `0x780eae` by `0x1eb32..0x1eb50`.

  Render work records are the middle edge between the pool and bitmap
  dispatch. Startup `0x2feb6` initializes selector bytes `0x7820bc` and
  `0x7820c0`; `0x1ecd6..0x1ed76` alternates records `0x7820c4` and
  `0x782128`, writes active pointer `0x783a18`, initializes geometry through
  `0x1ee9e` when the source geometry changes, or reuses same-geometry fields
  through `0x33238`. Bridge `0x1ed84 -> 0x1edc6` then copies source roots into
  render-record roots `+0x18`, `+0x1c`, `+0x20`, and context slots
  `+0x24..+0x60`.

  The active band loop `0x1eba4..0x1ecd2` decides when the selected render
  record actually reaches bitmap dispatch. It consumes active/paired
  work-record fields `+0x06`, `+0x0c`, `+0x0e`, `+0x10`, and `+0x16`, cleans
  up when `0x780ea5` is set or `+0x0c < +0x10`, throttles when `+0x0e > 0x28`,
  waits when computed capacity is below `9`, and otherwise calls `0x1ef6a`
  before incrementing render band word `+0x10` and throttle word `+0x0e`.

  Render entry `0x1ef6a` loads active render record `0x783a18`, derives band
  caches through `0x1ef86`, then calls bucket-chain renderer `0x1efc2`,
  rule-list renderer `0x1f446`, and fixed-list renderer `0x1f756` in that
  order. Bucket objects dispatch compact glyphs through `0x1effe`,
  segment-list spans through `0x1f812`, and encoded raster through `0x1f88e`.
  Destination helpers write current-band buffer `0x783a28` or fallback buffer
  `0x7810b4 + byte_pair_offset` using stride `0x783a1c` and row offsets
  `0x7839f8..`; documented helpers store generated words or bytes directly
  rather than blending against previous destination contents.
  Physical engine consumption of those rendered buffers is the formatter/DC
  boundary, not another parser command effect. Evidence:
  [Render Entry Outcome Matrix](page-raster-imaging.md#render-entry-outcome-matrix),
  [active-render-scheduler.md](active-render-scheduler.md), and
  [page-record-storage.md](page-record-storage.md).

This index is evidence-backed as a routing map because it is grounded in the
checked-in parser table audit in [pcl-command-map.md](pcl-command-map.md) and
the owning command-family notes named in the table. Pixel claims for a
specific stream belong to the owner note that traces the concrete fields, page
objects, bridge records, and render helpers.
