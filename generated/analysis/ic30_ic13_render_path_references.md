# IC30/IC13 Render Path Reference Leads

Raw byte scan for render-path entry addresses and bitmap-state globals.
Classifications are manual notes from focused disassembly; this report is a
lead index, not a complete call graph.

## `0x0001ed84`

Role: copies the active page/control record into the selected render work
record

| Offset | Current classification |
| --- | --- |
| `0x01ed78` | called after optional render-state setup in the page/control record alternator |

## `0x0001edc6`

Role: copies queue/list pointers from source record to render record and
normalizes object flags/fields

| Offset | Current classification |
| --- | --- |
| `0x01edb8` | called by `0x1ed84` with destination render record and source active page/control record |

## `0x0001ee9e`

Role: initializes bitmap render state, including line stride at `0x783a1c`

| Offset | Current classification |
| --- | --- |
| `0x01ed70` | called when the active record band/height metadata changes |

## `0x0001ef6a`

Role: band render entry using work record at `0x783a18`

| Offset | Current classification |
| --- | --- |
| `0x01eca0` | called from the surrounding band/page scheduling loop |

## `0x0001f446`

Role: dispatches special/object-class bitmap writers through table `0x1f4a0`

| Offset | Current classification |
| --- | --- |
| `0x01ef78` | called between bucket-chain dispatch and fixed-width rule writer |

## `0x0001f756`

Role: walks render-record list at `+0x20` and writes fixed-width/rule-like
bitmap spans

| Offset | Current classification |
| --- | --- |
| `0x01ef7e` | called by band render entry `0x1ef6a` |

## `0x0001f812`

Role: renders segment-list objects selected from the bucket chain

| Offset | Current classification |
| --- | --- |
| `0x01efec` | called by bucket-chain dispatcher for objects with positive class bits |

## `0x0001f88e`

Role: renders encoded span objects selected from the bucket chain

| Offset | Current classification |
| --- | --- |
| `0x01eff4` | called by bucket-chain dispatcher for objects with negative class bits |

## `0x007810b4`

Role: bitmap/page buffer base

| Offset | Current classification |
| --- | --- |
| `0x0009d0` | startup or memory initialization reference |
| `0x000b4e` | startup or memory initialization store |
| `0x013c74` | unclassified alias/reference lead |
| `0x013cde` | unclassified alias/reference lead |
| `0x017ff2` | unclassified alias/reference lead |
| `0x0180fc` | unclassified alias/reference lead |
| `0x01829c` | unclassified alias/reference lead |
| `0x018626` | unclassified alias/reference lead |
| `0x01871c` | unclassified alias/reference lead |
| `0x018ec8` | unclassified alias/reference lead |
| `0x019080` | unclassified alias/reference lead |
| `0x019cde` | unclassified alias/reference lead |
| `0x01eee0` | bitmap render record receives buffer base |
| `0x01ef42` | buffer-clear/skip helper base |
| `0x01f070` | unclassified alias/reference lead |
| `0x01f18a` | unclassified alias/reference lead |
| `0x01f248` | unclassified alias/reference lead |
| `0x01f332` | unclassified alias/reference lead |
| `0x01f586` | word-mask writer wraps to base plus byte offset |
| `0x01f616` | solid-mask writer wraps to base plus byte offset |
| `0x01f6d4` | destination pointer setup falls back to base buffer |
| `0x01f804` | fixed-width writer wraps to base plus byte offset |
| `0x01f8fa` | unclassified alias/reference lead |
| `0x01f950` | unclassified alias/reference lead |
| `0x01f95a` | unclassified alias/reference lead |
| `0x01f9fc` | unclassified alias/reference lead |
| `0x01fa0a` | unclassified alias/reference lead |
| `0x01fa18` | unclassified alias/reference lead |
| `0x02fec0` | unclassified alias/reference lead |

## `0x00783a18`

Role: current render work record pointer

| Offset | Current classification |
| --- | --- |
| `0x01ed10` | record alternator publishes selected work record |
| `0x01ef6e` | band render entry loads it into A6 |

## `0x00783a1c`

Role: bitmap line stride in bytes

| Offset | Current classification |
| --- | --- |
| `0x01eeba` | `0x1ee9e` stores record width word times four |
| `0x01f52c` | word-mask writer advances destination by stride |
| `0x01f5ee` | solid-mask writer advances destination by stride |
| `0x01f696` | destination pointer setup scales rows by stride |
| `0x01f6e2` | unclassified alias/reference lead |
| `0x01f7ec` | fixed-width writer advances destination by stride |
| `0x01f864` | segment writer advances destination by stride |
| `0x01f8ec` | unclassified alias/reference lead |
| `0x01f926` | unclassified alias/reference lead |
| `0x01f9cc` | unclassified alias/reference lead |
| `0x01fa5e` | unclassified alias/reference lead |
| `0x01fe78` | unclassified alias/reference lead |
| `0x020292` | unclassified alias/reference lead |
| `0x0207ae` | unclassified alias/reference lead |
| `0x020cca` | unclassified alias/reference lead |
| `0x0212e6` | unclassified alias/reference lead |
| `0x021902` | unclassified alias/reference lead |
| `0x02201e` | unclassified alias/reference lead |
| `0x02273a` | unclassified alias/reference lead |
| `0x022f56` | unclassified alias/reference lead |
| `0x023772` | unclassified alias/reference lead |
| `0x024092` | unclassified alias/reference lead |
| `0x0249b2` | unclassified alias/reference lead |
| `0x0253d2` | unclassified alias/reference lead |
| `0x025df2` | unclassified alias/reference lead |
| `0x026912` | unclassified alias/reference lead |
| `0x027432` | unclassified alias/reference lead |
| `0x027868` | unclassified alias/reference lead |
| `0x027d9c` | unclassified alias/reference lead |
| `0x0283d2` | unclassified alias/reference lead |
| `0x028a08` | unclassified alias/reference lead |
| `0x02913e` | unclassified alias/reference lead |
| `0x029874` | unclassified alias/reference lead |
| `0x02a0aa` | unclassified alias/reference lead |
| `0x02a8e0` | unclassified alias/reference lead |
| `0x02b216` | unclassified alias/reference lead |
| `0x02bb4c` | unclassified alias/reference lead |
| `0x02c586` | unclassified alias/reference lead |
| `0x02cfc0` | unclassified alias/reference lead |
| `0x02dafa` | unclassified alias/reference lead |
| `0x02e646` | unclassified alias/reference lead |
| `0x02f294` | unclassified alias/reference lead |

## `0x00783a20`

Role: band row remainder/offset used by destination pointer setup

| Offset | Current classification |
| --- | --- |
| `0x01efa8` | computed from active render record by `0x1ef86` |
| `0x01f416` | used by span setup helper |
| `0x01f652` | used by destination pointer setup `0x1f626` |
| `0x01f6b4` | unclassified alias/reference lead |

## `0x00783a28`

Role: current band destination base pointer

| Offset | Current classification |
| --- | --- |
| `0x01efb8` | computed from render record base and band position |
| `0x01f3f2` | direct destination base load |
| `0x01f672` | destination pointer setup path |
| `0x01f690` | destination pointer setup path |

Current result: `0x1edc6` is the first confirmed bridge from queued
page/control records into a render work record, and its concrete
queue/list/context-slot copy contract is decoded in
`ic30_ic13_page_record_bridge.md`. `0x1ef6a` and helpers then render a band
using `0x783a18`, `0x783a1c`, `0x783a28`, and buffer base `0x7810b4`; complete
parser-produced page objects and all merge rules remain to be decoded.
