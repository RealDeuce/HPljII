#!/usr/bin/env python3
"""Executable renderer fixtures for LaserJet II ROM-derived imaging behavior."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIRMWARE = ROOT / "generated" / "roms" / "ic30_ic13.bin"
RESOURCES = ROOT / "generated" / "roms" / "ic32_ic15.bin"
ANALYSIS = ROOT / "generated" / "analysis"


def u16(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 2], "big")


def u32(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def require_firmware() -> bytes:
    if not FIRMWARE.exists():
        raise FileNotFoundError("Missing generated/roms/ic30_ic13.bin; run tools/generate_rom_artifacts.py first")
    return FIRMWARE.read_bytes()


def require_resources() -> bytes:
    if not RESOURCES.exists():
        raise FileNotFoundError("Missing generated/roms/ic32_ic15.bin; run tools/generate_rom_artifacts.py first")
    return RESOURCES.read_bytes()


def resolve_builtin_glyph(resources: bytes, context: int, glyph_index: int) -> dict[str, int | bytes]:
    if not (context & 0x40000000):
        raise AssertionError(f"context 0x{context:08x} does not select the built-in offset-table form")
    firmware_address = context & 0x00FFFFFF
    if not (0x80000 <= firmware_address < 0xC0000):
        raise AssertionError(f"context 0x{context:08x} is outside the built-in resource window")
    base = firmware_address - 0x80000
    table = base + u16(resources, base + 8)
    entry = base + u32(resources, table + glyph_index * 4)
    bitmap_delta = resources[entry + 4]
    mode = resources[entry + 5]
    rows = u16(resources, entry + 6)
    width = u16(resources, entry + 8)
    span = (width + 7) // 8
    render_span = span
    if render_span & 1 and mode != 2 and render_span != 1:
        render_span += 1
    bitmap = entry + bitmap_delta
    return {
        "base": base,
        "table": table,
        "entry": entry,
        "bitmap": bitmap,
        "delta": bitmap_delta,
        "mode": mode,
        "rows": rows,
        "width": width,
        "span": span,
        "render_span": render_span,
        "sample": resources[bitmap : bitmap + min(16, rows * max(render_span, 1))],
    }


def expand_mode0(payload: bytes) -> list[int]:
    return [int.from_bytes(payload[i : i + 2], "big") for i in range(0, len(payload), 2)]


def expand_mode1(data: bytes, payload: bytes) -> list[int]:
    return [u16(data, 0x30914 + byte * 2) for byte in payload]


def expand_mode2(data: bytes, payload: bytes) -> list[int]:
    return [u32(data, 0x30B14 + byte * 4) for byte in payload]


def expand_mode3(data: bytes, payload: bytes) -> list[int]:
    out: list[int] = []
    for byte in payload:
        first = u16(data, 0x30914 + byte * 2)
        out.append((u16(data, 0x30914 + ((first >> 8) & 0xFF) * 2) << 16) | u16(data, 0x30914 + (first & 0xFF) * 2))
    return out


def coord_decode(coord: int, band_base: int = 0x100000, payload_offset: int = 0x40) -> dict[str, int]:
    row_index = (coord >> 12) & 0xF
    byte_pair_offset = (coord & 0xFF) * 2
    subbyte = (coord >> 8) & 0xF
    a001 = subbyte | (0x10 if subbyte else 0)
    return {
        "row_index": row_index,
        "byte_pair_offset": byte_pair_offset,
        "a001": a001,
        "a1": band_base + row_index * 0x20 + byte_pair_offset + payload_offset,
    }


def clip_count(coord: int, count: int, band_remainder: int) -> int:
    rows_here = band_remainder - ((coord >> 12) & 0xF)
    if count > rows_here:
        return ((count - rows_here) << 16) | (rows_here & 0xFFFF)
    return count


def dest_1f626_case(coord: int, d2_in: int, d3_in: int) -> dict[str, int | str]:
    band_base = 0x100000
    buffer_base = 0x200000
    stride = 0x100
    band_remainder = 8
    row = (coord >> 12) & 0xF
    a2 = (coord & 0xFF) * 2
    if d2_in == 0:
        return {
            "branch": "current band",
            "a1": band_base + row * 0x20 + a2,
            "d2": d2_in,
            "d3": clip_count(coord, d3_in, band_remainder),
        }
    if row > d2_in:
        rows_here = band_remainder - d2_in - row
        d3_out = ((d3_in - rows_here) << 16) | (rows_here & 0xFFFF) if d3_in > rows_here else d3_in
        return {
            "branch": "shifted current band",
            "a1": band_base + stride * d2_in + row * 0x20 + a2,
            "d2": d2_in,
            "d3": d3_out,
        }
    d2_out = d2_in - row
    return {
        "branch": "fallback buffer",
        "a1": buffer_base + stride * (row + d2_out) + a2,
        "d2": d2_out,
        "d3": d3_in,
    }


@dataclass(frozen=True)
class Write:
    dst: int
    source: str
    src: int
    size: int

    def text(self) -> str:
        kind = "word" if self.size == 2 else "byte"
        return f"dst+0x{self.dst:02x} <= {self.source}+0x{self.src:02x} {kind}"


@dataclass(frozen=True)
class RowCopyResult:
    writes: tuple[Write, ...]
    a1: int
    a2: int
    a3: int


def row_copy_setup(data: bytes, helper: int) -> dict[str, int | bool]:
    pos = helper
    d0_adjust = 0
    table_base = 0
    dest_phase = False
    source_phase = False
    source_row_skip = False
    for _ in range(80):
        op = u16(data, pos)
        if op == 0x2039 and u32(data, pos + 2) == 0x00783A1C:
            pos += 6
        elif op & 0xF1FF == 0x5180:
            amount = (op >> 9) & 7
            d0_adjust += 8 if amount == 0 else amount
            pos += 2
        elif op == 0x0480:
            d0_adjust += u32(data, pos + 2)
            pos += 6
        elif op in (0x41F9, 0x49F9):
            table_base = u32(data, pos + 2)
            pos += 6
        elif op == 0xD2F9 and u32(data, pos + 2) == 0x00783A46:
            dest_phase = True
            pos += 6
        elif op == 0xD4F9 and u32(data, pos + 2) == 0x00783A46:
            source_phase = True
            pos += 6
        elif op == 0x3079 and u32(data, pos + 2) == 0x00783A40:
            source_row_skip = True
            pos += 6
        elif op in (0x48E7,):
            pos += 4
        elif op in (0xE54B,):
            pos += 2
        elif op in (0x2070, 0x2874):
            pos += 4
        elif op in (0x4ED0, 0x4ED4):
            break
        else:
            raise AssertionError(f"unhandled row-copy setup opcode 0x{op:04x} at 0x{pos:06x}")
    if table_base == 0:
        raise AssertionError(f"no row-count table found for helper 0x{helper:06x}")
    return {
        "table_base": table_base,
        "d0_adjust": d0_adjust,
        "dest_phase": dest_phase,
        "source_phase": source_phase,
        "source_row_skip": source_row_skip,
    }


def simulate_row_copy(data: bytes, helper: int, rows: int, stride: int = 0x20, phase: int = 0x10, source_row_delta: int = 0x04) -> RowCopyResult:
    setup = row_copy_setup(data, helper)
    target = u32(data, int(setup["table_base"]) + rows * 4)
    d0 = stride - int(setup["d0_adjust"])
    a1 = phase if setup["dest_phase"] else 0
    a2 = phase if setup["source_phase"] else 0
    a3 = 0
    writes: list[Write] = []
    pos = target
    for _ in range(2000):
        op = u16(data, pos)
        if op == 0x4E75:
            return RowCopyResult(tuple(writes), a1, a2, a3)
        if op == 0x4CDF:
            pos += 4
        elif op == 0x129A:
            writes.append(Write(a1, "A2", a2, 1))
            a2 += 1
            pos += 2
        elif op == 0x12DA:
            writes.append(Write(a1, "A2", a2, 1))
            a2 += 1
            a1 += 1
            pos += 2
        elif op == 0x129B:
            writes.append(Write(a1, "A3", a3, 1))
            a3 += 1
            pos += 2
        elif op == 0x329A:
            writes.append(Write(a1, "A2", a2, 2))
            a2 += 2
            pos += 2
        elif op == 0x32DA:
            writes.append(Write(a1, "A2", a2, 2))
            a2 += 2
            a1 += 2
            pos += 2
        elif op == 0xD3C0:
            a1 += d0
            pos += 2
        elif op == 0xD5C8:
            a2 += source_row_delta
            pos += 2
        else:
            raise AssertionError(f"unhandled row-copy tail opcode 0x{op:04x} at 0x{pos:06x}")
    raise AssertionError(f"row-copy tail from 0x{target:06x} did not reach RTS")


def assert_equal(name: str, actual: object, expected: object) -> str:
    if actual != expected:
        raise AssertionError(f"{name}: expected {expected!r}, got {actual!r}")
    return f"- {name}: ok"


def run_selftest(data: bytes, resources: bytes) -> list[str]:
    lines = ["# IC30/IC13 Executable Renderer Fixture Harness", ""]
    lines.append("This report is emitted by `tools/render_fixture_harness.py` after executing ROM-derived fixture models.")
    lines.append("")
    checks: list[str] = []

    sample = bytes.fromhex("00 01 02 03 04 05 08 0f 10 33 55 aa f0 ff")
    checks.append(assert_equal("mode 0 literal words", expand_mode0(bytes.fromhex("12 34 ab cd 00 ff 55 aa")), [0x1234, 0xABCD, 0x00FF, 0x55AA]))
    checks.append(assert_equal("mode 1 byte expansion", expand_mode1(data, sample), [0x0000, 0x0003, 0x000C, 0x000F, 0x0030, 0x0033, 0x00C0, 0x00FF, 0x0300, 0x0F0F, 0x3333, 0xCCCC, 0xFF00, 0xFFFF]))
    checks.append(assert_equal("mode 2 byte expansion", expand_mode2(data, sample), [0x00000000, 0x00000700, 0x00003800, 0x00003F00, 0x0001C000, 0x0001C700, 0x000E0000, 0x000FFF00, 0x00700000, 0x03F03F00, 0x1C71C700, 0xE38E3800, 0xFFF00000, 0xFFFFFF00]))
    checks.append(assert_equal("mode 3 cascaded expansion", expand_mode3(data, sample), [0x00000000, 0x0000000F, 0x000000F0, 0x000000FF, 0x00000F00, 0x00000F0F, 0x0000F000, 0x0000FFFF, 0x000F0000, 0x00FF00FF, 0x0F0F0F0F, 0xF0F0F0F0, 0xFFFF0000, 0xFFFFFFFF]))

    checks.append(assert_equal("coordinate decode 0x1234", coord_decode(0x1234), {"row_index": 1, "byte_pair_offset": 0x68, "a001": 0x12, "a1": 0x1000C8}))
    checks.append(assert_equal("band clip 0x7000 count 5", clip_count(0x7000, 5, 8), 0x00040001))
    checks.append(assert_equal("destination shifted current band", dest_1f626_case(0x3234, 2, 3), {"branch": "shifted current band", "a1": 0x1002C8, "d2": 2, "d3": 3}))
    checks.append(assert_equal("destination fallback buffer", dest_1f626_case(0x1234, 12, 5), {"branch": "fallback buffer", "a1": 0x200C68, "d2": 11, "d3": 5}))

    width3 = simulate_row_copy(data, u32(data, 0x1F08E + 3 * 4), 3)
    checks.append(assert_equal("main row-copy width 3 rows 3 writes", [write.text() for write in width3.writes], [
        "dst+0x00 <= A2+0x00 word",
        "dst+0x02 <= A3+0x00 byte",
        "dst+0x20 <= A2+0x02 word",
        "dst+0x22 <= A3+0x01 byte",
        "dst+0x40 <= A2+0x04 word",
        "dst+0x42 <= A3+0x02 byte",
    ]))
    checks.append(assert_equal("main row-copy width 3 final registers", (width3.a1, width3.a2, width3.a3), (0x60, 0x06, 0x03)))

    width16 = simulate_row_copy(data, u32(data, 0x1F08E + 16 * 4), 3)
    checks.append(assert_equal("main row-copy width 16 rows 3 write count", len(width16.writes), 24))
    checks.append(assert_equal("main row-copy width 16 first/last writes", (width16.writes[0].text(), width16.writes[-1].text()), ("dst+0x00 <= A2+0x00 word", "dst+0x4e <= A2+0x2e word")))
    checks.append(assert_equal("main row-copy width 16 final registers", (width16.a1, width16.a2, width16.a3), (0x60, 0x30, 0x00)))

    rem1 = simulate_row_copy(data, u32(data, 0x1F1AC + 1 * 4), 3)
    checks.append(assert_equal("remainder row-copy width 1 rows 3 writes", [write.text() for write in rem1.writes], [
        "dst+0x10 <= A3+0x00 byte",
        "dst+0x30 <= A3+0x01 byte",
        "dst+0x50 <= A3+0x02 byte",
    ]))
    checks.append(assert_equal("remainder row-copy width 1 final registers", (rem1.a1, rem1.a2, rem1.a3), (0x70, 0x00, 0x03)))

    chunk16 = simulate_row_copy(data, 0x2F27C, 3)
    checks.append(assert_equal("chunk row-copy width 16 rows 3 write count", len(chunk16.writes), 24))
    checks.append(assert_equal("chunk row-copy width 16 first/last writes", (chunk16.writes[0].text(), chunk16.writes[-1].text()), ("dst+0x10 <= A2+0x10 word", "dst+0x5e <= A2+0x46 word")))
    checks.append(assert_equal("chunk row-copy width 16 final registers", (chunk16.a1, chunk16.a2, chunk16.a3), (0x70, 0x4C, 0x00)))

    default_glyph0 = resolve_builtin_glyph(resources, 0x4008004C, 0)
    checks.append(assert_equal("resource context 0x4008004c glyph 0 fields", {key: default_glyph0[key] for key in ("base", "table", "entry", "bitmap", "delta", "mode", "rows", "width", "render_span")}, {
        "base": 0x00004C,
        "table": 0x000096,
        "entry": 0x001088,
        "bitmap": 0x001092,
        "delta": 10,
        "mode": 1,
        "rows": 32,
        "width": 9,
        "render_span": 2,
    }))
    checks.append(assert_equal("resource context 0x4008004c glyph 0 bitmap sample", bytes(default_glyph0["sample"]).hex(" "), "1c 00 3e 00 3e 00 3e 00 3e 00 3e 00 3e 00 3e 00"))

    courier_glyph0 = resolve_builtin_glyph(resources, 0x44080418, 0)
    checks.append(assert_equal("resource context 0x44080418 glyph 0 fields", {key: courier_glyph0[key] for key in ("base", "table", "entry", "bitmap", "delta", "mode", "rows", "width", "render_span")}, {
        "base": 0x000418,
        "table": 0x000462,
        "entry": 0x007BAA,
        "bitmap": 0x007BB4,
        "delta": 10,
        "mode": 1,
        "rows": 29,
        "width": 28,
        "render_span": 4,
    }))

    line_printer_glyph0 = resolve_builtin_glyph(resources, 0x440946B4, 0)
    checks.append(assert_equal("resource context 0x440946b4 glyph 0 fields", {key: line_printer_glyph0[key] for key in ("base", "table", "entry", "bitmap", "delta", "mode", "rows", "width", "render_span")}, {
        "base": 0x0146B4,
        "table": 0x0146FE,
        "entry": 0x018730,
        "bitmap": 0x01873A,
        "delta": 10,
        "mode": 1,
        "rows": 16,
        "width": 16,
        "render_span": 2,
    }))

    lines.append(f"checks: {len(checks)}")
    lines.append("")
    lines.extend(checks)
    lines.append("")
    return lines


def main() -> None:
    data = require_firmware()
    resources = require_resources()
    report = "\n".join(run_selftest(data, resources))
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    (ANALYSIS / "ic30_ic13_renderer_fixture_harness.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
