# IC30/IC13 Destination and Clipping Fixtures

These fixtures model the arithmetic in bitmap destination helpers `0x1f3d4`,
`0x1f414`, and the main cases of `0x1f626`. They use synthetic render state so
renderer tests can validate the arithmetic independently of a full page job.

## Helper `0x1f3d4` Coordinate Decode

Input `D1` is treated as a packed coordinate word. The helper computes:

- `row_index = D1 >> 12`, used as an index into word table `0x7839f8`.
- `byte_pair_offset = (D1 & 0xff) * 2`, added directly to the destination
  pointer.
- `subbyte = (D1 >> 8) & 0x0f`; if nonzero, bit `0x10` is set before writing
  the low byte to MMIO `0xa001`.
- destination pointer `A1 = 0x783a28 + row_offsets[row_index] +
  byte_pair_offset + A2`.

Synthetic state for the fixture table below: `0x783a28 = 0x100000`, `A2 =
0x40`, and `row_offsets[i] = i * 0x20`.

| Coordinate | Row index | Byte-pair offset | `0xa001` value | Expected `A1` |
| ---: | ---: | ---: | ---: | ---: |
| `0x0000` | 0 | `0x0000` | `0x00` | `0x100040` |
| `0x0001` | 0 | `0x0002` | `0x00` | `0x100042` |
| `0x00ff` | 0 | `0x01fe` | `0x00` | `0x10023e` |
| `0x0100` | 0 | `0x0000` | `0x11` | `0x100040` |
| `0x0f00` | 0 | `0x0000` | `0x1f` | `0x100040` |
| `0x1000` | 1 | `0x0000` | `0x00` | `0x100060` |
| `0x1234` | 1 | `0x0068` | `0x12` | `0x1000c8` |
| `0x8abc` | 8 | `0x0178` | `0x1a` | `0x1002b8` |
| `0xf0ff` | 15 | `0x01fe` | `0x00` | `0x10041e` |

## Helper `0x1f414` Band Count Split

After `0x1f3d4`, helper `0x1f414` clips the requested count in `D3` against
`0x783a20 - row_index`. If the count crosses the band boundary, the returned
longword packs `remaining_after_band` in the high word and `rows_in_this_band`
in the low word.

| Coordinate | Input count | `0x783a20` | Rows in this band | Remaining after band | Returned `D3` |
| ---: | ---: | ---: | ---: | ---: | ---: |
| `0x0000` | 5 | 8 | 5 | 0 | `0x00000005` |
| `0x3000` | 5 | 8 | 5 | 0 | `0x00000005` |
| `0x7000` | 5 | 8 | 1 | 4 | `0x00040001` |
| `0x8000` | 5 | 8 | 0 | 5 | `0x00050000` |
| `0xa200` | 10 | 12 | 2 | 8 | `0x00080002` |

## Helper `0x1f626` Destination Cases

Helper `0x1f626` repeats the same packed-coordinate decode, then chooses
between current-band, shifted-in-band, and fallback-buffer destinations using
`D2` and `0x783a20`. The table uses synthetic state: `0x783a28=0x100000`,
`0x7810b4=0x200000`, `0x783a1c=0x100`, `0x783a20=8`, `A2=(coord & 0xff)*2`,
and `row_offsets[i]=i*0x20`.

| Case | Coordinate | Input `D2` | Input count `D3` | Expected branch | Expected `A1` | Returned `D2` | Returned `D3` |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| current band/no D2 | `0x1234` | 0 | 5 | current band | `0x100088` | 0 | `0x00000005` |
| shifted current band | `0x3234` | 2 | 3 | shifted current band | `0x1002c8` | 2 | `0x00000003` |
| fallback buffer | `0x1234` | 12 | 5 | fallback buffer | `0x200c68` | 11 | `0x00000005` |
| band boundary split | `0x7002` | 1 | 4 | shifted current band | `0x1001e4` | 1 | `0x00040000` |
