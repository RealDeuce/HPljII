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

Primary parser-core fixtures:

- `0xdaf0 tokenizes lowercase-final numeric chain into two six-byte records`
- `0xdb74 parses sign, capped fraction digits, and final byte`
- `0xdb74 returns D7 zero for semicolon continuation final`
- `0x121cc snapshots delayed payload handler and parsed record`
- `0x12218 restores delayed parsed record and dispatches saved handler`
- `0x121cc/0x15d0a-modeled font descriptor command stream`
- `0x11f5a/0x12452 transparent text restores and consumes counted bytes`
- `0x12452 transparent text probe keeps non-0x58 byte`
- `0x1228a consumes absolute delayed payload count without echo`
- `0x12358 direct alternate path echoes positive payload bytes only`

## Parser Front-Door Owner Summary

This note owns the transition from one admitted byte to a parser outcome. It
does not own command-family side effects after a terminal handler starts
writing cursor, font, raster, rectangle, macro, or page state.

The front-door route is:

```text
0xa904 byte source
  -> 0xda9a ESC-aware parser byte wrapper
  -> 0x11774 parser loop
  -> printable fallback, append sink, table handler, zero-handler reset,
     callback continuation, delayed-payload restore, or parser return
```

Writers:

- `0xda9a` writes no parser state, but it decides what byte `0x11774` sees.
  It returns ordinary bytes unchanged, returns `ESC` after pushing/logging the
  lookahead byte through `0x9ec0`, and swallows `ESC ? 0x11`.
- `0xdace` is the sibling payload reader, not the parser wrapper. It reads
  through `0xa904` and normalizes local payload pair `1a 58` to `0x00`.
- `0xdb74` writes six-byte command records at `0x78299e`, numeric scratch, and
  final-byte fields consumed by terminal handlers.
- `0xdaf0` combines multiple parameter records in the same PCL family and
  rewinds `0x78299e` when lookahead belongs to the current family.
- `0x11774` writes parser mode `0x782999`, chooses normal table `0x112a4` or
  alternate/data table `0x116f6`, records matched bytes in
  `0x783196..0x783199`, calls nonzero table handlers, and resets parser
  scratch on terminal zero-handler paths.
- Setup and callback helpers `0x11ea4`, `0x11eb6`, `0x11ec8`, `0x11eda`,
  `0x11eec`, `0x11ff6`, `0x12008`, and `0x1201e` write callback pointer
  `0x78299a` or synthetic records so later bytes stay in the active command
  family.
- Delayed-payload scheduler `0x121cc` writes pending flag `0x782a1a`, handler
  pointer `0x782a1c`, and saved record `0x782a20..0x782a25`; restore helper
  `0x12218` copies that record back to the live cursor and calls the saved
  handler when parser state returns to mode zero.

Readers and consumers:

- Printable fallback calls `0xd04a` in normal mode. From there, text/font
  owner notes consume selected context, cursor, source object, page root, and
  render state.
- Alternate/data printable and alternate/data blank C0 rows append through
  `0xe002`. They have no immediate page effect; macro/data-chain replay later
  consumes the stored bytes as ordinary `0xa904` input.
- Nonzero table handlers consume the live six-byte record or parser mode and
  then hand off to [pcl-command-map.md](pcl-command-map.md) owner families.
- Zero-handler rows consume no command handler but can still call
  `0x12218`. If delayed payload is pending, the zero-handler terminal boundary
  is what restores and dispatches the saved payload handler.
- Delayed payload consumers include transparent reader `0x12452`, VFC reader
  `0x12cfe`, raster transfer `0x105d0`, font descriptor/current handlers
  `0x15d0a` and `0x16c14`, and generic drain `0x1228a -> 0x12328`.
- Parser-external return at `0x117d2..0x11818` services latch `0x780e3b` and
  macro/page state byte `0x782a92`; it returns before command-family state is
  mutated.

Outcome classes:

- Printable page output:
  normal mode-zero printable bytes and selected no-match fallback reach
  `0xd04a`. Page objects and pixels are downstream of that call, not parser
  state.
- State-only command:
  a matched terminal handler updates persistent state such as cursor, page
  geometry, selected font, VFC, macro, raster setup, or rectangle dimensions.
  Output appears only when later bytes consume that state.
- Binary payload:
  the parser stores a handler/record pair; payload bytes are read later by the
  restored handler rather than by the command-table matcher.
- No-output parser artifact:
  explicit blank C0 rows, `ESC ?`, display-reader `ESC Z`, `ESC &lT/t`, and
  generic counted drains reset, append, or synchronize parser state without
  drawing.
- Host/status side channel:
  table handlers such as the model-ID path emit host response bytes through
  FIFO helpers, not page records.

Field classification at this boundary:

- Canonical parser state:
  mode `0x782999`, alternate/data flag `0x782c18`, command-record cursor
  `0x78299e`, six-byte command records, delayed fields
  `0x782a1a/0x782a1c/0x782a20..0x782a25`, and parser table roots.
- Parser scratch:
  byte scratch `0x782a26/0x782a2a..`, numeric scratch
  `0x782a3e/0x782a42..`, matched-byte buffer `0x783196..0x783199`, and
  transient lookahead bytes.
- Firmware bookkeeping:
  callback pointer `0x78299a`, append sink `0xe002`, logging/pushback helper
  `0x9ec0`, payload-control helper `0xd99a`, service latch `0x780e3b`, and
  macro/page state byte `0x782a92`.
- Canonical page/render state:
  none is written by the parser loop alone. Page roots, records, publication,
  scheduler fields, and pixels begin in the command-family owner reached by
  the parser outcome.
- Hardware/external state:
  outside this parser checkpoint after `0xa904` has admitted the byte.
- Unknown:
  no ROM-local unknown remains for classifying an admitted byte into these
  parser outcomes. Remaining unknowns are command-family, resource, or
  hardware boundaries named by the downstream owner notes.

## State Blocks

The parser initializes these fields at `0x11774` before entering the byte loop:

| Address | Group | Meaning |
| --- | --- | --- |
| `0x782999` | canonical | Current parser mode. Cleared at parser start. |
| `0x78299a` | firmware bookkeeping | State handler pointer; starts as `0x11b8e`. |
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
| `0x783196..0x783199` | parser scratch | Local matched-byte buffer. |

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

The instruction-level wrapper flow is:

- `0xda9a..0xdaa4` calls host-byte fetch `0xa904` and returns immediately
  through `0xdacc` when the byte is not `ESC` (`0x1b`).
- `0xdaa6..0xdab0` handles the `ESC` lookahead. It fetches one more byte
  through `0xa904`; if that byte is not `?`, it goes to the pushback/log path.
- `0xdab2..0xdabe` handles the `ESC ?` private pair. It fetches a third byte:
  `0x11` is swallowed and restarts the wrapper at `0xda9a`; any other byte
  rejoins the first-byte comparison at `0xdaa0`, so another `ESC` can be
  treated as a fresh escape byte.
- `0xdac0..0xdacc` logs or pushes back the non-`?` lookahead byte through
  `0x9ec0`, then returns `D7 = 0x1b`. The parser loop therefore dispatches
  on the `ESC` byte while the lookahead byte remains available through the
  firmware's pushback/log source ordering.

Routine `0xdace` is a separate payload/control byte reader. It calls `0xa904`.
If the byte is not `0x1a`, it returns that byte. If it sees `0x1a 0x58`, it
calls `0xd99a` and returns `D7 = 0`. If the second byte is not `0x58`, it
returns the second byte. Generic delayed drains and several command-family
payload consumers use this routine because their payload bytes need this local
control handling. Transparent print data is a sibling counted reader with its
own local `1a` probe, documented in
[transparent-print-data.md](transparent-print-data.md), not a `0xdace` caller.

The `0xdace` reader flow is:

- `0xdace..0xdad8` calls `0xa904` and returns any byte other than `0x1a`.
- `0xdada..0xdae4` fetches the probe byte after `0x1a`. A non-`0x58` probe is
  returned as the payload byte; the leading `0x1a` is consumed by the probe.
- `0xdae6..0xdaec` handles `1a 58`: it calls local helper `0xd99a`, clears
  `D7`, and returns one normalized payload byte `0x00`.

These two readers are intentionally different. Parser syntax bytes go through
`0xda9a` so `ESC` can drive parser state while preserving the lookahead byte.
Counted payload readers that call `0xdace` do not run the `ESC` lookahead
logic; they only apply the local `1a 58 -> 00` payload-control rule.

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

Fixture `0xdb74 parses sign, capped fraction digits, and final byte` pins the
record layout with signed integer and fractional fields, including the cap at
six integer digits and four stored fractional digits. Fixture `0xdb74 returns
D7 zero for semicolon continuation final` pins the tokenizer return contract:
semicolon and colon continuation finals store the final byte in the record but
return `D7 = 0` to the caller.

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

Fixture `0xdaf0 tokenizes lowercase-final numeric chain into two six-byte
records` proves this command-family combine behavior directly. The lowercase
record remains in the six-byte record stream, the cursor is positioned so the
uppercase sibling can be parsed as a second record, and later handlers see the
same canonical record sequence that the ROM parser built.

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

The normal table's mode-zero blank C0 rows `0x00`, `0x07`, and `0x0b`
are concrete examples of that matched zero-handler path. They have next mode
zero, so they enter `0x11912..0x119bc`, call `0x12218`, reset
`0x78299e`, `0x782a26`, `0x782a3e`, and `0x782a56`, and clear the
local matched-byte buffer. Because these bytes match explicit table entries,
they bypass the unmatched mode-zero normal fallback at `0x118d6..0x11900`.
That fallback is the only path in this loop that consults `0x782f06` /
`0x782eeb` and may route an otherwise unmatched byte through printable handler
`0xd04a`.

Alternate/data mode uses a different zero-handler subpath before the same
terminal reset. For mode-zero matched C0 rows with no handler, including
`0x00`, `0x07`, `0x08`, `0x09`, `0x0a`, `0x0b`, `0x0c`, `0x0d`,
`0x0e`, and `0x0f`, `0x11930..0x11ab8` stores the byte in parser scratch,
optionally flushes prior scratch through `0x123ae`, flushes numeric scratch
through `0x123de`, appends the matched byte through `0xe002`, then rejoins
`0x119b0..0x119f4`. The byte is therefore preserved in the alternate/data
append stream, but still does not run the normal-mode control handler or
printable fallback.

If no table entry matches in mode zero normal mode, the loop consults the active
font-context state at `0x782f06` / `0x782eeb`. If that context byte is `1`, it calls
`0xd04a` for the byte; otherwise it ignores the byte and fetches again.

### Main Parser Branch Boundaries

The `0x11774` loop is the first shared semantic route after normalized byte
fetch. These ranges are the ROM-local decision points a reader should follow
before jumping to a command-family owner note:

- `0x11774..0x117c4`: parser-session initialization. The loop clears mode byte
  `0x782999`, installs default callback `0x11b8e` in `0x78299a`, initializes
  the six-byte command-record cursor to `0x7829a2`, clears delayed-payload
  state `0x782a1a` / `0x782a1c`, resets byte and numeric scratch cursors
  `0x782a26` / `0x782a3e`, clears `0x782a56`, and sets the local matched-byte
  buffer to `0x783196..0x783199`.
- `0x117d2..0x11818`: fetch one byte through `0xda9a`, copy it to `D5`, then
  service two parser-external latches before ordinary dispatch. If
  `0x780e3b == 1`, it clears that byte and repeatedly calls `0x10c8` with
  `0x780202`. If macro/page state byte `0x782a92 == 0x63`, it rewrites it to
  `1` and returns from the parser loop.
- `0x1181a..0x11886`: mode-zero printable fast path. If `0x782999 == 0` and
  `(D5 & 0x7f) >= 0x20`, normal mode delays for a short counter and calls
  `0xd04a(D5)`. Alternate/data mode, selected by nonzero `0x782c18`, appends
  the same byte through `0xe002(D5)` and fetches the next byte without calling
  the printable handler.
- `0x11840..0x118b2`: dispatch-table selection. Normal mode uses start/end
  pointers from `0x112a4` / `0x112a8`, indexed by mode `0x782999`.
  Alternate/data mode uses parallel pointers from `0x116f6` / `0x116fa`.
  Each table entry is six bytes: match byte, next mode, handler longword.
- `0x118b2..0x11910`: table scan and no-match split. A matching byte reaches
  `0x11912`. If no entry matches, mode-zero normal parsing reaches
  `0x118d6..0x11900`, where the selected font-context byte at
  `0x782ee6 + 16 * 0x782f06 + 5` gates fallback printable output through
  `0xd04a(D5)`. Mode-zero alternate/data no-match reaches `0x11b82`, which
  appends through `0xe002(D5)`. Nonzero no-match reaches `0x11b32`, which
  calls the active parser callback pointer in `0x78299a`.
- `0x11912..0x119a4`: matched table entry with a nonzero handler. The handler
  longword at entry `+2` is copied to `A5`. If local matched-byte buffer space
  remains, the byte is stored in `0x783196..0x783199`. The same-mode marker at
  the local end byte is set when the current mode already equals entry `+1`.
  The handler is then called through `jsr (A5)`, and control falls into the
  same terminal-state path used by zero-handler entries.
- `0x119a6..0x119f4`: normal zero-handler terminal path. The parser resets
  byte scratch, writes next mode byte `entry+1` to `0x782999`, and when that
  next mode is zero calls `0x12218` before restoring the command-record cursor,
  byte scratch cursor, numeric scratch cursor, alternate echo latch, and local
  matched-byte buffer.
- `0x11930..0x11ab8`: alternate/data zero-handler terminal path. The loop
  still writes the next mode and can call the same `0x12218` delayed-payload
  restore, but before terminal reset it preserves matched C0 and command bytes
  by flushing byte scratch through `0x123ae`, numeric scratch through
  `0x123de`, and appending the matched byte through `0xe002`.
- `0x11a04..0x11a9c`: macro-control exception inside that alternate/data
  path. If the current parser mode is `17`, the active six-byte record word
  `+2` is zero, and the final byte is `x` or `X`, the loop does not append the
  final byte as an ordinary stored command byte. Lowercase `x` rejoins the
  terminal path immediately. Uppercase `X` tests current macro record raw count
  `0x782d7a(+4)`, and when it is greater than `1` appends one zero byte through
  `0xe002` before the terminal reset. This post-handler append is separate
  from selector-`0` handler `0xdd86`, which can already seed macro definition
  bytes before control returns to the parser loop.
- `0x11af6..0x11b2e`: nonzero next-mode continuation after a state transition.
  When the active callback is `0x11d0c` or `0x11dd2` and the byte is a
  lowercase final in `0x60..0x7e`, the loop calls `0xdaf0` to continue command
  combining in the same family before fetching another byte.
- `0x11b32..0x11b7e`: callback no-match path for nonzero parser modes. The
  current byte is passed to the callback in `0x78299a`. If the callback returns
  with mode zero, the loop resets parser cursors and clears pending
  delayed-payload byte `0x782a1a`; if mode remains nonzero, it fetches the
  next byte.

The important output boundary is that `0x11774` itself does not draw pixels.
It either calls a semantic handler such as `0xd04a`, a command-family handler,
or `0x12218` delayed-payload restore; appends bytes to alternate/data storage
through `0xe002`; or resets parser scratch with no page-object producer.

## Inbound Byte Outcome Contract

After fetch wrapper `0xda9a` returns a normalized byte, parser loop `0x11774`
reduces that byte to one of the following ROM-visible outcomes. This is the
top-level byte-to-parser-result contract; command-family notes own the later
state and page-object details after a nonzero handler is called.

- Parser-external service or return: `0x117d2..0x11818` first services latch
  `0x780e3b` by clearing it and repeatedly calling `0x10c8` with `0x780202`.
  It then treats macro/page state byte `0x782a92 == 0x63` as a parser return
  boundary, rewrites the byte to `1`, and exits without routing the current
  normalized byte through a command handler.
- Normal printable byte: in mode zero with normal parser table selection
  (`0x782999 == 0`, `0x782c18 == 0`) and `(D5 & 0x7f) >= 0x20`,
  `0x1181a..0x11886` calls printable handler `0xd04a(D5)`. The parser loop is
  only the dispatcher; text placement and page-record production are owned by
  the printable/text path.
- Alternate/data printable byte: the same printable range with nonzero
  alternate/data selector `0x782c18` calls append helper `0xe002(D5)` instead
  of `0xd04a`. The byte is preserved for the active data stream, macro stream,
  or replay context, and the parser fetches again without immediate page-state
  mutation.
- Table-matched command byte: `0x11840..0x119a4` selects the normal table
  (`0x112a4` / `0x112a8`) or alternate/data table (`0x116f6` / `0x116fa`),
  scans six-byte rows, records the matched byte in `0x783196..0x783199` when
  there is room, and calls the nonzero handler longword at row `+2`. The row's
  next-mode byte becomes the parser mode in the terminal path.
- Matched zero-handler row: `0x119a6..0x119f4` is an explicit no-command-output
  transition for normal-table rows whose handler longword is zero. It resets
  parser scratch and cursor state, stores the next mode in `0x782999`, and
  calls delayed-payload restore `0x12218` only when the next mode is zero.
- Alternate/data zero-handler append row: `0x11930..0x11ab8` handles the
  corresponding alternate/data blank rows. Before the same terminal reset, it
  can flush byte scratch through `0x123ae`, flush numeric scratch through
  `0x123de`, and append the matched byte through `0xe002`.
- Mode-zero no-match normal fallback: `0x118b2..0x11900` consults selected
  context byte `0x782ee6 + 16 * 0x782f06 + 5`. Value `1` routes the byte to
  printable handler `0xd04a(D5)`; any other value ignores the byte and fetches
  again.
- Mode-zero no-match alternate/data append: `0x11b82..0x11b8a` appends the
  byte through `0xe002(D5)` when no alternate/data table row matched and the
  parser mode is zero.
- Nonzero-mode callback no-match: `0x11b32..0x11b7e` passes the byte to active
  callback pointer `0x78299a`. If the callback returns to mode zero, the loop
  clears parser cursors and pending delayed-payload byte `0x782a1a`; otherwise
  it keeps the command-family mode active and fetches again.

Field grouping for this parser contract:

- Canonical parser state: mode byte `0x782999`, normal/alternate table slices
  at `0x112a4..0x116fa`, parser record fields `0x78299e..0x7829a3`, and
  selected context index `0x782f06`.
- Parser scratch: byte and numeric scratch cursors `0x782a26` / `0x782a3e`,
  local matched-byte buffer `0x783196..0x783199`, and delayed-payload pending
  fields `0x782a1a` / `0x782a1c`.
- Firmware bookkeeping: active callback pointer `0x78299a`,
  alternate/data selector `0x782c18`, service latch `0x780e3b`,
  macro/page state byte `0x782a92`, error/report helper `0x9ec0`, append
  helper `0xe002`, and delayed restore helper `0x12218`.
- Canonical page/render state: not written directly by parser loop `0x11774`.
  Page/image effects begin only after a called semantic handler such as
  `0xd04a` or a command-family handler mutates the downstream owner state.

Evidence: `generated/disasm/ic30_ic13_main_parser_loop_011774.lst` contains
the branch ranges listed above;
`generated/analysis/ic30_ic13_parser_dispatch_tables.md` contains the table
rows and handler longwords; [pcl-command-map.md](pcl-command-map.md) maps
those rows to checked-in command-family owner notes.

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
- `0x11fd2` and `0x11fe4`: alternate/data parser `ESC )` / `ESC (` wrappers.
  They call `0x11ec8` and then tokenize through `0xdaf0`; unlike normal
  wrappers `0x12008` and `0x1201e`, they do not append the synthetic slot
  record first.
- `0x11f4c`: rewinds `0x78299e` by six for lowercase chaining finals.

Evidence:
`generated/disasm/ic30_ic13_parser_setup_handlers_011ea4.lst`,
`generated/disasm/ic30_ic13_control_z_handlers_0120d2.lst`,
`generated/disasm/ic30_ic13_font_selector_setup_helpers_011ec8.lst`,
`generated/analysis/ic30_ic13_parser_dispatch_tables.md`, and
[symbol-set-selection.md](symbol-set-selection.md).

Control-Z terminal behavior is table-dependent. In the normal parser table,
`0x120d2` handles nested `0x1a`: it checks selected context byte
`0x782eeb + 0x10 * 0x782f06` and only routes printable value `0x1a` through
`0xd04a` when that byte is `1`. Normal `0x1a X` reaches `0x1219e`, which routes
value `0x100` through `0xd04a`. In the alternate/data table, nested `0x1a`
reaches `0x1210c` and appends byte `0x1a` through `0xe002`; alternate
`0x1a X` reaches `0x121b2`, calls `0xd99a`, and appends normalized byte `0x7f`
through `0xe002`. These rows are therefore parser-control terminals, not PCL
imaging commands.

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

See [display-functions.md](display-functions.md#owner-summary) for the composed
renderer-facing contract for the normal output loop, alternate append loop,
Control-Z siblings, and `ESC z` status edge. This section preserves parser-core
details.

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
`ESC Y display-functions stream reaches page-record output` checks the normal
handler: it consumes `ESC Y!\x05! ESC Z`, routes values `21 05 21 1b 5a`,
queues visible `!`, `!`, and `Z`, and reaches the ROM-derived page-record row
path. Fixture `ESC Y display-functions filter-on routes controls as
printable` checks the nonzero filter branch for the normal handler: with
selected-context byte `1` and high-control filter `1`, stream
`ESC Y\x05\x80\x1aX! ESC Z` normalizes `0x1a 0x58` to `0x7f`, routes values
`05 80 7f 21 1b 5a` through `0xd04a`, queues six compact entries, and records
digest
`1cdd8203b43944801ec8d1d01c6ab4fa3808fc1f81a7ebfa4d04452369193b63`. Fixture
`0x12120 ESC Y alternate append stores normalized display bytes` checks the
alternate/data handler: it consumes payload bytes `21 1a 58 1b 5a`, appends
the literal prefix plus normalized loop values as `1b 59 21 7f 1b 5a`, and
stores them through `0xe002` in macro chunk `0x783988` before terminating on
appended `ESC Z`.

## Delayed Payload Scheduler

`0x121cc` stores a pending payload call. It rewinds `0x78299e` by six to the current
record. If no delayed payload is already pending, it writes:

```text
0x782a1a      pending flag = 1
0x782a1c      handler longword passed by caller
0x782a20..25  six-byte command record snapshot
```

The pending check is part of the ROM contract. Disassembly
`0x121cc..0x12210` always rewinds the active record cursor before testing
`0x782a1a`, but it only writes the pending flag, handler pointer, and saved
record when the flag was clear. A second arming call while a delayed payload is
already pending therefore does not replace the saved handler or saved six-byte
record.

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

Alternate/data mode wrapper `0x12358` has two branches:

- If saved handler `0x782a1c` equals the wrapper argument, `0x12358` calls
  `0x1228a`. This preserves the generic counted-drain behavior for stateful
  `W/w` payloads that were explicitly armed with `0x1228a`.
- If the saved handler differs from the wrapper argument, `0x12358` does not
  call that saved handler. It rewinds the restored record by six, reads signed
  word `+2`, and returns immediately for nonpositive counts. For positive
  counts it drains bytes through `0xdace` and echoes each normalized byte
  through `0xe002` until the count is consumed or `0xdace` returns `-1`.

Thus alternate/data mode turns non-wrapper delayed payloads into echoed data
rather than normal command-family effects. Raster `0x105d0`, transparent text
`0x12452`, and font handlers do not run from this branch unless the parser has
returned to normal mode before `0x12218` dispatches them.

Fixtures `0x121cc snapshots delayed payload handler and parsed record` and
`0x12218 restores delayed parsed record and dispatches saved handler` pin the
bookkeeping fields: pending flag `0x782a1a`, handler pointer `0x782a1c`, saved
record `0x782a20..0x782a25`, restored active record at `0x78299e`, and handler
clear after dispatch. Fixture `0x1228a consumes absolute delayed payload count
without echo` proves generic wrapper `0x1228a` uses the absolute value of
record word `+2`, drains bytes through `0x12328` / `0xdace`, and does not echo
payload bytes through the alternate/data append path.
Fixture `0x12358 direct alternate path echoes positive payload bytes only`
proves the non-wrapper alternate/data branch above: positive counts are echoed
through `0xe002`, while nonpositive counts return without consuming payload.

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

Transparent print data is the direct parser-core delayed-payload sibling at
`0x11f5a`. It schedules handler `0x12452` through `0x121cc`; after
`0x12218` restores the saved count record, `0x12452` consumes the absolute
byte count and routes bytes into text/fixed-space output. Fixture
`0x11f5a/0x12452 transparent text restores and consumes counted bytes` pins
that restore/consume boundary. Fixture `0x12452 transparent text probe keeps
non-0x58 byte` pins the local Control-Z probe edge: `0x1a 0x58` is the
normalized special pair, while a non-`0x58` second byte remains payload data.

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
  transfer` checks that the parser reaches `0x11f82` and stores the delayed
  raster transfer record before payload bytes are consumed.
- Fixture `modeled raster command stream parses ESC *t300R / ESC *r1A /
  ESC *b4W payload boundary` checks that `0x12218` restores the saved `W`
  record before the payload reader consumes the following bytes.
- Fixture `transparent data parser trace feeds page-record queue` checks that
  delayed transparent text restores through `0x12452` before routing
  payload bytes into text/fixed-space output.
- Fixture `0x121cc/0x15d0a-modeled font descriptor command stream` checks that
  zero-count font descriptor `W` commands use the same scheduler fields before
  handler `0x15d0a` consumes the restored record.
- Fixtures `resource payload stream ties ROM parser dispatch to 0x16c14
  install` and `downloaded character stream ties ROM parser dispatch to
  rendered object` check that the same delayed-record contract feeds
  downloaded-font payload handlers before visible glyph output.

Confidence:

- High for tokenizer record layout, cursor rewind, helper selection, delayed
  snapshot/restore, and alternate/data redirection because these are direct
  disassembly reads and checked by fixtures across raster, transparent text,
  downloaded-font, and macro paths.
- Medium only for command-family semantics beyond the parser boundary. Those
  are intentionally documented in command-family notes.

Fixture evidence:

- `0xdaf0 tokenizes lowercase-final numeric chain into two six-byte records`
- `0xdb74 parses sign, capped fraction digits, and final byte`
- `0xdb74 returns D7 zero for semicolon continuation final`
- `0x121cc snapshots delayed payload handler and parsed record`
- `0x12218 restores delayed parsed record and dispatches saved handler`
- `0x121cc/0x15d0a-modeled font descriptor command stream`
- `0x11f5a/0x12452 transparent text restores and consumes counted bytes`
- `0x12452 transparent text probe keeps non-0x58 byte`
- `0x1228a consumes absolute delayed payload count without echo`
- `0x12358 direct alternate path echoes positive payload bytes only`
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

## Reproduction Contract

For a supplied byte stream, this layer is reproduced when the same admitted
bytes produce the same parser mode, six-byte records, handler calls, delayed
payload restore events, and alternate/data appends that the ROM parser would
produce. The required ROM-visible behavior is:

- Parser syntax bytes enter through `0xda9a`, not directly through `0xa904`.
  The wrapper makes `ESC` visible as one parser byte while reporting the
  non-`?` lookahead byte through `0x9ec0`; it also swallows only the private
  `ESC ? 0x11` sequence. Counted payload readers do not use this `ESC`
  wrapper unless their documented command-family path says so.
- The tokenizer stores syntax in six-byte records at `0x78299e`: flag byte,
  final byte, signed integer word, and signed fractional word. Scratch digits
  in `0x782a42..0x782a3e` are not canonical command state. Handlers consume
  the record words, not the scratch text.
- Cursor rewinds are semantic state. `0xdaf0`, `0x11f4c`, and `0x121cc`
  can subtract six from `0x78299e` so a lowercase chain, terminal handler, or
  delayed payload setup sees the intended record. A reproduction must not
  collapse those records into one parsed event.
- Parser mode `0x782999` selects the current normal table slice
  `0x112a4` / `0x112a8` or alternate/data table slice
  `0x116f6` / `0x116fa`, depending on `0x782c18`. Matched entries write the
  next mode byte and optionally call the handler longword at entry `+2`.
- The mode-zero printable fast path is table-external behavior. In normal
  mode, printable bytes call `0xd04a`; in alternate/data mode they append
  through `0xe002`. Matched blank C0 rows are different from unmatched bytes:
  they take the explicit terminal state path and do not fall through to the
  selected-context printable fallback.
- Returning to mode zero can dispatch a pending delayed payload. The terminal
  state path calls `0x12218`; if `0x782a1a == 1`, `0x12218` restores saved
  record bytes `0x782a20..0x782a25`, calls saved handler `0x782a1c` in normal
  mode, or redirects non-wrapper payloads through `0x12358` in alternate/data
  mode.
- Delayed payload scheduling is edge-triggered by the first saved command.
  `0x121cc` always rewinds the active record cursor, but it only writes
  pending flag `0x782a1a`, handler pointer `0x782a1c`, and saved record
  bytes when no delayed payload is already pending. Later arming attempts do
  not replace the saved handler or record.
- Counted binary/text payload bytes follow the consumer selected by the
  command path. Generic delayed drains use `0x1228a -> 0x12328 -> 0xdace`,
  while raster, transparent text, and downloaded-font handlers have their own
  documented consumers after `0x12218` restores the saved record.
- Alternate/data mode is not command ignorance. It preserves parser state and
  payload boundaries, but redirects printable bytes, matched blank C0 rows,
  and many non-wrapper delayed payload bytes into stored data through
  `0xe002` instead of immediate page or render handlers.

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
