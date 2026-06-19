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


def s16(data: bytes, offset: int) -> int:
    value = u16(data, offset)
    return value - 0x10000 if value & 0x8000 else value


def s8(value: int) -> int:
    value &= 0xFF
    return value - 0x100 if value & 0x80 else value


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


def glyph_bitmap_rows(resources: bytes, glyph: dict[str, int | bytes]) -> list[str]:
    mode = int(glyph["mode"])
    if mode != 1:
        raise AssertionError(f"mode {mode} glyph bitmap decoder is not implemented")
    bitmap = int(glyph["bitmap"])
    rows = int(glyph["rows"])
    width = int(glyph["width"])
    render_span = int(glyph["render_span"])
    bitmap_bytes = resources[bitmap : bitmap + rows * render_span]
    return bitmap_bytes_to_rows(bitmap_bytes, rows, width, render_span)


def built_in_base_map(resources: bytes, context: int, host_char: int) -> dict[str, int]:
    if not (context & 0x40000000):
        raise AssertionError(f"context 0x{context:08x} does not select the built-in offset-table form")
    base = (context & 0x00FFFFFF) - 0x80000
    first_char = u16(resources, base + 0x0E)
    last_char = u16(resources, base + 0x10)
    mapped = host_char - first_char if first_char <= host_char <= last_char else 0
    return {
        "base": base,
        "first_char": first_char,
        "last_char": last_char,
        "host_char": host_char,
        "mapped": mapped & 0xFF,
    }


def build_text_source_object_from_1393a(resources: bytes, context: int, host_char: int, x: int, y: int, context_slot: int = 0) -> dict[str, int]:
    mapping = built_in_base_map(resources, context, host_char)
    glyph = resolve_builtin_glyph(resources, context, mapping["mapped"])
    return {
        "context": context,
        "host_char": host_char,
        "mapped": mapping["mapped"],
        "glyph_entry": int(glyph["entry"]),
        "glyph_width": int(glyph["width"]),
        "glyph_rows": int(glyph["rows"]),
        "flag": 1,
        "x": x,
        "y": y,
        "context_slot": context_slot & 0x0F,
    }


def scanned_builtin_record_bases(resources: bytes) -> list[int]:
    bases: list[int] = []
    cursor = 0
    seen = 0
    while cursor + 12 <= len(resources) and seen < 256:
        marker = u32(resources, cursor)
        if marker == 0x48454144:  # HEAD
            length = u32(resources, cursor + 4)
            if length <= 0:
                break
            cursor += length
            seen += 1
            continue
        if marker in (0x00000014, 0x00000015):
            length = u32(resources, cursor + 4)
            if length <= 0:
                break
            bases.append(cursor)
            cursor += length
            seen += 1
            continue
        break
    return bases


def tall_builtin_glyph_targets(resources: bytes) -> list[dict[str, int]]:
    targets: list[dict[str, int]] = []
    for base in scanned_builtin_record_bases(resources):
        first_char = u16(resources, base + 0x0E)
        last_char = u16(resources, base + 0x10)
        table = base + u16(resources, base + 8)
        for glyph_index in range(last_char - first_char + 1):
            entry = base + u32(resources, table + glyph_index * 4)
            delta = resources[entry + 4]
            mode = resources[entry + 5]
            rows = u16(resources, entry + 6)
            width = u16(resources, entry + 8)
            if rows > 0x80:
                targets.append({
                    "base": base,
                    "glyph": glyph_index,
                    "entry": entry,
                    "delta": delta,
                    "mode": mode,
                    "rows": rows,
                    "width": width,
                })
    return targets


def bitmap_bytes_to_rows(bitmap: bytes | bytearray, rows: int, width: int, stride: int) -> list[str]:
    out: list[str] = []
    for row_index in range(rows):
        row = bitmap[row_index * stride : (row_index + 1) * stride]
        bits = "".join("#" if (byte >> (7 - bit)) & 1 else "." for byte in row for bit in range(8))
        out.append(bits[:width])
    return out


def render_glyph_rows_via_main_row_copy(data: bytes, resources: bytes, glyph: dict[str, int | bytes], dest_stride: int = 0x20) -> list[str]:
    mode = int(glyph["mode"])
    if mode != 1:
        raise AssertionError(f"mode {mode} row-copy renderer is not implemented")
    rows = int(glyph["rows"])
    width = int(glyph["width"])
    render_span = int(glyph["render_span"])
    if render_span < 1 or render_span > 16:
        raise AssertionError(f"main row-copy table cannot render span {render_span}")
    if render_span & 1 and render_span != 1:
        raise AssertionError("odd multi-byte spans need the A3 trailing-byte fixture before rendering")

    bitmap = int(glyph["bitmap"])
    source = resources[bitmap : bitmap + rows * render_span]
    dest = bytearray(rows * dest_stride)
    result = simulate_row_copy(data, u32(data, 0x1F08E + render_span * 4), rows, stride=dest_stride)
    for write in result.writes:
        if write.source != "A2":
            raise AssertionError(f"unexpected {write.source} write for mode-1 glyph row-copy")
        if write.src + write.size > len(source):
            raise AssertionError(f"source read past glyph bitmap at +0x{write.src:x}")
        if write.dst + write.size > len(dest):
            raise AssertionError(f"destination write past fixture buffer at +0x{write.dst:x}")
        dest[write.dst : write.dst + write.size] = source[write.src : write.src + write.size]
    return bitmap_bytes_to_rows(dest, rows, width, dest_stride)


def render_compact_mode0_payload(data: bytes, resources: bytes, context: int, payload: bytes, dest_stride: int = 0x20, band_rows: int = 64) -> dict[str, object]:
    count = u16(payload, 0)
    pos = 2
    rendered: list[dict[str, int]] = []
    dest = bytearray(band_rows * dest_stride)
    max_width = 0
    max_bottom = 0
    for _ in range(count):
        glyph_index = payload[pos]
        coord = u16(payload, pos + 1)
        pos += 3
        subbyte = (coord >> 8) & 0x0F
        if subbyte:
            raise AssertionError("compact mode-0 fixture does not implement sub-byte phase yet")
        glyph = resolve_builtin_glyph(resources, context, glyph_index)
        rows = int(glyph["rows"])
        width = int(glyph["width"])
        render_span = int(glyph["render_span"])
        if (coord >> 12) + rows > band_rows:
            raise AssertionError("compact mode-0 fixture does not implement band-crossing continuation yet")
        source = resources[int(glyph["bitmap"]) : int(glyph["bitmap"]) + rows * render_span]
        dest_base = ((coord >> 12) & 0x0F) * dest_stride + (coord & 0x00FF) * 2
        result = simulate_row_copy(data, u32(data, 0x1F08E + render_span * 4), rows, stride=dest_stride)
        for write in result.writes:
            if write.source != "A2":
                raise AssertionError(f"unexpected {write.source} write for compact mode-0 glyph")
            start = dest_base + write.dst
            dest[start : start + write.size] = source[write.src : write.src + write.size]
        rendered.append({
            "glyph": glyph_index,
            "coord": coord,
            "dest_base": dest_base,
            "span": render_span,
            "rows": rows,
            "width": width,
            "helper": u32(data, 0x1F08E + render_span * 4),
        })
        max_width = max(max_width, (coord & 0x00FF) * 16 + width)
        max_bottom = max(max_bottom, ((coord >> 12) & 0x0F) + rows)
    return {
        "count": count,
        "rendered": rendered,
        "rows": bitmap_bytes_to_rows(dest, max_bottom, max_width, dest_stride),
    }


def compact_text_coord(x: int, y: int) -> int:
    return ((y & 0x0F) << 12) | ((x & 0x0F) << 8) | ((x >> 4) & 0x00FF)


def pack12(whole: int, frac: int = 0) -> int:
    if not 0 <= frac < 12:
        raise AssertionError(f"packed 12-subunit fraction out of range: {frac}")
    return ((whole & 0xFFFF) << 16) | (frac & 0xFFFF)


def unpack12(value: int) -> tuple[int, int]:
    whole = (value >> 16) & 0xFFFF
    if whole & 0x8000:
        whole -= 0x10000
    frac = value & 0xFFFF
    if frac & 0x8000:
        frac -= 0x10000
    return whole, frac


def packed12_to_subunits(value: int) -> int:
    whole, frac = unpack12(value)
    return whole * 12 + frac


def subunits_to_packed12(value: int) -> int:
    whole, frac = divmod(value, 12)
    return pack12(whole, frac)


def add_packed12(left: int, right: int) -> int:
    return subunits_to_packed12(packed12_to_subunits(left) + packed12_to_subunits(right))


def sub_packed12(left: int, right: int) -> int:
    return subunits_to_packed12(packed12_to_subunits(left) - packed12_to_subunits(right))


def line_termination_mode_bits(parameter: int) -> int:
    value = abs(int(parameter))
    if value == 0:
        return 0x00
    if value == 1:
        return 0x80
    if value == 2:
        return 0x60
    if value == 3:
        return 0xE0
    raise AssertionError("ESC &k#G fixture only models accepted values 0..3")


def control_fixture_state(**overrides: int) -> dict[str, int]:
    state = {
        "cursor_x": pack12(10),
        "cursor_y": pack12(20),
        "left_margin": pack12(5),
        "right_limit": pack12(100),
        "page_width": 120,
        "hmi": pack12(2),
        "vmi": pack12(3),
        "pending_width": 1,
        "right_limit_latch": 1,
        "pending_text": 1,
        "line_termination": 0,
        "span_flush_enable": 0,
        "alternate_metrics": 0,
        "previous_width_word": 0,
        "page_roots": 0,
        "page_finalizes": 0,
        "span_flushes": 0,
        "post_flushes": 0,
        "span_updates": 0,
    }
    state.update(overrides)
    return state


def control_cr_helper(state: dict[str, int]) -> None:
    state["cursor_x"] = state["left_margin"]
    state["right_limit_latch"] = 0
    state["pending_text"] = 0


def control_text_flush_helper(state: dict[str, int]) -> None:
    state["pending_width"] = 0
    if state["span_flush_enable"]:
        state["span_flushes"] += 1
        state["post_flushes"] += 1


def control_lf_helper(state: dict[str, int]) -> None:
    state["page_roots"] += 1
    state["cursor_y"] = add_packed12(state["cursor_y"], state["vmi"])
    state["pending_text"] = 0


def control_ff_helper(state: dict[str, int]) -> None:
    state["page_finalizes"] += 1
    state["pending_text"] = 0


def control_span_update(state: dict[str, int]) -> None:
    state["span_updates"] += 1


def apply_direct_control_code(state: dict[str, int], code: int) -> dict[str, int]:
    state = dict(state)
    if code == 0x0D:  # CR
        control_cr_helper(state)
        control_text_flush_helper(state)
        if state["line_termination"] & 0x80:
            control_lf_helper(state)
    elif code == 0x0A:  # LF
        if state["line_termination"] & 0x40:
            control_cr_helper(state)
        control_text_flush_helper(state)
        control_lf_helper(state)
    elif code == 0x0C:  # FF
        if state["line_termination"] & 0x20:
            control_cr_helper(state)
        control_text_flush_helper(state)
        state["page_roots"] += 1
        control_ff_helper(state)
        state["pending_text"] = 0xFF
    elif code == 0x09:  # HT
        hmi_subunits = packed12_to_subunits(state["hmi"])
        if hmi_subunits == 0:
            return state
        if state["cursor_x"] < state["left_margin"]:
            next_cursor = state["left_margin"]
        else:
            distance = packed12_to_subunits(sub_packed12(state["cursor_x"], state["left_margin"]))
            tab_index = ((distance // hmi_subunits) & ~0x07) + 8
            next_cursor = add_packed12(state["left_margin"], subunits_to_packed12(tab_index * hmi_subunits))
        limit = pack12(state["page_width"]) if state["cursor_x"] > state["right_limit"] else state["right_limit"]
        if next_cursor > limit:
            next_cursor = limit
        state["cursor_x"] = next_cursor
        state["right_limit_latch"] = 1 if next_cursor == state["right_limit"] else 0
        state["pending_text"] = 0
        control_span_update(state)
    elif code == 0x08:  # BS
        amount = pack12(state["previous_width_word"]) if state["alternate_metrics"] else state["hmi"]
        next_cursor = sub_packed12(state["cursor_x"], amount)
        next_subunits = packed12_to_subunits(next_cursor)
        left_subunits = packed12_to_subunits(state["left_margin"])
        if state["cursor_x"] >= state["left_margin"] and next_subunits < left_subunits:
            next_cursor = state["left_margin"]
        if next_subunits < 0:
            next_cursor = 0
        state["cursor_x"] = next_cursor
        state["pending_width"] = 1
        state["right_limit_latch"] = 0
        state["pending_text"] = 0
        control_span_update(state)
    else:
        raise AssertionError(f"unsupported direct control fixture byte 0x{code:02x}")
    return state


def reset_fixture_state(**overrides: int) -> dict[str, int]:
    state = {
        "environment_gate": 0,
        "alternate_mode": 1,
        "alternate_parser_byte": 1,
        "orientation": 1,
        "vertical_offset_source": 60,
        "top_offset": 0,
        "vertical_offset_word": 7,
        "raster_active": 1,
        "raster_origin": 33,
        "raster_baseline": 44,
        "raster_scale_minus_one": 0,
        "raster_scale": 0,
        "raster_limit": 0,
        "page_extent": 3180,
        "font_context_flag": 0,
        "font_metric_flag_clear": 0x12,
        "font_metric_flag_set": 0x34,
        "font_hmi_clear": pack12(1),
        "font_hmi_set": pack12(2),
        "active_primary_symbol": 0x0115,
        "active_secondary_symbol": 0x0125,
        "glyph_map_selector": 1,
        "primary_symbol_snapshot": 0,
        "secondary_symbol_snapshot": 0,
        "alternate_metrics": 0,
        "hmi": 0,
        "data_chain_ptr": 0,
        "current_object_ptr": 0x123456,
        "parser_selector": 0x55,
        "page_parser_state": 1,
        "text_accum0": 1,
        "text_accum1": 2,
        "text_accum2": 3,
        "text_accum3": 4,
        "parser_record_cursor": 0,
        "parser_records_cleared": 0,
        "data_chain_records_freed": 0,
        "pool_records_pruned": 0,
        "reset_status": 0xff,
        "span_flush_enable": 1,
        "pending_width": 1,
        "span_flushes": 0,
        "post_flushes": 0,
        "active_record_waits": 0,
        "page_root_present": 1,
        "page_root_class": 1,
        "page_root_flags": 0,
        "page_publications": 0,
        "page_root_clears": 0,
        "current_page_root": 1,
        "published_pool_record": 0,
        "page_publication_flag": 0,
        "transient_page_byte": 1,
        "cursor_transient_a": 1,
        "cursor_transient_b": 1,
    }
    state.update(overrides)
    return state


def apply_esc_e_reset(state: dict[str, int]) -> dict[str, int]:
    state = dict(state)
    if state["environment_gate"] == 0:
        state["alternate_mode"] = 0

    control_text_flush_helper(state)
    state["active_record_waits"] += 1

    if not state["page_root_present"] or state["page_root_class"] != 1:
        state["current_page_root"] = 0
        state["page_root_clears"] += 1
    else:
        state["transient_page_byte"] = 0
        state["cursor_transient_a"] = 0
        state["cursor_transient_b"] = 0
        state["page_publications"] += 1
        state["published_pool_record"] = 1
        state["page_publication_flag"] = 1
        state["current_page_root"] = 0
        state["page_root_clears"] += 1

    state["orientation"] = 0
    state["top_offset"] = 0x96 - state["vertical_offset_source"]
    state["vertical_offset_word"] = 0
    state["raster_active"] = 0
    state["raster_origin"] = 0
    state["raster_baseline"] = 0
    state["raster_scale_minus_one"] = 3
    state["raster_scale"] = 4
    raster_denominator = state["raster_scale"] << 3
    state["raster_limit"] = ((state["page_extent"] - state["raster_origin"]) + 1 + raster_denominator - 1) // raster_denominator

    state["glyph_map_selector"] = 0
    if state["font_context_flag"]:
        state["alternate_metrics"] = state["font_metric_flag_set"]
        state["hmi"] = state["font_hmi_set"]
    else:
        state["alternate_metrics"] = state["font_metric_flag_clear"]
        state["hmi"] = state["font_hmi_clear"]
    state["primary_symbol_snapshot"] = state["active_primary_symbol"]
    state["secondary_symbol_snapshot"] = state["active_secondary_symbol"]

    state["data_chain_ptr"] = 0x782D3E
    state["data_chain_records_freed"] += 1
    state["current_object_ptr"] = 0
    state["parser_selector"] = 0
    state["alternate_mode"] = 0
    state["alternate_parser_byte"] = 0
    state["page_parser_state"] = 0
    state["text_accum0"] = 0
    state["text_accum1"] = 0
    state["text_accum2"] = 0
    state["text_accum3"] = 0
    state["parser_record_cursor"] = 0x782C1E
    state["parser_records_cleared"] = 8
    state["pool_records_pruned"] += 1
    state["reset_status"] = 0
    return state


def apply_direct_control_stream(state: dict[str, int], stream: bytes) -> dict[str, int]:
    state = dict(state)
    pos = 0
    while pos < len(stream):
        byte = stream[pos]
        if byte == 0x1B:
            if pos + 1 < len(stream) and stream[pos + 1] == ord("E"):
                state = apply_esc_e_reset(state)
                pos += 2
                continue
            if pos + 3 >= len(stream) or stream[pos + 1 : pos + 3] != b"&k":
                raise AssertionError(f"unsupported ESC sequence at stream offset {pos}")
            pos += 3
            sign = 1
            if pos < len(stream) and stream[pos] in (ord("+"), ord("-")):
                sign = -1 if stream[pos] == ord("-") else 1
                pos += 1
            if pos >= len(stream) or not chr(stream[pos]).isdigit():
                raise AssertionError("ESC &k#G fixture requires an integer parameter")
            value = 0
            while pos < len(stream) and chr(stream[pos]).isdigit():
                value = value * 10 + stream[pos] - ord("0")
                pos += 1
            if pos >= len(stream) or stream[pos] != ord("G"):
                raise AssertionError("ESC &k#G fixture only models final byte G")
            state["line_termination"] = line_termination_mode_bits(sign * value)
            pos += 1
            continue
        if byte in (0x08, 0x09, 0x0A, 0x0C, 0x0D):
            state = apply_direct_control_code(state, byte)
            pos += 1
            continue
        raise AssertionError(f"unsupported direct control stream byte 0x{byte:02x} at offset {pos}")
    return state


def position_flagged_text_source_via_d824(
    resources: bytes,
    source: dict[str, int],
    cursor_x: int,
    cursor_y: int,
    printable_offset: int = 0,
    orientation: int = 0,
    orientation_extent: int = 0,
    source_x_offset: int = 0,
) -> dict[str, object]:
    d5 = int(cursor_x)
    d7 = d5 + int(source_x_offset)
    overflow_correction = d7
    if d7 < 0:
        overflow_correction = (-d7) << 16
        d5 = -int(source_x_offset)
    else:
        overflow_correction = 0

    if orientation == 0:
        d4 = int(cursor_y)
    else:
        d4 = int(orientation_extent) - d5
        d5 = int(cursor_y)

    glyph_entry = source["glyph_entry"]
    d5 = d5 + int(printable_offset) + s16(resources, glyph_entry)
    d4 = d4 - s16(resources, glyph_entry + 2)

    positioned = dict(source)
    positioned["x"] = d5
    positioned["y"] = d4
    positioned["context_slot"] = source["context_slot"] & 0x0F
    return {
        "source": positioned,
        "overflow_correction": overflow_correction,
        "glyph_x_offset": s16(resources, glyph_entry),
        "glyph_y_offset": s16(resources, glyph_entry + 2),
        "cursor_x": cursor_x,
        "cursor_y": cursor_y,
        "printable_offset": printable_offset,
        "orientation": orientation,
        "orientation_extent": orientation_extent,
        "source_x_offset": source_x_offset,
    }


def position_unflagged_text_source_via_d3b2(
    source: dict[str, int],
    inline_record: bytes,
    cursor_x: int,
    cursor_y: int,
    printable_offset: int = 0,
    orientation: int = 0,
    orientation_extent: int = 0,
    context_metric_flag: int = 0,
    source_x_offset: int = 0,
) -> dict[str, object]:
    if len(inline_record) < 3:
        raise AssertionError("inline source record fixture needs at least three bytes")
    d5 = int(cursor_x) + int(source_x_offset)
    if d5 < 0:
        overflow_correction = (-d5) << 16
        d5 = 0
    else:
        overflow_correction = 0

    if orientation == 0:
        d4 = int(cursor_y)
    else:
        d4 = int(orientation_extent) - d5
        d5 = int(cursor_y)

    d5 += int(printable_offset)
    if context_metric_flag:
        d4 -= inline_record[1] - 1
        d5 += s8(inline_record[2]) + 1 - (inline_record[0] << 3)
    else:
        d4 += s8(inline_record[2]) + 1 - inline_record[1]

    positioned = dict(source)
    positioned["x"] = d5
    positioned["y"] = d4
    positioned["context_slot"] = source["context_slot"] & 0x0F
    return {
        "source": positioned,
        "overflow_correction": overflow_correction,
        "record0": inline_record[0],
        "record1": inline_record[1],
        "record2_signed": s8(inline_record[2]),
        "cursor_x": cursor_x,
        "cursor_y": cursor_y,
        "printable_offset": printable_offset,
        "orientation": orientation,
        "orientation_extent": orientation_extent,
        "context_metric_flag": context_metric_flag,
        "source_x_offset": source_x_offset,
    }


def queue_text_source_via_12f2e(resources: bytes, source: dict[str, int]) -> dict[str, object]:
    if source["flag"] == 0:
        raise AssertionError("inline/downloaded text source records are not implemented")
    selector = source["context_slot"] & 0x0F
    glyph_entry = source["glyph_entry"]
    width = u16(resources, glyph_entry + 8)
    rows = u16(resources, glyph_entry + 6)
    if width > 0x80:
        selector |= 0x1000
    if rows > 0x80:
        selector |= 0x2000
        segment = (rows - 1) >> 7
        objects: list[dict[str, int | bytes]] = []
        while segment >= 0:
            obj = bytearray(0x0C)
            obj[4:6] = selector.to_bytes(2, "big")
            obj[6:8] = (1).to_bytes(2, "big")
            obj[8] = source["mapped"] & 0xFF
            obj[9] = segment & 0xFF
            obj[10:12] = compact_text_coord(source["x"], source["y"]).to_bytes(2, "big")
            objects.append({
                "bucket_index": (source["y"] >> 4) + segment * 8,
                "segment": segment,
                "object": bytes(obj),
            })
            segment -= 1
        return {
            "path": "segmented",
            "objects": objects,
            "object_size": 0x28,
            "capacity": 0x08,
            "entry_size": 4,
            "selector": selector,
            "coord": compact_text_coord(source["x"], source["y"]),
            "glyph": source["mapped"] & 0xFF,
            "rows": rows,
            "width": width,
        }
    obj = bytearray(0x0B)
    obj[4:6] = selector.to_bytes(2, "big")
    obj[6:8] = (1).to_bytes(2, "big")
    obj[8] = source["mapped"] & 0xFF
    obj[9:11] = compact_text_coord(source["x"], source["y"]).to_bytes(2, "big")
    return {
        "path": "short",
        "object": bytes(obj),
        "object_size": 0x26,
        "capacity": 0x0A,
        "entry_size": 3,
        "bucket_index": source["y"] >> 4,
        "selector": selector,
        "coord": compact_text_coord(source["x"], source["y"]),
        "glyph": source["mapped"] & 0xFF,
        "rows": rows,
        "width": width,
    }


def render_compact_text_bucket_object(data: bytes, resources: bytes, contexts: tuple[int, ...], obj: bytes) -> dict[str, object]:
    selector = obj[4]
    context_slot = obj[5] & 0x0F
    if selector & 0x30:
        raise AssertionError("compact text bucket fixture only implements mode 0")
    if context_slot >= len(contexts):
        raise AssertionError(f"context slot {context_slot} is not available")
    payload = obj[6:]
    rendered = render_compact_mode0_payload(data, resources, contexts[context_slot], payload)
    rendered["selector"] = u16(obj, 4)
    rendered["context_slot"] = context_slot
    rendered["payload"] = payload
    return rendered


def render_single_printable_stream(
    data: bytes,
    resources: bytes,
    stream: bytes,
    context: int,
    cursor_x: int,
    cursor_y: int,
    context_slot: int = 0,
) -> dict[str, object]:
    if len(stream) != 1 or stream[0] < 0x20 or stream[0] == 0x7F:
        raise AssertionError("printable stream fixture currently models exactly one normal printable byte")
    source = build_text_source_object_from_1393a(resources, context, stream[0], x=0, y=0, context_slot=context_slot)
    positioned = position_flagged_text_source_via_d824(resources, source, cursor_x=cursor_x, cursor_y=cursor_y)
    positioned_source = positioned["source"]
    assert isinstance(positioned_source, dict)
    bucket = queue_text_source_via_12f2e(resources, positioned_source)
    obj = bucket["object"]
    if not isinstance(obj, bytes):
        raise AssertionError("printable stream fixture only models short compact text objects")
    rendered = render_compact_text_bucket_object(data, resources, (context,), obj)
    return {
        "stream": stream,
        "source": source,
        "positioned": positioned,
        "bucket": bucket,
        "rendered": rendered,
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


def select_keys(values: dict[str, int], keys: tuple[str, ...]) -> dict[str, int]:
    return {key: values[key] for key in keys}


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

    checks.append(assert_equal("ESC &k#G line termination mode bits", {value: line_termination_mode_bits(value) for value in range(4)}, {0: 0x00, 1: 0x80, 2: 0x60, 3: 0xE0}))
    control_fields = ("cursor_x", "cursor_y", "pending_width", "right_limit_latch", "pending_text", "page_roots", "page_finalizes", "span_flushes", "post_flushes", "span_updates")
    cr_default = apply_direct_control_code(control_fixture_state(
        cursor_x=pack12(42, 3),
        cursor_y=pack12(20),
        left_margin=pack12(7, 2),
        pending_width=1,
        right_limit_latch=1,
        pending_text=1,
        line_termination=0x00,
        span_flush_enable=1,
    ), 0x0D)
    checks.append(assert_equal("CR resets horizontal cursor and flushes pending text span", select_keys(cr_default, control_fields), {
        "cursor_x": pack12(7, 2),
        "cursor_y": pack12(20),
        "pending_width": 0,
        "right_limit_latch": 0,
        "pending_text": 0,
        "page_roots": 0,
        "page_finalizes": 0,
        "span_flushes": 1,
        "post_flushes": 1,
        "span_updates": 0,
    }))
    cr_lf = apply_direct_control_code(control_fixture_state(
        cursor_x=pack12(42),
        cursor_y=pack12(20, 11),
        left_margin=pack12(7),
        vmi=pack12(0, 2),
        line_termination=0x80,
    ), 0x0D)
    checks.append(assert_equal("CR line-termination mode 1 also advances vertical cursor", select_keys(cr_lf, control_fields), {
        "cursor_x": pack12(7),
        "cursor_y": pack12(21, 1),
        "pending_width": 0,
        "right_limit_latch": 0,
        "pending_text": 0,
        "page_roots": 1,
        "page_finalizes": 0,
        "span_flushes": 0,
        "post_flushes": 0,
        "span_updates": 0,
    }))
    lf_mode2 = apply_direct_control_code(control_fixture_state(
        cursor_x=pack12(42),
        cursor_y=pack12(10),
        left_margin=pack12(6),
        vmi=pack12(1),
        pending_width=1,
        right_limit_latch=1,
        pending_text=1,
        line_termination=0x60,
    ), 0x0A)
    checks.append(assert_equal("LF line-termination mode 2 resets horizontal cursor", select_keys(lf_mode2, control_fields), {
        "cursor_x": pack12(6),
        "cursor_y": pack12(11),
        "pending_width": 0,
        "right_limit_latch": 0,
        "pending_text": 0,
        "page_roots": 1,
        "page_finalizes": 0,
        "span_flushes": 0,
        "post_flushes": 0,
        "span_updates": 0,
    }))
    ff_mode2 = apply_direct_control_code(control_fixture_state(
        cursor_x=pack12(42),
        left_margin=pack12(6),
        pending_width=1,
        right_limit_latch=1,
        pending_text=1,
        line_termination=0x20,
        span_flush_enable=1,
    ), 0x0C)
    checks.append(assert_equal("FF line-termination mode 2 resets horizontal cursor and marks page eject", select_keys(ff_mode2, control_fields), {
        "cursor_x": pack12(6),
        "cursor_y": pack12(20),
        "pending_width": 0,
        "right_limit_latch": 0,
        "pending_text": 0xFF,
        "page_roots": 1,
        "page_finalizes": 1,
        "span_flushes": 1,
        "post_flushes": 1,
        "span_updates": 0,
    }))
    ht_next_stop = apply_direct_control_code(control_fixture_state(
        cursor_x=pack12(17),
        left_margin=pack12(5),
        hmi=pack12(1),
        right_limit=pack12(100),
        page_width=120,
        pending_text=1,
    ), 0x09)
    checks.append(assert_equal("HT advances to next eight-column stop", select_keys(ht_next_stop, control_fields), {
        "cursor_x": pack12(21),
        "cursor_y": pack12(20),
        "pending_width": 1,
        "right_limit_latch": 0,
        "pending_text": 0,
        "page_roots": 0,
        "page_finalizes": 0,
        "span_flushes": 0,
        "post_flushes": 0,
        "span_updates": 1,
    }))
    ht_clamp = apply_direct_control_code(control_fixture_state(
        cursor_x=pack12(110),
        left_margin=pack12(0),
        hmi=pack12(1),
        right_limit=pack12(100),
        page_width=90,
        pending_text=1,
    ), 0x09)
    checks.append(assert_equal("HT clamps to page width when already beyond right limit", select_keys(ht_clamp, control_fields), {
        "cursor_x": pack12(90),
        "cursor_y": pack12(20),
        "pending_width": 1,
        "right_limit_latch": 0,
        "pending_text": 0,
        "page_roots": 0,
        "page_finalizes": 0,
        "span_flushes": 0,
        "post_flushes": 0,
        "span_updates": 1,
    }))
    bs_default = apply_direct_control_code(control_fixture_state(
        cursor_x=pack12(20),
        left_margin=pack12(5),
        hmi=pack12(2),
        pending_text=1,
        right_limit_latch=1,
    ), 0x08)
    checks.append(assert_equal("BS subtracts HMI and sets pending previous-width latch", select_keys(bs_default, control_fields), {
        "cursor_x": pack12(18),
        "cursor_y": pack12(20),
        "pending_width": 1,
        "right_limit_latch": 0,
        "pending_text": 0,
        "page_roots": 0,
        "page_finalizes": 0,
        "span_flushes": 0,
        "post_flushes": 0,
        "span_updates": 1,
    }))
    bs_left_clamp = apply_direct_control_code(control_fixture_state(
        cursor_x=pack12(6),
        left_margin=pack12(5),
        hmi=pack12(3),
    ), 0x08)
    checks.append(assert_equal("BS clamps at left margin when crossing it", select_keys(bs_left_clamp, control_fields), {
        "cursor_x": pack12(5),
        "cursor_y": pack12(20),
        "pending_width": 1,
        "right_limit_latch": 0,
        "pending_text": 0,
        "page_roots": 0,
        "page_finalizes": 0,
        "span_flushes": 0,
        "post_flushes": 0,
        "span_updates": 1,
    }))
    bs_previous_width = apply_direct_control_code(control_fixture_state(
        cursor_x=pack12(30),
        left_margin=pack12(5),
        hmi=pack12(2),
        alternate_metrics=1,
        previous_width_word=4,
    ), 0x08)
    checks.append(assert_equal("BS alternate metrics subtracts previous width word", select_keys(bs_previous_width, control_fields), {
        "cursor_x": pack12(26),
        "cursor_y": pack12(20),
        "pending_width": 1,
        "right_limit_latch": 0,
        "pending_text": 0,
        "page_roots": 0,
        "page_finalizes": 0,
        "span_flushes": 0,
        "post_flushes": 0,
        "span_updates": 1,
    }))
    control_stream_fields = control_fields + ("line_termination",)
    stream_cr_lf = apply_direct_control_stream(control_fixture_state(
        cursor_x=pack12(42),
        cursor_y=pack12(20, 11),
        left_margin=pack12(7),
        vmi=pack12(0, 2),
    ), b"\x1b&k1G\r")
    checks.append(assert_equal("control stream ESC &k1G then CR applies CR+LF", select_keys(stream_cr_lf, control_stream_fields), {
        "cursor_x": pack12(7),
        "cursor_y": pack12(21, 1),
        "pending_width": 0,
        "right_limit_latch": 0,
        "pending_text": 0,
        "page_roots": 1,
        "page_finalizes": 0,
        "span_flushes": 0,
        "post_flushes": 0,
        "span_updates": 0,
        "line_termination": 0x80,
    }))
    stream_lf = apply_direct_control_stream(control_fixture_state(
        cursor_x=pack12(42),
        cursor_y=pack12(10),
        left_margin=pack12(6),
        vmi=pack12(1),
        pending_width=1,
        right_limit_latch=1,
        pending_text=1,
    ), b"\x1b&k2G\n")
    checks.append(assert_equal("control stream ESC &k2G then LF applies CR+LF", select_keys(stream_lf, control_stream_fields), {
        "cursor_x": pack12(6),
        "cursor_y": pack12(11),
        "pending_width": 0,
        "right_limit_latch": 0,
        "pending_text": 0,
        "page_roots": 1,
        "page_finalizes": 0,
        "span_flushes": 0,
        "post_flushes": 0,
        "span_updates": 0,
        "line_termination": 0x60,
    }))
    stream_ht_bs = apply_direct_control_stream(control_fixture_state(
        cursor_x=pack12(17),
        left_margin=pack12(5),
        hmi=pack12(1),
        right_limit=pack12(100),
        page_width=120,
        pending_text=1,
    ), b"\x1b&k0G\t\b")
    checks.append(assert_equal("control stream HT then BS updates tab and previous-width state", select_keys(stream_ht_bs, control_stream_fields), {
        "cursor_x": pack12(20),
        "cursor_y": pack12(20),
        "pending_width": 1,
        "right_limit_latch": 0,
        "pending_text": 0,
        "page_roots": 0,
        "page_finalizes": 0,
        "span_flushes": 0,
        "post_flushes": 0,
        "span_updates": 2,
        "line_termination": 0x00,
    }))
    reset_fields = (
        "alternate_mode",
        "alternate_parser_byte",
        "orientation",
        "top_offset",
        "vertical_offset_word",
        "raster_active",
        "raster_origin",
        "raster_baseline",
        "raster_scale_minus_one",
        "raster_scale",
        "raster_limit",
        "glyph_map_selector",
        "alternate_metrics",
        "hmi",
        "primary_symbol_snapshot",
        "secondary_symbol_snapshot",
        "data_chain_ptr",
        "current_object_ptr",
        "parser_selector",
        "page_parser_state",
        "text_accum0",
        "text_accum1",
        "text_accum2",
        "text_accum3",
        "parser_record_cursor",
        "parser_records_cleared",
        "data_chain_records_freed",
        "pool_records_pruned",
        "reset_status",
        "pending_width",
        "span_flushes",
        "post_flushes",
        "active_record_waits",
        "current_page_root",
        "page_publications",
        "page_root_clears",
        "published_pool_record",
        "page_publication_flag",
        "transient_page_byte",
        "cursor_transient_a",
        "cursor_transient_b",
    )
    reset_valid_page = apply_direct_control_stream(reset_fixture_state(
        vertical_offset_source=50,
        page_extent=3180,
        font_context_flag=0,
        font_metric_flag_clear=0x12,
        font_hmi_clear=pack12(1, 6),
        active_primary_symbol=0x0115,
        active_secondary_symbol=0x0125,
        page_root_present=1,
        page_root_class=1,
        span_flush_enable=1,
    ), b"\x1bE")
    checks.append(assert_equal("ESC E stream publishes valid page root and resets environment/parser state", select_keys(reset_valid_page, reset_fields), {
        "alternate_mode": 0,
        "alternate_parser_byte": 0,
        "orientation": 0,
        "top_offset": 100,
        "vertical_offset_word": 0,
        "raster_active": 0,
        "raster_origin": 0,
        "raster_baseline": 0,
        "raster_scale_minus_one": 3,
        "raster_scale": 4,
        "raster_limit": 100,
        "glyph_map_selector": 0,
        "alternate_metrics": 0x12,
        "hmi": pack12(1, 6),
        "primary_symbol_snapshot": 0x0115,
        "secondary_symbol_snapshot": 0x0125,
        "data_chain_ptr": 0x782D3E,
        "current_object_ptr": 0,
        "parser_selector": 0,
        "page_parser_state": 0,
        "text_accum0": 0,
        "text_accum1": 0,
        "text_accum2": 0,
        "text_accum3": 0,
        "parser_record_cursor": 0x782C1E,
        "parser_records_cleared": 8,
        "data_chain_records_freed": 1,
        "pool_records_pruned": 1,
        "reset_status": 0,
        "pending_width": 0,
        "span_flushes": 1,
        "post_flushes": 1,
        "active_record_waits": 1,
        "current_page_root": 0,
        "page_publications": 1,
        "page_root_clears": 1,
        "published_pool_record": 1,
        "page_publication_flag": 1,
        "transient_page_byte": 0,
        "cursor_transient_a": 0,
        "cursor_transient_b": 0,
    }))
    reset_no_page = apply_direct_control_stream(reset_fixture_state(
        environment_gate=1,
        alternate_mode=1,
        page_root_present=0,
        page_root_class=0,
        font_context_flag=1,
        font_metric_flag_set=0x34,
        font_hmi_set=pack12(2, 3),
        active_primary_symbol=0x0455,
        active_secondary_symbol=0x0555,
        span_flush_enable=0,
    ), b"\x1bE")
    checks.append(assert_equal("ESC E stream clears missing page root without publication", select_keys(reset_no_page, (
        "alternate_mode",
        "alternate_parser_byte",
        "glyph_map_selector",
        "alternate_metrics",
        "hmi",
        "primary_symbol_snapshot",
        "secondary_symbol_snapshot",
        "pending_width",
        "span_flushes",
        "post_flushes",
        "active_record_waits",
        "current_page_root",
        "page_publications",
        "page_root_clears",
        "published_pool_record",
        "page_publication_flag",
        "reset_status",
    )), {
        "alternate_mode": 0,
        "alternate_parser_byte": 0,
        "glyph_map_selector": 0,
        "alternate_metrics": 0x34,
        "hmi": pack12(2, 3),
        "primary_symbol_snapshot": 0x0455,
        "secondary_symbol_snapshot": 0x0555,
        "pending_width": 0,
        "span_flushes": 0,
        "post_flushes": 0,
        "active_record_waits": 1,
        "current_page_root": 0,
        "page_publications": 0,
        "page_root_clears": 1,
        "published_pool_record": 0,
        "page_publication_flag": 0,
        "reset_status": 0,
    }))

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
    default_glyph0_rows = glyph_bitmap_rows(resources, default_glyph0)
    checks.append(assert_equal("resource context 0x4008004c glyph 0 full bitmap rows", default_glyph0_rows, [
        "...###...",
        "..#####..",
        "..#####..",
        "..#####..",
        "..#####..",
        "..#####..",
        "..#####..",
        "..#####..",
        "..#####..",
        "...###...",
        "..#####..",
        "..#####..",
        "...###...",
        "..#####..",
        "...###...",
        "..#####..",
        "...###...",
        "...###...",
        "...###...",
        "...###...",
        "...###...",
        ".........",
        ".........",
        ".........",
        ".........",
        "..#####..",
        ".#######.",
        "#########",
        "#########",
        "#########",
        ".#######.",
        "..#####..",
    ]))
    checks.append(assert_equal("resource context 0x4008004c glyph 0 main row-copy rendered rows", render_glyph_rows_via_main_row_copy(data, resources, default_glyph0), default_glyph0_rows))

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
    courier_glyph0_rows = glyph_bitmap_rows(resources, courier_glyph0)
    checks.append(assert_equal("resource context 0x44080418 glyph 0 full bitmap rows", courier_glyph0_rows, [
        "...........######...........",
        "........############........",
        ".......####......####.......",
        ".....###............###.....",
        "....##................##....",
        "...##..................##...",
        "..##....................##..",
        "..##....................##..",
        ".##......................##.",
        ".##......................##.",
        ".##......#........#......##.",
        "##......###......###......##",
        "##.......#........#.......##",
        "##........................##",
        "##........................##",
        "##........................##",
        "##........................##",
        "##........................##",
        ".##......................##.",
        ".##.....##........##.....##.",
        ".##......##......##......##.",
        "..##......########......##..",
        "..##.......######.......##..",
        "...##..................##...",
        "....##................##....",
        ".....###............###.....",
        ".......###........###.......",
        "........############........",
        "...........######...........",
    ]))
    checks.append(assert_equal("resource context 0x44080418 glyph 0 main row-copy rendered rows", render_glyph_rows_via_main_row_copy(data, resources, courier_glyph0), courier_glyph0_rows))

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
    line_printer_glyph0_rows = glyph_bitmap_rows(resources, line_printer_glyph0)
    checks.append(assert_equal("resource context 0x440946b4 glyph 0 full bitmap rows", line_printer_glyph0_rows, [
        "......####......",
        "....########....",
        "..###......###..",
        "..##........##..",
        ".##..........##.",
        ".##..........##.",
        "##.####..####.##",
        "##..##....##..##",
        "##............##",
        "##............##",
        ".##..#....#..##.",
        ".##..######..##.",
        "..##..####..##..",
        "..###......###..",
        "....########....",
        "......####......",
    ]))
    checks.append(assert_equal("resource context 0x440946b4 glyph 0 main row-copy rendered rows", render_glyph_rows_via_main_row_copy(data, resources, line_printer_glyph0), line_printer_glyph0_rows))

    line_printer_glyph32 = resolve_builtin_glyph(resources, 0x440946B4, 32)
    checks.append(assert_equal("resource context 0x440946b4 glyph 32 fields", {key: line_printer_glyph32[key] for key in ("base", "table", "entry", "bitmap", "delta", "mode", "rows", "width", "render_span")}, {
        "base": 0x0146B4,
        "table": 0x0146FE,
        "entry": 0x015330,
        "bitmap": 0x01533A,
        "delta": 10,
        "mode": 1,
        "rows": 22,
        "width": 4,
        "render_span": 1,
    }))
    line_printer_glyph32_rows = glyph_bitmap_rows(resources, line_printer_glyph32)
    checks.append(assert_equal("resource context 0x440946b4 glyph 32 full bitmap rows", line_printer_glyph32_rows, [
        "####",
        "....",
        "####",
        "....",
        "####",
        "....",
        "####",
        "....",
        "####",
        "....",
        "####",
        "....",
        "####",
        "....",
        "####",
        "....",
        "####",
        "....",
        "####",
        "....",
        "####",
        "....",
    ]))
    checks.append(assert_equal("resource context 0x440946b4 glyph 32 main row-copy rendered rows", render_glyph_rows_via_main_row_copy(data, resources, line_printer_glyph32), line_printer_glyph32_rows))

    line_printer_mapping = built_in_base_map(resources, 0x440946B4, 0x21)
    checks.append(assert_equal("line-printer built-in base map host 0x21 to glyph 32", line_printer_mapping, {
        "base": 0x0146B4,
        "first_char": 0x01,
        "last_char": 0xFF,
        "host_char": 0x21,
        "mapped": 0x20,
    }))
    text_source = build_text_source_object_from_1393a(resources, 0x440946B4, 0x21, x=0, y=0, context_slot=0)
    checks.append(assert_equal("0x1393a-modeled text source object fields", text_source, {
        "context": 0x440946B4,
        "host_char": 0x21,
        "mapped": 0x20,
        "glyph_entry": 0x015330,
        "glyph_width": 4,
        "glyph_rows": 22,
        "flag": 1,
        "x": 0,
        "y": 0,
        "context_slot": 0,
    }))
    produced_bucket = queue_text_source_via_12f2e(resources, text_source)
    checks.append(assert_equal("0x12f2e-modeled short bucket object fields", {key: produced_bucket[key] for key in ("path", "object", "object_size", "capacity", "entry_size", "bucket_index", "selector", "coord", "glyph", "rows", "width")}, {
        "path": "short",
        "object": bytes.fromhex("00 00 00 00 00 00 00 01 20 00 00"),
        "object_size": 0x26,
        "capacity": 0x0A,
        "entry_size": 3,
        "bucket_index": 0,
        "selector": 0,
        "coord": 0,
        "glyph": 0x20,
        "rows": 22,
        "width": 4,
    }))
    positioned_fixture = position_flagged_text_source_via_d824(resources, text_source, cursor_x=10, cursor_y=21)
    checks.append(assert_equal("0xd824-modeled positioned text source fields", positioned_fixture, {
        "source": {
            "context": 0x440946B4,
            "host_char": 0x21,
            "mapped": 0x20,
            "glyph_entry": 0x015330,
            "glyph_width": 4,
            "glyph_rows": 22,
            "flag": 1,
            "x": 16,
            "y": 0,
            "context_slot": 0,
        },
        "overflow_correction": 0,
        "glyph_x_offset": 6,
        "glyph_y_offset": 21,
        "cursor_x": 10,
        "cursor_y": 21,
        "printable_offset": 0,
        "orientation": 0,
        "orientation_extent": 0,
        "source_x_offset": 0,
    }))
    positioned_source = positioned_fixture["source"]
    assert isinstance(positioned_source, dict)
    positioned_bucket = queue_text_source_via_12f2e(resources, positioned_source)
    checks.append(assert_equal("0xd824-positioned short bucket object fields", {key: positioned_bucket[key] for key in ("path", "object", "bucket_index", "selector", "coord", "glyph", "rows", "width")}, {
        "path": "short",
        "object": bytes.fromhex("00 00 00 00 00 00 00 01 20 00 01"),
        "bucket_index": 0,
        "selector": 0,
        "coord": 0x0001,
        "glyph": 0x20,
        "rows": 22,
        "width": 4,
    }))
    overflow_positioned_fixture = position_flagged_text_source_via_d824(resources, text_source, cursor_x=10, cursor_y=21, source_x_offset=-26)
    checks.append(assert_equal("0xd824-modeled negative-overflow positioned source fields", overflow_positioned_fixture, {
        "source": {
            "context": 0x440946B4,
            "host_char": 0x21,
            "mapped": 0x20,
            "glyph_entry": 0x015330,
            "glyph_width": 4,
            "glyph_rows": 22,
            "flag": 1,
            "x": 32,
            "y": 0,
            "context_slot": 0,
        },
        "overflow_correction": 0x00100000,
        "glyph_x_offset": 6,
        "glyph_y_offset": 21,
        "cursor_x": 10,
        "cursor_y": 21,
        "printable_offset": 0,
        "orientation": 0,
        "orientation_extent": 0,
        "source_x_offset": -26,
    }))
    overflow_positioned_source = overflow_positioned_fixture["source"]
    assert isinstance(overflow_positioned_source, dict)
    overflow_positioned_bucket = queue_text_source_via_12f2e(resources, overflow_positioned_source)
    checks.append(assert_equal("0xd824-negative-overflow short bucket object fields", {key: overflow_positioned_bucket[key] for key in ("path", "object", "bucket_index", "selector", "coord", "glyph", "rows", "width")}, {
        "path": "short",
        "object": bytes.fromhex("00 00 00 00 00 00 00 01 20 00 02"),
        "bucket_index": 0,
        "selector": 0,
        "coord": 0x0002,
        "glyph": 0x20,
        "rows": 22,
        "width": 4,
    }))

    inline_source = {
        "context": 0x00000000,
        "host_char": 0x41,
        "mapped": 0x01,
        "glyph_entry": 0,
        "glyph_width": 0,
        "glyph_rows": 0,
        "flag": 0,
        "x": 0,
        "y": 0,
        "context_slot": 3,
    }
    inline_record = bytes.fromhex("02 03 04")
    unflagged_fixture = position_unflagged_text_source_via_d3b2(
        inline_source,
        inline_record,
        cursor_x=10,
        cursor_y=20,
        printable_offset=7,
        context_metric_flag=0,
        source_x_offset=5,
    )
    checks.append(assert_equal("0xd3b2-modeled unflagged source fields", unflagged_fixture, {
        "source": {
            "context": 0x00000000,
            "host_char": 0x41,
            "mapped": 0x01,
            "glyph_entry": 0,
            "glyph_width": 0,
            "glyph_rows": 0,
            "flag": 0,
            "x": 22,
            "y": 22,
            "context_slot": 3,
        },
        "overflow_correction": 0,
        "record0": 0x02,
        "record1": 0x03,
        "record2_signed": 0x04,
        "cursor_x": 10,
        "cursor_y": 20,
        "printable_offset": 7,
        "orientation": 0,
        "orientation_extent": 0,
        "context_metric_flag": 0,
        "source_x_offset": 5,
    }))
    unflagged_overflow_fixture = position_unflagged_text_source_via_d3b2(
        inline_source,
        inline_record,
        cursor_x=10,
        cursor_y=20,
        printable_offset=20,
        context_metric_flag=1,
        source_x_offset=-15,
    )
    checks.append(assert_equal("0xd3b2-modeled unflagged overflow source fields", unflagged_overflow_fixture, {
        "source": {
            "context": 0x00000000,
            "host_char": 0x41,
            "mapped": 0x01,
            "glyph_entry": 0,
            "glyph_width": 0,
            "glyph_rows": 0,
            "flag": 0,
            "x": 9,
            "y": 18,
            "context_slot": 3,
        },
        "overflow_correction": 0x00050000,
        "record0": 0x02,
        "record1": 0x03,
        "record2_signed": 0x04,
        "cursor_x": 10,
        "cursor_y": 20,
        "printable_offset": 20,
        "orientation": 0,
        "orientation_extent": 0,
        "context_metric_flag": 1,
        "source_x_offset": -15,
    }))

    tall_text_source = build_text_source_object_from_1393a(resources, 0x440946B4, 0x20, x=0, y=0, context_slot=0)
    checks.append(assert_equal("0x1393a-modeled tall text source object fields", tall_text_source, {
        "context": 0x440946B4,
        "host_char": 0x20,
        "mapped": 0x1F,
        "glyph_entry": 0x0146B4,
        "glyph_width": 74,
        "glyph_rows": 1108,
        "flag": 1,
        "x": 0,
        "y": 0,
        "context_slot": 0,
    }))
    tall_bucket = queue_text_source_via_12f2e(resources, tall_text_source)
    checks.append(assert_equal("0x12f2e-modeled segmented bucket metadata", {key: tall_bucket[key] for key in ("path", "object_size", "capacity", "entry_size", "selector", "coord", "glyph", "rows", "width")}, {
        "path": "segmented",
        "object_size": 0x28,
        "capacity": 0x08,
        "entry_size": 4,
        "selector": 0x2000,
        "coord": 0,
        "glyph": 0x1F,
        "rows": 1108,
        "width": 74,
    }))
    checks.append(assert_equal("0x12f2e-modeled segmented bucket objects", tall_bucket["objects"], [
        {"bucket_index": 64, "segment": 8, "object": bytes.fromhex("00 00 00 00 20 00 00 01 1f 08 00 00")},
        {"bucket_index": 56, "segment": 7, "object": bytes.fromhex("00 00 00 00 20 00 00 01 1f 07 00 00")},
        {"bucket_index": 48, "segment": 6, "object": bytes.fromhex("00 00 00 00 20 00 00 01 1f 06 00 00")},
        {"bucket_index": 40, "segment": 5, "object": bytes.fromhex("00 00 00 00 20 00 00 01 1f 05 00 00")},
        {"bucket_index": 32, "segment": 4, "object": bytes.fromhex("00 00 00 00 20 00 00 01 1f 04 00 00")},
        {"bucket_index": 24, "segment": 3, "object": bytes.fromhex("00 00 00 00 20 00 00 01 1f 03 00 00")},
        {"bucket_index": 16, "segment": 2, "object": bytes.fromhex("00 00 00 00 20 00 00 01 1f 02 00 00")},
        {"bucket_index": 8, "segment": 1, "object": bytes.fromhex("00 00 00 00 20 00 00 01 1f 01 00 00")},
        {"bucket_index": 0, "segment": 0, "object": bytes.fromhex("00 00 00 00 20 00 00 01 1f 00 00 00")},
    ]))
    tall_targets = tall_builtin_glyph_targets(resources)
    checks.append(assert_equal("firmware-scanned tall built-in glyph target summary", {
        "count": len(tall_targets),
        "nonzero_delta": sum(1 for target in tall_targets if target["delta"] != 0),
        "modes": sorted({target["mode"] for target in tall_targets}),
        "widths": sorted({target["width"] for target in tall_targets}),
        "rows": sorted({target["rows"] for target in tall_targets}),
        "unique_entries": len({target["entry"] for target in tall_targets}),
        "unique_bases": len({target["base"] for target in tall_targets}),
    }, {
        "count": 420,
        "nonzero_delta": 0,
        "modes": [0],
        "widths": [74],
        "rows": [972, 976, 1104, 1108, 19900, 20062, 35584, 37624, 37818, 38600],
        "unique_entries": 24,
        "unique_bases": 24,
    }))

    compact_text_object = produced_bucket["object"]
    assert isinstance(compact_text_object, bytes)
    compact_mode0 = render_compact_text_bucket_object(data, resources, (0x440946B4,), compact_text_object)
    checks.append(assert_equal("compact text bucket object fixture metadata", {key: compact_mode0[key] for key in ("selector", "context_slot", "count", "rendered", "payload")}, {
        "selector": 0,
        "context_slot": 0,
        "count": 1,
        "rendered": [{
            "glyph": 32,
            "coord": 0,
            "dest_base": 0,
            "span": 1,
            "rows": 22,
            "width": 4,
            "helper": 0x01FA5C,
        }],
        "payload": bytes.fromhex("00 01 20 00 00"),
    }))
    checks.append(assert_equal("compact text bucket object fixture rendered rows", compact_mode0["rows"], line_printer_glyph32_rows))
    positioned_text_object = positioned_bucket["object"]
    assert isinstance(positioned_text_object, bytes)
    positioned_mode0 = render_compact_text_bucket_object(data, resources, (0x440946B4,), positioned_text_object)
    checks.append(assert_equal("0xd824-positioned compact text rendered rows", positioned_mode0["rows"], [f"................{row}" for row in line_printer_glyph32_rows]))
    overflow_positioned_text_object = overflow_positioned_bucket["object"]
    assert isinstance(overflow_positioned_text_object, bytes)
    overflow_positioned_mode0 = render_compact_text_bucket_object(data, resources, (0x440946B4,), overflow_positioned_text_object)
    checks.append(assert_equal("0xd824-negative-overflow compact text rendered rows", overflow_positioned_mode0["rows"], [f"................................{row}" for row in line_printer_glyph32_rows]))
    printable_stream = render_single_printable_stream(data, resources, b"!", 0x440946B4, cursor_x=10, cursor_y=21)
    printable_stream_source = printable_stream["source"]
    printable_stream_bucket = printable_stream["bucket"]
    printable_stream_rendered = printable_stream["rendered"]
    assert isinstance(printable_stream_source, dict)
    assert isinstance(printable_stream_bucket, dict)
    assert isinstance(printable_stream_rendered, dict)
    checks.append(assert_equal("single printable byte stream builds positioned compact text object", {
        "stream": printable_stream["stream"],
        "source": printable_stream_source,
        "bucket_object": printable_stream_bucket["object"],
        "rendered": {key: printable_stream_rendered[key] for key in ("selector", "context_slot", "count", "rendered", "payload")},
    }, {
        "stream": b"!",
        "source": text_source,
        "bucket_object": positioned_text_object,
        "rendered": {key: positioned_mode0[key] for key in ("selector", "context_slot", "count", "rendered", "payload")},
    }))
    checks.append(assert_equal("single printable byte stream renders expected rows", printable_stream_rendered["rows"], positioned_mode0["rows"]))

    lines.append("## Built-In Glyph Bitmap Fixtures")
    lines.append("")
    lines.append("These rows are decoded from the resource-ROM bytes returned by the same built-in offset-table path that renderer helper `0x1f354` uses. `#` is a set pixel and `.` is a clear pixel; rows are clipped to the glyph width field.")
    lines.append("")
    for title, glyph, rows in (
        ("context `0x4008004c`, glyph `0`", default_glyph0, default_glyph0_rows),
        ("context `0x44080418`, glyph `0`", courier_glyph0, courier_glyph0_rows),
        ("context `0x440946b4`, glyph `0`", line_printer_glyph0, line_printer_glyph0_rows),
        ("context `0x440946b4`, glyph `32`", line_printer_glyph32, line_printer_glyph32_rows),
    ):
        lines.append(f"### {title}")
        lines.append("")
        lines.append(f"entry `0x{int(glyph['entry']):06x}`, bitmap `0x{int(glyph['bitmap']):06x}`, width `{int(glyph['width'])}`, rows `{int(glyph['rows'])}`, span `{int(glyph['render_span'])}`")
        lines.append("")
        lines.extend(f"`{row}`" for row in rows)
        lines.append("")

    lines.append("## Main Row-Copy Integration Fixtures")
    lines.append("")
    lines.append("These fixtures feed the same resource glyph bytes through the main compact-glyph row-copy table at `0x1f08e`. The destination buffer uses a synthetic `0x20` byte row stride, matching the existing row-copy fixtures, and the reconstructed destination rows must match the direct resource decode above.")
    lines.append("")
    lines.append("| Context | Glyph | Span | Helper | Result |")
    lines.append("| ---: | ---: | ---: | ---: | --- |")
    for context, glyph_index, glyph in (
        (0x4008004C, 0, default_glyph0),
        (0x44080418, 0, courier_glyph0),
        (0x440946B4, 0, line_printer_glyph0),
        (0x440946B4, 32, line_printer_glyph32),
    ):
        span = int(glyph["render_span"])
        lines.append(f"| `0x{context:08x}` | `{glyph_index}` | `{span}` | `0x{u32(data, 0x1F08E + span * 4):06x}` | decoded destination rows match resource rows |")
    lines.append("")

    lines.append("## Direct Control-Code Cursor Fixtures")
    lines.append("")
    lines.append("These fixtures model the packed 12-subunit cursor/page state touched by `0xf02c..0xf55e`. They are synthetic state fixtures, not a full parser byte-stream run yet, but they pin the ROM-derived side effects that text streams need before page-object rendering.")
    lines.append("")
    lines.append("- `ESC &k#G` line-termination bits: `0 -> 0x00`, `1 -> 0x80`, `2 -> 0x60`, `3 -> 0xe0`.")
    lines.append("- CR resets x to the left margin and flushes a pending text span; in mode 1 it also advances y from `20+11/12` by `2/12` to `21+1/12`.")
    lines.append("- LF in mode 2 performs the CR-style x reset before advancing y by VMI.")
    lines.append("- FF in mode 2 performs the CR-style x reset, flushes pending text, ensures/finalizes a page root marker, and leaves pending text/page-eject state as `0xff`.")
    lines.append("- HT from x `17`, left margin `5`, and HMI `1` advances to the next eight-column stop at x `21`; a second fixture clamps HT to page width `90` when the cursor is already beyond the right limit.")
    lines.append("- BS subtracts HMI, clamps at the left margin when it would cross it, and in alternate metrics mode subtracts the previous-width word instead.")
    lines.append("- Byte-stream fixtures now drive the same model from actual PCL/control bytes: `ESC &k1G` followed by CR applies CR+LF, `ESC &k2G` followed by LF applies CR+LF, and `ESC &k0G` followed by HT/BS advances to x `21` then backs up to x `20`.")
    lines.append("- The fixture parser intentionally recognizes only `ESC &k#G`, `ESC E`, and direct control bytes; printable text, combined escape sequences, and real page-object allocation still need fuller parser-driven fixtures.")
    lines.append("")

    lines.append("## `ESC E` Reset Fixtures")
    lines.append("")
    lines.append("These fixtures model the reset sequence documented in `generated/analysis/ic30_ic13_esc_e_reset_flow.md`. They are synthetic state fixtures driven by the actual byte stream `ESC E`; they do not yet start from parser-produced page objects.")
    lines.append("")
    lines.append("- Valid page-root case: flushes pending text span, runs the active-record wait hook, publishes the current page/control record, sets the publication flag, clears transient page bytes, then clears the current page root.")
    lines.append("- Missing/invalid page-root case: clears the current page root without publication.")
    lines.append("- Both cases reset orientation to portrait, recompute the vertical offset from `0x96 - source`, clear the related vertical offset word, reinitialize raster state to scale minus one `3` / scale `4`, refresh HMI and symbol snapshots from the current-font context, reset the parser/data-chain pointer to `0x782d3e`, clear parser/text accumulation state, prune command/data records, and clear reset status `0x782a93`.")
    lines.append("- Remaining gap: replace these synthetic reset-state fixtures with fixtures that enter through the full parser and compare the finalized page/control records produced by a real pending page.")
    lines.append("")

    lines.append("## Compact Text Bucket Fixture")
    lines.append("")
    lines.append("This fixture starts with the base built-in character map that `0x14d9c` creates for `LINE_PRINTER`: host byte `0x21` maps to glyph byte `0x20`. The `0x1393a` source-object model records context `0x440946b4`, glyph entry `0x015330`, flag `1`, `x=0`, `y=0`, and context slot `0`; the `0x12f2e` producer model then emits the short compact text bucket consumed by renderer `0x1effe` / `0x1f034`. The render band is still synthetic and unclipped, but the compact object bytes now come from the modeled source fields rather than a hand-written glyph/coordinate pair.")
    lines.append("")
    lines.append(f"- base map: host `0x{text_source['host_char']:02x}` -> glyph `0x{text_source['mapped']:02x}`")
    lines.append(f"- source fields: context `0x{text_source['context']:08x}`, glyph entry `0x{text_source['glyph_entry']:06x}`, width `{text_source['glyph_width']}`, rows `{text_source['glyph_rows']}`, flag `{text_source['flag']}`, x `{text_source['x']}`, y `{text_source['y']}`, context slot `{text_source['context_slot']}`")
    lines.append(f"- producer path: `{produced_bucket['path']}`, bucket index `{produced_bucket['bucket_index']}`, object size `0x{int(produced_bucket['object_size']):02x}`, capacity `{produced_bucket['capacity']}`, entry size `{produced_bucket['entry_size']}`")
    lines.append(f"- object bytes: `{' '.join(f'{byte:02x}' for byte in compact_text_object)}`")
    lines.append(f"- payload bytes: `{' '.join(f'{byte:02x}' for byte in compact_mode0['payload'])}`")
    lines.append(f"- selector: `0x{int(compact_mode0['selector']):04x}`, context slot `{compact_mode0['context_slot']}`")
    rendered_entry = compact_mode0["rendered"][0]
    assert isinstance(rendered_entry, dict)
    lines.append(
        f"- rendered entry: glyph `{rendered_entry['glyph']}`, coord `0x{int(rendered_entry['coord']):04x}`, "
        f"dest base `+0x{int(rendered_entry['dest_base']):02x}`, span `{rendered_entry['span']}`, helper `0x{int(rendered_entry['helper']):06x}`"
    )
    lines.append("- rendered rows:")
    lines.extend(f"`{row}`" for row in compact_mode0["rows"])
    lines.append("")

    lines.append("## `0xd824` Positioned Text Bucket Fixture")
    lines.append("")
    lines.append("This fixture models the flagged/built-in positioning handoff at `0xd824` before running the same `0x12f2e` producer model. With `LINE_PRINTER` host byte `0x21`, source x-offset `0`, cursor x `10`, cursor y `21`, orientation `0`, and printable offset `0`, the real glyph-entry words at `0x015330` add x offset `6` and subtract y offset `21`; `0xd824` therefore writes source coordinates `x=16`, `y=0`, context slot `0`, then `0x12f2e` emits compact coord `0x0001`.")
    lines.append("")
    positioned_source_report = positioned_fixture["source"]
    assert isinstance(positioned_source_report, dict)
    lines.append(f"- positioned source: x `{positioned_source_report['x']}`, y `{positioned_source_report['y']}`, context slot `{positioned_source_report['context_slot']}`, overflow correction `{positioned_fixture['overflow_correction']}`")
    lines.append(f"- glyph offsets: x `{positioned_fixture['glyph_x_offset']}`, y `{positioned_fixture['glyph_y_offset']}`")
    lines.append(f"- object bytes: `{' '.join(f'{byte:02x}' for byte in positioned_text_object)}`")
    lines.append(f"- payload bytes: `{' '.join(f'{byte:02x}' for byte in positioned_mode0['payload'])}`")
    positioned_rendered = positioned_mode0["rendered"][0]
    assert isinstance(positioned_rendered, dict)
    lines.append(
        f"- rendered entry: glyph `{positioned_rendered['glyph']}`, coord `0x{int(positioned_rendered['coord']):04x}`, "
        f"dest base `+0x{int(positioned_rendered['dest_base']):02x}`, span `{positioned_rendered['span']}`, helper `0x{int(positioned_rendered['helper']):06x}`"
    )
    lines.append("- rendered rows:")
    lines.extend(f"`{row}`" for row in positioned_mode0["rows"])
    lines.append("")
    lines.append("The same model also exercises the negative-left overflow branch. With cursor x `10` and source x-offset `-26`, `0xd824` sees `cursor_x + source_x_offset = -16`, returns overflow correction `0x00100000`, rewrites the working cursor to `26`, then adds the glyph x offset `6` to queue source x `32`. That produces compact coord `0x0002`, still byte-aligned for the current renderer fixture.")
    lines.append("")
    overflow_source_report = overflow_positioned_fixture["source"]
    assert isinstance(overflow_source_report, dict)
    lines.append(f"- overflow positioned source: x `{overflow_source_report['x']}`, y `{overflow_source_report['y']}`, context slot `{overflow_source_report['context_slot']}`, overflow correction `0x{int(overflow_positioned_fixture['overflow_correction']):08x}`")
    lines.append(f"- overflow object bytes: `{' '.join(f'{byte:02x}' for byte in overflow_positioned_text_object)}`")
    lines.append(f"- overflow payload bytes: `{' '.join(f'{byte:02x}' for byte in overflow_positioned_mode0['payload'])}`")
    overflow_rendered = overflow_positioned_mode0["rendered"][0]
    assert isinstance(overflow_rendered, dict)
    lines.append(
        f"- overflow rendered entry: glyph `{overflow_rendered['glyph']}`, coord `0x{int(overflow_rendered['coord']):04x}`, "
        f"dest base `+0x{int(overflow_rendered['dest_base']):02x}`, span `{overflow_rendered['span']}`, helper `0x{int(overflow_rendered['helper']):06x}`"
    )
    lines.append("- overflow rendered rows:")
    lines.extend(f"`{row}`" for row in overflow_positioned_mode0["rows"])
    lines.append("")

    lines.append("## Single Printable Byte Stream Fixture")
    lines.append("")
    lines.append("This fixture starts one step earlier than the producer-modeled text bucket: the host byte stream is `21` (`!`). Under the documented normal parser conditions, that byte reaches `0xd04a`, enters `0x1393a`, maps through the active `LINE_PRINTER` character map to glyph byte `0x20`, takes the flagged/built-in `0xd824` path with cursor `(10,21)`, emits the same short `0x12f2e` compact object as the positioned fixture, and renders through `0x1effe` / `0x1f034`.")
    lines.append("")
    lines.append("- stream bytes: `21`")
    lines.append(f"- source object from `0x1393a`: context `0x{printable_stream_source['context']:08x}`, host `0x{printable_stream_source['host_char']:02x}`, mapped glyph `0x{printable_stream_source['mapped']:02x}`, glyph entry `0x{printable_stream_source['glyph_entry']:06x}`, flag `{printable_stream_source['flag']}`")
    lines.append(f"- compact object bytes: `{' '.join(f'{byte:02x}' for byte in positioned_text_object)}`")
    lines.append("- rendered rows match the `0xd824` positioned text fixture above.")
    lines.append("- remaining gap: broaden this from a one-byte normal printable path into a parser stream that can mix printable text, direct control codes, reset, and page-object allocation without fixture-only state.")
    lines.append("")

    lines.append("## `0xd3b2` Unflagged Positioning Fixture")
    lines.append("")
    lines.append("This fixture pins the unflagged/inline positioning arithmetic at `0xd3b2` with a synthetic inline source record. It intentionally stops before `0x12f2e`, because the inline/downloaded compact payload layout is not implemented yet. The inline record bytes are `02 03 04`, so record byte 2 contributes signed value `4` in both branches.")
    lines.append("")
    unflagged_source_report = unflagged_fixture["source"]
    assert isinstance(unflagged_source_report, dict)
    lines.append(f"- context metric flag clear: cursor `(10,20)`, printable offset `7`, source x-offset `5` -> x `{unflagged_source_report['x']}`, y `{unflagged_source_report['y']}`, context slot `{unflagged_source_report['context_slot']}`, overflow correction `{unflagged_fixture['overflow_correction']}`")
    unflagged_overflow_source_report = unflagged_overflow_fixture["source"]
    assert isinstance(unflagged_overflow_source_report, dict)
    lines.append(f"- context metric flag set plus left overflow: cursor `(10,20)`, printable offset `20`, source x-offset `-15` -> x `{unflagged_overflow_source_report['x']}`, y `{unflagged_overflow_source_report['y']}`, context slot `{unflagged_overflow_source_report['context_slot']}`, overflow correction `0x{int(unflagged_overflow_fixture['overflow_correction']):08x}`")
    lines.append("- remaining gap: replace this synthetic positioning fixture with real parser-produced inline/downloaded source objects and implement their `0x12f2e` payload path.")
    lines.append("")

    lines.append("## Segmented Text Bucket Producer Fixture")
    lines.append("")
    lines.append("The same producer model also covers the `0x12f2e` segmented path where the glyph height word exceeds `0x80`. For `LINE_PRINTER`, host byte `0x20` maps to glyph byte `0x1f`; the resolved table target is the record base `0x0146b4`, whose height word is `0x0454` and width word is `0x004a`. `0x12f2e` therefore sets selector bit `0x2000`, computes segment index `(rows - 1) >> 7 = 8`, and emits one four-byte entry per segment while stepping the bucket index down by eight.")
    lines.append("")
    lines.append(f"- source fields: context `0x{tall_text_source['context']:08x}`, host `0x{tall_text_source['host_char']:02x}`, glyph `0x{tall_text_source['mapped']:02x}`, glyph entry `0x{tall_text_source['glyph_entry']:06x}`, width `{tall_text_source['glyph_width']}`, rows `{tall_text_source['glyph_rows']}`")
    lines.append(f"- producer path: `{tall_bucket['path']}`, selector `0x{int(tall_bucket['selector']):04x}`, object size `0x{int(tall_bucket['object_size']):02x}`, capacity `{tall_bucket['capacity']}`, entry size `{tall_bucket['entry_size']}`")
    lines.append(f"- firmware-scanned tall target summary: `{len(tall_targets)}` targets across `{len({target['base'] for target in tall_targets})}` records; every target has delta `0`, mode `0`, and width `74`, so the verified built-in resources do not yet provide a normal bitmap-entry fixture for rendering `0x1f1f0`")
    lines.append("| Bucket | Segment byte | Object bytes |")
    lines.append("| ---: | ---: | --- |")
    tall_objects = tall_bucket["objects"]
    assert isinstance(tall_objects, list)
    for obj in tall_objects:
        assert isinstance(obj, dict)
        object_bytes = obj["object"]
        assert isinstance(object_bytes, bytes)
        lines.append(f"| `{obj['bucket_index']}` | `{obj['segment']}` | `{' '.join(f'{byte:02x}' for byte in object_bytes)}` |")
    lines.append("")

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
