# IC30/IC13 ESC E Reset Flow

Generated from `0xcc52`, `0xcc70`, helper windows around `0xcbd4`, `0xcda2`,
`0xe146`, and the page-root finalizer `0xff1e` in the verified firmware image.
This report tracks the host-visible PCL software reset boundary. Names remain
provisional where the underlying helper routines are not fully decoded.

## Entry Sequence

| Step | Firmware evidence | Confirmed reset role |
| ---: | --- | --- |
| 1 | `0xcc52 -> jsr 0xcc70` | performs the main environment/page/raster reset work |
| 2 | `0xcc5c -> bsr 0xcbd4` | refreshes current-font metric state used by text motion after reset |
| 3 | `0xcc60 -> jsr 0xe146` | resets parser/data-chain state and clears transient parser records |
| 4 | `0xcc66 -> clr.b 0x782a93` | clears a reset/status byte after parser reset completes |

## Main Environment Reset `0xcc70`

- Loads the raster graphics state block base `0x783170` into `A5`.
- If `0x7810b2` is clear, clears alternate/data parser mode byte `0x782c18`
  before any page work.
- Calls direct-control text flush helper `0xf34a`, page-root finalizer
  `0xff1e`, and active page/control-record wait helper `0x9ac2`.
- In the normal environment rebuild path, clears orientation byte `0x782da3`,
  calls `0xcda2`, `0xf952`, `0xf9ac`, and `0xf87e`, then recomputes `0x782dce
  = 0x96 - 0x782dbe` and clears `0x782dd0`.
- Calls follow-up environment/font/page helpers `0xea16`, `0xe9ba`, `0xf8fc`,
  `0xfe54`, `0x12b96`, and `0x103ea`.
- Reinitializes raster state at `0x783170`: clears byte `+0x12`, word `+0x00`,
  and long `+0x0a`; writes word `+0x08 = 3` and word `+0x0e = 4`; derives word
  `+0x10` from page extent `0x782db4`, baseline word `+0x00`, and scale word
  `+0x08`.
- If `0x7810b2` is clear and `0x780e3c == 1`, it copies `0x7821a2` to
  `0x780e8f` and ORs bit `1` into `0x780e26` via helper `0x9b5e`; otherwise it
  can route through `0x1bba6` before the same rebuild path.

## Environment Defaults `0xcda2`

| Address range | Firmware operation | Reproduction meaning |
| ---: | --- | --- |
| `0xcdaa..0xcddc` | Initializes four 0x6c-byte page/control records rooted at `0x780f02`; each record's `+0x1c` points to a 0x400-byte bucket region at `0x7810bc + 0x400*n`. | Reset rebuilds the page/control pool's bucket-array backing pointers before page objects are queued. |
| `0xcddc..0xcdf0` | Stores `0x782a26 = 0x782a2a` and cursor-stack top `0x782d36 = 0x782c96`. | Parser scratch and the cursor stack return to their base positions. |
| `0xcdf0..0xce10` | Clears `0x78316a`, `0x783166`, and `0x78316e`; copies default byte `0x78219d` into word `0x782da4`. | Environment motion/status accumulators are reset and the default display/page mode is restored. |
| `0xce10..0xce3e` | If reset gate `0x7810b2` is clear, calls `0x15a6`, copies default byte `0x7821a2` into `0x782da6`, calls `0x15ac`, and sets `0x782997 = 1`, `0x782998 = 1`. | Some user/default environment bytes are reloaded only in the normal host reset path. |
| `0xce3e..0xce84` | Clears `0x782990`, sets `0x782a6d = 1`, clears `0x78297e`, `0x782c72`, `0x782c73`, `0x783184`, `0x783185`, `0x782f2c`, `0x78318f`, and `0x783190`, then sets `0x783191 = 1`. | Page/transient text flags, line-termination mode, and display-function bytes return to reset defaults before printing resumes. |
| `0xce84..0xcec8` | Recomputes HMI `0x78315c` from primary current-font context `0x782ee6`: flagged contexts use long `+0x24` through `0x10550`; unflagged contexts use word `+0x1a` scaled by `0x00057e40` through `0x3324a` and `0x104d8`. | Horizontal motion after reset remains font-derived, not a fixed constant. |
| `0xcec8..0xcf38` | Reads default line-spacing word `0x78219e`, normalizes it through `0xcfea`, clamps values below `5` or above `0x80` through `0xcf52`, converts through `0x104d8`, and stores VMI/line advance `0x783160`. | The reset VMI is derived from default/user line spacing but clamped to firmware bounds before cursor motion uses it. |
| `0xcf38..0xcf50` | Calls `0x15a6`, clears `0x780e99`, then calls `0x15ac`. | Completes the normal environment refresh handshake after default VMI/HMI restoration. |

## Font Metric Refresh `0xcbd4`

- Starts from current-font context base `0x782ee6` and clears glyph-map
  selector `0x782f06`.
- If context byte `+4` is clear, copies source byte `+0x19` into `0x78318e`,
  converts source word `+0x1a` through helpers `0x3324a` and `0x104d8`, and
  stores the result in HMI/default-motion longword `0x78315c`.
- If context byte `+4` is set, copies source byte `+0x21` into `0x78318e`,
  converts source longword at `+0x24` through `0x10550`, and stores the result
  in `0x78315c`.
- Copies active symbol words `0x783144` and `0x783146` into requested/snapshot
  words `0x782f08` and `0x782f0a`.

## Parser/Data Reset `0xe146`

- Sets current data-chain pointer `0x782d76` to base `0x782d3e`, calls helper
  `0xe1e4`, then clears current object pointer `0x782d7a`.
- Clears selector/state word `0x783164`, alternate/data parser bytes
  `0x782c18` and `0x782c19`, page/parser state byte `0x782a92`, and text
  accumulation bytes `0x783196..0x783199`.
- Clears eight 10-byte records starting at `0x782c1e` and resets cursor
  pointer `0x782c6e` to `0x782c1e`.
- Calls `0xe996(0x782ee2, 0x78319a, 0x7831a2)`, then calls `0xdf80` to clear
  command/data pool records whose byte `+0x0a` is zero.
- Helper `0xe1e4` walks data-chain records from `0x782d76` through `0x782d68`,
  marks byte `+8 = 4`, clears byte `+9`, frees any `+0x0a` 0x100-byte
  allocation through `0x18b4`, and clears the allocation pointer.

## Page-Root Finalize Hook `0xff1e`

- `0xcc70` calls `0xff1e` before rebuilding the print environment. This is the
  ROM hook that matches the PCL requirement that `ESC E` prints/finalizes a
  partial page rather than merely discarding it.
- If current page root `0x78297a` is null, or its byte `+4` is not `1`,
  `0xff1e` clears `0x78297a` and returns.
- If parser/page state `0x782a92 == 1` and root flags permit more work, it
  uses saved key `0x782a94`, may call `0xe4f4`, re-enters parser loop
  `0x11774`, and ensures a page root through `0x10084` before continuing.
- The final publication path clears transient bytes `0x78297e`, `0x782c72`,
  and `0x782c73`, updates root fields, copies the root's backing pool record
  to `0x780ea6`, sets `0x782996 = 1`, and then clears `0x78297a`.

## State Reference Scan

| Address | Current reset role | Longword literal references |
| ---: | --- | --- |
| `0x007810b2` | reset/environment gate tested by `0xcc70`; when clear, reset clears alternate/data parser mode | `0x00312c`, `0x0039b8`, `0x00438a`, `0x006292`, `0x006616`, `0x006622`, `0x0072b2`, `0x009b2e`, `0x00cc80`, `0x00cca0`, `0x00ce12` |
| `0x00782c18` | alternate/data parser mode cleared by `0xcc70` and again by parser-state reset `0xe146` | `0x00cc88`, `0x00d9ac`, `0x00dd66`, `0x00dd96`, `0x00ddb0`, `0x00ddfe`, `0x00de38`, `0x00e16c`, `0x011830`, `0x011842`, `0x0118ce`, `0x011934`, `0x011d8e`, `0x011e60`, `0x012258` |
| `0x00783170` | raster graphics state block reset by `0xcc70` | `0x00cc7a`, `0x00f9f2`, `0x00fc7e`, `0x0105da`, `0x010764`, `0x010812` |
| `0x00782da3` | orientation byte cleared by the main `0xcc70` environment rebuild path | `0x00ccd8`, `0x00d3e4`, `0x00d864`, `0x00e298`, `0x00e390`, `0x00e6ce`, `0x00e810`, `0x00f884`, `0x00f9be`, `0x00fa4a`, `0x010254`, `0x010268`, `0x0103f0`, `0x010608`, `0x010702`, `0x01079a`, ... (38 total) |
| `0x00782dce` | top/vertical offset recomputed as `0x96 - 0x782dbe` during reset/page-size rebuild | `0x00ca60`, `0x00cbaa`, `0x00cd06`, `0x00e5fe`, `0x00e620`, `0x00ea2e`, `0x00ea84`, `0x00eaf8`, `0x00eb44`, `0x00ed56`, `0x00ed86`, `0x00f15a`, `0x00f71c`, `0x00f93c`, `0x00fc18`, `0x00fc32`, ... (30 total) |
| `0x00782dd0` | related vertical/page offset word cleared during reset/page-size rebuild | `0x00cd0c`, `0x00e604`, `0x00e626`, `0x00fc1e`, `0x00fc38`, `0x00fe18`, `0x01028c`, `0x012d5c`, `0x012d84` |
| `0x00782a26` | parameter/text scratch pointer reset to `0x782a2a` by `0xcda2` | `0x00cde2`, `0x0117a8`, `0x0119ac`, `0x0119d2`, `0x0119fe`, `0x011a30`, `0x011a36`, `0x011a98`, `0x011acc`, `0x011aee`, `0x011b56`, `0x0123be` |
| `0x00782d36` | cursor-stack top pointer reset to `0x782c96` by `0xcda2` | `0x00cdec`, `0x00f786`, `0x00f790`, `0x00f7fa` |
| `0x00783160` | VMI/line advance recomputed by `0xcda2` from default line spacing word `0x78219e` | `0x00ca7e`, `0x00cb7e`, `0x00cef8`, `0x00cf1c`, `0x00cf34`, `0x00eac6`, `0x00ed0a`, `0x00f0be`, `0x00f130`, `0x00f188`, `0x00f58a`, `0x00f912`, `0x00fa16`, `0x00fe5e`, `0x0102cc`, `0x0102f8`, ... (23 total) |
| `0x00783166` | environment motion accumulator longword cleared by `0xcda2` | `0x00cdf8`, `0x0108fe`, `0x010b24`, `0x010c04`, `0x010c34`, `0x010e4c`, `0x010e5c`, `0x01e86a`, `0x01e882`, `0x01e89c`, `0x01e8ce`, `0x030fc8`, `0x03100a`, `0x031118`, `0x031166` |
| `0x0078316a` | environment motion accumulator longword cleared by `0xcda2` | `0x00cdf2`, `0x0108f4`, `0x010a84`, `0x010bc2`, `0x010c2c`, `0x010c80`, `0x010e92`, `0x010ea2`, `0x01e870`, `0x01e888`, `0x01e8a2`, `0x01e8d4`, `0x030fd0`, `0x031010`, `0x031120`, `0x03116e` |
| `0x0078316e` | environment motion/status word cleared by `0xcda2` | `0x00cdfe`, `0x0108b6`, `0x010e16` |
| `0x00782da4` | display/page mode word loaded from default byte `0x78219d` by `0xcda2` | `0x00ce0c`, `0x00ef22`, `0x00ef2e`, `0x010054`, `0x01c23a`, `0x01e0d6`, `0x01e90a`, `0x030f2c`, `0x030f36` |
| `0x00782da6` | environment byte copied from default byte `0x7821a2` by `0xcda2` when reset gate permits | `0x003d44`, `0x003d54`, `0x00ce24`, `0x00ef6e`, `0x00f012`, `0x00fa78`, `0x00fa8c`, `0x00fcba`, `0x00fccc`, `0x01004c` |
| `0x00782990` | page/status byte cleared by `0xcda2` | `0x00ce40`, `0x00efbc`, `0x00f004`, `0x0100fa` |
| `0x00782a6d` | parser/page flag set to `1` by `0xcda2` | `0x00ca3a`, `0x00cb84`, `0x00ce48`, `0x00d0e4`, `0x00d138`, `0x00ebc0`, `0x00ed60`, `0x00f084`, `0x00f0e8`, `0x00f11c`, `0x00f16e`, `0x00f1c4`, `0x00f312`, `0x00f528`, `0x00f6f6`, `0x00f826` |
| `0x0078297e` | page-root transient byte cleared by `0xcda2` and `0xff1e` | `0x00c478`, `0x00ce4e`, `0x00d45c`, `0x00d46e`, `0x00d8ac`, `0x00d8be`, `0x00ffb8` |
| `0x00782c72` | pending page/allocation latch cleared by `0xcda2` and `0xff1e` | `0x00ce54`, `0x00d9f6`, `0x00da18`, `0x00da26`, `0x00ffbe`, `0x0100a0`, `0x0100be` |
| `0x00782c73` | pending page/allocation latch cleared by `0xcda2` and `0xff1e` | `0x00ce5a`, `0x00da56`, `0x00da5e`, `0x00da7c`, `0x00ffc4`, `0x010098`, `0x0100b8` |
| `0x00783184` | pending text/span flag cleared by `0xcda2` | `0x00ce60`, `0x00d4ba`, `0x00d90a`, `0x00e32a`, `0x00ebd2`, `0x00f356`, `0x00f742`, `0x00f868`, `0x0103be`, `0x0103c6`, `0x01175a`, `0x0126a4`, `0x0126e8`, `0x0126f2`, `0x012724` |
| `0x00783185` | pending text/span flag cleared by `0xcda2` | `0x00ce66`, `0x00d4f2`, `0x00d942`, `0x0126d6` |
| `0x00782f2c` | font/symbol dirty flag cleared by `0xcda2` | `0x00c598`, `0x00c5ce`, `0x00c682`, `0x00c76c`, `0x00c7d4`, `0x00c834`, `0x00c890`, `0x00c91c`, `0x00c97e`, `0x00ce6c`, `0x0179b2`, `0x01b99a`, `0x01c052`, `0x01c096` |
| `0x0078318f` | line-termination mode byte cleared by `0xcda2` | `0x00ce72`, `0x00ee22`, `0x00ee34`, `0x00ee4c`, `0x00ee5e`, `0x00f040`, `0x00f094`, `0x00f0f8` |
| `0x00783190` | display-function byte cleared by `0xcda2` | `0x00ce78`, `0x00d302`, `0x00d33e`, `0x00d772`, `0x00d7ae`, `0x00eddc`, `0x00edec`, `0x01c22c`, `0x01e0dc`, `0x01e910`, `0x030f3c` |
| `0x00783191` | display-function byte set to `1` by `0xcda2` | `0x00ce80`, `0x00ee8e`, `0x00eea0`, `0x00f388`, `0x01c232`, `0x01e0e2`, `0x01e916`, `0x030f42` |
| `0x0078315c` | HMI/default horizontal motion recomputed by `0xcbd4` from current font metrics | `0x00c4bc`, `0x00c4ee`, `0x00caf4`, `0x00cc14`, `0x00cc32`, `0x00ceae`, `0x00cec4`, `0x00d1aa`, `0x00d1de`, `0x00d5aa`, `0x00d610`, `0x00eb80`, `0x00eba0`, `0x00ec36`, `0x00ec56`, `0x00f1d6`, ... (29 total) |
| `0x0078318e` | alternate previous-width/text-metric flag refreshed by `0xcbd4` | `0x00c488`, `0x00c4c8`, `0x00cbf4`, `0x00cc20`, `0x00d16c`, `0x00d2a0`, `0x00d588`, `0x00d6e2`, `0x00f2be`, `0x010366`, `0x010392` |
| `0x00782f06` | primary/secondary glyph-map selector cleared by `0xcbd4` | `0x00c5dc`, `0x00c600`, `0x00c698`, `0x00c6aa`, `0x00c6c6`, `0x00c6de`, `0x00cbe4`, `0x00d094`, `0x00e2ae`, `0x00e2d0`, `0x00e528`, `0x00e54a`, `0x00e69c`, `0x00e702`, `0x00e726`, `0x00e73c`, ... (42 total) |
| `0x00782f08` | active primary symbol word snapshot copied from `0x783144` by `0xcbd4` | `0x00c66e`, `0x00cc3c`, `0x00e696`, `0x00e7ac`, `0x00e7de`, `0x0103ae`, `0x01576a` |
| `0x00782f0a` | active secondary symbol word snapshot copied from `0x783146` by `0xcbd4` | `0x00cc46`, `0x00e6fa`, `0x00e82c`, `0x0103b8`, `0x015772` |
| `0x00782d76` | current parser/data-chain pointer reset to `0x782d3e` by `0xe146` | `0x00732e`, `0x009ee2`, `0x009f74`, `0x00a956`, `0x00cd90`, `0x00dd48`, `0x00e010`, `0x00e154`, `0x00e1ee`, `0x00e236`, `0x00e27e`, `0x00e3ce`, `0x00e426`, `0x00e4e8`, `0x00e5aa` |
| `0x00782d7a` | current parser/data-chain object pointer cleared by `0xe146` | `0x00dd42`, `0x00e022`, `0x00e0d2`, `0x00e0e0`, `0x00e10a`, `0x00e160`, `0x00e432`, `0x00e43a`, `0x00e5b0`, `0x00ff76`, `0x00ff7e`, `0x011a72` |
| `0x00783164` | parsed-command selector/current state word cleared by `0xe146` | `0x00dd32`, `0x00dda6`, `0x00dee6`, `0x00e13a`, `0x00e166` |
| `0x00782a92` | parser/page finalization state cleared by `0xe146`; also tested by `0xff1e` | `0x006608`, `0x00660e`, `0x0066ba`, `0x00ded2`, `0x00dede`, `0x00def6`, `0x00dfd6`, `0x00e178`, `0x00e3fe`, `0x00fc5c`, `0x00fc68`, `0x00fe3c`, `0x00fe48`, `0x00ff44`, `0x00ff8a`, `0x0103d4`, ... (26 total) |
| `0x00782a93` | top-level `ESC E` completion/status byte cleared after `0xe146` | `0x00cc68` |
| `0x00782a94` | saved command/data key used by `0xff1e` when finalizing a partial page | `0x00deec`, `0x00dfce`, `0x00ff6a` |
| `0x00783196` | text accumulation byte cleared by `0xe146` | `0x00e17e`, `0x0117be`, `0x0119e8`, `0x011b6c`, `0x012414` |
| `0x00783197` | text accumulation byte cleared by `0xe146` | `0x00e184` |
| `0x00783198` | text accumulation byte cleared by `0xe146` | `0x00e18a` |
| `0x00783199` | text accumulation byte cleared by `0xe146` | `0x00e190`, `0x0117c6` |
| `0x00782c1e` | base of eight 10-byte parser/control records cleared by `0xe146` | `0x00e196`, `0x018a06` |
| `0x00782c6e` | parser/control record cursor reset to `0x782c1e` by `0xe146` | `0x00e19c`, `0x00e4c2`, `0x00e4e2`, `0x00e4fe`, `0x00e520`, `0x00e66c`, `0x00e678` |
| `0x0078297a` | current page root finalized or cleared by `0xff1e`, called early by `0xcc70` | `0x00c44a`, `0x00c50a`, `0x00c61c`, `0x00d204`, `0x00d48a`, `0x00d636`, `0x00d8da`, `0x00da68`, `0x00ff28`, `0x00ff30`, `0x00ff56`, `0x00ffa4`, `0x00ffb2`, `0x01008e`, `0x0100ee`, `0x01011a`, ... (35 total) |
| `0x00780ea6` | current page/control pool record published by `0xff1e` finalization path | `0x00314c`, `0x003bf8`, `0x004428`, `0x0062c0`, `0x00653a`, `0x00774c`, `0x009aa0`, `0x009aba`, `0x01006e`, `0x01c334`, `0x01e0f6`, `0x01e92a`, `0x030f56` |
| `0x00782996` | page/control publication flag set by `0xff1e` finalization path | `0x01007c`, `0x0130e6`, `0x013224`, `0x0138ec` |

## Current Reproduction Contract

- A byte-stream model must treat `ESC E` as a page/environment boundary: flush
  pending text spans, run the page-root finalization path, rebuild page
  geometry/font metrics, reset raster graphics state, and clear
  parser/data-chain state.
- The ROM evidence distinguishes `ESC E` from a simple hard clear: `0xff1e`
  can publish/finalize the current page root before `0x78297a` is cleared.
- `tools/render_fixture_harness.py` now has synthetic `ESC E` byte-stream
  fixtures for valid-page-root publication and missing-root clearing, plus a
  mixed `!\x1bE` fixture that applies valid-root reset after queued text.
  Exact reset reproduction still needs fixtures that start from a fuller
  parser-allocated page root; the current page-record reset fixture now
  compares the modeled published record against the bridged/rendered compact
  bucket.
