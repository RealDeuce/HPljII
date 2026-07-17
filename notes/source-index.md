# Source Index

## Owner Summary

This note owns the local source-document inventory and the evidence policy for
manual/PDF material. It is not a command-behavior owner: ROM behavior must
still be proven by dumped ROM bytes, disassembly, decoded tables,
cross-references, RAM field writers/readers, and checked-in owner notes.

Use these sources as follows:

- The LaserJet Series II Technical Reference Manual is authoritative for
  published PCL syntax, units, logical page terminology, documented user
  behavior, memory-use estimates, and manual command names.
- The LaserJet II / III service manual is authoritative for documented
  hardware assemblies, connector names, control-panel procedures, diagnostic
  messages, service labels, and physical signal descriptions.
- Data sheets are supporting evidence for product identity, memory options,
  interfaces, and high-level specifications.
- LaserJet III material is compatibility context only unless the Series II ROM
  disassembly or Series II service text ties it to a 33440-visible behavior.

Evidence boundary:

- Manual syntax can name a command family, but it does not prove the ROM
  parser route, handler address, RAM field write, page-object shape, render
  helper, or pixel output. Those claims belong to the firmware notes.
- Service-manual hardware labels can name physical signals or assemblies, but
  they do not prove which MMIO bit or wait-object transition the ROM is using
  unless the disassembly-backed owner note reaches that register or field.
- OCR or extracted-text tables are search aids. Verify ambiguous command
  bytes, signal names, dimensions, and message text against the PDF image or
  ROM evidence before promoting them into a semantic owner note.

Evidence audit result:

- This source index is not a behavioral proof for parser, page-object, or
  pixel claims. A semantic claim is documented only when a checked-in firmware
  owner cites ROM bytes, handler addresses, focused disassembly, decoded
  tables, RAM fields, static cross-references, or resource bytes for that
  claim.
- Generated reports and fixture outputs are supporting evidence. They can
  prove that a branch driver reaches the documented ROM state or that a helper
  transcription is internally consistent, but they do not replace an owner note
  that explains what the ROM instructions do.
- Manual and service sources may close naming or physical-label boundaries
  only after the ROM owner note has already reached the relevant command,
  field, register, status bit, connector signal, or panel message. If that
  ROM-local route is missing, the work belongs in the firmware owner note
  before this source index can be used for labels.
- Exact unresolved evidence gaps remain in
  [unresolved-boundaries.md](unresolved-boundaries.md), not in the source
  inventory. When a missing PDF, board, resource, or physical-correlation item
  is needed, the owning boundary entry must name the address, range, field, or
  physical identity that the source would close.

## Local PDFs

### `33440-90905_HP_LaserJet_series_II_Technical_Reference_Manual_Aug1989.pdf`

HP LaserJet Series II Technical Reference Manual, part number
33440-90905. This is the main source for PCL4 behavior, printer command
syntax, command tables, programming hints, memory-use estimates, and
interface appendices.

High-value sections:

- Chapter 1: PCL architecture and escape sequence syntax.
- Chapter 2: logical page, printable area, coordinate units.
- Chapter 3: print environments, defaults, resets.
- Chapters 4-12: PCL commands by feature area.
- Chapter 13: programming hints, memory use, common errors.
- Appendix A: character sets and printer command tables.
- Appendix B: Centronics, RS-232C, and RS-422 interfaces.

### `hplaserjetclassicsiiiii.pdf`

LaserJet II / III Combined Service Manual, HP part number 33449-90906,
first edition February 1990. This is the main source for hardware,
formatter/DC controller architecture, control panel behavior,
diagnostics, error messages, service mode, parts, wiring, and signal
tables.

High-value sections:

- Chapter 1: features, memory capacities, component overview,
  control-panel overview.
- Chapter 3: installation, control panel, menus, NVRAM defaults, self
  tests, service mode.
- Chapter 5: theory of operation, formatter/interface PCA, DC
  Controller, engine systems, power.
- Chapter 7: troubleshooting, message table, sensor checks, DC
  Controller signal listing and timing.
- Appendix D: cabling diagrams and interface pinouts.
- Appendix E/C: memory expansion installation and associated messages.

### `5843739.pdf`

HP LaserJet Series II Desktop Office Printer Data Sheet. Useful for
concise product specs and accessory part numbers.

High-value facts:

- HP 33440A, 300 dpi, up to 8 pages/minute.
- 512 KB installed RAM, about 395 KB standard user memory.
- Memory boards: 33443A 1 MB, 33444A 2 MB, 33445A 4 MB.
- Interfaces: Centronics parallel and RS-232C/RS-422 serial.
- Paper tray: 200 sheets input, 100 sheets top output, 20 sheets face-up
  rear output.

### `92286PC.pdf`

HP ProCollection Font Cartridge manual for product `92286PC`. This local
reference supplies the ProCollection's published font table, product naming,
and family compatibility statement. The manual is a catalog source, not proof
of cartridge ROM contents or firmware resource-selection behavior. The
separately verified physical ROM dump and extracted inventory are documented
in [rom-dump-manifest.md](rom-dump-manifest.md#92286pc-procollection-cartridge)
and
[font-cartridge-catalog.md](font-cartridge-catalog.md) for the broader bitmap
cartridge index and its evidence boundary.

### `manualsplus_06859.pdf`

LaserJet III User's Manual archive. Mostly HP 33449/PCL5, but useful for
compatibility boundaries, user-visible UI behavior, memory board
messages, and appendices that overlap the II/III service manual.

Use sparingly for LaserJet II work. Treat LaserJet III-only features
such as PCL5, scalable typefaces, Resolution Enhancement, auto
font/raster rotation, page protection, localized display messages, and
expanded symbol sets as non-33440 behavior unless the service manual
says otherwise.

## Extraction Notes

- Text extraction was done with `pdftotext -layout`; OCR errors include
  `I`/`1`, `O`/`0`, and garbled table cells.
- Signal and pin tables were paraphrased into Markdown. Verify against
  PDF images before building hardware or interpreting connector
  orientation.
- The service manual combines HP 33440 and HP 33449. These notes call
  out LaserJet III-only behavior where it appears near shared material.
