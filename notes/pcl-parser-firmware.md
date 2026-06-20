# PCL Parser Firmware Notes

Sources: `generated/disasm/ic30_ic13_host_byte_fetch_00a904.lst`; `generated/disasm/ic30_ic13_main_parser_loop_011774.lst`; `generated/disasm/ic30_ic13_pcl_escape_parser_00da9a.lst`; `generated/disasm/ic30_ic13_esc_e_reset_00cc52.lst`; `generated/disasm/ic30_ic13_esc_e_metric_refresh_00cbd4.lst`; `generated/disasm/ic30_ic13_esc_e_environment_reset_00cda2.lst`; `generated/disasm/ic30_ic13_esc_e_parser_state_reset_00e146.lst`; `generated/disasm/ic30_ic13_control_code_handlers_00f02c.lst`; `generated/analysis/ic30_ic13_host_byte_fetch_flow.md`; `generated/analysis/ic30_ic13_direct_control_code_flow.md`; `generated/analysis/ic30_ic13_esc_e_reset_flow.md`; `generated/analysis/ic30_ic13_parser_dispatch_tables.md`; `generated/analysis/ic30_ic13_parser_xrefs.md`; `generated/analysis/ic30_ic13_cmpi_byte_candidates.md`.

These are current anchors for the path from host bytes into PCL command records. Names are provisional until caller/callee cross-references are broader.

## Host Byte Fetch Anchor

`generated/analysis/ic30_ic13_host_byte_fetch_flow.md` now splits routine `0x0000a904` into a priority-ordered normalized byte source. It returns the next input byte in `D7`, or `D7=-1` in the one immediate no-byte/error branch where `0x780e66` and `0x780e3b` are both set. It checks several buffered sources first:

- State flag `0x7821cd`.
- Mode/status flag `0x780e66`.
- Pushback-like buffer count/pointer at `0x783e8c` / `0x783e8e`.
- Current data chain pointer at `0x782d76`.
- Another buffer count/pointer at `0x783e76` / `0x783e78`.
- Ring-buffer-looking count/pointer at `0x783e54` / `0x783e56`, wrapping between `0x783a4c` and `0x783e53`.

One direct hardware input path starts at `0x0000a9f0` when mode selector `0x780e40 == 1`:

1. Polls `0x8e01` until bit `0x10` is set, with timeout counter `0x2710`.
2. Reads input byte from `0x8801` into `D7`.
3. If byte is `0x1a`, echoes/logs it through routine `0x9ec0` and keeps `D7 = 0x1a`.
4. Waits for bit 0 of `0x8c01` to clear.
5. Toggles output/control registers including `0xa601`, `0xaa01`, and state byte `0x7828fa`.

A second direct input path starts at `0x0000aaa6` when `0x780e40` is nonzero but not `1`. It polls `0xfffee005`, treats bit 0 as data-ready, ORs status bits 7 and 6 into `0x780e2e` as `0x80` and `0x40`, reads the byte from `0xfffee001`, and writes handshake shadow `0x7828fb` to `0xfffee009`. The cleanup helper at `0xab8e` is called from `0x35de` and normalizes either the `0xaa01`/`0xa601` mode-1 handshake or the `0xfffee009` mode-2 handshake with the literal `bclr #0x40,D0` operation seen at `0xabe0`.

Current interpretation: these are host-interface or formatter I/O status/data registers. The ROM evidence proves polling/data/handshake behavior, but the exact physical interface names still need board or manual correlation.

`tools/render_fixture_harness.py` now includes executable `0xa904` source-priority fixtures. They cover the immediate `D7=-1` branch, pending service retry, first LIFO priority, data-chain end-marker retry into the second LIFO source, ring-buffer priority while `0x780e40 == 0`, and both direct hardware paths including direct-mode `0x1a` reporting through `0x9ec0` and mode-2 control-shadow bit 6.

## ESC Byte Handling

Routine `0x0000da9a` calls the byte fetch routine at `0xa904` and returns the next byte in `D7`, with special handling for escape-like sequences:

- Compares fetched byte to `0x1b` (`ESC`).
- If the next byte after `ESC` is not `0x3f` (`?`), it pushes/logs that byte through `0x9ec0` and returns `D7 = 0x1b`.
- If it sees `ESC ? 0x11`, it skips that sequence and resumes fetching.

Routine `0x0000dace` recognizes `0x1a 0x58` and calls `0xd99a`. This may be host-control or job-control behavior, not enough is known yet to name it.

## Escape Sequence Tokenizer

Routine `0x0000daf0` builds escape-command records using:

- byte source function pointer `A3 = 0x0000da9a`;
- record cursor/root pointer at `0x78299e`;
- scratch text/parameter buffer at `0x782a42`;
- six-byte records advanced by `+6` in the tokenizer phase.

Observed behavior:

- Parses bytes in the PCL parameter/intermediate range `0x20..0x3f`.
- Handles `<...>` bracketed spans specially in helper `0x0000db46`.
- Skips leading spaces.
- Accepts optional `+` or `-`.
- Parses up to six decimal integer digits into word field `record+2`.
- Parses an optional fractional part after `.` with up to four digits into word field `record+4`.
- Stores the terminating byte at `record+1`.
- Treats `:` and `;` as command-combining continuation markers by returning `D7 = 0`.

This matches PCL escape syntax closely enough to treat `0xdaf0`/`0xdb74` as the first confirmed PCL tokenizer anchor.

## Main Parser Loop

Routine `0x00011774` is the current main parser loop anchor. It initializes:

- `0x78299a` to handler `0x00011b8e`;
- `0x78299e` to tokenizer record cursor `0x7829a2`;
- `0x782a26` to `0x782a2a`;
- `0x782a3e` to text/parameter scratch buffer `0x782a42`;
- local text accumulation region `0x783196..0x783199`.

The loop repeatedly calls `0x0000da9a`, keeps the fetched byte in `D5`, and dispatches through a mode-indexed six-byte table:

```text
byte_to_match, next_mode, handler_long
```

Normal parser pointer table: `0x000112a4`.
Alternate/data parser pointer table: `0x000116f6`.

Current parser mode is stored at `0x782999`. If `0x782c18` is clear, the normal table is used. If `0x782c18` is set, the alternate/data table is used; that table preserves state transitions but suppresses many command handlers, consistent with a data collection or macro/download mode.

## Direct Control Codes

Normal mode 0 has these direct control-code entries:

| Byte | Meaning | Handler |
| --- | --- | --- |
| `0x1b` | `ESC` | next mode 1, setup handler `0x011eb6` |
| `0x1a` | control-Z-style host control | next mode 2, setup handler `0x011ea4` |
| `0x0f` | SI | `0x00c68a` |
| `0x0e` | SO | `0x00c6b8` |
| `0x0d` | CR | `0x00f02c` |
| `0x0c` | FF | `0x00f0f0` |
| `0x0b` | VT | no handler in table |
| `0x0a` | LF | `0x00f08c` |
| `0x09` | HT | `0x00f1cc` |
| `0x08` | BS | `0x00f2a8` |
| `0x07` | BEL | no handler in table |
| `0x00` | NUL | no handler in table |

`generated/analysis/ic30_ic13_direct_control_code_flow.md` now traces these handlers into cursor/page-visible side effects. The line-termination command `ESC &k#G` writes bit patterns to `0x78318f`: `0` stores `0x00`, `1` stores `0x80`, `2` stores `0x60`, and `3` stores `0xe0`. CR tests bit 7 to optionally also advance vertically, LF tests bit 6 to optionally also reset horizontally, and FF tests bit 5 to optionally also reset horizontally before page finalization.

The CR/LF/FF/HT/BS handlers update state around `0x782c8a`, `0x782c8e`, `0x782dd6`, `0x782dda`, `0x78315c`, `0x783160`, and `0x78318f`, with helper calls into the coordinate arithmetic block around `0x104d8..0x10518`. They can also flush text spans through `0x12714` / `0x126e2`, ensure/finalize page roots through `0x10084` / `0xff1e`, and update active font context spans through `0xd4ac` / `0xd8fc`.

`tools/render_fixture_harness.py` now has synthetic packed-state fixtures for the `ESC &k#G` bit map plus CR/LF/FF/HT/BS cursor/page effects. It also has narrow byte-stream fixtures for `ESC &k1G` followed by CR, `ESC &k2G` followed by LF, and `ESC &k0G` followed by HT/BS. A mixed stream fixture now drives `ESC &k1G`, printable `!`, CR, printable `!` through one modeled pass, proving that the stored line-termination mode applies before the second printable byte is positioned; a page-record variant queues the same printable bytes through `0x1387c` and bridges them through `0x1edc6`. A second mixed fixture drives printable `!` followed by `ESC E`, proving reset publication/clear state after a queued text object in the same byte-stream model; its page-record variant queues the glyph through `0x1387c` and bridges it through `0x1edc6`. These prove the direct-control/reset subset from actual PCL/control bytes, but they still need to be broadened into the full firmware parser path with real page-object allocation.

For normal printable text, the harness now drives a one-byte stream `0x21` (`!`) through the modeled `0x1393a` source-object builder, `0xd824` positioning handoff, `0x12f2e` compact queue producer, and compact-glyph renderer. It also has a two-byte `!!` fixture that advances the packed horizontal cursor through the simple `0xd550` default-advance branch between bytes and combines the two entries into one short compact text object. The initialized `LINE_PRINTER` metric fixture derives HMI `0x00120000` from resource longword `0x00480000` through the `0x10550` conversion path and renders the second glyph from compact coord `0x0202`, which `0x1f3d4` decodes as `$a001 = 0x12` / pixel x `34`. The mixed `ESC &k1G!\r!` fixture queues the post-CR glyph at coord `0x3b00` / `$a001 = 0x1b`, records that blank shifted rows clear the full byte span `x=11..18`, and now has a page-record allocator/bridge variant for the same stream; the mixed `!\x1bE` fixture keeps the pre-reset glyph renderable, publishes/clears the valid current page root through reset, and now has a page-record allocator/bridge variant for the same stream. `0x1387c` allocator fixtures now queue short compact objects and segmented tall-glyph objects under the page-record bucket-array shape, and a `0x1edc6` bridge fixture copies that compact bucket/context slot into render-record shape, pins the rule/fixed-list normalization side effects, and includes producer-shaped `0x13386`/`0x136d2` rule-list objects. This is still a narrow normal-mode fixture, not a full parser state emulator.

## Top-Level ESC Dispatch

After `ESC`, parser mode 1 maps bytes to command families:

| Sequence | Next mode | Handler |
| --- | ---: | --- |
| `ESC E` | 0 | `0x00cc52` |
| `ESC *` | 3 | `0x011ec8` |
| `ESC )` | 4 | `0x012008` |
| `ESC (` | 4 | `0x01201e` |
| `ESC &` | 5 | `0x011ec8` |
| `ESC =` | 0 | `0x00f176` |
| `ESC 9` | 0 | `0x00e9ba` |
| `ESC z` | 0 | `0x00cd86` |
| `ESC Y` | 0 | `0x012536` |

`generated/analysis/ic30_ic13_esc_e_reset_flow.md` now traces `ESC E` beyond the top-level dispatch. `0x00cc52` calls `0x00cc70`, `0x00cbd4`, and `0x00e146`, then clears `0x782a93`. `0xcc70` flushes pending text spans, calls page-root finalizer `0xff1e`, waits for active page/control records through `0x9ac2`, rebuilds page/environment state, and reinitializes raster block `0x783170`. `0xcbd4` refreshes HMI/default text motion and active symbol snapshots from current-font context state. `0xe146` resets parser/data-chain state, clears transient parser records and text accumulation bytes, and prunes command/data pool records. This is the firmware anchor for PCL software reset and its partial-page finalization behavior.

`tools/render_fixture_harness.py` now has synthetic `ESC E` byte-stream fixtures for both reset page-root cases: valid roots are published before the current root is cleared, while missing/invalid roots clear without publication. The mixed `!\x1bE` fixture exercises that valid-root reset path after queuing a printable text object, and its page-record variant queues and bridges that object under page-record storage rules. The `0x1387c` allocator fixtures queue short and segmented compact buckets under page-record storage rules, and the `0x1edc6` bridge fixture proves the render-record copy contract for that compact bucket. These fixtures still need parser-produced page objects before they can prove the full firmware reset path.

## Parsed-Command Dispatch

After tokenization, routine `0x0000dd08` uses the parameter value from `record+2`, compares it with current state at `0x783164`, and jumps through a table at `0x0000dca8` via common dispatch helper `0x00033298`.

The table maps selector values to handlers:

| Selector | Handler |
| ---: | --- |
| 10 | `0x0000df36` |
| 9 | `0x0000df24` |
| 8 | `0x0000df12` |
| 7 | `0x0000df08` |
| 6 | `0x0000defe` |
| 5 | `0x0000def4` |
| 4 | `0x0000dec8` |
| 3 | `0x0000dea2` |
| 2 | `0x0000de7c` |
| 1 | `0x0000ddfc` |
| 0 | `0x0000dd86` |

The selector-1 handler checks an already-tokenized byte sequence for:

```text
ESC & f
```

Specifically, it checks bytes at offsets `+4`, `+5`, and `+6` from a command/data pointer for `0x1b`, `0x26`, and `0x66`. This is an important PCL macro-control lead because `ESC & f` is the PCL macro command family.

Top-level `ESC &` enters mode 5. The normal table currently identifies these subfamilies:

| Prefix | Next mode | Handler |
| --- | ---: | --- |
| `ESC &s` | 8 | `0x011eda` |
| `ESC &p` | 9 | `0x011eda` |
| `ESC &l` | 10 | `0x011eda` |
| `ESC &k` | 11 | `0x011eda` |
| `ESC &f` | 17 | `0x011eda` |
| `ESC &d` | 0 | `0x012622` |
| `ESC &a` | 12 | `0x011eda` |

This matches high-value PCL areas: page/layout (`&l`), font/text attributes (`&k`, `&d`), cursor positioning (`&a`), and macros (`&f`).

## Record Pools and Output Chains

The parser uses a pool of 32 records at `0x782a98`, each apparently 12 bytes long:

- `0xdf4e` clears all 32 records by repeatedly calling `0xdfba`.
- `0xdf80` clears only records whose byte at offset `+0x0a` is zero.
- `0xdfba` clears fields at `+4`, `+8`, `+0x0a`, frees a `0x100` byte allocation via `0x18b4`, and clears the record pointer.
- `0xe002` appends a byte to a current data chain, allocating `0x100` byte chunks through `0x170c` as needed.
- `0xe0a4` finds or allocates a record in the 32-entry pool keyed by a word at offset `+8`.

These structures need full naming, but they are already concrete enough to drive PCL parser fixture work.

## Rejected Lead

The `cmpi.w #0x000c` at `0x0001053a` is not the PCL form-feed handler. The surrounding code is arithmetic/modulo-style helper code and hexadecimal/decimal formatting, so it should not be used as a control-code anchor.

## Next RE Targets

- Find callers of `0xdaf0` and `0xdd08`, and keep expanding the named roles for the `0xa904` callers listed in `generated/analysis/ic30_ic13_host_byte_fetch_flow.md`.
- Decode all normal and alternate parser table handlers into PCL command names.
- Decode the six-byte tokenizer records and 12-byte command/data pool records.
- Follow `ESC & f` handling into macro definition/execution state.
- Replace the synthetic `ESC E` fixtures with fixtures that start from parser-produced page objects and prove the `0xff1e` finalization/publication path before reset clears the current page root.
- Extend the mixed-stream page-record fixture into real parser-produced page-object allocation/finalization, then add one macro command once handler destinations are named.
