# Control Panel, NVRAM, Resets, and Self Tests

Sources: `hplaserjetclassicsiiiii.pdf` ch. 1 section 1-7, ch. 3 sections 3-3
through 3-7; `33440-90905...pdf` ch. 3.

## Hardware

The HP 33440 control panel has:

- One-line 16-character LCD.
- Eight keys.
- LEDs:
  - Green `READY`.
  - Amber `ON LINE`.
  - Amber `FORM FEED`.
  - Amber `MANUAL`.

The physical control panel is a separate panel assembly connected by
cable, but the control logic is on the Interface PCA. Service manual
figure 5-17 shows a `Panel interface` block on the Interface PCA
connected to the external `Control panel`.

The Interface PCA generates the display data and supplies the
control-panel voltages. A blank display points first at service-mode
state, control panel, control-panel cable, or Interface PCA.

## Keys

- `ON LINE`
  - Short press: Toggle online/offline. Required online to receive data;
    offline
    to use
    most
    panel functions.
  - Hold behavior: Used during cold reset when held at power-on.
- `CONTINUE/RESET`
  - Short press: Clear most recoverable errors, resume printing,
    override manual
    feed/media
    requests.
  - Hold behavior: Hold until `07 RESET`; resets to panel Printing Menu
    settings and clears temporary soft fonts, temporary macros, and
    stored page data.
- `PRINT FONTS/TEST`
  - Short press: Print font samples from available fonts.
  - Hold behavior: Hold to `05 SELF TEST`; hold longer to `04 SELF TEST`
    continuous
    mode.
- `FORM FEED`
  - Short press: Print stored page-buffer data when offline and ready.
  - Hold behavior: None noted.
- `MENU`
  - Short press: Enter Printing Menu and step through items.
  - Hold behavior: Hold about 5 seconds to enter Configuration Menu.
- `ENTER/RESET MENU`
  - Short press: Save current menu selection; asterisk marks saved
    choice.
  - Hold behavior: Hold until `09 MENU RESET`; restores Printing Menu
    factory defaults and clears temporary fonts/macros/page data.
- `+` / `-`
  - Short press: Step through choices.
  - Hold behavior: Hold to scroll.

## LED Semantics

- `ON LINE`: lit when ready to receive host data. While printing, taking
  the printer offline may be delayed until paper motion finishes; host
  data transfer stops when key is pressed.
- `FORM FEED`: lit when page data is stored; flashes while stored data
  is being printed.
- `READY`: lit when ready; flashes while receiving or processing data;
  off when an error/status/attendance message is displayed.
- `MANUAL`: lit when manual feed was selected by panel or software.

## Menus

Printing Menu contains page/job defaults that software can override:

- Copies.
- Manual feed.
- Font source.
- Font number.
- Form length / lines per page.

HP 33440 Configuration Menu contains:

- Symbol set.
- Auto Continue.
- Interface parameters:
  - `I/O=SERIAL` or `I/O=PARALLEL`; HP 33440 factory default is serial.
  - `BAUDRATE=9600` default when serial.
  - `ROBUST XON=ON` default.
  - `DTR POLARITY=HI` default.

HP 33449 differs: default I/O is parallel, symbol set is in Printing
Menu, and it adds RET/page-protection/language features.

## Factory Defaults - HP 33440

From service manual table 3-1 and Technical Reference ch. 3:

| Feature | HP 33440 default |
| --- | --- |
| Copies | 1 |
| Font source | Internal |
| Font number | 0 |
| Form length | 60 lines |
| Symbol set | Roman-8 |
| Auto Continue | Off |
| I/O | Serial |
| Baud rate | 9600 |
| Robust XON | On |
| DTR polarity | High |
| Paper feed | Installed tray |
| Orientation | Portrait |
| Page size | Installed paper tray size |
| VMI | 8 increments = 6 lpi |
| HMI | 12 increments = 10 cpi |
| Top margin | 1/2 inch = 150 dots |
| Text length | paper length minus 1/2 inch top and bottom margins |
| Perforation skip | On |
| Line termination | CR=CR, LF=LF, FF=FF |
| Raster graphics resolution | 75 dpi |
| End-of-line wrap | Off |
| Display functions | Off |

Default font:

- Orientation: portrait.
- Symbol set: Roman-8.
- Spacing: fixed.
- Pitch: 10 cpi.
- Height: 12 point.
- Style: upright.
- Stroke weight: medium.
- Typeface: Courier.
- Underline: off.

## User Defaults and Modified Environment

User defaults are set from the control panel and retained across
power-off. LaserJet II user-selectable PCL defaults:

- Number of copies.
- Paper source.
- Font source/font number.
- Form length.

Modified print environment is current runtime PCL state. Software
commands change this state until another command or reset. Current
cursor position and cursor stack are not part of the modified print
environment.

## ROM Panel-Default Record Path

The manual "user defaults" above are backed in ROM state by compact default
records. This path matters for rendering because software reset consumes the
canonical defaults produced here before rebuilding page geometry, copy count,
paper-source defaults, and VMI.

Entry and dispatch:

- `0xa3ca` is the immediate panel/service byte source found in the ROM. It
  reads `$8000.w & 0xff`, waits through `0x8bea(0x14)`, rereads the same
  hardware word, and loops until the two samples match.
- Service dispatcher `0x3dae` uses `0x7821aa` as the last-byte gate and reaches
  the default-store family through table entries including `0xef -> 0x3ef8`,
  `0xfd -> 0x3f6a`, and `0xbf -> 0x4922`.
- Menu commit handler `0x4922` checks service/menu latches `0x7821b2`,
  `0x780e2d.3`, `0x7822dc`, and progress byte `0x782272`. When
  `0x782272.4` is set it calls default updater `0x4fb0` directly. Otherwise
  it stages the current selection through the handler table rooted at
  `0x782274 + 0x12`, advances selector index `0x782278`, copies staged value
  `0x782280 + 4*index` into `0x78227c`, and clears `0x782272` after index
  `0x14`.
- If no staged progress is active, `0x4922` waits for the debounced input byte
  to remain equal to `0x7821aa` for timer delta `0x2a`, sets temporary flag
  `0x7822d4`, calls `0x4162`, clears `0x7822d4` / `0x7822dc`, and sets
  `0x780e6a = 1`.

Default-record model:

- Active default bank selector `0x7822d5` is scaled through
  `0x332ee(selector, 3)`. The selected backing record base is
  `0x780eda + 2 * scaled_selector`.
- Loader `0x5e80` copies the selected record into runtime defaults. Record
  byte `+0` becomes staged byte `0x782280` and canonical default
  `0x78219d`. Record byte `+5` bit 2 becomes staged long `0x782284` and
  canonical byte `0x7821a2`, with value `0x80` when set and `0` when clear.
  Record word `+2` becomes staged line-spacing value `0x782290` and canonical
  word `0x78219e`.
- The same loader derives byte `0x7821a3 = 0x87 + (record byte +4 low
  nibble)`, mirrors it to `0x780e97`, and sets `0x780e55 = 2`.
- Active-record validator `0x56c2` scans word-2 entries at
  `0x780eda + 2*D5` for `D5 = 2, 5, 8, ...` until it finds bit 15 set. It
  writes the corresponding compact bank number to `0x7822d5`. If no active
  record is found after `D5 > 8`, it calls `0x1284(0xe2, 0x21)`, which selects
  string `0xb44b` (`67 SERVICE`) in the generated string table.

Menu/default writers:

- `0x4fb0` compares current candidate `0x78227c` against staged table entry
  `0x782280 + 4*0x782278`. Selector `2` also compares `0x78219b`, selector
  `3` compares `0x78219c`, and selector `4` converts the candidate through
  `0xcf52` before comparing with `0x78219e`. On change it writes the staged
  table entry, calls `0x56c2`, dispatches the selected update handler from
  `0x782274 + 0x12`, and calls maintenance helper `0x571e`.
- Update handler `0x5060` writes selected-record byte `+0`, mirrors it to
  `0x78219d`, and marks dirty word `0x780eba + 2*scaled_selector`.
- Update handler `0x50be` rewrites selected-record byte `+5` bit 2 from
  `0x782284`, mirrors the bit as `0x7821a2 = 0x80` or `0`, and marks dirty
  word `0x780ebe + 2*scaled_selector`.
- Update handler `0x52ba` converts staged line-spacing value `0x782290`
  through `0xcf52`, writes selected-record word `+2`, mirrors it to
  `0x78219e`, and marks dirty word `0x780ebc + 2*scaled_selector`.

Retained-record maintenance:

- Startup helper `0x5a16` forces all 16 dirty/read-mask words
  `0x780eba..0x780ed8` to `1`, calls read helper `0x97e4`, and then clears
  all 16 flags. This bulk-load path has no explicit success return inspected
  by its caller.
- Commit helper `0x96c4` writes only dirty retained words. It sends command
  byte `0x84`, then for each dirty index sends
  `((index << 3) | 0x83) << 16 | word`, sends `0x81`, delays, sends `0x80`,
  snapshots the written image, calls `0x97e4` for readback, restores the write
  image, and compares dirty readback words against the pre-read snapshot.
- Read helper `0x97e4` sends command byte `0x85`, then for each dirty/read-mask
  index sends command class `0x86` and shifts `$8c01.1` into the corresponding
  `0x780eda` word.
- Serial helper `0x9a4a` changes the low three bits of shadow `0x7828f6` and
  writes the result to `$a400`. Observed retained-storage callers use phase
  pair `1 -> 3` for zero bits, `5 -> 7` for one bits, and `1 -> 0` for
  deassert.
- Maintenance helper `0x571e` clears dirty flags, copies three-word record
  groups between active banks, advances `0x7822d5`, updates packed maintenance
  counter `0x780ef0`, clears auxiliary flags `0x780eb8`, and retries
  `0x96c4`. Exhausted commit retries call `0x9bee(0x780e36, 0x00000008)`,
  which sets bit 3 of byte `0x780e39`; the service/status path consumes that
  bit as the `68 SERVICE` condition.
- Helper `0x5a62` clears all 16 backing records and marks all dirty flags when
  the service byte is `0xde`. Otherwise it reloads records from ROM fallback
  tables `0xba3e` and `0xba44`, then calls `0x571e`.

Field classes:

- Canonical state:
  selected default bank `0x7822d5`, backing records `0x780eda..`, canonical
  defaults `0x78219d`, `0x78219e`, and `0x7821a2`, and active/default bytes
  `0x78219b`, `0x78219c`, `0x7821a0`, `0x7821a3`, and `0x780e97`.
- Derived/cache state:
  staged menu values `0x782280`, `0x782284`, `0x782288`, `0x78228c`,
  `0x782290`, `0x782294`, and `0x782298`, plus maintenance counter
  `0x780ef0`.
- Parser/service scratch:
  last panel byte `0x7821aa`, progress byte `0x782272`, handler-table pointer
  `0x782274`, selector index `0x782278`, current candidate `0x78227c`, and
  temporary commit flag `0x7822d4`.
- Firmware bookkeeping:
  dirty/read-mask flags `0x780eba..0x780ed8`, auxiliary flags
  `0x780eb8`, status bytes `0x780e36..0x780e39`, serial shadow
  `0x7828f6`, and menu/service latches `0x7821b2`, `0x7822dc`, and
  `0x780e6a`.
- Hardware/external:
  service/panel byte source `$8000.w`, retained-storage output/control
  register `$a400`, and retained-storage input/status register `$8c01`.
- Unknown:
  the ROM identifies the immediate registers and software protocol above, but
  not the external panel protocol behind `$8000.w` or the physical retained
  storage device and pins behind `$a400` / `$8c01`.

Output effect:

- These handlers do not draw pixels directly. Their output effect is default
  state: `ESC E` reset consumes `0x78219d`, `0x78219e`, and `0x7821a2`
  through `0xcda2`; paper-source handler `0xef62` can consume `0x7821a2` as a
  default fallback; later page, text, and raster handlers consume the rebuilt
  VMI, paper/default byte, copy count, and environment fields. For a renderer
  that starts from canonical defaults, the backing records are provenance. For
  a renderer that models panel reset, cold reset, or power-cycle behavior, the
  backing records, dirty flags, retained-storage serial path, and fallback
  tables become part of the initial page environment.

Evidence:

- `generated/disasm/ic30_ic13_panel_service_byte_source_00a39a.lst`
- `generated/disasm/ic30_ic13_panel_service_dispatch_003dae.lst`
- `generated/disasm/ic30_ic13_panel_menu_commit_004922.lst`
- `generated/disasm/ic30_ic13_default_env_menu_update_004fb0.lst`
- `generated/disasm/ic30_ic13_default_env_record_maintenance_0056c2.lst`
- `generated/disasm/ic30_ic13_default_env_load_005e80.lst`
- `generated/disasm/ic30_ic13_retained_record_bulk_load_005a16.lst`
- `generated/disasm/ic30_ic13_nvram_default_record_commit_0096c4.lst`
- `generated/disasm/ic30_ic13_nvram_serial_bit_helpers_009860.lst`
- Reset consumers are documented in
  [reset-default-environment.md](reset-default-environment.md).

## Reset Types

### Software Reset: `ESC E`

- Restores the user default environment.
- Deletes temporary fonts and temporary macros.
- Prints any partial pages received.
- HP recommends sending it at beginning and end of each job.

### Control Panel `07 RESET`

- Restores current printing settings to control-panel settings.
- Clears temporary soft fonts, temporary macros, and stored page data.
- Discards formatted pages not yet printed.

### `09 MENU RESET`

- Restores Printing Menu items to factory defaults.
- Clears temporary soft fonts, temporary macros, and stored page data.
- Does not reset all Configuration Menu state.

### `08 COLD RESET`

Performed by holding `ON LINE` while powering on.

- Restores Printing Menu and I/O Configuration Menu items to factory
  defaults.
- Does not reset page count.
- Does not reset envelope cassette size.
- HP 33449 also preserves display language.
- After reset, verify I/O settings before placing the printer online.

## Envelope Tray State

When an envelope tray is inserted, HP 33440 displays `ENVELOPE=[size]`.
Choices are:

- `COM10`
- `MONARC`
- `C5`
- `DL`

This setting is independent of normal Printing Menu media selection and
is retained. The service manual states cold reset does not change the
envelope tray size setting.

## NVRAM

HP 33440 Interface PCA NVRAM:

- Capacity: 32 bytes.
- Stores panel setup/configuration and page count.
- Page count is accurate while powered.
- On power-off, page count is rounded down to nearest 10 and stored.
- Service mode can edit page count after Interface PCA replacement.

NVRAM-related messages:

- `68 SERVICE`: NVRAM failure; panel values revert to factory defaults;
  printer can continue until PCA replacement.
- HP 33449 also has `68 ERROR` recoverable NVRAM reset and
  `68 READY/SERVICE`; these are not necessarily HP 33440 behavior.

## Self Tests

### Power-On / `05 SELF TEST`

Runs at power-on and when `PRINT FONTS/TEST` is held about 2-5 seconds.
Checks:

- Program ROM.
- Internal font ROM.
- Interface/Formatter RAM and optional RAM.
- DRAM controller.
- Interface/Formatter logic.
- LEDs.

Power-on runs only the non-printing part. A panel-requested self test
prints information and pattern pages.

HP 33440 printed self-test information:

- Page count.
- Program ROM date code.
- Internal font ROM date code.
- Auto Continue setting.
- Installed memory.
- Selected symbol set.
- Printing Menu selections.
- Configuration Menu selections.
- Ripple print pattern for print quality/density checks.

The HP 33440 self-test page is described as about 12 percent coverage.

### `04 SELF TEST`

Continuous self-test printing. Useful for paper path stress. Stop with
`ON LINE`, `PRINT FONTS/TEST`, or `CONTINUE/RESET`. Several pages may
continue while buffers clear.

### `15 ENGINE TEST`

Activated with the physical test print button. Prints vertical lines and
bypasses the Interface PCA. Verifies DC Controller circuitry and engine
components.

## Service Mode

Entry:

1. Hold `ON LINE`, `CONTINUE/RESET`, and `ENTER/RESET MENU` while
   powering on for at least one second.
2. Display is blank and all four LEDs illuminate if selected.
3. Press `CONTINUE/RESET` once.
4. Press `ENTER/RESET MENU`.
5. Display reads `SERVICE MODE`.

Uses:

- Print service-mode self-test patterns.
- Run continuous service-mode self tests.
- Display and set page count in NVRAM.

Exit with `ON LINE` or `CONTINUE/RESET`; HP 33440 may require another
`ON LINE` press to return online.

## Emulator Takeaways

- The control panel is not just UI. It persists defaults and triggers
  meaningful firmware paths.
- Model NVRAM early, even if backed by a simple byte array.
- Implement all reset types distinctly; ROM code and PCL behavior depend
  on differences between `ESC E`, `07 RESET`, `09 MENU RESET`, and cold
  reset.
- Self-test paths are likely the best first ROM milestones because they
  exercise ROM checksum, RAM sizing, NVRAM, LEDs/display, and
  print-engine command paths without host PCL input.
