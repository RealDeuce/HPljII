#!/usr/bin/env python3
"""Generate local LaserJet II ROM analysis indexes from verified artifacts."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "generated"
FIRMWARE = GENERATED / "roms" / "ic30_ic13.bin"
RESOURCES = GENERATED / "roms" / "ic32_ic15.bin"
ANALYSIS = GENERATED / "analysis"
DISASM = GENERATED / "disasm" / "ic30_ic13_reset_000110.lst"


PRINTABLE = set(range(0x20, 0x7f))


def write_if_changed(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = text.encode("utf-8")
    old = path.read_bytes() if path.exists() else None
    if old != data:
        path.write_bytes(data)


def require_artifacts() -> None:
    missing = [path for path in (FIRMWARE, RESOURCES) if not path.exists()]
    if missing:
        names = ", ".join(str(path.relative_to(ROOT)) for path in missing)
        raise FileNotFoundError(f"Missing generated ROM artifacts: {names}. Run tools/generate_rom_artifacts.py first.")


def extract_strings(data: bytes, min_len: int = 4) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    start: int | None = None
    for i, b in enumerate(data + b"\x00"):
        if b in PRINTABLE:
            if start is None:
                start = i
            continue
        if start is not None and i - start >= min_len:
            out.append((start, data[start:i].decode("ascii", errors="replace")))
        start = None
    return out


def format_strings(title: str, strings: list[tuple[int, str]]) -> str:
    lines = [f"# {title}", "", f"count: {len(strings)}", ""]
    for offset, value in strings:
        lines.append(f"{offset:06x}  {value}")
    lines.append("")
    return "\n".join(lines)


def find_named_markers(data: bytes, names: list[bytes]) -> dict[str, list[int]]:
    found: dict[str, list[int]] = {}
    for name in names:
        offsets: list[int] = []
        start = 0
        while True:
            pos = data.find(name, start)
            if pos < 0:
                break
            offsets.append(pos)
            start = pos + 1
        found[name.decode("ascii")] = offsets
    return found


def detect_regular_groups(offsets: list[int]) -> list[list[int]]:
    groups: list[list[int]] = []
    if len(offsets) < 3:
        return groups
    for step in (976, 1104, 1108):
        group = [offsets[0]]
        last = offsets[0]
        for off in offsets[1:]:
            if off - last == step:
                group.append(off)
            elif len(group) >= 3:
                groups.append(group)
                group = [off]
            else:
                group = [off]
            last = off
        if len(group) >= 3:
            groups.append(group)
    return groups


def align_even(value: int) -> int:
    return value if value % 2 == 0 else value + 1


def u16(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 2], "big")


def s16(data: bytes, offset: int) -> int:
    value = u16(data, offset)
    return value - 0x10000 if value & 0x8000 else value


def u32(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "big")


def find_all(data: bytes, needle: bytes) -> list[int]:
    offsets: list[int] = []
    start = 0
    while True:
        pos = data.find(needle, start)
        if pos < 0:
            break
        offsets.append(pos)
        start = pos + 1
    return offsets


def jsr_abs_refs(data: bytes, target: int) -> list[int]:
    return find_all(data, b"\x4e\xb9" + target.to_bytes(4, "big"))


def pcl_symbol_set_code(value: int) -> str:
    number, suffix = divmod(value, 32)
    if 1 <= suffix <= 26:
        return f"{number}{chr(64 + suffix)}"
    return f"0x{value:04x}"


SYMBOL_SET_NAMES = {
    0x0004: "ISO 60: Norwegian version 1",
    0x0005: "HP Roman Extension",
    0x0006: "ISO 25: French",
    0x0007: "HP German",
    0x0009: "ISO 15: Italian",
    0x000B: "ISO 14: JIS ASCII",
    0x0013: "ISO 11: Swedish",
    0x0015: "ISO 6: ASCII",
    0x0024: "ISO 61: Norwegian version 2",
    0x0025: "ISO 4: United Kingdom",
    0x0026: "ISO 69: French",
    0x0027: "ISO 21: German",
    0x004B: "ISO 57: Chinese",
    0x0053: "ISO 17: Spanish",
    0x0055: "ISO 2: International Reference Version",
    0x0073: "ISO 10: Swedish",
    0x0093: "ISO 16: Portuguese",
    0x00B3: "ISO 84: Portuguese",
    0x00D3: "ISO 85: Spanish",
    0x0115: "HP Roman-8",
    0x0033: "HP Spanish",
}


def symbol_set_name(value: int) -> str:
    return SYMBOL_SET_NAMES.get(value, "(unidentified)")


def resource_marker_report(data: bytes) -> str:
    markers = find_named_markers(data, [b"HEAD", b"COURIER", b"LINE_PRINTER", b"SH7-9233-01", b"SH7-9234-01"])
    lines = ["# IC32/IC15 Resource Marker Index", ""]
    for name, offsets in markers.items():
        hex_offsets = ", ".join(f"0x{off:06x}" for off in offsets)
        lines.append(f"{name}: {len(offsets)} occurrence(s)")
        lines.append(hex_offsets if hex_offsets else "(none)")
        groups = detect_regular_groups(offsets)
        if groups:
            lines.append("regular groups:")
            for group in groups:
                lines.append(f"  {len(group)} entries from 0x{group[0]:06x} to 0x{group[-1]:06x}")
        lines.append("")
    return "\n".join(lines)


def font_record_offsets(data: bytes) -> list[tuple[str, int]]:
    records: list[tuple[str, int]] = []
    for name in (b"COURIER", b"LINE_PRINTER"):
        start = 0
        while True:
            pos = data.find(name, start)
            if pos < 0:
                break
            records.append((name.decode("ascii"), pos))
            start = pos + 1
    return sorted(records, key=lambda item: item[1])


def font_record_start_for_name(name: str, offset: int) -> int:
    return align_even(offset + len(name))


def infer_font_record_name(data: bytes, record_start: int) -> tuple[str, int | None]:
    for raw_name in (b"LINE_PRINTER", b"COURIER"):
        name_start = record_start - len(raw_name)
        if name_start >= 0 and data[name_start:record_start] == raw_name:
            return raw_name.decode("ascii"), name_start
        name_start = record_start - len(raw_name) - 1
        if name_start >= 0 and data[name_start : name_start + len(raw_name)] == raw_name:
            padding = data[name_start + len(raw_name) : record_start]
            if all(byte == 0 for byte in padding):
                return raw_name.decode("ascii"), name_start
    return "(unnamed)", None


def firmware_scanned_font_records(data: bytes) -> list[dict[str, int | str | None]]:
    records: list[dict[str, int | str | None]] = []
    cursor = 0
    seen = 0
    while cursor + 12 <= len(data) and seen < 256:
        marker = u32(data, cursor)
        if marker == 0x48454144:  # HEAD
            length = u32(data, cursor + 4)
            if length <= 0:
                break
            cursor += length
            continue
        if marker in (0x00000014, 0x00000015):
            length = u32(data, cursor + 4)
            table_delta = u16(data, cursor + 8)
            if length <= 0 or cursor + length > len(data):
                break
            name, name_offset = infer_font_record_name(data, cursor)
            byte_c = data[cursor + 0x0C]
            byte_d = data[cursor + 0x0D]
            context_flags = 0x40000000 | ((byte_d & 0x03) << 28)
            if byte_c == 2:
                context_flags |= 0x04000000
            firmware_address = 0x80000 + cursor
            records.append(
                {
                    "name": name,
                    "name_offset": name_offset,
                    "record_start": cursor,
                    "firmware_address": firmware_address,
                    "length": length,
                    "table_delta": table_delta,
                    "table": cursor + table_delta,
                    "first_char": u16(data, cursor + 0x0E),
                    "last_char": u16(data, cursor + 0x10),
                    "height_a": u16(data, cursor + 0x12),
                    "width_a": u16(data, cursor + 0x14),
                    "height_b": u16(data, cursor + 0x1C),
                    "width_b": u16(data, cursor + 0x1E),
                    "class_byte": data[cursor + 0x20],
                    "style_byte": byte_d,
                    "context_longword": context_flags | firmware_address,
                }
            )
            cursor += length
            seen += 1
            continue
        if marker in (0x00000000, 0xFFFFFFFF):
            break
        cursor += 2
    return records


def decode_font_record(data: bytes, name: str, offset: int, next_same: int | None) -> list[str]:
    record_start = font_record_start_for_name(name, offset)
    header_words = [u16(data, record_start + i * 2) for i in range(0, 24)]
    header_signed = [s16(data, record_start + i * 2) for i in range(0, 24)]
    length = u32(data, record_start + 4)
    offset_table_delta = u16(data, record_start + 8)
    offset_table = record_start + offset_table_delta
    glyph_offsets = [(u32(data, offset_table + i * 4), record_start + u32(data, offset_table + i * 4)) for i in range(0, 16)]
    next_delta = None if next_same is None else next_same - offset
    structured = u32(data, record_start) in (0x00000014, 0x00000015) and offset_table_delta == 0x004A
    lines = [
        f"## {name} @0x{offset:06x}",
        "",
        f"- firmware record start: `0x{record_start:06x}`",
        f"- built-in firmware address: `0x{0x80000 + record_start:06x}`",
        f"- header-like record: `{'yes' if structured else 'no'}`",
        f"- length field at record + 4: `0x{length:08x}` ({length})",
        f"- next same-name delta: `{next_delta}`" if next_delta is not None else "- next same-name delta: `(none)`",
        f"- candidate offset-table delta: `0x{offset_table_delta:04x}`",
        f"- candidate offset-table address: `0x{offset_table:06x}`",
        "",
        "First 24 header words, unsigned and signed:",
        "",
        "| Index | Address | Unsigned | Signed |",
        "| ---: | --- | ---: | ---: |",
    ]
    for i, (word, signed) in enumerate(zip(header_words, header_signed)):
        lines.append(f"| {i} | `0x{record_start + i * 2:06x}` | `0x{word:04x}` | {signed} |")
    lines.extend(
        [
            "",
            "First 16 firmware offset-table entries. Entries are 32-bit offsets relative to the selected record base.",
            "",
        ]
    )
    lines.append("| Index | Relative offset | Resource target |")
    lines.append("| ---: | ---: | ---: |")
    for i, (raw32, target) in enumerate(glyph_offsets):
        lines.append(f"| {i} | `0x{raw32:08x}` | `0x{target:06x}` |")
    lines.append("")
    return lines


def font_record_report(data: bytes) -> str:
    records = font_record_offsets(data)
    by_name: dict[str, list[int]] = {}
    for name, offset in records:
        by_name.setdefault(name, []).append(offset)
    next_same: dict[tuple[str, int], int | None] = {}
    for name, offsets in by_name.items():
        for i, offset in enumerate(offsets):
            next_same[(name, offset)] = offsets[i + 1] if i + 1 < len(offsets) else None

    lines = ["# IC32/IC15 Candidate Font Records", ""]
    lines.append("String search is useful for labeling records, but the firmware stores the selected context as the record start address, not the string address.")
    lines.append("For named built-in records, the record start is the even address immediately after the name/padding and begins with longword `0x00000014` or `0x00000015`.")
    lines.append("Other name hits are likely embedded in glyph bitmap/data payloads.")
    lines.append("")
    lines.append("| Name | Name offset | Header-like | Record start | Firmware address | Length | Next same-name delta | Offset table |")
    lines.append("| --- | --- | --- | --- | ---: | ---: | ---: | --- |")
    for name, offset in records:
        record_start = font_record_start_for_name(name, offset)
        length = u32(data, record_start + 4)
        table = record_start + u16(data, record_start + 8)
        structured = u32(data, record_start) in (0x00000014, 0x00000015) and u16(data, record_start + 8) == 0x004A
        nxt = next_same[(name, offset)]
        delta = "" if nxt is None else str(nxt - offset)
        lines.append(f"| `{name}` | `0x{offset:06x}` | {'yes' if structured else 'no'} | `0x{record_start:06x}` | `0x{0x80000 + record_start:06x}` | {length} | {delta} | `0x{table:06x}` |")
    lines.append("")

    for name, offset in records:
        record_start = font_record_start_for_name(name, offset)
        structured = u32(data, record_start) in (0x00000014, 0x00000015) and u16(data, record_start + 8) == 0x004A
        if structured:
            lines.extend(decode_font_record(data, name, offset, next_same[(name, offset)]))
    return "\n".join(lines)


def resource_glyph_probe_report(data: bytes) -> str:
    header_records = firmware_scanned_font_records(data)

    def table_limit(record: dict[str, int | str]) -> int:
        return min(len(data), int(record["record_start"]) + int(record["length"]))

    def table_targets(record: dict[str, int | str]) -> list[tuple[int, int, int]]:
        base = int(record["record_start"])
        table = int(record["table"])
        end = table_limit(record)
        targets: list[tuple[int, int, int]] = []
        pos = table
        index = 0
        while pos + 4 <= end:
            relative = u32(data, pos)
            target = base + relative
            if relative and 0 <= target < len(data):
                targets.append((index, relative, target))
            pos += 4
            index += 1
        return targets

    def plausible_glyph_entry(offset: int) -> dict[str, int | bytes] | None:
        if offset < 0 or offset + 10 >= len(data):
            return None
        bitmap_delta = data[offset + 4]
        plane_mode = data[offset + 5]
        height = u16(data, offset + 6)
        width = u16(data, offset + 8)
        if not (4 <= bitmap_delta <= 0x40):
            return None
        if plane_mode not in (0, 1, 2):
            return None
        if not (1 <= height <= 128):
            return None
        if not (1 <= width <= 128):
            return None
        span = (width + 7) // 8
        render_span = span
        if render_span & 1 and plane_mode != 2 and render_span != 1:
            render_span += 1
        bitmap = offset + bitmap_delta
        if bitmap + min(height, 4) * max(render_span, 1) > len(data):
            return None
        return {
            "bitmap_delta": bitmap_delta,
            "plane_mode": plane_mode,
            "height": height,
            "width": width,
            "span": span,
            "render_span": render_span,
            "bitmap": bitmap,
            "sample": data[bitmap : bitmap + min(16, min(height, 4) * max(render_span, 1))],
        }

    def first_candidate_in_range(start: int, end: int) -> tuple[int, dict[str, int | bytes]] | None:
        for pos in range(max(0, start), min(len(data), end)):
            candidate = plausible_glyph_entry(pos)
            if candidate is not None:
                return pos, candidate
        return None

    def referenced_ranges(record: dict[str, int | str]) -> list[tuple[int, int]]:
        targets = sorted(set(target for _, _relative, target in table_targets(record) if target < len(data)))
        ranges: list[tuple[int, int]] = []
        for index, target in enumerate(targets):
            next_target = targets[index + 1] if index + 1 < len(targets) else min(len(data), target + 0x100)
            if next_target <= target:
                next_target = min(len(data), target + 0x100)
            ranges.append((target, min(next_target, target + 0x120)))
        return ranges

    lines = ["# IC32/IC15 Resource Glyph Probe", ""]
    lines.append("Generated from the firmware-scanned built-in font records and the field layout consumed by glyph resolver `0x1f354`.")
    lines.append("The firmware selects a context longword whose low 24 bits are a resource address. For built-in records it sets bit 30, so `0x1f354` uses the offset-table form.")
    lines.append("")

    lines.append("## Firmware-Scanned Font Records")
    lines.append("")
    lines.append("| Name | Name offset | Record start | Firmware address | Context longword | Table | Table entries | First..last char | Size-like words | Length | Class/style |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | --- |")
    for record in header_records:
        targets = table_targets(record)
        name_offset = record["name_offset"]
        name_text = f"`0x{int(name_offset):06x}`" if name_offset is not None else "(none)"
        lines.append(
            f"| `{record['name']}` | {name_text} | `0x{int(record['record_start']):06x}` | `0x{int(record['firmware_address']):06x}` | "
            f"`0x{int(record['context_longword']):08x}` | `0x{int(record['table']):06x}` | {len(targets)} | "
            f"`0x{int(record['first_char']):04x}`..`0x{int(record['last_char']):04x}` | "
            f"`{int(record['height_a'])}x{int(record['width_a'])}`, `{int(record['height_b'])}x{int(record['width_b'])}` | "
            f"`0x{int(record['length']):08x}` | `0x{int(record['class_byte']):02x}`/`0x{int(record['style_byte']):02x}` |"
        )
    lines.append("")

    sample_records = [
        next((record for record in header_records if record["name"] == "(unnamed)" and int(record["record_start"]) == 0x00004C), None),
        next((record for record in header_records if record["name"] == "COURIER" and int(record["record_start"]) == 0x000418), None),
        next((record for record in header_records if record["name"] == "LINE_PRINTER" and int(record["record_start"]) == 0x0146B4), None),
    ]
    lines.append("## Table Target Probes")
    lines.append("")
    for record in [record for record in sample_records if record is not None]:
        targets = table_targets(record)
        unique_targets = sorted(set(target for _, _relative, target in targets if target < len(data)))
        lines.append(f"### `{record['name']}` record @`0x{int(record['record_start']):06x}`")
        lines.append("")
        lines.append(f"- nonzero table entries: `{len(targets)}`")
        lines.append(f"- unique in-image target range: `0x{unique_targets[0]:06x}`..`0x{unique_targets[-1]:06x}`" if unique_targets else "- unique in-image target range: `(none)`")
        lines.append("")
        lines.append("| Table index | Relative offset | Resource target | Bytes at target | Firmware `0x1f354` fields |")
        lines.append("| ---: | ---: | ---: | --- | --- |")
        for index, relative, target in targets[:32]:
            end = min(len(data), target + 0x100)
            candidate = first_candidate_in_range(target, end)
            target_bytes = data[target : target + 10].hex(" ") if target < len(data) else "(outside image)"
            if candidate is None:
                candidate_text = "(none in next 0x100 bytes)"
            else:
                candidate_offset, details = candidate
                candidate_text = (
                    f"`0x{candidate_offset:06x}`: delta `{int(details['bitmap_delta'])}`, mode `{int(details['plane_mode'])}`, "
                    f"height `{int(details['height'])}`, width `{int(details['width'])}`, render span `{int(details['render_span'])}`, "
                    f"bitmap `0x{int(details['bitmap']):06x}`, sample `{bytes(details['sample']).hex(' ')}`"
                )
            lines.append(f"| {index} | `0x{relative:08x}` | `0x{target:06x}` | `{target_bytes}` | {candidate_text} |")
        lines.append("")

    lines.append("## Plausible Glyph-Entry Candidates in Referenced Ranges")
    lines.append("")
    lines.append("A plausible entry satisfies the exact field constraints needed by `0x1f354`: byte `+4` is a bitmap-data delta, byte `+5` is a small plane/mode value, word `+6` is row count, and word `+8` is pixel width.")
    lines.append("")
    lines.append("| Source record | Candidate | Bitmap | Delta | Mode | Height | Width | Render span | Sample bitmap bytes |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |")
    emitted: set[int] = set()
    for record in [record for record in sample_records if record is not None]:
        found = 0
        for start, end in referenced_ranges(record):
            for pos in range(start, end):
                if pos in emitted:
                    continue
                candidate = plausible_glyph_entry(pos)
                if candidate is None:
                    continue
                emitted.add(pos)
                found += 1
                lines.append(
                    f"| `{record['name']}` @`0x{int(record['record_start']):06x}` | `0x{pos:06x}` | `0x{int(candidate['bitmap']):06x}` | "
                    f"{int(candidate['bitmap_delta'])} | {int(candidate['plane_mode'])} | {int(candidate['height'])} | {int(candidate['width'])} | "
                    f"{int(candidate['render_span'])} | `{bytes(candidate['sample']).hex(' ')}` |"
                )
                if found >= 24:
                    break
            if found >= 24:
                break
    lines.append("")
    lines.append("## Current Interpretation")
    lines.append("")
    lines.append("- The built-in firmware scan begins at address `0x80000`, so an `IC32,IC15` file offset maps to firmware address `0x80000 + offset`.")
    lines.append("- Built-in font candidates set bit 30 in the selected context longword. That selects the `0x1f354` offset-table form, where word `record+8` gives the table delta and each 32-bit table entry is a relative offset from the selected record base.")
    lines.append("- The earlier high-word-only interpretation was wrong: entries such as `0x00007792` in the `COURIER` table resolve to `record_start + 0x7792`, not absolute `0x7792`.")
    lines.append("- This now gives concrete real-glyph fixtures for the renderer harness. For example, the unnamed record at `0x00004c` has context `0x4008004c`; table entry 0 resolves to glyph entry `0x001088`, whose bitmap starts at `0x001092`.")
    lines.append("")
    return "\n".join(lines)


def font_context_bridge_report(data: bytes) -> str:
    def long_refs(value: int) -> list[int]:
        needle = value.to_bytes(4, "big")
        refs: list[int] = []
        start = 0
        while True:
            pos = data.find(needle, start)
            if pos < 0:
                break
            refs.append(pos)
            start = pos + 1
        return refs

    tracked_addresses = [
        (0x007828A0, "selected candidate object pointer source for `0x1e9a0`"),
        (0x007828A8, "selected candidate slot pointer"),
        (0x00782EE6, "primary current font context record"),
        (0x00782EF6, "secondary current font context record"),
        (0x0078297A, "current page-root pointer"),
        (0x00783A2C, "active compact-glyph render context"),
    ]

    lines = ["# IC30/IC13 Font Context Bridge", ""]
    lines.append("This report tracks the current evidence for the bridge from selected font resource candidates to the compact glyph context longword consumed by renderer helper `0x1f354`.")
    lines.append("")

    lines.append("## Confirmed Context Flow")
    lines.append("")
    lines.append("| Step | Address | Code fact | Current meaning |")
    lines.append("| ---: | --- | --- | --- |")
    lines.append("| 1 | `0x1e9a0` | saves `0x78289f`/`0x7821a0`, calls `0x1ae7e`, then loads `A5 = 0x7828a0` | selects a font candidate object under temporary orientation/typeface state |")
    lines.append("| 2 | `0x1e9e6` | `move.l (A5), 0x782ee6` | copies the selected candidate longword into the primary current-font context record |")
    lines.append("| 3 | `0x1e9ec..0x1ea12` | shifts the selected longword by bits 30 and 26 into `0x782eea` and `0x782eeb` | stores context flags adjacent to the primary context longword |")
    lines.append("| 4 | `0x1ea18` | `move.l A5, 0x7828a8` | records the selected candidate slot pointer for later metric/table setup |")
    lines.append("| 5 | `0x144d2` | chooses `0x782ee6` or `0x782ef6` based on `0x7828de`, then copies `(0x7828a8)` into that record | common active-object path updates primary or secondary current-font context records |")
    lines.append("| 6 | `0xc428` | uses helper `0x332ee` with scale `0x10`, adds the result to `0x782ee6`, and treats the result as a current-font context record pointer | entry point for installing primary/secondary font context records into the page root |")
    lines.append("| 7 | `0xc4fc` | scans 16 page-root font slots at `root+0x2c + 4*n`, comparing masked low 24-bit context addresses and `0x78297f+n` live flags | finds an existing slot or the first inactive slot; returns `0x11` if full |")
    lines.append("| 8 | `0xc562..0xc574` | writes `A5` into `root+0x2c + 4*slot` and calls `0x15a6`/`0x15ac` around the update | page-root font slots store pointers to current-font context records, not raw glyph bitmap data |")
    lines.append("| 9 | `0x1edc6` | copies source `+0x2c..+0x68` to render-record `+0x24..+0x60` | page-root font slots become render-record context slots |")
    lines.append("| 10 | `0x1f008` | `move.l (0x24,A6,D0.w), 0x783a2c` | compact glyph object byte `+5` low nibble selects one render-record context slot |")
    lines.append("| 11 | `0x1f354` | tests bit 30 of `0x783a2c`, masks to 24 bits, and resolves the glyph entry | final renderer-side interpretation of the context longword |")
    lines.append("")

    lines.append("## Key Routines")
    lines.append("")
    lines.append("| Routine | Role | Selected instruction facts |")
    lines.append("| --- | --- | --- |")
    lines.append("| `0x14398` | active candidate chooser | walks active list `0x78287c`/`0x7827b8`, chooses a negative/active entry, writes selected slot pointer to `0x7828a8` |")
    lines.append("| `0x1440c` | current font metric/state snapshot | reads `0x7828a8`, masks selected candidate longword to a resource address, and snapshots resource bytes into `0x783148/0x783152` state records |")
    lines.append("| `0x144d2` | primary/secondary context record updater | writes selected candidate longword and bit-derived flags into `0x782ee6` or `0x782ef6` |")
    lines.append("| `0x14c64` | selected font object dispatcher | if no matching active object exists, reads `0x7828a8`, updates font range tables, then calls `0x14d9c`/`0x14e24`/`0x14f16`/`0x1440c` |")
    lines.append("| `0xc428` / `0xc4fc` | current-font context installer | maps the normalized current-font context record selected from the `0x782ee6` family to page-root `+0x2c` slots and keeps slot live flags at `0x78297f+n` |")
    lines.append("| `0x1393a` | text object font-context capture | selects `0x782ee6`/`0x782ef6` using `0x782f06`, copies the current context longword into a text object, and stores the adjacent flag byte at object `+0x10` |")
    lines.append("")

    lines.append("## Absolute Reference Counts")
    lines.append("")
    lines.append("| Address | Role | Reference count | First references |")
    lines.append("| ---: | --- | ---: | --- |")
    for value, role in tracked_addresses:
        refs = long_refs(value)
        first = ", ".join(f"`0x{ref:06x}`" for ref in refs[:8])
        if len(refs) > 8:
            first += ", ..."
        lines.append(f"| `0x{value:08x}` | {role} | {len(refs)} | {first} |")
    lines.append("")

    lines.append("## Current Interpretation")
    lines.append("")
    lines.append("- A render context slot is a pointer to a current-font context record (`0x782ee6` or `0x782ef6` family), whose first longword is the selected candidate/resource longword plus flag bits.")
    lines.append("- Page-root `+0x2c` does not hold raw glyph bitmap pointers. It holds up to 16 current-font context record pointers, which are copied to render-record `+0x24` before compact glyph rendering.")
    lines.append("- For built-in contexts, that bridge is now resolved: the selected context low 24 bits map to an `IC32,IC15` offset by subtracting `0x80000`, bit 30 selects the offset-table form, and table entries are relative 32-bit glyph-entry offsets from the selected record start.")
    lines.append("- The remaining font/text gap is upstream of `0x1f354`: reproduce the primary/secondary character-to-glyph maps at `0x782f32` / `0x783032`, including symbol-set patching, so host bytes feed the same compact glyph index documented in `ic30_ic13_text_glyph_index_flow.md`.")
    lines.append("")
    return "\n".join(lines)


def text_glyph_index_flow_report(firmware: bytes, resources: bytes) -> str:
    routines = [
        (0x0000D4AC, "built-in text metrics/span update"),
        (0x0000D824, "text source object positioning and queue handoff"),
        (0x0000D8FC, "alternate text source object queue handoff"),
        (0x00012F2E, "compact text/glyph bucket producer"),
        (0x0001393A, "character-code to glyph-index capture"),
        (0x00014D9C, "built-in range map initializer"),
        (0x00014E24, "inline/downloaded validity map initializer"),
        (0x00014EB6, "inline/downloaded glyph-validity probe"),
        (0x00014F16, "symbol-set map patcher"),
        (0x0001F354, "renderer glyph/context resolver"),
    ]

    table_refs = [
        (0x00782F06, "primary/secondary text-map selector"),
        (0x00782F32, "primary 256-byte character-to-glyph map"),
        (0x00783032, "secondary 256-byte character-to-glyph map"),
        (0x00782EE6, "primary current-font context record"),
        (0x00782EF6, "secondary current-font context record"),
        (0x00783132, "primary high-character/symbol-set flag"),
        (0x00783133, "secondary high-character/symbol-set flag"),
        (0x00783134, "primary mapped character range"),
        (0x0078313A, "secondary mapped character range"),
        (0x00783144, "primary active symbol-set word"),
        (0x00783146, "secondary active symbol-set word"),
    ]

    def fmt_refs(refs: list[int]) -> str:
        if not refs:
            return "(none)"
        text = ", ".join(f"`0x{ref:06x}`" for ref in refs[:12])
        if len(refs) > 12:
            text += f", ... ({len(refs)} total)"
        return text

    records = firmware_scanned_font_records(resources)
    example_records = [
        next((record for record in records if record["name"] == "(unnamed)" and int(record["record_start"]) == 0x00004C), None),
        next((record for record in records if record["name"] == "COURIER" and int(record["record_start"]) == 0x000418), None),
        next((record for record in records if record["name"] == "LINE_PRINTER" and int(record["record_start"]) == 0x0146B4), None),
    ]

    lines = ["# IC30/IC13 Text Glyph-Index Flow", ""]
    lines.append("Generated from instruction windows around `0x1393a`, `0x12f2e`, and the font-map initializers, plus byte scans of the verified firmware image.")
    lines.append("This report tracks the byte that starts each compact text payload entry and becomes the `D1` glyph index consumed by renderer helper `0x1f354`.")
    lines.append("")

    lines.append("## Confirmed Flow")
    lines.append("")
    lines.append("| Step | Firmware evidence | Meaning for reproduction |")
    lines.append("| ---: | --- | --- |")
    lines.append("| 1 | `0x14c64` dispatches selected font activation through `0x14d9c` for bit-30 built-in contexts, or `0x14e24` for inline/downloaded contexts, then `0x14f16` and `0x1440c` | selected font changes rebuild one of the 256-byte character-to-glyph maps before text is queued |")
    lines.append("| 2 | `0x14d9c` chooses `0x782f32` or `0x783032` from `0x7828de`, reads selected record words `+0x0e` and `+0x10`, zero-fills before/after that range, and writes incrementing bytes through the range | built-in records get a base map where host character `first_char+n` maps to glyph index `n` before symbol-set patching |")
    lines.append("| 3 | `0x14e24` clears/map-fills the same 256-byte table through `0x14eb6`, which validates fixed records at `context_base+0x40+8*glyph` | inline/downloaded contexts use the same map bytes, but only for glyph slots that have valid records |")
    lines.append("| 4 | `0x14f16` applies symbol-set `0x0115` (`8U`, HP Roman-8) handling from `0x783144`/`0x783146`: copy upper 0x80 down for `0x0005` (`0E`, HP Roman Extension), leave lower half for `0x0015` (`0U`, ISO 6 ASCII), or apply named byte-pair patch tables from `0x14fce` | symbol-set aliases are not a renderer concern; they alter the map byte before text object creation |")
    lines.append("| 5 | `0x1393a` selects map/context pair from `0x782f06`: primary `0x782f32` + `0x782ee6`, or secondary `0x783032` + `0x782ef6`; then reads `D6 = byte[map + original_char]` | original host character code is converted to a compact glyph index at text-object build time |")
    lines.append("| 6 | `0x1393a` stores the mapped byte as word at text object `+0x0a`, copies the current context longword to text object `+0`, and copies the context flag byte to text object `+0x10` | text object byte `+0x0b` is the low byte of the mapped glyph index, and the object carries the selected font resource context |")
    lines.append("| 7 | if the context flag byte is nonzero, `0x1393a` range-checks the original character and resolves text object `+4` through the same offset-table formula used by `0x1f354`: base + word `+8`, long table entry indexed by mapped byte, then add base | built-in text objects already point at the concrete resource glyph entry for metrics, proving the mapped byte indexes the same table used by the renderer |")
    lines.append("| 8 | if the context flag byte is zero, `0x1393a` sets text object `+4 = context_base + 0x40 + 8*mapped_byte` | inline/downloaded text objects use the fixed-record layout later handled by `0x1f354` when bit 30 is clear |")
    lines.append("| 9 | the paired queue handoffs `0xd3b2` / `0xd824` fill source positioning fields `+0x12`, `+0x14`, `+0x16`, mark the selected font slot live, then call `0x12f2e`; the paired span updates `0xd4ac` / `0xd8fc` operate on the selected context record afterward | positioned text source objects are converted into compact page-bucket objects, then text span/bounds state is updated separately |")
    lines.append("| 10 | `0x12f2e` appends source byte `+0x0b` as the first byte of every compact payload entry at `0x1302a` and `0x1304e` | compact payload entry byte 0 is the glyph index byte produced by the character map |")
    lines.append("| 11 | compact renderers `0x1f034`, `0x1f0d2`, `0x1f1f0`, and `0x1f264` call `0x1f354` with that byte in `D1` after loading a render-record context slot into `0x783a2c` | renderer glyph selection is fully keyed by `(selected context longword, mapped glyph byte)` |")
    lines.append("")

    lines.append("## Absolute JSR Call-Site Scan")
    lines.append("")
    lines.append("This scan finds `JSR absolute long` opcodes (`4eb9`) that target the named routines. It does not include PC-relative calls.")
    lines.append("")
    lines.append("| Target | Role | Absolute JSR references |")
    lines.append("| ---: | --- | --- |")
    for target, role in routines:
        lines.append(f"| `0x{target:06x}` | {role} | {fmt_refs(jsr_abs_refs(firmware, target))} |")
    lines.append("")

    lines.append("## Table and State References")
    lines.append("")
    lines.append("| Absolute address | Role | Longword literal references |")
    lines.append("| ---: | --- | --- |")
    for address, role in table_refs:
        lines.append(f"| `0x{address:08x}` | {role} | {fmt_refs(find_all(firmware, address.to_bytes(4, 'big')))} |")
    lines.append("")

    lines.append("## Built-In Base-Map Examples")
    lines.append("")
    lines.append("These are the base mappings created by `0x14d9c` before `0x14f16` applies symbol-set patches.")
    lines.append("")
    lines.append("| Context | Record | Character range | Example mapped bytes |")
    lines.append("| ---: | --- | --- | --- |")
    for record in [record for record in example_records if record is not None]:
        first = int(record["first_char"])
        last = int(record["last_char"])
        examples: list[str] = []
        for char in range(first, min(last + 1, first + 4)):
            examples.append(f"`0x{char:02x}->0x{char - first:02x}`")
        lines.append(
            f"| `0x{int(record['context_longword']):08x}` | `{record['name']}` @`0x{int(record['record_start']):06x}` | "
            f"`0x{first:02x}`..`0x{last:02x}` | {', '.join(examples)} |"
        )
    lines.append("")

    lines.append("## Current Reproduction Contract")
    lines.append("")
    lines.append("- To render built-in text exactly, reproduce the firmware's active map table for the selected primary/secondary font slot, including `0x14f16` symbol-set patching.")
    lines.append("- The compact glyph payload byte is not necessarily the original host byte. It is the mapped byte stored at text object `+0x0b` and copied by `0x12f2e`.")
    lines.append("- The renderer-side glyph identity is `(context longword, mapped byte)`. For built-in contexts the context low 24 bits map to `IC32,IC15` offset `address - 0x80000`, bit 30 selects the offset table, and each table entry is a relative 32-bit offset from the record start.")
    lines.append("- The `0x14fce` symbol-set patch tables and their Technical Reference names are decoded in `ic30_ic13_symbol_set_patch_tables.md`; the live host parser path into `0x1393a` is documented in `ic30_ic13_printable_text_path.md`; paired cursor/queue/span paths after `0x1393a` are documented in `ic30_ic13_text_cursor_span_flow.md`; `tools/render_fixture_harness.py` now models a base-map -> `0x1393a` source-object -> `0xd824` positioning -> `0x12f2e` short bucket path for `LINE_PRINTER` host byte `0x21`, includes one-byte and two-byte normal printable stream fixtures for byte `0x21` through source mapping, `0xd550` default cursor advance, positioning, same-bucket queueing, and rendering, renders the initialized `LINE_PRINTER` HMI case where `0x10550(0x00480000)` produces advance `0x00120000` and compact coord `0x0202` / `$a001 = 0x12`, adds a mixed `ESC &k1G!\\r!` fixture where CR+LF positions the second glyph at coord `0x3b00` / `$a001 = 0x1b` and proves full-byte shifted blank-row clearing, queues that same mixed stream through page-record `0x1387c` allocation before bridging it with `0x1edc6`, and adds a mixed `!\\x1bE` fixture where reset publishes and clears a valid current page root after queued text and has the pre-reset object queued/bridged through page-record storage. It also covers the negative-left overflow branch, adds `0x1387c` page-record bucket allocator fixtures for short reuse, full-object new-head allocation, and segmented tall-glyph bucket allocation/reuse, adds a `0x1edc6` page-record bridge fixture for compact bucket/context-slot copying plus rule/fixed-list normalization and producer-shaped `0x13386`/`0x136d2` rule-list objects, adds a selected inline/downloaded map/source fixture through `0x14e24`/`0x14eb6` -> `0x1393a` -> `0xd3b2` -> `0x12f2e` -> render plus `0x168dc`/`0x16942` font payload-reader fixtures, `0x172c0`/`0x16c14` downloaded-font record bookkeeping fixtures, `0x170be`/`0x17108`/`0x17150` record lookup/mark/unmark fixtures, `0x15a56`/`0x16df6` font-id/control dispatch fixtures, and `0x16fae`/`0x17362`/`0x17026`/`0x1719c` validation-table/staged-header/payload-backed inline allocation fixtures, keeps synthetic inline/downloaded records for `0x12f2e` short, page-record short, width-bit, segmented, and combined width+segmented payload shapes, and renders synthetic `0x1f0d2` wide inline, `0x1f1f0` segmented inline, and `0x1f264` segmented-wide inline payload rows, models a segmented `0x2000` producer path for host byte `0x20`, and scans that the firmware-scanned tall built-in targets are mode-0/delta-0 record headers rather than normal bitmap entries. Remaining work is to replace the synthetic allocator/bridge and selected inline fixed-record memory with parser-produced page roots and font-download parser-populated inline/downloaded records, find or construct a real `0x1f1f0` bitmap-entry fixture, broaden row-copy fixtures beyond the current mode-1 built-in examples, and broaden the printable stream fixture into full parser-produced page-object payloads.")
    lines.append("")
    return "\n".join(lines)


def printable_text_path_report(firmware: bytes) -> str:
    routines = [
        (0x0000A904, "raw host byte fetch"),
        (0x0000DA9A, "normal parser byte fetch / ESC wrapper"),
        (0x00011774, "main parser loop"),
        (0x0000D04A, "printable text entry"),
        (0x0001393A, "host byte to text source object"),
        (0x0000D140, "flag-zero text advance/metrics path"),
        (0x0000D550, "built-in/flagged text advance and queue path"),
        (0x0000D824, "positioned source object queue handoff"),
        (0x0000D8FC, "post-advance context span/bounds update path"),
        (0x00012F2E, "compact text/glyph bucket producer"),
    ]

    state_addresses = [
        (0x00782999, "main parser mode/state byte"),
        (0x00782C18, "alternate/data parser mode flag"),
        (0x00782D7E, "printable text source-object scratch buffer"),
        (0x00782F06, "primary/secondary text-map selector"),
        (0x00783132, "primary high-character/symbol-set flag"),
        (0x00783133, "secondary high-character/symbol-set flag"),
        (0x00782A6D, "printable text pending/spacing flag cleared by `0xd04a`"),
        (0x00782A6E, "text clipping/queue precheck result word"),
        (0x00782C8A, "current text cursor x-like coordinate"),
        (0x00782C8E, "current text cursor y-like coordinate"),
        (0x00783184, "text vertical-bounds update enable flag"),
        (0x00783185, "text descent/offset adjustment flag"),
        (0x00783186, "text span low-x flush threshold"),
        (0x00783188, "text span high-x watermark"),
        (0x0078318A, "text span high-y watermark"),
        (0x0078297A, "current page-root pointer"),
        (0x0078297E, "current page-root font slot index"),
        (0x0078297F, "page-root font slot live flags"),
    ]

    def fmt_refs(refs: list[int]) -> str:
        if not refs:
            return "(none)"
        text = ", ".join(f"`0x{ref:06x}`" for ref in refs[:12])
        if len(refs) > 12:
            text += f", ... ({len(refs)} total)"
        return text

    lines = ["# IC30/IC13 Printable Text Path", ""]
    lines.append("Generated from instruction windows around `0x11774`, `0xda9a`, and `0xd04a`, plus absolute-call and state-literal scans of the verified firmware image.")
    lines.append("This report tracks how a normal host printable byte reaches the text source-object builder and, for the flagged built-in path, the compact page-object producer.")
    lines.append("")

    lines.append("## Confirmed Host-Byte Route")
    lines.append("")
    lines.append("| Step | Firmware evidence | Meaning for reproduction |")
    lines.append("| ---: | --- | --- |")
    lines.append("| 1 | `0x11774` initializes its byte-source pointer to `0xda9a`, then repeatedly calls it at `0x117d2` and saves the returned byte in `D5` | the normal PCL parser works from bytes fetched through the `0xda9a` wrapper |")
    lines.append("| 2 | `0xda9a` calls raw byte fetch `0xa904`; if the byte is not ESC (`0x1b`), it returns it directly in `D7` | ordinary printable bytes flow from the host interface to the parser without command-token decoding |")
    lines.append("| 3 | if `0xda9a` sees ESC, it fetches the following byte; `ESC ? 0x11` is skipped, otherwise the following byte is echoed/recorded through `0x9ec0` and `D7` is forced back to `0x1b` | command parsing begins from an ESC token, while printable data remains a single returned byte |")
    lines.append("| 4 | in parser state `0x782999 == 0`, if the command-dispatch table does not claim the byte and alternate/data mode `0x782c18` is clear, the normal printable branch calls `0xd04a` at `0x11880` | unescaped text bytes in the normal parser mode enter the printable text routine |")
    lines.append("| 5 | the high-character/symbol path at `0x118d6..0x11900` also calls `0xd04a` when the selected context flag byte at `0x782eeb + 0x10*0x782f06` equals `1` | some non-ASCII/active-symbol bytes can still route through the same printable text builder |")
    lines.append("| 6 | `0xd04a` uses scratch text source object `0x782d7e`; for bytes above `0xff` it calls `0xd99a` and falls back to `0x7f` on failure | the source-object entry always receives a bounded character code |")
    lines.append("| 7 | for bytes above `0x7f`, if both high-character flags `0x783132` and `0x783133` are clear, `0xd04a` masks the byte to 7 bits; on the primary map it wraps the operation with `0xc6b8` / `0xc68a` | high-bit input can be normalized before character-map lookup, depending on active symbol/font state |")
    lines.append("| 8 | `0xd04a` calls `0x1393a(host_byte, 0x782d7e)` at `0xd0ae` | this is the live parser path into the previously documented host-byte to glyph-index source-object builder |")
    lines.append("| 9 | after `0x1393a`, `0xd04a` tests source byte `+0x10`; zero branches to `0xd140`, nonzero branches to `0xd550`; both paths clear `0x782a6d` before return | source-object context flags select the following text metrics/queue path |")
    lines.append("| 10 | `0xd550` calls `0xd6bc`, updates cursor arithmetic, ensures a page root through `0x10084` when source `+4` is nonzero, and when `0x782a6e == 0` calls `0xd824` at `0xd66e` | the flagged/built-in path has a confirmed pre-advance compact page-object handoff |")
    lines.append("| 11 | `0xd824` writes source words `+0x12` and `+0x14` from current cursor/page geometry, writes source word `+0x16 = byte[0x78297e]`, marks `0x78297f + slot`, and calls `0x12f2e` at `0xd47a`; on allocation failure it marks page-root `+0x15.0`, calls `0xff1e` and `0x10084`, then retries | a live printable source object can become the same compact text/glyph bucket object consumed by the renderer |")
    lines.append("| 12 | after cursor update, `0xd550` calls `0xd8fc((source+0))` at `0xd690` when `0x782a6e == 0`; `0xd8fc` checks context fields `+0x16/+0x18/+0x1a` against current y, page extent `0x782db6`, and span watermarks `0x783186/0x783188/0x78318a`, flushing through `0x12714` / `0x126e2` if the current x falls below the low threshold | the flagged printable path queues through `0xd824` and then updates text span/bounds state through the selected context record |")
    lines.append("| 13 | the fixed-space helper `0xd0f0` calls `0x1393a(0x20, 0x782d7e)`; if the source flag is nonzero it clears source `+4` before entering `0xd550`, otherwise it uses `0xd140` | firmware has a space-specific source-object path that shares the same branch structure but suppresses the built-in glyph-entry pointer in one case |")
    lines.append("")

    lines.append("## Source Object Fields Touched by the Live Path")
    lines.append("")
    lines.append("| Field | Writer | Current interpretation |")
    lines.append("| ---: | --- | --- |")
    lines.append("| `+0x00` | `0x1393a` | selected current-font context longword |")
    lines.append("| `+0x04` | `0x1393a`, `0xd0f0` | built-in glyph-entry pointer or inline fixed-record pointer; `0xd0f0` can clear it before `0xd550` |")
    lines.append("| `+0x0a/+0x0b` | `0x1393a` | mapped compact glyph index word/low byte copied later by `0x12f2e` |")
    lines.append("| `+0x10` | `0x1393a` | context flag byte tested by `0xd04a` to select `0xd140` or `0xd550` |")
    lines.append("| `+0x12` | `0xd824` | x-like positioned source coordinate used by `0x12f2e` |")
    lines.append("| `+0x14` | `0xd824` | y-like positioned source coordinate used by `0x12f2e` |")
    lines.append("| `+0x16` | `0xd824` | page-root/render context slot index copied from `0x78297e` and consumed by `0x12f2e`; this is distinct from context record `+0x16` read by `0xd8fc` |")
    lines.append("")
    lines.append("## Context Record Fields Touched by Span Updates")
    lines.append("")
    lines.append("| Field | Reader | Current interpretation |")
    lines.append("| ---: | --- | --- |")
    lines.append("| `+0x16` | `0xd8fc` | y-like lower bound for flagged/built-in span update |")
    lines.append("| `+0x18` | `0xd8fc` | height/extent contribution checked against page extent `0x782db6` |")
    lines.append("| `+0x1a` | `0xd8fc` | optional offset subtracted from the y watermark when `0x783185` is set |")
    lines.append("| `+0x2b` | `0xd4ac` | optional offset added to the y watermark when `0x783185` is set and nonzero |")
    lines.append("| `+0x2c` | `0xd4ac` | y-like lower bound for unflagged/inline span update |")
    lines.append("| `+0x2d` | `0xd4ac` | height/extent contribution checked against page extent `0x782db6` |")
    lines.append("")

    lines.append("## Absolute JSR Call-Site Scan")
    lines.append("")
    lines.append("This scan finds `JSR absolute long` opcodes (`4eb9`) that target the named routines. It does not include PC-relative calls.")
    lines.append("")
    lines.append("| Target | Role | Absolute JSR references |")
    lines.append("| ---: | --- | --- |")
    for target, role in routines:
        lines.append(f"| `0x{target:06x}` | {role} | {fmt_refs(jsr_abs_refs(firmware, target))} |")
    lines.append("")

    lines.append("## State References")
    lines.append("")
    lines.append("| Absolute address | Role | Longword literal references |")
    lines.append("| ---: | --- | --- |")
    for address, role in state_addresses:
        lines.append(f"| `0x{address:08x}` | {role} | {fmt_refs(find_all(firmware, address.to_bytes(4, 'big')))} |")
    lines.append("")

    lines.append("## Current Reproduction Contract")
    lines.append("")
    lines.append("- A normal printable host byte reaches `0x1393a` through `0xa904` -> `0xda9a` -> `0x11774` -> `0xd04a` when parser state `0x782999` is zero and alternate/data parser mode `0x782c18` is clear.")
    lines.append("- The live parser path uses the same mapped glyph byte and context fields documented in `ic30_ic13_text_glyph_index_flow.md`; the next byte-to-pixel model must therefore drive `0xd04a`/`0x1393a`, not feed renderer glyph bytes directly from the host stream.")
    lines.append("- The paired cursor/queue/span behavior after `0x1393a` is detailed in `ic30_ic13_text_cursor_span_flow.md`; `tools/render_fixture_harness.py` now has one-byte and two-byte normal printable stream fixtures for `0x21` -> glyph `0x20` through `0xd824`, the simple `0xd550` default-advance branch, `0x12f2e`, and rendering. It also renders the initialized `LINE_PRINTER` HMI case, where `0x10550(0x00480000)` produces advance `0x00120000` and the second glyph compact coord `0x0202` decodes to `$a001 = 0x12` / pixel x `34`. The mixed `ESC &k1G!\\r!` fixture now proves that line-termination mode is applied before the second printable byte is positioned, queueing it at coord `0x3b00` after CR+LF; the same stream now has a page-record variant that allocates/reuses the compact object through `0x1387c` and bridges it through `0x1edc6`; the mixed `!\\x1bE` fixture proves reset publication/clear state after queued text and has a page-record allocator/bridge variant for the pre-reset object. The `0x1387c` allocator fixture now queues a short compact object into page-record bucket-array shape and covers the segmented tall-glyph page-record bucket sequence, and the `0x1edc6` bridge fixture proves how that compact bucket and context slot are copied into the render record. The remaining integration gap is to replace fixture-only state with real parser-produced page objects before replacing the current producer-modeled text bucket fixtures.")
    lines.append("")
    return "\n".join(lines)


def text_cursor_span_report(firmware: bytes) -> str:
    routines = [
        (0x0000D140, "unflagged/inline text advance entry"),
        (0x0000D28A, "unflagged text bounds precheck"),
        (0x0000D3B2, "unflagged positioned source queue handoff"),
        (0x0000D4AC, "unflagged text span/bounds update"),
        (0x0000D550, "flagged/built-in text advance entry"),
        (0x0000D6BC, "flagged text bounds precheck"),
        (0x0000D824, "flagged positioned source queue handoff"),
        (0x0000D8FC, "flagged text span/bounds update"),
        (0x00010510, "fixed-point compare/subtract helper"),
        (0x00010518, "fixed-point add helper"),
        (0x00010550, "fixed-point metric conversion helper"),
        (0x0000F054, "conditional page/text state recovery helper"),
        (0x00010084, "ensure page root"),
        (0x000126E2, "post-flush text state reset/update"),
        (0x00012714, "pending text span flush"),
        (0x00012F2E, "compact text/glyph bucket producer"),
    ]

    state_addresses = [
        (0x0078297A, "current page-root pointer"),
        (0x0078297E, "current page-root font slot index"),
        (0x0078297F, "page-root font slot live flags"),
        (0x00782A58, "text pending-width latch flag"),
        (0x00782A5A, "latched previous text width"),
        (0x00782A5C, "latched previous text advance"),
        (0x00782A6E, "text precheck result word"),
        (0x00782C8A, "current text cursor x-like coordinate"),
        (0x00782C8E, "current text cursor y-like coordinate"),
        (0x00782DA3, "orientation byte"),
        (0x00782DB2, "orientation/page extent used by positioned text"),
        (0x00782DB6, "page vertical extent for text bounds"),
        (0x00782DB8, "page horizontal extent for text wrap/clip"),
        (0x00782DC0, "top/left printable offset used by text queue handoff"),
        (0x00782DDA, "fixed-point current line/text limit"),
        (0x0078315C, "default text advance"),
        (0x00783184, "text vertical-bounds update enable flag"),
        (0x00783185, "text descent/offset adjustment flag"),
        (0x00783186, "text span low-x flush threshold"),
        (0x00783188, "text span high-x watermark"),
        (0x0078318A, "text span high-y watermark"),
        (0x0078318E, "alternate metrics/kerning mode flag"),
        (0x00783190, "text auto-recovery/clip retry flag"),
    ]

    def fmt_refs(refs: list[int]) -> str:
        if not refs:
            return "(none)"
        text = ", ".join(f"`0x{ref:06x}`" for ref in refs[:12])
        if len(refs) > 12:
            text += f", ... ({len(refs)} total)"
        return text

    lines = ["# IC30/IC13 Text Cursor and Span Flow", ""]
    lines.append("Generated from the printable-text window around `0xd140..0xd8fc` plus absolute-call and state-literal scans of the verified firmware image.")
    lines.append("This report narrows the text reproduction boundary after `0x1393a`: how source-object metrics advance the text cursor, produce compact page buckets, and update text span watermarks.")
    lines.append("")

    lines.append("## Paired Text Paths")
    lines.append("")
    lines.append("| Path | Entry | Precheck | Queue handoff | Span/bounds update | Current role |")
    lines.append("| --- | ---: | ---: | ---: | ---: | --- |")
    lines.append("| unflagged / inline | `0xd140` | `0xd28a` | `0xd3b2` | `0xd4ac` | used when source object byte `+0x10` is clear |")
    lines.append("| flagged / built-in | `0xd550` | `0xd6bc` | `0xd824` | `0xd8fc` | used when source object byte `+0x10` is nonzero |")
    lines.append("")

    lines.append("## Confirmed Arithmetic and Side Effects")
    lines.append("")
    lines.append("| Step | Firmware evidence | Reproduction meaning |")
    lines.append("| ---: | --- | --- |")
    lines.append("| 1 | Both `0xd140` and `0xd550` call a path-specific precheck (`0xd28a` or `0xd6bc`) and store its result in `0x782a6e` | a nonzero precheck suppresses queue and span-update side effects for the current character |")
    lines.append("| 2 | Both entries seed `D5` from current cursor `0x782c8a` and derive an advance `D4` either from the active text metrics, from the latched previous width/advance pair `0x782a5a/0x782a5c`, or from default advance `0x78315c` | horizontal cursor movement is metric-driven, with special centering/kerning behavior when `0x78318e` and `0x782a58` are active |")
    lines.append("| 3 | When `0x782a58` is set, both entries add half of `(latched_width - current_width)` to `0x782c8a`, rounding the arithmetic right shift toward zero for odd negative deltas | repeated text can be centered against the previous character width before the main advance is applied |")
    lines.append("| 4 | Both entries add `D4` to cursor `D5`, then if the low 16 bits are `>= 12`, subtract `12` from `D5` | text cursor coordinates use a 12-subunit fixed-point-like residue; crossing the residue boundary normalizes the whole cursor value |")
    lines.append("| 5 | If the source has drawable content (`source+4` nonzero for `0xd550`, source word `+0x0a` nonzero for `0xd140`), the code ensures page root `0x78297a` through `0x10084` before queueing | printable text only allocates compact page objects when a drawable source record/glyph word is present |")
    lines.append("| 6 | If `0x782a6e == 0`, `0xd140` calls `0xd3b2` and `0xd550` calls `0xd824`; each handoff writes source `+0x12/+0x14/+0x16`, marks `0x78297f + slot`, and calls `0x12f2e`, retrying via `0xff1e` / `0x10084` on allocation failure | both source-object classes converge into the same compact text bucket producer |")
    lines.append("| 7 | `0xd3b2` handles unflagged source positioning with byte metrics at source record `+1/+2` and the context-record byte at context `+0x16`; `0xd824` handles flagged source positioning with word metrics at source record `+0/+2` | the two paths use different source-record layouts before producing the same `0x12f2e` source coordinate fields |")
    lines.append("| 8 | Both handoffs account for negative left overflow by returning a fixed-point correction in `D7`; the caller adds that value back into the local cursor candidate before repeating limit checks | clipped-left text changes the queued source coordinate and the cursor update together |")
    lines.append("| 9 | After final cursor clamping, both entries write `0x782c8a = D5` and clear `0x782a58` | the text cursor is committed only after queue/limit handling has stabilized |")
    lines.append("| 10 | If `0x782a6e == 0`, `0xd140` calls `0xd4ac((source+0))` and `0xd550` calls `0xd8fc((source+0))`; both check the current y coordinate against context-record lower-bound/height fields and `0x782db6`, update `0x78318a` and `0x783188`, and flush through `0x12714` / `0x126e2` when current x is below `0x783186` | span/bounds state is maintained from the selected context record after successful printable text placement and can force pending span emission |")
    lines.append("")

    lines.append("## Source Field Use")
    lines.append("")
    lines.append("| Field | Unflagged path | Flagged path |")
    lines.append("| ---: | --- | --- |")
    lines.append("| `+0x00` | context pointer; `0xd3b2` reads context byte `+0x16` | context pointer; `0xd824` does not test context byte `+0x16` |")
    lines.append("| `+0x04` | inline/fixed source record pointer used by `0xd140`, `0xd28a`, and `0xd3b2` | concrete built-in glyph-entry pointer used by `0xd550`, `0xd6bc`, and `0xd824` |")
    lines.append("| `+0x08` | signed horizontal offset/advance contribution used by `0xd3b2` | signed horizontal offset/advance contribution used by `0xd824` |")
    lines.append("| `+0x0a/+0x0b` | glyph index word/byte; word zero suppresses page-root allocation in `0xd140` | glyph index word/byte; copied by `0x12f2e` after `0xd824` |")
    lines.append("| `+0x12` | written by `0xd3b2` as the x-like source coordinate | written by `0xd824` as the x-like source coordinate |")
    lines.append("| `+0x14` | written by `0xd3b2` as the y-like source coordinate | written by `0xd824` as the y-like source coordinate |")
    lines.append("| `+0x16` | written by `0xd3b2` as context slot for `0x12f2e` | written by `0xd824` as context slot for `0x12f2e` |")
    lines.append("")

    lines.append("## Context Record Field Use")
    lines.append("")
    lines.append("The span-update calls pass `(source+0)`, not the source object itself, so these fields belong to the selected context record.")
    lines.append("")
    lines.append("| Context field | Reader | Current interpretation |")
    lines.append("| ---: | --- | --- |")
    lines.append("| `+0x16` | `0xd8fc` | y-like lower bound for flagged/built-in span update |")
    lines.append("| `+0x18` | `0xd8fc` | height/extent contribution checked against page extent `0x782db6` |")
    lines.append("| `+0x1a` | `0xd8fc` | optional offset subtracted from y watermark when `0x783185` is set |")
    lines.append("| `+0x2b` | `0xd4ac` | optional offset added to y watermark when `0x783185` is set and nonzero |")
    lines.append("| `+0x2c` | `0xd4ac` | y-like lower bound for unflagged/inline span update |")
    lines.append("| `+0x2d` | `0xd4ac` | height/extent contribution checked against page extent `0x782db6` |")
    lines.append("")

    lines.append("## Absolute JSR Call-Site Scan")
    lines.append("")
    lines.append("This scan finds `JSR absolute long` opcodes (`4eb9`) that target the named routines. It does not include PC-relative calls.")
    lines.append("")
    lines.append("| Target | Role | Absolute JSR references |")
    lines.append("| ---: | --- | --- |")
    for target, role in routines:
        lines.append(f"| `0x{target:06x}` | {role} | {fmt_refs(jsr_abs_refs(firmware, target))} |")
    lines.append("")

    lines.append("## State References")
    lines.append("")
    lines.append("| Absolute address | Role | Longword literal references |")
    lines.append("| ---: | --- | --- |")
    for address, role in state_addresses:
        lines.append(f"| `0x{address:08x}` | {role} | {fmt_refs(find_all(firmware, address.to_bytes(4, 'big')))} |")
    lines.append("")

    lines.append("## Current Reproduction Contract")
    lines.append("")
    lines.append("- A faithful text model must run the active source object through the same paired path selected by source byte `+0x10`; feeding `0x12f2e` directly is only a producer-level fixture.")
    lines.append("- The cursor `0x782c8a` is updated after path-specific metric extraction, fixed-point residue normalization by 12 subunits, optional left/right clipping correction, and queue retry handling.")
    lines.append("- The compact text bucket payload still depends on the mapped glyph byte from `0x1393a`, but exact pixel placement also depends on source fields `+0x12/+0x14/+0x16` produced by `0xd3b2` or `0xd824` and on context-record span flush side effects in `0xd4ac` / `0xd8fc`.")
    lines.append("- The flagged `0xd824` positioning path, including the negative-left overflow branch, has executable queue/render fixtures in `tools/render_fixture_harness.py`, and printable stream fixtures now carry host byte `0x21` through `0x1393a`, `0xd824`, the simple `0xd550` default-advance branch for a second byte, `0x12f2e`, and rendering. The initialized `LINE_PRINTER` HMI case renders through the same path and proves compact coord `0x0202` as `$a001 = 0x12` / pixel x `34`; the mixed `ESC &k1G!\\r!` case proves CR+LF repositioning before the second printable byte, exposes full-byte shifted blank-row clearing, and now has a page-record allocator/bridge variant for the same byte stream; the mixed `!\\x1bE` case proves reset publication/clear state after queued text and now has a page-record allocator/bridge variant for the pre-reset object. A `0x1387c` fixture queues short and segmented compact buckets into page-record shape, and a `0x1edc6` fixture bridges that compact bucket into render-record shape, pins rule/fixed-list normalization, and now includes producer-shaped `0x13386`/`0x136d2` rule-list objects. The `0xd3b2` fixtures now cover both unflagged positioning branches, a selected inline/downloaded map/source path through `0x14e24`/`0x14eb6` -> `0x1393a`, `0x168dc`/`0x16942` font payload-reader copying and continuation, `0x172c0` current-record scanning, `0x16c14` replacement/free-slot/no-slot bookkeeping, `0x170be` payload-record lookup, `0x17108`/`0x17150` current-record mark/unmark count transfer, `0x15a56`/`0x16df6` font-id/control dispatch, `0x16fae` validation-table and symbol-byte staging, `0x17362` setup-type handling, `0x17026` allocation-size/header staging, `0x1719c` sparse header initialization, synthetic inline/downloaded `0x12f2e` short/page-record/wide/segmented/combined payloads, and synthetic `0x1f0d2` wide inline, `0x1f1f0` segmented inline, and `0x1f264` segmented-wide inline render rows. Remaining work is to use real parser-produced source/page objects and name the coordinate axes by comparing orientation, CR/LF/FF, and raster placement behavior.")
    lines.append("")
    return "\n".join(lines)


def active_symbol_set_flow_report(data: bytes) -> str:
    routines = [
        (0x000120BE, "symbol-set terminal wrapper"),
        (0x0001BE22, "PCL symbol-set word handler"),
        (0x00017708, "primary/secondary font ID selection"),
        (0x0001AC0A, "default-font command symbol table builder"),
        (0x0001AF36, "font-selection fallback symbol table builder"),
        (0x0001B04C, "default/fallback symbol table refresh wrapper"),
        (0x0000C580, "common font/symbol update refresh"),
        (0x00013EB8, "selected font/object refresh from common updater"),
        (0x0000C428, "current-font context installer"),
        (0x000156DE, "font candidate filter against requested symbol set"),
        (0x00015850, "requested symbol-set normalizer"),
        (0x00015890, "built-in candidate symbol-set reader"),
        (0x000158BE, "inline/downloaded candidate symbol-set reader"),
        (0x00014F16, "active character-map symbol patcher"),
    ]

    state_addresses = [
        (0x0078299A, "parser continuation handler pointer"),
        (0x0078299E, "parser command-record stack pointer"),
        (0x00782EF4, "primary requested symbol-set word"),
        (0x00782F04, "secondary requested symbol-set word"),
        (0x0078289E, "temporary primary/secondary default-font slot selector"),
        (0x0078289F, "temporary orientation/font-list selector"),
        (0x007828A0, "temporary or selected candidate-list pointer"),
        (0x007828A4, "candidate/default symbol-set word scratch"),
        (0x007828A8, "selected candidate slot pointer"),
        (0x00783144, "primary active selected symbol-set word"),
        (0x00783146, "secondary active selected symbol-set word"),
        (0x00782F08, "primary remembered active symbol-set fallback"),
        (0x00782F0A, "secondary remembered active symbol-set fallback"),
        (0x00782F0C, "font-selection fallback symbol table: orientation 0 primary"),
        (0x00782F10, "font-selection fallback symbol table: orientation 0 secondary"),
        (0x00782F14, "font-selection fallback symbol table: orientation 1 primary"),
        (0x00782F18, "font-selection fallback symbol table: orientation 1 secondary"),
        (0x00782F1C, "`@0`/`@1` default-font table: orientation 0 primary"),
        (0x00782F20, "`@0`/`@1` default-font table: orientation 0 secondary"),
        (0x00782F24, "`@0`/`@1` default-font table: orientation 1 primary"),
        (0x00782F28, "`@0`/`@1` default-font table: orientation 1 secondary"),
        (0x00782F2C, "font/symbol update dirty flag"),
        (0x00782F2D, "font/symbol update in-progress flag"),
        (0x00782F06, "primary/secondary selected text slot"),
        (0x007828DE, "font-selection slot currently being rebuilt"),
    ]

    def fmt_refs(refs: list[int], limit: int = 10) -> str:
        if not refs:
            return "(none)"
        text = ", ".join(f"`0x{ref:06x}`" for ref in refs[:limit])
        if len(refs) > limit:
            text += f", ... ({len(refs)} total)"
        return text

    compat_pairs: list[tuple[int, int]] = []
    for pos in range(0x15840, 0x1584C, 4):
        compat_pairs.append((u16(data, pos), u16(data, pos + 2)))

    def dispatch_table(table: int) -> tuple[list[tuple[int, int]], int]:
        entries: list[tuple[int, int]] = []
        pos = table
        while True:
            target = u32(data, pos)
            pos += 4
            if target == 0:
                return entries, u32(data, pos)
            match = u32(data, pos)
            pos += 4
            entries.append((match, target))

    final_entries, final_default = dispatch_table(0x1BE0A)
    at_entries, at_default = dispatch_table(0x1BDE2)

    normal_examples = [
        (0, ord("U"), 0x0015, "0U"),
        (8, ord("U"), 0x0115, "8U"),
        (0, ord("E"), 0x0005, "0E"),
        (2, ord("U"), 0x0055, "2U"),
    ]

    lines = ["# IC30/IC13 Active Symbol-Set Flow", ""]
    lines.append("Generated from focused firmware windows around the PCL parser, symbol-set handler `0x1be22`, common font refresh `0xc580`, and font candidate activation `0x156de`.")
    lines.append("This report tracks how host commands such as `ESC (8U` and `ESC )0B` become the active symbol-set words that rebuild the primary/secondary character-to-glyph maps.")
    lines.append("")

    lines.append("## Parser Entry Points")
    lines.append("")
    lines.append("| Host command family | Setup handler | Slot setup evidence | Terminal dispatch |")
    lines.append("| --- | ---: | --- | --- |")
    lines.append("| `ESC (` primary font-designation family | `0x1201e` | calls `0x11f26`, which pushes parser record byte `0x80` and word `0` | final bytes `@`..`^` dispatch to `0x120be` |")
    lines.append("| `ESC )` secondary font-designation family | `0x12008` | calls `0x11efe`, which pushes parser record byte `0x80` and word `1` | final bytes `@`..`^` dispatch to `0x120be` |")
    lines.append("| terminal wrapper | `0x120be` | calls `0x1be22`, then common refresh `0xc580` | shared path for normal symbol-set selection, `X` font-ID selection, and `@` default/table variants |")
    lines.append("")

    lines.append("## Symbol-Set Word Construction")
    lines.append("")
    lines.append("Routine `0x1be22` pops the parsed command record, reads the final byte into `D3`, reads the numeric parameter into `D5`, and reads the slot word into `D4`. For ordinary symbol-set final letters, it computes:")
    lines.append("")
    lines.append("```text")
    lines.append("symbol_word = (abs(parameter) << 5) + final_byte - 0x40")
    lines.append("requested_slot = 0x782ef4 + 0x10 * slot")
    lines.append("word[requested_slot] = symbol_word")
    lines.append("```")
    lines.append("")
    lines.append("The `0x10 * slot` stride makes `0x782ef4` the primary requested symbol-set word and `0x782f04` the secondary requested symbol-set word. This matches PCL's symbol-set notation: the number is the high component and `A..Z` maps to suffix values `1..26`.")
    lines.append("")
    lines.append("| PCL code | Parameter | Final byte | Computed word | Manual name in current table |")
    lines.append("| --- | ---: | ---: | ---: | --- |")
    for parameter, final_byte, expected, label in normal_examples:
        computed = (parameter << 5) + final_byte - 0x40
        lines.append(f"| `{label}` | `{parameter}` | `0x{final_byte:02x}` | `0x{computed:04x}` | {symbol_set_name(expected)} |")
    lines.append("")
    lines.append("The computed word is intentionally provisional for two final-byte cases. Final `X` restores the previous requested symbol word and selects a font by ID. Final `@` runs a numeric sub-dispatch whose documented `3@` case selects default font characteristics.")
    lines.append("")

    lines.append("## Final-Byte Special Cases")
    lines.append("")
    lines.append("The common dispatch helper `0x33298` reads `{target, match}` longword pairs until a zero target, then jumps to the default target that follows. The final-byte table at `0x1be0a` decodes as:")
    lines.append("")
    lines.append("| Match | Target | Firmware effect |")
    lines.append("| ---: | ---: | --- |")
    final_descriptions = {
        0x58: "final `X`: restore the saved requested symbol word, set `0x78287b`, call `0x17708(slot, parameter)` for font-ID selection, then set dirty flag `0x782f2c = 2` and `0x782f2d = 1`",
        0x40: "final `@`: dispatch the numeric parameter through table `0x1bde2`",
    }
    for match, target in final_entries:
        lines.append(f"| `0x{match:02x}` | `0x{target:06x}` | {final_descriptions.get(match, '(unidentified)')} |")
    lines.append(f"| default | `0x{final_default:06x}` | mark `0x782f2c`/`0x782f2d` dirty using the requested symbol word already stored at `0x782ef4 + 0x10*slot` |")
    lines.append("")

    lines.append("The final `@` numeric table at `0x1bde2` decodes as:")
    lines.append("")
    lines.append("| Parameter | Target | Firmware effect |")
    lines.append("| ---: | ---: | --- |")
    at_descriptions = {
        0: "set requested word from `0x782f1c + 8*orientation + 4*slot`, then mark maps dirty",
        1: "set requested word from `0x782f1c + 8*orientation`, ignoring the primary/secondary slot offset, then mark maps dirty",
        2: "for primary slot, restore the old requested word; for secondary slot, copy primary requested word `0x782ef4`; then mark maps dirty",
        3: "default-font path: use `0x1b250`/`0x1ad66` to find or synthesize a candidate, temporarily install `0x7828a4` as the active symbol word for the slot, call `0x1b2fe`, restore the previous active/context state, then mark maps dirty",
    }
    for match, target in at_entries:
        lines.append(f"| `{match}` | `0x{target:06x}` | {at_descriptions.get(match, '(unidentified)')} |")
    lines.append(f"| default | `0x{at_default:06x}` | restore the old requested word and return without setting the dirty flags |")
    lines.append("")

    lines.append("## Default and Fallback Symbol Tables")
    lines.append("")
    lines.append("The LaserJet II Technical Reference documents `ESC (3@` / `ESC )3@` as the Default Font command and states that it sets all font characteristics except orientation to the user default font. The same manual text does not name `@0`, `@1`, or `@2`; the behavior below is therefore firmware-derived.")
    lines.append("")
    lines.append("| Table | Builder | Consumer | Layout | Firmware meaning |")
    lines.append("| --- | ---: | ---: | --- | --- |")
    lines.append("| `0x782f0c`, `0x782f10`, `0x782f14`, `0x782f18` | `0x1af36` | `0x156de` fallback at `0x1577e` | orientation 0 primary, orientation 0 secondary, orientation 1 primary, orientation 1 secondary | candidate-selection fallback words used after remembered active words `0x782f08`/`0x782f0a` do not satisfy current selection |")
    lines.append("| `0x782f1c`, `0x782f20`, `0x782f24`, `0x782f28` | `0x1ac0a` | `0x1be22` final-`@` table | same four-entry orientation/slot layout | default-font command words used by `@0` and `@1`; `@3` uses the candidate found by `0x1b250`/`0x1ad66` more directly |")
    lines.append("")
    lines.append("When `0x1b250` finds a current default candidate, `0x1ac0a` clones its scratch word `0x7828a4` into all four `0x782f1c..0x782f28` entries. Otherwise it toggles temporary orientation/list selectors `0x78289f` and `0x78289e`, calls `0x1ab84`, and records one word per orientation/slot. `0x1af36` performs the parallel setup for the `0x782f0c..0x782f18` fallback table using `0x1ad66`.")
    lines.append("")

    lines.append("## Refresh and Active Selection")
    lines.append("")
    lines.append("| Step | Firmware evidence | Reproduction meaning |")
    lines.append("| ---: | --- | --- |")
    lines.append("| 1 | `0x1be22` writes the requested word into `0x782ef4 + 0x10*slot` and marks `0x782f2c`/`0x782f2d` | host symbol-set command changes the requested font-selection criteria, not just a renderer flag |")
    lines.append("| 2 | `0x120be` immediately calls `0xc580` | symbol-set commands run the same common refresh used by other font-selection commands |")
    lines.append("| 3 | `0xc580` reads the slot from the parser record, checks dirty flag `0x782f2c`, and calls `0x13eb8` and/or `0xc428` depending on current slot state | requested symbol-set changes can rebuild selected font context and reinstall it into page-root font slots |")
    lines.append("| 4 | `0x156de` reads `0x782ef4` for primary or `0x782f04` for secondary, normalizes it through `0x15850`, and scans the active candidate list | the requested PCL word becomes the filter key for built-in/downloaded font candidates |")
    lines.append("| 5 | `0x156de` writes the selected active word to `0x783144` for primary or `0x783146` for secondary after fallback/default handling | these are the active words consumed later by character-map setup |")
    lines.append("| 6 | `0x1440c` snapshots `0x783144`/`0x783146` into selected-font state records at `0x783148`/`0x783152` offset `+4` | active object comparison can reject cached state when the symbol set changes |")
    lines.append("| 7 | `0x14f16` reads `0x783144` or `0x783146` after base map initialization | Roman-8 built-in maps are patched according to the active requested symbol set before text objects are queued |")
    lines.append("| 8 | `0xc580` and the orientation handler `0x10220` copy active words into `0x782f08`/`0x782f0a` | these remembered values are fallback/default inputs if current candidate selection cannot satisfy the requested word |")
    lines.append("")

    lines.append("## Compatibility Pair Table")
    lines.append("")
    lines.append("At `0x15742`, candidate symbol word `D7` is swapped into the high word and requested symbol word `D3` is copied into the low word, then compared against longwords at `0x15840`. These pairs allow a candidate with one symbol-set word to satisfy a related requested word.")
    lines.append("")
    lines.append("| Entry | Candidate word | Candidate code | Requested word | Requested code |")
    lines.append("| ---: | ---: | --- | ---: | --- |")
    for index, (candidate, requested) in enumerate(compat_pairs):
        lines.append(f"| {index} | `0x{candidate:04x}` | `{pcl_symbol_set_code(candidate)}` | `0x{requested:04x}` | `{pcl_symbol_set_code(requested)}` |")
    lines.append("")

    lines.append("## Absolute JSR Call-Site Scan")
    lines.append("")
    lines.append("| Target | Role | Absolute JSR references |")
    lines.append("| ---: | --- | --- |")
    for target, role in routines:
        lines.append(f"| `0x{target:06x}` | {role} | {fmt_refs(jsr_abs_refs(data, target))} |")
    lines.append("")

    lines.append("## State Address References")
    lines.append("")
    lines.append("| Address | Role | Longword literal references |")
    lines.append("| ---: | --- | --- |")
    for address, role in state_addresses:
        lines.append(f"| `0x{address:08x}` | {role} | {fmt_refs(find_all(data, address.to_bytes(4, 'big')))} |")
    lines.append("")

    lines.append("## Current Reproduction Contract")
    lines.append("")
    lines.append("- Parse primary `ESC (` and secondary `ESC )` symbol-set commands into PCL words with `(number << 5) + suffix`, where suffix `A..Z` is `1..26`, except for final `X` and `@` special cases.")
    lines.append("- Treat `ESC (#X` / `ESC )#X` as font-ID selection through `0x17708`; it restores the prior requested symbol word rather than accepting the provisional `X` symbol word.")
    lines.append("- Treat `ESC (3@` / `ESC )3@` as default-font selection; the firmware also implements `@` parameters `0..2` as table/copy variants documented above.")
    lines.append("- Treat `0x782ef4`/`0x782f04` as requested criteria and `0x783144`/`0x783146` as the active post-selection words.")
    lines.append("- Rebuild the selected primary/secondary character-to-glyph map after symbol-set changes, then apply the `0x14f16` patch rules documented in `ic30_ic13_symbol_set_patch_tables.md`.")
    lines.append("- Do not feed host bytes directly to `0x1f354`; the queued compact glyph byte must come from the active map selected by this flow.")
    lines.append("")
    return "\n".join(lines)


def symbol_set_patch_table_report(data: bytes) -> str:
    table = 0x14FCE
    entry_count = 18

    def patch_pairs(pointer: int) -> list[tuple[int, int]]:
        if pointer < 0 or pointer + 2 > len(data):
            return []
        count = u16(data, pointer)
        pairs: list[tuple[int, int]] = []
        pos = pointer + 2
        for _ in range(count):
            if pos + 2 > len(data):
                break
            pairs.append((data[pos], data[pos + 1]))
            pos += 2
        return pairs

    entries: list[dict[str, int | list[tuple[int, int]]]] = []
    for index in range(entry_count):
        pos = table + index * 6
        symbol_value = u16(data, pos)
        pointer = u32(data, pos + 2)
        entries.append({"index": index, "symbol_value": symbol_value, "pointer": pointer, "pairs": patch_pairs(pointer)})

    lines = ["# IC30/IC13 Symbol-Set Patch Tables", ""]
    lines.append("Generated from the data table rooted at `0x14fce`, consumed by `0x14f16` after built-in font map initialization.")
    lines.append("")
    lines.append("Symbol-set names are from the LaserJet Series II Technical Reference, Table 8-1 / Table 10-2. Routine `0x14f16` only enters this path when the selected font normalizes to symbol set `0x0115` (`8U`, HP Roman-8). It then reads the active requested symbol-set word from `0x783144` or `0x783146` and handles it as follows:")
    lines.append("")
    lines.append("- `0x0005` (`0E`, HP Roman Extension): copy the upper 128 map bytes down over the lower 128 bytes, then clear the upper 128 bytes.")
    lines.append("- `0x0015` (`0U`, ISO 6: ASCII): leave the lower map half alone, clear the upper 128 bytes.")
    lines.append("- table hit at `0x14fce`: apply byte pairs from the selected patch table, then clear the upper 128 bytes.")
    lines.append("- no table hit: leave the map as initialized by `0x14d9c`/`0x14e24`.")
    lines.append("")
    lines.append("Each patch pair is interpreted by `0x14fa0..0x14fa4` as `map[dst] = map[src]`. This remaps host character `dst` to the glyph index that the active map had for character `src`.")
    lines.append("")

    lines.append("## Patch Table Index")
    lines.append("")
    lines.append("| Entry | Symbol value | PCL code | Manual name | Patch table | Pair count |")
    lines.append("| ---: | ---: | --- | --- | ---: | ---: |")
    for entry in entries:
        symbol_value = int(entry["symbol_value"])
        pointer = int(entry["pointer"])
        pairs = entry["pairs"]
        assert isinstance(pairs, list)
        lines.append(f"| {int(entry['index'])} | `0x{symbol_value:04x}` | `{pcl_symbol_set_code(symbol_value)}` | {symbol_set_name(symbol_value)} | `0x{pointer:06x}` | {len(pairs)} |")
    lines.append("")

    lines.append("## Patch Pair Details")
    lines.append("")
    for entry in entries:
        symbol_value = int(entry["symbol_value"])
        pointer = int(entry["pointer"])
        pairs = entry["pairs"]
        assert isinstance(pairs, list)
        lines.append(f"### `{pcl_symbol_set_code(symbol_value)}` (`0x{symbol_value:04x}`), {symbol_set_name(symbol_value)} @`0x{pointer:06x}`")
        lines.append("")
        lines.append("| Pair | Destination char | Source char | Effect |")
        lines.append("| ---: | ---: | ---: | --- |")
        for pair_index, (dst, src) in enumerate(pairs):
            lines.append(f"| {pair_index} | `0x{dst:02x}` | `0x{src:02x}` | `map[0x{dst:02x}] = map[0x{src:02x}]` |")
        lines.append("")

    lines.append("## Example Effects on Built-In Base Maps")
    lines.append("")
    lines.append("For the first `COURIER` and `LINE_PRINTER` records, the pre-patch base range is `0x01..0xff`, so `map[x] = x - 1` for nonzero bytes. Under that base map, a pair `dst,src` makes host byte `dst` select glyph index `src - 1`.")
    lines.append("")
    lines.append("| Symbol | Manual name | First four remaps under `0x01..0xff` base |")
    lines.append("| --- | --- | --- |")
    for entry in entries:
        symbol_value = int(entry["symbol_value"])
        pairs = entry["pairs"]
        assert isinstance(pairs, list)
        examples: list[str] = []
        for dst, src in pairs[:4]:
            glyph = 0 if src == 0 else src - 1
            examples.append(f"`0x{dst:02x}->glyph 0x{glyph:02x}`")
        lines.append(f"| `{pcl_symbol_set_code(symbol_value)}` | {symbol_set_name(symbol_value)} | {', '.join(examples) if examples else '(none)'} |")
    lines.append("")
    return "\n".join(lines)


def scan_signature_report(firmware: bytes, resources: bytes) -> str:
    signatures = {
        "PROG": b"PROG",
        "HEAD": b"HEAD",
        "ESC_byte": b"\x1b",
        "form_feed_byte": b"\x0c",
    }
    lines = ["# Firmware and Resource Signature Scan", ""]
    for image_name, data in (("IC30/IC13 firmware", firmware), ("IC32/IC15 resources", resources)):
        lines.append(f"## {image_name}")
        lines.append("")
        for label, sig in signatures.items():
            offsets: list[int] = []
            start = 0
            while True:
                pos = data.find(sig, start)
                if pos < 0:
                    break
                offsets.append(pos)
                start = pos + 1
            shown = ", ".join(f"`0x{off:06x}`" for off in offsets[:32])
            if len(offsets) > 32:
                shown += f", ... ({len(offsets)} total)"
            lines.append(f"- `{label}`: {shown if shown else '(none)'}")
        lines.append("")
    return "\n".join(lines)


def categorized_long_references(data: bytes) -> str:
    categories = {
        "low_mmio_or_vectors": lambda v: 0x00008000 <= v <= 0x0000ffff,
        "option_space": lambda v: v in (0x00200000, 0x00400000),
        "copied_state_ram": lambda v: 0x00780000 <= v <= 0x0078ffff,
        "top_of_ram": lambda v: 0x00ff0000 <= v <= 0x00ffffff,
        "high_mmio": lambda v: 0xfffe0000 <= v <= 0xffffffff,
        "ascii_signatures": lambda v: v in (0x48454144, 0x50524f47),
    }
    hits: dict[str, dict[int, list[int]]] = {name: {} for name in categories}
    for offset in range(0, len(data) - 3, 2):
        value = u32(data, offset)
        for name, predicate in categories.items():
            if predicate(value):
                hits[name].setdefault(value, []).append(offset)
    lines = ["# IC30/IC13 Big-Endian Long Reference Scan", ""]
    lines.append("Scanned even offsets only. This includes both code and data, so treat entries as leads until disassembled.")
    lines.append("")
    for name, values in hits.items():
        lines.append(f"## {name}")
        lines.append("")
        if not values:
            lines.append("(none)")
            lines.append("")
            continue
        lines.append("| Value | Count | First offsets |")
        lines.append("| --- | ---: | --- |")
        for value, offsets in sorted(values.items()):
            shown = ", ".join(f"`0x{off:06x}`" for off in offsets[:8])
            if len(offsets) > 8:
                shown += ", ..."
            lines.append(f"| `0x{value:08x}` | {len(offsets)} | {shown} |")
        lines.append("")
    return "\n".join(lines)


def cmpi_byte_candidates(data: bytes) -> str:
    candidates: list[tuple[int, int, int]] = []
    for offset in range(0, len(data) - 3, 2):
        opcode = u16(data, offset)
        # cmpi.b #imm,<ea> is 0000 1100 00xx xxxx, followed by a word holding the byte immediate.
        if opcode & 0xff00 == 0x0c00:
            imm_word = u16(data, offset + 2)
            if imm_word <= 0x00ff:
                candidates.append((offset, opcode, imm_word))
    interesting = {0x08, 0x09, 0x0a, 0x0c, 0x0d, 0x1b}
    interesting.update(range(0x20, 0x7f))
    filtered = [(off, op, imm) for off, op, imm in candidates if imm in interesting]
    counts = Counter(imm for _, _, imm in filtered)
    lines = ["# IC30/IC13 `cmpi.b` Immediate Candidates", ""]
    lines.append("Linear opcode scan for `cmpi.b #imm,<ea>` patterns. This includes false positives from embedded tables.")
    lines.append("")
    lines.append("## Counts")
    lines.append("")
    lines.append("| Immediate | Char | Count |")
    lines.append("| --- | --- | ---: |")
    for imm, count in sorted(counts.items()):
        char = repr(chr(imm)) if 0x20 <= imm < 0x7f else f"control 0x{imm:02x}"
        lines.append(f"| `0x{imm:02x}` | `{char}` | {count} |")
    lines.append("")
    lines.append("## Occurrences")
    lines.append("")
    lines.append("| Offset | Opcode | Immediate | Char |")
    lines.append("| --- | --- | --- | --- |")
    for off, op, imm in filtered:
        char = repr(chr(imm)) if 0x20 <= imm < 0x7f else f"control 0x{imm:02x}"
        lines.append(f"| `0x{off:06x}` | `0x{op:04x}` | `0x{imm:02x}` | `{char}` |")
    lines.append("")
    return "\n".join(lines)


def signed16(value: int) -> int:
    return value - 0x10000 if value & 0x8000 else value


def signed8(value: int) -> int:
    return value - 0x100 if value & 0x80 else value


def linear_control_flow_scan(data: bytes) -> tuple[dict[int, list[tuple[int, str]]], list[tuple[int, int, str]]]:
    refs: dict[int, list[tuple[int, str]]] = {}
    all_refs: list[tuple[int, int, str]] = []

    def add(src: int, dst: int, kind: str) -> None:
        if 0 <= dst < len(data):
            refs.setdefault(dst, []).append((src, kind))
            all_refs.append((src, dst, kind))

    for offset in range(0, len(data) - 5, 2):
        opcode = u16(data, offset)
        ext = u16(data, offset + 2)

        if opcode == 0x4eb9:
            add(offset, u32(data, offset + 2), "jsr_abs")
        elif opcode == 0x4ef9:
            add(offset, u32(data, offset + 2), "jmp_abs")
        elif opcode == 0x41f9:
            add(offset, u32(data, offset + 2), "lea_abs_a0")
        elif opcode == 0x43f9:
            add(offset, u32(data, offset + 2), "lea_abs_a1")
        elif opcode == 0x45f9:
            add(offset, u32(data, offset + 2), "lea_abs_a2")
        elif opcode == 0x47f9:
            add(offset, u32(data, offset + 2), "lea_abs_a3")
        elif opcode == 0x49f9:
            add(offset, u32(data, offset + 2), "lea_abs_a4")
        elif opcode == 0x4bf9:
            add(offset, u32(data, offset + 2), "lea_abs_a5")
        elif opcode == 0x4df9:
            add(offset, u32(data, offset + 2), "lea_abs_a6")
        elif opcode & 0xff00 in (0x6000, 0x6100):
            disp8 = opcode & 0x00ff
            mnemonic = "bsr" if opcode & 0xff00 == 0x6100 else "bra"
            if disp8 == 0 and offset + 4 <= len(data):
                add(offset, offset + 2 + signed16(ext), f"{mnemonic}_w")
            elif disp8 != 0:
                add(offset, offset + 2 + signed8(disp8), f"{mnemonic}_b")

    return refs, all_refs


def xref_report(data: bytes) -> str:
    refs, all_refs = linear_control_flow_scan(data)
    anchors = {
        0x0000A904: "byte_fetch",
        0x0000DA9A: "esc_byte_fetch_wrapper",
        0x0000DACE: "control_1a_58_probe",
        0x0000DAF0: "escape_tokenizer",
        0x0000DB46: "angle_bracket_helper",
        0x0000DB74: "parameter_parser",
        0x0000DD08: "parsed_command_dispatch",
        0x0000DFBA: "clear_command_record",
        0x0000E002: "append_command_byte",
        0x0000E0A4: "find_or_alloc_command_record",
        0x0000FF1E: "page_root_finalize_or_reset",
        0x00010084: "ensure_page_object_root",
        0x00012714: "text_span_flush_to_page_objects",
        0x00012F2E: "text_object_queue_builder",
        0x00013070: "raster_row_object_builder",
        0x00013250: "bucket_object_alloc_and_link",
        0x000132B6: "display_list_stream_allocator",
        0x00013386: "rectangle_object_queue_entry",
        0x000133AA: "rectangle_object_insert",
        0x0001381C: "display_list_storage_alloc",
        0x0001387C: "bucket_find_or_alloc",
        0x000138DE: "raster_payload_copy_from_host",
        0x00013A48: "font_candidate_overlap_or_order_check",
        0x00014398: "font_candidate_select",
        0x0001440C: "snapshot_selected_font_candidate",
        0x00014C64: "font_candidate_dispatch",
        0x0001519A: "font_candidate_pitch_filter",
        0x000153C6: "font_candidate_style_filter",
        0x0001569C: "font_candidate_activate_primary_list",
        0x000156DE: "font_candidate_filter_current_selection",
        0x00016C14: "font_resource_download_or_object_add",
        0x000196C4: "page_root_font_slot_scan",
        0x00019DD2: "font_resource_scheduler_handoff",
        0x0001A2E4: "font_resource_candidate_scan",
        0x0001A616: "font_resource_region_scan",
        0x0001A9BE: "font_candidate_classify_and_count",
        0x0001ED84: "copy_active_page_record_to_render_record",
        0x0001EDC6: "page_record_queue_bridge",
        0x0001EE9E: "bitmap_render_state_setup",
        0x0001EF6A: "bitmap_band_render_entry",
        0x0001EF86: "bitmap_band_destination_base_setup",
        0x0001EFC2: "bitmap_bucket_chain_dispatch",
        0x0001F3D4: "bitmap_object_coordinate_decode",
        0x0001F414: "bitmap_object_span_setup",
        0x0001F446: "bitmap_special_object_dispatch",
        0x0001F4E0: "bitmap_word_mask_writer",
        0x0001F596: "bitmap_solid_mask_writer",
        0x0001F626: "bitmap_destination_pointer_setup",
        0x0001F756: "bitmap_fixed_width_rule_writer",
        0x0001F812: "bitmap_segment_list_writer",
        0x0001F862: "bitmap_segment_writer",
        0x0001F88E: "bitmap_encoded_span_writer",
        0x00033298: "common_dispatch_helper",
    }
    lines = ["# IC30/IC13 Parser Anchor Cross-References", ""]
    lines.append("Linear scan over even offsets for selected 68000 absolute calls, jumps, LEAs, BRA, and BSR forms.")
    lines.append("This is a lead generator, not a full disassembler; confirm each reference in local disassembly before naming behavior.")
    lines.append("")
    for addr, name in anchors.items():
        lines.append(f"## {name} (`0x{addr:06x}`)")
        lines.append("")
        incoming = refs.get(addr, [])
        if not incoming:
            lines.append("(no direct references found)")
            lines.append("")
            continue
        lines.append("| Source | Kind |")
        lines.append("| --- | --- |")
        for src, kind in sorted(incoming):
            lines.append(f"| `0x{src:06x}` | `{kind}` |")
        lines.append("")

    parser_region = [(src, dst, kind) for src, dst, kind in all_refs if 0x0000D900 <= dst <= 0x0000E500]
    lines.append("## References Into Parser Region 0x00d900..0x00e500")
    lines.append("")
    lines.append("| Destination | Source | Kind |")
    lines.append("| --- | --- | --- |")
    for src, dst, kind in sorted(parser_region, key=lambda item: (item[1], item[0], item[2])):
        lines.append(f"| `0x{dst:06x}` | `0x{src:06x}` | `{kind}` |")
    lines.append("")
    return "\n".join(lines)


def byte_pattern_report(data: bytes) -> str:
    patterns = {
        "ESC_E": b"\x1bE",
        "ESC_amp_f": b"\x1b&f",
        "ESC_amp_l": b"\x1b&l",
        "ESC_star_r": b"\x1b*r",
        "ESC_star_b": b"\x1b*b",
        "ESC_paren": b"\x1b(",
        "ESC_right_paren": b"\x1b)",
    }
    lines = ["# IC30/IC13 Literal Byte Pattern Scan", ""]
    lines.append("Raw byte scan; hits may be code immediates, tables, or embedded data.")
    lines.append("")
    for name, pattern in patterns.items():
        offsets: list[int] = []
        start = 0
        while True:
            pos = data.find(pattern, start)
            if pos < 0:
                break
            offsets.append(pos)
            start = pos + 1
        shown = ", ".join(f"`0x{off:06x}`" for off in offsets[:32])
        if len(offsets) > 32:
            shown += f", ... ({len(offsets)} total)"
        lines.append(f"- `{name}`: {shown if shown else '(none)'}")
    lines.append("")
    return "\n".join(lines)


def find_long_occurrences(data: bytes, value: int) -> list[int]:
    pattern = value.to_bytes(4, "big")
    offsets: list[int] = []
    start = 0
    while True:
        pos = data.find(pattern, start)
        if pos < 0:
            break
        offsets.append(pos)
        start = pos + 1
    return offsets


def page_root_reference_report(data: bytes) -> str:
    tracked = {
        0x0078297A: (
            "current page-root pointer",
            {
                0x00C44A: "page state/font-slot lookup path",
                0x00C50A: "page-root `+0x2c` font-slot manager",
                0x00C61C: "page state/font-slot update path",
                0x00D204: "text placement ensures page root before queuing",
                0x00D48A: "text object insertion retries after page-root reallocation",
                0x00D636: "alternate text placement ensures page root before queuing",
                0x00D8DA: "alternate text object insertion retries after page-root reallocation",
                0x00DA68: "display-function page-root flag update",
                0x00FF28: "page-root finalize/reset",
                0x00FF30: "page-root finalize/reset",
                0x00FF56: "page-root dirty-flag test",
                0x00FFA4: "page-root clear on finalize",
                0x00FFB2: "page-root state update after finalize",
                0x01008E: "ensure page-root entry",
                0x0100EE: "store newly allocated page root",
                0x01011A: "page-root initialization",
                0x0106DC: "raster transfer marks page-root flags",
                0x010D28: "rectangle/rule handler lead",
                0x011754: "parser/data path page-root guard",
                0x0127B4: "text span flush marks page-root flags",
                0x01326E: "bucket object allocator under `+0x1c`",
                0x013288: "bucket object allocator under `+0x1c`",
                0x0133D8: "rectangle/rule linked-list producer",
                0x0133E6: "rectangle/rule linked-list producer",
                0x0133FA: "rectangle/rule linked-list producer",
                0x013430: "rectangle/rule linked-list producer",
                0x01343C: "rectangle/rule linked-list producer",
                0x0136E4: "rectangle/rule second-mode producer",
                0x01370C: "rectangle/rule second-mode producer",
                0x01373C: "rectangle/rule second-mode producer",
                0x013760: "rectangle/rule second-mode producer",
                0x01376E: "rectangle/rule second-mode producer",
                0x01388A: "bucket find-or-allocate under `+0x1c`",
                0x0196DA: "page-root `+0x2c` font-slot scan",
                0x0196EE: "page-root `+0x2c` font-slot scan",
            },
        ),
        0x00780EA6: (
            "page/control record pool head used by allocator `0x9a9a`",
            {
                0x00314C: "pool initialization",
                0x003BF8: "scheduler/status polling",
                0x004428: "pool record cleanup",
                0x0062C0: "pool record cleanup",
                0x00653A: "control-code/page-eject path checks active pool record",
                0x00774C: "pool scheduling path",
                0x009AA0: "allocator/free-list helper",
                0x009ABA: "allocator/free-list helper",
                0x01006E: "current page root's underlying pool record published to `0x780ea6`",
                0x01C334: "font sample/page setup path",
                0x01E0F6: "font page setup path",
                0x01E92A: "alternate font page setup path",
                0x030F56: "embedded table/data hit; not disassembled as code",
            },
        ),
        0x00780EAA: ("page/control pool cursor alias", {}),
        0x00780EAE: ("page/control pool cursor alias", {}),
        0x00780EB2: ("page/control pool cursor alias", {}),
        0x00780EB6: ("page/control pool cursor alias", {}),
    }
    lines = ["# IC30/IC13 Page-Root Reference Leads", ""]
    lines.append("Raw even/odd byte scan for absolute longwords that name the current page root or the page/control record pool.")
    lines.append("Classifications are manual notes from focused disassembly windows; they are intended to prevent re-tracing rejected compositor leads.")
    lines.append("")
    for value, (role, notes) in tracked.items():
        offsets = find_long_occurrences(data, value)
        lines.append(f"## `{value:#010x}` - {role}")
        lines.append("")
        lines.append("| Offset | Current classification |")
        lines.append("| --- | --- |")
        for offset in offsets:
            note = notes.get(offset, "unclassified alias/reference lead")
            lines.append(f"| `0x{offset:06x}` | {note} |")
        if not offsets:
            lines.append("| | no occurrences |")
        lines.append("")
    lines.append("Current result: direct `0x78297a` references identify page-object producers, page-root finalization, font-slot scans, and pool management. None yet proves a final bucket-chain walker for page-root offsets `+0x1c`, `+0x24`, or `+0x28`.")
    lines.append("")
    return "\n".join(lines)


def render_path_reference_report(data: bytes) -> str:
    tracked = {
        0x0001ED84: (
            "copies the active page/control record into the selected render work record",
            {
                0x01ED78: "called after optional render-state setup in the page/control record alternator",
            },
        ),
        0x0001EDC6: (
            "copies queue/list pointers from source record to render record and normalizes object flags/fields",
            {
                0x01EDB8: "called by `0x1ed84` with destination render record and source active page/control record",
            },
        ),
        0x0001EE9E: (
            "initializes bitmap render state, including line stride at `0x783a1c`",
            {
                0x01ED70: "called when the active record band/height metadata changes",
            },
        ),
        0x0001EF6A: (
            "band render entry using work record at `0x783a18`",
            {
                0x01ECA0: "called from the surrounding band/page scheduling loop",
            },
        ),
        0x0001F446: (
            "dispatches special/object-class bitmap writers through table `0x1f4a0`",
            {
                0x01EF78: "called between bucket-chain dispatch and fixed-width rule writer",
            },
        ),
        0x0001F756: (
            "walks render-record list at `+0x20` and writes fixed-width/rule-like bitmap spans",
            {
                0x01EF7E: "called by band render entry `0x1ef6a`",
            },
        ),
        0x0001F812: (
            "renders segment-list objects selected from the bucket chain",
            {
                0x01EFEC: "called by bucket-chain dispatcher for objects with positive class bits",
            },
        ),
        0x0001F88E: (
            "renders encoded span objects selected from the bucket chain",
            {
                0x01EFF4: "called by bucket-chain dispatcher for objects with negative class bits",
            },
        ),
        0x007810B4: (
            "bitmap/page buffer base",
            {
                0x0009D0: "startup or memory initialization reference",
                0x000B4E: "startup or memory initialization store",
                0x01EEE0: "bitmap render record receives buffer base",
                0x01EF42: "buffer-clear/skip helper base",
                0x01F586: "word-mask writer wraps to base plus byte offset",
                0x01F616: "solid-mask writer wraps to base plus byte offset",
                0x01F6D4: "destination pointer setup falls back to base buffer",
                0x01F804: "fixed-width writer wraps to base plus byte offset",
            },
        ),
        0x00783A18: (
            "current render work record pointer",
            {
                0x01ED10: "record alternator publishes selected work record",
                0x01EF6E: "band render entry loads it into A6",
            },
        ),
        0x00783A1C: (
            "bitmap line stride in bytes",
            {
                0x01EEBA: "`0x1ee9e` stores record width word times four",
                0x01F52C: "word-mask writer advances destination by stride",
                0x01F5EE: "solid-mask writer advances destination by stride",
                0x01F696: "destination pointer setup scales rows by stride",
                0x01F7EC: "fixed-width writer advances destination by stride",
                0x01F864: "segment writer advances destination by stride",
            },
        ),
        0x00783A20: (
            "band row remainder/offset used by destination pointer setup",
            {
                0x01EFA8: "computed from active render record by `0x1ef86`",
                0x01F416: "used by span setup helper",
                0x01F652: "used by destination pointer setup `0x1f626`",
            },
        ),
        0x00783A28: (
            "current band destination base pointer",
            {
                0x01EFB8: "computed from render record base and band position",
                0x01F3F2: "direct destination base load",
                0x01F672: "destination pointer setup path",
                0x01F690: "destination pointer setup path",
            },
        ),
    }
    lines = ["# IC30/IC13 Render Path Reference Leads", ""]
    lines.append("Raw byte scan for render-path entry addresses and bitmap-state globals.")
    lines.append("Classifications are manual notes from focused disassembly; this report is a lead index, not a complete call graph.")
    lines.append("")
    for value, (role, notes) in tracked.items():
        offsets = find_long_occurrences(data, value)
        lines.append(f"## `{value:#010x}` - {role}")
        lines.append("")
        lines.append("| Offset | Current classification |")
        lines.append("| --- | --- |")
        for offset in offsets:
            note = notes.get(offset, "unclassified alias/reference lead")
            lines.append(f"| `0x{offset:06x}` | {note} |")
        if not offsets:
            lines.append("| | no occurrences |")
        lines.append("")
    lines.append("Current result: `0x1edc6` is the first confirmed bridge from queued page/control records into a render work record, and its concrete queue/list/context-slot copy contract is decoded in `ic30_ic13_page_record_bridge.md`. `0x1ef6a` and helpers then render a band using `0x783a18`, `0x783a1c`, `0x783a28`, and buffer base `0x7810b4`; complete parser-produced page objects and all merge rules remain to be decoded.")
    lines.append("")
    return "\n".join(lines)


def page_record_bridge_report(data: bytes) -> str:
    lines = ["# IC30/IC13 Page-Record to Render-Record Bridge", ""]
    lines.append("Generated from focused disassembly of `0x1ed84..0x1ee9c` in the verified firmware image.")
    lines.append("This report records the concrete field-copy contract between queued page/control records and the render work record consumed by `0x1ef6a` and its bucket/list dispatchers.")
    lines.append("")

    lines.append("## Active Record Copy Entry `0x1ed84`")
    lines.append("")
    lines.append("| Address | Instruction fact | Current meaning |")
    lines.append("| --- | --- | --- |")
    lines.append("| `0x1ed8c` | loads destination render record pointer from stack argument into `A5` | caller selects which render work record is being prepared |")
    lines.append("| `0x1ed90` | loads source active page/control record from `0x780eae` into `A4` | source record is the active page/control record selected by the scheduler |")
    lines.append("| `0x1ed96..0x1eda8` | copies source words `+0x18/+0x1a` into destination words `+0x0a/+0x0c/+0x10/+0x16` and clears destination word `+0x0e` | band/page dimensions and starting row state are initialized before object-list copying |")
    lines.append("| `0x1edb2..0x1edb6` | calls `0x1edc6(destination, source)` | queue/list pointers and font/context slots are copied by the helper below |")
    lines.append("")

    lines.append("## Queue/List Copy Helper `0x1edc6`")
    lines.append("")
    lines.append("| Address | Instruction fact | Render-record contract |")
    lines.append("| --- | --- | --- |")
    lines.append("| `0x1edd6..0x1ede0` | returns immediately if source record is null | null active records produce no copied queue/list state |")
    lines.append("| `0x1ede2` | `move.l (0x1c,A4),(0x18,A5)` | page/control bucket array root `+0x1c` becomes render-record bucket root `+0x18` |")
    lines.append("| `0x1ede8` | `move.l (0x24,A4),(0x1c,A5)` | page/control rule/list chain `+0x24` becomes render-record list `+0x1c` for `0x1f446` |")
    lines.append("| `0x1edee` | `move.l (0x28,A4),(0x20,A5)` | page/control second-mode/fixed-width chain `+0x28` becomes render-record list `+0x20` for `0x1f756` |")
    lines.append("| `0x1edf4..0x1ee0e` | walks render-record `+0x1c`; ORs byte `object+5` with `0x10`; copies word `object+0x0a` to `object+0x0c` | rule/list objects are marked and receive a duplicated dimension/band word before dispatch |")
    lines.append("| `0x1ee10..0x1ee5e` | walks render-record `+0x20`; ORs byte `object+5` with `0x10`; copies word `object+8` to `object+0x0a`; writes byte `+0x0c=1`, byte `+0x0d=8` | fixed-width/text-span-like objects are normalized to the shape expected by the fixed-width writer |")
    lines.append("| `0x1ee60..0x1ee94` | loops `D7=0..15`, copying longwords from source `+0x2c+4*D7` to destination `+0x24+4*D7` | 16 page-root font/context slots become render-record context slots selected by compact bucket byte `+5` |")
    lines.append("")

    lines.append("## Renderer Consumers")
    lines.append("")
    lines.append("| Render-record field | Consumer | Current role |")
    lines.append("| --- | --- | --- |")
    lines.append("| `+0x18` | `0x1efc2` bucket-chain dispatcher | compact text/glyph buckets from `0x12f2e` and encoded raster row objects from `0x13070` / `0x13250` |")
    lines.append("| `+0x1c` | `0x1f446` special/rule-list dispatcher | rectangle/rule objects from `0x13386` / `0x133aa` after bridge normalization |")
    lines.append("| `+0x20` | `0x1f756` fixed-width/rule writer | second-mode rule/text-span objects from `0x13520` / `0x136d2` after bridge normalization |")
    lines.append("| `+0x24..+0x60` | `0x1f008` / `0x1f354` compact glyph context resolver | compact object byte `+5` low nibble selects one of the 16 copied context slots |")
    lines.append("")

    lines.append("## Reproduction Contract")
    lines.append("")
    lines.append("- A page-object reproduction model must preserve the three page/control record queues separately until the `0x1edc6` bridge copies them into render-record fields `+0x18`, `+0x1c`, and `+0x20`.")
    lines.append("- The compact text/glyph path is the least transformed by the bridge: the bucket root pointer is copied, and the renderer then selects context slots copied from source `+0x2c..+0x68`.")
    lines.append("- The rule/list and fixed-width chains are not pass-through. Their object bytes are normalized by `0x1edc6` before the render dispatchers see them, so fixtures must compare the post-bridge object shape when validating these paths.")
    lines.append("- `tools/render_fixture_harness.py` now has a `0x1edc6` fixture that bridges a compact text bucket, verifies the copied context slot can render the same glyph rows, and pins both list-normalization side effects. The remaining gap is to replace that synthetic page/control record with a parser-produced page root and compare the finalized record published by `0xff1e`.")
    lines.append("")
    return "\n".join(lines)


def compact_bucket_allocator_report(data: bytes) -> str:
    lines = ["# IC30/IC13 Compact Bucket Allocator", ""]
    lines.append("Generated from focused disassembly of `0x12f2e`, `0x1387c`, and the shared stream allocator at `0x1381c` in the verified firmware image.")
    lines.append("This report records how compact text/glyph objects are found, allocated, and linked under the page-root `+0x1c` bucket array before the `0x1edc6` render-record bridge copies that array into the renderer.")
    lines.append("")

    lines.append("## Producer Inputs from `0x12f2e`")
    lines.append("")
    lines.append("| Address | Instruction fact | Current meaning |")
    lines.append("| --- | --- | --- |")
    lines.append("| `0x12f3c..0x12f60` | reads source words `+0x12/+0x14`, stores `source_y >> 4` in `0x782a7c`, and packs y/subbyte/x pieces into a word on the stack | `0x782a7c` is the page-root bucket index; the stack word becomes the compact coordinate payload |")
    lines.append("| `0x12f68..0x12f6e` | masks source word `+0x16` to four bits and starts selector `D5` with that value | low selector bits are the render context slot used later by compact rendering |")
    lines.append("| `0x12f70..0x12fbe` | selects flagged or unflagged source metrics and sets selector bit `0x1000` for wide glyphs | flagged sources compare glyph-entry word `+8` against `0x80` and use word `+6` as row count; unflagged sources compare inline-record byte `+0` against `0x10` and use byte `+1` as row count; selector byte `+4` bit `0x10` chooses compact render mode 1 when width exceeds the path threshold |")
    lines.append("| `0x12fc0..0x12fd4` | sets selector bit `0x2000` when rows exceed `0x80`; computes segment `(rows - 1) >> 7`; adds `segment * 8` to `0x782a7c` | tall glyphs are stored as multiple segment entries across bucket indices spaced by 8 |")
    lines.append("| `0x12fd6..0x12fe0` | calls `0x1387c(selector, capacity=8, object_size=0x28)` for segmented entries | segmented compact objects have four-byte entries |")
    lines.append("| `0x12ff4..0x12ffe` | calls `0x1387c(selector, capacity=10, object_size=0x26)` for short entries | short compact objects have three-byte entries |")
    lines.append("| `0x1301c..0x13034` | increments object count at `+6`; writes mapped glyph byte, segment byte, and compact coord | segmented payload entry is `glyph, segment, coord_hi, coord_lo` |")
    lines.append("| `0x1303e..0x13068` | increments object count at `+6`; writes mapped glyph byte and compact coord | short payload entry is `glyph, coord_hi, coord_lo` |")
    lines.append("")

    lines.append("## Find-or-Allocate Helper `0x1387c`")
    lines.append("")
    lines.append("| Address | Instruction fact | Current meaning |")
    lines.append("| --- | --- | --- |")
    lines.append("| `0x13884` | loads selector argument into `D5` | selector is the word written to object `+4` for compact text/glyph objects |")
    lines.append("| `0x13888..0x1389c` | loads current page root `0x78297a`, follows root `+0x1c`, indexes by `0x782a7c * 4`, and loads the bucket head | compact text/glyph objects are chained from the page-root bucket array |")
    lines.append("| `0x138a2..0x138b2` | compares existing object word `+4` with selector and returns it if count word `+6` is below the capacity argument at stack `+0x0e` | matching objects are reused until their entry count reaches capacity |")
    lines.append("| `0x138d6..0x138dc` | walks `object+0` next pointers until a match or end of chain | different selector objects can coexist in the same bucket chain |")
    lines.append("| `0x138b6..0x138ca` | calls `0x1381c(object_size)`, copies old bucket head to new object `+0`, stores new object into the bucket head, and writes selector at `+4` | new compact objects are inserted at the bucket head |")
    lines.append("")

    lines.append("## Shared Stream Allocator `0x1381c`")
    lines.append("")
    lines.append("| Address | Instruction fact | Current meaning |")
    lines.append("| --- | --- | --- |")
    lines.append("| `0x13820..0x13834` | compares requested byte count against remaining bytes `0x782a70` | uses the current 0x100-byte chunk when enough payload space remains |")
    lines.append("| `0x13836..0x13860` | allocates a new 0x100-byte chunk via `0x1710`, links it through `0x782a72`, sets next-free pointer to chunk `+4`, and sets remaining bytes to `0xfc` | chunk first longword is the next-chunk link; the remaining 252 bytes are object storage |")
    lines.append("| `0x13864..0x13874` | returns the old next-free pointer, advances `0x782a76`, and subtracts the requested size from `0x782a70` | compact/raster/rule objects share the same page-root stream-storage pool |")
    lines.append("")

    lines.append("## Reproduction Contract")
    lines.append("")
    lines.append("- A page-object model must keep `0x782a7c` as the bucket index, not as part of the object payload. `0x1387c` uses it to choose one entry in the page-root `+0x1c` bucket-head array.")
    lines.append("- Compact object identity for reuse is the selector word at object `+4`; capacity is supplied by the producer (`10` for short entries, `8` for segmented entries) and compared against count word `+6`.")
    lines.append("- When no reusable object exists, new compact objects are linked at the head of the selected bucket chain and receive selector word `+4`; payload count starts at zero until the producer increments it.")
    lines.append("- `tools/render_fixture_harness.py` now has executable `0x1387c` fixtures for short reuse, full-object new-head allocation, segmented tall-glyph bucket allocation/reuse, and mixed printable/control and printable/reset byte streams that queue through page-record storage before bridging through `0x1edc6`; it also renders a short object queued through that page-record allocator before bridging it through `0x1edc6`.")
    lines.append("")
    return "\n".join(lines)


def render_dispatch_table_report(data: bytes) -> str:
    lines = ["# IC30/IC13 Render Object Dispatch Tables", ""]
    lines.append("Generated from literal dispatch tables and confirmed producer/consumer instructions in the firmware image.")
    lines.append("Field names are provisional, but the branch conditions and table targets are direct code facts.")
    lines.append("")

    lines.append("## Bucket Object Class Branch at `0x1efc2`")
    lines.append("")
    lines.append("The bucket walker loads a bucket object, advances `A1` to object offset `+4`, masks byte `+4` with `0xc0`, and dispatches as follows.")
    lines.append("")
    lines.append("| Object byte `+4` high bits | Branch | Current role |")
    lines.append("| --- | --- | --- |")
    lines.append("| `0x00..0x3f` | `bsr 0x1effe` | compact object; byte `+4` bits `0x10/0x20` select table `0x1f024`; byte `+5` low nibble selects render-record context slot `+0x24 + 4*n` |")
    lines.append("| `0x40..0x7f` | `jsr 0x1f812` | segment-list object |")
    lines.append("| `0x80..0xff` | `jsr 0x1f88e` | encoded-span object; raster rows are born with byte `+4 = 0x80` |")
    lines.append("")

    compact_table = [
        ("`object+4 & 0x30 == 0x00`", 0),
        ("`object+4 & 0x30 == 0x10`", 1),
        ("`object+4 & 0x30 == 0x20`", 2),
        ("`object+4 & 0x30 == 0x30`", 3),
    ]
    lines.append("## Compact Bucket Sub-Dispatch Table `0x1f024`")
    lines.append("")
    lines.append("Selected by `(object[4] & 0x30) >> 2`, which is a byte offset into a longword table.")
    lines.append("")
    lines.append("| Selector | Table entry | Target |")
    lines.append("| --- | ---: | --- |")
    for label, index in compact_table:
        addr = 0x1F024 + index * 4
        lines.append(f"| {label} | `0x{addr:06x}` | `0x{u32(data, addr):06x}` |")
    lines.append("")

    special_table = [u32(data, 0x1F4A0 + i * 4) for i in range(16)]
    lines.append("## Render-Record `+0x1c` List Dispatch Table `0x1f4a0`")
    lines.append("")
    lines.append("Routine `0x1f446` walks render-record list `+0x1c`, filters by the current band, then uses `object[5] & 0x0f` to select this table.")
    lines.append("")
    lines.append("| `object[5] & 0x0f` | Target |")
    lines.append("| ---: | --- |")
    for index, target in enumerate(special_table):
        lines.append(f"| {index} | `0x{target:06x}` |")
    lines.append("")

    encoded_table = [u32(data, 0x1F8CA + i * 4) for i in range(4)]
    lines.append("## Encoded-Span Sub-Dispatch Table `0x1f8ca`")
    lines.append("")
    lines.append("Routine `0x1f88e` starts from bucket object `+4`, reads `object[5] & 0x03`, and selects this table after setting up destination coordinates.")
    lines.append("")
    lines.append("| `object[5] & 0x03` | Target |")
    lines.append("| ---: | --- |")
    for index, target in enumerate(encoded_table):
        lines.append(f"| {index} | `0x{target:06x}` |")
    lines.append("")

    lines.append("## Producer-to-Renderer Mapping")
    lines.append("")
    lines.append("| Producer | Queue/list | Selector fields written | Confirmed render path |")
    lines.append("| --- | --- | --- | --- |")
    lines.append("| `0x13070` / `0x13250` raster row objects | page-root `+0x1c` bucket array -> render-record `+0x18` | `object[4]=0x80`, `object[5]` is the low byte of the first `0x13250` argument sourced from raster-state word `+0x08`, `object[6]=capacity`, `object[8]=packed key`, payload at `+0x0a` | high-bit branch to `0x1f88e`, then table `0x1f8ca` |")
    lines.append("| `0x12f2e` text/glyph bucket objects via `0x1387c` | page-root `+0x1c` bucket array -> render-record `+0x18` | word at `object+4` is the selector/key from `D5`; bits `0x1000`/`0x2000` become byte `+4` bits `0x10`/`0x20`; count word is at `+0x06`; entries start at `+0x08` | compact branch to `0x1effe`, then table `0x1f024` |")
    lines.append("| `0x13386` / `0x133aa` rectangle/rule objects | page-root `+0x24` -> render-record `+0x1c` | `object[4]=0x782a7d`, `object[5] |= source[8]`, words `+6/+8/+0a` from packed key and dimensions; bridge copies `+0x0a` to `+0x0c` | list renderer `0x1f446`, then table `0x1f4a0` |")
    lines.append("| `0x13520` / `0x136d2` second-mode rule/text-span objects | page-root `+0x28` -> render-record `+0x20` | `object[4]=0x782a7d`, `object[5]=source[1]`, words `+6/+8`; bridge copies `+8` to `+0x0a` and sets `+0x0c=1`, `+0x0d=8` | fixed-width/rule writer `0x1f756` / `0x1f7b0` |")
    lines.append("")
    lines.append("`tools/render_fixture_harness.py` now has parser-derived raster state fixtures for `0x10808` (`ESC *t#R`) and `0x1075a` (`ESC *r#A`), proving 300/150/100/75 dpi select encoded modes 0/1/2/3 before queueing a mode-0 transfer object; it also has modeled raster command/data stream fixtures for `ESC *t300R` / `ESC *r1A` / delayed `ESC *b4W`, `ESC *t150R` / `ESC *r0A` / delayed `ESC *b2W`, `ESC *t100R` / `ESC *r0A` / delayed `ESC *b2W`, and `ESC *t75R` / `ESC *r0A` / delayed `ESC *b2W` bytes that record handler `0x0105d0`, queue mode-0/1/2/3 objects, bridge the `ESC *b4W` page-record object through `0x1edc6`, and render the literal, two-row, three-row, and four-row expansions; a separate `ESC *t300R` / `ESC *r0A` stream with two consecutive `ESC *b2W` payloads verifies row_y `0 -> 1 -> 2` and page-record chain objects at coords `0x1000` then `0x0000`. Same-group lowercase-final chaining fixtures cover `ESC *t300r150R` and chained `ESC *b2w` / `2W`, proving continued parser mode and payload-boundary placement while producing the same two-row page-record chain shape as the separate-command stream. A bare `ESC *rB` stream proves handler `0x107fa` clears only raster active state and allows a following `ESC *t150R` mode change. Raster row fixtures also queue byte-aligned mode-0 object `00 00 00 00 80 00 00 04 00 01 f0 0f aa 55`, non-byte-aligned mode-0 object `00 00 00 00 80 00 00 02 04 01 c3 3c`, mode-1 object `00 00 00 00 80 01 00 02 00 01 f0 0f`, byte-aligned mode-2 object `00 00 00 00 80 02 00 02 00 01 f0 0f`, non-byte-aligned mode-2 object `00 00 00 00 80 02 00 02 04 01 f0 0f`, band-clipped mode-2 object `00 00 00 00 80 02 00 02 f0 01 f0 0f` with fallback-buffer continuation rows, and mode-3 object `00 00 00 00 80 03 00 02 00 01 f0 0f` through the `0x13070` / `0x13250` / `0x138de` shape, bridge the byte-aligned mode-0 object through `0x1edc6`, and render the rows through `0x1f88e` / `0x1f8da`, `0x1f8e6`, `0x1f920`, and `0x1f9c6`.")
    lines.append("")
    return "\n".join(lines)


def render_subrenderer_report(data: bytes) -> str:
    def table_rows(base: int, count: int) -> list[str]:
        return [f"| {i} | `0x{base + i * 4:06x}` | `0x{u32(data, base + i * 4):06x}` |" for i in range(count)]

    lines = ["# IC30/IC13 Render Subrenderer Notes", ""]
    lines.append("Generated from focused renderer tables and instruction-level field use.")
    lines.append("This names byte/word consumption and write patterns, not final high-level PCL semantics.")
    lines.append("")

    lines.append("## Glyph/Context Resolver `0x1f354`")
    lines.append("")
    lines.append("The compact branch stores one render-record context longword into `0x783a2c` before calling a compact renderer. `0x1f354` resolves a glyph/resource entry from that context and the glyph index in `D1`.")
    lines.append("")
    lines.append("| Context form | Test | Resulting fields |")
    lines.append("| --- | --- | --- |")
    lines.append("| offset-table form | bit 30 of `0x783a2c` set | clears high byte, uses context base plus word `+8` as offset table, indexes long offsets by `D1`, and reads glyph fields from the selected entry |")
    lines.append("| fixed-record form | bit 30 clear | clears high byte, uses context base plus `0x40 + 8*D1`, reads inline glyph fields, and adds a long bitmap offset from that record |")
    lines.append("")
    lines.append("Observed outputs from `0x1f354`: `A2` points at glyph bitmap data, `D1` is a byte/word span count derived from glyph width, `D3` is a row/count field, and `A3` may point at an alternate glyph plane/row when the glyph has more than one row/plane.")
    lines.append("")

    lines.append("## Compact Glyph Object Modes")
    lines.append("")
    lines.append("The compact renderers all start with a word count at the object payload pointer, then process that many entries. Each entry begins with a glyph/resource index byte consumed by `0x1f354`; the remaining bytes differ by mode.")
    lines.append("")
    lines.append("| Selector bits from object byte `+4` | Target | Payload entry shape | Current write behavior |")
    lines.append("| --- | --- | --- | --- |")
    lines.append("| `0x00` | `0x1f034` | glyph byte, coordinate word | resolves glyph, computes destination with `0x1f3d4`/`0x1f414`, then uses table `0x1f08e` indexed by glyph span/count to copy glyph rows; if clipped across a band, repeats from `0x7810b4 + D2` |")
    lines.append("| `0x10` | `0x1f0d2` | glyph byte, coordinate word | like `0x1f034`, but splits wide glyphs into full 16-pixel chunks via helper `0x2f27c` and a remainder through table `0x1f1ac`; uses scratch `0x783a40..0x783a48` |")
    lines.append("| `0x20` | `0x1f1f0` | glyph byte, vertical/plane byte, coordinate word | adjusts glyph bitmap pointers by `byte*0x80`, clips height to `0x80`, then uses table `0x1f08e` |")
    lines.append("| `0x30` | `0x1f264` | glyph byte, vertical/plane byte, coordinate word | combines the vertical/plane adjustment of `0x1f1f0` with the chunk/remainder loop of `0x1f0d2` |")
    lines.append("")

    lines.append("## Compact Glyph Row Tables")
    lines.append("")
    lines.append("Table `0x1f08e` is selected by the glyph span/count returned in `D5`; table `0x1f1ac` is selected by a remainder count for wide glyph chunks.")
    lines.append("")
    lines.append("### Table `0x1f08e`")
    lines.append("")
    lines.append("| Index | Entry | Target |")
    lines.append("| ---: | --- | --- |")
    lines.extend(table_rows(0x1F08E, 17))
    lines.append("")
    lines.append("### Table `0x1f1ac`")
    lines.append("")
    lines.append("| Index | Entry | Target |")
    lines.append("| ---: | --- | --- |")
    lines.extend(table_rows(0x1F1AC, 17))
    lines.append("")

    lines.append("## Encoded Raster Span Modes")
    lines.append("")
    lines.append("Routine `0x1f88e` enters with `A1` at bucket object `+4`; it skips object byte `+4`, uses `object[5] & 0x03` as mode, reads word `object+6` into `D5`, reads word `object+8` into `D1`, computes destination with `0x1f3d4`/`0x1f414`, then sets `D2 = D5` before mode dispatch.")
    lines.append("")
    lines.append("| Mode | Target | Payload consumed after object `+0x0a` | Write pattern |")
    lines.append("| ---: | --- | --- | --- |")
    lines.append("| 0 | `0x1f8da` | words | copies `D2` bytes as literal words from payload to consecutive destination words |")
    lines.append("| 1 | `0x1f8e6` | bytes | expands each byte through 16-bit table `0x30914` and writes the same word to the current destination and one adjacent row/band destination |")
    lines.append("| 2 | `0x1f920` | bytes, one skipped byte between table lookups | expands bytes through 32-bit table `0x30b14` and writes each longword to up to three row/band destinations selected by clipped row remainder state |")
    lines.append("| 3 | `0x1f9c6` | bytes | expands each byte through two levels of table `0x30914` into a longword and writes it to four row/band destinations selected by clipped row remainder state |")
    lines.append("")

    lines.append("## Encoded Raster Expansion Tables")
    lines.append("")
    lines.append("The mode-1 and mode-3 byte expansion table begins at `0x30914`; mode 2 uses longword table `0x30b14`. First entries are enough to identify the expansion pattern.")
    lines.append("")
    lines.append("| Table | Entry size | First 16 decoded values |")
    lines.append("| --- | --- | --- |")
    table_30914 = ", ".join(f"`0x{u16(data, 0x30914 + i * 2):04x}`" for i in range(16))
    table_30b14 = ", ".join(f"`0x{u32(data, 0x30B14 + i * 4):08x}`" for i in range(16))
    lines.append(f"| `0x30914` | word | {table_30914} |")
    lines.append(f"| `0x30b14` | long | {table_30b14} |")
    lines.append("")

    lines.append("## Row-Copy Helper Tables")
    lines.append("")
    lines.append("Helper `0x2f27c` uses `D3` as an index into table `0x2f2ac`, after offsetting `A1` and `A2` by `0x783a46`; its table targets are descending unrolled row-copy routines that copy glyph words and advance by stride `0x783a1c - 0x0e`. Helper `0x1fa5c` and `0x1fe76` use similar table-driven byte/word row writers.")
    lines.append("Generated fixture report `ic30_ic13_render_row_copy_fixtures.md` decodes the main width table `0x1f08e`, the wide-glyph remainder table `0x1f1ac`, and the `0x2f27c` chunk helper into synthetic A1/A2/A3 write traces. Odd byte-width spans copy the trailing byte from `A3`; even byte-width spans are all word copies from `A2`.")
    lines.append("")
    lines.append("### Table `0x2f2ac` first 16 targets")
    lines.append("")
    lines.append("| Index | Entry | Target |")
    lines.append("| ---: | --- | --- |")
    lines.extend(table_rows(0x2F2AC, 16))
    lines.append("")
    lines.append("### Table `0x1fa70` first 16 targets")
    lines.append("")
    lines.append("| Index | Entry | Target |")
    lines.append("| ---: | --- | --- |")
    lines.extend(table_rows(0x1FA70, 16))
    lines.append("")
    lines.append("### Table `0x1fe8a` first 16 targets")
    lines.append("")
    lines.append("| Index | Entry | Target |")
    lines.append("| ---: | --- | --- |")
    lines.extend(table_rows(0x1FE8A, 16))
    lines.append("")
    return "\n".join(lines)


def render_row_copy_fixture_report(data: bytes) -> str:
    stride = 0x20
    source_row_delta = 0x04

    def setup_for_helper(helper: int) -> dict[str, int | bool | None]:
        pos = helper
        d0_adjust = 0
        table_base: int | None = None
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
            elif op in (0x4ED0, 0x4ED4):
                break
            elif op in (0x48E7,):
                pos += 4
            elif op in (0xE54B,):
                pos += 2
            elif op in (0x2070, 0x2874):
                pos += 4
            else:
                pos += 2
        return {
            "table_base": table_base,
            "d0_adjust": d0_adjust,
            "dest_phase": dest_phase,
            "source_phase": source_phase,
            "source_row_skip": source_row_skip,
        }

    def simulate_tail(target: int, setup: dict[str, int | bool | None], row_count: int) -> tuple[list[dict[str, int | str]], int, int, int, list[str]]:
        d0 = stride - int(setup["d0_adjust"] or 0)
        a1 = 0x10 if setup["dest_phase"] else 0
        a2 = 0x10 if setup["source_phase"] else 0
        a3 = 0
        writes: list[dict[str, int | str]] = []
        unknown: list[str] = []
        pos = target
        for _ in range(2000):
            op = u16(data, pos)
            if op == 0x4E75:
                return writes, a1, a2, a3, unknown
            if op == 0x4CDF:
                pos += 4
                continue
            if op == 0x129A:
                writes.append({"kind": "byte", "dst": a1, "src": a2, "source": "A2", "size": 1})
                a2 += 1
                pos += 2
            elif op == 0x12DA:
                writes.append({"kind": "byte", "dst": a1, "src": a2, "source": "A2", "size": 1})
                a2 += 1
                a1 += 1
                pos += 2
            elif op == 0x129B:
                writes.append({"kind": "byte", "dst": a1, "src": a3, "source": "A3", "size": 1})
                a3 += 1
                pos += 2
            elif op == 0x329A:
                writes.append({"kind": "word", "dst": a1, "src": a2, "source": "A2", "size": 2})
                a2 += 2
                pos += 2
            elif op == 0x32DA:
                writes.append({"kind": "word", "dst": a1, "src": a2, "source": "A2", "size": 2})
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
                unknown.append(f"0x{pos:06x}:0x{op:04x}")
                return writes, a1, a2, a3, unknown
        unknown.append(f"tail from 0x{target:06x} did not reach RTS")
        return writes, a1, a2, a3, unknown

    def writes_summary(writes: list[dict[str, int | str]], limit: int = 12) -> str:
        if not writes:
            return "(no writes)"
        cells = []
        for write in writes[:limit]:
            source = str(write.get("source", "A2"))
            cells.append(f"`dst+0x{int(write['dst']):02x} <= {source}+0x{int(write['src']):02x} {write['kind']}`")
        if len(writes) > limit:
            cells.append(f"... {len(writes) - limit} more")
        return ", ".join(cells)

    def helper_row(table_base: int, index: int, label: str) -> str:
        helper = u32(data, table_base + index * 4)
        setup = setup_for_helper(helper)
        row_table = setup["table_base"]
        if row_table is None:
            return f"| {label} | {index} | `0x{helper:06x}` | `(no row table found)` |  |  |  |"
        row0 = u32(data, row_table)
        row1 = u32(data, row_table + 4)
        writes, a1_end, a2_end, a3_end, unknown = simulate_tail(row1, setup, 1)
        d0_adjust = int(setup["d0_adjust"] or 0)
        stride_text = "`stride`" if d0_adjust == 0 else f"`stride - 0x{d0_adjust:x}`"
        phase_bits = []
        if setup["dest_phase"]:
            phase_bits.append("A1 += `0x783a46`")
        if setup["source_phase"]:
            phase_bits.append("A2 += `0x783a46`")
        if setup["source_row_skip"]:
            phase_bits.append("A2 row skip += `0x783a40`")
        phase_text = ", ".join(phase_bits) if phase_bits else "none"
        unknown_text = ", ".join(unknown) if unknown else ""
        return (
            f"| {label} | {index} | `0x{helper:06x}` | `0x{row_table:06x}` | "
            f"`0x{row0:06x}` / `0x{row1:06x}` | {stride_text}; {phase_text} | "
            f"{writes_summary(writes, 8)}; end A1 `+0x{a1_end:02x}`, A2 `+0x{a2_end:02x}`, A3 `+0x{a3_end:02x}` {unknown_text} |"
        )

    def fixture_block(title: str, helper: int, row_counts: list[int]) -> list[str]:
        setup = setup_for_helper(helper)
        table_base = setup["table_base"]
        lines = [f"### {title}", ""]
        if table_base is None:
            lines.append(f"No row-count table found in helper `0x{helper:06x}`.")
            lines.append("")
            return lines
        d0_adjust = int(setup["d0_adjust"] or 0)
        stride_text = "stride" if d0_adjust == 0 else f"stride - 0x{d0_adjust:x}"
        lines.append(f"Helper `0x{helper:06x}` uses row-count table `0x{table_base:06x}` with `D0 = {stride_text}`.")
        lines.append("")
        lines.append("| Rows (`D3`) | Tail target | Writes from synthetic A1/A2/A3 | Final A1 | Final A2 | Final A3 |")
        lines.append("| ---: | --- | --- | ---: | ---: | ---: |")
        for row_count in row_counts:
            target = u32(data, table_base + row_count * 4)
            writes, a1_end, a2_end, a3_end, unknown = simulate_tail(target, setup, row_count)
            suffix = f" Unknown: {', '.join(unknown)}" if unknown else ""
            lines.append(
                f"| {row_count} | `0x{target:06x}` | {writes_summary(writes, 24)}{suffix} | `+0x{a1_end:02x}` | `+0x{a2_end:02x}` | `+0x{a3_end:02x}` |"
            )
        lines.append("")
        return lines

    lines = ["# IC30/IC13 Compact Glyph Row-Copy Fixtures", ""]
    lines.append("Generated by parsing the ROM's row-copy helper prologues, row-count jump tables, and unrolled copy tails.")
    lines.append("The synthetic fixture state uses `stride=0x20`, `0x783a46=0x10` when a helper phases A1/A2, and `0x783a40=0x04` when a tail advances the source pointer between rows.")
    lines.append("Destination/source offsets are relative to the synthetic A1/A2 inputs after any helper prologue phasing.")
    lines.append("")

    lines.append("## Main Compact-Glyph Width Table `0x1f08e`")
    lines.append("")
    lines.append("The compact modes `0x1f034` and `0x1f1f0` select this table with the glyph span/count returned by `0x1f354`; index 0 is the error path.")
    lines.append("")
    lines.append("| Width index | Table index | Helper | Row-count table | Row 0 / row 1 target | Derived stride/phasing | One-row write fixture |")
    lines.append("| --- | ---: | --- | --- | --- | --- | --- |")
    for index in range(1, 17):
        lines.append(helper_row(0x1F08E, index, f"{index} byte(s)"))
    lines.append("")

    lines.append("## Wide-Glyph Remainder Table `0x1f1ac`")
    lines.append("")
    lines.append("The wide compact modes `0x1f0d2` and `0x1f264` use this table after full 16-byte chunks have been rendered through `0x2f27c`; `0x783a46` supplies the current chunk/remainder x phase.")
    lines.append("")
    lines.append("| Remainder | Table index | Helper | Row-count table | Row 0 / row 1 target | Derived stride/phasing | One-row write fixture |")
    lines.append("| --- | ---: | --- | --- | --- | --- | --- |")
    for index in range(1, 17):
        lines.append(helper_row(0x1F1AC, index, f"{index} byte(s)"))
    lines.append("")

    lines.append("## Representative Multi-Row Fixtures")
    lines.append("")
    lines.extend(fixture_block("Main width 1 byte helper", u32(data, 0x1F08E + 1 * 4), [0, 1, 3]))
    lines.extend(fixture_block("Main width 3 byte helper", u32(data, 0x1F08E + 3 * 4), [0, 1, 3]))
    lines.extend(fixture_block("Main width 16 byte helper", u32(data, 0x1F08E + 16 * 4), [0, 1, 3]))
    lines.extend(fixture_block("Wide-glyph 16 byte chunk helper `0x2f27c`", 0x2F27C, [0, 1, 3]))
    lines.extend(fixture_block("Remainder width 1 byte helper", u32(data, 0x1F1AC + 1 * 4), [0, 1, 3]))
    lines.extend(fixture_block("Remainder width 16 byte helper", u32(data, 0x1F1AC + 16 * 4), [0, 1, 3]))
    return "\n".join(lines)


def render_expansion_fixture_report(data: bytes) -> str:
    sample_bytes = [0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x08, 0x0F, 0x10, 0x33, 0x55, 0xAA, 0xF0, 0xFF]

    def expand_word(byte: int) -> int:
        return u16(data, 0x30914 + byte * 2)

    def expand_long(byte: int) -> int:
        return u32(data, 0x30B14 + byte * 4)

    def mode3_long(byte: int) -> int:
        first = expand_word(byte)
        high = (first >> 8) & 0xFF
        low = first & 0xFF
        return (expand_word(high) << 16) | expand_word(low)

    literal_payload = bytes([0x12, 0x34, 0xAB, 0xCD, 0x00, 0xFF, 0x55, 0xAA])
    literal_words = [u16(literal_payload, i) for i in range(0, len(literal_payload), 2)]

    lines = ["# IC30/IC13 Encoded Raster Expansion Fixtures", ""]
    lines.append("These fixtures are generated directly from ROM expansion tables used by encoded raster span modes under `0x1f88e`.")
    lines.append("They are intended as small renderer-unit expectations before full page-coordinate fixtures exist.")
    lines.append("")

    lines.append("## Mode 0 Literal Word Copy")
    lines.append("")
    lines.append("Mode 0 (`0x1f8da`) copies payload words directly to consecutive destination words while decrementing the byte count by two.")
    lines.append("")
    lines.append(f"- sample payload bytes: `{' '.join(f'{byte:02x}' for byte in literal_payload)}`")
    lines.append(f"- expected destination words: `{', '.join(f'0x{word:04x}' for word in literal_words)}`")
    lines.append("")

    lines.append("## Mode 1 Byte-to-Word Expansion")
    lines.append("")
    lines.append("Mode 1 (`0x1f8e6`) expands each payload byte through word table `0x30914`, then writes the same word to the current destination and one adjacent row/band destination.")
    lines.append("")
    lines.append("| Payload byte | Expanded word | Relative writes per byte |")
    lines.append("| ---: | ---: | --- |")
    for byte in sample_bytes:
        word = expand_word(byte)
        lines.append(f"| `0x{byte:02x}` | `0x{word:04x}` | `(row 0, word n)=0x{word:04x}` and `(row 1, word n)=0x{word:04x}` |")
    lines.append("")

    lines.append("## Mode 2 Byte-to-Long Expansion")
    lines.append("")
    lines.append("Mode 2 (`0x1f920`) expands bytes through longword table `0x30b14`. The loop advances the payload pointer by two for each lookup, so paired/skip-byte payload layouts must preserve that stride.")
    lines.append("")
    lines.append("| Payload byte used | Expanded long | High word | Low word |")
    lines.append("| ---: | ---: | ---: | ---: |")
    for byte in sample_bytes:
        value = expand_long(byte)
        lines.append(f"| `0x{byte:02x}` | `0x{value:08x}` | `0x{value >> 16:04x}` | `0x{value & 0xffff:04x}` |")
    lines.append("")

    lines.append("## Mode 3 Cascaded Byte Expansion")
    lines.append("")
    lines.append("Mode 3 (`0x1f9c6`) first expands the payload byte through `0x30914`, then expands the high and low bytes of that word through the same table to form one longword.")
    lines.append("")
    lines.append("| Payload byte | First table word | Final long | High word | Low word |")
    lines.append("| ---: | ---: | ---: | ---: | ---: |")
    for byte in sample_bytes:
        first = expand_word(byte)
        value = mode3_long(byte)
        lines.append(f"| `0x{byte:02x}` | `0x{first:04x}` | `0x{value:08x}` | `0x{value >> 16:04x}` | `0x{value & 0xffff:04x}` |")
    lines.append("")

    lines.append("## Minimal Fixture Vectors")
    lines.append("")
    lines.append("These compact vectors can be copied into a renderer test once the destination-address setup is implemented.")
    lines.append("")
    lines.append("| Mode | Input bytes | Expected expanded values |")
    lines.append("| ---: | --- | --- |")
    mode1_values = [expand_word(byte) for byte in sample_bytes]
    mode2_values = [expand_long(byte) for byte in sample_bytes]
    mode3_values = [mode3_long(byte) for byte in sample_bytes]
    lines.append(f"| 0 | `{' '.join(f'{byte:02x}' for byte in literal_payload)}` | `{', '.join(f'0x{word:04x}' for word in literal_words)}` |")
    lines.append(f"| 1 | `{' '.join(f'{byte:02x}' for byte in sample_bytes)}` | `{', '.join(f'0x{value:04x}' for value in mode1_values)}` |")
    lines.append(f"| 2 | `{' '.join(f'{byte:02x}' for byte in sample_bytes)}` | `{', '.join(f'0x{value:08x}' for value in mode2_values)}` |")
    lines.append(f"| 3 | `{' '.join(f'{byte:02x}' for byte in sample_bytes)}` | `{', '.join(f'0x{value:08x}' for value in mode3_values)}` |")
    lines.append("")
    return "\n".join(lines)


def render_destination_fixture_report(data: bytes) -> str:
    def low16(value: int) -> int:
        return value & 0xFFFF

    def high16(value: int) -> int:
        return (value >> 16) & 0xFFFF

    def coord_decode(coord: int) -> dict[str, int]:
        word = coord & 0xFFFF
        row_index = word >> 12
        byte_pair_offset = (word & 0x00FF) * 2
        subbyte = (word >> 8) & 0x0F
        a001 = subbyte | (0x10 if subbyte else 0)
        return {
            "coord": word,
            "row_index": row_index,
            "byte_pair_offset": byte_pair_offset,
            "subbyte": subbyte,
            "a001": a001,
        }

    def clip_count(coord: int, count: int, band_remainder: int) -> int:
        row_index = coord_decode(coord)["row_index"]
        rows_here = band_remainder - row_index
        if rows_here < count:
            return ((count - rows_here) << 16) | (rows_here & 0xFFFF)
        return count & 0xFFFF

    sample_coords = [0x0000, 0x0001, 0x00FF, 0x0100, 0x0F00, 0x1000, 0x1234, 0x8ABC, 0xF0FF]
    clip_cases = [
        (0x0000, 5, 8),
        (0x3000, 5, 8),
        (0x7000, 5, 8),
        (0x8000, 5, 8),
        (0xA200, 10, 12),
    ]
    row_offsets = [i * 0x20 for i in range(16)]
    band_base = 0x100000
    object_payload_offset = 0x40
    buffer_base = 0x200000
    stride = 0x100

    lines = ["# IC30/IC13 Destination and Clipping Fixtures", ""]
    lines.append("These fixtures model the arithmetic in bitmap destination helpers `0x1f3d4`, `0x1f414`, and the main cases of `0x1f626`.")
    lines.append("They use synthetic render state so renderer tests can validate the arithmetic independently of a full page job.")
    lines.append("")

    lines.append("## Helper `0x1f3d4` Coordinate Decode")
    lines.append("")
    lines.append("Input `D1` is treated as a packed coordinate word. The helper computes:")
    lines.append("")
    lines.append("- `row_index = D1 >> 12`, used as an index into word table `0x7839f8`.")
    lines.append("- `byte_pair_offset = (D1 & 0xff) * 2`, added directly to the destination pointer.")
    lines.append("- `subbyte = (D1 >> 8) & 0x0f`; if nonzero, bit `0x10` is set before writing the low byte to MMIO `0xa001`.")
    lines.append("- destination pointer `A1 = 0x783a28 + row_offsets[row_index] + byte_pair_offset + A2`.")
    lines.append("")
    lines.append("Synthetic state for the fixture table below: `0x783a28 = 0x100000`, `A2 = 0x40`, and `row_offsets[i] = i * 0x20`.")
    lines.append("")
    lines.append("| Coordinate | Row index | Byte-pair offset | `0xa001` value | Expected `A1` |")
    lines.append("| ---: | ---: | ---: | ---: | ---: |")
    for coord in sample_coords:
        decoded = coord_decode(coord)
        expected_a1 = band_base + row_offsets[decoded["row_index"]] + decoded["byte_pair_offset"] + object_payload_offset
        lines.append(
            f"| `0x{coord:04x}` | {decoded['row_index']} | `0x{decoded['byte_pair_offset']:04x}` | `0x{decoded['a001']:02x}` | `0x{expected_a1:06x}` |"
        )
    lines.append("")

    lines.append("## Helper `0x1f414` Band Count Split")
    lines.append("")
    lines.append("After `0x1f3d4`, helper `0x1f414` clips the requested count in `D3` against `0x783a20 - row_index`.")
    lines.append("If the count crosses the band boundary, the returned longword packs `remaining_after_band` in the high word and `rows_in_this_band` in the low word.")
    lines.append("")
    lines.append("| Coordinate | Input count | `0x783a20` | Rows in this band | Remaining after band | Returned `D3` |")
    lines.append("| ---: | ---: | ---: | ---: | ---: | ---: |")
    for coord, count, band_remainder in clip_cases:
        row_index = coord_decode(coord)["row_index"]
        rows_here = band_remainder - row_index
        returned = clip_count(coord, count, band_remainder)
        lines.append(
            f"| `0x{coord:04x}` | {count} | {band_remainder} | {low16(returned)} | {high16(returned)} | `0x{returned:08x}` |"
        )
    lines.append("")

    lines.append("## Helper `0x1f626` Destination Cases")
    lines.append("")
    lines.append("Helper `0x1f626` repeats the same packed-coordinate decode, then chooses between current-band, shifted-in-band, and fallback-buffer destinations using `D2` and `0x783a20`.")
    lines.append("The table uses synthetic state: `0x783a28=0x100000`, `0x7810b4=0x200000`, `0x783a1c=0x100`, `0x783a20=8`, `A2=(coord & 0xff)*2`, and `row_offsets[i]=i*0x20`.")
    lines.append("")
    lines.append("| Case | Coordinate | Input `D2` | Input count `D3` | Expected branch | Expected `A1` | Returned `D2` | Returned `D3` |")
    lines.append("| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |")
    dest_cases = [
        ("current band/no D2", 0x1234, 0, 5),
        ("shifted current band", 0x3234, 2, 3),
        ("fallback buffer", 0x1234, 12, 5),
        ("band boundary split", 0x7002, 1, 4),
    ]
    band_remainder = 8
    for name, coord, d2_in, d3_in in dest_cases:
        decoded = coord_decode(coord)
        row = decoded["row_index"]
        a2 = decoded["byte_pair_offset"]
        if d2_in == 0:
            branch = "current band"
            a1 = band_base + row_offsets[row] + a2
            d2_out = d2_in
            d3_out = clip_count(coord, d3_in, band_remainder)
        elif row > d2_in:
            branch = "shifted current band"
            a1 = band_base + stride * d2_in + row_offsets[row] + a2
            d2_out = d2_in
            rows_here = band_remainder - d2_in - row
            if d3_in > rows_here:
                d3_out = ((d3_in - rows_here) << 16) | (rows_here & 0xFFFF)
            else:
                d3_out = d3_in
        else:
            branch = "fallback buffer"
            d2_out = d2_in - row
            a1 = buffer_base + stride * (row + d2_out) + a2
            d3_out = d3_in
        lines.append(
            f"| {name} | `0x{coord:04x}` | {d2_in} | {d3_in} | {branch} | `0x{a1:06x}` | {d2_out} | `0x{d3_out:08x}` |"
        )
    lines.append("")
    return "\n".join(lines)


def decode_parser_dispatch_entries(data: bytes, table_base: int, label: str, max_modes: int = 20) -> list[str]:
    lines = [f"## {label} pointer table @0x{table_base:06x}", ""]
    starts = [u32(data, table_base + i * 4) for i in range(max_modes)]
    entries: list[tuple[int, int, int, int, int]] = []
    for mode in range(max_modes - 1):
        start = starts[mode]
        end = starts[mode + 1]
        if not (0 <= start <= end <= len(data)):
            continue
        if start == end:
            continue
        lines.append(f"### Mode {mode}: `0x{start:06x}`..`0x{end:06x}`")
        lines.append("")
        lines.append("| Byte | Char | Next mode | Handler |")
        lines.append("| --- | --- | ---: | --- |")
        pos = start
        while pos + 6 <= end:
            byte = data[pos]
            next_mode = data[pos + 1]
            handler = u32(data, pos + 2)
            char = repr(chr(byte)) if 0x20 <= byte < 0x7f else f"control 0x{byte:02x}"
            handler_text = "" if handler == 0 else f"`0x{handler:06x}`"
            lines.append(f"| `0x{byte:02x}` | `{char}` | {next_mode} | {handler_text} |")
            entries.append((mode, byte, next_mode, handler, pos))
            pos += 6
        lines.append("")
    return lines


def parser_dispatch_table_report(data: bytes) -> str:
    lines = ["# IC30/IC13 Parser Dispatch Tables", ""]
    lines.append("Decoded from the main parser loop at `0x11774`.")
    lines.append("")
    lines.append("Each mode points to a contiguous range of six-byte entries:")
    lines.append("")
    lines.append("```text")
    lines.append("byte_to_match, next_mode, handler_long")
    lines.append("```")
    lines.append("")
    lines.append("A zero handler leaves the byte to generic/default handling. Nonzero handlers are called after the parser updates mode state.")
    lines.append("")
    lines.extend(decode_parser_dispatch_entries(data, 0x112a4, "normal parser"))
    lines.extend(decode_parser_dispatch_entries(data, 0x116f6, "alternate/data parser"))
    return "\n".join(lines)


def parser_modes(data: bytes, table_base: int, max_modes: int = 20) -> dict[int, list[tuple[int, int, int]]]:
    starts = [u32(data, table_base + i * 4) for i in range(max_modes)]
    modes: dict[int, list[tuple[int, int, int]]] = {}
    for mode in range(max_modes - 1):
        start = starts[mode]
        end = starts[mode + 1]
        if not (0 <= start <= end <= len(data)) or start == end:
            continue
        entries: list[tuple[int, int, int]] = []
        pos = start
        while pos + 6 <= end:
            entries.append((data[pos], data[pos + 1], u32(data, pos + 2)))
            pos += 6
        modes[mode] = entries
    return modes


def mode_prefixes(modes: dict[int, list[tuple[int, int, int]]], max_depth: int = 4) -> dict[int, list[tuple[int, ...]]]:
    prefixes: dict[int, list[tuple[int, ...]]] = {0: [()]}
    seen = {(0, ())}
    queue = [(0, ())]
    while queue:
        mode, prefix = queue.pop(0)
        if len(prefix) >= max_depth:
            continue
        for byte, next_mode, _handler in modes.get(mode, []):
            if next_mode == 0:
                continue
            if next_mode == mode:
                continue
            next_prefix = prefix + (byte,)
            existing = prefixes.get(next_mode, [])
            if existing:
                shortest = min(len(item) for item in existing)
                if len(next_prefix) > shortest:
                    continue
            key = (next_mode, next_prefix)
            if key in seen:
                continue
            seen.add(key)
            prefixes.setdefault(next_mode, []).append(next_prefix)
            queue.append((next_mode, next_prefix))
    return prefixes


def seq_text(seq: tuple[int, ...]) -> str:
    if not seq:
        return "(root)"
    parts: list[str] = []
    for byte in seq:
        if byte == 0x1b:
            parts.append("ESC")
        elif 0x20 <= byte < 0x7f:
            parts.append(chr(byte))
        else:
            parts.append(f"0x{byte:02x}")
    return " ".join(parts)


KNOWN_PCL_COMMANDS = {
    (0x1b, 0x45): "Printer reset",
    (0x1b, 0x39): "Clear horizontal margins",
    (0x1b, 0x59): "Display functions on",
    (0x1b, 0x5a): "Display functions off",
    (0x1b, 0x26, 0x6c, 0x58): "Number of copies",
    (0x1b, 0x26, 0x6c, 0x48): "Paper source / page eject",
    (0x1b, 0x26, 0x6c, 0x41): "Page size",
    (0x1b, 0x26, 0x6c, 0x50): "Page length in lines",
    (0x1b, 0x26, 0x6c, 0x4f): "Orientation",
    (0x1b, 0x26, 0x6c, 0x45): "Top margin",
    (0x1b, 0x26, 0x6c, 0x46): "Text length",
    (0x1b, 0x26, 0x6c, 0x4c): "Perforation skip",
    (0x1b, 0x26, 0x6c, 0x43): "VMI",
    (0x1b, 0x26, 0x6c, 0x44): "Lines per inch",
    (0x1b, 0x26, 0x61, 0x4c): "Left margin",
    (0x1b, 0x26, 0x61, 0x4d): "Right margin",
    (0x1b, 0x26, 0x61, 0x43): "Horizontal column position",
    (0x1b, 0x26, 0x61, 0x48): "Horizontal decipoint position",
    (0x1b, 0x26, 0x61, 0x52): "Vertical row position",
    (0x1b, 0x26, 0x61, 0x56): "Vertical decipoint position",
    (0x1b, 0x26, 0x6b, 0x48): "HMI",
    (0x1b, 0x26, 0x6b, 0x47): "Line termination mode",
    (0x1b, 0x26, 0x66, 0x53): "Push/pop cursor position",
    (0x1b, 0x26, 0x66, 0x59): "Macro ID",
    (0x1b, 0x26, 0x66, 0x58): "Macro control",
    (0x1b, 0x26, 0x64, 0x44): "Underline mode",
    (0x1b, 0x2a, 0x74, 0x52): "Raster resolution",
    (0x1b, 0x2a, 0x72, 0x41): "Start raster graphics",
    (0x1b, 0x2a, 0x72, 0x42): "End raster graphics",
    (0x1b, 0x2a, 0x62, 0x57): "Transfer raster row bytes",
    (0x1b, 0x2a, 0x63, 0x41): "Rectangle width dots",
    (0x1b, 0x2a, 0x63, 0x42): "Rectangle height dots",
    (0x1b, 0x2a, 0x63, 0x48): "Rectangle width decipoints",
    (0x1b, 0x2a, 0x63, 0x56): "Rectangle height decipoints",
    (0x1b, 0x2a, 0x63, 0x50): "Fill rectangle",
    (0x1b, 0x2a, 0x63, 0x44): "Assign font ID",
    (0x1b, 0x2a, 0x63, 0x46): "Font control",
    (0x1b, 0x28, 0x73, 0x50): "Primary spacing",
    (0x1b, 0x28, 0x73, 0x48): "Primary pitch",
    (0x1b, 0x28, 0x73, 0x56): "Primary point size",
    (0x1b, 0x28, 0x73, 0x53): "Primary style",
    (0x1b, 0x28, 0x73, 0x42): "Primary stroke weight",
    (0x1b, 0x28, 0x73, 0x54): "Primary typeface",
    (0x1b, 0x29, 0x73, 0x50): "Secondary spacing",
    (0x1b, 0x29, 0x73, 0x48): "Secondary pitch",
    (0x1b, 0x29, 0x73, 0x56): "Secondary point size",
    (0x1b, 0x29, 0x73, 0x53): "Secondary style",
    (0x1b, 0x29, 0x73, 0x42): "Secondary stroke weight",
    (0x1b, 0x29, 0x73, 0x54): "Secondary typeface",
}


def flattened_command_map(data: bytes, table_base: int, title: str) -> list[str]:
    modes = parser_modes(data, table_base)
    prefixes = mode_prefixes(modes)
    rows: list[tuple[tuple[int, ...], int, int, int, int]] = []
    for mode, entries in modes.items():
        mode_prefixes_for_entries = prefixes.get(mode)
        if mode_prefixes_for_entries is None:
            continue
        for prefix in mode_prefixes_for_entries:
            for byte, next_mode, handler in entries:
                seq = prefix + (byte,)
                rows.append((seq, mode, next_mode, handler, byte))

    lines = [f"## {title}", ""]
    lines.append("| Sequence | Mode | Next mode | Handler | Known meaning |")
    lines.append("| --- | ---: | ---: | --- | --- |")
    for seq, mode, next_mode, handler, _byte in sorted(rows, key=lambda item: (item[0], item[1], item[2], item[3])):
        handler_text = "" if handler == 0 else f"`0x{handler:06x}`"
        meaning = KNOWN_PCL_COMMANDS.get(seq, "")
        lines.append(f"| `{seq_text(seq)}` | {mode} | {next_mode} | {handler_text} | {meaning} |")
    lines.append("")
    return lines


def parser_command_map_report(data: bytes) -> str:
    lines = ["# IC30/IC13 Flattened PCL Command Map", ""]
    lines.append("Generated from parser dispatch pointer tables, using the shortest known prefix for each parser mode.")
    lines.append("Known meanings are assigned only when they directly match commands already listed in `notes/pcl4-language.md`.")
    lines.append("")
    lines.extend(flattened_command_map(data, 0x112a4, "Normal parser table @0x112a4"))
    lines.extend(flattened_command_map(data, 0x116f6, "Alternate/data parser table @0x116f6"))
    return "\n".join(lines)


def font_control_flow_report(data: bytes) -> str:
    def fmt_refs(refs: list[int]) -> str:
        if not refs:
            return "(none)"
        text = ", ".join(f"`0x{ref:06x}`" for ref in refs[:12])
        if len(refs) > 12:
            text += f", ... ({len(refs)} total)"
        return text

    table = 0x16DB6
    entries: list[tuple[int, int]] = []
    pos = table
    while True:
        target = u32(data, pos)
        value = u32(data, pos + 4)
        pos += 8
        if target == 0:
            default_target = value
            break
        entries.append((value, target))

    roles = {
        0: "if `0x782a92 != 2`, calls `0x179da(1)`, which walks 32 records under `0x782640` and calls `0x187fe` for each record id",
        1: "if `0x782a92 != 2`, calls `0x179da(0)`, the same all-record walk with the alternate `0x187fe` argument",
        2: "if `0x782a92 != 2`, calls `0x187fe(1)` for the current `0x782f2e` font id",
        3: "if `0x782a92 != 2`, calls `0x17b5c`; that helper uses current font id `0x782f2e` plus character/code word `0x782f30` to clear or replace one glyph record",
        4: "calls `0x17150`; if the current record exists and bit 6 is set, clears bit 6 and moves one count from `0x782786` back to `0x782782`",
        5: "calls `0x17108`; if the current record exists and bit 6 is clear, sets bit 6 and moves one count from `0x782782` to `0x782786`",
        6: "if `0x782a92 != 2`, calls `0x18180` and then `0x1b04c` for active/current font-resource housekeeping",
    }

    state_addresses = [
        (0x0078299E, "parser record cursor rewound by `0x15a56` and `0x16df6` before reading the parsed parameter"),
        (0x00782F2E, "current font id written by `ESC *c#D` and consumed by font-control helpers"),
        (0x00782F30, "current character/code word consumed by the value-3 helper `0x17b5c`"),
        (0x00782A92, "mode/status byte that suppresses font-control values 0, 1, 2, 3, and 6 when it equals `2`"),
        (0x00782640, "start of 32 current downloaded-font records, 10 bytes each"),
        (0x00782782, "unmarked/current downloaded-font count adjusted by `0x17108` and `0x17150`"),
        (0x00782786, "marked/current downloaded-font count adjusted opposite `0x782782`"),
        (0x00783140, "download payload byte budget used by `0x16c14` and lower payload readers"),
    ]

    routines = [
        (0x015A56, "`ESC *c#D` assign-font-id handler"),
        (0x016DF6, "`ESC *c#F` font-control dispatcher"),
        (0x0179DA, "all-record font-control walker"),
        (0x0187FE, "current-record release/delete wrapper"),
        (0x017B5C, "current character/glyph record clear helper"),
        (0x017108, "mark current downloaded record"),
        (0x017150, "unmark current downloaded record"),
        (0x018180, "active/current font-resource housekeeping helper"),
        (0x016C14, "downloaded font/resource payload add command"),
    ]

    lines = ["# IC30/IC13 Font ID and Font-Control Flow", ""]
    lines.append("Generated from the verified firmware image and focused disassembly around `0x15a56`, `0x16df6`, and the immediate font-control targets.")
    lines.append("This is the host-command edge for downloaded-font bookkeeping: `ESC *c#D` selects the current font id, while `ESC *c#F` dispatches control values that delete, mark, unmark, or refresh current downloaded-font records.")
    lines.append("")

    lines.append("## Assign Font ID")
    lines.append("")
    lines.append("| Handler | Firmware behavior | Reproduction meaning |")
    lines.append("| --- | --- | --- |")
    lines.append("| `0x15a56` (`ESC *c#D`) | rewinds parser record cursor `0x78299e` by six bytes, reads the parsed signed word at `+2`, stores its absolute value in `0x782f2e`, and maps `-32768` to `0x7fff` | subsequent downloaded-font control and payload commands operate on this normalized current font id |")
    lines.append("")

    lines.append("## Font-Control Jump Table")
    lines.append("")
    lines.append(f"The table at `0x{table:06x}` is decoded as `(target_long, value_long)` pairs terminated by target `0`; the terminal value is the default target `0x{default_target:06x}`.")
    lines.append("")
    lines.append("| `ESC *c#F` value | Target | Immediate ROM effect |")
    lines.append("| ---: | ---: | --- |")
    for value, target in sorted(entries):
        lines.append(f"| `{value}` | `0x{target:06x}` | {roles.get(value, '(unlabeled)')} |")
    lines.append(f"| other | `0x{default_target:06x}` | no-op return |")
    lines.append("")

    lines.append("## Related Routines")
    lines.append("")
    lines.append("| Routine | Role | Absolute JSR references |")
    lines.append("| ---: | --- | --- |")
    for routine, role in routines:
        lines.append(f"| `0x{routine:06x}` | {role} | {fmt_refs(jsr_abs_refs(data, routine))} |")
    lines.append("")

    lines.append("## State References")
    lines.append("")
    lines.append("| Address | Current role | Longword literal references |")
    lines.append("| ---: | --- | --- |")
    for address, role in state_addresses:
        lines.append(f"| `0x{address:08x}` | {role} | {fmt_refs(find_all(data, address.to_bytes(4, 'big')))} |")
    lines.append("")

    lines.append("## Current Reproduction Contract")
    lines.append("")
    lines.append("- A byte-stream reproduction must preserve the global current font id at `0x782f2e`; `ESC *c#D` normalization happens before `ESC *c#F`, `ESC (#X` / `ESC )#X`, and downloaded payload installation consult current records.")
    lines.append("- Font-control values `0`, `1`, `2`, `3`, and `6` are suppressed when `0x782a92 == 2`; values `4` and `5` still run the downloaded-record mark/unmark helpers.")
    lines.append("- The concrete payload-install path remains `0x16c14` -> `0x17026` -> `0x1719c` -> `0x1bc38`, but this report names the PCL command edge that selects which current downloaded-font records those lower helpers mutate.")
    lines.append("")
    return "\n".join(lines)


def host_byte_fetch_flow_report(data: bytes) -> str:
    def fmt_refs(refs: list[int]) -> str:
        if not refs:
            return "(none)"
        text = ", ".join(f"`0x{ref:06x}`" for ref in refs[:16])
        if len(refs) > 16:
            text += f", ... ({len(refs)} total)"
        return text

    state_addresses = [
        (0x007821CD, "fetch blocked / service-needed flag tested before all sources"),
        (0x00780E66, "buffer-source bitfield; bits are cleared as stacked sources drain"),
        (0x00780E3B, "forces immediate `D7=-1` return when `0x780e66` is set"),
        (0x00783E8C, "first LIFO byte count"),
        (0x00783E8E, "first LIFO byte pointer; bytes are read with predecrement"),
        (0x00782D76, "current data-chain/control pointer; field `+4` selects helper `0x9f6a` or end marker"),
        (0x00783E76, "second LIFO byte count"),
        (0x00783E78, "second LIFO byte pointer; bytes are read with predecrement"),
        (0x00783E54, "ring-buffer byte count"),
        (0x00783E56, "ring-buffer read pointer"),
        (0x00780E40, "direct hardware input mode selector"),
        (0x00780E2E, "alternate direct-input status/error accumulator"),
        (0x007828EC, "direct-input handshake state byte"),
        (0x007821C4, "direct-input timeout/service state cleared after successful handshakes"),
        (0x007821CC, "set while service helper `0x10cc(0x780202)` runs before retrying fetch"),
        (0x007828FA, "`0x8e01/0x8801/0x8c01` mode control shadow written to `0xaa01`"),
        (0x007828FB, "`0xfffee005/0xfffee001` mode control shadow written to `0xfffee009`"),
    ]

    lines = ["# IC30/IC13 Host Byte Fetch Flow", ""]
    lines.append("Generated from routine `0x0000a904`, its local branches through `0x0000abf0`, and absolute-call/state-reference scans of the verified firmware image.")
    lines.append("This report tracks the normalized byte source that feeds the PCL parser and raster/download payload readers. Names remain provisional where MMIO register roles are not board-confirmed.")
    lines.append("")

    lines.append("## Source Priority")
    lines.append("")
    lines.append("| Order | Entry/condition | Firmware behavior | Reproduction meaning |")
    lines.append("| ---: | --- | --- | --- |")
    lines.append("| 1 | `0x7821cd != 0` at `0xa904` | branches to `0xaa88`, sets `0x7821cc`, calls `0x10cc(0x780202)`, clears `0x7821cc`, then retries `0xa904` | service/error work can run before any byte source is consumed |")
    lines.append("| 2 | `0x780e66 != 0` and `0x780e3b != 0` | returns `D7 = -1` immediately | callers must treat negative `D7` as no-byte/end/error, as several payload readers already do |")
    lines.append("| 3 | `0x783e8c != 0` | reads byte from `--0x783e8e`, decrements `0x783e8c`, returns | first stacked pushback/source buffer has priority over live hardware input |")
    lines.append("| 4 | `(*0x782d76)+4 != 0` | if field is not `-1`, calls `0x9f6a` and returns; if field is `-1`, clears it, calls `0xe22c`, and retries | current data-chain source can supply bytes or signal a chain transition before other buffers |")
    lines.append("| 5 | `0x783e76 != 0` | reads byte from `--0x783e78`, decrements `0x783e76`, returns | second stacked byte source is consumed after the data-chain source |")
    lines.append("| 6 | `0x780e40 == 0` and `0x783e54 != 0` | reads byte from ring pointer `0x783e56`, wraps after `0x783e53` back to `0x783a4c`, decrements `0x783e54`, returns | buffered ring input is used before direct hardware fallback when direct mode is not selected |")
    lines.append("| 7 | `0x780e40 == 1` | enters direct path `0xa9f0` using short MMIO registers `0x8e01`, `0x8801`, `0x8c01`, plus `0xa601`/`0xaa01` handshakes | one hardware input backend polls status bit 4, reads one byte, waits for acknowledge bit 0 to clear, then toggles control lines |")
    lines.append("| 8 | `0x780e40 != 0 && != 1` | enters direct path `0xaaa6` using long MMIO registers `0xfffee005`, `0xfffee001`, `0xfffee009` | alternate hardware input backend polls ready/error bits, reads one byte, and updates a separate control shadow |")
    lines.append("")

    lines.append("## Direct Hardware Input Modes")
    lines.append("")
    lines.append("| Selector | Status/data/control evidence | Success path | Timeout/error path |")
    lines.append("| --- | --- | --- | --- |")
    lines.append("| `0x780e40 == 1` | `0xa9f4` reads `0x8e01` bit `0x10`; `0xaa06` reads data byte from `0x8801`; `0xaa26` waits for `0x8c01` bit 0 to clear; `0xaa3a..0xaa64` writes `0xa601` and `0xaa01` from shadow `0x7828fa` | byte is masked to 8 bits in `D7`; `0x1a` is reported through `0x9ec0` and preserved as `0x1a`; handshake clears `0x7828ec` and `0x7821c4` | if `0x8e01.4` is not seen before `D0=0x2710` expires, branches through service helper at `0xaa88` and retries |")
    lines.append("| `0x780e40 != 0 && != 1` | `0xaae4` reads `0xfffee005`; bit 0 means data ready; bits 7/6 are error/status cases; `0xab08` reads data byte from `0xfffee001`; `0xab2e..0xab44` writes shadow `0x7828fb` to `0xfffee009` | byte is masked to 8 bits in `D7`; `0x1a` is reported through `0x9ec0` and preserved as `0x1a`; success sets `0x7828ec=1`, sets control-shadow bit 6, and clears `0x7821c4` | bit 7 ORs `0x80` into `0x780e2e`; bit 6 ORs `0x40` into `0x780e2e`; timeout or status/error branches through service helper at `0xab70` and retries |")
    lines.append("| cleanup helper `0xab8e` | called from `0x35de` after helper `0xa39a` returns zero; mode 1 toggles `0xaa01`/`0xa601` from `0x7828fa`, mode 2 applies `bclr #0x40,D0` to `0x7828fb` before writing `0xfffee009` | normalizes handshake state after external service code | not a byte source by itself |")
    lines.append("")

    lines.append("## Callers and Payload Consumers")
    lines.append("")
    lines.append(f"- Direct absolute `JSR 0xa904` callers: {fmt_refs(jsr_abs_refs(data, 0x0000A904))}.")
    lines.append("- Confirmed caller roles from focused listings:")
    lines.append("  - `0xda9a`, `0xdaa6`, and `0xdab2`: normal ESC-aware parser byte wrapper.")
    lines.append("  - `0xdace` and `0xdada`: `0x1a 0x58` control probe used by raster/download payload paths.")
    lines.append("  - `0x12142` / `0x12152`, `0x124bc` / `0x124cc`, and `0x12582` / `0x12592`: parser payload/text repeat readers that also treat `0x1a 0x58` specially.")
    lines.append("  - `0x138fa` / `0x13904`: raster payload copy path `0x138de` that stores host bytes into queued raster row objects.")
    lines.append("  - `0x168dc`, `0x168fe`, `0x16960`, `0x1697a`, `0x169ca`, and `0x169e0`: downloaded/font-resource payload readers that keep continuation state under `0x7827c6..0x7827d8` and byte budget `0x783140`.")
    lines.append("")

    lines.append("## State Reference Scan")
    lines.append("")
    lines.append("| Address | Current role | Longword literal references |")
    lines.append("| ---: | --- | --- |")
    for address, role in state_addresses:
        lines.append(f"| `0x{address:08x}` | {role} | {fmt_refs(find_all(data, address.to_bytes(4, 'big')))} |")
    lines.append("")

    lines.append("## Current Reproduction Contract")
    lines.append("")
    lines.append("- A byte-stream emulator can feed parser/imaging work above `0xa904` by returning normalized `D7` bytes in the same order as the priority table, while preserving `D7=-1` as a no-byte/end/error return for callers that test it. `tools/render_fixture_harness.py` now has executable `0xa904` source-priority fixtures covering the no-byte return, service retry, first LIFO, data-chain end retry, second LIFO, ring-buffer mode, and both direct hardware modes including direct-mode `0x1a` reporting and mode-2 control-shadow bit 6.")
    lines.append("- Exact host-interface emulation still needs board/manual correlation for `0x8e01/0x8801/0x8c01`, `0xa601/0xaa01`, and `0xfffee005/0xfffee001/0xfffee009`; current ROM evidence only proves the polling, data, handshake, and status-bit behavior.")
    lines.append("- Both direct modes special-case input byte `0x1a` through `0x9ec0`, and higher-level payload readers also interpret `0x1a 0x58` by calling `0xd99a`; byte-stream reproduction must preserve that control path rather than treating all payload bytes as opaque.")
    lines.append("- Font payload reader `0x168dc` copies linear downloaded-font bytes to `A4`, decrements byte budget `0x783140` only for stored payload bytes, and saves continuation state in `0x7827c6/0x7827ca/0x7827d2` when the budget expires. Reader `0x16942` handles split odd-width glyph planes: `A4` receives `rows * prefix_span` bytes, `A3 = A4 + rows * prefix_span` receives one trailing byte per row, and continuation state also records `0x7827ce`, `0x7827d6`, and `0x7827d8`. `0x172c0` scans 10-byte current downloaded-font records under `0x782640..0x782776`, returning existing/free/full statuses; `0x16c14` uses that result to replace an existing payload through `0x1887a`, clear matching continuation state, or install a new payload and update candidate counters/cursors. `0x170be` maps a low-24-bit payload pointer back to a current-record slot and id; `0x17108` sets record flag bit 6 and transfers a count from `0x782782` to `0x782786` for an unmarked current payload record; `0x17150` clears that bit and transfers the count back. `0x15a56` normalizes the current font id from `ESC *c#D`, and `0x16df6` dispatches `ESC *c#F` values while suppressing values `0`, `1`, `2`, `3`, and `6` when `0x782a92 == 2`. `0x16fae` walks the validation table at `0x16eae`, then copies up to 16 optional symbol bytes through `0x1599c` into `0x782842` and stores the count at `0x782856`; `0x17362` sets staged type byte `+0x0c` and `0x7827ba`, `0x17026` stages record type `0x15` and allocation size `((0x7827ba << 2) + 0x9b) >> 6`, and `0x1719c` copies the sparse staged header plus optional symbol bytes into the allocated record. `tools/render_fixture_harness.py` now has executable fixtures for both readers, record bookkeeping/lookup/marking/unmarking, font-id/control dispatch, validation/symbol-byte staging, table-driven staged-header predicate side effects, payload-backed inline map/render, and allocation/header initialization, including `0x1a 0x58` handling, continuation checkpoints, replacement/free-slot updates, no-slot budget skip, count transfer, validation failure, zero-budget validation, table-driven predicate clamps, payload-backed inline map/render, and optional symbol-byte append offsets.")
    lines.append("")
    return "\n".join(lines)


def direct_control_code_flow_report(data: bytes) -> str:
    def fmt_refs(refs: list[int]) -> str:
        if not refs:
            return "(none)"
        text = ", ".join(f"`0x{ref:06x}`" for ref in refs[:16])
        if len(refs) > 16:
            text += f", ... ({len(refs)} total)"
        return text

    state_addresses = [
        (0x0078299E, "parser six-byte record cursor rewound by parsed cursor-position handlers"),
        (0x00782A57, "right-margin/line-limit latch set when horizontal cursor reaches `0x782dda`"),
        (0x00782A58, "pending previous-width latch cleared before text span flushes and set by BS"),
        (0x00782A5A, "latched previous text width used by BS when alternate metrics flag is set"),
        (0x00782A6D, "printable/pending text flag cleared by control-code cursor moves; FF sets it to `0xff` after page eject"),
        (0x00782C8A, "current horizontal text cursor, reset by CR and changed by HT/BS"),
        (0x00782C8E, "current vertical text cursor, advanced by LF and reset/recomputed by FF"),
        (0x00782C96, "bottom of the `ESC &f#S` cursor stack"),
        (0x00782D36, "next-free pointer and upper bound for the `ESC &f#S` cursor stack"),
        (0x00782DB8, "horizontal page extent used to clamp HT and horizontal positioning"),
        (0x00782DC6, "vertical upper bound used by `ESC &a#R/#V` and cursor-stack pop clamps"),
        (0x00782DCA, "vertical lower bound used by helper `0xf6e2`"),
        (0x00782DCE, "top/vertical offset added by FF helper `0xf124` and absolute `ESC &a#R/#V` positioning"),
        (0x00782DD6, "left-margin/default horizontal cursor copied into `0x782c8a` by CR helper `0xf06e`"),
        (0x00782DDA, "right-margin/current horizontal limit used by HT and helper `0xf4ca`"),
        (0x0078315C, "default horizontal motion / HMI value used by HT and BS"),
        (0x00783160, "line advance / VMI value added by LF and FF helpers"),
        (0x00783184, "pending text span flush enable tested by `0xf34a`"),
        (0x0078318E, "alternate previous-width mode tested by BS"),
        (0x0078318F, "line-termination mode byte written by `ESC &k#G` and tested by CR/LF/FF"),
        (0x00783191, "vertical overflow recovery enable tested by `0xf36c`"),
    ]

    lines = ["# IC30/IC13 Direct Control-Code Flow", ""]
    lines.append("Generated from handlers `0xf02c..0xf55e`, line-termination handler `0xedf8`, and state-reference scans of the verified firmware image.")
    lines.append("This report tracks direct parser mode-0 control codes that change cursor/page state before text or raster objects are queued.")
    lines.append("")

    lines.append("## Line-Termination Mode")
    lines.append("")
    lines.append("PCL `ESC &k#G` reaches handler `0xedf8`, which stores absolute values into `0x78318f`:")
    lines.append("")
    lines.append("| `#` | Stored byte | Firmware effect bits | PCL meaning |")
    lines.append("| ---: | ---: | --- | --- |")
    lines.append("| 0 | `0x00` | no extra CR/LF/FF coupling | CR=CR, LF=LF, FF=FF |")
    lines.append("| 1 | `0x80` | CR tests bit 7 and also calls LF advance | CR=CR+LF |")
    lines.append("| 2 | `0x60` | LF tests bit 6 and FF tests bit 5, both also call CR reset | LF=CR+LF, FF=CR+FF |")
    lines.append("| 3 | `0xe0` | bits 7, 6, and 5 all set | CR=CR+LF, LF=CR+LF, FF=CR+FF |")
    lines.append("")

    lines.append("## Direct Control Handlers")
    lines.append("")
    lines.append("| Byte | Handler | Confirmed side effects | Pixel-reproduction consequence |")
    lines.append("| ---: | ---: | --- | --- |")
    lines.append("| CR `0x0d` | `0xf02c` | calls CR helper `0xf06e`, then `0xf34a`; if `0x78318f.7` is set, calls LF helper `0xf0b2` | resets horizontal text cursor to left/default margin and may also advance vertically depending on `ESC &k#G` |")
    lines.append("| LF `0x0a` | `0xf08c` | if `0x78318f.6` is set, calls CR helper `0xf06e`; always calls `0xf34a` and LF helper `0xf0b2` | advances vertical cursor by line advance `0x783160`, with optional horizontal reset |")
    lines.append("| FF `0x0c` | `0xf0f0` | if `0x78318f.5` is set, calls CR helper `0xf06e`; calls `0xf34a`, ensures page root through `0x10084`, calls page/eject helper `0xf124`, then writes `0x782a6d = 0xff` | finalizes current page/root state and recomputes vertical cursor for the next page context, with optional horizontal reset |")
    lines.append("| HT `0x09` | `0xf1cc` | converts default HMI `0x78315c`; computes next eight-column stop from `0x782c8a - 0x782dd6`, clamps against `0x782dda` or `0x782db8 << 16`, writes `0x782c8a`, then calls `0xd8fc` or `0xd4ac` for active context span update | horizontal cursor jumps to firmware tab stop and can flush/update text span bounds before the next printable byte |")
    lines.append("| BS `0x08` | `0xf2a8` | subtracts either previous width `0x782a5a << 16` when `0x78318e` is set or default HMI `0x78315c`; clamps at `0` and crossing `0x782dd6`; writes `0x782c8a`, sets `0x782a58=1`, clears `0x782a57/0x782a6d`, then calls `0xd8fc` or `0xd4ac` | horizontal cursor backs up using current text metrics while preserving a pending previous-width state for the following printable character |")
    lines.append("| `ESC &a#C` | `0xf39e` | converts parsed decimal columns through current HMI `0x78315c`, scales through helpers `0x332ee`/`0x3324a`/`0x104d8`, and commits through `0xf4ca` using parsed-record bit 0 as the relative flag | column positioning changes horizontal text/raster placement in HMI units with the same horizontal clamps/span updates as HT/BS |")
    lines.append("| `ESC &a#H` | `0xf416` | converts parsed decipoints as five packed subunits per decipoint, then commits through `0xf4ca` using parsed-record bit 0 as the relative flag | horizontal decipoint positioning maps host coordinates into 300 dpi twelfths before object placement |")
    lines.append("| `ESC &a#R` | `0xf560` | ensures a page root, masks the parsed flag to bit 0, adds fractional `0.7200` before VMI scaling for absolute rows, converts through current VMI `0x783160`, commits through `0xf6e2`, calls overflow recovery helper `0x1048c` for relative moves, and clamps absolute rows to `0x782dc6` | row positioning uses VMI units and has a firmware absolute-row bias that must be reproduced before text/raster queuing |")
    lines.append("| `ESC &a#V` | `0xf60a` | converts parsed decipoints as five packed subunits per decipoint, commits through `0xf6e2` using parsed-record bit 0 as the relative flag, and clamps to `0x782dc6` | vertical decipoint positioning maps host coordinates into the same vertical cursor used by text and raster start state |")
    lines.append("| `ESC &f0S` / `ESC &f1S` | `0xf75e` | selector `0` pushes `0x782c8a` plus `0x782c8e + 0x782dbe` as an 8-byte stack entry while `0x782d36` is below the upper bound; selector `1` pops while the pointer is above `0x782c96`, restores horizontal position clamped to `0x782db8 - 1/12`, restores vertical position after subtracting `0x782dbe` and clamping to `0x782dc6 - 1/12`, clears `0x782a57/0x782a6d`, and flushes pending spans when `0x783184` is set | cursor push/pop is part of placement state and can change subsequent text/raster coordinates after page size, orientation, or margins have changed |")
    lines.append("")

    lines.append("## Shared Helpers")
    lines.append("")
    lines.append("| Helper | Confirmed behavior |")
    lines.append("| ---: | --- |")
    lines.append("| `0xf06e` | copies `0x782dd6` to `0x782c8a`, clears `0x782a57` and `0x782a6d` |")
    lines.append("| `0xf34a` | clears `0x782a58`; if `0x783184` is nonzero, flushes pending text span through `0x12714` and `0x126e2` |")
    lines.append("| `0xf0b2` | ensures page root through `0x10084`, adds `0x783160` to `0x782c8e` via `0x10518`, calls `0xf36c`, optionally calls `0x1048c`, and clears `0x782a6d` |")
    lines.append("| `0xf124` | calls page-root finalize `0xff1e`, derives a fixed-point vertical value from `0x783160`, constants `0x12` and `0x19`, and `0x782dce`, writes `0x782c8e`, and clears `0x782a6d` |")
    lines.append("| `0xf36c` | compares vertical cursor `0x782c8e` against limit/state `0x782dc2`; when `0x783191` is set and limit is exceeded, calls `0xf124` and returns zero |")
    lines.append("| `0xf4ca` | shared horizontal-position commit helper used by ESC-positioning handlers; optionally adds to `0x782c8a`, clamps between `0` and `0x782db8 << 16`, writes `0x782c8a`, updates `0x782a57`, clears `0x782a6d`, and calls `0xd8fc` or `0xd4ac` |")
    lines.append("| `0xf6e2` | shared vertical-position commit helper used by `ESC &a#R/#V`; ensures a page root, clears/flushes pending text state through `0xf34a`, adds either the current vertical cursor or top offset `0x782dce`, clamps against lower bound `0x782dca`, writes `0x782c8e`, and returns the written cursor |")
    lines.append("")

    lines.append("## State Reference Scan")
    lines.append("")
    lines.append("| Address | Current role | Longword literal references |")
    lines.append("| ---: | --- | --- |")
    for address, role in state_addresses:
        lines.append(f"| `0x{address:08x}` | {role} | {fmt_refs(find_all(data, address.to_bytes(4, 'big')))} |")
    lines.append("")

    lines.append("## Current Reproduction Contract")
    lines.append("")
    lines.append("- A byte-stream model must apply `ESC &k#G` before interpreting CR/LF/FF because the firmware stores the mode as bit flags in `0x78318f` and the direct control handlers test those bits at runtime.")
    lines.append("- CR/LF/FF/HT/BS do not only change cursor coordinates; they can flush pending text spans, ensure/finalize page roots, and invoke the same context span update routines `0xd4ac` / `0xd8fc` used after printable text.")
    lines.append("- Axis names remain provisional, but `tools/render_fixture_harness.py` now has synthetic state fixtures for the line-termination map plus CR/LF/FF/HT/BS cursor/page effects, `ESC &f#S` cursor stack push/pop and clamp behavior, `ESC &a#C/#H/#R/#V` cursor-position conversion/relative/clamp behavior, narrow byte-stream fixtures for `ESC &k1G`+CR, `ESC &k2G`+LF, and `ESC &k0G`+HT/BS, a mixed `ESC &k1G!\\r!` fixture that applies CR+LF before queueing the second printable glyph, and a mixed `!\\x1bE` fixture that applies reset publication/clear state after queued text and has a page-record allocator/bridge variant for the pre-reset glyph. The remaining step is expanding this into the full firmware parser path with real page-object allocation.")
    lines.append("")
    return "\n".join(lines)


def esc_e_reset_flow_report(data: bytes) -> str:
    def fmt_refs(refs: list[int]) -> str:
        if not refs:
            return "(none)"
        text = ", ".join(f"`0x{ref:06x}`" for ref in refs[:16])
        if len(refs) > 16:
            text += f", ... ({len(refs)} total)"
        return text

    state_addresses = [
        (0x007810B2, "reset/environment gate tested by `0xcc70`; when clear, reset clears alternate/data parser mode"),
        (0x00782C18, "alternate/data parser mode cleared by `0xcc70` and again by parser-state reset `0xe146`"),
        (0x00783170, "raster graphics state block reset by `0xcc70`"),
        (0x00782DA3, "orientation byte cleared by the main `0xcc70` environment rebuild path"),
        (0x00782DCE, "top/vertical offset recomputed as `0x96 - 0x782dbe` during reset/page-size rebuild"),
        (0x00782DD0, "related vertical/page offset word cleared during reset/page-size rebuild"),
        (0x0078315C, "HMI/default horizontal motion recomputed by `0xcbd4` from current font metrics"),
        (0x0078318E, "alternate previous-width/text-metric flag refreshed by `0xcbd4`"),
        (0x00782F06, "primary/secondary glyph-map selector cleared by `0xcbd4`"),
        (0x00782F08, "active primary symbol word snapshot copied from `0x783144` by `0xcbd4`"),
        (0x00782F0A, "active secondary symbol word snapshot copied from `0x783146` by `0xcbd4`"),
        (0x00782D76, "current parser/data-chain pointer reset to `0x782d3e` by `0xe146`"),
        (0x00782D7A, "current parser/data-chain object pointer cleared by `0xe146`"),
        (0x00783164, "parsed-command selector/current state word cleared by `0xe146`"),
        (0x00782A92, "parser/page finalization state cleared by `0xe146`; also tested by `0xff1e`"),
        (0x00782A93, "top-level `ESC E` completion/status byte cleared after `0xe146`"),
        (0x00782A94, "saved command/data key used by `0xff1e` when finalizing a partial page"),
        (0x00783196, "text accumulation byte cleared by `0xe146`"),
        (0x00783197, "text accumulation byte cleared by `0xe146`"),
        (0x00783198, "text accumulation byte cleared by `0xe146`"),
        (0x00783199, "text accumulation byte cleared by `0xe146`"),
        (0x00782C1E, "base of eight 10-byte parser/control records cleared by `0xe146`"),
        (0x00782C6E, "parser/control record cursor reset to `0x782c1e` by `0xe146`"),
        (0x0078297A, "current page root finalized or cleared by `0xff1e`, called early by `0xcc70`"),
        (0x00780EA6, "current page/control pool record published by `0xff1e` finalization path"),
        (0x00782996, "page/control publication flag set by `0xff1e` finalization path"),
    ]

    lines = ["# IC30/IC13 ESC E Reset Flow", ""]
    lines.append("Generated from `0xcc52`, `0xcc70`, helper windows around `0xcbd4`, `0xcda2`, `0xe146`, and the page-root finalizer `0xff1e` in the verified firmware image.")
    lines.append("This report tracks the host-visible PCL software reset boundary. Names remain provisional where the underlying helper routines are not fully decoded.")
    lines.append("")

    lines.append("## Entry Sequence")
    lines.append("")
    lines.append("| Step | Firmware evidence | Confirmed reset role |")
    lines.append("| ---: | --- | --- |")
    lines.append("| 1 | `0xcc52 -> jsr 0xcc70` | performs the main environment/page/raster reset work |")
    lines.append("| 2 | `0xcc5c -> bsr 0xcbd4` | refreshes current-font metric state used by text motion after reset |")
    lines.append("| 3 | `0xcc60 -> jsr 0xe146` | resets parser/data-chain state and clears transient parser records |")
    lines.append("| 4 | `0xcc66 -> clr.b 0x782a93` | clears a reset/status byte after parser reset completes |")
    lines.append("")

    lines.append("## Main Environment Reset `0xcc70`")
    lines.append("")
    lines.append("- Loads the raster graphics state block base `0x783170` into `A5`.")
    lines.append("- If `0x7810b2` is clear, clears alternate/data parser mode byte `0x782c18` before any page work.")
    lines.append("- Calls direct-control text flush helper `0xf34a`, page-root finalizer `0xff1e`, and active page/control-record wait helper `0x9ac2`.")
    lines.append("- In the normal environment rebuild path, clears orientation byte `0x782da3`, calls `0xcda2`, `0xf952`, `0xf9ac`, and `0xf87e`, then recomputes `0x782dce = 0x96 - 0x782dbe` and clears `0x782dd0`.")
    lines.append("- Calls follow-up environment/font/page helpers `0xea16`, `0xe9ba`, `0xf8fc`, `0xfe54`, `0x12b96`, and `0x103ea`.")
    lines.append("- Reinitializes raster state at `0x783170`: clears byte `+0x12`, word `+0x00`, and long `+0x0a`; writes word `+0x08 = 3` and word `+0x0e = 4`; derives word `+0x10` from page extent `0x782db4`, baseline word `+0x00`, and scale word `+0x08`.")
    lines.append("- If `0x7810b2` is clear and `0x780e3c == 1`, it copies `0x7821a2` to `0x780e8f` and ORs bit `1` into `0x780e26` via helper `0x9b5e`; otherwise it can route through `0x1bba6` before the same rebuild path.")
    lines.append("")

    lines.append("## Font Metric Refresh `0xcbd4`")
    lines.append("")
    lines.append("- Starts from current-font context base `0x782ee6` and clears glyph-map selector `0x782f06`.")
    lines.append("- If context byte `+4` is clear, copies source byte `+0x19` into `0x78318e`, converts source word `+0x1a` through helpers `0x3324a` and `0x104d8`, and stores the result in HMI/default-motion longword `0x78315c`.")
    lines.append("- If context byte `+4` is set, copies source byte `+0x21` into `0x78318e`, converts source longword at `+0x24` through `0x10550`, and stores the result in `0x78315c`.")
    lines.append("- Copies active symbol words `0x783144` and `0x783146` into requested/snapshot words `0x782f08` and `0x782f0a`.")
    lines.append("")

    lines.append("## Parser/Data Reset `0xe146`")
    lines.append("")
    lines.append("- Sets current data-chain pointer `0x782d76` to base `0x782d3e`, calls helper `0xe1e4`, then clears current object pointer `0x782d7a`.")
    lines.append("- Clears selector/state word `0x783164`, alternate/data parser bytes `0x782c18` and `0x782c19`, page/parser state byte `0x782a92`, and text accumulation bytes `0x783196..0x783199`.")
    lines.append("- Clears eight 10-byte records starting at `0x782c1e` and resets cursor pointer `0x782c6e` to `0x782c1e`.")
    lines.append("- Calls `0xe996(0x782ee2, 0x78319a, 0x7831a2)`, then calls `0xdf80` to clear command/data pool records whose byte `+0x0a` is zero.")
    lines.append("- Helper `0xe1e4` walks data-chain records from `0x782d76` through `0x782d68`, marks byte `+8 = 4`, clears byte `+9`, frees any `+0x0a` 0x100-byte allocation through `0x18b4`, and clears the allocation pointer.")
    lines.append("")

    lines.append("## Page-Root Finalize Hook `0xff1e`")
    lines.append("")
    lines.append("- `0xcc70` calls `0xff1e` before rebuilding the print environment. This is the ROM hook that matches the PCL requirement that `ESC E` prints/finalizes a partial page rather than merely discarding it.")
    lines.append("- If current page root `0x78297a` is null, or its byte `+4` is not `1`, `0xff1e` clears `0x78297a` and returns.")
    lines.append("- If parser/page state `0x782a92 == 1` and root flags permit more work, it uses saved key `0x782a94`, may call `0xe4f4`, re-enters parser loop `0x11774`, and ensures a page root through `0x10084` before continuing.")
    lines.append("- The final publication path clears transient bytes `0x78297e`, `0x782c72`, and `0x782c73`, updates root fields, copies the root's backing pool record to `0x780ea6`, sets `0x782996 = 1`, and then clears `0x78297a`.")
    lines.append("")

    lines.append("## State Reference Scan")
    lines.append("")
    lines.append("| Address | Current reset role | Longword literal references |")
    lines.append("| ---: | --- | --- |")
    for address, role in state_addresses:
        lines.append(f"| `0x{address:08x}` | {role} | {fmt_refs(find_all(data, address.to_bytes(4, 'big')))} |")
    lines.append("")

    lines.append("## Current Reproduction Contract")
    lines.append("")
    lines.append("- A byte-stream model must treat `ESC E` as a page/environment boundary: flush pending text spans, run the page-root finalization path, rebuild page geometry/font metrics, reset raster graphics state, and clear parser/data-chain state.")
    lines.append("- The ROM evidence distinguishes `ESC E` from a simple hard clear: `0xff1e` can publish/finalize the current page root before `0x78297a` is cleared.")
    lines.append("- `tools/render_fixture_harness.py` now has synthetic `ESC E` byte-stream fixtures for valid-page-root publication and missing-root clearing, plus a mixed `!\\x1bE` fixture that applies valid-root reset after queued text. Exact reset reproduction still needs fixtures that start from parser-produced page objects and compare the resulting finalized page/control records.")
    lines.append("")
    return "\n".join(lines)


def page_geometry_table_report(data: bytes) -> str:
    word_tables = [
        ("height_or_vertical_extent", 0x00A112, "read by `0x009d16`, stored at `0x782db4` by `ESC &l#A`"),
        ("width_or_horizontal_extent", 0x00A128, "read by `0x009d4e`, stored at `0x782db2` by `ESC &l#A`"),
        ("landscape_margin_table", 0x00A13E, "read by `0x009d86`; used when orientation byte `0x782da3` is nonzero"),
        ("portrait_margin_table", 0x00A154, "read by `0x009dbe`; used when orientation byte `0x782da3` is zero"),
    ]
    internal_codes = list(range(0x0B))
    pcl_code_notes = {
        0x00: "default/legacy; also PCL 80 maps to internal `0x88`, masked here to 8",
        0x01: "PCL page size 26",
        0x02: "PCL page size 2",
        0x05: "PCL page size 3",
        0x06: "PCL page size 1",
        0x07: "PCL 81 maps to internal `0x87`, masked here to 7",
        0x08: "PCL 80 maps to internal `0x88`, masked here to 8",
        0x09: "PCL 90 maps to internal `0x89`, masked here to 9",
        0x0A: "PCL 91 maps to internal `0x8a`, masked here to 10",
    }

    lines = ["# IC30/IC13 Page Geometry Lookup Tables", ""]
    lines.append("The lookup routines at `0x009d16`, `0x009d4e`, `0x009d86`, and `0x009dbe` mask the page-code argument with `0x7f` and accept indexes `0..10`.")
    lines.append("Values are decoded as big-endian words from the firmware image. Table names are provisional until each consumer is fully traced.")
    lines.append("")
    lines.append("| Internal index | PCL mapping note | a112 / `0x9d16` | a128 / `0x9d4e` | a13e / `0x9d86` | a154 / `0x9dbe` |")
    lines.append("| ---: | --- | ---: | ---: | ---: | ---: |")
    for index in internal_codes:
        values = [u16(data, base + index * 2) for _name, base, _desc in word_tables]
        note = pcl_code_notes.get(index, "")
        lines.append(
            f"| {index} | {note} | {values[0]} | {values[1]} | {values[2]} | {values[3]} |"
        )
    lines.append("")
    lines.append("## Consumers")
    lines.append("")
    for name, base, desc in word_tables:
        lines.append(f"- `{name}` @`0x{base:06x}`: {desc}.")
    lines.append("- `ESC &l#A` handler `0x00fc74` maps PCL page-size values `1`, `2`, `3`, `26`, `80`, `81`, `90`, and `91` to internal page codes, writes `0x782da2`, stores width at `0x782db2` through `0x009d4e`, stores height at `0x782db4` through `0x009d16`, and then recomputes orientation-dependent extents.")
    lines.append("- `ESC &l#O` handler `0x010220` accepts only absolute values `0` and `1`, writes orientation byte `0x782da3`, calls the same margin/extent helpers, and reloads four orientation threshold words through `0x0103ea`.")
    lines.append("- `0x009e56` computes `(0x051f - floor(argument / 2)) mod 16` through signed remainder helper `0x033238`; `ESC &l#A` feeds it the `0x782db4` table value and stores the result at `0x782dc0`.")
    lines.append("- Coordinate helpers at `0x0104d8..0x010550` convert between a packed 12-subunit fixed-point form and integer coordinates; raster code uses these helpers around `0x0105d0..0x010758`.")
    lines.append("")
    return "\n".join(lines)


def decode_startup_tables(data: bytes) -> str:
    lines = ["# IC30/IC13 Startup Tables", ""]
    lines.append("## Timing/control table at 0x0000048e")
    lines.append("")
    count = int.from_bytes(data[0x48e:0x490], "big")
    lines.append(f"count word: 0x{count:04x} ({count + 1} writes)")
    pos = 0x490
    for i in range(count + 1):
        value = int.from_bytes(data[pos : pos + 2], "big")
        delay = int.from_bytes(data[pos + 2 : pos + 6], "big")
        lines.append(f"{i:02d}  @{pos:06x}  a400=0x{value:04x}  delay=0x{delay:08x}")
        pos += 6
    lines.append("")
    lines.append("## Trampoline destination table at 0x000004c0")
    lines.append("")
    count = int.from_bytes(data[0x4c0:0x4c2], "big")
    lines.append(f"count word: 0x{count:04x} ({count + 1} JMP stubs copied)")
    pos = 0x4c2
    for i in range(count + 1):
        dest = int.from_bytes(data[pos : pos + 4], "big")
        lines.append(f"{i:02d}  RAM stub @0x{0x780000 + i * 6:06x} -> 0x{dest:06x}")
        pos += 4
    lines.append("")
    return "\n".join(lines)


ABS_RE = re.compile(r"\$([0-9a-f]{4,8})(?:\.([wlb]))?")


def absolute_reference_report(disasm_text: str) -> str:
    counts: Counter[int] = Counter()
    examples: dict[int, str] = {}
    for line in disasm_text.splitlines():
        if not line or ":" not in line:
            continue
        for match in ABS_RE.finditer(line):
            value = int(match.group(1), 16)
            if value < 0x8000:
                continue
            counts[value] += 1
            examples.setdefault(value, line.strip())
    lines = ["# Reset-Window Absolute Reference Index", ""]
    lines.append("Generated from generated/disasm/ic30_ic13_reset_000110.lst.")
    lines.append("")
    lines.append("| Address | Count | First observed instruction |")
    lines.append("| --- | ---: | --- |")
    for value, count in sorted(counts.items()):
        lines.append(f"| `0x{value:08x}` | {count} | `{examples[value]}` |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    require_artifacts()
    firmware = FIRMWARE.read_bytes()
    resources = RESOURCES.read_bytes()

    firmware_strings = extract_strings(firmware)
    resource_strings = extract_strings(resources)
    write_if_changed(ANALYSIS / "ic30_ic13_strings.txt", format_strings("IC30/IC13 Strings", firmware_strings))
    write_if_changed(ANALYSIS / "ic32_ic15_strings.txt", format_strings("IC32/IC15 Strings", resource_strings))
    write_if_changed(ANALYSIS / "ic32_ic15_resource_markers.txt", resource_marker_report(resources))
    write_if_changed(ANALYSIS / "ic32_ic15_font_records.md", font_record_report(resources))
    write_if_changed(ANALYSIS / "ic32_ic15_resource_glyph_probe.md", resource_glyph_probe_report(resources))
    write_if_changed(ANALYSIS / "ic30_ic13_startup_tables.txt", decode_startup_tables(firmware))
    write_if_changed(ANALYSIS / "signature_scan.md", scan_signature_report(firmware, resources))
    write_if_changed(ANALYSIS / "ic30_ic13_long_reference_scan.md", categorized_long_references(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_cmpi_byte_candidates.md", cmpi_byte_candidates(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_parser_xrefs.md", xref_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_host_byte_fetch_flow.md", host_byte_fetch_flow_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_font_control_flow.md", font_control_flow_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_direct_control_code_flow.md", direct_control_code_flow_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_esc_e_reset_flow.md", esc_e_reset_flow_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_literal_patterns.md", byte_pattern_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_page_root_references.md", page_root_reference_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_render_path_references.md", render_path_reference_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_compact_bucket_allocator.md", compact_bucket_allocator_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_page_record_bridge.md", page_record_bridge_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_render_dispatch_tables.md", render_dispatch_table_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_render_subrenderers.md", render_subrenderer_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_font_context_bridge.md", font_context_bridge_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_text_glyph_index_flow.md", text_glyph_index_flow_report(firmware, resources))
    write_if_changed(ANALYSIS / "ic30_ic13_printable_text_path.md", printable_text_path_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_text_cursor_span_flow.md", text_cursor_span_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_active_symbol_set_flow.md", active_symbol_set_flow_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_symbol_set_patch_tables.md", symbol_set_patch_table_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_render_expansion_fixtures.md", render_expansion_fixture_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_render_destination_fixtures.md", render_destination_fixture_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_render_row_copy_fixtures.md", render_row_copy_fixture_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_parser_dispatch_tables.md", parser_dispatch_table_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_pcl_command_map.md", parser_command_map_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_page_geometry_tables.md", page_geometry_table_report(firmware))

    if DISASM.exists():
        write_if_changed(ANALYSIS / "ic30_ic13_reset_absolute_refs.md", absolute_reference_report(DISASM.read_text(encoding="utf-8")))

    print(f"firmware strings: {len(firmware_strings)}")
    print(f"resource strings: {len(resource_strings)}")
    print("analysis output: generated/analysis")


if __name__ == "__main__":
    main()
