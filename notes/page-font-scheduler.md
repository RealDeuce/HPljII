# Page/Font Scheduler Handoff

This note documents routine `0x19dd2..0x1a2e2`, the ROM-visible handoff that
can run after host/external quiesce and before normal parsing/rendering
resumes. It scans optional resource windows, compares fresh resource-window
state against canonical state, refreshes font/resource bookkeeping, and returns
a scheduler status to its caller.

Status: composed for the scheduler wrapper, optional-window scratch scan,
canonical/scratch comparison predicates, status-return branch, long refresh
chain, and caller contracts. It has no direct bitmap output, but it can affect
later pixels by pruning candidates, releasing downloaded-font payloads,
refreshing active font slots, or stopping a caller on a status branch.

## Evidence

- `generated/disasm/ic30_ic13_page_scheduler_019dd2.lst`
- `generated/disasm/ic30_ic13_font_resource_refresh_helpers_0178fa.lst`
- `generated/disasm/ic30_ic13_font_scheduler_commit_01a4fa.lst`
- `generated/disasm/ic30_ic13_font_candidate_window_prune_01ba92.lst`
- `generated/disasm/ic30_ic13_font_default_update_01ba40.lst`
- `generated/disasm/ic30_ic13_host_input_quiesce_004200.lst`
- `generated/disasm/ic30_ic13_host_scheduler_caller_004700.lst`
- `generated/disasm/ic30_ic13_external_ready_service_loop_00ba48.lst`
- `generated/disasm/ic30_ic13_font_resource_scan_01a2e4.lst`
- `generated/disasm/ic30_ic13_status_bit_helpers_009ba2.lst`
- `generated/analysis/ic30_ic13_parser_xrefs.md`
- `generated/analysis/ic30_ic13_renderer_fixture_harness.md`
- `notes/semantic-state-model.md` section `Page/Font Scheduler Handoff`
- `notes/external-ready-service.md`
- `notes/resource-rom.md`
- `notes/downloaded-fonts.md`

Primary fixtures:

- `0x19dd2 optional-window change composes refresh helpers`
- `0x19dd2 modeled unchanged and status branch exits`
- `0x447a/0x4760 consume scheduler return differently`
- `0xbb0a external-ready teardown ignores scheduler return`
- `0x1a2e4 font scan ignores scheduler return`

## Field Groups

Canonical state:

- `0x7828b6..0x7828dd`: two 20-byte canonical resource-window table slots.
  `0x1a042` and `0x19f08` compare these against the fresh scratch slots;
  `0x1a900` replaces them from the scratch block.
- `0x780e2e`: status longword root. The status branch raises mask
  `0x00000200` through `0x9bee`.
- `0x780e8d`: byte copy of the canonical-side mismatch predicate on the
  status-return branch.

Derived/cache state:

- `0x782894`: pointer to the current stack scratch block at `A6-0x28`.
- `0x782884`: current scan pointer inside the active optional resource window.
- `0x78288c`: active optional resource-window base, either `0x200000` or
  `0x400000`.
- `0x782890`: active optional resource-window limit, either `0x3ffffe` or
  `0x5ffffe`.
- `0x782898`: terminal byte copied from record offset `+0x0c` by `0x1a220`
  or from record offset `+0x05` by `0x1a254`.
- Candidate-list window pointers and counts: `0x7827a8`, `0x7827ac`,
  `0x7827b0`, `0x7827b4`, `0x782790`, `0x782794`, `0x782798`, and
  `0x78279c`.

Parser scratch:

- `A6-0x29`: canonical-side mismatch byte returned by `0x1a042`.
- `A6-0x2a`: fresh-scan-side mismatch byte returned by `0x19f08`.
- `A6-0x28..A6-0x15`: fresh slot `0` for optional window `1`
  (`0x200000..0x3ffffe`).
- `A6-0x14..A6-0x01`: fresh slot `1` for optional window `2`
  (`0x400000..0x5ffffe`).
- `A6-0x02`: local output word passed by font-resource scan caller
  `0x1a3c8..0x1a3e0` to resolver `0x1b50e` after scheduler return.

Firmware bookkeeping:

- `0x782780`: candidate-count snapshot written by font-resource scan caller
  `0x1a3b8`.
- `0x782640..0x782776`: 32 current downloaded-font records walked by
  `0x178fa`.
- `0x782324..`: candidate pointer-list entries pruned by `0x1ba92` and marked
  dirty by `0x19d9c`.
- `0x782f2c` and `0x782f2d`: active-font dirty bytes set by `0x179aa`.
- Host-quiesce caller bookkeeping after `0x447a`: `0x780e3a`,
  `0x7821cd.0`, `0x7821b0`, and `0x780e68`.
- Host/menu caller bookkeeping after `0x4760`: `0x782272`, `0x782278`,
  `0x782288`, `0x78228c`, `0x782290`, and `0x7822de`.
- Return `D7`: `1` for unchanged and long-refresh paths; `0` for the
  status-return branch after `0x72a2 == 0` and first predicate nonzero.
- Stack argument slot `(A7)`: reused for predicate arguments to `0x19fb8`,
  `0x1ba92`, `0x178fa`, and `0x1a4fa`.

Unknown:

- Board-level meaning of `$8000.14` and `$8000.15`.
- Physical optional-resource contents for windows `0x200000..0x3ffffe` and
  `0x400000..0x5ffffe`.
- Manual-facing names for non-signature optional-resource boundary records
  reached after `0x1b9c0` returns `-1`. The ROM-local classifier and
  direct signature-skip behavior are documented in
  [built-in-resource-scan.md](built-in-resource-scan.md).
- User-facing name for `0x780e8d` and status mask `0x00000200`.

## Writers

- `0x19dd6..0x19dda` computes `A6-0x28` and writes it to `0x782894`.
- `0x19eb6..0x19f00` clears the two scratch slots, checks `$8000.14/15`, and
  calls `0x1a0f2(1)` or `0x1a0f2(2)` for enabled optional windows.
- `0x1a0f2..0x1a21e` seeds `0x78288c`, `0x782884`, and `0x782890`, chooses
  scratch slot `0` or `1`, appends record words, and copies terminal byte
  `0x782898`.
- `0x1b9c0` classifies the current resource cursor for `0x1a0f2`: `HEAD`
  returns `1`; `FONT`, `font`, `DUMY`, `TABL`, or `tabl` at the current
  cursor, or the same signatures at cursor `+8`, return `0`; and neither
  match returns `-1`.
- `0x1a220..0x1a252` handles a classifier return of `1`: copy record byte
  `+0x0c` to `0x782898`, advance `0x782884` by record longword `+0x04`, and
  return record word `+0x0e`.
- `0x1a254..0x1a2e2` handles a classifier return of `0`: skip signatures
  `TABL`, `tabl`, `DUMY`, `FONT`, and `font`; for the first other record,
  copy byte `+0x05` to `0x782898`, advance by eight bytes, and return word
  `+0x06`. A classifier return of `-1` appends a zero word and advances to
  the next optional-resource grid point without calling either helper.
- `0x19de6..0x19df6` stores returns from `0x1a042` and `0x19f08` into
  local predicate bytes.
- `0x19e32..0x19e46` writes `0x780e8d = first_predicate` and calls
  `0x9bee(0x780e2e, 0x00000200)`.
- `0x1ba92..0x1bb9c` prunes candidate-list entries in the affected optional
  resource range, calls `0x1bd2e`, decrements `0x78278e`, and adjusts
  candidate-list counts and pointer windows.
- `0x178fa..0x179a8` walks current downloaded-font records and releases
  matching nonzero payload pointers through `0x1887a`.
- `0x19d9c..0x19dca` sets bit 3 in the first `0x78278e` candidate entries.
- `0x1a4fa..0x1a612` selects the fresh-side optional-resource scan range,
  writes `0x78288c`, `0x782890`, and `0x782888 = 0x40000`, then calls
  `0x1a616`.
- `0x1a900..0x1a9b6` calls `0x1b04c`, validates active contexts
  `0x782ee6` and `0x782ef6` through `0x1b4c0`, calls `0x179aa(0/1)` when a
  context is missing or not bit-27 marked, and copies ten longwords from
  `0x782894` into `0x7828b6`.
- `0x1a2e4..0x1a3c2` is a caller-side setup path: it initializes built-in
  candidate scan state, reports `0xe7/0x39` when no candidates are found,
  snapshots `0x78278e` to `0x782780`, then calls `0x19dd2`.

## Readers And Consumers

- Known callers: `0x00447a`, `0x004760`, `0x007164`, `0x00bb16`, and
  `0x01a3c2`.
- `0x19dfa..0x19e04` consumes the two predicate bytes to choose unchanged
  versus changed paths.
- `0x19e22..0x19e30` consumes `0x72a2` and first predicate byte to choose the
  status-return path.
- `0x1a042..0x1a0f0` consumes canonical slots at `0x7828b6 + slot * 0x14`
  and compares them against matching scratch slots.
- `0x19f08..0x19fb6` consumes fresh scratch slots and compares them against
  matching canonical slots.
- `0x19fb8..0x1a040` consumes the predicate argument and `0x78219b` to select
  when to call `0x6364`.
- `0x19e64..0x19e84` consumes the first predicate for `0x1ba92` and
  `0x178fa`, then calls `0x19d9c`.
- `0x19e8a..0x19e9a` consumes the second predicate for `0x1a4fa`, then calls
  `0x1a900`.
- Host-input quiesce caller `0x447a` ignores scheduler `D7` and continues
  through the quiesce tail.
- Host/menu caller `0x4760` consumes scheduler `D7`: `D7 = 0` returns
  immediately, while `D7 != 0` enters menu/default setup and polling.
- External-ready teardown at `0xba48 -> 0xbb16` records scheduler side effects
  but ignores scheduler `D7` before status aggregation through `0x36e4`.
- Font-resource scan caller `0x1a2e4 -> 0x1a3c2` ignores scheduler `D7`, then
  passes `0x78219b`, `0x78219c`, and `A6-0x02` to `0x1b50e`; only resolver
  `D7 == 0` calls `0x6364`.

## Output Effect

This scheduler has no direct page-record or bitmap output. Its pixel risk is
indirect: optional-window changes can remove candidate entries, release
downloaded-font payloads, mark candidates dirty, refresh active font slots,
commit new canonical resource-window state, or raise a status branch that
changes whether callers continue.

Fixture `0x19dd2 optional-window change composes refresh helpers` proves one
changed-window path through predicates `(1, 1)`: `0x1ba92` prunes a
`0x200000..0x3ffffe` candidate through `0x1bd2e`, `0x178fa` releases one
current-record payload through `0x1887a`, `0x19d9c` marks remaining candidate
index `0` dirty, `0x1a4fa` hands range `(2097152, 4194302)` to `0x1a616`, and
`0x1a900` commits scratch slot zero to canonical `0x7828b6`.

Fixture `0x19dd2 modeled unchanged and status branch exits` proves the
both-zero path returning `D7 = 1` after `0x19fb8(0)` and `0x1b04c`, plus the
modeled `0x72a2 == 0` status branch writing `0x780e8d = 1`, raising
`0x9bee(0x780e2e, 0x00000200)`, calling `0x19fb8(1)`, and returning
`D7 = 0`.

Fixture `0x447a/0x4760 consume scheduler return differently` proves the two
host-side caller contracts. Fixture `0xbb0a external-ready teardown ignores
scheduler return` proves the external-ready teardown caller. Fixture
`0x1a2e4 font scan ignores scheduler return` proves the built-in font-resource
scan caller.

## Reproduction Contract

A ROM-derived renderer/emulator must preserve:

- the `0x782894` scratch-pointer publication and two 20-byte scratch slots;
- `$8000.14/15` gates for optional-window scans;
- optional-window ranges `0x200000..0x3ffffe` and `0x400000..0x5ffffe`;
- canonical/scratch comparison predicates from `0x1a042` and `0x19f08`;
- both-zero, status-return, and long-refresh scheduler return paths;
- candidate pruning through `0x1ba92` and current-record release through
  `0x178fa`;
- dirty-bit marking through `0x19d9c`;
- fresh-side range handoff through `0x1a4fa`;
- canonical table commit and active-context refresh through `0x1a900`;
- caller-specific handling of scheduler `D7`.

## Confidence

High for call order, predicate branching, scratch layout, optional-window
bases/limits, canonical versus scratch comparison, `0x19fb8` predicates,
candidate-list pruning, current-record release predicates, dirty-bit marking,
range handoff, active-context checks, canonical-table copy, status-mask call,
and return values because they are direct disassembly evidence and
fixture-backed.

Medium for treating the routine as a page/font scheduler handoff: caller
locations and callee behavior support that role, and shared helper interiors
are documented in sibling checkpoints. Physical optional-resource contents are
not yet represented by live hardware/emulator evidence.

## Remaining Edges

- `0x19dd2 -> 0x1ba92/0x178fa/0x19d9c/0x1a4fa/0x1a900`: one modeled changed
  optional-window path is fixture-backed. Remaining work is a live CPU or
  physical-resource execution of the same sequence.
- `0x1a616`: built-in window `0x080000..0x0ffffe` is composed in
  `Built-In Resource Scan And Candidate Windows`; optional windows
  `0x200000..0x3ffffe` and `0x400000..0x5ffffe` remain unverified physical
  inputs.
- `0x1887a`, `0x1b4c0`, `0x1b04c`, and `0x179aa`: generic interiors are
  documented in downloaded-font, macro, and font-selection checkpoints.
  Remaining work here is live optional-resource execution through those
  callees.
- `0x1b9c0`: ROM-local classifier returns are documented in
  `Built-In Resource Scan And Candidate Windows`; the remaining edge is a
  physical optional-resource image or live CPU session that reaches the
  non-signature `-1` boundary.
