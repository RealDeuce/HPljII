# Display Functions

This note is the semantic contract for the LaserJet II `ESC Y ... ESC Z`
display-functions reader family, its alternate/data append variant, local
Control-Z siblings, and the `ESC z` display-functions-off/status edge.

Status: composed for parser dispatch through normal page-record output,
alternate/data append, and guarded `ESC z` status signaling. The low-level
ledger remains in `notes/pcl-parser-core.md`,
`notes/semantic-state-model.md`, and the generated disassembly files listed
below.

## Evidence

- `generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst`
- `generated/disasm/ic30_ic13_control_z_handlers_0120d2.lst`
- `generated/disasm/ic30_ic13_esc_e_reset_00cc52.lst`
- `generated/disasm/ic30_ic13_status_signal_helpers_009b5e.lst`
- `generated/analysis/ic30_ic13_parser_dispatch_tables.md`
- `generated/analysis/ic30_ic13_pcl_command_map.md`
- `generated/analysis/ic30_ic13_renderer_fixture_harness.md`
- `notes/pcl-parser-core.md`
- `notes/semantic-state-model.md`
- `notes/transparent-print-data.md`

Primary fixtures:

- `ESC Y display-functions stream reaches page-record output`
- `ESC Y display-functions filter-on routes controls as printable`
- `0x12120 ESC Y alternate append stores normalized display bytes`

## Field Groups

Canonical reader state:

- Local flag `D4`: zero until a routed or appended value is `ESC` (`0x1b`),
  one after `ESC`, and tested when the current value is `Z` (`0x5a`) to
  terminate the loop.
- Normalized loop value `D5`: fetched through `0xa904`, with local pair
  `0x1a 0x58` normalized to `0x7f` after `0xd99a`.
- Loop termination: `ESC Z` after normalization or `0xa904` returning `-1`.

Canonical normal-output filter state:

- `0x782f06`: selected font/context slot.
- `0x782eea + 0x10 * slot`: selected context byte copied to `D3`.
- `0x782efa`: fallback high-control filter byte used when high-character flags
  `0x783132` and `0x783133` are clear.
- Local stack word `A6-2` in `0x12536`: high-control filter word for
  `0x80..0x9f`.

Canonical append state:

- `0xe002`: macro/data-chain append sink used by alternate/data handler
  `0x12120`.
- Macro chunk `0x783988`: fixture-visible destination for the appended
  `ESC Y` prefix and normalized loop values.

Firmware bookkeeping:

- `0xd99a`: local side effect for `0x1a 0x58` control reporting.
- `0xf054`: CR post-handler called by normal handler `0x12536` after routed
  value `0x0d`.
- Control-Z handler siblings:
  - `0x120d2`: conditionally routes literal `0x1a` through printable handler
    `0xd04a` when selected context byte equals `1`.
  - `0x1210c`: appends literal `0x1a` through `0xe002`.
  - `0x1219e`: routes synthetic value `0x100` through `0xd04a`.
  - `0x121b2`: calls `0xd99a` and appends `0x7f` through `0xe002`.

Parser/data-chain guard state:

- `0x782d76`: active data-chain frame pointer. `ESC z` handler `0xcd86` reads
  frame byte `+9`.
- `0x780e2d.3`: service/status busy bit tested by `0x9c2c`.
- `0x7821cc`: service-in-progress marker set during the status signal and
  cleared before return.
- `0x7822db`: service/status marker set by `0x9c2c`.
- `0x780e2a.3`: warning/status accumulator bit ORed by
  `0x9b5e(0x780e2a, 0x8)`.

Unknown:

- Manual-facing names for `0x7821cc`, `0x7822db`, and `0x780e2a.3` remain
  inferred from status-side effects.
- External consumers of the status bit are outside this display-functions
  checkpoint.

## Writers

- Normal parser table dispatches `ESC Y` to `0x12536`.
- Alternate/data parser table dispatches `ESC Y` to `0x12120`.
- `0x1212a..0x12140` writes literal `ESC Y` through `0xe002`.
- `0x12142..0x1219c` appends normalized loop values through `0xe002` until
  `ESC Z` or no-byte termination.
- `0x1253e..0x12582` computes the normal-output selected-context byte and
  high-control filter word.
- `0x12582..0x1261e` writes visible text/fixed-space effects by calling
  `0xd04a` or `0xd0f0` for each normalized loop value.
- Both `0x12120` and `0x12536` call `0xd99a` for local `0x1a 0x58`
  normalization.
- `0xcd86` conditionally calls `0x9c2c` for `ESC z` when the active data-chain
  frame byte `+9` is zero.
- `0x9c2c` sets `0x7821cc` and `0x7822db`, calls
  `0x9b5e(0x780e2a, 0x8)`, and clears `0x7821cc`.

## Readers And Consumers

- `0xa904` supplies raw loop bytes from live input, pushback, or data-chain
  replay sources.
- `0x12120` consumes normalized loop bytes for append-only output through
  `0xe002`.
- `0x12536` consumes selected context/filter state, then routes C0 and
  high-control ranges through the same `0xd0f0` / `0xd04a` consumers used by
  transparent print data and direct text.
- `0xcd86` consumes active data-chain frame byte `+9` before the guarded
  `0x9c2c` helper boundary.
- Downstream normal-output consumers are source-object mapping, cursor/spacing
  state, page-record queueing, page-record bridge, and render entry.

## Output Effect

Alternate/data `0x12120` has no direct pixels in this checkpoint. It preserves
the display-functions byte stream by appending literal `ESC Y` and each
normalized value through `0xe002`, with `0x1a 0x58` represented as `0x7f`,
until `ESC Z`.

The alternate/data append loop is:

- `0x1212a..0x12140`: append literal `0x1b` and `0x59`.
- `0x12142..0x12168`: fetch one byte through `0xa904`; if it is `0x1a`, fetch
  one more byte and replace `0x1a 0x58` with `0x7f` after calling `0xd99a`.
- `0x1216a..0x12178`: return on `-1`, otherwise append the normalized value
  through `0xe002`.
- `0x1217a..0x12184`: if the appended value is `ESC`, set local flag `D4` and
  continue.
- `0x12186..0x12198`: if the appended value is `Z` and `D4` is set, return.
- `0x1219a..0x1219c`: otherwise clear `D4` and continue.

The byte-stream example
`0x12120 ESC Y alternate append stores normalized display bytes` exercises
payload `21 1a 58 1b 5a`; the recorded append stream is
`1b 59 21 7f 1b 5a` in macro chunk `0x783988`.

Normal `0x12536` can produce pixels or fixed spacing. Values `0x00..0x1f`
route through `0xd0f0` only when selected context byte `D3` is zero. Values
`0x80..0x9f` route through `0xd0f0` only when the high-control filter word is
zero. All other values route through `0xd04a`.

The normal-output loop is:

- `0x1253e..0x12582`: compute selected context byte `D3` from
  `0x782eea + 0x10 * 0x782f06`, then choose local high-control filter word
  `A6-2` from `0x782efa` or `D3` according to high-character flags
  `0x783132` and `0x783133`.
- `0x12582..0x125aa`: fetch through `0xa904` and normalize local
  `0x1a 0x58` to `0x7f`.
- `0x125aa..0x125b0`: return on no-byte `-1`.
- `0x125b2..0x125c4`: route C0 values through `0xd0f0` when `D3` is zero.
- `0x125c6..0x125e2`: route `0x80..0x9f` values through `0xd0f0` when
  `A6-2` is zero.
- `0x125e4..0x125e6`: pass all other values to `0xd04a`.
- `0x125ec..0x125f4`: after routed CR (`0x0d`), call `0xf054`.
- `0x125fa..0x1261e`: maintain the local `ESC`/`Z` termination flag and loop.

Normal-route matrix:

- C0 values `0x00..0x1f`, selected context byte `0`: route through
  `0xd0f0`, so they can advance spacing without queueing a compact text entry.
- C0 values `0x00..0x1f`, selected context byte nonzero: route through
  `0xd04a`, so they are printable display-function bytes.
- High-control values `0x80..0x9f`, high-control filter word `0`: route
  through `0xd0f0`.
- High-control values `0x80..0x9f`, high-control filter word nonzero: route
  through `0xd04a`.
- Values outside those two ranges route through `0xd04a`.
- A terminating `ESC Z` pair is still consumed as routed values before the
  local `ESC`/`Z` state ends the loop.

Local Control-Z terminal behavior is table-dependent and comes from the
mode-2 dispatch rows in
`generated/analysis/ic30_ic13_parser_dispatch_tables.md` and
`generated/analysis/ic30_ic13_pcl_command_map.md`:

- Normal parser mode 0 sees byte `0x1a`, dispatches setup handler `0x11ea4`,
  and enters mode 2. In mode 2, byte `0x1a` dispatches `0x120d2`; byte `X`
  dispatches `0x1219e`.
- Alternate/data parser mode 0 uses the same `0x11ea4` setup, but its mode-2
  table dispatches byte `0x1a` to `0x1210c` and byte `X` to `0x121b2`.

The four local terminal handlers do not share one global Control-Z meaning:

- `0x120d2..0x1210a`: normal nested `0x1a`. The handler reads selected slot
  byte `0x782f06`, calls `0x332ee(slot, 0x10)`, adds base `0x782eeb`, and tests
  that context byte. Only value `1` calls `0xd04a(0x1a)` at
  `0x120fc..0x12106`; other values return with no page object.
- `0x1219e..0x121b0`: normal `0x1a X`. The handler calls `0xd04a(0x100)` and
  returns. This is a printable-path synthetic value, not a byte appended to the
  macro/data chain.
- `0x1210c..0x1211e`: alternate/data nested `0x1a`. The handler calls
  `0xe002(0x1a)` and returns, preserving the literal byte in the append sink.
- `0x121b2..0x121ca`: alternate/data `0x1a X`. The handler calls `0xd99a`,
  then `0xe002(0x7f)`, matching the `ESC Y` local normalization of `0x1a 0x58`
  to `0x7f` in append-only contexts.

The canonical state for this local family is the parser mode/table row plus
the selected context byte used only by `0x120d2`. The derived/cache state is
the slot product returned by `0x332ee`. Firmware bookkeeping is `0xd99a` on the
alternate/data `0x1a X` terminal. Output effect is either printable-path entry
through `0xd04a`, macro/data-chain append through `0xe002`, or no output for
the false branch of `0x120d2`.

Byte-stream example `ESC Y display-functions stream reaches page-record
output` exercises the default-filter normal path for `ESC Y!\x05! ESC Z`:
handler `0x12536` consumes values `21 05 21 1b 5a`, routes them
`d04a d0f0 d04a d0f0 d04a`, and queues visible `!`, `!`, and `Z` entries at
compact coords `0x0001`, `0x0403`, and `0x0405`.

Byte-stream example `ESC Y display-functions filter-on routes controls as
printable` exercises the complementary normal branch. With selected-context
byte `1` and high-control filter `1`, stream `ESC Y\x05\x80\x1aX! ESC Z`
normalizes `0x1a 0x58` to `0x7f`, routes values `05 80 7f 21 1b 5a` through
`0xd04a`, and queues six compact entries with object prefix
`00 00 00 00 00 00 00 06 04 0b 00 7f 0e 01 7e 1f 02 20 06 04 1a 53 05 59 06
06`.

`ESC z` has no direct page-record output in this checkpoint. Its ROM effect is
the guarded status path at `0xcd86..0xcda0`: if active frame byte `+9` is zero,
`0x9c2c` waits for `0x780e2d.3` to clear, sets `0x7821cc` and `0x7822db`, ORs
bit `0x8` into `0x780e2a` through `0x9b5e`, clears `0x7821cc`, and returns.
If frame byte `+9` is nonzero, it returns without signaling.

## Reproduction Contract

A byte-stream renderer must preserve:

- `ESC Y` as a reader loop that consumes subsequent bytes until normalized
  `ESC Z` or no-byte return;
- local `0x1a 0x58 -> 0x7f` normalization inside this reader;
- alternate/data behavior that appends literal `ESC Y` plus normalized loop
  bytes through the macro/data append sink;
- normal behavior that routes default-filtered C0 and high-control bytes
  through fixed-space handling;
- normal behavior that routes the same ranges through printable text when the
  selected context/filter state is nonzero;
- the fact that terminating `ESC Z` bytes participate as routed/appended
  values before the loop terminates;
- `ESC z` as a guarded status/service edge, not a text-rendering command.

## Confidence

High for loop termination, local normalization, alternate append, normal
default-filter route, normal filter-on printable route, and page-record output
because the claims are backed by disassembly `0x12120..0x1219c`,
`0x12536..0x1261e`, the `0xd04a`/`0xd0f0` consumers, and the named byte-stream
examples above. Those examples exercise the branch interpretation; they are not
an external rendered-output oracle.

High for the `ESC z` guard and `0x9c2c` call boundary because they are direct
disassembly reads. Medium for the manual-facing names and external consumers
of the status bits.

## Remaining Edges

- No ROM middle edge remains for the `0x12536..0x1261e` normal page-output
  loop, the `0x12120..0x1219c` alternate/data append loop, the local
  Control-Z sibling handlers, or the `0xcd86 -> 0x9c2c` display-functions-off
  status boundary.
- Remaining display-functions work is optional physical/reference correlation
  and external status-consumer naming, not parser or renderer discovery.
