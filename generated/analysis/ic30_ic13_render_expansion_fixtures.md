# IC30/IC13 Encoded Raster Expansion Fixtures

These fixtures are generated directly from ROM expansion tables used by
encoded raster span modes under `0x1f88e`. They are intended as small
renderer-unit expectations before full page-coordinate fixtures exist.

## Mode 0 Literal Word Copy

Mode 0 (`0x1f8da`) copies payload words directly to consecutive destination
words while decrementing the byte count by two.

- sample payload bytes: `12 34 ab cd 00 ff 55 aa`
- expected destination words: `0x1234, 0xabcd, 0x00ff, 0x55aa`

## Mode 1 Byte-to-Word Expansion

Mode 1 (`0x1f8e6`) expands each payload byte through word table `0x30914`,
then writes the same word to the current destination and one adjacent row/band
destination.

| Payload byte | Expanded word | Relative writes per byte |
| ---: | ---: | --- |
| `0x00` | `0x0000` | `(row 0, word n)=0x0000` and `(row 1, word n)=0x0000` |
| `0x01` | `0x0003` | `(row 0, word n)=0x0003` and `(row 1, word n)=0x0003` |
| `0x02` | `0x000c` | `(row 0, word n)=0x000c` and `(row 1, word n)=0x000c` |
| `0x03` | `0x000f` | `(row 0, word n)=0x000f` and `(row 1, word n)=0x000f` |
| `0x04` | `0x0030` | `(row 0, word n)=0x0030` and `(row 1, word n)=0x0030` |
| `0x05` | `0x0033` | `(row 0, word n)=0x0033` and `(row 1, word n)=0x0033` |
| `0x08` | `0x00c0` | `(row 0, word n)=0x00c0` and `(row 1, word n)=0x00c0` |
| `0x0f` | `0x00ff` | `(row 0, word n)=0x00ff` and `(row 1, word n)=0x00ff` |
| `0x10` | `0x0300` | `(row 0, word n)=0x0300` and `(row 1, word n)=0x0300` |
| `0x33` | `0x0f0f` | `(row 0, word n)=0x0f0f` and `(row 1, word n)=0x0f0f` |
| `0x55` | `0x3333` | `(row 0, word n)=0x3333` and `(row 1, word n)=0x3333` |
| `0xaa` | `0xcccc` | `(row 0, word n)=0xcccc` and `(row 1, word n)=0xcccc` |
| `0xf0` | `0xff00` | `(row 0, word n)=0xff00` and `(row 1, word n)=0xff00` |
| `0xff` | `0xffff` | `(row 0, word n)=0xffff` and `(row 1, word n)=0xffff` |

## Mode 2 Byte-to-Long Expansion

Mode 2 (`0x1f920`) expands bytes through longword table `0x30b14`. The loop
advances the payload pointer by two for each lookup, so paired/skip-byte
payload layouts must preserve that stride.

| Payload byte used | Expanded long | High word | Low word |
| ---: | ---: | ---: | ---: |
| `0x00` | `0x00000000` | `0x0000` | `0x0000` |
| `0x01` | `0x00000700` | `0x0000` | `0x0700` |
| `0x02` | `0x00003800` | `0x0000` | `0x3800` |
| `0x03` | `0x00003f00` | `0x0000` | `0x3f00` |
| `0x04` | `0x0001c000` | `0x0001` | `0xc000` |
| `0x05` | `0x0001c700` | `0x0001` | `0xc700` |
| `0x08` | `0x000e0000` | `0x000e` | `0x0000` |
| `0x0f` | `0x000fff00` | `0x000f` | `0xff00` |
| `0x10` | `0x00700000` | `0x0070` | `0x0000` |
| `0x33` | `0x03f03f00` | `0x03f0` | `0x3f00` |
| `0x55` | `0x1c71c700` | `0x1c71` | `0xc700` |
| `0xaa` | `0xe38e3800` | `0xe38e` | `0x3800` |
| `0xf0` | `0xfff00000` | `0xfff0` | `0x0000` |
| `0xff` | `0xffffff00` | `0xffff` | `0xff00` |

## Mode 3 Cascaded Byte Expansion

Mode 3 (`0x1f9c6`) first expands the payload byte through `0x30914`, then
expands the high and low bytes of that word through the same table to form one
longword.

| Payload byte | First table word | Final long | High word | Low word |
| ---: | ---: | ---: | ---: | ---: |
| `0x00` | `0x0000` | `0x00000000` | `0x0000` | `0x0000` |
| `0x01` | `0x0003` | `0x0000000f` | `0x0000` | `0x000f` |
| `0x02` | `0x000c` | `0x000000f0` | `0x0000` | `0x00f0` |
| `0x03` | `0x000f` | `0x000000ff` | `0x0000` | `0x00ff` |
| `0x04` | `0x0030` | `0x00000f00` | `0x0000` | `0x0f00` |
| `0x05` | `0x0033` | `0x00000f0f` | `0x0000` | `0x0f0f` |
| `0x08` | `0x00c0` | `0x0000f000` | `0x0000` | `0xf000` |
| `0x0f` | `0x00ff` | `0x0000ffff` | `0x0000` | `0xffff` |
| `0x10` | `0x0300` | `0x000f0000` | `0x000f` | `0x0000` |
| `0x33` | `0x0f0f` | `0x00ff00ff` | `0x00ff` | `0x00ff` |
| `0x55` | `0x3333` | `0x0f0f0f0f` | `0x0f0f` | `0x0f0f` |
| `0xaa` | `0xcccc` | `0xf0f0f0f0` | `0xf0f0` | `0xf0f0` |
| `0xf0` | `0xff00` | `0xffff0000` | `0xffff` | `0x0000` |
| `0xff` | `0xffff` | `0xffffffff` | `0xffff` | `0xffff` |

## Minimal Fixture Vectors

These compact vectors can be copied into a renderer test once the
destination-address setup is implemented.

| Mode | Input bytes | Expected expanded values |
| ---: | --- | --- |
| 0 | `12 34 ab cd 00 ff 55 aa` | `0x1234, 0xabcd, 0x00ff, 0x55aa` |
| 1 | `00 01 02 03 04 05 08 0f 10 33 55 aa f0 ff` | `0x0000, 0x0003, 0x000c, 0x000f, 0x0030, 0x0033, 0x00c0, 0x00ff, 0x0300, 0x0f0f, 0x3333, 0xcccc, 0xff00, 0xffff` |
| 2 | `00 01 02 03 04 05 08 0f 10 33 55 aa f0 ff` | `0x00000000, 0x00000700, 0x00003800, 0x00003f00, 0x0001c000, 0x0001c700, 0x000e0000, 0x000fff00, 0x00700000, 0x03f03f00, 0x1c71c700, 0xe38e3800, 0xfff00000, 0xffffff00` |
| 3 | `00 01 02 03 04 05 08 0f 10 33 55 aa f0 ff` | `0x00000000, 0x0000000f, 0x000000f0, 0x000000ff, 0x00000f00, 0x00000f0f, 0x0000f000, 0x0000ffff, 0x000f0000, 0x00ff00ff, 0x0f0f0f0f, 0xf0f0f0f0, 0xffff0000, 0xffffffff` |
