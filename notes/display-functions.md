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

## Owner Summary

Concept: this note owns the `ESC Y ... ESC Z` display-functions reader
family, its alternate/data append form, local Control-Z terminal siblings, and
the `ESC z` display-functions-off/status edge. It documents how those parser
terminals either feed ordinary text imaging, preserve bytes for macro/data
replay, emit local Control-Z variants, or touch status state without creating
a page object.

Primary route:

- Parser dispatch selects normal `ESC Y` handler `0x12536` or alternate/data
  `ESC Y` handler `0x12120` from the command tables documented in
  [pcl-command-map.md](pcl-command-map.md#owner-summary).
- Both handlers read loop bytes through host source `0xa904` and terminate on
  no-byte return or the local normalized `ESC Z` pair.
- Normal reader route:
  `0x12536 -> 0xa904 -> local 0x1a 0x58 normalization -> 0xd0f0/0xd04a
  -> direct-control printable path -> page-record storage -> render`.
- Alternate/data route:
  `0x12120 -> 0xe002(ESC) -> 0xe002(Y) -> 0xa904 loop -> local
  0x1a 0x58 normalization -> 0xe002(value)` until local `ESC Z`.
- Local Control-Z parser terminals route through `0x120d2`, `0x1210c`,
  `0x1219e`, or `0x121b2`; their output is either printable text through
  `0xd04a`, append-only bytes through `0xe002`, or no output.
- `ESC z` handler `0xcd86` is a guarded status edge: it reads active data-chain
  frame byte `+9` and can call status helper `0x9c2c`, but it does not create
  a page record.

Field groups:

- Canonical filter state: selected font slot `0x782f06`, C0 filter byte
  `0x782eea + 0x10 * slot`, fallback high-control filter byte `0x782efa`,
  and high-character flags `0x783132` / `0x783133`.
- Canonical append state: append sink `0xe002` and macro/data chunk
  destination visible at `0x783988` in the alternate append fixture.
- Canonical status state: active data-chain frame pointer `0x782d76`, service
  busy bit `0x780e2d.3`, markers `0x7821cc` and `0x7822db`, and warning bit
  `0x780e2a.3`.
- Derived/cache: local high-control filter word at `A6-2`, selected-context
  slot product from `0x332ee`, normalized loop value `D5`, and normalized
  `0x7f` value produced from local `0x1a 0x58` pairs after `0xd99a`.
- Parser/direct-reader scratch: local `D4` ESC-before-Z flag, selected
  termination on local `ESC Z` or `0xa904 == -1`, mode-2 local Control-Z
  dispatch rows, and command records that route bytes to `0x120d2`, `0x1210c`,
  `0x1219e`, or `0x121b2`.
- Firmware bookkeeping: `0xd99a` reporting/normalization side effect and
  status helper `0x9c2c`.
- Unknown: manual-facing names for status latches are unknown; their ROM-local
  writes and consumers are the `0xcd86 -> 0x9c2c -> 0x9b5e` boundary.

Writers and readers:

- `0x12536` reads host bytes and filter fields, then calls `0xd0f0` for
  default-filter fixed-space handling or `0xd04a` for printable imaging.
- `0x12120` writes literal `ESC Y` and normalized payload bytes through
  `0xe002`.
- `0x120d2` conditionally calls `0xd04a(0x1a)` after reading the selected
  Control-Z context byte; `0x1219e` always calls `0xd04a(0x100)`.
- `0x1210c` writes literal `0x1a` through `0xe002`; `0x121b2` calls `0xd99a`
  and writes normalized `0x7f` through `0xe002`.
- `0xcd86` reads data-chain frame state; `0x9c2c` writes status markers and
  calls `0x9b5e(0x780e2a, 0x8)`.
- Downstream consumers are the direct-control printable/fixed-space owner,
  macro/data-chain replay owner, page-record storage owner, and active render
  owner.

Output effect:

- Normal `ESC Y` can create compact text objects because its routed bytes enter
  `0xd04a`; default-filtered control ranges can instead enter fixed-space
  handler `0xd0f0`.
- The normal routed-text page-image boundary is the shared compact path:
  `0xd04a -> 0x1393a -> 0xd140/0xd550 -> 0x12f2e -> 0x1387c` queues a
  compact bucket object under current root `+0x1c`. The compact object carries
  selector/context/count fields in `+0x04/+0x05/+0x06/+0x08` and payload
  entries beginning at `+0x0a`; bridge `0x1ed84 -> 0x1edc6` later copies root
  `+0x1c` to render root `+0x18`, and render entry `0x1ef6a -> 0x1efc2 ->
  0x1effe` selects the compact glyph/fixed-space helper.
- Alternate/data `ESC Y` creates no immediate pixels. It preserves bytes in
  the append sink for later macro/data-chain replay.
- Local Control-Z terminals are table-dependent; they are not one global
  control code. Each terminal's page, append, or no-output behavior is listed
  below with its exact handler address.
- `ESC z` creates no page object and no pixels; its observable ROM effect is
  the guarded status-marker path.

Evidence and boundaries:

- Disassembly evidence is in
  `generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst`,
  `generated/disasm/ic30_ic13_control_z_handlers_0120d2.lst`, and
  `generated/disasm/ic30_ic13_status_signal_helpers_009b5e.lst`.
- Generated table evidence is in
  `generated/analysis/ic30_ic13_parser_dispatch_tables.md` and
  `generated/analysis/ic30_ic13_pcl_command_map.md`.
- Fixture evidence is named in the Primary fixtures list above; those streams
  pin the normal page-record route, filter-on printable route, and alternate
  append route.
- No unresolved ROM-local middle edge remains inside `0x12536..0x1261e`,
  `0x12120..0x1219c`, the local Control-Z handlers, or the
  `0xcd86 -> 0x9c2c` status boundary.
- Remaining boundaries are external status-consumer naming and any physical
  interpretation of the status bits, not parser, page-record, or render
  routing.

## Display Functions Decision Checkpoint

This checkpoint composes the display-functions family from parser dispatch to
its possible output classes. It starts when the parser table selects `ESC Y`,
local Control-Z, or `ESC z`, and ends with routed text/fixed-space output,
stored append bytes, local Control-Z behavior, or status signaling.

Decision route:

- Normal display reader: normal parser mode `1` maps `ESC Y` to `0x12536`.
  The handler reads loop bytes directly through `0xa904`, normalizes local
  `0x1a 0x58` to `0x7f`, routes each value through `0xd04a` or `0xd0f0`, and
  returns only after routed `ESC Z` or no-byte return.
- Alternate/data display reader: alternate/data parser mode `1` maps `ESC Y`
  to `0x12120`. The handler appends literal `ESC Y`, then appends normalized
  loop values through `0xe002` until appended `ESC Z` or no-byte return.
- Local Control-Z terminals: mode-2 dispatch is table-dependent. Normal
  `0x1a 0x1a` calls `0x120d2`, normal `0x1a X` calls `0x1219e`,
  alternate/data `0x1a 0x1a` calls `0x1210c`, and alternate/data `0x1a X`
  calls `0x121b2`.
- Display-functions off/status: parser `ESC z` reaches `0xcd86`. It reads
  active data-chain frame byte `+9`; only the guarded zero case calls
  `0x9c2c`, which writes status markers and ORs `0x780e2a.3`.

State classification:

- Canonical reader state: local previous-ESC flag `D4`, normalized value `D5`,
  direct loop source `0xa904`, and local termination on normalized `ESC Z`.
- Canonical filter/text state: selected slot `0x782f06`, C0 filter byte
  `0x782eea + 0x10 * slot`, fallback high-control filter `0x782efa`,
  high-character flags `0x783132` / `0x783133`, and text/page state consumed by
  `0xd04a` or `0xd0f0`.
- Canonical append state: append sink `0xe002` and macro/data-chain storage
  used by `0x12120`, `0x1210c`, and `0x121b2`.
- Canonical status state: active data-chain frame pointer `0x782d76`, service
  busy bit `0x780e2d.3`, status markers `0x7821cc` / `0x7822db`, and warning
  bit `0x780e2a.3`.
- Derived/cache state: selected-slot product from `0x332ee`, local high-control
  filter word at `A6-2`, and normalized `0x7f` after `0xd99a`.
- Parser scratch: mode-1 and mode-2 command-table state while dispatching
  `ESC Y`, local Control-Z, or `ESC z`.
- Firmware bookkeeping: `0xd99a`, `0xf054` after routed CR, and the status
  helper `0x9c2c`.
- Unknown: manual-facing names and physical consumers for the status bits
  written by `0xcd86 -> 0x9c2c`.

Writers, readers, and output effect:

- Writers are `0x12536` for routed display-loop output, `0x12120` for
  append-only display-loop bytes, `0x120d2` / `0x1219e` for normal local
  Control-Z page-output variants, `0x1210c` / `0x121b2` for alternate append
  variants, and `0xcd86 -> 0x9c2c` for status markers.
- Readers and consumers are `0xa904` for loop bytes, filter fields
  `0x782eea` / `0x782efa` / `0x783132` / `0x783133`, Control-Z context byte
  `0x782eeb + 0x10 * slot`, append sink `0xe002`, printable/fixed-space
  consumers `0xd04a` / `0xd0f0`, and status accumulator `0x780e2a`.
- Visible output comes only from normal routed values that reach `0xd04a` or
  from fixed-space effects through `0xd0f0`; alternate/data paths store bytes
  for later replay, and `ESC z` is status-only.
- Page objects and pixels are downstream of the compact route
  `0xd04a -> 0x1393a -> 0x12f2e -> 0x1387c`, publication `0xff1e`, bridge
  `0x1ed84 -> 0x1edc6`, and render dispatch `0x1ef6a -> 0x1efc2 ->
  0x1effe`. Alternate append paths do not touch those roots until replayed
  bytes re-enter the normal parser route through `0xa904`.

Evidence and unresolved boundary:

- Parser-table evidence is
  `generated/analysis/ic30_ic13_parser_dispatch_tables.md` and
  `generated/analysis/ic30_ic13_pcl_command_map.md`.
- Reader and local-terminal evidence is
  `generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst` and
  `generated/disasm/ic30_ic13_control_z_handlers_0120d2.lst`.
- Status evidence is
  `generated/disasm/ic30_ic13_status_signal_helpers_009b5e.lst`.
- Fixture evidence is `ESC Y display-functions stream reaches page-record
  output`, `ESC Y display-functions filter-on routes controls as printable`,
  and `0x12120 ESC Y alternate append stores normalized display bytes`.
- No ROM-local middle edge remains for the documented `ESC Y` readers, local
  Control-Z terminals, or `ESC z` status route. Remaining work is external
  status-consumer naming or new byte streams that expose different filter,
  append, page-object, or status fields.

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
- `0x782eea + 0x10 * slot`: selected-context C0 filter byte copied to `D3`.
  In normal display-functions loop `0x12536`, zero routes C0 values through
  `0xd0f0`; nonzero routes them through `0xd04a`.
- `0x782efa`: fallback high-control filter byte used when high-character flags
  `0x783132` and `0x783133` are clear. In `0x12536`, zero routes
  `0x80..0x9f` values through `0xd0f0`; nonzero routes them through `0xd04a`.
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
    `0xd04a` when the Control-Z context byte equals `1`.
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
- `0x1253e..0x12582` computes the normal-output selected-context C0 filter byte
  and high-control filter word.
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
route through `0xd0f0` only when selected-context C0 filter byte `D3` is zero.
Values `0x80..0x9f` route through `0xd0f0` only when the high-control filter
word is zero. All other values route through `0xd04a`.

The normal-output loop is:

- `0x1253e..0x12582`: compute selected-context C0 filter byte `D3` from
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

- C0 values `0x00..0x1f`, selected-context C0 filter byte `0`: route through
  `0xd0f0`, so they can advance spacing without queueing a compact text entry.
- C0 values `0x00..0x1f`, selected-context C0 filter byte nonzero: route through
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
the `0x782eeb + 0x10 * slot` Control-Z context byte used only by `0x120d2`.
That byte is separate from the `0x782eea + 0x10 * slot` C0 filter byte used by
normal `ESC Y` loop `0x12536`. The derived/cache state is the slot product
returned by `0x332ee`. Firmware bookkeeping is `0xd99a` on the alternate/data
`0x1a X` terminal. Output effect is either printable-path entry through
`0xd04a`, macro/data-chain append through `0xe002`, or no output for the false
branch of `0x120d2`.

Byte-stream example `ESC Y display-functions stream reaches page-record
output` exercises the default-filter normal path for `ESC Y!\x05! ESC Z`:
handler `0x12536` consumes values `21 05 21 1b 5a`, routes them
`d04a d0f0 d04a d0f0 d04a`, and queues visible `!`, `!`, and `Z` entries at
compact coords `0x0001`, `0x0403`, and `0x0405`.

Byte-stream example `ESC Y display-functions filter-on routes controls as
printable` exercises the complementary normal branch. With selected-context
C0 filter byte `1` and high-control filter `1`, stream
`ESC Y\x05\x80\x1aX! ESC Z`
normalizes `0x1a 0x58` to `0x7f`, routes values `05 80 7f 21 1b 5a` through
`0xd04a`, and queues six compact entries with object prefix
`00 00 00 00 00 00 00 06 04 0b 00 7f 0e 01 7e 1f 02 20 06 04 1a 53 05 59 06
06`.

`ESC z` has no direct page-record output in this checkpoint. Its ROM effect is
the guarded status path at `0xcd86..0xcda0`: if active frame byte `+9` is zero,
`0x9c2c` waits for `0x780e2d.3` to clear, sets `0x7821cc` and `0x7822db`, ORs
bit `0x8` into `0x780e2a` through `0x9b5e`, clears `0x7821cc`, and returns.
If frame byte `+9` is nonzero, it returns without signaling.

## Display-Functions Outcome Matrix

This matrix is the owner-level routing table for display-functions streams.
It preserves the low-level handler ledger above while making the semantic
outcome explicit: each accepted parser route either feeds ordinary page/text
output, writes macro/data append bytes for later replay, or updates status
state with no page object.

- Normal `ESC Y` reader, default-filtered controls:
  parser mode 1 dispatches `ESC Y` to `0x12536`. The loop reads bytes through
  `0xa904`, normalizes local `0x1a 0x58` to `0x7f` after `0xd99a`, and routes
  values through `0xd0f0` when they are C0 bytes and
  `0x782eea + 0x10 * 0x782f06` is zero, or high-control bytes and the local
  high-control filter word is zero. Output is fixed-space/text-state behavior,
  not a compact printable entry for those filtered values; later visible
  placement is owned by the direct-control printable/fixed-space path.
- Normal `ESC Y` reader, printable values:
  the same `0x12536` loop routes all non-filtered values through `0xd04a`.
  This includes ordinary printable bytes, C0 bytes when the selected C0 filter
  byte is nonzero, high-control bytes when the high-control filter word is
  nonzero, local `0x1a 0x58` represented as `0x7f`, and the terminating
  `ESC Z` pair before the local flag exits the loop. The downstream consumer
  path is `0xd04a -> 0x1393a -> 0x12f2e -> 0x1387c`, then publication and
  render through `0xff1e -> 0x1ed84 -> 0x1edc6 -> 0x1ef6a`.
- Alternate/data `ESC Y` reader:
  alternate/data mode dispatches `ESC Y` to `0x12120`. The handler writes
  literal `ESC Y` through `0xe002`, then appends each normalized loop value
  through `0xe002` until local `ESC Z` or no-byte return. The canonical state
  is the append sink and macro/data storage, not page-root state; pixels can
  appear only if later data-chain replay feeds those stored bytes back through
  `0xa904`.
- Normal local Control-Z, nested `0x1a`:
  mode-2 dispatch sends `0x1a 0x1a` to `0x120d2`. The handler reads selected
  slot `0x782f06`, derives `0x10 * slot` through `0x332ee`, and tests
  context byte `0x782eeb + 0x10 * slot`. Only byte value `1` calls
  `0xd04a(0x1a)`; all other values return with no page object.
- Normal local Control-Z, non-`0x1a` second byte:
  mode-2 dispatch sends `0x1a X` to `0x1219e`, which calls
  `0xd04a(0x100)`. This is a synthetic printable-path value; it does not
  write the append sink.
- Alternate/data local Control-Z:
  alternate/data mode-2 dispatch sends nested `0x1a` to `0x1210c`, which
  appends literal `0x1a` through `0xe002`, and sends `0x1a X` to `0x121b2`,
  which calls `0xd99a` and appends `0x7f`. Both outcomes are append-only
  until a later macro/data-chain replay path consumes the stored bytes.
- `ESC z` display-functions off/status:
  parser dispatch reaches `0xcd86`, which reads active data-chain frame
  pointer `0x782d76` and frame byte `+9`. A zero frame kind calls
  `0x9c2c`; nonzero returns without page output. `0x9c2c` writes status
  markers `0x7821cc` and `0x7822db`, ORs bit `0x8` into `0x780e2a` through
  `0x9b5e`, then clears `0x7821cc`. The unresolved part is the external
  status-consumer name, not parser routing or page rendering.

State grouping for this matrix:

- Canonical reader/input state:
  local `ESC` flag `D4`, normalized value `D5`, source loop `0xa904`, and
  termination on normalized `ESC Z` or no-byte return.
- Canonical text/filter state:
  selected slot `0x782f06`, C0 filter byte
  `0x782eea + 0x10 * slot`, Control-Z context byte
  `0x782eeb + 0x10 * slot`, high-control fallback byte `0x782efa`, and
  high-character flags `0x783132` / `0x783133`.
- Canonical append/status state:
  append sink `0xe002`, macro/data storage such as fixture-visible chunk
  `0x783988`, active data-chain frame `0x782d76`, status markers
  `0x7821cc` / `0x7822db`, and warning/status accumulator `0x780e2a.3`.
- Parser scratch:
  mode-1 `ESC Y` / `ESC z` dispatch state, mode-2 local Control-Z dispatch
  state, and per-loop normalized bytes that are discarded after routing or
  append.
- Firmware bookkeeping:
  `0xd99a` normalization/reporting side effect, `0xf054` after routed CR in
  the normal reader, and `0x9c2c` waiting on service busy bit `0x780e2d.3`.
- Unknown:
  no ROM-local handler, consumer, or page-output middle edge is unknown for
  the documented outcomes. Remaining unknowns are manual-facing names and
  external consumers for the status bits written by `0xcd86 -> 0x9c2c`.

Evidence for the matrix is the same checked-in ledger: reader listings
`generated/disasm/ic30_ic13_text_payload_repeat_readers_012120.lst`
`0x12120..0x1219c` and `0x12536..0x1261e`, local terminal listing
`generated/disasm/ic30_ic13_control_z_handlers_0120d2.lst`
`0x120d2..0x121ca`, status listing
`generated/disasm/ic30_ic13_status_signal_helpers_009b5e.lst`
`0x9c2c..0x9c8e`, table rows in
`generated/analysis/ic30_ic13_parser_dispatch_tables.md`, and fixtures
`ESC Y display-functions stream reaches page-record output`,
`ESC Y display-functions filter-on routes controls as printable`, and
`0x12120 ESC Y alternate append stores normalized display bytes`.

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
- local Control-Z mode-2 dispatch is table-dependent: normal `0x1a 0x1a`
  calls `0x120d2` and only emits printable `0x1a` when the Control-Z context
  byte at `0x782eeb + 0x10 * 0x782f06` equals `1`; normal `0x1a X` always
  calls `0xd04a(0x100)`;
- alternate/data Control-Z siblings append through `0xe002` instead of
  queueing page objects: nested `0x1a` appends literal `0x1a`, and `0x1a X`
  runs `0xd99a` then appends `0x7f`;
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
