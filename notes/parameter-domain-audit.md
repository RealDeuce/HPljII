# Parameter Domain Audit

This note audits the documentation failure mode where one exercised fixture
stream can accidentally become the semantic claim for an entire parameterized
command family. The audit is source-level documentation work: each row checks
whether the checked-in owner docs describe the handler's parameter domain,
distinguished values, shared exits, and no-op/reject cases, instead of only the
named fixture stream.

Audit method:

- Search the owner notes for fixture-shaped wording such as `documented path`,
  `covered selector`, `only for`, `primary stream`, and literal `ESC ...`
  streams used as sentence subjects.
- Compare each suspect against the command-family index in
  [pcl-command-map.md](pcl-command-map.md#high-value-normal-mode-handlers).
- Spot-check the handler listings for families most likely to hide sibling
  parameter behavior.
- Patch any claim where a fixture example was standing in for the full command
  domain.

## Result

One documentation defect was confirmed and fixed: underline/span command
documentation over-emphasized `ESC &d3D`. The ROM writes selector `1` only for
absolute `3D`, but accepted non-`3D` `D` forms such as `0D`, `1D`, and `2D`
write selector `0` and still arm pending span state through `0x126e2`.

No other audited high-value command family had the same defect in the checked
owner docs. Some families still use fixture streams as examples, but their
owner prose also states the parameter domain and sibling behavior.

## Audited Command Families

- `ESC &l#A` page size:
  Evidence is `0xfc74..0xfdc8`, the page-size handler listing, and the
  command map. The docs list accepted table values `1`, `2`, `3`, `26`, `80`,
  `81`, `90`, and `91`; other values are ignored. Result: pass.
- `ESC &l#O` orientation:
  Evidence is `0x10220`, the orientation listing, and the command map. Values
  below `2` are accepted, values `>= 2` are rejected, and the same value exits
  unchanged. Result: pass.
- `ESC &l#P` page length:
  Evidence is `0xf9e8..0xfc52` and the command map. Nonzero line counts use
  VMI conversion; selector zero takes the default-page branch. Result: pass.
- `ESC &l#W` VFC payload:
  Evidence is `0x11f6e`, `0x12cfe`, `0x12358`, and delayed-payload docs.
  Counted payload normally loads the VFC table; alternate/data appends bytes.
  Result: pass.
- `ESC &l#V` VFC channel:
  Evidence is `0x1280a` and the VFC owner. Selector zero, channel hits,
  misses, wrap, and after-text recovery are separated. Result: pass.
- `ESC &l#C/#D` VMI and LPI:
  Evidence is `0xcb00`, `0xc992`, the HMI/VMI listing, and direct-control
  docs. `#C` accepts in-range 1/48-inch values; `#D` admits the ROM LPI set
  and treats zero as `12`. Result: pass.
- `ESC &l#E/#F` top/text length:
  Evidence is `0xece2`, `0xea9e`, and the command map. VMI-scaled values have
  extent rejection; text-length zero restores the default bottom. Result:
  pass.
- `ESC &l#L` perforation skip:
  Evidence is `0xee64` and direct-control docs. Selector `0` clears, selector
  `1` sets, and other selectors leave prior state. Result: pass.
- `ESC &l#H/#X` paper source/copies:
  Evidence is `0xef62`, `0xeef0`, and the command map. Paper source maps a
  selector table; copies ignore zero and clamp above `99`. Result: pass.
- `ESC &a#L/#M` margins:
  Evidence is `0xeb58`, `0xec0c`, the command map, and direct-control docs.
  Both use absolute HMI-column conversion; left/right values reject or clamp
  by page/margin limits. Result: pass.
- `ESC &a#C/#H/#R/#V` cursor position:
  Evidence is `0xf39e`, `0xf416`, `0xf560`, `0xf60a`, and direct-control
  docs. Column/row forms use HMI/VMI; decipoint forms use five packed
  subunits; the relative flag is honored. Result: pass.
- `ESC &k#H` HMI:
  Evidence is `0xca8c` and the HMI/VMI listing. The absolute
  integer/fraction pair is accepted up to `0x348` and scales by `30` packed
  subunits. `ESC &k6H!!` remains only the example stream. Result: pass.
- `ESC &k#G` line termination:
  Evidence is `0xedf8` and direct-control docs. Selector bits affect CR, LF,
  and FF follow-on behavior. Docs use a mode matrix and direct-control
  fixtures, not one stream only. Result: pass.
- `ESC &k#S` pitch mode:
  Evidence is `0xc390`, the pitch-mode handler, and font-context docs.
  ROM-confirmed selectors `0`, `2`, and `4` synthesize pitch-update records.
  Result: pass.
- `ESC &f#S` cursor stack:
  Evidence is `0xf75e` and direct-control docs. Selector `0` pushes, selector
  `1` pops, and full/empty bounds are documented. Result: pass.
- `ESC &f#Y/#X` macro ID/control:
  Evidence is `0xe112`, `0xdd08`, and the macro owner. ID is
  absolute-normalized; control selectors `0..10` have distinct macro actions.
  Result: pass.
- `ESC &p#X` transparent print data:
  Evidence is `0x11f5a`, `0x12452`, `0x12358`, and the transparent owner.
  Normal restore consumes counted bytes; alternate/data appends counted bytes.
  Result: pass.
- `ESC &d#D`, `ESC &d@`, `W/w`:
  Evidence is `0x12622..0x126e2` and the text payload/repeat listing.
  Non-`3D` `D` forms write selector `0`; `3D` writes selector `1`; `@`
  flushes; `W/w` schedule payload. Result: fixed.
- `ESC &s#C` wrap mode:
  Evidence is `0xedb0` and the wrap-mode listing. Selector `0` stores `1`,
  selector `1` clears, and other values no-op. Result: pass.
- `ESC *t#R` raster resolution:
  Evidence is `0x10808`, the raster handler listing, and the raster owner.
  Resolution is accepted only while the raster active byte is clear; mode/scale
  feed later `*b#W` output. Result: pass.
- `ESC *r#A/#B` raster start/end:
  Evidence is `0x1075a`, `0x107fa`, and the raster handler listing. Start
  seeds origin/bounds only when inactive; selector `1` changes origin source;
  end clears only the active byte. Result: pass.
- `ESC *b#W` raster transfer:
  Evidence is `0x11f82`, `0x105d0`, and the raster owner. Counted payload is
  delayed; accepted rows queue objects; clipped/beyond-extent rows drain or
  cap. Result: pass.
- `ESC *p#X/#Y` dot position:
  Evidence is `0xf48c`, `0xf692`, and direct-control docs. Whole-dot packed
  coordinates use the relative flag and shared cursor commit helpers. Result:
  pass.
- `ESC *c#A/#B/#H/#V/#G/#P` rectangle/rule:
  Evidence is `0x10898..0x10ae0`, the rectangle listing, and the rectangle
  owner. Setup writes dimensions and fill id; final `#P` maps missing/zero,
  gray, and HP-pattern selectors. Result: pass.
- `ESC *c#D/#E/#F` downloaded font control:
  Evidence is `0x15a56`, `0x15a18`, `0x16df6`, and the font-control listing.
  ID/code writers absolute-normalize; `#F` dispatches values `0..6` with guard
  behavior. Result: pass.
- `ESC (` / `ESC )` font designation:
  Evidence is `0x120be`, `0x1201e`, `0x12008`, and the font owner. Primary
  and secondary setup preserve slot, final byte, and lowercase chaining
  distinctions. Result: pass.
- `ESC (s#W` / `ESC )s#W` font payload:
  Evidence is `0x11f96`, `0x15d0a`, `0x16c14`, and the downloaded-font owner.
  Count zero schedules descriptor/current-record path; nonzero schedules the
  payload path; alternate/data appends. Result: pass.

## Documentation Fixes From This Audit

- [pcl-command-map.md](pcl-command-map.md): the pending-span top-level
  paragraph now describes `ESC &d#D` selector domain before using
  `ESC &d3D ! ESC &d@` as the alternate-offset example stream.
- [direct-control-codes.md](direct-control-codes.md),
  [pcl4-language.md](pcl4-language.md),
  [semantic-state-model.md](semantic-state-model.md),
  [firmware-dataflow-model.md](firmware-dataflow-model.md), and
  [end-to-end-reproduction-map.md](end-to-end-reproduction-map.md) already
  carry the same underline selector correction from the previous pass.

## Residual Rule

Future command-family docs should phrase claims as `ESC family + parameter
domain + distinguished cases + shared helper/exit`, then use fixture streams
only as evidence examples. A fixture stream is not allowed to be the semantic
subject when sibling parameters reach the same handler or shared output path.
