# IC30/IC13 Tokenizer and Macro Dispatch Callers

This report closes the static caller lead from `notes/pcl-parser-firmware.md`:
direct callers of tokenizer `0xdaf0` are listed by role, while macro
dispatcher `0xdd08` is shown as parser-table-reached rather than
direct-call-reached.

## `0xdaf0` Six-Byte Tokenizer Callers

Direct absolute `JSR 0xdaf0` callers: `0x011b28`, `0x011bdc`, `0x011c88`,
`0x011d64`, `0x011e2a`, `0x011fda`, `0x011fec`, `0x012014`, `0x01202a`,
`0x01262a`.

| Caller | Current classification |
| ---: | --- |
| `0x011b28` | main parser fallback for active callback handlers `0x11d0c` or `0x11dd2`; printable `0x60..0x7e` bytes can restart the six-byte tokenizer after the callback path has kept parser mode state alive |
| `0x011bdc` | stateful helper `0x11ba6`; punctuation-prefixed commands consume one extra host byte through `0xda9a`, tokenize the current numeric record, and arm delayed payload handler `0x1228a` for `W/w` |
| `0x011c88` | stateful helper `0x11c6c`; generic command helper tokenizes the current record, special-cases mode 4, and treats `W/w` as a delayed-payload boundary through `0x121cc(0x1228a)` |
| `0x011d64` | callback handler `0x11d0c`; lowercase payload continuations push the record cursor back by six bytes before re-entering `0xdaf0`, while uppercase final bytes restore delayed payload state |
| `0x011e2a` | callback handler `0x11dd2`; same pushed-back tokenizer restart as `0x11d0c`, followed by common font-state refresh helper `0xc580` before final delayed-payload restore |
| `0x011fda` | alternate/data parser `ESC )` wrapper `0x11fd2`; calls group setup `0x11ec8`, then tokenizes the following numeric/final record |
| `0x011fec` | alternate/data parser `ESC (` wrapper `0x11fe4`; calls group setup `0x11ec8`, then tokenizes the following numeric/final record |
| `0x012014` | normal parser `ESC )` wrapper `0x12008`; group setup `0x11ec8` and right-font setup `0x11efe` precede tokenization |
| `0x01202a` | normal parser `ESC (` wrapper `0x1201e`; group setup `0x11ec8` and left-font setup `0x11f26` precede tokenization |
| `0x01262a` | normal parser `ESC &d` handler `0x12622`; tokenizes underline/text attribute records and uses the same `W/w` delayed-payload boundary shape as the other stateful helpers |

Tokenizer contract confirmed by these callers:

- `0xdaf0` is not a standalone PCL command handler; it fills the six-byte
  parsed-record stream under `0x78299e` and leaves the final byte in record
  byte `+1`.
- Stateful parser helpers deliberately subtract six from `0x78299e` before
  re-entering `0xdaf0`; reproduction must preserve that record-cursor rewind
  because it changes which command record later payload handlers restore.
- `W/w` finals are the repeated delayed-payload boundary: callers arm
  `0x121cc(0x1228a)` before the payload reader later restores state through
  `0x12218`.

## Stateful Tokenizer Helper Variants

The focused disassembly window
`generated/disasm/ic30_ic13_tokenizer_stateful_helpers_011ba6.lst` covers the
helper bodies that the caller list previously left only partly classified.

- `0x011ba6` (punctuation-prefixed helper, tokenizer call `0x011bdc`):
Setup: If the incoming byte is `0x21..0x2f`, fetch one more host byte through
`0xda9a`, echo it through `0x9ec0`, and stop early only when that fetched byte
is space. Payload boundary: `W/w` arms delayed handler `0x1228a` through
`0x121cc`; lowercase continuation bytes `0x60..0x7e` re-enter `0xdaf0` after
rewinding the parsed-record cursor. Finalization: Terminal bytes `0x40..0x5e`
restore delayed state through `0x12218`; other terminal bytes are echoed
through `0x9ec0`.
- `0x011c6c` (generic stateful command helper, tokenizer call `0x011c88`):
Setup: Echoes the incoming command byte through `0x9ec0`, skips only space,
then tokenizes the current record. Payload boundary: `W/w` arms delayed
handler `0x1228a`; if parser mode byte `0x782999` is mode 4, the helper
bypasses that `W/w` special case and immediately rewinds the parsed-record
cursor. Finalization: Lowercase continuation bytes loop back through `0xdaf0`;
terminal bytes `0x40..0x5e` restore via `0x12218`, otherwise the byte is
echoed through `0x9ec0`.
- `0x011d0c` (callback continuation helper, tokenizer call `0x011d64`):
Setup: Lowercase bytes `0x60..0x7e` are continuation candidates; only
lowercase `w` arms delayed handler `0x1228a` before the tokenizer restart.
Payload boundary: Uppercase `W` sets an internal `D4` flag and arms the same
delayed handler before terminal processing. Finalization: In alternate/data
mode with byte `0x782a56` set, terminal bytes can append either the terminal
byte alone or a leading `0x30` plus the terminal byte through `0xe002` before
`0x12218` restores delayed state.
- `0x011dd2` (font-refreshing callback continuation helper, tokenizer call
  `0x011e2a`):
Setup: Uses the same lowercase `w` continuation and uppercase `W` terminal
delayed-payload tests as helper `0x11d0c`. Payload boundary: Uppercase `W`
rewinds `0x78299e` and calls common font-state refresh helper `0xc580` before
terminal processing. Finalization: Alternate/data terminal append behavior
matches `0x11d0c`, including the optional leading `0x30` byte before
`0x12218`.

Reproduction contract added by these variants:

- A byte-stream parser must model `0x78299e` rewind before repeated
  tokenization, because the next delayed payload or terminal handler restores
  the six-byte record that the rewind selects.
- The `0x1228a` delayed handler is not limited to raster/font `W` payloads;
  these generic helpers also arm it for `W/w` boundaries, with helper-specific
  exceptions for mode 4 and font-state refresh.

## `0xdd08` Macro Dispatcher Reachability

Direct absolute `JSR 0xdd08` callers: (none). `0xdd08` is reached through
parser dispatch table entries, not through direct `JSR` instructions.

| Table | Mode | Entry | Byte | Next mode | Meaning |
| --- | ---: | ---: | --- | ---: | --- |
| normal | 17 | `0x011268` | `0x78` / `x` | 17 | chained macro-control record |
| normal | 17 | `0x01127a` | `0x58` / `X` | 0 | terminal macro-control record |
| alternate/data | 17 | `0x0116ba` | `0x78` / `x` | 17 | chained macro-control record |
| alternate/data | 17 | `0x0116cc` | `0x58` / `X` | 0 | terminal macro-control record |

Current reproduction consequence:

- `ESC &f#x` remains in mode 17 and calls `0xdd08`; `ESC &f#X` returns to mode
  0 and calls the same handler. The alternate/data table keeps the same `x/X
  -> 0xdd08` reachability while disabling the normal `y/Y` macro-id handler,
  which matches the macro-definition payload behavior already exercised in the
  renderer harness.
