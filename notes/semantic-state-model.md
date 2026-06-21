# Semantic State Model

This file composes broad-enough ROM clusters into renderer-facing state
concepts. It complements the low-level ledger in
`notes/reverse-engineering-ledger.md`; it does not replace address-level
notes, disassembly windows, or executable fixtures.

## Vertical Forms Control

Status: partially anchored. The table definition path and its immediate
text-bottom effect are modeled. The channel-jump consumer is identified,
but its full page-eject/search behavior is not yet fully lifted.

Concept: vertical forms control is a per-line, 16-channel stop table used
by `ESC &l#W` definitions and consumed by `ESC &l#V` vertical channel
jumps. It affects visible output by changing the text-length bottom cache
and, through the unresolved jump consumer, can move the vertical cursor or
force page/line recovery before later printable bytes are queued.

### Field Groups

- `0x782dde..0x782edd`: canonical VFC table.
  Semantic role: 128 16-bit VFC channel words, two payload bytes per
  line.
  Evidence: writer `0x12cfe`, default builder `0x12b96`, consumer
  `0x1280a`; fixture
  `0x12cfe ESC &l#W loads vertical forms control state`.
- `0x783160`: canonical VMI / line advance.
  Semantic role: converts between line numbers and packed cursor
  positions.
  Evidence: VMI writers `0xcb00`/`0xc992`; readers `0xfe54`,
  `0x1280a`, `0x12cfe`; fixture
  `0xf9e8 ESC &l#P converts VMI lines to page length and selects
  internal page code`.
- `0x782dce`: canonical top offset.
  Semantic role: origin for VFC line-to-cursor conversion.
  Evidence: writers `0xece2`, `0xf9e8`, `0x12cfe`; readers `0x1280a`,
  `0x12cfe`; fixture
  `0x12cfe ESC &l#W loads vertical forms control state`.
- `0x782dd2`: derived/cache text-length bottom.
  Semantic role: text-bottom cache; `0x12cfe` copies VFC-derived limit
  here.
  Evidence: writers `0xea9e`, `0xea16`, `0x12cfe`; consumers include
  vertical overflow helpers; fixture
  `mixed VFC definition stream consumes payload before printable
  page-record queue`.
- `0x782dc2`: derived/cache VFC limit.
  Semantic role: VFC-derived bottom/limit before it is copied to
  `0x782dd2`.
  Evidence: writer `0x12cfe`; consumer `0xf36c`; long-reference scan
  lists `0xf372`, `0x12cec`, and `0x12f16`.
- `0x782ede`: derived/cache last VFC/page line index.
  Semantic role: payload count bound and channel-search limit.
  Evidence: writers `0xfe54`/`0x12cfe`; readers `0x1280a`, `0x12cfe`;
  fixture records `last_line = 63` for Letter at 6 LPI.
- `0x782edf`: derived/cache last text line index.
  Semantic role: default VFC table builder `0x12b96` input.
  Evidence: writer `0xfe54`; reader `0x12b96`; disassembly
  `0xfe54..0xfe94` and `0x12b96..0x12bb6`.
- `0x782ee0`: derived/cache last printable text line.
  Semantic role: clamps channel-derived bottom.
  Evidence: writer `0xfe54`; readers `0x1280a`, `0x12cfe`; fixture
  records `text_last_line = 62` for Letter at 6 LPI.
- `0x782ee1`: firmware bookkeeping.
  Semantic role: modified-layout flag cleared after VFC table load.
  Evidence: writers `0xca8c`/`0xcb00`/`0x12cfe`; disassembly
  `0x12f1e..0x12f24`.
- `0x78299e`: parser scratch.
  Semantic role: parsed six-byte command record cursor rewound by
  command handlers.
  Evidence: `0x11f6e` schedules delayed handler; `0x12cfe` rewinds and
  reads parsed count.

### Writers

- `0x11f6e` is the parser final for `ESC &l#W`; it schedules delayed
  handler `0x12cfe` through `0x121cc`.
- `0x12cfe` is the VFC table payload handler. It rewinds parser scratch
  at `0x78299e`, reads the absolute byte count, consumes payload bytes
  through `0xdace`, stores bytes into `0x782dde`, clears unused table
  bytes, derives `0x782dc2`, copies it to `0x782dd2`, and clears
  `0x782ee1`.
- `0x12b96` builds the default VFC table from line-number divisibility
  and boundary rules. It writes `0x782dde` words and is called by
  `0x12cfe` zero-count/default handling and by page-geometry refresh
  paths such as `0xf9e8`.
- `0xfe54` computes the VFC line-count caches `0x782edf`,
  `0x782ee0`, and `0x782ede` from VMI, top offset, text bottom, page
  extent, and vertical offset source.

### Readers And Consumers

- `0x1280a` is the `ESC &l#V` consumer. It reads the absolute channel
  selector, current VMI, cursor y `0x782c8e`, top offset `0x782dce`,
  text-line caches `0x782ede`/`0x782ee0`, and channel words from
  `0x782dde`. It searches forward or backward depending on cursor
  position relative to top offset.
- `0xf36c` consumes the derived limit `0x782dc2` during vertical
  overflow/perforation handling.
- Printable output is indirectly affected: the `ESC &l4W 00 00 00 02 !`
  fixture proves payload bytes are consumed before printable parsing, then
  the following `!` still reaches the page-record queue at compact coord
  `0x9001`.

### Output Effect

The anchored output effect is text-bottom recomputation and payload
boundary behavior. In the current fixture, a Letter 6-LPI base state with
top offset `90`, text bottom `3240`, and VMI `50` receives
`ESC &l4W 00 00 00 02`. Handler `0x12cfe` stores the table prefix
`00 00 00 02`, derives text bottom `190`, and leaves the following
printable `!` queued at compact coord `0x9001`.

### Confidence

High for the `0x11f6e -> 0x12cfe` delayed payload boundary, table bytes,
reject cases, zero-count reset, and text-bottom cache effect. Medium for
the exact semantic names of `0x782ede`/`0x782edf`/`0x782ee0`; the
line-count interpretation matches fixtures and disassembly but still
needs the complete `0x1280a` consumer lifted.

### Fixtures

- `0x12cfe ESC &l#W loads vertical forms control state`
- `mixed VFC definition stream consumes payload before printable
  page-record queue`
- Supporting existing fixtures:
  `0xc992 ESC &l#D accepts ROM LPI set and refreshes pending vertical
  cursor`, `0xf9e8 ESC &l#P converts VMI lines to page length and
  selects internal page code`

### Disassembly Evidence

- `generated/disasm/ic30_ic13_vertical_forms_control_01280a.lst`:
  `0x1280a..0x12b5e`, `0x12b96..0x12cfc`,
  `0x12cfe..0x12f28`
- `generated/analysis/ic30_ic13_direct_control_code_flow.md` and
  `generated/disasm/ic30_ic13_control_code_handlers_00f02c.lst`:
  direct vertical helpers `0xf054`, `0xf06e`, `0xf124`, and `0xf36c`
- `generated/disasm/ic30_ic13_hmi_vmi_handlers_00ca8c.lst`: VMI writers
  feeding the line-count math

### Unresolved Middle Edges

- `0x1280a..0x1295e`: forward channel search from current cursor to a
  matching VFC channel word is identified but not fully modeled.
- `0x129c6..0x12afc`: wrap/search/page-recovery branches call
  `0xf34a`, `0xf124`, and `0xf06e`; exact page-publication boundaries
  and cursor final positions still need fixtures.
- `0x12b96..0x12cfc`: default table bit meanings are known by bit
  positions but not fully named by PCL channel convention.
- Lowercase `ESC &l#w...#W` delayed-record preservation is inferred from
  the shared `0x121cc` boundary but not yet covered by a VFC-specific
  fixture.
