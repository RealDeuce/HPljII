# Errors and Status Messages

Sources: `hplaserjetclassicsiiiii.pdf` ch. 7 table 7-2; `33440-90905...pdf` ch. 13.

## Normal Status

| Message | Meaning |
| --- | --- |
| `00 READY` | Printer ready. |
| `02 WARMING UP` | Fuser/engine warmup. |
| `04 SELF TEST` | Continuous self-test printing. |
| `05 SELF TEST` | Self test in progress. |
| `06 PRINTING TEST` | Self-test page printing. |
| `06 FONT PRINTOUT` | Font sample pages printing. |
| `07 RESET` | Panel reset in progress. |
| `08 COLD RESET` | Cold reset in progress. |
| `09 MENU RESET` | Printing Menu reset in progress. |
| `10 RESET TO SAVE` | Reset needed to apply selected Printing Menu changes. |
| `15 ENGINE TEST` | Engine test pattern printing from physical test button. |

## Attendance / User Action

| Message | Meaning / action |
| --- | --- |
| `11 PAPER OUT` | Add paper to input tray. HP 33440-specific wording in service table. |
| `12 PRINTER OPEN` | Close top cover. |
| `13 PAPER JAM` | Clear paper, then continue/reset to reprint as appropriate. |
| `14 NO EP CRT` | Install EP-S cartridge. |
| `16 TONER LOW` | Replace or redistribute EP-S cartridge. |
| `PC LOAD [paper]` | Requested paper size not installed or tray is empty. |
| `PE FEED [envelope]` | Manual envelope feed requested. |
| `PF FEED [paper]` | Manual paper feed requested. |
| `ENVELOPE=[size]` | HP 33440 envelope tray inserted; select COM10, MONARC, C5, or DL. |
| `FC LEFT/RIGHT/BOTH` | Font cartridge changed while offline with buffered data. |
| `FE CARTRIDGE` | Cartridge removed while online; power off, reinsert, power on. |

For `PC LOAD [paper]`, `[paper]` can be A4, EXEC, LETTER, or LEGAL.

## Data / Page Errors

- `20 ERROR`: Memory overflow: too much font, macro, raster, or page-composition data.
  Continue prints what was received. Simplify job or add memory.
- `21 ERROR`: Page too complex for formatter/engine timing. Reduce complexity. HP 33449
  can also use page protection with extra memory.
- `22 ERROR`: Host/printer communication protocol problem. Check baud, handshake, and
  I/O settings. XON/XOFF and DTR are supported; ENQ/ACK is not.
- `40 ERROR`: Data transfer error. Common causes include powering host down while
  printer online or mismatched baud rates.
- `41 ERROR`: Temporary page error. Often beam detect related; printer attempts recovery
  and page repeat. If beam detect cannot recover for about two seconds, expect `51
  ERROR`.

## Optional I/O and Cartridge Errors

| Message | Meaning |
| --- | --- |
| `42 ERROR` | Optional I/O problem; press continue, reseat optional I/O PCA. |
| `43 ERROR` | Optional interface communication problem. |
| `69 SERVICE` | Timeout between Interface/Formatter PCA and optional I/O PCA. |
| `70 ERROR` | HP 33449 firmware cartridge not designed for printer. |
| `71 ERROR` | HP 33449 firmware cartridge not designed for printer. |
| `72 SERVICE` | HP 33449 font cartridge removed too quickly after insertion. |
| `79 SERVICE` | HP 33449 formatter error; isolate memory, cartridges, optional I/O. |

`72 SERVICE` can also indicate a bad font-cartridge connector.

## Engine Service Errors

| Message | Meaning |
| --- | --- |
| `50 SERVICE` | Fuser malfunction. Power off 10+ minutes, then troubleshoot fuser. |
| `51 ERROR` | Laser beam lost for over about two seconds / beam detect malfunction. |
| `52 ERROR` | Scanner motor unable to maintain speed. |

## Memory / Formatter Service Errors

- `53 ERROR`: HP 33440 optional memory incompatible with Interface PCA; use HP memory.
- `31 SERVICE`: Program ROM checksum error on Interface/Formatter PCA.
- `32 SERVICE`: Internal font ROM checksum error on Interface/Formatter PCA.
- `33 SERVICE`: Dynamic RAM or optional memory PCA error. Remove optional memory and
  retest.
- `54 SERVICE`: Laser scan buffer error.
- `55 SERVICE`: Dynamic RAM controller error.
- `57 SERVICE`: Miscellaneous Interface/Formatter PCA hardware or address error. Check
  cables, font cartridges, accessories; then replace PCA if persistent.
- `68 ERROR`: HP 33449 recoverable NVRAM error; settings may reset.
- `68 SERVICE`: NVRAM failure. On HP 33440/33449, operation may continue with factory
  defaults until Interface/Formatter PCA replacement.

## Formatter/DC Controller Communication

- `55 ERROR`: Communication problem between DC Controller PCA and Interface/Formatter
  PCA. Undefined status exchanged or status request unanswered. Service procedure says
  run Engine Test to verify DC Controller path, check J209 jumper and voltages, then
  replace Interface/Formatter PCA or DC Controller PCA.

Note: There is both `55 ERROR` and `55 SERVICE`; keep them distinct. `55 ERROR` is
formatter/DC communication. `55 SERVICE` is dynamic RAM controller.

## Self-Test Failure Mapping

Self-test covers:

- Program ROM -> `31 SERVICE`.
- Internal font ROM -> `32 SERVICE`.
- DRAM/optional memory -> `33 SERVICE`.
- Scan buffers -> `54 SERVICE`.
- DRAM controller -> `55 SERVICE`.
- NVRAM -> `68 SERVICE` or model-specific `68 ERROR`.

## Sensor-Related Message Sources

- Paper out / load: cassette sensor `PS301`, tray-size switches `SW201`-`SW203`.
- Manual feed: manual feed sensor `PS302`.
- Paper jam: delivery sensor `PS331`.
- Printer open: cover / +24B interlock path.
- No EP cartridge: cartridge sensitivity switches `CSENS1`/`CSENS2` both high.
- Toner low: toner sensor `TSENS`.
- Beam/scanner errors: `BD`, scanner tach `FG+`/`FG-`, scanner speed control `SCNCONT`,
  laser feedback `PD`.

## Emulator Takeaways

- Implement error codes as named engine/formatter states, not only display strings.
- `Auto Continue` affects whether recoverable errors wait indefinitely or display for
  about 10 seconds then resume.
- Many service codes map directly to hardware blocks; use them as milestones when
  reverse-engineering startup self-test branches.
- Keep HP 33449-only messages available as compatibility references but avoid exposing
  them in HP 33440 mode unless ROM behavior proves otherwise.
