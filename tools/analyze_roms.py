#!/usr/bin/env python3
"""Generate local LaserJet II ROM analysis indexes from verified artifacts."""

from __future__ import annotations

import hashlib
import json
import re
import textwrap
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "generated"
FIRMWARE = GENERATED / "roms" / "ic30_ic13.bin"
RESOURCES = GENERATED / "roms" / "ic32_ic15.bin"
ANALYSIS = GENERATED / "analysis"
DISASM = GENERATED / "disasm" / "ic30_ic13_reset_000110.lst"


PRINTABLE = set(range(0x20, 0x7f))


def wrap_markdown(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    paragraph: list[str] = []
    in_code = False
    bullet_re = re.compile(r"^(\s*)((?:[-*+])|(?:\d+\.))\s+(.*)$")

    def flush_paragraph() -> None:
        if not paragraph:
            return
        joined = " ".join(line.strip() for line in paragraph)
        out.extend(textwrap.wrap(
            joined,
            width=78,
            break_long_words=False,
            break_on_hyphens=False,
        ))
        paragraph.clear()

    def append_bullet(line: str) -> bool:
        match = bullet_re.match(line)
        if not match:
            return False
        indent, marker, body = match.groups()
        prefix = f"{indent}{marker} "
        out.extend(textwrap.wrap(
            body.strip(),
            width=78,
            initial_indent=prefix,
            subsequent_indent=" " * len(prefix),
            break_long_words=False,
            break_on_hyphens=False,
        ) or [prefix.rstrip()])
        return True

    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            flush_paragraph()
            out.append(line)
            in_code = not in_code
            continue
        if in_code:
            out.append(line)
            continue
        if (
            stripped.startswith("`")
            and stripped.endswith("`")
            and set(stripped.strip("`")) <= {".", "#"}
        ):
            flush_paragraph()
            out.append(line)
            continue
        if bullet_re.match(line):
            flush_paragraph()
            append_bullet(line)
            continue
        if (
            not stripped
            or stripped.startswith(("#", "|", "<!--"))
            or re.match(r"^[-*_]{3,}\s*$", stripped)
        ):
            flush_paragraph()
            out.append(line)
            continue
        paragraph.append(line)
    flush_paragraph()
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def write_if_changed(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".md":
        text = wrap_markdown(text)
    data = text.encode("utf-8")
    old = path.read_bytes() if path.exists() else None
    if old != data:
        path.write_bytes(data)


def require_artifacts() -> None:
    missing = [path for path in (FIRMWARE, RESOURCES) if not path.exists()]
    if missing:
        names = ", ".join(str(path.relative_to(ROOT)) for path in missing)
        raise FileNotFoundError(f"Missing generated ROM artifacts: {names}. Run tools/generate_rom_artifacts.py first.")


def s8(value: int) -> int:
    value &= 0xFF
    return value - 0x100 if value & 0x80 else value


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


def packed_font_metric(word_value: int, byte_value: int) -> int:
    return (((int(word_value) & 0xFFFF) << 8) | (int(byte_value) & 0xFF)) & 0xFFFFFFFF


def builtin_pitch_via_13b76(word_0x24: int, byte_0x26: int) -> int:
    packed = packed_font_metric(word_0x24, byte_0x26)
    if packed < 2:
        return 0xFFFF
    return min(0xFFFF, 0x01D4C000 // packed)


def builtin_height_via_13bca(word_0x28: int, byte_0x2a: int) -> int:
    packed = packed_font_metric(word_0x28, byte_0x2a)
    return (packed * 0x00E1) // 0x2580


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
            pitch_word = u16(data, cursor + 0x24)
            pitch_byte = data[cursor + 0x26]
            height_word = u16(data, cursor + 0x28)
            height_byte = data[cursor + 0x2A]
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
                    "spacing_byte_0x21": data[cursor + 0x21],
                    "symbol_word_0x22": u16(data, cursor + 0x22),
                    "symbol_byte_0x3c": data[cursor + 0x3C],
                    "pitch_word_0x24": pitch_word,
                    "pitch_byte_0x26": pitch_byte,
                    "height_word_0x28": height_word,
                    "height_byte_0x2a": height_byte,
                    "pitch_13b76": builtin_pitch_via_13b76(pitch_word, pitch_byte),
                    "height_13bca": builtin_height_via_13bca(height_word, height_byte),
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


def firmware_scanned_candidate_partitions(records: list[dict[str, int | str | None]]) -> dict[str, object]:
    base = 0x782324
    counters = {
        "0x78278e": 0,
        "0x782790": 0,
        "0x782792": 0,
        "0x782794": 0,
        "0x782796": 0,
        "0x782798": 0,
        "0x78279a": 0,
        "0x78279c": 0,
        "0x78279e": 0,
    }
    cursors = {
        "0x7827a0": base,
        "0x7827a4": base,
        "0x7827a8": base,
        "0x7827ac": base,
        "0x7827b0": base,
        "0x7827b4": base,
    }
    events: list[dict[str, int | str | bool]] = []
    for index, record in enumerate(records):
        address = int(record["firmware_address"]) & 0x00FFFFFF
        class_byte = int(record["class_byte"]) & 0xFF
        low_resource_window = 0x080000 <= address <= 0x0FFFFE
        extension_window = 0x200000 <= address <= 0x5FFFFE
        counters["0x78278e"] += 1
        counter_branch = "other"

        if class_byte == 1:
            counters["0x782790"] += 1
            counter_branch = "class-one"
            if low_resource_window:
                counters["0x782792"] += 1
                for key in ("0x7827a4", "0x7827a8", "0x7827ac", "0x7827b0", "0x7827b4"):
                    cursors[key] += 4
            if extension_window:
                counters["0x782794"] += 1
                for key in ("0x7827a8", "0x7827ac", "0x7827b0", "0x7827b4"):
                    cursors[key] += 4
        elif class_byte == 0:
            counters["0x782798"] += 1
            counter_branch = "class-zero"
            if low_resource_window:
                counters["0x78279a"] += 1
                for key in ("0x7827b0", "0x7827b4"):
                    cursors[key] += 4
            if extension_window:
                counters["0x78279c"] += 1
                cursors["0x7827b4"] += 4

        events.append({
            "index": index,
            "name": str(record["name"]),
            "record_start": int(record["record_start"]),
            "firmware_address": int(record["firmware_address"]),
            "context_longword": int(record["context_longword"]),
            "class_byte": class_byte,
            "low_resource_window": low_resource_window,
            "extension_window": extension_window,
            "counter_branch": counter_branch,
        })
    return {
        "base": base,
        "counters": counters,
        "cursors": cursors,
        "events": events,
    }


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
    header_records = firmware_scanned_font_records(data)
    partitions = firmware_scanned_candidate_partitions(header_records)
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
    lines.append("## Firmware-Scanned Candidate Partitions")
    lines.append("")
    lines.append("This table follows the same sequential resource scan shape as firmware routines `0x1a616` and `0x1a9be`: `HEAD` records are skipped by length, accepted type `0x14`/`0x15` font records are validated, and their record-start firmware addresses feed the candidate list.")
    lines.append("")
    counters = partitions["counters"]
    cursors = partitions["cursors"]
    assert isinstance(counters, dict)
    assert isinstance(cursors, dict)
    lines.append("- accepted records: `%d`" % int(counters["0x78278e"]))
    lines.append("- class `1` records: total `%d`, built-in low-window `%d`, extension-window `%d`" % (
        int(counters["0x782790"]),
        int(counters["0x782792"]),
        int(counters["0x782794"]),
    ))
    lines.append("- class `0` records: total `%d`, built-in low-window `%d`, extension-window `%d`" % (
        int(counters["0x782798"]),
        int(counters["0x78279a"]),
        int(counters["0x78279c"]),
    ))
    lines.append("- final cursor windows: `%s`" % ", ".join(
        f"{key}=0x{int(cursors[key]):06x}"
        for key in ("0x7827a0", "0x7827a4", "0x7827a8", "0x7827ac", "0x7827b0", "0x7827b4")
    ))
    lines.append("- `0x1569c` activation: class-zero uses `0x78287c = 0x%06x`, `0x7827b8 = %d`; class-one uses `0x78287c = 0x%06x`, `0x7827b8 = %d`; each selected entry is marked active with high bit `0x80000000`." % (
        int(cursors["0x7827ac"]),
        int(counters["0x782798"]),
        int(cursors["0x7827a0"]),
        int(counters["0x782790"]),
    ))
    class_zero_symbols = [
        int(record["symbol_word_0x22"])
        for record in header_records
        if int(record["class_byte"]) == 0
    ]
    class_one_symbols = [
        int(record["symbol_word_0x22"])
        for record in header_records
        if int(record["class_byte"]) == 1
    ]
    lines.append("- `0x156de` concrete symbol filtering: the built-in class-zero window starts with record `+0x22` words %s, and class-one starts with %s; a primary `0x0115` filter therefore keeps the three Roman-8 entries in the active window, moves `0x78287c` to the first survivor, and reduces `0x7827b8` from 12 to 3." % (
        " / ".join(f"`0x{word:04x}`" for word in class_zero_symbols[:4]),
        " / ".join(f"`0x{word:04x}`" for word in class_one_symbols[:4]),
    ))
    class_zero_records = [
        record
        for record in header_records
        if int(record["class_byte"]) == 0
    ]
    roman8_survivors = [
        (index, record)
        for index, record in enumerate(class_zero_records)
        if int(record["symbol_word_0x22"]) == 0x0115
    ]
    roman8_tuples = [
        (
            index,
            record,
            (
                int(record["height_13bca"]),
                data[int(record["record_start"]) + 0x2F],
                s8(data[int(record["record_start"]) + 0x30]),
                data[int(record["record_start"]) + 0x31],
            ),
        )
        for index, record in roman8_survivors
    ]
    selected_index, selected_record, selected_tuple = max(roman8_tuples, key=lambda item: item[2])
    selected_slot = int(cursors["0x7827ac"]) + selected_index * 4
    lines.append("- `0x14398` concrete active chooser: `0x13c06` ranks resource class first, then same-class built-ins use `0x1428c` to compare decoded height, byte `+0x2f`, signed byte `+0x30`, and byte `+0x31`. The class-zero Roman-8 survivor tuples are %s, so the chooser writes selected slot `0x%06x` / record `0x%06x` to `0x7828a8`." % (
        " / ".join(
            "`0x%06x:%s`" % (int(record["record_start"]), list(fields))
            for _index, record, fields in roman8_tuples
        ),
        selected_slot,
        int(selected_record["record_start"]),
    ))
    class_zero_heights = [
        int(record["height_13bca"])
        for record in header_records
        if int(record["class_byte"]) == 0
    ]
    lines.append("- `0x1519a` concrete height filtering: built-in class-zero decoded heights are %s; requested height `0x04b0` keeps the eight `1200`-unit candidates via the +/-`0x19` range, while requested `0x0384` misses that range and the nearest-height fallback keeps the four `850`-unit candidates." % (
        " / ".join(f"`{height}`" for height in class_zero_heights),
    ))
    class_zero_pitches = [
        int(record["pitch_13b76"])
        for record in header_records
        if int(record["class_byte"]) == 0
    ]
    class_zero_spacings = [
        int(record["spacing_byte_0x21"])
        for record in header_records
        if int(record["class_byte"]) == 0
    ]
    lines.append("- `0x153c6` concrete spacing/pitch filtering: built-in class-zero spacing bytes are %s and decoded pitches are %s; requested spacing `0` plus pitch `0x03e8` keeps the eight `1000`-unit candidates via the +/-`5` range, while requested pitch `0x04b0` misses that range and `0x1562c` selects the next available pitch `1666`, keeping four candidates." % (
        " / ".join(f"`{spacing}`" for spacing in class_zero_spacings),
        " / ".join(f"`{pitch}`" for pitch in class_zero_pitches),
    ))
    lines.append("")
    lines.append("| Scan index | Name | Record start | Firmware address | Context longword | Class | Partition |")
    lines.append("| ---: | --- | ---: | ---: | ---: | ---: | --- |")
    for event in partitions["events"]:
        assert isinstance(event, dict)
        lines.append(
            f"| {int(event['index'])} | `{event['name']}` | `0x{int(event['record_start']):06x}` | "
            f"`0x{int(event['firmware_address']):06x}` | `0x{int(event['context_longword']):08x}` | "
            f"`{int(event['class_byte'])}` | {event['counter_branch']} |"
        )
    lines.append("")
    lines.append("The verified built-in ROM image contributes only low-window records here: twelve class `0` records and twelve class `1` records. The extension-window counters remain zero until cartridge or external resource ranges are scanned.")
    lines.append("")
    lines.append("## String-Labeled Candidate Records")
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


def builtin_glyph_payload_extract(data: bytes) -> tuple[str, str]:
    header_records = firmware_scanned_font_records(data)
    extracted_at = "generated from verified IC32,IC15 resource interleave"
    manifest: dict[str, object] = {
        "source": "generated/roms/ic32_ic15.bin",
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "extractor": extracted_at,
        "records": [],
    }
    report_lines = ["# IC32/IC15 Built-In Glyph Payload Extract", ""]
    report_lines.append(
        "Generated by walking the same `HEAD`/typed built-in font records as "
        "firmware routines `0x1a616`/`0x1a9be`, then resolving each nonzero "
        "offset-table entry with the `0x1f354` built-in glyph formula."
    )
    report_lines.append("")

    total_slots = 0
    total_nonzero = 0
    total_payloads = 0
    total_payload_bytes = 0
    mode_counts: Counter[int] = Counter()
    skipped_reasons: Counter[str] = Counter()
    unique_payload_hashes: set[str] = set()
    record_summaries: list[dict[str, object]] = []

    for record_index, record in enumerate(header_records):
        base = int(record["record_start"])
        table = int(record["table"])
        first_char = int(record["first_char"])
        last_char = int(record["last_char"])
        range_count = max(0, last_char - first_char + 1)
        table_limit = min(len(data), base + int(record["length"]))
        table_slots = min(range_count, max(0, (table_limit - table) // 4))
        glyphs: list[dict[str, object]] = []
        record_payloads = 0
        record_payload_bytes = 0
        record_modes: Counter[int] = Counter()
        record_skips: Counter[str] = Counter()

        for glyph_index in range(table_slots):
            total_slots += 1
            table_entry = table + glyph_index * 4
            relative = u32(data, table_entry)
            if relative == 0:
                skipped_reasons["zero-table-entry"] += 1
                record_skips["zero-table-entry"] += 1
                continue
            total_nonzero += 1
            entry = base + relative
            host_byte = first_char + glyph_index
            glyph_record: dict[str, object] = {
                "host_byte": host_byte,
                "glyph_index": glyph_index,
                "table_entry": table_entry,
                "relative_offset": relative,
                "entry_offset": entry,
                "entry_firmware_address": 0x80000 + entry,
            }
            if entry < 0 or entry + 10 > len(data):
                glyph_record["status"] = "entry-out-of-range"
                skipped_reasons["entry-out-of-range"] += 1
                record_skips["entry-out-of-range"] += 1
                glyphs.append(glyph_record)
                continue

            bitmap_delta = data[entry + 4]
            mode = data[entry + 5]
            rows = u16(data, entry + 6)
            width = u16(data, entry + 8)
            span = (width + 7) // 8 if width else 0
            render_span = span
            if render_span & 1 and mode != 2 and render_span != 1:
                render_span += 1
            bitmap = entry + bitmap_delta
            payload_length = rows * max(render_span, 1)
            mode_counts[mode] += 1
            record_modes[mode] += 1

            glyph_record.update({
                "x_offset": s16(data, entry),
                "y_offset": s16(data, entry + 2),
                "bitmap_delta": bitmap_delta,
                "mode": mode,
                "rows": rows,
                "width": width,
                "span": span,
                "render_span": render_span,
                "bitmap_offset": bitmap,
                "bitmap_firmware_address": 0x80000 + bitmap,
                "payload_length": payload_length,
            })
            if (
                bitmap_delta == 0
                or rows == 0
                or width == 0
                or bitmap < 0
                or bitmap + payload_length > len(data)
            ):
                glyph_record["status"] = "no-normal-payload"
                skipped_reasons["no-normal-payload"] += 1
                record_skips["no-normal-payload"] += 1
                glyphs.append(glyph_record)
                continue

            payload = data[bitmap : bitmap + payload_length]
            digest = hashlib.sha256(payload).hexdigest()
            glyph_record.update({
                "status": "extracted",
                "payload_sha256": digest,
                "payload_hex": payload.hex(),
            })
            glyphs.append(glyph_record)
            total_payloads += 1
            total_payload_bytes += len(payload)
            record_payloads += 1
            record_payload_bytes += len(payload)
            unique_payload_hashes.add(digest)

        record_summary = {
            "scan_index": record_index,
            "name": str(record["name"]),
            "record_start": base,
            "firmware_address": int(record["firmware_address"]),
            "context_longword": int(record["context_longword"]),
            "first_char": first_char,
            "last_char": last_char,
            "table": table,
            "table_slots": table_slots,
            "nonzero_entries": sum(1 for glyph in glyphs if int(glyph["relative_offset"]) != 0),
            "extracted_payloads": record_payloads,
            "payload_bytes": record_payload_bytes,
            "modes": {str(key): record_modes[key] for key in sorted(record_modes)},
            "skipped": {key: record_skips[key] for key in sorted(record_skips)},
        }
        record_summaries.append(record_summary)
        manifest_record = dict(record_summary)
        manifest_record["glyphs"] = glyphs
        records = manifest["records"]
        assert isinstance(records, list)
        records.append(manifest_record)

    manifest["summary"] = {
        "records": len(header_records),
        "table_slots": total_slots,
        "nonzero_entries": total_nonzero,
        "extracted_payloads": total_payloads,
        "payload_bytes": total_payload_bytes,
        "unique_payload_hashes": len(unique_payload_hashes),
        "modes": {str(key): mode_counts[key] for key in sorted(mode_counts)},
        "skipped": {key: skipped_reasons[key] for key in sorted(skipped_reasons)},
    }

    report_lines.append("## Summary")
    report_lines.append("")
    report_lines.append(
        "- Records scanned: `%d`; table slots: `%d`; nonzero entries: `%d`."
        % (len(header_records), total_slots, total_nonzero)
    )
    report_lines.append(
        "- Extracted payloads: `%d`; payload bytes: `%d`; unique payload "
        "hashes: `%d`."
        % (total_payloads, total_payload_bytes, len(unique_payload_hashes))
    )
    report_lines.append(
        "- Glyph modes seen: `%s`; skipped entries: `%s`."
        % (
            ", ".join(f"{mode}:{mode_counts[mode]}" for mode in sorted(mode_counts)),
            ", ".join(f"{key}:{skipped_reasons[key]}" for key in sorted(skipped_reasons)),
        )
    )
    report_lines.append("")
    report_lines.append(
        "The companion local JSON artifact "
        "`generated/analysis/ic32_ic15_builtin_glyph_payloads.json` includes "
        "one record per extracted glyph with host byte, mapped glyph index, "
        "entry offsets, signed placement offsets, dimensions, render span, "
        "payload SHA-256, and exact payload bytes as hex. It remains ignored "
        "with the other ROM-derived generated artifacts."
    )
    report_lines.append("")
    report_lines.append("## Per-Record Coverage")
    report_lines.append("")
    report_lines.append("| Scan | Name | Record | Context | Range | Slots | Extracted | Bytes | Modes | Skipped |")
    report_lines.append("| ---: | --- | ---: | ---: | --- | ---: | ---: | ---: | --- | --- |")
    for summary in record_summaries:
        modes = summary["modes"]
        skipped = summary["skipped"]
        assert isinstance(modes, dict)
        assert isinstance(skipped, dict)
        report_lines.append(
            f"| {int(summary['scan_index'])} | `{summary['name']}` | "
            f"`0x{int(summary['record_start']):06x}` | "
            f"`0x{int(summary['context_longword']):08x}` | "
            f"`0x{int(summary['first_char']):02x}`..`0x{int(summary['last_char']):02x}` | "
            f"{int(summary['table_slots'])} | {int(summary['extracted_payloads'])} | "
            f"{int(summary['payload_bytes'])} | "
            f"{', '.join(f'{key}:{value}' for key, value in modes.items())} | "
            f"{', '.join(f'{key}:{value}' for key, value in skipped.items())} |"
        )
    report_lines.append("")
    return (
        "\n".join(report_lines),
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
    )


def builtin_glyph_rows_from_record(data: bytes, record: dict[str, int | str | None], host_byte: int) -> dict[str, object]:
    first_char = int(record["first_char"])
    last_char = int(record["last_char"])
    if not (first_char <= host_byte <= last_char):
        raise AssertionError(
            f"host byte 0x{host_byte:02x} outside record range "
            f"0x{first_char:02x}..0x{last_char:02x}"
        )
    glyph_index = host_byte - first_char
    base = int(record["record_start"])
    table = int(record["table"])
    relative = u32(data, table + glyph_index * 4)
    if relative == 0:
        raise AssertionError(f"host byte 0x{host_byte:02x} maps to an empty glyph")
    entry = base + relative
    bitmap_delta = data[entry + 4]
    mode = data[entry + 5]
    rows = u16(data, entry + 6)
    width = u16(data, entry + 8)
    span = (width + 7) // 8
    render_span = span
    if render_span & 1 and mode != 2 and render_span != 1:
        render_span += 1
    if mode != 1:
        raise AssertionError(f"sample renderer only handles mode-1 glyphs, got mode {mode}")
    bitmap = entry + bitmap_delta
    payload = data[bitmap : bitmap + rows * render_span]
    decoded_rows: list[str] = []
    for row in range(rows):
        row_bytes = payload[row * render_span : (row + 1) * render_span]
        decoded = []
        for bit_index in range(width):
            value = row_bytes[bit_index // 8]
            mask = 0x80 >> (bit_index % 8)
            decoded.append("#" if value & mask else ".")
        decoded_rows.append("".join(decoded))
    return {
        "host_byte": host_byte,
        "glyph_index": glyph_index,
        "entry": entry,
        "bitmap": bitmap,
        "rows": rows,
        "width": width,
        "render_span": render_span,
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "decoded_rows": decoded_rows,
    }


def compose_direct_glyph_sample(data: bytes, record: dict[str, int | str | None], text: str) -> dict[str, object]:
    return compose_direct_glyph_byte_sample(data, record, text.encode("latin-1"), text)


def compose_direct_glyph_byte_sample(
    data: bytes,
    record: dict[str, int | str | None],
    sample_bytes: bytes,
    label: str,
) -> dict[str, object]:
    glyphs = [
        builtin_glyph_rows_from_record(data, record, byte)
        for byte in sample_bytes
    ]
    height = max(int(glyph["rows"]) for glyph in glyphs)
    composed_rows: list[str] = []
    for row_index in range(height):
        parts: list[str] = []
        for glyph in glyphs:
            rows = glyph["decoded_rows"]
            assert isinstance(rows, list)
            if row_index < len(rows):
                parts.append(str(rows[row_index]))
            else:
                parts.append("." * int(glyph["width"]))
        composed_rows.append(".".join(parts))
    return {
        "text": label,
        "sample_bytes": sample_bytes.hex(" "),
        "record_start": int(record["record_start"]),
        "context_longword": int(record["context_longword"]),
        "rows": composed_rows,
        "row_sha256": hashlib.sha256("\n".join(composed_rows).encode("ascii")).hexdigest(),
        "glyphs": [
            {
                "host_byte": int(glyph["host_byte"]),
                "glyph_index": int(glyph["glyph_index"]),
                "entry": int(glyph["entry"]),
                "bitmap": int(glyph["bitmap"]),
                "width": int(glyph["width"]),
                "rows": int(glyph["rows"]),
                "render_span": int(glyph["render_span"]),
                "payload_sha256": str(glyph["payload_sha256"]),
            }
            for glyph in glyphs
        ],
    }


def builtin_font_sample_report(data: bytes) -> str:
    records = firmware_scanned_font_records(data)
    courier = next(
        record
        for record in records
        if record["name"] == "COURIER" and int(record["record_start"]) == 0x000418
    )
    line_printer = next(
        record
        for record in records
        if record["name"] == "LINE_PRINTER" and int(record["record_start"]) == 0x0146B4
    )
    samples = [
        ("COURIER", compose_direct_glyph_sample(data, courier, "LASERJETII")),
        ("LINE_PRINTER", compose_direct_glyph_sample(data, line_printer, "LASERJETII")),
    ]
    lines = ["# IC32/IC15 Built-In Font Direct Samples", ""]
    lines.append(
        "These samples consume the same mode-1 payload bytes emitted in "
        "`ic32_ic15_builtin_glyph_payloads.json` and decode them directly "
        "into `#`/`.` rows. They prove the extractor output is renderable "
        "font input, but they are not a firmware cursor/baseline or self-test "
        "placement proof."
    )
    lines.append("")
    for name, sample in samples:
        rows = sample["rows"]
        glyphs = sample["glyphs"]
        assert isinstance(rows, list)
        assert isinstance(glyphs, list)
        lines.append(f"## {name}")
        lines.append("")
        lines.append(
            "- Text: `%s`; record `0x%06x`; context `0x%08x`; row hash `%s`."
            % (
                str(sample["text"]),
                int(sample["record_start"]),
                int(sample["context_longword"]),
                str(sample["row_sha256"]),
            )
        )
        lines.append(
            "- Glyph indexes: `%s`."
            % ", ".join(
                "0x%02x->0x%02x" % (int(glyph["host_byte"]), int(glyph["glyph_index"]))
                for glyph in glyphs
            )
        )
        lines.append("")
        lines.append("```text")
        lines.extend(str(row) for row in rows)
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def c_string(data: bytes, offset: int) -> str:
    end = data.find(b"\x00", offset)
    if end < 0:
        end = len(data)
    return data[offset:end].decode("ascii", errors="replace")


def font_sample_page_report(data: bytes) -> str:
    return font_sample_page_report_with_resources(data, b"")


def font_sample_page_report_with_resources(data: bytes, resources: bytes) -> str:
    source_table = 0x1C170
    source_names = [
        (index, u32(data, source_table + index * 4))
        for index in range(4)
    ]
    header_strings = [
        0x1C7EA,
        0x1C82D,
        0x1C836,
        0x1C878,
        0x1C8AD,
        0x1C8DF,
    ]
    style_strings = [
        0x1D17C,
        0x1D184,
        0x1D18C,
        0x1D193,
    ]
    symbol_variant_table = 0x1C0A6
    symbol_variant_rows = [
        (
            u16(data, symbol_variant_table + index * 8),
            data[symbol_variant_table + index * 8 + 2],
            u32(data, symbol_variant_table + index * 8 + 4),
        )
        for index in range(7)
    ]
    family_name_table = 0x1C11A
    family_name_rows = [
        (
            u16(data, family_name_table + index * 6),
            u32(data, family_name_table + index * 6 + 2),
        )
        for index in range(6)
    ]
    sample_bytes_1 = data[0x1C1CF:0x1C1E8]
    sample_bytes_2 = data[0x1C1E9:0x1C202]
    direct_samples: list[tuple[str, str, dict[str, object]]] = []
    if resources:
        records = firmware_scanned_font_records(resources)
        sample_records = [
            (
                "COURIER",
                next(
                    record
                    for record in records
                    if record["name"] == "COURIER" and int(record["record_start"]) == 0x000418
                ),
            ),
            (
                "LINE_PRINTER",
                next(
                    record
                    for record in records
                    if record["name"] == "LINE_PRINTER" and int(record["record_start"]) == 0x0146B4
                ),
            ),
        ]
        for font_name, record in sample_records:
            direct_samples.append((
                font_name,
                "sample run 1",
                compose_direct_glyph_byte_sample(resources, record, sample_bytes_1, "sample-run-1"),
            ))
            direct_samples.append((
                font_name,
                "sample run 2",
                compose_direct_glyph_byte_sample(resources, record, sample_bytes_2, "sample-run-2"),
            ))

    lines = ["# IC30/IC13 Font Sample Page Path", ""]
    lines.append(
        "This report covers the first ROM facts behind the control-panel font "
        "printout/self-test sample path. It is not a full placement proof yet; "
        "it names the firmware strings, print helpers, and font-context setup "
        "that feed the same `0xd04a` printable path used by host text."
    )
    lines.append("")

    lines.append("## Literal Strings and Samples")
    lines.append("")
    lines.append("| Address | Text |")
    lines.append("| ---: | --- |")
    for offset in header_strings:
        lines.append(f"| `0x{offset:06x}` | `{c_string(data, offset)}` |")
    lines.append("")
    lines.append("Source/category pointer table at `0x1c170`:")
    lines.append("")
    lines.append("| Index | Pointer | Text |")
    lines.append("| ---: | ---: | --- |")
    for index, pointer in source_names:
        lines.append(f"| {index} | `0x{pointer:06x}` | `{c_string(data, pointer)}` |")
    lines.append("")
    lines.append("Style labels used by the font-row formatter:")
    lines.append("")
    lines.append("| Address | Text |")
    lines.append("| ---: | --- |")
    for offset in style_strings:
        lines.append(f"| `0x{offset:06x}` | `{c_string(data, offset)}` |")
    lines.append("")
    lines.append(
        "- Sample byte run 1 at `0x1c1cf`: `%s`."
        % " ".join(f"0x{byte:02x}" for byte in sample_bytes_1)
    )
    lines.append(
        "- Sample byte run 2 at `0x1c1e9`: `%s`."
        % " ".join(f"0x{byte:02x}" for byte in sample_bytes_2)
    )
    lines.append("")

    lines.append("## Outer Loop and Page Boundaries")
    lines.append("")
    lines.append("| Address | Fact |")
    lines.append("| ---: | --- |")
    lines.append("| `0x1c204` | Entry checks accepted-resource count `0x78278e`, reports status `0xe3/0x51` if no font records exist, then calls setup helper `0xe9ba`. |")
    lines.append("| `0x1c22a..0x1c236` | Clears display-function bytes `0x783190/0x783191` and sets `0x782da4 = 1` before printing. |")
    lines.append("| `0x1c23e..0x1c26c` | Clears four per-source status bytes at `0x783f02..0x783f05`. |")
    lines.append("| `0x1c26e..0x1c28a` | Clears row-height word `0x783f06` and local counters before the font pass loop. |")
    lines.append("| `0x1c28e..0x1c2c4` | Runs two font-class passes: pass `0` requires class-zero count `0x782798`, pass `1` requires class-one count `0x782790`. Empty passes skip to the next pass. |")
    lines.append("| `0x1c2cc..0x1c2f2` | For a nonempty pass, calls `0x1d76c`, ensures a page root through `0x10084`, selects initial candidate state through `0x1e9a0`, and prints the first headers before advancing vertically through `0x1cfb4`. |")
    lines.append("| `0x1c2fe..0x1c332` | Prints up to four source groups for a pass. When the group index reaches `4`, snapshots published pool pointer `0x780ea6`, clears a local page flag, and calls FF handler `0xf0f0`. |")
    lines.append("| `0x1c344..0x1c350` | Increments the class-pass counter and loops back to `0x1c28e`; after both passes, returns the saved pool pointer. |")
    lines.append("| `0x1c540..0x1c5c6` | Maintains a 16-entry recent-font list at `0x783f0a` with count byte `0x783f08`, preventing duplicate candidate rows and appending new selected contexts until full. |")
    lines.append("")
    lines.append(
        "The loop therefore reaches the existing page-object machinery before "
        "sample text is emitted: `0x10084` creates/ensures the page root, "
        "`0x1c5e8` installs each selected font into the current-font/page-root "
        "state, `0x1ca2c` and helpers print labels/sample bytes through "
        "`0xd04a`, and `0xf0f0` finalizes/ejects between class passes."
    )
    lines.append("")

    lines.append("## Candidate Row Traversal")
    lines.append("")
    lines.append("| Address | Fact |")
    lines.append("| ---: | --- |")
    lines.append("| `0x1c354..0x1c386` | After the first header pass, clears the one-shot header flag. If the recent-context list has reached 16 entries, calls `0x1d79c(source)` and starts a continuation page through `0x1c9f6` when another printable source row remains. |")
    lines.append("| `0x1c386..0x1c3aa` | Emits the source/category heading with `0x1ca2c(source, 0, current-context, 0)`, then asks `0x1b50e(source, row-index, &next-index)` for the first candidate row in that source group. |")
    lines.append("| `0x1c3be..0x1c3e4` | Normalizes the returned candidate through `0x1c746`, reads selector/flag bytes via `0x1c766` and `0x1c7a8`, and reads class/orientation through `0x1c710` for comparison with the current class pass. |")
    lines.append("| `0x1c3e8..0x1c42e` | If the candidate class does not match the current pass, either retries candidate lookup or marks the current source status byte at `0x783f02 + source`. |")
    lines.append("| `0x1c432..0x1c470` | For a matching candidate, installs its context through `0x1c5e8`; if the recent list is full and the candidate is not the last list entry at `0x783f46`, starts a continuation page and reprints the source heading. |")
    lines.append("| `0x1c470..0x1c4f2` | Flushes pending text, calls `0x1d050` to advance/check current row height, and calls `0x1d868` to test whether an alternate sample row needs its own continuation-page heading. |")
    lines.append("| `0x1c4f2..0x1c53c` | Emits the formatted font row through `0x1cabe`; if no continuation happened, installs the candidate via `0x1cece` and emits sample byte runs through `0x1cf34`, storing the return flag in local page-break word `-6(A6)`. |")
    lines.append("| `0x1c540..0x1c5c6` | Scans recent-context entries at `0x783f0a`; duplicates jump back to the source-pass decision path, while a new context is appended and count byte `0x783f08` is incremented. |")
    lines.append("| `0x1c5ca..0x1c5e4` | Advances candidate row index `D5` up to `0x63`; when exhausted, stores the final per-source status byte at `0x783f02 + source`, increments source group `D4`, clears row index, and returns to the source loop at `0x1c2fe`. |")
    lines.append("")
    lines.append(
        "This pins the row traversal around the previously open `0x1c334` "
        "region. The missing executable model is now narrow: reproduce the "
        "`0x1b50e` candidate sequence and feed these row decisions into the "
        "already identified printable/page-object path."
    )
    lines.append("")

    lines.append("## Candidate Resolver `0x1b50e`")
    lines.append("")
    lines.append("| Address | Fact |")
    lines.append("| ---: | --- |")
    lines.append("| `0x1b516..0x1b558` | Requested ordinal `0xff` disables lookup, clears the caller output word, and returns no resource address. Otherwise `0x1b8ea(mode, ordinal)` is tried first; on fast-probe success, the selected resource comes from `0x7828a0` and the output word from `0x7828a4`. |")
    lines.append("| `0x1b568..0x1b5a4` | Selects the first scan window. Mode `3` uses pointer/count `0x7827ac` / `0x78279a`; modes `1` and `2` use `0x7827b0` / `0x78279c`; mode `0` uses `0x7827b4` / `0x78279e`. Other modes miss. |")
    lines.append("| `0x1b5a4..0x1b60c` | Sets Roman-8 substitution flag `0x7828ac = 1` unless requested symbol word `0x7821a0` is one of `0x0115`, `0x0175`, `0x0155`, or `0x000e`. |")
    lines.append("| `0x1b61a..0x1b650` | For each first-window candidate, reads its candidate word through `0x1bbfe`, classifies it through `0x1b750(mode, slot, word)`, and advances pointer/count when the classifier returns zero. |")
    lines.append("| `0x1b650..0x1b74e` | When the first window is exhausted, selects the second scan window. Mode `3` uses `0x7827a0` / `0x782792`; modes `1` and `2` use `0x7827a4` / `0x782794`; mode `0` uses `0x7827a8` / `0x782796`. |")
    lines.append("| `0x1b66e..0x1b6ec` | Classifier return `2` marks a pending duplicate Roman-8 candidate. When the requested ordinal is reached and candidate word is Roman-8 with substitution enabled and a duplicate is pending, the output word is the requested symbol `0x7821a0`; otherwise it is the candidate word. |")
    lines.append("| `0x1b6b2..0x1b706` | Non-selected Roman-8 candidates can count twice for non-special requested symbols, unless the current selected slot `0x7828a0` is the same slot; this is the duplicate-suppression branch used by the printout row traversal. |")
    lines.append("| `0x1b750..0x1b7ac` | Candidate classifier accepts only candidates passing `0x1b7b2` range/special/downloaded checks and `0x1b8b6` current-Roman-8 suppression; it returns `2` for the current selected slot in modes `1` or `2`, otherwise `1`. |")
    lines.append("| `0x1b7b2..0x1b8b4` | Admissibility checks are mode-specific: mode `3` accepts the built-in symbol words above, mode `1` accepts `0x200000..0x3ffffe`, mode `2` accepts `0x400000..0x5ffffe`, and mode `0` accepts downloaded records whose `0x170be` record flags include bit 30. |")
    lines.append("| `0x1b8ea..0x1b98c` | Fast probe clears `0x7828a0`; mode `3` searches fallback via `0x1ae7e`, modes `1` and `2` call `0x1adaa` first with primary selector `0x78289f = 0` and then with secondary selector `0x78289f = 1`. It succeeds only for requested ordinal zero and a nonzero `0x7828a0`. |")
    lines.append("")
    lines.append(
        "For the font sample page, source-group mode and row ordinal therefore "
        "drive exactly which candidate record enters `0x1c746` and later "
        "`0x1cabe` / `0x1cf34`. Reproducing the printed rows must preserve "
        "the two-window order and the Roman-8 duplicate/substitution cases, "
        "not just iterate the candidate slots once."
    )
    lines.append("")

    if direct_samples:
        lines.append("## Direct Glyph Payload Hashes")
        lines.append("")
        lines.append(
            "These hashes render the ROM sample byte runs directly through the "
            "extracted built-in glyph payloads for the first `COURIER` and "
            "first `LINE_PRINTER` records. They still bypass the surrounding "
            "`0x1c334` page-object loop."
        )
        lines.append("")
        lines.append("| Font | Sample | Record | Context | Row hash | Glyph count |")
        lines.append("| --- | --- | ---: | ---: | --- | ---: |")
        for font_name, sample_name, sample in direct_samples:
            glyphs = sample["glyphs"]
            assert isinstance(glyphs, list)
            lines.append(
                f"| `{font_name}` | {sample_name} | "
                f"`0x{int(sample['record_start']):06x}` | "
                f"`0x{int(sample['context_longword']):08x}` | "
                f"`{sample['row_sha256']}` | {len(glyphs)} |"
            )
        lines.append("")

    lines.append("## Print and Placement Helpers")
    lines.append("")
    lines.append("| Routine | Observed behavior |")
    lines.append("| ---: | --- |")
    lines.append("| `0x1d12e` | Reads a null-terminated ROM string and calls printable handler `0xd04a` for each byte, so sample-page labels enter the same text path as host bytes. |")
    lines.append("| `0x1d152` | Advances horizontal cursor `0x782c8a` by the caller value scaled through `0x332ee(..., 0x1e)`. |")
    lines.append("| `0x1cfb4` | Advances vertical cursor `0x782c8e` by converting current position through `0x104fe`, adding `0x0258`, then converting back through `0x104d8`. |")
    lines.append("| `0x1cfe4` | Computes a line advance from current font/sample state and clamps it to at least `0x0258` before updating `0x782c8e`. |")
    lines.append("| `0x1ca2c` | Emits source labels and sample rows, calls `0x1d964`/`0x1d12e`, flushes spans through `0x126e2`/`0x12714`, and stores row-height state in `0x783f06`. |")
    lines.append("| `0x1cabe` | Formats a font row prefix: source code bytes `S`, `L`, `R`, or `I`; two decimal digits; style/spacing/pitch/height details; then sample text. |")
    lines.append("")

    lines.append("## Header, Row, and Sample Sequencing")
    lines.append("")
    lines.append("| Address | Fact |")
    lines.append("| ---: | --- |")
    lines.append("| `0x1c916` | Resets sample-page VMI/HMI, initializes vertical cursor word `0x782c8e = 0x0024`, clears `0x782c90`, selects portrait/landscape header text from `0x782da3`, then prints column headers with repeated `0x1cfb4` line advances. |")
    lines.append("| `0x1c9b8` | Clears all 16 recent-context slots at `0x783f0a`, sets count byte `0x783f08 = 1`, and seeds the first slot with the active context. |")
    lines.append("| `0x1c9f6` | Starts a continuation page by calling FF handler `0xf0f0`, ensuring a page root through `0x10084`, reinstalling the active context through `0x1c5e8`, rerunning header setup `0x1c916`, and reseeding the recent list. |")
    lines.append("| `0x1ca2c` | Before printing a source heading, compares `0x782c8e + current-row-height` against page-limit word `0x782db6`; if it would overrun, it enters the continuation path at `0x1c9f6`. |")
    lines.append("| `0x1ca86..0x1caa6` | Flushes pending text with `0x126e2`, prints the selected source/category label from table `0x1c170` via `0x1d12e`, flushes with `0x12714`, advances one line, and stores the row-height word in `0x783f06`. |")
    lines.append("| `0x1cb26..0x1cb66` | Builds and prints row prefix bytes: source code `S/L/R/I`, two decimal digits from the row number, a terminator, then advances `0x782c8a` by two horizontal units. |")
    lines.append("| `0x1cb6e..0x1cc5e` | Prints style, pitch, height, and symbol-set fields from the selected record, using `0x1d198`, `0x13b76`, `0x13bca`, `0x1cc6e`, and `0x1cd78`, with one- or two-unit `0x1d152` horizontal advances between columns. |")
    lines.append("| `0x1cf34..0x1cf9a` | Emits sample run 1 from `0x1c1cf`; if `0x783132` is nonzero, it flushes, updates row/overflow state via `0x1d050`, advances horizontally by `0x31` units, installs the alternate context via `0x1cece`, then emits sample run 2 from `0x1c1e9`. |")
    lines.append("| `0x1d050` | Chooses the larger current/alternate row height, may update `0x783f06`, advances by `0x1cfe4`, and if the page limit `0x782db6` would be exceeded, starts a continuation heading via `0x1ca2c` before advancing again. |")
    lines.append("")
    lines.append(
        "These addresses move the sample printout closer to a reproducible page "
        "model: the source label, row prefix, metric columns, and both sample "
        "byte runs are now tied to cursor state (`0x782c8a`, `0x782c8e`), "
        "page-limit state (`0x782db6`), and explicit flush points."
    )
    lines.append("")

    lines.append("## Row Formatting and Fit Helpers")
    lines.append("")
    lines.append("| Routine | Observed behavior |")
    lines.append("| ---: | --- |")
    lines.append("| `0x1d198` | Formats the font-name/style column. It resolves built-in and downloaded names differently, appends spacing/style labels from the local string table, numeric style digits when needed, then pads through `0x1d152` so the column occupies 25 emitted characters. |")
    lines.append("| `0x1d460` | Walks resource subrecords tagged `FONT`/`font`, `TABL`/`tabl`, or `DUMY`/`DUMY`-like data by adding embedded offsets, then reads the word at `+6` from the resolved font record. |")
    lines.append("| `0x1d4ee` | Searches 32 downloaded-font slots at `0x782640` for a payload pointer matching the selected record and returns status `1`, status `0x15`, or reports `0xe3/0x52` if no slot matches. |")
    lines.append("| `0x1d5fa` | For a built-in record, follows the relative name pointer at `+0x38`, reads the stored length word, and emits either a trimmed name or a 25-character-capped name depending on the caller flag. |")
    lines.append("| `0x1d6ea` | Emits a null-terminated string through `0xd04a` while tracking the current column width and suppressing output after the width reaches 26. |")
    lines.append("| `0x1d71e` | Emits fixed-length name bytes through `0xd04a`, replacing C0 controls and bytes `0x80..0x9f` with spaces. |")
    lines.append("| `0x1d76c` | Writes a six-byte parsed-command record at `0x78299e` with flag byte `0x80` and the requested orientation word, then calls the normal orientation handler `0x10220`. |")
    lines.append("| `0x1d79c` | Probes up to two candidates from `0x1b50e`, compares their orientation/class through `0x1c710` against `0x782da3`, and consults the per-source byte at `0x783f02 + source` for landscape/source gating. |")
    lines.append("| `0x1d868` / `0x1dcf2` | Temporarily installs current and alternate contexts, uses `0x1dc38` to simulate one or two sample-row advances, and compares the projected y plus row height against page-limit word `0x782db6`. |")
    lines.append("| `0x1d964` | Resolves a candidate for a source group when none is passed in, checks fit with `0x1dcf2`, installs the selected context through `0x1cece`, and tests alternate-row placement when `0x783132` is set. |")
    lines.append("")
    lines.append(
        "The font-name and fit helpers show that the printout is not just a "
        "linear string dump. It reuses the parser's orientation handler, "
        "applies the same printable-byte sanitizer for names, and performs "
        "preflight page-fit tests before emitting the source heading or "
        "alternate sample row."
    )
    lines.append("")

    lines.append("### Row Formatter Lookup Tables")
    lines.append("")
    lines.append(
        "`0x1d198` uses two local lookup tables before falling back to "
        "style/numeric formatting. The first table matches the derived "
        "symbol byte and variant word, and the second matches the family byte "
        "from the selected resource record."
    )
    lines.append("")
    lines.append("Symbol/variant substitutions at `0x1c0a6`:")
    lines.append("")
    lines.append("| Variant word | Symbol byte | Label pointer | Label |")
    lines.append("| ---: | ---: | ---: | --- |")
    for variant_word, symbol_byte, pointer in symbol_variant_rows:
        if 0x20 <= symbol_byte < 0x7F:
            symbol_text = f"`0x{symbol_byte:02x}` (`{chr(symbol_byte)}`)"
        else:
            symbol_text = f"`0x{symbol_byte:02x}`"
        lines.append(
            f"| `0x{variant_word:04x}` | {symbol_text} | "
            f"`0x{pointer:06x}` | `{c_string(data, pointer)}` |"
        )
    lines.append("")
    lines.append("Family-name substitutions at `0x1c11a`:")
    lines.append("")
    lines.append("| Family byte | Label pointer | Label |")
    lines.append("| ---: | ---: | --- |")
    for family_byte, pointer in family_name_rows:
        lines.append(
            f"| `0x{family_byte:04x}` | `0x{pointer:06x}` | "
            f"`{c_string(data, pointer)}` |"
        )
    lines.append("")

    lines.append("## Font Context Setup")
    lines.append("")
    lines.append(
        "`0x1c5e8` installs the selected candidate into the primary current-font "
        "state before sample text is printed:"
    )
    lines.append("")
    lines.append("- writes selected context longword to `0x782ee6`;")
    lines.append("- stores context flag bits into `0x782eea` and `0x782eeb`;")
    lines.append("- maps the selected resource back to candidate slot `0x7828a8` via `0x1b4c0`;")
    lines.append("- clears primary/secondary selector `0x7828de` to primary;")
    lines.append("- reads active symbol word through `0x15890` or `0x158be` into `0x783144`;")
    lines.append("- runs selected-font activation/map rebuild through `0x14c64`;")
    lines.append("- marks current-font dirty byte `0x782f2d = 1`;")
    lines.append("- installs the current-font context into the page root through `0xc428`;")
    lines.append("- forces VMI words `0x783160/0x783162 = 0x0032/0x0000`;")
    lines.append("- forces HMI words `0x78315c/0x78315e = 0x001e/0x0000`.")
    lines.append("")
    lines.append(
        "This ties the font printout path to the same resource-selection, "
        "symbol-map, page-root font-slot, and printable text machinery already "
        "used by the host-byte fixtures. The remaining placement work is to "
        "model the surrounding `0x1c334` loop and compare the produced page "
        "objects against these direct payload hashes and a known printed/"
        "self-test sample."
    )
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
    lines.append("| `0x14c64` | selected font object dispatcher | if no matching active object exists, reads `0x7828a8`; bit-30 offset-table resource records update `0x783134`/`0x78313a` range words and `0x783132`/`0x783133` flags before `0x14d9c`, while bit-30-clear fixed-record resources call `0x14e24`; both paths then call `0x14f16` and `0x1440c` |")
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
    lines.append("- For built-in contexts, that bridge is now resolved: the selected context low 24 bits map to an `IC32,IC15` offset by subtracting `0x80000`; for both built-in and RAM-backed font-resource records, bit 30 selects the offset-table form, and table entries are relative 32-bit glyph-entry offsets from the selected record start.")
    lines.append("- The concrete `0x14c64` built-in cache-miss fixture selects record `0x009fb0`, narrows its `0x21..0xfe` base range to `0x21..0x7e` for active Roman Extension word `0x0005`, patches map byte `0x21` to glyph `0x80`, clears the upper half, and snapshots state at `0x783148` through `0x1440c`.")
    lines.append("- The synthetic `0x14c64` fixed-record cache-miss fixture writes selected byte `+0x0e` to `0x783132`, rebuilds map `0x782f32` through `0x14e24` / `0x14eb6`, maps host `0x21` to glyph `1`, and snapshots inline state byte `+8 = 1` at `0x783148` through `0x1440c`.")
    lines.append("- The payload-backed fixture now takes a table-validated `0x16fae` header allocated through `0x17026` / `0x1719c`; the `0x16c14` installed path selects it as a bit-30 offset-table resource through `0x14c64`/`0x14d9c` and `0x15890`, while a separate bit-30-clear control case proves the `0x14e24`/`0x14eb6` fixed-record form and `0x158be` `+0x17` encoded-symbol read.")
    lines.append("- The remaining font/text gap is live parser/font-state selection for those allocated records and candidate filters, so host bytes select the same compact glyph index documented in `ic30_ic13_text_glyph_index_flow.md` without hand-selected records.")
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
    lines.append("| 1 | `0x14c64` dispatches selected font activation through `0x14d9c` for bit-30 offset-table resources, or `0x14e24` for bit-30-clear fixed-record resources, then `0x14f16` and `0x1440c` | selected font changes rebuild one of the 256-byte character-to-glyph maps before text is queued |")
    lines.append("| 2 | `0x14d9c` chooses `0x782f32` or `0x783032` from `0x7828de`, reads selected record words `+0x0e` and `+0x10`, zero-fills before/after that range, and writes incrementing bytes through the range | built-in records get a base map where host character `first_char+n` maps to glyph index `n` before symbol-set patching |")
    lines.append("| 3 | `0x14e24` clears/map-fills the same 256-byte table through `0x14eb6`, which validates fixed records at `context_base+0x40+8*glyph` | bit-30-clear fixed-record resources use the same map bytes, but only for glyph slots that have valid records |")
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
    lines.append("- The renderer-side glyph identity is `(context longword, mapped byte)`. ROM built-in context low 24 bits map to `IC32,IC15` offset `address - 0x80000`; bit 30 selects the offset-table resource form for both ROM and RAM-backed records, and each table entry is a relative 32-bit offset from the record start.")
    lines.append("- The `0x14fce` symbol-set patch tables and their Technical Reference names are decoded in `ic30_ic13_symbol_set_patch_tables.md`; the harness now drives `ESC (2U` and `ESC )0E` through `0x120be`/`0x1be22`, traces the same stream through ROM parser setup handlers `0x1201e`/`0x12008` and terminal handler `0x120be`, applies the resulting `0x0055` patch table plus `0x0005` Roman Extension half-map to the `LINE_PRINTER` base map, separately traces `ESC (7X` plus `ESC )0@`/`ESC (1@`/`ESC )2@`/`ESC (3@`/`ESC )3@` through the same parser terminal path to pin the `X` font-ID and `@0..@3` special-case model, and now pins `0x1ac0a`/`0x1af36` default/fallback table-builder side effects that feed `@0`, `@1`, `@3`, and `0x156de` fallback selection; the live host parser path into `0x1393a` is documented in `ic30_ic13_printable_text_path.md`; paired cursor/queue/span paths after `0x1393a` are documented in `ic30_ic13_text_cursor_span_flow.md`; `tools/render_fixture_harness.py` now models a base-map -> `0x1393a` source-object -> `0xd824` positioning -> `0x12f2e` short bucket path for `LINE_PRINTER` host byte `0x21`, includes one-byte and two-byte normal printable stream fixtures for byte `0x21` through source mapping, `0xd550` default cursor advance, positioning, same-bucket queueing, and rendering, renders the initialized `LINE_PRINTER` HMI case where `0x10550(0x00480000)` produces advance `0x00120000` and compact coord `0x0202` / `$a001 = 0x12`, adds a mixed `ESC &k1G!\\r!` fixture where CR+LF positions the second glyph at coord `0x3b00` / `$a001 = 0x1b` and proves full-byte shifted blank-row clearing, traces that same mixed stream through parser handlers `0xedf8`, `0xd04a`, `0xf02c`, and `0xd04a` before page-record `0x1387c` allocation/reuse and `0x1edc6` bridge/rendering, adds a margin stream `ESC &a1L!` that routes `0xeb58` -> `0xd04a` before queueing/rendering the glyph at compact coord `0x0801` / pixel x `24`, adds cursor-position streams `ESC &a2C!` and `ESC &a1R!` that route `0xf39e` and `0xf560` -> `0xd04a` before queueing/rendering glyphs at compact coords `0x0a02` / pixel x `42` and `0x1001` / bucket `4`, adds a vertical-layout stream `ESC &l3E!` that routes `0xece2` -> `0xd04a` before queueing/rendering the glyph at compact coord `0x9001` in bucket `6`, and adds a mixed `!\\x1bE` fixture where reset publishes and clears a valid current page root after queued text and has the pre-reset object queued/bridged through page-record storage. It also covers the negative-left overflow branch, adds `0x1387c` page-record bucket allocator fixtures for short reuse, full-object new-head allocation, and segmented tall-glyph bucket allocation/reuse, adds a `0x1edc6` page-record bridge fixture for compact bucket/context-slot copying plus rule/fixed-list normalization, producer-shaped `0x13386`/`0x136d2` rule-list objects, and text/rule/raster plus simple execute/call and mixed-control macro execute parser-to-page-record checks and macro-payload rule/raster band composition, adds a selected inline/downloaded map/source fixture through `0x14e24`/`0x14eb6` -> `0x1393a` -> `0xd3b2` -> `0x12f2e` -> render plus `0x168dc`/`0x16942` font payload-reader fixtures, `0x172c0`/`0x16c14` downloaded-font record bookkeeping fixtures, `0x170be`/`0x17108`/`0x17150` record lookup/mark/unmark fixtures, `0x15a56`/`0x16df6` font-id/control dispatch fixtures, and `0x16fae`/`0x17362`/`0x17026`/`0x1719c` validation-table/staged-header/payload-backed inline allocation fixtures, keeps synthetic inline/downloaded records for `0x12f2e` short, page-record short, width-bit, segmented, and combined width+segmented payload shapes as isolation controls, constructs selected inline/downloaded wide, segmented, and segmented-wide fixed records for host bytes `0x23`, `0x24`, and `0x25` through `0x14e24`/`0x14eb6` -> `0x1393a` -> `0xd3b2` -> `0x12f2e`, renders those constructed records through `0x1f0d2`, `0x1f1f0`, and `0x1f264`, adds type-2 `0x1719c` payload-backed fixed-record coverage for the `0x1f0d2` and `0x1f1f0` cases, ties the `ESC *c4660d37e5F` ROM parser trace to the current id/current character used by the following descriptor and character payload fixtures, ties the `ESC )s0W` ROM parser trace to `0x15d0a` current-record and continuation descriptor routes, and ties the `ESC )s2193W` ROM parser trace to a `0x16498` downloaded character-object fixture that allocates the larger glyph `0x25` bitmap object, copies its split-plane payload through `0x16874`/`0x16942`, resolves it as a downloaded-pointer glyph, and renders the `0x1f264` segmented-wide row, models a segmented `0x2000` producer path for host byte `0x20`, adds a ROM-scanned built-in row-copy span matrix for spans 1, 2, 4, 6, and 8, and scans that all firmware-scanned built-in glyph records top out at mode-1 render span 8 for normal bitmaps, with the mode-0 tall targets being zero-delta aliases rather than normal bitmap entries. Remaining work is to replace the synthetic allocator/bridge and constructed font-download object bytes with parser-produced page roots, live font-download parser-populated inline/downloaded records, and full parser-produced page-object payloads.")
    lines.append("- The right-margin page-record boundary now covers `ESC &a1M!`: parser handler `0xec0c` moves the cursor/right margin to two initialized `LINE_PRINTER` HMI columns before printable `0xd04a` queues the glyph at compact coord `0x0a02` / pixel x `42` through the same bridge.")
    lines.append("- The chained-margin page-record boundary now covers `ESC &a6l9M!`: lowercase-final `ESC &a6l` leaves parser mode `12` open after handler `0xeb58`, `9M` reaches handler `0xec0c`, then printable `0xd04a` queues the glyph at compact coord `0x0207` / pixel x `114` through the same bridge.")
    lines.append("- The LF page-record boundary now covers `ESC &k2G!\\n!`: line-termination handler `0xedf8` sets mode `0x60`, LF handler `0xf08c` applies CR+LF before the second printable `0xd04a`, and the glyph queues at compact coord `0x3b00` through the same bridge.")
    lines.append("- The HT/BS page-record boundary now covers `ESC &k0G HT BS !`: parser handler `0xedf8` clears line-termination mode, HT reaches `0xf1cc`, BS reaches `0xf2a8`, then printable `0xd04a` queues the glyph at compact coord `0x0a01` / pixel x `26` through the same bridge.")
    lines.append("- The horizontal-decipoint page-record boundary now covers `ESC &a72H!`: parser handler `0xf416` converts 72 decipoints into 30 packed cursor units before printable `0xd04a` queues the glyph at compact coord `0x0402` / pixel x `36` through the same bridge.")
    lines.append("- The vertical-decipoint page-record boundary now covers `ESC &a72V!`: parser handler `0xf60a` converts 72 decipoints into packed cursor y `30` before printable `0xd04a` queues the glyph at compact coord `0x9001` in bucket `0` with nine blank rows before the bridged glyph body.")
    lines.append("- The chained cursor-position page-record boundary now covers `ESC &a2c+1R!`: lowercase-final `ESC &a2c` leaves parser mode `12` open after handler `0xf39e`, relative `+1R` reaches handler `0xf560`, then printable `0xd04a` queues the glyph at compact coord `0x1a02` in bucket `3` through the same bridge.")
    lines.append("- The cursor-stack page-record boundary now covers `ESC &f0S ESC &a2C ESC &f1S!`: parser handlers `0xf75e`, `0xf39e`, and `0xf75e` save, move, and restore the cursor before printable `0xd04a` queues the glyph at compact coord `0x0001` through the same page-record bridge.")
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
    lines.append("- The live parser path uses the same mapped glyph byte and context fields documented in `ic30_ic13_text_glyph_index_flow.md`; the symbol-set stream fixture now proves `ESC (2U`/`ESC )0E` route through ROM parser setup handlers `0x1201e`/`0x12008` and terminal handler `0x120be`, then update active primary/secondary words before `0x14f16` patches the `LINE_PRINTER` map; the next byte-to-pixel model must therefore drive `0xd04a`/`0x1393a`, not feed renderer glyph bytes directly from the host stream.")
    lines.append("- The paired cursor/queue/span behavior after `0x1393a` is detailed in `ic30_ic13_text_cursor_span_flow.md`; `tools/render_fixture_harness.py` now has one-byte and two-byte normal printable stream fixtures for `0x21` -> glyph `0x20` through `0xd824`, the simple `0xd550` default-advance branch, `0x12f2e`, and rendering. It also renders the initialized `LINE_PRINTER` HMI case, where `0x10550(0x00480000)` produces advance `0x00120000` and the second glyph compact coord `0x0202` decodes to `$a001 = 0x12` / pixel x `34`. The plain `!!` stream now has a ROM-parser trace through two `0xd04a` printable events tied to a page-record variant that allocates/reuses the compact object through `0x1387c` and bridges it through `0x1edc6`. The mixed `ESC &k1G!\\r!` fixture proves that line-termination mode is applied before the second printable byte is positioned, queueing it at coord `0x3b00` after CR+LF; the same stream now has a ROM-parser trace through `0xedf8`, `0xd04a`, `0xf02c`, and `0xd04a` tied to a page-record variant that allocates/reuses the compact object through `0x1387c` and bridges it through `0x1edc6`; `ESC &a1L!` now ties margin handler `0xeb58` to page-record queueing and renders the shifted glyph at compact coord `0x0801`; `ESC &a2C!` and `ESC &a1R!` tie cursor-position handlers `0xf39e` and `0xf560` to page-record queueing and render shifted glyphs at compact coords `0x0a02` and `0x1001`; `ESC &l3E!` ties top-margin handler `0xece2` to page-record queueing and renders the vertically shifted glyph at compact coord `0x9001` in bucket `6`; the mixed `!\\x1bE` fixture proves reset publication/clear state after queued text and has a page-record allocator/bridge/publication variant for the pre-reset object. The `0x1387c` allocator fixture now queues a short compact object into page-record bucket-array shape and covers the segmented tall-glyph page-record bucket sequence, and the `0x1edc6` bridge fixture proves how that compact bucket and context slot are copied into the render record. The remaining integration gap is to replace fixture-only state with fuller parser-allocated page roots before replacing the current producer-modeled text bucket fixtures.")
    lines.append("- `ESC &a1M!` now ties right-margin handler `0xec0c` to page-record queueing and proves right-margin cursor movement feeds the next printable `0xd04a` at compact coord `0x0a02`.")
    lines.append("- `ESC &a6l9M!` now ties lowercase-final margin chaining to page-record queueing: handler `0xeb58` leaves parser mode `12` active for `0xec0c`, and the next printable `0xd04a` lands at compact coord `0x0207` / pixel x `114`.")
    lines.append("- `ESC &k2G!\\n!` now ties LF handler `0xf08c` to page-record queueing: line-termination mode `0x60` causes CR+LF movement before the second printable `0xd04a`, which lands at compact coord `0x3b00`.")
    lines.append("- `ESC &k0G HT BS !` now ties direct HT/BS handlers to page-record queueing: `0xedf8` clears line termination, HT handler `0xf1cc` moves the cursor to x `21`, BS handler `0xf2a8` backs it up to x `20`, and printable `0xd04a` lands at compact coord `0x0a01` / pixel x `26`.")
    lines.append("- `ESC &a72H!` now ties horizontal-decipoint handler `0xf416` to page-record queueing and proves decipoint positioning feeds the next printable `0xd04a` at compact coord `0x0402`.")
    lines.append("- `ESC &a72V!` now ties vertical-decipoint handler `0xf60a` to page-record queueing and proves decipoint positioning feeds the next printable `0xd04a` at compact coord `0x9001` / bucket `0`.")
    lines.append("- `ESC &a2c+1R!` now ties lowercase-final cursor-position chaining to page-record queueing: handler `0xf39e` leaves parser mode `12` active for relative `0xf560`, and the next printable `0xd04a` lands at compact coord `0x1a02` / bucket `3`.")
    lines.append("- `ESC &f0S ESC &a2C ESC &f1S!` now ties the cursor-stack handler path to page-record queueing: the middle cursor move is undone by `0xf75e` pop before printable `0xd04a`, so the bridged glyph renders at restored-origin compact coord `0x0001`.")
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
    lines.append("- The active symbol-set stream fixture now carries `ESC (2U` and `ESC )0E` through ROM parser setup handlers `0x1201e`/`0x12008`, terminal handler `0x120be`, `0x1be22`, and `0xc580`, applies the resulting `LINE_PRINTER` map patches, and keeps the mapped-byte dependency upstream of positioning. The flagged `0xd824` positioning path, including the negative-left overflow branch, has executable queue/render fixtures in `tools/render_fixture_harness.py`, and printable stream fixtures now carry host byte `0x21` through `0x1393a`, `0xd824`, the simple `0xd550` default-advance branch for a second byte, `0x12f2e`, and rendering. The initialized `LINE_PRINTER` HMI case renders through the same path and proves compact coord `0x0202` as `$a001 = 0x12` / pixel x `34`; the mixed `ESC &k1G!\\r!` case proves CR+LF repositioning before the second printable byte, exposes full-byte shifted blank-row clearing, and now has a parser-traced page-record allocator/bridge variant for the same byte stream; `ESC &a1L!` ties the left-margin parser handler to a shifted compact text object at coord `0x0801`; `ESC &a2C!` and `ESC &a1R!` tie cursor-position parser handlers to shifted compact text objects at coords `0x0a02` and `0x1001`; `ESC &l3E!` ties the top-margin parser handler to a vertically shifted compact text object at coord `0x9001`; the mixed `!\\x1bE` case proves reset publication/clear state after queued text and now has a page-record allocator/bridge/publication variant for the pre-reset object. A `0x1387c` fixture queues short and segmented compact buckets into page-record shape, and a `0x1edc6` fixture bridges that compact bucket into render-record shape, pins rule/fixed-list normalization, and now includes producer-shaped `0x13386`/`0x136d2` rule-list objects. The `0xd3b2` fixtures now cover both unflagged positioning branches, a selected inline/downloaded map/source path through `0x14e24`/`0x14eb6` -> `0x1393a`, `0x168dc`/`0x16942` font payload-reader copying and continuation, `0x172c0` current-record scanning, `0x16c14` replacement/free-slot/no-slot bookkeeping, `0x170be` payload-record lookup, `0x17108`/`0x17150` current-record mark/unmark count transfer, `0x15a56`/`0x16df6` font-id/control dispatch, `0x16fae` validation-table and symbol-byte staging, `0x17362` setup-type handling, `0x17026` allocation-size/header staging, `0x1719c` sparse header initialization, synthetic inline/downloaded `0x12f2e` short/page-record/wide/segmented/combined payloads, type-2 payload-backed selected inline `0x1f0d2` wide and `0x1f1f0` segmented render rows, a selected-memory `0x1f264` segmented-wide isolation row, an `ESC *c4660d37e5F` parser/current-state boundary check feeding font install state, an `ESC )s0W` parser/route boundary check for `0x15d0a`, and an `ESC )s2193W` parser/object boundary check that reaches the `0x16498` downloaded-pointer `0x1f264` segmented-wide row. Remaining work is to use fuller parser-produced source/page objects and name the coordinate axes by comparing orientation, CR/LF/FF, and raster placement behavior.")
    lines.append("- The right-margin stream `ESC &a1M!` now proves `0xec0c` can move the horizontal cursor through the margin limit path and still feed printable `0xd04a` into page-record output at compact coord `0x0a02`.")
    lines.append("- The chained-margin stream `ESC &a6l9M!` now proves lowercase-final `0xeb58` can preserve parser mode for `0xec0c` and still feed printable `0xd04a` into page-record output at compact coord `0x0207` / pixel x `114`.")
    lines.append("- The LF stream `ESC &k2G!\\n!` now proves direct-control handler `0xf08c` consumes line-termination mode `0x60`, applies CR+LF movement, and feeds the next printable `0xd04a` into page-record output at compact coord `0x3b00`.")
    lines.append("- The HT/BS stream `ESC &k0G HT BS !` now proves direct-control handlers `0xf1cc` and `0xf2a8` can update the cursor/span state before printable `0xd04a` feeds page-record output at compact coord `0x0a01` / pixel x `26`.")
    lines.append("- The horizontal-decipoint stream `ESC &a72H!` now proves `0xf416` can convert decipoints through the horizontal cursor path and feed printable `0xd04a` into page-record output at compact coord `0x0402`.")
    lines.append("- The vertical-decipoint stream `ESC &a72V!` now proves `0xf60a` can convert decipoints through the vertical cursor path and feed printable `0xd04a` into page-record output at compact coord `0x9001` / bucket `0`.")
    lines.append("- The chained cursor-position stream `ESC &a2c+1R!` now proves lowercase-final horizontal positioning can keep parser mode `12` active for relative vertical positioning and still feed printable `0xd04a` into page-record output at compact coord `0x1a02` / bucket `3`.")
    lines.append("- The cursor-stack stream `ESC &f0S ESC &a2C ESC &f1S!` now proves the `0xf75e` push/pop path can bracket a cursor-position command and still feed printable `0xd04a` into page-record output at the restored compact coord `0x0001`.")
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
    lines.append("The executable harness now models both `0x1ac0a` branches and both `0x1af36` fallback branches: current-candidate mode copies `0x7828a4` into the relevant slots, while synthesized mode records one word per `0x78289f` orientation and `0x78289e` primary/secondary selector. It also pins the `0x1b250` outer current-default candidate path: `0x78219c == 0xff` disables it, otherwise `0x1b50e` supplies a resource address and word, `0x1b4c0` maps that low-24 address back to a canonical candidate slot, and `0x7827ac` decides the restored `0x78289f` orientation flag. `0x1b50e` is now pinned as a fast-probe-or-two-pass resolver: requested index `0` can accept `0x1b8ea`, while the scan path uses `0x1b750`/`0x1b7b2`/`0x1b8b6` to classify range, special-symbol, and downloaded candidates and to suppress the already-current Roman-8 slot; non-special requested words can count a Roman-8 candidate twice, with the duplicate ordinal writing the requested word instead of candidate word `0x0115`. `0x1ab84` is now pinned as the synthesized default search that tries `0x1adaa(1)` and `0x1adaa(2)` under the current orientation, flips `0x78289f` only after both miss, repeats both range searches, and finally falls through to `0x1ae7e`. It also pins the `0x1ad66` control flow: try `0x1adaa(1)` for `0x200000..0x3ffffe`, try `0x1adaa(2)` for `0x400000..0x5ffffe`, and fall back through `0x1ae7e` to either a `0x1b060` match or the bit-30-selected `0x15890`/`0x158be` base-candidate reader. `0x1bbfe` is now modeled as the bit-30 dispatcher into `0x15890`/`0x158be`, and `0x1b060` is modeled as the default-candidate predicate over orientation, pitch `0x03e8`, height `0x04b0`, style bytes, spacing byte `3`, and requested-symbol fallback rules. The remaining live-state gap is selection and filtering over the concrete `0x1a9be` candidate windows, not the table writes, `@` parser exposure, scanner partitioning, built-in record identities, `0x1b250`/`0x1b50e` result plumbing, `0x1ab84`/`0x1ad66` list/range/fallback control flow, or the `0x1bbfe`/`0x1b060` helper logic.")
    lines.append("")

    lines.append("## Refresh and Active Selection")
    lines.append("")
    lines.append("| Step | Firmware evidence | Reproduction meaning |")
    lines.append("| ---: | --- | --- |")
    lines.append("| 1 | `0x1be22` writes the requested word into `0x782ef4 + 0x10*slot` and marks `0x782f2c`/`0x782f2d` | host symbol-set command changes the requested font-selection criteria, not just a renderer flag |")
    lines.append("| 2 | `0x120be` immediately calls `0xc580` | symbol-set commands run the same common refresh used by other font-selection commands |")
    lines.append("| 3 | `0xc580` reads the slot from the parser record, checks dirty flag `0x782f2c`, and calls `0x13eb8` and/or `0xc428` depending on current slot state | requested symbol-set changes can rebuild selected font context and reinstall it into page-root font slots |")
    lines.append("| 4 | `0x156de` reads `0x782ef4` for primary or `0x782f04` for secondary, uses `0x783f00` as the initial normalized-symbol flag, and scans the active candidate list | the requested PCL word becomes the filter key for built-in/downloaded font candidates |")
    lines.append("| 5 | If the requested word has no active match, `0x156de` retries the remembered word from `0x782f08`/`0x782f0a`; if that is unchanged or still misses, it loads the `0x782f0c..18` fallback-table word and normalizes that fallback through `0x15850` | fallback/default handling changes the active word before final pruning |")
    lines.append("| 6 | `0x156de` writes the selected active word to `0x783144` for primary or `0x783146` for secondary, then makes a second active-list pass that clears bit 31 on rejects, moves `0x78287c` to the first survivor, and shrinks `0x7827b8` | these are the active words and surviving candidates consumed later by character-map setup |")
    lines.append("| 7 | `0x1440c` snapshots `0x783144`/`0x783146` into selected-font state records at `0x783148`/`0x783152` offset `+4` | active object comparison can reject cached state when the symbol set changes |")
    lines.append("| 8 | `0x14f16` reads `0x783144` or `0x783146` after base map initialization | Roman-8 built-in maps are patched according to the active requested symbol set before text objects are queued |")
    lines.append("| 9 | `0xc580` and the orientation handler `0x10220` copy active words into `0x782f08`/`0x782f0a` | these remembered values are fallback/default inputs if current candidate selection cannot satisfy the requested word |")
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
    lines.append("- `tools/render_fixture_harness.py` now traces host-visible `ESC (7X`, `ESC )0@`, `ESC (1@`, `ESC )2@`, `ESC (3@`, and `ESC )3@` streams through parser setup handlers `0x1201e`/`0x12008` and terminal handler `0x120be`, then checks the modeled `0x1be22` special-case targets `0x1c066`, `0x1bed4`, `0x1bf0a`, `0x1bf36`, and `0x1bf74`.")
    lines.append("- Reproduce `0x1ac0a` and `0x1af36` table writes before applying `@0`/`@1` or font-selection fallback behavior; the harness now checks the current-candidate and synthesized-candidate table shapes.")
    lines.append("- Reproduce `0x1a9be` scanner-side candidate-list partitioning before default-font searches: every accepted record increments `0x78278e`; class `1` increments `0x782790` and splits low built-in-resource candidates into `0x782792` and cartridge/extension-range candidates into `0x782794`; class `0` increments `0x782798` and splits the same ranges into `0x78279a` and `0x78279c`; the cursor windows at `0x7827a0..0x7827b4` advance cumulatively across those partitions.")
    lines.append("- For the verified `IC32,IC15` resource ROM, the built-in scan contributes 24 concrete `HEAD`-path records: twelve class `0` and twelve class `1`, all in the low built-in resource window. The extension-range counters stay zero until cartridge/external resource ranges are scanned.")
    lines.append("- Reproduce `0x1569c` active-list setup: `0x782da3 == 0` selects class-zero pointer/count `0x7827ac`/`0x782798`, while nonzero selects class-one pointer/count `0x7827a0`/`0x782790`; for the verified built-ins these become `0x782354`/`12` and `0x782324`/`12`, and selected entries are marked with active bit `0x80000000`.")
    lines.append("- Reproduce `0x156de` as a two-pass active-list filter: find a satisfiable requested/remembered/fallback symbol word using exact match, normalized Roman-8 match, or the compatibility pairs at `0x15840`; then clear the active bit on rejected entries, move `0x78287c` to the first retained slot, and write the retained count to `0x7827b8`. The harness now pins class-zero primary `0x0115` over the real built-ins as slots `0x782354/0x782364/0x782374`, and a class-one secondary miss falling through to fallback word `0x000e` as slots `0x782330/0x782340/0x782350`.")
    lines.append("- Reproduce `0x1ad66` as a three-stage default-font candidate search: range class 1, then range class 2, then `0x1ae7e` fallback. Range hits filter candidate high-nibble flags by primary/secondary slot mask and low-24-bit resource address range before `0x1bbfe` dispatches symbol-word reads to `0x15890` for bit-30 offset-table resources or `0x158be` for bit-30-clear fixed-record resources. Fallback first accepts a `0x1b060` match, where the helper validates orientation, pitch, height, style, and spacing, then accepts either exact requested-symbol matches or Roman-8 fallback for non-excluded requested words; accepted `0x1b060` candidates write the requested word from `0x7821a0` to `0x7828a4`.")
    lines.append("- Treat `0x782ef4`/`0x782f04` as requested criteria and `0x783144`/`0x783146` as the active post-selection words.")
    lines.append("- Rebuild the selected primary/secondary character-to-glyph map after symbol-set changes, then apply the `0x14f16` patch rules documented in `ic30_ic13_symbol_set_patch_tables.md`; `tools/render_fixture_harness.py` now drives `ESC (2U` and `ESC )0E` through both the ROM parser trace and symbol-set stream model, then applies the resulting `0x0055` patch-table and `0x0005` Roman Extension map rules to the `LINE_PRINTER` base map.")
    lines.append("- Do not feed host bytes directly to `0x1f354`; the queued compact glyph byte must come from the active map selected by this flow.")
    lines.append("")
    return "\n".join(lines)


def symbol_set_patch_table_report(data: bytes, resources: bytes = b"") -> str:
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

    def base_map_for_record(record: dict[str, int | str | None]) -> list[int]:
        first_char = int(record["first_char"])
        last_char = int(record["last_char"])
        mapping = [0] * 0x100
        for char in range(first_char, last_char + 1):
            mapping[char & 0xFF] = (char - first_char) & 0xFF
        return mapping

    def apply_14f16_to_map(mapping: list[int], symbol_word: int) -> list[int]:
        out = list(mapping)
        if symbol_word == 0x0005:
            out[:0x80] = out[0x80:0x100]
            out[0x80:0x100] = [0] * 0x80
            return out
        if symbol_word == 0x0015:
            out[0x80:0x100] = [0] * 0x80
            return out
        for entry in entries:
            if int(entry["symbol_value"]) != symbol_word:
                continue
            pairs = entry["pairs"]
            assert isinstance(pairs, list)
            for dst, src in pairs:
                out[dst] = out[src]
            out[0x80:0x100] = [0] * 0x80
            return out
        return out

    def record_summary(record: dict[str, int | str | None]) -> str:
        return (
            f"`0x{int(record['record_start']):06x}` "
            f"{record['name']} class {int(record['class_byte'])}"
        )

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

    if resources:
        records = firmware_scanned_font_records(resources)
        by_symbol: dict[int, list[dict[str, int | str | None]]] = {}
        for record in records:
            by_symbol.setdefault(int(record["symbol_word_0x22"]), []).append(record)

        lines.append("## Verified Built-In Symbol Inventory")
        lines.append("")
        lines.append("These are the symbol words exposed by the 24 firmware-scanned `HEAD` path font records in `IC32,IC15`. Roman-8 (`8U`) records are the ones whose maps can be altered by `0x14f16`; the other built-in symbol words are selected as separate font records rather than patched through the Roman-8 table.")
        lines.append("")
        lines.append("| Symbol word | PCL code | Name | Count | Record starts | Character ranges |")
        lines.append("| ---: | --- | --- | ---: | --- | --- |")
        for symbol_word in sorted(by_symbol):
            group = by_symbol[symbol_word]
            starts = ", ".join(
                f"`0x{int(record['record_start']):06x}`"
                for record in group
            )
            ranges = sorted({
                "0x%02x..0x%02x" % (
                    int(record["first_char"]),
                    int(record["last_char"]),
                )
                for record in group
            })
            lines.append(
                "| `0x%04x` | `%s` | %s | %d | %s | %s |"
                % (
                    symbol_word,
                    pcl_symbol_set_code(symbol_word),
                    symbol_set_name(symbol_word),
                    len(group),
                    starts,
                    ", ".join(f"`{item}`" for item in ranges),
                )
            )
        lines.append("")

        sample_chars = [0x21, 0x23, 0x24, 0x5B, 0x5C, 0x5D, 0x7E, 0xA1]
        roman8_record = by_symbol.get(0x0115, [None])[0]
        if roman8_record is not None:
            base_map = base_map_for_record(roman8_record)
            scenarios = [
                (0x0115, "base Roman-8 / no `0x14fce` hit"),
                (0x0015, "`0U` ISO 6 ASCII hard-coded upper clear"),
                (0x0005, "`0E` Roman Extension hard-coded upper-half copy"),
                (0x0055, "`2U` IRV patch table"),
                (0x0025, "`1E` UK patch table"),
                (0x0007, "`0G` German patch table"),
            ]
            lines.append("## Real Roman-8 Map Samples")
            lines.append("")
            lines.append("The table below starts from the first scanned Roman-8 built-in record, then applies the same `0x14f16` rules that run after `0x14d9c`. Values are compact glyph bytes queued by `0x12f2e`, not final host bytes.")
            lines.append("")
            lines.append(f"Record: {record_summary(roman8_record)}")
            lines.append("")
            lines.append("| Active symbol | Meaning | " + " | ".join(f"`0x{char:02x}`" for char in sample_chars) + " |")
            lines.append("| --- | --- | " + " | ".join("---:" for _ in sample_chars) + " |")
            for symbol_word, meaning in scenarios:
                patched = apply_14f16_to_map(base_map, symbol_word)
                samples = " | ".join(f"`0x{patched[char]:02x}`" for char in sample_chars)
                lines.append(f"| `{pcl_symbol_set_code(symbol_word)}` | {meaning} | {samples} |")
            lines.append("")

        lines.append("## Non-Roman-8 Built-In Base Samples")
        lines.append("")
        lines.append("These records do not enter the `0x14f16` Roman-8 patch table unless selected font normalization changes to `0x0115`; their exact glyph bytes come from their own built-in base ranges.")
        lines.append("")
        lines.append("| Symbol | Record | " + " | ".join(f"`0x{char:02x}`" for char in sample_chars) + " |")
        lines.append("| --- | --- | " + " | ".join("---:" for _ in sample_chars) + " |")
        for symbol_word in sorted(by_symbol):
            if symbol_word == 0x0115:
                continue
            record = by_symbol[symbol_word][0]
            mapping = base_map_for_record(record)
            samples = " | ".join(f"`0x{mapping[char]:02x}`" for char in sample_chars)
            lines.append(
                f"| `{pcl_symbol_set_code(symbol_word)}` | "
                f"{record_summary(record)} | {samples} |"
            )
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


def page_root_allocation_report(data: bytes) -> str:
    def fmt_refs(refs: list[int]) -> str:
        if not refs:
            return "(none)"
        text = ", ".join(f"`0x{ref:06x}`" for ref in refs[:12])
        if len(refs) > 12:
            text += f", ... ({len(refs)} total)"
        return text

    caller_groups = [
        ("printable text, unflagged and flagged handoffs", [0x00D20A, 0x00D49A, 0x00D63C, 0x00D8EA]),
        ("display-function/text fallback and post-finalize parser recovery", [0x00D9EC, 0x00DA4C, 0x00FF9A]),
        ("direct controls and cursor-positioning page advances", [0x00F0B6, 0x00F10C, 0x00F17A, 0x00F2B0, 0x00F576, 0x00F6EE]),
        ("raster and rectangle producers", [0x0106A4, 0x0106EC, 0x010D0A, 0x010D38]),
        ("text span flush and font/page setup paths", [0x012788, 0x0127C4, 0x012912, 0x01C2D2, 0x01CA08, 0x01E0EE, 0x01E922]),
    ]

    lines = ["# IC30/IC13 Page-Root Allocation Flow", ""]
    lines.append("Generated from the focused disassembly window `generated/disasm/ic30_ic13_page_root_allocate_010084.lst` plus cross-reference scans of the verified firmware image.")
    lines.append("This report pins the page/control record allocation boundary that text, raster, rules, direct controls, and reset/finalization all depend on before the `0x1edc6` render-record bridge.")
    lines.append("")

    lines.append("## `0x10084` Ensure-Root Contract")
    lines.append("")
    lines.append("| Address | Instruction fact | Reproduction consequence |")
    lines.append("| ---: | --- | --- |")
    lines.append("| `0x1008c..0x10094` | loads current root `0x78297a` into `A5`/`D7` and branches to return when nonzero | existing page roots are reused without reinitializing queues, font slots, or stream-storage state |")
    lines.append("| `0x10096..0x100a6` | tests pending bytes `0x782c73` and `0x782c72`; if either is set, calls `0x9ac2` at `0x100b0` | pending active-record/page work can run before the first root allocation |")
    lines.append("| `0x100b6..0x100bc` | clears `0x782c73` and `0x782c72` after the wait/helper path | the allocation boundary consumes those pending latches |")
    lines.append("| `0x100c2` | calls allocator `0x9a9a`; returned `D7` becomes the new root pointer | page roots are allocated from the page/control record pool, not from the later 0x100-byte display-list chunks |")
    lines.append("| `0x100ca..0x100d6` | wraps root byte `+4 = 1` with `0x15a6` / `0x15ac` | new roots start as active class/state `1` before the initializer runs |")
    lines.append("| `0x100dc..0x100e6` | clears stream byte count `0x782a70`, computes `A2 = root + 0x20`, and stores it in `0x782a72` | the root's `+0x20` longword is the head link for display-list storage chunks |")
    lines.append("| `0x100ec..0x100f8` | stores the root in `0x78297a`, calls initializer `0x10110`, and clears `0x782990` | subsequent producers see the initialized current root and a cleared transient byte |")
    lines.append("| `0x100fe..0x1010e` | loads `A4 = root+0x1c`, clears 256 longwords, then loops back to the fast-return path | compact/raster bucket heads are a 256-entry array at root `+0x1c`; allocation itself does not seed `0x782a76` |")
    lines.append("")

    lines.append("## `0x10110` Root Initializer")
    lines.append("")
    lines.append("| Root field | Instruction fact | Current interpretation |")
    lines.append("| ---: | --- | --- |")
    lines.append("| `+0x06` | `0x1013a` copies page-code byte `0x782da2` | root records the current page size code |")
    lines.append("| `+0x08`, `+0x0a` | `0x10142..0x10146` clear both bytes | root-local publication/status flags start clear |")
    lines.append("| `+0x0e`, `+0x10` | `0x10124..0x1012a` stores longword `-1` at `+0x10` and clears word `+0x0e` | page-band/start fields are reset before render scheduling |")
    lines.append("| `+0x14` | `0x1014a` clears the root flags word | finalize/retry flags start clear on a fresh root |")
    lines.append("| `+0x16` | `0x10158..0x10174` divides extent word `0x782db2` by `0x10` via `0x3324a` and stores the result | render/page width bucket count or band extent is derived from active horizontal extent |")
    lines.append("| `+0x20` | `0x1014e` clears the display-list chunk head | the stream allocator will link 0x100-byte object-storage chunks here later |")
    lines.append("| `+0x24`, `+0x28` | `0x10178..0x1017c` clears both list heads | rule/list and fixed-list queues start empty until producers insert objects |")
    lines.append("| `+0x09` | `0x10186..0x101ae` adds `0x782db4 + 0x782dc0 + 0x20`, divides by `0x20`, and stores the low byte | vertical/band extent derives from page height plus printable offset |")
    lines.append("| `+0x2c..+0x68` | `0x101d6..0x10212` clears all 16 context slots/live flags, then copies the current selected font-context longword into slot 0 | a fresh root has exactly one active render context until printable/font setup installs more slots |")
    lines.append("")

    lines.append("## Call-Site Groups")
    lines.append("")
    lines.append(f"Absolute `JSR` references to `0x10084`: {fmt_refs(jsr_abs_refs(data, 0x00010084))}.")
    lines.append("")
    lines.append("| Producer family | Observed call sites | Reproduction implication |")
    lines.append("| --- | --- | --- |")
    for label, refs in caller_groups:
        observed = [ref for ref in refs if ref in jsr_abs_refs(data, 0x00010084)]
        lines.append(f"| {label} | {fmt_refs(observed)} | these producers share the same root allocation and bucket/list initialization boundary |")
    lines.append("")

    lines.append("## Current Reproduction Contract")
    lines.append("")
    lines.append("- A byte-stream reproduction must call the root-allocation boundary before any text/raster/rule producer writes under root `+0x1c`, `+0x24`, or `+0x28`; otherwise object identity and render ordering will not match the firmware.")
    lines.append("- `0x10084` initializes the root and bucket array, but display-list object payload storage is still allocated later through `0x1381c`; the harness fixture therefore deliberately leaves `0x782a76` unchanged after first-root creation.")
    lines.append("- The existing `tools/render_fixture_harness.py` checks `0x10084-modeled page-root allocation side effects`, `0x10110 page-root initializer installs selected context slot`, and `0x10110 page-root initializer copies geometry fields` pin these side effects in executable form before queueing short compact text through `0x1387c` and bridging through `0x1edc6`; the raster transfer fixture now also carries the same modeled allocation record through `0x105d0` before `0x13070` / `0x13250` queue the primary row object.")
    lines.append("- The remaining fidelity gap is a live parser-state run that lets `0xd04a`/`0xd824`, `0x105d0`, or `0x10b80` call this allocator with real page/control pool records instead of the current abstract root pointer.")
    lines.append("")
    return "\n".join(lines)


def page_root_finalization_report(data: bytes) -> str:
    def fmt_refs(refs: list[int]) -> str:
        if not refs:
            return "(none)"
        text = ", ".join(f"`0x{ref:06x}`" for ref in refs[:12])
        if len(refs) > 12:
            text += f", ... ({len(refs)} total)"
        return text

    caller_groups = [
        ("reset and page/control publication", [0x00CC92, 0x00EF96, 0x00F128]),
        ("printable text retry/finalize paths", [0x00D494, 0x00D8E4, 0x00DA30, 0x00DA86]),
        ("text span flush retry path", [0x0127BE]),
        ("page geometry and layout changes", [0x00FA68, 0x00FB10, 0x00FCAA, 0x00FD6E, 0x010262]),
        ("raster transfer page-boundary path", [0x0106E6]),
        ("rectangle/rule queue retry path", [0x010D32]),
        ("font-slot/default update flush path", [0x01BA76]),
    ]

    lines = ["# IC30/IC13 Page-Root Finalization Flow", ""]
    lines.append("Generated from `generated/disasm/ic30_ic13_page_root_finalize_00ff1e.lst` plus cross-reference scans of the verified firmware image.")
    lines.append("This report pins the publication boundary after a current page root has accumulated text, raster, or rule objects and before reset, FF, or page-geometry changes clear that root.")
    lines.append("")

    lines.append("## `0xff1e` Finalize Contract")
    lines.append("")
    lines.append("| Address | Instruction fact | Reproduction consequence |")
    lines.append("| ---: | --- | --- |")
    lines.append("| `0xff26..0xff3e` | tests current root `0x78297a`; if it is null or root byte `+4` is not `1`, branches to `0xffa2` | missing or non-active roots are discarded by clearing `0x78297a` without publication |")
    lines.append("| `0xff40..0xff66` | when page/parser state byte `0x782a92 == 1`, tests root flags word `+0x14` bit 0; if set, skips the parser-reentry detour | bit 0 marks a root that has already taken the retry/finalize path and should publish without recursive parser work |")
    lines.append("| `0xff68..0xff72` | passes saved longword `0x782a94` to helper `0xe0a4` | partial command/data state can be restored before finalizing the root |")
    lines.append("| `0xff74..0xff9a` | if current parser/data-chain object `0x782d7a` exists and its first longword is nonzero, stores `0x782a92 = 2`, calls `0xe4f4`, re-enters parser loop `0x11774`, and ensures a root through `0x10084` | finalization can run pending parser/data-chain bytes before publishing the page record |")
    lines.append("| `0xffb0..0xffcc` | loads active root into `A5`, clears transient bytes `0x78297e`, `0x782c72`, `0x782c73`, clears root word `+0x18`, and copies root `+0x16` to `+0x1a` | publication snapshots final band/extent metadata and consumes transient root-allocation latches |")
    lines.append("| `0xffd2..0x1003e` | consumes flags `0x782997`, `0x780e99`, and `0x782998`, setting root byte `+8` or bits 0/1 in root byte `+0x0a` while wrapping writes in `0x15a6`/`0x15ac` | pending page/control status bytes become root-local publication flags before the record is handed off |")
    lines.append("| `0x10044..0x1005a` | copies `0x782da6` to root byte `+7` and `0x782da4` to root word `+0x0c` | finalized records carry current page/environment metadata in the root header |")
    lines.append("| `0x10060..0x10080` | writes root byte `+4 = 2`, copies root longword `+0` to `0x780ea6`, sets `0x782996 = 1`, then branches to clear `0x78297a` | active root state `1` becomes published state `2`; the backing pool record is exposed to the page/control scheduler and current-root ownership is dropped |")
    lines.append("")

    lines.append("## Call-Site Groups")
    lines.append("")
    all_refs = jsr_abs_refs(data, 0x0000FF1E)
    lines.append(f"Absolute `JSR` references to `0xff1e`: {fmt_refs(all_refs)}.")
    lines.append("")
    lines.append("| Caller family | Observed call sites | Reproduction implication |")
    lines.append("| --- | --- | --- |")
    for label, refs in caller_groups:
        observed = [ref for ref in refs if ref in all_refs]
        lines.append(f"| {label} | {fmt_refs(observed)} | these paths share the same publish-or-clear contract before continuing |")
    lines.append("")

    lines.append("## State Reference Scan")
    lines.append("")
    state_addresses = [
        (0x0078297A, "current page root consumed and cleared by `0xff1e`"),
        (0x00782A92, "page/parser finalization state tested for the parser-reentry detour"),
        (0x00782A94, "saved command/data key restored through helper `0xe0a4`"),
        (0x00782D7A, "current parser/data-chain object tested before re-entering `0x11774`"),
        (0x0078297E, "transient root/font-slot byte cleared on publication"),
        (0x00782C72, "pending allocation/finalization latch cleared on publication"),
        (0x00782C73, "pending allocation/finalization latch cleared on publication"),
        (0x00782997, "pending status bit copied into root byte `+0x0a` bit 0"),
        (0x00780E99, "pending status byte copied into root byte `+8`"),
        (0x00782998, "pending status bit copied into root byte `+0x0a` bit 1"),
        (0x00782DA6, "page/environment byte copied into finalized root `+7`"),
        (0x00782DA4, "page/environment word copied into finalized root `+0x0c`"),
        (0x00780EA6, "published page/control pool record pointer written from root longword `+0`"),
        (0x00782996, "page/control publication flag set after root state changes to `2`"),
    ]
    lines.append("| Address | Current finalization role | Longword literal references |")
    lines.append("| ---: | --- | --- |")
    for address, role in state_addresses:
        lines.append(f"| `0x{address:08x}` | {role} | {fmt_refs(find_all(data, address.to_bytes(4, 'big')))} |")
    lines.append("")

    lines.append("## Current Reproduction Contract")
    lines.append("")
    lines.append("- A page-root reproduction must distinguish the no-publication clear path from the active-root publication path: only active roots with byte `+4 == 1` are promoted to state `2` and exposed through `0x780ea6`.")
    lines.append("- The finalizer is not a pure state copy. In the `0x782a92 == 1` case it can restore saved command/data state, re-enter the parser at `0x11774`, and ensure a root again before publication.")
    lines.append("- The published pool record must preserve the root-header fields written by `0xff1e`: state byte `+4`, environment byte `+7`, status byte `+8`, status bits in `+0x0a`, environment word `+0x0c`, the `+0x16` to `+0x1a` copy, cleared `+0x18`, queue root `+0x1c`, rule/fixed roots `+0x24/+0x28`, and context slots from `+0x2c`.")
    lines.append("- Reset, FF, page-size, orientation, text retry, rectangle/rule queue retry, font-slot/default update, and raster page-boundary paths all share this finalizer; byte-perfect reproduction should therefore compare the same published root shape at this boundary before rendering through `0x1edc6`.")
    lines.append("- `tools/render_fixture_harness.py` already models valid-root publication, missing-root clear, mixed printable reset/FF/page-geometry publication, and the `0xff1e` header-field copies for default and nonzero status/environment state. The remaining fidelity gap is to replace those fixture-only source/root objects with roots produced by the full parser and allocator path.")
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
    lines.extend(textwrap.wrap(
        "Classifications are manual notes from focused disassembly; this report is "
        "a lead index, not a complete call graph.",
        width=78,
        break_long_words=False,
        break_on_hyphens=False,
    ))
    lines.append("")
    for value, (role, notes) in tracked.items():
        offsets = find_long_occurrences(data, value)
        lines.append(f"## `{value:#010x}`")
        lines.append("")
        lines.extend(textwrap.wrap(
            role,
            width=78,
            initial_indent="Role: ",
            subsequent_indent="      ",
            break_long_words=False,
            break_on_hyphens=False,
        ))
        lines.append("")
        lines.append("| Offset | Current classification |")
        lines.append("| --- | --- |")
        for offset in offsets:
            note = notes.get(offset, "unclassified alias/reference lead")
            lines.append(f"| `0x{offset:06x}` | {note} |")
        if not offsets:
            lines.append("| | no occurrences |")
        lines.append("")
    lines.extend(textwrap.wrap(
        "Current result: `0x1edc6` is the first confirmed bridge from queued "
        "page/control records into a render work record, and its concrete "
        "queue/list/context-slot copy contract is decoded in "
        "`ic30_ic13_page_record_bridge.md`. `0x1ef6a` and helpers then render "
        "a band using `0x783a18`, `0x783a1c`, `0x783a28`, and buffer base "
        "`0x7810b4`; complete parser-produced page objects and all merge rules "
        "remain to be decoded.",
        width=78,
        break_long_words=False,
        break_on_hyphens=False,
    ))
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

    lines.append("## Render Band Setup `0x1ef86`")
    lines.append("")
    lines.append("Before the bucket/list dispatchers run, `0x1ef6a` calls `0x1ef86` with the current render record in `A6`. The helper computes `(word +0x10 + word +0x08 - word +0x0a) / word +0x06` using unsigned word division, stores the remainder in `0x783a22`, stores `(word +0x06 - remainder) << 4` in `0x783a20`, and stores `long +0x00 + ((remainder << 6) * word +0x04)` in both `0x783a28` and render-record long `+0x12`.")
    lines.append("`tools/render_fixture_harness.py` now has an executable `0x1ef86` fixture that pins those four outputs before the `0x1efc2` bucket-chain dispatch check.")
    lines.append("")

    lines.append("## Render Entry Call Order `0x1ef6a`")
    lines.append("")
    lines.append("The render entry calls `0x1ef86`, `0x1efc2`, `0x1f446`, and `0x1f756` in that order for the current render record. The executable fixture now feeds one synthetic render record containing compact text and encoded raster bucket objects at `+0x18`, a selector-7 rule list at `+0x1c`, and a fixed-width list at `+0x20`, then verifies the layer composition in that same call order.")
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

    lines.append("## Fixed-Width List Renderer `0x1f756`")
    lines.append("")
    lines.append("After bucket and rule-list rendering, `0x1ef6a` calls `0x1f756` for render-record list `+0x20`. It runs only when render word `+0x10` is on a five-band boundary, filters objects by byte `+4 <= band+4`, skips objects whose word `+0x0a` is non-positive, uses byte `+5 & 0x0f` as an index into longword table `0x308de`, then calls `0x1f7b0`. The helper clears bridge flag bit `0x10`, uses word `+6` as the packed coordinate, subtracts the available rows from word `+0x0a`, clips the current draw count, and writes the selected low pattern word once per row through the `0x1f626` destination helper.")
    lines.append("`tools/render_fixture_harness.py` now has an executable `0x1f756` fixture that renders one normalized `+0x20` object, verifies the table longword, and checks the post-render object mutation.")
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
    lines.append("- `tools/render_fixture_harness.py` now has a `0x1ed84`/`0x1edc6` fixture that copies source words `+0x18/+0x1a` into render-record header words `+0x0a/+0x0c/+0x10/+0x16`, clears render word `+0x0e`, bridges a compact text bucket, verifies the copied context slot can render the same glyph rows, pins the render-record destination offsets `+0x18/+0x1c/+0x20/+0x24`, pins both list-normalization side effects, pins `0x1ef86` render-band remainder/base-pointer setup, `0x1efc2` selected-bucket class dispatch, `0x1f812` segment-list rendering, `0x1f756` fixed-width list rendering, and the `0x1ef6a` call order over bucket/rule/fixed-width consumers, composes a non-overlapping compact text bucket plus selector-7 rule from the same bridged render record into one page band, overlays a separately bridged mode-0 raster row into that same band, traces simple execute/call and mixed-control macro execute payloads from the `0xa904` data-chain through parser handlers into the same page-record streams, composes a macro execute payload page-record layer with the same selector-7 rule and mode-0 raster row, and carries reset/FF/page-size/orientation `0xff1e` published records through `0x1ed84` and `0x1ef6a`. The remaining gap is fuller live-parser page-object allocation and the true heterogeneous bucket-chain/full-page merge.")
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
    lines.append("- The executable `0x1381c` stream-allocator fixture now pins first-chunk allocation, same-chunk reuse, second-chunk linking through the previous chunk's first longword, `0x782a70` remaining-byte accounting, `0x782a72` link-field movement, and `0x782a76` next-free updates. The addressed `0x133aa` and `0x136d2` fixtures now use the same allocator for 14-byte rectangle/rule entries under page-root `+0x24` and `+0x28`, pinning bucket-byte ordered insertion, including equal-bucket insertion after the existing equal entry.")
    lines.append("- The address-aware `0x1387c` fixture now pins how that stream allocation becomes a bucket object: first allocation writes selector `+4` and bucket head `root+0x1c[0x782a7c]`, reuse returns the same object while count `+6` is below capacity, and a full matching object forces a new head whose longword `+0` points to the prior object.")
    lines.append("- A composed addressed page-record fixture now materializes one `+0x1c` compact bucket, one `+0x24` rule list, and one `+0x28` fixed list by following the allocated objects' `+0` links, then carries those bytes through `0xff1e`, `0x1ed84`, and `0x1edc6` to prove the addressed stream objects match the existing render-record bridge contract.")
    lines.append("- `tools/render_fixture_harness.py` now has executable `0x1387c` fixtures for short reuse, full-object new-head allocation, segmented tall-glyph bucket allocation/reuse, and printable, mixed printable/control, printable/reset, left/right-margin-positioned printable, horizontal/vertical cursor-positioned printable, horizontal/vertical-decipoint-positioned printable, chained cursor-positioned printable, vertical-layout-positioned printable, simple macro execute, and mixed-control macro execute byte streams that queue through page-record storage before bridging through `0x1edc6`; the plain `!!` path is tied to two ROM parser `0xd04a` events, the mixed `ESC &k1G!\\r!` path is tied to ROM parser handlers `0xedf8`, `0xd04a`, `0xf02c`, and `0xd04a`, the margin `ESC &a1L!` and `ESC &a1M!` paths are tied to `0xeb58`/`0xec0c` then `0xd04a`, the cursor-position `ESC &a2C!`, `ESC &a72H!`, `ESC &a1R!`, `ESC &a72V!`, and `ESC &a2c+1R!` paths are tied to `0xf39e`/`0xf416`/`0xf560`/`0xf60a` plus lowercase-chain `0xf39e`/`0xf560` then `0xd04a`, the top-margin `ESC &l3E!` path is tied to `0xece2` then `0xd04a`, the macro execute replayed `!\\r` path is tied to parser handlers `0xd04a` and `0xf02c`, the macro execute replayed `ESC &k1G!\\r!` path is tied to `0xedf8`, `0xd04a`, `0xf02c`, and `0xd04a`, and the harness also renders a short object queued through that page-record allocator before bridging it through `0x1edc6`.")
    lines.append("- The same page-record coverage now includes cursor-stack-positioned text: `ESC &f0S ESC &a2C ESC &f1S!` routes through `0xf75e`/`0xf39e`/`0xf75e` before printable `0xd04a`, proving the pop restores compact coord `0x0001` before queue/bridge/render.")
    lines.append("- The same page-record coverage now includes chained margin-positioned text: `ESC &a6l9M!` routes lowercase-final `0xeb58` and final `0xec0c` before printable `0xd04a`, proving compact coord `0x0207` / pixel x `114` before queue/bridge/render.")
    lines.append("- The same page-record coverage now includes LF-positioned text: `ESC &k2G!\\n!` routes through `0xedf8`/`0xd04a`/`0xf08c`/`0xd04a`, proving LF mode `0x60` applies CR+LF before queueing the second glyph at compact coord `0x3b00`.")
    lines.append("- The same page-record coverage now includes HT/BS-positioned text: `ESC &k0G HT BS !` routes through `0xedf8`/`0xf1cc`/`0xf2a8` before printable `0xd04a`, proving compact coord `0x0a01` / pixel x `26` before queue/bridge/render.")
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
    lines.append("`tools/render_fixture_harness.py` now has an executable `0x1efc2` bucket-chain fixture that selects render-record bucket word `+0x10`, converts it to a `+0x18` bucket-array slot offset, and pins the compact, segment-list, and encoded-span branch targets plus the compact/encoded subtable entries.")
    lines.append("")

    lines.append("## Segment-List Bucket Renderer `0x1f812`")
    lines.append("")
    lines.append("The `0x40..0x7f` bucket class enters `0x1f812` with `A1` pointing at object byte `+4`. The routine skips to object word `+6` for an entry count, then consumes six bytes per entry: coordinate word, a row-count byte whose low nibble becomes `D2`, one skipped byte, and a width/mask word. Helper `0x1f836` decodes the coordinate through `0x1f3d4`, converts the width/mask word into a full-word count plus a trailing mask from table `0x308f2`, and `0x1f862` writes full `0xffff` words plus that trailing mask for each row.")
    lines.append("`tools/render_fixture_harness.py` now has an executable `0x1f812` fixture that renders one counted segment-list span through this layout and verifies the ROM mask table value.")
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
    lines.append("| `0x13520` / `0x136d2` second-mode rule/text-span objects | page-root `+0x28` -> render-record `+0x20` | `object[4]=0x782a7d`, `object[5]=source[1]`, words `+6/+8`; addressed fixture pins `+0` sorted links from `0x1381c` allocation; bridge copies `+8` to `+0x0a` and sets `+0x0c=1`, `+0x0d=8` | fixed-width/rule writer `0x1f756` / `0x1f7b0` |")
    lines.append("")
    lines.append("`tools/render_fixture_harness.py` now has parser-derived raster state fixtures for `0x10808` (`ESC *t#R`) and `0x1075a` (`ESC *r#A`), proving 300/150/100/75 dpi select encoded modes 0/1/2/3 before queueing a mode-0 transfer object.")
    lines.append("It also has modeled raster command/data stream fixtures for `ESC *t300R` / `ESC *r1A` / delayed `ESC *b4W`, `ESC *t150R` / `ESC *r0A` / delayed `ESC *b2W`, `ESC *t100R` / `ESC *r0A` / delayed `ESC *b2W`, and `ESC *t75R` / `ESC *r0A` / delayed `ESC *b2W` bytes that record handler `0x0105d0`, ensure the modeled page root through `0x10084` before queued transfers, queue mode-0/1/2/3 objects, bridge the `ESC *b4W` page-record object through `0x1edc6`, and render the literal, two-row, three-row, and four-row expansions; the primary 300-dpi stream now has a cross-boundary check tying the ROM parser handlers and `0x12218` restore to the modeled payload offset, page-root allocation, queued object, bridge, rendered row, and row counter, and the same bytes are fetched through the modeled `0xa904` ring source before reaching that parser/object/render boundary; the 150/100/75-dpi streams now have the same ROM parser-handler, restored-record, payload-offset, queued-object, and rendered-row boundary for modes 1/2/3; the `ESC *t300R` / `ESC *r0A` / `ESC *b4W` edge stream ties the parser/restore path to capped queueing and beyond-extent drain/no-row-advance transfer gates; a separate `ESC *t300R` / `ESC *r0A` stream with two consecutive uppercase `ESC *b2W` payloads now has a ROM parser trace for the independent restored records and payload offsets while verifying row_y `0 -> 1 -> 2` and page-record chain objects at coords `0x1000` then `0x0000`.")
    lines.append("Same-group lowercase-final chaining fixtures cover `ESC *t300r150R` and chained `ESC *b2w2W`; the lowercase `w` records the delayed transfer and keeps parser mode in the `*b` family, then the uppercase `W` triggers `0x12218` restore/dispatch and consumes the single raster payload. The chained transfer stream now has a ROM parser trace proving the uppercase `W` does not overwrite the lowercase `80 77 00 02 00 00` delayed record before the payload reaches the modeled queued object and rendered row. A bare `ESC *rB` stream proves handler `0x107fa` clears only raster active state and allows a following `ESC *t150R` mode change.")
    lines.append("Raster row fixtures also queue byte-aligned mode-0 object `00 00 00 00 80 00 00 04 00 01 f0 0f aa 55`, non-byte-aligned mode-0 object `00 00 00 00 80 00 00 02 04 01 c3 3c`, mode-1 object `00 00 00 00 80 01 00 02 00 01 f0 0f`, byte-aligned mode-2 object `00 00 00 00 80 02 00 02 00 01 f0 0f`, non-byte-aligned mode-2 object `00 00 00 00 80 02 00 02 04 01 f0 0f`, band-clipped mode-2 object `00 00 00 00 80 02 00 02 f0 01 f0 0f` with fallback-buffer continuation rows, and mode-3 object `00 00 00 00 80 03 00 02 00 01 f0 0f` through the `0x13070` / `0x13250` / `0x138de` shape, bridge the byte-aligned mode-0 object through `0x1edc6`, and render the rows through `0x1f88e` / `0x1f8da`, `0x1f8e6`, `0x1f920`, and `0x1f9c6`.")
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


def parser_table_handler_entries(
    data: bytes,
    table_base: int,
    label: str,
    handler_target: int,
    max_modes: int = 20,
) -> list[dict[str, int | str]]:
    starts = [u32(data, table_base + i * 4) for i in range(max_modes)]
    matches: list[dict[str, int | str]] = []
    for mode in range(max_modes - 1):
        start = starts[mode]
        end = starts[mode + 1]
        if not (0 <= start <= end <= len(data)) or start == end:
            continue
        pos = start
        while pos + 6 <= end:
            byte = data[pos]
            next_mode = data[pos + 1]
            handler = u32(data, pos + 2)
            if handler == handler_target:
                matches.append({
                    "table": label,
                    "table_base": table_base,
                    "mode": mode,
                    "entry": pos,
                    "byte": byte,
                    "next_mode": next_mode,
                    "handler": handler,
                })
            pos += 6
    return matches


def tokenizer_macro_caller_report(data: bytes) -> str:
    def fmt_refs(refs: list[int]) -> str:
        if not refs:
            return "(none)"
        return ", ".join(f"`0x{ref:06x}`" for ref in refs)

    def byte_label(byte: int) -> str:
        if 0x20 <= byte < 0x7F:
            return f"`0x{byte:02x}` / `{chr(byte)}`"
        return f"`0x{byte:02x}`"

    tokenizer_target = 0x0000DAF0
    macro_dispatch_target = 0x0000DD08
    tokenizer_call_roles = {
        0x011B28: (
            "main parser fallback for active callback handlers `0x11d0c` or "
            "`0x11dd2`; printable `0x60..0x7e` bytes can restart the "
            "six-byte tokenizer after the callback path has kept parser mode "
            "state alive"
        ),
        0x011BDC: (
            "stateful helper `0x11ba6`; punctuation-prefixed commands consume "
            "one extra host byte through `0xda9a`, tokenize the current numeric "
            "record, and arm delayed payload handler `0x1228a` for `W/w`"
        ),
        0x011C88: (
            "stateful helper `0x11c6c`; generic command helper tokenizes the "
            "current record, special-cases mode 4, and treats `W/w` as a "
            "delayed-payload boundary through `0x121cc(0x1228a)`"
        ),
        0x011D64: (
            "callback handler `0x11d0c`; lowercase payload continuations push "
            "the record cursor back by six bytes before re-entering `0xdaf0`, "
            "while uppercase final bytes restore delayed payload state"
        ),
        0x011E2A: (
            "callback handler `0x11dd2`; same pushed-back tokenizer restart as "
            "`0x11d0c`, followed by common font-state refresh helper `0xc580` "
            "before final delayed-payload restore"
        ),
        0x011FDA: (
            "alternate/data parser `ESC )` wrapper `0x11fd2`; calls group "
            "setup `0x11ec8`, then tokenizes the following numeric/final record"
        ),
        0x011FEC: (
            "alternate/data parser `ESC (` wrapper `0x11fe4`; calls group "
            "setup `0x11ec8`, then tokenizes the following numeric/final record"
        ),
        0x012014: (
            "normal parser `ESC )` wrapper `0x12008`; group setup `0x11ec8` "
            "and right-font setup `0x11efe` precede tokenization"
        ),
        0x01202A: (
            "normal parser `ESC (` wrapper `0x1201e`; group setup `0x11ec8` "
            "and left-font setup `0x11f26` precede tokenization"
        ),
        0x01262A: (
            "normal parser `ESC &d` handler `0x12622`; tokenizes underline/text "
            "attribute records and uses the same `W/w` delayed-payload boundary "
            "shape as the other stateful helpers"
        ),
    }
    stateful_helper_variants = [
        {
            "entry": 0x011BA6,
            "name": "punctuation-prefixed helper",
            "tokenizer_call": 0x011BDC,
            "setup": (
                "If the incoming byte is `0x21..0x2f`, fetch one more host "
                "byte through `0xda9a`, echo it through `0x9ec0`, and stop "
                "early only when that fetched byte is space."
            ),
            "payload": (
                "`W/w` arms delayed handler `0x1228a` through `0x121cc`; "
                "lowercase continuation bytes `0x60..0x7e` re-enter "
                "`0xdaf0` after rewinding the parsed-record cursor."
            ),
            "final": (
                "Terminal bytes `0x40..0x5e` restore delayed state through "
                "`0x12218`; other terminal bytes are echoed through `0x9ec0`."
            ),
        },
        {
            "entry": 0x011C6C,
            "name": "generic stateful command helper",
            "tokenizer_call": 0x011C88,
            "setup": (
                "Echoes the incoming command byte through `0x9ec0`, skips "
                "only space, then tokenizes the current record."
            ),
            "payload": (
                "`W/w` arms delayed handler `0x1228a`; if parser mode byte "
                "`0x782999` is mode 4, the helper bypasses that `W/w` special "
                "case and immediately rewinds the parsed-record cursor."
            ),
            "final": (
                "Lowercase continuation bytes loop back through `0xdaf0`; "
                "terminal bytes `0x40..0x5e` restore via `0x12218`, otherwise "
                "the byte is echoed through `0x9ec0`."
            ),
        },
        {
            "entry": 0x011D0C,
            "name": "callback continuation helper",
            "tokenizer_call": 0x011D64,
            "setup": (
                "Lowercase bytes `0x60..0x7e` are continuation candidates; "
                "only lowercase `w` arms delayed handler `0x1228a` before "
                "the tokenizer restart."
            ),
            "payload": (
                "Uppercase `W` sets an internal `D4` flag and arms the same "
                "delayed handler before terminal processing."
            ),
            "final": (
                "In alternate/data mode with byte `0x782a56` set, terminal "
                "bytes can append either the terminal byte alone or a leading "
                "`0x30` plus the terminal byte through `0xe002` before "
                "`0x12218` restores delayed state."
            ),
        },
        {
            "entry": 0x011DD2,
            "name": "font-refreshing callback continuation helper",
            "tokenizer_call": 0x011E2A,
            "setup": (
                "Uses the same lowercase `w` continuation and uppercase `W` "
                "terminal delayed-payload tests as helper `0x11d0c`."
            ),
            "payload": (
                "Uppercase `W` rewinds `0x78299e` and calls common font-state "
                "refresh helper `0xc580` before terminal processing."
            ),
            "final": (
                "Alternate/data terminal append behavior matches `0x11d0c`, "
                "including the optional leading `0x30` byte before `0x12218`."
            ),
        },
    ]
    macro_table_entries = (
        parser_table_handler_entries(
            data,
            0x112A4,
            "normal",
            macro_dispatch_target,
        )
        + parser_table_handler_entries(
            data,
            0x116F6,
            "alternate/data",
            macro_dispatch_target,
        )
    )

    lines = ["# IC30/IC13 Tokenizer and Macro Dispatch Callers", ""]
    lines.append(
        "This report closes the static caller lead from "
        "`notes/pcl-parser-firmware.md`: direct callers of tokenizer "
        "`0xdaf0` are listed by role, while macro dispatcher `0xdd08` is "
        "shown as parser-table-reached rather than direct-call-reached."
    )
    lines.append("")
    lines.append("## `0xdaf0` Six-Byte Tokenizer Callers")
    lines.append("")
    lines.append(
        f"Direct absolute `JSR 0xdaf0` callers: "
        f"{fmt_refs(jsr_abs_refs(data, tokenizer_target))}."
    )
    lines.append("")
    lines.append("| Caller | Current classification |")
    lines.append("| ---: | --- |")
    for caller in jsr_abs_refs(data, tokenizer_target):
        role = tokenizer_call_roles.get(caller, "unclassified tokenizer caller")
        lines.append(f"| `0x{caller:06x}` | {role} |")
    lines.append("")
    lines.append("Tokenizer contract confirmed by these callers:")
    lines.append("")
    lines.append(
        "- `0xdaf0` is not a standalone PCL command handler; it fills the "
        "six-byte parsed-record stream under `0x78299e` and leaves the "
        "final byte in record byte `+1`."
    )
    lines.append(
        "- Stateful parser helpers deliberately subtract six from `0x78299e` "
        "before re-entering `0xdaf0`; reproduction must preserve that "
        "record-cursor rewind because it changes which command record later "
        "payload handlers restore."
    )
    lines.append(
        "- `W/w` finals are the repeated delayed-payload boundary: callers "
        "arm `0x121cc(0x1228a)` before the payload reader later restores "
        "state through `0x12218`."
    )
    lines.append("")
    lines.append("## Stateful Tokenizer Helper Variants")
    lines.append("")
    lines.append(
        "The focused disassembly window "
        "`generated/disasm/ic30_ic13_tokenizer_stateful_helpers_011ba6.lst` "
        "covers the helper bodies that the caller list previously left only "
        "partly classified."
    )
    lines.append("")
    for helper in stateful_helper_variants:
        lines.append(
            f"- `0x{int(helper['entry']):06x}` "
            f"({helper['name']}, tokenizer call "
            f"`0x{int(helper['tokenizer_call']):06x}`):"
        )
        lines.append(f"  Setup: {helper['setup']}")
        lines.append(f"  Payload boundary: {helper['payload']}")
        lines.append(f"  Finalization: {helper['final']}")
    lines.append("")
    lines.append("Reproduction contract added by these variants:")
    lines.append("")
    lines.append(
        "- A byte-stream parser must model `0x78299e` rewind before repeated "
        "tokenization, because the next delayed payload or terminal handler "
        "restores the six-byte record that the rewind selects."
    )
    lines.append(
        "- The `0x1228a` delayed handler is not limited to raster/font `W` "
        "payloads; these generic helpers also arm it for `W/w` boundaries, "
        "with helper-specific exceptions for mode 4 and font-state refresh."
    )
    lines.append("")
    lines.append("## `0xdd08` Macro Dispatcher Reachability")
    lines.append("")
    lines.append(
        f"Direct absolute `JSR 0xdd08` callers: "
        f"{fmt_refs(jsr_abs_refs(data, macro_dispatch_target))}."
    )
    lines.append(
        "`0xdd08` is reached through parser dispatch table entries, not "
        "through direct `JSR` instructions."
    )
    lines.append("")
    lines.append("| Table | Mode | Entry | Byte | Next mode | Meaning |")
    lines.append("| --- | ---: | ---: | --- | ---: | --- |")
    for entry in macro_table_entries:
        byte = int(entry["byte"])
        next_mode = int(entry["next_mode"])
        meaning = (
            "chained macro-control record"
            if next_mode == int(entry["mode"])
            else "terminal macro-control record"
        )
        lines.append(
            f"| {entry['table']} | {entry['mode']} | "
            f"`0x{int(entry['entry']):06x}` | {byte_label(byte)} | "
            f"{next_mode} | {meaning} |"
        )
    lines.append("")
    lines.append("Current reproduction consequence:")
    lines.append("")
    lines.append(
        "- `ESC &f#x` remains in mode 17 and calls `0xdd08`; `ESC &f#X` "
        "returns to mode 0 and calls the same handler. The alternate/data "
        "table keeps the same `x/X -> 0xdd08` reachability while disabling "
        "the normal `y/Y` macro-id handler, which matches the macro-definition "
        "payload behavior already exercised in the renderer harness."
    )
    lines.append("")
    return "\n".join(lines)


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
    (0x08,): "Backspace",
    (0x09,): "Horizontal tab",
    (0x0A,): "Line feed",
    (0x0C,): "Form feed",
    (0x0D,): "Carriage return",
    (0x1b, 0x45): "Printer reset",
    (0x1b, 0x39): "Clear horizontal margins",
    (0x1b, 0x59): "Display functions on",
    (0x1b, 0x5a): "Display functions off",
    (0x1b, 0x3d): "Half-line feed",
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
    (0x1b, 0x26, 0x70, 0x58): "Transparent print data",
    (0x1b, 0x26, 0x73, 0x43): "End-of-line wrap",
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
    (0x1b, 0x2a, 0x63, 0x45): "Character code",
    (0x1b, 0x2a, 0x63, 0x46): "Font control",
    (0x1b, 0x2a, 0x70, 0x58): "Horizontal dot position",
    (0x1b, 0x2a, 0x70, 0x59): "Vertical dot position",
    (0x1b, 0x28, 0x73, 0x50): "Primary spacing",
    (0x1b, 0x28, 0x73, 0x48): "Primary pitch",
    (0x1b, 0x28, 0x73, 0x56): "Primary point size",
    (0x1b, 0x28, 0x73, 0x57): "Download font/character data",
    (0x1b, 0x28, 0x73, 0x53): "Primary style",
    (0x1b, 0x28, 0x73, 0x42): "Primary stroke weight",
    (0x1b, 0x28, 0x73, 0x54): "Primary typeface",
    (0x1b, 0x29, 0x73, 0x50): "Secondary spacing",
    (0x1b, 0x29, 0x73, 0x48): "Secondary pitch",
    (0x1b, 0x29, 0x73, 0x56): "Secondary point size",
    (0x1b, 0x29, 0x73, 0x57): "Download font/character data",
    (0x1b, 0x29, 0x73, 0x53): "Secondary style",
    (0x1b, 0x29, 0x73, 0x42): "Secondary stroke weight",
    (0x1b, 0x29, 0x73, 0x54): "Secondary typeface",
}


def known_pcl_meaning(seq: tuple[int, ...], next_mode: int) -> str:
    meaning = KNOWN_PCL_COMMANDS.get(seq)
    if meaning is not None:
        return meaning
    if seq and 0x61 <= seq[-1] <= 0x7A:
        uppercase_seq = seq[:-1] + (seq[-1] - 0x20,)
        meaning = KNOWN_PCL_COMMANDS.get(uppercase_seq)
        if meaning is not None:
            if next_mode == 0:
                return meaning
            return f"{meaning} (lowercase chaining final)"
    return ""


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
        meaning = known_pcl_meaning(seq, next_mode)
        lines.append(f"| `{seq_text(seq)}` | {mode} | {next_mode} | {handler_text} | {meaning} |")
    lines.append("")
    return lines


def parser_command_map_report(data: bytes) -> str:
    lines = ["# IC30/IC13 Flattened PCL Command Map", ""]
    lines.append("Generated from parser dispatch pointer tables, using the shortest known prefix for each parser mode.")
    lines.append(
        "Known meanings are assigned when they match commands already listed "
        "in `notes/pcl4-language.md` or a lowercase final chains to the same "
        "parser family as its uppercase command."
    )
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
        (0x0078299E, "parser record cursor rewound by font/download handlers before reading the parsed parameter"),
        (0x00782F2E, "current font id written by `ESC *c#D` and consumed by font-control helpers"),
        (0x00782F30, "current character/code word written by `ESC *c#E` and consumed by character payload/control helpers"),
        (0x00782A92, "mode/status byte that suppresses font-control values 0, 1, 2, 3, and 6 when it equals `2`"),
        (0x00782640, "start of 32 current downloaded-font records, 10 bytes each"),
        (0x00782782, "unmarked/current downloaded-font count adjusted by `0x17108` and `0x17150`"),
        (0x00782786, "marked/current downloaded-font count adjusted opposite `0x782782`"),
        (0x00783140, "download payload byte budget used by `0x16c14` and lower payload readers"),
    ]

    routines = [
        (0x015A56, "`ESC *c#D` assign-font-id handler"),
        (0x015A18, "`ESC *c#E` character-code handler"),
        (0x011F96, "`ESC )s#W` / `ESC (s#W` delayed font payload selector"),
        (0x015D0A, "zero-count font/download descriptor delayed-payload handler"),
        (0x0169F6, "descriptor kind validator for byte `4`"),
        (0x016A10, "descriptor selector mapper: zero -> status 1, nonzero -> status 2"),
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
    lines.append("Generated from the verified firmware image and focused disassembly around `0x15a18`, `0x15a56`, `0x11f96`, `0x16df6`, and the immediate font-control targets.")
    lines.append("This is the host-command edge for downloaded-font bookkeeping: `ESC *c#D` selects the current font id, `ESC *c#E` selects the current character/code word, `ESC )s#W` / `ESC (s#W` schedules the binary payload consumer, and `ESC *c#F` dispatches control values that delete, mark, unmark, or refresh current downloaded-font records.")
    lines.append("")

    lines.append("## Font and Character Selection")
    lines.append("")
    lines.append("| Handler | Firmware behavior | Reproduction meaning |")
    lines.append("| --- | --- | --- |")
    lines.append("| `0x15a56` (`ESC *c#D`) | rewinds parser record cursor `0x78299e` by six bytes, reads the parsed signed word at `+2`, stores its absolute value in `0x782f2e`, and maps `-32768` to `0x7fff` | subsequent downloaded-font control and payload commands operate on this normalized current font id |")
    lines.append("| `0x15a18` (`ESC *c#E`) | rewinds parser record cursor `0x78299e` by six bytes, reads the parsed signed word at `+2`, stores its absolute value in `0x782f30`, and maps `-32768` to `0x7fff` | later `ESC )s#W` character payloads and `ESC *c3F` cleanup select the same character/code word |")
    lines.append("")

    lines.append("## Font Payload Selector")
    lines.append("")
    lines.append("| Handler | Firmware behavior | Reproduction meaning |")
    lines.append("| --- | --- | --- |")
    lines.append("| `0x11f96` (`ESC )s#W` / `ESC (s#W`) | inspects the parsed byte-count parameter from the six-byte record: count `0` schedules delayed handler `0x15d0a`, and any nonzero count schedules delayed handler `0x16c14` through `0x121cc` | zero-length `W` enters the descriptor/setup path; nonzero `W` enters downloaded font/character payload installation |")
    lines.append("| `0x15d0a` | stores the absolute parsed count in `0x783140`, rejects counts below `3` or parser mode `2`, reads descriptor byte `0` through `0x169f6` which accepts only value `4`, then reads selector byte `1` through `0x16a10` where zero returns status `1` and nonzero returns status `2` | zero-length `W` is a descriptor packet, not a no-op; byte `4` is the accepted descriptor kind and byte `1` chooses current-record versus continuation handling |")
    lines.append("| `0x15d0a` status `1` branch | scans current downloaded-font records through `0x172c0`; an existing current record is looked up through `0x1b4c0`, and object flag bit 30 selects `0x16498` when set or `0x16606` when clear | descriptor bytes following `ESC )s0W` can install a downloaded-character object or a downloaded-font-resource object for the current font id |")
    lines.append("| `0x15d0a` status `2` branch | requires continuation flag `0x7827c6 == 1`, looks up saved payload `0x7827da` through `0x1b4c0`, and object flag bit 30 selects resume helper `0x15b9a` when set or `0x15c4c` when clear | nonzero selector bytes resume an interrupted descriptor/payload copy instead of allocating from the current record table |")
    lines.append("| `0x16c14` | stores the absolute parsed count in `0x783140`, scans or allocates the current downloaded-font record slot, and either skips that many payload bytes or installs the allocated payload pointer | nonzero `ESC )s#W` payload bytes become the current font resource or character object used by later text rendering |")
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
    lines.append("- A byte-stream reproduction must preserve the global current font id at `0x782f2e` and current character/code word at `0x782f30`; `ESC *c#D` and `ESC *c#E` normalization happen before `ESC *c#F`, `ESC (#X` / `ESC )#X`, and downloaded payload installation consult current records. The harness now ties parser-derived current id `0x1234` and current character `0x25` from `ESC *c4660d37e5F` into the following descriptor route and character payload fixtures.")
    lines.append("- `ESC )s0W` / `ESC (s0W` are not ordinary zero-byte skips: `0x11f96` schedules descriptor handler `0x15d0a`; the harness now ties the `ESC )s0W` parser trace to restored handler `0x15d0a`, descriptor offset/budget, selector-zero routing through the current downloaded-font record, and selector-nonzero continuation routing through saved payload `0x7827da`.")
    lines.append("- Nonzero `W` counts schedule `0x16c14`; the harness now traces `ESC )s80W` through ROM parser table `0x11774` to restored handler `0x16c14`, payload offset/length, `0x16fae` validation, `0x17026`/`0x1719c` allocation, and `0x1bc38` candidate insertion for a font-resource payload. It also ties the full `ESC )s2193W` parser trace to restored handler `0x16c14`, payload offset/length, the `0x16498` downloaded character-object allocation, `0x16874`/`0x16942` payload copy, and the rendered `0x1f264` segmented-wide row. `0x15d0a` reaches the same character-object path only after the descriptor branch resolves an existing object whose flag bit 30 is set.")
    lines.append("- Font-control values `0`, `1`, `2`, `3`, and `6` are suppressed when `0x782a92 == 2`; values `4` and `5` still run the downloaded-record mark/unmark helpers.")
    lines.append("- The concrete font-resource payload-install path is now pinned from `ESC )s80W` through `0x16c14` -> `0x16fae` -> `0x17026` -> `0x1719c` -> `0x1bc38`, while character payload installation reaches the `0x16498` object path; this report now names the PCL command edge that selects which current downloaded-font records and character objects those lower helpers mutate.")
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

    def fmt_all_refs(refs: list[int]) -> str:
        if not refs:
            return "(none)"
        return ", ".join(f"`0x{ref:06x}`" for ref in refs)

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
    caller_roles = {
        0x00DA9A: (
            "ESC-aware parser byte wrapper",
            "First fetch for normal parser input; returns non-ESC bytes directly.",
            "No explicit `D7=-1` test here; caller loop decides parser end/state.",
        ),
        0x00DAA6: (
            "ESC wrapper display-functions probe",
            "Second fetch after ESC; checks for `?` display-function prefix.",
            "No explicit `D7=-1` test.",
        ),
        0x00DAB2: (
            "ESC wrapper display-functions probe",
            "Third fetch after `ESC ?`; loops on `0x11`, otherwise reports the byte through `0x9ec0` and returns ESC.",
            "No explicit `D7=-1` test.",
        ),
        0x00DACE: (
            "`0x1a 0x58` control probe",
            "Fetches a byte and, if it is `0x1a`, fetches a second byte looking for `0x58`.",
            "On `0x1a 0x58`, calls `0xd99a` and returns `D7=0`; otherwise leaves the fetched byte path unchanged.",
        ),
        0x00DADA: (
            "`0x1a 0x58` control probe",
            "Second byte of the `0xdace` probe.",
            "Only the exact `0x58` second byte triggers `0xd99a` and normalized zero.",
        ),
        0x012142: (
            "alternate/data text append reader",
            "After seeding `ESC Y`, fetches bytes, appends through `0xe002`, and treats `ESC ... Z` as an end marker.",
            "Stops on `D7=-1`; `0x1a 0x58` calls `0xd99a` and appends `0x7f`.",
        ),
        0x012152: (
            "alternate/data text append reader",
            "Second byte of the local `0x1a 0x58` probe in the `ESC Y` append reader.",
            "Only exact `0x58` normalizes the pair to appended `0x7f`.",
        ),
        0x0124BC: (
            "bounded text repeat reader",
            "Reads up to counter `D4`, routes printable bytes through `0xd04a`, and filters control ranges through `0xd0f0` depending on active symbol state.",
            "Stops on `D7=-1`; `0x1a 0x58` calls `0xd99a` and substitutes `0x7f` before text handling.",
        ),
        0x0124CC: (
            "bounded text repeat reader",
            "Second byte of the bounded reader's `0x1a 0x58` probe.",
            "Only exact `0x58` normalizes to `0x7f`.",
        ),
        0x012582: (
            "ESC-terminated text repeat reader",
            "Reads text until `D7=-1` or an `ESC ... Z` terminator, routes printable bytes through `0xd04a`, and calls `0xf054` after CR.",
            "Stops on `D7=-1`; `0x1a 0x58` calls `0xd99a` and substitutes `0x7f`.",
        ),
        0x012592: (
            "ESC-terminated text repeat reader",
            "Second byte of the ESC-terminated reader's `0x1a 0x58` probe.",
            "Only exact `0x58` normalizes to `0x7f`.",
        ),
        0x0138FA: (
            "raster payload copy reader",
            "Copies normalized host bytes into raster object storage for delayed transfer handler `0x105d0`.",
            "Uses the same local `0x1a 0x58` probe shape; negative `D7` ends/drains through the raster reader status path.",
        ),
        0x013904: (
            "raster payload copy reader",
            "Second byte of the raster copy `0x1a 0x58` probe.",
            "Exact `0x58` calls `0xd99a` and stores normalized zero.",
        ),
        0x0168DC: (
            "linear downloaded-font payload reader",
            "Copies host bytes to `A4`, decrements payload budget `0x783140`, and saves continuation state when the current copy window expires.",
            "`0x1a 0x58` calls `0xd99a` and stores zero; negative `D7` returns failure status.",
        ),
        0x0168FE: (
            "linear downloaded-font payload reader",
            "Second byte of the linear reader's `0x1a 0x58` probe.",
            "Only exact `0x58` normalizes to stored zero.",
        ),
        0x016960: (
            "split-plane downloaded-font prefix reader",
            "Copies prefix-span bytes to `A4` for odd-width split-plane glyph rows.",
            "`0x1a 0x58` calls `0xd99a` and stores zero; negative `D7` returns failure status.",
        ),
        0x01697A: (
            "split-plane downloaded-font tail reader",
            "Copies one trailing byte per row to `A3` after the prefix plane.",
            "`0x1a 0x58` calls `0xd99a` and stores zero; negative `D7` returns failure status.",
        ),
        0x0169CA: (
            "split-plane downloaded-font prefix reader",
            "Second byte of the prefix-plane `0x1a 0x58` probe.",
            "Only exact `0x58` normalizes to stored zero.",
        ),
        0x0169E0: (
            "split-plane downloaded-font tail reader",
            "Second byte of the tail-plane `0x1a 0x58` probe.",
            "Only exact `0x58` normalizes to stored zero.",
        ),
    }

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
    fetch_callers = jsr_abs_refs(data, 0x0000A904)
    lines.append(f"Direct absolute `JSR 0xa904` callers: {fmt_all_refs(fetch_callers)}.")
    lines.append("")
    lines.append("The table below classifies every direct caller found in the verified firmware image.")
    lines.append("")
    lines.append("| Caller | Role | Byte handling | End/control handling |")
    lines.append("| ---: | --- | --- | --- |")
    for caller in fetch_callers:
        role = caller_roles.get(caller)
        if role is None:
            lines.append(f"| `0x{caller:06x}` | unclassified | | |")
            continue
        name, byte_handling, end_handling = role
        lines.append(f"| `0x{caller:06x}` | {name} | {byte_handling} | {end_handling} |")
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
    lines.append("- A byte-stream emulator can feed parser/imaging work above `0xa904` by returning normalized `D7` bytes in the same order as the priority table, while preserving `D7=-1` as a no-byte/end/error return for callers that test it. `tools/render_fixture_harness.py` now has executable `0xa904` source-priority fixtures covering the no-byte return, service retry, first LIFO, data-chain end retry, second LIFO, ring-buffer mode, and both direct hardware modes including direct-mode `0x1a` reporting and mode-2 control-shadow bit 6; it also feeds ring-buffer bytes for `ESC &k1G!\\r!` through the ROM parser trace, page-record queue, `0x1edc6` bridge, and final rendered rows, and feeds the primary `ESC *t300R` / `ESC *r1A` / `ESC *b4W` raster stream through the same `0xa904` ring source before the parser/delayed-transfer/page-record/bridge/render boundary.")
    lines.append("- Exact host-interface emulation still needs board/manual correlation for `0x8e01/0x8801/0x8c01`, `0xa601/0xaa01`, and `0xfffee005/0xfffee001/0xfffee009`; current ROM evidence only proves the polling, data, handshake, and status-bit behavior.")
    lines.append("- Both direct modes special-case input byte `0x1a` through `0x9ec0`, and higher-level payload readers also interpret `0x1a 0x58` by calling `0xd99a`; byte-stream reproduction must preserve that control path rather than treating all payload bytes as opaque.")
    lines.append("- All 19 direct `0xa904` call sites are now classified. Parser wrapper callers can pass `D7=-1` upward without a local stop test, text repeat readers stop on it, raster and font payload readers treat it as an end/error status, and `0x1a 0x58` is normalized differently by consumer family: `0xdace` returns zero, text repeat readers substitute `0x7f`, and raster/font payload readers store zero.")
    lines.append("- Font payload reader `0x168dc` copies linear downloaded-font bytes to `A4`, decrements byte budget `0x783140` only for stored payload bytes, and saves continuation state in `0x7827c6/0x7827ca/0x7827d2` when the budget expires. Reader `0x16942` handles split odd-width glyph planes: `A4` receives `rows * prefix_span` bytes, `A3 = A4 + rows * prefix_span` receives one trailing byte per row, and continuation state also records `0x7827ce`, `0x7827d6`, and `0x7827d8`. `0x172c0` scans 10-byte current downloaded-font records under `0x782640..0x782776`, returning existing/free/full statuses; `0x16c14` uses that result to replace an existing payload through `0x1887a`, clear matching continuation state, or install a new payload and update candidate counters/cursors. `0x170be` maps a low-24-bit payload pointer back to a current-record slot and id; `0x17108` sets record flag bit 6 and transfers a count from `0x782782` to `0x782786` for an unmarked current payload record; `0x17150` clears that bit and transfers the count back. `0x15a56` normalizes the current font id from `ESC *c#D`, and `0x16df6` dispatches `ESC *c#F` values while suppressing values `0`, `1`, `2`, `3`, and `6` when `0x782a92 == 2`. `0x16fae` walks the validation table at `0x16eae`, then copies up to 16 optional symbol bytes through `0x1599c` into `0x782842` and stores the count at `0x782856`; `0x17362` sets staged type byte `+0x0c` and `0x7827ba`, `0x17026` stages record type `0x15` and allocation size `((0x7827ba << 2) + 0x9b) >> 6`, and `0x1719c` copies the sparse staged header plus optional symbol bytes into the allocated record. `tools/render_fixture_harness.py` now has executable fixtures for both readers, record bookkeeping/lookup/marking/unmarking, font-id/control dispatch, `ESC )s80W` resource-payload command restoration, validation/symbol-byte staging, table-driven staged-header predicate side effects, payload-backed inline map/render, type-2 payload-backed wide/segmented fixed-record rendering, and allocation/header initialization, including `0x1a 0x58` handling, continuation checkpoints, replacement/free-slot updates, no-slot budget skip, count transfer, validation failure, zero-budget validation, table-driven predicate clamps, payload-backed inline map/render, and optional symbol-byte append offsets.")
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
        (0x00782DD6, "left-margin/default horizontal cursor copied into `0x782c8a` by CR helper `0xf06e` and written by `ESC &a#L`"),
        (0x00782DDA, "right-margin/current horizontal limit used by HT/helper `0xf4ca` and written by `ESC &a#M`"),
        (0x0078315C, "default horizontal motion / HMI value used by HT and BS"),
        (0x00783160, "line advance / VMI value added by LF and FF helpers"),
        (0x00783184, "pending text span flush enable tested by `0xf34a`"),
        (0x0078318E, "alternate previous-width mode tested by BS"),
        (0x0078318F, "line-termination mode byte written by `ESC &k#G` and tested by CR/LF/FF"),
        (0x00783190, "end-of-line wrap flag written by `ESC &s#C` and tested by printable text overflow paths"),
        (0x00783191, "vertical overflow recovery enable tested by `0xf36c`"),
    ]

    lines = ["# IC30/IC13 Direct Control-Code Flow", ""]
    lines.append("Generated from handlers `0xf02c..0xf55e`, line-termination handler `0xedf8`, wrap handler `0xedb0`, dot-position handlers `0xf48c`/`0xf692`, transparent-data handler `0x11f5a`, and state-reference scans of the verified firmware image.")
    lines.append("This report tracks parser commands that change cursor/page/text state before text or raster objects are queued.")
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

    lines.append("## Wrap and Transparent Data")
    lines.append("")
    lines.append("PCL `ESC &s#C` reaches handler `0xedb0`, which rewinds the parsed six-byte record and uses the absolute parsed value:")
    lines.append("")
    lines.append("| `#` | Firmware state | Reproduction meaning |")
    lines.append("| ---: | --- | --- |")
    lines.append("| 0 | writes `0x783190 = 1` | end-of-line wrap is enabled for printable text overflow paths |")
    lines.append("| 1 | clears `0x783190` | end-of-line wrap is disabled |")
    lines.append("| other | leaves `0x783190` unchanged | unsupported selector is ignored after record rewind |")
    lines.append("")
    lines.append("PCL `ESC &p#X` reaches handler `0x11f5a`, which only arms delayed payload handler `0x12452` through `0x121cc`; the payload bytes are consumed later after `0x12218` restores the saved command record. Consumer `0x12452` uses the absolute byte count, stops on `D7=-1`, applies the same `0x1a 0x58 -> 0x7f` normalization as other text repeat readers, routes printable bytes through `0xd04a`, and filters control bytes through `0xd0f0` depending on the active symbol/high-byte state.")
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
    lines.append("| `ESC &a#L` | `0xeb58` | takes absolute parsed columns, scales through current HMI `0x78315c`, rejects values beyond `0x782dda - HMI`, writes `0x782dd6`, and moves `0x782c8a` with pending-span flush when the new margin is right of the cursor or pending text is marked | left margin directly changes CR reset position, HT/BS clamps, and the next printable text origin |")
    lines.append("| `ESC &a#M` | `0xec0c` | takes `abs(parameter) + 1` columns, scales through HMI, rejects values before `0x782dd6 + HMI`, clamps beyond `0x782db8`, writes `0x782dda`, and when the new margin is left of the cursor moves `0x782c8a`, updates the active span, and sets `0x782a57` | right margin limits horizontal positioning and can force the current cursor to the new line limit |")
    lines.append("| `ESC &a#C` | `0xf39e` | converts parsed decimal columns through current HMI `0x78315c`, scales through helpers `0x332ee`/`0x3324a`/`0x104d8`, and commits through `0xf4ca` using parsed-record bit 0 as the relative flag | column positioning changes horizontal text/raster placement in HMI units with the same horizontal clamps/span updates as HT/BS |")
    lines.append("| `ESC &a#H` | `0xf416` | converts parsed decipoints as five packed subunits per decipoint, then commits through `0xf4ca` using parsed-record bit 0 as the relative flag | horizontal decipoint positioning maps host coordinates into 300 dpi twelfths before object placement |")
    lines.append("| `ESC &a#R` | `0xf560` | ensures a page root, masks the parsed flag to bit 0, adds fractional `0.7200` before VMI scaling for absolute rows, converts through current VMI `0x783160`, commits through `0xf6e2`, calls overflow recovery helper `0x1048c` for relative moves, and clamps absolute rows to `0x782dc6` | row positioning uses VMI units and has a firmware absolute-row bias that must be reproduced before text/raster queuing |")
    lines.append("| `ESC &a#V` | `0xf60a` | converts parsed decipoints as five packed subunits per decipoint, commits through `0xf6e2` using parsed-record bit 0 as the relative flag, and clamps to `0x782dc6` | vertical decipoint positioning maps host coordinates into the same vertical cursor used by text and raster start state |")
    lines.append("| `ESC *p#X` | `0xf48c` | sign-extends the parsed word, shifts it left 16 bits to a whole-dot packed coordinate, then commits through `0xf4ca` using parsed-record bit 0 as the relative flag | horizontal dot positioning shares the same clamp, right-limit latch, pending-text clear, and active-span update path as `ESC &a#C/#H` |")
    lines.append("| `ESC *p#Y` | `0xf692` | sign-extends the parsed word, shifts it left 16 bits, commits through `0xf6e2` using parsed-record bit 0 as the relative flag, then clamps to `0x782dc6` | vertical dot positioning shares the same page-root, pending-span flush, top/relative base, and vertical-bound behavior as `ESC &a#R/#V` |")
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
    lines.append("- `ESC &s#C` is not only parser metadata: selector `0` writes wrap flag `0x783190=1` and selector `1` clears it. Printable text overflow paths test this flag, so wrap mode has to be part of the text layout state.")
    lines.append("- `ESC &p#X` transparent data is not opaque to rendering. It uses delayed-payload restore through `0x121cc`/`0x12218`, then handler `0x12452` feeds each consumed byte through the same printable/control text pipeline as repeat text, including `0x1a 0x58` normalization to `0x7f`.")
    lines.append("- `ESC *p#X/#Y` dot positioning converts host dots to whole-dot packed cursor coordinates with `parameter << 16`, then uses the same horizontal and vertical commit helpers as the `ESC &a` cursor-position commands.")
    lines.append("- CR/LF/FF/HT/BS do not only change cursor coordinates; they can flush pending text spans, ensure/finalize page roots, and invoke the same context span update routines `0xd4ac` / `0xd8fc` used after printable text.")
    lines.append("- Axis names remain provisional, but `tools/render_fixture_harness.py` now has synthetic state fixtures for the line-termination map plus CR/LF/FF/HT/BS cursor/page effects, `ESC &f#S` cursor stack push/pop and clamp behavior, `ESC &a#C/#H/#R/#V` cursor-position conversion/relative/clamp behavior, `ESC &a#L/#M` margin conversion/reject/cursor-move behavior, narrow byte-stream fixtures for `ESC &k1G`+CR, `ESC &k2G`+LF, `ESC &k2G`+FF, `ESC &k3G`+CR/LF/FF, `ESC &k0G`+HT/BS, `ESC &f0S`/`ESC &f1S` through selector handler `0xf75e`, chained `ESC &l8c6d3e2F` through vertical-layout handlers `0xcb00`/`0xc992`/`0xece2`/`0xea9e`, chained `ESC &a3.5c+1R` through cursor-position handlers `0xf39e` and `0xf560`, and chained `ESC &a6l9M` through margin handlers `0xeb58` and `0xec0c`, a mixed `ESC &k1G!\\r!` fixture that applies CR+LF before queueing the second printable glyph and ties the ROM parser handlers to the page-record allocator/bridge result, an `ESC &a1L!` fixture that ties left-margin handler `0xeb58` to shifted page-record text output, `ESC &a2C!` and `ESC &a1R!` fixtures that tie cursor-position handlers `0xf39e` and `0xf560` to shifted page-record text output, an `ESC &l3E!` fixture that ties top-margin handler `0xece2` to vertically shifted page-record text output, a mixed `!\\x1bE` fixture that applies reset publication/clear state after queued text and has a page-record allocator/bridge/publication variant for the pre-reset glyph, and a publication-boundary fixture tying reset, FF, page-size, and orientation parser-handler sequences to one-root allocation, one `0xff1e` publication, current-root clearing, and rendered rows after `0x1edc6`. The remaining step is expanding this into the full firmware parser path with real page-object allocation.")
    lines.append("- The direct-control/page-record boundary fixtures now also drive `ESC &a1M!`, tying right-margin handler `0xec0c` to cursor movement and restored page-record text output through printable handler `0xd04a` at compact coord `0x0a02`.")
    lines.append("- The direct-control/page-record boundary fixtures now also drive `ESC &a6l9M!`, tying lowercase-final left-margin handler `0xeb58` and right-margin handler `0xec0c` to text output through printable handler `0xd04a` at compact coord `0x0207` / pixel x `114`.")
    lines.append("- The direct-control/page-record boundary fixtures now also drive `ESC &k2G!\\n!`, tying LF handler `0xf08c` to line-termination mode `0x60`, CR+LF cursor movement, and text output through printable handler `0xd04a` at compact coord `0x3b00`.")
    lines.append("- The direct-control/page-record boundary fixtures now also drive `ESC &k0G HT BS !`, tying line-termination handler `0xedf8`, HT handler `0xf1cc`, and BS handler `0xf2a8` to text output through printable handler `0xd04a` at compact coord `0x0a01` / pixel x `26`.")
    lines.append("- The direct-control/page-record boundary fixtures now also drive `ESC &a72H!`, tying horizontal-decipoint handler `0xf416` to cursor conversion and restored page-record text output through printable handler `0xd04a` at compact coord `0x0402`.")
    lines.append("- The direct-control/page-record boundary fixtures now also drive `ESC &a72V!`, tying vertical-decipoint handler `0xf60a` to cursor conversion and restored page-record text output through printable handler `0xd04a` at compact coord `0x9001` / bucket `0`.")
    lines.append("- The direct-control/page-record boundary fixtures now also drive `ESC &a2c+1R!`, tying lowercase-final horizontal cursor-position handler `0xf39e` and relative vertical handler `0xf560` to text output through printable handler `0xd04a` at compact coord `0x1a02` / bucket `3`.")
    lines.append("- A new direct-control/page-record boundary fixture drives `ESC &f0S ESC &a2C ESC &f1S!`, tying cursor-stack handlers `0xf75e` and cursor-position handler `0xf39e` to restored text output through printable handler `0xd04a` at compact coord `0x0001`.")
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
        (0x00782A26, "parameter/text scratch pointer reset to `0x782a2a` by `0xcda2`"),
        (0x00782D36, "cursor-stack top pointer reset to `0x782c96` by `0xcda2`"),
        (0x00783160, "VMI/line advance recomputed by `0xcda2` from default line spacing word `0x78219e`"),
        (0x00783166, "environment motion accumulator longword cleared by `0xcda2`"),
        (0x0078316A, "environment motion accumulator longword cleared by `0xcda2`"),
        (0x0078316E, "environment motion/status word cleared by `0xcda2`"),
        (0x00782DA4, "display/page mode word loaded from default byte `0x78219d` by `0xcda2`"),
        (0x00782DA6, "environment byte copied from default byte `0x7821a2` by `0xcda2` when reset gate permits"),
        (0x00782990, "page/status byte cleared by `0xcda2`"),
        (0x00782A6D, "parser/page flag set to `1` by `0xcda2`"),
        (0x0078297E, "page-root transient byte cleared by `0xcda2` and `0xff1e`"),
        (0x00782C72, "pending page/allocation latch cleared by `0xcda2` and `0xff1e`"),
        (0x00782C73, "pending page/allocation latch cleared by `0xcda2` and `0xff1e`"),
        (0x00783184, "pending text/span flag cleared by `0xcda2`"),
        (0x00783185, "pending text/span flag cleared by `0xcda2`"),
        (0x00782F2C, "font/symbol dirty flag cleared by `0xcda2`"),
        (0x0078318F, "line-termination mode byte cleared by `0xcda2`"),
        (0x00783190, "display-function byte cleared by `0xcda2`"),
        (0x00783191, "display-function byte set to `1` by `0xcda2`"),
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

    lines.append("## Environment Defaults `0xcda2`")
    lines.append("")
    lines.append("| Address range | Firmware operation | Reproduction meaning |")
    lines.append("| ---: | --- | --- |")
    lines.append("| `0xcdaa..0xcddc` | Initializes four 0x6c-byte page/control records rooted at `0x780f02`; each record's `+0x1c` points to a 0x400-byte bucket region at `0x7810bc + 0x400*n`. | Reset rebuilds the page/control pool's bucket-array backing pointers before page objects are queued. |")
    lines.append("| `0xcddc..0xcdf0` | Stores `0x782a26 = 0x782a2a` and cursor-stack top `0x782d36 = 0x782c96`. | Parser scratch and the cursor stack return to their base positions. |")
    lines.append("| `0xcdf0..0xce10` | Clears `0x78316a`, `0x783166`, and `0x78316e`; copies default byte `0x78219d` into word `0x782da4`. | Environment motion/status accumulators are reset and the default display/page mode is restored. |")
    lines.append("| `0xce10..0xce3e` | If reset gate `0x7810b2` is clear, calls `0x15a6`, copies default byte `0x7821a2` into `0x782da6`, calls `0x15ac`, and sets `0x782997 = 1`, `0x782998 = 1`. | Some user/default environment bytes are reloaded only in the normal host reset path. |")
    lines.append("| `0xce3e..0xce84` | Clears `0x782990`, sets `0x782a6d = 1`, clears `0x78297e`, `0x782c72`, `0x782c73`, `0x783184`, `0x783185`, `0x782f2c`, `0x78318f`, and `0x783190`, then sets `0x783191 = 1`. | Page/transient text flags, line-termination mode, and display-function bytes return to reset defaults before printing resumes. |")
    lines.append("| `0xce84..0xcec8` | Recomputes HMI `0x78315c` from primary current-font context `0x782ee6`: flagged contexts use long `+0x24` through `0x10550`; unflagged contexts use word `+0x1a` scaled by `0x00057e40` through `0x3324a` and `0x104d8`. | Horizontal motion after reset remains font-derived, not a fixed constant. |")
    lines.append("| `0xcec8..0xcf38` | Reads default line-spacing word `0x78219e`, normalizes it through `0xcfea`, clamps values below `5` or above `0x80` through `0xcf52`, converts through `0x104d8`, and stores VMI/line advance `0x783160`. | The reset VMI is derived from default/user line spacing but clamped to firmware bounds before cursor motion uses it. |")
    lines.append("| `0xcf38..0xcf50` | Calls `0x15a6`, clears `0x780e99`, then calls `0x15ac`. | Completes the normal environment refresh handshake after default VMI/HMI restoration. |")
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
    lines.append("- `tools/render_fixture_harness.py` now has synthetic `ESC E` byte-stream fixtures for valid-page-root publication and missing-root clearing, plus a mixed `!\\x1bE` fixture that applies valid-root reset after queued text. Exact reset reproduction still needs fixtures that start from a fuller parser-allocated page root; the current page-record reset fixture now compares the modeled published record against the bridged/rendered compact bucket.")
    lines.append("")
    return "\n".join(lines)


def page_geometry_table_report(data: bytes) -> str:
    def add_wrapped(
        lines: list[str],
        text: str,
        prefix: str = "",
        subsequent: str | None = None,
    ) -> None:
        if subsequent is None:
            subsequent = " " * len(prefix)
        lines.extend(textwrap.wrap(
            text,
            width=78,
            initial_indent=prefix,
            subsequent_indent=subsequent,
            break_long_words=False,
            break_on_hyphens=False,
        ))

    word_tables = [
        (
            "height_or_vertical_extent",
            0x00A112,
            "read by `0x009d16`, stored at `0x782db4` by `ESC &l#A`",
        ),
        (
            "width_or_horizontal_extent",
            0x00A128,
            "read by `0x009d4e`, stored at `0x782db2` by `ESC &l#A`",
        ),
        (
            "landscape_margin_table",
            0x00A13E,
            "read by `0x009d86`; used when orientation byte `0x782da3` is nonzero",
        ),
        (
            "portrait_margin_table",
            0x00A154,
            "read by `0x009dbe`; used when orientation byte `0x782da3` is zero",
        ),
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
    manual_logical_dimensions = [
        ("Executive", 1, 0x06, 2025, 3150, 3030, 2175),
        ("Letter", 2, 0x02, 2400, 3300, 3180, 2550),
        ("Legal", 3, 0x05, 2400, 4200, 4080, 2550),
        ("A4", 26, 0x01, 2338, 3507, 3389, 2480),
        ("Monarch", 80, 0x88, 1012, 2250, 2130, 1162),
        ("COM-10", 81, 0x87, 1087, 2850, 2730, 1237),
        ("DL", 90, 0x89, 1157, 2598, 2480, 1299),
        ("C5", 91, 0x8A, 1771, 2704, 2586, 1913),
    ]
    manual_margins = {
        # paper: (portrait_left, portrait_right, portrait_top, portrait_bottom,
        #         landscape_left, landscape_right, landscape_top, landscape_bottom)
        "Executive": (50, 100, 60, 60, 60, 60, 50, 100),
        "Letter": (50, 100, 60, 60, 60, 60, 50, 100),
        "Legal": (50, 100, 60, 60, 60, 60, 50, 100),
        "A4": (50, 92, 60, 58, 60, 58, 50, 92),
        "Monarch": (50, 100, 60, 60, 60, 60, 50, 100),
        "COM-10": (50, 100, 60, 60, 60, 60, 50, 100),
        "DL": (50, 92, 60, 58, 60, 58, 50, 92),
        "C5": (50, 92, 60, 58, 60, 58, 50, 92),
    }

    lines = ["# IC30/IC13 Page Geometry Lookup Tables", ""]
    add_wrapped(
        lines,
        "The lookup routines at `0x009d16`, `0x009d4e`, `0x009d86`, and `0x009dbe` mask "
        "the page-code argument with `0x7f` and accept indexes `0..10`.",
    )
    add_wrapped(
        lines,
        "Values are decoded as big-endian words from the firmware image. Table names are "
        "provisional until each consumer is fully traced.",
    )
    lines.append("")
    lines.append(
        "| Internal index | PCL mapping note | a112 / `0x9d16` | a128 / `0x9d4e` | "
        "a13e / `0x9d86` | a154 / `0x9dbe` |"
    )
    lines.append("| ---: | --- | ---: | ---: | ---: | ---: |")
    for index in internal_codes:
        values = [u16(data, base + index * 2) for _name, base, _desc in word_tables]
        note = pcl_code_notes.get(index, "")
        lines.append(
            f"| {index} | {note} | {values[0]} | {values[1]} | {values[2]} | {values[3]} |"
        )
    lines.append("")
    lines.append("## Manual Logical-Dimension Cross-Check")
    lines.append("")
    add_wrapped(
        lines,
        "The Technical Reference figure values in `notes/pcl4-language.md` match the ROM logical "
        "page dimensions as follows: `0x9d16` is portrait logical width, `0x9dbe` is portrait "
        "logical length, `0x9d4e` is landscape logical width, and `0x9d86` is landscape logical "
        "length."
    )
    lines.append("")
    lines.append("| Paper | PCL | Index | Portrait W | Portrait L | Landscape W | Landscape L | Result |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |")
    all_match = True
    for (
        paper,
        pcl_value,
        internal_code,
        portrait_w,
        portrait_l,
        landscape_w,
        landscape_l,
    ) in manual_logical_dimensions:
        index = internal_code & 0x7F
        rom_portrait_w = u16(data, 0x00A112 + index * 2)
        rom_portrait_l = u16(data, 0x00A154 + index * 2)
        rom_landscape_w = u16(data, 0x00A128 + index * 2)
        rom_landscape_l = u16(data, 0x00A13E + index * 2)
        matches = (
            rom_portrait_w == portrait_w
            and rom_portrait_l == portrait_l
            and rom_landscape_w == landscape_w
            and rom_landscape_l == landscape_l
        )
        all_match = all_match and matches
        result = "match" if matches else "MISMATCH"
        lines.append(
            f"| {paper} | {pcl_value} | {index} | {rom_portrait_w} / {portrait_w} | "
            f"{rom_portrait_l} / {portrait_l} | {rom_landscape_w} / {landscape_w} | "
            f"{rom_landscape_l} / {landscape_l} | {result} |"
        )
    lines.append("")
    add_wrapped(
        lines,
        "- Result: all supported `ESC &l#A` page-size values with manual figure entries "
        f"{'match' if all_match else 'do not match'} the ROM logical page dimensions.",
        subsequent="  ",
    )
    lines.append("")
    lines.append("## Printable-Area Margin Cross-Check")
    lines.append("")
    add_wrapped(
        lines,
        "The same four ROM tables also recover the manual printable-area margins. In portrait, "
        "`0x9d86 - 0x9d16` gives the horizontal margin sum and `0x9dbe - 0x9d4e - 60` "
        "gives the bottom margin. In landscape, `0x9dbe - 0x9d4e` gives the horizontal "
        "margin sum and `0x9d86 - 0x9d16 - 50` gives the bottom margin.",
    )
    lines.append("")
    lines.append("| Paper | Portrait H Sum | Portrait Bottom | Landscape H Sum | Landscape Bottom | Result |")
    lines.append("| --- | ---: | ---: | ---: | ---: | --- |")
    all_margin_match = True
    for (
        paper,
        _pcl_value,
        internal_code,
        _portrait_w,
        _portrait_l,
        _landscape_w,
        _landscape_l,
    ) in manual_logical_dimensions:
        index = internal_code & 0x7F
        rom_portrait_w = u16(data, 0x00A112 + index * 2)
        rom_portrait_l = u16(data, 0x00A154 + index * 2)
        rom_landscape_w = u16(data, 0x00A128 + index * 2)
        rom_landscape_l = u16(data, 0x00A13E + index * 2)
        margins = manual_margins[paper]
        portrait_h_sum = rom_landscape_l - rom_portrait_w
        manual_portrait_h_sum = margins[0] + margins[1]
        portrait_bottom = rom_portrait_l - rom_landscape_w - margins[2]
        manual_portrait_bottom = margins[3]
        landscape_h_sum = rom_portrait_l - rom_landscape_w
        manual_landscape_h_sum = margins[4] + margins[5]
        landscape_bottom = rom_landscape_l - rom_portrait_w - margins[6]
        manual_landscape_bottom = margins[7]
        matches = (
            portrait_h_sum == manual_portrait_h_sum
            and margins[2] == 0x3C
            and portrait_bottom == manual_portrait_bottom
            and landscape_h_sum == manual_landscape_h_sum
            and margins[6] == 0x32
            and landscape_bottom == manual_landscape_bottom
        )
        all_margin_match = all_margin_match and matches
        result = "match" if matches else "MISMATCH"
        lines.append(
            f"| {paper} | {portrait_h_sum} / {manual_portrait_h_sum} | "
            f"{portrait_bottom} / {manual_portrait_bottom} | "
            f"{landscape_h_sum} / {manual_landscape_h_sum} | "
            f"{landscape_bottom} / {manual_landscape_bottom} | {result} |"
        )
    lines.append("")
    add_wrapped(
        lines,
        "- Result: all supported `ESC &l#A` page-size values recover the manual printable-area "
        f"margin sums and bottom margins: {'match' if all_margin_match else 'MISMATCH'}.",
        subsequent="  ",
    )
    lines.append("")
    lines.append("## Consumers")
    lines.append("")
    for name, base, desc in word_tables:
        add_wrapped(lines, f"- `{name}` @`0x{base:06x}`: {desc}.", subsequent="  ")
    add_wrapped(
        lines,
        "- `ESC &l#A` handler `0x00fc74` maps PCL page-size values `1`, `2`, `3`, `26`, "
        "`80`, `81`, `90`, and `91` to internal page codes, writes `0x782da2`, stores width "
        "at `0x782db2` through `0x009d4e`, stores height at `0x782db4` through `0x009d16`, "
        "and then recomputes orientation-dependent extents.",
        subsequent="  ",
    )
    add_wrapped(
        lines,
        "- `ESC &l#O` handler `0x010220` accepts only absolute values `0` and `1`, writes "
        "orientation byte `0x782da3`, calls the same margin/extent helpers, and reloads four "
        "orientation threshold words through `0x0103ea`; `tools/render_fixture_harness.py` "
        "now drives chained `ESC &l1a1O` through page-size handler `0xfc74` and orientation "
        "handler `0x10220`.",
        subsequent="  ",
    )
    add_wrapped(
        lines,
        "- `ESC &l#D` handler `0x00c992` takes absolute lines-per-inch, treats `0` as `12`, "
        "accepts only `1,2,3,4,6,8,12,16,24,48`, converts to packed line advance as "
        "`3600 / LPI` twelfths, rejects values beyond `0x782dba`, stores `0x783160`, sets "
        "`0x782ee1`, and refreshes pending vertical cursor "
        "`0x782c8e = 0x782dce + VMI * 18 / 25` when text is pending.",
        subsequent="  ",
    )
    add_wrapped(
        lines,
        "- `ESC &l#C` handler `0x00cb00` takes absolute VMI in 1/48-inch units with "
        "fractional support, rejects integer parts above `0x150` or converted values beyond "
        "`0x782dba`, stores `0x783160`, refreshes pending vertical cursor with the same "
        "`VMI * 18 / 25` offset, and sets `0x782ee1` only when the converted VMI is nonzero.",
        subsequent="  ",
    )
    add_wrapped(
        lines,
        "- `ESC &l#E` handler `0x00ece2` scales top margin lines through current VMI, rejects "
        "zero-VMI or positions at/beyond `0x782dba`, stores "
        "`0x782dce = top_margin - 0x782dbe`, recomputes default text-length bottom through "
        "helper `0xea16`, refreshes pending vertical cursor, then calls `0xfe54` and "
        "`0x12b96`.",
        subsequent="  ",
    )
    add_wrapped(
        lines,
        "- `ESC &l#F` handler `0x00ea9e` scales text length lines through current VMI, "
        "rejects zero-VMI and lengths beyond the remaining page after current top margin, "
        "stores `0x782dd2 = 0x782dce + text_length`, and uses helper `0xea16` to restore the "
        "default text-length bottom when the parameter is zero.",
        subsequent="  ",
    )
    add_wrapped(
        lines,
        "- `0x009e56` computes `(0x051f - floor(argument / 2)) mod 16` through signed "
        "remainder helper `0x033238`; `ESC &l#A` feeds it the `0x782db4` table value and "
        "stores the result at `0x782dc0`.",
        subsequent="  ",
    )
    add_wrapped(
        lines,
        "- Coordinate helpers at `0x0104d8..0x010550` convert between a packed 12-subunit "
        "fixed-point form and integer coordinates; raster code uses these helpers around "
        "`0x0105d0..0x010758`.",
        subsequent="  ",
    )
    lines.append("")
    return "\n".join(lines)


def raster_graphics_flow_report(data: bytes) -> str:
    def add_wrapped(lines: list[str], text: str, prefix: str = "", subsequent: str | None = None) -> None:
        if subsequent is None:
            subsequent = " " * len(prefix)
        lines.extend(textwrap.wrap(
            text,
            width=100,
            initial_indent=prefix,
            subsequent_indent=subsequent,
            break_long_words=False,
            break_on_hyphens=False,
        ))

    def fmt_refs(refs: list[int]) -> str:
        if not refs:
            return "(none)"
        text = ", ".join(f"`0x{ref:06x}`" for ref in refs[:12])
        if len(refs) > 12:
            text += f", ... ({len(refs)} total)"
        return text

    command_handlers = [
        (
            "`ESC *t#R`",
            "0x10808",
            "Maps the parsed resolution to raster mode/scale state at `0x783170`. "
            "The executable stream fixtures pin 300/150/100/75 dpi as modes `0..3`.",
        ),
        (
            "`ESC *r#A`",
            "0x1075a",
            "Starts raster graphics, captures the current cursor-derived origin/baseline, and "
            "computes the row limit used by later transfers.",
        ),
        (
            "`ESC *r#B`",
            "0x107fa",
            "Clears only the active raster state; a later `ESC *t#R` can still change mode.",
        ),
        (
            "`ESC *b#W`",
            "0x11f82 -> 0x121cc -> 0x105d0",
            "Records a delayed payload handler. `0x12218` restores the six-byte command record "
            "and dispatches `0x105d0` after the payload begins.",
        ),
    ]
    queue_steps = [
        (
            "`0x105d0`",
            "Restored raster-transfer handler. It checks active state and row limits, caps the "
            "stored byte count to the printable gate, drains any overflow bytes, and advances the "
            "raster row only for accepted transfers.",
        ),
        (
            "`0x10084`",
            "Ensures the current page/control root before an accepted row object is queued.",
        ),
        (
            "`0x13070`",
            "Builds the raster row source object from raster x/y, mode, byte count, and payload "
            "metadata.",
        ),
        (
            "`0x13250`",
            "Allocates and links the encoded-span bucket object under page-root `+0x1c`; raster "
            "objects are born with byte `+4 = 0x80` and byte `+5` selecting encoded mode.",
        ),
        (
            "`0x138de`",
            "Copies the accepted host payload bytes into the queued object starting at `+0x0a`.",
        ),
        (
            "`0x1edc6`",
            "Copies the page-root bucket array to render-record `+0x18` without normalizing raster "
            "objects.",
        ),
        (
            "`0x1efc2 -> 0x1f88e`",
            "Dispatches the high-bit encoded-span object to the raster renderer. The low two bits "
            "of object byte `+5` select modes `0..3` through table `0x1f8ca`.",
        ),
    ]
    state_addresses = [
        (0x00783170, "raster graphics state block base used by reset, mode, start, and transfer paths"),
        (0x00782C8A, "current horizontal cursor word captured as raster start axis/source x"),
        (0x00782C8E, "current vertical cursor word captured as raster start axis/source y"),
        (0x00782DB4, "page extent/input used while computing raster transfer limits"),
        (0x00782DB6, "vertical page extent used by geometry/raster clipping paths"),
        (0x00782DB8, "horizontal page extent used by geometry/raster clipping paths"),
        (0x0078297A, "current page-root pointer ensured before queuing accepted raster rows"),
        (0x00782A70, "remaining object-storage bytes reset by `0x10084` and consumed by allocators"),
        (0x00782A72, "current object-storage chunk link pointer seeded from root `+0x20`"),
        (0x00782A76, "next-free object-storage pointer used by the shared allocator"),
    ]

    lines = ["# IC30/IC13 Raster Graphics Flow", ""]
    add_wrapped(
        lines,
        "This report collects the raster command edge, delayed payload handoff, page-object "
        "queueing, and bitmap render dispatch from the verified firmware image.",
    )
    lines.append("")

    lines.append("## Command and Payload Edge")
    lines.append("")
    for command, handler, behavior in command_handlers:
        lines.append(f"- {command}")
        lines.append(f"  - Handler: `{handler}`")
        add_wrapped(lines, behavior, "  - Firmware behavior: ", "    ")
    lines.append("")

    lines.append("## Queue and Render Path")
    lines.append("")
    for routine, behavior in queue_steps:
        add_wrapped(lines, behavior, f"- {routine}: ", "  ")
    lines.append("")

    lines.append("## Parser/Data Boundary")
    lines.append("")
    add_wrapped(
        lines,
        "Normal parser table entries route `ESC *t#R`, `ESC *r#A`, and `ESC *b#W` through "
        "`0x10808`, `0x1075a`, and `0x11f82` respectively.",
        "- ",
        "  ",
    )
    add_wrapped(
        lines,
        "`0x11f82` does not copy raster bytes directly. It snapshots the delayed handler "
        "`0x105d0` through `0x121cc`, so payload bytes are consumed only after `0x12218` restores "
        "the command record.",
        "- ",
        "  ",
    )
    add_wrapped(
        lines,
        "Lowercase-final `ESC *b#w` preserves parser mode in the `*b` family. The uppercase "
        "`W` terminator replaces the delayed snapshot and starts exactly one payload transfer.",
        "- ",
        "  ",
    )
    add_wrapped(
        lines,
        "The harness ties this to ROM parser traces for 300/150/100/75-dpi streams, consecutive "
        "rows, capped transfers, beyond-extent drains, and same-group lowercase-final transfer "
        "boundaries.",
        "- ",
        "  ",
    )
    lines.append("")

    lines.append("## State Reference Scan")
    lines.append("")
    for address, role in state_addresses:
        lines.append(f"- `0x{address:08x}`")
        add_wrapped(lines, role, "  - Role: ", "    ")
        add_wrapped(
            lines,
            fmt_refs(find_all(data, address.to_bytes(4, "big"))),
            "  - Longword literal references: ",
            "    ",
        )
    lines.append("")

    lines.append("## Call-Site Anchors")
    lines.append("")
    add_wrapped(
        lines,
        "`0x10084` ensure-root calls from raster transfer sites: "
        f"{fmt_refs([ref for ref in (0x0106A4, 0x0106EC) if ref in jsr_abs_refs(data, 0x00010084)])}.",
        "- ",
        "  ",
    )
    add_wrapped(
        lines,
        "`0xff1e` finalization calls from raster page-boundary site: "
        f"{fmt_refs([ref for ref in (0x0106E6,) if ref in jsr_abs_refs(data, 0x0000FF1E)])}.",
        "- ",
        "  ",
    )
    add_wrapped(lines, f"`0x13070` raster row builder references: {fmt_refs(jsr_abs_refs(data, 0x00013070))}.", "- ", "  ")
    add_wrapped(lines, f"`0x13250` bucket object allocator references: {fmt_refs(jsr_abs_refs(data, 0x00013250))}.", "- ", "  ")
    add_wrapped(lines, f"`0x138de` raster payload copy references: {fmt_refs(jsr_abs_refs(data, 0x000138DE))}.", "- ", "  ")
    lines.append("")

    lines.append("## Current Reproduction Contract")
    lines.append("")
    add_wrapped(
        lines,
        "A byte-stream reproduction must preserve the delayed `ESC *b#W` payload boundary: the "
        "six-byte parsed record and the payload bytes are separate pieces of state until "
        "`0x12218` restores and dispatches `0x105d0`.",
        "- ",
        "  ",
    )
    add_wrapped(
        lines,
        "Accepted transfers must ensure a page root before `0x13070` / `0x13250` queue the row "
        "object. Drained transfers beyond the page extent consume host bytes but do not queue an "
        "object or advance the row counter.",
        "- ",
        "  ",
    )
    add_wrapped(
        lines,
        "Raster row objects share the page-root `+0x1c` bucket array with compact text buckets, "
        "but render through the encoded-span high-bit branch rather than the compact glyph branch.",
        "- ",
        "  ",
    )
    add_wrapped(
        lines,
        "`tools/render_fixture_harness.py` currently proves parser dispatch, delayed restore, "
        "root allocation, object bytes, bridge copying, and final rendered rows for the primary "
        "`ESC *t300R` / `ESC *r1A` / `ESC *b4W` stream, plus mode, cap/drain, multi-row, "
        "lowercase-final, and end-raster variants. The mixed "
        "`!\\x1b*c12a5b0P\\x1b*t300R\\x1b*r0A\\x1b*b2W` fixture now also has an addressed "
        "allocation variant where the raster row queues through addressed `0x13070` / "
        "`0x13250` storage after the addressed text and rule objects, then renders the same "
        "bucket/rule/raster rows and publishes the materialized addressed record through the "
        "modeled `0xff1e` pool-record boundary.",
        "- ",
        "  ",
    )
    add_wrapped(
        lines,
        "Remaining work is a fuller CPU/parser-state fixture that replaces modeled state with "
        "real page/control pool records while preserving the same byte-stream-to-pixel boundary.",
        "- ",
        "  ",
    )
    lines.append("")
    return "\n".join(lines)


def rectangle_graphics_flow_report(data: bytes) -> str:
    def fmt_refs(refs: list[int]) -> str:
        if not refs:
            return "(none)"
        shown = ", ".join(f"`0x{ref:06x}`" for ref in refs[:12])
        if len(refs) > 12:
            shown += f", ... ({len(refs)} total)"
        return shown

    state_addresses = [
        (0x00782C8A, "current horizontal cursor word used as rectangle start x"),
        (0x00782C8E, "current vertical cursor word used as rectangle start y"),
        (0x00782DB6, "vertical page extent used to reject/clip rectangle height"),
        (0x00782DB8, "horizontal page extent used to reject/clip rectangle width"),
        (0x00782DC0, "horizontal page/raster phase added into rectangle object key by `0x134d6`"),
        (0x00783166, "current rectangle height, written by `ESC *c#B/#V`"),
        (0x0078316A, "current rectangle width, written by `ESC *c#A/#H`"),
        (0x0078316E, "current area-fill id, written by `ESC *c#G` and consumed by `ESC *c#P`"),
    ]
    lines = ["# IC30/IC13 Rectangle Graphics Flow", ""]
    lines.append("This report tracks the PCL rectangle/rule command edge into the already-modeled page-record rule-list producer. Names remain provisional where exact pattern rendering is still open.")
    lines.append("")
    lines.append("## Command Handlers")
    lines.append("")
    lines.append("| Command | Handler | Firmware behavior | Reproduction consequence |")
    lines.append("| --- | ---: | --- | --- |")
    lines.append("| `ESC *c#A` | `0x10e68` | requires an explicit positive integer dot width, stores it as packed word `0x78316a`, otherwise clears width | dot width state is integer pixels before clipping |")
    lines.append("| `ESC *c#B` | `0x10e22` | requires an explicit positive integer dot height, stores it as packed word `0x783166`, otherwise clears height | dot height state is integer pixels before clipping |")
    lines.append("| `ESC *c#H` | `0x10a40` | converts explicit nonnegative decipoints through five 300-dpi subunits per decipoint, rounds up to a pixel by adding eleven subunits before packed conversion, and stores `0x78316a`; missing, negative, or zero values clear width | decipoint width is rounded up before the fill command sees the integer word |")
    lines.append("| `ESC *c#V` | `0x10ae0` | same decipoint conversion as width and stores `0x783166` | decipoint height is rounded up before clipping/queuing |")
    lines.append("| `ESC *c#G` | `0x10dce` | stores absolute nonzero area-fill id in `0x78316e`; missing or zero clears it | `ESC *c2P` and `ESC *c3P` use this id as their selector input |")
    lines.append("| `ESC *c#P` | `0x10898` | maps fill mode `0`/missing to selector `7`; mode `2` maps area-fill percentages through threshold selectors `0..7`; mode `3` maps pattern ids `1..6` to selectors `8..13`, with portrait/landscape remaps for ids `1..4`; if width/height are nonzero, calls `0x10b80` | fill command validates selector, clips the rectangle to page extents, and queues a rule-list object through `0x13386` |")
    lines.append("")
    lines.append("## Queue Path")
    lines.append("")
    lines.append("- `0x10b80` rejects rectangles starting beyond the printable extents, clips negative starts and overlong width/height, handles landscape coordinate swapping, ensures a page root through `0x10084`, then queues source record `0x782a88` through `0x13386`.")
    lines.append("- If `0x13386` reports no room, `0x10d22..0x10d3e` sets page-root flag bit `root+0x15.0`, finalizes the current root through `0xff1e`, ensures a fresh root through `0x10084`, and retries the same source record. This is the rectangle/rule counterpart to the text queue retry paths.")
    lines.append("- `0x13386` runs `0x134d6` to compute bucket word `0x782a7c` and compact rule key `0x782a7e` from source x/y plus `0x782dc0`; `0x133aa` stores the low bucket byte at object `+4` and inserts a 14-byte object under page-root `+0x24`. The executable addressed fixture now allocates these objects through `0x1381c`, verifies the `+0` next links, and pins sorted insertion for earlier, later, and equal bucket bytes.")
    lines.append("- `0x1edc6` later copies page-root `+0x24` to render-record `+0x1c`, ORs object byte `+5` with `0x10`, and copies height word `+0x0a` to `+0x0c` before `0x1f446` dispatch.")
    lines.append("- `0x1f446` walks the bridged rule list for each five-bucket render band. Selector `7` dispatches to solid helper `0x1f596`, which decodes the packed key through `0x1f626`/`$a001` sub-byte positioning and writes full `0xffff` words plus a trailing mask from table `0x308be`; the other selectors dispatch to pattern helper `0x1f4e0`, which uses the pointer table at `0x2fefe` and the same mask helper `0x1f6ee`.")
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
    lines.append("- A byte-stream model must preserve rectangle width/height state across commands until `ESC *c#P` consumes it; reset/rebuild paths clear `0x78316a`, `0x783166`, and `0x78316e`.")
    lines.append("- Dot sizes and decipoint sizes are not interchangeable at fractional boundaries: decipoint handlers round up with the firmware's `+11` subunit bias before storing the packed value.")
    lines.append("- `tools/render_fixture_harness.py` now pins dot/decipoint size stores, `ESC *c#G` absolute/clear behavior, `ESC *c#P` selector mapping, a chained `ESC *c12a5b0P` byte stream queueing the selector-7 rule object plus a ROM `0x11774` dispatch trace for the same stream, portrait rule-list object queueing/bridge normalization, solid black selector-7 rendering through `0x1f446`/`0x1f596`, solid and patterned rule band-crossing continuation, a two-band page-row assembly for a crossing HP-pattern rule, gray selectors `0..6` and HP pattern selectors `8..13` through `0x1f446`/`0x1f4e0`, sub-byte HP pattern masks/pixels, left/right/top/bottom and landscape edge clipping plus off-page ignore reasons, and a parser-to-retry boundary that ties the same `ESC *c12a5b0P` handlers `0x10e68`/`0x10e22`/`0x10898` to the `0x10d22` no-room path through `0xff1e`, `0x10084`, `0x13386`, `0x1edc6`, and rule rendering. Remaining work is parser-produced full-page comparisons for these rule paths.")
    lines.extend([
        "- The mixed `!\\x1b*c12a5b0P` fixture now has an addressed allocation",
        "  variant: printable `!` queues through addressed `0x1387c`, the chained",
        "  rectangle queues through addressed `0x133aa`, and the materialized",
        "  record matches the older byte-list bridge/render output.",
    ])
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
    glyph_payload_report, glyph_payload_json = builtin_glyph_payload_extract(resources)

    firmware_strings = extract_strings(firmware)
    resource_strings = extract_strings(resources)
    write_if_changed(ANALYSIS / "ic30_ic13_strings.txt", format_strings("IC30/IC13 Strings", firmware_strings))
    write_if_changed(ANALYSIS / "ic32_ic15_strings.txt", format_strings("IC32/IC15 Strings", resource_strings))
    write_if_changed(ANALYSIS / "ic32_ic15_resource_markers.txt", resource_marker_report(resources))
    write_if_changed(ANALYSIS / "ic32_ic15_font_records.md", font_record_report(resources))
    write_if_changed(ANALYSIS / "ic32_ic15_resource_glyph_probe.md", resource_glyph_probe_report(resources))
    write_if_changed(ANALYSIS / "ic32_ic15_builtin_glyph_payloads.md", glyph_payload_report)
    write_if_changed(ANALYSIS / "ic32_ic15_builtin_glyph_payloads.json", glyph_payload_json)
    write_if_changed(ANALYSIS / "ic32_ic15_builtin_font_samples.md", builtin_font_sample_report(resources))
    write_if_changed(ANALYSIS / "ic30_ic13_font_sample_page.md", font_sample_page_report_with_resources(firmware, resources))
    write_if_changed(ANALYSIS / "ic30_ic13_startup_tables.txt", decode_startup_tables(firmware))
    write_if_changed(ANALYSIS / "signature_scan.md", scan_signature_report(firmware, resources))
    write_if_changed(ANALYSIS / "ic30_ic13_long_reference_scan.md", categorized_long_references(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_cmpi_byte_candidates.md", cmpi_byte_candidates(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_parser_xrefs.md", xref_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_tokenizer_macro_callers.md", tokenizer_macro_caller_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_host_byte_fetch_flow.md", host_byte_fetch_flow_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_font_control_flow.md", font_control_flow_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_direct_control_code_flow.md", direct_control_code_flow_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_esc_e_reset_flow.md", esc_e_reset_flow_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_literal_patterns.md", byte_pattern_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_page_root_references.md", page_root_reference_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_page_root_allocation.md", page_root_allocation_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_page_root_finalization.md", page_root_finalization_report(firmware))
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
    write_if_changed(ANALYSIS / "ic30_ic13_symbol_set_patch_tables.md", symbol_set_patch_table_report(firmware, resources))
    write_if_changed(ANALYSIS / "ic30_ic13_render_expansion_fixtures.md", render_expansion_fixture_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_render_destination_fixtures.md", render_destination_fixture_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_render_row_copy_fixtures.md", render_row_copy_fixture_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_parser_dispatch_tables.md", parser_dispatch_table_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_pcl_command_map.md", parser_command_map_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_page_geometry_tables.md", page_geometry_table_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_raster_graphics_flow.md", raster_graphics_flow_report(firmware))
    write_if_changed(ANALYSIS / "ic30_ic13_rectangle_graphics_flow.md", rectangle_graphics_flow_report(firmware))

    if DISASM.exists():
        write_if_changed(ANALYSIS / "ic30_ic13_reset_absolute_refs.md", absolute_reference_report(DISASM.read_text(encoding="utf-8")))

    print(f"firmware strings: {len(firmware_strings)}")
    print(f"resource strings: {len(resource_strings)}")
    print("analysis output: generated/analysis")


if __name__ == "__main__":
    main()
