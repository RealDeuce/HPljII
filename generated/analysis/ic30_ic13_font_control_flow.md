# IC30/IC13 Font ID and Font-Control Flow

Generated from the verified firmware image and focused disassembly around
`0x15a18`, `0x15a56`, `0x11f96`, `0x16df6`, and the immediate font-control
targets. This is the host-command edge for downloaded-font bookkeeping: `ESC
*c#D` selects the current font id, `ESC *c#E` selects the current
character/code word, `ESC )s#W` / `ESC (s#W` schedules the binary payload
consumer, and `ESC *c#F` dispatches control values that delete, mark, unmark,
or refresh current downloaded-font records.

## Font and Character Selection

| Handler | Firmware behavior | Reproduction meaning |
| --- | --- | --- |
| `0x15a56` (`ESC *c#D`) | rewinds parser record cursor `0x78299e` by six bytes, reads the parsed signed word at `+2`, stores its absolute value in `0x782f2e`, and maps `-32768` to `0x7fff` | subsequent downloaded-font control and payload commands operate on this normalized current font id |
| `0x15a18` (`ESC *c#E`) | rewinds parser record cursor `0x78299e` by six bytes, reads the parsed signed word at `+2`, stores its absolute value in `0x782f30`, and maps `-32768` to `0x7fff` | later `ESC )s#W` character payloads and `ESC *c3F` cleanup select the same character/code word |

## Font Payload Selector

| Handler | Firmware behavior | Reproduction meaning |
| --- | --- | --- |
| `0x11f96` (`ESC )s#W` / `ESC (s#W`) | inspects the parsed byte-count parameter from the six-byte record: count `0` schedules delayed handler `0x15d0a`, and any nonzero count schedules delayed handler `0x16c14` through `0x121cc` | zero-length `W` enters the descriptor/setup path; nonzero `W` enters downloaded font/character payload installation |
| `0x15d0a` | stores the absolute parsed count in `0x783140`, rejects counts below `3` or parser mode `2`, reads descriptor byte `0` through `0x169f6` which accepts only value `4`, then reads selector byte `1` through `0x16a10` where zero returns status `1` and nonzero returns status `2` | zero-length `W` is a descriptor packet, not a no-op; byte `4` is the accepted descriptor kind and byte `1` chooses current-record versus continuation handling |
| `0x15d0a` status `1` branch | scans current downloaded-font records through `0x172c0`; an existing current record is looked up through `0x1b4c0`, and object flag bit 30 selects `0x16498` when set or `0x16606` when clear | descriptor bytes following `ESC )s0W` can install a downloaded-character object or a downloaded-font-resource object for the current font id |
| `0x15d0a` status `2` branch | requires continuation flag `0x7827c6 == 1`, looks up saved payload `0x7827da` through `0x1b4c0`, and object flag bit 30 selects resume helper `0x15b9a` when set or `0x15c4c` when clear | nonzero selector bytes resume an interrupted descriptor/payload copy instead of allocating from the current record table |
| `0x16c14` | stores the absolute parsed count in `0x783140`, scans or allocates the current downloaded-font record slot, and either skips that many payload bytes or installs the allocated payload pointer | nonzero `ESC )s#W` payload bytes become the current font resource or character object used by later text rendering |

## Font-Control Jump Table

The table at `0x016db6` is decoded as `(target_long, value_long)` pairs
terminated by target `0`; the terminal value is the default target `0x016eaa`.

| `ESC *c#F` value | Target | Immediate ROM effect |
| ---: | ---: | --- |
| `0` | `0x016e16` | if `0x782a92 != 2`, calls `0x179da(1)`, which walks 32 records under `0x782640` and calls `0x187fe` for each record id |
| `1` | `0x016e34` | if `0x782a92 != 2`, calls `0x179da(0)`, the same all-record walk with the alternate `0x187fe` argument |
| `2` | `0x016e4c` | if `0x782a92 != 2`, calls `0x187fe(1)` for the current `0x782f2e` font id |
| `3` | `0x016e68` | if `0x782a92 != 2`, calls `0x17b5c`; that helper uses current font id `0x782f2e` plus character/code word `0x782f30` to clear or replace one glyph record |
| `4` | `0x016e7e` | calls `0x17150`; if the current record exists and bit 6 is set, clears bit 6 and moves one count from `0x782786` back to `0x782782` |
| `5` | `0x016e86` | calls `0x17108`; if the current record exists and bit 6 is clear, sets bit 6 and moves one count from `0x782782` to `0x782786` |
| `6` | `0x016e8e` | if `0x782a92 != 2`, calls `0x18180` and then `0x1b04c` for active/current font-resource housekeeping |
| other | `0x016eaa` | no-op return |

## Related Routines

| Routine | Role | Absolute JSR references |
| ---: | --- | --- |
| `0x015a56` | `ESC *c#D` assign-font-id handler | (none) |
| `0x015a18` | `ESC *c#E` character-code handler | (none) |
| `0x011f96` | `ESC )s#W` / `ESC (s#W` delayed font payload selector | (none) |
| `0x015d0a` | zero-count font/download descriptor delayed-payload handler | (none) |
| `0x0169f6` | descriptor kind validator for byte `4` | `0x015d5e` |
| `0x016a10` | descriptor selector mapper: zero -> status 1, nonzero -> status 2 | `0x015d74` |
| `0x016df6` | `ESC *c#F` font-control dispatcher | (none) |
| `0x0179da` | all-record font-control walker | `0x016e28`, `0x016e44`, `0x01bbac` |
| `0x0187fe` | current-record release/delete wrapper | `0x016e5e`, `0x017a06` |
| `0x017b5c` | current character/glyph record clear helper | `0x016e76` |
| `0x017108` | mark current downloaded record | `0x016e86` |
| `0x017150` | unmark current downloaded record | `0x016e7e` |
| `0x018180` | active/current font-resource housekeeping helper | `0x016e9c` |
| `0x016c14` | downloaded font/resource payload add command | (none) |

## State References

| Address | Current role | Longword literal references |
| ---: | --- | --- |
| `0x0078299e` | parser record cursor rewound by font/download handlers before reading the parsed parameter | `0x002f18`, `0x00c39a`, `0x00c3ca`, `0x00c3d0`, `0x00c3e4`, `0x00c3f4`, `0x00c58a`, `0x00c592`, `0x00c6f6`, `0x00c6fe`, `0x00c78a`, `0x00c792`, ... (146 total) |
| `0x00782f2e` | current font id written by `ESC *c#D` and consumed by font-control helpers | `0x015a88`, `0x016d74`, `0x0172e2`, `0x017716`, `0x017720`, `0x01778e`, `0x0179ee`, `0x017a00`, `0x017a18`, `0x01837e`, `0x01bbb4` |
| `0x00782f30` | current character/code word written by `ESC *c#E` and consumed by character payload/control helpers | `0x015a4a`, `0x0164ea`, `0x0165f0`, `0x016658`, `0x0167f6`, `0x017ba8`, `0x01bbba` |
| `0x00782a92` | mode/status byte that suppresses font-control values 0, 1, 2, 3, and 6 when it equals `2` | `0x006608`, `0x00660e`, `0x0066ba`, `0x00ded2`, `0x00dede`, `0x00def6`, `0x00dfd6`, `0x00e178`, `0x00e3fe`, `0x00fc5c`, `0x00fc68`, `0x00fe3c`, ... (26 total) |
| `0x00782640` | start of 32 current downloaded-font records, 10 bytes each | `0x0170e0`, `0x0172c6`, `0x017306`, `0x017908`, `0x0179e8`, `0x01d508` |
| `0x00782782` | unmarked/current downloaded-font count adjusted by `0x17108` and `0x17150` | `0x016da8`, `0x017142`, `0x01718e`, `0x01847a`, `0x018938`, `0x01896e` |
| `0x00782786` | marked/current downloaded-font count adjusted opposite `0x782782` | `0x017148`, `0x017194`, `0x018976`, `0x0189ce` |
| `0x00783140` | download payload byte budget used by `0x16c14` and lower payload readers | `0x01599e`, `0x0159ac`, `0x0159b8`, `0x0159c6`, `0x015d26`, `0x015d2e`, `0x015d36`, `0x015d40`, `0x015dce`, `0x015f18`, `0x0163b0`, `0x016548`, ... (21 total) |

## Current Reproduction Contract

- A byte-stream reproduction must preserve the global current font id at
  `0x782f2e` and current character/code word at `0x782f30`; `ESC *c#D` and
  `ESC *c#E` normalization happen before `ESC *c#F`, `ESC (#X` / `ESC )#X`,
  and downloaded payload installation consult current records. The harness now
  ties parser-derived current id `0x1234` and current character `0x25` from
  `ESC *c4660d37e5F` into the following descriptor route and character payload
  fixtures.
- `ESC )s0W` / `ESC (s0W` are not ordinary zero-byte skips: `0x11f96`
  schedules descriptor handler `0x15d0a`; the harness now ties the `ESC )s0W`
  parser trace to restored handler `0x15d0a`, descriptor offset/budget,
  selector-zero routing through the current downloaded-font record, and
  selector-nonzero continuation routing through saved payload `0x7827da`.
- Nonzero `W` counts schedule `0x16c14`; the harness now traces `ESC )s80W`
  through ROM parser table `0x11774` to restored handler `0x16c14`, payload
  offset/length, `0x16fae` validation, `0x17026`/`0x1719c` allocation, and
  `0x1bc38` candidate insertion for a font-resource payload. It also ties the
  full `ESC )s2193W` parser trace to restored handler `0x16c14`, payload
  offset/length, the `0x16498` downloaded character-object allocation,
  `0x16874`/`0x16942` payload copy, and the rendered `0x1f264` segmented-wide
  row. `0x15d0a` reaches the same character-object path only after the
  descriptor branch resolves an existing object whose flag bit 30 is set.
- Font-control values `0`, `1`, `2`, `3`, and `6` are suppressed when
  `0x782a92 == 2`; values `4` and `5` still run the downloaded-record
  mark/unmark helpers.
- The concrete font-resource payload-install path is now pinned from `ESC
  )s80W` through `0x16c14` -> `0x16fae` -> `0x17026` -> `0x1719c` ->
  `0x1bc38`, while character payload installation reaches the `0x16498` object
  path; this report now names the PCL command edge that selects which current
  downloaded-font records and character objects those lower helpers mutate.
