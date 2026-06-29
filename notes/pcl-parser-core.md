# PCL Parser Core Firmware

This note documents the core parser path after [host-byte-fetch.md](host-byte-fetch.md):
bytes from `0xa904` become parser bytes, six-byte command records, table dispatches, and
delayed payload calls.

This is not a command reference. Command-specific state changes live in
[pcl-command-map.md](pcl-command-map.md),
[page-raster-imaging.md](page-raster-imaging.md), and
[resource-rom.md](resource-rom.md). The purpose here is to document what the shared
parser code does before those handlers take over.

Primary disassembly evidence:

- `generated/disasm/ic30_ic13_pcl_escape_parser_00da9a.lst`
- `generated/disasm/ic30_ic13_main_parser_loop_011774.lst`
- `generated/disasm/ic30_ic13_tokenizer_stateful_helpers_011ba6.lst`
- `generated/disasm/ic30_ic13_payload_dispatch_011f82.lst`
- `generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst`

Executable evidence is in `tools/render_fixture_harness.py`, especially the parser trace
helpers and the `0x121cc` / `0x12218` delayed-payload helpers.

## State Blocks

The parser initializes these fields at `0x11774` before entering the byte loop:

| Address | Group | Meaning |
| --- | --- | --- |
| `0x782999` | canonical | Current parser mode. Cleared at parser start. |
| `0x78299a` | firmware bookkeeping | Current state handler pointer. Starts as `0x11b8e`. |
| `0x78299e` | canonical | Cursor for six-byte parsed command records. |
| `0x782a1a` | firmware bookkeeping | Delayed-payload pending flag. |
| `0x782a1c` | firmware bookkeeping | Delayed-payload handler pointer. |
| `0x782a20..0x782a25` | firmware bookkeeping | Saved six-byte command record. |
| `0x782a26` | parser scratch | Cursor into byte scratch at `0x782a2a`. |
| `0x782a2a..` | parser scratch | Accumulated nonnumeric command bytes. |
| `0x782a3e` | parser scratch | Cursor into numeric text scratch at `0x782a42`. |
| `0x782a42..` | parser scratch | Digits/sign/fraction bytes collected by tokenizer. |
| `0x782a56` | firmware bookkeeping | Alternate-mode echo helper latch. |
| `0x782c18` | canonical | Alternate/data-mode flag. Chooses alternate parser table. |
| `0x783196..0x783199` | parser scratch | Small local accumulation buffer for matched bytes. |

The six-byte command record at `0x78299e` has this layout:

```text
+0  flags
+1  terminating/final byte
+2  signed integer parameter word
+4  signed fractional parameter word
```

The flag byte is cleared before parsing. `0xdb74` sets bit `0x80` when a numeric value
is present. It writes `0x81` after a leading `+` or `-`, so bit `0x01` is a sign-seen
marker in observed records.

## Parser Byte Wrapper At 0xda9a

Routine `0xda9a` is the normal byte source used by the parser loop and tokenizer. It
calls `0xa904` and returns the byte in `D7` unless the byte is `ESC`.

If the first byte is not `ESC`, `0xda9a` returns it unchanged. If the byte is `ESC`, it
fetches one more byte:

- `ESC` followed by anything except `?` logs that second byte through `0x9ec0` and
  returns `D7 = 0x1b`. The second byte is not lost; it is reported to the
  logging/pushback helper before the parser sees the `ESC`.
- `ESC ? 0x11` is swallowed and the routine restarts from the top.
- `ESC ? X`, where `X` is not `0x11`, compares `X` as if it were the first fetched byte.
  If `X` is not another `ESC`, it returns `X`.

This wrapper is why the main parser sees `ESC` as a single dispatch byte even though
`0xda9a` has already inspected the next host byte.

Routine `0xdace` is a separate payload/control byte reader. It calls `0xa904`. If the
byte is not `0x1a`, it returns that byte. If it sees `0x1a 0x58`, it calls `0xd99a` and
returns `D7 = 0`. If the second byte is not `0x58`, it returns the second byte. Raster,
font, transparent-text, and repeat readers use this routine because their payload bytes
need this local control handling.

## Tokenizer At 0xdb74

`0xdb74` allocates and fills one six-byte command record. It advances `0x78299e` by six
before parsing so callers can rewind the current record by subtracting six from the
cursor.

The tokenizer reads through `0xda9a`, not directly through `0xa904`.

Its behavior:

1. Clear the record flag byte and fractional word.
2. Skip leading spaces.
3. Accept optional `+` or `-`; copy it to scratch and set record flag `0x81`.
4. If the next byte is `.` or a decimal digit, set flag bit `0x80`.
5. Parse up to six integer digits into a long accumulator.
6. Clamp the integer accumulator to `0x7fff`.
7. Negate the integer if a sign was seen and store the low word at record `+2`.
8. If a decimal point is present, parse up to four fractional digits.
9. Negate the fractional accumulator if a sign was seen and store it at `+4`.
10. Skip any additional fractional digits beyond the four stored digits.
11. Store the terminating byte at record `+1`.
12. Log the terminating byte through `0x9ec0`.
13. Return `D7 = 0` for terminators `:` or `;`; otherwise return the terminator.

The digit bytes copied into `0x782a42..0x782a3e` are parser scratch, not the canonical
numeric value. The record words at `+2` and `+4` are the fields that handlers consume.

## Angle Helper At 0xdb46

`0xdb46` is called by `0xdaf0` after a byte has been fetched. If the byte is not `<`, it
returns immediately.

When the byte is `<`, the helper consumes a bracketed span through the caller's
byte-source pointer. It keeps reading until it sees `>`. A nested `<` forces an extra
byte fetch before continuing. After a closing `>`, it fetches the next byte and repeats
if that next byte is another `<`.

The helper does not build command records itself. It positions `D7` on the next byte
that should be considered by the command-combining wrapper.

## Command Combiner At 0xdaf0

`0xdaf0` wraps `0xdb74` for PCL escape-command combining. It sets:

- `A3 = 0xda9a`, the byte-source function;
- `A4 = 0x78299e`, the command-record cursor pointer.

It first calls `0xdb74` to parse one record. Then it rewinds `0x78299e` by six to point
back at that record, fetches the next byte through `0xda9a`, and runs the angle helper.

The combiner then decides whether more records belong to the same command family:

- If the current record's flag byte is nonnegative and the next byte is in `0x20..0x3f`,
  it loops back to `0xdb74` to parse another parameter or intermediate record.
- If the next byte is still in `0x20..0x3f` but the flag byte is negative, it consumes
  bytes through `0xda9a` and the angle helper until the final byte is outside that
  range.
- It writes the final byte to record `+1`, logs it through `0x9ec0`, advances `0x78299e`
  by six, and returns.

This means lowercase PCL finals such as `c` or `b` can leave a record pending for the
uppercase final in the same family, while the final uppercase byte is what causes
command dispatch or delayed payload restore.

## Main Parser Loop At 0x11774

The main loop fetches one parser byte by calling `0xda9a`, copies it to `D5`, and then
decides whether it is printable text or a parser-table byte.

Mode zero has a fast printable path. The loop masks the byte with `0x7f`; if the result
is at least `0x20`, it is printable-ish:

- In normal mode (`0x782c18 == 0`), the loop delays for a short counter and calls
  printable handler `0xd04a`.
- In alternate/data mode (`0x782c18 != 0`), it appends the byte through `0xe002` instead
  of calling the normal printable handler.

Nonprintable bytes, nonzero parser modes, and bytes not handled by the fast path go
through parser dispatch tables. The entry format is six bytes:

```text
+0  byte to match
+1  next parser mode
+2  handler longword
```

Normal-mode table pointers come from `0x112a4` and `0x112a8`, indexed by `0x782999`.
Alternate/data-mode table pointers come from `0x116f6` and `0x116fa`.

The loop scans from the start pointer to the end pointer, comparing entry `+0` with
`D5`. If it finds a matching entry with a nonzero handler longword, it may append the
byte to the local buffer, then calls that handler. The default state handler `0x11b8e`
logs the byte through `0x9ec0` and clears `0x782999`.

If the matching entry has a zero handler longword, the entry is a state transition
rather than an immediate action. In normal mode, the loop writes entry `+1` to
`0x782999`. If the new mode is zero, it calls `0x12218` to restore and dispatch any
delayed payload, then resets the command-record and scratch cursors to their initial
parser values.

If no table entry matches in mode zero normal mode, the loop consults the active
font-context state at `0x782f06` / `0x782eeb`. If that context byte is `1`, it calls
`0xd04a` for the byte; otherwise it ignores the byte and fetches again.

## Stateful Parser Helpers

The helper family at `0x11ba6`, `0x11c6c`, `0x11d0c`, and `0x11dd2` handles multi-record
command families. These helpers are the middle layer between a table transition and
command-specific handlers.

Common behavior across the family:

- call `0xdaf0` to parse another record in the same escape family;
- fetch lookahead bytes through `0xda9a`;
- recognize `w` / `W` as delayed-payload markers;
- schedule wrapper `0x1228a` through `0x121cc` for byte-count payloads;
- call `0x12218` when a terminal byte in `0x40..0x5e` ends the family;
- rewind `0x78299e` by six when the lookahead byte belongs to the current record instead
  of a new one.

These helpers are why a stream such as `ESC *b4W` separates the parsed byte count from
the four payload bytes. The `W` record is first saved by `0x121cc`; the payload reader
is called later only after `0x12218` restores the saved record.

Setup handlers:

- `0x11ea4`: mode-0 `0x1a` setup. It writes callback pointer `0x11b8e` to
  `0x78299a`. The next mode-2 byte decides whether the sequence is
  `0x1a 0x58` (`0x1219e`) or nested `0x1a` (`0x120d2`).
- `0x11eb6`: mode-0 `ESC` setup. It writes callback pointer `0x11ba6` to
  `0x78299a`; mode 1 then routes `*`, `&`, `(`, `)`, `E`, `Y`, and other
  top-level ESC finals.
- `0x11ec8`, `0x11eda`, and `0x11eec`: write active callback pointers
  `0x11c6c`, `0x11d0c`, and `0x11dd2` respectively for nested command-family
  tokenization.
- `0x11efe`: appends a synthetic six-byte record with byte `0x80` and word
  `1`; normal parser `ESC )` uses this to mark the secondary font-designation
  side before tokenization.
- `0x11f26`: appends a synthetic six-byte record with byte `0x80` and word
  `0`; normal parser `ESC (` uses this to mark the primary font-designation
  side before tokenization.
- `0x11f4c`: rewinds `0x78299e` by six for lowercase chaining finals.

Evidence:
`generated/disasm/ic30_ic13_parser_setup_handlers_011ea4.lst`,
`generated/disasm/ic30_ic13_font_selector_setup_helpers_011ec8.lst`,
`generated/analysis/ic30_ic13_parser_dispatch_tables.md`, and
`generated/analysis/ic30_ic13_active_symbol_set_flow.md`.

Variant behavior:

- `0x11ba6`: punctuation-prefixed helper. Incoming bytes `0x21..0x2f`
  consume one extra host byte through `0xda9a`, echo that fetched byte
  through `0x9ec0`, and stop early only if it is space. Otherwise the helper
  tokenizes at `0x11bdc`, arms wrapper `0x1228a` for `W/w`, loops lowercase
  continuation bytes `0x60..0x7e` back through `0xdaf0`, and sends terminal
  bytes `0x40..0x5e` to `0x12218`.
- `0x11c6c`: generic stateful command helper. It echoes the incoming byte
  through `0x9ec0`, skips space, tokenizes at `0x11c88`, and normally treats
  `W/w` as a delayed-payload boundary. Parser mode `4` is the exception:
  after the lookahead fetch, it bypasses the `W/w` special case and rewinds
  `0x78299e` by six before continuing.
- `0x11d0c`: callback continuation helper. Lowercase bytes `0x60..0x7e`
  are continuation candidates; lowercase `w` arms `0x1228a` before the
  tokenizer restart. Uppercase `W` clears mode state, sets local flag `D4`,
  and arms the same wrapper before terminal processing. In alternate/data
  mode, when `0x782a56` is set, terminal bytes append either the terminal
  byte alone or `0x30` plus the terminal byte through `0xe002` before
  `0x12218`.
- `0x11dd2`: font-refreshing callback continuation helper. It shares the
  lowercase `w` and uppercase `W` payload tests with `0x11d0c`; the uppercase
  path rewinds `0x78299e` and calls common font-state refresh helper
  `0xc580` before the terminal range check. Its alternate/data terminal
  append behavior matches `0x11d0c`.

These distinctions are documented from
`generated/disasm/ic30_ic13_tokenizer_stateful_helpers_011ba6.lst` and
summarized in `generated/analysis/ic30_ic13_tokenizer_macro_callers.md`.
For reproduction, the important semantic edge is that `0x78299e` rewinds
select which six-byte record the delayed handler later sees; this affects
generic payload readers, raster payloads, downloaded-font payloads, and macro
data-chain replay.

## ESC Y Display Functions Readers

`ESC Y` enters a reader loop that stays active until the byte stream supplies
`ESC Z` or `0xa904` returns `-1`. The normal parser table dispatches `ESC Y`
to `0x12536`; the alternate/data parser table dispatches it to `0x12120`.

Shared loop rules:

- seed an `ESC`-seen flag `D4 = 0`;
- fetch bytes directly through `0xa904`, not `0xda9a`;
- treat local byte pair `0x1a 0x58` as one value `0x7f` after calling
  `0xd99a`;
- set `D4 = 1` after a routed/appended value `0x1b`;
- stop only when the next routed/appended value is `0x5a` while `D4 == 1`, or
  when the fetch returns `-1`;
- clear `D4` after any non-terminating value other than `0x1b`.

The alternate/data handler `0x12120` first appends literal `ESC Y` through
`0xe002`, then appends each normalized loop value through `0xe002`. It does
not call the text imaging path. Its output effect is data-chain text append,
including normalized `0x7f` for `0x1a 0x58`, until `ESC Z` terminates.

The normal handler `0x12536` is display-functions text imaging. It derives the
same selected context byte and high-control filtering word used by transparent
print data:

- selected slot `0x782f06` is scaled by `0x332ee`;
- context byte `0x782eea + 0x10 * slot` is copied to `D3`;
- fallback byte `0x782efa` supplies the local high-control filter when
  `0x783132` and `0x783133` are clear.

After the same `0xa904` / `0x1a 0x58` normalization, `0x12536` routes
`0x00..0x1f` through `0xd0f0` only when `D3 == 0`, routes `0x80..0x9f`
through `0xd0f0` only when the local filter word is zero, and routes all other
values through `0xd04a`. If the routed value is CR (`0x0d`), it also calls
`0xf054` after the text/control handler. Its output effect is visible text or
fixed-space output using the same source-object and page-record consumers as
direct text and transparent print data.

Evidence: normal parser dispatch table mode 1 entry for byte `0x59` to
`0x12536`, alternate/data mode 1 entry for byte `0x59` to `0x12120`, and
disassembly `generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst`
at `0x12120..0x1219c` and `0x12536..0x1261e`. Fixture
`ESC Y display-functions stream reaches page-record output` proves the normal
handler consumes `ESC Y!\x05! ESC Z`, routes values `21 05 21 1b 5a`, queues
visible `!`, `!`, and `Z`, and renders the resulting page-record rows. Fixture
`ESC Y display-functions filter-on routes controls as printable` proves the
nonzero filter branch for the normal handler: with selected-context byte `1`
and high-control filter `1`, stream `ESC Y\x05\x80\x1aX! ESC Z` normalizes
`0x1a 0x58` to `0x7f`, routes values `05 80 7f 21 1b 5a` through `0xd04a`,
queues six compact entries, and renders digest
`1cdd8203b43944801ec8d1d01c6ab4fa3808fc1f81a7ebfa4d04452369193b63`. Fixture
`0x12120 ESC Y alternate append stores normalized display bytes` proves the
alternate/data handler consumes payload bytes `21 1a 58 1b 5a`, appends the
literal prefix plus normalized loop values as `1b 59 21 7f 1b 5a`, and stores
them through `0xe002` in macro chunk `0x783988` before terminating on appended
`ESC Z`.

## Delayed Payload Scheduler

`0x121cc` stores a pending payload call. It rewinds `0x78299e` by six to the current
record. If no delayed payload is already pending, it writes:

```text
0x782a1a      pending flag = 1
0x782a1c      handler longword passed by caller
0x782a20..25  six-byte command record snapshot
```

Known scheduler callers:

- `0x11f82` schedules raster transfer handler `0x105d0`.
- `0x11f96` schedules font descriptor/setup handler `0x15d0a` when the count in the
  previous record is zero.
- `0x11f96` schedules downloaded font/character handler `0x16c14` when that count is
  nonzero.
- The stateful helpers schedule wrapper `0x1228a` for generic counted payloads.

`0x12218` restores and dispatches the saved payload. If `0x782a1a != 1`, it returns.
Otherwise it clears the pending flag, copies the saved six-byte record to the current
`0x78299e` cursor, advances the cursor by six, and dispatches:

- In normal mode (`0x782c18 == 0`), it calls the saved handler pointer from `0x782a1c`.
- In alternate/data mode, it calls `0x12358` with wrapper `0x1228a` instead.

After dispatch, `0x12218` clears the saved handler longword.

`0x1228a` rewinds the current record, reads the integer count at record `+2`, takes its
absolute value, and calls `0x12328`. `0x12328` consumes that many bytes through
`0xdace`. It returns `D7 = -1` if `0xdace` reports `-1`; otherwise it returns `D7 = 1`
when the count has been consumed.

The downloaded-font delayed handlers use the same drain contract after their
own install work. In `generated/disasm/ic30_ic13_font_payload_setup_015b80.lst`,
`0x15d0a` stores the absolute count in `0x783140`, follows bit-30
downloaded-character records through `0x15dc6 -> 0x16498`, then falls through
to `0x15dcc`, where it passes the remaining `0x783140` value to `0x12328`.
The alternate `0x15b9a`, `0x15c4c`, and `0x16606` branches also join the same
`0x15dcc -> 0x12328` drain before returning. In
`generated/disasm/ic30_ic13_font_resource_object_add_016c14.lst`, nonzero
`ESC )s#W` resource installs converge on `0x16c68`, which likewise calls
`0x12328` with `0x783140` before returning to the parser loop.

`0x12358` is the alternate/data-mode path. If the saved handler pointer equals the
argument passed to `0x12358`, it calls `0x1228a`. Otherwise it consumes a positive count
through `0xdace` and echoes each normalized byte through `0xe002`.

## Parser Record Semantic Checkpoint

This cluster is covered as the parser-record and delayed-payload boundary
between normalized input bytes and command-family handlers. Its main
reproduction contract is that command finals and following payload bytes are
not one event: the firmware writes a six-byte record, may save that record,
and later restores it before payload consumption.

Field groups:

- Canonical parser state:
  - `0x782999`: current parser mode byte;
  - `0x78299e`: current six-byte command-record cursor;
  - six-byte command record: flag byte, final byte, signed integer word,
    and signed fractional word;
  - `0x782c18`: normal versus alternate/data parser mode.
- Parser scratch:
  - `0x782a26` and `0x782a2a..`: nonnumeric command-byte scratch;
  - `0x782a3e` and `0x782a42..`: sign/digit/fraction tokenizer scratch;
  - `0x783196..0x783199`: local matched-byte accumulation buffer.
- Firmware bookkeeping:
  - `0x78299a`: active callback helper pointer selected by setup handlers
    `0x11ea4`, `0x11eb6`, `0x11ec8`, `0x11eda`, and `0x11eec`;
  - `0x782a1a`: delayed-payload pending flag;
  - `0x782a1c`: delayed handler pointer;
  - `0x782a20..0x782a25`: saved six-byte command record;
  - `0x782a56`: alternate/data echo-helper latch.
- Derived records/cache:
  - `0x11efe` appends a synthetic secondary font-designation record with
    byte `0x80` and word `1`;
  - `0x11f26` appends a synthetic primary font-designation record with
    byte `0x80` and word `0`;
  - `0x11f4c` derives a lowercase-chain continuation by rewinding
    `0x78299e` by one record.
- Unknown:
  - no unresolved parser-record fields for this checkpoint. Remaining
    command-family unknowns are tracked in their own notes after records
    reach terminal handlers.

Writers:

- `0xdb74` writes command-record fields and numeric scratch.
- `0xdaf0` combines records in one PCL escape family and rewinds the record
  cursor when lookahead still belongs to that family.
- `0x11774` clears initial parser state, dispatches by normal or
  alternate/data tables, writes parser mode transitions, and triggers
  `0x12218` when a state transition returns to mode zero.
- `0x11ba6`, `0x11c6c`, `0x11d0c`, and `0x11dd2` tokenize stateful
  command families, arm `0x121cc(0x1228a)` for `W/w` payload boundaries,
  and decide whether terminal bytes restore delayed state through
  `0x12218`.
- `0x121cc` writes the pending flag, saved handler, and saved six-byte
  record; `0x12218` clears the flag, restores the saved record to the
  active cursor, dispatches the saved handler, and clears the handler
  longword.
- `0x1228a`, `0x12328`, and `0x12358` consume counted payloads or append
  alternate/data payload bytes after `0x12218` restores the record.

Readers and consumers:

- Terminal command handlers consume the active six-byte record selected by
  the helper/cursor rewind behavior.
- Raster transfer `0x105d0`, transparent text `0x12452`, downloaded-font
  handlers `0x15d0a` and `0x16c14`, and generic wrapper `0x1228a` depend
  on the same delayed-record restore contract.
- Macro definition mode and alternate/data mode consume parser records but
  redirect payload bytes through `0xe002` rather than immediate imaging.

Output effect:

- This checkpoint has no pixels by itself. It preserves the record and
  payload state that later pixel-producing handlers consume.
- Fixture `0x11774 ROM dispatch table routes raster stream to delayed
  transfer` proves the parser reaches `0x11f82` and stores the delayed
  raster transfer record before payload bytes are consumed.
- Fixture `modeled raster command stream parses ESC *t300R / ESC *r1A /
  ESC *b4W payload boundary` proves `0x12218` restores the saved `W`
  record before the payload reader consumes the following bytes.
- Fixture `transparent data parser trace feeds page-record queue` proves
  delayed transparent text restores through `0x12452` before routing
  payload bytes into text/fixed-space output.
- Fixtures `resource payload stream ties ROM parser dispatch to 0x16c14
  install` and `downloaded character stream ties ROM parser dispatch to
  rendered object` prove the same delayed-record contract feeds
  downloaded-font payload handlers before visible glyph output.

Confidence:

- High for tokenizer record layout, cursor rewind, helper selection, delayed
  snapshot/restore, and alternate/data redirection because these are direct
  disassembly reads and fixture-backed across raster, transparent text,
  downloaded-font, and macro paths.
- Medium only for command-family semantics beyond the parser boundary. Those
  are intentionally documented in command-family notes.

Fixture evidence:

- `0x11774 ROM dispatch table routes raster stream to delayed transfer`
- `modeled raster command stream parses ESC *t300R / ESC *r1A / ESC *b4W
  payload boundary`
- `raster chained transfer parser trace preserves lowercase delayed record`
- `transparent data parser trace feeds page-record queue`
- `resource payload stream ties ROM parser dispatch to 0x16c14 install`
- `downloaded character stream ties ROM parser dispatch to rendered object`
- `macro execute frame payload feeds 0xa904 data-chain bytes`
- Macro execute/call replay fixtures documented in
  [pcl-parser-firmware.md](pcl-parser-firmware.md).

Disassembly evidence:

- `generated/disasm/ic30_ic13_pcl_escape_parser_00da9a.lst`
- `generated/disasm/ic30_ic13_main_parser_loop_011774.lst`
- `generated/disasm/ic30_ic13_tokenizer_stateful_helpers_011ba6.lst`
- `generated/disasm/ic30_ic13_parser_setup_handlers_011ea4.lst`
- `generated/disasm/ic30_ic13_payload_dispatch_011f82.lst`
- `generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst`
- `generated/disasm/ic30_ic13_font_payload_readers_0168dc.lst`
- `generated/analysis/ic30_ic13_tokenizer_macro_callers.md`

Unresolved middle edges:

- None for parser-record layout, tokenizer rewind, delayed scheduler
  snapshot, or `0x12218` restore/dispatch. Open work after this boundary is
  command-family specific: terminal handler effects, page-object allocation,
  font/raster payload interpretation, macro data-chain lifecycle, and final
  rendered output.

## Reproduction Requirements

A byte-stream reproduction must preserve these parser contracts:

- Feed parser bytes through `0xda9a`, not directly through `0xa904`.
- Feed counted binary/text payload bytes through the consumer used by the ROM path,
  usually `0xdace` for delayed payload consumers.
- Preserve the six-byte command-record cursor at `0x78299e` and the rewind by six bytes
  used by handlers and delayed payload setup.
- Treat `0x782a42..0x782a3e` as scratch text; the canonical parsed numeric fields are
  the words in the six-byte record.
- Preserve `0x782999` mode transitions and the normal vs alternate table choice
  controlled by `0x782c18`.
- Preserve delayed payload state `0x782a1a`, `0x782a1c`, and saved record bytes
  `0x782a20..0x782a25` across the command terminator that triggers `0x12218`.
- Do not collapse command records and payload bytes into one parser event. The ROM
  stores the command record first and consumes payload bytes later.

## Parser-Core Status

The shared parser mechanism and currently identified command-family parser
edges in this note are documented.

- `0x12452` transparent print data is documented in
  [transparent-print-data.md](transparent-print-data.md). That command-family
  note covers delayed restore, `1a` probe handling, C0 and `0x80..0x9f`
  filtering, fixed-space output, nonzero-filter printable routing, and
  secondary-context segmented page-record output through concrete fixtures.
- New command-family semantic notes should keep citing terminal handlers and
  output effects rather than parser-table membership alone.
