# IC32/IC15 Resource Glyph Probe

Generated from the firmware-scanned built-in font records and the field layout
consumed by glyph resolver `0x1f354`. The firmware selects a context longword
whose low 24 bits are a resource address. For built-in records it sets bit 30,
so `0x1f354` uses the offset-table form.

## Firmware-Scanned Font Records

| Name | Name offset | Record start | Firmware address | Context longword | Table | Table entries | First..last char | Size-like words | Length | Class/style |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | --- |
| `(unnamed)` | (none) | `0x00004c` | `0x08004c` | `0x4008004c` | `0x000096` | 189 | `0x0021`..`0x00fe` | `30x50`, `30x50` | `0x000003cc` | `0x00`/`0x00` |
| `COURIER` | `0x000410` | `0x000418` | `0x080418` | `0x44080418` | `0x000462` | 253 | `0x0001`..`0x00ff` | `30x54`, `30x50` | `0x00000450` | `0x00`/`0x00` |
| `COURIER` | `0x000860` | `0x000868` | `0x080868` | `0x44080868` | `0x0008b2` | 253 | `0x0001`..`0x00ff` | `30x54`, `30x50` | `0x00000450` | `0x00`/`0x00` |
| `COURIER` | `0x000cb0` | `0x000cb8` | `0x080cb8` | `0x40080cb8` | `0x000d02` | 1650 | `0x0021`..`0x00ff` | `30x50`, `30x50` | `0x000092f8` | `0x00`/`0x00` |
| `(unnamed)` | (none) | `0x009fb0` | `0x089fb0` | `0x40089fb0` | `0x009ffa` | 189 | `0x0021`..`0x00fe` | `30x50`, `30x50` | `0x000003cc` | `0x00`/`0x00` |
| `COURIER` | `0x00a374` | `0x00a37c` | `0x08a37c` | `0x4408a37c` | `0x00a3c6` | 253 | `0x0001`..`0x00ff` | `30x54`, `30x50` | `0x00000450` | `0x00`/`0x00` |
| `COURIER` | `0x00a7c4` | `0x00a7cc` | `0x08a7cc` | `0x4408a7cc` | `0x00a816` | 253 | `0x0001`..`0x00ff` | `30x54`, `30x50` | `0x00000450` | `0x00`/`0x00` |
| `COURIER` | `0x00ac14` | `0x00ac1c` | `0x08ac1c` | `0x4008ac1c` | `0x00ac66` | 1409 | `0x0021`..`0x00ff` | `30x50`, `30x50` | `0x000096c8` | `0x00`/`0x00` |
| `(unnamed)` | (none) | `0x0142e4` | `0x0942e4` | `0x400942e4` | `0x01432e` | 189 | `0x0021`..`0x00fe` | `18x35`, `18x35` | `0x000003d0` | `0x00`/`0x00` |
| `LINE_PRINTER` | `0x0146a8` | `0x0146b4` | `0x0946b4` | `0x440946b4` | `0x0146fe` | 253 | `0x0001`..`0x00ff` | `18x39`, `18x38` | `0x00000454` | `0x00`/`0x00` |
| `LINE_PRINTER` | `0x014afc` | `0x014b08` | `0x094b08` | `0x44094b08` | `0x014b52` | 253 | `0x0001`..`0x00ff` | `18x39`, `18x38` | `0x00000454` | `0x00`/`0x00` |
| `LINE_PRINTER` | `0x014f50` | `0x014f5c` | `0x094f5c` | `0x40094f5c` | `0x014fa6` | 760 | `0x0021`..`0x00ff` | `18x39`, `18x38` | `0x00004dbc` | `0x00`/`0x00` |
| `(unnamed)` | (none) | `0x019d18` | `0x099d18` | `0x40099d18` | `0x019d62` | 189 | `0x0021`..`0x00fe` | `30x50`, `30x50` | `0x000003cc` | `0x01`/`0x00` |
| `COURIER` | `0x01a0dc` | `0x01a0e4` | `0x09a0e4` | `0x4409a0e4` | `0x01a12e` | 253 | `0x0001`..`0x00ff` | `30x54`, `30x50` | `0x00000450` | `0x01`/`0x00` |
| `COURIER` | `0x01a52c` | `0x01a534` | `0x09a534` | `0x4409a534` | `0x01a57e` | 253 | `0x0001`..`0x00ff` | `30x54`, `30x50` | `0x00000450` | `0x01`/`0x00` |
| `COURIER` | `0x01a97c` | `0x01a984` | `0x09a984` | `0x4009a984` | `0x01a9ce` | 1642 | `0x0021`..`0x00ff` | `30x50`, `30x50` | `0x00008b00` | `0x01`/`0x00` |
| `(unnamed)` | (none) | `0x023484` | `0x0a3484` | `0x400a3484` | `0x0234ce` | 189 | `0x0021`..`0x00fe` | `30x50`, `30x50` | `0x000003cc` | `0x01`/`0x00` |
| `COURIER` | `0x023848` | `0x023850` | `0x0a3850` | `0x440a3850` | `0x02389a` | 253 | `0x0001`..`0x00ff` | `30x54`, `30x50` | `0x00000450` | `0x01`/`0x00` |
| `COURIER` | `0x023c98` | `0x023ca0` | `0x0a3ca0` | `0x440a3ca0` | `0x023cea` | 253 | `0x0001`..`0x00ff` | `30x54`, `30x50` | `0x00000450` | `0x01`/`0x00` |
| `COURIER` | `0x0240e8` | `0x0240f0` | `0x0a40f0` | `0x400a40f0` | `0x02413a` | 1401 | `0x0021`..`0x00ff` | `30x50`, `30x50` | `0x000093ba` | `0x01`/`0x00` |
| `(unnamed)` | (none) | `0x02d4aa` | `0x0ad4aa` | `0x400ad4aa` | `0x02d4f4` | 189 | `0x0021`..`0x00fe` | `18x35`, `18x35` | `0x000003d0` | `0x01`/`0x00` |
| `LINE_PRINTER` | `0x02d86e` | `0x02d87a` | `0x0ad87a` | `0x440ad87a` | `0x02d8c4` | 253 | `0x0001`..`0x00ff` | `18x39`, `18x38` | `0x00000454` | `0x01`/`0x00` |
| `LINE_PRINTER` | `0x02dcc2` | `0x02dcce` | `0x0adcce` | `0x440adcce` | `0x02dd18` | 253 | `0x0001`..`0x00ff` | `18x39`, `18x38` | `0x00000454` | `0x01`/`0x00` |
| `LINE_PRINTER` | `0x02e116` | `0x02e122` | `0x0ae122` | `0x400ae122` | `0x02e16c` | 831 | `0x0021`..`0x00ff` | `18x39`, `18x38` | `0x00004e5e` | `0x01`/`0x00` |

## Table Target Probes

### `(unnamed)` record @`0x00004c`

- nonzero table entries: `189`
- unique in-image target range: `0x001088`..`0x0078ca`

| Table index | Relative offset | Resource target | Bytes at target | Firmware `0x1f354` fields |
| ---: | ---: | ---: | --- | --- |
| 0 | `0x0000103c` | `0x001088` | `00 0a 00 1f 0a 01 00 20 00 09` | `0x001088`: delta `10`, mode `1`, height `32`, width `9`, render span `2`, bitmap `0x001092`, sample `1c 00 3e 00 3e 00 3e 00` |
| 1 | `0x00001086` | `0x0010d2` | `00 06 00 1e 0a 01 00 11 00 12` | `0x0010d2`: delta `10`, mode `1`, height `17`, width `18`, render span `4`, bitmap `0x0010dc`, sample `7c 0f 80 00 fe 1f c0 00 fe 1f c0 00 fe 1f c0 00` |
| 2 | `0x000010d4` | `0x001120` | `00 06 00 20 0a 01 00 26 00 13` | `0x001120`: delta `10`, mode `1`, height `38`, width `19`, render span `4`, bitmap `0x00112a`, sample `01 83 00 00 01 83 00 00 01 83 00 00 01 83 00 00` |
| 3 | `0x00001176` | `0x0011c2` | `00 05 00 21 0a 01 00 28 00 15` | `0x0011c2`: delta `10`, mode `1`, height `40`, width `21`, render span `4`, bitmap `0x0011cc`, sample `00 30 00 00 00 78 00 00 00 78 00 00 00 78 00 00` |
| 4 | `0x00001220` | `0x00126c` | `00 04 00 1f 0a 01 00 21 00 16` | `0x00126c`: delta `10`, mode `1`, height `33`, width `22`, render span `4`, bitmap `0x001276`, sample `03 c0 00 00 0f f0 00 00 1f f8 00 00 3c 3c 00 00` |
| 5 | `0x000012ae` | `0x0012fa` | `00 05 00 1c 0a 01 00 1d 00 15` | `0x0012fa`: delta `10`, mode `1`, height `29`, width `21`, render span `4`, bitmap `0x001304`, sample `01 f8 00 00 07 fe 00 00 0f ff 00 00 0f ff 00 00` |
| 6 | `0x0000132c` | `0x001378` | `00 09 00 1e 0a 01 00 10 00 0c` | `0x001378`: delta `10`, mode `1`, height `16`, width `12`, render span `2`, bitmap `0x001382`, sample `03 e0 07 f0 07 f0 0f f0` |
| 7 | `0x00001356` | `0x0013a2` | `00 0c 00 1e 0a 01 00 28 00 0b` | `0x0013a2`: delta `10`, mode `1`, height `40`, width `11`, render span `2`, bitmap `0x0013ac`, sample `00 c0 01 e0 03 e0 07 c0` |
| 8 | `0x000013b0` | `0x0013fc` | `00 07 00 1e 0a 01 00 28 00 0a` | `0x0013fc`: delta `10`, mode `1`, height `40`, width `10`, render span `2`, bitmap `0x001406`, sample `60 00 f0 00 f8 00 78 00` |
| 9 | `0x0000140a` | `0x001456` | `00 05 00 1c 0a 01 00 15 00 15` | `0x001456`: delta `10`, mode `1`, height `21`, width `21`, render span `4`, bitmap `0x001460`, sample `00 f8 00 00 00 f8 00 00 00 f8 00 00 00 f8 00 00` |
| 10 | `0x00001468` | `0x0014b4` | `00 02 00 1a 0a 01 00 19 00 19` | `0x0014b4`: delta `10`, mode `1`, height `25`, width `25`, render span `4`, bitmap `0x0014be`, sample `00 1c 00 00 00 1c 00 00 00 1c 00 00 00 1c 00 00` |
| 11 | `0x000014d6` | `0x001522` | `00 09 00 06 0a 01 00 0f 00 0a` | `0x001522`: delta `10`, mode `1`, height `15`, width `10`, render span `2`, bitmap `0x00152c`, sample `0f c0 1f c0 1f 80 1f 80` |
| 12 | `0x000014fe` | `0x00154a` | `00 04 00 10 0a 01 00 05 00 17` | `0x00154a`: delta `10`, mode `1`, height `5`, width `23`, render span `4`, bitmap `0x001554`, sample `7f ff fc 00 ff ff fe 00 ff ff fe 00 ff ff fe 00` |
| 13 | `0x0000151c` | `0x001568` | `00 0a 00 07 0a 01 00 08 00 09` | `0x001568`: delta `10`, mode `1`, height `8`, width `9`, render span `2`, bitmap `0x001572`, sample `3e 00 7f 00 ff 80 ff 80` |
| 14 | `0x00001536` | `0x001582` | `00 00 00 1e 0a 01 00 28 00 1a` | `0x001582`: delta `10`, mode `1`, height `40`, width `26`, render span `4`, bitmap `0x00158c`, sample `00 00 01 80 00 00 03 c0 00 00 03 80 00 00 07 80` |
| 15 | `0x000015e0` | `0x00162c` | `00 05 00 1c 0a 01 00 1d 00 15` | `0x00162c`: delta `10`, mode `1`, height `29`, width `21`, render span `4`, bitmap `0x001636`, sample `01 fc 00 00 07 ff 00 00 0f ff 80 00 1f 07 c0 00` |
| 16 | `0x0000165e` | `0x0016aa` | `00 05 00 1c 0a 01 00 1d 00 16` | `0x0016aa`: delta `10`, mode `1`, height `29`, width `22`, render span `4`, bitmap `0x0016b4`, sample `07 f0 00 00 1f f8 00 00 7f f8 00 00 7c 78 00 00` |
| 17 | `0x000016dc` | `0x001728` | `00 04 00 1c 0a 01 00 1d 00 14` | `0x001728`: delta `10`, mode `1`, height `29`, width `20`, render span `4`, bitmap `0x001732`, sample `01 fc 00 00 0f ff 00 00 3f ff 80 00 3f 0f c0 00` |
| 18 | `0x0000175a` | `0x0017a6` | `00 05 00 1c 0a 01 00 1d 00 13` | `0x0017a6`: delta `10`, mode `1`, height `29`, width `19`, render span `4`, bitmap `0x0017b0`, sample `03 f0 00 00 1f fc 00 00 3f ff 00 00 7c 1f 80 00` |
| 19 | `0x000017d8` | `0x001824` | `00 04 00 1c 0a 01 00 1d 00 15` | `0x001824`: delta `10`, mode `1`, height `29`, width `21`, render span `4`, bitmap `0x00182e`, sample `00 1f 00 00 00 1f 00 00 00 3f 00 00 00 3f 00 00` |
| 20 | `0x00001856` | `0x0018a2` | `00 04 00 1c 0a 01 00 1d 00 16` | `0x0018a2`: delta `10`, mode `1`, height `29`, width `22`, render span `4`, bitmap `0x0018ac`, sample `1f ff f0 00 3f ff f8 00 3f ff f0 00 38 00 00 00` |
| 21 | `0x000018d4` | `0x001920` | `00 05 00 1c 0a 01 00 1d 00 15` | `0x001920`: delta `10`, mode `1`, height `29`, width `21`, render span `4`, bitmap `0x00192a`, sample `00 0f e0 00 00 7f f0 00 01 ff e0 00 03 f8 00 00` |
| 22 | `0x00001952` | `0x00199e` | `00 04 00 1c 0a 01 00 1d 00 15` | `0x00199e`: delta `10`, mode `1`, height `29`, width `21`, render span `4`, bitmap `0x0019a8`, sample `7f ff f0 00 ff ff f8 00 ff ff f8 00 f0 00 70 00` |
| 23 | `0x000019d0` | `0x001a1c` | `00 04 00 1c 0a 01 00 1d 00 15` | `0x001a1c`: delta `10`, mode `1`, height `29`, width `21`, render span `4`, bitmap `0x001a26`, sample `03 fe 00 00 0f ff 80 00 1f ff c0 00 3f 07 e0 00` |
| 24 | `0x00001a4e` | `0x001a9a` | `00 04 00 1c 0a 01 00 1d 00 15` | `0x001a9a`: delta `10`, mode `1`, height `29`, width `21`, render span `4`, bitmap `0x001aa4`, sample `03 fc 00 00 0f ff 00 00 1f ff 80 00 3f 07 c0 00` |
| 25 | `0x00001acc` | `0x001b18` | `00 0a 00 16 0a 01 00 17 00 09` | `0x001b18`: delta `10`, mode `1`, height `23`, width `9`, render span `2`, bitmap `0x001b22`, sample `3e 00 7f 00 ff 80 ff 80` |
| 26 | `0x00001b04` | `0x001b50` | `00 0a 00 16 0a 01 00 1b 00 0b` | `0x001b50`: delta `10`, mode `1`, height `27`, width `11`, render span `2`, bitmap `0x001b5a`, sample `0f 80 1f c0 3f e0 3f e0` |
| 27 | `0x00001b44` | `0x001b90` | `00 03 00 19 0a 01 00 18 00 17` | `0x001b90`: delta `10`, mode `1`, height `24`, width `23`, render span `4`, bitmap `0x001b9a`, sample `00 00 02 00 00 00 0e 00 00 00 3e 00 00 00 fc 00` |
| 28 | `0x00001bae` | `0x001bfa` | `00 02 00 13 0a 01 00 0b 00 1a` | `0x001bfa`: delta `10`, mode `1`, height `11`, width `26`, render span `4`, bitmap `0x001c04`, sample `ff ff ff c0 ff ff ff c0 ff ff ff c0 00 00 00 00` |
| 29 | `0x00001be4` | `0x001c30` | `00 04 00 19 0a 01 00 18 00 17` | `0x001c30`: delta `10`, mode `1`, height `24`, width `23`, render span `4`, bitmap `0x001c3a`, sample `80 00 00 00 e0 00 00 00 f8 00 00 00 7e 00 00 00` |
| 30 | `0x00001c4e` | `0x001c9a` | `00 04 00 1f 0a 01 00 20 00 15` | `0x001c9a`: delta `10`, mode `1`, height `32`, width `21`, render span `4`, bitmap `0x001ca4`, sample `02 fa 00 00 0f ff 80 00 3f ff c0 00 7f af e0 00` |
| 31 | `0x00001cd8` | `0x001d24` | `00 05 00 1f 0a 01 00 23 00 15` | `0x001d24`: delta `10`, mode `1`, height `35`, width `21`, render span `4`, bitmap `0x001d2e`, sample `00 fc 00 00 03 ff 00 00 07 ff 80 00 0f c7 c0 00` |

### `COURIER` record @`0x000418`

- nonzero table entries: `253`
- unique in-image target range: `0x001088`..`0x009ef6`

| Table index | Relative offset | Resource target | Bytes at target | Firmware `0x1f354` fields |
| ---: | ---: | ---: | --- | --- |
| 0 | `0x00007792` | `0x007baa` | `00 01 00 1c 0a 01 00 1d 00 1c` | `0x007baa`: delta `10`, mode `1`, height `29`, width `28`, render span `4`, bitmap `0x007bb4`, sample `00 1f 80 00 00 ff f0 00 01 e0 78 00 07 00 0e 00` |
| 1 | `0x00007810` | `0x007c28` | `00 01 00 1c 0a 01 00 1d 00 1c` | `0x007c28`: delta `10`, mode `1`, height `29`, width `28`, render span `4`, bitmap `0x007c32`, sample `00 1f 80 00 00 ff f0 00 01 ff f8 00 07 ff fe 00` |
| 2 | `0x0000788e` | `0x007ca6` | `00 02 00 1c 0a 01 00 1d 00 19` | `0x007ca6`: delta `10`, mode `1`, height `29`, width `25`, render span `4`, bitmap `0x007cb0`, sample `1e 00 3c 00 3f 80 fe 00 7f e3 ff 00 ff e3 ff 80` |
| 3 | `0x0000790c` | `0x007d24` | `00 04 00 1c 0a 01 00 1d 00 15` | `0x007d24`: delta `10`, mode `1`, height `29`, width `21`, render span `4`, bitmap `0x007d2e`, sample `00 20 00 00 00 70 00 00 00 70 00 00 00 f8 00 00` |
| 4 | `0x00007692` | `0x007aaa` | `00 02 00 1d 0a 01 00 1e 00 1a` | `0x007aaa`: delta `10`, mode `1`, height `30`, width `26`, render span `4`, bitmap `0x007ab4`, sample `00 3f 00 00 00 ff c0 00 01 ff e0 00 03 ff f0 00` |
| 5 | `0x00007714` | `0x007b2c` | `00 02 00 1c 0a 01 00 1d 00 19` | `0x007b2c`: delta `10`, mode `1`, height `29`, width `25`, render span `4`, bitmap `0x007b36`, sample `00 08 00 00 00 08 00 00 00 1c 00 00 00 1c 00 00` |
| 6 | `0x0000798a` | `0x007da2` | `00 09 00 13 0a 01 00 0b 00 0b` | `0x007da2`: delta `10`, mode `1`, height `11`, width `11`, render span `2`, bitmap `0x007dac`, sample `1f 00 3f 80 7f c0 ff e0` |
| 7 | `0x000079aa` | `0x007dc2` | `00 00 00 1d 0a 01 00 1e 00 1e` | `0x007dc2`: delta `10`, mode `1`, height `30`, width `30`, render span `4`, bitmap `0x007dcc`, sample `ff ff ff fc ff ff ff fc ff ff ff fc ff ff ff fc` |
| 8 | `0x00007a2c` | `0x007e44` | `00 00 00 1d 0a 01 00 1e 00 1e` | `0x007e44`: delta `10`, mode `1`, height `30`, width `30`, render span `4`, bitmap `0x007e4e`, sample `00 1f e0 00 00 7f f8 00 01 e0 1e 00 07 80 07 80` |
| 9 | `0x00007aae` | `0x007ec6` | `00 00 00 1d 0a 01 00 1e 00 1e` | `0x007ec6`: delta `10`, mode `1`, height `30`, width `30`, render span `4`, bitmap `0x007ed0`, sample `ff ff ff fc ff e0 1f fc ff 80 07 fc fe 00 01 fc` |
| 10 | `0x00007b30` | `0x007f48` | `00 04 00 1a 0a 01 00 1a 00 19` | `0x007f48`: delta `10`, mode `1`, height `26`, width `25`, render span `4`, bitmap `0x007f52`, sample `00 00 3f 80 00 00 3f 80 00 00 0f 80 00 00 0f 80` |
| 11 | `0x00007ba2` | `0x007fba` | `00 05 00 1d 0a 01 00 1f 00 14` | `0x007fba`: delta `10`, mode `1`, height `31`, width `20`, render span `4`, bitmap `0x007fc4`, sample `01 f8 00 00 07 fe 00 00 0e 07 00 00 18 01 80 00` |
| 12 | `0x00007c28` | `0x008040` | `00 07 00 1e 0a 01 00 21 00 0f` | `0x008040`: delta `10`, mode `1`, height `33`, width `15`, render span `2`, bitmap `0x00804a`, sample `00 80 00 80 00 c0 00 c0` |
| 13 | `0x00007c74` | `0x00808c` | `00 07 00 1f 0a 01 00 23 00 11` | `0x00808c`: delta `10`, mode `1`, height `35`, width `17`, render span `4`, bitmap `0x008096`, sample `01 00 00 00 01 80 00 00 01 c0 00 00 01 e0 00 00` |
| 14 | `0x00007d0a` | `0x008122` | `00 03 00 19 0a 01 00 17 00 17` | `0x008122`: delta `10`, mode `1`, height `23`, width `23`, render span `4`, bitmap `0x00812c`, sample `00 38 00 00 00 38 00 00 30 38 18 00 38 38 38 00` |
| 15 | `0x00007d70` | `0x008188` | `00 06 00 17 0a 01 00 13 00 13` | `0x008188`: delta `10`, mode `1`, height `19`, width `19`, render span `4`, bitmap `0x008192`, sample `80 00 00 00 e0 00 00 00 f8 00 00 00 fe 00 00 00` |
| 16 | `0x00007dc6` | `0x0081de` | `00 05 00 17 0a 01 00 13 00 13` | `0x0081de`: delta `10`, mode `1`, height `19`, width `19`, render span `4`, bitmap `0x0081e8`, sample `00 00 20 00 00 00 e0 00 00 03 e0 00 00 0f e0 00` |
| 17 | `0x000071a4` | `0x0075bc` | `00 07 00 1c 0a 01 00 1d 00 0f` | `0x0075bc`: delta `10`, mode `1`, height `29`, width `15`, render span `2`, bitmap `0x0075c6`, sample `01 00 03 80 03 80 07 c0` |
| 18 | `0x00007e1c` | `0x008234` | `00 05 00 1f 0a 01 00 20 00 14` | `0x008234`: delta `10`, mode `1`, height `32`, width `20`, render span `4`, bitmap `0x00823e`, sample `1c 03 80 00 3e 07 c0 00 3e 07 c0 00 3e 07 c0 00` |
| 19 | `0x000074b2` | `0x0078ca` | `00 03 00 1c 0a 01 00 25 00 18` | `0x0078ca`: delta `10`, mode `1`, height `37`, width `24`, render span `4`, bitmap `0x0078d4`, sample `03 ff fe 00 0f ff ff 00 1f ff fe 00 3f fc 70 00` |
| 20 | `0x0000429e` | `0x0046b6` | `00 06 00 1c 0a 01 00 22 00 11` | `0x0046b6`: delta `10`, mode `1`, height `34`, width `17`, render span `4`, bitmap `0x0046c0`, sample `07 ce 00 00 1f fe 00 00 3c 3e 00 00 78 0e 00 00` |
| 21 | `0x00007ea6` | `0x0082be` | `00 05 00 08 0a 01 00 09 00 14` | `0x0082be`: delta `10`, mode `1`, height `9`, width `20`, render span `4`, bitmap `0x0082c8`, sample `ff ff f0 00 ff ff f0 00 ff ff f0 00 ff ff f0 00` |
| 22 | `0x00007ed4` | `0x0082ec` | `00 07 00 1c 0a 01 00 1f 00 0f` | `0x0082ec`: delta `10`, mode `1`, height `31`, width `15`, render span `2`, bitmap `0x0082f6`, sample `01 00 03 80 03 80 07 c0` |
| 23 | `0x00007090` | `0x0074a8` | `00 07 00 1c 0a 01 00 1d 00 0f` | `0x0074a8`: delta `10`, mode `1`, height `29`, width `15`, render span `2`, bitmap `0x0074b2`, sample `01 00 03 80 03 80 07 c0` |
| 24 | `0x0000711a` | `0x007532` | `00 07 00 1c 0a 01 00 1d 00 0f` | `0x007532`: delta `10`, mode `1`, height `29`, width `15`, render span `2`, bitmap `0x00753c`, sample `03 80 03 80 03 80 03 80` |
| 25 | `0x000070d4` | `0x0074ec` | `00 00 00 15 0a 01 00 0f 00 1c` | `0x0074ec`: delta `10`, mode `1`, height `15`, width `28`, render span `4`, bitmap `0x0074f6`, sample `00 00 30 00 00 00 38 00 00 00 18 00 00 00 1c 00` |
| 26 | `0x0000715e` | `0x007576` | `00 02 00 15 0a 01 00 0f 00 1c` | `0x007576`: delta `10`, mode `1`, height `15`, width `28`, render span `4`, bitmap `0x007580`, sample `00 c0 00 00 01 c0 00 00 01 80 00 00 03 80 00 00` |
| 27 | `0x00009a68` | `0x009e80` | `00 02 00 0f 0a 01 00 09 00 1a` | `0x009e80`: delta `10`, mode `1`, height `9`, width `26`, render span `4`, bitmap `0x009e8a`, sample `e0 00 00 00 e0 00 00 00 e0 00 00 00 e0 00 00 00` |
| 28 | `0x000071e8` | `0x007600` | `00 01 00 15 0a 01 00 0f 00 1c` | `0x007600`: delta `10`, mode `1`, height `15`, width `28`, render span `4`, bitmap `0x00760a`, sample `00 c0 30 00 01 c0 38 00 01 80 18 00 03 80 1c 00` |
| 29 | `0x00007f1c` | `0x008334` | `00 06 00 17 0a 01 00 13 00 13` | `0x008334`: delta `10`, mode `1`, height `19`, width `19`, render span `4`, bitmap `0x00833e`, sample `00 40 00 00 00 40 00 00 00 e0 00 00 00 e0 00 00` |
| 30 | `0x00007f72` | `0x00838a` | `00 06 00 17 0a 01 00 13 00 13` | `0x00838a`: delta `10`, mode `1`, height `19`, width `19`, render span `4`, bitmap `0x008394`, sample `ff ff e0 00 7f ff c0 00 7f ff c0 00 3f ff 80 00` |
| 32 | `0x00000c70` | `0x001088` | `00 0a 00 1f 0a 01 00 20 00 09` | `0x001088`: delta `10`, mode `1`, height `32`, width `9`, render span `2`, bitmap `0x001092`, sample `1c 00 3e 00 3e 00 3e 00` |

### `LINE_PRINTER` record @`0x0146b4`

- nonzero table entries: `253`
- unique in-image target range: `0x015330`..`0x019c96`

| Table index | Relative offset | Resource target | Bytes at target | Firmware `0x1f354` fields |
| ---: | ---: | ---: | --- | --- |
| 0 | `0x0000407c` | `0x018730` | `00 01 00 12 0a 01 00 10 00 10` | `0x018730`: delta `10`, mode `1`, height `16`, width `16`, render span `2`, bitmap `0x01873a`, sample `03 c0 0f f0 38 1c 30 0c` |
| 1 | `0x000040a6` | `0x01875a` | `00 01 00 12 0a 01 00 10 00 10` | `0x01875a`: delta `10`, mode `1`, height `16`, width `16`, render span `2`, bitmap `0x018764`, sample `03 c0 0f f0 3f fc 3f fc` |
| 2 | `0x000040d0` | `0x018784` | `00 01 00 15 0a 01 00 15 00 11` | `0x018784`: delta `10`, mode `1`, height `21`, width `17`, render span `4`, bitmap `0x01878e`, sample `3c 1e 00 00 7e 3f 00 00 7f 7f 00 00 ff ff 80 00` |
| 3 | `0x0000412e` | `0x0187e2` | `00 01 00 15 0a 01 00 17 00 11` | `0x0187e2`: delta `10`, mode `1`, height `23`, width `17`, render span `4`, bitmap `0x0187ec`, sample `00 80 00 00 01 c0 00 00 01 c0 00 00 03 e0 00 00` |
| 4 | `0x00004012` | `0x0186c6` | `00 01 00 15 0a 01 00 16 00 10` | `0x0186c6`: delta `10`, mode `1`, height `22`, width `16`, render span `2`, bitmap `0x0186d0`, sample `03 c0 0f f0 1f f8 1f f8` |
| 5 | `0x00004048` | `0x0186fc` | `00 01 00 15 0a 01 00 15 00 10` | `0x0186fc`: delta `10`, mode `1`, height `21`, width `16`, render span `2`, bitmap `0x018706`, sample `01 80 03 c0 07 e0 07 e0` |
| 6 | `0x00004194` | `0x018848` | `00 04 00 10 0a 01 00 0b 00 0b` | `0x018848`: delta `10`, mode `1`, height `11`, width `11`, render span `2`, bitmap `0x018852`, sample `1f 00 3f 80 7f c0 ff e0` |
| 7 | `0x000041b4` | `0x018868` | `00 00 00 15 0a 01 00 16 00 12` | `0x018868`: delta `10`, mode `1`, height `22`, width `18`, render span `4`, bitmap `0x018872`, sample `ff ff c0 00 ff ff c0 00 ff ff c0 00 ff ff c0 00` |
| 8 | `0x00004216` | `0x0188ca` | `00 01 00 12 0a 01 00 10 00 10` | `0x0188ca`: delta `10`, mode `1`, height `16`, width `16`, render span `2`, bitmap `0x0188d4`, sample `07 e0 1f f8 38 1c 60 06` |
| 9 | `0x00004240` | `0x0188f4` | `00 00 00 13 0a 01 00 12 00 12` | `0x0188f4`: delta `10`, mode `1`, height `18`, width `18`, render span `4`, bitmap `0x0188fe`, sample `ff ff c0 00 fc 0f c0 00 f0 03 c0 00 e1 e1 c0 00` |
| 10 | `0x00004292` | `0x018946` | `00 01 00 13 0a 01 00 11 00 11` | `0x018946`: delta `10`, mode `1`, height `17`, width `17`, render span `4`, bitmap `0x018950`, sample `00 1f 80 00 00 1f 80 00 00 07 80 00 00 0f 80 00` |
| 11 | `0x000042e0` | `0x018994` | `00 03 00 13 0a 01 00 14 00 0d` | `0x018994`: delta `10`, mode `1`, height `20`, width `13`, render span `2`, bitmap `0x01899e`, sample `0f 80 3f e0 70 70 60 30` |
| 12 | `0x00004312` | `0x0189c6` | `00 03 00 18 0a 01 00 18 00 0d` | `0x0189c6`: delta `10`, mode `1`, height `24`, width `13`, render span `2`, bitmap `0x0189d0`, sample `01 00 01 80 01 c0 01 e0` |
| 13 | `0x0000434c` | `0x018a00` | `00 01 00 1b 0a 01 00 1f 00 11` | `0x018a00`: delta `10`, mode `1`, height `31`, width `17`, render span `4`, bitmap `0x018a0a`, sample `01 00 00 00 01 80 00 00 01 c0 00 00 01 e0 00 00` |
| 14 | `0x000043d2` | `0x018a86` | `00 00 00 13 0a 01 00 12 00 12` | `0x018a86`: delta `10`, mode `1`, height `18`, width `18`, render span `4`, bitmap `0x018a90`, sample `00 c0 00 00 00 c0 00 00 30 c3 00 00 38 c7 00 00` |
| 15 | `0x00004424` | `0x018ad8` | `00 01 00 12 0a 01 00 0f 00 0f` | `0x018ad8`: delta `10`, mode `1`, height `15`, width `15`, render span `2`, bitmap `0x018ae2`, sample `80 00 e0 00 f8 00 fe 00` |
| 16 | `0x0000444c` | `0x018b00` | `00 01 00 12 0a 01 00 0f 00 0f` | `0x018b00`: delta `10`, mode `1`, height `15`, width `15`, render span `2`, bitmap `0x018b0a`, sample `00 02 00 0e 00 3e 00 fe` |
| 17 | `0x00003cb0` | `0x018364` | `00 04 00 15 0a 01 00 16 00 0b` | `0x018364`: delta `10`, mode `1`, height `22`, width `11`, render span `2`, bitmap `0x01836e`, sample `04 00 0e 00 1f 00 3f 80` |
| 18 | `0x00004474` | `0x018b28` | `00 04 00 15 0a 01 00 16 00 0a` | `0x018b28`: delta `10`, mode `1`, height `22`, width `10`, render span `2`, bitmap `0x018b32`, sample `f3 c0 f3 c0 f3 c0 f3 c0` |
| 19 | `0x00003ef0` | `0x0185a4` | `00 01 00 17 0a 01 00 1d 00 10` | `0x0185a4`: delta `10`, mode `1`, height `29`, width `16`, render span `2`, bitmap `0x0185ae`, sample `01 ff 07 ff 1f cc 3f cc` |
| 20 | `0x0000262a` | `0x016cde` | `00 03 00 17 0a 01 00 1b 00 0c` | `0x016cde`: delta `10`, mode `1`, height `27`, width `12`, render span `2`, bitmap `0x016ce8`, sample `0f 00 3f c0 70 e0 60 60` |
| 21 | `0x000044aa` | `0x018b5e` | `00 00 00 08 0a 01 00 09 00 12` | `0x018b5e`: delta `10`, mode `1`, height `9`, width `18`, render span `4`, bitmap `0x018b68`, sample `ff ff c0 00 ff ff c0 00 ff ff c0 00 ff ff c0 00` |
| 22 | `0x000044d8` | `0x018b8c` | `00 04 00 15 0a 01 00 18 00 0b` | `0x018b8c`: delta `10`, mode `1`, height `24`, width `11`, render span `2`, bitmap `0x018b96`, sample `04 00 0e 00 1f 00 3f 80` |
| 23 | `0x00003bd8` | `0x01828c` | `00 04 00 15 0a 01 00 16 00 0b` | `0x01828c`: delta `10`, mode `1`, height `22`, width `11`, render span `2`, bitmap `0x018296`, sample `04 00 0e 00 1f 00 3f 80` |
| 24 | `0x00003c44` | `0x0182f8` | `00 04 00 15 0a 01 00 16 00 0b` | `0x0182f8`: delta `10`, mode `1`, height `22`, width `11`, render span `2`, bitmap `0x018302`, sample `0e 00 0e 00 0e 00 0e 00` |
| 25 | `0x00003c0e` | `0x0182c2` | `00 00 00 10 0a 01 00 0b 00 11` | `0x0182c2`: delta `10`, mode `1`, height `11`, width `17`, render span `4`, bitmap `0x0182cc`, sample `00 18 00 00 00 18 00 00 00 0c 00 00 00 06 00 00` |
| 26 | `0x00003c7a` | `0x01832e` | `00 01 00 10 0a 01 00 0b 00 11` | `0x01832e`: delta `10`, mode `1`, height `11`, width `17`, render span `4`, bitmap `0x018338`, sample `0c 00 00 00 0c 00 00 00 18 00 00 00 30 00 00 00` |
| 27 | `0x0000558c` | `0x019c40` | `00 01 00 0c 0a 01 00 07 00 10` | `0x019c40`: delta `10`, mode `1`, height `7`, width `16`, render span `2`, bitmap `0x019c4a`, sample `e0 00 e0 00 e0 00 e0 00` |
| 28 | `0x00003ce6` | `0x01839a` | `00 00 00 10 0a 01 00 0b 00 12` | `0x01839a`: delta `10`, mode `1`, height `11`, width `18`, render span `4`, bitmap `0x0183a4`, sample `0c 0c 00 00 0c 0c 00 00 18 06 00 00 30 03 00 00` |
| 29 | `0x00004512` | `0x018bc6` | `00 02 00 11 0a 01 00 0f 00 0f` | `0x018bc6`: delta `10`, mode `1`, height `15`, width `15`, render span `2`, bitmap `0x018bd0`, sample `01 00 01 00 03 80 03 80` |
| 30 | `0x0000453a` | `0x018bee` | `00 02 00 11 0a 01 00 0f 00 0f` | `0x018bee`: delta `10`, mode `1`, height `15`, width `15`, render span `2`, bitmap `0x018bf8`, sample `ff fe 7f fc 7f fc 3f f8` |
| 32 | `0x00000c7c` | `0x015330` | `00 06 00 15 0a 01 00 16 00 04` | `0x015330`: delta `10`, mode `1`, height `22`, width `4`, render span `1`, bitmap `0x01533a`, sample `f0 00 f0 00` |

## Plausible Glyph-Entry Candidates in Referenced Ranges

A plausible entry satisfies the exact field constraints needed by `0x1f354`:
byte `+4` is a bitmap-data delta, byte `+5` is a small plane/mode value, word
`+6` is row count, and word `+8` is pixel width.

| Source record | Candidate | Bitmap | Delta | Mode | Height | Width | Render span | Sample bitmap bytes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `(unnamed)` @`0x00004c` | `0x001088` | `0x001092` | 10 | 1 | 32 | 9 | 2 | `1c 00 3e 00 3e 00 3e 00` |
| `(unnamed)` @`0x00004c` | `0x0010cc` | `0x00110a` | 62 | 0 | 6 | 30 | 4 | `80 00 7c 0f 80 00 7c 0f 80 00 7c 0f 80 00 7c 0f` |
| `(unnamed)` @`0x00004c` | `0x0010d2` | `0x0010dc` | 10 | 1 | 17 | 18 | 4 | `7c 0f 80 00 fe 1f c0 00 fe 1f c0 00 fe 1f c0 00` |
| `(unnamed)` @`0x00004c` | `0x001120` | `0x00112a` | 10 | 1 | 38 | 19 | 4 | `01 83 00 00 01 83 00 00 01 83 00 00 01 83 00 00` |
| `(unnamed)` @`0x00004c` | `0x0011c2` | `0x0011cc` | 10 | 1 | 40 | 21 | 4 | `00 30 00 00 00 78 00 00 00 78 00 00 00 78 00 00` |
| `(unnamed)` @`0x00004c` | `0x00126c` | `0x001276` | 10 | 1 | 33 | 22 | 4 | `03 c0 00 00 0f f0 00 00 1f f8 00 00 3c 3c 00 00` |
| `(unnamed)` @`0x00004c` | `0x0012fa` | `0x001304` | 10 | 1 | 29 | 21 | 4 | `01 f8 00 00 07 fe 00 00 0f ff 00 00 0f ff 00 00` |
| `(unnamed)` @`0x00004c` | `0x001378` | `0x001382` | 10 | 1 | 16 | 12 | 2 | `03 e0 07 f0 07 f0 0f f0` |
| `(unnamed)` @`0x00004c` | `0x0013a2` | `0x0013ac` | 10 | 1 | 40 | 11 | 2 | `00 c0 01 e0 03 e0 07 c0` |
| `(unnamed)` @`0x00004c` | `0x0013fc` | `0x001406` | 10 | 1 | 40 | 10 | 2 | `60 00 f0 00 f8 00 78 00` |
| `(unnamed)` @`0x00004c` | `0x001456` | `0x001460` | 10 | 1 | 21 | 21 | 4 | `00 f8 00 00 00 f8 00 00 00 f8 00 00 00 f8 00 00` |
| `(unnamed)` @`0x00004c` | `0x0014b4` | `0x0014be` | 10 | 1 | 25 | 25 | 4 | `00 1c 00 00 00 1c 00 00 00 1c 00 00 00 1c 00 00` |
| `(unnamed)` @`0x00004c` | `0x001522` | `0x00152c` | 10 | 1 | 15 | 10 | 2 | `0f c0 1f c0 1f 80 1f 80` |
| `(unnamed)` @`0x00004c` | `0x00154a` | `0x001554` | 10 | 1 | 5 | 23 | 4 | `7f ff fc 00 ff ff fe 00 ff ff fe 00 ff ff fe 00` |
| `(unnamed)` @`0x00004c` | `0x001568` | `0x001572` | 10 | 1 | 8 | 9 | 2 | `3e 00 7f 00 ff 80 ff 80` |
| `(unnamed)` @`0x00004c` | `0x001582` | `0x00158c` | 10 | 1 | 40 | 26 | 4 | `00 00 01 80 00 00 03 c0 00 00 03 80 00 00 07 80` |
| `(unnamed)` @`0x00004c` | `0x00162c` | `0x001636` | 10 | 1 | 29 | 21 | 4 | `01 fc 00 00 07 ff 00 00 0f ff 80 00 1f 07 c0 00` |
| `(unnamed)` @`0x00004c` | `0x0016aa` | `0x0016b4` | 10 | 1 | 29 | 22 | 4 | `07 f0 00 00 1f f8 00 00 7f f8 00 00 7c 78 00 00` |
| `(unnamed)` @`0x00004c` | `0x001728` | `0x001732` | 10 | 1 | 29 | 20 | 4 | `01 fc 00 00 0f ff 00 00 3f ff 80 00 3f 0f c0 00` |
| `(unnamed)` @`0x00004c` | `0x0017a6` | `0x0017b0` | 10 | 1 | 29 | 19 | 4 | `03 f0 00 00 1f fc 00 00 3f ff 00 00 7c 1f 80 00` |
| `(unnamed)` @`0x00004c` | `0x001824` | `0x00182e` | 10 | 1 | 29 | 21 | 4 | `00 1f 00 00 00 1f 00 00 00 3f 00 00 00 3f 00 00` |
| `(unnamed)` @`0x00004c` | `0x0018a2` | `0x0018ac` | 10 | 1 | 29 | 22 | 4 | `1f ff f0 00 3f ff f8 00 3f ff f0 00 38 00 00 00` |
| `(unnamed)` @`0x00004c` | `0x001920` | `0x00192a` | 10 | 1 | 29 | 21 | 4 | `00 0f e0 00 00 7f f0 00 01 ff e0 00 03 f8 00 00` |
| `(unnamed)` @`0x00004c` | `0x00199e` | `0x0019a8` | 10 | 1 | 29 | 21 | 4 | `7f ff f0 00 ff ff f8 00 ff ff f8 00 f0 00 70 00` |
| `COURIER` @`0x000418` | `0x001a1c` | `0x001a26` | 10 | 1 | 29 | 21 | 4 | `03 fe 00 00 0f ff 80 00 1f ff c0 00 3f 07 e0 00` |
| `COURIER` @`0x000418` | `0x001a9a` | `0x001aa4` | 10 | 1 | 29 | 21 | 4 | `03 fc 00 00 0f ff 00 00 1f ff 80 00 3f 07 c0 00` |
| `COURIER` @`0x000418` | `0x001b18` | `0x001b22` | 10 | 1 | 23 | 9 | 2 | `3e 00 7f 00 ff 80 ff 80` |
| `COURIER` @`0x000418` | `0x001b4a` | `0x001b88` | 62 | 0 | 10 | 22 | 4 | `78 00 78 00 f0 00 70 00 00 03 00 19 0a 01 00 18` |
| `COURIER` @`0x000418` | `0x001b50` | `0x001b5a` | 10 | 1 | 27 | 11 | 2 | `0f 80 1f c0 3f e0 3f e0` |
| `COURIER` @`0x000418` | `0x001b90` | `0x001b9a` | 10 | 1 | 24 | 23 | 4 | `00 00 02 00 00 00 0e 00 00 00 3e 00 00 00 fc 00` |
| `COURIER` @`0x000418` | `0x001bf4` | `0x001bfa` | 6 | 0 | 2 | 19 | 4 | `00 02 00 13 0a 01 00 0b` |
| `COURIER` @`0x000418` | `0x001bfa` | `0x001c04` | 10 | 1 | 11 | 26 | 4 | `ff ff ff c0 ff ff ff c0 ff ff ff c0 00 00 00 00` |
| `COURIER` @`0x000418` | `0x001c30` | `0x001c3a` | 10 | 1 | 24 | 23 | 4 | `80 00 00 00 e0 00 00 00 f8 00 00 00 7e 00 00 00` |
| `COURIER` @`0x000418` | `0x001c9a` | `0x001ca4` | 10 | 1 | 32 | 21 | 4 | `02 fa 00 00 0f ff 80 00 3f ff c0 00 7f af e0 00` |
| `COURIER` @`0x000418` | `0x001d24` | `0x001d2e` | 10 | 1 | 35 | 21 | 4 | `00 fc 00 00 03 ff 00 00 07 ff 80 00 0f c7 c0 00` |
| `COURIER` @`0x000418` | `0x001dba` | `0x001dc4` | 10 | 1 | 29 | 30 | 4 | `03 ff 80 00 07 ff 80 00 03 ff c0 00 00 0f c0 00` |
| `COURIER` @`0x000418` | `0x001e38` | `0x001e42` | 10 | 1 | 29 | 26 | 4 | `7f ff c0 00 ff ff f0 00 7f ff fc 00 0f 00 7e 00` |
| `COURIER` @`0x000418` | `0x001eb6` | `0x001ec0` | 10 | 1 | 29 | 25 | 4 | `00 1f c0 00 00 ff f3 00 03 ff ff 80 07 f5 7f 80` |
| `COURIER` @`0x000418` | `0x001f34` | `0x001f3e` | 10 | 1 | 29 | 26 | 4 | `7f ff 00 00 ff ff e0 00 7f ff f8 00 1e 01 fc 00` |
| `COURIER` @`0x000418` | `0x001fb2` | `0x001fbc` | 10 | 1 | 29 | 25 | 4 | `7f ff ff 00 ff ff ff 80 7f ff ff 80 07 80 03 80` |
| `COURIER` @`0x000418` | `0x002030` | `0x00203a` | 10 | 1 | 29 | 25 | 4 | `7f ff ff 00 ff ff ff 80 7f ff ff 80 07 80 03 80` |
| `COURIER` @`0x000418` | `0x0020ae` | `0x0020b8` | 10 | 1 | 29 | 27 | 4 | `00 3f 86 00 00 ff ef 00 03 ff ff 00 07 eb ff 00` |
| `COURIER` @`0x000418` | `0x00212c` | `0x002136` | 10 | 1 | 29 | 28 | 4 | `7f e0 7f e0 ff f0 ff f0 7f e0 7f e0 0f 00 0f 00` |
| `COURIER` @`0x000418` | `0x0021aa` | `0x0021b4` | 10 | 1 | 29 | 22 | 4 | `7f ff f8 00 ff ff fc 00 7f ff f8 00 00 78 00 00` |
| `COURIER` @`0x000418` | `0x002228` | `0x002232` | 10 | 1 | 29 | 27 | 4 | `03 ff ff c0 07 ff ff e0 03 ff ff c0 00 00 f0 00` |
| `COURIER` @`0x000418` | `0x0022a6` | `0x0022b0` | 10 | 1 | 29 | 28 | 4 | `7f f0 7f e0 ff f8 ff f0 7f f0 7f e0 07 80 0f 00` |
| `COURIER` @`0x000418` | `0x002324` | `0x00232e` | 10 | 1 | 29 | 27 | 4 | `7f ff 00 00 ff ff 80 00 7f ff 00 00 03 c0 00 00` |
| `COURIER` @`0x000418` | `0x0023a2` | `0x0023ac` | 10 | 1 | 29 | 30 | 4 | `7f c0 0f f8 ff c0 0f fc 7f e0 1f f8 0f e0 1f c0` |
| `LINE_PRINTER` @`0x0146b4` | `0x015330` | `0x01533a` | 10 | 1 | 22 | 4 | 1 | `f0 00 f0 00` |
| `LINE_PRINTER` @`0x0146b4` | `0x015366` | `0x015370` | 10 | 1 | 12 | 12 | 2 | `f0 f0 f0 f0 f0 f0 f0 f0` |
| `LINE_PRINTER` @`0x0146b4` | `0x015388` | `0x015392` | 10 | 1 | 24 | 17 | 4 | `03 87 00 00 03 87 00 00 03 87 00 00 03 06 00 00` |
| `LINE_PRINTER` @`0x0146b4` | `0x0153f2` | `0x0153fc` | 10 | 1 | 24 | 16 | 2 | `03 80 03 80 1f e0 7f f8` |
| `LINE_PRINTER` @`0x0146b4` | `0x01542c` | `0x015436` | 10 | 1 | 24 | 17 | 4 | `3c 02 00 00 7e 07 00 00 e7 06 00 00 c3 0e 00 00` |
| `LINE_PRINTER` @`0x0146b4` | `0x015496` | `0x0154a0` | 10 | 1 | 24 | 16 | 2 | `07 80 1f e0 1c e0 38 70` |
| `LINE_PRINTER` @`0x0146b4` | `0x0154d0` | `0x0154da` | 10 | 1 | 12 | 7 | 1 | `1e 00 1e 00` |
| `LINE_PRINTER` @`0x0146b4` | `0x0154f2` | `0x0154fc` | 10 | 1 | 25 | 9 | 2 | `03 80 07 80 0f 80 1f 00` |
| `LINE_PRINTER` @`0x0146b4` | `0x01552e` | `0x015538` | 10 | 1 | 25 | 9 | 2 | `e0 00 f0 00 f8 00 7c 00` |
| `LINE_PRINTER` @`0x0146b4` | `0x01556a` | `0x015574` | 10 | 1 | 14 | 15 | 2 | `03 80 03 80 03 80 43 84` |
| `LINE_PRINTER` @`0x0146b4` | `0x015590` | `0x01559a` | 10 | 1 | 15 | 15 | 2 | `03 80 03 80 03 80 03 80` |
| `LINE_PRINTER` @`0x0146b4` | `0x0155b8` | `0x0155c2` | 10 | 1 | 10 | 7 | 1 | `3e 00 3e 00` |
| `LINE_PRINTER` @`0x0146b4` | `0x0155d6` | `0x0155e0` | 10 | 1 | 3 | 9 | 2 | `ff 80 ff 80 ff 80` |
| `LINE_PRINTER` @`0x0146b4` | `0x0155e6` | `0x0155f0` | 10 | 1 | 5 | 6 | 1 | `fc 00 fc 00` |
| `LINE_PRINTER` @`0x0146b4` | `0x0155fa` | `0x015604` | 10 | 1 | 25 | 15 | 2 | `00 1e 00 1c 00 3c 00 38` |
| `LINE_PRINTER` @`0x0146b4` | `0x015636` | `0x015640` | 10 | 1 | 24 | 14 | 2 | `07 80 1f e0 3f f0 78 78` |
| `LINE_PRINTER` @`0x0146b4` | `0x015670` | `0x01567a` | 10 | 1 | 24 | 8 | 1 | `0f 00 1f 00` |
| `LINE_PRINTER` @`0x0146b4` | `0x0156a4` | `0x0156ab` | 7 | 0 | 2 | 23 | 4 | `02 00 17 0a 01 00 18 00` |
| `LINE_PRINTER` @`0x0146b4` | `0x0156aa` | `0x0156b4` | 10 | 1 | 24 | 14 | 2 | `1f c0 7f f0 7f f8 f0 78` |
| `LINE_PRINTER` @`0x0146b4` | `0x0156e4` | `0x0156ee` | 10 | 1 | 24 | 15 | 2 | `ff fc ff fc ff fc 00 3c` |
| `LINE_PRINTER` @`0x0146b4` | `0x01571e` | `0x015728` | 10 | 1 | 24 | 15 | 2 | `01 c0 01 c0 03 80 03 80` |
| `LINE_PRINTER` @`0x0146b4` | `0x015758` | `0x015762` | 10 | 1 | 24 | 13 | 2 | `ff f0 ff f0 ff f0 e0 00` |
| `LINE_PRINTER` @`0x0146b4` | `0x015792` | `0x01579c` | 10 | 1 | 24 | 16 | 2 | `00 70 00 f0 01 e0 03 c0` |
| `LINE_PRINTER` @`0x0146b4` | `0x0157cc` | `0x0157d6` | 10 | 1 | 24 | 16 | 2 | `ff ff ff ff ff ff 00 1e` |

## Current Interpretation

- The built-in firmware scan begins at address `0x80000`, so an `IC32,IC15`
  file offset maps to firmware address `0x80000 + offset`.
- Built-in font candidates set bit 30 in the selected context longword. That
  selects the `0x1f354` offset-table form, where word `record+8` gives the
  table delta and each 32-bit table entry is a relative offset from the
  selected record base.
- The earlier high-word-only interpretation was wrong: entries such as
  `0x00007792` in the `COURIER` table resolve to `record_start + 0x7792`, not
  absolute `0x7792`.
- This now gives concrete real-glyph fixtures for the renderer harness. For
  example, the unnamed record at `0x00004c` has context `0x4008004c`; table
  entry 0 resolves to glyph entry `0x001088`, whose bitmap starts at
  `0x001092`.
