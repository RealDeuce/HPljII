# PCL4 / PCL Level IV Notes

Sources:
`33440-90905_HP_LaserJet_series_II_Technical_Reference_Manual_Aug1989.pdf`,
especially ch. 1-3, ch. 13, appendix A.

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

Evidence: [pcl-parser-core.md](pcl-parser-core.md),
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
- font selection and downloaded fonts: primary/secondary font selectors,
  symbol-set handling, downloaded-font descriptors, downloaded-character
  payloads, and compact glyph renderers;
- macros and alternate/data parsing: macro id/control commands, data-chain
  replay, overlay publication, and display-functions append behavior.

Concrete evidence is in [pcl-command-map.md](pcl-command-map.md),
[pcl-parser-core.md](pcl-parser-core.md),
[semantic-state-model.md](semantic-state-model.md), and the command-family
notes cited from those files.

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
| Display functions off | `ESC Z` |
| Transparent print data | `ESC &p#X` followed by data |

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
- Pixel-producing streams must pass through page-object publication and render
  dispatch where applicable: current page root `0x78297a`, publication
  `0xff1e`, active-record bridge `0x1ed84` / `0x1edc6`, and render entry
  `0x1ef6a`.
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
  decode at `0x0c0000..0x0c0321`, compact downloaded-glyph helper targets
  above the valid `0x1fe76` table, broader byte-stream variants that change a
  named field/object/helper, and hardware/MMIO timing or physical naming.

- Printable bytes and C0 controls:
  mode-zero `0x11774` dispatches printable bytes to `0xd04a`; CR/LF/FF/HT/BS
  use `0xf02c`, `0xf08c`, `0xf0f0`, `0xf1cc`, and `0xf2a8`. `0xd04a` /
  `0x1393a` build text source state, `0x12f2e` writes compact bucket
  objects, and controls mutate cursor and pending-span state. Compact text
  reaches `0xff1e`, `0x1ed84`, `0x1edc6`, `0x1ef6a`, and compact renderers.
  The concrete baseline `!!` stream maps bytes `21 21` to built-in
  `LINE_PRINTER` glyph `0x20`, compact object
  `00 00 00 00 00 00 00 02 20 00 01 20 02 02`, bridge context slot `0`, and
  render route `0x1ef6a -> 0x1efc2 -> 0x1effe -> 0x1f034 -> 0x1f354`;
  command-family variants should be compared against that spine when they
  change cursor state, selected context/map, object shape, or row helper
  inputs.
  Evidence:
  [direct-control-codes.md](direct-control-codes.md),
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
  the preserved page through `0x1ed84 -> 0x1edc6 -> 0x1ef6a`.
  Evidence:
  [publication-commands.md](publication-commands.md),
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
  `0x0a02`.
  Evidence:
  [direct-control-codes.md](direct-control-codes.md) and
  `Text Cursor And Direct Controls` in
  [semantic-state-model.md](semantic-state-model.md).
- VFC table definition, VFC channel jumps, and perforation skip:
  `ESC &l#W` schedules `0x11f6e -> 0x121cc -> 0x12218 -> 0x12cfe`;
  `ESC &l#V` uses `0x1280a`; `ESC &l#L` uses `0xee64`. The table loader
  writes `0x782dde..0x782edd` and line caches; channel jumps consume VMI,
  current y, top offset, and channel masks; perforation skip writes
  `0x783191`. Output is cursor-only movement, page publication/recovery, or
  later overflow page eject; no separate renderer exists. Concrete stream
  `ESC &l4W 00 00 00 02 !` stores the four table bytes at `0x782dde`,
  derives VFC/text-bottom cache state before printable parsing resumes, and
  the following `!` queues at compact coordinate `0x9001`. Channel stream
  `ESC &l2V!` scans the table through `0x1280a`, writes y `176`, resets x to
  left margin `10`, and queues the following `!` at compact coordinate
  `0xb001`.
  Evidence:
  [vertical-forms-control.md](vertical-forms-control.md).
- Transparent and display-function data:
  `ESC &p#X` schedules `0x11f5a -> 0x121cc -> 0x12218 -> 0x12452`;
  `ESC Y ... ESC Z` uses `0x12536` or alternate `0x12120`. The transparent
  reader consumes counted bytes through `0xdace`, normalizes/filter-controls,
  and re-enters printable/control paths; display readers append/report bytes
  without ordinary page-state effects. Transparent bytes can become compact
  text through the same `0xd04a` path. Display-functions are parser/input
  behavior, not page imaging. Concrete stream `ESC &p2X!!` restores delayed
  record `80 58 00 02 00 00`, consumes payload bytes `21 21`, routes both
  through `0xd04a`, and queues the same compact coordinates `0x0001` and
  `0x0202` as the direct printable `!!` baseline before publication/render.
  Evidence:
  [transparent-print-data.md](transparent-print-data.md) and
  [display-functions.md](display-functions.md).
- Raster graphics:
  `ESC *t#R` uses `0x10808`, `ESC *r#A/#B` use `0x1075a` / `0x107fa`, and
  delayed `ESC *b#W` uses
  `0x11f82 -> 0x121cc -> 0x12218 -> 0x105d0`. Raster handlers write
  `0x783170..0x783182`, gate transfer counts, allocate encoded-span objects
  through `0x13070` / `0x13250`, and copy payload via `0x138de`. Encoded
  raster objects publish through page roots and render via
  `0x1ef6a -> 0x1efc2 -> 0x1f88e`; dense split allocation is bounded at
  `0x132b6..0x13382`. Concrete stream
  `ESC *t300R ESC *r1A ESC *b4W f0 0f aa 55` queues encoded raster object
  `00 00 00 00 80 00 00 04 00 01 f0 0f aa 55`; byte `+0x04 = 0x80`
  selects raster dispatch, byte `+0x05 = 0` selects mode-0 literal helper
  `0x1f8da`, word `+0x06 = 4` is the copied payload capacity, and key
  `+0x08 = 0x0001` is the packed coordinate consumed after publication.
  Evidence:
  [raster-graphics.md](raster-graphics.md).
- Rectangle/rule graphics:
  `ESC *c` mode `16` routes width/height/fill writers `0x10e68`, `0x10e22`,
  `0x10dce`, and fill command `0x10898`. Size/id handlers write
  `0x783166..0x78316e`; `0x10898` clips the active rectangle and queues
  rule-list objects through `0x13386` / `0x133aa`. Solid and patterned rules
  render through `0x1f446`, `0x1f596`, and `0x1f4e0`, including
  band-crossing continuation. Concrete stream `ESC *c12a5b0P` queues
  selector-7 rule object
  `00 00 00 00 01 07 4a 00 00 0c 00 05 00 00` under page-root `+0x24`;
  bridge `0x1edc6` copies the rule list to render-record `+0x1c`, and
  `0x1f446` dispatches selector `7` to solid helper `0x1f596`.
  Evidence:
  [rectangle-graphics.md](rectangle-graphics.md).
- Font selection and downloaded fonts:
  primary/secondary setup `0x1201e` / `0x12008`, designation terminal
  `0x120be`, attribute wrappers around `0xc930`, `0xc89c`, `0xc6ec`,
  `0xc780`, `0xc840`, `0xc7e0`, and downloaded `W` handler `0x11f96` are the
  first route boundaries. Selection updates requested fields and maps via
  `0xc580`, `0x13eb8`, `0x144d2`, and `0x14c64`; downloaded
  descriptors/payloads use `0x15d0a`, `0x16c14`, `0x1719c`, and `0x16498`.
  Pitch-mode `ESC &k#S/s` is routed through handler `0xc390`, which accepts
  selectors `0`, `2`, and `4`, rewrites synthetic pitch records, and rejoins
  `0xc89c -> 0xc580` before any later printable output.
  Selected maps affect later printable bytes; downloaded glyphs install
  records that later queue compact objects and render through `0x1effe` /
  `0x1f0d2` / `0x1f1f0` / `0x1f264`. Concrete final-`X` stream
  `ESC (7X!!` selects built-in context `0xc0089fb0` and queues prefix
  `00 00 00 00 00 00 00 02 00 89 00 00 87 02`. Concrete downloaded glyph
  stream `ESC )s80W ... ESC )s3W f0 f0 f0 !` installs glyph `0x21`, queues
  compact object `00 00 00 00 00 00 00 01 21 5a 00`, and renders through the
  same publication/bridge/compact-render pipeline.
  Evidence:
  [font-context-metrics.md](font-context-metrics.md),
  [built-in-resource-scan.md](built-in-resource-scan.md), and
  [downloaded-fonts.md](downloaded-fonts.md).
- Macro definition, replay, overlay, and data-chain input:
  `ESC &f#Y` uses `0xe112`, `ESC &f#X` uses `0xdd08`, alternate append uses
  `0xe002`, execute/call frames come from `0xe418`, and overlay frame
  production uses `0xe4f4` from `0xff1e`. Macro records live at `0x782a98`,
  current id at `0x783164`, data-chain frames at `0x782d76`, and overlay
  id/state at `0x782a94` / `0x782a92`; `0xa904` gives replay frames
  byte-source priority. Stored bytes re-enter the same parser and renderer as
  live bytes. Overlay can add text, transparent data, raster, rule/span
  payloads before publication. Concrete overlay stream
  `ESC &f123Y ESC &f0X ! CR ESC &f1X ESC &f4X` stores payload `21 0d`;
  publication replays it before root copy, queues compact text object
  `00 00 00 00 00 00 00 01 20 00 01`, and lets CR mutate cursor/page state
  without adding a second visible object.
  Evidence:
  [macro-data-chain.md](macro-data-chain.md).
- Status/model side channels:
  `ESC *r#K` and `ESC *s#^` route through `0x12034 -> 0x122be` and
  host-output helper `0xb090`. They consume status/model predicates and output
  bytes through the host FIFO. They emit host-visible response bytes such as
  `33440A\r\n`; they do not create page roots or pixels. Evidence:
  [errors-and-status.md](errors-and-status.md) and
  [host-byte-fetch.md](host-byte-fetch.md).

Confidence is high for this index as a routing map because it is backed by the
checked-in parser table audit in [pcl-command-map.md](pcl-command-map.md) and
the owning command-family notes named in the table. Pixel confidence for any
specific stream still belongs to the owner note that traces the concrete
fields, page objects, bridge records, and render helpers.
