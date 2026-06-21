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

The physical control panel is a separate panel assembly connected by cable, but
the control logic is on the Interface PCA. Service manual figure 5-17 shows a
`Panel interface` block on the Interface PCA connected to the external `Control
panel`.

The Interface PCA generates the display data and supplies the control-panel
voltages. A blank display points first at service-mode state, control panel,
control-panel cable, or Interface PCA.

## Keys

- `ON LINE`
  - Short press: Toggle online/offline. Required online to receive data; offline
    to use
    most
    panel functions.
  - Hold behavior: Used during cold reset when held at power-on.
- `CONTINUE/RESET`
  - Short press: Clear most recoverable errors, resume printing, override manual
    feed/media
    requests.
  - Hold behavior: Hold until `07 RESET`; resets to panel Printing Menu settings
    and
    clears
    temporary soft fonts, temporary macros, and stored page data.
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
  - Short press: Save current menu selection; asterisk marks saved choice.
  - Hold behavior: Hold until `09 MENU RESET`; restores Printing Menu factory
    defaults
    and
    clears temporary fonts/macros/page data.
- `+` / `-`
  - Short press: Step through choices.
  - Hold behavior: Hold to scroll.

## LED Semantics

- `ON LINE`: lit when ready to receive host data. While printing, taking the
  printer offline may be delayed until paper motion finishes; host data transfer
  stops when key is pressed.
- `FORM FEED`: lit when page data is stored; flashes while stored data is being
  printed.
- `READY`: lit when ready; flashes while receiving or processing data; off when
  an error/status/attendance message is displayed.
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

HP 33449 differs: default I/O is parallel, symbol set is in Printing Menu, and
it adds RET/page-protection/language features.

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

User defaults are set from the control panel and retained across power-off.
LaserJet II user-selectable PCL defaults:

- Number of copies.
- Paper source.
- Font source/font number.
- Form length.

Modified print environment is current runtime PCL state. Software commands
change this state until another command or reset. Current cursor position and
cursor stack are not part of the modified print environment.

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

- Restores Printing Menu and I/O Configuration Menu items to factory defaults.
- Does not reset page count.
- Does not reset envelope cassette size.
- HP 33449 also preserves display language.
- After reset, verify I/O settings before placing the printer online.

## Envelope Tray State

When an envelope tray is inserted, HP 33440 displays `ENVELOPE=[size]`. Choices
are:

- `COM10`
- `MONARC`
- `C5`
- `DL`

This setting is independent of normal Printing Menu media selection and is
retained. The service manual states cold reset does not change the envelope tray
size setting.

## NVRAM

HP 33440 Interface PCA NVRAM:

- Capacity: 32 bytes.
- Stores panel setup/configuration and page count.
- Page count is accurate while powered.
- On power-off, page count is rounded down to nearest 10 and stored.
- Service mode can edit page count after Interface PCA replacement.

NVRAM-related messages:

- `68 SERVICE`: NVRAM failure; panel values revert to factory defaults; printer
  can continue until PCA replacement.
- HP 33449 also has `68 ERROR` recoverable NVRAM reset and `68 READY/SERVICE`;
  these are not necessarily HP 33440 behavior.

## Self Tests

### Power-On / `05 SELF TEST`

Runs at power-on and when `PRINT FONTS/TEST` is held about 2-5 seconds. Checks:

- Program ROM.
- Internal font ROM.
- Interface/Formatter RAM and optional RAM.
- DRAM controller.
- Interface/Formatter logic.
- LEDs.

Power-on runs only the non-printing part. A panel-requested self test prints
information and pattern pages.

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

Continuous self-test printing. Useful for paper path stress. Stop with `ON
LINE`, `PRINT FONTS/TEST`, or `CONTINUE/RESET`. Several pages may continue while
buffers clear.

### `15 ENGINE TEST`

Activated with the physical test print button. Prints vertical lines and
bypasses the Interface PCA. Verifies DC Controller circuitry and engine
components.

## Service Mode

Entry:

1. Hold `ON LINE`, `CONTINUE/RESET`, and `ENTER/RESET MENU` while powering on
   for at least one second.
2. Display is blank and all four LEDs illuminate if selected.
3. Press `CONTINUE/RESET` once.
4. Press `ENTER/RESET MENU`.
5. Display reads `SERVICE MODE`.

Uses:

- Print service-mode self-test patterns.
- Run continuous service-mode self tests.
- Display and set page count in NVRAM.

Exit with `ON LINE` or `CONTINUE/RESET`; HP 33440 may require another `ON LINE`
press to return online.

## Emulator Takeaways

- The control panel is not just UI. It persists defaults and triggers meaningful
  firmware paths.
- Model NVRAM early, even if backed by a simple byte array.
- Implement all reset types distinctly; ROM code and PCL behavior depend on
  differences between `ESC E`, `07 RESET`, `09 MENU RESET`, and cold reset.
- Self-test paths are likely the best first ROM milestones because they exercise
  ROM checksum, RAM sizing, NVRAM, LEDs/display, and print-engine command paths
  without host PCL input.
