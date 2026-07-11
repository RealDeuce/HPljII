# IC30/IC13 Page-Root Finalization Flow

Generated from `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst` plus
cross-reference scans of the verified firmware image. This report pins the
publication boundary after a current page root has accumulated text, raster,
or rule objects and before reset, FF, or page-geometry changes clear that
root.

## `0xff1e` Finalize Contract

| Address | Instruction fact | Reproduction consequence |
| ---: | --- | --- |
| `0xff26..0xff3e` | tests current root `0x78297a`; if it is null or root byte `+4` is not `1`, branches to `0xffa2` | missing or non-active roots are discarded by clearing `0x78297a` without publication |
| `0xff40..0xff66` | when page/parser state byte `0x782a92 == 1`, tests root flags word `+0x14` bit 0; if set, skips the parser-reentry detour | bit 0 marks a root that has already taken the retry/finalize path and should publish without recursive parser work |
| `0xff68..0xff72` | passes saved longword `0x782a94` to helper `0xe0a4` | partial command/data state can be restored before finalizing the root |
| `0xff74..0xff9a` | if current parser/data-chain object `0x782d7a` exists and its first longword is nonzero, stores `0x782a92 = 2`, calls `0xe4f4`, re-enters parser loop `0x11774`, and ensures a root through `0x10084` | finalization can run pending parser/data-chain bytes before publishing the page record |
| `0xffb0..0xffcc` | loads active root into `A5`, clears transient bytes `0x78297e`, `0x782c72`, `0x782c73`, clears root word `+0x18`, and copies root `+0x16` to `+0x1a` | publication snapshots final band/extent metadata and consumes transient root-allocation latches |
| `0xffd2..0x1003e` | consumes flags `0x782997`, `0x780e99`, and `0x782998`, setting root byte `+8` or bits 0/1 in root byte `+0x0a` while wrapping writes in `0x15a6`/`0x15ac` | pending page/control status bytes become root-local publication flags before the record is handed off |
| `0x10044..0x1005a` | copies `0x782da6` to root byte `+7` and `0x782da4` to root word `+0x0c` | finalized records carry current page/environment metadata in the root header |
| `0x10060..0x10080` | writes root byte `+4 = 2`, copies root longword `+0` to `0x780ea6`, sets `0x782996 = 1`, then branches to clear `0x78297a` | active root state `1` becomes published state `2`; the backing pool record is exposed to the page/control scheduler and current-root ownership is dropped |

## Call-Site Groups

Absolute `JSR` references to `0xff1e`: `0x00cc92`, `0x00d494`, `0x00d8e4`,
`0x00da30`, `0x00da86`, `0x00ef96`, `0x00f128`, `0x00fa68`, `0x00fb10`,
`0x00fcaa`, `0x00fd6e`, `0x0106e6`, ... (15 total).

| Caller family | Observed call sites | Reproduction implication |
| --- | --- | --- |
| reset and page/control publication | `0x00cc92`, `0x00ef96`, `0x00f128` | these paths share the same publish-or-clear contract before continuing |
| printable text retry/finalize paths | `0x00d494`, `0x00d8e4`, `0x00da30`, `0x00da86` | these paths share the same publish-or-clear contract before continuing |
| text span flush retry path | `0x0127be` | these paths share the same publish-or-clear contract before continuing |
| page geometry and layout changes | `0x00fa68`, `0x00fb10`, `0x00fcaa`, `0x00fd6e` | these paths share the same publish-or-clear contract before continuing |
| raster transfer page-boundary path | `0x0106e6` | these paths share the same publish-or-clear contract before continuing |
| rectangle/rule queue retry path | `0x010d32` | these paths share the same publish-or-clear contract before continuing |
| font-slot/default update flush path | `0x01ba76` | these paths share the same publish-or-clear contract before continuing |

## State Reference Scan

| Address | Current finalization role | Longword literal references |
| ---: | --- | --- |
| `0x0078297a` | current page root consumed and cleared by `0xff1e` | `0x00c44a`, `0x00c50a`, `0x00c61c`, `0x00d204`, `0x00d48a`, `0x00d636`, `0x00d8da`, `0x00da68`, `0x00ff28`, `0x00ff30`, `0x00ff56`, `0x00ffa4`, ... (35 total) |
| `0x00782a92` | page/parser finalization state tested for the parser-reentry detour | `0x006608`, `0x00660e`, `0x0066ba`, `0x00ded2`, `0x00dede`, `0x00def6`, `0x00dfd6`, `0x00e178`, `0x00e3fe`, `0x00fc5c`, `0x00fc68`, `0x00fe3c`, ... (26 total) |
| `0x00782a94` | saved command/data key restored through helper `0xe0a4` | `0x00deec`, `0x00dfce`, `0x00ff6a` |
| `0x00782d7a` | current parser/data-chain object tested before re-entering `0x11774` | `0x00dd42`, `0x00e022`, `0x00e0d2`, `0x00e0e0`, `0x00e10a`, `0x00e160`, `0x00e432`, `0x00e43a`, `0x00e5b0`, `0x00ff76`, `0x00ff7e`, `0x011a72` |
| `0x0078297e` | transient root/font-slot byte cleared on publication | `0x00c478`, `0x00ce4e`, `0x00d45c`, `0x00d46e`, `0x00d8ac`, `0x00d8be`, `0x00ffb8` |
| `0x00782c72` | pending allocation/finalization latch cleared on publication | `0x00ce54`, `0x00d9f6`, `0x00da18`, `0x00da26`, `0x00ffbe`, `0x0100a0`, `0x0100be` |
| `0x00782c73` | pending allocation/finalization latch cleared on publication | `0x00ce5a`, `0x00da56`, `0x00da5e`, `0x00da7c`, `0x00ffc4`, `0x010098`, `0x0100b8` |
| `0x00782997` | pending status bit copied into root byte `+0x0a` bit 0 | `0x00ce32`, `0x00fb24`, `0x00fd78`, `0x00ffd6`, `0x00fffa` |
| `0x00780e99` | pending status byte copied into root byte `+8` | `0x0080c6`, `0x00cf40`, `0x00fb30`, `0x00fd84`, `0x00ffee`, `0x010002` |
| `0x00782998` | pending status bit copied into root byte `+0x0a` bit 1 | `0x00ce3a`, `0x00f020`, `0x010022`, `0x010040` |
| `0x00782da6` | page/environment byte copied into finalized root `+7` | `0x003d44`, `0x003d54`, `0x00ce24`, `0x00ef6e`, `0x00f012`, `0x00fa78`, `0x00fa8c`, `0x00fcba`, `0x00fccc`, `0x01004c` |
| `0x00782da4` | page/environment word copied into finalized root `+0x0c` | `0x00ce0c`, `0x00ef22`, `0x00ef2e`, `0x010054`, `0x01c23a`, `0x01e0d6`, `0x01e90a`, `0x030f2c`, `0x030f36` |
| `0x00780ea6` | published page/control pool record pointer written from root longword `+0` | `0x00314c`, `0x003bf8`, `0x004428`, `0x0062c0`, `0x00653a`, `0x00774c`, `0x009aa0`, `0x009aba`, `0x01006e`, `0x01c334`, `0x01e0f6`, `0x01e92a`, ... (13 total) |
| `0x00782996` | page/control publication flag set after root state changes to `2` | `0x01007c`, `0x0130e6`, `0x013224`, `0x0138ec` |

## Current Reproduction Contract

- A page-root reproduction must distinguish the no-publication clear path from
  the active-root publication path: only active roots with byte `+4 == 1` are
  promoted to state `2` and exposed through `0x780ea6`.
- The finalizer is not a pure state copy. In the `0x782a92 == 1` case it can
  restore saved command/data state, re-enter the parser at `0x11774`, and
  ensure a root again before publication.
- The published pool record must preserve the root-header fields written by
  `0xff1e`: state byte `+4`, environment byte `+7`, status byte `+8`, status
  bits in `+0x0a`, environment word `+0x0c`, the `+0x16` to `+0x1a` copy,
  cleared `+0x18`, queue root `+0x1c`, rule/fixed roots `+0x24/+0x28`, and
  context slots from `+0x2c`.
- Reset, FF, page-size, orientation, text retry, rectangle/rule queue retry,
  font-slot/default update, and raster page-boundary paths all share this
  finalizer; byte-perfect reproduction should therefore compare the same
  published root shape at this boundary before rendering through `0x1edc6`.
- `tools/render_fixture_harness.py` already models valid-root publication,
  missing-root clear, mixed printable reset/FF/page-geometry publication, and
  the `0xff1e` header-field copies for default and nonzero status/environment
  state. The remaining fidelity gap is to replace those fixture-only
  source/root objects with roots produced by the full parser and allocator
  path.
