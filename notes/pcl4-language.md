# PCL4 / PCL Level IV Notes

Sources: `33440-90905_HP_LaserJet_series_II_Technical_Reference_Manual_Aug1989.pdf`, especially ch.
1-3, ch. 13, appendix A.

## PCL Level

LaserJet Series II is a PCL Level IV device. PCL levels are upward-compatible supersets:

- Level I: print and space.
- Level II: EDP/transaction.
- Level III: office word processing.
- Level IV: page formatting.

PCL commands set printer features and normally remain in effect until changed by another command or
reset.

Unsupported PCL commands should be ignored.

## Command Types

PCL has three command types:

- Control codes: single ASCII control characters such as CR, LF, FF.
- Two-character escape sequences: `ESC X`.
- Parameterized escape sequences.

`ESC` is ASCII 27 / hex `1B`. The manuals print it as `Ec` or similar OCR variants.

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
- `[binary data]`: immediate bytes after terminator, length usually given by value field.

If a required value field is omitted, value 0 is assumed.

## Combining Commands

Commands with the same parameterized and group characters can be combined. In a combined sequence,
previous terminators become lowercase parameter characters until the final uppercase terminator.

Example concept:

```text
ESC &l1O
ESC &l2A
```

Can combine to:

```text
ESC &l1o2A
```

Parser implication: the same final letter in different case can mean "parameter continues" versus
"command terminates".

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

The printer tracks positions internally in 1/3600 inch units and truncates to physical dot positions
when printing.

Columns are based on HMI. Rows are based on VMI or lines per inch.

## Logical Page and Printable Area

The logical page is the addressable area in which the PCL cursor can be positioned. The cursor
cannot move outside logical page bounds. The printable area is the part of the physical page where
the engine can place dots.

`(0,0)` is at the left edge of the logical page at the current top margin position. Changing top
margin changes the physical position of `(0,0)`.

All dimensions below are 300 dpi dots from Technical Reference figures 2-2 and 2-3. Columns
`A`/`B` are physical dimensions, `C`/`D` are logical dimensions, and `E`/`F`/`G`/`H` are
left/right/top/bottom unprintable margins.

Portrait:

| Paper | Phys W `A` | Phys L `B` | Log W `C` | Log L `D` | Left `E` | Right `F` | Top `G` | Bottom `H` |
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

| Paper | Phys L `A` | Phys W `B` | Log W `C` | Log L `D` | Left `E` | Right `F` | Top `G` | Bottom `H` |
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

- Text: if any part of the character cell falls outside the printable area, the whole character is
  clipped, even if the out-of-area portion has no set dots.
- Raster graphics and rules: if the cursor starts inside the printable area, only the portion
  extending outside the printable area is clipped.

## Print Environments

### Factory Default Environment

ROM-stored defaults. See [control-panel-nvram-selftest.md](control-panel-nvram-selftest.md).

### User Default Environment

Control-panel-selected defaults, retained across power-off. LaserJet II user defaults:

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

Approximate soft font formula and macro formula are in the Technical Reference; verify from PDF
before coding an exact memory-accounting test.

## Common PCL Errors

- `20 ERROR`: memory overflow during font download, macro creation, raster graphics download, or
  page composition.
- `21 ERROR`: page too complex to print at engine pace.
- `22 ERROR`: I/O protocol problem.
- `40 ERROR`: data transfer problem, often baud mismatch or host power transition.

## Command Quick Reference

This is an emulator-oriented subset from appendix A. `#` is an ASCII decimal value.

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
| HMI in 1/120 inch increments | `ESC &k#H` |
| VMI in 1/48 inch increments | `ESC &l#C` |
| Lines per inch | `ESC &l#D` |

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
| Delete all fonts | `ESC *c0F` |
| Delete temporary fonts | `ESC *c1F` |
| Delete last specified font ID | `ESC *c2F` |
| Make font temporary | `ESC *c4F` |
| Make font permanent | `ESC *c5F` |
| Select primary font by ID | `ESC (#X` |
| Select secondary font by ID | `ESC )#X` |

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
| End-of-line wrap on | `ESC &s0C` |
| End-of-line wrap off | `ESC &s1C` |

## Emulator Takeaways

- Build the parser around command syntax and environment mutation, not isolated strings.
- Implement command combining correctly early; real drivers use it.
- `ESC E` must differ from panel reset in page-buffer behavior.
- Internal positioning should use 1/3600 inch units if you want command-compatible cursor math.
- Unsupported commands should consume the correct syntax and then no-op.
