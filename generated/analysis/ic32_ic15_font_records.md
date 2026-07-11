# IC32/IC15 Candidate Font Records

String search is useful for labeling records, but the firmware stores the
selected context as the record start address, not the string address. For
named built-in records, the record start is the even address immediately after
the name/padding and begins with longword `0x00000014` or `0x00000015`. Other
name hits are likely embedded in glyph bitmap/data payloads.

## Firmware-Scanned Candidate Partitions

This table follows the same sequential resource scan shape as firmware
routines `0x1a616` and `0x1a9be`: `HEAD` records are skipped by length,
accepted type `0x14`/`0x15` font records are validated, and their record-start
firmware addresses feed the candidate list.

- accepted records: `24`
- class `1` records: total `12`, built-in low-window `12`, extension-window
  `0`
- class `0` records: total `12`, built-in low-window `12`, extension-window
  `0`
- final cursor windows: `0x7827a0=0x782324, 0x7827a4=0x782354,
  0x7827a8=0x782354, 0x7827ac=0x782354, 0x7827b0=0x782384, 0x7827b4=0x782384`
- `0x1569c` activation: class-zero uses `0x78287c = 0x782354`, `0x7827b8 =
  12`; class-one uses `0x78287c = 0x782324`, `0x7827b8 = 12`; each selected
  entry is marked active with high bit `0x80000000`.
- `0x156de` concrete symbol filtering: the built-in class-zero window starts
  with record `+0x22` words `0x0115` / `0x0155` / `0x0175` / `0x000e`, and
  class-one starts with `0x0115` / `0x0155` / `0x0175` / `0x000e`; a primary
  `0x0115` filter therefore keeps the three Roman-8 entries in the active
  window, moves `0x78287c` to the first survivor, and reduces `0x7827b8` from
  12 to 3.
- `0x14398` concrete active chooser: `0x13c06` ranks resource class first,
  then same-class built-ins use `0x1428c` to compare decoded height, byte
  `+0x2f`, signed byte `+0x30`, and byte `+0x31`. The class-zero Roman-8
  survivor tuples are `0x00004c:[1200, 0, 0, 3]` / `0x009fb0:[1200, 0, 3, 3]`
  / `0x0142e4:[850, 0, 0, 0]`, so the chooser writes selected slot `0x782364`
  / record `0x009fb0` to `0x7828a8`.
- `0x1519a` concrete height filtering: built-in class-zero decoded heights are
  `1200` / `1200` / `1200` / `1200` / `1200` / `1200` / `1200` / `1200` /
  `850` / `850` / `850` / `850`; requested height `0x04b0` keeps the eight
  `1200`-unit candidates via the +/-`0x19` range, while requested `0x0384`
  misses that range and the nearest-height fallback keeps the four `850`-unit
  candidates.
- `0x153c6` concrete spacing/pitch filtering: built-in class-zero spacing
  bytes are `0` / `0` / `0` / `0` / `0` / `0` / `0` / `0` / `0` / `0` / `0` /
  `0` and decoded pitches are `1000` / `1000` / `1000` / `1000` / `1000` /
  `1000` / `1000` / `1000` / `1666` / `1666` / `1666` / `1666`; requested
  spacing `0` plus pitch `0x03e8` keeps the eight `1000`-unit candidates via
  the +/-`5` range, while requested pitch `0x04b0` misses that range and
  `0x1562c` selects the next available pitch `1666`, keeping four candidates.

| Scan index | Name | Record start | Firmware address | Context longword | Class | Partition |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 0 | `(unnamed)` | `0x00004c` | `0x08004c` | `0x4008004c` | `0` | class-zero |
| 1 | `COURIER` | `0x000418` | `0x080418` | `0x44080418` | `0` | class-zero |
| 2 | `COURIER` | `0x000868` | `0x080868` | `0x44080868` | `0` | class-zero |
| 3 | `COURIER` | `0x000cb8` | `0x080cb8` | `0x40080cb8` | `0` | class-zero |
| 4 | `(unnamed)` | `0x009fb0` | `0x089fb0` | `0x40089fb0` | `0` | class-zero |
| 5 | `COURIER` | `0x00a37c` | `0x08a37c` | `0x4408a37c` | `0` | class-zero |
| 6 | `COURIER` | `0x00a7cc` | `0x08a7cc` | `0x4408a7cc` | `0` | class-zero |
| 7 | `COURIER` | `0x00ac1c` | `0x08ac1c` | `0x4008ac1c` | `0` | class-zero |
| 8 | `(unnamed)` | `0x0142e4` | `0x0942e4` | `0x400942e4` | `0` | class-zero |
| 9 | `LINE_PRINTER` | `0x0146b4` | `0x0946b4` | `0x440946b4` | `0` | class-zero |
| 10 | `LINE_PRINTER` | `0x014b08` | `0x094b08` | `0x44094b08` | `0` | class-zero |
| 11 | `LINE_PRINTER` | `0x014f5c` | `0x094f5c` | `0x40094f5c` | `0` | class-zero |
| 12 | `(unnamed)` | `0x019d18` | `0x099d18` | `0x40099d18` | `1` | class-one |
| 13 | `COURIER` | `0x01a0e4` | `0x09a0e4` | `0x4409a0e4` | `1` | class-one |
| 14 | `COURIER` | `0x01a534` | `0x09a534` | `0x4409a534` | `1` | class-one |
| 15 | `COURIER` | `0x01a984` | `0x09a984` | `0x4009a984` | `1` | class-one |
| 16 | `(unnamed)` | `0x023484` | `0x0a3484` | `0x400a3484` | `1` | class-one |
| 17 | `COURIER` | `0x023850` | `0x0a3850` | `0x440a3850` | `1` | class-one |
| 18 | `COURIER` | `0x023ca0` | `0x0a3ca0` | `0x440a3ca0` | `1` | class-one |
| 19 | `COURIER` | `0x0240f0` | `0x0a40f0` | `0x400a40f0` | `1` | class-one |
| 20 | `(unnamed)` | `0x02d4aa` | `0x0ad4aa` | `0x400ad4aa` | `1` | class-one |
| 21 | `LINE_PRINTER` | `0x02d87a` | `0x0ad87a` | `0x440ad87a` | `1` | class-one |
| 22 | `LINE_PRINTER` | `0x02dcce` | `0x0adcce` | `0x440adcce` | `1` | class-one |
| 23 | `LINE_PRINTER` | `0x02e122` | `0x0ae122` | `0x400ae122` | `1` | class-one |

The verified built-in ROM image contributes only low-window records here:
twelve class `0` records and twelve class `1` records. The extension-window
counters remain zero until cartridge or external resource ranges are scanned.

## String-Labeled Candidate Records

| Name | Name offset | Header-like | Record start | Firmware address | Length | Next same-name delta | Offset table |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| `COURIER` | `0x000410` | yes | `0x000418` | `0x080418` | 1104 | 1104 | `0x000462` |
| `COURIER` | `0x000860` | yes | `0x000868` | `0x080868` | 1104 | 1104 | `0x0008b2` |
| `COURIER` | `0x000cb0` | yes | `0x000cb8` | `0x080cb8` | 37624 | 976 | `0x000d02` |
| `COURIER` | `0x001080` | no | `0x001088` | `0x081088` | 167837728 | 37620 | `0x001091` |
| `COURIER` | `0x00a374` | yes | `0x00a37c` | `0x08a37c` | 1104 | 1104 | `0x00a3c6` |
| `COURIER` | `0x00a7c4` | yes | `0x00a7cc` | `0x08a7cc` | 1104 | 1104 | `0x00a816` |
| `COURIER` | `0x00ac14` | yes | `0x00ac1c` | `0x08ac1c` | 38600 | 976 | `0x00ac66` |
| `COURIER` | `0x00afe4` | no | `0x00afec` | `0x08afec` | 167837727 | 61688 | `0x00aff7` |
| `LINE_PRINTER` | `0x0146a8` | yes | `0x0146b4` | `0x0946b4` | 1108 | 1108 | `0x0146fe` |
| `LINE_PRINTER` | `0x014afc` | yes | `0x014b08` | `0x094b08` | 1108 | 1108 | `0x014b52` |
| `LINE_PRINTER` | `0x014f50` | yes | `0x014f5c` | `0x094f5c` | 19900 | 980 | `0x014fa6` |
| `LINE_PRINTER` | `0x015324` | no | `0x015330` | `0x095330` | 167837718 | 99658 | `0x015334` |
| `COURIER` | `0x01a0dc` | yes | `0x01a0e4` | `0x09a0e4` | 1104 | 1104 | `0x01a12e` |
| `COURIER` | `0x01a52c` | yes | `0x01a534` | `0x09a534` | 1104 | 1104 | `0x01a57e` |
| `COURIER` | `0x01a97c` | yes | `0x01a984` | `0x09a984` | 35584 | 976 | `0x01a9ce` |
| `COURIER` | `0x01ad4c` | no | `0x01ad54` | `0x09ad54` | 167837705 | 35580 | `0x01ad74` |
| `COURIER` | `0x023848` | yes | `0x023850` | `0x0a3850` | 1104 | 1104 | `0x02389a` |
| `COURIER` | `0x023c98` | yes | `0x023ca0` | `0x0a3ca0` | 1104 | 1104 | `0x023cea` |
| `COURIER` | `0x0240e8` | yes | `0x0240f0` | `0x0a40f0` | 37818 | 976 | `0x02413a` |
| `COURIER` | `0x0244b8` | no | `0x0244c0` | `0x0a44c0` | 167837707 |  | `0x0244df` |
| `LINE_PRINTER` | `0x02d86e` | yes | `0x02d87a` | `0x0ad87a` | 1108 | 1108 | `0x02d8c4` |
| `LINE_PRINTER` | `0x02dcc2` | yes | `0x02dcce` | `0x0adcce` | 1108 | 1108 | `0x02dd18` |
| `LINE_PRINTER` | `0x02e116` | yes | `0x02e122` | `0x0ae122` | 20062 | 980 | `0x02e16c` |
| `LINE_PRINTER` | `0x02e4ea` | no | `0x02e4f6` | `0x0ae4f6` | 167837700 |  | `0x02e50c` |

## COURIER @0x000410

- firmware record start: `0x000418`
- built-in firmware address: `0x080418`
- header-like record: `yes`
- length field at record + 4: `0x00000450` (1104)
- next same-name delta: `1104`
- candidate offset-table delta: `0x004a`
- candidate offset-table address: `0x000462`

First 24 header words, unsigned and signed:

| Index | Address | Unsigned | Signed |
| ---: | --- | ---: | ---: |
| 0 | `0x000418` | `0x0000` | 0 |
| 1 | `0x00041a` | `0x0014` | 20 |
| 2 | `0x00041c` | `0x0000` | 0 |
| 3 | `0x00041e` | `0x0450` | 1104 |
| 4 | `0x000420` | `0x004a` | 74 |
| 5 | `0x000422` | `0x0000` | 0 |
| 6 | `0x000424` | `0x0200` | 512 |
| 7 | `0x000426` | `0x0001` | 1 |
| 8 | `0x000428` | `0x00ff` | 255 |
| 9 | `0x00042a` | `0x001e` | 30 |
| 10 | `0x00042c` | `0x0036` | 54 |
| 11 | `0x00042e` | `0x0028` | 40 |
| 12 | `0x000430` | `0x000d` | 13 |
| 13 | `0x000432` | `0xfff7` | -9 |
| 14 | `0x000434` | `0x001e` | 30 |
| 15 | `0x000436` | `0x0032` | 50 |
| 16 | `0x000438` | `0x0000` | 0 |
| 17 | `0x00043a` | `0x0155` | 341 |
| 18 | `0x00043c` | `0x0078` | 120 |
| 19 | `0x00043e` | `0x0000` | 0 |
| 20 | `0x000440` | `0x00c8` | 200 |
| 21 | `0x000442` | `0x0000` | 0 |
| 22 | `0x000444` | `0x005c` | 92 |
| 23 | `0x000446` | `0x0000` | 0 |

First 16 firmware offset-table entries. Entries are 32-bit offsets relative to
the selected record base.

| Index | Relative offset | Resource target |
| ---: | ---: | ---: |
| 0 | `0x00007792` | `0x007baa` |
| 1 | `0x00007810` | `0x007c28` |
| 2 | `0x0000788e` | `0x007ca6` |
| 3 | `0x0000790c` | `0x007d24` |
| 4 | `0x00007692` | `0x007aaa` |
| 5 | `0x00007714` | `0x007b2c` |
| 6 | `0x0000798a` | `0x007da2` |
| 7 | `0x000079aa` | `0x007dc2` |
| 8 | `0x00007a2c` | `0x007e44` |
| 9 | `0x00007aae` | `0x007ec6` |
| 10 | `0x00007b30` | `0x007f48` |
| 11 | `0x00007ba2` | `0x007fba` |
| 12 | `0x00007c28` | `0x008040` |
| 13 | `0x00007c74` | `0x00808c` |
| 14 | `0x00007d0a` | `0x008122` |
| 15 | `0x00007d70` | `0x008188` |

## COURIER @0x000860

- firmware record start: `0x000868`
- built-in firmware address: `0x080868`
- header-like record: `yes`
- length field at record + 4: `0x00000450` (1104)
- next same-name delta: `1104`
- candidate offset-table delta: `0x004a`
- candidate offset-table address: `0x0008b2`

First 24 header words, unsigned and signed:

| Index | Address | Unsigned | Signed |
| ---: | --- | ---: | ---: |
| 0 | `0x000868` | `0x0000` | 0 |
| 1 | `0x00086a` | `0x0014` | 20 |
| 2 | `0x00086c` | `0x0000` | 0 |
| 3 | `0x00086e` | `0x0450` | 1104 |
| 4 | `0x000870` | `0x004a` | 74 |
| 5 | `0x000872` | `0x0000` | 0 |
| 6 | `0x000874` | `0x0200` | 512 |
| 7 | `0x000876` | `0x0001` | 1 |
| 8 | `0x000878` | `0x00ff` | 255 |
| 9 | `0x00087a` | `0x001e` | 30 |
| 10 | `0x00087c` | `0x0036` | 54 |
| 11 | `0x00087e` | `0x0028` | 40 |
| 12 | `0x000880` | `0x000d` | 13 |
| 13 | `0x000882` | `0xfff7` | -9 |
| 14 | `0x000884` | `0x001e` | 30 |
| 15 | `0x000886` | `0x0032` | 50 |
| 16 | `0x000888` | `0x0000` | 0 |
| 17 | `0x00088a` | `0x0175` | 373 |
| 18 | `0x00088c` | `0x0078` | 120 |
| 19 | `0x00088e` | `0x0000` | 0 |
| 20 | `0x000890` | `0x00c8` | 200 |
| 21 | `0x000892` | `0x0000` | 0 |
| 22 | `0x000894` | `0x005c` | 92 |
| 23 | `0x000896` | `0x0000` | 0 |

First 16 firmware offset-table entries. Entries are 32-bit offsets relative to
the selected record base.

| Index | Relative offset | Resource target |
| ---: | ---: | ---: |
| 0 | `0x00007342` | `0x007baa` |
| 1 | `0x000073c0` | `0x007c28` |
| 2 | `0x0000743e` | `0x007ca6` |
| 3 | `0x000074bc` | `0x007d24` |
| 4 | `0x00007242` | `0x007aaa` |
| 5 | `0x000072c4` | `0x007b2c` |
| 6 | `0x0000753a` | `0x007da2` |
| 7 | `0x0000755a` | `0x007dc2` |
| 8 | `0x000075dc` | `0x007e44` |
| 9 | `0x0000765e` | `0x007ec6` |
| 10 | `0x000076e0` | `0x007f48` |
| 11 | `0x00007752` | `0x007fba` |
| 12 | `0x000077d8` | `0x008040` |
| 13 | `0x00007824` | `0x00808c` |
| 14 | `0x000078ba` | `0x008122` |
| 15 | `0x00007920` | `0x008188` |

## COURIER @0x000cb0

- firmware record start: `0x000cb8`
- built-in firmware address: `0x080cb8`
- header-like record: `yes`
- length field at record + 4: `0x000092f8` (37624)
- next same-name delta: `976`
- candidate offset-table delta: `0x004a`
- candidate offset-table address: `0x000d02`

First 24 header words, unsigned and signed:

| Index | Address | Unsigned | Signed |
| ---: | --- | ---: | ---: |
| 0 | `0x000cb8` | `0x0000` | 0 |
| 1 | `0x000cba` | `0x0014` | 20 |
| 2 | `0x000cbc` | `0x0000` | 0 |
| 3 | `0x000cbe` | `0x92f8` | -27912 |
| 4 | `0x000cc0` | `0x004a` | 74 |
| 5 | `0x000cc2` | `0x0000` | 0 |
| 6 | `0x000cc4` | `0x0100` | 256 |
| 7 | `0x000cc6` | `0x0021` | 33 |
| 8 | `0x000cc8` | `0x00ff` | 255 |
| 9 | `0x000cca` | `0x001e` | 30 |
| 10 | `0x000ccc` | `0x0032` | 50 |
| 11 | `0x000cce` | `0x0024` | 36 |
| 12 | `0x000cd0` | `0x000d` | 13 |
| 13 | `0x000cd2` | `0xfff7` | -9 |
| 14 | `0x000cd4` | `0x001e` | 30 |
| 15 | `0x000cd6` | `0x0032` | 50 |
| 16 | `0x000cd8` | `0x0000` | 0 |
| 17 | `0x000cda` | `0x000e` | 14 |
| 18 | `0x000cdc` | `0x0078` | 120 |
| 19 | `0x000cde` | `0x0000` | 0 |
| 20 | `0x000ce0` | `0x00c8` | 200 |
| 21 | `0x000ce2` | `0x0000` | 0 |
| 22 | `0x000ce4` | `0x005c` | 92 |
| 23 | `0x000ce6` | `0x0000` | 0 |

First 16 firmware offset-table entries. Entries are 32-bit offsets relative to
the selected record base.

| Index | Relative offset | Resource target |
| ---: | ---: | ---: |
| 0 | `0x000003d0` | `0x001088` |
| 1 | `0x0000041a` | `0x0010d2` |
| 2 | `0x00000468` | `0x001120` |
| 3 | `0x0000050a` | `0x0011c2` |
| 4 | `0x000005b4` | `0x00126c` |
| 5 | `0x00000642` | `0x0012fa` |
| 6 | `0x00009212` | `0x009eca` |
| 7 | `0x000006ea` | `0x0013a2` |
| 8 | `0x00000744` | `0x0013fc` |
| 9 | `0x0000079e` | `0x001456` |
| 10 | `0x000007fc` | `0x0014b4` |
| 11 | `0x0000086a` | `0x001522` |
| 12 | `0x00000892` | `0x00154a` |
| 13 | `0x000008b0` | `0x001568` |
| 14 | `0x000008ca` | `0x001582` |
| 15 | `0x00000974` | `0x00162c` |

## COURIER @0x00a374

- firmware record start: `0x00a37c`
- built-in firmware address: `0x08a37c`
- header-like record: `yes`
- length field at record + 4: `0x00000450` (1104)
- next same-name delta: `1104`
- candidate offset-table delta: `0x004a`
- candidate offset-table address: `0x00a3c6`

First 24 header words, unsigned and signed:

| Index | Address | Unsigned | Signed |
| ---: | --- | ---: | ---: |
| 0 | `0x00a37c` | `0x0000` | 0 |
| 1 | `0x00a37e` | `0x0014` | 20 |
| 2 | `0x00a380` | `0x0000` | 0 |
| 3 | `0x00a382` | `0x0450` | 1104 |
| 4 | `0x00a384` | `0x004a` | 74 |
| 5 | `0x00a386` | `0x0000` | 0 |
| 6 | `0x00a388` | `0x0200` | 512 |
| 7 | `0x00a38a` | `0x0001` | 1 |
| 8 | `0x00a38c` | `0x00ff` | 255 |
| 9 | `0x00a38e` | `0x001e` | 30 |
| 10 | `0x00a390` | `0x0036` | 54 |
| 11 | `0x00a392` | `0x0028` | 40 |
| 12 | `0x00a394` | `0x000d` | 13 |
| 13 | `0x00a396` | `0xfff7` | -9 |
| 14 | `0x00a398` | `0x001e` | 30 |
| 15 | `0x00a39a` | `0x0032` | 50 |
| 16 | `0x00a39c` | `0x0000` | 0 |
| 17 | `0x00a39e` | `0x0155` | 341 |
| 18 | `0x00a3a0` | `0x0078` | 120 |
| 19 | `0x00a3a2` | `0x0000` | 0 |
| 20 | `0x00a3a4` | `0x00c8` | 200 |
| 21 | `0x00a3a6` | `0x0000` | 0 |
| 22 | `0x00a3a8` | `0x0060` | 96 |
| 23 | `0x00a3aa` | `0x0000` | 0 |

First 16 firmware offset-table entries. Entries are 32-bit offsets relative to
the selected record base.

| Index | Relative offset | Resource target |
| ---: | ---: | ---: |
| 0 | `0x00007b5a` | `0x011ed6` |
| 1 | `0x00007bd8` | `0x011f54` |
| 2 | `0x00007c56` | `0x011fd2` |
| 3 | `0x00007cd4` | `0x012050` |
| 4 | `0x00007a5a` | `0x011dd6` |
| 5 | `0x00007adc` | `0x011e58` |
| 6 | `0x00007d52` | `0x0120ce` |
| 7 | `0x00007d72` | `0x0120ee` |
| 8 | `0x00007df4` | `0x012170` |
| 9 | `0x00007e76` | `0x0121f2` |
| 10 | `0x00007ef8` | `0x012274` |
| 11 | `0x00007f6a` | `0x0122e6` |
| 12 | `0x00007ff0` | `0x01236c` |
| 13 | `0x0000803c` | `0x0123b8` |
| 14 | `0x000080d2` | `0x01244e` |
| 15 | `0x00008138` | `0x0124b4` |

## COURIER @0x00a7c4

- firmware record start: `0x00a7cc`
- built-in firmware address: `0x08a7cc`
- header-like record: `yes`
- length field at record + 4: `0x00000450` (1104)
- next same-name delta: `1104`
- candidate offset-table delta: `0x004a`
- candidate offset-table address: `0x00a816`

First 24 header words, unsigned and signed:

| Index | Address | Unsigned | Signed |
| ---: | --- | ---: | ---: |
| 0 | `0x00a7cc` | `0x0000` | 0 |
| 1 | `0x00a7ce` | `0x0014` | 20 |
| 2 | `0x00a7d0` | `0x0000` | 0 |
| 3 | `0x00a7d2` | `0x0450` | 1104 |
| 4 | `0x00a7d4` | `0x004a` | 74 |
| 5 | `0x00a7d6` | `0x0000` | 0 |
| 6 | `0x00a7d8` | `0x0200` | 512 |
| 7 | `0x00a7da` | `0x0001` | 1 |
| 8 | `0x00a7dc` | `0x00ff` | 255 |
| 9 | `0x00a7de` | `0x001e` | 30 |
| 10 | `0x00a7e0` | `0x0036` | 54 |
| 11 | `0x00a7e2` | `0x0028` | 40 |
| 12 | `0x00a7e4` | `0x000d` | 13 |
| 13 | `0x00a7e6` | `0xfff7` | -9 |
| 14 | `0x00a7e8` | `0x001e` | 30 |
| 15 | `0x00a7ea` | `0x0032` | 50 |
| 16 | `0x00a7ec` | `0x0000` | 0 |
| 17 | `0x00a7ee` | `0x0175` | 373 |
| 18 | `0x00a7f0` | `0x0078` | 120 |
| 19 | `0x00a7f2` | `0x0000` | 0 |
| 20 | `0x00a7f4` | `0x00c8` | 200 |
| 21 | `0x00a7f6` | `0x0000` | 0 |
| 22 | `0x00a7f8` | `0x0060` | 96 |
| 23 | `0x00a7fa` | `0x0000` | 0 |

First 16 firmware offset-table entries. Entries are 32-bit offsets relative to
the selected record base.

| Index | Relative offset | Resource target |
| ---: | ---: | ---: |
| 0 | `0x0000770a` | `0x011ed6` |
| 1 | `0x00007788` | `0x011f54` |
| 2 | `0x00007806` | `0x011fd2` |
| 3 | `0x00007884` | `0x012050` |
| 4 | `0x0000760a` | `0x011dd6` |
| 5 | `0x0000768c` | `0x011e58` |
| 6 | `0x00007902` | `0x0120ce` |
| 7 | `0x00007922` | `0x0120ee` |
| 8 | `0x000079a4` | `0x012170` |
| 9 | `0x00007a26` | `0x0121f2` |
| 10 | `0x00007aa8` | `0x012274` |
| 11 | `0x00007b1a` | `0x0122e6` |
| 12 | `0x00007ba0` | `0x01236c` |
| 13 | `0x00007bec` | `0x0123b8` |
| 14 | `0x00007c82` | `0x01244e` |
| 15 | `0x00007ce8` | `0x0124b4` |

## COURIER @0x00ac14

- firmware record start: `0x00ac1c`
- built-in firmware address: `0x08ac1c`
- header-like record: `yes`
- length field at record + 4: `0x000096c8` (38600)
- next same-name delta: `976`
- candidate offset-table delta: `0x004a`
- candidate offset-table address: `0x00ac66`

First 24 header words, unsigned and signed:

| Index | Address | Unsigned | Signed |
| ---: | --- | ---: | ---: |
| 0 | `0x00ac1c` | `0x0000` | 0 |
| 1 | `0x00ac1e` | `0x0014` | 20 |
| 2 | `0x00ac20` | `0x0000` | 0 |
| 3 | `0x00ac22` | `0x96c8` | -26936 |
| 4 | `0x00ac24` | `0x004a` | 74 |
| 5 | `0x00ac26` | `0x0000` | 0 |
| 6 | `0x00ac28` | `0x0100` | 256 |
| 7 | `0x00ac2a` | `0x0021` | 33 |
| 8 | `0x00ac2c` | `0x00ff` | 255 |
| 9 | `0x00ac2e` | `0x001e` | 30 |
| 10 | `0x00ac30` | `0x0032` | 50 |
| 11 | `0x00ac32` | `0x0024` | 36 |
| 12 | `0x00ac34` | `0x000d` | 13 |
| 13 | `0x00ac36` | `0xfff7` | -9 |
| 14 | `0x00ac38` | `0x001e` | 30 |
| 15 | `0x00ac3a` | `0x0032` | 50 |
| 16 | `0x00ac3c` | `0x0000` | 0 |
| 17 | `0x00ac3e` | `0x000e` | 14 |
| 18 | `0x00ac40` | `0x0078` | 120 |
| 19 | `0x00ac42` | `0x0000` | 0 |
| 20 | `0x00ac44` | `0x00c8` | 200 |
| 21 | `0x00ac46` | `0x0000` | 0 |
| 22 | `0x00ac48` | `0x0060` | 96 |
| 23 | `0x00ac4a` | `0x0000` | 0 |

First 16 firmware offset-table entries. Entries are 32-bit offsets relative to
the selected record base.

| Index | Relative offset | Resource target |
| ---: | ---: | ---: |
| 0 | `0x000003d0` | `0x00afec` |
| 1 | `0x00000418` | `0x00b034` |
| 2 | `0x0000046a` | `0x00b086` |
| 3 | `0x00000508` | `0x00b124` |
| 4 | `0x000005ae` | `0x00b1ca` |
| 5 | `0x00000640` | `0x00b25c` |
| 6 | `0x000095dc` | `0x0141f8` |
| 7 | `0x000006e8` | `0x00b304` |
| 8 | `0x0000073c` | `0x00b358` |
| 9 | `0x00000790` | `0x00b3ac` |
| 10 | `0x000007f2` | `0x00b40e` |
| 11 | `0x0000086c` | `0x00b488` |
| 12 | `0x00000898` | `0x00b4b4` |
| 13 | `0x000008be` | `0x00b4da` |
| 14 | `0x000008dc` | `0x00b4f8` |
| 15 | `0x00000986` | `0x00b5a2` |

## LINE_PRINTER @0x0146a8

- firmware record start: `0x0146b4`
- built-in firmware address: `0x0946b4`
- header-like record: `yes`
- length field at record + 4: `0x00000454` (1108)
- next same-name delta: `1108`
- candidate offset-table delta: `0x004a`
- candidate offset-table address: `0x0146fe`

First 24 header words, unsigned and signed:

| Index | Address | Unsigned | Signed |
| ---: | --- | ---: | ---: |
| 0 | `0x0146b4` | `0x0000` | 0 |
| 1 | `0x0146b6` | `0x0014` | 20 |
| 2 | `0x0146b8` | `0x0000` | 0 |
| 3 | `0x0146ba` | `0x0454` | 1108 |
| 4 | `0x0146bc` | `0x004a` | 74 |
| 5 | `0x0146be` | `0x0000` | 0 |
| 6 | `0x0146c0` | `0x0200` | 512 |
| 7 | `0x0146c2` | `0x0001` | 1 |
| 8 | `0x0146c4` | `0x00ff` | 255 |
| 9 | `0x0146c6` | `0x0012` | 18 |
| 10 | `0x0146c8` | `0x0027` | 39 |
| 11 | `0x0146ca` | `0x001c` | 28 |
| 12 | `0x0146cc` | `0x000a` | 10 |
| 13 | `0x0146ce` | `0xfffa` | -6 |
| 14 | `0x0146d0` | `0x0012` | 18 |
| 15 | `0x0146d2` | `0x0026` | 38 |
| 16 | `0x0146d4` | `0x0000` | 0 |
| 17 | `0x0146d6` | `0x0155` | 341 |
| 18 | `0x0146d8` | `0x0048` | 72 |
| 19 | `0x0146da` | `0x0000` | 0 |
| 20 | `0x0146dc` | `0x008d` | 141 |
| 21 | `0x0146de` | `0xab00` | -21760 |
| 22 | `0x0146e0` | `0x0044` | 68 |
| 23 | `0x0146e2` | `0x0000` | 0 |

First 16 firmware offset-table entries. Entries are 32-bit offsets relative to
the selected record base.

| Index | Relative offset | Resource target |
| ---: | ---: | ---: |
| 0 | `0x0000407c` | `0x018730` |
| 1 | `0x000040a6` | `0x01875a` |
| 2 | `0x000040d0` | `0x018784` |
| 3 | `0x0000412e` | `0x0187e2` |
| 4 | `0x00004012` | `0x0186c6` |
| 5 | `0x00004048` | `0x0186fc` |
| 6 | `0x00004194` | `0x018848` |
| 7 | `0x000041b4` | `0x018868` |
| 8 | `0x00004216` | `0x0188ca` |
| 9 | `0x00004240` | `0x0188f4` |
| 10 | `0x00004292` | `0x018946` |
| 11 | `0x000042e0` | `0x018994` |
| 12 | `0x00004312` | `0x0189c6` |
| 13 | `0x0000434c` | `0x018a00` |
| 14 | `0x000043d2` | `0x018a86` |
| 15 | `0x00004424` | `0x018ad8` |

## LINE_PRINTER @0x014afc

- firmware record start: `0x014b08`
- built-in firmware address: `0x094b08`
- header-like record: `yes`
- length field at record + 4: `0x00000454` (1108)
- next same-name delta: `1108`
- candidate offset-table delta: `0x004a`
- candidate offset-table address: `0x014b52`

First 24 header words, unsigned and signed:

| Index | Address | Unsigned | Signed |
| ---: | --- | ---: | ---: |
| 0 | `0x014b08` | `0x0000` | 0 |
| 1 | `0x014b0a` | `0x0014` | 20 |
| 2 | `0x014b0c` | `0x0000` | 0 |
| 3 | `0x014b0e` | `0x0454` | 1108 |
| 4 | `0x014b10` | `0x004a` | 74 |
| 5 | `0x014b12` | `0x0000` | 0 |
| 6 | `0x014b14` | `0x0200` | 512 |
| 7 | `0x014b16` | `0x0001` | 1 |
| 8 | `0x014b18` | `0x00ff` | 255 |
| 9 | `0x014b1a` | `0x0012` | 18 |
| 10 | `0x014b1c` | `0x0027` | 39 |
| 11 | `0x014b1e` | `0x001c` | 28 |
| 12 | `0x014b20` | `0x000a` | 10 |
| 13 | `0x014b22` | `0xfffa` | -6 |
| 14 | `0x014b24` | `0x0012` | 18 |
| 15 | `0x014b26` | `0x0026` | 38 |
| 16 | `0x014b28` | `0x0000` | 0 |
| 17 | `0x014b2a` | `0x0175` | 373 |
| 18 | `0x014b2c` | `0x0048` | 72 |
| 19 | `0x014b2e` | `0x0000` | 0 |
| 20 | `0x014b30` | `0x008d` | 141 |
| 21 | `0x014b32` | `0xab00` | -21760 |
| 22 | `0x014b34` | `0x0044` | 68 |
| 23 | `0x014b36` | `0x0000` | 0 |

First 16 firmware offset-table entries. Entries are 32-bit offsets relative to
the selected record base.

| Index | Relative offset | Resource target |
| ---: | ---: | ---: |
| 0 | `0x00003c28` | `0x018730` |
| 1 | `0x00003c52` | `0x01875a` |
| 2 | `0x00003c7c` | `0x018784` |
| 3 | `0x00003cda` | `0x0187e2` |
| 4 | `0x00003bbe` | `0x0186c6` |
| 5 | `0x00003bf4` | `0x0186fc` |
| 6 | `0x00003d40` | `0x018848` |
| 7 | `0x00003d60` | `0x018868` |
| 8 | `0x00003dc2` | `0x0188ca` |
| 9 | `0x00003dec` | `0x0188f4` |
| 10 | `0x00003e3e` | `0x018946` |
| 11 | `0x00003e8c` | `0x018994` |
| 12 | `0x00003ebe` | `0x0189c6` |
| 13 | `0x00003ef8` | `0x018a00` |
| 14 | `0x00003f7e` | `0x018a86` |
| 15 | `0x00003fd0` | `0x018ad8` |

## LINE_PRINTER @0x014f50

- firmware record start: `0x014f5c`
- built-in firmware address: `0x094f5c`
- header-like record: `yes`
- length field at record + 4: `0x00004dbc` (19900)
- next same-name delta: `980`
- candidate offset-table delta: `0x004a`
- candidate offset-table address: `0x014fa6`

First 24 header words, unsigned and signed:

| Index | Address | Unsigned | Signed |
| ---: | --- | ---: | ---: |
| 0 | `0x014f5c` | `0x0000` | 0 |
| 1 | `0x014f5e` | `0x0014` | 20 |
| 2 | `0x014f60` | `0x0000` | 0 |
| 3 | `0x014f62` | `0x4dbc` | 19900 |
| 4 | `0x014f64` | `0x004a` | 74 |
| 5 | `0x014f66` | `0x0000` | 0 |
| 6 | `0x014f68` | `0x0100` | 256 |
| 7 | `0x014f6a` | `0x0021` | 33 |
| 8 | `0x014f6c` | `0x00ff` | 255 |
| 9 | `0x014f6e` | `0x0012` | 18 |
| 10 | `0x014f70` | `0x0027` | 39 |
| 11 | `0x014f72` | `0x001c` | 28 |
| 12 | `0x014f74` | `0x000a` | 10 |
| 13 | `0x014f76` | `0xfffa` | -6 |
| 14 | `0x014f78` | `0x0012` | 18 |
| 15 | `0x014f7a` | `0x0026` | 38 |
| 16 | `0x014f7c` | `0x0000` | 0 |
| 17 | `0x014f7e` | `0x000e` | 14 |
| 18 | `0x014f80` | `0x0048` | 72 |
| 19 | `0x014f82` | `0x0000` | 0 |
| 20 | `0x014f84` | `0x008d` | 141 |
| 21 | `0x014f86` | `0xab00` | -21760 |
| 22 | `0x014f88` | `0x0044` | 68 |
| 23 | `0x014f8a` | `0x0000` | 0 |

First 16 firmware offset-table entries. Entries are 32-bit offsets relative to
the selected record base.

| Index | Relative offset | Resource target |
| ---: | ---: | ---: |
| 0 | `0x000003d4` | `0x015330` |
| 1 | `0x0000040a` | `0x015366` |
| 2 | `0x0000042c` | `0x015388` |
| 3 | `0x00000496` | `0x0153f2` |
| 4 | `0x000004d0` | `0x01542c` |
| 5 | `0x0000053a` | `0x015496` |
| 6 | `0x00004d18` | `0x019c74` |
| 7 | `0x00000596` | `0x0154f2` |
| 8 | `0x000005d2` | `0x01552e` |
| 9 | `0x0000060e` | `0x01556a` |
| 10 | `0x00000634` | `0x015590` |
| 11 | `0x0000065c` | `0x0155b8` |
| 12 | `0x0000067a` | `0x0155d6` |
| 13 | `0x0000068a` | `0x0155e6` |
| 14 | `0x0000069e` | `0x0155fa` |
| 15 | `0x000006da` | `0x015636` |

## COURIER @0x01a0dc

- firmware record start: `0x01a0e4`
- built-in firmware address: `0x09a0e4`
- header-like record: `yes`
- length field at record + 4: `0x00000450` (1104)
- next same-name delta: `1104`
- candidate offset-table delta: `0x004a`
- candidate offset-table address: `0x01a12e`

First 24 header words, unsigned and signed:

| Index | Address | Unsigned | Signed |
| ---: | --- | ---: | ---: |
| 0 | `0x01a0e4` | `0x0000` | 0 |
| 1 | `0x01a0e6` | `0x0014` | 20 |
| 2 | `0x01a0e8` | `0x0000` | 0 |
| 3 | `0x01a0ea` | `0x0450` | 1104 |
| 4 | `0x01a0ec` | `0x004a` | 74 |
| 5 | `0x01a0ee` | `0x0000` | 0 |
| 6 | `0x01a0f0` | `0x0200` | 512 |
| 7 | `0x01a0f2` | `0x0001` | 1 |
| 8 | `0x01a0f4` | `0x00ff` | 255 |
| 9 | `0x01a0f6` | `0x001e` | 30 |
| 10 | `0x01a0f8` | `0x0036` | 54 |
| 11 | `0x01a0fa` | `0x0028` | 40 |
| 12 | `0x01a0fc` | `0x000d` | 13 |
| 13 | `0x01a0fe` | `0xfff7` | -9 |
| 14 | `0x01a100` | `0x001e` | 30 |
| 15 | `0x01a102` | `0x0032` | 50 |
| 16 | `0x01a104` | `0x0100` | 256 |
| 17 | `0x01a106` | `0x0155` | 341 |
| 18 | `0x01a108` | `0x0078` | 120 |
| 19 | `0x01a10a` | `0x0000` | 0 |
| 20 | `0x01a10c` | `0x00c8` | 200 |
| 21 | `0x01a10e` | `0x0000` | 0 |
| 22 | `0x01a110` | `0x005c` | 92 |
| 23 | `0x01a112` | `0x0000` | 0 |

First 16 firmware offset-table entries. Entries are 32-bit offsets relative to
the selected record base.

| Index | Relative offset | Resource target |
| ---: | ---: | ---: |
| 0 | `0x00007128` | `0x02120c` |
| 1 | `0x000071a2` | `0x021286` |
| 2 | `0x0000721c` | `0x021300` |
| 3 | `0x0000728a` | `0x02136e` |
| 4 | `0x00007048` | `0x02112c` |
| 5 | `0x000070ba` | `0x02119e` |
| 6 | `0x000072e8` | `0x0213cc` |
| 7 | `0x00007308` | `0x0213ec` |
| 8 | `0x0000738a` | `0x02146e` |
| 9 | `0x0000740c` | `0x0214f0` |
| 10 | `0x0000748e` | `0x021572` |
| 11 | `0x000074fc` | `0x0215e0` |
| 12 | `0x00007556` | `0x02163a` |
| 13 | `0x000075ba` | `0x02169e` |
| 14 | `0x0000762a` | `0x02170e` |
| 15 | `0x00007690` | `0x021774` |

## COURIER @0x01a52c

- firmware record start: `0x01a534`
- built-in firmware address: `0x09a534`
- header-like record: `yes`
- length field at record + 4: `0x00000450` (1104)
- next same-name delta: `1104`
- candidate offset-table delta: `0x004a`
- candidate offset-table address: `0x01a57e`

First 24 header words, unsigned and signed:

| Index | Address | Unsigned | Signed |
| ---: | --- | ---: | ---: |
| 0 | `0x01a534` | `0x0000` | 0 |
| 1 | `0x01a536` | `0x0014` | 20 |
| 2 | `0x01a538` | `0x0000` | 0 |
| 3 | `0x01a53a` | `0x0450` | 1104 |
| 4 | `0x01a53c` | `0x004a` | 74 |
| 5 | `0x01a53e` | `0x0000` | 0 |
| 6 | `0x01a540` | `0x0200` | 512 |
| 7 | `0x01a542` | `0x0001` | 1 |
| 8 | `0x01a544` | `0x00ff` | 255 |
| 9 | `0x01a546` | `0x001e` | 30 |
| 10 | `0x01a548` | `0x0036` | 54 |
| 11 | `0x01a54a` | `0x0028` | 40 |
| 12 | `0x01a54c` | `0x000d` | 13 |
| 13 | `0x01a54e` | `0xfff7` | -9 |
| 14 | `0x01a550` | `0x001e` | 30 |
| 15 | `0x01a552` | `0x0032` | 50 |
| 16 | `0x01a554` | `0x0100` | 256 |
| 17 | `0x01a556` | `0x0175` | 373 |
| 18 | `0x01a558` | `0x0078` | 120 |
| 19 | `0x01a55a` | `0x0000` | 0 |
| 20 | `0x01a55c` | `0x00c8` | 200 |
| 21 | `0x01a55e` | `0x0000` | 0 |
| 22 | `0x01a560` | `0x005c` | 92 |
| 23 | `0x01a562` | `0x0000` | 0 |

First 16 firmware offset-table entries. Entries are 32-bit offsets relative to
the selected record base.

| Index | Relative offset | Resource target |
| ---: | ---: | ---: |
| 0 | `0x00006cd8` | `0x02120c` |
| 1 | `0x00006d52` | `0x021286` |
| 2 | `0x00006dcc` | `0x021300` |
| 3 | `0x00006e3a` | `0x02136e` |
| 4 | `0x00006bf8` | `0x02112c` |
| 5 | `0x00006c6a` | `0x02119e` |
| 6 | `0x00006e98` | `0x0213cc` |
| 7 | `0x00006eb8` | `0x0213ec` |
| 8 | `0x00006f3a` | `0x02146e` |
| 9 | `0x00006fbc` | `0x0214f0` |
| 10 | `0x0000703e` | `0x021572` |
| 11 | `0x000070ac` | `0x0215e0` |
| 12 | `0x00007106` | `0x02163a` |
| 13 | `0x0000716a` | `0x02169e` |
| 14 | `0x000071da` | `0x02170e` |
| 15 | `0x00007240` | `0x021774` |

## COURIER @0x01a97c

- firmware record start: `0x01a984`
- built-in firmware address: `0x09a984`
- header-like record: `yes`
- length field at record + 4: `0x00008b00` (35584)
- next same-name delta: `976`
- candidate offset-table delta: `0x004a`
- candidate offset-table address: `0x01a9ce`

First 24 header words, unsigned and signed:

| Index | Address | Unsigned | Signed |
| ---: | --- | ---: | ---: |
| 0 | `0x01a984` | `0x0000` | 0 |
| 1 | `0x01a986` | `0x0014` | 20 |
| 2 | `0x01a988` | `0x0000` | 0 |
| 3 | `0x01a98a` | `0x8b00` | -29952 |
| 4 | `0x01a98c` | `0x004a` | 74 |
| 5 | `0x01a98e` | `0x0000` | 0 |
| 6 | `0x01a990` | `0x0100` | 256 |
| 7 | `0x01a992` | `0x0021` | 33 |
| 8 | `0x01a994` | `0x00ff` | 255 |
| 9 | `0x01a996` | `0x001e` | 30 |
| 10 | `0x01a998` | `0x0032` | 50 |
| 11 | `0x01a99a` | `0x0024` | 36 |
| 12 | `0x01a99c` | `0x000d` | 13 |
| 13 | `0x01a99e` | `0xfff7` | -9 |
| 14 | `0x01a9a0` | `0x001e` | 30 |
| 15 | `0x01a9a2` | `0x0032` | 50 |
| 16 | `0x01a9a4` | `0x0100` | 256 |
| 17 | `0x01a9a6` | `0x000e` | 14 |
| 18 | `0x01a9a8` | `0x0078` | 120 |
| 19 | `0x01a9aa` | `0x0000` | 0 |
| 20 | `0x01a9ac` | `0x00c8` | 200 |
| 21 | `0x01a9ae` | `0x0000` | 0 |
| 22 | `0x01a9b0` | `0x005c` | 92 |
| 23 | `0x01a9b2` | `0x0000` | 0 |

First 16 firmware offset-table entries. Entries are 32-bit offsets relative to
the selected record base.

| Index | Relative offset | Resource target |
| ---: | ---: | ---: |
| 0 | `0x000003d0` | `0x01ad54` |
| 1 | `0x000003fe` | `0x01ad82` |
| 2 | `0x00000450` | `0x01add4` |
| 3 | `0x000004cc` | `0x01ae50` |
| 4 | `0x00000554` | `0x01aed8` |
| 5 | `0x000005e2` | `0x01af66` |
| 6 | `0x00008a1c` | `0x0233a0` |
| 7 | `0x00000662` | `0x01afe6` |
| 8 | `0x000006ae` | `0x01b032` |
| 9 | `0x000006f4` | `0x01b078` |
| 10 | `0x00000752` | `0x01b0d6` |
| 11 | `0x000007c0` | `0x01b144` |
| 12 | `0x000007de` | `0x01b162` |
| 13 | `0x00000816` | `0x01b19a` |
| 14 | `0x00000832` | `0x01b1b6` |
| 15 | `0x000008d8` | `0x01b25c` |

## COURIER @0x023848

- firmware record start: `0x023850`
- built-in firmware address: `0x0a3850`
- header-like record: `yes`
- length field at record + 4: `0x00000450` (1104)
- next same-name delta: `1104`
- candidate offset-table delta: `0x004a`
- candidate offset-table address: `0x02389a`

First 24 header words, unsigned and signed:

| Index | Address | Unsigned | Signed |
| ---: | --- | ---: | ---: |
| 0 | `0x023850` | `0x0000` | 0 |
| 1 | `0x023852` | `0x0014` | 20 |
| 2 | `0x023854` | `0x0000` | 0 |
| 3 | `0x023856` | `0x0450` | 1104 |
| 4 | `0x023858` | `0x004a` | 74 |
| 5 | `0x02385a` | `0x0000` | 0 |
| 6 | `0x02385c` | `0x0200` | 512 |
| 7 | `0x02385e` | `0x0001` | 1 |
| 8 | `0x023860` | `0x00ff` | 255 |
| 9 | `0x023862` | `0x001e` | 30 |
| 10 | `0x023864` | `0x0036` | 54 |
| 11 | `0x023866` | `0x0028` | 40 |
| 12 | `0x023868` | `0x000d` | 13 |
| 13 | `0x02386a` | `0xfff7` | -9 |
| 14 | `0x02386c` | `0x001e` | 30 |
| 15 | `0x02386e` | `0x0032` | 50 |
| 16 | `0x023870` | `0x0100` | 256 |
| 17 | `0x023872` | `0x0155` | 341 |
| 18 | `0x023874` | `0x0078` | 120 |
| 19 | `0x023876` | `0x0000` | 0 |
| 20 | `0x023878` | `0x00c8` | 200 |
| 21 | `0x02387a` | `0x0000` | 0 |
| 22 | `0x02387c` | `0x0060` | 96 |
| 23 | `0x02387e` | `0x0000` | 0 |

First 16 firmware offset-table entries. Entries are 32-bit offsets relative to
the selected record base.

| Index | Relative offset | Resource target |
| ---: | ---: | ---: |
| 0 | `0x000079ca` | `0x02b21a` |
| 1 | `0x00007a44` | `0x02b294` |
| 2 | `0x00007abe` | `0x02b30e` |
| 3 | `0x00007b2c` | `0x02b37c` |
| 4 | `0x000078ea` | `0x02b13a` |
| 5 | `0x0000795c` | `0x02b1ac` |
| 6 | `0x00007b8a` | `0x02b3da` |
| 7 | `0x00007baa` | `0x02b3fa` |
| 8 | `0x00007c2c` | `0x02b47c` |
| 9 | `0x00007cae` | `0x02b4fe` |
| 10 | `0x00007d30` | `0x02b580` |
| 11 | `0x00007d9e` | `0x02b5ee` |
| 12 | `0x00007df8` | `0x02b648` |
| 13 | `0x00007e5c` | `0x02b6ac` |
| 14 | `0x00007ecc` | `0x02b71c` |
| 15 | `0x00007f32` | `0x02b782` |

## COURIER @0x023c98

- firmware record start: `0x023ca0`
- built-in firmware address: `0x0a3ca0`
- header-like record: `yes`
- length field at record + 4: `0x00000450` (1104)
- next same-name delta: `1104`
- candidate offset-table delta: `0x004a`
- candidate offset-table address: `0x023cea`

First 24 header words, unsigned and signed:

| Index | Address | Unsigned | Signed |
| ---: | --- | ---: | ---: |
| 0 | `0x023ca0` | `0x0000` | 0 |
| 1 | `0x023ca2` | `0x0014` | 20 |
| 2 | `0x023ca4` | `0x0000` | 0 |
| 3 | `0x023ca6` | `0x0450` | 1104 |
| 4 | `0x023ca8` | `0x004a` | 74 |
| 5 | `0x023caa` | `0x0000` | 0 |
| 6 | `0x023cac` | `0x0200` | 512 |
| 7 | `0x023cae` | `0x0001` | 1 |
| 8 | `0x023cb0` | `0x00ff` | 255 |
| 9 | `0x023cb2` | `0x001e` | 30 |
| 10 | `0x023cb4` | `0x0036` | 54 |
| 11 | `0x023cb6` | `0x0028` | 40 |
| 12 | `0x023cb8` | `0x000d` | 13 |
| 13 | `0x023cba` | `0xfff7` | -9 |
| 14 | `0x023cbc` | `0x001e` | 30 |
| 15 | `0x023cbe` | `0x0032` | 50 |
| 16 | `0x023cc0` | `0x0100` | 256 |
| 17 | `0x023cc2` | `0x0175` | 373 |
| 18 | `0x023cc4` | `0x0078` | 120 |
| 19 | `0x023cc6` | `0x0000` | 0 |
| 20 | `0x023cc8` | `0x00c8` | 200 |
| 21 | `0x023cca` | `0x0000` | 0 |
| 22 | `0x023ccc` | `0x0060` | 96 |
| 23 | `0x023cce` | `0x0000` | 0 |

First 16 firmware offset-table entries. Entries are 32-bit offsets relative to
the selected record base.

| Index | Relative offset | Resource target |
| ---: | ---: | ---: |
| 0 | `0x0000757a` | `0x02b21a` |
| 1 | `0x000075f4` | `0x02b294` |
| 2 | `0x0000766e` | `0x02b30e` |
| 3 | `0x000076dc` | `0x02b37c` |
| 4 | `0x0000749a` | `0x02b13a` |
| 5 | `0x0000750c` | `0x02b1ac` |
| 6 | `0x0000773a` | `0x02b3da` |
| 7 | `0x0000775a` | `0x02b3fa` |
| 8 | `0x000077dc` | `0x02b47c` |
| 9 | `0x0000785e` | `0x02b4fe` |
| 10 | `0x000078e0` | `0x02b580` |
| 11 | `0x0000794e` | `0x02b5ee` |
| 12 | `0x000079a8` | `0x02b648` |
| 13 | `0x00007a0c` | `0x02b6ac` |
| 14 | `0x00007a7c` | `0x02b71c` |
| 15 | `0x00007ae2` | `0x02b782` |

## COURIER @0x0240e8

- firmware record start: `0x0240f0`
- built-in firmware address: `0x0a40f0`
- header-like record: `yes`
- length field at record + 4: `0x000093ba` (37818)
- next same-name delta: `976`
- candidate offset-table delta: `0x004a`
- candidate offset-table address: `0x02413a`

First 24 header words, unsigned and signed:

| Index | Address | Unsigned | Signed |
| ---: | --- | ---: | ---: |
| 0 | `0x0240f0` | `0x0000` | 0 |
| 1 | `0x0240f2` | `0x0014` | 20 |
| 2 | `0x0240f4` | `0x0000` | 0 |
| 3 | `0x0240f6` | `0x93ba` | -27718 |
| 4 | `0x0240f8` | `0x004a` | 74 |
| 5 | `0x0240fa` | `0x0000` | 0 |
| 6 | `0x0240fc` | `0x0100` | 256 |
| 7 | `0x0240fe` | `0x0021` | 33 |
| 8 | `0x024100` | `0x00ff` | 255 |
| 9 | `0x024102` | `0x001e` | 30 |
| 10 | `0x024104` | `0x0032` | 50 |
| 11 | `0x024106` | `0x0024` | 36 |
| 12 | `0x024108` | `0x000d` | 13 |
| 13 | `0x02410a` | `0xfff7` | -9 |
| 14 | `0x02410c` | `0x001e` | 30 |
| 15 | `0x02410e` | `0x0032` | 50 |
| 16 | `0x024110` | `0x0100` | 256 |
| 17 | `0x024112` | `0x000e` | 14 |
| 18 | `0x024114` | `0x0078` | 120 |
| 19 | `0x024116` | `0x0000` | 0 |
| 20 | `0x024118` | `0x00c8` | 200 |
| 21 | `0x02411a` | `0x0000` | 0 |
| 22 | `0x02411c` | `0x0060` | 96 |
| 23 | `0x02411e` | `0x0000` | 0 |

First 16 firmware offset-table entries. Entries are 32-bit offsets relative to
the selected record base.

| Index | Relative offset | Resource target |
| ---: | ---: | ---: |
| 0 | `0x000003d0` | `0x0244c0` |
| 1 | `0x00000406` | `0x0244f6` |
| 2 | `0x0000046c` | `0x02455c` |
| 3 | `0x000004f4` | `0x0245e4` |
| 4 | `0x00000588` | `0x024678` |
| 5 | `0x00000622` | `0x024712` |
| 6 | `0x000092ce` | `0x02d3be` |
| 7 | `0x000006a4` | `0x024794` |
| 8 | `0x000006f0` | `0x0247e0` |
| 9 | `0x0000073c` | `0x02482c` |
| 10 | `0x0000079a` | `0x02488a` |
| 11 | `0x00000810` | `0x024900` |
| 12 | `0x0000084e` | `0x02493e` |
| 13 | `0x00000886` | `0x024976` |
| 14 | `0x000008a6` | `0x024996` |
| 15 | `0x00000952` | `0x024a42` |

## LINE_PRINTER @0x02d86e

- firmware record start: `0x02d87a`
- built-in firmware address: `0x0ad87a`
- header-like record: `yes`
- length field at record + 4: `0x00000454` (1108)
- next same-name delta: `1108`
- candidate offset-table delta: `0x004a`
- candidate offset-table address: `0x02d8c4`

First 24 header words, unsigned and signed:

| Index | Address | Unsigned | Signed |
| ---: | --- | ---: | ---: |
| 0 | `0x02d87a` | `0x0000` | 0 |
| 1 | `0x02d87c` | `0x0014` | 20 |
| 2 | `0x02d87e` | `0x0000` | 0 |
| 3 | `0x02d880` | `0x0454` | 1108 |
| 4 | `0x02d882` | `0x004a` | 74 |
| 5 | `0x02d884` | `0x0000` | 0 |
| 6 | `0x02d886` | `0x0200` | 512 |
| 7 | `0x02d888` | `0x0001` | 1 |
| 8 | `0x02d88a` | `0x00ff` | 255 |
| 9 | `0x02d88c` | `0x0012` | 18 |
| 10 | `0x02d88e` | `0x0027` | 39 |
| 11 | `0x02d890` | `0x001c` | 28 |
| 12 | `0x02d892` | `0x000a` | 10 |
| 13 | `0x02d894` | `0xfffa` | -6 |
| 14 | `0x02d896` | `0x0012` | 18 |
| 15 | `0x02d898` | `0x0026` | 38 |
| 16 | `0x02d89a` | `0x0100` | 256 |
| 17 | `0x02d89c` | `0x0155` | 341 |
| 18 | `0x02d89e` | `0x0048` | 72 |
| 19 | `0x02d8a0` | `0x0000` | 0 |
| 20 | `0x02d8a2` | `0x008d` | 141 |
| 21 | `0x02d8a4` | `0xab00` | -21760 |
| 22 | `0x02d8a6` | `0x0044` | 68 |
| 23 | `0x02d8a8` | `0x0000` | 0 |

First 16 firmware offset-table entries. Entries are 32-bit offsets relative to
the selected record base.

| Index | Relative offset | Resource target |
| ---: | ---: | ---: |
| 0 | `0x000043ba` | `0x031c34` |
| 1 | `0x000043e4` | `0x031c5e` |
| 2 | `0x0000440e` | `0x031c88` |
| 3 | `0x0000445c` | `0x031cd6` |
| 4 | `0x00004326` | `0x031ba0` |
| 5 | `0x00004370` | `0x031bea` |
| 6 | `0x000044aa` | `0x031d24` |
| 7 | `0x000044ca` | `0x031d44` |
| 8 | `0x0000451c` | `0x031d96` |
| 9 | `0x00004546` | `0x031dc0` |
| 10 | `0x00004598` | `0x031e12` |
| 11 | `0x000045e6` | `0x031e60` |
| 12 | `0x00004624` | `0x031e9e` |
| 13 | `0x00004662` | `0x031edc` |
| 14 | `0x000046b0` | `0x031f2a` |
| 15 | `0x00004702` | `0x031f7c` |

## LINE_PRINTER @0x02dcc2

- firmware record start: `0x02dcce`
- built-in firmware address: `0x0adcce`
- header-like record: `yes`
- length field at record + 4: `0x00000454` (1108)
- next same-name delta: `1108`
- candidate offset-table delta: `0x004a`
- candidate offset-table address: `0x02dd18`

First 24 header words, unsigned and signed:

| Index | Address | Unsigned | Signed |
| ---: | --- | ---: | ---: |
| 0 | `0x02dcce` | `0x0000` | 0 |
| 1 | `0x02dcd0` | `0x0014` | 20 |
| 2 | `0x02dcd2` | `0x0000` | 0 |
| 3 | `0x02dcd4` | `0x0454` | 1108 |
| 4 | `0x02dcd6` | `0x004a` | 74 |
| 5 | `0x02dcd8` | `0x0000` | 0 |
| 6 | `0x02dcda` | `0x0200` | 512 |
| 7 | `0x02dcdc` | `0x0001` | 1 |
| 8 | `0x02dcde` | `0x00ff` | 255 |
| 9 | `0x02dce0` | `0x0012` | 18 |
| 10 | `0x02dce2` | `0x0027` | 39 |
| 11 | `0x02dce4` | `0x001c` | 28 |
| 12 | `0x02dce6` | `0x000a` | 10 |
| 13 | `0x02dce8` | `0xfffa` | -6 |
| 14 | `0x02dcea` | `0x0012` | 18 |
| 15 | `0x02dcec` | `0x0026` | 38 |
| 16 | `0x02dcee` | `0x0100` | 256 |
| 17 | `0x02dcf0` | `0x0175` | 373 |
| 18 | `0x02dcf2` | `0x0048` | 72 |
| 19 | `0x02dcf4` | `0x0000` | 0 |
| 20 | `0x02dcf6` | `0x008d` | 141 |
| 21 | `0x02dcf8` | `0xab00` | -21760 |
| 22 | `0x02dcfa` | `0x0044` | 68 |
| 23 | `0x02dcfc` | `0x0000` | 0 |

First 16 firmware offset-table entries. Entries are 32-bit offsets relative to
the selected record base.

| Index | Relative offset | Resource target |
| ---: | ---: | ---: |
| 0 | `0x00003f66` | `0x031c34` |
| 1 | `0x00003f90` | `0x031c5e` |
| 2 | `0x00003fba` | `0x031c88` |
| 3 | `0x00004008` | `0x031cd6` |
| 4 | `0x00003ed2` | `0x031ba0` |
| 5 | `0x00003f1c` | `0x031bea` |
| 6 | `0x00004056` | `0x031d24` |
| 7 | `0x00004076` | `0x031d44` |
| 8 | `0x000040c8` | `0x031d96` |
| 9 | `0x000040f2` | `0x031dc0` |
| 10 | `0x00004144` | `0x031e12` |
| 11 | `0x00004192` | `0x031e60` |
| 12 | `0x000041d0` | `0x031e9e` |
| 13 | `0x0000420e` | `0x031edc` |
| 14 | `0x0000425c` | `0x031f2a` |
| 15 | `0x000042ae` | `0x031f7c` |

## LINE_PRINTER @0x02e116

- firmware record start: `0x02e122`
- built-in firmware address: `0x0ae122`
- header-like record: `yes`
- length field at record + 4: `0x00004e5e` (20062)
- next same-name delta: `980`
- candidate offset-table delta: `0x004a`
- candidate offset-table address: `0x02e16c`

First 24 header words, unsigned and signed:

| Index | Address | Unsigned | Signed |
| ---: | --- | ---: | ---: |
| 0 | `0x02e122` | `0x0000` | 0 |
| 1 | `0x02e124` | `0x0014` | 20 |
| 2 | `0x02e126` | `0x0000` | 0 |
| 3 | `0x02e128` | `0x4e5e` | 20062 |
| 4 | `0x02e12a` | `0x004a` | 74 |
| 5 | `0x02e12c` | `0x0000` | 0 |
| 6 | `0x02e12e` | `0x0100` | 256 |
| 7 | `0x02e130` | `0x0021` | 33 |
| 8 | `0x02e132` | `0x00ff` | 255 |
| 9 | `0x02e134` | `0x0012` | 18 |
| 10 | `0x02e136` | `0x0027` | 39 |
| 11 | `0x02e138` | `0x001c` | 28 |
| 12 | `0x02e13a` | `0x000a` | 10 |
| 13 | `0x02e13c` | `0xfffa` | -6 |
| 14 | `0x02e13e` | `0x0012` | 18 |
| 15 | `0x02e140` | `0x0026` | 38 |
| 16 | `0x02e142` | `0x0100` | 256 |
| 17 | `0x02e144` | `0x000e` | 14 |
| 18 | `0x02e146` | `0x0048` | 72 |
| 19 | `0x02e148` | `0x0000` | 0 |
| 20 | `0x02e14a` | `0x008d` | 141 |
| 21 | `0x02e14c` | `0xab00` | -21760 |
| 22 | `0x02e14e` | `0x0044` | 68 |
| 23 | `0x02e150` | `0x0000` | 0 |

First 16 firmware offset-table entries. Entries are 32-bit offsets relative to
the selected record base.

| Index | Relative offset | Resource target |
| ---: | ---: | ---: |
| 0 | `0x000003d4` | `0x02e4f6` |
| 1 | `0x000003ee` | `0x02e510` |
| 2 | `0x00000410` | `0x02e532` |
| 3 | `0x0000045e` | `0x02e580` |
| 4 | `0x000004a8` | `0x02e5ca` |
| 5 | `0x000004f6` | `0x02e618` |
| 6 | `0x00004dfa` | `0x032f1c` |
| 7 | `0x00000558` | `0x02e67a` |
| 8 | `0x00000586` | `0x02e6a8` |
| 9 | `0x000005b4` | `0x02e6d6` |
| 10 | `0x000005dc` | `0x02e6fe` |
| 11 | `0x00000604` | `0x02e726` |
| 12 | `0x0000061c` | `0x02e73e` |
| 13 | `0x00000638` | `0x02e75a` |
| 14 | `0x0000064e` | `0x02e770` |
| 15 | `0x00000694` | `0x02e7b6` |
