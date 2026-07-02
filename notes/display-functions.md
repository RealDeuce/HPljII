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
- `0x12120` writes literal `ESC Y` through `0xe002`, then appends normalized
  loop values through `0xe002` until `ESC Z` or no-byte termination.
- `0x12536` writes visible text/fixed-space effects by calling `0xd04a` or
  `0xd0f0` for each normalized loop value.
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
until `ESC Z`. Fixture
`0x12120 ESC Y alternate append stores normalized display bytes` proves payload
`21 1a 58 1b 5a` is stored as `1b 59 21 7f 1b 5a` in macro chunk
`0x783988`.

Normal `0x12536` can produce pixels or fixed spacing. Values `0x00..0x1f`
route through `0xd0f0` only when selected context byte `D3` is zero. Values
`0x80..0x9f` route through `0xd0f0` only when the high-control filter word is
zero. All other values route through `0xd04a`.

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

Fixture `ESC Y display-functions stream reaches page-record output` proves
the default-filter normal path for `ESC Y!\x05! ESC Z`: handler `0x12536`
consumes values `21 05 21 1b 5a`, routes them
`d04a d0f0 d04a d0f0 d04a`, queues visible `!`, `!`, and `Z` entries at
compact coords `0x0001`, `0x0403`, and `0x0405`, and renders row digest
`c7d0fb0a66181acd591244aab0a7f450f895b3b89ea98d189a00a25c3de04d85`.

Fixture `ESC Y display-functions filter-on routes controls as printable`
proves the complementary normal branch. With selected-context byte `1` and
high-control filter `1`, stream `ESC Y\x05\x80\x1aX! ESC Z` normalizes
`0x1a 0x58` to `0x7f`, routes values `05 80 7f 21 1b 5a` through `0xd04a`,
queues six compact entries with object prefix
`00 00 00 00 00 00 00 06 04 0b 00 7f 0e 01 7e 1f 02 20 06 04 1a 53 05 59 06
06`, and renders row digest
`1cdd8203b43944801ec8d1d01c6ab4fa3808fc1f81a7ebfa4d04452369193b63`.

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
default-filter route, normal filter-on printable route, page-record output, and
rendered row digests because each is backed by disassembly and named fixtures.

High for the `ESC z` guard and `0x9c2c` call boundary because they are direct
disassembly reads. Medium for the manual-facing names and external consumers
of the status bits.

## Remaining Edges

- No ROM middle edge remains for the `0x12536..0x1261e` normal page-output
  loop, the `0x12120..0x1219c` alternate/data append loop, the local
  Control-Z sibling handlers, or the `0xcd86 -> 0x9c2c` display-functions-off
  status boundary.
- Remaining display-functions work is broader physical/reference output and
  external status-consumer naming, not parser or renderer discovery.
