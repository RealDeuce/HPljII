# IC30/IC13 Page-Root Reference Leads

Raw even/odd byte scan for absolute longwords that name the current page root
or the page/control record pool. Classifications are manual notes from focused
disassembly windows; they are intended to prevent re-tracing rejected
compositor leads.

## `0x0078297a` - current page-root pointer

| Offset | Current classification |
| --- | --- |
| `0x00c44a` | page state/font-slot lookup path |
| `0x00c50a` | page-root `+0x2c` font-slot manager |
| `0x00c61c` | page state/font-slot update path |
| `0x00d204` | text placement ensures page root before queuing |
| `0x00d48a` | text object insertion retries after page-root reallocation |
| `0x00d636` | alternate text placement ensures page root before queuing |
| `0x00d8da` | alternate text object insertion retries after page-root reallocation |
| `0x00da68` | display-function page-root flag update |
| `0x00ff28` | page-root finalize/reset |
| `0x00ff30` | page-root finalize/reset |
| `0x00ff56` | page-root dirty-flag test |
| `0x00ffa4` | page-root clear on finalize |
| `0x00ffb2` | page-root state update after finalize |
| `0x01008e` | ensure page-root entry |
| `0x0100ee` | store newly allocated page root |
| `0x01011a` | page-root initialization |
| `0x0106dc` | raster transfer marks page-root flags |
| `0x010d28` | rectangle/rule handler lead |
| `0x011754` | parser/data path page-root guard |
| `0x0127b4` | text span flush marks page-root flags |
| `0x01326e` | bucket object allocator under `+0x1c` |
| `0x013288` | bucket object allocator under `+0x1c` |
| `0x0133d8` | rectangle/rule linked-list producer |
| `0x0133e6` | rectangle/rule linked-list producer |
| `0x0133fa` | rectangle/rule linked-list producer |
| `0x013430` | rectangle/rule linked-list producer |
| `0x01343c` | rectangle/rule linked-list producer |
| `0x0136e4` | rectangle/rule second-mode producer |
| `0x01370c` | rectangle/rule second-mode producer |
| `0x01373c` | rectangle/rule second-mode producer |
| `0x013760` | rectangle/rule second-mode producer |
| `0x01376e` | rectangle/rule second-mode producer |
| `0x01388a` | bucket find-or-allocate under `+0x1c` |
| `0x0196da` | page-root `+0x2c` font-slot scan |
| `0x0196ee` | page-root `+0x2c` font-slot scan |

## `0x00780ea6` - page/control record pool head used by allocator `0x9a9a`

| Offset | Current classification |
| --- | --- |
| `0x00314c` | pool initialization |
| `0x003bf8` | scheduler/status polling |
| `0x004428` | pool record cleanup |
| `0x0062c0` | pool record cleanup |
| `0x00653a` | control-code/page-eject path checks active pool record |
| `0x00774c` | pool scheduling path |
| `0x009aa0` | allocator/free-list helper |
| `0x009aba` | allocator/free-list helper |
| `0x01006e` | current page root's underlying pool record published to `0x780ea6` |
| `0x01c334` | font sample/page setup path |
| `0x01e0f6` | font page setup path |
| `0x01e92a` | alternate font page setup path |
| `0x030f56` | embedded table/data hit; not disassembled as code |

## `0x00780eaa` - page/control pool cursor alias

| Offset | Current classification |
| --- | --- |
| `0x002292` | unclassified alias/reference lead |
| `0x0022a0` | unclassified alias/reference lead |
| `0x0022aa` | unclassified alias/reference lead |
| `0x0022b6` | unclassified alias/reference lead |
| `0x0022c8` | unclassified alias/reference lead |
| `0x0022ce` | unclassified alias/reference lead |
| `0x002892` | unclassified alias/reference lead |
| `0x003152` | unclassified alias/reference lead |
| `0x003bba` | unclassified alias/reference lead |
| `0x003cf2` | unclassified alias/reference lead |
| `0x003d1c` | unclassified alias/reference lead |
| `0x007724` | unclassified alias/reference lead |
| `0x007734` | unclassified alias/reference lead |
| `0x007746` | unclassified alias/reference lead |
| `0x007756` | unclassified alias/reference lead |
| `0x00775c` | unclassified alias/reference lead |
| `0x007f92` | unclassified alias/reference lead |
| `0x008068` | unclassified alias/reference lead |
| `0x008084` | unclassified alias/reference lead |
| `0x01eb48` | unclassified alias/reference lead |

## `0x00780eae` - page/control pool cursor alias

| Offset | Current classification |
| --- | --- |
| `0x0020d6` | unclassified alias/reference lead |
| `0x003158` | unclassified alias/reference lead |
| `0x009af4` | unclassified alias/reference lead |
| `0x01eb4c` | unclassified alias/reference lead |
| `0x01ed1a` | unclassified alias/reference lead |
| `0x01ed92` | unclassified alias/reference lead |
| `0x01eece` | unclassified alias/reference lead |
| `0x01ef06` | unclassified alias/reference lead |

## `0x00780eb2` - page/control pool cursor alias

| Offset | Current classification |
| --- | --- |
| `0x00199a` | unclassified alias/reference lead |
| `0x001b00` | unclassified alias/reference lead |
| `0x001b62` | unclassified alias/reference lead |
| `0x001b78` | unclassified alias/reference lead |
| `0x001c0e` | unclassified alias/reference lead |
| `0x001cdc` | unclassified alias/reference lead |
| `0x001f06` | unclassified alias/reference lead |
| `0x001f10` | unclassified alias/reference lead |
| `0x001f1c` | unclassified alias/reference lead |
| `0x001f22` | unclassified alias/reference lead |
| `0x001f2a` | unclassified alias/reference lead |
| `0x001f4c` | unclassified alias/reference lead |
| `0x001f94` | unclassified alias/reference lead |
| `0x0020dc` | unclassified alias/reference lead |
| `0x00315e` | unclassified alias/reference lead |
| `0x006bfa` | unclassified alias/reference lead |
| `0x007242` | unclassified alias/reference lead |
| `0x00772a` | unclassified alias/reference lead |
| `0x007762` | unclassified alias/reference lead |
| `0x007774` | unclassified alias/reference lead |
| `0x007784` | unclassified alias/reference lead |
| `0x007790` | unclassified alias/reference lead |
| `0x00779c` | unclassified alias/reference lead |
| `0x0077a2` | unclassified alias/reference lead |
| `0x007f8c` | unclassified alias/reference lead |
| `0x009afa` | unclassified alias/reference lead |

## `0x00780eb6` - page/control pool cursor alias

| Offset | Current classification |
| --- | --- |
| `0x003164` | unclassified alias/reference lead |

Current result: direct `0x78297a` references identify page-object producers,
page-root finalization, font-slot scans, and pool management. None yet proves
a final bucket-chain walker for page-root offsets `+0x1c`, `+0x24`, or
`+0x28`.
