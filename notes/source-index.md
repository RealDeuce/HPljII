# Source Index

## Local PDFs

### `33440-90905_HP_LaserJet_series_II_Technical_Reference_Manual_Aug1989.pdf`

HP LaserJet Series II Technical Reference Manual, part number 33440-90905. This is the main source for PCL4 behavior, printer command syntax, command tables, programming hints, memory-use estimates, and interface appendices.

High-value sections:

- Chapter 1: PCL architecture and escape sequence syntax.
- Chapter 2: logical page, printable area, coordinate units.
- Chapter 3: print environments, defaults, resets.
- Chapters 4-12: PCL commands by feature area.
- Chapter 13: programming hints, memory use, common errors.
- Appendix A: character sets and printer command tables.
- Appendix B: Centronics, RS-232C, and RS-422 interfaces.

### `hplaserjetclassicsiiiii.pdf`

LaserJet II / III Combined Service Manual, HP part number 33449-90906, first edition February 1990. This is the main source for hardware, formatter/DC controller architecture, control panel behavior, diagnostics, error messages, service mode, parts, wiring, and signal tables.

High-value sections:

- Chapter 1: features, memory capacities, component overview, control-panel overview.
- Chapter 3: installation, control panel, menus, NVRAM defaults, self tests, service mode.
- Chapter 5: theory of operation, formatter/interface PCA, DC Controller, engine systems, power.
- Chapter 7: troubleshooting, message table, sensor checks, DC Controller signal listing and timing.
- Appendix D: cabling diagrams and interface pinouts.
- Appendix E/C: memory expansion installation and associated messages.

### `5843739.pdf`

HP LaserJet Series II Desktop Office Printer Data Sheet. Useful for concise product specs and accessory part numbers.

High-value facts:

- HP 33440A, 300 dpi, up to 8 pages/minute.
- 512 KB installed RAM, about 395 KB standard user memory.
- Memory boards: 33443A 1 MB, 33444A 2 MB, 33445A 4 MB.
- Interfaces: Centronics parallel and RS-232C/RS-422 serial.
- Paper tray: 200 sheets input, 100 sheets top output, 20 sheets face-up rear output.

### `manualsplus_06859.pdf`

LaserJet III User's Manual archive. Mostly HP 33449/PCL5, but useful for compatibility boundaries, user-visible UI behavior, memory board messages, and appendices that overlap the II/III service manual.

Use sparingly for LaserJet II work. Treat LaserJet III-only features such as PCL5, scalable typefaces, Resolution Enhancement, auto font/raster rotation, page protection, localized display messages, and expanded symbol sets as non-33440 behavior unless the service manual says otherwise.

## Extraction Notes

- Text extraction was done with `pdftotext -layout`; OCR errors include `I`/`1`, `O`/`0`, and garbled table cells.
- Signal and pin tables were paraphrased into Markdown. Verify against PDF images before building hardware or interpreting connector orientation.
- The service manual combines HP 33440 and HP 33449. These notes call out LaserJet III-only behavior where it appears near shared material.
