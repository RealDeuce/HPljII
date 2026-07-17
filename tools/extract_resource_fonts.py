#!/usr/bin/env python3
"""Extract LaserJet resource-ROM font records into an emulator asset."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from tools.analyze_roms import firmware_scanned_font_records, s16, u16, u32
    from tools.probe_resource_window import resource_head_scan
except ModuleNotFoundError:
    from analyze_roms import firmware_scanned_font_records, s16, u16, u32
    from probe_resource_window import resource_head_scan


SCHEMA = "hp-laserjet-resource-fonts-v1"
FIXED_BANK_SIZE = 0x40000
FIXED_HEADER_SIZE = 0x40
FIXED_ENTRY_SIZE = 8
FIXED_LOW_SLOT_COUNT = 96


def parse_int(value: str) -> int:
    try:
        return int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer: {value}") from exc


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def mapped_address(base_address: int | None, offset: int) -> int | None:
    if base_address is None:
        return None
    return base_address + offset


def stored_record_name(
    data: bytes,
    record: dict[str, int | str | None],
) -> dict[str, Any]:
    first_char = int(record["first_char"])
    last_char = int(record["last_char"])
    slot_count = max(0, last_char - first_char + 1)
    name_header = int(record["table"]) + slot_count * 4
    record_end = int(record["record_start"]) + int(record["length"])

    if name_header + 2 > min(record_end, len(data)):
        return {
            "offset": None,
            "length": 0,
            "text": str(record["name"]),
            "bytes_hex": "",
            "status": "name-header-out-of-range",
        }

    length = u16(data, name_header)
    name_start = name_header + 2
    name_end = name_start + length
    if length > 25 or name_end > min(record_end, len(data)):
        return {
            "offset": name_start,
            "length": length,
            "text": str(record["name"]),
            "bytes_hex": "",
            "status": "invalid-name-length",
        }

    raw = data[name_start:name_end]
    printable = all(0x20 <= byte <= 0x7E for byte in raw)
    return {
        "offset": name_start,
        "length": length,
        "text": raw.decode("ascii") if printable else raw.decode("ascii", errors="replace"),
        "bytes_hex": raw.hex(),
        "status": "decoded" if printable else "non-ascii",
    }


def selection_fields(
    data: bytes,
    record_start: int,
) -> dict[str, int]:
    """Return raw fields read by the firmware's font-selection paths."""

    return {
        "byte_0x0c": data[record_start + 0x0C],
        "byte_0x0d": data[record_start + 0x0D],
        "first_char_0x0e": u16(data, record_start + 0x0E),
        "last_char_0x10": u16(data, record_start + 0x10),
        "word_0x12": u16(data, record_start + 0x12),
        "word_0x14": u16(data, record_start + 0x14),
        "word_0x1c": u16(data, record_start + 0x1C),
        "word_0x1e": u16(data, record_start + 0x1E),
        "class_0x20": data[record_start + 0x20],
        "spacing_0x21": data[record_start + 0x21],
        "symbol_0x22": u16(data, record_start + 0x22),
        "pitch_word_0x24": u16(data, record_start + 0x24),
        "pitch_byte_0x26": data[record_start + 0x26],
        "height_word_0x28": u16(data, record_start + 0x28),
        "height_byte_0x2a": data[record_start + 0x2A],
        "byte_0x2f": data[record_start + 0x2F],
        "byte_0x30": data[record_start + 0x30],
        "byte_0x31": data[record_start + 0x31],
        "byte_0x3c": data[record_start + 0x3C],
    }


def extract_glyph_slots(
    data: bytes,
    record: dict[str, int | str | None],
    base_address: int | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    record_start = int(record["record_start"])
    record_end = record_start + int(record["length"])
    table = int(record["table"])
    first_char = int(record["first_char"])
    last_char = int(record["last_char"])
    requested_slots = max(0, last_char - first_char + 1)
    available_slots = max(0, (min(record_end, len(data)) - table) // 4)
    slot_count = min(requested_slots, available_slots)

    slots: list[dict[str, Any]] = []
    extracted = 0
    absent = 0
    no_normal_payload = 0
    payload_bytes = 0
    modes: dict[str, int] = {}

    for glyph_index in range(slot_count):
        host_byte = first_char + glyph_index
        table_entry = table + glyph_index * 4
        relative = u32(data, table_entry)
        slot: dict[str, Any] = {
            "host_byte": host_byte,
            "glyph_index": glyph_index,
            "table_entry_offset": table_entry,
            "relative_offset": relative,
        }
        table_address = mapped_address(base_address, table_entry)
        if table_address is not None:
            slot["table_entry_address"] = table_address

        if relative == 0:
            slot["status"] = "absent"
            absent += 1
            slots.append(slot)
            continue

        entry = record_start + relative
        if entry < 0 or entry + 10 > len(data):
            raise ValueError(
                f"record 0x{record_start:06x} host byte 0x{host_byte:02x}: "
                f"glyph entry 0x{entry:06x} is outside the image"
            )

        bitmap_delta = data[entry + 4]
        mode = data[entry + 5]
        rows = u16(data, entry + 6)
        width = u16(data, entry + 8)
        storage_span = (width + 7) // 8 if width else 0
        render_span = storage_span
        if render_span & 1 and mode != 2 and render_span != 1:
            render_span += 1
        bitmap = entry + bitmap_delta
        payload_length = rows * max(render_span, 1)
        slot.update(
            {
                "entry_offset": entry,
                "entry_in_record": record_start <= entry < record_end,
                "entry_header_hex": data[entry : entry + 10].hex(),
                "entry_prefix_hex": data[entry:bitmap].hex(),
                "x_offset": s16(data, entry),
                "y_offset": s16(data, entry + 2),
                "bitmap_delta": bitmap_delta,
                "mode": mode,
                "rows": rows,
                "width": width,
                "storage_span": storage_span,
                "render_span": render_span,
                "bitmap_offset": bitmap,
                "bitmap_in_record": (
                    record_start <= bitmap
                    and bitmap + payload_length <= record_end
                ),
                "payload_length": payload_length,
            }
        )
        entry_address = mapped_address(base_address, entry)
        bitmap_address = mapped_address(base_address, bitmap)
        if entry_address is not None and bitmap_address is not None:
            slot["entry_address"] = entry_address
            slot["bitmap_address"] = bitmap_address

        mode_key = str(mode)
        modes[mode_key] = modes.get(mode_key, 0) + 1
        if bitmap_delta == 0 or rows == 0 or width == 0:
            slot["status"] = "no-normal-payload"
            no_normal_payload += 1
            slots.append(slot)
            continue
        if bitmap < 0 or bitmap + payload_length > len(data):
            raise ValueError(
                f"record 0x{record_start:06x} host byte 0x{host_byte:02x}: "
                f"bitmap 0x{bitmap:06x}+0x{payload_length:x} exceeds the image"
            )

        payload = data[bitmap : bitmap + payload_length]
        slot.update(
            {
                "status": "extracted",
                "payload_sha256": sha256(payload),
                "payload_hex": payload.hex(),
            }
        )
        extracted += 1
        payload_bytes += payload_length
        slots.append(slot)

    summary = {
        "requested_slots": requested_slots,
        "emitted_slots": slot_count,
        "extracted_glyphs": extracted,
        "absent_glyphs": absent,
        "no_normal_payload_glyphs": no_normal_payload,
        "payload_bytes": payload_bytes,
        "modes": modes,
    }
    return slots, summary


def build_head_asset(
    source_path: Path,
    data: bytes,
    label: str,
    base_address: int | None,
) -> dict[str, Any]:
    head_scan = resource_head_scan(data, scan_span=len(data))
    if head_scan["head_offsets"] != [0]:
        raise ValueError(
            "resource image must contain exactly one HEAD chain at offset 0"
        )
    if head_scan["status"] != "end":
        raise ValueError(f"resource HEAD scan ended with {head_scan['status']}")

    records = firmware_scanned_font_records(data)
    if len(records) != len(head_scan["walked_records"]):
        raise ValueError(
            f"HEAD walker found {len(head_scan['walked_records'])} records, "
            f"font scanner accepted {len(records)}"
        )

    output_records: list[dict[str, Any]] = []
    total_slots = 0
    total_glyphs = 0
    total_absent = 0
    total_no_normal_payload = 0
    total_payload_bytes = 0
    total_modes: dict[str, int] = {}

    for scan_index, record in enumerate(records):
        record_start = int(record["record_start"])
        record_length = int(record["length"])
        record_end = record_start + record_length
        table_delta = int(record["table"]) - record_start
        name = stored_record_name(data, record)
        slots, glyph_summary = extract_glyph_slots(data, record, base_address)

        output_record: dict[str, Any] = {
            "scan_index": scan_index,
            "name": name,
            "record_offset": record_start,
            "record_type": u32(data, record_start),
            "record_length": record_length,
            "record_sha256": sha256(data[record_start:record_end]),
            "offset_table_delta": table_delta,
            "offset_table_offset": int(record["table"]),
            "header_hex": data[record_start : record_start + table_delta].hex(),
            "selection_fields": selection_fields(data, record_start),
            "decoded_metrics": {
                "pitch_13b76": int(record["pitch_13b76"]),
                "height_13bca": int(record["height_13bca"]),
            },
            "glyph_summary": glyph_summary,
            "glyph_slots": slots,
        }
        record_address = mapped_address(base_address, record_start)
        table_address = mapped_address(base_address, int(record["table"]))
        if record_address is not None and table_address is not None:
            flags = 0x40000000 | (
                (data[record_start + 0x0D] & 0x03) << 28
            )
            if data[record_start + 0x0C] == 2:
                flags |= 0x04000000
            output_record["record_address"] = record_address
            output_record["offset_table_address"] = table_address
            output_record["context_longword"] = flags | record_address
        output_records.append(output_record)

        total_slots += int(glyph_summary["emitted_slots"])
        total_glyphs += int(glyph_summary["extracted_glyphs"])
        total_absent += int(glyph_summary["absent_glyphs"])
        total_no_normal_payload += int(
            glyph_summary["no_normal_payload_glyphs"]
        )
        total_payload_bytes += int(glyph_summary["payload_bytes"])
        for mode, count in dict(glyph_summary["modes"]).items():
            total_modes[str(mode)] = total_modes.get(str(mode), 0) + int(count)

    terminator_offset = 0
    if records:
        last = records[-1]
        terminator_offset = int(last["record_start"]) + int(last["length"])

    return {
        "schema": SCHEMA,
        "label": label,
        "source": {
            "path": str(source_path),
            "size_bytes": len(data),
            "sha256": sha256(data),
        },
        "mapping": {
            "address_mode": "mapped" if base_address is not None else "rom-relative",
            "base_address": base_address,
        },
        "resource_chain": {
            "head_offset": 0,
            "record_count": len(records),
            "terminator_offset": terminator_offset,
            "scan_status": str(head_scan["status"]),
        },
        "summary": {
            "records": len(records),
            "glyph_slots": total_slots,
            "extracted_glyphs": total_glyphs,
            "absent_glyphs": total_absent,
            "no_normal_payload_glyphs": total_no_normal_payload,
            "payload_bytes": total_payload_bytes,
            "modes": total_modes,
        },
        "records": output_records,
    }


def fixed_record_fields(data: bytes, record_start: int) -> dict[str, int]:
    """Expose fixed-record fields used directly by known firmware paths."""

    return {
        "extension_flag_0x0e": data[record_start + 0x0E],
        "byte_0x0f": data[record_start + 0x0F],
        "byte_0x10": data[record_start + 0x10],
        "byte_0x11": data[record_start + 0x11],
        "byte_0x16": data[record_start + 0x16],
        "symbol_set_0x17": data[record_start + 0x17],
        "typeface_0x18": data[record_start + 0x18],
        "spacing_0x19": data[record_start + 0x19],
        "pitch_0x1a": u16(data, record_start + 0x1A),
        "word_0x1c": u16(data, record_start + 0x1C),
        "height_0x20": u16(data, record_start + 0x20),
        "byte_0x26": data[record_start + 0x26],
        "byte_0x27_signed": int.from_bytes(
            data[record_start + 0x27 : record_start + 0x28],
            "big",
            signed=True,
        ),
        "next_record_delta_0x2e": u32(data, record_start + 0x2E),
    }


def walk_fixed_banks(data: bytes) -> list[dict[str, Any]]:
    if not data or len(data) % FIXED_BANK_SIZE:
        raise ValueError(
            "fixed FONT image size must be a nonzero multiple of 0x40000"
        )

    banks: list[dict[str, Any]] = []
    for bank_index, bank_start in enumerate(
        range(0, len(data), FIXED_BANK_SIZE)
    ):
        bank_end = bank_start + FIXED_BANK_SIZE
        if data[bank_start : bank_start + 4] != b"FONT":
            raise ValueError(
                f"fixed bank {bank_index} does not start with FONT"
            )

        record_offsets: list[int] = []
        cursor = bank_start
        terminal_offset: int | None = None
        terminator_offset: int | None = None

        while cursor + FIXED_HEADER_SIZE <= bank_end:
            if data[cursor : cursor + 4] != b"FONT":
                raise ValueError(
                    f"fixed bank {bank_index} expected FONT at "
                    f"0x{cursor:06x}"
                )
            name_bytes = data[cursor + 4 : cursor + 14]
            name = name_bytes.rstrip(b"\x00 ").decode(
                "ascii", errors="replace"
            )
            delta = u32(data, cursor + 0x2E)
            if delta < FIXED_HEADER_SIZE:
                raise ValueError(
                    f"fixed record at 0x{cursor:06x} has invalid "
                    f"next delta 0x{delta:x}"
                )
            next_cursor = cursor + delta
            if next_cursor > bank_end or next_cursor <= cursor:
                raise ValueError(
                    f"fixed record at 0x{cursor:06x} leaves bank at "
                    f"0x{next_cursor:06x}"
                )

            if name == "DUMMY":
                terminal_offset = cursor
                terminator_offset = next_cursor
                break

            record_offsets.append(cursor)
            cursor = next_cursor
        else:
            raise ValueError(f"fixed bank {bank_index} has no DUMMY record")

        if terminal_offset is None or terminator_offset is None:
            raise ValueError(f"fixed bank {bank_index} has no DUMMY record")
        if any(data[terminator_offset : terminator_offset + 4]):
            raise ValueError(
                f"fixed bank {bank_index} has no zero terminator at "
                f"0x{terminator_offset:06x}"
            )

        banks.append(
            {
                "bank_index": bank_index,
                "bank_offset": bank_start,
                "bank_size": FIXED_BANK_SIZE,
                "record_offsets": record_offsets,
                "terminal_record_offset": terminal_offset,
                "terminator_offset": terminator_offset,
                "scan_status": "end",
            }
        )

    return banks


def extract_fixed_glyph_slots(
    data: bytes,
    record_start: int,
    bank_start: int,
    base_address: int | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    extension_flag = data[record_start + 0x0E]
    slot_count = FIXED_LOW_SLOT_COUNT * (2 if extension_flag else 1)
    bank_end = bank_start + FIXED_BANK_SIZE
    slots: list[dict[str, Any]] = []
    extracted = 0
    absent = 0
    payload_bytes = 0
    layouts: dict[str, int] = {}

    for glyph_index in range(slot_count):
        if glyph_index < FIXED_LOW_SLOT_COUNT:
            host_byte = 0x20 + glyph_index
        else:
            host_byte = 0xA0 + glyph_index - FIXED_LOW_SLOT_COUNT

        entry = record_start + FIXED_HEADER_SIZE
        entry += glyph_index * FIXED_ENTRY_SIZE
        if entry + FIXED_ENTRY_SIZE > bank_end:
            raise ValueError(
                f"fixed record 0x{record_start:06x} glyph "
                f"0x{host_byte:02x} has an entry outside its bank"
            )

        span = data[entry]
        rows = data[entry + 1]
        relative_raw = u32(data, entry + 4)
        relative = relative_raw & 0x00FFFFFF
        bitmap = record_start + relative
        valid = span != 0 and rows != 0 and relative != 0
        reject_reason: str | None = None

        if valid and span == 1 and rows == 2:
            if bitmap < bank_start or bitmap + 2 > bank_end:
                valid = False
                reject_reason = "special-bitmap-outside-bank"
            elif u16(data, bitmap) == 0:
                valid = False
                reject_reason = "special-bitmap-word-zero"
        elif not valid:
            if span == 0:
                reject_reason = "zero-span"
            elif rows == 0:
                reject_reason = "zero-rows"
            else:
                reject_reason = "zero-bitmap-offset"

        slot: dict[str, Any] = {
            "host_byte": host_byte,
            "glyph_index": glyph_index,
            "entry_offset": entry,
            "entry_hex": data[entry : entry + FIXED_ENTRY_SIZE].hex(),
            "span_bytes": span,
            "rows": rows,
            "byte_0x02_signed": int.from_bytes(
                data[entry + 2 : entry + 3], "big", signed=True
            ),
            "byte_0x03": data[entry + 3],
            "bitmap_relative_raw": relative_raw,
            "bitmap_relative_24": relative,
        }
        entry_address = mapped_address(base_address, entry)
        if entry_address is not None:
            slot["entry_address"] = entry_address

        if not valid:
            slot["status"] = "absent"
            slot["reject_reason"] = reject_reason
            absent += 1
            slots.append(slot)
            continue

        payload_length = span * rows
        if bitmap < bank_start or bitmap + payload_length > bank_end:
            raise ValueError(
                f"fixed record 0x{record_start:06x} glyph "
                f"0x{host_byte:02x} bitmap 0x{bitmap:06x}+"
                f"0x{payload_length:x} leaves its bank"
            )

        layout = (
            "split-last-byte-plane"
            if span > 1 and span & 1
            else "linear-rows"
        )
        payload = data[bitmap : bitmap + payload_length]
        slot.update(
            {
                "status": "extracted",
                "bitmap_offset": bitmap,
                "payload_layout": layout,
                "payload_length": payload_length,
                "payload_sha256": sha256(payload),
                "payload_hex": payload.hex(),
            }
        )
        bitmap_address = mapped_address(base_address, bitmap)
        if bitmap_address is not None:
            slot["bitmap_address"] = bitmap_address
        extracted += 1
        payload_bytes += payload_length
        layouts[layout] = layouts.get(layout, 0) + 1
        slots.append(slot)

    return slots, {
        "requested_slots": slot_count,
        "emitted_slots": slot_count,
        "extracted_glyphs": extracted,
        "absent_glyphs": absent,
        "payload_bytes": payload_bytes,
        "payload_layouts": layouts,
    }


def build_fixed_font_asset(
    source_path: Path,
    data: bytes,
    label: str,
    base_address: int | None,
) -> dict[str, Any]:
    banks = walk_fixed_banks(data)
    output_banks: list[dict[str, Any]] = []
    output_records: list[dict[str, Any]] = []
    total_slots = 0
    total_glyphs = 0
    total_absent = 0
    total_payload_bytes = 0
    total_layouts: dict[str, int] = {}

    for bank in banks:
        bank_index = int(bank["bank_index"])
        bank_start = int(bank["bank_offset"])
        bank_record_indexes: list[int] = []

        for record_offset in list(bank["record_offsets"]):
            record_start = int(record_offset)
            record_length = u32(data, record_start + 0x2E)
            record_end = record_start + record_length
            name_raw = data[record_start + 4 : record_start + 14]
            name = name_raw.rstrip(b"\x00 ").decode(
                "ascii", errors="replace"
            )
            slots, glyph_summary = extract_fixed_glyph_slots(
                data,
                record_start,
                bank_start,
                base_address,
            )
            record_index = len(output_records)
            bank_record_indexes.append(record_index)
            output_record: dict[str, Any] = {
                "scan_index": record_index,
                "bank_index": bank_index,
                "name": {
                    "offset": record_start + 4,
                    "length": len(name_raw.rstrip(b"\x00 ")),
                    "text": name,
                    "bytes_hex": name_raw.hex(),
                    "status": "decoded",
                },
                "record_offset": record_start,
                "record_type_ascii": "FONT",
                "record_length": record_length,
                "record_sha256": sha256(data[record_start:record_end]),
                "header_hex": data[
                    record_start : record_start + FIXED_HEADER_SIZE
                ].hex(),
                "selection_fields": fixed_record_fields(data, record_start),
                "glyph_summary": glyph_summary,
                "glyph_slots": slots,
            }
            record_address = mapped_address(base_address, record_start)
            if record_address is not None:
                output_record["record_address"] = record_address
                output_record["context_longword"] = record_address
            output_records.append(output_record)

            total_slots += int(glyph_summary["emitted_slots"])
            total_glyphs += int(glyph_summary["extracted_glyphs"])
            total_absent += int(glyph_summary["absent_glyphs"])
            total_payload_bytes += int(glyph_summary["payload_bytes"])
            for layout, count in dict(
                glyph_summary["payload_layouts"]
            ).items():
                total_layouts[str(layout)] = total_layouts.get(
                    str(layout), 0
                ) + int(count)

        output_banks.append(
            {
                "bank_index": bank_index,
                "bank_offset": bank_start,
                "bank_size": int(bank["bank_size"]),
                "record_count": len(bank_record_indexes),
                "record_indexes": bank_record_indexes,
                "terminal_record_offset": int(
                    bank["terminal_record_offset"]
                ),
                "terminator_offset": int(bank["terminator_offset"]),
                "scan_status": str(bank["scan_status"]),
            }
        )

    return {
        "schema": SCHEMA,
        "resource_format": "fixed-FONT-chain",
        "label": label,
        "source": {
            "path": str(source_path),
            "size_bytes": len(data),
            "sha256": sha256(data),
        },
        "mapping": {
            "address_mode": (
                "mapped" if base_address is not None else "rom-relative"
            ),
            "base_address": base_address,
        },
        "resource_chain": {
            "bank_size": FIXED_BANK_SIZE,
            "bank_count": len(banks),
            "record_count": len(output_records),
            "banks": output_banks,
        },
        "summary": {
            "records": len(output_records),
            "glyph_slots": total_slots,
            "extracted_glyphs": total_glyphs,
            "absent_glyphs": total_absent,
            "no_normal_payload_glyphs": 0,
            "payload_bytes": total_payload_bytes,
            "payload_layouts": total_layouts,
        },
        "records": output_records,
    }


def build_asset(
    source_path: Path,
    data: bytes,
    label: str,
    base_address: int | None,
) -> dict[str, Any]:
    if data.startswith(b"FONT"):
        return build_fixed_font_asset(
            source_path, data, label, base_address
        )
    return build_head_asset(source_path, data, label, base_address)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extract HEAD/type-0x14 or fixed FONT-chain LaserJet resources "
            "into a versioned JSON asset with descriptor fields and exact "
            "bitmap payloads."
        )
    )
    parser.add_argument("input", type=Path, help="logical resource ROM image")
    parser.add_argument("--output", "-o", type=Path, required=True)
    parser.add_argument(
        "--label",
        help="asset label; defaults to the input filename stem",
    )
    parser.add_argument(
        "--base-address",
        type=parse_int,
        help=(
            "optional mapped address such as 0x200000 or 0x400000; omit to "
            "keep the asset slot-independent and ROM-relative"
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = args.input
    data = source.read_bytes()
    asset = build_asset(
        source,
        data,
        args.label or args.input.stem,
        args.base_address,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(asset, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = asset["summary"]
    print(
        f"extracted {summary['records']} records, "
        f"{summary['glyph_slots']} slots, "
        f"{summary['extracted_glyphs']} glyphs, "
        f"{summary['payload_bytes']} payload bytes -> {args.output}"
    )


if __name__ == "__main__":
    main()
